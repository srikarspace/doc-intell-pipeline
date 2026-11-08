"""Trust replays with a tiny in-memory database. No network, no key, no CUAD files."""

from docintel.domain.schema.fields import ContractFields
from docintel.evals import trust
from docintel.evals.runner import TABLES, empty_answer
from docintel.evals.store import connect

FIELDS = {field: empty_answer(field) for field in ContractFields.model_fields}
FIELDS["governing_law"] = {"quotes": ["laws of Michigan"], "value": "Michigan", "found": True}
FIELDS["renewal_term"] = {"quotes": ["renews for *** years"], "value": None, "found": True}
FIRST = ContractFields.model_validate(FIELDS)
FINAL = trust.blank(FIRST, {"governing_law"})  # any answer that is not FIRST


def test_blank_changes_only_the_named_fields():
    answer = trust.blank(FIRST, {"renewal_term"})
    assert answer.renewal_term.model_dump() == empty_answer("renewal_term")
    assert answer.governing_law == FIRST.governing_law
    assert FIRST.renewal_term.found  # the original does not change


def test_first_answers_read_attempt_0_not_the_final():
    with connect(":memory:") as con:
        con.execute(TABLES)
        rows = [
            ("r1", "d1", 0, FIRST.model_dump_json()),
            ("r1", "d1", 1, FINAL.model_dump_json()),
            ("r1", "d2", 0, '{"parties": '),  # did not fit the schema
        ]
        for run_id, doc_id, attempt_no, raw_text in rows:
            con.execute(
                "INSERT INTO attempts (run_id, doc_id, attempt_no, raw_text) VALUES (?, ?, ?, ?)",
                [run_id, doc_id, attempt_no, raw_text],
            )
        assert trust.first_answers(con, "r1") == {"d1": FIRST, "d2": None}


def test_derive_copies_the_parent_and_can_run_again(monkeypatch):
    monkeypatch.setattr(trust, "score", lambda con, run_id: 0)  # these need CUAD labels and text
    monkeypatch.setattr(trust, "validate", lambda con, run_id: 0)
    with connect(":memory:") as con:
        con.execute(TABLES)
        con.execute(
            "INSERT INTO runs (run_id, split, model, n_docs, est_cost_usd, max_retries) "
            "VALUES ('r1', 'dev', 'fake', 2, 0.1, 2)"
        )
        trust.derive(con, "r1", "first", {"d1": FIRST, "d2": None})
        run_id = trust.derive(con, "r1", "first", {"d1": FIRST, "d2": None})  # again: no error
        run = con.execute(
            "SELECT split, model, est_cost_usd FROM runs WHERE run_id = ?", [run_id]
        ).fetchone()
        (n_rows,) = con.execute(
            "SELECT count(*) FROM predictions WHERE run_id = ?", [run_id]
        ).fetchone()
    assert run_id == "r1-first"
    assert run == ("dev", "fake", 0)
    assert n_rows == 24  # 12 fields for each contract, once
