import type { Job } from "../../hooks/useAnalysis.ts";
import { prettyType } from "../../lib/analysis.ts";
import { type FieldInfo, type Sample, samplePdfUrl } from "../../lib/api.ts";
import { DropZone } from "./DropZone.tsx";
import { FieldChips } from "./FieldChips.tsx";
import { SampleTiles } from "./SampleTiles.tsx";

type Props = {
  fields: FieldInfo[] | undefined;
  samples: Sample[] | undefined;
  loadError: Error | null;
  chosen: Set<string>;
  onChosen: (chosen: Set<string>) => void;
  onStart: (job: Omit<Job, "id">) => void;
};

/** Step 1: the fields. Step 2: a PDF or a sample. Either one starts the analysis. */
export function StartScreen({ fields, samples, loadError, chosen, onChosen, onStart }: Props) {
  const picked = fields?.filter((f) => chosen.has(f.name)).map((f) => f.name) ?? [];
  const off = picked.length === 0;

  return (
    <main className="mx-auto mt-6 grid max-w-[880px] gap-7">
      <div>
        <h1 className="text-[clamp(26px,4vw,34px)] leading-tight font-semibold tracking-tight text-balance">
          Check a contract in one pass
        </h1>
        <p className="mt-1.5 max-w-[60ch] text-base-content/70">
          Choose the fields, then drop a PDF or pick a sample. Every answer comes with the exact quote, highlighted in
          the PDF. Anything doubtful is flagged for you to accept or fix.
        </p>
      </div>
      {loadError && (
        <div role="alert" className="rounded-xl bg-error/10 px-4 py-3 text-error">
          Could not load the fields or samples from the API. Is it running? ({loadError.message})
        </div>
      )}
      {fields ? <FieldChips fields={fields} chosen={chosen} onChange={onChosen} /> : <div className="skeleton h-40" />}
      <DropZone
        disabled={off}
        onFile={(pdf) => onStart({ input: { pdf }, pdf, title: pdf.name, subtitle: "Upload", fields: picked })}
      />
      {samples && (
        <SampleTiles
          samples={samples}
          disabled={off}
          onPick={(s) =>
            onStart({
              input: { sampleId: s.id },
              pdf: samplePdfUrl(s.id),
              title: s.title,
              subtitle: prettyType(s.contract_type),
              fields: picked,
            })
          }
        />
      )}
    </main>
  );
}
