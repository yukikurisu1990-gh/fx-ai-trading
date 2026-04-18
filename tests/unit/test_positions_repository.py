"""Unit tests for PositionsRepository — pure Python, no DB required."""

from __future__ import annotations

from unittest.mock import MagicMock

from fx_ai_trading.repositories.positions import PositionsRepository

_ROW = (
    "snap-001",  # position_snapshot_id
    "ord-001",  # order_id
    "acc-001",  # account_id
    "EUR_USD",  # instrument
    "open",  # event_type
    "1000.0000",  # units
    "1.08500000",  # avg_price
    "12.50000000",  # unrealized_pl
    None,  # realized_pl
    "2026-01-01",  # event_time_utc
    None,  # correlation_id
)
_DICT = {
    "position_snapshot_id": "snap-001",
    "order_id": "ord-001",
    "account_id": "acc-001",
    "instrument": "EUR_USD",
    "event_type": "open",
    "units": "1000.0000",
    "avg_price": "1.08500000",
    "unrealized_pl": "12.50000000",
    "realized_pl": None,
    "event_time_utc": "2026-01-01",
    "correlation_id": None,
}


def _make_repo(fetchone_return=None, fetchall_rows=None):
    engine = MagicMock()
    conn = MagicMock()
    result = MagicMock()
    result.fetchone.return_value = fetchone_return
    if fetchall_rows is not None:
        result.__iter__ = MagicMock(return_value=iter(fetchall_rows))
    conn.execute.return_value = result
    conn.__enter__ = MagicMock(return_value=conn)
    conn.__exit__ = MagicMock(return_value=False)
    engine.connect.return_value = conn
    return PositionsRepository(engine=engine)


class TestGetByPositionId:
    def test_returns_dict_when_found(self) -> None:
        repo = _make_repo(fetchone_return=_ROW)
        result = repo.get_by_position_id("snap-001")
        assert result == _DICT

    def test_returns_none_when_not_found(self) -> None:
        repo = _make_repo(fetchone_return=None)
        assert repo.get_by_position_id("missing") is None

    def test_passes_snapshot_id_as_param(self) -> None:
        repo = _make_repo(fetchone_return=None)
        repo.get_by_position_id("snap-xyz")
        call_args = repo._engine.connect().__enter__().execute.call_args
        assert call_args[0][1]["position_snapshot_id"] == "snap-xyz"


class TestGetOpenPositions:
    def test_returns_empty_list_when_no_rows(self) -> None:
        repo = _make_repo(fetchall_rows=[])
        assert repo.get_open_positions("acc-001") == []

    def test_returns_list_of_dicts(self) -> None:
        repo = _make_repo(fetchall_rows=[_ROW])
        result = repo.get_open_positions("acc-001")
        assert result == [_DICT]

    def test_passes_account_id_as_param(self) -> None:
        repo = _make_repo(fetchall_rows=[])
        repo.get_open_positions("acc-abc")
        call_args = repo._engine.connect().__enter__().execute.call_args
        assert call_args[0][1]["account_id"] == "acc-abc"
