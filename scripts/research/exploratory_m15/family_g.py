"""Family G -- cross-pair / relative strength. `NON_DECISION_BEARING_EXPLORATORY_ONLY`.

`RESEARCH_SCRATCH_NON_AUTHORITATIVE`. Nothing here is evidence, a candidate
selection, or a Formal Confirmation input.

Why a separate runner
---------------------

Families A-F decide one pair at a time, so `runner.run_registry` can hand each
strategy one pair's bars. A cross-sectional strategy cannot be expressed that
way: the decision for `EUR_USD` at time *t* depends on where `EUR_USD` sits in
the ranking of **all twenty** pairs at that same *t*. So this module builds a
**panel** -- one shared UTC timestamp grid, twenty aligned mid-close columns --
decides on the panel, and only then splits the answer back into twenty per-pair
position series which `engine.evaluate` prices exactly as it prices every other
family. The cost model, the one-bar shift and the metrics are unchanged.

Causality, stated precisely
---------------------------

Three places where a cross-sectional design can leak, and what is done about
each:

1. **Alignment.** The panel grid is the *union* of the twenty pairs'
   timestamps, and a pair missing a bar carries its **last observed** close
   forward (`ffill`). Forward-filling is backward-looking; the alternative --
   interpolating, or reindexing with a future value -- is not. A pair whose
   price is stale is ranked on stale information, which is what a live system
   would also have.
2. **The ranking instant.** The rank at grid bar *t* uses closes at *t* and
   *t - lookback* only. `engine.evaluate` then shifts the whole position series
   by one bar, so the first return earned is *t+1 -> t+2*.
3. **The dispersion filter.** Its threshold is a quantile of *previous* grid
   points only (expanding, `shift(1)`), never of the whole sample. Taking the
   quantile over the full history is the standard way to invent a selectivity
   edge, and it is the reason `_causal_quantile` exists rather than a
   `Series.quantile` call.

The rollover guard from `strategies.py` is kept: a rebalance grid of 96 bars is
exactly 24 hours, so a grid that lands on the 22:00 UTC bar lands on it *every
single time*. A blocked decision is deferred one bar, not dropped.

Weights
-------

Positions are not restricted to `{-1, 0, +1}` here. `engine.evaluate` prices any
real-valued position correctly -- gross is `position x forward return`, cost is
`|delta position| x per-side cost` -- so a volatility-scaled weight is charged in
proportion to the size it actually puts on. One caveat that belongs in the
report rather than a comment: `_per_trade_pnl` starts a new "trade" whenever the
held value *changes*, so a vol-scaled variant that re-sizes the same position at
a grid point books two trades where an equal-weight variant books one. Trade
counts are therefore comparable within a weighting scheme and not across.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Final

import numpy as np
import pandas as pd

from scripts.research.exploratory_m15 import bars as bars_module
from scripts.research.exploratory_m15 import engine

PAIRS: Final[tuple[str, ...]] = (
    "EUR_USD",
    "GBP_USD",
    "AUD_USD",
    "NZD_USD",
    "USD_CHF",
    "USD_CAD",
    "EUR_GBP",
    "USD_JPY",
    "EUR_JPY",
    "GBP_JPY",
    "AUD_JPY",
    "NZD_JPY",
    "CHF_JPY",
    "EUR_CHF",
    "EUR_AUD",
    "EUR_CAD",
    "AUD_NZD",
    "AUD_CAD",
    "GBP_AUD",
    "GBP_CHF",
)

CURRENCIES: Final[tuple[str, ...]] = (
    "USD",
    "EUR",
    "JPY",
    "GBP",
    "AUD",
    "NZD",
    "CAD",
    "CHF",
)


# ---------------------------------------------------------------------------
# the panel
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Panel:
    """Twenty pairs on one UTC grid. Closes are mid; returns are log."""

    pairs: tuple[str, ...]
    grid: pd.DatetimeIndex
    close: pd.DataFrame  # grid x pairs, ffilled mid close
    log_close: pd.DataFrame  # log of the above
    bars: dict[str, pd.DataFrame]

    def past_return(self, lookback: int) -> pd.DataFrame:
        """Log return over the trailing `lookback` bars, ending at this bar."""
        return self.log_close - self.log_close.shift(lookback)

    def vol(self, lookback: int, window_multiple: int = 20) -> pd.DataFrame:
        """Trailing sigma of the same-horizon return, for scale-free ranking."""
        window = lookback * window_multiple
        step = self.log_close.diff()
        return step.rolling(window, min_periods=window // 2).std() * np.sqrt(lookback)


def build_panel(pairs=PAIRS) -> Panel:
    loaded = {pair: bars_module.load(pair) for pair in pairs}
    grid = pd.DatetimeIndex(sorted(set().union(*(set(f["ts"]) for f in loaded.values()))))
    close = pd.DataFrame(
        {
            pair: pd.Series(frame["mid_c"].to_numpy(), index=pd.DatetimeIndex(frame["ts"]))
            .reindex(grid)
            .ffill()
            for pair, frame in loaded.items()
        },
        index=grid,
    )[list(pairs)]
    return Panel(
        pairs=tuple(pairs),
        grid=grid,
        close=close,
        log_close=np.log(close),
        bars=loaded,
    )


# ---------------------------------------------------------------------------
# currency decomposition
# ---------------------------------------------------------------------------


def legs(pair: str) -> tuple[str, str]:
    base, quote = pair.split("_")
    return base, quote


def currency_strength(panel: Panel, lookback: int, *, normalise: bool = False) -> pd.DataFrame:
    """Per-currency strength: the mean signed move of every pair it appears in.

    `+1` where the currency is the base, `-1` where it is the quote. A currency
    that rose against everything scores high. This is the graph-averaged, and so
    much less noisy, version of a single pair's move -- which is the whole
    hypothesis being tested against the plain pair ranking.
    """
    moves = panel.past_return(lookback)
    if normalise:
        moves = moves / panel.vol(lookback).replace(0.0, np.nan)
    out = {}
    for currency in CURRENCIES:
        columns: list[str] = []
        signs: list[float] = []
        for pair in panel.pairs:
            base, quote = legs(pair)
            if currency == base:
                columns.append(pair)
                signs.append(1.0)
            elif currency == quote:
                columns.append(pair)
                signs.append(-1.0)
        block = moves[columns].to_numpy() * np.asarray(signs)
        out[currency] = pd.Series(np.nanmean(block, axis=1), index=panel.grid)
    frame = pd.DataFrame(out, index=panel.grid)
    #: the eight legs are not a balanced design (USD appears 7 times, CAD 3), so
    #: demeaning is what makes "strength" mean *relative* strength.
    return frame.sub(frame.mean(axis=1), axis=0)


def strength_spread(panel: Panel, lookback: int, *, normalise: bool = False) -> pd.DataFrame:
    """Per-pair `strength(base) - strength(quote)`, on the panel grid."""
    strength = currency_strength(panel, lookback, normalise=normalise)
    out = {}
    for pair in panel.pairs:
        base, quote = legs(pair)
        out[pair] = strength[base] - strength[quote]
    return pd.DataFrame(out, index=panel.grid)[list(panel.pairs)]


# ---------------------------------------------------------------------------
# signal construction
# ---------------------------------------------------------------------------


def _causal_quantile(
    series: pd.Series, q: float, *, min_periods: int = 20, window: int | None = None
) -> pd.Series:
    """Quantile of **strictly prior** observations only.

    Expanding by default. `window` switches to a trailing window, which matters
    for a persistent series: the corpus opens in the high-volatility April 2025
    stretch, so an expanding quantile of realised volatility is set by the first
    weeks and is never exceeded again. That is a property of the threshold, not
    of the strategy, which is why both are reported.
    """
    prior = series.shift(1)
    if window is None:
        return prior.expanding(min_periods=min_periods).quantile(q)
    return prior.rolling(window, min_periods=min(min_periods, window // 2)).quantile(q)


def _grid_mask(panel: Panel, hold: int, phase: int = 0) -> pd.Series:
    mask = np.zeros(len(panel.grid), dtype=bool)
    mask[phase % hold :: hold] = True
    return pd.Series(mask, index=panel.grid)


def cross_sectional_positions(
    panel: Panel,
    *,
    score: pd.DataFrame,
    hold: int,
    k: int = 3,
    phase: int = 0,
    sign: float = -1.0,
    weight: str = "equal",
    vol_lookback: int | None = None,
    dispersion_q: float | None = None,
    gate: pd.Series | None = None,
    gate_label: str = "cross_sectional_std",
    gate_window: int | None = None,
    blend: bool = False,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Rank on `score`, take the extremes, hold to the next grid point.

    `sign = -1` fades the ranking (long the losers, short the winners); `+1` is
    the momentum control that must be worse if the mean-reversion reading is
    real rather than an artefact of the cost accounting.

    `blend=True` runs **every** phase of the rebalance grid at once as `hold`
    overlapping tranches of `1/hold` weight each, which is why `phase` stops
    mattering. It is not an averaging of results after the fact: opposite
    changes in two tranches cancel inside the book before any cost is charged,
    so the blend's turnover is strictly lower than the mean tranche's. The
    identity used is that an equal blend of all `hold` phases holds, at bar *t*,
    the mean of the raw decisions at *t, t-1, ... t-hold+1* -- a rolling mean.
    """
    grid_points = _grid_mask(panel, hold, phase)
    ranks = score.rank(axis=1, ascending=True, na_option="keep")
    valid = score.notna().sum(axis=1)
    top = (valid.to_numpy()[:, None] - ranks.to_numpy()) < k  # k largest scores
    bottom = ranks.to_numpy() <= k  # k smallest scores
    #: sign = -1 (fade): short the k largest past moves, long the k smallest.
    #: sign = +1 is the momentum control, and is the same thing negated.
    raw = np.where(top, sign, 0.0) + np.where(bottom, -sign, 0.0)
    raw = pd.DataFrame(raw, index=panel.grid, columns=list(score.columns))
    raw[score.isna()] = 0.0

    if weight == "vol_scaled":
        if vol_lookback is None:
            raise ValueError("vol_scaled needs a vol_lookback")
        sigma = panel.vol(vol_lookback)
        inv = 1.0 / sigma.replace(0.0, np.nan)
        #: scale so the *mean* active weight is 1 -- the equal-weight variant's
        #: gross exposure, redistributed, not a leveraged version of it
        active = raw.abs() > 0
        scale = inv.where(active)
        norm = scale.mean(axis=1)
        raw = raw * (scale.div(norm, axis=0)).fillna(0.0)
    elif weight != "equal":
        raise ValueError(f"unknown weight {weight!r}")

    traded_points = grid_points.copy()
    dispersion_info: dict[str, Any] = {}
    if dispersion_q is not None:
        #: evaluated at **every** bar, not only at this phase's grid points.
        #: Each blended tranche rebalances at its own instant and applies the
        #: filter there, so the gate has to be defined wherever a tranche might
        #: be deciding. Restricting it to `grid_points` zeroes `raw` on the bars
        #: the other tranches use and silently collapses the blend to nothing --
        #: which is what a first version did, and it showed up as an exposure of
        #: 0.00 rather than as an error.
        dispersion = score.std(axis=1) if gate is None else gate
        threshold = _causal_quantile(dispersion, dispersion_q, min_periods=500, window=gate_window)
        keep = (dispersion > threshold).fillna(False)
        traded_points = grid_points & keep
        dispersion_info = {
            "dispersion_q": dispersion_q,
            "grid_points": int(grid_points.sum()),
            "grid_points_traded": int(traded_points.sum()),
            "bars_above_threshold_share": float(keep[threshold.notna()].mean()),
            "gate": gate_label,
            "gate_window": gate_window,
        }
        #: on a skipped rebalance the book goes flat rather than drifting on a
        #: stale ranking -- otherwise "selectivity" silently becomes "hold longer"
        raw = raw.where(keep, 0.0)

    if blend:
        decided = raw.rolling(hold, min_periods=hold).mean().fillna(0.0)
        dispersion_info["blend_tranches"] = hold
    else:
        decided = raw.where(grid_points).ffill().fillna(0.0)
    return decided, dispersion_info


def _apply_rollover_guard(decided: pd.Series, frame: pd.DataFrame) -> pd.Series:
    """`strategies._hold`, on a series already reindexed to one pair's bars."""
    blocked = (frame["rollover"] | frame["spread_close_pips"].isna()).to_numpy()
    signal = decided.copy()
    changed = signal.ne(signal.shift(1)).to_numpy()
    signal[blocked & changed] = np.nan
    return signal.ffill().fillna(0.0)


def to_pair_positions(panel: Panel, decided: pd.DataFrame) -> dict[str, pd.Series]:
    out = {}
    for pair in panel.pairs:
        frame = panel.bars[pair]
        series = decided[pair].reindex(pd.DatetimeIndex(frame["ts"]))
        series = pd.Series(series.to_numpy(), index=frame.index).fillna(0.0)
        out[pair] = _apply_rollover_guard(series, frame)
    return out


# ---------------------------------------------------------------------------
# strategy constructors -- each returns (positions on grid, info)
# ---------------------------------------------------------------------------


def g_rank_reversal(
    panel: Panel,
    *,
    lookback: int = 96,
    hold: int = 96,
    k: int = 3,
    metric: str = "logret",
    sign: float = -1.0,
    weight: str = "equal",
    phase: int = 0,
    dispersion_q: float | None = None,
    demean: bool = False,
    blend: bool = False,
    gate_kind: str = "cross_sectional_std",
    gate_window: int | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Rank the twenty pairs by their own past move; fade the extremes.

    `gate_kind` decides what `dispersion_q` gates on, and exists so the
    selectivity result can be attacked rather than admired:

    - `cross_sectional_std`  -- the spread of the twenty scores, the hypothesis.
    - `market_abs_move`      -- the mean |move| across pairs. Contains no
      information about the *shape* of the cross-section, only its size, so if
      this gate works as well the word "dispersion" is doing no work and the
      honest description is "trade when the market is moving".
    - `market_realised_vol`  -- mean trailing sigma of per-bar returns, which
      does not look at the ranking horizon at all.
    - `dispersion_over_vol`  -- the spread divided by that volatility, i.e. the
      part of dispersion that is *not* just a volatile market.
    """
    score = panel.past_return(lookback)
    if metric == "vol_norm":
        score = score / panel.vol(lookback).replace(0.0, np.nan)
    elif metric != "logret":
        raise ValueError(metric)
    if demean:
        score = score.sub(score.mean(axis=1), axis=0)
    gate = None
    if dispersion_q is not None and gate_kind != "cross_sectional_std":
        market_vol = panel.vol(lookback).mean(axis=1)
        if gate_kind == "market_abs_move":
            gate = score.abs().mean(axis=1)
        elif gate_kind == "market_realised_vol":
            gate = market_vol
        elif gate_kind == "dispersion_over_vol":
            gate = score.std(axis=1) / market_vol.replace(0.0, np.nan)
        else:
            raise ValueError(gate_kind)
    return cross_sectional_positions(
        panel,
        score=score,
        hold=hold,
        k=k,
        sign=sign,
        weight=weight,
        vol_lookback=lookback,
        phase=phase,
        dispersion_q=dispersion_q,
        gate=gate,
        gate_label=gate_kind,
        gate_window=gate_window,
        blend=blend,
    )


def g_strength_reversal(
    panel: Panel,
    *,
    lookback: int = 96,
    hold: int = 96,
    k: int = 3,
    normalise: bool = False,
    sign: float = -1.0,
    weight: str = "equal",
    phase: int = 0,
    dispersion_q: float | None = None,
    blend: bool = False,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Rank by the *currency-graph* divergence of the two legs; fade it."""
    score = strength_spread(panel, lookback, normalise=normalise)
    return cross_sectional_positions(
        panel,
        score=score,
        hold=hold,
        k=k,
        sign=sign,
        weight=weight,
        vol_lookback=lookback,
        phase=phase,
        dispersion_q=dispersion_q,
        blend=blend,
    )


def g_residual_reversal(
    panel: Panel,
    *,
    lookback: int = 96,
    hold: int = 96,
    k: int = 3,
    sign: float = -1.0,
    weight: str = "equal",
    phase: int = 0,
    dispersion_q: float | None = None,
    blend: bool = False,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Fade only what the currency graph does **not** explain.

    `own move - (strength(base) - strength(quote))` is the part of a pair's move
    that is idiosyncratic to the pair rather than to either of its currencies.
    If the reversion is a currency-level phenomenon this should be worse than
    `g_strength_reversal`; if it is a pair-level one it should be better.
    """
    score = panel.past_return(lookback) - strength_spread(panel, lookback)
    return cross_sectional_positions(
        panel,
        score=score,
        hold=hold,
        k=k,
        sign=sign,
        weight=weight,
        vol_lookback=lookback,
        phase=phase,
        dispersion_q=dispersion_q,
        blend=blend,
    )


def exposure_matrix(pairs: tuple[str, ...]) -> np.ndarray:
    """`E[c, p]` = +1 if currency `c` is `p`'s base, -1 if it is the quote."""
    matrix = np.zeros((len(CURRENCIES), len(pairs)))
    for column, pair in enumerate(pairs):
        base, quote = legs(pair)
        matrix[CURRENCIES.index(base), column] = 1.0
        matrix[CURRENCIES.index(quote), column] = -1.0
    return matrix


def g_currency_neutral_reversal(
    panel: Panel,
    *,
    lookback: int = 96,
    hold: int = 96,
    k: int = 3,
    sign: float = -1.0,
    phase: int = 0,
    blend: bool = False,
    dispersion_q: float | None = None,
    project: bool = True,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """The top/bottom-k basket, projected onto the currency-neutral subspace.

    The literal reading of "isolate *relative* overextension". A top-3 /
    bottom-3 basket picked out of twenty pairs carries whatever net currency
    exposure the ranking happens to hand it -- short three JPY crosses and the
    book is simply long JPY, which is a directional bet on one currency wearing
    a cross-sectional costume. Projecting the weight vector onto the null space
    of the 8x20 currency-exposure matrix removes every such leg exactly, leaving
    only the part of the basket no single-currency position could replicate.

    The projection is a fixed linear map on the weight vector -- it uses no
    prices and no future information -- and it is applied to the raw decision
    before the hold, so the neutral book is what is actually held.
    """
    score = panel.past_return(lookback)
    decided, info = cross_sectional_positions(
        panel,
        score=score,
        hold=hold,
        k=k,
        sign=sign,
        phase=phase,
        dispersion_q=dispersion_q,
        blend=blend,
    )
    if not project:
        info["currency_neutral"] = False
        return decided, info
    matrix = exposure_matrix(panel.pairs)
    #: residual-maker for the row space of E: w - E^+ (E w)
    projector = np.eye(len(panel.pairs)) - np.linalg.pinv(matrix) @ matrix
    values = decided.to_numpy() @ projector.T
    neutral = pd.DataFrame(values, index=panel.grid, columns=list(panel.pairs))
    gross_before = float(np.abs(decided.to_numpy()).sum())
    gross_after = float(np.abs(values).sum())
    info.update(
        {
            "currency_neutral": True,
            "gross_weight_retained": round(gross_after / gross_before, 4)
            if gross_before
            else float("nan"),
            "max_residual_currency_exposure": float(np.abs(matrix @ values.T).max()),
        }
    )
    return neutral, info


def g_timeseries_reversal(
    panel: Panel,
    *,
    lookback: int = 96,
    hold: int = 96,
    sign: float = -1.0,
    phase: int = 0,
    blend: bool = False,
    gate_q: float | None = None,
    gate_kind: str = "own_abs_move",
    gate_window: int | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """The matched **time-series** control: no ranking, only each pair's own sign.

    This is the comparison the family exists to make. It runs on the same panel,
    the same rebalance grid, the same blend, the same cost model and the same
    gate as the cross-sectional variants, and differs in exactly one thing:
    a pair's position depends on its own move alone, never on where that move
    sits among the other nineteen. Any gap between this and
    `g_rank_reversal` is what the cross-section is worth.

    `gate_kind="own_abs_move"` gates each pair on its own move's causal
    quantile; `"market_abs_move"` uses the same single market-wide gate the
    cross-sectional variants use, so the two differ only in the signal.
    """
    move = panel.past_return(lookback)
    #: `sign = -1` is the fade, matching `cross_sectional_positions`, where the
    #: largest score is given `sign`. Writing `-sign` here would silently make
    #: the "time-series control" a momentum strategy whose gross is the exact
    #: negative of the intended one -- which is how a first version read.
    raw = sign * np.sign(move)
    raw = pd.DataFrame(raw, index=panel.grid, columns=list(panel.pairs)).fillna(0.0)
    info: dict[str, Any] = {"gate": gate_kind, "gate_window": gate_window}
    if gate_q is not None:
        if gate_kind == "own_abs_move":
            magnitude = move.abs()
            keep = pd.DataFrame(
                {
                    column: (
                        magnitude[column]
                        > _causal_quantile(
                            magnitude[column],
                            gate_q,
                            min_periods=500,
                            window=gate_window,
                        )
                    )
                    for column in panel.pairs
                },
                index=panel.grid,
            )
        elif gate_kind == "market_abs_move":
            market = move.abs().mean(axis=1)
            threshold = _causal_quantile(market, gate_q, min_periods=500, window=gate_window)
            keep = pd.DataFrame(
                np.repeat((market > threshold).to_numpy()[:, None], len(panel.pairs), axis=1),
                index=panel.grid,
                columns=list(panel.pairs),
            )
        else:
            raise ValueError(gate_kind)
        raw = raw.where(keep.fillna(False), 0.0)
        info["gate_q"] = gate_q
        info["bars_above_threshold_share"] = float(keep.mean(axis=1).mean())
    if blend:
        decided = raw.rolling(hold, min_periods=hold).mean().fillna(0.0)
        info["blend_tranches"] = hold
    else:
        decided = raw.where(_grid_mask(panel, hold, phase)).ffill().fillna(0.0)
    return decided, info


def g_extreme_currency_pair(
    panel: Panel,
    *,
    lookback: int = 96,
    hold: int = 96,
    k: int = 1,
    sign: float = -1.0,
    phase: int = 0,
    blend: bool = False,
    universe: tuple[str, ...] | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Trade only the pairs joining the `k` strongest to the `k` weakest legs.

    A tighter reading of "currency strength": rather than ranking pairs by a
    derived spread, find the currencies at the two ends of the strength ladder
    and fade the pairs that actually connect them.
    """
    strength = currency_strength(panel, lookback)
    order = strength.rank(axis=1, ascending=True)
    n = len(CURRENCIES)
    weak = order <= k
    strong = order > n - k
    raw = pd.DataFrame(0.0, index=panel.grid, columns=list(panel.pairs))
    for pair in panel.pairs:
        base, quote = legs(pair)
        #: base strong + quote weak => the pair is stretched up => fade it short
        up = (strong[base] & weak[quote]).to_numpy()
        down = (weak[base] & strong[quote]).to_numpy()
        raw[pair] = np.where(up, sign, 0.0) + np.where(down, -sign, 0.0)
    if universe is not None:
        raw[[c for c in raw.columns if c not in universe]] = 0.0
    if blend:
        decided = raw.rolling(hold, min_periods=hold).mean().fillna(0.0)
        return decided, {"blend_tranches": hold}
    grid_points = _grid_mask(panel, hold, phase)
    decided = raw.where(grid_points).ffill().fillna(0.0)
    return decided, {}


# ---------------------------------------------------------------------------
# evaluation
# ---------------------------------------------------------------------------


def _session_concentration(results, panel: Panel) -> dict[str, Any]:
    totals = {"asia": 0.0, "europe": 0.0, "us": 0.0}
    for result in results:
        frame = panel.bars[result.pair]
        net = result.net.to_numpy()
        for session in totals:
            totals[session] += float(net[(frame["session"] == session).to_numpy()].sum())
    denominator = sum(abs(v) for v in totals.values()) or 1.0
    top = max(totals, key=lambda s: abs(totals[s]))
    return {
        "session_net_pips": {k: round(v, 1) for k, v in totals.items()},
        "top_session": top,
        "top_session_share_of_abs_pnl": float(abs(totals[top]) / denominator),
    }


def _split_metrics(results, split_index: int) -> dict[str, Any]:
    first = sum(float(r.net.iloc[:split_index].sum()) for r in results)
    second = sum(float(r.net.iloc[split_index:].sum()) for r in results)
    return {"first_half_net_pips": round(first, 1), "second_half_net_pips": round(second, 1)}


def _pooled_profit_factor(results) -> float:
    wins = losses = 0.0
    for result in results:
        per_trade = engine._per_trade_pnl(result.position, result.net)
        wins += float(per_trade[per_trade > 0].sum())
        losses += float(-per_trade[per_trade < 0].sum())
    return float(wins / losses) if losses > 0 else float("inf")


def evaluate_panel(
    panel: Panel,
    decided: pd.DataFrame,
    *,
    name: str,
    cost_multipliers=engine.COST_MULTIPLIERS,
    info: dict[str, Any] | None = None,
) -> dict[str, Any]:
    positions = to_pair_positions(panel, decided)
    base_results = None
    summary: dict[str, Any] = {"strategy": name, **(info or {})}
    for multiplier in cost_multipliers:
        results = [
            engine.evaluate(
                panel.bars[pair],
                positions[pair],
                name=name,
                pair=pair,
                cost_multiplier=multiplier,
            )
            for pair in panel.pairs
        ]
        by_pair = {r.pair: r.metrics["net_pips"] for r in results}
        portfolio = (
            pd.concat([r.net.rename(r.pair) for r in results], axis=1).fillna(0.0).sum(axis=1)
        )
        equity = portfolio.cumsum()
        drawdown = equity - equity.cummax()
        std = float(portfolio.std())
        block = {
            "portfolio_net_pips": float(portfolio.sum()),
            "net_pips_per_pair": float(portfolio.sum() / len(panel.pairs)),
            "gross_pips": float(sum(r.metrics["gross_pips"] for r in results)),
            "cost_pips": float(sum(r.metrics["cost_pips"] for r in results)),
            "sharpe_like": float(portfolio.mean() / std * np.sqrt(engine.BARS_PER_YEAR))
            if std > 0
            else 0.0,
            "max_drawdown_pips": float(drawdown.min()),
        }
        if multiplier == 1.0:
            base_results = results
            per_trade_total = sum(r.metrics["n_closed_trades"] for r in results)
            exposure = float(np.mean([r.metrics["exposure"] for r in results]))
            #: a blended book re-sizes every bar, so `n_closed_trades` (which
            #: starts a new trade on any change of held value) stops meaning
            #: "round trips". Total |delta position| / 2 does mean that, for a
            #: discrete book and a continuous one alike, so both are reported.
            round_trips = float(
                sum(float(r.position.diff().abs().fillna(r.position.abs()).sum()) for r in results)
                / 2.0
            )
            worst = max(by_pair, key=lambda p: abs(by_pair[p]))
            summary.update(block)
            summary.update(
                {
                    "pairs_positive": int(sum(1 for v in by_pair.values() if v > 0)),
                    "pairs": len(by_pair),
                    "total_closed_trades": int(per_trade_total),
                    "effective_round_trips": round(round_trips, 1),
                    "pips_per_round_trip": float(portfolio.sum() / round_trips)
                    if round_trips > 0
                    else float("nan"),
                    "win_rate": float(np.nanmean([r.metrics["win_rate"] for r in results])),
                    "profit_factor": _pooled_profit_factor(results),
                    "avg_trade_pips": float(portfolio.sum() / per_trade_total)
                    if per_trade_total
                    else float("nan"),
                    "turnover_per_year": float(
                        np.mean([r.metrics["turnover_per_year"] for r in results])
                    ),
                    "mean_exposure": exposure,
                    "net_per_unit_exposure": float(portfolio.sum() / exposure / len(panel.pairs))
                    if exposure > 0
                    else float("nan"),
                    "top_pair": worst,
                    "top_pair_share_of_abs_pnl": float(
                        abs(by_pair[worst]) / (sum(abs(v) for v in by_pair.values()) or 1.0)
                    ),
                    "net_ex_top_pair": float(sum(by_pair.values()) - by_pair[worst]),
                    "net_by_pair": {k: round(v, 1) for k, v in sorted(by_pair.items())},
                    "equity_curve_stability": engine.stability(portfolio, None),
                    **_session_concentration(results, panel),
                    **_split_metrics(results, len(panel.bars[panel.pairs[0]]) // 2),
                }
            )
        else:
            summary[f"net_at_cost_x{multiplier}"] = block["portfolio_net_pips"]
            summary[f"sharpe_at_cost_x{multiplier}"] = block["sharpe_like"]
    summary["_results"] = base_results
    return summary


def run_registry(
    panel: Panel,
    registry: dict[str, tuple[Callable, dict]],
    *,
    keep_results: bool = False,
) -> list[dict[str, Any]]:
    rows = []
    for name, (function, kwargs) in registry.items():
        decided, info = function(panel, **kwargs)
        row = evaluate_panel(panel, decided, name=name, info={**info, "params": dict(kwargs)})
        if not keep_results:
            row.pop("_results", None)
        rows.append(row)
    return rows


HEADLINE: Final[tuple[str, ...]] = (
    "strategy",
    "portfolio_net_pips",
    "net_pips_per_pair",
    "sharpe_like",
    "max_drawdown_pips",
    "total_closed_trades",
    "win_rate",
    "profit_factor",
    "avg_trade_pips",
    "effective_round_trips",
    "pips_per_round_trip",
    "turnover_per_year",
    "mean_exposure",
    "net_per_unit_exposure",
    "pairs_positive",
    "top_pair_share_of_abs_pnl",
    "top_session_share_of_abs_pnl",
    "net_at_cost_x1.25",
    "net_at_cost_x1.5",
    "gross_pips",
    "cost_pips",
    "first_half_net_pips",
    "second_half_net_pips",
)


def table(rows: list[dict[str, Any]]) -> pd.DataFrame:
    frame = pd.DataFrame(rows)
    frame["periods_positive"] = [r["equity_curve_stability"]["periods_positive"] for r in rows]
    columns = [c for c in HEADLINE if c in frame.columns] + ["periods_positive"]
    return frame[columns].sort_values("portfolio_net_pips", ascending=False)


__all__ = [
    "CURRENCIES",
    "PAIRS",
    "Panel",
    "build_panel",
    "cross_sectional_positions",
    "currency_strength",
    "evaluate_panel",
    "g_extreme_currency_pair",
    "exposure_matrix",
    "g_currency_neutral_reversal",
    "g_rank_reversal",
    "g_residual_reversal",
    "g_strength_reversal",
    "g_timeseries_reversal",
    "run_registry",
    "strength_spread",
    "table",
    "to_pair_positions",
]
