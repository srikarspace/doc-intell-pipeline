# Python for Phase 1a

This file explains the new Python in Part 1a. Read one section when the main doc links to it.
Type hints are in the 0b companion ([PY-2](./phase-0b.md#py-2)), sets in 0d
([PY-6](./phase-0d.md#py-6)).

<a id="py-1"></a>
## PY-1. Classes and Pydantic `BaseModel`

A **class** is a template for objects. `class Strict(BaseModel):` makes a new class that
**inherits** from `BaseModel`. It gets all of `BaseModel`'s methods. In JS: `class Strict extends
BaseModel {}`.

```python
class Strict(BaseModel):
    """Base for every model we send to the LLM: no unknown keys, no type guessing."""

    model_config = ConfigDict(extra="forbid", strict=True)


class Clause(Strict):
    quotes: list[str]
    found: bool
```

Things to know:

- **Fields are written as `name: type`** in the class body. No constructor needed. Pydantic
  reads the type hints and builds the checks. In zod: `z.object({ quotes: z.array(z.string()),
  found: z.boolean() })`.
- **`model_config`** is a special name. Pydantic reads its settings from it. `Clause` inherits
  the config of `Strict`.
- **Make an object** by calling the class with keyword arguments: `Clause(quotes=[], found=True)`.
  A wrong type raises `ValidationError` at once.
- **From JSON**: `Clause.model_validate_json(text)` parses and checks in one step. Like
  `schema.parse(JSON.parse(text))` in zod.
- **To JSON Schema**: `Clause.model_json_schema()` returns a dict. Like `z.toJSONSchema(schema)`.
- **No `new`**: in Python you call the class like a function.

<a id="py-2"></a>
## PY-2. `list[str]`, `str | None`, and `Field`

These are type hints, and in Pydantic they are also rules.

```python
QUOTES = Field(description="Exact text copied from the contract. Empty list if not found.")

class Text(Strict):
    quotes: list[str] = QUOTES
    value: str | None
    found: bool
```

- **`list[str]`**: a list of strings. In TS: `string[]`.
- **`str | None`**: a string or `None` (Python's `null`). In TS: `string | null`. It does not mean
  "optional". The key must still be there.
- **`= something`** after a field gives it a default. Then the key becomes optional. That is why
  our field models have no defaults.
- **`Field(...)`** adds extra facts about a field. `description` goes into the JSON Schema.
  `Field(...)` with no `default=` keeps the field required. So `quotes: list[str] = QUOTES` looks
  like a default, but it is not one.

<a id="py-3"></a>
## PY-3. `type[...]`: a class as an argument

In Python, a class is a value. You can pass it to a function, like any other value.

```python
def response_format(schema: type[BaseModel]) -> dict:
    ...
    "name": schema.__name__,
    "schema": schema.model_json_schema(),
```

- **`type[BaseModel]`** means "the class `BaseModel` or a class that inherits it". Not an object
  made from it. So you call `response_format(Clause)`, not `response_format(Clause(...))`.
- **`schema.__name__`** is the class name as a string: `"Clause"`.
- In TS you would write `schema: typeof BaseModel`, or pass a zod schema object.

<a id="py-4"></a>
## PY-4. `SecretStr` and `@lru_cache`

**`SecretStr`** holds a string but hides it when printed:

```python
openrouter_api_key: SecretStr
...
repr(s.openrouter_api_key)        # SecretStr('**********')
s.openrouter_api_key.get_secret_value()   # the real key
```

So a log line or an error message never shows the key by mistake.

**`@lru_cache`** is a **decorator**: a line with `@` above a function that wraps it. `lru_cache`
remembers the return value. The first call runs the function. Every later call returns the saved
result.

```python
@lru_cache
def get_settings() -> Settings:
    return Settings()
```

In JS: lodash `_.memoize(() => new Settings())`. A JS module that exports one object does the
same job. Tests call `get_settings.cache_clear()` to start fresh.

<a id="py-5"></a>
## PY-5. `pytest.raises`

`pytest.raises(SomeError)` checks that the code inside the `with` block raises that error. If
nothing is raised, the test fails with `DID NOT RAISE`.

```python
def test_no_type_guessing():
    with pytest.raises(ValidationError):
        Answer.model_validate_json('{"quotes": [], "found": "yes"}')
```

In Jest: `expect(() => Answer.parse(...)).toThrow(ZodError)`. The `with` block is the same `with`
as in 0b ([PY-3](./phase-0b.md#py-3)): pytest checks the error when the block ends.
