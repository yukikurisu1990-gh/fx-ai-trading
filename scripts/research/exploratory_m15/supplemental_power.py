"""Whether the supplemental history resolved the question, on rates not totals.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

Two things this module refuses to do, both of which the obvious code would.

**It compares rates, not totals.** The original span is 248 dates and the
supplemental one is 730. Net pips per pair accumulate with the span, so putting
`+262.1` beside `-577.3` and calling the second one "larger" compares two
different questions. Every comparison here is per pair per day, and the totals
are carried alongside only so the reader can check the arithmetic.

**Its power arithmetic is signed correctly.** `round2_power.analyse` computes
`power` from `observed / sd` and `span_multiple` from `(mde / observed) ** 2`,
both of which assume the effect is positive; the first collapses towards zero
for a negative effect and the second is meaningless. That module is left
untouched, because it is the committed record of Round 2's numbers and Round 2's
effect really was positive. This one uses `|effect|` for the two-sided power and
reports the sign separately, because here the effect is negative and the
interesting question is whether it is *reliably* negative.

The headline question is not "is the supplemental period significant". It is
**does the sign replicate**, and that is answered by the sign.
"""

from __future__ import annotations

from typing import Any, Final

import numpy as np
import pandas as pd
from scipy import stats

from scripts.research.exploratory_m15 import familywise, round2_sensitivity

SEED: Final[int] = 20260905
DRAWS: Final[int] = 20_000
#: the pre-registered centre, frozen at `c076988` and not moved this round
CENTRE: Final[dict[str, Any]] = {"lookback": 480, "hold": 480, "entry_z": 1.0}


def _daily(series: pd.Series) -> np.ndarray:
    grouped = series.groupby(series.index.floor("D")).sum()
    return grouped.to_numpy()


def _block_bootstrap(values: np.ndarray, rng: np.random.Generator, draws: int) -> np.ndarray:
    chunks = [
        values[i : i + familywise.BLOCK_DAYS] for i in range(0, len(values), familywise.BLOCK_DAYS)
    ]
    return np.asarray(
        [
            np.concatenate([chunks[j] for j in rng.integers(0, len(chunks), len(chunks))]).mean()
            for _ in range(draws)
        ]
    )


def rate_comparison(
    original_daily: pd.Series, supplemental_daily: pd.Series, *, draws: int = DRAWS
) -> dict[str, Any]:
    """Per-pair-per-day rates, their bootstrap intervals, and their difference."""
    rng = np.random.default_rng(SEED)
    out: dict[str, Any] = {}
    boots: dict[str, np.ndarray] = {}
    for label, series in (("original", original_daily), ("supplemental", supplemental_daily)):
        values = _daily(series)
        boot = _block_bootstrap(values, rng, draws)
        boots[label] = boot
        out[label] = {
            "days": int(len(values)),
            "total_pips_per_pair": round(float(values.sum()), 1),
            "rate_pips_per_pair_per_day": round(float(values.mean()), 4),
            "rate_ci95": [
                round(float(np.percentile(boot, 2.5)), 4),
                round(float(np.percentile(boot, 97.5)), 4),
            ],
            "rate_se": round(float(boot.std()), 4),
            "p_rate_le_zero": round(float((boot <= 0).mean()), 4),
        }

    difference = boots["supplemental"] - boots["original"]
    observed_difference = float(_daily(supplemental_daily).mean() - _daily(original_daily).mean())
    #: what the supplemental period would have produced had the original rate
    #: been the truth -- the quantity a replication is actually about
    projected = float(_daily(original_daily).mean() * len(_daily(supplemental_daily)))
    out["difference_supplemental_minus_original"] = {
        "rate": round(observed_difference, 4),
        "ci95": [
            round(float(np.percentile(difference, 2.5)), 4),
            round(float(np.percentile(difference, 97.5)), 4),
        ],
        "se": round(float(difference.std()), 4),
        "p_two_sided_no_difference": round(
            float(2 * min((difference >= 0).mean(), (difference <= 0).mean())), 4
        ),
    }
    out["projection"] = {
        "supplemental_net_if_original_rate_held": round(projected, 1),
        "supplemental_net_observed": round(float(_daily(supplemental_daily).sum()), 1),
        "shortfall_pips_per_pair": round(float(_daily(supplemental_daily).sum() - projected), 1),
    }

    pooled = np.concatenate([_daily(original_daily), _daily(supplemental_daily)])
    pooled_boot = _block_bootstrap(pooled, rng, draws)
    out["combined"] = {
        "days": int(len(pooled)),
        "total_pips_per_pair": round(float(pooled.sum()), 1),
        "rate_pips_per_pair_per_day": round(float(pooled.mean()), 4),
        "rate_ci95": [
            round(float(np.percentile(pooled_boot, 2.5)), 4),
            round(float(np.percentile(pooled_boot, 97.5)), 4),
        ],
        "rate_se": round(float(pooled_boot.std()), 4),
        "se_shrank_versus_original": bool(pooled_boot.std() < boots["original"].std()),
    }
    return out


def two_sided_power(daily: pd.Series, *, draws: int = DRAWS) -> dict[str, Any]:
    """Power on `|effect|`, so a negative effect is not silently read as no effect."""
    rng = np.random.default_rng(SEED)
    values = _daily(daily)
    boot = _block_bootstrap(values, rng, draws) * len(values)
    observed = float(values.sum())
    sd = float(boot.std())
    z_alpha, z_power = 1.959964, 0.841621
    mde = (z_alpha + z_power) * sd
    power = float(1 - stats.norm.cdf(z_alpha - abs(observed) / sd)) if sd > 0 else 0.0
    multiple = (mde / abs(observed)) ** 2 if observed else float("inf")
    return {
        "observed_net_pips_per_pair": round(observed, 1),
        "sign": "positive" if observed > 0 else "negative",
        "effect_sd": round(sd, 1),
        "minimum_detectable_effect_two_sided_80pct": round(mde, 1),
        "abs_observed_over_mde": round(abs(observed) / mde, 2) if mde else None,
        "power_at_observed_absolute_effect": round(power, 2),
        "span_days": int(len(values)),
        "span_multiple_for_80pct": round(float(multiple), 2),
        "additional_days_needed": int(max(0.0, multiple * len(values) - len(values))),
    }


def family_of_nine(loaded: dict[str, pd.DataFrame]) -> dict[str, pd.Series]:
    """The 9-cell neighbourhood as daily series, for the family-max rule."""
    return {
        f"lb{lb}_h{hold}_z1.0": round2_sensitivity.daily_for(
            loaded, {"lookback": lb, "hold": hold, "entry_z": 1.0}
        )
        for lb in (384, 480, 576)
        for hold in (384, 480, 576)
    }


def family_max(loaded: dict[str, pd.DataFrame], *, reference: float, draws: int = DRAWS):
    """Round 2's decision rule, applied unchanged to the supplemental family."""
    return round2_sensitivity.power_under_the_family_max_rule(
        family_of_nine(loaded), effects=(reference,), draws=draws
    )


__all__ = [
    "CENTRE",
    "DRAWS",
    "SEED",
    "family_max",
    "family_of_nine",
    "rate_comparison",
    "two_sided_power",
]
