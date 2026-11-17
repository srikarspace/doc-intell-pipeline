# Phase 4b2: requests, reviews and a stats query

In this part, the app starts to remember. Every extract request becomes one row in DuckDB, the good ones and the failed
ones. Every review (Accept or Modify, from the review card in the prototype) becomes one row that points at a stored
answer. One query then gives you the numbers a product owner asks for: how many requests, how many failed, how slow,
how much money.

This is part 2 of 2 for Phase 4b. It needs 4b. The paid checkpoint costs about $0.0015.

## Words used in this part

Read these first.

- **Row**: one record in a table. Example: one extract request, with its status, cost and time.
- **PRIMARY KEY**: the column that names a row. No two rows can have the same one. Example: `request_id`.
- **UNIQUE**: a rule that no two rows may have the same values in these columns. Example: one review per
  `(request_id, field)`.
- **Constraint**: a rule the database checks on every write, like PRIMARY KEY and UNIQUE. A write that breaks it fails.
- **File lock**: DuckDB lets only one program open its file for writing at a time. A second one gets an error.
- **p50 / p95**: the time that 50% (or 95%) of requests are faster than. p50 is the usual case, p95 the slow case.
  Example: p95 = 30 s means 1 request in 20 takes longer than 30 s.
- **JSON column**: a column that stores a whole JSON value. Example: the full answer of a request.
- **Hard delete / soft delete**: remove the row, or keep it with a "deleted at" time.
- **201, 204, 409**: "Created", "done, nothing to send back" and "conflict with what is already there".

## Objectives

By the end of this part you should be able to:

1. Store one row per extract request, with the request_id from 4b as its key, even when the request fails.
2. Save a review against the stored answer, so the old value comes from the server, not the browser.
3. Let the database enforce "one review per field", and turn its error into a 409.
4. Undo a review with `DELETE`, and say what a 204 and a 404 mean there.
5. Read p50, p95, errors and cost from one SQL query, and say why p95 needs many requests.

## Dependencies

No new library. This part needs:

- 4b: the request_id on `request.state`, and `finished` / `failed` in `routes.py`.
- 4a: the `FieldName` type, the `api` fixture. 1a2: `evals/store.py` with `connect`.

## The big picture

Before this part, an answer was gone after the response. After this part:

```text
POST /v1/extract            -> row in `requests` (status 200, cost, latency, the full answer)
POST /v1/extract (too long) -> row in `requests` (status 413, the error)
POST /v1/reviews            -> row in `reviews` (old value from the stored answer, new value)
DELETE /v1/reviews/{id}     -> that row is gone
make stats                  -> requests, errors, p50, p95, cost per route; reviews per action
```

- **4c2** sends `POST /v1/reviews` from the review card, and `DELETE` from its undo button.
- **Phase 5** uses `make stats` for the README: real latency and cost per request.

## Remember this

> The server keeps its own copy of every answer, keyed by the request_id. A review only names the request and the
> field. The old value is read from the stored answer, so the browser cannot change history. The database itself
> enforces "one review per field", and one SQL query turns the rows into p50, p95, errors and cost.
>
> **Store the answer, review against the store.**

## Why

**Reviews are the product.** The UI flags fields for a human. If the human's choice is lost on refresh, the flag was
for nothing.

**A failed request is data too.** The error rate is "failed rows / all rows". With no row for a failure, the error
rate is always 0%.

**Numbers for the write-up must be real.** "p95 latency" and "cost per contract" in the README come from rows, not
from memory.

## Design decisions

- **The same DuckDB file as the evals.** One file, one `connect` helper, no new server. Other option: a second file
  for the app. That splits the data, and the lock problem stays the same (Gotchas).
- **A short connection per write.** Each write opens the file, writes and closes it. So `make stats` and a notebook can
  read in between. Other option: one connection for the life of the server. It would hold the file lock all the time.
- **The full answer is stored as JSON.** A review needs the old value, and 4c2 may want to reload a past answer. Other
  option: one row per field. More tables, and nothing needs it yet.
- **Rows are written in the API, not in `domain/`.** `run_pipeline` stays free of storage, like it is free of HTTP.
  Other option: save inside `run_pipeline`. Then the eval runner would write app rows too.
- **The browser never sends the old value.** It sends `request_id`, `field`, `action` and maybe `value`. Other option:
  send old and new. Then a bug or a bad client could write a wrong history.
- **Review rules are checked in two places.** Pydantic checks the shape (a known field, `modify` has a value). The
  database checks the state (the request exists, one review per field). Each check lives where the facts are.
- **Error types again, with their own status map.** `REVIEW_ERRORS` works like `KNOWN_ERRORS` from 4a. Other option:
  return `None` and check it in the route. The reason for the error would be lost.

## Worked example

All numbers are real. Guess before you open each box.

### Round 1: p50 and p95 of two requests

Two Kubient requests took 6,004 ms and 44,860 ms. DuckDB's `quantile_cont` draws a straight line between the sorted
values. Guess the p50 and the p95.

<details><summary>Guess, then open</summary>

```text
[(25432.0, 42917.2)]
```

p50 is halfway between the two: 25,432 ms. No request took that long. p95 is 95% of the way to the slow one: 42,917 ms.
With two requests, these numbers mean almost nothing. A p95 needs at least 20 requests before one request in 20 can
show up. Collect many requests before you write a p95 in the README.
</details>

### Round 2: what is the old value?

The model said `non_compete` was **not found** in Kubient (and the check flagged it). The user picks Modify, and types
`Yes: Customer may not work with any Third-Party`. Guess the `old` value in the saved review.

<details><summary>Guess, then open</summary>

```text
{"review_id":"5676e3de-06e6-47ac-b760-391c510e0e08","field":"non_compete","action":"modify","old":null,"new":"Yes: Customer may not work with any Third-Party"}
```

`null`, the model's real answer, read from the stored row. This review is a labeled mistake: a "not found" that a human
says was there. Rows like this are what a later eval set can be built from.
</details>

### Round 3: accept the same field twice

The user clicks Accept on `renewal_term`, then clicks it again (a double click). Guess the second answer.

<details><summary>Guess, then open</summary>

```text
{"detail":"'renewal_term' is already reviewed; undo it first"} 409
```

The `UNIQUE (request_id, field)` rule refused the second row. The code never looked for an old review first. The
database did the check, in the same step as the write, so two fast clicks cannot both get in.
</details>

## Project setup

```sh
mkdir -p src/docintel/db
touch src/docintel/db/__init__.py src/docintel/db/app_data.py
touch tests/test_reviews.py
```

You should now have:

```text
src/docintel/
├── db/
│   ├── __init__.py
│   └── app_data.py   # new: tables, save and undo, the stats query
├── api/
│   ├── routes.py     # changed: save rows, the review routes
│   └── schemas.py    # changed: Review, ReviewSaved
└── core/
    └── config.py     # changed: app_db
tests/
├── conftest.py       # changed: a temp database
└── test_reviews.py   # new
```

## Step 1: the tables

**Why.** Before any write, you decide what one row is.

### Your decision: the `requests` columns

Write your column list down before you open the reference. Questions to answer:

1. What does `make stats` need? (Route, status, latency, cost.)
2. What does a review need? (The answer, to read the old value.)
3. What does a failed request have? (No parser, no cost, but a status and an error.)
4. What finds the same contract again later? (4a's `Document`: filename, sha256, sample_id.)

Evidence: the real Kubient answer (12 fields, with highlights) is 3.5 KB of JSON. Even 1,000 requests are a few MB,
which is nothing for DuckDB.

<details><summary>Reference: the two tables, in <code>src/docintel/db/app_data.py</code></summary>

```python
"""The app's own data in DuckDB: one row per extract request, one row per review."""

import json
import uuid

import duckdb

from docintel.core.config import get_settings
from docintel.domain.pipeline import Document, ExtractResult
from docintel.evals.store import connect

TABLES = """
CREATE TABLE IF NOT EXISTS requests (
    request_id VARCHAR PRIMARY KEY,
    created_at TIMESTAMP DEFAULT current_timestamp,
    route VARCHAR,
    sample_id VARCHAR,
    filename VARCHAR,
    sha256 VARCHAR,
    fields VARCHAR[],
    status INTEGER,
    error VARCHAR,
    parser VARCHAR,
    pages INTEGER,
    needs_review BOOLEAN,
    cost_usd DOUBLE,
    latency_ms INTEGER,
    result JSON
);
CREATE TABLE IF NOT EXISTS reviews (
    review_id VARCHAR PRIMARY KEY,
    created_at TIMESTAMP DEFAULT current_timestamp,
    request_id VARCHAR,
    field VARCHAR,
    action VARCHAR,
    old_value JSON,
    new_value JSON,
    UNIQUE (request_id, field)
);
"""
```
</details>

Here, the reference has:

1. `requests`, keyed by the request_id from 4b. The columns after `error` are empty (`NULL`) for a failed request.
2. `fields VARCHAR[]`: a list column, the fields that were asked for. Empty means all 12.
3. `result JSON`: the whole `ExtractResult`.
4. `reviews`, with `UNIQUE (request_id, field)`. That one line is the "one review per field" rule (Step 3).

Add to the bottom of `src/docintel/db/app_data.py`:

```python
class NoRequest(LookupError):
    pass


class NotAsked(ValueError):
    pass


class AlreadyReviewed(ValueError):
    pass


def db() -> duckdb.DuckDBPyConnection:
    """A short connection. Use it in a `with` block, so the file is free again right after."""
    con = connect(get_settings().app_db)
    con.execute(TABLES)
    return con
```

Here, we:

1. Add three error types for reviews. Step 3 maps each one to a status code.
2. Open the file named by the `app_db` setting, and make the tables if they are not there yet.

Add the setting in `src/docintel/core/config.py`, under `tracing`:

```python
    app_db: str = "data/docintel.duckdb"  # requests and reviews; tests use a temp file
```

And in `tests/conftest.py`, give each test its own empty database. The `api` fixture asks for `tmp_path`, and sets one
more env var:

```python
def api(monkeypatch, sent, tmp_path) -> TestClient:
    """A TestClient with the fake model, the fake parser and a new, empty database."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-test")
    monkeypatch.setenv("APP_DB", str(tmp_path / "app.duckdb"))
```

Here, `tmp_path` is a new empty folder for each test, made by pytest. Without this line, every test run would write
rows into your real `data/docintel.duckdb`.

*Python: `with db() as con` is in [PY-1](./py/phase-4b2.md#py-1).*

Checkpoint:

```sh
uv run python -c "from docintel.db.app_data import db; con = db(); print(con.sql('SHOW TABLES'))"
```

```text
┌─────────────┐
│    name     │
│   varchar   │
├─────────────┤
│ answers     │
│ attempts    │
│ contracts   │
│ eval_sets   │
│ issues      │
│ labels      │
│ llm_calls   │
│ predictions │
│ requests    │
│ reviews     │
│ runs        │
│ scores      │
│ scores_r1   │
│ splits      │
└─────────────┘
    14 rows
```

The app's two tables now sit next to the eval tables from Phases 1 to 3.

## Step 2: one row per request

**Why.** The error rate, the p95 and the reviews all start from these rows.

Add to the bottom of `src/docintel/db/app_data.py`:

```python
def save_request(
    request_id: str,
    route: str,
    document: Document,
    fields: list[str],
    result: ExtractResult | None = None,
    status: int = 200,
    error: str | None = None,
) -> None:
    """One row per extract request, the good ones and the failed ones."""
    row = {
        "request_id": request_id,
        "route": route,
        "sample_id": document.sample_id,
        "filename": document.filename,
        "sha256": document.sha256,
        "fields": fields,
        "status": status,
        "error": error,
    }
    if result is not None:
        row |= {
            "parser": result.parser,
            "pages": result.pages,
            "needs_review": result.needs_review,
            "cost_usd": result.cost_usd,
            "latency_ms": result.latency_ms,
            "result": result.model_dump_json(),
        }
    columns = ", ".join(row)  # our own names; the values go in through `?`
    marks = ", ".join("?" for _ in row)
    with db() as con:
        con.execute(f"INSERT INTO requests ({columns}) VALUES ({marks})", list(row.values()))
```

Here, we:

1. Build the row as a dict: the parts every request has.
2. Add the parts only a good answer has, with `|=`.
3. Build the SQL from the dict's keys. The keys are our own names, so this is safe. The values go in through `?`, so
   the database never reads them as SQL.

*Python: `row |= {...}` and the joins are in [PY-2](./py/phase-4b2.md#py-2).*

Now call it from the two helpers in `src/docintel/api/routes.py`. Update the imports:

```python
from docintel.db import app_data
```

The helpers get the request, so they know the id and the route:

```python
def finished(request: Request, fields: list[str], result: ExtractResult) -> None:
    """One log line and one row per answer. Never log the contract text: it can be private."""
    log.info(
        "extract.done",
        parser=result.parser,
        pages=result.pages,
        fields=len(result.fields),
        needs_review=result.needs_review,
        cost_usd=result.cost_usd,
        latency_ms=result.latency_ms,
    )
    app_data.save_request(
        request.state.request_id, request.url.path, result.document, fields, result=result
    )


def failed(request: Request, document: Document, fields: list[str], error: HTTPException) -> None:
    log.warning("extract.failed", status=error.status_code, detail=error.detail)
    app_data.save_request(
        request.state.request_id,
        request.url.path,
        document,
        fields,
        status=error.status_code,
        error=error.detail,
    )
```

Then, in both routes, pass the new arguments: `finished(request, fields or [], result)` and
`failed(request, document, fields or [], error)`.

Checkpoint (free). Make a PDF with 101 blank pages, and send it:

```sh
uv run python -c "from pypdf import PdfWriter; w = PdfWriter(); [w.add_blank_page(612, 792) for _ in range(101)]; w.write('data/long.pdf')"
curl -s -X POST localhost:8000/v1/extract -F pdf=@data/long.pdf
```

```text
{"detail":"101 pages, the limit is 100"}
```

Then one paid request (about $0.001), and the stream with two fields (about $0.0004):

```sh
curl -s -X POST localhost:8000/v1/extract -F sample_id=kubient -o /dev/null
curl -sN -X POST localhost:8000/v1/extract/stream -F sample_id=kubient -F fields=parties -F fields=non_compete -o /dev/null
uv run python -c "from docintel.db.app_data import db; con = db(); print(con.sql('SELECT route, status, error, parser, cost_usd, latency_ms FROM requests ORDER BY created_at'))"
```

```text
┌────────────────────┬────────┬─────────────────────────────┬─────────┬────────────┬────────────┐
│       route        │ status │            error            │ parser  │  cost_usd  │ latency_ms │
│      varchar       │ int32  │           varchar           │ varchar │   double   │   int32    │
├────────────────────┼────────┼─────────────────────────────┼─────────┼────────────┼────────────┤
│ /v1/extract        │    413 │ 101 pages, the limit is 100 │ NULL    │       NULL │       NULL │
│ /v1/extract        │    200 │ NULL                        │ pypdf   │ 0.00102564 │      44860 │
│ /v1/extract/stream │    200 │ NULL                        │ pypdf   │ 0.00042504 │       6477 │
└────────────────────┴────────┴─────────────────────────────┴─────────┴────────────┴────────────┘
```

Three rows. The 413 has a status and an error, and nothing else. The first Kubient request was slow (45 s): one slow
call from the provider. Round 1 shows what that does to p50 and p95.

## Step 3: reviews

**Why.** The review card in 4c2 needs somewhere to save the user's choice.

### Your decision: the review rules

Write your rules down before you open the reference. Questions to answer:

1. **How many reviews per field?** One (a second one needs an undo first), or many (the newest wins).
2. **What does undo do?** Delete the row (hard), or mark it as undone (soft, keeps the history).
3. **Which fields can be reviewed?** Any of the 12, or only the ones the request asked for.

Evidence: the prototype has Accept, Modify and an undo link under each flagged row. Nothing in the app reads a review
history yet. The UI sends one review per click.

<details><summary>Reference: one review per field, hard delete, only asked fields</summary>

Add to `src/docintel/api/schemas.py` (with `from typing import Literal, Self`, `model_validator` from `pydantic`, and
`FieldName`):

```python
Value = str | list[str] | None  # the same type as a field's `value`
```

```python
class Review(BaseModel):
    """What the review card sends: accept the value, or replace it."""

    request_id: str
    field: FieldName
    action: Literal["accept", "modify"]
    value: Value = None  # only for "modify"

    @model_validator(mode="after")
    def value_only_when_modified(self) -> Self:
        if self.action == "modify" and self.value is None:
            raise ValueError("modify needs a value")
        if self.action == "accept" and self.value is not None:
            raise ValueError("accept keeps the old value, so send no value")
        return self


class ReviewSaved(BaseModel):
    review_id: str
    field: FieldName
    action: Literal["accept", "modify"]
    old: Value
    new: Value
```

Add to the bottom of `src/docintel/db/app_data.py`:

```python
def save_review(request_id: str, field: str, action: str, value=None) -> dict:
    """Accept or modify one field of one answer. The old value comes from our row, not the user."""
    with db() as con:
        found = con.execute(
            "SELECT result FROM requests WHERE request_id = ? AND status = 200", [request_id]
        ).fetchone()
        if found is None:
            raise NoRequest(f"no answer with request_id {request_id!r}")
        fields = json.loads(found[0])["fields"]
        if field not in fields:
            raise NotAsked(f"{field!r} was not asked for in this request")
        old = fields[field]["value"]
        new = old if action == "accept" else value
        review_id = str(uuid.uuid4())
        try:
            con.execute(
                "INSERT INTO reviews (review_id, request_id, field, action, old_value, new_value) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                [review_id, request_id, field, action, json.dumps(old), json.dumps(new)],
            )
        except duckdb.ConstraintException:
            raise AlreadyReviewed(f"{field!r} is already reviewed; undo it first") from None
    return {"review_id": review_id, "field": field, "action": action, "old": old, "new": new}


def undo_review(review_id: str) -> bool:
    """Delete one review. False when there was none."""
    with db() as con:
        gone = con.execute(
            "DELETE FROM reviews WHERE review_id = ? RETURNING review_id", [review_id]
        ).fetchall()
    return bool(gone)
```

Add to `src/docintel/api/routes.py`, next to `KNOWN_ERRORS`:

```python
REVIEW_ERRORS = {
    app_data.NoRequest: 404,
    app_data.NotAsked: 422,
    app_data.AlreadyReviewed: 409,
}
```

And at the bottom (with `Response` from `fastapi`, and `Review`, `ReviewSaved` from the schemas):

```python
@router.post("/v1/reviews", status_code=201)
def review(body: Review) -> ReviewSaved:
    """Accept or modify one field. One review per field: undo it to change your mind."""
    try:
        saved = app_data.save_review(body.request_id, body.field, body.action, body.value)
    except tuple(REVIEW_ERRORS) as e:
        raise HTTPException(REVIEW_ERRORS[type(e)], str(e)) from None
    log.info("review.saved", extract_id=body.request_id, field=body.field, action=body.action)
    return ReviewSaved(**saved)


@router.delete("/v1/reviews/{review_id}", status_code=204)
def undo(review_id: str) -> Response:
    if not app_data.undo_review(review_id):
        raise HTTPException(404, f"no review {review_id!r}")
    log.info("review.undone", review_id=review_id)
    return Response(status_code=204)
```
</details>

Here, the reference:

1. `Review` checks the shape. `field` is a `FieldName`, so `"price"` gets a 422 before any code runs (as in 4a). The
   `model_validator` checks the two fields together: `modify` needs a value, `accept` must not have one.
2. `save_review` reads the stored answer. No row (or a failed one) is `NoRequest`. A field that was not asked for is
   `NotAsked`.
3. The old value comes from the stored answer. For `accept`, the new value is the old one.
4. The insert is the check: the `UNIQUE` rule raises `ConstraintException`, which becomes `AlreadyReviewed`.
5. `undo_review` deletes the row. `RETURNING` gives back what was deleted, so "nothing" means 404.
6. The routes map each error type to its status, the same way as `KNOWN_ERRORS`.

*Python: `model_validator` and `Self` are in [PY-3](./py/phase-4b2.md#py-3). `RETURNING` and `fetchone` are in
[PY-4](./py/phase-4b2.md#py-4).*

Checkpoint (free). Use the request_id of your first Kubient request (it asked for all 12 fields). Your ids will
differ from the ones below:

```sh
R=63311fed-065e-4953-8a55-1e536bebc47e
curl -s -X POST localhost:8000/v1/reviews -H 'content-type: application/json' -d "{\"request_id\": \"$R\", \"field\": \"renewal_term\", \"action\": \"accept\"}"
curl -s -w " %{http_code}" -X POST localhost:8000/v1/reviews -H 'content-type: application/json' -d "{\"request_id\": \"$R\", \"field\": \"renewal_term\", \"action\": \"modify\"}"
```

```text
{"review_id":"b52495a9-8a36-4ab2-8bde-e60f0e2ab84b","field":"renewal_term","action":"accept","old":null,"new":null}
{"detail":[{"type":"value_error","loc":["body"],"msg":"Value error, modify needs a value","input":{"request_id":"63311fed-065e-4953-8a55-1e536bebc47e","field":"renewal_term","action":"modify"},"ctx":{"error":{}}}]} 422
```

A field the stream request did not ask for:

```sh
curl -s -w " %{http_code}" -X POST localhost:8000/v1/reviews -H 'content-type: application/json' -d '{"request_id": "f144d0b1-d6f3-44e5-8765-1d9a0c64cafd", "field": "governing_law", "action": "accept"}'
```

```text
{"detail":"'governing_law' was not asked for in this request"} 422
```

Then undo the `non_compete` review from Round 2, twice:

```sh
curl -s -w "%{http_code}" -X DELETE localhost:8000/v1/reviews/5676e3de-06e6-47ac-b760-391c510e0e08
curl -s -w " %{http_code}" -X DELETE localhost:8000/v1/reviews/5676e3de-06e6-47ac-b760-391c510e0e08
```

```text
204
{"detail":"no review '5676e3de-06e6-47ac-b760-391c510e0e08'"} 404
```

The server log has one line per review. For an Accept on `parties`, then its undo:

```text
{"extract_id": "63311fed-065e-4953-8a55-1e536bebc47e", "field": "parties", "action": "accept", "event": "review.saved", "request_id": "9d41593a-b028-4228-989a-2116e5e86995", "level": "info", "timestamp": "2026-11-17T04:15:49.191685Z"}
{"review_id": "5ea80886-3dce-4f72-a332-a3229c0638f3", "event": "review.undone", "request_id": "f20dcf86-3548-4a6f-af24-28779d2032bb", "level": "info", "timestamp": "2026-11-17T04:15:49.272425Z"}
```

Look at the two ids. `request_id` is the id of the review request itself (from the 4b middleware). `extract_id` is the
answer that was reviewed.

## Step 4: the stats query

**Why.** One command answers "how is the app doing?".

Add to the bottom of `src/docintel/db/app_data.py`:

```python
STATS = """
SELECT route,
       count(*) AS requests,
       count(*) FILTER (WHERE status <> 200) AS errors,
       round(quantile_cont(latency_ms, 0.5)) AS p50_ms,
       round(quantile_cont(latency_ms, 0.95)) AS p95_ms,
       round(sum(cost_usd), 5) AS cost_usd
FROM requests
GROUP BY route
ORDER BY route
"""
REVIEW_COUNTS = "SELECT action, count(*) AS reviews FROM reviews GROUP BY action ORDER BY action"


if __name__ == "__main__":
    with db() as con:
        print(con.sql(STATS))
        print(con.sql(REVIEW_COUNTS))
```

Here, we:

1. Group the rows by route, and count all of them and the failed ones (`FILTER` counts only the rows that match).
2. Take p50 and p95 with `quantile_cont`. It skips `NULL`, so failed rows (no latency) do not pull the numbers down.
3. Add up the cost. Failed rows add nothing (see Gotchas).
4. Count the reviews by action.

Add a target to `Makefile`:

```makefile
stats:  ## p50, p95, errors and cost of the app requests, and the review counts
	uv run python -m docintel.db.app_data
```

Checkpoint. The server can keep running, because it holds the file only while it writes:

```sh
make stats
```

```text
┌────────────────────┬──────────┬────────┬─────────┬─────────┬──────────┐
│       route        │ requests │ errors │ p50_ms  │ p95_ms  │ cost_usd │
│      varchar       │  int64   │ int64  │ double  │ double  │  double  │
├────────────────────┼──────────┼────────┼─────────┼─────────┼──────────┤
│ /v1/extract        │        2 │      1 │ 44860.0 │ 44860.0 │  0.00103 │
│ /v1/extract/stream │        1 │      0 │  6477.0 │  6477.0 │  0.00043 │
└────────────────────┴──────────┴────────┴─────────┴─────────┴──────────┘

┌─────────┬─────────┐
│ action  │ reviews │
│ varchar │  int64  │
├─────────┼─────────┤
│ accept  │       1 │
│ modify  │       1 │
└─────────┴─────────┘
```

`/v1/extract` has 2 requests and 1 error (the 413). Its p50 and p95 are the same: there is only one good request in
it. Round 1 explains why that number is not worth writing down yet.

## Step 5: a small test

**Why.** A lost row or a second review would break no other test, and the UI would look fine.

The test names say what is protected: every request is one row, even a failed one; the old value comes from the
server; one review per field, and undo frees it; bad reviews are refused.

<details><summary>Put this in <code>tests/test_reviews.py</code></summary>

```python
"""Rows for requests and reviews, in a temp database. The fakes come from `conftest.py`."""

from docintel.db.app_data import db
from docintel.domain import pipeline
from docintel.domain.pipeline import TooLong


def extract(api, fields: list[str]) -> dict:
    return api.post("/v1/extract", data={"sample_id": "kubient", "fields": fields}).json()


def review(api, request_id: str, field: str, action: str, value=None):
    body = {"request_id": request_id, "field": field, "action": action, "value": value}
    return api.post("/v1/reviews", json=body)


def test_every_request_is_one_row_even_a_failed_one(api, monkeypatch):
    extract(api, ["parties"])

    def too_long(path):
        raise TooLong("120 pages, the limit is 100")

    monkeypatch.setattr(pipeline, "parse_pdf", too_long)
    extract(api, ["parties"])
    with db() as con:
        rows = con.execute(
            "SELECT status, error, fields FROM requests ORDER BY created_at"
        ).fetchall()
    assert rows == [(200, None, ["parties"]), (413, "120 pages, the limit is 100", ["parties"])]


def test_the_old_value_comes_from_the_server(api):
    answer = extract(api, ["parties"])
    saved = review(api, answer["request_id"], "parties", "modify", ["Acme Inc."]).json()
    assert saved["old"] == ["Acme Inc.", "Beta LLC"]  # from the stored answer, not from the browser
    assert saved["new"] == ["Acme Inc."]


def test_one_review_per_field_and_undo_frees_it(api):
    request_id = extract(api, ["parties"])["request_id"]
    first = review(api, request_id, "parties", "accept")
    assert first.status_code == 201
    assert review(api, request_id, "parties", "accept").status_code == 409
    review_id = first.json()["review_id"]
    assert api.delete(f"/v1/reviews/{review_id}").status_code == 204
    assert api.delete(f"/v1/reviews/{review_id}").status_code == 404
    assert review(api, request_id, "parties", "accept").status_code == 201


def test_bad_reviews_are_refused(api):
    request_id = extract(api, ["parties"])["request_id"]
    assert review(api, "no-such-id", "parties", "accept").status_code == 404
    assert review(api, request_id, "governing_law", "accept").status_code == 422  # not asked
    assert review(api, request_id, "parties", "modify").status_code == 422  # no value
```
</details>

Here, each test gets a new empty database from the `api` fixture. `db()` in a test opens that same temp file, because
it reads the same `APP_DB` setting.

Checkpoint:

```sh
uv run pytest -q tests/test_reviews.py
make test
```

```text
4 passed in 0.58s
132 passed in 2.79s
```

<details><summary>Full <code>src/docintel/db/app_data.py</code></summary>

```python
"""The app's own data in DuckDB: one row per extract request, one row per review."""

import json
import uuid

import duckdb

from docintel.core.config import get_settings
from docintel.domain.pipeline import Document, ExtractResult
from docintel.evals.store import connect

TABLES = """
CREATE TABLE IF NOT EXISTS requests (
    request_id VARCHAR PRIMARY KEY,
    created_at TIMESTAMP DEFAULT current_timestamp,
    route VARCHAR,
    sample_id VARCHAR,
    filename VARCHAR,
    sha256 VARCHAR,
    fields VARCHAR[],
    status INTEGER,
    error VARCHAR,
    parser VARCHAR,
    pages INTEGER,
    needs_review BOOLEAN,
    cost_usd DOUBLE,
    latency_ms INTEGER,
    result JSON
);
CREATE TABLE IF NOT EXISTS reviews (
    review_id VARCHAR PRIMARY KEY,
    created_at TIMESTAMP DEFAULT current_timestamp,
    request_id VARCHAR,
    field VARCHAR,
    action VARCHAR,
    old_value JSON,
    new_value JSON,
    UNIQUE (request_id, field)
);
"""


class NoRequest(LookupError):
    pass


class NotAsked(ValueError):
    pass


class AlreadyReviewed(ValueError):
    pass


def db() -> duckdb.DuckDBPyConnection:
    """A short connection. Use it in a `with` block, so the file is free again right after."""
    con = connect(get_settings().app_db)
    con.execute(TABLES)
    return con


def save_request(
    request_id: str,
    route: str,
    document: Document,
    fields: list[str],
    result: ExtractResult | None = None,
    status: int = 200,
    error: str | None = None,
) -> None:
    """One row per extract request, the good ones and the failed ones."""
    row = {
        "request_id": request_id,
        "route": route,
        "sample_id": document.sample_id,
        "filename": document.filename,
        "sha256": document.sha256,
        "fields": fields,
        "status": status,
        "error": error,
    }
    if result is not None:
        row |= {
            "parser": result.parser,
            "pages": result.pages,
            "needs_review": result.needs_review,
            "cost_usd": result.cost_usd,
            "latency_ms": result.latency_ms,
            "result": result.model_dump_json(),
        }
    columns = ", ".join(row)  # our own names; the values go in through `?`
    marks = ", ".join("?" for _ in row)
    with db() as con:
        con.execute(f"INSERT INTO requests ({columns}) VALUES ({marks})", list(row.values()))


def save_review(request_id: str, field: str, action: str, value=None) -> dict:
    """Accept or modify one field of one answer. The old value comes from our row, not the user."""
    with db() as con:
        found = con.execute(
            "SELECT result FROM requests WHERE request_id = ? AND status = 200", [request_id]
        ).fetchone()
        if found is None:
            raise NoRequest(f"no answer with request_id {request_id!r}")
        fields = json.loads(found[0])["fields"]
        if field not in fields:
            raise NotAsked(f"{field!r} was not asked for in this request")
        old = fields[field]["value"]
        new = old if action == "accept" else value
        review_id = str(uuid.uuid4())
        try:
            con.execute(
                "INSERT INTO reviews (review_id, request_id, field, action, old_value, new_value) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                [review_id, request_id, field, action, json.dumps(old), json.dumps(new)],
            )
        except duckdb.ConstraintException:
            raise AlreadyReviewed(f"{field!r} is already reviewed; undo it first") from None
    return {"review_id": review_id, "field": field, "action": action, "old": old, "new": new}


def undo_review(review_id: str) -> bool:
    """Delete one review. False when there was none."""
    with db() as con:
        gone = con.execute(
            "DELETE FROM reviews WHERE review_id = ? RETURNING review_id", [review_id]
        ).fetchall()
    return bool(gone)


STATS = """
SELECT route,
       count(*) AS requests,
       count(*) FILTER (WHERE status <> 200) AS errors,
       round(quantile_cont(latency_ms, 0.5)) AS p50_ms,
       round(quantile_cont(latency_ms, 0.95)) AS p95_ms,
       round(sum(cost_usd), 5) AS cost_usd
FROM requests
GROUP BY route
ORDER BY route
"""

REVIEW_COUNTS = "SELECT action, count(*) AS reviews FROM reviews GROUP BY action ORDER BY action"


if __name__ == "__main__":
    with db() as con:
        print(con.sql(STATS))
        print(con.sql(REVIEW_COUNTS))
```
</details>

## Break it on purpose

The breaks are free. Put the code back after each one.

**Break 1: drop the UNIQUE rule.** In `TABLES`, remove the line `UNIQUE (request_id, field)`, and the comma at the end
of the line before it. Guess which line of which test fails.

<details><summary>What you see</summary>

```text
>       assert review(api, request_id, "parties", "accept").status_code == 409
E       AssertionError: assert 201 == 409
1 failed, 3 passed in 1.20s
```

The second Accept is saved. Now one field has two reviews, and nothing says which one counts. The tests use a new
database each time, so they see the change at once. Your real `data/docintel.duckdb` would not: `CREATE TABLE IF NOT
EXISTS` never changes a table that is already there.
</details>

**Break 2: forget the failed rows.** In `failed`, delete the `app_data.save_request(...)` call. Guess what the stats
would say.

<details><summary>What you see</summary>

```text
E       AssertionError: assert [(200, None, ['parties'])] == [(200, None, ... ['parties'])]
E         Right contains one more item: (413, '120 pages, the limit is 100', ['parties'])
```

Only the good request has a row. `make stats` would show 0 errors, always. The error rate would look perfect, because
the errors were never written down.
</details>

## Experiment

This part runs no experiment. The `make stats` numbers come from three checkpoint requests. Before you put a p95 in the
README (Phase 5), run at least 20 requests on the dev samples, and write their `make stats` table in `EXPERIMENTS.md`.

## Gotchas

- **An open notebook locks the database.** Run `make nb`, open `data/docintel.duckdb`, then try a review. The route
  fails with 500, and the server log says:

  ```text
  _duckdb.IOException: IO Error: Could not set lock on file ".../data/docintel.duckdb": Conflicting lock is held in .../python3.12 (PID 4537) by user srikarkoppisetti. See also https://duckdb.org/docs/stable/connect/concurrency
  ```

  Close the notebook's connection (`con.close()`), or open it with `read_only=True`. The eval runner has the same
  problem: do not run evals while the app is serving.
- **A failed request can still cost money.** `NoAnswer` comes after three paid attempts, but its row has no cost. The
  cost is in the trace (4b, on each `attempt`).
- **A table change needs a migration.** `CREATE TABLE IF NOT EXISTS` makes a table once. To add a column later, run
  `ALTER TABLE` by hand, or delete the two tables (only on your machine, never with real reviews in them).
- **A crash (500) leaves no row.** Only the known errors are saved. A bug shows up in the log (`extract.crashed`), not in
  `make stats`.

## Explain back, then commit

Explain to Claude in a few sentences:

- Your two decisions: the `requests` columns and the review rules, and why.
- `app_data.py`: why one short connection per write, and why the SQL built from the dict's keys is safe.
- `routes.py`: where each row is written, and what a failed request's row holds.
- `schemas.py` and `save_review`: which check is in Pydantic, which is in the database, and why the old value never
  comes from the browser.
- What 201, 204, 404, 409 and 422 mean for the review routes.
- `make stats`: what p50 and p95 mean, and why two requests are not enough (Round 1).

Then:

```sh
git status
git add Makefile src/docintel/core/config.py src/docintel/db/__init__.py src/docintel/db/app_data.py src/docintel/api/routes.py src/docintel/api/schemas.py tests/conftest.py tests/test_reviews.py
git commit -m "phase 4b2: request and review rows in DuckDB, and a stats query"
```

## Conclusion

The app now remembers every request and every human review, and one command turns them into numbers. Phase 4b is
done. Go back through the objectives and check each one without notes. Then answer:

1. A user clicks Accept twice, very fast. Why can only one of the two clicks be saved?
2. Your README says "p95: 12 s". Which query gave that number, over how many requests, and why does the count matter?

Looking for more challenges? Try these (optional):

1. Add `GET /v1/requests/{request_id}` that returns the stored answer, with its reviews applied.
2. Add a `p95` per parser (pypdf and Docling OCR) to `STATS`, and guess the gap before you run it.

Checklist (`../PLAN.md`): **Human review** (Accept and Modify saved, with undo). **Cost and latency tracking**
(p50, p95, cost per route from real rows). **Observability** (errors counted, review log lines). Next: 4c.
