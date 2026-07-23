import os
import sys
import json
import argparse
import numpy as np
import torch
from torch.utils.data import DataLoader

sys.path.insert(0, os.path.abspath("."))

from lnn.model import SpandanaLTC
from utils.common import get_device
from utils.torch_dataset import build_sequences, BearingSequenceDataset
from utils.schema import CANONICAL_FEATURE_KEYS, GROUND_TRUTH_ENUM
from evaluation.metrics import classification_metrics, model_size_bytes, count_parameters, measure_inference_latency, predict_all

"""
Evaluates the general 6-dataset LTC (health severity: healthy/warning/faulty)
on the REAL (never-augmented) test split. Reports macro metrics rather than
just accuracy, since accuracy alone is misleading under the real ~3.2:1
healthy/faulty imbalance disclosed in preprocessing/build_six_dataset_unified.py
-- and because "warning" has zero test examples, its row will show 0 support,
not fabricated performance.
"""


def load_test_sequences(unified_path: str, seq_len: int, stride: int):
    data = np.load(unified_path, allow_pickle=True)
    X, y, groups = data["X_test"], data["y_test"], data["group_test"]
    return build_sequences(X, y, groups, seq_len=seq_len, stride=stride)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default=os.path.join("data", "unified_schema", "six_dataset_unified.npz"))
    parser.add_argument("--config", default=os.path.join("configs", "ltc_general_config.json"))
    parser.add_argument("--checkpoint", default=os.path.join("data", "checkpoints", "ltc_general", "best_ltc_general.pt"))
    parser.add_argument("--reports-dir", default="reports")
    parser.add_argument("--label", default="baseline", help="Tag distinguishing this run in the output filenames (e.g. 'baseline' vs 'augmented').")
    args = parser.parse_args()

    with open(args.config, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    device = get_device()
    num_classes = len(GROUND_TRUTH_ENUM)
    feature_dim = len(CANONICAL_FEATURE_KEYS)

    seq_X, seq_y = load_test_sequences(args.data, cfg["seq_len"], cfg["stride"])
    loader = DataLoader(BearingSequenceDataset(seq_X, seq_y), batch_size=cfg["batch_size"], shuffle=False)

    model = SpandanaLTC(
        input_size=feature_dim, num_classes=num_classes, hidden_size=cfg["hidden_size"],
        sparsity_level=cfg["sparsity_level"], ode_unfolds=cfg["ode_unfolds"], seed=cfg["seed"],
    )
    checkpoint = torch.load(args.checkpoint, map_location=device, weights_only=False)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.to(device)

    y_true, y_pred, y_proba = predict_all(model, loader, device)
    metrics = classification_metrics(y_true, y_pred, y_proba, num_classes)

    train_result_path = os.path.join(os.path.dirname(args.checkpoint), "train_result.json")
    train_result = {}
    if os.path.exists(train_result_path):
        with open(train_result_path, "r", encoding="utf-8") as f:
            train_result = json.load(f)

    sample_input = next(iter(loader))[0][:1]
    latency = measure_inference_latency(model, sample_input, device)

    result = {
        "label": args.label,
        "metrics": metrics,
        "latency_ms": latency,
        "model_size_bytes": model_size_bytes(args.checkpoint),
        "n_parameters": count_parameters(model),
        "training_time_sec": train_result.get("training_time_sec"),
        "epochs_run": train_result.get("epochs_run"),
    }

    os.makedirs(args.reports_dir, exist_ok=True)
    out_path = os.path.join(args.reports_dir, f"general_model_evaluation_{args.label}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, default=str)

    print(f"[{args.label}] classes={GROUND_TRUTH_ENUM}")
    print(f"[{args.label}] accuracy={metrics['accuracy']:.4f} precision_macro={metrics['precision_macro']:.4f} "
          f"recall_macro={metrics['recall_macro']:.4f} f1_macro={metrics['f1_macro']:.4f} roc_auc_macro={metrics['roc_auc_macro']:.4f}")
    print(f"[{args.label}] confusion_matrix={metrics['confusion_matrix']}")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
