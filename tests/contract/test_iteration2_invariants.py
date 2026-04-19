"""Contract tests: Iteration 2 aggregate invariants (M25 / §6.13).

Verifies that all Iteration 2 deliverables satisfy their structural contracts:
  - New contract test files exist (M13-M23 scope)
  - New Protocol interfaces are importable
  - Forbidden-pattern lint covers the 2 new Iteration 2 checks (11, 12)
  - No FixedTwoFactor in src/ production code

These are structural invariants — they do not re-test the logic of each
subsystem (that is covered by the individual contract and integration tests).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_SRC_ROOT = _PROJECT_ROOT / "src"
_CONTRACTS_DIR = _PROJECT_ROOT / "tests" / "contract"

if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from tools.lint.custom_checks import find_src_only_forbidden_patterns  # noqa: E402

# ---------------------------------------------------------------------------
# Iteration 2 contract test files (must exist — each represents a milestone)
# ---------------------------------------------------------------------------

_ITERATION2_CONTRACT_FILES = [
    "test_live_confirmation_gate.py",  # M13
    "test_oanda_broker_account_type.py",  # M13
    "test_exit_policy_rules.py",  # M14
    "test_exit_event_fsm.py",  # M14
    "test_email_notifier.py",  # M17
    "test_emergency_flat_two_factor.py",  # M22
    "test_projection_transport.py",  # M23
]

# ---------------------------------------------------------------------------
# Iteration 2 new Protocol / service modules (must be importable)
# ---------------------------------------------------------------------------

_ITERATION2_MODULES = [
    "fx_ai_trading.adapters.projector.supabase",
    "fx_ai_trading.services.projection_service",
    "fx_ai_trading.ops.two_factor",
    "fx_ai_trading.ops.process_manager",
    "fx_ai_trading.services.learning_ops",
]


class TestIteration2ContractFilesExist:
    @pytest.mark.parametrize("filename", _ITERATION2_CONTRACT_FILES)
    def test_contract_file_exists(self, filename: str) -> None:
        path = _CONTRACTS_DIR / filename
        assert path.exists(), f"Iteration 2 contract test file missing: {path}"

    def test_minimum_contract_count(self) -> None:
        """At least 7 Iteration 2 contract test files must be present."""
        present = [f for f in _ITERATION2_CONTRACT_FILES if (_CONTRACTS_DIR / f).exists()]
        assert len(present) >= 7, (
            f"Expected >= 7 Iteration 2 contract files, found {len(present)}: {present}"
        )


class TestIteration2ModulesImportable:
    @pytest.mark.parametrize("module_path", _ITERATION2_MODULES)
    def test_module_importable(self, module_path: str) -> None:
        import importlib

        try:
            importlib.import_module(module_path)
        except ImportError as exc:
            pytest.fail(f"Iteration 2 module {module_path!r} not importable: {exc}")

    def test_two_factor_authenticator_protocol_importable(self) -> None:
        from fx_ai_trading.ops.two_factor import TwoFactorAuthenticator  # noqa: F401

    def test_projection_transport_client_importable(self) -> None:
        from fx_ai_trading.adapters.projector.supabase import (  # noqa: F401
            SupabaseProjectionTransport,
        )

    def test_learning_ops_clock_injected(self) -> None:
        from datetime import UTC, datetime

        from fx_ai_trading.common.clock import FixedClock
        from fx_ai_trading.services.learning_ops import LearningOps

        clock = FixedClock(datetime(2026, 1, 1, tzinfo=UTC))
        ops = LearningOps(clock=clock)
        assert ops is not None


class TestIteration2LintPatternsActive:
    """Verify checks 11 and 12 are active in find_src_only_forbidden_patterns."""

    def test_check11_live_key_detected(self) -> None:
        code = 'cfg = "OANDA_ACCESS_TOKEN=abc123def456ghi789jkl"\n'
        findings = find_src_only_forbidden_patterns(code)
        assert any("live API key" in f for f in findings), (
            f"Check 11 (live key) not detected. Findings: {findings}"
        )

    def test_check12_fixed_two_factor_detected(self) -> None:
        code = "auth = FixedTwoFactor(True)\n"
        findings = find_src_only_forbidden_patterns(code)
        assert any("FixedTwoFactor" in f for f in findings), (
            f"Check 12 (FixedTwoFactor bypass) not detected. Findings: {findings}"
        )

    def test_check11_normal_string_not_flagged(self) -> None:
        code = 'msg = "normal configuration value"\n'
        findings = find_src_only_forbidden_patterns(code)
        assert not any("live API key" in f for f in findings)

    def test_check12_console_two_factor_not_flagged(self) -> None:
        code = "auth = ConsoleTwoFactor()\n"
        findings = find_src_only_forbidden_patterns(code)
        assert not any("FixedTwoFactor" in f for f in findings)


class TestNoFixedTwoFactorInSrc:
    """FixedTwoFactor must not appear as a function call in any src/ file."""

    def test_no_fixed_two_factor_calls_in_src(self) -> None:
        violations: list[str] = []
        for py_file in sorted(_SRC_ROOT.rglob("*.py")):
            try:
                code = py_file.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            findings = find_src_only_forbidden_patterns(code)
            for f in findings:
                if "FixedTwoFactor" in f:
                    rel = py_file.relative_to(_PROJECT_ROOT)
                    violations.append(f"{rel}: {f}")
        assert not violations, f"FixedTwoFactor found in src/ (2-factor bypass): {violations}"
