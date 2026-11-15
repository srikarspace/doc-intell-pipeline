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
    sub.add_parser("compare", help="quality against cost for every cell that has a run")
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
