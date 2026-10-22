# Phase 1c2: run a whole split

In this part, you finish `evals/runner.py`: a loop that sends many contracts at the same time,
resume for a stopped run, and the command line. You build it one piece at a time, with a
checkpoint after each piece. At the end you run E1: the first full run on the 52 dev contracts.

This is part 2 of 4 for Phase 1c. 1c built the tables, the estimate and `score`. 1c3 reads the
E1 results. 1c4 compares models.

## Words used in this part

Read these first. 1c words (run, `run_id`, prediction, estimate, rescore) are used again.

- **Concurrency**: how many calls are waiting for an answer at the same time. Example: 8.
- **Thread**: a second worker inside one Python program. While one thread waits for the network,
  another can send a request.
- **Thread pool**: a fixed group of threads that take jobs from a queue. Like `p-limit` in JS.
- **Future**: a box for a result that is not ready yet. Like a JS `Promise`.
- **Resume**: finish a stopped run without redoing the contracts that are already done.
- **Pilot run**: a small real run first, to check the code and the real cost. Example: 3
  contracts.
- **CLI (command line interface)**: a program you start from the terminal with flags. Example:
  `run --split dev --limit 3`.
- **Subcommand**: the first word after the program name, like `commit` in `git commit`.
- **Wall time**: the time on the clock for the whole run. With 8 calls at once, it is much less
  than the sum of all call times.
- **p50, p95**: the latency that 50% (or 95%) of calls stay under. p50 is the median. p95 shows
  the slow calls.

## Objectives

By the end of this part you should be able to:

1. Explain how 8 threads make the run faster, and why only one thread writes to DuckDB.
2. Explain what happens to a call that crashes, and to a call that returns bad JSON.
3. Stop a run with Ctrl-C and finish it with `--resume`, without paying twice.
4. Run a pilot, and compare its real cost with the estimate.
5. Find a run's cost, latency and failures in DuckDB from its `run_id`.

## Dependencies

You install nothing new. `concurrent.futures`, `argparse` and `datetime` are part of Python.

This part needs 1c: the three tables, `estimate`, `to_rows`, `score`, and the first two tests in
`test_runner.py`. It also uses `extract` (1b) and `log_call` (1a2).

You need a real key in `.env`. The pilot costs less than one cent. The full dev run costs about
ten cents.

## The big picture

Before this part, `runner.py` can store and score answers, but it has no loop and no command.

After this part, one command does the whole split:

```
splits ─► text ─► extract (8 at once) ─► predictions ─► score ─► scores
                         └─► llm_calls (cost, latency)
```

- `run_docs` sends the contracts 8 at a time and stores each answer as it arrives.
- `todo` finds the contracts that are not done yet. That is resume.
- `run` and `score` are subcommands of one CLI.
- E1 is the first full dev run. 1c3 turns it into the results table.

## Remember this

> Most of an LLM call is waiting, so 8 threads wait together and the run is about 8 times
> faster at the same cost. Only the main thread writes to DuckDB. Resume means "do only the
> contracts with no answer yet", and the database already knows which ones those are.
>
> **Wait together, write alone. The database knows what is done.**

## Why

**Calls are slow.** The 1b call took 22 seconds. One at a time, 52 contracts take very long.
Most of that time the program only waits for the network.

**Runs stop.** Wi-Fi drops, a provider fails, you press Ctrl-C. Without resume, you start again
and pay again for every contract that was already done.

**One bad contract must not stop 51 good ones.** A call that fails after all its retries is
noted, and the run goes on. Resume tries it again later.

## Design decisions

- **`run_id` is the start time, like `20261021-143205`.** Easy to read, sorts by date, and two
  runs never share one. Other option: a hash of the setup. Then the same command resumes by
  itself, but you can never run the same setup twice.
- **Threads, and only the main thread writes to DuckDB.** Our client from 1a2 is not `async`,
  so threads fit it. One DuckDB connection must not be used by many threads at once. Other
  option: `asyncio` with an async client, like `Promise.all` in JS. It needs a second client.
- **Resume looks at `predictions`.** A contract is done when it has rows. Other option: a
  progress file. Then the file and the database can disagree.
- **A call that crashes writes nothing.** Resume tries it again. A call that returns bad JSON
  writes 12 empty rows (your 1c decision). Fixing bad JSON is the job of 2b.
- **`--resume` reads the setup from `runs`.** The flags are ignored, so one run can never mix
  two models. Other option: trust the flags. One typo would mix two setups in one `run_id`.
- **Ask before spending.** The command prints the estimate and waits for `y`. `--yes` skips the
  question, for scripts. The run is saved in `runs` only after `y`.

## Worked example

Guess before you open each box.

### Round 1: four calls of one second

A fake `extract` waits one second, then answers. We run it on 4 contracts, first with
concurrency 1, then with concurrency 4. Guess the two wall times.

<details><summary>Guess, then open</summary>

Real output from Step 1:

```
concurrency 1: 4.1 s
concurrency 4: 1.1 s
```

The four threads all wait at the same time. Waiting is most of an LLM call, so the full dev run
is about 8 times faster with 8 threads. The cost is the same: you pay per token, not per second.
</details>

### Round 2: the run stops at 30 of 52

Your E1 run stops after 30 contracts: the Wi-Fi drops. You type the same command again, with no
`--resume`. What happens, and what does it cost?

<details><summary>Guess, then open</summary>

A new run starts, with a new `run_id`, and sends all 52 contracts again. You pay for 82 calls,
and the first 30 answers sit in an unfinished run.

With `--resume <run_id>`, `todo` finds the 22 contracts with no rows. Only those are sent. The
finished run has 52 contracts and one `run_id`, as if it never stopped.
</details>

## Project setup

No new files. You add to `src/docintel/evals/runner.py` and `tests/test_runner.py` from 1c.

```
src/docintel/evals/
└── runner.py                  from 1c: tables, estimate, rows, score
tests/
└── test_runner.py             from 1c: 2 tests
```

## Step 1: many contracts at the same time

**Why.** 52 slow calls, one at a time, waste most of the time waiting. And a stopped run must
not be paid for twice.

Update the imports at the top of `src/docintel/evals/runner.py`:

```python
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
from docintel.evals.scorers import score_doc
from docintel.evals.store import connect
```

Some of these are used only in Step 2. Then add to the bottom of the file:

```python
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
```

*Python here: [`ThreadPoolExecutor`, `submit` and `as_completed`](./py/phase-1c2.md#py-1) ·
[`try` / `finally` and Ctrl-C](./py/phase-1c2.md#py-2).*

Here, we:

1. In `todo`, find the contracts of this run that already have rows, and return the others.
   This is resume: the database is the record of what is done.
2. In `run_docs`, start a pool of `concurrency` threads.
3. Give every contract to the pool with `submit`. Each one returns a future. The dict
   `futures` remembers which contract each future belongs to.
4. `as_completed` hands us each future when it is finished, fastest first, not in the order we
   sent them.
5. For each finished call, write it to `llm_calls` with the `run_id`, then write its 12 rows.
   Only this main thread touches DuckDB.
6. A call that raised an error (network down after all retries, a 400) writes nothing. The run
   goes on. A later resume sends it again.
7. `finally` runs even on Ctrl-C. It drops the calls that have not started yet. Without it,
   Python would finish (and pay for) all the waiting calls before it stops.

Note that `extract` gets no `con`. A worker thread must not write to DuckDB, so `run_docs` calls
`log_call` itself.

Checkpoint. A fake `extract` that waits one second shows the speed-up with no cost. It returns no
answer, so each line says `ok=False`. Guess both times first (Round 1):

```sh
$ uv run python - <<'EOF'
import time
from docintel.core.llm import LLMResult
from docintel.evals import runner
from docintel.evals.store import connect

def slow_fake(text, model, *, prompt_version):
    time.sleep(1)  # like a 1-second LLM call
    return LLMResult("{}", None, "fake", {}, 0.0, 1000, model, "Fake", 1)

runner.extract = slow_fake
texts = {"doc-a": "...", "doc-b": "...", "doc-c": "...", "doc-d": "..."}
with connect(":memory:") as con:
    con.execute(runner.TABLES)
    for n in (1, 4):
        start = time.perf_counter()
        runner.run_docs(con, f"demo-{n}", texts, "fake", "v1", concurrency=n)
        print(f"concurrency {n}: {time.perf_counter() - start:.1f} s")
    print(runner.todo(con, "demo-4", ["doc-a", "doc-e"]))
EOF
[1/4] doc-a  ok=False  $0.0000  1.0 s
[2/4] doc-b  ok=False  $0.0000  1.0 s
[3/4] doc-c  ok=False  $0.0000  1.0 s
[4/4] doc-d  ok=False  $0.0000  1.0 s
concurrency 1: 4.1 s
[1/4] doc-b  ok=False  $0.0000  1.0 s
[2/4] doc-d  ok=False  $0.0000  1.0 s
[3/4] doc-c  ok=False  $0.0000  1.0 s
[4/4] doc-a  ok=False  $0.0000  1.0 s
concurrency 4: 1.1 s
['doc-e']
```

1. One at a time: 4 seconds, in the order we sent them.
2. Four at a time: 1 second, and the order is mixed (yours may differ). Whichever finishes first
   is written first.
3. Each call still took 1.0 s. Concurrency makes the run faster, not each call.
4. `todo` says `doc-a` is done and `doc-e` is not. That is resume.

The database is `:memory:`, so this demo writes nothing to your real file.
`runner.extract = slow_fake` swaps the real function for the fake in this one script only. The
test in Step 4 does the same in a cleaner way.

## Step 2: the command

**Why.** One command runs the plan's experiment, with the same flags every time.

Add to the bottom of `src/docintel/evals/runner.py`:

```python
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
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    with connect() as con:
        con.execute(TABLES)
        if args.command == "score":
            print(f"scored {score(con, args.run_id)} docs for run {args.run_id}")
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

*Python here: [`argparse` with subcommands](./py/phase-1c2.md#py-3) ·
[slices with `None`: `docs[:None]`](./py/phase-1c2.md#py-4) ·
`if __name__ == "__main__"`: [0b PY-7](./py/phase-0b.md#py-7).*

Here, we:

1. Define two subcommands, like `git commit` and `git push`: `run` and `score`.
2. `score RUN_ID` only rescores. No money, no network.
3. For a new run, make the `run_id` from the clock. Take the setup from the flags. `--limit 3`
   keeps the first 3 contracts.
4. For `--resume`, read the setup from `runs`. The flags are ignored.
5. Keep only the contracts with no rows yet, read their text, and print the estimate.
6. Ask before spending. Save the run in `runs` only after `y`, so a "no" leaves nothing behind.
7. Run, measure the wall time, score, and print a short summary. If some calls failed, print
   the resume command.

Checkpoint. The help text costs nothing:

```sh
$ uv run python -m docintel.evals.runner --help
usage: python -m docintel.evals.runner [-h] {run,score} ...

positional arguments:
  {run,score}
    run        extract every doc of a split, then score the run
    score      score a stored run again (no LLM calls)

options:
  -h, --help   show this help message and exit
```

Try `run --help` too: one line per flag, with the `help=` text you wrote.

## Step 3: the pilot run, and a stop on purpose

**Why.** A small real run checks the code and the real cost before you spend on 52 contracts.

Run 3 real contracts. Answer `y` at the prompt.

```sh
$ uv run python -m docintel.evals.runner run --split dev --parser cuad_txt --model qwen/qwen3-235b-a22b-2507 --prompt-version v1 --limit 3
run 20261021-HHMMSS: 3 of 3 docs to do, qwen/qwen3-235b-a22b-2507, about $0.0051
Start? [y/N] y
```

<!-- LIVE OUTPUT: pilot run lines from the user's own run -->

The first line is real: the estimate for the first 3 dev contracts is $0.0051. After the
prompt, your output has this shape:

1. Three lines `[i/3] <doc_id>  ok=True  $<cost>  <seconds> s`, in the order they finish.
2. `done in <seconds> s: 3 of 3 docs scored, 0 calls failed`.

If a line says `FAILED`, read the error name. `BadRequestError` means a 400: read the message.

Then compare the estimate with the real cost. In the notebook:

```python
con.sql("""
SELECT r.run_id, r.n_docs, r.est_cost_usd, sum(c.cost_usd) AS real_cost,
       count(*) FILTER (WHERE NOT c.ok) AS bad_answers
FROM runs r JOIN llm_calls c USING (run_id)
GROUP BY r.run_id, r.n_docs, r.est_cost_usd
""")
```

<!-- LIVE OUTPUT: estimate against real cost for the pilot run -->

You see one row per run. If `real_cost` is more than twice `est_cost_usd`, look at `provider`
in `llm_calls` before the full run.

Now stop a run on purpose. Close the notebook connection. Start a pilot of 10 with
`--limit 10 --concurrency 2`, answer `y`, and press Ctrl-C after two lines. The traceback ends
with:

```
KeyboardInterrupt
```

Then run `--resume <run_id>`, with the `run_id` from the first line. Guess first: how many
contracts are left to do?

<!-- LIVE OUTPUT: resume line from the user's own run -->

The first line says `<n> of 10 docs to do`, where `n` is 10 minus the lines you saw before
Ctrl-C. The calls that were in flight when you pressed Ctrl-C were paid for, but not stored.
They are sent again.

## Step 4: a test for resume

**Why.** One more thing must stay true: a crash in one contract does not stop the others, and
resume redoes only what is missing.

Update the imports at the top of `tests/test_runner.py`:

```python
from docintel.core.llm import LLMResult
from docintel.domain.schema.fields import ContractFields
from docintel.evals import runner
from docintel.evals.store import connect
```

Add to the bottom of `tests/test_runner.py`:

```python
def test_resume_skips_done_docs_and_retries_crashed_ones(monkeypatch):
    def fake_extract(text, model, *, prompt_version):
        if text == "crash":
            raise TimeoutError("network down")
        return result(PRED)

    monkeypatch.setattr(runner, "extract", fake_extract)
    texts = {"d1": "ok", "d2": "crash", "d3": "ok"}
    with connect(":memory:") as con:
        con.execute(runner.TABLES)
        failed = runner.run_docs(con, "r1", texts, "fake", "v1", concurrency=2)
        left = runner.todo(con, "r1", list(texts))
        n_calls = con.execute("SELECT count(*) FROM llm_calls WHERE run_id = 'r1'").fetchone()
    assert failed == 1
    assert left == ["d2"]  # only the crashed doc is done again
    assert n_calls == (2,)
```

*Python here: [`monkeypatch.setattr`](./py/phase-1c2.md#py-5).*

Here, we:

1. Replace `extract` with a fake for this one test. The text `"crash"` raises an error, like a
   network that stays down.
2. Run three contracts in an in-memory database, two threads at a time.
3. Check that the run goes on after the crash and counts one failure.
4. Check that two calls were logged, and that `todo` returns only the crashed contract.

Checkpoint:

```sh
$ make lint && make test
All checks passed!
...
tests/test_data_load.py ....                                             [ 12%]
tests/test_extract.py ...                                                [ 21%]
tests/test_llm.py ....                                                   [ 33%]
tests/test_runner.py ...                                                 [ 42%]
tests/test_schema.py ....                                                [ 54%]
tests/test_scorers.py .........                                          [ 81%]
tests/test_smoke.py .                                                    [ 84%]
tests/test_splits.py .....                                               [100%]

============================== 33 passed in 0.57s ==============================
```

Your project should now look like this:

```
src/docintel/evals/
└── runner.py                  + todo, run_docs, parse_args, main
tests/
└── test_runner.py             3 tests
data/
└── docintel.duckdb            + the pilot runs, and soon E1
```

<details><summary>Full <code>src/docintel/evals/runner.py</code> (after 1c2)</summary>

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
from docintel.evals.scorers import score_doc
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
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    with connect() as con:
        con.execute(TABLES)
        if args.command == "score":
            print(f"scored {score(con, args.run_id)} docs for run {args.run_id}")
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

<details><summary>Full <code>tests/test_runner.py</code></summary>

```python
"""Runner rules with a fake extract. No network, no key, no CUAD files."""

from docintel.core.llm import LLMResult
from docintel.domain.schema.fields import ContractFields
from docintel.evals import runner
from docintel.evals.store import connect

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


def test_resume_skips_done_docs_and_retries_crashed_ones(monkeypatch):
    def fake_extract(text, model, *, prompt_version):
        if text == "crash":
            raise TimeoutError("network down")
        return result(PRED)

    monkeypatch.setattr(runner, "extract", fake_extract)
    texts = {"d1": "ok", "d2": "crash", "d3": "ok"}
    with connect(":memory:") as con:
        con.execute(runner.TABLES)
        failed = runner.run_docs(con, "r1", texts, "fake", "v1", concurrency=2)
        left = runner.todo(con, "r1", list(texts))
        n_calls = con.execute("SELECT count(*) FROM llm_calls WHERE run_id = 'r1'").fetchone()
    assert failed == 1
    assert left == ["d2"]  # only the crashed doc is done again
    assert n_calls == (2,)
```
</details>

## Break it on purpose

**Break 1: one crash stops everything.** In `run_docs`, replace the inner `try` / `except`
block with only `result = future.result()`. Guess what the test says:

```
>           raise TimeoutError("network down")
E           TimeoutError: network down
FAILED tests/test_runner.py::test_resume_skips_done_docs_and_retries_crashed_ones
========================= 1 failed, 32 passed in 0.62s =========================
```

One network error would end the whole run. The contracts after it would never be stored.
Change it back.

**Break 2 (thinking only): write from the threads.** Imagine you pass `con` to `extract`, so
each thread logs its own call. Why is that a problem?

<details><summary>Guess, then open</summary>

Several threads would use one DuckDB connection at the same time. DuckDB does not allow that for
one connection. Sometimes it works, sometimes a write fails or mixes up. That kind of bug is
the worst: it does not show up every time. One writer, the main thread, removes the risk.
</details>

## Experiment

This is E1: the baseline on the full dev split. 1c3 turns it into the results table.

Close the notebook connection, then run:

```sh
$ uv run python -m docintel.evals.runner run --split dev --parser cuad_txt --model qwen/qwen3-235b-a22b-2507 --prompt-version v1
```

The first line prints the `run_id` and an estimate of about $0.087. Answer `y`. If any call
failed, finish with `--resume <run_id>` until it says `52 of 52 docs scored`.

<!-- LIVE OUTPUT: E1 summary line and run_id from the user's own run -->

Then check the run in the notebook. Put your `run_id` in `RUN`:

```python
RUN = "20261021-HHMMSS"
con.sql("""
SELECT
    (SELECT count(*) FROM predictions WHERE run_id = $run) AS prediction_rows,
    (SELECT count(DISTINCT doc_id) FILTER (WHERE NOT ok) FROM predictions WHERE run_id = $run) AS bad_answers,
    (SELECT round(sum(cost_usd), 4) FROM llm_calls WHERE run_id = $run) AS cost_usd,
    (SELECT round(quantile_cont(latency_ms, 0.5) / 1000, 1) FROM llm_calls WHERE run_id = $run) AS p50_s,
    (SELECT round(quantile_cont(latency_ms, 0.95) / 1000, 1) FROM llm_calls WHERE run_id = $run) AS p95_s,
    (SELECT sum(tp) FROM scores WHERE run_id = $run) AS tp,
    (SELECT sum(fp) FROM scores WHERE run_id = $run) AS fp,
    (SELECT sum(fn) FROM scores WHERE run_id = $run) AS fn
""", params={"run": RUN})
```

*SQL here: `quantile_cont` is from [0c PY-7](./py/phase-0c.md#py-7).*

<!-- LIVE OUTPUT: E1 check table from the user's own run -->

Expect one row with 8 columns:

- `prediction_rows` is 624: 52 contracts times 12 fields. Anything else means a contract is
  missing.
- `bad_answers` is a small number, often 0.
- `cost_usd` is near the estimate. `p95_s` is much bigger than `p50_s`: long contracts are slow.
- `tp`, `fp`, `fn` are the sums over all fields. 1c3 splits them per field.

Start the E1 entry in `EXPERIMENTS.md` now. 1c3 fills in the results and the conclusion.

```markdown
## E1: baseline extraction on clean text
- **Date:**
- **run_id(s):** <E1 run_id> (pilot: <pilot run_id>)
- **Question / hypothesis:** How well does Qwen3-235B with prompt v1 find the 12 fields on clean
  CUAD text? Which fields are weak?
- **Data:** dev, 52 contracts, 12 fields, CUAD .txt (clean)
- **Setup:** qwen/qwen3-235b-a22b-2507, parser cuad_txt, prompt v1, temperature 0, no validation
  retries. Bad answers scored as: <your 1c Step 3 decision>
- **Results:** cost <total> (estimate <est>), p50 <s>, p95 <s>, bad answers <n>. P/R per field
  and per group: see 1c3.
- **Conclusion:** (1c3)
- **Next step:** (1c3)
```

## Gotchas

- **The database is locked.** DuckDB allows one writer. Close the notebook connection (or the
  other terminal) before a run.
- **`--resume` ignores your flags.** It uses the setup stored in `runs`. To change the model,
  start a new run.
- **Ctrl-C costs a little.** Calls in flight are paid for, but not stored. `llm_calls` and the
  OpenRouter bill count them, so a run's cost in `llm_calls` is the real cost.
- **`--resume` with a wrong `run_id`.** `fetchone()` returns `None`, and Python says `cannot
  unpack non-iterable NoneType object`. Copy the `run_id` from the first line of the run.
- **Never run on test now.** `--split test` exists for the final numbers in Phase 5. Every choice
  until then uses dev only.
- **Too many 429s.** If many lines take long or fail with `RateLimitError`, use
  `--concurrency 4`.

## Explain back, then commit

Explain each changed file to Claude in a few sentences (the rule in `PLAN.md`): `runner.py`
(`todo`, `run_docs` and its two kinds of failure, the threads, `main` and resume) and
`test_runner.py` (the new test). Show the E1 check table and your E1 entry. Then:

```sh
$ git status
$ git add src/docintel/evals/runner.py tests/test_runner.py EXPERIMENTS.md notebooks/00_explore.ipynb
$ git commit -m "phase 1c2: concurrent runner with resume and CLI, E1 run"
```

## Conclusion

What you have now:

- One command that runs any split with any model and prompt, 8 calls at a time.
- Resume that never pays twice for a stored answer.
- A pilot run that checks the estimate.
- E1: the first full dev run, with its cost and latency.

Go back to the objectives. Check that you can do each one without notes. Then answer:

1. Why does each worker thread call `extract` without `con`?
2. A call fails with a 400 error. What is stored, and what does `--resume` do with it?

Want more practice? Try these (optional):

1. Add a `--max-cost` flag that stops before the run if the estimate is higher.
2. Run the pilot with `--concurrency 1` and `--concurrency 8`. Compare the wall times and the
   p50 latency. Does p50 change?
3. Make `estimate` use the real characters per token from your pilot run in `llm_calls`.

Checklist (`../PLAN.md`): **Experiments: run_id, one change at a time, cost, p50/p95** (run_id,
cost and p50/p95 done; "one change at a time" comes with E1.1 in 1c4). **Retries, timeouts,
degradation, idempotency** (started: a crashed call does not stop the run, and resume never
stores a contract twice).
