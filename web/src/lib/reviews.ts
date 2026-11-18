// Reviews as plain functions: what a field shows after a review, what is still open, why a field was flagged,
// and the reviewed answer for Copy JSON. No React, no fetch, so the test can check them.

import type { ExtractResult, FieldInfo, FieldResult, Issue, ReviewSaved, Value } from "./api.ts";

export type Reviews = Record<string, ReviewSaved>; // field name -> its saved review

export type FieldKind = "yesno" | "list" | "text";

const YES_OR_NO_GROUP = "Yes or no"; // the group name from api/fields.py

/** How the Modify editor asks for a new value. */
export function kindOf(info: FieldInfo, f: FieldResult): FieldKind {
  if (info.group === YES_OR_NO_GROUP) return "yesno";
  if (Array.isArray(f.value)) return "list";
  return "text";
}

/** What a field shows after its review. Accept keeps the answer. Modify replaces it, with no quote. */
export function shown(f: FieldResult, review: ReviewSaved | undefined): Pick<FieldResult, "found" | "value" | "quotes"> {
  if (!review || review.action === "accept") return f;
  if (review.new === "No") return { found: false, value: null, quotes: [] };
  return { found: true, value: review.new === "Yes" ? null : review.new, quotes: [] };
}

/** The flagged fields with no review yet, in the order of the field list. */
export function pending(result: ExtractResult, fields: FieldInfo[], reviews: Reviews): string[] {
  return fields.map((f) => f.name).filter((name) => result.fields[name]?.needs_review && !reviews[name]);
}

/** Why a field was flagged, in plain words: a short title and one line more. */
export function reasonFor(issue: Issue, label: string): { title: string; more: string } {
  const field = label.toLowerCase();
  switch (issue.rule) {
    case "maybe_missed":
      return {
        title: "The model said “not found”, but the contract may have it.",
        more: `This line has words that often mean a ${field} clause. Read it, then keep “not found” or change it.`,
      };
    case "quote_off_topic":
      return {
        title: "The quote may be about something else.",
        more: `A ${field} quote usually has words about ${field}. This quote has none of them.`,
      };
    case "quote_missing":
      return {
        title: "This quote is not in the contract text.",
        more: "The model changed some words when it copied the text. The answer itself may still be right.",
      };
    case "quote_gap":
      return { title: "The quote is split.", more: "Its words are in the contract, but not side by side." };
    case "quote_no_words":
      return { title: "The quote has no words to check.", more: "It may be only numbers or symbols." };
    case "bad_date":
      return { title: "This is not a real date.", more: `The model wrote “${issue.detail}”. Check the date in the contract.` };
    case "found_no_quote":
    case "found_no_value":
    case "quote_not_found":
    case "value_not_found":
      return { title: "The answer does not agree with itself.", more: `${issue.detail}.` };
    default:
      return { title: "A rule flagged this field.", more: `${issue.rule}: ${issue.detail}` };
  }
}

/** The answer after the reviews: what Copy JSON gives. Each field keeps its review, so the change can be traced. */
export function reviewedAnswer(result: ExtractResult, reviews: Reviews) {
  const fields: Record<string, { found: boolean; value: Value; quotes: string[]; review: ReviewSaved | null }> = {};
  for (const [name, f] of Object.entries(result.fields)) {
    const s = shown(f, reviews[name]);
    fields[name] = { found: s.found, value: s.value, quotes: s.quotes, review: reviews[name] ?? null };
  }
  return { request_id: result.request_id, document: result.document, fields };
}

/** The editor's text -> the value to send. A list takes one item per line. */
export function parseValue(kind: FieldKind, text: string): Value {
  if (kind === "list") return text.split("\n").map((line) => line.trim()).filter(Boolean);
  return text.trim();
}
