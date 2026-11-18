import { Check, Minus, RotateCcw } from "lucide-react";
import { useEffect, useState } from "react";
import { type Analysis, pill, rows } from "../analysis.ts";
import type { FieldInfo } from "../api.ts";
import { StatusPill } from "./StatusPill.tsx";

const REVEAL_MS = 140; // the gap between two rows
const reducedMotion = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;

type Props = {
  title: string;
  subtitle: string;
  analysis: Analysis;
  fields: FieldInfo[]; // the chosen fields, in schema order
  onRetry: () => void;
};

/** The work card: skeleton rows while it runs, then the answers one by one, then the pill. */
export function AnalyzeCard({ title, subtitle, analysis, fields, onRetry }: Props) {
  const all = analysis.result ? rows(analysis.result, fields) : [];
  const shown = useReveal(analysis.phase === "done" ? all.length : 0);
  const allShown = shown >= all.length;
  const result = analysis.result;

  return (
    <article className="relative rounded-[20px] border border-base-300 bg-base-100 shadow-[0_1px_2px_rgba(20,22,40,.05),0_12px_40px_rgba(20,22,40,.08)]">
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
          {fields.map((f, i) => {
            const row = i < shown ? all[i] : null;
            return (
              <li
                key={f.name}
                className={`grid grid-cols-[22px_minmax(0,1fr)_auto] items-center gap-3 rounded-xl px-3 py-2.5 ${
                  row?.icon === "warn" ? "bg-warning/10" : ""
                }`}
              >
                {row ? <RowIcon icon={row.icon} /> : <span className="skeleton size-[22px] rounded-md" />}
                <span className="min-w-0">
                  <div className="text-xs leading-tight text-base-content/50">{f.label}</div>
                  {row ? (
                    <div className={`truncate text-sm ${row.none ? "text-base-content/50" : ""}`}>{row.text}</div>
                  ) : (
                    <div className="skeleton mt-1.5 h-2.5" style={{ width: `${45 + ((f.name.length * 7) % 45)}%` }} />
                  )}
                </span>
                <span>
                  {row?.page && (
                    <span className="rounded-md border border-base-300 px-1.5 py-px font-mono text-[11.5px] text-base-content/50">
                      p. {row.page}
                    </span>
                  )}
                </span>
              </li>
            );
          })}
        </ul>
      )}

      {result && allShown && (
        <footer className="flex flex-wrap items-center gap-2 border-t border-base-300 px-[22px] pt-3.5 pb-[34px] font-mono text-xs text-base-content/50">
          <span>{result.parser}</span>·<span>{result.pages} pages</span>·<span>${result.cost_usd.toFixed(4)}</span>·
          <span>{(result.latency_ms / 1000).toFixed(1)} s</span>
        </footer>
      )}

      <StatusPill pill={pill(analysis, allShown)} />
    </article>
  );
}

function RowIcon({ icon }: { icon: "ok" | "no" | "warn" }) {
  const look = {
    ok: "bg-success text-success-content",
    no: "bg-base-300 text-base-content/70",
    warn: "bg-warning text-warning-content",
  }[icon];
  return (
    <span className={`pop grid size-[22px] place-items-center rounded-full text-[13px] font-bold ${look}`}>
      {icon === "ok" && <Check size={13} strokeWidth={3.2} />}
      {icon === "no" && <Minus size={12} strokeWidth={3} />}
      {icon === "warn" && "!"}
    </span>
  );
}

/** Counts from 0 up to `total`, one step every REVEAL_MS. Starts again at 0 when `total` is 0. */
function useReveal(total: number): number {
  const [shown, setShown] = useState(0);
  useEffect(() => {
    if (total === 0) return setShown(0);
    if (reducedMotion()) return setShown(total);
    const timer = setInterval(() => {
      setShown((n) => {
        if (n + 1 >= total) clearInterval(timer);
        return Math.min(n + 1, total);
      });
    }, REVEAL_MS);
    return () => clearInterval(timer);
  }, [total]);
  return shown;
}
