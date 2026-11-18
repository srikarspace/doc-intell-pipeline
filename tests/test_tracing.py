"""The trace of one request: which spans, under which parent, joined by one request_id."""

import pytest
from openinference.instrumentation.openai import OpenAIInstrumentor
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from docintel.domain import pipeline
from docintel.domain.pipeline import TooLong


@pytest.fixture(scope="module")
def exporter():
    """Spans go to a list in memory, not to Phoenix. A process can set its provider only once."""
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    OpenAIInstrumentor().instrument(tracer_provider=provider)
    yield exporter
    OpenAIInstrumentor().uninstrument()


@pytest.fixture
def spans(exporter):
    exporter.clear()
    return exporter


def post(api, fields):
    return api.post("/v1/extract", data={"sample_id": "kubient", "fields": fields})


def tree(spans) -> dict[str, str | None]:
    """Each span's name, and the name of its parent."""
    finished = spans.get_finished_spans()
    names = {s.context.span_id: s.name for s in finished}
    return {s.name: names.get(s.parent.span_id) if s.parent else None for s in finished}


def test_one_request_is_one_tree(api, spans):
    post(api, ["parties"])
    assert tree(spans) == {
        "POST /v1/extract": None,  # FastAPI makes these 4 by itself, once a provider is set
        "fastapi.dependencies": "POST /v1/extract",
        "fastapi.endpoint": "POST /v1/extract",
        "fastapi.serialization": "POST /v1/extract",
        "pipeline": "fastapi.endpoint",  # in another thread, but under the same request
        "parse": "pipeline",
        "extract": "pipeline",
        "attempt": "extract",
        "ChatCompletion": "attempt",  # made by OpenInference, not by us
        "check": "pipeline",
        "highlight": "pipeline",
    }


def test_one_id_joins_the_header_the_answer_and_the_trace(api, spans):
    api.get("/health")  # not traced
    response = post(api, ["parties"])
    (root,) = [s for s in spans.get_finished_spans() if s.name == "pipeline"]
    assert response.headers["X-Request-ID"] == response.json()["request_id"]
    assert root.attributes["request_id"] == response.json()["request_id"]
    assert "GET /health" not in tree(spans)


def test_a_failed_step_is_marked_in_the_trace(api, spans, monkeypatch):
    def too_long(path):
        raise TooLong("120 pages, the limit is 100")

    monkeypatch.setattr(pipeline, "parse_pdf", too_long)
    assert post(api, ["parties"]).status_code == 413
    (parse,) = [s for s in spans.get_finished_spans() if s.name == "parse"]
    assert parse.status.status_code.name == "ERROR"
    assert "ChatCompletion" not in tree(spans)  # it stopped before the paid call
