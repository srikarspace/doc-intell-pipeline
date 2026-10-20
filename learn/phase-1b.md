# Phase 1b: prompt v1 and extract

In this part, you write the first prompt (your decision) and build `extract()`. It turns one
contract into your 12 fields with one LLM call. You build it one piece at a time, with a
checkpoint after each piece. Then you run it on one real dev contract and compare three fields
with the lawyers' labels. 1b2 turns that comparison into scoring rules.

## Words used in this part

Read these first. 1a and 1a2 words (schema, strict mode, `call_llm`, `LLMResult`) are used again.

- **Prompt**: the text we send to the model to tell it what to do. Example: "Copy the exact
  text from the contract."
- **System prompt**: the message with the rules. It is the same for every contract.
- **User prompt**: the message with the data. Here, it holds one contract.
- **Prompt version**: a name for one exact prompt text, like `v1`. A new text gets a new name.
- **Placeholder**: a marker in a text that code replaces later. Example: `{contract}` becomes
  the contract text.
- **Extraction**: reading a document and filling in fields. Example: Governing Law = Michigan.
- **Gold label**: the right answer, given by a lawyer. Our gold labels are the `labels` table.
- **Context window**: the most tokens a model can read in one call. Qwen3-235B: about 262,000.

## Objectives

By the end of this part you should be able to:

1. Defend each rule in your prompt v1 with evidence from the data.
2. Explain why prompts live in files with a version name, and not in code.
3. Show that the contract text goes into the prompt with no change at all.
4. Run `extract()` on one dev contract, and compare a present, an absent and a list field with
   the gold labels.
5. Say how many tokens one contract uses and what it costs.

## Dependencies

You install nothing new.

This part needs 1a2 to be done: `call_llm` in `core/llm.py`, its tests green, and one live call
that worked. If 1a2 is not done yet, do it first.

The live run in Step 4 uses your OpenRouter key. It costs under one tenth of a cent.

## The big picture

Before this part, `call_llm` can send any messages with any schema. Nothing knows how to ask
about a contract.

After this part:

- `domain/extract/prompts/v1/` holds the prompt, as two text files.
- `extract(text)` builds the messages and calls `call_llm` with `ContractFields`.
- One real answer is saved in `data/examples/ecoscience_v1.json`.

1b2 scores that saved answer. 1c runs `extract` on all 52 dev contracts and records the prompt
version in each run. 2b sends errors back to the model with the same messages.

## Remember this

> The prompt is data, not code. It lives in files with a version name, and every run says which
> version it used. The contract goes into the prompt with no change, so every quote can be found
> again in the source. To change the prompt, you make a new version.
>
> **New prompt, new version. Contract text goes in unchanged.**

## Why

**A prompt change is an experiment.** Changing one sentence can move recall by many points. If
`v1` can change quietly, an old number no longer says which prompt made it.

**Quotes must be checkable.** 2a checks that each quote is really in the contract. That only
works if the model saw the exact text we check against.

**One call per contract is cheap.** One call reads the contract once for all 12 fields. Twelve
calls would read it twelve times, at twelve times the input cost.

## Design decisions

- **Prompts are files in `domain/extract/prompts/v1/`.** You can read and compare them like any
  text. Other option: Python strings in `extract.py`. A prompt edit then looks like a code edit.
- **Two files: `system.md` and `user.md`.** Rules go in the system message, the contract in the
  user message. Other option: one message with both. Harder to see which part changed.
- **The placeholder is filled with `str.replace`.** `str.format` reads every `{` in the prompt as
  a placeholder. A JSON example in the prompt then breaks it (Step 2). Other option: a template
  library like Jinja. One more library for one job.
- **The placeholder must appear exactly once.** Zero means the contract is missing. Two means the
  contract is sent twice, at twice the cost. Other option: no check. The bug shows up only in
  the bill.
- **One call for all 12 fields.** Cheap, and the schema keeps the fields apart. Other option: one
  call per field. Maybe a little better per field, but 12 times the cost.
- **The contract comes from `txt_path`.** For all 52 dev contracts, the `.txt` file is exactly the
  text the `labels` offsets point into. Other option: the JSON file. Same text, slower to read.

## Worked example

Our example is a real dev contract:
`EcoScienceSolutionsInc_20171117_8-K_EX-10.1_10956472_EX-10.1_Endorsement Agreement`. It is
18,104 characters, about 4,500 tokens. 9 of the 12 fields are present.

Guess before you open each box. The answers come from a real run in Step 4: model
`qwen/qwen3-235b-a22b-2507`, prompt `v1`, temperature 0. Your run can differ a little.

### Round 1: a present field (Governing Law)

The gold span is:

> Regardless of the place of execution hereof, this Agreement, all amendments hereto, and any and
> all issues or controversies arising here from or related hereto, shall be governed by and
> construed exclusively in accordance with the laws and decisions of the State of Michigan.

Guess the model's `value`. Then guess its quote: the whole sentence, or only the end?

<details><summary>Guess, then open</summary>

Real output:

```json
{"quotes": ["this Agreement, all amendments hereto, and any and all issues or controversies arising here from or related hereto, shall be governed by and construed exclusively in accordance with the laws and decisions of the State of Michigan."],
 "value": "Michigan",
 "found": true}
```

- `value` is `"Michigan"`, not `"State of Michigan"`. It follows the rule "only the state or
  country".
- The quote drops the opening words "Regardless of the place of execution hereof,". It is still
  an exact copy, but it is shorter than the gold span. The token overlap with gold is 0.88. That
  is above the 1b2 threshold of 0.5, so it still counts.
- It keeps the typo "here from" as it is. The model copied the text and did not fix it. That is
  what the exact-copy rule asks for.
</details>

### Round 2: an absent field (Change Of Control)

The gold label says the contract has no change of control clause. Only 18 of the 52 dev contracts
have one. Guess `found` and `quotes`.

<details><summary>Guess, then open</summary>

Real output:

```json
{"quotes": [], "found": false}
```

- Correct. The words "change of control" and "merger" are not in the contract.
- The trap was section 15: "Neither this Agreement nor any of the rights or obligations contained
  herein may be assigned or transferred by either party without the prior written consent of the
  other party." That is **Anti-Assignment** (gold, start 12453), not change of control. The model
  put it under `anti_assignment` only, so there is no false positive here.
</details>

### Round 3: a list field (Parties)

The gold has four spans: `Eco Science Solutions, Inc.`, `ESSI`, `Stephen Marley`, `Talent`. Two
are names and two are short names the contract defines. Guess what the model puts in `value`,
and what it puts in `quotes`.

<details><summary>Guess, then open</summary>

Real output:

```json
{"quotes": ["THIS ENDORSEMENT AGREEMENT (the \"Agreement\") is dated as of this 14th day of November 2017 (\"Effective Date\"), by and between Eco Science Solutions, Inc. (\"ESSI\"), a Nevada corporation, and Stephen Marley (\"Talent\"), an individual."],
 "value": ["Eco Science Solutions, Inc. (\"ESSI\")", "Stephen Marley (\"Talent\")"],
 "found": true}
```

This is the interesting round. The model found the right parties, but it broke two rules:

- **`quotes`: one long sentence, not 4 names.** The prompt says "quotes has each name and each
  short name". The model copied the whole first sentence. That sentence is an exact copy, but its
  token overlap with each gold span is low: 0.13, 0.03, 0.07 and 0.03. All four are under 0.5,
  so 1b2 scores this field as wrong. The names are right, but the quote fails the rule.
- **`value`: the short names are still in it.** `"Eco Science Solutions, Inc. (\"ESSI\")"`
  should be `"Eco Science Solutions, Inc."`. The rule says short names go in `quotes` only.
- Rule 2 in the prompt ("copy the shortest full sentence or clause") pulls the model toward full
  sentences. For parties, that rule fights the parties rule. Write this down. It is the first
  candidate change for prompt `v2`, after you see the 1c numbers.
</details>

## Project setup

Create the folders and empty files:

```sh
$ mkdir -p src/docintel/domain/extract/prompts/v1
$ touch src/docintel/domain/extract/__init__.py src/docintel/domain/extract/extract.py
$ touch src/docintel/domain/extract/prompts/v1/system.md src/docintel/domain/extract/prompts/v1/user.md
$ touch tests/test_extract.py
```

You should now have:

```
src/docintel/
├── core/
│   ├── config.py
│   └── llm.py                 call_llm (1a2)
├── domain/
│   ├── extract/
│   │   ├── __init__.py
│   │   ├── extract.py         load_prompt, build_messages, extract
│   │   └── prompts/
│   │       └── v1/
│   │           ├── system.md  the rules (your decision)
│   │           └── user.md    the contract goes here
│   └── schema/
│       └── fields.py
└── evals/
tests/
└── test_extract.py            empty
```

## Step 1: prompt v1 (your decision)

**Why.** The prompt decides what the model looks for and how it writes the answer. Every number
in 1c comes from this text.

Here is the evidence. CUAD gives one short definition for each category. These are the real
"Details" lines from `CUAD_v1.json`:

| Field | CUAD definition |
|---|---|
| Parties | The two or more parties who signed the contract |
| Agreement Date | The date of the contract |
| Governing Law | Which state/country's law governs the interpretation of the contract? |
| Non-Compete | Is there a restriction on the ability of a party to compete with the counterparty or operate in a certain geography or business or technology sector? |
| Change Of Control | Does one party have the right to terminate or is consent or notice required of the counterparty if such party undergoes a change of control, such as a merger, stock sale, transfer of all or substantially all of its assets or business, or assignment by operation of law? |
| Anti-Assignment | Is consent or notice required of a party if the contract is assigned to a third party? |
| Renewal Term | What is the renewal term after the initial term expires? This includes automatic extensions and unilateral extensions with prior notice. |
| Notice Period To Terminate Renewal | What is the notice period required to terminate renewal? |
| Cap On Liability | Does the contract include a cap on liability upon the breach of a party's obligation? This includes time limitation for the counterparty to bring claims or maximum amount for recovery. |
| License Grant | Does the contract contain a license granted by one party to its counterparty? |
| Ip Ownership Assignment | Does intellectual property created by one party become the property of the counterparty, either per the terms of the contract or upon the occurrence of certain events? |
| Non-Transferable License | Does the contract limit the ability of a party to transfer the license being granted to a third party? |

More evidence from 0c and 1a:

- Gold spans are long. The median span for yes/no and license fields is 218 to 356 characters:
  whole sentences or clauses.
- 8 of the 12 fields are absent in more than 45% of contracts. The model must be good at saying
  "not there".
- Your schema has `quotes`, `value` and `found`. The model sees the field names and docstrings,
  but not what you want in `value`.

Decide each question. Write your answers in a markdown cell called "Prompt v1" in your notebook:

1. **Field definitions.** Copy the CUAD lines as they are, rewrite them in plain words, or give
   none (the model sees only the field names)?
2. **The absent rule.** What exactly should the model return when a field is not there? Say it
   for all three shapes: `Clause`, `Text`, `Names`.
3. **Quote length.** One key phrase, a full sentence, or the whole clause? Long gold spans favor
   longer quotes. 1b2 will measure the overlap.
4. **Exact copy.** How strongly do you say "copy, do not fix"? Models like to fix typos and add
   "...".
5. **Value formats.** Date as YYYY-MM-DD (from 1a)? What if only the year is known? Law as a
   short place name? What goes in `parties.value` and what in `parties.quotes`?
6. **Placement.** Rules in the system message and the contract in the user message? Wrap the
   contract in a tag like `<contract>` so the model sees where it starts and ends?

Then write `src/docintel/domain/extract/prompts/v1/system.md` with your rules. Write
`src/docintel/domain/extract/prompts/v1/user.md` with a short line and the placeholder
`{contract}`, exactly once.

Checkpoint. Check the files exist and are not empty:

```sh
$ wc -c src/docintel/domain/extract/prompts/v1/*.md
    2287 src/docintel/domain/extract/prompts/v1/system.md
      76 src/docintel/domain/extract/prompts/v1/user.md
    2363 total
```

These are the sizes of the reference below. Yours will differ. 2,287 characters is about 570
tokens, so the rules cost about one eighth of this contract.

<details><summary>Reference prompt v1 (open after you decide)</summary>

`system.md`:

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
- notice_period_to_terminate_renewal: the notice needed to stop a renewal, like "90 days".
- cap_on_liability: a short summary of the cap, like "fees paid in the last 12 months".

What each field means:
- parties: the two or more parties who signed the contract.
- agreement_date: the date of the contract.
- governing_law: which state or country's law governs the contract.
- non_compete: a party may not compete with the other party, or may not work in a certain place,
  business or technology.
- change_of_control: a party may end the contract, or must get consent or give notice, if the
  other party is bought, merged, or sells most of its assets.
- anti_assignment: consent or notice is needed to give the contract to a third party.
- renewal_term: the renewal term after the first term ends, including automatic renewals.
- notice_period_to_terminate_renewal: the notice needed to stop a renewal.
- cap_on_liability: a limit on how much a party must pay if it breaks the contract, or a time limit
  to bring claims.
- license_grant: one party gives the other a license.
- ip_ownership_assignment: intellectual property made by one party becomes the other party's
  property.
- non_transferable_license: a party may not transfer the license to a third party.
```

`user.md`:

```markdown
Fill in the 12 fields for this contract.

<contract>
{contract}
</contract>
```

Why:

- The CUAD lines are rewritten in plain words, and the field names match your schema.
- Rule 2 gives the absent answer as real JSON, so the model copies its shape.
- Rule 3 ties `found` to the quotes. `found: true` with no quote cannot be checked in 2a.
- "Shortest full sentence or clause": long enough to overlap the long gold spans, short enough to
  avoid copying a whole page.
- Parties: names in `value`, names and short names in `quotes`. The gold spans hold both.
</details>

## Step 2: load the prompt and build the messages

**Why.** `extract` must read one exact prompt version and put the contract in it with no change.

Put this in `src/docintel/domain/extract/extract.py`:

```python
"""Extract the 12 fields from one contract, with one LLM call and a versioned prompt."""

from pathlib import Path

import duckdb

from docintel.core.llm import LLMResult, call_llm
from docintel.domain.schema.fields import ContractFields

PROMPTS = Path(__file__).parent / "prompts"
PLACEHOLDER = "{contract}"


def load_prompt(version: str) -> tuple[str, str]:
    """(system, user) text of one prompt version, like "v1"."""
    folder = PROMPTS / version
    system = (folder / "system.md").read_text(encoding="utf-8")
    user = (folder / "user.md").read_text(encoding="utf-8")
    return system, user


def build_messages(text: str, version: str = "v1") -> list[dict]:
    """The messages for one contract. The contract text goes in unchanged."""
    system, user = load_prompt(version)
    if user.count(PLACEHOLDER) != 1:
        raise ValueError(f"prompt {version}: user.md must contain {PLACEHOLDER} exactly once")
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user.replace(PLACEHOLDER, text)},
    ]
```

*Python here: [`Path(__file__).parent`](./py/phase-1b.md#py-1) ·
[`read_text`](./py/phase-1b.md#py-2) · [`str.replace` and `str.format`](./py/phase-1b.md#py-3) ·
[returning two values](./py/phase-1b.md#py-4).*

Here, we:

1. Find the `prompts` folder next to `extract.py`, wherever you run the code from. Like
   `__dirname` in Node.
2. Read the two files of one version as text.
3. Check the placeholder is in `user.md` exactly once. If not, stop with a clear error.
4. Put the contract where the placeholder is. Nothing else in the text changes.
5. Return the two messages in the shape `call_llm` takes.

Why not `str.format`? The reference `system.md` has a JSON example, `{"quotes": [], "found":
false}`. This is what `.format` does with it:

```
KeyError: '"quotes"'
```

It read `{"quotes"...}` as a placeholder named `"quotes"`. `str.replace` only looks for the one
exact string `{contract}`.

Checkpoint. Build the messages for the example contract. Guess the second line first:

```sh
$ uv run python -c "
from pathlib import Path
import duckdb
from docintel.domain.extract.extract import build_messages
DOC = 'EcoScienceSolutionsInc_20171117_8-K_EX-10.1_10956472_EX-10.1_Endorsement Agreement'
con = duckdb.connect('data/docintel.duckdb', read_only=True)
(txt_path,) = con.execute('SELECT txt_path FROM contracts WHERE doc_id = ?', [DOC]).fetchone()
text = Path(txt_path).read_text(encoding='utf-8')
messages = build_messages(text)
print([m['role'] for m in messages], len(text), len(messages[1]['content']))
print(text in messages[1]['content'])
print(sum(len(m['content']) for m in messages) // 4)"
['system', 'user'] 18104 18170
True
5114
```

1. Two messages, in order.
2. The user message is 66 characters longer than the contract: the line and the tags around it.
3. `True`: the whole contract is inside, exactly as it was.
4. About 5,100 tokens of text, at 4 characters per token. This is a rough guess. Step 4 shows the
   real count.

## Step 3: `extract`

**Why.** Callers should ask for "the fields of this contract", and not build messages
themselves.

Add to the bottom of `src/docintel/domain/extract/extract.py`:

```python
def extract(
    text: str,
    model: str | None = None,
    *,
    prompt_version: str = "v1",
    con: duckdb.DuckDBPyConnection | None = None,
    run_id: str | None = None,
) -> LLMResult[ContractFields]:
    """All 12 fields for one contract text."""
    messages = build_messages(text, prompt_version)
    return call_llm(messages, ContractFields, con=con, run_id=run_id, model=model)
```

Here, we:

1. Build the messages for this text and this prompt version.
2. Call `call_llm` with your 1a schema, `ContractFields`.
3. Pass `con` and `run_id` through, so the call is logged. 1c sets `run_id`.
4. Return the whole `LLMResult`: parsed fields or error, plus tokens, cost and latency.

`extract` adds no new logic. That is the point: it is a small typed function, Pydantic out, that
the runner, the API and later an agent can all call.

Checkpoint:

```sh
$ uv run python -c "
import inspect
from docintel.domain.extract.extract import extract
print(inspect.signature(extract))"
(text: str, model: str | None = None, *, prompt_version: str = 'v1', con: _duckdb.DuckDBPyConnection | None = None, run_id: str | None = None) -> docintel.core.llm.LLMResult[docintel.domain.schema.fields.ContractFields]
```

## Step 4: run it on one dev contract

**Why.** Only a real answer shows what the prompt really does.

Close the notebook connection first: this writes to `llm_calls`. Then run:

```sh
$ uv run python -c "
from pathlib import Path
from docintel.domain.extract.extract import extract
from docintel.evals.store import connect
DOC = 'EcoScienceSolutionsInc_20171117_8-K_EX-10.1_10956472_EX-10.1_Endorsement Agreement'
with connect() as con:
    (txt_path,) = con.execute('SELECT txt_path FROM contracts WHERE doc_id = ?', [DOC]).fetchone()
    r = extract(Path(txt_path).read_text(encoding='utf-8'), con=con)
print(r.error, r.provider, r.attempts)
print(r.usage['prompt_tokens'], r.usage['completion_tokens'], r.cost_usd, r.latency_ms)
Path('data/examples').mkdir(exist_ok=True)
Path('data/examples/ecoscience_v1.json').write_text(r.raw_text, encoding='utf-8')"
```

Real output (your numbers will differ a little):

```
None Parasail 1
4476 697 0.00118424 22304
```

- Line 1: no error. OpenRouter picked the provider Parasail, and it took 1 attempt.
- Line 2: 4,476 prompt tokens. That is lower than the 5,114 we guessed in Step 2. Four characters
  per token is only a rough rule, and this tokenizer packs legal English better.
- 697 completion tokens. Most of them are the quotes.
- The cost was about $0.0012, and the call took 22 seconds. One call at a time, the 52 dev
  contracts would take many minutes. That is why 1c runs several calls at the same time.
- If `error` isn't `None`, read it before anything else. A schema error means the provider
  ignored `json_schema`.

Here, we:

1. Read the contract text from its `txt_path`.
2. Run `extract` with prompt `v1`, and log the call.
3. Print the error (it should be `None`), the provider, tokens, cost and latency.
4. Save the raw JSON answer in `data/examples/`. 1b2 scores this file. `data/` is not in git.

Now open the notebook, run cell 1, and compare with the gold labels:

```python
DOC = "EcoScienceSolutionsInc_20171117_8-K_EX-10.1_10956472_EX-10.1_Endorsement Agreement"
con.sql("""
SELECT category, is_present, start_char, left(span_text, 60) AS span
FROM labels
WHERE doc_id = $doc AND category IN ('Governing Law', 'Change Of Control', 'Parties')
ORDER BY category, start_char
""", params={"doc": DOC})
```

```
┌───────────────────┬────────────┬────────────┬──────────────────────────────────────────────────────────────┐
│     category      │ is_present │ start_char │                             span                             │
├───────────────────┼────────────┼────────────┼──────────────────────────────────────────────────────────────┤
│ Change Of Control │ false      │       NULL │ NULL                                                         │
│ Governing Law     │ true       │      14962 │ Regardless of the place of execution hereof, this Agreement, │
│ Parties           │ true       │        149 │ Eco Science Solutions, Inc.                                  │
│ Parties           │ true       │        179 │ ESSI                                                         │
│ Parties           │ true       │        213 │ Stephen Marley                                               │
│ Parties           │ true       │        230 │ Talent                                                       │
└───────────────────┴────────────┴────────────┴──────────────────────────────────────────────────────────────┘
```

And the model's answer for the same three fields. Run this in the terminal. It reads the saved
file, so there is no API call:

```sh
$ uv run python -c "
from pathlib import Path
from docintel.domain.schema.fields import ContractFields
pred = ContractFields.model_validate_json(Path('data/examples/ecoscience_v1.json').read_text(encoding='utf-8'))
for name in ['governing_law', 'change_of_control', 'parties']:
    print(name, getattr(pred, name).model_dump_json())"
governing_law {"quotes":["this Agreement, all amendments hereto, ... the State of Michigan."],"value":"Michigan","found":true}
change_of_control {"quotes":[],"found":false}
parties {"quotes":["THIS ENDORSEMENT AGREEMENT (the \"Agreement\") is dated as of ... an individual."],"value":["Eco Science Solutions, Inc. (\"ESSI\")","Stephen Marley (\"Talent\")"],"found":true}
```

(The long quotes are cut with `...` here. Your terminal prints them in full.)

`model_validate_json` passing is itself a check: the saved answer still fits `ContractFields`.

Now open the three rounds in the Worked example. Write in your notebook, for each field: right,
wrong, or "right, but the quote is shorter than the gold span".

## Step 5: a test for the rules that must never break

**Why.** Three things must always be true:

1. Every prompt version has a non-empty `system.md` and a `user.md` with the placeholder once.
2. The contract text goes into the messages unchanged, even with `{`, `}` and quotes in it.
3. An unknown version fails loudly, not with an empty prompt.

Put this in `tests/test_extract.py`:

```python
"""Prompt and message rules. No network, no key."""

import pytest

from docintel.domain.extract.extract import PLACEHOLDER, PROMPTS, build_messages, load_prompt

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
```

*Python here: [`iterdir` and `is_dir`](./py/phase-1b.md#py-5) · `pytest.raises`:
[1a PY-5](./py/phase-1a.md#py-5).*

Here, we:

1. Go through every folder in `prompts/`. When you add `v2`, it is tested with no new code.
2. Use a fake contract with braces, quotes and a newline: the characters that break templates.
3. Check the text is inside the user message, and the placeholder is gone.
4. Ask for `v999`, which does not exist. It must raise `FileNotFoundError`.

Checkpoint:

```sh
$ make lint && make test
All checks passed!
...
tests/test_data_load.py ....                                             [ 19%]
tests/test_extract.py ...                                                [ 33%]
tests/test_llm.py ....                                                   [ 52%]
tests/test_schema.py ....                                                [ 71%]
tests/test_smoke.py .                                                    [ 76%]
tests/test_splits.py .....                                               [100%]

============================== 21 passed in 0.81s ==============================
```

Your project should now look like this:

```
src/docintel/
├── core/
│   ├── config.py
│   └── llm.py
├── domain/
│   ├── extract/
│   │   ├── __init__.py
│   │   ├── extract.py         PROMPTS, PLACEHOLDER, load_prompt, build_messages, extract
│   │   └── prompts/v1/
│   │       ├── system.md
│   │       └── user.md
│   └── schema/fields.py
└── evals/
tests/
├── test_extract.py            3 tests
└── ...
data/
├── docintel.duckdb            + 1 row in llm_calls
└── examples/
    └── ecoscience_v1.json     the saved answer for 1b2
```

<details><summary>Full <code>src/docintel/domain/extract/extract.py</code></summary>

```python
"""Extract the 12 fields from one contract, with one LLM call and a versioned prompt."""

from pathlib import Path

import duckdb

from docintel.core.llm import LLMResult, call_llm
from docintel.domain.schema.fields import ContractFields

PROMPTS = Path(__file__).parent / "prompts"
PLACEHOLDER = "{contract}"


def load_prompt(version: str) -> tuple[str, str]:
    """(system, user) text of one prompt version, like "v1"."""
    folder = PROMPTS / version
    system = (folder / "system.md").read_text(encoding="utf-8")
    user = (folder / "user.md").read_text(encoding="utf-8")
    return system, user


def build_messages(text: str, version: str = "v1") -> list[dict]:
    """The messages for one contract. The contract text goes in unchanged."""
    system, user = load_prompt(version)
    if user.count(PLACEHOLDER) != 1:
        raise ValueError(f"prompt {version}: user.md must contain {PLACEHOLDER} exactly once")
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user.replace(PLACEHOLDER, text)},
    ]


def extract(
    text: str,
    model: str | None = None,
    *,
    prompt_version: str = "v1",
    con: duckdb.DuckDBPyConnection | None = None,
    run_id: str | None = None,
) -> LLMResult[ContractFields]:
    """All 12 fields for one contract text."""
    messages = build_messages(text, prompt_version)
    return call_llm(messages, ContractFields, con=con, run_id=run_id, model=model)
```
</details>

## Break it on purpose

**Break 1: the placeholder twice.** Add a last line to `user.md`: `Reminder: {contract} is above.`
Guess which tests fail:

```
E           AssertionError: assert 2 == 1
E           ValueError: prompt v1: user.md must contain {contract} exactly once
FAILED tests/test_extract.py::test_every_version_has_both_files - AssertionEr...
FAILED tests/test_extract.py::test_contract_text_goes_in_unchanged - ValueErr...
========================= 2 failed, 19 passed in 0.88s =========================
```

Without the check, each call would send the contract twice and cost twice as much. No error,
only a bigger bill. Remove the line.

**Break 2: a path from the current folder.** Change `PROMPTS` to `Path("prompts")`. Guess what
happens when you run from the project root:

```
E       FileNotFoundError: [Errno 2] No such file or directory: 'prompts'
E       FileNotFoundError: [Errno 2] No such file or directory: 'prompts/v1/system.md'
FAILED tests/test_extract.py::test_every_version_has_both_files - FileNotFoun...
FAILED tests/test_extract.py::test_contract_text_goes_in_unchanged - FileNotF...
========================= 2 failed, 19 passed in 0.79s =========================
```

`Path("prompts")` means "a `prompts` folder where I run the command". `Path(__file__).parent`
means "next to this file". In Docker (4c) and in the API (4a), the working folder is different
again. Change it back.

## Experiment

This part runs one contract, not a dataset. There is no `run_id` yet: the runner comes in 1c.
So there is no `EXPERIMENTS.md` entry. The `llm_calls` row and `data/examples/ecoscience_v1.json`
are the record.

Use the numbers for a first cost guess for 1c. In the notebook:

```python
con.sql("SELECT prompt_tokens, completion_tokens, cost_usd, latency_ms FROM llm_calls ORDER BY created_at DESC LIMIT 1")
```

Dev has 52 contracts, about 13,000 tokens each on average. This one has about 5,100 by the same
4-characters rule. Multiply
its cost by 52 times 13,000 / 5,100 for a rough cost of one dev run. Write that number in your
notebook.

## Gotchas

- **Never edit `v1` after 1c.** Copy the folder to `v2`, then edit. Old runs must still point to
  the text that made them.
- **A typo in the placeholder.** `{contracts}` or `{ contract }` is not found. The check raises
  `ValueError`, so the model never gets a prompt with no contract.
- **Lock error.** Step 4 writes to `data/docintel.duckdb`. Close the notebook connection first.
- **The biggest contract.** The longest CUAD contract is about 84,500 tokens. It fits the
  262,000-token window, but it costs about 16 times this one.
- **Read the answer, not only the error.** `error` is `None` when the JSON fits the schema. The
  content can still be wrong. That is what 1b2 measures.

## Explain back, then commit

Explain each changed file to Claude in a few sentences (the rule in `PLAN.md`): `system.md` and
`user.md` (each rule and its evidence), `extract.py` (each function, and why `replace` and not
`format`), `test_extract.py` (each test), and the notebook cells "Prompt v1" and the three-field
comparison. Then:

```sh
$ git status
$ git add src/docintel/domain/extract tests/test_extract.py notebooks/00_explore.ipynb
$ git commit -m "phase 1b: prompt v1 and extract()"
```

## Conclusion

What you have now:

- Prompt `v1`, in two files, with a reason for each rule.
- `extract(text)`: one call, your schema, the contract text unchanged.
- One real answer for one dev contract, saved for 1b2, and a first cost guess for 1c.

Go back to the objectives. Check that you can do each one without notes. Then answer:

1. Why must the contract go into the prompt with no change at all? Which later part needs it?
2. You want to add one sentence to the prompt after 1c. What do you do, and why?

Want more practice? Try these (optional):

1. Run `extract` on the same contract three times. Do the quotes change? (`temperature=0`
   helps, but some providers are still not fully the same each time.)
2. Make a `v2` with the CUAD definitions copied word for word. Compare the three fields.
3. Count the tokens of your `system.md` with the `prompt_tokens` of a call on a tiny contract.

Checklist (`../PLAN.md`): **Prompt versioning; context engineering** (prompt versioning done;
context engineering started: rules in the system message, the contract in tags in the user
message, one call for all fields).
