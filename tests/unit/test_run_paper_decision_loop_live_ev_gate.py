"""Unit tests: live spread/EV entry gate — F-1 crash regression.

See docs/design/project_wide_logic_audit_fable5_findings.md §3 F-1: the
live entry path read ``meta_result.adopted_ev_after_cost`` but
``MetaCycleRunResult`` had no such field, so the first adopted trade in
live mode raised AttributeError and the spread/EV gate never executed.

These tests prove (a) the field now exists and flows into the gate
without AttributeError, (b) a missing/invalid post-cost EV fails CLOSED
(no trade) instead of defaulting to 0.0, and (c) no adoption yields
``adopted_ev_after_cost=None`` without authorising a trade.

No credentials, broker, network, cloud, real data, or model training.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from fx_ai_trading.services.meta_cycle_runner import MetaCycleRunResult

_RUNNER_PATH = Path(__file__).resolve().parents[2] / "scripts" / "run_paper_decision_loop.py"
_spec = importlib.util.spec_from_file_location("paper_decision_runner_ev_gate", _RUNNER_PATH)
runner = importlib.util.module_from_spec(_spec)
sys.modules["paper_decision_runner_ev_gate"] = runner
assert _spec.loader is not None
_spec.loader.exec_module(runner)


def _make_result(*, adopted: bool, adopted_ev_after_cost: float | None) -> MetaCycleRunResult:
    return MetaCycleRunResult(
        cycle_id="cyc-f1",
        meta_decision_id="md-f1",
        adopted=adopted,
        trading_signal_id="ts-f1" if adopted else None,
        adopted_strategy_id="s-f1" if adopted else None,
        adopted_instrument="EUR_USD" if adopted else None,
        adopted_direction="buy" if adopted else None,
        candidate_count=1,
        trade_candidate_count=1 if adopted else 0,
        filtered_count=0,
        fallback_used=False,
        no_trade_event_count=0 if adopted else 1,
        adopted_ev_after_cost=adopted_ev_after_cost,
    )


class TestF1AttributeRegression:
    def test_adopted_result_field_reaches_gate_without_attribute_error(self) -> None:
        # Before the F-1 fix this attribute access raised AttributeError.
        r = _make_result(adopted=True, adopted_ev_after_cost=5.0)
        allow, reason = runner._evaluate_live_ev_gate(r.adopted_ev_after_cost, 1.0)
        assert allow is True
        assert reason == "ev_clears_spread"

    def test_dataclass_default_is_none_and_gate_fails_closed(self) -> None:
        # Constructors that predate the field get None, never 0.0 — and
        # the live gate must then block, not trade.
        r = MetaCycleRunResult(
            cycle_id="cyc-f1-default",
            meta_decision_id="md-f1-default",
            adopted=True,
            trading_signal_id="ts",
            adopted_strategy_id="s",
            adopted_instrument="EUR_USD",
            adopted_direction="buy",
            candidate_count=1,
            trade_candidate_count=1,
            filtered_count=0,
            fallback_used=False,
            no_trade_event_count=0,
        )
        assert r.adopted_ev_after_cost is None
        allow, reason = runner._evaluate_live_ev_gate(r.adopted_ev_after_cost, 1.0)
        assert allow is False
        assert reason == "ev_missing_fail_closed"

    def test_no_adoption_yields_none_without_trade_authorisation(self) -> None:
        r = _make_result(adopted=False, adopted_ev_after_cost=None)
        assert r.adopted is False
        assert r.adopted_ev_after_cost is None
        allow, _ = runner._evaluate_live_ev_gate(r.adopted_ev_after_cost, 0.8)
        assert allow is False


class TestLiveEvGateDecision:
    def test_missing_ev_fails_closed(self) -> None:
        assert runner._evaluate_live_ev_gate(None, 1.0) == (False, "ev_missing_fail_closed")

    def test_non_finite_ev_fails_closed(self) -> None:
        assert runner._evaluate_live_ev_gate(float("nan"), 1.0) == (
            False,
            "ev_missing_fail_closed",
        )
        assert runner._evaluate_live_ev_gate(float("inf"), 1.0) == (
            False,
            "ev_missing_fail_closed",
        )

    def test_spread_eats_ev_blocks(self) -> None:
        assert runner._evaluate_live_ev_gate(1.0, 1.0) == (False, "spread_eats_ev")
        assert runner._evaluate_live_ev_gate(0.5, 1.0) == (False, "spread_eats_ev")

    def test_positive_net_ev_allows(self) -> None:
        assert runner._evaluate_live_ev_gate(2.0, 1.0) == (True, "ev_clears_spread")

    def test_no_spread_quote_preserves_preexisting_fail_open(self) -> None:
        # Pricing endpoint unavailable — gate cannot evaluate; unchanged
        # pre-existing behaviour (documented in _fetch_live_quote).
        assert runner._evaluate_live_ev_gate(None, None) == (True, "no_spread_quote")
        assert runner._evaluate_live_ev_gate(5.0, None) == (True, "no_spread_quote")
