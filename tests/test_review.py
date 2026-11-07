"""Review rules and stored issues on fake answers. No network, no key, no CUAD files."""

import json

from docintel.domain.schema.fields import ContractFields
from docintel.domain.validate.review import needs_review, review_answer
from docintel.evals import runner
from docintel.evals.store import connect

CONTRACT = """Limitation of Liability. Neither party's liability shall exceed the fees paid.
Either party may terminate this Agreement upon 90 days written notice."""


def answer(**fields) -> ContractFields:
    """All 12 fields not found, except the ones given."""
    data = {field: runner.empty_answer(field) for field in ContractFields.model_fields}
    return ContractFields.model_validate(data | fields)


def test_off_topic_quote_is_flagged():
    quote = "Either party may terminate this Agreement"
    pred = answer(non_compete={"quotes": [quote], "found": True})
    assert [(i.field, i.rule) for i in review_answer(pred, CONTRACT)] == [
        ("non_compete", "quote_off_topic"),
        ("cap_on_liability", "maybe_missed"),
    ]


def test_found_cap_is_not_flagged():
    quote = "Neither party's liability shall exceed the fees paid."
    pred = answer(cap_on_liability={"quotes": [quote], "value": "the fees paid", "found": True})
    assert review_answer(pred, CONTRACT) == []


def test_review_issues_are_only_warnings():
    pred = answer(non_compete={"quotes": ["upon 90 days written notice"], "found": True})
    issues = review_answer(pred, CONTRACT)
    assert {i.severity for i in issues} == {"warn"}
    assert needs_review(issues) == {"non_compete", "cap_on_liability"}


def test_validate_replays_and_marks_bad_answers(monkeypatch):
    monkeypatch.setitem(runner.PARSERS, "cuad_txt", lambda con, doc_id: CONTRACT)
    fields = answer().model_dump()
    good = [("r1", "d1", f, True, False, json.dumps(a)) for f, a in fields.items()]
    bad = [("r1", "d2", f, False, False, json.dumps(a)) for f, a in fields.items()]
    with connect(":memory:") as con:
        con.execute(runner.TABLES)
        con.execute("INSERT INTO runs (run_id, parser) VALUES ('r1', 'cuad_txt')")
        con.executemany("INSERT INTO predictions VALUES (?, ?, ?, ?, ?, ?)", good + bad)
        first = runner.validate(con, "r1")
        again = runner.validate(con, "r1")  # a replay replaces the rows, it does not add to them
        rules = con.execute("SELECT doc_id, rule, count(*) FROM issues GROUP BY ALL ORDER BY 1")
        rules = rules.fetchall()
    assert first == again == 13
    assert rules == [("d1", "maybe_missed", 1), ("d2", "bad_schema", 12)]
