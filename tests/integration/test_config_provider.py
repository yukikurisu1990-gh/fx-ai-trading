"""Integration tests for ConfigProvider.

Requires RUN_DB_INTEGRATION_TESTS=1 and a DATABASE_URL the caller exported.
Tests never read .env — having the resource is not authorization to use it.
Exercises compute_version() against the live app_settings table.
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
def provider(engine):
    from fx_ai_trading.config.config_provider import ConfigProvider
    from fx_ai_trading.repositories.app_settings import AppSettingsRepository

    repo = AppSettingsRepository(engine)
    return ConfigProvider(repo=repo)


def test_compute_version_returns_16_hex_chars(provider) -> None:
    version = provider.compute_version()
    assert len(version) == 16
    assert all(c in "0123456789abcdef" for c in version)


def test_compute_version_is_deterministic(provider) -> None:
    v1 = provider.compute_version()
    v2 = provider.compute_version()
    assert v1 == v2


def test_get_existing_key(provider) -> None:
    value = provider.get("expected_account_type")
    assert value is not None
