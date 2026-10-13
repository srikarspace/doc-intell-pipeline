"""DuckDB connection helper. One database file for the whole project."""

from pathlib import Path

import duckdb

DB_PATH = Path("data/docintel.duckdb")


def connect(path: Path | str = DB_PATH) -> duckdb.DuckDBPyConnection:
    """Open (or create) the project database. Pass ":memory:" for a throwaway one in tests."""
    if str(path) != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(path))
