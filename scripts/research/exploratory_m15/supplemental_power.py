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
#: The candidate is **not** restated here. An audit found a `CENTRE` literal in
#: this module that no code read and no test pinned, while the driver built the
#: real one from `round2.CENTRE` -- two copies of a frozen parameter, one of them
#: free to drift. The single definition lives in
#: `supplemental_replication.FROZEN`, which reads `round2.CENTRE`.


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
        #: A percentile-bootstrap (CI-inversion) p, not a null-distribution p:
        #: the resampling distribution is centred on the observed difference,
        #: so this reports how far zero sits in its tail. It also treats the
        #: original period's rate as a fixed comparator, and that period is
        #: where the candidate's neighbourhood was chosen -- which biases the
        #: difference away from zero.
        "p_two_sided_no_difference_ci_inversion": round(
            float(2 * min((difference >= 0).mean(), (difference <= 0).mean())), 4
        ),
    }
    out["projection"] = {
        "supplemental_net_if_original_rate_held": round(projected, 1),
        "supplemental_net_observed": round(float(_daily(supplemental_daily).sum()), 1),
        "shortfall_pips_per_pair": round(float(_daily(supplemental_daily).sum() - projected), 1),
    }

    #: Chronological. Concatenating the later period first and then taking
    #: contiguous blocks bootstraps a series whose "adjacent" days include one
    #: pair 20 months apart; an audit measured the resulting SE at 0.3563 against
    #: 0.3862 for the correctly ordered series, i.e. a CI about 8% too tight.
    pooled_series = pd.concat([supplemental_daily, original_daily]).sort_index()
    pooled = _daily(pooled_series)
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


def two_sided_power(
    daily: pd.Series, *, alternative: float | None = None, draws: int = DRAWS
) -> dict[str, Any]:
    """Power against a **pre-specified** alternative, plus the observed-effect one.

    `alternative` is the effect the study was designed to detect — here, the
    total the period would have produced had the development rate held. That is
    the decision-relevant number and it is reported first.

    `power_at_observed_absolute_effect` is kept because the plan asks for it, but
    it is *observed power*: a monotone restatement of the p-value, and near
    useless for reading a null result. An audit pointed out that leading with it
    understated this study by a factor of about 1.4 — in the direction of the
    conclusion, which is not a reason to leave it uncorrected.

    Power on `|effect|`, so a negative effect is not silently read as no effect.
    """
    rng = np.random.default_rng(SEED)
    values = _daily(daily)
    boot = _block_bootstrap(values, rng, draws) * len(values)
    observed = float(values.sum())
    sd = float(boot.std())
    z_alpha, z_power = 1.959964, 0.841621
    mde = (z_alpha + z_power) * sd
    power = float(1 - stats.norm.cdf(z_alpha - abs(observed) / sd)) if sd > 0 else 0.0
    multiple = (mde / abs(observed)) ** 2 if observed else float("inf")
    #: Trading days and calendar days are different units, and `round2_power`
    #: reports the calendar one. Reporting only the first made this round's "+190
    #: days" look like a correction of Round 2's "+220" for the same quantity.
    trading_days = int(len(values))
    index = values_index(daily)
    calendar_days = int((index.max() - index.min()).days) + 1
    out = {
        "observed_net_pips_per_pair": round(observed, 1),
        "sign": "positive" if observed > 0 else "negative",
        "effect_sd": round(sd, 1),
        "minimum_detectable_effect_two_sided_80pct": round(mde, 1),
        "abs_observed_over_mde": round(abs(observed) / mde, 2) if mde else None,
        "power_at_observed_absolute_effect": round(power, 2),
        "trading_days": trading_days,
        "calendar_span_days": calendar_days,
        "span_multiple_for_80pct": round(float(multiple), 2),
        "additional_trading_days_needed": int(max(0.0, multiple * trading_days - trading_days)),
        "additional_calendar_days_needed": int(max(0.0, multiple * calendar_days - calendar_days)),
    }
    if alternative is not None:
        out["pre_specified_alternative"] = round(float(alternative), 1)
        out["power_against_pre_specified_alternative"] = round(
            float(1 - stats.norm.cdf(z_alpha - abs(alternative) / sd)) if sd > 0 else 0.0, 3
        )
    return out


def values_index(daily: pd.Series) -> pd.DatetimeIndex:
    grouped = daily.groupby(daily.index.floor("D")).sum()
    return pd.DatetimeIndex(grouped.index)


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
    """Round 2's decision rule, applied unchanged to the supplemental family.

    `reference` is the **pre-specified alternative** — the total this period
    would have produced had the development rate held — not the development
    period's own total. The two differ because the spans differ, and using the
    latter reports power against an effect nobody hypothesised for this window.
    """
    return round2_sensitivity.power_under_the_family_max_rule(
        family_of_nine(loaded), effects=(reference,), draws=draws
    )


__all__ = [
    "DRAWS",
    "SEED",
    "family_max",
    "family_of_nine",
    "rate_comparison",
    "two_sided_power",
    "values_index",
]
