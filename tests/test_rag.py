import os
import sys
import unittest

sys.path.insert(0, os.path.abspath("."))

from genai.adapter import PredictionAdapter
from genai.retrieval import KnowledgeBaseLoader, VectorStore, MaintenanceRetriever
from genai.llm_generator import LLMReportGenerator
from utils.schema import validate_report_record, validate_prediction_record


class TestRAGPipeline(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.retriever = MaintenanceRetriever(kb_dir="knowledge_base", index_file=os.path.join("vector_store", "kb_index.pkl"))
        cls.generator = LLMReportGenerator()

    def test_kb_loading_and_chunking(self):
        chunks = self.retriever.vector_store.chunks
        self.assertGreater(len(chunks), 5, "Knowledge base should contain at least 5 document chunks.")
        
        categories = set(c.category for c in chunks)
        self.assertTrue(any("bearing_faults" in cat for cat in categories))
        self.assertTrue(any("motor_faults" in cat for cat in categories))
        self.assertTrue(any("maintenance" in cat for cat in categories))
        self.assertTrue(any("safety" in cat for cat in categories))

    def test_prediction_adapter_normalization(self):
        raw_prediction = {
            "machine_id": "TEST_MOTOR_100",
            "health_score": 25.0,
            "anomaly_score": 0.75,
            "predicted_fault": "Inner Race Fault",
            "prediction_confidence": 0.92,
        }
        normalized = PredictionAdapter.normalize_prediction(raw_prediction)
        
        self.assertEqual(normalized["machine_id"], "TEST_MOTOR_100")
        self.assertEqual(normalized["health_score"], 25.0)
        self.assertEqual(normalized["anomaly_score"], 0.75)
        self.assertEqual(normalized["predicted_fault"], "Inner Race Fault")
        self.assertIn("timestamp", normalized)
        self.assertIn("window_id", normalized)
        
        query = PredictionAdapter.build_search_query(normalized)
        self.assertIn("Inner Race Fault", query)

    def test_vector_store_retrieval(self):
        query = "inner race defect BPFI vibration spalling"
        results = self.retriever.retrieve(query, top_k=3)
        self.assertEqual(len(results), 3)
        
        top_result = results[0]
        self.assertIn("relevance_score", top_result)
        self.assertGreater(top_result["relevance_score"], 0.0)
        self.assertIn("inner_race", top_result["fault_tag"].lower())

    def test_llm_report_generation_and_schema_validation(self):
        sample_pred = {
            "machine_id": "MOTOR_001",
            "window_id": "win_001",
            "timestamp": "2026-07-24T13:00:00Z",
            "health_score": 15.0,
            "anomaly_score": 0.85,
            "fault_probability": 0.85,
            "predicted_fault": "Inner Race Fault",
            "prediction_confidence": 0.89,
            "remaining_useful_life_hours": 8.5,
            "recommended_action": "Immediate inspection recommended."
        }
        
        normalized = PredictionAdapter.normalize_prediction(sample_pred)
        chunks = self.retriever.retrieve_for_prediction(normalized, top_k=3)
        report = self.generator.generate_report(normalized, chunks)
        
        self.assertEqual(report["machine_id"], "MOTOR_001")
        self.assertEqual(report["severity"], "critical")
        self.assertIsInstance(report["evidence"], list)
        self.assertIsInstance(report["recommended_action"], list)
        
        val_err = validate_report_record(report)
        self.assertIsNone(val_err, f"Report failed schema validation: {val_err}")


if __name__ == "__main__":
    unittest.main()
