import os
import sys
import json
import argparse
from datetime import datetime, timezone
from typing import Optional

import numpy as np
import torch

sys.path.insert(0, os.path.abspath("."))

from lnn.model import SpandanaLTC
from preprocessing.bearing_common import BEARING_CLASSES, decode_label, SignalScaler
from features.bearing_features import extract_bearing_feature_vector, feature_vector_to_array, BEARING_FEATURE_KEYS
from inference.decision_rules import recommend_action
from augmentation.vae import FeatureVAE
from utils.schema import CANONICAL_FEATURE_KEYS, fill_feature_vector

# This engine's inputs are always bearing-vibration windows, so only the
# dims a bearing feature vector actually populates are meaningful for
# reconstruction-error-based anomaly scoring -- see FeatureVAE.reconstruction_error.
_BEARING_DIM_INDICES = [CANONICAL_FEATURE_KEYS.index(k) for k in BEARING_FEATURE_KEYS]

_FAULT_TYPE_DISPLAY = {
    "healthy": "Healthy",
    "inner_race": "Inner Race Fault",
    "outer_race": "Outer Race Fault",
    "ball": "Ball/Roller Fault",
    "combined": "Combined Inner+Outer Fault",
}

_MIN_RUL_HISTORY = 5
_MIN_DECLINE_PER_HOUR = 0.05  # health_score points/hour; below this we consider the trend too flat to project


class LTCInferenceEngine:
    """
    Production inference engine for Spandana, built around the fact that
    `ncps.torch.LTC` is a genuinely stateful recurrent cell: `forward`
    returns the hidden state (`hx`) it just computed, and accepts the
    previous call's `hx` back in. This engine keeps one `hx` per
    `machine_id` and feeds ONE window at a time (seq_len=1 per call) rather
    than re-processing a fixed lookback buffer -- the machine's continuous
    operating history lives entirely in its persisted `hx`, which is what
    "a continuously updating machine memory" means concretely here.

    It also tracks each machine's last-seen timestamp so it can pass the
    real elapsed wall-clock time as `timespans` on the next call -- a
    machine whose sensor read late or early changes the LTC's internal
    dynamics accordingly, instead of silently being treated as on-time.
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

        # Optional VAE-based anomaly scorer, trained on "healthy"-only feature
        # vectors in the 24-dim canonical schema (utils/schema.py) shared
        # across all 6 datasets -- see augmentation/vae.py. NOTE (disclosed,
        # not hidden): because each dataset only populates its own slice of
        # that 24-dim vector and zero-fills the rest, this reconstruction
        # error is confounded with "which sensor rig produced this reading"
        # as much as with genuine health signal. Treat anomaly_score as a
        # secondary, weaker indicator alongside fault_probability, not a
        # replacement for it. If the VAE/scaler files aren't present, this
        # falls back to fault_probability, matching the original behavior.
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
        self._health_history: dict[str, list] = {}  # machine_id -> [(timestamp, health_score), ...]

    def reset_machine(self, machine_id: str):
        """Clears persisted state for one machine, e.g. after a bearing swap or sensor reset."""
        self._hx.pop(machine_id, None)
        self._last_timestamp.pop(machine_id, None)
        self._health_history.pop(machine_id, None)

    def _elapsed_seconds(self, machine_id: str, timestamp: datetime) -> float:
        last = self._last_timestamp.get(machine_id)
        if last is None:
            return 1.0  # first observation for this machine: no prior reference, assume unit dt
        return max((timestamp - last).total_seconds(), 1e-3)

    def _estimate_rul_hours(self, machine_id: str) -> Optional[float]:
        """
        Linear trend of health_score vs. time for this machine. Returns
        None (omitted from the output, not a fabricated number) unless
        there is enough history AND a clearly declining trend -- reporting
        a "remaining useful life" from 2 noisy points or a flat/improving
        trend would be actively misleading.
        """
        history = self._health_history.get(machine_id, [])
        if len(history) < _MIN_RUL_HISTORY:
            return None

        t0 = history[0][0]
        hours = np.array([(t - t0).total_seconds() / 3600.0 for t, _ in history])
        scores = np.array([s for _, s in history])
        if hours.max() - hours.min() < 1e-6:
            return None

        slope, intercept = np.polyfit(hours, scores, 1)  # health_score per hour
        if slope >= -_MIN_DECLINE_PER_HOUR:
            return None  # flat or improving -- no meaningful "time to failure" to report

        current_hour = hours[-1]
        current_score = scores[-1]
        hours_to_zero = current_score / (-slope)
        return round(float(max(hours_to_zero, 0.0)), 2)

    @torch.no_grad()
    def _vae_anomaly_score(self, bearing_feature_vector: np.ndarray, fallback: float) -> float:
        """
        Converts the 17-dim bearing feature vector into the 24-dim canonical
        schema (utils.schema.fill_feature_vector, zero-filling fields this
        source doesn't provide), scales it with the general model's scaler,
        and returns the healthy-only VAE's reconstruction error squashed to
        [0, 1) via 1 - exp(-mse / scale). Falls back to `fallback`
        (fault_probability) if no VAE was loaded.
        """
        if self.vae is None or self.vae_scaler is None:
            return round(fallback, 4)

        bearing_feats = dict(zip(BEARING_FEATURE_KEYS, bearing_feature_vector.tolist()))
        canonical = fill_feature_vector(bearing_feats)
        canonical_vec = np.array([canonical[k] for k in CANONICAL_FEATURE_KEYS], dtype=np.float32)
        scaled = self.vae_scaler.transform(canonical_vec.reshape(1, -1), clip=10.0)
        x = torch.tensor(scaled, dtype=torch.float32).to(self.device)

        mse = float(self.vae.reconstruction_error(x, dims_mask=_BEARING_DIM_INDICES)[0])
        return round(float(1.0 - np.exp(-mse / 5.0)), 4)

    @torch.no_grad()
    def predict_from_signal(self, machine_id: str, signal: np.ndarray, fs: float,
                             window_id: str = None, timestamp: datetime = None) -> dict:
        """Extracts features from one raw vibration window and predicts using persisted machine state."""
        feats = extract_bearing_feature_vector(signal, fs=fs)
        return self.predict_from_feature_vector(machine_id, feature_vector_to_array(feats), window_id, timestamp)

    @torch.no_grad()
    def predict_from_feature_vector(self, machine_id: str, feature_vector: np.ndarray,
                                     window_id: str = None, timestamp: datetime = None) -> dict:
        timestamp = timestamp or datetime.now(timezone.utc)
        elapsed = self._elapsed_seconds(machine_id, timestamp)

        scaled = self.scaler.transform(feature_vector.reshape(1, -1))[0]
        x = torch.tensor(scaled, dtype=torch.float32).view(1, 1, -1).to(self.device)
        timespans = torch.tensor([[elapsed]], dtype=torch.float32).to(self.device)

        hx_in = self._hx.get(machine_id)
        logits, hx_out = self.model(x, hx_in, timespans)
        self._hx[machine_id] = hx_out.detach()
        self._last_timestamp[machine_id] = timestamp

        proba = torch.softmax(logits, dim=1).cpu().numpy()[0]
        pred_idx = int(np.argmax(proba))
        predicted_fault = decode_label(pred_idx)
        fault_probability = float(1.0 - proba[BEARING_CLASSES.index("healthy")])
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
            "predicted_fault": _FAULT_TYPE_DISPLAY.get(predicted_fault, predicted_fault),
            "prediction_confidence": round(prediction_confidence, 4),
            "remaining_useful_life_hours": remaining_useful_life_hours,
            "recommended_action": recommend_action(predicted_fault, health_score),
        }


def main():
    parser = argparse.ArgumentParser(description="Run one offline prediction from a raw vibration signal saved as .npy")
    parser.add_argument("--signal", required=True, help="Path to a .npy file containing a 1D vibration signal")
    parser.add_argument("--fs", type=float, required=True, help="Sample rate (Hz) of the signal")
    parser.add_argument("--machine-id", default="MACHINE_001")
    parser.add_argument("--checkpoint", default=os.path.join("data", "checkpoints", "lnn", "best_ltc.pt"))
    parser.add_argument("--scaler", default=os.path.join("data", "unified", "feature_scaler.json"))
    parser.add_argument("--vae-checkpoint", default=os.path.join("data", "checkpoints", "vae", "healthy_vae.pt"))
    parser.add_argument("--vae-scaler", default=os.path.join("data", "unified_schema", "feature_scaler.json"))
    args = parser.parse_args()

    engine = LTCInferenceEngine(args.checkpoint, args.scaler, vae_checkpoint_path=args.vae_checkpoint, vae_scaler_path=args.vae_scaler)
    signal = np.load(args.signal)
    result = engine.predict_from_signal(args.machine_id, signal, args.fs)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
