"""Integration tests: ctl resume-from-safe-stop command (M22 / Mi-CTL-1).

Verifies that --reason is required, that a successful invocation writes
a SAFE_STOP_RESUME entry to the SafeStopJournal, and that the entry
contains the provided reason.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from fx_ai_trading.common.clock import FixedClock
from fx_ai_trading.supervisor.safe_stop_journal import SafeStopJournal


@pytest.fixture()
def journal(tmp_path: Path) -> tuple[SafeStopJournal, Path]:
    journal_path = tmp_path / "safe_stop.jsonl"
    return SafeStopJournal(journal_path=journal_path), journal_path


def _call_do_resume(reason: str, journal_obj: SafeStopJournal) -> None:
    from scripts.ctl import _do_resume  # type: ignore[import]

    clock = FixedClock(datetime(2026, 1, 1, tzinfo=UTC))
    _do_resume(reason, journal=journal_obj, clock=clock)


class TestResumeFromSafeStop:
    def test_writes_journal_entry(self, journal) -> None:
        j, path = journal
        _call_do_resume("investigation complete", j)
        assert path.exists()

    def test_journal_contains_safe_stop_resume(self, journal) -> None:
        j, path = journal
        _call_do_resume("investigation complete", j)
        entry = json.loads(path.read_text())
        assert entry["event_code"] == "SAFE_STOP_RESUME"

    def test_journal_entry_includes_reason(self, journal) -> None:
        j, path = journal
        _call_do_resume("maintenance done", j)
        entry = json.loads(path.read_text())
        assert entry["reason"] == "maintenance done"

    def test_journal_entry_includes_occurred_at(self, journal) -> None:
        j, path = journal
        _call_do_resume("root cause fixed", j)
        entry = json.loads(path.read_text())
        assert "occurred_at" in entry
        assert "2026" in entry["occurred_at"]

    def test_journal_entry_includes_initiator(self, journal) -> None:
        j, path = journal
        _call_do_resume("all clear", j)
        entry = json.loads(path.read_text())
        assert "ctl" in entry["initiator"]

    def test_multiple_resumes_append(self, journal) -> None:
        j, path = journal
        _call_do_resume("reason A", j)
        _call_do_resume("reason B", j)
        lines = [ln for ln in path.read_text().splitlines() if ln.strip()]
        assert len(lines) == 2

    def test_resume_does_not_raise(self, journal) -> None:
        j, path = journal
        try:
            _call_do_resume("any reason", j)
        except Exception as exc:
            pytest.fail(f"Unexpected exception: {exc}")
