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
from docintel.evals.scorers import metrics, score_doc
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


COST = """
SELECT count(*), sum(cost_usd), quantile_cont(latency_ms, 0.5) / 1000,
    quantile_cont(latency_ms, 0.95) / 1000, count(*) FILTER (WHERE NOT ok)
FROM llm_calls WHERE run_id = ?
"""


def fmt(x: float | None) -> str:
    return "-" if x is None else f"{x:.2f}"


def report(con: duckdb.DuckDBPyConnection, run_id: str) -> None:
    """Print P/R/F1 per field, per group and for all fields, then cost and latency."""
    print(f"{'':36} {'tp':>4} {'fp':>4} {'fn':>4} {'P':>5} {'R':>5} {'F1':>5}")
    for r in metrics(con, run_id):
        scores = f"{fmt(r['precision']):>5} {fmt(r['recall']):>5} {fmt(r['f1']):>5}"
        print(f"{r['name']:36} {r['tp']:4} {r['fp']:4} {r['fn']:4} {scores}")
    calls, cost, p50, p95, bad = con.execute(COST, [run_id]).fetchone()
    if calls:  # the 1b-example run has scores but no logged calls
        print(f"{calls} calls, ${cost:.4f}, p50 {p50:.1f} s, p95 {p95:.1f} s, {bad} bad answers")


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
    show = sub.add_parser("report", help="print P/R per field and group, cost and latency")
    show.add_argument("run_id")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    with connect() as con:
        con.execute(TABLES)
        if args.command == "score":
            print(f"scored {score(con, args.run_id)} docs for run {args.run_id}")
            return
        if args.command == "report":
            report(con, args.run_id)
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
