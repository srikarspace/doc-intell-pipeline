"""Reuse stored answers as test fixtures, so the e2e test needs no paid model call.

Run from the repo root:

    uv run python web/e2e/fixtures.py export <request_id>   # -> web/src/fixtures/<sample>-...json
    uv run python web/e2e/fixtures.py seed <fixture.json>   # that answer -> `requests` in APP_DB
"""

import argparse
import json
from pathlib import Path

import duckdb

from docintel.core.config import get_settings
from docintel.db import app_data
from docintel.domain.pipeline import ExtractResult

FIXTURES = Path("web/src/fixtures")
ROUTE = "/v1/extract/stream"


def events_for(result: dict) -> list[dict]:
    """The stream the API sends for this answer. Attempts are not stored: one clean attempt."""
    return [
        {"event": "stage", "data": {"name": "parse", "status": "start"}},
        {
            "event": "stage",
            "data": {
                "name": "parse",
                "status": "done",
                "parser": result["parser"],
                "pages": result["pages"],
            },
        },
        {"event": "stage", "data": {"name": "extract", "status": "start"}},
        {"event": "attempt", "data": {"n": 0, "errors": 0}},
        {"event": "stage", "data": {"name": "check", "status": "start"}},
        {"event": "result", "data": result},
    ]


def export(request_id: str, db: str) -> Path:
    """Write one stored answer as a stream fixture. Read-only: the database is not changed."""
    query = "SELECT sample_id, result FROM requests WHERE request_id = ? AND status = 200"
    with duckdb.connect(db, read_only=True) as con:
        row = con.execute(query, [request_id]).fetchone()
    if row is None:
        raise SystemExit(f"no stored answer with request_id {request_id!r}")
    sample_id, result = row
    if sample_id is None:
        raise SystemExit("this answer is for an upload; the e2e test can only open samples")
    out = FIXTURES / f"{sample_id}-stream.json"
    out.write_text(json.dumps(events_for(json.loads(result)), indent=1) + "\n", encoding="utf-8")
    return out


def seed(path: str) -> str:
    """Save the fixture's answer in APP_DB, so reviews of it work. Running it twice is fine."""
    events = json.loads(Path(path).read_text(encoding="utf-8"))
    result = ExtractResult.model_validate(events[-1]["data"])
    try:
        fields = list(result.fields)
        app_data.save_request(result.request_id, ROUTE, result.document, fields, result=result)
    except duckdb.ConstraintException:
        pass  # already saved
    return result.request_id


if __name__ == "__main__":
    raw = argparse.RawTextHelpFormatter
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=raw)
    commands = parser.add_subparsers(dest="command", required=True)
    one = commands.add_parser("export", help="a stored answer -> a stream fixture")
    one.add_argument("request_id")
    one.add_argument("--db", default="data/docintel.duckdb")
    two = commands.add_parser("seed", help="a stream fixture -> the requests table of APP_DB")
    two.add_argument("fixture")
    args = parser.parse_args()
    if args.command == "export":
        print(f"wrote {export(args.request_id, args.db)}")
    else:
        print(f"saved {seed(args.fixture)} in {get_settings().app_db}")
