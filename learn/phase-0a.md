# Phase 0a: project setup

About an hour. Eight files, all already built. You type a little and run a lot.

This part is different from the rest. The setup was built before the tutor model started, so
instead of typing it you read each file, predict what a command will do, then run it. From 0b on
you type everything.

---

## The big picture

Before this part the repo was three markdown files. After it, the repo is a Python **package**
called `docintel` with its own private Python, its own installed libraries, a test runner, a
linter, and a Makefile of shortcuts.

```sh
make test     # run every test
make lint     # check style and common bugs
make nb       # open Jupyter in the browser
```

Every later part depends on this. 0b puts the CUAD loader in `src/docintel/evals/`. Phase 1 adds
`llm/`, `schema/`, `extract/`, `score/`. All of them are imported as `docintel.something`, run with
`uv run`, tested with `make test`, and checked with `make lint`. None of that works without the
eight files below.

Gaps on purpose: there is no code yet that does anything with contracts. That starts in 0b.

## Files

| File | Job |
|---|---|
| `pyproject.toml` | the `package.json`: name, Python version, dependencies, tool settings |
| `uv.lock` | the `package-lock.json`: exact version of all 118 packages |
| `.python-version` | the `.nvmrc`: which Python this repo uses (3.12) |
| `.env.example` | a template for `.env`, which holds your OpenRouter key |
| `Makefile` | the `"scripts"` block: `make test`, `make lint`, `make nb`, ... |
| `src/docintel/__init__.py` | turns the folder into an importable package (like `index.js`) |
| `tests/test_smoke.py` | one test proving the package and libraries import |
| `.gitignore` | keeps `.venv/`, `.env` and `data/` out of git |

Python help for this part: [`learn/py/phase-0a.md`](./py/phase-0a.md).

---

## Remember this

> Your Mac has its own Python, but this project never uses it. uv gives the project a private
> Python and a private folder of libraries, `.venv/`, the way npm gives a project
> `node_modules/`. Anything you run through `uv run` uses that private copy. Anything you run
> without it uses the Mac's copy, which does not have duckdb or pydantic installed.
>
> **Always `uv run`. The project lives in `.venv`.**

---

## Why

**Python has no `node_modules` by default.** In Node, `npm install` puts libraries next to your
code and `require` finds them. Python's default is one shared pile of libraries for the whole
machine. Two projects needing different pydantic versions would fight. A **virtual environment**
(venv) is the fix: a folder holding its own Python and its own libraries. `.venv/` is this
project's.

**uv is npm, nvm and npx in one tool.** It installs Python itself (like nvm), creates and fills the
venv (like `npm install`), writes the lockfile (like `package-lock.json`), and runs commands inside
the venv (like `npx`). Before uv, Python needed four separate tools for this. uv is also fast:
`uv sync` on this repo takes about 10 milliseconds when nothing changed.

**Tests and lint from day one.** Every later part ends with "Test: `make test` is green". Phase 1c
(scoring) and 2a (validators) are mostly tests. Setting up pytest now means the habit is free
later. ruff catches unused imports and old syntax before they pile up.

**A Makefile so you remember one word.** `uv run ruff check . && uv run ruff format --check .` is a
lot to type. `make lint` is not. Same idea as `npm run lint`.

---

## Design decisions

- **uv, not pip + venv.** pip is Python's original installer; it has no lockfile and does not
  manage Python versions. Poetry is the older all-in-one alternative; uv does the same job, faster,
  and is what new projects pick in 2026.
- **The `src/` layout** (`src/docintel/` rather than `docintel/` at the root). Your code is only
  importable after it is installed into the venv, never by accident because you happened to run
  Python from the repo folder. That catches packaging bugs early. The alternative (flat layout) is
  simpler but lets tests pass locally that fail in Docker later.
- **Python pinned to 3.12** (`>=3.12,<3.13`). Docling and some ML libraries lag behind new Python
  releases. Pinning means "works on my machine" is the same machine everywhere, including the
  Docker image in Phase 5.
- **Dev dependencies in a separate group.** pytest, ruff and jupyter are only needed while
  developing, like `devDependencies`. The Docker image in Phase 5 will skip them.
- **ruff for both linting and formatting.** It replaces three older tools (flake8, isort, black),
  like one tool doing eslint and prettier. The rule sets picked are the safe core: real errors,
  import order, modern syntax, likely bugs. No style nitpicks.
- **make, not just.** `just` is a nicer Makefile replacement, but `make` is already on every Mac and
  Linux machine. One less thing to install.

---

## Worked example

Predict before opening each one.

### Round 1: two Pythons

Run these two commands from the repo root. What does each print?

```sh
python3 -c "import duckdb; print('ok')"
uv run python -c "import duckdb; print('ok')"
```

<details><summary>Predict, then open</summary>

```
Traceback (most recent call last):
  File "<string>", line 1, in <module>
ModuleNotFoundError: No module named 'duckdb'
ok
```

The first one uses the Mac's Python (from Homebrew, version 3.13). Nobody installed duckdb there,
so it fails. The second one uses `.venv/bin/python` (3.12), where uv installed it.

See it directly:

```sh
python3 --version              # Python 3.13.1
uv run python --version        # Python 3.12.15
uv run which python            # /Users/youruser/.../doc-intell-pipeline/.venv/bin/python
```

This is the number one beginner error in Python. If you ever see `ModuleNotFoundError` for a
library you know you installed, you forgot `uv run`.
</details>

### Round 2: where does `import docintel` come from?

`src/docintel/__init__.py` is one line. `tests/test_smoke.py` does `import docintel`. The tests run
from the repo root, not from `src/`. How does Python find it?

<details><summary>Predict, then open</summary>

`uv sync` installed your own project into the venv, in **editable** mode. Look:

```sh
ls .venv/lib/python3.12/site-packages | grep docintel
cat .venv/lib/python3.12/site-packages/docintel.pth
```

```
docintel-0.1.0.dist-info
docintel.pth
/Users/youruser/.../doc-intell-pipeline/src
```

`site-packages` is the venv's `node_modules`. The `.pth` file is one line: a path. Python adds
every path listed in a `.pth` file to its search list. So `import docintel` finds
`src/docintel/`. It is like `npm link`: the package points at your live source, so edits show up
without reinstalling.
</details>

### Round 3: adding a library

You run `uv add humanize` (a small library that prints "3 minutes ago"). Which files change?

<details><summary>Predict, then open</summary>

Three things change:

1. `pyproject.toml` gets `"humanize>=4.x"` in `dependencies`, like `npm i` editing `package.json`.
2. `uv.lock` gets a new `[[package]]` block with the exact version and a hash.
3. `.venv/` gets the files.

Undo it with `uv remove humanize`. Never edit `uv.lock` by hand, same as `package-lock.json`.
`uv add --dev <pkg>` puts it in the `dev` group instead (like `npm i -D`).
</details>

---

## Your task

Seven steps. Each one is a file to read and a command to run. Run everything from the repo root.

### 1. pyproject.toml

**Why.** One file describes the whole project: what it is called, which Python, which libraries,
and how each tool is configured. Every later part that adds a library changes this file.

```toml
[project]
name = "docintel"
version = "0.1.0"
description = "Document intelligence pipeline: CUAD contract PDFs -> cited, validated JSON."
readme = "README.md"
requires-python = ">=3.12,<3.13"
dependencies = [
    "duckdb>=1.5.6",
    "openai>=3.28.0",
    "pydantic>=2.14.0",
    "pypdf>=6.20.0",
    "python-dotenv>=1.2.4",
]

[build-system]
requires = ["uv_build>=0.13.0,<0.14.0"]
build-backend = "uv_build"

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
# E/F = pycodestyle + pyflakes basics, I = import sorting, UP = modern syntax, B = common bugs
select = ["E", "F", "I", "UP", "B"]

[tool.pytest.ini_options]
testpaths = ["tests"]

[dependency-groups]
dev = [
    "ipykernel>=7.4.0",
    "jupyter>=1.1.1",
    "pytest>=9.1.1",
    "ruff>=0.17.0",
]
```

*Python here: [TOML, the config format](./py/phase-0a.md#py-1).*

- `[project]` is the `package.json` top half. `dependencies` is `dependencies`; `>=1.5.6` means
  "this or newer", like `^` but without an upper limit (the lockfile pins the exact one).
- What each library is for: **duckdb** the database (0b), **pydantic** typed data models (1a),
  **openai** the client we point at OpenRouter (1a), **python-dotenv** reads `.env` (1a),
  **pypdf** reads PDFs (0b page counts, 3a parsing).
- `[build-system]` tells tools how to turn `src/docintel` into an installable package. You never
  touch it.
- `[tool.*]` blocks are tool settings in one place, like an `"eslintConfig"` key in
  `package.json`.

Run:

```sh
uv tree --depth 1
```

Predict how many top-level entries you see, then check. You should see `docintel v0.1.0` with
nine children, four of them marked `(group: dev)`.

### 2. uv.lock and .python-version

**Why.** These two files make the setup reproducible. A fresh clone plus `uv sync` gives the exact
same 118 packages on the exact same Python.

`.python-version` is one line:

```
3.12
```

`uv.lock` is long and machine-written. Look at the top:

```sh
head -12 uv.lock
grep -c '^\[\[package\]\]' uv.lock
```

```
version = 1
revision = 5
requires-python = "==3.12.*"

[[package]]
name = "annotated-types"
version = "0.8.0"
...
118
```

- 118 packages, though you asked for nine. The rest are dependencies of dependencies (jupyter
  alone pulls in dozens). Same as `node_modules` being far bigger than `package.json`.
- Commit both files. `.venv/` is never committed; it is rebuilt from these.

Run:

```sh
uv sync
```

```
Resolved 118 packages in 3ms
Checked 115 packages in 10ms
```

"Resolved" means it checked the lockfile against `pyproject.toml`. "Checked" means `.venv`
already matches. Nothing to do. This is `npm ci` on a repo that is already installed.

### 3. .env.example and .gitignore

**Why.** Phase 1a calls OpenRouter, which needs a secret key. The key must never reach git.

```sh
# Copy to .env and fill in. .env is gitignored; never commit real keys.
OPENROUTER_API_KEY=
```

`.gitignore` is GitHub's standard Python template plus one block at the end:

```gitignore
# Project data (CUAD PDFs, DuckDB files)
data/
```

- Same pattern as Node: commit `.env.example`, ignore `.env`. The template already ignores
  `.env`, `.venv`, `__pycache__/` (Python's compiled-file cache) and `.ruff_cache/`.
- `data/` is ignored because CUAD is about 170 MB unzipped (plus the 106 MB zip), and anyone can re-download it with
  `make data` (0b).

Run:

```sh
cp .env.example .env
git check-ignore -v .env data/ .venv/
```

Predict: will `git check-ignore` print three lines or fewer? Each printed line names the
`.gitignore` rule that ignores the path. All three should print. Leave `.env` empty for now;
Phase 1a fills it.

Now one more. The first version of the loader lived in `src/docintel/data/`. Is that folder
ignored?

```sh
git check-ignore -v src/docintel/data/
```

<details><summary>Predict, then open</summary>

```
.gitignore:223:data/	src/docintel/data/
```

It is ignored. That is a bug in the setup. A pattern like `data/` with no leading slash matches a
folder called `data` **at any depth**, so it also swallows `src/docintel/data/`, and that code
would never have reached git. 0b moves the loader to `evals/`, but any future folder named `data`
would hit the same trap. A leading slash anchors the pattern to the repo root:

```gitignore
# Project data (CUAD PDFs, DuckDB files)
/data/
```

Make that one-character fix in `.gitignore`, then run the command again. It should print nothing
(not ignored), while `git check-ignore -v data/` still prints a line.
</details>

### 4. src/docintel/__init__.py

**Why.** This is the package. Every module in later parts (`docintel.evals`, `docintel.core`, ...)
is a subfolder next to this file.

```python
"""docintel: CUAD contract PDFs -> cited, validated JSON."""
```

*Python here: [packages and `__init__.py`](./py/phase-0a.md#py-2) ·
[docstrings](./py/phase-0a.md#py-3).*

- One docstring, no code. Its only job is to exist: a folder with an `__init__.py` is a package.
- The folder is called `docintel` while the repo is called `doc-intell-pipeline`. Python names
  cannot contain `-`, so the import name is always short and underscore-free.

Run:

```sh
uv run python -c "import docintel; print(docintel.__doc__); print(docintel.__file__)"
```

Predict both lines before running. The second is the full path to the file above.

### 5. tests/test_smoke.py

**Why.** A **smoke test** is the smallest test that proves the setup is alive. If it fails,
something is wrong with the environment, not with your code.

```python
"""Smoke test: proves the package and core deps import inside the uv env."""


def test_imports():
    import dotenv  # noqa: F401
    import duckdb  # noqa: F401
    import openai  # noqa: F401
    import pydantic  # noqa: F401

    import docintel  # noqa: F401
```

*Python here: [pytest discovery and bare `assert`](./py/phase-0a.md#py-4) ·
[`# noqa`](./py/phase-0a.md#py-5).*

- No `assert` needed: if any import fails, the test errors and goes red.
- pytest finds it because the file starts with `test_` and the function starts with `test_`. No
  registration, no config beyond `testpaths = ["tests"]`.
- The import of `python-dotenv` is `import dotenv`. Package names and import names differ
  sometimes. You install `python-dotenv` and `pypdf`, you import `dotenv` and `pypdf`.

Run:

```sh
make test
```

The output ends with `N passed`. Right now N is 8: this test plus seven loader tests from the old
0b code, which you delete and re-type in 0b.

### 6. Makefile

**Why.** Shortcuts for the five commands you run all the time.

```makefile
.PHONY: install data test lint fmt nb

install:  ## install all deps (incl. dev) into .venv
	uv sync

data:  ## download CUAD into data/raw/ + load DuckDB (data/docintel.duckdb)
	uv run python -m docintel.data

test:  ## run pytest
	uv run pytest

lint:  ## check style + common bugs (no changes)
	uv run ruff check .
	uv run ruff format --check .

fmt:  ## auto-fix lint + format
	uv run ruff check --fix .
	uv run ruff format .

nb:  ## launch Jupyter Lab in notebooks/
	uv run jupyter lab notebooks/
```

*Python here: [`python -m`](./py/phase-0a.md#py-6).*

- Each `name:` is a **target**, like a key in `"scripts"`. The indented lines under it must start
  with a real tab, not spaces. Make is strict about this.
- `.PHONY` says these targets are commands, not files. Without it, a folder named `data/` would
  make `make data` think the job is already done.
- `lint` checks and changes nothing (safe in CI). `fmt` rewrites files. Run `fmt`, then `lint`.

Run:

```sh
make lint
```

```
uv run ruff check .
All checks passed!
uv run ruff format --check .
N files already formatted
```

### 7. Commit

Commit only the setup. The old loader code stays uncommitted, because 0b deletes it. `git reset`
first unstages anything you added earlier (it touches only the staging area, never your files),
so the commit holds exactly this list.

```sh
git reset
git add pyproject.toml uv.lock .python-version .env.example .gitignore Makefile \
        src/docintel/__init__.py tests/test_smoke.py \
        README.md CLAUDE.md PLAN.md learn/
git diff --cached --stat
git diff --cached --name-only | grep -x '.env'
git diff --cached | grep -E 'sk-or-v1-[0-9a-f]{20,}'
git commit -m "phase 0a: project setup"
```

Both greps must print nothing. The first checks `.env` itself is not staged. The second looks for
a real key (`sk-or-v1-` followed by a long run of hex characters); placeholders like
`sk-or-v1-...` in the docs do not match. If either prints a line, run `git restore --staged <file>`
before committing.

---

## Test

```sh
make install && make test && make lint
```

All three succeed: `Checked 115 packages`, `N passed`, `All checks passed!`.

### Deliberate failure 1: a red test

Create `tests/test_scratch.py`:

```python
def test_parties_count():
    parties = ["Acme Inc.", "Beta LLC"]
    assert len(parties) == 3
```

Run `make test`. Expect:

```
>       assert len(parties) == 3
E       AssertionError: assert 2 == 3
E        +  where 2 = len(['Acme Inc.', 'Beta LLC'])
...
FAILED tests/test_scratch.py::test_parties_count
```

pytest rewrote a plain `assert` into a message showing both sides and where the `2` came from. Jest
needs `expect(x).toBe(y)` to get that; pytest gets it from `assert`.

### Deliberate failure 2: a lint error

Create `src/docintel/scratch.py`:

```python
import os
from typing import List
import json


def names(rows: List[dict]) -> list:
    x = 1
    return [r["name"] for r in rows]
```

Run `make lint`. Expect six errors, among them:

```
I001 [*] Import block is un-sorted or un-formatted
F401 [*] `os` imported but unused
UP035 `typing.List` is deprecated, use `list` instead
F841 Local variable `x` is assigned to but never used
Found 6 errors.
[*] 4 fixable with `--fix`
```

Each code maps to a rule set in `pyproject.toml`: `F` (pyflakes, real mistakes), `I` (imports),
`UP` (old syntax). Run `make fmt` and then `make lint` again. Predict which errors survive the
auto-fix (hint: ruff will not delete a line of logic for you).

Delete both scratch files when done. `make test` and `make lint` are green again.

- A `ModuleNotFoundError` in either command means you ran pytest or ruff without `uv run`.
- `make: *** missing separator` means the Makefile got spaces instead of a tab.

---

## Gotchas

- **Forgetting `uv run`.** The Mac's `python3` has none of the libraries. See Round 1.
- **VS Code picks the wrong Python.** Open the command palette, "Python: Select Interpreter",
  choose `./.venv/bin/python`. Otherwise the editor underlines every import in red while the
  code runs fine.
- **`uv add` while Jupyter is open.** The running notebook kernel will not see the new library.
  Restart the kernel (Kernel menu, Restart).
- **Editing `uv.lock` by hand.** Don't. Change `pyproject.toml` with `uv add` or `uv remove` and
  let uv rewrite the lock.

---

## Recap

`pyproject.toml` and `uv.lock` describe the project and pin every library; `.venv/` is the
installed copy, rebuilt with `uv sync`. `src/docintel/` is the package, installed in editable mode
so `import docintel` finds your live code. `make test` and `make lint` are the two checks every
later part ends with.

1. A teammate clones the repo and runs `python3 -m pytest`. It fails with
   `ModuleNotFoundError: No module named 'pydantic'`. What happened, and what is the one-word fix?
2. You run `uv add rich`. Name the three things that change, and which of them you commit.

Next, 0b: you delete the CUAD loader and type it back in, learning the CUAD format, why DuckDB, and
why the `contracts` and `labels` tables look the way they do.
