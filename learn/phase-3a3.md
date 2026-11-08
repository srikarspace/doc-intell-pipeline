# Phase 3a3: the vision parser, cost first

In this part, you build the third parser. It sends a picture of each page to a vision LLM. This parser
costs money, so you add a limit on every call and a budget before you add anything else.

This is part 3 of 3 for Phase 3a. It needs 3a. 3a2 is not needed for the code here, but the pilot compares
against it if you ran it.

## Words used in this part

Read these first. Parser, cache and latency are from 3a.

- **Vision LLM**: an LLM that can read images. Example: you send a photo of a page, and it writes the text.
- **DPI**: dots per inch, how sharp a page image is. Example: 150 DPI makes a letter page 1275 pixels wide.
- **Data URL**: a whole file written as text inside a string. Example: `data:image/png;base64,iVBOR...`.
- **Token limit (`max_tokens`)**: the most tokens the model may write in one answer.
- **Hidden thinking**: text the model writes for itself before the answer. You do not see it, but you pay
  for it as output tokens.
- **Runaway call**: a call that keeps writing until it hits a limit, and bills all of it.
- **Budget**: the most money one run may spend. The code stops before it can pass this amount.
- **Provider price**: the price of one company that hosts the model. It can differ from the listed price.

## Objectives

By the end of this part you should be able to:

1. Explain why a vision call can cost far more than its visible answer.
2. Add a token limit, and a budget check that runs before each call.
3. Estimate a paid run from the provider's real price.
4. Explain why the parser refuses a long document and does not cut it.
5. Run a pilot of two models, and choose one with a rule you wrote first.

## Dependencies

New library:

- `pypdfium2`: draws a PDF page as an image. Docling already brings it, but we use it directly, so we list it.

This part needs:

- 3a: `ParsedDoc`, `from_pages`, `cached_parse`, `PARSERS`.
- 1a2: `call_llm`. You add one optional argument to it.
- An OpenRouter key in `.env` (`sk-or-v1-...`), for the Experiment only.

Steps 1 to 8 make **no paid calls**. Only the Experiment costs money, and you start it yourself.

## The big picture

Before this part, the parsers could read a text layer (pypdf) or use local models (Docling).

After this part:

```text
page images -> vision LLM, one page at a time -> ParsedDoc
                 |
    token limit on each call + budget before each call
```

- **Extraction does not change.** It stays on DeepSeek V4 Flash, which is text only and cannot read images.
- **3b** runs the model you keep through the pipeline, on clean PDFs and on fake scans.
- **Phase 4** can use this parser when a user uploads a scan, so the limits matter in production too.

## Remember this

> A paid call has no natural end. The model can keep writing, and you pay for every token, also when the call
> fails. So money is protected in two places: a token limit makes the worst cost of one call known, and a budget
> check before each call stops the run before it can pass the limit.
>
> **Know the worst case before you press send.**

## Why

**This really happened.** While the docs for this part were being prepared, one call wrote 131,072 tokens of
empty space. It cost $0.46, and it was on a run with a $0.10 limit. The limit was only checked between
documents, and no token limit was set. Round 3 shows the real row.

**Vision is the only parser that costs per page.** A pilot can be cheap or not, depending on the model. You
estimate first, with the real price.

**We need evidence on real contracts.** No test score we found compares these two models on this kind of page.
A small pilot on your own data is the real check.

## Design decisions

- **One call per page.** A page failure is then one page. It also makes the worst cost easy to compute. Other
  option: send all pages in one call. A long answer is harder to limit, and one failure loses all.
- **The answer uses a small schema, `PageText`, through `call_llm`.** You get retries, the Parasail pin, cost
  and the `llm_calls` log with no new code. Other option: a new plain-text client. That is more code to test.
- **`max_tokens` is optional in `call_llm`.** Extraction does not send it, so its numbers cannot change. Other
  option: a limit on all calls. That would change E1 to E2 behaviour.
- **The budget checks the worst case of the next page.** Other option: check only what was spent. The check
  would pass, and then one more call could still go past the limit.
- **A failed call still counts as spent.** It was billed. Other option: count only good pages, which hides the
  most expensive event.
- **A long document is refused, not cut.** A cut document would lose answers on later pages. 3b would then count
  misses that are not the model's fault. Other option: parse the first 20 pages and say nothing.
- **A bad answer raises an error.** So it never reaches the cache. Other option: store `""` for that page. The
  cache would then hide the failure forever.
- **Each model has its own parser name.** The cache key is `(parser, doc_id)`, so two models cannot mix text.
  Other option: one name and a model setting. Changing the setting would return the old model's text.
- **The estimate uses the provider's price.** Round 2 shows why. Other option: `price()` from `runner.py`. It
  gives the listed price, and that is not what Parasail charges.

## Worked example

These are the real logged rows, from 5 calls on 3 dev pages. Three pages is very little evidence. Guess before you
open each box.

| Model | Page | Tokens in | Tokens out | Cost | Time |
|---|---|---|---|---|---|
| DeepSeek V4.1 Flash | Springbank p1 | 1,142 | 2,352 | $0.0032 | 10.3 s |
| DeepSeek V4.1 Flash | Pacific p1 | 1,142 | 2,252 | $0.0030 | 9.2 s |
| DeepSeek V4.1 Flash | Pacific p2 (blank) | 1,142 | 19 | $0.0004 | 0.7 s |
| Kimi K2.6 | Springbank p1 | 2,900 | 4,928 | $0.0194 | 33.9 s |
| Kimi K2.6 | Pacific p1 | 2,900 | 131,072 | $0.4609 | 489 s |

### Round 1: where do the tokens go?

The DeepSeek answer for Springbank p1 is 1,663 characters. That is about 400 tokens. The row says 2,352 tokens
out. Where are the others?

<details><summary>Guess, then open</summary>

Hidden thinking. About 80% of the output tokens are text the model wrote for itself, and you pay for all of it.
For Kimi on the same page, it is 4,928 tokens for a 1,614-character answer. So you cannot estimate cost from the
length of the page text. You need a real row, and that is why `PAGE_TOKENS` in Step 6 holds real numbers.
</details>

### Round 2: which price?

OpenRouter lists a price for each model. `price()` from `runner.py` reads it. For DeepSeek V4.1 Flash 1017, it says
$0.006 per million tokens in, and $0.50 out. Guess the cost of Springbank p1 at the listed price. Then compare it
with the $0.0032 in the row.

<details><summary>Guess, then open</summary>

The listed price gives about $0.0012, so it is wrong by more than 2 times. The list shows the cheapest company, and
we pin Parasail. Parasail charges $0.30 and $1.20. With those: 1,142 x 0.30/M + 2,352 x 1.20/M = $0.0032, an exact
match with the row. Always estimate with the provider you really use.
</details>

### Round 3: the expensive failure

Look at the last row. It is a normal page of text. The call failed, and the answer was 449,741 characters, nearly
all spaces and new lines. Guess: how much of the $0.46 is billed if the answer is useless?

<details><summary>Guess, then open</summary>

All of it. The model wrote until it reached 131,072 tokens. Pydantic then rejected the text, but the tokens were
already paid for. With a limit of 12,000 tokens, the worst Kimi page costs about $0.044, more than 10 times less.
The same model read Springbank p1 correctly. So a model can be good on one page, and run away on the next.
</details>

## Project setup

```sh
uv add pypdfium2
touch src/docintel/domain/parse/vision.py
touch src/docintel/evals/parse_pilot.py
touch tests/test_vision_parser.py
```

You should now have:

```text
src/docintel/
├── domain/parse/
│   └── vision.py        # new
└── evals/
    └── parse_pilot.py   # new
tests/
└── test_vision_parser.py    # new
```

## Step 1: a token limit in `call_llm`

**Why.** Without this, Round 3 can happen again. It comes before any vision code.

Update `_send` in `src/docintel/core/llm.py`. The new parts are the argument, the `limit` line and `**limit`:

```python
def _send(client, messages, schema, model, max_attempts, backoff_s, max_tokens=None):
    """One request, tried again only on RETRYABLE errors. Returns (response, attempts)."""
    limit = {"max_tokens": max_tokens} if max_tokens else {}
    for attempt in range(1, max_attempts + 1):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                response_format=response_format(schema),
                extra_body={"provider": provider_prefs()},
                temperature=0,
                **limit,
            )
```

Then, in `call_llm`, add one argument after `backoff_s`:

```python
    backoff_s: float = 1.0,
    max_tokens: int | None = None,
) -> LLMResult[T]:
```

And pass it on, in the same function:

```python
    resp, attempts = _send(
        client, messages, schema, model, s.llm_max_attempts, backoff_s, max_tokens
    )
```

*Python here: [`**limit`](./py/phase-3a3.md#py-1).*

Here, we send `max_tokens` only when a caller asks for it. Without the argument, the request is the same as before,
so extraction does not change.

Checkpoint:

```sh
uv run pytest tests/test_llm.py -q
```

```text
4 passed in 0.46s
```

## Step 2: the choices for a vision call (your decision)

**Why.** These four numbers and words decide the quality and the cost of every page.

You decide four things. Write them in `EXPERIMENTS.md`, as part of the E3.0 entry.

**The prompt.** What to look at: the model must copy, not summarize. It must say what to do with a blank page, and
with a word it cannot read.

**DPI.** Real sizes for Pacific p1:

| DPI | Image size |
|---|---|
| 100 | 62 KB |
| 150 | 121 KB |
| 200 | 213 KB |

More DPI gives sharper letters and a bigger file. In the real rows, a 150 DPI page was 1,142 tokens in for DeepSeek
and 2,900 for Kimi, including the prompt.

**The page cap.** 34 of the 52 dev contracts have 20 pages or fewer (235 pages in total). The longest has 82.

**The token limit.** Real output rows: 2,352 and 4,928 tokens for normal pages. Kimi costs $3.50 per million output
tokens at Parasail, so each 1,000 tokens of limit adds $0.0035 to its worst page. A limit that is too low stops good
pages. A limit that is too high makes the worst case expensive.

<details><summary>Reference (open after you write yours)</summary>

- **Prompt:** the `PROMPT` in Step 3.
- **DPI 150:** a common choice for reading text, and small files. 3b can test others on scans.
- **Page cap 20:** it covers 34 contracts, enough to choose from.
- **Token limit 12,000:** more than twice the largest normal row, so good pages should pass. It is only a judgment
  from 5 rows. The pilot will show if it is too low.
</details>

The steps below use the reference values. Use your own.

## Step 3: page images and the budget

**Why.** The budget must exist before the first paid call is written.

Put this in `src/docintel/domain/parse/vision.py`:

```python
"""Parser 3: send a picture of each page to a vision LLM. Paid, per page."""

import base64
import io
import time
from pathlib import Path

import pypdfium2 as pdfium

from docintel.core.llm import call_llm
from docintel.domain.parse.base import ParsedDoc, Parser, from_pages
from docintel.domain.schema.fields import Strict
from docintel.evals.store import connect

MODELS = {
    "deepseek_vl": "deepseek/deepseek-v4.1-flash-1017",
    "kimi_vl": "moonshotai/kimi-k2.6",
}
MAX_PAGES = 20
DPI = 150
MAX_OUTPUT_TOKENS = 12_000  # hidden thinking counts; one call without a limit cost $0.46
PROMPT = (
    "Copy all the text on this page, exactly as written, in reading order. "
    "Do not fix mistakes. Do not add a summary or comments. "
    "If a word cannot be read, write [unclear]. If the page is blank, return an empty string."
)


class PageText(Strict):
    text: str


class TooManyPages(ValueError):
    pass


class BudgetExceeded(RuntimeError):
    pass


class Budget:
    """A spending limit shared by all calls of one run."""

    def __init__(self, limit_usd: float):
        self.limit_usd = limit_usd
        self.spent = 0.0

    def check(self, worst_case_usd: float) -> None:
        """Stop before a call that could pass the limit."""
        if self.spent + worst_case_usd > self.limit_usd:
            raise BudgetExceeded(
                f"spent ${self.spent:.4f}, next page could cost ${worst_case_usd:.4f}, "
                f"limit ${self.limit_usd:.2f}"
            )

    def add(self, cost_usd: float) -> None:
        self.spent += cost_usd
```

*Python here: [your own error types](./py/phase-3a3.md#py-2).*

Here, we:

1. List the two candidate models. The name on the left is also the parser name, and so part of the cache key.
2. Keep your Step 2 choices at the top of the file.
3. Build `Budget`: one object that all calls of a run share.

Add to the bottom of `src/docintel/domain/parse/vision.py`:

```python
def page_images(pdf_path: Path, dpi: int = DPI) -> list[str]:
    """One PNG data URL per page. Refuses a document over MAX_PAGES."""
    pdf = pdfium.PdfDocument(pdf_path)
    if len(pdf) > MAX_PAGES:
        raise TooManyPages(f"{len(pdf)} pages, the cap is {MAX_PAGES}")
    urls = []
    for page in pdf:
        buffer = io.BytesIO()
        page.render(scale=dpi / 72).to_pil().convert("L").save(buffer, format="PNG")
        encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
        urls.append(f"data:image/png;base64,{encoded}")
    return urls


def page_messages(image_url: str) -> list[dict]:
    content = [
        {"type": "text", "text": PROMPT},
        {"type": "image_url", "image_url": {"url": image_url}},
    ]
    return [{"role": "user", "content": content}]
```

*Python here: [an image in memory, then base64](./py/phase-3a3.md#py-3).*

Here, we:

1. Refuse a long document before any work is done.
2. Draw each page, turn it grey, and save it as PNG in memory. PNG keeps letter edges sharp.
3. Turn the bytes into a data URL. It is the form that the API accepts inside a message.
4. Build one user message, with the prompt and the image.

Checkpoint (free, no network):

```sh
uv run python - <<'EOF'
from pathlib import Path

from docintel.domain.parse.vision import page_images
from docintel.evals.store import connect

with connect() as con:
    (path,) = con.execute(
        "SELECT pdf_path FROM contracts WHERE doc_id LIKE 'PACIFICSYSTEMS%'"
    ).fetchone()
for dpi in (100, 150, 200):
    urls = page_images(Path(path), dpi=dpi)
    print(dpi, "DPI:", [round(len(u) * 3 / 4 / 1024) for u in urls], "KB", urls[0][:30])
EOF
```

```text
100 DPI: [62, 3] KB data:image/png;base64,iVBORw0K
150 DPI: [121, 6] KB data:image/png;base64,iVBORw0K
200 DPI: [213, 8] KB data:image/png;base64,iVBORw0K
```

Page 2 is the blank page from 3a, so its image is tiny.

## Step 4: the parser

**Why.** This joins the limit, the budget and the page calls into the same shape as the other parsers.

Add to the bottom of `src/docintel/domain/parse/vision.py`:

```python
def make_vision_parser(
    parser_name: str,
    run_id: str | None = None,
    client=None,
    budget: Budget | None = None,
    worst_page_usd: float = 0.0,
) -> Parser:
    """A parser for one model. `run_id` tags its rows in `llm_calls`."""
    budget = budget or Budget(float("inf"))

    def parse(pdf_path: Path) -> ParsedDoc:
        start = time.perf_counter()
        pages, cost = [], 0.0
        with connect() as con:
            for url in page_images(pdf_path):
                budget.check(worst_page_usd)
                result = call_llm(
                    page_messages(url),
                    PageText,
                    con=con,
                    run_id=run_id,
                    model=MODELS[parser_name],
                    client=client,
                    max_tokens=MAX_OUTPUT_TOKENS,
                )
                budget.add(result.cost_usd or 0.0)  # a failed call is still paid for
                if result.parsed is None:  # raise, so a bad page never reaches the cache
                    raise ValueError(f"{parser_name}: bad answer: {result.error}")
                pages.append(result.parsed.text)
                cost += result.cost_usd or 0.0
        latency_ms = round((time.perf_counter() - start) * 1000)
        return from_pages(pages, cost_usd=cost, latency_ms=latency_ms, parser_name=parser_name)

    return parse
```

*Python here: [a function that returns a function](./py/phase-1a2.md#py-7).*

Here, for each page, in order:

1. Check the budget. If the worst case could pass the limit, stop before any call.
2. Send the page, with the token limit.
3. Add the real cost to the budget, also when the answer is bad.
4. If the answer is bad, stop. Nothing reaches the cache.

`make_vision_parser` returns a function, so it fits the same `Parser` shape as `parse_pypdf`.

## Step 5: add it to the registry

**Why.** The promise from 3a: the rest of the code asks for a parser by name.

Update the imports at the top of `src/docintel/domain/parse/__init__.py`:

```python
from docintel.domain.parse.vision import MODELS, make_vision_parser
```

Then update `PARSERS` in the same file. If you skipped 3a2, leave out the `docling` line:

```python
PARSERS: dict[str, Parser] = {
    "pypdf": parse_pypdf,
    "docling": parse_docling,
    **{name: make_vision_parser(name) for name in MODELS},
}
```

Checkpoint:

```sh
uv run python - <<'EOF'
import sys

from docintel.domain.parse import PARSERS

print(list(PARSERS))
print("torch loaded:", "torch" in sys.modules)
EOF
```

```text
['pypdf', 'docling', 'deepseek_vl', 'kimi_vl']
torch loaded: False
```

## Step 6: cost first

**Why.** You see the cost before you can spend it.

<details><summary>Put the imports at the top of <code>src/docintel/evals/parse_pilot.py</code></summary>

```python
"""Pilot for 3a3: the parsers on the same few dev contracts, cost checked first."""

import argparse
import json
import urllib.request
from collections import Counter
from datetime import datetime
from pathlib import Path

from docintel.core.config import get_settings
from docintel.domain.parse import PARSERS
from docintel.domain.parse.base import ParsedDoc
from docintel.domain.parse.cache import cached_parse
from docintel.domain.parse.vision import (
    MAX_OUTPUT_TOKENS,
    MAX_PAGES,
    MODELS,
    Budget,
    BudgetExceeded,
    make_vision_parser,
)
from docintel.domain.validate.citations import quote_status, words
from docintel.evals.store import connect
```
</details>

Add below the imports in `src/docintel/evals/parse_pilot.py`:

```python
PAGE_TOKENS = {"deepseek_vl": (1142, 2352), "kimi_vl": (2900, 4928)}  # (in, out), real 3a3 rows


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


def page_costs(parser_name: str) -> tuple[float, float]:
    """(usual, worst) cost of one page, in USD."""
    in_price, out_price = provider_price(MODELS[parser_name])
    tokens_in, tokens_out = PAGE_TOKENS[parser_name]
    usual = tokens_in * in_price + tokens_out * out_price
    return usual, tokens_in * in_price + MAX_OUTPUT_TOKENS * out_price
```

Here, we:

1. Read the price of the provider we pinned. This needs no key, and it costs nothing.
2. Use the highest price if the provider has more than one endpoint, so the estimate is not too low.
3. Compute two costs per page: usual, from a real row, and worst, from the token limit.

## Step 7: which contracts (your decision), then the pilot

**Why.** The pilot must compare the models on the same pages, and fit your budget.

What to look at:

- Length matters for cost. Three bands of length give short and long contracts.
- 34 dev contracts fit the cap of 20 pages. Dev only, never test.
- Estimated with the real prices (you see this below):

| Option | Docs | Pages | DeepSeek usual | Kimi usual |
|---|---|---|---|---|
| `--per-band 1` | 3 | 25 | $0.08 | $0.49 |
| `--per-band 3` | 9 | 69 | $0.22 | $1.34 |

Write your rule for choosing docs and your budget in `EXPERIMENTS.md`. Then compare.

<details><summary>Reference (open after you write yours)</summary>

Add this to `src/docintel/evals/parse_pilot.py`:

```python
def pick_docs(con, per_band: int) -> list[tuple]:
    """`per_band` dev contracts from each third of the lengths, at most MAX_PAGES pages."""
    return con.execute(
        """
        WITH d AS (
            SELECT doc_id, pdf_path, txt_path, n_pages,
                   ntile(3) OVER (ORDER BY n_pages, doc_id) AS band
            FROM contracts JOIN splits USING (doc_id)
            WHERE split = 'dev' AND n_pages <= ?
        ), ranked AS (
            SELECT *, row_number() OVER (PARTITION BY band ORDER BY md5(doc_id)) AS r FROM d
        )
        SELECT doc_id, pdf_path, txt_path, n_pages FROM ranked WHERE r <= ? ORDER BY band, doc_id
        """,
        [MAX_PAGES, per_band],
    ).fetchall()
```

Here, `ntile(3)` makes three length bands. `md5(doc_id)` gives a fixed order that does not depend on the
contract's name or length, so the same docs come back every time.

Start with `--per-band 1` and `--budget 1.00`. It keeps the risk small, and 3 docs is enough to catch a bad model.
</details>

The rest of the file is reporting and the command line. It is boilerplate, so copy it.

<details><summary>Add to the bottom of <code>src/docintel/evals/parse_pilot.py</code></summary>

```python
def report_row(name: str, parsed: list[ParsedDoc], docs: list[tuple], spans: dict) -> str:
    n_pages = sum(len(d.pages) for d in parsed)
    txt = sum(len(Path(t).read_text(encoding="utf-8")) for _, _, t, _ in docs[: len(parsed)])
    status = Counter()
    for doc, (doc_id, *_) in zip(parsed, docs, strict=False):
        source = words(doc.text)
        status.update(quote_status(s, source) for s in spans[doc_id])
    found = status["same_words"] + status["gap"]
    cost = sum(d.cost_usd for d in parsed)
    secs = sum(d.latency_ms for d in parsed) / 1000 / max(n_pages, 1)
    ratio = sum(len(d.text) for d in parsed) / max(txt, 1)
    return (
        f"{name:12} {len(parsed):4} {n_pages:5} {ratio:6.3f} "
        f"{found:4}/{sum(status.values()):<4} ${cost:7.4f} {secs:7.2f}"
    )


def main() -> None:
    ap = argparse.ArgumentParser(prog="python -m docintel.evals.parse_pilot")
    ap.add_argument("--per-band", type=int, default=1)
    ap.add_argument("--budget", type=float, required=True, help="stop before passing this, in USD")
    ap.add_argument("--parsers", nargs="+", default=["pypdf", *MODELS], choices=list(PARSERS))
    ap.add_argument("--yes", action="store_true")
    args = ap.parse_args()

    with connect() as con:
        docs = pick_docs(con, args.per_band)
        spans = {
            d[0]: [
                s
                for (s,) in con.execute(
                    "SELECT span_text FROM labels WHERE doc_id = ? AND is_present "
                    "AND span_text IS NOT NULL",
                    [d[0]],
                ).fetchall()
            ]
            for d in docs
        }
    n_pages = sum(d[3] for d in docs)
    vision = [p for p in args.parsers if p in MODELS]
    costs = {p: page_costs(p) for p in vision}
    print(f"{len(docs)} docs, {n_pages} pages, budget ${args.budget:.2f}")
    for p, (usual, worst) in costs.items():
        print(f"{p}: usual ${usual * n_pages:.4f}, worst ${worst * n_pages:.4f}")
    if vision and not args.yes and input("Start? [y/N] ").strip().lower() != "y":
        return

    run_id = f"pilot-{datetime.now():%Y%m%d-%H%M%S}"
    budget = Budget(args.budget)
    results = {}
    try:
        for name in args.parsers:
            parser = PARSERS[name]
            if name in MODELS:
                parser = make_vision_parser(
                    name, run_id=run_id, budget=budget, worst_page_usd=costs[name][1]
                )
            results[name] = []
            for doc_id, path, _, _ in docs:
                results[name].append(cached_parse(name, doc_id, Path(path), parser))
    except BudgetExceeded as e:
        print("stopped:", e)
    print(f"run {run_id}, spent now ${budget.spent:.4f}")
    print("parser       docs pages  ratio    quotes     cost  s/page")
    for name, parsed in results.items():
        if parsed:
            print(report_row(name, parsed, docs, spans))


if __name__ == "__main__":
    main()
```
</details>

Checkpoint 1: the free parser only. It makes no paid call.

```sh
uv run python -m docintel.evals.parse_pilot --per-band 1 --budget 0 --parsers pypdf
```

```text
3 docs, 25 pages, budget $0.00
run pilot-20261108-080213, spent now $0.0000
parser       docs pages  ratio    quotes     cost  s/page
pypdf           3    25  0.997   56/58   $ 0.0000    0.01
```

Checkpoint 2: see the estimate. Type `n` at the question. It makes no paid call.

```sh
uv run python -m docintel.evals.parse_pilot --per-band 1 --budget 1.00
```

```text
3 docs, 25 pages, budget $1.00
deepseek_vl: usual $0.0791, worst $0.3686
kimi_vl: usual $0.4856, worst $1.1044
Start? [y/N] n
```

Checkpoint 3: a budget too small for one page. Guess first: how many calls does it make?

```sh
uv run python -m docintel.evals.parse_pilot --per-band 1 --budget 0.01 --yes
```

```text
3 docs, 25 pages, budget $0.01
deepseek_vl: usual $0.0791, worst $0.3686
kimi_vl: usual $0.4856, worst $1.1044
stopped: spent $0.0000, next page could cost $0.0147, limit $0.01
run pilot-20261108-080109, spent now $0.0000
parser       docs pages  ratio    quotes     cost  s/page
pypdf           3    25  0.997   56/58   $ 0.0000    0.01
```

No calls. The budget stopped the first page before it was sent. `pypdf` still appears, because it ran first.

Your `run_id` will differ.

## Step 8: a small test

**Why.** These rules protect your money, so they must never break without a warning.

The test names say what is protected: pages stay in order and the limit is sent, a bad answer is never cached, the
budget stops before the call, a failed call still counts, too many pages is refused, and extraction sends no limit.

<details><summary>Put this in <code>tests/test_vision_parser.py</code></summary>

```python
"""The vision parser with a fake OpenRouter: no network, no key, no cost."""

import json

import httpx2
import pytest
from openai import OpenAI
from pypdf import PdfWriter

from docintel.core.config import get_settings
from docintel.core.llm import call_llm
from docintel.domain.parse import vision
from docintel.domain.parse.cache import cached_parse
from docintel.domain.parse.vision import (
    MAX_OUTPUT_TOKENS,
    Budget,
    BudgetExceeded,
    PageText,
    TooManyPages,
    make_vision_parser,
    page_images,
)
from docintel.evals.store import connect


def reply(content: str, cost: float = 0.01) -> httpx2.Response:
    return httpx2.Response(
        200,
        json={
            "id": "gen-1",
            "object": "chat.completion",
            "created": 0,
            "model": "fake/vision",
            "provider": "FakeCloud",
            "choices": [
                {
                    "index": 0,
                    "finish_reason": "stop",
                    "message": {"role": "assistant", "content": content},
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "cost": cost},
        },
    )


def fake_client(*responses: httpx2.Response) -> tuple[OpenAI, list]:
    sent = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        sent.append(json.loads(request.content))
        return responses[len(sent) - 1]

    http = httpx2.Client(transport=httpx2.MockTransport(handler))
    client = OpenAI(
        api_key="sk-or-v1-test", base_url="https://fake.test/v1", max_retries=0, http_client=http
    )
    return client, sent


@pytest.fixture(autouse=True)
def setup(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-test")
    get_settings.cache_clear()
    monkeypatch.setattr(vision, "connect", lambda: connect(tmp_path / "test.duckdb"))
    monkeypatch.setattr(vision, "page_images", lambda path: ["data:a", "data:b"])
    yield
    get_settings.cache_clear()


def page(text: str) -> httpx2.Response:
    return reply(json.dumps({"text": text}))


def test_pages_stay_in_order_and_costs_add_up(tmp_path):
    client, sent = fake_client(page("one"), page(""))
    doc = make_vision_parser("deepseek_vl", client=client)(tmp_path / "x.pdf")
    assert doc.pages == ["one", ""]
    assert doc.cost_usd == pytest.approx(0.02)
    assert all(body["max_tokens"] == MAX_OUTPUT_TOKENS for body in sent)


def test_a_bad_answer_raises_and_is_not_cached(tmp_path):
    client, _ = fake_client(reply("   "))
    parser = make_vision_parser("deepseek_vl", client=client)
    with pytest.raises(ValueError, match="bad answer"):
        cached_parse("deepseek_vl", "doc-1", tmp_path / "x.pdf", parser, tmp_path / "cache")
    assert not (tmp_path / "cache").exists()


def test_the_budget_stops_before_the_call(tmp_path):
    client, sent = fake_client(page("one"), page("two"))
    budget = Budget(0.015)
    parser = make_vision_parser("deepseek_vl", client=client, budget=budget, worst_page_usd=0.01)
    with pytest.raises(BudgetExceeded):
        parser(tmp_path / "x.pdf")
    assert len(sent) == 1  # page 2 could pass the limit, so it was never sent
    assert budget.spent == pytest.approx(0.01)


def test_a_failed_call_still_counts_as_spent(tmp_path):
    client, _ = fake_client(reply("   ", cost=0.46))
    budget = Budget(1.0)
    with pytest.raises(ValueError):
        make_vision_parser("deepseek_vl", client=client, budget=budget)(tmp_path / "x.pdf")
    assert budget.spent == pytest.approx(0.46)


def test_too_many_pages_is_refused(tmp_path, monkeypatch):
    monkeypatch.undo()
    writer = PdfWriter()
    for _ in range(21):
        writer.add_blank_page(width=200, height=200)
    pdf = tmp_path / "long.pdf"
    writer.write(pdf)
    with pytest.raises(TooManyPages):
        page_images(pdf)


def test_other_calls_send_no_token_limit():
    client, sent = fake_client(page("x"))
    call_llm([{"role": "user", "content": "hi"}], PageText, client=client, backoff_s=0)
    assert "max_tokens" not in sent[0]
```
</details>

*Python here: [`monkeypatch.undo()`](./py/phase-3a3.md#py-4) · [the fake client](./py/phase-1a2.md#py-7).*

Here, we use a fake OpenRouter, as in 1a2. The 0.46 in the failed-call test is the real cost from Round 3.

Checkpoint:

```sh
uv run pytest tests/test_vision_parser.py -q
make lint
```

```text
......                                                                   [100%]
6 passed in 0.57s
```

Your project structure should now look like this:

```text
src/docintel/
├── core/llm.py              # call_llm has max_tokens
├── domain/parse/
│   ├── __init__.py          # PARSERS has 4 parsers
│   ├── base.py
│   ├── cache.py
│   ├── docling_parser.py
│   ├── pypdf_parser.py
│   └── vision.py            # Budget, page_images, make_vision_parser
└── evals/parse_pilot.py     # estimate, pick_docs, report
tests/
├── test_docling_parser.py
├── test_parse_cache.py
└── test_vision_parser.py
```

## Break it on purpose

Both breaks run only the fake client, so they cost nothing.

**Break 1: remove the token limit.** In `make_vision_parser`, delete the line `max_tokens=MAX_OUTPUT_TOKENS,`. Guess:
does a test notice?

```sh
uv run pytest tests/test_vision_parser.py -q
```

<details><summary>What you see</summary>

```text
FAILED tests/test_vision_parser.py::test_pages_stay_in_order_and_costs_add_up
1 failed, 5 passed
```

Good. If nothing noticed, the next runaway call would be found on your bill. Put the line back.
</details>

**Break 2: count only good pages.** Move the line `budget.add(...)` to just after `pages.append(...)`. Guess: which
test fails?

<details><summary>What you see</summary>

```text
FAILED tests/test_vision_parser.py::test_a_failed_call_still_counts_as_spent
1 failed, 5 passed
```

The most expensive call in Round 3 was a failed one. A budget that skips failures misses exactly that. Put the line
back.
</details>

## Experiment

This is the only paid step in this part. It was not run while writing this doc. Only the 5 rows in the Worked example
are real, so the table below is the shape.

**1. Write your keep rule first.** Write it in `EXPERIMENTS.md`, and commit it before the run, as in 2b3. You keep one
vision model for 3b.

<details><summary>Reference rule (open after you write yours)</summary>

Keep the cheaper model, unless the other one finds at least 2 more quotes. A model with any failed page is out, unless
both have one. Check the text of one page by eye for made-up words.
</details>

**2. Run it.**

```sh
uv run python -m docintel.evals.parse_pilot --per-band 1 --budget 1.00
```

**run_id:** it prints as `pilot-<date>-<time>`. It tags the rows in `llm_calls`.

The shape to expect (your numbers will differ):

```text
3 docs, 25 pages, budget $1.00
deepseek_vl: usual $0.0791, worst $0.3686
kimi_vl: usual $0.4856, worst $1.1044
Start? [y/N] y
run pilot-<date>-<time>, spent now $<spent>
parser       docs pages  ratio    quotes     cost  s/page
pypdf           3    25  0.997   56/58   $ 0.0000    0.01
deepseek_vl     3    25  <r>     <n>/58  $<c>        <s>
kimi_vl         3    25  <r>     <n>/58  $<c>        <s>
```

To add Docling to the table, add `--parsers pypdf docling deepseek_vl kimi_vl`.

If it stops with `stopped: ...` or a bad answer, read the message. Cached documents are not paid for again, so you can
run the same command after you decide what to do.

**3. See what each page really cost:**

```sh
uv run python - <<'EOF'
from docintel.evals.store import connect

with connect() as con:
    print(con.execute(
        "SELECT model, count(*), sum(completion_tokens), max(completion_tokens), sum(cost_usd), "
        "sum(CASE WHEN ok THEN 0 ELSE 1 END) FROM llm_calls "
        "WHERE run_id LIKE 'pilot-%' GROUP BY model"
    ).fetchall())
EOF
```

If `max(completion_tokens)` equals your limit, a page hit the limit. Look at it before you trust the result.

**4. Fill in the entry in `EXPERIMENTS.md`:**

```markdown
## E3.0: vision model pilot
- **Date:** <date>
- **run_id(s):** <pilot-...>
- **Question / hypothesis:** Which vision model reads our contract pages well enough for its cost?
- **Data:** dev, <n> contracts, <n> pages, PDFs with a text layer. No scans yet.
- **Setup:** deepseek/deepseek-v4.1-flash-1017 and moonshotai/kimi-k2.6 on Parasail. Prompt, DPI, page cap and token
  limit: <your Step 2 values>.
- **Keep rule (written before the run):** <your rule>.
- **Results:** the pilot table, cost per page, largest output tokens, failed pages.
- **Limits:** few pages, clean PDFs, one run each. It shows a trade-off, and it is not a strong claim.
- **Conclusion:** <model kept, against your rule>.
- **Next step:** 3b, fake scans and the full parser comparison.
```

Tune on dev only. The test split is for the final numbers.

## Gotchas

- **Close the notebook first.** The parser holds a DuckDB connection for a whole document.
- **A failed page loses that document's paid pages.** The cache saves whole documents. The next try pays for them again.
- **A long answer can stop at your limit.** The JSON is then cut, and the page fails. Check step 3 of the Experiment.
- **A timed-out call may still be billed.** The budget only counts what the API reports, so keep some room in it.
- **`run_id` is on `llm_calls` only.** A pilot is not a row in `runs`, because it scores no fields.

## Explain back, then commit

Explain to Claude in a few sentences:

- `llm.py`: what `**limit` sends, and why extraction does not change.
- `vision.py`: the order of the 4 steps per page, and why the budget check comes first.
- Why a document over the cap is refused.
- `parse_pilot.py`: usual cost, worst cost, and why the price comes from the provider.
- `test_vision_parser.py`: which money rule each test protects.
- Your keep rule, and your pilot result against it.

Commit your keep rule alone before the paid run:

```sh
git add EXPERIMENTS.md
git commit -m "E3.0 keep rule, before the pilot"
```

Then, after the run:

```sh
git status
git add pyproject.toml uv.lock src/docintel/core/llm.py src/docintel/domain/parse src/docintel/evals/parse_pilot.py tests/test_vision_parser.py EXPERIMENTS.md
git commit -m "phase 3a3: vision parser, budget, pilot E3.0"
```

## Conclusion

You now have three kinds of parser behind one interface, and paid calls with a known worst case. Go back through the
objectives and check each one without notes. Then answer:

1. Why does the budget check the worst case of the next page, and not just what was spent?
2. A model gets 2 more quotes and costs 6 times more. What would you do in 3b, and why?

Looking for more challenges? Try these (optional):

1. Store each page in the cache, so a failed page does not lose the others.
2. Send the same page at 100 DPI and at 200 DPI. Does the text change? (Check the cost first.)

Checklist (`../PLAN.md`): **Parsers: text layer vs layout vs multimodal; CER** (the multimodal part). **Experiments:
run_id, one change at a time, cost, p50/p95** (cost first, a budget, a rule written before the run).
