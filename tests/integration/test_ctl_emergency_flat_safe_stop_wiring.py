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
