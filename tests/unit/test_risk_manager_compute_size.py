"""Unit tests: RiskManagerService.compute_size (Cycle 6.6).

Asserts that:
  - compute_size delegates to the injected PositionSizer.size(...).
  - It raises RuntimeError when no PositionSizer is injected.
  - SizeResult is returned verbatim (no post-processing on the service side).
  - The 4-constraint accept() path is unaffected by the new __init__ arguments.
"""

from __future__ import annotations

import pytest

from fx_ai_trading.domain.risk import Exposure, Instrument, SizeResult
from fx_ai_trading.services.position_sizer import PositionSizerService
from fx_ai_trading.services.risk_manager import RiskManagerService


def _instrument(
    symbol: str = "EURUSD",
    min_lot: int = 1000,
) -> Instrument:
    return Instrument(
        instrument=symbol,
        base_currency=symbol[:3],
        quote_currency=symbol[3:],
        pip_location=-4,
        min_trade_units=min_lot,
    )


class _RecordingSizer:
    """Collects call arguments so we can assert the delegation signature."""

    def __init__(self, ret: SizeResult) -> None:
        self._ret = ret
        self.calls: list[dict[str, object]] = []

    def size(
        self,
        account_balance: float,
        risk_pct: float,
        sl_pips: float,
        instrument: Instrument,
    ) -> SizeResult:
        self.calls.append(
            {
                "account_balance": account_balance,
                "risk_pct": risk_pct,
                "sl_pips": sl_pips,
                "instrument": instrument,
            }
        )
        return self._ret


class TestComputeSizeDelegation:
    def test_delegates_to_injected_position_sizer(self) -> None:
        sizer = _RecordingSizer(SizeResult(size_units=5000, reason=None))
        mgr = RiskManagerService(position_sizer=sizer)
        inst = _instrument()

        result = mgr.compute_size(
            account_balance=10_000.0,
            risk_pct=1.0,
            sl_pips=20.0,
            instrument=inst,
        )

        assert result == SizeResult(size_units=5000, reason=None)
        assert len(sizer.calls) == 1
        call = sizer.calls[0]
        assert call["account_balance"] == 10_000.0
        assert call["risk_pct"] == 1.0
        assert call["sl_pips"] == 20.0
        assert call["instrument"] is inst

    def test_propagates_size_result_verbatim(self) -> None:
        # SizeResult with a non-None reason (SizeUnderMin / InvalidSL / etc.)
        # must be returned as-is, without the service rewriting it.
        sizer = _RecordingSizer(SizeResult(size_units=0, reason="SizeUnderMin"))
        mgr = RiskManagerService(position_sizer=sizer)

        result = mgr.compute_size(
            account_balance=100.0,
            risk_pct=1.0,
            sl_pips=500.0,
            instrument=_instrument(),
        )

        assert result.size_units == 0
        assert result.reason == "SizeUnderMin"

    def test_raises_when_position_sizer_not_injected(self) -> None:
        mgr = RiskManagerService()  # no position_sizer
        with pytest.raises(RuntimeError, match="position_sizer"):
            mgr.compute_size(
                account_balance=10_000.0,
                risk_pct=1.0,
                sl_pips=20.0,
                instrument=_instrument(),
            )

    def test_real_position_sizer_roundtrip(self) -> None:
        # Smoke-test the end-to-end arithmetic with the concrete sizer
        # so that compute_size isn't a hollow shim in practice.
        mgr = RiskManagerService(position_sizer=PositionSizerService())
        result = mgr.compute_size(
            account_balance=10_000.0,
            risk_pct=1.0,
            sl_pips=10.0,
            instrument=_instrument(min_lot=1000),
        )
        # risk_amount = 10_000 * 0.01 = 100 ; raw_units = 100/10 = 10 ; < min 1000
        assert result.size_units == 0
        assert result.reason == "SizeUnderMin"


class TestAcceptUnaffected:
    """Cycle 6.6 must preserve the existing 4-constraint accept() path."""

    def test_accept_still_works_with_new_init_args(self) -> None:
        mgr = RiskManagerService(
            max_concurrent_positions=5,
            position_sizer=_RecordingSizer(SizeResult(size_units=1, reason=None)),
            max_open_positions=10,
            cooloff_max_failures=99,
        )
        exposure = Exposure(
            per_currency={},
            per_direction={},
            total_risk_correlation_adjusted=0.0,
            concurrent_positions=4,
        )
        result = mgr.accept(None, exposure)
        assert result.accepted is True
        assert result.exposure_after is not None
        assert result.exposure_after.concurrent_positions == 5

    def test_accept_reject_codes_unchanged(self) -> None:
        mgr = RiskManagerService(
            max_concurrent_positions=5,
            position_sizer=_RecordingSizer(SizeResult(size_units=1, reason=None)),
        )
        exposure = Exposure(
            per_currency={},
            per_direction={},
            total_risk_correlation_adjusted=0.0,
            concurrent_positions=5,
        )
        assert mgr.accept(None, exposure).reject_reason == "risk.concurrent_limit"
