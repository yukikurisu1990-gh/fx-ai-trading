"""Background subprocess launcher for model retrain (Phase 9.5)."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[4]
_RETRAIN_SCRIPT = _REPO_ROOT / "scripts" / "retrain_production_models.py"


@dataclass(frozen=True)
class RetrainHandle:
    pid: int


def launch(*, skip_fetch: bool = False, days: int = 365) -> RetrainHandle:
    """Launch retrain_production_models.py as a detached background process."""
    argv = [sys.executable, str(_RETRAIN_SCRIPT), "--days", str(days)]
    if skip_fetch:
        argv.append("--skip-fetch")
    proc = subprocess.Popen(
        argv,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return RetrainHandle(pid=proc.pid)


def is_running(pid: int) -> bool:
    """Return True if the given PID is still alive."""
    try:
        import psutil  # optional dep

        p = psutil.Process(pid)
        return p.is_running() and p.status() not in ("zombie", "dead")
    except Exception:
        pass
    try:
        import os

        os.kill(pid, 0)
        return True
    except OSError:
        return False
