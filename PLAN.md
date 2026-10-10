# Document Intelligence Pipeline — Plan

## Context
Learning project + portfolio piece. Takes messy contract PDFs → returns clean, cited, validated JSON. Built in phases; each phase ends with a measurable result + user explaining it back.
Goal: User can explain every design choice + trade-off and reproduce it, not vibe-coded.

**The product (end state):** upload a contract + type a request ("parties, renewal term, any non-compete?") → JSON with each answer + exact quote from contract + needs-review flag.

**4 questions the project must answer (hiring manager):**
1. Which documents did we choose, and why?
2. OCR-style vs multimodal parsing — quality vs cost?
3. Which fields did the model handle well / badly, and why?
4. How did we handle schema validation (what broke, what we caught, did retries help)?

## Decisions
| Area | Choice |
|---|---|
| Data | CUAD v1 (510 contracts, 41 categories, lawyer-labelled spans) |
| Scope | 12 fields, 3 per group (final pick in Phase 0) |
| LLM | OpenRouter, open-weight Qwen (Qwen3 text for extraction, Qwen3-VL for multimodal parse); `response_format: json_schema` + `require_parameters: true` |
| Validation | Pydantic (always — provider schema enforcement not guaranteed) |
| Parsers | pypdf (naive, free) vs Docling (layout, local, free) vs Qwen3-VL (page images, paid). LlamaParse dropped (paid) |
| Store | DuckDB (runs, predictions, scores, cost, latency) |
| Tracing | Arize Phoenix, local |
| Serve | FastAPI → Docker → GCP Cloud Run |
| Tooling | Python 3.12, uv, pytest, ruff, Jupyter |
| Time | No estimates. Phase done when its "Done when" is met |

## Ownership rule
- **User owns the core (the "brain"):** schema, prompts, scoring, validation/citation/retry logic, experiment design, router rules, field planner, analysis, write-up.
- **Claude owns infra (the "plumbing"):** setup, data loading, LLM client, DuckDB, runners, parser wrappers, scan degrader, FastAPI, Docker, Cloud Run, Phoenix wiring, charts.
- User can ask Claude for help on core tasks anytime — rule: Claude explains/hints, user types the code.
- Claude's code must be small, commented, and explained after each task.

## Candidate 12 fields (confirm in Phase 0)
| Group | Fields | Answer shape |
|---|---|---|
| Basic facts | Parties, Agreement Date, Governing Law | short value |
| Yes/no + quote | Non-Compete, Change of Control, Anti-Assignment | bool + span |
| Numbers/terms | Renewal Term, Notice Period to Terminate Renewal, Cap on Liability | duration/amount + span |
| License/IP | License Grant, IP Ownership Assignment, Non-Transferable License | long legal span |

## Repo layout (target)
```
src/docintel/
  data/      loader, splits            (Claude)
  llm/       OpenRouter client, cost   (Claude)
  store/     DuckDB                    (Claude)
  schema/    Pydantic field models     (User)
  extract/   prompt + extractor        (User)
  validate/  validators, citation, retry (User)
  score/     precision/recall          (User)
  parse/     parser wrappers           (Claude) + degrader (Claude)
  route/     router rules              (User)
  planner/   prompt → fields           (User)
  api/       FastAPI                   (Claude)
notebooks/   exploration + analysis
tests/
PLAN.md  EXPERIMENTS.md  README.md
```

## Experiment discipline (applies to every phase)
- Every run → entry in `EXPERIMENTS.md`: **ID, question/hypothesis, data (which split, N docs), setup (model, parser, prompt version), results (P/R table, cost, latency), conclusion, next step.**
- Splits fixed in Phase 0: **dev** (look at, tune on) / **test** (only for final numbers). Never tune on test.
- Every run tagged with a `run_id` in DuckDB → any number in the write-up traceable to a run.
- Change one thing at a time vs a baseline.

---

## Phase 0 — Setup + understand the data
**Done when:** CUAD loaded in DuckDB, 12 fields chosen, doc subset + dev/test split fixed, data card written.

**User**
- Explore CUAD in notebook: contract types, page counts, how often each category is present/absent, span lengths.
- Choose 12 fields + doc subset (~100), justify (coverage of groups, presence rates, contract types).
- Define dev/test split (stratified by contract type).
- Write `EXPERIMENTS.md` entry E0: data card + choices + why.

**Claude — prompts**
> **P0.1 Setup:** "Set up a Python 3.12 project with uv in this repo: package `src/docintel`, pytest, ruff, jupyter, python-dotenv, pydantic, duckdb, openai SDK. Add `.env.example` with OPENROUTER_API_KEY. Add a Makefile/`justfile` with `test`, `lint`, `nb`. Explain every file you created in 2 lines each, as if I'm a JS dev (compare to npm/package.json where useful)."

> **P0.2 Data loader:** "Write `src/docintel/data/` to download CUAD v1 (PDFs, full-text .txt, CUAD_v1.json, master_clauses.csv) into `data/raw/` (gitignored), and load into DuckDB tables: `contracts(doc_id, title, contract_type, n_pages, n_chars, txt_path, pdf_path)` and `labels(doc_id, category, span_text, start_char, end_char, is_present)`. Add tests on a tiny fixture. Then walk me through the CUAD JSON format with one real example."

> **P0.3 Exploration starter:** "Create `notebooks/00_explore.ipynb` with empty, titled cells + DuckDB connection only — I will write the queries. List 8 questions I should answer about the data, without answering them."

> **P0.4 Split helper:** "After I decide the split rules, implement `make_splits(seed, rules)` writing a `splits(doc_id, split)` table. Deterministic, tested."

**Learning checkpoint:** explain to Claude: what a CUAD label is, why these 12 fields, why dev/test split, what "absent" labels mean for scoring.

---

## Phase 1 — Baseline extraction on clean text
**Why clean text first:** isolates extraction errors from parsing errors.
**Done when:** per-field + per-group P/R table on dev set with cost/latency, logged as E1.

**User**
- Pydantic schema for 12 fields: each field = `value`, `quote` (verbatim), `found: bool`.
- Extraction prompt v1 (system + user), versioned.
- Scoring rules per field type: e.g. normalized exact match for dates/law; span overlap (token Jaccard ≥ threshold) for quotes; presence for yes/no. Define TP/FP/FN incl. "absent" cases. Write tests with hand-made examples.
- Pick Qwen text model from OpenRouter (must support structured_outputs). Run on dev, analyze, write E1.

**Claude — prompts**
> **P1.1 LLM client:** "Write `src/docintel/llm/` — a thin OpenRouter client using the openai SDK (base_url openrouter) that takes messages + a Pydantic model, sends `response_format` json_schema with `require_parameters: true`, returns (raw_text, parsed_or_error, usage, cost_usd, latency_ms). Retries only on network/429. Log every call to DuckDB `llm_calls`. Don't parse/validate beyond returning the raw — validation is my job. Explain how json_schema gets generated from Pydantic."

> **P1.2 Batch runner:** "Write `src/docintel/run.py` CLI: `run --split dev --parser cuad_txt --model X --prompt-version v1` → for each doc calls my `extract(text, model)` function (stub it, don't implement), stores predictions in DuckDB `predictions(run_id, doc_id, field, value, quote, found, ...)`, then calls my `score(run_id)` (stub). Concurrency limit + resume if interrupted."

> **P1.3 Results view:** "Write a function + notebook cell that renders the P/R table per field and per group for a run_id, plus total cost and p50/p95 latency. Make a bar chart per field."

**Learning checkpoint:** explain precision vs recall using a real FP and FN from your run; why your scoring threshold; which fields are weakest and a hypothesis why.

---

## Phase 2 — Trust layer (the agentic part)
**Done when:** before/after comparison vs E1: validation failure rate, hallucinated quotes caught, retry lift, needs-review rate. Logged E2.x.

**User**
- Pydantic validators (date sanity, expiration > start, enums, non-empty quote when found).
- Citation check: quote must appear in source text (normalized/fuzzy), else fail.
- Self-correction loop: on failure, send errors back to model, max 2 retries. Record attempts.
- Needs-review flag rules (failed after retries, low agreement, etc.).
- Experiments: E2.1 validation only, E2.2 + citation check, E2.3 + retry loop. One change at a time.

**Claude — prompts**
> **P2.1 Test harness:** "Create pytest fixtures with fake model responses (valid, malformed JSON, wrong types, hallucinated quote, missing field) so I can unit-test my validators and retry loop without calling the API. Don't write the validators."

> **P2.2 Attempt logging:** "Extend DuckDB schema + runner to record each extraction attempt (attempt_no, errors, fixed?) so I can compute retry lift. Add a query helper `retry_stats(run_id)`."

**Learning checkpoint:** explain why this is "agentic" vs a pipeline; what failed most; whether retries were worth the extra cost; why lawyers care more about recall on some fields.

---

## Phase 3 — Parser comparison (OCR-style vs multimodal)
**Done when:** quality-vs-cost chart for 3 parsers × (clean PDFs, degraded scans), per field group. Logged E3.x.

**User**
- Design experiment: which docs, how many degraded, what metric decides "better", what cost counts (parse + extraction tokens).
- Run each parser end-to-end through Phase 2 pipeline on dev.
- Analysis: where did multimodal win/lose and why (look at actual pages).

**Claude — prompts**
> **P3.1 Parser wrappers:** "Write `src/docintel/parse/` with a common interface `parse(pdf_path) -> ParsedDoc(text, pages, cost_usd, latency_ms, parser_name)` for: pypdf, Docling (local), and Qwen3-VL via OpenRouter (render pages to images, transcribe page-by-page, concatenate). Cache outputs on disk keyed by (parser, doc_id). Explain the trade-offs each one makes."

> **P3.2 Scan degrader:** "Write a script that turns a PDF into a 'fake scan' image-only PDF: rasterize, slight rotation, noise, blur, lower DPI. Parameters configurable, seeded. Show me before/after of one page."

> **P3.3 Parse-quality metric:** "Add a function measuring parse quality vs CUAD's .txt (character error rate) so we separate parse quality from extraction quality."

> **P3.4 Charts:** "Plot quality (F1) vs cost per doc for each parser × condition; and per-group F1 heatmap."

**Learning checkpoint:** explain the trade-off in one sentence with numbers; when you'd pay for multimodal; why CER and F1 can disagree.

---

## Phase 4 — Router (conditional)
**Only if Phase 3 shows multimodal wins on an identifiable subset.** Otherwise E4 = "router not justified" + evidence — valid result.
**Done when:** router vs always-cheap vs always-multimodal on **test** split, quality + cost. Logged E4.

**User**
- Write routing rules from dev evidence (e.g. pypdf text empty/garbled ratio, chars per page, CER proxy).
- Run all 3 strategies on test. Compare.

**Claude — prompts**
> **P4.1 Signals:** "Compute candidate cheap routing signals per doc (chars/page, non-alpha ratio, dictionary-word ratio from pypdf output, image-only page count) into a DuckDB table. Don't pick thresholds — I will."

**Learning checkpoint:** explain why rules were designed on dev and tested on test (overfitting), and the cost saved vs quality lost.

---

## Phase 5 — Service: prompt → fields → cited JSON
**Done when:** live Cloud Run URL; upload PDF + text request → cited JSON with needs_review flags; traces visible in Phoenix; planner eval logged E5.

**User**
- Field planner: map free-text request → known fields (catalog of 12) + flag unknown. Build schema dynamically from selected Pydantic sub-models.
- Planner eval: ~30 hand-written requests with expected fields → precision/recall of planner.
- Decide behavior for unknown fields (refuse vs best-effort unscored).

**Claude — prompts**
> **P5.1 API:** "Write FastAPI app `src/docintel/api/`: `POST /extract` (multipart PDF + `request` text) → calls `plan_fields`, parse (router or default), extract+validate pipeline → returns JSON; `GET /health`. Pydantic response models, size limits, timeouts. Explain each part comparing to Express."

> **P5.2 Phoenix:** "Wire Arize Phoenix locally with OpenInference/OpenTelemetry so each request shows spans: plan → parse → extract attempts → validate. Show me how to read a trace."

> **P5.3 Docker:** "Write a Dockerfile (multi-stage, slim, uv) + .dockerignore. Decide whether Docling ships in the image (size/memory) based on Phase 3/4 results; explain the choice."

> **P5.4 Cloud Run:** "Walk me step-by-step through creating a GCP account/project, enabling Artifact Registry + Cloud Run, storing OPENROUTER_API_KEY in Secret Manager, building + deploying. Give commands, I'll run them. Set memory/CPU/concurrency/min-instances=0 and explain cost implications."

**Learning checkpoint:** demo the live URL end-to-end and narrate each trace span.

---

## Phase 6 — Write-up
**Done when:** README answers the 4 hiring questions with numbers traceable to run_ids; user passes a mock interview.

**User**
- Write README narrative: problem, data choice, architecture, results, trade-offs, failures, what's next.

**Claude — prompts**
> **P6.1 Charts/tables:** "Generate final figures from DuckDB for the README (per-field P/R, parser quality vs cost, retry lift, router comparison). Each figure cites its run_id."

> **P6.2 Architecture diagram:** "Draw a mermaid diagram of the final system."

> **P6.3 Mock interview:** "Act as a hiring manager. Ask me 10 hard questions about this project one at a time; don't help; grade answers at the end with gaps to study."

---

## Verification (overall)
- `pytest` green each phase (scoring, validators, retry, planner have unit tests).
- Every number in README traceable to `run_id` in DuckDB + entry in `EXPERIMENTS.md`.
- Reproducibility: fresh clone → `uv sync` → download data → `run --split test ...` reproduces final table.
- Live: `curl -F pdf=@sample.pdf -F request="parties and renewal term" $URL/extract` returns cited JSON.

## First action after approval
Copy this plan to repo `PLAN.md` + create `EXPERIMENTS.md` template (entry format above). Then Phase 0 starts with P0.1.
