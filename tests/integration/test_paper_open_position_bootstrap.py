"""Integration: ``scripts/paper_open_position`` round-trips against SQLite.

Exercises the full M9 paper-bootstrap write path end-to-end:

  create_order → update_status(SUBMITTED) → PaperBroker.place_order →
  update_status(FILLED) → StateManager.on_fill

and asserts the resulting DB state is consistent with what the
subsequent ``run_paper_loop`` exit cadence expects:

  - ``orders`` row present with ``status='FILLED'`` (the user's explicit
    acceptance criterion for Option B: FSM-compliant terminal state).
  - ``positions`` row with ``event_type='open'`` and
    ``avg_price == PaperBroker.nominal_price``.
  - ``secondary_sync_outbox`` mirrors the positions row.
  - ``StateManager.open_instruments()`` now reports the instrument.
  - ``StateManager.open_position_details()`` returns one
    ``OpenPositionInfo`` with the correctly derived side
    (``buy → long``, via the M-1a LEFT JOIN on orders.direction).

The paper components here are **production** code (``PaperBroker`` +
real ``StateManager`` + real ``OrdersRepository``).  The only test-side
substitution is the SQLAlchemy engine (in-memory SQLite instead of
Postgres) — the write path does not use Postgres-only features, so the
same code that runs against a live DB runs against this fixture.

In-memory SQLite is used so the test does not depend on ``DATABASE_URL``
or a live Postgres.  Foreign-key references (accounts, instruments,
trading_signals) are intentionally NOT declared in the test DDL — this
matches the convention already established in
``tests/integration/test_paper_loop_close_path.py`` and keeps the test
self-contained.

Out of scope (NOT asserted here — split into separate PRs if needed):

- Exit round-trip (open → close via run_exit_gate) — covered by
  ``tests/integration/test_paper_loop_close_path.py``.
- ``orders.submitted_at`` / ``orders.filled_at`` persistence — those
  are intentionally NULL under Option B (see module docstring of
  ``scripts/paper_open_position.py``).
- ``order_transactions`` / metrics / SafeStop — none relevant to the
  bootstrap write path.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import create_engine, text

# scripts/paper_open_position.py is not part of the installed package —
# load it via importlib so the test can call its production seam
# directly.  Mirrors the loader pattern in
# tests/integration/test_paper_loop_close_path.py.
_BOOTSTRAP_PATH = Path(__file__).resolve().parents[2] / "scripts" / "paper_open_position.py"


def _load_bootstrap_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "scripts.paper_open_position_for_bootstrap_test", _BOOTSTRAP_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_ACCOUNT_ID = "__test_account_bootstrap_open__"
_INSTRUMENT = "EUR_USD"


# --- DDL ---------------------------------------------------------------------
# Same schema shape as tests/integration/test_paper_loop_close_path.py —
# kept in sync deliberately so both tests exercise the same columns.
# (FKs omitted — SQLite does not enforce them by default and the
# bootstrap writes are self-contained.)

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


@pytest.fixture
def bootstrap_mod():
    return _load_bootstrap_module()


# ---------------------------------------------------------------------------
# The actual open-path test
# ---------------------------------------------------------------------------


class TestPaperOpenPositionBootstrap:
    """The bootstrap writes a consistent open-position DB state end-to-end."""

    def test_happy_path_round_trip(self, bootstrap_mod, engine) -> None:
        result = bootstrap_mod.bootstrap_open_position(
            engine=engine,
            instrument=_INSTRUMENT,
            direction="buy",
            units=1000,
            account_id=_ACCOUNT_ID,
            nominal_price=1.0,
        )

        # --- BootstrapResult fields ------------------------------------
        assert result.side == "long"
        assert result.fill_price == 1.0
        assert result.order_id  # ULID, non-empty
        assert result.position_snapshot_id

        # --- orders row: status reached terminal FILLED ----------------
        with engine.connect() as conn:
            ord_rows = (
                conn.execute(
                    text(
                        "SELECT order_id, status, direction, units, account_type"
                        " FROM orders WHERE order_id = :oid"
                    ),
                    {"oid": result.order_id},
                )
                .mappings()
                .all()
            )
        assert len(ord_rows) == 1
        o = ord_rows[0]
        assert o["status"] == "FILLED"
        assert o["direction"] == "buy"
        assert int(o["units"]) == 1000
        assert o["account_type"] == "demo"

        # --- positions row: event_type='open', avg_price = fill_price --
        with engine.connect() as conn:
            pos_rows = (
                conn.execute(
                    text(
                        "SELECT position_snapshot_id, event_type, units, avg_price"
                        " FROM positions WHERE order_id = :oid"
                    ),
                    {"oid": result.order_id},
                )
                .mappings()
                .all()
            )
        assert len(pos_rows) == 1
        p = pos_rows[0]
        assert p["position_snapshot_id"] == result.position_snapshot_id
        assert p["event_type"] == "open"
        assert int(p["units"]) == 1000
        assert float(p["avg_price"]) == pytest.approx(1.0)

        # --- secondary_sync_outbox mirrors the positions write --------
        with engine.connect() as conn:
            mirrored_tables = {
                row[0]
                for row in conn.execute(
                    text("SELECT DISTINCT table_name FROM secondary_sync_outbox")
                ).fetchall()
            }
        assert "positions" in mirrored_tables

        # --- StateManager reports the instrument open -----------------
        from fx_ai_trading.services.state_manager import StateManager

        sm = StateManager(engine, account_id=_ACCOUNT_ID)
        assert _INSTRUMENT in sm.open_instruments()

        details = sm.open_position_details()
        assert len(details) == 1
        info = details[0]
        assert info.instrument == _INSTRUMENT
        assert info.order_id == result.order_id
        assert info.units == 1000
        assert info.avg_price == pytest.approx(1.0)
        # M-1a: side derived via LEFT JOIN orders.direction
        # (buy → long per _DIRECTION_TO_SIDE).
        assert info.side == "long"

    def test_sell_direction_maps_to_short_side(self, bootstrap_mod, engine) -> None:
        result = bootstrap_mod.bootstrap_open_position(
            engine=engine,
            instrument=_INSTRUMENT,
            direction="sell",
            units=500,
            account_id=_ACCOUNT_ID,
            nominal_price=1.1,
        )
        assert result.side == "short"

        from fx_ai_trading.services.state_manager import StateManager

        sm = StateManager(engine, account_id=_ACCOUNT_ID)
        details = sm.open_position_details()
        assert len(details) == 1
        assert details[0].side == "short"
        assert details[0].avg_price == pytest.approx(1.1)

    def test_duplicate_open_is_rejected_and_leaves_state_untouched(
        self, bootstrap_mod, engine
    ) -> None:
        first = bootstrap_mod.bootstrap_open_position(
            engine=engine,
            instrument=_INSTRUMENT,
            direction="buy",
            units=1000,
            account_id=_ACCOUNT_ID,
        )

        # Second invocation for the same (account, instrument) must
        # raise without writing anything.
        with pytest.raises(bootstrap_mod.DuplicateOpenInstrumentError):
            bootstrap_mod.bootstrap_open_position(
                engine=engine,
                instrument=_INSTRUMENT,
                direction="buy",
                units=1000,
                account_id=_ACCOUNT_ID,
            )

        # Still exactly one orders row + one positions row.
        with engine.connect() as conn:
            ord_count = conn.execute(text("SELECT COUNT(*) FROM orders")).scalar()
            pos_count = conn.execute(text("SELECT COUNT(*) FROM positions")).scalar()
        assert ord_count == 1
        assert pos_count == 1

        # And the surviving row is the first one.
        with engine.connect() as conn:
            (only_oid,) = conn.execute(text("SELECT order_id FROM orders")).fetchone()
        assert only_oid == first.order_id
