import os
import sys
import unittest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath("."))

from backend.app import app


class TestBackendAPI(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_health_endpoint(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertTrue(data["knowledge_base"]["indexed"])
        self.assertGreater(data["knowledge_base"]["total_chunks"], 0)

    def test_report_generation_endpoint(self):
        sample_pred = {
            "machine_id": "API_TEST_MOTOR",
            "window_id": "win_123",
            "timestamp": "2026-07-24T13:00:00Z",
            "health_score": 65.0,
            "anomaly_score": 0.45,
            "fault_probability": 0.35,
            "predicted_fault": "Outer Race Fault",
            "prediction_confidence": 0.82,
            "recommended_action": "Inspect housing alignment."
        }
        response = self.client.post("/report", json=sample_pred)
        self.assertEqual(response.status_code, 200)
        report = response.json()
        self.assertEqual(report["machine_id"], "API_TEST_MOTOR")
        self.assertEqual(report["severity"], "warning")
        self.assertIn("Outer Race Fault", report["title"])

    def test_rag_search_endpoint(self):
        payload = {"query": "rotor imbalance dynamic balancing", "top_k": 2}
        response = self.client.post("/rag/search", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 2)
        self.assertGreater(len(data["results"]), 0)

    def test_dashboard_machine_status_endpoint(self):
        sample_pred = {
            "machine_id": "DASH_MOTOR_01",
            "health_score": 95.0,
            "anomaly_score": 0.05,
            "predicted_fault": "Healthy",
            "prediction_confidence": 0.98,
            "recommended_action": "No immediate action required."
        }
        response = self.client.post("/api/v1/dashboard/machine-status", json=sample_pred)
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["machine_id"], "DASH_MOTOR_01")
        self.assertEqual(payload["status"], "healthy")
        self.assertIn("prediction", payload)
        self.assertIn("retrieval", payload)
        self.assertIn("report", payload)

    def test_get_machine_reports_history_endpoint(self):
        sample_pred = {
            "machine_id": "HIST_TEST_MOTOR",
            "health_score": 90.0,
            "predicted_fault": "Healthy",
            "recommended_action": "Routine inspection."
        }
        self.client.post("/report", json=sample_pred)

        response = self.client.get("/reports/HIST_TEST_MOTOR")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["machine_id"], "HIST_TEST_MOTOR")
        self.assertGreaterEqual(data["count"], 1)



if __name__ == "__main__":
    unittest.main()
