"""Integration tests for OrdersRepository.

Requires DATABASE_URL (from .env or env var). Auto-skipped when unset.
Inserts fixture broker/account/instrument/order rows, verifies read/write, cleans up.
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

_BROKER_ID = "__test_broker_ord__"
_ACCOUNT_ID = "__test_account_ord__"
_INSTRUMENT = "__TEST_INSTR__"
_ORDER_ID = "__test_order_001__"


@pytest.fixture(scope="module")
def engine():
    e = create_engine(_DATABASE_URL)
    yield e
    e.dispose()


@pytest.fixture(scope="module")
def repo(engine):
    from fx_ai_trading.repositories.orders import OrdersRepository

    return OrdersRepository(engine)


@pytest.fixture(scope="module", autouse=True)
def seed_and_cleanup(engine):
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO brokers (broker_id, name) VALUES (:id, :name) ON CONFLICT DO NOTHING"
            ),
            {"id": _BROKER_ID, "name": "Test Broker Ord"},
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
        conn.execute(text("DELETE FROM orders WHERE order_id = :id"), {"id": _ORDER_ID})
        conn.execute(text("DELETE FROM accounts WHERE account_id = :id"), {"id": _ACCOUNT_ID})
        conn.execute(text("DELETE FROM brokers WHERE broker_id = :id"), {"id": _BROKER_ID})
        conn.execute(text("DELETE FROM instruments WHERE instrument = :i"), {"i": _INSTRUMENT})


def test_create_and_get_order(repo) -> None:
    repo.create_order(
        order_id=_ORDER_ID,
        account_id=_ACCOUNT_ID,
        instrument=_INSTRUMENT,
        account_type="demo",
        order_type="market",
        direction="buy",
        units="1000",
    )
    result = repo.get_by_order_id(_ORDER_ID)
    assert result is not None
    assert result["order_id"] == _ORDER_ID
    assert result["status"] == "PENDING"
    assert result["direction"] == "buy"


def test_get_missing_order_returns_none(repo) -> None:
    assert repo.get_by_order_id("__no_such_order__") is None
