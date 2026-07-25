import { useEffect, useState } from "react";
import { PlayCircle } from "lucide-react";
import { PageTransition } from "@/components/layout/PageTransition";
import { PageHeader } from "@/components/ui/PageHeader";
import { PredictionCard } from "@/components/features/PredictionCard";
import { ModelInfoCard } from "@/components/features/ModelInfoCard";
import { ReportCard } from "@/components/features/ReportCard";
import { KnowledgeSourcesCard } from "@/components/features/KnowledgeSourcesCard";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { CardSkeleton } from "@/components/ui/LoadingSkeleton";
import { useMachines } from "@/hooks/useMachines";
import { fetchPrediction, fetchReport, simulateWindow } from "@/services/spandanaService";
import { SIMULATE_SCENARIOS } from "@/services/mockData";
import type { KnowledgeChunk, MaintenanceReport, Prediction } from "@/types";
import { cn } from "@/utils/cn";

const BEARING_SOURCES = new Set(["nasa_ims", "cwru", "paderborn"]);

// On a fresh backend, /machines returns [] until a real prediction has ever
// been made -- with nothing to select, the Simulate buttons would stay
// disabled forever and there'd be no way to get started. This fallback entry
// keeps the page usable from a cold start: picking it and clicking Simulate
// runs the REAL model exactly like any other machine (the backend creates
// the machine record on first prediction, it doesn't need to pre-exist).
const DEFAULT_MACHINE = { id: "DEMO_MOTOR_01", name: "Demo Motor 01" };

export default function Predictions() {
  const { machines } = useMachines();
  const [selected, setSelected] = useState<string>(DEFAULT_MACHINE.id);
  const [prediction, setPrediction] = useState<Prediction | null>(null);
  const [report, setReport] = useState<MaintenanceReport | null>(null);
  const [retrieval, setRetrieval] = useState<{ query: string; chunks: KnowledgeChunk[] } | null>(null);
  const [loading, setLoading] = useState(false);
  const [simulating, setSimulating] = useState<string | null>(null);

  const selectorOptions =
    machines.length > 0 ? machines.map((m) => ({ id: m.id, name: m.name })) : [DEFAULT_MACHINE];
  const machine = machines.find((m) => m.id === selected);
  const modelKind = machine && BEARING_SOURCES.has(String(machine.source)) ? "bearing" : "general";

  useEffect(() => {
    // Once real machines exist, prefer selecting a real one over the
    // placeholder -- but only if the user hasn't already picked something.
    if (machines.length > 0 && selected === DEFAULT_MACHINE.id) {
      setSelected(machines[0].id);
    }
  }, [machines, selected]);

  useEffect(() => {
    if (!selected) return;
    let active = true;
    setLoading(true);
    setRetrieval(null);
    (async () => {
      const [p, r] = await Promise.all([fetchPrediction(selected), fetchReport(selected)]);
      if (!active) return;
      setPrediction(p.data);
      setReport(r.data);
      setLoading(false);
    })();
    return () => {
      active = false;
    };
  }, [selected]);

  const runSimulation = async (scenario: (typeof SIMULATE_SCENARIOS)[number]) => {
    if (!selected) return;
    setSimulating(scenario.key);
    const { data } = await simulateWindow(selected, scenario.source, { ...scenario.features });
    setPrediction(data.prediction);
    setReport(data.report);
    setRetrieval(data.retrieval);
    setSimulating(null);
  };

  return (
    <PageTransition>
      <PageHeader
        title="AI Predictions"
        subtitle="Live inference from the Liquid Neural Network (LTC), grounded by the RAG maintenance-intelligence layer."
        breadcrumbs={[{ label: "Home", to: "/" }, { label: "Predictions" }]}
      />

      {/* Machine selector */}
      <div className="mb-4 flex flex-wrap gap-2">
        {selectorOptions.map((m) => (
          <button
            key={m.id}
            onClick={() => setSelected(m.id)}
            className={cn(
              "rounded-xl border px-3 py-1.5 text-sm transition-colors",
              selected === m.id
                ? "border-primary bg-primary/10 text-primary"
                : "border-border text-muted hover:text-foreground",
            )}
          >
            {m.name}
          </button>
        ))}
      </div>

      {/* Simulate controls */}
      <Card className="mb-5 p-4">
        <p className="mb-3 text-xs uppercase tracking-wide text-muted">
          Simulate a sensor window (runs the real model + RAG pipeline)
        </p>
        <div className="flex flex-wrap gap-2">
          {SIMULATE_SCENARIOS.map((s) => (
            <Button
              key={s.key}
              variant="secondary"
              size="sm"
              disabled={!selected || simulating !== null}
              onClick={() => runSimulation(s)}
              title={s.description}
            >
              <PlayCircle size={15} className={simulating === s.key ? "animate-spin" : ""} />
              {s.label}
            </Button>
          ))}
        </div>
      </Card>

      <div className="grid gap-5 lg:grid-cols-[1fr_360px]">
        <div className="space-y-5">
          {loading || !prediction ? (
            <CardSkeleton />
          ) : (
            <PredictionCard prediction={prediction} />
          )}
          {report && (
            <ReportCard report={report} machine={machine} onDownload={() => {
              const blob = new Blob([JSON.stringify(report, null, 2)], { type: "application/json" });
              const url = URL.createObjectURL(blob);
              const a = document.createElement("a");
              a.href = url;
              a.download = `spandana-report-${report.machine_id}.json`;
              a.click();
              URL.revokeObjectURL(url);
            }} />
          )}
          {retrieval && <KnowledgeSourcesCard query={retrieval.query} chunks={retrieval.chunks} />}
        </div>
        <div className="space-y-5">
          <ModelInfoCard modelKind={modelKind} />
          <Card className="p-5">
            <h3 className="mb-2 font-display text-lg text-foreground">
              How to read this
            </h3>
            <ul className="space-y-2 text-sm text-muted">
              <li>
                <span className="text-foreground">Health Score</span> — 0–100
                condition index derived from fault probability.
              </li>
              <li>
                <span className="text-foreground">Anomaly Score</span> —
                unsupervised VAE reconstruction error, independent of the
                classifier.
              </li>
              <li>
                <span className="text-foreground">AI Report</span> — grounded
                in retrieved maintenance documents (see Retrieved Knowledge
                Sources after simulating), not an ungrounded LLM guess.
              </li>
            </ul>
          </Card>
        </div>
      </div>
    </PageTransition>
  );
}
