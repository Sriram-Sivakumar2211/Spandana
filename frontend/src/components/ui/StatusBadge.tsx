import { cn } from "@/utils/cn";
import { STATUS_TOKENS } from "@/utils/status";
import type { HealthStatus } from "@/types";

interface StatusBadgeProps {
  status: HealthStatus;
  label?: string;
  dot?: boolean;
  className?: string;
}

export function StatusBadge({
  status,
  label,
  dot = true,
  className,
}: StatusBadgeProps) {
  const t = STATUS_TOKENS[status];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium",
        t.soft,
        t.text,
        className,
      )}
    >
      {dot && (
        <span
          className={cn("h-1.5 w-1.5 rounded-full", t.bg)}
          aria-hidden="true"
        />
      )}
      {label ?? t.label}
    </span>
  );
}
