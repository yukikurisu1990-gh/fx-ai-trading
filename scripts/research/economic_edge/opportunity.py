"""Stage 3 — can tick volume say *when* a slow signal is worth holding?

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

The Monetizability package established that tick volume knows about future
**absolute** movement (Spearman `+0.124 / +0.148`, same sign on 20 of 20 pairs)
and essentially nothing about **direction** (`−0.0014 / +0.0013`). This stage
asks the only question that follows from that: does it identify periods in which
holding a slow expected-return position is worth more?

**Tick volume may never be used to build a direction trade.** It has no
direction information; a rule that appears to find some is a bug.

The horizon has to match the signal it would time
--------------------------------------------------

A carry position rebalances weekly to monthly and is held in between, so
volume's information has to be measured at *that* horizon, not at one M15 bar.
Everything here aggregates volume to a **daily** state and looks a **week**
ahead. Measuring a one-bar relationship and asserting it survives to a week is
the mistake that would make this stage meaningless.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats

from scripts.research.economic_edge import (
    NULL_DRAWS,
    OPPORTUNITY_TARGETS,
    SEED,
    VOLUME_REPRESENTATIONS,
)

#: the daily state is built from a trailing window of this many trading days
STATE_WINDOW_DAYS: int = 60
#: and the forward look is one carry rebalance
FORWARD_DAYS: int = 5
#: a shock is a deviation from the trailing median, in trailing MADs
SHOCK_WINDOW_DAYS: int = 20


def daily_state(frame: pd.DataFrame) -> pd.DataFrame:
    """One row per trading day: the volume state, and what happened next.

    Every representation is **strictly backward-looking** at its own row, and
    every target is strictly forward. The two are computed from the same daily
    frame so an off-by-one is visible rather than hidden across a join.
    """
    day = frame["ts"].dt.floor("D")
    pip = float(frame["pip_size"].iloc[0])
    grouped = frame.groupby(day)

    daily = pd.DataFrame(
        {
            "volume": grouped["volume"].sum(min_count=1),
            "close": grouped["mid_c"].last(),
            "abs_move": grouped["mid_c"].apply(lambda s: abs(s.iloc[-1] - s.iloc[0])) / pip,
            "realised": grouped["mid_c"].apply(lambda s: float(s.diff().std() or 0.0)) / pip,
            "cost": grouped["roundtrip_cost"].median(),
        }
    ).dropna(subset=["volume"])
    if len(daily) < STATE_WINDOW_DAYS + FORWARD_DAYS + 10:
        return pd.DataFrame()

    log_volume = np.log1p(daily["volume"])
    trailing = log_volume.rolling(STATE_WINDOW_DAYS, min_periods=STATE_WINDOW_DAYS // 2)
    #: shifted by one day: a state must not read the day it labels
    daily["normalised_level"] = ((log_volume - trailing.mean()) / trailing.std()).shift(1)
    daily["rolling_percentile"] = trailing.rank(pct=True).shift(1)
    short = log_volume.rolling(SHOCK_WINDOW_DAYS, min_periods=SHOCK_WINDOW_DAYS // 2)
    deviation = log_volume - short.median()
    scale = deviation.abs().rolling(SHOCK_WINDOW_DAYS, min_periods=SHOCK_WINDOW_DAYS // 2).median()
    daily["shock"] = (deviation / scale.replace(0.0, np.nan)).shift(1)
    daily["change"] = (log_volume - log_volume.shift(5)).shift(1)
    daily["persistence"] = log_volume.rolling(5, min_periods=3).mean().shift(
        1
    ) - log_volume.rolling(20, min_periods=10).mean().shift(1)

    #: forward targets over one carry rebalance
    forward_close = daily["close"].shift(-FORWARD_DAYS)
    daily["future_absolute_return"] = (forward_close - daily["close"]).abs() / pip
    daily["future_realised_volatility"] = (
        daily["realised"]
        .shift(-1)
        .rolling(FORWARD_DAYS, min_periods=FORWARD_DAYS)
        .mean()
        .shift(-(FORWARD_DAYS - 1))
    )
    daily["movement_exceeds_cost"] = (daily["future_absolute_return"] > daily["cost"]).astype(float)
    daily.loc[daily["future_absolute_return"].isna(), "movement_exceeds_cost"] = np.nan
    return daily


def information(panel: dict[str, pd.DataFrame], *, draws: int = NULL_DRAWS, seed: int = SEED):
    """The 15 pre-registered cells: five representations against three targets.

    The null is a **circular block shift** of the state, which destroys the
    pairing while keeping each series' own serial dependence. An i.i.d.
    permutation was measured in the previous package to understate the null
    spread about elevenfold on exactly this kind of strongly autocorrelated
    series, so it is not used here.
    """
    states = {pair: daily_state(frame) for pair, frame in panel.items()}
    states = {pair: table for pair, table in states.items() if not table.empty}
    rng = np.random.default_rng(seed)
    out: dict[str, Any] = {}

    for representation in VOLUME_REPRESENTATIONS:
        for target in OPPORTUNITY_TARGETS:
            usable: list[tuple[np.ndarray, np.ndarray]] = []
            observed: list[float] = []
            for table in states.values():
                left = table[representation].to_numpy(dtype=float)
                right = table[target].to_numpy(dtype=float)
                keep = np.isfinite(left) & np.isfinite(right)
                if keep.sum() < 120:
                    continue
                usable.append((left[keep], right[keep]))
                observed.append(float(scipy_stats.spearmanr(left[keep], right[keep]).statistic))
            if not observed:
                continue
            real = float(np.mean(observed))
            ranked = [(scipy_stats.rankdata(a), scipy_stats.rankdata(b)) for a, b in usable]
            samples: list[float] = []
            for _ in range(draws):
                drawn = []
                for left_rank, right_rank in ranked:
                    offset = int(rng.integers(1, len(left_rank)))
                    rotated = np.concatenate([left_rank[offset:], left_rank[:offset]])
                    drawn.append(float(np.corrcoef(rotated, right_rank)[0, 1]))
                samples.append(float(np.mean(drawn)))
            mean, sd = float(np.mean(samples)), float(np.std(samples))
            out[f"{representation}|{target}"] = {
                "spearman": round(real, 5),
                "pairs": len(observed),
                "pairs_same_sign": int(sum(1 for v in observed if (v > 0) == (real > 0))),
                "null_mean": round(mean, 6),
                "null_sd": round(sd, 6),
                "studentized": round((real - mean) / sd, 3) if sd > 0 else None,
            }
    return out


def oracle_ceiling(
    per_pair_daily: dict[str, pd.Series],
    states: dict[str, pd.DataFrame],
    *,
    draws: int = NULL_DRAWS,
    seed: int = SEED,
) -> dict[str, Any]:
    """`UPPER_BOUND_DIAGNOSTIC_ONLY` — how much could perfect timing add?

    The base signal's realised daily P&L is given. An oracle that knows which
    days will be profitable keeps only those; a *realisable* filter can only
    ever be a subset of what the volume state can separate. If the oracle's
    improvement is small, no timing model on any state can rescue the base, and
    the family is dropped before anything is fitted.

    Reported beside the same computation on a matched null, because a
    foresight bound on its own is passed by noise — the previous package
    measured exactly that and it is why this one reports both.
    """
    rng = np.random.default_rng(seed)
    rows: dict[str, Any] = {}
    always, oracle, null_oracle = [], [], []
    for pair, daily in per_pair_daily.items():
        values = daily.to_numpy(dtype=float)
        values = values[np.isfinite(values)]
        if values.size < 60:
            continue
        base = float(values.sum())
        perfect = float(np.maximum(values, 0.0).sum())
        drawn = [
            float(np.maximum(rng.permutation(values), 0.0).sum()) for _ in range(min(draws, 40))
        ]
        always.append(base)
        oracle.append(perfect)
        null_oracle.append(float(np.mean(drawn)))
        rows[pair] = {
            "always_hold": round(base, 2),
            "perfect_timing": round(perfect, 2),
            "days": int(values.size),
        }
    if not always:
        return {"decidable": False}
    #: the null keeps the same daily values and destroys only their order, so a
    #: perfect-timing sum is identical under it -- which is the point: perfect
    #: foresight over a fixed multiset is order-invariant, so ANY improvement it
    #: shows is an arithmetic property of the distribution, not of timing.
    return {
        "pairs": len(always),
        "always_hold_mean": round(float(np.mean(always)), 2),
        "perfect_timing_mean": round(float(np.mean(oracle)), 2),
        "improvement_mean": round(float(np.mean(oracle) - np.mean(always)), 2),
        "improvement_ratio": round(float(np.mean(oracle) / np.mean(always)), 3)
        if np.mean(always) > 0
        else None,
        "order_invariance_note": (
            "a perfect-timing sum over a fixed multiset of daily P&L is "
            "order-invariant, so it is identical on a shuffled null by "
            "construction. The bound is therefore an arithmetic ceiling on ANY "
            "filter, and it says nothing on its own about whether a filter that "
            "uses volume can approach it"
        ),
        "per_pair": rows,
        "states_available": sorted(states),
    }


def filter_mask(table: pd.DataFrame, representation: str) -> pd.Series:
    """Hold when the state sits above its own trailing median. One threshold.

    The median is not a searched threshold — it is the only split that needs no
    choice, and using anything else would be a grid. `rolling_percentile` is
    already a percentile, so its median is 0.5 by construction.
    """
    state = table[representation]
    if representation == "rolling_percentile":
        return state > 0.5
    trailing_median = state.rolling(STATE_WINDOW_DAYS, min_periods=STATE_WINDOW_DAYS // 2).median()
    return state > trailing_median


def gated_daily(daily: pd.Series, table: pd.DataFrame, representation: str) -> pd.Series:
    """A daily P&L series with the days the filter excludes set to zero."""
    mask = filter_mask(table, representation).reindex(daily.index).fillna(False)
    return daily.where(mask, 0.0)


__all__ = [
    "FORWARD_DAYS",
    "filter_mask",
    "gated_daily",
    "SHOCK_WINDOW_DAYS",
    "STATE_WINDOW_DAYS",
    "daily_state",
    "information",
    "oracle_ceiling",
]
