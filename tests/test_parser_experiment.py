"""E3 wiring: the rules that keep the parser experiment fair and free of surprise costs."""

import pytest

from docintel.domain.parse.cache import cache_path
from docintel.evals.parser_experiment import SET_NAME, freeze, split_cell
from docintel.evals.runner import CELLS, PARSERS, TABLES, cached_text, docs_for
from docintel.evals.store import connect


@pytest.fixture
def con(tmp_path):
    with connect(tmp_path / "t.duckdb") as c:
        c.execute(TABLES)
        c.execute(
            "CREATE TABLE contracts (doc_id VARCHAR, pdf_path VARCHAR, txt_path VARCHAR, "
            "n_pages INTEGER)"
        )
        c.execute("CREATE TABLE splits (doc_id VARCHAR, split VARCHAR)")
        for n, (doc_id, split) in enumerate(
            [("a", "dev"), ("b", "dev"), ("c", "dev"), ("hidden", "test")], start=1
        ):
            c.execute("INSERT INTO contracts VALUES (?, 'p', 't', ?)", [doc_id, n])
            c.execute("INSERT INTO splits VALUES (?, ?)", [doc_id, split])
        yield c


def test_a_missing_parse_stops_the_run(tmp_path):
    with pytest.raises(FileNotFoundError, match="run the parse stage"):
        cached_text("deepseek_vl@mild", "doc-1", tmp_path)


def test_a_run_cannot_start_a_parse(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # an empty folder, so nothing is cached here
    with pytest.raises(FileNotFoundError, match="run the parse stage"):
        PARSERS["deepseek_vl@mild"](None, "doc-1")


def test_every_cell_has_its_own_cache_folder():
    paths = {cache_path(cell, "doc-1") for cell in CELLS}
    assert len(paths) == len(CELLS)


def test_clean_cells_use_the_plain_names():
    assert split_cell("pypdf") == ("pypdf", "clean")
    assert split_cell("deepseek_vl@heavy") == ("deepseek_vl", "heavy")


def test_the_frozen_set_has_only_dev_docs(con):
    docs = freeze(con, per_band=5)
    assert "hidden" not in docs
    assert docs_for(con, SET_NAME) == sorted(docs)
    assert docs_for(con, "test") == ["hidden"]


def test_a_frozen_set_cannot_change(con):
    freeze(con, per_band=1)
    con.execute("DELETE FROM eval_sets WHERE doc_id = 'a'")
    with pytest.raises(SystemExit, match="frozen"):
        freeze(con, per_band=5)
