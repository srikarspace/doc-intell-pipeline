# Python for Phase 1a2

This file explains the new Python in Part 1a2. Read one section when the main doc links to it.
Classes and `type[...]` are in the 1a companion ([PY-1](./phase-1a.md#py-1),
[PY-3](./phase-1a.md#py-3)).

<a id="py-1"></a>
## PY-1. `@dataclass`

`@dataclass` turns a class with typed fields into a simple record. Python writes the constructor
for you.

```python
@dataclass
class LLMResult[T: BaseModel]:
    raw_text: str
    parsed: T | None
    ...
    attempts: int
```

- Make one with positional or keyword arguments: `LLMResult(raw_text="...", parsed=None, ...)`.
- `print(r)` shows every field, and `==` compares field by field.
- In TS: an `interface LLMResult { rawText: string; ... }` plus a plain object.

Why not a Pydantic model? A dataclass does no checks. We build `LLMResult` ourselves from values
we trust, so checks would only cost time. Pydantic is for data from outside, like the model's
answer.

<a id="py-2"></a>
## PY-2. Generics: `[T: BaseModel]`

A **generic** function works with many types and keeps track of which one. Python 3.12 writes the
type parameter in square brackets after the name:

```python
def call_llm[T: BaseModel](messages: list[dict], schema: type[T], ...) -> LLMResult[T]:
```

Read it like this:

1. `[T: BaseModel]`: `T` is some class that inherits `BaseModel`.
2. `schema: type[T]`: you pass that class.
3. `-> LLMResult[T]`: you get back a result whose `parsed` is an object of that class.

So `call_llm(messages, Clause)` gives an `LLMResult[Clause]`, and your editor knows that
`r.parsed.found` exists. In TS: `function callLlm<T extends BaseModel>(schema: new () => T):
LLMResult<T>`. It is only a hint for tools. Python does not check it when the code runs.

<a id="py-3"></a>
## PY-3. `try` / `except`, a tuple of errors, and `raise`

`try` / `except` is JS `try` / `catch`, but you name the error class you catch:

```python
try:
    return schema.model_validate_json(raw_text), None
except ValidationError as e:
    return None, str(e)
```

- **Only that class is caught.** Any other error goes up to the caller. In JS you catch
  everything and check `if (e instanceof ValidationError)`.
- **A tuple catches several classes**: `except RETRYABLE:` where
  `RETRYABLE = (openai.APIConnectionError, openai.RateLimitError)`.
- **Subclasses count.** `APITimeoutError` inherits `APIConnectionError`, so it is caught too.
- **`raise` alone**, inside `except`, sends the same error up again. In JS: `throw e`.
- **`str(e)`** turns the error into its message text.

<a id="py-4"></a>
## PY-4. `time.perf_counter`, `time.sleep`, and `**`

```python
start = time.perf_counter()
...
latency_ms = round((time.perf_counter() - start) * 1000)
```

- **`time.perf_counter()`** gives a time in seconds, as a float. Only the difference between two
  calls means something. In JS: `performance.now()`, but that one is in milliseconds.
- **`time.sleep(s)`** stops the program for `s` seconds. It blocks, like a sync sleep. JS has no
  blocking sleep. You would `await new Promise(r => setTimeout(r, ms))`.
- **`2 ** (attempt - 1)`**: `**` is "to the power of". `2 ** 0` is 1, `2 ** 1` is 2, `2 ** 2` is 4.
  In JS: also `**`.

<a id="py-5"></a>
## PY-5. Keyword-only arguments after `*`

A bare `*` in the parameter list means: every parameter after it must be passed by name.

```python
def call_llm[T: BaseModel](messages, schema, *, con=None, run_id=None, model=None, client=None, backoff_s=1.0):

call_llm(messages, Text, con=con)          # fine
call_llm(messages, Text, con)              # TypeError: call_llm() takes 2 positional arguments but 3 were given
```

So a call always says which option it sets. In JS this is the options object:
`callLlm(messages, Text, { con })`. Defaults work as in 0d ([PY-7](./phase-0d.md#py-7)).

<a id="py-6"></a>
## PY-6. `x or default` and `getattr`

```python
model = model or s.docintel_model
raw_text = resp.choices[0].message.content or ""
provider = getattr(resp, "provider", None)
```

- **`a or b`** gives `a` if it is "truthy", else `b`. `None` and `""` are falsy. In JS: `a || b`.
  Python has no `??`. So `0 or 5` gives 5, like `0 || 5` in JS.
- **`getattr(obj, "name", default)`** reads an attribute by its name, or gives `default` if it is
  missing. In JS: `obj.provider ?? null`. We use it because `provider` is an extra key from
  OpenRouter. It is not part of the SDK's own class.

<a id="py-7"></a>
## PY-7. `*responses`, and a function inside a function

**`*responses`** in a `def` collects any number of positional arguments into a tuple:

```python
def fake_client(*responses: httpx2.Response) -> tuple[OpenAI, list]:

fake_client(httpx2.Response(429), reply('{"quotes": [], "found": false}'))   # responses has 2 items
```

In JS: rest parameters, `function fakeClient(...responses)`.

**A function inside a function** can use the outer function's variables. This is a **closure**,
the same as in JS:

```python
    sent = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        sent.append(request)
        return responses[len(sent) - 1]
```

Each time the fake server gets a request, `handler` adds it to `sent`. Then it returns the next
response: the first request gets `responses[0]`, the second gets `responses[1]`. The test reads
`len(sent)` to count requests.
