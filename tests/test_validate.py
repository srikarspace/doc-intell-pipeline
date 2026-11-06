"""Validator rules on fake model answers. No network, no key."""

import json

import pytest

from docintel.core.llm import LLMResult, _parse
from docintel.domain.schema.fields import ContractFields
from docintel.domain.validate.citations import quote_status, words
from docintel.domain.validate.rules import check_result, date_ok

CONTRACT = """This Agreement is dated as of March 1, 2020. Neither party may assign
this Agreement without consent.
Page 7
The license is non-transferable."""


def empty_answer() -> dict:
    """A valid answer for all 12 fields: nothing found."""
    answer = {field: {"quotes": [], "found": False} for field in ContractFields.model_fields}
    answer["parties"]["value"] = []
    for field in (
        "agreement_date",
        "governing_law",
        "renewal_term",
        "notice_period_to_terminate_renewal",
        "cap_on_liability",
    ):
        answer[field]["value"] = None
    return answer


def check(raw: str) -> list:
    """The same path as a real answer: parse the raw text, then check it."""
    parsed, error = _parse(ContractFields, raw)
    result = LLMResult(
        raw_text=raw,
        parsed=parsed,
        error=error,
        usage={},
        cost_usd=None,
        latency_ms=0,
        model="fake",
        provider=None,
        attempts=1,
    )
    return check_result(result, CONTRACT)


def rules(raw: str) -> list[tuple[str, str]]:
    return [(i.field, i.rule) for i in check(raw)]


def test_valid_answer_has_no_issues():
    answer = empty_answer()
    answer["agreement_date"] = {
        "quotes": ["dated as of March 1, 2020"],
        "value": "2020-03-01",
        "found": True,
    }
    assert rules(json.dumps(answer)) == []


def test_malformed_answer_marks_every_field():
    issues = check("")  # a real V4.1 answer: an empty reply
    assert {i.rule for i in issues} == {"bad_schema"}
    assert {i.field for i in issues} == set(ContractFields.model_fields)


def test_wrong_type_marks_every_field():
    answer = empty_answer()
    answer["non_compete"]["found"] = "yes"
    assert {i.rule for i in check(json.dumps(answer))} == {"bad_schema"}


def test_made_up_quote_is_an_error_in_that_field_only():
    answer = empty_answer()
    answer["anti_assignment"] = {"quotes": ["Either party may assign freely."], "found": True}
    assert rules(json.dumps(answer)) == [("anti_assignment", "quote_missing")]


def test_found_needs_quote_and_value():
    answer = empty_answer()
    answer["renewal_term"]["found"] = True
    assert rules(json.dumps(answer)) == [
        ("renewal_term", "found_no_quote"),
        ("renewal_term", "found_no_value"),
    ]


@pytest.mark.parametrize(
    ("quote", "status"),
    [
        ("Neither party may assign this Agreement", "same_words"),  # across a newline
        ("NEITHER  PARTY MAY ASSIGN", "same_words"),  # case and spaces
        ("consent. The license is non-transferable", "gap"),  # "Page 7" is in between
        ("Neither party may assign this Agreement with consent", "missing"),  # a changed word
        ("March 2, 2020", "missing"),  # a changed number
        ("[●]", "no_words"),
    ],
)
def test_quote_status(quote, status):
    assert quote_status(quote, words(CONTRACT)) == status


@pytest.mark.parametrize(
    ("value", "ok"),
    [
        ("2020", True),
        ("2020-03", True),
        ("2020-03-01", True),
        ("2020-13-01", False),
        ("March 1, 2020", False),
        ("2999-01-01", False),
        ("1066", False),
    ],
)
def test_date_ok(value, ok):
    assert date_ok(value) is ok
