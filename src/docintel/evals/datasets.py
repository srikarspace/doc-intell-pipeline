"""CUAD v1: download it, parse it, load it into DuckDB. Run: `make data`."""

import csv
import hashlib
import json
import random
import re
import unicodedata
import urllib.request
import zipfile
from collections import defaultdict
from pathlib import Path

import duckdb
from pypdf import PdfReader

from docintel.evals.store import connect

CUAD_URL = "https://zenodo.org/records/4595826/files/CUAD_v1.zip?download=1"
CUAD_MD5 = "c38f490a984420b8a62600db401fafd5"
RAW_DIR = Path("data/raw")

FIELDS = {
    "basic facts": ["Parties", "Agreement Date", "Governing Law"],
    "yes/no + quote": ["Non-Compete", "Change Of Control", "Anti-Assignment"],
    "numbers/terms": [
        "Renewal Term",
        "Notice Period To Terminate Renewal",
        "Cap On Liability",
    ],
    "license/IP": [
        "License Grant",
        "Ip Ownership Assignment",
        "Non-Transferable License",
    ],
}


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


# same type contract in different folders
SAME_TYPE = {
    "Affiliate Agreement": "Affiliate_Agreements",
    "Endorsement Agreement": "Endorsement",
    "Joint Venture _ Filing": "Joint Venture",
}


def family(doc_id: str) -> str:
    """Company part of a doc_id: the text before the first "_" or " - ", lowercase."""
    return re.split(r"_| - ", doc_id, maxsplit=1)[0].lower()


def group_families(rows: list[tuple[str, str]]) -> tuple[dict, dict]:
    """family -> [doc_id, ...] and family -> type (the type of its first doc)."""
    docs, ftype = defaultdict(list), {}
    for doc_id, ctype in rows:
        fam = family(doc_id)
        docs[fam].append(doc_id)
        ftype.setdefault(fam, SAME_TYPE.get(ctype, ctype))
    return docs, ftype


def pick_side(in_type: dict[str, int], overall: dict[str, int], dev_share: float) -> str:
    """The side that is furthest below its share: first inside this type, then overall."""
    for c in (in_type, overall):
        target = dev_share * (c["dev"] + c["test"])
        if c["dev"] < target:
            return "dev"
        if c["dev"] > target:
            return "test"
    return "dev"


def make_splits(
    con: duckdb.DuckDBPyConnection, seed: int = 0, n_docs: int = 100, dev_share: float = 0.5
) -> dict[str, int]:
    """Pick about n_docs contracts, stratified by type; a whole family goes to one side."""
    rows = con.execute("SELECT doc_id, contract_type FROM contracts ORDER BY doc_id").fetchall()
    docs, ftype = group_families(rows)
    by_type = defaultdict(list)  # type -> [family, ...]
    for fam in sorted(docs):
        by_type[ftype[fam]].append(fam)

    rng = random.Random(seed)
    counts = {"dev": 0, "test": 0}
    split_of = {}  # doc_id -> "dev" | "test"
    for ctype in sorted(by_type):
        fams = by_type[ctype]
        rng.shuffle(fams)
        quota = max(1, round(n_docs * sum(len(docs[f]) for f in fams) / len(rows)))
        in_type = {"dev": 0, "test": 0}
        for fam in fams:
            if in_type["dev"] + in_type["test"] >= quota:
                break
            side = pick_side(in_type, counts, dev_share)
            for doc_id in docs[fam]:
                split_of[doc_id] = side
            counts[side] += len(docs[fam])
            in_type[side] += len(docs[fam])

    con.execute("CREATE OR REPLACE TABLE splits (doc_id VARCHAR PRIMARY KEY, split VARCHAR)")
    con.executemany("INSERT INTO splits VALUES (?, ?)", sorted(split_of.items()))
    return counts


def read_answers(cuad_dir: Path) -> dict[str, dict[str, str]]:
    """key -> {category: answer} from the "-Answer" columns of master_clauses.csv."""
    out = {}
    with (cuad_dir / "master_clauses.csv").open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            answers = {}
            for col, val in r.items():
                category, _, tail = col.rpartition("-")
                if tail.strip() == "Answer" and val.strip():  # one column is "...- Answer"
                    answers[category.strip()] = val.strip()
            out[_key(Path(r["Filename"]).stem)] = answers
    return out


def load_answers(con: duckdb.DuckDBPyConnection, cuad_dir: Path) -> int:
    """(Re)create `answers`: CUAD's short answer per (contract, category). Returns the row count."""
    table = read_answers(cuad_dir)
    rows = [
        (doc["title"], category, answer)
        for doc in read_docs(cuad_dir)
        for category, answer in (_lookup(table, doc["title"]) or {}).items()
    ]
    con.execute(
        "CREATE OR REPLACE TABLE answers (doc_id VARCHAR, category VARCHAR, answer VARCHAR)"
    )
    con.executemany("INSERT INTO answers VALUES (?, ?, ?)", rows)
    return len(rows)


def main() -> None:
    cuad_dir = download_cuad()
    with connect() as con:
        n_contracts, n_labels = load_cuad(con, cuad_dir)
        counts = make_splits(con)
        n_answers = load_answers(con, cuad_dir)
    print(f"Loaded {n_contracts} contracts, {n_labels} label rows, {n_answers} answers")
    print(f"Splits: {counts['dev']} dev, {counts['test']} test")


if __name__ == "__main__":
    main()
