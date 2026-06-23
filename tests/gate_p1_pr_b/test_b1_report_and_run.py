"""PR-B.1 report schema + orchestrator + launcher integration tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import gate_p1_pr_b_launcher as launcher
from scripts._gate_p1_inspector import b1_run, bootstrap
from scripts._gate_p1_inspector.authority import pair_universe as pu
from scripts._gate_p1_inspector.b1_constants import (
    ALLOWED_FIRST_RUN_OUTCOMES,
    OUTCOME_PARTIAL,
    OUTCOME_RETENTION_UNRESOLVED,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def _pairs() -> list[str]:
    return pu.resolve_pair_universe(REPO_ROOT).pairs or []


def _run_b1(report_dir: Path, data_dir: Path, repo_root: Path, spans=("365d",)) -> dict:
    report_dir.mkdir(parents=True, exist_ok=True)
    bootstrap.run_b1_under_guards(
        report_dir,
        "b1-unit",
        data_dir=data_dir,
        repo_root=repo_root,
        candidate_spans=spans,
        first_run_mode=True,
        enforce_bytecode=False,
    )
    return b1_run.load_report(report_dir)


def test_b1_run_emits_allowed_first_run_outcome(tmp_path, write_full_universe):
    data_dir = tmp_path / "data"
    write_full_universe(data_dir, _pairs(), "365d", n_rows=5)
    report = _run_b1(tmp_path / "out", data_dir, REPO_ROOT)
    assert report["top_level_outcome"] in ALLOWED_FIRST_RUN_OUTCOMES
    # All 20 pairs present + schema-valid + OANDA archive manifest present in the
    # real repo => retention probe required => PARTIAL.
    assert report["top_level_outcome"] == OUTCOME_PARTIAL
    assert report["first_run_mode"] is True


def test_b1_run_retention_unresolved_without_archive(tmp_path, write_full_universe):
    # Point repo_root at a tmp tree with the authority sources copied but no
    # OANDA archive manifest => retention unresolved.
    data_dir = tmp_path / "data"
    write_full_universe(data_dir, _pairs(), "365d", n_rows=5)
    fake_repo = tmp_path / "repo"
    (fake_repo / "scripts").mkdir(parents=True)
    for rel in (
        "scripts/stage23_0a_build_outcome_dataset.py",
        "scripts/stage22_0a_scalp_label_design.py",
    ):
        (fake_repo / rel).write_bytes((REPO_ROOT / rel).read_bytes())
    report = _run_b1(tmp_path / "out2", data_dir, fake_repo)
    assert report["top_level_outcome"] == OUTCOME_RETENTION_UNRESOLVED


def test_b1_run_insufficient_when_pairs_missing(tmp_path, write_candle_file):
    data_dir = tmp_path / "data"
    # Only one pair present out of 20 => insufficient.
    write_candle_file(data_dir, _pairs()[0], "365d", n_rows=5)
    report = _run_b1(tmp_path / "out3", data_dir, REPO_ROOT)
    assert report["top_level_outcome"] == "LOCAL_DATA_INSUFFICIENT_FOR_NEW_EPOCH"


def test_b1_report_has_no_pass_or_success_labels(tmp_path, write_full_universe):
    data_dir = tmp_path / "data"
    write_full_universe(data_dir, _pairs(), "365d", n_rows=5)
    report_dir = tmp_path / "out4"
    _run_b1(report_dir, data_dir, REPO_ROOT)
    report_text = (report_dir / "gate_p1_report.json").read_text(encoding="utf-8")
    md_text = (report_dir / "report.md").read_text(encoding="utf-8")
    for token in ("FORMALLY_VERIFIED", "SENTINEL_VERIFICATION_COMPLETE", "TIER1", "TIER_1"):
        assert token not in report_text
    assert "PASS" not in md_text
    assert "LOCAL_DATA_CANDIDATE_FEASIBLE_FOR_CONSTRUCTION_REVIEW" not in report_text


def test_b1_report_states_pr_b2_not_implemented(tmp_path, write_full_universe):
    data_dir = tmp_path / "data"
    write_full_universe(data_dir, _pairs(), "365d", n_rows=5)
    report_dir = tmp_path / "out5"
    report = _run_b1(report_dir, data_dir, REPO_ROOT)
    assert report["pr_b2_implemented"] is False
    assert report["dependency_inventory_performed"] is False
    assert report["pipeline_feasibility_performed"] is False
    assert report["t2_execution_authorised"] is False
    md = (report_dir / "report.md").read_text(encoding="utf-8")
    assert "PR-B.2" in md and "NOT authorised" in md


def test_b1_report_contains_no_raw_rows(tmp_path, write_full_universe):
    data_dir = tmp_path / "data"
    write_full_universe(data_dir, _pairs(), "365d", n_rows=5)
    report_dir = tmp_path / "out6"
    _run_b1(report_dir, data_dir, REPO_ROOT)
    raw_inv = json.loads((report_dir / "raw_inventory_365d_BA.json").read_text(encoding="utf-8"))
    for forbidden in ("rows", "raw_rows", "candles", "payload"):
        assert forbidden not in raw_inv
    # Per-file entries carry derived metadata only (no row arrays).
    for file_entry in raw_inv["files"]:
        assert "rows" not in file_entry
        assert set(file_entry).issuperset({"file_sha256", "row_count", "schema_valid"})


def test_b1_run_writes_only_under_report_dir(tmp_path, write_full_universe):
    data_dir = tmp_path / "data"
    write_full_universe(data_dir, _pairs(), "365d", n_rows=5)
    report_dir = tmp_path / "out7"
    _run_b1(report_dir, data_dir, REPO_ROOT)
    written = {p.name for p in report_dir.iterdir()}
    assert "gate_p1_report.json" in written
    assert "report.md" in written
    # Data dir is untouched (read-only).
    assert all(f.suffix == ".jsonl" for f in data_dir.iterdir())


def test_launcher_b1_end_to_end(tmp_path, write_full_universe):
    data_dir = tmp_path / "data"
    write_full_universe(data_dir, _pairs(), "365d", n_rows=5)
    report_root = tmp_path / "b1_out"
    rc = launcher.run(
        [
            "--mode",
            "b1",
            "--report-id",
            "b1-e2e-001",
            "--report-root",
            str(report_root),
            "--data-dir",
            str(data_dir),
            "--candidate-spans",
            "365d",
            "--first-run",
        ]
    )
    if rc == launcher.EXIT_PREFLIGHT_FAILED:
        pytest.skip("launcher pre-flight failed (likely a dirty tracked worktree)")
    assert rc == launcher.EXIT_OK
    report = json.loads(
        (report_root / "b1-e2e-001" / "gate_p1_report.json").read_text(encoding="utf-8")
    )
    assert report["top_level_outcome"] in ALLOWED_FIRST_RUN_OUTCOMES
    assert report["pr_b2_implemented"] is False
