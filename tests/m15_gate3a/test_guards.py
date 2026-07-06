"""Refusal guard tests — synthetic-only machinery must fail closed."""

from __future__ import annotations

import pytest

from scripts.m15_gate3a.guards import (
    RealDataRefusedError,
    assert_no_forbidden_operation,
    assert_status_allowed,
    assert_synthetic_only,
    refuse_real_path,
)


def test_synthetic_modes_allowed_real_refused() -> None:
    assert_synthetic_only("synthetic")
    assert_synthetic_only("fixture")
    for bad in ("real", "production", "live", "demo"):
        with pytest.raises(RealDataRefusedError):
            assert_synthetic_only(bad)


def test_real_protected_paths_refused() -> None:
    for p in (
        "artifacts/ml_step4/365d_ba_v1/first_run_181dc52f3a08/x.json",
        "artifacts/gate_p1_pr_b/firstrun_365d_ba/raw_inventory_365d_BA.json",
    ):
        with pytest.raises(RealDataRefusedError):
            refuse_real_path(p)


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
