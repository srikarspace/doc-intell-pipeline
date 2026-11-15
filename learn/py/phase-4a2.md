# Python for Phase 4a2

This file explains the new Python in Part 4a2. Read one section when the main doc links to it. A test fixture and
`monkeypatch` are in 1a2 and 3a3 ([PY-4](./phase-3a3.md#py-4)).

<a id="py-1"></a>
## PY-1. Decorators for routes

```python
@router.get("/health")
def health() -> Health:
    return Health(status="ok", version=VERSION)
```

1. `@router.get("/health")` registers the function below it for `GET /health`. In Express:
   `router.get("/health", health)`.
2. The return type `-> Health` is read by FastAPI. It checks the answer, and shows its shape on `/docs`.
3. A plain `def` route runs in a thread by itself. An `async def` route runs on the event loop.

<a id="py-2"></a>
## PY-2. `Annotated`, `Form` and `Depends`

```python
async def extract(
    pdf: UploadFile,
    client: Annotated[object, Depends(get_llm_client)],
    request: Annotated[str, Form()] = "",
) -> ExtractResult:
```

1. `Annotated[type, extra]` is a type with a note attached. FastAPI reads the note.
2. `Form()` says "this comes from a form field". In Express with `multer`: `req.body.request`.
3. `Depends(get_llm_client)` says "call this function, and pass me its result". A test can replace it with
   `app.dependency_overrides[get_llm_client] = ...`.
4. `UploadFile` with no note is a file field. In Express: `req.file`.

<a id="py-3"></a>
## PY-3. `await`, threads and `wait_for`

```python
return await asyncio.wait_for(
    run_in_threadpool(run_pipeline, path, request, client), timeout=TIMEOUT_S
)
```

1. `run_in_threadpool(f, a, b)` runs `f(a, b)` in another thread, and gives back something you can `await`. In Node,
   it is like a worker thread wrapped in a Promise.
2. `asyncio.wait_for(x, timeout=...)` waits at most that long, then raises `TimeoutError`. In JS:
   `Promise.race([x, timeout(240_000)])`.
3. As with `Promise.race`, the slow work is not stopped. Only the waiting stops.

<a id="py-4"></a>
## PY-4. `conftest.py` and a fixture that returns a function

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
