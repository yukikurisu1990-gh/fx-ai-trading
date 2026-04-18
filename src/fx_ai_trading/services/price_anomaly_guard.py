"""PriceAnomalyGuardService — ATR-based flash-halt detection skeleton (D3 §2 / 6.3 / M9).

Implements the PriceAnomalyGuard Protocol.

M9 scope:
  - is_anomaly(): always returns False (no real spike detection yet).
  - record(): stores the ATR reading internally (for Phase 7 use).

Phase 7: detect flash-crash / price-spike by comparing latest price deviation
to atr_spike_multiplier × stored atr_14. Trigger flash-halt (return True) when
deviation exceeds the multiplier threshold.
"""

from __future__ import annotations

import logging

_log = logging.getLogger(__name__)

_DEFAULT_ATR_SPIKE_MULTIPLIER = 3.0


class PriceAnomalyGuardService:
    """ATR-based anomaly guard skeleton for M9.

    Args:
        atr_spike_multiplier: (Phase 7) Multiplier applied to atr_14 to define
            the spike threshold. Stored now; used in Phase 7 implementation.
    """

    def __init__(self, atr_spike_multiplier: float = _DEFAULT_ATR_SPIKE_MULTIPLIER) -> None:
        self._spike_multiplier = atr_spike_multiplier
        self._atr_by_instrument: dict[str, float] = {}

    def is_anomaly(self, instrument: str) -> bool:
        """M9 skeleton — always returns False.

        Phase 7: return True when price deviation > atr_spike_multiplier × atr_14.
        """
        _log.debug(
            "PriceAnomalyGuardService.is_anomaly: skeleton — returning False (%s)", instrument
        )
        return False

    def record(self, instrument: str, atr: float) -> None:
        """Store the latest ATR reading for *instrument*.

        Used by Phase 7 is_anomaly() logic.
        """
        _log.debug(
            "PriceAnomalyGuardService.record: %s atr=%.6f (stored for Phase 7)",
            instrument,
            atr,
        )
        self._atr_by_instrument[instrument] = atr
