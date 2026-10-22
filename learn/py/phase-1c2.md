# Python for Phase 1c2

This file explains the new Python in Part 1c2. Read one section when the main doc links to it.
`try` / `except` is in the 1a2 companion ([PY-3](./phase-1a2.md#py-3)).

<a id="py-1"></a>
## PY-1. `ThreadPoolExecutor`, `submit` and `as_completed`

```python
pool = ThreadPoolExecutor(max_workers=concurrency)
futures = {pool.submit(extract, text, model, prompt_version=prompt_version): doc_id
           for doc_id, text in texts.items()}
for i, future in enumerate(as_completed(futures), start=1):
    result = future.result()
```

1. `ThreadPoolExecutor(max_workers=8)` starts a pool of up to 8 threads.
2. `pool.submit(fn, *args, **kwargs)` puts one job in the queue and returns a `Future` at once.
   The call `fn(*args, **kwargs)` happens later, on a free thread. Pass the function and its
   arguments, not `fn(...)`: that would run it right now, on this thread.
3. `as_completed(futures)` gives back each future when it is done, fastest first. Looping over a
   dict loops over its keys, so it gets the futures.
4. `future.result()` returns what `fn` returned. If `fn` raised an error, `result()` raises the
   same error here, in the main thread.
5. `enumerate(..., start=1)` counts the loop: `1, 2, 3, ...`. It gives the `[i/52]` numbers.

In JS, with the `p-limit` package:

```js
const limit = pLimit(8);
const jobs = docs.map(d => limit(() => extract(d.text)));
for (const job of jobs) { const result = await job; }   // in order, not fastest first
```

Python has a lock (the GIL) that lets only one thread run Python code at a time. That is fine
here: our threads spend almost all their time waiting for the network, and waiting does not
need the lock. For heavy math, threads would not help.

<a id="py-2"></a>
## PY-2. `try` / `finally` and Ctrl-C

```python
try:
    for i, future in enumerate(as_completed(futures), start=1):
        ...
finally:
    pool.shutdown(cancel_futures=True)
```

- The `finally` block always runs: after a normal end, after an error, and after Ctrl-C. In JS
  it is the same `try { } finally { }`.
- Ctrl-C raises `KeyboardInterrupt` in the main thread. It is an exception like any other, so
  `finally` runs, then Python stops and prints the traceback.
- `shutdown(cancel_futures=True)` cancels the jobs that have not started. It still waits for the
  ones that are running.

`except Exception` does not catch Ctrl-C. `KeyboardInterrupt` is not an `Exception` in Python,
on purpose: a broad `except` should never stop you from stopping a program.

<a id="py-3"></a>
## PY-3. `argparse` with subcommands

```python
parser = argparse.ArgumentParser(prog="python -m docintel.evals.runner")
sub = parser.add_subparsers(dest="command", required=True)
run = sub.add_parser("run", help="extract every doc of a split, then score the run")
run.add_argument("--limit", type=int, help="only the first N docs: a cheap pilot run")
run.add_argument("--yes", action="store_true", help="do not ask before spending money")
args = parser.parse_args(argv)
```

- `argparse` is Python's own flag parser, like `commander` or `yargs` in Node.
- `add_subparsers` makes subcommands. `dest="command"` stores the chosen one in
  `args.command`, as `"run"` or `"score"`.
- `--prompt-version` becomes `args.prompt_version`: dashes turn into underscores.
- `type=int` turns `"3"` into `3`. A flag you leave out is `None`, unless it has a `default`.
- `action="store_true"` makes a flag with no value: `--yes` gives `True`, no flag gives `False`.
- `choices=[...]` refuses any other value with a clear error.
- `--help` is made for you from the `help=` texts.

`parse_args(argv)` reads `sys.argv` when `argv` is `None`. A test can pass a list instead:
`parse_args(["run", "--limit", "3"])`.

Two more small tools in `main`:

- `datetime.now().strftime("%Y%m%d-%H%M%S")` formats the time as `20261021-143205`. `%Y` is the
  year, `%m` the month, `%H` the hour, and so on.
- `input("Start? [y/N] ")` prints the text and waits for one line from the keyboard.

<a id="py-4"></a>
## PY-4. Slices with `None`: `docs[:None]`

```python
n_docs = len(docs_for(con, split)[: args.limit])
```

- `docs[:3]` is the first 3 items, like JS `docs.slice(0, 3)`.
- `docs[:None]` is all items. `None` means "no end".
- `docs[:100]` on a list of 52 is all 52. A slice never fails for a number that is too big.

So when you leave out `--limit`, `args.limit` is `None`, and the slice keeps the whole split.
No `if` is needed.

<a id="py-5"></a>
## PY-5. `monkeypatch.setattr`: swap a function in one test

```python
monkeypatch.setattr(runner, "extract", fake_extract)
```

1. `monkeypatch` is a pytest fixture, like `tmp_path` in 0b ([PY-8](./phase-0b.md#py-8)). You
   get it by naming it as a test argument.
2. `setattr(runner, "extract", fake_extract)` replaces the name `extract` inside the `runner`
   module. `run_docs` looks up `extract` there, so it calls the fake.
3. After the test, pytest puts the real `extract` back. Other tests never see the fake.

In Jest: `jest.spyOn(runner, "extract").mockImplementation(fakeExtract)`, then
`mockRestore()`.

Patch the name where it is used, not where it is defined. `runner.py` did
`from ...extract import extract`, so it has its own name `runner.extract`. Patching
`docintel.domain.extract.extract.extract` would not change the one `run_docs` calls.
