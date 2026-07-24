import type { HealthStatus } from "@/types";

/** Derive a health status from a 0..100 score (shared thresholds). */
export function statusFromScore(score: number): HealthStatus {
  if (score >= 75) return "healthy";
  if (score >= 45) return "warning";
  return "critical";
}

interface StatusTokens {
  label: string;
  /** tailwind text color class */
  text: string;
  /** tailwind bg color class (solid) */
  bg: string;
  /** soft translucent background */
  soft: string;
  /** the raw CSS var color */
  color: string;
}

export const STATUS_TOKENS: Record<HealthStatus, StatusTokens> = {
  healthy: {
    label: "Healthy",
    text: "text-success",
    bg: "bg-success",
    soft: "bg-success/10",
    color: "var(--success)",
  },
  warning: {
    label: "Warning",
    text: "text-warning",
    bg: "bg-warning",
    soft: "bg-warning/10",
    color: "var(--warning)",
  },
  critical: {
    label: "Critical",
    text: "text-critical",
    bg: "bg-critical",
    soft: "bg-critical/10",
    color: "var(--critical)",
  },
};

export function statusColor(status: HealthStatus): string {
  return STATUS_TOKENS[status].color;
}
