# Phase 0b: data loader

About an hour. Four files.

## The big picture

After 0a the package is empty. After 0b, `make data` turns CUAD's 510 contracts into two DuckDB
tables (`Loaded 510 contracts, 28031 label rows`). 0c explores them, 0d splits them, 1c scores
against `labels`, 2b checks quotes via the offsets. The zip is already in `data/raw/`.

## Files

| File | Job |
|---|---|
| `src/docintel/evals/__init__.py` | makes `evals/` a package (one docstring) |
| `src/docintel/evals/store.py` | opens the DuckDB file; `:memory:` for tests |
| `src/docintel/evals/datasets.py` | download, parse, load CUAD; `python -m` entry point |
| `tests/test_data_load.py` | 4 tests on a fake 2-contract CUAD |
| `Makefile` | changed: `data` target points at the new module |

Python help for this part: [`learn/py/phase-0b.md`](./py/phase-0b.md).

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

## Design decisions

- **DuckDB**: one file like SQLite, no server; stores by column, so counts and percentiles are fast.
  Postgres is for the live app (Phase 5); CSV + pandas has no SQL and no types.
- **Two tables**: contract facts exist once, labels are many (like `users` and `orders`). Join on
  `doc_id`.
- **Long, not wide**: one row per span (28,031 rows) makes every question `GROUP BY category`.
  `master_clauses.csv` is the wide version (83 columns), where every question is a column loop.
- **Absent is a row** (`is_present=false`, NULL span): a model saying "not found" where lawyers
  found nothing is correct, and you can only count it if the row exists.
- **Offsets kept**: `text[start:end] == span`, the ground truth for the 2b citation check.
- **`doc_id` = file stem** (the JSON `title`): unique, stable, readable. **`contract_type`** from the
  PDF's folder, **`title`** from the CSV; CUAD stores them nowhere else.
- **`CREATE OR REPLACE`**: re-running rebuilds both tables, like a seed script.
- **md5 + `.part`**: a corrupt or half-finished download can never pass as the real zip.

## Worked example

Real CUAD data. Predict before opening.

The zip unpacks to:

```
data/raw/CUAD_v1/
  CUAD_v1.json            40 MB, every label (SQuAD style)
  master_clauses.csv      the same labels, wide
  full_contract_txt/      510 .txt files, the text offsets point into
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

Exactly the answer text: offsets count from 0, end exclusive, like JS `context.slice(4740, 4861)`.
CUAD gives no end, so we compute `end_char = start + len(text)`. All 13,823 present spans match.
</details>

### Round 2: how many `labels` rows?

This contract has 41 categories. Parties has 4 answers (`FEDERATED INVESTMENT MANAGEMENT COMPANY`,
`"Adviser"`, `FEDERATED ADVISORY SERVICES COMPANY`, `"FASC"`), Expiration Date has 0. How many rows
does each produce?

<details><summary>Predict, then open</summary>

Parties: 4 rows, nicknames included. Expiration Date: 1 row, span and offsets NULL,
`is_present = false`. Hence 28,031 rows, more than 510 x 41 = 20,910 pairs.
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
For `É`, the JSON stores `E` + a combining accent, the PDF one character; **NFKD** normalization
splits both into `E` + accent and the ASCII encode drops the accent. That fixes 4 of 5. For
Harpoon, `_lookup` falls back to the single key starting with ours (`None` if two do: never guess).
0 of 510 miss.
</details>

## Your task

### 0. Delete the old loader

**Why.** You re-type it in the shared project layout, where offline eval code lives in `evals/`.

```sh
rm -rf src/docintel/data src/docintel/store tests/test_data_load.py
git status --short    # if any of those show as staged (A), run: git reset -q
make test             # 1 passed (only the smoke test is left)
```

### 1. src/docintel/evals/__init__.py and store.py

**Why.** One place opens the database, so tests can swap in a throwaway one.

```python
"""Offline evaluation: datasets, the DuckDB store, later scorers and the runner."""
```

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

- `:memory:` is a DuckDB special name: a database that lives in RAM and vanishes on close.

### 2. src/docintel/evals/datasets.py

**Why.** The whole loader: download, then parse (the messy part), then load. Type it top to bottom.

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

*Python here: [`with`](./py/phase-0b.md#py-3) · [comprehensions](./py/phase-0b.md#py-4) ·
[generators and `yield`](./py/phase-0b.md#py-5) · [dict `|` and `or`](./py/phase-0b.md#py-6) ·
[`__name__ == "__main__"`](./py/phase-0b.md#py-7).*

- `iter_*` yield rows; `load_cuad` inserts them in bulk. Parsing stays separate from the database.
- `$doc_id` placeholders fill from each dict by name. Never build SQL with f-strings (a `'` in a
  title breaks it). A leading `_` means "internal", by convention only.

### 3. Makefile

**Why.** `make data` must run the new module. Only the `data` recipe changes.

```makefile
.PHONY: install data test lint fmt nb

install:  ## install all deps (incl. dev) into .venv
	uv sync

data:  ## download CUAD into data/raw/ + load DuckDB (data/docintel.duckdb)
	uv run python -m docintel.evals.datasets

test:  ## run pytest
	uv run pytest

lint:  ## check style + common bugs (no changes)
	uv run ruff check .
	uv run ruff format --check .

fmt:  ## auto-fix lint + format
	uv run ruff check --fix .
	uv run ruff format .

nb:  ## launch Jupyter Lab in notebooks/
	uv run jupyter lab notebooks/
```

### 4. tests/test_data_load.py

**Why.** A 2-contract fake CUAD runs in milliseconds and pins each design decision.

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

- Every test that names `con` gets a freshly loaded DB. `# fmt: skip` keeps the nested data compact.

### 5. Explain back, then commit

Explain each new file to Claude in a few sentences (the gate in `PLAN.md`). Then:

```sh
make lint && make test
git add src/docintel/evals tests/test_data_load.py Makefile
git commit -m "phase 0b: data loader in evals/"
```

## Test

```sh
make test   # 5 passed
make data   # Loaded 510 contracts, 28031 label rows (pypdf warnings are harmless)
uv run python -c "import duckdb; print(duckdb.connect('data/docintel.duckdb', read_only=True).sql('SELECT count(*) FILTER (WHERE pdf_path IS NULL) AS null_pdf FROM contracts'))"
```

`null_pdf` must be 0.

**Deliberate failure 1.** In `iter_contracts` use `pdfs.get(_key(stem))` instead of
`_lookup(pdfs, stem)`. Predict `null_pdf`, run `make data` + the query. (1: Harpoon.) Put it back.

**Deliberate failure 2.** Make `end_char` `start + len(text) - 1`. `make test` fails with a span
missing its last letter (`'Beta LL' == 'Beta LLC'`), the bug 2b's citation check exists to catch.

## Gotchas

- **"Could not set lock on file"**: a notebook holds the DB; close it or use `read_only=True`.
- **Fresh clone**: the first `make data` downloads 106 MB silently and Zenodo can be slow.
- **Your own tables** (0d's `splits`) go next to these two; never edit these by hand, a reload
  wipes them.

## Recap

`datasets.py` downloads CUAD once and flattens it into `contracts` (510) and `labels` (28,031),
fuzzy-matching file names. `store.py` opens the DB; tests use `:memory:`.

1. Why are there more `labels` rows than 510 x 41, and how many rows does an absent category get?
2. Why does `_lookup` return `None` when two keys share the prefix, instead of the first?

Checklist (`../PLAN.md`): **DuckDB SQL ... long vs wide tables** (the long vs wide half; the SQL
half is 0c).
