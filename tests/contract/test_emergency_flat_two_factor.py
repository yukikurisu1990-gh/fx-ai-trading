"""Contract tests: emergency-flat-all 2-factor gate (M22 / Mi-CTL-1).

Verifies that _do_emergency_flat() cannot execute without a passing
2-factor confirmation, and that a confirmed challenge allows execution.
Uses FixedTwoFactor stubs (no real IO).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from fx_ai_trading.ops.two_factor import FixedTwoFactor


@pytest.fixture()
def notifier_log(tmp_path: Path):
    """Provide a temporary FileNotifier backed by a temp file."""
    from fx_ai_trading.adapters.notifier.file import FileNotifier

    log_file = tmp_path / "notifications.jsonl"
    return FileNotifier(log_path=log_file), log_file


def _call_do_emergency_flat(two_factor, notifier_obj, log_file: Path) -> tuple[bool, list[dict]]:
    from datetime import UTC, datetime

    from fx_ai_trading.common.clock import FixedClock
    from scripts.ctl import _do_emergency_flat  # type: ignore[import]

    clock = FixedClock(datetime(2026, 1, 1, tzinfo=UTC))
    result = _do_emergency_flat(two_factor, notifier=notifier_obj, clock=clock)
    entries: list[dict] = []
    if log_file.exists():
        for line in log_file.read_text(encoding="utf-8").splitlines():
            if line.strip():
                entries.append(json.loads(line))
    return result, entries


class TestTwoFactorGateBlocking:
    def test_rejected_two_factor_returns_false(self, notifier_log) -> None:
        notifier_obj, log_file = notifier_log
        result, _ = _call_do_emergency_flat(FixedTwoFactor(False), notifier_obj, log_file)
        assert result is False

    def test_rejected_two_factor_writes_no_notification(self, notifier_log) -> None:
        notifier_obj, log_file = notifier_log
        _call_do_emergency_flat(FixedTwoFactor(False), notifier_obj, log_file)
        assert not log_file.exists() or log_file.read_text() == ""

    def test_confirmed_two_factor_returns_true(self, notifier_log) -> None:
        notifier_obj, log_file = notifier_log
        result, _ = _call_do_emergency_flat(FixedTwoFactor(True), notifier_obj, log_file)
        assert result is True

    def test_confirmed_two_factor_writes_critical_notification(self, notifier_log) -> None:
        notifier_obj, log_file = notifier_log
        _call_do_emergency_flat(FixedTwoFactor(True), notifier_obj, log_file)
        entries = json.loads(log_file.read_text())
        assert entries["event_code"] == "EMERGENCY_FLAT_ALL"
        assert entries["severity"] == "critical"

    def test_confirmed_two_factor_logs_correct_event_code(self, notifier_log) -> None:
        notifier_obj, log_file = notifier_log
        _call_do_emergency_flat(FixedTwoFactor(True), notifier_obj, log_file)
        entry = json.loads(log_file.read_text())
        assert entry["event_code"] == "EMERGENCY_FLAT_ALL"

    def test_rejection_does_not_raise(self, notifier_log) -> None:
        notifier_obj, log_file = notifier_log
        try:
            _call_do_emergency_flat(FixedTwoFactor(False), notifier_obj, log_file)
        except Exception as exc:
            pytest.fail(f"Rejection raised unexpectedly: {exc}")

    def test_fixed_two_factor_false_implements_protocol(self) -> None:
        two_factor = FixedTwoFactor(False)
        assert callable(two_factor.run_challenge)
        assert two_factor.run_challenge() is False

    def test_fixed_two_factor_true_implements_protocol(self) -> None:
        two_factor = FixedTwoFactor(True)
        assert two_factor.run_challenge() is True
