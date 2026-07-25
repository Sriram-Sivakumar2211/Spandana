import os
import re
import json
import logging
from typing import Dict, Any, List, Optional

from utils.schema import validate_report_record

logger = logging.getLogger("spandana.llm_generator")

# Matches a genuine markdown list item: "- ...", "* ...", "1. ...", "[ ] ...",
# "[x] ...". Used to tell real checklist/action lines apart from headers
# ("## Pre-Inspection Safety Protocol") and prose -- both of which used to
# get scooped up by a looser line filter and shown as if they were
# recommended actions, which read as nonsensical in the UI.
_LIST_ITEM_RE = re.compile(r"^(?:-|\*|\d+\.)\s+")
_CHECKBOX_RE = re.compile(r"^\[[ xX]\]\s*")


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
                # Gemini's JSON mode reliably produced schema-conformant output
                # in testing, but an LLM's output shape isn't a hard guarantee
                # the way a schema-validated code path is -- validate before
                # trusting it, since a malformed field (e.g. recommended_action
                # as a string instead of a list) would otherwise reach the
                # frontend's report.recommended_action.map(...) and crash the
                # whole page with no server-side signal anything went wrong.
                schema_error = validate_report_record(report) if report else "empty response"
                if schema_error:
                    logger.warning(f"Gemini response failed schema validation: {schema_error}. Falling back to grounded rule engine.")
                    report = None
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

        # "gemini-1.5-flash" was retired by Google (confirmed via a live
        # ListModels call against this project's API key -- it now 404s).
        # "gemini-flash-latest" is Google's maintained alias for the current
        # flash-tier model, chosen so this doesn't go stale again the next
        # time a specific dated model is deprecated.
        model = genai.GenerativeModel("gemini-flash-latest")
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

    def _extract_actionable_lines(self, text: str, limit: int) -> List[str]:
        """
        Pulls genuine checklist/action items out of a knowledge-base section --
        only lines actually written as a bullet, numbered, or checkbox list
        item, never a markdown heading or a prose sentence. The previous
        version matched ANY line over 20 characters, which meant section
        headings like "## Pre-Inspection Safety Protocol" or a document's own
        title were shown in the UI as if they were recommended actions --
        confusing, since a heading isn't an instruction.
        """
        actions: List[str] = []
        if limit <= 0:
            return actions
        for raw_line in text.split("\n"):
            line = raw_line.strip()
            if not line or not _LIST_ITEM_RE.match(line):
                continue
            # "- [ ] Verify..." is a bullet AND a checkbox stacked -- strip
            # the bullet marker first, then the checkbox that follows it.
            cleaned = _LIST_ITEM_RE.sub("", line)
            cleaned = _CHECKBOX_RE.sub("", cleaned)
            cleaned = cleaned.replace("**", "").strip()
            cleaned = cleaned.rstrip(".") + "."
            if len(cleaned) < 15 or len(cleaned) > 220:
                continue
            if cleaned not in actions:
                actions.append(cleaned)
            if len(actions) >= limit:
                break
        return actions

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

        # Grounded cause, tailored per severity rather than one generic
        # sentence reused for every outcome including "healthy" (where
        # claiming to have "verified matching spectral and impact patterns"
        # made no sense -- a healthy reading has no fault pattern to match).
        top_chunk = chunks[0] if chunks else None
        if severity == "healthy":
            likely_cause = "Model output shows no fault signature present."
            if top_chunk:
                likely_cause += f" Cross-checked against '{top_chunk['title']}', consistent with normal operating parameters."
        else:
            likely_cause = f"Model output indicates a signature consistent with '{fault}'."
            if top_chunk:
                likely_cause += f" Reference: '{top_chunk['title']}' ({top_chunk['source_file']})."

        # Actions: the model's own rule-based recommendation first, then real
        # checklist items pulled from the top retrieved chunks (never
        # headers/titles -- see _extract_actionable_lines).
        recommended_actions = [pred["recommended_action"]]
        for c in chunks[:2]:
            remaining = 4 - len(recommended_actions)
            if remaining <= 0:
                break
            for action in self._extract_actionable_lines(c["text"], remaining):
                if action not in recommended_actions:
                    recommended_actions.append(action)

        # Safety note only makes sense when physical inspection is actually
        # being recommended -- a healthy machine needing "no action" doesn't
        # need a LOTO/PPE warning attached to it.
        if severity == "healthy":
            notes = "No physical intervention required at this time; continue routine monitoring."
        else:
            notes = "Enforce Lockout/Tagout (LOTO) protocols and verify PPE (safety glasses, gloves, ear protection) before any physical inspection or servicing."

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
