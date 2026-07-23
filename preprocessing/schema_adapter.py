import os
import sys
import json
import logging
from datetime import datetime

sys.path.insert(0, os.path.abspath("."))

from utils.schema import fill_feature_vector, bearing_class_to_ground_truth
from preprocessing.bearing_common import BEARING_CLASSES

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

"""
Standardizes the window records ALREADY produced by both tracks' existing
preprocessing (Member 1's data/windows/*_windows.jsonl, Member 2's
data/bearing_windows/*_windows.jsonl) into the schema defined by
backend/schemas/sensor_input.json. This reads already-computed features --
it does not re-run any raw-signal preprocessing, per the "do not create a
second data pipeline" constraint.

Known simplifications (disclosed, not hidden):
  - `operating_mode` defaults to "normal" for every record: none of the 6
    datasets currently carry an operating-condition signal in their
    exported windows, so anything more specific would be fabricated.
  - `sequence_id` for the 3 Member 1 datasets is one id per whole dataset
    ("<source>_stream"), because their exported records don't carry a
    per-recording/per-experiment id (only the 3 bearing datasets do, via
    `group_id`). This is a ceiling imposed by what Member 1's pipeline
    already exports, not something this adapter re-derives from raw data.
  - `ground_truth` for the 3 bearing datasets is coarsened to healthy/faulty
    (no "warning" tier yet) -- their specific fault-location label (e.g.
    "inner_race") is preserved as the actual model training target
    elsewhere, not lost, just not expressed in this 3-tier field.
"""

_MEMBER1_WINDOW_CFG = {
    "metropt3": {"window_size": 60, "step": 10, "sampling_rate_hz": 1.0},
    "thermal_motor": {"window_size": 10, "step": 5, "sampling_rate_hz": 1.0},
    "squirrel_cage": {"window_size": 10, "step": 5, "sampling_rate_hz": 1.0},
}

MEMBER1_SOURCES = list(_MEMBER1_WINDOW_CFG.keys())
BEARING_SOURCES = ["nasa_ims", "cwru", "paderborn"]
ALL_SOURCES = MEMBER1_SOURCES + BEARING_SOURCES


def _parse_ts(ts_str: str) -> datetime:
    return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))


def _bearing_window_cfg(pcfg: dict, source: str) -> dict:
    c = pcfg[source]
    return {"window_size": c["window_size"], "step": c["step"]}


def standardize_member1_records(source: str, raw_records: list, sampling_rate_hz: float,
                                 window_size: int, step: int) -> list:
    overlap = window_size - step
    sequence_id = f"{source}_stream"
    nominal_delta_ms = (step / sampling_rate_hz) * 1000.0

    standardized = []
    prev_ts = None
    for rec in raw_records:
        ts = _parse_ts(rec["timestamp"])
        delta_ms = nominal_delta_ms if prev_ts is None else max((ts - prev_ts).total_seconds() * 1000.0, 0.0)
        prev_ts = ts

        standardized.append({
            "machine_id": rec["machine_id"],
            "sequence_id": sequence_id,
            "window_id": rec["window_id"],
            "timestamp": rec["timestamp"],
            "delta_time_ms": round(delta_ms, 2),
            "source": source,
            "operating_mode": "normal",
            "sampling_rate_hz": sampling_rate_hz,
            "window_size": window_size,
            "overlap": overlap,
            "features": fill_feature_vector(rec["features"]),
            "ground_truth": rec["label"],  # already healthy/warning/faulty
        })
    return standardized


def standardize_bearing_records(source: str, raw_records: list, sampling_rate_hz: float,
                                 window_size: int, step: int) -> list:
    overlap = window_size - step
    nominal_delta_ms = (step / sampling_rate_hz) * 1000.0

    last_ts_per_group = {}
    standardized = []
    for rec in raw_records:
        group_id = rec["group_id"]
        ts = _parse_ts(rec["timestamp"])
        prev_ts = last_ts_per_group.get(group_id)
        delta_ms = nominal_delta_ms if prev_ts is None else max((ts - prev_ts).total_seconds() * 1000.0, 0.0)
        last_ts_per_group[group_id] = ts

        standardized.append({
            "machine_id": rec["machine_id"],
            "sequence_id": group_id,
            "window_id": rec["window_id"],
            "timestamp": rec["timestamp"],
            "delta_time_ms": round(delta_ms, 2),
            "source": source,
            "operating_mode": "normal",
            "sampling_rate_hz": sampling_rate_hz,
            "window_size": window_size,
            "overlap": overlap,
            "features": fill_feature_vector(rec["features"]),
            "ground_truth": bearing_class_to_ground_truth(rec["label"]),
        })
    return standardized


def load_jsonl(path: str) -> list:
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def main():
    with open(os.path.join("configs", "dataset_paths.json"), "r", encoding="utf-8") as f:
        paths_cfg = json.load(f)
    with open(os.path.join("configs", "preprocessing_config.json"), "r", encoding="utf-8") as f:
        pcfg = json.load(f)

    out_dir = os.path.join("data", "unified_schema")
    os.makedirs(out_dir, exist_ok=True)

    all_standardized = []
    per_source_counts = {}

    for source, cfg in _MEMBER1_WINDOW_CFG.items():
        path = os.path.join("data", "windows", f"{source}_windows.jsonl")
        if not os.path.exists(path):
            logger.warning("Member 1 source %s not found at %s, skipping", source, path)
            continue
        raw = load_jsonl(path)
        standardized = standardize_member1_records(source, raw, cfg["sampling_rate_hz"], cfg["window_size"], cfg["step"])
        all_standardized.extend(standardized)
        per_source_counts[source] = len(standardized)
        logger.info("%s: standardized %d records", source, len(standardized))

    for source in BEARING_SOURCES:
        path = os.path.join("data", "bearing_windows", f"{source}_windows.jsonl")
        if not os.path.exists(path):
            logger.warning("Bearing source %s not found at %s, skipping", source, path)
            continue
        raw = load_jsonl(path)
        bcfg = _bearing_window_cfg(pcfg, source)
        sampling_rate_hz = paths_cfg[source]["sample_rate_hz"]
        standardized = standardize_bearing_records(source, raw, sampling_rate_hz, bcfg["window_size"], bcfg["step"])
        all_standardized.extend(standardized)
        per_source_counts[source] = len(standardized)
        logger.info("%s: standardized %d records", source, len(standardized))

    for source in ALL_SOURCES:
        source_records = [r for r in all_standardized if r["source"] == source]
        if not source_records:
            continue
        with open(os.path.join(out_dir, f"{source}_standardized.jsonl"), "w", encoding="utf-8") as f:
            for r in source_records:
                f.write(json.dumps(r) + "\n")

    with open(os.path.join(out_dir, "all_sources_standardized.jsonl"), "w", encoding="utf-8") as f:
        for r in all_standardized:
            f.write(json.dumps(r) + "\n")

    logger.info("Standardized %d total records across %d sources: %s", len(all_standardized), len(per_source_counts), per_source_counts)


if __name__ == "__main__":
    main()
