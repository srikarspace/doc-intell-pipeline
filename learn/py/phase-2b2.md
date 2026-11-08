# Python for Phase 2b2

This file explains the new Python (and SQL) in Part 2b2. Read one section when the main doc links to it.
`defaultdict` is in 0d ([PY-3](./phase-0d.md#py-3)), dict merge `|` is in 0b ([PY-6](./phase-0b.md#py-6)),
`if __name__ == "__main__":` is in 0b ([PY-7](./phase-0b.md#py-7)), and `x if test else y` is in 1c3
([PY-2](./phase-1c3.md#py-2)).

<a id="py-1"></a>
## PY-1. A type alias: `Answers = dict[...]`

```python
Answers = dict[str, ContractFields | None]  # doc_id -> answer; None: it did not fit the schema


def first_answers(con: duckdb.DuckDBPyConnection, run_id: str) -> Answers:
```

1. A type can be stored in a name, like any value. `Answers` is now a short name for the long type.
2. Five functions use it. If the shape changes, you change one line.
3. Python does not check it when the code runs. It is for you, your editor and readers.

In TypeScript: `type Answers = Record<string, ContractFields | null>`.

<a id="py-2"></a>
## PY-2. `_parse`: a name that starts with `_`

```python
from docintel.core.llm import _parse
```

A leading `_` means "this is inside the module, not part of its public face". Python does not stop you
from importing it. It is only a sign.

Here we import it on purpose. The "before" must be parsed exactly like the live call parsed it. A
second copy of the parse could drift. `tests/test_retry.py` (2b) imports it for the same reason.

In JS, it is like a function a module does not list in its docs, but still exports.

<a id="py-3"></a>
## PY-3. A dict comprehension with `if ... else` in the value

```python
return {
    doc_id: blank(answer, broken[doc_id]) if answer and broken[doc_id] else answer
    for doc_id, answer in answers.items()
}
```

For each contract, in order:

1. `answer and broken[doc_id]` is true only if both are "truthy".
2. `None` is false. So a bad-schema answer is never blanked: it is already empty.
3. An empty set is false. So a contract with no broken fields keeps its answer as it is.
4. Otherwise, `blank` makes a new answer.

In JS: `Object.fromEntries(Object.entries(answers).map(([id, a]) => [id, a && broken[id].size ? blank(a, broken[id]) : a]))`.

<a id="py-4"></a>
## PY-4. `model_dump() | {...}`, then `model_validate`

```python
return ContractFields.model_validate(answer.model_dump() | {f: empty_answer(f) for f in fields})
```

Read it from the inside out:

1. `answer.model_dump()` turns the model into a plain dict of 12 fields (1c [PY-3](./phase-1c.md#py-3)).
2. `{f: empty_answer(f) for f in fields}` is a small dict with only the fields to blank.
3. `|` merges them. The right side wins, so those fields become empty.
4. `model_validate` builds a new model and checks it again.

Why not `model_copy(update=...)` (2b [PY-4](./phase-2b.md#py-4))? `update` takes the values as they
are. Here they are plain dicts, so the copy would hold a dict where a model should be. `model_validate`
turns each dict into the right field model.

<a id="py-5"></a>
## PY-5. `defaultdict(set)`, and reading a missing key

```python
broken = defaultdict(set)
for doc_id, field, rule in rows:
    if rule in rules:
        broken[doc_id].add(field)
```

1. `defaultdict(set)` gives an empty set the first time a key is used. So `.add` works at once.
2. A set keeps each field once, even if one field has two errors.
3. A trap: just reading `broken[doc_id]` also creates the key, with an empty set. That is fine here,
   because the empty set is false (PY-3). Use `broken.get(doc_id)` if you must not add keys.

<a id="py-6"></a>
## PY-6. `INSERT ... SELECT`: copy a row with one change

```sql
INSERT INTO runs (run_id, split, parser, model, prompt_version, n_docs, est_cost_usd, max_retries)
SELECT ?, split, parser, model, prompt_version, n_docs, 0, max_retries
FROM runs WHERE run_id = ?
```

1. The `SELECT` reads the parent's row.
2. In its place, it puts the new `run_id` (the first `?`) and a cost of 0.
3. The `INSERT` writes what the `SELECT` returns. No Python touches the values.
4. `created_at` is not in the list, so it gets its default: now.

<a id="py-7"></a>
## PY-7. `answer::VARCHAR`, `$a` and `IN $v` (DuckDB)

```sql
SELECT ..., answer::VARCHAR AS answer, tp FROM ... WHERE run_id = $a
SELECT count(DISTINCT (doc_id, field)) FILTER (WHERE rule IN $v) ...
```

```python
con.execute(CHANGED, {"a": first, "b": final})
con.execute(ERRORS, sets | {"run_id": first})
```

1. `x::VARCHAR` changes the type of `x` to text. Two JSON answers are then compared as text. That works
   because `json.dumps` always writes the fields in the same order.
2. `$a` is a named parameter. You pass a dict, and DuckDB puts `first` where `$a` is. It is safer than
   an f-string, like `?`.
3. `IN $v` with a Python list checks if `rule` is one of the items.
4. `count(DISTINCT (doc_id, field))` counts pairs. A field with two errors counts once.

<a id="py-8"></a>
## PY-8. `:>8`, `:8.3f` and `:.0%`

```python
f"{'first: P':>8}"   # "first: P" (already 8 wide)
f"{a['f1']:5.3f}"    # "0.939"
f"{cost1 / cost0:.0%}"  # "2%"
```

After the `:` (1d2 [PY-2](./phase-1d2.md#py-2)):

1. `>8` puts the text on the right of 8 spaces. It is `padStart(8)` in JS. `<` is left, and `^` is
   center.
2. `5.3f` means a number with 3 decimals, at least 5 wide. In JS: `x.toFixed(3).padStart(5)`.
3. `.0%` multiplies by 100, keeps no decimal, and adds `%`.

The header and the rows use the same widths, so the columns line up.

<a id="py-9"></a>
## PY-9. `(n_rows,) = ...fetchone()`, and one cursor

```python
(n_rows,) = con.execute(
    "SELECT count(*) FROM predictions WHERE run_id = ?", [run_id]
).fetchone()
```

1. `fetchone()` returns a tuple, even for one value: `(24,)`.
2. `(n_rows,) = ...` unpacks it (1b [PY-4](./phase-1b.md#py-4)). It also fails loudly if the tuple does
   not have exactly one item.
3. Call `fetchone()` right away. In DuckDB, `con.execute` returns `con` itself. A second `execute`
   replaces the first result, so an older variable now reads the new one.

The trap, with real output: two `execute` calls, then two `fetchone` calls.

```text
E           AssertionError: assert (24,) == ('dev', 'fake', 0)
```
