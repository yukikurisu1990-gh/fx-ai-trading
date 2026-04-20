"""Contract tests: Operator Console must NOT expose emergency-flat-all.

Verifies the 3-layer defense (M26 Phase 1):
  1. Type level — CtlCommand Literal excludes "emergency-flat-all".
  2. Data shape — preflight.ButtonState has no emergency/flat field.
  3. Code level — page source has no button/invoke for the dangerous op.

These tests are static/source-level and do not require a Streamlit runtime.
"""

from __future__ import annotations

from pathlib import Path
from typing import get_args

import pytest

_PAGE_PATH = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "fx_ai_trading"
    / "dashboard"
    / "pages"
    / "1_Operator_Console.py"
)


def test_ctl_command_literal_excludes_emergency_flat_all() -> None:
    from fx_ai_trading.dashboard.operator.ctl_invoker import CtlCommand

    allowed = get_args(CtlCommand)
    assert "emergency-flat-all" not in allowed


def test_preflight_button_state_has_no_emergency_or_flat_field() -> None:
    from fx_ai_trading.dashboard.operator.preflight import ButtonState

    fields = set(ButtonState.__dataclass_fields__.keys())
    forbidden = {f for f in fields if "flat" in f.lower() or "emergency" in f.lower()}
    assert forbidden == set(), f"Forbidden field(s) on ButtonState: {forbidden}"


def test_page_file_exists() -> None:
    assert _PAGE_PATH.exists(), f"Operator Console page missing at {_PAGE_PATH}"


def test_page_does_not_invoke_emergency_flat() -> None:
    src = _PAGE_PATH.read_text(encoding="utf-8")
    forbidden_invocations = [
        'invoke("emergency-flat-all"',
        "invoke('emergency-flat-all'",
        '"emergency-flat-all", "emergency-flat-all"',
    ]
    for needle in forbidden_invocations:
        assert needle not in src, f"Forbidden invocation literal found: {needle!r}"


def test_page_buttons_do_not_mention_emergency_or_flat() -> None:
    src = _PAGE_PATH.read_text(encoding="utf-8")
    button_lines = [line for line in src.splitlines() if "st.button(" in line]
    assert button_lines, "Sanity: page must contain at least one st.button(...) call"
    for line in button_lines:
        lower = line.lower()
        assert "emergency" not in lower, f"Forbidden 'emergency' in button line: {line}"
        assert "flat" not in lower, f"Forbidden 'flat' in button line: {line}"


def test_page_includes_cli_only_notice() -> None:
    src = _PAGE_PATH.read_text(encoding="utf-8")
    assert "CLI-only" in src, "Page must include the CLI-only notice"
    assert "emergency-flat-all" in src, (
        "Page must explicitly mention emergency-flat-all in the CLI-only notice"
    )


@pytest.mark.parametrize("forbidden_command", ["emergency-flat-all"])
def test_build_argv_type_does_not_accept_dangerous_command(forbidden_command: str) -> None:
    """Runtime sanity: even though Literal isn't enforced at runtime, the
    Literal definition itself does not list emergency-flat-all."""
    from fx_ai_trading.dashboard.operator.ctl_invoker import CtlCommand

    assert forbidden_command not in get_args(CtlCommand)
