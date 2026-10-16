"""LLM client tests with a fake OpenRouter (no network, no key, no cost)."""

import httpx2
import openai
import pytest
from openai import OpenAI

from docintel.core.config import get_settings
from docintel.core.llm import call_llm
from docintel.domain.schema.fields import Strict
from docintel.evals.store import connect

MESSAGES = [{"role": "user", "content": "Is there a non-compete clause?"}]


class Answer(Strict):  # a tiny schema, so these tests do not depend on your field choices
    quotes: list[str]
    found: bool


def reply(content: str) -> httpx2.Response:
    """A fake OpenRouter answer, shaped like the real one."""
    return httpx2.Response(
        200,
        json={
            "id": "gen-1",
            "object": "chat.completion",
            "created": 0,
            "model": "qwen/test",
            "provider": "FakeCloud",
            "choices": [
                {
                    "index": 0,
                    "finish_reason": "stop",
                    "message": {"role": "assistant", "content": content},
                }
            ],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15,
                "cost": 1e-6,
            },
        },
    )


def fake_client(*responses: httpx2.Response) -> tuple[OpenAI, list]:
    """A real OpenAI client whose HTTP layer returns `responses` in order."""
    sent = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        sent.append(request)
        return responses[len(sent) - 1]

    http = httpx2.Client(transport=httpx2.MockTransport(handler))
    client = OpenAI(
        api_key="sk-or-v1-test", base_url="https://fake.test/v1", max_retries=0, http_client=http
    )
    return client, sent


@pytest.fixture(autouse=True)
def settings(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-test")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_valid_json_is_parsed_and_logged():
    client, _ = fake_client(reply('{"quotes": ["shall not compete"], "found": true}'))
    with connect(":memory:") as con:
        r = call_llm(MESSAGES, Answer, con=con, client=client)
        rows = con.execute("SELECT ok, provider, cost_usd FROM llm_calls").fetchall()
    assert r.parsed == Answer(quotes=["shall not compete"], found=True)
    assert r.error is None
    assert rows == [(True, "FakeCloud", 1e-6)]


def test_bad_json_is_an_error_not_a_crash():
    client, _ = fake_client(reply('{"quotes": [], "found": "yes"}'))
    with connect(":memory:") as con:
        r = call_llm(MESSAGES, Answer, con=con, client=client)
        rows = con.execute("SELECT ok, raw_text FROM llm_calls").fetchall()
    assert r.parsed is None
    assert "found" in r.error
    assert rows == [(False, '{"quotes": [], "found": "yes"}')]


def test_429_is_retried():
    client, sent = fake_client(httpx2.Response(429), reply('{"quotes": [], "found": false}'))
    r = call_llm(MESSAGES, Answer, client=client, backoff_s=0)
    assert r.attempts == 2
    assert len(sent) == 2


def test_400_is_not_retried():
    client, sent = fake_client(httpx2.Response(400), reply("{}"))
    with pytest.raises(openai.BadRequestError):
        call_llm(MESSAGES, Answer, client=client, backoff_s=0)
    assert len(sent) == 1
