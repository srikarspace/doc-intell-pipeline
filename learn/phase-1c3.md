# Phase 1c3: the E1 results

In this part, you turn the E1 run into numbers anyone can read: precision, recall and F1 per
field and per group, with cost and latency. You build it one piece at a time, with a checkpoint
after each piece. Then you draw one chart, read the real misses, and finish the E1 entry.

This is part 3 of 4 for Phase 1c. 1c2 ran E1. 1c4 runs the same experiment with other models.

## Words used in this part

Read these first. 1b2 words (precision, recall, F1) and 1c2 words (p50, p95) are used again.

- **Per field**: one score for each of the 12 fields. Example: Governing Law F1 0.9.
- **Group**: the 4 groups of 3 fields from 0d. Example: "basic facts" is Parties, Agreement
  Date and Governing Law.
- **Micro average**: add up TP, FP and FN of all fields first, then compute one score. Common
  fields count more.
- **Macro average**: compute a score for each field, then take the mean. Every field counts the
  same.
- **F1 from counts**: `2TP / (2TP + FP + FN)`. The same number as the 1b2 formula, but it also
  works when precision is empty. Example: TP 0, FP 0, FN 10 gives 0.
- **Baseline**: the run every later run is compared with. Here: E1.
- **Dev dependency**: a library only the developer needs, not the running app. Like
  `devDependencies` in `package.json`.

## Objectives

By the end of this part you should be able to:

1. Read the E1 table: which fields are strong, which are weak.
2. Defend your choice of micro or macro average for groups.
3. Explain precision and recall with one real FP and one real FN from E1.
4. Say if a miss is the model's fault or the scoring rule's fault, with evidence.
5. Print the full results of any run from its `run_id`.

## Dependencies

New library:

- **matplotlib**: draws charts in Python. A dev dependency: only the notebook uses it.

This part needs 1c2: your E1 `run_id`, and the `1b-example` run from 1c Step 4. It makes no LLM
call, so it costs nothing.

## The big picture

Before this part, E1 is 624 rows of TP, FP and FN. Nobody can read that.

After this part:

- `metrics(run_id)` gives precision, recall and F1 per field, per group, and for all fields.
- `report RUN_ID` prints that table with the run's cost and latency.
- E1 is written in `EXPERIMENTS.md`, with a chart and two real misses.

1c4, 2a, 2b and 3b compare with E1 the same way. Phase 5 puts these tables in the README.

## Remember this

> One number hides everything, so look per field, then read the real misses. A miss is the
> model's fault only if the answer is really wrong. Often the answer is right and the rule is
> too strict, and then the fix is a rule, not a model.
>
> **Per field first. Read the misses before you blame the model.**

## Why

**The fields are very different.** Parties is present in all 52 dev contracts, Notice Period in
only 9. A single F1 for all fields mostly measures the common ones.

**A score can be wrong.** In 1b2 you saw a right quote fail the Jaccard threshold. Before you
blame the model, you must look at the text.

**The next parts need a target.** 2a adds validators, 2b adds retries. Each must say "better than
E1 on these fields". That needs the E1 table per field.

## Design decisions

- **`metrics` returns rows, not a printed table.** The CLI prints them, and the notebook charts
  them. Other option: SQL in the notebook only. Then the numbers depend on notebook code that is
  not tested.
- **Groups come from `datasets.FIELDS`.** The 0d groups are written once. Other option: a second
  list in `scorers.py`. Two lists can disagree.
- **F1 from counts.** `2TP / (2TP + FP + FN)` is 0 for a model that never answers, not empty.
  Other option: the harmonic mean of P and R. Empty when P is empty, which hides the worst
  fields.
- **`report` reads cost and latency from `llm_calls`.** That table has every call, also the ones
  sent twice after a Ctrl-C. So the cost is the real cost. Other option: sum the costs of the
  stored answers. That would hide money you really spent.

## Worked example

Real data from your 1b answer, stored as the `1b-example` run in 1c. Guess before you open each
box.

### Round 1: a right answer, scored wrong

For Notice Period To Terminate Renewal, the model quoted:

```
unless either party provides a thirty-day notice of written termination one to the other
```

The gold span is the whole renewal sentence: `The term of this Agreement shall be for one (1)
year ... unless either party provides a thirty-day notice of written termination one to the
other ("Term").` The model's value is `30 days`. TP, FP or FN?

<details><summary>Guess, then open</summary>

FP and FN. The quote is an exact copy, and it is the right part. But it has 14 words and the
gold span has 36. Jaccard is 0.47, just under 0.5.

So this miss is the rule's fault, not the model's. Write misses like this down. If many fields
fail this way, 2a can add a rule like "the quote is inside the gold span".
</details>

### Round 2: the right names, in the wrong place

For Parties, the gold spans are short: `Eco Science Solutions, Inc.`, `ESSI`, `Stephen Marley`,
`Talent`. The model's value lists both parties correctly. Its only quote is the whole first
sentence of the contract. TP, FP or FN?

<details><summary>Guess, then open</summary>

FP and FN. Each short name against a long sentence gives a small Jaccard. Your prompt v1 asks
for "each name and each short name" in `quotes`, but the model copied the sentence instead.

This one is half the model's fault: it did not follow the prompt. It is also a sign that Parties
may need a better rule, such as "every party name in `value` appears in a gold span". Prompt v2
or 2a can test that. Only one change at a time.
</details>

### Round 3: micro or macro

A run has Parties at F1 0.9 (52 contracts with Parties) and Notice Period at F1 0.1 (9
contracts). Guess the "all fields" F1 for these two fields: closer to 0.9 or to 0.5?

<details><summary>Guess, then open</summary>

With the micro average: close to 0.9. Parties has many more TPs, FPs and FNs, so it fills
almost all of the counts. With the macro average: exactly 0.5, the mean of 0.9 and 0.1.

Micro answers "how good is one answer, on average?". Macro answers "how good is a typical
field?". You decide which one the groups use in Step 1.
</details>

## Project setup

Install matplotlib as a dev dependency, and create the test file:

```sh
uv add --dev matplotlib
touch tests/test_metrics.py
```

uv prints the packages it added, `matplotlib` among them.

*Python here: [`uv add --dev`](./py/phase-1c3.md#py-1).*

You should now have:

```
src/docintel/evals/
├── datasets.py                FIELDS: the 4 groups
├── runner.py                  from 1c2
└── scorers.py                 score_doc
tests/
└── test_metrics.py            empty
pyproject.toml                 + matplotlib in the dev group
```

## Step 1: precision and recall per field and group (your decision)

**Why.** E1 needs one table that anyone can read: a row per field, per group, and for all.

Look at the evidence. Dev contracts where each field is present, from `labels`:

| Field | Present in | Field | Present in |
|---|---|---|---|
| Parties | 52 | Renewal Term | 20 |
| Agreement Date | 48 | Non-Transferable License | 14 |
| Governing Law | 45 | Non-Compete | 13 |
| Anti-Assignment | 41 | Change Of Control | 10 |
| Cap On Liability | 29 | Ip Ownership Assignment | 10 |
| License Grant | 22 | Notice Period To Terminate Renewal | 9 |

Decide, and write it in your "Scoring rules" cell:

1. **Groups and "all": micro or macro?** (Round 3.)
2. **Precision with no answers (`TP + FP = 0`)**: empty, as in 1b2? And F1 in that case: empty,
   or 0?

Update the imports at the top of `src/docintel/evals/scorers.py`:

```python
import re

import duckdb

from docintel.domain.schema.fields import CUAD_CATEGORY, ContractFields
from docintel.evals.datasets import FIELDS
```

Then add to the bottom of `src/docintel/evals/scorers.py`:

```python
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
```

*Python here: [`x if test else y` inside a dict](./py/phase-1c3.md#py-2) · `|` on dicts:
[0b PY-6](./py/phase-0b.md#py-6) · `**`: [1c PY-4](./py/phase-1c.md#py-4).*

Here, we:

1. Build `GROUPS` from the 0d groups: each group gets the attribute names of its 3 fields.
2. In `prf`, return `None` for any number that would divide by zero. F1 uses the count formula.
3. In `metrics`, sum TP, FP and FN per field for this run, in one SQL query.
4. Make one dict of "sets": each field alone, each group, and "all".
5. For each set, add up the counts, then compute the three scores. Adding counts first is the
   micro average.

Checkpoint. Guess the last line first: what is F1 for all fields of your 1b answer?

```sh
uv run python -c "
from docintel.evals.scorers import GROUPS, metrics, prf
from docintel.evals.store import connect
print(GROUPS['basic facts'])
print(prf(0, 0, 10))
with connect() as con:
    for r in metrics(con, '1b-example')[-5:]:
        print(r['name'], r['tp'], r['fp'], r['fn'], round(r['f1'], 2))"
```

```text
['parties', 'agreement_date', 'governing_law']
{'precision': None, 'recall': 0.0, 'f1': 0.0}
basic facts 2 1 1 0.67
yes/no + quote 2 0 0 1.0
numbers/terms 1 1 1 0.5
license/IP 2 0 0 1.0
all 7 2 2 0.78
```

1. The group lists your attribute names, so it matches the `field` column in `scores`.
2. The lazy model from 1b2 Round 3: precision empty, recall 0, F1 0.
3. The 7 TP, 2 FP and 2 FN from 1c Step 4, split into the 4 groups. The two misses (Parties and
   Notice Period) are Rounds 1 and 2.

<details><summary>Reference choice (open after you decide)</summary>

1. Micro for groups and "all". It answers "how often is one answer right", which is what a user
   of the product feels. Show the per-field table next to it, so rare fields are never hidden.
   Macro F1 is an optional extra column.
2. Precision empty, as in 1b2: "no answers" is not "0% right". F1 from counts, so a field the
   model never finds shows 0. An empty F1 would hide the worst fields.
</details>

## Step 2: the report command

**Why.** One command should print everything E1 needs, from a `run_id`.

Update the scorers import at the top of `src/docintel/evals/runner.py`:

```python
from docintel.evals.scorers import metrics, score_doc
```

Add this to `src/docintel/evals/runner.py`, just above `parse_args`:

```python
COST = """
SELECT count(*), sum(cost_usd), quantile_cont(latency_ms, 0.5) / 1000,
    quantile_cont(latency_ms, 0.95) / 1000, count(*) FILTER (WHERE NOT ok)
FROM llm_calls WHERE run_id = ?
"""


def fmt(x: float | None) -> str:
    return "-" if x is None else f"{x:.2f}"


def report(con: duckdb.DuckDBPyConnection, run_id: str) -> None:
    """Print P/R/F1 per field, per group and for all fields, then cost and latency."""
    print(f"{'':36} {'tp':>4} {'fp':>4} {'fn':>4} {'P':>5} {'R':>5} {'F1':>5}")
    for r in metrics(con, run_id):
        scores = f"{fmt(r['precision']):>5} {fmt(r['recall']):>5} {fmt(r['f1']):>5}"
        print(f"{r['name']:36} {r['tp']:4} {r['fp']:4} {r['fn']:4} {scores}")
    calls, cost, p50, p95, bad = con.execute(COST, [run_id]).fetchone()
    if calls:  # the 1b-example run has scores but no logged calls
        print(f"{calls} calls, ${cost:.4f}, p50 {p50:.1f} s, p95 {p95:.1f} s, {bad} bad answers")
```

Add a third subcommand in `parse_args`, just after `rescore.add_argument("run_id")`:

```python
    show = sub.add_parser("report", help="print P/R per field and group, cost and latency")
    show.add_argument("run_id")
```

And in `main`, just after the `score` block:

```python
        if args.command == "report":
            report(con, args.run_id)
            return
```

*Python here: f-string widths are in [1b2 PY-7](./py/phase-1b2.md#py-7).*

Here, we:

1. Read the run's calls from `llm_calls`: how many, total cost, p50 and p95 in seconds, and
   how many answers failed the schema.
2. Print the scores with 2 decimals, and `-` for an empty number.
3. Skip the cost line when the run has no logged calls, like `1b-example`.
4. Add `report RUN_ID` to the CLI, next to `run` and `score`.

Checkpoint. First on the `1b-example` run, which costs nothing:

```sh
uv run python -m docintel.evals.runner report 1b-example
```

```text
                                       tp   fp   fn     P     R    F1
parties                                 0    1    1  0.00  0.00  0.00
agreement_date                          1    0    0  1.00  1.00  1.00
governing_law                           1    0    0  1.00  1.00  1.00
non_compete                             1    0    0  1.00  1.00  1.00
change_of_control                       0    0    0     -     -     -
anti_assignment                         1    0    0  1.00  1.00  1.00
renewal_term                            1    0    0  1.00  1.00  1.00
notice_period_to_terminate_renewal      0    1    1  0.00  0.00  0.00
cap_on_liability                        0    0    0     -     -     -
license_grant                           1    0    0  1.00  1.00  1.00
ip_ownership_assignment                 0    0    0     -     -     -
non_transferable_license                1    0    0  1.00  1.00  1.00
basic facts                             2    1    1  0.67  0.67  0.67
yes/no + quote                          2    0    0  1.00  1.00  1.00
numbers/terms                           1    1    1  0.50  0.50  0.50
license/IP                              2    0    0  1.00  1.00  1.00
all                                     7    2    2  0.78  0.78  0.78
```

The three `-` rows are true negatives only: absent in the contract, and the model said so.

Now on your E1 run:

```sh
uv run python -m docintel.evals.runner report <E1 run_id>
```

<!-- LIVE OUTPUT: E1 report from the user's own run -->

Your output has 17 score rows and one cost line. Check three things:

1. The `all` row's `tp`, `fp` and `fn` are the same as in your 1c2 E1 check table.
2. No field row shows `-` in all three columns. Every field is present in at least 9 dev
   contracts.
3. The cost line says `52 calls` or a little more. More means a resume sent some calls again.

## Step 3: one chart per field

**Why.** A chart shows the weak fields at a glance. It goes in the README in Phase 5.

Add a new cell to `notebooks/00_explore.ipynb`, with your E1 `run_id`:

```python
import matplotlib.pyplot as plt

from docintel.domain.schema.fields import CUAD_CATEGORY
from docintel.evals.scorers import metrics

RUN = "<E1 run_id>"
rows = [r for r in metrics(con, RUN) if r["name"] in CUAD_CATEGORY]
rows.sort(key=lambda r: r["f1"] or 0)  # weakest field at the bottom
y = list(range(len(rows)))

fig, ax = plt.subplots(figsize=(8, 5.5))
ax.barh([i + 0.17 for i in y], [r["precision"] or 0 for r in rows], height=0.3,
        color="#2a78d6", label="precision")
ax.barh([i - 0.17 for i in y], [r["recall"] or 0 for r in rows], height=0.3,
        color="#eb6834", label="recall")
ax.set_yticks(y, [r["name"] for r in rows])
ax.set_xlim(0, 1)
ax.set_xlabel("score (0 to 1)")
ax.set_title(f"E1: precision and recall per field, run {RUN}", loc="left")
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncols=2, frameon=False)
ax.grid(axis="x", color="#e4e3df")
ax.set_axisbelow(True)
for side in ("top", "right", "left"):
    ax.spines[side].set_visible(False)
ax.tick_params(axis="y", length=0)
fig.tight_layout()
```

*Python here: [matplotlib: `subplots`, `barh`, `ax`](./py/phase-1c3.md#py-3) ·
[`sort(key=lambda ...)`](./py/phase-1c3.md#py-4).*

Here, we:

1. Keep only the 12 field rows, and sort them by F1. `sort` puts the lowest first, and
   `barh` draws the first row at the bottom.
2. Draw two thin bars per field: precision (blue) a little above the center, recall (orange) a
   little below.
3. Put the field names on the left, and fix the scale from 0 to 1, so two charts can be compared.
4. Put the legend under the chart, where no bar can cover it.
5. Keep only light vertical grid lines. The bars carry the data.

An empty precision is drawn as no bar. The `report` table is the place to read exact numbers.

Checkpoint. Run the cell.

<!-- LIVE OUTPUT: describe the E1 chart from the user's own run -->

You see 12 rows of paired bars, weakest field at the bottom, legend under the x axis. Two
patterns to look for:

1. **Long orange, short blue**: high recall, low precision. The model says "found" too often.
2. **Short orange, long blue**: the model is right when it answers, but it misses many.

Write one sentence per pattern you see in a markdown cell.

## Step 4: read the real misses

**Why.** A number says "Renewal Term is weak". Only the text says why.

Add a cell to the notebook. Pick your weakest field from the chart, and its CUAD category:

```python
MISSES = """
SELECT s.doc_id, s.fp, s.fn, s.quote_ok, s.value_ok,
    p.answer->>'$.value' AS model_value, p.answer->>'$.quotes[0]' AS model_quote,
    (SELECT any_value(span_text) FROM labels l
     WHERE l.doc_id = s.doc_id AND l.category = $category AND l.is_present) AS gold_span
FROM scores s JOIN predictions p USING (run_id, doc_id, field)
WHERE s.run_id = $run AND s.field = $field AND s.fp + s.fn > 0
"""
params = {"run": RUN, "field": "renewal_term", "category": "Renewal Term"}
for doc, fp, fn, q_ok, v_ok, value, quote, gold in con.execute(MISSES, params).fetchall():
    print(f"{doc[:50]}  fp={fp} fn={fn} quote_ok={q_ok} value_ok={v_ok} value={value}")
    print("  model:", (quote or "")[:200])
    print("  gold: ", (gold or "")[:200])
```

*Python here: [DuckDB JSON paths: `->>'$.value'`](./py/phase-1c3.md#py-5) ·
[a query inside `SELECT`](./py/phase-1c3.md#py-6).*

Here, we:

1. Keep only the rows of this run and this field with an FP or an FN.
2. Join each score row to its prediction, and take the model's value and first quote out of the
   JSON.
3. Find one gold span for the same contract and category, with a small query inside `SELECT`.
4. Print each miss on three lines: the checks, then the model's quote, then the gold.

Checkpoint. Try it on `1b-example` first. Change `params` to this, and run the cell:

```python
params = {"run": "1b-example", "field": "notice_period_to_terminate_renewal",
          "category": "Notice Period To Terminate Renewal"}
```

```
EcoScienceSolutionsInc_20171117_8-K_EX-10.1_109564  fp=1 fn=1 quote_ok=False value_ok=None value=30 days
  model: unless either party provides a thirty-day notice of written termination one to the other
  gold:  The term of this Agreement shall be for one (1) year commencing on the Effective Date and automatically renewing annually thereafter, unless either party provides a thirty-day notice of written termin
```

This is Round 1. `value_ok` is `None` because this field uses the quote rule. The model's quote
is inside the gold span: right answer, rule too strict. Now set `params` back to your E1 run
and your weakest field.

<!-- LIVE OUTPUT: misses for the user's weakest field -->

For each miss, sort it into one of these:

| Kind | Sign in the output | Whose fault |
|---|---|---|
| Missed | `fn=1`, `fp=0`, no quote | model (or prompt) |
| Wrong answer | `fp=1 fn=1`, the quote is about something else | model |
| Right, but too short or long | `fp=1 fn=1`, the quote is inside the gold span, or the other way round | scoring rule |
| Found, lawyer did not | `fp=1 fn=0`, gold is `None` | model, or a CUAD label is missing |

Write in a markdown cell: one real FP and one real FN from E1, with their kind. Then a guess:
why is this field weak? This is the Phase 1 learning checkpoint.

## Step 5: a test for the rules that must never break

**Why.** Every later comparison reads `metrics`. Two things must stay true: the scores for the
edge cases, and groups that add up their fields' counts. (That every field is in a group is
already checked by the 1a test in `test_schema.py`.)

Put this in `tests/test_metrics.py`:

```python
"""P/R/F1 and the group sums. No network, no CUAD files."""

import pytest

from docintel.domain.schema.fields import CUAD_CATEGORY
from docintel.evals.runner import TABLES
from docintel.evals.scorers import metrics, prf
from docintel.evals.store import connect

ROW = "INSERT INTO scores (run_id, doc_id, field, tp, fp, fn) VALUES ('r1', 'd1', ?, ?, 0, ?)"


def test_prf():
    assert prf(8, 2, 8) == {"precision": 0.8, "recall": 0.5, "f1": pytest.approx(16 / 26)}
    assert prf(0, 0, 10) == {"precision": None, "recall": 0.0, "f1": 0.0}  # the lazy model
    assert prf(0, 0, 0) == {"precision": None, "recall": None, "f1": None}  # only TNs


def test_groups_add_up_counts():
    with connect(":memory:") as con:
        con.execute(TABLES)
        for field in CUAD_CATEGORY:
            tp, fn = (1, 1) if field in ("parties", "agreement_date") else (0, 0)
            con.execute(ROW, [field, tp, fn])
        rows = {r["name"]: r for r in metrics(con, "r1")}
    assert len(rows) == 12 + 4 + 1
    assert (rows["basic facts"]["tp"], rows["basic facts"]["fn"]) == (2, 2)
    assert rows["basic facts"]["recall"] == rows["all"]["recall"] == 0.5
    assert rows["cap_on_liability"]["f1"] is None
```

*Python here: [`pytest.approx`](./py/phase-1c3.md#py-7).*

Here, we:

1. Check `prf` on the 1b2 examples: 8 right of 10 answers with 16 present, the lazy model, and
   a field with only true negatives.
2. Build a tiny `scores` table: Parties and Agreement Date each have one TP and one FN, the rest
   is empty. Check the group row and the "all" row add them up, and that an empty field has no
   F1.

Checkpoint:

```sh
make lint && make test
```

```text
All checks passed!
...
tests/test_data_load.py ....                                             [ 11%]
tests/test_extract.py ...                                                [ 20%]
tests/test_llm.py ....                                                   [ 31%]
tests/test_metrics.py ..                                                 [ 37%]
tests/test_runner.py ...                                                 [ 45%]
tests/test_schema.py ....                                                [ 57%]
tests/test_scorers.py .........                                          [ 82%]
tests/test_smoke.py .                                                    [ 85%]
tests/test_splits.py .....                                               [100%]

============================== 35 passed in 0.61s ==============================
```

Your project should now look like this:

```
src/docintel/evals/
├── runner.py                  + COST, fmt, report; the `report` subcommand
└── scorers.py                 + GROUPS, prf, PER_FIELD, metrics
tests/
├── test_metrics.py            2 tests
└── ...
notebooks/00_explore.ipynb     + chart, misses
pyproject.toml, uv.lock        + matplotlib (dev)
```

<details><summary>Full <code>src/docintel/evals/scorers.py</code></summary>

```python
"""Score one contract's extracted fields against the CUAD gold labels. Rules are 1b2 decisions."""

import re

import duckdb

from docintel.domain.schema.fields import CUAD_CATEGORY, ContractFields
from docintel.evals.datasets import FIELDS

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
```
</details>

<details><summary>Full <code>src/docintel/evals/runner.py</code> (after 1c3)</summary>

```python
"""Batch runner: extract every contract of a split, store the answers, score them."""

import argparse
import json
import time
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import duckdb

from docintel.core.config import get_settings
from docintel.core.llm import LLMResult, log_call
from docintel.domain.extract.extract import build_messages, extract
from docintel.domain.schema.fields import ContractFields, Names
from docintel.evals.scorers import metrics, score_doc
from docintel.evals.store import connect

TABLES = """
CREATE TABLE IF NOT EXISTS runs (
    run_id VARCHAR PRIMARY KEY, created_at TIMESTAMP DEFAULT current_timestamp,
    split VARCHAR, parser VARCHAR, model VARCHAR, prompt_version VARCHAR,
    n_docs INTEGER, est_cost_usd DOUBLE
);
CREATE TABLE IF NOT EXISTS predictions (
    run_id VARCHAR, doc_id VARCHAR, field VARCHAR,
    ok BOOLEAN,     -- false: the answer did not fit the schema, so the field is stored empty
    found BOOLEAN,
    answer JSON,    -- the whole field answer (quotes, value, found), so score() can rebuild it
    PRIMARY KEY (run_id, doc_id, field)
);
CREATE TABLE IF NOT EXISTS scores (
    run_id VARCHAR, doc_id VARCHAR, field VARCHAR, rule VARCHAR, gold_present BOOLEAN,
    found BOOLEAN, quote_ok BOOLEAN, value_ok BOOLEAN, tp INTEGER, fp INTEGER, fn INTEGER,
    PRIMARY KEY (run_id, doc_id, field)
);
"""


def docs_for(con: duckdb.DuckDBPyConnection, split: str) -> list[str]:
    """The doc_ids of one split, always in the same order."""
    rows = con.execute("SELECT doc_id FROM splits WHERE split = ? ORDER BY doc_id", [split])
    return [doc_id for (doc_id,) in rows.fetchall()]


def cuad_txt(con: duckdb.DuckDBPyConnection, doc_id: str) -> str:
    """The clean text that CUAD gives for each contract."""
    (path,) = con.execute("SELECT txt_path FROM contracts WHERE doc_id = ?", [doc_id]).fetchone()
    return Path(path).read_text(encoding="utf-8")


PARSERS = {"cuad_txt": cuad_txt}  # 3a adds pypdf, Docling and Qwen3-VL

CHARS_PER_TOKEN = 4.0  # 1b measured about 4.6; a smaller number makes the guess a little high
OUTPUT_TOKENS = 1000  # per contract; the 1b answer used 697


def price(model: str) -> tuple[float, float]:
    """(input, output) price in USD per token, as OpenRouter lists it. No key needed."""
    url = f"{get_settings().openrouter_base_url}/models"
    with urllib.request.urlopen(url, timeout=30) as resp:
        prices = {m["id"]: m["pricing"] for m in json.load(resp)["data"]}
    p = prices[model]  # a KeyError here means the model id is wrong
    return float(p["prompt"]), float(p["completion"])


def estimate(texts: list[str], model: str, prompt_version: str) -> float:
    """A rough cost in USD for these contracts, before any call is made."""
    in_price, out_price = price(model)
    chars = sum(len(m["content"]) for t in texts for m in build_messages(t, prompt_version))
    return chars / CHARS_PER_TOKEN * in_price + len(texts) * OUTPUT_TOKENS * out_price


def empty_answer(field: str) -> dict:
    """The "not found" answer for one field: no quotes, and an empty value if it has one."""
    model = ContractFields.model_fields[field].annotation
    answer = {"quotes": [], "found": False}
    if "value" in model.model_fields:
        answer["value"] = [] if model is Names else None
    return answer


def to_rows(run_id: str, doc_id: str, result: LLMResult[ContractFields]) -> list[tuple]:
    """12 rows for one contract. An answer that failed the schema gives 12 empty fields."""
    ok = result.parsed is not None
    rows = []
    for field in ContractFields.model_fields:
        answer = getattr(result.parsed, field).model_dump() if ok else empty_answer(field)
        rows.append((run_id, doc_id, field, ok, answer["found"], json.dumps(answer)))
    return rows


def from_rows(rows: list[tuple[str, str]]) -> ContractFields:
    """Rebuild one contract's answer from its (field, answer JSON) rows."""
    return ContractFields.model_validate({field: json.loads(answer) for field, answer in rows})


SCORE_ROW = (
    "INSERT INTO scores VALUES ($run_id, $doc_id, $field, $rule, $gold_present, $found, "
    "$quote_ok, $value_ok, $tp, $fp, $fn)"
)


def score(con: duckdb.DuckDBPyConnection, run_id: str) -> int:
    """(Re)score one run from its stored predictions. No LLM call. Returns the number of docs."""
    rows = con.execute(
        "SELECT doc_id, field, answer FROM predictions WHERE run_id = ?", [run_id]
    ).fetchall()
    by_doc = defaultdict(list)
    for doc_id, field, answer in rows:
        by_doc[doc_id].append((field, answer))
    con.execute("DELETE FROM scores WHERE run_id = ?", [run_id])
    for doc_id, fields in by_doc.items():
        scored = score_doc(con, doc_id, from_rows(fields))
        con.executemany(SCORE_ROW, [{"run_id": run_id, "doc_id": doc_id, **r} for r in scored])
    return len(by_doc)


def todo(con: duckdb.DuckDBPyConnection, run_id: str, doc_ids: list[str]) -> list[str]:
    """The docs of this run with no predictions yet. This is what makes resume work."""
    rows = con.execute("SELECT DISTINCT doc_id FROM predictions WHERE run_id = ?", [run_id])
    done = {doc_id for (doc_id,) in rows.fetchall()}
    return [doc_id for doc_id in doc_ids if doc_id not in done]


def run_docs(
    con: duckdb.DuckDBPyConnection,
    run_id: str,
    texts: dict[str, str],
    model: str,
    prompt_version: str,
    concurrency: int,
) -> int:
    """Extract many contracts at the same time. Returns how many calls failed.

    Only the worker threads call the LLM. Only this thread writes to DuckDB.
    """
    pool = ThreadPoolExecutor(max_workers=concurrency)
    futures = {
        pool.submit(extract, text, model, prompt_version=prompt_version): doc_id
        for doc_id, text in texts.items()
    }
    failed = 0
    try:
        for i, future in enumerate(as_completed(futures), start=1):
            doc_id = futures[future]
            try:
                result = future.result()
            except Exception as e:  # still failing after the retries, or a 400 error
                failed += 1
                print(f"[{i}/{len(futures)}] {doc_id[:40]}  FAILED {type(e).__name__}: {e}")
                continue
            log_call(con, result, "ContractFields", run_id)
            con.executemany(
                "INSERT INTO predictions VALUES (?, ?, ?, ?, ?, ?)",
                to_rows(run_id, doc_id, result),
            )
            print(
                f"[{i}/{len(futures)}] {doc_id[:40]}  ok={result.parsed is not None}"
                f"  ${result.cost_usd or 0:.4f}  {result.latency_ms / 1000:.1f} s"
            )
    finally:
        pool.shutdown(cancel_futures=True)  # on Ctrl-C: drop the calls that have not started
    return failed


COST = """
SELECT count(*), sum(cost_usd), quantile_cont(latency_ms, 0.5) / 1000,
    quantile_cont(latency_ms, 0.95) / 1000, count(*) FILTER (WHERE NOT ok)
FROM llm_calls WHERE run_id = ?
"""


def fmt(x: float | None) -> str:
    return "-" if x is None else f"{x:.2f}"


def report(con: duckdb.DuckDBPyConnection, run_id: str) -> None:
    """Print P/R/F1 per field, per group and for all fields, then cost and latency."""
    print(f"{'':36} {'tp':>4} {'fp':>4} {'fn':>4} {'P':>5} {'R':>5} {'F1':>5}")
    for r in metrics(con, run_id):
        scores = f"{fmt(r['precision']):>5} {fmt(r['recall']):>5} {fmt(r['f1']):>5}"
        print(f"{r['name']:36} {r['tp']:4} {r['fp']:4} {r['fn']:4} {scores}")
    calls, cost, p50, p95, bad = con.execute(COST, [run_id]).fetchone()
    if calls:  # the 1b-example run has scores but no logged calls
        print(f"{calls} calls, ${cost:.4f}, p50 {p50:.1f} s, p95 {p95:.1f} s, {bad} bad answers")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="python -m docintel.evals.runner")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="extract every doc of a split, then score the run")
    run.add_argument("--split", choices=["dev", "test"], default="dev")
    run.add_argument("--parser", choices=list(PARSERS), default="cuad_txt")
    run.add_argument("--model", help="OpenRouter model id (default: DOCINTEL_MODEL)")
    run.add_argument("--prompt-version", default="v1")
    run.add_argument("--limit", type=int, help="only the first N docs: a cheap pilot run")
    run.add_argument("--concurrency", type=int, default=8, help="calls at the same time")
    run.add_argument("--resume", metavar="RUN_ID", help="finish a run that was stopped")
    run.add_argument("--yes", action="store_true", help="do not ask before spending money")
    rescore = sub.add_parser("score", help="score a stored run again (no LLM calls)")
    rescore.add_argument("run_id")
    show = sub.add_parser("report", help="print P/R per field and group, cost and latency")
    show.add_argument("run_id")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    with connect() as con:
        con.execute(TABLES)
        if args.command == "score":
            print(f"scored {score(con, args.run_id)} docs for run {args.run_id}")
            return
        if args.command == "report":
            report(con, args.run_id)
            return
        if args.resume:
            run_id = args.resume
            split, parser, model, version, n_docs = con.execute(
                "SELECT split, parser, model, prompt_version, n_docs FROM runs WHERE run_id = ?",
                [run_id],
            ).fetchone()
        else:
            run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
            split, parser, version = args.split, args.parser, args.prompt_version
            model = args.model or get_settings().docintel_model
            n_docs = len(docs_for(con, split)[: args.limit])
        doc_ids = todo(con, run_id, docs_for(con, split)[:n_docs])
        texts = {doc_id: PARSERS[parser](con, doc_id) for doc_id in doc_ids}
        cost = estimate(list(texts.values()), model, version)
        print(f"run {run_id}: {len(texts)} of {n_docs} docs to do, {model}, about ${cost:.4f}")
        if texts and not args.yes and input("Start? [y/N] ").strip().lower() != "y":
            return
        if not args.resume:
            con.execute(
                "INSERT INTO runs (run_id, split, parser, model, prompt_version, n_docs, "
                "est_cost_usd) VALUES (?, ?, ?, ?, ?, ?, ?)",
                [run_id, split, parser, model, version, n_docs, cost],
            )
        start = time.perf_counter()
        failed = run_docs(con, run_id, texts, model, version, args.concurrency)
        wall_s = time.perf_counter() - start
        n = score(con, run_id)
        print(f"done in {wall_s:.0f} s: {n} of {n_docs} docs scored, {failed} calls failed")
        if n < n_docs:
            print(f"finish it with: --resume {run_id}")


if __name__ == "__main__":
    main()
```
</details>

## Break it on purpose

**Break 1: a copy-paste bug.** In `metrics`, change the `fn` line to
`fn = sum(counts[f][1] for f in fields)`: index 1 instead of 2. Guess which test fails:

```
E       assert (2, 0) == (2, 2)
E         At index 1 diff: 0 != 2
FAILED tests/test_metrics.py::test_groups_add_up_counts - assert (2, 0) == (2...
========================= 1 failed, 34 passed in 0.68s =========================
```

Every FN would be read from the FP column. Recall would be wrong for every field, and nothing
would crash. Change it back.

**Break 2: no F1 without a TP.** In `prf`, change the F1 line to
`"f1": 2 * tp / (2 * tp + fp + fn) if tp else None,`. Guess what happens to the lazy model:

```
E       AssertionError: assert {'precision':...0, 'f1': None} == {'precision':....0, 'f1': 0.0}
E         Differing items:
E         {'f1': None} != {'f1': 0.0}
FAILED tests/test_metrics.py::test_prf - AssertionError: assert {'precision':...
========================= 1 failed, 34 passed in 0.63s =========================
```

The lazy model's F1 would be empty, not 0. The chart would show no bar, and the field would
look "not measured" instead of "never found". Change it back.

## Experiment

This part finishes E1. There is no new run: everything comes from your E1 `run_id`. Finish the
E1 entry in `EXPERIMENTS.md`:

- **Results:** paste the `report` table and the cost line. Add the chart from Step 3.
- **Conclusion:** the 2 strongest and the 2 weakest fields. For each weak one, say "model" or
  "rule", with one real miss from Step 4.
- **Next step:** E1.1 (other models, 1c4), then 2a (validators and citations).

## Gotchas

- **Never change a rule and compare with an old score.** After a rule change, run
  `score RUN_ID` for every run you compare, so all rows use the same rules.
- **Small numbers are noisy.** 9 contracts with Notice Period means one contract moves its
  recall by 0.11. Do not draw big conclusions from one rare field.
- **A `KeyError` in `metrics`.** The run has no scores for some field. Run `score RUN_ID` again.
- **The chart cell fails with `No module named 'matplotlib'`.** Restart the notebook kernel after
  `uv add`, so it sees the new library.

## Explain back, then commit

Explain each changed file to Claude in a few sentences (the rule in `PLAN.md`): `scorers.py`
(`GROUPS`, `prf`, `metrics` and your two decisions), `runner.py` (`report`), `test_metrics.py`
(each test), the notebook (the chart, one real FP and one real FN), and the E1 entry. Then:

```sh
git status
git add src/docintel/evals/scorers.py src/docintel/evals/runner.py tests/test_metrics.py pyproject.toml uv.lock notebooks/00_explore.ipynb EXPERIMENTS.md
git commit -m "phase 1c3: per-field metrics, report command, E1 results"
```

## Conclusion

What you have now:

- Precision, recall and F1 per field, per group and overall, from any `run_id`.
- A chart and real misses that explain the weakest field.
- E1, the baseline every later part compares with.

Go back to the objectives. Check that you can do each one without notes. Then answer:

1. A field has precision 0.95 and recall 0.40. What does the model do wrong, and what would a
   lawyer feel?
2. Why is a quote that is inside the gold span still scored as FP and FN?

Want more practice? Try these (optional):

1. Add a macro F1 column to `report`, and compare it with the micro "all" row.
2. Copy E1's predictions to a new run with SQL:
   `INSERT INTO predictions SELECT 'e1-t04', doc_id, field, ok, found, answer FROM predictions
   WHERE run_id = '<E1 run_id>'`. Set `THRESHOLD = 0.4`, run `score e1-t04`, then
   `report e1-t04`. How many misses turn into TPs? Put `THRESHOLD` back afterwards. E1 itself
   stays untouched.
3. Draw the same chart for the 4 groups.

Checklist (`../PLAN.md`): **Precision/recall/F1 per field; span scoring** (done: per field, per
group, with real misses).
