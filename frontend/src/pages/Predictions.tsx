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
import { fetchPrediction, fetchReport, resetMachine, simulateWindow } from "@/services/spandanaService";
import { SIMULATE_SCENARIOS } from "@/services/mockData";
import type { KnowledgeChunk, Machine, MaintenanceReport, Prediction } from "@/types";
import { cn } from "@/utils/cn";

const BEARING_SOURCES = new Set(["nasa_ims", "cwru", "paderborn"]);

/**
 * Small (+/-1.5%) multiplicative noise per feature, applied fresh on every
 * Simulate click. The model is deterministic -- identical input always
 * produces an identical output, which is mathematically correct but reads as
 * suspicious/hardcoded in a demo when every click shows the exact same
 * number to the decimal. Real sensors never report the literal same value
 * twice either, so this is also just more realistic. The noise is small
 * enough that it never changes which class a scenario lands in -- only the
 * decimals move, not the story.
 */
function jitterFeatures(features: Record<string, number>): Record<string, number> {
  const out: Record<string, number> = {};
  for (const [k, v] of Object.entries(features)) {
    out[k] = v === 0 ? 0 : v * (1 + (Math.random() - 0.5) * 0.03);
  }
  return out;
}

export default function Predictions() {
  const { machines } = useMachines();
  const [selected, setSelected] = useState<string>("");
  const [prediction, setPrediction] = useState<Prediction | null>(null);
  const [report, setReport] = useState<MaintenanceReport | null>(null);
  const [retrieval, setRetrieval] = useState<{ query: string; chunks: KnowledgeChunk[] } | null>(null);
  // What's currently shown in the cards below -- kept separate from
  // `selected` (the machine picker) because a Simulate click displays a
  // DIFFERENT machine (its own dedicated demo ID, see mockData.ts) than
  // whatever happens to be selected in the picker. Passing the picker's
  // machine as context for a simulated result would show the wrong
  // name/source/location next to it.
  const [displayMachine, setDisplayMachine] = useState<Machine | undefined>(undefined);
  const [displaySource, setDisplaySource] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [simulating, setSimulating] = useState<string | null>(null);

  const modelKind = displaySource && BEARING_SOURCES.has(displaySource) ? "bearing" : "general";

  useEffect(() => {
    if (!selected && machines.length > 0) setSelected(machines[0].id);
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
      setDisplayMachine(machines.find((m) => m.id === selected));
      setDisplaySource(machines.find((m) => m.id === selected)?.source ?? null);
      setLoading(false);
    })();
    return () => {
      active = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selected]);

  const runSimulation = async (scenario: (typeof SIMULATE_SCENARIOS)[number]) => {
    setSimulating(scenario.key);
    // Reset first: this scenario's dedicated machine may have accumulated
    // hidden state from earlier clicks (including testing), which would
    // otherwise shift the result away from the clean baseline this scenario
    // is meant to demonstrate. Then jitter the input slightly so repeated
    // clicks show natural variation instead of the identical number forever.
    await resetMachine(scenario.machineId);
    const { data } = await simulateWindow(scenario.machineId, scenario.source, jitterFeatures(scenario.features));
    setPrediction(data.prediction);
    setReport(data.report);
    setRetrieval(data.retrieval);
    // The simulated machine won't be in `machines` immediately (that list
    // refreshes on its own poll), so show it without registry context rather
    // than pairing it with a stale/unrelated Machine object.
    setDisplayMachine(undefined);
    setDisplaySource(scenario.source);
    setSimulating(null);
  };

  return (
    <PageTransition>
      <PageHeader
        title="AI Predictions"
        subtitle="Live inference from the Liquid Neural Network (LTC), grounded by the RAG maintenance-intelligence layer."
        breadcrumbs={[{ label: "Home", to: "/" }, { label: "Predictions" }]}
      />

      {/* Simulate controls -- always available, each button uses its own
          dedicated machine so results never depend on click order. */}
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
              disabled={simulating !== null}
              onClick={() => runSimulation(s)}
              title={s.description}
            >
              <PlayCircle size={15} className={simulating === s.key ? "animate-spin" : ""} />
              {s.label}
            </Button>
          ))}
        </div>
      </Card>

      {/* Machine selector -- browse an already-predicted real machine's
          latest result, separate from the Simulate demo scenarios above. */}
      {machines.length > 0 && (
        <div className="mb-4">
          <p className="mb-2 text-xs uppercase tracking-wide text-muted">
            Or browse a real machine's latest prediction
          </p>
          <div className="flex flex-wrap gap-2">
            {machines.map((m) => (
              <button
                key={m.id}
                onClick={() => setSelected(m.id)}
                className={cn(
                  "rounded-xl border px-3 py-1.5 text-sm transition-colors",
                  selected === m.id && !simulating
                    ? "border-primary bg-primary/10 text-primary"
                    : "border-border text-muted hover:text-foreground",
                )}
              >
                {m.name}
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="grid gap-5 lg:grid-cols-[1fr_360px]">
        <div className="space-y-5">
          {loading || !prediction ? (
            <CardSkeleton />
          ) : (
            <PredictionCard prediction={prediction} />
          )}
          {report && (
            <ReportCard report={report} machine={displayMachine} onDownload={() => {
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
