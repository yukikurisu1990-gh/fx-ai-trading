"""Stage 2 — carry economics, with spot and interest kept apart.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

The classic carry error is to report one number. A carry strategy that collected
its interest and gave every basis point back on spot is a **different object**
from one where spot helped, and they have opposite implications for whether the
thing is worth pursuing. So every result here carries three lines that add up —
**spot**, **carry**, **cost** — and never a single "gross".

What is being held, exactly
---------------------------

A position of `+1` in `BASE_QUOTE` earns, per calendar day held:

* `spot_pips` — the change in the mid, in pips;
* `carry_pips` — `(rate(BASE) − rate(QUOTE)) / 365 × price / pip_size`;

and pays `roundtrip_cost` in pips each time the position changes. Accrual is by
**calendar** day, so a weekend accrues three — the same convention a broker uses,
and about 40% of the annual accrual is in weekends and holidays.

Research carry is not broker carry
----------------------------------

What a retail account actually receives is the broker's financing, which embeds
a markup and a tom-next spread. No public archive of it exists. Everything here
is **research carry** built from public policy rates; the gap is recorded and
referred, never claimed away.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from scripts.research.economic_edge import (
    CARRY_CHANGE_LOOKBACK_REBALANCES,
    CARRY_DEAD_BAND_PCT,
    CROSS_SECTIONAL_K,
    CURRENCIES,
    DAYS_PER_YEAR,
    REBALANCE_BARS,
)
from scripts.research.exploratory_m15 import engine
from scripts.research.round_a import panels as panel_loader

#: 96 M15 bars in a day
BARS_PER_DAY = 96


def attach_rates(frame: pd.DataFrame, rate_panel: pd.DataFrame, pair: str) -> pd.DataFrame:
    """Join the daily rate panel onto one pair's M15 frame by UTC calendar date.

    The rate panel is already lagged by `RATE_LAG_TRADING_DAYS`, so this join
    cannot reach a rate the bar's own day announced.
    """
    base, quote = pair.split("_")
    out = frame.copy()
    day = out["ts"].dt.floor("D")
    out["rate_base"] = day.map(rate_panel[base]).to_numpy()
    out["rate_quote"] = day.map(rate_panel[quote]).to_numpy()
    out["carry_rate_pct"] = out["rate_base"] - out["rate_quote"]
    #: pips earned per calendar day by a +1 position
    out["carry_pips_per_day"] = (
        out["carry_rate_pct"] / 100.0 / DAYS_PER_YEAR * out["mid_c"] / out["pip_size"]
    )
    return out


def _rebalance_grid(length: int, stride: int, phase: int) -> np.ndarray:
    grid = np.zeros(length, dtype=bool)
    grid[phase::stride] = True
    return grid


def _elapsed_days(ts: pd.Series) -> np.ndarray:
    """Calendar days between consecutive bars — three across a weekend."""
    seconds = np.asarray(ts.diff().dt.total_seconds().to_numpy(), dtype=float).copy()
    seconds[0] = 0.0
    return np.nan_to_num(seconds, nan=0.0) / 86_400.0


def evaluate(
    frame: pd.DataFrame,
    position: pd.Series,
    *,
    pair: str,
    cost_multiplier: float = 1.0,
) -> dict[str, Any]:
    """One pair, one position series: spot, carry and cost, kept separate.

    The position is held from the bar **after** the decision, exactly as
    `engine.evaluate` does, and the spot line is computed by that same function
    so the two studies cannot drift apart.
    """
    result = engine.evaluate(
        frame, position, name="carry", pair=pair, cost_multiplier=cost_multiplier
    )
    #: `Result` exposes `net` and the totals; the spot and cost lines are
    #: recovered from its own metrics so the two studies cannot drift apart
    spot_total = float(result.metrics["gross_pips"])
    cost_total = float(result.metrics["cost_pips"])

    held = position.shift(1).fillna(0.0).to_numpy()
    elapsed = _elapsed_days(frame["ts"])
    carry = np.nan_to_num(
        held * frame["carry_pips_per_day"].to_numpy() * elapsed, nan=0.0, posinf=0.0, neginf=0.0
    )
    total = result.net.to_numpy() + carry

    stamps = frame["ts"]
    daily = pd.Series(total, index=stamps).groupby(stamps.dt.floor("D").to_numpy()).sum()
    equity = np.cumsum(total)
    turnover = float(np.abs(np.diff(np.concatenate([[0.0], held]))).sum())

    return {
        "spot_pips": round(spot_total, 2),
        "carry_pips": round(float(carry.sum()), 2),
        "gross_pips": round(spot_total + float(carry.sum()), 2),
        "cost_pips": round(cost_total, 2),
        "net_pips": round(float(total.sum()), 2),
        "turnover_units": round(turnover, 2),
        "trades": int(result.metrics.get("n_closed_trades", 0)),
        "max_drawdown_pips": round(float((equity - np.maximum.accumulate(equity)).min()), 2),
        "days_held": round(float((np.abs(held) * elapsed).sum()), 1),
        "mean_carry_rate_pct": round(float(np.nanmean(frame["carry_rate_pct"].to_numpy())), 4),
        "_daily": daily,
    }


# ------------------------------------------------------------------ families


def signal_pair_level(frame: pd.DataFrame, *, stride: int, phase: int) -> pd.Series:
    """**C-A** — long when the differential exceeds a dead-band, short below."""
    differential = frame["carry_rate_pct"].to_numpy()
    raw = np.where(
        differential > CARRY_DEAD_BAND_PCT,
        1.0,
        np.where(differential < -CARRY_DEAD_BAND_PCT, -1.0, 0.0),
    )
    return _hold(frame, raw, stride=stride, phase=phase)


def signal_carry_change(frame: pd.DataFrame, *, stride: int, phase: int) -> pd.Series:
    """**C-C** — the *change* in the differential over a fixed lookback."""
    lookback = stride * CARRY_CHANGE_LOOKBACK_REBALANCES
    differential = frame["carry_rate_pct"]
    change = (differential - differential.shift(lookback)).to_numpy()
    raw = np.sign(np.nan_to_num(change, nan=0.0))
    return _hold(frame, raw, stride=stride, phase=phase)


def _hold(frame: pd.DataFrame, raw: np.ndarray, *, stride: int, phase: int) -> pd.Series:
    """Decide only on the rebalance grid, hold in between, never across a rollover."""
    decided = pd.Series(raw, index=frame.index).where(
        pd.Series(_rebalance_grid(len(frame), stride, phase), index=frame.index)
    )
    held = decided.ffill().fillna(0.0)
    blocked = frame["rollover"] & (held != held.shift(1))
    return held.where(~blocked).ffill().fillna(0.0)


def cross_sectional_positions(
    rate_panel: pd.DataFrame, pairs: tuple[str, ...], *, k: int
) -> dict[str, pd.Series]:
    """**C-B** — rank the currencies, hold the top and bottom `k` at currency level.

    A currency's target exposure is `+1/k` if it is in the top `k` by rate,
    `−1/k` if in the bottom `k`, and zero otherwise. A pair's position is then
    `(target(BASE) − target(QUOTE)) / 2`, which expresses the currency view
    through the pairs available without double-counting either leg.
    """
    ranks = rate_panel[list(CURRENCIES)].rank(axis=1, method="average", ascending=False)
    target = pd.DataFrame(0.0, index=rate_panel.index, columns=list(CURRENCIES))
    target[ranks <= k] = 1.0 / k
    target[ranks > len(CURRENCIES) - k] = -1.0 / k
    out: dict[str, pd.Series] = {}
    for pair in pairs:
        base, quote = pair.split("_")
        out[pair] = (target[base] - target[quote]) / 2.0
    return out


def signal_cross_sectional(
    frame: pd.DataFrame, daily_position: pd.Series, *, stride: int, phase: int
) -> pd.Series:
    """Project a daily currency-level target onto one pair's M15 grid."""
    day = frame["ts"].dt.floor("D")
    raw = day.map(daily_position).to_numpy(dtype=float)
    return _hold(frame, np.nan_to_num(raw, nan=0.0), stride=stride, phase=phase)


# ------------------------------------------------------------------- the run


def _pool(rows: dict[str, dict[str, Any]], trading_days: int) -> dict[str, Any]:
    """Per-pair results pooled, with the breadth and concentration the plan asks for."""
    if not rows:
        return {"pairs": 0}
    keys = [k for k, v in next(iter(rows.values())).items() if isinstance(v, int | float)]
    pooled = {key: round(float(np.mean([r[key] for r in rows.values()])), 3) for key in keys}
    nets = {pair: r["net_pips"] for pair, r in rows.items()}
    total = float(sum(nets.values()))
    jpy = [v for p, v in nets.items() if p in panel_loader.JPY_PAIRS]
    non_jpy = [v for p, v in nets.items() if p not in panel_loader.JPY_PAIRS]

    daily = pd.concat([r["_daily"] for r in rows.values()], axis=1).fillna(0.0).mean(axis=1)
    by_day = daily.sort_values(ascending=False)
    pooled |= {
        "pairs": len(rows),
        "pairs_net_positive": int(sum(1 for v in nets.values() if v > 0)),
        "jpy_mean_net": round(float(np.mean(jpy)), 2) if jpy else None,
        "non_jpy_mean_net": round(float(np.mean(non_jpy)), 2) if non_jpy else None,
        "largest_pair_share": round(max(nets.values()) / total, 4) if total > 0 else None,
        "top10_day_share": round(float(by_day.head(10).sum() / daily.sum()), 4)
        if daily.sum() > 0
        else None,
        "annualised_turnover": round(
            float(np.mean([r["turnover_units"] for r in rows.values()]))
            / max(trading_days, 1)
            * 312.0,
            2,
        ),
        "sub_period_net": [
            round(float(block.sum()), 1) for block in np.array_split(daily.to_numpy(), 4)
        ],
        "effective_independent_pairs": panel_loader.effective_independent_pairs(
            {pair: r["_daily"] for pair, r in rows.items()}
        ),
    }
    return pooled


def run_family(
    panel: dict[str, pd.DataFrame],
    rate_panel: pd.DataFrame,
    *,
    family: str,
    rebalance: str,
    trading_days: int,
    cost_multiplier: float = 1.0,
    phases: int = 4,
) -> dict[str, Any]:
    """One (family, rebalance) cell, phase-averaged over the rebalance grid."""
    stride = REBALANCE_BARS[rebalance]
    step = max(1, stride // phases)
    pairs = tuple(panel)
    daily_positions = (
        cross_sectional_positions(rate_panel, pairs, k=int(family.split("_k")[1]))
        if family.startswith("cross_sectional")
        else None
    )

    per_pair: dict[str, dict[str, Any]] = {}
    for pair, frame in panel.items():
        collected: list[dict[str, Any]] = []
        for phase in range(phases):
            if family == "pair_level":
                position = signal_pair_level(frame, stride=stride, phase=phase * step)
            elif family == "carry_change":
                position = signal_carry_change(frame, stride=stride, phase=phase * step)
            else:
                position = signal_cross_sectional(
                    frame, daily_positions[pair], stride=stride, phase=phase * step
                )
            collected.append(evaluate(frame, position, pair=pair, cost_multiplier=cost_multiplier))
        averaged = {
            key: float(np.mean([row[key] for row in collected]))
            for key in collected[0]
            if isinstance(collected[0][key], int | float)
        }
        averaged["_daily"] = (
            pd.concat([row["_daily"] for row in collected], axis=1).fillna(0.0).mean(axis=1)
        )
        per_pair[pair] = averaged

    pooled = _pool(per_pair, trading_days)
    pooled["family"] = family
    pooled["rebalance"] = rebalance
    pooled["cost_multiplier"] = cost_multiplier
    return pooled


FAMILIES: tuple[str, ...] = (
    "pair_level",
    *(f"cross_sectional_k{k}" for k in CROSS_SECTIONAL_K),
    "carry_change",
)


__all__ = [
    "BARS_PER_DAY",
    "FAMILIES",
    "attach_rates",
    "cross_sectional_positions",
    "evaluate",
    "run_family",
    "signal_carry_change",
    "signal_cross_sectional",
    "signal_pair_level",
]
