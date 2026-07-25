import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowUpRight, Gauge, Thermometer, Zap, Wind } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { statusColor } from "@/utils/status";
import { formatFault, formatMaybe, formatRpm, formatSource, timeAgo } from "@/utils/format";
import type { Machine } from "@/types";

function Metric({
  icon: Icon,
  value,
  unit,
}: {
  icon: typeof Gauge;
  value: string;
  unit: string;
}) {
  return (
    <div className="flex min-w-0 items-center gap-2">
      <Icon size={15} className="shrink-0 text-muted" />
      <span className="truncate text-sm text-foreground tnum">{value}</span>
      <span className="shrink-0 text-xs text-muted">{unit}</span>
    </div>
  );
}

export function MachineCard({ machine, index = 0 }: { machine: Machine; index?: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05, duration: 0.35 }}
      whileHover={{ y: -4 }}
    >
      <Card className="flex h-full flex-col p-5 transition-shadow hover:shadow-soft-lg">
        <div className="flex items-start justify-between">
          <div className="min-w-0">
            <h3 className="truncate font-display text-lg text-foreground">
              {machine.name}
            </h3>
            <p className="text-xs text-muted">
              {machine.id} · {machine.source ? formatSource(machine.source) : "Unknown source"}
            </p>
          </div>
          <StatusBadge status={machine.status} />
        </div>

        <div className="mt-4">
          <div className="mb-1.5 flex items-center justify-between text-xs">
            <span className="text-muted">Health Score</span>
            <span className="text-foreground tnum">
              {machine.health_score.toFixed(1)}%
            </span>
          </div>
          <ProgressBar
            value={machine.health_score}
            color={statusColor(machine.status)}
          />
        </div>

        <div className="mt-4 grid grid-cols-2 gap-3">
          <Metric icon={Thermometer} value={formatMaybe(machine.temperature, 1)} unit="°C" />
          <Metric icon={Wind} value={formatRpm(machine.rpm)} unit="rpm" />
          <Metric icon={Zap} value={formatMaybe(machine.current, 1)} unit="A" />
          <Metric icon={Gauge} value={formatMaybe(machine.vibration, 2)} unit="mm/s" />
        </div>

        <div className="mt-4 flex items-center justify-between border-t border-border pt-3">
          <div>
            <p className="text-[11px] uppercase tracking-wide text-muted">
              Prediction
            </p>
            <p className="text-sm text-foreground">
              {formatFault(machine.predicted_fault)}
            </p>
          </div>
          <p className="text-[11px] text-muted">{timeAgo(machine.last_updated)}</p>
        </div>

        <Link
          to={`/machines/${machine.id}`}
          className="mt-4 inline-flex items-center justify-center gap-1.5 rounded-xl border border-border py-2 text-sm text-foreground transition-colors hover:border-primary hover:text-primary"
        >
          View Details <ArrowUpRight size={15} />
        </Link>
      </Card>
    </motion.div>
  );
}
