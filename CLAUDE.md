# CLAUDE.md

Document intelligence pipeline: CUAD contract PDFs → cited, validated JSON. Learning + portfolio project. Full plan: `PLAN.md`. Run log: `EXPERIMENTS.md`.

## Hard rules
- **Never commit, push, or create branches.** Only the user commits — they review the diff between phases. Leave all changes uncommitted.
- **Don't write core code.** User owns: schema, prompts, scoring, validation/citation/retry, experiment design, router rules, field planner, analysis, write-up. On these, explain/hint only — user types the code.
- **Claude owns infra only:** setup, data loading, LLM client, DuckDB, runners, parser wrappers, scan degrader, FastAPI, Docker, Cloud Run, Phoenix, charts. Leave stubs for user-owned functions; don't implement them.
- Stay within the current phase's prompt (P0.1, P1.2, …). No scope creep into later phases.
- Never tune or peek at the **test** split for decisions; dev only.

## How to work with the user
- User is a JS full-stack engineer, newer to Python. Explain like ELI15; compare to JS/npm/Express where useful.
- After each task: short explanation of every file/function created and why.
- Keep code small, readable, commented where non-obvious.
- No time estimates.
- Every experiment run → `run_id` in DuckDB + entry in `EXPERIMENTS.md`.

## Stack
Python 3.12, uv, pytest, ruff, Jupyter · OpenRouter (open-weight Qwen3 / Qwen3-VL, `response_format: json_schema`, `require_parameters: true`) · Pydantic · pypdf / Docling / Qwen3-VL parsers · DuckDB · Arize Phoenix (local) · FastAPI · Docker · GCP Cloud Run.

## Layout
`src/docintel/{data,llm,store,schema,extract,validate,score,parse,route,planner,api}` · `notebooks/` · `tests/` · `data/` (gitignored).

## Commands
_(fill in after P0.1 setup)_
