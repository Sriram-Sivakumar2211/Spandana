import os
import re
import glob
import logging
import numpy as np
import pandas as pd

from preprocessing.bearing_common import clean_signal

logger = logging.getLogger(__name__)

_TIMESTAMP_RE = re.compile(r"^\d{4}\.\d{2}\.\d{2}\.\d{2}\.\d{2}\.\d{2}$")

# NASA IMS bearing test-rig documentation (Qiu et al. 2006 / the dataset's
# own Readme, widely cited): each run recorded 4 bearings until one of them
# failed. The failing bearing/channel and the fault type it eventually
# exhibited are known from the post-mortem teardown notes; every other
# channel in that same run stayed healthy for the run's duration. There is
# no ground-truth failure timestamp, so channel health is a heuristic
# derived below from the RMS trend, not a certified label.
_TEST_CONFIG = {
    "1st_test": {
        "n_channels": 8,
        # column_index -> (bearing_id, is_failing_channel, eventual_fault_type)
        "channels": {
            0: ("bearing1_ch1", False, None),
            1: ("bearing1_ch2", False, None),
            2: ("bearing2_ch1", False, None),
            3: ("bearing2_ch2", False, None),
            4: ("bearing3_ch1", True, "inner_race"),
            5: ("bearing3_ch2", True, "inner_race"),
            6: ("bearing4_ch1", True, "ball"),
            7: ("bearing4_ch2", True, "ball"),
        },
    },
    "2nd_test": {
        "n_channels": 4,
        "channels": {
            0: ("bearing1", True, "outer_race"),
            1: ("bearing2", False, None),
            2: ("bearing3", False, None),
            3: ("bearing4", False, None),
        },
    },
    "3rd_test": {
        "n_channels": 4,
        "channels": {
            0: ("bearing1", False, None),
            1: ("bearing2", False, None),
            2: ("bearing3", True, "outer_race"),
            3: ("bearing4", False, None),
        },
    },
}


class NASAIMSPreprocessor:
    """
    Preprocessor for the NASA IMS run-to-failure bearing dataset. Unlike
    CWRU/Paderborn, IMS ships with no per-file fault label -- only the fact
    that one bearing per run eventually failed. Health state is therefore
    inferred from the RMS trend of the documented failing channel relative
    to its own early-life baseline (`onset_factor` sigma above baseline
    marks the onset of the fault; everything before that is "healthy",
    everything after is labeled with the run's documented eventual fault
    type). Non-failing channels in the same run are always "healthy".
    """

    def __init__(self, raw_dir: str = None, sample_rate_hz: float = 20000.0, onset_factor: float = 3.0, baseline_fraction: float = 0.10):
        if raw_dir is None:
            raw_dir = os.path.join("data", "raw", "nasa_ims")
        self.raw_dir = raw_dir
        self.sample_rate_hz = sample_rate_hz
        self.onset_factor = onset_factor
        self.baseline_fraction = baseline_fraction

    def _find_snapshot_dir(self, test_name: str) -> str:
        """
        Handles the dataset's inconsistent nesting across mirrors, e.g.
        '<raw_dir>/1st_test/1st_test/<snapshot files>' or
        '<raw_dir>/3rd_test/4th_test/txt/<snapshot files>'. Searches
        recursively for the deepest directory whose files match the
        'YYYY.MM.DD.HH.MM.SS' snapshot naming convention.
        """
        test_root = os.path.join(self.raw_dir, test_name)
        if not os.path.isdir(test_root):
            raise FileNotFoundError(f"NASA IMS test folder not found: {test_root}")

        for dirpath, _dirnames, filenames in os.walk(test_root):
            snapshot_files = [f for f in filenames if _TIMESTAMP_RE.match(f)]
            if snapshot_files:
                return dirpath
        raise FileNotFoundError(f"No snapshot files found under {test_root}")

    def _list_snapshot_files(self, test_name: str, max_files: int = None) -> list:
        snap_dir = self._find_snapshot_dir(test_name)
        files = sorted(f for f in os.listdir(snap_dir) if _TIMESTAMP_RE.match(f))
        if max_files:
            # Evenly subsample across the whole run so early/mid/late life are all represented.
            idx = np.linspace(0, len(files) - 1, max_files).astype(int)
            files = [files[i] for i in sorted(set(idx))]
        return [os.path.join(snap_dir, f) for f in files]

    def _read_snapshot(self, path: str, n_channels: int) -> np.ndarray:
        df = pd.read_csv(path, sep="\t", header=None, dtype=np.float32)
        arr = df.values
        if arr.shape[1] != n_channels:
            raise ValueError(f"Expected {n_channels} channels in {path}, found {arr.shape[1]}")
        return arr

    def load_run(self, test_name: str, max_files: int = None) -> list:
        """
        Loads one run (e.g. '1st_test') and returns per-channel records:
        [{signal, fs, bearing_class, source_file, bearing_id, test_name, snapshot_index}]
        """
        if test_name not in _TEST_CONFIG:
            raise ValueError(f"Unknown NASA IMS test name '{test_name}'. Expected one of {list(_TEST_CONFIG)}")
        cfg = _TEST_CONFIG[test_name]

        paths = self._list_snapshot_files(test_name, max_files=max_files)
        n_snapshots = len(paths)
        if n_snapshots == 0:
            raise RuntimeError(f"No snapshots found for {test_name}")

        # Pass 1: compute per-channel RMS trend across the whole (subsampled) run.
        rms_trend = np.zeros((n_snapshots, cfg["n_channels"]), dtype=np.float64)
        raw_signals = []
        for i, p in enumerate(paths):
            arr = self._read_snapshot(p, cfg["n_channels"])
            raw_signals.append(arr)
            rms_trend[i] = np.sqrt(np.mean(arr.astype(np.float64) ** 2, axis=0))

        baseline_n = max(1, int(n_snapshots * self.baseline_fraction))
        baseline_rms = rms_trend[:baseline_n].mean(axis=0)

        records = []
        for col_idx, (bearing_id, is_failing, fault_type) in cfg["channels"].items():
            threshold = baseline_rms[col_idx] * self.onset_factor
            for i, p in enumerate(paths):
                signal = clean_signal(raw_signals[i][:, col_idx])
                if is_failing and rms_trend[i, col_idx] > threshold:
                    bearing_class = fault_type
                else:
                    bearing_class = "healthy"

                records.append({
                    "signal": signal,
                    "fs": self.sample_rate_hz,
                    "bearing_class": bearing_class,
                    "source_file": f"{test_name}/{bearing_id}/{os.path.basename(p)}",
                    "bearing_id": bearing_id,
                    "test_name": test_name,
                    "snapshot_index": i,
                })

        logger.info(
            "Loaded %s: %d snapshots x %d channels = %d records",
            test_name, n_snapshots, cfg["n_channels"], len(records),
        )
        return records

    def load_all(self, tests: list = None, max_files_per_test: int = None) -> list:
        tests = tests or list(_TEST_CONFIG.keys())
        all_records = []
        for t in tests:
            try:
                all_records.extend(self.load_run(t, max_files=max_files_per_test))
            except FileNotFoundError as e:
                logger.warning("Skipping %s: %s", t, e)
        if not all_records:
            raise RuntimeError(f"No NASA IMS records could be loaded from {self.raw_dir}")
        return all_records


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    prep = NASAIMSPreprocessor(raw_dir="C:/Users/MG-Laptop/OneDrive/Data/Hackathons/LNN/Datasets/Nasa IMS dataset")
    recs = prep.load_run("1st_test", max_files=50)
    print(f"Loaded {len(recs)} records from a 50-snapshot subsample of 1st_test.")
    classes = {}
    for r in recs:
        classes[r["bearing_class"]] = classes.get(r["bearing_class"], 0) + 1
    print("Class distribution:", classes)
