"""Contract tests: ExitPolicyService rule contracts (M14 / M-EXIT-1).

Verifies the public ExitPolicy contract:
  1. ExitPolicyService implements the ExitPolicy Protocol (structural).
  2. Core rules (emergency_stop / sl / tp / max_holding_time) return correct decisions.
  3. Priority ordering: emergency_stop > sl > tp > max_holding_time (core subset).
  4. Multiple rules can fire simultaneously; all enumerated in reasons.
  5. ExitDecision is frozen / immutable.
  6. should_exit=False when no rule fires.
  Phase 9.X: extended priority emergency_stop > manual > session_close > sl > tp
             > news_pause > max_holding_time > reverse_signal > ev_decay.
"""

from __future__ import annotations

import pytest

from fx_ai_trading.domain.exit import ExitDecision, ExitPolicy
from fx_ai_trading.services.exit_policy import ExitPolicyService

_LONG = "long"
_SHORT = "short"


class TestExitPolicyProtocolConformance:
    def test_service_satisfies_protocol(self) -> None:
        svc = ExitPolicyService()
        assert isinstance(svc, ExitPolicy)
        assert hasattr(svc, "evaluate")

    def test_evaluate_returns_exit_decision(self) -> None:
        svc = ExitPolicyService()
        result = svc.evaluate("p1", "EUR_USD", _LONG, 1.1, None, None, 0, {})
        assert isinstance(result, ExitDecision)

    def test_exit_decision_is_frozen(self) -> None:
        svc = ExitPolicyService()
        d = svc.evaluate("p1", "EUR_USD", _LONG, 1.1, None, None, 0, {})
        with pytest.raises((AttributeError, TypeError)):
            d.should_exit = True  # type: ignore[misc]


class TestRuleContracts:
    def test_emergency_stop_rule_fires_with_context_flag(self) -> None:
        svc = ExitPolicyService()
        d = svc.evaluate("p1", "EUR_USD", _LONG, 1.1, None, None, 0, {"emergency_stop": True})
        assert d.should_exit is True
        assert d.primary_reason == "emergency_stop"

    def test_sl_rule_fires_for_long_at_sl_price(self) -> None:
        svc = ExitPolicyService()
        d = svc.evaluate("p1", "EUR_USD", _LONG, 1.0900, None, 1.0900, 0, {})
        assert d.should_exit is True
        assert "sl" in d.reasons

    def test_tp_rule_fires_for_long_at_tp_price(self) -> None:
        svc = ExitPolicyService()
        d = svc.evaluate("p1", "EUR_USD", _LONG, 1.1100, 1.1100, None, 0, {})
        assert d.should_exit is True
        assert "tp" in d.reasons

    def test_max_holding_time_rule_fires_at_threshold(self) -> None:
        svc = ExitPolicyService(max_holding_seconds=3600)
        d = svc.evaluate("p1", "EUR_USD", _LONG, 1.1, None, None, 3600, {})
        assert d.should_exit is True
        assert "max_holding_time" in d.reasons

    def test_no_rule_fires_returns_false(self) -> None:
        svc = ExitPolicyService(max_holding_seconds=86400)
        d = svc.evaluate("p1", "EUR_USD", _LONG, 1.1050, 1.1100, 1.0900, 0, {})
        assert d.should_exit is False
        assert d.reasons == ()
        assert d.primary_reason is None


class TestPriorityOrdering:
    def test_emergency_stop_is_first_when_all_rules_fire(self) -> None:
        svc = ExitPolicyService(max_holding_seconds=0)
        d = svc.evaluate(
            "p1",
            "EUR_USD",
            _LONG,
            1.0850,
            1.0800,
            1.0900,
            999999,
            {"emergency_stop": True},
        )
        assert d.reasons[0] == "emergency_stop"
        assert d.primary_reason == "emergency_stop"

    def test_sl_before_tp_in_reasons(self) -> None:
        svc = ExitPolicyService()
        d = svc.evaluate("p1", "EUR_USD", _LONG, 1.0900, 1.0900, 1.0900, 0, {})
        sl_idx = d.reasons.index("sl")
        tp_idx = d.reasons.index("tp")
        assert sl_idx < tp_idx

    def test_tp_before_max_holding_in_reasons(self) -> None:
        svc = ExitPolicyService(max_holding_seconds=0)
        d = svc.evaluate("p1", "EUR_USD", _LONG, 1.1100, 1.1100, None, 1, {})
        tp_idx = d.reasons.index("tp")
        mht_idx = d.reasons.index("max_holding_time")
        assert tp_idx < mht_idx

    def test_multiple_reasons_all_enumerated(self) -> None:
        svc = ExitPolicyService(max_holding_seconds=0)
        d = svc.evaluate("p1", "EUR_USD", _LONG, 1.0900, 1.0900, 1.0900, 1, {})
        assert "sl" in d.reasons
        assert "tp" in d.reasons
        assert "max_holding_time" in d.reasons
        assert len(d.reasons) == 3
