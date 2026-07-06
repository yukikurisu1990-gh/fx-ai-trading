"""Warm-up burn-in policy tests (PR #430 T-1)."""

from __future__ import annotations

import pytest

from scripts.m15_gate3a.warmup import WarmupPolicy, WarmupPolicyError


def test_valid_policy_metadata() -> None:
    m = WarmupPolicy(w_bars=300, longest_feature_lookback_bars=200).as_metadata()
    assert m["first_w_bars_event_eligible"] is False
    assert m["dead_window_loaded"] is False
    assert m["w_bars"] == 300


def test_w_too_small_fails() -> None:
    with pytest.raises(WarmupPolicyError):
        WarmupPolicy(w_bars=100, longest_feature_lookback_bars=200).validate()


def test_w_missing_or_nonpositive_fails() -> None:
    with pytest.raises(WarmupPolicyError):
        WarmupPolicy(w_bars=0, longest_feature_lookback_bars=10).validate()


def test_load_before_forward_floor_fails() -> None:
    p = WarmupPolicy(w_bars=50, longest_feature_lookback_bars=50)
    with pytest.raises(WarmupPolicyError):
        p.assert_load_allowed("2026-03-01T00:00:00Z")  # dead window
