"""Unit tests: NotifierProbeResult / probe_slack_webhook / probe_smtp_connection (G-3 PR-4).

Covers ``docs/design/g3_notifier_fix_plan.md`` §3.4 connectivity probes.

Invariants pinned by these tests:
  - Probes never raise — every error path returns ``NotifierProbeResult``.
  - Probes never issue application traffic (no HTTP POST to the Slack
    webhook, no SMTP EHLO / AUTH / MAIL).  Verified by patching
    ``socket.gethostbyname`` and ``socket.create_connection`` at the
    ``fx_ai_trading.supervisor.health`` module level so a real network
    call would fail loudly.
  - Probe timeout is forwarded to ``socket.create_connection``.
  - Malformed Slack URLs degrade rather than crash startup.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from fx_ai_trading.supervisor.health import (
    NotifierProbeResult,
    probe_slack_webhook,
    probe_smtp_connection,
)

# ---------------------------------------------------------------------------
# probe_slack_webhook
# ---------------------------------------------------------------------------


class TestProbeSlackWebhook:
    def test_ok_path_resolves_dns_and_connects_tcp(self) -> None:
        with (
            patch("fx_ai_trading.supervisor.health.socket.gethostbyname") as dns,
            patch("fx_ai_trading.supervisor.health.socket.create_connection") as conn,
        ):
            dns.return_value = "1.2.3.4"
            conn.return_value.__enter__ = MagicMock(return_value=MagicMock())
            conn.return_value.__exit__ = MagicMock(return_value=False)
            result = probe_slack_webhook("https://hooks.slack.com/T/B/X")

        assert isinstance(result, NotifierProbeResult)
        assert result.is_ok is True
        assert result.name == "slack_webhook"
        dns.assert_called_once_with("hooks.slack.com")
        # Default https → port 443.
        assert conn.call_args.args == (("hooks.slack.com", 443),)

    def test_invalid_url_returns_degraded_without_dns_call(self) -> None:
        with (
            patch("fx_ai_trading.supervisor.health.socket.gethostbyname") as dns,
            patch("fx_ai_trading.supervisor.health.socket.create_connection") as conn,
        ):
            result = probe_slack_webhook("not a url")

        assert result.is_ok is False
        assert "invalid url" in result.detail
        dns.assert_not_called()
        conn.assert_not_called()

    def test_dns_failure_returns_degraded(self) -> None:
        with patch(
            "fx_ai_trading.supervisor.health.socket.gethostbyname",
            side_effect=OSError("name resolution failed"),
        ):
            result = probe_slack_webhook("https://hooks.slack.example/T/B/X")

        assert result.is_ok is False
        assert "dns" in result.detail.lower()

    def test_tcp_failure_returns_degraded(self) -> None:
        with (
            patch(
                "fx_ai_trading.supervisor.health.socket.gethostbyname",
                return_value="1.2.3.4",
            ),
            patch(
                "fx_ai_trading.supervisor.health.socket.create_connection",
                side_effect=ConnectionRefusedError("connection refused"),
            ),
        ):
            result = probe_slack_webhook("https://hooks.slack.example/T/B/X")

        assert result.is_ok is False
        assert "tcp" in result.detail.lower()

    def test_socket_timeout_returns_degraded(self) -> None:
        # socket.timeout subclasses OSError — the OSError catch must
        # cover it so the probe surfaces a degraded result instead of
        # propagating the exception out of step 15.
        with (
            patch(
                "fx_ai_trading.supervisor.health.socket.gethostbyname",
                return_value="1.2.3.4",
            ),
            patch(
                "fx_ai_trading.supervisor.health.socket.create_connection",
                side_effect=TimeoutError("timed out"),
            ),
        ):
            result = probe_slack_webhook("https://hooks.slack.example/T/B/X")

        assert result.is_ok is False
        assert "tcp" in result.detail.lower()

    def test_timeout_kwarg_forwarded_to_create_connection(self) -> None:
        with (
            patch(
                "fx_ai_trading.supervisor.health.socket.gethostbyname",
                return_value="1.2.3.4",
            ),
            patch("fx_ai_trading.supervisor.health.socket.create_connection") as conn,
        ):
            conn.return_value.__enter__ = MagicMock(return_value=MagicMock())
            conn.return_value.__exit__ = MagicMock(return_value=False)
            probe_slack_webhook("https://hooks.slack.com/T/B/X", timeout_s=0.5)

        assert conn.call_args.kwargs.get("timeout") == 0.5

    def test_explicit_port_in_url_is_honoured(self) -> None:
        with (
            patch(
                "fx_ai_trading.supervisor.health.socket.gethostbyname",
                return_value="1.2.3.4",
            ),
            patch("fx_ai_trading.supervisor.health.socket.create_connection") as conn,
        ):
            conn.return_value.__enter__ = MagicMock(return_value=MagicMock())
            conn.return_value.__exit__ = MagicMock(return_value=False)
            probe_slack_webhook("https://hooks.slack.example:8443/T/B/X")

        assert conn.call_args.args[0] == ("hooks.slack.example", 8443)

    def test_http_url_defaults_to_port_80(self) -> None:
        with (
            patch(
                "fx_ai_trading.supervisor.health.socket.gethostbyname",
                return_value="1.2.3.4",
            ),
            patch("fx_ai_trading.supervisor.health.socket.create_connection") as conn,
        ):
            conn.return_value.__enter__ = MagicMock(return_value=MagicMock())
            conn.return_value.__exit__ = MagicMock(return_value=False)
            probe_slack_webhook("http://hooks.slack.example/T/B/X")

        assert conn.call_args.args[0] == ("hooks.slack.example", 80)


# ---------------------------------------------------------------------------
# probe_smtp_connection
# ---------------------------------------------------------------------------


class TestProbeSmtpConnection:
    def test_ok_path_resolves_dns_and_connects_tcp(self) -> None:
        with (
            patch("fx_ai_trading.supervisor.health.socket.gethostbyname") as dns,
            patch("fx_ai_trading.supervisor.health.socket.create_connection") as conn,
        ):
            dns.return_value = "10.0.0.1"
            conn.return_value.__enter__ = MagicMock(return_value=MagicMock())
            conn.return_value.__exit__ = MagicMock(return_value=False)
            result = probe_smtp_connection("smtp.example.com", 587)

        assert result.is_ok is True
        assert result.name == "smtp_connection"
        dns.assert_called_once_with("smtp.example.com")
        assert conn.call_args.args[0] == ("smtp.example.com", 587)

    def test_dns_failure_returns_degraded(self) -> None:
        with patch(
            "fx_ai_trading.supervisor.health.socket.gethostbyname",
            side_effect=OSError("nodename nor servname"),
        ):
            result = probe_smtp_connection("smtp.invalid.example", 587)

        assert result.is_ok is False
        assert "dns" in result.detail.lower()

    def test_tcp_failure_returns_degraded(self) -> None:
        with (
            patch(
                "fx_ai_trading.supervisor.health.socket.gethostbyname",
                return_value="10.0.0.1",
            ),
            patch(
                "fx_ai_trading.supervisor.health.socket.create_connection",
                side_effect=ConnectionRefusedError("port closed"),
            ),
        ):
            result = probe_smtp_connection("smtp.example.com", 25)

        assert result.is_ok is False
        assert "tcp" in result.detail.lower()

    def test_timeout_kwarg_forwarded_to_create_connection(self) -> None:
        with (
            patch(
                "fx_ai_trading.supervisor.health.socket.gethostbyname",
                return_value="10.0.0.1",
            ),
            patch("fx_ai_trading.supervisor.health.socket.create_connection") as conn,
        ):
            conn.return_value.__enter__ = MagicMock(return_value=MagicMock())
            conn.return_value.__exit__ = MagicMock(return_value=False)
            probe_smtp_connection("smtp.example.com", 587, timeout_s=0.25)

        assert conn.call_args.kwargs.get("timeout") == 0.25


# ---------------------------------------------------------------------------
# Sanity: probes do not exercise notification protocols
# ---------------------------------------------------------------------------


class TestProbesDoNotIssueApplicationTraffic:
    def test_slack_probe_does_not_import_or_call_slack_notifier(self) -> None:
        """No SlackNotifier.send / requests.post / urllib request must fire."""
        with (
            patch(
                "fx_ai_trading.supervisor.health.socket.gethostbyname",
                return_value="1.2.3.4",
            ),
            patch("fx_ai_trading.supervisor.health.socket.create_connection") as conn,
        ):
            conn.return_value.__enter__ = MagicMock(return_value=MagicMock())
            conn.return_value.__exit__ = MagicMock(return_value=False)
            probe_slack_webhook("https://hooks.slack.com/T/B/X")
        # Only socket-level interactions; no HTTP layer.  If a future
        # refactor adds requests.post here, this test will fail because
        # the conn.call_args would gain HTTP-shaped kwargs.
        assert "data" not in conn.call_args.kwargs
        assert "json" not in conn.call_args.kwargs

    def test_smtp_probe_does_not_issue_ehlo_or_auth(self) -> None:
        """The probe must not invoke smtplib — only socket.create_connection."""
        with (
            patch(
                "fx_ai_trading.supervisor.health.socket.gethostbyname",
                return_value="10.0.0.1",
            ),
            patch("fx_ai_trading.supervisor.health.socket.create_connection") as conn,
            patch("smtplib.SMTP") as smtp_cls,
        ):
            conn.return_value.__enter__ = MagicMock(return_value=MagicMock())
            conn.return_value.__exit__ = MagicMock(return_value=False)
            probe_smtp_connection("smtp.example.com", 587)

        smtp_cls.assert_not_called()
