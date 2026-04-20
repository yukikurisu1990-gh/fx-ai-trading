"""Unit tests for env_writer.atomic_write_env (M26 Phase 3).

Verifies:
  - Successful write replaces target via tmp + os.replace.
  - Mid-write exception leaves target untouched and tmp removed.
  - PID re-check just before rename aborts the write.
  - Exception messages never contain plaintext values.
  - Tmp file lives in the same directory as the target (Windows atomicity).
"""

from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import patch

import pytest

from fx_ai_trading.dashboard.config_console.env_writer import (
    SupervisorRunningError,
    atomic_write_env,
)


class _StubPM:
    def __init__(self, *, running: bool = False, run_after_open: bool = False):
        self._running = running
        self._run_after_open = run_after_open
        self._call_count = 0

    def is_running(self) -> bool:
        self._call_count += 1
        if self._run_after_open and self._call_count >= 1:
            return True
        return self._running


class TestSuccessPath:
    def test_writes_target_when_pm_idle(self, tmp_path: Path) -> None:
        target = tmp_path / ".env"
        pm = _StubPM(running=False)
        atomic_write_env(target, {"FOO": "bar"}, process_manager=pm)
        assert target.read_text(encoding="utf-8") == "FOO=bar\n"

    def test_overwrites_existing_target(self, tmp_path: Path) -> None:
        target = tmp_path / ".env"
        target.write_text("OLD=v\n", encoding="utf-8")
        pm = _StubPM(running=False)
        atomic_write_env(target, {"NEW": "v"}, process_manager=pm)
        assert target.read_text(encoding="utf-8") == "NEW=v\n"

    def test_creates_parent_directory(self, tmp_path: Path) -> None:
        target = tmp_path / "nested" / "dir" / ".env"
        pm = _StubPM(running=False)
        atomic_write_env(target, {"K": "v"}, process_manager=pm)
        assert target.exists()

    def test_multi_key_serialization(self, tmp_path: Path) -> None:
        target = tmp_path / ".env"
        pm = _StubPM(running=False)
        atomic_write_env(target, {"A": "1", "B": "two"}, process_manager=pm)
        text = target.read_text(encoding="utf-8")
        assert "A=1" in text
        assert "B=two" in text

    def test_no_tmp_files_left_behind(self, tmp_path: Path) -> None:
        target = tmp_path / ".env"
        pm = _StubPM(running=False)
        atomic_write_env(target, {"K": "v"}, process_manager=pm)
        leftover = list(tmp_path.glob("*.tmp"))
        assert leftover == []


class TestPidGate:
    def test_aborts_when_pm_running_at_recheck(self, tmp_path: Path) -> None:
        target = tmp_path / ".env"
        pm = _StubPM(running=True)
        with pytest.raises(SupervisorRunningError):
            atomic_write_env(target, {"K": "v"}, process_manager=pm)
        assert not target.exists()

    def test_aborts_cleans_tmp(self, tmp_path: Path) -> None:
        target = tmp_path / ".env"
        pm = _StubPM(running=True)
        with pytest.raises(SupervisorRunningError):
            atomic_write_env(target, {"K": "v"}, process_manager=pm)
        leftover = list(tmp_path.glob("*.tmp"))
        assert leftover == []

    def test_preserves_existing_target_on_abort(self, tmp_path: Path) -> None:
        target = tmp_path / ".env"
        target.write_text("ORIGINAL=keep\n", encoding="utf-8")
        pm = _StubPM(running=True)
        with pytest.raises(SupervisorRunningError):
            atomic_write_env(target, {"NEW": "v"}, process_manager=pm)
        assert target.read_text(encoding="utf-8") == "ORIGINAL=keep\n"


class TestMidWriteFailure:
    def test_replace_failure_preserves_original(self, tmp_path: Path) -> None:
        target = tmp_path / ".env"
        target.write_text("ORIGINAL=keep\n", encoding="utf-8")
        pm = _StubPM(running=False)
        with (
            patch(
                "fx_ai_trading.dashboard.config_console.env_writer.os.replace",
                side_effect=OSError("simulated replace failure"),
            ),
            pytest.raises(OSError),
        ):
            atomic_write_env(target, {"NEW": "v"}, process_manager=pm)
        assert target.read_text(encoding="utf-8") == "ORIGINAL=keep\n"
        leftover = list(tmp_path.glob("*.tmp"))
        assert leftover == []


class TestNoSecretLeakage:
    def test_exception_messages_redact_values(
        self,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        target = tmp_path / ".env"
        secret = "SECRET-VALUE-DO-NOT-LEAK-1234"
        pm = _StubPM(running=False)
        caplog.set_level(logging.DEBUG)
        with (
            patch(
                "fx_ai_trading.dashboard.config_console.env_writer.os.replace",
                side_effect=OSError("disk error"),
            ),
            pytest.raises(OSError) as excinfo,
        ):
            atomic_write_env(target, {"TOKEN": secret}, process_manager=pm)
        # Exception text must not contain the value
        assert secret not in str(excinfo.value)
        # Captured logs must not contain the value
        for record in caplog.records:
            assert secret not in record.getMessage()

    def test_supervisor_running_error_redacts_values(self, tmp_path: Path) -> None:
        target = tmp_path / ".env"
        secret = "ANOTHER-SECRET-XYZ-9876"
        pm = _StubPM(running=True)
        with pytest.raises(SupervisorRunningError) as excinfo:
            atomic_write_env(target, {"TOKEN": secret}, process_manager=pm)
        assert secret not in str(excinfo.value)


class TestTmpFileLocation:
    def test_tmp_lives_in_same_directory(self, tmp_path: Path) -> None:
        """os.replace source must live in the same dir as target (Windows atomicity)."""
        target = tmp_path / ".env"
        captured: dict[str, Path] = {}

        def fake_replace(src, dst):
            captured["src"] = Path(src)
            captured["dst"] = Path(dst)
            os.rename(src, dst)

        import os

        with patch(
            "fx_ai_trading.dashboard.config_console.env_writer.os.replace",
            side_effect=fake_replace,
        ):
            atomic_write_env(target, {"K": "v"}, process_manager=_StubPM(running=False))
        assert captured["src"].parent == target.parent
        assert captured["dst"] == target
