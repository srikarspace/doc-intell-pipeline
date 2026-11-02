# Experiments Log

Every run gets an entry. Numbers must trace to a `run_id` in DuckDB.
Rules: tune on **dev** only; **test** is for final numbers. Change one thing at a time vs a baseline.

## Entry template

### E<n> — <short title>
- **Date:**
- **run_id(s):**
- **Question / hypothesis:**
- **Data:** split (dev/test), N docs, which fields, clean vs degraded
- **Setup:** model, parser, prompt version, validation/retry settings
- **Results:** P/R/F1 per field + per group, cost (total, per doc), latency p50/p95
- **Conclusion:**
- **Next step:**

---

## E0 — Data card + choices
- **Date:**
- **Contracts chosen (N, how sampled, why):**
- **12 fields (per group) + why:**
- **Presence rates per field:**
- **Dev/test split rule + sizes:**
- **Known limitations of the data:**

## E1: baseline extraction on clean text
- **Date:** 2026-11-01
- **run_id(s):** 20261101-192153 (pilots: 20261101-155906 with 3 docs, 20261101-191023 with
  10 docs)
- **Question / hypothesis:** How well does Qwen3-235B with prompt v1 find the 12 fields on clean
  CUAD text? Which fields are weak?
- **Data:** dev, 52 contracts, 12 fields, CUAD .txt (clean)
- **Setup:** qwen/qwen3-235b-a22b-2507, parser cuad_txt, prompt v1, temperature 0, no validation
  retries. Bad answers scored as: 12 empty "not found" fields (`ok=false`), so each field with
  a gold answer counts as a miss (FN).
- **Results:** 52 calls, 0 failed, 0 bad answers, 624 prediction rows. Cost $0.090 (estimate
  $0.087). Tokens: 555,804 in, 40,208 out (about 770 out per doc; the estimate used 1000).
  Latency p50 63.1 s, p95 106.3 s. Totals: TP 238, FP 124, FN 75. P/R per field and per
  group: see 1c3.
- **Conclusion:** (1c3)
- **Next step:** (1c3)
