import type { ReactNode } from "react";
import type { FieldInfo, FieldResult, ReviewSaved } from "../../lib/api.ts";
import type { Focus } from "../../lib/boxes.ts";
import { shown } from "../../lib/reviews.ts";

type Props = {
  info: FieldInfo;
  f: FieldResult;
  review: ReviewSaved | undefined;
  focus: Focus | null;
  onFocus: (focus: Focus) => void;
  onUndo: () => void;
  busy: boolean;
  error: string | null;
  children?: ReactNode; // the review card, for a flagged field with no review
};

/** What opens under a row: each quote (click it to jump in the PDF), the review card, or the review and Undo. */
export function FieldDetail({ info, f, review, focus, onFocus, onUndo, busy, error, children }: Props) {
  const s = shown(f, review);
  const empty = !s.quotes.length && !f.needs_review && !review;

  return (
    <div className="grid gap-2.5 pb-3">
      {s.quotes.length > 0 && (
        <div className="mx-3 ml-[46px] grid gap-2">
          {s.quotes.map((quote, i) => {
            const box = f.highlights.find((h) => h.quote_index === i);
            const on = focus?.field === info.name && focus.kind === "quote" && focus.index === i;
            return (
              <button
                key={i}
                onClick={() => onFocus({ field: info.name, kind: "quote", index: i })}
                aria-pressed={on}
                title="Show in the PDF"
                className={`border-l-2 py-0.5 pl-2.5 text-left text-[13px] hover:text-base-content ${
                  on ? "border-primary text-base-content" : "border-primary/50 text-base-content/70"
                }`}
              >
                “{quote}”
                <span className="block text-xs text-base-content/50">
                  {box ? `page ${box.page}` : "not found on the page"}
                </span>
              </button>
            );
          })}
        </div>
      )}

      {empty && (
        <p className="mx-3 ml-[46px] text-[12.5px] text-base-content/50">
          The model found no {info.label.toLowerCase()} in this contract.
        </p>
      )}

      {children}

      {review && (
        <p className="mx-3 ml-[46px] text-[12.5px] text-base-content/60">
          {review.action === "accept"
            ? f.found
              ? "You accepted this answer."
              : "You kept “not found”."
            : "You changed this answer."}{" "}
          <button className="link link-primary" disabled={busy} onClick={onUndo}>
            Undo
          </button>
          {error && (
            <span role="alert" className="block text-error">
              {error}
            </span>
          )}
        </p>
      )}
    </div>
  );
}
