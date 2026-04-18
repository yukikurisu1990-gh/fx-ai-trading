"""Integration tests for AccountsRepository.

Requires DATABASE_URL (from .env or env var). Auto-skipped when unset.
Inserts fixture broker/account rows, verifies read/write, then cleans up.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from fx_ai_trading.config.common_keys_context import CommonKeysContext

_CTX = CommonKeysContext(
    run_id="integ-run-001",
    environment="test",
    code_version="0.0.0",
    config_version="test-cfg",
)

load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)

_DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()

pytestmark = pytest.mark.skipif(
    not _DATABASE_URL, reason="DATABASE_URL not set — skipping integration tests"
)

_BROKER_ID = "__test_broker_acct__"
_ACCOUNT_ID = "__test_account_001__"


@pytest.fixture(scope="module")
def engine():
    e = create_engine(_DATABASE_URL)
    yield e
    e.dispose()


@pytest.fixture(scope="module")
def repo(engine):
    from fx_ai_trading.repositories.accounts import AccountsRepository

    return AccountsRepository(engine)


@pytest.fixture(scope="module", autouse=True)
def seed_and_cleanup(engine):
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO brokers (broker_id, name)"
                " VALUES (:broker_id, :name)"
                " ON CONFLICT DO NOTHING"
            ),
            {"broker_id": _BROKER_ID, "name": "Test Broker"},
        )
        conn.execute(
            text(
                "INSERT INTO accounts (account_id, broker_id, account_type, base_currency)"
                " VALUES (:account_id, :broker_id, :account_type, :base_currency)"
                " ON CONFLICT DO NOTHING"
            ),
            {
                "account_id": _ACCOUNT_ID,
                "broker_id": _BROKER_ID,
                "account_type": "demo",
                "base_currency": "USD",
            },
        )
    yield
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM accounts WHERE account_id = :id"), {"id": _ACCOUNT_ID})
        conn.execute(text("DELETE FROM brokers WHERE broker_id = :id"), {"id": _BROKER_ID})


def test_get_by_account_id_returns_dict(repo) -> None:
    result = repo.get_by_account_id(_ACCOUNT_ID)
    assert result is not None
    assert result["account_id"] == _ACCOUNT_ID
    assert result["account_type"] == "demo"


def test_get_by_account_id_missing_returns_none(repo) -> None:
    assert repo.get_by_account_id("__no_such_account__") is None


def test_list_accounts_includes_seeded(repo) -> None:
    results = repo.list_accounts()
    ids = [r["account_id"] for r in results]
    assert _ACCOUNT_ID in ids


def test_update_account_changes_field(repo) -> None:
    repo.update_account(_ACCOUNT_ID, _CTX, account_type="live")
    result = repo.get_by_account_id(_ACCOUNT_ID)
    assert result is not None
    assert result["account_type"] == "live"
    repo.update_account(_ACCOUNT_ID, _CTX, account_type="demo")
