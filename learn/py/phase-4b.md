# Python for Phase 4b

This file explains the new Python in Part 4b. Read one section when the main doc links to it. Fixtures and `yield` in
a fixture are in 4a ([PY-7](./phase-4a.md#py-7)).

<a id="py-1"></a>
## PY-1. `contextvars`: a value for this request only

```python
structlog.contextvars.bind_contextvars(request_id=request_id)
```

1. A **context variable** holds one value per request, not one value for the whole program.
2. The server handles many requests at once. Each one sees only its own `request_id`.
3. In Node, it is `AsyncLocalStorage`: `storage.run({ requestId }, () => next())`.
4. `merge_contextvars` (in `logs.py`) reads these values, and adds them to every log line.
5. The value follows the work into `run_in_threadpool` and into new `asyncio` tasks. That is why the `extract.done`
   line, written after the thread ends, still has the id.

`clear_contextvars()` comes first, so a value from an old request can never leak into a new one.

<a id="py-2"></a>
## PY-2. `lifespan`: code at start and at stop

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    setup_tracing()
    yield
```

1. FastAPI runs the code **before** `yield` once, when the server starts.
2. The server then handles requests while the function waits at `yield`.
3. Code **after** `yield` (none here) runs once, when the server stops.
4. `@asynccontextmanager` turns this one function into the "start" and "stop" pair FastAPI wants.

In Express, the "start" part is the code before `app.listen(...)`. The "stop" part is a `process.on("SIGTERM", ...)`
handler.

<a id="py-3"></a>
## PY-3. A middleware with `call_next`

```python
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    ...
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response
```

1. `@app.middleware("http")` registers the function for every HTTP request.
2. Code before `await call_next(request)` runs before the route.
3. `call_next` runs the route, and gives back its response.
4. Code after it can change the response, then returns it.

In Express:

```js
app.use(async (req, res, next) => {
  req.requestId = crypto.randomUUID();
  res.set("X-Request-ID", req.requestId);
  next();
});
```

`request.state` is a free place to keep your own values for this request. In Express: `req.requestId`.

<a id="py-4"></a>
## PY-4. Keyword arguments through `run_in_threadpool`, and `**kwargs`

```python
run_in_threadpool(run_pipeline, path, fields or [], document, client, request_id=request.state.request_id)
```

1. `run_in_threadpool(f, a, b, key=v)` calls `f(a, b, key=v)` in a thread.
2. `request_id=...` is a **keyword argument**: passed by name, not by place. `run_pipeline` has five arguments before
   it, and the route skips `on_event`, so it must use the name.
3. In JS, the closest is an options object: `runPipeline(path, fields, doc, client, { requestId })`.

The test's fake:

```python
lambda *args, **kwargs: time.sleep(0.5)
```

1. `*args` collects the arguments passed by place, as a tuple. In JS: `(...args) =>`.
2. `**kwargs` collects the arguments passed by name, as a dict. JS has no direct match, because JS has no named
   arguments.
3. Without `**kwargs`, a call with `request_id=` fails with "got an unexpected keyword argument".

<a id="py-5"></a>
## PY-5. `with` for a span, and `dict | dict`

```python
with tracer.start_as_current_span("parse") as span:
    doc = parse_pdf(pdf_path)
    span.set_attributes({"parser": doc.parser_name, "pages": len(doc.pages)})
```

1. `start_as_current_span(...)` starts a span and makes it the "current" one. A span started inside it becomes its
   child.
2. `as span` gives you the span, so you can add facts to it.
3. When the block ends, the span ends. On an error, it first marks the span as `ERROR`, then lets the error go on.
4. In JS, it is like this, written for you:

```js
const span = tracer.startSpan("parse");
try { ... } catch (e) { span.recordException(e); throw e; } finally { span.end(); }
```

`done | {"pages": 2}` makes a new dict with the keys of both. On a clash, the right side wins. In JS:
`{ ...done, pages: 2 }`.

<a id="py-6"></a>
## PY-6. A fixture with `scope="module"`

```python
@pytest.fixture(scope="module")
def exporter():
    ...
    yield exporter
    OpenAIInstrumentor().uninstrument()
```

1. A normal fixture runs again for every test. `scope="module"` runs it **once** for the whole file.
2. In Jest: `beforeAll` (before `yield`) and `afterAll` (after `yield`).
3. It is needed here, because a process can set its tracer provider only once.
4. The `spans` fixture has the normal scope. It clears the list before each test, so each test sees only its own
   spans.
