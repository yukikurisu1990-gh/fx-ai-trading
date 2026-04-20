"""Stub StrategyEvaluator implementations — Phase 6 Cycle 6.3.

Two stubs:

  AlwaysNoTradeStrategy
      Returns signal='no_trade' every time.  Serves as the control
      baseline that proves the pipeline can carry no_trade rows
      alongside trade rows.

  DeterministicTrendStrategy
      Always produces a trade direction ('long' or 'short').  Direction
      is derived deterministically from (cycle_id, instrument) so tests
      and re-runs are reproducible.  All numeric fields are populated
      with realistic dummy values — confidence is intentionally well
      above a plausible Meta threshold (0.70) so that the Cycle 6.4
      Meta pass is guaranteed to emit at least one trading_signal.

Both stubs are pure-functional: ``evaluate()`` has no DB access and
no hidden state.  They satisfy the ``StrategyEvaluator`` Protocol.

Neither stub reads features for decision-making.  That is delegated
to real strategies.  Here we only demonstrate the full StrategyOutput
shape and ensure downstream cycles have non-degenerate inputs.
"""

from __future__ import annotations

import hashlib

from fx_ai_trading.domain.feature import FeatureSet
from fx_ai_trading.domain.strategy import StrategyContext, StrategySignal


class AlwaysNoTradeStrategy:
    """Control stub: always returns no_trade with confidence 0.0."""

    STRATEGY_ID = "stub.always_no_trade.v1"
    STRATEGY_TYPE = "stub"
    STRATEGY_VERSION = "1.0.0"

    def evaluate(
        self,
        instrument: str,  # noqa: ARG002
        features: FeatureSet,  # noqa: ARG002
        context: StrategyContext,  # noqa: ARG002
    ) -> StrategySignal:
        return StrategySignal(
            strategy_id=self.STRATEGY_ID,
            strategy_type=self.STRATEGY_TYPE,
            strategy_version=self.STRATEGY_VERSION,
            signal="no_trade",
            confidence=0.0,
            ev_before_cost=0.0,
            ev_after_cost=0.0,
            tp=0.0,
            sl=0.0,
            holding_time_seconds=0,
            enabled=True,
        )


class DeterministicTrendStrategy:
    """Always-trading stub: emits 'long' or 'short' by hash of (cycle, instrument).

    Field values:
      confidence          = 0.70 (chosen > any plausible Meta threshold
                            so that Cycle 6.4 is guaranteed to produce
                            at least one trading_signal)
      ev_before_cost      = 15.0 pips
      ev_after_cost       = 12.0 pips (assumes ~3 pip cost/spread)
      tp                  = 20.0 pips in favorable direction
      sl                  = 10.0 pips in adverse direction
      holding_time_seconds= 3600 (1h)

    The hash-based direction choice is deterministic per (cycle_id,
    instrument), so tests and replays are reproducible.  Cycle 6.4
    tests can pin cycle_id to get a known direction.
    """

    STRATEGY_ID = "stub.deterministic_trend.v1"
    STRATEGY_TYPE = "stub"
    STRATEGY_VERSION = "1.0.0"

    CONFIDENCE = 0.70
    EV_BEFORE_COST = 15.0
    EV_AFTER_COST = 12.0
    TP = 20.0
    SL = 10.0
    HOLDING_TIME_SECONDS = 3600

    def evaluate(
        self,
        instrument: str,
        features: FeatureSet,  # noqa: ARG002
        context: StrategyContext,
    ) -> StrategySignal:
        direction = _pick_direction(cycle_id=context.cycle_id, instrument=instrument)
        return StrategySignal(
            strategy_id=self.STRATEGY_ID,
            strategy_type=self.STRATEGY_TYPE,
            strategy_version=self.STRATEGY_VERSION,
            signal=direction,
            confidence=self.CONFIDENCE,
            ev_before_cost=self.EV_BEFORE_COST,
            ev_after_cost=self.EV_AFTER_COST,
            tp=self.TP,
            sl=self.SL,
            holding_time_seconds=self.HOLDING_TIME_SECONDS,
            enabled=True,
        )


def _pick_direction(*, cycle_id: str, instrument: str) -> str:
    """Deterministic long/short picker.

    Uses SHA-256 of "cycle_id|instrument" -> parity of first byte.  Any
    hash is fine; we need only (reproducibility, uniform distribution
    across cycles, no external dependency).
    """
    digest = hashlib.sha256(f"{cycle_id}|{instrument}".encode()).digest()
    return "long" if digest[0] % 2 == 0 else "short"


__all__ = [
    "AlwaysNoTradeStrategy",
    "DeterministicTrendStrategy",
]
