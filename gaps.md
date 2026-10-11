# Gaps

Known gaps in the 3-week plan. Review after week 1 and fold the useful ones into `PLAN.md`.

## Open

1. **Weekly no-AI task missing from the roadmap.** `../PLAN.md` asks for one task per week with
   no AI. Candidates: week 1 a SQL query on `labels`, week 2 a scorer tweak, week 3 a new API
   route.
2. **Hiring answers left to the end.** At the end of each phase, write 3 to 4 sentences answering
   its hiring question (with numbers and run_ids) in a running README draft: Q1 after 0c, Q3
   after 1c, Q4 after 2b, Q2 after 3b.
3. **Thin practice on scaling and pair programming.** "100x" and system design only come up in
   the mock interview; repo-reading only in 3a (Docling). The Concepts checklist is outside P1 and
   needs separate study time.
4. **Passive copying in typing parts.** Re-typing (like 0b) doesn't stick on its own. The
   draft-first core-logic parts and the explain-back gate are what make it stick; don't skip them.
5. **0b length.** About 800 visible lines against the ~700 cap. Keep it whole for now, or split
   steps 1 to 4 and 5 to 7 if it feels too long.

## Risks to watch

- **Pace.** One part per day while new to Python; week 3 (GCP, Docker, CI, Next.js) has the most
  setup friction. If behind, cut 4d to a bare upload page; never cut evals.
- **Small samples.** Qwen3-VL on ~10 docs shows the trade-off but is not a strong claim; say so in
  the README.
- **Cost.** Estimate before every batch run; keep the credit limit on the OpenRouter key.
