import os
import sys
import json
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath("."))

from realtime.replay import run_replay

def validate_pipeline():
    print("=== STARTING PIPELINE VALIDATION ===")
    errors = []

    # 1. Check folder existence and file non-emptiness
    required_files = [
        "data/processed/metropt3_cleaned.parquet",
        "data/processed/metropt3_cleaned.csv",
        "data/processed/thermal_motor_features.parquet",
        "data/processed/thermal_motor_features.csv",
        "data/processed/squirrel_cage_features.parquet",
        "data/processed/squirrel_cage_features.csv",
        "data/windows/metropt3_windows.jsonl",
        "data/windows/metropt3_features.npy",
        "data/windows/metropt3_labels.npy",
        "data/windows/thermal_motor_windows.jsonl",
        "data/windows/thermal_motor_features.npy",
        "data/windows/thermal_motor_labels.npy",
        "data/windows/squirrel_cage_windows.jsonl",
        "data/windows/squirrel_cage_features.npy",
        "data/windows/squirrel_cage_labels.npy",
        "data/stream_ready/metropt3_stream.jsonl",
        "data/stream_ready/thermal_motor_stream.jsonl",
        "data/stream_ready/squirrel_cage_stream.jsonl",
        "data/stream_ready/unified_stream.jsonl"
    ]

    for fpath in required_files:
        if not os.path.exists(fpath):
            errors.append(f"Missing required output file: {fpath}")
        elif os.path.getsize(fpath) == 0:
            errors.append(f"File is empty: {fpath}")
        else:
            print(f"  [PASS] File exists and non-empty: {fpath} ({os.path.getsize(fpath)} bytes)")

    # 2. Validate JSON Schema & NaN checks in JSONL records
    valid_sources = {"squirrel_cage", "metropt3", "thermal_motor"}
    valid_labels = {"healthy", "warning", "faulty"}
    required_feature_keys = {"rms", "kurtosis", "skewness", "crest_factor", "dominant_frequency", "temperature", "current", "rpm"}

    for stream_file in ["data/stream_ready/unified_stream.jsonl"]:
        if os.path.exists(stream_file):
            record_count = 0
            with open(stream_file, "r", encoding="utf-8") as f:
                for idx, line in enumerate(f):
                    record_count += 1
                    try:
                        rec = json.loads(line)
                    except Exception as e:
                        errors.append(f"Line {idx} in {stream_file} is invalid JSON: {e}")
                        continue

                    # Key presence checks
                    for key in ["machine_id", "timestamp", "source", "window_id", "features", "label"]:
                        if key not in rec:
                            errors.append(f"Line {idx} missing key '{key}'")

                    if rec.get("source") not in valid_sources:
                        errors.append(f"Line {idx} invalid source: {rec.get('source')}")

                    if rec.get("label") not in valid_labels:
                        errors.append(f"Line {idx} invalid label: {rec.get('label')}")

                    # Feature NaN checks
                    feats = rec.get("features", {})
                    missing_feat_keys = required_feature_keys - set(feats.keys())
                    if missing_feat_keys:
                        errors.append(f"Line {idx} features missing required keys: {missing_feat_keys}")

                    for fk, fval in feats.items():
                        if fval is None or (isinstance(fval, float) and (np.isnan(fval) or np.isinf(fval))):
                            errors.append(f"Line {idx} feature '{fk}' contains NaN/Inf/None: {fval}")

            print(f"  [PASS] Validated {record_count} stream records in {stream_file}")

    # 3. Check NPY array shapes and NaNs
    for npy_name in ["metropt3_features.npy", "thermal_motor_features.npy", "squirrel_cage_features.npy"]:
        npy_path = os.path.join("data", "windows", npy_name)
        if os.path.exists(npy_path):
            arr = np.load(npy_path)
            if np.isnan(arr).any() or np.isinf(arr).any():
                errors.append(f"NPY array {npy_name} contains NaN or Inf values!")
            else:
                print(f"  [PASS] NPY array {npy_name} shape {arr.shape} is clean (No NaNs/Infs).")

    # 4. Test Real-Time Replay Engine execution
    print("\n--- Testing Real-Time Replay Engine ---")
    try:
        run_replay(source="metropt3", delay=0.01, limit=5, post_api=False)
        print("  [PASS] Real-time replay executed successfully.")
    except Exception as e:
        errors.append(f"Real-time replay raised exception: {e}")

    # 5. Final Verdict
    print("\n========================================")
    if errors:
        print(f"VALIDATION FAILED with {len(errors)} errors:")
        for err in errors:
            print(f" - {err}")
        sys.exit(1)
    else:
        print("ALL VALIDATION TESTS PASSED SUCCESSFULLY! Data pipeline is ready for Member 2 handoff.")
        print("========================================")

if __name__ == "__main__":
    validate_pipeline()
