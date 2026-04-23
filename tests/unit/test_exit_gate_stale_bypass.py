"""Unit tests: stale_max_age_seconds threading through Supervisor (replay PR4).

Pins the contract that:
  - attach_exit_gate() accepts stale_max_age_seconds and stores it in
    _ExitGateAttachment.
  - run_exit_gate_tick() forwards stale_max_age_seconds to run_exit_gate,
    so a small threshold causes noop_stale_quote and a large one allows the
    close path to execute.
  - build_supervisor_with_paper_stack() accepts stale_max_age_seconds and
    passes it to attach_exit_gate().
  - The default (60.0) preserves existing live-mode behaviour.

Tests stub run_exit_gate itself so the unit tests do not need a DB or
OANDA connection.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from fx_ai_trading.common.clock import FixedClock
from fx_ai_trading.domain.price_feed import Quote
from fx_ai_trading.supervisor.supervisor import Supervisor

_NOW = datetime(2026, 4, 24, 12, 0, 0, tzinfo=UTC)

# ---------------------------------------------------------------------------
# Minimal QuoteFeed stub that returns a quote with a configurable age
# ---------------------------------------------------------------------------


class _AgedQuoteFeed:
    """Returns a single Quote whose ts is *age_seconds* before *now*."""

    def __init__(self, now: datetime, age_seconds: float) -> None:
        self._quote = Quote(
            price=1.10,
            ts=now - timedelta(seconds=age_seconds),
            source="oanda_rest_snapshot",
        )

    def get_quote(self, instrument: str) -> Quote:  # noqa: ARG002
        return self._quote


# ---------------------------------------------------------------------------
# Helpers to build a minimal Supervisor with attach_exit_gate wired
# ---------------------------------------------------------------------------


def _make_supervisor(
    stale_max_age_seconds: float,
    quote_age_seconds: float,
) -> tuple[Supervisor, list[dict[str, Any]]]:
    """Return (supervisor, calls_captured) where calls_captured accumulates
    every kwargs dict that run_exit_gate was invoked with."""
    clock = FixedClock(_NOW)
    sup = Supervisor(clock=clock)
    feed = _AgedQuoteFeed(_NOW, quote_age_seconds)

    calls: list[dict[str, Any]] = []

    def _fake_run_exit_gate(**kw: object) -> list[object]:
        calls.append(kw)
        return []

    broker = MagicMock()
    state_manager = MagicMock()
    exit_policy = MagicMock()

    sup.attach_exit_gate(
        broker=broker,
        account_id="acct-test",
        state_manager=state_manager,
        exit_policy=exit_policy,
        quote_feed=feed,
        stale_max_age_seconds=stale_max_age_seconds,
    )

    with patch(
        "fx_ai_trading.services.exit_gate_runner.run_exit_gate",
        side_effect=_fake_run_exit_gate,
    ):
        sup.run_exit_gate_tick()

    return sup, calls


# ---------------------------------------------------------------------------
# Tests: _ExitGateAttachment stores stale_max_age_seconds
# ---------------------------------------------------------------------------


class TestAttachExitGateStoresStaleMaxAge:
    def test_default_is_60_seconds(self) -> None:
        clock = FixedClock(_NOW)
        sup = Supervisor(clock=clock)
        sup.attach_exit_gate(
            broker=MagicMock(),
            account_id="acct-test",
            state_manager=MagicMock(),
            exit_policy=MagicMock(),
            quote_feed=_AgedQuoteFeed(_NOW, 0),
        )
        assert sup._exit_gate is not None
        assert sup._exit_gate.stale_max_age_seconds == 60.0

    def test_custom_value_stored(self) -> None:
        clock = FixedClock(_NOW)
        sup = Supervisor(clock=clock)
        sup.attach_exit_gate(
            broker=MagicMock(),
            account_id="acct-test",
            state_manager=MagicMock(),
            exit_policy=MagicMock(),
            quote_feed=_AgedQuoteFeed(_NOW, 0),
            stale_max_age_seconds=99999.0,
        )
        assert sup._exit_gate is not None
        assert sup._exit_gate.stale_max_age_seconds == 99999.0


# ---------------------------------------------------------------------------
# Tests: run_exit_gate_tick forwards stale_max_age_seconds
# ---------------------------------------------------------------------------


class TestRunExitGateTickForwardsStaleMaxAge:
    def test_small_threshold_forwarded(self) -> None:
        _sup, calls = _make_supervisor(stale_max_age_seconds=1.0, quote_age_seconds=0)
        assert len(calls) == 1
        assert calls[0]["stale_max_age_seconds"] == pytest.approx(1.0)

    def test_large_threshold_forwarded(self) -> None:
        _sup, calls = _make_supervisor(stale_max_age_seconds=99999.0, quote_age_seconds=0)
        assert len(calls) == 1
        assert calls[0]["stale_max_age_seconds"] == pytest.approx(99999.0)

    def test_default_threshold_forwarded(self) -> None:
        clock = FixedClock(_NOW)
        sup = Supervisor(clock=clock)
        sup.attach_exit_gate(
            broker=MagicMock(),
            account_id="acct-test",
            state_manager=MagicMock(),
            exit_policy=MagicMock(),
            quote_feed=_AgedQuoteFeed(_NOW, 0),
        )
        calls: list[dict[str, Any]] = []

        def _capture(**kw: object) -> list[object]:
            calls.append(kw)
            return []

        with patch(
            "fx_ai_trading.services.exit_gate_runner.run_exit_gate",
            side_effect=_capture,
        ):
            sup.run_exit_gate_tick()

        assert calls[0]["stale_max_age_seconds"] == pytest.approx(60.0)


# ---------------------------------------------------------------------------
# Tests: build_supervisor_with_paper_stack threads stale_max_age_seconds
# ---------------------------------------------------------------------------


class TestBuildSupervisorWithPaperStackThreadsStaleMaxAge:
    def _build(self, stale_max_age_seconds: float) -> Supervisor:
        import importlib.util
        import sys
        from pathlib import Path as _Path

        _repo_root = _Path(__file__).resolve().parents[2]
        alias = "_run_paper_loop_stale_test"
        if alias not in sys.modules:
            spec = importlib.util.spec_from_file_location(
                alias, _repo_root / "scripts" / "run_paper_loop.py"
            )
            assert spec and spec.loader
            mod = importlib.util.module_from_spec(spec)
            sys.modules[alias] = mod
            spec.loader.exec_module(mod)
        mod = sys.modules[alias]

        fake_engine = MagicMock()

        # Patch heavy constructors that touch network / DB
        with (
            patch.object(mod, "OandaAPIClient", return_value=MagicMock()),
            patch.object(mod, "OandaQuoteFeed", return_value=_AgedQuoteFeed(_NOW, 0)),
            patch.object(mod, "PaperBroker", return_value=MagicMock()),
            patch.object(mod, "StateManager", return_value=MagicMock()),
            patch.object(mod, "ExitPolicyService", return_value=MagicMock()),
            patch.object(mod, "WallClock", return_value=FixedClock(_NOW)),
        ):
            oanda = SimpleNamespace(
                access_token="tok", account_id="acct-test", environment="practice"
            )
            supervisor, _feed = mod.build_supervisor_with_paper_stack(
                oanda=oanda,
                instrument="EUR_USD",
                engine=fake_engine,
                stale_max_age_seconds=stale_max_age_seconds,
            )
        return supervisor

    def test_default_stale_max_age_is_60(self) -> None:
        import importlib.util
        import sys
        from pathlib import Path as _Path

        _repo_root = _Path(__file__).resolve().parents[2]
        alias = "_run_paper_loop_stale_test"
        if alias not in sys.modules:
            spec = importlib.util.spec_from_file_location(
                alias, _repo_root / "scripts" / "run_paper_loop.py"
            )
            assert spec and spec.loader
            mod = importlib.util.module_from_spec(spec)
            sys.modules[alias] = mod
            spec.loader.exec_module(mod)
        mod = sys.modules[alias]

        with (
            patch.object(mod, "OandaAPIClient", return_value=MagicMock()),
            patch.object(mod, "OandaQuoteFeed", return_value=_AgedQuoteFeed(_NOW, 0)),
            patch.object(mod, "PaperBroker", return_value=MagicMock()),
            patch.object(mod, "StateManager", return_value=MagicMock()),
            patch.object(mod, "ExitPolicyService", return_value=MagicMock()),
            patch.object(mod, "WallClock", return_value=FixedClock(_NOW)),
        ):
            oanda = SimpleNamespace(
                access_token="tok", account_id="acct-test", environment="practice"
            )
            supervisor, _feed = mod.build_supervisor_with_paper_stack(
                oanda=oanda,
                instrument="EUR_USD",
                engine=MagicMock(),
            )
        assert supervisor._exit_gate is not None
        assert supervisor._exit_gate.stale_max_age_seconds == pytest.approx(60.0)

    def test_custom_stale_max_age_stored(self) -> None:
        sup = self._build(stale_max_age_seconds=86400.0)
        assert sup._exit_gate is not None
        assert sup._exit_gate.stale_max_age_seconds == pytest.approx(86400.0)
