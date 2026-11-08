# Python for Phase 3a3

This file explains the new Python in Part 3a3. Read one section when the main doc links to it. A function inside a
function and the fake client are in 1a2 ([PY-7](./phase-1a2.md#py-7)).

<a id="py-1"></a>
## PY-1. `**limit`: send keys only when they exist

```python
limit = {"max_tokens": max_tokens} if max_tokens else {}
resp = client.chat.completions.create(model=model, temperature=0, **limit)
```

1. `limit` is `{"max_tokens": 12000}`, or an empty dict.
2. `**limit` turns each key into a named argument.
3. An empty dict adds nothing, so the request is the same as before.

In JS, it is `create({ model, temperature: 0, ...limit })`.

<a id="py-2"></a>
## PY-2. Your own error types

```python
class BudgetExceeded(RuntimeError):
    pass
```

1. `pass` means the class has no extra code. The name is the point.
2. `except BudgetExceeded as e:` catches only this error. Other errors keep going up.

In JS: `class BudgetExceeded extends Error {}`.

<a id="py-3"></a>
## PY-3. An image in memory, then base64

```python
buffer = io.BytesIO()
page.render(scale=dpi / 72).to_pil().convert("L").save(buffer, format="PNG")
encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
```

1. `io.BytesIO()` acts like a file, but it lives in memory. `save` writes into it.
2. `dpi / 72`: a PDF measures size in points, 72 per inch. So 150 DPI is a scale of about 2.08.
3. `.convert("L")` makes the image grey.
4. `b64encode` gives bytes, and `.decode("ascii")` turns them into a string.

In Node: `buffer.toString('base64')`.

<a id="py-4"></a>
## PY-4. `monkeypatch.undo()`

```python
def test_too_many_pages_is_refused(tmp_path, monkeypatch):
    monkeypatch.undo()
```

The `setup` fixture replaces `page_images` with a fake for every test. This one test needs the real function.
`monkeypatch.undo()` removes every change made so far with this `monkeypatch`, so the real `page_images` is back.

The test does not call the model, so it needs no key.
