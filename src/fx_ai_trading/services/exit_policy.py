"""ExitPolicyService — per-position exit decision engine (M14 / M-EXIT-1).

Implements the ExitPolicy Protocol from domain/exit.py.

Rule priority (high to low) per Phase 1 §4.9.3:
  1. emergency_stop   — context["emergency_stop"] is True
  2. manual           — context["manual_close"] is True (operator single-position close)
  3. session_close    — context["session_close"] is True (market closed / weekend)
  4. sl               — current_price breaches stop-loss level
  5. tp               — current_price breaches take-profit level
  6. news_pause       — context["near_event"] is True (event window proximity)
  7. max_holding_time — holding_seconds >= configured threshold
  8. reverse_signal   — context["reverse_signal"] is True (opposite-direction meta signal)
  9. ev_decay         — context["ev_decay"] is True (EV_after_cost < threshold)

Rules 2-3, 6, 8-9 are Phase 9.X additions (context-dict driven; fire only when
the corresponding context key is True — absent/False keys are silent no-ops).
All triggered rules are enumerated in ExitDecision.reasons in priority order.
The highest-priority triggered rule is ExitDecision.primary_reason.
"""

from __future__ import annotations

from fx_ai_trading.domain.exit import ExitDecision
from fx_ai_trading.domain.reason_codes import CloseReason, ExitCloseReason


class ExitPolicyService:
    """Concrete implementation of ExitPolicy for MVP scope.

    Args:
        max_holding_seconds: Positions held longer than this trigger
            max_holding_time exit (default 24 h = 86400 s).
    """

    def __init__(self, max_holding_seconds: int = 86400) -> None:
        self._max_holding_seconds = max_holding_seconds

    def evaluate(
        self,
        position_id: str,
        instrument: str,
        side: str,
        current_price: float,
        tp: float | None,
        sl: float | None,
        holding_seconds: int,
        context: dict,
    ) -> ExitDecision:
        """Evaluate whether *position_id* should be closed.

        Returns ExitDecision with should_exit=True and populated reasons
        if any rule fires.  Rules are checked in strict priority order so
        primary_reason always reflects the highest-priority trigger.
        """
        reasons: list[str] = []

        self._check_emergency_stop(reasons, context)
        self._check_manual(reasons, context)
        self._check_session_close(reasons, context)
        self._check_sl(reasons, side, current_price, sl)
        self._check_tp(reasons, side, current_price, tp)
        self._check_news_pause(reasons, context)
        self._check_max_holding_time(reasons, holding_seconds)
        self._check_reverse_signal(reasons, context)
        self._check_ev_decay(reasons, context)

        should_exit = bool(reasons)
        return ExitDecision(
            position_id=position_id,
            should_exit=should_exit,
            reasons=tuple(reasons),
            primary_reason=reasons[0] if reasons else None,
            tp_price=tp,
            sl_price=sl,
        )

    # ------------------------------------------------------------------
    # Rule checks — each appends to reasons when triggered
    # ------------------------------------------------------------------

    def _check_emergency_stop(self, reasons: list[str], context: dict) -> None:
        if context.get("emergency_stop"):
            reasons.append(CloseReason.EMERGENCY_STOP)

    def _check_manual(self, reasons: list[str], context: dict) -> None:
        if context.get("manual_close"):
            reasons.append(ExitCloseReason.MANUAL)

    def _check_session_close(self, reasons: list[str], context: dict) -> None:
        if context.get("session_close"):
            reasons.append(ExitCloseReason.SESSION_CLOSE)

    def _check_news_pause(self, reasons: list[str], context: dict) -> None:
        if context.get("near_event"):
            reasons.append(ExitCloseReason.NEWS_PAUSE)

    def _check_reverse_signal(self, reasons: list[str], context: dict) -> None:
        if context.get("reverse_signal"):
            reasons.append(ExitCloseReason.REVERSE_SIGNAL)

    def _check_ev_decay(self, reasons: list[str], context: dict) -> None:
        if context.get("ev_decay"):
            reasons.append(ExitCloseReason.EV_DECAY)

    def _check_sl(
        self, reasons: list[str], side: str, current_price: float, sl: float | None
    ) -> None:
        if sl is None:
            return
        if (side == "long" and current_price <= sl) or (side == "short" and current_price >= sl):
            reasons.append(CloseReason.SL)

    def _check_tp(
        self, reasons: list[str], side: str, current_price: float, tp: float | None
    ) -> None:
        if tp is None:
            return
        if (side == "long" and current_price >= tp) or (side == "short" and current_price <= tp):
            reasons.append(CloseReason.TP)

    def _check_max_holding_time(self, reasons: list[str], holding_seconds: int) -> None:
        if holding_seconds >= self._max_holding_seconds:
            reasons.append(CloseReason.MAX_HOLDING_TIME)
