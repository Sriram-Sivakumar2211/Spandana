import os
import sys
import unittest

sys.path.insert(0, os.path.abspath("."))

from utils.schema import (
    validate_input_record,
    validate_prediction_record,
    validate_report_record,
    MODEL_PREDICTION_SCHEMA,
    MAINTENANCE_REPORT_SCHEMA
)


class TestReportSchema(unittest.TestCase):

    def test_valid_prediction_schema(self):
        valid_pred = {
            "machine_id": "MOTOR_001",
            "window_id": "MOTOR_001_2026-07-24T13:00:00+00:00",
            "timestamp": "2026-07-24T13:00:00Z",
            "health_score": 85.5,
            "anomaly_score": 0.12,
            "fault_probability": 0.145,
            "predicted_fault": "Inner Race Fault",
            "prediction_confidence": 0.855,
            "remaining_useful_life_hours": 124.5,
            "recommended_action": "Schedule vibration monitoring within 48 hours."
        }
        err = validate_prediction_record(valid_pred)
        self.assertIsNone(err, f"Prediction schema validation failed: {err}")

    def test_invalid_prediction_schema(self):
        invalid_pred = {
            "machine_id": "MOTOR_001",
            # Missing required timestamp, health_score, etc.
        }
        err = validate_prediction_record(invalid_pred)
        self.assertIsNotNone(err)

    def test_valid_maintenance_report_schema(self):
        valid_report = {
            "machine_id": "MOTOR_001",
            "timestamp": "2026-07-24T13:00:00Z",
            "severity": "critical",
            "title": "MOTOR_001 — CRITICAL ALERT: Inner Race Fault",
            "summary": "Elevated fault probability detected on MOTOR_001.",
            "evidence": [
                "LTC model prediction: Inner Race Fault with 89.0% confidence.",
                "Machine health score evaluated at 15.0 / 100."
            ],
            "likely_cause": "Spalling along inner raceway.",
            "recommended_action": [
                "Schedule immediate maintenance inspection.",
                "Purge old grease and check for metallic particles."
            ],
            "urgency": "Immediate (within 24h)",
            "confidence": 0.89,
            "notes": "Enforce Lockout/Tagout (LOTO) protocols."
        }
        err = validate_report_record(valid_report)
        self.assertIsNone(err, f"Report schema validation failed: {err}")


if __name__ == "__main__":
    unittest.main()
