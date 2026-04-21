"""Supervisor process entry point — `python -m fx_ai_trading.supervisor` (G-0 / G-1).

Builds the minimum dependency graph for SafeStopHandler.fire(), runs
StartupRunner, then blocks until a stop signal arrives.  On signal, calls
Supervisor.trigger_safe_stop() so the four-step contract executes:

    1. SafeStopJournal.append      → logs/safe_stop.jsonl
    2. stop_callback                → trading_allowed=False
    3. NotifierDispatcher.dispatch  → logs/notifications.jsonl (+ externals)
    4. supervisor_events INSERT     → DB (skipped when DATABASE_URL absent)

Signal handling (cross-platform):
  - Unix: SIGTERM (psutil.terminate) and SIGINT.
  - Windows: SIGBREAK (CTRL_BREAK_EVENT, see ProcessManager.stop) and SIGINT.
    Note: on Windows, psutil.Process.terminate() maps to TerminateProcess()
    which is uncatchable; ProcessManager therefore sends CTRL_BREAK_EVENT
    instead, which this module catches via SIGBREAK.
"""

from __future__ import annotations

import logging
import os
import signal
import sys
import threading
import time
import uuid
from pathlib import Path
from types import FrameType
from typing import TYPE_CHECKING

from fx_ai_trading.adapters.notifier.dispatcher import NotifierDispatcherImpl
from fx_ai_trading.adapters.notifier.file import FileNotifier
from fx_ai_trading.common.clock import WallClock
from fx_ai_trading.config.common_keys_context import CommonKeysContext
from fx_ai_trading.repositories.supervisor_events import SupervisorEventsRepository
from fx_ai_trading.supervisor.safe_stop_journal import SafeStopJournal
from fx_ai_trading.supervisor.startup import StartupContext, StartupError
from fx_ai_trading.supervisor.supervisor import Supervisor

if TYPE_CHECKING:
    from sqlalchemy import Engine

_log = logging.getLogger("fx_ai_trading.supervisor")
_LOGS_DIR = Path("logs")

_shutdown_event = threading.Event()


def _build_engine_or_none() -> Engine | None:
    """Best-effort DB engine build; returns None when DATABASE_URL is unset.

    Live operation requires DATABASE_URL.  Local smoke runs may omit it,
    in which case step 4 (supervisor_events INSERT) is skipped — steps
    1–3 still execute so the safe_stop contract is observably partial
    rather than silently absent.
    """
    db_url = os.environ.get("DATABASE_URL", "").strip()
    if not db_url:
        _log.warning("DATABASE_URL not set — supervisor_events DB write (step 4) will be skipped")
        return None
    from fx_ai_trading.adapters.persistence.postgres import PostgreSQLAdapter

    return PostgreSQLAdapter(url=db_url).engine


def _build_common_keys_ctx() -> CommonKeysContext:
    return CommonKeysContext(
        run_id=str(uuid.uuid4()),
        environment=os.environ.get("FX_AI_ENVIRONMENT", "paper"),
        code_version=os.environ.get("FX_AI_CODE_VERSION", "unknown"),
        config_version=os.environ.get("FX_AI_CONFIG_VERSION", "unknown"),
    )


def _make_signal_handler(supervisor: Supervisor, clock: WallClock):
    def _handler(signum: int, _frame: FrameType | None) -> None:
        signame = signal.Signals(signum).name
        _log.critical(
            "Supervisor received %s (signum=%d) — triggering safe_stop",
            signame,
            signum,
        )
        try:
            supervisor.trigger_safe_stop(
                reason=f"ctl_stop_requested:{signame.lower()}",
                occurred_at=clock.now(),
                payload={"signal": signame, "pid": os.getpid()},
            )
        except Exception:  # noqa: BLE001
            _log.exception("Supervisor.trigger_safe_stop raised")
        finally:
            _shutdown_event.set()

    return _handler


def _install_signal_handlers(handler) -> None:
    """Register handler for SIGTERM/SIGBREAK + SIGINT on the running platform."""
    if sys.platform == "win32":
        # SIGTERM cannot be reliably caught on Windows; CTRL_BREAK_EVENT → SIGBREAK is.
        signal.signal(signal.SIGINT, handler)
        signal.signal(signal.SIGBREAK, handler)  # type: ignore[attr-defined]
    else:
        signal.signal(signal.SIGTERM, handler)
        signal.signal(signal.SIGINT, handler)


def main() -> int:
    """Entry point invoked by `python -m fx_ai_trading.supervisor`."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [supervisor] %(name)s: %(message)s",
    )
    _LOGS_DIR.mkdir(parents=True, exist_ok=True)

    clock = WallClock()
    journal = SafeStopJournal(journal_path=_LOGS_DIR / "safe_stop.jsonl")
    file_notifier = FileNotifier(log_path=_LOGS_DIR / "notifications.jsonl")
    dispatcher = NotifierDispatcherImpl(file_notifier=file_notifier)

    engine = _build_engine_or_none()
    repo = SupervisorEventsRepository(engine) if engine is not None else None
    common_keys_ctx = _build_common_keys_ctx() if engine is not None else None

    supervisor = Supervisor(clock=clock)
    ctx = StartupContext(
        journal=journal,
        notifier=dispatcher,
        clock=clock,
        engine=engine,
        supervisor_events_repo=repo,
        common_keys_ctx=common_keys_ctx,
    )

    try:
        result = supervisor.startup(ctx)
    except StartupError as exc:
        _log.critical("Supervisor startup failed: %s", exc)
        return 2

    _log.info(
        "Supervisor startup outcome=%s pid=%d — awaiting stop signal",
        result.outcome,
        os.getpid(),
    )

    _install_signal_handlers(_make_signal_handler(supervisor, clock))

    # Ready marker (test harness sync — see tests/integration/test_ctl_stop_safe_stop_e2e.py).
    # No-op when FX_AI_SUPERVISOR_READY_FILE is unset (production default).
    ready_file = os.environ.get("FX_AI_SUPERVISOR_READY_FILE", "").strip()
    if ready_file:
        Path(ready_file).write_text(str(os.getpid()), encoding="utf-8")

    # Poll instead of Event.wait() because threading.Event.wait() blocks in a
    # Win32 wait that is not interrupted by SIGBREAK; time.sleep() is.
    while not _shutdown_event.is_set():
        time.sleep(0.2)

    _log.info("Supervisor exiting cleanly (pid=%d)", os.getpid())
    return 0


if __name__ == "__main__":
    sys.exit(main())
