# Python for Phase 1b

This file explains the new Python in Part 1b. Read one section when the main doc links to it.
`pathlib` basics are in the 0b companion ([PY-1](./phase-0b.md#py-1)).

<a id="py-1"></a>
## PY-1. `Path(__file__).parent`: a folder next to this file

`__file__` is the path of the Python file that is running this line. `.parent` is its folder.

```python
PROMPTS = Path(__file__).parent / "prompts"
```

So `PROMPTS` is `.../src/docintel/domain/extract/prompts`, wherever you start the program from.
In Node: `path.join(__dirname, "prompts")`.

`Path("prompts")` is different. It means "a `prompts` folder in the current working folder",
like `path.resolve("prompts")` in Node. It breaks when you run from another folder (Break 2).

<a id="py-2"></a>
## PY-2. `read_text` and `write_text`

```python
system = (folder / "system.md").read_text(encoding="utf-8")
Path("data/examples/ecoscience_v1.json").write_text(r.raw_text, encoding="utf-8")
```

- `read_text()` reads the whole file into one string. In Node: `fs.readFileSync(p, "utf8")`.
- `write_text(s)` writes a string to a file, and replaces what was there.
- Always pass `encoding="utf-8"`. Without it, Python uses the computer's default, which is not
  UTF-8 on every system. Contracts have characters like `’` and `“`.
- `Path("data/examples").mkdir(exist_ok=True)` makes the folder, and does nothing if it is
  already there. Like `fs.mkdirSync(p, { recursive: true })`.

<a id="py-3"></a>
## PY-3. `str.replace`, `str.format` and f-strings

Three ways to put a value into a text:

```python
user.replace("{contract}", text)              # 1. find this exact string, put text there
user.format(contract=text)                    # 2. fill every {name} in user
f"prompt {version}: user.md must contain ..." # 3. f-string, written in the code
```

1. **`replace(old, new)`** changes every copy of one exact string. It reads nothing else. Like
   `str.replaceAll(old, new)` in JS.
2. **`format(...)`** treats every `{...}` in the text as a placeholder. A `{` that is not a
   placeholder, like in a JSON example, gives `KeyError`. To keep a real `{`, you must write
   `{{`.
3. **f-string**: an `f` before the quotes. `{version}` is filled from the variable `version`.
   Like a JS template literal `` `prompt ${version}` ``. Use it only for text you write in the
   code, never for a file you load.

Also used: `user.count("{contract}")` tells how many times the string appears. In JS:
`user.split("{contract}").length - 1`.

<a id="py-4"></a>
## PY-4. Returning two values, and unpacking

A function can return a **tuple**: several values in one, separated by commas.

```python
def load_prompt(version: str) -> tuple[str, str]:
    ...
    return system, user

system, user = load_prompt(version)       # unpacking: two names, two values
```

In JS: `return [system, user]` and `const [system, user] = loadPrompt(version)`.

A tuple with one item needs a comma. `fetchone()` returns a row as a tuple, here with one column:

```python
(txt_path,) = con.execute("SELECT txt_path FROM contracts WHERE doc_id = ?", [DOC]).fetchone()
```

The comma inside `(txt_path,)` says "unpack a one-item tuple". If the row is missing,
`fetchone()` gives `None`, and this line fails with `TypeError`. That is fine here: a missing
contract should stop the script.

<a id="py-5"></a>
## PY-5. `iterdir` and `is_dir`

```python
versions = [p.name for p in PROMPTS.iterdir() if p.is_dir()]
```

- `iterdir()` gives every file and folder directly inside a folder. Like `fs.readdirSync`.
- `is_dir()` is true for folders. So only `v1`, `v2`, ... are kept.
- `p.name` is the last part of the path: `"v1"`.

The order of `iterdir()` is not fixed. That does not matter here, because the test checks each
version on its own. Use `sorted(...)` when order matters (0d [PY-4](./phase-0d.md#py-4)).
