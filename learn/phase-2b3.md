# Phase 2b3: the trust run (E2.1 to E2.3)

In this part, you answer the last question in the README: did validation and retries help? You write a
keep rule for retries, make one paid dev run with `--retries 2`, and read it with the 2b2 tool. Then you
log E2.1 to E2.3 and the Phase 2 "done when" numbers.

This is part 3 of 3 for Phase 2b. This part adds no code.

## Words used in this part

Read these first. First answer, final answer, policy and derived run are from 2b2.

- **Lift**: how much F1 goes up after a change. Example: 0.907 to 0.910 is a lift of 0.003.
- **Keep rule**: the test a change must pass to stay. You write it before the run (1d2).
- **Paired bootstrap**: the 1d `gap` cell. It picks contracts at random many times, and uses the same
  picks for both runs.
- **Retry cost per contract**: what the retries cost, split over the contracts. Example: $0.02 over 52
  contracts is about $0.0004 each.
- **Made-up quote**: a quote that is not in the contract, and is also wrong by the gold labels. The
  citation check should catch it.
- **"Done when" numbers**: the 4 numbers that close Phase 2 in `PLAN.md`: validation failure rate,
  made-up quotes caught, retry lift and needs-review rate.

## Objectives

By the end of this part you should be able to:

1. Write a keep rule for retries before the run, and say why it uses counts.
2. Run one dev run with retries, and build its derived runs.
3. Read E2.1, E2.2 and E2.3 as three single changes from the same first answers.
4. Apply your rule line by line, and say pass or fail with numbers.
5. Report the Phase 2 "done when" numbers, each with its `run_id`.

## Dependencies

You install nothing new. This part needs:

- 2b2: `python -m docintel.evals.trust`, and your policy in `EXPERIMENTS.md`.
- 2b: `--retries` and the `attempts` table.
- 1d: the notebook cells `per_doc`, `f1` and `gap`.
- About $0.15 for one dev run on Parasail. The run is yours to start.

## The big picture

Before this part, the trust layer and its replay tool exist, but no new run has used them.

After this part:

```text
keep rule (written, committed) -> one dev run, --retries 2 -> trust <run_id> -> 6 runs, 1 table
                                                                                  |
                     E2.1 (blank validation) . E2.2 (+ citation) . E2.3 (retries) -> EXPERIMENTS.md
```

- **Phase 3** runs the same commands on worse text. There, errors should be more common.
- **Phase 4** uses your verdict as the default for `--retries` in the API.
- **Phase 5** uses these numbers to answer README question 4.

## Remember this

> Write the rule, then pay for the run, then read the rule one line at a time. On clean text, the
> retry loop has very few errors to fix, so the lift will be small. A small, honest "no" with numbers
> is a real result. A rule changed after the run is not.
>
> **Rule first, run second, verdict third.**

## Why

**The README asks it.** Question 4 is "Schema validation: what broke, what we caught, and did retries
help?" Each part of the answer needs a number with a `run_id`.

**Retries cost money on every future run.** If they stay, every contract in Phase 3 and in the API may
pay for them. So they must pass a rule, like prompt v2 in 1d2.

**Small effects need careful reading.** The retry may change 1 to 5 fields out of 624. F1 alone hides
that. Counts of fixed, lost and gained fields show it.

## Design decisions

- **The keep rule uses counts.** The bootstrap cannot see a change of 1 to 3 fields (Round 1). Other
  option: "the low end of `gap` is above 0". It would fail even if retries help.
- **The rule is committed before the run.** The commit date proves it came first. Other option: write
  it in the notebook only. Then nobody can check the order.
- **E2.3 uses your policy on both sides.** First and final answers get the same policy, so only the
  retries change. Other option: final with blanking against first without it. That is two changes.
- **"Keep" means a new default.** If retries pass, `--retries 2` becomes the default for later runs and
  the API. Other option: keep them only for Phase 3. Then the verdict on clean text means nothing.
- **No new code.** The 2b2 tool prints everything. Other option: a script per experiment. More code,
  and the same numbers.

## Worked example

Guess before you open each box.

### Round 1: will the bootstrap see it?

A retry fixes 1 field on 52 contracts. F1 moves by about 0.003. The 1d `gap` cell gives a 95% range.
On E1.3, that range was about 0.04 wide. Will the low end be above 0?

<details><summary>Guess, then open</summary>

No. A gap of 0.003 sits in the middle of a range from about -0.02 to +0.02. The bootstrap cannot tell
a 1-field change from luck. So you report the range, but the keep rule counts fields: fixed, lost and
gained. Each of those you can check by hand.
</details>

### Round 2: what does one retry cost?

The 2b live check (`2b-check`) ran Pareteum with retries on Parasail. Attempt 0 sent 15,621 tokens in
and got 4,729 out. The retry sent the contract again, plus the old answer and the feedback. Guess: does
the retry cost more or less than attempt 0?

<details><summary>Guess, then open</summary>

Less. The real rows:

| Attempt | Tokens in | Tokens out | Cost |
|---|---|---|---|
| 0 | 15,621 | 4,729 | $0.0035 |
| 1 | 16,612 | 1,060 | $0.0015 |

The retry sends about 1,000 more tokens in. But output tokens cost much more than input tokens, and the
retry wrote far fewer. Both answers have the same length: 3,278 characters, under 1,000 tokens. So most
of the 4,729 output tokens of attempt 0 are likely the model's hidden thinking, which is billed as
output. This is one contract. Your run gives the real average.
</details>

## Project setup

This part adds no files. You change only `EXPERIMENTS.md`, and maybe the results table in `README.md`.

## Step 1: the keep rule for retries (your decision)

**Why.** Retries cost money on every future run. They stay only if they pass a rule you write now.

Write the rule in the E2.1 to E2.3 entry from 2b2. Commit it before Step 2.

What to look at:

- **Errors are rare.** 3 fields on the kept run, 6 on Parasail v1 (E2.0, 2b2 Step 3).
- **Many cannot be fixed.** `***` and blank forms (2b Round 1). The no-progress stop ends those early.
- **A retry can lose a TP.** 2b Round 3: the easy fix for `found_no_value` is `found` false.
- **Cost.** Attempt 0 costs about $0.11 for dev on Parasail. One retry may cost less than its attempt 0
  (Round 2). Guess: 5 contracts, 1 or 2 retries each, about $0.01 to $0.02.
- **The bootstrap cannot see 1 field** (Round 1).

The options:

1. **Lift with the bootstrap:** keep if the low end of `gap` is above 0. Almost sure to fail here.
2. **Counts:** keep if no TP is lost, at least one error field is fixed, and the cost is small.
3. **Cost only:** keep if retries add less than some percent. It ignores harm.

<details><summary>Reference rule (open after you write yours)</summary>

Keep `--retries 2` only if all of these are true, on the row of your 2b2 policy:

1. `lost` is 0.
2. Error fields go down by at least 1 (validation plus citation).
3. Final F1 is not lower than first F1.
4. Retries cost at most 20% of attempt 0.
5. 0 bad answers in the final answers.

If it passes, `--retries 2` becomes the default for later runs and the API. If it fails, the default
stays 0, and the loop stays in the code for Phase 3.
</details>

Then commit the rule alone:

```sh
git add EXPERIMENTS.md
git commit -m "E2.3 keep rule, before the run"
```

## Step 2: the run

**Why.** This is the only paid step. The policy and the keep rule are committed, so the result cannot change them.

First, check that the 2b pilot was served by Parasail:

```sh
uv run python - <<'EOF'
from docintel.evals.store import connect

with connect() as con:
    print(con.execute("SELECT DISTINCT provider FROM llm_calls WHERE run_id = '20261107-222125'").fetchall())
EOF
```

```text
[('Parasail',)]
```

Then start the run:

```sh
uv run python -m docintel.evals.runner run --split dev --retries 2
```

The shape of the output (your numbers will differ):

```text
run <run_id>: 52 of 52 docs to do, deepseek/deepseek-v4-flash, about $<estimate>
Start? [y/N] y
[1/52] <doc_id>  ok=True  tries=1  $0.00xx
...
[k/52] <doc_id>  ok=True  tries=2  $0.00xx
...
done in <n> s: 52 of 52 docs scored, 0 calls failed
```

Write the `run_id` down. If calls fail, use `--resume <run_id>`: it keeps `--retries 2`. Check the
provider of the new run with the same query, and your `run_id`.

## Step 3: the trust table

**Why.** One command turns the run into the 6 runs that E2.1 to E2.3 compare.

```sh
uv run python -m docintel.evals.trust <run_id>
```

The shape (from the 2b2 pilot, which had no errors; yours has 52 contracts and some errors):

```text
           first: P     R    F1  final: P     R    F1  changed lost gained
keep          0.958 0.920 0.939     0.958 0.920 0.939        0    0      0
blank-v       0.958 0.920 0.939     0.958 0.920 0.939        0    0      0
blank-vc      0.958 0.920 0.939     0.958 0.920 0.939        0    0      0
error fields: validation 0 -> 0, citation 0 -> 0
retries: 0 of 3 contracts, 0 calls, 0 fixed
cost: first answers $0.0086, retries $0.0000 (0%), $0.0029 per contract
```

Here, read it like this:

1. The left half of each row is the first answers. The right half is the final answers.
2. `changed`, `lost` and `gained` compare the two halves of one row. They measure only the retries.
3. On your run, expect small numbers in `changed`: between 0 and the number of error fields.
4. A check: if `fixed` is above 0, `changed` on the `keep` row must be above 0 too (2b2 Break 1).

## Step 4: E2.1 and E2.2

**Why.** Each one is a single change to the first answers. Only the left half matters here.

Read the left half of the 3 rows:

- **E2.1:** `blank-v` against `keep`. What did blanking validation errors do to P, R and F1?
- **E2.2:** `blank-vc` against `keep`. What did blanking citation errors add?

Now the paired bootstrap. Open the notebook (the trust command must be done) and run your 1d cells.
Then:

```python
RUN = "<run_id>"
print("E2.1 blank-v minus first:", gap(f"{RUN}-first-blank-v", f"{RUN}-first"))
print("E2.2 blank-vc minus first:", gap(f"{RUN}-first-blank-vc", f"{RUN}-first"))
```

*Python here: [run names with f-strings](./py/phase-2b3.md#py-1).*

The shape: two lines like `(0.001, -0.004, 0.006)`, as (gap, low end, high end).

Then see what the citation check caught on the first answers:

```python
con.execute("""
    SELECT doc_id[:20], field, tp, fp FROM issues JOIN scores USING (run_id, doc_id, field)
    WHERE run_id = ? AND issues.rule = 'quote_missing'
""", [f"{RUN}-first"]).fetchall()
```

*Python here: [a `"""` string](./py/phase-2b3.md#py-2) · [`doc_id[:20]` in DuckDB](./py/phase-2b3.md#py-3)
· [`issues.rule`](./py/phase-2b3.md#py-4).*

A row with `fp = 1` is a made-up quote that was caught. A row with `tp = 1` is a right answer with a
copy error (2b2 Round 2). On the E1.3 Parasail run (`20261105-213036`), the same query gives:

```text
[('CORALGOLDRESOURCES,L', 'anti_assignment', 1, 0), ('UpjohnInc_20200121_1', 'cap_on_liability', 1, 0)]
```

Check your 2b2 policy against your own line ("it changes if ..."). Write pass or fail in the notebook.
Do not change the policy now unless your line says so.

## Step 5: E2.3, the retry loop

**Why.** This is the one change the whole of Phase 2b was built for.

Use the row of your policy. Compare its left half with its right half. Then the bootstrap, in the
notebook:

```python
print("E2.3 final minus first (A):", gap(RUN, f"{RUN}-first"))
```

For policy B, use `gap(f"{RUN}-blank-v", f"{RUN}-first-blank-v")`. For C, use `-blank-vc`.

Now apply your Step 1 rule, one line at a time. For the reference rule:

| Line | Where to read it | Pass? |
|---|---|---|
| 1. `lost` is 0 | your policy row | |
| 2. error fields go down by 1 or more | `error fields:` line | |
| 3. final F1 not lower | your policy row | |
| 4. retries at most 20% of attempt 0 | `cost:` line | |
| 5. 0 bad answers | `runner report <run_id>`, last line | |

For line 5:

```sh
uv run python -m docintel.evals.runner report <run_id>
```

The last line has the shape `<n> calls, $<cost>, p50 <x> s, p95 <y> s, 0 bad answers`. It counts
every attempt, so `<n>` is 52 plus the retries.

If one line fails, retries are not kept. Write which line failed, with its number.

## Step 6: the Phase 2 "done when" numbers

**Why.** `PLAN.md` closes Phase 2 with these four numbers, first against final.

Close the notebook. Run `validate` on the first and the final answers:

```sh
uv run python -m docintel.evals.runner validate <run_id>-first
uv run python -m docintel.evals.runner validate <run_id>
```

The shape (from the 2b2 pilot's `-first` run):

```text
stored 3 issues for run 20261107-222125-first
errors: 0 fields (0.0%) in 0 contracts
needs review: 3 fields (8.3%) in 2 contracts
need a look (gold): 5 fields, 2 of them missed
caught: 2 of 5, and 0 of the 2 missed
by rule: quote_gap 3
```

Fill in this table for your entry:

| Number | First answers | Final answers |
|---|---|---|
| Validation failure rate (the `errors:` line) | | |
| Made-up quotes caught (Step 4, rows with `fp = 1`) | | |
| Retry lift (F1, with the `gap` range) | | |
| Needs-review rate (the `needs review:` line) | | |

Also compare with E2.0, the kept run on Crusoe: errors 0.5%, needs review 5.6%, 0 `quote_missing`.

## Break it on purpose

**Break 1: the trust tool on an old run.** Run it on the E1.3 Parasail run, which was made before 2b.
Guess: what happens?

```sh
uv run python -m docintel.evals.trust 20261105-213036
```

<details><summary>What you see</summary>

```text
           first: P     R    F1  final: P     R    F1  changed lost gained
...
    tp = sum(counts[f][0] for f in fields)
             ~~~~~~^^^
KeyError: 'parties'
```

That run has no rows in `attempts`. So `first_answers` returns nothing, and `-first` is an empty run
with no scores. `metrics` then finds no `parties` row. The tool needs a run made with the 2b code. The
derived runs it made before the crash stay in the database. The `-first` ones are empty. They do no
harm.
</details>

## Experiment

**Command:** Step 2, then Step 3. **run_id:** one new run, plus 5 derived runs (`-first`,
`-first-blank-v`, `-first-blank-vc`, `-blank-v`, `-blank-vc`).

The table to expect (shape, not numbers): 3 policy rows, each with P, R and F1 for first and final,
then `changed`, `lost` and `gained`. Then the error line, the retries line and the cost line.

Fill in the E2.1 to E2.3 entry from 2b2. Split it into three entries:

```markdown
## E2.1: keep or blank a field with a validation error
- **Date:** <date>
- **Score rules Hash:** `6ffdaa7` (same rules as E1.2). Code: <commit>.
- **run_id(s):** first answers <run_id>-first, blanked <run_id>-first-blank-v. Parent <run_id>.
- **Question / hypothesis:** Does blanking fields with a validation error raise F1? How many TPs does
  it lose?
- **Data:** dev, 52 contracts, 12 fields, CUAD .txt.
- **Setup:** deepseek/deepseek-v4-flash on Parasail, prompt v1, first answers of a `--retries 2` run.
  Replay only, no LLM calls.
- **Policy written before the run:** <your 2b2 Step 5 choice, and the line that would change it>.
- **Results:** P/R/F1 keep and blank-v, `gap` with range, fields blanked, TPs lost.
- **Conclusion:** <keep or blank, against your line>.
- **Next step:** E2.2.

## E2.2: the same, plus the citation check
- Same as E2.1, with <run_id>-first-blank-vc. Add: the `quote_missing` rows, and how many were made up.

## E2.3: the retry loop
- **run_id(s):** <run_id> (final) against <run_id>-first, with policy <A, B or C>.
- **Keep rule (written before the run):** <your Step 1 rule>.
- **Results:** P/R/F1 first and final, `gap` with range, changed, lost, gained, error fields before
  and after, contracts retried, retry calls, fixed, retry cost (total, percent of attempt 0, per
  contract), p95. The Phase 2 "done when" table from Step 6.
- **Limits:** dev only, 52 contracts, clean text. Errors are rare, so the counts are small. The rules
  were written from dev data.
- **Conclusion:** <each line of the rule: pass or fail>. Default retries: <0 or 2>.
- **Next step:** Phase 3, the same loop on worse text.
```

Then add an E2.3 row to the results table in `README.md`: what changed, and F1 first to final. Use only
dev. The test split gives the final numbers at the end of the project.

## Gotchas

- **`estimate` counts attempt 0 only.** The real cost is in the `cost:` line of the trust report.
- **Do not edit `retry.md` or the rules after you see the results.** That would fit them to dev. A
  change needs a new run and a new entry.
- **A pinned provider can be busy.** With no backup, a busy Parasail gives errors. Resume the run later.
- **The database is locked.** Close the notebook before each command, and the other way round.
- **Derived runs have no cost line.** The cost lives with the parent run, in `runner report <run_id>`.

## Explain back, then commit

Explain to Claude in a few sentences (the rule in `PLAN.md`):

- Your keep rule: why each line, and why counts, not the bootstrap.
- The trust table: what each column means, on one real row.
- E2.1 to E2.3: the verdict for each, with the numbers.
- The 4 "done when" numbers, and what they say about clean text.

Then:

```sh
git status
git add EXPERIMENTS.md README.md
git commit -m "phase 2b3: trust experiments E2.1 to E2.3"
```

## Conclusion

What you have now:

- One dev run with retries, and 5 derived runs, each with a `run_id`.
- E2.1 to E2.3 in `EXPERIMENTS.md`, judged by rules written before the run.
- The Phase 2 "done when" numbers, and a default for `--retries`.

Go back to the objectives. Check that you can do each one without notes. Then answer:

1. Why does E2.3 use the same policy on the first and the final answers?
2. A retry fixed 1 field and lost 0 TPs, but the `gap` range still includes 0. Is that a fail? Use your
   rule.
3. What would you expect to change in the trust table on pypdf text in Phase 3?

Want more practice? Try these (optional):

1. Split the retry cost by error rule. Which rule costs the most retries?
2. Find a contract where a retry changed a field. Read its `attempts` rows and say what the model did.

Checklist (`../PLAN.md`): **Validation, citation check, retry with feedback; retry cost** (measured:
error rate, what the citation check caught, retry lift and cost per contract). **Experiments: run_id,
one change at a time, cost, p50/p95** (one run, derived runs, a committed rule before the run).
**Precision/recall/F1 per field; span scoring** (paired bootstrap on each change).
