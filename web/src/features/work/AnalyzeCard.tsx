import { RotateCcw } from "lucide-react";
import type { ReactNode } from "react";
import type { Analysis, Pill, Row } from "../../lib/analysis.ts";
import type { FieldInfo } from "../../lib/api.ts";
import { FieldRow } from "./FieldRow.tsx";
import { StatusPill } from "./StatusPill.tsx";

type Props = {
  title: string;
  subtitle: string;
  analysis: Analysis;
  fields: FieldInfo[]; // the chosen fields, in schema order
  rows: Row[];
  shownCount: number; // rows show one by one; the rest are skeletons
  open: string | null;
  pill: Pill;
  onPill?: () => void;
  onToggle: (field: string) => void;
  onRetry: () => void;
  detail: (field: string) => ReactNode; // what opens under a row
  footer: ReactNode;
};

/** The work card: a header, one row per field (skeletons first), an error or a footer, and the pill. */
export function AnalyzeCard(props: Props) {
  const { title, subtitle, analysis, fields, rows, shownCount, open, pill, onPill, onToggle, onRetry, detail, footer } = props;

  return (
    <article className="relative self-start rounded-[20px] border border-base-300 bg-base-100 shadow-[0_1px_2px_rgba(20,22,40,.05),0_12px_40px_rgba(20,22,40,.08)]">
      <header className="flex flex-wrap items-baseline gap-2.5 border-b border-base-300 px-[22px] py-[18px]">
        <h2 className="text-[17px] font-semibold tracking-tight">{title}</h2>
        <span className="size-1 self-center rounded-full bg-base-content/40" />
        <span className="text-base-content/50">{subtitle}</span>
        {analysis.pages !== null && (
          <span className="ml-auto font-mono text-xs text-base-content/50">{analysis.pages} pages</span>
        )}
      </header>

      {analysis.phase === "failed" ? (
        <div className="px-[22px] pt-5 pb-12">
          <div role="alert" className="flex flex-wrap items-center gap-3 rounded-xl bg-error/10 px-4 py-3 text-error">
            <div className="mr-auto">
              <div className="font-semibold">{analysis.error!.detail}</div>
              <div className="font-mono text-xs opacity-70">
                {analysis.error!.status ? `HTTP ${analysis.error!.status}` : "no answer from the API"}
              </div>
            </div>
            <button className="btn-quiet" onClick={onRetry}>
              <RotateCcw size={14} /> Try again
            </button>
          </div>
        </div>
      ) : (
        <ul className="grid gap-0.5 px-2.5 pt-2 pb-9">
          {fields.map((info, i) => {
            const row = i < shownCount ? rows[i] : null;
            return (
              <FieldRow key={info.name} info={info} row={row} open={open === info.name} onToggle={() => onToggle(info.name)}>
                {row && detail(info.name)}
              </FieldRow>
            );
          })}
        </ul>
      )}

      {footer}
      <StatusPill pill={pill} onClick={onPill} />
    </article>
  );
}
