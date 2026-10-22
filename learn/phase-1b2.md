# Phase 1b2: scoring rules

In this part, you decide how one answer is judged right or wrong (your decisions), then build
`evals/scorers.py`. You build it one piece at a time, with a checkpoint after each piece. At the
end you score the real answer you saved in 1b, field by field.

## Words used in this part

Read these first. 0b words (span, present, absent) are used again.

- **Score**: a number that says how good the answers are. We compute it, we do not guess it.
- **TP (true positive)**: the field is there, and the model found it correctly.
- **FP (false positive)**: the model said something that is wrong or not there.
- **FN (false negative)**: the field is there, and the model missed it.
- **TN (true negative)**: the field is not there, and the model said so.
- **Precision**: of everything the model said, how much was right. `TP / (TP + FP)`. Example: 8
  right out of 10 answers = 0.8.
- **Recall**: of everything that was there, how much the model found. `TP / (TP + FN)`.
  Example: found 8 of 16 = 0.5.
- **F1**: one number that mixes precision and recall. `2 * P * R / (P + R)`.
- **Normalize**: change two texts to one standard form before you compare them. Example:
  `"11/14/17"` and `"2017-11-14"` both become `"2017-11-14"`.
- **Jaccard**: shared words divided by all words. Example: `"the State of Michigan"` and
  `"laws of Michigan"` share 2 of 5 words, so 0.4.
- **Threshold**: the lowest score that still counts as a match. Example: 0.5.

## Objectives

By the end of this part you should be able to:

1. Defend your rule for each field type: yes/no, value, and quote.
2. Explain TP, FP, FN and TN with one real field from the example contract.
3. Explain why an absent field with an absent answer is not counted in precision or recall.
4. Show why a correct short quote can fail a Jaccard threshold.
5. Score one saved answer with `score_doc`, and read the table.

## Dependencies

You install nothing new.

This part needs 1b: `data/examples/ecoscience_v1.json`, the real answer for the example
contract. It makes no LLM call, so it costs nothing.

## The big picture

Before this part, we have one answer and the gold labels, but no rule that says "right".

After this part:

- `answers` holds CUAD's short answer for each contract and category, like `Michigan`.
- `scorers.py` turns one answer into one row per field, with `tp`, `fp` and `fn`.

1c sums these rows over 52 dev contracts into precision and recall per field. That table is E1.
2a and 2b change the pipeline and compare with E1. Every one of those numbers uses your rules.

## Remember this

> A score is only as fair as its rules, so the rules are written down and tested. Each field gets
> one outcome: TP, FP, FN or TN. A wrong answer is both an FP (you said something wrong) and an
> FN (you missed the right one). Absent and absent is a TN: it is correct, but precision and
> recall never count it.
>
> **One field, one outcome. Wrong is FP and FN. TN is right but not counted.**

## Why

**Two texts can say the same thing.** The lawyer wrote `11/14/17`. The model writes
`2017-11-14`. A plain `==` says wrong. Normalizing first says right.

**Quotes never match exactly.** The model copies a little more or a little less than the lawyer
highlighted. An overlap score with a threshold says "close enough".

**Absent fields are most of the data.** 8 of 12 fields are absent in more than 45% of contracts.
The rules must say what happens when either side says "not there".

## Design decisions

- **Gold values come from `master_clauses.csv`.** CUAD's lawyers wrote short answers, like
  `Michigan` and `30 days`. Other option: parse them out of the long spans ourselves. More code,
  and our parser would be one more thing to trust.
- **An `answers` table, loaded by `make data`.** Scoring then needs only SQL. Other option: read
  the CSV inside `scorers.py`. Two places that read CUAD.
- **One rule per field, in a dict `RULE`.** You can see every rule in one place. Other option: if
  statements spread over the code.
- **Token Jaccard on sets of words.** Simple, and order does not matter. Other option: character
  overlap with offsets. Better for 2a, but too strict for a first score.
- **Rows, not totals.** `score_doc` returns one row per field. 1c stores rows and sums them in SQL.
  Other option: return precision and recall. Then you cannot see which contract failed.

## Worked example

Real numbers. Guess before you open each box.

### Round 1: a correct quote that is too short

Take a short gold span for Governing Law: `This Agreement shall be governed by the laws of the
State of Michigan.` The model quotes only `Michigan`. The threshold is 0.5. Is the quote a match?

<details><summary>Guess, then open</summary>

No. Real output:

```
jaccard('Michigan', gold)                                      0.09
jaccard('governed by the laws of the State of Michigan', gold) 0.64
```

That gold span has 11 different words. `Michigan` shares only one of them. The real span in the
example contract is longer, so a short quote does even worse there. The answer is right,
but the quote rule says wrong. So a quote rule needs quotes of about the same size as the gold
spans. Your prompt v1 asks for a full sentence for this reason. Governing Law also uses the value
rule (Step 3), so `Michigan` as a value is fine.
</details>

### Round 2: a date with unknown parts

CUAD's answer is `[]/[]/2020`: the lawyer knew only the year. The model writes `2020-03-01`. Right
or wrong?

<details><summary>Guess, then open</summary>

With the reference rules, wrong. `[]/[]/2020` becomes `"2020"`, and `2020-03-01` stays
`"2020-03-01"`. They are not equal.

You could say "right if the known parts match". Then a model that writes any date in 2020 gets
full points. 25 of the 510 CUAD dates are year-only. This is a real decision, so it is in Step 2.
</details>

### Round 3: the lazy model

Change Of Control is present in 18 of the 52 dev contracts. Model A always says "not there".
Model B always says "there", with a good quote. Guess precision and recall for each.

<details><summary>Guess, then open</summary>

- **Model A**: TP 0, FP 0, FN 18, TN 34. Recall = 0 / 18 = 0. Precision = 0 / 0: no answer at
  all, so we write it as empty, not as 0 or 1.
- **Model B**: TP 18, FP 34, FN 0. Recall = 18 / 18 = 1.0. Precision = 18 / 52 = 0.35.

Model A gets 34 of 52 right (65%), and is useless. That is why we report precision and recall,
not "percent correct". TNs make a lazy model look good.
</details>

## Project setup

Create the empty files:

```sh
$ touch src/docintel/evals/scorers.py tests/test_scorers.py
```

You should now have:

```
src/docintel/
├── domain/
│   ├── extract/extract.py
│   └── schema/fields.py       CUAD_CATEGORY is used here
└── evals/
    ├── datasets.py            + read_answers, load_answers
    ├── scorers.py             empty
    └── store.py
tests/
└── test_scorers.py            empty
data/
└── examples/
    └── ecoscience_v1.json     from 1b
```

## Step 1: gold values (your decision)

**Why.** The value rule needs a right value to compare with. `labels` has only long spans.

Look at the evidence. `master_clauses.csv` has an `-Answer` column for each category. Real values
for the example contract:

| Category | CUAD answer | Gold span (start) |
|---|---|---|
| Agreement Date | `11/14/17` | `14th day of November 2017` |
| Governing Law | `Michigan` | `Regardless of the place of execution hereof, ...` |
| Renewal Term | `successive 1 year` | `The term of this Agreement shall be for one (1) year ...` |
| Notice Period To Terminate Renewal | `30 days` | the same span as Renewal Term |
| Change Of Control | `No` | (absent) |

Over all 510 contracts:

- Agreement Date answers look like `9/99/99`, `99/99/99` or `[]/[]/2020`. 45 are empty.
- Governing Law has 76 empty answers. Some list several places: `Illinois; New York`.
- One column name has a space: `Notice Period To Terminate Renewal- Answer`.

Decide, and write it in a markdown cell called "Scoring rules" in your notebook:

1. **Use CUAD's answers, or parse the spans yourself?**
2. **When the CUAD answer is empty but the span is present,** what decides the field?

Then add this to `src/docintel/evals/datasets.py`, just above `main`, if you use CUAD's answers:

```python
def read_answers(cuad_dir: Path) -> dict[str, dict[str, str]]:
    """key -> {category: answer} from the "-Answer" columns of master_clauses.csv."""
    out = {}
    with (cuad_dir / "master_clauses.csv").open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            answers = {}
            for col, val in r.items():
                category, _, tail = col.rpartition("-")
                if tail.strip() == "Answer" and val.strip():  # one column is "...- Answer"
                    answers[category.strip()] = val.strip()
            out[_key(Path(r["Filename"]).stem)] = answers
    return out


def load_answers(con: duckdb.DuckDBPyConnection, cuad_dir: Path) -> int:
    """(Re)create `answers`: CUAD's short answer per (contract, category). Returns the row count."""
    table = read_answers(cuad_dir)
    rows = [
        (doc["title"], category, answer)
        for doc in read_docs(cuad_dir)
        for category, answer in (_lookup(table, doc["title"]) or {}).items()
    ]
    con.execute(
        "CREATE OR REPLACE TABLE answers (doc_id VARCHAR, category VARCHAR, answer VARCHAR)"
    )
    con.executemany("INSERT INTO answers VALUES (?, ?, ?)", rows)
    return len(rows)
```

*Python here: [`rpartition`](./py/phase-1b2.md#py-1) · `_key` and `_lookup` are from 0b.*

Here, we:

1. Read each CSV row. For each column, cut at the last `-`. If the right part is `Answer`, with
   or without a space, the left part is the category.
2. Keep only answers that are not empty. An empty answer is "no value", not a value.
3. Key each row by the fuzzy file name key from 0b, the same way `read_titles` does.
4. For each contract in the JSON, find its row with `_lookup`, and make one row per answer.
5. Replace the `answers` table and insert all rows.

Update `main` at the bottom of `src/docintel/evals/datasets.py`:

```python
def main() -> None:
    cuad_dir = download_cuad()
    with connect() as con:
        n_contracts, n_labels = load_cuad(con, cuad_dir)
        counts = make_splits(con)
        n_answers = load_answers(con, cuad_dir)
    print(f"Loaded {n_contracts} contracts, {n_labels} label rows, {n_answers} answers")
    print(f"Splits: {counts['dev']} dev, {counts['test']} test")
```

Checkpoint. Close the notebook connection, then:

```sh
$ make data
uv run python -m docintel.evals.datasets
Loaded 510 contracts, 28031 label rows, 19700 answers
Splits: 52 dev, 52 test
```

The splits did not change: same seed, same table. In the notebook, count the value answers on
dev:

```python
con.sql("""
SELECT category, count(*) AS n
FROM answers JOIN splits USING (doc_id)
WHERE split = 'dev'
  AND category IN ('Agreement Date', 'Governing Law', 'Renewal Term', 'Notice Period To Terminate Renewal')
GROUP BY category
ORDER BY category
""")
```

```
┌────────────────────────────────────┬───────┐
│              category              │   n   │
├────────────────────────────────────┼───────┤
│ Agreement Date                     │    47 │
│ Governing Law                      │    44 │
│ Notice Period To Terminate Renewal │    10 │
│ Renewal Term                       │    17 │
└────────────────────────────────────┴───────┘
```

Compare with 0d: Agreement Date is present in 48 dev contracts, but has 47 answers. For that one
contract, the value rule has nothing to compare with.

<details><summary>Reference choice (open after you decide)</summary>

1. CUAD's answers, loaded into `answers` as above.
2. If the answer is empty or has no usable value (like `[]`), judge the field by its quote
   instead. Step 3 does this.
</details>

## Step 2: the match rules (your decision)

**Why.** "Right" needs an exact meaning for quotes and for values.

Decide each question in your "Scoring rules" cell:

1. **Quote threshold.** The CUAD paper counts a match at Jaccard 0.5 or more. Lower is kinder to
   short quotes (Round 1). Higher punishes extra words.
2. **Words.** Lowercase? Keep numbers? Drop punctuation?
3. **Many quotes, many spans.** Is one good pair enough, or must every gold span be matched?
4. **Dates.** Two-digit years: is `17` 1917 or 2017? Unknown parts (Round 2): equal only, or
   "known parts match"?
5. **Law.** Drop "the State of"? What if CUAD lists two places?

Put this in `src/docintel/evals/scorers.py`:

```python
"""Score one contract's extracted fields against the CUAD gold labels. Rules are 1b2 decisions."""

import re

import duckdb

from docintel.domain.schema.fields import CUAD_CATEGORY, ContractFields

THRESHOLD = 0.5  # token Jaccard needed for a quote to match a gold span (the CUAD paper uses 0.5)


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
```

*Python here: [`re.findall`](./py/phase-1b2.md#py-2) ·
[set `&` and `|`](./py/phase-1b2.md#py-3) · [`any` with two `for`s](./py/phase-1b2.md#py-4).*

Here, we:

1. Turn a text into a set of lowercase words and numbers. Punctuation is dropped.
2. Divide the shared words by all words of both texts.
3. Count a field's quotes as good if any one quote matches any one gold span.

Checkpoint:

```sh
$ uv run python -c "
from docintel.evals.scorers import tokens, jaccard
print(sorted(tokens('ESSI shall have the right to use the name, image, likeness')))
gold = 'This Agreement shall be governed by the laws of the State of Michigan.'
print(round(jaccard('governed by the laws of the State of Michigan', gold), 2), round(jaccard('Michigan', gold), 2))"
['essi', 'have', 'image', 'likeness', 'name', 'right', 'shall', 'the', 'to', 'use']
0.64 0.09
```

`the` appears twice in the text, but once in the set. Now add the value rules to the bottom of
`src/docintel/evals/scorers.py`:

```python
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
```

*Python here: [string methods: `split`, `zfill`, `isdigit`, `join`](./py/phase-1b2.md#py-5).*

Here, we:

1. In `norm_date`, read CUAD's `month/day/year` or the model's `YYYY-MM-DD`. A two-digit year
   above 30 is 19xx, else 20xx. Then keep parts in the order year, month, day, until the first
   unknown one.
2. In `norm_law`, drop the filler words and sort the rest, so word order does not matter.
3. In `value_ok`, split CUAD's answer at `;`, normalize each place, and check if the model's
   value is one of them.
4. Return `None`, not `False`, when CUAD has no usable value. "Cannot judge" is not "wrong".

Checkpoint. Guess each line first:

```sh
$ uv run python -c "
from docintel.evals.scorers import norm_date, norm_law, value_ok
for d in ['11/14/17', '2017-11-14', '[]/[]/2020', '09/[]/2019', '[]/[]/[]', '2020']: print(repr(d), '->', repr(norm_date(d)))
print(norm_law('the State of Michigan'), '|', norm_law('Illinois; New York'), '|', value_ok('governing_law', 'New York', 'Illinois; New York'))"
'11/14/17' -> '2017-11-14'
'2017-11-14' -> '2017-11-14'
'[]/[]/2020' -> '2020'
'09/[]/2019' -> '2019-09'
'[]/[]/[]' -> None
'2020' -> '2020'
michigan | illinois new york | True
```

`norm_law('Illinois; New York')` mixes both places, but `value_ok` splits at `;` first. So `New
York` matches the second place.

<details><summary>Reference choice (open after you decide)</summary>

1. Threshold 0.5, as in the CUAD paper. Short quotes fail, so prompt v1 asks for full sentences.
2. Lowercase letters and numbers only.
3. One good pair is enough for the field. Per-span scoring is a later extension.
4. `> 30` means 19xx: CUAD contracts are from about 1990 to 2020. Equal only: no points for
   guessing a full date when the lawyer knew only the year.
5. Drop "the", "state", "of", "laws", "commonwealth". Any one of the `;` places counts.
</details>

## Step 3: the outcome table (your decision)

**Why.** Each field of each contract needs exactly one outcome, so 1c can add them up.

Decide in your "Scoring rules" cell:

1. **Which rule for which field?** `presence` (found or not), `value` (Step 2 value rules), or
   `quote` (Step 2 quote rule). The PLAN suggests presence for yes/no, value for dates and law,
   quotes for the rest.
2. **Found, but wrong.** FP only, or FP and FN?
3. **Gold absent, model found.** FP, even with a good-looking quote?

Add `RULE` to `src/docintel/evals/scorers.py`, just below `THRESHOLD`:

```python
RULE = {  # field -> how a found answer is judged correct
    "agreement_date": "value",
    "governing_law": "value",
    "parties": "quote",
    "renewal_term": "quote",
    "notice_period_to_terminate_renewal": "quote",
    "cap_on_liability": "quote",
}  # every other field: "presence"
```

Then add `outcome` to the bottom of `src/docintel/evals/scorers.py`:

```python
def outcome(gold_present: bool, found: bool, correct: bool) -> tuple[int, int, int]:
    """(tp, fp, fn) for one field of one contract. A wrong answer counts as fp and fn."""
    if not gold_present:
        return (0, 1, 0) if found else (0, 0, 0)
    if not found:
        return (0, 0, 1)
    return (1, 0, 0) if correct else (0, 1, 1)
```

Here, we:

1. List the fields that do not use `presence`. The six yes/no and license fields are only
   "found or not".
2. Gold absent: found is an FP, not found is a TN, written `(0, 0, 0)`.
3. Gold present, not found: FN.
4. Gold present, found: TP if correct, else FP and FN.

Checkpoint. Guess the five tuples first:

```sh
$ uv run python -c "
from docintel.evals.scorers import outcome
print([outcome(*c) for c in [(False, False, True), (False, True, True), (True, False, True), (True, True, True), (True, True, False)]])"
[(0, 0, 0), (0, 1, 0), (0, 0, 1), (1, 0, 0), (0, 1, 1)]
```

<details><summary>Reference choice (open after you decide)</summary>

1. The `RULE` dict above. Parties uses the quote rule: its gold spans are the names, so a name in
   `quotes` matches a span closely.
2. FP and FN. A wrong governing law is a wrong answer and a missed right one. Counting only FP
   would make a wrong answer look better than no answer.
3. FP. The lawyer found nothing. A quote there is either a mistake or a disagreement. Both cost
   the user time.
</details>

## Step 4: score one contract

**Why.** This is the function 1c calls for every dev contract.

Add to the bottom of `src/docintel/evals/scorers.py`:

```python
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
```

*Python here: [`list(...) FILTER` and `any_value` in SQL](./py/phase-1b2.md#py-6) ·
`getattr`: [1a2 PY-6](./py/phase-1a2.md#py-6).*

Here, we:

1. Read the gold for one contract in one query: present or not, the list of spans, and CUAD's
   answer. `LEFT JOIN` keeps categories that have no answer.
2. Go through your 12 fields with `CUAD_CATEGORY` from 1a.
3. Check the quotes for every field, and the value only where the rule is `value`.
4. If CUAD has no usable value, use the quote rule instead (Step 1, question 2).
5. Turn the checks into `(tp, fp, fn)` with `outcome`, and keep one row per field.

`quote_ok` is in every row, even when the rule is `presence`. 2a uses it to find found-but-unproven
answers.

Checkpoint. Score the answer you saved in 1b:

```sh
$ uv run python - <<'EOF'
import duckdb
from docintel.domain.schema.fields import ContractFields
from docintel.evals.scorers import score_doc
DOC = 'EcoScienceSolutionsInc_20171117_8-K_EX-10.1_10956472_EX-10.1_Endorsement Agreement'
pred = ContractFields.model_validate_json(open('data/examples/ecoscience_v1.json').read())
con = duckdb.connect('data/docintel.duckdb', read_only=True)
rows = score_doc(con, DOC, pred)
for r in rows:
    print(f"{r['field']:36} {r['rule']:8} {r['gold_present']!s:5} {r['found']!s:5} {r['quote_ok']!s:5} {r['value_ok']!s:5} {r['tp']} {r['fp']} {r['fn']}")
print({k: sum(r[k] for r in rows) for k in ('tp', 'fp', 'fn')})
EOF
```

This one uses a heredoc (`<<'EOF' ... EOF`), not `-c "..."`. Inside `"..."`, zsh reads `!s` as a
history command and stops with `no such word in event`. The quotes around `'EOF'` tell zsh to
leave the text alone.

<!-- LIVE OUTPUT: score table from the user's saved 1b answer -->

*Python here: [f-string widths like `:36` and `!s`](./py/phase-1b2.md#py-7).*

The columns are: field, rule, gold present, found, quote ok, value ok, tp, fp, fn.

Read the table. For each field with `fp` or `fn`, find the reason in the columns:

1. `found` false but `gold_present` true: the model missed it.
2. `rule` quote and `quote_ok` false: the quote did not overlap enough. Look at its length.
3. `rule` value and `value_ok` false: compare the two values by hand.

Write each miss in your notebook: is the model wrong, or is the rule too strict? 1c will show
which happens more.

## Step 5: a test for the rules that must never break

**Why.** If a rule changes by mistake, every later number changes, and nothing else tells you.
Four things must stay true: the Jaccard edges, the date forms, the outcome table, and the
counting of absent fields.

Put this in `tests/test_scorers.py`:

```python
"""Scoring rules on tiny hand-made cases. No network, no CUAD files."""

import pytest

from docintel.domain.schema.fields import CUAD_CATEGORY, ContractFields, Names
from docintel.evals.scorers import jaccard, norm_date, outcome, score_doc
from docintel.evals.store import connect

LAW = "This Agreement shall be governed by the laws of the State of Michigan."


def test_jaccard():
    assert jaccard(LAW, LAW.upper()) == 1.0
    assert jaccard("Michigan", "Delaware") == 0.0
    assert jaccard("", LAW) == 0.0


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("11/14/17", "2017-11-14"),
        ("2017-11-14", "2017-11-14"),
        ("[]/[]/2020", "2020"),
        ("4/1/98", "1998-04-01"),
        ("[]/[]/[]", None),
        (None, None),
    ],
)
def test_norm_date(text, expected):
    assert norm_date(text) == expected


def test_outcome_table():
    assert outcome(gold_present=False, found=False, correct=True) == (0, 0, 0)  # true negative
    assert outcome(gold_present=False, found=True, correct=True) == (0, 1, 0)
    assert outcome(gold_present=True, found=False, correct=True) == (0, 0, 1)
    assert outcome(gold_present=True, found=True, correct=True) == (1, 0, 0)
    assert outcome(gold_present=True, found=True, correct=False) == (0, 1, 1)


def absent(cls) -> dict:
    """An empty answer for one field model."""
    data = {"quotes": [], "found": False}
    if "value" in cls.model_fields:
        data["value"] = [] if cls is Names else None
    return data


def test_score_doc_counts_absent_fields():
    """Gold: only Governing Law is present. The model finds it, and a non-compete that is absent."""
    pred = {f: absent(info.annotation) for f, info in ContractFields.model_fields.items()}
    pred["governing_law"] = {"quotes": [LAW], "value": "Michigan", "found": True}
    pred["non_compete"] = {"quotes": ["shall not compete"], "found": True}
    with connect(":memory:") as con:
        con.execute(
            "CREATE TABLE labels (doc_id TEXT, category TEXT, span_text TEXT, is_present BOOL)"
        )
        con.execute("CREATE TABLE answers (doc_id TEXT, category TEXT, answer TEXT)")
        for category in CUAD_CATEGORY.values():
            present = category == "Governing Law"
            span = LAW if present else None
            con.execute("INSERT INTO labels VALUES ('d1', ?, ?, ?)", [category, span, present])
        con.execute("INSERT INTO answers VALUES ('d1', 'Governing Law', 'Michigan')")
        rows = {r["field"]: r for r in score_doc(con, "d1", ContractFields.model_validate(pred))}
    assert (rows["governing_law"]["tp"], rows["governing_law"]["value_ok"]) == (1, True)
    assert rows["non_compete"]["fp"] == 1
    assert sum(r["tp"] + r["fp"] + r["fn"] for r in rows.values()) == 2  # 10 true negatives
```

*Python here: [`@pytest.mark.parametrize`](./py/phase-1b2.md#py-8).*

Here, we:

1. Check the Jaccard edges: same words in another case, no shared words, an empty text.
2. Run `norm_date` on six inputs in one test, with `parametrize`. Each pair is its own test.
3. Check all five rows of the outcome table.
4. Build a fake gold with only Governing Law present, and a fake answer for all 12 fields. The
   `absent` helper fills in the empty shape for each field model.
5. Check one TP, one FP, and that the other 10 fields add nothing: they are true negatives.

The fake tables have only the columns `score_doc` reads. No CUAD files, no key.

Checkpoint:

```sh
$ make lint && make test
All checks passed!
...
tests/test_data_load.py ....                                             [ 13%]
tests/test_extract.py ...                                                [ 23%]
tests/test_llm.py ....                                                   [ 36%]
tests/test_schema.py ....                                                [ 50%]
tests/test_scorers.py .........                                          [ 80%]
tests/test_smoke.py .                                                    [ 83%]
tests/test_splits.py .....                                               [100%]

============================== 30 passed in 0.87s ==============================
```

`test_scorers.py` shows 9 dots: `parametrize` made 6 tests out of one.

Your project should now look like this:

```
src/docintel/
├── domain/
│   ├── extract/extract.py
│   └── schema/fields.py
└── evals/
    ├── datasets.py            + read_answers, load_answers; main loads answers
    ├── scorers.py             THRESHOLD, tokens, jaccard, quote_ok, norm_date, norm_law,
    │                          value_ok, RULE, outcome, GOLD, score_doc
    └── store.py
tests/
├── test_scorers.py            9 tests
└── ...
data/
└── docintel.duckdb            + answers (19,700 rows)
```

<details><summary>Full <code>src/docintel/evals/scorers.py</code></summary>

```python
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
```
</details>

## Break it on purpose

**Break 1: wrong counts as FP only.** In `outcome`, change the last line to
`return (1, 0, 0) if correct else (0, 1, 0)`. Guess which test fails:

```
E       assert (0, 1, 0) == (0, 1, 1)
E         At index 2 diff: 0 != 1
FAILED tests/test_scorers.py::test_outcome_table - assert (0, 1, 0) == (0, 1, 1)
========================= 1 failed, 29 passed in 0.56s =========================
```

With this change, a wrong answer would hurt precision but not recall. A model that answers every
field, right or wrong, would get better recall than an honest one. Change it back.

**Break 2: all two-digit years are 19xx.** Change the year line to `year = "19" + year`. Guess
which of the six date cases fails:

```
E       AssertionError: assert '1917-11-14' == '2017-11-14'
FAILED tests/test_scorers.py::test_norm_date[11/14/17-2017-11-14] - Assertion...
========================= 1 failed, 29 passed in 0.81s =========================
```

Only `11/14/17`. `4/1/98` still passes, because 98 really is 1998. The test name shows which
case failed. Change it back.

## Experiment

This part scores one contract, not a dataset. There is no `run_id` yet, so there is no
`EXPERIMENTS.md` entry. Your "Scoring rules" cell is the record. E1 in 1c will cite it.

## Gotchas

- **Never change a rule after E1 without a new run.** Old numbers used the old rule. Change the
  rule, rerun, and log a new entry.
- **Do not tune the rules on test.** Look at dev misses only. A rule that fits test makes the
  final number lie.
- **`make data` replaces `answers`, `contracts` and `labels`, but not `llm_calls`.** Your logged
  calls stay.
- **Precision with no answers.** `TP + FP = 0` means divide by zero. In 1c, show it as empty, not
  0 (Round 3).
- **A `KeyError` in `score_doc`.** `gold[category]` failed: a name in `CUAD_CATEGORY` is not a
  category in `labels`. The 1a test should have caught it.

## Explain back, then commit

Explain each changed file to Claude in a few sentences (the rule in `PLAN.md`): `datasets.py`
(the two new functions and the column name trap), `scorers.py` (each rule and its evidence),
`test_scorers.py` (each test), and the notebook "Scoring rules" cell with the score table.
Then:

```sh
$ git status
$ git add src/docintel/evals/datasets.py src/docintel/evals/scorers.py tests/test_scorers.py notebooks/00_explore.ipynb
$ git commit -m "phase 1b2: scoring rules, answers table, scorers.py"
```

## Conclusion

What you have now:

- An `answers` table with CUAD's short answers.
- Scoring rules for every field, written down, with reasons.
- `score_doc`: one row per field with `tp`, `fp`, `fn` and the checks behind them.
- The first real score for one dev contract.

Go back to the objectives. Check that you can do each one without notes. Then answer:

1. Why is a wrong value both an FP and an FN?
2. A model says "absent" for every field. Its "percent correct" is high. Why are its precision
   and recall still bad?

Want more practice? Try these (optional):

1. Compute Jaccard for each of the model's quotes in your example against its best gold span.
   Which fields are close to 0.5?
2. Try threshold 0.3 and 0.7 on the example. Which outcomes change?
3. Write `score_spans`: precision and recall over spans, not fields, for Parties.

Checklist (`../PLAN.md`): **Precision/recall/F1 per field; span scoring** (span scoring and the
TP/FP/FN rules done; precision, recall and F1 per field come in 1c).
