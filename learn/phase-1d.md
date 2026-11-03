# Phase 1d: review the errors and fix the scoring (E1.2)

In this part, you read the errors of the kept run and sort each one by its cause. Then you fix the
scoring rules where a right answer is marked wrong, one rule at a time. You rescore the stored runs
with no LLM calls and no cost.

This is part 1 of 2 for Phase 1d. Part 2 (1d2) writes prompt v2 and runs E1.3. It uses the errors
that are left after your rules, so it comes after your E1.2.

## Words used in this part

Read these first. TP, FP, FN, Jaccard and threshold are from 1b2.

- **Cause**: why an answer counts as an error. This part uses four: scoring, prompt, labels and hard
  contract.
- **Rescore**: run `score` again on stored answers. The answers stay the same. Only the marks change.
- **Snapshot**: a copy of a table at one moment. Example: `scores_r1` keeps the marks of the old
  rules.
- **Flip**: one field of one contract whose TP, FP or FN changed after a rule change. Example: FP and
  FN becomes TP.
- **Inside**: a quote is inside a gold span when nearly all its words are in that span. Example:
  `shall automatically renew` is inside the whole renewal sentence.
- **Overlap**: shared words divided by the size of the smaller text. Example: 2 shared words and a
  smaller text of 2 words gives 1.0.
- **False pass**: a wrong answer that the rule marks right. A kind rule makes more of these.
- **Negative control**: a test that gives the rule answers that must fail. Example: this contract's
  names against the next contract's gold spans.
- **Blank date**: a date in a form that nobody filled in. Example: `[●]`.
- **Bootstrap**: pick contracts at random, with repeats, many times, and compute the result each
  time. The spread of results shows how much is just luck in the sample.

## Objectives

By the end of this part you should be able to:

1. Sort a real error into scoring, prompt, labels or hard contract, and defend your choice.
2. Explain why scoring gets fixed before the prompt.
3. Change one scoring rule, rescore with no LLM calls, and read every flip.
4. Test a kinder rule against answers that must fail.
5. Say what a higher score does and does not prove.

## Dependencies

You install nothing new. This part needs:

- 1b2: the rules in `src/docintel/evals/scorers.py`, and `tests/test_scorers.py`.
- 1c: `score` and `report` in `src/docintel/evals/runner.py`.
- 1c4: the kept run `20261102-200003` (`deepseek/deepseek-v4-flash`, prompt v1), and E1.1.

Your numbers should match this doc until you make your first rule decision. After that, they match
only if your rule matches the reference.

## The big picture

Before this part, the kept run has F1 0.80 and 87 wrong field answers. E1.1 found that 51 of them
are also wrong in Qwen3.8 and GLM-5.3. So a new model may not fix them. We do not know why yet.

After this part:

- Each error type has a cause, written in your notebook.
- `scorers.py` has fewer false errors. Tests protect the new rules.
- `scores_r1` keeps the old marks, so E1 and E1.1 can still be checked.
- E1.2 gives the same five runs under the new rules.
- 1d2 knows which fields are really weak. Later parts (2a, 2b) measure against the final 1d run.

## Remember this

> A score measures two things at once: the model, and the rule that marks it. If the rule is wrong,
> you may fix the wrong thing. So fix the rule first, and change nothing else. A score that goes up
> this way shows a better ruler, not a better model.
>
> **Fix the ruler first, then the model.**

## Why

**The prompt must solve real errors.** A prompt rule for `parties` is wasted if the model already
gives the right names. Scoring first shows which fields are really weak.

**A kinder rule always helps the score.** So a higher score proves nothing alone. A rule change must
also fail the answers that should fail. That is the reason for Step 7.

**Reading only errors has a bias.** We look for right answers marked wrong. We do not look as hard
for wrong answers marked right. So fixes mostly push the score up. Step 7 reduces this bias. E1.2
must also say it plainly.

## Design decisions

- **Snapshot with one SQL line.** `scores_r1` copies the old marks. Other option: add a rules version
  column to `scores`. That changes the primary key, `metrics` and every query, for one comparison.
- **Same `run_id` after rescoring.** The answers did not change, so it is the same run. Other option:
  copy each run to a new id. Then one run has two names.
- **No new columns in `scores`.** The `rule` column already holds free text, and `value_ok` can hold
  the result of a value check. Other option: a new column per rule. That needs a table change for
  very little gain.
- **One rule, one rescore.** You see what each rule did. Other option: all rules at once. Then one
  bad rule can hide behind three good ones.

## Worked example

Real errors from the kept run. Guess the cause before you open each box.

### Round 1: right names, low score

The model's `value` for one contract is `['I-ESCROW, INC.', '2THEMART.COM, INC.']`. Its quote is the
whole first sentence of the contract. The gold spans are `2THEMART.COM, INC.`, `I-ESCROW, INC.`,
`i-Escrow` and `2TheMart`. The best Jaccard is 0.06. What is the cause?

<details><summary>Guess, then open</summary>

Scoring. The model has the right names. A long sentence and a short name can never reach Jaccard 0.5,
because the sentence has too many other words. You saw this in 1c3 Round 2.
</details>

### Round 2: the right part of a long sentence

The model quotes `this Agreement shall automatically renew for successive additional three-year
terms`. The gold span is that text with more around it: `Unless either party gives written notice
... this Agreement shall automatically renew for successive additional three-year terms; provided,
however, ...`. Jaccard is 0.29. What is the cause?

<details><summary>Guess, then open</summary>

Scoring. Prompt v1 asks for "the shortest full sentence or clause", and the model obeys. Lawyers
marked the whole sentence. Jaccard punishes the short quote, even though each word of it is in the
gold span. Your 1c3 Conclusion asked about this exact case.
</details>

### Round 3: a good quote for another question

For `notice_period_to_terminate_renewal`, the gold says absent. The model quotes `Either Party may
terminate this Agreement for any reason following the Initial Term upon ninety (90) days written
notice to the other Party.` Lawyers marked this sentence under another category: Termination For
Convenience. What is the cause?

<details><summary>Guess, then open</summary>

Prompt. This is a real quote, but for a different question. It ends the whole contract at any time.
It does not stop a renewal. No fair scoring rule should pass it. A clearer prompt rule may fix it, so
this one goes to 1d2.
</details>

## Project setup

You create no new files. You change these:

```text
├── notebooks/00_explore.ipynb        + error review cells
├── src/docintel/evals/scorers.py     + four rule changes
├── tests/test_scorers.py             + tests for the new rules
└── EXPERIMENTS.md                    + E1.2
```

Your database also gets one new table: `scores_r1`.

Add these imports to a new notebook cell. Open `con` as you did in 1c3:

```python
import json
import random
from collections import defaultdict

from docintel.domain.schema.fields import CUAD_CATEGORY
from docintel.evals.scorers import tokens
```

## Step 1: keep the old marks

**Why.** `score` deletes a run's marks before it writes new ones. After E1.2, `report` would no longer
match the E1 and E1.1 tables.

Close the notebook connection (`con.close()`), then run this once:

```sh
uv run python -c "
from docintel.evals.store import connect
with connect() as con:
    con.execute('CREATE TABLE scores_r1 AS SELECT * FROM scores')
    print(con.execute('SELECT count(*) FROM scores_r1').fetchone())"
```

```text
(3360,)
```

*Python here: [`CREATE TABLE ... AS SELECT`](./py/phase-1d.md#py-1).*

Here, we copy every row of `scores` to a new table. `r1` means "rules, version 1". If you run it a
second time, DuckDB raises an error. That is good: it cannot overwrite your old marks.

Save the code version too:

```sh
git log -1 --format='%h %s' -- src/docintel/evals/scorers.py
```

```text
f8a2f10 add 1c3
```

Write that hash down for E1.2. Anyone can check out `f8a2f10` and get the old rules back.

## Step 2: sort the errors by cause (your decision)

**Why.** Each cause has a different fix. Sorting tells you what to change, and what to leave alone.

Open `con` again in the notebook. This cell picks up to 5 errors per field, with a seed:

```python
RUN = "20261102-200003"
ERRORS = """
SELECT field, doc_id, s.gold_present, s.found, p.answer
FROM scores_r1 s JOIN predictions p USING (run_id, doc_id, field)
WHERE run_id = ? AND (s.fp > 0 OR s.fn > 0)
ORDER BY field, doc_id
"""
by_field = defaultdict(list)
for row in con.execute(ERRORS, [RUN]).fetchall():
    by_field[row[0]].append(row)
rng = random.Random(7)
sample = [row for rows in by_field.values() for row in rng.sample(rows, min(5, len(rows)))]
print(len(sample), {field: len(rows) for field, rows in by_field.items()})
```

```text
46 {'agreement_date': 5, 'anti_assignment': 1, 'cap_on_liability': 11, 'change_of_control': 7, 'governing_law': 3, 'ip_ownership_assignment': 4, 'license_grant': 1, 'non_compete': 9, 'non_transferable_license': 2, 'notice_period_to_terminate_renewal': 10, 'parties': 22, 'renewal_term': 12}
```

*Python here: [`rng.sample`](./py/phase-1d.md#py-2) · `defaultdict`: [0d PY-3](./py/phase-0d.md#py-3)
· `random.Random`: [0d PY-4](./py/phase-0d.md#py-4).*

Here, we read errors from `scores_r1`, so the list stays the same after you rescore. The counts add up
to 87. We take up to 5 from each field, so small fields give all their errors.

Add this cell. `show` prints one error, and `filed_under` gives a hint about its label:

<details><summary>Cell: <code>filed_under</code> and <code>show</code> (open and copy)</summary>

```python
def filed_under(doc_id, quotes):
    """Categories whose gold spans share most words with a quote. A hint, not proof."""
    spans = con.execute(
        "SELECT category, span_text FROM labels WHERE doc_id = ? AND is_present", [doc_id]
    ).fetchall()
    hits = set()
    for category, span in spans:
        s = tokens(span)
        for quote in quotes:
            q = tokens(quote)
            if len(q) >= 4 and len(s) >= 4 and len(q & s) / min(len(q), len(s)) >= 0.6:
                hits.add(category)
    return sorted(hits)


def show(row, width=220):
    field, doc_id, present, found, answer = row
    a = json.loads(answer)
    gold = con.execute(
        "SELECT span_text FROM labels WHERE doc_id = ? AND category = ? AND is_present",
        [doc_id, CUAD_CATEGORY[field]],
    ).fetchall()
    print(f"{field} | {doc_id[:30]} | gold_present={present} found={found}")
    print("  value:", a.get("value"))
    for quote in a["quotes"]:
        print("  quote:", quote[:width])
    for (span,) in gold:
        print("  gold :", span[:width])
    print("  lawyers filed the quote under:", filed_under(doc_id, a["quotes"]))
```

</details>

Checkpoint. Show the errors of one field:

```python
for row in sample:
    if row[0] == "governing_law":
        show(row)
```

```text
governing_law | DYNAMEXINC_06_06_1996-EX-10.4- | gold_present=True found=True
  value: Ontario, Canada
  quote: This Agreement shall be governed and construed in accordance with the laws of the Province of Ontario.
  gold : This Agreement shall be governed and construed in accordance with the         laws of the Province of Ontario.
  lawyers filed the quote under: ['Effective Date', 'Expiration Date', 'Governing Law', 'Insurance']
```

This is the first of three.

The last line is noisy. Other spans can share many words. Use it as a hint only.

Now read all 46. For each one, ask these questions in order, and stop at the first "yes":

| Question | Cause | Who can fix it |
|---|---|---|
| Is the answer right when a person reads it, but marked wrong? | scoring | this part |
| Does the answer fit the field, but the lawyers' labels disagree or contradict each other? | labels | nobody; note it |
| Is the answer wrong, and would a clearer rule in the prompt likely fix it? | prompt | 1d2 |
| Is the contract blank, hidden (`***`), or truly unclear? | hard contract | nobody; note it |

Decide, and write this in a markdown cell before you open the box:

1. A table: one row per field, with a count for each cause.
2. Which scoring rules you think are wrong. Those are the only rules you may change.
3. One error you could not sort easily, and why.

<details><summary>Reference sort of all 87 (open after you decide)</summary>

This is one reader's judgment. Another careful reader would sort a few differently.

| Field | Errors | Scoring | Prompt | Labels | Hard |
|---|---|---|---|---|---|
| parties | 22 | 21 | 0 | 0 | 1 |
| agreement_date | 5 | 3 | 0 | 0 | 2 |
| governing_law | 3 | 3 | 0 | 0 | 0 |
| non_compete | 9 | 0 | 6 | 1 | 2 |
| change_of_control | 7 | 0 | 4 | 2 | 1 |
| anti_assignment | 1 | 0 | 0 | 0 | 1 |
| renewal_term | 12 | 8 | 3 | 1 | 0 |
| notice_period_to_terminate_renewal | 10 | 3 | 4 | 3 | 0 |
| cap_on_liability | 11 | 1 | 6 | 2 | 2 |
| license_grant | 1 | 0 | 0 | 1 | 0 |
| ip_ownership_assignment | 4 | 0 | 3 | 1 | 0 |
| non_transferable_license | 2 | 0 | 1 | 1 | 0 |
| **Total** | **87** | **39** | **27** | **12** | **9** |

Examples:

- **Labels.** `renewal_term` labels disagree. "HSWI shall have the right to renew" is marked. "May be
  renewed ... upon mutual written agreement" is not. For Rae, `answers` says `60 days`, but no span
  is marked for that field.
- **Hard.** One contract has `Signed in September 17, 2008` and a gold date of `18/9/2008`.
- **Prompt.** `non_compete` FPs are often exclusive deals. In 3 of 5 cases, the quote is near text
  that lawyers marked as Exclusivity.

So 39 of 87 errors are the rule's fault. That is why scoring comes first.
</details>

## Step 3: the `governing_law` rule (your decision)

**Why.** The smallest fix comes first. All three errors have a right place and a quote with Jaccard
1.0.

The evidence, as `value` -> CUAD answer:

- `Ontario, Canada` -> `Province of Ontario, Canada`
- `South Africa` -> `Republic of South Africa`
- `California and Hong Kong` -> `California; Hong Kong`

Your options:

1. **Ignore more words, and also accept all the places together.** Small change to `norm_law` and
   `value_ok`.
2. **Pass if the quote matches, even when the value fails.** Very simple. But a wrong value next to a
   right quote then passes.
3. **Use a fuzzy text match on values.** `New York` and `New Jersey` look alike, so this is risky.

Decide, write your rule as one sentence in the notebook, then write it in
`src/docintel/evals/scorers.py`.

<details><summary>Reference rule (open after you decide)</summary>

Add above `norm_law`, then use it inside:

```python
LAW_WORDS = {"the", "state", "of", "laws", "commonwealth", "province", "republic", "and"}


def norm_law(text: str | None) -> str | None:
    """Normalize a place: "the State of New York" -> "new york"."""
    if not text:
        return None
    words = " ".join(sorted(tokens(text) - LAW_WORDS))
    return words or None
```

In `value_ok`, replace the first `golds = ...` line:

```python
    parts = (answer or "").split(";")
    golds = [norm(part) for part in [*parts, " ".join(parts)]]  # each place, or all of them
```

Here, we:

1. Remove two more words that do not name a place, and also `and`.
2. Keep each CUAD part as a right answer. `California` alone still passes.
3. Add all the parts together as one more right answer.
</details>

*Python here: [`[*parts, ...]`](./py/phase-1d.md#py-3).*

Checkpoint. Close the notebook connection, then:

```sh
uv run python -m docintel.evals.runner score 20261102-200003
uv run python -m docintel.evals.runner report 20261102-200003 | grep -E "^(governing_law|all)"
```

With the reference rule:

```text
scored 52 docs for run 20261102-200003
governing_law                          45    0    0  1.00  1.00  1.00
all                                   259   67   54  0.79  0.83  0.81
```

The same `all` row before this step was `256 70 57` with F1 0.80.

## Step 4: the blank date rule (your decision)

**Why.** Three errors say the model missed a date. But the contract has no date to find.

The evidence: in all three, the model says "not found", and the score counts an FN.

| Gold span | CUAD answer |
|---|---|
| `[●]` | none |
| `this  _____ day of _________, 20___` | `[]/[]/20[]` |
| `[●]` | `[]/[]/[][]` |

Your options:

1. **Count nothing.** Finding the blank is fine. Not finding it is also fine.
2. **Treat it as absent.** "Not found" is right. But a model that quotes the blank gets an FP.
3. **Leave it.** Lawyers marked something, so it stays an FN.

There is a trap in the test for "blank". Look at the gold span `03/01/05` (CUAD answer `3/1/05`). It
has no 4-digit year. Is it blank?

Decide and write your rule, then code it in `src/docintel/evals/scorers.py`.

<details><summary>Reference rule (open after you decide)</summary>

Add above `outcome`:

```python
def blank_date(field: str, spans: list[str]) -> bool:
    """A date the lawyers marked in a form, but with no year filled in: "[●]" or "20___"."""
    return (
        field == "agreement_date"
        and bool(spans)
        and not any(re.search(r"\d{4}", span) for span in spans)
    )
```

In `score_doc`, replace the `if rule == "value" ...` block through the `outcome` line:

```python
        if rule == "value" and v_ok is None:
            rule = "blank" if blank_date(field, spans) else "quote"  # no usable CUAD value
        checks = {"presence": True, "quote": q_ok, "value": v_ok, "blank": True}
        correct = checks[rule]
        tp, fp, fn = (0, 0, 0) if rule == "blank" else outcome(present, answer_field.found, correct)
```

Here, we:

1. Check for a blank only when CUAD has no usable value. `3/1/05` has a value, so it never gets here.
2. Check that no gold span has a 4-digit year.
3. For a blank, store `rule = "blank"` and count nothing.
</details>

*Python here: [`re.search(r"\d{4}", ...)`](./py/phase-1d.md#py-4).*

Checkpoint. Close the notebook connection, then:

```sh
uv run python -m docintel.evals.runner score 20261102-200003
uv run python -m docintel.evals.runner report 20261102-200003 | grep -E "^(agreement_date|all)"
```

With the reference rule:

```text
scored 52 docs for run 20261102-200003
agreement_date                         44    2    1  0.96  0.98  0.97
all                                   259   67   51  0.79  0.84  0.81
```

TP stays at 44. Only FN falls: 3 errors are no longer counted.

## Step 5: the quote rule (your decision)

**Why.** Twelve answers quote the right clause but fail Jaccard. This rule affects three fields:
`renewal_term`, `notice_period_to_terminate_renewal` and `cap_on_liability`.

The evidence. Each option ran on the kept run's quotes, and on quotes that must fail:

| Option | Passes on real gold (51) | Passes on the next contract's gold (23) | Passes on other fields' gold (355) |
|---|---|---|---|
| Now: Jaccard >= 0.5 | 37 | 0 | 0 |
| Lower: Jaccard >= 0.25 | 46 | 6 | 2 |
| Overlap >= 0.8 | 49 | 0 | 24 |
| Jaccard >= 0.5, or quote inside span (80% of its words) | 49 | 0 | 0 |

The last two columns are negative controls. Each pass there is a false pass.

The options:

1. **Lower threshold.** One number changes. But it passes quotes from other contracts.
2. **Overlap.** It divides by the smaller text. A whole contract pasted as a quote scores 1.0 against
   any span. (Break 1 shows this.)
3. **Inside.** It divides by the quote's own words. A long quote full of other words fails.
4. **Compare values instead.** CUAD has `successive 1 year` for the model's `1 year`. But this needs
   a parser for lengths of time, and for `cap_on_liability` the CUAD answer is only `Yes`.

Also decide: how many words must a quote have? A word minimum stops `three-year` from passing. On
dev, any minimum from 1 to 4 gives the same results. A minimum of 5 loses one right answer:
`automatically renewing annually thereafter`. So dev cannot fully choose this number.

Decide and write your rule, then code it in `src/docintel/evals/scorers.py`.

<details><summary>Reference rule (open after you decide)</summary>

Add below `THRESHOLD`:

```python
INSIDE = 0.8  # share of a quote's words that must be in the span
MIN_WORDS = 4  # a shorter quote is too small to prove anything
```

Replace `quote_ok` with these two functions:

```python
def inside(quote: str, span: str) -> bool:
    """True if the quote is part of the span: enough words, and nearly all are in the span."""
    q, s = tokens(quote), tokens(span)
    return len(q) >= MIN_WORDS and len(q & s) / len(q) >= INSIDE


def quote_ok(quotes: list[str], spans: list[str]) -> bool:
    """True if any model quote matches a gold span well enough, or is a part of one."""
    return any(jaccard(q, s) >= THRESHOLD or inside(q, s) for q in quotes for s in spans)
```

Here, we:

1. Keep Jaccard, so every old pass stays a pass.
2. Divide by the quote's words only. A long quote fails `inside`.
3. Allow 20% other words, for small differences like a word in brackets.

The minimum of 4 is partly fitted to one dev example. That is a known weakness. Note it in E1.2.
</details>

*Python here: set `&` and `any` with two `for`s are in [1b2 PY-3](./py/phase-1b2.md#py-3) and
[1b2 PY-4](./py/phase-1b2.md#py-4).*

Checkpoint. Close the notebook connection, then:

```sh
uv run python -m docintel.evals.runner score 20261102-200003
uv run python -m docintel.evals.runner report 20261102-200003 | grep -E "^(renewal|notice|cap|all)"
```

With the reference rule:

```text
scored 52 docs for run 20261102-200003
renewal_term                           18    2    2  0.90  0.90  0.90
notice_period_to_terminate_renewal      8    6    1  0.57  0.89  0.70
cap_on_liability                       23    6    6  0.79  0.79  0.79
all                                   271   55   39  0.83  0.87  0.85
```

Guess first: `renewal_term` was the second weakest field. Is it still weak?

## Step 6: the `parties` rule (your decision)

**Why.** This is the largest group: 21 errors with the right names. The `quote` rule compares a
sentence to a name, so it cannot work here.

Your options, with the result on the kept run's 52 contracts:

1. **Compare `value` to the gold spans.** Each name the model gives must match a span. 49 pass. On the
   next contract's gold, 2 of 52 pass, and both are related contracts with the same parties. It cannot
   see a party that the model left out.
2. **Compare `value` to the names in the CUAD answer.** Each CUAD name must be in `value`. It can see
   a missing party. Only 40 of 51 pass, because the answer text has spelling errors like
   `Pifzer Inc.` and pieces like `Party A and Party B`. It needs more text cleaning.
3. **Keep the quote rule, and ask for shorter quotes.** Prompt v1 already asks for names in `quotes`.
   This keeps a broken rule, and needs a new run to test.

Decide and write your rule, then code it in `src/docintel/evals/scorers.py`.

<details><summary>Reference rule (open after you decide)</summary>

In `RULE`, change the `parties` line to:

```python
    "parties": "names",
```

Add below `quote_ok`:

```python
def name_ok(name: str, span: str) -> bool:
    """True if one name holds the other, or they share most words: "Acme" and "Acme, Inc."."""
    a, b = tokens(name), tokens(span)
    return bool(a and b) and (a <= b or b <= a or jaccard(name, span) >= THRESHOLD)


def names_ok(names: list[str], spans: list[str]) -> bool:
    """True if the model gave names, and every one of them matches a gold span."""
    return bool(names) and all(any(name_ok(n, s) for s in spans) for n in names)
```

In `score_doc`, replace the `v_ok = ...` line with:

```python
        v_ok = None
        if rule == "value":
            v_ok = value_ok(field, answer_field.value, answer)
        elif rule == "names":
            v_ok = names_ok(answer_field.value, spans)
```

And add `"names"` to `checks`:

```python
        checks = {"presence": True, "quote": q_ok, "value": v_ok, "names": v_ok, "blank": True}
```

Here, we:

1. Treat a name as right when it holds a gold span, or the span holds it.
2. Also accept a shared-word match, so small spelling errors in the gold can pass.
3. Store the result in `value_ok`. We need no new column.
</details>

*Python here: [`a <= b` on sets](./py/phase-1d.md#py-5) · [`all(any(...))`](./py/phase-1d.md#py-6).*

Checkpoint. Close the notebook connection, then:

```sh
uv run python -m docintel.evals.runner score 20261102-200003
uv run python -m docintel.evals.runner report 20261102-200003
```

With all four reference rules (group rows left out here):

```text
scored 52 docs for run 20261102-200003
                                       tp   fp   fn     P     R    F1
parties                                49    3    3  0.94  0.94  0.94
agreement_date                         44    2    1  0.96  0.98  0.97
governing_law                          45    0    0  1.00  1.00  1.00
non_compete                             9    5    4  0.64  0.69  0.67
change_of_control                       8    5    2  0.62  0.80  0.70
anti_assignment                        40    0    1  1.00  0.98  0.99
renewal_term                           18    2    2  0.90  0.90  0.90
notice_period_to_terminate_renewal      8    6    1  0.57  0.89  0.70
cap_on_liability                       23    6    6  0.79  0.79  0.79
license_grant                          22    1    0  0.96  1.00  0.98
ip_ownership_assignment                10    4    0  0.71  1.00  0.83
non_transferable_license               14    2    0  0.88  1.00  0.93
all                                   290   36   20  0.89  0.94  0.91
```

Read this carefully. The model's answers did not change. Only the ruler changed. Compared with E1.1,
the weakest fields are different now: `non_compete`, `change_of_control` and notice are the problem.
`parties` and `renewal_term` are not.

## Step 7: try to break your rules

**Why.** A kinder rule always raises the score. We must check that it still fails wrong answers.

**Read every flip.** Restart the notebook kernel, so it loads your new `scorers.py`. Open `con`, and run
the imports and `RUN` again. Then:

```python
con.sql("""
SELECT n.field,
    count(*) FILTER (WHERE o.tp = 0 AND n.tp = 1) AS now_right,
    count(*) FILTER (WHERE o.tp = 1 AND n.tp = 0 AND n.fp + n.fn > 0) AS now_wrong,
    count(*) FILTER (WHERE n.tp + n.fp + n.fn = 0) AS not_counted
FROM scores n JOIN scores_r1 o USING (run_id, doc_id, field)
WHERE n.run_id = '20261102-200003' AND (o.tp, o.fp, o.fn) <> (n.tp, n.fp, n.fn)
GROUP BY n.field ORDER BY n.field
""")
```

```text
┌────────────────────────────────────┬───────────┬───────────┬─────────────┐
│               field                │ now_right │ now_wrong │ not_counted │
│              varchar               │   int64   │   int64   │    int64    │
├────────────────────────────────────┼───────────┼───────────┼─────────────┤
│ agreement_date                     │         0 │         0 │           3 │
│ cap_on_liability                   │         1 │         0 │           0 │
│ governing_law                      │         3 │         0 │           0 │
│ notice_period_to_terminate_renewal │         3 │         0 │           0 │
│ parties                            │        21 │         2 │           0 │
│ renewal_term                       │         8 │         0 │           0 │
└────────────────────────────────────┴───────────┴───────────┴─────────────┘
```

*SQL here: [comparing three columns at once](./py/phase-1d.md#py-1).*

Here, we join the new marks to the old ones, and keep only rows that changed. A rule that only says
"yes" more often can never make `now_wrong` above zero. So look at those first.

With the reference rule, the two new wrong answers are:

- `['Astro Nutrition', 'Deep Systems']` against `AstroNutrition.com`. A right answer is now marked
  wrong. The words join differently, so `name_ok` fails. Leave it, and note it.
- `['Nuveen ... Fund', 'Nuveen Fund Advisors, LLC', '[●]']`. The model gave a blank as a name, and left
  out one party. This one is fair.

**Run the negative controls.** These answers must fail:

<details><summary>Cell: negative controls (open and copy)</summary>

```python
from docintel.evals.scorers import names_ok, quote_ok

QUOTE_FIELDS = ["renewal_term", "notice_period_to_terminate_renewal", "cap_on_liability"]
rows = con.execute("SELECT doc_id FROM splits WHERE split = 'dev' ORDER BY doc_id").fetchall()
docs = [doc for (doc,) in rows]


def spans(doc, field):
    rows = con.execute(
        "SELECT span_text FROM labels WHERE doc_id = ? AND category = ? AND is_present",
        [doc, CUAD_CATEGORY[field]],
    ).fetchall()
    return [span for (span,) in rows]


def answers(doc):
    rows = con.execute(
        "SELECT field, answer FROM predictions WHERE run_id = ? AND doc_id = ?", [RUN, doc]
    ).fetchall()
    return {field: json.loads(answer) for field, answer in rows}


tried = passed = 0
for doc in docs:
    pred = answers(doc)
    for field in QUOTE_FIELDS:
        if not pred[field]["found"]:
            continue
        for other in CUAD_CATEGORY:
            gold = spans(doc, other)
            if other not in QUOTE_FIELDS and gold:
                tried += 1
                passed += quote_ok(pred[field]["quotes"], gold)
print(f"quotes against other fields: {passed} of {tried} pass")

tried = passed = 0
for doc, next_doc in zip(docs, docs[1:] + docs[:1]):
    tried += 1
    if names_ok(answers(doc)["parties"]["value"], spans(next_doc, "parties")):
        passed += 1
        print("  ", doc[:32], "->", next_doc[:32])
print(f"names against the next contract: {passed} of {tried} pass")
```

</details>

```text
quotes against other fields: 0 of 355 pass
   KUBIENT,INC_07_02_2020-EX-10.14- -> KUBIENT,INC_07_02_2020-EX-10.14-
   WOMENSGOLFUNLIMITEDINC_03_29_200 -> WOMENSGOLFUNLIMITEDINC_03_29_200
names against the next contract: 2 of 52 pass
```

*Python here: [`zip(docs, docs[1:] + docs[:1])`](./py/phase-1d.md#py-7).*

The cell tests each quote against other fields' gold in the same contract, and each list of names
against the next contract's gold. It prints each pass, so a person can check it. Both passes here are
related contracts with the same parties, so they are not false passes.

**Write down what your rules still cannot see:**

1. **A party left out.** One contract's `value` is `['Agent', 'U.S. Affiliate']`. The real party
   Tribute Pharmaceuticals is missing. It passes under the old rule and the new one, because both
   names match a span.
2. **The `presence` rule.** Of 103 TPs on these fields, 4 have a quote that matches no gold span. At
   least 2 of them cite a different right clause. We leave this rule alone: this part changes rules
   only where a right answer is marked wrong.

## Step 8: rescore every run and check your model choice (your decision)

**Why.** Models can only be compared under the same rule. The rule change may also change the model
decision from 1c4.

Close the notebook connection, then rescore every stored run:

```sh
uv run python -c "
from docintel.evals.runner import score
from docintel.evals.store import connect
with connect() as con:
    rows = con.execute('SELECT DISTINCT run_id FROM predictions ORDER BY run_id').fetchall()
    for (run,) in rows:
        print(run, score(con, run))"
```

```text
1b-example 1
20261101-155906 3
...
20261102-202705 52
```

This makes no LLM calls. It rescores the pilots too, so no old marks stay in `scores`.

Open `con` again, then compare old and new:

```python
RUNS = [
    "20261101-192153",
    "20261102-194826",
    "20261102-200003",
    "20261102-200841",
    "20261102-202705",
]
con.sql("""
WITH s AS (SELECT run_id, sum(tp) AS tp, sum(fp) AS fp, sum(fn) AS fn FROM scores GROUP BY run_id),
o AS (SELECT run_id, sum(tp) AS tp, sum(fp) AS fp, sum(fn) AS fn FROM scores_r1 GROUP BY run_id)
SELECT r.model, round(2 * o.tp / (2 * o.tp + o.fp + o.fn), 3) AS old_f1,
    round(s.tp / (s.tp + s.fp), 3) AS p, round(s.tp / (s.tp + s.fn), 3) AS r,
    round(2 * s.tp / (2 * s.tp + s.fp + s.fn), 3) AS new_f1,
    s.tp::INT AS tp, s.fp::INT AS fp, s.fn::INT AS fn
FROM runs r JOIN s USING (run_id) JOIN o USING (run_id)
WHERE list_contains($runs, run_id) ORDER BY new_f1 DESC
""", params={"runs": RUNS})
```

```text
┌───────────────────────────────────┬────────┬────────┬────────┬────────┬───────┬───────┬───────┐
│               model               │ old_f1 │   p    │   r    │ new_f1 │  tp   │  fp   │  fn   │
│              varchar              │ double │ double │ double │ double │ int32 │ int32 │ int32 │
├───────────────────────────────────┼────────┼────────┼────────┼────────┼───────┼───────┼───────┤
│ deepseek/deepseek-v4-flash        │  0.801 │   0.89 │  0.935 │  0.912 │   290 │    36 │    20 │
│ z-ai/glm-5.3-flash                │  0.782 │  0.868 │  0.958 │  0.911 │   297 │    45 │    13 │
│ qwen/qwen3.8-27b                  │  0.783 │  0.879 │  0.935 │  0.906 │   290 │    40 │    20 │
│ deepseek/deepseek-v4.1-flash-1017 │  0.776 │  0.891 │  0.894 │  0.892 │   277 │    34 │    33 │
│ qwen/qwen3-235b-a22b-2507         │  0.705 │  0.768 │  0.897 │  0.827 │   278 │    84 │    32 │
└───────────────────────────────────┴────────┴────────┴────────┴────────┴───────┴───────┴───────┘
```

Are these gaps real, or luck? The bootstrap in E1.1 was not saved in the repo, so here it is as a cell:

<details><summary>Cell: bootstrap (open and copy)</summary>

```python
def per_doc(run):
    rows = con.execute(
        "SELECT doc_id, sum(tp), sum(fp), sum(fn) FROM scores WHERE run_id = ? GROUP BY doc_id",
        [run],
    ).fetchall()
    return {doc: (tp, fp, fn) for doc, tp, fp, fn in rows}


def f1(counts, docs):
    tp, fp, fn = (sum(counts[d][i] for d in docs) for i in range(3))
    return 2 * tp / (2 * tp + fp + fn)


def gap(run_a, run_b, n=4000, seed=7):
    """F1 of a minus F1 of b, with a 95% range. Re-samples contracts, not single fields."""
    a, b = per_doc(run_a), per_doc(run_b)
    docs = sorted(a)
    rng = random.Random(seed)
    picks = (rng.choices(docs, k=len(docs)) for _ in range(n))
    gaps = sorted(f1(a, pick) - f1(b, pick) for pick in picks)
    low, high = gaps[int(n * 0.025)], gaps[int(n * 0.975)]
    return round(f1(a, docs) - f1(b, docs), 3), round(low, 3), round(high, 3)


OTHERS = {
    "E1": "20261101-192153",
    "Qwen3.8": "20261102-194826",
    "GLM-5.3": "20261102-200841",
    "V4.1": "20261102-202705",
}
for name, other in OTHERS.items():
    print(f"V4 minus {name}:", gap(RUN, other))
```

</details>

```text
V4 minus E1: (0.085, 0.053, 0.118)
V4 minus Qwen3.8: (0.006, -0.012, 0.023)
V4 minus GLM-5.3: (0.001, -0.023, 0.025)
V4 minus V4.1: (0.02, -0.006, 0.055)
```

*Python here: [`rng.choices`](./py/phase-1d.md#py-2).*

Each row is (gap, low end, high end). If the range includes zero, the gap could be luck. The cell picks
52 contracts at random, with repeats, 4,000 times. Both runs use the same picks.

Decide: apply your 1c4 keep rule to this table. Add the cost and p95 from your E1.1 entry. Does the
kept model change? Write your answer in the notebook.

<details><summary>Reference choice (open after you decide)</summary>

The 1c4 rule: F1 at least E1's minus 0.02, and cheaper or faster at p95; if several pass, the cheapest.

- Qwen3.8 fails: it costs more than E1 ($0.883) and is slower (p95 209.8 s).
- V4 ($0.204), GLM-5.3 ($0.213) and V4.1 ($0.381) pass, because they are faster than E1.
- V4 is the cheapest of those, so **V4 stays**.

GLM-5.3 is worth noting. Its recall is higher (0.958 against 0.935), its precision lower. The F1 gap
could be zero, so the data does not separate them. A product that cares most about not missing clauses
could fairly prefer GLM-5.3.
</details>

## Step 9: tests for the new rules

**Why.** A rule can go wrong later without anyone seeing it. A failing test will say so.

Write tests for your rules in `tests/test_scorers.py`. Each rule needs a case it must pass, and a case
it must fail. Write yours first, then compare.

<details><summary>Reference tests (open after you write yours)</summary>

Update the imports at the top of `tests/test_scorers.py`:

```python
from docintel.evals.scorers import (
    blank_date,
    inside,
    jaccard,
    names_ok,
    norm_date,
    outcome,
    quote_ok,
    score_doc,
    value_ok,
)
```

Add to the bottom of `tests/test_scorers.py`:

```python
GOLD_SENTENCE = (
    "this Agreement shall automatically renew for successive additional three-year terms"
)


def test_inside_needs_enough_words_from_the_span():
    assert inside("automatically renew for successive additional", GOLD_SENTENCE)
    assert not inside("three-year", GOLD_SENTENCE)  # too short to prove anything
    assert not inside(LAW + " " + GOLD_SENTENCE, GOLD_SENTENCE)  # a long quote is not "inside"
    assert quote_ok(["automatically renew for successive additional"], [GOLD_SENTENCE])


def test_names_must_all_match_a_gold_span():
    spans = ["2THEMART.COM, INC.", "I-ESCROW, INC.", "i-Escrow", "2TheMart"]
    assert names_ok(["I-ESCROW, INC.", "2THEMART.COM, INC."], spans)
    assert names_ok(["I-Escrow"], spans)  # one name is enough: this rule cannot see a missing party
    assert not names_ok(["I-ESCROW, INC.", "Acme Corp."], spans)
    assert not names_ok([], spans)


def test_blank_date_is_only_a_date_with_no_year():
    assert blank_date("agreement_date", ["[●]"])
    assert blank_date("agreement_date", ["this _____ day of _________, 20___"])
    assert not blank_date("agreement_date", ["June 21, 1999"])
    assert not blank_date("agreement_date", [])
    assert not blank_date("governing_law", ["[●]"])


@pytest.mark.parametrize(
    ("value", "answer", "expected"),
    [
        ("Ontario, Canada", "Province of Ontario, Canada", True),
        ("South Africa", "Republic of South Africa", True),
        ("California and Hong Kong", "California; Hong Kong", True),
        ("California", "California; Hong Kong", True),
        ("Delaware", "California; Hong Kong", False),
    ],
)
def test_governing_law_values(value, answer, expected):
    assert value_ok("governing_law", value, answer) is expected
```
</details>

Here, we test what each rule must pass and must fail. There is no network and no CUAD file, like the
other tests in this file.

Checkpoint:

```sh
make test
make lint
```

```text
43 passed
All checks passed!
```

Your output has more lines than this. Check for these two. If `make lint` says the notebook needs
reformatting, see Gotchas.

The files changed are the ones listed in Project setup. Two tables hold the marks: `scores` (new rules)
and `scores_r1` (old rules).

<details><summary>Full <code>src/docintel/evals/scorers.py</code> with the reference rules</summary>

```python
"""Score one contract's extracted fields against the CUAD gold labels. Rules are 1b2 decisions."""

import re

import duckdb

from docintel.domain.schema.fields import CUAD_CATEGORY, ContractFields
from docintel.evals.datasets import FIELDS

THRESHOLD = 0.5  # token Jaccard needed for a quote to match a gold span (the CUAD paper uses 0.5)

INSIDE = 0.8  # share of a quote's words that must be in the span
MIN_WORDS = 4  # a shorter quote is too small to prove anything

RULE = {  # field -> how a found answer is judged correct
    "agreement_date": "value",
    "governing_law": "value",
    "parties": "names",
    "renewal_term": "quote",
    "notice_period_to_terminate_renewal": "quote",
    "cap_on_liability": "quote",
}  # every other field: "presence"


def tokens(text: str) -> set[str]:
    """Lowercase words and numbers, as a set."""
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def jaccard(a: str, b: str) -> float:
    """Shared tokens / all tokens. 1.0 = same words, 0.0 = no word in common."""
    ta, tb = tokens(a), tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def inside(quote: str, span: str) -> bool:
    """True if the quote is part of the span: enough words, and nearly all are in the span."""
    q, s = tokens(quote), tokens(span)
    return len(q) >= MIN_WORDS and len(q & s) / len(q) >= INSIDE


def quote_ok(quotes: list[str], spans: list[str]) -> bool:
    """True if any model quote matches a gold span well enough, or is a part of one."""
    return any(jaccard(q, s) >= THRESHOLD or inside(q, s) for q in quotes for s in spans)


def name_ok(name: str, span: str) -> bool:
    """True if one name holds the other, or they share most words: "Acme" and "Acme, Inc."."""
    a, b = tokens(name), tokens(span)
    return bool(a and b) and (a <= b or b <= a or jaccard(name, span) >= THRESHOLD)


def names_ok(names: list[str], spans: list[str]) -> bool:
    """True if the model gave names, and every one of them matches a gold span."""
    return bool(names) and all(any(name_ok(n, s) for s in spans) for n in names)


def norm_date(text: str | None) -> str | None:
    """CUAD "11/14/17" or model "2017-11-14" -> "2017-11-14". Unknown parts are left out."""
    text = (text or "").strip()
    if "/" in text:  # CUAD: month/day/year, "[]" for an unknown part
        month, day, year = (text.split("/") + ["", ""])[:3]
        if len(year) == 2 and year.isdigit():
            year = ("19" if int(year) > 30 else "20") + year
        parts = [year, month.zfill(2), day.zfill(2)]
    else:  # model: YYYY, YYYY-MM or YYYY-MM-DD
        parts = text.split("-")
    known = []
    for part in parts:  # keep parts until the first unknown one
        if not part.isdigit():
            break
        known.append(part)
    if not known or len(known[0]) != 4:
        return None  # no year, nothing to compare
    return "-".join(known)


LAW_WORDS = {"the", "state", "of", "laws", "commonwealth", "province", "republic", "and"}


def norm_law(text: str | None) -> str | None:
    """Normalize a place: "the State of New York" -> "new york"."""
    if not text:
        return None
    words = " ".join(sorted(tokens(text) - LAW_WORDS))
    return words or None


def value_ok(field: str, value: str | None, answer: str | None) -> bool | None:
    """Compare a normalized value with the CUAD answer. None if the answer has no usable value."""
    norm = norm_date if field == "agreement_date" else norm_law
    parts = (answer or "").split(";")
    golds = [norm(part) for part in [*parts, " ".join(parts)]]  # each place, or all of them
    golds = [g for g in golds if g]
    if not golds:
        return None
    return norm(value) in golds


def blank_date(field: str, spans: list[str]) -> bool:
    """A date the lawyers marked in a form, but with no year filled in: "[●]" or "20___"."""
    return (
        field == "agreement_date"
        and bool(spans)
        and not any(re.search(r"\d{4}", span) for span in spans)
    )


def outcome(gold_present: bool, found: bool, correct: bool) -> tuple[int, int, int]:
    """(tp, fp, fn) for one field of one contract. A wrong answer counts as fp and fn."""
    if not gold_present:
        return (0, 1, 0) if found else (0, 0, 0)
    if not found:
        return (0, 0, 1)
    return (1, 0, 0) if correct else (0, 1, 1)


GOLD = """
SELECT l.category, bool_or(l.is_present) AS present,
    list(l.span_text) FILTER (WHERE l.is_present) AS spans, any_value(a.answer) AS answer
FROM labels l LEFT JOIN answers a USING (doc_id, category)
WHERE l.doc_id = ?
GROUP BY l.category
"""


def score_doc(con: duckdb.DuckDBPyConnection, doc_id: str, pred: ContractFields) -> list[dict]:
    """One row per field: the rule used, the checks, and tp/fp/fn."""
    gold = {
        cat: (present, spans or [], answer)
        for cat, present, spans, answer in con.execute(GOLD, [doc_id]).fetchall()
    }
    rows = []
    for field, category in CUAD_CATEGORY.items():
        present, spans, answer = gold[category]
        answer_field = getattr(pred, field)
        rule = RULE.get(field, "presence")
        q_ok = quote_ok(answer_field.quotes, spans)
        v_ok = None
        if rule == "value":
            v_ok = value_ok(field, answer_field.value, answer)
        elif rule == "names":
            v_ok = names_ok(answer_field.value, spans)
        if rule == "value" and v_ok is None:
            rule = "blank" if blank_date(field, spans) else "quote"  # no usable CUAD value
        checks = {"presence": True, "quote": q_ok, "value": v_ok, "names": v_ok, "blank": True}
        correct = checks[rule]
        tp, fp, fn = (0, 0, 0) if rule == "blank" else outcome(present, answer_field.found, correct)
        rows.append(
            {
                "field": field,
                "rule": rule,
                "gold_present": present,
                "found": answer_field.found,
                "quote_ok": q_ok,
                "value_ok": v_ok,
                "tp": tp,
                "fp": fp,
                "fn": fn,
            }
        )
    return rows


GROUPS = {  # group -> its fields, from the 0d groups in datasets.FIELDS
    group: [field for field, category in CUAD_CATEGORY.items() if category in categories]
    for group, categories in FIELDS.items()
}


def prf(tp: int, fp: int, fn: int) -> dict:
    """Precision, recall and F1. None when there is nothing to divide by."""
    return {
        "precision": tp / (tp + fp) if tp + fp else None,
        "recall": tp / (tp + fn) if tp + fn else None,
        "f1": 2 * tp / (2 * tp + fp + fn) if tp + fp + fn else None,
    }


PER_FIELD = "SELECT field, sum(tp), sum(fp), sum(fn) FROM scores WHERE run_id = ? GROUP BY field"


def metrics(con: duckdb.DuckDBPyConnection, run_id: str) -> list[dict]:
    """P/R/F1 for each field, each group, and all fields. A group adds up its fields' counts."""
    counts = {f: (tp, fp, fn) for f, tp, fp, fn in con.execute(PER_FIELD, [run_id]).fetchall()}
    sets = {field: [field] for field in CUAD_CATEGORY} | GROUPS | {"all": list(CUAD_CATEGORY)}
    rows = []
    for name, fields in sets.items():
        tp = sum(counts[f][0] for f in fields)
        fp = sum(counts[f][1] for f in fields)
        fn = sum(counts[f][2] for f in fields)
        rows.append({"name": name, "tp": tp, "fp": fp, "fn": fn, **prf(tp, fp, fn)})
    return rows
```
</details>

<details><summary>Full <code>tests/test_scorers.py</code> with the reference rules</summary>

```python
"""Scoring rules on tiny hand-made cases. No network, no CUAD files."""

import pytest

from docintel.domain.schema.fields import CUAD_CATEGORY, ContractFields, Names
from docintel.evals.scorers import (
    blank_date,
    inside,
    jaccard,
    names_ok,
    norm_date,
    outcome,
    quote_ok,
    score_doc,
    value_ok,
)
from docintel.evals.store import connect

LAW = "This Agreement shall be governed by the laws of the State of Michigan."


def test_jaccard():
    assert jaccard(LAW, LAW.upper()) == 1.0
    assert jaccard("Michigan", "Delaware") == 0.0
    assert jaccard("", LAW) == 0.0


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("11/14/17", "2017-11-14"),
        ("2017-11-14", "2017-11-14"),
        ("[]/[]/2020", "2020"),
        ("4/1/98", "1998-04-01"),
        ("[]/[]/[]", None),
        (None, None),
    ],
)
def test_norm_date(text, expected):
    assert norm_date(text) == expected


def test_outcome_table():
    assert outcome(gold_present=False, found=False, correct=True) == (0, 0, 0)  # true negative
    assert outcome(gold_present=False, found=True, correct=True) == (0, 1, 0)
    assert outcome(gold_present=True, found=False, correct=True) == (0, 0, 1)
    assert outcome(gold_present=True, found=True, correct=True) == (1, 0, 0)
    assert outcome(gold_present=True, found=True, correct=False) == (0, 1, 1)


def absent(cls) -> dict:
    """An empty answer for one field model."""
    data = {"quotes": [], "found": False}
    if "value" in cls.model_fields:
        data["value"] = [] if cls is Names else None
    return data


def test_score_doc_counts_absent_fields():
    """Gold: only Governing Law is present. The model finds it, and a non-compete that is absent."""
    pred = {f: absent(info.annotation) for f, info in ContractFields.model_fields.items()}
    pred["governing_law"] = {"quotes": [LAW], "value": "Michigan", "found": True}
    pred["non_compete"] = {"quotes": ["shall not compete"], "found": True}
    with connect(":memory:") as con:
        con.execute(
            "CREATE TABLE labels (doc_id TEXT, category TEXT, span_text TEXT, is_present BOOL)"
        )
        con.execute("CREATE TABLE answers (doc_id TEXT, category TEXT, answer TEXT)")
        for category in CUAD_CATEGORY.values():
            present = category == "Governing Law"
            span = LAW if present else None
            con.execute("INSERT INTO labels VALUES ('d1', ?, ?, ?)", [category, span, present])
        con.execute("INSERT INTO answers VALUES ('d1', 'Governing Law', 'Michigan')")
        rows = {r["field"]: r for r in score_doc(con, "d1", ContractFields.model_validate(pred))}
    assert (rows["governing_law"]["tp"], rows["governing_law"]["value_ok"]) == (1, True)
    assert rows["non_compete"]["fp"] == 1
    assert sum(r["tp"] + r["fp"] + r["fn"] for r in rows.values()) == 2  # 10 true negatives


GOLD_SENTENCE = (
    "this Agreement shall automatically renew for successive additional three-year terms"
)


def test_inside_needs_enough_words_from_the_span():
    assert inside("automatically renew for successive additional", GOLD_SENTENCE)
    assert not inside("three-year", GOLD_SENTENCE)  # too short to prove anything
    assert not inside(LAW + " " + GOLD_SENTENCE, GOLD_SENTENCE)  # a long quote is not "inside"
    assert quote_ok(["automatically renew for successive additional"], [GOLD_SENTENCE])


def test_names_must_all_match_a_gold_span():
    spans = ["2THEMART.COM, INC.", "I-ESCROW, INC.", "i-Escrow", "2TheMart"]
    assert names_ok(["I-ESCROW, INC.", "2THEMART.COM, INC."], spans)
    assert names_ok(["I-Escrow"], spans)  # one name is enough: this rule cannot see a missing party
    assert not names_ok(["I-ESCROW, INC.", "Acme Corp."], spans)
    assert not names_ok([], spans)


def test_blank_date_is_only_a_date_with_no_year():
    assert blank_date("agreement_date", ["[●]"])
    assert blank_date("agreement_date", ["this _____ day of _________, 20___"])
    assert not blank_date("agreement_date", ["June 21, 1999"])
    assert not blank_date("agreement_date", [])
    assert not blank_date("governing_law", ["[●]"])


@pytest.mark.parametrize(
    ("value", "answer", "expected"),
    [
        ("Ontario, Canada", "Province of Ontario, Canada", True),
        ("South Africa", "Republic of South Africa", True),
        ("California and Hong Kong", "California; Hong Kong", True),
        ("California", "California; Hong Kong", True),
        ("Delaware", "California; Hong Kong", False),
    ],
)
def test_governing_law_values(value, answer, expected):
    assert value_ok("governing_law", value, answer) is expected
```
</details>

## Break it on purpose

Guess first, then open. Undo each change afterwards.

**Break 1: use a whole contract as the quote.** Compare Jaccard, overlap and `inside`:

```python
from docintel.evals.runner import cuad_txt
from docintel.evals.scorers import inside, jaccard

text = cuad_txt(con, docs[0])
span = "2THEMART.COM, INC."
a, b = tokens(text), tokens(span)
print(round(jaccard(text, span), 3), len(a & b) / min(len(a), len(b)), inside(text, span))
```

<details><summary>Guess, then open</summary>

```text
0.003 1.0 False
```

Overlap passes, because every word of the small span is in the contract. A model could pass any field
by quoting everything. `inside` divides by the quote's own words, so it fails.
</details>

**Break 2: set `MIN_WORDS = 1`.** What happens to the report? What happens to the tests?

<details><summary>Guess, then open</summary>

The report does not change at all, because the dev quotes are all long enough. But one test fails:

```text
>       assert not inside("three-year", GOLD_SENTENCE)  # too short to prove anything
E       AssertionError: assert not True
FAILED tests/test_scorers.py::test_inside_needs_enough_words_from_the_span
```

Dev data cannot defend this minimum. Only the test and your reasoning do. Some rules protect against
answers that have not appeared yet.
</details>

**Break 3: check for a blank date first.** In `score_doc`, change the check so `blank_date` runs for
every date, before looking at `v_ok`.

<details><summary>Guess, then open</summary>

```text
agreement_date                         43    2    1  0.96  0.98  0.97
all                                   289   36   20  0.89  0.94  0.91
```

A TP is lost. The real date `03/01/05` has no 4-digit year, so it now counts as blank. This bug came up
while the reference rule was being tested. Reading the flips caught it: `not_counted` was 4, not 3.
</details>

Rescore the kept run after you undo each break.

## Experiment

This is E1.2. It makes no LLM calls and creates no new `run_id`. Each run keeps its id, and only its
marks change. The command is the rescore in Step 8.

Expect this table shape: one row per model, with `model`, `old_f1`, `p`, `r`, `new_f1`, `tp`, `fp` and
`fn`. Dev only: never run this on `--split test` to choose a rule.

Add this to `EXPERIMENTS.md`:

```markdown
## E1.2: scoring rules fixed, no new LLM calls
- **Date:**
- **run_id(s):** 20261102-200003 (V4), 20261102-194826 (Qwen3.8), 20261102-200841 (GLM-5.3),
  20261102-202705 (V4.1), 20261101-192153 (E1). Same runs, new marks. Old marks: table `scores_r1`,
  rules at commit f8a2f10.
- **Question / hypothesis:** How many of the 87 errors are the rule's fault? Do the weak fields or the
  model choice change?
- **Data:** dev, 52 contracts, 12 fields, stored answers from E1 and E1.1. No new calls, $0.
- **Setup:** only the scoring rules change. Rules changed: <your rules, one line each>.
- **Error sort:** <sample size, seed, your table of causes>.
- **Results:** the old and new F1 table, the bootstrap gaps, and the new V4 per-field table.
- **Limits:** dev-fitted rules. Only errors were read closely, so fixes mostly raise the score. <what
  your rules cannot see, from Step 7>. Word minimum not proven by dev data.
- **Conclusion:** the model kept, and the fields that are still weak, with numbers.
- **Next step:** 1d2, prompt v2 for the weak fields, on these rules (E1.3).
```

Also add one line to the E1 and E1.1 entries, so their numbers stay honest:

```markdown
- **Note:** these numbers use the old rules (commit f8a2f10, table `scores_r1`). See E1.2.
```

## Gotchas

- **The database is locked.** DuckDB allows one writer. Close the notebook connection before each
  `score`. The error says `Could not set lock on file`.
- **The notebook uses old code.** Python loads `scorers.py` once. Restart the kernel after each change.
- **`make lint` complains about the notebook.** It already needs reformatting before this part. Run
  `make fmt`, then check the notebook still works.
- **`report` no longer matches E1.** That is expected after a rescore. Old numbers are in `scores_r1`.
- **0.91 is not a final score.** You wrote these rules while reading dev errors. Only the test split, at
  the end of the project, gives an honest number.
- **Do not fix a contract one at a time.** A rule like "accept `Astro Nutrition`" fits one example and
  teaches nothing. A rule must describe a kind of answer.

## Explain back, then commit

Explain to Claude in a few sentences (the rule in `PLAN.md`):

- Your cause table, and one error that was hard to sort.
- Each rule you changed: which right answers it frees, and which wrong answers it still fails.
- Why the score rising does not prove the pipeline got better.
- What your rules cannot see.

Then:

```sh
git status
git add src/docintel/evals/scorers.py tests/test_scorers.py notebooks/00_explore.ipynb EXPERIMENTS.md
git commit -m "phase 1d: scoring review and rule fixes (E1.2)"
```

## Conclusion

What you have now:

- A sorted list of errors, by cause, in your notebook.
- Fairer scoring rules, with tests and negative controls.
- E1.2: the same five runs under the new rules, with the old marks kept.
- A checked model decision, and a new list of weak fields for 1d2.

Go back to the objectives. Check that you can do each one without notes. Then answer:

1. Why would a prompt rule for `parties` have been wasted work?
2. A teammate's rule change raises F1 by 0.10. What two things do you check before you believe it?

Want more practice? Try these (optional):

1. Read 10 random TPs from `parties`. How many are really right? This looks for false passes directly.
2. Add a second check to `names_ok` that can see a missing party. What does it do to the negative
   control and to the F1?
3. Sort the errors of GLM-5.3 the same way. Are the causes the same?

Checklist (`../PLAN.md`): **Precision/recall/F1 per field; span scoring** (deepened: inside, names, and
negative controls for scoring rules). **Experiments: run_id, one change at a time, cost, p50/p95**
(deepened: rules change alone, with no new calls; bootstrap ranges on gaps).
