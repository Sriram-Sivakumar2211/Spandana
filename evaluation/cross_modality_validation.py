import os
import sys
import json
import argparse
import numpy as np
import torch
from torch.utils.data import DataLoader

sys.path.insert(0, os.path.abspath("."))

from lnn.model import SpandanaLTC
from utils.common import set_seed, get_device, setup_logging
from utils.training_loop import train_classifier_from_splits
from utils.torch_dataset import build_sequences, BearingSequenceDataset
from utils.schema import CANONICAL_FEATURE_KEYS, GROUND_TRUTH_ENUM, encode_ground_truth
from preprocessing.bearing_common import SignalScaler
from evaluation.metrics import classification_metrics, predict_all

logger = setup_logging(name="evaluation.cross_modality")

"""
Cross-MODALITY validation (distinct from evaluation/cross_dataset_validation.py's
cross-DATASET bearing-only scenarios): trains the general severity model
(healthy/warning/faulty, 24-dim canonical schema) on one machine MODALITY --
either Member 1's electro-mechanical sensors (MetroPT-3 air compressor,
squirrel-cage motor, thermal motor -- current/voltage/temperature/RPM
features) or Member 2's bearing-vibration rigs (NASA IMS/CWRU/Paderborn --
RMS/kurtosis/spectral/wavelet features) -- and evaluates on the OTHER
modality, held out entirely (never seen in training or scaler fitting).

This is a strictly harder test than cross-dataset domain shift: the two
modalities populate structurally DISJOINT slices of the 24-dim canonical
feature vector (see utils/schema.py::fill_feature_vector) -- e.g. a bearing
reading zero-fills temperature/current/rpm, and a MetroPT-3 reading
zero-fills RMS/kurtosis/spectral entropy. A model transferring across this
gap must generalize from "which features are populated and how" rather than
from comparable physical quantities, so a near-chance result here is an
expected, honest finding, not evidence of a broken pipeline.
"""

MEMBER1_SOURCES = ["metropt3", "thermal_motor", "squirrel_cage"]
BEARING_SOURCES = ["nasa_ims", "cwru", "paderborn"]


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


def load_source_train_val(splits_dir: str, sources: list):
    X_tr_parts, y_tr_parts, g_tr_parts = [], [], []
    X_v_parts, y_v_parts, g_v_parts = [], [], []
    for src in sources:
        records = load_standardized(src)
        X, y, groups = records_to_arrays(records)
        split = np.load(os.path.join(splits_dir, f"{src}_split.npz"))
        train_mask, val_mask = split["train_mask"], split["val_mask"]
        X_tr_parts.append(X[train_mask]); y_tr_parts.append(y[train_mask])
        g_tr_parts.append(np.array([f"{src}_{g}" for g in groups[train_mask]]))
        X_v_parts.append(X[val_mask]); y_v_parts.append(y[val_mask])
        g_v_parts.append(np.array([f"{src}_{g}" for g in groups[val_mask]]))
    X_train = np.concatenate(X_tr_parts); y_train = np.concatenate(y_tr_parts); g_train = np.concatenate(g_tr_parts)
    X_val = np.concatenate(X_v_parts); y_val = np.concatenate(y_v_parts); g_val = np.concatenate(g_v_parts)
    return (X_train, y_train, g_train), (X_val, y_val, g_val)


def load_target_full(sources: list):
    """Loads the ENTIRE target modality (not just its test split) -- when the
    target modality is the held-out side of a cross-modality scenario, none
    of it was used for training or scaler fitting, so its train/val/test
    split (computed for its own in-modality experiments) is irrelevant here."""
    X_parts, y_parts, g_parts = [], [], []
    for src in sources:
        records = load_standardized(src)
        X, y, groups = records_to_arrays(records)
        X_parts.append(X); y_parts.append(y)
        g_parts.append(np.array([f"{src}_{g}" for g in groups]))
    return np.concatenate(X_parts), np.concatenate(y_parts), np.concatenate(g_parts)


def run_scenario(name: str, source_names: list, target_names: list, splits_dir: str,
                  cfg: dict, checkpoints_dir: str, log_dir: str, device: torch.device) -> dict:
    logger.info("=== Cross-modality scenario: %s -> %s ===", "+".join(source_names), "+".join(target_names))

    (X_train, y_train, g_train), (X_val, y_val, g_val) = load_source_train_val(splits_dir, source_names)

    # Scaler fit ONLY on source-modality training features, mirroring a real
    # deployment where the target modality's statistics are unknown in advance.
    scaler = SignalScaler().fit(X_train)
    X_train_s = scaler.transform(X_train)
    X_val_s = scaler.transform(X_val)

    X_target, y_target, g_target = load_target_full(target_names)
    X_target_s = scaler.transform(X_target, clip=10.0)

    seq_train_X, seq_train_y = build_sequences(X_train_s, y_train, g_train, seq_len=cfg["seq_len"], stride=cfg["stride"])
    seq_val_X, seq_val_y = build_sequences(X_val_s, y_val, g_val, seq_len=cfg["seq_len"], stride=cfg["stride"])
    seq_target_X, seq_target_y = build_sequences(X_target_s, y_target, g_target, seq_len=cfg["seq_len"], stride=cfg["stride"])

    splits = {
        "train": (seq_train_X, seq_train_y),
        "val": (seq_val_X, seq_val_y),
        "test": (seq_target_X, seq_target_y),
    }

    num_classes = len(GROUND_TRUTH_ENUM)
    model = SpandanaLTC(
        input_size=X_train.shape[1], num_classes=num_classes, hidden_size=cfg["hidden_size"],
        sparsity_level=cfg["sparsity_level"], ode_unfolds=cfg["ode_unfolds"], seed=cfg["seed"],
    )

    scenario_checkpoints_dir = os.path.join(checkpoints_dir, name)
    scenario_log_dir = os.path.join(log_dir, name)
    result = train_classifier_from_splits(model, cfg, splits, scenario_checkpoints_dir, scenario_log_dir, num_classes, device)

    checkpoint = torch.load(result["checkpoint_path"], map_location=device, weights_only=False)
    model.load_state_dict(checkpoint["model_state_dict"])
    target_loader = DataLoader(BearingSequenceDataset(seq_target_X, seq_target_y), batch_size=cfg["batch_size"], shuffle=False)
    y_true, y_pred, y_proba = predict_all(model, target_loader, device)
    target_metrics = classification_metrics(y_true, y_pred, y_proba, num_classes)

    return {
        "scenario": name,
        "source_modality": source_names,
        "target_modality": target_names,
        "n_train_sequences": len(seq_train_y),
        "n_target_sequences": len(seq_target_y),
        "target_class_distribution": {c: int(np.sum(y_target == encode_ground_truth(c))) for c in GROUND_TRUTH_ENUM},
        "target_metrics": target_metrics,
        "training_time_sec": result["training_time_sec"],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=os.path.join("configs", "ltc_general_config.json"))
    parser.add_argument("--splits-dir", default=os.path.join("data", "bearing_splits"))
    parser.add_argument("--checkpoints-dir", default=os.path.join("data", "checkpoints", "cross_modality"))
    parser.add_argument("--log-dir", default=os.path.join("reports", "tensorboard", "cross_modality"))
    parser.add_argument("--reports-dir", default="reports")
    parser.add_argument("--epochs", type=int, default=20, help="Override epoch budget for the 2 scenario re-trains.")
    args = parser.parse_args()

    with open(args.config, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    cfg = dict(cfg)
    cfg["epochs"] = args.epochs
    cfg["patience"] = min(cfg["patience"], 5)

    set_seed(cfg["seed"])
    device = get_device()

    scenarios = [
        ("member1_to_bearing", MEMBER1_SOURCES, BEARING_SOURCES),
        ("bearing_to_member1", BEARING_SOURCES, MEMBER1_SOURCES),
    ]

    results = {}
    for name, sources, targets in scenarios:
        results[name] = run_scenario(name, sources, targets, args.splits_dir, cfg, args.checkpoints_dir, args.log_dir, device)

    os.makedirs(args.reports_dir, exist_ok=True)
    with open(os.path.join(args.reports_dir, "cross_modality_validation.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)

    lines = ["# Cross-Modality Validation Report", ""]
    lines.append(
        "Tests whether the general severity model (healthy/warning/faulty, 24-dim canonical schema) "
        "trained on ONE machine modality transfers to a structurally different modality it never saw -- "
        "Member 1's electro-mechanical sensors (MetroPT-3 air compressor, squirrel-cage motor, thermal "
        "motor) vs. Member 2's bearing-vibration rigs (NASA IMS, CWRU, Paderborn). This is strictly "
        "harder than cross-dataset domain shift (see cross_dataset_report.md): the two modalities "
        "populate disjoint slices of the 24-dim feature vector (utils/schema.py::fill_feature_vector), "
        "so transfer requires generalizing from 'which features are populated and how' rather than from "
        "comparable physical quantities."
    )
    lines.append("")
    lines.append("| Scenario | Source modality | Target modality | Target Accuracy | Target F1 (macro) | Target ROC AUC |")
    lines.append("|---|---|---|---|---|---|")
    for name, res in results.items():
        m = res["target_metrics"]
        lines.append(
            f"| {name} | {'+'.join(res['source_modality'])} | {'+'.join(res['target_modality'])} | "
            f"{m['accuracy']:.4f} | {m['f1_macro']:.4f} | {m['roc_auc_macro']:.4f} |"
        )
    lines.append("")
    for name, res in results.items():
        lines.append(f"**{name}** target class distribution: {res['target_class_distribution']}")
    lines.append("")
    lines.append(
        "**Honest interpretation**: read any result above alongside its target class distribution and "
        "the ground_truth caveat already disclosed for Member 1's data (preprocessing/schema_adapter.py) "
        "-- MetroPT-3 is 100% 'faulty', squirrel-cage and thermal_motor are 100% 'healthy' (no 'warning' "
        "examples exist anywhere in Member 1's data), so a model that always predicts one class can score "
        "deceptively well or poorly purely from this imbalance, independent of genuine cross-modality "
        "generalization. Numbers are reported as measured, without adjusting thresholds, oversampling, or "
        "re-labeling classes to manufacture a better-looking result."
    )

    with open(os.path.join(args.reports_dir, "cross_modality_report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print("\n".join(lines))


if __name__ == "__main__":
    main()
