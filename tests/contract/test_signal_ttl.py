"""Contract tests: ExecutionGate TTL invariant (D3 §2.6.2 / 6.15 / M10).

Invariant: signal_age_seconds > signal_ttl_seconds → Reject(SignalExpired).
TTL check is always the FIRST evaluation (before DeferExhausted, spread, etc.).

Tests:
  1. Signal within TTL → NOT SignalExpired (gate continues).
  2. Signal exactly at TTL boundary → NOT rejected (age == ttl is within limit).
  3. Signal 1s over TTL → Reject(SignalExpired).
  4. TTL-expired signal is rejected even when defer_count < threshold.
  5. TTL-expired signal is rejected even when spread is normal.
  6. TTL-expired signal is rejected even when broker is unreachable.
  7. signal_age_seconds is always present in GateResult.
  8. 14s signal with 15s TTL → approve path continues.
  9. 16s signal with 15s TTL → SignalExpired.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fx_ai_trading.common.clock import FixedClock
from fx_ai_trading.domain.execution import RealtimeContext, TradingIntent
from fx_ai_trading.services.execution_gate import ExecutionGateService

_SIGNAL_TTL = 15
_NOW = datetime(2024, 6, 1, 12, 0, 0, tzinfo=UTC)


def _make_intent(age_seconds: float) -> TradingIntent:
    return TradingIntent(
        trading_signal_id="sig001",
        order_id="ord001",
        account_id="acc001",
        instrument="EUR_USD",
        side="long",
        size_units=1000,
        tp=0.01,
        sl=0.005,
        signal_created_at=_NOW - timedelta(seconds=age_seconds),
    )


def _normal_context() -> RealtimeContext:
    return RealtimeContext(
        current_spread=0.00010,
        is_broker_reachable=True,
        checked_at=_NOW,
    )


def _gate(ttl: int = _SIGNAL_TTL) -> ExecutionGateService:
    return ExecutionGateService(
        signal_ttl_seconds=ttl,
        clock=FixedClock(_NOW),
    )


class TestSignalTTLContract:
    def test_within_ttl_not_signal_expired(self) -> None:
        """Signal 10s old with 15s TTL → does not produce SignalExpired."""
        gate = _gate()
        result = gate.check(_make_intent(10.0), _normal_context())
        assert result.reason_code != "SignalExpired"

    def test_exactly_at_ttl_not_rejected(self) -> None:
        """Signal exactly at TTL boundary (age == ttl) → not SignalExpired (strict >)."""
        gate = _gate()
        result = gate.check(_make_intent(float(_SIGNAL_TTL)), _normal_context())
        assert result.reason_code != "SignalExpired"

    def test_one_second_over_ttl_is_rejected(self) -> None:
        """Signal 1s past TTL → Reject(SignalExpired)."""
        gate = _gate()
        result = gate.check(_make_intent(_SIGNAL_TTL + 1.0), _normal_context())
        assert result.decision == "reject"
        assert result.reason_code == "SignalExpired"

    def test_ttl_rejected_before_defer_exhausted_check(self) -> None:
        """TTL check fires before DeferExhausted even with defer_count < threshold."""
        gate = _gate()
        # defer_count=0 < threshold=3, but signal is expired
        result = gate.check(_make_intent(_SIGNAL_TTL + 5.0), _normal_context(), defer_count=0)
        assert result.reason_code == "SignalExpired"

    def test_ttl_rejected_even_with_normal_spread(self) -> None:
        """TTL check fires before spread check."""
        gate = _gate()
        result = gate.check(_make_intent(_SIGNAL_TTL + 1.0), _normal_context())
        assert result.reason_code == "SignalExpired"

    def test_ttl_rejected_even_when_broker_unreachable(self) -> None:
        """TTL check fires before broker-reachability check."""
        gate = _gate()
        ctx = RealtimeContext(
            current_spread=0.00010,
            is_broker_reachable=False,
            checked_at=_NOW,
        )
        result = gate.check(_make_intent(_SIGNAL_TTL + 1.0), ctx)
        assert result.reason_code == "SignalExpired"

    def test_signal_age_always_present(self) -> None:
        """signal_age_seconds must be populated in every GateResult."""
        gate = _gate()
        for age in (0.0, 5.0, 15.0, 20.0):
            result = gate.check(_make_intent(age), _normal_context())
            assert isinstance(result.signal_age_seconds, float)
            assert result.signal_age_seconds >= 0.0

    def test_14s_signal_with_15s_ttl_not_expired(self) -> None:
        """14s signal with ttl=15 → gate continues (not SignalExpired)."""
        gate = _gate(ttl=15)
        result = gate.check(_make_intent(14.0), _normal_context())
        assert result.reason_code != "SignalExpired"

    def test_16s_signal_with_15s_ttl_is_expired(self) -> None:
        """16s signal with ttl=15 → Reject(SignalExpired)."""
        gate = _gate(ttl=15)
        result = gate.check(_make_intent(16.0), _normal_context())
        assert result.decision == "reject"
        assert result.reason_code == "SignalExpired"
