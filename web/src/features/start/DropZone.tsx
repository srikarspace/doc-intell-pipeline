import { Upload } from "lucide-react";
import { useState } from "react";

const MAX_MB = 10; // the same limit as MAX_BYTES in api/routes.py

type Props = { disabled: boolean; onFile: (file: File) => void };

/** Drop a PDF, or choose one. The server checks it again: this check only saves a trip. */
export function DropZone({ disabled, onFile }: Props) {
  const [over, setOver] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);

  const take = (file: File | undefined) => {
    if (!file || disabled) return;
    if (file.type !== "application/pdf" && !file.name.toLowerCase().endsWith(".pdf")) {
      return setProblem(`"${file.name}" is not a PDF.`);
    }
    if (file.size > MAX_MB * 1024 * 1024) return setProblem(`"${file.name}" is over ${MAX_MB} MB.`);
    setProblem(null);
    onFile(file);
  };

  return (
    <section>
      <div className="mb-2.5 text-xs font-semibold tracking-wider text-base-content/50 uppercase">2 · Contract</div>
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setOver(true);
        }}
        onDragLeave={() => setOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setOver(false);
          take(e.dataTransfer.files[0]);
        }}
        className={`grid min-h-48 place-items-center rounded-[18px] border-2 border-dashed p-6 text-center transition-colors ${
          over ? "border-primary bg-primary/10" : "border-primary/45 bg-base-100/75"
        } ${disabled ? "opacity-60" : ""}`}
      >
        <div>
          <Upload size={34} strokeWidth={1.7} className="mx-auto text-base-content/40" />
          <div className="mt-2.5 text-[17px] font-semibold">Drop a contract PDF here</div>
          <div className="text-[13px] text-base-content/50">
            or{" "}
            <label className={`link link-primary ${disabled ? "pointer-events-none" : ""}`}>
              choose a file
              <input
                type="file"
                accept="application/pdf"
                hidden
                disabled={disabled}
                onChange={(e) => {
                  take(e.target.files?.[0]);
                  e.target.value = ""; // so the same file can be chosen again
                }}
              />
            </label>{" "}
            · PDF, up to {MAX_MB} MB · scans are read with OCR
          </div>
          {problem && <p className="mt-2 text-[13px] text-error">{problem}</p>}
        </div>
      </div>
    </section>
  );
}
