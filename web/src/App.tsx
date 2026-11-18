import { useQuery } from "@tanstack/react-query";
import { ChevronLeft } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { type Analysis, next, prettyType, start } from "./analysis.ts";
import { getFields, getSamples, type Input, streamExtract } from "./api.ts";
import { AnalyzeCard } from "./components/AnalyzeCard.tsx";
import { DropZone } from "./components/DropZone.tsx";
import { FieldChips } from "./components/FieldChips.tsx";
import { SampleTiles } from "./components/SampleTiles.tsx";

type Job = { input: Input; title: string; subtitle: string; fields: string[] };

export default function App() {
  const fields = useQuery({ queryKey: ["fields"], queryFn: getFields });
  const samples = useQuery({ queryKey: ["samples"], queryFn: getSamples });
  const [chosen, setChosen] = useState<Set<string> | null>(null); // null: not loaded yet
  const [job, setJob] = useState<Job | null>(null);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const stop = useRef<AbortController | null>(null);

  // All fields are on at the start.
  useEffect(() => {
    if (fields.data && chosen === null) setChosen(new Set(fields.data.map((f) => f.name)));
  }, [fields.data, chosen]);

  const run = (j: Job) => {
    stop.current?.abort();
    const controller = new AbortController();
    stop.current = controller;
    setJob(j);
    setAnalysis(start(j.fields.length));
    window.scrollTo({ top: 0 });
    streamExtract(j.input, j.fields, fields.data!.length, (e) => setAnalysis((s) => s && next(s, e)), controller.signal).catch(
      (err: unknown) => {
        if (controller.signal.aborted) return; // "New contract" was clicked: nobody is waiting
        const detail = err instanceof TypeError ? "Could not reach the API. Is it running?" : String(err);
        setAnalysis((s) => s && next(s, { event: "error", data: { status: 0, detail } }));
      },
    );
  };

  const newContract = () => {
    stop.current?.abort();
    setJob(null);
    setAnalysis(null);
  };

  const picked = fields.data?.filter((f) => chosen?.has(f.name)).map((f) => f.name) ?? [];
  const loadError = fields.error ?? samples.error;

  return (
    <div className="px-4 pb-12">
      <header className="mx-auto flex max-w-[1240px] items-center gap-3 py-3.5">
        <div className="flex items-center gap-2 font-semibold tracking-tight">
          <img src="/favicon.svg" alt="" className="size-[22px]" />
          docintel
        </div>
        <span className="rounded-full border border-base-300 bg-base-100 px-2 py-0.5 text-xs text-base-content/50">
          local · one user
        </span>
      </header>

      {job && analysis ? (
        <main className="mx-auto mt-4 grid max-w-[720px] gap-5">
          <div>
            <button className="btn-quiet" onClick={newContract}>
              <ChevronLeft size={14} /> New contract
            </button>
          </div>
          <AnalyzeCard
            title={job.title}
            subtitle={job.subtitle}
            analysis={analysis}
            fields={fields.data!.filter((f) => job.fields.includes(f.name))}
            onRetry={() => run(job)}
          />
        </main>
      ) : (
        <main className="mx-auto mt-6 grid max-w-[880px] gap-7">
          <div>
            <h1 className="text-[clamp(26px,4vw,34px)] leading-tight font-semibold tracking-tight text-balance">
              Check a contract in one pass
            </h1>
            <p className="mt-1.5 max-w-[60ch] text-base-content/70">
              Choose the fields, then drop a PDF or pick a sample. Every answer comes with the exact quote from the
              contract. Anything doubtful is flagged for you to look at.
            </p>
          </div>
          {loadError && (
            <div role="alert" className="alert alert-error alert-soft">
              Could not load the fields or samples from the API. Is it running? ({String(loadError.message)})
            </div>
          )}
          {fields.isPending && <div className="skeleton h-40" />}
          {fields.data && chosen && <FieldChips fields={fields.data} chosen={chosen} onChange={setChosen} />}
          <DropZone
            disabled={picked.length === 0}
            onFile={(pdf) => run({ input: { pdf }, title: pdf.name, subtitle: "Upload", fields: picked })}
          />
          {samples.data && (
            <SampleTiles
              samples={samples.data}
              disabled={picked.length === 0}
              onPick={(s) =>
                run({ input: { sampleId: s.id }, title: s.title, subtitle: prettyType(s.contract_type), fields: picked })
              }
            />
          )}
        </main>
      )}
    </div>
  );
}
