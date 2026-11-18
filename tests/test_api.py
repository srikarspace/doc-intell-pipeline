"""The API routes, with the fakes from `conftest.py`."""

import time

import pytest

from docintel.api import routes
from docintel.domain.schema.fields import FIELDS

PDF = b"%PDF-1.4 fake"


def post(client, fields: list[str], data: bytes = PDF):
    return client.post("/v1/extract", files={"pdf": ("c.pdf", data)}, data={"fields": fields})


def test_health(api):
    assert api.get("/health").json() == {"status": "ok", "version": routes.VERSION}


def test_the_fields_are_listed_for_the_ui(api):
    fields = api.get("/v1/fields").json()
    assert [f["name"] for f in fields] == list(FIELDS)  # all 12, in schema order
    assert len({f["group"] for f in fields}) == 4


def test_only_the_chosen_fields_come_back(api, sent):
    response = post(api, ["governing_law", "parties"])
    body = response.json()
    assert response.status_code == 200
    assert list(body["fields"]) == ["parties", "governing_law"]  # schema order
    assert body["fields"]["parties"]["value"] == ["Acme Inc.", "Beta LLC"]
    assert body["cost_usd"] == pytest.approx(0.001)
    assert sent == ["ContractFields"]  # one call, for all 12 fields


def test_no_fields_means_all_12(api):
    assert list(post(api, []).json()["fields"]) == list(FIELDS)


def test_an_unknown_field_is_refused_before_any_call(api, sent):
    response = post(api, ["parties", "payment_terms"])
    assert response.status_code == 422
    assert sent == []


def test_a_file_that_is_not_a_pdf_is_refused(api):
    assert post(api, ["parties"], data=b"hello").status_code == 415


def test_a_large_file_is_refused(api, monkeypatch):
    monkeypatch.setattr(routes, "MAX_BYTES", 5)
    assert post(api, ["parties"]).status_code == 413


def test_a_slow_request_times_out(api, monkeypatch):
    monkeypatch.setattr(routes, "TIMEOUT_S", 0.05)
    monkeypatch.setattr(routes, "run_pipeline", lambda *args, **kwargs: time.sleep(0.5))
    assert post(api, ["parties"]).status_code == 504


def test_samples_are_listed_and_served(api):
    samples = api.get("/v1/samples").json()
    assert len(samples) == 10
    assert sum(s["scan"] for s in samples) == 1
    pdf = api.get(f"/v1/samples/{samples[0]['id']}/pdf")
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.content.startswith(b"%PDF-")


def test_an_unknown_sample_is_404(api):
    assert api.get("/v1/samples/../../.env/pdf").status_code == 404
    assert api.post("/v1/extract", data={"sample_id": "nope"}).status_code == 404


def test_a_sample_can_be_extracted(api):
    response = api.post("/v1/extract", data={"sample_id": "kubient", "fields": ["parties"]})
    assert response.status_code == 200
    assert response.json()["document"]["sample_id"] == "kubient"


def test_a_pdf_and_a_sample_together_are_refused(api):
    response = api.post("/v1/extract", files={"pdf": ("c.pdf", PDF)}, data={"sample_id": "kubient"})
    assert response.status_code == 422
