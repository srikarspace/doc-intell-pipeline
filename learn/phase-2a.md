# Phase 2a: validators and quote checks

In this part, you decide what makes an answer broken, then build the code that finds it. You build
one small module at a time, and check it on the answers already stored from E1, E1.1 and E1.3. There
are no LLM calls and no cost.

This is part 1 of 2 for Phase 2a. Part 2 (2a2) adds needs-review rules and stores the results.

## Words used in this part

Read these first. Precision, recall, TP, FP and FN are from 1b2 and 1c3.

- **Validator**: code that checks an answer and reports what is wrong. Example: "found is true, but
  there are no quotes".
- **Shape rule**: is the JSON the right form? Example: `found` must be `true` or `false`, not
  `"yes"`. The schema from 1a does this.
- **Content rule**: does the answer make sense? Example: a date must be a real date. The JSON shape
  can be perfect and the content still wrong.
- **Citation**: the exact text in the contract that supports an answer. In this project, the
  `quotes` list.
- **Hallucinated quote**: a quote the model wrote, but the contract does not contain. It looks real,
  so it is dangerous.
- **Near-miss**: a quote that is almost the same as the contract text. Example: the contract says
  `(vii)` and the quote says `(ix)`.
- **Fuzzy match**: a score from 0 to 1 that says how similar two texts are. Example: 0.98 means
  "almost the same".
- **False alarm**: a check says "problem", but the answer is fine.
- **Page break text**: words the PDF puts between two pages. Example: `Source: EXACT SCIENCES CORP,
  8-K, 8/22/2018`. The contract's sentence continues after them.
- **Issue**: our name for one problem in one field. It is a small object with four parts.
- **Severity**: how bad an issue is. Here, `error` or `warn`.
- **Replay**: run new code on answers already stored, with no new LLM call. Like `score` in 1c.
- **Seed**: a starting number for random choices, so the same "random" results come every time.

## Objectives

By the end of this part you should be able to:

1. Explain the difference between a shape rule and a content rule, with a real example of each.
2. Explain why one bad field must not blank the other 11 fields.
3. Check if a quote is really in a contract, and say why a fuzzy score is the wrong tool.
4. Give four real near-misses from stored runs, and say what the check does with each.
5. Run your rules on a stored run, and read the counts.

## Dependencies

You install nothing new. This part needs:

- 1a: the `Strict` base model and `ContractFields`.
- 1a2: `LLMResult` and `_parse` in `core/llm.py`.
- 1c: `from_rows` in `evals/runner.py`, and the stored runs.
- 1d: the E1.2 scoring rules. Every F1 in this doc uses them.
- 1d2: E1.3. Prompt v1 stays, so the kept run is still `20261102-200003` (DeepSeek V4 Flash, prompt
  v1, served by Crusoe), now marked by the E1.2 rules. E1.3 also stored a v1 run of the same model
  on Parasail.

## The big picture

Before this part, the pipeline trusts every answer that fits the schema. If the model writes a
quote that is not in the contract, nothing notices.

After this part, one function reads an answer and its contract, and returns a list of issues:

```text
LLMResult + contract text -> check_result -> [Issue, Issue, ...]
```

What later parts do with that list:

- **2a2** decides which fields a person must look at, and stores the issues in DuckDB.
- **2b** sends the errors back to the model, and asks it to try again.
- **Phase 3** runs the same checks on text from worse parsers.
- **Phase 4** shows the flags to the user in the API and the UI.

The kept run is the baseline, not E1. Your rates come from run `20261102-200003`. Many near-miss
examples come from E1, because E1 makes more of them.

Crusoe no longer serves V4 Flash, so new runs in 2b will use another provider. So we also check the
E1.3 run on Parasail (`20261105-213036`): same model, same prompt v1, another provider.

## Remember this

> The schema checks the shape of an answer. Your rules check if the answer makes sense, one field
> at a time, so one bad field never blanks the other 11. A quote counts only if its words are in
> the contract, in the same order. A fuzzy score is the wrong tool: change one number and the quote
> is still 99% similar, but it is wrong.
>
> **Shape in the schema. Sense in the rules. Same words, or it is not a quote.**

## Why

**The product promises a real quote.** A lawyer reads the quote and trusts the answer. A made-up
quote with a real-looking section number is worse than no answer.

**The provider cannot do this for us.** `response_format` can force a shape. It cannot know what
the contract says. Only our code has the contract and the answer together.

**The check must not make false alarms.** On the kept model, a plain `quote in text` fails 29 of 424
quotes. Every one of those 29 is fine. If a check is wrong that often, people stop reading it.

## Design decisions

The reference choices for your decisions are in Steps 1, 2 and 4. The choices here are not yours
to make: they follow from the code that exists.

- **A new folder, `domain/validate/`.** It sits next to `domain/extract/`, as `PLAN.md` says. Other
  option: put it in `evals/`. But the API needs these checks too, and the API must not depend on
  evals code.
- **`domain/` does not import `evals/`.** So `citations.py` gets its own `words` function, even
  though `evals/scorers.py` has a similar `tokens`. `words` keeps order and repeats. `tokens` is a
  set, so it has neither. Other option: share one function. Then a change for scoring could break
  the citation check without warning.
- **The contract is split into words once per contract.** A contract has thousands of words, and
  an answer has about 8 quotes. Other option: split it again for each quote. Slower, for no gain.
- **No new library.** Python's `re` is enough. Other option: `rapidfuzz`, for fast fuzzy scores.
  Step 2 shows why we do not need them.

Two rules from the plan do not apply. **"Expiration after start"**: your 12 fields have no
expiration date, because 0d did not choose one. **"Enums"**: no field has a fixed list of values.
The nearest rule is the shape of a duration, like `90 days`. It is a decision in 2a2.

## Worked example

Real text from CUAD and from your stored answers. Guess before you open each box.

### Round 1: a true quote that fails

The kept model quotes this for `non_transferable_license` in the Exact Sciences contract:

```text
Such license shall be non-transferable and non-sublicensable (except as provided in this
Agreement) and shall automatically terminate upon the expiration or earlier termination of this
Agreement.
```

The contract text is:

```text
Such license shall be non-transferable and non-sublicensable 17

Source: EXACT SCIENCES CORP, 8-K, 8/22/2018





(except as provided in this Agreement) and shall automatically terminate upon ...
```

Did the model make up this quote? What does `quote in text` say?

<details><summary>Guess, then open</summary>

The model did not make it up. It read across a page break, and left out the page number and the
footer. A person would do the same. But `quote in text` says `False`.

The quote is right, and the simple check says it is wrong. This is a false alarm.
</details>

### Round 2: two changed quotes

Both are real, from E1. In each, the model changed the contract's text a little.

```text
Coral Gold, contract: ... shall be assigned without thewritten consent of all the parties.
Coral Gold, quote:    ... shall be assigned without the written consent of all the parties.

Sucampo, contract:    (vii) which requires or restricts the payment of dividends ...
Sucampo, quote:       (ix) which requires or restricts the payment of dividends ...
```

One change fixes a typo. The other cites the wrong list item. Can a program tell which is which?

<details><summary>Guess, then open</summary>

Not without understanding the text. To a program, both are "one small piece changed". A check that
forgives the first one also forgives the second one.

The same model on Parasail does this twice in E1.3. Coral Gold comes back, and in Upjohn, `11∕2` (a
fraction the text lost) becomes `1½`.

So both count as `missing` in the reference. The Coral Gold quote is a false alarm, and we accept
that. Prompt v1 says "Do not fix spelling", so it is also a real rule break.
</details>

### Round 3: a quote with no words

The kept model gives this quote for `parties` in the Nuveen contract. The contract is a template,
with empty places to fill in.

```text
[●]
```

The contract does contain `[●]`, many times. Is this a good citation?

<details><summary>Guess, then open</summary>

No. `quote in text` says `True`, but the quote proves nothing. It has no letters and no numbers.

So "is it in the text" is not the only question. A quote also needs real words. The reference calls
this `no_words`.
</details>

## Project setup

DuckDB allows one writer at a time, so close the notebook connection before you run a checkpoint.

Create the new files:

```sh
mkdir -p src/docintel/domain/validate
touch src/docintel/domain/validate/{__init__,issues,citations,rules}.py tests/test_validate.py
```

You should now have:

```text
src/docintel/domain/
├── extract/
├── schema/
└── validate/
    ├── __init__.py
    ├── citations.py
    ├── issues.py
    └── rules.py
tests/
└── test_validate.py
```

## Step 1: where the rules live (your decision)

**Why.** Every later part depends on what happens when one rule fails.

There are two options.

**Option A: rules inside the schema.** Add a Pydantic validator to `Text`, `Clause` and `Names`.
When a rule fails, `_parse` returns `parsed=None`. The runner then stores 12 empty fields. You try
this for real in "Break it on purpose".

**Option B: rules outside the schema.** The schema keeps checking only the shape. A separate
function reads the parsed answer and returns a list of issues. Other fields are not touched.

Look at the evidence. These are real numbers from Step 5, on stored answers:

| Question | Option A | Option B |
|---|---|---|
| A field breaks a rule. What happens? | All 12 fields are blanked | Only that field gets an issue |
| Kept model, F1 0.912, errors only | 0.904 (2 contracts blanked, 7 correct fields lost) | 0.912 |
| Kept model, errors and warnings | 0.845 (8 contracts blanked, 42 correct fields lost) | 0.912 |
| Same model on Parasail, F1 0.907, errors only | 0.872 (5 contracts blanked, 23 correct fields lost) | 0.907 |
| E1, F1 0.827, errors only | 0.733 (11 contracts blanked, 58 correct fields lost) | 0.827 |
| How does the rule get the contract text? | Through Pydantic's `context` argument | A normal function argument |
| Does the provider see the rule? | No | No |
| Can old runs be rebuilt with `from_rows`? | Not all (Break 1) | Yes |

Decide these, and write them in a "Validation rules" cell in the notebook:

1. **Where do content rules live?** A, B, or a mix?
2. **What does a failed rule do to the answer?** Nothing, or does it clear the field?
3. **How many levels of problem do you need?** One, or two? Think about 2b: which problems are worth
   paying for a retry?

<details><summary>Reference choice (open after you decide)</summary>

1. Option B. `ContractFields` stays shape only, so the schema sent to the provider does not change.
2. Nothing. In 2a and 2a2, rules only report. So F1 cannot change by accident, and each later change
   can be measured alone. What to do about a failure is 2b's question.
3. Two. `error`: the answer breaks a rule, and a retry may fix it. `warn`: the answer may be fine,
   but a person should look.
</details>

Now the object every rule returns. Put this in `src/docintel/domain/validate/issues.py`:

```python
"""One problem found in one field of one answer."""

from typing import Literal

from docintel.domain.schema.fields import Strict


class Issue(Strict):
    """`error`: the answer breaks a rule. `warn`: it may be fine, but a person should look."""

    field: str
    rule: str
    severity: Literal["error", "warn"]
    detail: str
```

*Python here: [`Literal`](./py/phase-2a.md#py-1).*

Here, we:

1. Reuse `Strict` from 1a: no unknown keys, no type guessing.
2. Store which field, which rule, how bad, and a short detail for a person or for 2b's retry.
3. Allow only two values for `severity`. A typo in a rule fails at once.

Checkpoint:

```sh
uv run python -c "
from docintel.domain.validate.issues import Issue
print(Issue(field='non_compete', rule='quote_missing', severity='error', detail='A made-up quote.'))
Issue(field='non_compete', rule='quote_missing', severity='oops', detail='')"
```

```text
field='non_compete' rule='quote_missing' severity='error' detail='A made-up quote.'
Traceback (most recent call last):
  ...
pydantic_core._pydantic_core.ValidationError: 1 validation error for Issue
severity
  Input should be 'error' or 'warn' [type=literal_error, input_value='oops', input_type=str]
```

The first line prints the issue. The error on the second is what you want.

## Step 2: quote matching rules (your decision)

**Why.** "Is this quote really in the contract?" needs an exact meaning.

Here are the options, from strict to loose:

| Option | Rule | Example it accepts |
|---|---|---|
| Same bytes | `quote in text` | Only a perfect copy |
| Same words | Lowercase letters and numbers, side by side | Other spaces, case or punctuation |
| Same words, with a gap | Same words in order, extra source words allowed between them | A page footer in the middle |
| Fuzzy | Similarity score of 0.9 or more | Anything that looks close |

**Evidence 1: real answers.** How many quotes each option accepts. Same words and gap are counted
separately, so a quote is in one column only. You reproduce this table in Step 3.

```text
run             quotes same_bytes same_words  gap missing no_words
V4 (kept)          424        395        417    6       0        1
V4 v1 Parasail     432        370        418   12       2        0
E1                 441        342        429    9       3        0
Qwen3.8            408        372        404    4       0        0
GLM-5.3            413        361        403   10       0        0
V4.1               406        360        387    9       9        1
```

Read the kept model's row:

1. Same bytes fails 29 of 424 quotes. All 29 are spaces, case, page breaks, or a typo fix.
2. Same words and `no_words` leave only 7 to look at: 6 with a gap, and the `[●]` from Round 3.
3. **`missing` is 0. The kept model made up no quotes on these 52 contracts.**

Now read the Parasail row: the same model and prompt, on another provider.

1. It has 2 `missing` quotes. Neither has made-up words. Both fix broken contract text (Round 2).
2. It has twice as many `gap` quotes. Three of the 12 are cuts with `...`, not page breaks. The prompt
   does not allow `...`, and a warning is the right answer for them too.

Say this honestly in your write-up. The check is insurance, and the real number of made-up quotes
caught is zero. But a new provider changes how often the model breaks the copy rule.

**Evidence 2: real gaps.** The biggest gaps in all 6 runs:

- 1 word: a page number, like `Massachusetts, 13 in each case` in the Nuveen contract.
- 10 words: the page footer from Round 1.
- 42 words: a redaction note. In the MediWound contract, `*** Confidential treatment has been
  requested ...` sits inside the sentence.
- Then a big jump to 414 words. That is the Coral Gold quote: `thewritten` is not `written`, so the
  check finds the word `written` far away.

**Evidence 3: changed quotes.** Do the options catch a quote that a model changed? We took the kept
model's real quotes of 8 or more words, and changed each one on purpose, with a fixed seed. "Passes"
means the check did not call it `missing`.

```text
change                      n  fuzzy>=0.9  same_words  gap  missing
a number changed          130         121           0    0      130
shall -> may              117         110           0    7      110
not removed                45          41           0   45        0
a word added              311         257           0    0      311
from another contract     305           1           0    0      305

real quotes with a page break or a note inside:
  0.85  2ThemartComInc_19990826_  All rights (under any applicable intelle
  0.79  ExactSciencesCorp_201808  Such license shall be non-transferable a
  0.99  FIDELITYNATIONALINFORMAT  Notwithstanding the foregoing, in no eve
  0.55  MEDIWOUNDLTD_01_15_2014-  MediWound's rights as per Section 3.1 wi
  0.99  NUVEEN - REMARKETING AGR  This Agreement shall be construed in acc
  0.99  VARIABLESEPARATEACCOUNT_  AIG shall have the absolute right to ter
```

Read it in this order:

1. Fuzzy lets 121 of 130 changed numbers pass. `30 days` and `37 days` look almost the same to it.
2. Fuzzy also rejects 3 of the 6 real page-break quotes (0.85, 0.79, 0.55). It is wrong both ways.
3. Same words lets none of the changes pass.
4. **The gap check cannot see a removed `not`.** All 45 become `gap`, because the contract's extra
   word looks just like a page number. So a gap can never count as a clean match.

<details><summary>The script behind Evidence 3 (optional: it is slow, and needs Step 3 first)</summary>

```sh
uv run python - <<'EOF'
import difflib
import json
import random
import re
from collections import Counter

from docintel.domain.validate.citations import quote_status, words
from docintel.evals.runner import cuad_txt
from docintel.evals.store import connect

RUN = "20261102-200003"  # the kept model
random.seed(7)


def fuzzy(quote, source):
    """The best similarity (0 to 1) between the quote and any same-size piece of the source."""
    q = words(quote)
    rare = sorted(set(q), key=source.count)[:3]  # start only near the quote's rarest words
    starts = {max(0, i - q.index(w)) for w in rare for i, s in enumerate(source) if s == w}
    return max(
        (
            difflib.SequenceMatcher(None, " ".join(source[s : s + len(q)]), " ".join(q)).ratio()
            for s in starts
        ),
        default=0,
    )


def change_number(q):
    return re.sub(r"\d+", lambda m: str(int(m.group()) + 7), q, count=1)


def change_shall(q):
    return re.sub(r"\bshall\b", "may", q, count=1)


def drop_not(q):
    return re.sub(r"\b(shall|may|will) not\b", r"\1", q, count=1, flags=re.I)


def add_word(q):
    w = q.split()
    return " ".join(w[: len(w) // 2] + ["exclusively"] + w[len(w) // 2 :])


with connect() as con:
    rows = con.execute(
        "SELECT doc_id, answer FROM predictions WHERE run_id = ? ORDER BY doc_id, field", [RUN]
    ).fetchall()
    source = {d: words(cuad_txt(con, d)) for d, _ in rows}
quotes = [(d, q) for d, a in rows for q in json.loads(a)["quotes"] if len(q.split()) >= 8]
changes = {
    "a number changed": change_number,
    "shall -> may": change_shall,
    "not removed": drop_not,
    "a word added": add_word,
}
results = {}
for name, change in changes.items():
    tests = [(d, change(q)) for d, q in quotes if change(q) != q]
    results[name] = tests
others = [(d, random.choice(quotes)) for d, _ in quotes]
results["from another contract"] = [(d, o[1]) for d, o in others if o[0] != d]

print(f"{'change':24} {'n':>4} {'fuzzy>=0.9':>11} {'same_words':>11} {'gap':>4} {'missing':>8}")
for name, tests in results.items():
    status = Counter(quote_status(q, source[d]) for d, q in tests)
    close = sum(fuzzy(q, source[d]) >= 0.9 for d, q in tests)
    print(
        f"{name:24} {len(tests):4} {close:11} {status['same_words']:11} {status['gap']:4} {status['missing']:8}"
    )
print()
print("real quotes with a page break or a note inside:")
for d, q in quotes:
    if quote_status(q, source[d]) == "gap":
        print(f"  {fuzzy(q, source[d]):.2f}  {d[:24]:24}  {q[:40]}")
EOF
```
</details>

Decide these, and write them in your notebook cell:

1. **What counts as the same text?** Choose an option from the table.
2. **Page breaks.** Is a quote with a gap accepted, rejected, or accepted with a warning? How large
   can a gap be?
3. **A model that fixes a typo in the contract.** Accept it (Coral Gold), or treat it like Sucampo?
4. **A quote with no real words** (`[●]`). What should happen?

<details><summary>Reference choice (open after you decide)</summary>

1. Same words. No fuzzy score.
2. Accepted with a warning (`quote_gap`). Largest gap: 60 words. Real gaps stop at 42, and the next
   value is 414, so 60 sits in the empty space between them.
3. Treated like Sucampo: `quote_missing`. A program cannot tell the two apart (Round 2).
4. A warning (`quote_no_words`). The field may have other, better quotes.
</details>

Now the first half of the code. Put this in `src/docintel/domain/validate/citations.py`, and write
the two bodies yourself:

```python
"""Is a quote really in the contract? Compares words, in order, and never scores "how close"."""

import re

MAX_GAP = 60  # your decision: extra source words allowed between two quote words


def words(text: str) -> list[str]:
    """Lowercase words and numbers, in order. Spaces, case and punctuation are gone."""
    ...


def same_words(quote_words: list[str], source_words: list[str]) -> bool:
    """True if the quote's words appear in the source side by side, with nothing between."""
    ...
```

Hints:

1. `words` is one line. `re.findall` is in [1b2 PY-2](./py/phase-1b2.md#py-2).
2. For `same_words`, join each list into one string, and use `in`. Think about this trap: the words
   `["at"]` must not match inside `["that"]`.

<details><summary>Reference code (open after you try)</summary>

```python
def words(text: str) -> list[str]:
    """Lowercase words and numbers, in order. Spaces, case and punctuation are gone."""
    return re.findall(r"[a-z0-9]+", text.lower())


def same_words(quote_words: list[str], source_words: list[str]) -> bool:
    """True if the quote's words appear in the source side by side, with nothing between."""
    return f" {' '.join(quote_words)} " in f" {' '.join(source_words)} "
```

Here, we:

1. Keep only runs of letters and numbers, so spaces, case and punctuation stop mattering.
2. Put one space on each side of both strings, so `at` cannot match inside `that`.
</details>

*Python here: [`f" {' '.join(x)} "`](./py/phase-2a.md#py-2).*

Checkpoint. Guess each line first:

```sh
uv run python -c "
from docintel.domain.validate.citations import words, same_words
print(words('Such license shall be non-transferable.\n\n  FOR A \"TERM\"'))
source = words('without thewritten consent of Licensor. Page 7 The license is non-transferable.')
print(same_words(words('consent of  LICENSOR'), source))
print(same_words(words('consent of Licensor The license'), source))"
```

```text
['such', 'license', 'shall', 'be', 'non', 'transferable', 'for', 'a', 'term']
True
False
```

The last line is `False` because `page 7` sits between `licensor` and `the`.

## Step 3: gaps and the final status

**Why.** Page breaks are real, so we need a second, looser check. It must say "look at this", not
"this is fine".

Add to the bottom of `src/docintel/domain/validate/citations.py`, and write the bodies yourself:

```python
def follows_from(quote_words: list[str], source_words: list[str], start: int) -> bool:
    """True if the other quote words follow `start` in order, each within MAX_GAP extra words."""
    ...


def in_order(quote_words: list[str], source_words: list[str]) -> bool:
    """True if the quote's words appear in order somewhere, with small gaps allowed."""
    ...


def quote_status(quote: str, source_words: list[str]) -> str:
    """One of: no_words, same_words, gap, missing."""
    ...
```

Here is what each one does, on a small example. The quote is `consent of Licensor The license`, and
the source is `... consent of licensor page 7 the license is ...`.

1. `in_order` looks for each place where the source has the quote's first word, `consent`.
2. For each place, it calls `follows_from`.
3. `follows_from` looks for `of` in the next `MAX_GAP + 1` source words. It finds it, and moves there.
4. It does the same for `licensor`, then `the`. `page 7` is skipped, because the window is wide
   enough.
5. Every word was found, so the answer is `True`.
6. `quote_status` tries the checks from strict to loose, and returns the first that passes.

<details><summary>Reference code (open after you try)</summary>

```python
def follows_from(quote_words: list[str], source_words: list[str], start: int) -> bool:
    """True if the other quote words follow `start` in order, each within MAX_GAP extra words."""
    pos = start
    for word in quote_words[1:]:
        window = source_words[pos + 1 : pos + 2 + MAX_GAP]
        if word not in window:
            return False
        pos += 1 + window.index(word)
    return True


def in_order(quote_words: list[str], source_words: list[str]) -> bool:
    """True if the quote's words appear in order somewhere, with small gaps allowed."""
    return any(
        word == quote_words[0] and follows_from(quote_words, source_words, start)
        for start, word in enumerate(source_words)
    )


def quote_status(quote: str, source_words: list[str]) -> str:
    """One of: no_words, same_words, gap, missing."""
    quote_words = words(quote)
    if not quote_words:
        return "no_words"
    if same_words(quote_words, source_words):
        return "same_words"
    if in_order(quote_words, source_words):
        return "gap"
    return "missing"
```
</details>

*Python here: [a window with a slice, `in` and `.index`](./py/phase-2a.md#py-3) ·
[`any` with `enumerate`](./py/phase-2a.md#py-4).*

Checkpoint. Guess each line. Look closely at the last `in_order` line:

```sh
uv run python -c "
from docintel.domain.validate.citations import words, in_order, quote_status
source = words('without thewritten consent of Licensor. Page 7 The license is non-transferable.')
print(in_order(words('consent of Licensor The license'), source))
print(in_order(words('the license is transferable'), source))
for q in ['consent of licensor', 'Licensor. The license is', 'the written consent', '[●]']:
    print(repr(q), quote_status(q, source))"
```

```text
True
True
'consent of licensor' same_words
'Licensor. The license is' gap
'the written consent' missing
'[●]' no_words
```

The second line matters. The contract says `non-transferable`. The quote says `transferable`, which
means the opposite. `in_order` still says `True`, because `non` looks like a skipped word. This is
why `gap` is a warning.

Now reproduce Evidence 1, on real answers. You should get the same table. If your decisions are
different, your numbers can be too.

<details><summary>The command</summary>

```sh
uv run python - <<'EOF'
import json
from collections import Counter

from docintel.domain.validate.citations import quote_status, words
from docintel.evals.runner import cuad_txt
from docintel.evals.store import connect

RUNS = {
    "V4 (kept)": "20261102-200003",
    "V4 v1 Parasail": "20261105-213036",
    "E1": "20261101-192153",
    "Qwen3.8": "20261102-194826",
    "GLM-5.3": "20261102-200841",
    "V4.1": "20261102-202705",
}
print(
    f"{'run':15} {'quotes':>6} {'same_bytes':>10} {'same_words':>10} {'gap':>4} {'missing':>7} {'no_words':>8}"
)
with connect() as con:
    for name, run_id in RUNS.items():
        rows = con.execute("SELECT doc_id, answer FROM predictions WHERE run_id = ?", [run_id])
        status, n, same_bytes = Counter(), 0, 0
        for doc_id, answer in rows.fetchall():
            text = cuad_txt(con, doc_id)
            source_words = words(text)
            for quote in json.loads(answer)["quotes"]:
                n += 1
                same_bytes += quote in text
                status[quote_status(quote, source_words)] += 1
        print(
            f"{name:15} {n:6} {same_bytes:10} {status['same_words']:10} {status['gap']:4} "
            f"{status['missing']:7} {status['no_words']:8}"
        )
EOF
```

</details>

Look at the `missing` count for V4.1. Eight of its 9 are one strange quote, from one contract:

```text
{"quotes": ["value: null"], "found": false}
```

That is a real hallucinated quote. The model wrote part of the JSON format inside the `quotes` list.

## Step 4: field rules (your decision)

**Why.** A quote can be real while the rest of the field makes no sense.

Here are the candidate rules, and how often each one fails in the 5 stored runs:

```text
rule               V4 (kept)   E1  Qwen3.8  GLM-5.3  V4.1
found_no_quote             0    0        0        0     0
quote_not_found            0    6        0        0     8
found_no_value             3    4        1        3     1
value_not_found            0    0        0        0     0
bad_date                   0    0        0        0     0
```

The Parasail run adds only `found_no_value`, 4 times. Every other rule stays at 0.

What each one means, with real examples:

- **`found_no_quote`**: `found` is true, with no quotes. It never happens. It is still the most
  important rule, because the product promises a quote for each answer.
- **`quote_not_found`**: `found` is false, with a quote. Real example from E1: `found` is false, with
  the quote `This REMARKETING AGREEMENT, dated as of [●]`. The model is honest here: the date is
  blank. But prompt v1 says "no quotes" in this case.
- **`found_no_value`**: `found` is true, with an empty value. Real example from the kept model:
  `renewal_term` in the Pareteum contract, with the quote `automatically extended for consecutive
  *** periods`. The number is redacted, so no retry can ever find it.
- **`value_not_found`**: `found` is false, with a value.
- **`bad_date`**: `agreement_date` is not a real date. **0 of 270 dates fail in all 6 runs.** So this
  rule catches nothing today. It is one small function, and it guards against worse parsers and
  models later. Whether to keep it is your choice.

Decide these, and write them in your notebook cell:

1. **Which rules do you keep?**
2. **Error or warning?** A good test: "Could a retry fix this? Is a person needed?" Think about the
   redacted Pareteum field, and the honest `quote_not_found`.
3. **Date sanity.** Which formats are allowed? The prompt allows `YYYY`, `YYYY-MM` and `YYYY-MM-DD`.
   What is the oldest year you accept? Is a future date wrong?

<details><summary>Reference choice (open after you decide)</summary>

1. All five.
2. All five are errors: each one breaks a rule in prompt v1. The redacted Pareteum field stays an
   error too. 2b can see that a retry does not help, and that is a real result.
3. Only those three formats. It must be a real calendar date. Oldest year 1900. No future dates. A
   contract's date cannot be after today, and the stored answers run from 1995 to 2020.
</details>

Put this skeleton in `src/docintel/domain/validate/rules.py`, and write the bodies yourself:

```python
"""Content rules for one answer. Each field gets its own issues, so one bad field stays alone."""

import re
from datetime import date

from docintel.core.llm import LLMResult
from docintel.domain.schema.fields import ContractFields
from docintel.domain.validate.citations import quote_status, words
from docintel.domain.validate.issues import Issue


def date_ok(value: str) -> bool:
    """A real calendar date, in the prompt's format, not too old and not in the future."""
    ...


def check_quotes(field: str, quotes: list[str], source_words: list[str]) -> list[Issue]:
    """One issue per quote that is not clean."""
    ...


def check_found(field: str, answer) -> list[Issue]:
    """Do found, quotes and value agree with each other?"""
    ...


def check_field(field: str, answer, source_words: list[str]) -> list[Issue]:
    """All issues for one field."""
    ...
```

*Python here: [`date(...)` and `except ValueError`](./py/phase-2a.md#py-5) ·
[`re.compile` and `fullmatch`](./py/phase-2a.md#py-6) ·
[`hasattr`: a field with no `value`](./py/phase-2a.md#py-7).*

<details><summary>Reference code (open after you try)</summary>

```python
DATE_SHAPE = re.compile(r"\d{4}(-\d{2}(-\d{2})?)?")  # YYYY, YYYY-MM or YYYY-MM-DD, as in the prompt
OLDEST_YEAR = 1900


def date_ok(value: str) -> bool:
    """A real calendar date, in the prompt's format, not too old and not in the future."""
    if not DATE_SHAPE.fullmatch(value):
        return False
    year, month, day = (value.split("-") + ["01", "01"])[:3]  # a missing part counts as "01"
    try:
        parsed = date(int(year), int(month), int(day))
    except ValueError:  # like 2020-13-45
        return False
    return OLDEST_YEAR <= parsed.year and parsed <= date.today()


def check_quotes(field: str, quotes: list[str], source_words: list[str]) -> list[Issue]:
    """One issue per quote that is not clean."""
    issues = []
    for quote in quotes:
        status = quote_status(quote, source_words)
        short = quote[:80]
        if status == "missing":
            issues.append(Issue(field=field, rule="quote_missing", severity="error", detail=short))
        elif status == "gap":
            issues.append(Issue(field=field, rule="quote_gap", severity="warn", detail=short))
        elif status == "no_words":
            issues.append(Issue(field=field, rule="quote_no_words", severity="warn", detail=short))
    return issues


def check_found(field: str, answer) -> list[Issue]:
    """Do found, quotes and value agree with each other?"""
    problems = []
    if answer.found and not answer.quotes:
        problems.append(("found_no_quote", "found is true, but there are no quotes"))
    if not answer.found and answer.quotes:
        problems.append(("quote_not_found", "found is false, but there are quotes"))
    if hasattr(answer, "value"):
        if answer.found and not answer.value:
            problems.append(("found_no_value", "found is true, but value is empty"))
        if not answer.found and answer.value:
            problems.append(("value_not_found", "found is false, but value is not empty"))
    return [Issue(field=field, rule=r, severity="error", detail=d) for r, d in problems]


def check_field(field: str, answer, source_words: list[str]) -> list[Issue]:
    """All issues for one field."""
    issues = check_found(field, answer) + check_quotes(field, answer.quotes, source_words)
    if field == "agreement_date" and answer.value and not date_ok(answer.value):
        issues.append(Issue(field=field, rule="bad_date", severity="error", detail=answer.value))
    return issues
```

Here, we:

1. In `date_ok`, check the format first, then fill a missing month or day with `01`. `date(...)`
   refuses impossible dates like month 13.
2. In `check_quotes`, turn each status that is not clean into one issue. The detail is the first 80
   characters of the quote.
3. In `check_found`, collect `(rule, detail)` pairs, then turn them into issues. `Clause` has no
   `value`, so `hasattr` skips those rules for it.
4. In `check_field`, add the results together, and check the date only for `agreement_date`.
</details>

Checkpoint:

```sh
uv run python -c "
from docintel.domain.schema.fields import Text
from docintel.domain.validate.citations import words
from docintel.domain.validate.rules import check_field, date_ok
for v in ['2020-03', '2020-13-01', 'March 1, 2020', '2999-01-01']:
    print(f'{v:15} {date_ok(v)}')
source = words('This Agreement is dated as of March 1, 2020.')
good = Text(quotes=['dated as of March 1, 2020'], value='2020-03-01', found=True)
bad = Text(quotes=['dated as of March 2, 2020'], value='March 2', found=True)
empty = Text(quotes=[], value=None, found=True)
for answer in [good, bad, empty]:
    print([i.rule for i in check_field('agreement_date', answer, source)])"
```

```text
2020-03         True
2020-13-01      False
March 1, 2020   False
2999-01-01      False
[]
['quote_missing', 'bad_date']
['found_no_quote', 'found_no_value']
```

## Step 5: check a whole answer, on real data

**Why.** The rest of the pipeline holds a whole `LLMResult`, not one field.

Add to the bottom of `src/docintel/domain/validate/rules.py`, and write the bodies yourself:

```python
def check_answer(fields: ContractFields, text: str) -> list[Issue]:
    """All issues for one contract. The contract text is split into words only once."""
    ...


def bad_schema(detail: str) -> list[Issue]:
    """The answer did not fit the schema, so every field has this problem."""
    ...


def check_result(result: LLMResult[ContractFields], text: str) -> list[Issue]:
    """The issues for one LLM answer, whether or not it fit the schema."""
    ...
```

<details><summary>Reference code (open after you try)</summary>

```python
def check_answer(fields: ContractFields, text: str) -> list[Issue]:
    """All issues for one contract. The contract text is split into words only once."""
    source_words = words(text)
    issues = []
    for field in ContractFields.model_fields:
        issues += check_field(field, getattr(fields, field), source_words)
    return issues


def bad_schema(detail: str) -> list[Issue]:
    """The answer did not fit the schema, so every field has this problem."""
    return [
        Issue(field=field, rule="bad_schema", severity="error", detail=detail)
        for field in ContractFields.model_fields
    ]


def check_result(result: LLMResult[ContractFields], text: str) -> list[Issue]:
    """The issues for one LLM answer, whether or not it fit the schema."""
    if result.parsed is None:
        return bad_schema(result.error or "no answer")
    return check_answer(result.parsed, text)
```

</details>

*Python here: [`getattr` with a field name](./py/phase-2a.md#py-8).*

Here, we:

1. In `check_answer`, split the contract into words once, then check all 12 fields.
2. In `bad_schema`, handle an answer that did not fit the schema. It gets one issue per field, so
   later code has only one path: a list of issues.
3. In `check_result`, choose between the two.

Now replay your rules on two stored runs. No LLM call, no cost, and nothing is written:

<details><summary>The command</summary>

```sh
uv run python - <<'EOF'
from collections import Counter, defaultdict

from docintel.domain.validate.rules import check_answer
from docintel.evals.runner import cuad_txt, from_rows
from docintel.evals.store import connect

RUNS = {
    "V4 (kept)": "20261102-200003",
    "V4 v1 Parasail": "20261105-213036",
    "E1": "20261101-192153",
}


def f1(tp, fp, fn):
    return round(2 * tp / (2 * tp + fp + fn), 3)


with connect() as con:
    for name, run_id in RUNS.items():
        rows = con.execute(
            "SELECT doc_id, field, answer FROM predictions WHERE run_id = ?", [run_id]
        ).fetchall()
        by_doc = defaultdict(list)
        for doc_id, field, answer in rows:
            by_doc[doc_id].append((field, answer))
        issues = {
            doc_id: check_answer(from_rows(fields), cuad_txt(con, doc_id))
            for doc_id, fields in by_doc.items()
        }
        counts = Counter(i.rule for found in issues.values() for i in found)
        print(name, dict(counts.most_common()))
        scores = con.execute(
            "SELECT doc_id, tp, fp, fn, gold_present FROM scores WHERE run_id = ?", [run_id]
        ).fetchall()
        tp, fp, fn = (sum(s[i] for s in scores) for i in (1, 2, 3))
        print(f"  field by field: {tp} TP, F1 {f1(tp, fp, fn)}")
        for label, severities in [("errors", {"error"}), ("errors + warnings", {"error", "warn"})]:
            bad = {d for d, found in issues.items() if any(i.severity in severities for i in found)}
            good = [s for s in scores if s[0] not in bad]
            tp = sum(s[1] for s in good)
            fp = sum(s[2] for s in good)
            fn = sum(s[3] for s in good) + sum(s[4] for s in scores if s[0] in bad)
            print(f"  whole contract, {label}: {len(bad)} blanked, {tp} TP, F1 {f1(tp, fp, fn)}")
EOF
```

</details>

```text
V4 (kept) {'quote_gap': 6, 'found_no_value': 3, 'quote_no_words': 1}
  field by field: 290 TP, F1 0.912
  whole contract, errors: 2 blanked, 283 TP, F1 0.904
  whole contract, errors + warnings: 8 blanked, 248 TP, F1 0.845
V4 v1 Parasail {'quote_gap': 12, 'found_no_value': 4, 'quote_missing': 2}
  field by field: 283 TP, F1 0.907
  whole contract, errors: 5 blanked, 260 TP, F1 0.872
  whole contract, errors + warnings: 14 blanked, 194 TP, F1 0.746
E1 {'quote_gap': 9, 'quote_not_found': 6, 'found_no_value': 4, 'quote_missing': 3}
  field by field: 278 TP, F1 0.827
  whole contract, errors: 11 blanked, 220 TP, F1 0.733
  whole contract, errors + warnings: 18 blanked, 172 TP, F1 0.632
```

*Python here: `defaultdict`: [0d PY-3](./py/phase-0d.md#py-3) · `(x for ...)`:
[0b PY-5](./py/phase-0b.md#py-5).*

Read it:

1. The kept model has only 3 errors on 52 contracts, all `found_no_value`.
2. On Parasail, the same model and prompt have 6. The two `quote_missing` are fixes of broken text.
3. E1 has 13. So the same rules also measure how well a model follows the prompt.
4. "Whole contract" lines show what Option A from Step 1 would cost.
5. "Field by field" is exactly the F1 in `report`. Your rules did not change a score.

## Step 6: the test file

**Why.** A silent change here would mark real quotes as fake, or fake quotes as real.

Put this in `tests/test_validate.py`:

<details><summary>The test file</summary>

```python
"""Validator rules on fake model answers. No network, no key."""

import json

import pytest

from docintel.core.llm import LLMResult, _parse
from docintel.domain.schema.fields import ContractFields
from docintel.domain.validate.citations import quote_status, words
from docintel.domain.validate.rules import check_result, date_ok

CONTRACT = """This Agreement is dated as of March 1, 2020. Neither party may assign
this Agreement without consent.
Page 7
The license is non-transferable."""


def empty_answer() -> dict:
    """A valid answer for all 12 fields: nothing found."""
    answer = {field: {"quotes": [], "found": False} for field in ContractFields.model_fields}
    answer["parties"]["value"] = []
    for field in (
        "agreement_date",
        "governing_law",
        "renewal_term",
        "notice_period_to_terminate_renewal",
        "cap_on_liability",
    ):
        answer[field]["value"] = None
    return answer


def check(raw: str) -> list:
    """The same path as a real answer: parse the raw text, then check it."""
    parsed, error = _parse(ContractFields, raw)
    result = LLMResult(
        raw_text=raw,
        parsed=parsed,
        error=error,
        usage={},
        cost_usd=None,
        latency_ms=0,
        model="fake",
        provider=None,
        attempts=1,
    )
    return check_result(result, CONTRACT)


def rules(raw: str) -> list[tuple[str, str]]:
    return [(i.field, i.rule) for i in check(raw)]


def test_valid_answer_has_no_issues():
    answer = empty_answer()
    answer["agreement_date"] = {
        "quotes": ["dated as of March 1, 2020"],
        "value": "2020-03-01",
        "found": True,
    }
    assert rules(json.dumps(answer)) == []


def test_malformed_answer_marks_every_field():
    issues = check("")  # a real V4.1 answer: an empty reply
    assert {i.rule for i in issues} == {"bad_schema"}
    assert {i.field for i in issues} == set(ContractFields.model_fields)


def test_wrong_type_marks_every_field():
    answer = empty_answer()
    answer["non_compete"]["found"] = "yes"
    assert {i.rule for i in check(json.dumps(answer))} == {"bad_schema"}


def test_made_up_quote_is_an_error_in_that_field_only():
    answer = empty_answer()
    answer["anti_assignment"] = {"quotes": ["Either party may assign freely."], "found": True}
    assert rules(json.dumps(answer)) == [("anti_assignment", "quote_missing")]


def test_found_needs_quote_and_value():
    answer = empty_answer()
    answer["renewal_term"]["found"] = True
    assert rules(json.dumps(answer)) == [
        ("renewal_term", "found_no_quote"),
        ("renewal_term", "found_no_value"),
    ]


@pytest.mark.parametrize(
    ("quote", "status"),
    [
        ("Neither party may assign this Agreement", "same_words"),  # across a newline
        ("NEITHER  PARTY MAY ASSIGN", "same_words"),  # case and spaces
        ("consent. The license is non-transferable", "gap"),  # "Page 7" is in between
        ("Neither party may assign this Agreement with consent", "missing"),  # a changed word
        ("March 2, 2020", "missing"),  # a changed number
        ("[●]", "no_words"),
    ],
)
def test_quote_status(quote, status):
    assert quote_status(quote, words(CONTRACT)) == status


@pytest.mark.parametrize(
    ("value", "ok"),
    [
        ("2020", True),
        ("2020-03", True),
        ("2020-03-01", True),
        ("2020-13-01", False),
        ("March 1, 2020", False),
        ("2999-01-01", False),
        ("1066", False),
    ],
)
def test_date_ok(value, ok):
    assert date_ok(value) is ok
```

</details>

*Python here: `@pytest.mark.parametrize`: [1b2 PY-8](./py/phase-1b2.md#py-8).*

Here, we test each fake model response the plan asks for:

1. **Valid**: no issues.
2. **Malformed**: the empty string, a real V4.1 answer. Every field gets `bad_schema`.
3. **Wrong type**: `found` is `"yes"`. Same result.
4. **Hallucinated quote**: an error in that one field only. This is the promise from Step 1.

Then every status and every date case, so a change to your rules shows up at once.

Checkpoint:

```sh
uv run pytest tests/test_validate.py -q
make test
```

```text
..................                                                       [100%]
18 passed in 0.23s
```

```text
63 passed in 0.79s
```

`make lint` should also pass for your new files.

Your project structure is the same as in "Project setup". All the files now have code.

<details><summary>Full <code>src/docintel/domain/validate/citations.py</code></summary>

```python
"""Is a quote really in the contract? Compares words, in order, and never scores "how close"."""

import re

MAX_GAP = 60  # extra source words allowed between two quote words (real page breaks stop at 42)


def words(text: str) -> list[str]:
    """Lowercase words and numbers, in order. Spaces, case and punctuation are gone."""
    return re.findall(r"[a-z0-9]+", text.lower())


def same_words(quote_words: list[str], source_words: list[str]) -> bool:
    """True if the quote's words appear in the source side by side, with nothing between."""
    return f" {' '.join(quote_words)} " in f" {' '.join(source_words)} "


def follows_from(quote_words: list[str], source_words: list[str], start: int) -> bool:
    """True if the other quote words follow `start` in order, each within MAX_GAP extra words."""
    pos = start
    for word in quote_words[1:]:
        window = source_words[pos + 1 : pos + 2 + MAX_GAP]
        if word not in window:
            return False
        pos += 1 + window.index(word)
    return True


def in_order(quote_words: list[str], source_words: list[str]) -> bool:
    """True if the quote's words appear in order somewhere, with small gaps allowed."""
    return any(
        word == quote_words[0] and follows_from(quote_words, source_words, start)
        for start, word in enumerate(source_words)
    )


def quote_status(quote: str, source_words: list[str]) -> str:
    """One of: no_words, same_words, gap, missing."""
    quote_words = words(quote)
    if not quote_words:
        return "no_words"
    if same_words(quote_words, source_words):
        return "same_words"
    if in_order(quote_words, source_words):
        return "gap"
    return "missing"
```
</details>

<details><summary>Full <code>src/docintel/domain/validate/rules.py</code></summary>

```python
"""Content rules for one answer. Each field gets its own issues, so one bad field stays alone."""

import re
from datetime import date

from docintel.core.llm import LLMResult
from docintel.domain.schema.fields import ContractFields
from docintel.domain.validate.citations import quote_status, words
from docintel.domain.validate.issues import Issue

DATE_SHAPE = re.compile(r"\d{4}(-\d{2}(-\d{2})?)?")  # YYYY, YYYY-MM or YYYY-MM-DD, as in the prompt
OLDEST_YEAR = 1900


def date_ok(value: str) -> bool:
    """A real calendar date, in the prompt's format, not too old and not in the future."""
    if not DATE_SHAPE.fullmatch(value):
        return False
    year, month, day = (value.split("-") + ["01", "01"])[:3]  # a missing part counts as "01"
    try:
        parsed = date(int(year), int(month), int(day))
    except ValueError:  # like 2020-13-45
        return False
    return OLDEST_YEAR <= parsed.year and parsed <= date.today()


def check_quotes(field: str, quotes: list[str], source_words: list[str]) -> list[Issue]:
    """One issue per quote that is not clean."""
    issues = []
    for quote in quotes:
        status = quote_status(quote, source_words)
        short = quote[:80]
        if status == "missing":
            issues.append(Issue(field=field, rule="quote_missing", severity="error", detail=short))
        elif status == "gap":
            issues.append(Issue(field=field, rule="quote_gap", severity="warn", detail=short))
        elif status == "no_words":
            issues.append(Issue(field=field, rule="quote_no_words", severity="warn", detail=short))
    return issues


def check_found(field: str, answer) -> list[Issue]:
    """Do found, quotes and value agree with each other?"""
    problems = []
    if answer.found and not answer.quotes:
        problems.append(("found_no_quote", "found is true, but there are no quotes"))
    if not answer.found and answer.quotes:
        problems.append(("quote_not_found", "found is false, but there are quotes"))
    if hasattr(answer, "value"):
        if answer.found and not answer.value:
            problems.append(("found_no_value", "found is true, but value is empty"))
        if not answer.found and answer.value:
            problems.append(("value_not_found", "found is false, but value is not empty"))
    return [Issue(field=field, rule=r, severity="error", detail=d) for r, d in problems]


def check_field(field: str, answer, source_words: list[str]) -> list[Issue]:
    """All issues for one field."""
    issues = check_found(field, answer) + check_quotes(field, answer.quotes, source_words)
    if field == "agreement_date" and answer.value and not date_ok(answer.value):
        issues.append(Issue(field=field, rule="bad_date", severity="error", detail=answer.value))
    return issues


def check_answer(fields: ContractFields, text: str) -> list[Issue]:
    """All issues for one contract. The contract text is split into words only once."""
    source_words = words(text)
    issues = []
    for field in ContractFields.model_fields:
        issues += check_field(field, getattr(fields, field), source_words)
    return issues


def bad_schema(detail: str) -> list[Issue]:
    """The answer did not fit the schema, so every field has this problem."""
    return [
        Issue(field=field, rule="bad_schema", severity="error", detail=detail)
        for field in ContractFields.model_fields
    ]


def check_result(result: LLMResult[ContractFields], text: str) -> list[Issue]:
    """The issues for one LLM answer, whether or not it fit the schema."""
    if result.parsed is None:
        return bad_schema(result.error or "no answer")
    return check_answer(result.parsed, text)
```
</details>

## Break it on purpose

**Break 1: put a rule inside the schema (Option A).** This is how Pydantic validators work, so you
should try one once.

Do not run `score` during this break. `score` deletes the old rows first, so a crash would leave that
run with only part of its scores.

In `src/docintel/domain/schema/fields.py`, add `model_validator` to the Pydantic import, and add this
inside `class Text`:

```python
    @model_validator(mode="after")
    def found_needs_value(self):
        if self.found and not self.value:
            raise ValueError("found is true, but value is empty")
        return self
```

*Python here: [`@model_validator`](./py/phase-2a.md#py-9).*

Guess: does the provider see this rule? How many stored contracts can no longer be rebuilt?

<details><summary>The command</summary>

```sh
uv run python - <<'EOF'
from docintel.domain.schema.fields import ContractFields
from docintel.evals.runner import from_rows
from docintel.evals.store import connect

print("rule in the JSON schema:", "found_needs_value" in str(ContractFields.model_json_schema()))
RUN = "20261102-200003"
with connect() as con:
    docs = con.execute("SELECT DISTINCT doc_id FROM predictions WHERE run_id = ?", [RUN]).fetchall()
    broken = 0
    for (doc_id,) in sorted(docs):
        rows = con.execute(
            "SELECT field, answer FROM predictions WHERE run_id = ? AND doc_id = ?", [RUN, doc_id]
        ).fetchall()
        try:
            from_rows(rows)
        except ValueError as e:
            broken += 1
            print(doc_id[:30], "->", " ".join(str(e).splitlines()[:3])[:120])
print(f"{broken} of {len(docs)} contracts can no longer be rebuilt")
EOF
```

</details>

```text
rule in the JSON schema: False
PareteumCorp_20081001_8-K_EX-9 -> 2 validation errors for ContractFields renewal_term   Value error, found is true, but value is empty [type=value_error,
1 of 52 contracts can no longer be rebuilt
```

The validator is real Pydantic, and it works. But it fails the whole contract, the provider never
sees it, and an old run can no longer be rebuilt. Remove the validator and the import before you go on.

**Break 2: no gaps allowed.** Guess how many real quotes turn into `missing` at each `MAX_GAP`:

<details><summary>The command</summary>

```sh
uv run python - <<'EOF'
import json
from collections import Counter

from docintel.domain.validate import citations
from docintel.domain.validate.citations import quote_status, words
from docintel.evals.runner import cuad_txt
from docintel.evals.store import connect

RUN = "20261102-200003"
with connect() as con:
    rows = con.execute("SELECT doc_id, answer FROM predictions WHERE run_id = ?", [RUN]).fetchall()
    source = {d: words(cuad_txt(con, d)) for d, _ in rows}
for gap in (60, 5, 0):
    citations.MAX_GAP = gap
    status = Counter(quote_status(q, source[d]) for d, a in rows for q in json.loads(a)["quotes"])
    print(f"MAX_GAP {gap:2}: {dict(sorted(status.items()))}")
EOF
```

</details>

```text
MAX_GAP 60: {'gap': 6, 'no_words': 1, 'same_words': 417}
MAX_GAP  5: {'gap': 3, 'missing': 3, 'no_words': 1, 'same_words': 417}
MAX_GAP  0: {'missing': 6, 'no_words': 1, 'same_words': 417}
```

At `MAX_GAP` 0, the check reports 6 made-up quotes on a model that made up none.

## Experiment

This part makes no new run. The replay in Step 5 reads stored runs `20261102-200003`,
`20261105-213036` and `20261101-192153`. The results are logged in 2a2 as E2.0, with the review rules
added. Dev only: never replay on the test split to choose a rule.

## Gotchas

- **"Real" does not mean "right".** A quote that passes proves it is in the contract. It does not
  prove it answers the question. E1.3 counted wrong-quote TPs: 4 on Crusoe, 10 on Parasail. 2a2
  shows how often this happens.
- **`same_words` ignores punctuation.** `$100` and `100%` both become `100`. The quote check does not
  see that change.
- **A short quote passes easily.** `Company` is in almost every contract. The parties quotes are often
  this short.
- **The database is locked.** Close the notebook connection first.
- **`core/llm.py` still pins Parasail.** E1.3 added the pin for one experiment. 2a makes no calls, so
  it does not matter here. Decide the provider before the first new run in 2b.

## Explain back, then commit

Explain each changed file to Claude in a few sentences (the rule in `PLAN.md`):

- `issues.py`: why two severities?
- `citations.py`: each status, a real example of each, and why a gap is only a warning.
- `rules.py`: your rule decisions, and why one bad field stays alone.
- `test_validate.py`: what each fake response protects.

Then:

```sh
git status
git add src/docintel/domain/validate tests/test_validate.py notebooks/00_explore.ipynb
git commit -m "phase 2a: validators and quote checks"
```

## Conclusion

What you have now:

- `check_result`: an answer and its contract in, a list of issues out, field by field.
- A quote check with real evidence for each choice, and no fuzzy score.
- A real number for your write-up: the kept model made up 0 of 424 quotes on dev. On other
  Parasail, 2 quotes fail the check, and neither has made-up words.

Go back to the objectives. Check that you can do each one without notes. Then answer:

1. A quote has a fuzzy score of 0.99 against the contract, and its status is `missing`. Give a real
   way this can happen, and say why `missing` is the better answer.
2. Why can adding one sensible rule inside the Pydantic schema lower F1?

Want more practice? Try these (optional):

1. Run the Evidence 3 script. Add one more kind of change, like swapping two party names.
2. Find all 6 `gap` quotes of the kept model in the contract text. What are the skipped words?
3. Try the "squash" option: remove everything but letters and numbers, spaces too, then use `in`.
   Does it rescue Coral Gold? What could it wrongly accept?

Checklist (`../PLAN.md`): **Validation, citation check, retry with feedback; retry cost** (started:
validation and the citation check; 2a2 stores them; retry is in 2b). **Structured outputs: Pydantic
to JSON schema; enforcement vs validation** (done: you saw what the schema cannot enforce).
