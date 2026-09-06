"""`POST_HOC_DIAGNOSTIC_ONLY` — what the two positive results actually mean.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

**Nothing in this module may support a conclusion.** The plan (§10) says any
statistic outside the 28 pre-registered cells is labelled post-hoc and cannot
carry a verdict. These exist because the pre-registered results raised two
questions the pre-registered statistics cannot answer, and reporting the results
without them would be reporting less than is known.

The two questions
-----------------

**1. Is `VR < 1` microstructure?** `VR(2) = 0.9665` with `z = −13.8` implies a
first-order autocorrelation of about `−0.034`, which is the textbook signature of
bid-ask bounce (Roll 1984) rather than of anything tradable. None of the three
nulls controls for it: all of them destroy serial dependence, so bounce and
genuine reversion both show up as `real − null < 0`. The separation is to
recompute `VR` on a **coarser base return** — if the deficit survives when the
unit is 12 bars rather than 1, it is not a 1-bar quoting effect.

**2. Is B′-2's `k = 1.5σ` result a denominator artefact?** The retrace fraction
divides by the realised excursion, and the anchor detector fires at different
places on the real series and on the null. If real anchors carry systematically
larger excursions, the same absolute retrace becomes a smaller fraction and the
"less retrace" finding is arithmetic rather than path shape. The check is to
compare the anchor populations themselves — count, formation time, excursion
size, window length — not just the retrace.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from scripts.research.round_b_prime import EXCURSION_SIGMAS, SEED, nulls, retrace, variance_ratio

CLASSIFICATION = "POST_HOC_DIAGNOSTIC_ONLY"


def coarse_variance_ratio(frame: pd.DataFrame, base: int, q: int) -> float:
    """`VR(q)` computed on `base`-bar returns instead of 1-bar returns.

    At `base = 12` (three hours) a one-bar quoting effect has been aggregated
    away, so a deficit that survives is not bid-ask bounce.
    """
    values = variance_ratio.sigma_normalised_returns(frame)
    clean = values[np.isfinite(values)]
    usable = len(clean) // base * base
    if usable < base * q * 2:
        return float("nan")
    coarse = clean[:usable].reshape(-1, base).sum(axis=1)
    return variance_ratio.variance_ratio(coarse, q)


def microstructure_split(
    panel: dict[str, pd.DataFrame], *, bases: tuple[int, ...] = (1, 4, 12, 48)
) -> dict[str, Any]:
    """`VR` at a fixed total aggregation, reached through different base units.

    The same total horizon is assembled from 1-bar, 4-bar, 12-bar and 48-bar
    building blocks. A pure lag-1 effect disappears as the base grows; a
    longer-range effect does not.

    Also reports the MA(1) prediction: if the only autocorrelation were at lag 1,
    `ρ₁ = VR(2) − 1` and `VR(q) = 1 + 2ρ₁(1 − 1/q)`. The gap between that
    prediction and the observed `VR(q)` is what lag-1 cannot explain.
    """
    out: dict[str, Any] = {}
    for base in bases:
        row: dict[str, Any] = {}
        for q in (2, 4, 12, 40):
            values = [coarse_variance_ratio(frame, base, q) for frame in panel.values()]
            values = [v for v in values if np.isfinite(v)]
            if values:
                row[f"q{q}_total_bars_{base * q}"] = round(float(np.mean(values)), 5)
        out[f"base_{base}"] = row

    vr2 = variance_ratio.panel_vr(panel)[2]
    rho1 = vr2 - 1.0
    real = variance_ratio.panel_vr(panel)
    out["ma1_decomposition"] = {
        "rho1_implied_by_vr2": round(rho1, 5),
        "per_horizon": {
            q: {
                "observed": round(real[q], 5),
                "ma1_prediction": round(1 + 2 * rho1 * (1 - 1 / q), 5),
                "unexplained_by_lag1": round(real[q] - (1 + 2 * rho1 * (1 - 1 / q)), 5),
                "share_explained_by_lag1": round((2 * rho1 * (1 - 1 / q)) / (real[q] - 1), 3)
                if real[q] != 1
                else None,
            }
            for q in (12, 48, 96, 192, 480)
        },
    }
    return out


def anchor_population(
    panel: dict[str, pd.DataFrame],
    k: float,
    *,
    draws: int = 20,
    seed: int = SEED,
) -> dict[str, Any]:
    """Compare the anchor populations, not just the retrace they produce.

    If the real and null detectors select different kinds of event, the retrace
    fraction is not comparing like with like.
    """
    _, real = retrace.panel_geometry(panel, k)
    if real.empty:
        return {"k": k, "anchors": 0}

    def describe(frame: pd.DataFrame) -> dict[str, float]:
        return {
            "anchors": float(len(frame)),
            "median_bars_to_anchor": float(frame["bars_to_anchor"].median()),
            "median_excursion_sigma": float(frame["excursion_sigma"].median()),
            "median_observation_bars": float(frame["observation_bars"].median()),
            "median_scaled_excursion": float(
                (frame["excursion_sigma"] / np.sqrt(frame["bars_to_anchor"])).median()
            ),
            "median_adverse_extension_sigma": float(frame["adverse_extension_sigma"].median()),
        }

    rng = np.random.default_rng(seed)
    samples: list[dict[str, float]] = []
    for _ in range(draws):
        shuffled = {p: nulls.n2_sign_flip(f, rng) for p, f in panel.items()}
        _, frame = retrace.panel_geometry(shuffled, k)
        if not frame.empty:
            samples.append(describe(frame))

    observed = describe(real)
    return {
        "k": k,
        "real": {key: round(value, 4) for key, value in observed.items()},
        "null": {
            key: {
                "mean": round(float(np.mean([s[key] for s in samples])), 4),
                "sd": round(float(np.std([s[key] for s in samples])), 4),
                "z": round(
                    float(
                        (observed[key] - np.mean([s[key] for s in samples]))
                        / (np.std([s[key] for s in samples]) or np.inf)
                    ),
                    2,
                ),
            }
            for key in observed
        },
        "draws": len(samples),
        "note": (
            "if the anchor populations differ, the retrace fraction is not "
            "comparing like with like and the pre-registered difference is "
            "partly or wholly a selection artefact"
        ),
    }


def all_anchor_populations(panel: dict[str, pd.DataFrame], **kwargs) -> dict[str, Any]:
    return {str(k): anchor_population(panel, k, **kwargs) for k in EXCURSION_SIGMAS}


def harvestability(panel: dict[str, pd.DataFrame], *, horizons=(1, 2, 4, 12, 48)) -> dict[str, Any]:
    """Is the surviving structure large enough to pay for a round trip?

    The plan gave B′-2 an economic floor and gave B′-1 none — a defect in the
    pre-registration, because "the variance ratio differs from its null" is a
    statement about statistics and Case A's word "non-negligible" is a statement
    about economics.

    The floor that was missing is Round A's own: the **break-even information
    coefficient**, `cost / sd(q-bar move)`. Beside it, the IC the variance-ratio
    deficit actually implies. For an MA(1) with `VR(2) = 1 + ρ₁`, a rule that
    fades the previous `q`-bar move has an IC of about `√|VR(q) − 1|` at best —
    a generous upper bound, since it credits the whole variance deficit to a
    single predictable component.
    """
    out: dict[str, Any] = {}
    rho1 = variance_ratio.panel_vr(panel)[2] - 1.0
    out["rho1"] = round(rho1, 6)
    for q in horizons:
        moves: list[float] = []
        costs: list[float] = []
        for frame in panel.values():
            pips = (frame["mid_c"].diff(q) / frame["pip_size"]).dropna()
            if len(pips) > q * 4:
                moves.append(float(pips.std()))
                costs.append(float(frame["roundtrip_cost"].median()))
        if not moves:
            continue
        sd = float(np.mean(moves))
        cost = float(np.mean(costs))
        vr = variance_ratio.panel_vr(panel).get(q if q > 1 else 2)
        deficit = abs(vr - 1.0) if vr is not None else float("nan")
        out[str(q)] = {
            "sd_q_bar_move_pips": round(sd, 3),
            "median_roundtrip_cost_pips": round(cost, 3),
            "break_even_ic": round(cost / sd, 5) if sd else None,
            "vr_deficit": round(deficit, 5),
            #: A deliberately generous bound: it credits the *whole* variance
            #: deficit to one predictable component. Reported so the generous
            #: reading is visible, not because it is achievable.
            "generous_ic_upper_bound_sqrt_deficit": round(float(np.sqrt(deficit)), 5),
            "ratio_generous_over_break_even": round(float(np.sqrt(deficit)) / (cost / sd), 3)
            if sd and cost
            else None,
            #: The achievable one. If the deficit is a lag-1 effect -- which the
            #: base-unit test and the MA(1) decomposition both say it is -- then
            #: the correlation between adjacent non-overlapping q-blocks is only
            #: `ρ₁ / q`, because a single lag-1 covariance is spread across a
            #: q x q block. That is what a rule trading at horizon q could use.
            "ma1_block_autocorrelation": round(rho1 / q, 6),
            "ratio_ma1_block_over_break_even": round(abs(rho1 / q) / (cost / sd), 4)
            if sd and cost
            else None,
        }
    out["note"] = (
        "the generous bound credits the whole variance deficit to one component; "
        "the MA(1) block figure is what a rule at horizon q could actually use if "
        "the deficit is the lag-1 effect the base-unit test says it is. A ratio "
        "below 1 means the structure cannot pay for the spread."
    )
    return out


__all__ = [
    "CLASSIFICATION",
    "all_anchor_populations",
    "anchor_population",
    "coarse_variance_ratio",
    "harvestability",
    "microstructure_split",
]
