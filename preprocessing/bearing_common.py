import numpy as np
from sklearn.model_selection import GroupShuffleSplit

# Unified fault taxonomy shared across NASA IMS, CWRU and Paderborn.
# Not every dataset produces every class (e.g. only CWRU has isolated "ball"
# damage; only Paderborn has "combined"), but the encoding is fixed so label
# indices are comparable across datasets during cross-dataset validation.
BEARING_CLASSES = ["healthy", "inner_race", "outer_race", "ball", "combined"]
LABEL_TO_INDEX = {c: i for i, c in enumerate(BEARING_CLASSES)}
INDEX_TO_LABEL = {i: c for i, c in enumerate(BEARING_CLASSES)}


def encode_label(label: str) -> int:
    if label not in LABEL_TO_INDEX:
        raise ValueError(f"Unknown bearing fault label '{label}'. Expected one of {BEARING_CLASSES}")
    return LABEL_TO_INDEX[label]


def decode_label(index: int) -> str:
    return INDEX_TO_LABEL[int(index)]


def clean_signal(signal: np.ndarray, glitch_std: float = 20.0) -> np.ndarray:
    """
    Repairs a raw vibration signal without destroying fault-diagnostic
    impulsiveness. Bearing fault impacts are legitimate high-amplitude
    transients, so we deliberately do NOT clip generic outliers -- only:
      1. Interpolate NaN/Inf samples (sensor dropouts).
      2. Clip non-physical digitizer glitches beyond `glitch_std` sigma,
         which is far outside even severe fault impact amplitudes.
    """
    signal = np.asarray(signal, dtype=np.float64).copy()
    bad = ~np.isfinite(signal)
    if bad.any():
        good_idx = np.flatnonzero(~bad)
        if len(good_idx) == 0:
            return np.zeros_like(signal)
        signal[bad] = np.interp(np.flatnonzero(bad), good_idx, signal[good_idx])

    std = signal.std()
    mean = signal.mean()
    if std > 1e-12:
        limit = glitch_std * std
        signal = np.clip(signal, mean - limit, mean + limit)
    return signal


def sliding_window_indices(n_samples: int, window_size: int, step: int):
    """Yields (start, end) index pairs for a fixed-size sliding window over a 1D signal."""
    indices = []
    for start in range(0, n_samples - window_size + 1, step):
        indices.append((start, start + window_size))
    return indices


class SignalScaler:
    """
    Z-score feature scaler fit ONLY on the training split's feature vectors,
    then applied to train/val/test. Fitting on train-only avoids leaking
    validation/test statistics into the normalization step.
    """
    def __init__(self):
        self.mean_ = None
        self.std_ = None

    def fit(self, feature_matrix: np.ndarray) -> "SignalScaler":
        self.mean_ = feature_matrix.mean(axis=0)
        self.std_ = feature_matrix.std(axis=0)
        self.std_[self.std_ < 1e-8] = 1.0
        return self

    def transform(self, feature_matrix: np.ndarray, clip: float = None) -> np.ndarray:
        """
        `clip` bounds the z-scored output to [-clip, clip]. Leave it None for
        same-domain use (Phases 2-7), where features are always in a
        sane range relative to the fitted statistics. Cross-dataset
        validation (Phase 8) DOES need it: applying a scaler fit on one
        dataset's statistics to a completely different rig/sample-rate
        dataset can otherwise produce extreme z-scores that overflow the
        LNN's ODE integration (inf/inf -> NaN loss), which would be a
        numerical artifact, not a meaningful measurement of domain shift.
        """
        if self.mean_ is None:
            raise RuntimeError("SignalScaler must be fit() before transform().")
        scaled = (feature_matrix - self.mean_) / self.std_
        if clip is not None:
            scaled = np.clip(scaled, -clip, clip)
        return scaled

    def fit_transform(self, feature_matrix: np.ndarray) -> np.ndarray:
        return self.fit(feature_matrix).transform(feature_matrix)

    def to_dict(self) -> dict:
        return {"mean": self.mean_.tolist(), "std": self.std_.tolist()}

    @classmethod
    def from_dict(cls, d: dict) -> "SignalScaler":
        scaler = cls()
        scaler.mean_ = np.array(d["mean"], dtype=np.float64)
        scaler.std_ = np.array(d["std"], dtype=np.float64)
        return scaler


def group_aware_split(groups: np.ndarray, val_size: float = 0.15, test_size: float = 0.15, seed: int = 42):
    """
    Splits window indices into train/val/test while keeping every window that
    originated from the same raw source file/run ("group") in the same
    split. Overlapping sliding windows drawn from one run are highly
    correlated, so a plain random split would leak near-duplicate windows
    across train/test and inflate reported accuracy.

    Returns three boolean masks (train_mask, val_mask, test_mask) aligned
    with `groups`.
    """
    groups = np.asarray(groups)
    n = len(groups)
    idx = np.arange(n)

    gss1 = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=seed)
    train_val_idx, test_idx = next(gss1.split(idx, groups=groups))

    remaining_groups = groups[train_val_idx]
    relative_val_size = val_size / (1.0 - test_size)
    gss2 = GroupShuffleSplit(n_splits=1, test_size=relative_val_size, random_state=seed)
    train_idx_rel, val_idx_rel = next(gss2.split(train_val_idx, groups=remaining_groups))

    train_idx = train_val_idx[train_idx_rel]
    val_idx = train_val_idx[val_idx_rel]

    train_mask = np.zeros(n, dtype=bool)
    val_mask = np.zeros(n, dtype=bool)
    test_mask = np.zeros(n, dtype=bool)
    train_mask[train_idx] = True
    val_mask[val_idx] = True
    test_mask[test_idx] = True
    return train_mask, val_mask, test_mask
