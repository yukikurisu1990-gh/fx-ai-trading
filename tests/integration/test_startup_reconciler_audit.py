"""Integration tests: StartupReconciler audit-trail wiring (Cycle 6.8 / I-06).

Verifies the optional ``reconciliation_repo`` parameter:

  - Each non-NO_OP action emits exactly one audit row with the right
    trigger_reason / action_taken / order_id / detail shape.
  - NO_OP actions emit nothing (terminal DB statuses).
  - Default constructor (no reconciliation_repo) writes nothing — strict
    backward compatibility with the M8 baseline.

The reconciler is exercised against an in-memory orders_repo stub; the
ReconciliationEventsRepository is replaced by a MagicMock so we can
assert call shape without touching a real DB.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from fx_ai_trading.supervisor.reconciler import (
    ReconcilerAction,
    StartupReconciler,
)


class _StubBroker:
    """Returns a fixed broker_status for every order_id."""

    def __init__(self, status: str) -> None:
        self._status = status

    def get_order(self, order_id: str) -> object:  # pragma: no cover - stub
        return None


def _make_reconciler(
    orders: list[dict],
    *,
    broker_status_per_order: dict[str, str | None] | None = None,
    with_audit: bool = True,
):
    orders_repo = MagicMock()
    orders_repo.list_open_orders.return_value = orders
    ctx = MagicMock()
    audit_repo = MagicMock() if with_audit else None
    reconciler = StartupReconciler(
        orders_repo=orders_repo,
        context=ctx,
        broker=_StubBroker("ignored") if broker_status_per_order else None,
        reconciliation_repo=audit_repo,
    )
    if broker_status_per_order is not None:
        # Patch the protected hook so we control broker_status per order_id
        # without needing a real broker adapter.
        reconciler._get_broker_status = lambda oid: broker_status_per_order.get(oid)  # type: ignore[assignment]
    return reconciler, orders_repo, audit_repo


class TestStartupReconcilerAuditWiring:
    def test_no_audit_when_repo_not_injected(self) -> None:
        orders = [{"order_id": "o1", "status": "PENDING"}]
        reconciler, orders_repo, audit_repo = _make_reconciler(orders, with_audit=False)
        outcome = reconciler.reconcile()
        # Action still applied (PENDING + no broker → MARK_FAILED).
        orders_repo.update_status.assert_called_once_with("o1", "FAILED", reconciler._context)
        assert outcome.failed == 1
        # No audit repo to assert on.
        assert audit_repo is None

    def test_no_op_terminal_state_writes_no_audit(self) -> None:
        orders = [
            {"order_id": "o-filled", "status": "FILLED"},
            {"order_id": "o-canceled", "status": "CANCELED"},
            {"order_id": "o-failed", "status": "FAILED"},
        ]
        reconciler, _, audit_repo = _make_reconciler(orders)
        outcome = reconciler.reconcile()
        assert outcome.no_ops == 3
        audit_repo.insert.assert_not_called()

    def test_mark_failed_emits_one_audit_row(self) -> None:
        orders = [{"order_id": "o-pf", "status": "PENDING"}]
        reconciler, _, audit_repo = _make_reconciler(orders)
        reconciler.reconcile()
        audit_repo.insert.assert_called_once()
        kwargs = audit_repo.insert.call_args.kwargs
        assert kwargs["trigger_reason"] == "startup"
        assert kwargs["action_taken"] == "MARK_FAILED"
        assert kwargs["order_id"] == "o-pf"
        assert kwargs["detail"] == {"db_status": "PENDING", "broker_status": None}

    def test_mark_filled_emits_audit_with_broker_status(self) -> None:
        orders = [{"order_id": "o-sf", "status": "SUBMITTED"}]
        reconciler, orders_repo, audit_repo = _make_reconciler(
            orders,
            broker_status_per_order={"o-sf": "filled"},
        )
        reconciler.reconcile()
        orders_repo.update_status.assert_called_once_with("o-sf", "FILLED", reconciler._context)
        kwargs = audit_repo.insert.call_args.kwargs
        assert kwargs["action_taken"] == "MARK_FILLED"
        assert kwargs["detail"]["broker_status"] == "filled"

    def test_audit_failure_does_not_break_reconcile(self) -> None:
        """Audit insert exception is logged but does not stop the loop or
        get added to outcome.errors (which is reserved for action-apply errors)."""
        orders = [{"order_id": "o-pf", "status": "PENDING"}]
        reconciler, orders_repo, audit_repo = _make_reconciler(orders)
        audit_repo.insert.side_effect = RuntimeError("audit table missing")
        outcome = reconciler.reconcile()
        # The action itself succeeded; only the audit insert blew up.
        orders_repo.update_status.assert_called_once_with("o-pf", "FAILED", reconciler._context)
        assert outcome.failed == 1
        assert outcome.errors == []


class TestActionLabelMapping:
    def test_action_taken_label_uses_uppercase_form(self) -> None:
        # Sanity that the label map uses the contract-required UPPERCASE
        # form (MARK_FAILED, not mark_failed) — guards against regression
        # in _ACTION_TAKEN_LABEL within reconciler.py.
        from fx_ai_trading.supervisor.reconciler import _ACTION_TAKEN_LABEL

        for action in (
            ReconcilerAction.MARK_SUBMITTED,
            ReconcilerAction.MARK_FILLED,
            ReconcilerAction.MARK_CANCELED,
            ReconcilerAction.MARK_FAILED,
        ):
            assert _ACTION_TAKEN_LABEL[action.value].isupper()
            assert _ACTION_TAKEN_LABEL[action.value].startswith("MARK_")
