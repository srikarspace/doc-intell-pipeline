# Python for Phase 4a2

This file explains the new Python in Part 4a2. Read one section when the main doc links to it. A test fixture and
`monkeypatch` are in 1a2 and 3a3 ([PY-4](./phase-3a3.md#py-4)).

<a id="py-1"></a>
## PY-1. `lru_cache` for a file read once

```python
@lru_cache
def load_samples() -> dict[str, Sample]:
    rows = json.loads((SAMPLES_DIR / "samples.json").read_text(encoding="utf-8"))
    return {row["id"]: Sample(**row) for row in rows}
```

1. The first call reads the file. Every later call gets the same dict back, with no file read.
2. In Node, it is like `const samples = require("./samples.json")` at the top of a module: read once, then kept.
3. `Sample(**row)` passes each key of `row` as a named argument. In JS: `new Sample({ ...row })`.

<a id="py-2"></a>
## PY-2. Decorators for routes

```python
@router.get("/health")
def health() -> Health:
    return Health(status="ok", version=VERSION)
```

1. `@router.get("/health")` registers the function below it for `GET /health`. In Express:
   `router.get("/health", health)`.
2. The return type `-> Health` is read by FastAPI. It checks the answer, and shows its shape on `/docs`.
3. A plain `def` route runs in a thread by itself. An `async def` route runs on the event loop.

<a id="py-3"></a>
## PY-3. `Annotated`, `Form` and `Depends`

```python
async def extract(
    client: Annotated[object, Depends(get_llm_client)],
    pdf: UploadFile | None = None,
    sample_id: Annotated[str | None, Form()] = None,
    request: Annotated[str, Form()] = "",
) -> ExtractResult:
```

1. `Annotated[type, extra]` is a type with a note attached. FastAPI reads the note.
2. `Form()` says "this comes from a form field". In Express with `multer`: `req.body.sample_id`.
3. `UploadFile | None = None` is an optional file field. In Express: `req.file`, which may be missing.
4. `Depends(get_llm_client)` says "call this function, and pass me its result". A test can replace it with
   `app.dependency_overrides[get_llm_client] = ...`.

<a id="py-4"></a>
## PY-4. `await`, threads and `wait_for`

```python
return await asyncio.wait_for(
    run_in_threadpool(run_pipeline, path, request, document, client), timeout=TIMEOUT_S
)
```

1. `run_in_threadpool(f, a, b)` runs `f(a, b)` in another thread, and gives back something you can `await`. In Node,
   it is like a worker thread wrapped in a Promise.
2. `asyncio.wait_for(x, timeout=...)` waits at most that long, then raises `TimeoutError`. In JS:
   `Promise.race([x, timeout(240_000)])`.
3. As with `Promise.race`, the slow work is not stopped. Only the waiting stops.

<a id="py-5"></a>
## PY-5. `except tuple(...)`

```python
except tuple(KNOWN_ERRORS) as e:
    raise as_http(e) from None
```

1. `tuple(KNOWN_ERRORS)` is the dict's keys: `(TimeoutError, TooLong, ...)`.
2. `except` with a tuple catches any of those types. Other errors keep going up, and FastAPI answers 500.
3. `KNOWN_ERRORS[type(e)]` then finds the status code. In JS: `statusFor.get(err.constructor)`.
4. `from None` hides the first error in the log, because it is not a bug.

<a id="py-6"></a>
## PY-6. `conftest.py` and a fixture that returns a function

```python
@pytest.fixture
def api(monkeypatch):
    sent = []

    def use(plan: dict) -> TestClient:
        ...
        return TestClient(app)

    use.sent = sent
    yield use
    app.dependency_overrides.clear()
```

1. pytest loads `tests/conftest.py` by itself. Its fixtures can be used by every test file, with no import.
2. The fixture gives back a function, so each test can choose the plan the fake model returns: `api({"fields": ...})`.
3. `use.sent = sent` puts a list on the function itself. A Python function is an object, as in JS.
4. The code after `yield` runs after the test, even when the test fails. It is like Jest's `afterEach`.
