import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  HeartPulse,
  Layers,
  ShieldAlert,
  ThermometerSun,
  TriangleAlert,
} from "lucide-react";
import { PageTransition } from "@/components/layout/PageTransition";
import { PageHeader } from "@/components/ui/PageHeader";
import { HealthCard } from "@/components/features/HealthCard";
import { MachineTable } from "@/components/features/MachineTable";
import { SensorChart } from "@/components/features/SensorChart";
import { AlertCard } from "@/components/features/AlertCard";
import { CardSkeleton } from "@/components/ui/LoadingSkeleton";
import { Button } from "@/components/ui/Button";
import { useMachines } from "@/hooks/useMachines";
import { useStream } from "@/hooks/useStream";
import { fetchAlerts, summarize } from "@/services/spandanaService";
import type { AlertItem } from "@/types";
import { Link } from "react-router-dom";

export default function Dashboard() {
  const { machines, loading } = useMachines();
  const { series } = useStream({ window: 32 });
  const summary = useMemo(() => summarize(machines), [machines]);
  const [alerts, setAlerts] = useState<AlertItem[]>([]);

  useEffect(() => {
    let active = true;
    fetchAlerts().then(({ data }) => {
      if (active) setAlerts(data);
    });
    return () => {
      active = false;
    };
  }, []);

  return (
    <PageTransition>
      <PageHeader
        title="Fleet Overview"
        subtitle="Real-time health and predictive status across all monitored assets."
        actions={
          <Link to="/monitoring">
            <Button variant="secondary" size="sm">
              <Activity size={15} /> Live Monitoring
            </Button>
          </Link>
        }
      />

      {/* Top cards */}
      {loading ? (
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
          {Array.from({ length: 5 }).map((_, i) => (
            <CardSkeleton key={i} />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
          <HealthCard
            label="Total Machines"
            value={summary.total}
            icon={Layers}
            tone="primary"
            index={0}
          />
          <HealthCard
            label="Healthy"
            value={summary.healthy}
            icon={HeartPulse}
            tone="success"
            index={1}
          />
          <HealthCard
            label="Warning"
            value={summary.warning}
            icon={TriangleAlert}
            tone="warning"
            index={2}
          />
          <HealthCard
            label="Critical"
            value={summary.critical}
            icon={ShieldAlert}
            tone="critical"
            index={3}
          />
          <HealthCard
            label="Average Health"
            value={summary.average_health}
            decimals={1}
            suffix="%"
            icon={ThermometerSun}
            tone="primary"
            index={4}
          />
        </div>
      )}

      {/* Machine status table */}
      <section className="mt-6">
        <h2 className="mb-3 font-display text-xl text-foreground">
          Machine Status
        </h2>
        {loading ? <CardSkeleton /> : <MachineTable machines={machines} />}
      </section>

      {/* Live sensor graphs */}
      <section className="mt-6">
        <div className="mb-3 flex items-baseline justify-between">
          <h2 className="font-display text-xl text-foreground">
            Live Sensor Telemetry
          </h2>
          <span className="text-xs text-muted">Illustrative waveform — real health comes from the table above</span>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
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
          <SensorChart
            title="Current"
            unit="A"
            data={series}
            dataKey="current"
            color="var(--warning)"
          />
          <SensorChart
            title="RPM"
            unit="rpm"
            data={series}
            dataKey="rpm"
            color="var(--success)"
          />
        </div>
      </section>

      {/* Alerts + report preview */}
      <section className="mt-6 grid gap-4 lg:grid-cols-2">
        <AlertCard alerts={alerts} />
        <div className="rounded-2xl border border-border bg-card p-5 shadow-soft">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="font-display text-lg text-foreground">
              Latest AI Report
            </h3>
            <Link
              to="/reports"
              className="text-sm text-primary hover:underline"
            >
              View all
            </Link>
          </div>
          <p className="text-sm text-muted">
            The most critical asset right now is{" "}
            <span className="text-foreground">
              {machines.find((m) => m.status === "critical")?.name ??
                "None flagged"}
            </span>
            . Open Reports for the full AI-generated maintenance breakdown,
            evidence, and recommended actions.
          </p>
          <Link to="/reports">
            <Button variant="secondary" size="sm" className="mt-4">
              Open Reports
            </Button>
          </Link>
        </div>
      </section>
    </PageTransition>
  );
}
