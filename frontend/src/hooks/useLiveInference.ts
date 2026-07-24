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

const HEALTHY: Record<string, number> = {
  rms: 0.42, kurtosis: 3.0, skewness: 0.1, crest_factor: 3.2,
  dominant_frequency: 50, temperature: 62, current: 4.2, rpm: 1480,
};
const FAULT: Record<string, number> = {
  rms: 2.7, kurtosis: 5.4, skewness: 0.95, crest_factor: 5.8,
  dominant_frequency: 165, temperature: 87, current: 6.3, rpm: 1508,
};
const KEYS = Object.keys(HEALTHY);

function driftWindow(phase: number): Record<string, number> {
  // phase 0 -> healthy, 1 -> fault; small noise so successive windows differ.
  const f: Record<string, number> = {};
  for (const k of KEYS) {
    const base = HEALTHY[k] + (FAULT[k] - HEALTHY[k]) * phase;
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
