# doc-intell-pipeline

Document intelligence pipeline: CUAD contract PDFs → cited, validated JSON.

## Learning notes

Each part has notes in `learn/`:

- `learn/phase-N.md` covers what the part builds, why each file exists, the design decisions, and the code.
- `learn/py/phase-N.md` covers the Python the part uses.

## Roadmap

| Week | Phase | Parts | Status |
|---|---|---|---|
| 1 | 0 setup + data | [0a](./learn/phase-0a.md) setup · [0b](./learn/phase-0b.md) data loader · [0c](./learn/phase-0c.md) explore · [0d](./learn/phase-0d.md) fields, subset, split | in progress |
| 1–2 | 1 baseline extraction | 1a schema + LLM client · 1b extract + score · 1c batch run | planned |
| 2 | 2 trust layer | 2a validators + citations · 2b retry + experiments | planned |
| 2 | 3 parser comparison | 3a pypdf, Docling, Qwen3-VL · 3b scans + experiment | planned |
| 3 | 4 service (prod bar) | 4a planner + API · 4b observability · 4c Docker, Cloud Run, CI · 4d UI | planned |
| 3 | 5 write-up | figures, README, mock interview | planned |

Full plan: [PLAN.md](./PLAN.md). Run log: [EXPERIMENTS.md](./EXPERIMENTS.md).

## Data source

**CUAD v1** (Contract Understanding Atticus Dataset): 510 commercial contracts with 41 clause categories labelled by lawyers.

- Download (used by `docintel.evals.datasets`): https://zenodo.org/records/4595826/files/CUAD_v1.zip (~106 MB, md5 `c38f490a984420b8a62600db401fafd5`)
- Zenodo record: https://zenodo.org/records/4595826
- Project page: https://www.atticusprojectai.org/cuad
- Paper: Hendrycks et al., *CUAD: An Expert-Annotated NLP Dataset for Legal Contract Review* (NeurIPS 2021), https://arxiv.org/abs/2103.06268
- License: CC BY 4.0

The files are downloaded to `data/raw/`, which is gitignored.

## Inspecting the data

`make data` downloads CUAD and loads it into `data/docintel.duckdb` (tables: `contracts`, `labels`; from Part 0d also `splits`). To explore it with SQL in Jupyter, run `make nb` (see `notebooks/00_explore.ipynb`). To browse it from the terminal, use the DuckDB CLI:

```bash
brew install duckdb
duckdb data/docintel.duckdb          # SQL prompt; .quit to exit
duckdb -ui data/docintel.duckdb      # same, in a browser UI
```

Example queries:

```sql
SHOW TABLES;
DESCRIBE contracts;
SELECT * FROM contracts LIMIT 5;
SELECT category, count(*) FILTER (is_present) AS present
FROM labels GROUP BY 1 ORDER BY 2 DESC;
```

DuckDB allows one writer at a time. If another process (like `make data` or a notebook) has the file open, use `duckdb -readonly data/docintel.duckdb`. `make data` needs the file alone, so close notebook connections first.
