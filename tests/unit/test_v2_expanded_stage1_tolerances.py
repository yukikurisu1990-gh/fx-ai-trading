"""Stage 1 unit tests — tolerance registry immutability + F-1 vs drift separation."""

from __future__ import annotations

import pytest

from scripts._verification_harness import tolerances as T  # noqa: N812


def test_f1_n_trades_exact():
    assert T.F1_N_TRADES_EXPECTED == 34_626
    assert T.F1_N_TRADES_TOL == 0  # exact


def test_f1_sharpe_tolerance_strict():
    assert pytest.approx(-0.1732, abs=1e-12) == T.F1_SHARPE_EXPECTED
    assert pytest.approx(1e-4, abs=1e-12) == T.F1_SHARPE_TOL


def test_f1_ann_pnl_tolerance_pip():
    assert pytest.approx(-204_664.4, abs=1e-6) == T.F1_ANN_PNL_EXPECTED
    assert pytest.approx(0.5, abs=1e-12) == T.F1_ANN_PNL_TOL_PIP


def test_f1_val_sharpe_diagnostic_only():
    assert pytest.approx(-0.1863, abs=1e-12) == T.F1_VAL_SHARPE_DIAGNOSTIC_VALUE
    assert T.F1_VAL_SHARPE_HALT_PARTICIPATION is False


def test_drift_tolerances_present_and_distinct_from_f1():
    assert T.DRIFT_N_TRADES_TOL == 100
    assert pytest.approx(5e-3, abs=1e-12) == T.DRIFT_SHARPE_TOL
    assert pytest.approx(0.005, abs=1e-12) == T.DRIFT_ANN_PNL_TOL_PCT
    # F-1 vs drift separation — registry-level distinction
    assert T.F1_N_TRADES_TOL != T.DRIFT_N_TRADES_TOL
    assert T.F1_SHARPE_TOL != T.DRIFT_SHARPE_TOL


def test_sentinel_tolerances():
    assert pytest.approx(5e-3, abs=1e-12) == T.SPEARMAN_TOL
    assert T.ROW_COUNT_TOL == 10
    assert pytest.approx(5e-3, abs=1e-12) == T.VAL_SHARPE_TOL_SENTINEL


def test_assert_f1_does_not_reuse_drift_tolerance_passes():
    # Compile-time assertion: must not raise.
    T.assert_f1_does_not_reuse_drift_tolerance()


def test_size_guard_constant_95_mb():
    assert T.ARTIFACT_SIZE_GUARD_BYTES == 95 * 1024 * 1024


def test_schema_version():
    assert T.V2_EXPANDED_SCHEMA_VERSION == "v2-expanded-1.0"
