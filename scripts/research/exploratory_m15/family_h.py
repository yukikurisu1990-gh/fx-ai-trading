"""Family H — ML over the seen M15 development corpus.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` / `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

Nothing here is evidence, a candidate selection, or a Formal Confirmation input.
No result produced by this file may be cited for a GO, a Gate-3a pass, holdout
evidence, novelty evidence or production readiness.

The question
------------

The simple-rule families all lost to cost. The best of them,
``C2_rev_96h96_z1.5`` -- fade the last 24h move, decide on a 96-bar grid, hold 96
bars, only when the move is beyond 1.5 sigma -- reached **-53 net pips per pair**
over the whole span on +61 gross against 114 cost. Turnover is the binding
constraint, not the sign of the edge.

So the ML question is not "is there a signal". The IC scan already says there is
a small mean-reverting one at ~24h, negative in 20 of 20 pairs. It is **"can a
model select better entries at the same or lower turnover than the rule"**.

How leakage is kept out
-----------------------

Four separate mechanisms, because this is the one failure mode that would make
every number in this file worthless:

1. **Every feature is a backward window at bar t.** No ``shift(-k)``, no centred
   window, no full-sample statistic. The cross-sectional features rank pairs at
   the *same* timestamp using each pair's *past* return only.
2. **The label is the return the trade would actually earn.** ``engine.evaluate``
   holds ``position.shift(1)``, so a decision at bar *t* earns
   ``mid_c[t+H+1] - mid_c[t+1]``. That is exactly the target -- not
   ``mid_c[t+H] - mid_c[t]``, which is off by one bar and would quietly let the
   model see the bar it trades into.
3. **Purge by construction, not by calendar.** A train row *t* is dropped unless
   its whole label window ``t+H+1`` closes strictly before the first test bar,
   computed on **bar indices** per pair, so a weekend gap cannot make the
   calendar gap look wide enough while the bar gap is not.
4. **Every fitted quantity comes from train only.** The decision threshold is a
   quantile of the *training* prediction distribution. Taking it from the test
   fold would be a within-fold look-ahead that leaves no trace in the metrics.

The negative controls -- shuffled labels, dropped best pair, halved training
window -- are in the experiment driver and are reported whether or not they
flatter the result.
"""

from __future__ import annotations

import warnings
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Final

import numpy as np
import pandas as pd

from scripts.research.exploratory_m15 import bars as bars_module
from scripts.research.exploratory_m15 import engine

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=RuntimeWarning)

CLASSIFICATION: Final[str] = "NON_DECISION_BEARING_EXPLORATORY_ONLY"
CLASSIFICATION_SECONDARY: Final[str] = "RESEARCH_SCRATCH_NON_AUTHORITATIVE"

#: The label horizon, in M15 bars. 96 = 24h. Chosen from the IC scan: the
#: strongest cell is past-96 against forward-96 (mean IC -7.9%, negative in
#: 20/20 pairs), and 96 bars is also where the ~38 pip mean absolute move stops
#: being dominated by the ~3.7 pip round trip.
HORIZON: Final[int] = 96

#: The first bar of the walk-forward out-of-sample region. Everything before it
#: is only ever training data.
OOS_START: Final[str] = "2025-08-01"
#: Test fold boundaries (each fold's first bar). The last entry is the exclusive
#: upper bound and is the first date the loader refuses.
FOLD_EDGES: Final[tuple[str, ...]] = (
    "2025-08-01",
    "2025-09-01",
    "2025-10-01",
    "2025-11-01",
    "2025-12-01",
    "2025-12-29",
)

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

RETURN_HORIZONS: Final[tuple[int, ...]] = (4, 12, 24, 48, 96, 192, 384)
Z_WINDOW: Final[int] = 480

QUANTILE_LEVELS: Final[tuple[float, ...]] = (
    0.02,
    0.05,
    0.10,
    0.15,
    0.20,
    0.30,
    0.40,
    0.50,
    0.60,
    0.70,
    0.80,
    0.85,
    0.90,
    0.95,
    0.98,
)


def _q(level: float) -> str:
    return f"q{int(round(level * 100)):02d}"


# ---------------------------------------------------------------------------
# features -- every one of these is a backward window at bar t
# ---------------------------------------------------------------------------


def pair_features(bars: pd.DataFrame) -> pd.DataFrame:
    """Causal features for one pair. Nothing reads a bar later than ``t``."""
    close = bars["mid_c"]
    pip = bars["pip_size"]
    out: dict[str, pd.Series] = {}

    atr14 = engine.atr_pips(bars, 14)
    atr96 = engine.atr_pips(bars, 96)
    safe_atr = atr14.replace(0.0, np.nan)
    out["atr14"] = atr14
    out["atr_ratio"] = atr14 / atr96.replace(0.0, np.nan)
    out["atr_z"] = engine.zscore(atr14, Z_WINDOW)

    for h in RETURN_HORIZONS:
        move = (close - close.shift(h)) / pip
        out[f"ret_{h}"] = move
        out[f"retn_{h}"] = move / (safe_atr * np.sqrt(h))
    for h in (24, 96, 192):
        out[f"zret_{h}"] = engine.zscore((close - close.shift(h)) / pip, Z_WINDOW)

    out["rsi_14"] = engine.rsi(close, 14)
    out["rsi_48"] = engine.rsi(close, 48)
    out["adx_14"] = engine.adx(bars, 14)

    step = close.diff() / pip
    rv96 = step.rolling(96, min_periods=48).std()
    rv384 = step.rolling(384, min_periods=192).std()
    out["rv_96"] = rv96
    out["rv_ratio"] = rv96 / rv384.replace(0.0, np.nan)

    out["spread"] = bars["spread_close_pips"]
    out["spread_z"] = engine.zscore(bars["spread_close_pips"], Z_WINDOW)

    for window in (48, 192):
        high, low = engine.donchian(bars, window)
        span = (high - low).replace(0.0, np.nan)
        out[f"rangepos_{window}"] = (close - low) / span
        out[f"rangewidth_{window}"] = (high - low) / pip / safe_atr

    #: higher-timeframe context: a 4h and a 24h candle that has already closed
    for period, tag in ((16, "h4"), (96, "d1")):
        htf = engine.higher_timeframe(bars, period)
        out[f"htf_{tag}_dist"] = (close - htf["htf_close"]) / pip / safe_atr
        out[f"htf_{tag}_range"] = (htf["htf_high"] - htf["htf_low"]) / pip / safe_atr

    hour = bars["ts"].dt.hour + bars["ts"].dt.minute / 60.0
    out["hour_sin"] = np.sin(2 * np.pi * hour / 24.0)
    out["hour_cos"] = np.cos(2 * np.pi * hour / 24.0)
    out["dow"] = bars["ts"].dt.dayofweek.astype(float)
    for name in ("asia", "europe", "us"):
        out[f"sess_{name}"] = (bars["session"] == name).astype(float)
    out["is_rollover"] = bars["rollover"].astype(float)
    out["complete_96"] = bars["complete_bucket"].astype(float).rolling(96, min_periods=48).mean()

    frame = pd.DataFrame(out, index=bars.index)
    frame.insert(0, "ts", bars["ts"].to_numpy())
    frame.insert(1, "bar", np.arange(len(bars), dtype=np.int64))
    return frame


def add_labels(frame: pd.DataFrame, bars: pd.DataFrame, horizon: int = HORIZON) -> pd.DataFrame:
    """The pips a decision at bar t would earn, and the cost it would pay.

    ``engine.evaluate`` holds ``position.shift(1)``, so a decision at *t* is on
    risk from *t+1* to *t+H+1*. The label is that exact window. Being off by one
    bar here is the same defect as same-bar leakage, only harder to see.
    """
    close = bars["mid_c"]
    pip = bars["pip_size"]
    frame = frame.copy()
    frame["y_pips"] = ((close.shift(-(horizon + 1)) - close.shift(-1)) / pip).to_numpy()
    #: a round trip pays one full spread plus one pad, charged at the traded bar
    frame["roundtrip_cost"] = (bars["spread_close_pips"] + engine.SLIPPAGE_PAD_PIPS).to_numpy()
    frame["y_beats_cost"] = (frame["y_pips"].abs() - frame["roundtrip_cost"] > 0).astype(float)
    frame["y_up"] = (frame["y_pips"] > 0).astype(float)
    return frame


def build_panel(pairs: Sequence[str] = PAIRS, horizon: int = HORIZON) -> pd.DataFrame:
    """Every pair's features and labels stacked, plus cross-sectional columns."""
    blocks: list[pd.DataFrame] = []
    for pair in pairs:
        bars = bars_module.load(pair)
        frame = add_labels(pair_features(bars), bars, horizon)
        frame.insert(0, "pair", pair)
        blocks.append(frame)
    panel = pd.concat(blocks, ignore_index=True)

    #: cross-sectional context: where this pair's past move sits among the twenty
    #: at the *same* timestamp. Past returns only, so still causal.
    for column in ("retn_24", "retn_96", "retn_384"):
        grouped = panel.groupby("ts", observed=True)[column]
        panel[f"cs_rank_{column}"] = grouped.rank(pct=True)
        panel[f"cs_dev_{column}"] = panel[column] - grouped.transform("mean")
    panel["cs_rank_atr_z"] = panel.groupby("ts", observed=True)["atr_z"].rank(pct=True)
    return panel


LABEL_COLUMNS: Final[frozenset[str]] = frozenset(
    {"pair", "ts", "bar", "y_pips", "y_beats_cost", "y_up", "roundtrip_cost", "base_signal"}
)


def feature_columns(panel: pd.DataFrame) -> list[str]:
    return [c for c in panel.columns if c not in LABEL_COLUMNS]


# ---------------------------------------------------------------------------
# walk-forward
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Fold:
    index: int
    test_start: pd.Timestamp
    test_end: pd.Timestamp  # exclusive


def folds(edges: Sequence[str] = FOLD_EDGES) -> list[Fold]:
    stamps = [pd.Timestamp(e, tz="UTC") for e in edges]
    return [Fold(i, stamps[i], stamps[i + 1]) for i in range(len(stamps) - 1)]


def train_mask(
    panel: pd.DataFrame,
    test_start: pd.Timestamp,
    horizon: int = HORIZON,
    *,
    train_days: int | None = None,
) -> pd.Series:
    """Rows whose entire label window closes strictly before the test fold.

    Purging is on the **bar index**, per pair. A calendar purge would be wrong
    across a weekend, where 97 bars can span three days.
    """
    before = panel["ts"] < test_start
    first_test = panel.loc[~before].groupby("pair", observed=True)["bar"].min()
    limit = panel["pair"].map(first_test)
    keep = before & ((panel["bar"] + horizon + 1) < limit)
    if train_days is not None:
        keep = keep & (panel["ts"] >= test_start - pd.Timedelta(days=train_days))
    return keep.fillna(False)


# ---------------------------------------------------------------------------
# models
# ---------------------------------------------------------------------------


LGBM_REG: Final[dict[str, Any]] = {
    "objective": "regression",
    "n_estimators": 400,
    "learning_rate": 0.03,
    "num_leaves": 31,
    "min_child_samples": 300,
    "subsample": 0.8,
    "subsample_freq": 1,
    "colsample_bytree": 0.7,
    "reg_lambda": 5.0,
    "verbose": -1,
    "n_jobs": 4,
}
LGBM_CLF: Final[dict[str, Any]] = {**LGBM_REG, "objective": "binary"}


@dataclass
class WalkForward:
    """Out-of-sample predictions plus the per-fold train-side calibration."""

    predictions: pd.DataFrame
    importances: pd.DataFrame
    quantiles: pd.DataFrame
    diagnostics: dict[str, Any] = field(default_factory=dict)


def fit_predict(
    panel: pd.DataFrame,
    columns: Sequence[str],
    *,
    target: str = "y_pips",
    kind: str = "regression",
    horizon: int = HORIZON,
    train_stride: int = 6,
    train_days: int | None = None,
    shuffle_labels: bool = False,
    drop_pairs: Sequence[str] = (),
    fit_rows: pd.Series | None = None,
    predict_rows: pd.Series | None = None,
    seed: int = 7,
    sample_weight: str | None = None,
    params: dict[str, Any] | None = None,
    model: str = "lgbm",
    min_train_rows: int = 500,
) -> WalkForward:
    """Walk-forward out-of-sample predictions, per-fold importance and quantiles.

    ``train_stride`` thins the training rows. With a 96-bar label every bar's
    label overlaps the next 95, so consecutive rows are near-duplicates. Thinning
    costs little and stops the fit being dominated by that redundancy. It is
    **not** a leakage control and is not offered as one.
    """
    usable = panel["y_pips"].notna() & panel[list(columns)].notna().all(axis=1)
    fit_pool = usable if fit_rows is None else (usable & fit_rows)
    predict_pool = usable if predict_rows is None else (usable & predict_rows)
    if drop_pairs:
        fit_pool = fit_pool & ~panel["pair"].isin(list(drop_pairs))

    prediction_blocks: list[pd.DataFrame] = []
    importance_blocks: list[pd.DataFrame] = []
    quantile_rows: list[dict[str, Any]] = []
    rng = np.random.default_rng(seed)

    for fold in folds():
        test = (panel["ts"] >= fold.test_start) & (panel["ts"] < fold.test_end) & predict_pool
        train = train_mask(panel, fold.test_start, horizon, train_days=train_days) & fit_pool
        train = train & ((panel["bar"] % train_stride) == 0)
        train_rows = np.flatnonzero(train.to_numpy())
        test_rows = np.flatnonzero(test.to_numpy())
        if len(train_rows) < min_train_rows or not len(test_rows):
            continue

        x_train = panel.iloc[train_rows][list(columns)].to_numpy(dtype=np.float32)
        y_train = panel.iloc[train_rows][target].to_numpy(dtype=np.float64)
        if shuffle_labels:
            #: the negative control. Break the row/label pairing only; the label
            #: distribution, the feature matrix and the split stay identical.
            y_train = rng.permutation(y_train)
        weight = None
        if sample_weight is not None:
            weight = np.abs(panel.iloc[train_rows][sample_weight].to_numpy(dtype=np.float64))

        x_test = panel.iloc[test_rows][list(columns)].to_numpy(dtype=np.float32)
        raw_test, raw_train, gain, split = _fit_one(
            model, kind, params, seed, x_train, y_train, weight, x_test, list(columns)
        )

        prediction_blocks.append(
            pd.DataFrame(
                {
                    "row": test_rows,
                    "fold": fold.index,
                    "pred": raw_test,
                    "pair": panel.iloc[test_rows]["pair"].to_numpy(),
                    "bar": panel.iloc[test_rows]["bar"].to_numpy(),
                    "ts": panel.iloc[test_rows]["ts"].to_numpy(),
                    "y_pips": panel.iloc[test_rows]["y_pips"].to_numpy(),
                }
            )
        )
        #: thresholds come from the TRAIN prediction distribution, never the test
        #: fold's -- otherwise the position rule sees the fold it trades.
        quantile_rows.append(
            {
                "fold": fold.index,
                "n_train": int(len(train_rows)),
                "n_test": int(len(test_rows)),
                "train_start": str(panel.iloc[train_rows]["ts"].min()),
                "train_end": str(panel.iloc[train_rows]["ts"].max()),
                "test_start": str(fold.test_start),
                **{_q(level): float(np.quantile(raw_train, level)) for level in QUANTILE_LEVELS},
            }
        )
        if gain is not None:
            importance_blocks.append(
                pd.DataFrame(
                    {"fold": fold.index, "feature": list(columns), "gain": gain, "split": split}
                )
            )

    empty = pd.DataFrame()
    return WalkForward(
        predictions=pd.concat(prediction_blocks, ignore_index=True) if prediction_blocks else empty,
        importances=pd.concat(importance_blocks, ignore_index=True) if importance_blocks else empty,
        quantiles=pd.DataFrame(quantile_rows),
    )


def _fit_one(model, kind, params, seed, x_train, y_train, weight, x_test, columns):
    if model == "ridge":
        from sklearn.linear_model import Ridge
        from sklearn.preprocessing import StandardScaler

        scaler = StandardScaler().fit(x_train)
        fitted = Ridge(alpha=float((params or {}).get("alpha", 100.0)))
        fitted.fit(scaler.transform(x_train), y_train, sample_weight=weight)
        coef = np.abs(fitted.coef_)
        return (
            fitted.predict(scaler.transform(x_test)),
            fitted.predict(scaler.transform(x_train)),
            coef,
            np.ones_like(coef),
        )

    import lightgbm as lgb

    base = LGBM_CLF if kind == "classification" else LGBM_REG
    settings = {**base, **(params or {}), "random_state": seed}
    estimator = (lgb.LGBMClassifier if kind == "classification" else lgb.LGBMRegressor)(**settings)
    estimator.fit(x_train, y_train, sample_weight=weight)
    if kind == "classification":
        return (
            estimator.predict_proba(x_test)[:, 1],
            estimator.predict_proba(x_train)[:, 1],
            estimator.booster_.feature_importance("gain"),
            estimator.booster_.feature_importance("split"),
        )
    return (
        estimator.predict(x_test),
        estimator.predict(x_train),
        estimator.booster_.feature_importance("gain"),
        estimator.booster_.feature_importance("split"),
    )


# ---------------------------------------------------------------------------
# predictions -> positions
# ---------------------------------------------------------------------------


def decision_grid(frame: pd.DataFrame, stride: int, *, align: str = "bar") -> pd.Series:
    """Which rows are decision points.

    ``align="bar"`` spaces decisions every ``stride`` bars of that pair's own
    index, which is what the rule family does. ``align="ts"`` spaces them on the
    clock, so all twenty pairs decide at the same instant -- the only version a
    cross-sectional rank can use, because pairs do not share a bar count and a
    bar-index grid therefore scatters their decision points across the day.
    """
    if align == "bar":
        return (frame["bar"] % stride) == 0
    minutes = frame["ts"].astype("int64") // 60_000_000_000
    return (minutes % (stride * 15)) == 0


def grid_positions(
    walk: WalkForward,
    lengths: dict[str, int],
    *,
    stride: int = HORIZON,
    long_level: float = 0.90,
    short_level: float = 0.10,
    sign: float = 1.0,
    align: str = "bar",
) -> dict[str, pd.Series]:
    """A position decided on a fixed grid and held to the next grid point.

    The whole benchmark advantage is low turnover, so a model that re-decides
    every bar is not being asked the right question. ``stride`` is the decision
    spacing in bars, identical to the rule family's ``hold``.
    """
    positions = {pair: np.zeros(length, dtype=float) for pair, length in lengths.items()}
    if walk.predictions.empty:
        return {p: pd.Series(v, index=pd.RangeIndex(len(v))) for p, v in positions.items()}
    thresholds = walk.quantiles.set_index("fold")
    grid = walk.predictions[decision_grid(walk.predictions, stride, align=align)]
    for fold, block in grid.groupby("fold", observed=True):
        high = float(thresholds.loc[fold, _q(long_level)])
        low = float(thresholds.loc[fold, _q(short_level)])
        side = np.where(block["pred"] >= high, sign, np.where(block["pred"] <= low, -sign, 0.0))
        for pair, bar, value in zip(block["pair"], block["bar"], side, strict=True):
            if value:
                positions[pair][int(bar) : int(bar) + stride] = value
    return {p: pd.Series(v, index=pd.RangeIndex(len(v))) for p, v in positions.items()}


def cross_sectional_positions(
    walk: WalkForward,
    lengths: dict[str, int],
    *,
    stride: int = HORIZON,
    top_k: int = 4,
    sign: float = 1.0,
    align: str = "ts",
) -> dict[str, pd.Series]:
    """Long the ``top_k`` predicted pairs and short the bottom ``top_k``.

    Ranking happens inside one decision timestamp, so it needs no threshold
    fitted anywhere and is immune to the model's calibration drifting between
    folds -- a real risk when each fold is a separate fit.
    """
    positions = {pair: np.zeros(length, dtype=float) for pair, length in lengths.items()}
    if walk.predictions.empty:
        return {p: pd.Series(v, index=pd.RangeIndex(len(v))) for p, v in positions.items()}
    grid = walk.predictions[decision_grid(walk.predictions, stride, align=align)]
    for _, block in grid.groupby("ts", observed=True):
        if len(block) < 2 * top_k:
            continue
        ordered = block.sort_values("pred")
        for pair, bar in zip(ordered["pair"].head(top_k), ordered["bar"].head(top_k), strict=True):
            positions[pair][int(bar) : int(bar) + stride] = -sign
        for pair, bar in zip(ordered["pair"].tail(top_k), ordered["bar"].tail(top_k), strict=True):
            positions[pair][int(bar) : int(bar) + stride] = sign
    return {p: pd.Series(v, index=pd.RangeIndex(len(v))) for p, v in positions.items()}


def gate_positions(
    base: dict[str, pd.Series],
    walk: WalkForward,
    *,
    level: float = 0.50,
) -> dict[str, pd.Series]:
    """Meta-labelling: keep the base signal only where the model says take it.

    The gate is applied at the bar the base rule decides, and the threshold is
    again a train-side quantile.
    """
    if walk.predictions.empty:
        return {p: s * 0.0 for p, s in base.items()}
    thresholds = walk.quantiles.set_index("fold")
    allow = {pair: np.zeros(len(series), dtype=bool) for pair, series in base.items()}
    for fold, block in walk.predictions.groupby("fold", observed=True):
        cut = float(thresholds.loc[fold, _q(level)])
        taken = block[block["pred"] >= cut]
        for pair, bar in zip(taken["pair"], taken["bar"], strict=True):
            allow[pair][int(bar)] = True
    out: dict[str, pd.Series] = {}
    for pair, series in base.items():
        values = series.to_numpy().copy()
        #: a gate has to remove the whole trade, not just its first bar. Zeroing
        #: the entry bar alone would leave the next 95 bars of the run in place
        #: and merely delay the entry by one bar -- which reads as "the gate did
        #: nothing" in the trade count, because that is what it did.
        changed = np.r_[True, values[1:] != values[:-1]]
        starts = np.flatnonzero(changed)
        ends = np.r_[starts[1:], len(values)]
        for start, end in zip(starts, ends, strict=True):
            if values[start] != 0.0 and not allow[pair][start]:
                values[start:end] = 0.0
        out[pair] = pd.Series(values, index=series.index)
    return out


def mask_to_oos(position: pd.Series, bars: pd.DataFrame, start: str = OOS_START) -> pd.Series:
    """Zero a position outside the walk-forward region.

    Applied to the rule benchmarks too. Comparing a model measured on Aug-Dec
    against a rule measured on Apr-Dec would be a comparison of two different
    market periods wearing the same table.
    """
    live = (bars["ts"] >= pd.Timestamp(start, tz="UTC")).to_numpy()
    return pd.Series(np.where(live, position.to_numpy(), 0.0), index=position.index)


# ---------------------------------------------------------------------------
# reporting
# ---------------------------------------------------------------------------


@dataclass
class Variant:
    name: str
    positions: dict[str, pd.Series]
    note: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


def score(
    variant: Variant,
    loaded: dict[str, pd.DataFrame],
    *,
    periods: int = 5,
    oos_start: str = OOS_START,
) -> dict[str, Any]:
    """Cost-inclusive pooled metrics at every sensitivity multiplier.

    Pooling is equal-weight across pairs on a **timestamp** index, not on the
    positional bar index -- pairs do not share a bar count, so positional
    alignment would silently pair one pair's Tuesday with another's Wednesday.
    """
    pairs = [p for p in loaded if p in variant.positions]
    out: dict[str, Any] = {"strategy": variant.name, "note": variant.note, **variant.extra}
    for multiplier in engine.COST_MULTIPLIERS:
        results = [
            engine.evaluate(
                loaded[p],
                variant.positions[p],
                name=variant.name,
                pair=p,
                cost_multiplier=multiplier,
            )
            for p in pairs
        ]
        aligned = pd.concat(
            [r.net.set_axis(loaded[r.pair]["ts"]).rename(r.pair) for r in results], axis=1
        ).fillna(0.0)
        pooled = aligned.mean(axis=1).sort_index()
        tag = "" if multiplier == 1.0 else f"_x{multiplier:g}"
        out[f"net_pips_per_pair{tag}"] = round(float(pooled.sum()), 1)
        if multiplier != 1.0:
            continue
        std = float(pooled.std())
        equity = pooled.cumsum()
        per_pair_net = {r.pair: round(r.metrics["net_pips"], 1) for r in results}
        total = sum(abs(v) for v in per_pair_net.values()) or 1.0
        best = max(per_pair_net, key=per_pair_net.get)

        def mean_of(key: str, how=np.mean, digits: int = 3, rows=results) -> float:
            return round(float(how([r.metrics[key] for r in rows])), digits)

        out.update(
            {
                "gross_pips_per_pair": mean_of("gross_pips", digits=1),
                "cost_pips_per_pair": mean_of("cost_pips", digits=1),
                "sharpe_like": round(
                    float(pooled.mean() / std * np.sqrt(engine.BARS_PER_YEAR)) if std else 0.0, 3
                ),
                "max_drawdown_pips": round(float((equity - equity.cummax()).min()), 1),
                "pairs_positive": int(sum(1 for v in per_pair_net.values() if v > 0)),
                "pairs": len(pairs),
                "closed_trades": int(sum(r.metrics["n_closed_trades"] for r in results)),
                "win_rate": mean_of("win_rate", np.nanmean, 4),
                "profit_factor": mean_of("profit_factor", np.nanmedian),
                "avg_trade_pips": mean_of("avg_trade_pips", np.nanmean),
                "turnover_per_year": mean_of("turnover_per_year", digits=1),
                "exposure": mean_of("exposure"),
                "top_pair": best,
                "top_pair_share_of_abs_pnl": round(abs(per_pair_net[best]) / total, 3),
                "net_by_pair": dict(sorted(per_pair_net.items())),
            }
        )
        live = pooled[pooled.index >= pd.Timestamp(oos_start, tz="UTC")]
        out["chronological_slices"] = engine.stability(
            live.reset_index(drop=True), None, periods=periods
        )
        out["monthly_net_pips"] = {
            str(period): round(float(value), 1)
            for period, value in live.groupby(live.index.to_period("M")).sum().items()
        }
    return out


def prediction_quality(walk: WalkForward) -> dict[str, Any]:
    """Out-of-sample IC, before any position rule can flatter or ruin it."""
    if walk.predictions.empty:
        return {}
    from scipy import stats

    frame = walk.predictions
    overall = stats.spearmanr(frame["pred"], frame["y_pips"]).statistic
    by_fold = {
        int(fold): round(float(stats.spearmanr(block["pred"], block["y_pips"]).statistic), 4)
        for fold, block in frame.groupby("fold", observed=True)
    }
    by_pair = {
        str(pair): round(float(stats.spearmanr(block["pred"], block["y_pips"]).statistic), 4)
        for pair, block in frame.groupby("pair", observed=True)
    }
    return {
        "oos_spearman_ic": round(float(overall), 4),
        "oos_ic_by_fold": by_fold,
        "oos_ic_pairs_positive": int(sum(1 for v in by_pair.values() if v > 0)),
        "oos_ic_by_pair": by_pair,
        "n_oos_rows": int(len(frame)),
    }


def top_features(walk: WalkForward, limit: int = 20) -> list[dict[str, Any]]:
    if walk.importances.empty:
        return []
    total = walk.importances.groupby("feature")[["gain", "split"]].sum()
    total["gain_share"] = total["gain"] / total["gain"].sum()
    ordered = total.sort_values("gain", ascending=False).head(limit)
    return [
        {
            "feature": str(name),
            "gain_share": round(float(row["gain_share"]), 4),
            "splits": int(row["split"]),
        }
        for name, row in ordered.iterrows()
    ]


__all__ = [
    "CLASSIFICATION",
    "CLASSIFICATION_SECONDARY",
    "FOLD_EDGES",
    "HORIZON",
    "OOS_START",
    "PAIRS",
    "QUANTILE_LEVELS",
    "Variant",
    "WalkForward",
    "add_labels",
    "build_panel",
    "cross_sectional_positions",
    "decision_grid",
    "feature_columns",
    "fit_predict",
    "folds",
    "gate_positions",
    "grid_positions",
    "mask_to_oos",
    "pair_features",
    "prediction_quality",
    "score",
    "top_features",
    "train_mask",
]
