"""Unit tests for ctl_invoker argv builder and Literal type guard (M26 Phase 1)."""

from __future__ import annotations

import sys
from typing import get_args

import pytest

from fx_ai_trading.dashboard.operator import ctl_invoker
from fx_ai_trading.dashboard.operator.ctl_invoker import (
    CtlCommand,
    CtlResult,
    build_argv,
    invoke,
)


class TestCtlCommandLiteral:
    def test_literal_contains_exact_4_commands(self) -> None:
        allowed = set(get_args(CtlCommand))
        assert allowed == {
            "start",
            "stop",
            "resume-from-safe-stop",
            "run-reconciler",
        }

    def test_literal_excludes_emergency_flat_all(self) -> None:
        assert "emergency-flat-all" not in get_args(CtlCommand)


class TestBuildArgv:
    def test_start_basic(self) -> None:
        argv = build_argv("start")
        assert argv[0] == sys.executable
        assert argv[1].endswith("ctl.py")
        assert argv[2] == "start"
        assert "--confirm-live-trading" not in argv

    def test_start_with_confirm_live_trading(self) -> None:
        argv = build_argv("start", confirm_live_trading=True)
        assert argv[-1] == "--confirm-live-trading"

    def test_stop(self) -> None:
        argv = build_argv("stop")
        assert argv[2] == "stop"
        assert len(argv) == 3

    def test_run_reconciler(self) -> None:
        argv = build_argv("run-reconciler")
        assert argv[2] == "run-reconciler"
        assert len(argv) == 3

    def test_resume_with_reason(self) -> None:
        argv = build_argv("resume-from-safe-stop", reason="manual recovery")
        assert argv[2] == "resume-from-safe-stop"
        assert "--reason" in argv
        assert "manual recovery" in argv

    def test_resume_without_reason_raises(self) -> None:
        with pytest.raises(ValueError, match="non-empty reason"):
            build_argv("resume-from-safe-stop")

    def test_resume_with_empty_reason_raises(self) -> None:
        with pytest.raises(ValueError, match="non-empty reason"):
            build_argv("resume-from-safe-stop", reason="")

    def test_resume_with_whitespace_reason_raises(self) -> None:
        with pytest.raises(ValueError, match="non-empty reason"):
            build_argv("resume-from-safe-stop", reason="   ")


class TestInvokeTimeout:
    def test_timeout_returns_timed_out_result(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import subprocess

        def fake_run(*_args, **_kwargs):
            raise subprocess.TimeoutExpired(cmd="ctl", timeout=1)

        monkeypatch.setattr(subprocess, "run", fake_run)
        result = invoke("stop", timeout=1)
        assert isinstance(result, CtlResult)
        assert result.timed_out is True
        assert result.returncode == -1

    def test_invoke_passes_returncode_through(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import subprocess

        class _Proc:
            returncode = 0
            stdout = "ok\n"
            stderr = ""

        def fake_run(*_args, **_kwargs):
            return _Proc()

        monkeypatch.setattr(subprocess, "run", fake_run)
        result = invoke("run-reconciler")
        assert result.returncode == 0
        assert result.stdout == "ok\n"
        assert result.timed_out is False


class TestDefaultTimeout:
    def test_default_timeout_is_30_seconds(self) -> None:
        assert ctl_invoker.DEFAULT_TIMEOUT_SECONDS == 30
