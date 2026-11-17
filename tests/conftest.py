"""Shared fakes for the API tests: a fake OpenRouter and a fake parser. No network, no cost."""

import json

import httpx2
import pytest
from fastapi.testclient import TestClient
from openai import OpenAI

from docintel.api import routes
from docintel.api.app import app
from docintel.core.config import get_settings
from docintel.domain import pipeline
from docintel.domain.parse.base import from_pages
from docintel.domain.schema.fields import ContractFields
from docintel.evals.runner import empty_answer

CONTRACT = "This Agreement is made between Acme Inc. and Beta LLC."


def contract_answer() -> dict:
    answer = {f: empty_answer(f) for f in ContractFields.model_fields}
    names = ["Acme Inc.", "Beta LLC"]
    answer["parties"] = {"quotes": names, "value": names, "found": True}
    return answer


def fake_llm(sent: list) -> OpenAI:
    """Answers every extraction call with `contract_answer()`, and notes each call in `sent`."""

    def handler(request: httpx2.Request) -> httpx2.Response:
        sent.append(json.loads(request.content)["response_format"]["json_schema"]["name"])
        message = {"role": "assistant", "content": json.dumps(contract_answer())}
        body = {
            "id": "gen-1",
            "object": "chat.completion",
            "created": 0,
            "model": "fake/model",
            "choices": [{"index": 0, "finish_reason": "stop", "message": message}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "cost": 0.001},
        }
        return httpx2.Response(200, json=body)

    http = httpx2.Client(transport=httpx2.MockTransport(handler))
    return OpenAI(
        api_key="sk-or-v1-test", base_url="https://fake.test/v1", max_retries=0, http_client=http
    )


@pytest.fixture
def sent() -> list:
    """The calls the fake model got, one schema name per call."""
    return []


@pytest.fixture
def api(monkeypatch, sent) -> TestClient:
    """A TestClient with the fake model and the fake parser."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-test")
    get_settings.cache_clear()
    monkeypatch.setattr(pipeline, "parse_pdf", lambda path: from_pages([CONTRACT], 0.0, 1, "pypdf"))
    monkeypatch.setattr(pipeline, "locate", lambda path, quotes: [])  # the fake PDF has no pages
    app.dependency_overrides[routes.get_llm_client] = lambda: fake_llm(sent)
    yield TestClient(app)
    app.dependency_overrides.clear()
    get_settings.cache_clear()
