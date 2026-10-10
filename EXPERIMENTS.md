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
