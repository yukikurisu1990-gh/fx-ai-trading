"""ProcessManager — Supervisor subprocess lifecycle management (M22 / Mi-CTL-1).

Starts the Supervisor as a detached subprocess, records its PID in
logs/supervisor.pid, and provides stop / status operations.

graceful-stop → wait → SIGKILL ladder is implemented via psutil so that
it works on both Unix and Windows.

Catchable-stop on Windows (G-0/G-1 PR-B):
    Windows ``proc.terminate()`` is ``TerminateProcess`` — uncatchable,
    so the supervisor's SafeStopHandler 4-step contract never fires.
    Instead, ``start()`` spawns with ``CREATE_NEW_PROCESS_GROUP`` so
    ``stop()`` can deliver ``CTRL_BREAK_EVENT`` to that group only —
    Python receives this as ``SIGBREAK`` in the supervisor's signal
    handler.  This pair is the Windows analog of Unix SIGTERM and is
    what makes the safe-stop sequence reachable from outside.
"""

from __future__ import annotations

import logging
import os
import signal
import subprocess
import sys
from pathlib import Path

import psutil

_IS_WINDOWS = sys.platform == "win32"

# subprocess.CREATE_NEW_PROCESS_GROUP is Windows-only.  Resolve via
# getattr so this module imports cleanly on Linux CI runners; the
# value (0x00000200) is the documented CreateProcess flag and is only
# ever passed when ``_IS_WINDOWS`` is True.
_CREATE_NEW_PROCESS_GROUP = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200)

_log = logging.getLogger(__name__)

_DEFAULT_PID_FILE = Path("logs") / "supervisor.pid"


class ProcessManager:
    """Start, stop, and inspect the Supervisor subprocess.

    Args:
        pid_file: Path to the PID file. Defaults to logs/supervisor.pid.
    """

    def __init__(self, pid_file: Path = _DEFAULT_PID_FILE) -> None:
        self._pid_file = pid_file

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self, args: list[str] | None = None) -> int:
        """Spawn the Supervisor subprocess and record its PID.

        Args:
            args: Command line as a list of strings.  Defaults to
                  ``[sys.executable, "-m", "fx_ai_trading.supervisor"]``.

        Returns:
            PID of the new process.

        Raises:
            RuntimeError: if the Supervisor is already running.
            OSError: if the subprocess cannot be spawned or the PID file
                     cannot be written.
        """
        if self.is_running():
            pid = self._read_pid()
            raise RuntimeError(f"Supervisor is already running (PID {pid})")

        cmd = args or [sys.executable, "-m", "fx_ai_trading.supervisor"]
        popen_kwargs: dict = {"start_new_session": True}
        if _IS_WINDOWS:
            # Required so stop() can deliver CTRL_BREAK_EVENT to the
            # supervisor *only* (without it the event would propagate
            # to this process too).  Python translates the event into
            # SIGBREAK in the supervisor's signal handler.
            popen_kwargs["creationflags"] = _CREATE_NEW_PROCESS_GROUP
        proc = subprocess.Popen(cmd, **popen_kwargs)  # noqa: S603
        self._pid_file.parent.mkdir(parents=True, exist_ok=True)
        self._pid_file.write_text(str(proc.pid), encoding="utf-8")
        _log.info("ProcessManager.start: pid=%d cmd=%s", proc.pid, cmd)
        return proc.pid

    def stop(self, *, timeout_graceful: int = 10, timeout_kill: int = 5) -> bool:
        """Stop the Supervisor using a catchable signal → wait → SIGKILL.

        On Unix the catchable signal is SIGTERM (via ``proc.terminate()``).
        On Windows it is CTRL_BREAK_EVENT delivered to the new process
        group created by ``start()``; the supervisor receives it as
        SIGBREAK and runs the SafeStopHandler 4-step sequence before
        exit.  ``proc.terminate()`` on Windows is intentionally NOT used
        — it maps to TerminateProcess which is uncatchable and would
        skip safe_stop.

        Args:
            timeout_graceful: Seconds to wait after the catchable signal
                              before escalating.
            timeout_kill: Seconds to wait after SIGKILL before giving up.

        Returns:
            True if the process was stopped, False if no process was running.
        """
        pid = self._read_pid()
        if pid is None:
            _log.warning("ProcessManager.stop: no PID file found")
            return False

        try:
            proc = psutil.Process(pid)
        except psutil.NoSuchProcess:
            _log.warning("ProcessManager.stop: PID %d not found, cleaning up", pid)
            self._remove_pid_file()
            return False

        if _IS_WINDOWS:
            _log.info("ProcessManager.stop: sending CTRL_BREAK_EVENT to PID %d", pid)
            os.kill(pid, signal.CTRL_BREAK_EVENT)
        else:
            _log.info("ProcessManager.stop: sending SIGTERM to PID %d", pid)
            proc.terminate()
        try:
            proc.wait(timeout=timeout_graceful)
        except psutil.TimeoutExpired:
            _log.warning("ProcessManager.stop: graceful timeout, sending SIGKILL to PID %d", pid)
            proc.kill()
            try:
                proc.wait(timeout=timeout_kill)
            except psutil.TimeoutExpired:
                _log.error("ProcessManager.stop: PID %d did not respond to SIGKILL", pid)
                return False

        self._remove_pid_file()
        _log.info("ProcessManager.stop: PID %d stopped", pid)
        return True

    def is_running(self) -> bool:
        """Return True if a Supervisor process recorded in the PID file is alive."""
        pid = self._read_pid()
        if pid is None:
            return False
        return psutil.pid_exists(pid)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _read_pid(self) -> int | None:
        """Return the PID from the PID file, or None if absent / unreadable."""
        try:
            return int(self._pid_file.read_text(encoding="utf-8").strip())
        except (FileNotFoundError, ValueError):
            return None

    def _remove_pid_file(self) -> None:
        try:
            self._pid_file.unlink(missing_ok=True)
        except OSError as exc:
            _log.warning("ProcessManager: could not remove PID file: %s", exc)
