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


# ---------------------------------------------------------------------------
# Step exception isolation (G-2 / I-G2-06)
#
# Contract: a failure in any step must not prevent subsequent steps from
# executing.  Each exception must be logged (no silent failures) so that
# operators can correlate the partial completion with a root cause.
# ---------------------------------------------------------------------------


class TestStepExceptionIsolation:
    def test_step1_failure_does_not_prevent_steps_2_3_4(self, journal) -> None:
        """Journal failure must not prevent loop_stop / notifier / db."""
        order: list[str] = []

        # Make step 1 raise.
        def boom(_entry: dict) -> None:
            raise RuntimeError("disk full")

        journal.append = boom  # type: ignore[method-assign]

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
        # Must NOT raise.
        handler.fire(reason=_REASON, occurred_at=_FIXED_AT)

        assert order == ["loop_stop", "notifier", "db"]

    def test_step2_failure_does_not_prevent_steps_3_4(self, journal) -> None:
        """stop_callback failure must not prevent notifier / db."""
        order: list[str] = []

        original_append = journal.append

        def tracking_append(entry: dict) -> None:
            order.append("journal")
            original_append(entry)

        journal.append = tracking_append  # type: ignore[method-assign]

        def stop_cb():
            raise RuntimeError("loop already gone")

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

        assert order == ["journal", "notifier", "db"]

    def test_step3_failure_does_not_prevent_step_4(self, journal) -> None:
        """Notifier failure must not prevent supervisor_events INSERT."""
        order: list[str] = []

        original_append = journal.append

        def tracking_append(entry: dict) -> None:
            order.append("journal")
            original_append(entry)

        journal.append = tracking_append  # type: ignore[method-assign]

        def stop_cb():
            order.append("loop_stop")

        notifier = MagicMock()
        notifier.dispatch_direct_sync.side_effect = RuntimeError("slack 503")

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

        assert order == ["journal", "loop_stop", "db"]

    def test_all_steps_fail_does_not_raise(self, journal) -> None:
        """Even if every step raises, fire() must return cleanly."""

        def boom_journal(_entry: dict) -> None:
            raise RuntimeError("disk full")

        journal.append = boom_journal  # type: ignore[method-assign]

        def stop_cb():
            raise RuntimeError("loop gone")

        notifier = MagicMock()
        notifier.dispatch_direct_sync.side_effect = RuntimeError("slack down")

        db_repo = MagicMock()
        db_repo.insert_event.side_effect = RuntimeError("DB down")
        ctx = MagicMock()

        handler = SafeStopHandler(
            journal=journal,
            notifier=notifier,
            stop_callback=stop_cb,
            supervisor_events_repo=db_repo,
            common_keys_ctx=ctx,
        )
        # Must NOT raise.
        handler.fire(reason=_REASON, occurred_at=_FIXED_AT)

    def test_step1_failure_is_logged(self, journal, caplog) -> None:
        """Step 1 failure must emit an ERROR-level log (no silent failures)."""

        def boom(_entry: dict) -> None:
            raise RuntimeError("disk full")

        journal.append = boom  # type: ignore[method-assign]

        handler = SafeStopHandler(journal=journal)
        with caplog.at_level("ERROR", logger="fx_ai_trading.supervisor.safe_stop"):
            handler.fire(reason=_REASON, occurred_at=_FIXED_AT)

        messages = [r.getMessage() for r in caplog.records if r.levelname == "ERROR"]
        assert any("step 1" in m and "disk full" in m for m in messages), (
            f"step 1 failure not logged at ERROR level; got: {messages}"
        )

    def test_step2_failure_is_logged(self, journal, caplog) -> None:
        """Step 2 failure must emit an ERROR-level log (no silent failures)."""

        def stop_cb():
            raise RuntimeError("loop gone")

        handler = SafeStopHandler(journal=journal, stop_callback=stop_cb)
        with caplog.at_level("ERROR", logger="fx_ai_trading.supervisor.safe_stop"):
            handler.fire(reason=_REASON, occurred_at=_FIXED_AT)

        messages = [r.getMessage() for r in caplog.records if r.levelname == "ERROR"]
        assert any("step 2" in m and "loop gone" in m for m in messages), (
            f"step 2 failure not logged at ERROR level; got: {messages}"
        )

    def test_step3_failure_is_logged(self, journal, caplog) -> None:
        """Step 3 failure must emit an ERROR-level log (no silent failures)."""
        notifier = MagicMock()
        notifier.dispatch_direct_sync.side_effect = RuntimeError("slack 503")

        handler = SafeStopHandler(journal=journal, notifier=notifier)
        with caplog.at_level("ERROR", logger="fx_ai_trading.supervisor.safe_stop"):
            handler.fire(reason=_REASON, occurred_at=_FIXED_AT)

        messages = [r.getMessage() for r in caplog.records if r.levelname == "ERROR"]
        assert any("step 3" in m and "slack 503" in m for m in messages), (
            f"step 3 failure not logged at ERROR level; got: {messages}"
        )

    def test_step1_returns_false_on_exception(self, journal) -> None:
        """Step 1 must return False (not raise) on exception — PR-2 foundation."""

        def boom(_entry: dict) -> None:
            raise RuntimeError("disk full")

        journal.append = boom  # type: ignore[method-assign]

        handler = SafeStopHandler(journal=journal)
        assert handler._fire_step1_journal(_REASON, _FIXED_AT, {"reason": _REASON}) is False

    def test_step2_returns_false_on_exception(self, journal) -> None:
        """Step 2 must return False on exception."""

        def stop_cb():
            raise RuntimeError("loop gone")

        handler = SafeStopHandler(journal=journal, stop_callback=stop_cb)
        assert handler._fire_step2_loop_stop() is False

    def test_step3_returns_false_on_exception(self, journal) -> None:
        """Step 3 must return False on exception."""
        notifier = MagicMock()
        notifier.dispatch_direct_sync.side_effect = RuntimeError("slack down")

        handler = SafeStopHandler(journal=journal, notifier=notifier)
        assert handler._fire_step3_notifier(_FIXED_AT, {"reason": _REASON}) is False

    def test_step4_returns_false_on_exception(self, journal) -> None:
        """Step 4 must return False on exception (already wrapped pre-PR-1)."""
        db_repo = MagicMock()
        db_repo.insert_event.side_effect = RuntimeError("DB down")
        ctx = MagicMock()

        handler = SafeStopHandler(
            journal=journal,
            supervisor_events_repo=db_repo,
            common_keys_ctx=ctx,
        )
        assert handler._fire_step4_db(_FIXED_AT, {"reason": _REASON}, ctx) is False

    def test_steps_return_true_on_success(self, journal) -> None:
        """All steps must return True on the happy path."""
        notifier = MagicMock()
        db_repo = MagicMock()
        ctx = MagicMock()

        handler = SafeStopHandler(
            journal=journal,
            notifier=notifier,
            stop_callback=lambda: None,
            supervisor_events_repo=db_repo,
            common_keys_ctx=ctx,
        )
        assert handler._fire_step1_journal(_REASON, _FIXED_AT, {"reason": _REASON}) is True
        assert handler._fire_step2_loop_stop() is True
        assert handler._fire_step3_notifier(_FIXED_AT, {"reason": _REASON}) is True
        assert handler._fire_step4_db(_FIXED_AT, {"reason": _REASON}, ctx) is True

    def test_skipped_steps_return_true(self, journal) -> None:
        """Configured-skip path (dependency not set) must return True (no exception)."""
        # journal=None → step 1 skipped
        # stop_callback=None → step 2 skipped
        # notifier=None → step 3 skipped
        # repo/ctx=None → step 4 skipped
        handler = SafeStopHandler()
        assert handler._fire_step1_journal(_REASON, _FIXED_AT, {"reason": _REASON}) is True
        assert handler._fire_step2_loop_stop() is True
        assert handler._fire_step3_notifier(_FIXED_AT, {"reason": _REASON}) is True
        assert handler._fire_step4_db(_FIXED_AT, {"reason": _REASON}, None) is True
