"""Unit tests for RetryPolicy / compute_next_attempt_at (Cycle 6.2).

Backoff formula (this cycle, no jitter):
    next = now + min(base_delay * 2**(attempt_count - 1), max_delay)

attempt_count is the post-failure count, so attempt_count=1 yields
exactly base_delay (not 2 * base_delay).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from fx_ai_trading.sync.service import RetryPolicy, compute_next_attempt_at

_NOW = datetime(2026, 4, 20, 12, 0, 0, tzinfo=UTC)


def _policy(base_s: int, max_s: int) -> RetryPolicy:
    return RetryPolicy(
        base_delay=timedelta(seconds=base_s),
        max_delay=timedelta(seconds=max_s),
    )


class TestProgression:
    def test_attempt_one_equals_base(self) -> None:
        p = _policy(30, 1800)
        got = compute_next_attempt_at(now=_NOW, attempt_count=1, policy=p)
        assert got - _NOW == timedelta(seconds=30)

    def test_attempt_two_doubles(self) -> None:
        p = _policy(30, 1800)
        got = compute_next_attempt_at(now=_NOW, attempt_count=2, policy=p)
        assert got - _NOW == timedelta(seconds=60)

    def test_attempt_three_quadruples(self) -> None:
        p = _policy(30, 1800)
        got = compute_next_attempt_at(now=_NOW, attempt_count=3, policy=p)
        assert got - _NOW == timedelta(seconds=120)


class TestCap:
    def test_caps_at_max_delay(self) -> None:
        p = _policy(30, 60)
        # attempt 3 would be 120s uncapped -> cap at 60s
        got = compute_next_attempt_at(now=_NOW, attempt_count=3, policy=p)
        assert got - _NOW == timedelta(seconds=60)

    def test_very_large_attempt_is_capped_without_overflow(self) -> None:
        """Backoff must not OverflowError on pathological attempt counts."""
        p = _policy(30, 1800)
        got = compute_next_attempt_at(now=_NOW, attempt_count=10_000, policy=p)
        # Must land at or below max_delay, not raise.
        assert got - _NOW == timedelta(seconds=1800)


class TestInvalidInput:
    def test_zero_attempt_count_raises(self) -> None:
        p = _policy(30, 1800)
        with pytest.raises(ValueError, match="attempt_count must be >= 1"):
            compute_next_attempt_at(now=_NOW, attempt_count=0, policy=p)

    def test_negative_attempt_count_raises(self) -> None:
        p = _policy(30, 1800)
        with pytest.raises(ValueError, match="attempt_count must be >= 1"):
            compute_next_attempt_at(now=_NOW, attempt_count=-1, policy=p)


class TestDefaults:
    def test_default_policy_uses_30s_and_30min(self) -> None:
        p = RetryPolicy()
        assert p.base_delay == timedelta(seconds=30)
        assert p.max_delay == timedelta(minutes=30)

    def test_default_first_retry_is_30s(self) -> None:
        got = compute_next_attempt_at(now=_NOW, attempt_count=1, policy=RetryPolicy())
        assert got - _NOW == timedelta(seconds=30)
