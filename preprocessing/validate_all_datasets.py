import os
import sys
import json
import logging
import numpy as np

sys.path.insert(0, os.path.abspath("."))

from utils.schema import validate_input_record, CANONICAL_FEATURE_KEYS, GROUND_TRUTH_ENUM, SOURCE_ENUM
from preprocessing.schema_adapter import ALL_SOURCES

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

"""
Fails fast if any of the 6 standardized datasets are broken. Checks, per
the project's DATA VALIDATION requirements:
  - folder structure / file integrity (files exist, non-empty, parse as JSON)
  - schema compatibility (every record validated against
    backend/schemas/sensor_input.json via utils.schema.validate_input_record)
  - label mapping (ground_truth in the shared enum)
  - feature consistency (every CANONICAL_FEATURE_KEYS key present, no NaN/Inf)
  - missing values
  - timestamp ordering + sequence continuity (non-decreasing timestamps within
    a sequence_id)
  - leakage between train/val/test (index-set intersection check on the
    split masks in data/bearing_splits/*.npz, shared by all 6 sources)

Exits non-zero (and prints every error found) on any failure -- this is
meant to be run in CI/pre-training, not just informationally.
"""


def check_source(source: str, out_dir: str) -> list:
    errors = []
    path = os.path.join(out_dir, f"{source}_standardized.jsonl")

    if not os.path.exists(path):
        return [f"[{source}] missing standardized file: {path}"]
    if os.path.getsize(path) == 0:
        return [f"[{source}] standardized file is empty: {path}"]

    records = []
    with open(path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError as e:
                errors.append(f"[{source}] line {i}: invalid JSON: {e}")
                continue
            records.append(rec)

    if not records:
        errors.append(f"[{source}] no records parsed from {path}")
        return errors

    # Schema compatibility + label mapping + feature consistency + missing values
    last_ts_by_seq = {}
    for i, rec in enumerate(records):
        schema_err = validate_input_record(rec)
        if schema_err:
            errors.append(f"[{source}] line {i}: schema violation: {schema_err}")
            continue  # further checks assume a schema-valid shape

        if rec["source"] != source:
            errors.append(f"[{source}] line {i}: source field mismatch ('{rec['source']}')")
        if rec["ground_truth"] not in GROUND_TRUTH_ENUM:
            errors.append(f"[{source}] line {i}: invalid ground_truth '{rec['ground_truth']}'")

        missing_keys = set(CANONICAL_FEATURE_KEYS) - set(rec["features"].keys())
        if missing_keys:
            errors.append(f"[{source}] line {i}: features missing keys {missing_keys}")
        for k, v in rec["features"].items():
            if v is None or (isinstance(v, float) and (np.isnan(v) or np.isinf(v))):
                errors.append(f"[{source}] line {i}: feature '{k}' is NaN/Inf/None")

        # Timestamp ordering + sequence continuity within each sequence_id
        seq_id = rec["sequence_id"]
        ts = rec["timestamp"]
        if seq_id in last_ts_by_seq and ts < last_ts_by_seq[seq_id]:
            errors.append(f"[{source}] line {i}: timestamp out of order within sequence '{seq_id}'")
        last_ts_by_seq[seq_id] = ts

    logger.info("[%s] validated %d records (%d errors so far)", source, len(records), len(errors))
    return errors


def check_split_leakage(source: str, splits_dir: str) -> list:
    errors = []
    split_path = os.path.join(splits_dir, f"{source}_split.npz")
    if not os.path.exists(split_path):
        return [f"[{source}] missing split file: {split_path}"]

    split = np.load(split_path)
    train_idx = set(np.flatnonzero(split["train_mask"]).tolist())
    val_idx = set(np.flatnonzero(split["val_mask"]).tolist())
    test_idx = set(np.flatnonzero(split["test_mask"]).tolist())

    if train_idx & val_idx:
        errors.append(f"[{source}] train/val split overlap: {len(train_idx & val_idx)} shared indices")
    if train_idx & test_idx:
        errors.append(f"[{source}] train/test split overlap: {len(train_idx & test_idx)} shared indices")
    if val_idx & test_idx:
        errors.append(f"[{source}] val/test split overlap: {len(val_idx & test_idx)} shared indices")

    return errors


def main():
    out_dir = os.path.join("data", "unified_schema")
    splits_dir = os.path.join("data", "bearing_splits")

    all_errors = []
    per_source_status = {}

    for source in ALL_SOURCES:
        source_errors = check_source(source, out_dir)
        source_errors += check_split_leakage(source, splits_dir)
        all_errors.extend(source_errors)
        per_source_status[source] = "FAIL" if source_errors else "PASS"

    report_lines = ["# Preprocessing Validation Report", ""]
    report_lines.append("| Source | Status |")
    report_lines.append("|---|---|")
    for source, status in per_source_status.items():
        report_lines.append(f"| {source} | {status} |")
    report_lines.append("")

    if all_errors:
        report_lines.append(f"## {len(all_errors)} error(s) found")
        for e in all_errors:
            report_lines.append(f"- {e}")
    else:
        report_lines.append("All 6 datasets passed validation: schema-compatible, no NaN/Inf features, "
                              "no train/val/test split leakage, timestamps ordered within each sequence.")

    report = "\n".join(report_lines)
    os.makedirs("reports", exist_ok=True)
    with open(os.path.join("reports", "preprocessing_validation_report.md"), "w", encoding="utf-8") as f:
        f.write(report)

    print(report)
    if all_errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
