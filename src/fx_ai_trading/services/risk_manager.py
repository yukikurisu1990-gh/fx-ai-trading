"""RiskManagerService — 4-constraint portfolio risk gating (D3 §2.5.2 / M10).

Implements the RiskManager Protocol.

4 constraints evaluated in order (6.18 / phase6_hardening.md §6.5):
  C1: concurrent_positions >= max_concurrent_positions → Reject
  C2: per_currency exposure >= max_single_currency_exposure_pct → Reject
  C3: per_direction exposure >= max_net_directional_exposure_per_currency_pct → Reject
  C4: total_risk_correlation_adjusted >= total_risk_cap_pct → Reject

Invariants:
  - accept() returns RiskAcceptResult(accepted=True/False) — never raises.
  - When accepted=True, exposure_after reflects the updated concurrent_positions.
  - No execution logic, no DB writes (risk_events TODO for M12).
  - No re-evaluation of MetaDecision strategy logic.
"""

from __future__ import annotations

import logging

from fx_ai_trading.domain.risk import Exposure, RiskAcceptResult

_log = logging.getLogger(__name__)

# Default constraint values from phase6_hardening.md §6.5
_DEFAULT_MAX_CONCURRENT = 5
_DEFAULT_MAX_SINGLE_CURRENCY_PCT = 30.0
_DEFAULT_MAX_NET_DIRECTIONAL_PCT = 40.0
_DEFAULT_TOTAL_RISK_CAP_PCT = 10.0  # M10 simplified: 5 positions × 2% risk


class RiskManagerService:
    """Portfolio risk constraint checker for M10.

    Evaluates 4 constraints in fixed order before order creation.

    Args:
        max_concurrent_positions: Hard upper bound on simultaneous open positions.
        max_single_currency_exposure_pct: Max % of portfolio in any single currency.
        max_net_directional_exposure_per_currency_pct: Max net long/short % per currency.
        total_risk_cap_pct: Max total correlation-adjusted risk %.
    """

    def __init__(
        self,
        max_concurrent_positions: int = _DEFAULT_MAX_CONCURRENT,
        max_single_currency_exposure_pct: float = _DEFAULT_MAX_SINGLE_CURRENCY_PCT,
        max_net_directional_exposure_per_currency_pct: float = _DEFAULT_MAX_NET_DIRECTIONAL_PCT,
        total_risk_cap_pct: float = _DEFAULT_TOTAL_RISK_CAP_PCT,
    ) -> None:
        self._max_concurrent = max_concurrent_positions
        self._max_single_currency_pct = max_single_currency_exposure_pct
        self._max_net_directional_pct = max_net_directional_exposure_per_currency_pct
        self._total_risk_cap_pct = total_risk_cap_pct

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
                reject_reason="risk.concurrent_limit",
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
                    reject_reason="risk.single_currency_exposure",
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
                        reject_reason="risk.net_directional_exposure",
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
                reject_reason="risk.total_risk",
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
