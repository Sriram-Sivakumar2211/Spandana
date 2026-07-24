import { api } from "./api";
import type {
  AlertItem,
  DashboardMachineStatus,
  FleetSummary,
  HistoryRecord,
  Machine,
  MaintenanceReport,
  Prediction,
} from "@/types";
import {
  MACHINES,
  buildAlerts,
  buildHistory,
  predictionFor,
  reportFor,
} from "./mockData";
import { statusFromScore } from "@/utils/status";

/*
  Each call hits the REAL backend (backend/app.py) first and transparently
  falls back to mock data if it's unreachable, so the UI is always demoable.
  `live` on the return value surfaces which happened, powering the navbar
  "Live" vs "Demo Mode" indicator.
*/

let backendLive = false;
export function isBackendLive(): boolean {
  return backendLive;
}

async function withFallback<T>(
  request: () => Promise<T>,
  fallback: () => T,
): Promise<{ data: T; live: boolean }> {
  try {
    const data = await request();
    backendLive = true;
    return { data, live: true };
  } catch {
    backendLive = false;
    return { data: fallback(), live: false };
  }
}

function withStatus(m: Omit<Machine, "status"> & { status?: unknown }): Machine {
  return { ...m, status: statusFromScore(m.health_score) } as Machine;
}

/** GET /machines — the real in-memory registry, populated by every real prediction made so far. */
export async function fetchMachines() {
  return withFallback<Machine[]>(
    async () => {
      const { data } = await api.get<Omit<Machine, "status">[]>("/machines");
      return data.map(withStatus);
    },
    () => MACHINES,
  );
}

export function summarize(machines: Machine[]): FleetSummary {
  const total = machines.length;
  const healthy = machines.filter((m) => m.status === "healthy").length;
  const warning = machines.filter((m) => m.status === "warning").length;
  const critical = machines.filter((m) => m.status === "critical").length;
  const average_health =
    total === 0 ? 0 : machines.reduce((s, m) => s + m.health_score, 0) / total;
  return { total, healthy, warning, critical, average_health };
}

/** Latest full Prediction for one machine (GET /predictions/history?machine_id=). */
export async function fetchPrediction(machineId: string) {
  return withFallback<Prediction>(
    async () => {
      const { data } = await api.get<Prediction[]>("/predictions/history", {
        params: { machine_id: machineId },
      });
      if (data.length === 0) throw new Error("no predictions yet for this machine");
      return data[data.length - 1];
    },
    () => {
      const m = MACHINES.find((x) => x.id === machineId) ?? MACHINES[0];
      return predictionFor(m);
    },
  );
}

/** GET /predictions/history, joined with machine names for display. */
export async function fetchHistory() {
  return withFallback<HistoryRecord[]>(
    async () => {
      const [{ data: predictions }, { data: machines }] = await Promise.all([
        api.get<Prediction[]>("/predictions/history"),
        api.get<Omit<Machine, "status">[]>("/machines"),
      ]);
      const nameById = new Map(machines.map((m) => [m.id, m.name]));
      return predictions
        .map((p) => ({
          id: p.window_id,
          machine_id: p.machine_id,
          machine_name: nameById.get(p.machine_id) ?? p.machine_id,
          timestamp: p.timestamp,
          predicted_fault: p.predicted_fault,
          prediction_confidence: p.prediction_confidence,
          health_score: p.health_score,
          anomaly_score: p.anomaly_score,
          status: statusFromScore(p.health_score),
          recommended_action: p.recommended_action,
        }))
        .reverse();
    },
    () => buildHistory(),
  );
}

/**
 * Generates a fresh RAG-grounded report for a machine's latest known
 * prediction (POST /report — the real backend has no "GET current report"
 * route, since a report is always generated from a prediction on demand).
 */
export async function fetchReport(machineId: string) {
  return withFallback<MaintenanceReport>(
    async () => {
      const { data: history } = await api.get<Prediction[]>("/predictions/history", {
        params: { machine_id: machineId },
      });
      if (history.length === 0) throw new Error("no predictions yet for this machine");
      const latest = history[history.length - 1];
      const { data: report } = await api.post<MaintenanceReport>("/report", latest);
      return report;
    },
    () => {
      const m = MACHINES.find((x) => x.id === machineId) ?? MACHINES[0];
      return reportFor(m);
    },
  );
}

export async function fetchAlerts() {
  return withFallback<AlertItem[]>(
    async () => (await api.get<AlertItem[]>("/alerts")).data,
    () => buildAlerts(),
  );
}

/**
 * Full RAG-grounded assessment for one machine: takes its latest real
 * prediction and runs it through POST /api/v1/dashboard/machine-status, which
 * returns the model prediction, the retrieved knowledge-base chunks, and the
 * grounded maintenance report together -- everything real, nothing fabricated
 * client-side. Used by the machine detail view.
 */
export async function assessMachine(machineId: string) {
  return withFallback<DashboardMachineStatus>(
    async () => {
      const { data: history } = await api.get<Prediction[]>("/predictions/history", {
        params: { machine_id: machineId },
      });
      if (history.length === 0) throw new Error("no predictions yet for this machine");
      const latest = history[history.length - 1];
      const { data } = await api.post<DashboardMachineStatus>(
        "/api/v1/dashboard/machine-status",
        latest,
      );
      return data;
    },
    () => {
      const m = MACHINES.find((x) => x.id === machineId) ?? MACHINES[0];
      const prediction = predictionFor(m);
      return {
        machine_id: m.id,
        timestamp: prediction.timestamp,
        status: m.status,
        prediction,
        retrieval: { query: "", chunks: [] },
        report: reportFor(m),
      };
    },
  );
}

/**
 * Runs ONE real LTC inference via POST /predict -- the fast path (real trained
 * model, no RAG report generation), so Live Monitoring can stream a genuine
 * model-output curve at ~1s cadence. Every call advances that machine's
 * continuous-time hidden state on the backend (backend/app.py keeps the
 * engines alive across requests), so feeding a drifting window sequence shows
 * the stateful model responding over time -- not a client-side animation.
 * Falls back to the local generator only if the backend is unreachable.
 */
export async function runPrediction(
  machineId: string,
  source: string,
  features: Record<string, number>,
) {
  return withFallback<Prediction>(
    async () =>
      (
        await api.post<Prediction>("/predict", {
          machine_id: machineId,
          source,
          features,
        })
      ).data,
    () => {
      const m = MACHINES.find((x) => x.id === machineId) ?? MACHINES[0];
      return { ...predictionFor(m), health_score: 60 + Math.random() * 35 };
    },
  );
}

/**
 * Submits a labeled demo sensor window to POST /api/v1/sensor-stream and
 * returns the REAL resulting prediction + RAG report (the backend runs the
 * actual trained model -- see backend/app.py::_run_inference -- nothing here
 * is fabricated client-side). Used by the Predictions page's "Simulate"
 * controls; see mockData.ts::SIMULATE_SCENARIOS for what each scenario sends.
 */
export async function simulateWindow(
  machineId: string,
  source: string,
  features: Record<string, number>,
) {
  return withFallback<DashboardMachineStatus>(
    async () =>
      (
        await api.post<DashboardMachineStatus>("/api/v1/sensor-stream", {
          machine_id: machineId,
          source,
          features,
        })
      ).data,
    () => {
      const m = MACHINES.find((x) => x.id === machineId) ?? MACHINES[0];
      const prediction = predictionFor(m);
      return {
        machine_id: m.id,
        timestamp: prediction.timestamp,
        status: m.status,
        prediction,
        retrieval: { query: "", chunks: [] },
        report: reportFor(m),
      };
    },
  );
}
