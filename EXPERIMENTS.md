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
- **Date:**
- **run_id(s):** 20261101-192153 (pilot: <pilot run_id>)
- **Question / hypothesis:** How well does Qwen3-235B with prompt v1 find the 12 fields on clean
  CUAD text? Which fields are weak?
- **Data:** dev, 52 contracts, 12 fields, CUAD .txt (clean)
- **Setup:** qwen/qwen3-235b-a22b-2507, parser cuad_txt, prompt v1, temperature 0, no validation
  retries. Bad answers scored as: <your 1c Step 3 decision>
- **Results:** cost 0.09 (estimate 0.086), p50 63.1, p95 106.3, bad answers 0. P/R per field
  and per group: see 1c3.
- **Conclusion:** (1c3)
- **Next step:** (1c3)
