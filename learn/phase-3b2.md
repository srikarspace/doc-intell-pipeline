# Phase 3b2: the experiment design and its wiring

In this part, you design experiment E3. You decide what "better" means before you see any result. Then you connect
every parser to the Phase 2 pipeline, one piece at a time.

This is part 2 of 3 for Phase 3b. It needs 3b. It makes **no paid calls**.

## Words used in this part

Read these first. CER and condition are from 3b.

- **Cell**: one parser on one condition. Example: `deepseek_vl@mild`. A plain name like `pypdf` means clean.
- **Grid**: all the cells of the experiment, as a table of parsers and conditions.
- **Frozen set**: a list of contracts saved once, so that every run uses the same ones.
- **Noise floor**: how much F1 moves when nothing changed. Example: the same model scores 0.881 and 0.901.
- **Cost per document**: all the money spent on one contract. Example: parsing plus extraction.
- **Keep rule**: the test that decides the winner. You write it before the run (1d2).
- **Stage**: one separate part of a job. Here, parsing is one stage, and extraction is another.

## Objectives

By the end of this part you should be able to:

1. Choose the documents, the deciding metric and the costs that count, with evidence.
2. Say how large the noise floor is on your documents, and what that means for your rule.
3. Give Docling OCR its own parser name, and explain why.
4. Explain why a run reads only from the cache.
5. Print a CER table for each cell.

## Dependencies

You install nothing new. This part needs:

- 3b: `CONDITIONS`, `make_scan`, `scan_path`, `cer`.
- 3a3: `Budget`, `make_vision_parser`, and `page_costs` and `pick_docs` from `parse_pilot.py`.
- 3a2: `docling_parser.py`.
- 2b: the runner and `--retries`.

## The big picture

Before this part, the parsers worked alone, and the pipeline only knew `cuad_txt`.

After this part:

```text
frozen set (e3) -> fake scans -> parse stage (costs money, has a budget) -> cache
                                                                              |
                                  run stage: extract + validate + score, reads the cache only
```

- **3b3** starts these stages for real, and draws the chart.
- **Phase 4** uses your verdict to decide which parser handles a scan in production.

## Remember this

> Decide what "better" means before you see the numbers. If you decide afterwards, you will pick the rule that makes
> your favourite win. And with few contracts, F1 moves even when nothing changed. So a rule must ask for a gap bigger
> than that movement.
>
> **Write the rule first, and make it bigger than the noise.**

## Why

**Nine contracts is a small test.** One field changing moves F1 by more than 0.01. So we measure the noise first,
for free, from runs we already have.

**Parsing and extraction must be separate.** Parsing can cost money per page. Extraction costs money per contract.
A run that starts a paid parse by accident is the mistake that cost $0.46 in 3a3.

**The citation check must see the same text as the model.** In Phase 2, `validate` compared quotes with `cuad_txt`.
On a scan, the model read different text, so a quote must be checked against that text.

## Design decisions

- **A cell is one string, like `deepseek_vl@mild`.** It is the name in the cache and in `runs.parser`, so a number
  always traces to one cell. Other option: two columns, parser and condition. That means changing the `runs` table.
- **A clean cell keeps the plain name.** `deepseek_vl` is already in the cache, so the paid clean pages are reused.
  Other option: rename to `deepseek_vl@clean`. You would pay again, or need a migration.
- **The frozen set is a table.** Other option: call `pick_docs` each time. A change to the page cap would silently
  change the documents.
- **A set is reached with `--split e3`.** `--resume` already remembers `split`, so it keeps working. Other option: a
  new `--docs` flag and a new column.
- **A run reads only from the cache, and fails if the text is missing.** Other option: parse inside the run. One
  command could then spend money that you did not plan.
- **`docling_ocr` is a new parser name.** The cache key is the name, so OCR text cannot mix with non-OCR text (3a2).
  Other option: a setting. Changing it would return the old text.
- **The OCR engine is pinned.** Other option: `auto`, which picks by what is installed. Results could change on
  another machine, such as the Docker image in Phase 4.

## Worked example

These are real numbers from your database. Guess before you open each box.

### Round 1: how much does F1 move when nothing changes?

Your stored runs used the same model and prompt on `cuad_txt`. On the 9 contracts of the 3a3 pilot:

| Run | Provider | tp | fp | fn | F1 |
|---|---|---|---|---|---|
| `20261102-200003` | Crusoe | 41 | 7 | 2 | ? |
| `20261105-213036` | Parasail | 37 | 4 | 6 | ? |
| `20261108-062221` | Parasail | 37 | 4 | 6 | ? |

Guess the gap between the highest and the lowest F1.

<details><summary>Guess, then open</summary>

F1 is 0.901, 0.881 and 0.881. The gap is **0.02**, and only the provider changed. On all 52 contracts, the same runs
give 0.912, 0.907 and 0.903, a gap of 0.009. Fewer contracts mean more movement.
</details>

### Round 2: what is one field worth?

Take the run with tp 37, fp 4, fn 6. One right answer becomes a miss. So tp is 36, and fn is 7. Guess the new F1.

<details><summary>Guess, then open</summary>

0.881 becomes **0.867**. One field out of 108 moves F1 by 0.014. A rule that says "keep if F1 is higher" would change
its answer with a single field.
</details>

### Round 3: where does the money go?

From the real rows: a vision parse is $0.0234 per contract. Extraction on the same contracts was $0.00135 per contract.
Guess the share of the bill that is parsing.

<details><summary>Guess, then open</summary>

About **95%**. So for a vision cell, the extraction cost almost does not matter. For free parsers, extraction is the
whole bill. That is why the chart needs the total.
</details>

## Project setup

```sh
touch src/docintel/evals/parser_experiment.py
touch tests/test_parser_experiment.py
```

You should now have:

```text
src/docintel/evals/
└── parser_experiment.py        # new
tests/
└── test_parser_experiment.py   # new
```

## Step 1: design the experiment (your decision)

**Why.** Every later step follows from these choices.

Write all of them in `EXPERIMENTS.md`, under `## E3`. Then commit, before any run.

**Which documents.** At most 20 pages each, dev only.

| Option | Docs | Pages | Vision per scan condition (usual) | Clean vision | Label quotes |
|---|---|---|---|---|---|
| 3a3 pilot set | 9 | 69 | $0.22 | already paid | 158 quotes |
| All that fit the cap | 34 | 235 | about $0.74 | $0.53 more | not counted |

**What decides "better".** Options: F1 on all 12 fields; recall only; quotes found; CER. Remember 3b, Round 3: CER can
disagree with quotes.

**Which costs count.** Options: parse only; parse plus extraction; also the time of your machine. Docling is free in
money, and slow: real value is about 10 s per page on an 8 GB Mac, with 1.5 GB of memory. On Cloud Run, memory and time
are money. Say how you handle that.

**Which cells.** Options: the reference is `cuad_txt` on the same docs. Clean: `pypdf`, `docling`, `deepseek_vl`. Per
scan condition: `pypdf`, `docling_ocr`, `deepseek_vl`.

**Your keep rule.** Say when you would pay for vision on scans. Use the noise floor from Round 1.

<details><summary>Reference (open after you write yours)</summary>

- **Documents:** the 9 pilot docs. Clean vision is already paid for. The cost is small, and we say clearly that it is a
  small test.
- **Deciding metric:** F1 on all 12 fields. It measures what the product returns. CER is only used to explain results.
- **Costs that count:** parse plus extraction plus retries, per contract. Time per page is a separate column, and it
  goes to Phase 4.
- **Cells:** all 10 listed above, with `cuad_txt`.
- **Keep rule:** for each scan condition, use vision only if its F1 beats `docling_ocr` by at least 0.05 (more than
  twice the noise floor), and no page failed. If the gap is smaller, use free OCR.
</details>

Commit your rule alone:

```sh
git add EXPERIMENTS.md
git commit -m "E3 design and keep rule, before any run"
```

## Step 2: a parser for Docling with OCR (your decision)

**Why.** A scan has no text layer, so Docling needs OCR for it.

You decide the OCR engine.

| Engine | Works here | Works in Docker on Linux | Notes |
|---|---|---|---|
| RapidOCR, torch backend | yes, already installed | yes | used for all numbers in these docs |
| macOS Vision (`ocrmac`) | needs install | no | Mac only |
| Tesseract | needs a system program | yes, with an apt package | not tested here |
| `auto` | yes, picks RapidOCR now | depends | can change when something new is installed |

Write your choice in `EXPERIMENTS.md`, under `## E3`.

<details><summary>Reference (open after you write yours)</summary>

RapidOCR with the torch backend. It works here and in the Docker image. Pinning it means the result does not depend on
what else is installed.

Update `get_converter` in `src/docintel/domain/parse/docling_parser.py`:

```python
@lru_cache
def get_converter(do_ocr: bool = DO_OCR):
    """Build each converter once. The imports are here so that importing this file stays fast."""
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions, RapidOcrOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption

    options = PdfPipelineOptions(do_ocr=do_ocr, do_table_structure=DO_TABLES)
    if do_ocr:
        options.ocr_options = RapidOcrOptions(backend="torch")
    return DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)}
    )
```

Then replace `parse_docling` at the bottom of the same file:

```python
def run_docling(pdf_path: Path, do_ocr: bool, parser_name: str) -> ParsedDoc:
    start = time.perf_counter()
    result = get_converter(do_ocr).convert(pdf_path)
    pages = pages_of(result.document, result.input.page_count)
    latency_ms = round((time.perf_counter() - start) * 1000)
    return from_pages(pages, cost_usd=0.0, latency_ms=latency_ms, parser_name=parser_name)


def parse_docling(pdf_path: Path) -> ParsedDoc:
    return run_docling(pdf_path, do_ocr=False, parser_name="docling")


def parse_docling_ocr(pdf_path: Path) -> ParsedDoc:
    return run_docling(pdf_path, do_ocr=True, parser_name="docling_ocr")
```

In `src/docintel/domain/parse/__init__.py`, update the import:

```python
from docintel.domain.parse.docling_parser import parse_docling, parse_docling_ocr
```

Then add one line to `PARSERS`, after `"docling"`:

```python
    "docling_ocr": parse_docling_ocr,
```
</details>

*Python here: [`lru_cache` with an argument](./py/phase-3b2.md#py-1).*

Here, we:

1. Keep one converter per value of `do_ocr`, so the models load only once for each.
2. Share one `run_docling`, so the two parsers can only differ in `do_ocr` and in their name.

Checkpoint:

```sh
uv run pytest tests/test_docling_parser.py -q
```

```text
..                                                                       [100%]
2 passed in 0.66s
```

The second test checks that importing the parsers does not load torch. It must still pass.

## Step 3: freeze the documents

**Why.** The documents must not move between runs.

Add this table at the end of `TABLES` in `src/docintel/evals/runner.py`, before the closing `"""`:

```sql
CREATE TABLE IF NOT EXISTS eval_sets (
    set_name VARCHAR, doc_id VARCHAR, PRIMARY KEY (set_name, doc_id)
);
```

In the same file, replace `docs_for`:

```python
def docs_for(con: duckdb.DuckDBPyConnection, split: str) -> list[str]:
    """The doc_ids of one split, always in the same order."""
    rows = con.execute(
        "SELECT doc_id FROM splits WHERE split = $s "
        "UNION ALL SELECT doc_id FROM eval_sets WHERE set_name = $s ORDER BY doc_id",
        {"s": split},
    )
    return [doc_id for (doc_id,) in rows.fetchall()]
```

And in `parse_args`, change the choices of `--split`:

```python
    run.add_argument("--split", choices=["dev", "test", "e3"], default="dev")
```

Put this in `src/docintel/evals/parser_experiment.py`. Some imports stay unused until Step 6, so `ruff` may complain
until then:

```python
"""E3: freeze the docs, make the fake scans, parse them, and check the text."""

import argparse
from datetime import datetime
from pathlib import Path

import duckdb

from docintel.domain.parse import PARSERS
from docintel.domain.parse.base import ParsedDoc
from docintel.domain.parse.cache import cache_path, cached_parse
from docintel.domain.parse.scan import CONDITIONS, make_scan, scan_path
from docintel.domain.parse.vision import MODELS, Budget, BudgetExceeded, make_vision_parser
from docintel.domain.validate.citations import quote_status, words
from docintel.evals.cer import cer
from docintel.evals.parse_pilot import page_costs, pick_docs
from docintel.evals.runner import CELLS, TABLES
from docintel.evals.store import connect

SET_NAME = "e3"


def split_cell(cell: str) -> tuple[str, str]:
    """'deepseek_vl@mild' -> ('deepseek_vl', 'mild'). A plain name is the clean condition."""
    parser, _, condition = cell.partition("@")
    return parser, condition or "clean"


def freeze(con: duckdb.DuckDBPyConnection, per_band: int) -> list[str]:
    """Save the E3 docs once. A frozen set can never change without a clear error."""
    chosen = sorted(d[0] for d in pick_docs(con, per_band))
    rows = con.execute("SELECT doc_id FROM eval_sets WHERE set_name = ?", [SET_NAME]).fetchall()
    saved = sorted(doc_id for (doc_id,) in rows)
    if saved and saved != chosen:
        raise SystemExit(f"set {SET_NAME} is frozen with {len(saved)} other docs")
    if not saved:
        con.executemany("INSERT INTO eval_sets VALUES (?, ?)", [(SET_NAME, d) for d in chosen])
    return chosen


def frozen_docs(con: duckdb.DuckDBPyConnection, limit: int | None = None) -> list[tuple]:
    """(doc_id, pdf_path, txt_path, n_pages), the shortest first, so --limit stays cheap."""
    rows = con.execute(
        "SELECT doc_id, pdf_path, txt_path, n_pages FROM eval_sets JOIN contracts USING (doc_id) "
        "WHERE set_name = ? ORDER BY n_pages, doc_id",
        [SET_NAME],
    ).fetchall()
    return rows[:limit]
```

Here, we:

1. Read the docs from `splits`, or from `eval_sets`. A name exists in only one table, so one query covers both.
2. Reuse `pick_docs` from 3a3, which uses dev only.
3. Refuse to change a set once it is saved. If you want other documents, you must use another set name.
4. Order by length, so a `--limit` run stays small and cheap.

`CELLS` does not exist yet, so nothing can run until Step 4.

## Step 4: the cells, and text from the cache only

**Why.** The runner must find each cell's text, and must never start a parse.

Update the imports in `src/docintel/evals/runner.py`, after the `log_call` import and the `domain.extract` ones:

```python
from docintel.domain.parse.base import ParsedDoc
from docintel.domain.parse.cache import CACHE_DIR, cache_path
from docintel.domain.parse.scan import CONDITIONS
```

Then replace the line `PARSERS = {"cuad_txt": cuad_txt}` in the same file:

```python
CLEAN_CELLS = ["pypdf", "docling", "deepseek_vl"]
SCAN_PARSERS = ["pypdf", "docling_ocr", "deepseek_vl"]
CELLS = CLEAN_CELLS + [f"{p}@{c}" for c in CONDITIONS for p in SCAN_PARSERS]


def cached_text(cell: str, doc_id: str, cache_dir: Path = CACHE_DIR) -> str:
    """The stored text of one cell. A run reads it, and can never start a paid parse."""
    path = cache_path(cell, doc_id, cache_dir)
    if not path.exists():
        raise FileNotFoundError(f"no parse for {cell} / {doc_id}: run the parse stage first")
    return ParsedDoc.model_validate_json(path.read_text(encoding="utf-8")).text


def text_of(cell: str):
    def read(con: duckdb.DuckDBPyConnection, doc_id: str) -> str:
        return cached_text(cell, doc_id)

    return read


PARSERS = {"cuad_txt": cuad_txt, **{cell: text_of(cell) for cell in CELLS}}
```

*Python here: [a function per cell](./py/phase-3b2.md#py-2).*

Here, we:

1. Build the names: 3 clean cells, and 3 parsers for each condition.
2. Read a cell's text from the cache. If it is missing, stop with a clear message.
3. Add each cell to `PARSERS`. Now `run` and `validate` both use the text that the cell really produced.

Checkpoint (free). Guess first: does it ask to start?

```sh
uv run python -m docintel.evals.runner run --split dev --parser pypdf@mild --limit 1
```

The last line of the error (the first dev contract):

```text
FileNotFoundError: no parse for pypdf@mild / 2ThemartComInc_19990826_10-12G_EX-10.10_6700288_EX-10.10_Co-Branding Agreement_ Agency Agreement: run the parse stage first
```

It stops before the question. This error is what you want to see: no parse, so no run, and nothing is spent.

## Step 5: make the scans

**Why.** The parse stage needs one fake scan per document and condition.

Add to the bottom of `src/docintel/evals/parser_experiment.py`:

```python
def make_scans(docs: list[tuple]) -> None:
    for condition in CONDITIONS:
        for doc_id, pdf_path, _, _ in docs:
            path = scan_path(doc_id, condition)
            if not path.exists():
                make_scan(Path(pdf_path), path, doc_id, condition)
        print(f"{condition}: {len(docs)} scans in {scan_path('x', condition).parent}")


def pdf_for(cell: str, doc_id: str, pdf_path: str) -> Path:
    _, condition = split_cell(cell)
    return Path(pdf_path) if condition == "clean" else scan_path(doc_id, condition)


def pages_to_parse(cell: str, docs: list[tuple]) -> int:
    return sum(n for doc_id, _, _, n in docs if not cache_path(cell, doc_id).exists())
```

Here, `pdf_for` chooses the input: the real PDF for a clean cell, and the fake scan for the others. A scan that is
already on disk is not made again.

## Step 6: the parse stage, and the CER table

**Why.** This is the only stage that can spend money on pages, so it shows the cost first.

Add to the bottom of `src/docintel/evals/parser_experiment.py`:

```python
def parse_cells(cells: list[str], docs: list[tuple], limit_usd: float, yes: bool) -> None:
    """Parse each cell. Paid cells show their cost first, and share one budget."""
    paid = {c: split_cell(c)[0] for c in cells if split_cell(c)[0] in MODELS}
    costs = {p: page_costs(p) for p in set(paid.values())}
    for cell, parser in paid.items():
        usual, worst = costs[parser]
        n = pages_to_parse(cell, docs)
        print(f"{cell}: {n} pages to pay for, usual ${usual * n:.4f}, worst ${worst * n:.4f}")
    if paid and not yes and input("Start? [y/N] ").strip().lower() != "y":
        return
    run_id = f"e3-parse-{datetime.now():%Y%m%d-%H%M%S}"
    budget = Budget(limit_usd)
    try:
        for cell in cells:
            name = split_cell(cell)[0]
            parser = PARSERS[name]
            if name in MODELS:
                parser = make_vision_parser(
                    name, run_id=run_id, budget=budget, worst_page_usd=costs[name][1]
                )
            for doc_id, pdf_path, _, _ in docs:
                doc = cached_parse(cell, doc_id, pdf_for(cell, doc_id, pdf_path), parser)
                print(f"{cell:20} {doc_id[:36]:36} {len(doc.pages):3} pages")
    except BudgetExceeded as e:
        print("stopped:", e)
    print(f"run {run_id}, spent now ${budget.spent:.4f}")


def cell_stats(cell: str, docs: list[tuple], spans: dict[str, list[str]]) -> dict | None:
    """How good the text of one cell is. None if some doc is not parsed yet."""
    paths = [cache_path(cell, d[0]) for d in docs]
    if not all(p.exists() for p in paths):
        return None
    parsed = [ParsedDoc.model_validate_json(p.read_text(encoding="utf-8")) for p in paths]
    refs = [Path(d[2]).read_text(encoding="utf-8") for d in docs]
    found = total = 0
    for p, d in zip(parsed, docs, strict=True):
        source = words(p.text)
        status = [quote_status(s, source) for s in spans[d[0]]]
        found += sum(s in ("same_words", "gap") for s in status)
        total += len(status)
    return {
        "cer": sum(cer(p.text, r) for p, r in zip(parsed, refs, strict=True)) / len(docs),
        "found": found,
        "total": total,
        "parse_usd": sum(p.cost_usd for p in parsed) / len(docs),
        "s_page": sum(p.latency_ms for p in parsed)
        / 1000
        / max(sum(len(p.pages) for p in parsed), 1),
    }


def all_spans(con: duckdb.DuckDBPyConnection, docs: list[tuple]) -> dict[str, list[str]]:
    spans = {}
    for d in docs:
        rows = con.execute(
            "SELECT span_text FROM labels WHERE doc_id = ? AND is_present "
            "AND span_text IS NOT NULL",
            [d[0]],
        ).fetchall()
        spans[d[0]] = [s for (s,) in rows]
    return spans


def text_report(con: duckdb.DuckDBPyConnection, docs: list[tuple]) -> None:
    spans = all_spans(con, docs)
    print(f"{'cell':20} {'docs':>4} {'CER':>6} {'quotes':>9} {'$/doc':>8} {'s/page':>7}")
    for cell in CELLS:
        s = cell_stats(cell, docs, spans)
        if s:
            quotes = f"{s['found']}/{s['total']}"
            print(
                f"{cell:20} {len(docs):4} {s['cer']:6.3f} {quotes:>9} "
                f"${s['parse_usd']:7.4f} {s['s_page']:7.2f}"
            )
```

*Python here: [`dict` of costs, `set`](./py/phase-3b2.md#py-3).*

Here, in `parse_cells`, in order:

1. Find the paid cells, and read the provider's price.
2. Print the pages to pay for: the cached ones cost nothing.
3. Ask. The answer is `n` unless you say yes.
4. Parse with one shared `Budget`, so all paid cells stop at one limit.

`cell_stats` returns numbers, not text, because 3b3 reads them too.

The last part of the file is the command line. It is boilerplate, so copy it.

<details><summary>Add to the bottom of <code>src/docintel/evals/parser_experiment.py</code></summary>

```python
def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(prog="python -m docintel.evals.parser_experiment")
    sub = ap.add_subparsers(dest="command", required=True)
    f = sub.add_parser("freeze", help="save the E3 docs")
    f.add_argument("--per-band", type=int, default=3)
    sub.add_parser("scans", help="make the fake scans")
    p = sub.add_parser("parse", help="parse some cells, cost first")
    p.add_argument("--cells", nargs="+", required=True, choices=CELLS)
    p.add_argument("--budget", type=float, required=True, help="stop before passing this, in USD")
    p.add_argument("--limit", type=int, help="only the N shortest docs")
    p.add_argument("--yes", action="store_true")
    t = sub.add_parser("text", help="CER, quotes, cost and speed per cell")
    t.add_argument("--limit", type=int)
    return ap.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    with connect() as con:
        con.execute(TABLES)
        if args.command == "freeze":
            docs = freeze(con, args.per_band)
            print(f"{SET_NAME}: {len(docs)} docs frozen")
            return
        docs = frozen_docs(con, getattr(args, "limit", None))
        if args.command == "text":
            text_report(con, docs)
            return
    # the DuckDB file is closed here, so the parsers can open it
    if args.command == "scans":
        make_scans(docs)
    else:
        parse_cells(args.cells, docs, args.budget, args.yes)


if __name__ == "__main__":
    main()
```

3b3 adds one more command here.
</details>

Checkpoint 1: freeze, scan and parse the free cell. No paid call.

```sh
uv run python -m docintel.evals.parser_experiment freeze --per-band 3
uv run python -m docintel.evals.parser_experiment scans
uv run python -m docintel.evals.parser_experiment parse --cells pypdf@mild pypdf@heavy --budget 0
uv run python -m docintel.evals.parser_experiment text
```

```text
e3: 9 docs frozen
mild: 9 scans in data/scans/mild
heavy: 9 scans in data/scans/heavy
...
run e3-parse-20261108-214650, spent now $0.0000
cell                 docs    CER    quotes    $/doc  s/page
pypdf                   9  0.003  156/158  $ 0.0000    0.01
docling                 9  0.015  157/158  $ 0.0000    1.09
deepseek_vl             9  0.007  153/158  $ 0.0234    8.66
pypdf@mild              9  1.000    0/158  $ 0.0000    0.00
pypdf@heavy             9  1.000    0/158  $ 0.0000    0.00
```

The clean numbers should look familiar. They match the E3.0 quote counts.

Checkpoint 2: Docling OCR on the two shortest contracts. It is free, but it loads models. Check your memory first, as
in 3a2. Close other programs.

```sh
uv run python -m docintel.evals.parser_experiment parse --cells docling_ocr@mild docling_ocr@heavy --limit 2 --budget 0
uv run python -m docintel.evals.parser_experiment text --limit 2
```

```text
cell                 docs    CER    quotes    $/doc  s/page
pypdf                   2  0.001     22/24  $ 0.0000    0.01
docling                 2  0.011     24/24  $ 0.0000   10.56
deepseek_vl             2  0.010     22/24  $ 0.0106   12.45
pypdf@mild              2  1.000      0/24  $ 0.0000    0.00
docling_ocr@mild        2  0.074     23/24  $ 0.0000   10.29
pypdf@heavy             2  1.000      0/24  $ 0.0000    0.00
docling_ocr@heavy       2  0.258      8/24  $ 0.0000    7.23
```

The peak memory in that run was 1.48 GB. On a short set, a model load is a large part of `s/page`.

Checkpoint 3: see the paid estimate. Type `n`.

```sh
uv run python -m docintel.evals.parser_experiment parse --cells deepseek_vl@mild deepseek_vl@heavy --budget 1.20
```

```text
deepseek_vl@mild: 69 pages to pay for, usual $0.2184, worst $1.0172
deepseek_vl@heavy: 69 pages to pay for, usual $0.2184, worst $1.0172
Start? [y/N] n
```

Checkpoint 4: a run with nothing in the cache stops. Type `n` if it asks. It spends nothing.

```sh
uv run python -m docintel.evals.runner run --split e3 --parser deepseek_vl@mild
```

```text
FileNotFoundError: no parse for deepseek_vl@mild / BORROWMONEYCOM,INC_06_11_2020-EX-10.1-JOINT VENTURE AGREEMENT: run the parse stage first
```

## Step 7: a small test

**Why.** These rules keep the experiment fair and keep your money safe.

The test names say what is protected: a missing parse stops the run, a run cannot start a parse, every cell has its
own cache folder, a frozen set holds only dev docs, and it cannot change.

<details><summary>Put this in <code>tests/test_parser_experiment.py</code></summary>

```python
"""E3 wiring: the rules that keep the parser experiment fair and free of surprise costs."""

import pytest

from docintel.domain.parse.cache import cache_path
from docintel.evals.parser_experiment import SET_NAME, freeze, split_cell
from docintel.evals.runner import CELLS, PARSERS, TABLES, cached_text, docs_for
from docintel.evals.store import connect


@pytest.fixture
def con(tmp_path):
    with connect(tmp_path / "t.duckdb") as c:
        c.execute(TABLES)
        c.execute(
            "CREATE TABLE contracts (doc_id VARCHAR, pdf_path VARCHAR, txt_path VARCHAR, "
            "n_pages INTEGER)"
        )
        c.execute("CREATE TABLE splits (doc_id VARCHAR, split VARCHAR)")
        for n, (doc_id, split) in enumerate(
            [("a", "dev"), ("b", "dev"), ("c", "dev"), ("hidden", "test")], start=1
        ):
            c.execute("INSERT INTO contracts VALUES (?, 'p', 't', ?)", [doc_id, n])
            c.execute("INSERT INTO splits VALUES (?, ?)", [doc_id, split])
        yield c


def test_a_missing_parse_stops_the_run(tmp_path):
    with pytest.raises(FileNotFoundError, match="run the parse stage"):
        cached_text("deepseek_vl@mild", "doc-1", tmp_path)


def test_a_run_cannot_start_a_parse(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # an empty folder, so nothing is cached here
    with pytest.raises(FileNotFoundError, match="run the parse stage"):
        PARSERS["deepseek_vl@mild"](None, "doc-1")


def test_every_cell_has_its_own_cache_folder():
    paths = {cache_path(cell, "doc-1") for cell in CELLS}
    assert len(paths) == len(CELLS)


def test_clean_cells_use_the_plain_names():
    assert split_cell("pypdf") == ("pypdf", "clean")
    assert split_cell("deepseek_vl@heavy") == ("deepseek_vl", "heavy")


def test_the_frozen_set_has_only_dev_docs(con):
    docs = freeze(con, per_band=5)
    assert "hidden" not in docs
    assert docs_for(con, SET_NAME) == sorted(docs)
    assert docs_for(con, "test") == ["hidden"]


def test_a_frozen_set_cannot_change(con):
    freeze(con, per_band=1)
    con.execute("DELETE FROM eval_sets WHERE doc_id = 'a'")
    with pytest.raises(SystemExit, match="frozen"):
        freeze(con, per_band=5)
```
</details>

Checkpoint:

```sh
uv run pytest tests/test_parser_experiment.py -q
make test
```

```text
......                                                                   [100%]
6 passed in 0.49s
```

`make test` must be green. The older runner tests still pass, because `eval_sets` is empty there.

Your project structure should now look like this:

```text
src/docintel/
├── domain/parse/
│   ├── __init__.py              # PARSERS has docling_ocr
│   └── docling_parser.py        # do_ocr, run_docling, parse_docling_ocr
└── evals/
    ├── parser_experiment.py     # freeze, scans, parse, text
    └── runner.py                # eval_sets, CELLS, cached_text
tests/
└── test_parser_experiment.py
```

<details><summary>Complete <code>src/docintel/evals/parser_experiment.py</code> (as of this part)</summary>

```python
"""E3: freeze the docs, make the fake scans, parse them, and check the text."""

import argparse
from datetime import datetime
from pathlib import Path

import duckdb

from docintel.domain.parse import PARSERS
from docintel.domain.parse.base import ParsedDoc
from docintel.domain.parse.cache import cache_path, cached_parse
from docintel.domain.parse.scan import CONDITIONS, make_scan, scan_path
from docintel.domain.parse.vision import MODELS, Budget, BudgetExceeded, make_vision_parser
from docintel.domain.validate.citations import quote_status, words
from docintel.evals.cer import cer
from docintel.evals.parse_pilot import page_costs, pick_docs
from docintel.evals.runner import CELLS, TABLES
from docintel.evals.store import connect

SET_NAME = "e3"


def split_cell(cell: str) -> tuple[str, str]:
    """'deepseek_vl@mild' -> ('deepseek_vl', 'mild'). A plain name is the clean condition."""
    parser, _, condition = cell.partition("@")
    return parser, condition or "clean"


def freeze(con: duckdb.DuckDBPyConnection, per_band: int) -> list[str]:
    """Save the E3 docs once. A frozen set can never change without a clear error."""
    chosen = sorted(d[0] for d in pick_docs(con, per_band))
    rows = con.execute("SELECT doc_id FROM eval_sets WHERE set_name = ?", [SET_NAME]).fetchall()
    saved = sorted(doc_id for (doc_id,) in rows)
    if saved and saved != chosen:
        raise SystemExit(f"set {SET_NAME} is frozen with {len(saved)} other docs")
    if not saved:
        con.executemany("INSERT INTO eval_sets VALUES (?, ?)", [(SET_NAME, d) for d in chosen])
    return chosen


def frozen_docs(con: duckdb.DuckDBPyConnection, limit: int | None = None) -> list[tuple]:
    """(doc_id, pdf_path, txt_path, n_pages), the shortest first, so --limit stays cheap."""
    rows = con.execute(
        "SELECT doc_id, pdf_path, txt_path, n_pages FROM eval_sets JOIN contracts USING (doc_id) "
        "WHERE set_name = ? ORDER BY n_pages, doc_id",
        [SET_NAME],
    ).fetchall()
    return rows[:limit]


def make_scans(docs: list[tuple]) -> None:
    for condition in CONDITIONS:
        for doc_id, pdf_path, _, _ in docs:
            path = scan_path(doc_id, condition)
            if not path.exists():
                make_scan(Path(pdf_path), path, doc_id, condition)
        print(f"{condition}: {len(docs)} scans in {scan_path('x', condition).parent}")


def pdf_for(cell: str, doc_id: str, pdf_path: str) -> Path:
    _, condition = split_cell(cell)
    return Path(pdf_path) if condition == "clean" else scan_path(doc_id, condition)


def pages_to_parse(cell: str, docs: list[tuple]) -> int:
    return sum(n for doc_id, _, _, n in docs if not cache_path(cell, doc_id).exists())


def parse_cells(cells: list[str], docs: list[tuple], limit_usd: float, yes: bool) -> None:
    """Parse each cell. Paid cells show their cost first, and share one budget."""
    paid = {c: split_cell(c)[0] for c in cells if split_cell(c)[0] in MODELS}
    costs = {p: page_costs(p) for p in set(paid.values())}
    for cell, parser in paid.items():
        usual, worst = costs[parser]
        n = pages_to_parse(cell, docs)
        print(f"{cell}: {n} pages to pay for, usual ${usual * n:.4f}, worst ${worst * n:.4f}")
    if paid and not yes and input("Start? [y/N] ").strip().lower() != "y":
        return
    run_id = f"e3-parse-{datetime.now():%Y%m%d-%H%M%S}"
    budget = Budget(limit_usd)
    try:
        for cell in cells:
            name = split_cell(cell)[0]
            parser = PARSERS[name]
            if name in MODELS:
                parser = make_vision_parser(
                    name, run_id=run_id, budget=budget, worst_page_usd=costs[name][1]
                )
            for doc_id, pdf_path, _, _ in docs:
                doc = cached_parse(cell, doc_id, pdf_for(cell, doc_id, pdf_path), parser)
                print(f"{cell:20} {doc_id[:36]:36} {len(doc.pages):3} pages")
    except BudgetExceeded as e:
        print("stopped:", e)
    print(f"run {run_id}, spent now ${budget.spent:.4f}")


def cell_stats(cell: str, docs: list[tuple], spans: dict[str, list[str]]) -> dict | None:
    """How good the text of one cell is. None if some doc is not parsed yet."""
    paths = [cache_path(cell, d[0]) for d in docs]
    if not all(p.exists() for p in paths):
        return None
    parsed = [ParsedDoc.model_validate_json(p.read_text(encoding="utf-8")) for p in paths]
    refs = [Path(d[2]).read_text(encoding="utf-8") for d in docs]
    found = total = 0
    for p, d in zip(parsed, docs, strict=True):
        source = words(p.text)
        status = [quote_status(s, source) for s in spans[d[0]]]
        found += sum(s in ("same_words", "gap") for s in status)
        total += len(status)
    return {
        "cer": sum(cer(p.text, r) for p, r in zip(parsed, refs, strict=True)) / len(docs),
        "found": found,
        "total": total,
        "parse_usd": sum(p.cost_usd for p in parsed) / len(docs),
        "s_page": sum(p.latency_ms for p in parsed)
        / 1000
        / max(sum(len(p.pages) for p in parsed), 1),
    }


def all_spans(con: duckdb.DuckDBPyConnection, docs: list[tuple]) -> dict[str, list[str]]:
    spans = {}
    for d in docs:
        rows = con.execute(
            "SELECT span_text FROM labels WHERE doc_id = ? AND is_present "
            "AND span_text IS NOT NULL",
            [d[0]],
        ).fetchall()
        spans[d[0]] = [s for (s,) in rows]
    return spans


def text_report(con: duckdb.DuckDBPyConnection, docs: list[tuple]) -> None:
    spans = all_spans(con, docs)
    print(f"{'cell':20} {'docs':>4} {'CER':>6} {'quotes':>9} {'$/doc':>8} {'s/page':>7}")
    for cell in CELLS:
        s = cell_stats(cell, docs, spans)
        if s:
            quotes = f"{s['found']}/{s['total']}"
            print(
                f"{cell:20} {len(docs):4} {s['cer']:6.3f} {quotes:>9} "
                f"${s['parse_usd']:7.4f} {s['s_page']:7.2f}"
            )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(prog="python -m docintel.evals.parser_experiment")
    sub = ap.add_subparsers(dest="command", required=True)
    f = sub.add_parser("freeze", help="save the E3 docs")
    f.add_argument("--per-band", type=int, default=3)
    sub.add_parser("scans", help="make the fake scans")
    p = sub.add_parser("parse", help="parse some cells, cost first")
    p.add_argument("--cells", nargs="+", required=True, choices=CELLS)
    p.add_argument("--budget", type=float, required=True, help="stop before passing this, in USD")
    p.add_argument("--limit", type=int, help="only the N shortest docs")
    p.add_argument("--yes", action="store_true")
    t = sub.add_parser("text", help="CER, quotes, cost and speed per cell")
    t.add_argument("--limit", type=int)
    return ap.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    with connect() as con:
        con.execute(TABLES)
        if args.command == "freeze":
            docs = freeze(con, args.per_band)
            print(f"{SET_NAME}: {len(docs)} docs frozen")
            return
        docs = frozen_docs(con, getattr(args, "limit", None))
        if args.command == "text":
            text_report(con, docs)
            return
    # the DuckDB file is closed here, so the parsers can open it
    if args.command == "scans":
        make_scans(docs)
    else:
        parse_cells(args.cells, docs, args.budget, args.yes)


if __name__ == "__main__":
    main()
```
</details>

<details><summary>Complete <code>src/docintel/domain/parse/docling_parser.py</code></summary>

```python
"""Parser 2: Docling. Local layout and OCR models, free but slow."""

import time
from functools import lru_cache
from pathlib import Path

from docintel.domain.parse.base import ParsedDoc, from_pages

DO_OCR = False  # native PDFs have a text layer; 3b turns this on for scans
DO_TABLES = False  # one contract lost a quote with tables on; 3b can test this


@lru_cache
def get_converter(do_ocr: bool = DO_OCR):
    """Build each converter once. The imports are here so that importing this file stays fast."""
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions, RapidOcrOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption

    options = PdfPipelineOptions(do_ocr=do_ocr, do_table_structure=DO_TABLES)
    if do_ocr:
        options.ocr_options = RapidOcrOptions(backend="torch")
    return DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)}
    )


def pages_of(document, n_pages: int) -> list[str]:
    """The Markdown of each page, from 1 to n_pages. A page with nothing on it is ""."""
    return [document.export_to_markdown(page_no=n) for n in range(1, n_pages + 1)]


def run_docling(pdf_path: Path, do_ocr: bool, parser_name: str) -> ParsedDoc:
    start = time.perf_counter()
    result = get_converter(do_ocr).convert(pdf_path)
    pages = pages_of(result.document, result.input.page_count)
    latency_ms = round((time.perf_counter() - start) * 1000)
    return from_pages(pages, cost_usd=0.0, latency_ms=latency_ms, parser_name=parser_name)


def parse_docling(pdf_path: Path) -> ParsedDoc:
    return run_docling(pdf_path, do_ocr=False, parser_name="docling")


def parse_docling_ocr(pdf_path: Path) -> ParsedDoc:
    return run_docling(pdf_path, do_ocr=True, parser_name="docling_ocr")
```
</details>

## Break it on purpose

Both breaks cost nothing. Put the code back after each one.

**Break 1: let a run parse.** In `runner.py`, add `from docintel.domain.parse import parse_doc`. In `text_of`, replace
the `return` line with `return parse_doc(cell, doc_id, "x.pdf").text`. Guess: does a test notice?

<details><summary>What you see</summary>

```text
FAILED tests/test_parser_experiment.py::test_a_run_cannot_start_a_parse - Key...
1 failed, 5 passed
```

Good. It is the test that protects your money from a run. Put the code back.
</details>

**Break 2: change the set.** After `freeze`, run this and guess what happens:

```sh
uv run python -m docintel.evals.parser_experiment freeze --per-band 2
```

<details><summary>What you see</summary>

```text
set e3 is frozen with 9 other docs
```

Good. Comparing runs across different documents would be meaningless.
</details>

## Experiment

This part runs no experiment. Every paid step is in 3b3. Your `## E3` entry so far should hold: documents, the deciding
metric, costs that count, cells, the OCR engine, the damage settings, the CER level, and the keep rule.

## Gotchas

- **Close the notebook first.** `parse` opens DuckDB once per paid page.
- **`docling_ocr` needs memory.** Run one contract first, and close other programs (3a2).
- **`--budget` is shared across cells.** Give it enough for all the paid cells on one command.
- **A failed page loses that document's paid pages.** The cache saves whole documents (3a3).
- **`pypdf@mild` gives empty text.** Extraction will still run in 3b3. Its result is a useful zero.

## Explain back, then commit

Explain to Claude in a few sentences:

- Your E3 design: every decision and why.
- `docling_parser.py`: how OCR is separated from no OCR.
- `runner.py`: why `cached_text` raises and does not parse. Why `validate` needs the same text as the model.
- `parser_experiment.py`: the order of the stages, and where the money can be spent.
- Your keep rule, and how the noise floor shaped it.
- `test_parser_experiment.py`: which rule each test protects.

Then:

```sh
git status
git add src/docintel/domain/parse/__init__.py src/docintel/domain/parse/docling_parser.py src/docintel/evals/runner.py src/docintel/evals/parser_experiment.py tests/test_parser_experiment.py
git commit -m "phase 3b2: E3 design, cells, parse stage"
```

## Conclusion

Every parser can now reach the pipeline, and the rule for the winner is written and committed. Go back through the
objectives and check each one without notes. Then answer:

1. Why must the keep rule be written before the run, if the run costs less than $1?
2. Why is a gap of 0.05 a stronger claim on 52 contracts than on 9?

Looking for more challenges? Try these (optional):

1. Compute the noise floor from your own runs with the `gap` cell from 1d.
2. Add a `tables` option to `docling_ocr`, and see what happens to the table in the Kubient contract.

Checklist (`../PLAN.md`): **Experiments: run_id, one change at a time, cost, p50/p95** (the rule before the run, frozen
documents). **Dev/test split, leakage**. Next: 3b3.
