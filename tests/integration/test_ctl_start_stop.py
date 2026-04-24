"""Integration tests: ProcessManager start/stop lifecycle (M22 / Mi-CTL-1).

Uses a real subprocess (python -c "...sleep...") to verify the
start → is_running → stop lifecycle without spawning the real Supervisor.
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import psutil
import pytest

from fx_ai_trading.ops.process_manager import ProcessManager


@pytest.fixture()
def pm(tmp_path: Path) -> ProcessManager:
    pid_file = tmp_path / "supervisor.pid"
    return ProcessManager(pid_file=pid_file)


_SLEEP_CMD = [sys.executable, "-c", "import time; time.sleep(60)"]


class TestProcessManagerStartStop:
    def test_start_returns_positive_pid(self, pm: ProcessManager) -> None:
        pid = pm.start(args=_SLEEP_CMD)
        try:
            assert isinstance(pid, int)
            assert pid > 0
        finally:
            pm.stop()

    def test_start_writes_pid_file(self, pm: ProcessManager, tmp_path: Path) -> None:
        pm.start(args=_SLEEP_CMD)
        try:
            pid_file = tmp_path / "supervisor.pid"
            assert pid_file.exists()
        finally:
            pm.stop()

    def test_is_running_true_after_start(self, pm: ProcessManager) -> None:
        pm.start(args=_SLEEP_CMD)
        try:
            assert pm.is_running() is True
        finally:
            pm.stop()

    def test_is_running_false_before_start(self, pm: ProcessManager) -> None:
        assert pm.is_running() is False

    def test_stop_returns_true(self, pm: ProcessManager) -> None:
        pm.start(args=_SLEEP_CMD)
        result = pm.stop()
        assert result is True

    def test_is_running_false_after_stop(self, pm: ProcessManager) -> None:
        pm.start(args=_SLEEP_CMD)
        pm.stop()
        time.sleep(0.2)
        assert pm.is_running() is False

    def test_pid_file_removed_after_stop(self, pm: ProcessManager, tmp_path: Path) -> None:
        pm.start(args=_SLEEP_CMD)
        pm.stop()
        pid_file = tmp_path / "supervisor.pid"
        assert not pid_file.exists()

    def test_start_twice_raises_runtime_error(self, pm: ProcessManager) -> None:
        pm.start(args=_SLEEP_CMD)
        try:
            with pytest.raises(RuntimeError, match="already running"):
                pm.start(args=_SLEEP_CMD)
        finally:
            pm.stop()

    def test_stop_returns_false_when_not_running(self, pm: ProcessManager) -> None:
        result = pm.stop()
        assert result is False

    def test_start_pid_matches_psutil(self, pm: ProcessManager) -> None:
        pid = pm.start(args=_SLEEP_CMD)
        try:
            assert psutil.pid_exists(pid)
        finally:
            pm.stop()


class TestProcessManagerCrossPlatformBranching:
    """G-0/G-1 PR-B: verify Unix vs Windows branching in start() / stop().

    These tests mock the platform sentinel and ``subprocess.Popen`` /
    ``os.kill`` so the same coverage applies on both runners — the
    actual signal delivery is exercised end-to-end by
    ``test_supervisor_main_entrypoint.TestModuleSubprocessSmoke``.
    """

    def _fake_popen_returning(self, pid: int = 12345) -> MagicMock:
        proc = MagicMock()
        proc.pid = pid
        return proc

    def test_start_on_unix_does_not_set_creationflags(self, tmp_path: Path) -> None:
        pm = ProcessManager(pid_file=tmp_path / "supervisor.pid")
        fake_proc = self._fake_popen_returning()
        with (
            patch("fx_ai_trading.ops.process_manager._IS_WINDOWS", False),
            patch(
                "fx_ai_trading.ops.process_manager.subprocess.Popen",
                return_value=fake_proc,
            ) as mock_popen,
        ):
            pm.start(args=["/bin/true"])
        kwargs = mock_popen.call_args.kwargs
        assert "creationflags" not in kwargs
        assert kwargs.get("start_new_session") is True

    def test_start_on_windows_sets_create_new_process_group(self, tmp_path: Path) -> None:
        pm = ProcessManager(pid_file=tmp_path / "supervisor.pid")
        fake_proc = self._fake_popen_returning()
        with (
            patch("fx_ai_trading.ops.process_manager._IS_WINDOWS", True),
            patch(
                "fx_ai_trading.ops.process_manager.subprocess.Popen",
                return_value=fake_proc,
            ) as mock_popen,
        ):
            pm.start(args=["python", "-c", "pass"])
        kwargs = mock_popen.call_args.kwargs
        assert kwargs.get("creationflags") == subprocess.CREATE_NEW_PROCESS_GROUP

    def test_stop_on_unix_calls_terminate(self, tmp_path: Path) -> None:
        pid_file = tmp_path / "supervisor.pid"
        pid_file.write_text("99999", encoding="utf-8")
        pm = ProcessManager(pid_file=pid_file)

        fake_proc = MagicMock()
        with (
            patch("fx_ai_trading.ops.process_manager._IS_WINDOWS", False),
            patch("fx_ai_trading.ops.process_manager.psutil.Process", return_value=fake_proc),
            patch("fx_ai_trading.ops.process_manager.os.kill") as mock_os_kill,
        ):
            assert pm.stop() is True

        fake_proc.terminate.assert_called_once()
        mock_os_kill.assert_not_called()

    def test_stop_on_windows_sends_ctrl_break_event(self, tmp_path: Path) -> None:
        pid_file = tmp_path / "supervisor.pid"
        pid_file.write_text("99999", encoding="utf-8")
        pm = ProcessManager(pid_file=pid_file)

        fake_proc = MagicMock()
        # Windows-specific signal constant is only available on win32.
        # Use the integer value (1) directly so the test runs on Linux CI.
        ctrl_break_event = getattr(__import__("signal"), "CTRL_BREAK_EVENT", 1)
        with (
            patch("fx_ai_trading.ops.process_manager._IS_WINDOWS", True),
            patch(
                "fx_ai_trading.ops.process_manager.signal.CTRL_BREAK_EVENT",
                ctrl_break_event,
                create=True,
            ),
            patch("fx_ai_trading.ops.process_manager.psutil.Process", return_value=fake_proc),
            patch("fx_ai_trading.ops.process_manager.os.kill") as mock_os_kill,
        ):
            assert pm.stop() is True

        mock_os_kill.assert_called_once_with(99999, ctrl_break_event)
        fake_proc.terminate.assert_not_called()
