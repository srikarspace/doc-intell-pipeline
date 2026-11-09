"""The vision parser with a fake OpenRouter: no network, no key, no cost."""

import json

import httpx2
import pytest
from openai import OpenAI
from pypdf import PdfWriter

from docintel.core.config import get_settings
from docintel.core.llm import call_llm
from docintel.domain.parse import vision
from docintel.domain.parse.cache import cached_parse
from docintel.domain.parse.vision import (
    MAX_OUTPUT_TOKENS,
    Budget,
    BudgetExceeded,
    PageText,
    TooManyPages,
    make_vision_parser,
    page_images,
)
from docintel.evals.store import connect


def reply(content: str, cost: float = 0.01) -> httpx2.Response:
    return httpx2.Response(
        200,
        json={
            "id": "gen-1",
            "object": "chat.completion",
            "created": 0,
            "model": "fake/vision",
            "provider": "FakeCloud",
            "choices": [
                {
                    "index": 0,
                    "finish_reason": "stop",
                    "message": {"role": "assistant", "content": content},
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "cost": cost},
        },
    )


def fake_client(*responses: httpx2.Response) -> tuple[OpenAI, list]:
    sent = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        sent.append(json.loads(request.content))
        return responses[len(sent) - 1]

    http = httpx2.Client(transport=httpx2.MockTransport(handler))
    client = OpenAI(
        api_key="sk-or-v1-test", base_url="https://fake.test/v1", max_retries=0, http_client=http
    )
    return client, sent


@pytest.fixture(autouse=True)
def setup(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-test")
    get_settings.cache_clear()
    monkeypatch.setattr(vision, "connect", lambda: connect(tmp_path / "test.duckdb"))
    monkeypatch.setattr(vision, "page_images", lambda path: ["data:a", "data:b"])
    yield
    get_settings.cache_clear()


def page(text: str) -> httpx2.Response:
    return reply(json.dumps({"text": text}))


def test_pages_stay_in_order_and_costs_add_up(tmp_path):
    client, sent = fake_client(page("one"), page(""))
    doc = make_vision_parser("deepseek_vl", client=client)(tmp_path / "x.pdf")
    assert doc.pages == ["one", ""]
    assert doc.cost_usd == pytest.approx(0.02)
    assert all(body["max_tokens"] == MAX_OUTPUT_TOKENS for body in sent)


def test_a_bad_answer_raises_and_is_not_cached(tmp_path):
    client, _ = fake_client(reply("   "))
    parser = make_vision_parser("deepseek_vl", client=client)
    with pytest.raises(ValueError, match="bad answer"):
        cached_parse("deepseek_vl", "doc-1", tmp_path / "x.pdf", parser, tmp_path / "cache")
    assert not (tmp_path / "cache").exists()


def test_the_budget_stops_before_the_call(tmp_path):
    client, sent = fake_client(page("one"), page("two"))
    budget = Budget(0.015)
    parser = make_vision_parser("deepseek_vl", client=client, budget=budget, worst_page_usd=0.01)
    with pytest.raises(BudgetExceeded):
        parser(tmp_path / "x.pdf")
    assert len(sent) == 1  # page 2 could pass the limit, so it was never sent
    assert budget.spent == pytest.approx(0.01)


def test_a_failed_call_still_counts_as_spent(tmp_path):
    client, _ = fake_client(reply("   ", cost=0.46))
    budget = Budget(1.0)
    with pytest.raises(ValueError):
        make_vision_parser("deepseek_vl", client=client, budget=budget)(tmp_path / "x.pdf")
    assert budget.spent == pytest.approx(0.46)


def test_too_many_pages_is_refused(tmp_path, monkeypatch):
    monkeypatch.undo()
    writer = PdfWriter()
    for _ in range(21):
        writer.add_blank_page(width=200, height=200)
    pdf = tmp_path / "long.pdf"
    writer.write(pdf)
    with pytest.raises(TooManyPages):
        page_images(pdf)


def test_other_calls_send_no_token_limit():
    client, sent = fake_client(page("x"))
    call_llm([{"role": "user", "content": "hi"}], PageText, client=client, backoff_s=0)
    assert "max_tokens" not in sent[0]
