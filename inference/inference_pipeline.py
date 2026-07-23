import os
import sys
import json
import argparse
from datetime import datetime, timedelta, timezone

import numpy as np

sys.path.insert(0, os.path.abspath("."))

from inference.predict import LTCInferenceEngine
from preprocessing.bearing_common import sliding_window_indices


def replay_signal(engine: LTCInferenceEngine, machine_id: str, signal: np.ndarray, fs: float,
                   window_size: int = 2048, step: int = 1024, base_time: datetime = None) -> list:
    """
    Replays one long raw vibration recording through the inference engine
    window-by-window, in chronological order, returning one prediction JSON
    per window with the machine's hidden state (`hx`) carried continuously
    across all of them -- this is the offline equivalent of what a live
    deployment does: feed each newly-arrived window through
    predict_from_signal() and forward the resulting JSON downstream.

    Timestamps advance by exactly `step / fs` seconds per window (the true
    sensor cadence implied by the window step), NOT wall-clock "now" --
    otherwise every call would see ~0 elapsed time and the LTC's
    irregular-sampling-aware `timespans` input would be meaningless here.
    """
    engine.reset_machine(machine_id)
    base_time = base_time or datetime.now(timezone.utc)
    step_seconds = step / fs

    predictions = []
    for i, (start, end) in enumerate(sliding_window_indices(len(signal), window_size, step)):
        segment = signal[start:end]
        timestamp = base_time + timedelta(seconds=i * step_seconds)
        result = engine.predict_from_signal(machine_id, segment, fs, timestamp=timestamp)
        result["window_start_sample"] = start
        predictions.append(result)
    return predictions


def main():
    parser = argparse.ArgumentParser(description="Replay a raw vibration recording window-by-window through the LTC inference engine.")
    parser.add_argument("--signal", required=True, help="Path to a .npy file containing a 1D vibration signal")
    parser.add_argument("--fs", type=float, required=True)
    parser.add_argument("--machine-id", default="MACHINE_001")
    parser.add_argument("--window-size", type=int, default=2048)
    parser.add_argument("--step", type=int, default=1024)
    parser.add_argument("--checkpoint", default=os.path.join("data", "checkpoints", "lnn", "best_ltc.pt"))
    parser.add_argument("--scaler", default=os.path.join("data", "unified", "feature_scaler.json"))
    parser.add_argument("--vae-checkpoint", default=os.path.join("data", "checkpoints", "vae", "healthy_vae.pt"))
    parser.add_argument("--vae-scaler", default=os.path.join("data", "unified_schema", "feature_scaler.json"))
    parser.add_argument("--output", default=None, help="Optional path to write predictions as JSONL")
    args = parser.parse_args()

    engine = LTCInferenceEngine(args.checkpoint, args.scaler, vae_checkpoint_path=args.vae_checkpoint, vae_scaler_path=args.vae_scaler)
    signal = np.load(args.signal)
    predictions = replay_signal(engine, args.machine_id, signal, args.fs, args.window_size, args.step)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            for p in predictions:
                f.write(json.dumps(p) + "\n")
        print(f"Wrote {len(predictions)} predictions to {args.output}")
    else:
        for p in predictions[-5:]:
            print(json.dumps(p, indent=2))
        print(f"... {len(predictions)} total predictions")


if __name__ == "__main__":
    main()
