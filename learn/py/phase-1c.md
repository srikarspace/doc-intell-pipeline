# Python for Phase 1c

This file explains the new Python in Part 1c. Read one section when the main doc links to it.
Comprehensions are in the 0b companion ([PY-4](./phase-0b.md#py-4)). Pydantic models are in the
1a companion ([PY-1](./phase-1a.md#py-1)).

<a id="py-1"></a>
## PY-1. `urllib.request.urlopen` and `json.load`: a GET request

```python
with urllib.request.urlopen(url, timeout=30) as resp:
    prices = {m["id"]: m["pricing"] for m in json.load(resp)["data"]}
```

1. `urlopen(url)` sends a GET request and gives back the response. It is part of Python, so
   there is nothing to install.
2. `with` closes the connection at the end, like in 0b ([PY-3](./phase-0b.md#py-3)).
3. `json.load(resp)` reads the body and parses it. `json.load` reads from a file or a response.
   `json.loads` (with an `s`, for "string") parses a string.

In JS: `const prices = (await (await fetch(url)).json()).data`. A status like 404 raises
`urllib.error.HTTPError`, where `fetch` would only set `res.ok` to false. We use `urllib` here
because this one public GET needs no key and no SDK.

<a id="py-2"></a>
## PY-2. `model_fields[...].annotation`: ask a model about its fields

```python
model = ContractFields.model_fields[field].annotation
if "value" in model.model_fields:
    answer["value"] = [] if model is Names else None
```

1. Every Pydantic class has `model_fields`: a dict from field name to field info. Example:
   `ContractFields.model_fields["parties"]`.
2. `.annotation` is the type you wrote after the colon. For `parties: Names`, it is the class
   `Names` itself.
3. That class has its own `model_fields`. `"value" in ...` asks "does this class have a field
   called `value`?". `Clause` does not.
4. `model is Names` asks "is this the very same class?". For classes, `is` is the right check.

In JS with zod, the closest is `ContractFields.shape.parties`, then `instanceof` checks. Here
the class answers questions about itself, so `empty_answer` works for any field you add later.

<a id="py-3"></a>
## PY-3. JSON both ways: `model_dump`, `json.dumps`, `json.loads`

Three steps turn a Pydantic field into a string, and back:

```python
answer = getattr(result.parsed, field).model_dump()   # Pydantic object -> dict
json.dumps(answer)                                     # dict -> JSON string
ContractFields.model_validate({field: json.loads(answer) for field, answer in rows})
```

- `model_dump()` gives a plain dict: `{"quotes": [...], "value": "Michigan", "found": True}`.
- `json.dumps(d)` is `JSON.stringify(d)`. Python `True` and `None` become JSON `true` and `null`.
- `json.loads(s)` is `JSON.parse(s)`.
- `model_validate(d)` checks a dict and builds the model. It is the dict partner of
  `model_validate_json` from 1a2, which takes a string.

DuckDB gives a `JSON` column back to Python as a plain string. That is why `from_rows` calls
`json.loads` first.

<a id="py-4"></a>
## PY-4. `{"run_id": ..., **r}`: adding keys to a dict

```python
[{"run_id": run_id, "doc_id": doc_id, **r} for r in scored]
```

`**r` copies every key of `r` into the new dict. It is the JS spread:

```js
scored.map(r => ({ run_id: runId, doc_id: docId, ...r }));
```

`d | e` from 0b ([PY-6](./phase-0b.md#py-6)) does the same for two dicts. `{..., **r}` is handy
when you add single keys next to a whole dict. The result fills `$run_id`, `$doc_id`, `$field`
and the rest in `SCORE_ROW` by name ([0d PY-5](./phase-0d.md#py-5)).
