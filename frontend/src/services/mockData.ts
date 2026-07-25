import type {
  AlertItem,
  HistoryRecord,
  Machine,
  MaintenanceReport,
  Prediction,
  SensorSample,
} from "@/types";
import { statusFromScore } from "@/utils/status";
import { formatFault } from "@/utils/format";

/*
  Realistic fallback data used whenever the backend at :8000 is unreachable.
  Machines, sources and fault classes are the REAL ones from the Spandana
  datasets. MaintenanceReport shape here matches the REAL backend
  (backend/schema/maintenance_report.json / genai/llm_generator.py output)
  field-for-field, so switching between live and demo data is seamless.
*/

export const MACHINES: Machine[] = [
  {
    id: "MOTOR_001",
    name: "Compressor Main Drive",
    source: "metropt3",
    location: "Line A · Compressor Hall",
    status: "healthy",
    health_score: 96.4,
    temperature: 64.2,
    current: 4.3,
    rpm: 1480,
    vibration: 0.42,
    predicted_fault: "healthy",
    prediction_confidence: 0.96,
    anomaly_score: 0.05,
    last_updated: new Date(Date.now() - 25_000).toISOString(),
  },
  {
    id: "MOTOR_042",
    name: "Paderborn Bearing Rig",
    source: "paderborn",
    location: "Test Cell 2 · Bearing Bench",
    status: "warning",
    health_score: 58.1,
    temperature: 71.8,
    current: 5.1,
    rpm: 1500,
    vibration: 1.86,
    predicted_fault: "outer_race",
    prediction_confidence: 0.74,
    anomaly_score: 0.42,
    last_updated: new Date(Date.now() - 12_000).toISOString(),
  },
  {
    id: "CWRU_TEST_MOTOR",
    name: "CWRU Inner-Race Rig",
    source: "cwru",
    location: "Test Cell 1 · Drive-End",
    status: "critical",
    health_score: 21.7,
    temperature: 83.5,
    current: 6.4,
    rpm: 1772,
    vibration: 3.41,
    predicted_fault: "inner_race",
    prediction_confidence: 0.91,
    anomaly_score: 0.78,
    last_updated: new Date(Date.now() - 6_000).toISOString(),
  },
  {
    id: "NASA_IMS_B3",
    name: "NASA IMS Bearing 3",
    source: "nasa_ims",
    location: "Endurance Rig · Shaft 1",
    status: "healthy",
    health_score: 88.9,
    temperature: 59.7,
    current: 3.9,
    rpm: 2000,
    vibration: 0.63,
    predicted_fault: "healthy",
    prediction_confidence: 0.93,
    anomaly_score: 0.09,
    last_updated: new Date(Date.now() - 40_000).toISOString(),
  },
  {
    id: "THERMAL_MOTOR_03",
    name: "Thermal Imaging Motor",
    source: "thermal_motor",
    location: "Line B · IR Station",
    status: "warning",
    health_score: 63.4,
    temperature: 78.2,
    current: 4.8,
    rpm: 1460,
    vibration: 1.12,
    predicted_fault: "faulty",
    prediction_confidence: 0.68,
    anomaly_score: 0.39,
    last_updated: new Date(Date.now() - 18_000).toISOString(),
  },
  {
    id: "SQ_CAGE_07",
    name: "Squirrel-Cage Motor 07",
    source: "squirrel_cage",
    location: "Line B · Drive 7",
    status: "healthy",
    health_score: 91.2,
    temperature: 61.0,
    current: 4.1,
    rpm: 1470,
    vibration: 0.55,
    predicted_fault: "healthy",
    prediction_confidence: 0.95,
    anomaly_score: 0.06,
    last_updated: new Date(Date.now() - 33_000).toISOString(),
  },
];

const ACTIONS: Record<string, string> = {
  healthy: "Continue normal operation; no immediate action required.",
  faulty: "Schedule inspection soon and monitor trend closely.",
  outer_race:
    "Schedule inspection during the next planned maintenance window. Outer race defect signature detected — inspect bearing outer raceway and housing alignment.",
  inner_race:
    "Immediate inspection recommended — elevated risk of failure. Inner race defect signature detected — inspect bearing inner raceway and lubrication.",
  ball: "Schedule inspection soon and monitor trend closely. Ball/roller defect signature detected — inspect rolling elements for pitting or spalling.",
  combined:
    "Immediate inspection recommended — bearing replacement likely required.",
};

/**
 * Demo trigger payloads for POST /api/v1/sensor-stream, mirrored in the
 * Predictions page's "Simulate" controls. `healthy` and `elevated` are
 * representative Track-1-style (MetroPT-3) sensor readings routed to the
 * general model. `recorded_bearing_fault` is not invented: these are the
 * ACTUAL 17-dim features extracted (features/bearing_features.py) from a
 * real recorded CWRU inner-race fault signal, so the resulting prediction is
 * a genuine bearing-specialist inference, not a fabricated demo number.
 */
export const SIMULATE_SCENARIOS = [
  {
    key: "healthy",
    label: "Healthy Window",
    description: "Real healthy squirrel-cage motor feature vector (verified against the live model).",
    source: "squirrel_cage",
    // NOT invented: pulled directly from data/unified_schema/squirrel_cage_standardized.jsonl,
    // a real training record labeled "healthy". MetroPT-3 was deliberately
    // NOT used here -- its 4,995 standardized records are 100% labeled
    // "faulty" (disclosed in reports/cross_modality_report.md), so no
    // MetroPT-3-sourced input can honestly demonstrate a "healthy" result;
    // squirrel-cage's 321 records are 100% "healthy", the correct source for
    // this scenario. Verified live: general model returns "healthy".
    features: { rms: 0.2465, kurtosis: 3.0, skewness: 0.0, crest_factor: 4.5725, dominant_frequency: 0.0, temperature: 0.2187, current: 4.0, rpm: 1480, hotspot_ratio: 0.15, hotspot_intensity: 0.7317 },
  },
  {
    key: "elevated",
    label: "Fault Signature (MetroPT-3)",
    description: "Real MetroPT-3 compressor feature vector, labeled faulty in the source dataset.",
    source: "metropt3",
    // Also not invented: a real record from data/unified_schema/metropt3_standardized.jsonl
    // (ground_truth: "faulty"). Labeled "Fault Signature" rather than
    // "Elevated Wear"/"Warning" because MetroPT-3 has zero "warning"-labeled
    // examples -- like every source in this project, it's strictly
    // healthy-or-faulty, so claiming a "warning" result here would be
    // fabricated, not measured.
    features: { rms: 0.04, kurtosis: 7.0, skewness: -0.0, crest_factor: 1.0623, dominant_frequency: 0.3, temperature: 53.05, current: 0.04, rpm: 1480, tp2_pressure: -0.013, tp3_pressure: 9.0586 },
  },
  {
    key: "recorded_bearing_fault",
    label: "Recorded Bearing Fault Sample",
    description: "Real 17-dim features extracted from a recorded CWRU inner-race fault signal.",
    source: "cwru",
    features: {
      mean: 0.021, std: 0.2889, rms: 0.2896, variance: 0.0834, peak: 1.5481,
      peak_to_peak: 3.0243, crest_factor: 5.3455, skewness: -0.1281, kurtosis: 4.2797,
      dominant_frequency: 2578.12, spectral_energy: 172.6783, spectral_entropy: 0.627395,
      wavelet_energy_a4: 0.143426, wavelet_energy_d1: 0.001227, wavelet_energy_d2: 0.038302,
      wavelet_energy_d3: 0.416184, wavelet_energy_d4: 0.400861,
    },
  },
] as const;

export function predictionFor(machine: Machine): Prediction {
  const faultProb = 1 - machine.health_score / 100;
  return {
    machine_id: machine.id,
    window_id: `${machine.id}_${Date.now()}`,
    timestamp: new Date().toISOString(),
    health_score: Number(machine.health_score.toFixed(2)),
    anomaly_score: machine.anomaly_score,
    fault_probability: Number(faultProb.toFixed(4)),
    predicted_fault: machine.predicted_fault,
    prediction_confidence: machine.prediction_confidence,
    remaining_useful_life_hours:
      machine.status === "healthy"
        ? null
        : Number((machine.health_score * 4.3).toFixed(1)),
    recommended_action:
      ACTIONS[machine.predicted_fault] ?? ACTIONS.healthy,
  };
}

export function buildHistory(): HistoryRecord[] {
  const rows: HistoryRecord[] = [];
  const faults = ["healthy", "healthy", "outer_race", "inner_race", "ball", "combined"];
  for (let i = 0; i < 48; i++) {
    const m = MACHINES[i % MACHINES.length];
    const drift = Math.sin(i / 3) * 18;
    const score = Math.max(6, Math.min(99, m.health_score + drift - i * 0.4));
    const status = statusFromScore(score);
    const fault =
      status === "healthy"
        ? "healthy"
        : faults[(i % (faults.length - 1)) + 1];
    rows.push({
      id: `H-${1000 + i}`,
      machine_id: m.id,
      machine_name: m.name,
      timestamp: new Date(Date.now() - i * 37 * 60_000).toISOString(),
      predicted_fault: fault,
      prediction_confidence: Number((0.68 + Math.random() * 0.3).toFixed(3)),
      health_score: Number(score.toFixed(1)),
      anomaly_score: Number((1 - score / 100).toFixed(3)),
      status,
      recommended_action: ACTIONS[fault] ?? ACTIONS.healthy,
    });
  }
  return rows;
}

export function buildAlerts(): AlertItem[] {
  return MACHINES.filter((m) => m.status !== "healthy").map((m, i) => ({
    id: `A-${i}`,
    machine_id: m.id,
    machine_name: m.name,
    severity: m.status,
    message:
      m.status === "critical"
        ? `${formatFault(m.predicted_fault)} detected — health ${m.health_score.toFixed(0)}%, immediate inspection advised.`
        : `Early ${formatFault(m.predicted_fault)} signature — health ${m.health_score.toFixed(0)}%, monitor closely.`,
    timestamp: new Date(Date.now() - i * 9 * 60_000).toISOString(),
  }));
}

/** Matches the REAL backend/schema/maintenance_report.json shape exactly. */
export function reportFor(machine: Machine): MaintenanceReport {
  const p = predictionFor(machine);
  const faultLabel = formatFault(machine.predicted_fault);

  if (machine.status === "healthy") {
    return {
      machine_id: machine.id,
      timestamp: new Date().toISOString(),
      severity: "healthy",
      title: `${machine.name} — Normal Operational Status`,
      summary: `Machine ${machine.name} is operating within normal parameters with a health score of ${machine.health_score.toFixed(1)}%.`,
      evidence: [
        `LTC model prediction: Healthy with ${(p.prediction_confidence * 100).toFixed(1)}% confidence.`,
        `Machine health score evaluated at ${machine.health_score.toFixed(1)} / 100.`,
        `Unsupervised VAE anomaly score: ${p.anomaly_score.toFixed(4)}.`,
      ],
      likely_cause: "Model output indicates no fault signature present.",
      recommended_action: ["Continue normal operation.", "Maintain routine lubrication schedule."],
      urgency: "Routine (next maintenance cycle)",
      confidence: p.prediction_confidence,
      notes: "Enforce Lockout/Tagout (LOTO) protocols prior to any physical inspection.",
    };
  }

  const severity = machine.status;
  return {
    machine_id: machine.id,
    timestamp: new Date().toISOString(),
    severity,
    title:
      severity === "critical"
        ? `${machine.name} — CRITICAL ALERT: ${faultLabel}`
        : `${machine.name} — Maintenance Warning: ${faultLabel}`,
    summary: `${severity === "critical" ? "Elevated fault probability" : "Early anomaly indicators"} detected on ${machine.name}. Predicted condition: '${faultLabel}' (health: ${machine.health_score.toFixed(1)}%, anomaly score: ${p.anomaly_score.toFixed(2)}).`,
    evidence: [
      `LTC model prediction: ${faultLabel} with ${(p.prediction_confidence * 100).toFixed(1)}% confidence.`,
      `Machine health score evaluated at ${machine.health_score.toFixed(1)} / 100.`,
      `Unsupervised VAE anomaly score: ${p.anomaly_score.toFixed(4)}.`,
      ...(p.remaining_useful_life_hours !== null
        ? [`Linear trend extrapolation RUL: ${p.remaining_useful_life_hours.toFixed(1)} hours remaining.`]
        : []),
    ],
    likely_cause: `Model output indicates signature corresponding to ${faultLabel}.`,
    recommended_action: [
      ACTIONS[machine.predicted_fault] ?? ACTIONS.healthy,
      "Enforce Lockout/Tagout (LOTO) before any physical inspection.",
      "Re-check prediction after corrective action to confirm recovery.",
    ],
    urgency: severity === "critical" ? "Immediate (within 24h)" : "Scheduled (within 7 days)",
    confidence: p.prediction_confidence,
    notes: "Verify PPE and zero energy state before servicing.",
  };
}

/** Rolling telemetry generator for the live charts (client-side visual only, not a backend contract). */
export function makeSensorSample(prev: SensorSample | null): SensorSample {
  const now = new Date();
  const base = prev ?? {
    vibration: 0.6,
    temperature: 63,
    current: 4.3,
    rpm: 1480,
    health: 92,
  };
  const wobble = (v: number, amp: number, lo: number, hi: number) =>
    Math.min(hi, Math.max(lo, v + (Math.random() - 0.5) * amp));
  return {
    t: now.toISOString(),
    label: now.toLocaleTimeString(undefined, {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    }),
    vibration: Number(wobble(base.vibration, 0.35, 0.2, 3.6).toFixed(2)),
    temperature: Number(wobble(base.temperature, 1.2, 55, 88).toFixed(1)),
    current: Number(wobble(base.current, 0.4, 3.4, 6.6).toFixed(2)),
    rpm: Math.round(wobble(base.rpm, 22, 1440, 2010)),
    health: Number(wobble(base.health, 2.4, 15, 99).toFixed(1)),
  };
}

export function seedSensorSeries(n: number): SensorSample[] {
  const out: SensorSample[] = [];
  let prev: SensorSample | null = null;
  for (let i = 0; i < n; i++) {
    prev = makeSensorSample(prev);
    out.push(prev);
  }
  return out;
}
