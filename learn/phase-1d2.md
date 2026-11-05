# Phase 1d2: prompt v2 and a fair test (E1.3)

In this part, you write prompt v2 for the fields that are still weak. You also write the rule that
decides if v2 stays. You write that rule before the run. Then you run v2 on dev and apply your rule.

This is part 2 of 2 for Phase 1d. It uses the E1.2 rules from part 1, and it does not change them.

## Words used in this part

Read these first. TP, FP, FN and flip are from earlier parts.

- **Target field**: a field your v2 rules try to change. Example: `cap_on_liability`.
- **Check field**: a field your rules do not touch. It should stay about the same.
- **Keep rule**: the test v2 must pass, written before the run. Example: F1 goes up by at least 0.015.
- **Noise**: the change you get from running the same prompt twice. Example: 5 of 228 marks changed.
- **Ceiling**: the best score a change could reach. Example: fixing all 23 prompt errors gives F1 0.951.
- **Wrong-quote TP**: a `presence` field marked TP, but its quote matches no gold span. Example: the
  model says a clause exists and quotes the wrong one.
- **Frozen**: never edited again. Stored runs name `v1`, so `v1` must always mean the same text.
- **Pilot**: a cheap run on a few contracts, to check that the setup works. From 1c2.

## Objectives

By the end of this part you should be able to:

1. Read errors and right answers together, and write a prompt rule that keeps the right answers.
2. Say which errors a prompt can never fix.
3. Measure noise from stored runs, with no new cost.
4. Write a keep rule before a run, and defend each number in it.
5. Run one prompt change, read every flip, and apply your rule as you wrote it.

## Dependencies

You install nothing new. This part needs:

- 1b: versioned prompts in `src/docintel/domain/extract/prompts/`. A new folder needs no new code.
- 1c2: `run --prompt-version`, `--model`, `--limit`, and resume.
- 1d: your E1.2 rules, and the cells `filed_under`, `per_doc`, `f1` and `gap` in your notebook.

The reference numbers use the kept run under the E1.2 rules: TP 290, FP 36, FN 20. Step 1 checks this.

## The big picture

Before this part, the kept run has F1 0.912 on the fairer rules. It has 50 errors. Prompt v1 was
written before anyone had read an error.

After this part:

- `prompts/v2/` exists, and `v1` is unchanged.
- E1.3 says if v2 stays, by a rule written before the run.
- 2a knows which prompt is the baseline for its validators.

This is the first change in the project that tries to make the answers better. 1d changed only the
ruler.

## Remember this

> A prompt rule fixes some errors and can break some right answers. So read both before you write it.
> Decide what counts as a win before the run, because after the run you will want to win.
>
> **Write the rule first, then run.**

## Why

**The same dev errors shaped the rules.** You read dev errors, wrote rules for them, and test on dev.
So some gain is expected even from a weak rule. A clear keep rule stops you from fooling yourself. Only
the test split, at the end of the project, gives the honest number.

**Running twice does not give the same answers.** Temperature 0 does not make these runs repeat. So a
small gain could be luck. You need to know the size of that luck first.

**A prompt cannot fix a label.** Some errors are clauses that lawyers marked in one contract and not in
another. No rule can match both. If you chase them, you add rules that fit noise.

## Design decisions

- **One folder, with all the rules.** The plan asks for one v2 folder. Each rule talks about one field,
  so the per-field table shows what each rule did. Other option: one folder and one run per rule. That
  is cleaner, but costs one full run per rule.
- **What "one change" means here.** Only the prompt changes. Model, parser, data and scoring rules stay
  the same. Check fields warn you if a rule leaks into other fields.
- **`v1` is frozen.** Any edit after a run is a new version. Other option: edit `v1` in place and rely
  on git. Then the run table says `v1` for two different prompts.
- **No snapshot this time.** 1d changed marks in place, so it needed `scores_r1`. A v2 run gets a new
  `run_id`, so the v1 marks stay as they are.
- **Scoring stays frozen.** If you find a scoring problem, write it down for later. Changing both at
  once means you cannot tell which one moved the score.

## Worked example

Real rows from the kept run. Each one is a trap for a prompt rule.

### Round 1: a rule that looks obvious

`non_compete` has 5 FPs. In 3 of them, the lawyers filed the quote under Exclusivity. So you write: "An
exclusive deal does not count." Now read this TP from the Remark contract:

`World Book shall work exclusively with HSWI to publish Chinese language Content for the Open Free Web
and shall not itself, directly or indirectly, publish Chinese language Content ...`

What does your rule do to it?

<details><summary>Guess, then open</summary>

It may turn this TP into an FN. Lawyers marked this one as Non-Compete, and it says "exclusively". The
useful difference is smaller. Here, a party promises to work only with the other party. In the iVillage
FP, Ford is just the only sponsor of its type. You only see this if you read the right answers too.
</details>

### Round 2: two clauses, two marks

`change_of_control`. Guess which one the lawyers marked:

- Accuray: `this Agreement may be assigned by a Party in connection with a Change in Control of such
  party`
- Conformis: `either Party shall be permitted ... to assign this Agreement ... to a Third Party in
  connection with sale or transfer of all or substantially all of the assigning Party's business or
  assets ..., whether by Change of Control, merger, sale of assets or otherwise`

Can a prompt rule get both right?

<details><summary>Guess, then open</summary>

Conformis is marked. Accuray is not. Both let a party assign the contract when control changes. Any rule
that accepts one should accept the other. So this error is a label problem, and a prompt cannot fix it.
</details>

### Round 3: a count that looks scary

You want `cap_on_liability` to count bans on "indirect or consequential damages". You search the
contracts for those words. They are in 27 of 29 contracts with a gold cap, but also in 10 of 23 with no
gold cap. So the rule may add up to 10 FPs. Should you drop the rule?

<details><summary>Guess, then open</summary>

Not yet. Read the matches first. The search also matches `directly or indirectly`, which has nothing to
do with damages. When the words must come before "damages" or "loss", the count is 25 of 29 and 1 of 23.
That one contract is already an FP. The first draft of this doc made this exact mistake. A count is only
as good as the pattern behind it.
</details>

## Project setup

You change or create these:

```text
├── notebooks/00_explore.ipynb                     + review and comparison cells
├── src/docintel/domain/extract/prompts/v2/        new: system.md and user.md
├── tests/test_extract.py                          + two small tests
└── EXPERIMENTS.md                                 + E1.3, and the E1.2 hash
```

Open `con` in your notebook as you did in 1d, and run your 1d cells for `filed_under`, `per_doc`, `f1` and
`gap`. Add these imports:

```python
import json
import random
import re
from collections import defaultdict
from pathlib import Path

from docintel.domain.schema.fields import CUAD_CATEGORY
from docintel.evals.runner import from_rows
from docintel.evals.scorers import metrics, score_doc, tokens

RUN = "20261102-200003"  # V4 Flash, prompt v1, E1.2 marks
```

## Step 1: check the starting point

**Why.** v2 is compared with this run, so its marks must be the ones you logged in E1.2.

Run this in your notebook:

```python
con.sql(
    "SELECT sum(tp) AS tp, sum(fp) AS fp, sum(fn) AS fn FROM scores WHERE run_id = $run",
    params={"run": RUN},
)
```

```text
┌────────┬────────┬────────┐
│   tp   │   fp   │   fn   │
│ int128 │ int128 │ int128 │
├────────┼────────┼────────┤
│    290 │     36 │     20 │
└────────┴────────┴────────┘
```

Now check that the rules did not move since then:

```sh
git diff --stat HEAD -- src/docintel/evals/scorers.py
git log -1 --format=%h -- src/docintel/evals/scorers.py
```

```text
6ffdaa7
```

The first command prints nothing, because the file has no changes. Your E1.2 entry still says
`not committed yet`. Replace that with this hash. E1.3 will use the same one.

## Step 2: read errors and right answers (your decision)

**Why.** Errors show what a rule could fix. Right answers show what it could break.

Here is the current state of each field:

```sh
uv run python -m docintel.evals.runner report 20261102-200003
```

```text
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
...
all                                   290   36   20  0.89  0.94  0.91
52 calls, $0.2043, p50 31.0 s, p95 57.5 s, 0 bad answers
```

Close the database connection in the notebook before you run this command, then open it again.

Add this cell. It shows every counted answer of one field, errors first:

<details><summary>Cell: <code>review</code> (open and copy)</summary>

```python
ROWS = """
SELECT s.doc_id, s.tp, s.fp, s.fn, p.answer
FROM scores s JOIN predictions p USING (run_id, doc_id, field)
WHERE s.run_id = ? AND s.field = ? AND s.tp + s.fp + s.fn > 0
ORDER BY s.tp, s.doc_id
"""
GOLD = "SELECT span_text FROM labels WHERE doc_id = ? AND category = ? AND is_present"


def review(field, run=RUN, width=160):
    """Every counted answer of one field: the errors first, then the right answers."""
    for doc_id, tp, fp, fn, answer in con.execute(ROWS, [run, field]).fetchall():
        quotes = json.loads(answer)["quotes"]
        mark = "RIGHT" if tp else "FP+FN" if fp and fn else "FP" if fp else "FN"
        print(f"{mark:5} {doc_id[:28]} {filed_under(doc_id, quotes)}")
        for quote in quotes:
            print("      quote:", quote[:width])
        if fn:
            spans = con.execute(GOLD, [doc_id, CUAD_CATEGORY[field]]).fetchall()
            print("      gold :", spans[0][0][:width])
```

</details>

*Python here: [the chained `if ... else`](./py/phase-1d2.md#py-1), [`{mark:5}`](./py/phase-1d2.md#py-2).*

Checkpoint:

```python
review("non_compete")
```

```text
FN    2ThemartComInc_19990826_10-1 []
      gold : i-Escrow shall not run banner advertisements on the Co-Branded Site for any of 2TheMart's competitors.
FP    ConformisInc_20191101_10-Q_E ['Affiliate License-Licensee', 'Competitive Restriction Exception', 'Exclusivity']
      quote: Conformis shall be prohibited from developing or assisting another in developing, or causing another to develop, Patient-Specific Instrumentation for Off-The-Sh
FP    EuromediaHoldingsCorp_200702 ['Most Favored Nation']
      quote: Licensor shall not authorize the distribution or exhibition of any Licensed Program by any other means, including, without limitation, television (other than PP
...
RIGHT RemarkHoldingsInc_20081114_1 ['Exclusivity', 'Rofr/Rofo/Rofn']
      quote: Commencing on the Effective Date and continuing for eighteen (18) months, World Book shall work exclusively with HSWI to publish Chinese language Content for th
```

This field has 18 counted answers. The list in brackets is the hint from 1d.

Decide:

1. Run `review` for each field under 0.90 F1, plus any other field you want.
2. Start from the causes you logged in 1d. Check them again now that you see right answers too.
3. Write your list of target fields in the notebook. Leaving a weak field out is a fair choice.

<details><summary>Reference sort of the 50 errors left (open after you decide)</summary>

This is one reader's judgment. Another careful reader would sort a few differently. Newly wrong means an
E1.2 rule made the mark wrong.

| Field | Errors | Prompt | Labels | Hard | Newly wrong |
|---|---|---|---|---|---|
| non_compete | 9 | 4 | 3 | 2 | 0 |
| change_of_control | 7 | 2 | 4 | 1 | 0 |
| notice_period_to_terminate_renewal | 7 | 4 | 3 | 0 | 0 |
| cap_on_liability | 10 | 6 | 2 | 2 | 0 |
| ip_ownership_assignment | 4 | 3 | 1 | 0 | 0 |
| renewal_term | 4 | 3 | 1 | 0 | 0 |
| non_transferable_license | 2 | 1 | 1 | 0 | 0 |
| parties | 3 | 0 | 0 | 1 | 2 |
| agreement_date | 2 | 0 | 0 | 2 | 0 |
| anti_assignment | 1 | 0 | 0 | 1 | 0 |
| license_grant | 1 | 0 | 1 | 0 | 0 |
| **Total** | **50** | **23** | **16** | **9** | **2** |

This table differs from the 1d reference sort. After reading right answers, four errors moved from prompt
to labels:

- `non_compete`: Conformis and Pareteum. They read like real bans.
- `change_of_control`: Blackstone (a party may end the contract if the other is merged), and Remark (like
  the marked Conformis clause).

So a cause can change when you read more. Reference target fields: `non_compete`,
`notice_period_to_terminate_renewal`, `cap_on_liability` and `ip_ownership_assignment`. Together they hold
17 of the 23 prompt errors.

Left out, on purpose:

- `change_of_control`: F1 is low, but 4 of 7 errors are label conflicts (Round 2).
- `renewal_term`: F1 is already 0.90, and its labels disagree. Flotek's choice to extend is not marked.
  Remark's right to renew is marked.
- `non_transferable_license`: one prompt error is too few for a rule.
</details>

## Step 3: write a rule for each target field (your decision)

**Why.** A rule must describe a kind of clause. It must not describe one contract.

Each rule below has errors it could fix and right answers it must keep. Use `review` to read them in full.

| Field | Errors to fix | Right answers to keep | Tempting rule that goes too far |
|---|---|---|---|
| `notice_period...` | Integrity, Kubient, Optimized, Rae: a right to end the contract with notice | 2Themart: notice *to renew*. Euromedia: notice to end the term "as so extended" | "Only notice that stops a renewal" |
| `non_compete` | iVillage, Euromedia FPs. 2Themart, Tube FNs: bans on dealing with competitors | Remark: "work exclusively" | "Exclusivity never counts" |
| `cap_on_liability` | Tuniu, USA FNs. Kubient, Tube: quoted a time limit, gold is a damages ban. Arca, Borrow FPs: "not liable unless ..." | Time limits in Pareteum and TriCity | "Only money limits count" |
| `ip_ownership...` | Eco, Remark, TriCity FPs: a party keeps its own work | Tuniu: "shall be owned by Party B". Coral: "will be the sole and absolute property". Pf: "will become our property" | "The clause must say assign" |

For `cap_on_liability`, you can measure the risk first. Add this cell:

<details><summary>Cell: count the phrase (open and copy)</summary>

```python
PHRASE = re.compile(
    r"\b(consequential|indirect|incidental|punitive|special|exemplary)\b"
    r"[^.;]{0,80}\b(damages?|loss(es)?)\b",
    re.I,
)


def contract(doc_id):
    (path,) = con.execute("SELECT txt_path FROM contracts WHERE doc_id = ?", [doc_id]).fetchone()
    return Path(path).read_text(encoding="utf-8")


rows = con.execute(
    "SELECT doc_id, gold_present FROM scores WHERE run_id = ? AND field = 'cap_on_liability'", [RUN]
).fetchall()
gold = [bool(PHRASE.search(contract(d))) for d, present in rows if present]
none = [bool(PHRASE.search(contract(d))) for d, present in rows if not present]
print(f"gold cap: {sum(gold)} of {len(gold)}, no gold cap: {sum(none)} of {len(none)}")
```

</details>

```text
gold cap: 25 of 29, no gold cap: 1 of 23
```

*Python here: [the `re.compile` pattern](./py/phase-1d2.md#py-3).*

Here, we check one fact: this phrase is common where lawyers marked a cap, and rare where they did not.
So this rule has low risk. This is a text search, not a model test, so it cannot promise the result.

Decide. For each target field, write in your notebook:

1. Your rule, in one or two plain sentences.
2. The errors you expect it to fix.
3. The right answers it must keep.

Then guess how many errors v2 will fix in total. Write the guess down. You will check it in Step 8.

<details><summary>Reference rules (open after you decide)</summary>

- `notice_period...`: notice before a term ends, to stop or to choose a renewal. A right to end the
  contract at any time does not count.
- `non_compete`: add bans on helping a competitor, and promises to work only with the other party. A right
  to be the only seller, sponsor or licensee does not count by itself.
- `cap_on_liability`: add bans on kinds of damages. Quote each limit, since a time limit alone missed two
  answers. "Not liable unless it acted badly" alone does not count.
- `ip_ownership...`: rights must move to the other party, by assignment or by saying the work becomes that
  party's property. A party keeping its own work does not count.

The reference guess is 6 to 10 of the 17, with 1 or 2 new errors. It is only a guess.
</details>

## Step 4: write prompt v2 (your decision)

**Why.** A new folder keeps `v1` true for every stored run.

Create the folder:

```sh
cp -R src/docintel/domain/extract/prompts/v1 src/docintel/domain/extract/prompts/v2
```

Put your rules in `src/docintel/domain/extract/prompts/v2/system.md`, under "What each field means". Keep
everything else the same, including `v2/user.md`.

Keep them short. Say "does not count" only for a kind of clause you saw, and test each word against your
list of right answers.

Checkpoint. Read your own change, then check that the code can load it:

```sh
diff -u src/docintel/domain/extract/prompts/v1/system.md src/docintel/domain/extract/prompts/v2/system.md
uv run pytest tests/test_extract.py -q
```

*How to read this: [`diff -u`](./py/phase-1d2.md#py-4).*

The last lines of the output:

```text
...                                                                      [100%]
3 passed in 0.33s
```

The test `test_every_version_has_both_files` now also checks `v2`. You added no Python.

<details><summary>Reference changes to <code>v2/system.md</code> (open after you write yours)</summary>

```diff
-- notice_period_to_terminate_renewal: the notice needed to stop a renewal, like "90 days".
+- notice_period_to_terminate_renewal: the length of that notice, like "90 days".
 - cap_on_liability: a short summary of the cap, like "fees paid in the last 12 months".
 
 What each field means:
 - parties: the two or more parties who signed the contract.
 - agreement_date: the date of the contract.
 - governing_law: which state or country's law governs the contract.
-- non_compete: a party may not compete with the other party, or may not work in a certain place,
-  business or technology.
+- non_compete: a party may not compete with the other party, may not work in a certain place,
+  business or technology, may not deal with or help a competitor, or must work only with the other
+  party in one area. A right to be the only seller, sponsor or licensee does not count by itself.
 - change_of_control: a party may end the contract, or must get consent or give notice, if the
   other party is bought, merged, or sells most of its assets.
 - anti_assignment: consent or notice is needed to give the contract to a third party.
 - renewal_term: the renewal term after the first term ends, including automatic renewals.
-- notice_period_to_terminate_renewal: the notice needed to stop a renewal.
-- cap_on_liability: a limit on how much a party must pay if it breaks the contract, or a time limit
-  to bring claims.
+- notice_period_to_terminate_renewal: the notice a party must give before a term ends, to stop a
+  renewal or extension or to choose one. A right to end the contract at any time does not count.
+- cap_on_liability: a limit on how much a party must pay if it breaks the contract, a ban on
+  claiming some kinds of damages (like indirect or consequential damages), or a time limit to bring
+  claims. Quote each one you find. "Not liable unless it acted badly" alone does not count.
 - license_grant: one party gives the other a license.
-- ip_ownership_assignment: intellectual property made by one party becomes the other party's
-  property.
+- ip_ownership_assignment: intellectual property rights move to the other party: the contract
+  assigns them, or says that what one party makes becomes the other party's property. A party
+  keeping what it already owns or made for itself does not count.
```

This reference has not been run. No one knows its score yet, and that is on purpose.
</details>

<details><summary>Full reference <code>v2/system.md</code></summary>

```markdown
You read one legal contract and fill in 12 fields. Answer only with JSON that fits the schema.

Rules for every field:
1. quotes: copy the exact text from the contract, character for character. Do not fix spelling.
   Do not shorten with "...". Copy the shortest full sentence or clause that answers the field.
2. If the contract has nothing for a field, return no quotes and found false. Example:
   {"quotes": [], "found": false}. For a field with a value, value is null (or [] for parties).
3. found is true only if you give at least one quote.
4. Use only the contract. Do not guess.

Rules for values:
- agreement_date: the date of the contract as YYYY-MM-DD. If the day or month is missing, write
  YYYY-MM or YYYY.
- governing_law: only the state or country, like "New York" or "Ontario, Canada".
- parties: value has the legal name of each party that signs. quotes has each name and each short
  name the contract gives it, like "Company" or "Licensor".
- renewal_term: the length of each renewal, like "1 year".
- notice_period_to_terminate_renewal: the length of that notice, like "90 days".
- cap_on_liability: a short summary of the cap, like "fees paid in the last 12 months".

What each field means:
- parties: the two or more parties who signed the contract.
- agreement_date: the date of the contract.
- governing_law: which state or country's law governs the contract.
- non_compete: a party may not compete with the other party, may not work in a certain place,
  business or technology, may not deal with or help a competitor, or must work only with the other
  party in one area. A right to be the only seller, sponsor or licensee does not count by itself.
- change_of_control: a party may end the contract, or must get consent or give notice, if the
  other party is bought, merged, or sells most of its assets.
- anti_assignment: consent or notice is needed to give the contract to a third party.
- renewal_term: the renewal term after the first term ends, including automatic renewals.
- notice_period_to_terminate_renewal: the notice a party must give before a term ends, to stop a
  renewal or extension or to choose one. A right to end the contract at any time does not count.
- cap_on_liability: a limit on how much a party must pay if it breaks the contract, a ban on
  claiming some kinds of damages (like indirect or consequential damages), or a time limit to bring
  claims. Quote each one you find. "Not liable unless it acted badly" alone does not count.
- license_grant: one party gives the other a license.
- ip_ownership_assignment: intellectual property rights move to the other party: the contract
  assigns them, or says that what one party makes becomes the other party's property. A party
  keeping what it already owns or made for itself does not count.
- non_transferable_license: a party may not transfer the license to a third party.
```

</details>

## Step 5: write the keep rule, before any run (your decision)

**Why.** If you choose the bar after you see the score, the bar will move to fit the score.

You need three facts: how big luck is, how big a win could be, and what a win costs.

**Fact 1: noise, for free.** Your pilots from 1c2 and 1c4 used the same model and prompt as their full
runs. So their shared contracts are repeats. Add this cell. It scores in memory, and writes nothing:

<details><summary>Cell: <code>marks</code> and the pilot pairs (open and copy)</summary>

```python
def marks(run):
    rows = con.execute(
        "SELECT doc_id, field, answer FROM predictions WHERE run_id = ?", [run]
    ).fetchall()
    by_doc = defaultdict(list)
    for doc_id, field, answer in rows:
        by_doc[doc_id].append((field, answer))
    result = {}
    for doc_id, fields in by_doc.items():
        for r in score_doc(con, doc_id, from_rows(fields)):
            result[doc_id, r["field"]] = (r["tp"], r["fp"], r["fn"])
    return result


PAIRS = [
    ("20261101-155906", "20261101-192153"),
    ("20261101-191023", "20261101-192153"),
    ("20261102-193610", "20261102-194826"),
    ("20261102-202613", "20261102-202705"),
]
tried = flipped = 0
for pilot, full in PAIRS:
    a, b = marks(pilot), marks(full)
    changed = [key for key in a if a[key] != b[key]]
    tried += len(a)
    flipped += len(changed)
    print(pilot, "->", full, f"{len(changed)} of {len(a)} marks changed")
print(f"total: {flipped} of {tried} ({flipped / tried:.1%})")
```

</details>

```text
20261101-155906 -> 20261101-192153 0 of 36 marks changed
20261101-191023 -> 20261101-192153 3 of 120 marks changed
20261102-193610 -> 20261102-194826 1 of 36 marks changed
20261102-202613 -> 20261102-202705 1 of 36 marks changed
total: 5 of 228 (2.2%)
```

*Python here: [`result[doc_id, r["field"]]`](./py/phase-1d2.md#py-5).*

Here, we compare the same contracts across two runs. On 624 fields, 2.2% is about 14 changed marks. If
those go up and down at random, F1 moves by about 0.012 either way. That is a guess. These are other
models, and the sample is small.

**Fact 2: the size of a win.** Add this cell. It pretends the prompt fixed some random errors:

<details><summary>Cell: <code>fix</code> (open and copy)</summary>

```python
base = per_doc(RUN)
docs = sorted(base)
errors = con.execute(
    "SELECT doc_id, fp, fn FROM scores WHERE run_id = ? AND fp + fn > 0 ORDER BY doc_id, field", [RUN]
).fetchall()


def fix(count, seed):
    """Pretend the prompt fixed `count` random errors, and made no new ones."""
    new = dict(base)
    for doc, fp, fn in random.Random(seed).sample(errors, count):
        tp0, fp0, fn0 = new[doc]
        new[doc] = (tp0 + fn, fp0 - fp, fn0 - fn)
    return new


for count in (5, 10, 15, 20):
    gains = [f1(fix(count, seed), docs) - f1(base, docs) for seed in range(40)]
    print(f"{count:2} errors fixed: F1 up by {sum(gains) / len(gains):.3f}")
```

</details>

```text
 5 errors fixed: F1 up by 0.008
10 errors fixed: F1 up by 0.017
15 errors fixed: F1 up by 0.026
20 errors fixed: F1 up by 0.034
```

So the two facts together say: fewer than about 7 net fixes could be luck. Net means fixes minus new
errors.

The ceiling is close by. Under the reference sort:

| If v2 fixes | TP / FP / FN | F1 |
|---|---|---|
| nothing | 290 / 36 / 20 | 0.912 |
| all 17 errors in the reference target fields | 296 / 23 / 14 | 0.941 |
| all 23 prompt errors | 299 / 20 / 11 | 0.951 |

**Fact 3: the bootstrap has a blind spot.** `gap` picks contracts again, but keeps the same answers. So it
does not see noise from a second run. In a small test, even 5 fixed errors gave a range above 0. It is
useful, but too easy to be your only test.

**Optional: measure noise on the real model.** A second v1 run costs about $0.20. It gives the true noise
for V4 Flash, and may show another provider. It must finish before you write your rule:

```sh
uv run python -m docintel.evals.runner run --prompt-version v1 --model deepseek/deepseek-v4-flash
```

Options for the rule:

| Option | Good | Bad |
|---|---|---|
| F1 goes up | simple | a gain of 0.001 passes |
| F1 goes up by a margin larger than noise | ignores luck | can reject a small real gain |
| Margin, plus a recall floor | rules that only say "no" cannot win by losing answers | more numbers to defend |
| Bootstrap range above 0 only | looks scientific | does not see run noise |
| Add limits on cost, p95 and bad answers | protects what you pay for | p95 depends on the provider |

Decide. Write the rule in your E1.3 entry now, with real numbers. Also say what happens when v2 fails.

If you want proof of the date, you can commit it now. That choice is yours.

<details><summary>Reference keep rule (open after you decide)</summary>

```markdown
- **Keep rule (written before the run):** keep v2 only if all of these are true, against
  20261102-200003:
  1. All-field F1 is at least 0.927 (0.912 + 0.015, a little more than the noise guess).
  2. Recall is at least 0.925 (287 TP: it can lose 3).
  3. The low end of the `gap` range is above 0.
  4. 0 bad answers.
  5. Cost is at most $0.255, and p95 at most 71.9 s (1.25 times v1).
  6. Wrong-quote TPs are at most 6 (v1 has 4).
  If v2 fails, v1 stays. A v3 needs its own new entry and rule.
```

If you did the second v1 run, use the larger of 0.015 and twice the F1 gap between the two v1 runs.

This bar is hard: it needs about 9 net fixes from 17 target errors. That is on purpose. If v2 passes, you
can believe it. If v2 fails, you still learn which rules worked.
</details>

## Step 6: pilot

**Why.** A pilot finds a broken setup for very little money. Its score means nothing on 3 contracts.

Close the notebook connection, then run:

```sh
uv run python -m docintel.evals.runner run --prompt-version v2 --model deepseek/deepseek-v4-flash --limit 3
```

```text
run 20261105-085229: 3 of 3 docs to do, deepseek/deepseek-v4-flash, about $0.0041
Start? [y/N]
```

That part is real. Your `run_id` will differ. The estimate is too low for a model that reasons: the real
V4 Flash cost was about $0.004 per contract, so expect about $0.012 here. Type `y`.

Expected shape:

```text
[1/3] <doc_id>  ok=True  $<cost>  <seconds> s
[2/3] <doc_id>  ok=True  $<cost>  <seconds> s
[3/3] <doc_id>  ok=True  $<cost>  <seconds> s
done in <n> s: 3 of 3 docs scored, 0 calls failed
```

Check three things: every `ok=True`, the cost is near the guess, and the `prompt_version` is right.

```python
con.sql("SELECT run_id, model, prompt_version, n_docs FROM runs ORDER BY created_at DESC LIMIT 1")
```

Do not edit the prompt because of the pilot's score. If it is broken, fix the setup and pilot again.

## Step 7: run v2 on dev

**Why.** This is the experiment. The keep rule is already written, so nothing here is a choice.

```sh
uv run python -m docintel.evals.runner run --prompt-version v2 --model deepseek/deepseek-v4-flash
```

Type `y`. Expect about $0.20, a guess from the v1 run. The printed estimate will be near $0.07. If the run
stops, finish it with `--resume <run_id>`.

Then:

```sh
uv run python -m docintel.evals.runner report <your run_id>
```

The table has the same shape as Step 2. Add this to your notebook:

```python
V2 = "<your run_id>"
TARGETS = ["..."]  # your target fields from Step 2
con.sql(
    "SELECT provider, count(*) AS calls FROM llm_calls WHERE run_id = $run GROUP BY provider",
    params={"run": V2},
)
```

Here, we check the provider. All 52 v1 calls went to Crusoe. If v2 went elsewhere, the prompt is not the
only change. It is not a reason to throw the run away, but E1.3 must say it.

From here on, this doc shows shape only, because no v2 run existed when it was written. Your numbers
decide this part.

## Step 8: compare and decide

**Why.** The total alone can hide one rule that helped and one that hurt.

Add the per-field table:

```python
con.sql(
    """
SELECT list_contains($targets, o.field) AS target, o.field,
    sum(o.tp) AS tp1, sum(o.fp) AS fp1, sum(o.fn) AS fn1,
    sum(n.tp) AS tp2, sum(n.fp) AS fp2, sum(n.fn) AS fn2
FROM scores o JOIN scores n USING (doc_id, field)
WHERE o.run_id = $old AND n.run_id = $new
GROUP BY o.field
ORDER BY target DESC, o.field
""",
    params={"targets": TARGETS, "old": RUN, "new": V2},
).show(max_width=120)
```

Expect 12 rows. Your target fields come first. Read them in this order:

1. **Target fields.** Did FP fall? Did FN rise? A rule that only says "no" can do both.
2. **Check fields.** They should move only a little. A large change means a rule leaked, or noise is
   larger than you guessed.

Next, read every flip, as you did in 1d. Add this cell:

<details><summary>Cell: <code>changed</code> (open and copy)</summary>

```python
CHANGED = """
SELECT o.field, o.doc_id, o.tp, o.fp, o.fn, n.tp, n.fp, n.fn, p.answer
FROM scores o JOIN scores n USING (doc_id, field)
    JOIN predictions p ON p.run_id = n.run_id AND p.doc_id = n.doc_id AND p.field = n.field
WHERE o.run_id = ? AND n.run_id = ? AND (o.tp, o.fp, o.fn) <> (n.tp, n.fp, n.fn)
ORDER BY o.field, o.doc_id
"""


def changed(field, new=V2, old=RUN, width=160):
    for f, doc, *counts, answer in con.execute(CHANGED, [old, new]).fetchall():
        if f == field:
            print(doc[:28], counts[:3], "->", counts[3:])
            for quote in json.loads(answer)["quotes"]:
                print("   ", quote[:width])


changed("non_compete")
```

</details>

*Python here: [`for f, doc, *counts, answer in ...`](./py/phase-1d2.md#py-6).*

Each flip prints as `<doc_id> [<tp>, <fp>, <fn>] -> [<tp>, <fp>, <fn>]`, then the new quotes.

For each flip, ask: did the rule do this, or is it noise? Check the right answers you promised to keep in
Step 3. If a mark changed in a way you cannot connect to a rule, count it as noise.

Now collect the numbers for your keep rule:

<details><summary>Cell: the numbers for your rule (open and copy)</summary>

```python
all_new = next(r for r in metrics(con, V2) if r["name"] == "all")
print("F1", round(all_new["f1"], 3), "recall", round(all_new["recall"], 3))
print("V2 minus V1 (gap, low, high):", gap(V2, RUN))
con.sql(
    """
SELECT run_id, count(*) AS calls, count(*) FILTER (WHERE NOT ok) AS bad,
    round(sum(cost_usd), 3) AS cost, round(quantile_cont(latency_ms, 0.95) / 1000, 1) AS p95_s,
    round(avg(completion_tokens)) AS out_tokens
FROM llm_calls WHERE run_id IN ($old, $new) GROUP BY run_id
""",
    params={"old": RUN, "new": V2},
).show()
con.sql(
    """
SELECT run_id, count(*) AS wrong_quote_tps FROM scores
WHERE run_id IN ($old, $new) AND rule = 'presence' AND tp = 1 AND NOT quote_ok
GROUP BY run_id
""",
    params={"old": RUN, "new": V2},
).show()
```

</details>

In the last table, v1 shows 4.

It prints F1 and recall, then the gap as `(<gap>, <low>, <high>)`, then the two tables.

Decide. Apply your rule line by line, exactly as you wrote it. Then write one sentence: kept or not kept.
Compare the result with your guess from Step 3. A big miss in either direction teaches you something.

There is no reference answer here. Only your run can give it.

## Step 9: tests, and the default version

**Why.** Stored runs depend on old prompts. A test can stop an accidental edit.

Add `from hashlib import sha256` and `from docintel.domain.schema.fields import ContractFields` to the
imports of `tests/test_extract.py`.

Add to the bottom of `tests/test_extract.py`:

```python
def test_every_prompt_names_every_field():
    for version in [p.name for p in PROMPTS.iterdir() if p.is_dir()]:
        system, _ = load_prompt(version)
        for field in ContractFields.model_fields:
            assert f"- {field}:" in system, f"{version} does not define {field}"


def test_v1_never_changes():
    system, _ = load_prompt("v1")
    assert sha256(system.encode()).hexdigest()[:12] == "e4bcfc8ac5b5"
```

*Python here: [`sha256(...).hexdigest()`](./py/phase-1d2.md#py-7).*

Here, we guard two things:

1. Every prompt defines all 12 fields, so a rule edit cannot delete one.
2. The text of `v1` stays the same. The short hash is a fingerprint of the file.

Checkpoint:

```sh
uv run pytest tests/test_extract.py -q
make lint
```

```text
.....                                                                    [100%]
5 passed in 0.33s
```

`make lint` can still flag the notebook, as it did in 1d.

<details><summary>Full <code>tests/test_extract.py</code></summary>

```python
"""Prompt and message rules. No network, no key."""

from hashlib import sha256

import pytest

from docintel.domain.extract.extract import PLACEHOLDER, PROMPTS, build_messages, load_prompt
from docintel.domain.schema.fields import ContractFields

TEXT = 'Section {1}: "Licensor" shall {not} assign.\n'  # braces, quotes and a newline


def test_every_version_has_both_files():
    versions = [p.name for p in PROMPTS.iterdir() if p.is_dir()]
    assert versions
    for version in versions:
        system, user = load_prompt(version)
        assert system.strip()
        assert user.count(PLACEHOLDER) == 1


def test_contract_text_goes_in_unchanged():
    messages = build_messages(TEXT, "v1")
    assert [m["role"] for m in messages] == ["system", "user"]
    assert TEXT in messages[1]["content"]
    assert PLACEHOLDER not in messages[1]["content"]


def test_unknown_version_fails():
    with pytest.raises(FileNotFoundError):
        build_messages(TEXT, "v999")


def test_every_prompt_names_every_field():
    for version in [p.name for p in PROMPTS.iterdir() if p.is_dir()]:
        system, _ = load_prompt(version)
        for field in ContractFields.model_fields:
            assert f"- {field}:" in system, f"{version} does not define {field}"


def test_v1_never_changes():
    system, _ = load_prompt("v1")
    assert sha256(system.encode()).hexdigest()[:12] == "e4bcfc8ac5b5"
```

</details>

**Only if v2 passed.** `v1` is the default in three places: `build_messages` and `extract` in
`src/docintel/domain/extract/extract.py`, and `--prompt-version` in `src/docintel/evals/runner.py`. Change
all three to `v2`. If v2 failed, change nothing. The `v2` folder stays as a record of the run.

Your project structure now matches the tree in Project setup.

## Break it on purpose

### Break 1: F1 misses by a little

Suppose your bar is 0.927, and v2 gets 0.926. Everything else passes. What do you do?

<details><summary>Guess, then open</summary>

v2 does not pass. The bar is not special, but moving it after you saw the score removes its whole value.
You can write this in E1.3: "Close, did not pass." You can also try a v3, with a new rule and a new entry.
</details>

### Break 2: edit `v1` in place

Add one word to `v1/system.md`, then run the tests. Guess what fails, and why it matters.

<details><summary>Guess, then open</summary>

`test_v1_never_changes` fails with a different hash. Without this test, nothing would warn you. The `runs`
table would still say `v1` for answers made by the old text. Undo the word with `git checkout` on that one
file.
</details>

### Break 3: keep only the fields that improved

v2 is better on `cap_on_liability`, but worse on `non_compete`. A teammate says: "Take cap from v2 and the
rest from v1, and report the best of both." What is wrong with this?

<details><summary>Guess, then open</summary>

No single prompt produced that score. It also picks the lucky side of the noise after seeing the results.
To use only the cap rule, make that a v3, write a keep rule, and run it.
</details>

## Experiment

This is E1.3. It makes one full paid run, plus a pilot. The optional v1 rerun is a third.

- **Commands:** the `run` commands in Steps 6 and 7.
- **`run_id`:** one for the pilot, not used for results, and one for the full run.
- **Expected tables:** the 12-row per-field table from Step 8, one row per run for cost and latency, one
  row per run for wrong-quote TPs.
- **Dev only:** never run this on `--split test` to choose a prompt.

Add this to `EXPERIMENTS.md`. Fill in the keep rule before the run, and the rest after:

```markdown
## E1.3: prompt v2 for the weak fields
- **Date:**
- **Score rules Hash:** 6ffdaa7 (same rules as E1.2)
- **run_id(s):** <full run> against 20261102-200003. Pilot, not used for results: <pilot>.
- **Question / hypothesis:** Do specific rules for <your target fields> beat v1, without losing recall?
- **Data:** dev, 52 contracts, 12 fields, CUAD .txt (clean)
- **Setup:** deepseek/deepseek-v4-flash, parser cuad_txt, temperature 0, no validation retries. Only the
  prompt changes: v1 -> v2. Target fields: <list>. Check fields: <list>. Provider: <from Step 7>.
- **Keep rule (written before the run):** <your rule, with numbers>
- **Noise:** 5 of 228 marks changed between pilots and full runs (other models). <second v1 run, if any>
- **Guess before the run:** <errors fixed, new errors>
- **Results:** P, R, F1, TP / FP / FN, cost, p50, p95, bad answers, for v1 and v2. Per-field table for
  target and check fields. Gap with its range. Wrong-quote TPs for each.
- **Flips read:** <fixed by a rule, broken by a rule, noise, with counts>
- **Limits:** the rules were written from dev errors, so this gain is optimistic. Test gives the final
  number. <what else>
- **Conclusion:** kept or not kept, line by line against the rule. Which rules worked.
- **Next step:** 2a (validators and citations) on the kept prompt.
```

## Gotchas

- **The database is locked.** DuckDB allows one writer. Close the notebook connection before each `run`.
- **No scoring edits now.** If you find a scoring bug, log it and test it in its own later step. Changing it
  here breaks the comparison with v1.
- **Do not name contracts in the prompt.** "Tuniu's clause counts" fits dev only. A rule must describe a
  kind of clause.
- **`estimate` is too low.** It assumes 1,000 output tokens, and V4 Flash used about 8,950 per contract.
- **Each extra sentence can change how the model reads other fields.** That is why you watch check fields.
- **`quote_ok` is `any`.** "Quote each one" helps quote fields, because one match is enough. So more quotes
  can raise a score without better reading. Read those flips with care.

## Explain back, then commit

Explain to Claude in a few sentences (the rule in `PLAN.md`):

- Your target fields, and one weak field you left out, and why.
- One rule: the errors it should fix, the right answers it must keep.
- Each number in your keep rule, and where it came from.
- Your result: kept or not, one flip a rule caused, and one flip you think is noise.
- Why this gain is still optimistic.

Then:

```sh
git status
git add src/docintel/domain/extract/prompts/v2 tests/test_extract.py notebooks/00_explore.ipynb EXPERIMENTS.md
git commit -m "phase 1d2: prompt v2 and keep rule (E1.3)"
```

If v2 passed, also add `src/docintel/domain/extract/extract.py` and `src/docintel/evals/runner.py`.

## Conclusion

What you have now:

- `prompts/v2/`, with rules that come from errors and right answers.
- A keep rule written before the run, and a result judged by it.
- E1.3, and a clear prompt for 2a to build on.

Go back to the objectives. Check that you can do each one without notes. Then answer:

1. Why can a rule that fixes 10 FPs still make the product worse?
2. v2 gains 0.02 F1. Name two reasons that gain may not be real.

Want more practice? Try these (optional):

1. Sort the flips by cause: rule, noise, or unclear. Is the noise close to 2.2%?
2. Give v2 to GLM-5.3 on dev. Do the same rules work on another model? This costs about $0.21.
3. Write the `change_of_control` rule anyway, as a v3 with its own keep rule. Was your Round 2 guess
   right?

Checklist (`../PLAN.md`): **Prompt versioning; context engineering** (a frozen v1, and rules from real
errors). **Precision/recall/F1 per field; span scoring** (per-field comparison, wrong-quote check).
**Experiments: run_id, one change at a time, cost, p50/p95** (a keep rule written before the run, and noise
measured from repeats).
