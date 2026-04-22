"""Contract tests: DispatchResult / dispatch_direct_sync return value (G-3 PR-3).

Closes audit finding R-4 (``docs/design/g3_notifier_fix_plan.md`` §3.3.3):
pre-PR-3 the critical-path dispatcher returned ``None``, so
``SafeStopHandler`` step 3 could only check "did dispatch raise" — a
silent ``FileNotifier`` I/O failure produced ``_safe_stop_completed=True``
even though the safe_stop evidence had not been durably written.

PR-3 contract:
  - ``dispatch_direct_sync`` returns a ``DispatchResult``.
  - ``DispatchResult.file`` is always present (FileNotifier is required).
  - ``DispatchResult.externals`` preserves the constructor order.
  - ``DispatchResult.email`` is ``None`` when no Email notifier is wired
    (PR-1 hard guard keeps this ``None`` in production).
  - Convenience properties (``file_success`` / ``all_success`` /
    ``any_external_success``) are pinned by the tests below.

C-9 (non-blocking): even when external / email fail, the call must not
raise — only logged warnings.  Verified here so a future refactor that
adds raise-on-fail behaviour fails loudly.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock

from fx_ai_trading.adapters.notifier.dispatcher import NotifierDispatcherImpl
from fx_ai_trading.adapters.notifier.file import FileNotifier
from fx_ai_trading.domain.notifier import DispatchResult, NotifyEvent, NotifyResult

_FIXED_AT = datetime(2026, 1, 1, tzinfo=UTC)

_CRITICAL_EVENT = NotifyEvent(
    event_code="safe_stop.triggered",
    severity="critical",
    payload={"reason": "test"},
    occurred_at=_FIXED_AT,
)


def _make_file_notifier(tmp_path: Path) -> FileNotifier:
    return FileNotifier(log_path=tmp_path / "notifications.jsonl")


def _ok(name: str = "mock") -> NotifyResult:
    return NotifyResult(success=True, notifier_name=name, sent_at=_FIXED_AT)


def _fail(name: str = "mock", err: str = "boom") -> NotifyResult:
    return NotifyResult(success=False, notifier_name=name, sent_at=_FIXED_AT, error_message=err)


# ---------------------------------------------------------------------------
# DispatchResult dataclass shape
# ---------------------------------------------------------------------------


class TestDispatchResultShape:
    def test_minimum_fields_present(self) -> None:
        result = DispatchResult(file=_ok("file"))
        assert result.file.success is True
        assert result.externals == []
        assert result.email is None

    def test_file_success_property_reflects_file_leg(self) -> None:
        ok = DispatchResult(file=_ok("file"))
        bad = DispatchResult(file=_fail("file"))
        assert ok.file_success is True
        assert bad.file_success is False

    def test_all_success_requires_every_configured_leg(self) -> None:
        # All OK → True.
        result = DispatchResult(file=_ok(), externals=[_ok("slack")], email=_ok("email"))
        assert result.all_success is True
        # Any leg failure → False.
        assert DispatchResult(file=_fail(), externals=[_ok("slack")]).all_success is False
        assert DispatchResult(file=_ok(), externals=[_fail("slack")]).all_success is False
        assert (
            DispatchResult(file=_ok(), externals=[_ok("slack")], email=_fail("email")).all_success
            is False
        )
        # Email=None is treated as "not configured" → not a failure.
        assert DispatchResult(file=_ok(), externals=[_ok("slack")], email=None).all_success is True

    def test_any_external_success_property(self) -> None:
        assert DispatchResult(file=_ok(), externals=[]).any_external_success is False
        assert DispatchResult(file=_ok(), externals=[_fail("slack")]).any_external_success is False
        assert (
            DispatchResult(
                file=_ok(), externals=[_fail("slack"), _ok("pager")]
            ).any_external_success
            is True
        )


# ---------------------------------------------------------------------------
# dispatch_direct_sync return value
# ---------------------------------------------------------------------------


class TestDispatchDirectSyncReturn:
    def test_returns_dispatch_result(self, tmp_path) -> None:
        file_notifier = _make_file_notifier(tmp_path)
        dispatcher = NotifierDispatcherImpl(file_notifier=file_notifier)
        result = dispatcher.dispatch_direct_sync(_CRITICAL_EVENT, "critical", {})
        assert isinstance(result, DispatchResult)

    def test_file_leg_populated_with_real_file_notifier(self, tmp_path) -> None:
        file_notifier = _make_file_notifier(tmp_path)
        dispatcher = NotifierDispatcherImpl(file_notifier=file_notifier)
        result = dispatcher.dispatch_direct_sync(_CRITICAL_EVENT, "critical", {})
        assert result.file.success is True
        assert result.file.notifier_name == "file"
        assert result.file_success is True

    def test_externals_preserved_in_constructor_order(self, tmp_path) -> None:
        file_notifier = _make_file_notifier(tmp_path)
        ext1 = MagicMock()
        ext1.send.return_value = _ok("slack")
        ext2 = MagicMock()
        ext2.send.return_value = _fail("pager", err="paged out")
        dispatcher = NotifierDispatcherImpl(
            file_notifier=file_notifier,
            external_notifiers=[ext1, ext2],
        )
        result = dispatcher.dispatch_direct_sync(_CRITICAL_EVENT, "critical", {})
        assert [r.notifier_name for r in result.externals] == ["slack", "pager"]
        assert result.externals[0].success is True
        assert result.externals[1].success is False

    def test_email_none_when_not_configured(self, tmp_path) -> None:
        file_notifier = _make_file_notifier(tmp_path)
        dispatcher = NotifierDispatcherImpl(file_notifier=file_notifier)
        result = dispatcher.dispatch_direct_sync(_CRITICAL_EVENT, "critical", {})
        # PR-1 hard guard: factory never wires Email — assert the
        # dispatcher's contract surface mirrors that hard guard so a
        # future "email defaults to something" change fails this test.
        assert result.email is None

    def test_email_populated_when_configured(self, tmp_path) -> None:
        file_notifier = _make_file_notifier(tmp_path)
        email = MagicMock()
        email.send.return_value = _ok("email")
        dispatcher = NotifierDispatcherImpl(
            file_notifier=file_notifier,
            email_notifier=email,
        )
        result = dispatcher.dispatch_direct_sync(_CRITICAL_EVENT, "critical", {})
        assert result.email is not None
        assert result.email.notifier_name == "email"
        assert result.email.success is True

    def test_external_failure_does_not_raise_and_file_leg_still_succeeds(self, tmp_path) -> None:
        """C-9: external failure must not stop the fan-out or raise."""
        file_notifier = _make_file_notifier(tmp_path)
        ext = MagicMock()
        ext.send.return_value = _fail("slack", err="slack 503")
        dispatcher = NotifierDispatcherImpl(
            file_notifier=file_notifier,
            external_notifiers=[ext],
        )
        result = dispatcher.dispatch_direct_sync(_CRITICAL_EVENT, "critical", {})
        assert result.file_success is True
        assert result.externals[0].success is False
        # C-5 surface: any_external_success may be False but file_success
        # is True — SafeStop must not flip _safe_stop_completed to False.
        assert result.any_external_success is False

    def test_email_failure_does_not_raise_and_file_leg_still_succeeds(self, tmp_path) -> None:
        file_notifier = _make_file_notifier(tmp_path)
        email = MagicMock()
        email.send.return_value = _fail("email", err="smtp down")
        dispatcher = NotifierDispatcherImpl(
            file_notifier=file_notifier,
            email_notifier=email,
        )
        result = dispatcher.dispatch_direct_sync(_CRITICAL_EVENT, "critical", {})
        assert result.file_success is True
        assert result.email is not None
        assert result.email.success is False

    def test_file_failure_surfaces_in_dispatch_result(self, tmp_path) -> None:
        """File leg failure must be inspectable via ``file_success`` (C-4)."""
        file_notifier = MagicMock()
        file_notifier.send.return_value = _fail("file", err="disk full")
        dispatcher = NotifierDispatcherImpl(file_notifier=file_notifier)
        result = dispatcher.dispatch_direct_sync(_CRITICAL_EVENT, "critical", {})
        assert result.file.success is False
        assert result.file_success is False
        assert result.file.error_message == "disk full"

    def test_all_legs_failing_still_returns_dispatch_result(self, tmp_path) -> None:
        """Worst case: every leg fails — must still return DispatchResult, not raise."""
        file_notifier = MagicMock()
        file_notifier.send.return_value = _fail("file", err="disk full")
        ext = MagicMock()
        ext.send.return_value = _fail("slack", err="503")
        email = MagicMock()
        email.send.return_value = _fail("email", err="smtp down")
        dispatcher = NotifierDispatcherImpl(
            file_notifier=file_notifier,
            external_notifiers=[ext],
            email_notifier=email,
        )
        result = dispatcher.dispatch_direct_sync(_CRITICAL_EVENT, "critical", {})
        assert result.file_success is False
        assert result.externals[0].success is False
        assert result.email is not None and result.email.success is False
        assert result.all_success is False


# ---------------------------------------------------------------------------
# Fan-out side effects: every configured leg is still called even when
# earlier legs fail (C-9 non-blocking guarantee).
# ---------------------------------------------------------------------------


class TestFanOutContinuesOnFailure:
    def test_file_failure_does_not_short_circuit_externals_or_email(self, tmp_path) -> None:
        file_notifier = MagicMock()
        file_notifier.send.return_value = _fail("file", err="disk full")
        ext = MagicMock()
        ext.send.return_value = _ok("slack")
        email = MagicMock()
        email.send.return_value = _ok("email")
        dispatcher = NotifierDispatcherImpl(
            file_notifier=file_notifier,
            external_notifiers=[ext],
            email_notifier=email,
        )
        result = dispatcher.dispatch_direct_sync(_CRITICAL_EVENT, "critical", {})
        # File failed first but externals/email still ran.
        ext.send.assert_called_once()
        email.send.assert_called_once()
        assert result.file_success is False
        assert result.externals[0].success is True
        assert result.email is not None and result.email.success is True

    def test_external_failure_does_not_short_circuit_email(self, tmp_path) -> None:
        file_notifier = _make_file_notifier(tmp_path)
        ext = MagicMock()
        ext.send.return_value = _fail("slack", err="503")
        email = MagicMock()
        email.send.return_value = _ok("email")
        dispatcher = NotifierDispatcherImpl(
            file_notifier=file_notifier,
            external_notifiers=[ext],
            email_notifier=email,
        )
        dispatcher.dispatch_direct_sync(_CRITICAL_EVENT, "critical", {})
        email.send.assert_called_once()
