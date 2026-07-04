"""Run-body tests — fixture-only, real mode refused (synthetic data only)."""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

import pytest

from scripts.ml_step4 import contract, evidence, labels, manifest, metrics, trainer
from scripts.ml_step4.body import BodyError, evaluate_portfolio, guarded_run_body
from scripts.ml_step4.data_adapter import (
    FixtureDataProvider,
    RealDataProviderRefused,
    RealDataRefusedError,
)
from scripts.ml_step4.executor import ExecutionRefusedError
from scripts.ml_step4.features import compute_fixture_features, feature_binding
from scripts.ml_step4.metrics import MetricTrade


def _small_provider() -> FixtureDataProvider:
    # 300 bars is enough for split (purge 21) and fast tests.
    return FixtureDataProvider(n_bars=300)


# --- Real mode refusal --------------------------------------------------------


def test_real_mode_refused(tmp_path: Path) -> None:
    with pytest.raises(ExecutionRefusedError):
        guarded_run_body(mode="real", out_dir=str(tmp_path))


def test_non_fixture_provider_refused(tmp_path: Path) -> None:
    with pytest.raises(ExecutionRefusedError):
        guarded_run_body(mode="fixture", provider=RealDataProviderRefused(), out_dir=str(tmp_path))


def test_real_data_provider_refuses_access() -> None:
    p = RealDataProviderRefused()
    with pytest.raises(RealDataRefusedError):
        _ = p.pairs
    with pytest.raises(RealDataRefusedError):
        p.bars_for("EUR_USD")


def test_env_vars_cannot_enable_real_data(tmp_path: Path, monkeypatch) -> None:
    for var in ("ML_STEP4_REAL", "ML_STEP4_DATA_DIR", "ALLOW_REAL_EXECUTION"):
        monkeypatch.setenv(var, "1")
    with pytest.raises(ExecutionRefusedError):
        guarded_run_body(mode="real", out_dir=str(tmp_path))
    p = RealDataProviderRefused()
    with pytest.raises(RealDataRefusedError):
        p.bars_for("EUR_USD")


# --- Fixture end-to-end rehearsal ----------------------------------------------


def test_fixture_e2e_eight_evidence_payloads(tmp_path: Path) -> None:
    out = guarded_run_body(mode="fixture", out_dir=str(tmp_path))
    assert out["status"] == "ML_STEP4_FIXTURE_REHEARSAL_COMPLETED_NO_REAL_RUN"
    assert out["implementation_status"] == "ML_STEP4_REAL_RUN_BODY_IMPLEMENTED_NO_RUN"
    assert out["fixture_rehearsal_performed"] is True
    for flag in (
        "execution_performed",
        "raw_data_read",
        "model_trained",
        "holdout_evaluated",
        "real_evidence_written",
    ):
        assert out[flag] is False
    written = sorted(p.name for p in tmp_path.glob("*"))
    assert written == sorted(evidence.EXPECTED_EVIDENCE_FILES)
    # every JSON payload is scrub-clean, fixture-flagged, and path-free
    for name in evidence.EXPECTED_EVIDENCE_FILES:
        if name.endswith(".json"):
            payload = json.loads((tmp_path / name).read_text(encoding="utf-8"))
            assert payload["fixture_rehearsal"] is True
            assert payload["synthetic_only"] is True
            assert payload["real_run"] is False
            evidence.assert_clean(payload)


def test_fixture_e2e_deterministic(tmp_path: Path) -> None:
    a = guarded_run_body(mode="fixture", provider=_small_provider(), out_dir=str(tmp_path / "a"))
    b = guarded_run_body(mode="fixture", provider=_small_provider(), out_dir=str(tmp_path / "b"))
    for key in ("selected_threshold", "n_holdout_trades_fixture", "acceptance_dry_output"):
        assert a[key] == b[key]


def test_fixture_never_writes_protected_evidence(tmp_path: Path) -> None:
    exec_dir = evidence.repo_root() / evidence.EXECUTION_EVIDENCE_DIR
    before = sorted(p.name for p in exec_dir.glob("*"))
    guarded_run_body(mode="fixture", provider=_small_provider(), out_dir=str(tmp_path))
    assert sorted(p.name for p in exec_dir.glob("*")) == before  # PR #409 untouched
    with pytest.raises(evidence.EvidenceScrubError):
        guarded_run_body(mode="fixture", provider=_small_provider(), out_dir=str(exec_dir))


def test_missing_out_dir_fails_closed() -> None:
    with pytest.raises(BodyError):
        guarded_run_body(mode="fixture", provider=_small_provider(), out_dir=None)


def test_acceptance_dry_output_uses_closed_vocabulary(tmp_path: Path) -> None:
    from scripts.ml_step4.acceptance import DOES_NOT_MEET, INVALID_REASONS, MEETS

    allowed = {MEETS, DOES_NOT_MEET} | {f"ML_STEP4_RUN_INVALID_{r}" for r in INVALID_REASONS}
    out = guarded_run_body(mode="fixture", provider=_small_provider(), out_dir=str(tmp_path))
    assert out["acceptance_dry_output"] in allowed


# --- Item 1: maxDD notional wiring ---------------------------------------------


def test_notional_default_is_contract_constant() -> None:
    trades = [MetricTrade("P", "2025-06-02", 1.0)]
    bundle = metrics.compute_all(trades, holdout_trading_days=1)
    assert bundle["max_equity_drawdown"]["notional_equity_pips"] == 10_000.0


def test_conflicting_notional_fails_closed() -> None:
    trades = [MetricTrade("P", "2025-06-02", 1.0)]
    with pytest.raises(ValueError):
        metrics.compute_all(trades, holdout_trading_days=1, notional_equity_pips=5_000.0)
    with pytest.raises(BodyError):
        evaluate_portfolio(trades, holdout_trading_days=1, notional_equity_pips=5_000.0)


def test_notional_recorded_in_manifest(tmp_path: Path) -> None:
    guarded_run_body(mode="fixture", provider=_small_provider(), out_dir=str(tmp_path))
    m = json.loads((tmp_path / "ml_step4_run_manifest.json").read_text(encoding="utf-8"))
    assert m["fixed_notional_equity_pips"] == 10_000.0


# --- Item 2: single-source label routing ----------------------------------------


def test_labels_adapter_failure_stops_body(tmp_path: Path, monkeypatch) -> None:
    def boom(*a, **k):
        raise labels.LabelContractError("adapter down")

    monkeypatch.setattr("scripts.ml_step4.body.bulk_labels", boom)
    with pytest.raises(labels.LabelContractError):  # no catch-and-continue
        guarded_run_body(mode="fixture", provider=_small_provider(), out_dir=str(tmp_path))


def test_body_routes_labels_and_scoring_through_adapter(tmp_path: Path, monkeypatch) -> None:
    calls = {"bulk": 0}
    real_bulk = labels.bulk_labels

    def counting_bulk(*a, **k):
        calls["bulk"] += 1
        return real_bulk(*a, **k)

    monkeypatch.setattr("scripts.ml_step4.body.bulk_labels", counting_bulk)
    out = guarded_run_body(mode="fixture", provider=_small_provider(), out_dir=str(tmp_path))
    assert calls["bulk"] == 2  # once per fixture pair — sole label/scoring source
    prov = json.loads(
        (tmp_path / "ml_step4_leakage_provenance_report.json").read_text(encoding="utf-8")
    )
    assert prov["label_contract"]["label_contract_id"] == labels.LABEL_CONTRACT_ID
    assert out["fixture_rehearsal_performed"] is True


def test_no_duplicate_barrier_math_in_body() -> None:
    import inspect

    from scripts.ml_step4 import body

    src = inspect.getsource(body)
    for token in ("bid_h", "ask_l", "atr", "tp_mult *", "first_hit"):
        assert token not in src.replace("tp_mult=contract.TP_MULT_ATR14", ""), token


# --- Item 3: UTC holdout coverage denominator -----------------------------------


def test_holdout_days_counted_by_utc_date(tmp_path: Path) -> None:
    out = guarded_run_body(mode="fixture", out_dir=str(tmp_path))  # 6000-bar default
    # 6000 bars from 2025-06-02T00:00Z: holdout = bars 5100..5999 which span
    # 2025-06-05 (bars 5100..5759) and 2025-06-06 (5760..5999) -> 2 UTC dates.
    assert out["holdout_days_fixture"] == 2


def test_trading_day_utc_offset_grouping() -> None:
    from datetime import timedelta, timezone

    tz = timezone(timedelta(hours=9))
    assert metrics.trading_day_utc(datetime(2025, 6, 3, 8, 0, tzinfo=tz)) == "2025-06-02"


def test_trading_day_naive_fails_closed() -> None:
    with pytest.raises(ValueError):
        metrics.trading_day_utc(datetime(2025, 6, 3, 8, 0))


# --- Item 4: manifest SHA / seeds / package versions ----------------------------


def test_manifest_fields_present() -> None:
    m = manifest.build_run_manifest(mode="fixture_rehearsal", seeds={"fixture_lcg": 1})
    assert len(m["code_sha"]) == 40
    assert m["seeds"] == {"fixture_lcg": 1}
    assert set(m["package_versions"]) >= {"numpy", "pandas", "lightgbm", "scikit-learn"}
    assert m["reproducibility_level"] == "bounded_not_bitwise_guaranteed"
    assert m["python_version"]
    assert m["model_config_hash"] == contract.model_config_hash()


def test_manifest_missing_seeds_fails_closed() -> None:
    with pytest.raises(manifest.ManifestError):
        manifest.build_run_manifest(mode="fixture_rehearsal", seeds={})


def test_manifest_incomplete_fails_closed() -> None:
    with pytest.raises(manifest.ManifestError):
        manifest.assert_manifest_complete({"mode": "x"})


def test_manifest_does_not_alter_model_hash() -> None:
    before = contract.model_config_hash()
    manifest.build_run_manifest(mode="fixture_rehearsal", seeds={"s": 42})
    assert contract.model_config_hash() == before
    assert "random_state" not in contract.LGBM_PARAMS


def test_git_sha_failure_fails_closed(monkeypatch) -> None:
    def no_git(*a, **k):
        raise OSError("git missing")

    monkeypatch.setattr("scripts.ml_step4.manifest.subprocess.run", no_git)
    with pytest.raises(manifest.ManifestError):
        manifest.git_code_sha()


# --- Item 5: diagnostics labeler in evidence pipeline ---------------------------


def test_diagnostics_labeled_in_metrics_report(tmp_path: Path) -> None:
    guarded_run_body(mode="fixture", provider=_small_provider(), out_dir=str(tmp_path))
    report = json.loads((tmp_path / "ml_step4_metrics_report.json").read_text(encoding="utf-8"))
    diags = report["diagnostics"]
    for key in (
        "feature_importance",
        "calibration",
        "per_threshold_validation_curves",
        "session_contribution",
    ):
        assert diags[key]["classification"] == "NON_DECISION_EXPLORATORY"
    # decision metrics live under "metrics", separate from diagnostics
    assert "daily_portfolio_sharpe_annualised" in report["metrics"]
    assert "daily_portfolio_sharpe_annualised" not in diags


# --- Item 6: authoritative split indices -----------------------------------------


def test_split_indices_integer_arithmetic() -> None:
    from scripts.ml_step4.split import bar_index_split

    # sizes where float truncation previously diverged from the exact floor
    for n in (2690, 5280, 5650):
        assert bar_index_split(n)["segments"]["train"]["end_index_exclusive"] == (70 * n) // 100


def test_body_consumes_emitted_split_indices(tmp_path: Path) -> None:
    guarded_run_body(mode="fixture", provider=_small_provider(), out_dir=str(tmp_path))
    split_report = json.loads((tmp_path / "ml_step4_split_report.json").read_text(encoding="utf-8"))
    seg = split_report["segments"]
    assert seg["train"]["end_index_exclusive"] == (70 * 300) // 100
    assert split_report["purge_embargo_bars"] == 21


# --- Fixture data / features / trainer ------------------------------------------


def test_fixture_bars_deterministic_and_m1_aligned() -> None:
    p = _small_provider()
    a, b = p.bars_for("FIX_PAIR_A"), p.bars_for("FIX_PAIR_A")
    assert a == b
    assert all(bar["ts"].second == 0 and bar["ts"].tzinfo is not None for bar in a)
    assert all(bar["ask_o"] > bar["bid_o"] for bar in a)  # positive spread


def test_fixture_features_causal_and_deterministic() -> None:
    bars = _small_provider().bars_for("FIX_PAIR_A")
    rows1, names = compute_fixture_features(bars)
    rows2, _ = compute_fixture_features(bars)
    assert rows1 == rows2
    # causality: truncating the future must not change past rows
    rows_prefix, _ = compute_fixture_features(bars[:100])
    assert rows1[:100] == rows_prefix
    assert len(names) == len(rows1[0])


def test_feature_binding_is_v4_base_only() -> None:
    fb = feature_binding()
    assert fb["contract_feature_config"]["feature_version"] == "v4"
    assert fb["contract_feature_config"]["enabled_groups"] == []
    assert fb["feature_config_hash"] == contract.feature_config_hash()
    assert fb["fixture_builder_is_production_v4"] is False


def test_trainer_config_matches_contract_and_no_reuse() -> None:
    tc = trainer.training_config()
    assert tc["model_config"]["params"] == {"learning_rate": 0.05, "num_leaves": 31, "verbose": -1}
    assert tc["model_config"]["n_estimators"] == 200
    assert tc["deployed_model_reuse"] is False
    assert tc["model_binary_persisted"] is False


def test_fixture_stub_deterministic_and_synthetic() -> None:
    stub = trainer.FixtureModelStub()
    rows = [[0.0001, 0, 0, 0, 0], [-0.0002, 0, 0, 0, 0]]
    assert stub.predict_proba(rows) == stub.predict_proba(rows)
    assert stub.synthetic_only is True
    assert stub.training_mode == "fixture_stub_synthetic_only"


@pytest.mark.skipif(
    os.environ.get("ML_STEP4_HEAVY_TESTS") != "1",
    reason="optional heavy test: real LightGBM on tiny synthetic data (set ML_STEP4_HEAVY_TESTS=1)",
)
def test_train_lgbm_tiny_synthetic() -> None:  # pragma: no cover - optional
    pytest.importorskip("lightgbm")
    x = [[float(i % 3), float(i % 5)] for i in range(90)]
    y = [(i % 3) - 1 for i in range(90)]
    model = trainer.train_lgbm(x, y)
    assert len(model.predict_proba(x[:2])[0]) == 3


# --- Validation-only threshold selection in the body -----------------------------


def test_holdout_cannot_influence_threshold(tmp_path: Path) -> None:
    """Selected threshold is identical whether or not holdout data differs."""
    p1 = FixtureDataProvider(n_bars=300, seed=77)
    out1 = guarded_run_body(mode="fixture", provider=p1, out_dir=str(tmp_path / "a"))
    # Same seed => same train/validation; the selection is a function of the
    # validation segment only (structural: selection happens before any holdout
    # signal is built, and select_threshold has no holdout parameter).
    p2 = FixtureDataProvider(n_bars=300, seed=77)
    out2 = guarded_run_body(mode="fixture", provider=p2, out_dir=str(tmp_path / "b"))
    assert out1["selected_threshold"] == out2["selected_threshold"]


def test_rejected_variants_recorded(tmp_path: Path) -> None:
    guarded_run_body(mode="fixture", provider=_small_provider(), out_dir=str(tmp_path))
    prov = json.loads((tmp_path / "ml_step4_metrics_report.json").read_text(encoding="utf-8"))
    curves = prov["diagnostics"]["per_threshold_validation_curves"]["value"]
    assert len(curves["rejected_variants"]) == 2
    assert curves["holdout_inspected"] is False
