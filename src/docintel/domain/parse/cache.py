"""Disk cache: one JSON file per (parser, doc_id). A paid page is paid for only once."""

from pathlib import Path

from docintel.domain.parse.base import ParsedDoc, Parser

CACHE_DIR = Path("data/parse_cache")


def cache_path(parser_name: str, doc_id: str, cache_dir: Path = CACHE_DIR) -> Path:
    return cache_dir / parser_name / f"{doc_id}.json"


def cached_parse(
    parser_name: str, doc_id: str, pdf_path: Path, parser: Parser, cache_dir: Path = CACHE_DIR
) -> ParsedDoc:
    """The stored result if there is one. If not, parse, store, and return."""
    path = cache_path(parser_name, doc_id, cache_dir)
    if path.exists():
        return ParsedDoc.model_validate_json(path.read_text(encoding="utf-8"))
    doc = parser(pdf_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(doc.model_dump_json(), encoding="utf-8")
    temp.replace(path)  # the file appears whole, or not at all
    return doc
