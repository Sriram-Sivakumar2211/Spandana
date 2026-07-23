import os
import re
import json
import glob
import logging
import numpy as np
from scipy.io import loadmat

from preprocessing.bearing_common import clean_signal

logger = logging.getLogger(__name__)

# "N09_M07_F10_K001_1.mat" -> operating condition (speed/load/radial force) +
# bearing code (K001) + run/repetition number (1).
_FNAME_RE = re.compile(
    r"^(?P<speed>N\d+)_(?P<load>M\d+)_(?P<force>F\d+)_(?P<code>[A-Z]{1,2}\d{2,3})_(?P<run>\d+)\.mat$",
    re.IGNORECASE,
)

_DEFAULT_CODE_TABLE_PATH = os.path.join("configs", "paderborn_bearing_codes.json")


class PaderbornPreprocessor:
    """
    Preprocessor for the Paderborn University (KAt-DataCenter) bearing
    dataset. Bearing health state is looked up from the bearing-code
    reference table (configs/paderborn_bearing_codes.json) rather than
    hardcoded, since the mapping is documentation-derived and may need
    correction/extension by domain experts.
    """

    def __init__(self, raw_dir: str = None, sample_rate_hz: float = 64000.0, code_table_path: str = None):
        if raw_dir is None:
            raw_dir = os.path.join("data", "raw", "paderborn")
        self.raw_dir = raw_dir
        self.sample_rate_hz = sample_rate_hz

        code_table_path = code_table_path or _DEFAULT_CODE_TABLE_PATH
        with open(code_table_path, "r", encoding="utf-8") as f:
            self.code_table = json.load(f)

    def parse_filename(self, filename: str) -> dict:
        base = os.path.basename(filename)
        m = _FNAME_RE.match(base)
        if not m:
            logger.warning("Paderborn filename did not match expected pattern, skipping: %s", base)
            return None
        return {
            "file_name": base,
            "speed_code": m.group("speed"),
            "load_code": m.group("load"),
            "force_code": m.group("force"),
            "bearing_code": m.group("code").upper(),
            "run": m.group("run"),
        }

    def _bearing_class(self, bearing_code: str) -> str:
        entry = self.code_table.get(bearing_code)
        if entry is None:
            logger.warning("Bearing code '%s' missing from code table, treating as unknown/healthy", bearing_code)
            return "healthy"
        return entry["damage_type"]

    def _extract_vibration_channel(self, mat_path: str) -> np.ndarray:
        mat = loadmat(mat_path, struct_as_record=False, squeeze_me=True)
        top_keys = [k for k in mat.keys() if not k.startswith("__")]
        if not top_keys:
            raise ValueError(f"No top-level MATLAB struct found in {mat_path}")

        top_struct = mat[top_keys[0]]
        y_field = getattr(top_struct, "Y", None)
        if y_field is None:
            raise ValueError(f"Expected field 'Y' not found in struct of {mat_path}")

        channels = y_field if isinstance(y_field, np.ndarray) else [y_field]
        for ch in channels:
            name = str(getattr(ch, "Name", "")).lower()
            if "vibration" in name:
                return np.asarray(getattr(ch, "Data")).ravel()

        raise ValueError(f"No 'vibration' channel found among Y fields in {mat_path}")

    def load_all(self, bearing_codes: list = None, max_files_per_code: int = None) -> list:
        """
        Loads Paderborn .mat recordings, restricted to `bearing_codes` if
        given (else every code present in raw_dir), capped at
        `max_files_per_code` runs per bearing code to bound runtime on the
        full ~2600-file dataset.
        """
        if not os.path.exists(self.raw_dir):
            raise FileNotFoundError(f"Paderborn raw directory not found: {self.raw_dir}")

        code_dirs = sorted(
            d for d in os.listdir(self.raw_dir)
            if os.path.isdir(os.path.join(self.raw_dir, d))
        )
        if bearing_codes:
            code_dirs = [d for d in code_dirs if d in bearing_codes]

        records = []
        for code_dir in code_dirs:
            mat_paths = sorted(glob.glob(os.path.join(self.raw_dir, code_dir, "*.mat")))
            if max_files_per_code:
                mat_paths = mat_paths[:max_files_per_code]

            for p in mat_paths:
                meta = self.parse_filename(p)
                if meta is None:
                    continue
                try:
                    signal = self._extract_vibration_channel(p)
                except ValueError as e:
                    logger.warning("Skipping %s: %s", p, e)
                    continue

                signal = clean_signal(signal)
                records.append({
                    "signal": signal,
                    "fs": self.sample_rate_hz,
                    "bearing_class": self._bearing_class(meta["bearing_code"]),
                    "source_file": meta["file_name"],
                    "bearing_code": meta["bearing_code"],
                    "operating_condition": f"{meta['speed_code']}_{meta['load_code']}_{meta['force_code']}",
                })
                logger.info(
                    "Loaded %s: %d samples, code=%s, class=%s",
                    meta["file_name"], len(signal), meta["bearing_code"], records[-1]["bearing_class"],
                )

        if not records:
            raise RuntimeError(f"No Paderborn .mat files could be parsed from {self.raw_dir}")
        return records


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    prep = PaderbornPreprocessor(raw_dir="C:/Users/MG-Laptop/OneDrive/Data/Hackathons/LNN/Datasets/Paderboen bearing dataset")
    recs = prep.load_all(bearing_codes=["K001", "KA04", "KI04"], max_files_per_code=2)
    print(f"Loaded {len(recs)} Paderborn raw recordings.")
    for r in recs:
        print(f"  {r['source_file']}: class={r['bearing_class']}, len={len(r['signal'])}")
