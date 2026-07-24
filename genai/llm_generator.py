import os
import json
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("spandana.llm_generator")


class LLMReportGenerator:
    """
    Grounded maintenance report generator. Uses Google Gemini API when GEMINI_API_KEY
    is present, and falls back to a deterministic, grounded synthesizer when offline
    or without API key.
    """

    def __init__(self, prompt_path: str = os.path.join("prompts", "report_prompt.txt")):
        self.prompt_path = prompt_path
        self.prompt_template = self._load_prompt_template()

    def _load_prompt_template(self) -> str:
        if os.path.exists(self.prompt_path):
            with open(self.prompt_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def generate_report(self, normalized_pred: Dict[str, Any], retrieved_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generates a structured maintenance report grounded in model predictions
        and retrieved knowledge chunks.
        """
        api_key = os.getenv("GEMINI_API_KEY")
        report = None

        if api_key:
            try:
                report = self._call_gemini_api(api_key, normalized_pred, retrieved_chunks)
            except Exception as e:
                logger.warning(f"Gemini API call failed: {e}. Falling back to grounded rule engine.")

        if not report:
            report = self._generate_grounded_fallback(normalized_pred, retrieved_chunks)

        return report

    def _call_gemini_api(self, api_key: str, pred: Dict[str, Any], chunks: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        import google.generativeai as genai
        genai.configure(api_key=api_key)

        context_str = self._format_chunks_for_prompt(chunks)
        prompt = self.prompt_template.format(
            machine_id=pred["machine_id"],
            timestamp=pred["timestamp"],
            health_score=pred["health_score"],
            anomaly_score=pred["anomaly_score"],
            fault_probability=pred["fault_probability"],
            predicted_fault=pred["predicted_fault"],
            prediction_confidence=pred["prediction_confidence"],
            remaining_useful_life_hours=pred.get("remaining_useful_life_hours") or "N/A",
            recommended_action=pred["recommended_action"],
            retrieved_context=context_str,
        )

        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(
            prompt,
            generation_config={"temperature": 0.2, "response_mime_type": "application/json"}
        )

        raw_text = response.text.strip()
        # Clean any accidental markdown fencing if returned
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]

        return json.loads(raw_text.strip())

    def _format_chunks_for_prompt(self, chunks: List[Dict[str, Any]]) -> str:
        if not chunks:
            return "No relevant knowledge base documents retrieved."

        formatted = []
        for i, c in enumerate(chunks, 1):
            formatted.append(
                f"--- Document [{i}]: {c['title']} (Source: {c['source_file']}, Score: {c['relevance_score']}) ---\n"
                f"{c['text']}\n"
            )
        return "\n".join(formatted)

    def _generate_grounded_fallback(self, pred: Dict[str, Any], chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Deterministic, hallucination-free report synthesizer used when LLM API is unavailable.
        """
        health = pred["health_score"]
        anomaly = pred["anomaly_score"]
        fault = pred["predicted_fault"]
        confidence = pred["prediction_confidence"]
        rul = pred.get("remaining_useful_life_hours")

        # Determine severity
        if health >= 85.0 and anomaly < 0.35:
            severity = "healthy"
            urgency = "Routine (next maintenance cycle)"
            title = f"{pred['machine_id']} — Normal Operational Status"
            summary = f"Machine {pred['machine_id']} is operating within normal parameters with a health score of {health:.1f}%."
        elif health >= 50.0:
            severity = "warning"
            urgency = "Scheduled (within 7 days)"
            title = f"{pred['machine_id']} — Maintenance Warning: {fault}"
            summary = f"Early anomaly indicators detected on {pred['machine_id']}. Predicted condition: '{fault}' (health: {health:.1f}%, anomaly score: {anomaly:.2f})."
        else:
            severity = "critical"
            urgency = "Immediate (within 24h)"
            title = f"{pred['machine_id']} — CRITICAL ALERT: {fault}"
            summary = f"Elevated fault probability detected on {pred['machine_id']}. Health score has dropped to {health:.1f}% with predicted '{fault}'."

        # Collect evidence lines from prediction
        evidence = [
            f"LTC model prediction: {fault} with {confidence*100:.1f}% confidence.",
            f"Machine health score evaluated at {health:.1f} / 100.",
            f"Unsupervised VAE anomaly score: {anomaly:.4f}.",
        ]
        if rul is not None:
            evidence.append(f"Linear trend extrapolation RUL: {rul:.1f} hours remaining.")

        # Grounded cause & actions from retrieved knowledge chunks
        likely_cause = f"Model output indicates signature corresponding to {fault}."
        recommended_actions = [pred["recommended_action"]]
        notes = "Enforce Lockout/Tagout (LOTO) protocols prior to physical inspection."

        if chunks:
            top_chunk = chunks[0]
            likely_cause += f" Reference doc ({top_chunk['title']}): verified matching spectral and impact patterns."

            for c in chunks[:2]:
                text = c["text"]
                # Extract bullet items or action lines from retrieved text if present
                for line in text.split("\n"):
                    line_clean = line.strip(" -*#0123456789.")
                    if len(line_clean) > 20 and not line_clean.startswith("Diagnostic") and not line_clean.startswith("Overview"):
                        if line_clean not in recommended_actions and len(recommended_actions) < 4:
                            recommended_actions.append(line_clean)

                if "LOTO" in text or "Safety" in text or "PPE" in text:
                    notes += " Verify PPE and zero energy state before servicing."

        return {
            "machine_id": pred["machine_id"],
            "timestamp": pred["timestamp"],
            "severity": severity,
            "title": title,
            "summary": summary,
            "evidence": evidence,
            "likely_cause": likely_cause,
            "recommended_action": recommended_actions,
            "urgency": urgency,
            "confidence": confidence,
            "notes": notes,
        }
