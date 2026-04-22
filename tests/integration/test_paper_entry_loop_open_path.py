"""Integration: ``scripts/run_paper_entry_loop`` round-trips against SQLite.

Exercises the full open-side cadence path end-to-end:

  policy.evaluate() → _open_one_position →
    create_order → update_status(SUBMITTED) → PaperBroker.place_order →
    update_status(FILLED) → StateManager.on_fill

with a stub QuoteFeed that always returns a fresh quote, and asserts
the user's Loop 3 idempotency contract:

  - max_iterations=1 → exactly 1 open is written to DB.
  - max_iterations=2 → the 2nd tick is a no-op (instrument already
    open ⇒ policy returns 'already_open' ⇒ no second write).

The paper components here are **production** code (``PaperBroker`` +
real ``StateManager`` + real ``OrdersRepository`` +
``MinimumEntryPolicy``).  Only the engine (in-memory SQLite) and the
quote feed (a deterministic stub) are test-side substitutions.

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
from unittest.mock import MagicMock

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


def _build_components_with_fresh_quote_stub(mod: Any, engine: Any) -> Any:
    """Compose the real paper open-side stack with a deterministic feed.

    Avoids ``build_components`` so we don't have to pass real OANDA
    credentials.  The feed returns a quote with ``ts == _FIXED_NOW``
    and the clock returns ``_FIXED_NOW`` — age always 0s, so the
    policy's stale gate never trips.
    """
    from fx_ai_trading.adapters.broker.paper import PaperBroker
    from fx_ai_trading.common.clock import FixedClock
    from fx_ai_trading.repositories.orders import OrdersRepository
    from fx_ai_trading.services.state_manager import StateManager

    clock = FixedClock(_FIXED_NOW)
    feed = MagicMock()
    feed.get_quote.return_value = MagicMock(
        price=1.0,
        ts=_FIXED_NOW,  # age = 0s against the same FixedClock
        source="test-stub",
    )

    return mod.EntryComponents(
        state_manager=StateManager(engine, account_id=_ACCOUNT_ID, clock=clock),
        orders=OrdersRepository(engine),
        broker=PaperBroker(account_type="demo", nominal_price=1.0),
        quote_feed=feed,
        clock=clock,
    )


# ---------------------------------------------------------------------------
# Idempotency pin (Loop 3 contract #3)
# ---------------------------------------------------------------------------


class TestPaperEntryLoopIdempotency:
    """One open per cadence — the 2nd tick is a no-op for the same instrument."""

    def test_max_iterations_1_writes_exactly_one_open(self, mod: Any, engine: Any) -> None:
        components = _build_components_with_fresh_quote_stub(mod, engine)
        policy = mod.MinimumEntryPolicy(
            instrument=_INSTRUMENT,
            state_manager=components.state_manager,
            quote_feed=components.quote_feed,
            clock=components.clock,
            stale_after_seconds=60.0,
        )

        log = logging.getLogger("test_paper_entry_loop_open_path")
        iterations = mod.run_loop(
            components=components,
            policy=policy,
            instrument=_INSTRUMENT,
            direction="buy",
            units=1000,
            account_id=_ACCOUNT_ID,
            account_type="demo",
            interval_seconds=0.0,
            max_iterations=1,
            log=log,
            should_stop=lambda: False,
            sleep_fn=lambda _s: None,
            monotonic_fn=lambda: 0.0,
        )

        assert iterations == 1

        # Exactly one orders row + one positions(open) row.
        with engine.connect() as conn:
            ord_rows = conn.execute(text("SELECT order_id, status FROM orders")).fetchall()
            pos_rows = conn.execute(text("SELECT order_id, event_type FROM positions")).fetchall()
        assert len(ord_rows) == 1
        assert ord_rows[0][1] == "FILLED"
        assert len(pos_rows) == 1
        assert pos_rows[0][1] == "open"

    def test_max_iterations_2_second_tick_is_noop(self, mod: Any, engine: Any) -> None:
        components = _build_components_with_fresh_quote_stub(mod, engine)
        policy = mod.MinimumEntryPolicy(
            instrument=_INSTRUMENT,
            state_manager=components.state_manager,
            quote_feed=components.quote_feed,
            clock=components.clock,
            stale_after_seconds=60.0,
        )

        log = logging.getLogger("test_paper_entry_loop_open_path")

        # FixedClock + fixed-ts stub keep the quote fresh forever, so
        # the 2nd tick's no-op is driven ONLY by the 'already_open'
        # branch (not by the quote going stale).  That isolation is
        # what the idempotency pin requires.
        iterations = mod.run_loop(
            components=components,
            policy=policy,
            instrument=_INSTRUMENT,
            direction="buy",
            units=1000,
            account_id=_ACCOUNT_ID,
            account_type="demo",
            interval_seconds=0.0,
            max_iterations=2,
            log=log,
            should_stop=lambda: False,
            sleep_fn=lambda _s: None,
            monotonic_fn=lambda: 0.0,
        )

        assert iterations == 2

        # Still exactly one orders row + one positions row — the 2nd
        # tick must NOT have written anything.
        with engine.connect() as conn:
            ord_count = conn.execute(text("SELECT COUNT(*) FROM orders")).scalar()
            pos_count = conn.execute(
                text("SELECT COUNT(*) FROM positions WHERE event_type='open'")
            ).scalar()
        assert ord_count == 1
        assert pos_count == 1

        # And the StateManager view confirms exactly one open instrument.
        assert _INSTRUMENT in components.state_manager.open_instruments()
        details = components.state_manager.open_position_details()
        assert len(details) == 1
        assert details[0].instrument == _INSTRUMENT
