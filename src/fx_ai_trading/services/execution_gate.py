"""ExecutionGateService — TTL-first signal gating (D3 §2.6.2 / 6.15 / M10).

Implements the ExecutionGate Protocol.

Check order (invariant: TTL is always first):
  Step 1 — TTL:             signal_age > signal_ttl_seconds → Reject(SignalExpired)
  Step 2 — DeferExhausted:  defer_count >= threshold        → Reject(DeferExhausted)
  Step 3 — SpreadTooWide:   spread > max_spread_pips        → Defer
  Step 4 — BrokerUnreachable: not reachable                 → Reject(BrokerUnreachable)
  Step 5 — Approve

Invariants (6.15):
  - TTL check is unconditionally the first evaluation.
  - TTL-exceeded signals cannot be Deferred (checked before Defer path).
  - signal_age_seconds is recorded in every GateResult.
  - No async, no polling, no while loop (M10 sync-only).

M12 TODO: write to execution_metrics table on every check() call.
"""

from __future__ import annotations

import logging
from datetime import timedelta

from fx_ai_trading.common.clock import Clock, WallClock
from fx_ai_trading.domain.execution import GateResult, RealtimeContext, TradingIntent
from fx_ai_trading.domain.reason_codes import GateReason

_log = logging.getLogger(__name__)

# Defaults from phase6_hardening.md §6.5
_DEFAULT_TTL_SECONDS = 15
_DEFAULT_DEFER_TIMEOUT_SECONDS = 5
_DEFAULT_DEFER_EXHAUSTED_THRESHOLD = 3
_DEFAULT_MAX_SPREAD = 0.0005  # 5 pips expressed in price units (EUR/USD: 1 pip = 0.0001)


class ExecutionGateService:
    """TTL-first execution gate for M10 paper mode.

    Evaluates trading intents against real-time conditions before order submission.

    Args:
        signal_ttl_seconds: Max allowed signal age in seconds (6.15, default 15).
        defer_exhausted_threshold: Max defer attempts before DeferExhausted (default 3).
        defer_timeout_seconds: Seconds to wait per defer cycle (default 5).
        max_spread_pips: Spread threshold in price units above which a Defer is issued
            (default 0.0005 = 5 pips for major pairs; 1 pip = 0.0001).
        clock: Injectable clock (WallClock in production, FixedClock in tests).
    """

    def __init__(
        self,
        signal_ttl_seconds: int = _DEFAULT_TTL_SECONDS,
        defer_exhausted_threshold: int = _DEFAULT_DEFER_EXHAUSTED_THRESHOLD,
        defer_timeout_seconds: int = _DEFAULT_DEFER_TIMEOUT_SECONDS,
        max_spread_pips: float = _DEFAULT_MAX_SPREAD,
        clock: Clock | None = None,
    ) -> None:
        self._ttl = signal_ttl_seconds
        self._defer_threshold = defer_exhausted_threshold
        self._defer_timeout = defer_timeout_seconds
        self._max_spread = max_spread_pips
        self._clock: Clock = clock if clock is not None else WallClock()

    def check(
        self,
        intent: TradingIntent,
        realtime_context: RealtimeContext,
        defer_count: int = 0,
    ) -> GateResult:
        """Evaluate intent against real-time conditions.

        Args:
            intent: Validated trading intent including signal_created_at.
            realtime_context: Market snapshot (spread, broker reachability).
            defer_count: Number of times this signal has been deferred already.

        Returns:
            GateResult with decision 'approve' | 'reject' | 'defer',
            signal_age_seconds (always present), and optional reason_code.
        """
        now = self._clock.now()
        signal_age_seconds = (now - intent.signal_created_at).total_seconds()

        # Step 1 — TTL (must be first, invariant from 6.15)
        if signal_age_seconds > self._ttl:
            _log.debug(
                "ExecutionGateService: SignalExpired age=%.2fs > ttl=%ds (%s)",
                signal_age_seconds,
                self._ttl,
                intent.trading_signal_id,
            )
            return GateResult(
                decision="reject",
                signal_age_seconds=signal_age_seconds,
                reason_code=GateReason.SIGNAL_EXPIRED,
            )

        # Step 2 — DeferExhausted (TTL still valid but retried too many times)
        if defer_count >= self._defer_threshold:
            _log.debug(
                "ExecutionGateService: DeferExhausted count=%d >= threshold=%d (%s)",
                defer_count,
                self._defer_threshold,
                intent.trading_signal_id,
            )
            return GateResult(
                decision="reject",
                signal_age_seconds=signal_age_seconds,
                reason_code=GateReason.DEFER_EXHAUSTED,
            )

        # Step 3 — SpreadTooWide → Defer (with defer_until timestamp)
        if realtime_context.current_spread > self._max_spread:
            defer_until = now + timedelta(seconds=self._defer_timeout)
            _log.debug(
                "ExecutionGateService: SpreadTooWide spread=%.6f > max=%.6f → Defer (%s)",
                realtime_context.current_spread,
                self._max_spread,
                intent.trading_signal_id,
            )
            return GateResult(
                decision="defer",
                signal_age_seconds=signal_age_seconds,
                reason_code=GateReason.SPREAD_TOO_WIDE,
                defer_until=defer_until,
            )

        # Step 4 — BrokerUnreachable → Reject (cannot defer; broker must be up)
        if not realtime_context.is_broker_reachable:
            _log.debug(
                "ExecutionGateService: BrokerUnreachable (%s)",
                intent.trading_signal_id,
            )
            return GateResult(
                decision="reject",
                signal_age_seconds=signal_age_seconds,
                reason_code=GateReason.BROKER_UNREACHABLE,
            )

        # Step 5 — All checks passed → Approve
        _log.debug(
            "ExecutionGateService: approve age=%.2fs (%s)",
            signal_age_seconds,
            intent.trading_signal_id,
        )
        return GateResult(
            decision="approve",
            signal_age_seconds=signal_age_seconds,
            reason_code=None,
        )
