"""Integration tests for PlaceOrderUseCase — end-to-end via real DB.

Requires DATABASE_URL (from .env or env var). Auto-skipped when unset.

Flow verified:
  1. Account exists (fixture)
  2. PlaceOrderUseCase.execute() succeeds
  3. orders row created in DB
  4. positions snapshot created in DB
  5. account_type mismatch raises ValueError (no DB side-effects)
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)

_DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()

pytestmark = pytest.mark.skipif(
    not _DATABASE_URL, reason="DATABASE_URL not set — skipping integration tests"
)

_BROKER_ID = "__test_broker_uc__"
_ACCOUNT_ID = "__test_account_uc__"
_INSTRUMENT = "__TEST_INSTR_UC__"
_ORDER_ID = "__test_order_uc_001__"
_SNAP_ID = "__test_snap_uc_001__"


@pytest.fixture(scope="module")
def engine():
    e = create_engine(_DATABASE_URL)
    yield e
    e.dispose()


@pytest.fixture(scope="module")
def usecase(engine):
    from fx_ai_trading.repositories.accounts import AccountsRepository
    from fx_ai_trading.repositories.orders import OrdersRepository
    from fx_ai_trading.repositories.positions import PositionsRepository
    from fx_ai_trading.services.account_service import AccountService
    from fx_ai_trading.services.order_service import OrderService
    from fx_ai_trading.services.position_service import PositionService
    from fx_ai_trading.usecases.place_order_usecase import PlaceOrderUseCase

    account_svc = AccountService(AccountsRepository(engine))
    order_svc = OrderService(OrdersRepository(engine))
    position_svc = PositionService(PositionsRepository(engine))
    return PlaceOrderUseCase(
        account_service=account_svc,
        order_service=order_svc,
        position_service=position_svc,
    )


@pytest.fixture(scope="module", autouse=True)
def seed_and_cleanup(engine):
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO brokers (broker_id, name) VALUES (:id, :name) ON CONFLICT DO NOTHING"
            ),
            {"id": _BROKER_ID, "name": "Test Broker UC"},
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
                " VALUES (:i, 'TST', 'USD', -4) ON CONFLICT DO NOTHING"
            ),
            {"i": _INSTRUMENT},
        )
    yield
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM positions WHERE position_snapshot_id = :id"),
            {"id": _SNAP_ID},
        )
        conn.execute(text("DELETE FROM orders WHERE order_id = :id"), {"id": _ORDER_ID})
        conn.execute(text("DELETE FROM accounts WHERE account_id = :id"), {"id": _ACCOUNT_ID})
        conn.execute(text("DELETE FROM brokers WHERE broker_id = :id"), {"id": _BROKER_ID})
        conn.execute(text("DELETE FROM instruments WHERE instrument = :i"), {"i": _INSTRUMENT})


def test_place_buy_order_creates_order_and_position(usecase, engine) -> None:
    usecase.execute(
        order_id=_ORDER_ID,
        position_snapshot_id=_SNAP_ID,
        account_id=_ACCOUNT_ID,
        instrument=_INSTRUMENT,
        account_type="demo",
        order_type="market",
        direction="buy",
        units="1000",
        correlation_id="test-corr-001",
    )

    with engine.connect() as conn:
        order_row = conn.execute(
            text("SELECT order_id, status, direction FROM orders WHERE order_id = :id"),
            {"id": _ORDER_ID},
        ).fetchone()
        pos_row = conn.execute(
            text(
                "SELECT position_snapshot_id, event_type FROM positions"
                " WHERE position_snapshot_id = :id"
            ),
            {"id": _SNAP_ID},
        ).fetchone()

    assert order_row is not None, "order row must exist in DB"
    assert order_row[1] == "PENDING"
    assert order_row[2] == "buy"

    assert pos_row is not None, "position snapshot must exist in DB"
    assert pos_row[1] == "open"


def test_account_type_mismatch_raises_and_no_db_side_effects(usecase, engine) -> None:
    new_order_id = "__test_order_uc_mismatch__"
    new_snap_id = "__test_snap_uc_mismatch__"

    with pytest.raises(ValueError, match="account_type mismatch"):
        usecase.execute(
            order_id=new_order_id,
            position_snapshot_id=new_snap_id,
            account_id=_ACCOUNT_ID,
            instrument=_INSTRUMENT,
            account_type="live",
            order_type="market",
            direction="buy",
            units="500",
        )

    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT order_id FROM orders WHERE order_id = :id"),
            {"id": new_order_id},
        ).fetchone()
    assert row is None, "no order must be inserted when validation fails"


def test_invalid_units_raises_before_db(usecase, engine) -> None:
    with pytest.raises(ValueError, match="units"):
        usecase.execute(
            order_id="__should_not_exist__",
            position_snapshot_id="__snap_should_not_exist__",
            account_id=_ACCOUNT_ID,
            instrument=_INSTRUMENT,
            account_type="demo",
            order_type="market",
            direction="buy",
            units="0",
        )
