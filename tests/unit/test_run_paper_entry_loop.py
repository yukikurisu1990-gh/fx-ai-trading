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
# MinimumEntrySignal: 3-point monotonic momentum
# ---------------------------------------------------------------------------


class TestMinimumEntrySignal:
    """The signal classifies the last 3 fresh quotes into a direction.

    Pinned contract: signal touches NO clock, NO feed, NO staleness — it
    receives a fresh ``Quote`` and returns ``'buy'`` / ``'sell'`` /
    ``None`` only.  Warmup spans the first 2 ticks (until 3 quotes have
    been observed).  ``ts`` value is irrelevant to the signal (only
    ``price`` is consulted), but we still build tz-aware ``Quote``
    instances because ``Quote.__post_init__`` enforces it.
    """

    _NOW = datetime(2026, 4, 23, 12, 0, 0, tzinfo=UTC)

    @staticmethod
    def _quote(mod: Any, price: float) -> Any:
        # Use the real Quote DTO so __post_init__ runs (tz-aware check).
        from fx_ai_trading.domain.price_feed import Quote

        return Quote(price=price, ts=TestMinimumEntrySignal._NOW, source="test")

    def _feed(self, mod: Any, prices: list[float]) -> str | None:
        signal = mod.MinimumEntrySignal()
        result: str | None = None
        for p in prices:
            result = signal.evaluate(self._quote(mod, p))
        return result

    def test_first_call_returns_none_warmup(self, mod: Any) -> None:
        # 1 quote — strictly less than 3 → warmup.
        assert self._feed(mod, [1.0]) is None

    def test_two_quotes_still_warmup(self, mod: Any) -> None:
        # Boundary pin: 2 quotes is still < 3, even if price moved.
        # If this ever returns 'buy', the warmup boundary regressed.
        assert self._feed(mod, [1.0, 1.1]) is None

    def test_price_up_returns_buy(self, mod: Any) -> None:
        # 3 strictly increasing prices → 'buy'.
        assert self._feed(mod, [1.0, 1.05, 1.1]) == "buy"

    def test_price_down_returns_sell(self, mod: Any) -> None:
        # 3 strictly decreasing prices → 'sell'.
        assert self._feed(mod, [1.0, 0.95, 0.9]) == "sell"

    def test_price_equal_returns_none_flat(self, mod: Any) -> None:
        # 3 equal prices → no monotonic move → None.
        assert self._feed(mod, [1.0, 1.0, 1.0]) is None

    def test_non_monotonic_returns_none(self, mod: Any) -> None:
        # Boundary pin: peak shape (up then down) is NOT monotonic.
        # Covers the strict-monotonic contract; V-shape and equality
        # mixes are derivatives of (warmup pin + monotonic pin).
        assert self._feed(mod, [1.0, 1.1, 1.05]) is None


class TestFivePointMomentumSignal:
    """The signal classifies the last 5 fresh quotes into a direction.

    Mirrors ``TestMinimumEntrySignal`` with a 5-point window.  Added in
    M10-2 as the second concrete ``EntrySignal`` implementation; not a
    production-strategy improvement.  Warmup spans the first 4 ticks
    (until 5 quotes have been observed).
    """

    _NOW = datetime(2026, 4, 23, 12, 0, 0, tzinfo=UTC)

    @staticmethod
    def _quote(mod: Any, price: float) -> Any:
        from fx_ai_trading.domain.price_feed import Quote

        return Quote(price=price, ts=TestFivePointMomentumSignal._NOW, source="test")

    def _feed(self, mod: Any, prices: list[float]) -> str | None:
        signal = mod.FivePointMomentumSignal()
        result: str | None = None
        for p in prices:
            result = signal.evaluate(self._quote(mod, p))
        return result

    def test_first_call_returns_none_warmup(self, mod: Any) -> None:
        assert self._feed(mod, [1.0]) is None

    def test_four_quotes_still_warmup(self, mod: Any) -> None:
        # Boundary pin: 4 quotes is still < 5.
        assert self._feed(mod, [1.0, 1.01, 1.02, 1.03]) is None

    def test_five_strict_up_returns_buy(self, mod: Any) -> None:
        assert self._feed(mod, [1.0, 1.01, 1.02, 1.03, 1.04]) == "buy"

    def test_five_strict_down_returns_sell(self, mod: Any) -> None:
        assert self._feed(mod, [1.0, 0.99, 0.98, 0.97, 0.96]) == "sell"

    def test_equal_mix_returns_none(self, mod: Any) -> None:
        # Flat start prevents strict monotonicity.
        assert self._feed(mod, [1.0, 1.0, 1.01, 1.02, 1.03]) is None

    def test_non_monotonic_returns_none(self, mod: Any) -> None:
        # Peak shape: up then down — not strictly monotonic.
        assert self._feed(mod, [1.0, 1.01, 1.02, 1.01, 1.03]) is None


class TestStridedMinimumEntrySignal:
    """Stride-subsampled 3-point monotonic momentum.

    Reuses the ``MinimumEntrySignal`` 3-point rule but only samples every
    ``stride``-th quote.  Four cases pin the contract from the design:

      1. ``stride=5`` + 15 strictly increasing quotes → fires exactly
         once (on the final sampling tick), confirming sampled-deque
         logic produces the same buy verdict as the un-strided signal.
      2. ``stride=5`` + sampled series is non-monotonic → never fires,
         even when intermediate (dropped) quotes form a valid streak.
      3. ``stride=5`` + fewer than 15 quotes → never fires (sampled
         deque cannot reach 3 entries before the 15th tick).
      4. ``stride=1`` invariance: identical behaviour to
         ``MinimumEntrySignal`` on the same input sequence — pins the
         "no regression when stride is a no-op" property.
    """

    _NOW = datetime(2026, 4, 23, 12, 0, 0, tzinfo=UTC)

    @staticmethod
    def _quote(price: float) -> Any:
        from fx_ai_trading.domain.price_feed import Quote

        return Quote(price=price, ts=TestStridedMinimumEntrySignal._NOW, source="test")

    def _feed_stride(self, mod: Any, prices: list[float], *, stride: int = 5) -> list[str | None]:
        signal = mod.StridedMinimumEntrySignal(stride=stride)
        return [signal.evaluate(self._quote(p)) for p in prices]

    def test_stride5_fifteen_strict_up_fires_exactly_once(self, mod: Any) -> None:
        # 15 strictly increasing ticks → sampled indices 0/5/10 are the
        # 3 deque entries (prices 1.00 < 1.05 < 1.10) → 'buy' on tick 10.
        # Every other tick returns None (non-sampling or warmup).
        prices = [1.00 + 0.01 * i for i in range(15)]

        results = self._feed_stride(mod, prices, stride=5)

        fires = [i for i, r in enumerate(results) if r is not None]
        assert fires == [10]
        assert results[10] == "buy"

    def test_stride5_sampled_series_non_monotonic_never_fires(self, mod: Any) -> None:
        # Sampled prices at indices 0/5/10 = 1.00, 1.05, 1.00 (down at
        # the end).  Intermediate quotes go up strictly — confirming the
        # signal ignores dropped quotes and only the sampled series is
        # checked for monotonicity.
        prices = [1.00, 1.10, 1.20, 1.30, 1.40, 1.05, 1.15, 1.25, 1.35, 1.45, 1.00]

        results = self._feed_stride(mod, prices, stride=5)

        assert all(r is None for r in results)

    def test_stride5_fewer_than_fifteen_ticks_stays_in_warmup(self, mod: Any) -> None:
        # 14 ticks — sampled indices 0/5/10 need a 15th observation (or
        # rather, the 11th tick is the 3rd sample; but with 14 ticks we
        # only reach the 3rd sample at index 10, and the remainder is
        # non-sampling).  Confirm 10 ticks (only 2 samples at 0/5) is
        # still warmup — boundary pin against an off-by-one regression.
        prices = [1.00 + 0.01 * i for i in range(10)]

        results = self._feed_stride(mod, prices, stride=5)

        assert all(r is None for r in results)

    def test_stride1_reduces_to_minimum_entry_signal(self, mod: Any) -> None:
        # Invariance: stride=1 means every tick is sampled → behaviour
        # must exactly match ``MinimumEntrySignal`` on the same prices.
        prices = [1.00, 1.05, 1.10, 1.08, 1.12, 1.15, 1.20, 1.18, 1.10, 1.05]

        strided = mod.StridedMinimumEntrySignal(stride=1)
        baseline = mod.MinimumEntrySignal()

        strided_out = [strided.evaluate(self._quote(p)) for p in prices]
        baseline_out = [baseline.evaluate(self._quote(p)) for p in prices]

        assert strided_out == baseline_out


class TestMeanReversionEntrySignal:
    """3-point mean-reversion (counter-trend) signal.

    Mirrors the ``MinimumEntrySignal`` 3-point window but inverts the
    verdict: strict-up sequences produce ``'sell'`` (fade the rally),
    strict-down sequences produce ``'buy'`` (fade the dip).  Four cases
    pin the contract:

      1. 3 strictly increasing prices → ``'sell'`` (verdict inverted vs
         ``MinimumEntrySignal`` which would emit ``'buy'``).
      2. 3 strictly decreasing prices → ``'buy'`` (inverted from
         ``'sell'``).
      3. Warmup: fewer than 3 quotes → ``None`` for every prefix tick.
      4. Inversion-vs-momentum invariance: on a sequence of arbitrary
         prices, ``MeanReversionEntrySignal`` output is the
         direction-swapped image of ``MinimumEntrySignal`` output
         (``'buy'``↔``'sell'``, ``None``→``None``).  Pins both the
         "verdict inversion" rule and the "same warmup / same
         non-monotonic gating" properties in one assertion.
    """

    _NOW = datetime(2026, 4, 23, 12, 0, 0, tzinfo=UTC)

    @staticmethod
    def _quote(price: float) -> Any:
        from fx_ai_trading.domain.price_feed import Quote

        return Quote(price=price, ts=TestMeanReversionEntrySignal._NOW, source="test")

    def _feed(self, mod: Any, prices: list[float]) -> list[str | None]:
        signal = mod.MeanReversionEntrySignal()
        return [signal.evaluate(self._quote(p)) for p in prices]

    def test_strict_up_sequence_fires_sell(self, mod: Any) -> None:
        prices = [1.00, 1.05, 1.10]

        results = self._feed(mod, prices)

        assert results == [None, None, "sell"]

    def test_strict_down_sequence_fires_buy(self, mod: Any) -> None:
        prices = [1.10, 1.05, 1.00]

        results = self._feed(mod, prices)

        assert results == [None, None, "buy"]

    def test_warmup_fewer_than_three_quotes_returns_none(self, mod: Any) -> None:
        # First two ticks must always be None regardless of monotonicity
        # — the deque cannot have 3 entries yet.
        prices = [1.00, 1.05]

        results = self._feed(mod, prices)

        assert results == [None, None]

    def test_inversion_invariance_vs_minimum_entry_signal(self, mod: Any) -> None:
        # On the same input, MeanReversionEntrySignal must emit the
        # buy/sell-swapped image of MinimumEntrySignal.  None positions
        # (warmup, flat, non-monotonic) must coincide exactly — pinning
        # that both signals share the same gating and only the verdict
        # axis is inverted.
        prices = [1.00, 1.05, 1.10, 1.08, 1.12, 1.15, 1.20, 1.18, 1.10, 1.05]

        reversion = mod.MeanReversionEntrySignal()
        momentum = mod.MinimumEntrySignal()

        rev_out = [reversion.evaluate(self._quote(p)) for p in prices]
        mom_out = [momentum.evaluate(self._quote(p)) for p in prices]

        swap = {"buy": "sell", "sell": "buy", None: None}
        assert rev_out == [swap[v] for v in mom_out]


class TestDownMomentumSignal:
    """One-sided 3-point momentum: fires only on strict-down (sell).

    Asymmetric variant of ``MinimumEntrySignal`` that drops the buy
    side entirely.  Four cases pin the contract:

      1. 3 strictly decreasing prices → ``'sell'``.
      2. 3 strictly increasing prices → ``None`` (asymmetry — does NOT
         fire on up-trends; this is the load-bearing difference vs
         ``MinimumEntrySignal``).
      3. Warmup: fewer than 3 quotes → ``None`` for every prefix tick.
      4. Asymmetry-vs-momentum invariance: on a shared price series,
         output equals ``MinimumEntrySignal`` output **only when** that
         output is ``'sell'``; otherwise ``None``.  Pins both the
         "down rule matches MinimumEntrySignal" and "up rule is
         dropped" properties in one assertion.
    """

    _NOW = datetime(2026, 4, 23, 12, 0, 0, tzinfo=UTC)

    @staticmethod
    def _quote(price: float) -> Any:
        from fx_ai_trading.domain.price_feed import Quote

        return Quote(price=price, ts=TestDownMomentumSignal._NOW, source="test")

    def _feed(self, mod: Any, prices: list[float]) -> list[str | None]:
        signal = mod.DownMomentumSignal()
        return [signal.evaluate(self._quote(p)) for p in prices]

    def test_strict_down_sequence_fires_sell(self, mod: Any) -> None:
        prices = [1.10, 1.05, 1.00]

        results = self._feed(mod, prices)

        assert results == [None, None, "sell"]

    def test_strict_up_sequence_returns_none(self, mod: Any) -> None:
        # Critical asymmetry: an up-streak that would fire 'buy' under
        # MinimumEntrySignal must produce None here.
        prices = [1.00, 1.05, 1.10]

        results = self._feed(mod, prices)

        assert results == [None, None, None]

    def test_warmup_fewer_than_three_quotes_returns_none(self, mod: Any) -> None:
        prices = [1.10, 1.05]

        results = self._feed(mod, prices)

        assert results == [None, None]

    def test_asymmetry_vs_minimum_entry_signal(self, mod: Any) -> None:
        # On the same input, DownMomentumSignal must equal
        # MinimumEntrySignal where the latter said 'sell', and None
        # everywhere else (including positions where MinimumEntrySignal
        # said 'buy').  Pins the one-sided contract.
        prices = [1.00, 1.05, 1.10, 1.08, 1.12, 1.15, 1.20, 1.18, 1.10, 1.05]

        down = mod.DownMomentumSignal()
        momentum = mod.MinimumEntrySignal()

        down_out = [down.evaluate(self._quote(p)) for p in prices]
        mom_out = [momentum.evaluate(self._quote(p)) for p in prices]

        assert down_out == [v if v == "sell" else None for v in mom_out]


class TestMinimumEntryPickerLogic:
    """Priority picker: first-non-None wins; direction mismatch → no_signal.

    Uses MagicMock signals with fixed return values to isolate picker
    behaviour from price-comparison logic.  Pins the M10-3 contract:
      - ordered evaluation: first non-None is adopted, rest are skipped
      - all-None → no_signal
      - direction mismatch on adopted signal → no_signal (NOT ok)
    """

    _NOW = datetime(2026, 4, 23, 12, 0, 0, tzinfo=UTC)

    @staticmethod
    def _build_multi(
        mod: Any,
        *,
        signals_returns: list[str | None],
        direction: str = "buy",
    ) -> Any:
        sm = MagicMock()
        sm.open_instruments.return_value = frozenset()
        clock = MagicMock()
        clock.now.return_value = TestMinimumEntryPickerLogic._NOW
        feed = MagicMock()
        feed.get_quote.return_value = MagicMock(
            price=1.0,
            ts=TestMinimumEntryPickerLogic._NOW,
            source="x",
        )
        signals = [MagicMock(evaluate=MagicMock(return_value=r)) for r in signals_returns]
        return mod.MinimumEntryPolicy(
            instrument="EUR_USD",
            direction=direction,
            state_manager=sm,
            quote_feed=feed,
            clock=clock,
            signals=signals,
            stale_after_seconds=60.0,
        )

    def test_all_signals_none_returns_no_signal(self, mod: Any) -> None:
        policy = self._build_multi(mod, signals_returns=[None, None])
        decision = policy.evaluate()
        assert decision.should_fire is False
        assert decision.reason == "no_signal"

    def test_first_none_second_buy_fires(self, mod: Any) -> None:
        # Picker falls through first (None) and adopts second ('buy').
        policy = self._build_multi(mod, signals_returns=[None, "buy"], direction="buy")
        decision = policy.evaluate()
        assert decision.should_fire is True
        assert decision.reason == "ok"

    def test_first_buy_wins_over_second_sell(self, mod: Any) -> None:
        # 'buy' is non-None → adopted; 'sell' is never consulted.
        policy = self._build_multi(mod, signals_returns=["buy", "sell"], direction="buy")
        decision = policy.evaluate()
        assert decision.should_fire is True
        assert decision.reason == "ok"

    def test_first_sell_direction_mismatch_returns_no_signal(self, mod: Any) -> None:
        # first non-None = 'sell'; configured direction = 'buy' → mismatch → no_signal.
        # Proves direction mismatch on the adopted signal does not fall through to next.
        policy = self._build_multi(mod, signals_returns=["sell"], direction="buy")
        decision = policy.evaluate()
        assert decision.should_fire is False
        assert decision.reason == "no_signal"
