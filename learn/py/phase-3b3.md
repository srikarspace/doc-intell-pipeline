# Python for Phase 3b3

This file explains the new Python in Part 3b3. Read one section when the main doc links to it. matplotlib's `subplots`
and `ax` are in 1c3 ([PY-3](./phase-1c3.md#py-3)).

<a id="py-1"></a>
## PY-1. `arg_max`, and a dict of runs

```python
LATEST = """
SELECT parser, arg_max(run_id, created_at) FROM runs
WHERE split = ? AND model = ? AND prompt_version = 'v1' GROUP BY parser
"""
runs = dict(con.execute(LATEST, [SET_NAME, model]).fetchall())
```

1. `arg_max(run_id, created_at)` gives the `run_id` from the row with the largest `created_at`. It is a DuckDB function.
   In lodash: `_.maxBy(rows, "created_at").run_id`.
2. `fetchall()` returns pairs: `[("pypdf", "2026..."), ...]`.
3. `dict(pairs)` turns the pairs into a dict. In JS: `Object.fromEntries(pairs)`.

<a id="py-2"></a>
## PY-2. `next` with a generator

```python
baseline = next(r["f1"] for r in rows if r["cell"] == "cuad_txt")
```

`next` takes the first value and stops. In JS: `rows.find(r => r.cell === "cuad_txt").f1`. If nothing matches, Python
raises `StopIteration`. Here, that means you forgot the `cuad_txt` run.

<a id="py-3"></a>
## PY-3. `monkeypatch.setattr` on a module

```python
monkeypatch.setattr(pe, "all_spans", lambda con, docs: {})
```

This replaces `all_spans` in the `parser_experiment` module for one test. It is undone at the end of the test. It works
because `compare_rows` looks up `all_spans` in its own module each time. In Jest, it is `jest.spyOn(module, "fn")`.

So the test needs no label table, no cache, and no real contract.
