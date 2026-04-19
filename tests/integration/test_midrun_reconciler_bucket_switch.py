"""Integration tests: MidRunReconciler bucket switching (M15 / Ob-MIDRUN-1).

Verifies:
  1. Normal priority uses 'reconcile' bucket.
  2. High priority uses 'trading' bucket.
  3. No-op when no open orders.
  4. Rate-limited orders are skipped (not crashed).
  5. Actions applied correctly using StartupReconciler classify().
  6. outcome.examined / applied / skipped_by_rate_limit counts are correct.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from fx_ai_trading.supervisor.midrun_reconciler import MidRunOutcome, MidRunReconciler


class _TrackingRateLimiter:
    """RateLimiter substitute that records which buckets were acquired."""

    def __init__(self, *, always_grant: bool = True) -> None:
        self.calls: list[str] = []
        self._always_grant = always_grant

    def acquire(self, bucket: str) -> bool:
        self.calls.append(bucket)
        return self._always_grant

    def available_tokens(self, bucket: str) -> float:
        return 10.0 if self._always_grant else 0.0


def _make_reconciler(
    orders: list[dict] | None = None,
    *,
    always_grant: bool = True,
) -> tuple[MidRunReconciler, _TrackingRateLimiter, MagicMock]:
    tracker = _TrackingRateLimiter(always_grant=always_grant)
    repo = MagicMock()
    repo.list_open_orders.return_value = orders or []
    ctx = MagicMock()
    reconciler = MidRunReconciler(orders_repo=repo, context=ctx, rate_limiter=tracker)
    return reconciler, tracker, repo


class TestBucketSelection:
    def test_normal_priority_uses_reconcile_bucket(self) -> None:
        orders = [{"order_id": "o1", "status": "SUBMITTED"}]
        reconciler, tracker, _ = _make_reconciler(orders=orders)
        reconciler.check(priority="normal")
        assert all(b == "reconcile" for b in tracker.calls)

    def test_high_priority_uses_trading_bucket(self) -> None:
        orders = [{"order_id": "o1", "status": "SUBMITTED"}]
        reconciler, tracker, _ = _make_reconciler(orders=orders)
        reconciler.check(priority="high")
        assert all(b == "trading" for b in tracker.calls)

    def test_default_priority_is_normal(self) -> None:
        orders = [{"order_id": "o1", "status": "SUBMITTED"}]
        reconciler, tracker, _ = _make_reconciler(orders=orders)
        reconciler.check()
        assert all(b == "reconcile" for b in tracker.calls)

    def test_acquire_called_once_per_order(self) -> None:
        orders = [
            {"order_id": "o1", "status": "SUBMITTED"},
            {"order_id": "o2", "status": "SUBMITTED"},
        ]
        reconciler, tracker, _ = _make_reconciler(orders=orders)
        reconciler.check()
        assert len(tracker.calls) == 2


class TestOutcomeCounts:
    def test_no_open_orders_returns_zero_examined(self) -> None:
        reconciler, _, _ = _make_reconciler(orders=[])
        outcome = reconciler.check()
        assert outcome.examined == 0
        assert outcome.applied == 0
        assert outcome.skipped_by_rate_limit == 0

    def test_submitted_open_broker_is_no_op(self) -> None:
        """SUBMITTED + broker=None(not_found) → MARK_FAILED."""
        orders = [{"order_id": "o1", "status": "SUBMITTED"}]
        reconciler, _, repo = _make_reconciler(orders=orders)
        outcome = reconciler.check()
        assert outcome.examined == 1
        assert outcome.applied == 1
        repo.update_status.assert_called_once_with("o1", "FAILED", reconciler._context)

    def test_pending_broker_none_marks_failed(self) -> None:
        orders = [{"order_id": "o2", "status": "PENDING"}]
        reconciler, _, repo = _make_reconciler(orders=orders)
        outcome = reconciler.check()
        assert outcome.applied == 1
        repo.update_status.assert_called_once_with("o2", "FAILED", reconciler._context)

    def test_rate_limited_orders_counted_as_skipped(self) -> None:
        orders = [
            {"order_id": "o1", "status": "SUBMITTED"},
            {"order_id": "o2", "status": "SUBMITTED"},
        ]
        reconciler, _, _ = _make_reconciler(orders=orders, always_grant=False)
        outcome = reconciler.check()
        assert outcome.examined == 2
        assert outcome.skipped_by_rate_limit == 2
        assert outcome.applied == 0

    def test_order_ids_filter_applied(self) -> None:
        orders = [
            {"order_id": "o1", "status": "PENDING"},
            {"order_id": "o2", "status": "PENDING"},
        ]
        reconciler, _, repo = _make_reconciler(orders=orders)
        outcome = reconciler.check(order_ids=["o1"])
        assert outcome.examined == 1

    def test_errors_appended_on_repo_exception(self) -> None:
        orders = [{"order_id": "o1", "status": "PENDING"}]
        reconciler, _, repo = _make_reconciler(orders=orders)
        repo.update_status.side_effect = RuntimeError("db down")
        outcome = reconciler.check()
        assert len(outcome.errors) == 1
        assert "o1" in outcome.errors[0]


class TestReturnType:
    def test_check_returns_midrun_outcome(self) -> None:
        reconciler, _, _ = _make_reconciler()
        result = reconciler.check()
        assert isinstance(result, MidRunOutcome)
