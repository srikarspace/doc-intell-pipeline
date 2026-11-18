# Python for Phase 4c3

This file explains the new Python in Part 4c3: `web/e2e/fixtures.py`. Read one section when the main doc links to it.
`with`, `fetchone` and DuckDB connections are in 4b2 ([PY-1](./phase-4b2.md#py-1), [PY-4](./phase-4b2.md#py-4)).

<a id="py-1"></a>
## PY-1. `argparse` with two commands

```python
parser = argparse.ArgumentParser(description=__doc__, formatter_class=raw)
commands = parser.add_subparsers(dest="command", required=True)
one = commands.add_parser("export", help="a stored answer -> a stream fixture")
one.add_argument("request_id")
one.add_argument("--db", default="data/docintel.duckdb")
args = parser.parse_args()
if args.command == "export":
    ...
```

1. `add_subparsers` makes commands, like `git commit` and `git push`. `dest="command"` puts the chosen name in
   `args.command`.
2. `add_argument("request_id")` is a required word after the command. `"--db"` is an option with a default.
3. `--help` is free: `fixtures.py export --help` prints the arguments.
4. In Node, it is like `commander`: `program.command("export <requestId>").option("--db <path>", "...", "data/...")`.

<a id="py-2"></a>
## PY-2. `duckdb.connect(..., read_only=True)` and `SystemExit`

```python
with duckdb.connect(db, read_only=True) as con:
    row = con.execute(query, [request_id]).fetchone()
if row is None:
    raise SystemExit(f"no stored answer with request_id {request_id!r}")
```

1. `read_only=True` opens the file for reading only, so the script can never change your data. If another program
   has the file open for writing at that moment, the open fails with the lock error from 4b2. The server opens it
   only for a moment per write (4b2), so this is rare.
2. `raise SystemExit("message")` stops the script, prints the message, and exits with code 1. In Node:
   `console.error(msg); process.exit(1)`.
3. `{request_id!r}` puts the value in quotes, so an empty or odd id is easy to see.

<a id="py-3"></a>
## PY-3. `model_validate`, and `except ...: pass`

```python
result = ExtractResult.model_validate(events[-1]["data"])
try:
    app_data.save_request(result.request_id, ROUTE, result.document, fields, result=result)
except duckdb.ConstraintException:
    pass  # already saved
```

1. `model_validate(dict)` builds a Pydantic model from a dict, and checks every field. A broken fixture fails here, with
   a clear message. In JS with zod: `ExtractResult.parse(data)`.
2. `events[-1]` is the last item: the `result` event. In JS: `events.at(-1)`.
3. `save_request` inserts with `request_id` as the PRIMARY KEY. A second seed of the same answer breaks that rule, and
   DuckDB raises `ConstraintException`.
4. `pass` means "do nothing". Here the row is already there, which is what we want. So seeding twice is safe.
