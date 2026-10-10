# Python for Phase 0b

Covers the Python this part introduces; read sideways, one section at a time.

<a id="py-1"></a>
## PY-1. pathlib: paths as objects

`Path` is a file path you can do things with, instead of a string you glue together. `/` joins
parts, like `path.join` in Node.

```python
txt_path = cuad_dir / "full_contract_txt" / f"{stem}.txt"
```

Useful bits used in 0b:

| Python | Node |
|---|---|
| `p.stem` (`"Acme"` for `Acme.pdf`) | `path.parse(p).name` |
| `p.suffix` (`".pdf"`) | `path.extname(p)` |
| `p.parent.name` (the folder) | `path.basename(path.dirname(p))` |
| `p.exists()` | `fs.existsSync(p)` |
| `p.read_text(encoding="utf-8")` | `fs.readFileSync(p, 'utf8')` |
| `folder.rglob("*")` (every file, any depth) | a recursive `fs.readdirSync` |
| `p.mkdir(parents=True, exist_ok=True)` | `fs.mkdirSync(p, { recursive: true })` |

f-strings (`f"{stem}.txt"`) are template literals: `` `${stem}.txt` ``.

<a id="py-2"></a>
## PY-2. Type hints

Annotations after `:` and `->` say what a function takes and returns. Python does **not** check
them at runtime; editors and type checkers do. Like TypeScript types that vanish at runtime.

```python
def count_pages(pdf_path: Path | None) -> int | None:
```

- `Path | None` is a union: `Path | null` in TS.
- `dict[str, tuple[Path, str]]` is `Record<string, [Path, string]>`. A **tuple** is a fixed-size,
  read-only list, often used to return two things: `return len(contracts), len(labels)`.
- `def connect(path: Path | str = DB_PATH)`: `= DB_PATH` is a default argument, as in JS.

<a id="py-3"></a>
## PY-3. `with`: open, use, always close

`with` runs setup, gives you the object, and guarantees cleanup when the block ends, even after an
error. Files, zips and DB connections all support it.

```python
with connect() as con:
    n_contracts, n_labels = load_cuad(con, cuad_dir)
# con is closed here, error or not
```

The JS equivalent is a `try { ... } finally { con.close() }` you never have to write. Without
`with`, an exception halfway through `load_cuad` could leave the DuckDB file locked.

<a id="py-4"></a>
## PY-4. Comprehensions

A comprehension builds a list or dict from a loop in one expression. Read it as `map` + `filter`.

```python
{_key(p.stem): (p, p.parent.name) for p in pdfs if p.suffix.lower() == ".pdf"}
```

JS:

```js
Object.fromEntries(
  pdfs.filter(p => p.suffix.toLowerCase() === '.pdf')
      .map(p => [key(p.stem), [p, p.parent.name]])
)
```

- `[x for x in items if cond]` makes a list, `{k: v for ...}` a dict.
- Keep them to one condition. Anything longer reads better as a normal `for` loop.

<a id="py-5"></a>
## PY-5. Generators and `yield`

A function with `yield` returns a **generator**: it produces values one at a time, pausing between
them. Same as a JS `function*`.

```python
def iter_labels(cuad_dir: Path):
    for doc in read_docs(cuad_dir):
        ...
            yield row | ABSENT
```

```python
labels = list(iter_labels(cuad_dir))   # run it to the end, collect every row
```

- Nothing runs until something asks for values (`list(...)`, a `for` loop). Like `[...gen()]`.
- Why not build a list inside? The generator keeps "how to make a row" separate from "what to do
  with rows". A later part can stream rows elsewhere without touching the parser.
- A generator can be consumed once. Call the function again for a fresh one.

<a id="py-6"></a>
## PY-6. Dict merge `|` and the `or` default

`a | b` makes a new dict with `b`'s keys added over `a`'s, like `{...a, ...b}`:

```python
row = {"doc_id": doc["title"], "category": category}
yield row | ABSENT    # {"doc_id": ..., "category": ..., "span_text": None, ...}
```

Neither `row` nor `ABSENT` is changed. That matters for `ABSENT`, which is shared by every
absent row.

`x or default` returns `default` when `x` is "falsy" (`None`, `0`, `""`, empty list), like JS `||`:

```python
pdf_path, contract_type = _lookup(pdfs, stem) or (None, None)
```

`_lookup` returns a `(path, type)` tuple or `None`; `or (None, None)` keeps the unpacking on the
left from crashing. Python has no `??`; `or` is the idiom, so mind values like `0` that are falsy.

<a id="py-7"></a>
## PY-7. `if __name__ == "__main__":`

Every module has a `__name__`. When imported, it is the module's name (`"docintel.evals.datasets"`).
When run as the program (`python -m docintel.evals.datasets`), it is `"__main__"`.

```python
if __name__ == "__main__":
    main()
```

So `make data` runs `main()`, while tests can `import load_cuad` without starting a 106 MB
download. Node equivalent: `if (require.main === module) main()`.

<a id="py-8"></a>
## PY-8. pytest fixtures and `tmp_path`

A **fixture** is a function pytest runs before a test to build what it needs. A test asks for it by
naming it as a parameter. No imports, no calls: pytest matches by name.

```python
@pytest.fixture
def con(cuad_dir):                # needs the cuad_dir fixture first
    with connect(":memory:") as c:
        assert load_cuad(c, cuad_dir) == (2, 4)
        yield c                   # the test runs here; after it, the `with` closes c


def test_absent_label_is_a_row(con):   # gets a loaded DB
    ...
```

- `@pytest.fixture` is a **decorator**: a function that wraps the one below it. Think of a
  higher-order function applied at definition time.
- `tmp_path` is a built-in fixture: a fresh empty temp folder per test, deleted later. Jest's
  closest equivalent is creating a temp dir in `beforeEach`.
- Fixtures can use fixtures (`con` uses `cuad_dir` uses `tmp_path`). Each test gets fresh copies,
  so tests never share state.
- `yield` in a fixture splits setup (before) from teardown (after), like `beforeEach` + `afterEach`
  in one function.
