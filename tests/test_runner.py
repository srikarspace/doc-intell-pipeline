"""Runner rules with a fake extract. No network, no key, no CUAD files."""

from docintel.core.llm import LLMResult
from docintel.domain.extract.retry import Attempt
from docintel.domain.schema.fields import ContractFields
from docintel.evals import runner
from docintel.evals.store import connect

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


def test_resume_skips_done_docs_and_retries_crashed_ones(monkeypatch):
    def fake_extract(text, model, *, prompt_version, max_retries):
        if text == "crash":
            raise TimeoutError("network down")
        return [Attempt(0, result(PRED), [])]

    monkeypatch.setattr(runner, "extract_with_retry", fake_extract)
    texts = {"d1": "ok", "d2": "crash", "d3": "ok"}
    with connect(":memory:") as con:
        con.execute(runner.TABLES)
        failed = runner.run_docs(con, "r1", texts, "fake", "v1", concurrency=2)
        left = runner.todo(con, "r1", list(texts))
        n_calls = con.execute("SELECT count(*) FROM llm_calls WHERE run_id = 'r1'").fetchone()
    assert failed == 1
    assert left == ["d2"]  # only the crashed doc is done again
    assert n_calls == (2,)
