"""Atomic ``.env`` writer with PID race-recheck (M26 Phase 3).

Write path: serialize → write tmp file in **same directory** → ``os.replace()``.
Tmp file in the same dir guarantees atomicity on the same filesystem (Windows
``os.replace`` is non-atomic across volumes — see ``operations.md`` §15.4).

Just before ``os.replace``, ``ProcessManager.is_running()`` is re-checked. If
the Supervisor started in the meantime, the write is aborted and the tmp file
removed (race mitigation per ``m26_implementation_plan.md`` §4.5 #1).

Plaintext secret values are referenced ONLY as local variables in this module;
they are never logged, never returned, never embedded in exception messages.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from fx_ai_trading.dashboard.config_console.env_diff import render_env_text
from fx_ai_trading.ops.process_manager import ProcessManager

_log = logging.getLogger(__name__)

_TMP_SUFFIX = ".env.tmp"


class SupervisorRunningError(RuntimeError):
    """Raised when the Supervisor is detected as running before write."""


def atomic_write_env(
    target_path: Path,
    new_env: dict[str, str],
    *,
    process_manager: ProcessManager | None = None,
) -> None:
    """Write ``new_env`` to ``target_path`` atomically.

    Args:
        target_path: Final ``.env`` path. Tmp file is created in the same dir.
        new_env: Full environment to write (callers compute the merge upstream).
        process_manager: PID gate. Defaults to ``ProcessManager()`` (reads
            ``logs/supervisor.pid``). Injectable for tests.

    Raises:
        SupervisorRunningError: if a Supervisor PID is alive at the moment of
            the rename. The tmp file is removed before raising.
        OSError: if the underlying write / rename fails. Exception messages do
            NOT contain values from ``new_env``.
    """
    pm = process_manager or ProcessManager()
    target = Path(target_path)
    tmp = (
        target.with_suffix(target.suffix + _TMP_SUFFIX)
        if target.suffix
        else (target.parent / (target.name + _TMP_SUFFIX))
    )

    payload = render_env_text(new_env)

    target.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())

        if pm.is_running():
            _safe_unlink(tmp)
            raise SupervisorRunningError(
                "Supervisor started during .env write — aborted before rename"
            )

        os.replace(tmp, target)
        _log.info(
            "env_writer.atomic_write_env: wrote %d keys to target",
            len(new_env),
        )
    except SupervisorRunningError:
        raise
    except Exception:
        _safe_unlink(tmp)
        _log.exception("env_writer.atomic_write_env: failed (values redacted)")
        raise


def _safe_unlink(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        _log.warning("env_writer: could not remove tmp file (path redacted)")
