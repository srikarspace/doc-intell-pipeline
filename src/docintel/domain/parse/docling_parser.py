"""Parser 2: Docling. Local layout and OCR models, free but slow."""

import time
from functools import lru_cache
from pathlib import Path

from docintel.domain.parse.base import ParsedDoc, from_pages

DO_OCR = False  # native PDFs have a text layer; 3b turns this on for scans
DO_TABLES = False  # one contract lost a quote with tables on; 3b can test this


@lru_cache
def get_converter():
    """Build the converter once. The imports are here so that importing this file stays fast."""
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption

    options = PdfPipelineOptions(do_ocr=DO_OCR, do_table_structure=DO_TABLES)
    return DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)}
    )


def pages_of(document, n_pages: int) -> list[str]:
    """The Markdown of each page, from 1 to n_pages. A page with nothing on it is ""."""
    return [document.export_to_markdown(page_no=n) for n in range(1, n_pages + 1)]


def parse_docling(pdf_path: Path) -> ParsedDoc:
    start = time.perf_counter()
    result = get_converter().convert(pdf_path)
    pages = pages_of(result.document, result.input.page_count)
    latency_ms = round((time.perf_counter() - start) * 1000)
    return from_pages(pages, cost_usd=0.0, latency_ms=latency_ms, parser_name="docling")
