"""ML uplift harness synthetic-only smoke tests."""

from __future__ import annotations

import json

import pytest

from scripts.ml_uplift_harness.constants import NON_AUTHORISATION_FLAGS, SYNTHETIC_MARKERS
from scripts.ml_uplift_harness.contracts import HarnessContractError
from scripts.ml_uplift_harness.synthetic_runner import run_synthetic_smoke


def test_synthetic_smoke_succeeds_and_marks_output(tmp_path, synthetic_contract):
    report = run_synthetic_smoke(synthetic_contract, tmp_path, code_sha="test-sha")
    assert set(SYNTHETIC_MARKERS) <= set(report["markers"])
    for flag in NON_AUTHORISATION_FLAGS:
        assert report["non_authorisation_flags"][flag] is False
    exp_dir = tmp_path / "synthetic-exp-001"
    assert (exp_dir / "synthetic_report.json").exists()
    assert (exp_dir / "report.md").exists()


def test_synthetic_output_contains_required_markers(tmp_path, synthetic_contract):
    run_synthetic_smoke(synthetic_contract, tmp_path, code_sha="test-sha")
    text = (tmp_path / "synthetic-exp-001" / "synthetic_report.json").read_text(encoding="utf-8")
    for marker in ("SYNTHETIC_ONLY", "NO_MODEL_RUN", "NO_BACKTEST", "NO_TRADING_METRICS"):
        assert marker in text
    md = (tmp_path / "synthetic-exp-001" / "report.md").read_text(encoding="utf-8")
    assert "SYNTHETIC_ONLY" in md


def test_synthetic_output_has_no_forbidden_labels(tmp_path, synthetic_contract):
    run_synthetic_smoke(synthetic_contract, tmp_path, code_sha="test-sha")
    text = (tmp_path / "synthetic-exp-001" / "synthetic_report.json").read_text(encoding="utf-8")
    for token in (
        "PASS",
        "TIER1",
        "FORMALLY_VERIFIED",
        "SENTINEL_VERIFICATION_COMPLETE",
        "BYTE_ADMISSIBLE",
        "PRODUCTION_READY",
        "MODEL_IMPROVED",
        "EXPECTANCY_IMPROVED",
    ):
        assert token not in text


def test_synthetic_output_has_no_metric_values(tmp_path, synthetic_contract):
    run_synthetic_smoke(synthetic_contract, tmp_path, code_sha="test-sha")
    payload = json.loads(
        (tmp_path / "synthetic-exp-001" / "synthetic_report.json").read_text(encoding="utf-8")
    )

    def _walk(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                assert k.lower() not in {"sharpe", "pnl", "ic", "mi", "expectancy", "win_rate"}
                _walk(v)
        elif isinstance(obj, list):
            for item in obj:
                _walk(item)

    _walk(payload)


def test_invalid_contract_fails_closed(tmp_path, synthetic_contract):
    synthetic_contract["data_span"]["real_data_authorised"] = True
    with pytest.raises(HarnessContractError):
        run_synthetic_smoke(synthetic_contract, tmp_path, code_sha="test-sha")


def test_model_training_flag_fails_closed(tmp_path, synthetic_contract):
    synthetic_contract["non_authorisation"]["model_training_performed"] = True
    with pytest.raises(HarnessContractError):
        run_synthetic_smoke(synthetic_contract, tmp_path, code_sha="test-sha")
