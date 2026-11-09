"""Fake scans and CER: the rules that must never break without a warning."""

import pytest
from pypdf import PdfReader, PdfWriter

from docintel.domain.parse.scan import make_scan, scan_pages
from docintel.evals.cer import cer, normalize


@pytest.fixture
def pdf(tmp_path):
    writer = PdfWriter()
    for _ in range(2):
        writer.add_blank_page(width=200, height=200)
    path = tmp_path / "clean.pdf"
    writer.write(path)
    return path


def pixels(pdf, seed=0, doc_id="doc-1"):
    return [im.tobytes() for im in scan_pages(pdf, doc_id, "mild", seed)]


def test_same_seed_gives_the_same_pixels(pdf):
    assert pixels(pdf) == pixels(pdf)


def test_another_seed_or_doc_gives_other_pixels(pdf):
    assert pixels(pdf) != pixels(pdf, seed=1)
    assert pixels(pdf) != pixels(pdf, doc_id="doc-2")


def test_pages_of_one_doc_differ(pdf):
    first, second = pixels(pdf)
    assert first != second


def test_a_scan_has_no_text_layer_and_keeps_its_pages(pdf, tmp_path):
    reader = PdfReader(make_scan(pdf, tmp_path / "scan.pdf", "doc-1", "mild"))
    assert len(reader.pages) == 2
    assert all(not page.extract_text() for page in reader.pages)


@pytest.mark.parametrize(
    "text, expected",
    [("abc", 0.0), ("abd", 1 / 3), ("", 1.0), ("abcabcabc", 2.0)],
)
def test_cer_known_cases(text, expected):
    assert cer(text, "abc") == pytest.approx(expected)


def test_normalize_removes_only_what_is_not_an_error():
    assert normalize("## The  Party\n**Name**") == "the party name"
    assert normalize("a b", "raw") == "a b"
    assert cer("## Name", "name") == 0.0
    assert cer("Nane", "name") == pytest.approx(0.25)
