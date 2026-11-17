"""Highlights on real sample PDFs, and the event stream with the fakes from `conftest.py`."""

import json

from docintel.api.samples import SAMPLES_DIR
from docintel.domain import pipeline
from docintel.domain.locate import line_around, locate
from docintel.domain.parse.pypdf_parser import parse_pypdf
from docintel.domain.pipeline import TooLong

KUBIENT = SAMPLES_DIR / "kubient.pdf"
QUOTE = 'Kubient, Inc. ("Kubient")'


def events(client, fields: list[str]) -> list[tuple[str, dict]]:
    """Send a stream request, and read back (event, data) pairs."""
    data = {"sample_id": "kubient", "fields": fields}
    with client.stream("POST", "/v1/extract/stream", data=data) as response:
        text = "".join(response.iter_text())
    pairs = []
    for block in text.replace("\r\n", "\n").split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.splitlines() if ": " in line)
        if "event" in lines:
            pairs.append((lines["event"], json.loads(lines["data"])))
    return pairs


def test_a_quote_becomes_one_box_on_its_line():
    (h,) = locate(KUBIENT, [QUOTE])
    assert (h.quote_index, h.page, h.page_size) == (0, 1, (595.0, 842.0))
    assert len(h.rects) == 1  # the raised quote marks stay on the same line


def test_a_quote_on_two_lines_gets_two_boxes():
    quote = "Customer agrees not to work with, directly or indirectly, any Third-Party"
    (h,) = locate(KUBIENT, [quote])
    assert len(h.rects) == 2


def test_a_quote_that_is_not_there_gives_nothing():
    assert locate(KUBIENT, ["this sentence is not in the contract"]) == []
    assert locate(SAMPLES_DIR / "kubient-scan.pdf", [QUOTE]) == []  # a scan has no text layer


def test_a_rule_match_becomes_its_whole_line():
    pdf = SAMPLES_DIR / "ivillage.pdf"
    line = line_around(parse_pypdf(pdf).text, "renew")
    assert line.startswith("provide FMM with the opportunity to renew this Agreement")
    (h,) = locate(pdf, [line])
    assert h.page == 1


def test_events_come_in_order_and_end_with_the_result(api):
    names = [name for name, _ in events(api, ["parties"])]
    assert names == ["stage", "stage", "stage", "attempt", "stage", "result"]


def test_a_failure_ends_with_an_error_event(api, sent, monkeypatch):
    def too_long(path):
        raise TooLong("120 pages, the limit is 100")

    monkeypatch.setattr(pipeline, "parse_pdf", too_long)
    pairs = events(api, ["parties"])
    assert pairs[-1] == ("error", {"status": 413, "detail": "120 pages, the limit is 100"})
    assert sent == []  # it stopped before the paid call
