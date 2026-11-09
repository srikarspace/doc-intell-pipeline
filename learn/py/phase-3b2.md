# Python for Phase 3b2

This file explains the new Python in Part 3b2. Read one section when the main doc links to it. A function that returns
a function is in 1a2 ([PY-7](./phase-1a2.md#py-7)).

<a id="py-1"></a>
## PY-1. `lru_cache` with an argument

```python
@lru_cache
def get_converter(do_ocr: bool = DO_OCR):
```

`lru_cache` remembers the result for each set of arguments. So `get_converter(True)` and `get_converter(False)` are
built once each. In JS, it is a memoize function with a `Map` keyed by the arguments.

Called with no argument, it is stored under another key than `get_converter(False)`, even if the value is the same. We
always pass `do_ocr`, so that does not cost a second load.

<a id="py-2"></a>
## PY-2. A function per cell

```python
def text_of(cell: str):
    def read(con: duckdb.DuckDBPyConnection, doc_id: str) -> str:
        return cached_text(cell, doc_id)

    return read


PARSERS = {"cuad_txt": cuad_txt, **{cell: text_of(cell) for cell in CELLS}}
```

1. Each call to `text_of` makes a new `read` that remembers its own `cell`.
2. `{cell: ... for cell in CELLS}` builds a dict in one line. In JS: `Object.fromEntries(CELLS.map(...))`.
3. `**` spreads it into the outer dict, like `...` in JS.

A plain `lambda` inside the loop would be a bug. All of them would use the last `cell`. It is the same trap as `var` in
a JS `for` loop.

<a id="py-3"></a>
## PY-3. `dict` of costs, `set`

```python
paid = {c: split_cell(c)[0] for c in cells if split_cell(c)[0] in MODELS}
costs = {p: page_costs(p) for p in set(paid.values())}
```

1. `paid` maps each paid cell to its parser, keeping only the vision ones.
2. `set(...)` removes duplicates, like `new Set(...)` in JS. Two cells can use the same model.
3. So the price of each model is fetched once.
