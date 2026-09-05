"""The three checks the review found missing, as committed code.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

Each of these was raised by a review role against a first pass that either did
not run it or ran it in a scratch script nobody could re-run. They are here
because the finding they produce is the round's finding.

1. **Power against the decision rule that was actually pre-registered.** §9 of the
   plan commits to a family-max sign-flip test, so the critical value is the
   null's max, not a per-variant z. A single-variant power calculation answers a
   question the round did not ask, and it answers it far too generously.
2. **How much of the result is a handful of days.** The pooled daily series has a
   median of zero and is positive on about half its days. If dropping three days
   out of two hundred moves the family-wise `p` across the conventional
   threshold, the threshold was never the binding fact.
3. **The JPY bloc as its own family.** Six of the twenty pairs share a currency
   and most of the P&L. Correcting them, and the other fourteen, as separate
   families is the only way to see whether "a thin effect everywhere plus a large
   JPY component" survives the same test the headline had to pass.
"""

from __future__ import annotations

from typing import Any, Final

import numpy as np
import pandas as pd
from scipy import stats

from scripts.research.exploratory_m15 import PAIRS, engine, familywise, round2

SEED: Final[int] = 20260905
JPY: Final[tuple[str, ...]] = tuple(p for p in PAIRS if "JPY" in p)
NON_JPY: Final[tuple[str, ...]] = tuple(p for p in PAIRS if p not in JPY)


def daily_for(loaded: dict[str, pd.DataFrame], config: dict, *, pairs=None) -> pd.Series:
    """Phase-averaged pooled daily net over the pre-registered 8 phases."""
    chosen = list(pairs or loaded)
    hold = int(config["hold"])
    phases = list(range(0, hold, max(1, hold // round2.N_PHASES)))[: round2.N_PHASES]
    columns = []
    for pair in chosen:
        frame = loaded[pair]
        total = None
        for phase in phases:
            signal = round2._signal(
                frame,
                lookback=int(config["lookback"]),
                hold=hold,
                entry_z=float(config["entry_z"]),
                phase=phase,
                atr_bucket=str(config.get("atr_bucket", "all")),
            )
            result = engine.evaluate(frame, signal, name="s", pair=pair)
            total = result.net if total is None else total.add(result.net, fill_value=0.0)
        columns.append((total / len(phases)).set_axis(frame["ts"]).rename(pair))
    pooled = pd.concat(columns, axis=1).fillna(0.0).mean(axis=1)
    return pooled.groupby(pooled.index.floor("D")).sum()


def power_under_the_family_max_rule(
    daily: dict[str, pd.Series], *, effects=(262.1,), draws: int = 20_000
) -> dict[str, Any]:
    """Power for the test the plan pre-registered, not for a per-variant z.

    The decision rule is "the family maximum exceeds the null's 95th
    percentile". A candidate has to clear that, and the null max of a
    27-variant family sits far above any single variant's null. Computing power
    against a single-variant critical value overstates it by a wide margin.
    """
    result = familywise.family_wise(daily, draws=draws)
    names = sorted(daily)
    aligned = pd.concat([daily[n].rename(n) for n in names], axis=1).fillna(0.0)
    values = aligned.to_numpy()
    n_days = len(aligned)
    blocks = np.arange(n_days) // familywise.BLOCK_DAYS
    n_blocks = int(blocks.max()) + 1
    rng = np.random.default_rng(SEED)
    null_max = np.empty(draws)
    for draw in range(draws):
        signs = rng.choice((-1.0, 1.0), size=n_blocks)[blocks]
        null_max[draw] = (values * signs[:, None]).sum(axis=0).max()
    critical = float(np.percentile(null_max, 95))

    #: the spread of the family maximum under the alternative, taken from the
    #: block bootstrap of the observed series -- the same variance the effect has
    best = max(names, key=lambda n: daily[n].sum())
    series = daily[best].to_numpy()
    chunks = [
        series[i : i + familywise.BLOCK_DAYS] for i in range(0, len(series), familywise.BLOCK_DAYS)
    ]
    boot = np.asarray(
        [
            np.concatenate([chunks[j] for j in rng.integers(0, len(chunks), len(chunks))]).sum()
            for _ in range(draws)
        ]
    )
    sd = float(boot.std())
    powers = {
        str(effect): round(float(1 - stats.norm.cdf((critical - effect) / sd)), 3)
        for effect in effects
    }
    mde = critical + stats.norm.ppf(0.80) * sd
    reference = float(effects[0])
    return {
        "rule": "family maximum exceeds the null max 95th percentile",
        "critical_value": round(critical, 1),
        "effect_sd_from_block_bootstrap": round(sd, 1),
        "power_at": powers,
        "minimum_detectable_effect_80pct": round(float(mde), 1),
        "span_multiple_for_80pct": round(float((mde / reference) ** 2), 2)
        if reference > 0
        else None,
        "family_wise_p": result["family_wise_p_for_the_best"],
        "null_max_p95": result["family_null_max_p95"],
    }


def drop_best_days(daily: dict[str, pd.Series], *, counts=(0, 1, 3, 5, 10)) -> list[dict[str, Any]]:
    """How much of the family-wise `p` rests on the best few days."""
    names = sorted(daily)
    best = max(names, key=lambda n: daily[n].sum())
    order = daily[best].sort_values(ascending=False).index
    out = []
    for count in counts:
        dropped = set(order[:count])
        trimmed = {n: s[~s.index.isin(dropped)] for n, s in daily.items()}
        result = familywise.family_wise(trimmed, draws=20_000)
        out.append(
            {
                "days_dropped": count,
                "best_net": result["best_net_pips_per_pair"],
                "family_wise_p": result["family_wise_p_for_the_best"],
            }
        )
    return out


def bloc_families(loaded: dict[str, pd.DataFrame]) -> dict[str, Any]:
    """The same test on the JPY six and the non-JPY fourteen, separately."""
    out: dict[str, Any] = {}
    for label, pairs in (("all_20", PAIRS), ("jpy_6", JPY), ("non_jpy_14", NON_JPY)):
        daily = {
            round2.name_of(cfg): daily_for(loaded, cfg, pairs=pairs)
            for cfg in round2.primary_family()
        }
        result = familywise.family_wise(daily)
        out[label] = {
            "pairs": len(pairs),
            "best_variant": result["best_variant"],
            "best_net_pips_per_pair": result["best_net_pips_per_pair"],
            "family_wise_p": result["family_wise_p_for_the_best"],
            "null_max_median": result["family_null_max_median"],
        }
    return out


__all__ = [
    "JPY",
    "NON_JPY",
    "bloc_families",
    "daily_for",
    "drop_best_days",
    "power_under_the_family_max_rule",
]
