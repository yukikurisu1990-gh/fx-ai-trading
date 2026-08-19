"""Warm-up burn-in policy tests (PR #430 T-1)."""

from __future__ import annotations

import pytest

from scripts.m15_gate3a.warmup import WarmupPolicy, WarmupPolicyError


def test_valid_policy_metadata() -> None:
    """R-1: the two vacuous self-attestations are gone; the measured facts stay.

    ``first_w_bars_event_eligible: False`` and ``dead_window_loaded: False`` were
    hard-coded constants — neither could ever hold its opposite value, and the
    second was the T-1 leakage claim itself emitted as a fact this class never
    measures. They are deleted, not reported. What replaces them is a genuinely
    two-valued predicate for each property, exercised below, plus the derived
    boundary the metadata does legitimately declare.
    """
    policy = WarmupPolicy(w_bars=300, longest_feature_lookback_bars=200)
    m = policy.as_metadata()
    assert m["w_bars"] == 300
    assert m["longest_feature_lookback_bars"] == 200
    assert m["first_eligible_bar_index"] == 300
    assert "first_w_bars_event_eligible" not in m
    assert "dead_window_loaded" not in m
    # Both replacements answer both ways on the same code path.
    assert policy.is_event_eligible(299) is False
    assert policy.is_event_eligible(300) is True
    assert policy.loads_pre_forward("2026-04-24T23:59:59Z") is True
    assert policy.loads_pre_forward("2026-04-25T00:00:00Z") is False


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
