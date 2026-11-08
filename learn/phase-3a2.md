# Phase 3a2: Docling, read first and then wrapped

In this part, you read how Docling turns a PDF into a document. Then you wrap it behind the 3a interface.
You build it piece by piece, and you measure it on your own Mac.

This is part 2 of 3 for Phase 3a. It needs 3a.

## Words used in this part

Read these first. Parser, text layer, scan and cache are from 3a.

- **OCR**: optical character recognition. A program reads letters from a picture of a page.
- **Layout model**: a small model that finds the blocks on a page. Example: "this box is a heading, this
  box is a table".
- **Table structure model**: a small model that finds the rows and columns inside a table.
- **Pipeline**: a fixed list of steps. The output of one step is the input of the next.
- **Stage**: one step in Docling's pipeline. Example: the layout stage.
- **Local model**: a model that runs inside your Python program, on your Mac. It has no server and no key.
- **Peak memory**: the most memory the program used at any moment.
- **Lazy import**: an `import` placed inside a function, so it runs only when the function is called.

## Objectives

By the end of this part you should be able to:

1. Follow a call to `convert` through Docling's code, and name the stages in order.
2. Say what the OCR and table options change, with real numbers.
3. Wrap a heavy library so that importing your code stays fast.
4. Measure time and peak memory on your Mac.
5. Say what Docling adds over pypdf, and where it did worse.

## Dependencies

New library:

- `docling`: reads PDFs with layout and OCR models. It brings PyTorch (the library that runs the models).

The install adds about 1 GB to `.venv`. On the first run, Docling also downloads about 500 MB of model
files to `~/.cache/huggingface`. You have 8 GB of memory, so close Jupyter and heavy apps first.

This part needs 3a: `ParsedDoc`, `from_pages`, `parse_doc` and `PARSERS`.

## The big picture

Before this part, pypdf was the only parser. It cannot read a scan.

After this part:

```text
PARSERS = { "pypdf": copies the text layer,  "docling": layout models, OCR when turned on }
```

- **3a3** adds the third parser, a vision LLM.
- **3b** turns OCR on and reads fake scans. There, Docling should beat pypdf by a lot.
- **4c** decides if Docling goes into the Docker image. It adds about 1 GB.

## Remember this

> Docling is a pipeline of small local models: it reads the page, finds the layout, reads letters if needed,
> finds tables, and joins it all together. Each option turns on more models. More models cost more memory
> and time, and more structure can hurt a check that reads words in order. Measure the options on a real
> contract before you choose.
>
> **More models is not more correct. Measure it.**

## Why

**Reading a library before wrapping it shows what it can change.** The options only make sense if you know
which stage they control.

**A scan needs OCR.** pypdf returns nothing for a scan. Docling is the free way to read one.

**Your Mac has limits.** A wrapper that loads PyTorch at import would slow every command in the project,
even the ones that never parse.

## Design decisions

- **The converter is built once, with `@lru_cache`.** Building it loads the settings, and later runs reuse it.
  Other option: build one per document. That repeats the work for every contract.
- **Docling is imported inside the function (lazy import).** Importing `docintel.domain.parse` must not load
  PyTorch. Other option: import at the top of the file. Then even `make test` pays for it.
- **Pages come from `export_to_markdown(page_no=n)`.** It keeps our `pages` list and its blank pages. Other
  option: export the whole document, and lose the page positions.
- **We count pages with `result.input.page_count`.** A blank page has no content, so Docling's content cannot
  tell us it exists. Other option: count only pages with content, and lose the blank ones.
- **`cost_usd` is 0.** We count what we pay. Other option: put a price on your Mac's time. There is no fair
  number, and `latency_ms` already shows the time.
- **The options are constants in the file.** There are two of them, and 3b changes them on purpose. Other
  option: settings in `.env`. Then a run could change without a change in the code.

## Worked example

This is real dev data, on your Mac's kind of machine (M1, 8 GB). Guess before you open each box.

### Round 1: does OCR change a normal PDF?

The Kubient contract has 2 pages and a text layer. You run Docling with OCR on, and then with OCR off. Guess:
how many characters does each one give?

<details><summary>Guess, then open</summary>

Both give 8,899 characters. On the 9-page VNUE contract, both give 20,412. On these two PDFs, OCR changed
nothing. The text layer was already there. OCR matters when there is no text layer, and that is 3b.
</details>

### Round 2: tables on

Docling can rebuild a table. The Kubient contract has a revenue table, and the lawyers labelled part of it.
With the table model on, the text has this:

```text
| Type                 | Monthly Revenue* - Threshold   | Below Threshold - Customer   | ...
| Programmatic/Display | $ 300,000.00                   | 90%                          | ...
```

The lawyer's quote starts like this:

```text
Revenue/Profit Sharing 'Monthly Revenue* Below Threshold Above Threshold Type Threshold Customer Kubient ...
```

Guess: does the citation check find this quote with tables on?

<details><summary>Guess, then open</summary>

No. With tables on, 12 of 13 quotes are found. With tables off, 13 of 13. The table looks better to a person.
But Docling moved the header words next to each cell, so the words are in a new order. Our check reads words
in order. Better structure gave a worse result. This is one contract, so it is a warning and not a rule.
</details>

## Project setup

Install Docling:

```sh
uv add docling
```

The last lines show the new packages, and they include these:

```text
 + docling==2.149.0
 + torch==2.15.0
```

Then create the files:

```sh
touch src/docintel/domain/parse/docling_parser.py
touch tests/test_docling_parser.py
```

You should now have:

```text
src/docintel/domain/parse/
├── __init__.py
├── base.py
├── cache.py
├── docling_parser.py    # new
└── pypdf_parser.py
tests/
├── test_docling_parser.py    # new
└── test_parse_cache.py
```

## Step 1: trace Docling's pipeline (read the code)

**Why.** You will use two options. This step shows which stage each one controls.

You need only a browser. All links use the tag `v2.149.0`, so the line numbers stay correct.

Open each link and answer before you open the box:

1. [`DocumentConverter.convert`](https://github.com/docling-project/docling/blob/v2.149.0/docling/document_converter.py#L657).
   It takes one file. What does it call to do the work?
2. [`_execute_pipeline`](https://github.com/docling-project/docling/blob/v2.149.0/docling/document_converter.py#L1050).
   What object does it get, and which method does it call on it?
3. [`BasePipeline.execute`](https://github.com/docling-project/docling/blob/v2.149.0/docling/pipeline/base_pipeline.py#L81).
   Which three steps run, in order?
4. [`_create_run_ctx`](https://github.com/docling-project/docling/blob/v2.149.0/docling/pipeline/standard_pdf_pipeline.py#L803).
   The stages are created in this order: preprocess, ocr, layout, layout_postprocess, table, assemble.
   [Then read `# wire stages`](https://github.com/docling-project/docling/blob/v2.149.0/docling/pipeline/standard_pdf_pipeline.py#L866).
   Guess first: does OCR run before layout?

<details><summary>Check your trace</summary>

```text
convert(path)                                    document_converter.py:657
  -> convert_all -> _convert -> _process_document (checks the format is allowed)
  -> _execute_pipeline                           document_converter.py:1050
       -> _get_pipeline(format)                  a StandardPdfPipeline for a PDF
       -> pipeline.execute(...)                  base_pipeline.py:81
            1. _build_document                   the stages run on every page
            2. _assemble_document                pages become one document
            3. _enrich_document                  optional extras (off for us)
```

The stages run in this order, from the `# wire stages` lines:

```text
preprocess -> layout -> ocr -> layout_postprocess -> table -> assemble
(read the     (find     (read    (clean the          (rows and  (join
 text layer)   blocks)   letters)  blocks)            columns)   the page)
```

Creation order is not run order. `ocr` is created first, but it runs after `layout`. The order comes only
from the `add_output_queue` lines. Each stage is a thread, with a queue going to the next one. In JS terms,
it is like a chain of streams with `.pipe()`.
</details>

Now connect the options to the stages:

- `do_ocr` controls the `ocr` stage.
- `do_table_structure` controls the `table` stage.
- `layout` always runs. That is what Docling adds over pypdf, even with both options off.

## Step 2: choose the options (your decision)

**Why.** Each option costs memory and time, and it can change the text that the checks read.

You decide three things: OCR on or off for normal PDFs, tables on or off, and Markdown or plain text.

The evidence, measured on an M1 with 8 GB. Time is for `convert` only, with the models already downloaded:

| Contract | OCR | Tables | Convert | Chars | Peak memory | Quotes found |
|---|---|---|---|---|---|---|
| Kubient, 2 pages | on | on | 7.1 s | 8,899 | 0.94 GB | 12 of 13 |
| Kubient, 2 pages | off | on | 6.0 s | 8,899 | 0.99 GB | 12 of 13 |
| Kubient, 2 pages | off | off | 4.9 s | 8,107 | 0.62 GB | 13 of 13 |
| VNUE, 9 pages | off | on | 8.4 s | 20,412 | 0.99 GB | 18 of 18 |
| VNUE, 9 pages | on | on | 7.9 s | 20,412 | 1.02 GB | 18 of 18 |

Other things to look at:

- Round 2: tables moved words into a new order.
- `words()` ignores `#` and `|`, so Markdown marks do not hurt the citation check.
- CER in 3b counts every character. Markdown marks will count as errors there.
- Part of the first page's time is loading models. That is why 9 pages is not 4.5 times slower than 2 pages.

Write your choice in `EXPERIMENTS.md`, as a note for E3. Then compare.

<details><summary>Reference (open after you write yours)</summary>

- **OCR off** for normal PDFs. It changed nothing here. 3b turns it on for scans.
- **Tables off.** It is the lower memory choice, and it kept all 13 quotes. This is only 2 contracts, so 3b can
  test tables on as its own change.
- **Markdown.** It is the Docling output that supports `page_no`. With tables off, it mostly adds `## `.
</details>

## Step 3: the wrapper

**Why.** The rest of the pipeline must not know that Docling exists.

Put this in `src/docintel/domain/parse/docling_parser.py`. Use your own values for the two options:

```python
"""Parser 2: Docling. Local layout and OCR models, free but slow."""

import time
from functools import lru_cache
from pathlib import Path

from docintel.domain.parse.base import ParsedDoc, from_pages

DO_OCR = False  # native PDFs have a text layer; 3b turns this on for scans
DO_TABLES = False  # one contract lost a quote with tables on; 3b can test this


@lru_cache
def get_converter():
    """Build the converter once. The imports are here so that importing this file stays fast."""
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption

    options = PdfPipelineOptions(do_ocr=DO_OCR, do_table_structure=DO_TABLES)
    return DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)}
    )
```

*Python here: [an `import` inside a function](./py/phase-3a2.md#py-1) · [`@lru_cache`](./py/phase-1a.md#py-4).*

Here, we:

1. Set the two options from Step 2, at the top of the file.
2. Import Docling only when `get_converter` runs for the first time.
3. Build one converter, and reuse it for every contract.

Add to the bottom of `src/docintel/domain/parse/docling_parser.py`:

```python
def pages_of(document, n_pages: int) -> list[str]:
    """The Markdown of each page, from 1 to n_pages. A page with nothing on it is ""."""
    return [document.export_to_markdown(page_no=n) for n in range(1, n_pages + 1)]


def parse_docling(pdf_path: Path) -> ParsedDoc:
    start = time.perf_counter()
    result = get_converter().convert(pdf_path)
    pages = pages_of(result.document, result.input.page_count)
    latency_ms = round((time.perf_counter() - start) * 1000)
    return from_pages(pages, cost_usd=0.0, latency_ms=latency_ms, parser_name="docling")
```

Here, we:

1. Run the pipeline from Step 1.
2. Ask for each page by number. Docling's page numbers start at 1.
3. Return the same shape as pypdf. `pages_of` is a separate function so a test can use a fake document.

## Step 4: add it to the registry

**Why.** This is the promise from 3a: a new parser is one new line.

Update the imports at the top of `src/docintel/domain/parse/__init__.py`:

```python
from docintel.domain.parse.docling_parser import parse_docling
```

Then update the `PARSERS` line in the same file:

```python
PARSERS: dict[str, Parser] = {"pypdf": parse_pypdf, "docling": parse_docling}
```

Checkpoint. Guess first: is PyTorch loaded now?

```sh
uv run python - <<'EOF'
import sys

import docintel.domain.parse

print("docling loaded:", "docling.document_converter" in sys.modules)
print("torch loaded:", "torch" in sys.modules)
EOF
```

```text
docling loaded: False
torch loaded: False
```

The lazy import works. The heavy libraries load only when a contract is really parsed.

## Step 5: one small contract, with memory measured

**Why.** You have 8 GB. Start with 2 pages, and look at the memory before running more.

Close Jupyter and other heavy apps. The first run downloads the models, so it is slower. The later runs use the
saved files.

```sh
uv run python - <<'EOF'
import resource
from collections import Counter

from docintel.domain.parse import parse_doc
from docintel.domain.validate.citations import quote_status, words
from docintel.evals.store import connect

with connect() as con:
    doc_id, path = con.execute(
        "SELECT doc_id, pdf_path FROM contracts WHERE doc_id LIKE 'KUBIENT%'"
    ).fetchone()
    spans = [s for (s,) in con.execute(
        "SELECT span_text FROM labels WHERE doc_id = ? AND is_present AND span_text IS NOT NULL",
        [doc_id],
    ).fetchall()]
for name in ("pypdf", "docling"):
    doc = parse_doc(name, doc_id, path)
    source = words(doc.text)
    print(name, len(doc.pages), "pages,", len(doc.text), "chars,", doc.latency_ms, "ms,",
          dict(Counter(quote_status(s, source) for s in spans)))
print("peak memory GB:", round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e9, 2))
EOF
```

*Python here: [`resource.getrusage`](./py/phase-3a2.md#py-2).*

```text
pypdf 2 pages, 7590 chars, 20 ms, {'same_words': 13}
docling 2 pages, 8107 chars, 6634 ms, {'same_words': 13}
peak memory GB: 0.64
```

You may also see a warning about `HF_TOKEN`, and a note about `Redirects`. Both are harmless. If you chose
different options, your numbers will match the Step 2 table instead.

Here, read it like this:

1. Docling is about 300 times slower than pypdf on this contract. Most of that is loading models once.
2. The peak is about 1 GB or less, so 8 GB is enough, one document at a time.
3. On this normal PDF, Docling found no more quotes than pypdf. It earns its cost on scans, and 3b tests that.

Now the blank page from 3a:

```sh
uv run python - <<'EOF'
from docintel.domain.parse import parse_doc
from docintel.evals.store import connect

with connect() as con:
    doc_id, path = con.execute(
        "SELECT doc_id, pdf_path FROM contracts WHERE doc_id LIKE 'PACIFICSYSTEMS%'"
    ).fetchone()
print([len(p) for p in parse_doc("docling", doc_id, path).pages])
EOF
```

```text
[3954, 0]
```

The blank page keeps its place, the same as with pypdf.

If your Mac becomes very slow, or Docling is too slow for you, tell Claude your numbers. Then you can run Docling
only on the ~10 contracts from the 3a3 pilot, and not on all 52. That is your decision.

## Step 6: a small test

**Why.** Two rules could break without anyone noticing: page positions, and the fast import.

Put this in `tests/test_docling_parser.py`:

```python
"""The Docling wrapper, with a fake document. No models are loaded."""

import subprocess
import sys

from docintel.domain.parse.docling_parser import pages_of


class FakeDocument:
    def export_to_markdown(self, page_no):
        return {1: "first page", 3: "third page"}.get(page_no, "")


def test_every_page_keeps_its_place():
    assert pages_of(FakeDocument(), 3) == ["first page", "", "third page"]


def test_importing_the_parsers_does_not_load_torch():
    code = "import sys, docintel.domain.parse; sys.exit('torch' in sys.modules)"
    assert subprocess.run([sys.executable, "-c", code]).returncode == 0
```

*Python here: [a test that starts a new Python](./py/phase-3a2.md#py-3).*

Here, we use a new Python process for the import test. In the test run, another test may have loaded PyTorch
already, so `sys.modules` would not tell us anything.

Checkpoint:

```sh
uv run pytest tests/test_docling_parser.py tests/test_parse_cache.py -q
make lint
```

```text
.......                                                                  [100%]
7 passed in 0.25s
```

Your project structure should now look like this:

```text
src/docintel/domain/parse/
├── __init__.py          # PARSERS has 2 parsers
├── base.py
├── cache.py
├── docling_parser.py    # get_converter, pages_of, parse_docling
└── pypdf_parser.py
tests/
├── test_docling_parser.py
└── test_parse_cache.py
```

<details><summary>Full <code>src/docintel/domain/parse/docling_parser.py</code></summary>

```python
"""Parser 2: Docling. Local layout and OCR models, free but slow."""

import time
from functools import lru_cache
from pathlib import Path

from docintel.domain.parse.base import ParsedDoc, from_pages

DO_OCR = False  # native PDFs have a text layer; 3b turns this on for scans
DO_TABLES = False  # one contract lost a quote with tables on; 3b can test this


@lru_cache
def get_converter():
    """Build the converter once. The imports are here so that importing this file stays fast."""
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption

    options = PdfPipelineOptions(do_ocr=DO_OCR, do_table_structure=DO_TABLES)
    return DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)}
    )


def pages_of(document, n_pages: int) -> list[str]:
    """The Markdown of each page, from 1 to n_pages. A page with nothing on it is ""."""
    return [document.export_to_markdown(page_no=n) for n in range(1, n_pages + 1)]


def parse_docling(pdf_path: Path) -> ParsedDoc:
    start = time.perf_counter()
    result = get_converter().convert(pdf_path)
    pages = pages_of(result.document, result.input.page_count)
    latency_ms = round((time.perf_counter() - start) * 1000)
    return from_pages(pages, cost_usd=0.0, latency_ms=latency_ms, parser_name="docling")
```
</details>

## Break it on purpose

**Break 1: the old cache again.** Change `DO_TABLES` to the other value, and run the Step 5 command again. Guess:
does the `docling` line change?

<details><summary>What you see</summary>

The line does not change, and `ms` is the same as before. The cache key is `(parser, doc_id)`. It does not know
your options changed. Delete the folder and run again:

```sh
rm -rf data/parse_cache/docling
```

Now the line changes. This matters in 3b: OCR on and OCR off must not share a parser name. Change the value back.
</details>

**Break 2: the import at the top.** Move the three `docling` imports to the top of `docling_parser.py`. Guess: which
test fails?

<details><summary>What you see</summary>

`test_importing_the_parsers_does_not_load_torch` fails. Every command that imports the parser package now loads
PyTorch, even when it never parses anything. Move the imports back.
</details>

## Experiment

This part makes no `run_id`, and no entry of its own. Step 2's note goes into E3 in 3b. The Step 5 numbers are
measurements of your Mac, not a result about quality.

## Gotchas

- **Close the notebook first.** DuckDB allows one writer, and these scripts open the database.
- **Two runs at once use double the memory.** Run one document at a time on 8 GB.
- **`page_no` starts at 1.** Python lists start at 0, so `range(1, n + 1)` is correct.
- **Options are not part of the cache key.** After you change one, delete the folder (Break 1).

## Explain back, then commit

Explain to Claude in a few sentences:

- Step 1: the path from `convert` to the stages, and the real stage order.
- Your options in Step 2, with the numbers behind each one.
- `docling_parser.py`: why the imports are inside a function, and why `pages_of` is separate.
- `test_docling_parser.py`: why the import test starts a new Python.

Then:

```sh
git status
git add pyproject.toml uv.lock src/docintel/domain/parse tests/test_docling_parser.py
git commit -m "phase 3a2: Docling parser"
```

## Conclusion

You now have two parsers behind one interface, and you know what each Docling option costs on your Mac. Go back
through the objectives and check each one without notes. Then answer:

1. OCR was on and it changed nothing. Why will it matter in 3b?
2. Tables on lost a quote. Is that a Docling bug, or a limit of our check?

Looking for more challenges? Try these (optional):

1. Run Docling on all 52 dev contracts. Which contract is slowest per page?
2. Find another dev contract with a table, and repeat the Round 2 comparison.

Checklist (`../PLAN.md`): **Parsers: text layer vs layout vs multimodal; CER** (the layout part).
