import os
import re
import glob
import logging
import numpy as np
from scipy.io import loadmat

from preprocessing.bearing_common import clean_signal

logger = logging.getLogger(__name__)

# CWRU filename convention observed in this project's raw folder, e.g.
# "IR014_1_175.mat" -> fault=IR, size=014 (thousandths-inch defect diameter), load=1hp, file_id=175
# "OR007_6_1_136.mat" -> fault=OR, size=007, clock position=6, load=1hp, file_id=136
# "Time_Normal_1_098.mat" -> healthy baseline recording, load=1hp, file_id=098
_FNAME_RE = re.compile(
    r"^(?P<fault>Time_Normal|B|IR|OR)(?P<size>\d{3})?_(?:(?P<pos>\d+)_)?(?P<load>\d+)_(?P<file_id>\d+)\.mat$",
    re.IGNORECASE,
)

_FAULT_TO_BEARING_CLASS = {
    "B": "ball",
    "IR": "inner_race",
    "OR": "outer_race",
    "TIME_NORMAL": "healthy",
}


class CWRUPreprocessor:
    """
    Preprocessor for the Case Western Reserve University (CWRU) Bearing
    Data Center dataset. Parses fault type / defect diameter / motor load
    directly from the raw .mat filenames and extracts the drive-end (DE)
    vibration channel (falls back to fan-end/FE or base/BA if DE missing).
    """

    def __init__(self, raw_dir: str = None, sample_rate_hz: float = 48000.0):
        if raw_dir is None:
            raw_dir = os.path.join("data", "raw", "cwru", "raw")
        self.raw_dir = raw_dir
        self.sample_rate_hz = sample_rate_hz

    def parse_filename(self, filename: str) -> dict:
        base = os.path.basename(filename)
        m = _FNAME_RE.match(base)
        if not m:
            logger.warning("CWRU filename did not match expected pattern, skipping: %s", base)
            return None

        fault_raw = m.group("fault").upper()
        bearing_class = _FAULT_TO_BEARING_CLASS.get(fault_raw, "unknown")
        return {
            "file_name": base,
            "fault_code": fault_raw,
            "defect_size_mils": int(m.group("size")) if m.group("size") else 0,
            "motor_load_hp": int(m.group("load")),
            "file_id": m.group("file_id"),
            "bearing_class": bearing_class,
        }

    def _select_channel(self, mat_dict: dict) -> np.ndarray:
        """
        CWRU .mat files store channels under keys like 'X097_DE_time',
        'X097_FE_time', 'X097_BA_time', 'X097_RPM'. Preference order:
        drive-end (DE) > fan-end (FE) > base (BA), since DE is the standard
        channel used in the published CWRU fault-diagnosis literature.
        """
        keys = [k for k in mat_dict.keys() if not k.startswith("__")]
        for suffix in ("DE_time", "FE_time", "BA_time"):
            for k in keys:
                if k.endswith(suffix):
                    return np.asarray(mat_dict[k]).ravel()
        # Fallback: first numeric array-like key with more than a handful of samples
        for k in keys:
            arr = np.asarray(mat_dict[k])
            if arr.size > 100:
                return arr.ravel()
        raise ValueError(f"No usable vibration channel found among keys: {keys}")

    def load_all(self) -> list:
        """
        Loads every .mat file in raw_dir, returns a list of records:
        {signal, fs, bearing_class, source_file, motor_load_hp, defect_size_mils}
        """
        if not os.path.exists(self.raw_dir):
            raise FileNotFoundError(f"CWRU raw directory not found: {self.raw_dir}")

        mat_paths = sorted(glob.glob(os.path.join(self.raw_dir, "*.mat")))
        records = []
        for p in mat_paths:
            meta = self.parse_filename(p)
            if meta is None:
                continue
            mat = loadmat(p)
            try:
                signal = self._select_channel(mat)
            except ValueError as e:
                logger.warning("Skipping %s: %s", p, e)
                continue

            signal = clean_signal(signal)
            records.append({
                "signal": signal,
                "fs": self.sample_rate_hz,
                "bearing_class": meta["bearing_class"],
                "source_file": meta["file_name"],
                "motor_load_hp": meta["motor_load_hp"],
                "defect_size_mils": meta["defect_size_mils"],
            })
            logger.info("Loaded %s: %d samples, class=%s", meta["file_name"], len(signal), meta["bearing_class"])

        if not records:
            raise RuntimeError(f"No CWRU .mat files could be parsed from {self.raw_dir}")
        return records


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    prep = CWRUPreprocessor(raw_dir="C:/Users/MG-Laptop/OneDrive/Data/Hackathons/LNN/Datasets/CWRU bearing dataset/raw")
    recs = prep.load_all()
    print(f"Loaded {len(recs)} CWRU raw recordings.")
    for r in recs:
        print(f"  {r['source_file']}: class={r['bearing_class']}, len={len(r['signal'])}, load={r['motor_load_hp']}hp")
