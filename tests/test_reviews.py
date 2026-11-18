"""Rows for requests and reviews, in a temp database. The fakes come from `conftest.py`."""

from docintel.db.app_data import db
from docintel.domain import pipeline
from docintel.domain.pipeline import TooLong


def extract(api, fields: list[str]) -> dict:
    return api.post("/v1/extract", data={"sample_id": "kubient", "fields": fields}).json()


def review(api, request_id: str, field: str, action: str, value=None):
    body = {"request_id": request_id, "field": field, "action": action, "value": value}
    return api.post("/v1/reviews", json=body)


def test_every_request_is_one_row_even_a_failed_one(api, monkeypatch):
    extract(api, ["parties"])

    def too_long(path):
        raise TooLong("120 pages, the limit is 100")

    monkeypatch.setattr(pipeline, "parse_pdf", too_long)
    extract(api, ["parties"])
    with db() as con:
        rows = con.execute(
            "SELECT status, error, fields FROM requests ORDER BY created_at"
        ).fetchall()
    assert rows == [(200, None, ["parties"]), (413, "120 pages, the limit is 100", ["parties"])]


def test_the_old_value_comes_from_the_server(api):
    answer = extract(api, ["parties"])
    saved = review(api, answer["request_id"], "parties", "modify", ["Acme Inc."]).json()
    assert saved["old"] == ["Acme Inc.", "Beta LLC"]  # from the stored answer, not from the browser
    assert saved["new"] == ["Acme Inc."]


def test_one_review_per_field_and_undo_frees_it(api):
    request_id = extract(api, ["parties"])["request_id"]
    first = review(api, request_id, "parties", "accept")
    assert first.status_code == 201
    assert review(api, request_id, "parties", "accept").status_code == 409
    review_id = first.json()["review_id"]
    assert api.delete(f"/v1/reviews/{review_id}").status_code == 204
    assert api.delete(f"/v1/reviews/{review_id}").status_code == 404
    assert review(api, request_id, "parties", "accept").status_code == 201


def test_bad_reviews_are_refused(api):
    request_id = extract(api, ["parties"])["request_id"]
    assert review(api, "no-such-id", "parties", "accept").status_code == 404
    assert review(api, request_id, "governing_law", "accept").status_code == 422  # not asked
    assert review(api, request_id, "parties", "modify").status_code == 422  # no value
