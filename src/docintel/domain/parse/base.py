"""The one shape that every parser gives back."""

from collections.abc import Callable
from pathlib import Path

from pydantic import BaseModel, ConfigDict

PAGE_BREAK = "\n\n"


class ParsedDoc(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str  # all pages, joined with PAGE_BREAK
    pages: list[str]  # the text of each page; a blank page is ""
    cost_usd: float
    latency_ms: int
    parser_name: str


Parser = Callable[[Path], ParsedDoc]


def from_pages(pages: list[str], cost_usd: float, latency_ms: int, parser_name: str) -> ParsedDoc:
    """Build a ParsedDoc, so `text` and `pages` can never disagree."""
    return ParsedDoc(
        text=PAGE_BREAK.join(pages),
        pages=pages,
        cost_usd=cost_usd,
        latency_ms=latency_ms,
        parser_name=parser_name,
    )
