"""Unit tests: StateManager write path (Cycle 6.7b).

Covers:
  on_fill():
    - First fill for instrument → positions row with event_type='open'.
    - Second fill for same instrument → event_type='add' (pyramiding).
    - Returns a non-empty position_snapshot_id.
    - Enqueues one positions row to secondary_sync_outbox.
    - Cross-account: fill on acc-2 does not affect acc-1 open_instruments.

  on_close():
    - Writes positions row with event_type='close', units=0.
    - Writes close_events row linked via position_snapshot_id.
    - Returns (psid, ceid) — two distinct ULIDs.
    - Enqueues both rows (positions + close_events) to outbox.
    - After on_close, instrument is no longer visible in open_instruments.

  on_risk_verdict():
    - Writes risk_events row with verdict and constraint_violated.
    - Returns non-empty risk_event_id.
    - Accepted verdicts: constraint_violated=None persisted as NULL.
    - Rejected verdicts: constraint_violated stores dotted code (L6).
    - Enqueues risk_events row to outbox.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine, text

from fx_ai_trading.common.clock import FixedClock
from fx_ai_trading.services.state_manager import StateManager

_NOW = datetime(2026, 4, 20, 12, 0, 0, tzinfo=UTC)

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

_DDL_RISK_EVENTS = """
CREATE TABLE risk_events (
    risk_event_id       TEXT PRIMARY KEY,
    cycle_id            TEXT,
    instrument          TEXT,
    strategy_id         TEXT,
    verdict             TEXT NOT NULL,
    constraint_violated TEXT,
    detail              TEXT,
    event_time_utc      TEXT NOT NULL
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


@pytest.fixture
def engine():
    eng = create_engine("sqlite:///:memory:")
    with eng.begin() as conn:
        conn.execute(text(_DDL_POSITIONS))
        conn.execute(text(_DDL_CLOSE_EVENTS))
        conn.execute(text(_DDL_RISK_EVENTS))
        conn.execute(text(_DDL_ORDER_TRANSACTIONS))
        conn.execute(text(_DDL_OUTBOX))
    yield eng
    eng.dispose()


def _make_sm(engine, account_id: str = "acc-1") -> StateManager:
    return StateManager(engine, account_id=account_id, clock=FixedClock(_NOW))


def _positions_rows(engine, *, account_id: str = "acc-1") -> list:
    with engine.connect() as conn:
        return conn.execute(
            text("SELECT * FROM positions WHERE account_id = :aid ORDER BY event_time_utc"),
            {"aid": account_id},
        ).fetchall()


def _close_events_rows(engine) -> list:
    with engine.connect() as conn:
        return conn.execute(text("SELECT * FROM close_events")).fetchall()


def _risk_events_rows(engine, *, account_id: str | None = None) -> list:
    with engine.connect() as conn:
        return conn.execute(text("SELECT * FROM risk_events")).fetchall()


def _outbox_rows(engine, *, table_name: str | None = None) -> list:
    with engine.connect() as conn:
        if table_name:
            rows = conn.execute(
                text("SELECT * FROM secondary_sync_outbox WHERE table_name = :tn"),
                {"tn": table_name},
            ).fetchall()
        else:
            rows = conn.execute(text("SELECT * FROM secondary_sync_outbox")).fetchall()
    return rows


# --- on_fill ------------------------------------------------------------------


class TestOnFill:
    def test_first_fill_writes_open_event(self, engine) -> None:
        sm = _make_sm(engine)
        sm.on_fill(order_id="o1", instrument="EURUSD", units=1000, avg_price=1.10)
        rows = _positions_rows(engine)
        assert len(rows) == 1
        assert rows[0].event_type == "open"
        assert rows[0].instrument == "EURUSD"
        assert rows[0].order_id == "o1"

    def test_second_fill_same_instrument_writes_add_event(self, engine) -> None:
        sm = _make_sm(engine)
        sm.on_fill(order_id="o1", instrument="EURUSD", units=1000, avg_price=1.10)
        sm.on_fill(order_id="o2", instrument="EURUSD", units=500, avg_price=1.11)
        rows = _positions_rows(engine)
        assert len(rows) == 2
        event_types = {r.event_type for r in rows}
        assert event_types == {"open", "add"}

    def test_different_instruments_both_get_open(self, engine) -> None:
        sm = _make_sm(engine)
        sm.on_fill(order_id="o1", instrument="EURUSD", units=1000, avg_price=1.10)
        sm.on_fill(order_id="o2", instrument="USDJPY", units=1000, avg_price=150.0)
        rows = _positions_rows(engine)
        assert len(rows) == 2
        assert all(r.event_type == "open" for r in rows)

    def test_returns_non_empty_psid(self, engine) -> None:
        sm = _make_sm(engine)
        psid = sm.on_fill(order_id="o1", instrument="EURUSD", units=1000, avg_price=1.10)
        assert isinstance(psid, str) and len(psid) > 0

    def test_units_and_avg_price_persisted(self, engine) -> None:
        sm = _make_sm(engine)
        sm.on_fill(order_id="o1", instrument="EURUSD", units=2000, avg_price=1.2345)
        rows = _positions_rows(engine)
        assert float(rows[0].units) == 2000.0
        assert abs(float(rows[0].avg_price) - 1.2345) < 1e-6

    def test_enqueues_one_positions_outbox_row(self, engine) -> None:
        sm = _make_sm(engine)
        sm.on_fill(order_id="o1", instrument="EURUSD", units=1000, avg_price=1.10)
        rows = _outbox_rows(engine, table_name="positions")
        assert len(rows) == 1

    def test_outbox_payload_contains_event_type(self, engine) -> None:
        sm = _make_sm(engine)
        sm.on_fill(order_id="o1", instrument="EURUSD", units=1000, avg_price=1.10)
        row = _outbox_rows(engine, table_name="positions")[0]
        payload = json.loads(row.payload_json)
        assert payload["event_type"] == "open"
        assert payload["instrument"] == "EURUSD"

    def test_cross_account_fill_invisible_to_other_account(self, engine) -> None:
        sm1 = _make_sm(engine, account_id="acc-1")
        sm2 = _make_sm(engine, account_id="acc-2")
        sm2.on_fill(order_id="o1", instrument="EURUSD", units=1000, avg_price=1.10)
        assert sm1.open_instruments() == frozenset()
        assert sm2.open_instruments() == frozenset({"EURUSD"})

    def test_fill_after_close_writes_open_not_add(self, engine) -> None:
        sm = _make_sm(engine)
        sm.on_fill(order_id="o1", instrument="EURUSD", units=1000, avg_price=1.10)
        sm.on_close(
            order_id="o1",
            instrument="EURUSD",
            reasons=[{"priority": 1, "reason_code": "tp", "detail": ""}],
            primary_reason_code="tp",
        )
        # Re-open after close → should be 'open', not 'add'
        sm.on_fill(order_id="o2", instrument="EURUSD", units=1000, avg_price=1.12)
        rows = _positions_rows(engine)
        last_row = sorted(rows, key=lambda r: r.event_time_utc)[-1]
        assert last_row.event_type == "open"
        assert last_row.order_id == "o2"


# --- on_close -----------------------------------------------------------------


class TestOnClose:
    def test_writes_positions_close_row(self, engine) -> None:
        sm = _make_sm(engine)
        sm.on_fill(order_id="o1", instrument="EURUSD", units=1000, avg_price=1.10)
        sm.on_close(
            order_id="o1",
            instrument="EURUSD",
            reasons=[{"priority": 1, "reason_code": "sl", "detail": "stop hit"}],
            primary_reason_code="sl",
            pnl_realized=-50.0,
        )
        rows = _positions_rows(engine)
        close_row = next(r for r in rows if r.event_type == "close")
        assert close_row.instrument == "EURUSD"
        assert float(close_row.units) == 0.0
        assert float(close_row.realized_pl) == -50.0

    def test_writes_close_events_row(self, engine) -> None:
        sm = _make_sm(engine)
        sm.on_fill(order_id="o1", instrument="EURUSD", units=1000, avg_price=1.10)
        sm.on_close(
            order_id="o1",
            instrument="EURUSD",
            reasons=[{"priority": 1, "reason_code": "tp", "detail": ""}],
            primary_reason_code="tp",
            pnl_realized=120.0,
        )
        rows = _close_events_rows(engine)
        assert len(rows) == 1
        assert rows[0].primary_reason_code == "tp"
        assert rows[0].pnl_realized == 120.0

    def test_returns_two_distinct_ids(self, engine) -> None:
        sm = _make_sm(engine)
        sm.on_fill(order_id="o1", instrument="EURUSD", units=1000, avg_price=1.10)
        psid, ceid = sm.on_close(
            order_id="o1",
            instrument="EURUSD",
            reasons=[{"priority": 1, "reason_code": "tp", "detail": ""}],
            primary_reason_code="tp",
        )
        assert isinstance(psid, str) and len(psid) > 0
        assert isinstance(ceid, str) and len(ceid) > 0
        assert psid != ceid

    def test_instrument_hidden_after_close(self, engine) -> None:
        sm = _make_sm(engine)
        sm.on_fill(order_id="o1", instrument="EURUSD", units=1000, avg_price=1.10)
        assert sm.open_instruments() == frozenset({"EURUSD"})
        sm.on_close(
            order_id="o1",
            instrument="EURUSD",
            reasons=[{"priority": 1, "reason_code": "tp", "detail": ""}],
            primary_reason_code="tp",
        )
        assert sm.open_instruments() == frozenset()

    def test_enqueues_both_outbox_rows(self, engine) -> None:
        sm = _make_sm(engine)
        sm.on_fill(order_id="o1", instrument="EURUSD", units=1000, avg_price=1.10)
        sm.on_close(
            order_id="o1",
            instrument="EURUSD",
            reasons=[{"priority": 1, "reason_code": "tp", "detail": ""}],
            primary_reason_code="tp",
        )
        pos_rows = _outbox_rows(engine, table_name="positions")
        ce_rows = _outbox_rows(engine, table_name="close_events")
        assert len(pos_rows) == 2  # 1 open + 1 close
        assert len(ce_rows) == 1

    def test_reasons_json_stored_in_close_events(self, engine) -> None:
        sm = _make_sm(engine)
        sm.on_fill(order_id="o1", instrument="EURUSD", units=1000, avg_price=1.10)
        reasons = [{"priority": 1, "reason_code": "sl", "detail": "stop hit"}]
        sm.on_close(
            order_id="o1",
            instrument="EURUSD",
            reasons=reasons,
            primary_reason_code="sl",
        )
        row = _close_events_rows(engine)[0]
        stored = json.loads(row.reasons)
        assert stored == reasons


# --- on_risk_verdict ----------------------------------------------------------


class TestOnRiskVerdict:
    def test_writes_risk_events_row(self, engine) -> None:
        sm = _make_sm(engine)
        sm.on_risk_verdict(
            verdict="reject",
            cycle_id="cyc-1",
            instrument="EURUSD",
            constraint_violated="risk.duplicate_instrument",
        )
        rows = _risk_events_rows(engine)
        assert len(rows) == 1
        assert rows[0].verdict == "reject"
        assert rows[0].constraint_violated == "risk.duplicate_instrument"
        assert rows[0].instrument == "EURUSD"

    def test_returns_non_empty_reid(self, engine) -> None:
        sm = _make_sm(engine)
        reid = sm.on_risk_verdict(verdict="accept")
        assert isinstance(reid, str) and len(reid) > 0

    def test_accept_verdict_has_null_constraint(self, engine) -> None:
        sm = _make_sm(engine)
        sm.on_risk_verdict(verdict="accept", cycle_id="cyc-1", instrument="EURUSD")
        row = _risk_events_rows(engine)[0]
        assert row.verdict == "accept"
        assert row.constraint_violated is None

    def test_reject_stores_dotted_reason_code(self, engine) -> None:
        sm = _make_sm(engine)
        sm.on_risk_verdict(
            verdict="reject",
            constraint_violated="risk.max_open_positions",
        )
        row = _risk_events_rows(engine)[0]
        assert row.constraint_violated == "risk.max_open_positions"

    def test_enqueues_risk_events_outbox_row(self, engine) -> None:
        sm = _make_sm(engine)
        sm.on_risk_verdict(verdict="reject", constraint_violated="risk.cooloff")
        rows = _outbox_rows(engine, table_name="risk_events")
        assert len(rows) == 1

    def test_outbox_payload_contains_verdict(self, engine) -> None:
        sm = _make_sm(engine)
        sm.on_risk_verdict(verdict="accept", instrument="GBPUSD")
        row = _outbox_rows(engine, table_name="risk_events")[0]
        payload = json.loads(row.payload_json)
        assert payload["verdict"] == "accept"
        assert payload["instrument"] == "GBPUSD"

    def test_detail_dict_stored_as_json(self, engine) -> None:
        sm = _make_sm(engine)
        detail = {"size_reason": "zero_size"}
        sm.on_risk_verdict(
            verdict="reject",
            constraint_violated="risk.zero_size",
            detail=detail,
        )
        row = _risk_events_rows(engine)[0]
        stored = json.loads(row.detail)
        assert stored == detail

    def test_multiple_verdicts_all_persisted(self, engine) -> None:
        sm = _make_sm(engine)
        sm.on_risk_verdict(verdict="reject", constraint_violated="risk.cooloff")
        sm.on_risk_verdict(verdict="accept")
        sm.on_risk_verdict(verdict="reject", constraint_violated="risk.max_open_positions")
        rows = _risk_events_rows(engine)
        assert len(rows) == 3
