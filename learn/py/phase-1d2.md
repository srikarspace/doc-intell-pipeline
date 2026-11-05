# Python for Phase 1d2

This file explains the new Python (and one shell tool) in Part 1d2. Read one section when the main doc
links to it. `rng.sample` and `rng.choices` are in the 1d companion ([PY-2](./phase-1d.md#py-2)), and
`re.search` is there too ([PY-4](./phase-1d.md#py-4)).

<a id="py-1"></a>
## PY-1. Chained `if ... else`

```python
mark = "RIGHT" if tp else "FP+FN" if fp and fn else "FP" if fp else "FN"
```

Read it from left to right, and stop at the first true test:

1. If `tp` is not 0, the answer is `"RIGHT"`.
2. Else, if both `fp` and `fn` are not 0, the answer is `"FP+FN"`.
3. Else, if `fp` is not 0, the answer is `"FP"`.
4. Else, the answer is `"FN"`.

In JS: `tp ? "RIGHT" : fp && fn ? "FP+FN" : fp ? "FP" : "FN"`. The order of the words is different: in
Python, the value comes first and the test comes second.

<a id="py-2"></a>
## PY-2. `{mark:5}` and other f-string formats

```python
print(f"{mark:5} {doc_id[:28]}")                 # "FP    Conformis..."
print(f"{count:2} errors fixed")                 # " 5 errors fixed"
print(f"total: {flipped / tried:.1%}")           # "total: 2.2%"
```

After the `:`, you say how the value should look:

- `5` means use at least 5 characters. Text gets spaces on the right, and numbers on the left. It is like
  `padEnd(5)` and `padStart(2)` in JS.
- `.1%` multiplies by 100, keeps one decimal, and adds `%`. In JS: `(x * 100).toFixed(1) + "%"`.

<a id="py-3"></a>
## PY-3. The `re.compile` pattern

```python
PHRASE = re.compile(
    r"\b(consequential|indirect|incidental|punitive|special|exemplary)\b"
    r"[^.;]{0,80}\b(damages?|loss(es)?)\b",
    re.I,
)
```

`re.compile` makes a pattern you can use many times, like `new RegExp(...)` in JS. `re.I` means ignore
case, like the `i` flag in `/.../i`. Two strings next to each other become one string.

Now the pattern itself:

1. `\b` is the edge of a word. So `\bindirect\b` does not match `indirectly`. That one detail fixes Round 3.
2. `(a|b)` means a or b.
3. `[^.;]{0,80}` means up to 80 characters that are not `.` or `;`. So both words must be in the same
   sentence or clause.
4. `damages?` means `damage` or `damages`. `loss(es)?` means `loss` or `losses`.

<a id="py-4"></a>
## PY-4. Reading `diff -u`

```diff
-- non_compete: a party may not compete with the other party, or may not work in a certain place,
+- non_compete: a party may not compete with the other party, may not work in a certain place,
```

This is a shell tool, not Python. It is the same format as a git diff.

- A line starting with `-` is only in the old file.
- A line starting with `+` is only in the new file.
- A line starting with a space is in both.
- A line starting with `@@` says where in the file this part is.

Here, the second `-` or `+` is just the markdown list marker from the prompt.

<a id="py-5"></a>
## PY-5. `result[doc_id, r["field"]]`: a tuple as a dict key

```python
result[doc_id, r["field"]] = (r["tp"], r["fp"], r["fn"])
```

The key is a pair of values: `(doc_id, field)`. The brackets of the tuple are optional inside `[...]`.
Tuples can be keys because they cannot change.

JS objects cannot do this. A JS `Map` compares arrays by identity, so people often join the parts:
``map.set(`${docId}|${field}`, value)``. Python needs no such trick.

`a[key] != b[key]` compares the two tuples item by item. It is true if any of the three numbers differ.

<a id="py-6"></a>
## PY-6. `for f, doc, *counts, answer in rows`

```python
for f, doc, *counts, answer in con.execute(CHANGED, [old, new]).fetchall():
```

Each row has 9 items. `f` takes the first, `doc` takes the second, and `answer` takes the last. `*counts`
collects all the others into a list. So `counts` has 6 numbers: `counts[:3]` is the old marks, and
`counts[3:]` is the new marks.

JS has `const [f, doc, ...counts] = row`, but in JS the rest must come last. Python lets it sit in the
middle.

<a id="py-7"></a>
## PY-7. `sha256(...).hexdigest()`: a fingerprint

```python
sha256(system.encode()).hexdigest()[:12] == "e4bcfc8ac5b5"
```

1. `system.encode()` turns text into bytes. A hash works on bytes, not on text.
2. `sha256` computes a hash. Change one letter of the input, and the output changes completely.
3. `.hexdigest()` returns the hash as a string of 64 hex characters.
4. `[:12]` keeps the first 12. This is enough to notice an accidental edit.

In Node: `createHash("sha256").update(text).digest("hex").slice(0, 12)`.
