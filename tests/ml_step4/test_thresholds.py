"""Validation-only threshold selector tests."""

from __future__ import annotations

import pytest

from scripts.ml_step4.thresholds import ThresholdSelectionError, select_threshold


def _val(sharpe: float) -> dict[str, float]:
    return {"daily_portfolio_sharpe": sharpe, "n_trades": 500}


def test_selects_best_validation_sharpe() -> None:
    result = select_threshold({0.35: _val(0.5), 0.40: _val(0.9), 0.45: _val(0.7)})
    assert result.selected_threshold == 0.40
    assert result.selected_metrics["daily_portfolio_sharpe"] == 0.9
    assert {r["threshold"] for r in result.rejected} == {0.35, 0.45}
    assert result.as_dict()["holdout_inspected"] is False


def test_holdout_not_required_for_selection() -> None:
    # No holdout data provided anywhere; selection still succeeds.
    result = select_threshold({0.35: _val(0.1), 0.45: _val(0.2)})
    assert result.selected_threshold == 0.45


def test_unregistered_threshold_rejected() -> None:
    with pytest.raises(ThresholdSelectionError):
        select_threshold({0.50: _val(0.9)})


def test_missing_selection_metric_fails_closed() -> None:
    with pytest.raises(ThresholdSelectionError):
        select_threshold({0.40: {"n_trades": 100}})


def test_tie_prefers_production_default() -> None:
    result = select_threshold({0.35: _val(0.8), 0.40: _val(0.8), 0.45: _val(0.8)})
    assert result.selected_threshold == 0.40  # production default wins ties


def test_tie_without_default_prefers_smallest() -> None:
    result = select_threshold({0.35: _val(0.8), 0.45: _val(0.8)})
    assert result.selected_threshold == 0.35


def test_empty_input_fails_closed() -> None:
    with pytest.raises(ThresholdSelectionError):
        select_threshold({})


def test_non_finite_metric_fails_closed() -> None:
    with pytest.raises(ThresholdSelectionError):
        select_threshold({0.40: {"daily_portfolio_sharpe": float("nan")}})
