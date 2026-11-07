# Python for Phase 2b

This file explains the new Python (and SQL) in Part 2b. Read one section when the main doc links to it.
`@dataclass` is in the 1a2 companion ([PY-1](./phase-1a2.md#py-1)), dict merge `|` is in 0b
([PY-6](./phase-0b.md#py-6)), and `monkeypatch.setattr` is in 1c2 ([PY-5](./phase-1c2.md#py-5)).

<a id="py-1"></a>
## PY-1. `@property`: a method you read like a field

```python
@dataclass
class Attempt:
    issues: list[Issue]

    @property
    def errors(self) -> list[Issue]:
        return [i for i in self.issues if i.severity == "error"]
```

1. `attempt.errors` runs the method, with no `()`.
2. It is computed from `issues` each time. So it can never disagree with `issues`.
3. It is not stored, so it is not one of the dataclass fields.

In JS, it is a getter: `get errors() { return this.issues.filter(...) }`.

<a id="py-2"></a>
## PY-2. `messages + [...]`: a new list, not `append`

```python
messages = messages + [
    {"role": "assistant", "content": result.raw_text},
    {"role": "user", "content": feedback(attempt.errors)},
]
```

`a + b` makes a new list with the items of both. The old list does not change.

`messages.append(...)` would change the list in place. Here that is risky: `call_llm` got the same list
object, and a fake in a test keeps it. With `append`, the test would see the messages change after the
call. In JS, this is `[...messages, a, b]` against `messages.push(a, b)`.

<a id="py-3"></a>
## PY-3. `attempts[-2]`: counting from the end

```python
error_keys(attempt) == error_keys(attempts[-2])
```

A negative index counts from the end. `[-1]` is the last item, and `[-2]` is the one before it. Here,
`attempt` was just added, so `attempts[-2]` is the attempt before it.

In JS: `attempts.at(-2)`. Plain `attempts[-2]` in JS gives `undefined`.

<a id="py-4"></a>
## PY-4. `model_copy(update=...)`: a Pydantic copy with some fields changed

```python
answer = answer.model_copy(update={"anti_assignment": new_field})
```

1. It returns a new model. `answer` itself does not change.
2. `update` sets the given fields in the copy. Every other field stays.
3. It does not run validation again. That is fine here: each new field came from a model that was
   already valid.

In JS: `{ ...answer, anti_assignment: newField }`.

<a id="py-5"></a>
## PY-5. `iter` and `next`: one reply at a time

```python
replies = iter([first, second])
next(replies)  # first
next(replies)  # second
next(replies)  # error: StopIteration
```

`iter` turns a list into an iterator: it remembers where it is. Each `next` gives the next item. The
fake model uses it to answer differently on each call.

In JS: `const it = [first, second][Symbol.iterator](); it.next().value`.

<a id="py-6"></a>
## PY-6. `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`

```sql
ALTER TABLE runs ADD COLUMN IF NOT EXISTS max_retries INTEGER DEFAULT 0;
```

1. `CREATE TABLE IF NOT EXISTS` does nothing when the table is already there. It never adds columns.
2. `ALTER TABLE ... ADD COLUMN` adds a column to a table that exists.
3. `IF NOT EXISTS` makes it safe to run every time, like the `CREATE` lines.
4. `DEFAULT 0` fills the new column with 0 for every old row.

This is a tiny database migration. Phase 4 does them properly for Postgres.

<a id="py-7"></a>
## PY-7. `dataclasses.replace`: a dataclass copy with some fields changed

```python
final = replace(attempts[-1].result, parsed=final_answer(attempts))
```

It is the dataclass version of `model_copy(update=...)` (PY-4). It returns a new `LLMResult` with a
different `parsed`. Everything else is copied. The old one does not change.

<a id="py-8"></a>
## PY-8. `choices` in `argparse`

```python
run.add_argument("--retries", type=int, choices=[0, 1, 2], default=0)
```

`type=int` turns the text `"2"` into the number `2`. Then `choices` checks it. `--retries 5` stops with
a clear error before any call is made:

```text
python -m docintel.evals.runner run: error: argument --retries: invalid choice: '5' (choose from 0, 1, 2)
```

<a id="py-9"></a>
## PY-9. `[x] * 3` and `*` in a call

```python
fake_llm(monkeypatch, *[answer(anti_assignment=MADE_UP)] * 3)
```

Read it in two moves:

1. `[x] * 3` makes a list with `x` three times: `[x, x, x]`. In JS: `Array(3).fill(x)`.
2. `*` in a call unpacks the list into separate arguments. So `fake_llm` gets three replies, like
   `fakeLlm(monkeypatch, ...Array(3).fill(x))` in JS.

The `*replies` in the function's definition collects them again (1a2 [PY-7](./phase-1a2.md#py-7)).
