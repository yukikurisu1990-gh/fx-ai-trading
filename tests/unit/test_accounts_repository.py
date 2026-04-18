"""Unit tests for AccountsRepository — pure Python, no DB required."""

from __future__ import annotations

from unittest.mock import MagicMock

from fx_ai_trading.repositories.accounts import AccountsRepository

_ROW = ("acc-001", "broker-1", "demo", "USD", "2026-01-01", "2026-01-01")
_DICT = {
    "account_id": "acc-001",
    "broker_id": "broker-1",
    "account_type": "demo",
    "base_currency": "USD",
    "created_at": "2026-01-01",
    "updated_at": "2026-01-01",
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
    return AccountsRepository(engine=engine)


class TestGetByAccountId:
    def test_returns_dict_when_found(self) -> None:
        repo = _make_repo(fetchone_return=_ROW)
        result = repo.get_by_account_id("acc-001")
        assert result == _DICT

    def test_returns_none_when_not_found(self) -> None:
        repo = _make_repo(fetchone_return=None)
        result = repo.get_by_account_id("missing")
        assert result is None

    def test_passes_account_id_as_param(self) -> None:
        repo = _make_repo(fetchone_return=None)
        repo.get_by_account_id("acc-xyz")
        call_kwargs = repo._engine.connect().__enter__().execute.call_args
        assert call_kwargs[0][1]["account_id"] == "acc-xyz"


class TestListAccounts:
    def test_returns_empty_list_when_no_rows(self) -> None:
        repo = _make_repo(fetchall_rows=[])
        assert repo.list_accounts() == []

    def test_returns_list_of_dicts(self) -> None:
        repo = _make_repo(fetchall_rows=[_ROW])
        result = repo.list_accounts()
        assert result == [_DICT]

    def test_returns_multiple_rows(self) -> None:
        row2 = ("acc-002", "broker-1", "live", "USD", "2026-01-02", "2026-01-02")
        repo = _make_repo(fetchall_rows=[_ROW, row2])
        result = repo.list_accounts()
        assert len(result) == 2
        assert result[0]["account_id"] == "acc-001"
        assert result[1]["account_id"] == "acc-002"
