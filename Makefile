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

serve:  ## run the API on http://localhost:8000
	uv run uvicorn docintel.api.app:app --reload --no-access-log

nb:  ## launch Jupyter Lab in notebooks/
	uv run jupyter lab notebooks/

phoenix:  ## run Phoenix on http://localhost:6006 (traces are kept in data/phoenix/)
	PHOENIX_WORKING_DIR=data/phoenix PHOENIX_TELEMETRY_ENABLED=false \
	PHOENIX_AGENTS_DISABLE_BASH=true PHOENIX_AGENTS_DISABLE_WEB_ACCESS=true \
	PHOENIX_AGENTS_DISABLE_GITHUB=true \
	uvx --from arize-phoenix==21.0.0 phoenix serve
