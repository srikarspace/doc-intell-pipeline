# Phase 1a2: the LLM client

In this part, you build `call_llm`: one function that sends messages and your 1a schema to
OpenRouter, checks the answer, and logs the call in DuckDB. You build it one piece at a time,
with a checkpoint after each piece. At the end you make one real call, then test the rules with
a fake server.

## Words used in this part

Read these first. 1a words (schema, strict mode, enforcement, validation) are used again.

- **Messages**: the list you send to the model. Each item has a `role` (`system` or `user`) and
  `content`. Example: `[{"role": "user", "content": "Who are the parties?"}]`.
- **Token**: a small piece of text the model reads or writes. About 4 characters. You pay per
  token.
- **OpenRouter**: one API in front of many models and many providers. One key, one bill.
- **Endpoint**: one provider running one model. One model can have many endpoints. Example:
  Qwen3-235B runs on DeepInfra, Nebius, Parasail and others.
- **SDK**: a library that wraps an HTTP API in functions. Example: the `openai` package.
- **Rate limit, 429**: the server says "too many requests, wait". 429 is its HTTP status code.
- **400**: the server says "your request is wrong". Sending it again gives the same answer.
- **Retry, backoff**: send the same request again after it failed. Backoff means you wait longer
  each time: 1 s, then 2 s, then 4 s.
- **Latency**: how long one call takes, in milliseconds (ms).
- **Usage, cost**: how many tokens the call used, and what it cost in US dollars.
- **Fake server (mock)**: code that answers like the real server, with no network. Like `nock` or
  `msw` in JS.

## Objectives

By the end of this part you should be able to:

1. Trace one `call_llm` call, step by step, from messages to a row in `llm_calls`.
2. Say which errors the client retries, which it does not, and why.
3. Explain why bad JSON is returned as a result and not raised.
4. Find any call you made in `llm_calls`, with its tokens, cost and latency.
5. Test retry rules with a fake server, with no key and no cost.

## Dependencies

You install nothing new. `openai`, `pydantic`, `pydantic-settings` and `duckdb` are installed.
`httpx2` came with `openai`: it is the HTTP library the SDK uses inside.

This part needs 1a: `Strict` and your field models in `fields.py`, `get_settings` in
`config.py`, and `response_format` in `llm.py`.

You need a real key in `.env` for Step 6. Put a small credit limit on the key in the OpenRouter
settings. The live call costs a tiny fraction of a cent.

## The big picture

Before this part, the pipeline knows the shape of an answer, but has never asked a model.

After this part, `call_llm(messages, schema)` returns an `LLMResult`: raw text, parsed answer or
error, tokens, cost, latency, provider and attempts. Every call can be a row in `llm_calls`.

- 1b calls it with your prompt and `ContractFields` for one contract.
- 1c calls it for every dev contract, with a `run_id`.
- 2b reads `error`, sends it back to the model, and calls it again.

## Remember this

> A bad answer is a result, not a crash: `call_llm` returns the Pydantic error so 2b can use it.
> It retries only what waiting can fix: network errors, timeouts and 429. Every call is logged
> with its cost and latency, so every number later traces back to a real call.
>
> **Return bad answers, retry only what waiting fixes, log every call.**

## Why

**A bad answer is data.** In 2b we send the Pydantic error back to the model and ask it to fix
the answer. That only works if the client returns the error. 2a also counts how often each kind
of error happens.

**Some errors fix themselves, some never do.** A 429 or a dropped connection may work one second
later. A 400 or a bad key will fail the same way forever. Retrying those only wastes time.

**Every number needs a cost and a time.** The README must say what one contract costs and how
long it takes. If every call is in `llm_calls`, those numbers are one SQL query.

## Design decisions

- **`call_llm` returns a result object.** Bad JSON gives `parsed=None` and an `error` string.
  Other option: raise an exception. Then 2b must catch it to read the error.
- **Our own retry loop, only for network errors and 429.** The SDK retries by itself on 408, 409,
  429 and 5xx (Round 2). We turn that off (`max_retries=0`) so we can count attempts. Other
  option: keep the SDK retries. Then `attempts` in `llm_calls` would be wrong.
- **`con` and `client` are parameters.** `core/` does not import `evals/`. In Phase 4 the API
  logs to Postgres instead. Tests pass a fake `client`. Other option: open DuckDB and make the
  client inside `call_llm`. Then core code depends on eval code, and tests must patch the SDK.
- **`llm_calls` keeps the answer, not the prompt.** A contract is about 50,000 characters. 100
  calls would store 5 MB of copies of text we already have. Other option: store the prompt too.
  Easier to debug, much bigger file.
- **`temperature=0`.** The model picks its most likely answer, so runs change less. Other option:
  the default. More random answers, noisier evals.

## Worked example

Guess before you open each box.

### Round 1: one endpoint has no structured output

These are the real endpoints for `qwen/qwen3-235b-a22b-2507` on OpenRouter today:

```
GMICloud   fp8  structured
DeepInfra  fp8  structured
Parasail   fp8  structured
Venice     fp8  structured
Nebius     fp8  structured
Google          structured
Google          -
```

You send `response_format` without `require_parameters`. OpenRouter picks the last one. What
happens?

<details><summary>Guess, then open</summary>

The request still works. That endpoint ignores `response_format`. The model answers with free
text, maybe JSON, maybe with a sentence in front. Pydantic then fails, and you blame the prompt.

`"provider": {"require_parameters": True}` tells OpenRouter: only use endpoints that support every
parameter I sent. So the last endpoint is never picked.
</details>

### Round 2: the SDK's own retries

You make an `OpenAI` client with the default settings. The fake server always answers 429. How
many requests reach the server before you see an error?

<details><summary>Guess, then open</summary>

Three. The SDK's default is `max_retries=2`, and it retries 429 by itself. This is the real
output of that test:

```
RateLimitError 3
```

Your code made one call and saw one error. If we counted attempts in our code, we would write 1.
The real number is 3. That is why we set `max_retries=0` and do the retries ourselves.
</details>

## Project setup

Create the test file:

```sh
$ touch tests/test_llm.py
```

You should now have:

```
src/docintel/
├── core/
│   ├── config.py          from 1a
│   └── llm.py             response_format from 1a; this part adds the client
├── domain/schema/
│   └── fields.py          from 1a
└── evals/
    ├── datasets.py
    └── store.py
tests/
├── test_llm.py            empty
└── test_schema.py         from 1a
```

## Step 1: make the SDK client

**Why.** Every call needs a client with the key, the URL and the timeout.

Update the imports at the top of `src/docintel/core/llm.py`:

```python
"""Thin OpenRouter client: messages + Pydantic model in, LLMResult out. Every call is logged."""

import time
import uuid
from dataclasses import dataclass

import duckdb
import openai
from openai import OpenAI
from pydantic import BaseModel, ValidationError

from docintel.core.config import get_settings
```

`response_format` from 1a stays below the imports. Add to the bottom of
`src/docintel/core/llm.py`:

```python
def make_client() -> OpenAI:
    s = get_settings()
    return OpenAI(
        api_key=s.openrouter_api_key.get_secret_value(),
        base_url=s.openrouter_base_url,
        timeout=s.llm_timeout_s,
        max_retries=0,  # we retry ourselves, and only on network errors and 429
    )
```

Here, we:

1. Use the `openai` SDK, but point `base_url` at OpenRouter. OpenRouter speaks the same API.
2. Take the real key out of the `SecretStr` only here, at the last moment.
3. Turn off the SDK's own retries (Round 2).

Some imports are not used yet. The next steps use them.

Checkpoint:

```sh
$ uv run python -c "
from docintel.core.llm import make_client
c = make_client()
print(c.base_url, c.max_retries, c.timeout)"
https://openrouter.ai/api/v1/ 0 120.0
```

## Step 2: the result, and the check

**Why.** Every caller needs the same 9 facts about a call, and the answer must be checked in one
place.

Add to the bottom of `src/docintel/core/llm.py`:

```python
@dataclass
class LLMResult[T: BaseModel]:
    raw_text: str
    parsed: T | None  # None when the text did not fit the schema
    error: str | None  # the Pydantic error, so 2b can send it back to the model
    usage: dict
    cost_usd: float | None
    latency_ms: int
    model: str
    provider: str | None
    attempts: int


def _parse[T: BaseModel](schema: type[T], raw_text: str) -> tuple[T | None, str | None]:
    try:
        return schema.model_validate_json(raw_text), None
    except ValidationError as e:
        return None, str(e)
```

*Python here: [`@dataclass`](./py/phase-1a2.md#py-1) ·
[generics with `[T: BaseModel]`](./py/phase-1a2.md#py-2) ·
[`try` / `except`](./py/phase-1a2.md#py-3).*

Here, we:

1. Make `LLMResult`, a simple record with 9 fields. `T` is the schema class, so `parsed` has the
   right type for each call.
2. In `_parse`, read the JSON and check it in one step with `model_validate_json`.
3. On success, return `(answer, None)`. On failure, return `(None, error text)`. Never raise.

Checkpoint. Guess which of the three fail, and why:

```sh
$ uv run python -c "
from docintel.core.llm import _parse
from docintel.domain.schema.fields import Clause
print(_parse(Clause, '{\"quotes\": [\"shall not compete\"], \"found\": true}'))
print(_parse(Clause, '{\"quotes\": [], \"found\": \"yes\"}')[1])
print(_parse(Clause, '{\"quotes\": []}')[1])"
(Clause(quotes=['shall not compete'], found=True), None)
1 validation error for Clause
found
  Input should be a valid boolean [type=bool_type, input_value='yes', input_type=str]
    For further information visit https://errors.pydantic.dev/2.14/v/bool_type
1 validation error for Clause
found
  Field required [type=missing, input_value={'quotes': []}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.14/v/missing
```

Use one of your own field models if you have no `Clause`. The first is fine. The second has a
wrong type (1a, Round 2). The third has a missing key.

## Step 3: send, with retries

**Why.** One slow second at OpenRouter must not kill a run of 50 contracts.

Add to the bottom of `src/docintel/core/llm.py`:

```python
RETRYABLE = (openai.APIConnectionError, openai.RateLimitError)  # timeouts are connection errors


def _send(client, messages, schema, model, max_attempts, backoff_s):
    """One request, tried again only on RETRYABLE errors. Returns (response, attempts)."""
    for attempt in range(1, max_attempts + 1):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                response_format=response_format(schema),
                extra_body={"provider": {"require_parameters": True}},
                temperature=0,
            )
            return resp, attempt
        except RETRYABLE:
            if attempt == max_attempts:
                raise
            time.sleep(backoff_s * 2 ** (attempt - 1))  # 1 s, 2 s, 4 s
```

*Python here: [`except` with a tuple, and `raise`](./py/phase-1a2.md#py-3) ·
[`time.sleep` and `time.perf_counter`](./py/phase-1a2.md#py-4).*

Here, we:

1. Try up to `max_attempts` times (4 by default, from `config.py`).
2. Send the messages, the `response_format` from 1a, and `require_parameters` (Round 1).
   `extra_body` adds keys the SDK does not know about. OpenRouter reads them.
3. On success, return the response and the attempt number.
4. On a network error, a timeout or a 429, wait and try again. The wait doubles each time.
5. On the last attempt, `raise` the error to the caller.
6. Any other error (400 bad request, 401 bad key) is not caught. It goes up at once. Sending
   the same bad request again cannot fix it.

Checkpoint. Guess the three answers:

```sh
$ uv run python -c "
import openai
from docintel.core.llm import RETRYABLE
print(issubclass(openai.APITimeoutError, RETRYABLE), issubclass(openai.RateLimitError, RETRYABLE), issubclass(openai.BadRequestError, RETRYABLE))"
True True False
```

A timeout is a kind of connection error in the SDK, so it is retried too. A 400 is not.

## Step 4: log the call

**Why.** Cost and latency numbers for the README must come from somewhere you can query.

Add to the bottom of `src/docintel/core/llm.py`:

```python
LLM_CALLS = """
CREATE TABLE IF NOT EXISTS llm_calls (
    call_id VARCHAR PRIMARY KEY, created_at TIMESTAMP DEFAULT current_timestamp,
    run_id VARCHAR, model VARCHAR, provider VARCHAR, schema_name VARCHAR,
    attempts INTEGER, ok BOOLEAN, error VARCHAR, raw_text VARCHAR,
    prompt_tokens INTEGER, completion_tokens INTEGER, cost_usd DOUBLE, latency_ms INTEGER
)
"""


def log_call(con, result: LLMResult, schema_name: str, run_id: str | None = None) -> None:
    con.execute(LLM_CALLS)
    con.execute(
        "INSERT INTO llm_calls (call_id, run_id, model, provider, schema_name, attempts, ok, "
        "error, raw_text, prompt_tokens, completion_tokens, cost_usd, latency_ms) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            str(uuid.uuid4()),
            run_id,
            result.model,
            result.provider,
            schema_name,
            result.attempts,
            result.parsed is not None,
            result.error,
            result.raw_text,
            result.usage.get("prompt_tokens"),
            result.usage.get("completion_tokens"),
            result.cost_usd,
            result.latency_ms,
        ],
    )
```

*Python here: `?` placeholders: [0d PY-5](./py/phase-0d.md#py-5).*

Here, we:

1. Create the table only if it is missing (`IF NOT EXISTS`). Unlike `contracts`, this table must
   keep its old rows. `make data` never touches it.
2. Give each call a random id (`uuid4`), like `crypto.randomUUID()` in JS.
3. Leave `run_id` empty for now. 1c fills it, so a run's calls can be found.
4. Let DuckDB fill `created_at` with the current time.
5. Set `ok` to true only when Pydantic accepted the answer.

Checkpoint. Log a hand-made result twice into a throwaway database:

```sh
$ uv run python -c "
from docintel.core.llm import LLMResult, log_call
from docintel.evals.store import connect
r = LLMResult('{}', None, 'bad', {'prompt_tokens': 10, 'completion_tokens': 2}, 0.00001, 850, 'qwen/x', 'DeepInfra', 1)
with connect(':memory:') as con:
    log_call(con, r, 'Clause')
    log_call(con, r, 'Clause')
    print(con.sql('SELECT schema_name, ok, error, prompt_tokens, cost_usd, latency_ms FROM llm_calls'))"
┌─────────────┬─────────┬─────────┬───────────────┬──────────┬────────────┐
│ schema_name │   ok    │  error  │ prompt_tokens │ cost_usd │ latency_ms │
│   varchar   │ boolean │ varchar │     int32     │  double  │   int32    │
├─────────────┼─────────┼─────────┼───────────────┼──────────┼────────────┤
│ Clause      │ false   │ bad     │            10 │    1e-05 │        850 │
│ Clause      │ false   │ bad     │            10 │    1e-05 │        850 │
└─────────────┴─────────┴─────────┴───────────────┴──────────┴────────────┘
```

Two rows: the second `CREATE TABLE IF NOT EXISTS` did nothing.

## Step 5: `call_llm`, the one public function

**Why.** Callers should not know about retries, parsing or logging. They call one function.

Add to the bottom of `src/docintel/core/llm.py`:

```python
def call_llm[T: BaseModel](
    messages: list[dict],
    schema: type[T],
    *,
    con: duckdb.DuckDBPyConnection | None = None,
    run_id: str | None = None,
    model: str | None = None,
    client: OpenAI | None = None,
    backoff_s: float = 1.0,
) -> LLMResult[T]:
    """Send messages, ask for JSON that fits `schema`, check it with Pydantic, log the call."""
    s = get_settings()
    model = model or s.docintel_model
    client = client or make_client()

    start = time.perf_counter()
    resp, attempts = _send(client, messages, schema, model, s.llm_max_attempts, backoff_s)
    latency_ms = round((time.perf_counter() - start) * 1000)

    raw_text = resp.choices[0].message.content or ""
    parsed, error = _parse(schema, raw_text)
    usage = resp.usage.model_dump() if resp.usage else {}
    result = LLMResult(
        raw_text=raw_text,
        parsed=parsed,
        error=error,
        usage=usage,
        cost_usd=usage.get("cost"),
        latency_ms=latency_ms,
        model=resp.model,
        provider=getattr(resp, "provider", None),
        attempts=attempts,
    )
    if con is not None:
        log_call(con, result, schema.__name__, run_id)
    return result
```

*Python here: [keyword-only arguments after `*`](./py/phase-1a2.md#py-5) ·
[`x or default` and `getattr`](./py/phase-1a2.md#py-6).*

Here, we:

1. Use the settings for anything the caller did not pass. Tests pass their own `client`.
2. Start a timer, send with retries, stop the timer. Latency includes the retry waits, because
   the user waits for them too.
3. Read the text. Some providers send `null` when something goes wrong. `or ""` turns it into
   `""`, and Pydantic reports `Invalid JSON ... [type=json_invalid]`. So an empty answer is one
   more `ValidationError`, like the three in Step 2.
4. Check the text with the schema.
5. Read `cost` from `usage`. OpenRouter adds it to every answer. The SDK keeps extra keys like
   `cost` and `provider`, even though OpenAI's own API does not send them.
6. Log the call if we got a `con`, then return the result.

A call that fails after all retries raises, and leaves no row. It has no text and no cost. 1c
will record it as a failed contract.

There is no offline checkpoint here. Step 6 is the real one, and Step 7 tests each path.

## Step 6: one live call

**Why.** Fakes cannot tell you whether the real provider accepts your schema.

This call costs a tiny fraction of a cent. It uses a 1-sentence "contract" and the small `Text`
model, not a full contract. Use your own model name if it is not `Text`. It writes to
`data/docintel.duckdb`, so close the notebook connection first.

Checkpoint:

```sh
$ uv run python -c "
from docintel.core.llm import call_llm
from docintel.domain.schema.fields import Text
from docintel.evals.store import connect
messages = [
    {'role': 'system', 'content': 'Extract the governing law. Copy quotes exactly.'},
    {'role': 'user', 'content': 'This Agreement shall be governed by the laws of the State of New York.'},
]
with connect() as con:
    r = call_llm(messages, Text, con=con)
    print(r.raw_text)
    print(r.parsed)
    print(r.error, r.model, r.provider, r.attempts)
    print(r.usage['prompt_tokens'], r.usage['completion_tokens'], r.cost_usd, r.latency_ms)"
```

<!-- LIVE OUTPUT: pasted from the user's own run -->

Look at four things:

1. `raw_text` is pure JSON, with no sentence around it.
2. `parsed` is a `Text` object, and `error` is `None`.
3. `provider` is one of the endpoints with structured output (Round 1).
4. `cost_usd` is very small. A real contract is about 13,000 tokens, so it costs much more.

Now look at the row. Open the notebook, run cell 1, and add:

```python
con.sql("SELECT created_at, model, provider, ok, attempts, prompt_tokens, cost_usd, latency_ms FROM llm_calls")
```

You should see one row per live call you made. Close the connection again after.

## Step 7: a test for the rules that must never break

**Why.** Four things must always be true:

1. A good answer is parsed and logged.
2. A bad answer is an error in the result, not a crash.
3. A 429 is retried.
4. A 400 is not.

The test needs no key and no network. It uses a real `OpenAI` client, but swaps its HTTP layer
for a fake. `httpx2.MockTransport` calls our function instead of the internet.

Put this in `tests/test_llm.py`:

```python
"""LLM client tests with a fake OpenRouter (no network, no key, no cost)."""

import httpx2
import openai
import pytest
from openai import OpenAI

from docintel.core.config import get_settings
from docintel.core.llm import call_llm
from docintel.domain.schema.fields import Strict
from docintel.evals.store import connect

MESSAGES = [{"role": "user", "content": "Is there a non-compete clause?"}]


class Answer(Strict):  # a tiny schema, so these tests do not depend on your field choices
    quotes: list[str]
    found: bool


def reply(content: str) -> httpx2.Response:
    """A fake OpenRouter answer, shaped like the real one."""
    return httpx2.Response(
        200,
        json={
            "id": "gen-1",
            "object": "chat.completion",
            "created": 0,
            "model": "qwen/test",
            "provider": "FakeCloud",
            "choices": [
                {
                    "index": 0,
                    "finish_reason": "stop",
                    "message": {"role": "assistant", "content": content},
                }
            ],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15,
                "cost": 1e-6,
            },
        },
    )


def fake_client(*responses: httpx2.Response) -> tuple[OpenAI, list]:
    """A real OpenAI client whose HTTP layer returns `responses` in order."""
    sent = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        sent.append(request)
        return responses[len(sent) - 1]

    http = httpx2.Client(transport=httpx2.MockTransport(handler))
    client = OpenAI(
        api_key="sk-or-v1-test", base_url="https://fake.test/v1", max_retries=0, http_client=http
    )
    return client, sent


@pytest.fixture(autouse=True)
def settings(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-test")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
```

*Python here: [`*responses`, and a function inside a function](./py/phase-1a2.md#py-7) ·
fixtures: [0b PY-8](./py/phase-0b.md#py-8).*

Here, we:

1. Make `Answer`, a tiny schema, so these tests work whatever fields you chose in 1a.
2. `reply` builds a fake answer with the same keys OpenRouter sends, `cost` and `provider`
   included.
3. `fake_client` gives back the responses in order, and keeps a list of the requests it got. So
   a test can count requests.
4. The `autouse` fixture runs before every test. It sets a fake key and clears the settings
   cache, so no test reads your real `.env`.

Add the tests to the bottom of `tests/test_llm.py`:

```python
def test_valid_json_is_parsed_and_logged():
    client, _ = fake_client(reply('{"quotes": ["shall not compete"], "found": true}'))
    with connect(":memory:") as con:
        r = call_llm(MESSAGES, Answer, con=con, client=client)
        rows = con.execute("SELECT ok, provider, cost_usd FROM llm_calls").fetchall()
    assert r.parsed == Answer(quotes=["shall not compete"], found=True)
    assert r.error is None
    assert rows == [(True, "FakeCloud", 1e-6)]


def test_bad_json_is_an_error_not_a_crash():
    client, _ = fake_client(reply('{"quotes": [], "found": "yes"}'))
    with connect(":memory:") as con:
        r = call_llm(MESSAGES, Answer, con=con, client=client)
        rows = con.execute("SELECT ok, raw_text FROM llm_calls").fetchall()
    assert r.parsed is None
    assert "found" in r.error
    assert rows == [(False, '{"quotes": [], "found": "yes"}')]


def test_429_is_retried():
    client, sent = fake_client(httpx2.Response(429), reply('{"quotes": [], "found": false}'))
    r = call_llm(MESSAGES, Answer, client=client, backoff_s=0)
    assert r.attempts == 2
    assert len(sent) == 2


def test_400_is_not_retried():
    client, sent = fake_client(httpx2.Response(400), reply("{}"))
    with pytest.raises(openai.BadRequestError):
        call_llm(MESSAGES, Answer, client=client, backoff_s=0)
    assert len(sent) == 1
```

*Python here: `pytest.raises`: [1a PY-5](./py/phase-1a.md#py-5).*

Here, we:

1. Send a good answer. Check the parsed object and the logged row, `cost` and `provider`
   included.
2. Send `"found": "yes"`. Check it becomes an error and an `ok = false` row.
3. Send a 429, then a good answer. Two requests, `attempts == 2`. `backoff_s=0` so the test does
   not wait.
4. Send a 400, then a good answer. It must raise after the first request. The good answer is
   never used.

Checkpoint:

```sh
$ make lint && make test
All checks passed!
...
tests/test_data_load.py ....                                             [ 22%]
tests/test_llm.py ....                                                   [ 44%]
tests/test_schema.py ....                                                [ 66%]
tests/test_smoke.py .                                                    [ 72%]
tests/test_splits.py .....                                               [100%]

============================== 18 passed in 0.84s ==============================
```

Your project should now look like this:

```
src/docintel/
├── core/
│   ├── config.py          Settings, get_settings
│   └── llm.py             response_format, make_client, LLMResult, _parse, _send, log_call, call_llm
├── domain/schema/
│   └── fields.py          Strict, your field models, ContractFields, CUAD_CATEGORY
└── evals/
    ├── datasets.py
    └── store.py
tests/
├── test_data_load.py
├── test_llm.py            4 tests
├── test_schema.py         4 tests
├── test_smoke.py
└── test_splits.py
data/
└── docintel.duckdb        + llm_calls (your live calls)
```

<details><summary>Full <code>src/docintel/core/llm.py</code></summary>

```python
"""Thin OpenRouter client: messages + Pydantic model in, LLMResult out. Every call is logged."""

import time
import uuid
from dataclasses import dataclass

import duckdb
import openai
from openai import OpenAI
from pydantic import BaseModel, ValidationError

from docintel.core.config import get_settings


def response_format(schema: type[BaseModel]) -> dict:
    """The `response_format` that asks the provider to follow this Pydantic model."""
    return {
        "type": "json_schema",
        "json_schema": {
            "name": schema.__name__,
            "strict": True,
            "schema": schema.model_json_schema(),
        },
    }


def make_client() -> OpenAI:
    s = get_settings()
    return OpenAI(
        api_key=s.openrouter_api_key.get_secret_value(),
        base_url=s.openrouter_base_url,
        timeout=s.llm_timeout_s,
        max_retries=0,  # we retry ourselves, and only on network errors and 429
    )


@dataclass
class LLMResult[T: BaseModel]:
    raw_text: str
    parsed: T | None  # None when the text did not fit the schema
    error: str | None  # the Pydantic error, so 2b can send it back to the model
    usage: dict
    cost_usd: float | None
    latency_ms: int
    model: str
    provider: str | None
    attempts: int


def _parse[T: BaseModel](schema: type[T], raw_text: str) -> tuple[T | None, str | None]:
    try:
        return schema.model_validate_json(raw_text), None
    except ValidationError as e:
        return None, str(e)


RETRYABLE = (openai.APIConnectionError, openai.RateLimitError)  # timeouts are connection errors


def _send(client, messages, schema, model, max_attempts, backoff_s):
    """One request, tried again only on RETRYABLE errors. Returns (response, attempts)."""
    for attempt in range(1, max_attempts + 1):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                response_format=response_format(schema),
                extra_body={"provider": {"require_parameters": True}},
                temperature=0,
            )
            return resp, attempt
        except RETRYABLE:
            if attempt == max_attempts:
                raise
            time.sleep(backoff_s * 2 ** (attempt - 1))  # 1 s, 2 s, 4 s


LLM_CALLS = """
CREATE TABLE IF NOT EXISTS llm_calls (
    call_id VARCHAR PRIMARY KEY, created_at TIMESTAMP DEFAULT current_timestamp,
    run_id VARCHAR, model VARCHAR, provider VARCHAR, schema_name VARCHAR,
    attempts INTEGER, ok BOOLEAN, error VARCHAR, raw_text VARCHAR,
    prompt_tokens INTEGER, completion_tokens INTEGER, cost_usd DOUBLE, latency_ms INTEGER
)
"""


def log_call(con, result: LLMResult, schema_name: str, run_id: str | None = None) -> None:
    con.execute(LLM_CALLS)
    con.execute(
        "INSERT INTO llm_calls (call_id, run_id, model, provider, schema_name, attempts, ok, "
        "error, raw_text, prompt_tokens, completion_tokens, cost_usd, latency_ms) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            str(uuid.uuid4()),
            run_id,
            result.model,
            result.provider,
            schema_name,
            result.attempts,
            result.parsed is not None,
            result.error,
            result.raw_text,
            result.usage.get("prompt_tokens"),
            result.usage.get("completion_tokens"),
            result.cost_usd,
            result.latency_ms,
        ],
    )


def call_llm[T: BaseModel](
    messages: list[dict],
    schema: type[T],
    *,
    con: duckdb.DuckDBPyConnection | None = None,
    run_id: str | None = None,
    model: str | None = None,
    client: OpenAI | None = None,
    backoff_s: float = 1.0,
) -> LLMResult[T]:
    """Send messages, ask for JSON that fits `schema`, check it with Pydantic, log the call."""
    s = get_settings()
    model = model or s.docintel_model
    client = client or make_client()

    start = time.perf_counter()
    resp, attempts = _send(client, messages, schema, model, s.llm_max_attempts, backoff_s)
    latency_ms = round((time.perf_counter() - start) * 1000)

    raw_text = resp.choices[0].message.content or ""
    parsed, error = _parse(schema, raw_text)
    usage = resp.usage.model_dump() if resp.usage else {}
    result = LLMResult(
        raw_text=raw_text,
        parsed=parsed,
        error=error,
        usage=usage,
        cost_usd=usage.get("cost"),
        latency_ms=latency_ms,
        model=resp.model,
        provider=getattr(resp, "provider", None),
        attempts=attempts,
    )
    if con is not None:
        log_call(con, result, schema.__name__, run_id)
    return result
```
</details>

<details><summary>Full <code>tests/test_llm.py</code></summary>

```python
"""LLM client tests with a fake OpenRouter (no network, no key, no cost)."""

import httpx2
import openai
import pytest
from openai import OpenAI

from docintel.core.config import get_settings
from docintel.core.llm import call_llm
from docintel.domain.schema.fields import Strict
from docintel.evals.store import connect

MESSAGES = [{"role": "user", "content": "Is there a non-compete clause?"}]


class Answer(Strict):  # a tiny schema, so these tests do not depend on your field choices
    quotes: list[str]
    found: bool


def reply(content: str) -> httpx2.Response:
    """A fake OpenRouter answer, shaped like the real one."""
    return httpx2.Response(
        200,
        json={
            "id": "gen-1",
            "object": "chat.completion",
            "created": 0,
            "model": "qwen/test",
            "provider": "FakeCloud",
            "choices": [
                {
                    "index": 0,
                    "finish_reason": "stop",
                    "message": {"role": "assistant", "content": content},
                }
            ],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15,
                "cost": 1e-6,
            },
        },
    )


def fake_client(*responses: httpx2.Response) -> tuple[OpenAI, list]:
    """A real OpenAI client whose HTTP layer returns `responses` in order."""
    sent = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        sent.append(request)
        return responses[len(sent) - 1]

    http = httpx2.Client(transport=httpx2.MockTransport(handler))
    client = OpenAI(
        api_key="sk-or-v1-test", base_url="https://fake.test/v1", max_retries=0, http_client=http
    )
    return client, sent


@pytest.fixture(autouse=True)
def settings(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-test")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_valid_json_is_parsed_and_logged():
    client, _ = fake_client(reply('{"quotes": ["shall not compete"], "found": true}'))
    with connect(":memory:") as con:
        r = call_llm(MESSAGES, Answer, con=con, client=client)
        rows = con.execute("SELECT ok, provider, cost_usd FROM llm_calls").fetchall()
    assert r.parsed == Answer(quotes=["shall not compete"], found=True)
    assert r.error is None
    assert rows == [(True, "FakeCloud", 1e-6)]


def test_bad_json_is_an_error_not_a_crash():
    client, _ = fake_client(reply('{"quotes": [], "found": "yes"}'))
    with connect(":memory:") as con:
        r = call_llm(MESSAGES, Answer, con=con, client=client)
        rows = con.execute("SELECT ok, raw_text FROM llm_calls").fetchall()
    assert r.parsed is None
    assert "found" in r.error
    assert rows == [(False, '{"quotes": [], "found": "yes"}')]


def test_429_is_retried():
    client, sent = fake_client(httpx2.Response(429), reply('{"quotes": [], "found": false}'))
    r = call_llm(MESSAGES, Answer, client=client, backoff_s=0)
    assert r.attempts == 2
    assert len(sent) == 2


def test_400_is_not_retried():
    client, sent = fake_client(httpx2.Response(400), reply("{}"))
    with pytest.raises(openai.BadRequestError):
        call_llm(MESSAGES, Answer, client=client, backoff_s=0)
    assert len(sent) == 1
```
</details>

## Break it on purpose

**Break 1: retry a 400.** Add `openai.BadRequestError` to `RETRYABLE`. Guess which test fails:

```
E       Failed: DID NOT RAISE BadRequestError
FAILED tests/test_llm.py::test_400_is_not_retried - Failed: DID NOT RAISE Bad...
========================= 1 failed, 17 passed in 0.86s =========================
```

The second try got the good fake answer, so no error came out. With a real server, the second
try gets the same 400. The run just waits 1 s for nothing, on every bad request. Change it back.

**Break 2: raise on bad JSON.** In `_parse`, remove the `try` and `except`, and keep only
`return schema.model_validate_json(raw_text), None`. Guess the result:

```
E       pydantic_core._pydantic_core.ValidationError: 1 validation error for Answer
E       found
E         Input should be a valid boolean [type=bool_type, input_value='yes', input_type=str]
FAILED tests/test_llm.py::test_bad_json_is_an_error_not_a_crash - pydantic_co...
========================= 1 failed, 17 passed in 0.58s =========================
```

The error now escapes `call_llm`. No row is logged, and 1c would stop at the first bad answer.
Change it back.

## Experiment

This part runs no experiment. It makes one tiny call, not a dataset run, so there is no
`run_id` and no `EXPERIMENTS.md` entry. Your `llm_calls` row is the first trace. From 1c on,
every row has a `run_id`.

One query to keep for later:

```python
con.sql("SELECT count(*) AS calls, sum(cost_usd) AS usd, median(latency_ms) AS p50_ms FROM llm_calls")
```

## Gotchas

- **Lock error.** The live call writes to `data/docintel.duckdb`. If the notebook holds it, close
  the notebook connection first.
- **401 or 402 from OpenRouter.** 401 is a wrong key. 402 is no credit left. Neither is retried.
- **A 400 that says the schema is invalid.** Some strict providers allow fewer JSON Schema
  features. See the 1a gotcha: keep the schema simple.
- **Slow tests.** If `make test` takes seconds, a test forgot `backoff_s=0` and really waits.
- **Old settings in the notebook.** `get_settings()` keeps the first result. After you change
  `.env`, restart the kernel.

## Explain back, then commit

Explain each changed file to Claude in a few sentences (the rule in `PLAN.md`): `llm.py` (each
function, and what happens on bad JSON, a 429 and a 400) and `test_llm.py` (each test, and how
the fake server works). Then:

```sh
$ git status
$ git add src/docintel/core/llm.py tests/test_llm.py
$ git commit -m "phase 1a2: OpenRouter client with retries and llm_calls log"
```

## Conclusion

What you have now:

- `call_llm`: one function that asks for JSON, checks it, retries only what waiting can fix, and
  logs every call with tokens, cost and latency.
- A first real row in `llm_calls`.
- A test that guards the retry rules and the "bad answer is a result" rule.

Go back to the objectives. Check that you can do each one without notes. Then answer:

1. Why does a 429 get retried, but a 400 does not?
2. Why do we turn off the SDK's own retries, if they do the same job?

Want more practice? Try these (optional):

1. Add a test: a timeout (raise `httpx2.ReadTimeout` in the handler) is retried.
2. Read the `Retry-After` header on a 429, and wait that long instead of the fixed backoff.
3. Change the live call to ask about the parties with your Parties model. Does `value` match
   `quotes`?

Checklist (`../PLAN.md`): **Structured outputs: Pydantic to JSON schema; enforcement and
validation** (done, with 1a). **Retries, timeouts, degradation, idempotency** (retries and
timeouts started; the rest comes in Phase 4).
