"""MetaDeciderService — Filter → Score → Select consensus (D3 §2.4.4 / M9).

Implements the MetaDecider Protocol.

3-stage pipeline (M9 minimum rule set):

  Filter:
    1. Remove 'no_trade' signals.
    2. If EventCalendar is stale → no_trade (all candidates removed; 6.3 invariant).
    3. Remove candidates near a high-impact economic event (within near_event_minutes).
    4. Remove candidates flagged by PriceAnomalyGuard.

  Score:
    score = ev_before_cost * confidence  (simple multiplicative score)

  Select:
    Highest-scoring remaining candidate wins.
    If none remain → no_trade with reasons.

MetaDecider does NOT apply:
  - Risk sizing (M10: PositionSizer / RiskManager).
  - Execution gating (M10: ExecutionGate / TTL).
  - Correlation regime tightening enforcement (Phase 7).
  - DB writes (done by evaluation framework, not here).
"""

from __future__ import annotations

import logging
import uuid
from uuid import UUID

from fx_ai_trading.domain.event_calendar import EventCalendar
from fx_ai_trading.domain.meta import MetaContext, MetaDecision, NoTradeReason
from fx_ai_trading.domain.price_anomaly import PriceAnomalyGuard
from fx_ai_trading.domain.strategy import StrategySignal

_log = logging.getLogger(__name__)

# Default minimum EV to proceed (filters near-zero or negative EV candidates).
_DEFAULT_MIN_EV = 0.0

# Default window for near-event filtering in minutes.
_DEFAULT_NEAR_EVENT_MINUTES = 60


class MetaDeciderService:
    """Filter → Score → Select MetaDecider for M9.

    Args:
        event_calendar: Optional EventCalendar for near-event filtering and
            stale failsafe. If None, stale and near-event checks are skipped.
        price_anomaly_guard: Optional PriceAnomalyGuard for flash-halt detection.
            If None, anomaly check is skipped.
        min_ev: Minimum ev_before_cost required to pass the Score stage.
            Candidates with ev_before_cost <= min_ev are filtered out.
        near_event_minutes: High-impact events within this window filter a candidate.
    """

    def __init__(
        self,
        event_calendar: EventCalendar | None = None,
        price_anomaly_guard: PriceAnomalyGuard | None = None,
        min_ev: float = _DEFAULT_MIN_EV,
        near_event_minutes: int = _DEFAULT_NEAR_EVENT_MINUTES,
    ) -> None:
        self._calendar = event_calendar
        self._anomaly_guard = price_anomaly_guard
        self._min_ev = min_ev
        self._near_event_minutes = near_event_minutes

    def decide(
        self,
        candidates: list[StrategySignal],
        context: MetaContext,
    ) -> MetaDecision:
        """Run 3-stage consensus over *candidates* and return a MetaDecision."""
        decision_id = uuid.uuid4()

        filter_result = self._filter(candidates, context)
        filtered = filter_result["remaining"]
        filter_reasons: list[NoTradeReason] = filter_result["reasons"]
        filter_snapshot: dict = filter_result["snapshot"]

        if not filtered:
            return self._no_trade(
                decision_id,
                context,
                reasons=tuple(filter_reasons),
                filter_snapshot=filter_snapshot,
            )

        score_result = self._score(filtered)
        scored = score_result["scored"]
        score_contributions: tuple[dict, ...] = score_result["contributions"]
        score_snapshot: dict = score_result["snapshot"]

        return self._select(
            decision_id,
            context,
            scored=scored,
            score_contributions=score_contributions,
            filter_snapshot=filter_snapshot,
            score_snapshot=score_snapshot,
        )

    # ------------------------------------------------------------------
    # Stage 1 — Filter
    # ------------------------------------------------------------------

    def _filter(
        self,
        candidates: list[StrategySignal],
        context: MetaContext,
    ) -> dict:
        reasons: list[NoTradeReason] = []
        remaining: list[StrategySignal] = []
        filter_log: dict[str, list[str]] = {}

        # Rule F1: stale calendar → all no_trade
        if self._calendar is not None and self._calendar.is_stale():
            _log.warning("MetaDeciderService: EventCalendar is stale → no_trade (6.3)")
            detail = "EventCalendar exceeded max staleness"
            return {
                "remaining": [],
                "reasons": [NoTradeReason(reason_code="CALENDAR_STALE", detail=detail)],
                "snapshot": {
                    "rule": "calendar_stale",
                    "candidates_in": len(candidates),
                    "passed": 0,
                },
            }

        for sig in candidates:
            rejected_by: list[str] = []

            # Rule F2: explicit no_trade signal
            if sig.signal == "no_trade":
                rejected_by.append("signal_no_trade")

            # Rule F3: near high-impact economic event
            if not rejected_by and self._calendar is not None:
                currency = _instrument_to_currency(sig.strategy_id)
                upcoming = self._calendar.get_upcoming(currency, self._near_event_minutes)
                if upcoming:
                    rejected_by.append("near_event")

            # Rule F4: price anomaly
            if not rejected_by and self._anomaly_guard is not None:
                instrument = _strategy_id_to_instrument(sig.strategy_id)
                if self._anomaly_guard.is_anomaly(instrument):
                    rejected_by.append("price_anomaly")

            if rejected_by:
                filter_log[sig.strategy_id] = rejected_by
                for rule in rejected_by:
                    reasons.append(NoTradeReason(reason_code=rule.upper(), detail=sig.strategy_id))
            else:
                remaining.append(sig)

        return {
            "remaining": remaining,
            "reasons": reasons,
            "snapshot": {
                "candidates_in": len(candidates),
                "passed": len(remaining),
                "rejected": filter_log,
            },
        }

    # ------------------------------------------------------------------
    # Stage 2 — Score
    # ------------------------------------------------------------------

    def _score(self, candidates: list[StrategySignal]) -> dict:
        scored: list[tuple[float, StrategySignal]] = []
        contributions: list[dict] = []

        for sig in candidates:
            score = sig.ev_before_cost * sig.confidence
            scored.append((score, sig))

        scored.sort(key=lambda x: x[0], reverse=True)

        for score, sig in scored:
            contributions.append(
                {
                    "strategy_id": sig.strategy_id,
                    "score": round(score, 8),
                    "ev_before_cost": sig.ev_before_cost,
                    "confidence": sig.confidence,
                }
            )

        return {
            "scored": scored,
            "contributions": tuple(contributions),
            "snapshot": {
                "candidates_scored": len(scored),
                "top_score": round(scored[0][0], 8) if scored else None,
            },
        }

    # ------------------------------------------------------------------
    # Stage 3 — Select
    # ------------------------------------------------------------------

    def _select(
        self,
        decision_id: UUID,
        context: MetaContext,
        scored: list[tuple[float, StrategySignal]],
        score_contributions: tuple[dict, ...],
        filter_snapshot: dict,
        score_snapshot: dict,
    ) -> MetaDecision:
        if not scored:
            return self._no_trade(
                decision_id,
                context,
                reasons=(NoTradeReason(reason_code="NO_SCORED_CANDIDATES"),),
                filter_snapshot=filter_snapshot,
            )

        best_score, best_sig = scored[0]

        # Min-EV gate
        if best_sig.ev_before_cost <= self._min_ev:
            ev_detail = str(best_sig.ev_before_cost)
            return self._no_trade(
                decision_id,
                context,
                reasons=(NoTradeReason(reason_code="EV_BELOW_THRESHOLD", detail=ev_detail),),
                filter_snapshot=filter_snapshot,
                score_snapshot=score_snapshot,
                score_contributions=score_contributions,
            )

        active = tuple(s.strategy_id for _, s in scored)
        instrument = _strategy_id_to_instrument(best_sig.strategy_id)

        return MetaDecision(
            meta_decision_id=decision_id,
            cycle_id=context.cycle_id,
            no_trade=False,
            active_strategies=active,
            regime_detected=False,
            filter_snapshot=filter_snapshot,
            score_snapshot=score_snapshot,
            select_snapshot={
                "selected_strategy_id": best_sig.strategy_id,
                "score": round(best_score, 8),
            },
            score_contributions=score_contributions,
            concentration_warning=len(scored) == 1,
            no_trade_reasons=(),
            selected_instrument=instrument,
            selected_strategy_id=best_sig.strategy_id,
            selected_signal=best_sig.signal,
            selected_tp=best_sig.tp,
            selected_sl=best_sig.sl,
        )

    def _no_trade(
        self,
        decision_id: UUID,
        context: MetaContext,
        reasons: tuple[NoTradeReason, ...],
        filter_snapshot: dict | None = None,
        score_snapshot: dict | None = None,
        score_contributions: tuple[dict, ...] = (),
    ) -> MetaDecision:
        return MetaDecision(
            meta_decision_id=decision_id,
            cycle_id=context.cycle_id,
            no_trade=True,
            active_strategies=(),
            regime_detected=False,
            filter_snapshot=filter_snapshot or {},
            score_snapshot=score_snapshot or {},
            select_snapshot={"reason": "no_trade"},
            score_contributions=score_contributions,
            concentration_warning=False,
            no_trade_reasons=reasons,
            selected_instrument=None,
            selected_strategy_id=None,
            selected_signal=None,
            selected_tp=None,
            selected_sl=None,
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _instrument_to_currency(strategy_id: str) -> str:
    """Extract a currency hint from a strategy_id for near-event filtering.

    M9: returns the strategy_id itself as-is; real currency mapping is M10+.
    EventCalendar.get_upcoming() receives this; if no events match, returns [].
    """
    return strategy_id


def _strategy_id_to_instrument(strategy_id: str) -> str:
    """Extract instrument from a strategy_id.

    M9: returns strategy_id as instrument placeholder.
    Real instrument resolution is part of the evaluation framework (M10).
    """
    return strategy_id
