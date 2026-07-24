import { useState } from "react";
import { Pause, Play, Radio } from "lucide-react";
import {
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  CartesianGrid,
} from "recharts";
import { PageTransition } from "@/components/layout/PageTransition";
import { PageHeader } from "@/components/ui/PageHeader";
import { SensorChart } from "@/components/features/SensorChart";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { useStream } from "@/hooks/useStream";
import { statusColor, statusFromScore } from "@/utils/status";

export default function LiveMonitoring() {
  const [running, setRunning] = useState(true);
  const { series, latest } = useStream({ intervalMs: 1000, window: 48, running });
  const healthColor = latest
    ? statusColor(statusFromScore(latest.health))
    : "var(--primary)";

  return (
    <PageTransition>
      <PageHeader
        title="Live Monitoring"
        subtitle="Illustrative telemetry, refreshed every second — use Predictions to run the real model on a sensor window."
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

      <div className="mb-5 flex items-center gap-2 text-sm text-muted">
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
        {running ? "Streaming live" : "Stream paused"}
      </div>

      {/* Big health timeline */}
      <Card className="mb-5 p-5">
        <div className="mb-3 flex items-center justify-between">
          <div>
            <p className="text-sm text-muted">Health Score Timeline</p>
            <p className="text-3xl text-foreground tnum">
              {latest ? latest.health.toFixed(1) : "—"}
              <span className="ml-1 text-sm text-muted">/ 100</span>
            </p>
          </div>
        </div>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={series}
              margin={{ top: 8, right: 8, bottom: 0, left: -16 }}
            >
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
              <Line
                type="monotone"
                dataKey="health"
                stroke={healthColor}
                strokeWidth={2.5}
                dot={false}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </Card>

      {/* Sensor grid */}
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
    </PageTransition>
  );
}
