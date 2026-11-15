# Phase 4a3: API key, rate limit and spend cap

In this part, you put three guards in front of the extract route: who may call, how often, and how much money a day.
Each guard runs before the first paid call. Each one is compared to Express, and each has a checkpoint.

This is part 3 of 3 for Phase 4a. It needs 4a2. Every checkpoint in this part is free.

## Words used in this part

Read these first. Route, dependency and status code are from 4a2.

- **API key**: a secret string a client sends with each request, to prove it may call. Example: `X-API-Key: ...`.
- **Header**: a named line of text sent with an HTTP request. Example: `X-API-Key: dev-key-123`.
- **Fail closed**: when a setting is missing, refuse everything. The opposite, "fail open", lets everyone in.
- **Constant-time compare**: a string compare that takes the same time whether the first or the last letter differs.
  It stops an attacker from guessing a key one letter at a time.
- **Rate limit**: the most requests one client may send in a time window. Example: 10 per minute per IP.
- **Sliding window**: count the requests in the last 60 seconds, from now. Not "since the start of the minute".
- **Proxy**: a server between the client and your app. On Cloud Run, Google's front end is one.
- **`X-Forwarded-For`**: a header where proxies write the client's IP. Example: `6.6.6.6, 1.2.3.4`.
- **Spend cap**: the most money the API may spend in one day.
- **Reservation**: money set aside for a request before it runs, at its worst case. The real cost replaces it after.
- **Lock**: lets only one thread at a time change a shared value. Example: two requests adding to `spent`.

## Objectives

By the end of this part you should be able to:

1. Check an API key in a dependency, and say why the server refuses all calls when no key is set.
2. Build a per-IP sliding-window rate limit, and say which IP to trust behind a proxy.
3. Compute the worst cost of one request before any paid call.
4. Reserve that worst case, and give it back with the real cost, even when the request fails.
5. Say what breaks when the API runs on two Cloud Run instances, and which later part fixes it.

## Dependencies

You install nothing new. This part needs:

- 4a2: the app, `run_pipeline`, `conftest.py`.
- 4a: `PLAN_MAX_TOKENS`, and `provider_price` in `core/llm.py`.
- 3a3: the idea of `Budget`: check the worst case, then add the real cost.

## The big picture

Before this part, anyone who knew the URL could spend your OpenRouter money.

After this part:

```text
request -> rate limit (per IP) -> API key -> route checks -> parse
                                                               |
                    reserve worst cost (daily cap) -> plan -> extract -> settle the real cost
```

- **4b** moves the spend count to Postgres, so all instances share one number.
- **4c** keeps the key in Secret Manager, and sets a credit limit on the OpenRouter key itself.
- **4d** keeps the API key on the server side of the UI, never in the browser.

## Remember this

> Every guard runs before money is spent. Check who is calling, how often, and how much this request could cost.
> Reserve the worst case, so ten requests at the same moment cannot pass the cap. Pay the real cost after, in a
> `finally`, so a failed request still counts.
>
> **Who, how often, how much: before the first paid call.**

## Why

**A public URL is found.** Bots scan the internet for open APIs. Without a key, the first one spends your credit.

**A key is not enough.** A user with a valid key can still send a request in a loop by mistake.

**Money needs its own guard.** The rate limit counts requests, not dollars. A 100-page contract costs much more than a
2-page one.

## Design decisions

- **The rate limit runs before the key check.** Wrong-key attempts are counted too, so nobody can guess keys quickly.
  Other option: key first. Guessing would have no limit.
- **No key set on the server means 503 for everyone.** A missing setting must not open the door. Other option: no key
  means no check. One missing line in production would make the API public.
- **`secrets.compare_digest`, not `==`.** It takes the same time for any wrong key. Other option: `==`. It stops at the
  first different letter, and that time can be measured.
- **The IP is the last `X-Forwarded-For` entry.** A client can write any first entry. The proxy adds the real one at
  the end. Other option: the first entry. Anyone could pick a new IP for each request. Check this on Cloud Run in 4c.
- **Reserve the worst case, not "check what was spent".** Ten requests that start at once would all see "spent: $0".
  Other option: check `spent` only. That is the 3a3 lesson again: the check passes, then the calls pass the limit.
- **Settle in `finally`.** A request that fails after the plan call still paid for it. Other option: settle only on
  success. The cap would miss exactly the expensive failures.
- **All state in memory, with a lock.** It is simple, and it is correct on one instance. Other option: Postgres now.
  That is 4b's job. For now, the OpenRouter key's credit limit (4c) is the backup for many instances.
- **The spend cap lives in `core/`.** The pipeline uses it, and `domain/` must not import `api/`. Other option: put it
  in `api/limits.py`. Then the eval runner could not use the pipeline without the web code.
- **Cap reached is 503, rate limit is 429.** 429 means "you, slow down". 503 means "the service is closed for today,
  for everyone". Other option: 429 for both. A client would retry, and the cap would refuse it again.

## Worked example

All numbers are real. Guess before you open each box.

### Round 1: what does one request reserve?

Kubient is 2 pages, 7,590 characters. Its real requests cost $0.00067 and $0.00095. Guess the worst case, with the
4a and 4a2 token limits and 2 retries.

<details><summary>Guess, then open</summary>

```text
7590 chars, worst $0.0282
```

About 30 to 40 times the real cost. Every attempt may write 20,000 tokens, and each retry sends back the last answer.
It looks too careful. But one real call wrote 17,999 tokens (4a2), and a Kimi call once wrote 131,072 (3a3).
</details>

### Round 2: how many requests fit under a $1 cap?

With $1.00 a day and this contract, guess how many requests can run **at the same moment**. Then guess how many can
run in a day.

<details><summary>Guess, then open</summary>

At the same moment: 35 ($1.00 / $0.0282). After each request, the reservation is replaced by the real cost, about
$0.0008. So in a day: more than 1,000 such requests. The worst case limits how many run together, not how many run in
total.
</details>

### Round 3: what does `X-Forwarded-For` look like?

A client sends `X-Forwarded-For: 6.6.6.6` itself. The proxy adds the real address. The app receives
`6.6.6.6, 1.2.3.4`. Guess which one is real.

<details><summary>Guess, then open</summary>

`1.2.3.4`, the last one. The client wrote the first one, so it proves nothing. In Express, this is
`app.set("trust proxy", 1)`: trust one proxy, so take one entry from the right.
</details>

## Project setup

```sh
touch src/docintel/api/auth.py src/docintel/api/limits.py src/docintel/core/spend.py
touch tests/test_limits.py
```

You should now have:

```text
src/docintel/
├── api/
│   ├── auth.py          # new: API key
│   └── limits.py        # new: rate limit, the process's spend cap
└── core/
    └── spend.py         # new: DailySpend
tests/
└── test_limits.py       # new
```

## Step 1: the numbers (your decision)

**Why.** The guards need numbers, and they are yours to set.

| Choice | Evidence |
|---|---|
| Requests per IP per minute | one request takes 6 to 35 s (4a2). A person rarely sends more than a few a minute |
| Daily cap | worst case for a 2-page contract: $0.0282. Real cost: under $0.001 |
| Which IP to trust | Round 3. Cloud Run puts one Google proxy in front |

Write your values in `EXPERIMENTS.md`, under `## API limits (4a2)`.

<details><summary>Reference (open after you write yours)</summary>

10 requests per IP per minute. $1.00 a day. The last `X-Forwarded-For` entry, to be checked on Cloud Run in 4c.
</details>

Update `Settings` in `src/docintel/core/config.py`. Add three lines after `llm_max_attempts`:

```python
    docintel_api_key: SecretStr | None = None  # the key clients send; without it the API refuses
    docintel_daily_cap_usd: float = 1.00
    docintel_rate_limit: int = 10  # requests per IP per minute
```

Make a key, and add it to `.env`:

```sh
uv run python -c "import secrets; print(secrets.token_urlsafe(32))"
```

```text
<43 random characters>
```

```text
DOCINTEL_API_KEY=<the key you just made>
```

The key is a secret, like `sk-or-v1-...`. `.env` is not in git. 4c moves it to Secret Manager.

## Step 2: the API key

**Why.** Only callers with the key may spend money.

Put this in `src/docintel/api/auth.py`:

```python
"""API-key check. Like an Express middleware that runs before the route."""

import secrets
from typing import Annotated

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

from docintel.core.config import get_settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(key: Annotated[str | None, Security(api_key_header)]) -> None:
    expected = get_settings().docintel_api_key
    if expected is None:  # fail closed: a server with no key set answers nobody
        raise HTTPException(503, "the server has no API key set")
    if key is None or not secrets.compare_digest(
        key.encode(), expected.get_secret_value().encode()
    ):
        raise HTTPException(401, "missing or wrong API key")
```

*Python here: [`Security` and `APIKeyHeader`](./py/phase-4a3.md#py-1).*

Here, in order:

1. Read the `X-API-Key` header. `auto_error=False` lets us choose the error message.
2. If the server has no key, refuse with 503.
3. If the key is missing or wrong, refuse with 401. Compare in constant time.

In Express, this is a middleware: `(req, res, next) => req.get("X-API-Key") === key ? next() : res.status(401)...`.

## Step 3: the rate limit

**Why.** One client must not use the whole API.

Put this in `src/docintel/api/limits.py`:

```python
"""Per-IP rate limit, and the one spend cap of this process. Both live in memory."""

import threading
import time
from collections import defaultdict, deque
from functools import lru_cache

from fastapi import HTTPException, Request

from docintel.core.config import get_settings
from docintel.core.spend import DailySpend

WINDOW_S = 60


class RateLimiter:
    """At most `max_requests` per key in the last `window_s` seconds (a sliding window)."""

    def __init__(self, max_requests: int, window_s: float = WINDOW_S, clock=time.monotonic):
        self.max_requests = max_requests
        self.window_s = window_s
        self.clock = clock
        self.hits: dict[str, deque[float]] = defaultdict(deque)
        self.lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = self.clock()
        with self.lock:
            hits = self.hits[key]
            while hits and hits[0] <= now - self.window_s:
                hits.popleft()
            if len(hits) >= self.max_requests:
                return False
            hits.append(now)
            return True


@lru_cache
def get_rate_limiter() -> RateLimiter:
    return RateLimiter(get_settings().docintel_rate_limit)


def client_ip(request: Request) -> str:
    """The caller's IP. Behind Cloud Run, the last X-Forwarded-For entry is the one Google added."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[-1].strip()
    return request.client.host if request.client else "unknown"


def rate_limit(request: Request) -> None:
    if not get_rate_limiter().allow(client_ip(request)):
        raise HTTPException(429, "too many requests", headers={"Retry-After": str(WINDOW_S)})
```

*Python here: [`deque`, `defaultdict` and a lock](./py/phase-4a3.md#py-2).*

Here, in `allow`, for one IP:

1. Read the clock.
2. Drop every request older than the window, from the front of the queue.
3. If the queue is full, say no.
4. If not, add now to the queue, and say yes.

`clock` is an argument, so a test can move time forward with no waiting.

`limits.py` also has `get_spend`, for Step 5. Add it now, at the bottom:

```python
@lru_cache
def get_spend() -> DailySpend:
    return DailySpend(get_settings().docintel_daily_cap_usd)
```

It needs `core/spend.py`, so the app will not start until Step 4 is done.

## Step 4: the spend cap

**Why.** A count of requests is not a count of dollars.

Put this in `src/docintel/core/spend.py`:

```python
"""A daily spend cap, shared by every request of one process."""

import threading
from datetime import UTC, datetime
from functools import lru_cache

from docintel.core.llm import provider_price


class SpendCapReached(RuntimeError):
    pass


class DailySpend:
    """Money for one UTC day. A request reserves its worst case first, then pays the real cost."""

    def __init__(self, cap_usd: float, today=lambda: datetime.now(UTC).date()):
        self.cap_usd = cap_usd
        self.today = today
        self.day = today()
        self.spent = 0.0
        self.reserved = 0.0
        self.lock = threading.Lock()

    def _new_day(self) -> None:
        if self.today() != self.day:
            self.day, self.spent = self.today(), 0.0

    def reserve(self, worst_usd: float) -> None:
        """Stop before a request that could pass the cap."""
        with self.lock:
            self._new_day()
            if self.spent + self.reserved + worst_usd > self.cap_usd:
                raise SpendCapReached(
                    f"spent ${self.spent:.4f} today, reserved ${self.reserved:.4f}, "
                    f"this request could cost ${worst_usd:.4f}, cap ${self.cap_usd:.2f}"
                )
            self.reserved += worst_usd

    def settle(self, worst_usd: float, cost_usd: float) -> None:
        """Give back the reservation, and count what was really paid."""
        with self.lock:
            self.reserved -= worst_usd
            self.spent += cost_usd


@lru_cache
def price(model: str) -> tuple[float, float]:
    """The provider's price per token, read once per process. Free, no key needed."""
    return provider_price(model)
```

*Python here: [`lambda` as a default clock](./py/phase-4a3.md#py-3).*

Here, we:

1. Start a new day at midnight UTC. `spent` goes back to 0, and the reservations of running requests stay.
2. In `reserve`, refuse if spent plus reserved plus this worst case passes the cap.
3. In `settle`, give back the reservation, and add the real cost.
4. Read the provider's price once per process. It is the same price as in 3a3 and 4a.

## Step 5: reserve before the first paid call

**Why.** The pipeline is where the money is spent, so it is where the cap is checked.

Update the imports at the top of `src/docintel/domain/pipeline.py`. Add these two, and `PLAN_MAX_TOKENS`:

```python
from docintel.core.config import get_settings
from docintel.core.spend import DailySpend, price
from docintel.domain.planner.planner import PLAN_MAX_TOKENS, pick, plan_request
```

Add two numbers below `EXTRACT_MAX_TOKENS` in the same file:

```python
CHARS_PER_TOKEN = 3  # a low guess, so the worst case is high
PROMPT_TOKENS = 1_500  # the v1 system prompt and the retry message, with room to spare
```

Add `worst_cost` above `run_pipeline`:

```python
def worst_cost(text: str, in_price: float, out_price: float, retries: int = 2) -> float:
    """The most one request can cost: the plan, then every extraction attempt at its limit."""
    base = len(text) / CHARS_PER_TOKEN + PROMPT_TOKENS
    tokens_in = sum(base + k * EXTRACT_MAX_TOKENS for k in range(retries + 1))  # a retry resends
    tokens_out = (retries + 1) * EXTRACT_MAX_TOKENS
    plan = PROMPT_TOKENS * in_price + PLAN_MAX_TOKENS * out_price
    return plan + tokens_in * in_price + tokens_out * out_price
```

Here, for each of the 3 attempts, we count:

1. The contract and the prompts, at 3 characters per token. That is a low guess, so the cost is high.
2. Each retry sends back the last answer, so attempt `k` sends `k` more full answers.
3. Every attempt writes up to `EXTRACT_MAX_TOKENS`. The plan call adds its own worst case.

Now replace `run_pipeline` with this version:

```python
def run_pipeline(
    pdf_path: Path, request: str, client=None, spend: DailySpend | None = None
) -> ExtractResult:
    """Parse, reserve the worst cost, plan, extract with retries, check, keep the asked fields."""
    start = time.perf_counter()
    doc = parse_pdf(pdf_path)
    spend = spend or DailySpend(float("inf"))
    worst = worst_cost(doc.text, *price(get_settings().docintel_model))
    spend.reserve(worst)  # raises SpendCapReached before any paid call
    costs = []
    try:
        plan, plan_call = plan_request(request, client=client)
        costs.append(plan_call.cost_usd if plan_call else 0.0)
        if not plan.fields:
            raise NothingToExtract(f"no known field in the request; unknown: {plan.unknown}")
        attempts = extract_with_retry(doc.text, client=client, max_tokens=EXTRACT_MAX_TOKENS)
        costs += [a.result.cost_usd for a in attempts]
    finally:
        spend.settle(worst, sum(c or 0.0 for c in costs))
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

*Python here: [`try` and `finally`](./py/phase-4a3.md#py-4).*

Here, the new part, in order:

1. Parse. It is free (pypdf) or local (Docling).
2. Compute the worst cost, and reserve it. If the cap would be passed, `SpendCapReached` stops the request here.
3. Plan and extract, and collect the cost of each call.
4. In `finally`, settle: give back the reservation, and add what was really paid. This runs on success and on
   failure.

Checkpoint (free):

```sh
uv run python - <<'EOF'
from pathlib import Path

from docintel.core.spend import price
from docintel.domain.pipeline import parse_pdf, worst_cost

doc = parse_pdf(Path("data/kubient.pdf"))
print(len(doc.text), "chars,", f"worst ${worst_cost(doc.text, *price('deepseek/deepseek-v4-flash')):.4f}")
EOF
```

```text
7590 chars, worst $0.0282
```

## Step 6: put the guards on the route

**Why.** The guards exist. Now the route must use them.

Update the imports at the top of `src/docintel/api/routes.py`:

```python
from docintel.api.auth import require_api_key
from docintel.api.limits import get_spend, rate_limit
from docintel.api.schemas import Health
from docintel.core.spend import DailySpend, SpendCapReached
```

Then update the start of `extract` in the same file:

```python
@router.post("/v1/extract", dependencies=[Depends(rate_limit), Depends(require_api_key)])
async def extract(
    pdf: UploadFile,
    client: Annotated[object, Depends(get_llm_client)],
    spend: Annotated[DailySpend, Depends(get_spend)],
    request: Annotated[str, Form()] = "",
) -> ExtractResult:
```

Pass `spend` to the pipeline:

```python
                run_in_threadpool(run_pipeline, path, request, client, spend), timeout=TIMEOUT_S
```

And add one more error at the end of the `except` list:

```python
        except SpendCapReached as e:
            raise HTTPException(503, f"daily spend cap reached: {e}") from None
```

Here, `dependencies=[...]` runs the two guards in order, before the route body. In Express:
`router.post("/v1/extract", rateLimit, requireApiKey, handler)`. `/health` has no guards, so Cloud Run can always reach
it.

Checkpoint 1 (free): the key and the rate limit. Start the server with a limit of 3, so it is quick to reach:

```sh
DOCINTEL_API_KEY=dev-key-123 DOCINTEL_RATE_LIMIT=3 make serve
```

In a second terminal. Guess the four numbers of the last line first:

```sh
curl -s -w " %{http_code}\n" -F pdf=@data/kubient.pdf -F request=parties localhost:8000/v1/extract
curl -s -w " %{http_code}\n" -H "X-API-Key: nope" -F pdf=@data/kubient.pdf -F request=parties localhost:8000/v1/extract
for i in 1 2 3 4; do curl -s -o /dev/null -w "%{http_code} " -F pdf=@data/kubient.pdf -F request=parties localhost:8000/v1/extract; done; echo
```

```text
{"detail":"missing or wrong API key"} 401
{"detail":"missing or wrong API key"} 401
401 429 429 429
```

The two refused requests at the top counted too. So only one more fits, and it is refused for its key.

Checkpoint 2 (free): the cap. Stop the server, and start it with a cap smaller than one worst case:

```sh
DOCINTEL_API_KEY=dev-key-123 DOCINTEL_DAILY_CAP_USD=0.01 make serve
```

```sh
curl -s -w " %{http_code}\n" -H "X-API-Key: dev-key-123" -F pdf=@data/kubient.pdf -F request=parties localhost:8000/v1/extract
```

```text
{"detail":"daily spend cap reached: spent $0.0000 today, reserved $0.0000, this request could cost $0.0282, cap $0.01"} 503
```

No call was made. The planner did not run, because the reservation comes first.

## Step 7: a small test

**Why.** These rules protect the money. A broken one must fail a test, not show up on the bill.

First, update the `api` fixture in `tests/conftest.py`. It now sends a key, uses its own spend cap, and never reads
the price from the network.

<details><summary>The new <code>tests/conftest.py</code></summary>

```python
"""Shared fakes for the API tests: a fake OpenRouter and a fake parser. No network, no cost."""

import json

import httpx2
import pytest
from fastapi.testclient import TestClient
from openai import OpenAI

from docintel.api import routes
from docintel.api.app import app
from docintel.api.limits import get_rate_limiter, get_spend
from docintel.core.config import get_settings
from docintel.core.spend import DailySpend
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


API_KEY = "test-key"


@pytest.fixture
def api(monkeypatch):
    """`api(plan)`: a TestClient whose model answers with `plan`. `api.sent` lists the calls."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-test")
    monkeypatch.setenv("DOCINTEL_API_KEY", API_KEY)
    get_settings.cache_clear()
    get_rate_limiter.cache_clear()
    monkeypatch.setattr(pipeline, "parse_pdf", lambda path: from_pages([CONTRACT], 0.0, 1, "pypdf"))
    monkeypatch.setattr(pipeline, "price", lambda model: (1e-6, 1e-6))  # no network in tests
    spend = DailySpend(1.0)
    sent = []

    def use(plan: dict, key: str | None = API_KEY) -> TestClient:
        app.dependency_overrides[routes.get_llm_client] = lambda: fake_llm(plan, sent)
        app.dependency_overrides[get_spend] = lambda: spend
        return TestClient(app, headers={"X-API-Key": key} if key else {})

    use.sent, use.spend = sent, spend
    yield use
    app.dependency_overrides.clear()
    get_settings.cache_clear()
    get_rate_limiter.cache_clear()
```
</details>

The test names say what is protected: no key or a wrong key is refused, a server with no key answers nobody, health
needs no key, a fourth request is refused, the window slides, the cap stops a request before any call, a failed
request gives back its reservation, a new day starts at zero, and the IP is the last forwarded entry.

<details><summary>Put this in <code>tests/test_limits.py</code></summary>

```python
"""The guards: API key, rate limit, daily spend cap. Fakes come from `conftest.py`."""

import datetime as dt

import pytest
from starlette.requests import Request

from docintel.api.limits import RateLimiter, client_ip
from docintel.core.config import get_settings
from docintel.core.spend import DailySpend, SpendCapReached

PDF = b"%PDF-1.4 fake"
PLAN = {"fields": ["parties"], "unknown": []}


def post(client):
    return client.post("/v1/extract", files={"pdf": ("c.pdf", PDF)}, data={"request": "parties"})


def test_no_key_or_a_wrong_key_is_refused(api):
    assert post(api(PLAN, key=None)).status_code == 401
    assert post(api(PLAN, key="wrong")).status_code == 401
    assert api.sent == []


def test_a_server_with_no_key_set_answers_nobody(api, monkeypatch):
    monkeypatch.delenv("DOCINTEL_API_KEY")
    get_settings.cache_clear()
    assert post(api(PLAN)).status_code == 503


def test_the_health_check_needs_no_key(api):
    assert api(PLAN, key=None).get("/health").status_code == 200


def test_too_many_requests_from_one_ip(api, monkeypatch):
    monkeypatch.setenv("DOCINTEL_RATE_LIMIT", "2")
    get_settings.cache_clear()
    client = api(PLAN)
    assert [post(client).status_code for _ in range(3)] == [200, 200, 429]


def test_the_window_slides():
    now = [0.0]
    limiter = RateLimiter(max_requests=1, window_s=60, clock=lambda: now[0])
    assert limiter.allow("1.2.3.4")
    assert not limiter.allow("1.2.3.4")
    assert limiter.allow("5.6.7.8")  # each IP has its own count
    now[0] = 61.0
    assert limiter.allow("1.2.3.4")


def test_the_cap_stops_a_request_before_any_paid_call(api):
    api.spend.cap_usd = 0.0001
    assert post(api(PLAN)).status_code == 503
    assert api.sent == []


def test_a_failed_request_gives_back_its_reservation(api):
    response = post(api({"fields": [], "unknown": ["payment terms"]}))
    assert response.status_code == 422
    assert api.spend.reserved == pytest.approx(0.0)
    assert api.spend.spent == pytest.approx(0.001)  # the plan call was paid


def test_a_new_day_starts_at_zero():
    day = [dt.date(2026, 11, 15)]
    spend = DailySpend(1.0, today=lambda: day[0])
    spend.reserve(0.9)
    spend.settle(0.9, 0.9)
    with pytest.raises(SpendCapReached):
        spend.reserve(0.2)
    day[0] = dt.date(2026, 11, 16)
    spend.reserve(0.2)


def test_the_ip_is_the_last_forwarded_entry():
    scope = {"type": "http", "headers": [(b"x-forwarded-for", b"6.6.6.6, 1.2.3.4")], "client": None}
    assert client_ip(Request(scope)) == "1.2.3.4"  # the first entry can be written by anyone
```
</details>

Checkpoint:

```sh
uv run pytest tests/test_limits.py tests/test_api.py -q
make test
make lint
```

```text
................                                                         [100%]
16 passed in 0.17s
```

Your project structure should now look like this:

```text
src/docintel/
├── api/
│   ├── auth.py              # require_api_key
│   ├── limits.py            # RateLimiter, client_ip, rate_limit, get_spend
│   └── routes.py            # guards on /v1/extract
├── core/
│   ├── config.py            # + api key, daily cap, rate limit
│   └── spend.py             # DailySpend, price
└── domain/pipeline.py       # worst_cost, reserve and settle
tests/
├── conftest.py              # key, spend, no network for the price
└── test_limits.py
```

<details><summary>Complete <code>src/docintel/api/limits.py</code></summary>

```python
"""Per-IP rate limit, and the one spend cap of this process. Both live in memory."""

import threading
import time
from collections import defaultdict, deque
from functools import lru_cache

from fastapi import HTTPException, Request

from docintel.core.config import get_settings
from docintel.core.spend import DailySpend

WINDOW_S = 60


class RateLimiter:
    """At most `max_requests` per key in the last `window_s` seconds (a sliding window)."""

    def __init__(self, max_requests: int, window_s: float = WINDOW_S, clock=time.monotonic):
        self.max_requests = max_requests
        self.window_s = window_s
        self.clock = clock
        self.hits: dict[str, deque[float]] = defaultdict(deque)
        self.lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = self.clock()
        with self.lock:
            hits = self.hits[key]
            while hits and hits[0] <= now - self.window_s:
                hits.popleft()
            if len(hits) >= self.max_requests:
                return False
            hits.append(now)
            return True


@lru_cache
def get_rate_limiter() -> RateLimiter:
    return RateLimiter(get_settings().docintel_rate_limit)


@lru_cache
def get_spend() -> DailySpend:
    return DailySpend(get_settings().docintel_daily_cap_usd)


def client_ip(request: Request) -> str:
    """The caller's IP. Behind Cloud Run, the last X-Forwarded-For entry is the one Google added."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[-1].strip()
    return request.client.host if request.client else "unknown"


def rate_limit(request: Request) -> None:
    if not get_rate_limiter().allow(client_ip(request)):
        raise HTTPException(429, "too many requests", headers={"Retry-After": str(WINDOW_S)})
```
</details>

<details><summary>Complete <code>src/docintel/domain/pipeline.py</code></summary>

```python
"""One request, start to end: plan, parse, extract with retries, check. Typed in, typed out."""

import time
import uuid
from pathlib import Path

from pydantic import BaseModel

from docintel.core.config import get_settings
from docintel.core.spend import DailySpend, price
from docintel.domain.extract.retry import extract_with_retry, final_answer
from docintel.domain.parse.base import ParsedDoc
from docintel.domain.parse.docling_parser import parse_docling_ocr
from docintel.domain.parse.pypdf_parser import parse_pypdf
from docintel.domain.planner.planner import PLAN_MAX_TOKENS, pick, plan_request
from docintel.domain.validate.issues import Issue
from docintel.domain.validate.rules import check_answer

TEXT_CHARS_PER_PAGE = 200  # below this, the PDF is a scan; the thinnest dev contract has 870
MAX_PAGES = 100  # the longest dev contract has 82
MAX_SCAN_PAGES = 10  # Docling OCR reads about 7 to 10 s per page on an 8 GB Mac
EXTRACT_MAX_TOKENS = 20_000  # the largest real extraction answer used 17,999


CHARS_PER_TOKEN = 3  # a low guess, so the worst case is high
PROMPT_TOKENS = 1_500  # the v1 system prompt and the retry message, with room to spare


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


def worst_cost(text: str, in_price: float, out_price: float, retries: int = 2) -> float:
    """The most one request can cost: the plan, then every extraction attempt at its limit."""
    base = len(text) / CHARS_PER_TOKEN + PROMPT_TOKENS
    tokens_in = sum(base + k * EXTRACT_MAX_TOKENS for k in range(retries + 1))  # a retry resends
    tokens_out = (retries + 1) * EXTRACT_MAX_TOKENS
    plan = PROMPT_TOKENS * in_price + PLAN_MAX_TOKENS * out_price
    return plan + tokens_in * in_price + tokens_out * out_price


def run_pipeline(
    pdf_path: Path, request: str, client=None, spend: DailySpend | None = None
) -> ExtractResult:
    """Parse, reserve the worst cost, plan, extract with retries, check, keep the asked fields."""
    start = time.perf_counter()
    doc = parse_pdf(pdf_path)
    spend = spend or DailySpend(float("inf"))
    worst = worst_cost(doc.text, *price(get_settings().docintel_model))
    spend.reserve(worst)  # raises SpendCapReached before any paid call
    costs = []
    try:
        plan, plan_call = plan_request(request, client=client)
        costs.append(plan_call.cost_usd if plan_call else 0.0)
        if not plan.fields:
            raise NothingToExtract(f"no known field in the request; unknown: {plan.unknown}")
        attempts = extract_with_retry(doc.text, client=client, max_tokens=EXTRACT_MAX_TOKENS)
        costs += [a.result.cost_usd for a in attempts]
    finally:
        spend.settle(worst, sum(c or 0.0 for c in costs))
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

## Break it on purpose

Both breaks are free. Put the code back after each one.

**Break 1: settle only on success.** In `run_pipeline`, replace `finally:` with `except Exception:` and `raise`, and
move the `settle` line below the `try` block. Guess: which test fails?

<details><summary>What you see</summary>

```text
FAILED tests/test_limits.py::test_a_failed_request_gives_back_its_reservation
```

The request with only unknown fields failed after the plan call. Its reservation was never given back. After 35 such
requests, the cap would refuse everyone for the rest of the day.
</details>

**Break 2: compare with `==`.** In `require_api_key`, replace the `compare_digest` condition with
`if key != expected.get_secret_value():`. Guess: which test fails?

<details><summary>What you see</summary>

```text
9 passed
```

None. A timing attack cannot be seen in a unit test, because the difference is a few nanoseconds. This rule is kept by
code review, not by a test. Put `compare_digest` back.
</details>

## Experiment

This part runs no experiment. The guards change who may call and how much they may spend, not the answers. Your
Step 1 numbers are in `EXPERIMENTS.md`, next to the 4a2 limits.

## Gotchas

- **Each Cloud Run instance has its own counts.** Two instances mean two caps and two rate limits. 4b fixes the spend
  count with Postgres. The OpenRouter credit limit in 4c is the hard backup.
- **A restart forgets today's spend.** The memory is gone. 4b fixes this too.
- **The rate limit counts refused requests.** Checkpoint 1 shows it. That is on purpose.
- **A timed-out request still settles.** Its thread finishes, and `finally` adds the real cost.
- **A request that fails inside `extract_with_retry` loses the cost of its finished attempts.** The attempts list
  never comes back. The reservation is still returned. The OpenRouter credit limit covers this gap.

## Explain back, then commit

Explain to Claude in a few sentences:

- `auth.py`: why 503 when no key is set, and why `compare_digest`.
- `limits.py`: how the sliding window works, step by step. Which IP is trusted, and why.
- `spend.py`: reserve and settle, with the numbers from Round 1 and Round 2.
- `pipeline.py`: why the reservation comes after parsing and before planning. What `finally` protects.
- Why `spend.py` is in `core/`, not in `api/`.
- What breaks on two instances, and which part fixes it.

Then:

```sh
git status
git add src/docintel/api src/docintel/core/config.py src/docintel/core/spend.py src/docintel/domain/pipeline.py tests/conftest.py tests/test_limits.py EXPERIMENTS.md
git commit -m "phase 4a3: API key, rate limit, spend cap"
```

## Conclusion

The API now refuses strangers, slows down loops, and stops spending before the daily cap. Go back through the
objectives and check each one without notes. Then answer:

1. Ten requests for a 100-page contract arrive at the same second, with a $1 cap. What happens to each one?
2. Why is "reserve the worst case" safer than "check what was spent", even with only one instance?

Looking for more challenges? Try these (optional):

1. Add `X-RateLimit-Remaining` to every answer, like many public APIs do.
2. Add a second, smaller cap per API key, so one client cannot use the whole day.

Checklist (`../PLAN.md`): **Auth, rate limits, spend caps, secrets**. **Retries, timeouts, degradation, idempotency**
(the reservation is given back on every path). Phase 4a is done. Next: 4b.
