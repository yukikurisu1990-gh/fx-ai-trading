"""Refusal guard tests — synthetic-only machinery must fail closed."""

from __future__ import annotations

from pathlib import Path

import pytest

import scripts.m15_gate3a.guards as guards_mod
from scripts.m15_gate3a.guards import (
    RealDataRefusedError,
    assert_no_forbidden_operation,
    assert_status_allowed,
    assert_synthetic_only,
    refuse_real_path,
)

# Names only, and only ever joined under a synthetic root: RF-4 forbids a test
# from addressing the real protected tree, because the moment the guard regresses
# the suite itself becomes the thing that litters it.
_PROTECTED_TREES = (
    "artifacts/ml_step4/365d_ba_v1",
    "artifacts/gate_p1_pr_b/firstrun_365d_ba",
    "data",
    "models",
    "docs",
)


def test_synthetic_modes_allowed_real_refused() -> None:
    assert_synthetic_only("synthetic")
    assert_synthetic_only("fixture")
    for bad in ("real", "production", "live", "demo"):
        with pytest.raises(RealDataRefusedError):
            assert_synthetic_only(bad)


def test_real_protected_paths_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Containment is the subject here — not the relative-path refusal.

    The previous version passed **relative** spellings. ``resolve_candidate`` now
    refuses a relative path outright (§12.18 / D-7, because containment would
    otherwise depend on the working directory), so the test went green without
    ever reaching the containment test it names: vacuous with respect to its own
    subject. Absolute paths under a monkeypatched authority root make it test
    containment, and make the verdict independent of what happens to exist on
    this host.
    """
    root = tmp_path / "synthetic_repo"
    for tree in _PROTECTED_TREES:
        (root / tree).mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(guards_mod, "repo_root", lambda: root)
    monkeypatch.setattr(guards_mod, "_PROTECTED_PREFIXES", _PROTECTED_TREES)

    for tree in _PROTECTED_TREES:
        with pytest.raises(RealDataRefusedError, match="refused real/protected path"):
            refuse_real_path(root / tree)  # the tree itself
        with pytest.raises(RealDataRefusedError, match="refused real/protected path"):
            refuse_real_path(root / tree / "run" / "x.json")  # a leaf that does not exist yet
    # A guard that refuses everything proves nothing: both verdicts must occur.
    refuse_real_path(root / "harmless" / "out.json")


def test_forbidden_operations_refused() -> None:
    for op in (
        "read_real_data",
        "derive_real_m15",
        "train",
        "evaluate_validation",
        "evaluate_holdout",
        "execute",
        "write_model_binary",
        "adopt_forward_epoch",
    ):
        with pytest.raises(RealDataRefusedError):
            assert_no_forbidden_operation(**{op: True})


def test_unknown_operation_flag_refused() -> None:
    with pytest.raises(RealDataRefusedError):
        assert_no_forbidden_operation(some_unknown_op=True)


def test_no_forbidden_operation_when_all_false() -> None:
    assert_no_forbidden_operation(train=False, execute=False)  # no-op, no raise


def test_forbidden_statuses_refused() -> None:
    for s in (
        "NEW_EPOCH_ADOPTED",
        "BYTE_ADMISSIBLE",
        "PRODUCTION_READY",
        "MEETS",
        "M15_AUTHORISED",
    ):
        with pytest.raises(RealDataRefusedError):
            assert_status_allowed(s)


def test_allowed_status_ok() -> None:
    assert_status_allowed("M15_AGGREGATION_DATASET_MACHINERY_IMPLEMENTED_SYNTHETIC_ONLY_NO_RUN")
