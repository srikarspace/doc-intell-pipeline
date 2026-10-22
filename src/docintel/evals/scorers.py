"""Score one contract's extracted fields against the CUAD gold labels. Rules are 1b2 decisions."""

import re

import duckdb

from docintel.domain.schema.fields import CUAD_CATEGORY, ContractFields

THRESHOLD = 0.5  # token Jaccard needed for a quote to match a gold span (the CUAD paper uses 0.5)

RULE = {  # field -> how a found answer is judged correct
    "agreement_date": "value",
    "governing_law": "value",
    "parties": "quote",
    "renewal_term": "quote",
    "notice_period_to_terminate_renewal": "quote",
    "cap_on_liability": "quote",
}  # every other field: "presence"


def tokens(text: str) -> set[str]:
    """Lowercase words and numbers, as a set."""
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def jaccard(a: str, b: str) -> float:
    """Shared tokens / all tokens. 1.0 = same words, 0.0 = no word in common."""
    ta, tb = tokens(a), tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def quote_ok(quotes: list[str], spans: list[str]) -> bool:
    """True if any model quote matches any gold span well enough."""
    return any(jaccard(q, s) >= THRESHOLD for q in quotes for s in spans)


def norm_date(text: str | None) -> str | None:
    """CUAD "11/14/17" or model "2017-11-14" -> "2017-11-14". Unknown parts are left out."""
    text = (text or "").strip()
    if "/" in text:  # CUAD: month/day/year, "[]" for an unknown part
        month, day, year = (text.split("/") + ["", ""])[:3]
        if len(year) == 2 and year.isdigit():
            year = ("19" if int(year) > 30 else "20") + year
        parts = [year, month.zfill(2), day.zfill(2)]
    else:  # model: YYYY, YYYY-MM or YYYY-MM-DD
        parts = text.split("-")
    known = []
    for part in parts:  # keep parts until the first unknown one
        if not part.isdigit():
            break
        known.append(part)
    if not known or len(known[0]) != 4:
        return None  # no year, nothing to compare
    return "-".join(known)


def norm_law(text: str | None) -> str | None:
    """Normalize a place: "the State of New York" -> "new york"."""
    if not text:
        return None
    words = " ".join(sorted(tokens(text) - {"the", "state", "of", "laws", "commonwealth"}))
    return words or None


def value_ok(field: str, value: str | None, answer: str | None) -> bool | None:
    """Compare a normalized value with the CUAD answer. None if the answer has no usable value."""
    norm = norm_date if field == "agreement_date" else norm_law
    golds = [norm(part) for part in (answer or "").split(";")]
    golds = [g for g in golds if g]
    if not golds:
        return None
    return norm(value) in golds


def outcome(gold_present: bool, found: bool, correct: bool) -> tuple[int, int, int]:
    """(tp, fp, fn) for one field of one contract. A wrong answer counts as fp and fn."""
    if not gold_present:
        return (0, 1, 0) if found else (0, 0, 0)
    if not found:
        return (0, 0, 1)
    return (1, 0, 0) if correct else (0, 1, 1)


GOLD = """
SELECT l.category, bool_or(l.is_present) AS present,
    list(l.span_text) FILTER (WHERE l.is_present) AS spans, any_value(a.answer) AS answer
FROM labels l LEFT JOIN answers a USING (doc_id, category)
WHERE l.doc_id = ?
GROUP BY l.category
"""


def score_doc(con: duckdb.DuckDBPyConnection, doc_id: str, pred: ContractFields) -> list[dict]:
    """One row per field: the rule used, the checks, and tp/fp/fn."""
    gold = {
        cat: (present, spans or [], answer)
        for cat, present, spans, answer in con.execute(GOLD, [doc_id]).fetchall()
    }
    rows = []
    for field, category in CUAD_CATEGORY.items():
        present, spans, answer = gold[category]
        answer_field = getattr(pred, field)
        rule = RULE.get(field, "presence")
        q_ok = quote_ok(answer_field.quotes, spans)
        v_ok = value_ok(field, answer_field.value, answer) if rule == "value" else None
        if rule == "value" and v_ok is None:
            rule = "quote"  # CUAD has no usable value here, so judge the quote
        correct = {"presence": True, "quote": q_ok, "value": v_ok}[rule]
        tp, fp, fn = outcome(present, answer_field.found, correct)
        rows.append(
            {
                "field": field,
                "rule": rule,
                "gold_present": present,
                "found": answer_field.found,
                "quote_ok": q_ok,
                "value_ok": v_ok,
                "tp": tp,
                "fp": fp,
                "fn": fn,
            }
        )
    return rows
