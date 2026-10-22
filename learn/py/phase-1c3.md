# Python for Phase 1c3

This file explains the new Python (and a little SQL) in Part 1c3. Read one section when the main
doc links to it. Dict merge with `|` is in the 0b companion ([PY-6](./phase-0b.md#py-6)).

<a id="py-1"></a>
## PY-1. `uv add --dev`: a library for developers only

```sh
$ uv add --dev matplotlib
```

1. uv finds a version of matplotlib that fits your other libraries, and installs it in `.venv`.
2. It writes `matplotlib` in the `[dependency-groups]` `dev` list of `pyproject.toml`, next to
   `pytest` and `ruff`.
3. It updates `uv.lock`, so a fresh clone gets the same version.

It is `npm install -D matplotlib`. The Docker image in Phase 4 can install without the dev
group, so the API does not carry a chart library it never uses.

<a id="py-2"></a>
## PY-2. `x if test else y` inside a dict

```python
return {
    "precision": tp / (tp + fp) if tp + fp else None,
    "recall": tp / (tp + fn) if tp + fn else None,
}
```

1. `a if test else b` is one value: `a` when `test` is true, else `b`. In JS:
   `test ? a : b`. Python puts the test in the middle.
2. `if tp + fp` asks "is this number not zero?". `0` counts as false, any other number as true.
   So `tp / (tp + fp)` only runs when it cannot divide by zero.
3. Each line of the dict is one value, so the whole function is one `return`.

<a id="py-3"></a>
## PY-3. matplotlib: `subplots`, `barh`, `ax`

```python
fig, ax = plt.subplots(figsize=(8, 5.5))
ax.barh([i + 0.17 for i in y], [r["precision"] or 0 for r in rows], height=0.3,
        color="#2a78d6", label="precision")
ax.set_yticks(y, [r["name"] for r in rows])
```

- `plt.subplots()` makes a figure (`fig`, the whole image) and one chart area (`ax`, short for
  "axes"). `figsize` is width and height in inches.
- `ax.barh(ys, widths)` draws horizontal bars: one bar at each `y`, as long as its width.
  `height` is the thickness of a bar, in rows. `barh` with "h" is horizontal; `bar` is upright.
- Two bar sets at `i + 0.17` and `i - 0.17` sit next to each other, one pair per field.
- `set_yticks(positions, labels)` writes the field names at the row positions.
- `ax.spines` are the four frame lines around the chart. We hide three of them.

In the notebook, the last figure of a cell is shown under the cell. In JS, the closest is a
chart library like Chart.js, but matplotlib draws a picture, not a web page.

<a id="py-4"></a>
## PY-4. `sort(key=lambda ...)`

```python
rows.sort(key=lambda r: r["f1"] or 0)
```

1. `lambda r: r["f1"] or 0` is a tiny function with no name. In JS: `r => r.f1 ?? 0`.
2. `key=` tells `sort` what to compare: here, each row's F1. Python calls `key` once per row.
3. `or 0` puts an empty F1 (`None`) first, like a 0. Python cannot compare `None` with a number.
4. `.sort()` changes the list in place. `sorted(rows, key=...)` would make a new list.

In JS you write a compare function: `rows.sort((a, b) => (a.f1 ?? 0) - (b.f1 ?? 0))`.

<a id="py-5"></a>
## PY-5. DuckDB JSON paths: `->>'$.value'`

```sql
p.answer->>'$.value' AS model_value, p.answer->>'$.quotes[0]' AS model_quote
```

- `answer` is a `JSON` column. `$` is the whole JSON value. `$.value` is its `value` key.
  `$.quotes[0]` is the first item of `quotes`. Indexes start at 0, like JS.
- `->>` returns the part as text: `30 days`. `->` returns it as JSON: `"30 days"`, with quotes.
- A missing key gives `NULL`, not an error. A yes/no field has no `value`, so it is `NULL`.

In JS this is `JSON.parse(answer).quotes[0]`. In SQL, the database does it for every row.

<a id="py-6"></a>
## PY-6. A query inside `SELECT`

```sql
(SELECT any_value(span_text) FROM labels l
 WHERE l.doc_id = s.doc_id AND l.category = $category AND l.is_present) AS gold_span
```

1. The small query in brackets runs once for each row of the outer query.
2. It can use the outer row: `s.doc_id` is the contract of the current score row.
3. It must return one value. `any_value` picks one span if there are several (1b2
   [PY-6](./phase-1b2.md#py-6)).

A `JOIN` would give one row per gold span, so a contract with 3 spans would print 3 times.
The inner query keeps one row per miss.

<a id="py-7"></a>
## PY-7. `pytest.approx`

```python
assert prf(8, 2, 8) == {"precision": 0.8, "recall": 0.5, "f1": pytest.approx(16 / 26)}
```

Float math is not exact: `2 * 0.8 * 0.5 / 1.3` and `16 / 26` can differ in the last digit.
`pytest.approx(x)` is equal to any number very close to `x`. It also works inside a dict, as
here. In Jest: `expect(f1).toBeCloseTo(16 / 26)`.

`0.8` and `0.5` need no `approx`: `8 / 10` and `8 / 16` give exactly those floats.
