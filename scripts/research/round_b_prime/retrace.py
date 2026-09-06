"""B′-2 — excursion-anchored retrace geometry, against a matched null.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

Every earlier round decided on a **clock**: the move over the last `L` bars,
re-decided every `H` bars. All of them failed because the sign of that move does
not persist across periods. This one anchors on the **path** — the first bar at
which a cumulative move reaches `k · σ` scaled to the elapsed time — and asks a
question that does not require the sign to persist at all: *given that a move of
that size has completed, what shape does the path take afterwards?*

The selection is the whole problem
----------------------------------

Conditioning on "a large move just happened" picks a point near a local extreme
of the sampled path, and a partial retrace follows **under a random walk too**.
So the null is not "shuffle and see": it runs the **identical anchor detector and
the identical retrace measurement** on a series whose `|r_t|` is unchanged at
every bar and whose signs are re-drawn. The anchor-selection geometry is
reproduced rather than assumed away, and any difference is attributable to
directional dependence.

Rules fixed in the plan, so a path is never read favourably
-----------------------------------------------------------

* **Same-bar ambiguity.** M15 OHLC does not say whether the high or the low came
  first inside a bar. When a bar could satisfy two conditions, the **adverse one
  is taken first**. The count of ambiguous bars is reported.
* **Weekend gaps.** An anchor or a level crossed by a gap wider than one bar's
  spacing is tagged and reported separately. Structure that lives only there is
  recorded as weak.
* **Timeout and non-overlap.** If no anchor fires within `ANCHOR_TIMEOUT` bars
  the reference advances; consecutive anchors never share a reference.
"""

from __future__ import annotations

from typing import Any, Final

import numpy as np
import pandas as pd

from scripts.research.round_b_prime import (
    ANCHOR_TIMEOUT,
    EXCURSION_SIGMAS,
    HTF_FAST,
    HTF_RANGE_WINDOW,
    HTF_SLOW,
    NULL_DRAWS,
    OBSERVATION_WINDOW,
    RV_WINDOW,
    SEED,
    nulls,
)

#: Retrace levels the plan names, as fractions of the realised excursion.
RETRACE_LEVELS: Final[tuple[float, ...]] = (0.25, 0.50, 1.00)
#: The observation window is this multiple of the excursion's own duration.
WINDOW_MULTIPLE: Final[int] = 4
BAR_SECONDS: Final[int] = 900


def trailing_sigma(frame: pd.DataFrame) -> np.ndarray:
    """Per-bar volatility in **price** units, backward-looking, shifted one bar."""
    pips = frame["mid_c"].diff() / frame["pip_size"]
    sigma = pips.rolling(RV_WINDOW, min_periods=RV_WINDOW // 2).std().shift(1)
    return (sigma * frame["pip_size"]).to_numpy()


def htf_context(frame: pd.DataFrame) -> dict[str, np.ndarray]:
    """The two pre-registered context variables. Two states each, nothing more."""
    close = frame["mid_c"]
    fast = close - close.shift(HTF_FAST)
    slow = close - close.shift(HTF_SLOW)
    aligned = np.where(
        np.isfinite(fast) & np.isfinite(slow) & (np.sign(fast) == np.sign(slow)) & (fast != 0),
        "aligned",
        "mixed",
    )
    position = htf_range_position(frame)
    location = np.where(
        np.isfinite(position) & ((position <= 1 / 3) | (position >= 2 / 3)), "outer", "middle"
    )
    return {"htf_trend": aligned, "htf_location": location}


def htf_range_position(frame: pd.DataFrame) -> np.ndarray:
    """Where the close sits in the trailing range, before it is bucketed.

    Split out of `htf_context` so the causality of the rolling extremes can be
    tested. It cannot be tested through the label: a bar that moves a rolling
    extreme is *itself* at that extreme, so both the shifted and the unshifted
    range put it outside the `1/3 … 2/3` band and the two bucket identically.
    The numeric position separates them; the label cannot.
    """
    close = frame["mid_c"]
    high = close.rolling(HTF_RANGE_WINDOW, min_periods=HTF_RANGE_WINDOW // 2).max().shift(1)
    low = close.rolling(HTF_RANGE_WINDOW, min_periods=HTF_RANGE_WINDOW // 2).min().shift(1)
    span = (high - low).replace(0.0, np.nan)
    return ((close - low) / span).to_numpy()


def find_anchors(frame: pd.DataFrame, k: float) -> pd.DataFrame:
    """Every `k · σ` excursion, and the retrace geometry of the window after it.

    Walks forward from a reference bar; the excursion at bar `t` is measured
    against `σ[a] · √(t − a)`, so `k` means `k` standard deviations of a random
    walk over the elapsed time rather than of a single bar.
    """
    close = frame["mid_c"].to_numpy()
    high = frame["mid_h"].to_numpy()
    low = frame["mid_l"].to_numpy()
    sigma = trailing_sigma(frame)
    stamps = frame["ts"].to_numpy()
    context = htf_context(frame)
    n = len(frame)

    rows: list[dict[str, Any]] = []
    reference = RV_WINDOW
    ambiguous = 0
    while reference < n - OBSERVATION_WINDOW - 1:
        base = close[reference]
        scale = sigma[reference]
        if not np.isfinite(scale) or scale <= 0:
            reference += 1
            continue
        limit = min(reference + ANCHOR_TIMEOUT, n - OBSERVATION_WINDOW - 1)
        elapsed = np.arange(1, limit - reference + 1)
        moves = close[reference + 1 : limit + 1] - base
        thresholds = k * scale * np.sqrt(elapsed)
        hit = np.flatnonzero(np.abs(moves) >= thresholds)
        if hit.size == 0:
            reference = limit
            continue
        offset = int(hit[0])
        anchor = reference + 1 + offset
        excursion = float(moves[offset])
        direction = 1.0 if excursion > 0 else -1.0

        #: The observation window is scale-matched to the time the move took:
        #: a flat 480 bars is 37x the span of a median 1.5-sigma excursion, so it
        #: measures the window rather than the retrace and saturates every level
        #: rate on a random walk (median fraction 2.33, reached_50 = 0.86). Plan
        #: §14 carries the table. Capped at OBSERVATION_WINDOW.
        span = min(WINDOW_MULTIPLE * (offset + 1), OBSERVATION_WINDOW)
        window = slice(anchor + 1, anchor + 1 + span)
        window_high, window_low = high[window], low[window]
        if window_high.size == 0:
            break
        anchor_price = close[anchor]

        #: retrace is movement back toward the reference; continuation is away
        if direction > 0:
            retrace_depth = anchor_price - window_low
            continuation = window_high - anchor_price
        else:
            retrace_depth = window_high - anchor_price
            continuation = anchor_price - window_low
        magnitude = abs(excursion)
        retrace_fraction = np.maximum.accumulate(retrace_depth) / magnitude
        max_retrace = float(retrace_fraction[-1])

        #: same-bar ambiguity: a bar where both the retrace level and a further
        #: continuation extreme could be attributed. The adverse one -- further
        #: continuation, i.e. against a fade -- is taken first.
        levels: dict[str, Any] = {}
        for level in RETRACE_LEVELS:
            reached = np.flatnonzero(retrace_fraction >= level)
            if reached.size:
                bar = int(reached[0])
                levels[f"bars_to_{int(level * 100)}"] = bar + 1
                levels[f"reached_{int(level * 100)}"] = True
                same_bar = continuation[bar] >= np.max(continuation[: bar + 1])
                if same_bar:
                    ambiguous += 1
                levels[f"continuation_before_{int(level * 100)}"] = float(
                    np.max(continuation[: bar + 1]) / scale
                )
            else:
                levels[f"bars_to_{int(level * 100)}"] = None
                levels[f"reached_{int(level * 100)}"] = False
                levels[f"continuation_before_{int(level * 100)}"] = None

        gap = float(pd.Timedelta(stamps[anchor] - stamps[anchor - 1]).total_seconds()) > BAR_SECONDS
        rows.append(
            {
                "anchor": anchor,
                "ts": stamps[anchor],
                "excursion_sigma": magnitude / scale,
                "direction": direction,
                "bars_to_anchor": offset + 1,
                "observation_bars": span,
                "max_retrace_fraction": max_retrace,
                "adverse_extension_sigma": float(np.max(continuation) / scale),
                "weekend_gap_anchor": bool(gap),
                "htf_trend": context["htf_trend"][anchor],
                "htf_location": context["htf_location"][anchor],
                **levels,
            }
        )
        reference = anchor
    frame_out = pd.DataFrame(rows)
    frame_out.attrs["ambiguous_bars"] = ambiguous
    return frame_out


def summarise(anchors: pd.DataFrame) -> dict[str, Any]:
    """The distribution statistics the plan asks for. No PnL, no strategy."""
    if anchors.empty:
        return {"anchors": 0}
    fraction = anchors["max_retrace_fraction"].to_numpy()
    #: The retrace in sigma units, which has no excursion in its denominator.
    #: The fraction divides by the realised excursion, and the detector does not
    #: select the same excursions on the real series and on the null -- real
    #: anchors form faster and are smaller in sigma -- so a difference in the
    #: fraction can be a difference in denominators. This says the same thing
    #: without one.
    absolute = fraction * anchors["excursion_sigma"].to_numpy()
    out: dict[str, Any] = {
        "anchors": int(len(anchors)),
        "median_retrace_fraction": round(float(np.median(fraction)), 5),
        "median_retrace_sigma": round(float(np.median(absolute)), 5),
        "mean_retrace_fraction": round(float(np.mean(fraction)), 5),
        "median_excursion_sigma": round(float(anchors["excursion_sigma"].median()), 4),
        "median_adverse_extension_sigma": round(
            float(anchors["adverse_extension_sigma"].median()), 4
        ),
        "weekend_gap_anchors": int(anchors["weekend_gap_anchor"].sum()),
        "ambiguous_bars": int(anchors.attrs.get("ambiguous_bars", 0)),
    }
    for q in (10, 25, 50, 75, 90):
        out[f"retrace_q{q:02d}"] = round(float(np.percentile(fraction, q)), 5)
    for level in RETRACE_LEVELS:
        tag = int(level * 100)
        reached = anchors[f"reached_{tag}"]
        out[f"reached_{tag}_rate"] = round(float(reached.mean()), 5)
        bars = anchors.loc[reached, f"bars_to_{tag}"].dropna()
        out[f"median_bars_to_{tag}"] = round(float(bars.median()), 1) if len(bars) else None
        cont = anchors.loc[reached, f"continuation_before_{tag}"].dropna()
        out[f"median_continuation_before_{tag}"] = (
            round(float(cont.median()), 4) if len(cont) else None
        )
    out["timeout_rate"] = round(
        float(1 - anchors[f"reached_{int(RETRACE_LEVELS[0] * 100)}"].mean()), 5
    )
    #: Plan §5.6 clause 3 asks whether the effect is carried by a handful of
    #: **days**. Computed here rather than in a subset report, so that it flows
    #: through `against_null` and the trim applies to the real *and* the null
    #: side -- a trim applied to the real median alone says nothing about
    #: `real − null`, which is the quantity the kill condition reads.
    day = pd.to_datetime(anchors["ts"], utc=True).dt.floor("D")
    load = anchors.groupby(day)["max_retrace_fraction"].sum().abs().sort_values()
    load_sigma = anchors.assign(_a=absolute).groupby(day)["_a"].sum().abs().sort_values()
    for n in (10, 20):
        if len(load) > n:
            kept = anchors[~day.isin(load.index[-n:])]
            out[f"median_retrace_fraction_excluding_top_{n}_days"] = (
                round(float(kept["max_retrace_fraction"].median()), 5) if len(kept) else None
            )
        #: the same trim on the sigma-level statistic. The monetizability
        #: package reads its kill condition off that one, and a trim computed on
        #: the fraction would be trimming a different set of days.
        if len(load_sigma) > n:
            kept_sigma = absolute[(~day.isin(load_sigma.index[-n:])).to_numpy()]
            out[f"median_retrace_sigma_excluding_top_{n}_days"] = (
                round(float(np.median(kept_sigma)), 5) if len(kept_sigma) else None
            )
    out["anchor_days"] = int(load.size)
    return out


def panel_geometry(panel: dict[str, pd.DataFrame], k: float) -> tuple[dict[str, Any], pd.DataFrame]:
    """Pooled geometry over the pairs, and the per-anchor frame for diagnostics."""
    blocks = []
    ambiguous = 0
    for pair, frame in panel.items():
        found = find_anchors(frame, k)
        ambiguous += int(found.attrs.get("ambiguous_bars", 0))
        if len(found):
            found = found.assign(pair=pair)
            blocks.append(found)
    if not blocks:
        return {"anchors": 0}, pd.DataFrame()
    stacked = pd.concat(blocks, ignore_index=True)
    stacked.attrs["ambiguous_bars"] = ambiguous
    return summarise(stacked), stacked


def null_sanity(
    *,
    pairs: int = 20,
    length: int = 50_000,
    draws: int = 20,
    seed: int = SEED,
) -> dict[str, Any]:
    """B′-2's own sanity check: the detector on a generated random walk.

    B′-1 had one from the start and B′-2 did not, which mattered: the first
    version of this round used a null that re-attached each real bar's high and
    low offsets to a **sign-flipped** return, building bars that closed down
    with the close pinned to the high. `find_anchors` reads exactly those two
    columns, so the null's retrace was inflated and the real series appeared to
    retrace *less*. A sanity check on a walk with sign-coupled bar shapes would
    have shown the bias before any panel was read.

    The walk is panel-shaped — twenty series, not one — because `k = 3.0` yields
    single-digit anchor counts on one series and cannot say anything there.
    """
    rng = np.random.default_rng(seed)
    panel = {f"W{index:02d}": nulls.random_walk_frame(length, rng) for index in range(pairs)}
    out: dict[str, Any] = {"pairs": pairs, "bars_per_pair": length, "draws": draws}
    for k in EXCURSION_SIGMAS:
        result = against_null(panel, k, draws=draws, seed=seed)
        null = result.get("null")
        out[str(k)] = (
            {
                "anchors": result["real"]["anchors"],
                "median_retrace_fraction": null["median_retrace_fraction"],
                "median_adverse_extension_sigma": null["median_adverse_extension_sigma"],
            }
            if null
            else {"anchors": result["real"].get("anchors", 0), "decidable": False}
        )
    out["note"] = (
        "a generated walk has no reversion and no continuation, so every "
        "difference here must sit inside its null band; a threshold that does "
        "not is measuring the detector or the null rather than the data"
    )
    return out


def against_null(
    panel: dict[str, pd.DataFrame],
    k: float,
    *,
    draws: int = NULL_DRAWS,
    seed: int = SEED,
    null_name: str = "N2_sign_flip",
) -> dict[str, Any]:
    """The identical detector and measurement on the matched null.

    `M1` in the plan is `N2_sign_flip`: `|r_t|` unchanged at every bar, signs
    re-drawn. The detector is re-run, so the anchor-selection geometry that makes
    a retrace likely under any process is reproduced on both sides.
    """
    real, _ = panel_geometry(panel, k)
    if not real.get("anchors"):
        return {"k": k, "real": real, "null": None}
    rng = np.random.default_rng(seed)
    null = nulls.NULLS[null_name]
    samples: list[dict[str, Any]] = []
    for _ in range(draws):
        shuffled = {pair: null(frame, rng) for pair, frame in panel.items()}
        summary, _ = panel_geometry(shuffled, k)
        if summary.get("anchors"):
            samples.append(summary)
    if not samples:
        return {"k": k, "real": real, "null": None}
    keys = [
        "median_retrace_fraction",
        "median_retrace_sigma",
        "median_retrace_sigma_excluding_top_10_days",
        "median_retrace_fraction_excluding_top_10_days",
        "median_retrace_fraction_excluding_top_20_days",
        "mean_retrace_fraction",
        "median_adverse_extension_sigma",
        "reached_50_rate",
        "reached_100_rate",
        "median_bars_to_50",
        "median_continuation_before_50",
    ]
    null_stats: dict[str, Any] = {"draws": len(samples), "contract": nulls.CONTRACTS[null_name]}
    for key in keys:
        values = [s[key] for s in samples if s.get(key) is not None]
        if not values or real.get(key) is None:
            continue
        mean, sd = float(np.mean(values)), float(np.std(values))
        null_stats[key] = {
            "null_mean": round(mean, 5),
            "null_sd": round(sd, 5),
            "real": round(float(real[key]), 5),
            "real_minus_null": round(float(real[key]) - mean, 5),
            "studentized": round((float(real[key]) - mean) / sd, 3) if sd > 0 else None,
        }
    null_stats["null_median_anchors"] = int(np.median([s["anchors"] for s in samples]))

    #: Westfall--Young family-max over this threshold's statistics. The plan
    #: registers 5 statistics at each of 3 thresholds and asks (§9) for a
    #: family-max correction; the first version of this round computed one for
    #: B′-4 only. `per_draw_max_abs_z` is exported so the driver can take the
    #: max across thresholds without re-drawing.
    registered = [key for key in keys if key in null_stats and null_stats[key]["studentized"]]
    if registered:
        matrix = np.array(
            [
                [float(sample[key]) for sample in samples if sample.get(key) is not None]
                for key in registered
            ]
        )
        if matrix.ndim == 2 and matrix.shape[1] == len(samples):
            mean = matrix.mean(axis=1, keepdims=True)
            sd = matrix.std(axis=1, keepdims=True)
            sd[sd == 0] = np.inf
            observed = np.abs(
                (np.array([real[key] for key in registered]).reshape(-1, 1) - mean) / sd
            ).max()
            per_draw = np.abs((matrix - mean) / sd).max(axis=0)
            null_stats["family_max"] = {
                "cells": len(registered),
                "observed_max_abs_z": round(float(observed), 3),
                "family_wise_p": round(
                    float((np.sum(per_draw >= observed) + 1) / (len(per_draw) + 1)), 5
                ),
                "per_draw_max_abs_z": [round(float(v), 4) for v in per_draw],
            }
    return {"k": k, "real": real, "null": null_stats}


__all__ = [
    "htf_range_position",
    "null_sanity",
    "BAR_SECONDS",
    "RETRACE_LEVELS",
    "WINDOW_MULTIPLE",
    "against_null",
    "find_anchors",
    "htf_context",
    "panel_geometry",
    "summarise",
    "trailing_sigma",
]
