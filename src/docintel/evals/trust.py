"""Trust experiments: first and final answers of one retry run, with and without blanking."""

import argparse
from collections import defaultdict

import duckdb

from docintel.core.llm import _parse
from docintel.domain.schema.fields import ContractFields
from docintel.evals.runner import TABLES, empty_answer, from_rows, score, to_rows, validate
from docintel.evals.scorers import metrics
from docintel.evals.store import connect

VALIDATION = {"found_no_quote", "quote_not_found", "found_no_value", "value_not_found", "bad_date"}
CITATION = {"quote_missing"}
BLANK = {"blank-v": VALIDATION, "blank-vc": VALIDATION | CITATION}  # policy -> rules

Answers = dict[str, ContractFields | None]  # doc_id -> answer; None: it did not fit the schema


def first_answers(con: duckdb.DuckDBPyConnection, run_id: str) -> Answers:
    """Attempt 0 of each contract, read again from its raw text: the answer before any retry."""
    rows = con.execute(
        "SELECT doc_id, raw_text FROM attempts WHERE run_id = ? AND attempt_no = 0", [run_id]
    ).fetchall()
    return {doc_id: _parse(ContractFields, raw_text)[0] for doc_id, raw_text in rows}


def stored_answers(con: duckdb.DuckDBPyConnection, run_id: str) -> Answers:
    """The stored answer of each contract. For a retry run, this is the final answer."""
    rows = con.execute(
        "SELECT doc_id, field, ok, answer FROM predictions WHERE run_id = ?", [run_id]
    ).fetchall()
    by_doc = defaultdict(list)
    for doc_id, field, ok, answer in rows:
        by_doc[doc_id].append((field, ok, answer))
    return {
        doc_id: from_rows([(f, a) for f, _, a in fields])
        if all(ok for _, ok, _ in fields)
        else None
        for doc_id, fields in by_doc.items()
    }


def blank(answer: ContractFields, fields: set[str]) -> ContractFields:
    """The same answer, with these fields set to "not found"."""
    return ContractFields.model_validate(answer.model_dump() | {f: empty_answer(f) for f in fields})


def blanked(
    con: duckdb.DuckDBPyConnection, run_id: str, answers: Answers, rules: set[str]
) -> Answers:
    """Blank each field that has an error from `rules` in the stored issues of `run_id`."""
    rows = con.execute(
        "SELECT doc_id, field, rule FROM issues WHERE run_id = ? AND severity = 'error'", [run_id]
    ).fetchall()
    broken = defaultdict(set)
    for doc_id, field, rule in rows:
        if rule in rules:
            broken[doc_id].add(field)
    return {
        doc_id: blank(answer, broken[doc_id]) if answer and broken[doc_id] else answer
        for doc_id, answer in answers.items()
    }


def derive(con: duckdb.DuckDBPyConnection, parent: str, name: str, answers: Answers) -> str:
    """Store answers as a normal run named `<parent>-<name>`, then score and check it. No LLM."""
    run_id = f"{parent}-{name}"
    con.execute("DELETE FROM runs WHERE run_id = ?", [run_id])  # so it can run again
    con.execute("DELETE FROM predictions WHERE run_id = ?", [run_id])
    con.execute(
        "INSERT INTO runs (run_id, split, parser, model, prompt_version, n_docs, est_cost_usd, "
        "max_retries) SELECT ?, split, parser, model, prompt_version, n_docs, 0, max_retries "
        "FROM runs WHERE run_id = ?",
        [run_id, parent],
    )
    for doc_id, answer in answers.items():
        con.executemany(
            "INSERT INTO predictions VALUES (?, ?, ?, ?, ?, ?)", to_rows(run_id, doc_id, answer)
        )
    score(con, run_id)
    validate(con, run_id)
    return run_id


def build(con: duckdb.DuckDBPyConnection, run_id: str) -> dict[str, tuple[str, str]]:
    """Policy -> (first run, final run). The retry run itself is the final run for "keep"."""
    first, final = first_answers(con, run_id), stored_answers(con, run_id)
    first_run = derive(con, run_id, "first", first)
    runs = {"keep": (first_run, run_id)}
    for policy, rules in BLANK.items():
        runs[policy] = (
            derive(con, run_id, f"first-{policy}", blanked(con, first_run, first, rules)),
            derive(con, run_id, policy, blanked(con, run_id, final, rules)),
        )
    return runs


CHANGED = """
WITH a AS (SELECT doc_id, field, answer::VARCHAR AS answer, tp
           FROM predictions JOIN scores USING (run_id, doc_id, field) WHERE run_id = $a),
b AS (SELECT doc_id, field, answer::VARCHAR AS answer, tp
      FROM predictions JOIN scores USING (run_id, doc_id, field) WHERE run_id = $b)
SELECT count(*) FILTER (WHERE a.answer <> b.answer),
    count(*) FILTER (WHERE a.tp > 0 AND b.tp = 0),
    count(*) FILTER (WHERE a.tp = 0 AND b.tp > 0)
FROM a JOIN b USING (doc_id, field)
"""
ERRORS = """
SELECT count(DISTINCT (doc_id, field)) FILTER (WHERE rule IN $v),
    count(DISTINCT (doc_id, field)) FILTER (WHERE rule IN $c)
FROM issues WHERE run_id = $run_id AND severity = 'error'
"""
RETRIES = """
SELECT count(DISTINCT doc_id), count(DISTINCT doc_id) FILTER (WHERE attempt_no > 0),
    count(*) FILTER (WHERE attempt_no > 0), count(*) FILTER (WHERE fixed),
    sum(cost_usd) FILTER (WHERE attempt_no = 0),
    coalesce(sum(cost_usd) FILTER (WHERE attempt_no > 0), 0)
FROM attempts WHERE run_id = ?
"""


def report(con: duckdb.DuckDBPyConnection, run_id: str, runs: dict[str, tuple[str, str]]) -> None:
    """Print first against final answers for each policy, then the errors and the retry cost."""
    print(
        f"{'':10} {'first: P':>8} {'R':>5} {'F1':>5}  {'final: P':>8} {'R':>5} {'F1':>5}"
        f"  {'changed':>7} {'lost':>4} {'gained':>6}"
    )
    for policy, (first, final) in runs.items():
        a, b = metrics(con, first)[-1], metrics(con, final)[-1]  # the last row is all fields
        changed, lost, gained = con.execute(CHANGED, {"a": first, "b": final}).fetchone()
        print(
            f"{policy:10} {a['precision']:8.3f} {a['recall']:5.3f} {a['f1']:5.3f}"
            f"  {b['precision']:8.3f} {b['recall']:5.3f} {b['f1']:5.3f}"
            f"  {changed:7} {lost:4} {gained:6}"
        )
    first, final = runs["keep"]
    sets = {"v": list(VALIDATION), "c": list(CITATION)}
    v0, c0 = con.execute(ERRORS, sets | {"run_id": first}).fetchone()
    v1, c1 = con.execute(ERRORS, sets | {"run_id": final}).fetchone()
    print(f"error fields: validation {v0} -> {v1}, citation {c0} -> {c1}")
    docs, retried, retries, fixed, cost0, cost1 = con.execute(RETRIES, [run_id]).fetchone()
    print(f"retries: {retried} of {docs} contracts, {retries} calls, {fixed} fixed")
    print(
        f"cost: first answers ${cost0:.4f}, retries ${cost1:.4f} ({cost1 / cost0:.0%}),"
        f" ${(cost0 + cost1) / docs:.4f} per contract"
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m docintel.evals.trust")
    parser.add_argument("run_id", help="a run made with --retries")
    args = parser.parse_args(argv)
    with connect() as con:
        con.execute(TABLES)
        runs = build(con, args.run_id)
        report(con, args.run_id, runs)


if __name__ == "__main__":
    main()
