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
- **Score rules Hash:** `f8a2f10` (marks in `scores_r1`; see E1.2)
- **run_id(s):** 20261101-192153 (pilots: 20261101-155906, 20261101-191023)
- **Question / hypothesis:** How well does Qwen3-235B find the 12 fields? Which are weak?
- **Setup:** dev, 52 contracts, CUAD .txt. qwen/qwen3-235b-a22b-2507, prompt v1, temperature 0, no
  validation retries. A bad answer scores as 12 empty fields.
- **Results:** P 0.66, R 0.76, F1 0.71 (TP 238, FP 124, FN 75). $0.090, p50 63.1 s, p95 106.3 s, 0 bad.
  Group F1: basic facts 0.63, yes/no + quote 0.85, numbers/terms 0.65, license/IP 0.80.
- **Conclusion:** Weakest: parties (0.38) and notice_period_to_terminate_renewal (0.45).
  - parties is a scoring problem: all 32 misses have the right names, but the quote is the whole
    opening sentence and the gold spans are only the names.
  - notice_period is a model problem: 14 of 15 FPs quote the notice to end the agreement, not the
    notice to stop a renewal.
- **Next step:** E1.1.

## E1.1: using different models
- **Date:** 2026-11-02
- **Score rules Hash:** `f8a2f10` (marks in `scores_r1`; see E1.2)
- **Question / hypothesis:** Does a newer open-weight model beat E1, or match it for less cost or
  latency?
- **Setup:** same as E1; only the model changes, with default reasoning and OpenRouter's provider
  choice. Keep rule (1c4 reference): F1 at least E1's minus 0.02, and cheaper or faster at p95; if
  several pass, the cheapest. Pilots: 20261102-193610, 20261102-202613.
- **Results:**

  | Model | run_id | P | R | F1 | Cost | p50 | p95 | Bad |
  |---|---|---|---|---|---|---|---|---|
  | deepseek/deepseek-v4-flash | 20261102-200003 | 0.79 | 0.82 | 0.80 | $0.204 | 31.0 s | 57.5 s | 0 |
  | qwen/qwen3.8-27b | 20261102-194826 | 0.76 | 0.81 | 0.78 | $0.883 | 86.8 s | 209.8 s | 0 |
  | z-ai/glm-5.3-flash | 20261102-200841 | 0.75 | 0.82 | 0.78 | $0.213 | 22.6 s | 89.5 s | 0 |
  | deepseek/deepseek-v4.1-flash-1017 | 20261102-202705 | 0.78 | 0.77 | 0.78 | $0.381 | 26.2 s | 71.2 s | 2 |
  | qwen/qwen3-235b-a22b-2507 (E1) | 20261101-192153 | 0.66 | 0.76 | 0.71 | $0.090 | 63.1 s | 106.3 s | 0 |

  V4 minus E1: F1 +0.096 (95% range +0.048 to +0.146), a real gap. V4's gaps to the other newer models
  could be zero.
- **Conclusion:** Keep deepseek/deepseek-v4-flash: F1 0.80 against E1 0.71, at 2.3× the cost and
  p95 57.5 s against 106.3 s, with 0 bad answers.
  - The newest model did not win: V4.1 cost almost 2× as much, and 2 answers were empty after 9,950
    and 20,110 paid output tokens.
  - 51 of V4's 87 errors are also wrong in both Qwen3.8 and GLM-5.3.
  - Limit: Crusoe served all 52 V4 calls, while the others used 9 to 16 providers. So this does not
    fully separate model from provider.
- **Next step:** Sort the errors by cause (E1.2).

## E1.2: using different scoring rules for E1.1
- **Date:** 2026-11-05
- **Score rules Hash:** not committed yet (old rules: `f8a2f10`)
- **run_id(s):** the 5 full runs in E1.1. Same answers, new marks. No LLM calls, $0.
- **Question / hypothesis:** How many of V4's 87 errors are the rule's fault? Do the weak fields or
  the model choice change?
- **Setup:** only these rules change:
  - `parties`: every name in `value` must match a gold span, not the quote.
  - Quote fields: a quote also matches if it is part of a span (at least 4 words, 80% in the span).
  - `governing_law`: ignore "province", "republic" and "and"; accept all CUAD places together.
  - `agreement_date`: a date left blank in the form, with no year in any span, is not counted.
- **Error sort:** scoring 39, prompt 27, labels 12, hard contract 9 (reference sort in
  `learn/phase-1d.md`, one reader's judgment).
- **Results:**

  | Model | Old F1 | P | R | New F1 |
  |---|---|---|---|---|
  | deepseek/deepseek-v4-flash | 0.801 | 0.890 | 0.935 | 0.912 |
  | z-ai/glm-5.3-flash | 0.782 | 0.868 | 0.958 | 0.911 |
  | qwen/qwen3.8-27b | 0.783 | 0.879 | 0.935 | 0.906 |
  | deepseek/deepseek-v4.1-flash-1017 | 0.776 | 0.891 | 0.894 | 0.892 |
  | qwen/qwen3-235b-a22b-2507 (E1) | 0.705 | 0.768 | 0.897 | 0.827 |

  V4 minus E1: F1 +0.085 (95% range +0.053 to +0.118), a real gap. V4's gaps to the other newer models
  could be zero.

  V4 errors fell from 87 to 50 (30 made up, 14 missed, 6 wrong): 36 marks became right, 2 became
  wrong, and 3 are no longer counted.
  V4 field F1, old -> new: parties 0.58 -> 0.94, renewal_term 0.50 -> 0.90, notice_period 0.43 -> 0.70,
  governing_law 0.93 -> 1.00, agreement_date 0.94 -> 0.97, cap_on_liability 0.76 -> 0.79. The other 6
  fields did not change.
- **Limits:** The rules were fitted on dev, so this is a fairer measure, not a better model, and test
  gives the final number. `names_ok` cannot see a missing party, and the 4-word minimum is not proven
  by dev data. Negative controls: quotes against other fields passed 0 of 355; names against the next
  contract passed 2 of 52, both the same company.
- **Conclusion:** V4 Flash stays under the 1c4 keep rule: F1 0.912, and the cheapest that passes
  ($0.204). GLM-5.3 is level on F1 with higher recall. Weakest now: non_compete (0.67),
  change_of_control (0.70) and notice_period_to_terminate_renewal (0.70).
- **Next step:** 1d2, prompt v2 for the weak fields, on these rules (E1.3).
