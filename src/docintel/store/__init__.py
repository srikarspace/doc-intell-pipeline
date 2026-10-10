"""DuckDB connection helper. One file DB for the whole project."""

from pathlib import Path

import duckdb

DB_PATH = Path("data/docintel.duckdb")


def connect(path: Path | str = DB_PATH) -> duckdb.DuckDBPyConnection:
    """Open (or create) the project DuckDB file. Use ':memory:' for tests."""
    if str(path) != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(path))
