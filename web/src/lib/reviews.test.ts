// Reviews on the real Kubient answer (fixtures/kubient-stream.json): 2 flagged fields, non_compete and renewal_term.

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { pill, rows, start, next } from "./analysis.ts";
import type { ExtractResult, FieldInfo, ReviewSaved, StreamEvent } from "./api.ts";
import { kindOf, parseValue, pending, reasonFor, reviewedAnswer, type Reviews } from "./reviews.ts";

const events: StreamEvent[] = JSON.parse(
  readFileSync(new URL("../fixtures/kubient-stream.json", import.meta.url), "utf8"),
);
const result = (events.at(-1) as { data: ExtractResult }).data;
const GROUP: Record<string, string> = { non_compete: "Yes or no", parties: "Basic facts" };
const FIELDS: FieldInfo[] = Object.keys(result.fields).map((name) => ({ name, label: name, group: GROUP[name] ?? "Terms" }));

const review = (field: string, action: "accept" | "modify", value: ReviewSaved["new"]): ReviewSaved => ({
  review_id: `r-${field}`,
  field,
  action,
  old: result.fields[field].value,
  new: action === "accept" ? result.fields[field].value : value,
});

test("pending lists the flagged fields with no review, in field order", () => {
  assert.deepEqual(pending(result, FIELDS, {}), ["non_compete", "renewal_term"]);
  assert.deepEqual(pending(result, FIELDS, { non_compete: review("non_compete", "accept", null) }), ["renewal_term"]);
});

test("the pill says Passed once every flag has a review, and undo brings the issue back", () => {
  const done = events.reduce(next, start(12));
  const both: Reviews = {
    non_compete: review("non_compete", "accept", null),
    renewal_term: review("renewal_term", "accept", null),
  };
  assert.deepEqual(pill(done, true, both), { kind: "ok", text: "Passed", stage: "2 reviewed" });
  const { renewal_term: _undone, ...one } = both;
  assert.equal(pill(done, true, one).text, "1 issue found");
});

test("modify changes the row; a yes or no field set to No becomes not found", () => {
  const byName = (r: Reviews) => Object.fromEntries(rows(result, FIELDS, r).map((x) => [x.name, x]));
  const no = byName({ non_compete: review("non_compete", "modify", "No") });
  assert.deepEqual([no.non_compete.icon, no.non_compete.text, no.non_compete.reviewed], ["no", "Not in this contract", true]);
  const renewal = byName({ renewal_term: review("renewal_term", "modify", "1 year") });
  assert.deepEqual([renewal.renewal_term.icon, renewal.renewal_term.text], ["ok", "1 year"]);
});

test("Copy JSON keeps each review next to the new value", () => {
  const out = reviewedAnswer(result, { renewal_term: review("renewal_term", "modify", "1 year") });
  assert.equal(out.request_id, result.request_id);
  assert.deepEqual(out.fields.renewal_term, {
    found: true,
    value: "1 year",
    quotes: [],
    review: review("renewal_term", "modify", "1 year"),
  });
  assert.equal(out.fields.parties.review, null);
});

test("the editor kind and its value", () => {
  assert.equal(kindOf(FIELDS.find((f) => f.name === "non_compete")!, result.fields.non_compete), "yesno");
  assert.equal(kindOf(FIELDS.find((f) => f.name === "parties")!, result.fields.parties), "list");
  assert.deepEqual(parseValue("list", " Kubient, Inc.\n\nThe Associated Press "), ["Kubient, Inc.", "The Associated Press"]);
});

test("every flag on the real answer has a plain reason", () => {
  for (const name of ["non_compete", "renewal_term"]) {
    for (const issue of result.fields[name].issues) {
      assert.notEqual(reasonFor(issue, name).title, "A rule flagged this field.");
    }
  }
});
