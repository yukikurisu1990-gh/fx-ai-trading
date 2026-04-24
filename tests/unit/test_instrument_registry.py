"""Unit tests: OandaInstrumentRegistry TTL cache + type filtering (Phase 9.2)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

from fx_ai_trading.adapters.instrument_registry import OandaInstrumentRegistry
from fx_ai_trading.common.clock import FixedClock


def _make_entry(name: str, type_: str = "CURRENCY", tradeable: bool = True) -> dict:
    return {"name": name, "type": type_, "tradeable": tradeable}


def _make_client(entries: list[dict]) -> MagicMock:
    client = MagicMock()
    client.list_account_instruments.return_value = entries
    return client


class TestOandaInstrumentRegistryFiltering:
    def test_returns_currency_instruments_only(self) -> None:
        entries = [
            _make_entry("EUR_USD", "CURRENCY"),
            _make_entry("CORN_USD", "CFD"),
            _make_entry("GBP_USD", "CURRENCY"),
        ]
        client = _make_client(entries)
        reg = OandaInstrumentRegistry(client, "acct-1")
        result = reg.list_active()
        assert result == ["EUR_USD", "GBP_USD"]

    def test_excludes_non_tradeable(self) -> None:
        entries = [
            _make_entry("EUR_USD", tradeable=True),
            _make_entry("GBP_USD", tradeable=False),
        ]
        client = _make_client(entries)
        reg = OandaInstrumentRegistry(client, "acct-1")
        result = reg.list_active()
        assert "GBP_USD" not in result
        assert "EUR_USD" in result

    def test_result_is_sorted(self) -> None:
        entries = [
            _make_entry("USD_JPY"),
            _make_entry("AUD_USD"),
            _make_entry("EUR_USD"),
        ]
        client = _make_client(entries)
        reg = OandaInstrumentRegistry(client, "acct-1")
        result = reg.list_active()
        assert result == sorted(result)

    def test_empty_list_when_no_currency_pairs(self) -> None:
        client = _make_client([_make_entry("CORN_USD", "CFD")])
        reg = OandaInstrumentRegistry(client, "acct-1")
        assert reg.list_active() == []

    def test_custom_instrument_types(self) -> None:
        entries = [_make_entry("CORN_USD", "CFD"), _make_entry("EUR_USD", "CURRENCY")]
        client = _make_client(entries)
        reg = OandaInstrumentRegistry(client, "acct-1", instrument_types=frozenset({"CFD"}))
        assert reg.list_active() == ["CORN_USD"]


class TestOandaInstrumentRegistryTTL:
    def test_first_call_hits_api(self) -> None:
        client = _make_client([_make_entry("EUR_USD")])
        reg = OandaInstrumentRegistry(client, "acct-1")
        reg.list_active()
        client.list_account_instruments.assert_called_once_with("acct-1")

    def test_second_call_uses_cache(self) -> None:
        client = _make_client([_make_entry("EUR_USD")])
        reg = OandaInstrumentRegistry(client, "acct-1", ttl_seconds=3600)
        reg.list_active()
        reg.list_active()
        assert client.list_account_instruments.call_count == 1

    def test_expired_cache_triggers_refresh(self) -> None:
        client = _make_client([_make_entry("EUR_USD")])
        t0 = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        reg = OandaInstrumentRegistry(client, "acct-1", ttl_seconds=1, clock=FixedClock(t0))
        reg.list_active()
        # Manually expire cache by back-dating _cached_at.
        reg._cached_at = t0 - timedelta(seconds=10)
        reg.list_active()
        assert client.list_account_instruments.call_count == 2

    def test_invalidate_forces_refresh(self) -> None:
        client = _make_client([_make_entry("EUR_USD")])
        reg = OandaInstrumentRegistry(client, "acct-1")
        reg.list_active()
        reg.invalidate()
        reg.list_active()
        assert client.list_account_instruments.call_count == 2

    def test_returns_copy_not_internal_list(self) -> None:
        client = _make_client([_make_entry("EUR_USD")])
        reg = OandaInstrumentRegistry(client, "acct-1")
        result = reg.list_active()
        result.append("MUTATED")
        assert "MUTATED" not in reg.list_active()
