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
Docs follow the style of the testdriven.io FastAPI CRUD tutorial
(https://testdriven.io/blog/fastapi-crud/): objectives first, the project tree as it grows, code
added one piece at a time with the file named before each block, "Here, we..." explanations, and
a runnable checkpoint after every step. No TDD for now: tests stay small and guard invariants;
pipeline quality is measured with evals. TDD comes back after the 4 projects.

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
file, you probe gaps. Never commit. End each doc's Conclusion with which checklist items in
../PLAN.md this part covers.

Who I am. A full-stack JavaScript engineer (Node, Express, React, npm). Newer to Python. Not a
native English speaker. Define any Python, data, ML or LLM term the first time it shows up. JS
analogies help (npm, Express, lodash, Promise).

Simple English (most important style rule). Write as if explaining to a smart 15-year-old whose
first language is not English. learn/phase-0b.md is the reference for the level.
- Short sentences: one idea each, about 15 words. Split any sentence with "and", "which" or ";"
  doing two jobs.
- Common words. Not "flatten", "payoff", "swallow", "wire together", "by construction",
  "idempotent", "invariant" (unless defined). No idioms, no phrasal verbs that mean something
  else ("fall back" -> "use the backup plan").
- Start each doc with a "Words used in this part" list: every key term in one plain line plus a
  tiny example.
- Explain code as numbered steps of what happens, in order. Show a small concrete example (real
  input -> real output) before the general rule.
- Prefer lists over paragraphs. Paragraphs at most 3 short sentences.
- Say "guess" instead of "predict". Avoid "vs", "e.g.", "i.e.", "x" for "times" in prose.

Style: the testdriven.io FastAPI CRUD tutorial. Objectives up front ("By the end of this part
you should be able to:"). Show the project tree after setup (mkdir/touch commands, then "You
should now have:") and again when files are added. Build each file one piece at a time: name the
file before every block ("Put this in `path`:", "Add to the bottom of `path`:", "Update the
imports at the top of `path`:"), then explain it right after ("Here, we..." plus a short
numbered list when there are several moves). After every step, a checkpoint: the exact command
with a `$` prompt and its real output, run on real data where possible. Put the complete final
version of each file that was built in pieces inside a collapsed <details> block. Always wrap
file names in backticks (markdown eats __init__ otherwise).

No TDD. Code first, checked by checkpoints. One small test file per part, written last, for the
invariants that must never silently break. Quality of the pipeline is measured with evals.

Keep it focused. About 700 visible lines at most (collapsed <details> full-file references do
not count). Simple English comes first: if it cannot fit, split it into lettered parts rather
than make the English denser. Say what we add, why the pipeline
needs it, and what it changes in the bigger picture. Skip history and API trivia.

Pull out the one idea. Every doc has a "Remember this" box holding the single most important
idea of the part, in two to four sentences plus a one-line hook I can repeat from memory.

Explain design before code. Every doc has a "Design decisions" section: each table, schema,
interface or algorithm choice, why it looks this way, and the main alternative in one line.

My decisions stay mine. Where the plan marks a step as a user decision (fields, schema,
prompts, scoring rules, split rules, planner behaviour), first lay out the options and the
evidence to look at, ask me to decide and write it down, then give a reference version inside a
<details> block so I can compare after.

Experiments. Any part that runs the pipeline on data has an Experiment section: the exact
command, the run_id it produces, the table I should expect (shape, not numbers), and the
EXPERIMENTS.md entry to fill in. Tune on dev only; test is for final numbers.

Python lives in the companion. Never explain syntax inline in learn/phase-N.md. Put one italic
link line after a code block that needs it, pointing at an anchor in learn/py/phase-N.md.

Prose. No em dashes. Sentence case headings. Plain words. No time estimates. Never write my
name; I am "the user". Keys are written as sk-or-v1-... .
```

Each part's prompt below is the delta that follows the contract.

---

## The learn/phase-N.md template

```markdown
# Phase N: <title>

One or two lines: what you build in this part and how (piece by piece, checkpoint after each).

## Words used in this part
Every key term of the part, one plain line each plus a tiny example. Read before anything else.

## Objectives
"By the end of this part you should be able to:" then 4 or 5 numbered, checkable skills.

## Dependencies
New libraries (with what each is for) and anything the part assumes already exists.

## The big picture
Five to ten lines. What the pipeline could do before this part, what it can do after, and which
later parts depend on it.

## Remember this
> The single most important idea in two to four sentences, then a bold one-line hook.

## Why
Two to four short paragraphs, bold lead-in each. Only the reasons that shape the code.

## Design decisions
One bullet per choice: what we picked, why, the main alternative and why not.

## Worked example
Two or three predict-then-reveal rounds (<details> blocks) on real CUAD data, only the cases
that cause real bugs or real surprises.

## Project setup
Commands that create the files (mkdir/touch), then "You should now have:" and the tree.

## Step 1: <what this step makes work>
**Why.** One sentence tied to the product.
"Put this in `path`:" / "Add to the bottom of `path`:" / "Update the imports ..." + block.
"Here, we..." explanation. User decision steps: options, decide, then a <details> reference.
Checkpoint: `$ command` and its real output. Make sure it matches before moving on.

## Step 2 ... Step N
The last step is the small test file for this part's invariants. Then "Your project structure
should now look like this:" with the tree, and the full built-up files in <details>.

## Break it on purpose
One or two deliberate failures: what to change, what to predict, the real error output.

## Experiment
Only for parts that run on data. Command, run_id, expected table shape, EXPERIMENTS.md entry.

## Gotchas
Three or four bullets.

## Explain back, then commit
The gate, then the exact git add/commit commands.

## Conclusion
Two or three lines on what now exists. "Go back through the objectives." Two questions to check
understanding. "Looking for more challenges?" with two or three optional extensions. Checklist
items covered (from ../PLAN.md).
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
| Time | 3 weeks, one part per working day (see Roadmap). No time estimates inside docs |

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
  domain/    schema/ (field models) · extract/ · validate/ · parse/ (+ scan degrader) · planner/
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

## Roadmap (3 weeks)

The project is done at the end of week 3 (weeks 1 to 3 of `../PLAN.md`). One part per working
day. Parts were merged to fit; the router is cut (README future work).

| Week | Part | Topic | What it builds | Status |
|---|---|---|---|---|
| 1 | 0a | setup | uv project, deps, Makefile, ruff, pytest (read and run) | done |
| 1 | 0b | data loader | CUAD download, `contracts` + `labels` tables, invariant test | done |
| 1 | 0c | explore | notebook `00_explore.ipynb`: 6 questions, 6 findings (no `src/` code) | doc ready |
| 1 | 0d | fields, subset, split | choose 12 fields + doc subset + split rules, `make_splits`, test, E0 | doc ready |
| 1 | 1a | schema + LLM client | Pydantic field models, OpenRouter client with json_schema, `llm_calls` log | planned |
| 1 | 1b | extract + score | prompt v1, `extract()`, scoring rules, `evals/scorers.py` | planned |
| 2 | 1c | batch run | runner with run_id, concurrency, resume; P/R table; E1 | planned |
| 2 | 2a | validators + citations | Pydantic validators, quote-in-source check, needs-review rules | planned |
| 2 | 2b | retry + trust experiments | self-correction loop, attempt log, E2.1 to E2.3 | planned |
| 2 | 3a | parsers | common `parse()` interface, pypdf, Docling, Qwen3-VL (~10 docs), disk cache | planned |
| 2 | 3b | scans + parser experiment | scan degrader, CER, quality vs cost per parser, E3 | planned |
| 3 | 4a | planner + API | request -> fields, FastAPI `/v1/extract` + `/health`, key, rate limit, spend cap | planned |
| 3 | 4b | observability | Phoenix spans, JSON logs, Postgres request/cost log | planned |
| 3 | 4c | ship | Docker, Cloud Run, GitHub Actions with eval gate on `evals/mini/` | planned |
| 3 | 4d | UI | Next.js upload + cited JSON view on Vercel (Claude scaffolds) | planned |
| 3 | 5 | write-up + interview | figures with run_ids, README narrative, mock interview | planned |

---

## Phase 0: setup and understand the data

**Done when:** CUAD loaded in DuckDB, 12 fields chosen, doc subset and dev/test split fixed, data
card written (E0).

**Learning checkpoint:** explain what a CUAD label is, why these 12 fields, why a dev/test split,
and what "absent" labels mean for scoring.

> **0a Setup (read and run):** "The setup is already built (pyproject.toml, uv.lock,
> .python-version, Makefile, .env.example, src/docintel/__init__.py, tests/test_smoke.py). Write
> the doc as a reading-and-running part: what uv is (vs npm), virtual environments (vs
> node_modules), pyproject.toml line by line, ruff and pytest config, the Makefile targets,
> `uv run`. Each step: read the file, predict, run the checkpoint. Test: `make test` and
> `make lint` green."

> **0b Data loader:** "Have me delete src/docintel/data/, src/docintel/store/ and
> tests/test_data_load.py first, then scaffold evals/__init__.py, evals/store.py,
> evals/datasets.py. Teach: the CUAD zip layout and the SQuAD-style JSON (predict-then-reveal on
> answer_start slicing and on an absent label); why DuckDB; why two tables; why `labels` is long;
> why absent labels are rows; why offsets are kept; the messy-filename problem. Build datasets.py
> one function at a time with a real-data checkpoint after each. Last step: a small
> tests/test_data_load.py on a 2-contract fake CUAD. Test: `make data` prints 510 contracts,
> 28031 label rows; zero NULL pdf_path; `make test` green."

> **0c Explore:** "I create notebooks/00_explore.ipynb (DuckDB connection cell first) and answer
> 6 questions: contracts per type, contract length vs context window, presence rate per
> category, spans per contract, span length, related-contract families. For each: why it matters
> later, a query on a narrow slice with predict-then-run, then the full query and a Finding cell.
> Teach the SQL as it appears (GROUP BY, FILTER, CTEs, JOIN USING, quantiles) with lodash
> analogies in the companion."

> **0d Fields, subset, split (user decisions):** "From my 0c findings, choose the 12 fields and
> the ~100-doc subset (options + evidence, I decide, reference in `<details>`), and the split
> rules (stratify by type, related contracts on one side). Implement `make_splits(seed)` in
> evals/datasets.py writing `splits(doc_id, split)`, deterministic, with a small test. Finish
> with E0 in EXPERIMENTS.md."

---

## Phase 1: baseline extraction on clean text

**Why clean text first:** it isolates extraction errors from parsing errors.
**Done when:** per-field and per-group P/R table on dev with cost and latency, logged as E1.

**Learning checkpoint:** explain precision vs recall using a real FP and FN from the run; why the
scoring threshold; which fields are weakest and a hypothesis why.

> **1a Schema + LLM client:** "Schema is a user decision: each field = `value`, `quote`
> (verbatim), `found: bool`; options for list fields (Parties) and typed values (dates, bools).
> Then `src/docintel/core/llm.py` (+ `core/config.py`): a thin OpenRouter client on the openai
> SDK that takes messages + a Pydantic model, sends `response_format` json_schema with
> `require_parameters: true`, returns (raw_text, parsed_or_error, usage, cost_usd, latency_ms),
> retries only on network/429, logs every call to DuckDB `llm_calls`. Show how the json_schema is
> generated from the Pydantic model (compare to zod's toJSONSchema). Checkpoint: one live call on
> a tiny prompt."

> **1b Extract + score (user decisions):** "Prompt v1 is a user decision (system + user,
> versioned in files). Build `extract(text, model)` in domain/extract/ and run it on one dev
> contract; predict-then-reveal on a present field, an absent field and a list field. Then the
> scoring rules (user decisions): normalized exact match for dates/law, span overlap (token
> Jaccard >= threshold) for quotes, presence for yes/no; TP/FP/FN including absent cases.
> `evals/scorers.py`, checked on that one contract's real output, plus a small test of the rules."

> **1c Batch run:** "`src/docintel/evals/runner.py` CLI: `run --split dev --parser cuad_txt
> --model X --prompt-version v1`, stores `predictions(run_id, doc_id, field, value, quote, found,
> ...)`, calls `score(run_id)`, concurrency limit, resume if interrupted. Estimate cost before
> running. Results: P/R per field and per group, total cost, p50/p95 latency, bar chart per field.
> Experiment: E1."

---

## Phase 2: trust layer (the agentic part)

**Done when:** before/after vs E1: validation failure rate, hallucinated quotes caught, retry
lift, needs-review rate. Logged as E2.x.

**Learning checkpoint:** explain why this is "agentic" vs a pipeline; what failed most; whether
retries were worth the extra cost; why lawyers care more about recall on some fields.

> **2a Validators + citations (user decisions):** "Validator rules (date sanity, expiration
> after start, enums, non-empty quote when found) and quote matching rules (normalized/fuzzy) are
> user decisions. Worked examples of real near-misses from E1 output. Needs-review rules. Small
> test with fake model responses (valid, malformed, wrong types, hallucinated quote)."

> **2b Retry + trust experiments:** "On failure, send the errors back to the model, max 2
> retries; record each attempt (attempt_no, errors, fixed?) in DuckDB. Then E2.1 validation only,
> E2.2 + citation check, E2.3 + retry loop. One change at a time."

---

## Phase 3: parser comparison (OCR-style vs multimodal)

**Done when:** quality vs cost per parser and condition on dev, logged as E3.

**Learning checkpoint:** explain the trade-off in one sentence with numbers; when you would pay
for multimodal; why CER and F1 can disagree.

> **3a Parsers:** "`src/docintel/domain/parse/` with a common interface `parse(pdf_path) ->
> ParsedDoc(text, pages, cost_usd, latency_ms, parser_name)` for pypdf, Docling (local) and
> Qwen3-VL via OpenRouter (page images, ~10 dev docs, capped pages, cost estimated first). Disk
> cache keyed by (parser, doc_id). Repo-reading practice: trace Docling's conversion pipeline
> before wrapping it."

> **3b Scans + parser experiment (user decisions):** "A seeded scan degrader that turns ~10 dev
> PDFs into image-only fake scans (rasterize, rotate, noise, blur, lower DPI), with a before/after
> of one page. CER vs CUAD's .txt. Experiment design is a user decision (docs, metric that
> decides 'better', which costs count). Run each parser through the Phase 2 pipeline on dev.
> Charts: F1 vs cost per doc per parser x condition. E3."

---

## Phase 4: service (request -> fields -> cited JSON, prod bar)

**Done when:** the prod bar in ../PLAN.md is met: public API + UI URLs; upload PDF + text request
-> cited JSON with needs_review flags; auth, rate limit, spend cap; traces and cost log; CI eval
gate green. This phase builds the reusable skeleton for `agents/_template/`.

**Learning checkpoint:** demo the live URL end to end, narrate each trace span, and answer: how
would you deploy, monitor, secure, roll back and scale this to 100x?

> **4a Planner + API:** "Planner: map a free-text request to known fields (the 12), flag unknown
> ones (behaviour is a user decision), build the schema from the selected Pydantic sub-models;
> eval on ~15 hand-written requests (E4). Then FastAPI in `src/docintel/api/`: `POST /v1/extract`
> (multipart PDF + `request` text) -> plan, parse, extract + validate -> JSON; `GET /health`.
> Pydantic response models, size limits, timeouts, API-key auth, per-IP rate limit, daily spend
> cap. Compare each piece to Express."

> **4b Observability:** "Phoenix with OpenInference/OpenTelemetry so each request shows spans:
> plan, parse, extract attempts, validate. Structured JSON logs. Request/cost log in Postgres
> (Neon free) with an alembic migration; a p50/p95/error/cost query. How to read a trace."

> **4c Ship:** "Multi-stage slim Dockerfile with uv + .dockerignore (Docling in the image or not,
> from Phase 3 results). GCP project, Artifact Registry, Cloud Run, Secret Manager; memory, CPU,
> concurrency, min-instances=0 and their cost. OpenRouter key with a credit limit. GitHub
> Actions: ruff, pytest, eval regression gate on `evals/mini/` (threshold is a user decision),
> build and deploy on main. Rollback = redeploy the previous revision. I run every command."

> **4d UI:** "Small Next.js app in `web/`: upload PDF, type request, show JSON with each quote
> highlighted and needs_review badges. Deploy on Vercel; API key held server-side. Claude may
> scaffold; the user reviews and explains it back."

---

## Phase 5: write-up

**Done when:** README answers the 4 hiring questions with numbers traceable to run_ids; the user
passes a mock interview.

> **5 Write-up + interview:** "Final figures from DuckDB (per-field P/R, parser quality vs cost,
> retry lift), each citing its run_id, and a mermaid diagram. Guide me through the README
> narrative (problem, data choice, architecture, results, trade-offs, failures, next, including
> the router as future work). I write it. Then act as a hiring manager: 10 hard questions one at
> a time (deploy, monitoring, security, scaling), no help, grade at the end with gaps to study.
> Then tick checklist items in ../PLAN.md."

---

## Verification (overall)

- `make test` green after every part.
- Every number in the README traces to a `run_id` in DuckDB and an entry in `EXPERIMENTS.md`.
- Reproducibility: fresh clone -> `uv sync` -> `make data` -> `run --split test ...` reproduces
  the final table.
- Live: `curl -F pdf=@sample.pdf -F request="parties and renewal term" $URL/v1/extract` (with API
  key) returns cited JSON.
