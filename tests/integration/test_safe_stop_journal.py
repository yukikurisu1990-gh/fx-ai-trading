"""Integration tests for SafeStopJournal — fsync + read_all (6.1).

No DATABASE_URL required — journal is file-based.
Tests use tmp_path fixture for isolation.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from fx_ai_trading.supervisor.safe_stop_journal import SafeStopJournal

_FIXED_AT = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)


@pytest.fixture()
def journal(tmp_path: Path) -> SafeStopJournal:
    return SafeStopJournal(journal_path=tmp_path / "safe_stop.jsonl")


class TestAppend:
    def test_creates_file_on_first_append(self, journal, tmp_path) -> None:
        journal.append({"event_code": "safe_stop.triggered", "occurred_at": _FIXED_AT.isoformat()})
        assert (tmp_path / "safe_stop.jsonl").exists()

    def test_written_entry_is_valid_jsonl(self, journal, tmp_path) -> None:
        journal.append({"event_code": "test", "occurred_at": _FIXED_AT.isoformat()})
        lines = (tmp_path / "safe_stop.jsonl").read_text().splitlines()
        assert len(lines) == 1
        parsed = json.loads(lines[0])
        assert parsed["event_code"] == "test"

    def test_multiple_appends_produce_multiple_lines(self, journal, tmp_path) -> None:
        journal.append({"event_code": "ev1", "occurred_at": _FIXED_AT.isoformat()})
        journal.append({"event_code": "ev2", "occurred_at": _FIXED_AT.isoformat()})
        lines = (tmp_path / "safe_stop.jsonl").read_text().splitlines()
        assert len(lines) == 2

    def test_append_preserves_all_fields(self, journal) -> None:
        entry = {
            "event_code": "safe_stop.triggered",
            "reason": "db_fail",
            "occurred_at": _FIXED_AT.isoformat(),
            "order_ids": ["o1"],
        }
        journal.append(entry)
        result = journal.read_all()
        assert result[0]["reason"] == "db_fail"
        assert result[0]["order_ids"] == ["o1"]


class TestReadAll:
    def test_read_all_returns_empty_when_file_absent(self, tmp_path) -> None:
        j = SafeStopJournal(journal_path=tmp_path / "nonexistent.jsonl")
        assert j.read_all() == []

    def test_read_all_returns_written_entries(self, journal) -> None:
        journal.append({"event_code": "e1", "occurred_at": _FIXED_AT.isoformat()})
        journal.append({"event_code": "e2", "occurred_at": _FIXED_AT.isoformat()})
        entries = journal.read_all()
        assert len(entries) == 2
        assert entries[0]["event_code"] == "e1"
        assert entries[1]["event_code"] == "e2"

    def test_read_all_skips_malformed_lines(self, tmp_path) -> None:
        path = tmp_path / "safe_stop.jsonl"
        path.write_text('{"event_code": "ok"}\nnot-json\n{"event_code": "also_ok"}\n')
        j = SafeStopJournal(journal_path=path)
        entries = j.read_all()
        assert len(entries) == 2
        assert entries[0]["event_code"] == "ok"
        assert entries[1]["event_code"] == "also_ok"

    def test_read_all_skips_blank_lines(self, tmp_path) -> None:
        path = tmp_path / "safe_stop.jsonl"
        path.write_text('{"event_code": "ok"}\n\n\n')
        j = SafeStopJournal(journal_path=path)
        assert len(j.read_all()) == 1


class TestDurability:
    def test_file_contains_data_after_close_and_reopen(self, tmp_path) -> None:
        path = tmp_path / "safe_stop.jsonl"
        j1 = SafeStopJournal(journal_path=path)
        j1.append({"event_code": "persisted", "occurred_at": _FIXED_AT.isoformat()})
        j2 = SafeStopJournal(journal_path=path)
        entries = j2.read_all()
        assert len(entries) == 1
        assert entries[0]["event_code"] == "persisted"

    def test_append_only_does_not_overwrite(self, tmp_path) -> None:
        path = tmp_path / "safe_stop.jsonl"
        j = SafeStopJournal(journal_path=path)
        j.append({"event_code": "first", "occurred_at": _FIXED_AT.isoformat()})
        j.append({"event_code": "second", "occurred_at": _FIXED_AT.isoformat()})
        entries = j.read_all()
        assert entries[0]["event_code"] == "first"
        assert entries[1]["event_code"] == "second"
