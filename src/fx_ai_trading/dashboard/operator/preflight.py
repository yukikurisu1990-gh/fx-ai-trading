"""PID-file-driven button-state computation for Operator Console (M26 Phase 1).

Pure functions — no Streamlit dependency, so the logic is unit-testable
without a Streamlit runtime.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

DEFAULT_PID_FILE = Path("logs") / "supervisor.pid"


@dataclass(frozen=True)
class ButtonState:
    can_start: bool
    can_stop: bool
    can_resume: bool
    can_run_reconciler: bool


def read_pid(pid_file: Path = DEFAULT_PID_FILE) -> int | None:
    if not pid_file.exists():
        return None
    try:
        text = pid_file.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def compute_button_state(
    pid: int | None,
    *,
    reason: str = "",
) -> ButtonState:
    pid_present = pid is not None
    has_reason = bool(reason.strip())
    return ButtonState(
        can_start=not pid_present,
        can_stop=pid_present,
        can_resume=pid_present and has_reason,
        can_run_reconciler=True,
    )
