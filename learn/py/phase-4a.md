# Python for Phase 4a

This file explains the new Python in Part 4a. Read one section when the main doc links to it.

<a id="py-1"></a>
## PY-1. `Literal` from a tuple

```python
FIELDS = tuple(ContractFields.model_fields)
FieldName = Literal[FIELDS]
```

1. `ContractFields.model_fields` is a dict of the 12 fields. `tuple(...)` keeps only the names, in order.
2. `Literal[("parties", "agreement_date", ...)]` means "one of these strings, and nothing else".
3. Pydantic turns it into `"enum": [...]` in the JSON schema.

In TypeScript, it is `type FieldName = "parties" | "agreement_date" | ...`. Here the list is built from the model, so
it never goes out of date. Some type checkers warn about a variable inside `Literal`. Python and Pydantic accept it.

<a id="py-2"></a>
## PY-2. `create_model`

```python
chosen = {f: (ContractFields.model_fields[f].annotation, ...) for f in fields}
return create_model("Requested", __base__=Strict, **chosen)
```

1. `create_model` builds a model class while the program runs, as if you had written `class Requested(Strict): ...`.
2. Each entry is `(type, default)`. `...` (the Ellipsis object) means "required, no default".
3. `__base__=Strict` keeps the strict rules: no extra keys, no type guessing.

In zod, it is like `ContractFields.pick({ parties: true, non_compete: true })`.

<a id="py-3"></a>
## PY-3. `model_dump(include=...)`

```python
answer.model_dump(include={"parties", "non_compete"})
```

`model_dump` turns a model into a plain dict. `include` keeps only these keys. In lodash: `_.pick(answer, [...])`.
