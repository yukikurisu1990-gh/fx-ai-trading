"""Integration tests: Supervisor.attach_exit_gate / run_exit_gate_tick (M9 / H-1).

This is the cadence-seam wiring that lets the forthcoming M12 main loop
drive ``run_exit_gate`` per tick without the Supervisor itself owning a
loop (per ``supervisor.py`` module docstring).

Pinned invariants:

  - When ``attach_exit_gate`` has not been called, ``run_exit_gate_tick``
    is a no-op and returns ``[]`` — making the call safe to schedule
    unconditionally during bootstrap.
  - After ``trigger_safe_stop`` fires, the cadence path stops placing
    close orders even if the host loop keeps ticking.  This mirrors
    ``Supervisor.record_metrics`` so SafeStop semantics are identical
    across all cadence-driven seams.
  - ``run_exit_gate_tick`` forwards ``supervisor=self`` so the existing
    PR-5 / U-2 ``AccountTypeMismatchRuntime → trigger_safe_stop`` wiring
    inside ``run_exit_gate`` is preserved end-to-end.  We do NOT modify
    SafeStop here; we only re-use it.
  - Attaching exit-gate has zero effect on SafeStop idempotency.

These tests use mocks for ``Broker`` / ``StateManager`` / ``ExitPolicyService``
because the goal is to verify *the wiring*, not to re-test the gate
itself (which has its own contract suite under ``tests/contract``).
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from fx_ai_trading.common.clock import FixedClock
from fx_ai_trading.supervisor.supervisor import Supervisor


def _attach_defaults(supervisor: Supervisor) -> dict[str, MagicMock]:
    """Attach a minimal mock exit-gate config and return the mocks."""
    broker = MagicMock(name="broker")
    state_manager = MagicMock(name="state_manager")
    state_manager.open_position_details.return_value = []
    exit_policy = MagicMock(name="exit_policy")
    price_feed = MagicMock(name="price_feed", return_value=100.0)

    supervisor.attach_exit_gate(
        broker=broker,
        account_id="acct-1",
        state_manager=state_manager,
        exit_policy=exit_policy,
        price_feed=price_feed,
    )
    return {
        "broker": broker,
        "state_manager": state_manager,
        "exit_policy": exit_policy,
        "price_feed": price_feed,
    }


class TestRunExitGateTickGuards:
    """No-op paths: not-attached and post-safe_stop."""

    def test_returns_empty_list_when_not_attached(self) -> None:
        supervisor = Supervisor(clock=FixedClock(datetime(2026, 1, 1, tzinfo=UTC)))
        assert supervisor.run_exit_gate_tick() == []

    def test_does_not_call_run_exit_gate_when_not_attached(self) -> None:
        supervisor = Supervisor(clock=FixedClock(datetime(2026, 1, 1, tzinfo=UTC)))
        with patch("fx_ai_trading.services.exit_gate_runner.run_exit_gate") as mock_run:
            supervisor.run_exit_gate_tick()
        mock_run.assert_not_called()

    def test_returns_empty_list_after_safe_stop(self) -> None:
        """After SafeStop fires, the cadence seam must stop firing close orders."""
        supervisor = Supervisor(clock=FixedClock(datetime(2026, 1, 1, tzinfo=UTC)))
        _attach_defaults(supervisor)
        supervisor._is_stopped = True  # what trigger_safe_stop sets via _on_loop_stop

        with patch("fx_ai_trading.services.exit_gate_runner.run_exit_gate") as mock_run:
            result = supervisor.run_exit_gate_tick()

        assert result == []
        mock_run.assert_not_called()


class TestRunExitGateTickDispatch:
    """Happy path: attached → dependencies forwarded to run_exit_gate."""

    def test_calls_run_exit_gate_when_attached(self) -> None:
        supervisor = Supervisor(clock=FixedClock(datetime(2026, 1, 1, tzinfo=UTC)))
        _attach_defaults(supervisor)
        with patch(
            "fx_ai_trading.services.exit_gate_runner.run_exit_gate",
            return_value=[],
        ) as mock_run:
            supervisor.run_exit_gate_tick()
        mock_run.assert_called_once()

    def test_forwards_attached_dependencies(self) -> None:
        supervisor = Supervisor(clock=FixedClock(datetime(2026, 1, 1, tzinfo=UTC)))
        mocks = _attach_defaults(supervisor)
        with patch(
            "fx_ai_trading.services.exit_gate_runner.run_exit_gate",
            return_value=[],
        ) as mock_run:
            supervisor.run_exit_gate_tick()

        kwargs = mock_run.call_args.kwargs
        assert kwargs["broker"] is mocks["broker"]
        assert kwargs["account_id"] == "acct-1"
        assert kwargs["state_manager"] is mocks["state_manager"]
        assert kwargs["exit_policy"] is mocks["exit_policy"]
        assert kwargs["price_feed"] is mocks["price_feed"]

    def test_forwards_supervisor_self_for_safe_stop_wiring(self) -> None:
        """``supervisor=self`` keeps the PR-5/U-2 SafeStop callback live."""
        supervisor = Supervisor(clock=FixedClock(datetime(2026, 1, 1, tzinfo=UTC)))
        _attach_defaults(supervisor)
        with patch(
            "fx_ai_trading.services.exit_gate_runner.run_exit_gate",
            return_value=[],
        ) as mock_run:
            supervisor.run_exit_gate_tick()
        assert mock_run.call_args.kwargs["supervisor"] is supervisor

    def test_forwards_supervisor_clock(self) -> None:
        clock = FixedClock(datetime(2026, 1, 1, tzinfo=UTC))
        supervisor = Supervisor(clock=clock)
        _attach_defaults(supervisor)
        with patch(
            "fx_ai_trading.services.exit_gate_runner.run_exit_gate",
            return_value=[],
        ) as mock_run:
            supervisor.run_exit_gate_tick()
        assert mock_run.call_args.kwargs["clock"] is clock

    def test_forwards_default_long_side_and_none_tp_sl_context(self) -> None:
        supervisor = Supervisor(clock=FixedClock(datetime(2026, 1, 1, tzinfo=UTC)))
        _attach_defaults(supervisor)
        with patch(
            "fx_ai_trading.services.exit_gate_runner.run_exit_gate",
            return_value=[],
        ) as mock_run:
            supervisor.run_exit_gate_tick()
        kwargs = mock_run.call_args.kwargs
        assert kwargs["side"] == "long"
        assert kwargs["tp"] is None
        assert kwargs["sl"] is None
        assert kwargs["context"] is None

    def test_returns_run_exit_gate_result_unchanged(self) -> None:
        supervisor = Supervisor(clock=FixedClock(datetime(2026, 1, 1, tzinfo=UTC)))
        _attach_defaults(supervisor)
        sentinel = [MagicMock(name="ExitGateRunResult")]
        with patch(
            "fx_ai_trading.services.exit_gate_runner.run_exit_gate",
            return_value=sentinel,
        ):
            assert supervisor.run_exit_gate_tick() is sentinel


class TestAttachExitGateOptionalArgs:
    """Optional tp / sl / context / side / non-default values flow through."""

    def test_explicit_tp_sl_context_side_are_forwarded(self) -> None:
        supervisor = Supervisor(clock=FixedClock(datetime(2026, 1, 1, tzinfo=UTC)))
        broker = MagicMock()
        state_manager = MagicMock()
        state_manager.open_position_details.return_value = []
        exit_policy = MagicMock()
        price_feed = MagicMock(return_value=100.0)
        ctx = {"emergency_stop": False}

        supervisor.attach_exit_gate(
            broker=broker,
            account_id="acct-7",
            state_manager=state_manager,
            exit_policy=exit_policy,
            price_feed=price_feed,
            side="short",
            tp=110.5,
            sl=95.25,
            context=ctx,
        )

        with patch(
            "fx_ai_trading.services.exit_gate_runner.run_exit_gate",
            return_value=[],
        ) as mock_run:
            supervisor.run_exit_gate_tick()

        kwargs = mock_run.call_args.kwargs
        assert kwargs["side"] == "short"
        assert kwargs["tp"] == 110.5
        assert kwargs["sl"] == 95.25
        assert kwargs["context"] is ctx

    def test_second_attach_replaces_first(self) -> None:
        supervisor = Supervisor(clock=FixedClock(datetime(2026, 1, 1, tzinfo=UTC)))
        first = _attach_defaults(supervisor)

        new_state = MagicMock(name="state_manager_v2")
        new_state.open_position_details.return_value = []
        supervisor.attach_exit_gate(
            broker=first["broker"],
            account_id="acct-2",
            state_manager=new_state,
            exit_policy=first["exit_policy"],
            price_feed=first["price_feed"],
        )

        with patch(
            "fx_ai_trading.services.exit_gate_runner.run_exit_gate",
            return_value=[],
        ) as mock_run:
            supervisor.run_exit_gate_tick()

        kwargs = mock_run.call_args.kwargs
        assert kwargs["state_manager"] is new_state
        assert kwargs["account_id"] == "acct-2"


class TestSafeStopUnaffectedByExitGateAttach:
    """Wiring exit-gate must not perturb the SafeStop contract."""

    def test_attach_does_not_set_is_stopped(self) -> None:
        supervisor = Supervisor(clock=FixedClock(datetime(2026, 1, 1, tzinfo=UTC)))
        assert supervisor._is_stopped is False
        _attach_defaults(supervisor)
        assert supervisor._is_stopped is False

    def test_attach_does_not_set_safe_stop_completed(self) -> None:
        supervisor = Supervisor(clock=FixedClock(datetime(2026, 1, 1, tzinfo=UTC)))
        assert supervisor._safe_stop_completed is False
        _attach_defaults(supervisor)
        assert supervisor._safe_stop_completed is False

    def test_attach_does_not_grant_trading_allowed(self) -> None:
        """attach must not flip the trading gate; only startup() can."""
        supervisor = Supervisor(clock=FixedClock(datetime(2026, 1, 1, tzinfo=UTC)))
        assert supervisor.is_trading_allowed() is False
        _attach_defaults(supervisor)
        assert supervisor.is_trading_allowed() is False

    def test_safe_stop_after_attach_still_stops_tick(self) -> None:
        """End-to-end: attach → safe_stop fires → tick stays a no-op forever."""
        supervisor = Supervisor(clock=FixedClock(datetime(2026, 1, 1, tzinfo=UTC)))
        _attach_defaults(supervisor)
        # Simulate the loop-stop step of SafeStopHandler without running the
        # full handler — the public seam we care about here is _is_stopped.
        supervisor._on_loop_stop()

        with patch("fx_ai_trading.services.exit_gate_runner.run_exit_gate") as mock_run:
            assert supervisor.run_exit_gate_tick() == []
        mock_run.assert_not_called()
