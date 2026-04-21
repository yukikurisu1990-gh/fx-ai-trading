"""End-to-end: ProcessManager stop → SafeStopHandler four-step contract (G-0/G-1).

Verifies that `python -m fx_ai_trading.supervisor` can be started, that
ProcessManager.stop() delivers a *catchable* signal, and that the running
supervisor's signal handler invokes Supervisor.trigger_safe_stop() so the
safe_stop sequence actually fires:

    Step 1: SafeStopJournal.append → logs/safe_stop.jsonl entry
    Step 3: NotifierDispatcher.dispatch → logs/notifications.jsonl entry

Step 4 (supervisor_events INSERT) requires DATABASE_URL and is exercised
elsewhere; this test runs without DB to stay deterministic on CI.

Each test runs in an isolated cwd (tmp_path) so concurrent runs do not
collide on logs/.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from collections.abc import Generator
from pathlib import Path

import pytest

from fx_ai_trading.ops.process_manager import ProcessManager

_SUPERVISOR_BOOT_TIMEOUT_S = 15.0
_READY_POLL_INTERVAL_S = 0.1
_STOP_GRACEFUL_TIMEOUT_S = 15


@pytest.fixture()
def supervisor_workspace(tmp_path: Path) -> Generator[Path, None, None]:
    """Create an isolated workspace with logs/ subdir as the supervisor's cwd."""
    (tmp_path / "logs").mkdir(parents=True, exist_ok=True)
    yield tmp_path


def _wait_for_ready(ready_file: Path, timeout_s: float) -> int:
    """Block until *ready_file* exists; return supervisor PID written inside."""
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if ready_file.exists():
            content = ready_file.read_text(encoding="utf-8").strip()
            if content:
                return int(content)
        time.sleep(_READY_POLL_INTERVAL_S)
    raise AssertionError(
        f"Supervisor did not become ready within {timeout_s}s (no marker at {ready_file})"
    )


def _spawn_supervisor(workspace: Path) -> tuple[ProcessManager, Path]:
    """Spawn `python -m fx_ai_trading.supervisor` rooted at *workspace*.

    DATABASE_URL is intentionally cleared so the subprocess takes the
    no-DB path (steps 1–3 only).  Returns (ProcessManager, ready_file).
    """
    pid_file = workspace / "logs" / "supervisor.pid"
    ready_file = workspace / "logs" / "supervisor.ready"

    env = os.environ.copy()
    env.pop("DATABASE_URL", None)
    env["FX_AI_SUPERVISOR_READY_FILE"] = str(ready_file)

    pm = ProcessManager(pid_file=pid_file)

    cmd = [sys.executable, "-m", "fx_ai_trading.supervisor"]
    popen_kwargs: dict = {"cwd": str(workspace), "env": env}
    if sys.platform == "win32":
        popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        popen_kwargs["start_new_session"] = True

    proc = subprocess.Popen(cmd, **popen_kwargs)  # noqa: S603
    pid_file.parent.mkdir(parents=True, exist_ok=True)
    pid_file.write_text(str(proc.pid), encoding="utf-8")
    return pm, ready_file


class TestCtlStopGracefulSafeStop:
    def test_stop_writes_safe_stop_journal_entry(self, supervisor_workspace: Path) -> None:
        pm, ready_file = _spawn_supervisor(supervisor_workspace)
        try:
            _wait_for_ready(ready_file, _SUPERVISOR_BOOT_TIMEOUT_S)
            stopped = pm.stop(timeout_graceful=_STOP_GRACEFUL_TIMEOUT_S)
        finally:
            if pm.is_running():
                pm.stop(timeout_graceful=2)

        assert stopped is True

        journal = supervisor_workspace / "logs" / "safe_stop.jsonl"
        assert journal.exists(), "safe_stop.jsonl was not created — step 1 did not fire"
        lines = [
            json.loads(line)
            for line in journal.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        assert lines, "safe_stop.jsonl is empty — step 1 did not append"
        entry = lines[-1]
        assert entry["event_code"] == "safe_stop.triggered"
        assert entry["reason"].startswith("ctl_stop_requested:")

    def test_stop_writes_notifier_entry(self, supervisor_workspace: Path) -> None:
        pm, ready_file = _spawn_supervisor(supervisor_workspace)
        try:
            _wait_for_ready(ready_file, _SUPERVISOR_BOOT_TIMEOUT_S)
            pm.stop(timeout_graceful=_STOP_GRACEFUL_TIMEOUT_S)
        finally:
            if pm.is_running():
                pm.stop(timeout_graceful=2)

        notifications = supervisor_workspace / "logs" / "notifications.jsonl"
        assert notifications.exists(), "notifications.jsonl was not created — step 3 did not fire"
        lines = [
            json.loads(line)
            for line in notifications.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        assert lines, "notifications.jsonl is empty — step 3 did not dispatch"
        entry = lines[-1]
        assert entry["event_code"] == "safe_stop.triggered"
        assert entry["severity"] == "critical"

    def test_stop_completes_before_hard_kill_timeout(self, supervisor_workspace: Path) -> None:
        pm, ready_file = _spawn_supervisor(supervisor_workspace)
        try:
            _wait_for_ready(ready_file, _SUPERVISOR_BOOT_TIMEOUT_S)
            t0 = time.monotonic()
            stopped = pm.stop(timeout_graceful=_STOP_GRACEFUL_TIMEOUT_S)
            elapsed = time.monotonic() - t0
        finally:
            if pm.is_running():
                pm.stop(timeout_graceful=2)

        assert stopped is True
        # Graceful path: must complete well below the hard-kill escalation point.
        assert elapsed < _STOP_GRACEFUL_TIMEOUT_S, (
            f"Stop took {elapsed:.2f}s — process was hard-killed, not graceful"
        )
