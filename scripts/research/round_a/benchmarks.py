"""The nulls Round A's first draft did not have, and which change its answers.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

Three benchmarks, each added because a review role showed the corresponding
headline was unsupported without it.

**1. The atlas needs a null, because the null wins.** `MFE = max(up, down)` over
a window is an oracle taken over *two* directions, and for a driftless random
walk `E[median max|W|] ≈ 1.1 · σ√H`. So "median MFE is 34× the cost" is close to
an identity in `σ√H / cost` and contains no market information. Measured: an
IID shuffle of each pair's own bars — same marginals, all serial dependence
destroyed — scores **higher** than the real series on every horizon and every
panel. A market with provably zero exploitable structure beats the real one on
the metric the first draft used to declare the opportunity abundant.

What replaces it is the quantity that actually binds: the **break-even
information coefficient**, `cost / sd(terminal move)`. That is the signed edge a
strategy must have for the movement to pay for the spread, and it is comparable
to the ICs this programme has already measured.

**2. The family-max must be studentized.** `familywise.family_wise` maxes the raw
net *total*, and cells here fire on 8% to 50% of bars, so their null standard
deviations span 118 to 540. The null max is then produced almost entirely by the
frequent cells and a rare cell is compared against a yardstick built from
something else. Max-`t` (Westfall–Young) puts every cell on the same scale.

**3. The screen itself has a false-positive rate, and nobody had measured it.**
The six-condition structural screen is a decision rule over 39 correlated cells.
"Exactly one passed" means nothing until `P(at least one passes | null)` is
known. It is the number the branch decision turns on.
"""

from __future__ import annotations

from typing import Any, Final

import numpy as np
import pandas as pd

from scripts.research.exploratory_m15 import familywise

SEED: Final[int] = 20260906
SHUFFLE_DRAWS: Final[int] = 8
STUDENTIZED_DRAWS: Final[int] = 20_000
SCREEN_FWER_DRAWS: Final[int] = 4_000


def iid_shuffled(frame: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """The same bars in a random order: identical marginals, no serial structure.

    Each bar keeps its own return **and** its own intrabar high/low offsets, so
    the shuffled series has the pair's volatility and its bar shapes and nothing
    else. Any statistic a driftless random walk reproduces is a statistic about
    `σ` and `√H`, not about the market.
    """
    out = frame.copy()
    close = frame["mid_c"].to_numpy()
    steps = np.diff(close)
    order = rng.permutation(len(steps))
    walk = np.concatenate([[close[0]], close[0] + np.cumsum(steps[order])])
    for column, source in (("mid_h", "mid_h"), ("mid_l", "mid_l"), ("mid_o", "mid_o")):
        offset = (frame[source] - frame["mid_c"]).to_numpy()
        out[column] = walk + np.concatenate([[offset[0]], offset[1:][order]])
    out["mid_c"] = walk
    return out


def atlas_null(
    panel: dict[str, pd.DataFrame],
    horizons: tuple[int, ...],
    *,
    draws: int = SHUFFLE_DRAWS,
) -> dict[int, dict[str, float]]:
    """`median MFE / cost` under the IID shuffle, per horizon, pooled over pairs."""
    from scripts.research.round_a import atlas

    rng = np.random.default_rng(SEED)
    out: dict[int, dict[str, float]] = {}
    for horizon in horizons:
        ratios: list[float] = []
        reach: list[float] = []
        for _ in range(draws):
            rows = pd.concat(
                [atlas.excursions(iid_shuffled(f, rng), horizon) for f in panel.values()],
                ignore_index=True,
            )
            if rows.empty:
                continue
            ratios.append(float(np.median(rows["mfe"]) / np.median(rows["cost"])))
            reach.append(float((rows["mfe"] > 2 * rows["cost"]).mean()))
        out[horizon] = {
            "null_median_mfe_over_cost": round(float(np.mean(ratios)), 3),
            "null_p_mfe_gt_2x_cost": round(float(np.mean(reach)), 4),
            "draws": draws,
        }
    return out


def break_even_ic(panel: dict[str, pd.DataFrame], horizons: tuple[int, ...]) -> dict[int, Any]:
    """`cost / sd(terminal move)` — the signed edge the movement has to pay for.

    This is what the atlas should have reported. A direction-blind strategy
    captures **none** of the MFE however large it is; what it needs is a
    correlation with the *signed* forward return, and this is the level at which
    that correlation stops losing money.
    """
    from scripts.research.round_a import atlas

    out: dict[int, Any] = {}
    for horizon in horizons:
        rows = pd.concat([atlas.excursions(f, horizon) for f in panel.values()], ignore_index=True)
        if rows.empty:
            continue
        sd = float(rows["terminal_move"].std())
        cost = float(np.median(rows["cost"]))
        out[horizon] = {
            "sd_terminal_move_pips": round(sd, 2),
            "median_cost_pips": round(cost, 3),
            "break_even_ic": round(cost / sd, 5) if sd else None,
        }
    return out


def studentized_family_max(
    daily: dict[str, pd.Series], *, draws: int = STUDENTIZED_DRAWS
) -> dict[str, Any]:
    """Max-`t` over the family, so a rare cell is not judged by a frequent one.

    The committed `family_wise` maxes the raw total. With per-cell null sds
    spanning 118 to 540 on this family, that yardstick belongs to the cells that
    fire most often. Dividing each cell's total by its own null sd before taking
    the maximum is the standard Westfall–Young step and is what makes the
    comparison scale-free.
    """
    names = sorted(daily)
    aligned = pd.concat([daily[n].rename(n) for n in names], axis=1).fillna(0.0)
    values = aligned.to_numpy()
    observed = values.sum(axis=0)
    blocks = np.arange(len(aligned)) // familywise.BLOCK_DAYS
    n_blocks = int(blocks.max()) + 1

    rng = np.random.default_rng(SEED)
    null_totals = np.empty((draws, len(names)))
    for draw in range(draws):
        signs = rng.choice((-1.0, 1.0), size=n_blocks)[blocks]
        null_totals[draw] = (values * signs[:, None]).sum(axis=0)
    sd = null_totals.std(axis=0)
    sd[sd == 0] = np.inf

    observed_t = observed / sd
    null_t = null_totals / sd
    #: two-sided, because the plan treats a negative drift as informative
    null_max_abs = np.abs(null_t).max(axis=1)
    null_max_signed = null_t.max(axis=1)
    best = int(np.argmax(np.abs(observed_t)))
    return {
        "statistic": "max-t (Westfall-Young), each cell divided by its own null sd",
        "draws": draws,
        "n_cells": len(names),
        "null_sd_range": [round(float(sd.min()), 1), round(float(sd[np.isfinite(sd)].max()), 1)],
        "best_cell": names[best],
        "best_t": round(float(observed_t[best]), 3),
        "family_wise_p_two_sided": round(float((null_max_abs >= abs(observed_t[best])).mean()), 4),
        "family_wise_p_one_sided": round(float((null_max_signed >= observed_t[best]).mean()), 4),
        "per_cell_t": {name: round(float(observed_t[i]), 3) for i, name in enumerate(names)},
    }


def screen_false_positive_rate(
    per_cell: dict[str, dict[str, Any]],
    *,
    draws: int = SCREEN_FWER_DRAWS,
    deciding: tuple[str, ...],
) -> dict[str, Any]:
    """`P(at least one of 39 cells passes all six conditions | null)`.

    The six-condition screen is a decision rule, and a decision rule over 39
    correlated cells has a false-positive rate. Until it is measured, "exactly
    one passed" is uninterpretable — it could be a finding or the ordinary
    outcome. This resamples each panel's daily series with the same shared block
    sign-flip the family-max uses, rescales each cell's reported effect by
    `flipped total / observed total`, and re-applies conditions 1, 2, 3 and 6
    exactly as the driver does. Conditions 4 and 5 do not depend on the sign
    draw and are carried through unchanged.

    The rescaling is an approximation: it flips the *aggregate* rather than
    re-deriving each entry, so a cell's per-entry effect moves proportionally to
    its daily total. It is accurate enough for an order of magnitude, which is
    all a false-positive rate needs to be to settle a branch decision.
    """
    rng = np.random.default_rng(SEED)
    cells = sorted(per_cell)
    series = {
        cid: {panel: per_cell[cid][panel]["daily"] for panel in per_cell[cid]} for cid in cells
    }
    passes = np.zeros(draws, dtype=int)
    for draw in range(draws):
        survivors = 0
        flipped: dict[str, dict[str, float]] = {}
        for panel in {p for cid in cells for p in series[cid]}:
            members = [cid for cid in cells if panel in series[cid]]
            if not members:
                continue
            aligned = pd.concat([series[cid][panel].rename(cid) for cid in members], axis=1).fillna(
                0.0
            )
            n_blocks = int(np.arange(len(aligned)).max() // familywise.BLOCK_DAYS) + 1
            signs = rng.choice((-1.0, 1.0), size=n_blocks)[
                np.arange(len(aligned)) // familywise.BLOCK_DAYS
            ]
            totals = (aligned.to_numpy() * signs[:, None]).sum(axis=0)
            for i, cid in enumerate(members):
                observed_total = float(aligned.iloc[:, i].sum())
                scale = totals[i] / observed_total if observed_total else 0.0
                flipped.setdefault(cid, {})[panel] = scale

        for cid in cells:
            record = per_cell[cid]
            if not all(panel in record for panel in deciding):
                continue
            scales = flipped.get(cid, {})
            effects = [
                record[panel]["effect_over_cost"] * scales.get(panel, 0.0) for panel in deciding
            ]
            if (effects[0] > 0) != (effects[1] > 0):
                continue
            if not all(abs(e) >= 2.0 for e in effects):
                continue
            #: condition 2 uses the third panel when it is present
            third = [p for p in record if p not in deciding]
            if third:
                other = record[third[0]]["effect_over_cost"] * scales.get(third[0], 0.0)
                if other * effects[0] < 0 and abs(other) > min(abs(e) for e in effects):
                    continue
            #: condition 6, on the flipped series, using the plan's literal rule
            survives = True
            for panel in deciding:
                flipped_series = record[panel]["daily"] * scales.get(panel, 0.0)
                total = float(flipped_series.sum())
                best10 = float(np.sort(flipped_series.to_numpy())[::-1][:10].sum())
                if total == 0 or (total > 0) != (total - best10 > 0):
                    survives = False
                    break
            if not survives:
                continue
            #: conditions 4 and 5 do not depend on the draw
            if not record[deciding[0]].get("passes_static", True):
                continue
            survivors += 1
        passes[draw] = survivors
    return {
        "draws": draws,
        "p_at_least_one_passes": round(float((passes >= 1).mean()), 4),
        "mean_cells_passing": round(float(passes.mean()), 3),
        "distribution": {
            int(k): int(v) for k, v in zip(*np.unique(passes, return_counts=True), strict=True)
        },
        "note": "the six-condition screen's own false-positive rate; the branch turns on it",
    }


__all__ = [
    "SCREEN_FWER_DRAWS",
    "SEED",
    "SHUFFLE_DRAWS",
    "STUDENTIZED_DRAWS",
    "atlas_null",
    "break_even_ic",
    "iid_shuffled",
    "screen_false_positive_rate",
    "studentized_family_max",
]
