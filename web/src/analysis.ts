// What the analyze card shows, as plain functions with no React and no fetch.
// So the test can feed in real events and check the result, without a browser.

import type { ExtractResult, FieldInfo, FieldResult, StreamEvent } from "./api.ts";

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

/** The pill under the card. Rows show one by one after the result, so wait for the last one. */
export function pill(state: Analysis, allShown: boolean): Pill {
  if (state.phase === "failed") return { kind: "error", text: "Something went wrong" };
  if (state.phase === "running" || !allShown) return { kind: "busy", text: "Analyzing", stage: state.stage || undefined };
  const flagged = Object.values(state.result!.fields).filter((f) => f.needs_review).length;
  if (flagged) return { kind: "warn", text: `${plural(flagged, "issue")} found` };
  return { kind: "ok", text: "Passed" };
}

export type Row = {
  name: string;
  label: string;
  icon: "ok" | "no" | "warn";
  text: string;
  none: boolean; // "Not in this contract": shown in a lighter color
  page: number | null; // the page of the first quote
};

function valueText(f: FieldResult): string {
  if (!f.found) return "Not in this contract";
  if (Array.isArray(f.value)) return f.value.join("; ");
  if (f.value) return f.value;
  return f.quotes[0] ? `Yes · "${f.quotes[0]}"` : "Yes"; // a yes or no field has no value
}

/** One row per chosen field, in the order of `GET /v1/fields` (the schema order). */
export function rows(result: ExtractResult, fields: FieldInfo[]): Row[] {
  return fields
    .filter((info) => info.name in result.fields)
    .map((info) => {
      const f = result.fields[info.name];
      return {
        name: info.name,
        label: info.label,
        icon: f.needs_review ? "warn" : f.found ? "ok" : "no",
        text: valueText(f),
        none: !f.found,
        page: f.highlights[0]?.page ?? null,
      };
    });
}

/** "Non_Compete_Non_Solicit" -> "Non compete non solicit" */
export const prettyType = (t: string) =>
  t.replace(/_/g, " ").toLowerCase().replace(/^./, (c) => c.toUpperCase());
