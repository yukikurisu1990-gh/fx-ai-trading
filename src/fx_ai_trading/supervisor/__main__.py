"""Production entry point for the Supervisor process (G-3 PR-1).

Invoked by ``ProcessManager.start()`` as
``python -m fx_ai_trading.supervisor`` (see
``src/fx_ai_trading/ops/process_manager.py:57``).  Before this file
existed the spawn target ``fx_ai_trading.supervisor`` had no
``__main__`` and the subprocess would fail with ``ModuleNotFoundError``,
leaving production with no working Supervisor at all (G-3 audit R-1).

What this entry point does (PR-1, file-only safe)
─────────────────────────────────────────────────
1. Build ``WallClock``, ``FileNotifier`` and ``SafeStopJournal`` against
   their default ``logs/...`` paths (parent dir is created here).
2. Build the production ``NotifierDispatcherImpl`` via
   ``notifier_factory.build_notifier_dispatcher`` so that ``safe_stop``
   step 3 has a real fan-out target instead of the previous dead-code
   path.  Slack is wired only when ``SLACK_WEBHOOK_URL`` is present in
   the environment; Email is never wired in PR-1 (factory guard).
3. Build a ``StartupContext`` that supplies the dispatcher as
   ``ctx.notifier`` and leaves DB / broker / config provider as ``None``
   so degraded / stub steps short-circuit (per ``startup.py`` early-skip
   branches).  This is the minimum context required for the 16-step
   sequence to run without an external DB.
4. Run ``Supervisor.startup(ctx)``.  The process exits 0 when startup
   reaches "ready" or "degraded"; non-zero on ``StartupError``.

Out of scope for PR-1 (deferred per docs/design/g3_notifier_fix_plan.md §4)
─────────────────────────────────────────────────────────────────────────
- Email channel activation                    (PR-2)
- Email timeout / retry budget                (PR-2)
- ``DispatchResult`` introduction             (PR-3)
- Notifier health probe in startup step 15    (PR-4)
- Trading-loop / metrics-loop bootstrap       (M9 / M16)

The file-only fallback (P-2) is the intended steady state of this
entry point until PR-2 ~ PR-4 land.

PR-4 wiring (additive)
──────────────────────
The notifier health probes added to ``StartupRunner._step15_health_check``
read three optional env vars here and pass them to ``StartupContext``:

  ``SLACK_WEBHOOK_URL``  — Slack DNS+TCP probe (and the existing
                            SlackNotifier wiring; unchanged).
  ``SMTP_HOST``          — SMTP TCP probe host.
  ``SMTP_PORT``          — SMTP TCP probe port (int; ignored if non-numeric).

The probes are connectivity-only — they do NOT activate the Email
channel or change ``notifier_factory`` behaviour.  Absent env vars
silently skip the corresponding probe (no degraded mark).
"""

from __future__ import annotations

import logging
import os
import signal
import sys
import threading
from pathlib import Path

from fx_ai_trading.adapters.notifier.file import FileNotifier
from fx_ai_trading.common.clock import WallClock
from fx_ai_trading.supervisor.notifier_factory import build_notifier_dispatcher
from fx_ai_trading.supervisor.safe_stop_journal import SafeStopJournal
from fx_ai_trading.supervisor.startup import StartupContext, StartupError
from fx_ai_trading.supervisor.supervisor import Supervisor

_LOGS_DIR = Path("logs")
_NOTIFICATIONS_PATH = _LOGS_DIR / "notifications.jsonl"
_JOURNAL_PATH = _LOGS_DIR / "safe_stop.jsonl"

_SLACK_ENV_VAR = "SLACK_WEBHOOK_URL"
_SMTP_HOST_ENV_VAR = "SMTP_HOST"
_SMTP_PORT_ENV_VAR = "SMTP_PORT"


def _read_smtp_port_from_env() -> int | None:
    """Parse ``SMTP_PORT`` env var into an int; return None on absence/garbage.

    A non-numeric value silently disables the SMTP probe (logged at
    WARNING) rather than crashing startup — the probe is best-effort
    config validation, not a hard precondition.
    """
    raw = os.environ.get(_SMTP_PORT_ENV_VAR, "").strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        logging.getLogger(__name__).warning(
            "Supervisor entry point: %s=%r is not an integer — SMTP probe disabled",
            _SMTP_PORT_ENV_VAR,
            raw,
        )
        return None


def _build_supervisor_context() -> tuple[Supervisor, StartupContext]:
    """Construct the Supervisor + StartupContext used by ``main()``.

    Split out so tests can introspect the wiring (dispatcher identity,
    file-only externals, ``email_notifier=None``) without invoking the
    full startup sequence as a subprocess.
    """
    _LOGS_DIR.mkdir(parents=True, exist_ok=True)

    clock = WallClock()
    file_notifier = FileNotifier(log_path=_NOTIFICATIONS_PATH)
    journal = SafeStopJournal(journal_path=_JOURNAL_PATH)

    slack_url = os.environ.get(_SLACK_ENV_VAR, "").strip() or None
    dispatcher = build_notifier_dispatcher(
        file_notifier=file_notifier,
        slack_webhook_url=slack_url,
    )

    smtp_host = os.environ.get(_SMTP_HOST_ENV_VAR, "").strip() or None
    smtp_port = _read_smtp_port_from_env()

    supervisor = Supervisor(clock=clock)
    ctx = StartupContext(
        journal=journal,
        notifier=dispatcher,
        clock=clock,
        # PR-4: feed the probe-only fields.  Email is NOT activated
        # — these only drive the connectivity probe in step 15.
        slack_webhook_url=slack_url,
        smtp_host=smtp_host,
        smtp_port=smtp_port,
    )
    return supervisor, ctx


def _install_signal_driven_safe_stop(
    supervisor: Supervisor,
    ctx: StartupContext,
    log: logging.Logger,
) -> tuple[threading.Event, list[int]]:
    """Install SIGTERM/SIGINT handlers that signal the main thread to fire safe_stop.

    Returns the stop ``Event`` (set by handlers) and the list of signal
    numbers received (mutated by handlers).  The handler intentionally
    does only flag-setting work — ``trigger_safe_stop`` is invoked from
    the main thread after ``Event.wait()`` returns so the I/O-heavy
    SafeStopHandler 4-step sequence does not run inside a signal frame.
    """
    stop_event = threading.Event()
    received: list[int] = []

    def _handler(signum: int, _frame: object) -> None:
        received.append(signum)
        log.info("Supervisor: received signal %d — initiating safe_stop", signum)
        stop_event.set()

    # SIGTERM is the ProcessManager.stop() target on Unix.  SIGINT covers
    # interactive Ctrl+C.  Both are catchable on Unix and on Windows
    # signal.signal(SIGINT) is honored by the C runtime; SIGTERM on
    # Windows is not delivered by TerminateProcess (handled separately
    # in PR-B via CTRL_BREAK_EVENT + CREATE_NEW_PROCESS_GROUP).
    signal.signal(signal.SIGTERM, _handler)
    signal.signal(signal.SIGINT, _handler)
    return stop_event, received


def main() -> int:
    """Run the Supervisor startup sequence and return the process exit code."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [supervisor] %(message)s",
    )
    log = logging.getLogger(__name__)

    supervisor, ctx = _build_supervisor_context()
    log.info("Supervisor entry point: starting (file-only safe wiring per G-3 PR-1)")

    try:
        result = supervisor.startup(ctx)
    except StartupError as exc:
        log.error("Supervisor startup failed: %s", exc)
        return 1

    log.info(
        "Supervisor startup complete: outcome=%s degraded_steps=%s",
        result.outcome,
        result.degraded_steps,
    )

    stop_event, _received = _install_signal_driven_safe_stop(supervisor, ctx, log)
    log.info("Supervisor: awaiting stop signal (SIGTERM/SIGINT)")
    stop_event.wait()

    log.info("Supervisor: signal received — firing SafeStopHandler 4-step sequence")
    try:
        supervisor.trigger_safe_stop(
            reason="signal_received",
            occurred_at=ctx.clock.now(),
        )
    except Exception:
        log.exception("Supervisor: trigger_safe_stop raised — exiting non-zero")
        return 2

    log.info("Supervisor: safe_stop complete — exiting 0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
