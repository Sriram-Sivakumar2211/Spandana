import os
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional


class PredictionAdapter:
    """
    Adapter converting Member 2's LNN prediction JSON into the standardized
    input payload required by the RAG retrieval pipeline and LLM report layer.
    """

    @staticmethod
    def normalize_prediction(pred: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validates and fills default values for missing optional fields in Member 2 prediction.
        """
        machine_id = str(pred.get("machine_id", "UNKNOWN_MACHINE"))
        timestamp = pred.get("timestamp")
        if not timestamp:
            timestamp = datetime.now(timezone.utc).isoformat()

        health_score = float(pred.get("health_score", 100.0))
        health_score = max(0.0, min(100.0, health_score))

        anomaly_score = float(pred.get("anomaly_score", 0.0))
        anomaly_score = max(0.0, min(1.0, anomaly_score))

        fault_probability = float(pred.get("fault_probability", (100.0 - health_score) / 100.0))
        fault_probability = max(0.0, min(1.0, fault_probability))

        predicted_fault = str(pred.get("predicted_fault", "Healthy"))
        prediction_confidence = float(pred.get("prediction_confidence", 1.0))
        prediction_confidence = max(0.0, min(1.0, prediction_confidence))

        rul = pred.get("remaining_useful_life_hours")
        rul_hours = float(rul) if (rul is not None) else None

        recommended_action = str(pred.get("recommended_action", "No action specified."))

        top_features = pred.get("top_features", {})
        if not isinstance(top_features, dict):
            top_features = {}

        return {
            "machine_id": machine_id,
            "window_id": str(pred.get("window_id", f"{machine_id}_{timestamp}")),
            "timestamp": timestamp,
            "health_score": health_score,
            "anomaly_score": anomaly_score,
            "fault_probability": fault_probability,
            "predicted_fault": predicted_fault,
            "prediction_confidence": prediction_confidence,
            "remaining_useful_life_hours": rul_hours,
            "recommended_action": recommended_action,
            "top_features": top_features,
        }

    @staticmethod
    def build_search_query(normalized_pred: Dict[str, Any]) -> str:
        """
        Constructs an effective domain search query for RAG retrieval from model predictions.
        """
        fault = normalized_pred["predicted_fault"]
        health = normalized_pred["health_score"]
        anomaly = normalized_pred["anomaly_score"]
        features = normalized_pred.get("top_features", {})

        query_terms = [fault, "maintenance", "inspection", "safety"]

        if "inner race" in fault.lower():
            query_terms.extend(["inner race defect", "BPFI", "spalling", "bearing wear"])
        elif "outer race" in fault.lower():
            query_terms.extend(["outer race defect", "BPFO", "housing alignment", "spalling"])
        elif "ball" in fault.lower() or "roller" in fault.lower():
            query_terms.extend(["rolling element", "BSF", "cage defect", "ball fault"])
        elif "combined" in fault.lower():
            query_terms.extend(["severe bearing failure", "spalling", "replacement"])
        elif "healthy" in fault.lower():
            query_terms.extend(["normal operation", "routine lubrication", "inspection checklist"])
        elif fault.lower() == "warning":
            # The general 6-dataset severity model (Track 1 sources: MetroPT-3,
            # squirrel-cage, thermal motor) only outputs a coarse severity
            # label, not a specific fault location -- unlike the bearing
            # specialist above. Retrieving broadly across the motor_faults/
            # knowledge-base category is honest here; naming one specific
            # fault (e.g. "misalignment") would fabricate precision the model
            # itself doesn't have.
            query_terms.extend(["early degradation", "condition monitoring", "preventive maintenance", "rising temperature", "vibration increase"])
        elif fault.lower() == "faulty":
            query_terms.extend(["motor fault", "abnormal vibration", "overheating", "electrical anomaly", "rotor imbalance", "misalignment"])

        if health < 50.0 or anomaly > 0.5:
            query_terms.extend(["critical severity", "emergency action", "vibration RMS", "overheating"])

        for feat_name, feat_val in features.items():
            if feat_val:
                query_terms.append(f"{feat_name}")

        return " ".join(query_terms)
