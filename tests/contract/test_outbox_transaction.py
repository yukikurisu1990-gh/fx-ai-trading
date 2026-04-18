"""Contract tests: orders + outbox_events atomicity (D1 §6.6 / M8).

Invariant: orders(PENDING) and outbox_events(ORDER_SUBMIT_REQUEST) must be
committed in the same transaction.  If either INSERT fails, both are rolled back.

Tests use SQLite in-memory with only the tables needed (no full migration).
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, text

from fx_ai_trading.common.ulid import generate_ulid
from fx_ai_trading.config.common_keys_context import CommonKeysContext
from fx_ai_trading.repositories.orders import OrdersRepository
from fx_ai_trading.services.order_lifecycle import OrderLifecycleService

_CTX = CommonKeysContext(
    run_id="outbox-tx-test",
    environment="test",
    code_version="0.0.0",
    config_version="test-cfg",
)

_ACCOUNT_ID = "__outbox_tx_account__"
_INSTRUMENT = "__OUTBOX_TX_INSTR__"
_BROKER_ID = "__outbox_tx_broker__"


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
            text(
                "CREATE TABLE outbox_events ("
                "  outbox_event_id TEXT PRIMARY KEY,"
                "  order_id TEXT,"
                "  event_type TEXT NOT NULL,"
                "  status TEXT NOT NULL DEFAULT 'pending',"
                "  payload TEXT,"
                "  dispatch_attempts INTEGER NOT NULL DEFAULT 0,"
                "  last_attempted_at TEXT,"
                "  created_at TEXT DEFAULT CURRENT_TIMESTAMP"
                ")"
            )
        )
        conn.execute(
            text("INSERT INTO brokers VALUES (:id, :name)"),
            {"id": _BROKER_ID, "name": "Outbox Tx Broker"},
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
def service(engine):
    orders_repo = OrdersRepository(engine=engine)
    return OrderLifecycleService(engine=engine, orders_repo=orders_repo)


class TestOutboxAtomicity:
    def test_order_and_outbox_written_together(self, service, engine) -> None:
        """Both orders and outbox_events rows must exist after place_order_with_outbox."""
        order_id = generate_ulid()
        outbox_id = generate_ulid()

        service.place_order_with_outbox(
            order_id=order_id,
            outbox_event_id=outbox_id,
            account_id=_ACCOUNT_ID,
            instrument=_INSTRUMENT,
            account_type="demo",
            order_type="market",
            direction="buy",
            units="1000",
            context=_CTX,
        )

        with engine.connect() as conn:
            order_row = conn.execute(
                text("SELECT order_id, status FROM orders WHERE order_id = :id"),
                {"id": order_id},
            ).fetchone()
            outbox_row = conn.execute(
                text(
                    "SELECT outbox_event_id, order_id, status, event_type"
                    " FROM outbox_events WHERE outbox_event_id = :id"
                ),
                {"id": outbox_id},
            ).fetchone()

        assert order_row is not None, "orders row must exist"
        assert outbox_row is not None, "outbox_events row must exist"

    def test_order_initial_status_is_pending(self, service, engine) -> None:
        order_id = generate_ulid()
        outbox_id = generate_ulid()
        service.place_order_with_outbox(
            order_id=order_id,
            outbox_event_id=outbox_id,
            account_id=_ACCOUNT_ID,
            instrument=_INSTRUMENT,
            account_type="demo",
            order_type="market",
            direction="sell",
            units="500",
            context=_CTX,
        )
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT status FROM orders WHERE order_id = :id"), {"id": order_id}
            ).fetchone()
        assert row[0] == "PENDING"

    def test_outbox_initial_status_is_pending(self, service, engine) -> None:
        order_id = generate_ulid()
        outbox_id = generate_ulid()
        service.place_order_with_outbox(
            order_id=order_id,
            outbox_event_id=outbox_id,
            account_id=_ACCOUNT_ID,
            instrument=_INSTRUMENT,
            account_type="demo",
            order_type="market",
            direction="buy",
            units="1000",
            context=_CTX,
        )
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT status FROM outbox_events WHERE outbox_event_id = :id"),
                {"id": outbox_id},
            ).fetchone()
        assert row[0] == "pending"

    def test_outbox_event_type_is_submit_request(self, service, engine) -> None:
        order_id = generate_ulid()
        outbox_id = generate_ulid()
        service.place_order_with_outbox(
            order_id=order_id,
            outbox_event_id=outbox_id,
            account_id=_ACCOUNT_ID,
            instrument=_INSTRUMENT,
            account_type="demo",
            order_type="market",
            direction="buy",
            units="1000",
            context=_CTX,
        )
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT event_type FROM outbox_events WHERE outbox_event_id = :id"),
                {"id": outbox_id},
            ).fetchone()
        assert row[0] == "ORDER_SUBMIT_REQUEST"

    def test_outbox_references_order_id(self, service, engine) -> None:
        order_id = generate_ulid()
        outbox_id = generate_ulid()
        service.place_order_with_outbox(
            order_id=order_id,
            outbox_event_id=outbox_id,
            account_id=_ACCOUNT_ID,
            instrument=_INSTRUMENT,
            account_type="demo",
            order_type="market",
            direction="buy",
            units="1000",
            context=_CTX,
        )
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT order_id FROM outbox_events WHERE outbox_event_id = :id"),
                {"id": outbox_id},
            ).fetchone()
        assert row[0] == order_id

    def test_rollback_on_duplicate_order_id_leaves_no_outbox(self, service, engine) -> None:
        """If orders INSERT fails (duplicate PK), outbox_events must also be absent."""
        order_id = generate_ulid()
        outbox_id_first = generate_ulid()
        outbox_id_second = generate_ulid()

        # First write succeeds
        service.place_order_with_outbox(
            order_id=order_id,
            outbox_event_id=outbox_id_first,
            account_id=_ACCOUNT_ID,
            instrument=_INSTRUMENT,
            account_type="demo",
            order_type="market",
            direction="buy",
            units="1000",
            context=_CTX,
        )

        # Second write with same order_id must fail (duplicate PK)
        with pytest.raises(Exception):  # noqa: B017 — any DB integrity error
            service.place_order_with_outbox(
                order_id=order_id,  # duplicate!
                outbox_event_id=outbox_id_second,
                account_id=_ACCOUNT_ID,
                instrument=_INSTRUMENT,
                account_type="demo",
                order_type="market",
                direction="buy",
                units="1000",
                context=_CTX,
            )

        # The second outbox event must NOT exist (rolled back atomically)
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT outbox_event_id FROM outbox_events WHERE outbox_event_id = :id"),
                {"id": outbox_id_second},
            ).fetchone()
        assert row is None, "outbox event must not exist when order insert fails"


class TestOutboxPayload:
    def test_payload_stored_as_json(self, service, engine) -> None:
        order_id = generate_ulid()
        outbox_id = generate_ulid()
        payload = {"instrument": "EUR_USD", "signal_id": "sig001"}
        service.place_order_with_outbox(
            order_id=order_id,
            outbox_event_id=outbox_id,
            account_id=_ACCOUNT_ID,
            instrument=_INSTRUMENT,
            account_type="demo",
            order_type="market",
            direction="buy",
            units="1000",
            context=_CTX,
            payload=payload,
        )
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT payload FROM outbox_events WHERE outbox_event_id = :id"),
                {"id": outbox_id},
            ).fetchone()
        import json

        stored = json.loads(row[0])
        assert stored["instrument"] == "EUR_USD"
        assert stored["signal_id"] == "sig001"

    def test_none_payload_stored_as_null(self, service, engine) -> None:
        order_id = generate_ulid()
        outbox_id = generate_ulid()
        service.place_order_with_outbox(
            order_id=order_id,
            outbox_event_id=outbox_id,
            account_id=_ACCOUNT_ID,
            instrument=_INSTRUMENT,
            account_type="demo",
            order_type="market",
            direction="buy",
            units="1000",
            context=_CTX,
            payload=None,
        )
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT payload FROM outbox_events WHERE outbox_event_id = :id"),
                {"id": outbox_id},
            ).fetchone()
        assert row[0] is None
