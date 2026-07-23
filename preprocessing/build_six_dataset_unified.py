import os
import sys
import json
import logging
import numpy as np

sys.path.insert(0, os.path.abspath("."))

from utils.schema import CANONICAL_FEATURE_KEYS, GROUND_TRUTH_ENUM, encode_ground_truth
from preprocessing.schema_adapter import ALL_SOURCES
from preprocessing.bearing_common import SignalScaler

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

"""
Builds the combined 6-dataset training table for the general Spandana LTC:
X in the 23-dim CANONICAL_FEATURE_KEYS space (zero-filled per source where a
feature isn't applicable), y = ground_truth (healthy/warning/faulty -- the
one label space all 6 datasets can genuinely express; see
preprocessing/schema_adapter.py for why the bearing-specific fault-location
label is a separate, finer-grained task, not merged in here), groups =
sequence_id.

Reuses the split masks already computed by preprocessing/build_unified_bearing_dataset.py
(group-aware, 3 bearing datasets) and preprocessing/build_member1_splits.py
(chronological, 3 Member 1 datasets) rather than re-splitting -- this
preserves each source's existing leakage-avoidance strategy instead of
picking a new one that might not fit every dataset's available metadata.
"""


def load_standardized(source: str) -> list:
    path = os.path.join("data", "unified_schema", f"{source}_standardized.jsonl")
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def records_to_arrays(records: list):
    X = np.array([[r["features"][k] for k in CANONICAL_FEATURE_KEYS] for r in records], dtype=np.float32)
    y = np.array([encode_ground_truth(r["ground_truth"]) for r in records], dtype=np.int64)
    groups = np.array([r["sequence_id"] for r in records])
    return X, y, groups


def main():
    splits_dir = os.path.join("data", "bearing_splits")
    out_dir = os.path.join("data", "unified_schema")

    X_train_parts, y_train_parts, g_train_parts, src_train_parts = [], [], [], []
    X_val_parts, y_val_parts, g_val_parts, src_val_parts = [], [], [], []
    X_test_parts, y_test_parts, g_test_parts, src_test_parts = [], [], [], []

    per_source_counts = {}
    for source in ALL_SOURCES:
        records = load_standardized(source)
        X, y, groups = records_to_arrays(records)

        split = np.load(os.path.join(splits_dir, f"{source}_split.npz"))
        train_mask, val_mask, test_mask = split["train_mask"], split["val_mask"], split["test_mask"]
        if len(train_mask) != len(X):
            raise RuntimeError(
                f"{source}: split mask length {len(train_mask)} != standardized record count {len(X)} "
                "-- split was computed against a different window ordering."
            )

        X_train_parts.append(X[train_mask]); y_train_parts.append(y[train_mask]); g_train_parts.append(groups[train_mask])
        src_train_parts.append(np.full(train_mask.sum(), source))
        X_val_parts.append(X[val_mask]); y_val_parts.append(y[val_mask]); g_val_parts.append(groups[val_mask])
        src_val_parts.append(np.full(val_mask.sum(), source))
        X_test_parts.append(X[test_mask]); y_test_parts.append(y[test_mask]); g_test_parts.append(groups[test_mask])
        src_test_parts.append(np.full(test_mask.sum(), source))

        per_source_counts[source] = {"train": int(train_mask.sum()), "val": int(val_mask.sum()), "test": int(test_mask.sum())}
        logger.info("%s: %s", source, per_source_counts[source])

    X_train = np.concatenate(X_train_parts); y_train = np.concatenate(y_train_parts)
    g_train = np.concatenate(g_train_parts); src_train = np.concatenate(src_train_parts)
    X_val = np.concatenate(X_val_parts); y_val = np.concatenate(y_val_parts)
    g_val = np.concatenate(g_val_parts); src_val = np.concatenate(src_val_parts)
    X_test = np.concatenate(X_test_parts); y_test = np.concatenate(y_test_parts)
    g_test = np.concatenate(g_test_parts); src_test = np.concatenate(src_test_parts)

    scaler = SignalScaler().fit(X_train)
    X_train_s = scaler.transform(X_train)
    X_val_s = scaler.transform(X_val)
    X_test_s = scaler.transform(X_test)

    np.savez(
        os.path.join(out_dir, "six_dataset_unified.npz"),
        X_train=X_train_s, y_train=y_train, group_train=g_train, src_train=src_train,
        X_val=X_val_s, y_val=y_val, group_val=g_val, src_val=src_val,
        X_test=X_test_s, y_test=y_test, group_test=g_test, src_test=src_test,
    )
    with open(os.path.join(out_dir, "feature_scaler.json"), "w", encoding="utf-8") as f:
        json.dump(scaler.to_dict(), f, indent=2)
    with open(os.path.join(out_dir, "feature_schema.json"), "w", encoding="utf-8") as f:
        json.dump({"feature_keys": CANONICAL_FEATURE_KEYS, "classes": GROUND_TRUTH_ENUM}, f, indent=2)

    class_counts = {c: int(np.sum(y_train == encode_ground_truth(c))) for c in GROUND_TRUTH_ENUM}
    logger.info(
        "Six-dataset unified: train=%d val=%d test=%d, feature_dim=%d, train class distribution=%s",
        len(y_train), len(y_val), len(y_test), X_train.shape[1], class_counts,
    )

    summary = {"per_source": per_source_counts, "n_train": len(y_train), "n_val": len(y_val), "n_test": len(y_test),
               "feature_dim": int(X_train.shape[1]), "train_class_distribution": class_counts}
    with open(os.path.join("reports", "six_dataset_unified_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
