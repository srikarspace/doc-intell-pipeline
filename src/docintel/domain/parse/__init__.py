"""Parsers behind one interface. 3a2 and 3a3 add entries to PARSERS."""

from pathlib import Path

from docintel.domain.parse.base import ParsedDoc, Parser
from docintel.domain.parse.cache import cached_parse
from docintel.domain.parse.docling_parser import parse_docling
from docintel.domain.parse.pypdf_parser import parse_pypdf

PARSERS: dict[str, Parser] = {"pypdf": parse_pypdf, "docling": parse_docling}


def parse_doc(parser_name: str, doc_id: str, pdf_path: Path | str) -> ParsedDoc:
    """Parse one contract with the named parser. Uses the cache."""
    return cached_parse(parser_name, doc_id, Path(pdf_path), PARSERS[parser_name])
