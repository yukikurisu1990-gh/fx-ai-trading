"""Validation-only threshold selector tests (PR #411 B-2: full sweep required)."""

from __future__ import annotations

import pytest

from scripts.ml_step4.thresholds import ThresholdSelectionError, select_threshold


def _val(sharpe: float) -> dict[str, float]:
    return {"daily_portfolio_sharpe": sharpe, "n_trades": 500}


def _full(s35: float, s40: float, s45: float) -> dict[float, dict[str, float]]:
    return {0.35: _val(s35), 0.40: _val(s40), 0.45: _val(s45)}


def test_full_sweep_selects_best_validation_sharpe() -> None:
    result = select_threshold(_full(0.5, 0.9, 0.7))
    assert result.selected_threshold == 0.40
    assert result.selected_metrics["daily_portfolio_sharpe"] == 0.9
    assert {r["threshold"] for r in result.rejected} == {0.35, 0.45}
    assert result.as_dict()["holdout_inspected"] is False


def test_rejected_variants_are_the_two_non_selected() -> None:
    result = select_threshold(_full(0.9, 0.1, 0.2))
    assert result.selected_threshold == 0.35
    rejected = {r["threshold"]: r["validation_metrics"] for r in result.rejected}
    assert set(rejected) == {0.40, 0.45}
    assert all(not r["selected"] for r in result.rejected)


def test_holdout_not_required_for_selection() -> None:
    # No holdout data provided anywhere; selection succeeds on validation only.
    result = select_threshold(_full(0.1, 0.15, 0.2))
    assert result.selected_threshold == 0.45


# --- PR #411 B-2 fix: exactly the full registered candidate set is required


def test_b2_single_candidate_subset_raises() -> None:
    with pytest.raises(ThresholdSelectionError, match="exactly the registered"):
        select_threshold({0.45: _val(0.9)})


def test_b2_missing_one_candidate_raises() -> None:
    with pytest.raises(ThresholdSelectionError, match="missing=\\[0.4\\]"):
        select_threshold({0.35: _val(0.1), 0.45: _val(0.2)})


def test_b2_extra_candidate_raises() -> None:
    sweep = _full(0.1, 0.2, 0.3)
    sweep[0.50] = _val(0.9)
    with pytest.raises(ThresholdSelectionError, match="extra=\\[0.5\\]"):
        select_threshold(sweep)


def test_b2_non_numeric_key_raises() -> None:
    with pytest.raises(ThresholdSelectionError, match="non-numeric"):
        select_threshold({"high": _val(0.9), 0.35: _val(0.1), 0.40: _val(0.1)})  # type: ignore[dict-item]


def test_b2_missing_selection_metric_raises() -> None:
    sweep = _full(0.1, 0.2, 0.3)
    sweep[0.40] = {"n_trades": 100}  # metric absent for one candidate
    with pytest.raises(ThresholdSelectionError, match="missing selection metric"):
        select_threshold(sweep)


def test_b2_non_finite_metric_raises() -> None:
    sweep = _full(0.1, 0.2, 0.3)
    sweep[0.40] = {"daily_portfolio_sharpe": float("nan")}
    with pytest.raises(ThresholdSelectionError, match="non-finite"):
        select_threshold(sweep)


def test_b2_empty_input_raises() -> None:
    with pytest.raises(ThresholdSelectionError):
        select_threshold({})


# --- Deterministic tie-breaking (rule recorded: prefer 0.40, else smallest)


def test_tie_prefers_production_default() -> None:
    result = select_threshold(_full(0.8, 0.8, 0.8))
    assert result.selected_threshold == 0.40


def test_tie_without_default_prefers_smallest() -> None:
    # 0.35 and 0.45 tie at best; 0.40 is strictly worse -> smallest of the tied.
    result = select_threshold(_full(0.8, 0.1, 0.8))
    assert result.selected_threshold == 0.35


def test_selection_is_deterministic_across_key_order() -> None:
    a = select_threshold({0.45: _val(0.2), 0.35: _val(0.2), 0.40: _val(0.1)})
    b = select_threshold({0.35: _val(0.2), 0.40: _val(0.1), 0.45: _val(0.2)})
    assert a.selected_threshold == b.selected_threshold == 0.35
