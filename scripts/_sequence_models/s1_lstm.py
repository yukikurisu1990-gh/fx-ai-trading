"""S1: Bidirectional LSTM with final-step pooling + linear head.

Per PR #354 §4.1 (Phase 29.0b-α A0-broad design memo). α-fixed numerics:
  layers=2, hidden_dim=128, dropout=0.2, bidirectional=True.
"""

from __future__ import annotations

import torch
import torch.nn as nn

# α-fixed per PR #354 §4.1; NG#A0B-1 (no β-time grid)
S1_INPUT_DIM = 8
S1_HIDDEN_DIM = 128
S1_NUM_LAYERS = 2
S1_DROPOUT = 0.2


class S1BidirectionalLSTM(nn.Module):
    """Bidirectional LSTM; final-step pooling → scalar score.

    Per PR #354 §4.1:
      - layers=2; hidden_dim=128; dropout=0.2; bidirectional=True
      - input shape: (batch, 32, 8) — 32 M5 bars × 8 channels
      - pooling: final-step (last hidden state)
      - head: Linear(2*hidden_dim, 1) — bidirectional output = 2*hidden
      - output: scalar per row
    """

    def __init__(
        self,
        input_dim: int = S1_INPUT_DIM,
        hidden_dim: int = S1_HIDDEN_DIM,
        num_layers: int = S1_NUM_LAYERS,
        dropout: float = S1_DROPOUT,
    ):
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            dropout=dropout if num_layers > 1 else 0.0,
            bidirectional=True,
            batch_first=True,
        )
        self.head = nn.Linear(2 * hidden_dim, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (batch, 32, 8)
        out, _ = self.lstm(x)  # out: (batch, 32, 2*hidden_dim)
        pooled = out[:, -1, :]  # final-step pooling: (batch, 2*hidden_dim)
        return self.head(pooled).squeeze(-1)  # (batch,)
