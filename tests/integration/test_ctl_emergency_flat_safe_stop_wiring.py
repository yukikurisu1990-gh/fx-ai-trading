"""Integration tests: ctl emergency-flat-all → SafeStop wiring (PR-α / U-9).

Verifies that ``_do_emergency_flat`` — once 2-factor confirmation passes
and the existing FileNotifier event has been written — additionally:

  1. appends an ``emergency_flat_initiated`` entry to the
     ``SafeStopJournal`` (durable, append-only), and
  2. requests Supervisor stop via ``ProcessManager.stop()`` so that the
     existing in-Supervisor signal handler fires
     ``trigger_safe_stop`` (per Designer Freeze U-9 spec).

Supervisor-未起動時 (``is_running() is False``) は journal append のみ
実行し stop は no-op。例外は出ない (fail-safe).

This PR is strictly additive: existing 2-factor gate behaviour and the
FileNotifier event are unchanged and covered by
``tests/contract/test_emergency_flat_two_factor.py``.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from fx_ai_trading.adapters.notifier.file import FileNotifier
from fx_ai_trading.common.clock import FixedClock
from fx_ai_trading.ops.two_factor import FixedTwoFactor
from fx_ai_trading.supervisor.safe_stop_journal import SafeStopJournal

_FIXED_AT = datetime(2026, 4, 22, 12, 0, 0, tzinfo=UTC)


# --- doubles -----------------------------------------------------------------


class _FakeProcessManager:
    """Minimal ProcessManager double — exposes is_running() / stop() only."""

    def __init__(self, *, running: bool, stop_returns: bool = True) -> None:
        self._running = running
        self._stop_returns = stop_returns
        self.is_running_calls = 0
        self.stop_calls = 0

    def is_running(self) -> bool:
        self.is_running_calls += 1
        return self._running

    def stop(self) -> bool:
        self.stop_calls += 1
        return self._stop_returns


# --- fixtures ----------------------------------------------------------------


@pytest.fixture()
def journal(tmp_path: Path) -> tuple[SafeStopJournal, Path]:
    journal_path = tmp_path / "safe_stop.jsonl"
    return SafeStopJournal(journal_path=journal_path), journal_path


@pytest.fixture()
def notifier(tmp_path: Path) -> tuple[FileNotifier, Path]:
    log_path = tmp_path / "notifications.jsonl"
    return FileNotifier(log_path=log_path), log_path


def _invoke(
    *,
    two_factor,
    notifier_obj,
    journal_obj,
    process_manager,
) -> bool:
    from scripts.ctl import _do_emergency_flat  # type: ignore[import]

    return _do_emergency_flat(
        two_factor,
        notifier=notifier_obj,
        clock=FixedClock(_FIXED_AT),
        journal=journal_obj,
        process_manager=process_manager,
    )


# --- tests -------------------------------------------------------------------


class TestSafeStopJournalAppend:
    def test_confirmed_two_factor_appends_emergency_flat_initiated(self, journal, notifier) -> None:
        j, journal_path = journal
        notifier_obj, _ = notifier
        pm = _FakeProcessManager(running=True)

        result = _invoke(
            two_factor=FixedTwoFactor(True),
            notifier_obj=notifier_obj,
            journal_obj=j,
            process_manager=pm,
        )

        assert result is True
        assert journal_path.exists()
        entries = [
            json.loads(ln)
            for ln in journal_path.read_text(encoding="utf-8").splitlines()
            if ln.strip()
        ]
        assert len(entries) == 1
        entry = entries[0]
        assert entry["event_code"] == "emergency_flat_initiated"
        assert entry["initiator"] == "ctl emergency-flat-all"
        assert entry["occurred_at"].startswith("2026-04-22T12:00:00")
        assert "pid" in entry

    def test_rejected_two_factor_writes_no_journal_entry(self, journal, notifier) -> None:
        j, journal_path = journal
        notifier_obj, _ = notifier
        pm = _FakeProcessManager(running=True)

        result = _invoke(
            two_factor=FixedTwoFactor(False),
            notifier_obj=notifier_obj,
            journal_obj=j,
            process_manager=pm,
        )

        assert result is False
        assert not journal_path.exists()
        # Stop must NOT be requested when 2-factor rejected.
        assert pm.stop_calls == 0
        assert pm.is_running_calls == 0


class TestProcessManagerStopWiring:
    def test_supervisor_running_calls_stop(self, journal, notifier) -> None:
        j, _ = journal
        notifier_obj, _ = notifier
        pm = _FakeProcessManager(running=True)

        _invoke(
            two_factor=FixedTwoFactor(True),
            notifier_obj=notifier_obj,
            journal_obj=j,
            process_manager=pm,
        )

        assert pm.is_running_calls == 1
        assert pm.stop_calls == 1

    def test_supervisor_not_running_skips_stop_no_exception(self, journal, notifier) -> None:
        """U-9 fail-safe: PID file 不在 / 死プロセス → journal だけ書いて終了."""
        j, journal_path = journal
        notifier_obj, _ = notifier
        pm = _FakeProcessManager(running=False)

        try:
            result = _invoke(
                two_factor=FixedTwoFactor(True),
                notifier_obj=notifier_obj,
                journal_obj=j,
                process_manager=pm,
            )
        except Exception as exc:
            pytest.fail(f"Supervisor-未起動時に例外が発生してはならない: {exc}")

        assert result is True
        # is_running was checked, stop was NOT called.
        assert pm.is_running_calls == 1
        assert pm.stop_calls == 0
        # Journal entry was still written.
        assert journal_path.exists()
        entries = [
            json.loads(ln)
            for ln in journal_path.read_text(encoding="utf-8").splitlines()
            if ln.strip()
        ]
        assert len(entries) == 1
        assert entries[0]["event_code"] == "emergency_flat_initiated"

    def test_supervisor_stop_returns_false_does_not_raise(self, journal, notifier) -> None:
        """is_running() == True だが stop() == False (race) でも例外を出さない."""
        j, _ = journal
        notifier_obj, _ = notifier
        pm = _FakeProcessManager(running=True, stop_returns=False)

        try:
            result = _invoke(
                two_factor=FixedTwoFactor(True),
                notifier_obj=notifier_obj,
                journal_obj=j,
                process_manager=pm,
            )
        except Exception as exc:
            pytest.fail(f"stop() == False でも例外を出してはならない: {exc}")

        assert result is True
        assert pm.stop_calls == 1


class TestExistingNotifierBehaviourPreserved:
    def test_filenotifier_event_still_written(self, journal, notifier) -> None:
        """The PR-α additions MUST NOT regress the existing FileNotifier path."""
        j, _ = journal
        notifier_obj, log_path = notifier
        pm = _FakeProcessManager(running=False)

        _invoke(
            two_factor=FixedTwoFactor(True),
            notifier_obj=notifier_obj,
            journal_obj=j,
            process_manager=pm,
        )

        assert log_path.exists()
        entry = json.loads(log_path.read_text(encoding="utf-8"))
        assert entry["event_code"] == "EMERGENCY_FLAT_ALL"
        assert entry["severity"] == "critical"


# --- G-2 fix: _do_emergency_flat_positions closes open paper positions --------

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
    outbox_id      TEXT PRIMARY KEY,
    table_name     TEXT NOT NULL,
    primary_key    TEXT NOT NULL,
    version_no     BIGINT NOT NULL DEFAULT 0,
    payload_json   TEXT NOT NULL,
    enqueued_at    TEXT NOT NULL,
    acked_at       TEXT,
    last_error     TEXT,
    attempt_count  INTEGER NOT NULL DEFAULT 0,
    next_attempt_at TEXT,
    run_id         TEXT,
    environment    TEXT,
    code_version   TEXT,
    config_version TEXT
)
"""
_DDL_ORDERS = """
CREATE TABLE orders (order_id TEXT PRIMARY KEY, direction TEXT NOT NULL)
"""


def _make_db_engine():
    from sqlalchemy import create_engine, text

    eng = create_engine("sqlite:///:memory:")
    with eng.begin() as conn:
        conn.execute(text(_DDL_POSITIONS))
        conn.execute(text(_DDL_CLOSE_EVENTS))
        conn.execute(text(_DDL_OUTBOX))
        conn.execute(text(_DDL_ORDERS))
    return eng


def _seed_open_position(engine, *, order_id: str, instrument: str, account_id: str = "acc-1"):
    from sqlalchemy import text

    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO orders (order_id, direction) VALUES (:oid, 'buy') "
                "ON CONFLICT DO NOTHING"
            ),
            {"oid": order_id},
        )
        conn.execute(
            text(
                "INSERT INTO positions "
                "(position_snapshot_id, order_id, account_id, instrument, "
                " event_type, units, avg_price, unrealized_pl, realized_pl, "
                " event_time_utc) "
                "VALUES (:psid, :oid, :aid, :inst, 'open', 1000, 1.10, NULL, NULL, "
                "        '2026-04-28T10:00:00+00:00')"
            ),
            {"psid": f"ps-{order_id}", "oid": order_id, "aid": account_id, "inst": instrument},
        )


class TestEmergencyFlatPositions:
    """G-2 fix: _do_emergency_flat_positions closes open paper positions."""

    def _close_events(self, engine):
        from sqlalchemy import text

        with engine.connect() as conn:
            return conn.execute(text("SELECT * FROM close_events")).fetchall()

    def test_closes_single_open_position(self) -> None:
        from scripts.ctl import _do_emergency_flat_positions  # type: ignore[import]

        engine = _make_db_engine()
        _seed_open_position(engine, order_id="o1", instrument="EUR_USD")

        count = _do_emergency_flat_positions(
            account_id="acc-1",
            engine=engine,
            clock=FixedClock(_FIXED_AT),
        )

        assert count == 1
        assert len(self._close_events(engine)) == 1
        ce = self._close_events(engine)[0]
        assert ce.primary_reason_code == "emergency_stop"

    def test_closes_multiple_open_positions(self) -> None:
        from scripts.ctl import _do_emergency_flat_positions  # type: ignore[import]

        engine = _make_db_engine()
        _seed_open_position(engine, order_id="o1", instrument="EUR_USD")
        _seed_open_position(engine, order_id="o2", instrument="USD_JPY")

        count = _do_emergency_flat_positions(
            account_id="acc-1",
            engine=engine,
            clock=FixedClock(_FIXED_AT),
        )

        assert count == 2
        assert len(self._close_events(engine)) == 2

    def test_no_positions_returns_zero(self) -> None:
        from scripts.ctl import _do_emergency_flat_positions  # type: ignore[import]

        engine = _make_db_engine()
        count = _do_emergency_flat_positions(
            account_id="acc-1",
            engine=engine,
            clock=FixedClock(_FIXED_AT),
        )
        assert count == 0


class TestEmergencyFlatCallsPositionClose:
    """G-2 fix: _do_emergency_flat() calls position close when env has DB URL."""

    def test_env_with_db_url_closes_open_positions(self, journal, notifier, tmp_path) -> None:
        from scripts.ctl import _do_emergency_flat  # type: ignore[import]

        engine = _make_db_engine()
        _seed_open_position(engine, order_id="o1", instrument="EUR_USD")

        # Patch create_engine via env injection + monkeypatching is complex;
        # instead verify via a spy on _do_emergency_flat_positions.
        from unittest.mock import patch

        j, _ = journal
        notifier_obj, _ = notifier
        pm = _FakeProcessManager(running=False)

        closed_counts = []

        def _spy_positions(**kwargs):
            closed_counts.append(kwargs.get("account_id"))
            return 1

        with patch("scripts.ctl._do_emergency_flat_positions", side_effect=_spy_positions):
            result = _do_emergency_flat(
                FixedTwoFactor(True),
                notifier=notifier_obj,
                clock=FixedClock(_FIXED_AT),
                journal=j,
                process_manager=pm,
                env={"DATABASE_URL": "sqlite:///:memory:", "OANDA_ACCOUNT_ID": "acc-1"},
            )

        assert result is True
        assert closed_counts == ["acc-1"]

    def test_missing_database_url_skips_position_close(self, journal, notifier) -> None:
        from unittest.mock import patch

        from scripts.ctl import _do_emergency_flat  # type: ignore[import]

        j, _ = journal
        notifier_obj, _ = notifier
        pm = _FakeProcessManager(running=False)
        calls = []

        def _spy(**kwargs):
            calls.append(1)
            return 0

        with patch("scripts.ctl._do_emergency_flat_positions", side_effect=_spy):
            result = _do_emergency_flat(
                FixedTwoFactor(True),
                notifier=notifier_obj,
                clock=FixedClock(_FIXED_AT),
                journal=j,
                process_manager=pm,
                env={"OANDA_ACCOUNT_ID": "acc-1"},  # DATABASE_URL missing
            )

        assert result is True
        assert calls == []  # position close NOT called

    def test_rejected_2fa_skips_position_close(self, journal, notifier) -> None:
        from unittest.mock import patch

        from scripts.ctl import _do_emergency_flat  # type: ignore[import]

        j, _ = journal
        notifier_obj, _ = notifier
        pm = _FakeProcessManager(running=False)
        calls = []

        def _noop_flat(**_kw):
            calls.append(1)
            return 0

        with patch("scripts.ctl._do_emergency_flat_positions", side_effect=_noop_flat):
            result = _do_emergency_flat(
                FixedTwoFactor(False),
                notifier=notifier_obj,
                clock=FixedClock(_FIXED_AT),
                journal=j,
                process_manager=pm,
                env={"DATABASE_URL": "sqlite:///:memory:", "OANDA_ACCOUNT_ID": "acc-1"},
            )

        assert result is False
        assert calls == []  # 2FA rejected → position close never reached
