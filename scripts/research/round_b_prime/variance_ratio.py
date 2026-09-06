"""B′-1 — the variance ratio, against three nulls.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

`VR(q) = Var(r_q) / (q · Var(r_1))`. Below 1 is mean reversion at that
aggregation, above 1 is trend, 1 is a random walk.

Why this statistic and not Round A's
------------------------------------

Round A's `median MFE / cost` is monotone in `σ√H / cost` and an IID shuffle
beats the real market on it — it is an identity, not a measurement. `VR` is a
**second moment on returns**: a random walk gives exactly 1 whatever its
volatility, so the volatility level cancels and only the serial structure is
left. `Var` is taken as the mean of squares about zero rather than about the
sample mean, so a drift estimate cannot leak into the denominator and inflate the
ratio.

The nulls do the work, not the level
------------------------------------

`VR < 1` on its own is not evidence: overlapping windows, a finite sample and the
bid-ask bounce all bias it downward. What the round reads is `real − N2`, where
N2 preserves `|r_t|` at every bar and randomises only the signs — so volatility
clustering is identical on both sides and the difference is attributable to
directional dependence alone.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from scripts.research.round_a import panels
from scripts.research.round_b_prime import (
    NULL_DRAWS,
    RV_WINDOW,
    SEED,
    VR_HORIZONS,
    nulls,
)


def sigma_normalised_returns(frame: pd.DataFrame) -> np.ndarray:
    """1-bar returns divided by the pair's own trailing volatility.

    `σ` is the trailing standard deviation of 1-bar pip returns over
    `RV_WINDOW`, shifted by one bar so a return is never normalised by a window
    that contains it. Normalising makes pairs comparable and removes the pip-unit
    inflation that Round 2 measured at roughly half the apparent JPY effect.
    """
    pips = frame["mid_c"].diff() / frame["pip_size"]
    sigma = pips.rolling(RV_WINDOW, min_periods=RV_WINDOW // 2).std().shift(1)
    return (pips / sigma).to_numpy()


def variance_ratio(values: np.ndarray, q: int) -> float:
    """`VR(q)` from non-overlapping `q`-sums, about zero.

    Non-overlapping rather than the overlapping estimator: overlapping windows
    give a smaller variance but correlated observations, and this round compares
    against a null computed the identical way, so the simpler estimator with
    honest independence is preferred.
    """
    clean = values[np.isfinite(values)]
    usable = len(clean) // q * q
    if usable < 2 * q:
        return float("nan")
    sums = clean[:usable].reshape(-1, q).sum(axis=1)
    denominator = q * float(np.mean(clean[:usable] ** 2))
    if denominator == 0:
        return float("nan")
    return float(np.mean(sums**2) / denominator)


def panel_vr(
    panel: dict[str, pd.DataFrame], pairs: tuple[str, ...] | None = None
) -> dict[int, float]:
    """`VR(q)` per horizon, averaged over pairs."""
    chosen = pairs or tuple(panel)
    out: dict[int, float] = {}
    for q in VR_HORIZONS:
        values = [variance_ratio(sigma_normalised_returns(panel[p]), q) for p in chosen]
        values = [v for v in values if np.isfinite(v)]
        out[q] = round(float(np.mean(values)), 5) if values else float("nan")
    return out


def _statistic_for_sanity(frame: pd.DataFrame) -> dict[str, float]:
    values = sigma_normalised_returns(frame)
    return {f"VR_{q}": variance_ratio(values, q) for q in VR_HORIZONS}


def null_sanity(draws: int = 40, seed: int = SEED) -> dict[str, Any]:
    """Each null must return `VR ≈ 1` on a generated random walk.

    Run and reported before any real-versus-null comparison. A null that does not
    recover the known answer is measuring its own construction — which is exactly
    what the plan's originally registered block sign flip did, and why it was
    amended before this round ran anything.
    """
    return nulls.sanity_check(_statistic_for_sanity, draws=draws, seed=seed)


def against_nulls(
    panel: dict[str, pd.DataFrame],
    *,
    draws: int = NULL_DRAWS,
    seed: int = SEED,
    pairs: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    """Real `VR(q)` beside each null's distribution, with studentized effects."""
    chosen = pairs or tuple(panel)
    real = panel_vr(panel, chosen)
    out: dict[str, Any] = {"pairs": len(chosen), "real": real, "draws": draws}
    rng = np.random.default_rng(seed)
    for name, null in nulls.NULLS.items():
        samples: dict[int, list[float]] = {q: [] for q in VR_HORIZONS}
        for _ in range(draws):
            shuffled = {p: null(panel[p], rng) for p in chosen}
            for q, value in panel_vr(shuffled, chosen).items():
                if np.isfinite(value):
                    samples[q].append(value)
        out[name] = {
            "contract": nulls.CONTRACTS[name],
            "per_horizon": {
                q: {
                    "null_mean": round(float(np.mean(v)), 5),
                    "null_sd": round(float(np.std(v)), 5),
                    "null_ci95": [
                        round(float(np.percentile(v, 2.5)), 5),
                        round(float(np.percentile(v, 97.5)), 5),
                    ],
                    "real_minus_null": round(float(real[q] - np.mean(v)), 5),
                    "studentized": round(float((real[q] - np.mean(v)) / np.std(v)), 3)
                    if np.std(v) > 0
                    else None,
                }
                for q, v in samples.items()
                if v
            },
        }
    return out


def bloc_split(panel: dict[str, pd.DataFrame], *, draws: int = 60, seed: int = SEED):
    """The primary null only, on each currency bloc, so one bloc cannot carry it."""
    return {
        bloc: against_nulls(
            panel, draws=draws, seed=seed, pairs=tuple(p for p in members if p in panel)
        )
        for bloc, members in panels.BLOCS.items()
        if bloc != "ALL"
    }


def temporal_stability(
    panel: dict[str, pd.DataFrame], *, blocks: int = 4
) -> dict[int, list[float]]:
    """Real `VR(q)` in four chronological sub-blocks, to see whether it drifts."""
    reference = next(iter(panel.values()))
    edges = np.array_split(np.arange(len(reference)), blocks)
    out: dict[int, list[float]] = {q: [] for q in VR_HORIZONS}
    for chunk in edges:
        lo, hi = reference["ts"].iloc[chunk[0]], reference["ts"].iloc[chunk[-1]]
        sliced = {
            pair: frame[(frame["ts"] >= lo) & (frame["ts"] <= hi)] for pair, frame in panel.items()
        }
        for q, value in panel_vr(sliced).items():
            out[q].append(value)
    return out


__all__ = [
    "against_nulls",
    "bloc_split",
    "null_sanity",
    "panel_vr",
    "sigma_normalised_returns",
    "temporal_stability",
    "variance_ratio",
]
