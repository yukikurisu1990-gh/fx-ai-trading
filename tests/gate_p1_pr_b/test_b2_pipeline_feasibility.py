"""PR-B.2 static pipeline feasibility tests."""

from __future__ import annotations

import json
from pathlib import Path

from scripts._gate_p1_inspector.b2_constants import (
    PIPE_PATH_OBSERVED,
    PIPE_PATH_UNRESOLVED,
    PIPE_RETENTION_PROBE_REQUIRED,
    PR_B1_EVIDENCE_SPANS,
)
from scripts._gate_p1_inspector.inspector import pipeline_feasibility as pipe

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_feasibility_on_real_repo_static_only():
    result = pipe.build_pipeline_feasibility(REPO_ROOT)
    # No execution / raw read / metric flags.
    assert result["pipeline_executed"] is False
    assert result["raw_data_read"] is False
    assert result["features_generated"] is False
    assert result["labels_generated"] is False
    assert result["trading_metrics_computed"] is False
    assert PIPE_RETENTION_PROBE_REQUIRED in result["blocking_labels"]


def test_pr_b1_evidence_present_for_all_spans():
    result = pipe.build_pipeline_feasibility(REPO_ROOT)
    spans = {e["span"] for e in result["pr_b1_evidence_check"]}
    assert spans == set(PR_B1_EVIDENCE_SPANS)
    for e in result["pr_b1_evidence_check"]:
        assert e["present"] is True
        assert e["top_level_outcome"] == "LOCAL_DATA_CANDIDATE_PARTIAL_FEASIBILITY"


def test_static_references_found_without_execution():
    result = pipe.build_pipeline_feasibility(REPO_ROOT)
    assert result["summary"]["references_found"] == result["summary"]["references_total"]
    assert result["static_path_label"] == PIPE_PATH_OBSERVED


def test_feasibility_unresolved_without_evidence_or_sources(tmp_path):
    # Empty repo root: no sources, no PR-B.1 evidence => UNRESOLVED, still no exec.
    result = pipe.build_pipeline_feasibility(tmp_path)
    assert result["static_path_label"] == PIPE_PATH_UNRESOLVED
    assert result["pipeline_executed"] is False
    assert all(e["present"] is False for e in result["pr_b1_evidence_check"])


def test_evidence_check_reads_metadata_not_raw(tmp_path):
    # Provide only a synthetic gate_p1_report.json for one span; no raw data.
    span_dir = tmp_path / "artifacts/gate_p1_pr_b/firstrun_365d_ba"
    span_dir.mkdir(parents=True)
    retention = "RETENTION_CAPABILITY_REQUIRES_SEPARATE_AUTHORISED_PROBE"
    (span_dir / "gate_p1_report.json").write_text(
        json.dumps(
            {
                "top_level_outcome": "LOCAL_DATA_CANDIDATE_PARTIAL_FEASIBILITY",
                "per_candidate_summary": [{"retention_classification": retention}],
            }
        ),
        encoding="utf-8",
    )
    result = pipe.build_pipeline_feasibility(tmp_path)
    present = {e["span"]: e["present"] for e in result["pr_b1_evidence_check"]}
    assert present["365d_BA"] is True
    assert present["730d_BA"] is False  # not provided; no raw data invented
