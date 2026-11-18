import { useCallback, useEffect, useRef, useState } from "react";
import { type Analysis, next, start } from "../lib/analysis.ts";
import { type Input, streamExtract } from "../lib/api.ts";

/** One contract to analyze: what to send, what to show on the card, and where its PDF is. */
export type Job = {
  id: number; // a new id for every run, so the work screen starts fresh (and its reviews too)
  input: Input;
  title: string;
  subtitle: string;
  fields: string[];
  pdf: string | File; // a URL for a sample, the file itself for an upload
};

let lastId = 0;

/** Runs one stream at a time. Starting a new one, or leaving, stops the old one. */
export function useAnalysis(allFields: number) {
  const [job, setJob] = useState<Job | null>(null);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const stop = useRef<AbortController | null>(null);

  useEffect(() => () => stop.current?.abort(), []); // the page goes away: stop the call

  const run = useCallback(
    (j: Omit<Job, "id">) => {
      stop.current?.abort();
      const controller = new AbortController();
      stop.current = controller;
      setJob({ ...j, id: ++lastId });
      setAnalysis(start(j.fields.length));
      window.scrollTo({ top: 0 });
      const onEvent = (e: Parameters<typeof next>[1]) => setAnalysis((s) => s && next(s, e));
      streamExtract(j.input, j.fields, allFields, onEvent, controller.signal).catch((err: unknown) => {
        if (controller.signal.aborted) return; // "New contract" was clicked: nobody is waiting
        const detail = err instanceof TypeError ? "Could not reach the API. Is it running?" : String(err);
        onEvent({ event: "error", data: { status: 0, detail } });
      });
    },
    [allFields],
  );

  const reset = useCallback(() => {
    stop.current?.abort();
    setJob(null);
    setAnalysis(null);
  }, []);

  return { job, analysis, run, reset };
}
