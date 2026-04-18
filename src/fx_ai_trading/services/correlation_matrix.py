"""CorrelationMatrixService — dual-window rolling correlation skeleton (D3 §2 / 6.8 / M9).

Implements the CorrelationMatrix Protocol.

M9 scope:
  - get(): returns a stub CorrelationSnapshot with regime_detected=False.
  - update(): no-op; returns empty list.
  - exceeds_threshold(): always returns False.

Phase 7: implement real rolling dual-window correlation with Pearson computation
over market_candles rows and persist to correlation_snapshots table.
Regime tightening enforcement in MetaDecider.Select is also Phase 7.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from fx_ai_trading.domain.correlation import CorrelationConfig, CorrelationSnapshot

_log = logging.getLogger(__name__)

_STUB_CORR = 0.0


class CorrelationMatrixService:
    """Dual-window correlation skeleton for M9.

    All methods are safe no-ops in M9.
    Phase 7: inject market_repo and compute real Pearson correlations.
    """

    def get(self, instrument_a: str, instrument_b: str) -> CorrelationSnapshot:
        """Return a stub CorrelationSnapshot with no regime detected."""
        _log.debug(
            "CorrelationMatrixService.get: stub — %s/%s → corr=0.0, regime=False",
            instrument_a,
            instrument_b,
        )
        return CorrelationSnapshot(
            instrument_a=instrument_a,
            instrument_b=instrument_b,
            short_window_corr=_STUB_CORR,
            long_window_corr=_STUB_CORR,
            regime_detected=False,
            computed_at=datetime.now(UTC),  # noqa: CLOCK — stub timestamp only
        )

    def update(self, config: CorrelationConfig) -> list[CorrelationSnapshot]:
        """M9 skeleton — no-op; returns empty list."""
        _log.debug("CorrelationMatrixService.update: skeleton — no-op (M9)")
        return []

    def exceeds_threshold(
        self,
        instrument_a: str,
        instrument_b: str,
        threshold: float,
    ) -> bool:
        """M9 skeleton — always returns False."""
        return False
