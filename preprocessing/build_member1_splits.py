import os
import json
import logging
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

"""
Member 1's exported windows (data/windows/*_features.npy) carry no
per-recording/per-experiment group id (see preprocessing/schema_adapter.py's
docstring), so the group-aware split used for the 3 bearing datasets
(preprocessing/bearing_common.py::group_aware_split) cannot be applied here
-- there is only one group per whole dataset, which a group-based splitter
cannot subdivide.

Instead this uses a CHRONOLOGICAL split (train = earliest 70% of windows in
export order, val = next 15%, test = last 15%, no shuffling): it does not
prevent every possible leakage (windows immediately adjacent to a split
boundary can share a few raw samples due to the sliding-window overlap
Member 1's pipeline already used), but it does guarantee test windows never
appear earlier in time than train windows, which a random shuffle would not.
This is disclosed here and in the validation report, not hidden.
"""

SOURCES = ["metropt3", "thermal_motor", "squirrel_cage"]


def chronological_split(n: int, val_size: float = 0.15, test_size: float = 0.15):
    train_end = int(n * (1 - val_size - test_size))
    val_end = int(n * (1 - test_size))
    train_mask = np.zeros(n, dtype=bool)
    val_mask = np.zeros(n, dtype=bool)
    test_mask = np.zeros(n, dtype=bool)
    train_mask[:train_end] = True
    val_mask[train_end:val_end] = True
    test_mask[val_end:] = True
    return train_mask, val_mask, test_mask


def main():
    windows_dir = os.path.join("data", "windows")
    splits_dir = os.path.join("data", "bearing_splits")  # shared splits directory across all 6 sources
    os.makedirs(splits_dir, exist_ok=True)

    summary = {}
    for source in SOURCES:
        labels_path = os.path.join(windows_dir, f"{source}_labels.npy")
        if not os.path.exists(labels_path):
            logger.warning("Skipping %s: %s not found", source, labels_path)
            continue

        y = np.load(labels_path, allow_pickle=True)
        n = len(y)
        train_mask, val_mask, test_mask = chronological_split(n)

        np.savez(
            os.path.join(splits_dir, f"{source}_split.npz"),
            train_mask=train_mask, val_mask=val_mask, test_mask=test_mask,
        )
        summary[source] = {"n_total": int(n), "n_train": int(train_mask.sum()), "n_val": int(val_mask.sum()), "n_test": int(test_mask.sum())}
        logger.info("%s: %s", source, summary[source])

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
