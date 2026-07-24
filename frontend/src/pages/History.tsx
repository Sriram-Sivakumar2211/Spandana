import { useEffect, useMemo, useState } from "react";
import { List, GitCommitVertical } from "lucide-react";
import { PageTransition } from "@/components/layout/PageTransition";
import { PageHeader } from "@/components/ui/PageHeader";
import { HistoryTable } from "@/components/features/HistoryTable";
import { HistoryTimeline } from "@/components/features/HistoryTimeline";
import { SearchBar } from "@/components/ui/SearchBar";
import { Modal } from "@/components/ui/Modal";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { CardSkeleton } from "@/components/ui/LoadingSkeleton";
import { EmptyState } from "@/components/ui/States";
import { fetchHistory } from "@/services/spandanaService";
import { formatFault, formatTime, pct } from "@/utils/format";
import type { HealthStatus, HistoryRecord } from "@/types";
import { cn } from "@/utils/cn";

const FILTERS: { key: HealthStatus | "all"; label: string }[] = [
  { key: "all", label: "All" },
  { key: "healthy", label: "Healthy" },
  { key: "warning", label: "Warning" },
  { key: "critical", label: "Critical" },
];

export default function History() {
  const [rows, setRows] = useState<HistoryRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState<"table" | "timeline">("table");
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<HealthStatus | "all">("all");
  const [active, setActive] = useState<HistoryRecord | null>(null);

  useEffect(() => {
    let mounted = true;
    (async () => {
      const { data } = await fetchHistory();
      if (!mounted) return;
      setRows(data);
      setLoading(false);
    })();
    return () => {
      mounted = false;
    };
  }, []);

  const filtered = useMemo(() => {
    return rows.filter((r) => {
      const matchesFilter = filter === "all" || r.status === filter;
      const q = query.toLowerCase();
      const matchesQuery =
        !q ||
        r.machine_name.toLowerCase().includes(q) ||
        r.machine_id.toLowerCase().includes(q) ||
        formatFault(r.predicted_fault).toLowerCase().includes(q);
      return matchesFilter && matchesQuery;
    });
  }, [rows, filter, query]);

  return (
    <PageTransition>
      <PageHeader
        title="Prediction History"
        subtitle="Historical inference records across the fleet (GET /history)."
        breadcrumbs={[{ label: "Home", to: "/" }, { label: "History" }]}
        actions={
          <div className="flex rounded-xl border border-border p-0.5">
            <button
              onClick={() => setView("table")}
              className={cn(
                "flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm transition-colors",
                view === "table"
                  ? "bg-primary/10 text-primary"
                  : "text-muted hover:text-foreground",
              )}
            >
              <List size={15} /> Table
            </button>
            <button
              onClick={() => setView("timeline")}
              className={cn(
                "flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm transition-colors",
                view === "timeline"
                  ? "bg-primary/10 text-primary"
                  : "text-muted hover:text-foreground",
              )}
            >
              <GitCommitVertical size={15} /> Timeline
            </button>
          </div>
        }
      />

      <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <SearchBar
          value={query}
          onChange={setQuery}
          className="sm:max-w-xs"
          placeholder="Search history…"
        />
        <div className="flex gap-1.5">
          {FILTERS.map((f) => (
            <button
              key={f.key}
              onClick={() => setFilter(f.key)}
              className={cn(
                "rounded-xl border px-3 py-1.5 text-sm transition-colors",
                filter === f.key
                  ? "border-primary bg-primary/10 text-primary"
                  : "border-border text-muted hover:text-foreground",
              )}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <CardSkeleton />
      ) : filtered.length === 0 ? (
        <EmptyState title="No records match" message="Adjust your search or filter." />
      ) : view === "table" ? (
        <HistoryTable rows={filtered} onRowClick={setActive} />
      ) : (
        <HistoryTimeline rows={filtered} onRowClick={setActive} />
      )}

      <Modal
        open={!!active}
        onClose={() => setActive(null)}
        title={active ? `${active.machine_name} · Prediction` : ""}
      >
        {active && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <StatusBadge status={active.status} />
              <span className="text-xs text-muted">
                {formatTime(active.timestamp)}
              </span>
            </div>
            <dl className="grid grid-cols-2 gap-4">
              {[
                ["Machine ID", active.machine_id],
                ["Predicted Fault", formatFault(active.predicted_fault)],
                ["Confidence", pct(active.prediction_confidence, 1)],
                ["Health Score", `${active.health_score.toFixed(1)}%`],
                ["Anomaly Score", active.anomaly_score.toFixed(3)],
                ["Record ID", active.id],
              ].map(([k, v]) => (
                <div key={k}>
                  <dt className="text-xs text-muted">{k}</dt>
                  <dd className="text-sm text-foreground tnum">{v}</dd>
                </div>
              ))}
            </dl>
            <div className="rounded-xl border border-border bg-background/50 p-3">
              <p className="text-xs uppercase tracking-wide text-muted">
                Recommended Action
              </p>
              <p className="mt-1 text-sm text-foreground">
                {active.recommended_action}
              </p>
            </div>
          </div>
        )}
      </Modal>
    </PageTransition>
  );
}
