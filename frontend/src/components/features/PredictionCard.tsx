import { motion } from "framer-motion";
import {
  Activity,
  BrainCircuit,
  Clock,
  Gauge,
  ShieldCheck,
  Sparkles,
  Target,
} from "lucide-react";
import { Card } from "@/components/ui/Card";
import { HealthGauge } from "./HealthGauge";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { formatFault, formatRul, pct } from "@/utils/format";
import { statusFromScore } from "@/utils/status";
import type { Prediction } from "@/types";

function Metric({
  icon: Icon,
  label,
  value,
  sub,
}: {
  icon: typeof Gauge;
  label: string;
  value: string;
  sub?: string;
}) {
  return (
    <div className="rounded-xl border border-border bg-background/50 p-3">
      <div className="mb-1 flex items-center gap-1.5 text-muted">
        <Icon size={14} />
        <span className="text-xs">{label}</span>
      </div>
      <p className="text-lg text-foreground tnum">{value}</p>
      {sub && <p className="text-[11px] text-muted">{sub}</p>}
    </div>
  );
}

export function PredictionCard({ prediction }: { prediction: Prediction }) {
  const status = statusFromScore(prediction.health_score);
  return (
    <Card className="overflow-hidden">
      {/* Primary-model banner */}
      <div className="flex items-center justify-between border-b border-border bg-primary/5 px-5 py-3">
        <div className="flex items-center gap-2">
          <span className="grid h-8 w-8 place-items-center rounded-lg bg-primary text-primary-foreground">
            <BrainCircuit size={17} />
          </span>
          <div>
            <p className="text-sm font-medium text-foreground">
              Liquid Neural Network (LTC)
            </p>
            <p className="text-[11px] text-muted">
              Primary production model · ncps + AutoNCP
            </p>
          </div>
        </div>
        <span className="inline-flex items-center gap-1 rounded-full bg-primary/15 px-2.5 py-1 text-[11px] font-medium text-primary">
          <Sparkles size={12} /> Primary
        </span>
      </div>

      <div className="grid gap-5 p-5 md:grid-cols-[auto_1fr] md:items-center">
        <div className="flex flex-col items-center gap-3">
          <HealthGauge score={prediction.health_score} />
          <StatusBadge status={status} />
        </div>

        <div className="space-y-4">
          <div>
            <p className="text-xs uppercase tracking-wide text-muted">
              Predicted Condition
            </p>
            <motion.p
              key={prediction.predicted_fault}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              className="text-2xl text-foreground"
            >
              {formatFault(prediction.predicted_fault)}
            </motion.p>
            <div className="mt-2 flex items-center gap-2">
              <ProgressBar
                value={prediction.prediction_confidence * 100}
                className="max-w-[200px]"
              />
              <span className="text-xs text-muted tnum">
                {pct(prediction.prediction_confidence, 1)} confidence
              </span>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            <Metric
              icon={Activity}
              label="Anomaly Score"
              value={prediction.anomaly_score.toFixed(3)}
              sub="VAE reconstruction"
            />
            <Metric
              icon={Target}
              label="Fault Probability"
              value={pct(prediction.fault_probability, 1)}
            />
            <Metric
              icon={Clock}
              label="Remaining Life"
              value={formatRul(prediction.remaining_useful_life_hours)}
            />
          </div>

          <div className="flex items-start gap-2 rounded-xl border border-border bg-background/50 p-3">
            <ShieldCheck size={16} className="mt-0.5 shrink-0 text-primary" />
            <div>
              <p className="text-xs uppercase tracking-wide text-muted">
                Recommended Action
              </p>
              <p className="text-sm text-foreground">
                {prediction.recommended_action}
              </p>
            </div>
          </div>

          <p className="text-[11px] text-muted">
            Window <span className="tnum">{prediction.window_id}</span>
          </p>
        </div>
      </div>
    </Card>
  );
}
