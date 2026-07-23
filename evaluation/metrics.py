import os
import time
import numpy as np
import torch
from sklearn.metrics import (
    accuracy_score, precision_recall_fscore_support, roc_auc_score,
    confusion_matrix, precision_recall_curve,
)


def classification_metrics(y_true: np.ndarray, y_pred: np.ndarray, y_proba: np.ndarray, num_classes: int) -> dict:
    accuracy = accuracy_score(y_true, y_pred)
    precision, recall, f1, _support = precision_recall_fscore_support(
        y_true, y_pred, average="macro", zero_division=0
    )

    # Macro ROC AUC computed as a manual average of per-class one-vs-rest binary
    # AUCs, restricted to classes present in y_true. This deliberately avoids
    # sklearn's built-in multi_class="ovr" path: that path requires y_score
    # rows to sum to 1 over the FULL class set, which breaks whenever a
    # cross-dataset target is missing a class entirely (e.g. CWRU has no
    # "combined" samples) and we'd otherwise have to drop that probability
    # mass. Per-class binary AUC has no such requirement.
    classes_in_true = sorted(set(y_true.tolist()))
    per_class_aucs = []
    for c in classes_in_true:
        y_true_bin = (y_true == c).astype(int)
        if 0 < y_true_bin.sum() < len(y_true_bin):
            try:
                per_class_aucs.append(roc_auc_score(y_true_bin, y_proba[:, c]))
            except ValueError:
                pass
    roc_auc = float(np.mean(per_class_aucs)) if per_class_aucs else float("nan")

    cm = confusion_matrix(y_true, y_pred, labels=list(range(num_classes)))

    # False positives / negatives per class, aggregated (one-vs-rest).
    fp_total, fn_total = 0, 0
    for c in range(num_classes):
        fp_total += int(cm[:, c].sum() - cm[c, c])
        fn_total += int(cm[c, :].sum() - cm[c, c])

    return {
        "accuracy": float(accuracy),
        "precision_macro": float(precision),
        "recall_macro": float(recall),
        "f1_macro": float(f1),
        "roc_auc_macro": float(roc_auc),
        "confusion_matrix": cm.tolist(),
        "false_positives_total": fp_total,
        "false_negatives_total": fn_total,
    }


def pr_curve_per_class(y_true: np.ndarray, y_proba: np.ndarray, num_classes: int) -> dict:
    curves = {}
    for c in range(num_classes):
        y_true_bin = (y_true == c).astype(int)
        if y_true_bin.sum() == 0:
            continue
        precision, recall, _thresholds = precision_recall_curve(y_true_bin, y_proba[:, c])
        curves[str(c)] = {"precision": precision.tolist(), "recall": recall.tolist()}
    return curves


def model_size_bytes(checkpoint_path: str) -> int:
    return os.path.getsize(checkpoint_path)


def count_parameters(model: torch.nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


@torch.no_grad()
def measure_inference_latency(model: torch.nn.Module, sample_input: torch.Tensor, device: torch.device,
                               n_warmup: int = 10, n_runs: int = 100) -> dict:
    """Single-sample inference latency, matching real-time deployment (one window at a time)."""
    model.eval()
    sample_input = sample_input.to(device)

    for _ in range(n_warmup):
        model(sample_input)[0]

    if device.type == "cuda":
        torch.cuda.synchronize()

    timings = []
    for _ in range(n_runs):
        start = time.perf_counter()
        model(sample_input)[0]
        if device.type == "cuda":
            torch.cuda.synchronize()
        timings.append((time.perf_counter() - start) * 1000.0)

    timings = np.array(timings)
    return {
        "mean_ms": float(timings.mean()),
        "p50_ms": float(np.percentile(timings, 50)),
        "p95_ms": float(np.percentile(timings, 95)),
        "p99_ms": float(np.percentile(timings, 99)),
    }


@torch.no_grad()
def predict_all(model: torch.nn.Module, loader, device: torch.device):
    model.eval()
    all_logits, all_labels = [], []
    for xb, yb in loader:
        xb = xb.to(device)
        logits, _hx = model(xb)
        all_logits.append(logits.cpu().numpy())
        all_labels.append(yb.numpy())

    logits = np.concatenate(all_logits)
    labels = np.concatenate(all_labels)
    proba = torch.softmax(torch.from_numpy(logits), dim=1).numpy()
    preds = proba.argmax(axis=1)
    return labels, preds, proba
