"""Integration tests: MidRunReconciler audit + outbox_stale (Cycle 6.8 / I-06).

Covers:
  - Per-order audit row on non-NO_OP actions (with priority echoed in detail).
  - NO_OP terminal states write nothing.
  - Default constructor (no reconciliation_repo) is fully silent — strict
    backward compat with M15 baseline.
  - outbox_stale check: detection emits exactly one aggregated row.
  - outbox_stale disabled paths: ``outbox_stale_seconds=None`` and stale 0
    rows ⇒ no audit row.
  - trigger_reason validation rejects bad values.
  - Bucket switching is unaffected by the new wiring (regression guard).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest

from fx_ai_trading.supervisor.midrun_reconciler import MidRunReconciler


class _TrackingRateLimiter:
    def __init__(self, *, always_grant: bool = True) -> None:
        self.calls: list[str] = []
        self._always_grant = always_grant

    def acquire(self, bucket: str) -> bool:
        self.calls.append(bucket)
        return self._always_grant

    def available_tokens(self, bucket: str) -> float:
        return 10.0 if self._always_grant else 0.0


def _make(
    orders: list[dict] | None = None,
    *,
    with_audit: bool = True,
    trigger_reason: str = "midrun_heartbeat_gap",
    engine: object | None = None,
    outbox_stale_seconds: int | None = None,
):
    repo = MagicMock()
    repo.list_open_orders.return_value = orders or []
    ctx = MagicMock()
    audit_repo = MagicMock() if with_audit else None
    rl = _TrackingRateLimiter()
    reconciler = MidRunReconciler(
        orders_repo=repo,
        context=ctx,
        rate_limiter=rl,
        reconciliation_repo=audit_repo,
        trigger_reason=trigger_reason,
        engine=engine,
        outbox_stale_seconds=outbox_stale_seconds,
    )
    return reconciler, repo, audit_repo, rl


def _engine_returning_rows(rows: list[tuple]) -> MagicMock:
    """Return an Engine mock whose connection().execute().fetchall() yields *rows*."""
    engine = MagicMock()
    conn_cm = MagicMock()
    conn = MagicMock()
    conn.execute.return_value.fetchall.return_value = rows
    conn_cm.__enter__ = MagicMock(return_value=conn)
    conn_cm.__exit__ = MagicMock(return_value=False)
    engine.connect.return_value = conn_cm
    return engine


class TestAuditWiring:
    def test_no_audit_when_repo_not_injected(self) -> None:
        orders = [{"order_id": "o1", "status": "PENDING"}]
        reconciler, repo, audit_repo, _ = _make(orders, with_audit=False)
        outcome = reconciler.check()
        repo.update_status.assert_called_once_with("o1", "FAILED", reconciler._context)
        assert outcome.applied == 1
        assert audit_repo is None

    def test_no_op_terminal_writes_no_audit(self) -> None:
        orders = [{"order_id": "o-fil", "status": "FILLED"}]
        reconciler, _, audit_repo, _ = _make(orders)
        reconciler.check()
        audit_repo.insert.assert_not_called()

    def test_action_emits_audit_with_priority_in_detail(self) -> None:
        orders = [{"order_id": "o-p", "status": "PENDING"}]
        reconciler, _, audit_repo, _ = _make(orders)
        reconciler.check(priority="high")
        # exactly one call (no outbox_stale check fires; no engine).
        audit_repo.insert.assert_called_once()
        kwargs = audit_repo.insert.call_args.kwargs
        assert kwargs["trigger_reason"] == "midrun_heartbeat_gap"
        assert kwargs["action_taken"] == "MARK_FAILED"
        assert kwargs["order_id"] == "o-p"
        assert kwargs["detail"]["priority"] == "high"

    def test_periodic_drift_check_trigger_reason_propagates(self) -> None:
        orders = [{"order_id": "o-p", "status": "PENDING"}]
        reconciler, _, audit_repo, _ = _make(orders, trigger_reason="periodic_drift_check")
        reconciler.check()
        kwargs = audit_repo.insert.call_args.kwargs
        assert kwargs["trigger_reason"] == "periodic_drift_check"

    def test_invalid_trigger_reason_rejected(self) -> None:
        with pytest.raises(ValueError, match="trigger_reason must be one of"):
            MidRunReconciler(
                orders_repo=MagicMock(),
                context=MagicMock(),
                trigger_reason="startup",  # not allowed for MidRun
            )


class TestOutboxStaleCheck:
    def test_no_check_when_seconds_is_none(self) -> None:
        engine = _engine_returning_rows([])  # would matter if check ran
        reconciler, _, audit_repo, _ = _make(engine=engine, outbox_stale_seconds=None)
        reconciler.check()
        audit_repo.insert.assert_not_called()
        # connect() must not be called when feature disabled.
        engine.connect.assert_not_called()

    def test_no_audit_when_no_stale_rows(self) -> None:
        engine = _engine_returning_rows([])
        reconciler, _, audit_repo, _ = _make(engine=engine, outbox_stale_seconds=60)
        reconciler.check()
        engine.connect.assert_called()
        audit_repo.insert.assert_not_called()

    def test_stale_rows_emit_one_aggregated_audit_row(self) -> None:
        old = datetime(2026, 4, 21, 11, 0, 0, tzinfo=UTC)
        older = old - timedelta(minutes=5)
        rows = [
            ("risk_events", old),
            ("risk_events", older),
            ("order_transactions", old),
        ]
        engine = _engine_returning_rows(rows)
        reconciler, _, audit_repo, _ = _make(engine=engine, outbox_stale_seconds=60)
        reconciler.check()
        audit_repo.insert.assert_called_once()
        kwargs = audit_repo.insert.call_args.kwargs
        assert kwargs["trigger_reason"] == "outbox_stale"
        assert kwargs["action_taken"] == "outbox_stale_detected"
        # order_id is omitted entirely for outbox_stale rows (NULL in DB).
        assert kwargs.get("order_id") is None
        detail = kwargs["detail"]
        assert detail["count"] == 3
        assert detail["table_names"] == ["order_transactions", "risk_events"]
        assert detail["oldest_enqueued_at"] == older.isoformat()


class TestBackwardCompat:
    def test_default_constructor_has_no_audit_or_outbox(self) -> None:
        """Strict regression guard — the M15-style 4-arg construction must
        keep working with no audit-side effects."""
        from fx_ai_trading.supervisor.midrun_reconciler import MidRunReconciler

        repo = MagicMock()
        repo.list_open_orders.return_value = [
            {"order_id": "o", "status": "PENDING"},
        ]
        rl = _TrackingRateLimiter()
        # Original 4-arg signature still accepted.
        reconciler = MidRunReconciler(
            orders_repo=repo,
            context=MagicMock(),
            rate_limiter=rl,
            broker=None,
        )
        outcome = reconciler.check()
        assert outcome.applied == 1
        # Bucket selection still picks reconcile by default.
        assert rl.calls == ["reconcile"]
