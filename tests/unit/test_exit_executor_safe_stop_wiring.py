"""Unit tests: ``run_exit_gate`` AccountTypeMismatchRuntime → safe_stop wiring (PR-5 / U-2).

Migrated from the deprecated ``ExitExecutor`` path to ``run_exit_gate``
in M9/H-3b so the safe_stop wiring contract lives on the post-Cycle
6.7d (I-09) write path.  ``ExitExecutor`` itself is intentionally left
in tree until H-3c deletes it; this file no longer imports it.

The wiring being pinned (semantics unchanged from the original suite,
only the surface differs):

  - When ``broker.place_order`` raises ``AccountTypeMismatchRuntime``,
    ``supervisor.trigger_safe_stop(reason='account_type_mismatch_runtime')``
    fires (when a supervisor is wired) and the exception then
    propagates so the caller aborts.
  - ``StateManager.on_close`` MUST NOT run on this path.
  - Payload key set MUST exactly match PR-4 (run_execution_gate) /
    PR-5 (run_exit_gate).
  - A broken supervisor must NOT swallow the original mismatch
    exception.
  - When ExitPolicy returns ``should_exit=False``, the gate short-
    circuits before ``broker.place_order`` — broker is untouched, no
    safe_stop fires, no close-event is written.

Surface mapping vs the deprecated ``ExitExecutor`` test
───────────────────────────────────────────────────────
  ExitExecutor.execute(...)              → run_exit_gate(...)
  CloseEventsRepository.insert(...)      → StateManager.on_close(...)
  result is None  (should_exit=False)    → outcome == 'noop'
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from fx_ai_trading.common.clock import FixedClock
from fx_ai_trading.common.exceptions import AccountTypeMismatchRuntime
from fx_ai_trading.domain.broker import OrderRequest, OrderResult
from fx_ai_trading.domain.exit import ExitDecision
from fx_ai_trading.domain.state import OpenPositionInfo
from fx_ai_trading.services.exit_gate_runner import run_exit_gate

_FIXED_AT = datetime(2026, 4, 22, 12, 0, 0, tzinfo=UTC)
_OPEN_AT = datetime(2026, 4, 22, 11, 0, 0, tzinfo=UTC)


# --- doubles -----------------------------------------------------------------


class _MismatchBroker:
    """Broker whose ``place_order`` always raises AccountTypeMismatchRuntime.

    Mirrors the deprecated suite's double exactly so the wiring contract
    being verified is unchanged on this side of the migration.
    """

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


# --- helpers -----------------------------------------------------------------


def _make_position(
    *, instrument: str = "EUR_USD", order_id: str = "ord-xyz", units: int = 1000
) -> OpenPositionInfo:
    return OpenPositionInfo(
        instrument=instrument,
        order_id=order_id,
        units=units,
        avg_price=1.10,
        open_time_utc=_OPEN_AT,
    )


def _make_state_manager(positions: list[OpenPositionInfo]) -> MagicMock:
    """StateManager double — ``on_close`` MUST NOT be called on the
    AccountTypeMismatchRuntime path; per-test asserts pin that."""
    sm = MagicMock(name="state_manager")
    sm.open_position_details.return_value = positions
    return sm


def _make_exit_policy(*, should_exit: bool = True) -> MagicMock:
    policy = MagicMock(name="exit_policy")
    policy.evaluate.return_value = ExitDecision(
        position_id="ord-xyz",
        should_exit=should_exit,
        reasons=("max_holding_time",) if should_exit else (),
        primary_reason="max_holding_time" if should_exit else None,
    )
    return policy


# --- fixtures ----------------------------------------------------------------


@pytest.fixture()
def state_manager() -> MagicMock:
    return _make_state_manager([_make_position()])


@pytest.fixture()
def exit_policy() -> MagicMock:
    return _make_exit_policy(should_exit=True)


# --- tests -------------------------------------------------------------------


class TestAccountTypeMismatchRuntimeWiring:
    def test_no_supervisor_propagates_exception_unchanged(
        self, state_manager: MagicMock, exit_policy: MagicMock
    ) -> None:
        broker = _MismatchBroker()
        with pytest.raises(AccountTypeMismatchRuntime):
            run_exit_gate(
                broker=broker,
                account_id="acc-1",
                clock=FixedClock(_FIXED_AT),
                state_manager=state_manager,
                exit_policy=exit_policy,
                price_feed=lambda _instrument: 1.20,
                side="long",
                # supervisor=None (default)
            )
        # close-event write MUST NOT have happened.
        state_manager.on_close.assert_not_called()

    def test_supervisor_triggers_safe_stop_with_canonical_reason(
        self, state_manager: MagicMock, exit_policy: MagicMock
    ) -> None:
        broker = _MismatchBroker()
        spy = _SupervisorSpy()
        with pytest.raises(AccountTypeMismatchRuntime):
            run_exit_gate(
                broker=broker,
                account_id="acc-1",
                clock=FixedClock(_FIXED_AT),
                state_manager=state_manager,
                exit_policy=exit_policy,
                price_feed=lambda _instrument: 1.20,
                side="long",
                supervisor=spy,  # type: ignore[arg-type]
            )
        assert len(spy.calls) == 1
        call = spy.calls[0]
        assert call["reason"] == "account_type_mismatch_runtime"
        assert call["occurred_at"] == _FIXED_AT
        payload = call["payload"]
        # Payload key parity with PR-4 (run_execution_gate) /
        # PR-5 (run_exit_gate).
        assert set(payload.keys()) == {
            "actual_account_type",
            "expected_account_type",
            "instrument",
            "client_order_id",
            "detail",
        }
        assert payload["actual_account_type"] == "demo"
        # run_exit_gate has no per-call expected value (unlike
        # run_execution_gate); the mismatch text is fully captured in
        # ``detail`` (str(exc)).
        assert payload["expected_account_type"] is None
        assert payload["instrument"] == "EUR_USD"
        assert payload["client_order_id"]
        assert "demo" in payload["detail"] and "live" in payload["detail"]

    def test_supervisor_wired_does_not_write_close_event(
        self, state_manager: MagicMock, exit_policy: MagicMock
    ) -> None:
        broker = _MismatchBroker()
        with pytest.raises(AccountTypeMismatchRuntime):
            run_exit_gate(
                broker=broker,
                account_id="acc-1",
                clock=FixedClock(_FIXED_AT),
                state_manager=state_manager,
                exit_policy=exit_policy,
                price_feed=lambda _instrument: 1.20,
                side="long",
                supervisor=_SupervisorNoop(),  # type: ignore[arg-type]
            )
        state_manager.on_close.assert_not_called()

    def test_supervisor_trigger_safe_stop_failure_does_not_swallow_original(
        self, state_manager: MagicMock, exit_policy: MagicMock
    ) -> None:
        broker = _MismatchBroker()
        with pytest.raises(AccountTypeMismatchRuntime):
            run_exit_gate(
                broker=broker,
                account_id="acc-1",
                clock=FixedClock(_FIXED_AT),
                state_manager=state_manager,
                exit_policy=exit_policy,
                price_feed=lambda _instrument: 1.20,
                side="long",
                supervisor=_BrokenSupervisor(),  # type: ignore[arg-type]
            )
        state_manager.on_close.assert_not_called()

    def test_should_exit_false_short_circuits_before_broker(self, state_manager: MagicMock) -> None:
        """should_exit=False keeps existing behaviour: no broker call,
        no safe_stop firing, even when a supervisor is wired.

        ``run_exit_gate`` returns
        ``[ExitGateRunResult(outcome='noop')]`` here in place of the
        deprecated ``execute() → None`` signal.
        """
        broker = _MismatchBroker()
        spy = _SupervisorSpy()
        results = run_exit_gate(
            broker=broker,
            account_id="acc-1",
            clock=FixedClock(_FIXED_AT),
            state_manager=state_manager,
            exit_policy=_make_exit_policy(should_exit=False),
            price_feed=lambda _instrument: 1.20,
            side="long",
            supervisor=spy,  # type: ignore[arg-type]
        )
        assert [r.outcome for r in results] == ["noop"]
        assert broker.received == []
        assert spy.calls == []
        state_manager.on_close.assert_not_called()
