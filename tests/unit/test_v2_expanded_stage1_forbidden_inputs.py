"""Stage 1 unit tests — forbidden EXPLORATORY_ONLY path rejection."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts._verification_harness import forbidden_inputs as FI  # noqa: N812


def test_forbidden_prefix_registry_contains_stage29_0b():
    assert "artifacts/stage29_0b/" in FI.FORBIDDEN_PATH_PREFIXES


def test_assert_path_not_forbidden_passes_on_safe_path():
    FI.assert_path_not_forbidden("artifacts/tabular_targeted_verification_v2_expanded/foo.json")
    FI.assert_path_not_forbidden("data/m1_ba/USDJPY.parquet")
    FI.assert_path_not_forbidden("scripts/_verification_harness/tolerances.py")


def test_assert_path_not_forbidden_rejects_stage29_0b():
    for p in (
        "artifacts/stage29_0b/checkpoints/S1_seed42.pt",
        "artifacts/stage29_0b/sanity_probe.json",
        "artifacts/stage29_0b/windowed_dataset/usdjpy.parquet",
    ):
        with pytest.raises(FI.ForbiddenInputError):
            FI.assert_path_not_forbidden(p)


def test_assert_path_not_forbidden_rejects_when_subpath():
    # Windows-style backslash path normalised
    with pytest.raises(FI.ForbiddenInputError):
        FI.assert_path_not_forbidden("artifacts\\stage29_0b\\foo.json")


def test_check_paths_iterable_first_violation_raises():
    paths = [
        "data/m1_ba/USDJPY.parquet",
        "artifacts/stage29_0b/checkpoints/S2_seed42.pt",  # forbidden
        "scripts/_verification_harness/tolerances.py",
    ]
    with pytest.raises(FI.ForbiddenInputError):
        FI.check_paths_iterable(paths)


def test_write_forbidden_inputs_manifest(tmp_path: Path):
    out = tmp_path / "manifests" / "forbidden_inputs.json"
    FI.write_forbidden_inputs_manifest(out)
    assert out.is_file()
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "v2-expanded-1.0"
    assert "artifacts/stage29_0b/" in payload["forbidden_path_prefixes"]
    assert "9ac8fda" in payload["rationale"]
