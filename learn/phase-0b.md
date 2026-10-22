# Phase 0b: data loader

In this part, you put the 510 CUAD contracts into a database. You write the code one small
function at a time. After each function, you run it on the real data and look at the result.

## Words used in this part

Read these first. The rest of the doc uses them a lot.

- **Contract**: a legal agreement between companies. CUAD has 510 of them.
- **Category**: one of the 41 questions CUAD asks about every contract. Examples: "Governing
  Law", "Parties", "Expiration Date".
- **Label**: one answer a lawyer gave. The lawyer read the contract and highlighted the text that
  answers a category.
- **Span**: the exact piece of text the lawyer highlighted. Example: "governed by the laws of
  Delaware".
- **Offset**: a position number inside the text. Offset 0 is the first character, offset 1 is the
  second, and so on. Like an array index in JS.
- **Present / absent**: present means the lawyer found an answer. Absent means the lawyer looked
  and the contract does not have one. Example: a contract with no end date.
- **DuckDB**: a database that is just one file on your disk. No server to start. Like SQLite.
- **Table, row**: a table is like a sheet in Excel. A row is one line in that sheet.
- **Invariant**: a rule that must always be true. If it breaks, something is wrong. Tests check
  invariants.

## Objectives

By the end of this part you should be able to:

1. Show how one contract in the CUAD JSON file turns into rows in two tables, `contracts` and
   `labels`.
2. Explain why `labels` has one row per span, and why an absent answer still gets a row.
3. Use `start_char` and `end_char` to cut the lawyer's exact text out of a contract.
4. Match file names that are spelled a little differently, without writing a special case for
   each one.
5. Ask questions of the two tables with SQL, from Python and from the DuckDB command line.

## Dependencies

You install nothing new. Part 0a already added these:

- `duckdb`: the database.
- `pypdf`: reads PDF files. We use it to count pages. The test also uses it to make fake PDFs.
- `pytest`: runs the tests. Like Jest.

The CUAD data is already unzipped in `data/raw/CUAD_v1/`. Nothing downloads again.

## The big picture

Right now, the `docintel` package has no code. At the end of this part, `make data` prints
`Loaded 510 contracts, 28031 label rows`.

Every later part reads these two tables:

- 0c looks at the data and picks the fields we care about.
- 1b checks the model's answers against `labels`. `labels` is the answer key.
- 2a uses the offsets to check that the model's quotes are real.

## Remember this

> A label is a piece of text plus its address: the exact words, and the position where they start
> in the contract. We save one row for each piece of text. When the lawyer found nothing, we still
> save a row that says "absent". That way we can count "not there" too. The positions let us check
> any quote against the real contract.
>
> **One row per span, absent is a row, offsets are proof.**

## Why

**CUAD answers are pieces of text, not simple values.** The lawyers did not write "Pennsylvania".
They highlighted a sentence: "...governed by the laws of the Commonwealth of Pennsylvania". So our
model must also give two things back: the value, and the exact sentence it came from.

**The JSON file is deeply nested.** It was made for a research task, not for us. The answers sit
inside lists, inside lists, inside objects. If we turn it into simple tables once, then every
later question is one short SQL query. Without that, every question needs a page of loops.

**The labels are the answer key.** We do not add or change anything. Later, we compare the model's
answers with these rows, one category at a time. Did it find the answer? Is it the right text? Is
the quote real?

## Design decisions

For each choice: what we picked, why, and what else we could have picked.

- **DuckDB.** It is one file, with no server. It is fast at counting and grouping. Other options:
  Postgres needs a server (we use it later, in Phase 4, for the live app). CSV files with pandas
  have no SQL and no column types.
- **Two tables.** Some facts exist once per contract, like the page count. Labels exist many
  times per contract. So we use two tables, like `users` and `orders` in a shop app. They link by
  `doc_id`.
- **Long, not wide.** "Long" means one row per span, so many rows (28,031). "Wide" means one row
  per contract with one column per category. CUAD ships a wide file too: `master_clauses.csv`,
  with 83 columns. With long data, most questions are one `GROUP BY category`. With wide data, you
  must loop over 83 columns.
- **Absent is a row.** The row has `is_present = false` and an empty (NULL) span. Why? If the
  model says "not found" and the lawyer also found nothing, the model is right. We can only count
  that correct answer if the row exists.
- **We keep the offsets.** `text[start:end] == span` must be true for every label. Part 2a uses
  this to check that a quote is real.
- **Where each column comes from.** `doc_id` is the `title` in the JSON (the file name without
  `.txt`). `contract_type` is the name of the folder that holds the PDF. `title` comes from the
  CSV file. `n_pages` comes from the PDF. Labels come only from the JSON.
- **Read first, save second.** The `iter_*` functions only read the files and give back plain
  dicts. A different function, `load_cuad`, saves them. So you can look at rows without a
  database. Every checkpoint below does this.
- **`CREATE OR REPLACE`.** Running the loader again deletes the old tables and builds new ones.
  Like a seed script in a JS project.
- **md5 check and a `.part` file.** md5 is a short code computed from a file's bytes, like a
  fingerprint. If the download is broken, the fingerprint is different, and we stop. The `.part`
  file makes sure a half-finished download never looks like a full one.

## Worked example

This is real CUAD data. Guess the answer before you open each box.

The zip unpacks into this:

```
data/raw/CUAD_v1/
  CUAD_v1.json            40 MB, every label (SQuAD style)
  master_clauses.csv      the same labels, wide
  full_contract_txt/      510 .txt files, the text the offsets point into
  full_contract_pdf/      Part_I, Part_II, Part_III / <Contract Type> / *.pdf
  label_group_xlsx/       per-category spreadsheets (we ignore these)
```

Here is one contract inside `CUAD_v1.json`. The `...` parts are cut out to save space:

```json
{"title": "FEDERATEDGOVERNMENTINCOMESECURITIESINC_04_28_2020-EX-99.SERV AGREE-SERVICES AGREEMENT_SECONDAMENDMENT",
 "paragraphs": [{
   "context": "SECOND AMENDMENT TO SERVICES AGREEMENT This SECOND AMENDMENT ... (5,466 chars)",
   "qas": [
     {"id": "FEDERATED...SECONDAMENDMENT__Governing Law",
      "question": "Highlight the parts (if any) of this contract related to \"Governing Law\" ...",
      "answers": [{"text": "This Second Amendment shall be governed by and construed in accordance with the laws of the Commonwealth of Pennsylvania.",
                   "answer_start": 4740}],
      "is_impossible": false},
     {"id": "FEDERATED...SECONDAMENDMENT__Expiration Date", "answers": [], "is_impossible": true},
     "... 39 more, one per category"]}]}
```

How to read it:

- `context` is the full text of the contract.
- `qas` is the list of 41 questions and their answers.
- Each answer has `text` (the span) and `answer_start` (the offset where the span begins).
- `answers: []` (an empty list) means the lawyer found nothing. That category is absent.

### Round 1: what is `answer_start`?

The Governing Law answer has `answer_start: 4740`. Its text is 121 characters long. What do you get
from `context[4740:4861]`? What do we save in `start_char` and `end_char`?

<details><summary>Guess, then open</summary>

You get exactly the answer text. Counting starts at 0. The end number is not included. This is the
same as JS `context.slice(4740, 4861)`.

CUAD only gives the start. So we compute the end ourselves: `end_char = start + len(text)`. We
checked all 13,823 present spans this way, and every one matches.
</details>

### Round 2: how many `labels` rows?

Every contract gets the same 41 questions. In this contract, Parties has 4 answers
(`FEDERATED INVESTMENT MANAGEMENT COMPANY`, `"Adviser"`, `FEDERATED ADVISORY SERVICES COMPANY`,
`"FASC"`). Expiration Date has 0 answers. How many rows does each one make?

<details><summary>Guess, then open</summary>

Parties makes 4 rows, one per answer. The short nicknames count too.

Expiration Date makes 1 row. That row has `is_present = false`, and the span and offsets are empty
(NULL).

So every contract has at least 41 rows. Some categories have many answers, so the total is 28,031.
That is more than 510 times 41 = 20,910.
</details>

### Round 3: file names that almost match

We need the PDF for each contract. To find it, we look for the JSON `title` among the PDF file
names. If we only accept an exact match, 5 of the 510 contracts find no PDF. Here are the real
cases:

| JSON title (= .txt name) | PDF / CSV name |
|---|---|
| `Principal Life ... Servicing Agreement` | `... Servicing Agreement .PDF` (space, caps) |
| `NETGEAR,INC_..._BETWEEN INGRAM MICRO AND NETGEAR` | `..._AND NETGEAR-.pdf` |
| `LECLANCHÉ S.A. - JOINT DEVELOPMENT ...` | same on screen, different bytes |
| `HarpoonTherapeuticsInc_..._Development Agreement` | `..._Development Agreement_Option Agreement.pdf` |
| `MOELIS_CO_...` (title, for the CSV) | `MOELIS&CO_...PDF` |

How can you match all of them without a special `if` for each one?

<details><summary>Guess, then open</summary>

We make a simple "key" from each name with a function called `_key`. The key keeps only lowercase
English letters and digits. Spaces, `-`, `&`, `_` and capital letters all go away. Now
`MOELIS&CO` and `MOELIS_CO` both become `moelisco`.

The `É` case is harder. A computer can store `É` in two ways:

1. As one character: `É`.
2. As two characters: a plain `E`, then a separate accent mark.

Both look the same on screen, but the bytes are different. The JSON uses way 2. The PDF name uses
way 1. **NFKD** is a Python function that changes both names to way 2. Then we throw away every
character that is not plain English. The accent goes away, and both names become a plain `E`.

The key fixes 4 of the 5 cases.

Harpoon is the last one. Its PDF name has extra words at the end. So `_lookup` has a backup plan.
If there is no exact match, it looks for a key that starts with our key. If exactly one key does,
we use it. If two or more do, we return `None`, because guessing could pick the wrong contract.

Result: 0 of 510 contracts miss their PDF.
</details>

## Project setup

First, delete the old loader. You will type it again in the shared layout. In that layout, code
for offline tests of the pipeline ("evals") lives in `evals/`.

```sh
rm -rf src/docintel/data src/docintel/store tests/test_data_load.py
git status --short    # if any of those show as staged (A), run: git reset -q
```

Now create the new files. They are all empty for now:

```sh
mkdir -p src/docintel/evals
touch src/docintel/evals/__init__.py src/docintel/evals/store.py \
        src/docintel/evals/datasets.py tests/test_data_load.py
```

> Careful with the name `__init__.py`: two underscores, then `init`, then two underscores.
> Markdown shows `__init__` without backticks as bold **init**, so always copy file names from a
> code block. A file called `init.py` is wrong. Fix it with
> `mv src/docintel/evals/init.py src/docintel/evals/__init__.py`.

A **docstring** is a text in quotes at the top of a file or function. It says what the code is
for. Put this one-line docstring in `src/docintel/evals/__init__.py`:

```python
"""Offline evaluation: datasets, the DuckDB store, later scorers and the runner."""
```

You should now have:

```
src/docintel/
├── __init__.py
└── evals/
    ├── __init__.py        docstring only
    ├── datasets.py        empty: download, parse, load CUAD
    └── store.py           empty: open the DuckDB file
tests/
├── test_data_load.py      empty
└── test_smoke.py
```

Each step below works the same way:

1. Add some code.
2. Read what it does.
3. Run the checkpoint on the real data.

Run every checkpoint from the repo root (the top folder of the project). Do not go to the next step
until your output matches.

## Step 1: connect to DuckDB

**Why.** Only one function opens the database. That makes it easy for tests to use a temporary
database instead of the real one.

Put this in `src/docintel/evals/store.py`:

```python
"""DuckDB connection helper. One database file for the whole project."""

from pathlib import Path

import duckdb

DB_PATH = Path("data/docintel.duckdb")


def connect(path: Path | str = DB_PATH) -> duckdb.DuckDBPyConnection:
    """Open (or create) the project database. Pass ":memory:" for a throwaway one in tests."""
    if str(path) != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(path))
```

*Python here: [pathlib](./py/phase-0b.md#py-1) · [type hints](./py/phase-0b.md#py-2).*

Here, we:

1. Use `data/docintel.duckdb` when you do not give a path. That is the project's database file.
2. Make the `data/` folder if it does not exist. The `data/` folder is not in git, so a fresh copy
   of the repo does not have it. DuckDB cannot make a file inside a missing folder.
3. Skip making the folder when the path is `":memory:"`. This is a special name in DuckDB. It
   means: keep the database in RAM only, not in a file. It is gone when the program stops. Tests
   use it. There is no file, so there is no folder to make.

Checkpoint:

```sh
uv run python -c "from docintel.evals.store import connect; print(connect(':memory:').execute('SELECT 41 + 1').fetchone())"
```

```text
(42,)
```

## Step 2: match file names that almost match

**Why.** Without this, 5 contracts lose their PDF. Then they also lose their page count and their
contract type.

Put this in `src/docintel/evals/datasets.py`:

```python
"""CUAD v1: download it, parse it, load it into DuckDB. Run: `make data`."""

import re
import unicodedata


def _key(name: str) -> str:
    """Fuzzy file-name key: lowercase ASCII letters and digits only."""
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^0-9a-z]", "", ascii_name.lower())


def _lookup(table: dict, stem: str):
    """Exact key match, else the single key that starts with ours, else None."""
    k = _key(stem)
    if k in table:
        return table[k]
    hits = [value for key, value in table.items() if key.startswith(k)]
    return hits[0] if len(hits) == 1 else None
```

*Python here: [comprehensions](./py/phase-0b.md#py-4).*

Here, we:

1. Make a simple key from any name with `_key` (see Round 3):
   - `normalize("NFKD", ...)` splits letters like `É` into `E` + accent.
   - `.encode("ascii", "ignore")` throws away anything that is not plain English, like the
     accent.
   - `re.sub(r"[^0-9a-z]", "", ...)` removes everything that is not a lowercase letter or a digit.
     `re` is Python's regex module.
2. Find a match with `_lookup`. First it tries the exact key. If that fails, it looks for keys that
   start with ours. It uses the match only if there is exactly one.

The `_` at the start of `_key` means "only for use inside this file". Python does not enforce
this. It is a naming habit that everyone follows.

Checkpoint. Guess the three keys first:

```sh
uv run python -c "from docintel.evals.datasets import _key; print(_key('MOELIS&CO_x'), _key('MOELIS_CO_x'), _key('LECLANCHÉ S.A. - A&R AGREEMENT '))"
```

```text
moeliscox moeliscox leclanchesaaragreement
```

## Step 3: one row per contract

**Why.** The `contracts` table holds the facts that exist only once per contract: title, type,
page count, length, file paths.

Change the imports at the top of `datasets.py` to this:

```python
import csv
import json
import re
import unicodedata
from pathlib import Path

from pypdf import PdfReader
```

Add this to the bottom:

```python
def find_pdfs(cuad_dir: Path) -> dict[str, tuple[Path, str]]:
    """key -> (pdf_path, contract_type). The type is the PDF's parent folder name."""
    pdfs = (cuad_dir / "full_contract_pdf").rglob("*")
    return {_key(p.stem): (p, p.parent.name) for p in pdfs if p.suffix.lower() == ".pdf"}


def read_titles(cuad_dir: Path) -> dict[str, str]:
    """key -> readable title ("Document Name-Answer" in master_clauses.csv)."""
    with (cuad_dir / "master_clauses.csv").open(newline="", encoding="utf-8") as f:
        rows = csv.DictReader(f)
        return {_key(Path(r["Filename"]).stem): r["Document Name-Answer"].strip() for r in rows}


def count_pages(pdf_path: Path | None) -> int | None:
    try:
        return len(PdfReader(pdf_path).pages) if pdf_path else None
    except Exception:  # one broken PDF must not stop the load
        return None


def read_docs(cuad_dir: Path) -> list[dict]:
    return json.loads((cuad_dir / "CUAD_v1.json").read_text(encoding="utf-8"))["data"]


def iter_contracts(cuad_dir: Path):
    """Yield one row per contract for the `contracts` table."""
    pdfs, titles = find_pdfs(cuad_dir), read_titles(cuad_dir)
    for doc in read_docs(cuad_dir):
        stem = doc["title"]  # file name without extension; becomes doc_id
        pdf_path, contract_type = _lookup(pdfs, stem) or (None, None)
        txt_path = cuad_dir / "full_contract_txt" / f"{stem}.txt"
        yield {
            "doc_id": stem,
            "title": _lookup(titles, stem) or stem,
            "contract_type": contract_type,
            "n_pages": count_pages(pdf_path),
            "n_chars": len(doc["paragraphs"][0]["context"]),
            "txt_path": str(txt_path) if txt_path.exists() else None,
            "pdf_path": str(pdf_path) if pdf_path else None,
        }
```

*Python here: [`with`](./py/phase-0b.md#py-3) · [generators and `yield`](./py/phase-0b.md#py-5) ·
[dict `|` and `or`](./py/phase-0b.md#py-6).*

Here, we:

1. Build two lookup dicts. Both use `_key` names as keys.
   - `find_pdfs`: key → (PDF path, contract type). The contract type is the name of the folder the
     PDF sits in.
   - `read_titles`: key → nice title from the CSV file.
2. Read the JSON file once with `read_docs`.
3. Go through the contracts in `iter_contracts`. For each one, `yield` gives back one dict, which
   is one future row.
4. Catch every error in `count_pages`. If one PDF is broken, we get `None` for its page count.
   The other 509 contracts still load.

Checkpoint. Print the first contract:

```sh
uv run python -c "
from pathlib import Path
from docintel.evals.datasets import iter_contracts
print(next(iter_contracts(Path('data/raw/CUAD_v1'))))"
```

You should see this (we split it over several lines here so it is easier to read):

```python
{'doc_id': 'LIMEENERGYCO_09_09_1999-EX-10-DISTRIBUTOR AGREEMENT',
 'title': 'DISTRIBUTOR  AGREEMENT', 'contract_type': 'Distributor', 'n_pages': 10,
 'n_chars': 54290,
 'txt_path': 'data/raw/CUAD_v1/full_contract_txt/LIMEENERGYCO_09_09_1999-EX-10-DISTRIBUTOR AGREEMENT.txt',
 'pdf_path': 'data/raw/CUAD_v1/full_contract_pdf/Part_III/Distributor/LIMEENERGYCO_09_09_1999-EX-10-DISTRIBUTOR AGREEMENT.PDF'}
```

`contract_type` is `Distributor` because the PDF is in the folder `.../Part_III/Distributor/`.

## Step 4: one row per label

**Why.** This is the answer key. Each span gets one row. Each absent category also gets one row.

Add this to the bottom of `datasets.py`:

```python
ABSENT = {"span_text": None, "start_char": None, "end_char": None, "is_present": False}


def iter_labels(cuad_dir: Path):
    """Yield one row per answer span. No answer -> one ABSENT row, so "absent" is countable."""
    for doc in read_docs(cuad_dir):
        for qa in doc["paragraphs"][0]["qas"]:
            row = {"doc_id": doc["title"], "category": qa["id"].split("__")[-1]}
            if not qa["answers"]:
                yield row | ABSENT
            for ans in qa["answers"]:
                text, start = ans["text"], ans["answer_start"]
                yield row | {
                    "span_text": text,
                    "start_char": start,
                    "end_char": start + len(text),
                    "is_present": True,
                }
```

Here, we:

1. Get the category name from the question `id`. The `id` looks like `CONTRACTNAME__Governing Law`.
   We split it at `__` and keep the last part.
2. Give back one `ABSENT` row when the answer list is empty.
3. Otherwise, give back one row per answer, with `end_char` computed like in Round 1.

`row | ABSENT` makes a **new** dict that has the keys of both. The shared `ABSENT` dict never
changes.

Checkpoint. Guess both numbers before you run it:

```sh
uv run python -c "
from pathlib import Path
from docintel.evals.datasets import iter_labels
rows = list(iter_labels(Path('data/raw/CUAD_v1')))
print(len(rows), sum(r['is_present'] for r in rows))
print(rows[0])"
```

```text
28031 13823
{'doc_id': 'LIMEENERGYCO_09_09_1999-EX-10-DISTRIBUTOR AGREEMENT', 'category': 'Document Name', 'span_text': 'DISTRIBUTOR AGREEMENT', 'start_char': 44, 'end_char': 65, 'is_present': True}
```

There are 28,031 rows in total: 13,823 present spans and 14,208 absent rows. `sum` counts `True` as
1 and `False` as 0, so it counts the present rows.

## Step 5: save into DuckDB

**Why.** The rows must go into real tables, so every later part can ask questions with SQL.

Change the imports at the top of `datasets.py` to this:

```python
import csv
import json
import re
import unicodedata
from pathlib import Path

import duckdb
from pypdf import PdfReader
```

Add this to the bottom:

```python
SCHEMA = """
CREATE OR REPLACE TABLE contracts (
    doc_id VARCHAR PRIMARY KEY, title VARCHAR, contract_type VARCHAR,
    n_pages INTEGER, n_chars INTEGER, txt_path VARCHAR, pdf_path VARCHAR
);
CREATE OR REPLACE TABLE labels (
    doc_id VARCHAR, category VARCHAR, span_text VARCHAR,
    start_char INTEGER,  -- 0-based offset into the contract text
    end_char INTEGER,    -- exclusive, like JS str.slice(start, end)
    is_present BOOLEAN
);
"""


def load_cuad(con: duckdb.DuckDBPyConnection, cuad_dir: Path) -> tuple[int, int]:
    """(Re)create both tables. Returns (n_contracts, n_label_rows)."""
    con.execute(SCHEMA)
    contracts, labels = list(iter_contracts(cuad_dir)), list(iter_labels(cuad_dir))
    con.executemany(
        "INSERT INTO contracts VALUES ($doc_id, $title, $contract_type, $n_pages, $n_chars, "
        "$txt_path, $pdf_path)",
        contracts,
    )
    con.executemany(
        "INSERT INTO labels VALUES ($doc_id, $category, $span_text, $start_char, $end_char, "
        "$is_present)",
        labels,
    )
    return len(contracts), len(labels)
```

The **schema** is the list of tables and their columns, with a type for each column (`VARCHAR` is
text, `INTEGER` is a whole number, `BOOLEAN` is true/false).

Here, we:

1. Create both tables (or replace them if they already exist).
2. Collect all rows from `iter_contracts` and `iter_labels` into two lists.
3. Insert all rows at once with `executemany`. Each `$doc_id`-style placeholder gets its value
   from the dict key with the same name.

Never build SQL by pasting values into the string (with f-strings). A contract title with a `'` in
it would break the query. Placeholders handle this safely.

Checkpoint. Load into a temporary in-memory database, and ask the first real question:

```sh
uv run python -c "
from pathlib import Path
from docintel.evals.datasets import load_cuad
from docintel.evals.store import connect
with connect(':memory:') as con:
    print(load_cuad(con, Path('data/raw/CUAD_v1')))
    print(con.sql('SELECT category, count(*) AS n FROM labels WHERE is_present GROUP BY category ORDER BY n DESC LIMIT 3'))"
```

```text
(510, 28031)
┌──────────────────┬───────┐
│     category     │   n   │
│     varchar      │ int64 │
├──────────────────┼───────┤
│ Parties          │  2554 │
│ License Grant    │   777 │
│ Cap On Liability │   672 │
└──────────────────┴───────┘
```

This takes 10 to 20 seconds. Opening 510 PDFs to count pages is the slow part. Look at the SQL:
one `GROUP BY` answers "which categories have the most answers?". This is why we chose long
tables.

## Step 6: download and `make data`

**Why.** Someone with a fresh copy of the repo should get loaded tables with one command.

Change the imports at the top of `datasets.py` to this. The last line is new: it imports from our
own package.

```python
import csv
import hashlib
import json
import re
import unicodedata
import urllib.request
import zipfile
from pathlib import Path

import duckdb
from pypdf import PdfReader

from docintel.evals.store import connect
```

Add this below the imports, above `_key`:

```python
CUAD_URL = "https://zenodo.org/records/4595826/files/CUAD_v1.zip?download=1"
CUAD_MD5 = "c38f490a984420b8a62600db401fafd5"
RAW_DIR = Path("data/raw")


def _md5(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):  # 1 MB at a time
            h.update(chunk)
    return h.hexdigest()


def download_cuad(raw_dir: Path = RAW_DIR) -> Path:
    """Fetch + verify + unzip CUAD once. Returns the CUAD_v1/ folder."""
    out_dir, zip_path = raw_dir / "CUAD_v1", raw_dir / "CUAD_v1.zip"
    if out_dir.exists():
        return out_dir
    raw_dir.mkdir(parents=True, exist_ok=True)
    if not zip_path.exists():
        print(f"Downloading {CUAD_URL} (~106 MB) ...")
        tmp = zip_path.with_suffix(".part")  # a crash leaves a .part, never a broken .zip
        urllib.request.urlretrieve(CUAD_URL, tmp)
        tmp.rename(zip_path)
    if _md5(zip_path) != CUAD_MD5:
        raise RuntimeError(f"md5 mismatch for {zip_path}; delete it and retry")
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(raw_dir)
    return out_dir
```

Add this to the bottom:

```python
def main() -> None:
    cuad_dir = download_cuad()
    with connect() as con:
        n_contracts, n_labels = load_cuad(con, cuad_dir)
    print(f"Loaded {n_contracts} contracts, {n_labels} label rows")


if __name__ == "__main__":
    main()
```

*Python here: [`__name__ == "__main__"`](./py/phase-0b.md#py-7).*

Here, we:

1. Stop early in `download_cuad` if the `CUAD_v1/` folder already exists. That is why nothing
   downloads again.
2. Download into a `.part` file first, and rename it to `.zip` only when the download is complete.
   If the download crashes, you only have a `.part` file, never a broken `.zip`.
3. Compute the md5 fingerprint of the zip (`_md5` reads it 1 MB at a time to save memory). If it
   is not the known value, we stop with an error.
4. Unzip it.
5. Connect all the pieces in `main`: download, connect, load, print.

Now tell the Makefile to run the new file. Only the `data` lines change in `Makefile`:

```makefile
data:  ## download CUAD into data/raw/ + load DuckDB (data/docintel.duckdb)
	uv run python -m docintel.evals.datasets
```

The second line must start with a **tab**, not spaces. `make` gives an error on spaces.

Checkpoint. pypdf may print warnings like "Ignoring wrong pointing object". You can ignore them:

```sh
make data
```

```text
uv run python -m docintel.evals.datasets
Loaded 510 contracts, 28031 label rows
```

Then check that every contract found its PDF:

```sh
uv run python -c "import duckdb; print(duckdb.connect('data/docintel.duckdb', read_only=True).sql('SELECT count(*) FILTER (WHERE pdf_path IS NULL) AS null_pdf FROM contracts'))"
```

`null_pdf` must be 0.

<details><summary>Your full <code>src/docintel/evals/datasets.py</code></summary>

```python
"""CUAD v1: download it, parse it, load it into DuckDB. Run: `make data`."""

import csv
import hashlib
import json
import re
import unicodedata
import urllib.request
import zipfile
from pathlib import Path

import duckdb
from pypdf import PdfReader

from docintel.evals.store import connect

CUAD_URL = "https://zenodo.org/records/4595826/files/CUAD_v1.zip?download=1"
CUAD_MD5 = "c38f490a984420b8a62600db401fafd5"
RAW_DIR = Path("data/raw")


def _md5(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):  # 1 MB at a time
            h.update(chunk)
    return h.hexdigest()


def download_cuad(raw_dir: Path = RAW_DIR) -> Path:
    """Fetch + verify + unzip CUAD once. Returns the CUAD_v1/ folder."""
    out_dir, zip_path = raw_dir / "CUAD_v1", raw_dir / "CUAD_v1.zip"
    if out_dir.exists():
        return out_dir
    raw_dir.mkdir(parents=True, exist_ok=True)
    if not zip_path.exists():
        print(f"Downloading {CUAD_URL} (~106 MB) ...")
        tmp = zip_path.with_suffix(".part")  # a crash leaves a .part, never a broken .zip
        urllib.request.urlretrieve(CUAD_URL, tmp)
        tmp.rename(zip_path)
    if _md5(zip_path) != CUAD_MD5:
        raise RuntimeError(f"md5 mismatch for {zip_path}; delete it and retry")
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(raw_dir)
    return out_dir


def _key(name: str) -> str:
    """Fuzzy file-name key: lowercase ASCII letters and digits only."""
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^0-9a-z]", "", ascii_name.lower())


def _lookup(table: dict, stem: str):
    """Exact key match, else the single key that starts with ours, else None."""
    k = _key(stem)
    if k in table:
        return table[k]
    hits = [value for key, value in table.items() if key.startswith(k)]
    return hits[0] if len(hits) == 1 else None


def find_pdfs(cuad_dir: Path) -> dict[str, tuple[Path, str]]:
    """key -> (pdf_path, contract_type). The type is the PDF's parent folder name."""
    pdfs = (cuad_dir / "full_contract_pdf").rglob("*")
    return {_key(p.stem): (p, p.parent.name) for p in pdfs if p.suffix.lower() == ".pdf"}


def read_titles(cuad_dir: Path) -> dict[str, str]:
    """key -> readable title ("Document Name-Answer" in master_clauses.csv)."""
    with (cuad_dir / "master_clauses.csv").open(newline="", encoding="utf-8") as f:
        rows = csv.DictReader(f)
        return {_key(Path(r["Filename"]).stem): r["Document Name-Answer"].strip() for r in rows}


def count_pages(pdf_path: Path | None) -> int | None:
    try:
        return len(PdfReader(pdf_path).pages) if pdf_path else None
    except Exception:  # one broken PDF must not stop the load
        return None


def read_docs(cuad_dir: Path) -> list[dict]:
    return json.loads((cuad_dir / "CUAD_v1.json").read_text(encoding="utf-8"))["data"]


def iter_contracts(cuad_dir: Path):
    """Yield one row per contract for the `contracts` table."""
    pdfs, titles = find_pdfs(cuad_dir), read_titles(cuad_dir)
    for doc in read_docs(cuad_dir):
        stem = doc["title"]  # file name without extension; becomes doc_id
        pdf_path, contract_type = _lookup(pdfs, stem) or (None, None)
        txt_path = cuad_dir / "full_contract_txt" / f"{stem}.txt"
        yield {
            "doc_id": stem,
            "title": _lookup(titles, stem) or stem,
            "contract_type": contract_type,
            "n_pages": count_pages(pdf_path),
            "n_chars": len(doc["paragraphs"][0]["context"]),
            "txt_path": str(txt_path) if txt_path.exists() else None,
            "pdf_path": str(pdf_path) if pdf_path else None,
        }


ABSENT = {"span_text": None, "start_char": None, "end_char": None, "is_present": False}


def iter_labels(cuad_dir: Path):
    """Yield one row per answer span. No answer -> one ABSENT row, so "absent" is countable."""
    for doc in read_docs(cuad_dir):
        for qa in doc["paragraphs"][0]["qas"]:
            row = {"doc_id": doc["title"], "category": qa["id"].split("__")[-1]}
            if not qa["answers"]:
                yield row | ABSENT
            for ans in qa["answers"]:
                text, start = ans["text"], ans["answer_start"]
                yield row | {
                    "span_text": text,
                    "start_char": start,
                    "end_char": start + len(text),
                    "is_present": True,
                }


SCHEMA = """
CREATE OR REPLACE TABLE contracts (
    doc_id VARCHAR PRIMARY KEY, title VARCHAR, contract_type VARCHAR,
    n_pages INTEGER, n_chars INTEGER, txt_path VARCHAR, pdf_path VARCHAR
);
CREATE OR REPLACE TABLE labels (
    doc_id VARCHAR, category VARCHAR, span_text VARCHAR,
    start_char INTEGER,  -- 0-based offset into the contract text
    end_char INTEGER,    -- exclusive, like JS str.slice(start, end)
    is_present BOOLEAN
);
"""


def load_cuad(con: duckdb.DuckDBPyConnection, cuad_dir: Path) -> tuple[int, int]:
    """(Re)create both tables. Returns (n_contracts, n_label_rows)."""
    con.execute(SCHEMA)
    contracts, labels = list(iter_contracts(cuad_dir)), list(iter_labels(cuad_dir))
    con.executemany(
        "INSERT INTO contracts VALUES ($doc_id, $title, $contract_type, $n_pages, $n_chars, "
        "$txt_path, $pdf_path)",
        contracts,
    )
    con.executemany(
        "INSERT INTO labels VALUES ($doc_id, $category, $span_text, $start_char, $end_char, "
        "$is_present)",
        labels,
    )
    return len(contracts), len(labels)


def main() -> None:
    cuad_dir = download_cuad()
    with connect() as con:
        n_contracts, n_labels = load_cuad(con, cuad_dir)
    print(f"Loaded {n_contracts} contracts, {n_labels} label rows")


if __name__ == "__main__":
    main()
```
</details>

## Step 7: a test for the rules that must never break

**Why.** Three things must always be true:

1. The offsets cut out exactly the span.
2. An absent category is still a row.
3. Names that almost match still match.

If one of these breaks, we want to know right away. The test builds a tiny fake CUAD with just 2
contracts. It runs in less than a second.

This is the only test file in this part. From Phase 1 on, we measure how good the pipeline is
with evals (scored runs on real data). Tests here only protect the loader.

Put this in `tests/test_data_load.py`:

```python
"""Loader tests on a tiny fake CUAD_v1/ folder: 2 contracts, built fresh in a temp dir."""

import json
import unicodedata

import pytest
from pypdf import PdfWriter

from docintel.evals.datasets import _key, _lookup, load_cuad
from docintel.evals.store import connect

ACME = "CO-BRANDING AGREEMENT between Acme Inc. and Beta LLC. Governed by the laws of Delaware."
BETA = "SUPPLY AGREEMENT. Nothing interesting here."


def _qa(stem, category, text, spans):
    answers = [{"text": s, "answer_start": text.index(s)} for s in spans]
    return {"id": f"{stem}__{category}", "answers": answers, "is_impossible": not answers}


@pytest.fixture
def cuad_dir(tmp_path):
    root = tmp_path / "CUAD_v1"
    (root / "full_contract_txt").mkdir(parents=True)
    (root / "full_contract_txt" / "Acme.txt").write_text(ACME)
    (root / "full_contract_txt" / "Beta.txt").write_text(BETA)

    # Beta's PDF copies a real CUAD quirk: trailing space + uppercase .PDF
    for ctype, filename, pages in [("Co_Branding", "Acme.pdf", 3), ("Supply", "Beta .PDF", 1)]:
        folder = root / "full_contract_pdf" / "Part_I" / ctype
        folder.mkdir(parents=True)
        writer = PdfWriter()
        for _ in range(pages):
            writer.add_blank_page(width=612, height=792)
        writer.write(folder / filename)

    acme_qas = [
        _qa("Acme", "Governing Law", ACME, ["laws of Delaware"]),
        _qa("Acme", "Parties", ACME, ["Acme Inc.", "Beta LLC"]),
    ]
    beta_qas = [_qa("Beta", "Governing Law", BETA, [])]
    data = {"data": [
        {"title": "Acme", "paragraphs": [{"context": ACME, "qas": acme_qas}]},
        {"title": "Beta", "paragraphs": [{"context": BETA, "qas": beta_qas}]},
    ]}  # fmt: skip
    (root / "CUAD_v1.json").write_text(json.dumps(data))
    (root / "master_clauses.csv").write_text(
        "Filename,Document Name-Answer\nAcme.pdf,CO-BRANDING AGREEMENT\nBeta.pdf,SUPPLY AGREEMENT\n"
    )
    return root


@pytest.fixture
def con(cuad_dir):
    with connect(":memory:") as c:
        assert load_cuad(c, cuad_dir) == (2, 4)  # 1 law + 2 parties + 1 absent
        yield c


def test_contract_rows(con):
    rows = con.execute(
        "SELECT doc_id, title, contract_type, n_pages, n_chars FROM contracts ORDER BY doc_id"
    ).fetchall()
    assert rows == [
        ("Acme", "CO-BRANDING AGREEMENT", "Co_Branding", 3, len(ACME)),
        ("Beta", "SUPPLY AGREEMENT", "Supply", 1, len(BETA)),  # messy PDF name still found
    ]


def test_offsets_point_at_span(con):
    rows = con.execute(
        "SELECT l.span_text, l.start_char, l.end_char, c.txt_path "
        "FROM labels l JOIN contracts c USING (doc_id) WHERE l.is_present"
    ).fetchall()
    for span, start, end, txt_path in rows:
        assert open(txt_path).read()[start:end] == span


def test_absent_label_is_a_row(con):
    row = con.execute(
        "SELECT span_text, start_char, is_present FROM labels WHERE doc_id = 'Beta'"
    ).fetchone()
    assert row == (None, None, False)


def test_messy_names_match():
    pdf_name = "LECLANCHÉ S.A. - A&R AGREEMENT "
    json_name = unicodedata.normalize("NFD", "LECLANCHÉ S.A. - A_R AGREEMENT")  # É -> E + accent
    assert pdf_name != json_name
    assert _key(pdf_name) == _key(json_name)
    table = {_key("Harpoon_Development Agreement_Option Agreement"): "hit"}
    assert _lookup(table, "Harpoon_Development Agreement") == "hit"
```

*Python here: [pytest fixtures and `tmp_path`](./py/phase-0b.md#py-8).*

Here, we:

1. Build a fake `CUAD_v1/` folder inside a temporary folder (`cuad_dir`). It has 2 contracts:
   - Acme: one Governing Law answer and two Parties answers.
   - Beta: no Governing Law answer (absent). Its PDF is named `Beta .PDF`, with a space and capital
     letters, just like a real messy CUAD name.
   - `_qa` finds each answer's start with `text.index`, so the offsets are always correct.
2. Load the fake data into a `:memory:` database before each test (the `con` fixture).
3. Run four checks: the contract rows, the offsets, the absent row, and the name matching.

`# fmt: skip` tells ruff (the code formatter) not to spread the `data` dict over 15 lines.

Checkpoint:

```sh
make lint && make test
```

```text
All checks passed!
6 files already formatted
...
tests/test_data_load.py ....                                             [ 80%]
tests/test_smoke.py .                                                    [100%]

============================== 5 passed in 0.33s ===============================
```

Your project should now look like this:

```
src/docintel/
├── __init__.py
└── evals/
    ├── __init__.py
    ├── datasets.py        download, parse, load
    └── store.py           connect()
tests/
├── test_data_load.py      4 tests
└── test_smoke.py
data/                      gitignored
├── docintel.duckdb        contracts (510) + labels (28,031)
└── raw/CUAD_v1/
```

## Break it on purpose

Break the code, guess what happens, then check.

**Break 1.** In `iter_contracts`, change `_lookup(pdfs, stem)` to `pdfs.get(_key(stem))`. This
removes the backup plan. Guess the `null_pdf` number, then run `make data` and the `null_pdf`
query. (Answer: 1. It is Harpoon, the only contract that needs the backup plan.) Then change it
back.

**Break 2.** In `iter_labels`, change `end_char` to `start + len(text) - 1`. Then run `make test`:

```
E           AssertionError: assert 'Beta LL' == 'Beta LLC'
FAILED tests/test_data_load.py::test_offsets_point_at_span - AssertionError: ...
1 failed, 4 passed
```

The quote lost its last letter. In Part 2a, we build a check that catches exactly this kind of bug.
Change it back.

## Gotchas

Common problems, and how to fix them:

- **"Could not set lock on file"**: another program has the database open, like a notebook or the
  DuckDB command line. Close it, or open the database with `read_only=True`.
- **Fresh copy of the repo**: the first `make data` downloads 106 MB. The download site (Zenodo)
  can be slow.
- **Your own tables** (like the `splits` table in 0c) go in the same database file. Never edit
  `contracts` or `labels` by hand: the next `make data` deletes and rebuilds them.
- **`init.py` instead of `__init__.py`**: see Project setup.

## Explain back, then commit

Explain each new file to Claude in a few sentences (the rule in `PLAN.md`). Then:

```sh
git add src/docintel/evals tests/test_data_load.py Makefile
git commit -m "phase 0b: data loader in evals/"
```

## Conclusion

What you have now:

- `datasets.py` downloads CUAD once, and turns it into two tables: `contracts` (510 rows) and
  `labels` (28,031 rows). It also matches file names that are spelled a little differently.
- `store.py` opens the database.
- One small test file checks the three rules that must never break.

Go back to the objectives. Check that you can do each one without notes. Then answer:

1. Why are there more `labels` rows than 510 times 41? How many rows does an absent category get?
2. When two keys start with our key, why does `_lookup` return `None` instead of the first one?

Want more practice? Try these (optional):

1. In the DuckDB command line, find the 5 contract types with the most present labels per
   contract.
2. Find the contract with the most `Parties` rows. Open its `.txt` file and see why.
3. Time `make data`. Check that `count_pages` is the slow part.

Checklist (`../PLAN.md`): **DuckDB SQL ... long vs wide tables** (this part covers long vs wide;
part 0c covers the SQL).
