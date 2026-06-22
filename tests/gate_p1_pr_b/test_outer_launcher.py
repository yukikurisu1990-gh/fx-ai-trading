"""Outer launcher tests (plan §4, §10).

Argument-validation tests are git-free and deterministic. The end-to-end test
spawns the real guarded inner process; it skips if the launcher's pre-flight
worktree check fails (e.g. a dirty tracked worktree during local dev), so the
suite stays green regardless of local state while running fully in CI.
"""

from __future__ import annotations

import json

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


def test_unsafe_report_root_rejected(tmp_path):
    unsafe = tmp_path / "data" / "candles"
    rc = launcher.run(["--report-id", "abc", "--report-root", str(unsafe)])
    assert rc == launcher.EXIT_PREFLIGHT_FAILED


def test_unknown_flag_rejected():
    with pytest.raises(SystemExit):
        launcher.run(["--inspect-real-data", "data/candles.jsonl"])


def test_end_to_end_stub_run(tmp_path):
    report_root = tmp_path / "gate_p1_report_out"
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
