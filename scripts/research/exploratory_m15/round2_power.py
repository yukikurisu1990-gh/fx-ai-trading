"""Round 2's Q3: detection power, on the pre-registered quantity.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

Why this file exists at all
---------------------------

A first pass computed the power analysis in a scratch script that was never
committed, using **4** rebalance phases where the plan pre-registers **8**. The
four it used happen to be the better half — +305.7 against the complement's
+218.6 and the pre-registered mean of +262.1 — so the whole of Q3 sat on a
quantity 17% larger than the one that was registered, produced by code nobody
could re-run. A review role found both.

So: the pre-registered quantity is `N_PHASES = 8`, taken from `round2`, and this
module is committed alongside the numbers it produces.

Three nulls, and which one leads
--------------------------------

* **Block sign-flip** (`familywise`) — preserves the observed daily magnitudes
  and randomises only their signs, one draw shared across the family. This is
  the headline.
* **Shared-permutation random walk** — each pair's bar moves are permuted with a
  **common** key across pairs, so a random walk is built that keeps the
  cross-pair correlation. The first pass permuted each pair independently, which
  makes the twenty pairs independent inside the null, shrinks its standard
  deviation and inflates the z from 2.4 to 4.6. Supporting evidence only, and
  reported at the shared value.
* **Block bootstrap** — the confidence interval on the effect.

The power arithmetic is **two-sided throughout**. The first pass reported a
two-sided MDE beside a one-sided power, which is each row's more flattering half.
"""

from __future__ import annotations

from typing import Any, Final

import numpy as np
import pandas as pd
from scipy import stats

from scripts.research.exploratory_m15 import PAIRS, engine, round2
from scripts.research.exploratory_m15 import bars as bars_module

SEED: Final[int] = 20260905
BOOTSTRAP_DRAWS: Final[int] = 20_000
BLOCK_DAYS: Final[int] = 5
#: two-sided alpha 0.05, power 0.80
Z_ALPHA_TWO_SIDED: Final[float] = 1.959964
Z_POWER: Final[float] = 0.841621


def pooled_net(
    loaded: dict[str, pd.DataFrame],
    *,
    lookback: int,
    hold: int,
    entry_z: float,
    pairs: list[str] | None = None,
) -> pd.Series:
    """Phase-averaged pooled net, over the pre-registered 8 phases."""
    chosen = pairs or list(loaded)
    phases = list(range(0, hold, max(1, hold // round2.N_PHASES)))[: round2.N_PHASES]
    columns = []
    for pair in chosen:
        frame = loaded[pair]
        accumulated = None
        for phase in phases:
            signal = round2._signal(
                frame, lookback=lookback, hold=hold, entry_z=entry_z, phase=phase
            )
            result = engine.evaluate(frame, signal, name="q3", pair=pair)
            accumulated = (
                result.net if accumulated is None else accumulated.add(result.net, fill_value=0.0)
            )
        columns.append((accumulated / len(phases)).set_axis(frame["ts"]).rename(pair))
    return pd.concat(columns, axis=1).fillna(0.0).mean(axis=1)


def shared_random_walk(
    loaded: dict[str, pd.DataFrame], rng: np.random.Generator
) -> dict[str, pd.DataFrame]:
    """A random walk that keeps the cross-pair correlation.

    One permutation key, applied to every pair's bar moves on a shared timestamp
    index, so moves that happened at the same instant stay together. Permuting
    each pair independently would make the twenty pairs independent inside the
    null — which is not the null anyone means when they say "random walk", and
    which shrinks its standard deviation by about 40%.
    """
    union = sorted({ts for frame in loaded.values() for ts in frame["ts"]})
    order = rng.permutation(len(union))
    key = dict(zip(union, order, strict=True))
    out: dict[str, pd.DataFrame] = {}
    for pair, frame in loaded.items():
        copy = frame.copy()
        mid = frame["mid_c"].to_numpy()
        moves = np.diff(mid)
        rank = np.asarray([key[ts] for ts in frame["ts"].iloc[1:]])
        shuffled = moves[np.argsort(np.argsort(rank))]
        walk = np.concatenate([[mid[0]], mid[0] + np.cumsum(shuffled)])
        copy["mid_c"] = walk
        #: keep each bar's own high/low/open offsets, so the bar shape and the
        #: spread series are untouched and the cost model stays realistic
        copy["mid_h"] = walk + (frame["mid_h"] - frame["mid_c"]).to_numpy()
        copy["mid_l"] = walk + (frame["mid_l"] - frame["mid_c"]).to_numpy()
        copy["mid_o"] = walk + (frame["mid_o"] - frame["mid_c"]).to_numpy()
        out[pair] = copy
    return out


def analyse(
    loaded: dict[str, pd.DataFrame],
    *,
    lookback: int = 480,
    hold: int = 480,
    entry_z: float = 1.0,
    simulations: int = 100,
    pairs: list[str] | None = None,
    label: str = "all",
) -> dict[str, Any]:
    rng = np.random.default_rng(SEED)
    observed_series = pooled_net(loaded, lookback=lookback, hold=hold, entry_z=entry_z, pairs=pairs)
    observed = float(observed_series.sum())

    nulls = []
    for _ in range(simulations):
        walk = shared_random_walk(loaded, rng)
        nulls.append(
            float(
                pooled_net(walk, lookback=lookback, hold=hold, entry_z=entry_z, pairs=pairs).sum()
            )
        )
    nulls = np.asarray(nulls)

    daily = observed_series.groupby(observed_series.index.floor("D")).sum()
    values = daily.to_numpy()
    blocks = [values[i : i + BLOCK_DAYS] for i in range(0, len(values), BLOCK_DAYS)]
    boot = np.asarray(
        [
            np.concatenate([blocks[j] for j in rng.integers(0, len(blocks), len(blocks))]).sum()
            for _ in range(BOOTSTRAP_DRAWS)
        ]
    )
    sd = float(boot.std())
    mde = (Z_ALPHA_TWO_SIDED + Z_POWER) * sd
    power = float(1 - stats.norm.cdf(Z_ALPHA_TWO_SIDED - observed / sd)) if sd > 0 else 0.0
    span_days = int((daily.index.max() - daily.index.min()).days) + 1
    multiple = (mde / observed) ** 2 if observed > 0 else float("inf")

    #: concentration of the P&L in time, because a "stationary positive mean" is
    #: a poor description of a series carried by a handful of days
    ranked = np.sort(values)[::-1]
    total = values.sum()
    return {
        "label": label,
        "config": f"lb{lookback}_h{hold}_z{entry_z}",
        "phases": round2.N_PHASES,
        "pairs": len(pairs or loaded),
        "observed_net_pips_per_pair": round(observed, 1),
        "shared_random_walk_null": {
            "simulations": simulations,
            "mean": round(float(nulls.mean()), 1),
            "sd": round(float(nulls.std()), 1),
            "p95": round(float(np.percentile(nulls, 95)), 1),
            "max": round(float(nulls.max()), 1),
            "z": round(float((observed - nulls.mean()) / nulls.std()), 2),
            "p": round(float((nulls >= observed).mean()), 4),
        },
        "block_bootstrap": {
            "ci95": [
                round(float(np.percentile(boot, 2.5)), 1),
                round(float(np.percentile(boot, 97.5)), 1),
            ],
            "sd": round(sd, 1),
            "p_net_le_zero": round(float((boot <= 0).mean()), 3),
        },
        "power_two_sided": {
            "alpha": 0.05,
            "minimum_detectable_effect": round(float(mde), 1),
            "observed_over_mde": round(float(observed / mde), 2) if mde else None,
            "power_at_observed_effect": round(power, 2),
            "span_days": span_days,
            "span_multiple_for_80pct": round(float(multiple), 2),
            "additional_days_needed": int(max(0.0, multiple * span_days - span_days)),
        },
        "time_concentration": {
            "days": int(len(values)),
            "top_3_days_share": round(float(ranked[:3].sum() / total), 3) if total else None,
            "top_10_days_share": round(float(ranked[:10].sum() / total), 3) if total else None,
            "median_day": round(float(np.median(values)), 3),
            "share_of_days_positive": round(float((values > 0).mean()), 3),
        },
    }


def main() -> dict[str, Any]:
    loaded = {pair: bars_module.load(pair) for pair in PAIRS}
    jpy = [pair for pair in PAIRS if "JPY" in pair]
    non_jpy = [pair for pair in PAIRS if pair not in jpy]
    return {
        "all_20": analyse(loaded, label="all_20"),
        "jpy_6": analyse(loaded, pairs=jpy, label="jpy_6"),
        "non_jpy_14": analyse(loaded, pairs=non_jpy, label="non_jpy_14"),
    }


__all__ = ["analyse", "main", "pooled_net", "shared_random_walk"]
