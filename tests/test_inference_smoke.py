import os
import sys
import json
import numpy as np

sys.path.insert(0, os.path.abspath("."))

from preprocessing.cwru_preprocess import CWRUPreprocessor
from inference.predict import LTCInferenceEngine
from inference.inference_pipeline import replay_signal


def main():
    prep = CWRUPreprocessor(raw_dir="C:/Users/MG-Laptop/OneDrive/Data/Hackathons/LNN/Datasets/CWRU bearing dataset/raw")
    records = prep.load_all()
    ir_record = next(r for r in records if r["bearing_class"] == "inner_race")
    print(f"Using real signal from {ir_record['source_file']} (ground-truth class={ir_record['bearing_class']}), "
          f"{len(ir_record['signal'])} samples @ {ir_record['fs']} Hz")

    engine = LTCInferenceEngine(
        checkpoint_path=os.path.join("data", "checkpoints", "lnn", "best_ltc.pt"),
        scaler_path=os.path.join("data", "unified", "feature_scaler.json"),
        vae_checkpoint_path=os.path.join("data", "checkpoints", "vae", "healthy_vae.pt"),
        vae_scaler_path=os.path.join("data", "unified_schema", "feature_scaler.json"),
    )
    print(f"VAE anomaly scorer loaded: {engine.vae is not None}")

    predictions = replay_signal(engine, "CWRU_TEST_MOTOR", ir_record["signal"], ir_record["fs"],
                                 window_size=4096, step=2048)

    print(f"\nProduced {len(predictions)} window predictions. Last 3:")
    for p in predictions[-3:]:
        print(json.dumps(p, indent=2))

    fault_type_counts = {}
    for p in predictions:
        fault_type_counts[p["predicted_fault"]] = fault_type_counts.get(p["predicted_fault"], 0) + 1
    print(f"\nPrediction distribution across the replay: {fault_type_counts}")
    print(f"Final RUL estimate (if any): {predictions[-1]['remaining_useful_life_hours']}")


if __name__ == "__main__":
    main()
