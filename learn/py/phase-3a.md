# Python for Phase 3a

This file explains the new Python in Part 3a. Read one section when the main doc links to it. JSON with
Pydantic is in 1c ([PY-3](./phase-1c.md#py-3)). Modules and packages are in 0a ([PY-2](./phase-0a.md#py-2)),
and `tmp_path` is in 0b ([PY-8](./phase-0b.md#py-8)).

<a id="py-1"></a>
## PY-1. `Callable` and a name for a type

```python
Parser = Callable[[Path], ParsedDoc]
```

1. `Callable[[Path], ParsedDoc]` means "a function that takes a `Path` and returns a `ParsedDoc`".
2. `Parser = ...` gives that type a short name. It is a normal variable.

In TypeScript: `type Parser = (path: string) => ParsedDoc`. Python does not check it at run time. It is
for readers and editors.

<a id="py-2"></a>
## PY-2. `extract_text() or ""`

```python
pages = [page.extract_text() or "" for page in PdfReader(pdf_path).pages]
```

`a or b` gives `a` if `a` is truthy. If not, it gives `b`. So `None` becomes `""`, and `ParsedDoc` always
gets a list of strings.

It is like `x || ""` in JS. An empty string also goes to the right side, and that gives `""` again.

<a id="py-3"></a>
## PY-3. `with_name` and `replace`

```python
temp = path.with_name(path.name + ".tmp")
temp.write_text(doc.model_dump_json(), encoding="utf-8")
temp.replace(path)
```

1. `path.name` is the last part of the path, like `doc-1.json`.
2. `with_name` gives a new path in the same folder: `doc-1.json.tmp`.
3. `temp.replace(path)` renames the file over `path`. On one disk, this happens all at once.

We use `with_name` and not `with_suffix`. Our `doc_id` has dots, like `EX-10.1`, and `with_suffix` changes
only the part after the last dot.

In Node: `fs.writeFileSync(tmp, data); fs.renameSync(tmp, path)`.

<a id="py-4"></a>
## PY-4. Code in `__init__.py`

```python
from docintel.domain.parse import parse_doc
```

Importing a folder runs its `__init__.py`. So names defined there can be imported from the folder.

It is like `index.js` in a folder: `require('./parse')` runs `parse/index.js`. Other folders in this
project keep `__init__.py` empty. Here, it is the front door of the package.

<a id="py-5"></a>
## PY-5. A class you can call: `__call__`

```python
class CountingParser:
    def __init__(self):
        self.calls = 0

    def __call__(self, pdf_path: Path) -> ParsedDoc:
        self.calls += 1
        ...
```

1. `parser = CountingParser()` makes an object.
2. `parser(path)` runs `__call__`, so the object works where a function is expected.
3. It can also remember things. Here, `parser.calls` counts the calls.

In JS, you would use a function with a variable outside it (a closure). Python can do that too, but a
small class is easier to read in a test.
