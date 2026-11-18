# Phase 4c: the UI shell

In this part, the app gets a face. You pick fields from chips, then drop a PDF or click a sample tile. A card shows the
real stages of the pipeline on a pill, then the answers appear one row at a time. The pill ends on "2 issues found" or
"Passed". `make app` serves the UI and the API from one address.

This part is different from the others. The user asked Claude to write the UI code, so this is a **read and run**
doc, like 0a. You read each file, run each checkpoint, and then explain it back before you commit. It needs 4b2. The
paid checkpoints cost about $0.001 each.

## Words used in this part

Read these first.

- **SSE (server-sent events)**: a response that stays open and sends small named messages. Example:
  `event: stage` then `data: {"name": "parse", "status": "start"}`.
- **EventSource**: the browser's built-in SSE client. It can only send GET, with no body.
- **eventsource-parser**: a small npm package that cuts a stream of text into SSE messages. We use it with `fetch`.
- **Reducer**: a function `(state, event) -> new state` that never changes the old state. Example:
  `next(state, {event: "result", ...})` gives a state with `phase: "done"`.
- **Proxy (Vite dev server)**: Vite answers on :5173 and passes `/v1/...` calls on to FastAPI on :8000.
- **Same origin**: the page and the API have the same scheme, host and port. The browser then needs no CORS rules.
- **Static files**: files sent as they are, like `index.html` and `assets/index-CR3tJVz1.js`.
- **Build**: Vite turns `web/src/` into a few small files in `web/dist/`. Example: 275 kB of JS.
- **Skeleton**: a gray bar that holds the place of text that has not come yet.
- **daisyUI theme**: a set of color names (`primary`, `warning`, `base-100`, ...) that the components use.
- **Type stripping**: Node (22.18 or newer) can run a `.ts` file by deleting the types first. No compile step.

## Objectives

By the end of this part you should be able to:

1. Run the UI two ways (`make web` while you change it, `make app` to use it) and say why both are "same origin".
2. Explain why the stream uses `fetch` plus a parser, and not `EventSource`.
3. Follow one real SSE stream through the reducer, and say what the pill shows after each event.
4. Say which state lives in TanStack Query, which lives in React state, and why.
5. Show where each API error ends up in the UI: 415, 422, 504 and "API not running".

## Dependencies

npm packages, pinned to exact versions in `web/package.json`. Each one is at least two weeks old and has no OSV
advisory:

| Package | Version | Job |
|---|---|---|
| react, react-dom | 19.3.1 | the UI |
| vite, @vitejs/plugin-react | 8.3.5, 6.2.1 | dev server and build |
| typescript | 7.0.2 | type check only (`tsc --noEmit`) |
| tailwindcss, @tailwindcss/vite | 4.3.4 | utility classes |
| daisyui | 5.7.50 | components and themes, on top of Tailwind |
| lucide-react | 1.66.0 | icons |
| @tanstack/react-query | 5.105.3 | fetch and cache `/v1/fields` and `/v1/samples` |
| eventsource-parser | 4.1.3 | read the SSE stream from `fetch` |
| @types/node | 24.19.2 | types for `process` and `node:test` |

No test library. The plan said vitest, but `npm install` crashed on vitest's optional peer packages (an npm 10.9.2
bug: `Cannot read properties of null (reading 'edgesOut')`). Node's own test runner does the job, with one less
package.

Python: no new package. FastAPI already has `StaticFiles`.

## The big picture

```text
make web   browser -> :5173 Vite (UI, hot reload) --/v1, /health--> :8000 FastAPI (make serve)
make app   browser -> :8000 FastAPI: /v1/... and /health = API, everything else = web/dist
```

Inside the page:

```text
GET /v1/fields  -> chips (TanStack Query, fetched once)
GET /v1/samples -> tiles (TanStack Query, fetched once)
click a tile    -> POST /v1/extract/stream -> events -> next(state, event) -> card + pill
```

- **4c2** adds the PDF pane on the right, the review card, "Passed" after reviews, and Copy JSON.
- **Phase 5** records the demo video from this UI.

## Remember this

> The UI only draws what the API says. Every stage on the pill is a real event from the server. A pure reducer turns
> the events into state, so the whole flow can be tested with a saved stream and no browser. The page and the API
> come from one address, so there is no CORS to set up.
>
> **Events in, state out, one origin.**

## Why

**The API was ready; a person could not use it.** `curl` with `-F fields=...` is fine for you. A reviewer or a
demo video needs chips, a drop zone and a clear "what happened".

**Waiting 10 to 20 seconds needs feedback.** A spinner says "something". The stage pill says what: reading the PDF,
finding 4 fields, checking every quote. A retry is shown too.

**Errors must reach the user.** A 415, a 504 or a stopped server each get their own clear message, not a blank card.

## Design decisions

- **Same origin.** `make app` serves the built UI from FastAPI; `make web` uses Vite's proxy. Other option: Vite on
  :5173 calling :8000 directly. That needs CORS rules in FastAPI, and two setups to keep correct.
- **`fetch` plus eventsource-parser, not EventSource.** The extract needs a POST with a file. EventSource can only GET.
  Other option: upload first, then GET a stream by id. That is two calls and a store for uploads.
- **TanStack Query only for fields and samples.** They are plain "GET and cache" data. The stream is one long call that
  changes the card many times, so it lives in React state through the reducer. Other option: a query with
  `streamedQuery`. More magic for one call.
- **A pure reducer (`analysis.ts`).** No React, no `fetch` inside. So a saved stream can be replayed in a test. Other
  option: `setState` calls spread over the components. That can only be tested in a browser.
- **Rows appear after the `result` event.** The API sends all fields in one `result` event. The rows then show one by
  one, 140 ms apart, as a display choice. The stages before that are real. Other option: one event per field. That
  would need the model to stream, and the check runs on the whole answer anyway.
- **One accent color.** The daisyUI `primary` color is used for chips, links and the ring. Amber (`warning`) means
  only "needs review". Other option: daisyUI's default theme. Its colors do not match the prototype.
- **Check on the client too, then trust the server.** The drop zone refuses a `.txt` file and a file over 10 MB
  before any upload. The server still checks everything (415, 413). Other option: server only. The user would wait
  for an upload just to read "not a PDF".

## Worked example

All events and numbers are real. Guess before you open each box.

### Round 1: the pill during one stream

This is the real stream for the Kubient sample, with all 12 fields (the `data` lines are cut):

```text
event: stage    {"name": "parse", "status": "start"}
event: stage    {"name": "parse", "status": "done", "parser": "pypdf", "pages": 2}
event: stage    {"name": "extract", "status": "start"}
event: attempt  {"n": 0, "errors": 0}
event: stage    {"name": "check", "status": "start"}
event: result   {"request_id": "10419b08-...", "needs_review": true, ...}
```

Guess the words after "Analyzing ·" on the pill after each event.

<details><summary>Guess, then open</summary>

```text
Sending the PDF        (before any event)
Reading the PDF
Reading the PDF        (parse done: only the page count changes)
Finding 12 fields
Finding 12 fields      (an attempt with 0 errors changes nothing)
Checking every quote
(empty)                (the result: the rows start to show)
```

This list is the first test in `analysis.test.ts`. When all rows are shown, the pill says "2 issues found":
`non_compete` and `renewal_term` have `needs_review: true`.
</details>

### Round 2: a retry

The model's first answer broke 2 rules. The events are `attempt {"n": 0, "errors": 2}`, then
`attempt {"n": 1, "errors": 0}`. Guess the pill after each one.

<details><summary>Guess, then open</summary>

```text
Fixing 2 problems, try 2
Fixing 2 problems, try 2
```

`n` counts from 0, so the second try is `n + 2 = 2`. The second attempt has no errors, so the text stays until the
`check` stage starts.
</details>

### Round 3: what does the browser send?

You click Clear, then Parties, Governing law, Non-compete and Renewal term, then the Kubient tile. Guess the form
fields in the request.

<details><summary>Guess, then open</summary>

```text
sample_id = kubient
fields    = parties
fields    = governing_law
fields    = non_compete
fields    = renewal_term
```

Read from the real request in the browser. With all 12 chips on, the browser sends **no** `fields` at all. The API
reads "none" as "all 12" (4a), so the request stays short.
</details>

## Project setup

Claude made these files. Install the packages:

```sh
make web-install
```

```text
cd web && npm ci

added 48 packages, and audited 55 packages in 2s

13 packages are looking for funding
  run `npm fund` for details

5 high severity vulnerabilities

To address all issues (including breaking changes), run:
  npm audit fix --force

Run `npm audit` for details.
```

`npm ci` installs the exact versions from `package-lock.json`, like `uv sync` with `uv.lock`. The 5 warnings are one
problem: `picomatch` (used inside Vite) has a slow-regex bug in every version, so no fix exists yet. It runs only in
the build tool on your own file names, never in the app. Do not run `npm audit fix --force`: it would put Vite 6 back.

You should now have:

```text
web/
├── index.html
├── package.json
├── package-lock.json
├── tsconfig.json
├── vite.config.ts
├── public/
│   └── favicon.svg
└── src/
    ├── main.tsx
    ├── App.tsx
    ├── api.ts
    ├── analysis.ts
    ├── analysis.test.ts
    ├── index.css
    ├── fixtures/
    │   └── kubient-stream.json
    └── components/
        ├── FieldChips.tsx
        ├── DropZone.tsx
        ├── SampleTiles.tsx
        ├── AnalyzeCard.tsx
        └── StatusPill.tsx
```

Changed outside `web/`: `src/docintel/api/app.py`, `Makefile`, `.gitignore`.

## Step 1: the scaffold

Read `web/vite.config.ts`:

```ts
const api = process.env.API_URL ?? "http://localhost:8000";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: { "/v1": api, "/health": api },
  },
});
```

Here, we:

1. Add React (JSX, fast refresh) and Tailwind (it reads the classes in `src/` and makes only the CSS you use).
2. Send every `/v1/...` and `/health` call from :5173 on to the API. The browser only ever talks to :5173.
3. Allow another API address with `API_URL`. Claude used `API_URL=http://localhost:8001`, because :8000 was busy.

Read `web/tsconfig.json`. Three lines matter for the test:

- `"allowImportingTsExtensions": true` and `"noEmit": true`: imports end in `.ts`, like `./api.ts`. Node needs the
  real file name, and `tsc` only checks, it never writes JS.
- `"erasableSyntaxOnly": true`: no `enum` and no `namespace`. Node can only run TypeScript whose types can simply be
  deleted.

Read `web/package.json`. The scripts:

```json
"dev": "vite",
"build": "vite build",
"typecheck": "tsc --noEmit",
"test": "node --disable-warning=ExperimentalWarning --test \"src/**/*.test.ts\""
```

Checkpoint. Start the API in one terminal, and Vite in a second one:

```sh
make serve
```

```sh
make web
```

Then, in a third terminal, call the API through Vite:

```sh
curl -s localhost:5173/health
```

```text
{"status":"ok","version":"0.1.0"}
```

The answer came from FastAPI, through port 5173. Open http://localhost:5173 to see the start screen.

## Step 2: the theme

Read `web/src/index.css`. It has three parts:

1. `@import "tailwindcss"` and `@plugin "daisyui" { themes: false; }`: the components, with none of daisyUI's own
   themes.
2. Two `@plugin "daisyui/theme"` blocks, `docintel` (light, the default) and `docintel-dark` (`prefersdark: true`).
   The colors come from the prototype. Example: `--color-primary: #6656f0` in light, `#9a8cff` in dark.
3. Two small effects from the prototype: `.ring-busy` (the turning ring around the pill) and `.pop` (a row icon
   appears with a small bounce). Both stop when the system asks for less motion (`prefers-reduced-motion`).

Here, we use daisyUI's color names everywhere (`bg-base-100`, `text-warning`, `border-primary`). So dark mode needs no
`dark:` classes: the browser picks the theme, and the names point at new colors.

## Step 3: the API client

Read `web/src/api.ts`. The types copy the Pydantic models, one for one:

```ts
export type FieldResult = {
  // domain/pipeline.py
  found: boolean;
  value: string | string[] | null;
  quotes: string[];
  needs_review: boolean;
  issues: Issue[];
  highlights: Highlight[];
  evidence: string[];
  evidence_highlights: Highlight[];
};
```

Here, we write the types by hand, with a comment that names the Python file. If a Pydantic model changes, change the
type too. Other option: make the types from `/openapi.json` with a generator. That is one more tool for 6 small types.

Checkpoint. Compare with the real answer:

```sh
curl -s localhost:8000/v1/fields | head -c 160
```

```text
[{"name":"parties","label":"Parties","group":"Basic facts"},{"name":"agreement_date","label":"Agreement date","group":"Basic facts"},{"name":"governing_la
```

Each item has `name`, `label` and `group`, like `FieldInfo`.

Now the stream. Read `streamExtract`:

```ts
const form = new FormData();
if ("sampleId" in input) form.append("sample_id", input.sampleId);
else form.append("pdf", input.pdf);
if (fields.length < allFields) fields.forEach((f) => form.append("fields", f)); // none = all 12

const response = await fetch("/v1/extract/stream", { method: "POST", body: form, signal });
if (!response.ok || !response.body) {
  const body = await response.json().catch(() => null);
  onEvent({ event: "error", data: { status: response.status, detail: detailText(body) } });
  return;
}
const events = response.body.pipeThrough(new TextDecoderStream()).pipeThrough(new EventSourceParserStream());
for await (const message of events) {
  onEvent({ event: message.event, data: JSON.parse(message.data) } as StreamEvent);
}
```

Here, we:

1. Build the same form as `curl -F`. A repeated `fields` key is how FastAPI reads a list.
2. POST it. `signal` lets "New contract" stop the call.
3. If the answer is not 200 (a 415 or 422 comes before any stream), read FastAPI's `detail` and turn it into an
   `error` event. So the card has one way to show every error.
4. Otherwise, turn the bytes into text, cut the text into SSE messages, and hand each one to `onEvent`.

`detailText` handles the two shapes of `detail`: a string (`"the file is not a PDF"`), or a 422 list of problems
(it joins their `msg`).

Checkpoint (paid, about $0.0006). Watch the events arrive through the Vite proxy, with the time of each:

```sh
curl -s -N -X POST localhost:5173/v1/extract/stream -F sample_id=kubient -F fields=parties \
  | while IFS= read -r line; do case "$line" in event:*) echo "$(date +%H:%M:%S) $line";; esac; done
```

```text
19:45:20 event: stage
19:45:20 event: stage
19:45:20 event: stage
19:45:31 event: attempt
19:45:31 event: stage
19:45:31 event: result
```

The three stage events came at once, then 11 seconds of model time, then the rest. So the proxy passes each event
on when it comes, and does not wait for the end. That is what makes the pill live.

## Step 4: the reducer

Read `web/src/analysis.ts`. It has no React and no `fetch`. Four functions:

```ts
export function next(state: Analysis, e: StreamEvent): Analysis {
  switch (e.event) {
    case "stage":
      if (e.data.name === "parse" && e.data.status === "start") return { ...state, stage: "Reading the PDF" };
      if (e.data.name === "parse") return { ...state, pages: e.data.pages ?? null };
      if (e.data.name === "extract") return { ...state, stage: `Finding ${plural(state.fieldCount, "field")}` };
      return { ...state, stage: "Checking every quote" };
    case "attempt":
      if (e.data.errors === 0) return state;
      return { ...state, stage: `Fixing ${plural(e.data.errors, "problem")}, try ${e.data.n + 2}` };
    case "result":
      return { ...state, phase: "done", stage: "", pages: e.data.pages, result: e.data };
    case "error":
      return { ...state, phase: "failed", stage: "", error: e.data };
  }
}
```

Here, we:

1. Return a **new** object every time (`{ ...state, ... }`), like a Redux reducer. React sees a new object, and draws
   again.
2. Turn each event into the words the user reads. The words live here, not in the components.
3. Let TypeScript check the `switch`: `StreamEvent` lists the 4 event names, so a missing case is a type error.

The other three:

- `start(fieldCount)`: the state before any event (`"Sending the PDF"`).
- `pill(state, allShown)`: Analyzing while it runs **or** while rows are still showing, then "N issues found" or
  "Passed". On an error: "Something went wrong".
- `rows(result, fields)`: one row per chosen field, in the order of `GET /v1/fields`. The icon is `warn` if the field
  needs review, `ok` if found, `no` if not. The text copies the prototype: a list joined with `;`, a value, or
  `Yes · "quote"` for a yes or no field.

Checkpoint:

```sh
make web-test
```

```text
cd web && npm run typecheck && npm test

> docintel-web@0.1.0 typecheck
> tsc --noEmit

> docintel-web@0.1.0 test
> node --disable-warning=ExperimentalWarning --test "src/**/*.test.ts"
✔ the pill shows the real stages, in order (1.365333ms)
✔ a retry says how many problems the model must fix (0.16125ms)
✔ the pill waits for the last row, then counts the flagged fields (0.467666ms)
✔ an error event ends the run, with the server's words (0.079875ms)
✔ rows follow the field list order, and show found, not found and flagged (0.185875ms)
ℹ tests 5
ℹ suites 0
ℹ pass 5
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 119.330583
```

## Step 5: the components

Read them in this order. Each is small.

1. `main.tsx`: one `QueryClient` with `staleTime: Infinity`. Fields and samples never change while the app runs, so
   they are fetched once.
2. `App.tsx`: two screens. With no `job`, the start screen. With a `job`, "New contract" and the card.
3. `FieldChips.tsx`: the 4 groups come from the `group` of each field, in API order. Select all and Clear set the
   whole `Set`. With 0 chips on, "Pick at least one field." shows, and the tiles and drop zone are turned off.
4. `DropZone.tsx`: drag and drop or "choose a file". It refuses a file that is not a PDF, or is over 10 MB, before any
   upload. `e.target.value = ""` lets you pick the same file again.
5. `SampleTiles.tsx`: one button per sample. The scan sample has a "scan · OCR, slower" badge. It works: the API
   reads it with Docling OCR (3a2).
6. `AnalyzeCard.tsx`: a row for every chosen field. Before a row is shown, it has a skeleton icon and bar. After the
   result, `useReveal` counts from 0 up to the number of rows, one step every 140 ms. The footer (parser, pages,
   cost, seconds) comes after the last row.
7. `StatusPill.tsx`: the pill under the card. `key={pill.kind}` makes React build a new pill when the kind changes,
   so the `pop` animation runs again.

Now read `run` in `App.tsx`. It joins everything:

```ts
const run = (j: Job) => {
  stop.current?.abort();
  const controller = new AbortController();
  stop.current = controller;
  setJob(j);
  setAnalysis(start(j.fields.length));
  window.scrollTo({ top: 0 });
  streamExtract(j.input, j.fields, fields.data!.length, (e) => setAnalysis((s) => s && next(s, e)), controller.signal).catch(
    (err: unknown) => {
      if (controller.signal.aborted) return; // "New contract" was clicked: nobody is waiting
      const detail = err instanceof TypeError ? "Could not reach the API. Is it running?" : String(err);
      setAnalysis((s) => s && next(s, { event: "error", data: { status: 0, detail } }));
    },
  );
};
```

Here, we:

1. Stop any older call first, so two streams can never write to one card.
2. Set the start state, then feed every event through `next`. `setAnalysis((s) => ...)` uses the newest state, even
   when events come fast.
3. Turn a network failure (`fetch` throws a `TypeError` when nothing answers) into the same `error` event.
4. Ignore the failure that `abort()` causes on purpose.

"Try again" calls `run(job)` with the same job. "New contract" aborts and clears the job.

A gap to know: `abort()` stops the browser's call, not the server's work. The pipeline runs on in its thread and
still saves its `requests` row. That is fine for one local user. With many users, you would cancel the work too.

## Step 6: serve the UI from FastAPI

Read the new lines in `src/docintel/api/app.py`:

```python
WEB_DIST = Path("web/dist")  # the built UI, from `make app`; relative to the repo, like data/
```

```python
app.include_router(router)

# The UI, at the same address as the API, so the browser needs no CORS. Added after the routes, so
# /v1/... and /health still go to the API. Only there after `make app` builds it.
if WEB_DIST.is_dir():
    app.mount("/", StaticFiles(directory=WEB_DIST, html=True), name="web")
```

Here, we:

1. Mount the built files at `/`, **after** the routes. FastAPI tries routes in the order they were added, so `/v1/...`
   still reaches the API.
2. Use `html=True`, so `/` sends `index.html`.
3. Mount only if the folder exists. `make test` and `make serve` work without a build.

*Python: [PY-1](./py/phase-4c.md#py-1) and [PY-2](./py/phase-4c.md#py-2).*

The tracing from 4b is not changed: `not_traced` traces only `/v1/extract...`, so the page and its JS files never
show up in Phoenix.

Read the four new `Makefile` targets: `web-install` (`npm ci`), `web` (`npm run dev`), `web-test` (typecheck, then
the test) and `app` (`npm run build`, then uvicorn). `make app` has no `--reload`: it is for using the app, not for
changing it.

Checkpoint. Stop `make serve` and `make web`, then:

```sh
make app
```

```text
> docintel-web@0.1.0 build
> vite build

vite v8.3.5 building client environment for production...
transforming...
/*! 🌼 daisyUI 5.7.50 */
✓ 2100 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                   0.75 kB │ gzip:  0.40 kB
dist/assets/index-DDmEAO94.css   45.53 kB │ gzip:  9.20 kB
dist/assets/index-CR3tJVz1.js   275.36 kB │ gzip: 86.54 kB

✓ built in 486ms
INFO:     Started server process [43941]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8001 (Press CTRL+C to quit)
```

Claude ran this checkpoint on port 8001, because :8000 held the user's own server. On your machine the last line
says `:8000`. All outputs below come from that run.

In a second terminal:

```sh
curl -s -o /dev/null -w '%{http_code} %{content_type}\n' localhost:8000/
curl -s localhost:8000/v1/samples | head -c 80
```

```text
200 text/html; charset=utf-8
[{"id":"kubient","title":"Kubient: master services agreement","contract_type":"S
```

One port, two kinds of answer: the page at `/`, the API at `/v1/...`. The JSON log from 4b has a `request` line for
both.

## Step 7: the test

Read `web/src/analysis.test.ts`. It loads the real Kubient stream from `fixtures/kubient-stream.json` (6 events,
saved from the run in Round 1), and replays it:

```ts
function replay(list: StreamEvent[], fieldCount = 12): Analysis[] {
  const states = [start(fieldCount)];
  for (const e of list) states.push(next(states.at(-1)!, e));
  return states;
}
```

Here, we keep every state, not only the last, so a test can check the pill after each event (Round 1).

The 5 test names (in the Step 4 output) say what must never break without a sound. It uses `node:test` and `node:assert`, like Jest's `test` and `expect(...).toEqual(...)`. `assert.deepEqual` from
`node:assert/strict` compares objects key by key.

The checkpoint for this step is the `make web-test` run in Step 4.

## Step 8: try it in the browser

Open http://localhost:8000 (after `make app`). Each line below was checked in a real browser:

| Do this | You should see |
|---|---|
| Open the page | 12 chips in 4 groups, all on; a drop zone; 10 sample tiles, the last with "scan · OCR, slower" |
| Click Clear | "Pick at least one field." and the tiles turn gray |
| Turn on Parties, Governing law, Non-compete, Renewal term, then click Kubient (paid) | 4 skeleton rows, "Analyzing · Finding 4 fields" with the turning ring |
| Wait about 12 s | rows appear one by one; Non-compete and Renewal term in amber with "!"; pill "2 issues found"; footer `pypdf · 2 pages · $0.0008 · 11.4 s` |
| Click "New contract" | the start screen, with your 4 chips still chosen |
| Choose a `.txt` file | `"notes.txt" is not a PDF.` under the drop zone; no upload |
| Choose a `.pdf` that is really text | card with "the file is not a PDF", `HTTP 415`, "Try again"; pill "Something went wrong" |
| Set the system to dark mode | the dark theme, same layout |
| Make the window phone width | chips in 2 columns, tiles in 1, no side scroll |

The 415 also shows as a red line in the browser console: "Failed to load resource: the server responded with a
status of 415". That is the browser reporting the status, not a bug in the page.

## Break it

1. **Stop the API under an open page.** Open http://localhost:8000, stop `make app` with Ctrl+C, then click a tile.
   Guess the card.

   <details><summary>Guess, then open</summary>

   ```text
   Could not reach the API. Is it running?
   no answer from the API
   Try again
   ```

   `fetch` threw a `TypeError`, and `run` turned it into an `error` event. Start `make app` again, then click
   "Try again".
   </details>

2. **Remove the mount.** Comment out the two `app.mount` lines and run `make app`. Guess what `/` gives.

   <details><summary>Guess, then open</summary>

   `{"detail":"Not Found"}` with a 404. The API still works; nothing serves the page. Put the lines back.
   </details>

## Gotchas

- **`make serve` also serves an old UI.** Once `web/dist` exists, `make serve` mounts it too, at :8000. While you
  change the UI, use :5173 (`make web`). `make app` builds again each time.
- **Port 8000 is taken.** Another server is still running. Stop it, or run uvicorn with `--port 8001` and
  `API_URL=http://localhost:8001 make web`.
- **The model's time is most of the wait.** In the Step 3 run, 11 of the 11.1 seconds were the extraction call.
  The UI cannot make that faster; it can only show what is happening.

## Experiment

None. This part runs no eval and changes no prompt, schema or rule. The paid calls were only checkpoints.

## Explain-back gate

Before you commit, explain each of these in your own words. Claude will ask about the gaps.

1. `web/vite.config.ts`: what the proxy does, and why it means no CORS.
2. `web/src/api.ts`: why `fetch` and not `EventSource`; what happens on a 415.
3. `web/src/analysis.ts`: why it is pure; what `pill` shows while rows are still showing.
4. `web/src/App.tsx`: what `abort()` stops, and what it does not stop.
5. `web/src/components/AnalyzeCard.tsx`: how `useReveal` shows the rows.
6. `src/docintel/api/app.py`: why the mount comes after `include_router`.
7. `Makefile`: when to use `make web`, and when `make app`.

## Conclusion

The pipeline now has a UI that a person can use: pick fields, pick a contract, watch the real stages, read the
answers. Go back through the objectives and check each one without notes. Then answer:

1. The API sends all 12 fields in one `result` event. So where does the "one row at a time" come from, and is it
   honest?
2. You open the page, then stop the API, then click a tile. Name every function the error passes through before the
   card shows it.

Looking for more challenges? Try these (optional):

1. Show the scan sample's longer wait: if `parser` in the parse `done` event is `docling_ocr`, add "(OCR)" to the
   stage.
2. Add a "Cancel" button while it runs. What would the server need, so that the work really stops?

Checklist (`../PLAN.md`): **Prod bar: API + UI** (the UI half; local only, the demo video in 4c2 stands in for the
public URL). **Graceful degradation** (every API error and a stopped API get a clear message and "Try again").
**Human-in-the-loop** (flagged fields are shown in amber; the review itself comes in 4c2). Next: 4c2.
