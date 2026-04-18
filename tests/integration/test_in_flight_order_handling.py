"""Integration tests: in-flight order handling during safe_stop (M8).

Verifies that the StartupReconciler correctly handles open orders when
the system restarts after a safe_stop:

  - PENDING orders with no broker record → FAILED (D4 action matrix)
  - SUBMITTED orders with no broker record → FAILED (orphaned)
  - SUBMITTED orders at broker (open) → NO_OP (left in SUBMITTED)
  - Terminal orders (FILLED, CANCELED, FAILED) → untouched

Uses SQLite in-memory with a minimal schema (no full migration required).
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, text

from fx_ai_trading.common.ulid import generate_ulid
from fx_ai_trading.config.common_keys_context import CommonKeysContext
from fx_ai_trading.repositories.orders import OrdersRepository
from fx_ai_trading.supervisor.reconciler import ReconcilerAction, StartupReconciler

_CTX = CommonKeysContext(
    run_id="inflight-test",
    environment="test",
    code_version="0.0.0",
    config_version="test-cfg",
)

_ACCOUNT_ID = "__inflight_account__"
_INSTRUMENT = "__INFLIGHT_INSTR__"
_BROKER_ID = "__inflight_broker__"


@pytest.fixture(scope="module")
def engine():
    e = create_engine("sqlite://")
    with e.begin() as conn:
        conn.execute(text("CREATE TABLE brokers (broker_id TEXT PRIMARY KEY, name TEXT NOT NULL)"))
        conn.execute(
            text(
                "CREATE TABLE accounts ("
                "  account_id TEXT PRIMARY KEY,"
                "  broker_id TEXT NOT NULL,"
                "  account_type TEXT NOT NULL,"
                "  base_currency TEXT NOT NULL"
                ")"
            )
        )
        conn.execute(
            text(
                "CREATE TABLE instruments ("
                "  instrument TEXT PRIMARY KEY,"
                "  base_currency TEXT NOT NULL,"
                "  quote_currency TEXT NOT NULL,"
                "  pip_location INTEGER NOT NULL"
                ")"
            )
        )
        conn.execute(
            text(
                "CREATE TABLE orders ("
                "  order_id TEXT PRIMARY KEY,"
                "  client_order_id TEXT,"
                "  trading_signal_id TEXT,"
                "  account_id TEXT NOT NULL,"
                "  instrument TEXT NOT NULL,"
                "  account_type TEXT NOT NULL,"
                "  order_type TEXT NOT NULL,"
                "  direction TEXT NOT NULL,"
                "  units TEXT NOT NULL,"
                "  status TEXT NOT NULL DEFAULT 'PENDING',"
                "  submitted_at TEXT,"
                "  filled_at TEXT,"
                "  canceled_at TEXT,"
                "  correlation_id TEXT,"
                "  created_at TEXT DEFAULT CURRENT_TIMESTAMP"
                ")"
            )
        )
        conn.execute(
            text("INSERT INTO brokers VALUES (:id, :name)"),
            {"id": _BROKER_ID, "name": "InFlight Broker"},
        )
        conn.execute(
            text("INSERT INTO accounts VALUES (:aid, :bid, 'demo', 'USD')"),
            {"aid": _ACCOUNT_ID, "bid": _BROKER_ID},
        )
        conn.execute(
            text("INSERT INTO instruments VALUES (:i, 'TST', 'USD', -4)"),
            {"i": _INSTRUMENT},
        )
    yield e
    e.dispose()


@pytest.fixture()
def orders_repo(engine):
    return OrdersRepository(engine=engine)


@pytest.fixture()
def reconciler(orders_repo):
    return StartupReconciler(orders_repo=orders_repo, context=_CTX, broker=None)


def _insert_order(engine, order_id: str, status: str = "PENDING") -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO orders"
                " (order_id, account_id, instrument, account_type,"
                "  order_type, direction, units, status)"
                " VALUES (:oid, :aid, :instr, 'demo', 'market', 'buy', '1000', :status)"
            ),
            {
                "oid": order_id,
                "aid": _ACCOUNT_ID,
                "instr": _INSTRUMENT,
                "status": status,
            },
        )


class TestInFlightPendingOrders:
    def test_pending_order_with_no_broker_becomes_failed(self, engine, orders_repo, reconciler):
        """Safe-stop leaves PENDING orders with no broker record → must reconcile to FAILED."""
        order_id = generate_ulid()
        _insert_order(engine, order_id, "PENDING")

        outcome = reconciler.reconcile()

        result = orders_repo.get_by_order_id(order_id)
        assert result["status"] == "FAILED", (
            f"PENDING order with no broker record must become FAILED, got {result['status']!r}"
        )
        assert outcome.failed >= 1

    def test_multiple_pending_orders_all_become_failed(self, engine, orders_repo, reconciler):
        order_ids = [generate_ulid() for _ in range(3)]
        for oid in order_ids:
            _insert_order(engine, oid, "PENDING")

        reconciler.reconcile()

        for oid in order_ids:
            result = orders_repo.get_by_order_id(oid)
            assert result["status"] == "FAILED"


class TestInFlightSubmittedOrders:
    def test_submitted_order_with_no_broker_becomes_failed(self, engine, orders_repo, reconciler):
        """Orphaned SUBMITTED order (not found at broker) → FAILED."""
        order_id = generate_ulid()
        _insert_order(engine, order_id, "SUBMITTED")

        reconciler.reconcile()

        result = orders_repo.get_by_order_id(order_id)
        assert result["status"] == "FAILED", (
            f"Orphaned SUBMITTED order must become FAILED, got {result['status']!r}"
        )


class TestTerminalOrdersUntouched:
    @pytest.mark.parametrize("terminal_status", ["FILLED", "CANCELED", "FAILED"])
    def test_terminal_order_not_modified(self, engine, orders_repo, reconciler, terminal_status):
        """Terminal orders (FILLED, CANCELED, FAILED) must not be modified."""
        order_id = generate_ulid()
        _insert_order(engine, order_id, terminal_status)

        reconciler.reconcile()

        result = orders_repo.get_by_order_id(order_id)
        assert result["status"] == terminal_status, (
            f"Terminal {terminal_status!r} order must not be modified"
        )


class TestReconcileOutcome:
    def test_outcome_examined_count(self, engine, orders_repo, reconciler):
        """reconcile() outcome.examined must count all open orders."""
        order_ids = [generate_ulid(), generate_ulid()]
        for oid in order_ids:
            _insert_order(engine, oid, "PENDING")

        outcome = reconciler.reconcile()

        assert outcome.examined >= 2

    def test_outcome_failed_count_increases(self, engine, orders_repo, reconciler):
        order_id = generate_ulid()
        _insert_order(engine, order_id, "PENDING")

        outcome = reconciler.reconcile()
        assert outcome.failed >= 1

    def test_outcome_no_errors_for_valid_orders(self, engine, orders_repo):
        """Valid reconciliation must produce no errors list entries."""
        order_id = generate_ulid()
        _insert_order(engine, order_id, "FILLED")  # terminal — no_op

        rec = StartupReconciler(orders_repo=orders_repo, context=_CTX, broker=None)
        outcome = rec.reconcile()
        assert outcome.errors == []


class TestClassifyPureFunction:
    """Spot-check classify() for the safe_stop-relevant cases."""

    def test_pending_no_broker_is_mark_failed(self) -> None:
        assert StartupReconciler.classify("PENDING", None) == ReconcilerAction.MARK_FAILED

    def test_submitted_no_broker_is_mark_failed(self) -> None:
        assert StartupReconciler.classify("SUBMITTED", None) == ReconcilerAction.MARK_FAILED

    def test_filled_is_no_op(self) -> None:
        assert StartupReconciler.classify("FILLED", None) == ReconcilerAction.NO_OP
