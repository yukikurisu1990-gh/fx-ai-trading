"""What the momentum round can and cannot separate from noise.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `POST_HOC_EXPLORATORY_HYPOTHESIS`.

The first draft of this round reported point estimates and no interval, no
p-value and no named alternative, and then argued from three statistics that an
audit showed carry no information at all: "IC positive in only 1 of 8 blocks"
(the null's own expectation is 1.06 of 8), "0 of 20 leave-one-pair-out"
(arithmetically forced once the pooled estimate is that negative), and a headline
IC that sits inside its own permutation band. This module computes the things
that do carry information, so the document can argue from them instead.

Three nulls, and why each is built the way it is
------------------------------------------------

* **Joint permutation.** Every pair's bar moves are permuted with **one shared
  key**, so the twenty series stay contemporaneously dependent and the null is a
  cross-sectionally correlated random walk rather than twenty independent ones.
  The reversal rounds established that permuting pairs independently shrinks the
  null's spread by about 40% and inflates every z.
* **Overlapping-window IC bias.** A 480-bar lookback against a 480-bar forward
  return is mechanically negatively correlated under a random walk, and the bias
  scales with `lookback / n`. Comparing a 730-day IC with a 248-day IC without
  measuring that bias compares two different quantities — which is exactly what
  the first draft's three-span table did.
* **Breadth.** How many of the twenty pairs carry a positive IC is a different
  statistic from the mean IC and has a different null; with about five
  effectively independent pairs, its null is nowhere near 10 of 20.

Power is reported against **named alternatives**, never at the observed effect.
`supplemental_power.two_sided_power`'s own docstring calls observed power "a
monotone restatement of the p-value, and near useless for reading a null
result", and the first draft led with it anyway.
"""

from __future__ import annotations

from typing import Any, Final

import numpy as np
import pandas as pd
from scipy import stats

from scripts.research.exploratory_m15 import familywise

SEED: Final[int] = 20260906
BOOTSTRAP_DRAWS: Final[int] = 20_000
PERMUTATION_DRAWS: Final[int] = 300
Z_ALPHA_TWO_SIDED: Final[float] = 1.959964


def _daily(series: pd.Series) -> np.ndarray:
    return series.groupby(series.index.floor("D")).sum().to_numpy()


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


def interval(daily: pd.Series, *, draws: int = BOOTSTRAP_DRAWS) -> dict[str, Any]:
    """The point estimate with an interval and a p-value, which the doc lacked."""
    rng = np.random.default_rng(SEED)
    values = _daily(daily)
    boot = _block_bootstrap(values, rng, draws)
    rate = float(values.mean())
    se = float(boot.std())
    total_se = se * len(values)
    return {
        "days": int(len(values)),
        "total_pips_per_pair": round(float(values.sum()), 1),
        "rate_pips_per_pair_per_day": round(rate, 4),
        "rate_se": round(se, 4),
        "rate_ci95": [
            round(float(np.percentile(boot, 2.5)), 4),
            round(float(np.percentile(boot, 97.5)), 4),
        ],
        "total_ci95": [
            round(float(np.percentile(boot, 2.5)) * len(values), 1),
            round(float(np.percentile(boot, 97.5)) * len(values), 1),
        ],
        "total_se": round(total_se, 1),
        "p_two_sided_vs_zero": round(float(2 * min((boot <= 0).mean(), (boot >= 0).mean())), 4),
        "share_of_days_positive": round(float((values > 0).mean()), 3),
    }


def power_against(
    daily: pd.Series, alternatives: dict[str, float], *, draws: int = BOOTSTRAP_DRAWS
):
    """Power against effects someone actually hypothesised, and the rejection of each.

    `alternatives` maps a name to a **total** pips-per-pair effect over this span.
    Two numbers per alternative: the power the study had to detect it, and
    whether the observed result is inconsistent with it.
    """
    rng = np.random.default_rng(SEED)
    values = _daily(daily)
    observed = float(values.sum())
    sd = float(_block_bootstrap(values, rng, draws).std()) * len(values)
    out: dict[str, Any] = {
        "observed_net_pips_per_pair": round(observed, 1),
        "effect_sd": round(sd, 1),
    }
    for name, effect in alternatives.items():
        z = (observed - effect) / sd
        out[name] = {
            "alternative_total": round(float(effect), 1),
            "power_to_detect_it": round(
                float(1 - stats.norm.cdf(Z_ALPHA_TWO_SIDED - abs(effect) / sd)), 3
            ),
            "z_observed_vs_alternative": round(float(z), 2),
            "p_two_sided_observed_vs_alternative": round(float(2 * stats.norm.cdf(-abs(z))), 4),
        }
    return out


def _joint_permutation(loaded: dict[str, pd.DataFrame], rng: np.random.Generator):
    """One permutation of the **panel's rows**, so cross-pair dependence survives.

    Two earlier constructions here got this wrong and the error is worth stating
    because it decides whether the observed IC is inside its null band.

    The first truncated every pair to the shortest and applied one *positional*
    permutation. Pair bar counts differ by up to 152 over this span, so "row 100"
    is a different instant for different pairs.

    The second delegated to `round2_power.shared_random_walk`, which keys the
    permutation on timestamps — correct when every pair carries the same
    timestamps, which is what that round had. Here they do not: each pair's moves
    are reordered into *its own* index space, so a move two pairs shared at one
    instant lands at two different output positions and the pairs come apart.

    Both under-preserve dependence, and averaging twenty less-dependent series
    shrinks the spread of the mean: they gave null sds of 1.83% and 1.98% against
    3.3% here, implying about 15 effectively independent pairs where this corpus
    has five to six. `effective_independent_pairs` is returned beside the null so
    the construction is checked rather than asserted.

    So: inner-join every pair onto the timestamps they all share, permute the rows
    of that panel **once**, and rebuild each walk from its own permuted column.
    Contemporaneous moves stay contemporaneous.
    """
    panel = pd.concat(
        [frame.set_index("ts")["mid_c"].rename(pair) for pair, frame in loaded.items()],
        axis=1,
        join="inner",
    )
    moves = panel.diff().iloc[1:]
    order = rng.permutation(len(moves))
    walked = panel.iloc[0].to_numpy() + moves.to_numpy()[order].cumsum(axis=0)
    walked = pd.DataFrame(walked, columns=panel.columns, index=panel.index[1:])
    out: dict[str, pd.DataFrame] = {}
    for pair, frame in loaded.items():
        copy = frame.set_index("ts").loc[walked.index].copy()
        copy["mid_c"] = walked[pair].to_numpy()
        out[pair] = copy.reset_index()
    return out


def ic_null(
    loaded: dict[str, pd.DataFrame],
    *,
    lookback: int,
    horizon: int,
    draws: int = PERMUTATION_DRAWS,
) -> dict[str, Any]:
    """The overlapping-window IC bias, and the breadth null beside it.

    Returns the observed mean IC and positive-pair count with the permutation
    distribution of each, so a reader can see whether either is outside its band
    rather than being told it is small.
    """
    from scripts.research.exploratory_m15.momentum_replication import mean_ic

    observed_ic, observed_breadth, counted = mean_ic(loaded, lookback=lookback, horizon=horizon)
    rng = np.random.default_rng(SEED)
    ics = np.empty(draws)
    breadths = np.empty(draws)
    singles: list[float] = []
    first = next(iter(loaded))
    for draw in range(draws):
        walked = _joint_permutation(loaded, rng)
        ics[draw], breadths[draw], _ = mean_ic(walked, lookback=lookback, horizon=horizon)
        singles.append(mean_ic({first: walked[first]}, lookback=lookback, horizon=horizon)[0])
    per_pair_sd = float(np.std(singles))
    return {
        "pairs": counted,
        "observed_mean_ic": round(observed_ic, 4),
        "observed_pairs_with_positive_ic": observed_breadth,
        "draws": draws,
        "null_mean_ic": round(float(ics.mean()), 4),
        "null_ic_sd": round(float(ics.std()), 4),
        "null_ic_ci95": [
            round(float(np.percentile(ics, 2.5)), 4),
            round(float(np.percentile(ics, 97.5)), 4),
        ],
        "p_two_sided_ic": round(
            float(2 * min((ics <= observed_ic).mean(), (ics >= observed_ic).mean())), 4
        ),
        "bias_adjusted_mean_ic": round(observed_ic - float(ics.mean()), 4),
        "null_mean_breadth": round(float(breadths.mean()), 2),
        "null_breadth_ci95": [
            int(np.percentile(breadths, 2.5)),
            int(np.percentile(breadths, 97.5)),
        ],
        "p_one_sided_breadth_low": round(float((breadths <= observed_breadth).mean()), 4),
        #: A self-check on the construction, not a result. Twenty pairs whose
        #: dependence has been preserved should behave like five or six
        #: independent ones, which is what every round of this programme has
        #: measured. A number near twenty means the null decorrelated the panel
        #: and every z computed against it is inflated.
        "effective_independent_pairs": round(float((per_pair_sd / ics.std()) ** 2), 2),
        "null_per_pair_ic_sd": round(float(per_pair_sd), 4),
    }


def difference(a: pd.Series, b: pd.Series, *, draws: int = BOOTSTRAP_DRAWS) -> dict[str, Any]:
    """Whether two spans' daily rates differ, on the rate scale."""
    rng = np.random.default_rng(SEED)
    boot_a = _block_bootstrap(_daily(a), rng, draws)
    boot_b = _block_bootstrap(_daily(b), rng, draws)
    delta = boot_a - boot_b
    observed = float(_daily(a).mean() - _daily(b).mean())
    return {
        "rate_difference": round(observed, 4),
        "se": round(float(delta.std()), 4),
        "z": round(float(observed / delta.std()), 2),
        "ci95": [
            round(float(np.percentile(delta, 2.5)), 4),
            round(float(np.percentile(delta, 97.5)), 4),
        ],
        "p_two_sided": round(float(2 * min((delta >= 0).mean(), (delta <= 0).mean())), 4),
    }


__all__ = [
    "BOOTSTRAP_DRAWS",
    "PERMUTATION_DRAWS",
    "SEED",
    "difference",
    "ic_null",
    "interval",
    "power_against",
]
