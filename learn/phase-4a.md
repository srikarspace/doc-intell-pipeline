# Phase 4a: the planner (E4)

In this part, you build the planner. It reads a request typed by a person, and picks which of the 12 fields to
return. Then you measure it on requests you write yourself. Each piece has a checkpoint.

This is part 1 of 3 for Phase 4a. 4a2 builds the API around the pipeline. 4a3 adds the key, the rate limit and the
spend cap. This part costs about $0.002 in total.

## Words used in this part

Read these first.

- **Request**: what the user types. Example: `parties, renewal term, any non-compete?`.
- **Planner**: the code that turns a request into a list of field names.
- **Plan**: the planner's answer: the fields to return, and what it could not map. Example:
  `fields=['parties']`, `unknown=['payment terms']`.
- **Unknown**: a thing the request asks for that none of our 12 fields covers. Example: payment terms.
- **Enum**: a closed list of allowed values. Example: the 12 field names, and nothing else.
- **`Literal`**: the Python way to write an enum in a type. Example: `Literal["parties", "governing_law"]`.
- **Dynamic model**: a Pydantic model built while the program runs, not written by hand.
- **Exact match**: the plan has the right fields and the right "unknown or not". All of it, or it is a miss.
- **Eval set**: a fixed list of inputs with their right answers, used to measure a part. Here, about 15 requests.

## Objectives

By the end of this part you should be able to:

1. Explain why the planner chooses from a closed list, and what the schema does about it.
2. Map a free-text request to field names with one cheap LLM call, with a token limit.
3. Build a model with only the chosen fields, from the existing sub-models.
4. Write an eval set of requests, and score the planner on it (E4).
5. Explain why extraction still reads all 12 fields.

## Dependencies

You install nothing new. This part needs:

- 1a: `Strict` and `ContractFields`.
- 1a2 and 3a3: `call_llm`, with `max_tokens`.
- 3a3: `Budget`, and `provider_price` from `parse_pilot.py`. You move `provider_price` in Step 1.
- An OpenRouter key in `.env` (`sk-or-v1-...`), for two checkpoints and the Experiment.

## The big picture

Before this part, a run always extracted all 12 fields. Nobody could ask a question.

After this part:

```text
"parties, renewal term, any non-compete?"
        |
     planner (1 small LLM call, closed list of 12 names)
        |
Plan(fields=['parties', 'non_compete', 'renewal_term'], unknown=[])
```

- **4a2** puts the planner first in the pipeline, behind `POST /v1/extract`.
- **4d** shows the `unknown` list in the UI, so a user knows what was not answered.

## Remember this

> The planner only chooses. It never reads the contract. Its schema holds a closed list of the 12 names, so the
> model cannot invent a field. Anything it cannot map, it must list as unknown, so the user sees what is missing.
>
> **Choose from a closed list, and name what is missing.**

## Why

**People do not type field names.** They write "who signed this?" or "can they sell the company?". Something must
turn that into `parties` and `change_of_control`.

**A wrong guess is worse than "I don't know".** If the request asks for payment terms, the honest answer is "we do not
extract that". A silent empty answer looks like "the contract has no payment terms".

**It must be measured like everything else.** E4 is small, but it gives a number and a `run_id`.

## Design decisions

- **The field list in the schema is an enum, built from `ContractFields`.** A new field in the schema is a new
  allowed name, with no second list to update. Other option: a free string list, checked after. The model could
  answer `payment_terms`, and we would find out later.
- **Fields come back in schema order, with no repeats.** The same request always gives the same list. Other option:
  keep the model's order. Two runs could differ only in order.
- **An empty request means all 12, with no LLM call.** It is free, and the same every time. Other option: refuse it. A user who
  uploads a contract with no question still wants an answer.
- **Extraction still reads all 12 fields. The planner picks what to return.** The validators and the retry loop loop
  over all 12 fields. Also, E1 to E3 measured the 12-field call. Other option: a smaller schema per request. That is a
  new extraction call that no experiment has measured.
- **`selected_model` builds the smaller model from the same sub-models.** The returned JSON has the same shape as one
  field in E1 to E3. Other option: return a plain dict. Nothing would check its shape.
- **The eval set is a file you write.** You decide what "right" means, before you see the planner's answers. Other
  option: ask an LLM to write the requests. It would write requests that are easy for an LLM.
- **"Unknown" is scored yes or no.** The model's words change between runs (Round 3). Other option: compare the
  strings. Every run would look like a miss.

## Worked example

All numbers are real. Guess before you open each box.

### Round 1: do we need an LLM at all?

A keyword planner is free. For example: "renew" means `renewal_term`, "law" means `governing_law`. It was written to
fit the 16 requests of the reference set, so it is a kind test for it. Guess its exact-match score.

<details><summary>Guess, then open</summary>

**9 of 16.** It never finds an unknown, because it only knows our words. It also adds fields that nobody asked for:

```text
r01 ['agreement_date']   "Who signed this contract?": "signed" also means a date
r06 ['renewal_term']     "notice ... to stop it renewing": "renew" is in the question
r09 ['parties']          "Who owns the IP": "who" means parties
r14 ['parties']          "When was it signed": "signed" again
```

The LLM planner got 16 of 16 on the same set. A word list cannot tell "who signed" from "when was it signed".
</details>

### Round 2: what does a planner call cost?

The request `parties, renewal term, any non-compete?` gives a 3-field answer of about 60 characters. Guess the output
tokens.

<details><summary>Guess, then open</summary>

```text
349 444 0.00017318 2141 Parasail
```

349 tokens in, **444 out**, $0.00017, 2.1 s. Most of the output is hidden thinking, as in 3a3. Over 30 real calls,
the largest answer used 654 tokens. So a limit of 4,000 leaves a lot of room. It still caps the worst case at about
$0.0012 per call.
</details>

### Round 3: extract only the asked fields?

An extraction call costs $0.0018 on average. The input (the whole contract) is about 64% of that. Guess: if a request
asks for 1 field, how much would a 1-field extraction save?

<details><summary>Guess, then open</summary>

At most the output part, about 36%. The contract is read in full either way. And the risk is high: the validators,
the retry loop and every F1 number so far are built on the 12-field call. A small saving does not pay for a call that
was never measured. So we extract 12 and return the asked ones.
</details>

## Project setup

```sh
mkdir -p src/docintel/domain/planner evals
touch src/docintel/domain/planner/__init__.py
touch src/docintel/domain/planner/planner.py
touch src/docintel/domain/planner/prompt.md
touch src/docintel/evals/planner_eval.py
touch evals/planner_requests.json
touch tests/test_planner.py
```

You should now have:

```text
evals/
└── planner_requests.json        # new: your eval set
src/docintel/
├── domain/planner/
│   ├── __init__.py              # new
│   ├── planner.py               # new
│   └── prompt.md                # new
└── evals/
    └── planner_eval.py          # new
tests/
└── test_planner.py              # new
```

## Step 1: move `provider_price` to `core/llm.py`

**Why.** The planner eval needs the price too. A second user is the moment to move shared code to `core/`.

Cut `provider_price` from `src/docintel/evals/parse_pilot.py`, and paste it at the bottom of
`src/docintel/core/llm.py`:

```python
def provider_price(model: str) -> tuple[float, float]:
    """(input, output) USD per token on OUR provider. The highest, if it has several endpoints."""
    s = get_settings()
    url = f"{s.openrouter_base_url}/models/{model}/endpoints"
    with urllib.request.urlopen(url, timeout=30) as r:
        endpoints = json.load(r)["data"]["endpoints"]
    ours = [e["pricing"] for e in endpoints if e["provider_name"].lower() == s.docintel_provider]
    if not ours:
        raise ValueError(f"{model} is not served by {s.docintel_provider}")
    return max(float(p["prompt"]) for p in ours), max(float(p["completion"]) for p in ours)
```

Update the imports at the top of `src/docintel/core/llm.py`. Add `json` and `urllib.request`:

```python
import json
import time
import urllib.request
import uuid
```

In `src/docintel/evals/parse_pilot.py`, replace `from docintel.core.config import get_settings` with:

```python
from docintel.core.llm import provider_price
```

Remove `import urllib.request` there too, if `ruff` says it is unused.

Checkpoint:

```sh
uv run python -c "from docintel.core.llm import provider_price; print(provider_price('deepseek/deepseek-v4-flash'))"
make lint
```

```text
(1.4e-07, 2.8e-07)
```

That is $0.14 and $0.28 per million tokens on Parasail. It is free to read, and needs no key.

## Step 2: how the planner behaves (your decision)

**Why.** These choices decide what a user sees when the planner is unsure.

Decide four things. Write them in `EXPERIMENTS.md`, under a new `## E4` heading.

| Question | Options | Evidence |
|---|---|---|
| How to map | keyword list; LLM with an enum; both | Round 1: 9/16 against 16/16 |
| Unknown things | refuse the request; answer the known fields and list the unknown | Why, paragraph 2 |
| Empty request | all 12 fields; refuse | a user who asks nothing |
| Extraction scope | only the asked fields; all 12, return the asked ones | Round 3 |

Then decide one more: what to do when **only** unknown things are asked, like "payment terms?". 4a2 needs this.

<details><summary>Reference (open after you write yours)</summary>

- **How to map:** LLM with an enum. It costs about $0.0001 per request, and it can name unknowns.
- **Unknown things:** answer the known fields, and list the unknown ones in the response.
- **Empty request:** all 12 fields, with no LLM call.
- **Extraction scope:** extract all 12, return the asked ones.
- **Only unknown things:** refuse with status 422 and the unknown list, before any extraction call (4a2).
</details>

## Step 3: the plan schema and the prompt

**Why.** The schema is what stops the model from inventing a field.

Put this in `src/docintel/domain/planner/planner.py`:

```python
"""Planner: turn a free-text request into known fields, and list what we cannot answer."""

from pathlib import Path
from typing import Literal

import duckdb
from pydantic import BaseModel, create_model

from docintel.core.llm import LLMResult, call_llm
from docintel.domain.schema.fields import ContractFields, Strict

FIELDS = tuple(ContractFields.model_fields)
FieldName = Literal[FIELDS]
PROMPT = Path(__file__).parent / "prompt.md"
PLAN_MAX_TOKENS = 4000  # hidden thinking counts; real planner calls used at most 654


class Plan(Strict):
    fields: list[FieldName]
    unknown: list[str]


class PlanError(ValueError):
    pass
```

*Python here: [`Literal` from a tuple](./py/phase-4a.md#py-1).*

Here, we:

1. Take the 12 names from `ContractFields`, in their order.
2. Make a type that allows only those names.
3. Use it in `Plan`. The JSON schema sent to the model now holds an `enum` of 12 names.

The prompt is a user decision, as in 1b. It must say: what each field means, that only these names are allowed, and
how to list unknowns.

<details><summary>Reference prompt: put this in <code>src/docintel/domain/planner/prompt.md</code></summary>

```markdown
You turn a user's request into the fields that a contract tool can extract. Answer only with JSON
that fits the schema.

The fields:
- parties: who signed the contract.
- agreement_date: the date of the contract.
- governing_law: which state or country's law governs the contract.
- non_compete: a party may not compete, or may not work in a certain place or business.
- change_of_control: what happens if a party is bought, merged, or sells most of its assets.
- anti_assignment: consent or notice is needed to give the contract to a third party.
- renewal_term: how long the contract renews for after the first term.
- notice_period_to_terminate_renewal: the notice needed to stop a renewal.
- cap_on_liability: a limit on how much a party must pay, or on the time to bring claims.
- license_grant: one party gives the other a license.
- ip_ownership_assignment: intellectual property made by one party belongs to the other.
- non_transferable_license: a party may not transfer its license to a third party.

Rules:
1. fields: each field the request asks about, using only the names above, each name once.
2. "Everything" or "all fields" means all 12 names.
3. unknown: each thing the request asks about that no field covers, in a few words taken from the
   request. Example: "payment terms". Use [] if there is none.
4. Do not add a field that the request does not ask about.

Request:
{request}
```

The field lines are shorter than in the v1 extraction prompt. The planner only needs to know what each field is
about, not how to fill it.
</details>

Checkpoint (free):

```sh
uv run python - <<'EOF'
from docintel.domain.planner.planner import Plan

schema = Plan.model_json_schema()
print(schema["properties"]["fields"]["items"]["enum"][:3], "...", len(schema["properties"]["fields"]["items"]["enum"]))
EOF
```

```text
['parties', 'agreement_date', 'governing_law'] ... 12
```

## Step 4: one planner call

**Why.** This is the planner itself.

Add to the bottom of `src/docintel/domain/planner/planner.py`:

```python
def plan_messages(request: str) -> list[dict]:
    text = PROMPT.read_text(encoding="utf-8").replace("{request}", request)
    return [{"role": "user", "content": text}]


def plan_request(
    request: str,
    *,
    model: str | None = None,
    client=None,
    con: duckdb.DuckDBPyConnection | None = None,
    run_id: str | None = None,
) -> tuple[Plan, LLMResult | None]:
    """The fields a request asks for, in schema order. An empty request means all of them."""
    if not request.strip():
        return Plan(fields=list(FIELDS), unknown=[]), None
    result = call_llm(
        plan_messages(request),
        Plan,
        con=con,
        run_id=run_id,
        model=model,
        client=client,
        max_tokens=PLAN_MAX_TOKENS,
    )
    if result.parsed is None:
        raise PlanError(f"bad plan: {result.error}")
    chosen = set(result.parsed.fields)
    plan = Plan(fields=[f for f in FIELDS if f in chosen], unknown=result.parsed.unknown)
    return plan, result
```

Here, in order:

1. An empty request returns all 12 fields. No call is made.
2. Otherwise, send the prompt with the request inside it, with a token limit.
3. If the answer does not fit the schema, raise `PlanError`. A bad plan must never become "no fields".
4. Put the chosen fields in schema order, once each.

Checkpoint (paid, about $0.0002; the worst case is $0.0012):

```sh
uv run python - <<'EOF'
from docintel.domain.planner.planner import plan_request

plan, r = plan_request("parties, renewal term, any non-compete?")
print(plan)
print(r.usage.get("prompt_tokens"), r.usage.get("completion_tokens"), r.cost_usd, r.latency_ms, r.provider)
EOF
```

```text
fields=['parties', 'non_compete', 'renewal_term'] unknown=[]
349 444 0.00017318 2141 Parasail
```

The request said renewal term before non-compete. The plan uses schema order.

## Step 5: a model with only the chosen fields

**Why.** 4a2 returns only the asked fields. This builds their shape from the same sub-models.

Add to the bottom of `src/docintel/domain/planner/planner.py`:

```python
def selected_model(fields: list[str]) -> type[BaseModel]:
    """A model with only these fields, each with its own sub-model from ContractFields."""
    chosen = {f: (ContractFields.model_fields[f].annotation, ...) for f in fields}
    return create_model("Requested", __base__=Strict, **chosen)


def pick(answer: ContractFields, fields: list[str]) -> BaseModel:
    """Keep only the requested fields of a full answer."""
    return selected_model(fields).model_validate(answer.model_dump(include=set(fields)))
```

*Python here: [`create_model`](./py/phase-4a.md#py-2) · [`model_dump(include=...)`](./py/phase-4a.md#py-3).*

Here, we:

1. Build a new model class, named `Requested`, with one entry per chosen field.
2. Give each entry the same sub-model as in `ContractFields`: `Names`, `Text` or `Clause`.
3. In `pick`, keep only those fields of a full answer, and check them against the new model.

Checkpoint (free):

```sh
uv run python - <<'EOF'
from docintel.domain.planner.planner import selected_model

model = selected_model(["parties", "non_compete"])
print(model.__name__, list(model.model_fields))
print({k: v["$ref"] for k, v in model.model_json_schema()["properties"].items()})
EOF
```

```text
Requested ['parties', 'non_compete']
{'parties': '#/$defs/Names', 'non_compete': '#/$defs/Clause'}
```

## Step 6: your eval set (your decision)

**Why.** You decide what a right plan is, before the planner answers.

Write about 15 requests in `evals/planner_requests.json`. Each one has an `id`, the `request`, the `fields` it should
give, and `unknown`: true if it asks for something we do not extract.

Cover these cases:

- A field asked by name, and a field asked in other words ("who signed").
- Two or three fields in one request.
- "Everything", and an empty request.
- A thing we do not extract at all ("payment terms").
- A CUAD category that is **not** one of our 12, like expiration date or exclusivity. These are the hard ones.
- A request that could fit two fields.

<details><summary>Reference set (open after you write yours)</summary>

```json
[
  {"id": "r01", "request": "Who signed this contract?", "fields": ["parties"], "unknown": false},
  {"id": "r02", "request": "parties, renewal term, any non-compete?", "fields": ["parties", "non_compete", "renewal_term"], "unknown": false},
  {"id": "r03", "request": "Which state's law applies?", "fields": ["governing_law"], "unknown": false},
  {"id": "r04", "request": "Can they sell the company without asking us?", "fields": ["change_of_control"], "unknown": false},
  {"id": "r05", "request": "Is there a limit on damages?", "fields": ["cap_on_liability"], "unknown": false},
  {"id": "r06", "request": "How much notice do I need to give to stop it renewing?", "fields": ["notice_period_to_terminate_renewal"], "unknown": false},
  {"id": "r07", "request": "Can I hand this agreement over to another company?", "fields": ["anti_assignment"], "unknown": false},
  {"id": "r08", "request": "Do we get a license, and can we pass it on to someone else?", "fields": ["license_grant", "non_transferable_license"], "unknown": false},
  {"id": "r09", "request": "Who owns the IP we create?", "fields": ["ip_ownership_assignment"], "unknown": false},
  {"id": "r10", "request": "Everything.", "fields": ["parties", "agreement_date", "governing_law", "non_compete", "change_of_control", "anti_assignment", "renewal_term", "notice_period_to_terminate_renewal", "cap_on_liability", "license_grant", "ip_ownership_assignment", "non_transferable_license"], "unknown": false},
  {"id": "r11", "request": "", "fields": ["parties", "agreement_date", "governing_law", "non_compete", "change_of_control", "anti_assignment", "renewal_term", "notice_period_to_terminate_renewal", "cap_on_liability", "license_grant", "ip_ownership_assignment", "non_transferable_license"], "unknown": false},
  {"id": "r12", "request": "What are the payment terms?", "fields": [], "unknown": true},
  {"id": "r13", "request": "Governing law, and can we terminate for convenience?", "fields": ["governing_law"], "unknown": true},
  {"id": "r14", "request": "When was it signed and when does it expire?", "fields": ["agreement_date"], "unknown": true},
  {"id": "r15", "request": "Does it renew by itself, and for how long?", "fields": ["renewal_term"], "unknown": false},
  {"id": "r16", "request": "Is there an exclusivity clause or a non-compete?", "fields": ["non_compete"], "unknown": true}
]
```

r04 is the one that could fit two fields: selling the company is change of control, not assignment.
</details>

## Step 7: the E4 runner

**Why.** It scores every request, stores each plan, and shows the cost first.

Put this in `src/docintel/evals/planner_eval.py`:

```python
"""E4: the planner on hand-written requests. Cost first, one row per request in `plans`."""

import argparse
import json
from datetime import datetime
from pathlib import Path

import duckdb

from docintel.core.config import get_settings
from docintel.core.llm import provider_price
from docintel.domain.parse.vision import Budget, BudgetExceeded
from docintel.domain.planner.planner import PLAN_MAX_TOKENS, Plan, plan_messages, plan_request
from docintel.evals.store import connect

REQUESTS = Path("evals/planner_requests.json")
TABLE = """
CREATE TABLE IF NOT EXISTS plans (
    run_id VARCHAR, req_id VARCHAR, request VARCHAR, expected JSON, fields JSON, unknown JSON,
    tp INTEGER, fp INTEGER, fn INTEGER, unknown_ok BOOLEAN, exact BOOLEAN, cost_usd DOUBLE,
    PRIMARY KEY (run_id, req_id)
)
"""


def score_plan(case: dict, plan: Plan) -> dict:
    """Compare one plan with what the request should give."""
    want, got = set(case["fields"]), set(plan.fields)
    unknown_ok = bool(plan.unknown) == case["unknown"]
    return {
        "tp": len(want & got),
        "fp": len(got - want),
        "fn": len(want - got),
        "unknown_ok": unknown_ok,
        "exact": want == got and unknown_ok,
    }


def worst_cost(request: str) -> float:
    in_price, out_price = provider_price(get_settings().docintel_model)
    chars = len(plan_messages(request)[0]["content"])
    return chars / 3 * in_price + PLAN_MAX_TOKENS * out_price  # 3 chars per token: a high guess


def run(con: duckdb.DuckDBPyConnection, cases: list[dict], budget: Budget, run_id: str) -> None:
    con.execute(TABLE)
    for case in cases:
        budget.check(worst_cost(case["request"]))
        plan, result = plan_request(case["request"], con=con, run_id=run_id)
        cost = (result.cost_usd or 0.0) if result else 0.0
        budget.add(cost)
        s = score_plan(case, plan)
        row = [run_id, case["id"], case["request"], json.dumps(case)]
        row += [json.dumps(plan.fields), json.dumps(plan.unknown), *s.values(), cost]
        con.execute("INSERT INTO plans VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", row)
        mark = "ok  " if s["exact"] else "MISS"
        print(
            f"{mark} {case['id']} {case['request'][:44]!r:46} {plan.fields} unknown={plan.unknown}"
        )
```

Here, for each request, in order:

1. Check the budget against the worst case of this call. This is `Budget` from 3a3.
2. Plan the request. The call is logged in `llm_calls` with the `run_id`.
3. Score it: fields found, fields added, fields missed, and "unknown or not".
4. Store one row in `plans`, and print one line.

The summary and the command line are boilerplate, so copy them.

<details><summary>Add to the bottom of <code>src/docintel/evals/planner_eval.py</code></summary>

```python
SUMMARY = """
SELECT count(*), count(*) FILTER (WHERE exact), sum(tp), sum(fp), sum(fn),
    count(*) FILTER (WHERE unknown_ok), sum(cost_usd)
FROM plans WHERE run_id = ?
"""


def report(con: duckdb.DuckDBPyConnection, run_id: str) -> None:
    n, exact, tp, fp, fn, unknown_ok, cost = con.execute(SUMMARY, [run_id]).fetchone()
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    print(
        f"run {run_id}: exact {exact}/{n}, field P {precision:.2f} R {recall:.2f}, "
        f"unknown right {unknown_ok}/{n}, cost ${cost:.4f}"
    )


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="python -m docintel.evals.planner_eval")
    ap.add_argument("--requests", type=Path, default=REQUESTS)
    ap.add_argument("--budget", type=float, required=True, help="stop before passing this, in USD")
    ap.add_argument("--yes", action="store_true")
    args = ap.parse_args(argv)
    cases = json.loads(args.requests.read_text(encoding="utf-8"))
    worst = sum(worst_cost(c["request"]) for c in cases if c["request"].strip())
    print(f"{len(cases)} requests, worst case ${worst:.4f}, budget ${args.budget:.2f}")
    if not args.yes and input("Start? [y/N] ").strip().lower() != "y":
        return
    run_id = f"e4-{datetime.now():%Y%m%d-%H%M%S}"
    budget = Budget(args.budget)
    with connect() as con:
        try:
            run(con, cases, budget, run_id)
        except BudgetExceeded as e:
            print("stopped:", e)
        report(con, run_id)


if __name__ == "__main__":
    main()
```
</details>

Checkpoint (free; type `n`):

```sh
uv run python -m docintel.evals.planner_eval --budget 0.03
```

```text
16 requests, worst case $0.0178, budget $0.03
Start? [y/N] n
```

## Step 8: a small test

**Why.** If the enum or the empty-request rule breaks, the planner can invent fields or spend money with no warning.

The test names say what is protected: an unknown field name is refused, fields come back in order with a token limit,
an empty request makes no call, a bad plan raises, and `pick` keeps only the chosen fields.

<details><summary>Put this in <code>tests/test_planner.py</code></summary>

```python
"""The planner with a fake OpenRouter: no network, no key, no cost."""

import json

import httpx2
import pytest
from openai import OpenAI
from pydantic import ValidationError

from docintel.core.config import get_settings
from docintel.domain.planner.planner import (
    FIELDS,
    PLAN_MAX_TOKENS,
    Plan,
    PlanError,
    pick,
    plan_request,
    selected_model,
)
from docintel.domain.schema.fields import ContractFields
from docintel.evals.runner import empty_answer


def fake_client(content: str) -> tuple[OpenAI, list]:
    sent = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        sent.append(json.loads(request.content))
        body = {
            "id": "gen-1",
            "object": "chat.completion",
            "created": 0,
            "model": "fake/model",
            "choices": [
                {
                    "index": 0,
                    "finish_reason": "stop",
                    "message": {"role": "assistant", "content": content},
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "cost": 0.0001},
        }
        return httpx2.Response(200, json=body)

    http = httpx2.Client(transport=httpx2.MockTransport(handler))
    client = OpenAI(
        api_key="sk-or-v1-test", base_url="https://fake.test/v1", max_retries=0, http_client=http
    )
    return client, sent


@pytest.fixture(autouse=True)
def key(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-test")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_a_field_name_we_do_not_have_is_rejected():
    with pytest.raises(ValidationError):
        Plan(fields=["payment_terms"], unknown=[])


def test_fields_come_back_in_schema_order_with_a_token_limit():
    answer = {"fields": ["renewal_term", "parties", "parties"], "unknown": ["payment terms"]}
    client, sent = fake_client(json.dumps(answer))
    plan, _ = plan_request("renewal and parties, and payment terms", client=client)
    assert plan.fields == ["parties", "renewal_term"]
    assert plan.unknown == ["payment terms"]
    assert sent[0]["max_tokens"] == PLAN_MAX_TOKENS


def test_an_empty_request_means_all_fields_and_no_call():
    plan, result = plan_request("   ")
    assert plan.fields == list(FIELDS)
    assert result is None


def test_a_bad_plan_raises():
    client, _ = fake_client('{"fields": ["payment_terms"], "unknown": []}')
    with pytest.raises(PlanError):
        plan_request("payment terms", client=client)


def test_pick_keeps_only_the_chosen_fields():
    full = ContractFields.model_validate({f: empty_answer(f) for f in FIELDS})
    picked = pick(full, ["parties", "non_compete"])
    assert list(type(picked).model_fields) == ["parties", "non_compete"]
    assert set(selected_model(["governing_law"]).model_json_schema()["properties"]) == {
        "governing_law"
    }
```
</details>

Here, we use the fake OpenRouter from 1a2 and 3a3. No network, no key, no cost.

Checkpoint:

```sh
uv run pytest tests/test_planner.py -q
make lint
```

```text
.....                                                                    [100%]
5 passed in 0.41s
```

Your project structure should now look like this:

```text
evals/planner_requests.json
src/docintel/
├── core/llm.py                  # + provider_price
├── domain/planner/
│   ├── __init__.py
│   ├── planner.py               # Plan, plan_request, selected_model, pick
│   └── prompt.md
└── evals/
    ├── parse_pilot.py           # imports provider_price from core
    └── planner_eval.py          # E4
tests/test_planner.py
```

<details><summary>Complete <code>src/docintel/domain/planner/planner.py</code></summary>

```python
"""Planner: turn a free-text request into known fields, and list what we cannot answer."""

from pathlib import Path
from typing import Literal

import duckdb
from pydantic import BaseModel, create_model

from docintel.core.llm import LLMResult, call_llm
from docintel.domain.schema.fields import ContractFields, Strict

FIELDS = tuple(ContractFields.model_fields)
FieldName = Literal[FIELDS]
PROMPT = Path(__file__).parent / "prompt.md"
PLAN_MAX_TOKENS = 4000  # hidden thinking counts; real planner calls used at most 654


class Plan(Strict):
    fields: list[FieldName]
    unknown: list[str]


class PlanError(ValueError):
    pass


def plan_messages(request: str) -> list[dict]:
    text = PROMPT.read_text(encoding="utf-8").replace("{request}", request)
    return [{"role": "user", "content": text}]


def plan_request(
    request: str,
    *,
    model: str | None = None,
    client=None,
    con: duckdb.DuckDBPyConnection | None = None,
    run_id: str | None = None,
) -> tuple[Plan, LLMResult | None]:
    """The fields a request asks for, in schema order. An empty request means all of them."""
    if not request.strip():
        return Plan(fields=list(FIELDS), unknown=[]), None
    result = call_llm(
        plan_messages(request),
        Plan,
        con=con,
        run_id=run_id,
        model=model,
        client=client,
        max_tokens=PLAN_MAX_TOKENS,
    )
    if result.parsed is None:
        raise PlanError(f"bad plan: {result.error}")
    chosen = set(result.parsed.fields)
    plan = Plan(fields=[f for f in FIELDS if f in chosen], unknown=result.parsed.unknown)
    return plan, result


def selected_model(fields: list[str]) -> type[BaseModel]:
    """A model with only these fields, each with its own sub-model from ContractFields."""
    chosen = {f: (ContractFields.model_fields[f].annotation, ...) for f in fields}
    return create_model("Requested", __base__=Strict, **chosen)


def pick(answer: ContractFields, fields: list[str]) -> BaseModel:
    """Keep only the requested fields of a full answer."""
    return selected_model(fields).model_validate(answer.model_dump(include=set(fields)))
```
</details>

## Break it on purpose

Both breaks are free. Put the code back after each one.

**Break 1: allow any name.** In `Plan`, change `fields: list[FieldName]` to `fields: list[str]`. Guess: which tests
fail?

<details><summary>What you see</summary>

```text
FAILED tests/test_planner.py::test_a_field_name_we_do_not_have_is_rejected
FAILED tests/test_planner.py::test_a_bad_plan_raises - Failed: DID NOT...
2 failed, 3 passed
```

Without the enum, `payment_terms` becomes a "field". 4a2 would then fail later, deep in the pipeline.
</details>

**Break 2: remove the empty-request rule.** Delete the two lines that start with `if not request.strip():`. Guess:
what happens in the test?

<details><summary>What you see</summary>

```text
openai.AuthenticationError: Error code: 401 - {'error': {'message': 'User not found.', 'code': 401}}
FAILED tests/test_planner.py::test_an_empty_request_means_all_fields_and_no_call
1 failed, 4 passed
```

The test tried a real call, with the fake test key. It failed for free, and it told you a call was made.
</details>

## Experiment

**1. Write and commit your eval set and your Step 2 decisions first.**

```sh
git add evals/planner_requests.json EXPERIMENTS.md
git commit -m "E4 eval set and planner rules, before the run"
```

**2. Run it** (paid, about $0.001; the worst case is shown first):

```sh
uv run python -m docintel.evals.planner_eval --budget 0.03
```

**run_id:** it prints as `e4-<date>-<time>`. The rows are in `plans` and in `llm_calls`.

The real output on the reference set:

```text
16 requests, worst case $0.0178, budget $0.03
Start? [y/N] y
ok   r01 'Who signed this contract?'                    ['parties'] unknown=[]
ok   r02 'parties, renewal term, any non-compete?'      ['parties', 'non_compete', 'renewal_term'] unknown=[]
...
ok   r12 'What are the payment terms?'                  [] unknown=['payment terms']
ok   r13 'Governing law, and can we terminate for conv' ['governing_law'] unknown=['termination for convenience']
ok   r14 'When was it signed and when does it expire?'  ['agreement_date'] unknown=['expiration date']
ok   r15 'Does it renew by itself, and for how long?'   ['renewal_term'] unknown=[]
ok   r16 'Is there an exclusivity clause or a non-comp' ['non_compete'] unknown=['exclusivity clause']
run e4-20261115-111022: exact 16/16, field P 1.00 R 1.00, unknown right 16/16, cost $0.0010
```

A perfect score on 16 easy requests says the set is easy. It does not say the planner is perfect. If yours is
perfect too, add three harder requests and run again.

**3. Fill in the entry in `EXPERIMENTS.md`:**

```markdown
## E4: the planner
- **Date:** <date>
- **run_id(s):** <e4-...>
- **Question / hypothesis:** Can one cheap LLM call map free-text requests to the 12 fields, and name what it cannot?
- **Data:** <n> hand-written requests in `evals/planner_requests.json`, written before the run.
- **Setup:** deepseek/deepseek-v4-flash on Parasail, prompt `domain/planner/prompt.md`, enum of 12 names,
  token limit 4,000. Empty request: <your rule>.
- **Decisions (Step 2):** <yours>.
- **Results:** exact <n>/<n>, field P and R, unknown right <n>/<n>, cost, largest output tokens. The misses, if any.
- **Limits:** a small set, written by the same person who wrote the prompt. The words of `unknown` change between runs.
- **Conclusion:** <keep the planner as it is, or what to change>.
- **Next step:** 4a2, the API.
```

## Gotchas

- **The `unknown` words change between runs.** r13 gave "terminate for convenience" in one run, and "termination for
  convenience" in the next. Never compare them as strings.
- **A perfect score is a warning.** Write harder requests before you trust it.
- **Close the notebook first.** The runner writes to DuckDB.
- **The prompt is now a second prompt to version.** If you change it, run E4 again.

## Explain back, then commit

Explain to Claude in a few sentences:

- `planner.py`: what `FieldName` does to the JSON schema, and what happens to `payment_terms`.
- Why an empty request makes no call.
- Why extraction still reads all 12 fields.
- `selected_model` and `pick`: what they build, and for whom.
- `planner_eval.py`: what "exact" means, and why "unknown" is yes or no.
- Your E4 result, and what you would add to the eval set.

Then:

```sh
git status
git add src/docintel/core/llm.py src/docintel/evals/parse_pilot.py src/docintel/domain/planner src/docintel/evals/planner_eval.py tests/test_planner.py EXPERIMENTS.md
git commit -m "phase 4a: planner and E4"
```

## Conclusion

A request is now a list of known fields, plus an honest list of what we cannot answer. Go back through the objectives
and check each one without notes. Then answer:

1. The model answers `{"fields": ["payment_terms"]}`. What stops it, and where?
2. Why is "extract all 12, return 3" safer than "extract 3", even though it costs a little more?

Looking for more challenges? Try these (optional):

1. Add five requests in another language. Does the planner still map them?
2. Run E4 twice, and count how often the `unknown` words change.

Checklist (`../PLAN.md`): **Structured outputs: Pydantic → JSON schema; enforcement vs validation** (the enum, and
`PlanError`). **Prompt versioning; context engineering** (a second prompt in a file). **Experiments: run_id, one
change at a time, cost, p50/p95** (E4). Next: 4a2.
