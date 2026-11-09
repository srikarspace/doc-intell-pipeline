# Phase 3b3: the parser experiment (E3)

In this part, you run E3. You parse the fake scans, send every cell through the Phase 2 pipeline, and draw quality
against cost. Then you apply the rule you wrote in 3b2.

This is part 3 of 3 for Phase 3b. It needs 3b2, with your keep rule already committed.

**The paid steps were not run while writing this doc.** Tables marked "shape" show the form, not the numbers.

## Words used in this part

Read these first. Cell, frozen set, noise floor and keep rule are from 3b2.

- **Total cost per contract**: parsing money plus extraction money, divided by the number of contracts.
- **Reference line**: F1 on CUAD's own text. It is what a perfect parser could reach with this model.
- **Log scale**: an axis where each step multiplies. Example: $0.001, $0.01, $0.1 are at equal distances.
- **Small multiples**: several small charts with the same axes, one for each group.
- **Stop rule**: a condition, written before a paid run, that makes you stop and look.

## Objectives

By the end of this part you should be able to:

1. Run the free cells first, and the paid cells only after you see the estimate.
2. Build one table of quality, cost and speed for every cell.
3. Read a paired bootstrap on few contracts, and say what it cannot show.
4. Explain with your own numbers why CER and F1 can disagree.
5. Say in one sentence, with numbers, when you would pay for a vision parser.

## Dependencies

You install nothing new. `matplotlib` is already a dev dependency from 1c3.

This part needs:

- 3b2: the frozen set, the cells, your `## E3` design and your keep rule in git.
- 1d: the notebook cells `per_doc`, `f1` and `gap`.
- An OpenRouter key in `.env`.
- Money. From the real estimates: about $0.22 per scan condition for vision. Extraction on 9 contracts was about
  $0.012 per cell in the last dev run, so about $0.12 for 10 cells. The run is yours to start.

## The big picture

Before this part, every piece existed, but nothing had run together.

After this part:

```text
parse stage -> extract + validate + score -> compare table -> chart -> E3 -> your verdict
```

- **Phase 4** uses your verdict for scans, and decides if Docling goes in the Docker image.
- **Phase 5** uses this chart to answer README question 2: OCR-style or multimodal, quality against cost.

## Remember this

> A result is a trade-off with a price on it. "Vision is better" says nothing. "On heavy scans, vision adds this much
> F1 for this much money per contract" is something a person can decide on. And if the gap is inside the noise, the
> honest answer is that this test could not tell.
>
> **Every claim gets a number and a price.**

## Why

**One table, one chart.** Quality, cost and speed live in different tables. The comparison must put them side by side.

**The reference shows the ceiling.** If `cuad_txt` scores 0.88 on these 9 contracts, a parser at 0.87 has lost almost
nothing.

**CER explains, F1 decides.** You wrote this in your rule. This part shows you why.

## Design decisions

- **`compare` uses the newest run of each cell.** A failed try does not need cleaning up. Other option: type each
  `run_id` by hand. A typo would give a wrong row with no error.
- **`cuad_txt` runs on the same 9 contracts.** It is the same docs and the same code. Other option: take those docs from
  the old 52-contract run. That mixes in a different run, so noise looks like an effect.
- **Three small charts, one per condition.** Other option: one chart with all 9 points. We tried it. The labels landed
  on top of each other.
- **The cost axis is a log scale.** Free cells cost about $0.001, and vision costs about $0.025. On a normal axis, the
  free cells are one point. Total cost always includes extraction, so no value is zero.
- **Parser color, and a name on every point.** Color alone fails for color-blind readers. The three colors were checked
  with a color-vision tool.

## Worked example

The first two rounds use real numbers. Guess before you open each box.

### Round 1: which clean parser reads best?

From your 3b2 table:

| Cell | CER | Quotes found |
|---|---|---|
| `pypdf` | 0.003 | 156/158 |
| `docling` | 0.015 | 157/158 |
| `deepseek_vl` | 0.007 | 153/158 |

Guess: which one will have the best F1?

<details><summary>Guess, then open</summary>

You do not know yet. CER and quotes already rank them differently. Docling has the worst CER, and it finds the most
quotes. On clean PDFs, all three are close, and 9 contracts cannot rank them. Your run shows the real answer. This
question is the reason F1 decides.
</details>

### Round 2: what does a zero tell you?

`pypdf@mild` gives empty text. You still send it through extraction. Guess: is the call wasted?

<details><summary>Guess, then open</summary>

It is cheap, and it is the honest baseline. It answers the question "what happens if a user uploads a scan and we only
have pypdf?" Look at precision too: the correct behaviour on empty text is "not found" everywhere. Any `found` answer is
a made-up one. Validation should catch those.
</details>

### Round 3: what if the bootstrap range is wide?

Say `gap` gives `(0.04, -0.03, 0.12)` for vision minus OCR. Guess: did vision win?

<details><summary>Guess, then open</summary>

(The numbers in this box are an example.) The range includes 0. On 9 contracts, it often will. Your rule asks for a gap
of at least 0.05, and here the gap is 0.04. So the rule says no. Say it in those words: "not enough evidence on 9
contracts to pay for vision". That is a result, and it is useful.
</details>

## Project setup

```sh
touch tests/test_compare.py
```

You should now have:

```text
tests/
└── test_compare.py   # new
```

You also add a chart cell to `notebooks/00_explore.ipynb`, as in 1c3.

## Step 1: the free cells

**Why.** They cost nothing, and they tell you if your scans are working.

```sh
uv run python -m docintel.evals.parser_experiment parse --cells pypdf docling docling_ocr@mild docling_ocr@heavy --budget 0
uv run python -m docintel.evals.parser_experiment text
```

`docling_ocr` reads 69 pages per condition, so close other programs first. Cached documents are not read again.

The shape to expect (your numbers will differ):

```text
cell                 docs    CER    quotes    $/doc  s/page
pypdf                   9  0.003  156/158  $ 0.0000    0.01
docling                 9  0.015  157/158  $ 0.0000    1.09
deepseek_vl             9  0.007  153/158  $ 0.0234    8.66
pypdf@mild              9  1.000    0/158  $ 0.0000    0.00
docling_ocr@mild        9  <cer>    <n>/158  $ 0.0000  <s>
pypdf@heavy             9  1.000    0/158  $ 0.0000    0.00
docling_ocr@heavy       9  <cer>    <n>/158  $ 0.0000  <s>
```

Stop and check: if `docling_ocr@mild` is as bad as `pypdf@mild`, something is wrong with OCR. Do not pay for vision yet.

## Step 2: the paid vision cells

**Why.** This is the only large cost. So you see the estimate, and you set a stop rule first.

Write this in `EXPERIMENTS.md`, under `## E3`, before you start:

- **Stop rule:** stop if any page fails, if any call hits the token limit, or if the cost passes the usual estimate by
  50% before the first condition is done.

Then run one condition. Type `y` only if the estimate matches your plan:

```sh
uv run python -m docintel.evals.parser_experiment parse --cells deepseek_vl@mild --budget 0.60
```

```text
deepseek_vl@mild: 69 pages to pay for, usual $0.2184, worst $1.0172
Start? [y/N]
```

The budget of $0.60 is smaller than the worst case. That is on purpose: the run stops before it can pass it.

Check after the first condition, before you start the next one. Use the `run e3-parse-...` name it printed:

```sh
uv run python - <<'EOF'
from docintel.evals.store import connect

with connect() as con:
    print(con.execute(
        "SELECT run_id, count(*), sum(cost_usd), max(completion_tokens), count(*) FILTER (WHERE NOT ok) "
        "FROM llm_calls WHERE run_id LIKE 'e3-parse-%' GROUP BY run_id ORDER BY run_id"
    ).fetchall())
EOF
```

If `max(completion_tokens)` equals 12,000, a page hit the limit. Look at it. Heavy noise can make a model repeat itself.

If it looks right, run heavy the same way, with `--cells deepseek_vl@heavy`.

## Step 3: extraction on every cell

**Why.** This is the Phase 2 pipeline, unchanged, on 10 different texts.

First the reference, alone. Type `y` after you read the estimate:

```sh
uv run python -m docintel.evals.runner run --split e3 --parser cuad_txt
```

The shape to expect:

```text
run <run_id>: 9 of 9 docs to do, deepseek/deepseek-v4-flash, about $<est>
Start? [y/N] y
done in <s> s: 9 of 9 docs scored, 0 calls failed
```

Compare the printed estimate with the real cost before you continue. `--retries` is 2 by default since E2.3.

Then the other 9 cells. This loop skips the question, so read the cost after each line:

```sh
for cell in pypdf docling deepseek_vl pypdf@mild docling_ocr@mild deepseek_vl@mild pypdf@heavy docling_ocr@heavy deepseek_vl@heavy; do
  uv run python -m docintel.evals.runner run --split e3 --parser "$cell" --yes
done
```

A cell with bad text can need more retries. Each run stores its own `run_id`, so one failure does not lose the others.

## Step 4: one table for every cell

**Why.** This is the table you will read and put in the README.

Update the imports at the top of `src/docintel/evals/parser_experiment.py`. Add these two lines, in their sorted places:

```python
from docintel.core.config import get_settings
from docintel.evals.scorers import metrics
```

Add to `src/docintel/evals/parser_experiment.py`, above `parse_args`:

```python
LATEST = """
SELECT parser, arg_max(run_id, created_at) FROM runs
WHERE split = ? AND model = ? AND prompt_version = 'v1' GROUP BY parser
"""
EXTRACT_COST = "SELECT coalesce(sum(cost_usd), 0) FROM llm_calls WHERE run_id = ?"
FLAGS = """
SELECT count(DISTINCT (doc_id, field)),
    count(DISTINCT (doc_id, field)) FILTER (WHERE severity = 'error')
FROM issues WHERE run_id = ?
"""


def compare_rows(con: duckdb.DuckDBPyConnection, docs: list[tuple], model: str) -> list[dict]:
    """One row per cell: quality, cost per doc, speed. Uses the newest run of each cell."""
    runs = dict(con.execute(LATEST, [SET_NAME, model]).fetchall())
    spans = all_spans(con, docs)
    rows = []
    for cell in ["cuad_txt", *CELLS]:
        if cell not in runs:
            continue
        run_id = runs[cell]
        reference = {"cer": 0.0, "parse_usd": 0.0, "s_page": 0.0}
        stats = reference if cell == "cuad_txt" else cell_stats(cell, docs, spans)
        if stats is None:  # never report a cost of 0 for text that we cannot find
            raise SystemExit(f"{cell}: some docs are not parsed (run from the project folder)")
        (extract,) = con.execute(EXTRACT_COST, [run_id]).fetchone()
        review, errors = con.execute(FLAGS, [run_id]).fetchone()
        m = metrics(con, run_id)[-1]  # the last row is all fields
        n_fields = len(docs) * 12
        rows.append(
            {
                "cell": cell,
                "run_id": run_id,
                "p": m["precision"],
                "r": m["recall"],
                "f1": m["f1"],
                "cer": stats["cer"],
                "parse_usd": stats["parse_usd"],
                "extract_usd": extract / len(docs),
                "total_usd": stats["parse_usd"] + extract / len(docs),
                "s_page": stats["s_page"],
                "review": review / n_fields,
                "errors": errors,
            }
        )
    return rows


def print_compare(rows: list[dict]) -> None:
    print(
        f"{'cell':20} {'P':>5} {'R':>5} {'F1':>5} {'CER':>6} {'parse$':>8} {'extr$':>8} "
        f"{'total$':>8} {'s/page':>7} {'review':>7} {'errors':>6}"
    )
    for r in rows:
        p, recall, f1 = (0.0 if r[k] is None else r[k] for k in ("p", "r", "f1"))
        print(
            f"{r['cell']:20} {p:5.2f} {recall:5.2f} {f1:5.2f} {r['cer']:6.3f} "
            f"{r['parse_usd']:8.4f} {r['extract_usd']:8.4f} {r['total_usd']:8.4f} "
            f"{r['s_page']:7.2f} {r['review']:7.1%} {r['errors']:6}"
        )
```

*Python here: [`arg_max`, and a dict of runs](./py/phase-3b3.md#py-1).*

Here, for each cell that has a run, in order:

1. Find the newest `run_id` for that cell, with the same model and prompt.
2. Read P, R and F1 from the same `metrics` as Phase 1.
3. Add the parse cost per contract and the extraction cost per contract.
4. Read the review flags and the errors from `issues`.

If a cell has a run but its text is not in the cache, the report stops. It never shows a cost of 0 for text it cannot
find.

Then, in `parse_args`, add this after the `text` lines:

```python
    sub.add_parser("compare", help="quality against cost for every cell that has a run")
```

And in `main`, inside the `with` block, after the `text` command:

```python
        if args.command == "compare":
            print_compare(compare_rows(con, docs, get_settings().docintel_model))
            return
```

Checkpoint:

```sh
uv run python -m docintel.evals.parser_experiment compare
```

The shape to expect (your numbers will differ):

```text
cell                     P     R    F1    CER   parse$    extr$   total$  s/page  review errors
cuad_txt              <p>   <r>   <f1>  0.000   0.0000   <e>      <t>      0.00    <r>%    <n>
pypdf                 ...
...
deepseek_vl@heavy     ...
```

## Step 5: is the gap real?

**Why.** Your rule compares gaps. A gap needs a range.

Open the notebook, and run your `per_doc`, `f1` and `gap` cells from 1d. Then add this cell, using the `run_id` of each
cell from Step 4:

```python
RUNS = {
    "cuad_txt": "<run_id>",
    "docling_ocr@mild": "<run_id>",
    "deepseek_vl@mild": "<run_id>",
    "docling_ocr@heavy": "<run_id>",
    "deepseek_vl@heavy": "<run_id>",
}
print("mild, vision minus OCR:", gap(RUNS["deepseek_vl@mild"], RUNS["docling_ocr@mild"]))
print("heavy, vision minus OCR:", gap(RUNS["deepseek_vl@heavy"], RUNS["docling_ocr@heavy"]))
print("mild OCR minus reference:", gap(RUNS["docling_ocr@mild"], RUNS["cuad_txt"]))
```

With 9 contracts, expect wide ranges. Do not read a ranking into a range that includes 0.

## Step 6: the chart

**Why.** One picture shows quality and price together. It goes in the README.

Add this cell to `notebooks/00_explore.ipynb`:

```python
import os
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

from docintel.core.config import get_settings
from docintel.evals.parser_experiment import compare_rows, frozen_docs, split_cell

STYLE = {  # parser -> (color, label, label offset in points)
    "pypdf": ("#2a78d6", "pypdf", (0, 10)),
    "docling": ("#eb6834", "Docling", (0, -18)),
    "docling_ocr": ("#eb6834", "Docling OCR", (0, -18)),
    "deepseek_vl": ("#1baf7a", "Vision LLM", (-4, -18)),
}
INK, MUTED, SURFACE = "#0b0b0b", "#52514e", "#fcfcfb"

os.chdir(Path.cwd() if Path("data").exists() else Path.cwd().parent)  # paths start at the project folder
rows = compare_rows(con, frozen_docs(con), get_settings().docintel_model)
baseline = next(r["f1"] for r in rows if r["cell"] == "cuad_txt")
conditions = ["clean", "mild", "heavy"]
fig, axes = plt.subplots(1, 3, figsize=(11, 4), sharex=True, sharey=True, facecolor=SURFACE)
for ax, condition in zip(axes, conditions, strict=True):
    ax.set_facecolor(SURFACE)
    ax.axhline(baseline, color=MUTED, linewidth=1, linestyle="--")
    for r in rows:
        if r["cell"] == "cuad_txt" or split_cell(r["cell"])[1] != condition:
            continue
        color, label, offset = STYLE[split_cell(r["cell"])[0]]
        ax.scatter(r["total_usd"], r["f1"], s=90, color=color, edgecolor=SURFACE, linewidth=2, zorder=3)
        ax.annotate(label, (r["total_usd"], r["f1"]), xytext=offset, textcoords="offset points",
                    ha="center", color=MUTED, fontsize=9)
    ax.set_title(condition, loc="left", color=INK)
    ax.set_xscale("log")
    ax.set_xlim(0.0005, 0.06)
    ax.set_ylim(-0.08, 1.02)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f"${x:g}"))
    ax.grid(color="#e8e7e2", linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(colors=MUTED)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color("#c3c2b7")
axes[0].set_ylabel("F1, all 12 fields", color=MUTED)
axes[1].set_xlabel("Total cost per contract, log scale. Dashed line: F1 on CUAD text.", color=MUTED)
fig.suptitle("Quality against cost, for each scan condition", x=0.01, ha="left", color=INK)
fig.tight_layout()
fig.savefig("data/e3_quality_cost.png", dpi=130)
```

*Python here: [matplotlib: `subplots`, `ax`](./py/phase-1c3.md#py-3) · [`next` with a generator](./py/phase-3b3.md#py-2).*

Here, we:

1. Move to the project folder. `make nb` starts the notebook in `notebooks/`, but stored paths start at the project.
2. Draw one panel per condition, with the same axes, so positions can be compared.
3. Draw the reference as a dashed line in each panel.
4. Put one colored point per parser, with the name beside it. So identity is not color alone.
5. Change the axis to a log scale, with `$` labels.

Adjust the label offsets if two labels touch on your numbers. Check by eye. A point that is high and on the left is
good and cheap.

## Step 7: read the result

**Why.** The number means nothing until you answer the question with it.

Write down, using your own numbers:

1. **Clean condition.** Is any parser different from `cuad_txt`, beyond the noise?
2. **Mild.** Does free OCR keep F1 close to the reference?
3. **Heavy.** Where does free OCR break? What does vision buy here, and at what price per contract?
4. **CER against F1.** Find one cell where CER looks worse than F1 says, or the other way round. Open its text, and say
   why. A moved table (3b, Round 3) is one possible reason.
5. **Validation.** Does the `review` column go up as text gets worse? The E2.3 entry says errors should be more common on
   worse text. Did that happen?

Then apply your keep rule from 3b2, line by line, with pass or fail. Do not change the rule now. If you think the rule
was wrong, say so in the entry, and leave the verdict as the rule gives it.

## Step 8: a small test

**Why.** A wrong sum would give a wrong answer to the main question, and nothing would warn you.

The test names say what is protected: the newest run is used, the total adds parse and extraction per contract, the
reference has no parse cost, and a cell with no text stops the report.

<details><summary>Put this in <code>tests/test_compare.py</code></summary>

```python
"""The E3 report: each cell uses its newest run, and cost adds parse and extraction."""

import pytest

from docintel.domain.schema.fields import ContractFields
from docintel.evals import parser_experiment as pe
from docintel.evals.runner import TABLES
from docintel.evals.store import connect

MODEL = "fake/model"
DOCS = [("doc-1", "p", "t", 1), ("doc-2", "p", "t", 1)]


def add_run(con, run_id, cell, created, tp, cost):
    con.execute(
        "INSERT INTO runs (run_id, created_at, split, parser, model, prompt_version, n_docs) "
        "VALUES (?, ?, 'e3', ?, ?, 'v1', 2)",
        [run_id, created, cell, MODEL],
    )
    for field in ContractFields.model_fields:
        con.execute(
            "INSERT INTO scores VALUES "
            "(?, 'doc-1', ?, 'presence', true, true, true, true, ?, 0, 0)",
            [run_id, field, tp],
        )
    con.execute(
        "INSERT INTO llm_calls (run_id, cost_usd) VALUES (?, ?)",
        [run_id, cost],
    )


@pytest.fixture
def con(tmp_path, monkeypatch):
    monkeypatch.setattr(pe, "all_spans", lambda con, docs: {})
    stats = {"cer": 0.1, "found": 1, "total": 1, "parse_usd": 0.02, "s_page": 3.0}
    monkeypatch.setattr(pe, "cell_stats", lambda cell, docs, spans: stats)
    with connect(tmp_path / "t.duckdb") as c:
        c.execute(TABLES)
        c.execute("CREATE TABLE llm_calls (run_id VARCHAR, cost_usd DOUBLE)")
        yield c


def test_the_newest_run_of_a_cell_is_used(con):
    add_run(con, "old", "pypdf", "2026-01-01", 0, 0.0)
    add_run(con, "new", "pypdf", "2026-01-02", 1, 0.0)
    assert pe.compare_rows(con, DOCS, MODEL)[0]["run_id"] == "new"


def test_total_cost_adds_parse_and_extraction_per_doc(con):
    add_run(con, "r", "deepseek_vl@mild", "2026-01-01", 1, 0.01)
    row = pe.compare_rows(con, DOCS, MODEL)[0]
    assert row["extract_usd"] == pytest.approx(0.005)
    assert row["total_usd"] == pytest.approx(0.025)


def test_the_reference_has_no_parse_cost_or_errors(con):
    add_run(con, "r", "cuad_txt", "2026-01-01", 1, 0.01)
    row = pe.compare_rows(con, DOCS, MODEL)[0]
    assert (row["cer"], row["parse_usd"]) == (0.0, 0.0)


def test_a_cell_with_no_parsed_text_stops_the_report(con, monkeypatch):
    add_run(con, "r", "pypdf", "2026-01-01", 1, 0.0)
    monkeypatch.setattr(pe, "cell_stats", lambda cell, docs, spans: None)
    with pytest.raises(SystemExit, match="not parsed"):
        pe.compare_rows(con, DOCS, MODEL)
```
</details>

*Python here: [`monkeypatch.setattr` on a module](./py/phase-3b3.md#py-3).*

Checkpoint:

```sh
uv run pytest tests/test_compare.py -q
make test
make lint
```

```text
....                                                                     [100%]
4 passed in 0.52s
```

Your project structure should now look like this:

```text
src/docintel/evals/
└── parser_experiment.py     # + compare_rows, print_compare, compare command
tests/
└── test_compare.py
notebooks/00_explore.ipynb   # + E3 gap cell and chart
data/e3_quality_cost.png     # not in git
```

<details><summary>Complete <code>src/docintel/evals/parser_experiment.py</code></summary>

```python
"""E3: freeze the docs, make the fake scans, parse them, and check the text."""

import argparse
from datetime import datetime
from pathlib import Path

import duckdb

from docintel.core.config import get_settings
from docintel.domain.parse import PARSERS
from docintel.domain.parse.base import ParsedDoc
from docintel.domain.parse.cache import cache_path, cached_parse
from docintel.domain.parse.scan import CONDITIONS, make_scan, scan_path
from docintel.domain.parse.vision import MODELS, Budget, BudgetExceeded, make_vision_parser
from docintel.domain.validate.citations import quote_status, words
from docintel.evals.cer import cer
from docintel.evals.parse_pilot import page_costs, pick_docs
from docintel.evals.runner import CELLS, TABLES
from docintel.evals.scorers import metrics
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


LATEST = """
SELECT parser, arg_max(run_id, created_at) FROM runs
WHERE split = ? AND model = ? AND prompt_version = 'v1' GROUP BY parser
"""
EXTRACT_COST = "SELECT coalesce(sum(cost_usd), 0) FROM llm_calls WHERE run_id = ?"
FLAGS = """
SELECT count(DISTINCT (doc_id, field)),
    count(DISTINCT (doc_id, field)) FILTER (WHERE severity = 'error')
FROM issues WHERE run_id = ?
"""


def compare_rows(con: duckdb.DuckDBPyConnection, docs: list[tuple], model: str) -> list[dict]:
    """One row per cell: quality, cost per doc, speed. Uses the newest run of each cell."""
    runs = dict(con.execute(LATEST, [SET_NAME, model]).fetchall())
    spans = all_spans(con, docs)
    rows = []
    for cell in ["cuad_txt", *CELLS]:
        if cell not in runs:
            continue
        run_id = runs[cell]
        reference = {"cer": 0.0, "parse_usd": 0.0, "s_page": 0.0}
        stats = reference if cell == "cuad_txt" else cell_stats(cell, docs, spans)
        if stats is None:  # never report a cost of 0 for text that we cannot find
            raise SystemExit(f"{cell}: some docs are not parsed (run from the project folder)")
        (extract,) = con.execute(EXTRACT_COST, [run_id]).fetchone()
        review, errors = con.execute(FLAGS, [run_id]).fetchone()
        m = metrics(con, run_id)[-1]  # the last row is all fields
        n_fields = len(docs) * 12
        rows.append(
            {
                "cell": cell,
                "run_id": run_id,
                "p": m["precision"],
                "r": m["recall"],
                "f1": m["f1"],
                "cer": stats["cer"],
                "parse_usd": stats["parse_usd"],
                "extract_usd": extract / len(docs),
                "total_usd": stats["parse_usd"] + extract / len(docs),
                "s_page": stats["s_page"],
                "review": review / n_fields,
                "errors": errors,
            }
        )
    return rows


def print_compare(rows: list[dict]) -> None:
    print(
        f"{'cell':20} {'P':>5} {'R':>5} {'F1':>5} {'CER':>6} {'parse$':>8} {'extr$':>8} "
        f"{'total$':>8} {'s/page':>7} {'review':>7} {'errors':>6}"
    )
    for r in rows:
        p, recall, f1 = (0.0 if r[k] is None else r[k] for k in ("p", "r", "f1"))
        print(
            f"{r['cell']:20} {p:5.2f} {recall:5.2f} {f1:5.2f} {r['cer']:6.3f} "
            f"{r['parse_usd']:8.4f} {r['extract_usd']:8.4f} {r['total_usd']:8.4f} "
            f"{r['s_page']:7.2f} {r['review']:7.1%} {r['errors']:6}"
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
    sub.add_parser("compare", help="quality against cost for every cell that has a run")
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
        if args.command == "compare":
            print_compare(compare_rows(con, docs, get_settings().docintel_model))
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

## Break it on purpose

Both breaks are free. Put the code back after each one.

**Break 1: forget the parse cost.** In `compare_rows`, change `"total_usd": stats["parse_usd"] + extract / len(docs),`
to `"total_usd": extract / len(docs),`. Guess: which test fails?

<details><summary>What you see</summary>

```text
FAILED tests/test_compare.py::test_total_cost_adds_parse_and_extraction_per_doc
1 failed, 3 passed
```

Without it, vision would look nearly free, and the main
chart would be wrong by more than ten times.
</details>

**Break 2: use the oldest run.** In `LATEST`, change `arg_max` to `arg_min`. Guess: which test fails?

<details><summary>What you see</summary>

```text
FAILED tests/test_compare.py::test_the_newest_run_of_a_cell_is_used
1 failed, 3 passed
```

A repeat of a failed cell would otherwise be ignored.
</details>

## Experiment

**Commands:** Steps 1 to 4 above. **run_id:** one `e3-parse-<date>-<time>` per paid parse, and one `<date>-<time>` for
each extraction cell.

**The table to expect:** Step 4, one row per cell (10 rows if you kept the reference grid), and one chart.

Fill in the entry in `EXPERIMENTS.md`:

```markdown
## E3: parsers on clean text and fake scans
- **Date:** <date>
- **Commits:** <the commit with the keep rule> before the run.
- **run_id(s):** <one per cell, and the e3-parse runs>.
- **Question / hypothesis:** On scans, is a vision LLM worth its cost over free OCR?
- **Data:** dev, frozen set e3, 9 contracts, 69 pages. Conditions: clean, <yours>. Seed 0.
- **Setup:** extraction deepseek/deepseek-v4-flash, prompt v1, `--retries 2`, Parasail. Vision deepseek_vl, 150 DPI,
  token limit 12,000. OCR: <engine>. CER level: <level>. Damage settings: <values>.
- **Keep rule (written before the run):** <your rule>.
- **Stop rule:** <your rule>, <fired or not>.
- **Results:** the compare table, the gap ranges, the chart path, and the failed pages.
- **Limits:** 9 contracts, fake scans, one model, one run per cell, noise floor about 0.02. Fake damage is simpler than
  real scans (no stamps, no handwriting, no fold marks).
- **Conclusion:** <your rule, line by line>. One sentence: "<parser> for <condition>, because <gap>, at <cost per contract>."
- **Next step:** Phase 4, the scan path and if Docling goes in the Docker image.
```

Tune on dev only. The test split is for the final numbers.

## Gotchas

- **Run the free cells first.** They are the cheap way to find a broken scan.
- **`--yes` skips the question.** Use it only on a loop you already priced.
- **Do not change the damage after seeing results.** That is the same as tuning on the answer. Change it only with a
  new entry and a new rule.
- **A retry on bad text costs more.** Extraction cost may rise on heavy cells. It is counted in `total$`.
- **The chart reads the newest runs.** If you repeat one cell, the chart changes. Write the `run_id`s down in the entry.

## Explain back, then commit

Explain to Claude in a few sentences:

- `parser_experiment.py`: what each column of `compare` is, and which table it comes from.
- Your numbers: the trade-off in one sentence.
- When you would pay for vision, and when you would not.
- A real case from your run where CER and F1 disagree.
- Your keep rule, line by line, and what it decided.
- `test_compare.py`: which mistake each test catches.

Then:

```sh
git status
git add src/docintel/evals/parser_experiment.py tests/test_compare.py notebooks/00_explore.ipynb EXPERIMENTS.md
git commit -m "phase 3b3: E3 parser experiment"
```

## Conclusion

You can now say what a parser really costs, what it buys, and how sure you are. Phase 3 is done. Go back through the
objectives and check each one without notes. Then answer the Phase 3 checkpoint:

1. Explain the trade-off in one sentence, with numbers.
2. When would you pay for multimodal parsing?
3. Why can CER and F1 disagree?

Looking for more challenges? Try these (optional):

1. Run the same grid on all 34 contracts that fit the page cap, and see if your noise floor shrinks.
2. Add a real scanned page of your own, and read it by eye. Where is the fake scan too kind?

Checklist (`../PLAN.md`): **Parsers: text layer vs layout vs multimodal; CER** (complete). **Experiments: run_id, one
change at a time, cost, p50/p95** (quality against cost, with a rule written first).
