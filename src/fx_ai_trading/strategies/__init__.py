"""Strategy stubs — Phase 6 Cycle 6.3.

This module hosts pre-MVP Strategy implementations used to bootstrap
the full decision chain (Strategy -> Meta -> Execution).  The stubs
are intentionally minimal but MUST satisfy two contracts:

  1. At least one stub produces non-no_trade signals every cycle so
     the Meta cycle has something to score (see DeterministicTrendStrategy).
  2. Every stub populates the full ``StrategySignal`` field set
     (confidence, ev_before_cost, ev_after_cost, tp, sl,
      holding_time_seconds, enabled) — dummy values are allowed but
     must be concrete numbers, not None.

Real strategies (MA cross, breakout, EMA filter, etc.) replace these
stubs cycle-by-cycle without touching the Protocol or the runner.
"""

from .stubs import AlwaysNoTradeStrategy, DeterministicTrendStrategy

__all__ = ["AlwaysNoTradeStrategy", "DeterministicTrendStrategy"]
