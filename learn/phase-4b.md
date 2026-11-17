# Phase 4b: traces and logs

In this part, you make every request easy to follow after it is over. Each request gets one id. The id is in every log
line, in the answer, and in a **trace**: a tree of timed steps you can open in Phoenix. When a request is slow, wrong or
expensive, you find out why in a minute, not by adding `print` and running it again.

This is part 1 of 2 for Phase 4b. It needs 4a2. The paid checkpoint costs about $0.001.

## Words used in this part

Read these first.

- **Log line**: one fact written by the server while it works. Example: `{"event": "extract.done", "cost_usd": 0.0008}`.
- **request_id**: a random id given to one HTTP request. Example: `27ba93ef-e75f-4e3a-92a0-d5c63679eae5`.
- **Middleware**: code that runs around every request, before and after the route. In Express: `app.use(...)`.
- **Span**: one timed step, with a name, a start, an end and a few facts (**attributes**). Example: `parse`, 25 ms,
  `pages=2`.
- **Trace**: all the spans of one request, as a tree. A span inside another span is its **child**.
- **OpenTelemetry (OTel)**: the standard library and format for spans. Most tools can read it.
- **Tracer provider**: the object that decides where spans go. With none, spans cost nothing and go nowhere.
- **Exporter**: the part that sends finished spans somewhere. Example: to Phoenix, or to a list in a test.
- **Phoenix**: a local web app that stores traces and shows them as trees. It runs at `localhost:6006`.
- **Auto-trace (instrumentation)**: a library that makes spans for another library's calls, with no change to your
  code. Example: OpenInference makes a span for every OpenAI call.

## Objectives

By the end of this part you should be able to:

1. Give every request one id, and put it in the response header, the answer, every log line and the trace.
2. Write JSON logs with structlog, and say what must never be logged.
3. Add spans to the pipeline with OpenTelemetry, and explain why they cost nothing when tracing is off.
4. Run Phoenix on your machine, open one trace, and say where the time and the money went.
5. Test the shape of a trace with an in-memory exporter.

## Dependencies

New libraries (checked on PyPI and OSV: maintained, 0 open advisories):

- `structlog`: JSON logs. In Node, it is like `pino`.
- `arize-phoenix-otel`: one function, `register`, that sends OTel spans to Phoenix.
- `openinference-instrumentation-openai`: a span for every OpenAI call. Pinned to `0.1.73`: `0.1.74` is one day old.
- The Phoenix server (`arize-phoenix`) is **not** added. `uvx` runs it in its own folder, like `npx some-tool`.

This part needs 4a (the routes, the `api` fixture) and 4a2 (`run_pipeline` with `on_event`, the stream route).

## The big picture

Before this part, a request left nothing behind. After this part:

```text
curl ... /v1/extract
   header        x-request-id: 27ba93ef-...
   answer        {"request_id": "27ba93ef-...", ...}
   log lines     {"event": "extract.done", "request_id": "27ba93ef-...", "cost_usd": 0.00082936, ...}
                 {"event": "request", "request_id": "27ba93ef-...", "status": 200, "ms": 6011}
   trace         POST /v1/extract
                 └─ pipeline  request_id=27ba93ef-...
                    ├─ parse
                    ├─ extract
                    │  └─ attempt
                    │     └─ ChatCompletion    (tokens, model)
                    ├─ check
                    └─ highlight
```

4b2 uses the same id as the key of a row in DuckDB, and for the reviews.

## Remember this

> One request gets one id, at the very start. The id goes into the header, the answer, every log line and the root
> span. Logs say **what** happened, traces say **where the time went**, and the id joins them. Spans use the OTel API,
> which does nothing until the app turns it on, so the pipeline stays the same for evals and tests.
>
> **One id, three views: answer, log, trace.**

## Why

**"It was slow" is not something you can fix.** A trace says "the model took 5.8 s of 6.0 s, and parse took 25 ms".
Now you know what to work on.

**A retry costs money twice.** With one `attempt` span per call, you see at once when a request needed a repair retry,
and what it cost.

**A user can only send you what they see.** The UI can show the `request_id`. With it, you find the exact log lines and
trace of their request.

## Design decisions

- **The id is made by a middleware, at the start.** So even a failed or crashed request has one. Other option: let
  `run_pipeline` make it, as before. Then a request that fails before the pipeline has no id.
- **`run_pipeline` takes the id as an argument, with a default.** The eval runner calls it with no id, and gets a new
  one as before. Other option: read the id from a hidden global. Then `domain/` depends on the web.
- **Spans use the OTel API inside `domain/`.** With no tracer provider, each span is a "do nothing" object. Other
  option: make spans in the route from the `on_event` callbacks. Then the OpenAI call would not be inside its
  `attempt` span.
- **One span per step, the same steps as the stream.** `parse`, `extract` with one `attempt` per call, `check` and
  `highlight`. Other option: a span for each field. That is 12 tiny spans with nothing to learn from.
- **Only the extract routes are traced.** `/health` and the sample files would fill Phoenix, and pull its latency
  numbers down. Other option: trace everything. Phoenix showed a P50 of 49 ms, because of three `/health` calls.
- **Phoenix runs with `uvx`, outside the project, with its assistant tools and usage tracking off.** The app never
  imports it, and needs only its traces. Other option: add it to `pyproject.toml`. The lockfile gets much bigger, and
  the defaults let Phoenix's assistant run shell commands.
- **Logs hold numbers and names, never contract text or keys.** The trace does hold the prompt (OpenInference records
  it). That is fine while Phoenix runs only on your machine. Other option: hide inputs in traces too, with
  `OPENINFERENCE_HIDE_INPUTS=true`.

## Worked example

All numbers are real. Guess before you open each box.

### Round 1: where did the time go?

One Kubient request took 6,015 ms. It has spans for parse, the model call, check and highlight. Guess how long the
model call took.

<details><summary>Guess, then open</summary>

```text
POST /v1/extract       6015 ms
  pipeline             6004 ms
    parse                25 ms
    extract            5953 ms
      attempt          5952 ms
        ChatCompletion 5853 ms
    check                 0 ms
    highlight            24 ms
```

5,853 ms, or 97% of the request. Making parse or highlight faster would change nothing you can feel. The only thing that
matters for speed here is the model call.
</details>

### Round 2: what does Phoenix say it cost?

The `attempt` span says `cost_usd: 0.00082936`. Guess the "Total Cost" Phoenix shows for this trace.

<details><summary>Guess, then open</summary>

`$0`. Phoenix works out cost from its own price list, and it has no price for `deepseek/deepseek-v4-flash` through
OpenRouter. Our `cost_usd` comes from OpenRouter itself, so it is the real number. Read cost on the `attempt` span (and
in 4b2, from DuckDB), not from Phoenix's total.
</details>

## Project setup

```sh
uv add arize-phoenix-otel structlog "openinference-instrumentation-openai==0.1.73"
touch src/docintel/core/logs.py src/docintel/core/tracing.py
touch tests/test_tracing.py
```

Among the last lines of the output:

```text
 + opentelemetry-sdk==1.45.2
 + structlog==26.1.0
```

You should now have:

```text
src/docintel/
├── core/
│   ├── logs.py       # new: JSON logs
│   └── tracing.py    # new: send spans to Phoenix
├── api/
│   ├── app.py        # changed: middleware, lifespan
│   └── routes.py     # changed: pass the id, log the result
└── domain/
    ├── pipeline.py   # changed: spans
    └── extract/
        └── retry.py  # changed: one span per attempt
tests/
└── test_tracing.py   # new
```

## Step 1: JSON logs

**Why.** A log line must be easy to search, and it must carry the request_id by itself.

Put this in `src/docintel/core/logs.py`:

```python
"""JSON logs: one object per line, with the request_id of the request it belongs to."""

import structlog


def setup_logging() -> None:
    """Call once, when the app starts."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,  # adds request_id, set by the middleware
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ]
    )
```

Here, we tell structlog how to build each line. A **processor** is one function in a chain. Each one gets the line as
a dict, changes it, and passes it on:

1. `merge_contextvars` adds the keys that were "bound" for this request, like `request_id` (Step 2).
2. `add_log_level` adds `"level": "info"`.
3. `TimeStamper` adds the time, in UTC.
4. `JSONRenderer` turns the dict into one line of JSON.

*Python: `contextvars` is in [PY-1](./py/phase-4b.md#py-1).*

Checkpoint:

```sh
uv run python -c "import structlog; from docintel.core.logs import setup_logging; setup_logging(); structlog.get_logger().info('hello', pages=2)"
```

```text
{"pages": 2, "event": "hello", "level": "info", "timestamp": "2026-11-17T04:04:35.566864Z"}
```

## Step 2: one id per request

**Why.** Everything else in this part hangs on the id.

In `src/docintel/api/app.py`, add the imports `time`, `uuid`, `asynccontextmanager` (from `contextlib`), `structlog`,
`Request` (from `fastapi`) and `setup_logging`. Then make the rest of the file:

```python
log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    yield


app = FastAPI(title="docintel", version=VERSION, lifespan=lifespan)
app.include_router(router)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Give every request an id. Every log line and the trace carry it, and so does the answer."""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=request_id)
    start = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    ms = round((time.perf_counter() - start) * 1000)
    log.info(
        "request", method=request.method, path=request.url.path, status=response.status_code, ms=ms
    )
    return response
```

Here, we add two things:

1. `lifespan` runs once when the server starts (before `yield`), and once when it stops (after). Logging is set up
   there.
2. The middleware runs around every request:
   1. It makes a new id, and keeps it on `request.state`, so a route can read it.
   2. It binds the id, so every log line from now on, in this request, has it.
   3. `call_next(request)` runs the route. In Express: `next()`.
   4. It puts the id in the `X-Request-ID` header, and writes one `request` line.

*Python: `lifespan` and the middleware are in [PY-2](./py/phase-4b.md#py-2) and [PY-3](./py/phase-4b.md#py-3).*

Then, in `Makefile`, turn off uvicorn's own access log (our `request` line replaces it):

```makefile
serve:  ## run the API on http://localhost:8000
	uv run uvicorn docintel.api.app:app --reload --no-access-log
```

Checkpoint. Run `make serve` in one terminal, then:

```sh
curl -si localhost:8000/health
```

```text
HTTP/1.1 200 OK
date: Tue, 17 Nov 2026 03:59:48 GMT
server: uvicorn
content-length: 33
content-type: application/json
x-request-id: 0b2b75dd-375c-45d9-ac07-5d8228a6c046

{"status":"ok","version":"0.1.0"}
```

The server terminal shows:

```text
{"method": "GET", "path": "/health", "status": 200, "ms": 1, "event": "request", "request_id": "0b2b75dd-375c-45d9-ac07-5d8228a6c046", "level": "info", "timestamp": "2026-11-17T03:59:49.310641Z"}
```

The same id is in the header and in the log line.

## Step 3: the routes pass the id and log the result

**Why.** The answer's `request_id` must be the same id as the log and the trace. And each answer needs one line with
its numbers.

In `src/docintel/domain/pipeline.py`, give `run_pipeline` one more argument, after `on_event`:
`request_id: str | None = None`. Make its first line `request_id = request_id or str(uuid.uuid4())`. At the bottom,
the answer uses it: `request_id=request_id,` in place of `request_id=str(uuid.uuid4()),`.

In `src/docintel/api/routes.py`, update the imports and add a logger:

```python
import structlog
from fastapi import APIRouter, Depends, Form, HTTPException, Request, UploadFile
```

```python
router = APIRouter()
log = structlog.get_logger()
```

Add these two helpers after `as_http`:

```python
def finished(result: ExtractResult) -> None:
    """One log line per answer. Never the contract text: it can be private."""
    log.info(
        "extract.done",
        parser=result.parser,
        pages=result.pages,
        fields=len(result.fields),
        needs_review=result.needs_review,
        cost_usd=result.cost_usd,
        latency_ms=result.latency_ms,
    )


def failed(error: HTTPException) -> None:
    log.warning("extract.failed", status=error.status_code, detail=error.detail)
```

Here, we write one line for each answer, and one for each known failure. 4b2 adds a database row in the same two
places.

Now the routes. Each one gets `request: Request` as its first argument, and passes the id. In `extract`:

```python
        try:
            result = await asyncio.wait_for(
                run_in_threadpool(
                    run_pipeline,
                    path,
                    fields or [],
                    document,
                    client,
                    request_id=request.state.request_id,
                ),
                timeout=TIMEOUT_S,
            )
        except tuple(KNOWN_ERRORS) as e:
            error = as_http(e)
            failed(error)
            raise error from None
    finished(result)
    return result
```

In `extract_stream`, inside `work`: the same `request_id=...` goes after `emit`. Call `finished(result)` before the
`result` event, and `failed(error)` before the `error` event. The last `except` becomes:

```python
        except Exception:  # a bug: the details go to the log, not to the browser
            log.exception("extract.crashed")
            await queue.put(("error", {"status": 500, "detail": "internal error"}))
```

Here, `log.exception` writes the error **and** its stack. Before this part, a bug inside the stream left no trace at
all: the browser got "internal error", and the server said nothing.

*Python: the keyword argument through `run_in_threadpool` is in [PY-4](./py/phase-4b.md#py-4).*

Checkpoint:

```sh
make test
```

```text
E                       TypeError: test_a_slow_request_times_out.<locals>.<lambda>() got an unexpected keyword argument 'request_id'
FAILED tests/test_api.py::test_a_slow_request_times_out - TypeError: test_a_s...
1 failed, 124 passed in 1.99s
```

The fake `run_pipeline` in that 4a test takes `*args` only, and now it gets `request_id=`. A fake must accept what the
real function accepts. In `tests/test_api.py`, change the lambda to `lambda *args, **kwargs: time.sleep(0.5)`.

```sh
make test
```

```text
125 passed in 1.51s
```

## Step 4: spans in the pipeline

**Why.** The log says the request took 6 s. The spans say which step took them.

In `src/docintel/domain/pipeline.py`, add the import and a tracer under the constants:

```python
from opentelemetry import trace
```

```python
EXTRACT_MAX_TOKENS = 20_000  # the largest real extraction answer used 17,999
tracer = trace.get_tracer(__name__)
```

Then put each step of `run_pipeline` inside its own span. The steps are the same as before, moved one level in:

```python
    request_id = request_id or str(uuid.uuid4())
    start = time.perf_counter()
    chosen = [f for f in FIELDS if f in fields] or list(FIELDS)  # schema order, no repeats
    about = {"request_id": request_id, "sample_id": document.sample_id or "", "fields": chosen}
    with tracer.start_as_current_span("pipeline", attributes=about):
        with tracer.start_as_current_span("parse") as span:
            on_event("stage", {"name": "parse", "status": "start"})
            doc = parse_pdf(pdf_path)
            span.set_attributes({"parser": doc.parser_name, "pages": len(doc.pages)})
            done = {"name": "parse", "status": "done", "parser": doc.parser_name}
            on_event("stage", done | {"pages": len(doc.pages)})
        with tracer.start_as_current_span("extract"):
            on_event("stage", {"name": "extract", "status": "start"})
            attempts = extract_with_retry(
                doc.text,
                client=client,
                max_tokens=EXTRACT_MAX_TOKENS,
                on_attempt=lambda a: on_event(
                    "attempt", {"n": a.attempt_no, "errors": len(a.errors)}
                ),
            )
            answer = final_answer(attempts)
            if answer is None:
                raise NoAnswer("the model gave no answer that fits the schema")
        with tracer.start_as_current_span("check") as span:
            ...  # the check step, then: span.set_attribute("issues", len(issues))
        with tracer.start_as_current_span("highlight"):
            ...  # text_layer, results and the loop over chosen, as in 4a2
```

The full function is at the end of Step 7.

Here, we:

1. Move `chosen` to the top, and open a `pipeline` span with the facts that find it again: id, sample, fields.
2. Wrap each step in a child span. A `with` block ends the span when the block ends, even on an error.
3. Add the facts you only know after a step: parser and pages, the number of issues.

*Python: `with` and `dict | dict` are in [PY-5](./py/phase-4b.md#py-5).*

Now one span per model call. In `src/docintel/domain/extract/retry.py`, add the same import and tracer (under
`FEEDBACK`), and wrap the call in the loop:

```python
    for attempt_no in range(max_retries + 1):
        with tracer.start_as_current_span("attempt", attributes={"n": attempt_no}) as span:
            result = call_llm(
                messages, ContractFields, model=model, client=client, max_tokens=max_tokens
            )
            attempt = Attempt(attempt_no, result, check_result(result, text))
            span.set_attributes({"errors": len(attempt.errors), "cost_usd": result.cost_usd or 0.0})
        attempts.append(attempt)
```

Here, each call gets its own span, with its number, its errors and its real cost from OpenRouter. A request with a
repair retry shows two `attempt` spans, side by side.

No tracer provider is set yet, so every span is a "do nothing" object. Checkpoint:

```sh
make test
```

```text
125 passed in 1.51s
```

Nothing changed for the tests, and nothing changes for the eval runner.

## Step 5: Phoenix, and turning tracing on

**Why.** The spans need somewhere to go.

Put this in `src/docintel/core/tracing.py`:

```python
"""Send spans to the local Phoenix, and trace every OpenAI call on its own."""

from phoenix.otel import register

from docintel.core.config import get_settings


def setup_tracing() -> None:
    """Call once, when the app starts. With TRACING=false, spans cost nothing and go nowhere."""
    if get_settings().tracing:
        register(project_name="docintel", auto_instrument=True, batch=True)
```

Here, `register` does three things:

1. It sets the tracer provider, so the spans from Step 4 become real.
2. It adds an exporter that sends finished spans to Phoenix, in batches, from a background thread.
3. `auto_instrument=True` turns on every OpenInference package that is installed. So each OpenAI call gets a
   `ChatCompletion` span, with the model and the token counts.

Add the setting in `src/docintel/core/config.py`, under `llm_max_attempts`:

```python
    tracing: bool = True  # send spans to the local Phoenix; TRACING=false turns it off
```

In `src/docintel/api/app.py`, import `setup_tracing`, call it in `lifespan` after `setup_logging()`, and trace only the
extract routes:

```python
def not_traced(scope) -> bool:
    """Trace only the extract routes. /health and the sample files would hide them in Phoenix."""
    return not scope["path"].startswith("/v1/extract")


app = FastAPI(
    title="docintel", version=VERSION, lifespan=lifespan, telemetry={"exclude": not_traced}
)
```

Here, we use a feature of FastAPI itself: once a tracer provider is set, it makes its own spans for each request
(`POST /v1/extract`, and three small ones inside it). `exclude` skips the paths we do not want.

The tests use `TestClient(app)` with no `with`, so `lifespan` never runs in tests. Tests never send spans to Phoenix.

Last, add a target to `Makefile`:

```makefile
phoenix:  ## run Phoenix on http://localhost:6006 (traces are kept in data/phoenix/)
	PHOENIX_WORKING_DIR=data/phoenix PHOENIX_TELEMETRY_ENABLED=false \
	PHOENIX_AGENTS_DISABLE_BASH=true PHOENIX_AGENTS_DISABLE_WEB_ACCESS=true \
	PHOENIX_AGENTS_DISABLE_GITHUB=true \
	uvx --from arize-phoenix==21.0.0 phoenix serve
```

Here, Phoenix keeps its traces in `data/phoenix/` (which git ignores). Its usage tracking, and its assistant's shell,
web and GitHub tools, are off.

Checkpoint. Run `make phoenix` in one terminal (the first run downloads Phoenix). The end of its output:

```text
  Telemetry           ➖ Disabled
  Server-side bash    ➖ Disabled
🚀 Phoenix is up and running — open http://127.0.0.1:6006 to get started.
```

Then restart `make serve` in a second terminal. Its start now includes:

```text
|  Phoenix Project: docintel
|  Collector Endpoint: localhost:4317
```

## Step 6: one real request, and how to read its trace

**Why.** You learn to read a trace on a real one.

Checkpoint (paid, about $0.001):

```sh
curl -s -D - -X POST localhost:8000/v1/extract -F sample_id=kubient -o /dev/null | grep -i x-request-id
```

```text
x-request-id: 27ba93ef-e75f-4e3a-92a0-d5c63679eae5
```

The server terminal:

```text
{"parser": "pypdf", "pages": 2, "fields": 12, "needs_review": true, "cost_usd": 0.00082936, "latency_ms": 6004, "event": "extract.done", "request_id": "27ba93ef-e75f-4e3a-92a0-d5c63679eae5", "level": "info", "timestamp": "2026-11-17T04:00:06.195274Z"}
{"method": "POST", "path": "/v1/extract", "status": 200, "ms": 6011, "event": "request", "request_id": "27ba93ef-e75f-4e3a-92a0-d5c63679eae5", "level": "info", "timestamp": "2026-11-17T04:00:06.196004Z"}
```

Open `http://localhost:6006`, then the `docintel` project, then the `POST /v1/extract` row. Its tree, with the
attributes that matter:

```text
POST /v1/extract          6015 ms   http.response.status_code=200
  fastapi.dependencies       1 ms
  fastapi.endpoint        6008 ms
    pipeline              6004 ms   request_id=27ba93ef-...
      parse                 25 ms   parser=pypdf  pages=2
      extract             5953 ms
        attempt           5952 ms   n=0  errors=0  cost_usd=0.00082936
          ChatCompletion  5853 ms   llm.model_name=deepseek/deepseek-v4-flash
                                    llm.token_count.prompt=2378
                                    llm.token_count.completion_details.reasoning=1320
      check                  0 ms   issues=2
      highlight             24 ms
  fastapi.serialization      0 ms
```

How to read it, top to bottom:

1. **The root's time** is what the user waited.
2. **Find the widest child.** Here: `extract`, `attempt`, `ChatCompletion`. The model call is 97% of the time.
3. **Count the `attempt` spans.** Two or three mean repair retries, each one paid. Their `errors` say why.
4. **Look at tokens.** 1,320 answer tokens were "reasoning", the model thinking before it writes. They are paid too.
5. **Look for red.** A failed step has an `ERROR` status, and the steps after it are missing.
6. **Open `ChatCompletion`** for the exact prompt and answer: the fastest way to see why a field is wrong.

To find a request by its id: open the **Spans** tab, remove the `parent_id is None` filter (it shows only the roots),
and type:

```text
attributes["request_id"] == "27ba93ef-e75f-4e3a-92a0-d5c63679eae5"
```

It finds the `pipeline` span. Click it to open the whole trace. (For the stream route, `pipeline` sits right under
`POST /v1/extract/stream`, because it runs in the `work` task.)

## Step 7: a small test

**Why.** A change that moves the OpenAI call out of its `attempt` span, or loses the id, would break no other test.

The test names say what is protected: one request is one tree with the right parents, one id joins the header, the
answer and the trace (and `/health` is not traced), and a failed step is marked as an error in the trace, before any
paid call.

<details><summary>Put this in <code>tests/test_tracing.py</code></summary>

```python
"""The trace of one request: which spans, under which parent, joined by one request_id."""

import pytest
from openinference.instrumentation.openai import OpenAIInstrumentor
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from docintel.domain import pipeline
from docintel.domain.pipeline import TooLong


@pytest.fixture(scope="module")
def exporter():
    """Spans go to a list in memory, not to Phoenix. A process can set its provider only once."""
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    OpenAIInstrumentor().instrument(tracer_provider=provider)
    yield exporter
    OpenAIInstrumentor().uninstrument()


@pytest.fixture
def spans(exporter):
    exporter.clear()
    return exporter


def post(api, fields):
    return api.post("/v1/extract", data={"sample_id": "kubient", "fields": fields})


def tree(spans) -> dict[str, str | None]:
    """Each span's name, and the name of its parent."""
    finished = spans.get_finished_spans()
    names = {s.context.span_id: s.name for s in finished}
    return {s.name: names.get(s.parent.span_id) if s.parent else None for s in finished}


def test_one_request_is_one_tree(api, spans):
    post(api, ["parties"])
    assert tree(spans) == {
        "POST /v1/extract": None,  # FastAPI makes these 4 by itself, once a provider is set
        "fastapi.dependencies": "POST /v1/extract",
        "fastapi.endpoint": "POST /v1/extract",
        "fastapi.serialization": "POST /v1/extract",
        "pipeline": "fastapi.endpoint",  # in another thread, but under the same request
        "parse": "pipeline",
        "extract": "pipeline",
        "attempt": "extract",
        "ChatCompletion": "attempt",  # made by OpenInference, not by us
        "check": "pipeline",
        "highlight": "pipeline",
    }


def test_one_id_joins_the_header_the_answer_and_the_trace(api, spans):
    api.get("/health")  # not traced
    response = post(api, ["parties"])
    (root,) = [s for s in spans.get_finished_spans() if s.name == "pipeline"]
    assert response.headers["X-Request-ID"] == response.json()["request_id"]
    assert root.attributes["request_id"] == response.json()["request_id"]
    assert "GET /health" not in tree(spans)


def test_a_failed_step_is_marked_in_the_trace(api, spans, monkeypatch):
    def too_long(path):
        raise TooLong("120 pages, the limit is 100")

    monkeypatch.setattr(pipeline, "parse_pdf", too_long)
    assert post(api, ["parties"]).status_code == 413
    (parse,) = [s for s in spans.get_finished_spans() if s.name == "parse"]
    assert parse.status.status_code.name == "ERROR"
    assert "ChatCompletion" not in tree(spans)  # it stopped before the paid call
```
</details>

Here, the `exporter` fixture sets a real tracer provider, but its exporter keeps spans in a list. It also turns on
OpenInference by hand, because `lifespan` does not run in tests. The fake OpenAI client from `conftest.py` still gets a
real `ChatCompletion` span.

*Python: a fixture with `scope="module"` and `yield` is in [PY-6](./py/phase-4b.md#py-6).*

Checkpoint:

```sh
uv run pytest -q tests/test_tracing.py
make test
```

```text
3 passed in 0.14s
128 passed in 1.49s
```

<details><summary>Full <code>src/docintel/domain/pipeline.py</code> run_pipeline</summary>

```python
def run_pipeline(
    pdf_path: Path,
    fields: list[FieldName],
    document: Document,
    client=None,
    on_event: Emit = no_events,
    request_id: str | None = None,
) -> ExtractResult:
    """Parse, extract all 12 with retries, check, keep the chosen fields. One span per step."""
    request_id = request_id or str(uuid.uuid4())
    start = time.perf_counter()
    chosen = [f for f in FIELDS if f in fields] or list(FIELDS)  # schema order, no repeats
    about = {"request_id": request_id, "sample_id": document.sample_id or "", "fields": chosen}
    with tracer.start_as_current_span("pipeline", attributes=about):
        with tracer.start_as_current_span("parse") as span:
            on_event("stage", {"name": "parse", "status": "start"})
            doc = parse_pdf(pdf_path)
            span.set_attributes({"parser": doc.parser_name, "pages": len(doc.pages)})
            done = {"name": "parse", "status": "done", "parser": doc.parser_name}
            on_event("stage", done | {"pages": len(doc.pages)})
        with tracer.start_as_current_span("extract"):
            on_event("stage", {"name": "extract", "status": "start"})
            attempts = extract_with_retry(
                doc.text,
                client=client,
                max_tokens=EXTRACT_MAX_TOKENS,
                on_attempt=lambda a: on_event(
                    "attempt", {"n": a.attempt_no, "errors": len(a.errors)}
                ),
            )
            answer = final_answer(attempts)
            if answer is None:
                raise NoAnswer("the model gave no answer that fits the schema")
        with tracer.start_as_current_span("check") as span:
            on_event("stage", {"name": "check", "status": "start"})
            issues = check_answer(answer, doc.text)  # rule errors and review warnings
            span.set_attribute("issues", len(issues))
        with tracer.start_as_current_span("highlight"):
            text_layer = doc.parser_name == "pypdf"
            results = {}
            for name in chosen:
                own = [i for i in issues if i.field == name]
                part = getattr(answer, name).model_dump()
                evidence = [
                    line_around(doc.text, i.detail) for i in own if i.rule == "maybe_missed"
                ]
                results[name] = FieldResult(
                    **part,
                    needs_review=bool(own),
                    issues=own,
                    highlights=boxes(pdf_path, part["quotes"], text_layer),
                    evidence=evidence,
                    evidence_highlights=boxes(pdf_path, evidence, text_layer),
                )
    return ExtractResult(
        request_id=request_id,
        document=document,
        fields=results,
        needs_review=any(r.needs_review for r in results.values()),
        parser=doc.parser_name,
        pages=len(doc.pages),
        cost_usd=sum(a.result.cost_usd or 0.0 for a in attempts) + doc.cost_usd,
        latency_ms=round((time.perf_counter() - start) * 1000),
    )
```
</details>

<details><summary>Full <code>src/docintel/api/app.py</code></summary>

```python
"""The FastAPI app. Run it with: uv run uvicorn docintel.api.app:app"""

import time
import uuid
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request

from docintel.api.routes import VERSION, router
from docintel.core.logs import setup_logging
from docintel.core.tracing import setup_tracing

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    setup_tracing()
    yield


def not_traced(scope) -> bool:
    """Trace only the extract routes. /health and the sample files would hide them in Phoenix."""
    return not scope["path"].startswith("/v1/extract")


app = FastAPI(
    title="docintel", version=VERSION, lifespan=lifespan, telemetry={"exclude": not_traced}
)
app.include_router(router)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Give every request an id. Every log line and the trace carry it, and so does the answer."""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=request_id)
    start = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    ms = round((time.perf_counter() - start) * 1000)
    log.info(
        "request", method=request.method, path=request.url.path, status=response.status_code, ms=ms
    )
    return response
```
</details>

## Break it on purpose

The breaks are free. Put the code back after each one.

**Break 1: forget to pass the id.** In `extract`, remove the line `request_id=request.state.request_id,`. Guess which
test fails.

<details><summary>What you see</summary>

```text
E       AssertionError: assert '623fd140-16e...-161a3dcfaf63' == '23ba8afa-bc5...-a2199e722844'
1 failed, 2 passed in 0.23s
```

The header has the middleware's id, and the answer has a new one from the default. Nothing crashes. The log and the
trace now point at different ids, and you would only notice on the day you need them.
</details>

**Break 2: stop Phoenix.** Press Ctrl+C in the `make phoenix` terminal, then send a free request to a sample that does
not exist:

```sh
curl -s -X POST localhost:8000/v1/extract -F sample_id=nope
```

Guess: does the API still answer?

<details><summary>What you see</summary>

```text
{"detail":"no sample 'nope'"}
```

The server terminal, a few seconds later:

```text
Transient error StatusCode.UNAVAILABLE encountered while exporting traces to localhost:4317, retrying in 0.80s. Error details: failed to connect to all addresses; last error: UNKNOWN: ipv4:127.0.0.1:4317: Failed to connect to remote host: Connection refused
```

Yes. The exporter runs in a background thread, so a missing Phoenix costs a warning, not a failed request. With
`TRACING=false make serve`, the warning goes away too.
</details>

## Experiment

This part runs no experiment. The paid checkpoint is one request, to read a real trace. Cost, latency and tokens for
many requests come from DuckDB in 4b2.

## Gotchas

- **The `request` line is wrong for a stream.** For the Kubient stream it said `"ms": 3`, because `call_next` returns
  when the headers are sent. The trace said 4,348 ms. Use `extract.done`, or the trace.
- **The trace holds the contract text.** OpenInference records the prompt on `ChatCompletion`. Keep Phoenix local, or
  set `OPENINFERENCE_HIDE_INPUTS=true`.
- **A span shows up a few seconds late.** The exporter sends spans in batches. Wait, then refresh.
- **`set_tracer_provider` works once per process.** A second call is ignored with a warning. That is why the test
  fixture has `scope="module"`.

## Explain back, then commit

Explain to Claude in a few sentences:

- `app.py`: what the middleware does, in order, and why the id is made there and not in the pipeline.
- `logs.py`: what each processor adds, and what must never be in a log line.
- `pipeline.py` and `retry.py`: which spans exist, what is on each, and why they cost nothing in the eval runner.
- `tracing.py`: the three things `register` does.
- `routes.py`: where `finished`, `failed` and `log.exception` are called, and what the browser sees for a bug.
- How to read a trace: where the time went, how to see a retry, how to find a request by its id.

Then:

```sh
git status
git add pyproject.toml uv.lock Makefile src/docintel/core/config.py src/docintel/core/logs.py src/docintel/core/tracing.py src/docintel/api/app.py src/docintel/api/routes.py src/docintel/domain/pipeline.py src/docintel/domain/extract/retry.py tests/test_api.py tests/test_tracing.py
git commit -m "phase 4b: request ids, JSON logs and Phoenix traces"
```

## Conclusion

Every request now leaves three views behind, joined by one id: the answer, the log lines and the trace. Go back
through the objectives and check each one without notes. Then answer:

1. A user says "the answer for this contract was slow". What do you ask them for, and what do you open first?
2. Why does `run_pipeline` still work in the eval runner, with no Phoenix and no tracer provider?

Looking for more challenges? Try these (optional):

1. Add the OTel `trace_id` to each log line with a structlog processor, so a log line links straight to its trace.
2. Give our spans an OpenInference kind (`openinference.span.kind = "CHAIN"`) and see how Phoenix shows them.

Checklist (`../PLAN.md`): **Observability** (traces in Phoenix, JSON logs with request_id). **Cost and latency
tracking** (cost and tokens per call, on the trace). Next: 4b2.
