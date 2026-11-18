import { prettyType } from "../../lib/analysis.ts";
import type { Sample } from "../../lib/api.ts";

type Props = { samples: Sample[]; disabled: boolean; onPick: (sample: Sample) => void };

/** The 10 contracts that ship with the app. One click starts the analysis. */
export function SampleTiles({ samples, disabled, onPick }: Props) {
  return (
    <section>
      <div className="mb-2.5 text-xs font-semibold tracking-wider text-base-content/50 uppercase">
        Or try a sample · CUAD dev contracts
      </div>
      <div className="grid grid-cols-[repeat(auto-fill,minmax(200px,1fr))] gap-2.5">
        {samples.map((s) => (
          <button
            key={s.id}
            disabled={disabled}
            onClick={() => onPick(s)}
            className="grid content-start gap-1.5 rounded-xl border border-base-300 bg-base-100 p-3 text-left transition enabled:hover:-translate-y-px enabled:hover:border-primary disabled:cursor-not-allowed disabled:opacity-60"
          >
            <span className="text-[13.5px] leading-snug font-semibold">{s.title}</span>
            <span className="flex flex-wrap items-center gap-1.5 text-xs text-base-content/50">
              {prettyType(s.contract_type)} · {s.pages} pages
              {s.scan && <span className="badge badge-warning badge-outline badge-xs">scan · OCR, slower</span>}
            </span>
          </button>
        ))}
      </div>
    </section>
  );
}
