# Phase 1a: the answer schema

In this part, you design the shape of the model's answer for the 12 fields (the schema). You
write it as Pydantic models, turn it into the JSON that the provider needs, and add a settings
file for the key and the model name. You build it one piece at a time, with a checkpoint after
each piece. No model is called yet. 1a2 builds the client that sends this schema.

## Words used in this part

Read these first.

- **LLM**: a large language model. You send it text, it sends text back. Example: Qwen3.
- **Schema**: a description of the shape of some data: which keys, which types. Example: "`found`
  is a boolean".
- **JSON Schema**: a standard way to write a schema as JSON. Example:
  `{"type": "object", "properties": {"found": {"type": "boolean"}}}`.
- **Pydantic model**: a Python class that is also a schema. It checks data and can print its JSON
  Schema. Like a zod object in JS.
- **Structured output**: the model is asked to answer with JSON that fits a JSON Schema.
- **Provider**: the company that actually runs the model. Example: DeepInfra. OpenRouter sends
  your request to one of them.
- **Strict mode**: a flag that asks the provider to follow the schema exactly.
- **Enforcement**: the provider makes the model follow the schema while it writes.
- **Validation**: we check the answer after it arrives. Pydantic does this.
- **Lax and strict (in Pydantic)**: lax mode converts close types for you (`"yes"` becomes
  `True`). Strict mode refuses them.
- **Verbatim quote**: text copied exactly from the contract, letter by letter.
- **Environment variable (env var)**: a setting that lives outside the code. Example:
  `OPENROUTER_API_KEY=sk-or-v1-...` in `.env`.

## Objectives

By the end of this part you should be able to:

1. Defend your schema choices for each of the 4 field groups, with numbers from 0c.
2. Show the JSON Schema that Pydantic makes from your model.
3. Name the three things strict mode needs, and find them in the JSON.
4. Explain the difference between enforcement and validation, with one real example.
5. Load the key and the model name from `.env` without ever printing the key.

## Dependencies

One new library:

- `pydantic-settings`: reads settings from env vars and `.env` into a Pydantic class. Like
  `dotenv` plus a zod check of `process.env`.

Already installed: `pydantic`. You need an OpenRouter key in `.env`, written as
`OPENROUTER_API_KEY=sk-or-v1-...`. This part makes no calls, so it costs nothing.

## The big picture

Before this part, the pipeline has data, `FIELDS` and a split. It has no idea what an answer
looks like.

After this part:

- `domain/schema/fields.py` describes the answer for all 12 fields.
- `core/llm.py` has `response_format(schema)`: the schema in the shape the provider wants.
- `core/config.py` holds the key, the URL and the model name.

1a2 sends `response_format` to the model and checks the answer with the same models. 1b scores
each field. 2a checks each quote against the contract. Phase 4 returns the same JSON to the user.

## Remember this

> We ask the provider to follow our schema, but some providers only treat it as a hint. So the
> same Pydantic model that makes the schema also checks the answer, in strict mode. One class,
> two jobs: the request and the check.
>
> **One model, two jobs: ask with it, check with it.**

## Why

**Enforcement is not a promise.** OpenRouter's docs say some providers enforce the schema, and
others treat it as "a strong hint". So a missing key or a wrong type can still arrive. Only our
own check is sure.

**The schema decides what we can measure.** If a field has one quote, 1b can match only one span.
If dates are free text, 2a must parse them. Each choice here moves work to a later part.

**One source for the shape.** If the JSON Schema is written by hand, it drifts from the code that
reads the answer. Pydantic makes both from one class.

## Design decisions

- **The schema is Pydantic, in `domain/schema/`.** One class gives the JSON Schema and the check.
  Other option: write the JSON Schema by hand. Then two things can drift apart.
- **A `Strict` base class.** Every field model inherits `extra="forbid"` and `strict=True`. Other
  option: set them on each model. Easy to forget one.
- **No default values in field models.** Strict mode needs every key in `required`. A default
  removes the key from `required`. Other option: defaults plus a fix-up of the schema. More code
  to explain.
- **`strict=True` in Pydantic.** Without it, Pydantic turns `"yes"` into `True` (Round 2). Other
  option: lax mode. It hides model mistakes we want to count.
- **`CUAD_CATEGORY` maps names.** Python names cannot have spaces, CUAD names do. Other option:
  Pydantic aliases. They change the JSON keys the model sees, which is harder to read.
- **Settings with `pydantic-settings`, read once.** The key is checked at start, and a missing
  key is a clear error. Other option: `os.environ["..."]` in each file. The error comes late, in
  the middle of a run.

## Worked example

Guess before you open each box.

### Round 1: is `value: str | None` required?

A Pydantic field `value: str | None` has no default. In the JSON Schema, is `value` in
`required`?

<details><summary>Guess, then open</summary>

Yes. `str | None` only says the value may be `null`. The key must still be there. This is the
real output from this repo:

```
"value": {"anyOf": [{"type": "string"}, {"type": "null"}], "title": "Value"}
"required": ["quotes", "value", "found"]
```

Strict mode wants exactly this: every key present, `null` allowed. Add `= None` and `value`
leaves `required`. Break 1 shows the test that catches it.
</details>

### Round 2: the model writes `"found": "yes"`

The answer is `{"quotes": [], "found": "yes"}`. The schema says `found` is a boolean. Does
Pydantic reject it?

<details><summary>Guess, then open</summary>

Not by default. Pydantic's normal lax mode turns the string into a bool:

```
found=True
```

So a wrong type passes, and you never count it. With `strict=True`:

```
1 validation error for Clause
found
  Input should be a valid boolean [type=bool_type, input_value='yes', input_type=str]
```

Now it is an error you can see, count and send back to the model in 2b.
</details>

### Round 3: the model adds a key

The answer is `{"quotes": [], "found": true, "note": "hi"}`. Is that a problem?

<details><summary>Guess, then open</summary>

With `extra="forbid"`, yes:

```
1 validation error for Answer
note
  Extra inputs are not permitted [type=extra_forbidden, input_value='hi', input_type=str]
```

Without it, Pydantic quietly drops `note`. That sounds kind, but an unknown key often means the
model misread the schema. We want to see it.
</details>

## Project setup

Add the new library:

```sh
uv add pydantic-settings
```

```text
Resolved ... packages
...
 + pydantic-settings==2.16.0
```

Create the folders and empty files:

```sh
mkdir -p src/docintel/core src/docintel/domain/schema
touch src/docintel/core/__init__.py src/docintel/core/config.py src/docintel/core/llm.py
touch src/docintel/domain/__init__.py src/docintel/domain/schema/__init__.py
touch src/docintel/domain/schema/fields.py tests/test_schema.py
```

You should now have:

```
src/docintel/
├── core/
│   ├── __init__.py
│   ├── config.py          settings: key, URL, model
│   └── llm.py             response_format now; the client in 1a2
├── domain/
│   ├── __init__.py
│   └── schema/
│       ├── __init__.py
│       └── fields.py      the 12 field models (your decision)
└── evals/
    ├── datasets.py
    └── store.py
tests/
└── test_schema.py         empty
```

`core/` is code every project shares. `domain/` is code only this project has. The layout is in
`PLAN.md`.

## Step 1: the schema (your decision)

**Why.** The schema is the contract between the model and the rest of the pipeline. Every later
part reads it.

### 1a: the base class

Put this in `src/docintel/domain/schema/fields.py`. This part is not a decision. It is what
strict mode needs:

```python
"""The 12 fields as Pydantic models. The JSON schema we send to the model is built from these."""

from pydantic import BaseModel, ConfigDict, Field


class Strict(BaseModel):
    """Base for every model we send to the LLM: no unknown keys, no type guessing."""

    model_config = ConfigDict(extra="forbid", strict=True)
```

*Python here: [classes and `BaseModel`](./py/phase-1a.md#py-1).*

Here, we:

1. Make a base class. Every field model will inherit from it, like `class Clause extends Strict`
   in JS.
2. Set `extra="forbid"`: an unknown key is an error (Round 3). In the JSON Schema it becomes
   `"additionalProperties": false`.
3. Set `strict=True`: no type guessing (Round 2).

### 1b: your field models

Each field has some of `quotes`, `value` and `found`. Look at this evidence from your 0c
notebook:

| Group | Field | Spans when present | Median span (chars) |
|---|---|---|---|
| Basic facts | Parties | 5.0 | 17 |
| | Agreement Date | 1.0 | 16 |
| | Governing Law | 1.1 | 178 |
| Yes/no + quote | Non-Compete, Change Of Control, Anti-Assignment | 1.7 to 2.2 | 218 to 309 |
| Numbers/terms | Renewal Term, Notice Period, Cap On Liability | 1.1 to 2.4 | 270 to 306 |
| License/IP | License Grant, Ip Ownership, Non-Transferable | 2.2 to 3.0 | 337 to 356 |

Decide each question. Write your answers in a markdown cell called "Schema" in your notebook:

1. **One quote or a list?** `quote: str | None` or `quotes: list[str]`. Many fields have 2 or 3
   spans. With one quote, the model must pick one, and 1b has fewer chances to match a span.
2. **Key order.** The model writes keys in schema order. If `found` comes first, it decides before
   it looks. If `quotes` comes first, it copies the evidence, then decides. Which order?
3. **Parties.** `value: list[str]` plus `quotes`, or `list[Party]` where each `Party` has `name`
   and `quote`? CUAD's Parties spans are the names themselves (median 17 characters).
4. **Dates.** `value: str | None` with "YYYY-MM-DD" in the prompt, or `value: date | None`? With
   `date`, one bad date makes the whole answer fail Pydantic, so all 12 fields are lost.
5. **Yes/no fields.** Do they need a `value: bool`, or is `found` already the answer?
6. **Terms and amounts.** Free text (`"1 year"`) for now, or a number plus a unit? Typed values
   can come later, in 2a validators.

Then write your models below `Strict`. Every field model inherits `Strict`. Give no field a
default value. Then write the top model `ContractFields`, with 12 attributes, one per field.

A class docstring and a `Field(description=...)` go into the JSON Schema. The model reads them.
So write them for the model: short and clear.

*Python here: [`list[str]`, `str | None`, and `Field`](./py/phase-1a.md#py-2).*

### 1c: the name map

Add to the bottom of `src/docintel/domain/schema/fields.py`:

```python
CUAD_CATEGORY = {  # attribute name -> CUAD category, so 1b can join on labels.category
    "parties": "Parties",
    # ... one line per field, 12 in total, exact CUAD spelling from FIELDS
}
```

Here, we keep the link between your Python names and the CUAD names in one place. 1b uses it to
find the right `labels` rows for each answer.

Checkpoint. Guess the numbers first:

```sh
uv run python -c "
from docintel.domain.schema.fields import ContractFields
s = ContractFields.model_json_schema()
print(len(s['properties']), sorted(s['\$defs']))
print(s['\$defs']['Clause']['required'])
print(s['properties']['non_compete'])"
```

```text
12 ['Clause', 'Names', 'Text']
['quotes', 'found']
{'$ref': '#/$defs/Clause'}
```

This is the output of the reference below. Your class names can differ. The first number must be
12.

1. Each nested model goes into `$defs` once.
2. A field points to it with `$ref`, like an import.
3. 12 fields use only 3 shapes, so the schema stays small (about 2,600 characters).

<details><summary>Reference schema (open after you decide)</summary>

Answers: a list of quotes, quotes first, Parties as two lists, dates as text, `found` is the yes/no
answer, terms as free text. These go between `Strict` and `CUAD_CATEGORY`:

```python
QUOTES = Field(description="Exact text copied from the contract. Empty list if not found.")


class Clause(Strict):
    """A yes/no field: the clause is there or not. `found` is the answer."""

    quotes: list[str] = QUOTES
    found: bool


class Text(Strict):
    """A field with one short answer, like a date, a state or a term."""

    quotes: list[str] = QUOTES
    value: str | None
    found: bool


class Names(Strict):
    """A field with a list of answers, like the parties."""

    quotes: list[str] = QUOTES
    value: list[str]
    found: bool


class ContractFields(Strict):
    """All 12 fields for one contract."""

    parties: Names
    agreement_date: Text
    governing_law: Text
    non_compete: Clause
    change_of_control: Clause
    anti_assignment: Clause
    renewal_term: Text
    notice_period_to_terminate_renewal: Text
    cap_on_liability: Text
    license_grant: Clause
    ip_ownership_assignment: Clause
    non_transferable_license: Clause
```

Why:

- `QUOTES` has a description but no default, so `quotes` stays required.
- License/IP fields are `Clause`. Their CUAD labels are long spans with no short value.
- Parties as `list[Party]` is nicer to read, but it adds a fourth shape. The quotes are already
  the names. 1b can match `value` and `quotes` on their own.
- No descriptions on the 12 attributes. Pydantic puts them next to `$ref`, and some providers
  reject that. Format hints like "YYYY-MM-DD" go in the prompt in 1b.
</details>

## Step 2: settings

**Why.** The key, the URL and the model name must live in one place, outside the code. 1a2 reads
them to make the client.

Put this in `src/docintel/core/config.py`:

```python
"""Settings from env vars and `.env`. One place for keys, URLs and defaults."""

from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openrouter_api_key: SecretStr
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    docintel_model: str = "qwen/qwen3-235b-a22b-2507"
    llm_timeout_s: float = 120.0
    llm_max_attempts: int = 4  # 1 try + 3 retries, only for network errors and 429


@lru_cache
def get_settings() -> Settings:
    """Read the settings once, then reuse them."""
    return Settings()
```

*Python here: [`SecretStr` and `@lru_cache`](./py/phase-1a.md#py-4).*

Here, we:

1. Name each setting once. Pydantic reads the env var with the same name, in any case. So
   `openrouter_api_key` reads `OPENROUTER_API_KEY`.
2. Read `.env` too. A real env var wins over `.env`. `extra="ignore"` skips other lines in it.
3. Keep the key in a `SecretStr`, so a `print` shows stars, not the key.
4. Give every setting except the key a default. No key means a clear error at start.
5. `get_settings()` builds the object once. Every later call returns the same one.

The model is `qwen/qwen3-235b-a22b-2507`: open weights, no "thinking" tokens, and cheap ($0.09
per million input tokens). A dev run of about 0.66M tokens costs about 6 cents of input. The last
two settings are for 1a2.

Add one line to `.env.example`, so the next person knows the model can change:

```sh
DOCINTEL_MODEL=qwen/qwen3-235b-a22b-2507
```

Checkpoint. Guess what the second line prints:

```sh
uv run python -c "
from docintel.core.config import get_settings
s = get_settings()
print(s.docintel_model, s.llm_max_attempts)
print(repr(s.openrouter_api_key))"
```

```text
qwen/qwen3-235b-a22b-2507 4
SecretStr('**********')
```

Now run the same command from another folder, where there is no `.env`. You get:

```
pydantic_core._pydantic_core.ValidationError: 1 validation error for Settings
openrouter_api_key
  Field required [type=missing, input_value={}, input_type=dict]
```

`.env` is read from the folder you run in. Always run from the project root.

## Step 3: from Pydantic model to `response_format`

**Why.** The provider needs the schema as JSON, inside a `response_format` object.

`Model.model_json_schema()` gives the JSON Schema. In JS with zod 4, this is
`z.toJSONSchema(schema)`. Same idea: you write the schema once, in code, and print it as JSON.

Put this in `src/docintel/core/llm.py`:

```python
"""Thin OpenRouter client: messages + Pydantic model in, LLMResult out. Every call is logged."""

from pydantic import BaseModel


def response_format(schema: type[BaseModel]) -> dict:
    """The `response_format` that asks the provider to follow this Pydantic model."""
    return {
        "type": "json_schema",
        "json_schema": {
            "name": schema.__name__,
            "strict": True,
            "schema": schema.model_json_schema(),
        },
    }
```

*Python here: [`type[...]`: a class as an argument](./py/phase-1a.md#py-3).*

Here, we:

1. Take the class itself, not an object made from it. `schema.__name__` is its name, like
   `"Clause"`.
2. Wrap the JSON Schema in the shape OpenRouter wants: `type`, then `json_schema` with `name`,
   `strict` and `schema`.

The docstring at the top already describes the whole file. 1a2 adds the rest.

Checkpoint:

```sh
uv run python -c "
import json
from docintel.core.llm import response_format
from docintel.domain.schema.fields import Clause
print(json.dumps(response_format(Clause), indent=2))"
```

```text
{
  "type": "json_schema",
  "json_schema": {
    "name": "Clause",
    "strict": true,
    "schema": {
      "additionalProperties": false,
      "description": "A yes/no field: the clause is there or not. `found` is the answer.",
      "properties": {
        "quotes": {
          "description": "Exact text copied from the contract. Empty list if not found.",
          "items": {"type": "string"},
          "title": "Quotes",
          "type": "array"
        },
        "found": {"title": "Found", "type": "boolean"}
      },
      "required": ["quotes", "found"],
      "title": "Clause",
      "type": "object"
    }
  }
}
```

(Short lists are put on one line here to save space.) Find the three things strict mode needs:

1. `"strict": true`.
2. `"additionalProperties": false`.
3. Every property in `required`.

The docstring became `description`. The model reads it.

## Step 4: a test for the rules that must never break

**Why.** Four things must always be true:

1. Every object in the schema forbids extra keys and requires every key.
2. The schema covers exactly the 12 fields in `FIELDS`.
3. Pydantic does not guess types.
4. Pydantic does not accept unknown keys.

If one breaks, a provider may reject the schema, or a model mistake passes as a correct answer.

Put this in `tests/test_schema.py`:

```python
"""Schema rules that strict mode needs. No network, no key."""

import pytest
from pydantic import ValidationError

from docintel.domain.schema.fields import CUAD_CATEGORY, ContractFields, Strict
from docintel.evals.datasets import FIELDS


class Answer(Strict):  # a tiny model, so two tests do not depend on your field choices
    quotes: list[str]
    found: bool


def test_schema_is_strict():
    """Strict mode needs: no extra keys, and every key required, on every object."""
    schema = ContractFields.model_json_schema()
    for obj in [schema, *schema.get("$defs", {}).values()]:
        assert obj["additionalProperties"] is False
        assert set(obj["required"]) == set(obj["properties"])


def test_schema_covers_the_12_fields():
    assert set(CUAD_CATEGORY) == set(ContractFields.model_fields)
    assert sorted(CUAD_CATEGORY.values()) == sorted(f for group in FIELDS.values() for f in group)


def test_no_type_guessing():
    with pytest.raises(ValidationError):
        Answer.model_validate_json('{"quotes": [], "found": "yes"}')


def test_no_unknown_keys():
    with pytest.raises(ValidationError):
        Answer.model_validate_json('{"quotes": [], "found": true, "note": "hi"}')
```

*Python here: [`pytest.raises`](./py/phase-1a.md#py-5) · sets:
[0d PY-6](./py/phase-0d.md#py-6).*

Here, we:

1. Make `Answer`, a tiny model that inherits `Strict`. Two tests use it, so they keep working
   whatever fields you chose.
2. Walk the top schema and every model in `$defs`. Each must forbid extra keys. Its `required`
   set must equal its `properties` set.
3. Check that `CUAD_CATEGORY` names the same 12 attributes as `ContractFields`, and the same 12
   categories as `FIELDS` from 0d.
4. Send `"found": "yes"` and an extra key. Both must raise `ValidationError` (Rounds 2 and 3).

Checkpoint:

```sh
make lint && make test
```

```text
All checks passed!
...
tests/test_data_load.py ....                                             [ 28%]
tests/test_schema.py ....                                                [ 57%]
tests/test_smoke.py .                                                    [ 64%]
tests/test_splits.py .....                                               [100%]

============================== 14 passed in 0.68s ==============================
```

Your project should now look like this:

```
src/docintel/
├── core/
│   ├── __init__.py
│   ├── config.py          Settings, get_settings
│   └── llm.py             response_format
├── domain/
│   ├── __init__.py
│   └── schema/
│       ├── __init__.py
│       └── fields.py      Strict, your field models, ContractFields, CUAD_CATEGORY
└── evals/
    ├── datasets.py
    └── store.py
tests/
├── test_data_load.py
├── test_schema.py         4 tests
├── test_smoke.py
└── test_splits.py
```

<details><summary>Full <code>src/docintel/domain/schema/fields.py</code> (reference)</summary>

```python
"""The 12 fields as Pydantic models. The JSON schema we send to the model is built from these."""

from pydantic import BaseModel, ConfigDict, Field


class Strict(BaseModel):
    """Base for every model we send to the LLM: no unknown keys, no type guessing."""

    model_config = ConfigDict(extra="forbid", strict=True)


QUOTES = Field(description="Exact text copied from the contract. Empty list if not found.")


class Clause(Strict):
    """A yes/no field: the clause is there or not. `found` is the answer."""

    quotes: list[str] = QUOTES
    found: bool


class Text(Strict):
    """A field with one short answer, like a date, a state or a term."""

    quotes: list[str] = QUOTES
    value: str | None
    found: bool


class Names(Strict):
    """A field with a list of answers, like the parties."""

    quotes: list[str] = QUOTES
    value: list[str]
    found: bool


class ContractFields(Strict):
    """All 12 fields for one contract."""

    parties: Names
    agreement_date: Text
    governing_law: Text
    non_compete: Clause
    change_of_control: Clause
    anti_assignment: Clause
    renewal_term: Text
    notice_period_to_terminate_renewal: Text
    cap_on_liability: Text
    license_grant: Clause
    ip_ownership_assignment: Clause
    non_transferable_license: Clause


CUAD_CATEGORY = {  # attribute name -> CUAD category, so 1b can join on labels.category
    "parties": "Parties",
    "agreement_date": "Agreement Date",
    "governing_law": "Governing Law",
    "non_compete": "Non-Compete",
    "change_of_control": "Change Of Control",
    "anti_assignment": "Anti-Assignment",
    "renewal_term": "Renewal Term",
    "notice_period_to_terminate_renewal": "Notice Period To Terminate Renewal",
    "cap_on_liability": "Cap On Liability",
    "license_grant": "License Grant",
    "ip_ownership_assignment": "Ip Ownership Assignment",
    "non_transferable_license": "Non-Transferable License",
}
```
</details>

## Break it on purpose

**Break 1: a default value.** In one of your field models, change `found: bool` to
`found: bool = False`. Guess which test fails, then run `make test`:

```
E           AssertionError: assert {'quotes'} == {'found', 'quotes'}
E             Extra items in the right set:
E             'found'
FAILED tests/test_schema.py::test_schema_is_strict - AssertionError: assert {...
========================= 1 failed, 13 passed in 0.52s =========================
```

The default took `found` out of `required`. Some strict providers reject this schema. Others let
the model skip `found`. Change it back.

**Break 2: lax Pydantic.** In `Strict`, remove `strict=True`. Guess the result:

```
E       Failed: DID NOT RAISE ValidationError
FAILED tests/test_schema.py::test_no_type_guessing - Failed: DID NOT RAISE Va...
========================= 1 failed, 13 passed in 0.51s =========================
```

`"yes"` became `True` with no error. In 1c, this mistake would be scored as a correct answer and
never counted. Change it back.

## Experiment

This part runs no model, so there is no `run_id` and no `EXPERIMENTS.md` entry. Your "Schema"
cell in the notebook is the record of your choices. 1c will cite it.

## Gotchas

- **`Field required ... openrouter_api_key`.** You ran from a folder with no `.env`, or the key
  line is empty. Run from the project root.
- **A default sneaks in.** `x: str | None = None` looks harmless. It removes `x` from `required`.
  The test catches it.
- **Old code in the notebook.** After you change `fields.py`, restart the kernel before you
  import it again.
- **Keep the schema simple.** Some strict providers allow fewer JSON Schema features. Use objects,
  strings, booleans, lists and `null`. No `format`, no `minLength`.
- **Never print the key.** `print(s)` shows stars. `get_secret_value()` shows the real key. 1a2
  uses it in one place only.

## Explain back, then commit

Explain each changed file to Claude in a few sentences (the rule in `PLAN.md`): `fields.py` (each
schema choice and its evidence), `config.py`, `llm.py` (what `response_format` sends),
`test_schema.py` (each test), and the notebook "Schema" cell. Then:

```sh
git status
git add pyproject.toml uv.lock .env.example src/docintel/core src/docintel/domain tests/test_schema.py notebooks/00_explore.ipynb
git commit -m "phase 1a: field schema, settings, response_format"
```

Check the `git status` output first: `.env` must not be in the list.

## Conclusion

What you have now:

- A schema for the 12 fields, with your reasons, that strict mode accepts.
- `response_format`, which turns any Pydantic model into the JSON the provider needs.
- Settings that read the key once and never print it.
- A test that guards the strict rules.

Go back to the objectives. Check that you can do each one without notes. Then answer:

1. The provider has strict mode. Why do we still validate with Pydantic? Give the real example
   from this part.
2. Why does `str | None` with no default keep the key in `required`, and why does strict mode
   care?

Want more practice? Try these (optional):

1. Print `ContractFields.model_json_schema()` and count the characters with `len(json.dumps(...))`.
   How many tokens is that, at about 4 characters per token?
2. Try `value: date | None` in a scratch model. What does `model_json_schema()` add to it?
3. Write the same `Clause` schema in zod, and compare `z.toJSONSchema` with the Pydantic output.

Checklist (`../PLAN.md`): **Structured outputs: Pydantic to JSON schema; enforcement and
validation** (Pydantic to JSON Schema done; enforcement and validation explained here, used in
1a2).
