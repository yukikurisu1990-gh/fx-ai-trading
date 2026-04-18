"""Contract tests: safe_stop fire sequence order (6.1 / M7).

Verifies the mandatory four-step sequence:
    1. SafeStopJournal.append()          (file, DB-independent — always first)
    2. stop_callback()                    (loop stop — before notification)
    3. notifier.dispatch_direct_sync()   (critical Notifier)
    4. supervisor_events INSERT           (DB — always last)

Design invariant (D4 §2.1, phase6_hardening §6.1):
  - DB failure must not prevent steps 1-3 from executing.
  - Loop must stop (step 2) before external notification (step 3).
  - Journal (step 1) must execute even if steps 2-4 raise.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from fx_ai_trading.supervisor.safe_stop import SafeStopHandler
from fx_ai_trading.supervisor.safe_stop_journal import SafeStopJournal

_FIXED_AT = datetime(2026, 1, 1, tzinfo=UTC)
_REASON = "test_safe_stop"


@pytest.fixture()
def journal(tmp_path: Path) -> SafeStopJournal:
    return SafeStopJournal(journal_path=tmp_path / "safe_stop.jsonl")


# ---------------------------------------------------------------------------
# Step ordering (the critical contract)
# ---------------------------------------------------------------------------


class TestFireOrder:
    def test_journal_before_loop_stop(self, journal) -> None:
        """Journal (step 1) must complete before stop_callback (step 2)."""
        order: list[str] = []

        original_append = journal.append

        def tracking_append(entry: dict) -> None:
            order.append("journal")
            original_append(entry)

        journal.append = tracking_append  # type: ignore[method-assign]

        def stop_cb():
            order.append("loop_stop")

        handler = SafeStopHandler(
            journal=journal,
            stop_callback=stop_cb,
        )
        handler.fire(reason=_REASON, occurred_at=_FIXED_AT)
        assert order.index("journal") < order.index("loop_stop")

    def test_loop_stop_before_notifier(self, journal) -> None:
        """stop_callback (step 2) must complete before notifier (step 3)."""
        order: list[str] = []

        def stop_cb():
            order.append("loop_stop")

        notifier = MagicMock()

        def track_notify(*args, **kwargs):
            order.append("notifier")

        notifier.dispatch_direct_sync.side_effect = track_notify

        handler = SafeStopHandler(
            journal=journal,
            notifier=notifier,
            stop_callback=stop_cb,
        )
        handler.fire(reason=_REASON, occurred_at=_FIXED_AT)
        assert order.index("loop_stop") < order.index("notifier")

    def test_notifier_before_db(self, journal) -> None:
        """Notifier (step 3) must complete before DB write (step 4)."""
        order: list[str] = []

        notifier = MagicMock()

        def track_notify(*args, **kwargs):
            order.append("notifier")

        notifier.dispatch_direct_sync.side_effect = track_notify

        db_repo = MagicMock()

        def track_db(*args, **kwargs):
            order.append("db")

        db_repo.insert_event.side_effect = track_db
        ctx = MagicMock()

        handler = SafeStopHandler(
            journal=journal,
            notifier=notifier,
            supervisor_events_repo=db_repo,
            common_keys_ctx=ctx,
        )
        handler.fire(reason=_REASON, occurred_at=_FIXED_AT)
        assert order.index("notifier") < order.index("db")

    def test_full_sequence_order(self, journal) -> None:
        """Full four-step sequence must execute in strict order."""
        order: list[str] = []

        original_append = journal.append

        def tracking_append(entry: dict) -> None:
            order.append("journal")
            original_append(entry)

        journal.append = tracking_append  # type: ignore[method-assign]

        def stop_cb():
            order.append("loop_stop")

        notifier = MagicMock()

        def track_notify(*args, **kwargs):
            order.append("notifier")

        notifier.dispatch_direct_sync.side_effect = track_notify

        db_repo = MagicMock()

        def track_db(*args, **kwargs):
            order.append("db")

        db_repo.insert_event.side_effect = track_db
        ctx = MagicMock()

        handler = SafeStopHandler(
            journal=journal,
            notifier=notifier,
            stop_callback=stop_cb,
            supervisor_events_repo=db_repo,
            common_keys_ctx=ctx,
        )
        handler.fire(reason=_REASON, occurred_at=_FIXED_AT)
        assert order == ["journal", "loop_stop", "notifier", "db"]


# ---------------------------------------------------------------------------
# Durability: DB failure must not prevent steps 1-3
# ---------------------------------------------------------------------------


class TestDbFailureIsolation:
    def test_db_failure_does_not_prevent_journal_and_notifier(self, journal, tmp_path) -> None:
        """Steps 1-3 must complete even when step 4 (DB) raises."""
        order: list[str] = []

        original_append = journal.append

        def tracking_append(entry: dict) -> None:
            order.append("journal")
            original_append(entry)

        journal.append = tracking_append  # type: ignore[method-assign]

        def stop_cb():
            order.append("loop_stop")

        notifier = MagicMock()

        def track_notify(*args, **kwargs):
            order.append("notifier")

        notifier.dispatch_direct_sync.side_effect = track_notify

        db_repo = MagicMock()
        db_repo.insert_event.side_effect = Exception("DB down")
        ctx = MagicMock()

        handler = SafeStopHandler(
            journal=journal,
            notifier=notifier,
            stop_callback=stop_cb,
            supervisor_events_repo=db_repo,
            common_keys_ctx=ctx,
        )
        handler.fire(reason=_REASON, occurred_at=_FIXED_AT)

        assert "journal" in order
        assert "loop_stop" in order
        assert "notifier" in order

    def test_journal_written_when_db_fails(self, journal) -> None:
        db_repo = MagicMock()
        db_repo.insert_event.side_effect = Exception("DB down")
        ctx = MagicMock()

        handler = SafeStopHandler(
            journal=journal,
            supervisor_events_repo=db_repo,
            common_keys_ctx=ctx,
        )
        handler.fire(reason=_REASON, occurred_at=_FIXED_AT)

        entries = journal.read_all()
        assert len(entries) == 1
        assert entries[0]["event_code"] == "safe_stop.triggered"


# ---------------------------------------------------------------------------
# Notifier receives correct event
# ---------------------------------------------------------------------------


class TestNotifierPayload:
    def test_notifier_called_with_correct_event_code(self, journal) -> None:
        notifier = MagicMock()
        handler = SafeStopHandler(journal=journal, notifier=notifier)
        handler.fire(reason=_REASON, occurred_at=_FIXED_AT)

        notifier.dispatch_direct_sync.assert_called_once()
        event_arg = notifier.dispatch_direct_sync.call_args[0][0]
        assert event_arg.event_code == "safe_stop.triggered"

    def test_notifier_called_with_critical_severity(self, journal) -> None:
        notifier = MagicMock()
        handler = SafeStopHandler(journal=journal, notifier=notifier)
        handler.fire(reason=_REASON, occurred_at=_FIXED_AT)

        _, severity, _ = notifier.dispatch_direct_sync.call_args[0]
        assert severity == "critical"

    def test_payload_contains_reason(self, journal) -> None:
        notifier = MagicMock()
        handler = SafeStopHandler(journal=journal, notifier=notifier)
        handler.fire(reason="drawdown_exceeded", occurred_at=_FIXED_AT)

        _, _, payload = notifier.dispatch_direct_sync.call_args[0]
        assert payload["reason"] == "drawdown_exceeded"


# ---------------------------------------------------------------------------
# Journal content
# ---------------------------------------------------------------------------


class TestJournalContent:
    def test_journal_entry_has_event_code(self, journal) -> None:
        handler = SafeStopHandler(journal=journal)
        handler.fire(reason=_REASON, occurred_at=_FIXED_AT)
        entries = journal.read_all()
        assert entries[0]["event_code"] == "safe_stop.triggered"

    def test_journal_entry_has_reason(self, journal) -> None:
        handler = SafeStopHandler(journal=journal)
        handler.fire(reason="margin_call", occurred_at=_FIXED_AT)
        entries = journal.read_all()
        assert entries[0]["reason"] == "margin_call"

    def test_journal_entry_has_occurred_at(self, journal) -> None:
        handler = SafeStopHandler(journal=journal)
        handler.fire(reason=_REASON, occurred_at=_FIXED_AT)
        entries = journal.read_all()
        assert entries[0]["occurred_at"] == _FIXED_AT.isoformat()


# ---------------------------------------------------------------------------
# Structural: safe_stop sequence methods exist on SafeStopHandler
# ---------------------------------------------------------------------------


class TestStructural:
    def test_fire_method_exists(self) -> None:
        assert callable(getattr(SafeStopHandler, "fire", None))

    def test_four_step_methods_exist(self) -> None:
        assert callable(getattr(SafeStopHandler, "_fire_step1_journal", None))
        assert callable(getattr(SafeStopHandler, "_fire_step2_loop_stop", None))
        assert callable(getattr(SafeStopHandler, "_fire_step3_notifier", None))
        assert callable(getattr(SafeStopHandler, "_fire_step4_db", None))
