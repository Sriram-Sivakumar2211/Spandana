import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft, Gauge, Thermometer, Wind, Zap } from "lucide-react";
import { PageTransition } from "@/components/layout/PageTransition";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { PredictionCard } from "@/components/features/PredictionCard";
import { ReportCard } from "@/components/features/ReportCard";
import { KnowledgeSourcesCard } from "@/components/features/KnowledgeSourcesCard";
import { EmptyState } from "@/components/ui/States";
import { CardSkeleton } from "@/components/ui/LoadingSkeleton";
import { useMachines } from "@/hooks/useMachines";
import { assessMachine } from "@/services/spandanaService";
import { formatMaybe, formatRpm, formatSource } from "@/utils/format";
import type { DashboardMachineStatus } from "@/types";

export default function MachineDetail() {
  const { id } = useParams<{ id: string }>();
  const { machines, loading } = useMachines();
  const [assessment, setAssessment] = useState<DashboardMachineStatus | null>(null);
  const machine = machines.find((m) => m.id === id);
  const prediction = assessment?.prediction ?? null;

  useEffect(() => {
    if (!id) return;
    let active = true;
    (async () => {
      const { data } = await assessMachine(id);
      if (active) setAssessment(data);
    })();
    return () => {
      active = false;
    };
  }, [id]);

  if (loading) {
    return (
      <PageTransition>
        <CardSkeleton />
      </PageTransition>
    );
  }

  if (!machine) {
    return (
      <PageTransition>
        <EmptyState
          title="Machine not found"
          message={`No asset with ID "${id}".`}
        />
        <div className="mt-4">
          <Link to="/machines">
            <Button variant="secondary" size="sm">
              <ArrowLeft size={15} /> Back to Machines
            </Button>
          </Link>
        </div>
      </PageTransition>
    );
  }

  const specs = [
    { icon: Thermometer, label: "Temperature", value: `${formatMaybe(machine.temperature, 1)} °C` },
    { icon: Zap, label: "Current", value: `${formatMaybe(machine.current, 1)} A` },
    { icon: Wind, label: "RPM", value: formatRpm(machine.rpm) },
    { icon: Gauge, label: "Vibration", value: `${formatMaybe(machine.vibration, 2)} mm/s` },
  ];

  return (
    <PageTransition>
      <PageHeader
        title={machine.name}
        subtitle={`${machine.id} · ${machine.source ? formatSource(machine.source) : "Unknown source"} · ${machine.location}`}
        breadcrumbs={[
          { label: "Home", to: "/" },
          { label: "Machines", to: "/machines" },
          { label: machine.name },
        ]}
        actions={
          <Link to="/machines">
            <Button variant="secondary" size="sm">
              <ArrowLeft size={15} /> Back
            </Button>
          </Link>
        }
      />

      <div className="mb-5 grid grid-cols-2 gap-4 lg:grid-cols-4">
        {specs.map((s) => {
          const Icon = s.icon;
          return (
            <Card key={s.label} className="p-4">
              <div className="mb-1 flex items-center gap-1.5 text-muted">
                <Icon size={15} />
                <span className="text-xs">{s.label}</span>
              </div>
              <p className="text-2xl text-foreground tnum">{s.value}</p>
            </Card>
          );
        })}
      </div>

      {prediction ? (
        <div className="mb-5">
          <PredictionCard prediction={prediction} />
        </div>
      ) : (
        <CardSkeleton />
      )}

      {/* Real RAG-grounded maintenance intelligence for this machine */}
      <div className="grid gap-5 lg:grid-cols-[1fr_360px]">
        <div>
          {assessment?.report && (
            <ReportCard
              report={assessment.report}
              machine={machine}
              onDownload={() => {
                const blob = new Blob(
                  [JSON.stringify(assessment.report, null, 2)],
                  { type: "application/json" },
                );
                const url = URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = url;
                a.download = `spandana-report-${machine.id}.json`;
                a.click();
                URL.revokeObjectURL(url);
              }}
            />
          )}
        </div>
        <KnowledgeSourcesCard
          query={assessment?.retrieval?.query ?? ""}
          chunks={assessment?.retrieval?.chunks ?? []}
        />
      </div>
    </PageTransition>
  );
}
