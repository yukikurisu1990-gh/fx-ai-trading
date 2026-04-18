"""Unit tests for PlaceOrderUseCase — pure Python, no DB required."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from fx_ai_trading.config.common_keys_context import CommonKeysContext
from fx_ai_trading.usecases.place_order_usecase import PlaceOrderUseCase

_CTX = CommonKeysContext(
    run_id="run-test",
    environment="test",
    code_version="0.0.0",
    config_version="abc123",
)

_ACCOUNT = {
    "account_id": "acc-001",
    "broker_id": "broker-1",
    "account_type": "demo",
    "base_currency": "USD",
    "created_at": "2026-01-01",
    "updated_at": "2026-01-01",
}

_BASE_KWARGS = {
    "order_id": "ord-001",
    "position_snapshot_id": "snap-001",
    "account_id": "acc-001",
    "instrument": "EUR_USD",
    "account_type": "demo",
    "order_type": "market",
    "direction": "buy",
    "units": "1000",
    "context": _CTX,
}


def _make_usecase(account_return=_ACCOUNT):
    account_svc = MagicMock()
    account_svc.get_account.return_value = account_return
    order_svc = MagicMock()
    position_svc = MagicMock()
    return (
        PlaceOrderUseCase(
            account_service=account_svc,
            order_service=order_svc,
            position_service=position_svc,
        ),
        account_svc,
        order_svc,
        position_svc,
    )


class TestValidation:
    def test_zero_units_raises(self) -> None:
        uc, *_ = _make_usecase()
        with pytest.raises(ValueError, match="units"):
            uc.execute(**{**_BASE_KWARGS, "units": "0"})

    def test_negative_units_raises(self) -> None:
        uc, *_ = _make_usecase()
        with pytest.raises(ValueError, match="units"):
            uc.execute(**{**_BASE_KWARGS, "units": "-100"})

    def test_non_numeric_units_raises(self) -> None:
        uc, *_ = _make_usecase()
        with pytest.raises(ValueError, match="units"):
            uc.execute(**{**_BASE_KWARGS, "units": "abc"})

    def test_invalid_direction_raises(self) -> None:
        uc, *_ = _make_usecase()
        with pytest.raises(ValueError, match="direction"):
            uc.execute(**{**_BASE_KWARGS, "direction": "hold"})

    def test_missing_account_raises(self) -> None:
        uc, *_ = _make_usecase(account_return=None)
        with pytest.raises(ValueError, match="account not found"):
            uc.execute(**_BASE_KWARGS)

    def test_account_type_mismatch_raises(self) -> None:
        live_account = {**_ACCOUNT, "account_type": "live"}
        uc, *_ = _make_usecase(account_return=live_account)
        with pytest.raises(ValueError, match="account_type mismatch"):
            uc.execute(**_BASE_KWARGS)


class TestSuccessFlow:
    def test_buy_creates_order_and_open_position(self) -> None:
        uc, _, order_svc, position_svc = _make_usecase()
        uc.execute(**_BASE_KWARGS)
        order_svc.create_order.assert_called_once()
        call_kwargs = position_svc.record_position_event.call_args
        assert call_kwargs.kwargs["event_type"] == "open"

    def test_sell_creates_order_and_close_position(self) -> None:
        uc, _, order_svc, position_svc = _make_usecase()
        uc.execute(**{**_BASE_KWARGS, "direction": "sell"})
        order_svc.create_order.assert_called_once()
        call_kwargs = position_svc.record_position_event.call_args
        assert call_kwargs.kwargs["event_type"] == "close"

    def test_order_created_with_correct_params(self) -> None:
        uc, _, order_svc, _ = _make_usecase()
        uc.execute(**_BASE_KWARGS)
        order_svc.create_order.assert_called_once_with(
            order_id="ord-001",
            account_id="acc-001",
            instrument="EUR_USD",
            account_type="demo",
            order_type="market",
            direction="buy",
            units="1000",
            context=_CTX,
            correlation_id=None,
        )

    def test_position_snapshot_id_passed(self) -> None:
        uc, _, _, position_svc = _make_usecase()
        uc.execute(**_BASE_KWARGS)
        call_kwargs = position_svc.record_position_event.call_args
        assert call_kwargs.kwargs["position_snapshot_id"] == "snap-001"

    def test_correlation_id_propagated(self) -> None:
        uc, _, order_svc, position_svc = _make_usecase()
        uc.execute(**_BASE_KWARGS, correlation_id="corr-xyz")
        order_kwargs = order_svc.create_order.call_args.kwargs
        pos_kwargs = position_svc.record_position_event.call_args.kwargs
        assert order_kwargs["correlation_id"] == "corr-xyz"
        assert pos_kwargs["correlation_id"] == "corr-xyz"
