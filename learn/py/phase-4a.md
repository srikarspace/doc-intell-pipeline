# Python for Phase 4a

This file explains the new Python in Part 4a. Read one section when the main doc links to it. A test fixture and
`monkeypatch` are in 1a2 and 3a3 ([PY-4](./phase-3a3.md#py-4)).

<a id="py-1"></a>
## PY-1. `Literal` from a tuple

```python
FIELDS = tuple(ContractFields.model_fields)
FieldName = Literal[FIELDS]
```

1. `ContractFields.model_fields` is a dict of the 12 fields. `tuple(...)` keeps only the names, in order.
2. `Literal[("parties", "agreement_date", ...)]` means "one of these strings, and nothing else".
3. FastAPI reads it on `fields: list[FieldName]`, and refuses any other string with 422.

In TypeScript, it is `type FieldName = "parties" | "agreement_date" | ...`. Here the list is built from the model, so
it never goes out of date. Some type checkers warn about a variable inside `Literal`. Python and Pydantic accept it.

<a id="py-2"></a>
## PY-2. `lru_cache` for a file read once

```python
@lru_cache
def load_samples() -> dict[str, Sample]:
    rows = json.loads((SAMPLES_DIR / "samples.json").read_text(encoding="utf-8"))
    return {row["id"]: Sample(**row) for row in rows}
```

1. The first call reads the file. Every later call gets the same dict back, with no file read.
2. In Node, it is like `const samples = require("./samples.json")` at the top of a module: read once, then kept.
3. `Sample(**row)` passes each key of `row` as a named argument. In JS: `new Sample({ ...row })`.

<a id="py-3"></a>
## PY-3. Decorators for routes

```python
@router.get("/health")
def health() -> Health:
    return Health(status="ok", version=VERSION)
```

1. `@router.get("/health")` registers the function below it for `GET /health`. In Express:
   `router.get("/health", health)`.
2. The return type `-> Health` is read by FastAPI. It checks the answer, and shows its shape on `/docs`.
3. A plain `def` route runs in a thread by itself. An `async def` route runs on the event loop.

<a id="py-4"></a>
## PY-4. `Annotated`, `Form` and `Depends`

```python
async def extract(
    client: Annotated[object, Depends(get_llm_client)],
    pdf: UploadFile | None = None,
    sample_id: Annotated[str | None, Form()] = None,
    fields: Annotated[list[FieldName] | None, Form()] = None,
) -> ExtractResult:
```

1. `Annotated[type, extra]` is a type with a note attached. FastAPI reads the note.
2. `Form()` says "this comes from a form field". In Express with `multer`: `req.body.sample_id`.
3. `list[...]` in a form means the same key can come many times: `-F fields=parties -F fields=renewal_term`.
4. `UploadFile | None = None` is an optional file field. In Express: `req.file`, which may be missing.
5. `Depends(get_llm_client)` says "call this function, and pass me its result". A test can replace it with
   `app.dependency_overrides[get_llm_client] = ...`.

The default is `None`, not `[]`. A list as a default value is shared between calls in Python, and ruff warns about it.

<a id="py-5"></a>
## PY-5. `await`, threads and `wait_for`

```python
return await asyncio.wait_for(
    run_in_threadpool(run_pipeline, path, fields or [], document, client), timeout=TIMEOUT_S
)
```

1. `run_in_threadpool(f, a, b)` runs `f(a, b)` in another thread, and gives back something you can `await`. In Node,
   it is like a worker thread wrapped in a Promise.
2. `asyncio.wait_for(x, timeout=...)` waits at most that long, then raises `TimeoutError`. In JS:
   `Promise.race([x, timeout(240_000)])`.
3. As with `Promise.race`, the slow work is not stopped. Only the waiting stops.
4. `fields or []` turns `None` into an empty list. In JS: `fields ?? []`.

<a id="py-6"></a>
## PY-6. `except tuple(...)`

```python
except tuple(KNOWN_ERRORS) as e:
    raise as_http(e) from None
```

1. `tuple(KNOWN_ERRORS)` is the dict's keys: `(TimeoutError, TooLong, NoAnswer)`.
2. `except` with a tuple catches any of those types. Other errors keep going up, and FastAPI answers 500.
3. `KNOWN_ERRORS[type(e)]` then finds the status code. In JS: `statusFor.get(err.constructor)`.
4. `from None` hides the first error in the log, because it is not a bug.

<a id="py-7"></a>
## PY-7. `conftest.py` and a fixture that uses a fixture

```python
@pytest.fixture
def sent() -> list:
    return []


@pytest.fixture
def api(monkeypatch, sent) -> TestClient:
    ...
    app.dependency_overrides[routes.get_llm_client] = lambda: fake_llm(sent)
    yield TestClient(app)
    app.dependency_overrides.clear()
```

1. pytest loads `tests/conftest.py` by itself. Its fixtures can be used by every test file, with no import.
2. `api` asks for `sent` by name, so pytest makes `sent` first. A test that asks for both gets the **same** list:
   `def test_...(api, sent)`.
3. The fake model adds one item to `sent` per call, so a test can check "no call was made": `assert sent == []`.
4. The code after `yield` runs after the test, even when the test fails. It is like Jest's `afterEach`.
