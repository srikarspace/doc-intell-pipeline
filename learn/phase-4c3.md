# Phase 4c3: review, Passed, Copy JSON and the e2e test

In this part, the human decides. Under each "!" row, a review card says in plain words why the field was flagged, and
offers **Accept** or **Modify**. Each choice is saved by the API from 4b2, and can be undone. When every flag has a
review, the pill says "Passed". Copy JSON gives the reviewed answer. One Playwright test runs the whole flow on a
stored answer, with no paid call.

This is part 2 of 2 for 4c2. It needs 4c2. Claude wrote the code; this is a **read and run** doc. The e2e test costs
nothing. A live check in the browser costs about $0.001.

## Words used in this part

Read these first.

- **Mutation**: a call that changes data on the server. Example: `POST /v1/reviews`. TanStack Query's `useMutation`
  runs one, and tracks `isPending` and `error`.
- **Source of truth**: the one place that decides what is real. Here, the API: a review shows only after the API
  saved it.
- **409 Conflict**: "this clashes with what is already there". Example: a second review of the same field.
- **Clipboard API**: `navigator.clipboard.writeText(text)`. The browser may refuse it, so we need a backup plan.
- **Fixture**: saved data that a test uses instead of a real call. Example: `web/src/fixtures/kubient-stream.json`.
- **Seed**: put known rows into a database before a test.
- **e2e (end-to-end) test**: a test that drives a real browser against the real app, like a user.
- **`page.route`**: Playwright answers one URL itself, instead of the server. Like `nock` or `msw` in Node.
- **`webServer`**: Playwright starts the app before the tests, and stops it after.

## Objectives

By the end of this part you should be able to:

1. Follow one Accept click from the button to the row in DuckDB, and back to "Passed".
2. Say why the UI waits for the API before it shows a review, and what a 409 means here.
3. Turn any stored answer into a test fixture, and seed it into a test database.
4. Run the e2e test, and say which parts are real and which part is replayed.
5. Record a short demo of the product.

## Dependencies

| Package | Version | Job |
|---|---|---|
| @playwright/test | 1.64.1 | the e2e test runner (dev only) |

Plus one browser, downloaded once:

```sh
cd web && npx playwright install chromium
```

```text
Chrome Headless Shell 156.0.8078.4 (playwright chromium-headless-shell v1248) downloaded to /Users/.../Library/Caches/ms-playwright/chromium_headless_shell-1248
```

It also removes browsers that no installed Playwright version needs any more.

## The big picture

```text
"!" row opens -> ReviewCard: why (reasonFor) + evidence + [Modify] [Accept]
Accept        -> useReviews.save -> POST /v1/reviews -> app_data.save_review (4b2) -> 201 ReviewSaved
              -> reviews[field] = saved -> row shows "reviewed" -> next "!" opens -> pill counts again
Undo          -> DELETE /v1/reviews/{id} -> 204 -> the "!" comes back
Copy JSON     -> reviewedAnswer(result, reviews) -> clipboard
make e2e      -> build -> seed 2 stored answers into a temp DB -> API on :8010 -> Chromium
```

- **Phase 5** uses the demo video and Copy JSON output in the README.

## Remember this

> The API is the source of truth for reviews. The UI shows a review only after the API saved it, and the database
> refuses a second review of the same field. A stored real answer replaces the model in the e2e test, so the test is
> free and gives the same result every run, while the UI, the API and DuckDB stay real.
>
> **Save first, then show. Replay the model, keep the rest real.**

## Why

**A flag with no action is noise.** The reviewer needs to say "this is right" or "this is the right value", and the
choice must last.

**"Passed" must mean something.** It says that every flag was looked at by a person, not that the model was sure.

**The flow has many moving parts.** Stream, reveal, PDF, review, undo, pill. Unit tests check each rule. Only a
browser test checks that they work together.

## Design decisions

- **Wait for the server, no optimistic update.** The review shows after the 201. Other option: show it at once and
  roll back on an error. Faster by 20 ms, but a failed save could look saved.
- **Undo, then change.** One review per field (the 4b2 rule). To change your mind, undo first. Other option: let a
  second review replace the first. Then the review log loses what happened.
- **The editor follows the field.** A yes or no field gets two buttons and sends `"Yes"` or `"No"`. Parties (a list)
  gets one name per line and sends a list. Other fields get one line of text. Other option: one text box for all.
  Then "no" could mean "not found" or a value called "no".
- **The next flag opens by itself.** After a save, the next "!" row opens and takes the keyboard focus. Other option:
  stay on the saved row. Then the user must scroll to find the next one.
- **Plain reasons in the UI, not rule names.** `reasonFor` turns `quote_off_topic` into "The quote may be about
  something else." Other option: show the rule name. Nobody outside this project knows what it means.
- **Copy JSON keeps the review next to each field.** Other option: only the new values. Then nobody can see which
  values a person changed.
- **The e2e test replays a stored answer.** `page.route` answers the stream with a real answer from DuckDB. Other
  option: a real model call on every run. It costs money, takes 10 to 20 s, and the model's answer can change, so the
  test can fail with no bug.
- **A fake key in the e2e server.** `OPENROUTER_API_KEY=sk-or-v1-e2e-not-used`. If the replay ever breaks, a real call
  fails at once, and costs nothing.

## Worked example

All outputs are real. Guess before you open each box.

### Round 1: which row opens next?

Kubient has two flags: Non-compete (quote off topic) and Renewal term (maybe missed). Non-compete is open. You click
Accept. Guess what happens on the screen.

<details><summary>Guess, then open</summary>

1. The API answers `201`. Non-compete gets a green check and a "reviewed" chip.
2. Renewal term opens, with its review card. Its evidence line gets an amber box on the PDF.
3. The pill says "1 issue found · click to review".

The reasons on the new card:

```text
The model said “not found”, but the contract may have it.
This line has words that often mean a renewal term clause. Read it, then keep “not found” or change it.
```
</details>

### Round 2: the same review again

You reload the page (the UI forgets its reviews, but the database keeps them). You open Kubient again, and click
Accept on Non-compete. Guess the message in the card.

<details><summary>Guess, then open</summary>

```text
'non_compete' is already reviewed; undo it first
```

The 409 from 4b2, shown in the card (`role="alert"`). The pill stays at "2 issues found": the UI did not count a review
the server refused. See Gotchas: the UI cannot load old reviews yet.
</details>

### Round 3: Modify, then Copy JSON

On Renewal term, you click Modify, type `1 year` and Save. Guess the `renewal_term` part of Copy JSON.

<details><summary>Guess, then open</summary>

```json
"renewal_term": {
  "found": true,
  "value": "1 year",
  "quotes": [],
  "review": {
    "review_id": "6bfd7dec-fdd3-408a-96de-0599df9b9467",
    "field": "renewal_term",
    "action": "modify",
    "old": null,
    "new": "1 year"
  }
}
```

`quotes` is empty: the value came from a person, not from a quote. `old` is `null`, the model's real answer, read by
the server from the stored row (4b2).
</details>

## Project setup

New files:

```text
web/
├── playwright.config.ts
├── e2e/
│   ├── fixtures.py           export a stored answer, seed it into a test DB
│   └── review.spec.ts        the e2e test
└── src/
    ├── fixtures/ecoscience-stream.json   (new, exported from a stored run)
    ├── lib/reviews.ts, reviews.test.ts
    ├── hooks/useReviews.ts
    └── features/work/ReviewCard.tsx, CostFooter.tsx (Copy JSON)
```

Changed: `lib/api.ts` (`postReview`, `deleteReview`), `lib/analysis.ts` (rows and pill know reviews),
`features/work/WorkScreen.tsx`, `FieldDetail.tsx`, `StatusPill.tsx` (it is a button now), `Makefile` (`make e2e`),
`.gitignore` (`web/test-results/`, `web/playwright-report/`).

## Step 1: review rules, without React

Read `web/src/lib/reviews.ts`. Five pure functions:

```ts
export function shown(f: FieldResult, review: ReviewSaved | undefined) {
  if (!review || review.action === "accept") return f;
  if (review.new === "No") return { found: false, value: null, quotes: [] };
  return { found: true, value: review.new === "Yes" ? null : review.new, quotes: [] };
}
```

Here, we decide what a field shows after its review:

1. No review, or Accept: the model's answer, as it is.
2. Modify to "No": not found.
3. Modify to anything else: found, with the new value, and no quote.

The others:

- `pending(result, fields, reviews)`: the flagged fields with no review, in field order. The pill counts these.
- `reasonFor(issue, label)`: a title and one more line for each rule, with a safe default for a rule it does not know.
- `reviewedAnswer(result, reviews)`: the JSON for Copy JSON (Round 3).
- `parseValue(kind, text)`: the editor's text into a value. A list takes one item per line, and drops empty lines.

`rows` and `pill` in `analysis.ts` now take `reviews` too. A reviewed row shows `shown(...)`, gets a "reviewed" chip,
and loses its "!". The pill says "Passed · 2 reviewed".

Checkpoint:

```sh
make web-test
```

```text
✔ pending lists the flagged fields with no review, in field order (2.408834ms)
✔ the pill says Passed once every flag has a review, and undo brings the issue back (0.762792ms)
✔ modify changes the row; a yes or no field set to No becomes not found (0.685167ms)
✔ Copy JSON keeps each review next to the new value (0.374667ms)
✔ the editor kind and its value (0.293584ms)
✔ every flag on the real answer has a plain reason (0.692083ms)
ℹ pass 13
ℹ fail 0
```

(Only this part's 6 tests are shown; all 13 pass.)

## Step 2: save and undo

Read `postReview` and `deleteReview` at the bottom of `web/src/lib/api.ts`. Both go through `call`, which turns a
non-200 answer into an `ApiError` with FastAPI's `detail`.

Read `web/src/hooks/useReviews.ts`:

```ts
const save = useMutation({
  mutationFn: (body: ReviewInput) => postReview(body),
  onSuccess: (saved) => {
    const nextReviews = { ...reviews, [saved.field]: saved };
    setReviews(nextReviews);
    onSaved?.(nextReviews);
  },
});
```

Here, we:

1. Send the review. Nothing changes on screen yet (the buttons are off while `isPending`).
2. On a 201, keep the `ReviewSaved` from the server, with its `review_id` (Undo needs it).
3. Tell the work screen, so it can open the next flag.

`undo` sends `DELETE /v1/reviews/{review_id}`, and on a 204 removes the field from `reviews`. `errorFor(field)` gives
the error message of the last failed save or undo of that field, for the card.

## Step 3: the review card

Read `web/src/features/work/ReviewCard.tsx`. Under a "!" row, it shows, in order:

1. "Needs a look", and for each issue its `reasonFor` title and line.
2. For "maybe missed", each evidence line as a button: "page 1, highlighted in amber". Click it to jump in the PDF.
3. **Modify** and **Accept**. For a field the model did not find, Accept says **Keep "not found"**.
4. The error, if the save failed (`role="alert"`).

Modify swaps the buttons for the `Editor`, built by field kind (`kindOf`). The Save button is off while the value is
empty.

After a save, the card of the next flag takes the keyboard focus (`autoFocus`). A keyboard user can go on with Tab and
Enter, without the mouse.

Read `FieldDetail.tsx` again: a reviewed field says "You accepted this answer.", "You kept "not found"." or "You
changed this answer.", with an **Undo** link.

## Step 4: Passed and Copy JSON

The pill (`StatusPill.tsx`) is now a button while issues are open: "2 issues found · click to review". Click it to open
the first open flag. With none left: "Passed · 2 reviewed".

Read `web/src/features/work/CostFooter.tsx`. Copy JSON:

```ts
const copy = async () => {
  try {
    await navigator.clipboard.writeText(text());
    setCopied("yes");
    setTimeout(() => setCopied(null), 2000);
  } catch {
    setCopied("blocked"); // no clipboard (an old browser, or no permission): show the JSON instead
  }
};
```

Here, we try the clipboard. If the browser refuses, the JSON shows in a box under the footer, ready to select.

## Step 5: fixtures from stored answers

The user's idea: every real extract is already stored in `requests` (4b2), with its full answer. So a test can reuse
one, instead of paying for a new run.

Read `web/e2e/fixtures.py`. It has two commands. Export a stored answer as a stream fixture:

```sh
uv run python web/e2e/fixtures.py export b9ed26eb-d4a3-446f-af50-09cf9bd80d3a
```

```text
wrote web/src/fixtures/ecoscience-stream.json
```

That was the user's own EcoScience run. It opens the database read-only. It writes the 6 events the API would send,
with the stored answer as the `result`. Attempts are not stored, so it writes one clean attempt.

Seed a fixture's answer into a test database, so reviews of it work:

```sh
APP_DB=/path/to/test.duckdb uv run python web/e2e/fixtures.py seed web/src/fixtures/kubient-stream.json
```

```text
saved 10419b08-bd6b-4971-abe1-4aebbecba884 in /private/tmp/.../scratchpad/doc-seed.duckdb
```

It reuses `app_data.save_request` from 4b2, so the row is the same as a real one. Running it twice is fine.

*Python: [PY-1](./py/phase-4c3.md#py-1), [PY-2](./py/phase-4c3.md#py-2) and [PY-3](./py/phase-4c3.md#py-3).*

To list the stored answers you can export:

```sh
duckdb -readonly data/docintel.duckdb "SELECT request_id, sample_id FROM requests WHERE status=200"
```

## Step 6: the e2e test

Read `web/playwright.config.ts`. The `webServer` part:

```ts
webServer: {
  cwd: "..", // the repo root: web/dist and the Python package are found from there
  command: [
    `rm -f ${DB} ${DB}.wal`,
    seed("kubient"),
    seed("ecoscience"),
    `uv run uvicorn docintel.api.app:app --port ${PORT} --no-access-log`,
  ].join(" && "),
  url: `http://localhost:${PORT}/health`,
  env: { APP_DB: DB, TRACING: "false", OPENROUTER_API_KEY: "sk-or-v1-e2e-not-used" },
},
```

Here, we start from an empty temp database, seed the two stored answers, and start the real API on :8010. Your
`data/docintel.duckdb` and your own server on :8000 are never touched.

Read `web/e2e/review.spec.ts`. The replay:

```ts
async function replay(page: Page, sample: string) {
  const file = new URL(`../src/fixtures/${sample}-stream.json`, import.meta.url);
  const events: Event[] = JSON.parse(readFileSync(file, "utf8"));
  const body = events.map((e) => `event: ${e.event}\ndata: ${JSON.stringify(e.data)}\n\n`).join("");
  await page.route("**/v1/extract/stream", (route) =>
    route.fulfill({ status: 200, contentType: "text/event-stream", body }),
  );
}
```

Only this one URL is replayed. The fields, the samples, the PDF, the reviews and the undo all go to the real API.

The first test follows the whole flow: 2 issues, the PDF drawn, a quote box for Parties, Accept, the amber evidence box,
Keep "not found", "Passed · 2 reviewed", Undo, "1 issue found", and Copy JSON read back from the clipboard. The second
test opens EcoScience (no flags) and expects "Passed" at once.

Checkpoint:

```sh
make e2e
```

```text
✓ built in 500ms
[WebServer] INFO:     Started server process [48111]
[WebServer] INFO:     Waiting for application startup.
[WebServer] INFO:     Application startup complete.
[WebServer] INFO:     Uvicorn running on http://127.0.0.1:8010 (Press CTRL+C to quit)
Running 2 tests using 1 worker
  ✓  1 [chromium] › e2e/review.spec.ts:21:1 › review both flags of Kubient until it passes, then undo one (4.1s)
  ✓  2 [chromium] › e2e/review.spec.ts:57:1 › an answer with no flags passes at once (2.5s)
  2 passed (11.7s)
```

`VIDEO=1 make e2e` also records a silent video of each test in `web/test-results/`.

## Step 7: try it in the browser

Run `make app`, open http://localhost:8000, and click Kubient (paid, about $0.001). Checked in a real browser:

| Do this | You should see |
|---|---|
| Wait for the rows | the first "!" row is open, with "Needs a look" and its reason |
| Click Accept | the row turns green with "reviewed"; the next "!" opens; the pill counts down |
| On a yes or no field, click Modify | two buttons: "Yes, it is there" and "No" |
| On Renewal term, Modify, type `1 year`, Save | the row says "1 year", green, "reviewed" |
| When no "!" is left | pill "Passed · 2 reviewed" (green) |
| Click Undo under a reviewed row | the "!" comes back; pill "1 issue found · click to review" |
| Click the pill | the open flag opens |
| Click Copy JSON | "Copied"; paste it: each field has `review` |
| Press Tab after a save | the focus is in the next review card |

A live run may find a different number of flags: the model's answers can change between runs. In the live check, this
Kubient run had 1 flag, and one Accept gave "Passed · 1 reviewed".

Then check the database:

```sh
make stats
```

The review count by action goes up by one for each review you kept.

## Step 8: record the demo

About two minutes, with QuickTime (File, New Screen Recording) or any screen recorder. A script to follow:

1. **Start screen** (15 s): "Pick the fields, then a contract. 12 fields, from CUAD's lawyer labels."
2. **Kubient tile** (20 s): "These stages are real events from the server: reading, finding, checking every quote."
3. **Rows and PDF** (25 s): click Parties. "Every answer has its exact quote. The box comes from the server."
4. **A flag** (30 s): "The model said yes, but the quote has no word about competing. I read it, and accept."
5. **Evidence** (20 s): "Here the model said not found, but this line talks about renewal. I keep not found."
6. **Passed and Copy JSON** (10 s): "Every flag has a decision. Copy JSON keeps who changed what."

Save the video outside the repo, or in a folder that git ignores. Phase 5 links it from the README.

## Gotchas

- **A reload forgets the reviews on screen, not in DuckDB.** The API has no `GET` for the reviews of an answer yet,
  so the UI starts empty and a second review gets the 409 from Round 2. Undo is lost after a reload too.
- **Playwright cleans its browser cache.** `npx playwright install` deletes browser versions that no installed
  Playwright needs. Another tool that used an older version must download it again.
- **The clipboard needs permission in a test.** The test calls `context.grantPermissions(["clipboard-read",
  "clipboard-write"])`. In your own browser, `localhost` is allowed.
- **Exported fixtures have one clean attempt.** The stored row has the answer, not the attempts. A retry in the real
  run does not show in the replay.

## Experiment

None. The reviews are product data, not an eval. Phase 5 may count them with `make stats`.

## Explain-back gate

Before you commit, explain each of these in your own words. Claude will ask about the gaps.

1. `web/src/lib/reviews.ts`: `shown` for Accept, Modify to "No", and Modify to "1 year".
2. `web/src/hooks/useReviews.ts`: when a review shows on screen, and what happens on a 409.
3. `web/src/features/work/ReviewCard.tsx`: the three editor kinds, and where the focus goes after a save.
4. `web/src/features/work/CostFooter.tsx`: the backup plan when the clipboard is refused.
5. `web/e2e/fixtures.py`: `export` and `seed`, and why seeding is needed for reviews.
6. `web/playwright.config.ts`: what is real and what is replayed; why the fake key.
7. `web/e2e/review.spec.ts`: one step of the test, and the user action it stands for.

## Conclusion

The product loop is complete: pick, stream, read, look at the PDF, review, pass, copy. Go back through the objectives
and check each one without notes. Then answer:

1. The pill says "Passed". What did a person do, and what does it **not** promise about the model's answers?
2. The e2e test is green, but the model changed its answers last week. Which part of the app could break that the e2e
   test cannot see?

Looking for more challenges? Try these (optional):

1. Add `GET /v1/requests/{request_id}/reviews`, and load the reviews when an answer opens, so a reload keeps them.
2. Add a third e2e test: a 415 upload shows the error card, and "Try again" works.

Checklist (`../PLAN.md`): **Human-in-the-loop** (Accept, Modify and Undo, saved by the API, with Passed only when every
flag has a decision). **Prod bar: API + UI, a 2-min video** (the demo video stands in for the public URL). **Tests**
(one e2e test on a stored answer, with no model call). Next: Phase 5, the write-up.
