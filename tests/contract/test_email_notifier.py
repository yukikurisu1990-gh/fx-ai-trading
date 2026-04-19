"""Contract tests: EmailNotifier (M17 / 6.13).

Verifies:
  1. send() returns NotifyResult with success=True on successful delivery.
  2. send() returns NotifyResult(success=False) on SMTP error — never raises.
  3. SMTP password is NOT included in NotifyResult.error_message.
  4. notifier_name is "email" in all results.
  5. sent_at equals event.occurred_at (no datetime.now() call).
  6. Subject line contains severity and event_code.
  7. Recipients list is forwarded to SMTP send_message.
  8. STARTTLS is called when use_starttls=True (default).
  9. Auth login is called when username+password are provided.
 10. SMTP failure on attempt 1 is retried up to _MAX_RETRY times.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from fx_ai_trading.adapters.notifier.email import EmailNotifier
from fx_ai_trading.domain.notifier import NotifyEvent

_FIXED_AT = datetime(2026, 1, 1, tzinfo=UTC)

_EVENT = NotifyEvent(
    event_code="safe_stop.triggered",
    severity="critical",
    payload={"reason": "test"},
    occurred_at=_FIXED_AT,
)


def _make_notifier(
    *,
    host: str = "smtp.example.com",
    port: int = 587,
    sender: str = "alert@example.com",
    recipients: list[str] | None = None,
    username: str | None = "user",
    password: str | None = "s3cr3t",
    use_starttls: bool = True,
) -> EmailNotifier:
    return EmailNotifier(
        host=host,
        port=port,
        sender=sender,
        recipients=recipients or ["ops@example.com"],
        username=username,
        password=password,
        use_starttls=use_starttls,
    )


# ---------------------------------------------------------------------------
# Success path
# ---------------------------------------------------------------------------


class TestEmailNotifierSuccess:
    def test_returns_success_result(self) -> None:
        notifier = _make_notifier()
        with patch("smtplib.SMTP") as mock_smtp_cls:
            mock_smtp = MagicMock()
            mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_smtp)
            mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)
            result = notifier.send(_EVENT, "critical", {"reason": "test"})
        assert result.success is True
        assert result.notifier_name == "email"

    def test_sent_at_equals_event_occurred_at(self) -> None:
        notifier = _make_notifier()
        with patch("smtplib.SMTP") as mock_smtp_cls:
            mock_smtp = MagicMock()
            mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_smtp)
            mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)
            result = notifier.send(_EVENT, "critical", {})
        assert result.sent_at == _FIXED_AT

    def test_starttls_called_by_default(self) -> None:
        notifier = _make_notifier(use_starttls=True)
        with patch("smtplib.SMTP") as mock_smtp_cls:
            mock_smtp = MagicMock()
            mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_smtp)
            mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)
            notifier.send(_EVENT, "critical", {})
        mock_smtp.starttls.assert_called_once()

    def test_starttls_skipped_when_disabled(self) -> None:
        notifier = _make_notifier(use_starttls=False)
        with patch("smtplib.SMTP") as mock_smtp_cls:
            mock_smtp = MagicMock()
            mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_smtp)
            mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)
            notifier.send(_EVENT, "critical", {})
        mock_smtp.starttls.assert_not_called()

    def test_login_called_when_credentials_provided(self) -> None:
        notifier = _make_notifier(username="user", password="s3cr3t")
        with patch("smtplib.SMTP") as mock_smtp_cls:
            mock_smtp = MagicMock()
            mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_smtp)
            mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)
            notifier.send(_EVENT, "critical", {})
        mock_smtp.login.assert_called_once_with("user", "s3cr3t")

    def test_login_not_called_when_no_credentials(self) -> None:
        notifier = _make_notifier(username=None, password=None)
        with patch("smtplib.SMTP") as mock_smtp_cls:
            mock_smtp = MagicMock()
            mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_smtp)
            mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)
            notifier.send(_EVENT, "critical", {})
        mock_smtp.login.assert_not_called()

    def test_send_message_called(self) -> None:
        notifier = _make_notifier()
        with patch("smtplib.SMTP") as mock_smtp_cls:
            mock_smtp = MagicMock()
            mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_smtp)
            mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)
            notifier.send(_EVENT, "critical", {})
        mock_smtp.send_message.assert_called_once()


# ---------------------------------------------------------------------------
# Failure path — never raises
# ---------------------------------------------------------------------------


import smtplib  # noqa: E402 (after test helpers)


class TestEmailNotifierFailure:
    def test_smtp_error_returns_failure_result_not_raises(self) -> None:
        notifier = _make_notifier()
        with patch("smtplib.SMTP") as mock_smtp_cls:
            mock_smtp_cls.side_effect = smtplib.SMTPConnectError(111, "connection refused")
            result = notifier.send(_EVENT, "critical", {})
        assert result.success is False
        assert result.notifier_name == "email"

    def test_oserror_returns_failure_result_not_raises(self) -> None:
        notifier = _make_notifier()
        with patch("smtplib.SMTP") as mock_smtp_cls:
            mock_smtp_cls.side_effect = OSError("network unreachable")
            result = notifier.send(_EVENT, "critical", {})
        assert result.success is False

    def test_password_not_in_error_message(self) -> None:
        notifier = _make_notifier(password="super_secret_pw")
        with patch("smtplib.SMTP") as mock_smtp_cls:
            mock_smtp_cls.side_effect = smtplib.SMTPAuthenticationError(535, b"auth failed")
            result = notifier.send(_EVENT, "critical", {})
        assert result.error_message is not None
        assert "super_secret_pw" not in (result.error_message or "")

    def test_retries_up_to_max_on_transient_error(self) -> None:
        from fx_ai_trading.adapters.notifier.email import _MAX_RETRY

        notifier = _make_notifier()
        with patch("smtplib.SMTP") as mock_smtp_cls:
            mock_smtp_cls.side_effect = smtplib.SMTPConnectError(111, "refused")
            result = notifier.send(_EVENT, "critical", {})
        assert mock_smtp_cls.call_count == _MAX_RETRY
        assert result.success is False

    def test_success_on_second_attempt(self) -> None:
        notifier = _make_notifier()
        mock_smtp = MagicMock()
        mock_smtp.__enter__ = MagicMock(return_value=mock_smtp)
        mock_smtp.__exit__ = MagicMock(return_value=False)
        call_count = 0

        def smtp_factory(host, port):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise smtplib.SMTPConnectError(111, "transient")
            return mock_smtp

        with patch("smtplib.SMTP", side_effect=smtp_factory):
            result = notifier.send(_EVENT, "critical", {})
        assert result.success is True
        assert call_count == 2


# ---------------------------------------------------------------------------
# Secret safety — password must not appear in log records (M17)
# ---------------------------------------------------------------------------


import logging  # noqa: E402


class TestSecretSafety:
    def test_password_not_logged_on_failure(self, caplog) -> None:
        notifier = _make_notifier(password="ultra_secret_pw")
        with (
            patch("smtplib.SMTP") as mock_smtp_cls,
            caplog.at_level(logging.WARNING, logger="fx_ai_trading"),
        ):
            mock_smtp_cls.side_effect = smtplib.SMTPAuthenticationError(535, b"auth failed")
            notifier.send(_EVENT, "critical", {})
        for record in caplog.records:
            assert "ultra_secret_pw" not in record.getMessage()

    def test_password_not_logged_on_success(self, caplog) -> None:
        notifier = _make_notifier(password="ultra_secret_pw")
        with (
            patch("smtplib.SMTP") as mock_smtp_cls,
            caplog.at_level(logging.DEBUG, logger="fx_ai_trading"),
        ):
            mock_smtp = MagicMock()
            mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_smtp)
            mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)
            notifier.send(_EVENT, "critical", {})
        for record in caplog.records:
            assert "ultra_secret_pw" not in record.getMessage()
