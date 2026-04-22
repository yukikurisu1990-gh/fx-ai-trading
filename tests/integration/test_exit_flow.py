"""Integration test: ExitPolicy → run_exit_gate → close_events end-to-end (M14).

Migrated from the deprecated ``ExitExecutor`` path to ``run_exit_gate``
in M9/H-3a so the end-to-end exit flow is exercised on the post-Cycle-6.7d
(I-09) write path that delegates DB writes to ``StateManager.on_close``.
``ExitExecutor`` itself is intentionally left in tree until the rest of
H-3 finishes; this file no longer imports it.

Requires DATABASE_URL (from .env or env var). Auto-skipped when unset.

Flow:
  1. Module fixture inserts broker / account / instrument rows.
  2. Each test seeds its own (orders row + positions(open) row) so that
     ``state_manager.open_position_details()`` returns the test's
     position.  Per-test seeding (instead of one shared order) keeps the
     two tests independent — the TP-hit test would otherwise leave the
     position closed and starve the no-exit test.
  3. ``run_exit_gate`` is invoked with a real ``ExitPolicyService`` and a
     ``MockBroker`` so the *whole* policy → broker → state-manager →
     close_events / positions(close) / outbox chain is exercised.
  4. Verify the outcome list AND that close_events reflects the result.

Surface mapping vs the deprecated ``ExitExecutor`` test
───────────────────────────────────────────────────────
  ExitExecutor.execute(...)             → run_exit_gate(...)
  CloseEventsRepository.insert(...)     → StateManager.on_close(...)
  result.status == 'filled'             → outcome == 'closed'
  result is None                        → outcome == 'noop'
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from fx_ai_trading.common.clock import FixedClock
from fx_ai_trading.common.ulid import generate_ulid
from fx_ai_trading.config.common_keys_context import CommonKeysContext

load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)

_DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()

pytestmark = pytest.mark.skipif(
    not _DATABASE_URL, reason="DATABASE_URL not set — skipping integration tests"
)

_BROKER_ID = "__test_broker_exit__"
_ACCOUNT_ID = "__test_account_exit__"
_INSTRUMENT = "__TEST_EUR_EXIT__"
_FIXED_AT = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
_OPEN_AT = datetime(2026, 1, 1, 11, 0, 0, tzinfo=UTC)

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
def db_fixture(engine) -> Iterator[None]:
    """Insert prerequisite broker / account / instrument rows.

    Per-test order + position rows are seeded inside each test so the
    two tests stay independent.  Module-scoped teardown also sweeps any
    positions / close_events / outbox rows the tests left behind, so a
    crash inside a test still cleans up by the end of the module.
    """
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

    yield

    with engine.begin() as conn:
        # Outbox rows enqueued by StateManager.on_close (positions /
        # close_events table_names).  Scope by account_id substring in
        # the JSON payload — every payload includes account_id.  The
        # payload column is ``json`` in Postgres so we cast to text for
        # LIKE; sqlite stores it as TEXT and the cast is a no-op there.
        conn.execute(
            text(
                "DELETE FROM secondary_sync_outbox"
                " WHERE table_name IN ('positions', 'close_events')"
                "   AND payload_json::text LIKE :acct_like"
            ),
            {"acct_like": f"%{_ACCOUNT_ID}%"},
        )
        conn.execute(
            text("DELETE FROM close_events WHERE order_id LIKE :oid_like"),
            {"oid_like": "__test_entry_ord_exit_%"},
        )
        conn.execute(
            text("DELETE FROM positions WHERE account_id = :aid"),
            {"aid": _ACCOUNT_ID},
        )
        conn.execute(text("DELETE FROM orders WHERE account_id = :aid"), {"aid": _ACCOUNT_ID})
        conn.execute(text("DELETE FROM accounts WHERE account_id = :aid"), {"aid": _ACCOUNT_ID})
        conn.execute(
            text("DELETE FROM instruments WHERE instrument = :inst"), {"inst": _INSTRUMENT}
        )
        conn.execute(text("DELETE FROM brokers WHERE broker_id = :bid"), {"bid": _BROKER_ID})


def _seed_open_position(engine, *, order_id: str) -> None:
    """Create the orders row + positions(open) row this test will close.

    StateManager.open_position_details() requires a positions row with
    event_type='open' (and no matching 'close' for the same order_id).
    The test_exit_flow.py predecessor wrote only the orders row because
    ExitExecutor took position metadata as call arguments; run_exit_gate
    instead reads it from StateManager, so the position must exist in
    the DB.
    """
    from fx_ai_trading.repositories.orders import OrdersRepository

    OrdersRepository(engine).create_order(
        order_id=order_id,
        account_id=_ACCOUNT_ID,
        instrument=_INSTRUMENT,
        account_type="demo",
        order_type="market",
        direction="buy",
        units="1000",
        context=_CTX,
    )

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO positions (
                    position_snapshot_id, order_id, account_id, instrument,
                    event_type, units, avg_price, unrealized_pl, realized_pl,
                    event_time_utc, correlation_id
                ) VALUES (
                    :psid, :oid, :aid, :inst,
                    'open', 1000, 1.10, NULL, NULL,
                    :ts, NULL
                )
                """
            ),
            {
                "psid": generate_ulid(),
                "oid": order_id,
                "aid": _ACCOUNT_ID,
                "inst": _INSTRUMENT,
                "ts": _OPEN_AT.isoformat(),
            },
        )


class TestExitFlowEndToEnd:
    def test_tp_hit_writes_close_event(self, engine) -> None:
        from fx_ai_trading.adapters.broker.mock import MockBroker
        from fx_ai_trading.repositories.close_events import CloseEventsRepository
        from fx_ai_trading.services.exit_gate_runner import run_exit_gate
        from fx_ai_trading.services.exit_policy import ExitPolicyService
        from fx_ai_trading.services.state_manager import StateManager

        order_id = "__test_entry_ord_exit_tp__"
        _seed_open_position(engine, order_id=order_id)

        clock = FixedClock(_FIXED_AT)
        broker = MockBroker(account_type="demo", fill_price=1.1100)
        state_manager = StateManager(engine, account_id=_ACCOUNT_ID, clock=clock)
        # Real ExitPolicyService — same instance type the production gate
        # would receive — so the policy half of the contract is exercised
        # against the same TP comparison the deprecated test verified.
        policy = ExitPolicyService()

        results = run_exit_gate(
            broker=broker,
            account_id=_ACCOUNT_ID,
            clock=clock,
            state_manager=state_manager,
            exit_policy=policy,
            price_feed=lambda _instrument: 1.1100,
            side="long",
            tp=1.1100,
            sl=1.0900,
        )

        assert len(results) == 1
        assert results[0].outcome == "closed"
        assert results[0].primary_reason == "tp"

        repo = CloseEventsRepository(engine=engine)
        rows = repo.get_recent(limit=20)
        matching = [r for r in rows if r["order_id"] == order_id]
        assert len(matching) >= 1
        row = matching[0]
        assert row["primary_reason_code"] == "tp"
        reason_codes = {r["reason_code"] for r in row["reasons"]}
        assert "tp" in reason_codes

    def test_no_exit_writes_no_close_event(self, engine) -> None:
        from fx_ai_trading.adapters.broker.mock import MockBroker
        from fx_ai_trading.repositories.close_events import CloseEventsRepository
        from fx_ai_trading.services.exit_gate_runner import run_exit_gate
        from fx_ai_trading.services.exit_policy import ExitPolicyService
        from fx_ai_trading.services.state_manager import StateManager

        order_id = "__test_entry_ord_exit_noop__"
        _seed_open_position(engine, order_id=order_id)

        clock = FixedClock(_FIXED_AT)
        broker = MockBroker(account_type="demo")
        state_manager = StateManager(engine, account_id=_ACCOUNT_ID, clock=clock)
        policy = ExitPolicyService()

        results = run_exit_gate(
            broker=broker,
            account_id=_ACCOUNT_ID,
            clock=clock,
            state_manager=state_manager,
            exit_policy=policy,
            # Below TP, above SL → no exit rule fires.
            price_feed=lambda _instrument: 1.1050,
            side="long",
            tp=1.1100,
            sl=1.0900,
        )

        # Exactly one position was open; the gate must report it as 'noop'
        # and must NOT have placed an order or written a close_events row.
        assert [r.outcome for r in results if r.order_id == order_id] == ["noop"]
        assert len(broker._placed_orders) == 0

        repo = CloseEventsRepository(engine=engine)
        rows = repo.get_recent(limit=20)
        assert all(r["order_id"] != order_id for r in rows)
