import { Check, X } from "lucide-react";
import type { ReactNode } from "react";
import type { Pill } from "../analysis.ts";

const LOOK = {
  busy: "ring-busy bg-base-100",
  warn: "bg-warning/10 border-warning/50 text-warning",
  ok: "bg-success/10 border-success/50 text-success",
  error: "bg-error/10 border-error/50 text-error",
};

/** The pill under the card: Analyzing (with the stage), N issues found, or Passed. */
export function StatusPill({ pill }: { pill: Pill }) {
  return (
    <div className="absolute -bottom-[21px] left-1/2 z-10 -translate-x-1/2">
      <div
        role="status"
        aria-live="polite"
        key={pill.kind} // a new kind pops in
        className={`pop inline-flex items-center gap-2 rounded-full border border-base-300 px-[18px] py-2 text-[14.5px] font-semibold whitespace-nowrap shadow-lg ${LOOK[pill.kind]}`}
      >
        {pill.kind === "ok" && <Icon className="bg-success text-success-content"><Check size={12} strokeWidth={3.5} /></Icon>}
        {pill.kind === "warn" && <Icon className="bg-warning text-warning-content">!</Icon>}
        {pill.kind === "error" && <Icon className="bg-error text-error-content"><X size={12} strokeWidth={3.5} /></Icon>}
        {pill.text}
        {pill.stage && <span className="text-[13px] font-medium text-base-content/50">· {pill.stage}</span>}
      </div>
    </div>
  );
}

function Icon({ className, children }: { className: string; children: ReactNode }) {
  return <span className={`grid size-5 place-items-center rounded-full text-[13px] font-bold ${className}`}>{children}</span>;
}
