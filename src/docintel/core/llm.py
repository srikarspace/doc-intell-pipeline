"""Thin OpenRouter client: messages + Pydantic model in, LLMResult out. Every call is logged."""

from pydantic import BaseModel


def response_format(schema: type[BaseModel]) -> dict:
    """The `response_format` that asks the provider to follow this Pydantic model."""
    return {
        "type": "json_schema",
        "json_schema": {
            "name": schema.__name__,
            "strict": True,
            "schema": schema.model_json_schema(),
        },
    }
