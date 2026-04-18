"""Contract tests: StartupReconciler action matrix (D4 §2.1 / M8).

Verifies the classify() pure function for all 11 action matrix cases:

  DB_Status   | Broker_Status | Expected Action
  ------------|---------------|----------------
  PENDING     | not_found     | MARK_FAILED
  PENDING     | open          | MARK_SUBMITTED
  PENDING     | pending       | MARK_SUBMITTED
  PENDING     | filled        | MARK_FAILED   (edge: skipped SUBMITTED)
  PENDING     | canceled      | MARK_CANCELED
  PENDING     | failed        | MARK_FAILED
  SUBMITTED   | not_found     | MARK_FAILED   (orphaned)
  SUBMITTED   | open          | NO_OP
  SUBMITTED   | filled        | MARK_FILLED
  SUBMITTED   | canceled      | MARK_CANCELED
  SUBMITTED   | failed        | MARK_FAILED
  FILLED      | (any)         | NO_OP         (terminal)
  CANCELED    | (any)         | NO_OP         (terminal)
  FAILED      | (any)         | NO_OP         (terminal)
"""

from __future__ import annotations

import pytest

from fx_ai_trading.supervisor.reconciler import ReconcilerAction, StartupReconciler


class TestActionMatrixPendingOrders:
    def test_pending_broker_not_found_mark_failed(self) -> None:
        assert StartupReconciler.classify("PENDING", None) == ReconcilerAction.MARK_FAILED

    def test_pending_broker_not_found_string_mark_failed(self) -> None:
        assert StartupReconciler.classify("PENDING", "not_found") == ReconcilerAction.MARK_FAILED

    def test_pending_broker_open_mark_submitted(self) -> None:
        assert StartupReconciler.classify("PENDING", "open") == ReconcilerAction.MARK_SUBMITTED

    def test_pending_broker_pending_mark_submitted(self) -> None:
        assert StartupReconciler.classify("PENDING", "pending") == ReconcilerAction.MARK_SUBMITTED

    def test_pending_broker_filled_mark_failed(self) -> None:
        """PENDING→FILLED skips SUBMITTED — cannot do two-step in one pass. Mark FAILED."""
        assert StartupReconciler.classify("PENDING", "filled") == ReconcilerAction.MARK_FAILED

    def test_pending_broker_canceled_mark_canceled(self) -> None:
        assert StartupReconciler.classify("PENDING", "canceled") == ReconcilerAction.MARK_CANCELED

    def test_pending_broker_failed_mark_failed(self) -> None:
        assert StartupReconciler.classify("PENDING", "failed") == ReconcilerAction.MARK_FAILED


class TestActionMatrixSubmittedOrders:
    def test_submitted_broker_not_found_mark_failed(self) -> None:
        """Orphaned SUBMITTED order — broker has no record. Mark FAILED."""
        assert StartupReconciler.classify("SUBMITTED", None) == ReconcilerAction.MARK_FAILED

    def test_submitted_broker_open_no_op(self) -> None:
        """Normal in-flight order. No action needed."""
        assert StartupReconciler.classify("SUBMITTED", "open") == ReconcilerAction.NO_OP

    def test_submitted_broker_filled_mark_filled(self) -> None:
        assert StartupReconciler.classify("SUBMITTED", "filled") == ReconcilerAction.MARK_FILLED

    def test_submitted_broker_canceled_mark_canceled(self) -> None:
        assert StartupReconciler.classify("SUBMITTED", "canceled") == ReconcilerAction.MARK_CANCELED

    def test_submitted_broker_failed_mark_failed(self) -> None:
        assert StartupReconciler.classify("SUBMITTED", "failed") == ReconcilerAction.MARK_FAILED


class TestActionMatrixTerminalOrders:
    @pytest.mark.parametrize("broker_status", [None, "open", "filled", "canceled", "not_found"])
    def test_filled_is_always_no_op(self, broker_status) -> None:
        assert StartupReconciler.classify("FILLED", broker_status) == ReconcilerAction.NO_OP

    @pytest.mark.parametrize("broker_status", [None, "open", "filled", "canceled", "not_found"])
    def test_canceled_is_always_no_op(self, broker_status) -> None:
        assert StartupReconciler.classify("CANCELED", broker_status) == ReconcilerAction.NO_OP

    @pytest.mark.parametrize("broker_status", [None, "open", "filled", "canceled", "not_found"])
    def test_failed_is_always_no_op(self, broker_status) -> None:
        assert StartupReconciler.classify("FAILED", broker_status) == ReconcilerAction.NO_OP


class TestActionMatrixAllCases:
    def test_all_11_explicit_cases(self) -> None:
        """Exhaustive check of all 11 specified action matrix cases."""
        matrix = [
            ("PENDING", None, ReconcilerAction.MARK_FAILED),
            ("PENDING", "open", ReconcilerAction.MARK_SUBMITTED),
            ("PENDING", "pending", ReconcilerAction.MARK_SUBMITTED),
            ("PENDING", "filled", ReconcilerAction.MARK_FAILED),
            ("PENDING", "canceled", ReconcilerAction.MARK_CANCELED),
            ("PENDING", "failed", ReconcilerAction.MARK_FAILED),
            ("SUBMITTED", None, ReconcilerAction.MARK_FAILED),
            ("SUBMITTED", "open", ReconcilerAction.NO_OP),
            ("SUBMITTED", "filled", ReconcilerAction.MARK_FILLED),
            ("SUBMITTED", "canceled", ReconcilerAction.MARK_CANCELED),
            ("SUBMITTED", "failed", ReconcilerAction.MARK_FAILED),
        ]
        for db_status, broker_status, expected in matrix:
            result = StartupReconciler.classify(db_status, broker_status)
            assert result == expected, (
                f"classify({db_status!r}, {broker_status!r}) = {result} but expected {expected}"
            )


class TestReconcilerStructural:
    def test_classify_is_callable(self) -> None:
        assert callable(getattr(StartupReconciler, "classify", None))

    def test_reconcile_is_callable(self) -> None:
        assert callable(getattr(StartupReconciler, "reconcile", None))

    def test_reconciler_action_enum_has_required_values(self) -> None:
        required = {"no_op", "mark_submitted", "mark_filled", "mark_canceled", "mark_failed"}
        actual = {a.value for a in ReconcilerAction}
        assert required == actual
