"""The routes. Each one checks its input, then calls a typed function from `domain/`."""

import asyncio
import hashlib
import tempfile
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse

from docintel.api.fields import FIELD_INFO, FieldInfo
from docintel.api.samples import Sample, load_samples, sample_pdf
from docintel.api.schemas import Health
from docintel.domain.pipeline import Document, ExtractResult, NoAnswer, TooLong, run_pipeline
from docintel.domain.schema.fields import FieldName

VERSION = "0.1.0"
MAX_BYTES = 10 * 1024 * 1024  # the largest dev PDF is 0.48 MB; scans are bigger
TIMEOUT_S = 240  # 3 slow extraction calls, plus OCR on a 10-page scan
KNOWN_ERRORS = {  # error type -> HTTP status; anything else is a bug (500)
    TimeoutError: 504,
    TooLong: 413,
    NoAnswer: 502,
}


router = APIRouter()


def get_llm_client():
    """None means the real OpenRouter client. Tests replace this with a fake."""
    return None


@router.get("/health")
def health() -> Health:
    return Health(status="ok", version=VERSION)


@router.get("/v1/fields")
def list_fields() -> list[FieldInfo]:
    return FIELD_INFO


@router.get("/v1/samples")
def samples() -> list[Sample]:
    return list(load_samples().values())


@router.get("/v1/samples/{sample_id}/pdf")
def sample_file(sample_id: str) -> FileResponse:
    path = sample_pdf(sample_id)
    if path is None:
        raise HTTPException(404, f"no sample {sample_id!r}")
    return FileResponse(path, media_type="application/pdf")


def as_http(error: Exception) -> HTTPException:
    status = KNOWN_ERRORS[type(error)]
    detail = f"no answer within {TIMEOUT_S} s" if status == 504 else str(error)
    return HTTPException(status, detail)


async def read_input(pdf: UploadFile | None, sample_id: str | None) -> tuple[bytes, Document]:
    """The PDF bytes and their `Document`, from an upload or from a sample. Exactly one."""
    if (pdf is None) == (sample_id is None):
        raise HTTPException(422, "send a pdf or a sample_id, not both and not neither")
    if sample_id is not None:
        path = sample_pdf(sample_id)
        if path is None:
            raise HTTPException(404, f"no sample {sample_id!r}")
        data, filename = path.read_bytes(), path.name
    else:
        if pdf.size is not None and pdf.size > MAX_BYTES:
            raise HTTPException(413, f"the PDF is over {MAX_BYTES // (1024 * 1024)} MB")
        data, filename = await pdf.read(), pdf.filename or "upload.pdf"
    if not data.startswith(b"%PDF-"):
        raise HTTPException(415, "the file is not a PDF")
    sha = hashlib.sha256(data).hexdigest()
    return data, Document(filename=filename, sha256=sha, sample_id=sample_id)


@router.post("/v1/extract")
async def extract(
    client: Annotated[object, Depends(get_llm_client)],
    pdf: UploadFile | None = None,
    sample_id: Annotated[str | None, Form()] = None,
    fields: Annotated[list[FieldName] | None, Form()] = None,  # none: all 12
) -> ExtractResult:
    data, document = await read_input(pdf, sample_id)
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "upload.pdf"
        path.write_bytes(data)
        try:
            return await asyncio.wait_for(
                run_in_threadpool(run_pipeline, path, fields or [], document, client),
                timeout=TIMEOUT_S,
            )
        except tuple(KNOWN_ERRORS) as e:
            raise as_http(e) from None
