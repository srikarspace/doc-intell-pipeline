import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { StartScreen } from "./features/start/StartScreen.tsx";
import { WorkScreen } from "./features/work/WorkScreen.tsx";
import { useAnalysis } from "./hooks/useAnalysis.ts";
import { getFields, getSamples } from "./lib/api.ts";

/** The app: a top bar, then the start screen or the work screen. */
export default function App() {
  const fields = useQuery({ queryKey: ["fields"], queryFn: getFields });
  const samples = useQuery({ queryKey: ["samples"], queryFn: getSamples });
  const [chosen, setChosen] = useState<Set<string> | null>(null); // null: the user has not changed it, so all
  const { job, analysis, run, reset } = useAnalysis(fields.data?.length ?? 12);
  const allChosen = chosen ?? new Set(fields.data?.map((f) => f.name));

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

      {job && analysis && fields.data ? (
        <WorkScreen
          key={job.id} // a new job starts with a fresh screen: no open row, no reviews
          job={job}
          analysis={analysis}
          allFields={fields.data}
          onNew={reset}
          onRetry={() => run(job)}
        />
      ) : (
        <StartScreen
          fields={fields.data}
          samples={samples.data}
          loadError={fields.error ?? samples.error}
          chosen={allChosen}
          onChosen={setChosen}
          onStart={run}
        />
      )}
    </div>
  );
}
