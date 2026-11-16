# Phase 4a2: the API with FastAPI

In this part, you put the whole pipeline behind HTTP routes. A user picks a sample contract or uploads a PDF, types a
request, and gets cited JSON back. Each piece is compared to Express, and each has a checkpoint.

This is part 2 of 3 for Phase 4a. It needs 4a. The paid checkpoints cost about $0.002 in total.

## Words used in this part

Read these first. Planner and plan are from 4a.

- **API**: a program that other programs call over HTTP. Example: `curl` sends a PDF, and gets JSON back.
- **Route**: one URL and method, with the function that answers it. Example: `POST /v1/extract`.
- **FastAPI**: a Python web framework. It is like Express, plus Pydantic checks on input and output.
- **uvicorn**: the server that runs a FastAPI app. In Node, `app.listen()` does this job.
- **Multipart form**: the request format for file uploads. A browser form with a file field sends it.
- **`UploadFile`**: FastAPI's object for one uploaded file. It is like `req.file` from `multer`.
- **Sample**: a contract that ships with the app, so a user can try it with no file of their own.
- **Hash (sha256)**: a short fingerprint of a file. The same file always gives the same hash.
- **Dependency**: a function that FastAPI runs before a route, and whose result it passes in. It is like Express
  middleware that puts something on `req`.
- **Status code**: the number that says how a request went. Example: 200 OK, 413 too large, 504 too slow.
- **Event loop**: the one thread that runs all `async` code. If it waits, every request waits. Same as in Node.
- **Threadpool**: a few extra threads for slow work that is not `async`. Here, the pipeline runs there.
- **TestClient**: calls the app in memory, with no server. It is like `supertest`.

## Objectives

By the end of this part you should be able to:

1. Run a FastAPI app, and say what each piece is in Express.
2. Serve sample contracts safely, and take a sample or an upload in the same route.
3. Choose a parser from the PDF itself: text layer or scan.
4. Turn each known failure into one clear status code, from one map.
5. Keep the event loop free while a 30-second pipeline runs, and test it all with fakes.

## Dependencies

New libraries (checked on PyPI and OSV before choosing: maintained, 0 open advisories):

- `fastapi`: the web framework. Like `express`.
- `uvicorn`: the server. Like Node's `http` server.
- `python-multipart`: reads file uploads. Like `multer`.

This part needs:

- 4a: `plan_request`, `pick`, `PlanError`.
- 2b: `extract_with_retry` and `final_answer`. You add two arguments.
- 2a: `check_answer`, which also runs the review rules.
- 3a, 3b2: `parse_pypdf` and `parse_docling_ocr`. 3b2's frozen `e3` set and 3b's fake scans, for the samples.

## The big picture

Before this part, the pipeline ran only from the command line, on contracts in DuckDB.

After this part:

```text
curl -F sample_id=kubient -F request="parties"  ->  POST /v1/extract
                                                       |
     route: input checks -> run_pipeline() in a thread, with a time limit
                                                       |
     parse (pypdf or Docling OCR) -> plan -> extract + retries -> check -> pick -> JSON
```

- **4a3** adds highlights and a live event stream for the UI.
- **4c** builds the UI on these routes. It shows the samples as a list to pick from.

## Remember this

> The route is thin. It checks the input, calls one typed function, and turns each known failure into a clear
> status code. The pipeline knows nothing about HTTP, so the API, the eval runner and later an agent can all call it.
>
> **Thin route, typed pipeline, one status per failure.**

## Why

**A product needs an address.** A user cannot run `python -m`. They send a PDF, or pick a sample, at a URL.

**Samples make the demo work for anyone.** A person who clones the repo has no contract at hand. The 10 samples come
from your own `e3` set, so you already know how the pipeline does on them.

**A slow request must not block the others.** One extraction takes 13.6 s at the median, and up to 90 s.

## Design decisions

- **The pipeline is one function in `domain/`, typed in and out.** The route only checks HTTP things. Other option: put
  the steps in the route. The eval runner and 4b could not reuse them.
- **Parse first, then plan.** A file we cannot read (too many pages) is refused before the paid plan call, and the
  UI can show "parse" as the first step. Other option: plan first. A request with only unknown fields would fail a
  little sooner.
- **The PDF chooses its parser.** Text layer: pypdf. Scan: Docling OCR. The test is at least 200 characters per page.
  The thinnest dev contract has 870, and a fake scan has 0. Other option: let the user choose.
- **Samples are files in the package, with a manifest.** The id must be in `samples.json` before any path is built.
  Other option: build the path from the id. `../../.env` could then become a "sample".
- **One route takes a sample or an upload.** Both become bytes and a `Document`, then the same pipeline. Other option:
  two routes. Two copies of the same checks.
- **Every answer carries its `Document`, with a sha256.** 4b stores reviews against it. The same file gives the same
  hash, even with another name. Other option: the file name. Two contracts can share a name.
- **One map from error type to status code.** 4a3's stream route reuses it. Other option: an
  `except` per error in each route. They would drift apart.
- **The model client is a dependency.** A test can swap in a fake, with no network.

## Worked example

All outputs are real. Guess before you open each box.

### Round 1: what if the route is `async` and calls the pipeline directly?

`async def extract(...)` then `return run_pipeline(...)`, with no thread. Guess what happens to a second user during a
30-second request.

<details><summary>Guess, then open</summary>

They wait the whole 30 seconds. `run_pipeline` is normal code, so it holds the event loop until it ends. It is the
same as a `while` loop inside an Express handler. Break 1 shows the test that catches it.
</details>

### Round 2: is the same request always the same answer?

The same Kubient contract, the same request, sent twice. The first answer said `non_compete` was found, with a quote.
Guess the second.

<details><summary>Guess, then open</summary>

```text
{'parties': (True, False, []), 'non_compete': (False, False, []), 'renewal_term': (False, True, ['maybe_missed'])}
```

`non_compete` is now **not found**. The temperature is 0, and the answer still changed. The clause says "Customer agrees
not to work with ... any Third-Party". Even the model is unsure. That is why each field has `needs_review`.
</details>

## Project setup

```sh
uv add fastapi uvicorn python-multipart
mkdir -p src/docintel/api/samples
touch src/docintel/api/__init__.py src/docintel/api/app.py src/docintel/api/routes.py
touch src/docintel/api/schemas.py src/docintel/api/samples.py
touch src/docintel/domain/pipeline.py
touch tests/conftest.py tests/test_api.py
```

Add one target to the `Makefile`:

```make
serve:  ## run the API on http://localhost:8000
	uv run uvicorn docintel.api.app:app --reload
```

You should now have:

```text
src/docintel/
├── api/
│   ├── __init__.py
│   ├── app.py          # new: the app
│   ├── routes.py       # new: health, samples, extract
│   ├── samples.py      # new: read the sample list
│   ├── samples/        # new: 10 PDFs + samples.json (Step 5)
│   └── schemas.py      # new: the health answer
└── domain/
    └── pipeline.py     # new: one request, start to end
tests/
├── conftest.py         # new: shared fakes
└── test_api.py         # new
```

## Step 1: two new arguments for the retry loop

**Why.** The API needs a fake client in tests, and a token limit in production.

In `src/docintel/domain/extract/retry.py`, add two arguments to `extract_with_retry`, after `max_retries`:

```python
    client=None,
    max_tokens: int | None = None,
```

And pass them on, in the same function:

```python
        result = call_llm(
            messages, ContractFields, model=model, client=client, max_tokens=max_tokens
        )
```

Both default to "as before", so every eval run stays the same.

Your 2b test has a fake `call_llm`. It must accept the new arguments. In `tests/test_retry.py`, change the line
`def call(messages, schema, *, model=None):` to:

```python
    def call(messages, schema, *, model=None, client=None, max_tokens=None):
```

Checkpoint:

```sh
uv run pytest tests/test_retry.py -q
```

```text
.....                                                                    [100%]
5 passed in 0.04s
```

Without the test change, all 5 fail with `unexpected keyword argument 'client'`. A fake must follow the real signature.

## Step 2: routing and limits (your decision)

**Why.** These numbers decide what the API refuses, and how long a user may wait.

| Choice | Evidence |
|---|---|
| Text layer or scan | thinnest dev contract: 870 characters per page. Fake scans: 0 |
| Parser for a scan | E3: Docling OCR is free, F1 0.89 on mild scans. Vision only won on heavy ones |
| Most pages | longest dev contract: 82 pages |
| Most pages for a scan | Docling OCR: about 7 to 12 s per page on an 8 GB Mac |
| Largest file | largest dev PDF: 0.48 MB. A 2-page fake scan: 0.68 MB |
| Longest request | 4a requests are under 70 characters |
| Time limit | extraction: 13.6 s median, 36 s p95, 90 s max, per call; up to 3 calls with retries |
| Extraction token limit | largest real answer: 17,999 tokens. p99: about 6,000 |

Write your values in `EXPERIMENTS.md`, under a new `## API limits (4a2)` heading.

<details><summary>Reference (open after you write yours)</summary>

- Scan if under 200 characters per page. Scans go to Docling OCR. No vision yet.
- Most pages: 100. For a scan: 10. Largest file: 10 MB. Longest request: 500 characters.
- Time limit: 240 s. Enough for 3 slow extraction calls, plus OCR on a 10-page scan.
- Extraction token limit: 20,000, above the largest real answer.
</details>

## Step 3: the pipeline types and the parser choice

**Why.** The answer needs a fixed shape, and the PDF must find its parser.

<details><summary>Put the imports at the top of <code>src/docintel/domain/pipeline.py</code></summary>

```python
"""One request, start to end: plan, parse, extract with retries, check. Typed in, typed out."""

import time
import uuid
from pathlib import Path

from pydantic import BaseModel

from docintel.domain.extract.retry import extract_with_retry, final_answer
from docintel.domain.parse.base import ParsedDoc
from docintel.domain.parse.docling_parser import parse_docling_ocr
from docintel.domain.parse.pypdf_parser import parse_pypdf
from docintel.domain.planner.planner import pick, plan_request
from docintel.domain.validate.issues import Issue
from docintel.domain.validate.rules import check_answer
```
</details>

Add below the imports in `src/docintel/domain/pipeline.py`:

```python
TEXT_CHARS_PER_PAGE = 200  # below this, the PDF is a scan; the thinnest dev contract has 870
MAX_PAGES = 100  # the longest dev contract has 82
MAX_SCAN_PAGES = 10  # Docling OCR reads about 7 to 10 s per page on an 8 GB Mac
EXTRACT_MAX_TOKENS = 20_000  # the largest real extraction answer used 17,999


class TooLong(ValueError):
    pass


class NothingToExtract(ValueError):
    pass


class FieldResult(BaseModel):
    found: bool
    value: str | list[str] | None = None
    quotes: list[str]
    needs_review: bool
    issues: list[Issue]


class Document(BaseModel):
    filename: str
    sha256: str  # the same file always has the same hash, so reviews can find it again
    sample_id: str | None = None


class ExtractResult(BaseModel):
    request_id: str
    document: Document
    fields: dict[str, FieldResult]
    unknown: list[str]
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
```

Here, in `parse_pdf`, in order:

1. Read the text layer with pypdf. It is fast and free, so it always runs first.
2. Refuse a document that is too long.
3. If there is enough text, use it.
4. If not, it is a scan. Refuse a long scan, or read it with Docling OCR.

The checkpoint for this step comes after Step 5, when the samples exist.

## Step 4: the pipeline

**Why.** This is the one function that the API calls.

Add to the bottom of `src/docintel/domain/pipeline.py`:

```python
def run_pipeline(pdf_path: Path, request: str, document: Document, client=None) -> ExtractResult:
    """Parse, plan, extract with retries, check, and keep only the requested fields."""
    start = time.perf_counter()
    doc = parse_pdf(pdf_path)
    plan, plan_call = plan_request(request, client=client)
    if not plan.fields:
        raise NothingToExtract(f"no known field in the request; unknown: {plan.unknown}")
    attempts = extract_with_retry(doc.text, client=client, max_tokens=EXTRACT_MAX_TOKENS)
    answer = final_answer(attempts)
    if answer is None:
        raise ValueError("the model gave no answer that fits the schema")
    issues = check_answer(answer, doc.text)  # rule errors and review warnings
    picked = pick(answer, plan.fields)
    fields = {}
    for name in plan.fields:
        own = [i for i in issues if i.field == name]
        answer_part = getattr(picked, name).model_dump()
        fields[name] = FieldResult(**answer_part, needs_review=bool(own), issues=own)
    costs = [a.result.cost_usd for a in attempts] + [plan_call.cost_usd if plan_call else 0.0]
    return ExtractResult(
        request_id=str(uuid.uuid4()),
        document=document,
        fields=fields,
        unknown=plan.unknown,
        needs_review=any(f.needs_review for f in fields.values()),
        parser=doc.parser_name,
        pages=len(doc.pages),
        cost_usd=sum(c or 0.0 for c in costs) + doc.cost_usd,
        latency_ms=round((time.perf_counter() - start) * 1000),
    )
```

Here, in order:

1. Parse the PDF.
2. Plan the request. If no known field is asked, stop before the expensive call.
3. Extract all 12 fields, with retries and the token limit.
4. Check the answer: rule errors and review warnings.
5. Keep only the asked fields, each with its own issues.
6. Add up the cost of every call, and the time.

`check_answer` already runs the review rules from 2a2. Do not call `review_answer` too, or every warning comes twice.

## Step 5: the samples

**Why.** Anyone who runs the app can try it at once, on contracts with known results.

Run this once. It copies the 9 `e3` dev contracts and the Kubient mild fake scan into the package, and writes a
manifest. It is boilerplate, so copy it:

<details><summary>Command: build <code>src/docintel/api/samples/</code></summary>

```sh
uv run python - <<'EOF'
"""One-off: copy the E3 dev contracts and one fake scan into the app, with a small manifest."""

import json
import shutil
from pathlib import Path

from docintel.evals.store import connect

OUT = Path("src/docintel/api/samples")
TITLES = {  # doc_id start -> (id, title)
    "KUBIENT": ("kubient", "Kubient: master services agreement"),
    "EcoScience": ("ecoscience", "EcoScience: sponsorship agreement"),
    "VIVINT": ("vivint", "Vivint Solar: non-competition agreement"),
    "IVILLAGE": ("ivillage", "iVillage: sponsorship agreement"),
    "IntegrityFunds": ("integrity-funds", "Integrity Funds: underwriting contract"),
    "VARIABLESEPARATEACCOUNT": ("variable-account", "Variable Separate Account: capital maintenance"),
    "Euromedia": ("euromedia", "Euromedia: license agreement"),
    "BORROWMONEY": ("borrowmoney", "BorrowMoney.com: joint venture agreement"),
    "ElPolloLoco": ("el-pollo-loco", "El Pollo Loco: development agreement"),
}

with connect() as con:
    rows = con.execute(
        "SELECT doc_id, contract_type, n_pages, pdf_path FROM eval_sets JOIN contracts USING (doc_id) "
        "WHERE set_name = 'e3' ORDER BY n_pages, doc_id"
    ).fetchall()
OUT.mkdir(parents=True, exist_ok=True)
samples = []
for doc_id, contract_type, n_pages, pdf_path in rows:
    sample_id, title = next(v for k, v in TITLES.items() if doc_id.startswith(k))
    shutil.copy(pdf_path, OUT / f"{sample_id}.pdf")
    samples.append({"id": sample_id, "title": title, "contract_type": contract_type,
                    "pages": n_pages, "scan": False, "doc_id": doc_id})
kubient = samples[0]
shutil.copy(f"data/scans/mild/{kubient['doc_id']}.pdf", OUT / "kubient-scan.pdf")
samples.append(kubient | {"id": "kubient-scan", "title": kubient["title"] + " (scan)", "scan": True})
(OUT / "samples.json").write_text(json.dumps(samples, indent=2) + "\n", encoding="utf-8")
print(len(samples), "samples in", OUT)
EOF
```
</details>

```text
10 samples in src/docintel/api/samples
```

CUAD is licensed CC BY 4.0, so you may ship these PDFs. Credit CUAD in the README. They are dev contracts only.

Put this in `src/docintel/api/samples.py`:

```python
"""The sample contracts that ship with the app: CUAD dev PDFs (CC BY 4.0) and one fake scan."""

import json
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel

SAMPLES_DIR = Path(__file__).parent / "samples"


class Sample(BaseModel):
    id: str
    title: str
    contract_type: str
    pages: int
    scan: bool
    doc_id: str  # the CUAD id, so a result can be traced back to its labels


@lru_cache
def load_samples() -> dict[str, Sample]:
    rows = json.loads((SAMPLES_DIR / "samples.json").read_text(encoding="utf-8"))
    return {row["id"]: Sample(**row) for row in rows}


def sample_pdf(sample_id: str) -> Path | None:
    """The PDF of one sample, or None if there is no such sample."""
    if sample_id not in load_samples():  # never build a path from an unknown id
        return None
    return SAMPLES_DIR / f"{sample_id}.pdf"
```

*Python here: [`lru_cache` for a file read once](./py/phase-4a2.md#py-1).*

Here, `sample_pdf` checks the id against the manifest before it builds a path. Only those 10 files can ever be read.

Checkpoint (free): the parser choice on a sample and on its scan.

```sh
uv run python - <<'EOF'
from pathlib import Path

from docintel.domain.pipeline import parse_pdf

for name in ("kubient.pdf", "kubient-scan.pdf"):
    doc = parse_pdf(Path("src/docintel/api/samples") / name)
    print(f"src/.../{name}", doc.parser_name, len(doc.pages), "pages", len(doc.text), "chars", round(doc.latency_ms / 1000, 1), "s")
EOF
```

```text
src/.../kubient.pdf pypdf 2 pages 7590 chars 0.0 s
src/.../kubient-scan.pdf docling_ocr 2 pages 8083 chars 23.7 s
```

Docling also prints model warnings. You can ignore them.

## Step 6: the app, health and samples

**Why.** A server must answer "are you alive?", and the UI needs the sample list.

Put this in `src/docintel/api/schemas.py`:

```python
"""Shapes of the API's own answers. The extraction answer is `ExtractResult` from the pipeline."""

from pydantic import BaseModel


class Health(BaseModel):
    status: str
    version: str
```

<details><summary>Put the imports at the top of <code>src/docintel/api/routes.py</code></summary>

```python
"""The routes. Each one checks its input, then calls a typed function from `domain/`."""

import asyncio
import hashlib
import tempfile
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse

from docintel.api.samples import Sample, load_samples, sample_pdf
from docintel.api.schemas import Health
from docintel.domain.pipeline import (
    Document,
    ExtractResult,
    NothingToExtract,
    TooLong,
    run_pipeline,
)
from docintel.domain.planner.planner import PlanError
```
</details>

Add below the imports in `src/docintel/api/routes.py`:

```python
VERSION = "0.1.0"
MAX_BYTES = 10 * 1024 * 1024  # the largest dev PDF is 0.48 MB; scans are bigger
MAX_REQUEST_CHARS = 500
TIMEOUT_S = 240  # 3 slow extraction calls, plus OCR on a 10-page scan


router = APIRouter()


def get_llm_client():
    """None means the real OpenRouter client. Tests replace this with a fake."""
    return None


@router.get("/health")
def health() -> Health:
    return Health(status="ok", version=VERSION)


@router.get("/v1/samples")
def samples() -> list[Sample]:
    return list(load_samples().values())


@router.get("/v1/samples/{sample_id}/pdf")
def sample_file(sample_id: str) -> FileResponse:
    path = sample_pdf(sample_id)
    if path is None:
        raise HTTPException(404, f"no sample {sample_id!r}")
    return FileResponse(path, media_type="application/pdf")
```

Put this in `src/docintel/api/app.py`:

```python
"""The FastAPI app. Run it with: uv run uvicorn docintel.api.app:app"""

from fastapi import FastAPI

from docintel.api.routes import VERSION, router

app = FastAPI(title="docintel", version=VERSION)
app.include_router(router)
```

*Python here: [decorators for routes](./py/phase-4a2.md#py-2).*

Here, side by side with Express:

| FastAPI | Express |
|---|---|
| `router = APIRouter()` | `const router = express.Router()` |
| `@router.get("/health")` | `router.get("/health", handler)` |
| `-> list[Sample]` return type | `res.json(...)`, plus a shape check |
| `FileResponse(path)` | `res.sendFile(path)` |
| `app.include_router(router)` | `app.use(router)` |
| `uvicorn docintel.api.app:app` | `app.listen(8000)` |

Checkpoint. Start the server in one terminal:

```sh
make serve
```

In a second terminal:

```sh
curl -s localhost:8000/health; echo
curl -s localhost:8000/v1/samples | python -c "import json,sys; d=json.load(sys.stdin); print(len(d), 'samples'); [print(s['id'], '|', s['title'], '|', s['pages'], 'pages') for s in d[:3]]"
curl -s -o /dev/null -w "%{http_code} %{content_type} %{size_download} bytes\n" localhost:8000/v1/samples/kubient/pdf
curl -s -w " %{http_code}\n" localhost:8000/v1/samples/nope/pdf
```

```text
{"status":"ok","version":"0.1.0"}
10 samples
kubient | Kubient: master services agreement | 2 pages
ecoscience | EcoScience: sponsorship agreement | 3 pages
vivint | Vivint Solar: non-competition agreement | 4 pages
200 application/pdf 117795 bytes
{"detail":"no sample 'nope'"} 404
```

Open `http://localhost:8000/docs` in a browser too. FastAPI builds this page from your types.

## Step 7: the extract route

**Why.** This is the product: a contract and a request in, cited JSON out.

In `src/docintel/api/routes.py`, add the error map below `TIMEOUT_S`:

```python
KNOWN_ERRORS = {  # error type -> HTTP status; anything else is a bug (500)
    TimeoutError: 504,
    TooLong: 413,
    NothingToExtract: 422,
    PlanError: 502,
}
```

Then add to the bottom of the same file:

```python
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
    request: Annotated[str, Form()] = "",
) -> ExtractResult:
    if len(request) > MAX_REQUEST_CHARS:
        raise HTTPException(422, f"the request is over {MAX_REQUEST_CHARS} characters")
    data, document = await read_input(pdf, sample_id)
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "upload.pdf"
        path.write_bytes(data)
        try:
            return await asyncio.wait_for(
                run_in_threadpool(run_pipeline, path, request, document, client),
                timeout=TIMEOUT_S,
            )
        except tuple(KNOWN_ERRORS) as e:
            raise as_http(e) from None
```

*Python here: [`Annotated`, `Form` and `Depends`](./py/phase-4a2.md#py-3) · [`await`, threads and `wait_for`](./py/phase-4a2.md#py-4) · [`except tuple(...)`](./py/phase-4a2.md#py-5).*

Here, in order:

1. Refuse a request that is too long (422).
2. `read_input`: take exactly one of `pdf` or `sample_id`. Refuse an unknown sample (404), a large file (413), or a
   file that does not start like a PDF (415). Hash the bytes into a `Document`.
3. Save the bytes to a temporary folder, which is deleted afterwards.
4. Run the pipeline in a thread, with a time limit.
5. Turn any known error into its status code, through `KNOWN_ERRORS`:

| Error | Status | Means |
|---|---|---|
| `TimeoutError` | 504 | too slow |
| `TooLong` | 413 | too many pages |
| `NothingToExtract` | 422 | no known field was asked |
| `PlanError` | 502 | the planner model gave a bad answer |

Any other error gives 500. That is a bug to look at, not a user mistake.

The server restarts by itself when you save. Checkpoint 1 (free): bad inputs.

```sh
echo hello > hello.txt
cp src/docintel/api/samples/kubient.pdf data/kubient.pdf
curl -s -w " %{http_code}\n" -F pdf=@hello.txt -F request=parties localhost:8000/v1/extract
curl -s -w " %{http_code}\n" -F pdf=@data/kubient.pdf -F sample_id=kubient -F request=parties localhost:8000/v1/extract
```

```text
{"detail":"the file is not a PDF"} 415
{"detail":"send a pdf or a sample_id, not both and not neither"} 422
```

Checkpoint 2 (paid, about $0.001): a sample.

```sh
curl -s -F sample_id=kubient -F request="Who are the parties?" localhost:8000/v1/extract | python -m json.tool
```

In short: `parties` found with two names and no issue, `document` with the sample id and the file's sha256, parser
`pypdf`, $0.00085, 11.6 s.

<details><summary>The real output (open)</summary>

```text
{
    "request_id": "5e333e31-07a7-4112-8067-27a558d928cd",
    "document": {
        "filename": "kubient.pdf",
        "sha256": "e73f886d87570c89ca74b156eb6e9e0a00f0bc538898e603e6104896de33933c",
        "sample_id": "kubient"
    },
    "fields": {
        "parties": {
            "found": true,
            "value": ["Kubient, Inc.", "The Associated Press"],
            "quotes": ["Kubient, Inc. (\"Kubient\")", "The Associated Press (\"Customer\")"],
            "needs_review": false,
            "issues": []
        }
    },
    "unknown": [],
    "needs_review": false,
    "parser": "pypdf",
    "pages": 2,
    "cost_usd": 0.00085106,
    "latency_ms": 11626
}
```
</details>

The lists are shortened to one line here. An upload works the same way: `-F pdf=@data/kubient.pdf` instead of
`-F sample_id=kubient`. The hash is the same, because it is the same file.

## Step 8: a small test

**Why.** The route has many ways to answer. Each one must keep working, with no network and no cost.

The shared fakes go in `tests/conftest.py`, so 4a3 can use them too. pytest loads this file by itself.

<details><summary>Put this in <code>tests/conftest.py</code></summary>

```python
"""Shared fakes for the API tests: a fake OpenRouter and a fake parser. No network, no cost."""

import json

import httpx2
import pytest
from fastapi.testclient import TestClient
from openai import OpenAI

from docintel.api import routes
from docintel.api.app import app
from docintel.core.config import get_settings
from docintel.domain import pipeline
from docintel.domain.parse.base import from_pages
from docintel.domain.schema.fields import ContractFields
from docintel.evals.runner import empty_answer

CONTRACT = "This Agreement is made between Acme Inc. and Beta LLC."


def contract_answer() -> dict:
    answer = {f: empty_answer(f) for f in ContractFields.model_fields}
    names = ["Acme Inc.", "Beta LLC"]
    answer["parties"] = {"quotes": names, "value": names, "found": True}
    return answer


def fake_llm(plan: dict, sent: list) -> OpenAI:
    """Answers a planner call with `plan`, and an extraction call with `contract_answer()`."""

    def handler(request: httpx2.Request) -> httpx2.Response:
        schema = json.loads(request.content)["response_format"]["json_schema"]["name"]
        sent.append(schema)
        content = plan if schema == "Plan" else contract_answer()
        message = {"role": "assistant", "content": json.dumps(content)}
        body = {
            "id": "gen-1",
            "object": "chat.completion",
            "created": 0,
            "model": "fake/model",
            "choices": [{"index": 0, "finish_reason": "stop", "message": message}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "cost": 0.001},
        }
        return httpx2.Response(200, json=body)

    http = httpx2.Client(transport=httpx2.MockTransport(handler))
    return OpenAI(
        api_key="sk-or-v1-test", base_url="https://fake.test/v1", max_retries=0, http_client=http
    )


@pytest.fixture
def api(monkeypatch):
    """`api(plan)`: a TestClient whose model answers with `plan`. `api.sent` lists the calls."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-test")
    get_settings.cache_clear()
    monkeypatch.setattr(pipeline, "parse_pdf", lambda path: from_pages([CONTRACT], 0.0, 1, "pypdf"))
    sent = []

    def use(plan: dict) -> TestClient:
        app.dependency_overrides[routes.get_llm_client] = lambda: fake_llm(plan, sent)
        return TestClient(app)

    use.sent = sent
    yield use
    app.dependency_overrides.clear()
    get_settings.cache_clear()
```
</details>

*Python here: [`conftest.py` and a fixture that returns a function](./py/phase-4a2.md#py-6).*

The test names say what is protected: health answers, only the asked fields come back, a request with no known field
makes no extraction call, bad, large, long and slow requests are refused, samples are listed and served, an unknown
sample is 404, a sample can be extracted, and a PDF with a sample together is refused.

<details><summary>Put this in <code>tests/test_api.py</code></summary>

```python
"""The API routes, with the fakes from `conftest.py`."""

import time

import pytest

from docintel.api import routes

PDF = b"%PDF-1.4 fake"
PLAN = {"fields": ["parties"], "unknown": []}


def post(client, request: str, data: bytes = PDF):
    return client.post("/v1/extract", files={"pdf": ("c.pdf", data)}, data={"request": request})


def test_health(api):
    assert api({}).get("/health").json() == {"status": "ok", "version": routes.VERSION}


def test_only_the_requested_fields_come_back(api):
    client = api({"fields": ["parties"], "unknown": ["payment terms"]})
    response = post(client, "parties and payment terms")
    body = response.json()
    assert response.status_code == 200
    assert list(body["fields"]) == ["parties"]
    assert body["fields"]["parties"]["value"] == ["Acme Inc.", "Beta LLC"]
    assert body["unknown"] == ["payment terms"]
    assert body["cost_usd"] == pytest.approx(0.002)  # one plan call and one extraction call


def test_a_request_with_no_known_field_is_refused(api):
    response = post(api({"fields": [], "unknown": ["payment terms"]}), "payment terms")
    assert response.status_code == 422
    assert api.sent == ["Plan"]  # no extraction call was made


def test_a_file_that_is_not_a_pdf_is_refused(api):
    assert post(api({}), "parties", data=b"hello").status_code == 415


def test_a_large_file_is_refused(api, monkeypatch):
    monkeypatch.setattr(routes, "MAX_BYTES", 5)
    assert post(api({}), "parties").status_code == 413


def test_a_long_request_is_refused(api):
    assert post(api({}), "x" * (routes.MAX_REQUEST_CHARS + 1)).status_code == 422


def test_a_slow_request_times_out(api, monkeypatch):
    monkeypatch.setattr(routes, "TIMEOUT_S", 0.05)
    monkeypatch.setattr(routes, "run_pipeline", lambda *args: time.sleep(0.5))
    assert post(api({}), "parties").status_code == 504


def test_samples_are_listed_and_served(api):
    client = api({})
    samples = client.get("/v1/samples").json()
    assert len(samples) == 10
    assert sum(s["scan"] for s in samples) == 1
    pdf = client.get(f"/v1/samples/{samples[0]['id']}/pdf")
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.content.startswith(b"%PDF-")


def test_an_unknown_sample_is_404(api):
    client = api({})
    assert client.get("/v1/samples/../../.env/pdf").status_code == 404
    response = client.post("/v1/extract", data={"sample_id": "nope", "request": "parties"})
    assert response.status_code == 404


def test_a_sample_can_be_extracted(api):
    response = api(PLAN).post("/v1/extract", data={"sample_id": "kubient", "request": "parties"})
    assert response.status_code == 200
    assert response.json()["document"]["sample_id"] == "kubient"


def test_a_pdf_and_a_sample_together_are_refused(api):
    response = api({}).post(
        "/v1/extract", files={"pdf": ("c.pdf", PDF)}, data={"sample_id": "kubient"}
    )
    assert response.status_code == 422
```
</details>

Checkpoint:

```sh
uv run pytest tests/test_api.py -q
make test
make lint
```

```text
...........                                                              [100%]
11 passed in 0.16s
```

Your project structure should now look like this:

```text
src/docintel/
├── api/
│   ├── app.py
│   ├── routes.py        # health, samples, extract, KNOWN_ERRORS
│   ├── samples.py       # Sample, load_samples, sample_pdf
│   ├── samples/         # 10 PDFs + samples.json
│   └── schemas.py       # Health
└── domain/
    ├── extract/retry.py # + client, max_tokens
    └── pipeline.py      # parse_pdf, run_pipeline, Document, ExtractResult
tests/
├── conftest.py          # fake model, fake parser, api fixture
├── test_api.py
└── test_retry.py        # fake accepts the new arguments
```

<details><summary>Complete <code>src/docintel/domain/pipeline.py</code></summary>

```python
"""One request, start to end: plan, parse, extract with retries, check. Typed in, typed out."""

import time
import uuid
from pathlib import Path

from pydantic import BaseModel

from docintel.domain.extract.retry import extract_with_retry, final_answer
from docintel.domain.parse.base import ParsedDoc
from docintel.domain.parse.docling_parser import parse_docling_ocr
from docintel.domain.parse.pypdf_parser import parse_pypdf
from docintel.domain.planner.planner import pick, plan_request
from docintel.domain.validate.issues import Issue
from docintel.domain.validate.rules import check_answer

TEXT_CHARS_PER_PAGE = 200  # below this, the PDF is a scan; the thinnest dev contract has 870
MAX_PAGES = 100  # the longest dev contract has 82
MAX_SCAN_PAGES = 10  # Docling OCR reads about 7 to 10 s per page on an 8 GB Mac
EXTRACT_MAX_TOKENS = 20_000  # the largest real extraction answer used 17,999


class TooLong(ValueError):
    pass


class NothingToExtract(ValueError):
    pass


class FieldResult(BaseModel):
    found: bool
    value: str | list[str] | None = None
    quotes: list[str]
    needs_review: bool
    issues: list[Issue]


class Document(BaseModel):
    filename: str
    sha256: str  # the same file always has the same hash, so reviews can find it again
    sample_id: str | None = None


class ExtractResult(BaseModel):
    request_id: str
    document: Document
    fields: dict[str, FieldResult]
    unknown: list[str]
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


def run_pipeline(pdf_path: Path, request: str, document: Document, client=None) -> ExtractResult:
    """Parse, plan, extract with retries, check, and keep only the requested fields."""
    start = time.perf_counter()
    doc = parse_pdf(pdf_path)
    plan, plan_call = plan_request(request, client=client)
    if not plan.fields:
        raise NothingToExtract(f"no known field in the request; unknown: {plan.unknown}")
    attempts = extract_with_retry(doc.text, client=client, max_tokens=EXTRACT_MAX_TOKENS)
    answer = final_answer(attempts)
    if answer is None:
        raise ValueError("the model gave no answer that fits the schema")
    issues = check_answer(answer, doc.text)  # rule errors and review warnings
    picked = pick(answer, plan.fields)
    fields = {}
    for name in plan.fields:
        own = [i for i in issues if i.field == name]
        answer_part = getattr(picked, name).model_dump()
        fields[name] = FieldResult(**answer_part, needs_review=bool(own), issues=own)
    costs = [a.result.cost_usd for a in attempts] + [plan_call.cost_usd if plan_call else 0.0]
    return ExtractResult(
        request_id=str(uuid.uuid4()),
        document=document,
        fields=fields,
        unknown=plan.unknown,
        needs_review=any(f.needs_review for f in fields.values()),
        parser=doc.parser_name,
        pages=len(doc.pages),
        cost_usd=sum(c or 0.0 for c in costs) + doc.cost_usd,
        latency_ms=round((time.perf_counter() - start) * 1000),
    )
```
</details>

<details><summary>Complete <code>src/docintel/api/routes.py</code></summary>

```python
"""The routes. Each one checks its input, then calls a typed function from `domain/`."""

import asyncio
import hashlib
import tempfile
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse

from docintel.api.samples import Sample, load_samples, sample_pdf
from docintel.api.schemas import Health
from docintel.domain.pipeline import (
    Document,
    ExtractResult,
    NothingToExtract,
    TooLong,
    run_pipeline,
)
from docintel.domain.planner.planner import PlanError

VERSION = "0.1.0"
MAX_BYTES = 10 * 1024 * 1024  # the largest dev PDF is 0.48 MB; scans are bigger
MAX_REQUEST_CHARS = 500
TIMEOUT_S = 240  # 3 slow extraction calls, plus OCR on a 10-page scan
KNOWN_ERRORS = {  # error type -> HTTP status; anything else is a bug (500)
    TimeoutError: 504,
    TooLong: 413,
    NothingToExtract: 422,
    PlanError: 502,
}

router = APIRouter()


def get_llm_client():
    """None means the real OpenRouter client. Tests replace this with a fake."""
    return None


def as_http(error: Exception) -> HTTPException:
    status = KNOWN_ERRORS[type(error)]
    detail = f"no answer within {TIMEOUT_S} s" if status == 504 else str(error)
    return HTTPException(status, detail)


@router.get("/health")
def health() -> Health:
    return Health(status="ok", version=VERSION)


@router.get("/v1/samples")
def samples() -> list[Sample]:
    return list(load_samples().values())


@router.get("/v1/samples/{sample_id}/pdf")
def sample_file(sample_id: str) -> FileResponse:
    path = sample_pdf(sample_id)
    if path is None:
        raise HTTPException(404, f"no sample {sample_id!r}")
    return FileResponse(path, media_type="application/pdf")


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
    request: Annotated[str, Form()] = "",
) -> ExtractResult:
    if len(request) > MAX_REQUEST_CHARS:
        raise HTTPException(422, f"the request is over {MAX_REQUEST_CHARS} characters")
    data, document = await read_input(pdf, sample_id)
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "upload.pdf"
        path.write_bytes(data)
        try:
            return await asyncio.wait_for(
                run_in_threadpool(run_pipeline, path, request, document, client),
                timeout=TIMEOUT_S,
            )
        except tuple(KNOWN_ERRORS) as e:
            raise as_http(e) from None
```
</details>

## Break it on purpose

Both breaks are free. Put the code back after each one.

**Break 1: no thread.** In `extract`, replace the whole `return await asyncio.wait_for(...)` with
`return run_pipeline(path, request, document, client)`. Guess: which test fails?

<details><summary>What you see</summary>

```text
FAILED tests/test_api.py::test_a_slow_request_times_out - fastapi.excep...
1 failed, 10 passed
```

The slow fake ran to the end, and nothing stopped it. In production, every other user would wait too (Round 1).
</details>

**Break 2: trust the sample id.** In `sample_pdf`, delete the two lines of the `if sample_id not in load_samples()`
check. Guess: which test fails, and why does it matter?

<details><summary>What you see</summary>

```text
FAILED tests/test_api.py::test_an_unknown_sample_is_404 - FileNotFoundE...
1 failed, 10 passed
```

An unknown id now becomes a path, and the server tries to read it. Here it crashes. With a crafted id, it could read a
file you never meant to share. Always check the id against a list first.
</details>

## Experiment

This part runs no experiment. It adds no eval number. The checkpoints are single requests. Write your Step 2 limits in
`EXPERIMENTS.md`, because 4c and the README use them.

## Gotchas

- **Commas in file names break `curl -F`.** Many CUAD names have commas. Use a sample, or copy the file to a
  simple name first.
- **A timed-out request still runs.** `wait_for` stops waiting, but the thread finishes, and its calls are paid.
- **Docling OCR loads its models on the first scan.** The first scan is slower than the next ones.
- **The same request can give a different answer** (Round 2). That is what `needs_review` is for.
- **The API logs nothing to DuckDB yet.** `call_llm` gets no `con` here. 4b adds a request log.

## Explain back, then commit

Explain to Claude in a few sentences:

- `retry.py`: the two new arguments, and why the defaults keep E1 to E3 the same.
- `pipeline.py`: the order of the steps, how a PDF chooses its parser, and why parsing comes first.
- `samples.py`: why the id is checked before a path is built.
- `routes.py`: `read_input`, each status code, and why there is one error map.
- Why the pipeline runs in a thread. What happens to a request that times out.
- Each line of the Express table, from memory.

Then:

```sh
git status
git add pyproject.toml uv.lock Makefile src/docintel/api src/docintel/domain/pipeline.py src/docintel/domain/extract/retry.py tests/conftest.py tests/test_api.py tests/test_retry.py EXPERIMENTS.md
git commit -m "phase 4a2: FastAPI routes, samples, pipeline"
```

## Conclusion

A sample or an uploaded PDF, plus one sentence, now becomes cited JSON over HTTP, with clear errors. Go back through
the objectives and check each one without notes. Then answer:

1. A user uploads a 15-page scan. What happens, step by step, and what status do they get?
2. Why does every answer carry a sha256 of the file, and not only its name?

Looking for more challenges? Try these (optional):

1. Add `GET /v1/fields`, which lists the 12 field names and their meaning, for the UI.
2. Return `value` only for fields that have one, with `response_model_exclude_none=True`.

Checklist (`../PLAN.md`): **Retries, timeouts, degradation, idempotency** (the time limit, and one status per
failure). **Structured outputs** (the response model). Next: 4a3.
