"""Unit tests: RiskManagerService.allow_trade — Cycle 6.6 3-guard gate.

Order of evaluation is fixed:
  G1 ``risk.duplicate_instrument``
  G2 ``risk.max_open_positions``
  G3 ``risk.recent_execution_failure_cooloff``

First violation short-circuits; later guards are not evaluated.  The
method never raises.
"""

from __future__ import annotations

from fx_ai_trading.services.risk_manager import RiskManagerService


def _mgr(
    max_open_positions: int = 5,
    cooloff_max_failures: int = 3,
) -> RiskManagerService:
    return RiskManagerService(
        max_concurrent_positions=max_open_positions,
        max_open_positions=max_open_positions,
        cooloff_max_failures=cooloff_max_failures,
    )


class TestAllowTradePass:
    def test_allowed_when_all_guards_clean(self) -> None:
        result = _mgr().allow_trade(
            instrument="EURUSD",
            open_instruments=frozenset(),
            concurrent_positions=0,
            recent_failure_count=0,
        )
        assert result.allowed is True
        assert result.reject_reason is None

    def test_allowed_when_under_every_threshold(self) -> None:
        result = _mgr(max_open_positions=5, cooloff_max_failures=3).allow_trade(
            instrument="USDJPY",
            open_instruments=frozenset({"EURUSD"}),
            concurrent_positions=4,
            recent_failure_count=2,
        )
        assert result.allowed is True


class TestAllowTradeG1DuplicateInstrument:
    def test_reject_when_instrument_already_open(self) -> None:
        result = _mgr().allow_trade(
            instrument="EURUSD",
            open_instruments=frozenset({"EURUSD"}),
            concurrent_positions=1,
            recent_failure_count=0,
        )
        assert result.allowed is False
        assert result.reject_reason == "risk.duplicate_instrument"

    def test_accepts_set_type_as_open_instruments(self) -> None:
        # frozenset and plain set must both work (caller convenience).
        result = _mgr().allow_trade(
            instrument="EURUSD",
            open_instruments={"EURUSD", "USDJPY"},
            concurrent_positions=2,
            recent_failure_count=0,
        )
        assert result.reject_reason == "risk.duplicate_instrument"


class TestAllowTradeG2MaxOpenPositions:
    def test_reject_at_cap(self) -> None:
        result = _mgr(max_open_positions=5).allow_trade(
            instrument="EURUSD",
            open_instruments=frozenset(),
            concurrent_positions=5,
            recent_failure_count=0,
        )
        assert result.allowed is False
        assert result.reject_reason == "risk.max_open_positions"

    def test_reject_above_cap(self) -> None:
        result = _mgr(max_open_positions=3).allow_trade(
            instrument="EURUSD",
            open_instruments=frozenset(),
            concurrent_positions=7,
            recent_failure_count=0,
        )
        assert result.reject_reason == "risk.max_open_positions"


class TestAllowTradeG3CooloffRecentFailures:
    def test_reject_at_threshold(self) -> None:
        result = _mgr(cooloff_max_failures=3).allow_trade(
            instrument="EURUSD",
            open_instruments=frozenset(),
            concurrent_positions=0,
            recent_failure_count=3,
        )
        assert result.allowed is False
        assert result.reject_reason == "risk.recent_execution_failure_cooloff"

    def test_reject_above_threshold(self) -> None:
        result = _mgr(cooloff_max_failures=2).allow_trade(
            instrument="EURUSD",
            open_instruments=frozenset(),
            concurrent_positions=0,
            recent_failure_count=10,
        )
        assert result.reject_reason == "risk.recent_execution_failure_cooloff"


class TestAllowTradeShortCircuits:
    """First failing guard wins; later guards are not evaluated."""

    def test_g1_wins_over_g2(self) -> None:
        result = _mgr(max_open_positions=1).allow_trade(
            instrument="EURUSD",
            open_instruments=frozenset({"EURUSD"}),  # G1 trips
            concurrent_positions=10,  # G2 would also trip
            recent_failure_count=99,  # G3 would also trip
        )
        assert result.reject_reason == "risk.duplicate_instrument"

    def test_g2_wins_over_g3(self) -> None:
        result = _mgr(max_open_positions=5, cooloff_max_failures=3).allow_trade(
            instrument="EURUSD",
            open_instruments=frozenset(),  # G1 passes
            concurrent_positions=5,  # G2 trips
            recent_failure_count=99,  # G3 would also trip
        )
        assert result.reject_reason == "risk.max_open_positions"

    def test_g1_g2_g3_evaluation_order_matches_docstring(self) -> None:
        # Fresh manager per branch — no state; each call returns the
        # first failing reason only.
        m = _mgr(max_open_positions=2, cooloff_max_failures=2)
        assert (
            m.allow_trade(
                instrument="EURUSD",
                open_instruments=frozenset({"EURUSD"}),
                concurrent_positions=0,
                recent_failure_count=0,
            ).reject_reason
            == "risk.duplicate_instrument"
        )
        assert (
            m.allow_trade(
                instrument="EURUSD",
                open_instruments=frozenset(),
                concurrent_positions=2,
                recent_failure_count=0,
            ).reject_reason
            == "risk.max_open_positions"
        )
        assert (
            m.allow_trade(
                instrument="EURUSD",
                open_instruments=frozenset(),
                concurrent_positions=0,
                recent_failure_count=2,
            ).reject_reason
            == "risk.recent_execution_failure_cooloff"
        )
