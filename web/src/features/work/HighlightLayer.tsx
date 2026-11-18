import { type Mark, toBoxes } from "../../lib/boxes.ts";

/** The boxes on one drawn page. They sit on top of the page and let clicks pass through. */
export function HighlightLayer({ marks, pageWidth, pulseKey }: { marks: Mark[]; pageWidth: number; pulseKey: string }) {
  return (
    <>
      {marks.flatMap((m, i) =>
        toBoxes(m.highlight, pageWidth).map((b, j) => (
          <div
            key={`${pulseKey}-${i}-${j}`} // a new key restarts the pulse
            data-mark={m.kind}
            className={`pointer-events-none absolute rounded-[3px] mix-blend-multiply ${
              m.kind === "evidence" ? "mark-evidence" : "mark-quote"
            } ${m.focused ? "mark-pulse" : ""}`}
            style={{ left: b.left, top: b.top, width: b.width, height: b.height }}
          />
        )),
      )}
    </>
  );
}
