"""Unit tests for Service layer — pure Python, no DB required."""

from __future__ import annotations

from unittest.mock import MagicMock

from fx_ai_trading.services.account_service import AccountService
from fx_ai_trading.services.order_service import OrderService
from fx_ai_trading.services.position_service import PositionService


class TestAccountService:
    def _make(self, **kwargs):
        repo = MagicMock()
        for k, v in kwargs.items():
            setattr(repo, k, MagicMock(return_value=v))
        return AccountService(repo=repo)

    def test_get_account_delegates(self) -> None:
        svc = self._make(get_by_account_id={"account_id": "acc-1"})
        result = svc.get_account("acc-1")
        assert result["account_id"] == "acc-1"
        svc._repo.get_by_account_id.assert_called_once_with("acc-1")

    def test_get_account_none_passthrough(self) -> None:
        svc = self._make(get_by_account_id=None)
        assert svc.get_account("missing") is None

    def test_list_accounts_delegates(self) -> None:
        svc = self._make(list_accounts=[{"account_id": "acc-1"}])
        result = svc.list_accounts()
        assert len(result) == 1
        svc._repo.list_accounts.assert_called_once()

    def test_create_account_delegates(self) -> None:
        svc = self._make(create_account=None)
        svc.create_account("acc-1", "broker-1", "demo", "USD")
        svc._repo.create_account.assert_called_once_with(
            account_id="acc-1",
            broker_id="broker-1",
            account_type="demo",
            base_currency="USD",
        )


class TestOrderService:
    def _make(self, **kwargs):
        repo = MagicMock()
        for k, v in kwargs.items():
            setattr(repo, k, MagicMock(return_value=v))
        return OrderService(repo=repo)

    def test_get_order_delegates(self) -> None:
        svc = self._make(get_by_order_id={"order_id": "ord-1"})
        result = svc.get_order("ord-1")
        assert result["order_id"] == "ord-1"

    def test_get_order_none_passthrough(self) -> None:
        svc = self._make(get_by_order_id=None)
        assert svc.get_order("missing") is None

    def test_create_order_delegates(self) -> None:
        svc = self._make(create_order=None)
        svc.create_order(
            order_id="ord-1",
            account_id="acc-1",
            instrument="EUR_USD",
            account_type="demo",
            order_type="market",
            direction="buy",
            units="1000",
        )
        svc._repo.create_order.assert_called_once()


class TestPositionService:
    def _make(self, **kwargs):
        repo = MagicMock()
        for k, v in kwargs.items():
            setattr(repo, k, MagicMock(return_value=v))
        return PositionService(repo=repo)

    def test_get_position_delegates(self) -> None:
        svc = self._make(get_by_position_id={"position_snapshot_id": "snap-1"})
        result = svc.get_position("snap-1")
        assert result["position_snapshot_id"] == "snap-1"

    def test_get_open_positions_delegates(self) -> None:
        svc = self._make(get_open_positions=[])
        result = svc.get_open_positions("acc-1")
        assert result == []
        svc._repo.get_open_positions.assert_called_once_with("acc-1")
