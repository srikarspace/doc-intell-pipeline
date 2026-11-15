# Python for Phase 4a3

This file explains the new Python in Part 4a3. Read one section when the main doc links to it. `Annotated` and
`Depends` are in 4a2 ([PY-2](./phase-4a2.md#py-2)).

<a id="py-1"></a>
## PY-1. `Security` and `APIKeyHeader`

```python
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(key: Annotated[str | None, Security(api_key_header)]) -> None:
```

1. `APIKeyHeader` reads one header. It also adds an "Authorize" button to `/docs`.
2. `Security(...)` is `Depends(...)` for security things. FastAPI shows it on `/docs`.
3. `auto_error=False` gives `None` when the header is missing, instead of an automatic 403. We send our own 401.
4. The function returns nothing. If it does not raise, the route runs. In Express: a middleware that calls `next()`.

<a id="py-2"></a>
## PY-2. `deque`, `defaultdict` and a lock

```python
self.hits: dict[str, deque[float]] = defaultdict(deque)
self.lock = threading.Lock()
...
with self.lock:
    hits = self.hits[key]
    while hits and hits[0] <= now - self.window_s:
        hits.popleft()
```

1. `deque` is a list that is fast to change at both ends. `popleft()` is `shift()` in JS, but it is fast.
2. `defaultdict(deque)` makes an empty `deque` the first time a key is read. In JS:
   `hits[key] ??= []`.
3. FastAPI runs the guard functions in threads. Two threads could change the same `deque` at once. `with self.lock:`
   lets only one in at a time. Node has one thread for JS, so Express code rarely needs this.

<a id="py-3"></a>
## PY-3. `lambda` as a default clock

```python
def __init__(self, cap_usd: float, today=lambda: datetime.now(UTC).date()):
```

1. `lambda: ...` is a small function with no name. In JS: `() => new Date()`.
2. The default is a function, not a date. So each call to `self.today()` reads the date again.
3. A test passes its own function, and changes the day without waiting for midnight.

<a id="py-4"></a>
## PY-4. `try` and `finally`

```python
spend.reserve(worst)
costs = []
try:
    plan, plan_call = plan_request(request, client=client)
    ...
finally:
    spend.settle(worst, sum(c or 0.0 for c in costs))
```

The `finally` block runs when the `try` block ends, whether it returned normally or raised. The error still goes up
after `finally`. It is the same as `try { } finally { }` in JS.

`reserve` is before `try` on purpose. If `reserve` raises, there is nothing to give back.
