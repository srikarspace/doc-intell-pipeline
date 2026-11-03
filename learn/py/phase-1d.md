# Python for Phase 1d

This file explains the new Python (and a little SQL) in Part 1d. Read one section when the main doc
links to it. `defaultdict` and `random.Random` are in the 0d companion
([PY-3](./phase-0d.md#py-3), [PY-4](./phase-0d.md#py-4)).

<a id="py-1"></a>
## PY-1. `CREATE TABLE ... AS SELECT` and comparing three columns

```sql
CREATE TABLE scores_r1 AS SELECT * FROM scores
```

1. DuckDB makes a new table with the same columns as the `SELECT` result.
2. It copies the rows now. Later changes to `scores` do not reach `scores_r1`.
3. It does not copy the primary key. For this snapshot, that does not matter.

In JS, it is like `const scoresR1 = structuredClone(scores)`.

```sql
WHERE (o.tp, o.fp, o.fn) <> (n.tp, n.fp, n.fn)
```

The brackets make a group of three values. `<>` means "not equal". The row is kept if any of the
three is different. It is shorter than `o.tp <> n.tp OR o.fp <> n.fp OR o.fn <> n.fn`.

<a id="py-2"></a>
## PY-2. `rng.sample` and `rng.choices`

```python
rng.sample(rows, min(5, len(rows)))           # the error sample: no repeats
rng.choices(docs, k=len(docs))                # the bootstrap: repeats allowed
```

- `sample` picks different items, like dealing cards. Asking for more items than exist raises a
  `ValueError`, so we use `min(5, len(rows))`.
- `choices` puts each item back after it picks. One contract can appear three times, and another not
  at all. That is what a bootstrap needs.

JS has neither. You would use lodash `_.sampleSize` for `sample`, and write a small loop for `choices`.

<a id="py-3"></a>
## PY-3. `[*parts, " ".join(parts)]`

```python
parts = (answer or "").split(";")
golds = [norm(part) for part in [*parts, " ".join(parts)]]
```

For `California; Hong Kong`:

1. `parts` is `["California", " Hong Kong"]`.
2. `*parts` puts each item in the new list. It works like `...parts` in JS.
3. The new list is `["California", " Hong Kong", "California  Hong Kong"]`.
4. `norm` turns each one into a clean place name.

<a id="py-4"></a>
## PY-4. `re.search(r"\d{4}", span)`

```python
not any(re.search(r"\d{4}", span) for span in spans)
```

1. `\d{4}` means four digits in a row.
2. The `r` before the string means "raw". Python leaves the backslash alone. JS has `/\d{4}/`.
3. `re.search` finds the first match anywhere, or returns `None`. A match counts as true, and `None`
   counts as false. It is like `span.match(/\d{4}/)` in JS.

`re.findall` is in 1b2 ([PY-2](./phase-1b2.md#py-2)). It returns all matches. Here we only need to
know if one exists.

<a id="py-5"></a>
## PY-5. `a <= b` on sets

```python
a, b = tokens(name), tokens(span)
a <= b or b <= a
```

On sets, `<=` means "every item of a is also in b". It does not compare sizes as numbers.

- `{"acme"} <= {"acme", "inc"}` is `True`.
- `{"acme", "ltd"} <= {"acme", "inc"}` is `False`.

The long form is `a.issubset(b)`. JS sets now have `a.isSubsetOf(b)`. Other set operators are in 1b2
([PY-3](./phase-1b2.md#py-3)).

<a id="py-6"></a>
## PY-6. `all(any(...))`: a loop inside a loop

```python
bool(names) and all(any(name_ok(n, s) for s in spans) for n in names)
```

Read it from the outside in:

1. For each name `n`, is there any span that matches?
2. Are all the names like that?

In JS: `names.every(n => spans.some(s => nameOk(n, s)))`.

`all([])` is `True`, because nothing failed. That is why `bool(names)` comes first. With no names, the
answer must be false. JS has the same trap: `[].every(...)` is `true`.

<a id="py-7"></a>
## PY-7. `zip(docs, docs[1:] + docs[:1])`: each item with the next one

```python
for doc, next_doc in zip(docs, docs[1:] + docs[:1]):
```

With `docs = ["a", "b", "c"]`:

1. `docs[1:]` is `["b", "c"]`, and `docs[:1]` is `["a"]`. Together: `["b", "c", "a"]`.
2. `zip` walks both lists at once and gives pairs: `("a", "b")`, `("b", "c")`, `("c", "a")`.
3. The last contract is paired with the first, so each contract gets one partner.

JS has no built-in `zip`. Lodash has `_.zip`.
