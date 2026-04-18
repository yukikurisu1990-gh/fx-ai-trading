"""Integration tests for PositionsRepository.

Requires DATABASE_URL (from .env or env var). Auto-skipped when unset.
Inserts fixture broker/account/instrument/position rows, verifies read, cleans up.
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

_BROKER_ID = "__test_broker_pos__"
_ACCOUNT_ID = "__test_account_pos__"
_INSTRUMENT = "__TEST_INSTR_POS__"
_SNAPSHOT_ID = "__test_snapshot_001__"


@pytest.fixture(scope="module")
def engine():
    e = create_engine(_DATABASE_URL)
    yield e
    e.dispose()


@pytest.fixture(scope="module")
def repo(engine):
    from fx_ai_trading.repositories.positions import PositionsRepository

    return PositionsRepository(engine)


@pytest.fixture(scope="module", autouse=True)
def seed_and_cleanup(engine):
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO brokers (broker_id, name) VALUES (:id, :name) ON CONFLICT DO NOTHING"
            ),
            {"id": _BROKER_ID, "name": "Test Broker Pos"},
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
        conn.execute(
            text(
                "INSERT INTO positions"
                " (position_snapshot_id, account_id, instrument, event_type, units, event_time_utc)"
                " VALUES (:sid, :aid, :inst, 'open', 1000, NOW())"
                " ON CONFLICT DO NOTHING"
            ),
            {"sid": _SNAPSHOT_ID, "aid": _ACCOUNT_ID, "inst": _INSTRUMENT},
        )
    yield
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM positions WHERE position_snapshot_id = :id"),
            {"id": _SNAPSHOT_ID},
        )
        conn.execute(text("DELETE FROM accounts WHERE account_id = :id"), {"id": _ACCOUNT_ID})
        conn.execute(text("DELETE FROM brokers WHERE broker_id = :id"), {"id": _BROKER_ID})
        conn.execute(text("DELETE FROM instruments WHERE instrument = :i"), {"i": _INSTRUMENT})


def test_get_by_position_id_returns_dict(repo) -> None:
    result = repo.get_by_position_id(_SNAPSHOT_ID)
    assert result is not None
    assert result["position_snapshot_id"] == _SNAPSHOT_ID
    assert result["event_type"] == "open"


def test_get_by_position_id_missing_returns_none(repo) -> None:
    assert repo.get_by_position_id("__no_such_snapshot__") is None


def test_get_open_positions_includes_seeded(repo) -> None:
    results = repo.get_open_positions(_ACCOUNT_ID)
    ids = [r["position_snapshot_id"] for r in results]
    assert _SNAPSHOT_ID in ids


def test_get_open_positions_empty_account_returns_list(repo) -> None:
    results = repo.get_open_positions("__no_such_account__")
    assert isinstance(results, list)
    assert len(results) == 0
