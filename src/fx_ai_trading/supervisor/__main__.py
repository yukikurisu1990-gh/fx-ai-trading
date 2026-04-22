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
"""

from __future__ import annotations

import logging
import os
import sys
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

    supervisor = Supervisor(clock=clock)
    ctx = StartupContext(journal=journal, notifier=dispatcher, clock=clock)
    return supervisor, ctx


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
    return 0


if __name__ == "__main__":
    sys.exit(main())
