"""The three pre-registered tracks, run once each on the seen corpus.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `PRODUCTION_READINESS_NOT_CLAIMED`

The strongest status reachable here is `DEVELOPMENT_MODEL_CANDIDATE`. Nothing in
this module may be described as a confirmed edge, and no protected span is
readable from it.

What "cost-adjusted target" means in practice
---------------------------------------------

The pre-registration asks each track to predict a cost-adjusted quantity. A
per-leg cost adjustment is **not identified before the position is known** — the
cost of a leg depends on how much the position changes, which depends on the
prediction — so the regression target is the forward excess return and the cost
is charged where it is determined: at portfolio construction and in every
reported metric. The success rule is stated entirely in net terms, so nothing
rests on a gross figure.

Why Track B conditions a gain rather than a level
--------------------------------------------------

A regime-dependent intercept is identical across currencies on a day, and the
target sums to zero across currencies on a day, so its covariance with the target
is exactly zero — the coefficient is unidentified by construction. The affordable
and *identified* form is a regime-dependent **gain** on a shared slope vector,
which costs the same in the capacity budget and actually estimates something.
"""

from __future__ import annotations

from typing import Any, Final

import numpy as np
import pandas as pd

from scripts.research.model_learning import corpus as corpus_module
from scripts.research.model_learning import features as feature_module
from scripts.research.model_learning import prereg as prereg_module
from scripts.research.model_learning import walkforward as wf

#: Days of trailing history the longest feature needs before any fold may start.
WARMUP_DAYS: Final[int] = 60


def _stack(
    frames: dict[str, pd.DataFrame], names: tuple[str, ...], days: pd.DatetimeIndex
) -> tuple[np.ndarray, list[tuple[pd.Timestamp, str]]]:
    columns = []
    keys: list[tuple[pd.Timestamp, str]] = []
    first = frames[names[0]]
    for day in days:
        for currency in first.columns:
            keys.append((day, currency))
    for name in names:
        frame = frames[name].reindex(days)
        columns.append(frame.to_numpy().reshape(-1))
    return np.column_stack(columns), keys


def _rows(
    frames: dict[str, pd.DataFrame],
    names: tuple[str, ...],
    target: pd.DataFrame,
    days: pd.DatetimeIndex,
) -> pd.DataFrame:
    """One tidy frame of (day, currency, features…, y), with incomplete rows dropped."""
    pieces = {
        name: frames[name].reindex(days).stack(future_stack=True).rename(name) for name in names
    }
    pieces["y"] = target.reindex(days).stack(future_stack=True).rename("y")
    tidy = pd.concat(pieces.values(), axis=1)
    tidy.index.names = ["day", "currency"]
    return tidy.dropna()


def _predict_linear(
    tidy: pd.DataFrame,
    names: tuple[str, ...],
    folds: list[wf.Fold],
    target_df: float,
) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    """Fit each fold's ridge on the purged training rows, score the test rows."""
    scores = pd.Series(index=tidy.index, dtype=float)
    diagnostics: list[dict[str, Any]] = []
    days = tidy.index.get_level_values("day")
    for fold in folds:
        train = tidy[days <= fold.train_end]
        test = tidy[(days >= fold.test_start) & (days <= fold.test_end)]
        if train.empty or test.empty:
            continue
        centre, scale = wf.standardise(train[list(names)].to_numpy())
        design = (train[list(names)].to_numpy() - centre) / scale
        beta, penalty, achieved = wf.fit_ridge(design, train["y"].to_numpy(), target_df)
        scored = ((test[list(names)].to_numpy() - centre) / scale) @ beta
        scores.loc[test.index] = scored
        diagnostics.append(
            {
                "fold": fold.index,
                "train_days": fold.n_train_days,
                "test_days": fold.n_test_days,
                "penalty": round(float(penalty), 6),
                "effective_df": round(float(achieved), 4),
                "coefficients": {
                    name: round(float(value), 6) for name, value in zip(names, beta, strict=True)
                },
            }
        )
    frame = scores.dropna().unstack("currency")
    return frame, diagnostics


def _predict_regime_gain(
    tidy: pd.DataFrame,
    names: tuple[str, ...],
    folds: list[wf.Fold],
    target_df: float,
    state: pd.Series,
) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    """Shared slopes, one multiplicative gain per state, both fitted in-fold."""
    scores = pd.Series(index=tidy.index, dtype=float)
    diagnostics: list[dict[str, Any]] = []
    days = tidy.index.get_level_values("day")
    for fold in folds:
        train = tidy[days <= fold.train_end]
        test = tidy[(days >= fold.test_start) & (days <= fold.test_end)]
        if train.empty or test.empty:
            continue
        centre, scale = wf.standardise(train[list(names)].to_numpy())
        design = (train[list(names)].to_numpy() - centre) / scale
        beta, penalty, achieved = wf.fit_ridge(design, train["y"].to_numpy(), target_df)
        base_train = design @ beta
        train_state = state.reindex(train.index.get_level_values("day")).to_numpy()
        gains: dict[int, float] = {}
        for value in (0, 1):
            mask = train_state == value
            if mask.sum() < 2 or not np.any(base_train[mask]):
                gains[value] = 1.0
                continue
            denominator = float(np.dot(base_train[mask], base_train[mask]))
            gains[value] = (
                float(np.dot(base_train[mask], train["y"].to_numpy()[mask]) / denominator)
                if denominator > 0
                else 1.0
            )
        base_test = ((test[list(names)].to_numpy() - centre) / scale) @ beta
        test_state = state.reindex(test.index.get_level_values("day")).to_numpy()
        scored = base_test * np.where(test_state == 1, gains[1], gains[0])
        scores.loc[test.index] = scored
        diagnostics.append(
            {
                "fold": fold.index,
                "penalty": round(float(penalty), 6),
                "effective_df": round(float(achieved), 4),
                "regime_gains": {str(k): round(float(v), 6) for k, v in gains.items()},
                "coefficients": {
                    name: round(float(value), 6) for name, value in zip(names, beta, strict=True)
                },
            }
        )
    frame = scores.dropna().unstack("currency")
    return frame, diagnostics


def _fold_labels(days: pd.DatetimeIndex, folds: list[wf.Fold]) -> pd.Series:
    labels = pd.Series(index=days, dtype=float)
    for fold in folds:
        labels[(days >= fold.test_start) & (days <= fold.test_end)] = fold.index
    return labels


def _verdict(
    model: dict[str, Any], baseline: dict[str, Any], stressed: dict[str, Any]
) -> dict[str, Any]:
    """The pre-registered success rule, every clause evaluated and reported."""
    rule = prereg_module.SUCCESS_RULE
    incremental = model["net_annualised_ir"] - baseline["net_annualised_ir"]
    clauses = {
        "beats_baseline_by_mrie": incremental >= rule["beats_its_declared_baseline_by_at_least_ir"],
        "net_annualised_ir_positive": model["net_annualised_ir"] > 0,
        "survives_stressed_cost": stressed["net_annualised_ir"] > 0,
        "enough_folds_positive": model["share_of_folds_positive"]
        >= rule["positive_in_at_least_this_share_of_folds"],
        "enough_currencies_positive": model["positive_currencies"]
        >= rule["positive_currencies_at_least"],
        "top_ten_days_not_dominant": (
            model["top_ten_day_share_of_net"] is None
            or model["top_ten_day_share_of_net"] <= rule["top_ten_day_share_of_net_at_most"]
        ),
    }
    return {
        "incremental_net_annualised_ir": round(float(incremental), 4),
        "clauses": clauses,
        "survives": all(clauses.values()),
        "failed_clauses": sorted(name for name, ok in clauses.items() if not ok),
    }


def run() -> dict[str, Any]:
    """Every track, once. The pre-registration is checked before anything is read."""
    frozen = prereg_module.assert_frozen()
    panel = corpus_module.currency_panel()
    built = feature_module.build(panel)
    excess = panel["currency_excess_return"]
    forward = excess.shift(-1).dropna(how="all")
    days = forward.index
    usable = days[WARMUP_DAYS:]

    folds = wf.make_folds(
        usable,
        initial_train_years=prereg_module.CV_ARCHITECTURE["initial_train_years"],
        step_years=prereg_module.CV_ARCHITECTURE["step_years"],
        horizon_days=1,
    )
    fold_of = _fold_labels(usable, folds)

    #: Track B's state: the two-state split on the basket's 60-day realised
    #: volatility, thresholded at the expanding median of the **training** data
    #: only. An expanding median computed over the whole series and then split
    #: would carry the future into the state, which is the cheapest leakage
    #: available here.
    basket_vol = panel["common_factor"]["common_factor"].rolling(60, min_periods=60).std(ddof=0)
    threshold = basket_vol.expanding(min_periods=60).median().shift(1)
    state = (basket_vol > threshold).astype(float).reindex(usable)

    roundtrip = prereg_module.COST_MODEL["basket_roundtrip_bp"]
    stress = prereg_module.COST_MODEL["stress_multiple"]
    results: dict[str, Any] = {}

    for track in prereg_module.TRACKS:
        names = tuple(track["features"])
        tidy = _rows(built, names, forward, usable)
        target_df = float(track["declared_effective_parameters"])

        if track["track"] == "B":
            scores, diagnostics = _predict_regime_gain(tidy, names, folds, target_df, state)
            baseline_scores, baseline_diagnostics = _predict_linear(tidy, names, folds, target_df)
            baseline_weights = wf.weights_from_scores(baseline_scores)
            baseline_label = "the same features with no regime split"
        else:
            scores, diagnostics = _predict_linear(tidy, names, folds, target_df)
            baseline_diagnostics = []
            anchor = built["currency_excess_return_20d_z"].reindex(scores.index)
            baseline_weights = wf.top_bottom_weights(anchor)
            baseline_label = "unfitted top-2/bottom-2 rank of the 20-day excess return"

        model_weights = wf.weights_from_scores(scores)
        if track["track"] == "C":
            #: Track C does not choose a direction. It filters the base
            #: opportunity, so its book is the base book with the rejected legs
            #: set to zero and the remainder renormalised to the same gross.
            base = wf.top_bottom_weights(
                built["currency_excess_return_20d_z"].reindex(scores.index)
            )
            accept_threshold = scores.stack(future_stack=True).dropna().median()
            keep = (scores >= accept_threshold).astype(float)
            filtered = base * keep
            gross = filtered.abs().sum(axis=1).replace(0.0, np.nan)
            model_weights = filtered.div(gross, axis=0).fillna(0.0)
            baseline_weights = base
            baseline_label = "the base opportunity taken in full"

        index = model_weights.index
        realised = forward.reindex(index)
        model_series = wf.evaluate(model_weights, realised, roundtrip_bp=roundtrip)
        stressed_series = wf.evaluate(
            model_weights, realised, roundtrip_bp=roundtrip, cost_multiple=stress
        )
        baseline_series = wf.evaluate(
            baseline_weights.reindex(index).fillna(0.0), realised, roundtrip_bp=roundtrip
        )
        labels = fold_of.reindex(index)
        model_summary = wf.summarise(
            model_series, realised, fold_of=labels, regime=state.reindex(index)
        )
        results[track["candidate_id"]] = {
            "track": track["track"],
            "baseline": baseline_label,
            "model": model_summary,
            "model_at_stressed_cost": wf.summarise(stressed_series, realised, fold_of=labels),
            "baseline_metrics": wf.summarise(baseline_series, realised, fold_of=labels),
            "fold_diagnostics": diagnostics,
            "baseline_fold_diagnostics": baseline_diagnostics,
            "verdict": _verdict(
                model_summary,
                wf.summarise(baseline_series, realised, fold_of=labels),
                wf.summarise(stressed_series, realised, fold_of=labels),
            ),
        }

    return {
        "preregistration_frozen_hash": frozen,
        "corpus": corpus_module.provenance(panel),
        "feature_provenance": feature_module.provenance(),
        "folds": [
            {
                "index": fold.index,
                "train_end": str(fold.train_end.date()),
                "test_start": str(fold.test_start.date()),
                "test_end": str(fold.test_end.date()),
                "train_days": fold.n_train_days,
                "test_days": fold.n_test_days,
            }
            for fold in folds
        ],
        "tracks": results,
        "protected_spans_read": False,
        "strongest_status_reachable": "DEVELOPMENT_MODEL_CANDIDATE",
    }


__all__ = ["WARMUP_DAYS", "run"]
