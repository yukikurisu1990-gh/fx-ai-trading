"""Contract tests: close_events FSM driven through ``run_exit_gate`` (M14 / M-EXIT-1).

Migrated from the deprecated ``ExitExecutor`` path to ``run_exit_gate``
in M9/H-2 so the FSM truth lives on the post-Cycle-6.7d (I-09) write
path.  ``ExitExecutor`` itself was subsequently removed in M9/H-3c;
this file no longer imports it.

The contract being pinned (semantics unchanged from the original suite,
only the surface differs):

  No-exit decision → no broker order, no close-event write.
  Exit decision    → broker.place_order called once with the OPPOSITE
                     side, original size_units, and the same account /
                     instrument.  ``StateManager.on_close`` is then
                     invoked exactly once carrying the position's
                     ``order_id``, the ``primary_reason_code`` from
                     ``ExitDecision``, and a ``reasons`` list whose
                     ``reason_code`` set equals ``decision.reasons``.

Surface mapping vs the deprecated ``ExitExecutor`` suite
────────────────────────────────────────────────────────
  ExitExecutor.execute(...)                  → run_exit_gate(...)
  CloseEventsRepository.insert(...)          → StateManager.on_close(...)
  return value: OrderResult                  → list[ExitGateRunResult]
                                                ('closed' / 'noop' /
                                                'broker_rejected')

``state_manager`` and ``exit_policy`` are mocked because this is a
contract test for the pipeline's *interaction shape*, not for the
StateManager append-only contract (covered separately by
``tests/integration/test_state_manager*``) or the ExitPolicy rule
priority contract (covered by ``tests/unit/test_exit_policy*``).

``broker.place_order`` returns ``status='filled'`` so the gate proceeds
to the on_close write — ``broker_rejected`` paths are out of scope here.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

from fx_ai_trading.common.clock import FixedClock
from fx_ai_trading.domain.exit import ExitDecision
from fx_ai_trading.domain.state import OpenPositionInfo
from fx_ai_trading.services.exit_gate_runner import run_exit_gate

_FIXED_AT = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
_OPEN_AT = datetime(2026, 1, 1, 11, 0, 0, tzinfo=UTC)  # 1 hour before _FIXED_AT


def _make_decision(*, should_exit: bool = True, reasons=("tp",), primary_reason="tp"):
    return ExitDecision(
        position_id="pos-1",
        should_exit=should_exit,
        reasons=tuple(reasons),
        primary_reason=primary_reason if should_exit else None,
    )


def _make_position(
    *, instrument: str = "EUR_USD", order_id: str = "ord-1", units: int = 1000
) -> OpenPositionInfo:
    return OpenPositionInfo(
        instrument=instrument,
        order_id=order_id,
        units=units,
        avg_price=1.10,
        open_time_utc=_OPEN_AT,
    )


def _make_state_manager(positions: list[OpenPositionInfo]) -> MagicMock:
    sm = MagicMock(name="state_manager")
    sm.open_position_details.return_value = positions
    sm.on_close.return_value = ("snapshot-id", "close-event-id")
    return sm


def _make_exit_policy(decision: ExitDecision) -> MagicMock:
    policy = MagicMock(name="exit_policy")
    policy.evaluate.return_value = decision
    return policy


def _make_broker(*, status: str = "filled") -> MagicMock:
    broker = MagicMock(name="broker")
    broker.place_order.return_value = MagicMock(
        client_order_id="mock-client-1",
        broker_order_id="mock-close-1",
        status=status,
        filled_units=1000,
    )
    return broker


def _run(
    *,
    broker: MagicMock,
    state_manager: MagicMock,
    exit_policy: MagicMock,
    side: str = "long",
):
    return run_exit_gate(
        broker=broker,
        account_id="acc-1",
        clock=FixedClock(_FIXED_AT),
        state_manager=state_manager,
        exit_policy=exit_policy,
        price_feed=lambda _instrument: 1.20,
        side=side,
    )


# ---------------------------------------------------------------------------
# No-exit decision
# ---------------------------------------------------------------------------


class TestNoExitDecision:
    def test_returns_single_noop_result_when_no_exit(self) -> None:
        broker = _make_broker()
        state_manager = _make_state_manager([_make_position()])
        decision = _make_decision(should_exit=False, reasons=(), primary_reason=None)
        exit_policy = _make_exit_policy(decision)

        results = _run(broker=broker, state_manager=state_manager, exit_policy=exit_policy)

        assert len(results) == 1
        assert results[0].outcome == "noop"

    def test_broker_not_called_when_no_exit(self) -> None:
        broker = _make_broker()
        state_manager = _make_state_manager([_make_position()])
        decision = _make_decision(should_exit=False, reasons=(), primary_reason=None)
        exit_policy = _make_exit_policy(decision)

        _run(broker=broker, state_manager=state_manager, exit_policy=exit_policy)

        broker.place_order.assert_not_called()

    def test_state_manager_on_close_not_called_when_no_exit(self) -> None:
        broker = _make_broker()
        state_manager = _make_state_manager([_make_position()])
        decision = _make_decision(should_exit=False, reasons=(), primary_reason=None)
        exit_policy = _make_exit_policy(decision)

        _run(broker=broker, state_manager=state_manager, exit_policy=exit_policy)

        state_manager.on_close.assert_not_called()


# ---------------------------------------------------------------------------
# Exit-fired path
# ---------------------------------------------------------------------------


class TestExitDecisionExecuted:
    def test_broker_place_order_called_once(self) -> None:
        broker = _make_broker()
        state_manager = _make_state_manager([_make_position()])
        exit_policy = _make_exit_policy(_make_decision())

        _run(broker=broker, state_manager=state_manager, exit_policy=exit_policy)

        broker.place_order.assert_called_once()

    def test_closing_side_is_opposite_for_long(self) -> None:
        broker = _make_broker()
        state_manager = _make_state_manager([_make_position()])
        exit_policy = _make_exit_policy(_make_decision())

        _run(
            broker=broker,
            state_manager=state_manager,
            exit_policy=exit_policy,
            side="long",
        )

        request = broker.place_order.call_args[0][0]
        assert request.side == "short"

    def test_closing_side_is_opposite_for_short(self) -> None:
        broker = _make_broker()
        state_manager = _make_state_manager([_make_position(units=500)])
        exit_policy = _make_exit_policy(_make_decision())

        _run(
            broker=broker,
            state_manager=state_manager,
            exit_policy=exit_policy,
            side="short",
        )

        request = broker.place_order.call_args[0][0]
        assert request.side == "long"

    def test_close_size_units_matches_position(self) -> None:
        broker = _make_broker()
        state_manager = _make_state_manager([_make_position(units=750)])
        exit_policy = _make_exit_policy(_make_decision())

        _run(broker=broker, state_manager=state_manager, exit_policy=exit_policy)

        request = broker.place_order.call_args[0][0]
        assert request.size_units == 750

    def test_state_manager_on_close_called_once(self) -> None:
        broker = _make_broker()
        state_manager = _make_state_manager([_make_position()])
        exit_policy = _make_exit_policy(_make_decision())

        _run(broker=broker, state_manager=state_manager, exit_policy=exit_policy)

        state_manager.on_close.assert_called_once()

    def test_state_manager_on_close_uses_position_order_id(self) -> None:
        broker = _make_broker()
        state_manager = _make_state_manager([_make_position(order_id="my-entry-order")])
        exit_policy = _make_exit_policy(_make_decision())

        _run(broker=broker, state_manager=state_manager, exit_policy=exit_policy)

        kwargs = state_manager.on_close.call_args.kwargs
        assert kwargs["order_id"] == "my-entry-order"

    def test_state_manager_on_close_primary_reason_code_matches_decision(self) -> None:
        broker = _make_broker()
        state_manager = _make_state_manager([_make_position()])
        exit_policy = _make_exit_policy(
            _make_decision(reasons=("emergency_stop", "sl"), primary_reason="emergency_stop")
        )

        _run(broker=broker, state_manager=state_manager, exit_policy=exit_policy)

        kwargs = state_manager.on_close.call_args.kwargs
        assert kwargs["primary_reason_code"] == "emergency_stop"

    def test_state_manager_on_close_reasons_contain_all_reasons(self) -> None:
        broker = _make_broker()
        state_manager = _make_state_manager([_make_position()])
        exit_policy = _make_exit_policy(
            _make_decision(reasons=("sl", "max_holding_time"), primary_reason="sl")
        )

        _run(broker=broker, state_manager=state_manager, exit_policy=exit_policy)

        kwargs = state_manager.on_close.call_args.kwargs
        reason_codes = {r["reason_code"] for r in kwargs["reasons"]}
        assert "sl" in reason_codes
        assert "max_holding_time" in reason_codes

    def test_run_exit_gate_returns_closed_outcome_with_primary_reason(self) -> None:
        """Replaces the legacy ``execute() returns OrderResult`` contract.

        ``run_exit_gate`` does not propagate the broker's ``OrderResult``
        upward — the FSM-visible success signal is now the
        ``ExitGateRunResult(outcome='closed', primary_reason=…)`` entry
        in the returned list.  Pinning that signal here keeps the
        contract one-to-one with the deprecated test it replaces.
        """
        broker = _make_broker()
        state_manager = _make_state_manager([_make_position()])
        exit_policy = _make_exit_policy(_make_decision(primary_reason="tp"))

        results = _run(broker=broker, state_manager=state_manager, exit_policy=exit_policy)

        assert len(results) == 1
        assert results[0].outcome == "closed"
        assert results[0].primary_reason == "tp"
