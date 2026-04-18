"""Contract tests for OrdersRepository FSM — uses SQLite, no external DB required.

Verifies that update_status() enforces forward-only transitions:
  PENDING → SUBMITTED → FILLED | CANCELED | FAILED
Backward and invalid transitions must raise RepositoryError.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, text

from fx_ai_trading.common.exceptions import RepositoryError
from fx_ai_trading.config.common_keys_context import CommonKeysContext
from fx_ai_trading.repositories.orders import _VALID_TRANSITIONS, OrdersRepository

_CTX = CommonKeysContext(
    run_id="fsm-test",
    environment="test",
    code_version="0.0.0",
    config_version="test-cfg",
)

_BROKER_ID = "__fsm_broker__"
_ACCOUNT_ID = "__fsm_account__"
_INSTRUMENT = "__FSM_INSTR__"


@pytest.fixture(scope="module")
def engine():
    e = create_engine("sqlite://")
    with e.begin() as conn:
        conn.execute(text(
            "CREATE TABLE brokers (broker_id TEXT PRIMARY KEY, name TEXT NOT NULL)"
        ))
        conn.execute(text(
            "CREATE TABLE accounts ("
            "  account_id TEXT PRIMARY KEY,"
            "  broker_id TEXT NOT NULL REFERENCES brokers(broker_id),"
            "  account_type TEXT NOT NULL,"
            "  base_currency TEXT NOT NULL,"
            "  created_at TEXT DEFAULT CURRENT_TIMESTAMP,"
            "  updated_at TEXT DEFAULT CURRENT_TIMESTAMP"
            ")"
        ))
        conn.execute(text(
            "CREATE TABLE instruments ("
            "  instrument TEXT PRIMARY KEY,"
            "  base_currency TEXT NOT NULL,"
            "  quote_currency TEXT NOT NULL,"
            "  pip_location INTEGER NOT NULL"
            ")"
        ))
        conn.execute(text(
            "CREATE TABLE orders ("
            "  order_id TEXT PRIMARY KEY,"
            "  client_order_id TEXT,"
            "  trading_signal_id TEXT,"
            "  account_id TEXT NOT NULL REFERENCES accounts(account_id),"
            "  instrument TEXT NOT NULL REFERENCES instruments(instrument),"
            "  account_type TEXT NOT NULL,"
            "  order_type TEXT NOT NULL,"
            "  direction TEXT NOT NULL,"
            "  units TEXT NOT NULL,"
            "  status TEXT NOT NULL DEFAULT 'PENDING',"
            "  submitted_at TEXT,"
            "  filled_at TEXT,"
            "  canceled_at TEXT,"
            "  correlation_id TEXT,"
            "  created_at TEXT DEFAULT CURRENT_TIMESTAMP"
            ")"
        ))
        conn.execute(text(
            "INSERT INTO brokers VALUES (:id, :name)"
        ), {"id": _BROKER_ID, "name": "FSM Broker"})
        conn.execute(
            text(
                "INSERT INTO accounts"
                " VALUES (:aid, :bid, 'demo', 'USD', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            ),
            {"aid": _ACCOUNT_ID, "bid": _BROKER_ID},
        )
        conn.execute(text(
            "INSERT INTO instruments VALUES (:i, 'TST', 'USD', -4)"
        ), {"i": _INSTRUMENT})
    yield e
    e.dispose()


@pytest.fixture(scope="module")
def repo(engine):
    return OrdersRepository(engine=engine)


def _insert_order(repo: OrdersRepository, order_id: str, status: str = "PENDING") -> None:
    repo.create_order(
        order_id=order_id,
        account_id=_ACCOUNT_ID,
        instrument=_INSTRUMENT,
        account_type="demo",
        order_type="market",
        direction="buy",
        units="1000",
        context=_CTX,
    )
    if status != "PENDING":
        with repo._engine.begin() as conn:
            conn.execute(
                text("UPDATE orders SET status = :s WHERE order_id = :oid"),
                {"s": status, "oid": order_id},
            )


class TestFSMForwardTransitions:
    def test_pending_to_submitted(self, repo) -> None:
        _insert_order(repo, "__fsm_p2s__")
        repo.update_status("__fsm_p2s__", "SUBMITTED", _CTX)
        result = repo.get_by_order_id("__fsm_p2s__")
        assert result["status"] == "SUBMITTED"

    def test_pending_to_canceled(self, repo) -> None:
        _insert_order(repo, "__fsm_p2c__")
        repo.update_status("__fsm_p2c__", "CANCELED", _CTX)
        result = repo.get_by_order_id("__fsm_p2c__")
        assert result["status"] == "CANCELED"

    def test_pending_to_failed(self, repo) -> None:
        _insert_order(repo, "__fsm_p2f__")
        repo.update_status("__fsm_p2f__", "FAILED", _CTX)
        result = repo.get_by_order_id("__fsm_p2f__")
        assert result["status"] == "FAILED"

    def test_submitted_to_filled(self, repo) -> None:
        _insert_order(repo, "__fsm_s2fi__", status="SUBMITTED")
        repo.update_status("__fsm_s2fi__", "FILLED", _CTX)
        result = repo.get_by_order_id("__fsm_s2fi__")
        assert result["status"] == "FILLED"

    def test_submitted_to_canceled(self, repo) -> None:
        _insert_order(repo, "__fsm_s2ca__", status="SUBMITTED")
        repo.update_status("__fsm_s2ca__", "CANCELED", _CTX)
        result = repo.get_by_order_id("__fsm_s2ca__")
        assert result["status"] == "CANCELED"

    def test_submitted_to_failed(self, repo) -> None:
        _insert_order(repo, "__fsm_s2fa__", status="SUBMITTED")
        repo.update_status("__fsm_s2fa__", "FAILED", _CTX)
        result = repo.get_by_order_id("__fsm_s2fa__")
        assert result["status"] == "FAILED"


class TestFSMBackwardTransitionsRejected:
    def test_filled_to_pending_raises(self, repo) -> None:
        _insert_order(repo, "__fsm_fi2p__", status="FILLED")
        with pytest.raises(RepositoryError, match="FILLED"):
            repo.update_status("__fsm_fi2p__", "PENDING", _CTX)

    def test_filled_to_submitted_raises(self, repo) -> None:
        _insert_order(repo, "__fsm_fi2s__", status="FILLED")
        with pytest.raises(RepositoryError, match="FILLED"):
            repo.update_status("__fsm_fi2s__", "SUBMITTED", _CTX)

    def test_canceled_to_pending_raises(self, repo) -> None:
        _insert_order(repo, "__fsm_ca2p__", status="CANCELED")
        with pytest.raises(RepositoryError, match="CANCELED"):
            repo.update_status("__fsm_ca2p__", "PENDING", _CTX)

    def test_failed_to_pending_raises(self, repo) -> None:
        _insert_order(repo, "__fsm_fa2p__", status="FAILED")
        with pytest.raises(RepositoryError, match="FAILED"):
            repo.update_status("__fsm_fa2p__", "PENDING", _CTX)

    def test_submitted_to_pending_raises(self, repo) -> None:
        _insert_order(repo, "__fsm_s2p__", status="SUBMITTED")
        with pytest.raises(RepositoryError, match="SUBMITTED"):
            repo.update_status("__fsm_s2p__", "PENDING", _CTX)


class TestFSMEdgeCases:
    def test_missing_order_raises(self, repo) -> None:
        with pytest.raises(RepositoryError, match="not found"):
            repo.update_status("__no_such_order__", "SUBMITTED", _CTX)

    def test_invalid_target_status_raises(self, repo) -> None:
        _insert_order(repo, "__fsm_invalid__")
        with pytest.raises(RepositoryError):
            repo.update_status("__fsm_invalid__", "BOGUS", _CTX)

    def test_terminal_states_have_no_transitions(self) -> None:
        for state in ("FILLED", "CANCELED", "FAILED"):
            assert _VALID_TRANSITIONS[state] == set(), f"{state} must be terminal"

    def test_all_fsm_states_defined(self) -> None:
        expected = {"PENDING", "SUBMITTED", "FILLED", "CANCELED", "FAILED"}
        assert set(_VALID_TRANSITIONS.keys()) == expected
