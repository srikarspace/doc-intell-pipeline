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
