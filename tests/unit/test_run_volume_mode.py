"""Unit tests for scripts/run_volume_mode.py — Phase 9.X-F/V-1."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from scripts.run_volume_mode import (
    Config,
    SessionState,
    VolumeRunner,
    _config_from_args,
    _parse_hours_jst,
    _quote_volume_usd,
    _within_hours,
)

JST = ZoneInfo("Asia/Tokyo")


def _cfg(**overrides):
    base = dict(
        instrument="USD_JPY",
        units_per_trade=5000,
        target_volume_usd=500_000.0,
        max_spread_pip=1.5,
        max_daily_loss_jpy=3000.0,
        hours_jst_start=15,
        hours_jst_end=21,
        max_hourly_trades=6,
        max_daily_trades=50,
        tp_pip=1.0,
        sl_pip=3.0,
        time_stop_sec=90.0,
        cooloff_min_sec=30.0,
        cooloff_max_sec=60.0,
    )
    base.update(overrides)
    return Config(**base)


# ---------------------------------------------------------------------------
# CLI / Config
# ---------------------------------------------------------------------------


class TestParseHoursJst:
    def test_valid(self):
        assert _parse_hours_jst("15-21") == (15, 21)

    def test_start_must_be_less_than_end(self):
        import argparse

        with pytest.raises(argparse.ArgumentTypeError):
            _parse_hours_jst("21-15")

    def test_out_of_range(self):
        import argparse

        with pytest.raises(argparse.ArgumentTypeError):
            _parse_hours_jst("0-24")

    def test_garbage(self):
        import argparse

        with pytest.raises(argparse.ArgumentTypeError):
            _parse_hours_jst("not-a-range")


class TestConfigFromArgs:
    def test_live_requires_confirmation(self):
        import argparse

        ns = argparse.Namespace(
            account="live",
            confirm_live_trading=False,
            instrument="USD_JPY",
            units_per_trade=5000,
            target_volume_usd=500_000.0,
            max_spread_pip=1.5,
            max_daily_loss_jpy=3000.0,
            hours_jst=(15, 21),
            max_hourly_trades=6,
            max_daily_trades=50,
            tp_pip=1.0,
            sl_pip=3.0,
            time_stop_sec=90.0,
            cooloff_min_sec=30.0,
            cooloff_max_sec=60.0,
            pip_size=0.01,
            poll_interval_sec=2.0,
            dry_run=False,
        )
        with pytest.raises(SystemExit, match="confirm-live-trading"):
            _config_from_args(ns)

    def test_demo_default(self):
        import argparse

        ns = argparse.Namespace(
            account="demo",
            confirm_live_trading=False,
            instrument="USD_JPY",
            units_per_trade=5000,
            target_volume_usd=500_000.0,
            max_spread_pip=1.5,
            max_daily_loss_jpy=3000.0,
            hours_jst=(15, 21),
            max_hourly_trades=6,
            max_daily_trades=50,
            tp_pip=1.0,
            sl_pip=3.0,
            time_stop_sec=90.0,
            cooloff_min_sec=30.0,
            cooloff_max_sec=60.0,
            pip_size=0.01,
            poll_interval_sec=2.0,
            dry_run=False,
        )
        cfg = _config_from_args(ns)
        assert cfg.account_type == "demo"
        assert cfg.environment == "practice"

    def test_live_with_confirmation(self):
        import argparse

        ns = argparse.Namespace(
            account="live",
            confirm_live_trading=True,
            instrument="USD_JPY",
            units_per_trade=5000,
            target_volume_usd=500_000.0,
            max_spread_pip=1.5,
            max_daily_loss_jpy=3000.0,
            hours_jst=(15, 21),
            max_hourly_trades=6,
            max_daily_trades=50,
            tp_pip=1.0,
            sl_pip=3.0,
            time_stop_sec=90.0,
            cooloff_min_sec=30.0,
            cooloff_max_sec=60.0,
            pip_size=0.01,
            poll_interval_sec=2.0,
            dry_run=False,
        )
        cfg = _config_from_args(ns)
        assert cfg.account_type == "live"
        assert cfg.environment == "live"

    def test_invalid_cooloff_ordering(self):
        import argparse

        ns = argparse.Namespace(
            account="demo",
            confirm_live_trading=False,
            instrument="USD_JPY",
            units_per_trade=5000,
            target_volume_usd=500_000.0,
            max_spread_pip=1.5,
            max_daily_loss_jpy=3000.0,
            hours_jst=(15, 21),
            max_hourly_trades=6,
            max_daily_trades=50,
            tp_pip=1.0,
            sl_pip=3.0,
            time_stop_sec=90.0,
            cooloff_min_sec=60.0,
            cooloff_max_sec=30.0,
            pip_size=0.01,
            poll_interval_sec=2.0,
            dry_run=False,
        )
        with pytest.raises(SystemExit, match="cooloff"):
            _config_from_args(ns)


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


class TestWithinHours:
    def test_inside(self):
        cfg = _cfg(hours_jst_start=15, hours_jst_end=21)
        assert _within_hours(datetime(2026, 4, 26, 18, 0, tzinfo=JST), cfg)

    def test_before_start(self):
        cfg = _cfg(hours_jst_start=15, hours_jst_end=21)
        assert not _within_hours(datetime(2026, 4, 26, 14, 59, tzinfo=JST), cfg)

    def test_at_end_excluded(self):
        cfg = _cfg(hours_jst_start=15, hours_jst_end=21)
        assert not _within_hours(datetime(2026, 4, 26, 21, 0, tzinfo=JST), cfg)


class TestQuoteVolumeUsd:
    def test_usd_jpy(self):
        # USD on base side: notional in USD = units.
        assert _quote_volume_usd("USD_JPY", 5000, 150.0) == 5000.0

    def test_usd_cad(self):
        assert _quote_volume_usd("USD_CAD", 5000, 1.35) == 5000.0

    def test_eur_usd(self):
        # USD on quote side: notional in USD = units * mid.
        assert _quote_volume_usd("EUR_USD", 5000, 1.10) == pytest.approx(5500.0)

    def test_unsupported_cross(self):
        with pytest.raises(ValueError, match="USD"):
            _quote_volume_usd("EUR_GBP", 5000, 0.85)


# ---------------------------------------------------------------------------
# Gate logic — uses fakes so no HTTP is involved
# ---------------------------------------------------------------------------


class _FakeQuote:
    def __init__(self, bid: float, ask: float) -> None:
        self.bid = bid
        self.ask = ask


class _FakeQuoteFeed:
    def __init__(self, quote: _FakeQuote | Exception | None = None) -> None:
        self._quote = quote

    def get_quote(self, _instrument: str):
        if isinstance(self._quote, Exception):
            raise self._quote
        return self._quote


class _FakeBroker:
    account_id = "FAKE"


class _FakeLog:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    def emit(self, event, **fields):
        self.events.append((event, fields))


def _runner_at_jst(hour: int, *, quote=None, **state_kw):
    cfg = _cfg()
    feed = _FakeQuoteFeed(quote if quote is not None else _FakeQuote(bid=150.000, ask=150.005))
    log = _FakeLog()
    runner = VolumeRunner(cfg, _FakeBroker(), feed, log)  # type: ignore[arg-type]
    for k, v in state_kw.items():
        setattr(runner.state, k, v)
    return runner, log


class TestGate:
    def _at_hour(self, runner, hour: int):
        # Monkey-patch datetime.now within the module under test.
        import scripts.run_volume_mode as mod

        class _FrozenDT(datetime):
            @classmethod
            def now(cls, tz=None):
                return datetime(2026, 4, 26, hour, 0, tzinfo=tz or JST)

        orig = mod.datetime
        mod.datetime = _FrozenDT  # type: ignore[assignment]
        try:
            return runner._gate()
        finally:
            mod.datetime = orig  # type: ignore[assignment]

    def test_outside_hours(self):
        runner, _ = _runner_at_jst(10)
        assert self._at_hour(runner, 10) == "outside_hours"

    def test_volume_target_hit(self):
        runner, _ = _runner_at_jst(18, cumulative_volume_usd=500_001.0)
        assert self._at_hour(runner, 18) == "volume_target_hit"

    def test_daily_limit(self):
        runner, _ = _runner_at_jst(18, daily_trades=50)
        assert self._at_hour(runner, 18) == "daily_limit"

    def test_loss_cap(self):
        runner, _ = _runner_at_jst(18, daily_pnl_jpy=-3000.0)
        assert self._at_hour(runner, 18) == "loss_cap"

    def test_hourly_limit(self):
        import time as _time

        now = _time.time()
        runner, _ = _runner_at_jst(18, hourly_window=[now] * 6)
        assert self._at_hour(runner, 18) == "hourly_limit"

    def test_cooldown_after_losses(self):
        runner, _ = _runner_at_jst(18, consecutive_losses=3)
        assert self._at_hour(runner, 18) == "cooldown_after_losses"

    def test_spread_too_wide(self):
        runner, _ = _runner_at_jst(
            18,
            quote=_FakeQuote(bid=150.000, ask=150.020),  # 2.0 pip spread
        )
        assert self._at_hour(runner, 18) == "spread_too_wide"

    def test_quote_error(self):
        runner, log = _runner_at_jst(18, quote=RuntimeError("api down"))
        assert self._at_hour(runner, 18) == "quote_error"
        # An error event was logged.
        assert any(e == "cycle.error" for e, _ in log.events)

    def test_proceed_when_all_clear(self):
        runner, _ = _runner_at_jst(18)
        assert self._at_hour(runner, 18) is None

    def test_halt_reason_short_circuits(self):
        runner, _ = _runner_at_jst(18)
        runner.state.halt_reason = "close_failed"
        assert self._at_hour(runner, 18) == "close_failed"


# ---------------------------------------------------------------------------
# SessionState helpers
# ---------------------------------------------------------------------------


class TestSessionState:
    def test_record_hourly_trims_old_entries(self):
        s = SessionState()
        # 4000 sec ago should be evicted; 100 sec ago kept.
        s.hourly_window = [1000.0, 5000.0]
        s.record_hourly(5500.0)
        # Cutoff = 5500 - 3600 = 1900 → only 5000 and 5500 survive.
        assert s.hourly_window == [5000.0, 5500.0]
