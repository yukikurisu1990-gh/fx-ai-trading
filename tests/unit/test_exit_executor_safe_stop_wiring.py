"""Unit tests: ExitExecutor.execute() AccountTypeMismatchRuntime → safe_stop wiring (PR-5 / U-2).

ExitExecutor is deprecated since Cycle 6.7d (I-09); this PR does NOT
revive or restructure it.  These tests cover ONLY the safe_stop wiring
added in PR-5 so that the deprecated path observes the same canonical
behaviour as ``run_exit_gate`` and ``run_execution_gate``:

  - When ``broker.place_order`` raises ``AccountTypeMismatchRuntime``,
    ``supervisor.trigger_safe_stop(reason='account_type_mismatch_runtime')``
    is fired (when a supervisor is wired) and the exception then
    propagates so the caller aborts.
  - The close_events repository INSERT MUST NOT run on this path.
  - Payload key set MUST exactly match PR-4 / PR-5 run_exit_gate.
  - A broken supervisor must NOT swallow the original exception.
"""

from __future__ import annotations

import warnings
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from fx_ai_trading.common.exceptions import AccountTypeMismatchRuntime
from fx_ai_trading.domain.broker import OrderRequest, OrderResult
from fx_ai_trading.domain.exit import ExitDecision
from fx_ai_trading.services.exit_executor import ExitExecutor

_FIXED_AT = datetime(2026, 4, 22, 12, 0, 0, tzinfo=UTC)


# --- doubles -----------------------------------------------------------------


class _MismatchBroker:
    account_type: str = "demo"

    def __init__(self, *, actual_account_type: str = "live") -> None:
        self._actual = actual_account_type
        self.received: list[OrderRequest] = []

    def place_order(self, request: OrderRequest) -> OrderResult:
        self.received.append(request)
        raise AccountTypeMismatchRuntime(
            f"Broker account_type {self._actual!r} != expected {self.account_type!r}"
        )


class _SupervisorSpy:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def trigger_safe_stop(self, **kwargs) -> None:
        self.calls.append(kwargs)


class _SupervisorNoop:
    def trigger_safe_stop(self, **_kwargs) -> None:
        return None


class _BrokenSupervisor:
    def trigger_safe_stop(self, **_kwargs) -> None:
        raise RuntimeError("supervisor blew up")


# --- fixtures ----------------------------------------------------------------


@pytest.fixture()
def repo() -> MagicMock:
    """CloseEventsRepository mock — its insert MUST NOT be called on this path."""
    return MagicMock()


@pytest.fixture()
def decision() -> ExitDecision:
    return ExitDecision(
        position_id="ord-xyz",
        should_exit=True,
        reasons=("max_holding_time",),
        primary_reason="max_holding_time",
    )


def _make_executor(broker, repo) -> ExitExecutor:
    # ExitExecutor.__init__ emits a DeprecationWarning; suppress it for tests.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        return ExitExecutor(broker=broker, close_events_repo=repo)


# --- tests -------------------------------------------------------------------


class TestAccountTypeMismatchRuntimeWiring:
    def test_no_supervisor_propagates_exception_unchanged(
        self, repo: MagicMock, decision: ExitDecision
    ) -> None:
        broker = _MismatchBroker()
        executor = _make_executor(broker, repo)
        with pytest.raises(AccountTypeMismatchRuntime):
            executor.execute(
                decision=decision,
                account_id="acc-1",
                instrument="EUR_USD",
                side="long",
                size_units=1000,
                entry_order_id="ord-xyz",
                occurred_at=_FIXED_AT,
                # supervisor=None (default)
            )
        # close_events INSERT must NOT have been called.
        repo.insert.assert_not_called()

    def test_supervisor_triggers_safe_stop_with_canonical_reason(
        self, repo: MagicMock, decision: ExitDecision
    ) -> None:
        broker = _MismatchBroker()
        executor = _make_executor(broker, repo)
        spy = _SupervisorSpy()
        with pytest.raises(AccountTypeMismatchRuntime):
            executor.execute(
                decision=decision,
                account_id="acc-1",
                instrument="EUR_USD",
                side="long",
                size_units=1000,
                entry_order_id="ord-xyz",
                occurred_at=_FIXED_AT,
                supervisor=spy,  # type: ignore[arg-type]
            )
        assert len(spy.calls) == 1
        call = spy.calls[0]
        assert call["reason"] == "account_type_mismatch_runtime"
        assert call["occurred_at"] == _FIXED_AT
        payload = call["payload"]
        # Payload key parity with PR-4 (run_execution_gate) and
        # PR-5 (run_exit_gate).
        assert set(payload.keys()) == {
            "actual_account_type",
            "expected_account_type",
            "instrument",
            "client_order_id",
            "detail",
        }
        assert payload["actual_account_type"] == "demo"
        assert payload["expected_account_type"] is None
        assert payload["instrument"] == "EUR_USD"
        assert payload["client_order_id"]
        assert "demo" in payload["detail"] and "live" in payload["detail"]

    def test_supervisor_wired_does_not_write_close_event(
        self, repo: MagicMock, decision: ExitDecision
    ) -> None:
        broker = _MismatchBroker()
        executor = _make_executor(broker, repo)
        with pytest.raises(AccountTypeMismatchRuntime):
            executor.execute(
                decision=decision,
                account_id="acc-1",
                instrument="EUR_USD",
                side="long",
                size_units=1000,
                entry_order_id="ord-xyz",
                occurred_at=_FIXED_AT,
                supervisor=_SupervisorNoop(),  # type: ignore[arg-type]
            )
        repo.insert.assert_not_called()

    def test_supervisor_trigger_safe_stop_failure_does_not_swallow_original(
        self, repo: MagicMock, decision: ExitDecision
    ) -> None:
        broker = _MismatchBroker()
        executor = _make_executor(broker, repo)
        with pytest.raises(AccountTypeMismatchRuntime):
            executor.execute(
                decision=decision,
                account_id="acc-1",
                instrument="EUR_USD",
                side="long",
                size_units=1000,
                entry_order_id="ord-xyz",
                occurred_at=_FIXED_AT,
                supervisor=_BrokenSupervisor(),  # type: ignore[arg-type]
            )
        repo.insert.assert_not_called()

    def test_should_exit_false_short_circuits_before_broker(self, repo: MagicMock) -> None:
        """should_exit=False keeps existing behaviour: no broker call,
        no safe_stop firing, even when a supervisor is wired."""
        broker = _MismatchBroker()
        executor = _make_executor(broker, repo)
        spy = _SupervisorSpy()
        result = executor.execute(
            decision=ExitDecision(position_id="ord-xyz", should_exit=False, reasons=()),
            account_id="acc-1",
            instrument="EUR_USD",
            side="long",
            size_units=1000,
            entry_order_id="ord-xyz",
            occurred_at=_FIXED_AT,
            supervisor=spy,  # type: ignore[arg-type]
        )
        assert result is None
        assert broker.received == []
        assert spy.calls == []
        repo.insert.assert_not_called()
