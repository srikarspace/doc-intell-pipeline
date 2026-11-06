"""Content rules for one answer. Each field gets its own issues, so one bad field stays alone."""

import re
from datetime import date

from docintel.core.llm import LLMResult
from docintel.domain.schema.fields import ContractFields
from docintel.domain.validate.citations import quote_status, words
from docintel.domain.validate.issues import Issue

DATE_SHAPE = re.compile(r"\d{4}(-\d{2}(-\d{2})?)?")  # YYYY, YYYY-MM or YYYY-MM-DD, as in the prompt
OLDEST_YEAR = 1900


def date_ok(value: str) -> bool:
    """A real calendar date, in the prompt's format, not too old and not in the future."""
    if not DATE_SHAPE.fullmatch(value):
        return False
    year, month, day = (value.split("-") + ["01", "01"])[:3]  # a missing part counts as "01"
    try:
        parsed = date(int(year), int(month), int(day))
    except ValueError:  # like 2020-13-45
        return False
    return OLDEST_YEAR <= parsed.year and parsed <= date.today()


def check_quotes(field: str, quotes: list[str], source_words: list[str]) -> list[Issue]:
    """One issue per quote that is not clean."""
    issues = []
    for quote in quotes:
        status = quote_status(quote, source_words)
        short = quote[:80]
        if status == "missing":
            issues.append(Issue(field=field, rule="quote_missing", severity="error", detail=short))
        elif status == "gap":
            issues.append(Issue(field=field, rule="quote_gap", severity="warn", detail=short))
        elif status == "no_words":
            issues.append(Issue(field=field, rule="quote_no_words", severity="warn", detail=short))
    return issues


def check_found(field: str, answer) -> list[Issue]:
    """Do found, quotes and value agree with each other?"""
    problems = []
    if answer.found and not answer.quotes:
        problems.append(("found_no_quote", "found is true, but there are no quotes"))
    if not answer.found and answer.quotes:
        problems.append(("quote_not_found", "found is false, but there are quotes"))
    if hasattr(answer, "value"):
        if answer.found and not answer.value:
            problems.append(("found_no_value", "found is true, but value is empty"))
        if not answer.found and answer.value:
            problems.append(("value_not_found", "found is false, but value is not empty"))
    return [Issue(field=field, rule=r, severity="error", detail=d) for r, d in problems]


def check_field(field: str, answer, source_words: list[str]) -> list[Issue]:
    """All issues for one field."""
    issues = check_found(field, answer) + check_quotes(field, answer.quotes, source_words)
    if field == "agreement_date" and answer.value and not date_ok(answer.value):
        issues.append(Issue(field=field, rule="bad_date", severity="error", detail=answer.value))
    return issues


def check_answer(fields: ContractFields, text: str) -> list[Issue]:
    """All issues for one contract. The contract text is split into words only once."""
    source_words = words(text)
    issues = []
    for field in ContractFields.model_fields:
        issues += check_field(field, getattr(fields, field), source_words)
    return issues


def bad_schema(detail: str) -> list[Issue]:
    """The answer did not fit the schema, so every field has this problem."""
    return [
        Issue(field=field, rule="bad_schema", severity="error", detail=detail)
        for field in ContractFields.model_fields
    ]


def check_result(result: LLMResult[ContractFields], text: str) -> list[Issue]:
    """The issues for one LLM answer, whether or not it fit the schema."""
    if result.parsed is None:
        return bad_schema(result.error or "no answer")
    return check_answer(result.parsed, text)
