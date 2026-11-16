# Phase 4a2: highlights, evidence and a live stream

In this part, you give the UI the three things it needs from the prototype. First, where each quote is on the page, so
a click can highlight it. Second, for a "maybe missed" flag, the line that raised it. Third, a live stream of the real
steps, so the user watches "Analyzing" move forward.

This is part 2 of 2 for Phase 4a. It needs 4a. The paid checkpoint costs about $0.002.

## Words used in this part

Read these first. Route and dependency are from 4a.

- **Text layer**: the letters stored inside a PDF (3b). A scan has none.
- **Char box**: the small rectangle that one letter fills on the page. Example: `(318.9, 772.5, 324.1, 780.1)`.
- **PDF point**: the unit of a PDF page, 1/72 of an inch. A letter page is 612 by 792 points.
- **Bottom-left origin**: in a PDF, `y = 0` is the bottom of the page. On a screen, `y = 0` is the top.
- **Highlight**: the page number and the boxes that cover one quote, one box per line.
- **Evidence**: the line of the contract that made a review rule fire. Example: the line with "renew" in it.
- **SSE (server-sent events)**: one HTTP response that stays open, and sends small text messages as things happen.
  Example: `event: stage` then `data: {"name": "parse"}`.
- **Callback**: a function you pass in, which the code calls when something happens. Example: `on_event("stage", ...)`.
- **Queue**: a line of items. One side puts items in, the other side takes them out, in order.

## Objectives

By the end of this part you should be able to:

1. Turn a quote into a page number and line boxes, from the PDF's text layer.
2. Explain why a raised quote mark can split a line, and how the code keeps it whole.
3. Point a "maybe missed" flag at the line that raised it.
4. Report the pipeline's real steps through a callback, and send them as SSE from a thread to the browser.
5. Say what the UI will do with a highlight, including the flip of the y axis.

## Dependencies

New library (checked on PyPI and OSV: maintained, 0 open advisories):

- `sse-starlette`: sends SSE from FastAPI. In Express, you would write `res.write("event: ...\n\n")` by hand.

This part needs:

- 4a: `KNOWN_ERRORS`, `as_http`, `read_input`, `conftest.py`, the samples.
- 3a3: `pypdfium2`, already installed. 2a: the word rule of the citation check. 2a2: the `maybe_missed` rule.

## The big picture

Before this part, the API answered once, at the end, with quotes as plain text.

After this part:

```text
POST /v1/extract/stream
   event: stage   {"name": "parse", "status": "start"}
   event: stage   {"name": "parse", "status": "done", "parser": "pypdf", "pages": 5}
   event: stage   {"name": "extract", "status": "start"}
   event: attempt {"n": 0, "errors": 0}
   event: stage   {"name": "check", "status": "start"}
   event: result  {... "highlights": [{"page": 1, "rects": [...]}], "evidence_highlights": [...] ...}
```

- **4c** turns the `stage` events into the words on the "Analyzing" pill, and reveals the rows when `result` arrives.
- **4c2** draws each quote box (accent color) and each evidence box (amber) over the PDF page, and scrolls to it when
  a row is clicked.
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

**A flag must show its reason.** "Maybe missed" means the model said "not found", but the contract has words like
"renew". The review card in the prototype shows that line, and the PDF highlights it. The user decides in seconds.

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
- **Evidence is the whole line around the rule's match.** The rule may match only "renew", inside "renewal". A word
  piece has no box, and alone it tells the user little. Other option: highlight only the matched words.
- **Scans get no boxes.** They have no text layer. The UI still shows the quote and the evidence text. Other option:
  OCR boxes now. That is a bigger change to the parsers.
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

*Python here: [a type alias, and `tuple` in a model](./py/phase-4a2.md#py-1).*

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

## Step 3: the evidence line

**Why.** A "maybe missed" issue holds only the words the rule matched, such as `renew`. The user needs the whole line,
and its box.

Add to the bottom of `src/docintel/domain/locate.py`:

```python
def line_around(text: str, words: str) -> str:
    """The whole line of `text` that holds `words`. A short rule match becomes a line to show."""
    at = text.find(words)
    if at < 0:
        return words
    start = text.rfind("\n", 0, at) + 1
    end = text.find("\n", at + len(words))
    return text[start : end if end >= 0 else len(text)].strip()
```

Here, in order:

1. Find the matched words in the parsed text.
2. Go back to the start of that line, and forward to its end.
3. Return the line. If the words are not found, return the words, so the caller always gets text.

Checkpoint (free): the two "maybe missed" words that the review rules find in iVillage.

```sh
uv run python - <<'EOF'
from docintel.api.samples import sample_pdf
from docintel.domain.locate import line_around, locate
from docintel.domain.parse.pypdf_parser import parse_pypdf

pdf = sample_pdf("ivillage")
text = parse_pypdf(pdf).text
for words in ("renew", "LIMITATION OF LIABILITY"):
    line = line_around(text, words)
    (h,) = locate(pdf, [line])
    print(repr(words), "->", repr(line), "| page", h.page, h.rects)
EOF
```

```text
'renew' -> 'provide FMM with the opportunity to renew this Agreement (the "Renewal Term") on' | page 1 [(13.6, 492.4, 356.7, 498.1)]
'LIMITATION OF LIABILITY' -> '11.      LIMITATION OF LIABILITY. NEITHER PARTY SHALL HAVE ANY LIABILITY' | page 3 [(14.2, 107.2, 322.4, 111.7)]
```

The line comes from pypdf's text, and `locate` finds it again in pdfium's text, with the same word rule.

## Step 4: report the steps, and add the boxes to the answer

**Why.** The UI needs to know what the pipeline is doing, and where each quote and each evidence line is.

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

from docintel.domain.locate import Highlight, line_around, locate
```

Add three fields at the end of `FieldResult`:

```python
    highlights: list[Highlight] = []  # where each quote is; empty for a scan
    evidence: list[str] = []  # "maybe missed": the line that holds the words the rule found
    evidence_highlights: list[Highlight] = []  # where each evidence line is
```

Then add the callback type and a small helper above `run_pipeline`, and replace `run_pipeline`:

```python
Emit = Callable[[str, dict], None]  # (event name, data); the API turns these into SSE events


def no_events(event: str, data: dict) -> None:
    pass


def boxes(pdf_path: Path, texts: list[str], text_layer: bool) -> list[Highlight]:
    """Line boxes for each text, when the PDF has a text layer. A scan has none."""
    return locate(pdf_path, texts) if text_layer and texts else []


def run_pipeline(
    pdf_path: Path,
    fields: list[FieldName],
    document: Document,
    client=None,
    on_event: Emit = no_events,
) -> ExtractResult:
    """Parse, extract all 12 with retries, check, keep the chosen fields. Reports each step."""
    start = time.perf_counter()
    on_event("stage", {"name": "parse", "status": "start"})
    doc = parse_pdf(pdf_path)
    done = {"name": "parse", "status": "done", "parser": doc.parser_name, "pages": len(doc.pages)}
    on_event("stage", done)
    on_event("stage", {"name": "extract", "status": "start"})
    attempts = extract_with_retry(
        doc.text,
        client=client,
        max_tokens=EXTRACT_MAX_TOKENS,
        on_attempt=lambda a: on_event("attempt", {"n": a.attempt_no, "errors": len(a.errors)}),
    )
    answer = final_answer(attempts)
    if answer is None:
        raise NoAnswer("the model gave no answer that fits the schema")
    on_event("stage", {"name": "check", "status": "start"})
    issues = check_answer(answer, doc.text)  # rule errors and review warnings
    text_layer = doc.parser_name == "pypdf"
    chosen = [f for f in FIELDS if f in fields] or list(FIELDS)  # schema order, no repeats
    results = {}
    for name in chosen:
        own = [i for i in issues if i.field == name]
        part = getattr(answer, name).model_dump()
        evidence = [line_around(doc.text, i.detail) for i in own if i.rule == "maybe_missed"]
        results[name] = FieldResult(
            **part,
            needs_review=bool(own),
            issues=own,
            highlights=boxes(pdf_path, part["quotes"], text_layer),
            evidence=evidence,
            evidence_highlights=boxes(pdf_path, evidence, text_layer),
        )
    return ExtractResult(
        request_id=str(uuid.uuid4()),
        document=document,
        fields=results,
        needs_review=any(r.needs_review for r in results.values()),
        parser=doc.parser_name,
        pages=len(doc.pages),
        cost_usd=sum(a.result.cost_usd or 0.0 for a in attempts) + doc.cost_usd,
        latency_ms=round((time.perf_counter() - start) * 1000),
    )
```

*Python here: [`Callable`, and a lambda that calls a callback](./py/phase-4a2.md#py-2).*

Here, the new parts, in order:

1. Report `stage` events at the start and end of parsing (with the page count), and at the start of extract and check.
2. Report each `attempt`, so a retry is visible.
3. For each "maybe missed" issue, keep its evidence line.
4. For a text PDF, find the boxes of each quote and each evidence line. `boxes` skips the PDF when there is nothing
   to find.

## Step 5: the stream route

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
    fields: Annotated[list[FieldName] | None, Form()] = None,
) -> EventSourceResponse:
    """The same work as /v1/extract, sent as events while it runs: stage, attempt, result."""
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
                run_in_threadpool(run_pipeline, path, fields or [], document, client, emit),
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

*Python here: [a queue between a thread and `async`](./py/phase-4a2.md#py-3) · [an `async` generator](./py/phase-4a2.md#py-4).*

Here, in order:

1. Check the input, and save the PDF, as in `extract`.
2. `emit` hands each event from the pipeline's thread to the event loop, safely.
3. `work` runs the pipeline in a thread, with the time limit. At the end it adds `result`, or one `error` event with the
   status code from `KNOWN_ERRORS`, then `None` to say "the end".
4. `events` takes items from the queue, in order, and sends each one as SSE. After the end, it waits for `work`, and
   deletes the temporary folder.

Checkpoint (paid, about $0.002). Start the server with `make serve`. `-N` tells curl to print events as they come:

```sh
curl -s -N -F sample_id=ivillage -F fields=parties -F fields=renewal_term -F fields=cap_on_liability localhost:8000/v1/extract/stream
```

```text
event: stage
data: {"name": "parse", "status": "start"}

event: stage
data: {"name": "parse", "status": "done", "parser": "pypdf", "pages": 5}

event: stage
data: {"name": "extract", "status": "start"}

: ping - 2026-11-16 18:39:08.801792+00:00

event: attempt
data: {"n": 0, "errors": 0}

event: stage
data: {"name": "check", "status": "start"}

event: result
data: {"request_id": "...", ...}
```

The `result` line is long. Its fields, in short (quote boxes, then evidence boxes):

```text
parties found  [{"quote_index": 0, "page": 1, ...}, {"quote_index": 1, "page": 1, ...}]  []
renewal_term not found  review ['maybe_missed']  []  [{"quote_index": 0, "page": 1, "page_size": [595.0, 842.0], "rects": [[13.6, 492.4, 356.7, 498.1]]}]
cap_on_liability not found  review ['maybe_missed']  []  [{"quote_index": 0, "page": 3, "page_size": [595.0, 842.0], "rects": [[14.2, 107.2, 322.4, 111.7]]}]
cost 0.00174356 ms 16080 parser pypdf
```

Both flags point at the same lines as Step 3. These are the two amber rows of the prototype. Watch the terminal while
it runs: the `extract` stage waits a few seconds, then the rest comes at once. The `: ping` line is a comment that
sse-starlette sends every 15 s to keep the connection open. The browser ignores it.

## Step 6: a small test

**Why.** Wrong boxes or a stream in the wrong order would break the UI with no error on the server.

First, add one line to the `api` fixture in `tests/conftest.py`, after the `parse_pdf` line. The fake PDF of the tests has
no pages, so `locate` must not open it:

```python
    monkeypatch.setattr(pipeline, "locate", lambda path, quotes: [])  # the fake PDF has no pages
```

The test names say what is protected: a quote is one box on its line, a two-line quote has two boxes, a missing quote
and a scan give nothing, a rule match becomes its whole line, the events come in order and end with the result, and a
failure ends with an error event before any paid call.

<details><summary>Put this in <code>tests/test_stream.py</code></summary>

```python
"""Highlights on real sample PDFs, and the event stream with the fakes from `conftest.py`."""

import json

from docintel.api.samples import SAMPLES_DIR
from docintel.domain import pipeline
from docintel.domain.locate import line_around, locate
from docintel.domain.parse.pypdf_parser import parse_pypdf
from docintel.domain.pipeline import TooLong

KUBIENT = SAMPLES_DIR / "kubient.pdf"
QUOTE = 'Kubient, Inc. ("Kubient")'


def events(client, fields: list[str]) -> list[tuple[str, dict]]:
    """Send a stream request, and read back (event, data) pairs."""
    data = {"sample_id": "kubient", "fields": fields}
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


def test_a_rule_match_becomes_its_whole_line():
    pdf = SAMPLES_DIR / "ivillage.pdf"
    line = line_around(parse_pypdf(pdf).text, "renew")
    assert line.startswith("provide FMM with the opportunity to renew this Agreement")
    (h,) = locate(pdf, [line])
    assert h.page == 1


def test_events_come_in_order_and_end_with_the_result(api):
    names = [name for name, _ in events(api, ["parties"])]
    assert names == ["stage", "stage", "stage", "attempt", "stage", "result"]


def test_a_failure_ends_with_an_error_event(api, sent, monkeypatch):
    def too_long(path):
        raise TooLong("120 pages, the limit is 100")

    monkeypatch.setattr(pipeline, "parse_pdf", too_long)
    pairs = events(api, ["parties"])
    assert pairs[-1] == ("error", {"status": 413, "detail": "120 pages, the limit is 100"})
    assert sent == []  # it stopped before the paid call
```
</details>

The box tests use real sample PDFs from `src/docintel/api/samples/`. They are part of the repo, so the test still
needs no network.

Checkpoint:

```sh
uv run pytest tests/test_stream.py -q
make test
make lint
```

```text
......                                                                   [100%]
6 passed in 0.14s
```

Your project structure should now look like this:

```text
src/docintel/
├── api/routes.py            # + /v1/extract/stream
└── domain/
    ├── extract/retry.py     # + on_attempt
    ├── locate.py            # Highlight, find_span, line_rects, locate, line_around
    └── pipeline.py          # on_event, boxes, highlights and evidence in FieldResult
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


def line_around(text: str, words: str) -> str:
    """The whole line of `text` that holds `words`. A short rule match becomes a line to show."""
    at = text.find(words)
    if at < 0:
        return words
    start = text.rfind("\n", 0, at) + 1
    end = text.find("\n", at + len(words))
    return text[start : end if end >= 0 else len(text)].strip()
```
</details>

<details><summary>Complete <code>src/docintel/domain/pipeline.py</code></summary>

```python
"""One request, start to end: parse, extract with retries, check. Typed in, typed out."""

import time
import uuid
from collections.abc import Callable
from pathlib import Path

from pydantic import BaseModel

from docintel.domain.extract.retry import extract_with_retry, final_answer
from docintel.domain.locate import Highlight, line_around, locate
from docintel.domain.parse.base import ParsedDoc
from docintel.domain.parse.docling_parser import parse_docling_ocr
from docintel.domain.parse.pypdf_parser import parse_pypdf
from docintel.domain.schema.fields import FIELDS, FieldName
from docintel.domain.validate.issues import Issue
from docintel.domain.validate.rules import check_answer

TEXT_CHARS_PER_PAGE = 200  # below this, the PDF is a scan; the thinnest dev contract has 870
MAX_PAGES = 100  # the longest dev contract has 82
MAX_SCAN_PAGES = 10  # Docling OCR reads about 7 to 12 s per page on an 8 GB Mac
EXTRACT_MAX_TOKENS = 20_000  # the largest real extraction answer used 17,999


class TooLong(ValueError):
    pass


class NoAnswer(ValueError):
    pass


class FieldResult(BaseModel):
    found: bool
    value: str | list[str] | None = None
    quotes: list[str]
    needs_review: bool
    issues: list[Issue]
    highlights: list[Highlight] = []  # where each quote is; empty for a scan
    evidence: list[str] = []  # "maybe missed": the line that holds the words the rule found
    evidence_highlights: list[Highlight] = []  # where each evidence line is


class Document(BaseModel):
    filename: str
    sha256: str  # the same file always has the same hash, so reviews can find it again
    sample_id: str | None = None


class ExtractResult(BaseModel):
    request_id: str
    document: Document
    fields: dict[str, FieldResult]
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


def boxes(pdf_path: Path, texts: list[str], text_layer: bool) -> list[Highlight]:
    """Line boxes for each text, when the PDF has a text layer. A scan has none."""
    return locate(pdf_path, texts) if text_layer and texts else []


def run_pipeline(
    pdf_path: Path,
    fields: list[FieldName],
    document: Document,
    client=None,
    on_event: Emit = no_events,
) -> ExtractResult:
    """Parse, extract all 12 with retries, check, keep the chosen fields. Reports each step."""
    start = time.perf_counter()
    on_event("stage", {"name": "parse", "status": "start"})
    doc = parse_pdf(pdf_path)
    done = {"name": "parse", "status": "done", "parser": doc.parser_name, "pages": len(doc.pages)}
    on_event("stage", done)
    on_event("stage", {"name": "extract", "status": "start"})
    attempts = extract_with_retry(
        doc.text,
        client=client,
        max_tokens=EXTRACT_MAX_TOKENS,
        on_attempt=lambda a: on_event("attempt", {"n": a.attempt_no, "errors": len(a.errors)}),
    )
    answer = final_answer(attempts)
    if answer is None:
        raise NoAnswer("the model gave no answer that fits the schema")
    on_event("stage", {"name": "check", "status": "start"})
    issues = check_answer(answer, doc.text)  # rule errors and review warnings
    text_layer = doc.parser_name == "pypdf"
    chosen = [f for f in FIELDS if f in fields] or list(FIELDS)  # schema order, no repeats
    results = {}
    for name in chosen:
        own = [i for i in issues if i.field == name]
        part = getattr(answer, name).model_dump()
        evidence = [line_around(doc.text, i.detail) for i in own if i.rule == "maybe_missed"]
        results[name] = FieldResult(
            **part,
            needs_review=bool(own),
            issues=own,
            highlights=boxes(pdf_path, part["quotes"], text_layer),
            evidence=evidence,
            evidence_highlights=boxes(pdf_path, evidence, text_layer),
        )
    return ExtractResult(
        request_id=str(uuid.uuid4()),
        document=document,
        fields=results,
        needs_review=any(r.needs_review for r in results.values()),
        parser=doc.parser_name,
        pages=len(doc.pages),
        cost_usd=sum(a.result.cost_usd or 0.0 for a in attempts) + doc.cost_usd,
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

from docintel.api.fields import FIELD_INFO, FieldInfo
from docintel.api.samples import Sample, load_samples, sample_pdf
from docintel.api.schemas import Health
from docintel.domain.pipeline import Document, ExtractResult, NoAnswer, TooLong, run_pipeline
from docintel.domain.schema.fields import FieldName

VERSION = "0.1.0"
MAX_BYTES = 10 * 1024 * 1024  # the largest dev PDF is 0.48 MB; scans are bigger
TIMEOUT_S = 240  # 3 slow extraction calls, plus OCR on a 10-page scan
KNOWN_ERRORS = {  # error type -> HTTP status; anything else is a bug (500)
    TimeoutError: 504,
    TooLong: 413,
    NoAnswer: 502,
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


@router.get("/v1/fields")
def list_fields() -> list[FieldInfo]:
    return FIELD_INFO


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
    fields: Annotated[list[FieldName] | None, Form()] = None,  # none: all 12
) -> ExtractResult:
    data, document = await read_input(pdf, sample_id)
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "upload.pdf"
        path.write_bytes(data)
        try:
            return await asyncio.wait_for(
                run_in_threadpool(run_pipeline, path, fields or [], document, client),
                timeout=TIMEOUT_S,
            )
        except tuple(KNOWN_ERRORS) as e:
            raise as_http(e) from None


@router.post("/v1/extract/stream")
async def extract_stream(
    client: Annotated[object, Depends(get_llm_client)],
    pdf: UploadFile | None = None,
    sample_id: Annotated[str | None, Form()] = None,
    fields: Annotated[list[FieldName] | None, Form()] = None,
) -> EventSourceResponse:
    """The same work as /v1/extract, sent as events while it runs: stage, attempt, result."""
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
                run_in_threadpool(run_pipeline, path, fields or [], document, client, emit),
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
2 failed, 4 passed
```

Both box tests fail. The raised quote marks each start a new "line" (Round 1). In the UI, one highlight would look
like three broken pieces. The evidence test still passes: its line has no raised marks.
</details>

## Experiment

This part runs no experiment. The Step 2 count (156 of 158) is a check, not a new eval number: it reuses the 158 quotes
of the `e3` set.

## Gotchas

- **A quote across a page break is not found.** `locate` looks at one page at a time. It is rare in CUAD; the UI still
  shows the quote text.
- **A quote with a copy error is not found.** The same as `quote_missing` in 2a. No box is better than a wrong box.
- **Only the first match of a rule is evidence.** `maybe_missed` keeps its first match, so a contract with "renew" on
  three pages shows one line.
- **A closed stream does not stop the work.** If the browser leaves, the thread still finishes, and its calls are
  still paid.
- **`curl` without `-N` waits for the end.** It holds back the output. The events are still sent as they happen.

## Explain back, then commit

Explain to Claude in a few sentences:

- `locate.py`: the steps from a quote to line boxes, and why lines are joined that way (Round 1).
- `line_around`: why the whole line, and not only the matched words.
- Why the boxes use points and a bottom-left origin, and how the UI flips them (Round 3).
- `pipeline.py`: which events are sent, and when. Why `on_event` is a plain callback.
- `routes.py`: the job of `emit`, `work` and `events`, and why `call_soon_threadsafe`.
- How an error reaches the browser in a stream.

Then:

```sh
git status
git add pyproject.toml uv.lock src/docintel/domain/locate.py src/docintel/domain/pipeline.py src/docintel/domain/extract/retry.py src/docintel/api/routes.py tests/conftest.py tests/test_stream.py
git commit -m "phase 4a2: highlights, evidence and the event stream"
```

## Conclusion

The API can now say where each quote is, why a field was flagged, and what it is doing while it works. Phase 4a is
done. Go back through the objectives and check each one without notes. Then answer:

1. A quote is found by the citation check, but `locate` returns nothing for it. Give two reasons.
2. Why does the stream send an `error` event, and not an HTTP error status?

Looking for more challenges? Try these (optional):

1. Keep Docling's OCR word boxes in `ParsedDoc`, and highlight scans too.
2. Give `quote_off_topic` evidence too: the words from the rule's topic list that the quote should have had.

Checklist (`../PLAN.md`): **Structured outputs** (the `Highlight` model). **Retries, timeouts, degradation** (an
error event, no boxes for scans). Next: 4b.
