import os
import sys
import json
import logging
import numpy as np
import torch

sys.path.insert(0, os.path.abspath("."))

from augmentation.vae import train_vae
from utils.common import set_seed, get_device, setup_logging
from utils.schema import CANONICAL_FEATURE_KEYS, GROUND_TRUTH_ENUM, encode_ground_truth

logger = setup_logging(name="augmentation.augment_training_data")

"""
Rare-class augmentation for the general 6-dataset severity classifier.
`preprocessing/build_six_dataset_unified.py` revealed a real, honest class
imbalance in the ALREADY-EXISTING preprocessed data this project reuses:
"warning" has zero examples across all 6 sources (nothing to learn from --
not augmented here, since fabricating a class from nothing is not
augmentation, it's invention), and "faulty" is a ~3.2x minority relative to
"healthy" in the training split.

This trains a small VAE (augmentation/vae.py) on the REAL "faulty" training
vectors only, then samples synthetic faulty vectors to bring the training
class ratio closer to balanced. Synthetic samples never touch val/test --
only the training split is augmented, so evaluation always reflects real
data. Whether this is actually kept depends on whether it improves
validation macro-F1 (checked in lnn/train_general.py's evaluation, not
assumed here).

Each synthetic feature vector is repeated `seq_len` times to form one
synthetic "sequence" (a unique synthetic group_id per vector) -- this
mirrors how the real bearing datasets behave in practice: a single raw
recording is one static operating condition, so consecutive windows within
it are already near-identical, not an evolving trajectory.
"""


def augment(unified_path: str, seq_len: int, target_ratio: float = 1.0, seed: int = 42):
    set_seed(seed)
    device = get_device()
    data = np.load(unified_path, allow_pickle=True)
    X_train, y_train, g_train = data["X_train"], data["y_train"], data["group_train"]

    healthy_idx = encode_ground_truth("healthy")
    faulty_idx = encode_ground_truth("faulty")

    n_healthy = int(np.sum(y_train == healthy_idx))
    n_faulty = int(np.sum(y_train == faulty_idx))
    n_synthetic = max(0, int(n_healthy * target_ratio) - n_faulty)
    logger.info("Real train counts: healthy=%d faulty=%d -> generating %d synthetic faulty vectors", n_healthy, n_faulty, n_synthetic)

    faulty_vectors = torch.tensor(X_train[y_train == faulty_idx], dtype=torch.float32)
    input_dim = faulty_vectors.shape[1]

    faulty_vae = train_vae(faulty_vectors, input_dim=input_dim, epochs=150, device=device)

    healthy_vectors = torch.tensor(X_train[y_train == healthy_idx], dtype=torch.float32)
    healthy_vae = train_vae(healthy_vectors, input_dim=input_dim, epochs=150, device=device)

    os.makedirs(os.path.join("data", "checkpoints", "vae"), exist_ok=True)
    torch.save({"model_state_dict": healthy_vae.state_dict(), "input_dim": input_dim,
                "latent_dim": healthy_vae.latent_dim}, os.path.join("data", "checkpoints", "vae", "healthy_vae.pt"))

    if n_synthetic == 0:
        logger.info("Faulty class already at/above target ratio -- no synthetic samples needed.")
        synthetic_X = np.empty((0, input_dim), dtype=np.float32)
        synthetic_y = np.empty((0,), dtype=np.int64)
        synthetic_groups = np.empty((0,), dtype=object)
    else:
        n_vectors = int(np.ceil(n_synthetic / seq_len))
        synthetic_vectors = faulty_vae.generate(n_vectors, device).cpu().numpy()

        synthetic_X_parts, synthetic_y_parts, synthetic_groups_parts = [], [], []
        for i, vec in enumerate(synthetic_vectors):
            group_id = f"synthetic_faulty_{i}"
            for _ in range(seq_len):
                synthetic_X_parts.append(vec)
                synthetic_y_parts.append(faulty_idx)
                synthetic_groups_parts.append(group_id)
        synthetic_X = np.array(synthetic_X_parts, dtype=np.float32)
        synthetic_y = np.array(synthetic_y_parts, dtype=np.int64)
        synthetic_groups = np.array(synthetic_groups_parts, dtype=object)

    X_train_aug = np.concatenate([X_train, synthetic_X])
    y_train_aug = np.concatenate([y_train, synthetic_y])
    g_train_aug = np.concatenate([g_train.astype(object), synthetic_groups])

    out_path = unified_path.replace(".npz", "_augmented.npz")
    np.savez(
        out_path,
        X_train=X_train_aug, y_train=y_train_aug, group_train=g_train_aug,
        X_val=data["X_val"], y_val=data["y_val"], group_val=data["group_val"],
        X_test=data["X_test"], y_test=data["y_test"], group_test=data["group_test"],
    )

    summary = {
        "real_train_healthy": n_healthy, "real_train_faulty": n_faulty,
        "n_synthetic_vectors_generated": len(synthetic_X) // seq_len if seq_len else 0,
        "n_synthetic_rows_added": int(len(synthetic_X)),
        "augmented_path": out_path,
    }
    logger.info("Augmentation summary: %s", summary)
    return summary


if __name__ == "__main__":
    result = augment(os.path.join("data", "unified_schema", "six_dataset_unified.npz"), seq_len=5)
    os.makedirs("reports", exist_ok=True)
    with open(os.path.join("reports", "augmentation_summary.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(json.dumps(result, indent=2))
