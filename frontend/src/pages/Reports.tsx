import { useEffect, useState } from "react";
import { PageTransition } from "@/components/layout/PageTransition";
import { PageHeader } from "@/components/ui/PageHeader";
import { ReportCard } from "@/components/features/ReportCard";
import { CardSkeleton } from "@/components/ui/LoadingSkeleton";
import { useMachines } from "@/hooks/useMachines";
import { fetchReport } from "@/services/spandanaService";
import type { MaintenanceReport } from "@/types";
import { cn } from "@/utils/cn";

export default function Reports() {
  const { machines } = useMachines();
  const [selected, setSelected] = useState<string>("");
  const [report, setReport] = useState<MaintenanceReport | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!selected && machines.length > 0) setSelected(machines[0].id);
  }, [machines, selected]);

  useEffect(() => {
    if (!selected) return;
    let active = true;
    setLoading(true);
    (async () => {
      const { data } = await fetchReport(selected);
      if (!active) return;
      setReport(data);
      setLoading(false);
    })();
    return () => {
      active = false;
    };
  }, [selected]);

  const download = () => {
    if (!report) return;
    const blob = new Blob([JSON.stringify(report, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `spandana-report-${report.machine_id}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <PageTransition>
      <PageHeader
        title="AI Maintenance Reports"
        subtitle="Structured, RAG-grounded maintenance intelligence per asset (POST /report)."
        breadcrumbs={[{ label: "Home", to: "/" }, { label: "Reports" }]}
      />

      <div className="mb-5 flex flex-wrap gap-2">
        {machines.map((m) => (
          <button
            key={m.id}
            onClick={() => setSelected(m.id)}
            className={cn(
              "rounded-xl border px-3 py-1.5 text-sm transition-colors",
              selected === m.id
                ? "border-primary bg-primary/10 text-primary"
                : "border-border text-muted hover:text-foreground",
            )}
          >
            {m.name}
          </button>
        ))}
      </div>

      {loading || !report ? (
        <CardSkeleton />
      ) : (
        <ReportCard
          report={report}
          machine={machines.find((m) => m.id === selected)}
          onDownload={download}
        />
      )}
    </PageTransition>
  );
}
