"""Contract tests: RateLimiter 2-bucket independence and capacity (M15 / Ob-MIDRUN-1).

Verifies:
  1. RateLimiter exposes 'trading' and 'reconcile' buckets.
  2. Buckets are independent — exhausting one does not affect the other.
  3. 'reconcile' bucket capacity is 2 (rate_limit_reconcile_rps = 2, §6.2).
  4. 'trading' bucket capacity exceeds 'reconcile'.
  5. Tokens refill over time (fake clock).
  6. Unknown bucket name raises ValueError.
  7. acquire() returns bool (True/False — never raises on exhaustion).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from fx_ai_trading.common.rate_limiter import RateLimiter


class _StepClock:
    """Deterministic clock for token-bucket tests — manually advanced."""

    def __init__(self) -> None:
        self._dt = datetime(2026, 1, 1, tzinfo=UTC)

    def now(self) -> datetime:
        return self._dt

    def advance(self, seconds: float) -> None:
        self._dt += timedelta(seconds=seconds)


def _make_limiter() -> tuple[RateLimiter, _StepClock]:
    clock = _StepClock()
    limiter = RateLimiter(clock=clock)
    return limiter, clock


class TestBucketExistence:
    def test_acquire_trading_bucket_returns_bool(self) -> None:
        limiter, _ = _make_limiter()
        result = limiter.acquire("trading")
        assert isinstance(result, bool)

    def test_acquire_reconcile_bucket_returns_bool(self) -> None:
        limiter, _ = _make_limiter()
        result = limiter.acquire("reconcile")
        assert isinstance(result, bool)

    def test_fresh_trading_bucket_grants_first_acquire(self) -> None:
        limiter, _ = _make_limiter()
        assert limiter.acquire("trading") is True

    def test_fresh_reconcile_bucket_grants_first_acquire(self) -> None:
        limiter, _ = _make_limiter()
        assert limiter.acquire("reconcile") is True

    def test_unknown_bucket_raises_value_error(self) -> None:
        limiter, _ = _make_limiter()
        with pytest.raises(ValueError, match="Unknown RateLimiter bucket"):
            limiter.acquire("unknown")


class TestReconcileBucketCapacity:
    def test_reconcile_capacity_is_2(self) -> None:
        """Reconcile bucket allows exactly 2 tokens before exhaustion."""
        limiter, _ = _make_limiter()
        assert limiter.acquire("reconcile") is True
        assert limiter.acquire("reconcile") is True
        assert limiter.acquire("reconcile") is False

    def test_reconcile_available_tokens_starts_at_2(self) -> None:
        limiter, _ = _make_limiter()
        assert limiter.available_tokens("reconcile") == pytest.approx(2.0)

    def test_reconcile_tokens_decrease_on_acquire(self) -> None:
        limiter, _ = _make_limiter()
        limiter.acquire("reconcile")
        assert limiter.available_tokens("reconcile") == pytest.approx(1.0)


class TestTradingBucketCapacity:
    def test_trading_capacity_exceeds_reconcile(self) -> None:
        limiter, _ = _make_limiter()
        assert limiter.available_tokens("trading") > limiter.available_tokens("reconcile")

    def test_trading_bucket_allows_more_than_2_acquires(self) -> None:
        limiter, _ = _make_limiter()
        acquired = sum(1 for _ in range(5) if limiter.acquire("trading"))
        assert acquired > 2


class TestBucketIndependence:
    def test_exhausting_reconcile_does_not_affect_trading(self) -> None:
        limiter, _ = _make_limiter()
        while limiter.acquire("reconcile"):
            pass
        assert limiter.acquire("trading") is True

    def test_exhausting_trading_does_not_affect_reconcile(self) -> None:
        limiter, _ = _make_limiter()
        while limiter.acquire("trading"):
            pass
        assert limiter.acquire("reconcile") is True

    def test_reconcile_exhausted_trading_still_full(self) -> None:
        limiter, _ = _make_limiter()
        limiter.acquire("reconcile")
        limiter.acquire("reconcile")
        assert limiter.available_tokens("reconcile") == pytest.approx(0.0)
        assert limiter.available_tokens("trading") > 0.0


class TestTokenRefill:
    def test_reconcile_refills_after_1_second(self) -> None:
        limiter, clock = _make_limiter()
        limiter.acquire("reconcile")
        limiter.acquire("reconcile")
        assert limiter.acquire("reconcile") is False
        clock.advance(1.0)
        assert limiter.acquire("reconcile") is True

    def test_trading_refills_after_1_second(self) -> None:
        limiter, clock = _make_limiter()
        while limiter.acquire("trading"):
            pass
        clock.advance(1.0)
        assert limiter.acquire("trading") is True
