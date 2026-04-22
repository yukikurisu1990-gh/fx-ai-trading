"""Unit tests for ``scripts/run_paper_entry_loop``.

Scope is deliberately minimal.  The user's Loop 3 contract pins three
behaviours and forbids further over-coverage:

  1. ``_open_one_position`` calls collaborators in the exact 5-step
     order:
         ['create_order',
          'update_status(SUBMITTED)',
          'place_order',
          'update_status(FILLED)',
          'on_fill']
     pinned via a single call list (MagicMock side_effect → list.append).

  2. On broker rejection, the FILLED transition does NOT happen and
     ``on_fill`` is NOT called.  Pinned via the same call sequence.

  3. (idempotency is pinned in the integration test, not here.)

Plus the bare minimum required to keep the script's contracts honest:
  - duplicate pre-flight raises ``DuplicateOpenInstrumentError``
    (the Loop 2 contract: duplicate guard MUST be the typed exception).
  - ``MinimumEntryPolicy.evaluate`` returns the right reason for each
    of the 4 branches (already_open / no_quote / stale_quote / ok) —
    this is the new logic the script introduces, so a single sweep is
    warranted.
"""

from __future__ import annotations

import importlib.util
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

# scripts/ is not a package — load via importlib (same pattern as
# tests/unit/test_paper_open_position.py).
_SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "run_paper_entry_loop.py"


def _load_script_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "scripts.run_paper_entry_loop_for_unit_test", _SCRIPT_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def mod() -> Any:
    return _load_script_module()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_components(mod: Any, calls: list[str], *, broker_status: str = "filled") -> Any:
    """Build EntryComponents with MagicMock collaborators that append to ``calls``.

    The ``calls`` list is the single ordering pin used by the test.
    Every collaborator method that participates in the 5-step sequence
    appends one of these tokens:
        'create_order' / 'update_status(SUBMITTED)' /
        'update_status(FILLED)' / 'place_order' / 'on_fill'
    """
    sm = MagicMock()
    sm.open_instruments.return_value = frozenset()  # pre-flight passes

    def _on_fill(*, order_id: str, instrument: str, units: int, avg_price: float) -> str:
        calls.append("on_fill")
        return "psid-" + order_id[:6]

    sm.on_fill.side_effect = _on_fill

    orders = MagicMock()
    orders.create_order.side_effect = lambda *a, **kw: calls.append("create_order")

    def _update_status(order_id: str, new_status: str, context: Any) -> None:
        calls.append(f"update_status({new_status})")

    orders.update_status.side_effect = _update_status

    broker = MagicMock()

    def _place_order(request: Any) -> Any:
        calls.append("place_order")
        return MagicMock(
            status=broker_status,
            fill_price=1.0 if broker_status == "filled" else None,
            message=None if broker_status == "filled" else "rejected",
        )

    broker.place_order.side_effect = _place_order

    feed = MagicMock()
    clock = MagicMock()
    signal = MagicMock()

    return mod.EntryComponents(
        state_manager=sm,
        orders=orders,
        broker=broker,
        quote_feed=feed,
        clock=clock,
        signal=signal,
    )


# ---------------------------------------------------------------------------
# Pin #1: 5-step call order
# ---------------------------------------------------------------------------


class TestOpenOnePosition5StepOrder:
    """The 5-step FSM orchestration is pinned in exact order."""

    def test_happy_path_pins_exact_5_step_order(self, mod: Any) -> None:
        calls: list[str] = []
        components = _make_components(mod, calls)
        log = MagicMock()

        mod._open_one_position(
            instrument="EUR_USD",
            direction="buy",
            units=1000,
            account_id="acct-1",
            account_type="demo",
            components=components,
            log=log,
        )

        assert calls == [
            "create_order",
            "update_status(SUBMITTED)",
            "place_order",
            "update_status(FILLED)",
            "on_fill",
        ]


# ---------------------------------------------------------------------------
# Pin #2: broker_rejected sequence
# ---------------------------------------------------------------------------


class TestOpenOnePositionBrokerRejected:
    """Broker rejection aborts BEFORE the FILLED transition and on_fill."""

    def test_broker_rejected_sequence_omits_filled_and_on_fill(self, mod: Any) -> None:
        calls: list[str] = []
        components = _make_components(mod, calls, broker_status="rejected")
        log = MagicMock()

        with pytest.raises(mod.BrokerDidNotFillError):
            mod._open_one_position(
                instrument="EUR_USD",
                direction="buy",
                units=1000,
                account_id="acct-1",
                account_type="demo",
                components=components,
                log=log,
            )

        # Exact rejected-path sequence — no FILLED, no on_fill.
        assert calls == [
            "create_order",
            "update_status(SUBMITTED)",
            "place_order",
        ]
        assert "update_status(FILLED)" not in calls
        assert "on_fill" not in calls


# ---------------------------------------------------------------------------
# Loop 2 contract: duplicate guard MUST raise DuplicateOpenInstrumentError
# ---------------------------------------------------------------------------


class TestOpenOnePositionDuplicateGuard:
    """Duplicate pre-flight is the typed exception, never a return-value flag."""

    def test_duplicate_open_raises_typed_exception_and_writes_nothing(self, mod: Any) -> None:
        calls: list[str] = []
        components = _make_components(mod, calls)
        # Pre-flight: instrument is already open.
        components.state_manager.open_instruments.return_value = frozenset({"EUR_USD"})
        log = MagicMock()

        with pytest.raises(mod.DuplicateOpenInstrumentError):
            mod._open_one_position(
                instrument="EUR_USD",
                direction="buy",
                units=1000,
                account_id="acct-1",
                account_type="demo",
                components=components,
                log=log,
            )

        # No write happened — none of the 5 steps ran.
        assert calls == []


# ---------------------------------------------------------------------------
# MinimumEntryPolicy: 5-branch decision (already_open / no_quote /
# stale_quote / no_signal / ok)
# ---------------------------------------------------------------------------


class TestMinimumEntryPolicy:
    """Each of the 5 reason branches is reachable and labelled correctly.

    The signal layer is injected as a MagicMock so we can pin each
    branch without exercising the price-comparison logic (that lives in
    ``TestMinimumEntrySignal`` below).
    """

    @staticmethod
    def _build(
        mod: Any,
        *,
        open_set: frozenset[str],
        quote_age_seconds: float | None,
        feed_raises: bool = False,
        stale_after_seconds: float = 60.0,
        direction: str = "buy",
        signal_returns: str | None = "buy",
    ) -> Any:
        sm = MagicMock()
        sm.open_instruments.return_value = open_set

        clock = MagicMock()
        now = datetime(2026, 4, 23, 12, 0, 0, tzinfo=UTC)
        clock.now.return_value = now

        feed = MagicMock()
        if feed_raises:
            feed.get_quote.side_effect = RuntimeError("simulated feed outage")
        else:
            assert quote_age_seconds is not None
            quote_ts = now - timedelta(seconds=quote_age_seconds)
            feed.get_quote.return_value = MagicMock(price=1.0, ts=quote_ts, source="x")

        signal = MagicMock()
        signal.evaluate.return_value = signal_returns

        return mod.MinimumEntryPolicy(
            instrument="EUR_USD",
            direction=direction,
            state_manager=sm,
            quote_feed=feed,
            clock=clock,
            signal=signal,
            stale_after_seconds=stale_after_seconds,
        )

    def test_already_open(self, mod: Any) -> None:
        policy = self._build(mod, open_set=frozenset({"EUR_USD"}), quote_age_seconds=0.0)
        decision = policy.evaluate()
        assert decision.should_fire is False
        assert decision.reason == "already_open"

    def test_no_quote(self, mod: Any) -> None:
        policy = self._build(mod, open_set=frozenset(), quote_age_seconds=None, feed_raises=True)
        decision = policy.evaluate()
        assert decision.should_fire is False
        assert decision.reason == "no_quote"

    def test_stale_quote(self, mod: Any) -> None:
        # 120s old, threshold 60s → stale (strict >).
        policy = self._build(mod, open_set=frozenset(), quote_age_seconds=120.0)
        decision = policy.evaluate()
        assert decision.should_fire is False
        assert decision.reason == "stale_quote"
        assert decision.age_seconds == pytest.approx(120.0)

    def test_no_signal_when_signal_returns_none(self, mod: Any) -> None:
        # Fresh quote, but signal returned None (warmup or flat).
        policy = self._build(mod, open_set=frozenset(), quote_age_seconds=10.0, signal_returns=None)
        decision = policy.evaluate()
        assert decision.should_fire is False
        assert decision.reason == "no_signal"
        assert decision.age_seconds == pytest.approx(10.0)

    def test_no_signal_when_direction_mismatch(self, mod: Any) -> None:
        # Signal says 'sell' but runner is configured for 'buy' →
        # collapses into the same no_signal reason (no new event).
        policy = self._build(
            mod,
            open_set=frozenset(),
            quote_age_seconds=10.0,
            direction="buy",
            signal_returns="sell",
        )
        decision = policy.evaluate()
        assert decision.should_fire is False
        assert decision.reason == "no_signal"
        assert decision.age_seconds == pytest.approx(10.0)

    def test_ok(self, mod: Any) -> None:
        policy = self._build(
            mod,
            open_set=frozenset(),
            quote_age_seconds=10.0,
            direction="buy",
            signal_returns="buy",
        )
        decision = policy.evaluate()
        assert decision.should_fire is True
        assert decision.reason == "ok"
        assert decision.age_seconds == pytest.approx(10.0)


# ---------------------------------------------------------------------------
# MinimumEntrySignal: warmup / up / down / flat
# ---------------------------------------------------------------------------


class TestMinimumEntrySignal:
    """The signal classifies consecutive fresh-quote moves into a direction.

    Pinned contract: signal touches NO clock, NO feed, NO staleness — it
    receives a fresh ``Quote`` and returns ``'buy'`` / ``'sell'`` /
    ``None`` only.  ``ts`` value is irrelevant to the signal (only
    ``price`` is consulted), but we still build tz-aware ``Quote``
    instances because ``Quote.__post_init__`` enforces it.
    """

    _NOW = datetime(2026, 4, 23, 12, 0, 0, tzinfo=UTC)

    @staticmethod
    def _quote(mod: Any, price: float) -> Any:
        # Use the real Quote DTO so __post_init__ runs (tz-aware check).
        from fx_ai_trading.domain.price_feed import Quote

        return Quote(price=price, ts=TestMinimumEntrySignal._NOW, source="test")

    def test_first_call_returns_none_warmup(self, mod: Any) -> None:
        signal = mod.MinimumEntrySignal()
        assert signal.evaluate(self._quote(mod, 1.0)) is None

    def test_price_up_returns_buy(self, mod: Any) -> None:
        signal = mod.MinimumEntrySignal()
        signal.evaluate(self._quote(mod, 1.0))  # warmup
        assert signal.evaluate(self._quote(mod, 1.1)) == "buy"

    def test_price_down_returns_sell(self, mod: Any) -> None:
        signal = mod.MinimumEntrySignal()
        signal.evaluate(self._quote(mod, 1.1))  # warmup
        assert signal.evaluate(self._quote(mod, 1.0)) == "sell"

    def test_price_equal_returns_none_flat(self, mod: Any) -> None:
        signal = mod.MinimumEntrySignal()
        signal.evaluate(self._quote(mod, 1.0))  # warmup
        assert signal.evaluate(self._quote(mod, 1.0)) is None
