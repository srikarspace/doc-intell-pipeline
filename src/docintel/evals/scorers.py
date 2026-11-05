"""Score one contract's extracted fields against the CUAD gold labels. Rules are 1b2 decisions."""

import re

import duckdb

from docintel.domain.schema.fields import CUAD_CATEGORY, ContractFields
from docintel.evals.datasets import FIELDS

THRESHOLD = 0.5  # token Jaccard needed for a quote to match a gold span (the CUAD paper uses 0.5)

RULE = {  # field -> how a found answer is judged correct
    "agreement_date": "value",
    "governing_law": "value",
    "parties": "names",
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


INSIDE = 0.8  # share of a quote's words that must be in the span
MIN_WORDS = 4  # a shorter quote is too small to prove anything


def inside(quote: str, span: str) -> bool:
    """True if the quote is part of the span: enough words, and nearly all are in the span."""
    q, s = tokens(quote), tokens(span)
    return len(q) >= MIN_WORDS and len(q & s) / len(q) >= INSIDE


def quote_ok(quotes: list[str], spans: list[str]) -> bool:
    """True if any model quote matches a gold span well enough, or is a part of one."""
    return any(jaccard(q, s) >= THRESHOLD or inside(q, s) for q in quotes for s in spans)


def name_ok(name: str, span: str) -> bool:
    """True if one name holds the other, or they share most words: "Acme" and "Acme, Inc."."""
    a, b = tokens(name), tokens(span)
    return bool(a and b) and (a <= b or b <= a or jaccard(name, span) >= THRESHOLD)


def names_ok(names: list[str], spans: list[str]) -> bool:
    """True if the model gave names, and every one of them matches a gold span."""
    return bool(names) and all(any(name_ok(n, s) for s in spans) for n in names)


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


LAW_WORDS = {"the", "state", "of", "laws", "commonwealth", "province", "republic", "and"}


def norm_law(text: str | None) -> str | None:
    """Normalize a place: "the State of New York" -> "new york"."""
    if not text:
        return None
    words = " ".join(sorted(tokens(text) - LAW_WORDS))
    return words or None


def value_ok(field: str, value: str | None, answer: str | None) -> bool | None:
    """Compare a normalized value with the CUAD answer. None if the answer has no usable value."""
    norm = norm_date if field == "agreement_date" else norm_law
    parts = (answer or "").split(";")
    golds = [norm(part) for part in [*parts, " ".join(parts)]]  # each place, or all of them
    golds = [g for g in golds if g]
    if not golds:
        return None
    return norm(value) in golds


def blank_date(field: str, spans: list[str]) -> bool:
    """A date the lawyers marked in a form, but with no year filled in: "[●]" or "20___"."""
    return (
        field == "agreement_date"
        and bool(spans)
        and not any(re.search(r"\d{4}", span) for span in spans)
    )


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
        v_ok = None
        if rule == "value":
            v_ok = value_ok(field, answer_field.value, answer)
        elif rule == "names":
            v_ok = names_ok(answer_field.value, spans)
        if rule == "value" and v_ok is None:
            rule = "blank" if blank_date(field, spans) else "quote"  # no usable CUAD value
        checks = {"presence": True, "quote": q_ok, "value": v_ok, "names": v_ok, "blank": True}
        correct = checks[rule]
        tp, fp, fn = (0, 0, 0) if rule == "blank" else outcome(present, answer_field.found, correct)
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


GROUPS = {  # group -> its fields, from the 0d groups in datasets.FIELDS
    group: [field for field, category in CUAD_CATEGORY.items() if category in categories]
    for group, categories in FIELDS.items()
}


def prf(tp: int, fp: int, fn: int) -> dict:
    """Precision, recall and F1. None when there is nothing to divide by."""
    return {
        "precision": tp / (tp + fp) if tp + fp else None,
        "recall": tp / (tp + fn) if tp + fn else None,
        "f1": 2 * tp / (2 * tp + fp + fn) if tp + fp + fn else None,
    }


PER_FIELD = "SELECT field, sum(tp), sum(fp), sum(fn) FROM scores WHERE run_id = ? GROUP BY field"


def metrics(con: duckdb.DuckDBPyConnection, run_id: str) -> list[dict]:
    """P/R/F1 for each field, each group, and all fields. A group adds up its fields' counts."""
    counts = {f: (tp, fp, fn) for f, tp, fp, fn in con.execute(PER_FIELD, [run_id]).fetchall()}
    sets = {field: [field] for field in CUAD_CATEGORY} | GROUPS | {"all": list(CUAD_CATEGORY)}
    rows = []
    for name, fields in sets.items():
        tp = sum(counts[f][0] for f in fields)
        fp = sum(counts[f][1] for f in fields)
        fn = sum(counts[f][2] for f in fields)
        rows.append({"name": name, "tp": tp, "fp": fp, "fn": fn, **prf(tp, fp, fn)})
    return rows
