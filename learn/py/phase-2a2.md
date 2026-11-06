# Python for Phase 2a2

This file explains the new Python (and SQL) in Part 2a2. Read one section when the main doc links to it.
`re.search` is in the 1d companion ([PY-4](./phase-1d.md#py-4)), set operators are in 1b2
([PY-3](./phase-1b2.md#py-3)), and dict merge `|` is in 0b ([PY-6](./phase-0b.md#py-6)).

<a id="py-1"></a>
## PY-1. `CASE WHEN`: an if/else inside SQL

```sql
SELECT CASE WHEN fp > 0 AND fn > 0 THEN 'wrong' WHEN fp > 0 THEN 'made up'
            WHEN fn > 0 THEN 'missed' ELSE 'right, wrong quote' END AS kind
```

For each row, SQL tries the tests from top to bottom, and stops at the first true one:

1. Both `fp` and `fn` are above 0: `'wrong'`.
2. Else, `fp` is above 0: `'made up'`.
3. Else, `fn` is above 0: `'missed'`.
4. Else: `'right, wrong quote'`.

`END` closes it, and `AS kind` names the new column. In JS, it is a chain of `? :`, one per row. The
order matters: put the `AND` test first, or the second test takes those rows.

<a id="py-2"></a>
## PY-2. `set().union(*sets)` and `|=`

```python
phrases = set().union(*(sig[f] for f in PHRASE))
sig["A"] |= {(doc_id, i.field) for i in issues}
```

1. `a.union(b, c, d)` returns one set with every item of `a`, `b`, `c` and `d`.
2. `*(...)` unpacks the sets into separate arguments, like `...arrays` in JS.
3. `set()` is an empty set to start from. So the line works even when there are no sets.
4. `a |= b` adds every item of `b` into `a`. It is short for `a = a | b`.

In JS, the first line is `new Set(arrays.flatMap((s) => [...s]))`.

<a id="py-3"></a>
## PY-3. `match.group(0)` and `is None`

```python
match = MISSED[field].search(text)
if match is None:
    return []
detail = match.group(0)[:80]
```

1. `.search` returns a match object for the first place the pattern fits, or `None` if it fits nowhere.
2. `is None` checks for exactly `None`. Use `is` for `None`, not `==`. It is like `=== null` in JS.
3. `match.group(0)` is the text that matched. Example: `Limitation of Liability`. In JS, it is `m[0]`
   after `text.match(re)`.

<a id="py-4"></a>
## PY-4. `_` for values you skip

```python
if not all(ok for _, ok, _ in fields):
pred = from_rows([(field, answer) for field, _, answer in fields])
```

Each item in `fields` is a tuple of three: `(field, ok, answer)`. `_` is a normal name, but by habit it
means "I do not need this one".

1. The first line keeps only `ok`. `all(...)` is true if every `ok` is true.
2. The second line keeps `field` and `answer`, and skips `ok`.

In JS: `fields.every(([, ok]) => ok)`. JS can leave a hole. Python needs a name, so it uses `_`.

<a id="py-5"></a>
## PY-5. `monkeypatch.setitem`: swap a dict value in one test

```python
monkeypatch.setitem(runner.PARSERS, "cuad_txt", lambda con, doc_id: CONTRACT)
```

`PARSERS` is a dict: parser name to function. This line puts a fake function under `"cuad_txt"`, for
this test only. When the test ends, pytest puts the real one back.

1. `setattr` from 1c2 ([PY-5](./phase-1c2.md#py-5)) swaps a name in a module.
2. `setitem` swaps a key in a dict.

`validate` looks up `PARSERS[parser]` at run time, so it finds the fake. It never reads a CUAD file.

<a id="py-6"></a>
## PY-6. `GROUP BY ALL` (DuckDB)

```sql
SELECT doc_id, rule, count(*) FROM issues GROUP BY ALL ORDER BY 1
```

`GROUP BY ALL` means "group by every column that is not inside a function". Here, that is `doc_id` and
`rule`. It is the same as `GROUP BY doc_id, rule`. DuckDB has it, and many other databases do not.

`ORDER BY 1` sorts by the first column in the `SELECT`.

<a id="py-7"></a>
## PY-7. `first == again == 13`: chained comparisons

```python
assert first == again == 13
```

Python reads this as `first == again and again == 13`. So both must be 13.

JS reads `a === b === 13` as `(a === b) === 13`, which is `true === 13`, which is always false. Python
does not have this trap. It works the same for `<`: `0 <= x < 10`.
