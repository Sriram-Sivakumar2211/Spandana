import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft, Gauge, Thermometer, Wind, Zap } from "lucide-react";
import { PageTransition } from "@/components/layout/PageTransition";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { PredictionCard } from "@/components/features/PredictionCard";
import { SensorChart } from "@/components/features/SensorChart";
import { EmptyState } from "@/components/ui/States";
import { CardSkeleton } from "@/components/ui/LoadingSkeleton";
import { useMachines } from "@/hooks/useMachines";
import { useStream } from "@/hooks/useStream";
import { fetchPrediction } from "@/services/spandanaService";
import { formatMaybe, formatSource } from "@/utils/format";
import type { Prediction } from "@/types";

export default function MachineDetail() {
  const { id } = useParams<{ id: string }>();
  const { machines, loading } = useMachines();
  const { series } = useStream({ window: 30 });
  const [prediction, setPrediction] = useState<Prediction | null>(null);
  const machine = machines.find((m) => m.id === id);

  useEffect(() => {
    if (!id) return;
    let active = true;
    (async () => {
      const { data } = await fetchPrediction(id);
      if (active) setPrediction(data);
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
    { icon: Wind, label: "RPM", value: machine.rpm === null ? "—" : String(machine.rpm) },
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

      {prediction && (
        <div className="mb-5">
          <PredictionCard prediction={prediction} />
        </div>
      )}

      <h2 className="mb-3 font-display text-xl text-foreground">
        Live Telemetry
      </h2>
      <div className="grid gap-4 sm:grid-cols-2">
        <SensorChart
          title="Vibration"
          unit="mm/s"
          data={series}
          dataKey="vibration"
          color="var(--primary)"
        />
        <SensorChart
          title="Temperature"
          unit="°C"
          data={series}
          dataKey="temperature"
          color="var(--critical)"
        />
      </div>
    </PageTransition>
  );
}
