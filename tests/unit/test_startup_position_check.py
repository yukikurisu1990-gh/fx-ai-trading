"""Unit tests: check_position_integrity (startup position drift detection)."""

from __future__ import annotations

import pytest

from fx_ai_trading.services.startup_position_check import (
    PositionMismatchError,
    check_position_integrity,
)


class TestNoMismatch:
    def test_empty_db_no_broker_returns_ok(self) -> None:
        r = check_position_integrity(frozenset())
        assert not r.has_mismatch
        assert not r.broker_queried
        assert r.db_instruments == frozenset()
        assert r.broker_instruments is None

    def test_db_positions_no_broker_returns_ok(self) -> None:
        r = check_position_integrity(frozenset({"EUR_USD", "USD_JPY"}))
        assert not r.has_mismatch
        assert r.db_only == frozenset()
        assert r.broker_only == frozenset()

    def test_db_matches_broker_returns_ok(self) -> None:
        instr = frozenset({"EUR_USD", "GBP_USD"})
        r = check_position_integrity(instr, instr)
        assert not r.has_mismatch
        assert r.db_only == frozenset()
        assert r.broker_only == frozenset()

    def test_both_empty_with_broker_returns_ok(self) -> None:
        r = check_position_integrity(frozenset(), frozenset())
        assert not r.has_mismatch


class TestDbOnly:
    def test_db_position_not_at_broker(self) -> None:
        r = check_position_integrity(
            frozenset({"EUR_USD"}),
            frozenset(),
        )
        assert r.has_mismatch
        assert r.db_only == frozenset({"EUR_USD"})
        assert r.broker_only == frozenset()

    def test_multiple_db_only(self) -> None:
        r = check_position_integrity(
            frozenset({"EUR_USD", "USD_JPY", "GBP_USD"}),
            frozenset({"GBP_USD"}),
        )
        assert r.db_only == frozenset({"EUR_USD", "USD_JPY"})
        assert r.broker_only == frozenset()


class TestBrokerOnly:
    def test_broker_position_not_in_db(self) -> None:
        r = check_position_integrity(
            frozenset(),
            frozenset({"EUR_USD"}),
        )
        assert r.has_mismatch
        assert r.broker_only == frozenset({"EUR_USD"})
        assert r.db_only == frozenset()

    def test_multiple_broker_only(self) -> None:
        r = check_position_integrity(
            frozenset({"GBP_USD"}),
            frozenset({"EUR_USD", "USD_JPY", "GBP_USD"}),
        )
        assert r.broker_only == frozenset({"EUR_USD", "USD_JPY"})
        assert r.db_only == frozenset()


class TestBothMismatch:
    def test_db_only_and_broker_only(self) -> None:
        r = check_position_integrity(
            frozenset({"EUR_USD"}),
            frozenset({"USD_JPY"}),
        )
        assert r.has_mismatch
        assert r.db_only == frozenset({"EUR_USD"})
        assert r.broker_only == frozenset({"USD_JPY"})


class TestHaltOnMismatch:
    def test_no_mismatch_does_not_raise(self) -> None:
        check_position_integrity(
            frozenset({"EUR_USD"}),
            frozenset({"EUR_USD"}),
            halt_on_mismatch=True,
        )

    def test_mismatch_raises_when_halt_true(self) -> None:
        with pytest.raises(PositionMismatchError):
            check_position_integrity(
                frozenset({"EUR_USD"}),
                frozenset(),
                halt_on_mismatch=True,
            )

    def test_mismatch_no_raise_when_halt_false(self) -> None:
        r = check_position_integrity(
            frozenset({"EUR_USD"}),
            frozenset(),
            halt_on_mismatch=False,
        )
        assert r.has_mismatch

    def test_broker_only_raises_with_halt(self) -> None:
        with pytest.raises(PositionMismatchError, match="broker_only"):
            check_position_integrity(
                frozenset(),
                frozenset({"USD_JPY"}),
                halt_on_mismatch=True,
            )


class TestBrokerQueried:
    def test_broker_not_queried_when_none(self) -> None:
        r = check_position_integrity(frozenset(), None)
        assert not r.broker_queried

    def test_broker_queried_when_provided(self) -> None:
        r = check_position_integrity(frozenset(), frozenset())
        assert r.broker_queried
