# Phase 2b2: trust experiments

In this part, you build a small replay tool for the last question in the README: did validation and
retries help? Then you choose what happens to a field that still has an error, before any paid run.
Each step ends with a checkpoint. Nothing here costs money.

This is part 2 of 3 for Phase 2b. Part 1 (2b) built the retry loop. Part 3 (2b3) makes one dev run with
`--retries 2`, after a keep rule for retries, and logs E2.1 to E2.3.

## Words used in this part

Read these first. Error, warning, issue and replay are from 2a. Attempt and merge are from 2b.

- **First answer**: attempt 0 for a contract, before any retry. Example: the answer in `attempts` with
  `attempt_no = 0`.
- **Final answer**: the merged answer after the retries. It is what `predictions` stores.
- **Validation error**: an error about the shape of an answer. Example: `found_no_value`.
- **Citation error**: a quote that is not in the contract. The rule is `quote_missing`.
- **Policy**: what to do with a field that still has an error. "Keep and flag" keeps it with a
  needs-review flag. "Blank" sets it to "not found".
- **Derived run**: a run made from answers that are already stored, with no LLM call. Example:
  `<run_id>-first` holds the first answers of a retry run.
- **TP lost**: a field that was a TP before the change, and is not a TP after it.

## Objectives

By the end of this part you should be able to:

1. Explain why the "before" comes from the same run as the "after".
2. Rebuild the first answers of a retry run, and store them as a normal run.
3. Show with real rows why blanking a failed field can lose a right answer.
4. Choose what happens to a field that still has an error, from evidence, before the run.
5. Test that a replay can run twice and never reads the final answer as the "before".

## Dependencies

You install nothing new. This part needs:

- 2a and 2a2: `validate` and the `issues` table.
- 2b: `--retries`, the `attempts` table, and `final_answer`.
- Your 2b pilot run (`20261107-222125` here). It has attempt rows.

## The big picture

Before this part, the trust layer exists, but nobody has measured it on a new run.

After this part:

```text
one dev run, --retries 2
   |-- attempt 0 of each contract -> <run_id>-first            (the "before")
   |                                   |-- blank errors -> <run_id>-first-blank-v, -first-blank-vc
   |-- final answers (predictions) -> <run_id>                 (the "after")
                                       |-- blank errors -> <run_id>-blank-v, -blank-vc
```

- **2b3** runs this on a new dev run. E2.1 compares `-first` with `-first-blank-v`. E2.2 compares
  `-first` with `-first-blank-vc`. E2.3 compares first with final, under your policy.
- **Phase 3** runs the same tool on worse text. **Phase 5** uses the numbers in the write-up.

## Remember this

> Measure every change against the same first answers. One run gives both: attempt 0 is the "before",
> and the merged answer is the "after". So the provider and the luck of the run are the same on both
> sides. On clean text, the honest result may be "it barely matters", and that is still a result.
>
> **Same first answers, one change at a time.**

## Why

**The README asks it.** Question 4 is "Schema validation: what broke, what we caught, and did retries
help?" You need numbers with a `run_id` to answer it.

**Two runs would hide the effect.** At temperature 0, two v1 runs still differ by 0.012 F1 (E1.3). A
retry fixes a few fields. That is about 0.003. A second run would add more noise than the retry adds.

**Blanking looks safe, but is not free.** A field with an error is often still right. Blanking it turns
a TP into an FN. Only a replay can show how often.

## Design decisions

- **The "before" is attempt 0 of the retry run.** `attempts.raw_text` has every first answer. Other
  option: a second run with `--retries 0`. That adds run noise (0.012) to a tiny effect.
- **Derived runs are normal runs.** They have rows in `runs`, `predictions`, `scores` and `issues`.
  So `report`, `validate` and the `gap` cell work on them with no new code. Other option: compute the
  numbers in memory. Then no number traces to a `run_id`.
- **The name shows the parent.** `<run_id>-first-blank-v`. Other option: a new `parent` column.
- **The tool builds every policy.** You choose from the table, so a choice is never hidden in code.
  Other option: one setting for the policy. Then you would need one run of the tool per choice.
- **`trust.py` has its own command.** It imports `runner.py`. If `runner.py` imported it back, Python
  would hit a circular import. Other option: put it all in `runner.py`, which is already long.
- **`to_rows` takes the answer, not the `LLMResult`.** Derived runs have no `LLMResult`. One row
  builder for both kinds of run means they cannot drift apart.

## Worked example

Real answers from the Parasail v1 run `20261105-213036` (E1.3). Guess before you open each box.

### Round 1: blank a validation error

Pareteum, `renewal_term`, marked TP:

`If no termination notice is provided, the Agreement will be automatically extended for consecutive ***
periods until such time as *** termination notice is provided.`

It has `found` true and `value` null, so `found_no_value` fires. The policy is "blank". What happens to
the score?

<details><summary>Guess, then open</summary>

The field becomes "not found". The clause is in the contract, so the TP becomes an FN. Blanking fixed
the error and lost a right answer. On this run, blanking all 4 validation errors removes 2 FPs and loses
this 1 TP. F1 goes from 0.9071 to 0.9082.
</details>

### Round 2: blank a citation error

Coral Gold, `anti_assignment`, marked TP:

`Neither this Agreement nor any of the rights of any of the parties under this Agreement shall be
assigned without the written consent of all the parties.`

The contract says `thewritten`, so `quote_missing` fires. The policy now also blanks citation errors.
Guess the effect on the run.

<details><summary>Guess, then open</summary>

Both citation errors on this run are TPs: Coral Gold, and Upjohn `cap_on_liability`. Each quote "fixed"
broken text in the contract. Blanking them loses 2 more TPs. F1 drops to 0.9047, below the first answers.
The citation check found no made-up quotes here. It found right answers with a small copy error.
</details>

## Project setup

```sh
touch src/docintel/evals/trust.py tests/test_trust.py
```

You should now have:

```text
src/docintel/evals/
├── runner.py          + to_rows takes the answer
├── scorers.py
├── store.py
└── trust.py           new: first answers, blanking, derived runs, report
tests/
├── test_runner.py     + two to_rows calls
└── test_trust.py      new
```

## Step 1: one row builder

**Why.** Derived runs must store answers the same way as real runs.

Update `to_rows` in `src/docintel/evals/runner.py`:

```python
def to_rows(run_id: str, doc_id: str, pred: ContractFields | None) -> list[tuple]:
    """12 rows for one contract. None (the answer failed the schema) gives 12 empty fields."""
    ok = pred is not None
    rows = []
    for field in ContractFields.model_fields:
        answer = getattr(pred, field).model_dump() if ok else empty_answer(field)
        rows.append((run_id, doc_id, field, ok, answer["found"], json.dumps(answer)))
    return rows
```

Then in `run_docs`, the final answer no longer needs `replace`:

```python
            final = final_answer(attempts)
            con.executemany(
                "INSERT INTO predictions VALUES (?, ?, ?, ?, ?, ?)", to_rows(run_id, doc_id, final)
            )
```

And in the `print` below it, use `ok={final is not None}`.

Here, we:

1. Pass the answer itself. `None` still means "did not fit the schema".
2. Remove `from dataclasses import replace` and `LLMResult` from the imports. Nothing uses them now.
3. In `tests/test_runner.py`, change `result(PRED)` to `PRED` and `result(None)` to `None` in the two
   `to_rows` calls. Keep `result()`: the resume test still uses it.

Checkpoint:

```sh
make lint
make test
```

```text
uv run ruff check .
All checks passed!
uv run ruff format --check .
43 files already formatted
uv run pytest
...
72 passed in 3.24s
```

## Step 2: first and final answers

**Why.** E2.1 to E2.3 all start from the first answers. They are only in `attempts.raw_text`.

Put this in `src/docintel/evals/trust.py`:

```python
"""Trust experiments: first and final answers of one retry run, with and without blanking."""

import argparse
from collections import defaultdict

import duckdb

from docintel.core.llm import _parse
from docintel.domain.schema.fields import ContractFields
from docintel.evals.runner import TABLES, empty_answer, from_rows, score, to_rows, validate
from docintel.evals.scorers import metrics
from docintel.evals.store import connect

Answers = dict[str, ContractFields | None]  # doc_id -> answer; None: it did not fit the schema


def first_answers(con: duckdb.DuckDBPyConnection, run_id: str) -> Answers:
    """Attempt 0 of each contract, read again from its raw text: the answer before any retry."""
    rows = con.execute(
        "SELECT doc_id, raw_text FROM attempts WHERE run_id = ? AND attempt_no = 0", [run_id]
    ).fetchall()
    return {doc_id: _parse(ContractFields, raw_text)[0] for doc_id, raw_text in rows}


def stored_answers(con: duckdb.DuckDBPyConnection, run_id: str) -> Answers:
    """The stored answer of each contract. For a retry run, this is the final answer."""
    rows = con.execute(
        "SELECT doc_id, field, ok, answer FROM predictions WHERE run_id = ?", [run_id]
    ).fetchall()
    by_doc = defaultdict(list)
    for doc_id, field, ok, answer in rows:
        by_doc[doc_id].append((field, ok, answer))
    return {
        doc_id: from_rows([(f, a) for f, _, a in fields])
        if all(ok for _, ok, _ in fields)
        else None
        for doc_id, fields in by_doc.items()
    }
```

*Python here: [a type alias](./py/phase-2b2.md#py-1) · [`_parse` and the leading `_`](./py/phase-2b2.md#py-2)
· [`if ... else` inside a comprehension](./py/phase-2b2.md#py-3).*

Here, we:

1. Read attempt 0 of each contract and parse it with `_parse`. That is the same parse the live call
   used, so a bad schema gives `None` again.
2. Read the final answers from `predictions`. The grouping is the same as in `validate` (2a2).
3. Name the shape once: `Answers`. Every function below takes or returns it.

Some imports (`argparse`, `score`, `to_rows`, ...) are used only in Step 4. Until then, `make lint`
says they are unused. That is expected.

Checkpoint. Use your 2b pilot (it has `--retries 0`, so first and final must match). Close the notebook
first:

```sh
uv run python - <<'EOF'
from docintel.evals.store import connect
from docintel.evals.trust import first_answers, stored_answers

RUN = "20261107-222125"  # your 2b pilot
with connect() as con:
    first, final = first_answers(con, RUN), stored_answers(con, RUN)
print(len(first), len(final), first == final)
EOF
```

```text
3 3 True
```

## Step 3: blank a field

**Why.** E2.1 and E2.2 need the same answers with the failed fields set to "not found".

Add under the imports in `src/docintel/evals/trust.py`, above `Answers`:

```python
VALIDATION = {"found_no_quote", "quote_not_found", "found_no_value", "value_not_found", "bad_date"}
CITATION = {"quote_missing"}
BLANK = {"blank-v": VALIDATION, "blank-vc": VALIDATION | CITATION}  # policy -> rules
```

Add to the bottom of the same file:

```python
def blank(answer: ContractFields, fields: set[str]) -> ContractFields:
    """The same answer, with these fields set to "not found"."""
    return ContractFields.model_validate(answer.model_dump() | {f: empty_answer(f) for f in fields})


def blanked(
    con: duckdb.DuckDBPyConnection, run_id: str, answers: Answers, rules: set[str]
) -> Answers:
    """Blank each field that has an error from `rules` in the stored issues of `run_id`."""
    rows = con.execute(
        "SELECT doc_id, field, rule FROM issues WHERE run_id = ? AND severity = 'error'", [run_id]
    ).fetchall()
    broken = defaultdict(set)
    for doc_id, field, rule in rows:
        if rule in rules:
            broken[doc_id].add(field)
    return {
        doc_id: blank(answer, broken[doc_id]) if answer and broken[doc_id] else answer
        for doc_id, answer in answers.items()
    }
```

*Python here: [`model_dump() | {...}` then `model_validate`](./py/phase-2b2.md#py-4) ·
[`defaultdict(set)`](./py/phase-2b2.md#py-5).*

Here, we:

1. Split the 2a error rules in two. `bad_schema` is in neither: its fields are already empty.
2. `blank` dumps the answer to a dict, puts the empty answer over some fields, and checks it again with
   Pydantic. The old answer does not change.
3. `blanked` reads the stored errors of a run. It blanks a field only if one of its errors is in
   `rules`.
4. The issues must belong to the same answers. For first answers, use the issues of `<run_id>-first`.

Checkpoint. The Parasail v1 run from E1.3 already has its issues. Nothing is written:

```sh
uv run python - <<'EOF'
from docintel.domain.schema.fields import ContractFields
from docintel.evals.store import connect
from docintel.evals.trust import CITATION, VALIDATION, blanked, stored_answers

RUN = "20261105-213036"  # Parasail v1, from E1.3
with connect() as con:
    answers = stored_answers(con, RUN)
    for name, rules in [("validation", VALIDATION), ("validation + citation", VALIDATION | CITATION)]:
        new = blanked(con, RUN, answers, rules)
        changed = [
            (doc_id[:16], field)
            for doc_id in answers
            for field in ContractFields.model_fields
            if getattr(answers[doc_id], field) != getattr(new[doc_id], field)
        ]
        print(f"{name}: {sorted(changed)}")
EOF
```

```text
validation: [('NUVEEN - REMARKE', 'agreement_date'), ('OLDAPIWIND-DOWNL', 'parties'), ('PareteumCorp_200', 'notice_period_to_terminate_renewal'), ('PareteumCorp_200', 'renewal_term')]
validation + citation: [('CORALGOLDRESOURC', 'anti_assignment'), ('NUVEEN - REMARKE', 'agreement_date'), ('OLDAPIWIND-DOWNL', 'parties'), ('PareteumCorp_200', 'notice_period_to_terminate_renewal'), ('PareteumCorp_200', 'renewal_term'), ('UpjohnInc_202001', 'cap_on_liability')]
```

These are the 6 error fields of E1.3's Parasail run. Round 1 and Round 2 are two of them.

## Step 4: derived runs and the report

**Why.** Every number in E2.1 to E2.3 must trace to a `run_id`.

Add to the bottom of `src/docintel/evals/trust.py`:

```python
def derive(con: duckdb.DuckDBPyConnection, parent: str, name: str, answers: Answers) -> str:
    """Store answers as a normal run named `<parent>-<name>`, then score and check it. No LLM."""
    run_id = f"{parent}-{name}"
    con.execute("DELETE FROM runs WHERE run_id = ?", [run_id])  # so it can run again
    con.execute("DELETE FROM predictions WHERE run_id = ?", [run_id])
    con.execute(
        "INSERT INTO runs (run_id, split, parser, model, prompt_version, n_docs, est_cost_usd, "
        "max_retries) SELECT ?, split, parser, model, prompt_version, n_docs, 0, max_retries "
        "FROM runs WHERE run_id = ?",
        [run_id, parent],
    )
    for doc_id, answer in answers.items():
        con.executemany(
            "INSERT INTO predictions VALUES (?, ?, ?, ?, ?, ?)", to_rows(run_id, doc_id, answer)
        )
    score(con, run_id)
    validate(con, run_id)
    return run_id


def build(con: duckdb.DuckDBPyConnection, run_id: str) -> dict[str, tuple[str, str]]:
    """Policy -> (first run, final run). The retry run itself is the final run for "keep"."""
    first, final = first_answers(con, run_id), stored_answers(con, run_id)
    first_run = derive(con, run_id, "first", first)
    runs = {"keep": (first_run, run_id)}
    for policy, rules in BLANK.items():
        runs[policy] = (
            derive(con, run_id, f"first-{policy}", blanked(con, first_run, first, rules)),
            derive(con, run_id, policy, blanked(con, run_id, final, rules)),
        )
    return runs
```

*Python here: [`INSERT ... SELECT`](./py/phase-2b2.md#py-6).*

Here, we:

1. `derive` deletes the old rows first. So the tool can run twice on the same run.
2. It copies the parent's `runs` row with a new `run_id` and a cost of 0. No call was made.
3. It stores the answers with `to_rows`, then calls `score` and `validate`. `scores` and `issues` delete
   their own old rows.
4. `build` makes `-first` first. The first-answer blanking needs its issues.
5. It returns a pair per policy: the first run and the final run. For "keep", the final run is the
   retry run itself.

Now the report. Add to the bottom of the same file:

```python
CHANGED = """
WITH a AS (SELECT doc_id, field, answer::VARCHAR AS answer, tp
           FROM predictions JOIN scores USING (run_id, doc_id, field) WHERE run_id = $a),
b AS (SELECT doc_id, field, answer::VARCHAR AS answer, tp
      FROM predictions JOIN scores USING (run_id, doc_id, field) WHERE run_id = $b)
SELECT count(*) FILTER (WHERE a.answer <> b.answer),
    count(*) FILTER (WHERE a.tp > 0 AND b.tp = 0),
    count(*) FILTER (WHERE a.tp = 0 AND b.tp > 0)
FROM a JOIN b USING (doc_id, field)
"""
ERRORS = """
SELECT count(DISTINCT (doc_id, field)) FILTER (WHERE rule IN $v),
    count(DISTINCT (doc_id, field)) FILTER (WHERE rule IN $c)
FROM issues WHERE run_id = $run_id AND severity = 'error'
"""
RETRIES = """
SELECT count(DISTINCT doc_id), count(DISTINCT doc_id) FILTER (WHERE attempt_no > 0),
    count(*) FILTER (WHERE attempt_no > 0), count(*) FILTER (WHERE fixed),
    sum(cost_usd) FILTER (WHERE attempt_no = 0),
    coalesce(sum(cost_usd) FILTER (WHERE attempt_no > 0), 0)
FROM attempts WHERE run_id = ?
"""
```

*Python here: [`answer::VARCHAR` and `IN $v`](./py/phase-2b2.md#py-7) ·
[`FILTER`](./py/phase-0c.md#py-4).*

Here, each query answers one question:

1. `CHANGED`: between two runs, how many fields changed, how many TPs were lost, and how many were
   gained. It compares the stored JSON as text.
2. `ERRORS`: how many fields have a validation error, and how many have a citation error.
3. `RETRIES`: how many contracts got a retry, how many retries, how many fixed every error, and what
   attempt 0 and the retries cost.

Add the last two functions to the bottom of the same file:

```python
def report(con: duckdb.DuckDBPyConnection, run_id: str, runs: dict[str, tuple[str, str]]) -> None:
    """Print first against final answers for each policy, then the errors and the retry cost."""
    print(
        f"{'':10} {'first: P':>8} {'R':>5} {'F1':>5}  {'final: P':>8} {'R':>5} {'F1':>5}"
        f"  {'changed':>7} {'lost':>4} {'gained':>6}"
    )
    for policy, (first, final) in runs.items():
        a, b = metrics(con, first)[-1], metrics(con, final)[-1]  # the last row is all fields
        changed, lost, gained = con.execute(CHANGED, {"a": first, "b": final}).fetchone()
        print(
            f"{policy:10} {a['precision']:8.3f} {a['recall']:5.3f} {a['f1']:5.3f}"
            f"  {b['precision']:8.3f} {b['recall']:5.3f} {b['f1']:5.3f}"
            f"  {changed:7} {lost:4} {gained:6}"
        )
    first, final = runs["keep"]
    sets = {"v": list(VALIDATION), "c": list(CITATION)}
    v0, c0 = con.execute(ERRORS, sets | {"run_id": first}).fetchone()
    v1, c1 = con.execute(ERRORS, sets | {"run_id": final}).fetchone()
    print(f"error fields: validation {v0} -> {v1}, citation {c0} -> {c1}")
    docs, retried, retries, fixed, cost0, cost1 = con.execute(RETRIES, [run_id]).fetchone()
    print(f"retries: {retried} of {docs} contracts, {retries} calls, {fixed} fixed")
    print(
        f"cost: first answers ${cost0:.4f}, retries ${cost1:.4f} ({cost1 / cost0:.0%}),"
        f" ${(cost0 + cost1) / docs:.4f} per contract"
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m docintel.evals.trust")
    parser.add_argument("run_id", help="a run made with --retries")
    args = parser.parse_args(argv)
    with connect() as con:
        con.execute(TABLES)
        runs = build(con, args.run_id)
        report(con, args.run_id, runs)


if __name__ == "__main__":
    main()
```

*Python here: [format specs like `:>8` and `:.0%`](./py/phase-2b2.md#py-8).*

Here, we:

1. Print one row per policy. The left half is the first answers, and the right half is the final
   answers, both under that policy.
2. `changed`, `lost` and `gained` compare the two halves of that row. So they measure only the retries.
3. Print the error fields before and after the retries, and the retry cost.

Checkpoint. Run it on the pilot. It has no retries and no errors, so every row must be the same:

```sh
uv run python -m docintel.evals.trust 20261107-222125
```

```text
           first: P     R    F1  final: P     R    F1  changed lost gained
keep          0.958 0.920 0.939     0.958 0.920 0.939        0    0      0
blank-v       0.958 0.920 0.939     0.958 0.920 0.939        0    0      0
blank-vc      0.958 0.920 0.939     0.958 0.920 0.939        0    0      0
error fields: validation 0 -> 0, citation 0 -> 0
retries: 0 of 3 contracts, 0 calls, 0 fixed
cost: first answers $0.0086, retries $0.0000 (0%), $0.0029 per contract
```

Run it a second time. It must print the same, with no error.

## Step 5: what to do with a failed field (your decision)

**Why.** After the retries, some fields still have errors. The product must do something with them.

Decide this before the run. Write it in your notebook, with one line that says what result would
change your mind.

The options:

| Option | Validation errors | Citation errors | Row in the report |
|---|---|---|---|
| A. Keep and flag | keep, needs review | keep, needs review | `keep` |
| B. Blank validation | blank | keep, needs review | `blank-v` |
| C. Blank both | blank | blank | `blank-vc` |

The evidence (first answers, no retries, all from stored runs):

| Run | A: F1 (tp/fp/fn) | B | C |
|---|---|---|---|
| kept Crusoe `20261102-200003` | 0.9119 (290/36/20) | 0.9131 (289/34/21) | 0.9131 (no citation errors) |
| Parasail v1 `20261105-213036` | 0.9071 (283/31/27) | 0.9082 (282/29/28) | 0.9047 (280/29/30) |

Questions to think about:

1. B raises F1 by about 0.001 on both runs. Is that more than the noise (0.012)?
2. The TP that B loses is a real clause with a hidden value (Round 1). Would a lawyer rather see it
   flagged, or not at all?
3. C loses 2 right answers and catches no made-up quotes. When would C be the right choice?

<details><summary>Reference choice (open after you decide)</summary>

**A, keep and flag.**

1. B's gain (0.001) is far inside the noise. It is not a reason.
2. Every field B or C blanked that was a TP is a real clause. A blank hides it. A flag sends it to a
   person, which is what the needs-review flag is for.
3. C would be right if the citation check caught made-up quotes. On clean text, it caught copy errors.

What would change it: "Blank a kind of error only if, on the first answers, it lifts F1 by more than
0.012 and loses no TP." Phase 3 has worse text. There, made-up quotes may be common, and C may pass.
</details>

## Step 6: tests

**Why.** Three things must never break without a sound: the "before" is attempt 0, blanking touches
only the named fields, and `derive` can run again.

<details><summary>Put this in <code>tests/test_trust.py</code></summary>

```python
"""Trust replays with a tiny in-memory database. No network, no key, no CUAD files."""

from docintel.domain.schema.fields import ContractFields
from docintel.evals import trust
from docintel.evals.runner import TABLES, empty_answer
from docintel.evals.store import connect

FIELDS = {field: empty_answer(field) for field in ContractFields.model_fields}
FIELDS["governing_law"] = {"quotes": ["laws of Michigan"], "value": "Michigan", "found": True}
FIELDS["renewal_term"] = {"quotes": ["renews for *** years"], "value": None, "found": True}
FIRST = ContractFields.model_validate(FIELDS)
FINAL = trust.blank(FIRST, {"governing_law"})  # any answer that is not FIRST


def test_blank_changes_only_the_named_fields():
    answer = trust.blank(FIRST, {"renewal_term"})
    assert answer.renewal_term.model_dump() == empty_answer("renewal_term")
    assert answer.governing_law == FIRST.governing_law
    assert FIRST.renewal_term.found  # the original does not change


def test_first_answers_read_attempt_0_not_the_final():
    with connect(":memory:") as con:
        con.execute(TABLES)
        rows = [
            ("r1", "d1", 0, FIRST.model_dump_json()),
            ("r1", "d1", 1, FINAL.model_dump_json()),
            ("r1", "d2", 0, '{"parties": '),  # did not fit the schema
        ]
        for run_id, doc_id, attempt_no, raw_text in rows:
            con.execute(
                "INSERT INTO attempts (run_id, doc_id, attempt_no, raw_text) VALUES (?, ?, ?, ?)",
                [run_id, doc_id, attempt_no, raw_text],
            )
        assert trust.first_answers(con, "r1") == {"d1": FIRST, "d2": None}


def test_derive_copies_the_parent_and_can_run_again(monkeypatch):
    monkeypatch.setattr(trust, "score", lambda con, run_id: 0)  # these need CUAD labels and text
    monkeypatch.setattr(trust, "validate", lambda con, run_id: 0)
    with connect(":memory:") as con:
        con.execute(TABLES)
        con.execute(
            "INSERT INTO runs (run_id, split, model, n_docs, est_cost_usd, max_retries) "
            "VALUES ('r1', 'dev', 'fake', 2, 0.1, 2)"
        )
        trust.derive(con, "r1", "first", {"d1": FIRST, "d2": None})
        run_id = trust.derive(con, "r1", "first", {"d1": FIRST, "d2": None})  # again: no error
        run = con.execute(
            "SELECT split, model, est_cost_usd FROM runs WHERE run_id = ?", [run_id]
        ).fetchone()
        (n_rows,) = con.execute(
            "SELECT count(*) FROM predictions WHERE run_id = ?", [run_id]
        ).fetchone()
    assert run_id == "r1-first"
    assert run == ("dev", "fake", 0)
    assert n_rows == 24  # 12 fields for each contract, once
```

</details>

*Python here: [`monkeypatch.setattr`](./py/phase-1c2.md#py-5) ·
[`(n_rows,) = ...`](./py/phase-2b2.md#py-9).*

Here, each test protects one thing:

1. `blank` changes the named field, keeps the others, and leaves the original alone.
2. `first_answers` takes attempt 0, even when attempt 1 exists. A bad raw text gives `None`.
3. `derive` copies the parent's settings, sets the cost to 0, and does not double the rows on a rerun.

Checkpoint:

```sh
make lint
make test
```

```text
uv run ruff check .
All checks passed!
uv run ruff format --check .
45 files already formatted
uv run pytest
...
75 passed in 0.94s
```

Your project structure is now the tree from Project setup.

<details><summary>Full <code>src/docintel/evals/trust.py</code></summary>

```python
"""Trust experiments: first and final answers of one retry run, with and without blanking."""

import argparse
from collections import defaultdict

import duckdb

from docintel.core.llm import _parse
from docintel.domain.schema.fields import ContractFields
from docintel.evals.runner import TABLES, empty_answer, from_rows, score, to_rows, validate
from docintel.evals.scorers import metrics
from docintel.evals.store import connect

VALIDATION = {"found_no_quote", "quote_not_found", "found_no_value", "value_not_found", "bad_date"}
CITATION = {"quote_missing"}
BLANK = {"blank-v": VALIDATION, "blank-vc": VALIDATION | CITATION}  # policy -> rules

Answers = dict[str, ContractFields | None]  # doc_id -> answer; None: it did not fit the schema


def first_answers(con: duckdb.DuckDBPyConnection, run_id: str) -> Answers:
    """Attempt 0 of each contract, read again from its raw text: the answer before any retry."""
    rows = con.execute(
        "SELECT doc_id, raw_text FROM attempts WHERE run_id = ? AND attempt_no = 0", [run_id]
    ).fetchall()
    return {doc_id: _parse(ContractFields, raw_text)[0] for doc_id, raw_text in rows}


def stored_answers(con: duckdb.DuckDBPyConnection, run_id: str) -> Answers:
    """The stored answer of each contract. For a retry run, this is the final answer."""
    rows = con.execute(
        "SELECT doc_id, field, ok, answer FROM predictions WHERE run_id = ?", [run_id]
    ).fetchall()
    by_doc = defaultdict(list)
    for doc_id, field, ok, answer in rows:
        by_doc[doc_id].append((field, ok, answer))
    return {
        doc_id: from_rows([(f, a) for f, _, a in fields])
        if all(ok for _, ok, _ in fields)
        else None
        for doc_id, fields in by_doc.items()
    }


def blank(answer: ContractFields, fields: set[str]) -> ContractFields:
    """The same answer, with these fields set to "not found"."""
    return ContractFields.model_validate(answer.model_dump() | {f: empty_answer(f) for f in fields})


def blanked(
    con: duckdb.DuckDBPyConnection, run_id: str, answers: Answers, rules: set[str]
) -> Answers:
    """Blank each field that has an error from `rules` in the stored issues of `run_id`."""
    rows = con.execute(
        "SELECT doc_id, field, rule FROM issues WHERE run_id = ? AND severity = 'error'", [run_id]
    ).fetchall()
    broken = defaultdict(set)
    for doc_id, field, rule in rows:
        if rule in rules:
            broken[doc_id].add(field)
    return {
        doc_id: blank(answer, broken[doc_id]) if answer and broken[doc_id] else answer
        for doc_id, answer in answers.items()
    }


def derive(con: duckdb.DuckDBPyConnection, parent: str, name: str, answers: Answers) -> str:
    """Store answers as a normal run named `<parent>-<name>`, then score and check it. No LLM."""
    run_id = f"{parent}-{name}"
    con.execute("DELETE FROM runs WHERE run_id = ?", [run_id])  # so it can run again
    con.execute("DELETE FROM predictions WHERE run_id = ?", [run_id])
    con.execute(
        "INSERT INTO runs (run_id, split, parser, model, prompt_version, n_docs, est_cost_usd, "
        "max_retries) SELECT ?, split, parser, model, prompt_version, n_docs, 0, max_retries "
        "FROM runs WHERE run_id = ?",
        [run_id, parent],
    )
    for doc_id, answer in answers.items():
        con.executemany(
            "INSERT INTO predictions VALUES (?, ?, ?, ?, ?, ?)", to_rows(run_id, doc_id, answer)
        )
    score(con, run_id)
    validate(con, run_id)
    return run_id


def build(con: duckdb.DuckDBPyConnection, run_id: str) -> dict[str, tuple[str, str]]:
    """Policy -> (first run, final run). The retry run itself is the final run for "keep"."""
    first, final = first_answers(con, run_id), stored_answers(con, run_id)
    first_run = derive(con, run_id, "first", first)
    runs = {"keep": (first_run, run_id)}
    for policy, rules in BLANK.items():
        runs[policy] = (
            derive(con, run_id, f"first-{policy}", blanked(con, first_run, first, rules)),
            derive(con, run_id, policy, blanked(con, run_id, final, rules)),
        )
    return runs


CHANGED = """
WITH a AS (SELECT doc_id, field, answer::VARCHAR AS answer, tp
           FROM predictions JOIN scores USING (run_id, doc_id, field) WHERE run_id = $a),
b AS (SELECT doc_id, field, answer::VARCHAR AS answer, tp
      FROM predictions JOIN scores USING (run_id, doc_id, field) WHERE run_id = $b)
SELECT count(*) FILTER (WHERE a.answer <> b.answer),
    count(*) FILTER (WHERE a.tp > 0 AND b.tp = 0),
    count(*) FILTER (WHERE a.tp = 0 AND b.tp > 0)
FROM a JOIN b USING (doc_id, field)
"""
ERRORS = """
SELECT count(DISTINCT (doc_id, field)) FILTER (WHERE rule IN $v),
    count(DISTINCT (doc_id, field)) FILTER (WHERE rule IN $c)
FROM issues WHERE run_id = $run_id AND severity = 'error'
"""
RETRIES = """
SELECT count(DISTINCT doc_id), count(DISTINCT doc_id) FILTER (WHERE attempt_no > 0),
    count(*) FILTER (WHERE attempt_no > 0), count(*) FILTER (WHERE fixed),
    sum(cost_usd) FILTER (WHERE attempt_no = 0),
    coalesce(sum(cost_usd) FILTER (WHERE attempt_no > 0), 0)
FROM attempts WHERE run_id = ?
"""


def report(con: duckdb.DuckDBPyConnection, run_id: str, runs: dict[str, tuple[str, str]]) -> None:
    """Print first against final answers for each policy, then the errors and the retry cost."""
    print(
        f"{'':10} {'first: P':>8} {'R':>5} {'F1':>5}  {'final: P':>8} {'R':>5} {'F1':>5}"
        f"  {'changed':>7} {'lost':>4} {'gained':>6}"
    )
    for policy, (first, final) in runs.items():
        a, b = metrics(con, first)[-1], metrics(con, final)[-1]  # the last row is all fields
        changed, lost, gained = con.execute(CHANGED, {"a": first, "b": final}).fetchone()
        print(
            f"{policy:10} {a['precision']:8.3f} {a['recall']:5.3f} {a['f1']:5.3f}"
            f"  {b['precision']:8.3f} {b['recall']:5.3f} {b['f1']:5.3f}"
            f"  {changed:7} {lost:4} {gained:6}"
        )
    first, final = runs["keep"]
    sets = {"v": list(VALIDATION), "c": list(CITATION)}
    v0, c0 = con.execute(ERRORS, sets | {"run_id": first}).fetchone()
    v1, c1 = con.execute(ERRORS, sets | {"run_id": final}).fetchone()
    print(f"error fields: validation {v0} -> {v1}, citation {c0} -> {c1}")
    docs, retried, retries, fixed, cost0, cost1 = con.execute(RETRIES, [run_id]).fetchone()
    print(f"retries: {retried} of {docs} contracts, {retries} calls, {fixed} fixed")
    print(
        f"cost: first answers ${cost0:.4f}, retries ${cost1:.4f} ({cost1 / cost0:.0%}),"
        f" ${(cost0 + cost1) / docs:.4f} per contract"
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m docintel.evals.trust")
    parser.add_argument("run_id", help="a run made with --retries")
    args = parser.parse_args(argv)
    with connect() as con:
        con.execute(TABLES)
        runs = build(con, args.run_id)
        report(con, args.run_id, runs)


if __name__ == "__main__":
    main()
```

</details>

## Break it on purpose

**Break 1: the "before" is the final answer.** In `build`, change `first_answers(con, run_id)` to
`stored_answers(con, run_id)`. Guess: does a test fail? What does the report say?

<details><summary>What you see</summary>

All 75 tests pass. The tests check `first_answers`, not which function `build` calls.

On a test copy of the E1.3 run, with one retry added by hand that changed one field, the report
says:

```text
keep          0.901 0.910 0.905     0.901 0.910 0.905        0    0      0
...
retries: 1 of 52 contracts, 1 calls, 1 fixed
```

The "before" is now the "after", so the lift is always 0. Look for this: `fixed` above 0, but
`changed` is 0 on the `keep` row. A retry that fixed a field must change it. Put the line back.
</details>

**Break 2: no delete in `derive`.** Remove the two `DELETE` lines. Guess: which test fails?

<details><summary>What you see</summary>

```text
E       _duckdb.ConstraintException: Constraint Error: Duplicate key "run_id: r1-first" violates primary key constraint.
```

`test_derive_copies_the_parent_and_can_run_again` fails on the second `derive`. On real data, the
second `trust` command stops the same way. Put the lines back.
</details>

## Experiment

This part makes no paid run. The tool ran only on the pilot and on stored runs. Your policy goes into
`EXPERIMENTS.md` now, before the run:

```markdown
## E2.1 to E2.3: trust experiments (rules written before the run)
- **Date:** <date>
- **Policy for failed fields (2b2 Step 5):** <A, B or C>. It changes if: <your line>.
- **Keep rule for retries (2b3 Step 1):** <in 2b3>.
- **Results:** in 2b3.
```

Commit it with the code. The commit date proves the policy came first.

## Gotchas

- **Derived runs have no cost line.** `runner report <run_id>-first` prints P/R/F1, and no calls. The
  cost lives with the parent run.
- **`con.execute` returns the connection.** Two `execute` calls, then two `fetchone` calls, give the
  second result twice. Call `fetchone` right after each `execute`, as in the test.
- **The database is locked.** Close the notebook before the trust command, and the other way round.

## Explain back, then commit

Explain each changed file to Claude in a few sentences (the rule in `PLAN.md`):

- `runner.py`: why `to_rows` takes the answer now.
- `trust.py`: why the "before" is attempt 0, what each derived run holds, and what each query counts.
- `test_trust.py`: what each test protects, and which break no test catches.
- `EXPERIMENTS.md`: your policy, and the evidence behind it.

Then:

```sh
git status
git add src/docintel/evals/runner.py src/docintel/evals/trust.py tests/test_runner.py tests/test_trust.py EXPERIMENTS.md
git commit -m "phase 2b2: trust replay tool and rules before the run"
```

## Conclusion

What you have now:

- A replay tool that turns one retry run into 6 runs: first and final, under 3 policies.
- A policy for failed fields, written and committed before the run.

Go back to the objectives. Check that you can do each one without notes. Then answer:

1. Why is attempt 0 of the same run a better "before" than a second run with `--retries 0`?
2. Blanking removed an error and lowered recall. Use Round 1 to explain how.
3. Why does `build` make `-first` before the blanked first runs?

Want more practice? Try these (optional):

1. Add a policy that drops only the bad quote and keeps the field if another quote is left.
2. Replay policy B on the kept run `20261102-200003` with `blanked`. Do you get the Step 5 numbers?

Checklist (`../PLAN.md`): **Validation, citation check, retry with feedback; retry cost** (what to do
with a failed field, from replays; the retry cost query). **Experiments: run_id,
one change at a time, cost, p50/p95** (derived runs with their own `run_id`, a policy before the run).
The measured numbers come in 2b3.
