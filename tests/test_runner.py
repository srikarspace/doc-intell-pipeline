"""Runner rules with a fake extract. No network, no key, no CUAD files."""

from docintel.core.llm import LLMResult
from docintel.domain.schema.fields import ContractFields
from docintel.evals import runner

FIELDS = {field: runner.empty_answer(field) for field in ContractFields.model_fields}
FIELDS["parties"] = {"quotes": ["Acme Inc."], "value": ["Acme Inc.", "Beta LLC"], "found": True}
FIELDS["governing_law"] = {"quotes": ["laws of Michigan"], "value": "Michigan", "found": True}
PRED = ContractFields.model_validate(FIELDS)


def result(parsed: ContractFields | None) -> LLMResult[ContractFields]:
    return LLMResult(
        raw_text="{}",
        parsed=parsed,
        error=None if parsed else "bad json",
        usage={},
        cost_usd=0.001,
        latency_ms=10,
        model="fake",
        provider=None,
        attempts=1,
    )


def test_rows_rebuild_the_same_answer():
    rows = runner.to_rows("r1", "d1", result(PRED))
    assert len(rows) == 12
    assert runner.from_rows([(field, answer) for _, _, field, _, _, answer in rows]) == PRED


def test_bad_answer_becomes_12_empty_fields():
    rows = runner.to_rows("r1", "d1", result(None))
    assert {(ok, found) for _, _, _, ok, found, _ in rows} == {(False, False)}
    runner.from_rows([(field, answer) for _, _, field, _, _, answer in rows])  # still valid
