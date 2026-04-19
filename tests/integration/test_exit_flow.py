"""Integration test: ExitPolicy → ExitExecutor → close_events end-to-end (M14).

Requires DATABASE_URL (from .env or env var). Auto-skipped when unset.

Flow:
  1. Insert fixture broker / account / instrument / order rows.
  2. ExitPolicyService evaluates: TP hit → should_exit=True.
  3. ExitExecutor.execute() calls MockBroker + CloseEventsRepository.insert().
  4. Verify close_events row was written with correct data.
  5. Clean up fixture rows.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

import pytest
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from fx_ai_trading.config.common_keys_context import CommonKeysContext

load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)

_DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()

pytestmark = pytest.mark.skipif(
    not _DATABASE_URL, reason="DATABASE_URL not set — skipping integration tests"
)

_BROKER_ID = "__test_broker_exit__"
_ACCOUNT_ID = "__test_account_exit__"
_INSTRUMENT = "__TEST_EUR_EXIT__"
_ORDER_ID = "__test_entry_ord_exit__"
_FIXED_AT = datetime(2026, 1, 1, tzinfo=UTC)

_CTX = CommonKeysContext(
    run_id="exit-integ-run",
    environment="test",
    code_version="0.0.0",
    config_version="test-exit-cfg",
)


@pytest.fixture(scope="module")
def engine():
    e = create_engine(_DATABASE_URL)
    yield e
    e.dispose()


@pytest.fixture(scope="module", autouse=True)
def db_fixture(engine):
    """Insert prerequisite rows and clean up after the module."""
    from fx_ai_trading.repositories.orders import OrdersRepository

    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO brokers (broker_id, name)"
                " VALUES (:bid, 'test-exit-broker') ON CONFLICT DO NOTHING"
            ),
            {"bid": _BROKER_ID},
        )
        conn.execute(
            text(
                "INSERT INTO accounts (account_id, broker_id, account_type, base_currency)"
                " VALUES (:aid, :bid, 'demo', 'USD') ON CONFLICT DO NOTHING"
            ),
            {"aid": _ACCOUNT_ID, "bid": _BROKER_ID},
        )
        conn.execute(
            text(
                "INSERT INTO instruments (instrument, base_currency, quote_currency, pip_location)"
                " VALUES (:inst, 'EUR', 'USD', -4) ON CONFLICT DO NOTHING"
            ),
            {"inst": _INSTRUMENT},
        )

    orders_repo = OrdersRepository(engine)
    orders_repo.create_order(
        order_id=_ORDER_ID,
        account_id=_ACCOUNT_ID,
        instrument=_INSTRUMENT,
        account_type="demo",
        order_type="market",
        direction="buy",
        units="1000",
        context=_CTX,
    )

    yield

    with engine.begin() as conn:
        conn.execute(text("DELETE FROM close_events WHERE order_id = :oid"), {"oid": _ORDER_ID})
        conn.execute(text("DELETE FROM orders WHERE order_id = :oid"), {"oid": _ORDER_ID})
        conn.execute(text("DELETE FROM accounts WHERE account_id = :aid"), {"aid": _ACCOUNT_ID})
        conn.execute(
            text("DELETE FROM instruments WHERE instrument = :inst"), {"inst": _INSTRUMENT}
        )
        conn.execute(text("DELETE FROM brokers WHERE broker_id = :bid"), {"bid": _BROKER_ID})


class TestExitFlowEndToEnd:
    def test_tp_hit_writes_close_event(self, engine) -> None:
        from fx_ai_trading.adapters.broker.mock import MockBroker
        from fx_ai_trading.repositories.close_events import CloseEventsRepository
        from fx_ai_trading.services.exit_executor import ExitExecutor
        from fx_ai_trading.services.exit_policy import ExitPolicyService

        svc = ExitPolicyService()
        decision = svc.evaluate(
            position_id="pos-exit-flow-1",
            instrument=_INSTRUMENT,
            side="long",
            current_price=1.1100,
            tp=1.1100,
            sl=1.0900,
            holding_seconds=100,
            context={},
        )
        assert decision.should_exit is True
        assert "tp" in decision.reasons

        broker = MockBroker(account_type="demo", fill_price=1.1100)
        repo = CloseEventsRepository(engine=engine)
        executor = ExitExecutor(broker=broker, close_events_repo=repo)
        result = executor.execute(
            decision=decision,
            account_id=_ACCOUNT_ID,
            instrument=_INSTRUMENT,
            side="long",
            size_units=1000,
            entry_order_id=_ORDER_ID,
            occurred_at=_FIXED_AT,
        )
        assert result is not None
        assert result.status == "filled"

        rows = repo.get_recent(limit=10)
        matching = [r for r in rows if r["order_id"] == _ORDER_ID]
        assert len(matching) >= 1
        row = matching[0]
        assert row["primary_reason_code"] == "tp"
        reason_codes = {r["reason_code"] for r in row["reasons"]}
        assert "tp" in reason_codes

    def test_no_exit_writes_no_close_event(self, engine) -> None:
        from fx_ai_trading.adapters.broker.mock import MockBroker
        from fx_ai_trading.repositories.close_events import CloseEventsRepository
        from fx_ai_trading.services.exit_executor import ExitExecutor
        from fx_ai_trading.services.exit_policy import ExitPolicyService

        svc = ExitPolicyService()
        decision = svc.evaluate(
            position_id="pos-exit-flow-2",
            instrument=_INSTRUMENT,
            side="long",
            current_price=1.1050,
            tp=1.1100,
            sl=1.0900,
            holding_seconds=100,
            context={},
        )
        assert decision.should_exit is False

        broker = MockBroker(account_type="demo")
        repo = CloseEventsRepository(engine=engine)
        executor = ExitExecutor(broker=broker, close_events_repo=repo)
        result = executor.execute(
            decision=decision,
            account_id=_ACCOUNT_ID,
            instrument=_INSTRUMENT,
            side="long",
            size_units=1000,
            entry_order_id=_ORDER_ID,
            occurred_at=_FIXED_AT,
        )
        assert result is None
        assert len(broker._placed_orders) == 0
