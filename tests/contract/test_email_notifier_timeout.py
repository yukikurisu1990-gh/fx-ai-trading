"""Contract tests: EmailNotifier SMTP timeout / retry budget (G-3 PR-2).

Closes audit findings R-2 / R-3 from ``docs/design/g3_notifier_fix_plan.md``:

  R-2 — ``EmailNotifier`` had no SMTP timeout, so an unresponsive
        SMTP host could hang ``safe_stop`` step 3 indefinitely.
  R-3 — ``_MAX_RETRY = 3`` with no backoff stretched the wall-clock
        even when the host responded with errors quickly.

PR-2 fixes:

  - ``connect_timeout_s`` (default 10s) is forwarded to ``smtplib.SMTP``
    so both the TCP connect and subsequent socket reads are bounded.
  - ``_MAX_RETRY`` reduced from 3 → 2 so the worst-case wall-clock is
    ≤ 20s (well within the 30s ``safe_stop_step3_wall_budget_s`` from
    memo §3.3.1).

These tests pin the new contracts so a future refactor cannot quietly
re-open the indefinite-hang regression.
"""

from __future__ import annotations

import smtplib
import time
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from fx_ai_trading.adapters.notifier.email import (
    _DEFAULT_CONNECT_TIMEOUT_S,
    _MAX_RETRY,
    EmailNotifier,
)
from fx_ai_trading.domain.notifier import NotifyEvent

_FIXED_AT = datetime(2026, 1, 1, tzinfo=UTC)

_EVENT = NotifyEvent(
    event_code="safe_stop.triggered",
    severity="critical",
    payload={"reason": "timeout-contract"},
    occurred_at=_FIXED_AT,
)

# Wall-clock ceiling derived from memo §3.3.1.  Step-3 budget is 30s;
# the Email leg with PR-2 settings is bounded at 20s.  Asserting the
# 30s ceiling here proves that even with maximum hangs the SafeStop
# block stays under the documented budget.
_SAFE_STOP_STEP3_BUDGET_S = 30


def _make_notifier(
    *,
    host: str = "smtp.example.com",
    port: int = 587,
    sender: str = "alert@example.com",
    recipients: list[str] | None = None,
    username: str | None = None,
    password: str | None = None,
    use_starttls: bool = True,
    connect_timeout_s: int | None = None,
) -> EmailNotifier:
    kwargs: dict = {
        "host": host,
        "port": port,
        "sender": sender,
        "recipients": recipients or ["ops@example.com"],
        "username": username,
        "password": password,
        "use_starttls": use_starttls,
    }
    if connect_timeout_s is not None:
        kwargs["connect_timeout_s"] = connect_timeout_s
    return EmailNotifier(**kwargs)


# ---------------------------------------------------------------------------
# Default values are pinned (regression guard)
# ---------------------------------------------------------------------------


class TestModuleConstants:
    def test_max_retry_is_two(self) -> None:
        # Memo §3.2 mandates 2 attempts (was 3).  Pinning this prevents
        # a future change from quietly bumping the SafeStop budget.
        assert _MAX_RETRY == 2

    def test_default_connect_timeout_is_ten_seconds(self) -> None:
        assert _DEFAULT_CONNECT_TIMEOUT_S == 10

    def test_worst_case_wall_clock_within_safe_stop_budget(self) -> None:
        # 10s × 2 = 20s ≤ 30s budget (memo §3.3.1).  This arithmetic
        # check fails loudly if either constant drifts in a way that
        # would push step 3 past the documented budget.
        assert _DEFAULT_CONNECT_TIMEOUT_S * _MAX_RETRY <= _SAFE_STOP_STEP3_BUDGET_S


# ---------------------------------------------------------------------------
# timeout kwarg propagation — proves connect-phase guard is active
# ---------------------------------------------------------------------------


class TestTimeoutKwargPropagation:
    def test_default_timeout_passed_to_smtplib(self) -> None:
        notifier = _make_notifier()
        with patch("smtplib.SMTP") as mock_smtp_cls:
            mock_smtp = MagicMock()
            mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_smtp)
            mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)
            notifier.send(_EVENT, "critical", {})

        # Caller must hand smtplib a timeout kwarg.  Without this, the
        # connect / send sockets fall back to ``socket._GLOBAL_DEFAULT_TIMEOUT``
        # (effectively None / no limit) and ``safe_stop`` can hang.
        mock_smtp_cls.assert_called_once()
        _, kwargs = mock_smtp_cls.call_args
        assert kwargs.get("timeout") == _DEFAULT_CONNECT_TIMEOUT_S

    def test_explicit_timeout_param_propagated(self) -> None:
        notifier = _make_notifier(connect_timeout_s=7)
        with patch("smtplib.SMTP") as mock_smtp_cls:
            mock_smtp = MagicMock()
            mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_smtp)
            mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)
            notifier.send(_EVENT, "critical", {})
        _, kwargs = mock_smtp_cls.call_args
        assert kwargs.get("timeout") == 7

    def test_host_and_port_forwarded_unchanged(self) -> None:
        notifier = _make_notifier(host="smtp.internal", port=2525)
        with patch("smtplib.SMTP") as mock_smtp_cls:
            mock_smtp = MagicMock()
            mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_smtp)
            mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)
            notifier.send(_EVENT, "critical", {})
        args, kwargs = mock_smtp_cls.call_args
        assert args == ("smtp.internal", 2525)
        assert kwargs.get("timeout") == _DEFAULT_CONNECT_TIMEOUT_S


# ---------------------------------------------------------------------------
# Hang behaviour — never blocks past the 30s SafeStop budget
# ---------------------------------------------------------------------------


class TestHangReturnsWithinBudget:
    def test_socket_timeout_returns_within_safe_stop_budget(self) -> None:
        """Socket-level timeout (TimeoutError) must surface as a NotifyResult,
        not propagate, and the total wall-clock must stay under 30s."""
        notifier = _make_notifier()
        with patch("smtplib.SMTP") as mock_smtp_cls:
            # TimeoutError inherits from OSError, which the notifier
            # already catches.  Each attempt fires "instantly" once the
            # socket-level timeout would have elapsed in production.
            mock_smtp_cls.side_effect = TimeoutError("connect timed out")
            start = time.monotonic()
            result = notifier.send(_EVENT, "critical", {})
            elapsed = time.monotonic() - start

        assert result.success is False
        assert result.notifier_name == "email"
        assert elapsed < _SAFE_STOP_STEP3_BUDGET_S, (
            f"send() took {elapsed:.2f}s — must stay under SafeStop step-3"
            f" budget of {_SAFE_STOP_STEP3_BUDGET_S}s (memo §3.3.1)"
        )

    def test_connect_refused_returns_within_safe_stop_budget(self) -> None:
        notifier = _make_notifier()
        with patch("smtplib.SMTP") as mock_smtp_cls:
            mock_smtp_cls.side_effect = smtplib.SMTPConnectError(111, "refused")
            start = time.monotonic()
            result = notifier.send(_EVENT, "critical", {})
            elapsed = time.monotonic() - start

        assert result.success is False
        assert elapsed < _SAFE_STOP_STEP3_BUDGET_S

    def test_smtp_server_disconnected_returns_within_safe_stop_budget(self) -> None:
        notifier = _make_notifier()
        with patch("smtplib.SMTP") as mock_smtp_cls:
            mock_smtp_cls.side_effect = smtplib.SMTPServerDisconnected("hung up")
            start = time.monotonic()
            result = notifier.send(_EVENT, "critical", {})
            elapsed = time.monotonic() - start
        assert result.success is False
        assert elapsed < _SAFE_STOP_STEP3_BUDGET_S


# ---------------------------------------------------------------------------
# Retry budget — exactly _MAX_RETRY attempts, no more
# ---------------------------------------------------------------------------


class TestRetryBudget:
    def test_total_attempts_capped_at_max_retry(self) -> None:
        notifier = _make_notifier()
        with patch("smtplib.SMTP") as mock_smtp_cls:
            mock_smtp_cls.side_effect = TimeoutError("hang")
            notifier.send(_EVENT, "critical", {})
        # Exactly 2 attempts, never 3.  Drift here would breach the 30s
        # SafeStop budget the moment the per-attempt timeout fires.
        assert mock_smtp_cls.call_count == _MAX_RETRY == 2

    def test_no_retry_after_success(self) -> None:
        notifier = _make_notifier()
        attempts = 0

        def smtp_factory(host, port, *args, **kwargs):
            nonlocal attempts
            attempts += 1
            mock_smtp = MagicMock()
            mock_smtp.__enter__ = MagicMock(return_value=mock_smtp)
            mock_smtp.__exit__ = MagicMock(return_value=False)
            return mock_smtp

        with patch("smtplib.SMTP", side_effect=smtp_factory):
            result = notifier.send(_EVENT, "critical", {})
        assert result.success is True
        assert attempts == 1

    def test_success_on_second_attempt_does_not_overshoot(self) -> None:
        notifier = _make_notifier()
        attempts = 0

        def smtp_factory(host, port, *args, **kwargs):
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise TimeoutError("first attempt hung")
            mock_smtp = MagicMock()
            mock_smtp.__enter__ = MagicMock(return_value=mock_smtp)
            mock_smtp.__exit__ = MagicMock(return_value=False)
            return mock_smtp

        with patch("smtplib.SMTP", side_effect=smtp_factory):
            result = notifier.send(_EVENT, "critical", {})
        assert result.success is True
        # Second attempt succeeded; we must NOT consume the third slot.
        assert attempts == 2
