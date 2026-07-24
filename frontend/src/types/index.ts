/*
  These interfaces mirror the REAL Spandana backend (backend/app.py) field-for-
  field: Prediction matches backend/schema/model_prediction.json exactly;
  MaintenanceReport matches backend/schema/maintenance_report.json exactly;
  DashboardMachineStatus matches backend/schemas/dashboard_payload.json.
  Machine/FleetSummary/AlertItem mirror backend/app.py's in-memory
  _MACHINE_REGISTRY / /dashboard/summary / /alerts response shapes, which
  aren't formal JSON Schemas but are real, stable response contracts.
*/

export type HealthStatus = "healthy" | "warning" | "critical";

export type SourceDataset =
  | "squirrel_cage"
  | "metropt3"
  | "thermal_motor"
  | "cwru"
  | "paderborn"
  | "nasa_ims";

/** One model prediction — matches backend/schema/model_prediction.json field-for-field. */
export interface Prediction {
  machine_id: string;
  window_id: string;
  timestamp: string;
  health_score: number; // 0..100
  anomaly_score: number; // 0..1
  fault_probability: number; // 0..1
  predicted_fault: string; // bearing specialist: healthy/inner_race/outer_race/ball/combined; general model: healthy/warning/faulty
  prediction_confidence: number; // 0..1
  remaining_useful_life_hours: number | null;
  recommended_action: string;
}

/** Live telemetry sample for the streaming charts (client-side only; not a backend contract). */
export interface SensorSample {
  t: string; // ISO timestamp
  label: string; // short axis label (HH:mm:ss)
  vibration: number; // mm/s RMS
  temperature: number; // °C
  current: number; // A
  rpm: number;
  health: number; // 0..100
}

/**
 * A monitored machine. All fields except `status` match backend/app.py's
 * _MACHINE_REGISTRY entries (GET /machines) exactly; the backend has no
 * precomputed status field, so `status` is derived once client-side via
 * statusFromScore(health_score) at the data-fetching layer (useMachines,
 * mockData) and attached here for convenience -- every component below reads
 * it as a plain field rather than recomputing it repeatedly.
 */
export interface Machine {
  id: string;
  name: string;
  source: SourceDataset | string | null;
  location: string;
  status: HealthStatus;
  health_score: number;
  predicted_fault: string;
  prediction_confidence: number;
  anomaly_score: number;
  // Only populated once a prediction request supplied these canonical
  // feature keys (utils/schema.py); null until then, not fabricated.
  temperature: number | null;
  current: number | null;
  rpm: number | null;
  vibration: number | null;
  last_updated: string;
}

/** Matches GET /alerts response shape exactly. */
export interface AlertItem {
  id: string;
  machine_id: string;
  machine_name: string;
  severity: HealthStatus;
  message: string;
  timestamp: string;
}

/** Retrieved knowledge-base chunk — matches genai/retrieval.py::KnowledgeChunk.to_dict(). */
export interface KnowledgeChunk {
  chunk_id: string;
  title: string;
  category: string;
  fault_tag: string;
  source_file: string;
  text: string;
  relevance_score: number;
}

/**
 * RAG + LLM generated maintenance report — matches
 * backend/schema/maintenance_report.json field-for-field (both the Gemini
 * path and the grounded offline fallback in genai/llm_generator.py return
 * exactly this shape).
 */
export interface MaintenanceReport {
  machine_id: string;
  timestamp: string;
  severity: HealthStatus;
  title: string;
  summary: string;
  evidence: string[];
  likely_cause: string;
  recommended_action: string[];
  urgency: string;
  confidence: number;
  notes: string;
}

/**
 * Unified payload from POST /api/v1/dashboard/machine-status and
 * POST /api/v1/sensor-stream — matches backend/schemas/dashboard_payload.json.
 */
export interface DashboardMachineStatus {
  machine_id: string;
  timestamp: string;
  status: HealthStatus;
  prediction: Prediction;
  retrieval: {
    query: string;
    chunks: KnowledgeChunk[];
  };
  report: MaintenanceReport;
}

/** Matches GET /dashboard/summary exactly. */
export interface FleetSummary {
  total: number;
  healthy: number;
  warning: number;
  critical: number;
  average_health: number;
}

/** Client-side merge of a Prediction + machine name, used by History views. */
export interface HistoryRecord {
  id: string;
  machine_id: string;
  machine_name: string;
  timestamp: string;
  predicted_fault: string;
  prediction_confidence: number;
  health_score: number;
  anomaly_score: number;
  status: HealthStatus;
  recommended_action: string;
}
