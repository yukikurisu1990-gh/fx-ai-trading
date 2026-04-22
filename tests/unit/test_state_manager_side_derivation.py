"""Unit tests: ``StateManager.open_position_details`` side derivation (M-1a).

Pins the M-1a (Design A) contract added on top of Cycle 6.7c:

  ``open_position_details`` LEFT-JOINs ``positions`` against ``orders``
  and derives ``OpenPositionInfo.side`` from ``orders.direction`` via
  the canonical mapping ``_DIRECTION_TO_SIDE`` (``buy``→``long``,
  ``sell``→``short``).

Three defensive paths are pinned here:

  1. ``positions.order_id IS NULL``
       Schema permits NULL (``order_id`` is nullable per the model);
       the row is skipped with an error log.  No KeyError, no entry in
       the result.
  2. orphan ``positions`` row whose ``order_id`` has no matching
     ``orders`` row
       The LEFT JOIN yields ``direction=NULL``; the row is skipped
       with an error log.  Same defensive shape as (1).
  3. ``orders.direction`` outside the canonical ``{'buy', 'sell'}`` set
       Fail-fast: ``KeyError`` propagates.  A corrupt direction value
       is a contract violation that must surface, not be silently
       coerced.

The DDL fixture intentionally mirrors the ones in
``test_state_manager_write.py`` and ``test_state_manager_ordering_repro.py``
(plus the M-1a-specific ``orders`` table) so this file is self-contained.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine, text

from fx_ai_trading.common.clock import FixedClock
from fx_ai_trading.services.state_manager import StateManager

_NOW = datetime(2026, 4, 22, 12, 0, 0, tzinfo=UTC)
_OPEN_TIME = datetime(2026, 4, 22, 11, 0, 0, tzinfo=UTC)
_SM_LOGGER_NAME = "fx_ai_trading.services.state_manager"


# ---------------------------------------------------------------------------
# Module-logger spy
# ---------------------------------------------------------------------------
#
# ``caplog`` alone proved fragile here: when the full test suite runs,
# something earlier in the session leaves the ``fx_ai_trading.services``
# logger tree in a state where caplog's root handler does not receive the
# state_manager records (the records vanish — caplog reports an empty list
# even though the production code clearly executed the ``_log.error(...)``
# branch).  Rather than chase the upstream test that mutates global logging
# state, we attach a dedicated handler directly to the state_manager
# logger for the duration of the test so the assertion is independent of
# any propagation/disabled flags.


class _ListHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__(level=logging.DEBUG)
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


@pytest.fixture
def sm_log_records():
    """Capture every record emitted on ``_SM_LOGGER_NAME`` for the test
    duration, regardless of caplog plumbing state."""
    logger = logging.getLogger(_SM_LOGGER_NAME)
    handler = _ListHandler()
    prev_level = logger.level
    prev_disabled = logger.disabled
    logger.disabled = False
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    try:
        yield handler.records
    finally:
        logger.removeHandler(handler)
        logger.setLevel(prev_level)
        logger.disabled = prev_disabled


# ---------------------------------------------------------------------------
# DDL — kept in-file so the test module does not depend on neighbouring suites
# ---------------------------------------------------------------------------

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

_DDL_ORDER_TRANSACTIONS = """
CREATE TABLE order_transactions (
    broker_txn_id        TEXT NOT NULL,
    account_id           TEXT NOT NULL,
    order_id             TEXT,
    transaction_type     TEXT NOT NULL,
    transaction_time_utc TEXT NOT NULL,
    payload              TEXT,
    received_at_utc      TEXT NOT NULL,
    PRIMARY KEY (broker_txn_id, account_id)
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

# Minimal orders DDL — only the columns ``open_position_details`` reads
# via its M-1a LEFT JOIN.  The production schema has many more columns
# (``client_order_id`` / ``trading_signal_id`` / ``account_type`` / ...);
# tests do not exercise those here.
_DDL_ORDERS = """
CREATE TABLE orders (
    order_id  TEXT PRIMARY KEY,
    direction TEXT NOT NULL
)
"""


@pytest.fixture
def engine():
    eng = create_engine("sqlite:///:memory:")
    with eng.begin() as conn:
        conn.execute(text(_DDL_POSITIONS))
        conn.execute(text(_DDL_CLOSE_EVENTS))
        conn.execute(text(_DDL_ORDER_TRANSACTIONS))
        conn.execute(text(_DDL_OUTBOX))
        conn.execute(text(_DDL_ORDERS))
    yield eng
    eng.dispose()


# ---------------------------------------------------------------------------
# Seed helpers — bypass on_fill so we can test the JOIN directly with arbitrary
# (orders, positions) shapes including the bad ones (NULL / orphan / unknown).
# ---------------------------------------------------------------------------


def _seed_order(engine, *, order_id: str, direction: str) -> None:
    with engine.begin() as conn:
        conn.execute(
            text("INSERT INTO orders (order_id, direction) VALUES (:oid, :dir)"),
            {"oid": order_id, "dir": direction},
        )


def _seed_position(
    engine,
    *,
    psid: str,
    order_id: str | None,
    instrument: str,
    units: int = 1000,
    avg_price: float = 1.10,
    account_id: str = "acc-1",
    open_time: datetime = _OPEN_TIME,
) -> None:
    """Insert one ``positions`` row with ``event_type='open'``.

    ``order_id`` is intentionally typed ``str | None`` so we can probe the
    NULL-order_id defensive branch without going through ``on_fill`` (which
    always supplies a value).
    """
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
                "aid": account_id,
                "inst": instrument,
                "units": units,
                "avg": avg_price,
                "ts": open_time.isoformat(),
            },
        )


def _make_sm(engine, account_id: str = "acc-1") -> StateManager:
    return StateManager(engine, account_id=account_id, clock=FixedClock(_NOW))


# ---------------------------------------------------------------------------
# Happy path: direction → side mapping
# ---------------------------------------------------------------------------


class TestDirectionToSideMapping:
    def test_buy_direction_maps_to_long_side(self, engine) -> None:
        _seed_order(engine, order_id="o-buy", direction="buy")
        _seed_position(engine, psid="p1", order_id="o-buy", instrument="EURUSD")

        details = _make_sm(engine).open_position_details()

        assert len(details) == 1
        assert details[0].order_id == "o-buy"
        assert details[0].side == "long"

    def test_sell_direction_maps_to_short_side(self, engine) -> None:
        _seed_order(engine, order_id="o-sell", direction="sell")
        _seed_position(engine, psid="p1", order_id="o-sell", instrument="USDJPY")

        details = _make_sm(engine).open_position_details()

        assert len(details) == 1
        assert details[0].order_id == "o-sell"
        assert details[0].side == "short"

    def test_mixed_buy_and_sell_returns_correct_sides(self, engine) -> None:
        """Two positions with opposite directions → both rows present, each
        with the side derived from its own ``orders.direction`` row."""
        _seed_order(engine, order_id="o-buy", direction="buy")
        _seed_order(engine, order_id="o-sell", direction="sell")
        _seed_position(engine, psid="p1", order_id="o-buy", instrument="EURUSD")
        _seed_position(engine, psid="p2", order_id="o-sell", instrument="USDJPY")

        details = _make_sm(engine).open_position_details()
        sides_by_instrument = {d.instrument: d.side for d in details}

        assert sides_by_instrument == {"EURUSD": "long", "USDJPY": "short"}


# ---------------------------------------------------------------------------
# Defensive path 1: NULL order_id → skip + error log
# ---------------------------------------------------------------------------


class TestNullOrderIdSkipped:
    def test_null_order_id_row_is_skipped(self, engine, sm_log_records) -> None:
        _seed_position(engine, psid="p1", order_id=None, instrument="EURUSD")

        details = _make_sm(engine).open_position_details()

        assert details == []
        # Skip MUST be observable via an ERROR log so an operator sees it.
        assert any(
            "NULL order_id" in rec.getMessage() and rec.levelno == logging.ERROR
            for rec in sm_log_records
        ), f"expected NULL order_id error log, got: {[r.getMessage() for r in sm_log_records]}"

    def test_null_order_id_row_does_not_block_other_rows(self, engine) -> None:
        """One NULL-order_id row is dropped; a sibling well-formed row is
        still returned in the same call."""
        _seed_order(engine, order_id="o-good", direction="buy")
        _seed_position(engine, psid="p1", order_id=None, instrument="EURUSD")
        _seed_position(engine, psid="p2", order_id="o-good", instrument="USDJPY")

        details = _make_sm(engine).open_position_details()

        assert len(details) == 1
        assert details[0].order_id == "o-good"
        assert details[0].side == "long"


# ---------------------------------------------------------------------------
# Defensive path 2: orphan position (no matching orders row) → skip + error log
# ---------------------------------------------------------------------------


class TestOrphanPositionSkipped:
    def test_orphan_position_is_skipped(self, engine, sm_log_records) -> None:
        # NOTE: no _seed_order call → LEFT JOIN yields direction=NULL.
        _seed_position(engine, psid="p1", order_id="o-orphan", instrument="EURUSD")

        details = _make_sm(engine).open_position_details()

        assert details == []
        assert any(
            "orphan position" in rec.getMessage() and rec.levelno == logging.ERROR
            for rec in sm_log_records
        ), f"expected orphan position error log, got: {[r.getMessage() for r in sm_log_records]}"

    def test_orphan_does_not_block_other_rows(self, engine) -> None:
        """One orphan row is dropped; a sibling well-formed row is still
        returned in the same call."""
        _seed_order(engine, order_id="o-good", direction="sell")
        _seed_position(engine, psid="p1", order_id="o-orphan", instrument="EURUSD")
        _seed_position(engine, psid="p2", order_id="o-good", instrument="USDJPY")

        details = _make_sm(engine).open_position_details()

        assert len(details) == 1
        assert details[0].order_id == "o-good"
        assert details[0].side == "short"


# ---------------------------------------------------------------------------
# Defensive path 3: unknown direction → KeyError fail-fast
# ---------------------------------------------------------------------------


class TestUnknownDirectionFailsFast:
    def test_unknown_direction_raises_key_error(self, engine) -> None:
        """Direction outside the canonical ``{'buy', 'sell'}`` set is a
        contract violation — the M-1a derivation MUST raise rather than
        return a coerced or default ``side``.
        """
        _seed_order(engine, order_id="o-bad", direction="hold")  # unknown value
        _seed_position(engine, psid="p1", order_id="o-bad", instrument="EURUSD")

        with pytest.raises(KeyError):
            _make_sm(engine).open_position_details()

    def test_empty_string_direction_raises_key_error(self, engine) -> None:
        """An empty-string direction is also a contract violation."""
        _seed_order(engine, order_id="o-empty", direction="")
        _seed_position(engine, psid="p1", order_id="o-empty", instrument="USDJPY")

        with pytest.raises(KeyError):
            _make_sm(engine).open_position_details()
