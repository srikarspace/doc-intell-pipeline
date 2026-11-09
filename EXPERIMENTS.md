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
- **Score rules Hash:** `6ffdaa7` (old rules: `f8a2f10`)
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

## E1.3: using different prompt
- **Date:** 2026-11-05
- **Score rules Hash:** `6ffdaa7` (same rules as E1.2)
- **run_id(s):** clean test, both on Parasail: v1 20261105-213036, v2 20261105-213505. Also v2 on mixed
  providers 20261105-201546, and v1 on Crusoe 20261102-200003 (from E1.1). Pilots, not used:
  20261105-201438, 20261105-212323, 20261105-212948. Stopped: 20261105-212357 (DeepInfra was
  overloaded, 429 `engine_overloaded`, 3 of 52 done).
- **Question / hypothesis:** Do specific rules for 4 weak fields beat v1, without losing recall?
- **Setup:** deepseek/deepseek-v4-flash, cuad_txt, temperature 0, no validation retries. Only the prompt
  changes: v1 -> v2. Target fields: non_compete, notice_period_to_terminate_renewal, cap_on_liability,
  ip_ownership_assignment. The first v2 run landed on other providers than v1 (Crusoe no longer serves
  V4 Flash), so both prompts were run again with the provider pinned to Parasail (fp8).
- **Keep rule (written before the run):** keep v2 only if all of these are true, against
  20261102-200003:
  1. All-field F1 is at least 0.927 (0.912 + 0.015, a little more than the noise guess).
  2. Recall is at least 0.925 (287 TP: it can lose 3).
  3. The low end of the `gap` range is above 0.
  4. 0 bad answers.
  5. Cost is at most $0.255, and p95 at most 71.9 s (1.25 times v1).
  6. Wrong-quote TPs are at most 6 (v1 has 4).
  If v2 fails, v1 stays. A v3 needs its own new entry and rule.
- **Results:**

  | Run | Provider | P | R | F1 | Cost | Out tokens | p95 | Bad | Wrong-quote TPs |
  |---|---|---|---|---|---|---|---|---|---|
  | v1 (E1.2) | Crusoe | 0.890 | 0.935 | 0.912 | $0.204 | 8,953 | 57.5 s | 0 | 4 |
  | v1 | Parasail | 0.901 | 0.913 | 0.907 | $0.112 | 2,601 | 37.3 s | 0 | 10 |
  | v2 | Parasail | 0.895 | 0.939 | 0.917 | $0.114 | 2,594 | 47.2 s | 0 | 11 |
  | v2 | Venice 40, Parasail 11, DigitalOcean 1 | 0.886 | 0.926 | 0.905 | $0.087 | 2,567 | 103.1 s | 0 | 6 |

  F1 gaps with 95% ranges (bootstrap, 4,000 re-samples, seed 7):
  - Prompt, v2 minus v1, both Parasail: +0.009 (-0.010 to +0.030): could be zero.
  - Provider, v1 Parasail minus v1 Crusoe: -0.005 (-0.028 to +0.019): could be zero.
  - v2 Parasail minus v1 Crusoe (keep rule): +0.005 (-0.021 to +0.030).

  Field F1 on Parasail, v1 -> v2:
  - Targets: cap_on_liability 0.81 -> 0.94 (FN 7 -> 0), ip_ownership_assignment 0.87 -> 0.91,
    non_compete 0.71 -> 0.67 (FP 5 -> 7), notice_period_to_terminate_renewal 0.63 -> 0.57 (FP 4 -> 6).
  - Side effect: non_transferable_license 0.88 -> 0.73 (FP 4 -> 7), not a target field.
  - The mixed-provider v2 run moved the same way for cap (0.79 -> 0.91) and non_transferable_license
    (0.93 -> 0.81).
- **Limits:** The rules were written from dev errors, so any gain is optimistic, and test gives the
  final number. Two v2 runs differ by 0.012 F1, about the size of the prompt effect. `llm_calls` has no
  `doc_id`, so a mixed-provider run cannot be split by provider.
- **Conclusion:** v2 is not kept, so v1 stays. Against the rule: 1 fails (F1 0.917 < 0.927), 2 passes
  (R 0.939), 3 fails (low end -0.021), 4 passes, 5 passes ($0.114, p95 47.2 s), 6 fails (11 > 6).
  - The cap_on_liability rule works: FN went to 0 in both v2 runs.
  - The non_compete and notice_period rules did not help in either run, and FPs went up.
  - Wrong-quote TPs rise with Parasail for both prompts (10 and 11, against 4 on Crusoe), so rule 6
    mostly measures the provider, not the prompt.
  - Parasail gives the same F1 as Crusoe with about 70% fewer output tokens, at about half the cost
    and a lower p95.
- **Next step:** Decide on a v3 with only the cap_on_liability rule (new entry and rule), and which
  provider to use. Remove the temporary Parasail pin in `core/llm.py`. Then 2a.

## E2.0: validation and review flags on stored runs
- **Date:** 2026-11-07
- **Score rules Hash:** `6ffdaa7` (same rules as E1.2). Validate code: `f200281`.
- **run_id(s):** replay of 20261102-200003 (kept: V4 Flash, v1, Crusoe). No LLM calls, $0.
- **Question / hypothesis:** How often do answers break a rule? How many real problems do review flags
  catch, and at what review rate?
- **Data:** dev, 52 contracts, 12 fields (624), CUAD .txt (clean).
- **Setup:** errors: `quote_missing`, `found_no_quote`, `quote_not_found`, `found_no_value`,
  `value_not_found`, `bad_date`, `bad_schema`. Warnings: `quote_gap` (MAX_GAP 60), `quote_no_words`,
  `quote_off_topic` (topic word parts, 10 fields), `maybe_missed` (change_of_control, cap_on_liability,
  renewal_term). Needs review = any field with at least one issue. No retries.
- **Results:**

  | Errors | Needs review | Need a look (gold) | Caught | Misses caught | `quote_missing` |
  |---|---|---|---|---|---|
  | 3 fields (0.5%), 2 contracts | 35 fields (5.6%), 27 contracts | 54 | 18 (33%) | 4 of 14 | 0 |

  By rule: quote_off_topic 15, maybe_missed 10, quote_gap 6, found_no_value 3, quote_no_words 1.
  18 of 35 flags (51%) point to a real problem.
- **Limits:** the review rules were written from dev answers, so the catch is optimistic; test gives the
  final number. "Need a look" uses gold labels, which have known errors (1d).
- **Conclusion:** Errors are rare (3 fields, all `found_no_value`), so a retry in 2b can fix very little
  on clean text. Flags are cheap per field (5.6%) but touch half the contracts (27 of 52). They catch a
  third of the real problems; the other 36 look clean. No made-up quotes.
- **Next step:** 2b, retry on errors. Before the first run: choose the provider (the Parasail pin in
  `core/llm.py`).

## E2.1: keep or blank a field with a validation error
- **Date:** 2026-11-08
- **Score rules Hash:** `6ffdaa7` (same rules as E1.2). Code: 2b2 tool, not committed yet (on `13771c0`).
- **run_id(s):** 20261108-062221-first against 20261108-062221-first-blank-v. Parent 20261108-062221 (`--retries 2`,
  Parasail). Evidence before the run: replays of 20261102-200003 (Crusoe), 20261105-213036 (Parasail v1).
- **Question / hypothesis:** Does blanking fields with a validation error (`found_no_quote`,
  `quote_not_found`, `found_no_value`, `value_not_found`, `bad_date`) raise F1? How many TPs does it
  lose?
- **Setup:** deepseek/deepseek-v4-flash on Parasail, prompt v1, first answers only. Replay, no LLM calls.
- **Evidence before the run (2b2 Step 5):**

  | Run | Keep: F1 (TP/FP/FN) | Blank validation |
  |---|---|---|
  | Crusoe 20261102-200003 | 0.9119 (290/36/20) | 0.9131 (289/34/21) |
  | Parasail v1 20261105-213036 | 0.9071 (283/31/27) | 0.9082 (282/29/28) |

  Blanking removes 2 FPs and loses 1 TP on each run (Pareteum `renewal_term`: a real clause with a
  hidden `***` value).
- **Policy (written before the run):** A, keep and flag. +0.001 is far inside the 0.012 noise, and a
  blank hides a real clause that a flag would send to a person. It changes if: blanking lifts F1 by
  more than 0.012 on the first answers, and loses no TP.
- **Results:**

  | Run | P | R | F1 | TP/FP/FN |
  |---|---|---|---|---|
  | first (keep) | 0.893 | 0.913 | 0.903 | 283/34/27 |
  | first-blank-v | 0.895 | 0.903 | 0.899 | 280/33/30 |

  Gap blank-v minus keep: -0.004 (-0.010 to 0.000). 4 fields blanked: 3 TPs lost (Pareteum
  `renewal_term` and `cap_on_liability`, Sucampo `cap_on_liability`, all `found_no_value` on a real
  clause), 1 FP removed (Pareteum `notice_period`).
- **Conclusion:** keep and flag (A) stays. Against the line: F1 went down, not up by 0.012, and 3 TPs
  were lost. Blanking a validation error hides more right answers than wrong ones.
- **Next step:** E2.2.

## E2.2: the same, plus the citation check
- **Date:** 2026-11-08
- **Score rules Hash:** `6ffdaa7` (same rules as E1.2). Code: as E2.1.
- **run_id(s):** 20261108-062221-first against 20261108-062221-first-blank-vc. Parent 20261108-062221.
- **Question / hypothesis:** Does also blanking fields with a citation error (`quote_missing`) raise F1?
  Are the caught quotes made up, or right answers with a copy error?
- **Setup:** as E2.1, plus `quote_missing` in the blanked rules.
- **Evidence before the run (2b2 Step 5):** Crusoe has no citation errors (same as E2.1). Parasail v1:
  0.9071 (283/31/27) -> 0.9047 (280/29/30). Both caught quotes were TPs with a copy error in the
  contract text (Coral Gold `anti_assignment`: `thewritten`; Upjohn `cap_on_liability`). 0 made up.
- **Policy (written before the run):** A, keep and flag. The same line as E2.1 changes it.
- **Results:** first-blank-vc: P 0.894, R 0.897, F1 0.895 (278/33/32). Gap blank-vc minus keep: -0.007
  (-0.015 to -0.002), a real loss. 6 fields blanked: 5 TPs lost, 1 FP removed.
  `quote_missing` on the first answers: Coral Gold `anti_assignment` (TP) and Upjohn `cap_on_liability`
  (TP). Both are right answers with a copy error against odd contract text (`thewritten`; `11⁄2` where the model wrote `1½`).
  0 made up, same as on the Parasail v1 run.
- **Conclusion:** keep and flag (A) stays. Blanking citation errors is the worst policy on clean text:
  the citation check catches copy errors, not made-up quotes.
- **Next step:** E2.3.

## E2.3: the retry loop
- **Date:** 2026-11-08
- **Score rules Hash:** `6ffdaa7` (same rules as E1.2). Code: as E2.1.
- **run_id(s):** 20261108-062221 (final) against 20261108-062221-first, policy A (`keep` row). All 56 calls on Parasail.
  Other derived runs: 20261108-062221-first-blank-v, -first-blank-vc, -blank-v, -blank-vc.
- **Question / hypothesis:** Do repair retries (max 2, errors sent back to the model) fix error fields
  without losing right answers, at a small cost?
- **Setup:** one dev run, 52 contracts, deepseek/deepseek-v4-flash, prompt v1, Parasail pinned,
  `--retries 2`. Then `python -m docintel.evals.trust <run_id>`.
- **Keep rule (written before the run):** keep `--retries 2` only if all of these are true, on the
  `keep` row:
  1. `lost` is 0.
  2. Error fields (validation plus citation) go down by at least 1.
  3. Final F1 is not lower than first F1.
  4. Retries cost at most 20% of attempt 0.
  5. 0 bad answers in the final answers.
  If it passes, `--retries 2` becomes the default for later runs and the API. If it fails, the default
  stays 0, and the loop stays in the code for Phase 3.
- **Results:**

  ```text
             first: P     R    F1  final: P     R    F1  changed lost gained
  keep          0.893 0.913 0.903     0.893 0.913 0.903        1    0      0
  blank-v       0.895 0.903 0.899     0.895 0.903 0.899        1    0      0
  blank-vc      0.894 0.897 0.895     0.894 0.900 0.897        1    0      1
  error fields: validation 4 -> 4, citation 2 -> 1
  retries: 4 of 52 contracts, 4 calls, 1 fixed
  cost: first answers $0.1131, retries $0.0078 (7%), $0.0023 per contract
  ```

  Gap final minus first (keep): 0.000 (0.000 to 0.000). Run: 56 calls, $0.121, p50 15.5 s, p95 33.5 s,
  0 bad answers.
  - Fixed: Upjohn `cap_on_liability`. The retry shortened the quote to text that is in the contract.
    It was a TP before and after, so F1 did not move.
  - Not fixed, stopped after 1 retry by the no-progress stop: Coral Gold (`thewritten`), Pareteum (3
    fields with `***` values), Sucampo `cap_on_liability`.
  - This run's first answers against the E1.3 Parasail v1 run: -0.004 (-0.018 to +0.011), run noise.

  Phase 2 "done when" numbers:

  | Number | First answers | Final answers |
  |---|---|---|
  | Validation failure rate | 6 fields (1.0%) in 4 contracts | 5 fields (0.8%) in 3 contracts |
  | Made-up quotes caught | 0 (2 `quote_missing`, both copy errors) | 0 (1 left: Coral Gold) |
  | Retry lift (F1) | 0.903 | 0.903 (gap 0.000, 0.000 to 0.000) |
  | Needs-review rate | 46 fields (7.4%) in 27 contracts | 45 fields (7.2%) in 26 contracts |

  E2.0 (kept run, Crusoe): errors 0.5%, needs review 5.6%, 0 `quote_missing`.
- **Limits:** dev only, 52 contracts, clean text. Errors are rare, so every count is small. The rules
  were written from dev data. The one fix made a quote checkable, not more correct.
- **Conclusion:** retries pass the keep rule, all 5 lines: 1 `lost` 0 (pass), 2 error fields 6 -> 5
  (pass), 3 F1 0.903 -> 0.903 (pass), 4 retries 7% of attempt 0 (pass), 5 0 bad answers (pass).
  So by the rule, `--retries 2` becomes the default. Honest size: 1 field of 624 changed, F1 did not
  move, and it costs about $0.0002 per contract. Most errors on clean text cannot be fixed by the
  model (redacted `***` values, broken words in the contract).
- **Next step:** done: `--retries` default is now 2 in `evals/runner.py`. Then Phase 3, the same loop and trust
  table on worse text, where errors should be more common.

## E3.0: vision model pilot
- **Date:** 2026-11-08
- **run_id(s):** pilot-20261108-210053 (3 docs), pilot-20261108-212103 (6 more docs; the first 3 came from the
  cache). Calls are in `llm_calls`.
- **Question / hypothesis:** Does the DeepSeek vision model read our contract pages well enough for its cost?
- **Data:** dev, 9 contracts, 69 pages (`--per-band 3`: 3 from each third of the lengths, at most 20 pages each),
  PDFs with a text layer. No scans yet.
- **Setup:** deepseek/deepseek-v4.1-flash-1017 on Parasail. One call per page, 150 DPI,
  grayscale, page cap 20, token limit 12,000, the copy prompt in `domain/parse/vision.py`. Budgets: $1.00 and $0.30.
  Free baselines: pypdf, and Docling with OCR and tables off.
- **Keep rule (written before the run):** none was written before the run. <user: write the rule, and say it came
  after the run>
- **Results:**

  | Parser | Docs | Pages | Ratio | Quotes found | Cost | s/page |
  |---|---|---|---|---|---|---|
  | pypdf | 9 | 69 | 0.999 | 156/158 | $0 | 0.01 |
  | docling | 9 | 69 | 0.991 | 157/158 | $0 | 1.09 |
  | deepseek_vl | 9 | 69 | 0.994 | 153/158 | $0.2108 | 8.66 |

  - DeepSeek: 69 of 69 pages OK, $0.0031 per page, largest output 7,028 tokens.
- **Limits:** Few pages, one run each, and PDFs with a text layer, where copying the text is expected to win. The gap
  is 4 quotes of 158, too small to rank quality.
- **Conclusion:** <user: the result against the rule>
- **Next step:** 3b, fake scans and the full parser comparison, with Docling OCR on.
