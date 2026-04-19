"""Integration tests: ProcessManager start/stop lifecycle (M22 / Mi-CTL-1).

Uses a real subprocess (python -c "...sleep...") to verify the
start → is_running → stop lifecycle without spawning the real Supervisor.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

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
