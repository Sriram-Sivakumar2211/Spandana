import os
import sys
import json
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.abspath("."))

from preprocessing.metropt3_preprocess import MetroPT3Preprocessor
from preprocessing.thermal_preprocess import ThermalMotorPreprocessor
from preprocessing.squirrel_cage_preprocess import SquirrelCagePreprocessor
from preprocessing.window_generator import SlidingWindowGenerator

def export_all():
    base_dir = "."
    proc_dir = os.path.join(base_dir, "data", "processed")
    win_dir = os.path.join(base_dir, "data", "windows")
    stream_dir = os.path.join(base_dir, "data", "stream_ready")

    os.makedirs(proc_dir, exist_ok=True)
    os.makedirs(win_dir, exist_ok=True)
    os.makedirs(stream_dir, exist_ok=True)

    win_gen = SlidingWindowGenerator(machine_id="MOTOR_001")
    all_stream_records = []

    # ---------------------------------------------------------
    # 1. METROPT-3 DATASET EXPORT
    # ---------------------------------------------------------
    print("--- Processing MetroPT-3 Dataset ---")
    metro_prep = MetroPT3Preprocessor()
    # Process sample subset for fast export and model readiness (e.g. 50,000 rows)
    df_metro = metro_prep.load_and_clean(nrows=50000)

    # Save cleaned table
    df_metro.to_parquet(os.path.join(proc_dir, "metropt3_cleaned.parquet"), index=False)
    df_metro.head(5000).to_csv(os.path.join(proc_dir, "metropt3_cleaned.csv"), index=False)

    metro_windows = win_gen.generate_df_windows(df_metro, source="metropt3", window_size=60, step=10)
    print(f"Generated {len(metro_windows)} MetroPT-3 sliding windows.")

    metro_win_file = os.path.join(win_dir, "metropt3_windows.jsonl")
    metro_stream_file = os.path.join(stream_dir, "metropt3_stream.jsonl")
    
    with open(metro_win_file, "w", encoding="utf-8") as f1, open(metro_stream_file, "w", encoding="utf-8") as f2:
        for w in metro_windows:
            line = json.dumps(w) + "\n"
            f1.write(line)
            f2.write(line)
            all_stream_records.append(w)

    # Export numeric NPY arrays for LNN/LSTM model training
    metro_feat_matrix = np.array([[v for v in w["features"].values()] for w in metro_windows], dtype=np.float32)
    metro_label_array = np.array([w["label"] for w in metro_windows])
    np.save(os.path.join(win_dir, "metropt3_features.npy"), metro_feat_matrix)
    np.save(os.path.join(win_dir, "metropt3_labels.npy"), metro_label_array)

    # ---------------------------------------------------------
    # 2. THERMAL MOTOR DATASET EXPORT
    # ---------------------------------------------------------
    print("\n--- Processing Thermal Motor Dataset ---")
    thermal_prep = ThermalMotorPreprocessor()
    thermal_imgs, thermal_meta = thermal_prep.load_samples(target_size=(128, 128), max_samples=2000)
    print(f"Loaded {len(thermal_imgs)} thermal motor images.")

    if len(thermal_imgs) > 0:
        thermal_windows = win_gen.generate_image_windows(thermal_imgs, thermal_meta, source="thermal_motor", window_size=10, step=5)
        print(f"Generated {len(thermal_windows)} thermal motor sliding windows.")

        thermal_win_file = os.path.join(win_dir, "thermal_motor_windows.jsonl")
        thermal_stream_file = os.path.join(stream_dir, "thermal_motor_stream.jsonl")

        with open(thermal_win_file, "w", encoding="utf-8") as f1, open(thermal_stream_file, "w", encoding="utf-8") as f2:
            for w in thermal_windows:
                line = json.dumps(w) + "\n"
                f1.write(line)
                f2.write(line)
                all_stream_records.append(w)

        thermal_feat_matrix = np.array([[v for v in w["features"].values()] for w in thermal_windows], dtype=np.float32)
        thermal_label_array = np.array([w["label"] for w in thermal_windows])
        np.save(os.path.join(win_dir, "thermal_motor_features.npy"), thermal_feat_matrix)
        np.save(os.path.join(win_dir, "thermal_motor_labels.npy"), thermal_label_array)

        # Tabular feature summary export
        df_thermal_feats = pd.DataFrame([w["features"] for w in thermal_windows])
        df_thermal_feats["label"] = [w["label"] for w in thermal_windows]
        df_thermal_feats.to_parquet(os.path.join(proc_dir, "thermal_motor_features.parquet"), index=False)
        df_thermal_feats.to_csv(os.path.join(proc_dir, "thermal_motor_features.csv"), index=False)

    # ---------------------------------------------------------
    # 3. SQUIRREL-CAGE INDUCTION MOTOR DATASET EXPORT
    # ---------------------------------------------------------
    print("\n--- Processing Squirrel-Cage Induction Motor Dataset ---")
    sq_prep = SquirrelCagePreprocessor()
    sq_imgs, sq_meta = sq_prep.load_samples(target_size=(128, 128))
    print(f"Loaded {len(sq_imgs)} squirrel cage images.")

    if len(sq_imgs) > 0:
        sq_windows = win_gen.generate_image_windows(sq_imgs, sq_meta, source="squirrel_cage", window_size=10, step=5)
        print(f"Generated {len(sq_windows)} squirrel cage sliding windows.")

        sq_win_file = os.path.join(win_dir, "squirrel_cage_windows.jsonl")
        sq_stream_file = os.path.join(stream_dir, "squirrel_cage_stream.jsonl")

        with open(sq_win_file, "w", encoding="utf-8") as f1, open(sq_stream_file, "w", encoding="utf-8") as f2:
            for w in sq_windows:
                line = json.dumps(w) + "\n"
                f1.write(line)
                f2.write(line)
                all_stream_records.append(w)

        sq_feat_matrix = np.array([[v for v in w["features"].values()] for w in sq_windows], dtype=np.float32)
        sq_label_array = np.array([w["label"] for w in sq_windows])
        np.save(os.path.join(win_dir, "squirrel_cage_features.npy"), sq_feat_matrix)
        np.save(os.path.join(win_dir, "squirrel_cage_labels.npy"), sq_label_array)

        df_sq_feats = pd.DataFrame([w["features"] for w in sq_windows])
        df_sq_feats["label"] = [w["label"] for w in sq_windows]
        df_sq_feats.to_parquet(os.path.join(proc_dir, "squirrel_cage_features.parquet"), index=False)
        df_sq_feats.to_csv(os.path.join(proc_dir, "squirrel_cage_features.csv"), index=False)

    # ---------------------------------------------------------
    # 4. UNIFIED STREAM EXPORT
    # ---------------------------------------------------------
    unified_stream_file = os.path.join(stream_dir, "unified_stream.jsonl")
    with open(unified_stream_file, "w", encoding="utf-8") as f:
        for w in all_stream_records:
            f.write(json.dumps(w) + "\n")

    print(f"\nSUCCESS: Exported {len(all_stream_records)} total unified window records across all 3 datasets.")

if __name__ == "__main__":
    export_all()
