import os
import sys
import json
import argparse

sys.path.insert(0, os.path.abspath("."))

from lnn.model import SpandanaLTC
from utils.common import set_seed, get_device, setup_logging
from utils.training_loop import train_classifier
from preprocessing.bearing_common import BEARING_CLASSES

logger = setup_logging(name="lnn.train")


def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_model(cfg: dict, input_size: int, num_classes: int) -> SpandanaLTC:
    return SpandanaLTC(
        input_size=input_size,
        num_classes=num_classes,
        hidden_size=cfg["hidden_size"],
        sparsity_level=cfg["sparsity_level"],
        ode_unfolds=cfg["ode_unfolds"],
        seed=cfg["seed"],
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=os.path.join("configs", "lnn_config.json"))
    parser.add_argument("--data", default=os.path.join("data", "unified", "unified_bearing_dataset.npz"))
    parser.add_argument("--checkpoints-dir", default=os.path.join("data", "checkpoints", "lnn"))
    parser.add_argument("--log-dir", default=os.path.join("reports", "tensorboard", "lnn"))
    args = parser.parse_args()

    cfg = load_config(args.config)
    set_seed(cfg["seed"])
    device = get_device()
    logger.info("Training LTC (ncps, production model) on device=%s", device)

    num_classes = len(BEARING_CLASSES)
    feature_dim = 17  # fixed by features.bearing_features.BEARING_FEATURE_KEYS
    model = build_model(cfg, input_size=feature_dim, num_classes=num_classes)

    result = train_classifier(model, cfg, args.data, args.checkpoints_dir, args.log_dir, num_classes, device)
    with open(os.path.join(args.checkpoints_dir, "train_result.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, default=str)
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
