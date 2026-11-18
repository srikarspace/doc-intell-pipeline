# Python for Phase 4c

This file explains the new Python in Part 4c. There is very little: most of 4c is TypeScript, which you know. Read
one section when the main doc links to it.

<a id="py-1"></a>
## PY-1. `app.mount` and `StaticFiles(html=True)`

```python
from fastapi.staticfiles import StaticFiles

app.mount("/", StaticFiles(directory=WEB_DIST, html=True), name="web")
```

1. `StaticFiles(directory=...)` is a small app that sends files from one folder, as they are.
2. `app.mount("/", ...)` puts that small app under a path. A request for `/assets/index-CR3tJVz1.js` gets the file
   `web/dist/assets/index-CR3tJVz1.js`.
3. `html=True` adds one rule: a request for a folder (like `/`) gets the `index.html` inside it.
4. `name="web"` is a label. FastAPI needs one for every mount.

In Express, it is one line:

```js
app.use("/", express.static("web/dist"));
```

`express.static` sends `index.html` for `/` by default. In Starlette, you turn that on with `html=True`.

<a id="py-2"></a>
## PY-2. Order of routes and mounts, and `Path.is_dir()`

```python
WEB_DIST = Path("web/dist")

app.include_router(router)  # first: /health, /v1/...
if WEB_DIST.is_dir():
    app.mount("/", StaticFiles(directory=WEB_DIST, html=True), name="web")  # then: everything else
```

1. FastAPI checks routes and mounts **in the order they were added**. The first match wins.
2. A mount at `/` matches every path. So if it came first, `/v1/fields` would look for a file named `v1/fields`, and
   give a 404.
3. In Express it is the same: a `app.use(express.static(...))` placed before your routes is checked before them.
4. `Path("web/dist")` is relative to the folder you run the command from (the repo root with `make`), like
   `"data/docintel.duckdb"` in `config.py`.
5. `.is_dir()` is `True` only when that path exists and is a folder. In Node: `fs.existsSync(p) &&
   fs.statSync(p).isDirectory()`.
6. The `if` runs once, when Python imports `app.py`. So a build made after `make serve` started is only served after a
   restart. `make app` builds first, then starts the server.
