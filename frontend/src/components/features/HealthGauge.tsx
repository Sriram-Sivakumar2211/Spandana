import { useEffect, useState } from "react";
import { statusFromScore, statusColor } from "@/utils/status";
import { clamp } from "@/utils/format";

interface HealthGaugeProps {
  score: number; // 0..100
  size?: number;
  label?: string;
}

/** SVG radial gauge with an animated sweep; color follows health status. */
export function HealthGauge({ score, size = 180, label = "Health Index" }: HealthGaugeProps) {
  const v = clamp(score);
  const color = statusColor(statusFromScore(v));
  const stroke = 12;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduce) {
      setProgress(v);
      return;
    }
    const id = requestAnimationFrame(() => setProgress(v));
    return () => cancelAnimationFrame(id);
  }, [v]);

  const offset = c - (progress / 100) * c;

  return (
    <div
      className="relative grid place-items-center"
      style={{ width: size, height: size }}
    >
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke="var(--border)"
          strokeWidth={stroke}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={offset}
          style={{ transition: "stroke-dashoffset 1s cubic-bezier(0.22,1,0.36,1)" }}
        />
      </svg>
      <div className="absolute flex flex-col items-center">
        <span className="text-4xl text-foreground tnum">{v.toFixed(1)}</span>
        <span className="text-xs text-muted">{label}</span>
      </div>
    </div>
  );
}
