"""Parser 2: Docling. Local layout and OCR models, free but slow."""

import time
from functools import lru_cache
from pathlib import Path

from docintel.domain.parse.base import ParsedDoc, from_pages

DO_OCR = False  # native PDFs have a text layer; 3b turns this on for scans
DO_TABLES = False  # one contract lost a quote with tables on; 3b can test this


@lru_cache
def get_converter(do_ocr: bool = DO_OCR):
    """Build each converter once. The imports are here so that importing this file stays fast."""
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions, RapidOcrOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption

    options = PdfPipelineOptions(do_ocr=do_ocr, do_table_structure=DO_TABLES)
    if do_ocr:
        options.ocr_options = RapidOcrOptions(backend="torch")
    return DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)}
    )


def pages_of(document, n_pages: int) -> list[str]:
    """The Markdown of each page, from 1 to n_pages. A page with nothing on it is ""."""
    return [document.export_to_markdown(page_no=n) for n in range(1, n_pages + 1)]


def run_docling(pdf_path: Path, do_ocr: bool, parser_name: str) -> ParsedDoc:
    start = time.perf_counter()
    result = get_converter(do_ocr).convert(pdf_path)
    pages = pages_of(result.document, result.input.page_count)
    latency_ms = round((time.perf_counter() - start) * 1000)
    return from_pages(pages, cost_usd=0.0, latency_ms=latency_ms, parser_name=parser_name)


def parse_docling(pdf_path: Path) -> ParsedDoc:
    return run_docling(pdf_path, do_ocr=False, parser_name="docling")


def parse_docling_ocr(pdf_path: Path) -> ParsedDoc:
    return run_docling(pdf_path, do_ocr=True, parser_name="docling_ocr")
