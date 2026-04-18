"""EVEstimatorService — expected-value computation v0 (D3 §2.4.2 / M9).

Implements the EVEstimator Protocol.

v0 heuristic formula:
  value = p_win × avg_win − (1 − p_win) × avg_loss − cost.total

Where:
  p_win   = signal.confidence  (simplified: confidence treated as win probability)
  avg_win  = signal.tp          (take-profit distance as expected win size)
  avg_loss = signal.sl          (stop-loss distance as expected loss size)

confidence_interval: ±20% of |value|  (crude M9 approximation).
Phase 7: EVCalibrator v1 replaces this with calibrated probabilities.

Invariants:
  - Deterministic: same signal + same cost → same EVEstimate.
  - signal='no_trade' → value = 0.0, empty CI.
  - No DB access, no random, no clock.
"""

from __future__ import annotations

from fx_ai_trading.domain.ev import Cost, EVEstimate
from fx_ai_trading.domain.strategy import StrategySignal


class EVEstimatorService:
    """Heuristic EV estimator for M9 (D3 §2.4.2 v0).

    No constructor arguments required for v0.
    """

    def estimate(self, signal: StrategySignal, cost: Cost) -> EVEstimate:
        """Return EVEstimate for *signal* after deducting *cost*.

        For 'no_trade' signals the value and CI are both zero.
        """
        if signal.signal == "no_trade":
            return EVEstimate(
                value=0.0,
                confidence_interval=(0.0, 0.0),
                components={
                    "p_win": 0.0,
                    "avg_win": 0.0,
                    "avg_loss": 0.0,
                    "cost_total": cost.total,
                    "formula": "no_trade",
                },
            )

        p_win = signal.confidence
        avg_win = signal.tp
        avg_loss = signal.sl

        value = p_win * avg_win - (1 - p_win) * avg_loss - cost.total
        value = round(value, 8)

        ci_half = abs(value) * 0.20
        ci_lo = round(value - ci_half, 8)
        ci_hi = round(value + ci_half, 8)

        return EVEstimate(
            value=value,
            confidence_interval=(ci_lo, ci_hi),
            components={
                "p_win": round(p_win, 8),
                "avg_win": round(avg_win, 8),
                "avg_loss": round(avg_loss, 8),
                "cost_total": round(cost.total, 8),
                "formula": "v0_heuristic",
            },
        )
