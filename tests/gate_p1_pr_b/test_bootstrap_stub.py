"""Bootstrap stub-mode tests (plan §10, §11).

These tests exercise the inner stub path in-process (with the bytecode guard
relaxed, since pytest does not run under ``python -B``) and assert the stub
report can never be read as a real Gate P1 inspection result.
"""

from __future__ import annotations

import importlib.util
import json
import sys

from scripts._gate_p1_inspector import bootstrap
from scripts._gate_p1_inspector.report.schema import FORBIDDEN_STUB_KEYS

# Real inspection submodules that belong to PR-B.1 / PR-B.2 and must be ABSENT.
_PR_B1_B2_MODULES = (
    "scripts._gate_p1_inspector.inspector.raw_inventory",
    "scripts._gate_p1_inspector.inspector.coverage",
    "scripts._gate_p1_inspector.inspector.dependency_inventory",
    "scripts._gate_p1_inspector.inspector.pipeline_feasibility",
    "scripts._gate_p1_inspector.inspector.retention",
    "scripts._gate_p1_inspector.inspector.resolver",
    "scripts._gate_p1_inspector.authority.pair_universe",
    "scripts._gate_p1_inspector.authority.schema",
)


def test_stub_run_emits_marked_stub_report(tmp_path):
    report_dir = tmp_path / "report"
    report_dir.mkdir()
    path = bootstrap.run_inner(report_dir, "unit-stub", first_run_mode=True, enforce_bytecode=False)
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["top_level_outcome"] == "STUB_NO_INSPECTION_PERFORMED"
    assert payload["stub_marker"] == "PR_B0_STUB_ONLY"
    assert payload["pr_b_stage"] == "PR-B.0"
    assert payload["inspection_performed"] is False
    assert payload["pr_b1_implemented"] is False
    assert payload["pr_b2_implemented"] is False


def test_stub_report_has_no_inspection_keys(tmp_path):
    report_dir = tmp_path / "report"
    report_dir.mkdir()
    path = bootstrap.run_inner(report_dir, "unit-stub", first_run_mode=True, enforce_bytecode=False)
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert FORBIDDEN_STUB_KEYS.isdisjoint(payload.keys())


def test_stub_run_writes_markdown_without_pass(tmp_path):
    report_dir = tmp_path / "report"
    report_dir.mkdir()
    bootstrap.run_inner(report_dir, "unit-stub", first_run_mode=True, enforce_bytecode=False)
    md = (report_dir / "report.md").read_text(encoding="utf-8")
    assert "PASS" not in md
    assert "NO Gate P1 inspection" in md


def test_stub_run_does_not_import_production_modules(tmp_path):
    report_dir = tmp_path / "report"
    report_dir.mkdir()
    prefixes = ("scripts.stage", "scripts.fetch_oanda", "fx_ai_trading", "src.")
    before = {m for m in sys.modules if m.startswith(prefixes)}
    bootstrap.run_inner(report_dir, "unit-stub", first_run_mode=True, enforce_bytecode=False)
    after = {m for m in sys.modules if m.startswith(prefixes)}
    # The stub run itself must import no production module (other tests in the
    # session may already have imported some; only the delta is attributable).
    assert after - before == set()


def test_pr_b1_b2_submodules_absent():
    for name in _PR_B1_B2_MODULES:
        try:
            spec = importlib.util.find_spec(name)
        except ModuleNotFoundError:
            spec = None  # parent package absent => submodule absent
        assert spec is None, f"{name} must not exist in PR-B.0"


def test_guards_uninstalled_after_run(tmp_path):
    import os

    report_dir = tmp_path / "report"
    report_dir.mkdir()
    bootstrap.run_inner(report_dir, "unit-stub", first_run_mode=True, enforce_bytecode=False)
    # os.environ lookups behave normally again (credential wrapper removed).
    assert os.environ.get("PATH") is not None
