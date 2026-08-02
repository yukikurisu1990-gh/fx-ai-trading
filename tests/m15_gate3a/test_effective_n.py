"""Effective-N estimator tests — pinned to the committed APPROVED_SPEC.

The spec (``artifacts/m15_gate3a/effective_n_estimator_spec.json``) fixes:

    rho_h_pair = 1 + (H - 1) * overlap_fraction_pair      H = 24
    N_eff_pair = N_raw_pair / rho_h_pair
    rho_x      = 1 + (P - 1) * mean_abs_pairwise_corr
    N_eff      = (sum of N_eff_pair) / rho_x

Expected values below are derived by hand from that spec, independently of the
implementation. Synthetic counts only.
"""

from __future__ import annotations

import pytest

from scripts.m15_gate3a.effective_n import (
    INSUFFICIENT_SAMPLE,
    NOT_EVALUATED,
    SUFFICIENT,
    EffectiveNError,
    effective_n,
)

# Contract constants restated independently of the module under test.
H = 24
RAW_FLOOR = 1000
NEFF_FLOOR = 400


def _pp(pair: str, raw: int, overlap: float) -> dict:
    return {"pair": pair, "raw_event_count": raw, "overlap_fraction": overlap}


def test_raw_count_preserved_and_independent_recovers_raw() -> None:
    pairs = [_pp(f"P{i}", 250, 0.0) for i in range(20)]
    r = effective_n(pairs, cross_pair_corr=0.0)
    assert r["raw_event_count"] == 5000
    assert r["effective_n"] == pytest.approx(5000.0)  # no thinning when independent
    assert r["verdict"] == SUFFICIENT
    assert r["n_pairs"] == 20
    assert r["horizon_bars"] == H


def test_per_pair_formula_matches_approved_spec() -> None:
    # Two pairs, different overlap: 250/(1+23*0.5) + 250/(1+23*0.2) = 20.0 + 45.4545...
    pairs = [_pp("A", 250, 0.5), _pp("B", 250, 0.2)]
    r = effective_n(pairs, cross_pair_corr=0.1)
    expected_a = 250 / (1 + (H - 1) * 0.5)
    expected_b = 250 / (1 + (H - 1) * 0.2)
    expected = (expected_a + expected_b) / (1 + (2 - 1) * 0.1)
    assert r["per_pair"][0]["effective_n"] == pytest.approx(expected_a)
    assert r["per_pair"][1]["effective_n"] == pytest.approx(expected_b)
    assert r["effective_n"] == pytest.approx(expected)
    assert r["rho_x"] == pytest.approx(1.1)


def test_b3_heterogeneous_overlap_is_insufficient_under_approved_spec() -> None:
    """B-3 regression: the audited counter-example.

    Per-pair (approved): 50/1 + 8000/24 = 383.33 -> below the 400 floor.
    The pre-fix portfolio scalar gave 8050/(1+23*0.5) = 644.0 -> SUFFICIENT.
    """
    r = effective_n([_pp("A", 50, 0.0), _pp("B", 8000, 1.0)], cross_pair_corr=0.0)
    assert r["effective_n"] == pytest.approx(383.3333333, rel=1e-6)
    assert r["effective_n"] < NEFF_FLOOR
    assert r["verdict"] == INSUFFICIENT_SAMPLE
    # The divergent scalar result must NOT be what we compute.
    assert r["effective_n"] != pytest.approx(644.0, rel=1e-6)


def test_below_raw_floor_insufficient_sample() -> None:
    r = effective_n([_pp("A", 900, 0.0)], cross_pair_corr=0.0)
    assert r["raw_event_count"] == 900 < RAW_FLOOR
    assert r["verdict"] == INSUFFICIENT_SAMPLE


def test_holdout_floors_are_value_pinned() -> None:
    """N_EFF_HOLDOUT_FLOOR must drive the verdict, not just be reported."""
    # raw = 1000 (>= raw floor), N_eff = 1000 / (1 + 3*1.0) = 250 -> below 400.
    pairs = [_pp(f"P{i}", 250, 0.0) for i in range(4)]
    r = effective_n(pairs, cross_pair_corr=1.0)
    assert r["raw_event_count"] == 1000
    assert r["effective_n"] == pytest.approx(250.0)
    assert r["verdict"] == INSUFFICIENT_SAMPLE
    # Exactly at the N_eff floor with raw above its floor -> sufficient.
    at_floor = effective_n([_pp(f"P{i}", 400, 0.0) for i in range(4)], cross_pair_corr=1.0)
    assert at_floor["effective_n"] == pytest.approx(float(NEFF_FLOOR))
    assert at_floor["verdict"] == SUFFICIENT


def test_raw_floor_boundary_is_pinned() -> None:
    just_below = effective_n([_pp("A", RAW_FLOOR - 1, 0.0)], cross_pair_corr=0.0)
    exactly_at = effective_n([_pp("A", RAW_FLOOR, 0.0)], cross_pair_corr=0.0)
    assert just_below["verdict"] == INSUFFICIENT_SAMPLE
    assert exactly_at["verdict"] == SUFFICIENT


def test_verdict_tokens_are_pinned_to_literals() -> None:
    """Retargeting the verdict constants must not go unnoticed."""
    assert SUFFICIENT == "SAMPLE_SUFFICIENT"
    assert INSUFFICIENT_SAMPLE == "INSUFFICIENT_SAMPLE"
    assert NOT_EVALUATED == "NOT_EVALUATED_AT_THIS_ROLE"


def test_invalid_adjustments_fail_closed() -> None:
    with pytest.raises(EffectiveNError):
        effective_n([_pp("A", 1000, 1.5)], cross_pair_corr=0.0)
    with pytest.raises(EffectiveNError):
        effective_n([_pp("A", 1000, 0.0)], cross_pair_corr=-0.1)
    with pytest.raises(EffectiveNError):
        effective_n([_pp("A", -5, 0.0)], cross_pair_corr=0.0)
    with pytest.raises(EffectiveNError):
        effective_n([], cross_pair_corr=0.0)
    with pytest.raises(EffectiveNError):
        effective_n([_pp("A", 1000, float("nan"))], cross_pair_corr=0.0)
    with pytest.raises(EffectiveNError):
        effective_n([_pp("A", 1000, 0.0)], cross_pair_corr=float("nan"))
    with pytest.raises(EffectiveNError):
        effective_n([_pp("A", True, 0.0)], cross_pair_corr=0.0)  # bool is not a count
    with pytest.raises(EffectiveNError):
        effective_n([_pp("A", 1, 0.0), _pp("A", 1, 0.0)], cross_pair_corr=0.0)  # duplicate pair
