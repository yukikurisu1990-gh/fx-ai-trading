"""ATR-based regime classifier with hysteresis (Phase 9.7).

Classifies market state as one of:
  'trend'    — moderate ATR; directional movement
  'range'    — low ATR; consolidation
  'high_vol' — elevated ATR; news or shock event

Hysteresis: regime switches only after N consecutive candles in the
candidate regime, preventing noise-driven churn.
"""

from __future__ import annotations

REGIME_TREND = "trend"
REGIME_RANGE = "range"
REGIME_HIGH_VOL = "high_vol"

_ALL_REGIMES = frozenset({REGIME_TREND, REGIME_RANGE, REGIME_HIGH_VOL})


def _compute_atr(candles: list[dict], period: int) -> list[float]:
    """Return simple-moving-average ATR series from OHLC candles.

    Returns one ATR value per candle starting at index *period* (inclusive),
    so len(result) == max(0, len(candles) - period).
    """
    if len(candles) < period + 1:
        return []

    trs: list[float] = []
    for i in range(1, len(candles)):
        high = float(candles[i]["high"])
        low = float(candles[i]["low"])
        prev_close = float(candles[i - 1]["close"])
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        trs.append(tr)

    if len(trs) < period:
        return []

    return [sum(trs[i - period + 1 : i + 1]) / period for i in range(period - 1, len(trs))]


def _raw_regime(
    candles: list[dict],
    atr_period: int,
    high_vol_multiplier: float,
    range_multiplier: float,
) -> str | None:
    """Classify the most recent candle without hysteresis.

    Returns None when there is insufficient data (< atr_period + 2 candles).
    """
    atrs = _compute_atr(candles, atr_period)
    if len(atrs) < 2:
        return None

    current_atr = atrs[-1]
    baseline_atr = sum(atrs) / len(atrs)

    if baseline_atr == 0.0:
        return None

    ratio = current_atr / baseline_atr
    if ratio >= high_vol_multiplier:
        return REGIME_HIGH_VOL
    if ratio <= range_multiplier:
        return REGIME_RANGE
    return REGIME_TREND


class ATRRegimeClassifier:
    """Stateful ATR regime classifier with hysteresis.

    Args:
        atr_period: Window size for ATR computation (default 14).
        high_vol_multiplier: current/baseline ATR ratio threshold for 'high_vol'.
        range_multiplier: current/baseline ATR ratio threshold for 'range'.
        hysteresis_periods: Consecutive candles required to confirm a regime switch.
    """

    def __init__(
        self,
        atr_period: int = 14,
        high_vol_multiplier: float = 1.5,
        range_multiplier: float = 0.7,
        hysteresis_periods: int = 3,
    ) -> None:
        if atr_period < 1:
            raise ValueError(f"atr_period must be >= 1, got {atr_period}")
        if hysteresis_periods < 1:
            raise ValueError(f"hysteresis_periods must be >= 1, got {hysteresis_periods}")

        self._atr_period = atr_period
        self._high_vol_multiplier = high_vol_multiplier
        self._range_multiplier = range_multiplier
        self._hysteresis_periods = hysteresis_periods

        self._current_regime: str | None = None
        self._candidate: str | None = None
        self._consecutive: int = 0

    @property
    def regime(self) -> str | None:
        """Current stable regime after hysteresis, or None if not yet established."""
        return self._current_regime

    def update(self, candles: list[dict]) -> str | None:
        """Process *candles* and return the current stable regime.

        Classifies the most recent candle's raw regime, then applies
        hysteresis: only promotes to stable when the same raw regime
        has been observed for *hysteresis_periods* consecutive updates.

        Returns None until the first stable regime is confirmed.
        """
        raw = _raw_regime(
            candles,
            self._atr_period,
            self._high_vol_multiplier,
            self._range_multiplier,
        )
        if raw is None:
            return self._current_regime

        if raw == self._candidate:
            self._consecutive += 1
        else:
            self._candidate = raw
            self._consecutive = 1

        if self._consecutive >= self._hysteresis_periods:
            self._current_regime = raw

        return self._current_regime


__all__ = [
    "ATRRegimeClassifier",
    "REGIME_HIGH_VOL",
    "REGIME_RANGE",
    "REGIME_TREND",
]
