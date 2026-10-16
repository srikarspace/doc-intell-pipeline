"""Thin OpenRouter client: messages + Pydantic model in, LLMResult out. Every call is logged."""

import time
import uuid
from dataclasses import dataclass

import duckdb
import openai
from openai import OpenAI
from pydantic import BaseModel, ValidationError

from docintel.core.config import get_settings


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


def make_client() -> OpenAI:
    s = get_settings()
    return OpenAI(
        api_key=s.openrouter_api_key.get_secret_value(),
        base_url=s.openrouter_base_url,
        timeout=s.llm_timeout_s,
        max_retries=0,  # we retry ourselves, and only on network errors and 429
    )


@dataclass
class LLMResult[T: BaseModel]:
    raw_text: str
    parsed: T | None  # None when the text did not fit the schema
    error: str | None  # the Pydantic error, so 2b can send it back to the model
    usage: dict
    cost_usd: float | None
    latency_ms: int
    model: str
    provider: str | None
    attempts: int


def _parse[T: BaseModel](schema: type[T], raw_text: str) -> tuple[T | None, str | None]:
    try:
        return schema.model_validate_json(raw_text), None
    except ValidationError as e:
        return None, str(e)


RETRYABLE = (openai.APIConnectionError, openai.RateLimitError)  # timeouts are connection errors


def _send(client, messages, schema, model, max_attempts, backoff_s):
    """One request, tried again only on RETRYABLE errors. Returns (response, attempts)."""
    for attempt in range(1, max_attempts + 1):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                response_format=response_format(schema),
                extra_body={"provider": {"require_parameters": True}},
                temperature=0,
            )
            return resp, attempt
        except RETRYABLE:
            if attempt == max_attempts:
                raise
            time.sleep(backoff_s * 2 ** (attempt - 1))  # 1 s, 2 s, 4 s


LLM_CALLS = """
CREATE TABLE IF NOT EXISTS llm_calls (
    call_id VARCHAR PRIMARY KEY, created_at TIMESTAMP DEFAULT current_timestamp,
    run_id VARCHAR, model VARCHAR, provider VARCHAR, schema_name VARCHAR,
    attempts INTEGER, ok BOOLEAN, error VARCHAR, raw_text VARCHAR,
    prompt_tokens INTEGER, completion_tokens INTEGER, cost_usd DOUBLE, latency_ms INTEGER
)
"""


def log_call(con, result: LLMResult, schema_name: str, run_id: str | None = None) -> None:
    con.execute(LLM_CALLS)
    con.execute(
        "INSERT INTO llm_calls (call_id, run_id, model, provider, schema_name, attempts, ok, "
        "error, raw_text, prompt_tokens, completion_tokens, cost_usd, latency_ms) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            str(uuid.uuid4()),
            run_id,
            result.model,
            result.provider,
            schema_name,
            result.attempts,
            result.parsed is not None,
            result.error,
            result.raw_text,
            result.usage.get("prompt_tokens"),
            result.usage.get("completion_tokens"),
            result.cost_usd,
            result.latency_ms,
        ],
    )


def call_llm[T: BaseModel](
    messages: list[dict],
    schema: type[T],
    *,
    con: duckdb.DuckDBPyConnection | None = None,
    run_id: str | None = None,
    model: str | None = None,
    client: OpenAI | None = None,
    backoff_s: float = 1.0,
) -> LLMResult[T]:
    """Send messages, ask for JSON that fits `schema`, check it with Pydantic, log the call."""
    s = get_settings()
    model = model or s.docintel_model
    client = client or make_client()

    start = time.perf_counter()
    resp, attempts = _send(client, messages, schema, model, s.llm_max_attempts, backoff_s)
    latency_ms = round((time.perf_counter() - start) * 1000)

    raw_text = resp.choices[0].message.content or ""
    parsed, error = _parse(schema, raw_text)
    usage = resp.usage.model_dump() if resp.usage else {}
    result = LLMResult(
        raw_text=raw_text,
        parsed=parsed,
        error=error,
        usage=usage,
        cost_usd=usage.get("cost"),
        latency_ms=latency_ms,
        model=resp.model,
        provider=getattr(resp, "provider", None),
        attempts=attempts,
    )
    if con is not None:
        log_call(con, result, schema.__name__, run_id)
    return result
