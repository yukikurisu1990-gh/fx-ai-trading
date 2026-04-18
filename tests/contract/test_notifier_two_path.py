"""Contract tests: Notifier two-path dispatch (6.13).

Verifies:
  1. dispatch_direct_sync sends to FileNotifier AND external notifiers (no outbox).
  2. dispatch_via_outbox does NOT send to external notifiers (outbox path, M8).
  3. FileNotifier is always called first on the critical path.
  4. External notifier failure on critical path is logged but does not raise.
  5. dispatch_direct_sync and dispatch_via_outbox are separate code paths.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from fx_ai_trading.adapters.notifier.dispatcher import NotifierDispatcherImpl
from fx_ai_trading.adapters.notifier.file import FileNotifier
from fx_ai_trading.domain.notifier import NotifyEvent, NotifyResult

_FIXED_AT = datetime(2026, 1, 1, tzinfo=UTC)

_CRITICAL_EVENT = NotifyEvent(
    event_code="safe_stop.triggered",
    severity="critical",
    payload={"reason": "test"},
    occurred_at=_FIXED_AT,
)

_INFO_EVENT = NotifyEvent(
    event_code="order.filled",
    severity="info",
    payload={"order_id": "ord-1"},
    occurred_at=_FIXED_AT,
)


def _make_file_notifier(tmp_path: Path) -> FileNotifier:
    return FileNotifier(log_path=tmp_path / "notifications.jsonl")


def _make_ok_result(name: str = "mock") -> NotifyResult:
    return NotifyResult(success=True, notifier_name=name, sent_at=_FIXED_AT)


def _make_fail_result(name: str = "mock") -> NotifyResult:
    return NotifyResult(success=False, notifier_name=name, sent_at=_FIXED_AT, error_message="err")


# ---------------------------------------------------------------------------
# Critical path (dispatch_direct_sync)
# ---------------------------------------------------------------------------


class TestDispatchDirectSync:
    def test_file_notifier_called_on_critical(self, tmp_path) -> None:
        file_notifier = _make_file_notifier(tmp_path)
        dispatcher = NotifierDispatcherImpl(file_notifier=file_notifier)
        dispatcher.dispatch_direct_sync(_CRITICAL_EVENT, "critical", {"reason": "test"})
        log = (tmp_path / "notifications.jsonl").read_text()
        assert "safe_stop.triggered" in log

    def test_external_notifier_also_called_on_critical(self, tmp_path) -> None:
        file_notifier = _make_file_notifier(tmp_path)
        external = MagicMock()
        external.send.return_value = _make_ok_result("slack")
        dispatcher = NotifierDispatcherImpl(
            file_notifier=file_notifier, external_notifiers=[external]
        )
        dispatcher.dispatch_direct_sync(_CRITICAL_EVENT, "critical", {"reason": "test"})
        external.send.assert_called_once_with(_CRITICAL_EVENT, "critical", {"reason": "test"})

    def test_file_notifier_called_before_external(self, tmp_path) -> None:
        call_order: list[str] = []
        file_notifier = _make_file_notifier(tmp_path)
        original_send = file_notifier.send

        def file_send(*args, **kwargs):
            call_order.append("file")
            return original_send(*args, **kwargs)

        file_notifier.send = file_send  # type: ignore[method-assign]
        external = MagicMock()

        def ext_send(*args, **kwargs):
            call_order.append("external")
            return _make_ok_result()

        external.send.side_effect = ext_send
        dispatcher = NotifierDispatcherImpl(
            file_notifier=file_notifier, external_notifiers=[external]
        )
        dispatcher.dispatch_direct_sync(_CRITICAL_EVENT, "critical", {})
        assert call_order == ["file", "external"]

    def test_external_failure_does_not_raise(self, tmp_path) -> None:
        file_notifier = _make_file_notifier(tmp_path)
        external = MagicMock()
        external.send.return_value = _make_fail_result("slack")
        dispatcher = NotifierDispatcherImpl(
            file_notifier=file_notifier, external_notifiers=[external]
        )
        dispatcher.dispatch_direct_sync(_CRITICAL_EVENT, "critical", {})

    def test_multiple_externals_all_called(self, tmp_path) -> None:
        file_notifier = _make_file_notifier(tmp_path)
        ext1 = MagicMock()
        ext1.send.return_value = _make_ok_result("slack")
        ext2 = MagicMock()
        ext2.send.return_value = _make_ok_result("pager")
        dispatcher = NotifierDispatcherImpl(
            file_notifier=file_notifier, external_notifiers=[ext1, ext2]
        )
        dispatcher.dispatch_direct_sync(_CRITICAL_EVENT, "critical", {})
        ext1.send.assert_called_once()
        ext2.send.assert_called_once()


# ---------------------------------------------------------------------------
# Non-critical path (dispatch_via_outbox)
# ---------------------------------------------------------------------------


class TestDispatchViaOutbox:
    def test_file_notifier_called_for_non_critical(self, tmp_path) -> None:
        file_notifier = _make_file_notifier(tmp_path)
        dispatcher = NotifierDispatcherImpl(file_notifier=file_notifier)
        dispatcher.dispatch_via_outbox(_INFO_EVENT, "info", {"order_id": "ord-1"})
        log = (tmp_path / "notifications.jsonl").read_text()
        assert "order.filled" in log

    def test_external_notifiers_not_called_on_outbox_path(self, tmp_path) -> None:
        """Critical path isolation: external notifiers must NOT be called via outbox."""
        file_notifier = _make_file_notifier(tmp_path)
        external = MagicMock()
        dispatcher = NotifierDispatcherImpl(
            file_notifier=file_notifier, external_notifiers=[external]
        )
        dispatcher.dispatch_via_outbox(_INFO_EVENT, "info", {})
        external.send.assert_not_called()


# ---------------------------------------------------------------------------
# Two-path separation (structural)
# ---------------------------------------------------------------------------


class TestTwoPathSeparation:
    def test_direct_sync_and_outbox_are_separate_methods(self) -> None:
        assert hasattr(NotifierDispatcherImpl, "dispatch_direct_sync")
        assert hasattr(NotifierDispatcherImpl, "dispatch_via_outbox")
        assert (
            NotifierDispatcherImpl.dispatch_direct_sync
            is not NotifierDispatcherImpl.dispatch_via_outbox
        )

    def test_file_notifier_is_required(self) -> None:
        with pytest.raises(TypeError):
            NotifierDispatcherImpl()  # type: ignore[call-arg]
