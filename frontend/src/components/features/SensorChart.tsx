import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card } from "@/components/ui/Card";
import type { SensorSample } from "@/types";

interface SensorChartProps {
  title: string;
  unit: string;
  data: SensorSample[];
  dataKey: keyof SensorSample;
  color: string;
  domain?: [number | "auto", number | "auto"];
}

function ChartTooltip({
  active,
  payload,
  unit,
}: {
  active?: boolean;
  payload?: Array<{ value: number; payload: SensorSample }>;
  unit: string;
}) {
  if (!active || !payload || payload.length === 0) return null;
  const p = payload[0];
  return (
    <div className="rounded-lg border border-border bg-card px-3 py-2 shadow-soft-lg">
      <p className="text-xs text-muted">{p.payload.label}</p>
      <p className="text-sm font-medium text-foreground tnum">
        {Number(p.value).toFixed(2)} {unit}
      </p>
    </div>
  );
}

export function SensorChart({
  title,
  unit,
  data,
  dataKey,
  color,
  domain = ["auto", "auto"],
}: SensorChartProps) {
  const gradientId = `grad-${String(dataKey)}`;
  const latest = data[data.length - 1]?.[dataKey];

  return (
    <Card className="p-4">
      <div className="mb-2 flex items-center justify-between">
        <div>
          <p className="text-sm text-muted">{title}</p>
          <p className="text-xl text-foreground tnum">
            {typeof latest === "number" ? latest.toFixed(2) : "—"}
            <span className="ml-1 text-xs text-muted">{unit}</span>
          </p>
        </div>
        <span
          className="h-2 w-2 animate-pulseline rounded-full"
          style={{ background: color }}
        />
      </div>
      <div className="h-32">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: -24 }}>
            <defs>
              <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={color} stopOpacity={0.35} />
                <stop offset="100%" stopColor={color} stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke="var(--grid-line)" vertical={false} />
            <XAxis
              dataKey="label"
              tick={{ fill: "var(--text-muted)", fontSize: 10 }}
              tickLine={false}
              axisLine={false}
              minTickGap={40}
            />
            <YAxis
              domain={domain}
              tick={{ fill: "var(--text-muted)", fontSize: 10 }}
              tickLine={false}
              axisLine={false}
              width={40}
            />
            <Tooltip
              content={<ChartTooltip unit={unit} />}
              cursor={{ stroke: color, strokeOpacity: 0.3 }}
            />
            <Area
              type="monotone"
              dataKey={dataKey as string}
              stroke={color}
              strokeWidth={2}
              fill={`url(#${gradientId})`}
              isAnimationActive={false}
              dot={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}
