"""Step 3 — ML uplift harness end-to-end synthetic dry-run tests.

Exercises the merged harness through its public entrypoint on the committed
synthetic config, verifies the produced report is safe/clearly-marked, and
validates the committed synthetic example report. No real data / model /
backtest / metric.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from scripts.ml_uplift_harness.contracts import HarnessContractError
from scripts.ml_uplift_harness.synthetic_runner import run_synthetic_smoke

REPO_ROOT = Path(__file__).resolve().parents[2]
_FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "ml_uplift_harness"
_CONFIG = _FIXTURE_DIR / "synthetic_dry_run_config.json"
_COMMITTED_REPORT = _FIXTURE_DIR / "synthetic_reports" / "synthetic_dry_run_report.json"

_REQUIRED_TOKENS = (
    "SYNTHETIC_ONLY",
    "NOT_REAL_EXPERIMENT_EVIDENCE",
    "NO_REAL_DATA",
    "NO_MODEL_RUN",
    "NO_BACKTEST",
    "NO_TRADING_METRICS",
    "REAL_EXPERIMENT_NOT_AUTHORISED",
    "T2_NOT_AUTHORISED",
    "BYTE_ADMISSIBILITY_NOT_APPROVED",
    "NEW_EPOCH_NOT_AUTHORISED",
    "PRODUCTION_CHANGE_NOT_AUTHORISED",
)

_FORBIDDEN_CLAIM_TOKENS = (
    "PASS",
    "TIER1",
    "TIER_1",
    "FORMALLY_VERIFIED",
    "SENTINEL_VERIFICATION_COMPLETE",
    "FEASIBLE_FOR_CONSTRUCTION",
    "BYTE_ADMISSIBLE",
    "PRODUCTION_READY",
    "MODEL_IMPROVED",
    "EXPECTANCY_IMPROVED",
)

_METRIC_KEYS = {"sharpe", "pnl", "ic", "mi", "expectancy", "win_rate", "drawdown", "return"}


def _load_config() -> dict:
    return json.loads(_CONFIG.read_text(encoding="utf-8"))


def _assert_report_safe(text: str) -> None:
    for token in _REQUIRED_TOKENS:
        assert token in text, f"required token missing: {token}"
    for token in _FORBIDDEN_CLAIM_TOKENS:
        assert token not in text, f"forbidden token present: {token}"
    # metric words (Sharpe/PnL case-insensitive; standalone IC/MI/return/etc.)
    assert not re.search(r"(?i)\bsharpe\b", text)
    assert not re.search(r"(?i)\bpnl\b", text)
    assert not re.search(r"\b(IC|MI)\b", text)
    assert not re.search(r"(?i)\b(win rate|drawdown)\b", text)


def _assert_no_metric_values(payload) -> None:
    if isinstance(payload, dict):
        for key, value in payload.items():
            assert key.lower() not in _METRIC_KEYS, f"metric-value key present: {key}"
            _assert_no_metric_values(value)
    elif isinstance(payload, list):
        for item in payload:
            _assert_no_metric_values(item)


def test_dry_run_through_harness_entrypoint(tmp_path):
    report = run_synthetic_smoke(_load_config(), tmp_path, code_sha="test-dry-run")
    # Writes only under tmp_path.
    exp_dir = tmp_path / "synthetic-dry-run-step3"
    assert (exp_dir / "synthetic_report.json").exists()
    text = (exp_dir / "synthetic_report.json").read_text(encoding="utf-8")
    _assert_report_safe(text)
    _assert_no_metric_values(report)
    for flag in report["non_authorisation_flags"].values():
        assert flag is False


def test_committed_synthetic_example_is_safe():
    assert _COMMITTED_REPORT.exists()
    # Committed example lives under tests/fixtures (never artifacts/ or data/).
    rel = _COMMITTED_REPORT.relative_to(REPO_ROOT).as_posix()
    assert rel.startswith("tests/fixtures/ml_uplift_harness/synthetic_reports/")
    text = _COMMITTED_REPORT.read_text(encoding="utf-8")
    _assert_report_safe(text)
    _assert_no_metric_values(json.loads(text))


def test_committed_example_not_under_forbidden_paths():
    rel = _COMMITTED_REPORT.relative_to(REPO_ROOT).as_posix()
    for bad in ("artifacts/", "data/", "artifacts/gate_p1_pr_b/", "artifacts/ml_uplift/"):
        assert not rel.startswith(bad)


@pytest.mark.parametrize(
    "path",
    [
        ("data_span", "real_data_authorised"),
        ("non_authorisation", "model_training_performed"),
        ("non_authorisation", "backtest_performed"),
        ("non_authorisation", "trading_metrics_computed"),
        ("non_authorisation", "t2_execution_authorised"),
        ("non_authorisation", "byte_admissibility_approved"),
        ("non_authorisation", "production_change_authorised"),
        ("non_authorisation", "llm_integration_authorised"),
    ],
)
def test_dry_run_fails_closed_on_forbidden_flag(tmp_path, path):
    cfg = _load_config()
    section, key = path
    cfg[section][key] = True
    with pytest.raises(HarnessContractError):
        run_synthetic_smoke(cfg, tmp_path, code_sha="test-dry-run")


def test_dry_run_rejects_artifacts_and_data_output_roots(tmp_path):
    cfg = _load_config()
    with pytest.raises(HarnessContractError):
        run_synthetic_smoke(cfg, REPO_ROOT / "artifacts" / "ml_uplift", code_sha="x")
    with pytest.raises(HarnessContractError):
        run_synthetic_smoke(cfg, tmp_path / "data" / "x", code_sha="x")
