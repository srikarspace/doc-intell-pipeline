"""One request, start to end: parse, extract with retries, check. Typed in, typed out."""

import time
import uuid
from collections.abc import Callable
from pathlib import Path

from pydantic import BaseModel

from docintel.domain.extract.retry import extract_with_retry, final_answer
from docintel.domain.locate import Highlight, line_around, locate
from docintel.domain.parse.base import ParsedDoc
from docintel.domain.parse.docling_parser import parse_docling_ocr
from docintel.domain.parse.pypdf_parser import parse_pypdf
from docintel.domain.schema.fields import FIELDS, FieldName
from docintel.domain.validate.issues import Issue
from docintel.domain.validate.rules import check_answer

TEXT_CHARS_PER_PAGE = 200  # below this, the PDF is a scan; the thinnest dev contract has 870
MAX_PAGES = 100  # the longest dev contract has 82
MAX_SCAN_PAGES = 10  # Docling OCR reads about 7 to 12 s per page on an 8 GB Mac
EXTRACT_MAX_TOKENS = 20_000  # the largest real extraction answer used 17,999


class TooLong(ValueError):
    pass


class NoAnswer(ValueError):
    pass


class FieldResult(BaseModel):
    found: bool
    value: str | list[str] | None = None
    quotes: list[str]
    needs_review: bool
    issues: list[Issue]
    highlights: list[Highlight] = []  # where each quote is; empty for a scan
    evidence: list[str] = []  # "maybe missed": the line that holds the words the rule found
    evidence_highlights: list[Highlight] = []  # where each evidence line is


class Document(BaseModel):
    filename: str
    sha256: str  # the same file always has the same hash, so reviews can find it again
    sample_id: str | None = None


class ExtractResult(BaseModel):
    request_id: str
    document: Document
    fields: dict[str, FieldResult]
    needs_review: bool
    parser: str
    pages: int
    cost_usd: float
    latency_ms: int


def parse_pdf(pdf_path: Path) -> ParsedDoc:
    """pypdf when the PDF has a text layer. Docling OCR when it is a scan."""
    doc = parse_pypdf(pdf_path)
    if len(doc.pages) > MAX_PAGES:
        raise TooLong(f"{len(doc.pages)} pages, the limit is {MAX_PAGES}")
    if len(doc.text.strip()) >= TEXT_CHARS_PER_PAGE * len(doc.pages):
        return doc
    if len(doc.pages) > MAX_SCAN_PAGES:
        raise TooLong(f"a scan of {len(doc.pages)} pages, the limit for scans is {MAX_SCAN_PAGES}")
    return parse_docling_ocr(pdf_path)


Emit = Callable[[str, dict], None]  # (event name, data); the API turns these into SSE events


def no_events(event: str, data: dict) -> None:
    pass


def boxes(pdf_path: Path, texts: list[str], text_layer: bool) -> list[Highlight]:
    """Line boxes for each text, when the PDF has a text layer. A scan has none."""
    return locate(pdf_path, texts) if text_layer and texts else []


def run_pipeline(
    pdf_path: Path,
    fields: list[FieldName],
    document: Document,
    client=None,
    on_event: Emit = no_events,
) -> ExtractResult:
    """Parse, extract all 12 with retries, check, keep the chosen fields. Reports each step."""
    start = time.perf_counter()
    on_event("stage", {"name": "parse", "status": "start"})
    doc = parse_pdf(pdf_path)
    done = {"name": "parse", "status": "done", "parser": doc.parser_name, "pages": len(doc.pages)}
    on_event("stage", done)
    on_event("stage", {"name": "extract", "status": "start"})
    attempts = extract_with_retry(
        doc.text,
        client=client,
        max_tokens=EXTRACT_MAX_TOKENS,
        on_attempt=lambda a: on_event("attempt", {"n": a.attempt_no, "errors": len(a.errors)}),
    )
    answer = final_answer(attempts)
    if answer is None:
        raise NoAnswer("the model gave no answer that fits the schema")
    on_event("stage", {"name": "check", "status": "start"})
    issues = check_answer(answer, doc.text)  # rule errors and review warnings
    text_layer = doc.parser_name == "pypdf"
    chosen = [f for f in FIELDS if f in fields] or list(FIELDS)  # schema order, no repeats
    results = {}
    for name in chosen:
        own = [i for i in issues if i.field == name]
        part = getattr(answer, name).model_dump()
        evidence = [line_around(doc.text, i.detail) for i in own if i.rule == "maybe_missed"]
        results[name] = FieldResult(
            **part,
            needs_review=bool(own),
            issues=own,
            highlights=boxes(pdf_path, part["quotes"], text_layer),
            evidence=evidence,
            evidence_highlights=boxes(pdf_path, evidence, text_layer),
        )
    return ExtractResult(
        request_id=str(uuid.uuid4()),
        document=document,
        fields=results,
        needs_review=any(r.needs_review for r in results.values()),
        parser=doc.parser_name,
        pages=len(doc.pages),
        cost_usd=sum(a.result.cost_usd or 0.0 for a in attempts) + doc.cost_usd,
        latency_ms=round((time.perf_counter() - start) * 1000),
    )
