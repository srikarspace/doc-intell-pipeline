# Python for Phase 1c4

This file explains the new Python (and a little SQL) in Part 1c4. Read one section when the main
doc links to it. `urlopen` and `json.load` are in the 1c companion ([PY-1](./phase-1c.md#py-1)).

<a id="py-1"></a>
## PY-1. `m.get(...) or None`

```python
hf = m.get("hugging_face_id") or None
```

1. `d.get(key)` returns the value, or `None` if the key is missing. `d[key]` would raise a
   `KeyError` instead. In JS, `m.hugging_face_id` gives `undefined` for a missing key, like
   `.get`.
2. Some models have the key with an empty string `""`. `or None` turns `""` into `None` too, so
   one `if hf:` covers both cases. `x or default` is in 1a2 ([PY-6](./phase-1a2.md#py-6)).

<a id="py-2"></a>
## PY-2. `next(..., default)`: the first match, or a backup value

```python
license = next((t for t in tags if t.startswith("license:")), "license: ?")
```

1. `(t for t in tags if ...)` is a generator: it makes the matches one at a time, only when
   asked ([0b PY-5](./phase-0b.md#py-5)).
2. `next(gen)` asks for the first one. It stops there: the other tags are never checked.
3. The second argument is the backup value when there is no match. Without it, `next` raises
   `StopIteration`.

In JS: `tags.find(t => t.startsWith("license:")) ?? "license: ?"`.

<a id="py-3"></a>
## PY-3. `* 1e6` and `:5.3f`

```python
print(f"{model:28} {float(p['prompt']) * 1e6:5.3f} {float(p['completion']) * 1e6:5.2f}")
```

- OpenRouter gives prices as strings, per token: `"0.00000009"`. `float(...)` makes a number.
- `1e6` is one million, written in scientific notation, like in JS. Times one million gives the
  price per million tokens: `0.09`.
- `:5.3f` prints a number 5 characters wide with 3 decimals: `0.090`. `:5.2f` gives 2 decimals.
- `:28` pads the model name to 28 characters, so the columns line up
  ([1b2 PY-7](./phase-1b2.md#py-7)).

<a id="py-4"></a>
## PY-4. `list_contains` and a list parameter

```python
con.sql("... WHERE list_contains($runs, run_id) ...", params={"runs": RUNS})
```

1. A Python list passed as a parameter becomes a DuckDB list: `['20261021-143205', ...]`.
2. `list_contains(list, value)` is true when the value is in the list. In JS:
   `RUNS.includes(run_id)`.
3. It replaces `run_id IN (?, ?, ?, ?)`, where you need one `?` per run. With a list, the query
   stays the same for 2 runs or 10.
