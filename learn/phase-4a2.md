# Phase 4a2: the API with FastAPI

In this part, you put the whole pipeline behind one HTTP route: upload a PDF, type a request, get cited JSON. Each
piece is compared to Express, and each has a checkpoint.

This is part 2 of 3 for Phase 4a. It needs 4a. The paid checkpoints cost about $0.003 in total.

## Words used in this part

Read these first. Planner and plan are from 4a.

- **API**: a program that other programs call over HTTP. Example: `curl` sends a PDF, and gets JSON back.
- **Route**: one URL and method, with the function that answers it. Example: `POST /v1/extract`.
- **FastAPI**: a Python web framework. It is like Express, plus Pydantic checks on input and output.
- **uvicorn**: the server that runs a FastAPI app. In Node, `app.listen()` does this job.
- **Multipart form**: the request format for file uploads. A browser form with a file field sends it.
- **`UploadFile`**: FastAPI's object for one uploaded file. It is like `req.file` from `multer`.
- **Dependency**: a function that FastAPI runs before a route, and whose result it passes in. It is like Express
  middleware that puts something on `req`.
- **Status code**: the number that says how a request went. Example: 200 OK, 413 too large, 504 too slow.
- **Event loop**: the one thread that runs all `async` code. If it waits, every request waits. Same as in Node.
- **Threadpool**: a few extra threads for slow work that is not `async`. Here, the pipeline runs there.
- **TestClient**: calls the app in memory, with no server. It is like `supertest`.

## Objectives

By the end of this part you should be able to:

1. Run a FastAPI app, and say what each piece is in Express.
2. Choose a parser from the PDF itself: text layer or scan.
3. Turn each known failure into one clear status code.
4. Keep the event loop free while a 30-second pipeline runs.
5. Test the whole route with a fake model and a fake parser.

## Dependencies

New libraries:

- `fastapi`: the web framework. Like `express`.
- `uvicorn`: the server. Like Node's `http` server.
- `python-multipart`: reads file uploads. Like `multer`.

This part needs:

- 4a: `plan_request`, `pick`, `PlanError`.
- 2b: `extract_with_retry` and `final_answer`. You add two arguments.
- 2a: `check_answer`, which also runs the review rules.
- 3a and 3b2: `parse_pypdf` and `parse_docling_ocr`.
- E3: which parser to use for a scan.

## The big picture

Before this part, the pipeline ran only from the command line, on contracts in DuckDB.

After this part:

```text
curl -F pdf=@kubient.pdf -F request="parties"  ->  POST /v1/extract
                                                       |
     route: size, type, length checks -> run_pipeline() in a thread, with a time limit
                                                       |
     parse (pypdf or Docling OCR) -> plan -> extract + retries -> check -> pick -> JSON
```

- **4a3** adds the API key, the rate limit and the spend cap in front of the route.
- **4b** adds a trace span for each step of `run_pipeline`.
- **4c** puts this app in Docker, on Cloud Run.

## Remember this

> The route is thin. It checks the input, calls one typed function, and turns each known failure into a clear
> status code. The pipeline knows nothing about HTTP, so the API, the eval runner and later an agent can all call it.
>
> **Thin route, typed pipeline, one status per failure.**

## Why

**A product needs an address.** A user cannot run `python -m`. They send a PDF to a URL.

**Failures must be clear.** A scan that is too long and a request with no known field are different problems. A user
needs to know which one it was.

**A slow request must not block the others.** One extraction takes 13.6 s at the median, and up to 90 s. A server that
waits on it serves nobody else.

## Design decisions

- **The pipeline is one function in `domain/`, typed in and out.** The route only checks HTTP things. Other option: put
  the steps in the route. The eval runner and 4b could not reuse them.
- **Parse first, then plan.** 4a3 needs the text length before the first paid call, to know the worst cost. Other
  option: plan first. A request with only unknown fields would skip parsing, but 4a3 could not reserve money.
- **The PDF chooses its parser.** Text layer: pypdf. Scan: Docling OCR. The test: at least 200 characters per page.
  The thinnest dev contract has 870, and a fake scan has 0. Other option: let the user choose. Users do not know if
  their PDF has a text layer.
- **No vision parser in the API yet.** It costs about 20 times more, and needs the spend cap of 4a3 first. Other option:
  use it for scans now. One upload could cost more than a whole day of use.
- **A token limit on extraction, in the API only.** The argument defaults to `None`, so every eval run stays the same.
  Other option: a limit everywhere. That would change the conditions of E1 to E3.
- **`run_in_threadpool` with `asyncio.wait_for`.** The event loop stays free, and a slow request gets 504. Other
  option: a plain `def` route. FastAPI also uses a thread then, but there is no time limit.
- **The model client is a dependency.** A test can swap in a fake, with no network. Other option: a global client.
  Tests would need to patch inside the pipeline.
- **Each field carries its own issues and `needs_review`.** The UI in 4d can show a badge per field. Other option: one
  list of issues for the whole answer. The UI would need to sort it again.

## Worked example

All outputs are real. Guess before you open each box.

### Round 1: why did `curl` fail?

You send a dev contract straight from the CUAD folder:

```sh
curl -F "pdf=@data/raw/.../KUBIENT,INC_07_02_2020-EX-10.14-MASTER SERVICES AGREEMENT_Part2.pdf" ...
```

`curl` prints status `000`, and the server log shows no request. Guess why.

<details><summary>Guess, then open</summary>

The comma. In `-F`, a comma separates several files. `curl` looked for a file named `...data/raw/.../KUBIENT` and
gave up before it sent anything. Copy the file to a simple name first, like `data/kubient.pdf`. Many CUAD names have
commas.
</details>

### Round 2: what if the route is `async` and calls the pipeline directly?

`async def extract(...)` then `return run_pipeline(...)`, with no thread. Guess what happens to a second user during a
30-second request.

<details><summary>Guess, then open</summary>

They wait the whole 30 seconds. `run_pipeline` is normal code, so it holds the event loop until it ends. No other
request can even start. It is the same as a `while` loop inside an Express handler. Break 1 shows the test that
catches it.
</details>

### Round 3: is the same request always the same answer?

You send the same Kubient contract with the same request twice. The first answer said `non_compete` was found, with a
quote. Guess the second.

<details><summary>Guess, then open</summary>

```text
{'parties': (True, False, []), 'non_compete': (False, False, []), 'renewal_term': (False, True, ['maybe_missed'])}
```

`non_compete` is now **not found**. The temperature is 0, and the answer still changed. The clause says "Customer agrees
not to work with ... any Third-Party". Is that a non-compete? Even the model is unsure. That is why each field has
`needs_review`, and why E1 to E3 measured on many contracts, not one.
</details>

## Project setup

```sh
uv add fastapi uvicorn python-multipart
mkdir -p src/docintel/api
touch src/docintel/api/__init__.py src/docintel/api/app.py src/docintel/api/routes.py src/docintel/api/schemas.py
touch src/docintel/domain/pipeline.py
touch tests/conftest.py tests/test_api.py
```

Add one target to the `Makefile`, as in the standard layout of `../PLAN.md`:

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
│   ├── routes.py       # new: /health and /v1/extract
│   └── schemas.py      # new: the health answer
└── domain/
    └── pipeline.py     # new: one request, start to end
tests/
├── conftest.py         # new: shared fakes
└── test_api.py         # new
```

## Step 1: two new arguments for the retry loop

**Why.** The API needs a fake client in tests, and a token limit in production.

In `src/docintel/domain/extract/retry.py`, update `extract_with_retry`:

```python
def extract_with_retry(
    text: str,
    model: str | None = None,
    *,
    prompt_version: str = "v1",
    max_retries: int = 2,
    client=None,
    max_tokens: int | None = None,
) -> list[Attempt]:
    """Every attempt for one contract, in order. Stops when there are no errors, or no progress."""
    messages = build_messages(text, prompt_version)
    attempts = []
    for attempt_no in range(max_retries + 1):
        result = call_llm(
            messages, ContractFields, model=model, client=client, max_tokens=max_tokens
        )
        attempt = Attempt(attempt_no, result, check_result(result, text))
        attempts.append(attempt)
        if not attempt.errors:
            break
        if attempt_no > 0 and error_keys(attempt) == error_keys(attempts[-2]):
            break  # the same errors came back, so another retry is wasted money
        messages = messages + [
            {"role": "assistant", "content": result.raw_text},
            {"role": "user", "content": feedback(attempt.errors)},
        ]
    return attempts
```

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
| Most pages for a scan | Docling OCR: about 7 to 10 s per page on an 8 GB Mac |
| Largest file | largest dev PDF: 0.48 MB. A 2-page fake scan: 0.68 MB |
| Longest request | 4a requests are under 70 characters |
| Time limit | extraction: 13.6 s median, 36 s p95, 90 s max, per call. Up to 3 calls with retries. Cloud Run's default limit is 300 s |
| Extraction token limit | largest real answer: 17,999 tokens. p99: about 6,000 |

Write your values in `EXPERIMENTS.md`, under a new `## API limits (4a2)` heading.

<details><summary>Reference (open after you write yours)</summary>

- Scan if under 200 characters per page. Scans go to Docling OCR. No vision yet.
- Most pages: 100. For a scan: 10.
- Largest file: 10 MB. Longest request: 500 characters.
- Time limit: 240 s, under Cloud Run's 300 s.
- Extraction token limit: 20,000, above the largest real answer.
</details>

## Step 3: the pipeline types and the parser choice

**Why.** The answer needs a fixed shape, and the PDF must find its parser.

Put this in `src/docintel/domain/pipeline.py`:

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


class ExtractResult(BaseModel):
    request_id: str
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

Checkpoint (free). Copy one dev contract and its mild fake scan from 3b to simple names first:

```sh
cp "data/raw/CUAD_v1/full_contract_pdf/Part_II/Service/KUBIENT,INC_07_02_2020-EX-10.14-MASTER SERVICES AGREEMENT_Part2.pdf" data/kubient.pdf
cp "data/scans/mild/KUBIENT,INC_07_02_2020-EX-10.14-MASTER SERVICES AGREEMENT_Part2.pdf" data/kubient_scan.pdf
uv run python - <<'EOF'
from pathlib import Path

from docintel.domain.pipeline import parse_pdf

for name in ("data/kubient.pdf", "data/kubient_scan.pdf"):
    doc = parse_pdf(Path(name))
    print(name, doc.parser_name, len(doc.pages), "pages", len(doc.text), "chars", round(doc.latency_ms / 1000, 1), "s")
EOF
```

```text
data/kubient.pdf pypdf 2 pages 7590 chars 0.0 s
data/kubient_scan.pdf docling_ocr 2 pages 8083 chars 24.5 s
```

Docling also prints model warnings. You can ignore them.

## Step 4: the pipeline

**Why.** This is the one function that the API calls.

Add to the bottom of `src/docintel/domain/pipeline.py`:

```python
def run_pipeline(pdf_path: Path, request: str, client=None) -> ExtractResult:
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

## Step 5: the app and the health route

**Why.** A server must answer "are you alive?" before anything else. Cloud Run asks it.

Put this in `src/docintel/api/schemas.py`:

```python
"""Shapes of the API's own answers. The extraction answer is `ExtractResult` from the pipeline."""

from pydantic import BaseModel


class Health(BaseModel):
    status: str
    version: str
```

Put this in `src/docintel/api/routes.py`:

```python
"""The routes. Each one checks its input, then calls a typed function from `domain/`."""

import asyncio
import tempfile
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool

from docintel.api.schemas import Health
from docintel.domain.pipeline import ExtractResult, NothingToExtract, TooLong, run_pipeline
from docintel.domain.planner.planner import PlanError

VERSION = "0.1.0"
MAX_BYTES = 10 * 1024 * 1024  # the largest dev PDF is 0.48 MB; scans are bigger
MAX_REQUEST_CHARS = 500
TIMEOUT_S = 240  # Cloud Run stops a request at 300 s by default


router = APIRouter()


def get_llm_client():
    """None means the real OpenRouter client. Tests replace this with a fake."""
    return None


@router.get("/health")
def health() -> Health:
    return Health(status="ok", version=VERSION)
```

Put this in `src/docintel/api/app.py`:

```python
"""The FastAPI app. Run it with: uv run uvicorn docintel.api.app:app"""

from fastapi import FastAPI

from docintel.api.routes import VERSION, router

app = FastAPI(title="docintel", version=VERSION)
app.include_router(router)
```

*Python here: [decorators for routes](./py/phase-4a2.md#py-1).*

Here, side by side with Express:

| FastAPI | Express |
|---|---|
| `router = APIRouter()` | `const router = express.Router()` |
| `@router.get("/health")` | `router.get("/health", handler)` |
| `-> Health` return type | `res.json(...)`, plus a shape check |
| `app.include_router(router)` | `app.use(router)` |
| `uvicorn docintel.api.app:app` | `app.listen(8000)` |

Checkpoint. Start the server in one terminal:

```sh
make serve
```

In a second terminal:

```sh
curl -s localhost:8000/health
```

```text
{"status":"ok","version":"0.1.0"}
```

Open `http://localhost:8000/docs` in a browser too. FastAPI builds this page from your types.

## Step 6: the extract route

**Why.** This is the product: a PDF and a request in, cited JSON out.

Add to the bottom of `src/docintel/api/routes.py`:

```python
@router.post("/v1/extract")
async def extract(
    pdf: UploadFile,
    client: Annotated[object, Depends(get_llm_client)],
    request: Annotated[str, Form()] = "",
) -> ExtractResult:
    if pdf.size is not None and pdf.size > MAX_BYTES:
        raise HTTPException(413, f"the PDF is over {MAX_BYTES // (1024 * 1024)} MB")
    data = await pdf.read()
    if not data.startswith(b"%PDF-"):
        raise HTTPException(415, "the file is not a PDF")
    if len(request) > MAX_REQUEST_CHARS:
        raise HTTPException(422, f"the request is over {MAX_REQUEST_CHARS} characters")
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "upload.pdf"
        path.write_bytes(data)
        try:
            return await asyncio.wait_for(
                run_in_threadpool(run_pipeline, path, request, client), timeout=TIMEOUT_S
            )
        except TimeoutError:
            raise HTTPException(504, f"no answer within {TIMEOUT_S} s") from None
        except TooLong as e:
            raise HTTPException(413, str(e)) from None
        except NothingToExtract as e:
            raise HTTPException(422, str(e)) from None
        except PlanError as e:
            raise HTTPException(502, str(e)) from None
```

*Python here: [`Annotated`, `Form` and `Depends`](./py/phase-4a2.md#py-2) · [`await`, threads and `wait_for`](./py/phase-4a2.md#py-3).*

Here, in order:

1. Refuse a file over the size limit (413), and a file that does not start like a PDF (415).
2. Refuse a request that is too long (422).
3. Save the upload to a temporary folder, which is deleted afterwards.
4. Run the pipeline in a thread, with a time limit.
5. Turn each known error into one status code:

| Error | Status | Means |
|---|---|---|
| `TimeoutError` | 504 | too slow |
| `TooLong` | 413 | too many pages |
| `NothingToExtract` | 422 | no known field was asked |
| `PlanError` | 502 | the planner model gave a bad answer |

Any other error gives 500. That is a bug to look at, not a user mistake.

The server restarts by itself when you save (`--reload`). Checkpoint 1 (free): a file that is not a PDF.

```sh
echo hello > hello.txt
curl -s -w " %{http_code}\n" -F pdf=@hello.txt -F request="parties" localhost:8000/v1/extract
```

```text
{"detail":"the file is not a PDF"} 415
```

Checkpoint 2 (one planner call, about $0.0001): a request with no known field.

```sh
curl -s -w " %{http_code}\n" -F pdf=@data/kubient.pdf -F request="What are the payment terms?" localhost:8000/v1/extract
```

```text
{"detail":"no known field in the request; unknown: ['payment terms']"} 422
```

Checkpoint 3 (paid, about $0.001): the real thing.

```sh
curl -s -F pdf=@data/kubient.pdf -F request="parties, renewal term, any non-compete?" localhost:8000/v1/extract | python -m json.tool
```

In short: `parties` found with 2 names and no issue, `non_compete` not found, `renewal_term` not found but flagged
for review. Parser `pypdf`, 2 pages, $0.00067, 6.1 s.

<details><summary>The real output (open)</summary>

```text
{
    "request_id": "133e85a2-d2d7-4c5a-ab10-579f94b87931",
    "fields": {
        "parties": {
            "found": true,
            "value": [
                "Kubient, Inc.",
                "The Associated Press"
            ],
            "quotes": [
                "Kubient, Inc. (\"Kubient\")",
                "The Associated Press (\"Customer\")"
            ],
            "needs_review": false,
            "issues": []
        },
        "non_compete": {
            "found": false,
            "value": null,
            "quotes": [],
            "needs_review": false,
            "issues": []
        },
        "renewal_term": {
            "found": false,
            "value": null,
            "quotes": [],
            "needs_review": true,
            "issues": [
                {
                    "field": "renewal_term",
                    "rule": "maybe_missed",
                    "severity": "warn",
                    "detail": "renew"
                }
            ]
        }
    },
    "unknown": [],
    "needs_review": true,
    "parser": "pypdf",
    "pages": 2,
    "cost_usd": 0.00066654,
    "latency_ms": 6071
}
```
</details>

`renewal_term` is not found, but the contract has the word "renew". The review rule from 2a2 asks a person to look.

Checkpoint 4 (paid, about $0.001): the fake scan goes to Docling OCR.

```sh
curl -s -F pdf=@data/kubient_scan.pdf -F request="Who are the parties?" localhost:8000/v1/extract | python -m json.tool
```

The end of the real answer:

```text
    "parser": "docling_ocr",
    "pages": 2,
    "cost_usd": 0.00093002,
    "latency_ms": 34903
```

## Step 7: a small test

**Why.** The route has six ways to answer. Each one must keep working, with no network and no cost.

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

*Python here: [`conftest.py` and a fixture that returns a function](./py/phase-4a2.md#py-4).*

The test names say what is protected: health answers, only the asked fields come back, a request with no known field
makes no extraction call, a file that is not a PDF is refused, and so are a large file, a long request and a slow one.

<details><summary>Put this in <code>tests/test_api.py</code></summary>

```python
"""The API routes, with the fakes from `conftest.py`."""

import time

import pytest

from docintel.api import routes

PDF = b"%PDF-1.4 fake"


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
```
</details>

Checkpoint:

```sh
uv run pytest tests/test_api.py -q
make test
make lint
```

```text
.......                                                                  [100%]
7 passed in 0.19s
```

Your project structure should now look like this:

```text
src/docintel/
├── api/
│   ├── app.py
│   ├── routes.py        # /health, /v1/extract
│   └── schemas.py       # Health
└── domain/
    ├── extract/retry.py # + client, max_tokens
    └── pipeline.py      # parse_pdf, run_pipeline, ExtractResult
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


class ExtractResult(BaseModel):
    request_id: str
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


def run_pipeline(pdf_path: Path, request: str, client=None) -> ExtractResult:
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
import tempfile
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool

from docintel.api.schemas import Health
from docintel.domain.pipeline import ExtractResult, NothingToExtract, TooLong, run_pipeline
from docintel.domain.planner.planner import PlanError

VERSION = "0.1.0"
MAX_BYTES = 10 * 1024 * 1024  # the largest dev PDF is 0.48 MB; scans are bigger
MAX_REQUEST_CHARS = 500
TIMEOUT_S = 240  # Cloud Run stops a request at 300 s by default

router = APIRouter()


def get_llm_client():
    """None means the real OpenRouter client. Tests replace this with a fake."""
    return None


@router.get("/health")
def health() -> Health:
    return Health(status="ok", version=VERSION)


@router.post("/v1/extract")
async def extract(
    pdf: UploadFile,
    client: Annotated[object, Depends(get_llm_client)],
    request: Annotated[str, Form()] = "",
) -> ExtractResult:
    if pdf.size is not None and pdf.size > MAX_BYTES:
        raise HTTPException(413, f"the PDF is over {MAX_BYTES // (1024 * 1024)} MB")
    data = await pdf.read()
    if not data.startswith(b"%PDF-"):
        raise HTTPException(415, "the file is not a PDF")
    if len(request) > MAX_REQUEST_CHARS:
        raise HTTPException(422, f"the request is over {MAX_REQUEST_CHARS} characters")
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "upload.pdf"
        path.write_bytes(data)
        try:
            return await asyncio.wait_for(
                run_in_threadpool(run_pipeline, path, request, client), timeout=TIMEOUT_S
            )
        except TimeoutError:
            raise HTTPException(504, f"no answer within {TIMEOUT_S} s") from None
        except TooLong as e:
            raise HTTPException(413, str(e)) from None
        except NothingToExtract as e:
            raise HTTPException(422, str(e)) from None
        except PlanError as e:
            raise HTTPException(502, str(e)) from None
```
</details>

## Break it on purpose

Both breaks are free. Put the code back after each one.

**Break 1: no thread.** In `extract`, replace the whole `return await asyncio.wait_for(...)` with
`return run_pipeline(path, request, client)`. Guess: which test fails?

<details><summary>What you see</summary>

```text
FAILED tests/test_api.py::test_a_slow_request_times_out - fastapi.exce...
1 failed, 6 passed
```

The slow fake ran to the end, and nothing stopped it. In production, every other user would wait too (Round 2).
</details>

**Break 2: forget one error.** Delete the two lines for `TooLong`. Send a long scan, or set `MAX_SCAN_PAGES = 1` and
send `data/kubient_scan.pdf` with `curl -s -w " %{http_code}\n"`. Guess the status code.

<details><summary>What you see</summary>

```text
Internal Server Error 500
```

The user cannot tell a bug from a long file. With the lines back:

```text
{"detail":"a scan of 2 pages, the limit for scans is 1"} 413
```
</details>

## Experiment

This part runs no experiment. It adds no eval number. The checkpoints above are single requests, and E1 to E3 are
still the quality numbers. Write your Step 2 limits in `EXPERIMENTS.md`, because 4c and the README use them.

## Gotchas

- **Commas in file names break `curl -F`.** Copy the file to a simple name (Round 1).
- **A timed-out request still runs.** `wait_for` stops waiting, but the thread finishes, and the calls are still paid.
  4a3 counts that money.
- **Docling OCR loads its models on the first scan.** The first scan is slower than the next ones.
- **The same request can give a different answer** (Round 3). That is what `needs_review` is for.
- **The API logs nothing to DuckDB.** `call_llm` gets no `con` here. 4b adds a request log in Postgres.

## Explain back, then commit

Explain to Claude in a few sentences:

- `retry.py`: the two new arguments, and why the defaults keep E1 to E3 the same.
- `pipeline.py`: the order of the steps, how a PDF chooses its parser, and why parsing comes first.
- `routes.py`: each status code, and what the user should do for each one.
- Why the pipeline runs in a thread. What happens to a request that times out.
- Each line of the Express table, from memory.
- `conftest.py` and `test_api.py`: how the fake model knows which call it is answering.

Then:

```sh
git status
git add pyproject.toml uv.lock Makefile src/docintel/api src/docintel/domain/pipeline.py src/docintel/domain/extract/retry.py tests/conftest.py tests/test_api.py tests/test_retry.py EXPERIMENTS.md
git commit -m "phase 4a2: FastAPI extract route"
```

## Conclusion

A PDF and a sentence now become cited JSON over HTTP, with clear errors. Go back through the objectives and check each
one without notes. Then answer:

1. A user uploads a 15-page scan. What happens, step by step, and what status do they get?
2. Why is `async def` with `run_in_threadpool` better than `async def` that calls the pipeline directly?

Looking for more challenges? Try these (optional):

1. Add `GET /v1/fields`, which lists the 12 field names and their meaning.
2. Return `value` only for fields that have one, with `response_model_exclude_none=True`.

Checklist (`../PLAN.md`): **Retries, timeouts, degradation, idempotency** (the time limit, and one status per
failure). **Structured outputs** (the response model). Next: 4a3.
