// PDF points -> CSS pixels. The API gives each line box in PDF points, measured from the bottom-left corner of
// the page. The browser measures from the top-left, in pixels of the drawn page.

import type { FieldResult, Highlight } from "./api.ts";

/** Which box the user looks at: a quote of the field, or an evidence line of a "maybe missed" flag. */
export type Focus = { field: string; kind: "quote" | "evidence"; index: number };

/** One highlight to draw on the PDF. Quotes use the accent color, evidence uses amber. */
export type Mark = { highlight: Highlight; kind: "quote" | "evidence"; focused: boolean };

/** The first thing to show for a field: its first quote, or its evidence line when it has no quote boxes. */
export function firstFocus(field: string, f: FieldResult, flagged: boolean): Focus {
  if (flagged && f.evidence_highlights.length && !f.highlights.length) return { field, kind: "evidence", index: 0 };
  return { field, kind: "quote", index: 0 };
}

/** The boxes to draw for one open field. A modified field has no quote, so no quote boxes. */
export function marksFor(f: FieldResult, focus: Focus | null, opts: { quotes: boolean; evidence: boolean }): Mark[] {
  const is = (kind: Mark["kind"], h: Highlight) => focus?.kind === kind && focus.index === h.quote_index;
  const quotes = opts.quotes ? f.highlights.map((h) => ({ highlight: h, kind: "quote" as const, focused: is("quote", h) })) : [];
  const evidence = opts.evidence
    ? f.evidence_highlights.map((h) => ({ highlight: h, kind: "evidence" as const, focused: is("evidence", h) }))
    : [];
  return [...quotes, ...evidence];
}

export type Box = { left: number; top: number; width: number; height: number }; // CSS px on the drawn page

const PAD = 2; // a little room around the text, so the box does not touch the letters
const round = (n: number) => Math.round(n * 10) / 10;

/** The boxes of one highlight, for a page drawn `pageWidth` pixels wide. */
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
