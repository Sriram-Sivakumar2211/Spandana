import os
import sys
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from fastapi import FastAPI, HTTPException, Query, Body, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse

sys.path.insert(0, os.path.abspath("."))

from utils.schema import validate_prediction_record, validate_report_record
from genai.adapter import PredictionAdapter
from genai.retrieval import MaintenanceRetriever
from genai.llm_generator import LLMReportGenerator

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

# In-memory store for generated machine reports
_MACHINE_REPORTS_STORE: Dict[str, List[Dict[str, Any]]] = {}


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


@app.post("/report")
@app.post("/api/v1/report")
def generate_report_endpoint(prediction: Dict[str, Any] = Body(...)):
    """
    Consumes Member 2 prediction JSON, retrieves relevant maintenance context,
    and returns a structured maintenance report.
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
    Processes incoming sensor window, generates prediction & RAG report, and updates state.
    """
    m_id = window_record.get("machine_id", "STREAM_MOTOR_01")
    timestamp = window_record.get("timestamp", datetime.now(timezone.utc).isoformat())
    feats = window_record.get("features", {})
    ground_truth = window_record.get("label", "healthy")

    # Simulate / evaluate inference parameters from features
    rms = float(feats.get("rms", 0.5))
    temp = float(feats.get("temperature", 45.0))
    kurtosis = float(feats.get("kurtosis", 3.0))

    if ground_truth == "faulty" or rms > 2.5 or kurtosis > 4.5:
        predicted_fault = "Inner Race Fault" if rms > 3.0 else "Outer Race Fault"
        fault_prob = 0.88
        health_score = 12.5
        anomaly_score = 0.76
        confidence = 0.89
    elif ground_truth == "warning" or rms > 1.2 or temp > 75.0:
        predicted_fault = "Bearing Wear Warning"
        fault_prob = 0.35
        health_score = 65.0
        anomaly_score = 0.38
        confidence = 0.72
    else:
        predicted_fault = "Healthy"
        fault_prob = 0.02
        health_score = 98.0
        anomaly_score = 0.08
        confidence = 0.96

    prediction = {
        "machine_id": m_id,
        "window_id": window_record.get("window_id", f"{m_id}_{timestamp}"),
        "timestamp": timestamp,
        "health_score": health_score,
        "anomaly_score": anomaly_score,
        "fault_probability": fault_prob,
        "predicted_fault": predicted_fault,
        "prediction_confidence": confidence,
        "recommended_action": f"Inspect machine {m_id} based on stream readings."
    }

    # Generate dashboard payload
    return dashboard_machine_status_endpoint(prediction)


# Serve frontend static dashboard files if present
frontend_dir = os.path.abspath("frontend")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="static")
