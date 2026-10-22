# Phase 1c: store and score a run

In this part, you build the first half of `evals/runner.py`: the tables for a run, a cost
estimate, and the code that stores each answer and scores it. You build it one piece at a time,
with a checkpoint after each piece. This part makes no LLM call, so it costs nothing.

1c has four parts:

- **1c**: store and score a run (this part).
- **1c2**: run a whole split, 8 calls at a time, with resume. Then E1, the first full run.
- **1c3**: E1 results: precision and recall per field, a chart, and the real misses.
- **1c4**: E1.1: the same run with newer open-weight models, and your choice of model.

## Words used in this part

Read these first. 1b2 words (TP, FP, FN, precision, recall) are used again.

- **Batch run**: the same job done on many items, with one command. Example: `extract` on all
  52 dev contracts.
- **Run, `run_id`**: one batch run, with one name. Every row it writes carries that name.
  Example: `20261021-143205`, the date and time it started.
- **Prediction**: what the model answered for one field of one contract. Example:
  `governing_law` is `Michigan`, found, with one quote.
- **Long table**: one row per small fact, like `labels`. Example: one row per contract and
  field, so 52 contracts give 624 rows.
- **JSON column**: a column that holds a JSON text. DuckDB can read parts of it with SQL.
- **Round trip**: turn something into another form and back, and get the same thing. Example:
  Pydantic object to JSON text to Pydantic object.
- **Estimate**: a guess of the cost before you spend anything. Example: about $0.09 for dev.
- **Rescore**: score stored predictions again, for example after a rule change. No new LLM call.

## Objectives

By the end of this part you should be able to:

1. Explain why predictions and scores are two separate steps, and what that saves.
2. Explain the three new tables and how `run_id` ties them together.
3. Estimate the cost of a run before you start it, and say why the estimate can be wrong.
4. Store one answer as 12 rows and rebuild the same answer from them.
5. Defend your rule for answers that fail the schema.

## Dependencies

You install nothing new. `json` and `urllib` are part of Python.

This part needs:

- 1b: `build_messages` and `data/examples/ecoscience_v1.json`, your real answer for one contract.
- 1b2: `score_doc` in `scorers.py`, and the `answers` table.

No LLM call. Step 2 reads OpenRouter's public price list, which is free and needs no key.

## The big picture

Before this part, we can extract and score one contract by hand, in a terminal.

The full runner, after 1c2:

```
splits ─► text ─► extract (8 at once) ─► predictions ─► score ─► scores
                         └─► llm_calls (cost, latency)
```

This part builds everything except "8 at once":

- `runs` says what each run was: split, parser, model, prompt version.
- `predictions` keeps every answer, one row per field.
- `score(run_id)` turns stored predictions into `scores` rows, with your 1b2 rules.

1c2 adds the loop over many contracts and the command. 1c3 sums `scores` into the E1 table.
2a, 2b and 3b change one thing and run the same command again.

## Remember this

> A run is a name for a set of rows. The runner stores every answer first, then scores it. So
> you pay for answers once, and you can score them again for free. The stored rows must rebuild
> exactly the answer the model gave, or every later score is wrong.
>
> **Pay once, score many times. Store it so you can rebuild it.**

## Why

**Answers cost money, scores do not.** An answer is an LLM call. A score is a few lines of
Python. If a scoring rule changes, we score the stored answers again. We do not pay for 52 new
calls.

**Every number needs a source.** The README will say "Governing Law F1 is 0.9". Someone asks
"which model, which prompt?" The `run_id` answers that with one query on `runs`.

**You should know the cost before you spend it.** One dev run is cheap. A wrong model id or a
long contract set can make it expensive. The estimate prints before anything is sent.

## Design decisions

- **A `runs` table, one row per run.** The setup is in one place. Other option: model and
  prompt in every prediction row. 624 copies of the same text.
- **`predictions` is long: one row per contract and field, like `labels`.** SQL per field is
  easy. Other option: one row per contract with all 12 fields as JSON. Then every field query
  needs JSON paths.
- **Each row keeps the field's whole answer as JSON.** `score` rebuilds the exact Pydantic
  object, so `score_doc` from 1b2 works unchanged. Other option: one column for value and one for
  quotes. Then Parties (a list) and yes/no fields (no value) need special code to rebuild.
- **`ok` and `found` are also plain columns.** SQL can count bad answers and found fields with
  no JSON at all.
- **A primary key on run, contract and field.** DuckDB refuses a second row for the same field.
  A bug that writes twice fails loudly. Other option: no key. Double rows would count twice in
  every score.
- **Predict, then score, as two steps.** Rescoring is free. Other option: score inside the loop.
  Then a rule change needs new LLM calls.
- **The estimate counts characters, not tokens.** It only needs to be roughly right, and 1c2's
  pilot run measures the real cost. Other option: each model's own tokenizer. Exact, but one
  more library for each model.

## Worked example

Real numbers. Guess before you open each box.

### Round 1: a rule changes after the run

E1 will cost about 9 cents for 52 contracts. After E1, you change `THRESHOLD` in `scorers.py`
from 0.5 to 0.4. What do you pay to get the new scores?

<details><summary>Guess, then open</summary>

Nothing. The 624 answers are stored in `predictions`. `score(run_id)` reads them, rebuilds each
answer, and calls `score_doc` with the new threshold. No LLM call.

If we only stored scores, the answers would be gone, and we would pay for 52 new calls. The new
answers would also be a little different, so you could not tell if the rule or the model made
the change.
</details>

### Round 2: the estimate and the real cost

The 1b contract has 18,104 characters. The estimate in Step 2 says $0.00101. The real call in
1b cost $0.00118. Why is the real cost higher?

<details><summary>Guess, then open</summary>

The estimate uses the price OpenRouter lists for the model: $0.09 per million input tokens. But
OpenRouter sent the 1b call to Parasail, which charges $0.14. Each provider has its own price.

So an estimate is a guide, not a promise. 1c2 runs a pilot of 3 contracts first, and compares
the real cost with the estimate.
</details>

### Round 3: one answer fails the schema

In a run of 52 contracts, one answer is bad JSON. Option A: count that contract as "nothing
found". Option B: leave it out of the scores. Which option gives the higher recall?

<details><summary>Guess, then open</summary>

Option B. The bad contract has present fields. Option A counts them as FN, so recall goes down.
Option B hides them, so the model looks better than it is. A user of the product would get
nothing for that contract. You decide this in Step 3.
</details>

## Project setup

Create the empty files:

```sh
touch src/docintel/evals/runner.py tests/test_runner.py
```

You should now have:

```
src/docintel/
├── core/llm.py                LLMResult
├── domain/extract/extract.py  build_messages
└── evals/
    ├── datasets.py
    ├── runner.py              empty
    ├── scorers.py             score_doc
    └── store.py
tests/
└── test_runner.py             empty
```

## Step 1: tables, contracts and text

**Why.** A run needs a list of contracts, the text of each, and tables for its rows.

Put this in `src/docintel/evals/runner.py`:

```python
"""Batch runner: extract every contract of a split, store the answers, score them."""

import json
import urllib.request
from collections import defaultdict
from pathlib import Path

import duckdb

from docintel.core.config import get_settings
from docintel.core.llm import LLMResult
from docintel.domain.extract.extract import build_messages
from docintel.domain.schema.fields import ContractFields, Names
from docintel.evals.scorers import score_doc

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
```

*Python here: `(path,) = ...fetchone()` is in [1b PY-4](./py/phase-1b.md#py-4).*

Here, we:

1. Import everything this part needs. Some imports are used only in later steps. `make lint`
   reports them as unused until Step 4. We run it in Step 5.
2. Create three tables, only if they are not there yet. `make data` never touches them.
3. `runs` has one row per run: its setup, how many contracts, and the cost estimate.
4. `predictions` and `scores` have a primary key of run, contract and field.
5. `docs_for` returns a split's contracts sorted by `doc_id`. The same order every time means a
   pilot of 3 and a resumed run always pick the same contracts (1c2).
6. `cuad_txt` reads CUAD's clean text. `PARSERS` maps a name to a function, so the command can
   pick one. Phase 3 adds PDF parsers here.

Checkpoint. Close the notebook connection first: this writes to the database.

```sh
uv run python -c "
from docintel.evals.runner import TABLES, docs_for, cuad_txt
from docintel.evals.store import connect
with connect() as con:
    con.execute(TABLES)
    dev = docs_for(con, 'dev')
    print(len(dev), dev[0])
    print(len(cuad_txt(con, dev[0])))
    print(con.sql('SELECT count(*) FROM runs').fetchone(), con.sql('SELECT count(*) FROM predictions').fetchone())"
```

```text
52 2ThemartComInc_19990826_10-12G_EX-10.10_6700288_EX-10.10_Co-Branding Agreement_ Agency Agreement
29454
(0,) (0,)
```

52 dev contracts, the first one has 29,454 characters, and both new tables are empty.

## Step 2: estimate the cost

**Why.** You should know what a run costs before you spend it.

Add to the bottom of `src/docintel/evals/runner.py`:

```python
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
```

*Python here: [`urllib.request.urlopen` and `json.load`](./py/phase-1c.md#py-1).*

Here, we:

1. Ask OpenRouter for its list of models and prices. This list is public, so it needs no key.
2. Keep only the price of our model, per token, for input and for output.
3. Build the real messages for each contract, so the system prompt is counted too.
4. Turn characters into tokens with a rough rule. In 1b, 20,456 characters were 4,476 tokens,
   about 4.6 per token. We use 4.0 so the guess is a little too high, not too low.
5. Add a guess for the output: 1,000 tokens for each contract.

Checkpoint. Guess first: is the estimate for the 1b contract above or below its real $0.00118?

```sh
uv run python -c "
from docintel.evals.runner import cuad_txt, docs_for, estimate, price
from docintel.evals.store import connect
DOC = 'EcoScienceSolutionsInc_20171117_8-K_EX-10.1_10956472_EX-10.1_Endorsement Agreement'
M = 'qwen/qwen3-235b-a22b-2507'
print(price(M))
with connect() as con:
    print(round(estimate([cuad_txt(con, DOC)], M, 'v1'), 5))
    print(round(estimate([cuad_txt(con, d) for d in docs_for(con, 'dev')], M, 'v1'), 3))"
```

```text
(9e-08, 5.5e-07)
0.00101
0.087
```

1. $0.09 and $0.55 per million tokens, written per token.
2. Below the real cost. That is Round 2: the provider was more expensive than the listed price.
3. The whole dev split: about 9 cents. Write this number in your notebook.

## Step 3: one answer, twelve rows (your decision)

**Why.** `predictions` stores one row per field. `score` must turn the rows back into the same
`ContractFields`.

First, decide what a bad answer means for the score. Bad means: the model answered, but the JSON
did not fit your schema. `parsed` is `None`, and `error` holds the Pydantic error.

The evidence:

- In 1a2 and 1b, every real answer fit the schema. Strict `json_schema` with
  `require_parameters` makes bad JSON rare, but not impossible.
- The newer models in 1c4 may fail more often.
- 2b sends the error back to the model and retries. That will fix many bad answers. E2.3
  measures how many.

Decide, and write it in your notebook, under your "Scoring rules" cell:

1. **Count it as "nothing found".** Every present field becomes an FN.
2. **Leave the contract out of the scores.** Precision and recall only see good answers.
3. **Stop the run.** No numbers until the model is fixed.

Whatever you pick, the runner stores the bad answer as 12 empty rows with `ok = false`. Your
choice lives in `score` (Step 4).

Add to the bottom of `src/docintel/evals/runner.py`:

```python
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
```

*Python here: [`model_fields[...].annotation`](./py/phase-1c.md#py-2) ·
[JSON both ways: `model_dump`, `json.dumps`, `json.loads`](./py/phase-1c.md#py-3).*

Here, we:

1. In `empty_answer`, look up the field's model class (`Clause`, `Text` or `Names`). Build the
   "not found" shape for it. Parties needs `[]`, a date needs `None`, a yes/no field has no
   value at all.
2. In `to_rows`, go through your 12 fields in schema order. For a good answer, turn the field's
   Pydantic object into a dict. For a bad one, use the empty shape.
3. Keep `ok` and `found` as their own columns, so SQL can count them. Keep the whole answer as a
   JSON string.
4. In `from_rows`, parse each JSON string back into a dict. Then let Pydantic check it and
   build the `ContractFields` again, with your strict rules.

Checkpoint. Guess the last line first: are the rebuilt fields equal to the original?

```sh
uv run python - <<'EOF'
import json
from pathlib import Path
from docintel.core.llm import LLMResult
from docintel.domain.schema.fields import ContractFields
from docintel.evals.runner import from_rows, to_rows
DOC = 'EcoScienceSolutionsInc_20171117_8-K_EX-10.1_10956472_EX-10.1_Endorsement Agreement'
pred = ContractFields.model_validate_json(Path('data/examples/ecoscience_v1.json').read_text())
good = LLMResult('', pred, None, {}, None, 0, 'm', None, 1)
bad = LLMResult('{}', None, 'bad json', {}, None, 0, 'm', None, 1)
rows = to_rows('1b-example', DOC, good)
print(len(rows), rows[2][2:5], json.loads(rows[2][5])['value'])
print(to_rows('1b-example', DOC, bad)[0][2:])
print(from_rows([(row[2], row[5]) for row in rows]) == pred)
EOF
```

```text
12 ('governing_law', True, True) Michigan
('parties', False, False, '{"quotes": [], "found": false, "value": []}')
True
```

1. 12 rows. The third is `governing_law`: ok, found, value `Michigan`.
2. A bad answer: `ok` and `found` are false, and Parties gets an empty list.
3. `True`: the rows rebuild exactly the answer we stored. Nothing is lost on the way.

`LLMResult(...)` here is a fake result with the 9 fields in order. Only `parsed` matters.

<details><summary>Reference choice (open after you decide)</summary>

Option 1: count it as "nothing found". The rows are already empty, so `score` needs no change.
Next to precision and recall, always report how many answers were bad (1c3 does this). Option 2
makes a model that breaks the schema look better than an honest one. Option 3 throws away 51
good answers because of one bad one.
</details>

## Step 4: score a run

**Why.** Scores come from stored predictions, so we can score again at any time for free.

Add to the bottom of `src/docintel/evals/runner.py`:

```python
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
```

*Python here: [`{"run_id": ..., **r}`: adding keys to a dict](./py/phase-1c.md#py-4) ·
`defaultdict`: [0d PY-3](./py/phase-0d.md#py-3) · `$name`: [0d PY-5](./py/phase-0d.md#py-5).*

Here, we:

1. Read all predictions of the run, and group the rows by contract.
2. Delete the old scores of this run. So scoring twice gives the same rows, not double rows.
3. For each contract, rebuild the `ContractFields` with `from_rows`, and call your `score_doc`
   from 1b2. The rules are exactly the ones you tested.
4. Add `run_id` and `doc_id` to each score row, and insert them by name.

If you chose "leave bad answers out" in Step 3, add `AND ok` to the first query. That one line
is your decision.

Checkpoint. Store your 1b answer as a tiny run called `1b-example`, then score it twice. Guess
first: how many rows does `scores` have after two calls?

```sh
uv run python - <<'EOF'
from pathlib import Path
from docintel.core.llm import LLMResult
from docintel.domain.schema.fields import ContractFields
from docintel.evals.runner import TABLES, score, to_rows
from docintel.evals.store import connect
DOC = 'EcoScienceSolutionsInc_20171117_8-K_EX-10.1_10956472_EX-10.1_Endorsement Agreement'
pred = ContractFields.model_validate_json(Path('data/examples/ecoscience_v1.json').read_text())
with connect() as con:
    con.execute(TABLES)
    rows = to_rows('1b-example', DOC, LLMResult('', pred, None, {}, None, 0, 'm', None, 1))
    con.executemany('INSERT INTO predictions VALUES (?, ?, ?, ?, ?, ?)', rows)
    print(score(con, '1b-example'), score(con, '1b-example'))
    print(con.execute("SELECT sum(tp), sum(fp), sum(fn), count(*) FROM scores WHERE run_id = '1b-example'").fetchone())
EOF
```

```text
1 1
(7, 2, 2, 12)
```

1. One contract scored, twice.
2. 12 score rows, not 24: the second call replaced the first.
3. 7 TP, 2 FP, 2 FN. Compare with your 1b2 Step 4 table. It must be the same, because the
   rules are the same. If it is not, the rows changed the answer on the way.

Keep the `1b-example` rows. 1c3 uses them as a free example. They have no row in `runs`, and
every later query filters by `run_id`. Run this checkpoint only once: a second time, the primary
key refuses the same 12 prediction rows.

## Step 5: a test for the rules that must never break

**Why.** Two things must stay true: the rows rebuild the same answer, and a bad answer still
gives 12 valid rows.

Put this in `tests/test_runner.py`:

```python
"""Runner rules with a fake extract. No network, no key, no CUAD files."""

from docintel.core.llm import LLMResult
from docintel.domain.schema.fields import ContractFields
from docintel.evals import runner

FIELDS = {field: runner.empty_answer(field) for field in ContractFields.model_fields}
FIELDS["parties"] = {"quotes": ["Acme Inc."], "value": ["Acme Inc.", "Beta LLC"], "found": True}
FIELDS["governing_law"] = {"quotes": ["laws of Michigan"], "value": "Michigan", "found": True}
PRED = ContractFields.model_validate(FIELDS)


def result(parsed: ContractFields | None) -> LLMResult[ContractFields]:
    return LLMResult(
        raw_text="{}",
        parsed=parsed,
        error=None if parsed else "bad json",
        usage={},
        cost_usd=0.001,
        latency_ms=10,
        model="fake",
        provider=None,
        attempts=1,
    )


def test_rows_rebuild_the_same_answer():
    rows = runner.to_rows("r1", "d1", result(PRED))
    assert len(rows) == 12
    assert runner.from_rows([(field, answer) for _, _, field, _, _, answer in rows]) == PRED


def test_bad_answer_becomes_12_empty_fields():
    rows = runner.to_rows("r1", "d1", result(None))
    assert {(ok, found) for _, _, _, ok, found, _ in rows} == {(False, False)}
    runner.from_rows([(field, answer) for _, _, field, _, _, answer in rows])  # still valid
```

Here, we:

1. Build one answer with a list (Parties), a value (Governing Law) and 10 empty fields.
2. Make a fake `LLMResult` with a helper, so each test only says what is different.
3. Check that 12 rows rebuild exactly that answer.
4. Check that a bad answer gives 12 rows with `ok` and `found` false, and that Pydantic still
   accepts them. If it did not, `score` would crash on the first bad answer.

The file says "with a fake extract" already: 1c2 adds a third test that uses one.

Checkpoint:

```sh
make lint && make test
```

```text
All checks passed!
...
tests/test_data_load.py ....                                             [ 12%]
tests/test_extract.py ...                                                [ 21%]
tests/test_llm.py ....                                                   [ 34%]
tests/test_runner.py ..                                                  [ 40%]
tests/test_schema.py ....                                                [ 53%]
tests/test_scorers.py .........                                          [ 81%]
tests/test_smoke.py .                                                    [ 84%]
tests/test_splits.py .....                                               [100%]

============================== 32 passed in 0.95s ==============================
```

Your project should now look like this:

```
src/docintel/
└── evals/
    ├── runner.py              TABLES, docs_for, cuad_txt, PARSERS, price, estimate,
    │                          empty_answer, to_rows, from_rows, score
    ├── scorers.py
    └── store.py
tests/
├── test_runner.py             2 tests
└── ...
data/
└── docintel.duckdb            + runs, predictions, scores (the 1b-example run)
```

<details><summary>Full <code>src/docintel/evals/runner.py</code> (after 1c)</summary>

```python
"""Batch runner: extract every contract of a split, store the answers, score them."""

import json
import urllib.request
from collections import defaultdict
from pathlib import Path

import duckdb

from docintel.core.config import get_settings
from docintel.core.llm import LLMResult
from docintel.domain.extract.extract import build_messages
from docintel.domain.schema.fields import ContractFields, Names
from docintel.evals.scorers import score_doc

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
```
</details>

## Break it on purpose

**Break 1: a null list.** In `empty_answer`, change the value line to `answer["value"] = None`.
Guess which test fails, and why:

```
E       pydantic_core._pydantic_core.ValidationError: 1 validation error for ContractFields
E       parties.value
E         Input should be a valid list [type=list_type, input_value=None, input_type=NoneType]
FAILED tests/test_runner.py::test_bad_answer_becomes_12_empty_fields - pydant...
========================= 1 failed, 31 passed in 0.83s =========================
```

Your strict schema says Parties is a list. `None` is not a list, not even an empty one. Without
this test, the first bad answer in a real run would crash `score`. Change it back.

**Break 2: a wrong model id.** Guess what `price` does with a capital `B`:

```sh
uv run python -c "
from docintel.evals.runner import price
price('qwen/qwen3.8-27B')"
```

```text
...
    p = prices[model]  # a KeyError here means the model id is wrong
        ~~~~~~^^^^^^^
KeyError: 'qwen/qwen3.8-27B'
```

Model ids are case-sensitive. The estimate fails before any money is spent. That is a second
job of the estimate: it checks the model id.

## Experiment

This part makes no LLM call and no run, so there is no `EXPERIMENTS.md` entry yet. Write your
dev cost estimate (Step 2) and your bad-answer rule (Step 3) in the notebook. E1 in 1c2 cites
both.

## Gotchas

- **The database is locked.** DuckDB allows one writer. Close the notebook connection before a
  checkpoint that writes. The error says `Could not set lock on file`.
- **`Constraint Error: Duplicate key`.** You inserted the same run, contract and field twice.
  That is the primary key doing its job. Use a new `run_id`, or delete the old rows first.
- **`make data` does not touch the new tables.** It replaces `contracts`, `labels`, `splits`
  and `answers` only. Your runs stay.
- **Prices change.** `price` reads them live, so an estimate made next week may differ a little.

## Explain back, then commit

Explain each changed file to Claude in a few sentences (the rule in `PLAN.md`): `runner.py` (the
three tables, why predictions and scores are separate, how a row rebuilds an answer, where your
Step 3 decision lives) and `test_runner.py` (each test). Then:

```sh
git status
git add src/docintel/evals/runner.py tests/test_runner.py notebooks/00_explore.ipynb
git commit -m "phase 1c: runs, predictions and scores tables, estimate, score(run_id)"
```

## Conclusion

What you have now:

- `runs`, `predictions` and `scores`, all tied together by `run_id`.
- A cost estimate that also checks the model id.
- Answers stored as rows that rebuild the exact Pydantic object.
- `score(run_id)`: rescoring for free, with your 1b2 rules.

Go back to the objectives. Check that you can do each one without notes. Then answer:

1. You change `THRESHOLD` from 0.5 to 0.4. What do you run, and what does it cost?
2. Why does `predictions` keep the whole answer as JSON, and not only `found`?

Want more practice? Try these (optional):

1. In the notebook, find all found fields of `1b-example` with SQL only:
   `SELECT field FROM predictions WHERE run_id = '1b-example' AND found`.
2. Make `estimate` print the input and output parts of the cost separately. Which part is
   bigger for dev?

Checklist (`../PLAN.md`): **Experiments: run_id, one change at a time, cost, p50/p95** (started:
`run_id` and the cost estimate; the runs, p50/p95 and "one change at a time" come in 1c2 to
1c4).
