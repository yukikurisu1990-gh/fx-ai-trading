"""Effective-N estimator tests (synthetic counts only)."""

from __future__ import annotations

import pytest

from scripts.m15_gate3a.effective_n import (
    INSUFFICIENT_SAMPLE,
    SUFFICIENT,
    EffectiveNError,
    effective_n,
)


def test_raw_count_preserved_and_independent_recovers_raw() -> None:
    r = effective_n(5000, overlap_fraction=0.0, cross_pair_corr=0.0, n_pairs=20)
    assert r["raw_event_count"] == 5000
    assert r["effective_n"] == pytest.approx(5000.0)  # no thinning when independent
    assert r["verdict"] == SUFFICIENT


def test_effective_n_from_adjustments() -> None:
    r = effective_n(5000, overlap_fraction=0.5, cross_pair_corr=0.2, n_pairs=20)
    # rho_h = 1 + 23*0.5 = 12.5 ; rho_x = 1 + 19*0.2 = 4.8 ; 5000/(12.5*4.8) ~= 83.3
    assert r["effective_n"] == pytest.approx(5000 / (12.5 * 4.8))
    assert r["verdict"] == INSUFFICIENT_SAMPLE  # below 400


def test_below_floor_insufficient_sample() -> None:
    # raw below the 1000 floor -> INSUFFICIENT_SAMPLE at holdout
    r = effective_n(900, overlap_fraction=0.0, cross_pair_corr=0.0, n_pairs=1)
    assert r["verdict"] == INSUFFICIENT_SAMPLE


def test_effective_below_400_insufficient() -> None:
    r = effective_n(1200, overlap_fraction=0.9, cross_pair_corr=0.5, n_pairs=20)
    assert r["effective_n"] < 400
    assert r["verdict"] == INSUFFICIENT_SAMPLE


def test_invalid_adjustments_fail_closed() -> None:
    with pytest.raises(EffectiveNError):
        effective_n(1000, overlap_fraction=1.5, cross_pair_corr=0.0, n_pairs=1)
    with pytest.raises(EffectiveNError):
        effective_n(1000, overlap_fraction=0.0, cross_pair_corr=-0.1, n_pairs=1)
    with pytest.raises(EffectiveNError):
        effective_n(-5, overlap_fraction=0.0, cross_pair_corr=0.0, n_pairs=1)
    with pytest.raises(EffectiveNError):
        effective_n(1000, overlap_fraction=0.0, cross_pair_corr=0.0, n_pairs=0)
