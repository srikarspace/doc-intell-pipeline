# Python for Phase 4b2

This file explains the new Python in Part 4b2. Read one section when the main doc links to it. Error types and a
status map are in 4a ([PY-6](./phase-4a.md#py-6)). `with` is in 4b ([PY-5](./phase-4b.md#py-5)).

<a id="py-1"></a>
## PY-1. `with db() as con`: close the file when done

```python
with db() as con:
    con.execute("INSERT INTO requests ...", values)
```

1. `db()` opens the DuckDB file, and gives back a connection.
2. A DuckDB connection works with `with`. When the block ends, it closes, even after an error.
3. Closing frees the file lock, so another program can open the file.
4. In Node, it is like `const con = await open(); try { ... } finally { await con.close(); }`.

Without `with`, the connection stays open until Python cleans it up, and the lock stays with it.

<a id="py-2"></a>
## PY-2. `row |= {...}`, and building SQL from a dict

```python
row = {"request_id": request_id, "route": route}
row |= {"parser": result.parser, "pages": result.pages}

columns = ", ".join(row)
marks = ", ".join("?" for _ in row)
```

1. `row |= other` adds the keys of `other` into `row`, in place. In JS: `Object.assign(row, other)`.
2. Looping over a dict gives its **keys**. So `", ".join(row)` is `"request_id, route, parser, pages"`. In JS:
   `Object.keys(row).join(", ")`.
3. `"?" for _ in row` makes one `?` per key. `_` is a name for "a value I do not use".
4. `list(row.values())` gives the values in the same order as the keys. Python dicts keep the order you added keys
   in, like JS objects with string keys.

Real values for a failed request:

```text
columns  request_id, route, sample_id, filename, sha256, fields, status, error
marks    ?, ?, ?, ?, ?, ?, ?, ?
```

<a id="py-3"></a>
## PY-3. `model_validator` and `Self`

```python
class Review(BaseModel):
    action: Literal["accept", "modify"]
    value: Value = None

    @model_validator(mode="after")
    def value_only_when_modified(self) -> Self:
        if self.action == "modify" and self.value is None:
            raise ValueError("modify needs a value")
        ...
        return self
```

1. A field type checks one field. A **model validator** checks several fields together.
2. `mode="after"` runs it after each field is checked, so `self.action` is already a valid `"accept"` or `"modify"`.
3. Raising `ValueError` turns into a 422, with your message in `msg`.
4. It must return `self`. `Self` is the type "this same class".

In JS with zod, it is `.refine((r) => r.action !== "modify" || r.value != null, "modify needs a value")`.

<a id="py-4"></a>
## PY-4. `fetchone`, `fetchall` and `RETURNING`

```python
found = con.execute("SELECT result FROM requests WHERE request_id = ?", [request_id]).fetchone()
gone = con.execute("DELETE FROM reviews WHERE review_id = ? RETURNING review_id", [review_id]).fetchall()
return bool(gone)
```

1. `fetchone()` gives the first row as a tuple, or `None` when there is no row. `found[0]` is its first column.
2. `fetchall()` gives every row, as a list of tuples.
3. `RETURNING review_id` makes a `DELETE` give back the rows it removed. No row means nothing was deleted.
4. `bool([])` is `False`, `bool([("5ea8...",)])` is `True`. In JS, an empty array is truthy, so you would write
   `gone.length > 0`.
