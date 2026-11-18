import { useEffect, useState } from "react";

const reducedMotion = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;

/** Counts from 0 up to `total`, one step every `gapMs`. Goes back to 0 when `total` is 0. */
export function useReveal(total: number, gapMs = 140): number {
  const [shown, setShown] = useState(0);
  useEffect(() => {
    if (total === 0) return setShown(0);
    if (reducedMotion()) return setShown(total);
    const timer = setInterval(() => {
      setShown((n) => {
        if (n + 1 >= total) clearInterval(timer);
        return Math.min(n + 1, total);
      });
    }, gapMs);
    return () => clearInterval(timer);
  }, [total, gapMs]);
  return shown;
}
