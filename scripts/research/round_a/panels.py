"""The three seen panels, and the derived columns both T1 and T2 need.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

Everything here is loaded from parquet caches that already exist. There is no
reader, no archive path and no span bound in this file, so no future edit to it
can widen a data scope — the three `load` functions it calls each carry their own
guard and each refuses everything outside its own window.

Derived columns are computed once per pair per panel and shared by T1 and T2, so
the two answer their questions about the same bars with the same state
definitions. Every one is a backward window at `t`; the only forward-looking
quantities in Round A are T1's excursions, which live in `atlas.py` and are
prohibited from entering a decision.
"""

from __future__ import annotations

from typing import Any, Final

import numpy as np
import pandas as pd

from scripts.research.exploratory_m15 import PAIRS, engine, round2
from scripts.research.exploratory_m15 import bars as development
from scripts.research.exploratory_m15 import momentum as momentum_panel
from scripts.research.exploratory_m15 import supplemental as supplemental_panel

#: Panel id -> (loader, span). The spans are copied from each route's own
#: constants rather than restated, so a panel cannot silently drift from the
#: window its guard enforces.
LOADERS: Final[dict[str, Any]] = {
    "momentum_2021_2023": (
        momentum_panel.load,
        momentum_panel.MOMENTUM_START_UTC,
        momentum_panel.MOMENTUM_END_UTC,
    ),
    "supplemental_2023_2025": (
        supplemental_panel.load,
        supplemental_panel.SUPPLEMENTAL_START_UTC,
        supplemental_panel.SUPPLEMENTAL_END_UTC,
    ),
    "development_2025": (development.load, "2025-04-25", "2025-12-28"),
}

BARS_PER_DAY: Final[int] = 96
JPY_PAIRS: Final[tuple[str, ...]] = tuple(p for p in PAIRS if "JPY" in p)
NON_JPY_PAIRS: Final[tuple[str, ...]] = tuple(p for p in PAIRS if "JPY" not in p)
BLOCS: Final[dict[str, tuple[str, ...]]] = {
    "ALL": tuple(PAIRS),
    "JPY": JPY_PAIRS,
    "non_JPY": NON_JPY_PAIRS,
}

#: T1's horizons, in M15 bars. Fixed in the plan.
ATLAS_HORIZONS: Final[tuple[int, ...]] = (16, 48, 96, 192, 480)
#: T2's horizons. Below 48 is closed by turnover arithmetic; above 480 the
#: non-overlapping count per pair falls under 30.
SCREEN_HORIZONS: Final[tuple[int, ...]] = (48, 192, 480)

#: The window the range-position family measures against, and the extreme-move
#: threshold. Both fixed in the plan.
RANGE_WINDOW: Final[int] = 192
EXTREME_LOOKBACK: Final[int] = 96
EXTREME_Z: Final[float] = 2.0
RV_FAST: Final[int] = 96
RV_SLOW: Final[int] = 384


def derived(frame: pd.DataFrame) -> pd.DataFrame:
    """The state columns, all backward windows at `t`.

    Reuses `round2`'s constants rather than restating them, so the ATR state here
    is the same object the reversal and momentum rounds conditioned on and the
    numbers are comparable to theirs.
    """
    out = frame.copy()
    close = out["mid_c"]
    pip = out["pip_size"]

    atr = engine.atr_pips(out, round2.ATR_PERIOD)
    rank = atr.rolling(round2.ATR_RANK_WINDOW, min_periods=round2.ATR_RANK_WINDOW // 2).rank(
        pct=True
    )
    atr_state = pd.Series(pd.NA, index=out.index, dtype="object")
    atr_state[rank <= 1 / 3] = "low"
    atr_state[(rank > 1 / 3) & (rank <= 2 / 3)] = "mid"
    atr_state[rank > 2 / 3] = "high"
    out["atr_state"] = atr_state
    out["atr_pips"] = atr

    step = close.diff() / pip
    rv_fast = step.rolling(RV_FAST, min_periods=RV_FAST // 2).std()
    rv_slow = step.rolling(RV_SLOW, min_periods=RV_SLOW // 2).std()
    ratio = rv_fast / rv_slow.replace(0.0, np.nan)
    vol_state = pd.Series(pd.NA, index=out.index, dtype="object")
    vol_state[ratio <= 1.0] = "compression"
    vol_state[ratio > 1.0] = "expansion"
    out["vol_state"] = vol_state

    #: The last **completed** 96-bar (24h) block, so nothing from the block still
    #: forming is read. `higher_timeframe` broadcasts the block's close to every
    #: bar and shifts by a whole period, so the difference wanted here is against
    #: the value one whole period earlier -- `.diff()` would compare adjacent bars
    #: and be zero everywhere except at the 173 block boundaries, which is what a
    #: first version of this file did.
    #:
    #: "Daily" means a 96-bar block from the panel's first bar, not a UTC
    #: calendar day: the grouping is by bar index. That is a consistent
    #: higher-timeframe context and it is not the same object as a D1 candle.
    htf = engine.higher_timeframe(out, BARS_PER_DAY)
    daily_change = htf["htf_close"] - htf["htf_close"].shift(BARS_PER_DAY)
    d1_state = pd.Series(pd.NA, index=out.index, dtype="object")
    d1_state[daily_change > 0] = "up"
    d1_state[daily_change < 0] = "down"
    out["d1_state"] = d1_state

    high, low = engine.donchian(out, RANGE_WINDOW)
    span = (high - low).replace(0.0, np.nan)
    position = (close - low) / span
    out["range_position"] = position
    range_state = pd.Series(pd.NA, index=out.index, dtype="object")
    for label, lo, hi in (
        ("Q1", -0.01, 0.25),
        ("Q2", 0.25, 0.50),
        ("Q3", 0.50, 0.75),
        ("Q4", 0.75, 1.01),
    ):
        range_state[(position > lo) & (position <= hi)] = label
    out["range_state"] = range_state

    extreme_z = engine.zscore((close - close.shift(EXTREME_LOOKBACK)) / pip, round2.Z_WINDOW)
    extreme_state = pd.Series(pd.NA, index=out.index, dtype="object")
    extreme_state[extreme_z.abs() > EXTREME_Z] = "extreme"
    extreme_state[extreme_z.abs() <= EXTREME_Z] = "normal"
    out["extreme_state"] = extreme_state

    out["roundtrip_cost"] = out["spread_close_pips"] + engine.SLIPPAGE_PAD_PIPS
    out["day"] = out["ts"].dt.floor("D")
    return out


def load_panel(panel: str) -> dict[str, pd.DataFrame]:
    loader, _, _ = LOADERS[panel]
    return {pair: derived(loader(pair)) for pair in PAIRS}


def panel_span(panel: str) -> tuple[str, str]:
    _, start, end = LOADERS[panel]
    return start, end


def trading_days(panel: dict[str, pd.DataFrame]) -> int:
    return int(pd.concat([f["day"] for f in panel.values()]).nunique())


def effective_independent_pairs(per_pair_daily: dict[str, pd.Series]) -> float:
    """`(sum sd)^2 / var(sum)` — the correlation-based estimator the rounds use.

    Twenty pairs behaving like twenty independent markets would return 20; this
    corpus has returned 4.6 to 6.5 every time it has been measured, and a value
    near 20 means the series handed in were not the pairs' own.
    """
    frame = pd.concat([s.rename(p) for p, s in per_pair_daily.items()], axis=1).fillna(0.0)
    columns = [c for c in frame.columns if frame[c].std() > 0]
    if len(columns) < 2:
        return float(len(columns))
    frame = frame[columns]
    total_sd = float(frame.sum(axis=1).std())
    if total_sd == 0:
        return float(len(columns))
    return round(float((frame.std().sum() / total_sd) ** 2), 2)


def tail_contributions(daily: pd.Series) -> dict[str, Any]:
    """Both tails. Reporting only the best days answers the wrong question for a
    negative series, which an audit caught in the supplemental round."""
    values = daily.to_numpy()
    if len(values) == 0:
        return {}
    best = np.sort(values)[::-1]
    worst = np.sort(values)
    total = float(values.sum())
    out: dict[str, Any] = {"days": int(len(values)), "total": round(total, 2)}
    for k in (1, 3, 5, 10, 20):
        if k <= len(values):
            out[f"best{k}"] = round(float(best[:k].sum()), 2)
            out[f"worst{k}"] = round(float(worst[:k].sum()), 2)
            out[f"net_ex_best{k}"] = round(total - float(best[:k].sum()), 2)
            out[f"net_ex_worst{k}"] = round(total - float(worst[:k].sum()), 2)
    return out


__all__ = [
    "ATLAS_HORIZONS",
    "BARS_PER_DAY",
    "BLOCS",
    "EXTREME_LOOKBACK",
    "EXTREME_Z",
    "JPY_PAIRS",
    "LOADERS",
    "NON_JPY_PAIRS",
    "RANGE_WINDOW",
    "SCREEN_HORIZONS",
    "derived",
    "effective_independent_pairs",
    "load_panel",
    "panel_span",
    "tail_contributions",
    "trading_days",
]
