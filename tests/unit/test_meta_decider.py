"""Unit tests: MetaDeciderService 3-stage pipeline (D3 §2.4.4 / M9).

Invariants:
  - no_trade == True  ↔  selected_instrument is None
  - MetaDecision is always returned (never raises)
  - Filter → Score → Select stages are independent
  - EventCalendar stale → no_trade regardless of candidates (6.3 invariant)
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from fx_ai_trading.common.clock import FixedClock
from fx_ai_trading.domain.event_calendar import EconomicEvent
from fx_ai_trading.domain.meta import MetaContext, MetaDecision
from fx_ai_trading.domain.strategy import StrategySignal
from fx_ai_trading.services.event_calendar import EventCalendarService
from fx_ai_trading.services.meta_decider import MetaDeciderService


def _make_signal(
    strategy_id: str = "strat_a",
    signal: str = "long",
    confidence: float = 0.6,
    ev_before_cost: float = 0.002,
    tp: float = 0.01,
    sl: float = 0.005,
) -> StrategySignal:
    return StrategySignal(
        strategy_id=strategy_id,
        strategy_type="test",
        strategy_version="v1",
        signal=signal,
        confidence=confidence,
        ev_before_cost=ev_before_cost,
        ev_after_cost=ev_before_cost,
        tp=tp,
        sl=sl,
        holding_time_seconds=3600,
        enabled=True,
    )


_NOW = datetime(2024, 6, 1, 12, 0, 0, tzinfo=UTC)

_CTX = MetaContext(
    cycle_id=uuid4(),
    account_id="acc001",
    config_version="test-v1",
)


@pytest.fixture()
def decider() -> MetaDeciderService:
    return MetaDeciderService()


class TestMetaDeciderInvariants:
    def test_no_trade_iff_selected_instrument_none(self, decider: MetaDeciderService) -> None:
        """Invariant: no_trade == True ↔ selected_instrument is None."""
        # With no candidates
        decision = decider.decide([], _CTX)
        assert decision.no_trade is True
        assert decision.selected_instrument is None

        # With a valid candidate
        decision2 = decider.decide([_make_signal()], _CTX)
        assert decision2.no_trade is False
        assert decision2.selected_instrument is not None

    def test_always_returns_meta_decision(self, decider: MetaDeciderService) -> None:
        """decide() must always return a MetaDecision, never raise."""
        decision = decider.decide([], _CTX)
        assert isinstance(decision, MetaDecision)

    def test_cycle_id_propagated(self, decider: MetaDeciderService) -> None:
        """cycle_id from context must be propagated to MetaDecision."""
        decision = decider.decide([_make_signal()], _CTX)
        assert decision.cycle_id == _CTX.cycle_id


class TestMetaDeciderFilter:
    def test_empty_candidates_produces_no_trade(self, decider: MetaDeciderService) -> None:
        decision = decider.decide([], _CTX)
        assert decision.no_trade is True

    def test_all_no_trade_signals_filtered(self, decider: MetaDeciderService) -> None:
        candidates = [
            _make_signal("a", signal="no_trade"),
            _make_signal("b", signal="no_trade"),
        ]
        decision = decider.decide(candidates, _CTX)
        assert decision.no_trade is True
        reason_codes = {r.reason_code for r in decision.no_trade_reasons}
        assert "SIGNAL_NO_TRADE" in reason_codes

    def test_stale_calendar_triggers_no_trade(self) -> None:
        """Stale EventCalendar → no_trade with CALENDAR_STALE reason (6.3)."""
        stale_clock = FixedClock(datetime(2025, 1, 1, tzinfo=UTC))
        # last_updated_at far in the past → stale immediately
        calendar = EventCalendarService(
            last_updated_at=datetime(2020, 1, 1, tzinfo=UTC),
            max_staleness_hours=24,
            clock=stale_clock,
        )
        decider = MetaDeciderService(event_calendar=calendar)
        decision = decider.decide([_make_signal()], _CTX)

        assert decision.no_trade is True
        reason_codes = {r.reason_code for r in decision.no_trade_reasons}
        assert "CALENDAR_STALE" in reason_codes

    def test_near_event_filters_candidate(self) -> None:
        """High-impact event within 60 min for matching currency → candidate filtered."""
        event_time = _NOW + timedelta(minutes=30)
        event = EconomicEvent(
            event_id="evt001",
            currency="strat_a",
            title="NFP",
            impact="high",
            scheduled_utc=event_time,
        )
        fixed_clock = FixedClock(_NOW)
        calendar = EventCalendarService(
            events=[event],
            last_updated_at=_NOW,
            max_staleness_hours=24,
            clock=fixed_clock,
        )
        decider = MetaDeciderService(event_calendar=calendar)
        decision = decider.decide([_make_signal("strat_a")], _CTX)
        assert decision.no_trade is True

    def test_price_anomaly_filters_candidate(self) -> None:
        """PriceAnomalyGuard.is_anomaly() = True → candidate filtered."""

        class _AlwaysAnomalous:
            def is_anomaly(self, instrument: str) -> bool:
                return True

            def record(self, instrument: str, atr: float) -> None:
                pass

        decider = MetaDeciderService(price_anomaly_guard=_AlwaysAnomalous())
        decision = decider.decide([_make_signal()], _CTX)
        assert decision.no_trade is True


class TestMetaDeciderScore:
    def test_highest_score_selected(self, decider: MetaDeciderService) -> None:
        """Multiple candidates: highest ev_after_cost * confidence wins (Phase 1 I-5)."""
        # strat_b: score = 0.003 * 0.9 = 0.0027 > strat_a: score = 0.002 * 0.6 = 0.0012
        candidates = [
            _make_signal("strat_a", confidence=0.6, ev_before_cost=0.002),
            _make_signal("strat_b", confidence=0.9, ev_before_cost=0.003),
        ]
        decision = decider.decide(candidates, _CTX)
        assert decision.no_trade is False
        assert decision.selected_strategy_id == "strat_b"

    def test_score_contributions_recorded(self, decider: MetaDeciderService) -> None:
        """score_contributions must be populated for each candidate that passes filter."""
        candidates = [_make_signal("a"), _make_signal("b")]
        decision = decider.decide(candidates, _CTX)
        assert len(decision.score_contributions) == 2
        ids = {c["strategy_id"] for c in decision.score_contributions}
        assert "a" in ids
        assert "b" in ids

    def test_active_strategies_recorded(self, decider: MetaDeciderService) -> None:
        """active_strategies must list all candidates that passed filter."""
        candidates = [_make_signal("a"), _make_signal("b")]
        decision = decider.decide(candidates, _CTX)
        assert "a" in decision.active_strategies
        assert "b" in decision.active_strategies


class TestMetaDeciderSelect:
    def test_single_valid_candidate_selected(self, decider: MetaDeciderService) -> None:
        sig = _make_signal("strat_x", signal="short", ev_before_cost=0.005)
        decision = decider.decide([sig], _CTX)
        assert decision.no_trade is False
        assert decision.selected_signal == "short"
        assert decision.selected_tp == sig.tp
        assert decision.selected_sl == sig.sl

    def test_concentration_warning_when_single_candidate(self, decider: MetaDeciderService) -> None:
        """concentration_warning must be True when only 1 strategy passes."""
        decision = decider.decide([_make_signal()], _CTX)
        assert decision.concentration_warning is True

    def test_no_concentration_warning_with_multiple_candidates(
        self, decider: MetaDeciderService
    ) -> None:
        candidates = [_make_signal("a"), _make_signal("b")]
        decision = decider.decide(candidates, _CTX)
        assert decision.concentration_warning is False

    def test_regime_detected_false_in_m9(self, decider: MetaDeciderService) -> None:
        """regime_detected must be False in M9 (Phase 7 adds real regime logic)."""
        decision = decider.decide([_make_signal()], _CTX)
        assert decision.regime_detected is False

    def test_no_trade_when_min_ev_not_met(self) -> None:
        """Candidate with ev_after_cost <= min_ev → no_trade (EV_BELOW_THRESHOLD)."""
        decider = MetaDeciderService(min_ev=0.01)
        # ev_after_cost=0.002 (== ev_before_cost in fixture) < min_ev=0.01
        decision = decider.decide([_make_signal(ev_before_cost=0.002)], _CTX)
        assert decision.no_trade is True
        reason_codes = {r.reason_code for r in decision.no_trade_reasons}
        assert "EV_BELOW_THRESHOLD" in reason_codes


class TestMetaDeciderRuleF5CSI:
    """Phase 9.3: Rule F5 — CSI strength filter."""

    def _ctx_with_strength(self, strength: dict[str, float]) -> MetaContext:
        return MetaContext(
            cycle_id=_CTX.cycle_id,
            account_id=_CTX.account_id,
            config_version=_CTX.config_version,
            currency_strength=strength,
        )

    def test_no_currency_strength_skips_rule(self) -> None:
        """currency_strength=None in context → Rule F5 is not applied."""
        decider = MetaDeciderService(min_csi_diff=9999.0)
        # min_csi_diff is extremely large, but strength is None → rule skipped → trade.
        decision = decider.decide([_make_signal("EUR_USD")], _CTX)
        assert decision.no_trade is False

    def test_sufficient_strength_diff_passes(self) -> None:
        """|EUR - USD| = 1.5 >= min_csi_diff=0.5 → candidate passes."""
        ctx = self._ctx_with_strength({"EUR": 1.2, "USD": -0.3})
        decider = MetaDeciderService(min_csi_diff=0.5)
        decision = decider.decide([_make_signal("EUR_USD")], ctx)
        assert decision.no_trade is False

    def test_insufficient_strength_diff_filters_candidate(self) -> None:
        """|EUR - USD| = 0.1 < min_csi_diff=0.5 → no_trade with CSI_STRENGTH_WEAK."""
        ctx = self._ctx_with_strength({"EUR": 0.05, "USD": -0.05})
        decider = MetaDeciderService(min_csi_diff=0.5)
        decision = decider.decide([_make_signal("EUR_USD")], ctx)
        assert decision.no_trade is True
        reason_codes = {r.reason_code for r in decision.no_trade_reasons}
        assert "meta.csi_strength_weak" in reason_codes

    def test_missing_currency_in_strength_passes(self) -> None:
        """Currency absent from strength dict → Rule F5 passes (no data = no block)."""
        ctx = self._ctx_with_strength({"EUR": 1.2})  # USD missing
        decider = MetaDeciderService(min_csi_diff=0.5)
        decision = decider.decide([_make_signal("EUR_USD")], ctx)
        assert decision.no_trade is False

    def test_non_pair_instrument_passes(self) -> None:
        """Non-``A_B`` strategy_id → Rule F5 passes silently."""
        ctx = self._ctx_with_strength({"EUR": 1.2, "USD": -0.3})
        decider = MetaDeciderService(min_csi_diff=0.5)
        decision = decider.decide([_make_signal("strat_a")], ctx)
        # "strat" and "a" not in strength → passes
        assert decision.no_trade is False

    def test_multiple_candidates_partial_filter(self) -> None:
        """Strong EUR_USD passes; weak GBP_JPY is filtered by CSI."""
        ctx = self._ctx_with_strength({"EUR": 1.5, "USD": -0.5, "GBP": 0.1, "JPY": 0.05})
        decider = MetaDeciderService(min_csi_diff=0.5)
        candidates = [_make_signal("EUR_USD"), _make_signal("GBP_JPY")]
        decision = decider.decide(candidates, ctx)
        assert decision.no_trade is False
        assert decision.selected_instrument == "EUR_USD"
