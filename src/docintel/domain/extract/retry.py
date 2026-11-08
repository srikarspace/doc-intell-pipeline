"""Repair retries: send the errors back to the model, at most `max_retries` times."""

from dataclasses import dataclass

from docintel.core.llm import LLMResult, call_llm
from docintel.domain.extract.extract import PROMPTS, build_messages
from docintel.domain.schema.fields import ContractFields
from docintel.domain.validate.issues import Issue
from docintel.domain.validate.rules import check_result

FEEDBACK = PROMPTS / "retry.md"


@dataclass
class Attempt:
    """One call for one contract: 0 is the first answer, 1 and 2 are repair retries."""

    attempt_no: int
    result: LLMResult[ContractFields]
    issues: list[Issue]

    @property
    def errors(self) -> list[Issue]:
        return [i for i in self.issues if i.severity == "error"]


def error_keys(attempt: Attempt) -> set[tuple[str, str]]:
    """Which (field, rule) pairs failed. Two attempts with the same keys made no progress."""
    return {(i.field, i.rule) for i in attempt.errors}


def feedback(errors: list[Issue]) -> str:
    """The message that tells the model what to fix. A bad schema is one line, not 12."""
    if any(e.rule == "bad_schema" for e in errors):
        lines = [f"- every field (bad_schema): {errors[0].detail[:1000]}"]
    else:
        lines = [f"- {e.field} ({e.rule}): {e.detail}" for e in errors]
    return FEEDBACK.read_text(encoding="utf-8").replace("{errors}", "\n".join(lines))


def extract_with_retry(
    text: str, model: str | None = None, *, prompt_version: str = "v1", max_retries: int = 2
) -> list[Attempt]:
    """Every attempt for one contract, in order. Stops when there are no errors, or no progress."""
    messages = build_messages(text, prompt_version)
    attempts = []
    for attempt_no in range(max_retries + 1):
        result = call_llm(messages, ContractFields, model=model)
        attempt = Attempt(attempt_no, result, check_result(result, text))
        attempts.append(attempt)
        if not attempt.errors:
            break
        if attempt_no > 0 and error_keys(attempt) == error_keys(attempts[-2]):
            break  # the same errors came back, so another retry is wasted money
        messages = messages + [
            {"role": "assistant", "content": result.raw_text},
            {"role": "user", "content": feedback(attempt.errors)},
        ]
    return attempts


def final_answer(attempts: list[Attempt]) -> ContractFields | None:
    """The first answer that fits the schema. A broken field takes its newest fixed version."""
    good = [a for a in attempts if a.result.parsed is not None]
    if not good:
        return None
    base = good[0]
    broken = {i.field for i in base.errors}
    answer = base.result.parsed
    for attempt in good[1:]:  # oldest first, so the newest fix wins
        fixed = broken - {i.field for i in attempt.errors}
        answer = answer.model_copy(update={f: getattr(attempt.result.parsed, f) for f in fixed})
    return answer
