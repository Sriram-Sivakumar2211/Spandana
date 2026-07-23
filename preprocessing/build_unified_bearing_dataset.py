import os
import sys
import json
import logging
import numpy as np

sys.path.insert(0, os.path.abspath("."))

from preprocessing.nasa_ims_preprocess import NASAIMSPreprocessor
from preprocessing.cwru_preprocess import CWRUPreprocessor
from preprocessing.paderborn_preprocess import PaderbornPreprocessor
from preprocessing.window_generator import SlidingWindowGenerator
from preprocessing.bearing_common import encode_label, group_aware_split, SignalScaler, BEARING_CLASSES
from features.bearing_features import BEARING_FEATURE_KEYS, feature_vector_to_array

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def _windows_to_arrays(windows: list):
    X = np.stack([feature_vector_to_array(w["features"]) for w in windows]).astype(np.float32)
    y = np.array([encode_label(w["label"]) for w in windows], dtype=np.int64)
    groups = np.array([w["group_id"] for w in windows])
    return X, y, groups


def build_dataset(name: str, records: list, win_gen: SlidingWindowGenerator, window_size: int, step: int) -> list:
    all_windows = []
    for rec in records:
        windows = win_gen.generate_vibration_windows(
            signal=rec["signal"],
            fs=rec["fs"],
            source=name,
            bearing_class=rec["bearing_class"],
            source_file=rec["source_file"],
            window_size=window_size,
            step=step,
        )
        all_windows.extend(windows)
    logger.info("%s: %d raw recordings -> %d windows", name, len(records), len(all_windows))
    return all_windows


def process_dataset(name: str, records: list, pcfg: dict, out_dirs: dict, split_cfg: dict) -> dict:
    win_gen = SlidingWindowGenerator(machine_id=f"{name.upper()}_RIG")
    windows = build_dataset(name, records, win_gen, pcfg["window_size"], pcfg["step"])
    if not windows:
        raise RuntimeError(f"No windows produced for dataset {name}")

    X, y, groups = _windows_to_arrays(windows)
    train_mask, val_mask, test_mask = group_aware_split(
        groups, val_size=split_cfg["val_size"], test_size=split_cfg["test_size"], seed=split_cfg["seed"]
    )

    os.makedirs(out_dirs["windows_dir"], exist_ok=True)
    os.makedirs(out_dirs["splits_dir"], exist_ok=True)

    np.save(os.path.join(out_dirs["windows_dir"], f"{name}_features.npy"), X)
    np.save(os.path.join(out_dirs["windows_dir"], f"{name}_labels.npy"), y)
    np.save(os.path.join(out_dirs["windows_dir"], f"{name}_groups.npy"), groups)

    # Also persist the raw per-window records as JSONL, matching Member 1's
    # data/windows/*_windows.jsonl convention -- this is what
    # preprocessing/schema_adapter.py reads to standardize both tracks into
    # the shared backend/schemas/sensor_input.json schema, without needing
    # to re-run any raw-signal preprocessing.
    windows_jsonl_path = os.path.join(out_dirs["windows_dir"], f"{name}_windows.jsonl")
    with open(windows_jsonl_path, "w", encoding="utf-8") as f:
        for w in windows:
            f.write(json.dumps(w) + "\n")

    np.savez(
        os.path.join(out_dirs["splits_dir"], f"{name}_split.npz"),
        train_mask=train_mask, val_mask=val_mask, test_mask=test_mask,
    )

    class_counts = {c: int(np.sum(y == encode_label(c))) for c in BEARING_CLASSES if np.sum(y == encode_label(c)) > 0}
    logger.info("%s class distribution: %s", name, class_counts)

    return {
        "name": name,
        "n_windows": len(windows),
        "feature_dim": X.shape[1],
        "class_counts": class_counts,
        "n_train": int(train_mask.sum()),
        "n_val": int(val_mask.sum()),
        "n_test": int(test_mask.sum()),
        "X": X, "y": y, "groups": groups,
        "train_mask": train_mask, "val_mask": val_mask, "test_mask": test_mask,
    }


def build_unified_split(results: dict, unified_dir: str):
    os.makedirs(unified_dir, exist_ok=True)

    X_train_parts, y_train_parts, src_train_parts = [], [], []
    X_val_parts, y_val_parts, src_val_parts = [], [], []
    X_test_parts, y_test_parts, src_test_parts = [], [], []

    for name, res in results.items():
        X, y = res["X"], res["y"]
        for mask, Xp, yp, sp in [
            (res["train_mask"], X_train_parts, y_train_parts, src_train_parts),
            (res["val_mask"], X_val_parts, y_val_parts, src_val_parts),
            (res["test_mask"], X_test_parts, y_test_parts, src_test_parts),
        ]:
            Xp.append(X[mask])
            yp.append(y[mask])
            sp.append(np.array([name] * int(mask.sum())))

    X_train = np.concatenate(X_train_parts)
    y_train = np.concatenate(y_train_parts)
    src_train = np.concatenate(src_train_parts)
    X_val = np.concatenate(X_val_parts)
    y_val = np.concatenate(y_val_parts)
    src_val = np.concatenate(src_val_parts)
    X_test = np.concatenate(X_test_parts)
    y_test = np.concatenate(y_test_parts)
    src_test = np.concatenate(src_test_parts)

    scaler = SignalScaler().fit(X_train)
    X_train_s = scaler.transform(X_train)
    X_val_s = scaler.transform(X_val)
    X_test_s = scaler.transform(X_test)

    np.savez(
        os.path.join(unified_dir, "unified_bearing_dataset.npz"),
        X_train=X_train_s, y_train=y_train, src_train=src_train,
        X_val=X_val_s, y_val=y_val, src_val=src_val,
        X_test=X_test_s, y_test=y_test, src_test=src_test,
    )
    with open(os.path.join(unified_dir, "feature_scaler.json"), "w", encoding="utf-8") as f:
        json.dump(scaler.to_dict(), f, indent=2)
    with open(os.path.join(unified_dir, "feature_schema.json"), "w", encoding="utf-8") as f:
        json.dump({"feature_keys": BEARING_FEATURE_KEYS, "classes": BEARING_CLASSES}, f, indent=2)

    logger.info(
        "Unified dataset: train=%d val=%d test=%d, feature_dim=%d",
        len(y_train), len(y_val), len(y_test), X_train.shape[1],
    )
    return {
        "n_train": len(y_train), "n_val": len(y_val), "n_test": len(y_test),
        "feature_dim": int(X_train.shape[1]),
    }


def main():
    with open(os.path.join("configs", "dataset_paths.json"), "r", encoding="utf-8") as f:
        paths = json.load(f)
    with open(os.path.join("configs", "preprocessing_config.json"), "r", encoding="utf-8") as f:
        pcfg_all = json.load(f)

    out_dirs = {
        "windows_dir": paths["output"]["windows_dir"],
        "splits_dir": paths["output"]["splits_dir"],
    }
    split_cfg = pcfg_all["split"]

    logger.info("Loading NASA IMS records...")
    nasa_prep = NASAIMSPreprocessor(raw_dir=paths["nasa_ims"]["raw_dir"])
    nasa_records = nasa_prep.load_all(max_files_per_test=pcfg_all["nasa_ims"]["max_files_per_test"])

    logger.info("Loading CWRU records...")
    cwru_prep = CWRUPreprocessor(raw_dir=paths["cwru"]["raw_dir"])
    cwru_records = cwru_prep.load_all()

    logger.info("Loading Paderborn records...")
    pb_prep = PaderbornPreprocessor(raw_dir=paths["paderborn"]["raw_dir"])
    pb_records = pb_prep.load_all(
        bearing_codes=pcfg_all["paderborn"]["bearing_codes"],
        max_files_per_code=pcfg_all["paderborn"]["max_files_per_code"],
    )

    results = {}
    results["nasa_ims"] = process_dataset("nasa_ims", nasa_records, pcfg_all["nasa_ims"], out_dirs, split_cfg)
    results["cwru"] = process_dataset("cwru", cwru_records, pcfg_all["cwru"], out_dirs, split_cfg)
    results["paderborn"] = process_dataset("paderborn", pb_records, pcfg_all["paderborn"], out_dirs, split_cfg)

    unified_summary = build_unified_split(results, paths["output"]["unified_dir"])

    summary = {
        name: {k: v for k, v in res.items() if k not in ("X", "y", "groups", "train_mask", "val_mask", "test_mask")}
        for name, res in results.items()
    }
    summary["unified"] = unified_summary

    os.makedirs(paths["output"]["reports_dir"], exist_ok=True)
    with open(os.path.join(paths["output"]["reports_dir"], "unified_dataset_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=str)

    logger.info("Done. Summary written to reports/unified_dataset_summary.json")


if __name__ == "__main__":
    main()
