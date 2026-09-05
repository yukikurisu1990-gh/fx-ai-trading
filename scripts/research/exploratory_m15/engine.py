"""The exploratory backtest engine: signals in, cost-inclusive metrics out.

`NON_DECISION_BEARING_EXPLORATORY_ONLY`.

The shape
---------

A strategy is a function from one pair's M15 bars to a **position series** in
`{-1, 0, +1}`, aligned to the bar whose close produced the decision. The engine
shifts it by one bar before it earns anything, so a signal computed from bar *t*
trades the *t+1* → *t+2* return. That single shift is what keeps same-bar target
leakage out, and every feature helper here is causal by construction: rolling
windows only, `shift(1)` on anything that touches the current bar's close.

Cost
----

`EXPLORATORY_ASSUMPTION`. R1's `cost_table` is excluded from decision-bearing
results and the eligible-bar rate derived from it is not an adoption basis, so
none of it is used here. Instead the cost of a position change is taken from the
**observed quoted spread on the bar the trade happens**, plus a flat pad:

    per_side_cost_pips = (spread_close_pips + SLIPPAGE_PAD_PIPS) / 2

charged on every unit of `|position change|`, so a full round trip pays one whole
spread plus one pad, and a flip from long to short pays two. **The halving is not
a discount.** Returns here are computed on the **mid**, and a buy fills at the ask
— half a spread above mid — while the matching sell fills at the bid, half a
spread below. Charging a whole spread per side would double-count. A first
drafting did exactly that and made every result twice as bad as the assumption
warranted; the correction is stated because it moves every number in this
package.

The pad is a research assumption, not the frozen cost schema's cell; the numbers
happen to be of the same order, which is why the label matters.

Sensitivity multipliers of 1.00 / 1.25 / 1.50 are reported for every result. A
strategy that only survives at the base assumption is not interesting.

What the metrics are, and are not
---------------------------------

Returns are **pip-denominated per unit position**, not currency, so pairs are
comparable without an FX conversion this package has no authority to define. The
"Sharpe-like" number is the annualised mean/σ of per-bar net pip returns; it is a
ranking device, not a Sharpe ratio, and it is deliberately never the only column.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Final

import numpy as np
import pandas as pd

#: `EXPLORATORY_ASSUMPTION`: the flat pad added to the observed spread.
SLIPPAGE_PAD_PIPS: Final[float] = 0.5
COST_MULTIPLIERS: Final[tuple[float, ...]] = (1.0, 1.25, 1.5)
#: M15 bars in a year, for annualising. 4 per hour, 24 hours, ~260 weekdays.
BARS_PER_YEAR: Final[float] = 4 * 24 * 260.0

COST_LABEL: Final[str] = (
    "EXPLORATORY_ASSUMPTION: per-side cost = (observed spread_close_pips at the trading "
    f"bar + {SLIPPAGE_PAD_PIPS} pip pad) / 2, charged per unit of |position change|, so a "
    "round trip pays one full spread plus one pad and a long/short flip pays two. Returns "
    "are mid-based, which is why the per-side charge is half. Not the frozen cost schema, "
    "and not R1's excluded cost_table."
)


# ---------------------------------------------------------------------------
# causal feature helpers
# ---------------------------------------------------------------------------


def ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False, min_periods=span).mean()


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    return 100.0 - 100.0 / (1.0 + rs)


def atr_pips(bars: pd.DataFrame, period: int = 14) -> pd.Series:
    """Wilder ATR on the mid series, in pips."""
    high, low, close = bars["mid_h"], bars["mid_l"], bars["mid_c"]
    prior = close.shift(1)
    true_range = pd.concat([high - low, (high - prior).abs(), (low - prior).abs()], axis=1).max(
        axis=1
    )
    return (
        true_range.ewm(alpha=1 / period, adjust=False, min_periods=period).mean() / bars["pip_size"]
    )


def zscore(series: pd.Series, window: int) -> pd.Series:
    mean = series.rolling(window, min_periods=window).mean()
    std = series.rolling(window, min_periods=window).std()
    return (series - mean) / std.replace(0.0, np.nan)


def donchian(bars: pd.DataFrame, window: int) -> tuple[pd.Series, pd.Series]:
    """Prior-window high and low, **excluding** the current bar."""
    high = bars["mid_h"].rolling(window, min_periods=window).max().shift(1)
    low = bars["mid_l"].rolling(window, min_periods=window).min().shift(1)
    return high, low


def adx(bars: pd.DataFrame, period: int = 14) -> pd.Series:
    high, low = bars["mid_h"], bars["mid_l"]
    up = high.diff()
    down = -low.diff()
    plus_dm = np.where((up > down) & (up > 0), up, 0.0)
    minus_dm = np.where((down > up) & (down > 0), down, 0.0)
    tr = atr_pips(bars, period) * bars["pip_size"]
    alpha = 1 / period
    plus = pd.Series(plus_dm, index=bars.index).ewm(alpha=alpha, adjust=False).mean() / tr
    minus = pd.Series(minus_dm, index=bars.index).ewm(alpha=alpha, adjust=False).mean() / tr
    dx = ((plus - minus).abs() / (plus + minus).replace(0.0, np.nan)) * 100.0
    return dx.ewm(alpha=alpha, adjust=False).mean()


def higher_timeframe(bars: pd.DataFrame, bars_per_period: int = 4) -> pd.DataFrame:
    """An H1 view built by folding M15, carried forward causally.

    No second data read: H1 is four M15 buckets. The result is shifted so a bar
    only ever sees an H1 candle that has already closed.
    """
    group = np.arange(len(bars)) // bars_per_period
    frame = pd.DataFrame(
        {
            "htf_close": bars.groupby(group)["mid_c"].transform("last"),
            "htf_high": bars.groupby(group)["mid_h"].transform("max"),
            "htf_low": bars.groupby(group)["mid_l"].transform("min"),
        }
    )
    #: shift by a whole period, so the current (still forming) candle is unseen
    return frame.shift(bars_per_period)


# ---------------------------------------------------------------------------
# evaluation
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Result:
    """One strategy on one pair, cost-inclusive. Exploratory only."""

    name: str
    pair: str
    metrics: dict[str, Any]
    equity: pd.Series = field(repr=False, default_factory=pd.Series)
    net: pd.Series = field(repr=False, default_factory=pd.Series)
    position: pd.Series = field(repr=False, default_factory=pd.Series)


def evaluate(
    bars: pd.DataFrame,
    position: pd.Series,
    *,
    name: str,
    pair: str,
    cost_multiplier: float = 1.0,
) -> Result:
    """Turn a decision series into cost-inclusive pip returns and metrics.

    `position` is the decision taken **at** each bar's close. It is shifted once
    here, so nothing earns on the bar that produced it.
    """
    held = position.shift(1).fillna(0.0)
    pip = bars["pip_size"]
    forward = (bars["mid_c"].shift(-1) - bars["mid_c"]) / pip
    gross = held * forward
    turnover = held.diff().abs().fillna(held.abs())
    #: half a spread per side: mid-based returns, ask on the way in, bid on the
    #: way out. A round trip therefore pays one full spread plus one pad.
    unit_cost = (bars["spread_close_pips"] + SLIPPAGE_PAD_PIPS) / 2.0 * cost_multiplier
    cost = turnover * unit_cost
    net = (gross - cost).fillna(0.0)

    trades = int((turnover > 0).sum())
    entries = held.ne(held.shift(1)) & held.ne(0)
    per_trade = _per_trade_pnl(held, net)
    equity = net.cumsum()
    drawdown = equity - equity.cummax()
    std = float(net.std())
    metrics = {
        "strategy": name,
        "pair": pair,
        "cost_multiplier": cost_multiplier,
        "bars": int(len(bars)),
        "net_pips": float(net.sum()),
        "gross_pips": float(gross.sum()),
        "cost_pips": float(cost.sum()),
        "sharpe_like": float(net.mean() / std * np.sqrt(BARS_PER_YEAR)) if std > 0 else 0.0,
        "max_drawdown_pips": float(drawdown.min()),
        "trades": trades,
        "entries": int(entries.sum()),
        "exposure": float(held.abs().mean()),
        "turnover_per_year": float(turnover.sum() / max(len(bars), 1) * BARS_PER_YEAR),
        "win_rate": float((per_trade > 0).mean()) if len(per_trade) else float("nan"),
        "profit_factor": _profit_factor(per_trade),
        "avg_trade_pips": float(per_trade.mean()) if len(per_trade) else float("nan"),
        "n_closed_trades": int(len(per_trade)),
    }
    return Result(name=name, pair=pair, metrics=metrics, equity=equity, net=net, position=held)


def _per_trade_pnl(held: pd.Series, net: pd.Series) -> np.ndarray:
    """Net pips grouped by contiguous non-zero holding at one sign."""
    sign = held.to_numpy()
    values = net.to_numpy()
    out: list[float] = []
    current = 0.0
    active = 0.0
    for position, value in zip(sign, values, strict=True):
        if position != active:
            if active != 0.0:
                out.append(current)
            current = 0.0
            active = position
        if active != 0.0:
            current += value
    if active != 0.0:
        out.append(current)
    return np.asarray(out, dtype=float)


def _profit_factor(per_trade: np.ndarray) -> float:
    if not len(per_trade):
        return float("nan")
    wins = per_trade[per_trade > 0].sum()
    losses = -per_trade[per_trade < 0].sum()
    return float(wins / losses) if losses > 0 else float("inf")


def stability(net: pd.Series, ts: pd.Series, *, periods: int = 4) -> dict[str, Any]:
    """Sign consistency across equal chronological slices."""
    chunks = np.array_split(np.arange(len(net)), periods)
    sums = [float(net.iloc[chunk].sum()) for chunk in chunks if len(chunk)]
    positive = sum(1 for value in sums if value > 0)
    return {
        "period_net_pips": [round(value, 1) for value in sums],
        "periods_positive": positive,
        "periods": len(sums),
        "worst_period_pips": round(min(sums), 1) if sums else float("nan"),
    }


__all__ = [
    "BARS_PER_YEAR",
    "COST_LABEL",
    "COST_MULTIPLIERS",
    "SLIPPAGE_PAD_PIPS",
    "Result",
    "adx",
    "atr_pips",
    "donchian",
    "ema",
    "evaluate",
    "higher_timeframe",
    "rsi",
    "stability",
    "zscore",
]
