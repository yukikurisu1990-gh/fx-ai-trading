"""Gate-3a strict scrubber + metadata artifact writer tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.m15_gate3a.artifacts import (
    ArtifactScrubError,
    assert_gate3a_clean,
    validate_metadata_artifact,
    write_metadata_artifact,
)
from scripts.m15_gate3a.guards import RealDataRefusedError


def test_metadata_only_artifact_passes() -> None:
    payload = {
        "artifact": "no_overlap_proof",
        "boundary_constants_utc": {"design_end": "2026-02-28T23:59:59Z"},
        "result": "PROVEN_TRUE",
        "metadata_only": True,
    }
    assert_gate3a_clean(payload)
    validate_metadata_artifact(payload)


def test_raw_row_like_payload_fails() -> None:
    with pytest.raises(ArtifactScrubError):
        assert_gate3a_clean({"bid_o": 1.10, "ask_o": 1.10005})


def test_candles_key_fails() -> None:
    with pytest.raises(ArtifactScrubError):
        assert_gate3a_clean({"candles": [{"o": 1}]})


def test_local_path_fails() -> None:
    with pytest.raises(ArtifactScrubError):
        assert_gate3a_clean({"note": "C:\\Users\\someone\\secret\\data.jsonl"})


def test_secret_like_string_fails() -> None:
    with pytest.raises(ArtifactScrubError):
        assert_gate3a_clean({"token": "AKIAIOSFODNN7EXAMPLE"})


def test_prediction_or_model_output_fails() -> None:
    with pytest.raises(ArtifactScrubError):
        assert_gate3a_clean({"predictions": [0.1, 0.9]})
    with pytest.raises(ArtifactScrubError):
        assert_gate3a_clean({"model": {"weights": [1, 2, 3]}})


def test_strategy_metric_keys_fail() -> None:
    with pytest.raises(ArtifactScrubError):
        assert_gate3a_clean({"sharpe": -1.2})
    with pytest.raises(ArtifactScrubError):
        assert_gate3a_clean({"holdout_metrics": {"expectancy": -3.0}})


def test_trade_level_payload_fails() -> None:
    with pytest.raises(ArtifactScrubError):
        assert_gate3a_clean({"trades": [{"pnl": 1.0}]})


def test_writer_writes_clean_and_refuses_real_paths(tmp_path: Path) -> None:
    out = tmp_path / "m15_gate3a"
    p = write_metadata_artifact(out, "no_overlap_proof.json", {"result": "PROVEN_TRUE"})
    assert p.exists()
    assert p.read_text(encoding="utf-8").strip().startswith("{")
    # refuse writing under the protected real evidence tree
    with pytest.raises(RealDataRefusedError):
        write_metadata_artifact("artifacts/ml_step4/365d_ba_v1/x", "y.json", {"ok": True})


def test_writer_rejects_dirty_payload(tmp_path: Path) -> None:
    with pytest.raises(ArtifactScrubError):
        write_metadata_artifact(tmp_path, "bad.json", {"rows": [{"bid_o": 1.1}]})
