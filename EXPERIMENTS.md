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
  Latency p50 63.1 s, p95 106.3 s. Totals: TP 238, FP 124, FN 75.
  All (micro): P 0.66, R 0.76, F1 0.71. Group F1: basic facts 0.63, yes/no + quote 0.85,
  numbers/terms 0.65, license/IP 0.80. Full per-field table: `report 20261101-192153`.
- **Conclusion:** Strongest: license_grant (F1 1.00) and anti_assignment (0.99). Weakest:
  parties (0.38) and notice_period_to_terminate_renewal (0.45).
  - parties: scoring, not the model. All 32 misses have the right names, but the quote is the
    whole opening sentence and the gold spans are just the names, so Jaccard stays under the
    threshold.
  - notice_period_to_terminate_renewal: the model. 14 of 15 FPs are in contracts with no gold
    answer: it quotes the notice to end the whole agreement ("terminated at any time ... upon 60
    days' written notice"), not the notice to stop a renewal.
- **Next step:** E1.1 (other open-weight models, 1c4), then 2a (validators and citations).


## E1.1: using different models
- **Date:** 2026-11-02
- **run_id(s):** 20261102-200003 (deepseek/deepseek-v4-flash), 20261102-194826 (qwen/qwen3.8-27b),
  20261102-200841 (z-ai/glm-5.3-flash), 20261102-202705 (deepseek/deepseek-v4.1-flash-1017), against
  E1 20261101-192153. Pilots, 3 docs each, not used for results: 20261102-193610 (Qwen3.8),
  20261102-202613 (DeepSeek V4.1).
- **Question / hypothesis:** Does a newer open-weight model beat Qwen3-235B-2507 on the same
  prompt, or match it for less cost or latency?
- **Data:** dev, 52 contracts, 12 fields, CUAD .txt (clean)
- **Setup:** same as E1; only the model changes. Licenses: Qwen3.8 Apache 2.0; DeepSeek V4, DeepSeek
  V4.1 and GLM-5.3 MIT. Each model with its default reasoning and OpenRouter's provider choice.
  Keep rule (1c4 reference): F1 at least E1's minus 0.02, and cheaper or faster at p95; if several
  pass, the cheapest. Closed models (GPT, Opus) were not run: they are not open-weight, and a full
  run would cost several dollars.
- **Results:**

  | Model | P | R | F1 | TP / FP / FN | Cost | Avg out tokens | p50 | p95 | Bad |
  |---|---|---|---|---|---|---|---|---|---|
  | deepseek/deepseek-v4-flash | 0.79 | 0.82 | 0.80 | 256 / 70 / 57 | $0.204 | 8,953 | 31.0 s | 57.5 s | 0 |
  | qwen/qwen3.8-27b | 0.76 | 0.81 | 0.78 | 252 / 79 / 61 | $0.883 | 8,801 | 86.8 s | 209.8 s | 0 |
  | z-ai/glm-5.3-flash | 0.75 | 0.82 | 0.78 | 256 / 86 / 57 | $0.213 | 6,990 | 22.6 s | 89.5 s | 0 |
  | deepseek/deepseek-v4.1-flash-1017 | 0.78 | 0.77 | 0.78 | 242 / 69 / 71 | $0.381 | 7,629 | 26.2 s | 71.2 s | 2 |
  | qwen/qwen3-235b-a22b-2507 (E1) | 0.66 | 0.76 | 0.71 | 238 / 124 / 75 | $0.090 | 773 | 63.1 s | 106.3 s | 0 |

  F1 gaps with 95% ranges (bootstrap: contracts re-sampled 4,000 times):
  - V4 minus E1: +0.096 (+0.048 to +0.146): a real gap.
  - V4 minus Qwen3.8: +0.019 (-0.013 to +0.052): could be zero.
  - V4 minus GLM-5.3: +0.020 (-0.019 to +0.060): could be zero.
  - V4.1 minus V4: -0.026 (-0.062 to +0.007): could be zero.

  V4 group F1: basic facts 0.81, yes/no + quote 0.87, numbers/terms 0.61, license/IP 0.93.
  V4 per field, E1 -> V4:
  - Better: agreement_date 0.66 -> 0.94, parties 0.38 -> 0.58, non_transferable_license
    0.72 -> 0.93, ip_ownership_assignment 0.62 -> 0.83, change_of_control 0.58 -> 0.70,
    governing_law 0.86 -> 0.93.
  - About the same: notice_period_to_terminate_renewal 0.45 -> 0.43, cap_on_liability
    0.77 -> 0.76, non_compete 0.67 -> 0.67, license_grant 1.00 -> 0.98, anti_assignment
    0.99 -> 0.99.
  - Worse: renewal_term 0.62 -> 0.50.

  Full per-field table: `report 20261102-200003`.
- **Conclusion:** Keep deepseek/deepseek-v4-flash: F1 0.80 against E1 0.71, at 2.3× the cost and
  p95 57.5 s against 106.3 s, with 0 bad answers.
  - The four newer models are tied on F1 on this data, so cost, p95 and bad answers decided it.
  - The newest model did not win. V4.1 cost almost 2× as much as V4. Its 2 bad answers were empty
    replies after 9,950 and 20,110 output tokens, and those tokens were still paid for.
  - Weakest V4 fields: notice_period_to_terminate_renewal (0.43), renewal_term (0.50) and
    parties (0.58).
  - 51 of V4's 87 wrong field answers are also wrong in both Qwen3.8 and GLM-5.3. Changing the model
    alone may not fix them. The cause is not checked yet.
  - Limit: providers differ between runs, so this does not fully separate model from provider.
    Crusoe served all 52 V4 calls. GLM-5.3 used 15 providers, V4.1 used 16 and Qwen3.8 used 9.
- **Next step:** Sort a sample of the shared errors by cause (prompt, scoring, labels, hard
  contract), then 2a (validators and citations) on the kept model.