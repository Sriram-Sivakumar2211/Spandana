import { motion } from "framer-motion";
import { cn } from "@/utils/cn";
import { clamp } from "@/utils/format";

interface ProgressBarProps {
  value: number; // 0..100
  color?: string; // css color
  className?: string;
  height?: number;
}

export function ProgressBar({
  value,
  color = "var(--primary)",
  className,
  height = 8,
}: ProgressBarProps) {
  const v = clamp(value);
  return (
    <div
      className={cn("w-full overflow-hidden rounded-full bg-foreground/10", className)}
      style={{ height }}
      role="progressbar"
      aria-valuenow={Math.round(v)}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      <motion.div
        className="h-full rounded-full"
        style={{ background: color }}
        initial={{ width: 0 }}
        animate={{ width: `${v}%` }}
        transition={{ type: "spring", stiffness: 120, damping: 20 }}
      />
    </div>
  );
}
