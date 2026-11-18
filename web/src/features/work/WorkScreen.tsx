import { ChevronLeft } from "lucide-react";
import { lazy, Suspense, useEffect, useState } from "react";
import type { Job } from "../../hooks/useAnalysis.ts";
import { useReveal } from "../../hooks/useReveal.ts";
import { useReviews } from "../../hooks/useReviews.ts";
import { type Analysis, pill, rows } from "../../lib/analysis.ts";
import type { FieldInfo, Value } from "../../lib/api.ts";
import { type Focus, firstFocus, marksFor } from "../../lib/boxes.ts";
import { kindOf, pending, type Reviews, reviewedAnswer, shown } from "../../lib/reviews.ts";
import { AnalyzeCard } from "./AnalyzeCard.tsx";
import { CostFooter } from "./CostFooter.tsx";
import { FieldDetail } from "./FieldDetail.tsx";
import { ReviewCard } from "./ReviewCard.tsx";

const PdfPane = lazy(() => import("./PdfPane.tsx")); // pdf.js loads only when a result is shown

type Props = {
  job: Job;
  analysis: Analysis;
  allFields: FieldInfo[];
  onNew: () => void;
  onRetry: () => void;
};

/**
 * The card, and the PDF next to it once the answers are in.
 * It owns which row is open, which box is in focus, and the reviews of this answer.
 */
export function WorkScreen({ job, analysis, allFields, onNew, onRetry }: Props) {
  const fields = allFields.filter((f) => job.fields.includes(f.name));
  const result = analysis.result;
  const [open, setOpen] = useState<string | null>(null);
  const [focus, setFocus] = useState<Focus | null>(null);
  const [clicks, setClicks] = useState(0); // every click on a row or a quote: scroll and pulse again
  const [moved, setMoved] = useState(false); // the keyboard focus moved into a review card after a review

  const openField = (name: string | null, reviews: Reviews) => {
    setOpen(name);
    setClicks((c) => c + 1);
    if (!name || !result) return setFocus(null);
    const f = result.fields[name];
    setFocus(firstFocus(name, f, f.needs_review && !reviews[name]));
  };

  // After a save, open the next flagged field, and move the keyboard there.
  const { reviews, save, undo, errorFor, busy } = useReviews((after) => {
    const nextOne = result && pending(result, fields, after)[0];
    setMoved(Boolean(nextOne));
    openField(nextOne ?? open, after);
  });

  const all = result ? rows(result, fields, reviews) : [];
  const shownCount = useReveal(analysis.phase === "done" ? all.length : 0);
  const ready = Boolean(result) && shownCount >= all.length;

  // When the last row shows, open the first flagged field (or the first found one).
  useEffect(() => {
    if (!ready || !result) return;
    const first = pending(result, fields, {})[0] ?? fields.find((f) => result.fields[f.name]?.found)?.name ?? null;
    openField(first, {});
  }, [ready]); // only when `ready` turns true; the other values are read at that moment

  const toggle = (name: string) => {
    setMoved(false);
    openField(open === name ? null : name, reviews);
  };

  const focusOn = (f: Focus) => {
    setFocus(f);
    setClicks((c) => c + 1);
  };

  const detail = (name: string) => {
    if (!result) return null;
    const info = fields.find((f) => f.name === name)!;
    const f = result.fields[name];
    const review = reviews[name];
    return (
      <FieldDetail
        info={info}
        f={f}
        review={review}
        focus={focus}
        onFocus={focusOn}
        onUndo={() => review && undo.mutate(review)}
        busy={busy}
        error={review ? errorFor(name) : null}
      >
        {f.needs_review && !review && (
          <ReviewCard
            info={info}
            f={f}
            kind={kindOf(info, f)}
            busy={busy}
            error={errorFor(name)}
            autoFocus={moved}
            onAccept={() => save.mutate({ request_id: result.request_id, field: name, action: "accept" })}
            onModify={(value: Value) => save.mutate({ request_id: result.request_id, field: name, action: "modify", value })}
            onShowEvidence={(index) => focusOn({ field: name, kind: "evidence", index })}
          />
        )}
      </FieldDetail>
    );
  };

  const openResult = open && result ? result.fields[open] : null;
  const marks =
    openResult && open
      ? marksFor(openResult, focus, {
          quotes: shown(openResult, reviews[open]).quotes.length > 0,
          evidence: openResult.needs_review && !reviews[open],
        })
      : [];
  const thePill = pill(analysis, ready || !result, reviews);
  const firstOpen = result ? pending(result, fields, reviews)[0] : undefined;

  return (
    <main
      className={`mx-auto mt-4 grid gap-x-5 gap-y-10 min-[920px]:gap-y-5 ${
        ready ? "max-w-[1240px] min-[920px]:grid-cols-[minmax(0,470px)_minmax(0,1fr)]" : "max-w-[720px]"
      }`}
    >
      <div className="col-span-full">
        <button className="btn-quiet" onClick={onNew}>
          <ChevronLeft size={14} /> New contract
        </button>
      </div>

      <AnalyzeCard
        title={job.title}
        subtitle={job.subtitle}
        analysis={analysis}
        fields={fields}
        rows={all}
        shownCount={shownCount}
        open={open}
        pill={thePill}
        onPill={firstOpen ? () => openField(firstOpen, reviews) : undefined}
        onToggle={toggle}
        onRetry={onRetry}
        detail={detail}
        footer={result && ready ? <CostFooter result={result} json={() => reviewedAnswer(result, reviews)} /> : null}
      />

      {ready && result && (
        <Suspense fallback={<div className="skeleton h-[70vh] rounded-2xl" />}>
          <PdfPane
            file={job.pdf}
            name={result.document.filename}
            marks={marks}
            pulseKey={`${open}-${clicks}`}
            scan={result.parser !== "pypdf"}
          />
        </Suspense>
      )}
    </main>
  );
}
