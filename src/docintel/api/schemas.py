"""Shapes of the API's own answers. The extraction answer is `ExtractResult` from the pipeline."""

from pydantic import BaseModel


class Health(BaseModel):
    status: str
    version: str
