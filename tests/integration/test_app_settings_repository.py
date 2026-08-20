"""Integration tests for AppSettingsRepository.

Requires RUN_DB_INTEGRATION_TESTS=1 and a DATABASE_URL the caller exported.
Tests never read .env — having the resource is not authorization to use it.
Reads and writes against the live app_settings table.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine

from tests.optin import database_url, requires_db

pytestmark = [pytest.mark.db, requires_db]


@pytest.fixture(scope="module")
def engine():
    e = create_engine(database_url())
    yield e
    e.dispose()


@pytest.fixture(scope="module")
def repo(engine):
    from fx_ai_trading.repositories.app_settings import AppSettingsRepository

    return AppSettingsRepository(engine)


def test_get_existing_key(repo) -> None:
    """A seeded key must return a non-None value."""
    value = repo.get("expected_account_type")
    assert value is not None


def test_get_missing_key_returns_none(repo) -> None:
    """An unknown key must return None (not raise)."""
    value = repo.get("__nonexistent_key_xyz__")
    assert value is None


def test_set_updates_value(repo) -> None:
    """set() must persist the new value, readable via get()."""
    original = repo.get("expected_account_type")
    try:
        repo.set("expected_account_type", "__test_sentinel__")
        assert repo.get("expected_account_type") == "__test_sentinel__"
    finally:
        # Restore original value regardless of assertion outcome.
        repo.set("expected_account_type", original)
        assert repo.get("expected_account_type") == original
