import os
import sys
import json
import numpy as np
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from fastapi import FastAPI, HTTPException, Query, Body, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse

sys.path.insert(0, os.path.abspath("."))

from utils.schema import validate_prediction_record, validate_report_record
from genai.adapter import PredictionAdapter
from genai.retrieval import MaintenanceRetriever
from genai.llm_generator import LLMReportGenerator
from inference.predict import LTCInferenceEngine
from inference.predict_general import GeneralLTCInferenceEngine
from features.bearing_features import BEARING_FEATURE_KEYS, feature_vector_to_array

app = FastAPI(
    title="Spandana RAG + LLM Maintenance Intelligence API",
    description="Backend API for Member 3 RAG maintenance intelligence and dashboard integration.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Services initialization
retriever = MaintenanceRetriever(kb_dir="knowledge_base", index_file=os.path.join("vector_store", "kb_index.pkl"))
generator = LLMReportGenerator(prompt_path=os.path.join("prompts", "report_prompt.txt"))

# Sources that carry the bearing-specific 17-dim feature schema and 5-class
# fault-location label (features/bearing_features.py, preprocessing/bearing_common.py).
_BEARING_SOURCES = {"nasa_ims", "cwru", "paderborn"}

# Both trained LTC models are loaded ONCE at process startup and kept alive
# for the life of the backend -- each call below reuses the same instance
# rather than re-constructing (and re-loading a checkpoint) per request. Both
# engines are genuinely stateful: they hold one hidden state (`hx`) per
# machine_id internally (inference/predict.py, inference/predict_general.py),
# so repeated calls for the same machine_id continue that machine's
# continuous-time state rather than starting fresh each time.
bearing_engine = LTCInferenceEngine(
    checkpoint_path=os.path.join("data", "checkpoints", "lnn", "best_ltc.pt"),
    scaler_path=os.path.join("data", "unified", "feature_scaler.json"),
    vae_checkpoint_path=os.path.join("data", "checkpoints", "vae", "healthy_vae.pt"),
    vae_scaler_path=os.path.join("data", "unified_schema", "feature_scaler.json"),
)
general_engine = GeneralLTCInferenceEngine(
    checkpoint_path=os.path.join("data", "checkpoints", "ltc_general_augmented", "best_ltc_general.pt"),
    scaler_path=os.path.join("data", "unified_schema", "feature_scaler.json"),
    vae_checkpoint_path=os.path.join("data", "checkpoints", "vae", "healthy_vae.pt"),
    vae_scaler_path=os.path.join("data", "unified_schema", "feature_scaler.json"),
)

# In-memory stores. Demo-appropriate (matches the existing _MACHINE_REPORTS_STORE
# pattern already in this file) -- swap for a real DB behind the same functions
# below if/when persistence across restarts is needed.
_MACHINE_REPORTS_STORE: Dict[str, List[Dict[str, Any]]] = {}
_PREDICTIONS_STORE: Dict[str, List[Dict[str, Any]]] = {}
_MACHINE_REGISTRY: Dict[str, Dict[str, Any]] = {}
_ALERT_HEALTH_THRESHOLD = 60.0


def _run_inference(machine_id: str, source: Optional[str], features: Optional[Dict[str, float]],
                    signal: Optional[List[float]], fs: Optional[float],
                    window_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Routes a single prediction request to the correct trained model rather
    than fabricating one. Bearing sources (nasa_ims/cwru/paderborn) with a
    raw signal go through the bearing specialist's own feature extraction;
    a bearing source's already-extracted 17-key feature vector also goes to
    the specialist. Everything else (Track 1 sources, or no source given)
    goes to the general 6-dataset severity model -- see
    inference/predict_general.py for why that split exists.
    """
    is_bearing = source in _BEARING_SOURCES

    if is_bearing and signal is not None:
        if fs is None:
            raise HTTPException(status_code=400, detail="'fs' (sample rate) is required when 'signal' is provided for a bearing source.")
        return bearing_engine.predict_from_signal(machine_id, np.array(signal, dtype=np.float32), fs, window_id=window_id)

    if is_bearing and features is not None:
        missing = [k for k in BEARING_FEATURE_KEYS if k not in features]
        if missing:
            # Fail fast rather than silently falling through to the general
            # model below -- verified this actually happens without this
            # check: an incomplete bearing feature set would otherwise be
            # served by a different model with no indication to the caller,
            # which is exactly the kind of silent degradation this project
            # has deliberately avoided everywhere else.
            raise HTTPException(
                status_code=400,
                detail=f"Bearing source '{source}' requires all {len(BEARING_FEATURE_KEYS)} bearing feature keys; missing: {missing}",
            )
        vec = feature_vector_to_array(features)
        return bearing_engine.predict_from_feature_vector(machine_id, vec, window_id=window_id)

    if features is None:
        raise HTTPException(status_code=400, detail="Request must include either 'signal' (+ 'fs') or 'features'.")

    return general_engine.predict_from_features(machine_id, features, window_id=window_id)


def _update_registry(prediction: Dict[str, Any], source: Optional[str] = None,
                      name: Optional[str] = None, location: Optional[str] = None,
                      features: Optional[Dict[str, float]] = None) -> None:
    """
    Upserts the lightweight machine registry backing /machines from a real
    prediction. `features` (when the caller has it) contributes raw-sensor
    display fields -- these are genuine canonical feature keys
    (utils/schema.py::CANONICAL_FEATURE_KEYS), not fabricated: temperature,
    current and rpm are named keys in that schema, and rms doubles as a
    vibration-amplitude proxy for display.
    """
    m_id = prediction["machine_id"]
    existing = _MACHINE_REGISTRY.get(m_id, {})
    features = features or {}
    _MACHINE_REGISTRY[m_id] = {
        "id": m_id,
        "name": name or existing.get("name") or m_id,
        "source": source or existing.get("source"),
        "location": location or existing.get("location") or "Unassigned",
        "health_score": prediction["health_score"],
        "predicted_fault": prediction["predicted_fault"],
        "prediction_confidence": prediction["prediction_confidence"],
        "anomaly_score": prediction["anomaly_score"],
        "temperature": features.get("temperature", existing.get("temperature")),
        "current": features.get("current", existing.get("current")),
        "rpm": features.get("rpm", existing.get("rpm")),
        "vibration": features.get("rms", existing.get("vibration")),
        "last_updated": prediction["timestamp"],
    }

    history = _PREDICTIONS_STORE.setdefault(m_id, [])
    history.append(prediction)
    if len(history) > 200:
        history.pop(0)


@app.get("/health")
@app.get("/api/v1/health")
def health_check():
    """Health check endpoint exposing service & knowledge base status."""
    kb_loaded = retriever.vector_store.vectorizer is not None
    chunks_count = len(retriever.vector_store.chunks)
    gemini_key_present = os.getenv("GEMINI_API_KEY") is not None

    return {
        "status": "healthy",
        "service": "Spandana RAG+LLM Intelligence Layer",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "knowledge_base": {
            "indexed": kb_loaded,
            "total_chunks": chunks_count
        },
        "llm_engine": {
            "provider": "Google Gemini API" if gemini_key_present else "Grounded Rule Engine (Offline Fallback)",
            "gemini_api_key_configured": gemini_key_present
        }
    }


@app.post("/predict")
def predict_endpoint(payload: Dict[str, Any] = Body(...)):
    """
    Runs the REAL trained LTC model (loaded once at startup, see
    bearing_engine/general_engine above) on a sensor window and returns a
    model_prediction.json-shaped result. Accepts either:
      {"machine_id", "source"?, "signal": [...], "fs": number, "window_id"?}
    or
      {"machine_id", "source"?, "features": {...}, "window_id"?}
    `source` (one of backend/schemas/sensor_input.json's enum) decides which
    trained model serves the request -- see _run_inference().
    """
    machine_id = payload.get("machine_id")
    if not machine_id:
        raise HTTPException(status_code=400, detail="'machine_id' is required.")

    prediction = _run_inference(
        machine_id=machine_id,
        source=payload.get("source"),
        features=payload.get("features"),
        signal=payload.get("signal"),
        fs=payload.get("fs"),
        window_id=payload.get("window_id"),
    )

    error = validate_prediction_record(prediction)
    if error:
        raise HTTPException(status_code=500, detail=f"Model produced a non-conformant prediction: {error}")

    _update_registry(prediction, source=payload.get("source"), name=payload.get("name"),
                      location=payload.get("location"), features=payload.get("features"))
    return prediction


@app.post("/report")
@app.post("/api/v1/report")
def generate_report_endpoint(prediction: Dict[str, Any] = Body(...)):
    """
    Consumes a prediction JSON (from /predict, or any upstream producer of the
    established schema), retrieves relevant maintenance context, and returns a
    structured maintenance report.
    """
    normalized_pred = PredictionAdapter.normalize_prediction(prediction)
    chunks = retriever.retrieve_for_prediction(normalized_pred, top_k=3)
    report = generator.generate_report(normalized_pred, chunks)

    # Store report history
    m_id = normalized_pred["machine_id"]
    history = _MACHINE_REPORTS_STORE.setdefault(m_id, [])
    history.append(report)
    if len(history) > 50:
        history.pop(0)

    return report


@app.post("/rag/search")
@app.post("/api/v1/rag/search")
def rag_search_endpoint(payload: Dict[str, Any] = Body(...)):
    """
    Debug & search endpoint for querying the knowledge base vector store.
    """
    query = payload.get("query", "")
    top_k = int(payload.get("top_k", 3))

    if not query:
        raise HTTPException(status_code=400, detail="Search payload must include a non-empty 'query' field.")

    chunks = retriever.retrieve(query, top_k=top_k)
    return {
        "query": query,
        "count": len(chunks),
        "results": chunks
    }


@app.post("/api/v1/dashboard/machine-status")
def dashboard_machine_status_endpoint(prediction: Dict[str, Any] = Body(...)):
    """
    Generates unified machine-status payload for the React / Web Dashboard combining
    model prediction, RAG retrieval context, and structured LLM report.
    """
    normalized_pred = PredictionAdapter.normalize_prediction(prediction)
    query = PredictionAdapter.build_search_query(normalized_pred)
    chunks = retriever.retrieve_for_prediction(normalized_pred, top_k=3)
    report = generator.generate_report(normalized_pred, chunks)

    health = normalized_pred["health_score"]
    anomaly = normalized_pred["anomaly_score"]

    if health >= 85.0 and anomaly < 0.35:
        overall_status = "healthy"
    elif health >= 50.0:
        overall_status = "warning"
    else:
        overall_status = "critical"

    _update_registry(normalized_pred, source=prediction.get("source"), features=prediction.get("features"))

    return {
        "machine_id": normalized_pred["machine_id"],
        "timestamp": normalized_pred["timestamp"],
        "status": overall_status,
        "prediction": normalized_pred,
        "retrieval": {
            "query": query,
            "chunks": chunks
        },
        "report": report
    }


@app.get("/reports/{machine_id}")
@app.get("/api/v1/reports/{machine_id}")
def get_machine_reports_endpoint(machine_id: str):
    """Retrieves generated report history for a given machine_id."""
    reports = _MACHINE_REPORTS_STORE.get(machine_id, [])
    return {
        "machine_id": machine_id,
        "count": len(reports),
        "reports": reports
    }


@app.post("/api/v1/sensor-stream")
def sensor_stream_endpoint(window_record: Dict[str, Any] = Body(...)):
    """
    Endpoint for Member 1 real-time stream replay client (`realtime/replay.py`).
    Runs the incoming sensor window through the REAL trained LTC model (via
    _run_inference -- previously this endpoint used hardcoded RMS/kurtosis
    threshold rules instead of calling the model; that was a placeholder from
    before the trained checkpoints existed and has been replaced), then
    generates the RAG report and updates dashboard state from that real
    prediction.
    """
    m_id = window_record.get("machine_id", "STREAM_MOTOR_01")
    source = window_record.get("source")
    feats = window_record.get("features", {})

    prediction = _run_inference(
        machine_id=m_id,
        source=source,
        features=feats,
        signal=None,
        fs=None,
        window_id=window_record.get("window_id"),
    )
    prediction["source"] = source
    prediction["features"] = feats

    return dashboard_machine_status_endpoint(prediction)


@app.post("/replay")
def replay_endpoint(payload: Dict[str, Any] = Body(...)):
    """
    Replays a list of feature-vector windows for one machine through
    _run_inference in order, carrying that machine's hidden state across the
    whole batch (both engines persist `hx` per machine_id) -- the batch
    equivalent of inference/inference_pipeline.py::replay_signal, exposed over
    the API for the frontend's replay-speed control.
    Body: {"machine_id", "source"?, "windows": [{"features": {...}}, ...]}
    """
    machine_id = payload.get("machine_id")
    windows = payload.get("windows")
    if not machine_id or not windows:
        raise HTTPException(status_code=400, detail="'machine_id' and non-empty 'windows' are required.")

    source = payload.get("source")
    predictions = []
    for w in windows:
        pred = _run_inference(
            machine_id=machine_id, source=source, features=w.get("features"),
            signal=w.get("signal"), fs=w.get("fs"), window_id=w.get("window_id"),
        )
        _update_registry(pred, source=source, features=w.get("features"))
        predictions.append(pred)

    return {"machine_id": machine_id, "count": len(predictions), "predictions": predictions}


@app.get("/machines")
def list_machines_endpoint():
    """All machines seen so far (populated by real predictions from /predict, /replay, or /api/v1/sensor-stream)."""
    return list(_MACHINE_REGISTRY.values())


@app.get("/machines/{machine_id}")
def get_machine_endpoint(machine_id: str):
    machine = _MACHINE_REGISTRY.get(machine_id)
    if machine is None:
        raise HTTPException(status_code=404, detail=f"No machine registered with id '{machine_id}'.")
    return machine


@app.get("/predictions/latest")
def latest_predictions_endpoint():
    """Most recent prediction per known machine."""
    return [history[-1] for history in _PREDICTIONS_STORE.values() if history]


@app.get("/predictions/history")
def predictions_history_endpoint(machine_id: Optional[str] = Query(default=None)):
    """Full prediction history, optionally filtered to one machine."""
    if machine_id:
        return _PREDICTIONS_STORE.get(machine_id, [])
    return [p for history in _PREDICTIONS_STORE.values() for p in history]


@app.get("/alerts")
def list_alerts_endpoint():
    """
    Alerts derived from real stored predictions -- any machine whose latest
    health_score is below _ALERT_HEALTH_THRESHOLD, not a separately
    fabricated notion of "alert".
    """
    alerts = []
    for m_id, history in _PREDICTIONS_STORE.items():
        if not history:
            continue
        latest = history[-1]
        if latest["health_score"] < _ALERT_HEALTH_THRESHOLD:
            machine = _MACHINE_REGISTRY.get(m_id, {})
            alerts.append({
                "id": f"{m_id}_{latest['window_id']}",
                "machine_id": m_id,
                "machine_name": machine.get("name", m_id),
                "severity": "critical" if latest["health_score"] < 30 else "warning",
                "message": latest["recommended_action"],
                "timestamp": latest["timestamp"],
            })
    alerts.sort(key=lambda a: a["timestamp"], reverse=True)
    return alerts


@app.post("/alerts")
def acknowledge_alert_endpoint(payload: Dict[str, Any] = Body(...)):
    """Placeholder acknowledgement hook for the frontend's alert panel (no separate ack store yet)."""
    return {"acknowledged": True, "alert_id": payload.get("alert_id")}


@app.get("/dashboard/summary")
def dashboard_summary_endpoint():
    """Fleet-wide counts for the dashboard's top summary cards, derived from _MACHINE_REGISTRY."""
    machines = list(_MACHINE_REGISTRY.values())
    total = len(machines)
    healthy = sum(1 for m in machines if m["health_score"] >= 85.0)
    critical = sum(1 for m in machines if m["health_score"] < _ALERT_HEALTH_THRESHOLD - 30)
    warning = total - healthy - critical
    average_health = round(sum(m["health_score"] for m in machines) / total, 2) if total else 0.0
    return {
        "total": total,
        "healthy": healthy,
        "warning": warning,
        "critical": critical,
        "average_health": average_health,
    }


# Serve the built frontend (frontend/dist, produced by `npm run build`) if
# present. Deliberately NOT frontend/ itself -- that's the React source tree
# (package.json, src/*.tsx, ...), not deployable static assets. In local
# development the Vite dev server (npm run dev, port 5173) is used instead,
# proxying API calls to this backend -- see frontend/vite.config.ts.
#
# Registered LAST (after every API route above) and matches any path, but
# Starlette tries routes in registration order, so none of the API routes
# above are shadowed -- this only ever runs for requests nothing else matched.
#
# A plain StaticFiles(html=True) mount here would 404 on a direct link or
# hard refresh to any client-side route (e.g. /predictions, /machines/X --
# React Router paths with no matching file in dist/), since it only serves
# index.html for the literal root path. This serves a real built file when
# one exists at the requested path (JS/CSS bundles, favicon, ...) and falls
# back to index.html otherwise, so React Router can take over client-side --
# confirmed broken without this (GET /predictions -> 404) before this fix.
frontend_dist_dir = os.path.abspath(os.path.join("frontend", "dist"))
if os.path.exists(frontend_dist_dir):
    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        candidate = os.path.abspath(os.path.join(frontend_dist_dir, full_path))
        is_within_dist = candidate.startswith(frontend_dist_dir + os.sep)
        if full_path and is_within_dist and os.path.isfile(candidate):
            return FileResponse(candidate)
        return FileResponse(os.path.join(frontend_dist_dir, "index.html"))
