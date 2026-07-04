"""Event-driven single-position-per-pair simulator tests."""

from __future__ import annotations

import pytest

from scripts.ml_step4.simulator import SimulatorError, TradeSignal, simulate


def test_overlapping_signal_ignored() -> None:
    signals = [
        TradeSignal("EUR_USD", entry=0, exit_=10, direction="long", pnl_pips=1.0),
        TradeSignal("EUR_USD", entry=5, exit_=15, direction="short", pnl_pips=2.0),
    ]
    out = simulate(signals)
    assert out["n_accepted"] == 1
    assert out["n_ignored"] == 1
    assert out["ignored_signals"][0]["reason"] == "pair_position_open"


def test_signal_accepted_after_exit() -> None:
    signals = [
        TradeSignal("EUR_USD", entry=0, exit_=10, direction="long", pnl_pips=1.0),
        TradeSignal("EUR_USD", entry=10, exit_=20, direction="long", pnl_pips=3.0),
    ]
    out = simulate(signals)
    assert out["n_accepted"] == 2
    assert out["n_ignored"] == 0


def test_per_pair_isolation() -> None:
    # Two pairs open concurrently is allowed (rule is per-pair, not portfolio).
    signals = [
        TradeSignal("EUR_USD", entry=0, exit_=10, direction="long", pnl_pips=1.0),
        TradeSignal("USD_JPY", entry=1, exit_=11, direction="short", pnl_pips=2.0),
        TradeSignal("USD_JPY", entry=2, exit_=12, direction="long", pnl_pips=9.0),  # blocked
    ]
    out = simulate(signals)
    assert out["n_accepted"] == 2
    accepted_pairs = sorted(t["pair"] for t in out["accepted_trades"])
    assert accepted_pairs == ["EUR_USD", "USD_JPY"]


def test_deterministic_order() -> None:
    a = simulate(
        [
            TradeSignal("B", entry=1, exit_=2, direction="long", pnl_pips=1.0),
            TradeSignal("A", entry=1, exit_=2, direction="short", pnl_pips=2.0),
        ]
    )
    b = simulate(
        [
            TradeSignal("A", entry=1, exit_=2, direction="short", pnl_pips=2.0),
            TradeSignal("B", entry=1, exit_=2, direction="long", pnl_pips=1.0),
        ]
    )
    assert a == b


def test_fail_closed_on_bad_interval() -> None:
    with pytest.raises(SimulatorError):
        simulate([TradeSignal("EUR_USD", entry=10, exit_=5, direction="long", pnl_pips=1.0)])


def test_fail_closed_on_missing_pair() -> None:
    with pytest.raises(SimulatorError):
        simulate([TradeSignal("", entry=0, exit_=1, direction="long", pnl_pips=1.0)])
