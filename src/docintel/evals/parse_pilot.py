"""Pilot for 3a3: the parsers on the same few dev contracts, cost checked first."""

import argparse
import json
import urllib.request
from collections import Counter
from datetime import datetime
from pathlib import Path

from docintel.core.config import get_settings
from docintel.domain.parse import PARSERS
from docintel.domain.parse.base import ParsedDoc
from docintel.domain.parse.cache import cached_parse
from docintel.domain.parse.vision import (
    MAX_OUTPUT_TOKENS,
    MAX_PAGES,
    MODELS,
    Budget,
    BudgetExceeded,
    make_vision_parser,
)
from docintel.domain.validate.citations import quote_status, words
from docintel.evals.store import connect

PAGE_TOKENS = {"deepseek_vl": (1142, 2352), "kimi_vl": (2900, 4928)}  # (in, out), real 3a3 rows


def provider_price(model: str) -> tuple[float, float]:
    """(input, output) USD per token on OUR provider. The highest, if it has several endpoints."""
    s = get_settings()
    url = f"{s.openrouter_base_url}/models/{model}/endpoints"
    with urllib.request.urlopen(url, timeout=30) as r:
        endpoints = json.load(r)["data"]["endpoints"]
    ours = [e["pricing"] for e in endpoints if e["provider_name"].lower() == s.docintel_provider]
    if not ours:
        raise ValueError(f"{model} is not served by {s.docintel_provider}")
    return max(float(p["prompt"]) for p in ours), max(float(p["completion"]) for p in ours)


def page_costs(parser_name: str) -> tuple[float, float]:
    """(usual, worst) cost of one page, in USD."""
    in_price, out_price = provider_price(MODELS[parser_name])
    tokens_in, tokens_out = PAGE_TOKENS[parser_name]
    usual = tokens_in * in_price + tokens_out * out_price
    return usual, tokens_in * in_price + MAX_OUTPUT_TOKENS * out_price

def pick_docs(con, per_band: int) -> list[tuple]:
    """`per_band` dev contracts from each third of the lengths, at most MAX_PAGES pages."""
    return con.execute(
        """
        WITH d AS (
            SELECT doc_id, pdf_path, txt_path, n_pages,
                   ntile(3) OVER (ORDER BY n_pages, doc_id) AS band
            FROM contracts JOIN splits USING (doc_id)
            WHERE split = 'dev' AND n_pages <= ?
        ), ranked AS (
            SELECT *, row_number() OVER (PARTITION BY band ORDER BY md5(doc_id)) AS r FROM d
        )
        SELECT doc_id, pdf_path, txt_path, n_pages FROM ranked WHERE r <= ? ORDER BY band, doc_id
        """,
        [MAX_PAGES, per_band],
    ).fetchall()

def report_row(name: str, parsed: list[ParsedDoc], docs: list[tuple], spans: dict) -> str:
    n_pages = sum(len(d.pages) for d in parsed)
    txt = sum(len(Path(t).read_text(encoding="utf-8")) for _, _, t, _ in docs[: len(parsed)])
    status = Counter()
    for doc, (doc_id, *_) in zip(parsed, docs, strict=False):
        source = words(doc.text)
        status.update(quote_status(s, source) for s in spans[doc_id])
    found = status["same_words"] + status["gap"]
    cost = sum(d.cost_usd for d in parsed)
    secs = sum(d.latency_ms for d in parsed) / 1000 / max(n_pages, 1)
    ratio = sum(len(d.text) for d in parsed) / max(txt, 1)
    return (
        f"{name:12} {len(parsed):4} {n_pages:5} {ratio:6.3f} "
        f"{found:4}/{sum(status.values()):<4} ${cost:7.4f} {secs:7.2f}"
    )


def main() -> None:
    ap = argparse.ArgumentParser(prog="python -m docintel.evals.parse_pilot")
    ap.add_argument("--per-band", type=int, default=1)
    ap.add_argument("--budget", type=float, required=True, help="stop before passing this, in USD")
    ap.add_argument("--parsers", nargs="+", default=["pypdf", *MODELS], choices=list(PARSERS))
    ap.add_argument("--yes", action="store_true")
    args = ap.parse_args()

    with connect() as con:
        docs = pick_docs(con, args.per_band)
        spans = {
            d[0]: [
                s
                for (s,) in con.execute(
                    "SELECT span_text FROM labels WHERE doc_id = ? AND is_present "
                    "AND span_text IS NOT NULL",
                    [d[0]],
                ).fetchall()
            ]
            for d in docs
        }
    n_pages = sum(d[3] for d in docs)
    vision = [p for p in args.parsers if p in MODELS]
    costs = {p: page_costs(p) for p in vision}
    print(f"{len(docs)} docs, {n_pages} pages, budget ${args.budget:.2f}")
    for p, (usual, worst) in costs.items():
        print(f"{p}: usual ${usual * n_pages:.4f}, worst ${worst * n_pages:.4f}")
    if vision and not args.yes and input("Start? [y/N] ").strip().lower() != "y":
        return

    run_id = f"pilot-{datetime.now():%Y%m%d-%H%M%S}"
    budget = Budget(args.budget)
    results = {}
    try:
        for name in args.parsers:
            parser = PARSERS[name]
            if name in MODELS:
                parser = make_vision_parser(
                    name, run_id=run_id, budget=budget, worst_page_usd=costs[name][1]
                )
            results[name] = []
            for doc_id, path, _, _ in docs:
                results[name].append(cached_parse(name, doc_id, Path(path), parser))
    except BudgetExceeded as e:
        print("stopped:", e)
    print(f"run {run_id}, spent now ${budget.spent:.4f}")
    print("parser       docs pages  ratio    quotes     cost  s/page")
    for name, parsed in results.items():
        if parsed:
            print(report_row(name, parsed, docs, spans))


if __name__ == "__main__":
    main()