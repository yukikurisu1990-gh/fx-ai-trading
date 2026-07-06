"""No-overlap proof utility tests — metadata-only, fail-closed."""

from __future__ import annotations

import pytest

from scripts.m15_gate3a.no_overlap import (
    NoOverlapError,
    assert_design_bounds,
    assert_forward_bounds,
    assert_no_dead_window,
    assert_per_file_bounds,
)
from scripts.m15_gate3a.warmup import WarmupPolicy, WarmupPolicyError


def test_design_ending_before_dead_window_passes() -> None:
    assert_design_bounds("2025-04-25T00:00:00Z", "2026-02-28T23:59:59Z")


def test_design_touching_dead_window_fails() -> None:
    with pytest.raises(NoOverlapError):
        assert_design_bounds("2025-04-25T00:00:00Z", "2026-03-01T00:00:00Z")


def test_forward_beginning_after_dead_window_passes() -> None:
    assert_forward_bounds("2026-04-25T00:00:00Z", "2026-07-01T00:00:00Z")


def test_forward_touching_dead_window_fails() -> None:
    with pytest.raises(NoOverlapError):
        assert_forward_bounds("2026-04-24T12:00:00Z", "2026-07-01T00:00:00Z")


def test_any_role_intersecting_dead_window_fails() -> None:
    with pytest.raises(NoOverlapError):
        assert_no_dead_window("2026-03-15T00:00:00Z", "2026-03-20T00:00:00Z", role="validation")


def test_per_file_bounds_design_pass_and_fail() -> None:
    ok = assert_per_file_bounds(
        [{"ts_min_utc": "2025-05-01T00:00:00Z", "ts_max_utc": "2025-12-31T23:59:59Z"}],
        role="design",
    )
    assert ok["result"] == "PROVEN_NO_DEAD_WINDOW_OVERLAP"
    with pytest.raises(NoOverlapError):
        assert_per_file_bounds(
            [{"ts_min_utc": "2025-05-01T00:00:00Z", "ts_max_utc": "2026-04-10T00:00:00Z"}],
            role="design",
        )


def test_per_file_missing_bounds_fails_closed() -> None:
    with pytest.raises(NoOverlapError):
        assert_per_file_bounds([{"ts_min_utc": "2025-05-01T00:00:00Z"}], role="design")


def test_feature_warmup_pre_forward_load_fails() -> None:
    policy = WarmupPolicy(w_bars=200, longest_feature_lookback_bars=200)
    policy.validate()
    # loading a dead-window / pre-forward timestamp must fail closed
    with pytest.raises(WarmupPolicyError):
        policy.assert_load_allowed("2026-04-20T00:00:00Z")
    # a forward-epoch timestamp is allowed
    policy.assert_load_allowed("2026-04-25T00:00:00Z")
