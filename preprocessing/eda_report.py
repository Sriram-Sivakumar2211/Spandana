import os
import sys
import json
import glob
import logging
import numpy as np
import pandas as pd
from scipy.io import loadmat

sys.path.insert(0, os.path.abspath("."))

from preprocessing.nasa_ims_preprocess import NASAIMSPreprocessor, _TEST_CONFIG, _TIMESTAMP_RE
from preprocessing.cwru_preprocess import CWRUPreprocessor
from preprocessing.paderborn_preprocess import PaderbornPreprocessor

logging.basicConfig(level=logging.WARNING)


def inspect_nasa_ims(raw_dir: str) -> dict:
    prep = NASAIMSPreprocessor(raw_dir=raw_dir)
    summary = {"dataset": "NASA IMS Bearing Dataset", "raw_dir": raw_dir, "tests": {}}

    for test_name, cfg in _TEST_CONFIG.items():
        try:
            snap_dir = prep._find_snapshot_dir(test_name)
        except FileNotFoundError as e:
            summary["tests"][test_name] = {"error": str(e)}
            continue

        files = sorted(f for f in os.listdir(snap_dir) if _TIMESTAMP_RE.match(f))
        sample_path = os.path.join(snap_dir, files[0])
        sample_df = pd.read_csv(sample_path, sep="\t", header=None)
        n_missing = int(sample_df.isna().sum().sum())

        summary["tests"][test_name] = {
            "snapshot_dir": snap_dir,
            "n_snapshots": len(files),
            "n_channels": sample_df.shape[1],
            "expected_channels": cfg["n_channels"],
            "samples_per_snapshot": sample_df.shape[0],
            "sample_rate_hz": prep.sample_rate_hz,
            "snapshot_duration_sec": sample_df.shape[0] / prep.sample_rate_hz,
            "first_snapshot": files[0],
            "last_snapshot": files[-1],
            "missing_values_in_sample_file": n_missing,
            "documented_failing_channels": {
                bearing_id: fault_type
                for _idx, (bearing_id, is_failing, fault_type) in cfg["channels"].items()
                if is_failing
            },
            "labels": "No ground-truth per-file labels; run-to-failure only. Health state is derived via RMS-trend heuristic (see nasa_ims_preprocess.py).",
        }
    return summary


def inspect_cwru(raw_dir: str) -> dict:
    prep = CWRUPreprocessor(raw_dir=raw_dir)
    mat_paths = sorted(glob.glob(os.path.join(raw_dir, "*.mat")))
    file_infos = []
    fault_classes = {}
    missing_total = 0

    for p in mat_paths:
        meta = prep.parse_filename(p)
        if meta is None:
            continue
        mat = loadmat(p)
        channel_keys = [k for k in mat.keys() if not k.startswith("__")]
        try:
            signal = prep._select_channel(mat)
            n_missing = int(np.sum(~np.isfinite(signal)))
        except ValueError:
            signal = np.array([])
            n_missing = None
        missing_total += n_missing or 0

        fault_classes[meta["bearing_class"]] = fault_classes.get(meta["bearing_class"], 0) + 1
        file_infos.append({
            "file": meta["file_name"],
            "fault_code": meta["fault_code"],
            "defect_size_mils": meta["defect_size_mils"],
            "motor_load_hp": meta["motor_load_hp"],
            "bearing_class": meta["bearing_class"],
            "available_channel_keys": channel_keys,
            "n_samples": int(len(signal)),
        })

    return {
        "dataset": "CWRU Bearing Dataset",
        "raw_dir": raw_dir,
        "n_files": len(file_infos),
        "sample_rate_hz": prep.sample_rate_hz,
        "fault_class_distribution": fault_classes,
        "missing_values_total": missing_total,
        "files": file_infos,
    }


def inspect_paderborn(raw_dir: str, max_codes: int = None) -> dict:
    prep = PaderbornPreprocessor(raw_dir=raw_dir)
    code_dirs = sorted(d for d in os.listdir(raw_dir) if os.path.isdir(os.path.join(raw_dir, d)))
    if max_codes:
        code_dirs = code_dirs[:max_codes]

    fault_classes = {}
    damage_modes = {}
    n_files_total = 0
    sample_channel_names = None
    missing_total = 0

    for code_dir in code_dirs:
        mat_paths = sorted(glob.glob(os.path.join(raw_dir, code_dir, "*.mat")))
        n_files_total += len(mat_paths)
        bearing_class = prep._bearing_class(code_dir)
        entry = prep.code_table.get(code_dir, {})
        fault_classes[bearing_class] = fault_classes.get(bearing_class, 0) + len(mat_paths)
        damage_modes[entry.get("damage_mode", "unknown")] = damage_modes.get(entry.get("damage_mode", "unknown"), 0) + len(mat_paths)

        if sample_channel_names is None and mat_paths:
            mat = loadmat(mat_paths[0], struct_as_record=False, squeeze_me=True)
            top_keys = [k for k in mat.keys() if not k.startswith("__")]
            top_struct = mat[top_keys[0]]
            y_field = getattr(top_struct, "Y", None)
            channels = y_field if isinstance(y_field, np.ndarray) else [y_field]
            sample_channel_names = [str(getattr(ch, "Name", "?")) for ch in channels]
            try:
                sig = prep._extract_vibration_channel(mat_paths[0])
                missing_total += int(np.sum(~np.isfinite(sig)))
            except ValueError:
                pass

    return {
        "dataset": "Paderborn Bearing Dataset",
        "raw_dir": raw_dir,
        "n_bearing_codes": len(code_dirs),
        "n_files_total": n_files_total,
        "sample_rate_hz": prep.sample_rate_hz,
        "sample_channel_names": sample_channel_names,
        "fault_class_distribution": fault_classes,
        "damage_mode_distribution": damage_modes,
        "missing_values_in_sample_file": missing_total,
    }


def render_markdown(nasa: dict, cwru: dict, paderborn: dict) -> str:
    lines = ["# Bearing Datasets — Phase 1 EDA Report", ""]
    lines.append("Auto-generated by `preprocessing/eda_report.py`. Do not hand-edit; re-run the script instead.")
    lines.append("")

    lines.append("## 1. NASA IMS Bearing Dataset")
    lines.append(f"- Raw dir: `{nasa['raw_dir']}`")
    for test_name, info in nasa["tests"].items():
        if "error" in info:
            lines.append(f"- **{test_name}**: {info['error']}")
            continue
        lines.append(f"### {test_name}")
        lines.append(f"- Snapshot directory: `{info['snapshot_dir']}`")
        lines.append(f"- Snapshots: {info['n_snapshots']} (first `{info['first_snapshot']}`, last `{info['last_snapshot']}`)")
        lines.append(f"- Channels: {info['n_channels']} (expected {info['expected_channels']})")
        lines.append(f"- Samples/snapshot: {info['samples_per_snapshot']} @ {info['sample_rate_hz']:.0f} Hz ({info['snapshot_duration_sec']:.2f}s per snapshot)")
        lines.append(f"- Missing values in sample file: {info['missing_values_in_sample_file']}")
        lines.append(f"- Documented failing channels this run: {info['documented_failing_channels']}")
        lines.append(f"- Labels: {info['labels']}")
        lines.append("")

    lines.append("## 2. CWRU Bearing Dataset")
    lines.append(f"- Raw dir: `{cwru['raw_dir']}`")
    lines.append(f"- Files: {cwru['n_files']}")
    lines.append(f"- Sample rate: {cwru['sample_rate_hz']:.0f} Hz")
    lines.append(f"- Fault class distribution: {cwru['fault_class_distribution']}")
    lines.append(f"- Missing values (total across files): {cwru['missing_values_total']}")
    lines.append("- File format: MATLAB `.mat`, channel keys observed: "
                  f"`{cwru['files'][0]['available_channel_keys'] if cwru['files'] else 'n/a'}`")
    lines.append("")

    lines.append("## 3. Paderborn Bearing Dataset")
    lines.append(f"- Raw dir: `{paderborn['raw_dir']}`")
    lines.append(f"- Bearing codes inspected: {paderborn['n_bearing_codes']}")
    lines.append(f"- Total files: {paderborn['n_files_total']}")
    lines.append(f"- Sample rate: {paderborn['sample_rate_hz']:.0f} Hz")
    lines.append(f"- Channel names (sample file): {paderborn['sample_channel_names']}")
    lines.append(f"- Fault class distribution (file counts): {paderborn['fault_class_distribution']}")
    lines.append(f"- Damage mode distribution (artificial vs real): {paderborn['damage_mode_distribution']}")
    lines.append(f"- Missing values in sample file: {paderborn['missing_values_in_sample_file']}")
    lines.append("")

    lines.append("## 4. Cross-Dataset Summary")
    lines.append("| Dataset | Sample Rate | Fault Classes | Label Source |")
    lines.append("|---|---|---|---|")
    lines.append(f"| NASA IMS | {nasa['tests'].get('1st_test', {}).get('sample_rate_hz', 'n/a')} Hz | healthy, inner_race, outer_race, ball | RMS-trend heuristic (no ground truth) |")
    lines.append(f"| CWRU | {cwru['sample_rate_hz']:.0f} Hz | healthy, inner_race, outer_race, ball | Filename-encoded (ground truth) |")
    lines.append(f"| Paderborn | {paderborn['sample_rate_hz']:.0f} Hz | healthy, inner_race, outer_race, combined | Bearing-code lookup table (ground truth) |")
    lines.append("")
    lines.append("**Domain shift note**: the three datasets differ in sample rate (20/48/64 kHz), rig geometry, "
                  "bearing type, and operating conditions, so raw signals are NOT directly comparable — only the "
                  "engineered feature vectors (Phase 3/4) are unified across datasets.")

    return "\n".join(lines)


def main():
    with open(os.path.join("configs", "dataset_paths.json"), "r", encoding="utf-8") as f:
        paths = json.load(f)

    nasa_summary = inspect_nasa_ims(paths["nasa_ims"]["raw_dir"])
    cwru_summary = inspect_cwru(paths["cwru"]["raw_dir"])
    paderborn_summary = inspect_paderborn(paths["paderborn"]["raw_dir"])

    os.makedirs(paths["output"]["reports_dir"], exist_ok=True)
    json_path = os.path.join(paths["output"]["reports_dir"], "bearing_eda_summary.json")
    md_path = os.path.join(paths["output"]["reports_dir"], "bearing_eda_report.md")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"nasa_ims": nasa_summary, "cwru": cwru_summary, "paderborn": paderborn_summary}, f, indent=2, default=str)

    md = render_markdown(nasa_summary, cwru_summary, paderborn_summary)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md)

    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")


if __name__ == "__main__":
    main()
