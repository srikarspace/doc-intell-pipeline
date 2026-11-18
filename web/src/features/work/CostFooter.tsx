import { Check, Copy } from "lucide-react";
import { useState } from "react";
import type { ExtractResult } from "../../lib/api.ts";

type Props = { result: ExtractResult; json: () => unknown };

/** Parser, pages, cost and time of the answer, and Copy JSON of the reviewed answer. */
export function CostFooter({ result, json }: Props) {
  const [copied, setCopied] = useState<"yes" | "blocked" | null>(null);
  const text = () => JSON.stringify(json(), null, 2);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text());
      setCopied("yes");
      setTimeout(() => setCopied(null), 2000);
    } catch {
      setCopied("blocked"); // no clipboard (an old browser, or no permission): show the JSON instead
    }
  };

  return (
    <footer className="border-t border-base-300 px-[22px] pt-3.5 pb-[34px]">
      <div className="flex flex-wrap items-center gap-2 font-mono text-xs text-base-content/50">
        <span>{result.parser}</span>·<span>{result.pages} pages</span>·<span>${result.cost_usd.toFixed(4)}</span>·
        <span>{(result.latency_ms / 1000).toFixed(1)} s</span>
        <span className="flex-1" />
        <button className="btn-quiet font-sans" onClick={copy}>
          {copied === "yes" ? <Check size={14} /> : <Copy size={14} />}
          {copied === "yes" ? "Copied" : "Copy JSON"}
        </button>
      </div>
      {copied === "blocked" && (
        <textarea
          readOnly
          aria-label="The reviewed answer as JSON"
          className="textarea mt-3 h-44 w-full font-mono text-xs"
          value={text()}
          onFocus={(e) => e.target.select()}
        />
      )}
    </footer>
  );
}
