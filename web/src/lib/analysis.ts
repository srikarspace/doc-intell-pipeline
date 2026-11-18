// What the analyze card shows, as plain functions with no React and no fetch.
// So the test can feed in real events and check the result, without a browser.

import type { ExtractResult, FieldInfo, FieldResult, StreamEvent } from "./api.ts";
import { type Reviews, shown } from "./reviews.ts";

export type Analysis = {
  phase: "running" | "done" | "failed";
  stage: string; // the words on the pill while it runs
  fieldCount: number;
  pages: number | null;
  result: ExtractResult | null;
  error: { status: number; detail: string } | null;
};

export function start(fieldCount: number): Analysis {
  return { phase: "running", stage: "Sending the PDF", fieldCount, pages: null, result: null, error: null };
}

const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? "" : "s"}`;

/** One event in, the new state out. It never changes the old state. */
export function next(state: Analysis, e: StreamEvent): Analysis {
  switch (e.event) {
    case "stage":
      if (e.data.name === "parse" && e.data.status === "start") return { ...state, stage: "Reading the PDF" };
      if (e.data.name === "parse") return { ...state, pages: e.data.pages ?? null };
      if (e.data.name === "extract") return { ...state, stage: `Finding ${plural(state.fieldCount, "field")}` };
      return { ...state, stage: "Checking every quote" };
    case "attempt":
      // An attempt with errors means the model is asked again, with the errors.
      if (e.data.errors === 0) return state;
      return { ...state, stage: `Fixing ${plural(e.data.errors, "problem")}, try ${e.data.n + 2}` };
    case "result":
      return { ...state, phase: "done", stage: "", pages: e.data.pages, result: e.data };
    case "error":
      return { ...state, phase: "failed", stage: "", error: e.data };
  }
}

export type Pill = { kind: "busy" | "warn" | "ok" | "error"; text: string; stage?: string };

/**
 * The pill under the card. Rows show one by one after the result, so wait for the last one.
 * Then count the flagged fields that have no review yet.
 */
export function pill(state: Analysis, allShown: boolean, reviews: Reviews = {}): Pill {
  if (state.phase === "failed") return { kind: "error", text: "Something went wrong" };
  if (state.phase === "running" || !allShown) return { kind: "busy", text: "Analyzing", stage: state.stage || undefined };
  const fields = state.result!.fields;
  const open = Object.keys(fields).filter((name) => fields[name].needs_review && !reviews[name]).length;
  if (open) return { kind: "warn", text: `${plural(open, "issue")} found`, stage: "click to review" };
  const done = Object.keys(reviews).length;
  return { kind: "ok", text: "Passed", stage: done ? `${done} reviewed` : undefined };
}

export type Row = {
  name: string;
  label: string;
  icon: "ok" | "no" | "warn";
  text: string;
  none: boolean; // "Not in this contract": shown in a lighter color
  page: number | null; // the page of the first quote
  reviewed: boolean;
};

function valueText(f: Pick<FieldResult, "found" | "value" | "quotes">): string {
  if (!f.found) return "Not in this contract";
  if (Array.isArray(f.value)) return f.value.join("; ");
  if (f.value) return f.value;
  return f.quotes[0] ? `Yes · "${f.quotes[0]}"` : "Yes"; // a yes or no field has no value
}

/** One row per chosen field, in the order of `GET /v1/fields` (the schema order). A review changes the row. */
export function rows(result: ExtractResult, fields: FieldInfo[], reviews: Reviews = {}): Row[] {
  return fields
    .filter((info) => info.name in result.fields)
    .map((info) => {
      const f = result.fields[info.name];
      const review = reviews[info.name];
      const s = shown(f, review);
      return {
        name: info.name,
        label: info.label,
        icon: f.needs_review && !review ? "warn" : s.found ? "ok" : "no",
        text: valueText(s),
        none: !s.found,
        page: s.quotes.length ? (f.highlights[0]?.page ?? null) : null,
        reviewed: Boolean(review),
      };
    });
}

/** "Non_Compete_Non_Solicit" -> "Non compete non solicit" */
export const prettyType = (t: string) =>
  t.replace(/_/g, " ").toLowerCase().replace(/^./, (c) => c.toUpperCase());
