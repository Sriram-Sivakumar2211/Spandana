import os
import json
from datetime import datetime, timezone
from typing import Optional

import numpy as np
import torch

from lnn.model import SpandanaLTC
from preprocessing.bearing_common import SignalScaler
from utils.schema import CANONICAL_FEATURE_KEYS, GROUND_TRUTH_ENUM, decode_ground_truth, fill_feature_vector
from inference.decision_rules import recommend_action
from augmentation.vae import FeatureVAE

_MIN_RUL_HISTORY = 5
_MIN_DECLINE_PER_HOUR = 0.05


class GeneralLTCInferenceEngine:
    """
    Serving wrapper for the general 6-dataset severity model (healthy/warning/
    faulty), the counterpart to inference/predict.py::LTCInferenceEngine (the
    bearing-only 5-class fault-location specialist). Exists because feeding
    non-bearing sources (MetroPT-3, squirrel-cage, thermal motor -- Track 1)
    through the bearing specialist would repeat the exact cross-modality
    mismatch documented in reports/cross_modality_report.md: those sources
    populate a different slice of the canonical feature space than the
    17-dim bearing vector the specialist expects. This engine instead consumes
    the 24-dim canonical feature space (utils/schema.py) any of the 6 sources
    can be expressed in, and is the correct model to call for that traffic.

    Same statefulness design as the bearing engine: one hidden state (`hx`)
    per machine_id, real elapsed time as `timespans`, single window per call.
    """

    def __init__(self, checkpoint_path: str, scaler_path: str, device: str = "cpu",
                 vae_checkpoint_path: str = None, vae_scaler_path: str = None):
        self.device = torch.device(device)
        checkpoint = torch.load(checkpoint_path, map_location=self.device, weights_only=False)
        cfg = checkpoint["config"]

        self.model = SpandanaLTC(
            input_size=checkpoint["input_size"],
            num_classes=checkpoint["num_classes"],
            hidden_size=cfg["hidden_size"],
            sparsity_level=cfg["sparsity_level"],
            ode_unfolds=cfg["ode_unfolds"],
            seed=cfg["seed"],
        )
        self.model.load_state_dict(checkpoint["model_state_dict"])
        self.model.to(self.device)
        self.model.eval()

        with open(scaler_path, "r", encoding="utf-8") as f:
            self.scaler = SignalScaler.from_dict(json.load(f))

        # Same healthy-only VAE reused by the bearing engine for anomaly
        # scoring -- here applied unmasked (full 24-dim reconstruction error),
        # since "which dims are informative" varies per source and there is
        # no single source-specific mask to apply generically.
        self.vae = None
        self.vae_scaler = None
        if vae_checkpoint_path and vae_scaler_path and os.path.exists(vae_checkpoint_path) and os.path.exists(vae_scaler_path):
            vae_checkpoint = torch.load(vae_checkpoint_path, map_location=self.device, weights_only=False)
            self.vae = FeatureVAE(input_dim=vae_checkpoint["input_dim"], latent_dim=vae_checkpoint["latent_dim"])
            self.vae.load_state_dict(vae_checkpoint["model_state_dict"])
            self.vae.to(self.device)
            self.vae.eval()
            with open(vae_scaler_path, "r", encoding="utf-8") as f:
                self.vae_scaler = SignalScaler.from_dict(json.load(f))

        self._hx: dict[str, torch.Tensor] = {}
        self._last_timestamp: dict[str, datetime] = {}
        self._health_history: dict[str, list] = {}

    def reset_machine(self, machine_id: str):
        self._hx.pop(machine_id, None)
        self._last_timestamp.pop(machine_id, None)
        self._health_history.pop(machine_id, None)

    def _elapsed_seconds(self, machine_id: str, timestamp: datetime) -> float:
        last = self._last_timestamp.get(machine_id)
        if last is None:
            return 1.0
        return max((timestamp - last).total_seconds(), 1e-3)

    def _estimate_rul_hours(self, machine_id: str) -> Optional[float]:
        history = self._health_history.get(machine_id, [])
        if len(history) < _MIN_RUL_HISTORY:
            return None
        t0 = history[0][0]
        hours = np.array([(t - t0).total_seconds() / 3600.0 for t, _ in history])
        scores = np.array([s for _, s in history])
        if hours.max() - hours.min() < 1e-6:
            return None
        slope, _intercept = np.polyfit(hours, scores, 1)
        if slope >= -_MIN_DECLINE_PER_HOUR:
            return None
        current_hour = hours[-1]
        current_score = scores[-1]
        hours_to_zero = current_score / (-slope)
        return round(float(max(hours_to_zero, 0.0)), 2)

    @torch.no_grad()
    def _vae_anomaly_score(self, canonical_vec: np.ndarray, fallback: float) -> float:
        if self.vae is None or self.vae_scaler is None:
            return round(fallback, 4)
        scaled = self.vae_scaler.transform(canonical_vec.reshape(1, -1), clip=10.0)
        x = torch.tensor(scaled, dtype=torch.float32).to(self.device)
        mse = float(self.vae.reconstruction_error(x)[0])
        return round(float(1.0 - np.exp(-mse / 5.0)), 4)

    @torch.no_grad()
    def predict_from_features(self, machine_id: str, features: dict,
                               window_id: str = None, timestamp: datetime = None) -> dict:
        """
        `features` may be a partial dict (e.g. Member 1's 12-key sensor
        payload, or a bearing source's 17-key vector) -- fill_feature_vector
        zero-fills whatever this source doesn't populate, exactly as done at
        training time (preprocessing/schema_adapter.py).
        """
        timestamp = timestamp or datetime.now(timezone.utc)
        elapsed = self._elapsed_seconds(machine_id, timestamp)

        canonical = fill_feature_vector(features)
        feature_vector = np.array([canonical[k] for k in CANONICAL_FEATURE_KEYS], dtype=np.float32)

        scaled = self.scaler.transform(feature_vector.reshape(1, -1))[0]
        x = torch.tensor(scaled, dtype=torch.float32).view(1, 1, -1).to(self.device)
        timespans = torch.tensor([[elapsed]], dtype=torch.float32).to(self.device)

        hx_in = self._hx.get(machine_id)
        logits, hx_out = self.model(x, hx_in, timespans)
        self._hx[machine_id] = hx_out.detach()
        self._last_timestamp[machine_id] = timestamp

        proba = torch.softmax(logits, dim=1).cpu().numpy()[0]
        pred_idx = int(np.argmax(proba))
        predicted_label = decode_ground_truth(pred_idx)
        healthy_idx = GROUND_TRUTH_ENUM.index("healthy")
        fault_probability = float(1.0 - proba[healthy_idx])
        health_score = round(float(max(0.0, min(100.0, (1.0 - fault_probability) * 100.0))), 2)
        prediction_confidence = float(proba[pred_idx])

        anomaly_score = self._vae_anomaly_score(feature_vector, fallback=fault_probability)

        history = self._health_history.setdefault(machine_id, [])
        history.append((timestamp, health_score))
        remaining_useful_life_hours = self._estimate_rul_hours(machine_id)

        return {
            "machine_id": machine_id,
            "window_id": window_id or f"{machine_id}_{timestamp.isoformat()}",
            "timestamp": timestamp.isoformat(),
            "health_score": health_score,
            "anomaly_score": anomaly_score,
            "fault_probability": round(fault_probability, 4),
            "predicted_fault": predicted_label,
            "prediction_confidence": round(prediction_confidence, 4),
            "remaining_useful_life_hours": remaining_useful_life_hours,
            "recommended_action": recommend_action(predicted_label, health_score),
        }
