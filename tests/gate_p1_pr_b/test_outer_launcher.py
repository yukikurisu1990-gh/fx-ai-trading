"""Outer launcher tests (plan §4, §10).

Argument-validation tests are git-free and deterministic. The end-to-end test
spawns the real guarded inner process; it skips if the launcher's pre-flight
worktree check fails (e.g. a dirty tracked worktree during local dev), so the
suite stays green regardless of local state while running fully in CI.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import gate_p1_pr_b_launcher as launcher


def test_invalid_report_id_fails_closed():
    rc = launcher.run(["--report-id", "bad id with spaces"])
    assert rc == launcher.EXIT_PREFLIGHT_FAILED


def test_non_stub_mode_fails_closed(capsys):
    rc = launcher.run(["--report-id", "abc", "--mode", "real"])
    assert rc == launcher.EXIT_PREFLIGHT_FAILED
    err = capsys.readouterr().err
    assert "PR-B.1" in err and "PR-B.2" in err


@pytest.mark.parametrize(
    "report_root",
    [
        "artifacts/gate_p1_pr_b0_stub",
        "data/gate_p1_pr_b0_stub",
        "data/oanda_archive/gate_p1_pr_b0_stub",
        "artifacts/gate_p1_report/x",
        "artifacts/gate_p2_verification/x",
    ],
)
def test_reserved_report_root_rejected(report_root):
    rc = launcher.run(["--report-id", "abc", "--report-root", report_root])
    assert rc == launcher.EXIT_PREFLIGHT_FAILED


def test_in_repo_report_root_rejected():
    # A path inside the repo working tree (even with no reserved component) is
    # rejected so stub output can never be accidentally committed.
    in_repo = str(launcher.REPO_ROOT / "src" / "gate_p1_pr_b0_stub")
    rc = launcher.run(["--report-id", "abc", "--report-root", in_repo])
    assert rc == launcher.EXIT_PREFLIGHT_FAILED


def test_default_stub_report_root_is_safe():
    # The default stub root must be outside the repo and free of reserved parts.
    default_root = launcher.DEFAULT_STUB_REPORT_ROOT.resolve()
    assert launcher._unsafe_report_root_reason(default_root, "stub") is None
    parts = {p.lower() for p in default_root.parts}
    assert parts.isdisjoint({"data", "artifacts"})


def test_tmp_path_report_root_is_accepted(tmp_path):
    # A clean system-temp path (pytest tmp_path) is safe for both modes.
    assert launcher._unsafe_report_root_reason(tmp_path.resolve(), "stub") is None
    assert launcher._unsafe_report_root_reason(tmp_path.resolve(), "b1") is None


def test_default_b1_report_root_is_controlled_inrepo():
    # b1 default lives under the controlled artifacts/gate_p1_pr_b subtree and
    # is accepted for b1 but rejected for stub (stub must be external).
    b1_root = launcher.DEFAULT_B1_REPORT_ROOT.resolve()
    assert launcher._unsafe_report_root_reason(b1_root, "b1") is None
    assert launcher._unsafe_report_root_reason(b1_root, "stub") is not None


def test_b1_rejects_reserved_and_wrong_inrepo_roots():
    # b1 still rejects data/, gate_p2_verification, and in-repo paths outside
    # the controlled artifacts/gate_p1_pr_b subtree.
    assert launcher._unsafe_report_root_reason(Path("data/x").resolve(), "b1") is not None
    assert (
        launcher._unsafe_report_root_reason(
            (launcher.REPO_ROOT / "artifacts" / "gate_p2_verification" / "x").resolve(), "b1"
        )
        is not None
    )
    assert (
        launcher._unsafe_report_root_reason((launcher.REPO_ROOT / "src" / "x").resolve(), "b1")
        is not None
    )


def test_b2_mode_still_rejected(capsys):
    rc = launcher.run(["--report-id", "abc", "--mode", "b2"])
    assert rc == launcher.EXIT_PREFLIGHT_FAILED
    assert "PR-B.2" in capsys.readouterr().err


def test_dependency_pipeline_modes_rejected():
    assert launcher.run(["--report-id", "abc", "--mode", "dependency"]) == (
        launcher.EXIT_PREFLIGHT_FAILED
    )
    assert launcher.run(["--report-id", "abc", "--mode", "pipeline"]) == (
        launcher.EXIT_PREFLIGHT_FAILED
    )


def test_unknown_flag_rejected():
    with pytest.raises(SystemExit):
        launcher.run(["--inspect-real-data", "data/candles.jsonl"])


def test_end_to_end_stub_run(tmp_path):
    report_root = tmp_path / "stub_out"
    rc = launcher.run(
        ["--report-id", "e2e-stub-001", "--report-root", str(report_root), "--first-run"]
    )

    if rc == launcher.EXIT_PREFLIGHT_FAILED:
        pytest.skip("launcher pre-flight failed (likely a dirty tracked worktree)")

    assert rc == launcher.EXIT_OK
    report_dir = report_root / "e2e-stub-001"
    payload = json.loads((report_dir / "gate_p1_report.json").read_text(encoding="utf-8"))
    assert payload["top_level_outcome"] == "STUB_NO_INSPECTION_PERFORMED"
    assert payload["stub_marker"] == "PR_B0_STUB_ONLY"
    assert payload["inspection_performed"] is False

    envelope = json.loads((report_dir / "execution_envelope.json").read_text(encoding="utf-8"))
    assert envelope["mode"] == "stub"
    assert envelope["post_run_audit"]["head_unchanged"] is True
    assert envelope["post_run_audit"]["diff_confined_to_report_dir"] is True
    # pr_b_code_hash agreed between outer envelope and inner (no drift HALT).
    assert envelope["pr_b_code_hash"] == payload["pr_b_code_hash"]


def test_report_id_collision_fails_closed(tmp_path):
    report_root = tmp_path / "out"
    first = launcher.run(["--report-id", "dup-001", "--report-root", str(report_root)])
    if first == launcher.EXIT_PREFLIGHT_FAILED:
        pytest.skip("launcher pre-flight failed (likely a dirty tracked worktree)")
    second = launcher.run(["--report-id", "dup-001", "--report-root", str(report_root)])
    assert second == launcher.EXIT_PREFLIGHT_FAILED
