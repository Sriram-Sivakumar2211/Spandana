import torch
import torch.nn as nn
from ncps.torch import LTC
from ncps.wirings import AutoNCP


class SpandanaLTC(nn.Module):
    """
    Liquid Time-Constant Network classifier over sequences of engineered
    sensor feature vectors, built on the official MIT `ncps` implementation
    (Hasani et al., "Liquid Time-Constant Networks", 2020) -- this project
    does not implement LTC ODE dynamics itself.

    This is the ONLY model in Spandana's final system: there is no LSTM
    anywhere in this path. `AutoNCP` wires `hidden_size` interneurons down
    to `num_classes` motor (output) neurons using the NCP sparse
    connectivity pattern from the same paper, so the classifier head is the
    network's own motor neurons rather than a bolted-on `nn.Linear`.

    Statefulness: `forward` accepts and returns the recurrent hidden state
    (`hx`) explicitly. Passing the previous call's `hx` back in on the next
    call is what lets a machine's hidden state persist continuously across
    windows arriving over time -- see `inference/predict.py`'s
    `LTCInferenceEngine`, which keeps one `hx` per `machine_id`.

    Irregular sampling: `forward` also accepts `timespans`, the real
    elapsed wall-clock time since the previous window. A vanilla LSTM/GRU
    has no principled way to use this; the LTC's per-neuron time constant
    is directly modulated by it, so a delayed or early sensor reading
    changes the dynamics instead of silently being treated as on-time.
    """

    def __init__(self, input_size: int, num_classes: int, hidden_size: int = 64,
                 sparsity_level: float = 0.5, ode_unfolds: int = 6, seed: int = 22222):
        super().__init__()
        wiring = AutoNCP(units=hidden_size, output_size=num_classes, sparsity_level=sparsity_level, seed=seed)
        self.ltc = LTC(
            input_size=input_size,
            units=wiring,
            return_sequences=False,
            batch_first=True,
            mixed_memory=False,  # mixed_memory=True would internally add an LSTM cell -- forbidden in this project
            ode_unfolds=ode_unfolds,
        )
        self.hidden_size = hidden_size
        self.num_classes = num_classes

    def forward(self, x: torch.Tensor, hx: torch.Tensor = None, timespans: torch.Tensor = None):
        """
        x: (batch, seq_len, input_size).
        hx: previous call's returned hidden state, or None to start from zero.
        timespans: (batch, seq_len) elapsed real time per step, or None for uniform dt=1.0.
        Returns (logits, hx) -- callers that don't need statefulness (e.g. batched
        offline training) can simply ignore the returned hx.
        """
        logits, hx_out = self.ltc(x, hx, timespans)
        return logits, hx_out
