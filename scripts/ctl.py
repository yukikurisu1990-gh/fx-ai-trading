#!/usr/bin/env python
"""ctl -- control CLI for FX-AI Trading system (M22 / Mi-CTL-1).

Commands:
  start                          Start Supervisor subprocess (records PID)
  stop                           Stop Supervisor gracefully (SIGTERM → SIGKILL)
  resume-from-safe-stop          Resume from safe_stop state (requires --reason)
  run-reconciler                 Trigger manual reconciliation
  emergency-flat-all             Flatten all positions (2-factor required)

Usage:
    python scripts/ctl.py start [--confirm-live-trading]
    python scripts/ctl.py stop
    python scripts/ctl.py resume-from-safe-stop --reason="..."
    python scripts/ctl.py run-reconciler
    python scripts/ctl.py emergency-flat-all
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

import click

# Ensure the src layout is importable when running as a script.
_repo_root = Path(__file__).resolve().parents[1]
_src_root = _repo_root / "src"
if str(_src_root) not in sys.path:
    sys.path.insert(0, str(_src_root))

from fx_ai_trading.adapters.notifier.file import FileNotifier  # noqa: E402
from fx_ai_trading.common.clock import Clock, WallClock  # noqa: E402
from fx_ai_trading.domain.notifier import NotifyEvent  # noqa: E402
from fx_ai_trading.ops.process_manager import ProcessManager  # noqa: E402
from fx_ai_trading.ops.two_factor import ConsoleTwoFactor, TwoFactorAuthenticator  # noqa: E402
from fx_ai_trading.supervisor.safe_stop_journal import SafeStopJournal  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [ctl] %(message)s",
)
_log = logging.getLogger(__name__)

_LOGS_DIR = _repo_root / "logs"
_PID_FILE = _LOGS_DIR / "supervisor.pid"

# ---------------------------------------------------------------------------
# Helpers — testable internal functions
# ---------------------------------------------------------------------------


def _ensure_logs_dir() -> None:
    _LOGS_DIR.mkdir(parents=True, exist_ok=True)


def _do_emergency_flat(
    two_factor: TwoFactorAuthenticator,
    notifier: FileNotifier | None = None,
    clock: Clock | None = None,
    journal: SafeStopJournal | None = None,
    process_manager: ProcessManager | None = None,
) -> bool:
    """Execute emergency flat with 2-factor confirmation.

    Returns True if the operation was authorised and executed.
    Returns False if the 2-factor challenge was rejected.

    PR-α (U-9): once 2-factor is confirmed and the FileNotifier event has
    been written, this function additionally
      1. appends an ``emergency_flat_initiated`` entry to ``SafeStopJournal``
         (durable, append-only — survives DB failure), and
      2. requests Supervisor stop via ``ProcessManager.stop()`` so that the
         existing in-Supervisor signal handler fires
         ``trigger_safe_stop`` and produces the canonical
         ``safe_stop.triggered`` journal entry.
    Supervisor-未起動時 (PID file 不在 / 死プロセス) は journal append のみ
    実行し stop は no-op (fail-safe; cross-process magic は導入しない).
    """
    click.echo("=" * 60)
    click.echo("EMERGENCY FLAT ALL — 2-factor confirmation required")
    click.echo("=" * 60)

    if not two_factor.run_challenge():
        _log.warning("emergency-flat-all: 2-factor confirmation REJECTED — aborted")
        click.echo("Operation aborted: confirmation failed.")
        return False

    _log.critical("emergency-flat-all: 2-factor CONFIRMED — executing emergency flat")

    _ensure_logs_dir()
    _clock: Clock = clock or WallClock()
    occurred_at = _clock.now()

    event = NotifyEvent(
        event_code="EMERGENCY_FLAT_ALL",
        severity="critical",
        payload={"initiator": "ctl", "pid": os.getpid()},
        occurred_at=occurred_at,
    )

    _notifier = notifier or FileNotifier(log_path=_LOGS_DIR / "notifications.jsonl")
    _notifier.send(event, severity="critical", payload=event.payload)

    # PR-α (U-9): wire emergency-flat-all to the SafeStop sequence.
    # Step 1: durable journal append (independent of Supervisor liveness).
    _journal = journal or SafeStopJournal(journal_path=_LOGS_DIR / "safe_stop.jsonl")
    _journal.append(
        {
            "event_code": "emergency_flat_initiated",
            "occurred_at": occurred_at.isoformat(),
            "initiator": "ctl emergency-flat-all",
            "pid": os.getpid(),
        }
    )

    # Step 2: request Supervisor stop only when one is actually running.
    # is_running() == False covers both "PID file missing" and "stale PID";
    # in either case stop is a no-op (fail-safe).
    _pm = process_manager or ProcessManager(pid_file=_PID_FILE)
    if _pm.is_running():
        stopped = _pm.stop()
        if stopped:
            click.echo(
                "Supervisor stop requested. safe_stop sequence delegated to its signal handler."
            )
        else:
            click.echo("Supervisor stop requested but process was not running.")
    else:
        _log.info("emergency-flat-all: Supervisor not running — journal recorded, stop is no-op")
        click.echo("Supervisor not running — journal entry recorded; stop skipped (fail-safe).")

    click.echo("Emergency flat request recorded. Notifier critical event sent.")
    click.echo("Ensure the Supervisor or broker layer processes the flat order.")
    return True


def _do_resume(
    reason: str,
    journal: SafeStopJournal | None = None,
    clock: Clock | None = None,
) -> None:
    """Record a safe_stop resume event to the journal."""
    _ensure_logs_dir()
    _clock: Clock = clock or WallClock()
    entry = {
        "event_code": "SAFE_STOP_RESUME",
        "reason": reason,
        "occurred_at": _clock.now().isoformat(),
        "initiator": "ctl resume-from-safe-stop",
    }
    _journal = journal or SafeStopJournal(journal_path=_LOGS_DIR / "safe_stop.jsonl")
    _journal.append(entry)
    _log.info("resume-from-safe-stop: reason=%s", reason)
    click.echo(json.dumps(entry, ensure_ascii=False))


# ---------------------------------------------------------------------------
# CLI commands
# ---------------------------------------------------------------------------


@click.group()
def cli() -> None:
    """FX-AI Trading control CLI."""


@cli.command()
@click.option(
    "--confirm-live-trading",
    is_flag=True,
    default=False,
    help="Pass this flag when starting with a live OANDA account.",
)
def start(confirm_live_trading: bool) -> None:
    """Start Supervisor subprocess (records PID in logs/supervisor.pid)."""
    _ensure_logs_dir()
    pm = ProcessManager(pid_file=_PID_FILE)
    try:
        pid = pm.start()
    except RuntimeError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    click.echo(f"Supervisor started (PID {pid}).")
    if confirm_live_trading:
        _log.info("ctl start --confirm-live-trading: operator_confirmed=True")
        click.echo("Live trading confirmation flag set.")


@cli.command()
def stop() -> None:
    """Stop Supervisor gracefully (SIGTERM → SIGKILL)."""
    pm = ProcessManager(pid_file=_PID_FILE)
    stopped = pm.stop()
    if stopped:
        click.echo("Supervisor stopped.")
    else:
        click.echo("No running Supervisor found.", err=True)
        sys.exit(1)


@cli.command("resume-from-safe-stop")
@click.option("--reason", required=True, help="Reason for resuming (audit log entry).")
def resume_from_safe_stop(reason: str) -> None:
    """Resume from safe_stop state. Records reason in safe_stop.jsonl."""
    _do_resume(reason)
    click.echo("Safe-stop resume recorded.")


@cli.command("run-reconciler")
def run_reconciler() -> None:
    """Trigger manual reconciliation (logs intent; real wiring in M15)."""
    _log.info("ctl run-reconciler: manual reconciliation requested")
    click.echo("Manual reconciliation triggered. Check logs for progress.")


@cli.command("emergency-flat-all")
def emergency_flat_all() -> None:
    """Flatten all positions — 2-factor confirmation required."""
    success = _do_emergency_flat(ConsoleTwoFactor())
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    cli()
