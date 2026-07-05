"""First-run real-path tests — synthetic production-shaped data only."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from scripts.ml_step4 import evidence, execute_365d_ba, features
from scripts.ml_step4.data_adapter import Real365dBaProvider, RealDataRefusedError
from scripts.ml_step4.inventory import InventoryRecord

# --- synthetic BA fixture files in the real schema ---------------------------


def _write_pair(root: Path, pair: str, n: int, seed: int) -> InventoryRecord:
    state = seed
    mid = 1.1000
    start = datetime(2025, 4, 26, 0, 0, tzinfo=UTC)
    lines = []
    for i in range(n):
        state = (state * 6364136223846793005 + 1442695040888963407) % (2**64)
        step = ((state >> 16) % 2001 - 1000) / 1000.0 * 0.00012
        state = (state * 6364136223846793005 + 1442695040888963407) % (2**64)
        wick = ((state >> 16) % 1000) / 1000.0 * 0.00025
        o, c = mid, mid + step
        hi, lo = max(o, c) + wick, min(o, c) - wick
        half = 0.00006
        ts = (start + timedelta(minutes=i)).strftime("%Y-%m-%dT%H:%M:%S.000000000Z")
        lines.append(
            json.dumps(
                {
                    "time": ts,
                    "volume": 10,
                    "bid_o": o - half,
                    "bid_h": hi - half,
                    "bid_l": lo - half,
                    "bid_c": c - half,
                    "ask_o": o + half,
                    "ask_h": hi + half,
                    "ask_l": lo + half,
                    "ask_c": c + half,
                }
            )
        )
        mid = c
    fname = f"candles_{pair}_M1_365d_BA.jsonl"
    data = ("\n".join(lines) + "\n").encode("utf-8")
    (root / fname).write_bytes(data)
    ts_min = start.strftime("%Y-%m-%dT%H:%M:%S.000000000Z")
    ts_max = (start + timedelta(minutes=n - 1)).strftime("%Y-%m-%dT%H:%M:%S.000000000Z")
    return InventoryRecord(
        filename=fname,
        sha256=hashlib.sha256(data).hexdigest(),
        size_bytes=len(data),
        ts_min_utc=ts_min,
        ts_max_utc=ts_max,
    )


def _provider(root: Path, pairs=("FIXA", "FIXB"), n: int = 2400) -> Real365dBaProvider:
    root.mkdir(parents=True, exist_ok=True)
    recs = [_write_pair(root, p, n, seed=1000 + i) for i, p in enumerate(pairs)]
    return Real365dBaProvider(recs, data_root=str(root))


# --- provider verification ----------------------------------------------------


def test_provider_verify_success(tmp_path: Path) -> None:
    prov = _provider(tmp_path / "data", n=300)
    rep = prov.verify()
    assert rep["all_match"] is True
    assert rep["observed_file_count"] == 2
    assert rep["provider_id"] == Real365dBaProvider.provider_id
    assert set(prov.pairs) == {"FIXA", "FIXB"}


def test_provider_tampered_file_fails_closed(tmp_path: Path) -> None:
    root = tmp_path / "data"
    prov = _provider(root, n=300)
    # tamper one file AFTER inventory hashing
    f = next(root.glob("candles_FIXA_*.jsonl"))
    f.write_bytes(f.read_bytes() + b'{"time":"x"}\n')
    with pytest.raises(RealDataRefusedError):
        prov.verify()


def test_provider_size_mismatch_fails_closed(tmp_path: Path) -> None:
    root = tmp_path / "data"
    root.mkdir(parents=True)
    rec = _write_pair(root, "FIXA", 300, seed=1)
    bad = InventoryRecord(
        filename=rec.filename,
        sha256=rec.sha256,
        size_bytes=rec.size_bytes + 5,
        ts_min_utc=rec.ts_min_utc,
        ts_max_utc=rec.ts_max_utc,
    )
    with pytest.raises(RealDataRefusedError):
        Real365dBaProvider([bad], data_root=str(root)).verify()


def test_provider_missing_file_fails_closed(tmp_path: Path) -> None:
    root = tmp_path / "data"
    root.mkdir(parents=True)
    rec = _write_pair(root, "FIXA", 300, seed=1)
    (root / rec.filename).unlink()
    with pytest.raises(RealDataRefusedError):
        Real365dBaProvider([rec], data_root=str(root)).verify()


def test_provider_pair_frame_requires_verify(tmp_path: Path) -> None:
    prov = _provider(tmp_path / "data", n=300)
    with pytest.raises(RealDataRefusedError):
        prov.pair_frame("FIXA")  # verify() not called


def test_provider_report_scrub_clean(tmp_path: Path) -> None:
    prov = _provider(tmp_path / "data", n=300)
    rep = prov.verify()
    evidence.assert_clean(rep)  # no personal paths / rows


# --- production v4-base feature seam ------------------------------------------


def _synthetic_df(n: int):
    import pandas as pd

    prov = None  # noqa
    start = datetime(2025, 4, 26, tzinfo=UTC)
    rows = []
    mid = 1.1
    for i in range(n):
        mid += 0.00008 * ((i % 7) - 3)
        rows.append(
            {
                "timestamp": start + timedelta(minutes=i),
                "bid_o": mid - 6e-5,
                "bid_h": mid + 2e-4,
                "bid_l": mid - 2e-4,
                "bid_c": mid - 6e-5,
                "ask_o": mid + 6e-5,
                "ask_h": mid + 3e-4,
                "ask_l": mid - 1e-4,
                "ask_c": mid + 6e-5,
            }
        )
    df = pd.DataFrame(rows)
    for c, (a, b) in {
        "open": ("bid_o", "ask_o"),
        "high": ("bid_h", "ask_h"),
        "low": ("bid_l", "ask_l"),
        "close": ("bid_c", "ask_c"),
    }.items():
        df[c] = (df[a] + df[b]) / 2.0
    return df


def test_feature_seam_39_base_cols_no_mtf() -> None:
    df, cols = features.compute_production_v4_base(_synthetic_df(2000))
    assert len(cols) == 39
    assert cols == list(features.V4_BASE_FEATURE_COLS)
    for mtf in ("h4_atr_14", "d1_return_3", "w1_return_1"):
        assert mtf not in df.columns  # excluded MTF must not appear


def test_feature_seam_causal_truncation_invariance() -> None:
    full, cols = features.compute_production_v4_base(_synthetic_df(2000))
    trunc, _ = features.compute_production_v4_base(_synthetic_df(2000).iloc[:1500].copy())
    # features for rows up to T are unchanged when future rows after T are removed
    a = full[cols].iloc[:1400].fillna(0.0).values.tolist()
    b = trunc[cols].iloc[:1400].fillna(0.0).values.tolist()
    assert a == b


def test_feature_binding_records_identity() -> None:
    fb = features.production_feature_binding()
    assert fb["n_features"] == 39
    assert fb["mtf_excluded"] is True
    assert fb["feature_version"] == "v4_base_only"


# --- CLI real-mode refusals / gates ------------------------------------------


def test_cli_no_flag_refuses(capsys) -> None:
    assert execute_365d_ba.main([]) == 2
    assert "REFUSED" in capsys.readouterr().out


def test_cli_execute_refuses(capsys) -> None:
    assert execute_365d_ba.main(["--execute"]) == 2


def test_env_vars_cannot_enable_first_run(tmp_path: Path, monkeypatch) -> None:
    for v in ("ML_STEP4_EXECUTE", "ML_STEP4_REAL", "ALLOW_REAL_EXECUTION"):
        monkeypatch.setenv(v, "1")
    # no first-run flag -> still refuses
    assert execute_365d_ba.main([]) == 2


def test_first_run_preflight_gates_pass_synthetic(tmp_path: Path) -> None:
    prov = _provider(tmp_path / "data", n=300)
    rep = execute_365d_ba.first_run_preflight(provider=prov)
    assert rep["run_status"] == "FIRST_RUN_GATES_PASSED_NO_TRAINING"
    assert rep["training_performed"] is False
    assert all(v == "PASS" for v in rep["gates"].values())
    assert rep["inventory"]["all_match"] is True


def test_first_run_preflight_checksum_gate_stops(tmp_path: Path) -> None:
    root = tmp_path / "data"
    prov = _provider(root, n=300)
    next(root.glob("candles_FIXA_*.jsonl")).write_bytes(b"corrupt")
    rep = execute_365d_ba.first_run_preflight(provider=prov)
    assert rep["run_status"] == "ML_STEP4_365D_BA_FIRST_RUN_STOPPED_BEFORE_TRAINING"
    assert rep["training_performed"] is False
    assert rep["evidence_written"] is False


# --- end-to-end real path (real LightGBM on tiny synthetic data) -------------


def test_first_run_end_to_end_tiny(tmp_path: Path) -> None:
    pytest.importorskip("lightgbm")
    from scripts.ml_step4.body import FIRST_RUN_COMPLETED, run_first_run_365d_ba

    prov = _provider(tmp_path / "data", pairs=("FIXA", "FIXB"), n=3000)
    prov.verify()
    out = tmp_path / "out"
    summary = run_first_run_365d_ba(provider=prov, out_dir=str(out), code_sha="0" * 40, real=True)

    assert summary["run_status"] == FIRST_RUN_COMPLETED
    assert summary["holdout_evaluated_count"] == 1
    assert summary["rerun_performed"] is False
    assert summary["checksum_all_match"] is True
    assert summary["feature_cols_n"] == 39
    assert summary["selected_threshold"] in (0.35, 0.40, 0.45)
    assert len(summary["rejected_threshold_variants"]) == 2
    # closed-vocabulary acceptance status
    from scripts.ml_step4.acceptance import DOES_NOT_MEET, INVALID_REASONS, MEETS

    allowed = {MEETS, DOES_NOT_MEET} | {f"ML_STEP4_RUN_INVALID_{r}" for r in INVALID_REASONS}
    assert summary["acceptance_status"] in allowed

    # eight metadata-only payloads written, all scrub-clean
    written = sorted(p.name for p in out.glob("*"))
    assert written == sorted(evidence.EXPECTED_EVIDENCE_FILES)
    for name in evidence.EXPECTED_EVIDENCE_FILES:
        if name.endswith(".json"):
            payload = json.loads((out / name).read_text(encoding="utf-8"))
            assert payload["real_run"] is True
            evidence.assert_clean(payload)
    prov_report = json.loads((out / "ml_step4_leakage_provenance_report.json").read_text("utf-8"))
    assert prov_report["provider_id"] == Real365dBaProvider.provider_id
    assert prov_report["checksum_all_match"] is True
    assert prov_report["holdout_evaluated_count"] == 1
    assert prov_report["threshold_selected_on"] == "validation_only"


def test_end_to_end_does_not_touch_protected_evidence(tmp_path: Path) -> None:
    pytest.importorskip("lightgbm")
    from scripts.ml_step4.body import run_first_run_365d_ba

    exec_dir = evidence.repo_root() / evidence.EXECUTION_EVIDENCE_DIR
    before = sorted(p.name for p in exec_dir.glob("*")) if exec_dir.exists() else []
    prov = _provider(tmp_path / "data", n=3000)
    prov.verify()
    run_first_run_365d_ba(
        provider=prov, out_dir=str(tmp_path / "out"), code_sha="0" * 40, real=True
    )
    after = sorted(p.name for p in exec_dir.glob("*")) if exec_dir.exists() else []
    assert before == after  # PR #409 stop evidence (8 files) untouched
