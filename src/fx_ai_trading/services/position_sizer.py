"""PositionSizerService — risk-based lot sizing (D3 §2.5.1 / M10).

Implements the PositionSizer Protocol.

M10 formula (v0):
  risk_amount  = account_balance × risk_pct / 100
  raw_units    = risk_amount / sl_pips          (sl_pips: stop-loss in pip-distance)
  size_units   = floor(raw_units / min_lot) × min_lot

Invariants:
  - size_units is always a multiple of min_trade_units, or 0.
  - sl_pips <= 0 → SizeResult(0, 'InvalidSL')
  - raw_units < min_trade_units → SizeResult(0, 'SizeUnderMin')
  - No broker API calls, no DB access, no clock usage.

Phase 7: replace sl_pips with pip_value-adjusted formula using real quote currency.
"""

from __future__ import annotations

import logging
import math

from fx_ai_trading.domain.risk import Instrument, SizeResult

_log = logging.getLogger(__name__)

_DEFAULT_RISK_PCT = 1.0


class PositionSizerService:
    """Risk-percentage-based position sizer for M10 paper mode.

    Args:
        risk_pct: Percentage of account balance to risk per trade (default 1.0).
    """

    def __init__(self, risk_pct: float = _DEFAULT_RISK_PCT) -> None:
        if risk_pct <= 0 or risk_pct > 100:
            raise ValueError(f"risk_pct must be in (0, 100], got {risk_pct}")
        self._risk_pct = risk_pct

    def size(
        self,
        account_balance: float,
        risk_pct: float,
        sl_pips: float,
        instrument: Instrument,
    ) -> SizeResult:
        """Return lot size based on fixed-risk formula.

        Args:
            account_balance: Total account balance in account currency.
            risk_pct: Percentage of balance to risk (overrides constructor default).
            sl_pips: Stop-loss distance in pips (must be > 0).
            instrument: Instrument reference data including min_trade_units.

        Returns:
            SizeResult with size_units=0 if under minimum, else rounded-down size.
        """
        if sl_pips <= 0:
            _log.debug(
                "PositionSizerService: sl_pips=%s <= 0 → InvalidSL (%s)",
                sl_pips,
                instrument.instrument,
            )
            return SizeResult(size_units=0, reason="InvalidSL")

        if risk_pct <= 0:
            _log.debug(
                "PositionSizerService: risk_pct=%s <= 0 → InvalidRiskPct (%s)",
                risk_pct,
                instrument.instrument,
            )
            return SizeResult(size_units=0, reason="InvalidRiskPct")

        risk_amount = account_balance * risk_pct / 100.0
        raw_units = risk_amount / sl_pips

        min_lot = instrument.min_trade_units
        size_units = math.floor(raw_units / min_lot) * min_lot

        if size_units < min_lot:
            _log.debug(
                "PositionSizerService: raw_units=%.2f < min_lot=%d → SizeUnderMin (%s)",
                raw_units,
                min_lot,
                instrument.instrument,
            )
            return SizeResult(size_units=0, reason="SizeUnderMin")

        _log.debug(
            "PositionSizerService: %s size=%d (risk_pct=%.2f, sl_pips=%.5f, balance=%.2f)",
            instrument.instrument,
            size_units,
            risk_pct,
            sl_pips,
            account_balance,
        )
        return SizeResult(size_units=size_units, reason=None)
