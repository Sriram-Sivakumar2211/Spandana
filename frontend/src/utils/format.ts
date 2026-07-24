/** Formatting + display helpers shared across pages. */

export function formatFault(fault: string): string {
  const map: Record<string, string> = {
    healthy: "Healthy",
    inner_race: "Inner Race Fault",
    outer_race: "Outer Race Fault",
    ball: "Ball / Roller Fault",
    combined: "Combined Fault",
  };
  return map[fault] ?? fault.replace(/_/g, " ");
}

export function formatSource(source: string): string {
  const map: Record<string, string> = {
    squirrel_cage: "Squirrel-Cage Motor",
    metropt3: "MetroPT-3 Compressor",
    thermal_motor: "Thermal Motor",
    cwru: "CWRU Bearing",
    paderborn: "Paderborn Bearing",
    nasa_ims: "NASA IMS Bearing",
  };
  return map[source] ?? source;
}

export function formatTime(iso: string): string {
  const d = new Date(iso);
  if (isNaN(d.getTime())) return iso;
  return d.toLocaleString(undefined, {
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function timeAgo(iso: string): string {
  const d = new Date(iso).getTime();
  if (isNaN(d)) return "—";
  const secs = Math.max(1, Math.floor((Date.now() - d) / 1000));
  if (secs < 60) return `${secs}s ago`;
  const mins = Math.floor(secs / 60);
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

export function formatRul(hours: number | null): string {
  if (hours === null || hours === undefined) return "Not projected";
  if (hours <= 0) return "Overdue";
  if (hours < 48) return `${hours.toFixed(1)} h`;
  return `${(hours / 24).toFixed(1)} days`;
}

export function pct(v: number, digits = 0): string {
  return `${(v * 100).toFixed(digits)}%`;
}

export function clamp(v: number, min = 0, max = 100): number {
  return Math.min(max, Math.max(min, v));
}

/** Formats a possibly-unknown sensor reading; the backend only knows these once a prediction request has supplied them. */
export function formatMaybe(v: number | null | undefined, decimals = 1): string {
  return v === null || v === undefined ? "—" : v.toFixed(decimals);
}
