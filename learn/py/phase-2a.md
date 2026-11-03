# Python for Phase 2a

This file explains the new Python in Part 2a. Read one section when the main doc links to it.
`re.findall` is in the 1b2 companion ([PY-2](./phase-1b2.md#py-2)), and `any` is in
[PY-4](./phase-1b2.md#py-4).

<a id="py-1"></a>
## PY-1. `Literal`: only these values

```python
severity: Literal["error", "warn"]
```

1. `Literal` lists the exact values a field may have.
2. Pydantic checks this when the object is made. `severity="oops"` raises a `ValidationError`.
3. In TypeScript it is `severity: "error" | "warn"`. The difference: TypeScript checks only at
   compile time, and Pydantic also checks when the code runs.

`str` would accept any typo, and the typo would only show up later, as a wrong count in a table.

<a id="py-2"></a>
## PY-2. `f" {' '.join(x)} "`: join, with a space on each side

```python
return f" {' '.join(quote_words)} " in f" {' '.join(source_words)} "
```

1. `' '.join(["at", "once"])` gives `"at once"`. In JS: `["at", "once"].join(" ")`.
2. The f-string adds one more space at the start and at the end: `" at once "`.
3. `a in b` on two strings asks if `a` is inside `b`. In JS: `b.includes(a)`.

Why the extra spaces? Without them, `"at"` is inside `"that"`. With them, `" at "` is not inside
`" that "`.

<a id="py-3"></a>
## PY-3. A window with a slice, `in` and `.index`

```python
window = source_words[pos + 1 : pos + 2 + MAX_GAP]
if word not in window:
    return False
pos += 1 + window.index(word)
```

1. `source_words[a : b]` makes a new list from position `a` up to, but not including, `b`. In JS:
   `source.slice(a, b)`. Near the end of the list, it returns fewer items. It never raises an error.
2. With `MAX_GAP = 60`, the window has 61 words: the next word, plus 60 that may be skipped.
3. `word not in window` searches the list. In JS: `!window.includes(word)`.
4. `window.index(word)` gives the first position in the window. In JS: `window.indexOf(word)`. The
   difference: `.index` raises a `ValueError` if the word is missing, and JS returns -1. We already
   checked, so it is safe.
5. `pos + 1 + index` turns the window position back into a position in `source_words`.

<a id="py-4"></a>
## PY-4. `any` with `enumerate`

```python
return any(
    word == quote_words[0] and follows_from(quote_words, source_words, start)
    for start, word in enumerate(source_words)
)
```

1. `enumerate(list)` gives `(position, item)` pairs. In JS: `list.entries()`.
2. `any(...)` stops at the first `True`. In JS, it is `source.some((word, start) => ...)`.
3. `and` also stops early. If the word is not the quote's first word, `follows_from` never runs. This
   keeps the check fast, because most words do not match.

<a id="py-5"></a>
## PY-5. `date(...)` and `except ValueError`

```python
year, month, day = (value.split("-") + ["01", "01"])[:3]
try:
    parsed = date(int(year), int(month), int(day))
except ValueError:
    return False
```

1. `"2020-03".split("-")` gives `["2020", "03"]`. Adding `["01", "01"]` gives 4 items, and `[:3]` keeps
   the first 3. So a missing month or day becomes `01`.
2. `date(2020, 13, 1)` raises a `ValueError`, because no month 13 exists. JS's `new Date(2020, 12, 1)`
   quietly moves to the next year, so this is safer.
3. Two `date` objects can be compared with `<=`, and `date.today()` gives today.

<a id="py-6"></a>
## PY-6. `re.compile` and `fullmatch`

```python
DATE_SHAPE = re.compile(r"\d{4}(-\d{2}(-\d{2})?)?")
if not DATE_SHAPE.fullmatch(value):
```

1. `re.compile` keeps a pattern in a variable, so it has a name. In JS: `const DATE_SHAPE = /.../`.
2. `fullmatch` needs the whole string to match, like `/^...$/` in JS. `"2020-03-01 or so"` fails.
3. `(...)?` means "this part is optional". So the pattern allows `2020`, `2020-03` and `2020-03-01`.
4. The `r` before the string means "raw": `\d` stays `\d`.

<a id="py-7"></a>
## PY-7. `hasattr`: a field with no `value`

```python
if hasattr(answer, "value"):
```

`Clause` has `quotes` and `found`, and `Text` and `Names` also have `value`. `hasattr` asks if the
object has that attribute. In JS: `"value" in answer`.

It is why `check_found` has no type on `answer`: any of the three models works. `not answer.value`
covers all the empty cases at once: `None`, `""` and `[]`. Careful in JS: there, `[]` counts as true.

<a id="py-8"></a>
## PY-8. `getattr` with a field name

```python
for field in ContractFields.model_fields:
    issues += check_field(field, getattr(fields, field), source_words)
```

1. `ContractFields.model_fields` is a dict, and a `for` over a dict gives its keys: the 12 field names.
2. `getattr(fields, "parties")` is `fields.parties`, with the name in a variable. In JS: `fields[field]`.
3. `issues += [...]` adds the items of one list to another. In JS: `issues.push(...list)`.

<a id="py-9"></a>
## PY-9. `@model_validator`: a Pydantic rule (Break 1)

```python
@model_validator(mode="after")
def found_needs_value(self):
    if self.found and not self.value:
        raise ValueError("found is true, but value is empty")
    return self
```

1. `@model_validator` is a decorator: it tells Pydantic to call this method when it builds the object.
2. `mode="after"` means "after the field types are checked", so `self.found` is a real bool.
3. Raising a `ValueError` makes the whole model fail with a `ValidationError`. Returning `self` means
   "all good". In zod, this is `.refine()` on an object.
4. `model_json_schema()` does not include it. The JSON schema cannot hold your Python code, so the
   provider never sees this rule. It is the same with zod's `.refine()` and `toJSONSchema`.
