# Python for Phase 0b

This file explains the new Python in Part 0b. Read one section when the main doc links to it.

<a id="py-1"></a>
## PY-1. pathlib: paths as objects

In Python, a file path can be a `Path` object, not just a string. You can ask a `Path` things, like
"what is the file name?" or "does this file exist?". You join parts with `/`, like `path.join` in
Node.

```python
txt_path = cuad_dir / "full_contract_txt" / f"{stem}.txt"
```

The ones we use in 0b, next to Node:

| Python | Node |
|---|---|
| `p.stem` (`"Acme"` for `Acme.pdf`) | `path.parse(p).name` |
| `p.suffix` (`".pdf"`) | `path.extname(p)` |
| `p.parent.name` (the folder) | `path.basename(path.dirname(p))` |
| `p.exists()` | `fs.existsSync(p)` |
| `p.read_text(encoding="utf-8")` | `fs.readFileSync(p, 'utf8')` |
| `folder.rglob("*")` (every file, any depth) | a recursive `fs.readdirSync` |
| `p.mkdir(parents=True, exist_ok=True)` | `fs.mkdirSync(p, { recursive: true })` |

`f"{stem}.txt"` is an **f-string**. It is the same as a JS template string: `` `${stem}.txt` ``.

<a id="py-2"></a>
## PY-2. Type hints

Type hints say what a function takes and what it gives back. They come after `:` and `->`.

```python
def count_pages(pdf_path: Path | None) -> int | None:
```

Read it like this: "`count_pages` takes a `Path` or `None`, and gives back an `int` or `None`."

Python does **not** check these hints when the code runs. Your editor and tools like mypy check
them. This is like TypeScript: the types are gone when the code runs.

More examples from 0b:

- `Path | None` means "a Path or None". In TypeScript: `Path | null`.
- `dict[str, tuple[Path, str]]` means "a dict with string keys, and each value is a pair (Path,
  string)". In TypeScript: `Record<string, [Path, string]>`.
- A **tuple** is a list with a fixed size that you cannot change. We often use it to return two
  things at once: `return len(contracts), len(labels)`.
- `def connect(path: Path | str = DB_PATH)`: the `= DB_PATH` part is a default value, the same as
  in JS.

<a id="py-3"></a>
## PY-3. `with`: open, use, always close

`with` opens something, lets you use it, and **always** closes it at the end. It closes it even
if an error happens. Files, zip files and database connections all work with `with`.

```python
with connect() as con:
    n_contracts, n_labels = load_cuad(con, cuad_dir)
# here, con is closed, with or without an error
```

In JS, you would write this by hand:

```js
const con = connect();
try { loadCuad(con, cuadDir); } finally { con.close(); }
```

Why it matters: if `load_cuad` crashes in the middle and nobody closes the connection, the DuckDB
file can stay locked. Then other programs cannot open it.

<a id="py-4"></a>
## PY-4. Comprehensions

A **comprehension** builds a list or a dict from a loop, in one line. Think of it as `map` and
`filter` together.

```python
{_key(p.stem): (p, p.parent.name) for p in pdfs if p.suffix.lower() == ".pdf"}
```

Read it from the middle:

1. `for p in pdfs`: go through each path.
2. `if p.suffix.lower() == ".pdf"`: keep only PDF files.
3. `_key(p.stem): (p, p.parent.name)`: for each one, add this key and value to the dict.

The same thing in JS:

```js
Object.fromEntries(
  pdfs.filter(p => p.suffix.toLowerCase() === '.pdf')
      .map(p => [key(p.stem), [p, p.parent.name]])
)
```

- `[x for x in items if cond]` makes a **list**. `{k: v for ...}` makes a **dict**.
- Keep them short, with at most one `if`. If it gets longer, a normal `for` loop is easier to read.

<a id="py-5"></a>
## PY-5. Generators and `yield`

A function with `yield` in it is a **generator**. It does not give back all values at once. It
gives back one value, pauses, and waits until someone asks for the next one. This is the same as
a `function*` in JS.

```python
def iter_labels(cuad_dir: Path):
    for doc in read_docs(cuad_dir):
        ...
            yield row | ABSENT
```

To get all the values, put it in `list(...)`:

```python
labels = list(iter_labels(cuad_dir))   # run it to the end, collect every row
```

Things to know:

- Nothing runs until something asks for values, like `list(...)` or a `for` loop. In JS:
  `[...gen()]`.
- Why not just build a list inside the function? Because then the function would decide what
  happens to the rows. With `yield`, the function only makes rows. Whoever calls it decides what to
  do with them (print one, save all, and so on).
- You can only go through a generator once. To start again, call the function again.

<a id="py-6"></a>
## PY-6. Dict merge `|` and the `or` default

**`a | b` merges two dicts.** It makes a new dict with the keys of `a`, plus the keys of `b`. If both
have the same key, `b` wins. In JS: `{...a, ...b}`.

```python
row = {"doc_id": doc["title"], "category": category}
yield row | ABSENT    # {"doc_id": ..., "category": ..., "span_text": None, ...}
```

`row` and `ABSENT` do not change. This is important for `ABSENT`, because every absent row uses the
same `ABSENT` dict.

**`x or default` gives a backup value.** If `x` is "empty-ish", you get `default`. Empty-ish
("falsy") values are `None`, `0`, `""` and empty lists. In JS: `x || default`.

```python
pdf_path, contract_type = _lookup(pdfs, stem) or (None, None)
```

`_lookup` gives back a pair `(path, type)`, or `None` when there is no match. The left side wants
two values. `None` is one value, so Python would crash. `or (None, None)` gives it two values.

Python has no `??` like JS. People use `or`. But be careful: `0` is also falsy, so `0 or 5` gives
`5`.

<a id="py-7"></a>
## PY-7. `if __name__ == "__main__":`

Every Python file has a hidden variable called `__name__`. Its value depends on how the file is
used:

- When another file **imports** it, `__name__` is the module name, like
  `"docintel.evals.datasets"`.
- When you **run** it directly (`python -m docintel.evals.datasets`), `__name__` is `"__main__"`.

```python
if __name__ == "__main__":
    main()
```

So `make data` runs the file, and `main()` runs. But when the test imports `load_cuad` from this
file, `main()` does not run, so the test does not start a 106 MB download.

In Node, the same idea is: `if (require.main === module) main()`.

<a id="py-8"></a>
## PY-8. pytest fixtures and `tmp_path`

A **fixture** is a function that pytest runs before a test. It prepares something the test needs,
like a database. The test asks for a fixture by using its name as a parameter. You do not import
it or call it. pytest matches the name for you.

```python
@pytest.fixture
def con(cuad_dir):                # needs the cuad_dir fixture first
    with connect(":memory:") as c:
        assert load_cuad(c, cuad_dir) == (2, 4)
        yield c                   # the test runs here; after it, the `with` closes c


def test_absent_label_is_a_row(con):   # gets a loaded DB
    ...
```

Things to know:

- `@pytest.fixture` is a **decorator**. A decorator is a function that wraps the function below
  it, to add extra behavior. Here, it tells pytest "this is a fixture".
- `tmp_path` is a fixture that pytest gives you for free. It is a new, empty folder for each test.
  pytest deletes it later. In Jest, you would make a temp folder in `beforeEach`.
- Fixtures can use other fixtures. `con` uses `cuad_dir`, and `cuad_dir` uses `tmp_path`. Each test
  gets fresh copies, so one test cannot change data for another test.
- `yield` in a fixture splits it into two halves. The code before `yield` runs before the test
  (like `beforeEach`). The code after `yield` runs after the test (like `afterEach`).
