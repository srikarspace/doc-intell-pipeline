"""Parser 1: copy the text that is stored inside the PDF. No model, free."""

import time
from pathlib import Path

from pypdf import PdfReader

from docintel.domain.parse.base import ParsedDoc, from_pages


def parse_pypdf(pdf_path: Path) -> ParsedDoc:
    start = time.perf_counter()
    pages = [page.extract_text() or "" for page in PdfReader(pdf_path).pages]
    latency_ms = round((time.perf_counter() - start) * 1000)
    return from_pages(pages, cost_usd=0.0, latency_ms=latency_ms, parser_name="pypdf")
