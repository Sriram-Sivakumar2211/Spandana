import { useEffect, useRef, useState } from "react";
import type { SensorSample } from "@/types";
import { makeSensorSample, seedSensorSeries } from "@/services/mockData";

interface UseStreamOptions {
  intervalMs?: number;
  window?: number;
  running?: boolean;
}

/**
 * Illustrative rolling telemetry for the sensor charts, generated client-side.
 * The real backend (backend/app.py) has no raw-waveform streaming endpoint —
 * its live signal is prediction/health output (GET /machines,
 * /predictions/history), not per-sample sensor telemetry — so this
 * intentionally does not attempt a network call; it is charted as a visual
 * approximation of what a live feed looks like, not live backend data.
 */
export function useStream({
  intervalMs = 1000,
  window = 40,
  running = true,
}: UseStreamOptions = {}) {
  const [series, setSeries] = useState<SensorSample[]>(() =>
    seedSensorSeries(window),
  );
  const latestRef = useRef<SensorSample | null>(series[series.length - 1] ?? null);

  useEffect(() => {
    if (!running) return;
    const tick = () => {
      const sample = makeSensorSample(latestRef.current);
      latestRef.current = sample;
      setSeries((prev) => {
        const next = [...prev, sample];
        return next.length > window ? next.slice(next.length - window) : next;
      });
    };

    const id = globalThis.setInterval(tick, intervalMs);
    return () => globalThis.clearInterval(id);
  }, [intervalMs, window, running]);

  return { series, latest: series[series.length - 1] ?? null };
}
