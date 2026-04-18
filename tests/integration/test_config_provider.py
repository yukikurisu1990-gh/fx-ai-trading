"""Integration tests for ConfigProvider.

Requires DATABASE_URL (from .env or env var). Auto-skipped when unset.
Exercises compute_version() against the live app_settings table.
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
