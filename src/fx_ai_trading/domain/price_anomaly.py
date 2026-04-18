"""PriceAnomalyGuard domain interface (D3 §2 / 6.3 / M9).

Provides flash-crash / price-spike detection as a second independent defence
after EventCalendar stale failsafe (6.3).

In M9 the service implementation is a skeleton that always returns False.
Phase 7: implement ATR-multiplier spike detection using real market data.
"""

from __future__ import annotations

from typing import Protocol


class PriceAnomalyGuard(Protocol):
    """ATR-based price anomaly detector (6.3).

    Usage pattern:
      1. Evaluation framework calls record(instrument, atr) once per cycle
         after FeatureService.build().
      2. MetaDecider.Filter calls is_anomaly(instrument) to gate each candidate.

    Invariant (M9 skeleton): is_anomaly() always returns False.
    Phase 7: raise flash-halt (return True) when latest price deviates from
    recent mean by more than atr_spike_multiplier × atr_14.
    """

    def is_anomaly(self, instrument: str) -> bool:
        """Return True if price is in an anomalous state for *instrument*.

        M9 skeleton — always returns False.
        """
        ...

    def record(self, instrument: str, atr: float) -> None:
        """Update the internal ATR reading for *instrument*.

        M9 skeleton — no-op.
        Called by the evaluation framework before MetaDecider.decide().
        """
        ...
