import { Sparkles } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import type { FieldInfo, FieldResult, Value } from "../../lib/api.ts";
import { type FieldKind, parseValue, reasonFor } from "../../lib/reviews.ts";

type Props = {
  info: FieldInfo;
  f: FieldResult;
  kind: FieldKind;
  busy: boolean;
  error: string | null;
  autoFocus: boolean; // after a review, the next card takes the keyboard focus
  onAccept: () => void;
  onModify: (value: Value) => void;
  onShowEvidence: (index: number) => void;
};

/** The card under a "!" row: why it was flagged, the evidence, and Accept or Modify. */
export function ReviewCard({ info, f, kind, busy, error, autoFocus, onAccept, onModify, onShowEvidence }: Props) {
  const [editing, setEditing] = useState(false);
  const card = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (autoFocus) card.current?.focus();
  }, [autoFocus]);

  return (
    <div
      ref={card}
      tabIndex={-1}
      aria-label={`Review ${info.label}`}
      className="mx-3 mb-3 ml-[46px] grid gap-2.5 rounded-[14px] border border-base-300 bg-base-100 p-3.5 shadow-md outline-none focus-visible:ring-2 focus-visible:ring-primary"
    >
      <h4 className="flex items-center gap-2 text-sm font-semibold">
        <Sparkles size={16} className="text-primary" /> {editing ? "Change the answer" : "Needs a look"}
      </h4>

      {!editing &&
        f.issues.map((issue, i) => {
          const why = reasonFor(issue, info.label);
          return (
            <div key={i} className="grid gap-1">
              <p className="text-[13px] font-medium">{why.title}</p>
              <p className="text-[13px] text-base-content/70">{why.more}</p>
            </div>
          );
        })}

      {!editing &&
        f.evidence.map((line, i) => {
          const box = f.evidence_highlights.find((h) => h.quote_index === i);
          return (
            <button
              key={i}
              onClick={() => onShowEvidence(i)}
              className="border-l-2 border-warning py-0.5 pl-2.5 text-left text-[13px] text-base-content/70 hover:text-base-content"
            >
              “{line}”
              <span className="block text-xs text-base-content/50">
                {box ? `page ${box.page}, highlighted in amber` : "not found on the page"}
              </span>
            </button>
          );
        })}

      {editing ? (
        <Editor
          kind={kind}
          f={f}
          busy={busy}
          onCancel={() => setEditing(false)}
          onSave={(value) => onModify(value)}
        />
      ) : (
        <div className="flex flex-wrap gap-2">
          <button className="btn btn-sm btn-outline btn-primary" disabled={busy} onClick={() => setEditing(true)}>
            Modify
          </button>
          <button className="btn btn-sm btn-neutral" disabled={busy} onClick={onAccept}>
            {f.found ? "Accept" : "Keep “not found”"}
          </button>
        </div>
      )}

      {error && (
        <p role="alert" className="text-[13px] text-error">
          {error}
        </p>
      )}
    </div>
  );
}

type EditorProps = {
  kind: FieldKind;
  f: FieldResult;
  busy: boolean;
  onCancel: () => void;
  onSave: (value: Value) => void;
};

/** The Modify form. A yes or no field gets two buttons; a list gets one line per item; the rest one line. */
function Editor({ kind, f, busy, onCancel, onSave }: EditorProps) {
  const start = Array.isArray(f.value) ? f.value.join("\n") : (f.value ?? "");
  const [text, setText] = useState(start);
  const [yes, setYes] = useState(!f.found); // a flagged yes or no field is usually wrong, so start on the other side
  const value: Value = kind === "yesno" ? (yes ? "Yes" : "No") : parseValue(kind, text);
  const empty = kind !== "yesno" && (value === "" || (Array.isArray(value) && value.length === 0));

  return (
    <form
      className="grid gap-2"
      onSubmit={(e) => {
        e.preventDefault();
        if (!empty) onSave(value);
      }}
    >
      {kind === "yesno" ? (
        <div className="inline-flex w-max overflow-hidden rounded-lg border border-base-300" role="group" aria-label="Is the clause in the contract?">
          {[true, false].map((choice) => (
            <button
              key={String(choice)}
              type="button"
              aria-pressed={yes === choice}
              onClick={() => setYes(choice)}
              className={`px-3 py-1.5 text-[13px] ${yes === choice ? "bg-primary/10 font-medium text-primary" : "text-base-content/70"}`}
            >
              {choice ? "Yes, it is there" : "No"}
            </button>
          ))}
        </div>
      ) : kind === "list" ? (
        <label className="grid gap-1 text-xs text-base-content/60">
          One name per line
          <textarea className="textarea textarea-sm w-full" rows={3} value={text} onChange={(e) => setText(e.target.value)} />
        </label>
      ) : (
        <label className="grid gap-1 text-xs text-base-content/60">
          The right value
          <input className="input input-sm w-full" value={text} onChange={(e) => setText(e.target.value)} />
        </label>
      )}
      <div className="flex gap-2">
        <button type="submit" className="btn btn-sm btn-neutral" disabled={busy || empty}>
          Save
        </button>
        <button type="button" className="btn btn-sm btn-ghost" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </form>
  );
}
