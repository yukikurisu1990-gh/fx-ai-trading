"""The strategy families for Round 1. `NON_DECISION_BEARING_EXPLORATORY_ONLY`.

Every function returns a position series in `{-1, 0, +1}` **decided at the bar's
close**; `engine.evaluate` shifts it before it earns anything. Nothing here reads
`mid_c` of a future bar, and every rolling window is closed at the current bar or
earlier — the `donchian` helper excludes the current bar on purpose, because a
breakout tested against a channel that already contains the breakout is the
classic way to invent an edge.

Incomplete buckets are left in the series rather than dropped. Ruling 3 makes
them diagnostics-only for *labels*; here they are simply bars a live system would
also have seen, and removing them would quietly assume a data feed nobody has.
Rollover bars are excluded from **entry** because their quotes are the day's
widest and the cost model charges the observed spread.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from scripts.research.exploratory_m15 import engine


def _entryable(bars: pd.DataFrame) -> pd.Series:
    """Bars a position may be opened on: not rollover, spread finite."""
    return (~bars["rollover"]) & bars["spread_close_pips"].notna()


def _hold(raw: pd.Series, bars: pd.DataFrame) -> pd.Series:
    """Carry a signal forward, but never *open* on a rollover bar."""
    blocked = ~_entryable(bars)
    signal = raw.copy()
    signal[blocked & (raw != raw.shift(1))] = np.nan
    return signal.ffill().fillna(0.0)


# --- A. trend / momentum ---------------------------------------------------


def ema_crossover(bars: pd.DataFrame, fast: int = 12, slow: int = 48) -> pd.Series:
    quick, slowly = engine.ema(bars["mid_c"], fast), engine.ema(bars["mid_c"], slow)
    raw = pd.Series(np.sign(quick - slowly), index=bars.index).fillna(0.0)
    return _hold(raw, bars)


def ema_slope(bars: pd.DataFrame, span: int = 48, lookback: int = 8) -> pd.Series:
    line = engine.ema(bars["mid_c"], span)
    raw = pd.Series(np.sign(line - line.shift(lookback)), index=bars.index).fillna(0.0)
    return _hold(raw, bars)


def multi_horizon_momentum(bars: pd.DataFrame, horizons=(16, 48, 96)) -> pd.Series:
    close = bars["mid_c"]
    votes = sum(np.sign(close - close.shift(h)).fillna(0.0) for h in horizons)
    raw = pd.Series(np.where(np.abs(votes) == len(horizons), np.sign(votes), 0.0), index=bars.index)
    return _hold(raw, bars)


def adx_trend(bars: pd.DataFrame, period: int = 14, floor: float = 25.0) -> pd.Series:
    strength = engine.adx(bars, period)
    direction = np.sign(engine.ema(bars["mid_c"], 24) - engine.ema(bars["mid_c"], 96))
    raw = pd.Series(np.where(strength > floor, direction, 0.0), index=bars.index).fillna(0.0)
    return _hold(raw, bars)


# --- B. breakout -----------------------------------------------------------


def donchian_breakout(bars: pd.DataFrame, window: int = 48) -> pd.Series:
    high, low = engine.donchian(bars, window)
    raw = pd.Series(0.0, index=bars.index)
    raw[bars["mid_c"] > high] = 1.0
    raw[bars["mid_c"] < low] = -1.0
    return _hold(raw.replace(0.0, np.nan), bars)


def volatility_adjusted_breakout(bars: pd.DataFrame, window: int = 48, k: float = 0.5) -> pd.Series:
    high, low = engine.donchian(bars, window)
    pad = engine.atr_pips(bars, 14).shift(1) * bars["pip_size"] * k
    raw = pd.Series(0.0, index=bars.index)
    raw[bars["mid_c"] > high + pad] = 1.0
    raw[bars["mid_c"] < low - pad] = -1.0
    return _hold(raw.replace(0.0, np.nan), bars)


def range_breakout(bars: pd.DataFrame, window: int = 24, exit_window: int = 12) -> pd.Series:
    """Enter on a channel break, leave on the opposite shorter channel."""
    high, low = engine.donchian(bars, window)
    exit_high, exit_low = engine.donchian(bars, exit_window)
    state = np.zeros(len(bars))
    close = bars["mid_c"].to_numpy()
    hi, lo = high.to_numpy(), low.to_numpy()
    xhi, xlo = exit_high.to_numpy(), exit_low.to_numpy()
    current = 0.0
    for i in range(len(bars)):
        if current == 0.0:
            if not np.isnan(hi[i]) and close[i] > hi[i]:
                current = 1.0
            elif not np.isnan(lo[i]) and close[i] < lo[i]:
                current = -1.0
        elif (
            current > 0
            and not np.isnan(xlo[i])
            and close[i] < xlo[i]
            or current < 0
            and not np.isnan(xhi[i])
            and close[i] > xhi[i]
        ):
            current = 0.0
        state[i] = current
    return _hold(pd.Series(state, index=bars.index), bars)


# --- C. mean reversion -----------------------------------------------------


def rsi_reversion(
    bars: pd.DataFrame, period: int = 14, low: float = 30.0, high: float = 70.0
) -> pd.Series:
    value = engine.rsi(bars["mid_c"], period)
    raw = pd.Series(np.nan, index=bars.index)
    raw[value < low] = 1.0
    raw[value > high] = -1.0
    raw[(value > 45.0) & (value < 55.0)] = 0.0
    return _hold(raw, bars)


def zscore_reversion(
    bars: pd.DataFrame, window: int = 48, entry: float = 2.0, exit_at: float = 0.5
) -> pd.Series:
    score = engine.zscore(bars["mid_c"], window)
    raw = pd.Series(np.nan, index=bars.index)
    raw[score < -entry] = 1.0
    raw[score > entry] = -1.0
    raw[score.abs() < exit_at] = 0.0
    return _hold(raw, bars)


def overextension(bars: pd.DataFrame, horizon: int = 8, k: float = 1.5) -> pd.Series:
    move = (bars["mid_c"] - bars["mid_c"].shift(horizon)) / bars["pip_size"]
    band = engine.atr_pips(bars, 14).shift(1) * k
    raw = pd.Series(np.nan, index=bars.index)
    raw[move < -band] = 1.0
    raw[move > band] = -1.0
    raw[move.abs() < band * 0.25] = 0.0
    return _hold(raw, bars)


# --- D. volatility / regime (used as filters as well as signals) -----------


def atr_regime(bars: pd.DataFrame, period: int = 14, window: int = 480) -> pd.Series:
    """+1 in the high-volatility regime, -1 in the low. A filter, not a signal."""
    value = engine.atr_pips(bars, period)
    median = value.rolling(window, min_periods=window // 2).median()
    return pd.Series(np.sign(value - median), index=bars.index).fillna(0.0)


def trend_vs_range(bars: pd.DataFrame, period: int = 14, floor: float = 25.0) -> pd.Series:
    return (engine.adx(bars, period) > floor).astype(float).fillna(0.0)


def filtered(signal: pd.Series, mask: pd.Series) -> pd.Series:
    return (signal * mask.astype(float)).fillna(0.0)


# --- E. session ------------------------------------------------------------


def session_mask(bars: pd.DataFrame, sessions) -> pd.Series:
    return bars["session"].isin(list(sessions)).astype(float)


# --- F. multi-timeframe ----------------------------------------------------


def mtf_agreement(
    bars: pd.DataFrame, fast: int = 12, slow: int = 48, htf_span: int = 24
) -> pd.Series:
    """M15 crossover, taken only when the H1 trend agrees."""
    entry = ema_crossover(bars, fast, slow)
    htf = engine.higher_timeframe(bars)
    htf_trend = np.sign(htf["htf_close"] - engine.ema(htf["htf_close"], htf_span))
    agree = pd.Series(htf_trend, index=bars.index).fillna(0.0)
    return pd.Series(np.where(entry == agree, entry, 0.0), index=bars.index)


def htf_context_breakout(bars: pd.DataFrame, window: int = 48, htf_span: int = 24) -> pd.Series:
    entry = donchian_breakout(bars, window)
    htf = engine.higher_timeframe(bars)
    htf_trend = pd.Series(
        np.sign(htf["htf_close"] - engine.ema(htf["htf_close"], htf_span)), index=bars.index
    ).fillna(0.0)
    return pd.Series(np.where(entry == htf_trend, entry, 0.0), index=bars.index)


# --- the registry Round 1 runs --------------------------------------------

BASELINES = {
    "baseline_ema_12_48": (ema_crossover, {}),
    "baseline_donchian_48": (donchian_breakout, {}),
    "baseline_rsi_14_30_70": (rsi_reversion, {}),
}

FAMILIES: dict[str, dict[str, tuple]] = {
    "A_trend": {
        "A_ema_cross_12_48": (ema_crossover, {}),
        "A_ema_cross_24_96": (ema_crossover, {"fast": 24, "slow": 96}),
        "A_ema_slope_48_8": (ema_slope, {}),
        "A_multi_horizon": (multi_horizon_momentum, {}),
        "A_adx_trend_25": (adx_trend, {}),
    },
    "B_breakout": {
        "B_donchian_48": (donchian_breakout, {}),
        "B_donchian_96": (donchian_breakout, {"window": 96}),
        "B_vol_adj_breakout": (volatility_adjusted_breakout, {}),
        "B_range_breakout_24_12": (range_breakout, {}),
    },
    "C_reversion": {
        "C_rsi_14_30_70": (rsi_reversion, {}),
        "C_rsi_14_20_80": (rsi_reversion, {"low": 20.0, "high": 80.0}),
        "C_zscore_48_2": (zscore_reversion, {}),
        "C_overextension_8": (overextension, {}),
    },
    "F_multi_timeframe": {
        "F_mtf_agreement": (mtf_agreement, {}),
        "F_htf_context_breakout": (htf_context_breakout, {}),
    },
}


__all__ = [
    "BASELINES",
    "FAMILIES",
    "adx_trend",
    "atr_regime",
    "donchian_breakout",
    "ema_crossover",
    "ema_slope",
    "filtered",
    "htf_context_breakout",
    "mtf_agreement",
    "multi_horizon_momentum",
    "overextension",
    "range_breakout",
    "rsi_reversion",
    "session_mask",
    "trend_vs_range",
    "volatility_adjusted_breakout",
    "zscore_reversion",
]


# --- C2. the finding: low-turnover reversal at a ~24h horizon ---------------
#
# The IC scan that motivated this: every return/oscillator feature has a
# **negative** information coefficient against forward returns at every horizon
# tested, and the sign is consistent across pairs. The strongest cell is the
# 96-bar (24h) past return against the 96-bar forward return -- mean IC -7.9%
# with **all twenty pairs** negative. Mean |96-bar move| is 38 pips against a
# ~3 pip round trip, so the horizon is where cost stops dominating.
#
# The families above lost to cost because they re-decide every bar. These decide
# on a fixed grid and hold, which is the only lever that moves turnover by an
# order of magnitude.


def reversal_hold(
    bars: pd.DataFrame,
    lookback: int = 96,
    hold: int = 96,
    entry_z: float = 1.0,
    z_window: int = 480,
) -> pd.Series:
    """Fade the last `lookback` bars' move, decide every `hold` bars, then hold.

    `entry_z` is selectivity: the move is scored against its own recent
    distribution and only extremes are taken. A sign-only version trades every
    grid point and earns about the cost; the whole question is whether picking
    the tail pays for itself.
    """
    move = (bars["mid_c"] - bars["mid_c"].shift(lookback)) / bars["pip_size"]
    score = engine.zscore(move, z_window)
    raw = pd.Series(0.0, index=bars.index)
    raw[score > entry_z] = -1.0
    raw[score < -entry_z] = 1.0
    #: decide only on the grid; between grid points the last decision stands
    grid = np.zeros(len(bars), dtype=bool)
    grid[::hold] = True
    decided = raw.where(pd.Series(grid, index=bars.index)).ffill().fillna(0.0)
    return _hold(decided, bars)


def reversal_hold_filtered(
    bars: pd.DataFrame,
    lookback: int = 96,
    hold: int = 96,
    entry_z: float = 1.0,
    max_spread_pips: float = 4.0,
) -> pd.Series:
    """The same, refusing to open where the quoted spread is wide."""
    signal = reversal_hold(bars, lookback, hold, entry_z)
    affordable = bars["spread_close_pips"] <= max_spread_pips
    return pd.Series(np.where(affordable, signal, 0.0), index=bars.index).ffill().fillna(0.0)


REVERSAL: dict[str, tuple] = {
    "C2_rev_96h96_z0": (reversal_hold, {"entry_z": 0.0}),
    "C2_rev_96h96_z1": (reversal_hold, {"entry_z": 1.0}),
    "C2_rev_96h96_z1.5": (reversal_hold, {"entry_z": 1.5}),
    "C2_rev_192h96_z1": (reversal_hold, {"lookback": 192, "entry_z": 1.0}),
    "C2_rev_96h192_z1": (reversal_hold, {"hold": 192, "entry_z": 1.0}),
    "C2_rev_48h48_z1": (reversal_hold, {"lookback": 48, "hold": 48, "entry_z": 1.0}),
    "C2_rev_192h192_z1": (reversal_hold, {"lookback": 192, "hold": 192, "entry_z": 1.0}),
    "C2_rev_96h96_z1_sprd": (reversal_hold_filtered, {}),
}
