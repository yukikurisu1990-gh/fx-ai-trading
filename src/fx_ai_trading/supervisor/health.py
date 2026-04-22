"""HealthChecker — periodic component health checks (D4 §6.4 / M7).

Supervisor calls check() every 10 seconds to detect component failures.
In M7, the implemented checks are:
  - DB connectivity (SELECT 1, 2s timeout)

Checks deferred to later milestones:
  - Broker.get_positions() liveness (M8)
  - PriceFeed / Transaction stream heartbeat age (M9)
  - OutboxProcessor last_processed_at (M8)
  - FileNotifier write heartbeat (M12)

Notifier reachability probes (G-3 PR-4 / docs/design/g3_notifier_fix_plan.md §3.4)
────────────────────────────────────────────────────────────────────────────────
``probe_slack_webhook`` and ``probe_smtp_connection`` are connectivity-only
startup probes invoked by ``StartupRunner._step15_health_check``.  They
surface external-notifier misconfigurations (DNS unresolved, blocked TCP
port) at startup so operators can correlate config issues with a single
``degraded`` outcome before the first ``safe_stop`` fire, rather than
discovering the breakage mid-incident.

The probes MUST NOT:
  - send any application traffic (no HTTP POST to the Slack webhook,
    no SMTP EHLO / AUTH / MAIL to the SMTP host),
  - activate the Email channel (PR-1 hard guard stays intact; the
    dispatcher's ``email_notifier`` field is untouched), or
  - change ``DispatchResult`` semantics (PR-3 contract).
They ONLY perform DNS resolution + TCP connect bounded by a per-probe
timeout (default 2s).  Probe failures flip the startup outcome to
``degraded`` — they never raise ``StartupError``.

Timestamp from injected Clock (no datetime.now() / time.time() here).
"""

from __future__ import annotations

import logging
import socket
import urllib.parse
from dataclasses import dataclass

from sqlalchemy import Engine, text

from fx_ai_trading.common.clock import Clock

_log = logging.getLogger(__name__)


@dataclass(frozen=True)
class CheckResult:
    """Result of a single health sub-check."""

    name: str
    is_ok: bool
    detail: str = ""


@dataclass(frozen=True)
class HealthStatus:
    """Aggregated health status returned by HealthChecker.check().

    is_ok is True iff all individual checks passed.
    """

    is_ok: bool
    checks: tuple[CheckResult, ...]
    checked_at: object  # datetime — kept as object to avoid import cycle

    @classmethod
    def from_checks(
        cls,
        checks: list[CheckResult],
        checked_at: object,
    ) -> HealthStatus:
        """Construct from a mutable list of CheckResult."""
        return cls(
            is_ok=all(c.is_ok for c in checks),
            checks=tuple(checks),
            checked_at=checked_at,
        )


class HealthChecker:
    """Runs the set of component health checks defined for M7.

    Args:
        clock: Used to timestamp the HealthStatus result.
        db_timeout_s: Maximum seconds for the DB SELECT 1 before marking
            the check failed.
    """

    _DB_CHECK_NAME = "db_connection"

    def __init__(self, clock: Clock, db_timeout_s: float = 2.0) -> None:
        self._clock = clock
        self._db_timeout_s = db_timeout_s

    def check(self, engine: Engine | None = None) -> HealthStatus:
        """Run all health checks and return aggregated HealthStatus.

        Args:
            engine: SQLAlchemy Engine for the DB check.  If None, the DB
                check is skipped (reported as ok with a note).

        Returns:
            HealthStatus with is_ok=True iff every check passed.
        """
        checked_at = self._clock.now()
        results: list[CheckResult] = []

        results.append(self._check_db(engine))

        status = HealthStatus.from_checks(results, checked_at=checked_at)
        if not status.is_ok:
            failed = [c.name for c in status.checks if not c.is_ok]
            _log.warning("HealthChecker: failed checks: %s", failed)
        return status

    # ------------------------------------------------------------------
    # Individual checks
    # ------------------------------------------------------------------

    def _check_db(self, engine: Engine | None) -> CheckResult:
        if engine is None:
            return CheckResult(
                name=self._DB_CHECK_NAME,
                is_ok=True,
                detail="skipped (no engine)",
            )
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return CheckResult(name=self._DB_CHECK_NAME, is_ok=True)
        except Exception as exc:  # noqa: BLE001
            return CheckResult(
                name=self._DB_CHECK_NAME,
                is_ok=False,
                detail=str(exc),
            )


# ---------------------------------------------------------------------------
# External-notifier reachability probes (G-3 PR-4 / memo §3.4)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class NotifierProbeResult:
    """Result of a single external-notifier reachability probe.

    Probes are connectivity-only (DNS + TCP connect) — they never
    exercise the notifier's application protocol, so an OK result here
    does NOT guarantee that a real send will succeed; it only rules out
    the most common "unreachable" failure modes.  A ``False`` result
    means the ``StartupRunner`` will mark the run ``degraded``; the
    operator is expected to correlate the detail field with the
    misconfigured channel.
    """

    name: str
    is_ok: bool
    detail: str = ""


def _probe_dns_and_tcp(name: str, host: str, port: int, timeout_s: float) -> NotifierProbeResult:
    """DNS-resolve ``host`` then TCP-connect to ``(host, port)`` under ``timeout_s``.

    Shared helper for ``probe_slack_webhook`` and ``probe_smtp_connection``.
    Never raises — every error path returns a ``NotifierProbeResult`` with
    ``is_ok=False``.  ``socket.timeout`` subclasses ``OSError`` so the
    ``OSError`` catch covers both DNS and TCP timeouts.
    """
    try:
        socket.gethostbyname(host)
    except OSError as exc:
        return NotifierProbeResult(name=name, is_ok=False, detail=f"dns: {exc}")
    try:
        with socket.create_connection((host, port), timeout=timeout_s):
            pass
    except OSError as exc:
        return NotifierProbeResult(name=name, is_ok=False, detail=f"tcp: {exc}")
    return NotifierProbeResult(name=name, is_ok=True, detail=f"{host}:{port} reachable")


def probe_slack_webhook(url: str, *, timeout_s: float = 2.0) -> NotifierProbeResult:
    """Probe a Slack webhook URL for DNS + TCP reachability.

    Parses the webhook URL for host/port only; no HTTP request is issued
    (the Slack webhook has no neutral GET endpoint and a POST would
    constitute an actual notification, which the PR-4 rules forbid).
    Returns ``NotifierProbeResult(is_ok=False)`` for malformed URLs,
    DNS failures, or TCP failures within ``timeout_s``.
    """
    name = "slack_webhook"
    parsed = urllib.parse.urlsplit(url)
    host = parsed.hostname
    if not host:
        return NotifierProbeResult(name=name, is_ok=False, detail="invalid url (no host)")
    port = parsed.port
    if port is None:
        port = 443 if parsed.scheme == "https" else 80
    return _probe_dns_and_tcp(name, host, port, timeout_s)


def probe_smtp_connection(host: str, port: int, *, timeout_s: float = 2.0) -> NotifierProbeResult:
    """Probe an SMTP host:port for DNS + TCP reachability.

    No EHLO / STARTTLS / AUTH / MAIL is issued — this is strictly a
    TCP reachability check.  The PR-1 Email-disabled hard guard is
    preserved: the dispatcher's ``email_notifier`` remains ``None``
    regardless of probe outcome.
    """
    return _probe_dns_and_tcp("smtp_connection", host, port, timeout_s)
