"""Contract tests: ExecutionGate DeferExhausted invariant (D3 §2.6.2 / 6.15 / M10).

Invariant: when defer_count >= defer_exhausted_threshold AND signal is within TTL
→ Reject(DeferExhausted).

Tests:
  1. defer_count < threshold → not DeferExhausted.
  2. defer_count == threshold → DeferExhausted.
  3. defer_count > threshold → DeferExhausted.
  4. DeferExhausted only when signal is within TTL (expired → SignalExpired wins).
  5. Spread-wide signal defers (returns 'defer') when within TTL and under threshold.
  6. defer_until is populated on Defer result.
  7. Threshold=3: counts 0, 1, 2 defer; count 3 triggers DeferExhausted.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fx_ai_trading.common.clock import FixedClock
from fx_ai_trading.domain.execution import RealtimeContext, TradingIntent
from fx_ai_trading.services.execution_gate import ExecutionGateService

_SIGNAL_TTL = 15
_DEFER_THRESHOLD = 3
_NOW = datetime(2024, 6, 1, 12, 0, 0, tzinfo=UTC)


def _make_intent(age_seconds: float = 5.0) -> TradingIntent:
    return TradingIntent(
        trading_signal_id="sig002",
        order_id="ord002",
        account_id="acc001",
        instrument="EUR_USD",
        side="long",
        size_units=1000,
        tp=0.01,
        sl=0.005,
        signal_created_at=_NOW - timedelta(seconds=age_seconds),
    )


def _wide_spread_context() -> RealtimeContext:
    """Spread above max_spread_pips to trigger Defer path."""
    return RealtimeContext(
        current_spread=0.99,
        is_broker_reachable=True,
        checked_at=_NOW,
    )


def _normal_context() -> RealtimeContext:
    return RealtimeContext(
        current_spread=0.00010,
        is_broker_reachable=True,
        checked_at=_NOW,
    )


def _gate(threshold: int = _DEFER_THRESHOLD) -> ExecutionGateService:
    return ExecutionGateService(
        signal_ttl_seconds=_SIGNAL_TTL,
        defer_exhausted_threshold=threshold,
        clock=FixedClock(_NOW),
    )


class TestDeferExhaustedContract:
    def test_below_threshold_not_exhausted(self) -> None:
        """defer_count < threshold → DeferExhausted not triggered."""
        gate = _gate()
        result = gate.check(_make_intent(), _normal_context(), defer_count=_DEFER_THRESHOLD - 1)
        assert result.reason_code != "DeferExhausted"

    def test_at_threshold_is_exhausted(self) -> None:
        """defer_count == threshold → Reject(DeferExhausted)."""
        gate = _gate()
        result = gate.check(_make_intent(), _normal_context(), defer_count=_DEFER_THRESHOLD)
        assert result.decision == "reject"
        assert result.reason_code == "DeferExhausted"

    def test_above_threshold_is_exhausted(self) -> None:
        """defer_count > threshold → Reject(DeferExhausted)."""
        gate = _gate()
        result = gate.check(_make_intent(), _normal_context(), defer_count=_DEFER_THRESHOLD + 5)
        assert result.decision == "reject"
        assert result.reason_code == "DeferExhausted"

    def test_ttl_expired_beats_defer_exhausted(self) -> None:
        """TTL-expired signal → SignalExpired even when defer_count >= threshold."""
        gate = _gate()
        result = gate.check(
            _make_intent(age_seconds=_SIGNAL_TTL + 1.0),
            _normal_context(),
            defer_count=_DEFER_THRESHOLD,
        )
        assert result.reason_code == "SignalExpired"

    def test_wide_spread_within_ttl_and_below_threshold_defers(self) -> None:
        """Within TTL, under threshold, wide spread → Defer (not reject)."""
        gate = _gate()
        result = gate.check(_make_intent(), _wide_spread_context(), defer_count=0)
        assert result.decision == "defer"
        assert result.reason_code == "SpreadTooWide"

    def test_defer_result_has_defer_until(self) -> None:
        """Defer result must include defer_until timestamp."""
        gate = _gate()
        result = gate.check(_make_intent(), _wide_spread_context(), defer_count=0)
        assert result.decision == "defer"
        assert result.defer_until is not None
        assert result.defer_until > _NOW

    def test_threshold_3_exhausted_at_count_3(self) -> None:
        """Default threshold=3: counts 0,1,2 are under threshold; 3 triggers exhausted."""
        gate = _gate(threshold=3)
        for count in (0, 1, 2):
            result = gate.check(_make_intent(), _normal_context(), defer_count=count)
            assert result.reason_code != "DeferExhausted", f"count={count} should not exhaust"
        result = gate.check(_make_intent(), _normal_context(), defer_count=3)
        assert result.reason_code == "DeferExhausted"
