"""ExitPolicyService — per-position exit decision engine (M14 / M-EXIT-1).

Implements the ExitPolicy Protocol from domain/exit.py.

Rule priority (high to low):
  1. emergency_stop  — context["emergency_stop"] is True
  2. sl              — current_price breaches stop-loss level
  3. tp              — current_price breaches take-profit level
  4. max_holding_time — holding_seconds >= configured threshold

All triggered rules are enumerated in ExitDecision.reasons in priority order.
The highest-priority triggered rule is ExitDecision.primary_reason.

Deferred to Phase 7:
  - reverse_signal / ev_decay / pre_event_halt (Interface prepared in domain/exit.py)
"""

from __future__ import annotations

from fx_ai_trading.domain.exit import ExitDecision


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
        self._check_sl(reasons, side, current_price, sl)
        self._check_tp(reasons, side, current_price, tp)
        self._check_max_holding_time(reasons, holding_seconds)

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
            reasons.append("emergency_stop")

    def _check_sl(
        self, reasons: list[str], side: str, current_price: float, sl: float | None
    ) -> None:
        if sl is None:
            return
        if (side == "long" and current_price <= sl) or (side == "short" and current_price >= sl):
            reasons.append("sl")

    def _check_tp(
        self, reasons: list[str], side: str, current_price: float, tp: float | None
    ) -> None:
        if tp is None:
            return
        if (side == "long" and current_price >= tp) or (side == "short" and current_price <= tp):
            reasons.append("tp")

    def _check_max_holding_time(self, reasons: list[str], holding_seconds: int) -> None:
        if holding_seconds >= self._max_holding_seconds:
            reasons.append("max_holding_time")
