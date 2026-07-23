import numpy as np
import torch
from torch.utils.data import Dataset


def build_sequences(X: np.ndarray, y: np.ndarray, groups: np.ndarray, seq_len: int = 5, stride: int = 1):
    """
    Turns a flat table of per-window feature vectors into overlapping
    sequences of `seq_len` consecutive windows, for the recurrent LTC model.
    Sequences never cross a group boundary (a group = one raw
    source recording), since windows from different recordings are not
    temporally contiguous. The label of a sequence is the label of its
    final (most recent) window -- i.e. "given the last seq_len windows of
    vibration behaviour, what is the machine's current condition".

    Groups shorter than `seq_len` are skipped (too little history).
    """
    seq_X, seq_y = [], []
    n = len(groups)
    start = 0
    while start < n:
        end = start
        while end < n and groups[end] == groups[start]:
            end += 1
        group_len = end - start
        if group_len >= seq_len:
            for s in range(start, end - seq_len + 1, stride):
                seq_X.append(X[s:s + seq_len])
                seq_y.append(y[s + seq_len - 1])
        start = end

    if not seq_X:
        return (
            np.empty((0, seq_len, X.shape[1]), dtype=np.float32),
            np.empty((0,), dtype=np.int64),
        )
    return np.stack(seq_X).astype(np.float32), np.array(seq_y, dtype=np.int64)


class BearingSequenceDataset(Dataset):
    """PyTorch Dataset over pre-built (seq_X, seq_y) arrays from build_sequences()."""

    def __init__(self, seq_X: np.ndarray, seq_y: np.ndarray):
        self.X = torch.from_numpy(seq_X).float()
        self.y = torch.from_numpy(seq_y).long()

    def __len__(self):
        return len(self.y)

    def __getitem__(self, idx):
        return self.X[idx], self.y[idx]
