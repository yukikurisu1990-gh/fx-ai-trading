"""T2 — the Conditional Sign Screen: does a state make the sign stable?

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

Four rounds established that the *unconditional* multi-day sign is not stable:
across three adjacent periods the mean IC ran −5.85%, +2.35%, −25.07%, and both
directions lost. What no round has tested is whether the sign is stable **inside**
a market state. That is the whole question here, and the answer may be "no" — in
which case direction prediction is finished on this data and the next round is
about labels rather than signs.

Thirty-nine cells, closed before the run
----------------------------------------

Five condition families, taken **marginally** rather than crossed: crossing five
families is thousands of cells nobody can correct for or interpret. Thirteen
levels times three horizons is 39, under the 48 the plan allows, and the family
is closed — no level, variable or horizon may be added now.

The context direction is fixed per family
-----------------------------------------

A drift needs a direction to be signed against, and choosing that direction after
seeing the drift would make every cell trivially "positive". So each family's
direction comes from that family's **own prior**, fixed in the plan:

* symmetric states (ATR, expansion, extreme) carry no directional claim of their
  own, so they use the reversal convention every previous round used — which
  also makes their sign directly comparable to those rounds;
* a higher-timeframe trend state claims continuation;
* a range-position state claims reversion toward the middle.

A negative drift is therefore as informative as a positive one: it says the
state's own prior is wrong there, consistently.

The estimator is non-overlapping and phase-averaged
---------------------------------------------------

Entries are taken at `t ≡ phase (mod H)` so that within a phase no two windows
overlap, and the eight phases are averaged. Round 1 found that a single phase
locks to one hour of the day on this corpus — a week is almost exactly 480 bars —
so a single-phase number is one draw from a wide distribution rather than an
estimate. Phase is a nuisance parameter: averaged, never selected.
"""

from __future__ import annotations

from typing import Any, Final

import numpy as np
import pandas as pd

from scripts.research.exploratory_m15 import round2
from scripts.research.round_a import panels

#: family id -> (state column, ordered levels, direction rule)
FAMILIES: Final[dict[str, tuple[str, tuple[str, ...], str]]] = {
    "F1_atr": ("atr_state", ("low", "mid", "high"), "fade_past_move"),
    "F2_vol": ("vol_state", ("compression", "expansion"), "fade_past_move"),
    "F3_d1_trend": ("d1_state", ("up", "down"), "follow_d1"),
    "F4_range": ("range_state", ("Q1", "Q2", "Q3", "Q4"), "fade_range_position"),
    "F5_extreme": ("extreme_state", ("extreme", "normal"), "fade_past_move"),
}

N_PHASES: Final[int] = round2.N_PHASES
#: A structural candidate must clear all six of these. Fixed in the plan.
MIN_EFFECT_OVER_COST: Final[float] = 2.0
MIN_EFFECTIVE_OBSERVATIONS: Final[int] = 30
MIN_EFFECTIVE_PAIRS: Final[float] = 3.0


def context_direction(frame: pd.DataFrame, rule: str, horizon: int) -> pd.Series:
    """The direction the state's own prior implies. Backward-looking throughout."""
    if rule == "fade_past_move":
        past = frame["mid_c"] - frame["mid_c"].shift(horizon)
        return -np.sign(past)
    if rule == "follow_d1":
        return frame["d1_state"].map({"up": 1.0, "down": -1.0}).astype(float)
    if rule == "fade_range_position":
        return -np.sign(frame["range_position"] - 0.5)
    raise ValueError(f"unknown direction rule {rule!r}")


def _entries(frame: pd.DataFrame, horizon: int, mask: pd.Series, rule: str) -> pd.DataFrame:
    """Non-overlapping, phase-averaged contributions for one pair and one cell."""
    pip = frame["pip_size"].to_numpy()
    close = frame["mid_c"].to_numpy()
    n = len(frame)
    direction = context_direction(frame, rule, horizon).to_numpy()

    #: a decision at t is on risk from t+1 and exits at t+H+1
    contribution = np.full(n, np.nan)
    last = n - horizon - 2
    if last >= 0:
        index = np.arange(0, last + 1)
        contribution[index] = (
            direction[index] * (close[index + horizon + 1] - close[index + 1]) / pip[index]
        )

    eligible = mask.to_numpy() & np.isfinite(contribution) & (direction != 0)
    blocks: list[pd.DataFrame] = []
    for phase in range(0, horizon, max(1, horizon // N_PHASES))[:N_PHASES]:
        taken = np.zeros(n, dtype=bool)
        taken[phase::horizon] = True
        taken &= eligible
        if not taken.any():
            continue
        blocks.append(
            pd.DataFrame(
                {
                    "phase": phase,
                    "day": frame["day"].to_numpy()[taken],
                    "pips": contribution[taken],
                    "cost": frame["roundtrip_cost"].to_numpy()[taken],
                }
            )
        )
    if not blocks:
        return pd.DataFrame(columns=["phase", "day", "pips", "cost"])
    return pd.concat(blocks, ignore_index=True)


def screen_cell(
    panel: dict[str, pd.DataFrame],
    *,
    family: str,
    level: str,
    horizon: int,
) -> dict[str, Any]:
    """One cell on one period, with the diagnostics the plan requires."""
    column, _, rule = FAMILIES[family]
    per_pair_entries: dict[str, pd.DataFrame] = {}
    for pair, frame in panel.items():
        mask = frame[column] == level
        per_pair_entries[pair] = _entries(frame, horizon, mask, rule)

    stacked = (
        pd.concat(
            [df.assign(pair=pair) for pair, df in per_pair_entries.items() if len(df)],
            ignore_index=True,
        )
        if any(len(df) for df in per_pair_entries.values())
        else pd.DataFrame()
    )
    if stacked.empty:
        return {"family": family, "level": level, "horizon": horizon, "entries": 0}

    #: phase-average per pair first, then across pairs, so a pair with more
    #: eligible bars in one phase cannot tilt the mean
    per_pair_mean = (
        stacked.groupby(["pair", "phase"], observed=True)["pips"]
        .mean()
        .groupby("pair", observed=True)
        .mean()
    )
    mean_per_entry = float(per_pair_mean.mean())
    median_cost = float(stacked["cost"].median())

    #: the daily series: each phase's entries attributed to the decision day,
    #: averaged over phases and then over pairs, so it is on the same
    #: pips-per-pair scale every round of this programme has used
    daily_by_phase = (
        stacked.groupby(["pair", "phase", "day"], observed=True)["pips"].sum().reset_index()
    )
    per_pair_daily = {
        pair: group.groupby("day", observed=True)["pips"].sum() / group["phase"].nunique()
        for pair, group in daily_by_phase.groupby("pair", observed=True)
    }
    pooled_daily = (
        pd.concat([s.rename(p) for p, s in per_pair_daily.items()], axis=1).fillna(0.0).mean(axis=1)
    )
    pooled_daily = pooled_daily.sort_index()

    total_days = panels.trading_days(panel)
    n_bars = sum(len(f) for f in panel.values())
    cell_bars = int(sum((f[column] == level).sum() for f in panel.values()))
    #: entries per phase, so windows within a phase do not overlap
    effective_observations = int(len(stacked) / max(1, stacked["phase"].nunique()))

    rate = mean_per_entry * panels.BARS_PER_DAY / horizon
    share = cell_bars / n_bars if n_bars else 0.0

    per_pair_total = {p: float(s.sum()) for p, s in per_pair_daily.items()}
    jpy = [p for p in per_pair_total if p in panels.JPY_PAIRS]
    non_jpy = [p for p in per_pair_total if p not in panels.JPY_PAIRS]

    return {
        "family": family,
        "level": level,
        "horizon": horizon,
        "direction_rule": rule,
        "entries": int(len(stacked)),
        "effective_observations": effective_observations,
        "cell_share": round(share, 4),
        "mean_pips_per_entry": round(mean_per_entry, 3),
        "median_roundtrip_cost": round(median_cost, 3),
        "effect_over_cost": round(mean_per_entry / median_cost, 3) if median_cost else None,
        "rate_pips_per_day": round(rate, 4),
        "contribution_pips_per_day": round(rate * share, 4),
        "total_pips_per_pair": round(float(pooled_daily.sum()), 2),
        "trading_days": total_days,
        "pairs_positive": int(sum(1 for v in per_pair_total.values() if v > 0)),
        "pairs_counted": len(per_pair_total),
        "jpy_total": round(float(np.mean([per_pair_total[p] for p in jpy])), 2) if jpy else None,
        "non_jpy_total": round(float(np.mean([per_pair_total[p] for p in non_jpy])), 2)
        if non_jpy
        else None,
        "effective_independent_pairs": panels.effective_independent_pairs(per_pair_daily),
        "tails": panels.tail_contributions(pooled_daily),
        "_daily": pooled_daily,
    }


def screen_panel(panel: dict[str, pd.DataFrame], panel_id: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for family, (_, levels, _) in FAMILIES.items():
        for level in levels:
            for horizon in panels.SCREEN_HORIZONS:
                cell = screen_cell(panel, family=family, level=level, horizon=horizon)
                cell["panel"] = panel_id
                rows.append(cell)
    return rows


def cell_id(row: dict[str, Any]) -> str:
    return f"{row['family']}:{row['level']}:h{row['horizon']}"


__all__ = [
    "FAMILIES",
    "MIN_EFFECTIVE_OBSERVATIONS",
    "MIN_EFFECTIVE_PAIRS",
    "MIN_EFFECT_OVER_COST",
    "N_PHASES",
    "cell_id",
    "context_direction",
    "screen_cell",
    "screen_panel",
]
