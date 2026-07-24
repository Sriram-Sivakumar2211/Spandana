import { useMemo, useState } from "react";
import { PageTransition } from "@/components/layout/PageTransition";
import { PageHeader } from "@/components/ui/PageHeader";
import { MachineCard } from "@/components/features/MachineCard";
import { SearchBar } from "@/components/ui/SearchBar";
import { CardSkeleton } from "@/components/ui/LoadingSkeleton";
import { EmptyState } from "@/components/ui/States";
import { useMachines } from "@/hooks/useMachines";
import { formatSource } from "@/utils/format";
import type { HealthStatus } from "@/types";
import { cn } from "@/utils/cn";

const FILTERS: { key: HealthStatus | "all"; label: string }[] = [
  { key: "all", label: "All" },
  { key: "healthy", label: "Healthy" },
  { key: "warning", label: "Warning" },
  { key: "critical", label: "Critical" },
];

export default function Machines() {
  const { machines, loading } = useMachines();
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<HealthStatus | "all">("all");

  const filtered = useMemo(() => {
    return machines.filter((m) => {
      const matchesFilter = filter === "all" || m.status === filter;
      const q = query.toLowerCase();
      const matchesQuery =
        !q ||
        m.name.toLowerCase().includes(q) ||
        m.id.toLowerCase().includes(q) ||
        (m.source ? formatSource(m.source).toLowerCase().includes(q) : false);
      return matchesFilter && matchesQuery;
    });
  }, [machines, filter, query]);

  return (
    <PageTransition>
      <PageHeader
        title="Machines"
        subtitle="All monitored industrial assets and their live condition."
        breadcrumbs={[{ label: "Home", to: "/" }, { label: "Machines" }]}
      />

      <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <SearchBar
          value={query}
          onChange={setQuery}
          className="sm:max-w-xs"
          placeholder="Search by name, ID or source…"
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
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <CardSkeleton key={i} />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <EmptyState
          title="No machines match"
          message="Try a different search term or filter."
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {filtered.map((m, i) => (
            <MachineCard key={m.id} machine={m} index={i} />
          ))}
        </div>
      )}
    </PageTransition>
  );
}
