# Document Intelligence Pipeline: plan

## Context

Learning project and portfolio piece. It takes messy contract PDFs and returns clean, cited,
validated JSON. Built one phase at a time; each phase ends with a measurable result and with the
user explaining it back.

Goal: the user can explain every design choice and trade-off and reproduce it. Not vibe-coded.

**The product (end state):** upload a contract, type a request ("parties, renewal term, any
non-compete?"), get JSON with each answer, the exact quote from the contract, and a needs-review
flag.

**4 questions the project must answer (hiring manager):**
1. Which documents did we choose, and why?
2. OCR-style vs multimodal parsing: quality vs cost?
3. Which fields did the model handle well or badly, and why?
4. How did we handle schema validation (what broke, what we caught, did retries help)?

The point of each phase is that the user can say two things when it is done: what we added, and
what it changes in the bigger picture of the pipeline.

---

## How this plan is used

Tutor + AI-assisted. Follows the shared standard in `../PLAN.md` (layout, prod bar, checklist).

1. Paste the tutor contract plus the part's prompt into a fresh session. The tutor writes
   `learn/phase-N.md` and `learn/py/phase-N.md`, then stops.
2. The user drives with AI pairing. Core logic (schema, prompts, scoring, validators, parsers
   interface, planner) is drafted by the user first, at least as a skeleton; Claude then helps
   finish, debug, and writes boilerplate on request.
3. Explain-back gate: before committing, the user explains each changed file to Claude. The user
   commits; Claude never commits.

### Tutor contract (paste at the top of every phase prompt)

```
You are a tutor, not an implementer. Read PLAN.md first, then the previous part's learn/ doc.

First output learn/phase-N.md and learn/py/phase-N.md (one pair per lettered part, e.g. 1a and
1b), then stop. While I work, pair with me: I draft core logic first; you suggest, debug, and
write boilerplate when I ask. Before I commit, run the explain-back gate: I explain each changed
file, you probe gaps. Never commit. End each doc's Recap with which checklist items in
../PLAN.md this part covers.

Who I am. A full-stack JavaScript engineer (Node, Express, React, npm). Newer to Python. Define
any Python, data, ML or LLM term the first time it shows up. JS analogies help (npm, Express,
lodash, Promise). Short sentences, one idea each.

Keep it small and concise. About an hour, 200 to 450 lines, mostly code. If it cannot fit, split
it into lettered parts. Say what we add, why the pipeline needs it, and what it changes in the
bigger picture. Skip history and API trivia that does not change the code I type.

Pull out the one idea. Every doc has a "Remember this" box holding the single most important
idea of the part, in two to four sentences plus a one-line hook I can repeat from memory.

Explain design before code. Every doc has a "Design decisions" section: each table, schema,
interface or algorithm choice, why it looks this way, and the main alternative in one line.

My decisions stay mine. Where the plan marks a step as a user decision (fields, schema,
prompts, scoring rules, split rules, router thresholds, planner behaviour), first lay out the
options and the evidence to look at, ask me to decide and write it down, then give a reference
version inside a <details> block so I can compare after.

Code blocks are whole files. When a part changes a file an earlier part wrote, print the
entire new file so I can paste it over the old one. Every file ends up with a test I run.

Experiments. Any part that runs the pipeline on data has an Experiment section: the exact
command, the run_id it produces, the table I should expect (shape, not numbers), and the
EXPERIMENTS.md entry to fill in. Tune on dev only; test is for final numbers.

Python lives in the companion. Never explain syntax inline in learn/phase-N.md. Put one italic
link line after a code block that needs it, pointing at an anchor in learn/py/phase-N.md.

Prose. No em dashes. Sentence case headings. Plain words. Never write my name; I am "the user".
Keys are written as sk-or-v1-... .
```

Each part's prompt below is the delta that follows the contract.

---

## The learn/phase-N.md template

```markdown
# Phase N: <title>

About an hour. <n> files.

## The big picture
Five to ten lines. What the pipeline could do before this part, what it can do after, and which
later phases depend on what we add today. One example command if it helps.

## Files
| File | Job |
One row per file created or changed, one-line job each.

## Remember this
> The single most important idea in two to four sentences, then a bold one-line hook.

## Why
Three or four short paragraphs, bold lead-in each. Only the reasons that shape the code.

## Design decisions
One bullet per choice: what we picked, why, the main alternative and why not.

## Worked example
Two or three predict-then-reveal rounds (<details> blocks) on real CUAD data, only the cases
that cause real bugs or real surprises.

## Your task
Numbered steps. Each opens with one bold "Why." sentence tied to the product, then the full file,
then one to three lines on what to notice. User decision steps use options, then decide, then a
<details> reference. Last step is the commit.

## Test
The command and its expected output. One deliberate failure, with what each wrong outcome means.

## Experiment
Only for parts that run on data. Command, run_id, expected table shape, EXPERIMENTS.md entry.

## Gotchas
Three or four bullets.

## Recap
Three lines on what now exists. Two questions to check understanding. Checklist items covered
(from ../PLAN.md), so the user can tick them.
```

## The learn/py/phase-N.md template

```markdown
# Python for Phase N

One line: covers the Python this part introduces; read sideways, one section at a time.

<a id="py-1"></a>
## PY-1. <construct, named the way I would search for it>
Two or three sentences of plain English, the JS equivalent, the real line from this repo that
uses it, and what it buys over the simpler version.
```

Rules: explicit `<a id="py-N"></a>` anchors; examples are real lines from this repo, never
`foo`/`bar`; three to eight sections, each readable in a minute; link back to earlier companions
by anchor instead of repeating them. The phase doc links in with
`*Python here: [label](./py/phase-N.md#py-3).*` right after the code block.

---

## Decisions (fixed)

| Area | Choice |
|---|---|
| Data | CUAD v1 (510 contracts, 41 categories, lawyer-labelled spans) |
| Scope | 12 fields, 3 per group (final pick in Phase 0) |
| LLM | OpenRouter, open-weight Qwen (Qwen3 text for extraction, Qwen3-VL for multimodal parse); `response_format: json_schema` + `require_parameters: true` |
| Validation | Pydantic (always; provider schema enforcement is not guaranteed) |
| Parsers | pypdf (naive, free) vs Docling (layout, local, free) vs Qwen3-VL (page images, paid) |
| Store | DuckDB offline (contracts, labels, splits, runs, predictions, scores, cost, latency); Postgres (Neon) in prod (request log, spend) |
| Tracing | Arize Phoenix (local in dev; hosted or self-hosted for prod) + JSON logs |
| Serve | FastAPI, Docker, GCP Cloud Run; Next.js UI on Vercel; GitHub Actions CI with eval gate (prod bar in ../PLAN.md) |
| Tooling | Python 3.12, uv, pytest, ruff, Jupyter, Makefile |
| Time | No estimates. A part is done when its Test passes and its "Done when" is met |

## Candidate 12 fields (confirmed in Phase 0d)

| Group | Fields | Answer shape |
|---|---|---|
| Basic facts | Parties, Agreement Date, Governing Law | short value |
| Yes/no + quote | Non-Compete, Change of Control, Anti-Assignment | bool + span |
| Numbers/terms | Renewal Term, Notice Period to Terminate Renewal, Cap on Liability | duration/amount + span |
| License/IP | License Grant, IP Ownership Assignment, Non-Transferable License | long legal span |

## Repo layout (target)

Standard layout shared by every project (see ../PLAN.md). Only `domain/` is project-specific.

```
src/docintel/
  core/      config.py (pydantic-settings) · llm.py (OpenRouter client, cost, retries) · log.py · trace.py
  domain/    schema/ (field models) · extract/ · validate/ · parse/ (+ scan degrader) · planner/ · route/ (stretch)
  evals/     store.py (DuckDB) · datasets.py (CUAD download/load, splits) · scorers.py (P/R) · runner.py (run_id)
  api/       app.py · routes.py · schemas.py · auth.py · limits.py
  db/        Postgres models + alembic migrations (prod request/spend log)
web/         Next.js UI
evals/mini/  fixed mini-set for the CI eval gate
learn/       phase docs · notebooks/ · tests/
Dockerfile · Makefile · .github/workflows/ci.yml · PLAN.md · EXPERIMENTS.md · README.md · CLAUDE.md
```

Agentic pattern: each capability (`extract`, `parse`, `plan`) is a typed function (Pydantic in,
Pydantic out) with a trace span, called by the API, the eval runner, and later as an agent tool.

## Experiment discipline (every phase)

- Every run gets an entry in `EXPERIMENTS.md`: ID, question/hypothesis, data (split, N docs),
  setup (model, parser, prompt version), results (P/R table, cost, latency), conclusion, next step.
- Splits fixed in Phase 0: **dev** (look at, tune on) and **test** (final numbers only). Never
  tune on test.
- Every run is tagged with a `run_id` in DuckDB, so any number in the write-up traces to a run.
- Change one thing at a time vs a baseline.

---

## Roadmap

| Part | Topic | What it builds | Status |
|---|---|---|---|
| 0a | setup | uv project, deps, Makefile, ruff, pytest (already built; doc explains it) | built, doc todo |
| 0b | data loader | CUAD download, `contracts` + `labels` tables, fixture tests (user re-types) | next |
| 0c | exploration | user-built notebook: the 8 data questions, predict then run | planned |
| 0d | fields + split | choose 12 fields + doc subset, `make_splits`, E0 data card | planned |
| 1a | schema + LLM client | Pydantic field models, OpenRouter client with json_schema, `llm_calls` log | planned |
| 1b | extraction | prompt v1, `extract(text, model)` on one contract | planned |
| 1c | scoring | TP/FP/FN rules per field type, unit tests | planned |
| 1d | batch run | runner with run_id, concurrency, resume; P/R table; E1 | planned |
| 2a | validators | Pydantic validators + fake-response fixtures | planned |
| 2b | citation check | quote must appear in source text | planned |
| 2c | retry loop | self-correction with errors fed back, attempt logging | planned |
| 2d | trust experiments | E2.1 to E2.3, needs-review rules | planned |
| 3a | parsers I | common `parse()` interface, pypdf, Docling, disk cache | planned |
| 3b | parsers II | Qwen3-VL page transcription (dev subset ~10 docs) | planned |
| 3c | scans + CER | scan degrader on ~10 dev docs, character error rate vs CUAD .txt | planned |
| 3d | parser experiment | quality vs cost per parser x condition, charts, E3 | planned |
| 4a | router | stretch: only if time is left after Phase 6 | stretch |
| 5a | planner | request -> fields, planner eval set | planned |
| 5b | API | FastAPI `/v1/extract` + `/health`, API key, rate limit, spend cap, timeouts | planned |
| 5c | observability | Phoenix spans + JSON logs + Postgres request/cost log | planned |
| 5d | Docker + Cloud Run | multi-stage image, GCP deploy, Secret Manager | planned |
| 5e | CI/CD | GitHub Actions: lint, test, eval gate on evals/mini, deploy on main | planned |
| 5f | UI | Next.js upload + JSON view with highlighted quotes, on Vercel | planned |
| 6a | figures | final charts and diagram, each citing a run_id | planned |
| 6b | write-up + interview | README narrative, mock interview | planned |

---

## Phase 0: setup and understand the data

**Done when:** CUAD loaded in DuckDB, 12 fields chosen, doc subset and dev/test split fixed, data
card written (E0).

**Learning checkpoint:** explain what a CUAD label is, why these 12 fields, why a dev/test split,
and what "absent" labels mean for scoring.

> **0a Setup (explain existing code):** "The setup is already built (pyproject.toml, uv.lock,
> .python-version, Makefile, .env.example, src/docintel/__init__.py, tests/test_smoke.py). Write
> the doc as a reading-and-running part instead of a typing part: what uv is (vs npm), virtual
> environments (vs node_modules), pyproject.toml line by line, ruff and pytest config, the
> Makefile targets, `uv run`. Your task = run each command and predict its output. Test:
> `make test` and `make lint` green."

> **0b Data loader (user re-types):** "Before step 1, have me delete src/docintel/data/,
> src/docintel/store/ and tests/test_data_load.py (they move to the standard layout:
> evals/store.py, evals/datasets.py; update the Makefile `data` target) (data/raw/ stays, so no re-download). Teach:
> the CUAD zip layout and the SQuAD-style JSON (one real example, predict-then-reveal on
> answer_start slicing and on an absent label); why DuckDB (embedded, analytical, like SQLite);
> why two tables; why `labels` is long (one row per span) not wide (41 columns, like
> master_clauses.csv); why absent labels are explicit rows; why offsets are kept (citations).
> Include the messy-filename problem (trailing spaces, & vs _, accents, extra suffix) as a worked
> example. Files: evals/__init__.py, evals/store.py, evals/datasets.py (download + load,
> `python -m docintel.evals.datasets`), tests/test_data_load.py with a tiny fixture. Test: `make test`, `make data`
> prints 510 contracts, 28031 label rows; zero NULL pdf_path."

> **0c Exploration (guided):** "I create notebooks/00_explore.ipynb from scratch (DuckDB
> connection cell first). The 8 data questions: per type counts, length/context window, presence
> rate per category, spans per contract, span length, span position, related-contract families,
> pypdf text layer vs .txt. For each question, why it matters for a later phase, a full query on a narrow slice with
> predict-then-run, then the full query for me to run and a prompt for what to write in the
> Finding cell. Teach the SQL as it appears (GROUP BY, FILTER, DISTINCT, CTEs, JOIN USING,
> quantiles, sampling) with lodash/JS analogies in the companion. Q8 compares the pypdf text
> layer to the CUAD .txt. Test: every Finding cell filled."

> **0d Fields + split (user decisions):** "Using my 0c findings, walk me through choosing the 12
> fields and the ~100-doc subset (options + evidence, I decide, reference in <details>). Then the
> split rules: stratify by contract type, keep related contracts (same filer/agreement family)
> on one side. Then implement `make_splits(seed, rules)` writing `splits(doc_id, split)`,
> deterministic, with tests. Finish with the E0 entry in EXPERIMENTS.md."

---

## Phase 1: baseline extraction on clean text

**Why clean text first:** it isolates extraction errors from parsing errors.
**Done when:** per-field and per-group P/R table on dev with cost and latency, logged as E1.

**Learning checkpoint:** explain precision vs recall using a real FP and FN from the run; why the
scoring threshold; which fields are weakest and a hypothesis why.

> **1a Schema + LLM client:** "Schema is a user decision: each field = `value`, `quote`
> (verbatim), `found: bool`; options for list fields (Parties) and typed values (dates, bools).
> Then `src/docintel/core/llm.py` (+ `core/config.py`): a thin OpenRouter client on the openai SDK that takes messages + a
> Pydantic model, sends `response_format` json_schema with `require_parameters: true`, returns
> (raw_text, parsed_or_error, usage, cost_usd, latency_ms), retries only on network/429, logs
> every call to DuckDB `llm_calls`. Show how the json_schema is generated from the Pydantic
> model (compare to zod's toJSONSchema). Test: one live call on a tiny prompt."

> **1b Extraction:** "Prompt v1 is a user decision (system + user, versioned in files). Build
> `extract(text, model)` and run it on one dev contract; predict-then-reveal on what the model
> returns for a present field, an absent field and a list field. Model choice: a Qwen3 text
> model on OpenRouter that supports structured outputs."

> **1c Scoring:** "Scoring rules are user decisions: normalized exact match for dates/law, span
> overlap (token Jaccard >= threshold) for quotes, presence for yes/no; TP/FP/FN including absent
> cases. Worked examples from real CUAD labels. `evals/scorers.py` + unit tests with hand-made
> examples."

> **1d Batch run:** "`src/docintel/evals/runner.py` CLI: `run --split dev --parser cuad_txt --model X
> --prompt-version v1`, stores `predictions(run_id, doc_id, field, value, quote, found, ...)`,
> calls `score(run_id)`, concurrency limit, resume if interrupted. Results view: P/R per field and
> per group, total cost, p50/p95 latency, bar chart per field. Experiment: E1."

---

## Phase 2: trust layer (the agentic part)

**Done when:** before/after vs E1: validation failure rate, hallucinated quotes caught, retry
lift, needs-review rate. Logged as E2.x.

**Learning checkpoint:** explain why this is "agentic" vs a pipeline; what failed most; whether
retries were worth the extra cost; why lawyers care more about recall on some fields.

> **2a Validators:** "pytest fixtures with fake model responses (valid, malformed JSON, wrong
> types, hallucinated quote, missing field). Validator rules are user decisions (date sanity,
> expiration after start, enums, non-empty quote when found)."

> **2b Citation check:** "Quote must appear in the source text (normalized/fuzzy match). Matching
> rules are a user decision; worked examples of near-misses from E1 output."

> **2c Retry loop:** "On failure, send the errors back to the model, max 2 retries. Record each
> attempt (attempt_no, errors, fixed?) in DuckDB; `retry_stats(run_id)`."

> **2d Trust experiments:** "Needs-review rules (user decision). Experiments E2.1 validation
> only, E2.2 + citation check, E2.3 + retry loop. One change at a time."

---

## Phase 3: parser comparison (OCR-style vs multimodal)

**Done when:** quality vs cost per parser and condition on dev, logged as E3.

**Learning checkpoint:** explain the trade-off in one sentence with numbers; when you would pay
for multimodal; why CER and F1 can disagree.

> **3a Parsers I:** "`src/docintel/domain/parse/` with a common interface `parse(pdf_path) ->
> ParsedDoc(text, pages, cost_usd, latency_ms, parser_name)` for pypdf and Docling (local). Cache
> outputs on disk keyed by (parser, doc_id). Trade-offs of each. Repo-reading practice: have me
> find and trace Docling's own conversion pipeline before wrapping it."

> **3b Parsers II:** "Qwen3-VL via OpenRouter on a dev subset (~10 docs, cap pages per doc):
> render pages to images, transcribe page by page, concatenate, track cost. Estimate cost before
> running."

> **3c Scans + CER:** "A scan degrader that turns ~10 dev PDFs into image-only 'fake scans'
> (rasterize, rotate, noise, blur, lower DPI; seeded, configurable), with a before/after of one
> page. Parse quality vs CUAD's .txt as character error rate. Without scans, multimodal never
> wins on CUAD's text-layer PDFs."

> **3d Parser experiment:** "Experiment design is a user decision (which docs, how many
> degraded, which metric decides 'better', which costs count). Run each parser end to end
> through the Phase 2 pipeline on dev. Charts: F1 vs cost per doc per parser x condition, per-group
> F1 heatmap. Analysis by looking at actual pages. E3."

---

## Phase 4: router (stretch)

**Skip unless time is left after Phase 6.** If Phase 3 shows multimodal wins on an identifiable
subset, the router is the natural next step; mention it in the README as future work otherwise.

> **4a Router:** "Compute cheap routing signals per doc (chars/page, non-alpha ratio,
> dictionary-word ratio from pypdf output, image-only page count) into DuckDB. Thresholds and
> rules are user decisions from dev evidence. Run all 3 strategies on test. E4."

---

## Phase 5: service (request -> fields -> cited JSON, prod bar)

**Done when:** the prod bar in ../PLAN.md is met: public API + UI URLs; upload PDF + text request
-> cited JSON with needs_review flags; auth, rate limit, spend cap; traces and cost log; CI eval
gate green; planner eval logged as E5. This phase builds the reusable skeleton for
`agents/_template/`.

**Learning checkpoint:** demo the live URL end to end, narrate each trace span, and answer: how
would you deploy, monitor, secure, roll back and scale this to 100x?

> **5a Planner:** "Map a free-text request to known fields (the 12) and flag unknown ones; build
> the schema dynamically from the selected Pydantic sub-models. Unknown-field behaviour is a user
> decision. Planner eval: ~30 hand-written requests with expected fields, precision/recall. E5."

> **5b API:** "FastAPI app `src/docintel/api/`: `POST /v1/extract` (multipart PDF + `request`
> text) -> plan, parse, extract + validate -> JSON; `GET /health`. Pydantic response models,
> size limits, timeouts, API-key auth, per-IP rate limit, daily spend cap. Compare each part to
> Express."

> **5c Observability:** "Phoenix with OpenInference/OpenTelemetry so each request shows spans:
> plan, parse, extract attempts, validate (hosted free tier or self-hosted so it works from Cloud
> Run). Structured JSON logs. Request/cost log in Postgres (Neon free) with an alembic migration;
> a p50/p95/error/cost query. How to read a trace."

> **5d Docker + Cloud Run:** "Multi-stage slim Dockerfile with uv + .dockerignore; whether Docling
> ships in the image (size/memory) is decided from Phase 3 results. Then GCP project, Artifact
> Registry, Cloud Run, secrets in Secret Manager, build and deploy. Memory/CPU/concurrency/
> min-instances=0 and their cost implications. OpenRouter key with a credit limit. I run every
> command."

> **5e CI/CD:** "GitHub Actions: ruff, pytest, and an eval regression gate on a fixed
> `evals/mini/` set (fails if F1 drops more than a user-chosen threshold), then build and deploy
> on main. Rollback = redeploy the previous revision."

> **5f UI:** "Small Next.js app in `web/`: upload PDF, type request, show JSON with each quote
> highlighted and needs_review badges. Deploy on Vercel; API key held server-side. Claude may
> scaffold; the user reviews and explains it back."

---

## Phase 6: write-up

**Done when:** README answers the 4 hiring questions with numbers traceable to run_ids; the user
passes a mock interview.

> **6a Figures:** "Final figures from DuckDB for the README (per-field P/R, parser quality vs
> cost, retry lift), each citing its run_id. A mermaid diagram of the final
> system."

> **6b Write-up + interview:** "Guide me through the README narrative (problem, data choice,
> architecture, results, trade-offs, failures, next). I write it. Then act as a hiring manager:
> 10 hard questions one at a time (include deploy, monitoring, security, scaling), no help, grade
> at the end with gaps to study. Then tick checklist items in ../PLAN.md and run the first weekly
> quiz."

---

## Verification (overall)

- `make test` green after every part.
- Every number in the README traces to a `run_id` in DuckDB and an entry in `EXPERIMENTS.md`.
- Reproducibility: fresh clone -> `uv sync` -> `make data` -> `run --split test ...` reproduces
  the final table.
- Live: `curl -F pdf=@sample.pdf -F request="parties and renewal term" $URL/v1/extract` (with API key) returns
  cited JSON.
