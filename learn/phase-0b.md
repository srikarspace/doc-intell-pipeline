# Phase 0b: data loader

In this part you turn CUAD's 510 contracts into two DuckDB tables. You build the loader one
function at a time, and after each step you run it on the real data to see what it produces.

## Objectives

By the end of this part you should be able to:

1. Explain how one CUAD JSON entry becomes rows in `contracts` and `labels`.
2. Explain why `labels` is long (one row per span) and why an absent category is still a row.
3. Slice a contract's text with `start_char` / `end_char` and get the lawyer's exact quote back.
4. Match messy file names without hand-written exceptions.
5. Query the loaded tables from Python and from the DuckDB CLI.

## Dependencies

Nothing new to install. 0a already added these:

- `duckdb`: the database (one file, no server).
- `pypdf`: counts PDF pages; the test also uses it to write fake PDFs.
- `pytest`: the test runner.

The CUAD zip is already unpacked in `data/raw/CUAD_v1/`, so nothing gets re-downloaded.

## The big picture

After 0a the package is empty. After 0b, `make data` prints `Loaded 510 contracts, 28031 label
rows`. Every later part reads these tables: 0c explores them and picks fields and splits, 1b
scores the model against `labels`, and 2a checks quotes using the offsets.

## Remember this

> A label is a quote with an address: the exact text plus where it starts in the contract. We
> store one row per quote, and a category the lawyers found absent still gets a row, so "not
> there" is a fact you can count. The offsets let any quote be checked against the source.
>
> **One row per span, absent is a row, offsets are proof.**

## Why

**CUAD answers are spans, not values.** Lawyers highlighted text ("...governed by the laws of the
Commonwealth of Pennsylvania"), so our model must also return a value plus a verbatim quote.

**The JSON is nested for a research task** (SQuAD 2.0 question answering). Flatten it once, and
every later question becomes one SQL query instead of a page of loops.

**The labels are the answer key.** We add nothing and judge nothing. Later parts score the
pipeline per category against these rows: found or not, right content, real quote.

## Design decisions

- **DuckDB**: one file like SQLite, no server; stores data by column, so counts and percentiles
  are fast. Postgres is for the live app (Phase 4); CSV + pandas has no SQL and no types.
- **Two tables**: contract facts exist once, labels are many (like `users` and `orders`). Join on
  `doc_id`.
- **Long, not wide**: one row per span (28,031 rows) makes every question a `GROUP BY category`.
  `master_clauses.csv` is the wide version (83 columns), where every question is a column loop.
- **Absent is a row** (`is_present=false`, NULL span): when the model says "not found" and the
  lawyers found nothing, the model is right. You can only count that if the row exists.
- **Offsets kept**: `text[start:end] == span` is the ground truth for the 2a citation check.
- **Where each column comes from**: `doc_id` is the JSON `title` (the file stem). `contract_type`
  is the PDF's parent folder, `title` comes from the CSV, `n_pages` from the PDF. The folder is a
  contract fact, not a label; labels come only from the JSON.
- **Parse apart from load**: `iter_*` functions yield plain dicts and `load_cuad` writes them, so
  you can look at rows without a database (every checkpoint below does).
- **`CREATE OR REPLACE`**: re-running rebuilds both tables, like a seed script.
- **md5 + `.part`**: a corrupt or half-finished download can never pass as the real zip.

## Worked example

Real CUAD data. Predict before opening.

The zip unpacks to:

```
data/raw/CUAD_v1/
  CUAD_v1.json            40 MB, every label (SQuAD style)
  master_clauses.csv      the same labels, wide
  full_contract_txt/      510 .txt files, the text the offsets point into
  full_contract_pdf/      Part_I, Part_II, Part_III / <Contract Type> / *.pdf
  label_group_xlsx/       per-category spreadsheets (we ignore these)
```

One contract inside `CUAD_v1.json` (`...` cut for space):

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

### Round 1: what is `answer_start`?

The Governing Law answer has `answer_start: 4740` and its text is 121 characters long. What is
`context[4740:4861]`, and what goes in `start_char` / `end_char`?

<details><summary>Predict, then open</summary>

Exactly the answer text: offsets count from 0 and the end is exclusive, like JS
`context.slice(4740, 4861)`. CUAD gives no end, so we compute `end_char = start + len(text)`. All
13,823 present spans match.
</details>

### Round 2: how many `labels` rows?

Every contract is asked the same 41 questions. Here Parties has 4 answers
(`FEDERATED INVESTMENT MANAGEMENT COMPANY`, `"Adviser"`, `FEDERATED ADVISORY SERVICES COMPANY`,
`"FASC"`) and Expiration Date has 0. How many rows does each produce?

<details><summary>Predict, then open</summary>

Parties: 4 rows, nicknames included. Expiration Date: 1 row, span and offsets NULL,
`is_present = false`. So every contract has at least 41 rows, and the total is 28,031, more than
510 x 41 = 20,910.
</details>

### Round 3: matching files that don't match

To fill `pdf_path` we look up each JSON `title` among the PDF file names. An exact match misses 5
of 510. Real cases:

| JSON title (= .txt name) | PDF / CSV name |
|---|---|
| `Principal Life ... Servicing Agreement` | `... Servicing Agreement .PDF` (space, caps) |
| `NETGEAR,INC_..._BETWEEN INGRAM MICRO AND NETGEAR` | `..._AND NETGEAR-.pdf` |
| `LECLANCHÉ S.A. - JOINT DEVELOPMENT ...` | same on screen, different bytes |
| `HarpoonTherapeuticsInc_..._Development Agreement` | `..._Development Agreement_Option Agreement.pdf` |
| `MOELIS_CO_...` (title, for the CSV) | `MOELIS&CO_...PDF` |

How do you match all of them without hand-written exceptions?

<details><summary>Predict, then open</summary>

`_key` keeps only lowercase ASCII letters and digits, so spaces, `-`, `&`, `_` and case vanish.
For `É`, the JSON stores `E` + a combining accent and the PDF name stores one character. **NFKD**
normalization splits both into `E` + accent, and the ASCII encode drops the accent. That fixes 4
of 5. For Harpoon, `_lookup` falls back to the single key that starts with ours (`None` if two
do: never guess). 0 of 510 miss.
</details>

## Project setup

Delete the old loader. You re-type it in the shared layout, where offline eval code lives in
`evals/`:

```sh
$ rm -rf src/docintel/data src/docintel/store tests/test_data_load.py
$ git status --short    # if any of those show as staged (A), run: git reset -q
```

Create the new files, all empty for now:

```sh
$ mkdir -p src/docintel/evals
$ touch src/docintel/evals/__init__.py src/docintel/evals/store.py \
        src/docintel/evals/datasets.py tests/test_data_load.py
```

> The file is `__init__.py`: two underscores, `init`, two underscores. Markdown renders
> unquoted `__init__` as bold **init**, so always copy file names from a code block. A file named
> `init.py` is just a module called `init`. Fix one with
> `mv src/docintel/evals/init.py src/docintel/evals/__init__.py`.

Put the package's one-line docstring in `src/docintel/evals/__init__.py`:

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

Each step below adds code, explains it, then runs it on the real data. Run every checkpoint from
the repo root. Before moving on from a step, make sure your output matches.

## Step 1: connect to DuckDB

**Why.** One place opens the database, so tests can swap in a throwaway one.

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

1. Default to the project file, `data/docintel.duckdb`.
2. Create `data/` if it is missing, so a fresh clone works.
3. Skip the folder for `":memory:"`, a DuckDB special name for a database that lives in RAM and
   disappears on close.

Checkpoint:

```sh
$ uv run python -c "from docintel.evals.store import connect; print(connect(':memory:').execute('SELECT 41 + 1').fetchone())"
(42,)
```

## Step 2: match messy file names

**Why.** Without this, 5 contracts lose their PDF, their page count and their contract type.

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

Here, `_key` turns any name into a plain comparison key (Round 3), and `_lookup` tries an exact
hit before the unique-prefix fallback. A leading `_` means "internal to this module", by
convention only.

Checkpoint. Predict the three keys first:

```sh
$ uv run python -c "from docintel.evals.datasets import _key; print(_key('MOELIS&CO_x'), _key('MOELIS_CO_x'), _key('LECLANCHÉ S.A. - A&R AGREEMENT '))"
moeliscox moeliscox leclanchesaaragreement
```

## Step 3: one row per contract

**Why.** The `contracts` table holds the facts that exist once per contract.

Update the imports at the top of `datasets.py`:

```python
import csv
import json
import re
import unicodedata
from pathlib import Path

from pypdf import PdfReader
```

Add to the bottom:

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

1. Build two lookup tables keyed by `_key`: every PDF (with its folder as the type) and every
   CSV title.
2. Walk the JSON once and `yield` one dict per contract.
3. Swallow errors in `count_pages`: one broken PDF gives `None` instead of stopping 510 contracts.

Checkpoint. Print the first contract:

```sh
$ uv run python -c "
from pathlib import Path
from docintel.evals.datasets import iter_contracts
print(next(iter_contracts(Path('data/raw/CUAD_v1'))))"
```

You should see (wrapped here):

```python
{'doc_id': 'LIMEENERGYCO_09_09_1999-EX-10-DISTRIBUTOR AGREEMENT',
 'title': 'DISTRIBUTOR  AGREEMENT', 'contract_type': 'Distributor', 'n_pages': 10,
 'n_chars': 54290,
 'txt_path': 'data/raw/CUAD_v1/full_contract_txt/LIMEENERGYCO_09_09_1999-EX-10-DISTRIBUTOR AGREEMENT.txt',
 'pdf_path': 'data/raw/CUAD_v1/full_contract_pdf/Part_III/Distributor/LIMEENERGYCO_09_09_1999-EX-10-DISTRIBUTOR AGREEMENT.PDF'}
```

`contract_type` is `Distributor` because the PDF sits in `.../Part_III/Distributor/`.

## Step 4: one row per label

**Why.** This is the answer key: one row per span, and one row for each absent category.

Add to the bottom of `datasets.py`:

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

Here, the category is the part of the question `id` after `__`. An empty `answers` list yields
one `ABSENT` row. Otherwise each answer yields one row, with `end_char` computed as in Round 1.
`row | ABSENT` builds a new dict, so the shared `ABSENT` is never changed.

Checkpoint. Predict both numbers before you run it:

```sh
$ uv run python -c "
from pathlib import Path
from docintel.evals.datasets import iter_labels
rows = list(iter_labels(Path('data/raw/CUAD_v1')))
print(len(rows), sum(r['is_present'] for r in rows))
print(rows[0])"
28031 13823
{'doc_id': 'LIMEENERGYCO_09_09_1999-EX-10-DISTRIBUTOR AGREEMENT', 'category': 'Document Name', 'span_text': 'DISTRIBUTOR AGREEMENT', 'start_char': 44, 'end_char': 65, 'is_present': True}
```

28,031 rows in total: 13,823 present spans plus 14,208 absent rows. `sum` counts `True` as 1.

## Step 5: load into DuckDB

**Why.** The rows have to land in tables that every later part can query with SQL.

Update the imports at the top of `datasets.py`:

```python
import csv
import json
import re
import unicodedata
from pathlib import Path

import duckdb
from pypdf import PdfReader
```

Add to the bottom:

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

Here, we create both tables, collect the rows from the two generators, and insert them in bulk.
`$doc_id` placeholders fill from each dict by name. Never build SQL with f-strings: a `'` in a
contract title would break the query.

Checkpoint. Load into a throwaway in-memory database and ask the first real question:

```sh
$ uv run python -c "
from pathlib import Path
from docintel.evals.datasets import load_cuad
from docintel.evals.store import connect
with connect(':memory:') as con:
    print(load_cuad(con, Path('data/raw/CUAD_v1')))
    print(con.sql('SELECT category, count(*) AS n FROM labels WHERE is_present GROUP BY category ORDER BY n DESC LIMIT 3'))"
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

It takes 10 to 20 seconds; opening 510 PDFs for page counts is the slow part. That `GROUP BY` is
the "long, not wide" payoff: one line of SQL.

## Step 6: download and `make data`

**Why.** A fresh clone must go from nothing to loaded tables with one command.

Update the imports at the top of `datasets.py` (the last line is new: our own package):

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

Add below the imports, above `_key`:

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

Add to the bottom:

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

1. Return early from `download_cuad` when the folder exists, which is why nothing re-downloads.
2. Download to a `.part` file and rename it only when complete.
3. Check the zip against a known md5 before unzipping.
4. Wire download, connect and load together in `main`.

Point the Makefile at the new module. Only the `data` line changes in `Makefile`:

```makefile
data:  ## download CUAD into data/raw/ + load DuckDB (data/docintel.duckdb)
	uv run python -m docintel.evals.datasets
```

The recipe line starts with a **tab**, not spaces; `make` rejects spaces.

Checkpoint. pypdf may print "Ignoring wrong pointing object" warnings; they are harmless:

```sh
$ make data
uv run python -m docintel.evals.datasets
Loaded 510 contracts, 28031 label rows
```

Then check that no contract lost its PDF:

```sh
$ uv run python -c "import duckdb; print(duckdb.connect('data/docintel.duckdb', read_only=True).sql('SELECT count(*) FILTER (WHERE pdf_path IS NULL) AS null_pdf FROM contracts'))"
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

## Step 7: a test for the invariants

**Why.** Three facts must never silently break: offsets slice back to the span, absent is a row,
and messy names still match. A 2-contract fake CUAD checks all three in under a second.

This is the only test file in this part. Quality of the pipeline itself is measured with evals
from Phase 1 on; tests here just guard the loader.

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

1. Build a fake `CUAD_v1/` in a temp folder with `cuad_dir`. `Beta .PDF` copies a real quirk
   (trailing space, uppercase extension). `_qa` computes `answer_start` with `text.index`, so the
   offsets are right by construction.
2. Load it into `:memory:` once per test with the `con` fixture.
3. Check the contract rows, the offsets, the absent row, and the file-name matching.

`# fmt: skip` stops ruff from spreading the nested data over 15 lines.

Checkpoint:

```sh
$ make lint && make test
All checks passed!
6 files already formatted
...
tests/test_data_load.py ....                                             [ 80%]
tests/test_smoke.py .                                                    [100%]

============================== 5 passed in 0.33s ===============================
```

Your project structure should now look like this:

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

**Deliberate failure 1.** In `iter_contracts`, use `pdfs.get(_key(stem))` instead of
`_lookup(pdfs, stem)`. Predict `null_pdf`, then run `make data` and the query. (It is 1: Harpoon,
the only case the prefix fallback handles.) Put it back.

**Deliberate failure 2.** In `iter_labels`, make `end_char` `start + len(text) - 1`, then run
`make test`:

```
E           AssertionError: assert 'Beta LL' == 'Beta LLC'
FAILED tests/test_data_load.py::test_offsets_point_at_span - AssertionError: ...
1 failed, 4 passed
```

A quote missing its last letter is exactly the bug 2a's citation check exists to catch. Put it
back.

## Gotchas

- **"Could not set lock on file"**: a notebook or the DuckDB CLI holds the database. Close it, or
  open with `read_only=True`.
- **Fresh clone**: the first `make data` downloads 106 MB, and Zenodo can be slow.
- **Your own tables** (0c's `splits`) go next to these two. Never edit these by hand: a reload
  wipes them.
- **`init.py` vs `__init__.py`**: see Project setup.

## Explain back, then commit

Explain each new file to Claude in a few sentences (the gate in `PLAN.md`). Then:

```sh
$ git add src/docintel/evals tests/test_data_load.py Makefile
$ git commit -m "phase 0b: data loader in evals/"
```

## Conclusion

`datasets.py` downloads CUAD once and flattens it into `contracts` (510 rows) and `labels`
(28,031 rows), fuzzy-matching file names on the way. `store.py` opens the database. One small
test file guards the three invariants.

Go back through the objectives and check that you can do each one without notes. Then answer:

1. Why are there more `labels` rows than 510 x 41, and how many rows does an absent category get?
2. Why does `_lookup` return `None` when two keys share the prefix, instead of picking the first?

Looking for more challenges?

1. In the DuckDB CLI, list the 5 contract types with the most present labels per contract.
2. Find the contract with the most `Parties` rows and open its `.txt` to see why.
3. Time `make data` and confirm `count_pages` is the slow part.

Checklist (`../PLAN.md`): **DuckDB SQL ... long vs wide tables** (the long vs wide half; the SQL
half is 0c).
