"""The E3 report: each cell uses its newest run, and cost adds parse and extraction."""

import pytest

from docintel.domain.schema.fields import ContractFields
from docintel.evals import parser_experiment as pe
from docintel.evals.runner import TABLES
from docintel.evals.store import connect

MODEL = "fake/model"
DOCS = [("doc-1", "p", "t", 1), ("doc-2", "p", "t", 1)]


def add_run(con, run_id, cell, created, tp, cost):
    con.execute(
        "INSERT INTO runs (run_id, created_at, split, parser, model, prompt_version, n_docs) "
        "VALUES (?, ?, 'e3', ?, ?, 'v1', 2)",
        [run_id, created, cell, MODEL],
    )
    for field in ContractFields.model_fields:
        con.execute(
            "INSERT INTO scores VALUES "
            "(?, 'doc-1', ?, 'presence', true, true, true, true, ?, 0, 0)",
            [run_id, field, tp],
        )
    con.execute(
        "INSERT INTO llm_calls (run_id, cost_usd) VALUES (?, ?)",
        [run_id, cost],
    )


@pytest.fixture
def con(tmp_path, monkeypatch):
    monkeypatch.setattr(pe, "all_spans", lambda con, docs: {})
    stats = {"cer": 0.1, "found": 1, "total": 1, "parse_usd": 0.02, "s_page": 3.0}
    monkeypatch.setattr(pe, "cell_stats", lambda cell, docs, spans: stats)
    with connect(tmp_path / "t.duckdb") as c:
        c.execute(TABLES)
        c.execute("CREATE TABLE llm_calls (run_id VARCHAR, cost_usd DOUBLE)")
        yield c


def test_the_newest_run_of_a_cell_is_used(con):
    add_run(con, "old", "pypdf", "2026-01-01", 0, 0.0)
    add_run(con, "new", "pypdf", "2026-01-02", 1, 0.0)
    assert pe.compare_rows(con, DOCS, MODEL)[0]["run_id"] == "new"


def test_total_cost_adds_parse_and_extraction_per_doc(con):
    add_run(con, "r", "deepseek_vl@mild", "2026-01-01", 1, 0.01)
    row = pe.compare_rows(con, DOCS, MODEL)[0]
    assert row["extract_usd"] == pytest.approx(0.005)
    assert row["total_usd"] == pytest.approx(0.025)


def test_the_reference_has_no_parse_cost_or_errors(con):
    add_run(con, "r", "cuad_txt", "2026-01-01", 1, 0.01)
    row = pe.compare_rows(con, DOCS, MODEL)[0]
    assert (row["cer"], row["parse_usd"]) == (0.0, 0.0)


def test_a_cell_with_no_parsed_text_stops_the_report(con, monkeypatch):
    add_run(con, "r", "pypdf", "2026-01-01", 1, 0.0)
    monkeypatch.setattr(pe, "cell_stats", lambda cell, docs, spans: None)
    with pytest.raises(SystemExit, match="not parsed"):
        pe.compare_rows(con, DOCS, MODEL)
