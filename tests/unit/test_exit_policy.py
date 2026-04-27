"""Unit tests: ExitPolicyService rule evaluation (M14 / M-EXIT-1)."""

from __future__ import annotations

from fx_ai_trading.services.exit_policy import ExitPolicyService

_LONG = "long"
_SHORT = "short"


def _make_service(max_holding_seconds: int = 86400) -> ExitPolicyService:
    return ExitPolicyService(max_holding_seconds=max_holding_seconds)


def _evaluate(
    service: ExitPolicyService,
    *,
    side: str = _LONG,
    current_price: float = 1.1000,
    tp: float | None = None,
    sl: float | None = None,
    holding_seconds: int = 0,
    context: dict | None = None,
):
    return service.evaluate(
        position_id="pos-1",
        instrument="EUR_USD",
        side=side,
        current_price=current_price,
        tp=tp,
        sl=sl,
        holding_seconds=holding_seconds,
        context=context or {},
    )


class TestNoExit:
    def test_no_rules_triggered_returns_should_exit_false(self) -> None:
        svc = _make_service()
        d = _evaluate(svc, current_price=1.1000, tp=1.1100, sl=1.0900)
        assert d.should_exit is False
        assert d.reasons == ()
        assert d.primary_reason is None

    def test_no_exit_with_empty_context(self) -> None:
        svc = _make_service()
        d = _evaluate(svc)
        assert d.should_exit is False


class TestEmergencyStop:
    def test_emergency_stop_true_triggers_exit(self) -> None:
        svc = _make_service()
        d = _evaluate(svc, context={"emergency_stop": True})
        assert d.should_exit is True
        assert "emergency_stop" in d.reasons
        assert d.primary_reason == "emergency_stop"

    def test_emergency_stop_false_does_not_trigger(self) -> None:
        svc = _make_service()
        d = _evaluate(svc, context={"emergency_stop": False})
        assert d.should_exit is False

    def test_emergency_stop_is_highest_priority(self) -> None:
        svc = _make_service()
        d = _evaluate(
            svc,
            side=_LONG,
            current_price=1.0850,
            sl=1.0900,
            tp=1.0800,
            context={"emergency_stop": True},
        )
        assert d.reasons[0] == "emergency_stop"


class TestStopLoss:
    def test_long_sl_hit_exact(self) -> None:
        svc = _make_service()
        d = _evaluate(svc, side=_LONG, current_price=1.0900, sl=1.0900)
        assert d.should_exit is True
        assert "sl" in d.reasons

    def test_long_sl_breached_below(self) -> None:
        svc = _make_service()
        d = _evaluate(svc, side=_LONG, current_price=1.0850, sl=1.0900)
        assert d.should_exit is True
        assert "sl" in d.reasons

    def test_long_sl_not_breached(self) -> None:
        svc = _make_service()
        d = _evaluate(svc, side=_LONG, current_price=1.0950, sl=1.0900)
        assert "sl" not in d.reasons

    def test_short_sl_hit_exact(self) -> None:
        svc = _make_service()
        d = _evaluate(svc, side=_SHORT, current_price=1.1100, sl=1.1100)
        assert d.should_exit is True
        assert "sl" in d.reasons

    def test_short_sl_breached_above(self) -> None:
        svc = _make_service()
        d = _evaluate(svc, side=_SHORT, current_price=1.1150, sl=1.1100)
        assert d.should_exit is True
        assert "sl" in d.reasons

    def test_short_sl_not_breached(self) -> None:
        svc = _make_service()
        d = _evaluate(svc, side=_SHORT, current_price=1.1050, sl=1.1100)
        assert "sl" not in d.reasons

    def test_sl_none_never_triggers(self) -> None:
        svc = _make_service()
        d = _evaluate(svc, side=_LONG, current_price=0.0001, sl=None)
        assert "sl" not in d.reasons


class TestTakeProfit:
    def test_long_tp_hit_exact(self) -> None:
        svc = _make_service()
        d = _evaluate(svc, side=_LONG, current_price=1.1100, tp=1.1100)
        assert d.should_exit is True
        assert "tp" in d.reasons

    def test_long_tp_exceeded_above(self) -> None:
        svc = _make_service()
        d = _evaluate(svc, side=_LONG, current_price=1.1150, tp=1.1100)
        assert d.should_exit is True
        assert "tp" in d.reasons

    def test_long_tp_not_reached(self) -> None:
        svc = _make_service()
        d = _evaluate(svc, side=_LONG, current_price=1.1050, tp=1.1100)
        assert "tp" not in d.reasons

    def test_short_tp_hit_exact(self) -> None:
        svc = _make_service()
        d = _evaluate(svc, side=_SHORT, current_price=1.0900, tp=1.0900)
        assert d.should_exit is True
        assert "tp" in d.reasons

    def test_short_tp_breached_below(self) -> None:
        svc = _make_service()
        d = _evaluate(svc, side=_SHORT, current_price=1.0850, tp=1.0900)
        assert d.should_exit is True
        assert "tp" in d.reasons

    def test_short_tp_not_reached(self) -> None:
        svc = _make_service()
        d = _evaluate(svc, side=_SHORT, current_price=1.0950, tp=1.0900)
        assert "tp" not in d.reasons

    def test_tp_none_never_triggers(self) -> None:
        svc = _make_service()
        d = _evaluate(svc, side=_LONG, current_price=9999.0, tp=None)
        assert "tp" not in d.reasons


class TestMaxHoldingTime:
    def test_holding_time_exceeded_triggers_exit(self) -> None:
        svc = _make_service(max_holding_seconds=3600)
        d = _evaluate(svc, holding_seconds=3600)
        assert d.should_exit is True
        assert "max_holding_time" in d.reasons

    def test_holding_time_exceeded_above_threshold(self) -> None:
        svc = _make_service(max_holding_seconds=3600)
        d = _evaluate(svc, holding_seconds=7200)
        assert "max_holding_time" in d.reasons

    def test_holding_time_below_threshold_no_trigger(self) -> None:
        svc = _make_service(max_holding_seconds=3600)
        d = _evaluate(svc, holding_seconds=3599)
        assert "max_holding_time" not in d.reasons

    def test_holding_time_zero_no_trigger(self) -> None:
        svc = _make_service()
        d = _evaluate(svc, holding_seconds=0)
        assert "max_holding_time" not in d.reasons


class TestDecisionFields:
    def test_position_id_propagated(self) -> None:
        svc = _make_service()
        d = svc.evaluate("my-pos", "EUR_USD", _LONG, 1.1, None, None, 0, {})
        assert d.position_id == "my-pos"

    def test_tp_price_propagated(self) -> None:
        svc = _make_service()
        d = _evaluate(svc, tp=1.1200)
        assert d.tp_price == 1.1200

    def test_sl_price_propagated(self) -> None:
        svc = _make_service()
        d = _evaluate(svc, sl=1.0800)
        assert d.sl_price == 1.0800


# ---------------------------------------------------------------------------
# Phase 9.X: extended close reasons (§4.9.2)
# ---------------------------------------------------------------------------


class TestExtendedCloseReasons:
    """Context-dict driven close reasons added in Phase 9.X (§4.9.2)."""

    # ------------------------------------------------------------------
    # Each rule fires when its context key is True
    # ------------------------------------------------------------------

    def test_manual_close_triggers_exit(self) -> None:
        svc = _make_service()
        d = _evaluate(svc, context={"manual_close": True})
        assert d.should_exit is True
        assert d.primary_reason == "close.manual"

    def test_session_close_triggers_exit(self) -> None:
        svc = _make_service()
        d = _evaluate(svc, context={"session_close": True})
        assert d.should_exit is True
        assert d.primary_reason == "close.session_close"

    def test_news_pause_triggers_exit(self) -> None:
        svc = _make_service()
        d = _evaluate(svc, context={"near_event": True})
        assert d.should_exit is True
        assert d.primary_reason == "close.news_pause"

    def test_reverse_signal_triggers_exit(self) -> None:
        svc = _make_service()
        d = _evaluate(svc, context={"reverse_signal": True})
        assert d.should_exit is True
        assert d.primary_reason == "close.reverse_signal"

    def test_ev_decay_triggers_exit(self) -> None:
        svc = _make_service()
        d = _evaluate(svc, context={"ev_decay": True})
        assert d.should_exit is True
        assert d.primary_reason == "close.ev_decay"

    def test_absent_context_keys_do_not_fire(self) -> None:
        svc = _make_service()
        d = _evaluate(svc, context={})
        assert d.should_exit is False

    def test_false_context_keys_do_not_fire(self) -> None:
        svc = _make_service()
        d = _evaluate(
            svc,
            context={
                "manual_close": False,
                "session_close": False,
                "near_event": False,
                "reverse_signal": False,
                "ev_decay": False,
            },
        )
        assert d.should_exit is False

    # ------------------------------------------------------------------
    # Priority ordering among the new rules (§4.9.3)
    # ------------------------------------------------------------------

    def test_manual_beats_session_close(self) -> None:
        svc = _make_service()
        d = _evaluate(svc, context={"manual_close": True, "session_close": True})
        assert d.primary_reason == "close.manual"
        assert "close.session_close" in d.reasons

    def test_session_close_beats_sl(self) -> None:
        svc = _make_service()
        d = _evaluate(
            svc, side=_LONG, current_price=1.0900, sl=1.0900, context={"session_close": True}
        )
        assert d.primary_reason == "close.session_close"
        assert "sl" in d.reasons

    def test_sl_beats_news_pause(self) -> None:
        svc = _make_service()
        d = _evaluate(
            svc, side=_LONG, current_price=1.0900, sl=1.0900, context={"near_event": True}
        )
        assert d.primary_reason == "sl"
        assert "close.news_pause" in d.reasons

    def test_news_pause_beats_max_holding_time(self) -> None:
        svc = _make_service(max_holding_seconds=0)
        d = _evaluate(svc, holding_seconds=1, context={"near_event": True})
        assert d.primary_reason == "close.news_pause"
        assert "max_holding_time" in d.reasons

    def test_max_holding_time_beats_reverse_signal(self) -> None:
        svc = _make_service(max_holding_seconds=0)
        d = _evaluate(svc, holding_seconds=1, context={"reverse_signal": True})
        assert d.primary_reason == "max_holding_time"
        assert "close.reverse_signal" in d.reasons

    def test_reverse_signal_beats_ev_decay(self) -> None:
        svc = _make_service()
        d = _evaluate(svc, context={"reverse_signal": True, "ev_decay": True})
        assert d.primary_reason == "close.reverse_signal"
        assert "close.ev_decay" in d.reasons

    def test_all_nine_rules_fire_simultaneously(self) -> None:
        svc = _make_service(max_holding_seconds=0)
        d = _evaluate(
            svc,
            side=_LONG,
            current_price=1.0900,
            tp=1.0900,
            sl=1.0900,
            holding_seconds=1,
            context={
                "emergency_stop": True,
                "manual_close": True,
                "session_close": True,
                "near_event": True,
                "reverse_signal": True,
                "ev_decay": True,
            },
        )
        assert d.should_exit is True
        assert d.primary_reason == "emergency_stop"
        assert len(d.reasons) == 9
        # Full priority order check
        order = list(d.reasons)
        assert order == [
            "emergency_stop",
            "close.manual",
            "close.session_close",
            "sl",
            "tp",
            "close.news_pause",
            "max_holding_time",
            "close.reverse_signal",
            "close.ev_decay",
        ]
