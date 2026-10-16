"""Schema rules that strict mode needs. No network, no key."""

import pytest
from pydantic import ValidationError

from docintel.domain.schema.fields import CUAD_CATEGORY, ContractFields, Strict
from docintel.evals.datasets import FIELDS


class Answer(Strict):  # a tiny model, so two tests do not depend on your field choices
    quotes: list[str]
    found: bool


def test_schema_is_strict():
    """Strict mode needs: no extra keys, and every key required, on every object."""
    schema = ContractFields.model_json_schema()
    for obj in [schema, *schema.get("$defs", {}).values()]:
        assert obj["additionalProperties"] is False
        assert set(obj["required"]) == set(obj["properties"])


def test_schema_covers_the_12_fields():
    assert set(CUAD_CATEGORY) == set(ContractFields.model_fields)
    assert sorted(CUAD_CATEGORY.values()) == sorted(f for group in FIELDS.values() for f in group)


def test_no_type_guessing():
    with pytest.raises(ValidationError):
        Answer.model_validate_json('{"quotes": [], "found": "yes"}')


def test_no_unknown_keys():
    with pytest.raises(ValidationError):
        Answer.model_validate_json('{"quotes": [], "found": true, "note": "hi"}')
