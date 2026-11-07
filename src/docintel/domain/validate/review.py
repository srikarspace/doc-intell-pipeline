"""Should a person look at this field? These rules read the answer and the contract, never gold."""

import re

from docintel.domain.schema.fields import ContractFields
from docintel.domain.validate.issues import Issue

TOPIC = {  # a quote for this field should hold at least one of these word parts
    "governing_law": ("govern", "law"),
    "non_compete": ("compet",),
    "change_of_control": ("control", "merger", "acqui", "change"),
    "anti_assignment": ("assign", "transfer"),
    "renewal_term": ("renew", "extend", "extension", "successive"),
    "notice_period_to_terminate_renewal": ("notice", "notif"),
    "cap_on_liability": ("liab", "damage", "exceed"),
    "license_grant": ("licens", "grant"),
    "ip_ownership_assignment": ("own", "assign", "title", "propert"),
    "non_transferable_license": ("transfer", "assign", "sublicens"),
}
MISSED = {  # the model says "not found", but the contract has these words
    "change_of_control": re.compile(r"change (of|in) control", re.I),
    "cap_on_liability": re.compile(
        r"limitation of liability|liability[^.;]{0,60}(shall not|will not|not) exceed", re.I
    ),
    "renewal_term": re.compile(r"\brenew", re.I),
}


def off_topic(field: str, answer) -> list[Issue]:
    """A real quote can still be about something else. Example: a notice quote with no "notice"."""
    if field not in TOPIC or not answer.found or not answer.quotes:
        return []
    quotes = " ".join(answer.quotes).lower()
    if any(part in quotes for part in TOPIC[field]):
        return []
    detail = answer.quotes[0][:80]
    return [Issue(field=field, rule="quote_off_topic", severity="warn", detail=detail)]


def maybe_missed(field: str, answer, text: str) -> list[Issue]:
    """The model says "not found", but the contract has words that often mean "found"."""
    if field not in MISSED or answer.found:
        return []
    match = MISSED[field].search(text)
    if match is None:
        return []
    return [Issue(field=field, rule="maybe_missed", severity="warn", detail=match.group(0)[:80])]


def review_answer(fields: ContractFields, text: str) -> list[Issue]:
    """The review issues for one contract: warnings only, so they never change an answer."""
    issues = []
    for field in ContractFields.model_fields:
        answer = getattr(fields, field)
        issues += off_topic(field, answer) + maybe_missed(field, answer, text)
    return issues


def needs_review(issues: list[Issue]) -> set[str]:
    """The fields a person must look at: every field with at least one issue."""
    return {issue.field for issue in issues}
