# Phase 4c2: clean UI structure, the PDF pane and highlights

In this part, the answers meet the contract. When the last row is shown, the card moves left and the PDF opens on the
right. Click a row, and the PDF scrolls to its quote and draws a box around it. A "maybe missed" flag gets its
evidence line in amber.

First, the UI code moves into a clear structure, as the user asked: rules in `lib/`, side effects in `hooks/`,
drawing in `features/`. `App.tsx` drops from 113 lines to 49.

This is part 1 of 2 for 4c2. Part 4c3 adds the review card, Passed, Copy JSON and the e2e test. Claude wrote the
code for both parts; this is a **read and run** doc, like 4c. It needs 4c. No paid call is needed.

## Words used in this part

Read these first.

- **pdf.js**: Mozilla's PDF reader, written in JavaScript. Firefox uses it. It draws each page on a `<canvas>`.
- **react-pdf**: a small React wrapper around pdf.js: `<Document file=...>` and `<Page pageNumber={1} />`.
- **Web Worker**: a background thread in the browser. pdf.js reads the PDF there, so the page stays smooth.
- **PDF point**: the unit inside a PDF. 72 points = 1 inch. An A4 page is 595 by 842 points.
- **Origin of a page**: where (0, 0) is. In a PDF, the bottom-left corner. In the browser, the top-left corner.
- **Code splitting**: the build makes a second JS file that loads only when needed. Example: pdf.js (633 kB) loads
  only when a result is shown.
- **`React.lazy`**: loads a component from its own file the first time it is drawn.
- **ResizeObserver**: a browser API that calls you when an element changes size.
- **Pure function**: same input, same output, and it changes nothing outside. Example: `toBoxes(highlight, 595)`.
- **Accessible name**: the words a screen reader says for a button. Playwright finds buttons by it too.

## Objectives

By the end of this part you should be able to:

1. Say what goes in `lib/`, `hooks/` and `features/`, and why that makes the code easier to test.
2. Turn a box in PDF points into CSS pixels by hand, including the flip of the y axis.
3. Explain why pdf.js loads only after the result, and how to see that in the build output.
4. Follow one click on a row to the box that pulses on the PDF.
5. Say why the PDF pane scrolls itself, and not the window.

## Dependencies

| Package | Version | Job |
|---|---|---|
| react-pdf | 11.0.0 | `<Document>` and `<Page>` for React |
| pdfjs-dist | 6.3.289 | pdf.js itself; pinned to the version react-pdf uses, so there is only one copy |

Both are at least two weeks old, with no OSV advisory.

The plan says "pdf.js eval off". In pdf.js 6, there is no switch any more: the old `isEvalSupported` option and the
code behind it are gone. So a bad PDF cannot run code through font loading, and there is nothing to turn off.

ESLint was planned as a "try". It is skipped: `typescript-eslint` supports TypeScript below 6.1, and we use 7.0.2.
`tsc --strict` stays our check.

## The big picture

```text
web/src/
├── main.tsx, App.tsx          App: top bar, then the start screen or the work screen
├── lib/                       pure rules, no React: api.ts, analysis.ts, boxes.ts (+ reviews.ts in 4c3)
├── hooks/                     side effects: useAnalysis (stream), useReveal (timer), useReviews (4c3)
└── features/
    ├── start/                 StartScreen, FieldChips, DropZone, SampleTiles
    └── work/                  WorkScreen, AnalyzeCard, FieldRow, FieldDetail, StatusPill,
                               CostFooter, PdfPane, HighlightLayer, ReviewCard (4c3)
```

One click, from row to box:

```text
FieldRow click -> WorkScreen: open = "parties", focus = {quote 0}, clicks + 1
              -> marksFor(field, focus) -> PdfPane -> HighlightLayer -> toBoxes(points -> px)
              -> the pane scrolls to the box, and the box pulses
```

- **4c3** puts the review card under a "!" row, and adds Passed and Copy JSON.
- **Phase 5** records the demo from this screen.

## Remember this

> The server says where each quote is, in PDF points. The browser only turns points into pixels: scale by the drawn
> width, and flip y, because a PDF counts from the bottom. That math is a pure function with a test, so the boxes
> stay right when the window changes size.
>
> **Points from the server, pixels in the browser, flip y.**

## Why

**A quote you cannot find is not a citation.** The answer says "page 1". A lawyer still has to look for the words.
A box on the page shows them at once.

**Evidence needs the same help.** "The model may have missed a renewal term" only makes sense next to the line that
made the rule fire.

**The code was getting hard to read.** `App.tsx` held the stream, the abort, the chips state and the layout. Adding
the PDF and reviews there would make one long file.

## Design decisions

- **Three folders by job, not by type.** `lib/` has rules (tested with `node --test`), `hooks/` has effects (fetch,
  timers, abort), `features/` has screens. Other option: one `components/` folder. It mixes rules with drawing, and
  rules in components need a browser to test.
- **Boxes come from the server.** `locate.py` (4a2) already found each quote's line boxes with pypdfium2. Other option:
  search the text in the browser with pdf.js's text layer. That is a second search, with its own rules, that could
  disagree with the citation check.
- **No text layer, no annotation layer.** We only draw the page and our boxes. Other option: turn them on, so text can
  be selected. That needs extra CSS and makes each page slower.
- **pdf.js loads late.** `React.lazy(() => import("./PdfPane.tsx"))`. Other option: import it at the top. The first
  page would then download 633 kB more before the user has picked a contract.
- **The pane scrolls itself.** The PDF is a tall box with its own scroll bar, next to the card. Other option: scroll the
  window. The card would then move away from the row you clicked.
- **The first flagged row opens by itself.** After the reveal, the user's next job is the first "!". Other option:
  open nothing. Then the user must hunt for the amber row.
- **Rows tell a screen reader their state.** The icons are `aria-hidden`; a hidden text says "found", "not found" or
  "needs review". The e2e test (4c3) found this: the "!" was part of the button's name.

## Worked example

All numbers are real. Guess before you open each box.

### Round 1: points to pixels

The quote `Kubient, Inc. ("Kubient")` is on page 1, an A4 page (595 by 842 points). Its box from the API is
`[318.9, 772.5, 398.5, 780.1]` (x0, y0, x1, y1, y from the bottom). The page is drawn 595 px wide, and we add 2 px of
room on each side. Guess `left` and `top` in CSS pixels.

<details><summary>Guess, then open</summary>

```text
{ left: 316.9, top: 59.9, width: 83.6, height: 11.6 }
```

At 595 px wide, 1 point is 1 px. `left` = 318.9 - 2. `top` = 842 - 780.1 - 2 = 59.9: the top edge of the text is
`y1`, counted from the bottom, so it is flipped. The quote is near the top of the page, as it should be.
</details>

### Round 2: a page twice as wide

The same box, on a page drawn 1190 px wide. Guess the `width`.

<details><summary>Guess, then open</summary>

```text
{ left: 635.8, top: 121.8, width: 163.2, height: 19.2 }
```

Not 167.2. The text is 79.6 points wide, so 159.2 px at 2 px per point. The 2 px of room on each side does not grow:
159.2 + 4 = 163.2. Claude first wrote 167.2 in the test, and the test caught it.
</details>

### Round 3: an upload

You drop your own `my-contract.pdf`. Guess which request the PDF pane makes to show it.

<details><summary>Guess, then open</summary>

```text
http://localhost:8001/assets/pdf.worker.min-Dswkl-cV.mjs
```

Only the pdf.js worker. The pane reads the `File` you dropped, straight from the browser's memory. A sample uses
`/v1/samples/{id}/pdf` instead. Both are in `Job.pdf`: a URL or a `File`.
</details>

## Project setup

Install the new packages (the lockfile already has them):

```sh
make web-install
```

```text
cd web && npm ci

added 65 packages, and audited 72 packages in 4s

19 packages are looking for funding
  run `npm fund` for details

5 high severity vulnerabilities
...
```

The 5 warnings are still the one `picomatch` problem inside Vite (see 4c).

You should now have (new and moved files only):

```text
web/src/
├── App.tsx                         (49 lines, was 113)
├── lib/
│   ├── api.ts                      (moved; + Rect, ReviewSaved, ApiError, samplePdfUrl)
│   ├── analysis.ts                 (moved)
│   ├── analysis.test.ts            (moved)
│   ├── boxes.ts                    (new)
│   └── boxes.test.ts               (new)
├── hooks/
│   ├── useAnalysis.ts              (new: the stream, out of App.tsx)
│   └── useReveal.ts                (new: out of AnalyzeCard.tsx)
└── features/
    ├── start/  StartScreen.tsx (new), FieldChips.tsx, DropZone.tsx, SampleTiles.tsx (moved)
    └── work/   WorkScreen.tsx, FieldRow.tsx, FieldDetail.tsx, HighlightLayer.tsx, PdfPane.tsx,
                CostFooter.tsx (new); AnalyzeCard.tsx, StatusPill.tsx (moved)
```

Also changed: `web/package.json`, `web/vite.config.ts`, `web/tsconfig.json`, `.gitignore`.

## Step 1: one job per folder

Read `web/src/App.tsx`. It now only picks a screen:

```tsx
{job && analysis && fields.data ? (
  <WorkScreen
    key={job.id} // a new job starts with a fresh screen: no open row, no reviews
    job={job}
    analysis={analysis}
    allFields={fields.data}
    onNew={reset}
    onRetry={() => run(job)}
  />
) : (
  <StartScreen ... onStart={run} />
)}
```

Here, we:

1. Keep the fields and samples queries here, because both screens use them.
2. Give the work screen `key={job.id}`. A new key makes React build a new `WorkScreen`, so its state (open row,
   reviews) starts empty. "Try again" also makes a new id.
3. Leave the chosen chips as `null` until the user changes them. `null` means "all". So there is no `useEffect` to
   fill the set when the fields arrive.

Read `web/src/hooks/useAnalysis.ts`. It is the old `run` from `App.tsx`, plus two things:

1. `Job` now has `id` and `pdf` (a URL for a sample, the `File` for an upload).
2. `useEffect(() => () => stop.current?.abort(), [])`: when the page goes away, the stream stops.

The rule for every file: `lib/` never imports React; `hooks/` hold `useState`, `useEffect` and `fetch`; `features/`
draw what they get as props.

Checkpoint. The old tests run from their new place:

```sh
make web-test
```

```text
✔ the pill shows the real stages, in order (1.769ms)
✔ a retry says how many problems the model must fix (0.102208ms)
✔ the pill waits for the last row, then counts the flagged fields (0.30925ms)
✔ an error event ends the run, with the server's words (0.069292ms)
✔ rows follow the field list order, and show found, not found and flagged (1.033875ms)
✔ at 595 px wide, 1 point is 1 px, and y is flipped to count from the top (1.351292ms)
✔ a page drawn twice as wide doubles the box, but the 2 px of room stays 2 px (0.284791ms)
✔ pending lists the flagged fields with no review, in field order (2.408834ms)
...
ℹ pass 13
ℹ fail 0
```

The first 5 are from 4c. The 2 box tests are this part. The rest are 4c3.

## Step 2: points to pixels

Read `web/src/lib/boxes.ts`:

```ts
export function toBoxes(h: Highlight, pageWidth: number): Box[] {
  const [pointsWide, pointsHigh] = h.page_size;
  const scale = pageWidth / pointsWide;
  return h.rects.map(([x0, y0, x1, y1]) => ({
    left: round(x0 * scale - PAD),
    top: round((pointsHigh - y1) * scale - PAD), // flip: y1 is the top edge, counted from the bottom
    width: round((x1 - x0) * scale + 2 * PAD),
    height: round((y1 - y0) * scale + 2 * PAD),
  }));
}
```

Here, we:

1. Find how many pixels one point is: the drawn width over the page width in points.
2. Scale every number by it.
3. Flip y: the distance from the top is the page height minus the top edge (`y1`).
4. Add 2 px of room around the text, and round to 0.1 px so the test can compare exact numbers.

Two more small functions in the same file:

- `firstFocus(field, f, flagged)`: what to show first. The first quote, or the evidence line when a flagged field has
  no quote boxes (a "maybe missed" field has no quote at all).
- `marksFor(f, focus, { quotes, evidence })`: the boxes to draw for the open field. Each one knows its kind (quote or
  evidence) and if it is the focused one.

Checkpoint: the two box tests in Step 1 are Rounds 1 and 2 of the worked example.

## Step 3: the PDF pane

Read `web/src/features/work/PdfPane.tsx`. The top:

```tsx
import workerUrl from "pdfjs-dist/build/pdf.worker.min.mjs?url";
import { Document, Page, pdfjs } from "react-pdf";

pdfjs.GlobalWorkerOptions.workerSrc = workerUrl;
```

Here, we tell pdf.js where its worker file is. `?url` asks Vite for the file's final URL, with its hash, like
`/assets/pdf.worker.min-Dswkl-cV.mjs`.

The pages:

```tsx
<Document file={file} onLoadSuccess={(pdf) => setCount(pdf.numPages)} ...>
  {width > 0 &&
    Array.from({ length: count }, (_, i) => i + 1).map((n) => (
      <div key={n} ref={...} className="relative overflow-hidden rounded-[3px] bg-white shadow-sm">
        <Page pageNumber={n} width={width} renderTextLayer={false} renderAnnotationLayer={false}
              onRenderSuccess={() => setDrawn((d) => d + 1)} ... />
        <HighlightLayer marks={marks.filter((m) => m.highlight.page === n)} pageWidth={width} pulseKey={pulseKey} />
        <span className="absolute right-2 bottom-1.5 ...">{n}</span>
      </div>
    ))}
</Document>
```

Here, we:

1. Load the PDF once (`file` is a URL or a `File`), and learn the page count.
2. Draw every page at the pane's width. `usePageWidth` reads that width with a `ResizeObserver`, so a bigger window
   gives bigger pages, and `toBoxes` moves the boxes with them.
3. Put a `HighlightLayer` on top of each page, with only that page's boxes. The boxes have `pointer-events: none`,
   so they never block a click.
4. Count drawn pages in `drawn`. The scroll effect waits for it, because a page has no height before it is drawn.

The scroll:

```tsx
useEffect(() => {
  const target = marks.find((m) => m.focused) ?? marks[0];
  const page = target && pages.current.get(target.highlight.page);
  if (!target || !page || !pane.current || !width) return;
  const top = page.offsetTop + toBoxes(target.highlight, width)[0].top - 80;
  ...
  pane.current.scrollTo({ top, behavior: smooth ? "smooth" : "auto" });
}, [pulseKey, drawn, width]);
```

It scrolls the pane (not the window) so the focused box is 80 px from the top. `pulseKey` changes on every click, so
clicking the same row again scrolls and pulses again.

Read `WorkScreen.tsx`, the lazy import:

```tsx
const PdfPane = lazy(() => import("./PdfPane.tsx")); // pdf.js loads only when a result is shown
```

```tsx
{ready && result && (
  <Suspense fallback={<div className="skeleton h-[70vh] rounded-2xl" />}>
    <PdfPane file={job.pdf} name={result.document.filename} marks={marks} pulseKey={`${open}-${clicks}`}
             scan={result.parser !== "pypdf"} />
  </Suspense>
)}
```

A scan (`docling_ocr`) has no boxes: its text came from OCR, not from the PDF's text layer. The pane then says "a scan:
no boxes, the text was read with OCR".

Checkpoint. The build makes separate files:

```sh
cd web && npm run build
```

```text
dist/index.html                              0.75 kB │ gzip:   0.39 kB
dist/assets/pdf.worker.min-Dswkl-cV.mjs  1,265.41 kB
dist/assets/index-BntzCFTI.css              66.78 kB │ gzip:  12.03 kB
dist/assets/index-B13NLmSL.js              291.90 kB │ gzip:  91.97 kB
dist/assets/PdfPane-fYtl-q33.js            632.74 kB │ gzip: 191.18 kB
✓ built in 500ms
```

The start screen loads `index-*.js` (292 kB). `PdfPane-*.js` and the worker load only after a result. Vite warns when
a file is over 500 kB, so `vite.config.ts` sets `chunkSizeWarningLimit: 700`, with a comment saying why.

## Step 4: rows that open

Read `web/src/features/work/WorkScreen.tsx`. It holds the state of the work screen:

```tsx
const [open, setOpen] = useState<string | null>(null);
const [focus, setFocus] = useState<Focus | null>(null);
const [clicks, setClicks] = useState(0); // every click on a row or a quote: scroll and pulse again
```

```tsx
const openField = (name: string | null, reviews: Reviews) => {
  setOpen(name);
  setClicks((c) => c + 1);
  if (!name || !result) return setFocus(null);
  const f = result.fields[name];
  setFocus(firstFocus(name, f, f.needs_review && !reviews[name]));
};
```

Here, we open one row at a time, and point the focus at its first box. When the last row is shown (`ready`), an
effect opens the first flagged field, or the first found one.

The layout switches when `ready` is true: `min-[920px]:grid-cols-[minmax(0,470px)_minmax(0,1fr)]`. On a wide screen,
the card is on the left (at most 470 px) and the PDF on the right. Below 920 px, they stack.

Read `FieldRow.tsx` and `FieldDetail.tsx`:

1. `FieldRow` is a `<button aria-expanded>`. Arrow Up and Arrow Down move between rows (`moveFocus`).
2. Its icon is `aria-hidden`. A hidden `sr-only` text says ", found", ", not found" or ", needs review".
3. `FieldDetail` lists each quote as a button with "page N" (or "not found on the page"). Click one to jump to it.

## Step 5: try it in the browser

Run `make app`, open http://localhost:8000, and click the Kubient tile (paid, about $0.001). Each line was checked in a
real browser, with the stored Kubient answer and once live. The scan line was checked with that answer changed to
look like an OCR result (no boxes), because a real scan run is slow and paid.

| Do this | You should see |
|---|---|
| Wait for the last row | the card moves left, the PDF opens on the right; the first "!" row is open |
| Look at page 1 | the Non-compete quote has a purple box around 4 lines of text |
| Click Parties | the pane scrolls up; two small boxes around `Kubient, Inc. ("Kubient")` and `The Associated Press ("Customer")`; the first one pulses |
| Click the second quote under Parties | its box pulses |
| Open Renewal term | an amber box around the line `partners (collectively "Third-Party") ... During the Term and any renewal terms of the` |
| Make the window narrow | the PDF moves under the card, with its own scroll |
| Dark mode | the card goes dark; the PDF pages stay white |
| Click the scan tile (slow: OCR) | the PDF shows, with "a scan: no boxes"; quotes say "not found on the page" |
| Drop your own PDF | it shows your file, not a sample |

## Break it

Remove the flip: in `toBoxes`, change the `top` line to `top: round(y1 * scale - PAD),`. Guess what the first box
test says.

<details><summary>Guess, then open</summary>

```text
✖ at 595 px wide, 1 point is 1 px, and y is flipped to count from the top (1.576667ms)
  + actual - expected
    actual: [ { left: 316.9, top: 778.1, width: 83.6, height: 11.6 } ],
    expected: [ { left: 316.9, top: 59.9, width: 83.6, height: 11.6 } ],
```

The box went to 778 px from the top: the bottom of the page, while the words are at the top. In the browser, every
box would sit in the wrong place, mirrored top to bottom. Put the line back.
</details>

## Gotchas

- **The Python `.gitignore` hid `web/src/lib/`.** The GitHub Python template has a `lib/` rule (for virtual
  environments). It matched our `lib/` folder too, so `git status` did not show it. `.gitignore` now has
  `!web/src/lib/`. Check with `git status --ignored web`: only `dist/`, `node_modules/` and `test-results/` should be
  there.
- **Boxes need the same page size.** pypdfium2 (server) and pdf.js (browser) must agree on the page size. They do for
  normal pages. A rotated page would need the rotation too; no sample has one.
- **On a phone, the PDF is below the card.** Clicking a row scrolls the PDF pane, but not the window to it.

## Experiment

None. No eval run, no prompt, schema or rule change.

## Explain-back gate

Before you commit, explain each of these in your own words. Claude will ask about the gaps.

1. `web/src/App.tsx`: why `key={job.id}` on the work screen.
2. `web/src/hooks/useAnalysis.ts`: what the empty `useEffect` cleanup stops.
3. `web/src/lib/boxes.ts`: the flip, with the Kubient numbers.
4. `web/src/features/work/PdfPane.tsx`: why the scroll waits for `drawn`; what `?url` gives.
5. `web/src/features/work/WorkScreen.tsx`: `open`, `focus` and `clicks`; why `React.lazy`.
6. `web/src/features/work/FieldRow.tsx`: what a screen reader says for a flagged row.
7. `.gitignore`: why `!web/src/lib/` is needed.

## Conclusion

Every answer now points at its words on the page. The code is split by job: rules you can test without a browser,
hooks for effects, and screens that only draw. Go back through the objectives and check each one without notes.
Then answer:

1. A quote box shows up at the bottom of the page, but the words are at the top. Which line do you check first, and
   which test should have caught it?
2. The start screen loads in 0.3 MB, but a result needs 1.9 MB more. Where does the rest come from, and when does it
   load?

Looking for more challenges? Try these (optional):

1. On a phone, scroll the window to the PDF pane when a row is clicked.
2. Draw the boxes of all found fields at once, in a lighter color, with the open one on top.

Checklist (`../PLAN.md`): **Prod bar: API + UI** (the UI shows each citation on the page). **Human-in-the-loop**
(flags open first, with their evidence highlighted). Next: 4c3.
