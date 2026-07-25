import { useEffect, useRef, useState } from "react";
import type { DashboardMachineStatus, MaintenanceReport, KnowledgeChunk } from "@/types";
import { runPrediction, simulateWindow, isBackendLive } from "@/services/spandanaService";

/*
  Streams REAL model output. Each tick sends one sensor window (a scripted
  degradation profile, since there is no physical sensor attached) to the
  actual trained LTC via the backend and plots what the MODEL returns --
  health_score, anomaly_score, fault_probability are genuine inference, not a
  client-side animation. The input profile drifts a machine from healthy
  toward a fault and back, so you watch the model's real assessment respond.

  Fast path: POST /predict every tick (real LTC, low latency). Every
  `ragEvery` ticks it instead uses POST /api/v1/sensor-stream, which also runs
  the real RAG retrieval + report, so the RAG panel refreshes with genuinely
  retrieved knowledge without bottlenecking the chart.
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
  ragEvery?: number;
}

export function useLiveInference({
  machineId,
  source,
  running,
  replaySpeed,
  window: windowSize = 40,
  ragEvery = 6,
}: Options) {
  const [series, setSeries] = useState<LivePoint[]>([]);
  const [dashboard, setDashboard] = useState<DashboardMachineStatus | null>(null);
  const [report, setReport] = useState<MaintenanceReport | null>(null);
  const [chunks, setChunks] = useState<KnowledgeChunk[]>([]);
  const [live, setLive] = useState(false);
  const tickRef = useRef(0);
  const phaseRef = useRef(0);
  const dirRef = useRef(1);

  useEffect(() => {
    if (!running) return;
    let active = true;

    const tick = async () => {
      // triangle wave: drift up to a fault, then recover, and repeat
      phaseRef.current += dirRef.current * 0.05;
      if (phaseRef.current >= 1) { phaseRef.current = 1; dirRef.current = -1; }
      if (phaseRef.current <= 0) { phaseRef.current = 0; dirRef.current = 1; }

      const features = driftWindow(phaseRef.current);
      const now = new Date();
      const label = now.toLocaleTimeString(undefined, {
        hour: "2-digit", minute: "2-digit", second: "2-digit",
      });
      const isRagTick = tickRef.current % ragEvery === 0;
      tickRef.current += 1;

      if (isRagTick) {
        const { data } = await simulateWindow(machineId, source, features);
        if (!active) return;
        setDashboard(data);
        setReport(data.report);
        setChunks(data.retrieval?.chunks ?? []);
        pushPoint(data.prediction, label);
      } else {
        const { data } = await runPrediction(machineId, source, features);
        if (!active) return;
        pushPoint(data, label);
      }
      setLive(isBackendLive());
    };

    const pushPoint = (
      p: { health_score: number; anomaly_score: number; fault_probability: number; predicted_fault: string; prediction_confidence: number },
      label: string,
    ) => {
      setSeries((prev) => {
        const point: LivePoint = {
          label,
          health: p.health_score,
          anomaly: Number((p.anomaly_score * 100).toFixed(1)),
          fault: Number((p.fault_probability * 100).toFixed(1)),
          predicted_fault: p.predicted_fault,
          confidence: p.prediction_confidence,
        };
        const next = [...prev, point];
        return next.length > windowSize ? next.slice(next.length - windowSize) : next;
      });
    };

    const intervalMs = Math.max(350, 1500 / replaySpeed);
    tick();
    const id = globalThis.setInterval(tick, intervalMs);
    return () => {
      active = false;
      globalThis.clearInterval(id);
    };
  }, [machineId, source, running, replaySpeed, windowSize, ragEvery]);

  return {
    series,
    latest: series[series.length - 1] ?? null,
    dashboard,
    report,
    chunks,
    live,
  };
}
