import { Check, Cpu, Layers, Timer } from "lucide-react";
import { Card } from "@/components/ui/Card";

/*
  Real, measured metrics for Spandana's two production LTC models (both
  ncps.torch.LTC + AutoNCP, no LSTM anywhere in this project's history) —
  sourced from reports/model_evaluation_report.md (bearing specialist) and
  reports/general_model_evaluation_augmented.json (general model). Which one
  applies depends on which engine served the current prediction (backend/app.py
  routes bearing sources to the specialist, everything else to the general
  model) -- see inference/predict.py and inference/predict_general.py.
*/
const MODEL_INFO = {
  bearing: {
    name: "LTC Bearing Specialist",
    architecture: "Liquid Time-Constant Network · ncps + AutoNCP · 5-class fault location",
    accuracy: 0.8871,
    f1_macro: 0.7397,
    params: 20972,
    mean_latency_ms: 5.67,
  },
  general: {
    name: "LTC General Severity Model",
    architecture: "Liquid Time-Constant Network · ncps + AutoNCP · 3-class severity, 6 datasets",
    accuracy: 0.9947,
    f1_macro: 0.9932,
    params: 14022,
    mean_latency_ms: 3.16,
  },
} as const;

const WHY_LTC = [
  "Continuous-time hidden state carried per machine across windows",
  "Native handling of irregular sensor sampling via elapsed-time input",
  "Compact, low-latency, edge-deployable",
  "Learns fault dynamics rather than fixed-step frames",
];

export function ModelInfoCard({ modelKind }: { modelKind: "bearing" | "general" }) {
  const model = MODEL_INFO[modelKind];
  const stats = [
    { icon: Check, label: "Accuracy", value: (model.accuracy * 100).toFixed(2) + "%" },
    { icon: Layers, label: "F1 (macro)", value: model.f1_macro.toFixed(4) },
    { icon: Cpu, label: "Parameters", value: model.params.toLocaleString() },
    { icon: Timer, label: "Mean latency", value: model.mean_latency_ms.toFixed(2) + " ms" },
  ];
  return (
    <Card className="p-5">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h3 className="font-display text-lg text-foreground">{model.name}</h3>
          <p className="text-xs text-muted">{model.architecture}</p>
        </div>
        <span className="rounded-full bg-primary/15 px-2.5 py-1 text-[11px] font-medium text-primary">
          Production
        </span>
      </div>

      <div className="grid grid-cols-2 gap-3">
        {stats.map((s) => {
          const Icon = s.icon;
          return (
            <div
              key={s.label}
              className="rounded-xl border border-border bg-background/50 p-3"
            >
              <div className="mb-1 flex items-center gap-1.5 text-muted">
                <Icon size={14} />
                <span className="text-xs">{s.label}</span>
              </div>
              <p className="text-lg text-foreground tnum">{s.value}</p>
            </div>
          );
        })}
      </div>

      <div className="mt-4">
        <p className="mb-2 text-xs uppercase tracking-wide text-muted">
          Why a Liquid Neural Network
        </p>
        <ul className="space-y-1.5">
          {WHY_LTC.map((r) => (
            <li key={r} className="flex items-start gap-2 text-sm text-foreground">
              <Check size={15} className="mt-0.5 shrink-0 text-success" />
              {r}
            </li>
          ))}
        </ul>
      </div>
      <p className="mt-3 text-[11px] text-muted">
        Metrics measured on a held-out test split. No LSTM comparison exists in
        this project — it was intentionally removed in favor of the LTC.
      </p>
    </Card>
  );
}
