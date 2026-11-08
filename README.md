# doc-intell-pipeline

Contract PDFs in, cited and validated JSON out. Each answer comes with the exact quote from the contract and a needs-review flag.

Built from **Project 1: Document intelligence pipeline** in [AI Engineer Projects](https://github.com/aishwaryanr/awesome-generative-ai-guide/blob/main/youtube/ai-engineer-projects.md) by Aishwarya Reganti ([aishwaryanr/awesome-generative-ai-guide](https://github.com/aishwaryanr/awesome-generative-ai-guide)). The project uses CUAD and measures precision and recall per field.

## What it answers

1. Which documents did we choose, and why?
2. OCR-style parsing or multimodal parsing: which gives better quality for the cost?
3. Which fields does the model handle well or badly, and why?
4. Schema validation: what broke, what we caught, and did retries help?

## Status

| Phase | Parts | Status |
|---|---|---|
| 0 setup + data | [0a](./learn/phase-0a.md) setup · [0b](./learn/phase-0b.md) loader · [0c](./learn/phase-0c.md) explore · [0d](./learn/phase-0d.md) fields + split | done |
| 1 baseline extraction | [1a](./learn/phase-1a.md) schema · [1a2](./learn/phase-1a2.md) LLM client · [1b](./learn/phase-1b.md) prompt + extract · [1b2](./learn/phase-1b2.md) scoring · [1c](./learn/phase-1c.md) store + score · [1c2](./learn/phase-1c2.md) batch run · [1c3](./learn/phase-1c3.md) E1 results · [1c4](./learn/phase-1c4.md) model comparison · [1d](./learn/phase-1d.md) scoring review · [1d2](./learn/phase-1d2.md) prompt v2 | done |
| 2 trust layer | [2a](./learn/phase-2a.md) validators + citations · [2a2](./learn/phase-2a2.md) needs-review rules · [2b](./learn/phase-2b.md) retry loop · [2b2](./learn/phase-2b2.md) trust replay tool · [2b3](./learn/phase-2b3.md) trust run | done |
| 3 parser comparison | pypdf, Docling, vision LLM (chosen in 3a3) · scans | planned |
| 4 service | planner + API · observability · Docker, Cloud Run, CI · UI | planned |
| 5 write-up | figures, README, mock interview | planned |

## Results so far (dev, 52 contracts, 12 fields)

| Experiment | What changed | F1 |
|---|---|---|
| E1 | Qwen3-235B, prompt v1 | 0.705 |
| E1.1 | DeepSeek V4 Flash, same prompt. Tied with the other new models, kept for cost and p95 | 0.801 |
| E1.2 | Fairer scoring rules, same stored answers, no new calls (E1 becomes 0.827) | 0.912 |
| E1.3 | Prompt v2 for 4 weak fields, on Parasail. Not kept: the gain could be zero, and it failed the keep rule written before the run | 0.917 (v1 on Parasail: 0.907) |
| E2.0 | Validation and review flags on the E1.2 run, no new calls. Errors 0.5% of fields, needs review 5.6%, 0 made-up quotes | 0.912 |
| E2.1 | Blank fields with a validation error, on the first answers of a `--retries 2` run on Parasail. Not kept: lost 3 right answers | 0.903 -> 0.899 |
| E2.2 | Also blank fields whose quote is not in the contract. Not kept: both caught quotes were right answers with copy errors | 0.903 -> 0.895 |
| E2.3 | Repair retries (max 2). Kept by the rule written before the run: 1 field fixed, 0 lost, +7% cost | 0.903 -> 0.903 |

E1 and E1.1 use the old scoring rules. Phase 2 builds on the E1.2 row: DeepSeek V4 Flash, prompt v1,
run `20261102-200003`. E2.1 to E2.3 come from one run, `20261108-062221`: its first answers are the
"before" and its final answers the "after". Details and limits are in [EXPERIMENTS.md](./EXPERIMENTS.md).
Test split numbers come at the end.

There are two notes for each part. `learn/phase-N.md` covers what the part builds and why. `learn/py/phase-N.md` covers the Python it uses. The full plan is in [PLAN.md](./PLAN.md), and runs are logged in [EXPERIMENTS.md](./EXPERIMENTS.md).

## Stack

Python 3.12, uv, pytest, ruff · OpenRouter (DeepSeek V4 Flash, kept in E1.1; `response_format: json_schema`, `require_parameters: true`) · Pydantic · DuckDB.

Planned additions: Docling and vision LLM parsers, FastAPI, Phoenix, Docker, Cloud Run and Next.js.

## Quickstart

```bash
make install   # uv sync
make data      # download CUAD, load data/docintel.duckdb
make test      # pytest; no network calls
make lint      # ruff
```

Put the OpenRouter key in `.env`, which is gitignored:

```bash
OPENROUTER_API_KEY=sk-or-v1-...
DOCINTEL_MODEL=deepseek/deepseek-v4-flash   # the kept model; without this line, the code uses qwen/qwen3-235b-a22b-2507
DOCINTEL_PROVIDER=parasail                  # optional; parasail is the default, and it has no backup
```

Main commands:

```bash
uv run python -m docintel.evals.runner run --split dev   # extract, retry (default 2), score, validate
uv run python -m docintel.evals.runner report <run_id>   # P/R/F1 per field, cost, latency
uv run python -m docintel.evals.runner validate <run_id> # store issues again, review report
uv run python -m docintel.evals.trust <run_id>           # first vs final answers, under 3 policies
```

DuckDB tables:
- `contracts`, `labels` and `splits` come from `make data`.
- `llm_calls` logs tokens, cost and latency for each call.
- `runs`, `predictions` and `scores` hold each eval run, its answers and its marks.
- `scores_r1` keeps the marks from the old scoring rules (see E1.2).
- `issues` holds each rule a field broke (errors and warnings); `attempts` holds every call of a retry
  run, with its errors and cost.
- Runs named `<run_id>-first`, `-blank-v`, ... are derived by `trust`: stored answers, no new calls.

To browse the database, run `duckdb -readonly data/docintel.duckdb` or `make nb`.

## Resources

- **Project brief:** [AI Engineer Projects](https://github.com/aishwaryanr/awesome-generative-ai-guide/blob/main/youtube/ai-engineer-projects.md), Project 1 (aishwaryanr/awesome-generative-ai-guide)
- **Data:** [CUAD v1](https://zenodo.org/records/4595826), the Contract Understanding Atticus Dataset. It has 510 contracts and 41 clause categories labelled by lawyers. License: CC BY 4.0.
  - Paper: Hendrycks et al., [CUAD: An Expert-Annotated NLP Dataset for Legal Contract Review](https://arxiv.org/abs/2103.06268) (NeurIPS 2021)
  - Project page: [atticusprojectai.org/cuad](https://www.atticusprojectai.org/cuad)
  - Zip: [CUAD_v1.zip](https://zenodo.org/records/4595826/files/CUAD_v1.zip) (~106 MB, md5 `c38f490a984420b8a62600db401fafd5`). It is saved to `data/raw/`, which is gitignored.
- **Doc style:** [testdriven.io FastAPI CRUD tutorial](https://testdriven.io/blog/fastapi-crud/)
