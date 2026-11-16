# Phase 4a3: highlights and a live stream

In this part, you give the UI the two things it needs from the video. First, where each quote is on the page, so a
click can highlight it. Second, a live stream of the real steps, so the user watches "Analyzing" move forward.

This is part 3 of 3 for Phase 4a. It needs 4a2. The paid checkpoint costs about $0.0007.

## Words used in this part

Read these first. Route and dependency are from 4a2.

- **Text layer**: the letters stored inside a PDF (3b). A scan has none.
- **Char box**: the small rectangle that one letter fills on the page. Example: `(318.9, 772.5, 324.1, 780.1)`.
- **PDF point**: the unit of a PDF page, 1/72 of an inch. A letter page is 612 by 792 points.
- **Bottom-left origin**: in a PDF, `y = 0` is the bottom of the page. On a screen, `y = 0` is the top.
- **Highlight**: the page number and the boxes that cover one quote, one box per line.
- **SSE (server-sent events)**: one HTTP response that stays open, and sends small text messages as things happen.
  Example: `event: stage` then `data: {"name": "parse"}`.
- **Callback**: a function you pass in, which the code calls when something happens. Example: `on_event("plan", ...)`.
- **Queue**: a line of items. One side puts items in, the other side takes them out, in order.

## Objectives

By the end of this part you should be able to:

1. Turn a quote into a page number and line boxes, from the PDF's text layer.
2. Explain why a raised quote mark can split a line, and how the code keeps it whole.
3. Report the pipeline's real steps through a callback, with no HTTP inside `domain/`.
4. Send those steps as SSE from a thread to the browser, with the same input checks as `/v1/extract`.
5. Say what the UI will do with a highlight, including the flip of the y axis.

## Dependencies

New library (checked on PyPI and OSV: maintained, 0 open advisories):

- `sse-starlette`: sends SSE from FastAPI. In Express, you would write `res.write("event: ...\n\n")` by hand.

This part needs:

- 4a2: `KNOWN_ERRORS`, `as_http`, `read_input`, `conftest.py`, the samples.
- 3a3: `pypdfium2`, already installed. 2a: the word rule of the citation check.

## The big picture

Before this part, the API answered once, at the end, with quotes as plain text.

After this part:

```text
POST /v1/extract/stream
   event: stage   {"name": "parse", "status": "start"}
   event: stage   {"name": "parse", "status": "done", "parser": "pypdf"}
   event: plan    {"fields": [...], "unknown": [...]}
   event: attempt {"n": 0, "errors": 0}
   event: result  {... "highlights": [{"page": 1, "rects": [[318.9, 772.5, 398.5, 780.1]]}] ...}
```

- **4c** turns the `stage` events into daisyUI `steps`, and reveals the rows when `result` arrives.
- **4c2** draws each highlight box over the PDF page, and scrolls to it when a row is clicked.
- **4b** adds a trace span around each of these same steps.

## Remember this

> A quote is useful in the UI only if it points at the page. The text layer knows where every letter is, so the same
> word rule as the citation check can find the quote, and its letter boxes become one box per line. The steps are
> reported through a plain callback, so the pipeline still knows nothing about HTTP.
>
> **Find the words, keep their boxes, report the steps.**

## Why

**A cited answer must be checkable in one click.** A lawyer does not want to search the PDF for a quote. The box shows
it at once.

**Waiting with no news feels broken.** An extraction takes 6 to 35 seconds. Real steps, shown as they happen, tell
the user that work is going on.

**The rows are revealed, not computed one by one.** Extraction is one call for 12 fields. The stream sends the real
steps, and the UI reveals the rows when the answer arrives. The doc says so, so the demo stays honest.

## Design decisions

- **Boxes come from pypdfium2's char boxes.** It is already installed, and it gives one box per letter. Other option:
  search in pdf.js in the browser. The browser would need its own copy of the word rule.
- **The same word rule as the citation check.** Lowercase words and numbers only. A quote that passes
  `quote_status` can be found here too. Other option: exact text search. One extra space would miss it.
- **One box per line.** A new line starts when the text goes back to the left, or stops overlapping from top to bottom.
  Other option: group by the bottom of each box. A raised quote mark then splits one line into three boxes.
- **Points with a bottom-left origin, plus the page size.** The UI can scale to any width, and flip y with one line.
  Other option: send pixels. They depend on the screen.
- **Scans get no boxes.** They have no text layer. The UI still shows the quote, and jumps to the page later if OCR
  boxes are added. Other option: OCR boxes now. That is a bigger change to the parsers.
- **`on_event` is a plain callback, default "do nothing".** The eval runner never sees it. Other option: pass the HTTP
  response into the pipeline. Then `domain/` would depend on the web.
- **A queue between the thread and the response.** The pipeline runs in a thread, the stream is `async`.
  `call_soon_threadsafe` is the safe way to hand an event over. Other option: put into the queue from the thread
  directly. `asyncio` objects are not thread-safe.
- **The stream reuses `KNOWN_ERRORS`, as an `error` event.** The status code of a stream is already 200 when an error
  happens, so the error goes inside it. Other option: close the stream with no reason.

## Worked example

All numbers are real. Guess before you open each box.

### Round 1: how many boxes for a short quote?

The quote is `Kubient, Inc. ("Kubient")`, on one line of page 1. The first version grouped letters by the bottom of
their boxes. Guess how many boxes it gave.

<details><summary>Guess, then open</summary>

```text
[(318.9, 772.5, 367.8, 780.1), (368.6, 777.5, 370.9, 779.9), (371.7, 774.2, 398.5, 780.1)]
```

Three. The `"` sits high on the line, so its box starts 5 points higher. The fix asks "is it to the right, and does it
overlap from top to bottom?". Then the answer is one box: `(318.9, 772.5, 398.5, 780.1)`.
</details>

### Round 2: will every quote get a box?

The 9 text samples hold 158 gold label quotes. Guess how many `locate` finds.

<details><summary>Guess, then open</summary>

```text
gold quotes with boxes: 156 of 158
```

156, the same count as pypdf in E3 (156/158), but **not the same quotes**:

- pypdf missed two dates in EcoScience, written "1st" with a small raised "st". pdfium reads them, so `locate` finds
  them.
- `locate` misses two quotes (iVillage, Variable Separate Account) that run across a page break. Their words match the
  whole document, but no single page. `locate` looks at one page at a time (see Gotchas).

Same count, different reasons. Always look at the misses, not only the number.
</details>

### Round 3: where does the box go on the screen?

A box is `(318.9, 772.5, 398.5, 780.1)` on a page of `(595, 842)` points. The UI shows the page 1,190 pixels wide.
Guess the top of the box on the screen, in pixels.

<details><summary>Guess, then open</summary>

The scale is 1190 / 595 = 2. A PDF counts y from the bottom, the screen from the top. So the top is
(842 - 780.1) * 2 = **123.8 px**, and the left is 318.9 * 2 = 637.8 px. 4c2 does exactly this.
</details>

## Project setup

```sh
uv add sse-starlette
touch src/docintel/domain/locate.py
touch tests/test_stream.py
```

You should now have:

```text
src/docintel/domain/
└── locate.py        # new: quote -> page and line boxes
tests/
└── test_stream.py   # new
```

## Step 1: find the quote's words on a page

**Why.** Everything else starts from "which letters are this quote?".

Put this in `src/docintel/domain/locate.py`:

```python
"""Where is a quote on the page? Line boxes from the text layer, so the UI can highlight it."""

import re
from pathlib import Path

import pypdfium2 as pdfium
from pydantic import BaseModel

WORD = re.compile(r"[a-z0-9]+")  # the same word rule as `citations.words`


Rect = tuple[float, float, float, float]  # x0, y0, x1, y1 in PDF points; (0, 0) is bottom left


class Highlight(BaseModel):
    quote_index: int
    page: int  # from 1
    page_size: tuple[float, float]
    rects: list[Rect]


def find_span(quote: list[str], words: list[str]) -> tuple[int, int] | None:
    """The first and last word index of `quote` inside `words`, side by side. None if absent."""
    n = len(quote)
    for start in range(len(words) - n + 1):
        if words[start : start + n] == quote:
            return start, start + n - 1
    return None
```

*Python here: [a type alias, and `tuple` in a model](./py/phase-4a3.md#py-1).*

Here, we:

1. Use the same word pattern as `citations.words`: lowercase letters and numbers.
2. Describe a highlight: which quote, which page, the page size, and the line boxes.
3. In `find_span`, slide along the page's words, and return the first and last word index of the quote.

## Step 2: letters to line boxes

**Why.** A quote can cover three lines. The UI needs one box per line, not one per letter.

Add to the bottom of `src/docintel/domain/locate.py`:

```python
def same_line(line: list[float], box: Rect) -> bool:
    """A box is on the current line if it is to the right and overlaps it from top to bottom."""
    x0, y0, _, y1 = box
    return x0 >= line[2] - 1 and y0 < line[3] and y1 > line[1]


def line_rects(boxes: list[Rect]) -> list[Rect]:
    """Join char boxes into one box per line, in reading order."""
    lines: list[list[float]] = []
    for box in boxes:
        if lines and same_line(lines[-1], box):
            line = lines[-1]
            line[1], line[2], line[3] = min(line[1], box[1]), box[2], max(line[3], box[3])
        else:
            lines.append(list(box))
    return [tuple(round(v, 1) for v in line) for line in lines]


def locate(pdf_path: Path, quotes: list[str]) -> list[Highlight]:
    """One Highlight per quote found in the text layer. A quote that is not found is skipped."""
    wanted = [(i, WORD.findall(q.lower())) for i, q in enumerate(quotes)]
    found = []
    pdf = pdfium.PdfDocument(pdf_path)
    for page_no, page in enumerate(pdf, start=1):
        text_page = page.get_textpage()
        text = text_page.get_text_range()
        spans = [(m.start(), m.end()) for m in WORD.finditer(text.lower())]
        words = [text[a:b].lower() for a, b in spans]
        for i, quote in wanted:
            span = find_span(quote, words) if quote else None
            if span is None:
                continue
            first, last = spans[span[0]][0], spans[span[1]][1]
            boxes = [text_page.get_charbox(k) for k in range(first, last) if not text[k].isspace()]
            found.append(
                Highlight(
                    quote_index=i, page=page_no, page_size=page.get_size(), rects=line_rects(boxes)
                )
            )
        wanted = [(i, q) for i, q in wanted if i not in {h.quote_index for h in found}]
    pdf.close()
    return sorted(found, key=lambda h: h.quote_index)
```

Here, in `locate`, for each page, in order:

1. Read the page text, and the start and end of every word in it.
2. For each quote not found yet, look for its words.
3. Take the char boxes from the first to the last letter, and skip spaces.
4. Join them into line boxes, and keep the page size.
5. Stop looking for a quote once it is found.

Checkpoint (free):

```sh
uv run python - <<'EOF'
from docintel.api.samples import sample_pdf
from docintel.domain.locate import locate

quotes = [
    'Kubient, Inc. ("Kubient")',
    "Customer agrees not to work with, directly or indirectly, any Third-Party",
    "this sentence is not in the contract",
]
for h in locate(sample_pdf("kubient"), quotes):
    print(h.quote_index, "page", h.page, h.page_size, h.rects)
print("scan:", locate(sample_pdf("kubient-scan"), quotes))
EOF
```

```text
0 page 1 (595.0, 842.0) [(318.9, 772.5, 398.5, 780.1)]
1 page 1 (595.0, 842.0) [(389.8, 610.9, 545.0, 618.5), (50.3, 600.8, 139.6, 608.4)]
scan: []
```

The second quote runs over two lines, so it has two boxes. The third is not in the contract, so it is skipped. The scan
has no text layer.

Checkpoint (free): every gold quote of the 9 text samples.

```sh
uv run python - <<'EOF'
from docintel.api.samples import load_samples, sample_pdf
from docintel.domain.locate import locate
from docintel.evals.store import connect

found = total = 0
with connect() as con:
    for s in load_samples().values():
        if s.scan:
            continue
        spans = [t for (t,) in con.execute(
            "SELECT span_text FROM labels WHERE doc_id = ? AND is_present AND span_text IS NOT NULL", [s.doc_id]
        ).fetchall()]
        found += len(locate(sample_pdf(s.id), spans))
        total += len(spans)
print("gold quotes with boxes:", found, "of", total)
EOF
```

```text
gold quotes with boxes: 156 of 158
```

## Step 3: report the steps, and add the boxes to the answer

**Why.** The UI needs to know what the pipeline is doing, and where each quote is.

In `src/docintel/domain/extract/retry.py`, add one argument to `extract_with_retry`, after `max_tokens`:

```python
    on_attempt=None,
```

And call it right after `attempts.append(attempt)`:

```python
        if on_attempt:
            on_attempt(attempt)
```

In `src/docintel/domain/pipeline.py`, update the imports:

```python
from collections.abc import Callable

from docintel.domain.locate import Highlight, locate
```

Add one field at the end of `FieldResult`:

```python
    highlights: list[Highlight] = []  # empty for a scan, or a quote not found in the text layer
```

Then add the callback type above `run_pipeline`, and replace `run_pipeline`:

```python
Emit = Callable[[str, dict], None]  # (event name, data); the API turns these into SSE events


def no_events(event: str, data: dict) -> None:
    pass


def run_pipeline(
    pdf_path: Path, request: str, document: Document, client=None, on_event: Emit = no_events
) -> ExtractResult:
    """Parse, plan, extract with retries, check, keep the asked fields. Reports each step."""
    start = time.perf_counter()
    on_event("stage", {"name": "parse", "status": "start"})
    doc = parse_pdf(pdf_path)
    on_event("stage", {"name": "parse", "status": "done", "parser": doc.parser_name})
    on_event("stage", {"name": "plan", "status": "start"})
    plan, plan_call = plan_request(request, client=client)
    on_event("plan", {"fields": plan.fields, "unknown": plan.unknown})
    if not plan.fields:
        raise NothingToExtract(f"no known field in the request; unknown: {plan.unknown}")
    on_event("stage", {"name": "extract", "status": "start"})
    attempts = extract_with_retry(
        doc.text,
        client=client,
        max_tokens=EXTRACT_MAX_TOKENS,
        on_attempt=lambda a: on_event("attempt", {"n": a.attempt_no, "errors": len(a.errors)}),
    )
    answer = final_answer(attempts)
    if answer is None:
        raise ValueError("the model gave no answer that fits the schema")
    on_event("stage", {"name": "check", "status": "start"})
    issues = check_answer(answer, doc.text)  # rule errors and review warnings
    picked = pick(answer, plan.fields)
    fields = {}
    for name in plan.fields:
        own = [i for i in issues if i.field == name]
        answer_part = getattr(picked, name).model_dump()
        boxes = locate(pdf_path, answer_part["quotes"]) if doc.parser_name == "pypdf" else []
        fields[name] = FieldResult(
            **answer_part, needs_review=bool(own), issues=own, highlights=boxes
        )
    costs = [a.result.cost_usd for a in attempts] + [plan_call.cost_usd if plan_call else 0.0]
    return ExtractResult(
        request_id=str(uuid.uuid4()),
        document=document,
        fields=fields,
        unknown=plan.unknown,
        needs_review=any(f.needs_review for f in fields.values()),
        parser=doc.parser_name,
        pages=len(doc.pages),
        cost_usd=sum(c or 0.0 for c in costs) + doc.cost_usd,
        latency_ms=round((time.perf_counter() - start) * 1000),
    )
```

*Python here: [`Callable`, and a lambda that calls a callback](./py/phase-4a3.md#py-2).*

Here, the new parts, in order:

1. Report `stage` events at the start and end of parsing, and at the start of plan, extract and check.
2. Report the `plan` as soon as it is known. The UI can draw the right number of rows.
3. Report each `attempt`, so a retry is visible.
4. For a text PDF, find the boxes of each quote of each returned field.

## Step 4: the stream route

**Why.** The browser needs the events while the work is running, not at the end.

In `src/docintel/api/routes.py`, update the imports:

```python
import json
import shutil

from sse_starlette import EventSourceResponse
```

Add to the bottom of `src/docintel/api/routes.py`:

```python
@router.post("/v1/extract/stream")
async def extract_stream(
    client: Annotated[object, Depends(get_llm_client)],
    pdf: UploadFile | None = None,
    sample_id: Annotated[str | None, Form()] = None,
    request: Annotated[str, Form()] = "",
) -> EventSourceResponse:
    """The same work as /v1/extract, sent as events while it runs: stage, plan, attempt, result."""
    if len(request) > MAX_REQUEST_CHARS:
        raise HTTPException(422, f"the request is over {MAX_REQUEST_CHARS} characters")
    data, document = await read_input(pdf, sample_id)
    folder = Path(tempfile.mkdtemp())
    path = folder / "upload.pdf"
    path.write_bytes(data)
    queue: asyncio.Queue = asyncio.Queue()
    loop = asyncio.get_running_loop()

    def emit(event: str, data: dict) -> None:  # runs in the pipeline's thread
        loop.call_soon_threadsafe(queue.put_nowait, (event, data))

    async def work() -> None:
        try:
            result = await asyncio.wait_for(
                run_in_threadpool(run_pipeline, path, request, document, client, emit),
                timeout=TIMEOUT_S,
            )
            await queue.put(("result", result.model_dump(mode="json")))
        except tuple(KNOWN_ERRORS) as e:
            error = as_http(e)
            await queue.put(("error", {"status": error.status_code, "detail": error.detail}))
        except Exception:  # a bug: say so, without the details
            await queue.put(("error", {"status": 500, "detail": "internal error"}))
        finally:
            await queue.put(None)  # the end

    async def events():
        task = asyncio.create_task(work())
        try:
            while (item := await queue.get()) is not None:
                name, payload = item
                yield {"event": name, "data": json.dumps(payload)}
        finally:
            await task
            shutil.rmtree(folder, ignore_errors=True)

    return EventSourceResponse(events())
```

*Python here: [a queue between a thread and `async`](./py/phase-4a3.md#py-3) · [an `async` generator](./py/phase-4a3.md#py-4).*

Here, in order:

1. Check the input, and save the PDF, as in `extract`.
2. `emit` hands each event from the pipeline's thread to the event loop, safely.
3. `work` runs the pipeline in a thread, with the time limit. At the end it adds `result`, or one `error` event with the
   status code from `KNOWN_ERRORS`, then `None` to say "the end".
4. `events` takes items from the queue, in order, and sends each one as SSE. After the end, it waits for `work`, and
   deletes the temporary folder.

Checkpoint (paid, about $0.0007). Start the server with `make serve`. `-N` tells curl to print events as they come:

```sh
curl -s -N -F sample_id=kubient -F request="parties, renewal term, any non-compete?" localhost:8000/v1/extract/stream
```

```text
event: stage
data: {"name": "parse", "status": "start"}

event: stage
data: {"name": "parse", "status": "done", "parser": "pypdf"}

event: stage
data: {"name": "plan", "status": "start"}

event: plan
data: {"fields": ["parties", "non_compete", "renewal_term"], "unknown": []}

event: stage
data: {"name": "extract", "status": "start"}

event: attempt
data: {"n": 0, "errors": 0}

event: stage
data: {"name": "check", "status": "start"}

event: result
data: {"request_id": "...", ...}
```

The `result` line is long. Its fields, in short:

```text
parties found  [{"quote_index": 0, "page": 1, "page_size": [595.0, 842.0], "rects": [[318.9, 772.5, 398.5, 780.1]]}, {"quote_index": 1, "page": 1, "page_size": [595.0, 842.0], "rects": [[423.7, 772.5, 536.6, 780.1]]}]
non_compete not found  []
renewal_term not found review []
cost 0.0006788600000000001 ms 13927 parser pypdf
```

Watch the terminal while it runs: the `extract` stage waits a few seconds, then the rest comes at once.

## Step 5: a small test

**Why.** Wrong boxes or a stream in the wrong order would break the UI with no error on the server.

First, add one line to the `api` fixture in `tests/conftest.py`, after the `parse_pdf` line. The fake PDF of the tests has
no pages, so `locate` must not open it:

```python
    monkeypatch.setattr(pipeline, "locate", lambda path, quotes: [])  # the fake PDF has no pages
```

The test names say what is protected: a quote is one box on its line, a two-line quote has two boxes, a missing quote
and a scan give nothing, the events come in order and end with the result, and a failure ends with an error event.

<details><summary>Put this in <code>tests/test_stream.py</code></summary>

```python
"""Highlights on a real sample PDF, and the event stream with the fakes from `conftest.py`."""

import json
from pathlib import Path

from docintel.api.samples import SAMPLES_DIR
from docintel.domain.locate import locate

KUBIENT = SAMPLES_DIR / "kubient.pdf"
QUOTE = 'Kubient, Inc. ("Kubient")'
PLAN = {"fields": ["parties"], "unknown": []}


def events(client, request: str) -> list[tuple[str, dict]]:
    """Send a stream request, and read back (event, data) pairs."""
    data = {"sample_id": "kubient", "request": request}
    with client.stream("POST", "/v1/extract/stream", data=data) as response:
        text = "".join(response.iter_text())
    pairs = []
    for block in text.replace("\r\n", "\n").split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.splitlines() if ": " in line)
        if "event" in lines:
            pairs.append((lines["event"], json.loads(lines["data"])))
    return pairs


def test_a_quote_becomes_one_box_on_its_line():
    (h,) = locate(KUBIENT, [QUOTE])
    assert (h.quote_index, h.page, h.page_size) == (0, 1, (595.0, 842.0))
    assert len(h.rects) == 1  # the raised quote marks stay on the same line


def test_a_quote_on_two_lines_gets_two_boxes():
    quote = "Customer agrees not to work with, directly or indirectly, any Third-Party"
    (h,) = locate(KUBIENT, [quote])
    assert len(h.rects) == 2


def test_a_quote_that_is_not_there_gives_nothing():
    assert locate(KUBIENT, ["this sentence is not in the contract"]) == []
    assert locate(SAMPLES_DIR / "kubient-scan.pdf", [QUOTE]) == []  # a scan has no text layer


def test_events_come_in_order_and_end_with_the_result(api):
    names = [name for name, _ in events(api(PLAN), "parties")]
    assert names == [
        "stage",
        "stage",
        "stage",
        "plan",
        "stage",
        "attempt",
        "stage",
        "result",
    ]


def test_a_failure_ends_with_an_error_event(api):
    pairs = events(api({"fields": [], "unknown": ["payment terms"]}), "payment terms")
    assert pairs[-1] == ("error", {"status": 422, "detail": pairs[-1][1]["detail"]})
    assert api.sent == ["Plan"]
    assert Path(KUBIENT).exists()  # the sample is read, never moved or deleted
```
</details>

The box tests use a real sample PDF from `src/docintel/api/samples/`. It is part of the repo, so the test still needs
no network.

Checkpoint:

```sh
uv run pytest tests/test_stream.py -q
make test
make lint
```

```text
.....                                                                    [100%]
5 passed in 0.10s
```

Your project structure should now look like this:

```text
src/docintel/
├── api/routes.py            # + /v1/extract/stream
└── domain/
    ├── extract/retry.py     # + on_attempt
    ├── locate.py            # Highlight, find_span, line_rects, locate
    └── pipeline.py          # on_event, highlights in FieldResult
tests/
├── conftest.py              # + locate is faked
└── test_stream.py
```

<details><summary>Complete <code>src/docintel/domain/locate.py</code></summary>

```python
"""Where is a quote on the page? Line boxes from the text layer, so the UI can highlight it."""

import re
from pathlib import Path

import pypdfium2 as pdfium
from pydantic import BaseModel

WORD = re.compile(r"[a-z0-9]+")  # the same word rule as `citations.words`

Rect = tuple[float, float, float, float]  # x0, y0, x1, y1 in PDF points; (0, 0) is bottom left


class Highlight(BaseModel):
    quote_index: int
    page: int  # from 1
    page_size: tuple[float, float]
    rects: list[Rect]


def find_span(quote: list[str], words: list[str]) -> tuple[int, int] | None:
    """The first and last word index of `quote` inside `words`, side by side. None if absent."""
    n = len(quote)
    for start in range(len(words) - n + 1):
        if words[start : start + n] == quote:
            return start, start + n - 1
    return None


def same_line(line: list[float], box: Rect) -> bool:
    """A box is on the current line if it is to the right and overlaps it from top to bottom."""
    x0, y0, _, y1 = box
    return x0 >= line[2] - 1 and y0 < line[3] and y1 > line[1]


def line_rects(boxes: list[Rect]) -> list[Rect]:
    """Join char boxes into one box per line, in reading order."""
    lines: list[list[float]] = []
    for box in boxes:
        if lines and same_line(lines[-1], box):
            line = lines[-1]
            line[1], line[2], line[3] = min(line[1], box[1]), box[2], max(line[3], box[3])
        else:
            lines.append(list(box))
    return [tuple(round(v, 1) for v in line) for line in lines]


def locate(pdf_path: Path, quotes: list[str]) -> list[Highlight]:
    """One Highlight per quote found in the text layer. A quote that is not found is skipped."""
    wanted = [(i, WORD.findall(q.lower())) for i, q in enumerate(quotes)]
    found = []
    pdf = pdfium.PdfDocument(pdf_path)
    for page_no, page in enumerate(pdf, start=1):
        text_page = page.get_textpage()
        text = text_page.get_text_range()
        spans = [(m.start(), m.end()) for m in WORD.finditer(text.lower())]
        words = [text[a:b].lower() for a, b in spans]
        for i, quote in wanted:
            span = find_span(quote, words) if quote else None
            if span is None:
                continue
            first, last = spans[span[0]][0], spans[span[1]][1]
            boxes = [text_page.get_charbox(k) for k in range(first, last) if not text[k].isspace()]
            found.append(
                Highlight(
                    quote_index=i, page=page_no, page_size=page.get_size(), rects=line_rects(boxes)
                )
            )
        wanted = [(i, q) for i, q in wanted if i not in {h.quote_index for h in found}]
    pdf.close()
    return sorted(found, key=lambda h: h.quote_index)
```
</details>

<details><summary>Complete <code>src/docintel/domain/pipeline.py</code></summary>

```python
"""One request, start to end: plan, parse, extract with retries, check. Typed in, typed out."""

import time
import uuid
from collections.abc import Callable
from pathlib import Path

from pydantic import BaseModel

from docintel.domain.extract.retry import extract_with_retry, final_answer
from docintel.domain.locate import Highlight, locate
from docintel.domain.parse.base import ParsedDoc
from docintel.domain.parse.docling_parser import parse_docling_ocr
from docintel.domain.parse.pypdf_parser import parse_pypdf
from docintel.domain.planner.planner import pick, plan_request
from docintel.domain.validate.issues import Issue
from docintel.domain.validate.rules import check_answer

TEXT_CHARS_PER_PAGE = 200  # below this, the PDF is a scan; the thinnest dev contract has 870
MAX_PAGES = 100  # the longest dev contract has 82
MAX_SCAN_PAGES = 10  # Docling OCR reads about 7 to 10 s per page on an 8 GB Mac
EXTRACT_MAX_TOKENS = 20_000  # the largest real extraction answer used 17,999


class TooLong(ValueError):
    pass


class NothingToExtract(ValueError):
    pass


class FieldResult(BaseModel):
    found: bool
    value: str | list[str] | None = None
    quotes: list[str]
    needs_review: bool
    issues: list[Issue]
    highlights: list[Highlight] = []  # empty for a scan, or a quote not found in the text layer


class Document(BaseModel):
    filename: str
    sha256: str  # the same file always has the same hash, so reviews can find it again
    sample_id: str | None = None


class ExtractResult(BaseModel):
    request_id: str
    document: Document
    fields: dict[str, FieldResult]
    unknown: list[str]
    needs_review: bool
    parser: str
    pages: int
    cost_usd: float
    latency_ms: int


def parse_pdf(pdf_path: Path) -> ParsedDoc:
    """pypdf when the PDF has a text layer. Docling OCR when it is a scan."""
    doc = parse_pypdf(pdf_path)
    if len(doc.pages) > MAX_PAGES:
        raise TooLong(f"{len(doc.pages)} pages, the limit is {MAX_PAGES}")
    if len(doc.text.strip()) >= TEXT_CHARS_PER_PAGE * len(doc.pages):
        return doc
    if len(doc.pages) > MAX_SCAN_PAGES:
        raise TooLong(f"a scan of {len(doc.pages)} pages, the limit for scans is {MAX_SCAN_PAGES}")
    return parse_docling_ocr(pdf_path)


Emit = Callable[[str, dict], None]  # (event name, data); the API turns these into SSE events


def no_events(event: str, data: dict) -> None:
    pass


def run_pipeline(
    pdf_path: Path, request: str, document: Document, client=None, on_event: Emit = no_events
) -> ExtractResult:
    """Parse, plan, extract with retries, check, keep the asked fields. Reports each step."""
    start = time.perf_counter()
    on_event("stage", {"name": "parse", "status": "start"})
    doc = parse_pdf(pdf_path)
    on_event("stage", {"name": "parse", "status": "done", "parser": doc.parser_name})
    on_event("stage", {"name": "plan", "status": "start"})
    plan, plan_call = plan_request(request, client=client)
    on_event("plan", {"fields": plan.fields, "unknown": plan.unknown})
    if not plan.fields:
        raise NothingToExtract(f"no known field in the request; unknown: {plan.unknown}")
    on_event("stage", {"name": "extract", "status": "start"})
    attempts = extract_with_retry(
        doc.text,
        client=client,
        max_tokens=EXTRACT_MAX_TOKENS,
        on_attempt=lambda a: on_event("attempt", {"n": a.attempt_no, "errors": len(a.errors)}),
    )
    answer = final_answer(attempts)
    if answer is None:
        raise ValueError("the model gave no answer that fits the schema")
    on_event("stage", {"name": "check", "status": "start"})
    issues = check_answer(answer, doc.text)  # rule errors and review warnings
    picked = pick(answer, plan.fields)
    fields = {}
    for name in plan.fields:
        own = [i for i in issues if i.field == name]
        answer_part = getattr(picked, name).model_dump()
        boxes = locate(pdf_path, answer_part["quotes"]) if doc.parser_name == "pypdf" else []
        fields[name] = FieldResult(
            **answer_part, needs_review=bool(own), issues=own, highlights=boxes
        )
    costs = [a.result.cost_usd for a in attempts] + [plan_call.cost_usd if plan_call else 0.0]
    return ExtractResult(
        request_id=str(uuid.uuid4()),
        document=document,
        fields=fields,
        unknown=plan.unknown,
        needs_review=any(f.needs_review for f in fields.values()),
        parser=doc.parser_name,
        pages=len(doc.pages),
        cost_usd=sum(c or 0.0 for c in costs) + doc.cost_usd,
        latency_ms=round((time.perf_counter() - start) * 1000),
    )
```
</details>

<details><summary>Complete <code>src/docintel/api/routes.py</code></summary>

```python
"""The routes. Each one checks its input, then calls a typed function from `domain/`."""

import asyncio
import hashlib
import json
import shutil
import tempfile
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse
from sse_starlette import EventSourceResponse

from docintel.api.samples import Sample, load_samples, sample_pdf
from docintel.api.schemas import Health
from docintel.domain.pipeline import (
    Document,
    ExtractResult,
    NothingToExtract,
    TooLong,
    run_pipeline,
)
from docintel.domain.planner.planner import PlanError

VERSION = "0.1.0"
MAX_BYTES = 10 * 1024 * 1024  # the largest dev PDF is 0.48 MB; scans are bigger
MAX_REQUEST_CHARS = 500
TIMEOUT_S = 240  # 3 slow extraction calls, plus OCR on a 10-page scan
KNOWN_ERRORS = {  # error type -> HTTP status; anything else is a bug (500)
    TimeoutError: 504,
    TooLong: 413,
    NothingToExtract: 422,
    PlanError: 502,
}

router = APIRouter()


def get_llm_client():
    """None means the real OpenRouter client. Tests replace this with a fake."""
    return None


def as_http(error: Exception) -> HTTPException:
    status = KNOWN_ERRORS[type(error)]
    detail = f"no answer within {TIMEOUT_S} s" if status == 504 else str(error)
    return HTTPException(status, detail)


@router.get("/health")
def health() -> Health:
    return Health(status="ok", version=VERSION)


@router.get("/v1/samples")
def samples() -> list[Sample]:
    return list(load_samples().values())


@router.get("/v1/samples/{sample_id}/pdf")
def sample_file(sample_id: str) -> FileResponse:
    path = sample_pdf(sample_id)
    if path is None:
        raise HTTPException(404, f"no sample {sample_id!r}")
    return FileResponse(path, media_type="application/pdf")


async def read_input(pdf: UploadFile | None, sample_id: str | None) -> tuple[bytes, Document]:
    """The PDF bytes and their `Document`, from an upload or from a sample. Exactly one."""
    if (pdf is None) == (sample_id is None):
        raise HTTPException(422, "send a pdf or a sample_id, not both and not neither")
    if sample_id is not None:
        path = sample_pdf(sample_id)
        if path is None:
            raise HTTPException(404, f"no sample {sample_id!r}")
        data, filename = path.read_bytes(), path.name
    else:
        if pdf.size is not None and pdf.size > MAX_BYTES:
            raise HTTPException(413, f"the PDF is over {MAX_BYTES // (1024 * 1024)} MB")
        data, filename = await pdf.read(), pdf.filename or "upload.pdf"
    if not data.startswith(b"%PDF-"):
        raise HTTPException(415, "the file is not a PDF")
    sha = hashlib.sha256(data).hexdigest()
    return data, Document(filename=filename, sha256=sha, sample_id=sample_id)


@router.post("/v1/extract")
async def extract(
    client: Annotated[object, Depends(get_llm_client)],
    pdf: UploadFile | None = None,
    sample_id: Annotated[str | None, Form()] = None,
    request: Annotated[str, Form()] = "",
) -> ExtractResult:
    if len(request) > MAX_REQUEST_CHARS:
        raise HTTPException(422, f"the request is over {MAX_REQUEST_CHARS} characters")
    data, document = await read_input(pdf, sample_id)
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "upload.pdf"
        path.write_bytes(data)
        try:
            return await asyncio.wait_for(
                run_in_threadpool(run_pipeline, path, request, document, client),
                timeout=TIMEOUT_S,
            )
        except tuple(KNOWN_ERRORS) as e:
            raise as_http(e) from None


@router.post("/v1/extract/stream")
async def extract_stream(
    client: Annotated[object, Depends(get_llm_client)],
    pdf: UploadFile | None = None,
    sample_id: Annotated[str | None, Form()] = None,
    request: Annotated[str, Form()] = "",
) -> EventSourceResponse:
    """The same work as /v1/extract, sent as events while it runs: stage, plan, attempt, result."""
    if len(request) > MAX_REQUEST_CHARS:
        raise HTTPException(422, f"the request is over {MAX_REQUEST_CHARS} characters")
    data, document = await read_input(pdf, sample_id)
    folder = Path(tempfile.mkdtemp())
    path = folder / "upload.pdf"
    path.write_bytes(data)
    queue: asyncio.Queue = asyncio.Queue()
    loop = asyncio.get_running_loop()

    def emit(event: str, data: dict) -> None:  # runs in the pipeline's thread
        loop.call_soon_threadsafe(queue.put_nowait, (event, data))

    async def work() -> None:
        try:
            result = await asyncio.wait_for(
                run_in_threadpool(run_pipeline, path, request, document, client, emit),
                timeout=TIMEOUT_S,
            )
            await queue.put(("result", result.model_dump(mode="json")))
        except tuple(KNOWN_ERRORS) as e:
            error = as_http(e)
            await queue.put(("error", {"status": error.status_code, "detail": error.detail}))
        except Exception:  # a bug: say so, without the details
            await queue.put(("error", {"status": 500, "detail": "internal error"}))
        finally:
            await queue.put(None)  # the end

    async def events():
        task = asyncio.create_task(work())
        try:
            while (item := await queue.get()) is not None:
                name, payload = item
                yield {"event": name, "data": json.dumps(payload)}
        finally:
            await task
            shutil.rmtree(folder, ignore_errors=True)

    return EventSourceResponse(events())
```
</details>

## Break it on purpose

The break is free. Put the code back after it.

**Break 1: group lines by their bottom.** In `same_line`, replace the `return` line with
`return abs(line[1] - y0) < 3`. Guess: which tests fail, and with what numbers?

<details><summary>What you see</summary>

```text
>       assert len(h.rects) == 1  # the raised quote marks stay on the same line
E       assert 3 == 1
>       assert len(h.rects) == 2
E       assert 3 == 2
```

Both box tests fail. The raised quote marks each start a new "line" (Round 1). In the UI, one highlight would look
like three broken pieces.
</details>

## Experiment

This part runs no experiment. The Step 2 count (156 of 158) is a check, not a new eval number: it reuses the 158 quotes
of the `e3` set.

## Gotchas

- **A quote across a page break is not found.** `locate` looks at one page at a time. It is rare in CUAD; the UI still
  shows the quote text.
- **A quote with a copy error is not found.** The same as `quote_missing` in 2a. No box is better than a wrong box.
- **A closed stream does not stop the work.** If the browser leaves, the thread still finishes, and its calls are
  still paid.
- **`curl` without `-N` waits for the end.** It holds back the output. The events are still sent as they happen.

## Explain back, then commit

Explain to Claude in a few sentences:

- `locate.py`: the steps from a quote to line boxes, and why lines are joined that way (Round 1).
- Why the boxes use points and a bottom-left origin, and how the UI flips them (Round 3).
- `pipeline.py`: which events are sent, and when. Why `on_event` is a plain callback.
- `routes.py`: the job of `emit`, `work` and `events`, and why `call_soon_threadsafe`.
- How an error reaches the browser in a stream.

Then:

```sh
git status
git add pyproject.toml uv.lock src/docintel/domain/locate.py src/docintel/domain/pipeline.py src/docintel/domain/extract/retry.py src/docintel/api/routes.py tests/conftest.py tests/test_stream.py
git commit -m "phase 4a3: highlights and the event stream"
```

## Conclusion

The API can now say where each quote is, and what it is doing while it works. Phase 4a is done. Go back through the
objectives and check each one without notes. Then answer:

1. A quote is found by the citation check, but `locate` returns nothing for it. Give two reasons.
2. Why does the stream send an `error` event, and not an HTTP error status?

Looking for more challenges? Try these (optional):

1. Keep Docling's OCR word boxes in `ParsedDoc`, and highlight scans too.
2. Send a `field` event for each field after `check`, so the UI could reveal rows from the server.

Checklist (`../PLAN.md`): **Structured outputs** (the `Highlight` model). **Retries, timeouts, degradation** (an
error event, no boxes for scans). Next: 4b.
