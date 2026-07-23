import os
import json
import numpy as np

"""
One-off enrichment step: the main unified-dataset build (build_unified_bearing_dataset.py)
does not persist per-window group ids (source recording) in the unified npz, only the
per-dataset name. Sequence models need group ids to avoid stitching windows from
different recordings together. Since group assignment to train/val/test is deterministic
and order-preserving, we can reconstruct group_train/group_val/group_test directly from
the already-saved per-dataset {name}_groups.npy + {name}_split.npz without recomputing
any features.
"""

DATASETS = ["nasa_ims", "cwru", "paderborn"]


def main():
    with open(os.path.join("configs", "dataset_paths.json"), "r", encoding="utf-8") as f:
        paths = json.load(f)

    windows_dir = paths["output"]["windows_dir"]
    splits_dir = paths["output"]["splits_dir"]
    unified_dir = paths["output"]["unified_dir"]

    group_train_parts, group_val_parts, group_test_parts = [], [], []
    y_check_train, y_check_val, y_check_test = [], [], []

    for name in DATASETS:
        groups = np.load(os.path.join(windows_dir, f"{name}_groups.npy"), allow_pickle=True)
        labels = np.load(os.path.join(windows_dir, f"{name}_labels.npy"))
        split = np.load(os.path.join(splits_dir, f"{name}_split.npz"))
        train_mask, val_mask, test_mask = split["train_mask"], split["val_mask"], split["test_mask"]

        group_train_parts.append(groups[train_mask])
        group_val_parts.append(groups[val_mask])
        group_test_parts.append(groups[test_mask])
        y_check_train.append(labels[train_mask])
        y_check_val.append(labels[val_mask])
        y_check_test.append(labels[test_mask])

    group_train = np.concatenate(group_train_parts)
    group_val = np.concatenate(group_val_parts)
    group_test = np.concatenate(group_test_parts)

    unified_path = os.path.join(unified_dir, "unified_bearing_dataset.npz")
    existing = dict(np.load(unified_path, allow_pickle=True))

    # Sanity check: reconstructed label order must match what's already stored.
    assert np.array_equal(existing["y_train"], np.concatenate(y_check_train)), "train label order mismatch"
    assert np.array_equal(existing["y_val"], np.concatenate(y_check_val)), "val label order mismatch"
    assert np.array_equal(existing["y_test"], np.concatenate(y_check_test)), "test label order mismatch"

    existing["group_train"] = group_train
    existing["group_val"] = group_val
    existing["group_test"] = group_test
    np.savez(unified_path, **existing)
    print(f"Added group_train ({len(group_train)}), group_val ({len(group_val)}), group_test ({len(group_test)}) to {unified_path}")


if __name__ == "__main__":
    main()
