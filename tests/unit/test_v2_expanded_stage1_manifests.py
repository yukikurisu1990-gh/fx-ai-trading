"""Stage 1 unit tests — provenance manifests + dependency hashes + size guard."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts._verification_harness import manifests as M  # noqa: N812
from scripts._verification_harness import tolerances as T  # noqa: N812

# ---------------------------------------------------------------------------
# contract_hash
# ---------------------------------------------------------------------------


def test_contract_hash_deterministic():
    d = {
        "scope": "foundation",
        "cells": [{"id": "C-sb-baseline", "scorer": "S-B"}],
        "thresholds": {"sharpe_tol": 1e-4},
    }
    h1 = M.compute_contract_hash(d)
    h2 = M.compute_contract_hash(dict(d))
    assert h1 == h2
    assert len(h1) == 64  # SHA-256 hex


def test_contract_hash_differs_on_value_change():
    d1 = {"a": 1}
    d2 = {"a": 2}
    assert M.compute_contract_hash(d1) != M.compute_contract_hash(d2)


# ---------------------------------------------------------------------------
# code_hash — formal 20-file topology
# ---------------------------------------------------------------------------


def test_formal_harness_topology_exactly_20_files():
    assert len(M.FORMAL_HARNESS_FILES) == 20


def test_formal_harness_topology_lists_stage1_files():
    stage1 = (
        "scripts/_verification_harness/__init__.py",
        "scripts/_verification_harness/manifests.py",
        "scripts/_verification_harness/event_log.py",
        "scripts/_verification_harness/pnl_identity.py",
        "scripts/_verification_harness/row_set.py",
        "scripts/_verification_harness/contract_snapshots.py",
        "scripts/_verification_harness/forbidden_inputs.py",
        "scripts/_verification_harness/tolerances.py",
    )
    for p in stage1:
        assert p in M.FORMAL_HARNESS_FILES


def test_compute_code_hash_at_stage_1_records_present_and_absent():
    result = M.compute_code_hash()
    # Stage 1 modules exist
    assert "scripts/_verification_harness/tolerances.py" in result.files_present
    assert "scripts/_verification_harness/event_log.py" in result.files_present
    assert "scripts/_verification_harness/pnl_identity.py" in result.files_present
    # Stage 2/3 modules absent (NOT yet implemented)
    assert "scripts/_verification_harness/sentinel_runner.py" in result.files_absent
    assert "scripts/_verification_harness/reporting.py" in result.files_absent
    assert "scripts/tabular_targeted_verification_v2_expanded.py" in result.files_absent
    # Hash is non-empty hex
    assert len(result.code_hash) == 64


# ---------------------------------------------------------------------------
# data_manifest_hash
# ---------------------------------------------------------------------------


def test_data_manifest_hash_deterministic(tmp_path: Path):
    a = tmp_path / "a.parquet"
    b = tmp_path / "b.parquet"
    a.write_bytes(b"hello")
    b.write_bytes(b"world")
    h1, p1 = M.compute_data_manifest_hash([a, b], pair_universe=("AAA", "BBB"), repo_root=tmp_path)
    h2, p2 = M.compute_data_manifest_hash([a, b], pair_universe=("AAA", "BBB"), repo_root=tmp_path)
    assert h1 == h2


def test_data_manifest_hash_changes_on_content_change(tmp_path: Path):
    a = tmp_path / "a.parquet"
    a.write_bytes(b"hello")
    h1, _ = M.compute_data_manifest_hash([a], repo_root=tmp_path)
    a.write_bytes(b"hello-modified")
    h2, _ = M.compute_data_manifest_hash([a], repo_root=tmp_path)
    assert h1 != h2


# ---------------------------------------------------------------------------
# environment_manifest
# ---------------------------------------------------------------------------


def test_compute_environment_manifest_records_python_version():
    env = M.compute_environment_manifest(seed=42)
    assert env["schema_version"] == "v2-expanded-1.0"
    assert env["seed"] == 42
    assert env["python_version"].startswith("3.")
    assert "lib_versions" in env


def test_assert_environment_manifests_match_passes_on_identical():
    env = M.compute_environment_manifest(seed=42)
    M.assert_environment_manifests_match(env, env)


def test_assert_environment_manifests_match_halts_on_seed_drift():
    env_a = M.compute_environment_manifest(seed=42)
    env_b = M.compute_environment_manifest(seed=43)
    with pytest.raises(M.ManifestError):
        M.assert_environment_manifests_match(env_a, env_b)


# ---------------------------------------------------------------------------
# dependency_source_hashes
# ---------------------------------------------------------------------------


def test_compute_dependency_source_hashes(tmp_path: Path):
    src_a = tmp_path / "fake_helper_a.py"
    src_a.write_text("def f(): return 1\n", encoding="utf-8")
    src_b = tmp_path / "fake_helper_b.py"
    src_b.write_text("def g(): return 2\n", encoding="utf-8")
    payload = M.compute_dependency_source_hashes(
        {"helper_a": src_a, "helper_b": src_b}, repo_root=tmp_path
    )
    assert payload["n_helpers"] == 2
    assert payload["helpers"]["helper_a"]["content_sha256"]
    assert payload["helpers"]["helper_b"]["content_sha256"]


def test_compute_dependency_source_hashes_missing_file_halts(tmp_path: Path):
    bogus = tmp_path / "nonexistent.py"
    with pytest.raises(M.ManifestError):
        M.compute_dependency_source_hashes({"missing": bogus}, repo_root=tmp_path)


def test_mandatory_helper_names_registry():
    assert "_compute_realised_barrier_pnl" in M.MANDATORY_HELPER_NAMES
    assert "precompute_realised_pnl_per_row" in M.MANDATORY_HELPER_NAMES
    assert "split_70_15_15" in M.MANDATORY_HELPER_NAMES
    assert "_build_pair_runtime" in M.MANDATORY_HELPER_NAMES


def test_assert_dependency_hashes_complete_passes_when_all_present():
    payload = {
        "helpers": {
            n: {"source_path": "x", "content_sha256": "0" * 64, "n_bytes": 1}
            for n in M.MANDATORY_HELPER_NAMES
        },
        "n_helpers": len(M.MANDATORY_HELPER_NAMES),
    }
    M.assert_dependency_hashes_complete(payload)


def test_assert_dependency_hashes_complete_halts_on_missing_mandatory():
    payload = {
        "helpers": {
            "_compute_realised_barrier_pnl": {
                "source_path": "x",
                "content_sha256": "0" * 64,
                "n_bytes": 1,
            },
        },
        "n_helpers": 1,
    }
    with pytest.raises(M.ManifestError):
        M.assert_dependency_hashes_complete(payload)


def test_assert_dependency_hashes_complete_halts_on_empty():
    with pytest.raises(M.ManifestError):
        M.assert_dependency_hashes_complete({"helpers": {}, "n_helpers": 0})


# ---------------------------------------------------------------------------
# size guard
# ---------------------------------------------------------------------------


def test_size_guard_under_limit(tmp_path: Path):
    p = tmp_path / "small.parquet"
    p.write_bytes(b"x" * 1024)
    M.assert_artifact_under_size_guard(p)  # no raise


def test_size_guard_halts_over_limit(tmp_path: Path, monkeypatch):
    p = tmp_path / "big.parquet"
    p.write_bytes(b"x" * 1024)
    # Patch the guard to a low byte threshold for the test
    monkeypatch.setattr(M, "ARTIFACT_SIZE_GUARD_BYTES", 100)
    with pytest.raises(M.ManifestError):
        M.assert_artifact_under_size_guard(p)


def test_size_guard_constant_from_tolerances():
    assert M.ARTIFACT_SIZE_GUARD_BYTES == T.ARTIFACT_SIZE_GUARD_BYTES


def test_check_artifact_tree_size_collects_violations(tmp_path: Path, monkeypatch):
    p_small = tmp_path / "small.parquet"
    p_small.write_bytes(b"x" * 50)
    p_big = tmp_path / "big.parquet"
    p_big.write_bytes(b"x" * 200)
    monkeypatch.setattr(M, "ARTIFACT_SIZE_GUARD_BYTES", 100)
    report = M.check_artifact_tree_size([p_small, p_big])
    assert report["n_files_inspected"] == 2
    assert len(report["violations"]) == 1
    assert report["violations"][0]["path"] == str(p_big)
    assert not report["all_under_guard"]


# ---------------------------------------------------------------------------
# write_manifest_json round-trip
# ---------------------------------------------------------------------------


def test_write_manifest_json_round_trip(tmp_path: Path):
    payload = {"schema_version": "v2-expanded-1.0", "data": [1, 2, 3]}
    out = tmp_path / "manifests" / "sample.json"
    M.write_manifest_json(payload, out)
    assert out.is_file()
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert loaded == payload
