# Phase 2b: the retry loop and the attempt log

In this part, you build the loop that sends the errors back to the model and asks it to try again. You
decide when to retry, what the message says, when to stop, and which answer wins. Every attempt is
stored in DuckDB. The loop is tested with a fake model. One live call on one contract is the only cost.

This is part 1 of 2 for Phase 2b. Part 2 (2b2) runs the experiments E2.1 to E2.3 on all of dev.

## Words used in this part

Read these first. Issue, error, warning and replay are from 2a.

- **Network retry**: the same request again, after a timeout or a 429. Built in 1a2. The model never
  sees it. Example: `LLMResult.attempts = 2`.
- **Repair retry**: a new request that includes the model's last answer and its errors. Example: "this
  quote is not in the contract".
- **Attempt**: one call for one contract. Attempt 0 is the first answer. Attempts 1 and 2 are repair
  retries.
- **Feedback message**: the text that lists the errors for the model. It is a prompt, so it lives in a
  file.
- **No progress**: a retry returns exactly the same errors as the attempt before. Another retry would
  likely do the same.
- **Merge**: build the final answer from several attempts, one field at a time.
- **Provider**: the company that runs the model for OpenRouter. Example: Parasail.

## Objectives

By the end of this part you should be able to:

1. Explain the difference between a network retry and a repair retry, with one example of each.
2. Say which errors a retry can fix, and which it never can, with real rows from stored runs.
3. Build a retry loop that stops early, and defend each stop rule.
4. Explain why the final answer changes only the fields that were broken.
5. Store every attempt with its cost, so 2b2 can measure retry cost per contract.

## Dependencies

You install nothing new. This part needs:

- 1a2: `call_llm`, `LLMResult` and `log_call` in `core/llm.py`.
- 1b: `build_messages` and the `prompts/` folder.
- 1c2: `run_docs` and the CLI in `evals/runner.py`.
- 2a and 2a2: `check_result`, which returns errors and warnings for one answer.

## The big picture

Before this part, one contract gets one call. If the answer breaks a rule, the issue is stored, and that
is all.

After this part:

```text
contract -> call -> check_result -> errors? -> feedback message -> call again (at most 2 times)
                                                                      |
                                    attempts table <- every attempt --+-- final answer -> predictions
```

- **2b2** runs this on all of dev and measures E2.1 to E2.3.
- **Phase 3** uses the same loop on text from worse parsers, where errors should be more common.
- **Phase 4** calls `extract_with_retry` from the API.

## Remember this

> A repair retry is a new, paid call. Send it only for errors a retry could fix, and stop when the same
> errors come back. Keep every field that was fine in the first answer: a retry may only change what
> was broken. Log every attempt, or the cost of retries is hidden.
>
> **Retry what is broken. Keep what is fine. Log every try.**

## Why

**The plan asks for it.** The hiring question is "did retries help?". You can only answer it with a
loop that logs every attempt.

**Errors on clean text are rare.** E2.0 found 3 error fields on the kept run, in 2 contracts. So expect
a small lift in 2b2. That is still a real answer to the question.

**The real test comes later.** Phase 3 sends worse text. More quotes will fail there, and the same loop
will be ready.

## Design decisions

- **The loop lives in `domain/extract/retry.py`.** The API needs it too, so it cannot live in `evals/`.
  Other option: put it in the runner. Then the API would need a second copy.
- **It returns every attempt, and the runner writes them.** Worker threads must not write to DuckDB
  (1c2). Other option: log inside the loop. That breaks the one-writer rule.
- **One path for all runs.** `--retries 0` uses the same loop, with no retries. Other option: keep the
  old `extract` path for runs with no retries. Then two paths can drift apart.
- **The feedback text is a file, `prompts/retry.md`.** It is a prompt, so it is versioned like one. It
  sits next to the version folders, not inside them, so `v1` does not change.
- **A new `attempts` table, keyed by `attempt_no`.** `llm_calls` has no `doc_id`, so it cannot say which
  contract a retry was for. Other option: add columns to `llm_calls`. That table is for every call in
  the project, not only runs.

## Worked example

Real answers from stored runs. Guess before you open each box.

### Round 1: an error no retry can fix

The kept run. `renewal_term` in the Pareteum contract has `found` true and an empty value. The quote is:

`the Agreement will be automatically extended for consecutive *** periods until such time as ***
termination notice is provided.`

The error is `found_no_value`. Will a retry fix it?

<details><summary>Guess, then open</summary>

No. The length is redacted: `***`. No model can read it. The mark is a TP, because the clause is there.
All 3 error fields on the kept run are like this: two in Pareteum (`***`), and one in a form with blank
names (`______`). A retry on the kept run would pay for calls that cannot help.
</details>

### Round 2: a right answer with a broken quote

The Parasail v1 run. Coral Gold, `anti_assignment`, marked TP:

`Neither this Agreement nor any of the rights of any of the parties under this Agreement shall be
assigned without the written consent of all the parties.`

The contract says `thewritten`, with no space. So 2a's check says `quote_missing`, an error. Is a
retry worth paying for?

<details><summary>Guess, then open</summary>

It depends on what you want. The mark is already a TP, so F1 cannot go up. But the product promises an
exact quote, so a retry that copies `thewritten` makes the citation true. The retry may also give up and
remove the quote. Then `found_no_quote` fires, and the field gets worse. 2b2 counts both.
</details>

### Round 3: a retry that loses a TP

Your feedback message says: "found is true, but value is empty. Fill in the value, or set found to
false." The model gets this for Pareteum `renewal_term`. What can it do?

<details><summary>Guess, then open</summary>

It cannot fill in `***`. So the easy way to fix the error is to set `found` to false. The error is
gone, and the loop calls it fixed. But the clause is there, so a TP becomes an FN. A retry that removes
an error can still make the answer worse. The words in the feedback message matter, like the words in a
prompt.
</details>

## Project setup

```sh
touch src/docintel/domain/extract/retry.py src/docintel/domain/extract/prompts/retry.md
touch tests/test_retry.py
```

You should now have:

```text
src/docintel/
├── core/
│   ├── config.py          + provider setting, new default model
│   └── llm.py             + provider_prefs, the pin moves out of _send
├── domain/extract/
│   ├── extract.py
│   ├── prompts/
│   │   ├── retry.md       new: the feedback message
│   │   ├── v1/
│   │   └── v2/
│   └── retry.py           new: the loop
└── evals/runner.py        + attempts table, --retries
tests/
├── test_retry.py          new
└── test_runner.py         + the fake returns attempts
```

## Step 1: provider and model (your decision)

**Why.** 2b2 makes a new run. It must say which provider served it, and that must not change during the
run.

`core/llm.py` still has the pin from E1.3, marked "temporary". The evidence, from E1.3:

| Run | Provider | F1 | Cost | Out tokens | p95 | Wrong-quote TPs |
|---|---|---|---|---|---|---|
| v1 (kept) | Crusoe | 0.912 | $0.204 | 8,953 | 57.5 s | 4 |
| v1 | Parasail | 0.907 | $0.112 | 2,601 | 37.3 s | 10 |
| v2 | Venice 40, Parasail 11, DigitalOcean 1 | 0.905 | $0.087 | 2,567 | 103.1 s | 6 |

Crusoe no longer serves V4 Flash. The F1 gap between Parasail and Crusoe could be zero.

Decide, and write it in a "Retry rules" cell in your notebook:

1. **Pin a provider, or let OpenRouter choose?**
2. **Where does the choice live?** In code, or in a setting you can change in `.env`?

<details><summary>Reference choice (open after you decide)</summary>

1. Pin Parasail. One provider for the whole run, so attempt 0 and the retries are served the same way.
   It is also half the cost. The higher wrong-quote TP count is a known limit, logged in E1.3.
2. A setting, `docintel_provider`. Empty means OpenRouter chooses. And the default model becomes V4
   Flash, so a missing `.env` line does not silently use Qwen.
</details>

In `src/docintel/core/config.py`, change the model line, and add one below it:

```python
    docintel_model: str = "deepseek/deepseek-v4-flash"  # kept in E1.1
    docintel_provider: str | None = "parasail"  # E1.3; empty means OpenRouter chooses
```

In `src/docintel/core/llm.py`, add this function above `RETRYABLE`:

```python
def provider_prefs() -> dict:
    """OpenRouter's provider rules. A pinned provider has no backup, so runs never mix providers."""
    prefs = {"require_parameters": True}
    provider = get_settings().docintel_provider
    if provider:
        prefs |= {"order": [provider], "allow_fallbacks": False}
    return prefs
```

*Python here: [dict merge `|`](./py/phase-0b.md#py-6).*

And in `_send`, replace the whole `extra_body={...}` block with:

```python
                extra_body={"provider": provider_prefs()},
```

Here, we:

1. Always ask for providers that support `response_format` (`require_parameters`, from 1a).
2. Add the pin only when the setting is not empty.
3. Turn off the backup provider, so a busy Parasail gives an error, not a different provider.

Checkpoint:

```sh
uv run python -c "from docintel.core.llm import provider_prefs; print(provider_prefs())"
DOCINTEL_PROVIDER= uv run python -c "from docintel.core.llm import provider_prefs; print(provider_prefs())"
```

```text
{'require_parameters': True, 'order': ['parasail'], 'allow_fallbacks': False}
{'require_parameters': True}
```

## Step 2: when to retry (your decision)

**Why.** Each retry resends the whole contract, about 10,500 tokens. On Parasail, one call costs about
$0.002.

The evidence, from E2.0 and the 2a2 replays:

| Retry on | Kept run: contracts | Parasail run: contracts | Can a retry fix it? |
|---|---|---|---|
| Errors only | 2 | 5 | Kept: none (`***`, blank form). Parasail: maybe the 2 broken quotes |
| Errors and warnings | 27 | 30 | Most warnings are on right answers (2a2: half are false alarms) |
| `bad_schema` only | 0 | 0 | V4.1 had 2 in E1.1, both empty after thousands of tokens |

With up to 2 retries, "errors only" adds at most 4 calls on the kept run. "Errors and warnings" adds up
to 54, which would about double the cost of a run.

Decide:

1. **Which issues start a retry?** All errors, some errors, or warnings too?
2. **How many retries at most?** The plan says 2.

<details><summary>Reference choice (open after you decide)</summary>

1. All errors, and no warnings. A warning means "a person should look". Sending it to the model would
   ask it to change answers that are often right. Errors break a rule of prompt v1, so asking the model
   to follow its own rules is fair.
2. Two, as the plan says. Step 4 adds a rule to stop earlier.
</details>

## Step 3: the feedback message (your decision)

**Why.** Round 3 showed that the words decide what the model does.

Things to decide, and write in your cell:

1. **What does each line say?** The field, the rule, and the detail from the issue? Only the field?
2. **What about `bad_schema`?** It gives 12 issues with the same Pydantic error. Send it 12 times, or
   once? `LLMResult.error` was kept in 1a2 for this moment.
3. **What may the model change?** Only the broken fields, or the whole answer?
4. **What should it do when it cannot fix an error?** Think about Pareteum.

Put your message in `src/docintel/domain/extract/prompts/retry.md`. Use `{errors}` where the list goes.

<details><summary>Reference choice and file (open after you decide)</summary>

1. Field, rule and detail. The detail is the quote or the problem, so the model sees what to fix.
2. Once, as "every field", cut to 1,000 characters. 12 copies of a long error waste tokens.
3. Only the broken fields. The merge in Step 4 enforces this anyway.
4. Keep `found` true and the value null. Then the same error comes back, and the loop stops (Step 4).
   The TP is safe.

```text
Your last answer broke some rules. Each problem is one line below.

{errors}

Fix only these fields. Keep every other field exactly as it was.
- A quote must be copied from the contract, character for character. If you cannot copy it exactly,
  remove it.
- found, quotes and value must agree: found is true only with at least one quote, and a field with a
  value needs a value.
- If the contract hides the value (like *** or a blank line), keep found true and value null.

Answer again with the JSON for all 12 fields.
```

</details>

## Step 4: when to stop, and which answer wins (your decision)

**Why.** A loop needs a clear end. And the final answer must not be worse than the first.

Stop rules to choose from:

- **A. No errors left.** The obvious one.
- **B. The limit.** After 2 retries, stop, whatever the result.
- **C. No progress.** The same (field, rule) pairs come back. Pareteum would stop after 1 retry, not 2.

Options for the final answer:

- **Last.** The newest attempt. Simple, but a retry can change a field that was fine (Round 3).
- **Fewest errors.** The attempt with the fewest errors. But a clean attempt can still have a wrong
  answer in a field that was fine before.
- **Merge.** Start from the first answer that fits the schema. Each broken field takes its newest
  version that has no error. Every other field stays as it was.

Decide:

1. **Which stop rules?**
2. **Which answer wins?** What happens when the first answer is `bad_schema`?

<details><summary>Reference choice (open after you decide)</summary>

1. All three: A, B and C.
2. Merge. A retry may only change what was broken, so it cannot lower a right field. When attempt 0 is
   `bad_schema`, there is nothing to keep, so the first answer that fits the schema is the start.
</details>

## Step 5: build the loop

**Why.** Your four decisions become one function that the runner and the API can call.

Put this skeleton in `src/docintel/domain/extract/retry.py`, and write the bodies yourself:

```python
"""Repair retries: send the errors back to the model, at most `max_retries` times."""

from dataclasses import dataclass

from docintel.core.llm import LLMResult, call_llm
from docintel.domain.extract.extract import PROMPTS, build_messages
from docintel.domain.schema.fields import ContractFields
from docintel.domain.validate.issues import Issue
from docintel.domain.validate.rules import check_result

FEEDBACK = PROMPTS / "retry.md"


@dataclass
class Attempt:
    """One call for one contract: 0 is the first answer, 1 and 2 are repair retries."""

    attempt_no: int
    result: LLMResult[ContractFields]
    issues: list[Issue]

    @property
    def errors(self) -> list[Issue]:
        return [i for i in self.issues if i.severity == "error"]


def error_keys(attempt: Attempt) -> set[tuple[str, str]]:
    """Which (field, rule) pairs failed. Two attempts with the same keys made no progress."""
    ...


def feedback(errors: list[Issue]) -> str:
    """The message that tells the model what to fix. A bad schema is one line, not 12."""
    ...


def extract_with_retry(
    text: str, model: str | None = None, *, prompt_version: str = "v1", max_retries: int = 2
) -> list[Attempt]:
    """Every attempt for one contract, in order. Stops when there are no errors, or no progress."""
    ...


def final_answer(attempts: list[Attempt]) -> ContractFields | None:
    """The first answer that fits the schema. A broken field takes its newest fixed version."""
    ...
```

*Python here: [`@dataclass`](./py/phase-1a2.md#py-1) · [`@property`](./py/phase-2b.md#py-1).*

<details><summary>Reference code (open after you try)</summary>

```python
def error_keys(attempt: Attempt) -> set[tuple[str, str]]:
    """Which (field, rule) pairs failed. Two attempts with the same keys made no progress."""
    return {(i.field, i.rule) for i in attempt.errors}


def feedback(errors: list[Issue]) -> str:
    """The message that tells the model what to fix. A bad schema is one line, not 12."""
    if any(e.rule == "bad_schema" for e in errors):
        lines = [f"- every field (bad_schema): {errors[0].detail[:1000]}"]
    else:
        lines = [f"- {e.field} ({e.rule}): {e.detail}" for e in errors]
    return FEEDBACK.read_text(encoding="utf-8").replace("{errors}", "\n".join(lines))


def extract_with_retry(
    text: str, model: str | None = None, *, prompt_version: str = "v1", max_retries: int = 2
) -> list[Attempt]:
    """Every attempt for one contract, in order. Stops when there are no errors, or no progress."""
    messages = build_messages(text, prompt_version)
    attempts = []
    for attempt_no in range(max_retries + 1):
        result = call_llm(messages, ContractFields, model=model)
        attempt = Attempt(attempt_no, result, check_result(result, text))
        attempts.append(attempt)
        if not attempt.errors:
            break
        if attempt_no > 0 and error_keys(attempt) == error_keys(attempts[-2]):
            break  # the same errors came back, so another retry is wasted money
        messages = messages + [
            {"role": "assistant", "content": result.raw_text},
            {"role": "user", "content": feedback(attempt.errors)},
        ]
    return attempts


def final_answer(attempts: list[Attempt]) -> ContractFields | None:
    """The first answer that fits the schema. A broken field takes its newest fixed version."""
    good = [a for a in attempts if a.result.parsed is not None]
    if not good:
        return None
    base = good[0]
    broken = {i.field for i in base.errors}
    answer = base.result.parsed
    for attempt in good[1:]:  # oldest first, so the newest fix wins
        fixed = broken - {i.field for i in attempt.errors}
        answer = answer.model_copy(update={f: getattr(attempt.result.parsed, f) for f in fixed})
    return answer
```

*Python here: [`messages + [...]`](./py/phase-2b.md#py-2) · [`attempts[-2]`](./py/phase-2b.md#py-3) ·
[`model_copy(update=...)`](./py/phase-2b.md#py-4).*

</details>

Here, in `extract_with_retry`, we:

1. Build the normal v1 messages once.
2. Call the model, and check the answer with your 2a rules.
3. Stop when there are no errors (rule A), or the same errors came back (rule C). The `range` ends the
   loop after 2 retries (rule B).
4. Add the model's own answer and the feedback, so the model sees what it wrote. The contract is not
   sent twice in one request, but every request carries it once.

And in `final_answer`, we:

1. Skip attempts that did not fit the schema.
2. Start from the first one that did.
3. Swap in a field only from an attempt where that field has no error.

Checkpoint with a fake model. It answers with a made-up quote first, then a real one. No key, no cost:

<details><summary>The command</summary>

```sh
uv run python - <<'EOF'
import json

from docintel.core.llm import LLMResult, _parse
from docintel.domain.extract import retry
from docintel.domain.schema.fields import ContractFields
from docintel.evals.runner import empty_answer

CONTRACT = "This Agreement is dated as of March 1, 2020. Neither party may assign this Agreement."
answers = {field: empty_answer(field) for field in ContractFields.model_fields}
made_up = answers | {"anti_assignment": {"quotes": ["Either party may assign."], "found": True}}
fixed = answers | {"anti_assignment": {"quotes": ["Neither party may assign"], "found": True}}
replies = iter([json.dumps(made_up), json.dumps(fixed)])


def fake_call_llm(messages, schema, *, model=None):
    raw = next(replies)
    parsed, error = _parse(schema, raw)
    return LLMResult(raw, parsed, error, {}, 0.002, 10, "fake", None, 1)


retry.call_llm = fake_call_llm  # only inside this script
attempts = retry.extract_with_retry(CONTRACT)
for a in attempts:
    print(a.attempt_no, [(i.field, i.rule) for i in a.errors])
print(retry.feedback(attempts[0].errors))
print(retry.final_answer(attempts).anti_assignment.quotes)
EOF
```

*Python here: [`iter` and `next`](./py/phase-2b.md#py-5).*

</details>

```text
0 [('anti_assignment', 'quote_missing')]
1 []
Your last answer broke some rules. Each problem is one line below.

- anti_assignment (quote_missing): Either party may assign.

Fix only these fields. Keep every other field exactly as it was.
- A quote must be copied from the contract, character for character. If you cannot copy it exactly,
  remove it.
- found, quotes and value must agree: found is true only with at least one quote, and a field with a
  value needs a value.
- If the contract hides the value (like *** or a blank line), keep found true and value null.

Answer again with the JSON for all 12 fields.

['Neither party may assign']
```

Two attempts. The retry fixed the quote, and the loop stopped.

## Step 6: store every attempt

**Why.** 2b2 must count retry cost per contract, and see which errors were fixed.

In `src/docintel/evals/runner.py`, add to the end of `TABLES`, before the closing `"""`:

```sql
CREATE TABLE IF NOT EXISTS attempts (
    run_id VARCHAR, doc_id VARCHAR, attempt_no INTEGER, ok BOOLEAN,
    errors JSON,    -- the error issues of this attempt, as "field:rule"
    fixed BOOLEAN,  -- a repair retry with no errors left
    cost_usd DOUBLE, latency_ms INTEGER, raw_text VARCHAR,
    PRIMARY KEY (run_id, doc_id, attempt_no)
);
ALTER TABLE runs ADD COLUMN IF NOT EXISTS max_retries INTEGER DEFAULT 0;
```

*Python here: [`ADD COLUMN IF NOT EXISTS`](./py/phase-2b.md#py-6).*

Here, we:

1. Store one row per attempt, with its own cost and time.
2. Store the raw answer of each attempt, so 2b2 can score attempt 0 on its own.
3. Add `max_retries` to the existing `runs` table. `CREATE TABLE IF NOT EXISTS` does nothing to a table
   that exists, so a new column needs `ALTER`. Old runs get 0.

Update the imports at the top of the same file. Put each line in its place in the sorted list:
`dataclasses` goes with the standard library imports (above `datetime`), and `retry` goes right after
`extract.extract`. `make lint` fails on imports out of order.

```python
from dataclasses import replace

from docintel.domain.extract.extract import build_messages
from docintel.domain.extract.retry import Attempt, extract_with_retry, final_answer
```

Remove `extract` from the old `extract.extract` import. The runner no longer calls it.

Add this function above `SCORE_ROW`:

```python
def attempt_rows(run_id: str, doc_id: str, attempts: list[Attempt]) -> list[tuple]:
    """One row per attempt, so cost and errors can be read per contract and per retry."""
    rows = []
    for a in attempts:
        errors = [f"{i.field}:{i.rule}" for i in a.errors]
        fixed = a.attempt_no > 0 and not errors
        r = a.result
        rows.append(
            (run_id, doc_id, a.attempt_no, r.parsed is not None, json.dumps(errors), fixed,
             r.cost_usd, r.latency_ms, r.raw_text)
        )
    return rows
```

`ruff format` will put each value on its own line. That is fine.

In `run_docs`, add `max_retries: int = 0` as the last argument. Then submit the loop instead of
`extract`:

```python
    futures = {
        pool.submit(
            extract_with_retry, text, model, prompt_version=prompt_version, max_retries=max_retries
        ): doc_id
        for doc_id, text in texts.items()
    }
```

Then rename `result` to `attempts` in the `try`. Keep the `except` block as it is: a Python `try`
needs its `except`, and a crashed contract must still be counted. Replace only what comes after it:

```python
            try:
                attempts = future.result()
            except Exception as e:  # still failing after the retries, or a 400 error
                failed += 1
                print(f"[{i}/{len(futures)}] {doc_id[:40]}  FAILED {type(e).__name__}: {e}")
                continue
            for a in attempts:  # every call is logged, retries too
                log_call(con, a.result, "ContractFields", run_id)
            con.executemany(
                "INSERT INTO attempts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                attempt_rows(run_id, doc_id, attempts),
            )
            final = replace(attempts[-1].result, parsed=final_answer(attempts))
            con.executemany(
                "INSERT INTO predictions VALUES (?, ?, ?, ?, ?, ?)", to_rows(run_id, doc_id, final)
            )
            cost = sum(a.result.cost_usd or 0 for a in attempts)
            print(
                f"[{i}/{len(futures)}] {doc_id[:40]}  ok={final.parsed is not None}"
                f"  tries={len(attempts)}  ${cost:.4f}"
            )
```

*Python here: [`dataclasses.replace`](./py/phase-2b.md#py-7).*

Here, we:

1. Log every attempt in `llm_calls`, so the total cost of a run stays right.
2. Write the attempts, then the final answer, from the main thread only.
3. Reuse `to_rows` from 1c. `replace` gives it an `LLMResult` that holds the merged answer.

Now the CLI. In `parse_args`, add to the `run` subcommand:

```python
    run.add_argument("--retries", type=int, choices=[0, 1, 2], default=0, help="repair retries")
```

*Python here: [`choices`](./py/phase-2b.md#py-8).*

In `main`:

1. In the `--resume` branch, also read `max_retries` from `runs`, into a variable `retries`.
2. In the new-run branch, set `retries = args.retries`.
3. Add `max_retries` to the `INSERT INTO runs`, with the value `retries`.
4. Pass `retries` as the last argument of `run_docs`.

So a resumed run uses the same retry setting as the start.

<details><summary>The new <code>main</code> lines</summary>

```python
            split, parser, model, version, n_docs, retries = con.execute(
                "SELECT split, parser, model, prompt_version, n_docs, max_retries FROM runs "
                "WHERE run_id = ?",
                [run_id],
            ).fetchone()
```

```python
            split, parser, version = args.split, args.parser, args.prompt_version
            retries = args.retries
```

```python
                "INSERT INTO runs (run_id, split, parser, model, prompt_version, n_docs, "
                "est_cost_usd, max_retries) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [run_id, split, parser, model, version, n_docs, cost, retries],
```

```python
        failed = run_docs(con, run_id, texts, model, version, args.concurrency, retries)
```

</details>

The resume test in `tests/test_runner.py` fakes `extract`, which the runner no longer calls. Update it:

```python
from docintel.domain.extract.retry import Attempt
```

```python
    def fake_extract(text, model, *, prompt_version, max_retries):
        if text == "crash":
            raise TimeoutError("network down")
        return [Attempt(0, result(PRED), [])]

    monkeypatch.setattr(runner, "extract_with_retry", fake_extract)
```

Checkpoint. This runs `TABLES` on the real database once, and reads the new column:

```sh
uv run python - <<'EOF'
from docintel.evals import runner
from docintel.evals.store import connect

with connect() as con:
    con.execute(runner.TABLES)
    print(con.execute("SELECT max_retries, count(*) FROM runs GROUP BY 1").fetchall())
    print(con.execute("SELECT count(*) FROM attempts").fetchone())
EOF
make test
```

```text
[(0, 16)]
(0,)
```

Every old run has 0 retries, and there are no attempts yet. `make test` still passes (67 tests). Your
run count may differ.

## Step 7: one live check

**Why.** The fake proves the logic. Only a real call proves the provider takes the longer message list.

This costs about $0.005. It uses Round 1's contract, where the errors cannot be fixed:

```sh
uv run python - <<'EOF'
from docintel.core.llm import log_call
from docintel.domain.extract.retry import error_keys, extract_with_retry
from docintel.evals.runner import cuad_txt
from docintel.evals.store import connect

with connect() as con:
    (doc,) = con.execute("SELECT doc_id FROM contracts WHERE doc_id LIKE 'PareteumCorp%'").fetchone()
    text = cuad_txt(con, doc)
attempts = extract_with_retry(text, max_retries=2)
with connect() as con:
    for a in attempts:
        log_call(con, a.result, "ContractFields", run_id="2b-check")
for a in attempts:
    print(a.attempt_no, a.result.provider, f"${a.result.cost_usd or 0:.4f}", sorted(error_keys(a)))
EOF
```

What you should see (shape, not numbers; the model may answer differently):

```text
0 Parasail $0.00..  [('notice_period_to_terminate_renewal', 'found_no_value'), ('renewal_term', 'found_no_value')]
1 Parasail $0.00..  [('notice_period_to_terminate_renewal', 'found_no_value'), ('renewal_term', 'found_no_value')]
```

Read it:

1. Two lines means the no-progress stop worked. The model kept the value null, as the message asked.
2. One line means attempt 0 had no errors this time. Run-to-run noise is real (1d2).
3. A changed error list means the model did something else. Read its `raw_text`. Did it set `found`
   to false (Round 3)?

Then a small pilot, to prove the old path still works:

```sh
uv run python -m docintel.evals.runner run --limit 3 --retries 0
```

Each line should now end with `tries=1` and a cost. Write the `run_id` down. Check its rows:

```sh
uv run python - <<'EOF'
from docintel.evals.store import connect

RUN = "<your pilot run_id>"
with connect() as con:
    print(con.execute("SELECT max_retries FROM runs WHERE run_id = ?", [RUN]).fetchone())
    print(con.execute("SELECT attempt_no, ok, errors, fixed FROM attempts WHERE run_id = ?", [RUN]).fetchall())
EOF
```

Expect `(0,)`, then 3 rows with `attempt_no` 0 and `fixed` false. The pilot is not used for results.

## Step 8: the test file

**Why.** Each stop rule and the merge must never break without a test failing.

<details><summary>Put this in <code>tests/test_retry.py</code></summary>

```python
"""Repair retries with a fake model. No network, no key, no cost."""

import json

from docintel.core.llm import LLMResult, _parse
from docintel.domain.extract import retry
from docintel.domain.schema.fields import ContractFields
from docintel.evals.runner import empty_answer

CONTRACT = "This Agreement is dated as of March 1, 2020. Neither party may assign this Agreement."
DATE = {"quotes": ["dated as of March 1, 2020"], "value": "2020-03-01", "found": True}
GOOD = {"quotes": ["Neither party may assign this Agreement."], "found": True}
MADE_UP = {"quotes": ["Either party may assign this Agreement."], "found": True}


def answer(**fields) -> str:
    """The raw JSON of an answer: all 12 fields not found, except the ones given."""
    data = {field: empty_answer(field) for field in ContractFields.model_fields}
    return json.dumps(data | fields)


def fake_llm(monkeypatch, *replies: str) -> list:
    """Make `call_llm` return `replies` in order. Returns the messages of each call."""
    sent = []

    def call(messages, schema, *, model=None):
        sent.append(messages)
        raw = replies[len(sent) - 1]
        parsed, error = _parse(schema, raw)
        return LLMResult(
            raw_text=raw,
            parsed=parsed,
            error=error,
            usage={},
            cost_usd=0.002,
            latency_ms=10,
            model="fake",
            provider=None,
            attempts=1,
        )

    monkeypatch.setattr(retry, "call_llm", call)
    return sent


def test_no_retry_when_the_first_answer_is_clean(monkeypatch):
    sent = fake_llm(monkeypatch, answer(agreement_date=DATE))
    attempts = retry.extract_with_retry(CONTRACT)
    assert len(attempts) == len(sent) == 1


def test_a_fixed_error_stops_after_one_retry(monkeypatch):
    sent = fake_llm(monkeypatch, answer(anti_assignment=MADE_UP), answer(anti_assignment=GOOD))
    attempts = retry.extract_with_retry(CONTRACT)
    assert [len(a.errors) for a in attempts] == [1, 0]
    assert [m["role"] for m in sent[1]] == ["system", "user", "assistant", "user"]
    assert "anti_assignment (quote_missing)" in sent[1][-1]["content"]


def test_the_same_errors_twice_stop_early(monkeypatch):
    sent = fake_llm(monkeypatch, *[answer(anti_assignment=MADE_UP)] * 3)
    retry.extract_with_retry(CONTRACT, max_retries=2)
    assert len(sent) == 2  # the third call would be wasted money


def test_bad_schema_sends_the_pydantic_error_once(monkeypatch):
    sent = fake_llm(monkeypatch, "", answer(anti_assignment=GOOD))
    attempts = retry.extract_with_retry(CONTRACT)
    message = sent[1][-1]["content"]
    assert message.count("bad_schema") == 1
    assert "Invalid JSON" in message
    assert retry.final_answer(attempts) == attempts[1].result.parsed


def test_merge_changes_only_the_broken_field(monkeypatch):
    moved = DATE | {"value": "2020-03-02"}  # the retry also changed a field that was fine
    fake_llm(
        monkeypatch,
        answer(agreement_date=DATE, anti_assignment=MADE_UP),
        answer(agreement_date=moved, anti_assignment=GOOD),
    )
    final = retry.final_answer(retry.extract_with_retry(CONTRACT))
    assert final.agreement_date.value == "2020-03-01"
    assert final.anti_assignment.quotes == GOOD["quotes"]
```

</details>

*Python here: [`[x] * 3` and `*` in a call](./py/phase-2b.md#py-9) ·
[`monkeypatch.setattr`](./py/phase-1c2.md#py-5).*

Here, each test protects one decision:

1. A clean first answer makes one call.
2. A fixed error stops after one retry, and the retry carries the old answer and the feedback.
3. The same errors twice stop the loop, even with retries left.
4. A bad schema sends the Pydantic error once, and the first good answer wins.
5. The merge keeps a field that was fine, even when the retry changed it.

Checkpoint:

```sh
make test
```

```text
72 passed in 0.71s
```

`make lint` should also pass for your new files.

<details><summary>Full <code>src/docintel/domain/extract/retry.py</code></summary>

```python
"""Repair retries: send the errors back to the model, at most `max_retries` times."""

from dataclasses import dataclass

from docintel.core.llm import LLMResult, call_llm
from docintel.domain.extract.extract import PROMPTS, build_messages
from docintel.domain.schema.fields import ContractFields
from docintel.domain.validate.issues import Issue
from docintel.domain.validate.rules import check_result

FEEDBACK = PROMPTS / "retry.md"


@dataclass
class Attempt:
    """One call for one contract: 0 is the first answer, 1 and 2 are repair retries."""

    attempt_no: int
    result: LLMResult[ContractFields]
    issues: list[Issue]

    @property
    def errors(self) -> list[Issue]:
        return [i for i in self.issues if i.severity == "error"]


def error_keys(attempt: Attempt) -> set[tuple[str, str]]:
    """Which (field, rule) pairs failed. Two attempts with the same keys made no progress."""
    return {(i.field, i.rule) for i in attempt.errors}


def feedback(errors: list[Issue]) -> str:
    """The message that tells the model what to fix. A bad schema is one line, not 12."""
    if any(e.rule == "bad_schema" for e in errors):
        lines = [f"- every field (bad_schema): {errors[0].detail[:1000]}"]
    else:
        lines = [f"- {e.field} ({e.rule}): {e.detail}" for e in errors]
    return FEEDBACK.read_text(encoding="utf-8").replace("{errors}", "\n".join(lines))


def extract_with_retry(
    text: str, model: str | None = None, *, prompt_version: str = "v1", max_retries: int = 2
) -> list[Attempt]:
    """Every attempt for one contract, in order. Stops when there are no errors, or no progress."""
    messages = build_messages(text, prompt_version)
    attempts = []
    for attempt_no in range(max_retries + 1):
        result = call_llm(messages, ContractFields, model=model)
        attempt = Attempt(attempt_no, result, check_result(result, text))
        attempts.append(attempt)
        if not attempt.errors:
            break
        if attempt_no > 0 and error_keys(attempt) == error_keys(attempts[-2]):
            break  # the same errors came back, so another retry is wasted money
        messages = messages + [
            {"role": "assistant", "content": result.raw_text},
            {"role": "user", "content": feedback(attempt.errors)},
        ]
    return attempts


def final_answer(attempts: list[Attempt]) -> ContractFields | None:
    """The first answer that fits the schema. A broken field takes its newest fixed version."""
    good = [a for a in attempts if a.result.parsed is not None]
    if not good:
        return None
    base = good[0]
    broken = {i.field for i in base.errors}
    answer = base.result.parsed
    for attempt in good[1:]:  # oldest first, so the newest fix wins
        fixed = broken - {i.field for i in attempt.errors}
        answer = answer.model_copy(update={f: getattr(attempt.result.parsed, f) for f in fixed})
    return answer
```

</details>

## Break it on purpose

**Break 1: remove the no-progress stop.** Delete the second `if` in `extract_with_retry`. Guess: which
test fails, and what is the cost on the kept run?

<details><summary>What you see</summary>

```text
>       assert len(sent) == 2  # the third call would be wasted money
E       assert 3 == 2
FAILED tests/test_retry.py::test_the_same_errors_twice_stop_early - assert 3 ...
1 failed, 4 passed in 0.48s
```

On the kept run, both error contracts cannot be fixed. Without the stop, each one costs 3 calls, not 2.
Small here. On worse text in Phase 3, it adds up. Put the line back.
</details>

**Break 2: the last answer wins.** Make `final_answer` return `attempts[-1].result.parsed`. Guess:
which test fails?

<details><summary>What you see</summary>

```text
E       AssertionError: assert '2020-03-02' == '2020-03-01'
FAILED tests/test_retry.py::test_merge_changes_only_the_broken_field - Assert...
1 failed, 4 passed in 0.31s
```

The retry fixed the quote, but it also moved the date by one day. With "last wins", that change goes
into the final answer, and nobody asked for it. Put the merge back.
</details>

**Break 3: log only the final attempt.** In `run_docs`, call `log_call` only for `attempts[-1]`. Guess:
what does `report` say about cost? It reports less than you paid. No test catches this one, so read
the `for a in attempts` line again before you commit.

## Experiment

This part makes no full run. The live check and the pilot are only to see that the code works.

- **The check:** `run_id` `2b-check` in `llm_calls`. It is not an experiment.
- **The pilot:** one `run_id`, with `--retries 0`. It is not used for results.

E2.1 to E2.3 are in 2b2. Before that part, do not run `--retries 2` on all of dev. The keep rule must
come first.

## Gotchas

- **Two kinds of retry.** `LLMResult.attempts` counts network retries. `attempt_no` counts repair
  retries. A repair retry can also have network retries inside it.
- **`estimate` does not know about retries.** It guesses the cost of attempt 0 only. The real cost is
  in `attempts`.
- **Each retry resends the whole contract.** That is about 10,500 tokens per retry. A retry costs about
  the same as the first call.
- **A pinned provider can be busy.** With no backup, a busy Parasail gives errors (E1.3 saw a 429 on
  DeepInfra). Resume the run later.
- **The database is locked.** Close the notebook before the checkpoints.

## Explain back, then commit

Explain each changed file to Claude in a few sentences (the rule in `PLAN.md`):

- `config.py` and `llm.py`: why pin, and why a setting.
- `retry.md`: each line, and Round 3.
- `retry.py`: each stop rule, and why the merge keeps fine fields.
- `runner.py`: why the main thread logs every attempt, and why `ALTER`.
- `test_retry.py` and `test_runner.py`: what each test protects.

Then:

```sh
git status
git add src/docintel/core src/docintel/domain/extract src/docintel/evals/runner.py tests/test_retry.py tests/test_runner.py
git commit -m "phase 2b: repair retry loop and attempt log"
```

## Conclusion

What you have now:

- A provider setting, so every run says how it was served.
- `extract_with_retry`: errors go back to the model, at most 2 times, with three stop rules.
- `final_answer`: a merge that can only change broken fields.
- An `attempts` table, so the cost of each retry is visible per contract.

Go back to the objectives. Check that you can do each one without notes. Then answer:

1. The kept run has 3 error fields. How many could a retry fix, and why?
2. Why can a retry that removes an error still lower F1? Use Round 3.
3. Why does the runner log every attempt, and not only the final one?

Want more practice? Try these (optional):

1. Write a feedback line for `quote_missing` that also shows the closest real text. Where would you
   find it?
2. Change `max_retries` to 1 in the live check. Does the answer change?
3. Make the loop stop when the cost of one contract passes a limit. Where does that check go?

Checklist (`../PLAN.md`): **Validation, citation check, retry with feedback; retry cost** (the retry
loop is built and logged; its lift and cost are measured in 2b2). **Retries, timeouts, degradation,
idempotency** (network retries from 1a2, and now repair retries with a limit and a stop rule).
