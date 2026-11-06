# Phase 2a2: needs-review rules and stored issues (E2.0)

In this part, you decide which fields a person must look at. You write two small review rules, store
every issue in DuckDB, and measure how many real problems the flags catch. It uses stored runs only.
There are no LLM calls and no cost.

This is part 2 of 2 for Phase 2a. Part 1 built `check_result`. This part adds review rules to it, stores
its output, and logs E2.0: the "before" numbers for 2b.

## Words used in this part

Read these first. TP, FP, FN, issue, severity and replay are from earlier parts.

- **Needs review**: a person must look at this field before anyone trusts it. Example:
  `cap_on_liability` in the Kubient contract.
- **Flag**: the mark that says "needs review". In this project, a field with at least one issue.
- **Need a look**: a field the gold labels say is a problem. It is wrong (FP or FN), or right with the
  wrong quote. We only know this on dev, because it needs the labels.
- **Review rate**: flagged fields divided by all fields. Example: 35 of 624 is 5.6%. This is the
  person's work.
- **Catch rate**: flagged "need a look" fields, divided by all "need a look" fields. Example: 18 of 54.
  This is like recall, for the flag.
- **Off-topic quote**: a real quote that is about something else. Example: a `cap_on_liability` quote
  about how long you have to start a lawsuit.
- **Maybe missed**: the model says "not found", but the contract has words that often mean "found".
  Example: the heading `Limitation of Liability`.

## Objectives

By the end of this part you should be able to:

1. Say what a review flag should catch, and measure it with two numbers: review rate and catch rate.
2. Write two review rules from evidence, and give a real false alarm for each.
3. Store the issues of any stored run, with no LLM call, and run it again safely.
4. Give the honest result: how many real problems the flags catch, and why the others look clean.
5. Fill in E2.0, the "before" numbers for 2b.

## Dependencies

You install nothing new. This part needs:

- 2a: `Issue`, `check_answer`, `bad_schema` and `check_result` in `domain/validate/`.
- 1c: `TABLES`, `from_rows`, `score` and the CLI in `evals/runner.py`.
- 1d and 1d2: the E1.2 marks in `scores`, and the idea of a wrong-quote TP.

The reference numbers use the kept run `20261102-200003`, with the Parasail run `20261105-213036` as a
check, the same as in 2a.

## The big picture

Before this part, `check_result` returns a list of issues. Nothing stores it, and nothing says which
fields a person must read.

After this part:

```text
stored answers -> validate(run_id) -> issues table -> needs review: fields with an issue
                                                   -> review_report: rate, and what it catches
```

- **2b** reads the `error` issues and asks the model to try again. E2.0 is its "before".
- **Phase 3** runs `validate` on text from worse parsers.
- **Phase 4** shows the flags in the API and the UI.

## Remember this

> A review flag is a guess about which answers are wrong. Measure it like a model: how much work it
> gives a person (review rate), and how many real problems it finds (catch rate). Most wrong answers
> look clean, so a flag that catches a third of them at a 6% review rate is a real result, not a
> failure.
>
> **A flag is a guess. Count what it costs and what it catches.**

## Why

**The product promises a needs-review flag.** A lawyer cannot read 624 fields. They can read 35.

**2a only finds broken answers.** On the kept run, 2a's rules flag 10 fields, and only 6 of them are
real problems. Yet 54 fields need a look. Most wrong answers break no rule.

**2b needs a "before".** Retry lift means nothing without the error rate before the retry.

## Design decisions

- **Review rules return `warn` issues, in the same list.** So the API, 2b and the report all read one
  list. Other option: a separate `needs_review` column. Then each reader needs two paths.
- **Review rules never read the gold labels.** They live in `domain/validate/`, because the API runs
  them too. The measurement uses gold, so it lives in `evals/`. Other option: one function for both.
  Then the API would need labels that do not exist for a new contract.
- **The `issues` table has no primary key.** One field can have two issues of the same rule: two `gap`
  quotes. So a replay deletes the run's rows first, as `score` does. Other option: a key with a quote
  number. More columns, for no gain.
- **`validate` reads the text from the run's parser.** The quote check must use the text the model saw.
  Today it is always `cuad_txt`. In Phase 3 it will not be. Other option: always read `cuad_txt`. Then
  Phase 3 would check Docling answers against the wrong text.
- **A bad answer gets its issues from the `ok` column.** A stored bad answer is 12 empty fields, not the
  real answer. Break 2 shows why.

## Worked example

Real answers from the kept run. Guess before you open each box.

### Round 1: two wrong answers, one contract

The Kubient contract (Part 1). Both answers are wrong:

- `cap_on_liability`: `No action, suit or proceeding shall be brought against a Party more than one
  year after ...`
- `notice_period_to_terminate_renewal`: `Either Party may terminate this Agreement for any reason
  following the Initial Term upon ninety (90) days written notice to the other Party.`

Both quotes are really in the contract. Which one can a simple rule catch?

<details><summary>Guess, then open</summary>

The cap. A cap quote should talk about liability, damages, or an amount it cannot exceed. This one has
none of those words. It is about how long you have to start a lawsuit.

The notice quote has the word "notice", the value `90 days` has a good shape, and the quote is real. It
is the notice to end the contract at any time, not the notice to stop a renewal. No word check can see
that. 36 of the 54 problems on the kept run look like this one: clean.
</details>

### Round 2: a right answer with no topic word

The BlackStone contract, `notice_period_to_terminate_renewal`. Marked TP:

`at least 60 days prior to the end of the Initial Term, or any successive three-year term`

A rule says "a notice quote must contain `notice` or `notif`". What happens?

<details><summary>Guess, then open</summary>

It is flagged, and it is right. The word "notice" is in the sentence before. The model cut the quote
there. This is a false alarm. It is cheap, because it is only a warning: a person reads one line and
moves on. If the rule were an error, 2b would pay for a retry on a right answer.
</details>

### Round 3: the model says "not found"

Two contracts where the model says "not found", but the contract has the words:

- Antares, `cap_on_liability`: `9.4 Limitation of Liability. [***].`
- Old API, `renewal_term`: `... may cause any such license, certificate, approval or permit to be
  withdrawn, cancelled, suspended or not renewed.`

Which one is a real miss?

<details><summary>Guess, then open</summary>

Antares. The lawyers marked the cap as present. But the text is redacted (`[***]`), so no model could
give a value. The flag still helps: a person sees the clause exists and is hidden.

Old API is a false alarm. "not renewed" is about permits, not the contract. A word search on the whole
contract cannot tell these apart. So this rule needs a short list of fields, chosen from evidence.
</details>

## Project setup

DuckDB allows one writer at a time, so close the notebook connection before each checkpoint.

```sh
touch src/docintel/domain/validate/review.py tests/test_review.py
```

You should now have:

```text
src/docintel/
├── domain/validate/
│   ├── citations.py
│   ├── issues.py
│   ├── review.py          new: review rules
│   └── rules.py           + one line: add the review issues
└── evals/runner.py        + issues table, validate, review_report, CLI
tests/
└── test_review.py         new
```

## Step 1: what a flag should catch (your decision)

**Why.** You cannot measure a flag until you say what it should find.

Run this. It sorts the problems on two runs by kind:

```sh
uv run python - <<'EOF'
from docintel.evals.store import connect

LOOK = """
SELECT CASE WHEN fp > 0 AND fn > 0 THEN 'wrong' WHEN fp > 0 THEN 'made up'
            WHEN fn > 0 THEN 'missed' ELSE 'right, wrong quote' END AS kind, count(*) AS n
FROM scores
WHERE run_id = ? AND (fp + fn > 0 OR (rule = 'presence' AND tp > 0 AND quote_ok IS FALSE))
GROUP BY kind ORDER BY n DESC
"""
with connect() as con:
    for run in ("20261102-200003", "20261105-213036"):
        print(run, con.execute(LOOK, [run]).fetchall())
EOF
```

*Python here: [`CASE WHEN`](./py/phase-2a2.md#py-1).*

```text
20261102-200003 [('made up', 30), ('missed', 14), ('wrong', 6), ('right, wrong quote', 4)]
20261105-213036 [('made up', 23), ('missed', 19), ('right, wrong quote', 10), ('wrong', 8)]
```

Here:

1. `made up` is an FP: the model found something the lawyers did not mark.
2. `missed` is an FN: the lawyers marked it, and the model said "not found".
3. `wrong` is both: the model found the clause, but the wrong part.
4. `right, wrong quote` is the wrong-quote TP from 1d2: the mark is right by luck.

That is 54 on the kept run, and 60 on Parasail. The first 50 of the kept run are the E1.2 errors.

Decide, and write it in a "Review rules" cell in your notebook:

1. **Which kinds should a flag catch?** All four? Should a wrong-quote TP count as a problem?
2. **Which kind costs a lawyer most?** Think about a missed non-compete against a made-up one.

<details><summary>Reference choice (open after you decide)</summary>

1. All four. A person reads the quote, so a right mark with the wrong quote still misleads them.
2. `missed`. A made-up clause is checked when the person reads its quote. A missed clause has no quote
   to read, so nobody looks. So the report counts misses on their own line.
</details>

## Step 2: review rules (your decision)

**Why.** 2a's rules catch 6 of 54. You need rules that read more than the shape of an answer.

The candidates, all from Round 1 to 3:

- **A. 2a issues only.** Every field with an `error` or a `warn` from 2a.
- **B. A, plus off-topic quotes.** For each field, a short list of word parts. A found answer whose
  quotes hold none of them gets a warning. Parties and dates have no list.
- **C. B, plus maybe missed.** For a few fields, a pattern. A "not found" answer whose contract matches
  it gets a warning.
- **D. Every weak field.** Flag all four fields with E1.2 F1 under 0.8, always.

Run this to see each option on both runs. It uses your 2a `check_answer`, plus candidate word lists
and patterns written before looking at the results:

<details><summary>The command</summary>

```sh
uv run python - <<'EOF'
import re
from collections import defaultdict

from docintel.domain.schema.fields import ContractFields
from docintel.domain.validate.rules import check_answer
from docintel.evals.runner import cuad_txt, from_rows
from docintel.evals.store import connect

TOPIC = {
    "governing_law": ("govern", "law"),
    "non_compete": ("compet",),
    "change_of_control": ("control", "merger", "acqui", "change"),
    "anti_assignment": ("assign", "transfer"),
    "renewal_term": ("renew", "extend", "extension", "successive"),
    "notice_period_to_terminate_renewal": ("notice", "notif"),
    "cap_on_liability": ("liab", "damage", "exceed"),
    "license_grant": ("licens", "grant"),
    "ip_ownership_assignment": ("own", "assign", "title", "propert"),
    "non_transferable_license": ("transfer", "assign", "sublicens"),
}
PHRASE = {
    "non_compete": r"\bnon-?compet|\bnot\b[^.;]{0,40}\bcompet",
    "change_of_control": r"change (of|in) control",
    "anti_assignment": r"\bassign",
    "renewal_term": r"\brenew",
    "cap_on_liability": r"limitation of liability|liability[^.;]{0,60}(shall not|will not|not) exceed",
}
WEAK = {"non_compete", "change_of_control", "notice_period_to_terminate_renewal", "cap_on_liability"}


def signals(con, run):
    """For each signal, the (doc_id, field) pairs it flags."""
    rows = con.execute("SELECT doc_id, field, answer FROM predictions WHERE run_id = ?", [run])
    by_doc = defaultdict(list)
    for doc_id, field, answer in rows.fetchall():
        by_doc[doc_id].append((field, answer))
    sig = defaultdict(set)
    for doc_id, fields in by_doc.items():
        pred, text = from_rows(fields), cuad_txt(con, doc_id)
        sig["A"] |= {(doc_id, i.field) for i in check_answer(pred, text)}
        for field in ContractFields.model_fields:
            a = getattr(pred, field)
            quotes = " ".join(a.quotes).lower()
            if field in TOPIC and a.found and not any(p in quotes for p in TOPIC[field]):
                sig["topic"].add((doc_id, field))
            if field in PHRASE and not a.found and re.search(PHRASE[field], text, re.I):
                sig[field].add((doc_id, field))
            if field in WEAK:
                sig["D"].add((doc_id, field))
    return sig


LOOK_ROWS = """
SELECT doc_id, field, fn > 0 AND fp = 0 FROM scores
WHERE run_id = ? AND (fp + fn > 0 OR (rule = 'presence' AND tp > 0 AND quote_ok IS FALSE))
"""
with connect() as con:
    for run in ("20261102-200003", "20261105-213036"):
        look = {(d, f): missed for d, f, missed in con.execute(LOOK_ROWS, [run]).fetchall()}
        sig = signals(con, run)
        phrases = set().union(*(sig[f] for f in PHRASE))
        options = {
            "A  2a issues": sig["A"],
            "B  A + off-topic": sig["A"] | sig["topic"],
            "C  B + maybe missed": sig["A"] | sig["topic"] | phrases,
            "D  every weak field": sig["D"],
        }
        print(f"{run}: {len(look)} need a look, {sum(look.values())} missed")
        for name, flagged in {**options, **{f"   {f}": sig[f] for f in PHRASE}}.items():
            hit = [look[k] for k in flagged if k in look]
            print(f"  {name:38} {len(flagged):3} flags ({len(flagged) / 624:5.1%})"
                  f"  caught {len(hit):2}  missed {sum(hit)}")
EOF
```

*Python here: [`set().union(*sets)` and `|=`](./py/phase-2a2.md#py-2) ·
[`re.search`](./py/phase-1d.md#py-4) · [set operators](./py/phase-1b2.md#py-3).*

</details>

```text
20261102-200003: 54 need a look, 14 missed
  A  2a issues                            10 flags ( 1.6%)  caught  6  missed 0
  B  A + off-topic                        25 flags ( 4.0%)  caught 14  missed 0
  C  B + maybe missed                     44 flags ( 7.1%)  caught 19  missed 5
  D  every weak field                    208 flags (33.3%)  caught 35  missed 11
     non_compete                           4 flags ( 0.6%)  caught  0  missed 0
     change_of_control                     2 flags ( 0.3%)  caught  1  missed 1
     anti_assignment                       5 flags ( 0.8%)  caught  1  missed 1
     renewal_term                          7 flags ( 1.1%)  caught  2  missed 2
     cap_on_liability                      1 flags ( 0.2%)  caught  1  missed 1
20261105-213036: 60 need a look, 19 missed
  A  2a issues                            17 flags ( 2.7%)  caught  5  missed 0
  B  A + off-topic                        33 flags ( 5.3%)  caught 13  missed 0
  C  B + maybe missed                     57 flags ( 9.1%)  caught 19  missed 6
  D  every weak field                    208 flags (33.3%)  caught 30  missed 13
     non_compete                           4 flags ( 0.6%)  caught  0  missed 0
     change_of_control                     3 flags ( 0.5%)  caught  0  missed 0
     anti_assignment                       5 flags ( 0.8%)  caught  1  missed 1
     renewal_term                          8 flags ( 1.3%)  caught  2  missed 2
     cap_on_liability                      4 flags ( 0.6%)  caught  3  missed 3
```

Read it:

1. **Off-topic doubles the catch** on both runs (6 to 14, 5 to 13), for about 15 more flags. About half of
   its flags are real problems.
2. **Only "maybe missed" finds misses.** No rule that reads the answer can see a miss, because a miss
   has no quote.
3. **The phrase fields are not equal.** `non_compete` flags 8 times on the two runs and catches 0.
   `anti_assignment` flags 10 and catches 2. `cap_on_liability` catches 4 of 5.
4. **D catches the most, at 33% of all fields.** That is close to reading every weak field by hand.
5. **No option catches more than 35 of 54.** Some wrong answers look exactly like right ones.

Decide, and write them in your "Review rules" cell:

1. **Which option?** Or a mix. Name the review rate you accept.
2. **The word lists.** Keep, cut or change each one. Write them before you run anything new.
3. **Which fields get "maybe missed"?** Use the per-field rows.
4. **What makes a field "needs review"?** Any issue? Or only some rules?
5. **Error or warning** for the new rules? Think about Round 2, and about 2b paying for retries.

<details><summary>Reference choice (open after you decide)</summary>

1. C, with a review rate under 10% on both runs. The extra work over B is small, and misses are the
   costly kind (Step 1).
2. The word lists above, as written.
3. `cap_on_liability`, `change_of_control` and `renewal_term`. Drop `non_compete` (0 caught in 8) and
   `anti_assignment` (the word "assign" is in almost every contract).
4. Any issue, of any severity. One simple rule that a person can understand.
5. Warnings. Round 2 is a right answer, and a retry cannot fix a redacted clause.
</details>

## Step 3: build the review rules

**Why.** Your Step 2 choices become code that the API can run on a new contract.

Put this skeleton in `src/docintel/domain/validate/review.py`, fill in your lists, and write the
bodies yourself:

```python
"""Should a person look at this field? These rules read the answer and the contract, never gold."""

import re

from docintel.domain.schema.fields import ContractFields
from docintel.domain.validate.issues import Issue

TOPIC = {}  # field -> word parts; a quote for this field should hold at least one
MISSED = {}  # field -> re.compile(...); "not found", but the contract has these words


def off_topic(field: str, answer) -> list[Issue]:
    """A real quote can still be about something else. Example: a notice quote with no "notice"."""
    ...


def maybe_missed(field: str, answer, text: str) -> list[Issue]:
    """The model says "not found", but the contract has words that often mean "found"."""
    ...


def review_answer(fields: ContractFields, text: str) -> list[Issue]:
    """The review issues for one contract: warnings only, so they never change an answer."""
    ...


def needs_review(issues: list[Issue]) -> set[str]:
    """The fields a person must look at: every field with at least one issue."""
    ...
```

*Python here: [`match.group(0)` and `is None`](./py/phase-2a2.md#py-3).*

<details><summary>Reference code (open after you try)</summary>

```python
TOPIC = {  # a quote for this field should hold at least one of these word parts
    "governing_law": ("govern", "law"),
    "non_compete": ("compet",),
    "change_of_control": ("control", "merger", "acqui", "change"),
    "anti_assignment": ("assign", "transfer"),
    "renewal_term": ("renew", "extend", "extension", "successive"),
    "notice_period_to_terminate_renewal": ("notice", "notif"),
    "cap_on_liability": ("liab", "damage", "exceed"),
    "license_grant": ("licens", "grant"),
    "ip_ownership_assignment": ("own", "assign", "title", "propert"),
    "non_transferable_license": ("transfer", "assign", "sublicens"),
}
MISSED = {  # the model says "not found", but the contract has these words
    "change_of_control": re.compile(r"change (of|in) control", re.I),
    "cap_on_liability": re.compile(
        r"limitation of liability|liability[^.;]{0,60}(shall not|will not|not) exceed", re.I
    ),
    "renewal_term": re.compile(r"\brenew", re.I),
}


def off_topic(field: str, answer) -> list[Issue]:
    """A real quote can still be about something else. Example: a notice quote with no "notice"."""
    if field not in TOPIC or not answer.found or not answer.quotes:
        return []
    quotes = " ".join(answer.quotes).lower()
    if any(part in quotes for part in TOPIC[field]):
        return []
    detail = answer.quotes[0][:80]
    return [Issue(field=field, rule="quote_off_topic", severity="warn", detail=detail)]


def maybe_missed(field: str, answer, text: str) -> list[Issue]:
    """The model says "not found", but the contract has words that often mean "found"."""
    if field not in MISSED or answer.found:
        return []
    match = MISSED[field].search(text)
    if match is None:
        return []
    return [Issue(field=field, rule="maybe_missed", severity="warn", detail=match.group(0)[:80])]


def review_answer(fields: ContractFields, text: str) -> list[Issue]:
    """The review issues for one contract: warnings only, so they never change an answer."""
    issues = []
    for field in ContractFields.model_fields:
        answer = getattr(fields, field)
        issues += off_topic(field, answer) + maybe_missed(field, answer, text)
    return issues


def needs_review(issues: list[Issue]) -> set[str]:
    """The fields a person must look at: every field with at least one issue."""
    return {issue.field for issue in issues}
```

</details>

Here, we:

1. Skip a field with no list, or with nothing found. `found_no_quote` from 2a already covers "found,
   but no quotes".
2. Join all quotes of a field, so one on-topic quote is enough.
3. Keep the matched words as the detail. A person sees why the field was flagged.
4. Return warnings only. A review rule never changes an answer, so F1 stays the same.

Now one line joins the two lists. In `src/docintel/domain/validate/rules.py`, update the imports:

```python
from docintel.domain.validate.review import review_answer
```

And change the last line of `check_answer`:

```python
    return issues + review_answer(fields, text)
```

Here, we keep 2a's one path: every reader gets one list from `check_result`.

Checkpoint, on Round 1's contract:

```sh
uv run python - <<'EOF'
from docintel.domain.validate.review import needs_review
from docintel.domain.validate.rules import check_answer
from docintel.evals.runner import cuad_txt, from_rows
from docintel.evals.store import connect

RUN = "20261102-200003"
with connect() as con:
    (doc,) = con.execute(
        "SELECT DISTINCT doc_id FROM predictions WHERE run_id = ? AND doc_id LIKE 'KUBIENT%Part1'", [RUN]
    ).fetchone()
    rows = con.execute(
        "SELECT field, answer FROM predictions WHERE run_id = ? AND doc_id = ?", [RUN, doc]
    ).fetchall()
    issues = check_answer(from_rows(rows), cuad_txt(con, doc))
for issue in issues:
    print(issue.field, issue.rule, issue.severity, issue.detail[:50])
print(needs_review(issues))
EOF
```

```text
cap_on_liability quote_off_topic warn No action, suit or proceeding shall be brought aga
{'cap_on_liability'}
```

The cap is flagged. The wrong notice answer is not, as Round 1 said. Run `make test`: the 2a tests still
pass, because their fake contract has none of the "maybe missed" words.

## Step 4: a shape rule for durations (your decision)

**Why.** 2a left this open: `renewal_term` and `notice_period_to_terminate_renewal` hold a duration,
like `90 days`. Should a value with no number and no unit be flagged?

The evidence. A simple pattern, "a number, then day, week, month or year", on every found value:

<details><summary>The command</summary>

```sh
uv run python - <<'EOF'
import json
import re

from docintel.evals.store import connect

DURATION = re.compile(
    r"\b(\d+|one|two|three|four|five|six|twelve|thirty|sixty|ninety)\b.*\b(day|week|month|year)s?\b", re.I
)
RUNS = {"V4 (kept)": "20261102-200003", "V4 v1 Parasail": "20261105-213036", "E1": "20261101-192153"}
FIELDS = "('renewal_term', 'notice_period_to_terminate_renewal')"
print(f"{'run':16} {'values':>6} {'do not fit':>12}")
with connect() as con:
    for name, run in RUNS.items():
        rows = con.execute(
            f"SELECT answer FROM predictions WHERE run_id = ? AND found AND field IN {FIELDS}", [run]
        ).fetchall()
        values = [json.loads(a)["value"] for (a,) in rows]
        bad = [v for v in values if v and not DURATION.search(v)]
        print(f"{name:16} {len(values):6} {len(bad):12}")
EOF
```

</details>

```text
run              values   do not fit
V4 (kept)            34            0
V4 v1 Parasail       29            0
E1                   47            5
```

The 5 from E1: `successive annual periods`, `indefinitely`, `terms set forth in a proposal`, a long
sentence about another agreement, and a date, `November 30, 2004`.

Decide: add the rule, or not?

<details><summary>Reference choice (open after you decide)</summary>

No rule. It catches nothing on the model we use. Two of E1's five (`successive annual periods`,
`indefinitely`) are fair answers that the rule would flag. A rule with no catches and known false alarms
only adds work. Phase 3 can add it if worse parsers make it fire.
</details>

## Step 5: store the issues

**Why.** A number in E2.0 must trace to rows in DuckDB, the same as F1 traces to `scores`.

In `src/docintel/evals/runner.py`, add the table to the end of `TABLES`, before the closing `"""`:

```sql
CREATE TABLE IF NOT EXISTS issues (
    run_id VARCHAR, doc_id VARCHAR, field VARCHAR, rule VARCHAR, severity VARCHAR, detail VARCHAR
);
```

Update the imports at the top of `src/docintel/evals/runner.py`:

```python
from docintel.domain.validate.rules import bad_schema, check_answer
```

Add this function after `score`:

```python
def validate(con: duckdb.DuckDBPyConnection, run_id: str) -> int:
    """(Re)check one run from its stored predictions. No LLM call. Returns the number of issues."""
    (parser,) = con.execute("SELECT parser FROM runs WHERE run_id = ?", [run_id]).fetchone()
    rows = con.execute(
        "SELECT doc_id, field, ok, answer FROM predictions WHERE run_id = ?", [run_id]
    ).fetchall()
    by_doc = defaultdict(list)
    for doc_id, field, ok, answer in rows:
        by_doc[doc_id].append((field, ok, answer))
    con.execute("DELETE FROM issues WHERE run_id = ?", [run_id])
    total = 0
    for doc_id, fields in by_doc.items():
        if not all(ok for _, ok, _ in fields):  # the stored fields are empty, not the real answer
            issues = bad_schema("the answer did not fit the schema")
        else:
            pred = from_rows([(field, answer) for field, _, answer in fields])
            issues = check_answer(pred, PARSERS[parser](con, doc_id))
        new = [(run_id, doc_id, i.field, i.rule, i.severity, i.detail) for i in issues]
        if new:  # DuckDB's executemany fails on an empty list
            con.executemany("INSERT INTO issues VALUES (?, ?, ?, ?, ?, ?)", new)
        total += len(new)
    return total
```

*Python here: [`_` for values you skip](./py/phase-2a2.md#py-4).*

Here, we:

1. Read the run's parser from `runs`, so the check uses the text the model saw.
2. Group the 12 rows of each contract, as `score` does.
3. Delete the run's old issues first. So a replay replaces the rows, and never adds to them.
4. Use `bad_schema` when the stored answer was bad. Its stored fields are empty, so checking them would
   find nothing.

Now the CLI. In `parse_args`, after the `report` subcommand:

```python
    check = sub.add_parser("validate", help="check a stored run again and store the issues")
    check.add_argument("run_id")
```

In `main`, after the `report` block:

```python
        if args.command == "validate":
            print(f"stored {validate(con, args.run_id)} issues for run {args.run_id}")
            return
```

And in the `run` path, right after `n = score(con, run_id)`:

```python
        validate(con, run_id)
```

So every new run in 2b gets its issues stored, with no extra command.

Checkpoint:

```sh
uv run python -m docintel.evals.runner validate 20261102-200003
uv run python -m docintel.evals.runner validate 20261102-200003
```

```text
stored 35 issues for run 20261102-200003
stored 35 issues for run 20261102-200003
```

The same number twice. The second run replaced the first.

## Step 6: the review report

**Why.** The two numbers from "Remember this", printed for any run.

Add to `src/docintel/evals/runner.py`, after `validate`:

```python
REVIEW = """
WITH flagged AS (SELECT DISTINCT doc_id, field FROM issues WHERE run_id = $run_id),
errors AS (SELECT DISTINCT doc_id, field FROM issues WHERE run_id = $run_id AND severity = 'error'),
look AS (  -- from the gold labels: wrong, or right with the wrong quote
    SELECT doc_id, field, fn > 0 AND fp = 0 AS missed FROM scores
    WHERE run_id = $run_id AND (fp + fn > 0 OR (rule = 'presence' AND tp > 0 AND quote_ok IS FALSE))
)
SELECT
    (SELECT count(*) FROM predictions WHERE run_id = $run_id),
    (SELECT count(*) FROM errors),
    (SELECT count(DISTINCT doc_id) FROM errors),
    (SELECT count(*) FROM flagged),
    (SELECT count(DISTINCT doc_id) FROM flagged),
    (SELECT count(*) FROM look),
    (SELECT count(*) FROM look WHERE missed),
    (SELECT count(*) FROM flagged JOIN look USING (doc_id, field)),
    (SELECT count(*) FROM flagged JOIN look USING (doc_id, field) WHERE missed)
"""


def review_report(con: duckdb.DuckDBPyConnection, run_id: str) -> None:
    """Print the error rate, the review rate, and how many real problems the flags catch."""
    n, err, err_docs, flags, flag_docs, look, missed, caught, caught_missed = con.execute(
        REVIEW, {"run_id": run_id}
    ).fetchone()
    print(f"errors: {err} fields ({err / n:.1%}) in {err_docs} contracts")
    print(f"needs review: {flags} fields ({flags / n:.1%}) in {flag_docs} contracts")
    print(f"need a look (gold): {look} fields, {missed} of them missed")
    print(f"caught: {caught} of {look}, and {caught_missed} of the {missed} missed")
    rules = con.execute(
        "SELECT rule, count(*) FROM issues WHERE run_id = ? GROUP BY rule ORDER BY 2 DESC", [run_id]
    ).fetchall()
    print("by rule:", ", ".join(f"{rule} {count}" for rule, count in rules))
```

*Python here: [`$run_id` placeholders](./py/phase-0d.md#py-5) ·
[a query inside `SELECT`](./py/phase-1c3.md#py-6).*

Here, we:

1. Count each field once in `flagged`, even when it has two issues.
2. Build `look` from `scores`, as in Step 1. This is the only part that reads gold labels.
3. Count `n` from `predictions`, so a run with no scores does not divide by 0.
4. Join `flagged` and `look` to count what the flags catch.

In `main`, call it after the `validate` print:

```python
            review_report(con, args.run_id)
```

Checkpoint, on all three stored runs:

```sh
for run in 20261102-200003 20261105-213036 20261101-192153; do
  uv run python -m docintel.evals.runner validate $run; echo
done
```

```text
stored 35 issues for run 20261102-200003
errors: 3 fields (0.5%) in 2 contracts
needs review: 35 fields (5.6%) in 27 contracts
need a look (gold): 54 fields, 14 of them missed
caught: 18 of 54, and 4 of the 14 missed
by rule: quote_off_topic 15, maybe_missed 10, quote_gap 6, found_no_value 3, quote_no_words 1

stored 49 issues for run 20261105-213036
errors: 6 fields (1.0%) in 5 contracts
needs review: 48 fields (7.7%) in 30 contracts
need a look (gold): 60 fields, 19 of them missed
caught: 18 of 60, and 5 of the 19 missed
by rule: quote_off_topic 16, maybe_missed 15, quote_gap 12, found_no_value 4, quote_missing 2

stored 49 issues for run 20261101-192153
errors: 13 fields (2.1%) in 11 contracts
needs review: 48 fields (7.7%) in 36 contracts
need a look (gold): 105 fields, 13 of them missed
caught: 25 of 105, and 3 of the 13 missed
by rule: quote_off_topic 19, quote_gap 9, maybe_missed 8, quote_not_found 6, found_no_value 4, quote_missing 3
```

Read it:

1. **Errors are rare on V4.** 3 fields in 2 contracts on the kept run. 2b can only retry these. So retry
   lift on clean text will be small, at most.
2. **The review rate is low per field, high per contract.** 5.6% of fields, but 27 of 52 contracts have
   at least one flag. A person opens half the contracts, and reads one or two fields in each.
3. **The catch is a third.** 18 of 54 on the kept run. The other 36 look clean (Round 1).
4. **E1 makes more problems, and the same rules catch a smaller share.** 25 of 105. Its errors are
   more often clean-looking ones.
5. **The made-up quote count is the 2a result.** `quote_missing` is 0 on the kept run, and 2 on Parasail
   (neither has made-up words, from 2a).

## Step 7: the test file

**Why.** Two things must never break without a test failing: a review rule only warns, and a replay
replaces rows.

<details><summary>Put this in <code>tests/test_review.py</code></summary>

```python
"""Review rules and stored issues on fake answers. No network, no key, no CUAD files."""

import json

from docintel.domain.schema.fields import ContractFields
from docintel.domain.validate.review import needs_review, review_answer
from docintel.evals import runner
from docintel.evals.store import connect

CONTRACT = """Limitation of Liability. Neither party's liability shall exceed the fees paid.
Either party may terminate this Agreement upon 90 days written notice."""


def answer(**fields) -> ContractFields:
    """All 12 fields not found, except the ones given."""
    data = {field: runner.empty_answer(field) for field in ContractFields.model_fields}
    return ContractFields.model_validate(data | fields)


def test_off_topic_quote_is_flagged():
    quote = "Either party may terminate this Agreement"
    pred = answer(non_compete={"quotes": [quote], "found": True})
    assert [(i.field, i.rule) for i in review_answer(pred, CONTRACT)] == [
        ("non_compete", "quote_off_topic"),
        ("cap_on_liability", "maybe_missed"),
    ]


def test_found_cap_is_not_flagged():
    quote = "Neither party's liability shall exceed the fees paid."
    pred = answer(cap_on_liability={"quotes": [quote], "value": "the fees paid", "found": True})
    assert review_answer(pred, CONTRACT) == []


def test_review_issues_are_only_warnings():
    pred = answer(non_compete={"quotes": ["upon 90 days written notice"], "found": True})
    issues = review_answer(pred, CONTRACT)
    assert {i.severity for i in issues} == {"warn"}
    assert needs_review(issues) == {"non_compete", "cap_on_liability"}


def test_validate_replays_and_marks_bad_answers(monkeypatch):
    monkeypatch.setitem(runner.PARSERS, "cuad_txt", lambda con, doc_id: CONTRACT)
    fields = answer().model_dump()
    good = [("r1", "d1", f, True, False, json.dumps(a)) for f, a in fields.items()]
    bad = [("r1", "d2", f, False, False, json.dumps(a)) for f, a in fields.items()]
    with connect(":memory:") as con:
        con.execute(runner.TABLES)
        con.execute("INSERT INTO runs (run_id, parser) VALUES ('r1', 'cuad_txt')")
        con.executemany("INSERT INTO predictions VALUES (?, ?, ?, ?, ?, ?)", good + bad)
        first = runner.validate(con, "r1")
        again = runner.validate(con, "r1")  # a replay replaces the rows, it does not add to them
        rules = con.execute("SELECT doc_id, rule, count(*) FROM issues GROUP BY ALL ORDER BY 1")
        rules = rules.fetchall()
    assert first == again == 13
    assert rules == [("d1", "maybe_missed", 1), ("d2", "bad_schema", 12)]
```

</details>

*Python here: [dict merge `|`](./py/phase-0b.md#py-6) ·
[`monkeypatch.setitem`](./py/phase-2a2.md#py-5) · [`GROUP BY ALL`](./py/phase-2a2.md#py-6) ·
[`first == again == 13`](./py/phase-2a2.md#py-7).*

Here, each test protects one thing:

1. An off-topic quote is flagged, and a "not found" cap with the words in the contract is flagged.
2. An on-topic, found cap gets no warning.
3. Review rules only warn, and `needs_review` lists the right fields.
4. A bad stored answer gets 12 `bad_schema` issues, and a second replay gives the same count.

Checkpoint:

```sh
make test
make lint
```

```text
67 passed in 0.84s
```

`make lint` should also pass: `All checks passed!` and `41 files already formatted`.

<details><summary>Full <code>src/docintel/domain/validate/review.py</code></summary>

```python
"""Should a person look at this field? These rules read the answer and the contract, never gold."""

import re

from docintel.domain.schema.fields import ContractFields
from docintel.domain.validate.issues import Issue

TOPIC = {  # a quote for this field should hold at least one of these word parts
    "governing_law": ("govern", "law"),
    "non_compete": ("compet",),
    "change_of_control": ("control", "merger", "acqui", "change"),
    "anti_assignment": ("assign", "transfer"),
    "renewal_term": ("renew", "extend", "extension", "successive"),
    "notice_period_to_terminate_renewal": ("notice", "notif"),
    "cap_on_liability": ("liab", "damage", "exceed"),
    "license_grant": ("licens", "grant"),
    "ip_ownership_assignment": ("own", "assign", "title", "propert"),
    "non_transferable_license": ("transfer", "assign", "sublicens"),
}
MISSED = {  # the model says "not found", but the contract has these words
    "change_of_control": re.compile(r"change (of|in) control", re.I),
    "cap_on_liability": re.compile(
        r"limitation of liability|liability[^.;]{0,60}(shall not|will not|not) exceed", re.I
    ),
    "renewal_term": re.compile(r"\brenew", re.I),
}


def off_topic(field: str, answer) -> list[Issue]:
    """A real quote can still be about something else. Example: a notice quote with no "notice"."""
    if field not in TOPIC or not answer.found or not answer.quotes:
        return []
    quotes = " ".join(answer.quotes).lower()
    if any(part in quotes for part in TOPIC[field]):
        return []
    detail = answer.quotes[0][:80]
    return [Issue(field=field, rule="quote_off_topic", severity="warn", detail=detail)]


def maybe_missed(field: str, answer, text: str) -> list[Issue]:
    """The model says "not found", but the contract has words that often mean "found"."""
    if field not in MISSED or answer.found:
        return []
    match = MISSED[field].search(text)
    if match is None:
        return []
    return [Issue(field=field, rule="maybe_missed", severity="warn", detail=match.group(0)[:80])]


def review_answer(fields: ContractFields, text: str) -> list[Issue]:
    """The review issues for one contract: warnings only, so they never change an answer."""
    issues = []
    for field in ContractFields.model_fields:
        answer = getattr(fields, field)
        issues += off_topic(field, answer) + maybe_missed(field, answer, text)
    return issues


def needs_review(issues: list[Issue]) -> set[str]:
    """The fields a person must look at: every field with at least one issue."""
    return {issue.field for issue in issues}
```

</details>

## Break it on purpose

**Break 1: forget the delete.** In `validate`, comment out the `DELETE` line. Run `validate` on the kept
run once more. Guess: which lines of the report change?

<details><summary>What you see</summary>

```text
stored 35 issues for run 20261102-200003
errors: 3 fields (0.5%) in 2 contracts
needs review: 35 fields (5.6%) in 27 contracts
need a look (gold): 54 fields, 14 of them missed
caught: 18 of 54, and 4 of the 14 missed
by rule: quote_off_topic 30, maybe_missed 20, quote_gap 12, found_no_value 6, quote_no_words 2
```

Only the last line. The field counts use `DISTINCT`, so they hide the copies. The rule counts double.
A bug that changes one line of four is easy to miss. The test in Step 7 catches it. Put the line back,
and run `validate` again to clean the table.
</details>

**Break 2: check a bad answer like a good one.** In `validate`, remove the `if not all(...)` branch, so
every contract goes through `check_answer`. Run it on the V4.1 run from E1.1, which has 2 bad answers:

```sh
uv run python -m docintel.evals.runner validate 20261102-202705
```

Guess: what happens to the 2 bad contracts?

<details><summary>What you see</summary>

With the branch:

```text
stored 78 issues for run 20261102-202705
errors: 34 fields (5.4%) in 5 contracts
```

Without it:

```text
stored 58 issues for run 20261102-202705
errors: 10 fields (1.6%) in 3 contracts
needs review: 49 fields (7.9%) in 31 contracts
```

The 24 `bad_schema` errors are gone. The 2 bad contracts now look clean: their stored fields are all
"not found", so only `maybe_missed` fires. The error rate drops from 5.4% to 1.6%, and nothing crashes.
That is the worst kind of bug for an experiment. Put the branch back, and run `validate` again.
</details>

## Experiment

This is E2.0. It makes no new run. It replays `20261102-200003`, `20261105-213036` and `20261101-192153`.

- **Command:** the loop in Step 6.
- **Expected table:** one row per run: error fields and contracts, made-up quotes, needs-review fields
  and contracts, caught of "need a look", misses caught.
- **Dev only:** never run `validate` on a test run to choose a rule.

Add this to `EXPERIMENTS.md`:

```markdown
## E2.0: validation and review flags on stored runs
- **Date:**
- **Score rules Hash:** 6ffdaa7 (same rules as E1.2)
- **run_id(s):** replays of 20261102-200003 (kept), 20261105-213036 (v1 on Parasail), 20261101-192153
  (E1). No LLM calls, $0.
- **Question / hypothesis:** How often do answers break a rule? How many real problems do review flags
  catch, and at what review rate?
- **Data:** dev, 52 contracts, 12 fields, CUAD .txt (clean)
- **Setup:** 2a rules (<MAX_GAP>, <severities>). Review rules: <word lists>, <maybe-missed fields>.
  Needs review = <your rule>. No retries.
- **Results:** per run: error fields (rate, contracts), `quote_missing` (and how many are made up, by
  hand), needs-review fields (rate, contracts), caught of "need a look", misses caught. Issues by rule.
- **Limits:** the review rules were written from dev answers, so the catch is optimistic; test gives the
  final number. "Need a look" uses gold labels, which have known errors (1d).
- **Conclusion:**
- **Next step:** 2b, retry on errors. Before the first run: choose the provider (the Parasail pin in
  `core/llm.py`).
```

## Gotchas

- **The rules were fitted on dev.** The word lists came from reading dev answers. The catch on test will
  likely be lower (guess).
- **`validate` writes to the database.** It deletes and inserts rows. Close the notebook first.
- **Run `score` before the report.** `review_report` reads `scores`. With no scores, "need a look" is 0.
  `run` already calls both, in that order.
- **Two Kubient contracts.** The doc_ids end in `_Part1` and `_Part2`. A `LIKE 'KUBIENT%'` picks one by
  chance.
- **Word lists are English only.** A quote with a typo or a broken word (Coral Gold's `thewritten`) can
  miss its topic word.

## Explain back, then commit

Explain each changed file to Claude in a few sentences (the rule in `PLAN.md`):

- `review.py`: each rule, a real catch and a real false alarm, and why both are warnings.
- `rules.py`: why one line, and not a second list.
- `runner.py`: why `validate` deletes first, why it reads `ok`, and why the report is in `evals/`.
- `test_review.py`: what each test protects.
- `EXPERIMENTS.md`: E2.0, line by line.

Then:

```sh
git status
git add src/docintel/domain/validate src/docintel/evals/runner.py tests/test_review.py EXPERIMENTS.md
git commit -m "phase 2a2: needs-review rules, stored issues, E2.0"
```

## Conclusion

What you have now:

- Two review rules from evidence, as warnings, in the same list as 2a's checks.
- An `issues` table for every run, rebuilt by `validate` with no LLM call.
- A report with the two numbers that describe a flag: review rate and catch rate.
- E2.0, the "before" numbers for 2b: 0.5% of fields break a rule on the kept run, 5.6% need review, and
  the flags catch 18 of 54 problems.

Go back to the objectives. Check that you can do each one without notes. Then answer:

1. Why can no rule that reads only the answer catch a missed clause?
2. Why is a review rule a warning, and not an error? Use Round 2 and Round 3.
3. The kept run has 3 error fields. What does that tell you about 2b's retry lift on clean text?

Want more practice? Try these (optional):

1. Round 1's notice answer is the notice to end the contract at any time. Add a notice rule: the quote
   must also hold `renew`, `expir` or `end of`. Count its flags and catches with the Step 2 script.
2. Run `validate` on the other E1.1 runs. Which model gets the highest catch rate?
3. Flag every `found` answer with a gap quote and an off-topic warning together. Is that pair ever wrong
   on dev?

Checklist (`../PLAN.md`): **Validation, citation check, retry with feedback; retry cost** (validation and
the citation check are done and stored; retry is in 2b). **Guardrails, human-in-the-loop** (started: the
needs-review flag, with its cost and catch). **Experiments: run_id, one change at a time, cost, p50/p95**
(E2.0 traces to stored runs).
