"""Shapes of the API's own answers. The extraction answer is `ExtractResult` from the pipeline."""

from typing import Literal, Self

from pydantic import BaseModel, model_validator

from docintel.domain.schema.fields import FieldName

Value = str | list[str] | None  # the same type as a field's `value`


class Health(BaseModel):
    status: str
    version: str


class Review(BaseModel):
    """What the review card sends: accept the value, or replace it."""

    request_id: str
    field: FieldName
    action: Literal["accept", "modify"]
    value: Value = None  # only for "modify"

    @model_validator(mode="after")
    def value_only_when_modified(self) -> Self:
        if self.action == "modify" and self.value is None:
            raise ValueError("modify needs a value")
        if self.action == "accept" and self.value is not None:
            raise ValueError("accept keeps the old value, so send no value")
        return self


class ReviewSaved(BaseModel):
    review_id: str
    field: FieldName
    action: Literal["accept", "modify"]
    old: Value
    new: Value
