"""Integration: ``scripts/run_paper_entry_loop`` round-trips against SQLite.

Exercises the full open-side cadence path end-to-end:

  policy.evaluate() → _open_one_position →
    create_order → update_status(SUBMITTED) → PaperBroker.place_order →
    update_status(FILLED) → StateManager.on_fill

with a deterministic ``_SequentialQuoteFeed`` stub that returns a
pre-defined sequence of fresh quotes (one per tick), and asserts the
user's Loop 3 contract under the **3-point monotonic momentum signal**
layer:

  - the first 2 ticks are always warmup no-ops (signal needs 3 quotes
    to compare → policy reason='no_signal').
  - 3-tick / direction-matching sequence ([1.0, 1.05, 1.1] + buy) →
    exactly 1 open is written on tick 3.
  - 4-tick / direction-matching sequence ([1.0, 1.05, 1.1, 1.15] +
    buy) → tick 4 is blocked by 'already_open' (still 1 open / 1
    position).
  - 3-tick direction-mismatch sequence ([1.0, 0.95, 0.9] + buy) → 0
    opens (signal points 'sell', policy collapses to reason='no_signal').

The paper components here are **production** code (``PaperBroker`` +
real ``StateManager`` + real ``OrdersRepository`` +
``MinimumEntryPolicy`` + real ``MinimumEntrySignal``).  Only the engine
(in-memory SQLite) and the quote feed (a deterministic sequential
stub) are test-side substitutions.

In-memory SQLite + DDL is reused verbatim from
``tests/integration/test_paper_open_position_bootstrap.py`` so both
tests exercise the same columns.  Foreign keys are intentionally
omitted (matches the convention).

Out of scope (NOT asserted here — split a separate PR if needed):

- Exit round-trip (open → close) — covered by
  ``tests/integration/test_paper_loop_close_path.py``.
- Full per-branch policy assertions (already covered by the unit test).
- Logging output / log file format.
"""

from __future__ import annotations

import importlib.util
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import create_engine, text

_SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "run_paper_entry_loop.py"


def _load_script_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "scripts.run_paper_entry_loop_for_integration_test", _SCRIPT_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_ACCOUNT_ID = "__test_account_entry_loop__"
_INSTRUMENT = "EUR_USD"


# --- DDL ---------------------------------------------------------------------
# Same shape as test_paper_open_position_bootstrap.py / test_paper_loop_close_path.py.

_DDL_ORDERS = """
CREATE TABLE orders (
    order_id          TEXT PRIMARY KEY,
    client_order_id   TEXT,
    trading_signal_id TEXT,
    account_id        TEXT NOT NULL,
    instrument        TEXT NOT NULL,
    account_type      TEXT NOT NULL,
    order_type        TEXT NOT NULL,
    direction         TEXT NOT NULL,
    units             NUMERIC(18,4) NOT NULL,
    status            TEXT NOT NULL DEFAULT 'PENDING',
    submitted_at      TEXT,
    filled_at         TEXT,
    canceled_at       TEXT,
    correlation_id    TEXT,
    created_at        TEXT NOT NULL DEFAULT (datetime('now'))
)
"""

_DDL_POSITIONS = """
CREATE TABLE positions (
    position_snapshot_id TEXT PRIMARY KEY,
    order_id             TEXT,
    account_id           TEXT NOT NULL,
    instrument           TEXT NOT NULL,
    event_type           TEXT NOT NULL,
    units                NUMERIC(18,4) NOT NULL,
    avg_price            NUMERIC(18,8),
    unrealized_pl        NUMERIC(18,8),
    realized_pl          NUMERIC(18,8),
    event_time_utc       TEXT NOT NULL,
    correlation_id       TEXT
)
"""

_DDL_OUTBOX = """
CREATE TABLE secondary_sync_outbox (
    outbox_id       TEXT PRIMARY KEY,
    table_name      TEXT NOT NULL,
    primary_key     TEXT NOT NULL,
    version_no      BIGINT NOT NULL DEFAULT 0,
    payload_json    TEXT NOT NULL,
    enqueued_at     TEXT NOT NULL,
    acked_at        TEXT,
    last_error      TEXT,
    attempt_count   INTEGER NOT NULL DEFAULT 0,
    next_attempt_at TEXT,
    run_id          TEXT,
    environment     TEXT,
    code_version    TEXT,
    config_version  TEXT
)
"""


@pytest.fixture
def engine():
    eng = create_engine("sqlite:///:memory:")
    with eng.begin() as conn:
        conn.execute(text(_DDL_ORDERS))
        conn.execute(text(_DDL_POSITIONS))
        conn.execute(text(_DDL_OUTBOX))
    try:
        yield eng
    finally:
        eng.dispose()


@pytest.fixture(scope="module")
def mod() -> Any:
    return _load_script_module()


# Fixed instant shared by the stub clock and the stub quote's ts.  Using
# a deterministic pair keeps the staleness math at age == 0s regardless
# of when the test runs, so we never need datetime.now().  Repo rule
# (development_rules.md §13.1) forbids datetime.now() outside WallClock.
_FIXED_NOW = datetime(2026, 4, 23, 12, 0, 0, tzinfo=UTC)


class _SequentialQuoteFeed:
    """Deterministic ``QuoteFeed`` returning a fixed price sequence.

    One ``Quote`` per tick.  ``ts`` is pinned to ``_FIXED_NOW`` so the
    policy's stale gate (M-3c) never trips against the same
    ``FixedClock``: any no-op observed in these tests is therefore
    attributable to the signal layer (warmup / flat / direction
    mismatch) or to ``already_open``, NOT to staleness.

    After the sequence is exhausted, the last quote is returned
    indefinitely (sticky tail).  Tests that care about exhaustion
    bound ``max_iterations`` to ``len(prices)``.
    """

    def __init__(self, prices: list[float]) -> None:
        from fx_ai_trading.domain.price_feed import Quote

        self._quotes = [Quote(price=p, ts=_FIXED_NOW, source="test-seq") for p in prices]
        self._idx = 0

    def get_quote(self, instrument: str) -> Any:  # noqa: ARG002 — single-instrument runner
        quote = self._quotes[min(self._idx, len(self._quotes) - 1)]
        self._idx += 1
        return quote


def _build_components_with_sequential_feed(
    mod: Any, engine: Any, prices: list[float], signal: Any = None
) -> Any:
    """Compose the real paper open-side stack with a ``_SequentialQuoteFeed``.

    Avoids ``build_components`` so we don't have to pass real OANDA
    credentials.  The ``signal`` parameter accepts any ``EntrySignal``-
    conforming instance; defaults to ``MinimumEntrySignal()`` to preserve
    existing test behaviour.  M10-2 integration test passes
    ``FivePointMomentumSignal()`` here to validate the Protocol seam.
    """
    from fx_ai_trading.adapters.broker.paper import PaperBroker
    from fx_ai_trading.common.clock import FixedClock
    from fx_ai_trading.repositories.orders import OrdersRepository
    from fx_ai_trading.services.state_manager import StateManager

    clock = FixedClock(_FIXED_NOW)
    return mod.EntryComponents(
        state_manager=StateManager(engine, account_id=_ACCOUNT_ID, clock=clock),
        orders=OrdersRepository(engine),
        broker=PaperBroker(account_type="demo", nominal_price=1.0),
        quote_feed=_SequentialQuoteFeed(prices),
        clock=clock,
        signal=signal if signal is not None else mod.MinimumEntrySignal(),
    )


def _run(
    mod: Any,
    components: Any,
    *,
    direction: str,
    max_iterations: int,
    signals: Any = None,
) -> int:
    policy_signal_kwargs = (
        {"signals": signals} if signals is not None else {"signal": components.signal}
    )
    policy = mod.MinimumEntryPolicy(
        instrument=_INSTRUMENT,
        direction=direction,
        state_manager=components.state_manager,
        quote_feed=components.quote_feed,
        clock=components.clock,
        stale_after_seconds=60.0,
        **policy_signal_kwargs,
    )
    log = logging.getLogger("test_paper_entry_loop_open_path")
    return mod.run_loop(
        components=components,
        policy=policy,
        instrument=_INSTRUMENT,
        direction=direction,
        units=1000,
        account_id=_ACCOUNT_ID,
        account_type="demo",
        interval_seconds=0.0,
        max_iterations=max_iterations,
        log=log,
        should_stop=lambda: False,
        sleep_fn=lambda _s: None,
        monotonic_fn=lambda: 0.0,
    )


# ---------------------------------------------------------------------------
# Signal-driven open contract (replaces the v1 availability-only pins)
# ---------------------------------------------------------------------------


class TestPaperEntryLoopSignalDriven:
    """Signal layer gates open firing — warmup, fire, idempotency, mismatch."""

    def test_warmup_first_two_ticks_no_fire_then_third_tick_fires(
        self, mod: Any, engine: Any
    ) -> None:
        # [1.0, 1.05, 1.1] + direction='buy' → ticks 1-2 warmup
        # (no_signal); tick 3 has 3 strictly increasing prices →
        # signal='buy' matches → 1 open.
        components = _build_components_with_sequential_feed(mod, engine, [1.0, 1.05, 1.1])
        iterations = _run(mod, components, direction="buy", max_iterations=3)
        assert iterations == 3

        with engine.connect() as conn:
            ord_rows = conn.execute(text("SELECT order_id, status FROM orders")).fetchall()
            pos_rows = conn.execute(text("SELECT order_id, event_type FROM positions")).fetchall()
        assert len(ord_rows) == 1, "warmup ticks must NOT write; 3rd tick fires exactly once"
        assert ord_rows[0][1] == "FILLED"
        assert len(pos_rows) == 1
        assert pos_rows[0][1] == "open"

    def test_fourth_tick_blocked_by_already_open(self, mod: Any, engine: Any) -> None:
        # [1.0, 1.05, 1.1, 1.15] + 'buy' → ticks 1-2 warmup,
        # tick 3 fires, tick 4 already_open (signal would still be
        # 'buy' but already_open returns earlier in evaluate()).
        components = _build_components_with_sequential_feed(mod, engine, [1.0, 1.05, 1.1, 1.15])
        iterations = _run(mod, components, direction="buy", max_iterations=4)
        assert iterations == 4

        with engine.connect() as conn:
            ord_count = conn.execute(text("SELECT COUNT(*) FROM orders")).scalar()
            pos_count = conn.execute(
                text("SELECT COUNT(*) FROM positions WHERE event_type='open'")
            ).scalar()
        assert ord_count == 1
        assert pos_count == 1
        assert _INSTRUMENT in components.state_manager.open_instruments()

    def test_direction_mismatch_does_not_fire(self, mod: Any, engine: Any) -> None:
        # [1.0, 0.95, 0.9] + 'buy' → ticks 1-2 warmup; tick 3 has
        # 3 strictly decreasing prices → signal='sell' != 'buy' →
        # reason='no_signal', 0 opens.
        components = _build_components_with_sequential_feed(mod, engine, [1.0, 0.95, 0.9])
        iterations = _run(mod, components, direction="buy", max_iterations=3)
        assert iterations == 3

        with engine.connect() as conn:
            ord_count = conn.execute(text("SELECT COUNT(*) FROM orders")).scalar()
            pos_count = conn.execute(
                text("SELECT COUNT(*) FROM positions WHERE event_type='open'")
            ).scalar()
        assert ord_count == 0
        assert pos_count == 0
        assert _INSTRUMENT not in components.state_manager.open_instruments()


class TestPaperEntryLoopFivePointSignal:
    """Protocol seam validation: FivePointMomentumSignal wires through correctly.

    Verifies that the ``EntrySignal`` Protocol seam introduced in M10-2
    accepts a second concrete implementation.  Not testing strategy quality
    — testing that the injection path functions end-to-end with SQLite.
    """

    def test_five_point_signal_fires_on_tick_five(self, mod: Any, engine: Any) -> None:
        # [1.0, 1.01, 1.02, 1.03, 1.04] + 'buy' → ticks 1-4 warmup
        # (fewer than 5 quotes); tick 5 fires (5 strictly increasing prices).
        components = _build_components_with_sequential_feed(
            mod,
            engine,
            [1.0, 1.01, 1.02, 1.03, 1.04],
            signal=mod.FivePointMomentumSignal(),
        )
        iterations = _run(mod, components, direction="buy", max_iterations=5)
        assert iterations == 5

        with engine.connect() as conn:
            ord_rows = conn.execute(text("SELECT order_id, status FROM orders")).fetchall()
            pos_rows = conn.execute(text("SELECT order_id, event_type FROM positions")).fetchall()
        assert len(ord_rows) == 1, "warmup ticks must NOT write; 5th tick fires exactly once"
        assert ord_rows[0][1] == "FILLED"
        assert len(pos_rows) == 1
        assert pos_rows[0][1] == "open"


class TestPaperEntryLoopMultiSignal:
    """Priority picker seam: ordered signals, first-non-None wins, end-to-end.

    Both tests use real signal instances (not mocks) wired through
    SQLite, proving the picker seam at the integration boundary.
    """

    def test_second_signal_fires_when_first_is_in_warmup(self, mod: Any, engine: Any) -> None:
        # signals = [FivePoint (needs 5), Minimum (needs 3)]
        # prices  = [1.0, 1.05, 1.1] + 'buy', max=3
        # Tick 3: FivePoint has only 3 quotes → warmup → None.
        #         Picker falls through to MinimumEntrySignal → 'buy' → fire.
        # Asserts: second signal is consulted when first returns None.
        components = _build_components_with_sequential_feed(
            mod, engine, [1.0, 1.05, 1.1], signal=mod.MinimumEntrySignal()
        )
        iterations = _run(
            mod,
            components,
            direction="buy",
            max_iterations=3,
            signals=[mod.FivePointMomentumSignal(), mod.MinimumEntrySignal()],
        )
        assert iterations == 3
        with engine.connect() as conn:
            ord_count = conn.execute(text("SELECT COUNT(*) FROM orders")).scalar()
            pos_count = conn.execute(
                text("SELECT COUNT(*) FROM positions WHERE event_type='open'")
            ).scalar()
        assert ord_count == 1
        assert pos_count == 1

    def test_first_signal_mismatch_blocks_second(self, mod: Any, engine: Any) -> None:
        # signals = [Minimum, FivePoint], prices = [1.0, 0.95, 0.9], direction='buy'
        # Tick 3: MinimumEntrySignal → 'sell' (first non-None, direction mismatch).
        #         Picker stops; FivePoint is NOT consulted → no_signal.
        # Asserts: first-non-None is adopted even when it mismatches direction.
        components = _build_components_with_sequential_feed(
            mod, engine, [1.0, 0.95, 0.9], signal=mod.MinimumEntrySignal()
        )
        iterations = _run(
            mod,
            components,
            direction="buy",
            max_iterations=3,
            signals=[mod.MinimumEntrySignal(), mod.FivePointMomentumSignal()],
        )
        assert iterations == 3
        with engine.connect() as conn:
            ord_count = conn.execute(text("SELECT COUNT(*) FROM orders")).scalar()
            pos_count = conn.execute(
                text("SELECT COUNT(*) FROM positions WHERE event_type='open'")
            ).scalar()
        assert ord_count == 0
        assert pos_count == 0
