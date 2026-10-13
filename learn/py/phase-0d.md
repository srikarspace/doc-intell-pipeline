# Python for Phase 0d

This file explains the new Python in Part 0d. Read one section when the main doc links to it.
Comprehensions and fixtures are in the 0b companion ([PY-4](./phase-0b.md#py-4),
[PY-8](./phase-0b.md#py-8)).

<a id="py-1"></a>
## PY-1. A comprehension with two `for`s

A comprehension can have two `for` parts. It reads left to right, like two nested loops.

```python
names = [f for group in FIELDS.values() for f in group]
```

Read it like this:

1. `for group in FIELDS.values()`: go through the 4 lists in `FIELDS`.
2. `for f in group`: go through the 3 names in each list.
3. `f`: put each name in the new list.

Result: one list of 12 names. In JS: `Object.values(FIELDS).flat()`.

`FIELDS.values()` gives the values of a dict, like `Object.values(obj)`. `.keys()` and `.items()`
work like `Object.keys` and `Object.entries`.

<a id="py-2"></a>
## PY-2. `re.split` with `maxsplit`

`re.split(pattern, text)` cuts a string wherever the regex matches. `maxsplit=1` stops after the
first cut, so you get at most two parts.

```python
re.split(r"_| - ", doc_id, maxsplit=1)[0].lower()
```

Example: `"Monsanto Company - SECOND A_R ..."` becomes `["Monsanto Company", "SECOND A_R ..."]`.
`[0]` keeps the left part.

- `r"_| - "` means "`_` or ` - `". The `|` is "or", as in JS regex.
- The `r` before the quotes makes a **raw string**: a backslash stays a backslash. Always use it
  for regex.
- In JS: `docId.split(/_| - /)[0].toLowerCase()`. JS `split` has a limit argument too, but it
  drops the rest of the string instead of keeping it in the last part.

<a id="py-3"></a>
## PY-3. `defaultdict` and `setdefault`

**`defaultdict(list)`** is a dict that makes an empty list the first time you use a missing key.
So you can add to a list without checking first.

```python
docs = defaultdict(list)
docs[fam].append(doc_id)       # no KeyError, even the first time
```

In JS you would write `(docs[fam] ??= []).push(docId)`. With lodash, the whole loop is
`_.groupBy(rows, r => family(r.doc_id))`.

**`d.setdefault(key, value)`** sets the key only if it is not there yet. If it is there, nothing
changes.

```python
ftype.setdefault(fam, SAME_TYPE.get(ctype, ctype))
```

So the first contract of a family decides its type. In JS: `ftype[fam] ??= type`.

**`d.get(key, default)`** reads a key, or gives `default` when the key is missing. In JS:
`SAME_TYPE[ctype] ?? ctype`.

<a id="py-4"></a>
## PY-4. `random.Random(seed)` and `sorted`

`random.Random(seed)` makes your own random generator. The same seed gives the same numbers, in
the same order, every time.

```python
rng = random.Random(seed)
rng.shuffle(fams)              # changes fams in place, returns None
```

JS has no built-in seeded generator. `Math.random()` is different every time, so you would need
an npm package like `seedrandom`.

Things to know:

- **Own generator, not the shared one.** `random.shuffle(...)` uses one generator shared by the
  whole program. Any other code can move it forward. Break 2 shows what happens.
- **Same input order.** A seed makes the shuffle repeatable only if the list starts in the same
  order. That is why we use `ORDER BY doc_id` and `sorted(...)` first.
- **`sorted(x)`** returns a new sorted list. `x.sort()` sorts in place. Like
  `[...x].sort()` and `x.sort()` in JS. `sorted(d)` on a dict sorts its keys.
- **Dict order.** A Python dict keeps the order you added keys, like a JS `Map`.

<a id="py-5"></a>
## PY-5. Placeholders: `?` and `$name`

In 0b, `executemany` filled `$doc_id`-style placeholders from dicts. With tuples, use `?`. Each
`?` takes the next value of the tuple, in order:

```python
con.executemany("INSERT INTO splits VALUES (?, ?)", sorted(split_of.items()))
```

`split_of.items()` gives `(doc_id, split)` pairs. `sorted` sorts them by `doc_id`. Each pair fills
the two `?`.

The same works for one query with `execute` and a list of values:

```python
con.execute("SELECT count(DISTINCT category) FROM labels WHERE list_contains(?, category)", [names])
```

`con.sql` takes named values through `params`:

```python
con.sql(query, params={"names": names})      # $names in the query gets this list
```

The rule from 0b still holds: never paste values into SQL with an f-string. Placeholders handle
quotes and lists safely.

<a id="py-6"></a>
## PY-6. Sets

A **set** holds each value once, with no order. In JS: `new Set()`.

```python
assert {split for _, split in rows} == {"dev", "test"}
```

- `{x for ...}` is a set comprehension. Curly braces with one value per item (no `key: value`).
- Two sets are `==` if they have the same items, in any order.
- `s.add(x)` adds one item. Adding it twice changes nothing.
- `_` is a name for a value you do not need. Here it skips the `doc_id`.

In the family test, `sides.setdefault(family(doc_id), set()).add(split)` builds, for each family,
the set of sides it is on. A family is fine when its set has one item.

<a id="py-7"></a>
## PY-7. Keyword arguments and defaults

```python
def make_splits(con, seed: int = 0, n_docs: int = 100, dev_share: float = 0.5): ...

make_splits(con)                       # seed 0, 100 docs, 0.5
make_splits(con, seed=7, n_docs=12)    # change two, keep dev_share 0.5
```

You can pass any parameter by its name, in any order. Parameters you skip get their default. In
JS, you would pass an options object: `makeSplits(con, { seed: 7, nDocs: 12 })`.

Python checks the names. `make_splits(con, sed=7)` fails with `TypeError: ... unexpected keyword
argument 'sed'`. A typo in a JS options object fails silently.
