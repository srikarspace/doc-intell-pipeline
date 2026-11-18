import { Check, Minus } from "lucide-react";
import type { KeyboardEvent, ReactNode } from "react";
import type { Row } from "../../lib/analysis.ts";
import type { FieldInfo } from "../../lib/api.ts";

type Props = {
  info: FieldInfo;
  row: Row | null; // null: not shown yet, so a skeleton
  open: boolean;
  onToggle: () => void;
  children?: ReactNode; // the detail, when open
};

/** One field: its icon, label, value and page. Click it (or press Enter) to open its detail. */
export function FieldRow({ info, row, open, onToggle, children }: Props) {
  const flagged = row?.icon === "warn";
  return (
    <li className={`rounded-xl transition-colors ${flagged ? "bg-warning/10" : open ? "bg-base-200" : ""}`}>
      <button
        data-row
        disabled={!row}
        aria-expanded={open}
        onClick={onToggle}
        onKeyDown={moveFocus}
        className="grid w-full grid-cols-[22px_minmax(0,1fr)_auto] items-center gap-3 rounded-xl px-3 py-2.5 text-left enabled:hover:bg-base-content/5"
      >
        {row ? <RowIcon icon={row.icon} /> : <span aria-hidden className="skeleton size-[22px] rounded-md" />}
        <span className="min-w-0">
          <span className="block text-xs leading-tight text-base-content/50">{info.label}</span>
          {row ? (
            <span className={`block truncate text-sm ${row.none ? "text-base-content/50" : ""}`}>{row.text}</span>
          ) : (
            <span className="skeleton mt-1.5 block h-2.5" style={{ width: `${45 + ((info.name.length * 7) % 45)}%` }} />
          )}
        </span>
        <span>
          {row?.reviewed ? (
            <span className="rounded-md border border-primary/40 px-1.5 py-px text-[11px] text-primary">reviewed</span>
          ) : (
            row?.page && (
              <span className="rounded-md border border-base-300 px-1.5 py-px font-mono text-[11.5px] text-base-content/50">
                p. {row.page}
              </span>
            )
          )}
          {row && <span className="sr-only">{SPOKEN[row.icon]}</span>}
        </span>
      </button>
      {open && children}
    </li>
  );
}

// The icons are pictures; a screen reader says these words instead, after the value.
const SPOKEN = { ok: ", found", no: ", not found", warn: ", needs review" };

/** Arrow Up and Arrow Down move between rows, like in a list. */
function moveFocus(e: KeyboardEvent<HTMLButtonElement>) {
  if (e.key !== "ArrowDown" && e.key !== "ArrowUp") return;
  e.preventDefault();
  const all = [...(e.currentTarget.closest("ul")?.querySelectorAll<HTMLButtonElement>("button[data-row]") ?? [])];
  const i = all.indexOf(e.currentTarget);
  all[Math.max(0, Math.min(all.length - 1, i + (e.key === "ArrowDown" ? 1 : -1)))]?.focus();
}

function RowIcon({ icon }: { icon: Row["icon"] }) {
  const look = {
    ok: "bg-success text-success-content",
    no: "bg-base-300 text-base-content/70",
    warn: "bg-warning text-warning-content",
  }[icon];
  return (
    <span aria-hidden className={`pop grid size-[22px] place-items-center rounded-full text-[13px] font-bold ${look}`}>
      {icon === "ok" && <Check size={13} strokeWidth={3.2} />}
      {icon === "no" && <Minus size={12} strokeWidth={3} />}
      {icon === "warn" && "!"}
    </span>
  );
}
