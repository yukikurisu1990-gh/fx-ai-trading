"""TSS (Trade Suitability Score) calculator (M20).

TSS is a normalised [0, 1] score representing how suitable an instrument is for
trading in the current market state.  Iteration 2 uses a linear combination of
signal confidence and directional consensus from strategy_signals rows.

Supported instruments (Iteration 2): USDJPY, EURUSD, GBPUSD.
Full instrument coverage and weight tuning are Iteration 3.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TSSResult:
    score: float
    components: list[dict]
    horizon_min: int
    direction: str  # 'buy' | 'sell' | 'no_trade'


_SUPPORTED_INSTRUMENTS = frozenset({"USDJPY", "EURUSD", "GBPUSD"})
_HORIZON_MIN = 60


class TSSCalculator:
    """Compute TSS for a single instrument from strategy_signals rows.

    Each signal row must have at minimum:
      - signal_direction: str  ('buy' | 'sell' | 'no_trade')
      - confidence: float | None  (0.0–1.0)
    """

    INSTRUMENTS = _SUPPORTED_INSTRUMENTS
    HORIZON_MIN = _HORIZON_MIN

    def __init__(
        self,
        weight_confidence: float = 0.7,
        weight_direction_strength: float = 0.3,
    ) -> None:
        self._w_conf = weight_confidence
        self._w_dir = weight_direction_strength

    def compute(self, instrument: str, signals: list[dict]) -> TSSResult | None:
        """Return TSSResult or None if instrument unsupported / no signals."""
        if instrument not in _SUPPORTED_INSTRUMENTS:
            return None
        if not signals:
            return None

        buy_conf: float = 0.0
        sell_conf: float = 0.0
        for s in signals:
            conf = float(s.get("confidence") or 0.0)
            direction = s.get("signal_direction", "no_trade")
            if direction == "buy":
                buy_conf += conf
            elif direction == "sell":
                sell_conf += conf

        total_conf = buy_conf + sell_conf
        if total_conf == 0.0:
            return None

        direction = "buy" if buy_conf >= sell_conf else "sell"
        dominant = max(buy_conf, sell_conf)
        n = max(len(signals), 1)
        avg_conf = dominant / n
        dir_strength = dominant / total_conf

        score = self._w_conf * avg_conf + self._w_dir * dir_strength
        score = round(min(max(score, 0.0), 1.0), 4)

        components = [
            {"name": "confidence", "value": round(avg_conf, 4), "weight": self._w_conf},
            {
                "name": "direction_strength",
                "value": round(dir_strength, 4),
                "weight": self._w_dir,
            },
        ]
        return TSSResult(
            score=score,
            components=components,
            horizon_min=_HORIZON_MIN,
            direction=direction,
        )
