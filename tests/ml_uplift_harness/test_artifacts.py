"""ML uplift harness artifact-path planning tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.ml_uplift_harness.artifacts import plan_artifact_manifest, validate_artifact_root
from scripts.ml_uplift_harness.contracts import HarnessContractError

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_temp_root_accepted_and_manifest_deterministic(tmp_path):
    m1 = plan_artifact_manifest(tmp_path, "exp-1", ["synthetic_report.json", "report.md"])
    m2 = plan_artifact_manifest(tmp_path, "exp-1", ["report.md", "synthetic_report.json"])
    assert m1["planned_report_files"] == m2["planned_report_files"]  # sorted, deterministic
    assert m1["write_performed"] is False
    assert m1["experiment_dir"].endswith("exp-1")


def test_real_artifacts_root_rejected():
    real_root = REPO_ROOT / "artifacts" / "ml_uplift"
    with pytest.raises(HarnessContractError):
        validate_artifact_root(real_root)


def test_raw_data_path_rejected(tmp_path):
    with pytest.raises(HarnessContractError):
        validate_artifact_root(tmp_path / "data" / "candles")


def test_in_repo_synthetic_marked_allowed(tmp_path):
    # A path under the repo that is clearly marked synthetic/tests is allowed.
    allowed = REPO_ROOT / "tests" / "ml_uplift_harness_tmp_example"
    assert validate_artifact_root(allowed) is not None


def test_planned_files_reject_non_json_md(tmp_path):
    with pytest.raises(HarnessContractError):
        plan_artifact_manifest(tmp_path, "exp-1", ["evil.exe"])
