"""Phase 29.0b-β sequence/NN architecture allowlist (S1 / S2 / S3).

Per PR #354 §4 (Phase 29.0b-α A0-broad design memo). Closed allowlist;
NG#A0B-1 forbids 4th architecture variant at β.

α-fixed numerics (no β-time grid):
  S1 BidirectionalLSTM: 2 layers, hidden=128, dropout=0.2
  S2 TemporalCNN: 4 blocks, kernel=3, dilations=[1,2,4,8], channels=64
  S3 TransformerEncoder: 2 layers, d_model=128, n_heads=4, ff_dim=256
"""

from __future__ import annotations

from typing import Literal

import torch.nn as nn

from .s1_lstm import S1BidirectionalLSTM
from .s2_temporal_cnn import S2TemporalCNN
from .s3_transformer import S3TransformerEncoder

ArchId = Literal["S1", "S2", "S3"]
CLOSED_ARCHITECTURE_ALLOWLIST: tuple[str, ...] = ("S1", "S2", "S3")


def build_sequence_model(arch_id: str) -> nn.Module:
    """Factory: build sequence model by closed-allowlist ID.

    NG#A0B-1: only S1 / S2 / S3 admissible; unknown ID raises ValueError.
    """
    if arch_id == "S1":
        return S1BidirectionalLSTM()
    if arch_id == "S2":
        return S2TemporalCNN()
    if arch_id == "S3":
        return S3TransformerEncoder()
    raise ValueError(
        f"Unknown arch_id={arch_id!r}; closed allowlist = "
        f"{CLOSED_ARCHITECTURE_ALLOWLIST} (NG#A0B-1)"
    )


__all__ = [
    "ArchId",
    "CLOSED_ARCHITECTURE_ALLOWLIST",
    "build_sequence_model",
    "S1BidirectionalLSTM",
    "S2TemporalCNN",
    "S3TransformerEncoder",
]
