# Phase 1c4: compare open-weight models (E1.1)

In this part, you run E1 again with 2 or 3 newer open-weight models, and decide which model the
project keeps. You write no new code in `src/`: the runner from 1c2 and the report from 1c3 do
the work. You check licenses, estimate, run pilots, run the full split, and compare in one table.

This is part 4 of 4 for Phase 1c.

## Words used in this part

Read these first. 1c3 words (per field, micro, baseline) are used again.

- **Open weights**: the model files are public. Anyone can download and run the model. Example:
  Qwen3-235B on Hugging Face.
- **Hugging Face**: the main website for model files. Like npm, but for models.
- **License**: the rules for using the weights. `apache-2.0` and `mit` allow business use.
  `other` means a custom license that you must read.
- **API-only model**: you can call it, but its weights are not public. Not open weights.
- **Reasoning tokens**: some models "think" in hidden text before they answer. You pay for that
  text as output tokens.
- **Quantization**: storing a model's numbers with fewer bits, so it runs cheaper. Example: fp8,
  fp4. Fewer bits can mean a little less quality.
- **Trade-off**: you get more of one thing by giving up some of another. Example: a cheaper model
  that is a little worse.

## Objectives

By the end of this part you should be able to:

1. Check that a model really has open weights and a usable license.
2. Explain why a reasoning model can cost several times its estimate.
3. Run the same experiment with only the model changed.
4. Compare models on F1, cost and latency in one table, with `run_id`s.
5. Defend your choice of model with numbers.

## Dependencies

You install nothing new. This part needs:

- 1c2: the `run` command, with pilot runs and resume.
- 1c3: `report`, the E1 results, and the E1 entry in `EXPERIMENTS.md`.

Each full run costs cents. Reasoning models can cost several times their estimate, so every
model gets a pilot of 3 contracts first.

## The big picture

Before this part, the project uses one model, Qwen3-235B-2507, chosen in the plan before any
data.

After this part, the model is chosen on dev data:

- E1.1 has one run per model, all with the same split, parser, prompt and rules.
- One table compares them: precision, recall, F1, cost, output tokens, p50, p95, bad answers.
- `DOCINTEL_MODEL` in `.env` holds the model you keep. Every later part uses it.

2a, 2b and 3b then measure their changes on that model.

## Remember this

> To compare models, change only the model. Same split, prompt, parser and rules, so any change
> in the numbers comes from the model. Judge quality, cost and latency together, because the
> best F1 is not always the best choice for a product.
>
> **One change at a time. Quality, cost and latency together.**

## Why

**The model is the biggest cost and the easiest change.** Newer open-weight models came out
after Qwen3-235B-2507. Some are cheaper, some may be better at this task. Only a run on dev can
say which.

**"Open" must be checked.** This project uses open-weight models only. A model on OpenRouter can
be API-only, or have weights under a license that does not allow business use.

**A model choice is a product choice.** In Phase 4, a user waits for the answer. p95 latency
matters there as much as F1. Cost per contract decides the spend cap.

## Design decisions

- **Only the model changes.** Same prompt v1, same parser, same rules, same dev split. Other
  option: also tune the prompt for each model. Then you cannot tell what made the difference.
- **Each model runs with its defaults.** Reasoning on or off, and the provider, are what
  OpenRouter picks. Other option: set them per model. That is a second change. It can be E1.2.
- **The license check is a script, not a memory.** OpenRouter gives the Hugging Face id, and
  Hugging Face gives the license. Other option: trust the model name. Names like "Flash" do not
  say whether the weights are public.
- **The comparison is one SQL query over `runs`, `scores` and `llm_calls`.** Every model is one
  row, and every row has a `run_id`. Other option: copy numbers by hand. Easy to mix up.

## Worked example

Real data from OpenRouter and Hugging Face. Guess before you open each box.

### Round 1: a Hugging Face id is not enough

`qwen/qwen3.8-flash` on OpenRouter lists a Hugging Face id: `Qwen/Qwen3.8-Flash-Next`. Can this
project use it as an open-weight model?

<details><summary>Guess, then open</summary>

Not without reading more. The weights are on Hugging Face, but the license tag is
`license:other`: a custom license. It may have limits, for example on business use. You must
read it first. Apache 2.0 and MIT are well known and allow business use. Step 1 checks every model this way.
</details>

### Round 2: the estimate of a reasoning model

`estimate` says the full dev run with `qwen/qwen3.8-27b` costs about $0.096. Its listed output
price is $1.35 per million tokens. Why can the real cost be several times higher?

<details><summary>Guess, then open</summary>

`estimate` guesses 1,000 output tokens per contract. A reasoning model may write thousands of
hidden tokens before the JSON, and you pay for all of them as output. At $1.35 per million,
5,000 extra tokens on 52 contracts add about $0.35.

The pilot shows the real number: `completion_tokens` in `llm_calls`.
</details>

### Round 3: same F1, half the cost, twice the p95

Model B has the same F1 as model A, at half the cost, with twice the p95 latency. Which one
would you keep?

<details><summary>Guess, then open</summary>

It depends on what the product needs, so it is your decision (Step 5). For overnight batch jobs,
B. For the API in Phase 4, where a user waits, a p95 of two minutes may be too slow. Write down
the rule before you see the numbers, so the numbers cannot change the rule.
</details>

## Project setup

No new files. You run commands, and add cells to `notebooks/00_explore.ipynb`.

## Step 1: check open weights and licenses

**Why.** Only models with public weights and a usable license may enter the comparison.

Run this check (no key needed). It reads each model's Hugging Face id from OpenRouter, then the
license from Hugging Face:

```sh
$ uv run python - <<'EOF'
import json
import urllib.request

MODELS = ["qwen/qwen3-235b-a22b-2507", "qwen/qwen3.8-27b", "qwen/qwen3.8-flash",
          "qwen/qwen3.7-plus", "deepseek/deepseek-v4-flash", "z-ai/glm-5.3-flash"]
with urllib.request.urlopen("https://openrouter.ai/api/v1/models") as resp:
    info = {m["id"]: m for m in json.load(resp)["data"]}
for model in MODELS:
    m = info[model]
    hf = m.get("hugging_face_id") or None
    license = "no weights on Hugging Face"
    if hf:
        with urllib.request.urlopen(f"https://huggingface.co/api/models/{hf}") as resp:
            tags = json.load(resp)["tags"]
        license = next((t for t in tags if t.startswith("license:")), "license: ?")
    p = m["pricing"]
    print(f"{model:28} {float(p['prompt']) * 1e6:5.3f} {float(p['completion']) * 1e6:5.2f}  {license}")
EOF
qwen/qwen3-235b-a22b-2507    0.090  0.55  license:apache-2.0
qwen/qwen3.8-27b             0.040  1.35  license:apache-2.0
qwen/qwen3.8-flash           0.150  0.47  license:other
qwen/qwen3.7-plus            0.320  1.28  no weights on Hugging Face
deepseek/deepseek-v4-flash   0.091  0.18  license:mit
z-ai/glm-5.3-flash           0.017  0.14  license:mit
```

*Python here: [`m.get(...) or None`](./py/phase-1c4.md#py-1) ·
[`next(..., default)`](./py/phase-1c4.md#py-2) · [`* 1e6` and `:5.3f`](./py/phase-1c4.md#py-3) ·
`urlopen`: [1c PY-1](./py/phase-1c.md#py-1).*

Here, we:

1. Read OpenRouter's public model list once, and index it by model id.
2. For each model, take its Hugging Face id. No id means no public weights.
3. Ask Hugging Face for that model, and keep its first `license:` tag.
4. Print the price per million input and output tokens, then the license.

The output (real, today; prices change, so run it again on the day you decide):

1. Qwen3-235B-2507, our baseline: Apache 2.0.
2. Qwen3.8-27B: open, Apache 2.0. A small dense model with 27 billion parameters.
3. Qwen3.8-Flash: weights exist, but under a custom license (Round 1).
4. Qwen3.7-Plus: API only. Not open weights, so not for this project.
5. DeepSeek-V4-Flash and GLM-5.3-Flash: open, MIT. Both are cheap.

Add any other model you want to try to `MODELS`, and check it the same way.

## Step 2: choose the models (your decision)

**Why.** E1.1 asks one question: does a newer open-weight model do better, or the same for less?

First, estimate each candidate on the whole dev split:

```sh
$ uv run python -c "
from docintel.evals.runner import cuad_txt, docs_for, estimate
from docintel.evals.store import connect
with connect() as con:
    texts = [cuad_txt(con, d) for d in docs_for(con, 'dev')]
for m in ['qwen/qwen3-235b-a22b-2507', 'qwen/qwen3.8-27b', 'deepseek/deepseek-v4-flash', 'z-ai/glm-5.3-flash']:
    print(f'{m:28} {estimate(texts, m, \"v1\"):.3f}')"
qwen/qwen3-235b-a22b-2507    0.087
qwen/qwen3.8-27b             0.096
deepseek/deepseek-v4-flash   0.068
z-ai/glm-5.3-flash           0.018
```

These are too low for reasoning models (Round 2). The pilots in Step 3 show the real cost.

Decide, and write it in the notebook before any run:

1. **Which 2 or 3 models?** Only models with open weights and a license you accept.
2. **What counts as "better"?** F1 for all fields? A field that matters most to a lawyer? Cost
   per contract? p95 latency, because the API in Phase 4 makes a user wait?
3. **Your keep rule.** Write it as a sentence you can check against the table, like "keep X
   if ...".

<details><summary>Reference choice (open after you decide)</summary>

1. Qwen3.8-27B (newest Qwen open model, small), DeepSeek-V4-Flash (a different family, cheap
   output), and GLM-5.3-Flash (the cheapest). Three different families tell you more than
   three sizes of one family.
2. F1 for all fields first, then the weakest E1 fields. A model that fixes one of them is
   interesting even at the same F1.
3. Keep a new model only if its "all" F1 is at least E1's minus 0.02, and it is cheaper or
   faster at p95. Ties keep the baseline: fewer changes.
</details>

## Step 3: a pilot for each model

**Why.** A reasoning model can cost much more than its estimate, or fail the schema. Three
contracts show it for less than a cent.

For each model you chose, run:

```sh
$ uv run python -m docintel.evals.runner run --split dev --parser cuad_txt --model qwen/qwen3.8-27b --prompt-version v1 --limit 3
```

Then look at its calls in the notebook:

```python
con.sql("""
SELECT model, provider, ok, completion_tokens, round(cost_usd, 5) AS cost_usd,
    round(latency_ms / 1000, 1) AS seconds
FROM llm_calls WHERE run_id = $run
""", params={"run": "<pilot run_id>"})
```

<!-- LIVE OUTPUT: pilot calls for each new model -->

Expect 3 rows. Read them in this order:

1. `ok` false: the answer failed your schema. Read `error` in `llm_calls` before you go on.
2. `completion_tokens` much more than about 700: the model is reasoning. Multiply the pilot's
   total cost by 52 / 3 for a better estimate of the full run.
3. `provider`: which company ran the model. Different providers can mean different prices and
   quantization.

If a full run would cost more than you want, drop that model now. Note why in the notebook.

## Step 4: the full runs and the comparison

**Why.** Only the full dev split gives numbers you can compare with E1.

Run each model you kept on the whole dev split, the same command without `--limit`. Use
`--resume` if one stops. Then compare all runs in one table. Put your E1 and E1.1 `run_id`s in
`RUNS` (full runs only, no pilots):

```python
RUNS = ["<E1 run_id>", "<run_id 2>", "<run_id 3>", "<run_id 4>"]
con.sql("""
WITH s AS (
    SELECT run_id, sum(tp) AS tp, sum(fp) AS fp, sum(fn) AS fn FROM scores GROUP BY run_id
), c AS (
    SELECT run_id, sum(cost_usd) AS cost, avg(completion_tokens) AS out_tokens,
        quantile_cont(latency_ms, 0.5) / 1000 AS p50, quantile_cont(latency_ms, 0.95) / 1000 AS p95,
        count(*) FILTER (WHERE NOT ok) AS bad
    FROM llm_calls GROUP BY run_id
)
SELECT r.model, round(tp / (tp + fp), 2) AS p, round(tp / (tp + fn), 2) AS r,
    round(2 * tp / (2 * tp + fp + fn), 2) AS f1, round(cost, 3) AS cost_usd,
    round(out_tokens) AS out_tok, round(p50, 1) AS p50_s, round(p95, 1) AS p95_s, bad
FROM runs r JOIN s USING (run_id) JOIN c USING (run_id)
WHERE list_contains($runs, run_id)
ORDER BY f1 DESC
""", params={"runs": RUNS})
```

*SQL here: CTEs and `JOIN USING` are in [0c PY-5](./py/phase-0c.md#py-5) and
[0c PY-6](./py/phase-0c.md#py-6) · [`list_contains` and a list parameter](./py/phase-1c4.md#py-4).*

Here, we:

1. In `s`, add up TP, FP and FN per run.
2. In `c`, compute per run: total cost, average output tokens, p50, p95 and bad answers.
3. Join both to `runs`, so each row shows its model. Compute micro P, R and F1 from the counts,
   the same way `metrics` does for "all".
4. Keep only the runs in `RUNS`, best F1 first.

<!-- LIVE OUTPUT: E1.1 comparison table -->

Expect one row per model and 9 columns: model, p, r, f1, cost_usd, out_tok, p50_s, p95_s, bad.
Check that the E1 row has the same F1 as the "all" row of `report <E1 run_id>`.

Then run `report` for the best new model, and compare its per-field rows with E1's. Which of
E1's weakest fields got better, and which got worse?

## Step 5: keep a model (your decision)

**Why.** Every later part uses one model. Choose it with the rule you wrote in Step 2.

Apply your rule to the table, and write the result in one sentence with numbers. Example shape:
"Keep `<model>`: F1 `<x>` against E1 `<y>`, at `<z>` times the cost and p95 `<s>` s."

<details><summary>Reference choice (open after you decide)</summary>

Apply the Step 2 rule exactly as written. If no model passes it, keep
`qwen/qwen3-235b-a22b-2507` and say so: "no new model beat the baseline" is a real result. If
two models pass, keep the cheaper one. Also note in E1.1 if one provider served most calls of a
model, because another provider may give other numbers.
</details>

If the model you keep is not the baseline, set it in `.env` and `.env.example`:

```
DOCINTEL_MODEL=<the model you keep>
```

Checkpoint. Guess first: which model does the runner use now, without `--model`?

```sh
$ uv run python -c "
from docintel.core.config import get_settings
print(get_settings().docintel_model)"
```

It prints the model you set. With no change, it prints `qwen/qwen3-235b-a22b-2507`.

There is no test file in this part: it adds no code to `src/`. The numbers come from `metrics`
and `score`, which the 1c and 1c3 tests protect.

## Break it on purpose

Both breaks are about the method, not the code. Think first, then open.

**Break 1: a pilot in the table.** You put a pilot `run_id` (3 contracts) in `RUNS`. What goes
wrong?

<details><summary>Guess, then open</summary>

Its F1 comes from 3 contracts, so one answer moves it a lot. Its cost is for 3 contracts, so it
looks 17 times cheaper than the others. The row looks like a great model, and it means nothing.
Compare full runs only. The `n_docs` column in `runs` tells you which is which.
</details>

**Break 2: two changes at once.** You run the new model with a new prompt v2 too, and F1 goes up
by 0.05. What can you say?

<details><summary>Guess, then open</summary>

Only that "model plus prompt" is better. Maybe the prompt did all of it, and the new model is
worse. You would need a third run, the new model with prompt v1, to know. That is why E1.1
changes only the model.
</details>

## Experiment

This is E1.1. For each chosen model, the pilot and then the full run:

```sh
$ uv run python -m docintel.evals.runner run --split dev --parser cuad_txt --model <model> --prompt-version v1
```

Each run prints its own `run_id`. The table in Step 4 has one row per model. Dev only: never run
`--split test` to choose a model.

Write the E1.1 entry in `EXPERIMENTS.md`:

```markdown
## E1.1: newer open-weight models, same setup
- **Date:**
- **run_id(s):** <one per model, plus E1>
- **Question / hypothesis:** Does a newer open-weight model beat Qwen3-235B-2507 on the same
  prompt, or match it for less cost or latency?
- **Data:** dev, 52 contracts, 12 fields, CUAD .txt
- **Setup:** same as E1; only the model changes. Models and licenses: <list>. Each model with its
  default reasoning and OpenRouter's provider choice. Keep rule: <your Step 2 rule>.
- **Results:** the comparison table, plus the weakest fields of the best new model.
- **Conclusion:** the model kept, and why, in one sentence with numbers.
- **Next step:** 2a, validators and citations, on the kept model.
```

## Gotchas

- **The provider changes too.** OpenRouter may send each call to another provider, with another
  price and another quantization (fp8, fp4). `provider` in `llm_calls` shows it.
- **Reasoning models are slow and wordy.** High `out_tok` means high cost and high p95. That is
  part of the result, not a bug.
- **A model fails the schema often.** Many `bad` answers count as "nothing found" (your 1c
  rule), so its recall drops. 2b's retries may fix that, but compare models as they are now.
- **Prices and models change.** Write the date in E1.1. A run next month may cost a little
  more or less.
- **A `KeyError` before the run.** The model id is wrong (1c Break 2). Copy it from Step 1.

## Explain back, then commit

Explain to Claude in a few sentences (the rule in `PLAN.md`): how you checked open weights, your
keep rule, the comparison table, and why you kept the model you kept. Then:

```sh
$ git status
$ git add notebooks/00_explore.ipynb EXPERIMENTS.md .env.example
$ git commit -m "phase 1c4: E1.1 open-weight model comparison"
```

`.env` holds your key, so it is never committed. Only `.env.example` carries the model name.

## Conclusion

What you have now:

- A license check for any model, with real output.
- E1.1: 3 or 4 open-weight models on the same setup, one row each, all with `run_id`s.
- The model the project keeps, chosen on dev with a rule you wrote first.

Go back to the objectives. Check that you can do each one without notes. Then answer:

1. Why does each model get a pilot, when `estimate` already gives a cost?
2. Model B has the same F1 as model A, at half the cost and twice the p95. Which do you keep for
   the API in Phase 4, and why?

Want more practice? Try these (optional):

1. Run the best new model with reasoning turned low (`"reasoning": {"effort": "low"}` in
   `extra_body`). That is a second change: log it as E1.2.
2. Add a "cost per 1,000 contracts" column to the comparison table.
3. Rerun the baseline once more. How much do its numbers move with no change at all?

Checklist (`../PLAN.md`): **Experiments: run_id, one change at a time, cost, p50/p95** (done:
E1.1 changes only the model). **Open vs frontier: cost per 1k calls, quality, p95** (started:
open models compared on cost, quality and p95; frontier models come in P2).
