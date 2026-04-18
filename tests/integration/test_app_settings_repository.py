"""Integration tests for AppSettingsRepository.

Requires DATABASE_URL (from .env or env var). Auto-skipped when unset.
Reads and writes against the live app_settings table.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)

_DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()

pytestmark = pytest.mark.skipif(
    not _DATABASE_URL, reason="DATABASE_URL not set — skipping integration tests"
)


@pytest.fixture(scope="module")
def engine():
    e = create_engine(_DATABASE_URL)
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
