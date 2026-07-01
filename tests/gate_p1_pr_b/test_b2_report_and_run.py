"""PR-B.2 report / resolver + launcher integration tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import gate_p1_pr_b_launcher as launcher
from scripts._gate_p1_inspector import b2_run, bootstrap
from scripts._gate_p1_inspector.b2_constants import ALLOWED_B2_OUTCOMES
from scripts._gate_p1_inspector.guards import GuardViolationError
from scripts._gate_p1_inspector.report import b2_writers

REPO_ROOT = Path(__file__).resolve().parents[2]


def _run_b2(report_dir: Path) -> dict:
    report_dir.mkdir(parents=True, exist_ok=True)
    bootstrap.run_b2_under_guards(
        report_dir,
        "b2-unit",
        repo_root=REPO_ROOT,
        clean_code_sha="unit-sha",
        base_master_sha="unit-base",
        generated_at="2026-07-01T00:00:00Z",
        enforce_bytecode=False,
    )
    return b2_run.load_report(report_dir)


def test_b2_emits_allowed_outcome_and_flags(tmp_path):
    report = _run_b2(tmp_path / "out")
    assert report["top_level_outcome"] in ALLOWED_B2_OUTCOMES
    assert report["pr_b2_implemented"] is True
    assert report["dependency_inventory_performed"] is True
    assert report["pipeline_feasibility_performed"] is True
    for flag in (
        "raw_data_read",
        "pipeline_executed",
        "model_executed",
        "backtest_executed",
        "feature_generation_performed",
        "label_generation_performed",
        "trading_metrics_computed",
        "t2_execution_authorised",
        "byte_admissibility_approved",
        "new_epoch_adoption_authorised",
        "production_change_authorised",
    ):
        assert report[flag] is False


def test_b2_preserves_pr_b1_span_status(tmp_path):
    report = _run_b2(tmp_path / "out2")
    status = report["pr_b1_span_status_unchanged"]
    for span in ("365d_BA", "730d_BA", "3650d_BA"):
        assert status[span]["top_level_outcome"] == "LOCAL_DATA_CANDIDATE_PARTIAL_FEASIBILITY"
        assert status[span]["retention_classification"] == (
            "RETENTION_CAPABILITY_REQUIRES_SEPARATE_AUTHORISED_PROBE"
        )
    assert report["first_run_pass_structurally_unreachable"] is True


def test_b2_report_has_no_forbidden_content(tmp_path):
    report_dir = tmp_path / "out3"
    _run_b2(report_dir)
    for name in (
        "gate_p1_pr_b2_report.json",
        "dependency_inventory.json",
        "pipeline_feasibility.json",
        "report.md",
    ):
        text = (report_dir / name).read_text(encoding="utf-8")
        for token in (
            "PASS",
            "FORMALLY_VERIFIED",
            "SENTINEL_VERIFICATION_COMPLETE",
            "TIER1",
            "TIER_1",
        ):
            assert token not in text


def test_b2_report_contains_no_raw_keys(tmp_path):
    report_dir = tmp_path / "out4"
    _run_b2(report_dir)
    for name in ("gate_p1_pr_b2_report.json", "dependency_inventory.json"):
        payload = json.loads((report_dir / name).read_text(encoding="utf-8"))
        for forbidden in ("rows", "raw_rows", "candles", "payload"):
            assert forbidden not in payload


def test_b2_writer_rejects_disallowed_outcome():
    with pytest.raises(GuardViolationError):
        b2_writers.validate_b2_outcome("PASS")
    with pytest.raises(GuardViolationError):
        b2_writers.validate_b2_outcome("TIER1_VERIFIED")


def test_b2_writer_rejects_forbidden_tokens(tmp_path):
    with pytest.raises(GuardViolationError):
        b2_writers.write_b2_json(tmp_path, "x.json", {"note": "BYTE_ADMISSIBILITY_APPROVED"})


def test_launcher_b2_mode_accepted_end_to_end(tmp_path):
    report_root = tmp_path / "b2_out"
    rc = launcher.run(
        ["--mode", "b2", "--report-id", "b2-e2e-001", "--report-root", str(report_root)]
    )
    if rc == launcher.EXIT_PREFLIGHT_FAILED:
        pytest.skip("launcher pre-flight failed (likely a dirty tracked worktree)")
    assert rc == launcher.EXIT_OK
    report = json.loads(
        (report_root / "b2-e2e-001" / "gate_p1_pr_b2_report.json").read_text(encoding="utf-8")
    )
    assert report["top_level_outcome"] in ALLOWED_B2_OUTCOMES
    assert report["pr_b2_implemented"] is True


def test_launcher_still_rejects_unauthorised_modes():
    assert launcher.run(["--report-id", "x", "--mode", "b3"]) == launcher.EXIT_PREFLIGHT_FAILED
    assert launcher.run(["--report-id", "x", "--mode", "dependency"]) == (
        launcher.EXIT_PREFLIGHT_FAILED
    )


def test_launcher_b2_rejects_reserved_report_root():
    assert (
        launcher.run(["--mode", "b2", "--report-id", "x", "--report-root", "data/x"])
        == launcher.EXIT_PREFLIGHT_FAILED
    )
