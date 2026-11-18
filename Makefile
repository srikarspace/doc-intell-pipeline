.PHONY: install data test lint fmt serve stats nb phoenix web-install web web-test app e2e

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

stats:  ## p50, p95, errors and cost of the app requests, and the review counts
	uv run python -m docintel.db.app_data

nb:  ## launch Jupyter Lab in notebooks/
	uv run jupyter lab notebooks/

phoenix:  ## run Phoenix on http://localhost:6006 (traces are kept in data/phoenix/)
	PHOENIX_WORKING_DIR=data/phoenix PHOENIX_TELEMETRY_ENABLED=false \
	PHOENIX_AGENTS_DISABLE_BASH=true PHOENIX_AGENTS_DISABLE_WEB_ACCESS=true \
	PHOENIX_AGENTS_DISABLE_GITHUB=true \
	uvx --from arize-phoenix==21.0.0 phoenix serve

web-install:  ## install the UI's npm packages into web/node_modules (exact versions from the lockfile)
	cd web && npm ci

web:  ## run the UI on http://localhost:5173 (needs `make serve` in another terminal)
	cd web && npm run dev

web-test:  ## check the UI's types, then run its test
	cd web && npm run typecheck && npm test

app:  ## build the UI into web/dist, then serve the UI and the API on http://localhost:8000
	cd web && npm run build
	uv run uvicorn docintel.api.app:app --no-access-log

e2e:  ## build the UI, then run the Playwright test on a stored answer (no model call); VIDEO=1 records it
	cd web && npm run build && npx playwright test
