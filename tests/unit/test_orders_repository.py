"""Unit tests for OrdersRepository — pure Python, no DB required."""

from __future__ import annotations

from unittest.mock import MagicMock

from fx_ai_trading.repositories.orders import OrdersRepository

_ROW = (
    "01ABCDEF",  # order_id
    None,  # client_order_id
    None,  # trading_signal_id
    "acc-001",  # account_id
    "EUR_USD",  # instrument
    "demo",  # account_type
    "market",  # order_type
    "buy",  # direction
    "1000.0000",  # units
    "PENDING",  # status
    None,  # submitted_at
    None,  # filled_at
    None,  # canceled_at
    None,  # correlation_id
    "2026-01-01",  # created_at
)
_DICT = {
    "order_id": "01ABCDEF",
    "client_order_id": None,
    "trading_signal_id": None,
    "account_id": "acc-001",
    "instrument": "EUR_USD",
    "account_type": "demo",
    "order_type": "market",
    "direction": "buy",
    "units": "1000.0000",
    "status": "PENDING",
    "submitted_at": None,
    "filled_at": None,
    "canceled_at": None,
    "correlation_id": None,
    "created_at": "2026-01-01",
}


def _make_repo(fetchone_return=None):
    engine = MagicMock()
    conn = MagicMock()
    result = MagicMock()
    result.fetchone.return_value = fetchone_return
    conn.execute.return_value = result
    conn.__enter__ = MagicMock(return_value=conn)
    conn.__exit__ = MagicMock(return_value=False)
    engine.connect.return_value = conn
    engine.begin.return_value = conn
    return OrdersRepository(engine=engine)


class TestGetByOrderId:
    def test_returns_dict_when_found(self) -> None:
        repo = _make_repo(fetchone_return=_ROW)
        result = repo.get_by_order_id("01ABCDEF")
        assert result == _DICT

    def test_returns_none_when_not_found(self) -> None:
        repo = _make_repo(fetchone_return=None)
        assert repo.get_by_order_id("missing") is None

    def test_passes_order_id_as_param(self) -> None:
        repo = _make_repo(fetchone_return=None)
        repo.get_by_order_id("ULID-XYZ")
        call_args = repo._engine.connect().__enter__().execute.call_args
        assert call_args[0][1]["order_id"] == "ULID-XYZ"


class TestCreateOrder:
    def test_calls_execute(self) -> None:
        repo = _make_repo()
        repo.create_order(
            order_id="ULID-001",
            account_id="acc-001",
            instrument="EUR_USD",
            account_type="demo",
            order_type="market",
            direction="buy",
            units="1000",
        )
        repo._engine.begin().__enter__().execute.assert_called_once()

    def test_passes_required_params(self) -> None:
        repo = _make_repo()
        repo.create_order(
            order_id="ULID-001",
            account_id="acc-001",
            instrument="EUR_USD",
            account_type="demo",
            order_type="market",
            direction="buy",
            units="1000",
        )
        call_args = repo._engine.begin().__enter__().execute.call_args
        params = call_args[0][1]
        assert params["order_id"] == "ULID-001"
        assert params["account_id"] == "acc-001"
        assert params["direction"] == "buy"

    def test_optional_params_default_to_none(self) -> None:
        repo = _make_repo()
        repo.create_order(
            order_id="ULID-001",
            account_id="acc-001",
            instrument="EUR_USD",
            account_type="demo",
            order_type="market",
            direction="buy",
            units="1000",
        )
        call_args = repo._engine.begin().__enter__().execute.call_args
        params = call_args[0][1]
        assert params["client_order_id"] is None
        assert params["trading_signal_id"] is None
        assert params["correlation_id"] is None
