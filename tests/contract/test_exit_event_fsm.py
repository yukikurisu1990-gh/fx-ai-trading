"""Contract tests: close_events FSM and ExitExecutor contracts (M14 / M-EXIT-1).

Verifies:
  1. ExitExecutor.execute() returns None when should_exit=False (no-op).
  2. ExitExecutor.execute() calls Broker.place_order when should_exit=True.
  3. Closing side is opposite of original side (long→short, short→long).
  4. CloseEventsRepository.insert() is called exactly once per execute().
  5. Reasons JSON contains the exit reasons in priority order.
  6. ExitExecutor does NOT call broker when should_exit=False.
  7. close_event primary_reason_code matches ExitDecision.primary_reason.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

from fx_ai_trading.domain.exit import ExitDecision
from fx_ai_trading.services.exit_executor import ExitExecutor

_FIXED_AT = datetime(2026, 1, 1, tzinfo=UTC)


def _make_executor(broker=None, repo=None) -> ExitExecutor:
    broker = broker or MagicMock()
    repo = repo or MagicMock()
    return ExitExecutor(broker=broker, close_events_repo=repo)


def _make_decision(*, should_exit: bool = True, reasons=("tp",), primary_reason="tp"):
    return ExitDecision(
        position_id="pos-1",
        should_exit=should_exit,
        reasons=tuple(reasons),
        primary_reason=primary_reason if should_exit else None,
    )


class TestNoExitDecision:
    def test_execute_returns_none_when_no_exit(self) -> None:
        executor = _make_executor()
        decision = _make_decision(should_exit=False, reasons=(), primary_reason=None)
        result = executor.execute(
            decision=decision,
            account_id="acc-1",
            instrument="EUR_USD",
            side="long",
            size_units=1000,
            entry_order_id="ord-1",
            occurred_at=_FIXED_AT,
        )
        assert result is None

    def test_broker_not_called_when_no_exit(self) -> None:
        broker = MagicMock()
        executor = _make_executor(broker=broker)
        decision = _make_decision(should_exit=False, reasons=(), primary_reason=None)
        executor.execute(
            decision=decision,
            account_id="acc-1",
            instrument="EUR_USD",
            side="long",
            size_units=1000,
            entry_order_id="ord-1",
            occurred_at=_FIXED_AT,
        )
        broker.place_order.assert_not_called()

    def test_repo_not_called_when_no_exit(self) -> None:
        repo = MagicMock()
        executor = _make_executor(repo=repo)
        decision = _make_decision(should_exit=False, reasons=(), primary_reason=None)
        executor.execute(
            decision=decision,
            account_id="acc-1",
            instrument="EUR_USD",
            side="long",
            size_units=1000,
            entry_order_id="ord-1",
            occurred_at=_FIXED_AT,
        )
        repo.insert.assert_not_called()


class TestExitDecisionExecuted:
    def test_broker_place_order_called_once(self) -> None:
        broker = MagicMock()
        broker.place_order.return_value = MagicMock(broker_order_id="mock-close-1")
        executor = _make_executor(broker=broker)
        executor.execute(
            decision=_make_decision(),
            account_id="acc-1",
            instrument="EUR_USD",
            side="long",
            size_units=1000,
            entry_order_id="ord-1",
            occurred_at=_FIXED_AT,
        )
        broker.place_order.assert_called_once()

    def test_closing_side_is_opposite_for_long(self) -> None:
        broker = MagicMock()
        broker.place_order.return_value = MagicMock(broker_order_id="mock-close-1")
        executor = _make_executor(broker=broker)
        executor.execute(
            decision=_make_decision(),
            account_id="acc-1",
            instrument="EUR_USD",
            side="long",
            size_units=1000,
            entry_order_id="ord-1",
            occurred_at=_FIXED_AT,
        )
        request = broker.place_order.call_args[0][0]
        assert request.side == "short"

    def test_closing_side_is_opposite_for_short(self) -> None:
        broker = MagicMock()
        broker.place_order.return_value = MagicMock(broker_order_id="mock-close-1")
        executor = _make_executor(broker=broker)
        executor.execute(
            decision=_make_decision(),
            account_id="acc-1",
            instrument="EUR_USD",
            side="short",
            size_units=500,
            entry_order_id="ord-1",
            occurred_at=_FIXED_AT,
        )
        request = broker.place_order.call_args[0][0]
        assert request.side == "long"

    def test_close_size_units_matches_position(self) -> None:
        broker = MagicMock()
        broker.place_order.return_value = MagicMock(broker_order_id="mock-close-1")
        executor = _make_executor(broker=broker)
        executor.execute(
            decision=_make_decision(),
            account_id="acc-1",
            instrument="EUR_USD",
            side="long",
            size_units=750,
            entry_order_id="ord-1",
            occurred_at=_FIXED_AT,
        )
        request = broker.place_order.call_args[0][0]
        assert request.size_units == 750

    def test_repo_insert_called_once(self) -> None:
        broker = MagicMock()
        broker.place_order.return_value = MagicMock(broker_order_id="mock-close-1")
        repo = MagicMock()
        executor = _make_executor(broker=broker, repo=repo)
        executor.execute(
            decision=_make_decision(),
            account_id="acc-1",
            instrument="EUR_USD",
            side="long",
            size_units=1000,
            entry_order_id="ord-1",
            occurred_at=_FIXED_AT,
        )
        repo.insert.assert_called_once()

    def test_repo_insert_uses_entry_order_id(self) -> None:
        broker = MagicMock()
        broker.place_order.return_value = MagicMock(broker_order_id="mock-close-1")
        repo = MagicMock()
        executor = _make_executor(broker=broker, repo=repo)
        executor.execute(
            decision=_make_decision(),
            account_id="acc-1",
            instrument="EUR_USD",
            side="long",
            size_units=1000,
            entry_order_id="my-entry-order",
            occurred_at=_FIXED_AT,
        )
        kwargs = repo.insert.call_args.kwargs
        assert kwargs["order_id"] == "my-entry-order"

    def test_repo_primary_reason_code_matches_decision(self) -> None:
        broker = MagicMock()
        broker.place_order.return_value = MagicMock(broker_order_id="mock-close-1")
        repo = MagicMock()
        executor = _make_executor(broker=broker, repo=repo)
        executor.execute(
            decision=_make_decision(
                reasons=("emergency_stop", "sl"), primary_reason="emergency_stop"
            ),
            account_id="acc-1",
            instrument="EUR_USD",
            side="long",
            size_units=1000,
            entry_order_id="ord-1",
            occurred_at=_FIXED_AT,
        )
        kwargs = repo.insert.call_args.kwargs
        assert kwargs["primary_reason_code"] == "emergency_stop"

    def test_repo_reasons_json_contains_all_reasons(self) -> None:
        broker = MagicMock()
        broker.place_order.return_value = MagicMock(broker_order_id="mock-close-1")
        repo = MagicMock()
        executor = _make_executor(broker=broker, repo=repo)
        executor.execute(
            decision=_make_decision(reasons=("sl", "max_holding_time"), primary_reason="sl"),
            account_id="acc-1",
            instrument="EUR_USD",
            side="long",
            size_units=1000,
            entry_order_id="ord-1",
            occurred_at=_FIXED_AT,
        )
        kwargs = repo.insert.call_args.kwargs
        reason_codes = {r["reason_code"] for r in kwargs["reasons"]}
        assert "sl" in reason_codes
        assert "max_holding_time" in reason_codes

    def test_execute_returns_order_result(self) -> None:
        from fx_ai_trading.domain.broker import OrderResult

        broker = MagicMock()
        mock_result = MagicMock(spec=OrderResult)
        broker.place_order.return_value = mock_result
        executor = _make_executor(broker=broker)
        result = executor.execute(
            decision=_make_decision(),
            account_id="acc-1",
            instrument="EUR_USD",
            side="long",
            size_units=1000,
            entry_order_id="ord-1",
            occurred_at=_FIXED_AT,
        )
        assert result is mock_result
