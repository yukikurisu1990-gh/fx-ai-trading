"""Families D and E: volatility/regime conditioning and session effects.

**`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.**

Nothing here is evidence, a candidate selection or a Formal Confirmation input.
No result in this module may be cited for a GO, a Gate-3a pass, holdout or
novelty evidence, or production readiness.

What this module adds to the Round 1 package
--------------------------------------------

`strategies.reversal_hold` decides on an **index** grid (`grid[::hold]`). Over
this corpus a week holds almost exactly 480 M15 bars, so a 96-bar index grid
lands on **one hour of the day** -- 00:00-01:00 UTC for the pairs with 16796
bars, 17:00-18:00 UTC for the pairs with 16728. The hour is decided by nothing
but how many bars a pair happens to be missing. That makes the existing headline
result a session-conditioned strategy with an *arbitrary, per-pair* session, and
it is why this module replaces the index grid with an explicit **UTC decision
hour** the experiments can sweep.

Everything is causal. Rolling windows close at the decision bar; the position
series is the decision taken *at* that bar's close, and `engine.evaluate` shifts
it once before it earns. Rollover bars may never open a position.

Pooling is on the **timestamp**, not the row number. Pairs differ in bar count
(16710 ... 16796), so the package runner's positional `concat` silently aligns
different clock times across pairs; this module aligns on `ts`.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Final

import numpy as np
import pandas as pd

from scripts.research.exploratory_m15 import bars as bars_module
from scripts.research.exploratory_m15 import engine

PAIRS_20: Final[tuple[str, ...]] = (
    "AUD_CAD",
    "AUD_JPY",
    "AUD_NZD",
    "AUD_USD",
    "CHF_JPY",
    "EUR_AUD",
    "EUR_CAD",
    "EUR_CHF",
    "EUR_GBP",
    "EUR_JPY",
    "EUR_USD",
    "GBP_AUD",
    "GBP_CHF",
    "GBP_JPY",
    "GBP_USD",
    "NZD_JPY",
    "NZD_USD",
    "USD_CAD",
    "USD_CHF",
    "USD_JPY",
)

#: Chronological split. Tuning happens on TUNE only; CHECK is looked at after a
#: choice is made and is reported separately, never averaged back in.
TUNE_END_UTC: Final[str] = "2025-08-26"
CHECK_START_UTC: Final[str] = "2025-08-27"

SESSIONS: Final[tuple[str, ...]] = ("asia", "europe", "us")
REGIMES: Final[tuple[str, ...]] = ("low", "mid", "high")

#: The `:00` bar of hour 22 is a `rollover` bar and can never open a position.
#: Hour 21 carries the day's widest quotes without being flagged, so it is
#: reported rather than silently dropped.
ROLLOVER_HOURS: Final[tuple[int, ...]] = (22,)


# ---------------------------------------------------------------------------
# per-pair feature cache
# ---------------------------------------------------------------------------


class Corpus:
    """Loaded bars plus memoised causal features, so a sweep is not O(n) recomputes."""

    def __init__(self, pairs: Sequence[str] = PAIRS_20) -> None:
        self.pairs = tuple(pairs)
        self.bars: dict[str, pd.DataFrame] = {p: bars_module.load(p) for p in self.pairs}
        self._cache: dict[tuple, pd.Series] = {}

    # -- primitives ---------------------------------------------------------

    def move(self, pair: str, lookback: int) -> pd.Series:
        """Past `lookback`-bar mid move, in pips. Known at the decision bar."""
        key = ("move", pair, lookback)
        if key not in self._cache:
            b = self.bars[pair]
            self._cache[key] = (b["mid_c"] - b["mid_c"].shift(lookback)) / b["pip_size"]
        return self._cache[key]

    def zmove(self, pair: str, lookback: int, window: int) -> pd.Series:
        key = ("z", pair, lookback, window)
        if key not in self._cache:
            self._cache[key] = engine.zscore(self.move(pair, lookback), window)
        return self._cache[key]

    def atr(self, pair: str, period: int = 14) -> pd.Series:
        key = ("atr", pair, period)
        if key not in self._cache:
            self._cache[key] = engine.atr_pips(self.bars[pair], period)
        return self._cache[key]

    def adx(self, pair: str, period: int = 14) -> pd.Series:
        key = ("adx", pair, period)
        if key not in self._cache:
            self._cache[key] = engine.adx(self.bars[pair], period)
        return self._cache[key]

    # -- regime labels ------------------------------------------------------

    def _terciles(self, series: pd.Series, window: int, name: str) -> pd.Series:
        """`low`/`mid`/`high` against the series' own trailing distribution.

        The window closes at the current bar, which is legitimate: the value and
        its trailing quantiles are both known at the close that decides.
        Warm-up bars are labelled `na` and are never tradeable.
        """
        lo = series.rolling(window, min_periods=window // 2).quantile(0.33)
        hi = series.rolling(window, min_periods=window // 2).quantile(0.67)
        out = pd.Series("mid", index=series.index, dtype=object)
        out[series < lo] = "low"
        out[series > hi] = "high"
        out[lo.isna() | series.isna()] = "na"
        out.name = name
        return out

    def atr_regime(self, pair: str, window: int = 480, period: int = 14) -> pd.Series:
        key = ("atr_reg", pair, window, period)
        if key not in self._cache:
            self._cache[key] = self._terciles(self.atr(pair, period), window, "atr_regime")
        return self._cache[key]

    def adx_regime(self, pair: str, window: int = 480, period: int = 14) -> pd.Series:
        key = ("adx_reg", pair, window, period)
        if key not in self._cache:
            self._cache[key] = self._terciles(self.adx(pair, period), window, "adx_regime")
        return self._cache[key]

    def spread_pct(self, pair: str, window: int = 480) -> pd.Series:
        """Where the quoted spread sits in its own trailing distribution, in [0, 1]."""
        key = ("spct", pair, window)
        if key not in self._cache:
            s = self.bars[pair]["spread_close_pips"]
            self._cache[key] = s.rolling(window, min_periods=window // 2).rank(pct=True)
        return self._cache[key]


# ---------------------------------------------------------------------------
# the variant specification
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Variant:
    """One conditioned reversal strategy.

    Decisions happen on a **clock** grid: the `:00` bar of `anchor_hour`, every
    `every_days`-th such bar. Between decisions the position is held. A gate that
    blocks a decision either holds the previous position (`on_block="hold"`, the
    lower-turnover reading) or forces flat (`"flat"`).
    """

    name: str
    lookback: int = 96
    z_window: int = 480
    entry_z: float = 1.5
    anchor_hour: int = 20
    every_days: int = 1
    #: which of the `every_days` decision slots is used. Like `anchor_hour` this
    #: is a nuisance parameter, not a tuning knob.
    phase: int = 0
    sessions: tuple[str, ...] | None = None
    atr_regimes: tuple[str, ...] | None = None
    adx_regimes: tuple[str, ...] | None = None
    spread_pct_max: float | None = None
    spread_window: int = 480
    min_move_atr: float | None = None
    regime_window: int = 480
    on_block: str = "hold"
    #: `+1` fades the move (mean reversion), `-1` follows it (momentum)
    direction: int = 1

    def describe(self) -> dict[str, Any]:
        return dict(self.__dict__)


def decision_mask(
    bars: pd.DataFrame, anchor_hour: int, every_days: int = 1, phase: int = 0
) -> pd.Series:
    """True on the `:00` bar of `anchor_hour`, every `every_days`-th occurrence."""
    ts = bars["ts"]
    at = (ts.dt.hour == anchor_hour) & (ts.dt.minute == 0)
    if every_days > 1:
        order = at.cumsum() - 1
        at = at & (order % every_days == phase % every_days)
    return at


def build_position(corpus: Corpus, pair: str, v: Variant) -> pd.Series:
    """The `{-1, 0, +1}` decision series for one pair. Causal by construction."""
    b = corpus.bars[pair]
    z = corpus.zmove(pair, v.lookback, v.z_window)

    target = pd.Series(0.0, index=b.index)
    target[z > v.entry_z] = -1.0 * v.direction
    target[z < -v.entry_z] = 1.0 * v.direction

    decide = decision_mask(b, v.anchor_hour, v.every_days, v.phase)
    #: a position may never be opened on a rollover bar, whatever the gate says
    allowed = (~b["rollover"]) & b["spread_close_pips"].notna() & z.notna()

    if v.sessions is not None:
        allowed &= b["session"].isin(list(v.sessions))
    if v.atr_regimes is not None:
        allowed &= corpus.atr_regime(pair, v.regime_window).isin(list(v.atr_regimes))
    if v.adx_regimes is not None:
        allowed &= corpus.adx_regime(pair, v.regime_window).isin(list(v.adx_regimes))
    if v.spread_pct_max is not None:
        allowed &= corpus.spread_pct(pair, v.spread_window) <= v.spread_pct_max
    if v.min_move_atr is not None:
        allowed &= corpus.move(pair, v.lookback).abs() >= v.min_move_atr * corpus.atr(pair)

    if v.on_block == "flat":
        acted = decide
        chosen = target.where(allowed, 0.0)
    elif v.on_block == "hold":
        acted = decide & allowed
        chosen = target
    else:
        raise ValueError("on_block must be 'hold' or 'flat', not " + repr(v.on_block))

    return chosen.where(acted).ffill().fillna(0.0)


# ---------------------------------------------------------------------------
# evaluation
# ---------------------------------------------------------------------------


def _mask_metrics(net: pd.Series, label: str) -> dict[str, Any]:
    equity = net.cumsum()
    drawdown = equity - equity.cummax()
    std = float(net.std())
    return {
        label + "_net_pips": float(net.sum()),
        label + "_sharpe_like": float(net.mean() / std * np.sqrt(engine.BARS_PER_YEAR))
        if std > 0
        else 0.0,
        label + "_max_drawdown_pips": float(drawdown.min()),
    }


def _entry_rows(bars: pd.DataFrame, position: pd.Series, net: pd.Series) -> pd.DataFrame:
    """One row per closed trade: entry clock context and the trade's net pips.

    The engine holds `position.shift(1)`, so the first bar that earns is the one
    after the decision. Entry context is taken from the decision bar, which is
    what a live system would have conditioned on.
    """
    held = position.shift(1).fillna(0.0).to_numpy()
    values = net.to_numpy()
    stamps = bars["ts"].to_numpy()
    hour = bars["ts"].dt.hour.to_numpy()
    session = bars["session"].to_numpy()
    rows: list[dict[str, Any]] = []
    active = 0.0
    running = 0.0
    start = 0

    def close(end: int) -> None:
        origin = max(start - 1, 0)
        rows.append(
            {
                "ts": stamps[start],
                "hour": int(hour[origin]),
                "session": str(session[origin]),
                "side": active,
                "net_pips": running,
                "bars_held": end - start,
            }
        )

    for i, (p, val) in enumerate(zip(held, values, strict=True)):
        if p != active:
            if active != 0.0:
                close(i)
            active, running, start = p, 0.0, i
        if active != 0.0:
            running += val
    if active != 0.0:
        close(len(held))
    return pd.DataFrame(rows)


def evaluate_variant(
    corpus: Corpus,
    v: Variant,
    *,
    pairs: Sequence[str] | None = None,
    cost_multipliers: Sequence[float] = engine.COST_MULTIPLIERS,
    with_trades: bool = True,
) -> dict[str, Any]:
    """Every metric the round is required to report, for one variant."""
    pairs = tuple(pairs or corpus.pairs)
    positions = {p: build_position(corpus, p, v) for p in pairs}

    per_pair: dict[str, dict[str, Any]] = {}
    nets: dict[str, pd.Series] = {}
    trades = []
    for p in pairs:
        b = corpus.bars[p]
        r = engine.evaluate(b, positions[p], name=v.name, pair=p, cost_multiplier=1.0)
        per_pair[p] = dict(r.metrics)
        nets[p] = r.net.set_axis(b["ts"])
        if with_trades:
            frame = _entry_rows(b, positions[p], r.net)
            if not frame.empty:
                frame["pair"] = p
                trades.append(frame)

    pooled = pd.concat([s.rename(p) for p, s in nets.items()], axis=1).fillna(0.0)
    pooled_net = pooled.mean(axis=1)

    by_pair = {p: per_pair[p]["net_pips"] for p in pairs}
    total_abs = sum(abs(x) for x in by_pair.values()) or 1.0
    best = max(by_pair, key=by_pair.get)

    out: dict[str, Any] = {
        "classification": "NON_DECISION_BEARING_EXPLORATORY_ONLY",
        "variant": v.name,
        "spec": v.describe(),
        "pairs": len(pairs),
        "pooled_net_pips_per_pair": float(pooled_net.sum()),
        "pooled_sharpe_like": float(
            pooled_net.mean() / pooled_net.std() * np.sqrt(engine.BARS_PER_YEAR)
        )
        if pooled_net.std() > 0
        else 0.0,
        "pooled_max_drawdown_pips": float(
            (pooled_net.cumsum() - pooled_net.cumsum().cummax()).min()
        ),
        "pairs_positive": int(sum(1 for x in by_pair.values() if x > 0)),
        "gross_pips_per_pair": float(np.mean([per_pair[p]["gross_pips"] for p in pairs])),
        "cost_pips_per_pair": float(np.mean([per_pair[p]["cost_pips"] for p in pairs])),
        "total_closed_trades": int(sum(per_pair[p]["n_closed_trades"] for p in pairs)),
        "mean_turnover_per_year": float(np.mean([per_pair[p]["turnover_per_year"] for p in pairs])),
        "mean_exposure": float(np.mean([per_pair[p]["exposure"] for p in pairs])),
        "top_pair": best,
        "top_pair_share_of_abs_pnl": float(abs(by_pair[best]) / total_abs),
        "net_by_pair": {k: round(x, 1) for k, x in sorted(by_pair.items())},
    }

    for m in cost_multipliers:
        if m == 1.0:
            continue
        series = []
        for p in pairs:
            b = corpus.bars[p]
            r = engine.evaluate(b, positions[p], name=v.name, pair=p, cost_multiplier=m)
            series.append(r.net.set_axis(b["ts"]).rename(p))
        joint = pd.concat(series, axis=1).fillna(0.0).mean(axis=1)
        out["net_at_cost_x" + str(m)] = float(joint.sum())
        out["pairs_positive_at_cost_x" + str(m)] = int(sum(1 for s in series if float(s.sum()) > 0))

    if with_trades and trades:
        tr = pd.concat(trades, ignore_index=True)
        wins = tr.loc[tr["net_pips"] > 0, "net_pips"].sum()
        losses = -tr.loc[tr["net_pips"] < 0, "net_pips"].sum()
        out.update(
            {
                "n_closed_trades_pooled": int(len(tr)),
                "win_rate": float((tr["net_pips"] > 0).mean()),
                "profit_factor": float(wins / losses) if losses > 0 else float("inf"),
                "avg_trade_pips": float(tr["net_pips"].mean()),
                "median_bars_held": float(tr["bars_held"].median()),
                "entry_session_counts": {
                    str(k): int(x) for k, x in tr["session"].value_counts().items()
                },
                "entry_session_net_pips": {
                    str(k): round(float(x), 1)
                    for k, x in tr.groupby("session")["net_pips"].sum().items()
                },
                "entry_session_avg_pips": {
                    str(k): round(float(x), 3)
                    for k, x in tr.groupby("session")["net_pips"].mean().items()
                },
                "entry_hour_counts": {int(k): int(x) for k, x in tr["hour"].value_counts().items()},
            }
        )
    else:
        out["n_closed_trades_pooled"] = 0

    quarters = np.array_split(np.arange(len(pooled_net)), 4)
    out["quarter_net_pips"] = [round(float(pooled_net.iloc[q].sum()), 1) for q in quarters]
    out["quarters_positive"] = int(sum(1 for q in quarters if pooled_net.iloc[q].sum() > 0))
    tune = pooled_net.index < pd.Timestamp(CHECK_START_UTC, tz="UTC")
    out.update(_mask_metrics(pooled_net[tune], "tune"))
    out.update(_mask_metrics(pooled_net[~tune], "check"))

    if len(pairs) > 1:
        rest = pooled[[p for p in pairs if p != best]].mean(axis=1)
        out["net_drop_best_pair"] = float(rest.sum())
        out["sharpe_drop_best_pair"] = (
            float(rest.mean() / rest.std() * np.sqrt(engine.BARS_PER_YEAR))
            if rest.std() > 0
            else 0.0
        )
    return out


def sweep_hours(
    corpus: Corpus,
    base: Variant,
    *,
    hours: Sequence[int] | None = None,
    pairs: Sequence[str] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Evaluate `base` at every usable anchor hour and summarise the distribution.

    The decision hour is a **nuisance parameter**. The package's index grid fixes
    it by accident and differently per pair, and choosing the best hour on the
    same data that measures it is the cheapest way in this whole round to
    manufacture an edge from nothing. So a configuration is reported as its
    distribution over hours — mean, spread, worst — and never as its best hour.
    """
    usable = [h for h in (hours if hours is not None else range(24)) if h not in ROLLOVER_HOURS]
    rows = []
    for h in usable:
        for ph in range(base.every_days):
            v = replace(base, name=f"{base.name}_h{h:02d}_p{ph}", anchor_hour=h, phase=ph)
            rows.append(evaluate_variant(corpus, v, pairs=pairs, **kwargs))
    frame = pd.DataFrame([compact(r) for r in rows])
    net = frame["pooled_net_pips_per_pair"]
    summary = {
        "variant": base.name,
        "spec": base.describe(),
        "hours": usable,
        "net_mean": float(net.mean()),
        "net_median": float(net.median()),
        "net_sd": float(net.std()),
        "net_min": float(net.min()),
        "net_max": float(net.max()),
        "cells_positive": int((net > 0).sum()),
        "hours_tested": len(usable),
        "cells_tested": len(frame),
        "phases_tested": base.every_days,
        "tune_net_mean": float(frame["tune_net_pips"].mean()),
        "check_net_mean": float(frame["check_net_pips"].mean()),
        "check_cells_positive": int((frame["check_net_pips"] > 0).sum()),
        "sharpe_mean": float(frame["pooled_sharpe_like"].mean()),
        "pairs_positive_mean": float(frame["pairs_positive"].mean()),
        "trades_mean": float(frame["n_closed_trades_pooled"].mean()),
        "avg_trade_pips_mean": float(frame["avg_trade_pips"].mean()),
        "turnover_mean": float(frame["mean_turnover_per_year"].mean()),
        "gross_per_pair_mean": float(frame["gross_pips_per_pair"].mean()),
        "cost_per_pair_mean": float(frame["cost_pips_per_pair"].mean()),
        "net_at_cost_x1.5_mean": float(frame["net_at_cost_x1.5"].mean())
        if "net_at_cost_x1.5" in frame
        else float("nan"),
        "drop_best_pair_mean": float(frame["net_drop_best_pair"].mean()),
        "quarters_positive_mean": float(frame["quarters_positive"].mean()),
    }
    return {"summary": summary, "per_hour": frame.to_dict(orient="records"), "rows": rows}


COMPACT_KEYS: Final[tuple[str, ...]] = (
    "variant",
    "pooled_net_pips_per_pair",
    "pooled_sharpe_like",
    "pairs_positive",
    "n_closed_trades_pooled",
    "avg_trade_pips",
    "win_rate",
    "profit_factor",
    "mean_turnover_per_year",
    "gross_pips_per_pair",
    "cost_pips_per_pair",
    "net_at_cost_x1.25",
    "net_at_cost_x1.5",
    "quarters_positive",
    "tune_net_pips",
    "check_net_pips",
    "net_drop_best_pair",
    "top_pair_share_of_abs_pnl",
    "pooled_max_drawdown_pips",
)


def compact(row: dict[str, Any]) -> dict[str, Any]:
    """The one-line view used in the sweep tables."""
    return {k: row.get(k) for k in COMPACT_KEYS}


def write(name: str, payload: dict[str, Any]) -> Path:
    """Write a result table under the exploratory scratch root."""
    bars_module.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    target = bars_module.CACHE_DIR / (name + ".json")
    target.write_text(
        json.dumps(
            {
                "classification": "NON_DECISION_BEARING_EXPLORATORY_ONLY",
                "classification_secondary": "RESEARCH_SCRATCH_NON_AUTHORITATIVE",
                "cost_assumption": engine.COST_LABEL,
                "development_span_utc": "2025-04-25..2025-12-28",
                "tune_check_boundary_utc": CHECK_START_UTC,
                **payload,
            },
            indent=2,
            sort_keys=True,
            default=str,
        ),
        encoding="utf-8",
    )
    return target


__all__ = [
    "CHECK_START_UTC",
    "COMPACT_KEYS",
    "Corpus",
    "PAIRS_20",
    "REGIMES",
    "ROLLOVER_HOURS",
    "SESSIONS",
    "TUNE_END_UTC",
    "Variant",
    "build_position",
    "compact",
    "decision_mask",
    "evaluate_variant",
    "replace",
    "sweep_hours",
    "write",
]
