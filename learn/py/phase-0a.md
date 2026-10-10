# Python for Phase 0a

Covers the Python and tooling this part introduces; read sideways, one section at a time.

<a id="py-1"></a>
## PY-1. TOML, the config format

`pyproject.toml` is written in **TOML**, a config format built to be easy for humans to read. It is
what JSON would look like if it allowed comments and did not need quotes around keys. Python's
whole ecosystem settled on it for project config.

```toml
[tool.ruff.lint]
# E/F = pycodestyle + pyflakes basics, I = import sorting, UP = modern syntax, B = common bugs
select = ["E", "F", "I", "UP", "B"]
```

The same thing as JSON:

```json
{ "tool": { "ruff": { "lint": { "select": ["E", "F", "I", "UP", "B"] } } } }
```

- `[a.b.c]` is a **table** header: everything below it, until the next header, lives at that
  nested path.
- `[[package]]` (double brackets, in `uv.lock`) means "one more item in the array called
  `package`". Each block is one element.
- `#` starts a comment. JSON's lack of comments is the main reason `package.json` cannot explain
  itself and this file can.

<a id="py-2"></a>
## PY-2. Modules, packages and `__init__.py`

A **module** is one `.py` file. A **package** is a folder of modules with an `__init__.py` in it.
`import docintel` runs `src/docintel/__init__.py` once and gives you back its contents as an
object.

```python
"""docintel: CUAD contract PDFs -> cited, validated JSON."""
```

The JS mapping:

| Python | JS |
|---|---|
| `import docintel` | `const docintel = require('docintel')` |
| `src/docintel/__init__.py` | `docintel/index.js` |
| `import docintel.evals` | `require('docintel/evals')` |
| `from docintel.evals.datasets import load_cuad` | `const { load_cuad } = require('docintel/evals/datasets')` |

- Python caches a module after its first import, like Node's `require` cache. A second
  `import docintel` does not re-run the file.
- An empty or docstring-only `__init__.py` is normal. 0b's `evals/__init__.py` is one docstring
  too; you import straight from the module file: `from docintel.evals.datasets import load_cuad`.
  An `__init__.py` can also re-export names, like a barrel `index.js`, but we do not need that yet.

<a id="py-3"></a>
## PY-3. Docstrings

A string literal as the very first statement of a file, function or class is its **docstring**.
Python keeps it at runtime in `__doc__`, so tools and `help()` can show it.

```python
"""Smoke test: proves the package and core deps import inside the uv env."""
```

```sh
uv run python -c "import docintel; print(docintel.__doc__)"
# docintel: CUAD contract PDFs -> cited, validated JSON.
```

- Triple quotes (`"""..."""`) allow multiple lines, like a JS template literal without the
  `${}` part.
- It is JSDoc's job, but it is a real value, not a comment. Editors show it on hover. ruff does not
  require them here; the repo uses them on modules and on functions whose name does not say
  enough.

<a id="py-4"></a>
## PY-4. pytest discovery and bare `assert`

pytest finds tests by name, with no registration step:

- files named `test_*.py` under `testpaths` (here `tests/`),
- functions in them named `test_*`.

```python
def test_imports():
    import dotenv  # noqa: F401
    ...
```

A test passes if the function returns without raising. It fails on any exception, including a
failed `assert`.

```python
assert len(parties) == 3
```

`assert` is a Python keyword: "raise an error if this is false". pytest rewrites it behind the
scenes so a failure prints both sides of the comparison:

```
E       AssertionError: assert 2 == 3
E        +  where 2 = len(['Acme Inc.', 'Beta LLC'])
```

- Jest equivalent: `test('parties count', () => expect(parties.length).toBe(3))`. pytest needs no
  `expect` library; plain `assert` is the whole API.
- Useful flags: `uv run pytest -k parties` runs only tests whose name contains "parties" (like
  `jest -t`), `-x` stops at the first failure, `-v` lists every test.

<a id="py-5"></a>
## PY-5. `# noqa` comments

`# noqa: F401` at the end of a line tells ruff to skip rule F401 ("imported but unused") on that
line only.

```python
    import duckdb  # noqa: F401
```

The smoke test imports libraries only to prove they import. It never uses them, so ruff would
rightly complain. `noqa` ("no quality assurance") says "this is on purpose".

- JS equivalent: `// eslint-disable-next-line no-unused-vars`, except it goes at the end of the
  line it applies to.
- Always name the rule (`F401`). A bare `# noqa` silences every rule on the line and hides real
  bugs.

<a id="py-6"></a>
## PY-6. `python -m`

`python -m docintel.evals.datasets` means "find the module `docintel.evals.datasets` through the
installed package and run it as the main program". It is how `make data` works from 0b on.

```makefile
data:
	uv run python -m docintel.evals.datasets
```

- Node equivalent: `node src/evals/datasets.js`, or a `"bin"` entry run with `npx`.
- Why `-m` and not `python src/docintel/evals/datasets.py`: with `-m`, Python resolves the name
  through the installed package, so imports like `from docintel.evals.store import connect`
  work. Running the file path directly can break them.
- The module notices it is the main program through `if __name__ == "__main__":` (0b explains it).
- You already used it: `uv run python -m pytest` is the same as `uv run pytest`.

<a id="py-7"></a>
## PY-7. Which Python is running? `sys.executable`

When something behaves differently in the terminal, in VS Code and in Jupyter, the first question is
"which Python is this?". Python can tell you:

```sh
uv run python -c "import sys; print(sys.executable)"
# /Users/youruser/.../doc-intell-pipeline/.venv/bin/python
```

In a notebook cell:

```python
import sys
sys.executable
```

- If it does not end in `.venv/bin/python`, you are on the wrong interpreter, and imports will
  fail or find different versions.
- JS has no real equivalent because `node_modules` is found by walking up folders from the script.
  Python finds libraries through the interpreter, so the interpreter is what matters.
