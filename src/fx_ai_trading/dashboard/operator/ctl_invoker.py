"""Subprocess wrapper for ctl 4 commands (M26 Phase 1).

Excludes ``emergency-flat-all`` by type-level enforcement (Literal). The CLI
remains the only invocation path for emergency flat — UI exposure is
forbidden by operations.md §15.1 / phase6_hardening.md §6.18 (4-defense gate).
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

CtlCommand = Literal["start", "stop", "resume-from-safe-stop", "run-reconciler"]

DEFAULT_TIMEOUT_SECONDS = 30

_REPO_ROOT = Path(__file__).resolve().parents[4]
_CTL_SCRIPT = _REPO_ROOT / "scripts" / "ctl.py"


@dataclass(frozen=True)
class CtlResult:
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool


def build_argv(
    command: CtlCommand,
    *,
    reason: str | None = None,
    confirm_live_trading: bool = False,
) -> list[str]:
    argv: list[str] = [sys.executable, str(_CTL_SCRIPT), command]
    if command == "resume-from-safe-stop":
        if reason is None or not reason.strip():
            raise ValueError("resume-from-safe-stop requires a non-empty reason")
        argv.extend(["--reason", reason])
    if command == "start" and confirm_live_trading:
        argv.append("--confirm-live-trading")
    return argv


def _decode(stream: bytes | str | None) -> str:
    if stream is None:
        return ""
    if isinstance(stream, bytes):
        return stream.decode("utf-8", errors="replace")
    return stream


def invoke(
    command: CtlCommand,
    *,
    reason: str | None = None,
    confirm_live_trading: bool = False,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> CtlResult:
    argv = build_argv(
        command, reason=reason, confirm_live_trading=confirm_live_trading
    )
    try:
        proc = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return CtlResult(
            returncode=-1,
            stdout=_decode(exc.stdout),
            stderr=_decode(exc.stderr),
            timed_out=True,
        )
    return CtlResult(
        returncode=proc.returncode,
        stdout=proc.stdout or "",
        stderr=proc.stderr or "",
        timed_out=False,
    )
