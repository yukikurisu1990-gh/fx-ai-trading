# ruff: noqa: E501 -- cost prose
"""S0-1: cost economics。**方向・損益は計算しない**（spread と、動きの大きさ = vol / range だけ）。

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

from scripts.research.patsd_stage0 import data, prereg


def _r(x: float, d: int = 4) -> float | None:
    return round(float(x), d) if x is not None and np.isfinite(x) else None


def relative_spread(bars: pd.DataFrame) -> pd.Series:
    """終値時点の spread / mid。rollover の終値の bar は除く（そこで entry / exit しない）。"""
    keep = ~bars["close_rollover"].astype(bool)
    return (
        bars.loc[keep, "spread_close_pips"] * bars.loc[keep, "pip_size"] / bars.loc[keep, "mid_c"]
    ).astype(float)


def relative_true_range(bars: pd.DataFrame) -> pd.Series:
    prev = bars["mid_c"].shift(1)
    high = np.maximum(bars["mid_h"], prev)
    low = np.minimum(bars["mid_l"], prev)
    return ((high - low) / bars["mid_c"]).iloc[1:].astype(float)


def years_of_span() -> float:
    first = pd.Timestamp(prereg.FIRST_DAY)
    last = pd.Timestamp(prereg.LAST_DAY)
    return float((last - first).days + 1) / 365.25


def pair_economics(m15: pd.DataFrame) -> dict[str, Any]:
    years = years_of_span()
    daily = data.aggregate(m15, "D")
    daily_ret = np.log(daily["mid_c"]).diff().dropna()
    days_per_year = len(daily) / years
    sigma_annual = float(daily_ret.std(ddof=1) * math.sqrt(days_per_year))
    out: dict[str, Any] = {
        "sigma_annual": _r(sigma_annual, 5),
        "trading_days_per_year": _r(days_per_year, 2),
    }
    for timeframe in prereg.TIMEFRAMES:
        bars = data.aggregate(m15, timeframe)
        spread = relative_spread(bars)
        true_range = relative_true_range(bars)
        bar_ret = np.log(bars["mid_c"]).diff().dropna()
        bars_per_day = len(bars) / len(daily)
        hold_days = prereg.STANDARD_HOLD_DAYS[timeframe]
        hold_bars = max(hold_days * bars_per_day, 1.0)
        turnover = days_per_year / hold_days
        c = float(spread.median())
        out[timeframe] = {
            "bars": len(bars),
            "spread_bp": {
                q: _r(float(spread.quantile(p)) * 1e4, 3)
                for q, p in (
                    ("p10", 0.1),
                    ("p25", 0.25),
                    ("median", 0.5),
                    ("p75", 0.75),
                    ("p90", 0.9),
                )
            }
            | {"mean": _r(float(spread.mean()) * 1e4, 3)},
            "atr_bp_median": _r(float(true_range.median()) * 1e4, 3),
            "cost_to_atr": _r(c / float(true_range.median()), 4),
            "bar_vol_bp": _r(float(bar_ret.std(ddof=1)) * 1e4, 3),
            "standard_hold_days": hold_days,
            "hold_bars": _r(hold_bars, 2),
            "cost_to_hold_move": _r(c / (float(bar_ret.std(ddof=1)) * math.sqrt(hold_bars)), 4),
            "turnover_round_trips_per_year": _r(turnover, 2),
            "sharpe_drag": _r(turnover * c / sigma_annual, 4),
            "required_gross_for_net_1": _r(1.0 + turnover * c / sigma_annual, 4),
        }
    session = m15.loc[~m15["rollover"].astype(bool)].copy()
    session["rel"] = session["spread_close_pips"] * session["pip_size"] / session["mid_c"]
    out["session_spread_bp_median"] = {
        k: _r(float(v) * 1e4, 3) for k, v in session.groupby("session")["rel"].median().items()
    }
    all_rows = m15.copy()
    all_rows["rel"] = all_rows["spread_close_pips"] * all_rows["pip_size"] / all_rows["mid_c"]
    out["hour_spread_bp_median"] = {
        int(k): _r(float(v) * 1e4, 3)
        for k, v in all_rows.groupby(all_rows["ts"].dt.hour)["rel"].median().items()
    }
    return out


def f3_month_end_power(m15: pd.DataFrame) -> dict[str, Any]:
    """F3（月末）の検出力の算術。**事象の return の符号は見ない**（H1 の vol と事象の数だけ）。"""
    h1 = data.aggregate(m15, "H1")
    sigma_h1 = float(np.log(h1["mid_c"]).diff().dropna().std(ddof=1))
    first_eval = pd.Timestamp(prereg.FIRST_DAY) + pd.offsets.BDay(prereg.WARMUP_BUSINESS_DAYS)
    months = pd.period_range(first_eval, pd.Timestamp(prereg.LAST_DAY), freq="M")
    n_events = len(months) - 1
    spread = relative_spread(data.aggregate(m15, "H1"))
    mde = 2.8 * sigma_h1 / math.sqrt(max(n_events, 1))
    return {
        "month_end_events_after_warmup": n_events,
        "h1_vol_bp": _r(sigma_h1 * 1e4, 3),
        "mde_per_event_bp_one_pair": _r(mde * 1e4, 3),
        "h1_round_trip_cost_bp": _r(float(spread.median()) * 1e4, 3),
        "note": "1 pair・1 時間の窓。pair を跨いだ合算は相関で目減りする",
    }


def summarize(per_pair: dict[str, dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for timeframe in prereg.TIMEFRAMES:
        drags = np.array([p[timeframe]["sharpe_drag"] for p in per_pair.values()], dtype=float)
        ratio = np.array([p[timeframe]["cost_to_atr"] for p in per_pair.values()], dtype=float)
        spread = np.array(
            [p[timeframe]["spread_bp"]["median"] for p in per_pair.values()], dtype=float
        )
        summary[timeframe] = {
            "sharpe_drag_median": _r(float(np.median(drags))),
            "sharpe_drag_p25_p75": [
                _r(float(np.percentile(drags, 25))),
                _r(float(np.percentile(drags, 75))),
            ],
            "sharpe_drag_min_max": [_r(float(drags.min())), _r(float(drags.max()))],
            "pairs_with_drag_le_0_5": int((drags <= 0.5).sum()),
            "cost_to_atr_median": _r(float(np.median(ratio))),
            "cost_to_atr_min_max": [_r(float(ratio.min())), _r(float(ratio.max()))],
            "spread_bp_median_of_pairs": _r(float(np.median(spread)), 3),
        }
    h4 = summary[prereg.S0_1_TIMEFRAME]["sharpe_drag_median"]
    bands = prereg.S0_1_BANDS
    summary["classification"] = (
        "GREEN" if h4 <= bands["green_max"] else "AMBER" if h4 <= bands["amber_max"] else "RED"
    )
    summary["classified_on"] = f"{prereg.S0_1_TIMEFRAME} median Sharpe drag = {h4}"
    return summary


__all__ = ["f3_month_end_power", "pair_economics", "summarize"]
