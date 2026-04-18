"""CorrelationMatrix domain interface and DTOs (D3 §2 / 6.8).

Dual-window (short 1h / long 30d) rolling correlation.
MVP: compute and store; regime tightening enforcement deferred to Phase 7.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

# ---------------------------------------------------------------------------
# DTOs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CorrelationConfig:
    """Configuration for CorrelationMatrix window and regime detection (6.8)."""

    short_window_hours: int = 1
    long_window_days: int = 30
    regime_delta_threshold: float = 0.3
    tightening_delta: float = 0.1
    update_interval_seconds: int = 60


@dataclass(frozen=True)
class CorrelationSnapshot:
    """Computed correlation values for a pair of instruments."""

    instrument_a: str
    instrument_b: str
    short_window_corr: float
    long_window_corr: float
    regime_detected: bool
    computed_at: datetime


# ---------------------------------------------------------------------------
# Interface (Protocol)
# ---------------------------------------------------------------------------


class CorrelationMatrix(Protocol):
    """Rolling dual-window correlation computation (D3 §2 / 6.8).

    MVP invariant: computes and persists correlation_snapshots; regime tightening
    applied to MetaDecider Select is deferred to Phase 7.
    Idempotent: same inputs → same correlation values.
    """

    def get(self, instrument_a: str, instrument_b: str) -> CorrelationSnapshot:
        """Return the latest correlation snapshot for the given pair."""
        ...

    def update(self, config: CorrelationConfig) -> list[CorrelationSnapshot]:
        """Recompute correlations for all active pairs using *config*.

        Side effect: writes to correlation_snapshots table.
        """
        ...

    def exceeds_threshold(
        self,
        instrument_a: str,
        instrument_b: str,
        threshold: float,
    ) -> bool:
        """Return True if absolute correlation between the pair exceeds *threshold*."""
        ...
