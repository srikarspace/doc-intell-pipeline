# Python for Phase 4a2

This file explains the new Python in Part 4a2. Read one section when the main doc links to it. `run_in_threadpool`
and `wait_for` are in 4a ([PY-5](./phase-4a.md#py-5)).

<a id="py-1"></a>
## PY-1. A type alias, and `tuple` in a model

```python
Rect = tuple[float, float, float, float]  # x0, y0, x1, y1


class Highlight(BaseModel):
    page_size: tuple[float, float]
    rects: list[Rect]
```

1. `Rect = ...` gives a long type a short name. In TypeScript: `type Rect = [number, number, number, number]`.
2. `tuple[float, float]` is exactly two numbers. Pydantic checks the count.
3. In JSON, a tuple becomes a list: `[595.0, 842.0]`.

<a id="py-2"></a>
## PY-2. `Callable`, and a lambda that calls a callback

```python
Emit = Callable[[str, dict], None]


def no_events(event: str, data: dict) -> None:
    pass

...
on_attempt=lambda a: on_event("attempt", {"n": a.attempt_no, "errors": len(a.errors)}),
```

1. `Callable[[str, dict], None]` is "a function that takes a string and a dict, and returns nothing". In TypeScript:
   `(event: string, data: object) => void`.
2. `no_events` is the default, so the pipeline can always call `on_event` without an `if`.
3. The `lambda` turns one `Attempt` into one event. In JS: `a => onEvent("attempt", { n: a.attemptNo, ... })`.

<a id="py-3"></a>
## PY-3. A queue between a thread and `async`

```python
queue: asyncio.Queue = asyncio.Queue()
loop = asyncio.get_running_loop()

def emit(event: str, data: dict) -> None:  # runs in the pipeline's thread
    loop.call_soon_threadsafe(queue.put_nowait, (event, data))
```

1. `asyncio.Queue` is a line of items for `async` code. `await queue.get()` waits for the next one.
2. The pipeline runs in another thread. `asyncio` objects must only be touched from the event loop's thread.
3. `loop.call_soon_threadsafe(f, x)` asks the event loop to run `f(x)` soon, on its own thread. It is the safe hand-over.

Node has no such problem, because all JS runs on one thread. A worker thread there sends messages with
`postMessage`, which is the same idea.

<a id="py-4"></a>
## PY-4. An `async` generator

```python
async def events():
    task = asyncio.create_task(work())
    try:
        while (item := await queue.get()) is not None:
            name, payload = item
            yield {"event": name, "data": json.dumps(payload)}
    finally:
        await task
        shutil.rmtree(folder, ignore_errors=True)
```

1. A function with `async def` and `yield` is an async generator. `EventSourceResponse` reads it one item at a time,
   and sends each item as soon as it is yielded. In JS: `async function*` with `for await`.
2. `asyncio.create_task(work())` starts `work` now, side by side. In JS: calling an async function without `await`.
3. `(item := await queue.get())` takes an item and names it in the same line. It is the "walrus" operator.
4. `finally` runs when the stream ends, also if the browser leaves early.
