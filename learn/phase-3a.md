# Phase 3a: the parser interface, pypdf and a disk cache

In this part, you start reading real PDFs. You build one interface for all parsers, the first parser
(pypdf) and a disk cache. You add one small piece at a time, with a checkpoint after each.

This is part 1 of 3 for Phase 3a. 3a2 adds Docling. 3a3 adds a vision LLM.

## Words used in this part

Read these first.

- **Parser**: code that turns a PDF into text. Example: PDF in, `"SPONSORSHIP AGREEMENT..."` out.
- **Text layer**: the characters stored inside a PDF, next to the picture of the page. A PDF made by
  Word has one. You can select its text with the mouse.
- **Scan**: a PDF that is only a picture of paper. It has no text layer.
- **Interface**: the shape that every parser must follow. Like a TypeScript `interface`.
- **Registry**: a dict from a name to a function. Example: `"pypdf"` gives `parse_pypdf`. Like a map of
  Express route handlers.
- **Disk cache**: results saved in files, so the work runs only once.
- **Cache key**: what makes one saved result different from another. Ours is `(parser, doc_id)`.
- **Cache hit / cache miss**: hit means the result is already saved. Miss means it is not.
- **Latency**: how long something took, in milliseconds.

## Objectives

By the end of this part you should be able to:

1. Say what `ParsedDoc` holds, and why every parser returns the same shape.
2. Explain what pypdf can and cannot read.
3. Explain the cache key, and why a cache hit still reports the old cost.
4. Show with real numbers why "same length" does not mean "same text".
5. Add a new parser with one new line in the registry.

## Dependencies

You install nothing new. `pypdf` has been in the project since 0a. This part needs:

- 0b: the `contracts` table, with `pdf_path` and `txt_path`.
- 2a: `words` and `quote_status` in `domain/validate/citations.py`.
- The CUAD PDFs in `data/raw/`.

## The big picture

Until now, the pipeline started from text that CUAD gave us:

```text
CUAD .txt -> extract -> validate -> cited JSON
```

Real users upload PDFs. After this part, the first step exists:

```text
PDF -> parse_doc("pypdf", doc_id, path) -> ParsedDoc -> (3b) extract -> validate -> cited JSON
                     |
          data/parse_cache/ (work runs once)
```

- **3a2 and 3a3** add one parser each, behind the same interface.
- **3b** runs all parsers through the pipeline and compares them.
- **Phase 4** calls `parse_doc` when a user uploads a PDF.

## Remember this

> Every parser gives back the same shape, so the rest of the pipeline never knows which one ran.
> The disk cache saves each result once, for each parser and document, with its first cost. So paid
> work is never paid for twice, and the cost report stays true.
>
> **One shape in, one shape out, pay once.**

## Why

**We need a fair comparison.** 3b changes only the parser. If each parser returned a different shape,
the rest of the code would change too. Then we could not say what caused a change in F1.

**Parsing can cost money.** The vision LLM in 3a3 charges per page. Running an experiment again must
not charge again.

**Parsing can be slow.** On your Mac, Docling takes much longer than pypdf (you measure this in 3a2).
The cache means you wait once.

## Design decisions

- **A function for each parser.** A parser is a function: path in, `ParsedDoc` out. Other option: a base
  class with subclasses. That adds code, and the parsers share no state.
- **Pydantic for `ParsedDoc`.** The cache stores it as JSON and reads it back. Pydantic does both, and
  it checks the file. Other option: a dataclass. Then you write the JSON code and the checks yourself.
- **`from_pages` builds every result.** `text` is made from `pages`, so the two cannot disagree. Other
  option: each parser joins pages itself. Three parsers, three chances for a bug.
- **The registry is a plain dict.** `runner.py` already does this with `PARSERS`. Other option: decorators
  that register functions. They hide what is registered.
- **The cache file name is the `doc_id`.** The file stays readable. The longest `doc_id` is 161 bytes
  (limit 255), and none has a `/`. Other option: a hash of the id. Safe, but you cannot see which file
  is which.
- **A cache hit returns the stored cost and latency.** They describe what the text really cost. Other
  option: return 0 on a hit. Then a second run would report a free parser.
- **Write to a temp file, then rename.** A rename happens all at once. If the program dies during a
  write, no half file is left under the real name. Other option: write directly, and risk half a file.
- **A broken cache file is an error.** Other option: parse again without saying anything. For a paid
  parser, that silently spends money.
- **The cache does not look at the parser's code.** Other option: add a code version to the key. That
  is more to maintain. You delete the cache when a parser changes (Break 2).

## Worked example

This is real dev data. Guess before you open each box.

### Round 1: an empty page

pypdf reads the 2-page Pacific Systems contract. The characters per page are `[4104, 0]`. CUAD's `.txt`
for this contract has 4,066 characters. Did pypdf lose a page?

<details><summary>Guess, then open</summary>

No. Page 2 is really blank. Drawn as an image, every pixel on it is white. The total length matches
CUAD's text, so nothing is missing. An empty page is not always a failure, so `pages` must keep the
blank page in its place.
</details>

### Round 2: a small word

This is the Eco Science sponsorship contract. The lawyer's label for Agreement Date is `1st day of
April, 2018`. Here is the same place in both texts:

```text
CUAD .txt:  ... made effective this 1st day of April, 2018 ("Eff
pypdf:      ... made effective this 1 st day of April, 2018 ("Eff
```

Our citation check from 2a compares words. Guess: does it find this quote in the pypdf text?

<details><summary>Guess, then open</summary>

No. `quote_status` returns `missing`. The "st" is printed small and raised in the PDF, so pypdf treats
it as a separate piece of text. `words()` then gives `["1", "st", ...]`, and the quote has `["1st",
...]`. The text looks almost right, but the check fails. In 3b, this could flag a correct answer.
</details>

### Round 3: the second run

A paid parser reads a contract for $0.25 and takes 900 ms. You run it again and get a cache hit. No call
is made. What should `cost_usd` say on the second run?

<details><summary>Guess, then open</summary>

$0.25. `cost_usd` means "what this text cost to make". 3b reports cost per document for each parser.
If a hit said $0, the second run of the experiment would make the paid parser look free.
</details>

## Project setup

From the project root:

```sh
mkdir -p src/docintel/domain/parse
touch src/docintel/domain/parse/__init__.py
touch src/docintel/domain/parse/base.py
touch src/docintel/domain/parse/pypdf_parser.py
touch src/docintel/domain/parse/cache.py
touch tests/test_parse_cache.py
```

You should now have:

```text
src/docintel/domain/parse/
├── __init__.py
├── base.py
├── cache.py
└── pypdf_parser.py
tests/
└── test_parse_cache.py
```

We do not name a file `pypdf.py`. A file with the same name as a library makes import errors hard to
read.

## Step 1: the shape of a parsed document (your decision)

**Why.** Everything after the parser reads this shape, so it is the most important choice in this part.

The plan fixes five fields: `text`, `pages`, `cost_usd`, `latency_ms` and `parser_name`. You decide what
`pages` is.

What to look at:

- Round 1: a blank page is real, and it has a position.
- The vision LLM in 3a3 works one page at a time. One page can fail.
- 3b will compare a clean page with its fake scan.

The options:

1. **`pages: int`**, the count. It is the smallest. You cannot see which page went wrong.
2. **`pages: list[str]`**, the text of each page. A blank page is `""`. It holds the text twice, in `text`
   and in `pages`.
3. **`pages: list[Page]`**, an object with number, text and more. It is flexible, but nothing needs the
   extra fields yet.

Also decide what goes between pages in `text`.

Write your version in `src/docintel/domain/parse/base.py`. Also write a helper that builds a `ParsedDoc`
from pages. Then compare.

<details><summary>Reference (open after you write yours)</summary>

Put this in `src/docintel/domain/parse/base.py`:

```python
"""The one shape that every parser gives back."""

from collections.abc import Callable
from pathlib import Path

from pydantic import BaseModel, ConfigDict

PAGE_BREAK = "\n\n"


class ParsedDoc(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str  # all pages, joined with PAGE_BREAK
    pages: list[str]  # the text of each page; a blank page is ""
    cost_usd: float
    latency_ms: int
    parser_name: str


Parser = Callable[[Path], ParsedDoc]


def from_pages(pages: list[str], cost_usd: float, latency_ms: int, parser_name: str) -> ParsedDoc:
    """Build a ParsedDoc, so `text` and `pages` can never disagree."""
    return ParsedDoc(
        text=PAGE_BREAK.join(pages),
        pages=pages,
        cost_usd=cost_usd,
        latency_ms=latency_ms,
        parser_name=parser_name,
    )
```

Here, we choose option 2:

1. Each page keeps its position, even when blank.
2. `PAGE_BREAK` is a blank line. `words()` ignores spaces and new lines, so the citation check does not
   notice it.
3. `Parser` gives a name to "a function from a path to a `ParsedDoc`".

*Python here: [`Callable` and a type name](./py/phase-3a.md#py-1).*
</details>

The steps below use the reference names. If your names differ, change the code to match.

Checkpoint:

```sh
uv run python - <<'EOF'
from docintel.domain.parse.base import from_pages

doc = from_pages(["Page one.", "", "Page three."], cost_usd=0.0, latency_ms=3, parser_name="demo")
print(repr(doc.text))
print(len(doc.pages))
print(doc.model_dump_json())
EOF
```

```text
'Page one.\n\n\n\nPage three.'
3
{"text":"Page one.\n\n\n\nPage three.","pages":["Page one.","","Page three."],"cost_usd":0.0,"latency_ms":3,"parser_name":"demo"}
```

The blank page is still there. It counts as page 2.

## Step 2: the pypdf parser

**Why.** It is the free baseline. The other two parsers must beat it to be worth their cost.

Put this in `src/docintel/domain/parse/pypdf_parser.py`:

```python
"""Parser 1: copy the text that is stored inside the PDF. No model, free."""

import time
from pathlib import Path

from pypdf import PdfReader

from docintel.domain.parse.base import ParsedDoc, from_pages


def parse_pypdf(pdf_path: Path) -> ParsedDoc:
    start = time.perf_counter()
    pages = [page.extract_text() or "" for page in PdfReader(pdf_path).pages]
    latency_ms = round((time.perf_counter() - start) * 1000)
    return from_pages(pages, cost_usd=0.0, latency_ms=latency_ms, parser_name="pypdf")
```

*Python here: [`extract_text() or ""`](./py/phase-3a.md#py-2).*

Here, we:

1. Open the PDF and go through its pages in order.
2. Copy the stored text of each page. A page with no text gives `""`.
3. Measure the time, like `call_llm` does.
4. Set the cost to 0, because nothing is paid.

Checkpoint:

```sh
uv run python - <<'EOF'
from pathlib import Path

from docintel.domain.parse.pypdf_parser import parse_pypdf
from docintel.evals.store import connect

with connect() as con:
    (path,) = con.execute(
        "SELECT pdf_path FROM contracts WHERE doc_id LIKE 'EcoScienceSolutionsInc_20180406%'"
    ).fetchone()
doc = parse_pypdf(Path(path))
print(doc.parser_name, len(doc.pages), "pages,", len(doc.text), "chars,", doc.cost_usd, "USD,", doc.latency_ms, "ms")
print(repr(doc.text[:90]))
EOF
```

```text
pypdf 3 pages, 8020 chars, 0.0 USD, 18 ms
'SPONSORSHIP AGREEMENT\nThis agreement (the "Agreement") is made effective this 1 st day of '
```

Your `ms` will differ a little. You can see the `1 st` from Round 2.

## Step 3: the disk cache

**Why.** In 3a3, a page costs money. A saved result must never be paid for again.

Put this in `src/docintel/domain/parse/cache.py`:

```python
"""Disk cache: one JSON file per (parser, doc_id). A paid page is paid for only once."""

from pathlib import Path

from docintel.domain.parse.base import ParsedDoc, Parser

CACHE_DIR = Path("data/parse_cache")


def cache_path(parser_name: str, doc_id: str, cache_dir: Path = CACHE_DIR) -> Path:
    return cache_dir / parser_name / f"{doc_id}.json"
```

Here, we choose where a result lives: `data/parse_cache/<parser>/<doc_id>.json`. `data/` is in
`.gitignore`, so the cache never goes into git.

Add to the bottom of `src/docintel/domain/parse/cache.py`:

```python
def cached_parse(
    parser_name: str, doc_id: str, pdf_path: Path, parser: Parser, cache_dir: Path = CACHE_DIR
) -> ParsedDoc:
    """The stored result if there is one. If not, parse, store, and return."""
    path = cache_path(parser_name, doc_id, cache_dir)
    if path.exists():
        return ParsedDoc.model_validate_json(path.read_text(encoding="utf-8"))
    doc = parser(pdf_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(doc.model_dump_json(), encoding="utf-8")
    temp.replace(path)  # the file appears whole, or not at all
    return doc
```

*Python here: [`with_name` and `replace`](./py/phase-3a.md#py-3) · [JSON both ways](./phase-1c.md#py-3).*

Here, we:

1. Look for the file. If it exists, read it and return it. The parser does not run.
2. If not, run the parser.
3. Write the result to `<name>.json.tmp`.
4. Rename it to the real name.

The parser is passed in as a value. So a test can pass a fake parser, and the cache code does not know
about pypdf.

There is no checkpoint yet. `cached_parse` needs a parser name and a parser. Step 4 gives it both.

## Step 4: one front door

**Why.** The rest of the code should ask for a parser by name. Adding a parser should be one new line.

Put this in `src/docintel/domain/parse/__init__.py`:

```python
"""Parsers behind one interface. 3a2 and 3a3 add entries to PARSERS."""

from pathlib import Path

from docintel.domain.parse.base import ParsedDoc, Parser
from docintel.domain.parse.cache import cached_parse
from docintel.domain.parse.pypdf_parser import parse_pypdf

PARSERS: dict[str, Parser] = {"pypdf": parse_pypdf}


def parse_doc(parser_name: str, doc_id: str, pdf_path: Path | str) -> ParsedDoc:
    """Parse one contract with the named parser. Uses the cache."""
    return cached_parse(parser_name, doc_id, Path(pdf_path), PARSERS[parser_name])
```

*Python here: [code in `__init__.py`](./py/phase-3a.md#py-4).*

Here, we keep one rule: other code calls `parse_doc`. It does not call a parser directly.

Then update the comment on the `PARSERS` line in `src/docintel/evals/runner.py`. That dict is a
different one. It connects to these parsers in 3b:

```python
PARSERS = {"cuad_txt": cuad_txt}  # 3b adds the parsers from 3a
```

Checkpoint. Guess first: which call is faster, and does `latency_ms` change?

```sh
uv run python - <<'EOF'
import time

from docintel.domain.parse import parse_doc
from docintel.evals.store import connect

with connect() as con:
    doc_id, path = con.execute(
        "SELECT doc_id, pdf_path FROM contracts WHERE doc_id LIKE 'EcoScienceSolutionsInc_20180406%'"
    ).fetchone()
for i in (1, 2):
    start = time.perf_counter()
    doc = parse_doc("pypdf", doc_id, path)
    took = (time.perf_counter() - start) * 1000
    print(f"call {i}: took {took:.1f} ms, stored latency_ms={doc.latency_ms}, {len(doc.text)} chars")
EOF
find data/parse_cache -type f
```

```text
call 1: took 19.7 ms, stored latency_ms=18, 8020 chars
call 2: took 0.9 ms, stored latency_ms=18, 8020 chars
data/parse_cache/pypdf/EcoScienceSolutionsInc_20180406_8-K_EX-10.1_11135398_EX-10.1_Sponsorship Agreement.json
```

Call 2 is much faster, because it only read a file. `latency_ms` stays 18. It is the time the parse
really took.

## Step 5: how good is pypdf on the dev PDFs?

**Why.** You want to know what the free parser gives before you pay for anything.

Guess first. pypdf's text is 0.97 to 1.02 times the length of CUAD's `.txt` on all 52 dev contracts. Out
of 1,332 lawyer quotes, how many appear in pypdf's text exactly, character by character?

```sh
uv run python - <<'EOF'
from collections import Counter

from docintel.domain.parse import parse_doc
from docintel.domain.validate.citations import quote_status, words
from docintel.evals.store import connect

with connect() as con:
    docs = con.execute(
        "SELECT doc_id, pdf_path FROM contracts JOIN splits USING (doc_id) "
        "WHERE split = 'dev' ORDER BY doc_id"
    ).fetchall()
    spans = con.execute(
        "SELECT doc_id, span_text FROM labels JOIN splits USING (doc_id) "
        "WHERE split = 'dev' AND is_present AND span_text IS NOT NULL"
    ).fetchall()
parsed = {doc_id: parse_doc("pypdf", doc_id, path) for doc_id, path in docs}
source = {doc_id: words(doc.text) for doc_id, doc in parsed.items()}
print(len(parsed), "docs,", sum(len(d.pages) for d in parsed.values()), "pages,", sum(d.latency_ms for d in parsed.values()), "ms")
print("exact match:", sum(span in parsed[doc_id].text for doc_id, span in spans), "of", len(spans))
print(Counter(quote_status(span, source[doc_id]) for doc_id, span in spans))
EOF
```

```text
52 docs, 901 pages, 5593 ms
exact match: 266 of 1332
Counter({'same_words': 1310, 'missing': 15, 'no_words': 6, 'gap': 1})
```

Here, read it like this:

1. An exact match finds only 20% of the quotes. The length was almost equal, so length told us little.
2. The word check from 2a finds 98% (`same_words`).
3. The gap between them is mostly line breaks. pypdf keeps a `\n` at the end of each printed line.
   CUAD's text does not.
4. 15 quotes are `missing`, like `1 st` in Round 2. `no_words` means the quote has no letters or numbers.

So on these PDFs, the text layer loses very little. That is on clean PDFs. A scan has no text layer, and
pypdf returns nothing. 3b measures that.

## Step 6: a small test for the rules

**Why.** A broken cache would quietly spend money, or quietly report the wrong cost.

Put this in `tests/test_parse_cache.py`:

```python
"""The parser interface and the disk cache: rules that must never silently break."""

from pathlib import Path

from pypdf import PdfWriter

from docintel.domain.parse.base import ParsedDoc, from_pages
from docintel.domain.parse.cache import cached_parse
from docintel.domain.parse.pypdf_parser import parse_pypdf


class CountingParser:
    """A fake parser that counts its calls. It costs $0.25 each time."""

    def __init__(self):
        self.calls = 0

    def __call__(self, pdf_path: Path) -> ParsedDoc:
        self.calls += 1
        return from_pages(["page one", ""], cost_usd=0.25, latency_ms=900, parser_name="fake")


def test_text_is_the_pages_joined():
    doc = from_pages(["a", "", "c"], cost_usd=0.0, latency_ms=1, parser_name="fake")
    assert doc.text == "a\n\n\n\nc"
    assert len(doc.pages) == 3


def test_second_call_does_not_parse_and_keeps_the_real_cost(tmp_path):
    parser = CountingParser()
    first = cached_parse("fake", "doc-1", Path("x.pdf"), parser, tmp_path)
    second = cached_parse("fake", "doc-1", Path("x.pdf"), parser, tmp_path)
    assert parser.calls == 1
    assert second == first
    assert second.cost_usd == 0.25  # the text cost money once; a hit must not report $0


def test_two_parsers_do_not_share_a_cache_entry(tmp_path):
    parser = CountingParser()
    cached_parse("parser_a", "doc-1", Path("x.pdf"), parser, tmp_path)
    cached_parse("parser_b", "doc-1", Path("x.pdf"), parser, tmp_path)
    assert parser.calls == 2


def test_no_temp_file_is_left_behind(tmp_path):
    cached_parse("fake", "doc-1", Path("x.pdf"), CountingParser(), tmp_path)
    assert [p.name for p in (tmp_path / "fake").iterdir()] == ["doc-1.json"]


def test_pypdf_gives_one_entry_per_page(tmp_path):
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    writer.add_blank_page(width=200, height=200)
    pdf = tmp_path / "two_pages.pdf"
    writer.write(pdf)
    assert parse_pypdf(pdf).pages == ["", ""]  # a blank page keeps its place
```

*Python here: [a class you can call](./py/phase-3a.md#py-5) · [`tmp_path`](./py/phase-0b.md#py-8).*

Here, we test the fake parser's call count. That is the only way to prove the cache stopped a second
parse.

Checkpoint:

```sh
uv run pytest tests/test_parse_cache.py -q
make lint
```

```text
.....                                                                    [100%]
5 passed in 0.14s
```

`make lint` should also pass.

Your project structure should now look like this:

```text
src/docintel/domain/parse/
├── __init__.py          # PARSERS, parse_doc
├── base.py              # ParsedDoc, Parser, from_pages
├── cache.py             # cache_path, cached_parse
└── pypdf_parser.py      # parse_pypdf
tests/
└── test_parse_cache.py
data/parse_cache/pypdf/  # one JSON file per contract (not in git)
```

<details><summary>Full <code>src/docintel/domain/parse/cache.py</code></summary>

```python
"""Disk cache: one JSON file per (parser, doc_id). A paid page is paid for only once."""

from pathlib import Path

from docintel.domain.parse.base import ParsedDoc, Parser

CACHE_DIR = Path("data/parse_cache")


def cache_path(parser_name: str, doc_id: str, cache_dir: Path = CACHE_DIR) -> Path:
    return cache_dir / parser_name / f"{doc_id}.json"


def cached_parse(
    parser_name: str, doc_id: str, pdf_path: Path, parser: Parser, cache_dir: Path = CACHE_DIR
) -> ParsedDoc:
    """The stored result if there is one. If not, parse, store, and return."""
    path = cache_path(parser_name, doc_id, cache_dir)
    if path.exists():
        return ParsedDoc.model_validate_json(path.read_text(encoding="utf-8"))
    doc = parser(pdf_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(doc.model_dump_json(), encoding="utf-8")
    temp.replace(path)  # the file appears whole, or not at all
    return doc
```
</details>

## Break it on purpose

**Break 1: a broken cache file.** Cut the saved file in half. Guess: does `parse_doc` parse again?

```sh
uv run python - <<'EOF'
from docintel.domain.parse import parse_doc
from docintel.domain.parse.cache import cache_path
from docintel.evals.store import connect

with connect() as con:
    doc_id, path = con.execute(
        "SELECT doc_id, pdf_path FROM contracts WHERE doc_id LIKE 'EcoScienceSolutionsInc_20180406%'"
    ).fetchone()
p = cache_path("pypdf", doc_id)
p.write_text(p.read_text(encoding="utf-8")[:200], encoding="utf-8")
parse_doc("pypdf", doc_id, path)
EOF
```

<details><summary>What you see</summary>

```text
pydantic_core._pydantic_core.ValidationError: 1 validation error for ParsedDoc
  Invalid JSON: EOF while parsing a string at line 1 column 200 [type=json_invalid, input_value='{"text":"SPONSORSHIP AGR...Promoter\\") and Eco Sc', input_type=str]
```

It stops with an error, and it does not parse again. For pypdf that seems strict. For a paid parser, it
stops a quiet charge. Delete the file to repair it:

```sh
rm -rf data/parse_cache
```
</details>

**Break 2: an old result.** In `pypdf_parser.py`, change `page.extract_text() or ""` to
`(page.extract_text() or "").upper()`. Run the code below before the change, and again after it. Guess:
does the second print show capital letters?

```sh
uv run python - <<'EOF'
from docintel.domain.parse import parse_doc
from docintel.evals.store import connect

with connect() as con:
    doc_id, path = con.execute(
        "SELECT doc_id, pdf_path FROM contracts WHERE doc_id LIKE 'EcoScienceSolutionsInc_20180406%'"
    ).fetchone()
print(repr(parse_doc("pypdf", doc_id, path).text[:40]))
EOF
```

<details><summary>What you see</summary>

Both runs print the same line:

```text
'SPONSORSHIP AGREEMENT\nThis agreement (th'
```

The cache key does not know the parser's code changed. So you keep getting the old text. After you
change a parser, delete its folder: `rm -rf data/parse_cache/pypdf`. Undo the change now.
</details>

## Experiment

This part makes no `run_id`, and no `EXPERIMENTS.md` entry. Step 5 only looks at the text. The first
entry for parsers is E3.0 in 3a3, and the full comparison is E3 in 3b.

## Gotchas

- **Run from the project root.** `pdf_path` and `CACHE_DIR` are relative paths.
- **Close the notebook first.** DuckDB allows one writer at a time, and `connect()` opens for writing.
- **Warning for 3b.** A fake scan of a contract needs its own `doc_id`. With the same `doc_id`, the cache
  returns the clean text, and the experiment means nothing.
- **Length is a weak check.** Step 5 shows it. Use the word check, and later CER.

## Explain back, then commit

Explain to Claude in a few sentences:

- `base.py`: why `pages` has this shape, and how `from_pages` protects it.
- `pypdf_parser.py`: what it can read, and what it cannot.
- `cache.py`: the key, what a hit returns, and why the rename comes last.
- `__init__.py`: how you add a parser.
- `test_parse_cache.py`: which rule each test protects.
- Step 5: why exact match says 20% and the word check says 98%.

Then:

```sh
git status
git add src/docintel/domain/parse tests/test_parse_cache.py src/docintel/evals/runner.py
git commit -m "phase 3a: parser interface, pypdf, disk cache"
```

## Conclusion

You now have one interface for parsers, a free parser that reads the text layer, and a cache that pays
once. Go back to the objectives and check each one without notes. Then answer:

1. A cache hit returns `cost_usd = 0.25`, but nothing was charged. Why is that the correct answer?
2. `quote_status` says `missing` for `1st day of April`. Is the model wrong, the parser wrong, or neither?

Looking for more challenges? Try these (optional):

1. List the 15 `missing` quotes. How many come from raised letters like `1 st`?
2. Which dev contract has the largest share of `missing` quotes, and why?

Checklist (`../PLAN.md`): **Parsers: text layer vs layout vs multimodal; CER** (the text layer part).
