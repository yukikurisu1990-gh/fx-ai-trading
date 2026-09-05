"""The multiple-comparison test the long-horizon result never had.

`NON_DECISION_BEARING_EXPLORATORY_ONLY`.

Two roles produced apparently opposite verdicts:

* the ML family ran a family-wise block sign-flip permutation over 57 variants
  and got **p = 0.699** for its best, with the null's max median (+226.5
  pips/pair) *above* the observed best (+173.3);
* the regime/session family found the reversal works at a **4–6 day** horizon —
  132/132 and 198/198 walk-forward cells net-positive in the held-out half — and
  said in terms that its 1,078-fit search had **never** been corrected for
  multiple comparison, and that the ML role's `p` "neither refutes nor defends"
  it because that family contained no long-horizon variant.

They are not opposite. They are two searches over different spaces, one of which
was tested and one of which was not. This module tests the second.

The null
--------

Block sign-flip on the pooled **daily** net-pip series: draw a random ±1 per
5-day block and apply the **same** draw to every variant, so the null keeps the
between-variant correlation that a single-dataset search creates. The statistic
is the maximum net across the family; the p-value is the fraction of draws whose
maximum reaches the observed maximum. Blocks preserve the autocorrelation a
multi-day holding period induces; sharing the draw is what makes it *family*-wise
rather than a per-variant test repeated.

What it can and cannot say
--------------------------

It corrects for **this** search. It cannot correct for the searches that came
before it in the same corpus, and it says nothing about whether an eight-month
sample generalises.
"""

from __future__ import annotations

from typing import Any, Final

import numpy as np
import pandas as pd

from scripts.research.exploratory_m15 import bars as bars_module
from scripts.research.exploratory_m15 import engine

BLOCK_DAYS: Final[int] = 5
DRAWS: Final[int] = 20_000
SEED: Final[int] = 20260905


def daily_net(
    pairs, signal_fn, kwargs: dict[str, Any], *, cost_multiplier: float = 1.0
) -> pd.Series:
    """Pooled equal-weight net pips per pair, resampled to UTC days."""
    columns = []
    for pair in pairs:
        frame = bars_module.load(pair)
        result = engine.evaluate(
            frame,
            signal_fn(frame, **kwargs),
            name="x",
            pair=pair,
            cost_multiplier=cost_multiplier,
        )
        columns.append(result.net.set_axis(frame["ts"]).rename(pair))
    pooled = pd.concat(columns, axis=1).fillna(0.0).mean(axis=1)
    return pooled.groupby(pooled.index.floor("D")).sum()


def family_wise(daily: dict[str, pd.Series], *, draws: int = DRAWS) -> dict[str, Any]:
    """Block sign-flip over a family, one shared draw per iteration."""
    names = sorted(daily)
    aligned = pd.concat([daily[name].rename(name) for name in names], axis=1).fillna(0.0)
    values = aligned.to_numpy()
    n_days = len(aligned)
    observed = values.sum(axis=0)
    blocks = np.arange(n_days) // BLOCK_DAYS
    n_blocks = int(blocks.max()) + 1

    rng = np.random.default_rng(SEED)
    null_max = np.empty(draws)
    null_each = np.zeros((draws, len(names)))
    for draw in range(draws):
        signs = rng.choice((-1.0, 1.0), size=n_blocks)[blocks]
        totals = (values * signs[:, None]).sum(axis=0)
        null_each[draw] = totals
        null_max[draw] = totals.max()

    best = int(np.argmax(observed))
    per_variant = {
        name: {
            "net_pips_per_pair": round(float(observed[i]), 1),
            "null_sd": round(float(null_each[:, i].std()), 1),
            "z": round(float(observed[i] / null_each[:, i].std()), 2)
            if null_each[:, i].std() > 0
            else 0.0,
            "p_individual": round(float((null_each[:, i] >= observed[i]).mean()), 4),
        }
        for i, name in enumerate(names)
    }
    return {
        "method": (
            "block sign-flip on pooled daily net pips, 5-day blocks, one sign draw shared "
            "across every variant so the null keeps the between-variant correlation a "
            "single-dataset search creates"
        ),
        "draws": draws,
        "block_days": BLOCK_DAYS,
        "n_days": int(n_days),
        "n_variants": len(names),
        "best_variant": names[best],
        "best_net_pips_per_pair": round(float(observed[best]), 1),
        "family_wise_p_for_the_best": round(float((null_max >= observed[best]).mean()), 4),
        "family_null_max_median": round(float(np.median(null_max)), 1),
        "family_null_max_p95": round(float(np.percentile(null_max, 95)), 1),
        "per_variant": per_variant,
    }


__all__ = ["BLOCK_DAYS", "DRAWS", "daily_net", "family_wise"]
