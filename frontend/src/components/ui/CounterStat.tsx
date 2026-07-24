import { useEffect, useRef, useState } from "react";

interface CounterStatProps {
  value: number;
  decimals?: number;
  suffix?: string;
  className?: string;
  durationMs?: number;
}

/** Animated count-up number, respecting reduced-motion. */
export function CounterStat({
  value,
  decimals = 0,
  suffix = "",
  className,
  durationMs = 900,
}: CounterStatProps) {
  const [display, setDisplay] = useState(0);
  const fromRef = useRef(0);

  useEffect(() => {
    const reduce = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;
    if (reduce) {
      setDisplay(value);
      fromRef.current = value;
      return;
    }
    const from = fromRef.current;
    const start = performance.now();
    let raf = 0;
    const step = (now: number) => {
      const p = Math.min(1, (now - start) / durationMs);
      const eased = 1 - Math.pow(1 - p, 3);
      setDisplay(from + (value - from) * eased);
      if (p < 1) raf = requestAnimationFrame(step);
      else fromRef.current = value;
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [value, durationMs]);

  return (
    <span className={className}>
      {display.toFixed(decimals)}
      {suffix}
    </span>
  );
}
