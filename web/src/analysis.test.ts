// The one test file for 4c. It runs with Node's own test runner: `npm test` (or `make web-test`).
// The events come from one real stream of the Kubient sample, saved in fixtures/.

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { type Analysis, next, pill, rows, start } from "./analysis.ts";
import type { ExtractResult, FieldInfo, StreamEvent } from "./api.ts";

const events: StreamEvent[] = JSON.parse(
  readFileSync(new URL("./fixtures/kubient-stream.json", import.meta.url), "utf8"),
);
const result = (events.at(-1) as { data: ExtractResult }).data;
const FIELDS: FieldInfo[] = Object.keys(result.fields).map((name) => ({ name, label: name, group: "g" }));

/** Every state, from the start to the end. */
function replay(list: StreamEvent[], fieldCount = 12): Analysis[] {
  const states = [start(fieldCount)];
  for (const e of list) states.push(next(states.at(-1)!, e));
  return states;
}

test("the pill shows the real stages, in order", () => {
  const stages = replay(events).map((s) => pill(s, false).stage ?? "");
  assert.deepEqual(stages, [
    "Sending the PDF",
    "Reading the PDF",
    "Reading the PDF", // parse done: only the page count changes
    "Finding 12 fields",
    "Finding 12 fields", // an attempt with no errors changes nothing
    "Checking every quote",
    "", // the result: the rows start to show
  ]);
});

test("a retry says how many problems the model must fix", () => {
  const retry: StreamEvent[] = [
    { event: "stage", data: { name: "extract", status: "start" } },
    { event: "attempt", data: { n: 0, errors: 2 } },
    { event: "attempt", data: { n: 1, errors: 0 } },
  ];
  assert.deepEqual(
    replay(retry, 3).map((s) => s.stage),
    ["Sending the PDF", "Finding 3 fields", "Fixing 2 problems, try 2", "Fixing 2 problems, try 2"],
  );
});

test("the pill waits for the last row, then counts the flagged fields", () => {
  const done = replay(events).at(-1)!;
  assert.equal(pill(done, false).text, "Analyzing");
  assert.deepEqual(pill(done, true), { kind: "warn", text: "2 issues found" }); // non_compete, renewal_term

  const clean = structuredClone(done);
  Object.values(clean.result!.fields).forEach((f) => (f.needs_review = false));
  assert.deepEqual(pill(clean, true), { kind: "ok", text: "Passed" });
});

test("an error event ends the run, with the server's words", () => {
  const failed = next(start(12), { event: "error", data: { status: 504, detail: "no answer within 240 s" } });
  assert.equal(failed.phase, "failed");
  assert.equal(failed.error?.detail, "no answer within 240 s");
  assert.equal(pill(failed, true).kind, "error");
});

test("rows follow the field list order, and show found, not found and flagged", () => {
  const reversed = [...FIELDS].reverse();
  assert.deepEqual(
    rows(result, reversed).map((r) => r.name),
    reversed.map((f) => f.name),
  );
  const byName = Object.fromEntries(rows(result, FIELDS).map((r) => [r.name, r]));
  assert.equal(byName.parties.icon, "ok");
  assert.equal(byName.parties.page, 1);
  assert.equal(byName.governing_law.text, "Not in this contract");
  assert.equal(byName.non_compete.icon, "warn");
});
