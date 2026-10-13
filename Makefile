.PHONY: install data test lint fmt nb

install:  ## install all deps (incl. dev) into .venv
	uv sync

data:  ## download CUAD into data/raw/ + load DuckDB (data/docintel.duckdb)
	uv run python -m docintel.evals.datasets

test:  ## run pytest
	uv run pytest

lint:  ## check style + common bugs (no changes)
	uv run ruff check .
	uv run ruff format --check .

fmt:  ## auto-fix lint + format
	uv run ruff check --fix .
	uv run ruff format .

nb:  ## launch Jupyter Lab in notebooks/
	uv run jupyter lab notebooks/
