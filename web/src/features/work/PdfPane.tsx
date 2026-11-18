// The PDF on the right, drawn by pdf.js (through react-pdf), with our boxes on top.
// This file is loaded only when a result is shown (React.lazy), so pdf.js is not in the first download.

import workerUrl from "pdfjs-dist/build/pdf.worker.min.mjs?url";
import { type RefObject, useEffect, useRef, useState } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import type { Mark } from "../../lib/boxes.ts";
import { toBoxes } from "../../lib/boxes.ts";
import { HighlightLayer } from "./HighlightLayer.tsx";

// pdf.js reads the PDF in a Web Worker (a background thread), so the page stays smooth.
// pdf.js 6 has no `eval` path at all, so a bad PDF cannot run code through font loading.
pdfjs.GlobalWorkerOptions.workerSrc = workerUrl;

type Props = {
  file: string | File; // a URL (sample) or the uploaded file
  name: string;
  marks: Mark[];
  pulseKey: string; // changes on every click on a row or a quote: scroll and pulse again
  scan: boolean; // a scan has no boxes
};

export default function PdfPane({ file, name, marks, pulseKey, scan }: Props) {
  const pane = useRef<HTMLElement>(null);
  const pages = useRef(new Map<number, HTMLDivElement>());
  const [count, setCount] = useState(0);
  const [drawn, setDrawn] = useState(0); // pages drawn so far; scrolling waits for the focused page
  const width = usePageWidth(pane);

  // Scroll the pane (not the window) so the focused box is near the top.
  useEffect(() => {
    const target = marks.find((m) => m.focused) ?? marks[0];
    const page = target && pages.current.get(target.highlight.page);
    if (!target || !page || !pane.current || !width) return;
    const top = page.offsetTop + toBoxes(target.highlight, width)[0].top - 80;
    const smooth = !window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    pane.current.scrollTo({ top, behavior: smooth ? "smooth" : "auto" });
  }, [pulseKey, drawn, width]); // `marks` is left out on purpose: it changes together with `pulseKey`

  return (
    <aside
      ref={pane}
      aria-label="Contract PDF"
      className="relative grid h-[70vh] min-h-[420px] auto-rows-max content-start gap-4 overflow-auto rounded-2xl [scrollbar-gutter:stable] border border-base-300 bg-base-300/40 p-4 min-[920px]:sticky min-[920px]:top-3 min-[920px]:h-[calc(100vh-90px)]"
    >
      <div className="flex items-center gap-2 text-[12.5px] text-base-content/50">
        <b className="font-medium text-base-content/70">{name}</b>·{" "}
        {scan ? "a scan: no boxes, the text was read with OCR" : "click a row to jump to its quote"}
      </div>
      <Document
        file={file}
        onLoadSuccess={(pdf) => setCount(pdf.numPages)}
        loading={<div className="skeleton aspect-[1/1.414] w-full" />}
        error={<p className="py-10 text-center text-base-content/50">The PDF could not load. The answers on the left still work.</p>}
        className="grid gap-4"
      >
        {width > 0 &&
          Array.from({ length: count }, (_, i) => i + 1).map((n) => (
            <div
              key={n}
              ref={(el) => {
                if (el) pages.current.set(n, el);
                else pages.current.delete(n);
              }}
              className="relative overflow-hidden rounded-[3px] bg-white shadow-sm"
            >
              <Page
                pageNumber={n}
                width={width}
                renderTextLayer={false}
                renderAnnotationLayer={false}
                onRenderSuccess={() => setDrawn((d) => d + 1)}
                loading={<div className="aspect-[1/1.414]" style={{ width }} />}
              />
              <HighlightLayer marks={marks.filter((m) => m.highlight.page === n)} pageWidth={width} pulseKey={pulseKey} />
              <span className="absolute right-2 bottom-1.5 font-mono text-[11px] text-neutral-500">{n}</span>
            </div>
          ))}
      </Document>
    </aside>
  );
}

/** The width a page can use inside the pane: it changes when the window changes. */
function usePageWidth(pane: RefObject<HTMLElement | null>): number {
  const [width, setWidth] = useState(0);
  useEffect(() => {
    if (!pane.current) return;
    const observer = new ResizeObserver(([entry]) => setWidth(Math.floor(entry.contentRect.width)));
    observer.observe(pane.current);
    return () => observer.disconnect();
  }, [pane]);
  return width;
}
