"""Repair retries with a fake model. No network, no key, no cost."""

import json

from docintel.core.llm import LLMResult, _parse
from docintel.domain.extract import retry
from docintel.domain.schema.fields import ContractFields
from docintel.evals.runner import empty_answer

CONTRACT = "This Agreement is dated as of March 1, 2020. Neither party may assign this Agreement."
DATE = {"quotes": ["dated as of March 1, 2020"], "value": "2020-03-01", "found": True}
GOOD = {"quotes": ["Neither party may assign this Agreement."], "found": True}
MADE_UP = {"quotes": ["Either party may assign this Agreement."], "found": True}


def answer(**fields) -> str:
    """The raw JSON of an answer: all 12 fields not found, except the ones given."""
    data = {field: empty_answer(field) for field in ContractFields.model_fields}
    return json.dumps(data | fields)


def fake_llm(monkeypatch, *replies: str) -> list:
    """Make `call_llm` return `replies` in order. Returns the messages of each call."""
    sent = []

    def call(messages, schema, *, model=None):
        sent.append(messages)
        raw = replies[len(sent) - 1]
        parsed, error = _parse(schema, raw)
        return LLMResult(
            raw_text=raw,
            parsed=parsed,
            error=error,
            usage={},
            cost_usd=0.002,
            latency_ms=10,
            model="fake",
            provider=None,
            attempts=1,
        )

    monkeypatch.setattr(retry, "call_llm", call)
    return sent


def test_no_retry_when_the_first_answer_is_clean(monkeypatch):
    sent = fake_llm(monkeypatch, answer(agreement_date=DATE))
    attempts = retry.extract_with_retry(CONTRACT)
    assert len(attempts) == len(sent) == 1


def test_a_fixed_error_stops_after_one_retry(monkeypatch):
    sent = fake_llm(monkeypatch, answer(anti_assignment=MADE_UP), answer(anti_assignment=GOOD))
    attempts = retry.extract_with_retry(CONTRACT)
    assert [len(a.errors) for a in attempts] == [1, 0]
    assert [m["role"] for m in sent[1]] == ["system", "user", "assistant", "user"]
    assert "anti_assignment (quote_missing)" in sent[1][-1]["content"]


def test_the_same_errors_twice_stop_early(monkeypatch):
    sent = fake_llm(monkeypatch, *[answer(anti_assignment=MADE_UP)] * 3)
    retry.extract_with_retry(CONTRACT, max_retries=2)
    assert len(sent) == 2  # the third call would be wasted money


def test_bad_schema_sends_the_pydantic_error_once(monkeypatch):
    sent = fake_llm(monkeypatch, "", answer(anti_assignment=GOOD))
    attempts = retry.extract_with_retry(CONTRACT)
    message = sent[1][-1]["content"]
    assert message.count("bad_schema") == 1
    assert "Invalid JSON" in message
    assert retry.final_answer(attempts) == attempts[1].result.parsed


def test_merge_changes_only_the_broken_field(monkeypatch):
    moved = DATE | {"value": "2020-03-02"}  # the retry also changed a field that was fine
    fake_llm(
        monkeypatch,
        answer(agreement_date=DATE, anti_assignment=MADE_UP),
        answer(agreement_date=moved, anti_assignment=GOOD),
    )
    final = retry.final_answer(retry.extract_with_retry(CONTRACT))
    assert final.agreement_date.value == "2020-03-01"
    assert final.anti_assignment.quotes == GOOD["quotes"]
