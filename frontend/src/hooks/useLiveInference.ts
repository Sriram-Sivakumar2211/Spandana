import { useCallback, useEffect, useRef, useState } from "react";
import type { DashboardMachineStatus, MaintenanceReport, KnowledgeChunk } from "@/types";
import { runPrediction, simulateWindow, isBackendLive } from "@/services/spandanaService";

/*
  Streams REAL model output. Each tick sends one sensor window (a scripted
  degradation profile, since there is no physical sensor attached) to the
  actual trained LTC via POST /predict and plots what the MODEL returns --
  health_score, anomaly_score, fault_probability are genuine inference, not a
  client-side animation. The input profile drifts a machine from healthy
  toward a fault and back, so you watch the model's real assessment respond.

  The chart loop deliberately NEVER calls the RAG+Gemini pipeline
  automatically. Google's free-tier Gemini quota is 20 requests/day; an
  earlier version of this hook called it on a timer (every few ticks) and
  exhausted the entire day's quota within minutes of the page being open,
  after which every report anywhere in the app silently fell back to the
  offline generator. generateReport() below is the only way to trigger a
  RAG+Gemini call from this page, and it only runs when explicitly invoked
  (a button click), so the number of Gemini calls made is always exactly the
  number of times a person chose to make one.
*/

export interface LivePoint {
  label: string;
  health: number;
  anomaly: number;
  fault: number;
  predicted_fault: string;
  confidence: number;
}

// Both endpoints are real training records, not invented numbers -- same
// values as services/mockData.ts::SIMULATE_SCENARIOS, pulled from
// data/unified_schema/{squirrel_cage,metropt3}_standardized.jsonl. Chosen
// deliberately: MetroPT-3 has zero "healthy"-labeled records in this project
// (100% "faulty") and squirrel-cage has zero "faulty" records (100%
// "healthy"), so a genuine healthy<->fault drift needs one endpoint from
// each. The "source" field only matters for routing bearing vs. general
// model (see backend/app.py::_run_inference), so blending across these two
// non-bearing sources is safe -- both are served by the same general model.
const HEALTHY: Record<string, number> = {
  rms: 0.2465, kurtosis: 3.0, skewness: 0.0, crest_factor: 4.5725,
  dominant_frequency: 0.0, temperature: 0.2187, current: 4.0, rpm: 1480,
  hotspot_ratio: 0.15, hotspot_intensity: 0.7317,
};
const FAULT: Record<string, number> = {
  rms: 0.04, kurtosis: 7.0, skewness: -0.0, crest_factor: 1.0623,
  dominant_frequency: 0.3, temperature: 53.05, current: 0.04, rpm: 1480,
  tp2_pressure: -0.013, tp3_pressure: 9.0586,
};
const KEYS = Array.from(new Set([...Object.keys(HEALTHY), ...Object.keys(FAULT)]));

function driftWindow(phase: number): Record<string, number> {
  // phase 0 -> healthy, 1 -> fault; small noise so successive windows differ.
  // HEALTHY/FAULT are two different real records with slightly different
  // populated keys (e.g. hotspot_* only on the healthy side, tp2/tp3_pressure
  // only on the fault side) -- missing on one side defaults to 0, matching
  // fill_feature_vector's own zero-fill semantics, not an arbitrary choice.
  const f: Record<string, number> = {};
  for (const k of KEYS) {
    const h = HEALTHY[k] ?? 0;
    const ft = FAULT[k] ?? 0;
    const base = h + (ft - h) * phase;
    f[k] = base * (1 + (Math.random() - 0.5) * 0.05);
  }
  return f;
}

interface Options {
  machineId: string;
  source: string;
  running: boolean;
  replaySpeed: number;
  window?: number;
}

export function useLiveInference({
  machineId,
  source,
  running,
  replaySpeed,
  window: windowSize = 40,
}: Options) {
  const [series, setSeries] = useState<LivePoint[]>([]);
  const [dashboard, setDashboard] = useState<DashboardMachineStatus | null>(null);
  const [report, setReport] = useState<MaintenanceReport | null>(null);
  const [chunks, setChunks] = useState<KnowledgeChunk[]>([]);
  const [live, setLive] = useState(false);
  const [generatingReport, setGeneratingReport] = useState(false);
  const phaseRef = useRef(0);
  const dirRef = useRef(1);
  const lastFeaturesRef = useRef<Record<string, number>>(driftWindow(0));

  useEffect(() => {
    if (!running) return;
    let active = true;

    const tick = async () => {
      // triangle wave: drift up to a fault, then recover, and repeat
      phaseRef.current += dirRef.current * 0.05;
      if (phaseRef.current >= 1) { phaseRef.current = 1; dirRef.current = -1; }
      if (phaseRef.current <= 0) { phaseRef.current = 0; dirRef.current = 1; }

      const features = driftWindow(phaseRef.current);
      lastFeaturesRef.current = features;
      const now = new Date();
      const label = now.toLocaleTimeString(undefined, {
        hour: "2-digit", minute: "2-digit", second: "2-digit",
      });

      const { data } = await runPrediction(machineId, source, features);
      if (!active) return;
      setSeries((prev) => {
        const point: LivePoint = {
          label,
          health: data.health_score,
          anomaly: Number((data.anomaly_score * 100).toFixed(1)),
          fault: Number((data.fault_probability * 100).toFixed(1)),
          predicted_fault: data.predicted_fault,
          confidence: data.prediction_confidence,
        };
        const next = [...prev, point];
        return next.length > windowSize ? next.slice(next.length - windowSize) : next;
      });
      setLive(isBackendLive());
    };

    const intervalMs = Math.max(350, 1500 / replaySpeed);
    tick();
    const id = globalThis.setInterval(tick, intervalMs);
    return () => {
      active = false;
      globalThis.clearInterval(id);
    };
  }, [machineId, source, running, replaySpeed, windowSize]);

  // Deliberate, single RAG+Gemini call using the model's current input window
  // -- call this from a button, never automatically. See module comment.
  const generateReport = useCallback(async () => {
    setGeneratingReport(true);
    try {
      const { data } = await simulateWindow(machineId, source, lastFeaturesRef.current);
      setDashboard(data);
      setReport(data.report);
      setChunks(data.retrieval?.chunks ?? []);
      setLive(isBackendLive());
    } finally {
      setGeneratingReport(false);
    }
  }, [machineId, source]);

  return {
    series,
    latest: series[series.length - 1] ?? null,
    dashboard,
    report,
    chunks,
    live,
    generateReport,
    generatingReport,
  };
}
