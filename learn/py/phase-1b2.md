# Python for Phase 1b2

This file explains the new Python (and a little SQL) in Part 1b2. Read one section when the main
doc links to it. `re` basics are in the 0d companion ([PY-2](./phase-0d.md#py-2)).

<a id="py-1"></a>
## PY-1. `str.rpartition`

`text.rpartition(sep)` cuts a string at the **last** `sep`. It always returns three parts:
before, the separator, after.

```python
category, _, tail = col.rpartition("-")
```

Examples from `master_clauses.csv`:

- `"Governing Law-Answer"` gives `("Governing Law", "-", "Answer")`.
- `"Notice Period To Terminate Renewal- Answer"` gives `(..., "-", " Answer")`. So we
  `strip()` the tail before we compare it.
- `"Filename"` has no `-`, so it gives `("", "", "Filename")`. The tail is not `Answer`, so it is
  skipped.

`_` is the name for the part we do not need. JS has no direct match. You would use
`lastIndexOf("-")` and two `slice` calls.

<a id="py-2"></a>
## PY-2. `re.findall`

`re.findall(pattern, text)` returns a list of every match.

```python
re.findall(r"[a-z0-9]+", "governed by the laws of michigan, 2017.")
# ['governed', 'by', 'the', 'laws', 'of', 'michigan', '2017']
```

`[a-z0-9]+` means "one or more letters or digits in a row". Everything else (spaces, commas,
dots) splits the words. In JS: `text.match(/[a-z0-9]+/g)`, but JS gives `null` for no match, and
Python gives `[]`.

<a id="py-3"></a>
## PY-3. Set operators: `&`, `|`, `-`

Sets were in 0d ([PY-6](./phase-0d.md#py-6)). They also have math operators:

```python
ta & tb                       # in both: the shared words
ta | tb                       # in either: all words
tokens(text) - {"the", "of"}  # in the first, not in the second
```

So `len(ta & tb) / len(ta | tb)` is Jaccard in one line. In JS you would write
`[...a].filter(x => b.has(x))` for `&`, and `new Set([...a, ...b])` for `|`.

<a id="py-4"></a>
## PY-4. `any(...)` with two `for`s

```python
return any(jaccard(q, s) >= THRESHOLD for q in quotes for s in spans)
```

1. The two `for`s go through every pair of one quote and one span, like the comprehension in
   0d ([PY-1](./phase-0d.md#py-1)).
2. For each pair, it computes `True` or `False`.
3. `any` returns `True` at the first `True`, and stops. If there are no pairs, it returns
   `False`.

In JS: `quotes.some(q => spans.some(s => jaccard(q, s) >= THRESHOLD))`. `all(...)` is the
partner, like `.every`.

<a id="py-5"></a>
## PY-5. String methods for dates: `split`, `zfill`, `isdigit`, `join`

```python
month, day, year = (text.split("/") + ["", ""])[:3]
parts = [year, month.zfill(2), day.zfill(2)]
return "-".join(known)
```

- `"11/14/17".split("/")` gives `["11", "14", "17"]`. Like JS `split`.
- `+ ["", ""]` then `[:3]` makes sure there are always 3 items, even for a bad text like `"2020"`
  with no `/`. `[:3]` takes the first 3, like `.slice(0, 3)`.
- `"9".zfill(2)` gives `"09"`: pad with zeros on the left. Like `padStart(2, "0")`. `"[]".zfill(2)`
  stays `"[]"`.
- `"17".isdigit()` is `True`. `"[]".isdigit()` is `False`. Like `/^\d+$/.test(s)`.
- `"-".join(["2017", "11"])` gives `"2017-11"`. In Python the separator comes first. In JS it is
  `["2017", "11"].join("-")`.

<a id="py-6"></a>
## PY-6. SQL: `LEFT JOIN`, `list(...) FILTER`, `any_value`

```sql
SELECT l.category, bool_or(l.is_present) AS present,
    list(l.span_text) FILTER (WHERE l.is_present) AS spans, any_value(a.answer) AS answer
FROM labels l LEFT JOIN answers a USING (doc_id, category)
```

- **`LEFT JOIN`** keeps every row of `labels`, even when `answers` has no match. The missing
  side is `NULL`. A plain `JOIN` would drop the 10 categories with no CUAD answer.
- **`labels l`** gives the table a short name, `l`, so `l.category` says which table.
- **`list(x)`** collects the values of a group into one list, like lodash `_.map` after a
  `_.groupBy`. With `FILTER (WHERE ...)` it keeps only some rows, as in 0c
  ([PY-4](./phase-0c.md#py-4)). An absent field gets `NULL`, so the code writes `spans or []`.
- **`any_value(x)`** takes one value of the group. All rows of a group have the same answer, so
  any one is fine.

<a id="py-7"></a>
## PY-7. f-string widths: `:36` and `!s`

```python
f"{r['field']:36} {r['rule']:8} {r['gold_present']!s:5}"
```

- `:36` pads the value to 36 characters, so the columns line up. Like `padEnd(36)`.
- `!s` turns the value into text first, with `str(...)`. `True`, `False` and `None` then pad like
  words.

This is only for printing in a checkpoint. In the notebook, DuckDB tables print better.

<a id="py-8"></a>
## PY-8. `@pytest.mark.parametrize`

One test function, many inputs. pytest runs it once per pair, as a separate test.

```python
@pytest.mark.parametrize(
    ("text", "expected"),
    [("11/14/17", "2017-11-14"), ("[]/[]/2020", "2020"), ...],
)
def test_norm_date(text, expected):
    assert norm_date(text) == expected
```

- The first argument names the parameters. The list gives one tuple per test.
- A failure names the case: `test_norm_date[11/14/17-2017-11-14]` (Break 2).
- In Jest: `test.each([["11/14/17", "2017-11-14"], ...])("%s", (text, expected) => ...)`.
