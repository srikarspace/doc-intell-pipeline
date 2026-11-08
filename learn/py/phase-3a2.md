# Python for Phase 3a2

This file explains the new Python in Part 3a2. Read one section when the main doc links to it. `@lru_cache`
is in 1a ([PY-4](./phase-1a.md#py-4)).

<a id="py-1"></a>
## PY-1. An `import` inside a function

```python
@lru_cache
def get_converter():
    from docling.document_converter import DocumentConverter, PdfFormatOption
    ...
```

1. An `import` at the top of a file runs when the file is imported.
2. An `import` inside a function runs when the function is called.
3. Python remembers imported modules in `sys.modules`, so a second call does not load them again.

We normally put imports at the top. Here, Docling loads PyTorch, and most commands never need it.

In JS, it is `const { X } = await import('./heavy.js')` inside a function.

<a id="py-2"></a>
## PY-2. `resource.getrusage`: peak memory

```python
print("peak memory GB:", round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e9, 2))
```

`ru_maxrss` is the most memory this process has used so far. On a Mac, the number is in bytes. On Linux, it is
in kilobytes, so this exact line is only correct on a Mac.

In Node: `process.resourceUsage().maxRSS`.

<a id="py-3"></a>
## PY-3. A test that starts a new Python

```python
code = "import sys, docintel.domain.parse; sys.exit('torch' in sys.modules)"
assert subprocess.run([sys.executable, "-c", code]).returncode == 0
```

1. `sys.executable` is the path of the Python that is running now, so the new process uses the same `.venv`.
2. `-c` runs the text as a program. It is like `node -e`.
3. `sys.exit(False)` gives exit code 0, and `sys.exit(True)` gives exit code 1.
4. `.returncode` is that exit code.

So the test passes only if PyTorch was not loaded.

In Node: `spawnSync(process.execPath, ['-e', code]).status`.
