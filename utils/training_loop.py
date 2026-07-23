import os
import time
import logging
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torch.utils.tensorboard import SummaryWriter

from utils.checkpoint import save_checkpoint, EarlyStopping
from utils.torch_dataset import build_sequences, BearingSequenceDataset

logger = logging.getLogger(__name__)


def load_unified_sequences(cfg: dict, unified_path: str) -> dict:
    data = np.load(unified_path, allow_pickle=True)
    splits = {}
    for split in ("train", "val", "test"):
        X, y = data[f"X_{split}"], data[f"y_{split}"]
        groups = data[f"group_{split}"]
        seq_X, seq_y = build_sequences(X, y, groups, seq_len=cfg["seq_len"], stride=cfg["stride"])
        splits[split] = (seq_X, seq_y)
        logger.info("%s: %d sequences of length %d", split, len(seq_y), cfg["seq_len"])
    return splits


def run_epoch(model, loader, criterion, optimizer, device, train: bool):
    """
    Batched offline training: every sequence starts from a fresh zero hidden
    state (hx=None) and uses uniform dt=1.0 between steps (timespans=None),
    since sliding-window sequences within one dataset are already extracted
    at a constant step. True cross-window state persistence and irregular
    elapsed-time handling are exercised at streaming inference time instead
    -- see inference/predict.py's LTCInferenceEngine, where batch_size=1
    and both hx and timespans carry real meaning.
    """
    model.train() if train else model.eval()
    total_loss, correct, total = 0.0, 0, 0

    with torch.set_grad_enabled(train):
        for xb, yb in loader:
            xb, yb = xb.to(device), yb.to(device)
            if train:
                optimizer.zero_grad()
            logits, _hx = model(xb)
            loss = criterion(logits, yb)
            if train:
                loss.backward()
                optimizer.step()

            total_loss += loss.item() * len(yb)
            correct += (logits.argmax(dim=1) == yb).sum().item()
            total += len(yb)

    return total_loss / total, correct / total


def train_classifier(model: nn.Module, cfg: dict, unified_path: str, checkpoints_dir: str,
                      log_dir: str, num_classes: int, device: torch.device) -> dict:
    """
    Train/validate/early-stop/checkpoint/test loop for the LTC model
    (utils.torch_dataset builds fixed-length sequences from the unified
    windows; the model itself is lnn/model.py::SpandanaLTC, built on ncps).
    """
    splits = load_unified_sequences(cfg, unified_path)
    return train_classifier_from_splits(model, cfg, splits, checkpoints_dir, log_dir, num_classes, device)


def train_classifier_from_splits(model: nn.Module, cfg: dict, splits: dict, checkpoints_dir: str,
                                  log_dir: str, num_classes: int, device: torch.device) -> dict:
    """
    Same train/validate/early-stop/checkpoint/test loop as train_classifier(),
    but takes already-built {"train": (X, y), "val": (X, y), "test": (X, y)}
    sequence arrays directly. Used by Phase 8 cross-dataset validation, where
    each scenario needs its own custom train/test split rather than the
    fixed unified_bearing_dataset.npz.
    """
    (X_train, y_train), (X_val, y_val), (X_test, y_test) = splits["train"], splits["val"], splits["test"]

    train_loader = DataLoader(BearingSequenceDataset(X_train, y_train), batch_size=cfg["batch_size"], shuffle=True)
    val_loader = DataLoader(BearingSequenceDataset(X_val, y_val), batch_size=cfg["batch_size"], shuffle=False)
    test_loader = DataLoader(BearingSequenceDataset(X_test, y_test), batch_size=cfg["batch_size"], shuffle=False)

    model = model.to(device)
    class_counts = np.bincount(y_train, minlength=num_classes).astype(np.float32)
    class_weights = torch.tensor(
        np.where(class_counts > 0, 1.0 / np.maximum(class_counts, 1), 0.0), dtype=torch.float32
    ).to(device)
    criterion = nn.CrossEntropyLoss(weight=class_weights)
    optimizer = torch.optim.Adam(model.parameters(), lr=cfg["lr"], weight_decay=cfg["weight_decay"])

    early_stopping = EarlyStopping(patience=cfg["patience"])
    os.makedirs(checkpoints_dir, exist_ok=True)
    checkpoint_path = os.path.join(checkpoints_dir, cfg["checkpoint_name"])
    writer = SummaryWriter(log_dir=log_dir)

    train_start = time.time()
    last_epoch = 0
    for epoch in range(cfg["epochs"]):
        last_epoch = epoch
        train_loss, train_acc = run_epoch(model, train_loader, criterion, optimizer, device, train=True)
        val_loss, val_acc = run_epoch(model, val_loader, criterion, optimizer, device, train=False)

        writer.add_scalar("Loss/train", train_loss, epoch)
        writer.add_scalar("Loss/val", val_loss, epoch)
        writer.add_scalar("Accuracy/train", train_acc, epoch)
        writer.add_scalar("Accuracy/val", val_acc, epoch)

        logger.info(
            "Epoch %d/%d | train_loss=%.4f train_acc=%.4f | val_loss=%.4f val_acc=%.4f",
            epoch + 1, cfg["epochs"], train_loss, train_acc, val_loss, val_acc,
        )

        if early_stopping.step(val_loss):
            save_checkpoint({
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "epoch": epoch,
                "val_loss": val_loss,
                "val_acc": val_acc,
                "config": cfg,
                "input_size": X_train.shape[-1],
                "num_classes": num_classes,
            }, checkpoint_path)
            logger.info("New best model saved (val_loss=%.4f) -> %s", val_loss, checkpoint_path)

        if early_stopping.should_stop:
            logger.info("Early stopping triggered at epoch %d", epoch + 1)
            break

    training_time_sec = time.time() - train_start

    checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=False)
    model.load_state_dict(checkpoint["model_state_dict"])
    # Unweighted criterion for the final test report: `criterion`'s per-class
    # weights are 0.0 for any class absent from y_train (correct for fighting
    # training-set imbalance), but reused at test time that makes any batch
    # drawn entirely from a class the source domain never had divide 0/0 = NaN
    # -- exactly what happens testing a source-trained model on a target
    # dataset with a fault type the source never saw (e.g. cross-dataset
    # scenarios in evaluation/cross_dataset_validation.py). Test loss should
    # reflect real model behavior on every target class, not be gated by
    # what the training set happened to contain.
    test_criterion = nn.CrossEntropyLoss()
    test_loss, test_acc = run_epoch(model, test_loader, test_criterion, optimizer, device, train=False)
    logger.info("Test results (best checkpoint): loss=%.4f acc=%.4f", test_loss, test_acc)

    writer.close()
    return {
        "test_loss": test_loss,
        "test_acc": test_acc,
        "best_val_loss": checkpoint["val_loss"],
        "best_epoch": checkpoint["epoch"],
        "epochs_run": last_epoch + 1,
        "training_time_sec": training_time_sec,
        "checkpoint_path": checkpoint_path,
    }
