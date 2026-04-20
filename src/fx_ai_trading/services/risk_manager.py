"""RiskManagerService — 4-constraint portfolio risk gating (D3 §2.5.2 / M10)
plus Cycle 6.6 pre-execution sizing + 3-guard gate.

Implements the RiskManager Protocol (accept).  Cycle 6.6 adds two
service-level helpers that are *not* part of the Protocol:

  compute_size(...)  — thin delegation to PositionSizer.size().  Kept
                       here so the Execution Gate holds exactly one
                       dependency (``risk_manager``) rather than two.
  allow_trade(...)   — 3 pre-execution guards applied BEFORE broker
                       dispatch but AFTER TTL + selector.  Ordered:
                         G1: duplicate instrument
                         G2: max_open_positions  (runtime cap)
                         G3: recent_execution_failure_cooloff

4-constraint accept() (6.18 / phase6_hardening.md §6.5):
  C1: concurrent_positions >= max_concurrent_positions → Reject
  C2: per_currency exposure >= max_single_currency_exposure_pct → Reject
  C3: per_direction exposure >= max_net_directional_exposure_per_currency_pct → Reject
  C4: total_risk_correlation_adjusted >= total_risk_cap_pct → Reject

Invariants:
  - accept() returns RiskAcceptResult(accepted=True/False) — never raises.
  - allow_trade() returns AllowTradeResult(allowed=True/False) — never raises.
  - compute_size() delegates to PositionSizer; returns SizeResult.
  - When accepted=True, exposure_after reflects the updated concurrent_positions.
  - No execution logic, no DB writes (risk_events TODO for M12).
  - No re-evaluation of MetaDecision strategy logic.
"""

from __future__ import annotations

import logging

from fx_ai_trading.domain.reason_codes import RiskReason
from fx_ai_trading.domain.risk import (
    AllowTradeResult,
    Exposure,
    Instrument,
    PositionSizer,
    RiskAcceptResult,
    SizeResult,
)

_log = logging.getLogger(__name__)

# Default constraint values from phase6_hardening.md §6.5
_DEFAULT_MAX_CONCURRENT = 5
_DEFAULT_MAX_SINGLE_CURRENCY_PCT = 30.0
_DEFAULT_MAX_NET_DIRECTIONAL_PCT = 40.0
_DEFAULT_TOTAL_RISK_CAP_PCT = 10.0  # M10 simplified: 5 positions × 2% risk

# Cycle 6.6 allow_trade defaults (provisional, M10 paper-mode).
_DEFAULT_MAX_OPEN_POSITIONS = 5
_DEFAULT_COOLOFF_MAX_FAILURES = 3


class RiskManagerService:
    """Portfolio risk constraint checker for M10 + Cycle 6.6 pre-execution gate.

    Evaluates 4 constraints in fixed order before order creation (accept).
    Cycle 6.6 adds compute_size (delegates to PositionSizer) and
    allow_trade (3 pre-execution guards).

    Args:
        max_concurrent_positions: Hard upper bound on simultaneous open positions.
        max_single_currency_exposure_pct: Max % of portfolio in any single currency.
        max_net_directional_exposure_per_currency_pct: Max net long/short % per currency.
        total_risk_cap_pct: Max total correlation-adjusted risk %.
        position_sizer: Injected PositionSizer (required for compute_size).
        max_open_positions: Runtime cap for allow_trade G2.  Defaults to
                            ``max_concurrent_positions`` if None.
        cooloff_max_failures: Recent-execution failure count threshold for G3.
    """

    def __init__(
        self,
        max_concurrent_positions: int = _DEFAULT_MAX_CONCURRENT,
        max_single_currency_exposure_pct: float = _DEFAULT_MAX_SINGLE_CURRENCY_PCT,
        max_net_directional_exposure_per_currency_pct: float = _DEFAULT_MAX_NET_DIRECTIONAL_PCT,
        total_risk_cap_pct: float = _DEFAULT_TOTAL_RISK_CAP_PCT,
        position_sizer: PositionSizer | None = None,
        max_open_positions: int | None = None,
        cooloff_max_failures: int = _DEFAULT_COOLOFF_MAX_FAILURES,
    ) -> None:
        self._max_concurrent = max_concurrent_positions
        self._max_single_currency_pct = max_single_currency_exposure_pct
        self._max_net_directional_pct = max_net_directional_exposure_per_currency_pct
        self._total_risk_cap_pct = total_risk_cap_pct
        self._position_sizer = position_sizer
        self._max_open_positions = (
            max_open_positions if max_open_positions is not None else max_concurrent_positions
        )
        self._cooloff_max_failures = cooloff_max_failures

    def accept(self, decision: object, exposure: Exposure) -> RiskAcceptResult:
        """Evaluate MetaDecision against current exposure using 4 constraints.

        Constraints are checked in order C1 → C2 → C3 → C4.
        First violation causes immediate Reject with the corresponding reason code.

        Args:
            decision: MetaDecision (type-erased to avoid circular import).
                      M10 uses exposure snapshot only; decision fields unused.
            exposure: Current portfolio exposure snapshot.

        Returns:
            RiskAcceptResult with accepted=True/False and optional reject_reason.
        """
        # C1: Concurrent positions cap
        if exposure.concurrent_positions >= self._max_concurrent:
            _log.debug(
                "RiskManagerService C1 Reject: concurrent=%d >= max=%d",
                exposure.concurrent_positions,
                self._max_concurrent,
            )
            return RiskAcceptResult(
                accepted=False,
                reject_reason=RiskReason.CONCURRENT_LIMIT,
            )

        # C2: Single currency exposure cap
        for currency, exposure_pct in exposure.per_currency.items():
            if exposure_pct >= self._max_single_currency_pct:
                _log.debug(
                    "RiskManagerService C2 Reject: %s exposure=%.1f%% >= max=%.1f%%",
                    currency,
                    exposure_pct,
                    self._max_single_currency_pct,
                )
                return RiskAcceptResult(
                    accepted=False,
                    reject_reason=RiskReason.SINGLE_CURRENCY_EXPOSURE,
                )

        # C3: Net directional exposure cap per currency
        for currency, directions in exposure.per_direction.items():
            for side, direction_pct in directions.items():
                if direction_pct >= self._max_net_directional_pct:
                    _log.debug(
                        "RiskManagerService C3 Reject: %s %s direction=%.1f%% >= max=%.1f%%",
                        currency,
                        side,
                        direction_pct,
                        self._max_net_directional_pct,
                    )
                    return RiskAcceptResult(
                        accepted=False,
                        reject_reason=RiskReason.NET_DIRECTIONAL_EXPOSURE,
                    )

        # C4: Total correlation-adjusted risk cap
        if exposure.total_risk_correlation_adjusted >= self._total_risk_cap_pct:
            _log.debug(
                "RiskManagerService C4 Reject: total_risk=%.2f%% >= cap=%.2f%%",
                exposure.total_risk_correlation_adjusted,
                self._total_risk_cap_pct,
            )
            return RiskAcceptResult(
                accepted=False,
                reject_reason=RiskReason.TOTAL_RISK,
            )

        # Shallow-copy outer dicts so exposure_after is independent of the snapshot.
        # Inner dicts of per_direction are not deep-copied (M10 paper-mode: no in-place mutation).
        exposure_after = Exposure(
            per_currency=dict(exposure.per_currency),
            per_direction={k: dict(v) for k, v in exposure.per_direction.items()},
            total_risk_correlation_adjusted=exposure.total_risk_correlation_adjusted,
            concurrent_positions=exposure.concurrent_positions + 1,
        )
        _log.debug(
            "RiskManagerService: accepted (concurrent %d → %d)",
            exposure.concurrent_positions,
            exposure_after.concurrent_positions,
        )
        return RiskAcceptResult(accepted=True, exposure_after=exposure_after)

    # ------------------------------------------------------------------
    # Cycle 6.6: pre-execution sizing + 3-guard gate
    # ------------------------------------------------------------------

    def compute_size(
        self,
        account_balance: float,
        risk_pct: float,
        sl_pips: float,
        instrument: Instrument,
    ) -> SizeResult:
        """Delegate to the injected PositionSizer.

        Kept as a method on RiskManagerService so the Execution Gate
        depends on exactly one risk-domain object.  Raises RuntimeError
        if no PositionSizer was injected (fail-fast in tests / config).
        """
        if self._position_sizer is None:
            raise RuntimeError(
                "RiskManagerService.compute_size requires a PositionSizer; "
                "inject one via the position_sizer constructor argument."
            )
        return self._position_sizer.size(
            account_balance=account_balance,
            risk_pct=risk_pct,
            sl_pips=sl_pips,
            instrument=instrument,
        )

    def allow_trade(
        self,
        *,
        instrument: str,
        open_instruments: frozenset[str] | set[str],
        concurrent_positions: int,
        recent_failure_count: int,
    ) -> AllowTradeResult:
        """Apply 3 pre-execution guards in fixed order.

        Fired AFTER selector + TTL and BEFORE broker dispatch.  First
        violation triggers immediate reject with the matching
        ``risk.*`` reason code; no later guard is evaluated.

        Guards:
          G1 ``risk.duplicate_instrument``         — instrument already has
             an open position.  Prevents unintended pyramiding.
          G2 ``risk.max_open_positions``           — concurrent open
             position count is at the runtime cap.  Distinct from C1 in
             that G2 covers the in-flight gate, C1 covers the portfolio
             snapshot accept().
          G3 ``risk.recent_execution_failure_cooloff``
             — recent execution failures (timeouts / rejects) exceed
             the threshold, forcing a cool-off window.  Note: *failure*
             not *loss* — this is an execution-path signal, not a PnL
             signal.

        Never raises.  All inputs are plain values the caller derives
        from the current orders/order_transactions snapshot.
        """
        # G1: duplicate instrument
        if instrument in open_instruments:
            _log.debug(
                "RiskManagerService.allow_trade G1 reject: %s already open",
                instrument,
            )
            return AllowTradeResult(allowed=False, reject_reason=RiskReason.DUPLICATE_INSTRUMENT)

        # G2: max open positions (runtime cap)
        if concurrent_positions >= self._max_open_positions:
            _log.debug(
                "RiskManagerService.allow_trade G2 reject: concurrent=%d >= max_open=%d",
                concurrent_positions,
                self._max_open_positions,
            )
            return AllowTradeResult(allowed=False, reject_reason=RiskReason.MAX_OPEN_POSITIONS)

        # G3: recent execution failure cooloff
        if recent_failure_count >= self._cooloff_max_failures:
            _log.debug(
                "RiskManagerService.allow_trade G3 reject: recent_failures=%d >= threshold=%d",
                recent_failure_count,
                self._cooloff_max_failures,
            )
            return AllowTradeResult(
                allowed=False,
                reject_reason=RiskReason.RECENT_EXECUTION_FAILURE_COOLOFF,
            )

        _log.debug(
            "RiskManagerService.allow_trade: allowed (instrument=%s, concurrent=%d, failures=%d)",
            instrument,
            concurrent_positions,
            recent_failure_count,
        )
        return AllowTradeResult(allowed=True, reject_reason=None)
