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

M-3b additions:
  - A ``QuoteFeed`` passed to ``attach_exit_gate`` is stored as-is and
    forwarded by reference to ``run_exit_gate`` (no double-wrap).
  - A legacy ``Callable[[str], float]`` is wrapped once at attach-time
    via ``callable_to_quote_feed(fn, clock=self._clock)``; the stored
    attachment is then a ``QuoteFeed`` whose ``get_quote`` returns the
    callable's output.

These tests use mocks for ``Broker`` / ``StateManager`` / ``ExitPolicyService``
because the goal is to verify *the wiring*, not to re-test the gate
itself (which has its own contract suite under ``tests/contract``).
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from fx_ai_trading.common.clock import FixedClock
from fx_ai_trading.domain.price_feed import Quote, QuoteFeed
from fx_ai_trading.supervisor.supervisor import Supervisor


class _StubQuoteFeed:
    """Minimal QuoteFeed implementation for wiring tests."""

    def __init__(self, price: float) -> None:
        self._price = price

    def get_quote(self, instrument: str) -> Quote:
        return Quote(
            price=self._price,
            ts=datetime(2026, 1, 1, tzinfo=UTC),
            source="test_fixture",
        )


def _attach_defaults(supervisor: Supervisor) -> dict[str, object]:
    """Attach a minimal mock exit-gate config and return the mocks."""
    broker = MagicMock(name="broker")
    state_manager = MagicMock(name="state_manager")
    state_manager.open_position_details.return_value = []
    exit_policy = MagicMock(name="exit_policy")
    quote_feed = _StubQuoteFeed(price=100.0)

    supervisor.attach_exit_gate(
        broker=broker,
        account_id="acct-1",
        state_manager=state_manager,
        exit_policy=exit_policy,
        quote_feed=quote_feed,
    )
    return {
        "broker": broker,
        "state_manager": state_manager,
        "exit_policy": exit_policy,
        "quote_feed": quote_feed,
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
        # M-3b: the QuoteFeed-typed input is stored & forwarded by reference
        # (no wrapping when already a QuoteFeed).
        assert kwargs["quote_feed"] is mocks["quote_feed"]
        # M-3b: the kwarg name was renamed from price_feed to quote_feed.
        assert "price_feed" not in kwargs

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

    def test_forwards_default_none_tp_sl_context(self) -> None:
        supervisor = Supervisor(clock=FixedClock(datetime(2026, 1, 1, tzinfo=UTC)))
        _attach_defaults(supervisor)
        with patch(
            "fx_ai_trading.services.exit_gate_runner.run_exit_gate",
            return_value=[],
        ) as mock_run:
            supervisor.run_exit_gate_tick()
        kwargs = mock_run.call_args.kwargs
        # M-1b: side is no longer forwarded (derived per-position by run_exit_gate).
        assert "side" not in kwargs
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
    """Optional tp / sl / context / non-default values flow through."""

    def test_explicit_tp_sl_context_are_forwarded(self) -> None:
        supervisor = Supervisor(clock=FixedClock(datetime(2026, 1, 1, tzinfo=UTC)))
        broker = MagicMock()
        state_manager = MagicMock()
        state_manager.open_position_details.return_value = []
        exit_policy = MagicMock()
        quote_feed = _StubQuoteFeed(price=100.0)
        ctx = {"emergency_stop": False}

        supervisor.attach_exit_gate(
            broker=broker,
            account_id="acct-7",
            state_manager=state_manager,
            exit_policy=exit_policy,
            quote_feed=quote_feed,
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
        # M-1b: side is no longer forwarded.
        assert "side" not in kwargs
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
            quote_feed=first["quote_feed"],
        )

        with patch(
            "fx_ai_trading.services.exit_gate_runner.run_exit_gate",
            return_value=[],
        ) as mock_run:
            supervisor.run_exit_gate_tick()

        kwargs = mock_run.call_args.kwargs
        assert kwargs["state_manager"] is new_state
        assert kwargs["account_id"] == "acct-2"


class TestAttachExitGateLegacyCallable:
    """M-3b: a legacy Callable[[str], float] is wrapped at attach-time
    via ``callable_to_quote_feed(fn, clock=self._clock)`` so the stored
    attachment is always a QuoteFeed.  This is the back-compat seam that
    lets every existing caller keep its lambda contract while the
    consumer side reads through ``.get_quote(...).price``.
    """

    def test_callable_is_wrapped_into_quote_feed(self) -> None:
        clock = FixedClock(datetime(2026, 1, 1, tzinfo=UTC))
        supervisor = Supervisor(clock=clock)
        broker = MagicMock(name="broker")
        state_manager = MagicMock(name="state_manager")
        state_manager.open_position_details.return_value = []
        exit_policy = MagicMock(name="exit_policy")

        legacy: object = lambda _instrument: 100.0  # noqa: E731

        supervisor.attach_exit_gate(
            broker=broker,
            account_id="acct-legacy",
            state_manager=state_manager,
            exit_policy=exit_policy,
            quote_feed=legacy,
        )

        with patch(
            "fx_ai_trading.services.exit_gate_runner.run_exit_gate",
            return_value=[],
        ) as mock_run:
            supervisor.run_exit_gate_tick()

        forwarded = mock_run.call_args.kwargs["quote_feed"]
        # The forwarded object is NOT the original callable…
        assert forwarded is not legacy
        # …it satisfies the QuoteFeed runtime_checkable contract…
        assert isinstance(forwarded, QuoteFeed)
        # …and the wrapped get_quote returns the legacy callable's output.
        q = forwarded.get_quote("EUR_USD")
        assert q.price == 100.0
        assert q.source == "legacy_callable"
        # ts is synthesized from the supervisor's clock.
        assert q.ts == clock.now()

    def test_quote_feed_passthrough_is_not_rewrapped(self) -> None:
        """Counterpart to the wrap test: a QuoteFeed input must be
        stored and forwarded by reference (no double-wrap).
        """
        supervisor = Supervisor(clock=FixedClock(datetime(2026, 1, 1, tzinfo=UTC)))
        broker = MagicMock(name="broker")
        state_manager = MagicMock(name="state_manager")
        state_manager.open_position_details.return_value = []
        exit_policy = MagicMock(name="exit_policy")
        quote_feed = _StubQuoteFeed(price=42.0)

        supervisor.attach_exit_gate(
            broker=broker,
            account_id="acct-passthrough",
            state_manager=state_manager,
            exit_policy=exit_policy,
            quote_feed=quote_feed,
        )

        with patch(
            "fx_ai_trading.services.exit_gate_runner.run_exit_gate",
            return_value=[],
        ) as mock_run:
            supervisor.run_exit_gate_tick()

        assert mock_run.call_args.kwargs["quote_feed"] is quote_feed


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
