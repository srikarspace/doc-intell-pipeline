"""The parser interface and the disk cache: rules that must never silently break."""

from pathlib import Path

from pypdf import PdfWriter

from docintel.domain.parse.base import ParsedDoc, from_pages
from docintel.domain.parse.cache import cached_parse
from docintel.domain.parse.pypdf_parser import parse_pypdf


class CountingParser:
    """A fake parser that counts its calls. It costs $0.25 each time."""

    def __init__(self):
        self.calls = 0

    def __call__(self, pdf_path: Path) -> ParsedDoc:
        self.calls += 1
        return from_pages(["page one", ""], cost_usd=0.25, latency_ms=900, parser_name="fake")


def test_text_is_the_pages_joined():
    doc = from_pages(["a", "", "c"], cost_usd=0.0, latency_ms=1, parser_name="fake")
    assert doc.text == "a\n\n\n\nc"
    assert len(doc.pages) == 3


def test_second_call_does_not_parse_and_keeps_the_real_cost(tmp_path):
    parser = CountingParser()
    first = cached_parse("fake", "doc-1", Path("x.pdf"), parser, tmp_path)
    second = cached_parse("fake", "doc-1", Path("x.pdf"), parser, tmp_path)
    assert parser.calls == 1
    assert second == first
    assert second.cost_usd == 0.25  # the text cost money once; a hit must not report $0


def test_two_parsers_do_not_share_a_cache_entry(tmp_path):
    parser = CountingParser()
    cached_parse("parser_a", "doc-1", Path("x.pdf"), parser, tmp_path)
    cached_parse("parser_b", "doc-1", Path("x.pdf"), parser, tmp_path)
    assert parser.calls == 2


def test_no_temp_file_is_left_behind(tmp_path):
    cached_parse("fake", "doc-1", Path("x.pdf"), CountingParser(), tmp_path)
    assert [p.name for p in (tmp_path / "fake").iterdir()] == ["doc-1.json"]


def test_pypdf_gives_one_entry_per_page(tmp_path):
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    writer.add_blank_page(width=200, height=200)
    pdf = tmp_path / "two_pages.pdf"
    writer.write(pdf)
    assert parse_pypdf(pdf).pages == ["", ""]  # a blank page keeps its place
