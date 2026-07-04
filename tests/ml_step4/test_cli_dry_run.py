"""CLI dry-run tests — no raw data read, no training, no evidence written."""

from __future__ import annotations

from scripts.ml_step4 import evidence
from scripts.ml_step4.run_365d_ba import build_dry_run_summary, main


def test_dry_run_returns_zero(capsys) -> None:
    rc = main(["--dry-run"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "ML_STEP4_CONTRACT_EXECUTOR_IMPLEMENTED_NO_RUN" in out
    assert "RESEARCH_FROZEN_HOLDOUT_EPOCH_365D_BA_V1" in out


def test_invoking_without_dry_run_is_refused(capsys) -> None:
    rc = main([])
    assert rc == 2
    assert "REFUSED" in capsys.readouterr().out


def test_dry_run_summary_flags_no_execution() -> None:
    s = build_dry_run_summary()
    assert s["execution_performed"] is False
    assert s["raw_data_read"] is False
    assert s["model_trained"] is False
    assert s["holdout_evaluated"] is False
    assert s["evidence_written"] is False
    assert s["execution_status"] == "ML_STEP4_EXECUTION_NOT_PERFORMED"
    assert s["production_status"] == "PRODUCTION_READINESS_NOT_CLAIMED"


def test_dry_run_summary_is_scrub_clean() -> None:
    # Metadata-only guarantee: no personal paths / raw rows / creds / env dumps.
    evidence.assert_clean(build_dry_run_summary())


def test_dry_run_reports_three_hashes() -> None:
    s = build_dry_run_summary()
    h = s["hashes"]
    assert set(h) == {"config_hash", "feature_config_hash", "model_config_hash"}
    assert all(len(v) == 64 for v in h.values())


def test_dry_run_lists_all_hard_gates() -> None:
    s = build_dry_run_summary()
    gates = s["pre_execution_hard_gates"]
    assert len(gates) == 16
    assert all(v == "REQUIRED_AT_EXECUTION_NOT_PERFORMED" for v in gates.values())
