"""S3: Transformer encoder with first-position pooling + linear head.

Per PR #354 §4.3 (Phase 29.0b-α A0-broad design memo). α-fixed numerics:
  2 layers, d_model=128, n_heads=4, ff_dim=256, dropout=0.2,
  sinusoidal positional encoding (fixed, not learned).
"""

from __future__ import annotations

import math

import torch
import torch.nn as nn

# α-fixed per PR #354 §4.3; NG#A0B-1
S3_INPUT_DIM = 8
S3_D_MODEL = 128
S3_N_HEADS = 4
S3_NUM_LAYERS = 2
S3_FF_DIM = 256
S3_DROPOUT = 0.2
S3_MAX_SEQ_LEN = 32


def _build_sinusoidal_pe(max_len: int, d_model: int) -> torch.Tensor:
    """Standard sinusoidal positional encoding (fixed; not learned).

    Per PR #354 §4.3.
    """
    pe = torch.zeros(max_len, d_model, dtype=torch.float32)
    position = torch.arange(0, max_len, dtype=torch.float32).unsqueeze(1)
    div_term = torch.exp(
        torch.arange(0, d_model, 2, dtype=torch.float32)
        * -(math.log(10000.0) / d_model)
    )
    pe[:, 0::2] = torch.sin(position * div_term)
    pe[:, 1::2] = torch.cos(position * div_term)
    return pe  # shape (max_len, d_model)


class S3TransformerEncoder(nn.Module):
    """Transformer encoder; sinusoidal PE; first-position pooling → scalar.

    Per PR #354 §4.3:
      - 2 encoder layers; d_model=128; n_heads=4; ff_dim=256; dropout=0.2
      - sinusoidal positional encoding (fixed)
      - first-position pooling (analogous to [CLS])
      - input shape: (batch, 32, 8); projected to d_model via input_proj
      - output: scalar per row
    """

    def __init__(
        self,
        input_dim: int = S3_INPUT_DIM,
        d_model: int = S3_D_MODEL,
        n_heads: int = S3_N_HEADS,
        num_layers: int = S3_NUM_LAYERS,
        ff_dim: int = S3_FF_DIM,
        dropout: float = S3_DROPOUT,
        max_seq_len: int = S3_MAX_SEQ_LEN,
    ):
        super().__init__()
        self.input_proj = nn.Linear(input_dim, d_model)
        self.register_buffer("pos_encoding", _build_sinusoidal_pe(max_seq_len, d_model))
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=n_heads,
            dim_feedforward=ff_dim,
            dropout=dropout,
            batch_first=True,
            activation="relu",
        )
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        self.head = nn.Linear(d_model, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (batch, 32, 8)
        proj = self.input_proj(x)  # → (batch, 32, 128)
        seq_len = proj.size(1)
        proj = proj + self.pos_encoding[:seq_len].unsqueeze(0)  # add PE
        out = self.encoder(proj)  # → (batch, 32, 128)
        pooled = out[:, 0, :]  # first-position pooling: (batch, 128)
        return self.head(pooled).squeeze(-1)  # (batch,)
