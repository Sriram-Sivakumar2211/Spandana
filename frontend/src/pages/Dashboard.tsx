import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  ArrowUpRight,
  HeartPulse,
  Layers,
  ShieldAlert,
  ThermometerSun,
  TriangleAlert,
} from "lucide-react";
import {
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  CartesianGrid,
} from "recharts";
import { Link } from "react-router-dom";
import { PageTransition } from "@/components/layout/PageTransition";
import { PageHeader } from "@/components/ui/PageHeader";
import { HealthCard } from "@/components/features/HealthCard";
import { MachineTable } from "@/components/features/MachineTable";
import { AlertCard } from "@/components/features/AlertCard";
import { Card } from "@/components/ui/Card";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { CardSkeleton } from "@/components/ui/LoadingSkeleton";
import { Button } from "@/components/ui/Button";
import { useMachines } from "@/hooks/useMachines";
import { useLiveInference } from "@/hooks/useLiveInference";
import { useSettings } from "@/context/SettingsContext";
import { fetchAlerts, fetchReport } from "@/services/spandanaService";
import type { AlertItem, MaintenanceReport } from "@/types";
import { formatFault, formatTime } from "@/utils/format";
import { statusFromScore } from "@/utils/status";

function LatestReportPreview({ machineId }: { machineId: string | null }) {
  const [report, setReport] = useState<MaintenanceReport | null>(null);
  useEffect(() => {
    if (!machineId) return;
    let active = true;
    fetchReport(machineId).then(({ data }) => {
      if (active) setReport(data);
    });
    return () => {
      active = false;
    };
  }, [machineId]);

  return (
    <Card className="p-5">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="font-display text-lg text-foreground">Latest AI Report</h3>
        <Link to="/reports" className="text-sm text-primary hover:underline">
          View all
        </Link>
      </div>
      {!report ? (
        <p className="text-sm text-muted">
          No report yet — run Live Monitoring or Predictions to generate one.
        </p>
      ) : (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <StatusBadge status={report.severity} />
            <span className="text-xs text-muted">
              {formatTime(report.timestamp)}
            </span>
          </div>
          <p className="font-display text-base text-foreground">{report.title}</p>
          <p className="text-sm text-muted">{report.summary}</p>
          {report.recommended_action[0] && (
            <div className="rounded-xl border border-border bg-background/50 p-3">
              <p className="text-xs uppercase tracking-wide text-muted">
                Top recommended action
              </p>
              <p className="mt-1 text-sm text-foreground">
                {report.recommended_action[0]}
              </p>
            </div>
          )}
          <Link to="/reports">
            <Button variant="secondary" size="sm">
              Full report <ArrowUpRight size={15} />
            </Button>
          </Link>
        </div>
      )}
    </Card>
  );
}

export default function Dashboard() {
  const { machines, loading } = useMachines();
  const { replaySpeed } = useSettings();
  const [alerts, setAlerts] = useState<AlertItem[]>([]);

  // Real, low-frequency live inference for the dashboard health pulse (no RAG
  // calls here -- ragEvery is set high so this stays a lightweight real curve).
  const { series, latest, live } = useLiveInference({
    machineId: "DASH_LIVE_MOTOR",
    source: "metropt3",
    running: true,
    replaySpeed,
    window: 28,
    ragEvery: 9999,
  });

  const summary = useMemo(() => {
    const total = machines.length;
    const healthy = machines.filter((m) => m.status === "healthy").length;
    const warning = machines.filter((m) => m.status === "warning").length;
    const critical = machines.filter((m) => m.status === "critical").length;
    const average_health =
      total === 0 ? 0 : machines.reduce((s, m) => s + m.health_score, 0) / total;
    return { total, healthy, warning, critical, average_health };
  }, [machines]);

  const criticalMachine = useMemo(() => {
    if (machines.length === 0) return null;
    return [...machines].sort((a, b) => a.health_score - b.health_score)[0];
  }, [machines]);

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

      {loading ? (
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
          {Array.from({ length: 5 }).map((_, i) => (
            <CardSkeleton key={i} />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
          <HealthCard label="Total Machines" value={summary.total} icon={Layers} tone="primary" index={0} />
          <HealthCard label="Healthy" value={summary.healthy} icon={HeartPulse} tone="success" index={1} />
          <HealthCard label="Warning" value={summary.warning} icon={TriangleAlert} tone="warning" index={2} />
          <HealthCard label="Critical" value={summary.critical} icon={ShieldAlert} tone="critical" index={3} />
          <HealthCard label="Average Health" value={summary.average_health} decimals={1} suffix="%" icon={ThermometerSun} tone="primary" index={4} />
        </div>
      )}

      {/* Machine status table */}
      <section className="mt-6">
        <h2 className="mb-3 font-display text-xl text-foreground">Machine Status</h2>
        {loading ? <CardSkeleton /> : <MachineTable machines={machines} />}
      </section>

      {/* Real live inference pulse */}
      <section className="mt-6">
        <Card className="p-5">
          <div className="mb-3 flex items-center justify-between">
            <div>
              <h2 className="font-display text-xl text-foreground">Live Model Inference</h2>
              <p className="text-xs text-muted">
                {live ? "Real health-score output from the LTC" : "Backend offline — demo fallback"} · updates in real time
              </p>
            </div>
            <div className="text-right">
              <p className="text-2xl text-foreground tnum">
                {latest ? latest.health.toFixed(1) : "—"}
              </p>
              <p className="text-xs text-muted">
                {latest ? formatFault(latest.predicted_fault) : "warming up…"}
              </p>
            </div>
          </div>
          <div className="h-40">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={series} margin={{ top: 6, right: 6, bottom: 0, left: -20 }}>
                <CartesianGrid stroke="var(--grid-line)" vertical={false} />
                <XAxis dataKey="label" tick={{ fill: "var(--text-muted)", fontSize: 10 }} tickLine={false} axisLine={false} minTickGap={50} />
                <YAxis domain={[0, 100]} tick={{ fill: "var(--text-muted)", fontSize: 10 }} tickLine={false} axisLine={false} />
                <Tooltip
                  contentStyle={{ background: "var(--card)", border: "1px solid var(--border)", borderRadius: 12, color: "var(--text)" }}
                  labelStyle={{ color: "var(--text-muted)" }}
                />
                <Line
                  type="monotone"
                  dataKey="health"
                  stroke={latest ? (statusFromScore(latest.health) === "critical" ? "var(--critical)" : statusFromScore(latest.health) === "warning" ? "var(--warning)" : "var(--success)") : "var(--primary)"}
                  strokeWidth={2.5}
                  dot={false}
                  isAnimationActive={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </section>

      {/* Alerts + real latest report */}
      <section className="mt-6 grid gap-4 lg:grid-cols-2">
        <AlertCard alerts={alerts} />
        <LatestReportPreview machineId={criticalMachine?.id ?? null} />
      </section>
    </PageTransition>
  );
}
