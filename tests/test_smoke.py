"""Smoke test: proves the package and core deps import inside the uv env."""


def test_imports():
    import dotenv  # noqa: F401
    import duckdb  # noqa: F401
    import openai  # noqa: F401
    import pydantic  # noqa: F401

    import docintel  # noqa: F401
