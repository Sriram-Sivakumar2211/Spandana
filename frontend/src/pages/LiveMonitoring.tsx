import { useState } from "react";
import { Activity, Cpu, Gauge, Pause, Play, Radio, TriangleAlert } from "lucide-react";
import {
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  CartesianGrid,
  Legend,
} from "recharts";
import { PageTransition } from "@/components/layout/PageTransition";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { ReportCard } from "@/components/features/ReportCard";
import { KnowledgeSourcesCard } from "@/components/features/KnowledgeSourcesCard";
import { useLiveInference } from "@/hooks/useLiveInference";
import { useSettings } from "@/context/SettingsContext";
import { statusFromScore } from "@/utils/status";
import { formatFault, pct } from "@/utils/format";

const LIVE_MACHINE = "LIVE_DEMO_MOTOR";

function Stat({
  icon: Icon,
  label,
  value,
  tone = "foreground",
}: {
  icon: typeof Gauge;
  label: string;
  value: string;
  tone?: "foreground" | "success" | "warning" | "critical";
}) {
  const toneClass = {
    foreground: "text-foreground",
    success: "text-success",
    warning: "text-warning",
    critical: "text-critical",
  }[tone];
  return (
    <Card className="p-4">
      <div className="mb-1 flex items-center gap-1.5 text-muted">
        <Icon size={14} />
        <span className="text-xs">{label}</span>
      </div>
      <p className={`text-2xl tnum ${toneClass}`}>{value}</p>
    </Card>
  );
}

export default function LiveMonitoring() {
  const [running, setRunning] = useState(true);
  const { replaySpeed } = useSettings();
  const { series, latest, report, chunks, live } = useLiveInference({
    machineId: LIVE_MACHINE,
    source: "metropt3",
    running,
    replaySpeed,
    window: 44,
  });

  const status = latest ? statusFromScore(latest.health) : "healthy";
  const healthTone =
    status === "healthy" ? "success" : status === "warning" ? "warning" : "critical";

  return (
    <PageTransition>
      <PageHeader
        title="Live Monitoring"
        subtitle="Real LTC inference on a scripted degradation profile — the curves below are genuine model output, not an animation."
        breadcrumbs={[{ label: "Home", to: "/" }, { label: "Live Monitoring" }]}
        actions={
          <Button
            variant={running ? "secondary" : "primary"}
            size="sm"
            onClick={() => setRunning((r) => !r)}
          >
            {running ? <Pause size={15} /> : <Play size={15} />}
            {running ? "Pause" : "Resume"}
          </Button>
        }
      />

      {/* Live status strip */}
      <div className="mb-5 flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-muted">
        <span className="flex items-center gap-2">
          <span className="relative flex h-2.5 w-2.5">
            {running && (
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary opacity-60" />
            )}
            <span
              className="relative inline-flex h-2.5 w-2.5 rounded-full"
              style={{ background: running ? "var(--primary)" : "var(--text-muted)" }}
            />
          </span>
          <Radio size={15} />
          {running ? "Streaming live inference" : "Paused"}
        </span>
        <span className="flex items-center gap-1.5">
          <Cpu size={14} />
          {live ? "Backend model connected" : "Backend offline — demo fallback"}
        </span>
        <span className="flex items-center gap-1.5">
          <Gauge size={14} />
          {replaySpeed.toFixed(1)}× replay speed
        </span>
      </div>

      {/* Current model assessment */}
      <div className="mb-5 grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Stat
          icon={Gauge}
          label="Health Score"
          value={latest ? latest.health.toFixed(1) : "—"}
          tone={healthTone}
        />
        <Stat
          icon={TriangleAlert}
          label="Predicted Condition"
          value={latest ? formatFault(latest.predicted_fault) : "—"}
        />
        <Stat
          icon={Activity}
          label="Anomaly Score"
          value={latest ? (latest.anomaly / 100).toFixed(3) : "—"}
          tone="warning"
        />
        <Stat
          icon={Cpu}
          label="Confidence"
          value={latest ? pct(latest.confidence, 1) : "—"}
        />
      </div>

      {/* Real model-output timeline */}
      <Card className="mb-5 p-5">
        <div className="mb-3 flex items-center justify-between">
          <div>
            <p className="text-sm text-muted">Model Output Timeline</p>
            <p className="text-xs text-muted">
              health · anomaly · fault-probability, streamed from the live model
            </p>
          </div>
          {latest && <StatusBadge status={status} />}
        </div>
        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={series} margin={{ top: 8, right: 8, bottom: 0, left: -16 }}>
              <CartesianGrid stroke="var(--grid-line)" vertical={false} />
              <XAxis
                dataKey="label"
                tick={{ fill: "var(--text-muted)", fontSize: 11 }}
                tickLine={false}
                axisLine={false}
                minTickGap={44}
              />
              <YAxis
                domain={[0, 100]}
                tick={{ fill: "var(--text-muted)", fontSize: 11 }}
                tickLine={false}
                axisLine={false}
              />
              <Tooltip
                contentStyle={{
                  background: "var(--card)",
                  border: "1px solid var(--border)",
                  borderRadius: 12,
                  color: "var(--text)",
                }}
                labelStyle={{ color: "var(--text-muted)" }}
              />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Line
                type="monotone"
                name="Health score"
                dataKey="health"
                stroke="var(--success)"
                strokeWidth={2.5}
                dot={false}
                isAnimationActive={false}
              />
              <Line
                type="monotone"
                name="Anomaly %"
                dataKey="anomaly"
                stroke="var(--warning)"
                strokeWidth={2}
                dot={false}
                isAnimationActive={false}
              />
              <Line
                type="monotone"
                name="Fault probability %"
                dataKey="fault"
                stroke="var(--critical)"
                strokeWidth={2}
                dot={false}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </Card>

      {/* Live RAG grounding for the current model state */}
      <div className="grid gap-5 lg:grid-cols-[1fr_360px]">
        <div>
          {report ? (
            <ReportCard
              report={report}
              onDownload={() => {
                const blob = new Blob([JSON.stringify(report, null, 2)], {
                  type: "application/json",
                });
                const url = URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = url;
                a.download = `spandana-live-report.json`;
                a.click();
                URL.revokeObjectURL(url);
              }}
            />
          ) : (
            <Card className="p-8 text-center text-sm text-muted">
              Generating the first RAG-grounded assessment from the live model
              state…
            </Card>
          )}
        </div>
        <div>
          <KnowledgeSourcesCard query="" chunks={chunks} />
          <Card className="mt-5 p-5">
            <h3 className="mb-2 font-display text-lg text-foreground">
              What you're watching
            </h3>
            <p className="text-sm text-muted">
              Each second, a sensor window is streamed through the trained
              Liquid Time-Constant model on the backend. Because the model keeps
              a continuous-time hidden state per machine, the curve reflects the
              machine's evolving condition — not independent guesses. The RAG
              panel re-grounds every few windows against the maintenance
              knowledge base.
            </p>
          </Card>
        </div>
      </div>
    </PageTransition>
  );
}
