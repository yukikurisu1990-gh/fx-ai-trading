"""Integration: ``run_paper_loop`` production paper stack drives the close path.

Exercises the M9 paper-stack-bootstrap completion criterion end-to-end:

  open position → supervisor.run_exit_gate_tick() → broker close →
  StateManager.on_close → close_events row + positions(close) row +
  pnl_realized populated.

The paper stack here is the **same** stack assembled by
``scripts/run_paper_loop.build_supervisor_with_paper_stack`` (real
``PaperBroker`` + real ``StateManager`` + real ``ExitPolicyService`` +
real ``OandaQuoteFeed``).  The only test-side substitution is the
``OandaAPIClient`` (replaced with a tiny double so no HTTP call is
made).  Everything else — including the QuoteFeed adapter, the staleness
gate, the M-1a side-derivation JOIN, and the M-2 PnL formula — is the
production code path.

In-memory SQLite is used so the test does not depend on ``DATABASE_URL``
or a live Postgres.  StateManager / on_close work transparently against
both engines; the exit-gate write path does not use Postgres-only
features.

The exit trigger is ``max_holding_time`` rather than TP because
``build_supervisor_with_paper_stack`` does not pass tp/sl through (per
its current contract).  Setting ``max_holding_seconds=1`` and a clock
five seconds after the open event causes the policy to fire on the
seeded position.

Out of scope here (split into separate PRs if needed):

- Re-attach the supervisor with tp/sl to exercise the TP rule (the M9
  exit_flow integration test already covers that path against real
  Postgres; this test mirrors it against the *paper-loop* wiring).
- broker_rejected / SafeStop / multi-position scenarios — those are
  unit-level and live in ``tests/unit/test_exit_gate_runner.py``.
"""

from __future__ import annotations

import importlib.util
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import create_engine, text

from fx_ai_trading.common.clock import FixedClock
from fx_ai_trading.common.ulid import generate_ulid
from fx_ai_trading.config.common_keys_context import CommonKeysContext
from fx_ai_trading.repositories.orders import OrdersRepository

# scripts/run_paper_loop.py is not part of the installed package — load
# it via importlib so the test can call its production seam directly.
# Mirrors the pattern used in tests/unit/test_run_paper_loop.py.
_RUN_PAPER_LOOP_PATH = Path(__file__).resolve().parents[2] / "scripts" / "run_paper_loop.py"


def _load_runner_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "scripts.run_paper_loop_for_close_path_test", _RUN_PAPER_LOOP_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_OPEN_TIME = datetime(2026, 4, 22, 12, 0, 0, tzinfo=UTC)
_NOW = _OPEN_TIME + timedelta(seconds=5)
_QUOTE_TIME = _NOW  # fresh quote — staleness gate must not trip


_BROKER_ID = "__test_broker_paper_close__"
_ACCOUNT_ID = "__test_account_paper_close__"
_INSTRUMENT = "EUR_USD"

_CTX = CommonKeysContext(
    run_id="paper-loop-close-path-run",
    environment="test",
    code_version="0.0.0",
    config_version="paper-loop-close-path-cfg",
)


# --- DDL ---------------------------------------------------------------------
# Superset of the columns ``StateManager.on_close`` and
# ``open_position_details`` read.  Postgres-specific column types are
# softened to TEXT/NUMERIC so SQLite accepts the schema unchanged.
# Mirrors the DDL used in tests/integration/test_execution_gate_end_to_end.py
# and tests/unit/test_exit_gate_runner.py — kept verbatim so the schema
# remains in lock-step with those long-standing fixtures.

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

_DDL_CLOSE_EVENTS = """
CREATE TABLE close_events (
    close_event_id       TEXT PRIMARY KEY,
    order_id             TEXT NOT NULL,
    position_snapshot_id TEXT,
    reasons              TEXT NOT NULL,
    primary_reason_code  TEXT NOT NULL,
    closed_at            TEXT NOT NULL,
    pnl_realized         NUMERIC(18,8),
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


# --- Test doubles ------------------------------------------------------------


class _StubOandaAPIClient:
    """Minimal ``OandaAPIClient`` substitute for ``OandaQuoteFeed``.

    Only ``get_pricing(account_id, instruments)`` is implemented — that
    is the sole method ``OandaQuoteFeed.get_quote`` calls.  The returned
    shape mirrors the OANDA REST contract: a list of dicts with
    ``time`` / ``bids`` / ``asks`` keys.  Mid-price = 1.11; ts = the
    integration test's fixed ``_QUOTE_TIME`` so the staleness gate stays
    fresh against the FixedClock.
    """

    def __init__(self, *, mid_price: float, ts: datetime) -> None:
        self._mid = mid_price
        self._ts = ts
        # Half-spread of 1 pip-equivalent so the mid round-trips exactly.
        self._half_spread = 0.0001
        self.calls: list[tuple[str, list[str]]] = []

    def get_pricing(self, account_id: str, instruments: list[str]) -> list[dict[str, Any]]:
        self.calls.append((account_id, list(instruments)))
        bid = self._mid - self._half_spread
        ask = self._mid + self._half_spread
        return [
            {
                "time": self._ts.isoformat().replace("+00:00", "Z"),
                "bids": [{"price": f"{bid:.5f}"}],
                "asks": [{"price": f"{ask:.5f}"}],
            }
        ]


# --- Fixtures ----------------------------------------------------------------


@pytest.fixture
def engine():
    eng = create_engine("sqlite:///:memory:")
    with eng.begin() as conn:
        conn.execute(text(_DDL_ORDERS))
        conn.execute(text(_DDL_POSITIONS))
        conn.execute(text(_DDL_CLOSE_EVENTS))
        conn.execute(text(_DDL_OUTBOX))
    yield eng
    eng.dispose()


def _seed_open_position(
    engine,
    *,
    order_id: str,
    units: int = 1000,
    avg_price: float = 0.99,
    direction: str = "buy",
) -> str:
    """Create the orders row + positions(open) row the test will close.

    Returns the position_snapshot_id of the seeded open row so the test
    can assert against it directly.  Mirrors the seeding helper in
    tests/integration/test_exit_flow.py — kept self-contained here so
    the test reads top-to-bottom without cross-file indirection.
    """
    OrdersRepository(engine).create_order(
        order_id=order_id,
        account_id=_ACCOUNT_ID,
        instrument=_INSTRUMENT,
        account_type="demo",
        order_type="market",
        direction=direction,
        units=str(units),
        context=_CTX,
    )

    psid = generate_ulid()
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO positions (
                    position_snapshot_id, order_id, account_id, instrument,
                    event_type, units, avg_price, unrealized_pl, realized_pl,
                    event_time_utc, correlation_id
                ) VALUES (
                    :psid, :oid, :aid, :inst,
                    'open', :units, :avg, NULL, NULL,
                    :ts, NULL
                )
                """
            ),
            {
                "psid": psid,
                "oid": order_id,
                "aid": _ACCOUNT_ID,
                "inst": _INSTRUMENT,
                "units": units,
                "avg": avg_price,
                "ts": _OPEN_TIME.isoformat(),
            },
        )
    return psid


# --- The actual close-path test ---------------------------------------------


class TestPaperLoopClosePath:
    """``run_paper_loop`` production stack exercises the full close path."""

    def test_open_position_flows_through_to_close_event(self, engine) -> None:
        runner = _load_runner_module()

        # Build the **production** paper stack via the runner's seam.
        # max_holding_seconds=1 makes the seeded position (open 5s ago)
        # immediately past the holding ceiling, so the policy fires and
        # the close path is exercised without needing tp/sl support in
        # the bootstrap function.
        oanda = runner.OandaConfig(
            access_token="dummy-token",
            account_id="dummy-account",
            environment="practice",
        )
        api_client = _StubOandaAPIClient(mid_price=1.11, ts=_QUOTE_TIME)
        clock = FixedClock(_NOW)

        supervisor, feed = runner.build_supervisor_with_paper_stack(
            oanda=oanda,
            instrument=_INSTRUMENT,
            engine=engine,
            account_id=_ACCOUNT_ID,
            clock=clock,
            max_holding_seconds=1,
            api_client=api_client,
        )

        # Seam smoke: feed is the production OandaQuoteFeed wired to our
        # stub api_client — calling it goes through the same code path
        # that ``run_exit_gate`` will trigger.
        from fx_ai_trading.adapters.price_feed.oanda_quote_feed import OandaQuoteFeed

        assert isinstance(feed, OandaQuoteFeed)

        order_id = "__test_paper_close_ord__"
        psid = _seed_open_position(engine, order_id=order_id)

        # --- Drive one tick (the run_paper_loop cadence step) -----------
        results = supervisor.run_exit_gate_tick()

        # --- Outcome ----------------------------------------------------
        assert len(results) == 1
        result = results[0]
        assert result.outcome == "closed"
        assert result.primary_reason == "max_holding_time"
        assert result.order_id == order_id
        assert result.instrument == _INSTRUMENT

        # --- close_events row ------------------------------------------
        with engine.connect() as conn:
            ce_rows = (
                conn.execute(
                    text("SELECT * FROM close_events WHERE order_id = :oid"),
                    {"oid": order_id},
                )
                .mappings()
                .all()
            )
        assert len(ce_rows) == 1
        ce = ce_rows[0]
        assert ce["primary_reason_code"] == "max_holding_time"
        # M-2 contract: gross PnL = (fill - avg) * units * sign(side).
        # Long position seeded at avg=0.99, units=1000; PaperBroker reads
        # the close fill from the same QuoteFeed the policy uses.
        #
        # Phase 9.10: OandaQuoteFeed now populates Quote.bid/ask, and
        # PaperBroker fills the close (short) leg at the bid side. With
        # mid=1.11 and half_spread=0.0001, bid=1.1099 so the spread-aware
        # close PnL is (1.1099 - 0.99) * 1000 = +119.9.
        assert ce["pnl_realized"] is not None
        assert float(ce["pnl_realized"]) == pytest.approx(119.9)

        # --- positions(close) row appended (append-only) ---------------
        with engine.connect() as conn:
            pos_rows = (
                conn.execute(
                    text(
                        "SELECT event_type, units FROM positions"
                        " WHERE order_id = :oid ORDER BY event_time_utc"
                    ),
                    {"oid": order_id},
                )
                .mappings()
                .all()
            )
        event_types = [r["event_type"] for r in pos_rows]
        assert "open" in event_types
        assert "close" in event_types

        # --- Open-positions view now empty (close visible to JOIN) -----
        # The same StateManager that on_close wrote against must report
        # zero open positions — proves the close row is observable to
        # the next tick.
        sm = supervisor._exit_gate.state_manager  # type: ignore[union-attr]
        assert sm.open_position_details() == []

        # --- Outbox mirror: positions + close_events both enqueued -----
        with engine.connect() as conn:
            mirrored_tables = {
                row[0]
                for row in conn.execute(
                    text("SELECT DISTINCT table_name FROM secondary_sync_outbox")
                ).fetchall()
            }
        assert "close_events" in mirrored_tables
        assert "positions" in mirrored_tables

        # --- The OandaQuoteFeed was called twice on this tick: once by
        # the exit-policy / staleness gate and once by PaperBroker for
        # the close-leg fill price. Both go through the same api_client.
        assert len(api_client.calls) == 2
        assert api_client.calls[0] == ("dummy-account", [_INSTRUMENT])
        assert api_client.calls[1] == ("dummy-account", [_INSTRUMENT])

        # psid is recorded on the close_events row when StateManager
        # successfully derived it from the open row — soft check, only
        # asserted when present so a future schema tweak that drops the
        # column does not break this test for unrelated reasons.
        if ce["position_snapshot_id"] is not None:
            assert ce["position_snapshot_id"] == psid
