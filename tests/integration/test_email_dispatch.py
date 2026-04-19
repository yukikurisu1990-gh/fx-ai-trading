"""Integration test: EmailNotifier end-to-end dispatch (M17).

Uses a threading-based fake SMTP server implemented in pure Python stdlib
(socketserver.StreamRequestHandler) — no external service or deprecated
smtpd module required.  Compatible with Python 3.12+.

The fake server implements the minimal SMTP protocol subset needed to
accept a single message: EHLO → MAIL FROM → RCPT TO → DATA → QUIT.
STARTTLS is not exercised here (tested via unit/contract layer);
the integration tests use use_starttls=False to avoid SSL setup.
"""

from __future__ import annotations

import socket
import socketserver
import threading
from datetime import UTC, datetime

import pytest

from fx_ai_trading.adapters.notifier.email import EmailNotifier
from fx_ai_trading.domain.notifier import NotifyEvent

_FIXED_AT = datetime(2026, 1, 1, tzinfo=UTC)

_CRITICAL_EVENT = NotifyEvent(
    event_code="safe_stop.triggered",
    severity="critical",
    payload={"reason": "integration-test"},
    occurred_at=_FIXED_AT,
)


# ---------------------------------------------------------------------------
# Minimal fake SMTP server
# ---------------------------------------------------------------------------


class _SMTPHandler(socketserver.StreamRequestHandler):
    """Handle a single SMTP session and record the received message."""

    def handle(self) -> None:
        server: _FakeSMTPServer = self.server  # type: ignore[assignment]
        wfile = self.wfile

        def send(line: str) -> None:
            wfile.write((line + "\r\n").encode())
            wfile.flush()

        send("220 fake-smtp ESMTP")
        while True:
            raw = self.rfile.readline()
            if not raw:
                break
            line = raw.decode(errors="replace").strip()
            upper = line.upper()
            if upper.startswith("EHLO") or upper.startswith("HELO"):
                send("250-fake-smtp")
                send("250 OK")
            elif upper.startswith("MAIL FROM"):
                server._mail_from = line.split(":", 1)[1].strip().strip("<>")
                send("250 OK")
            elif upper.startswith("RCPT TO"):
                rcpt = line.split(":", 1)[1].strip().strip("<>")
                server._rcpt_to.append(rcpt)
                send("250 OK")
            elif upper == "DATA":
                send("354 Start mail input")
                data_lines: list[str] = []
                while True:
                    data_raw = self.rfile.readline()
                    data_line = data_raw.decode(errors="replace")
                    if data_line.strip() == ".":
                        break
                    data_lines.append(data_line)
                server.received.append(
                    {
                        "from": server._mail_from,
                        "to": list(server._rcpt_to),
                        "data": "".join(data_lines),
                    }
                )
                server._mail_from = ""
                server._rcpt_to = []
                send("250 OK")
            elif upper.startswith("QUIT"):
                send("221 Bye")
                break
            elif upper.startswith("AUTH"):
                send("235 Authentication successful")
            else:
                send("250 OK")


class _FakeSMTPServer(socketserver.TCPServer):
    allow_reuse_address = True

    def __init__(self, server_address: tuple[str, int]) -> None:
        super().__init__(server_address, _SMTPHandler)
        self.received: list[dict] = []
        self._mail_from: str = ""
        self._rcpt_to: list[str] = []


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture()
def fake_smtp():
    """Start fake SMTP server in background thread; yield (host, port, server)."""
    port = _free_port()
    server = _FakeSMTPServer(("127.0.0.1", port))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield "127.0.0.1", port, server
    server.shutdown()
    thread.join(timeout=2)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestEmailDispatchIntegration:
    def test_message_delivered_to_fake_smtp(self, fake_smtp) -> None:
        host, port, server = fake_smtp
        notifier = EmailNotifier(
            host=host,
            port=port,
            sender="alert@example.com",
            recipients=["ops@example.com"],
            username=None,
            password=None,
            use_starttls=False,
        )
        result = notifier.send(_CRITICAL_EVENT, "critical", {"reason": "integration-test"})
        assert result.success is True
        assert len(server.received) == 1
        msg = server.received[0]
        assert msg["from"] == "alert@example.com"
        assert "ops@example.com" in msg["to"]

    def test_event_code_in_message_body(self, fake_smtp) -> None:
        host, port, server = fake_smtp
        notifier = EmailNotifier(
            host=host,
            port=port,
            sender="alert@example.com",
            recipients=["ops@example.com"],
            use_starttls=False,
        )
        notifier.send(_CRITICAL_EVENT, "critical", {})
        assert server.received
        assert "safe_stop.triggered" in server.received[0]["data"]

    def test_subject_contains_severity_and_event_code(self, fake_smtp) -> None:
        host, port, server = fake_smtp
        notifier = EmailNotifier(
            host=host,
            port=port,
            sender="alert@example.com",
            recipients=["ops@example.com"],
            use_starttls=False,
        )
        notifier.send(_CRITICAL_EVENT, "critical", {})
        raw = server.received[0]["data"]
        assert "CRITICAL" in raw
        assert "safe_stop.triggered" in raw

    def test_failure_on_wrong_port_returns_failure_not_raises(self) -> None:
        notifier = EmailNotifier(
            host="127.0.0.1",
            port=1,
            sender="a@b.com",
            recipients=["c@d.com"],
            use_starttls=False,
        )
        result = notifier.send(_CRITICAL_EVENT, "critical", {})
        assert result.success is False
        assert result.notifier_name == "email"

    def test_multiple_recipients_all_delivered(self, fake_smtp) -> None:
        host, port, server = fake_smtp
        notifier = EmailNotifier(
            host=host,
            port=port,
            sender="alert@example.com",
            recipients=["ops@example.com", "oncall@example.com"],
            use_starttls=False,
        )
        notifier.send(_CRITICAL_EVENT, "critical", {})
        msg = server.received[0]
        assert "ops@example.com" in msg["to"]
        assert "oncall@example.com" in msg["to"]
