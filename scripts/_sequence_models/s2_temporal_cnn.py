"""S2: Temporal CNN with global average pooling + linear head.

Per PR #354 §4.2 (Phase 29.0b-α A0-broad design memo). α-fixed numerics:
  4 blocks, kernel=3, dilations=[1,2,4,8], channels=64, dropout=0.2.
"""

from __future__ import annotations

import torch
import torch.nn as nn

# α-fixed per PR #354 §4.2; NG#A0B-1
S2_INPUT_DIM = 8
S2_CHANNELS = 64
S2_KERNEL = 3
S2_DILATIONS: tuple[int, ...] = (1, 2, 4, 8)
S2_DROPOUT = 0.2


class S2TemporalCNN(nn.Module):
    """1D Temporal CNN; 4 dilated blocks; global average pooling → scalar.

    Per PR #354 §4.2:
      - 4 conv blocks; kernel=3; dilations=[1,2,4,8]; channels=64
      - dropout=0.2 between blocks
      - pooling: global average over temporal dim
      - input shape: (batch, 32, 8) - transposed to (batch, 8, 32) for conv1d
      - output: scalar per row
    """

    def __init__(
        self,
        input_dim: int = S2_INPUT_DIM,
        channels: int = S2_CHANNELS,
        kernel: int = S2_KERNEL,
        dilations: tuple[int, ...] = S2_DILATIONS,
        dropout: float = S2_DROPOUT,
    ):
        super().__init__()
        blocks: list[nn.Module] = []
        prev_c = input_dim
        for d in dilations:
            # SAME padding for kernel=3 with dilation=d: pad = d * (kernel-1) // 2
            padding = d * (kernel - 1) // 2
            blocks.append(
                nn.Conv1d(
                    in_channels=prev_c,
                    out_channels=channels,
                    kernel_size=kernel,
                    padding=padding,
                    dilation=d,
                )
            )
            blocks.append(nn.ReLU())
            blocks.append(nn.Dropout(dropout))
            prev_c = channels
        self.blocks = nn.Sequential(*blocks)
        self.head = nn.Linear(channels, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (batch, 32, 8)
        x = x.transpose(1, 2)  # → (batch, 8, 32) channels-first for conv1d
        out = self.blocks(x)  # → (batch, 64, 32)
        pooled = out.mean(dim=2)  # global avg pool → (batch, 64)
        return self.head(pooled).squeeze(-1)  # (batch,)
