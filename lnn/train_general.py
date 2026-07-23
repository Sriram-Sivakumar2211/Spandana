import os
import sys
import json
import argparse

sys.path.insert(0, os.path.abspath("."))

from lnn.model import SpandanaLTC
from utils.common import set_seed, get_device, setup_logging
from utils.training_loop import train_classifier
from utils.schema import CANONICAL_FEATURE_KEYS, GROUND_TRUTH_ENUM

logger = setup_logging(name="lnn.train_general")

"""
Trains the GENERAL Spandana LTC: the health-severity (healthy/warning/faulty)
classifier that spans all 6 datasets via the shared 23-key canonical feature
schema (utils/schema.py). This is a different, coarser task than the
bearing-specific fault-LOCATION classifier trained by lnn/train.py (5
classes, bearing datasets only) -- the two tasks use different label spaces
that cannot be honestly merged into one (see preprocessing/schema_adapter.py),
so they are two separate models sharing the same SpandanaLTC architecture.
"""


def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=os.path.join("configs", "ltc_general_config.json"))
    parser.add_argument("--data", default=os.path.join("data", "unified_schema", "six_dataset_unified.npz"))
    parser.add_argument("--checkpoints-dir", default=os.path.join("data", "checkpoints", "ltc_general"))
    parser.add_argument("--log-dir", default=os.path.join("reports", "tensorboard", "ltc_general"))
    args = parser.parse_args()

    cfg = load_config(args.config)
    set_seed(cfg["seed"])
    device = get_device()
    logger.info("Training general 6-dataset LTC (ncps) on device=%s", device)

    num_classes = len(GROUND_TRUTH_ENUM)
    feature_dim = len(CANONICAL_FEATURE_KEYS)
    model = SpandanaLTC(
        input_size=feature_dim, num_classes=num_classes, hidden_size=cfg["hidden_size"],
        sparsity_level=cfg["sparsity_level"], ode_unfolds=cfg["ode_unfolds"], seed=cfg["seed"],
    )

    result = train_classifier(model, cfg, args.data, args.checkpoints_dir, args.log_dir, num_classes, device)
    with open(os.path.join(args.checkpoints_dir, "train_result.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, default=str)
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
