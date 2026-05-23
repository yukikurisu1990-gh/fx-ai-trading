"""Tolerance registry for Tabular Targeted Verification V2-expanded.

Constants are α-fixed by PR #357 + PR #358 amendment §A.1 + §7.2 (as amended).
Stage 1 implementation: constants only; no logic that performs verification.

Per amendment §A.1 (binding):

  Phase 28 §10 immutable baseline FAIL-FAST uses the inherited baseline-
  reproduction contract — strict tolerances ONLY. The control-drift
  tolerance (±100 / ±5e-3 / ±0.5%) is reserved for historic control drift
  diagnostic and MUST NEVER be reused for F-1 baseline FAIL-FAST.

Modification of any constant in this module triggers contract_hash mismatch
HALT in the orchestrator (Stage 2/3).
"""

from __future__ import annotations

from typing import Final

# ---------------------------------------------------------------------------
# F-1 strict Phase 28 §10 baseline FAIL-FAST (amendment §A.1; binding)
# ---------------------------------------------------------------------------

F1_N_TRADES_EXPECTED: Final[int] = 34_626
F1_N_TRADES_TOL: Final[int] = 0  # EXACT (±0)

F1_SHARPE_EXPECTED: Final[float] = -0.1732
F1_SHARPE_TOL: Final[float] = 1e-4  # ±1e-4 (NOT ±5e-3)

F1_ANN_PNL_EXPECTED: Final[float] = -204_664.4
F1_ANN_PNL_TOL_PIP: Final[float] = 0.5  # ±0.5 pip (NOT ±0.5%)

# val Sharpe -0.1863 is DIAGNOSTIC-ONLY by default per amendment §A.1.
# No HALT participation unless a merge-SHA contract explicitly binds it.
F1_VAL_SHARPE_DIAGNOSTIC_VALUE: Final[float] = -0.1863
F1_VAL_SHARPE_HALT_PARTICIPATION: Final[bool] = False  # DIAGNOSTIC-ONLY

# ---------------------------------------------------------------------------
# Control-chain drift tolerance (sentinel cells only; NEVER F-1)
# ---------------------------------------------------------------------------

DRIFT_N_TRADES_TOL: Final[int] = 100
DRIFT_SHARPE_TOL: Final[float] = 5e-3
DRIFT_ANN_PNL_TOL_PCT: Final[float] = 0.005  # ±0.5% of magnitude

# ---------------------------------------------------------------------------
# Per-cell sentinel tolerances
# ---------------------------------------------------------------------------

SPEARMAN_TOL: Final[float] = 5e-3  # S-1 Spearman +0.4381 reproduction
ROW_COUNT_TOL: Final[int] = 10  # S-2 Fix A per-cell row counts
VAL_SHARPE_TOL_SENTINEL: Final[float] = 5e-3  # sentinel val Sharpe (NOT F-1)

# ---------------------------------------------------------------------------
# Artifact size guard (amendment §A.5; binding)
# ---------------------------------------------------------------------------

ARTIFACT_SIZE_GUARD_BYTES: Final[int] = 95 * 1024 * 1024  # 95 MB; HALT if any
# single required committed file exceeds this size before PR creation.

# ---------------------------------------------------------------------------
# Schema version (binding for Stage 1 artifacts; future stages must match)
# ---------------------------------------------------------------------------

V2_EXPANDED_SCHEMA_VERSION: Final[str] = "v2-expanded-1.0"


def assert_f1_does_not_reuse_drift_tolerance() -> None:
    """Compile-time assertion: F-1 tolerance constants are distinct from drift.

    Per amendment §A.1: control-drift tolerance MUST NEVER be reused for F-1
    baseline FAIL-FAST. This module provides the registry; the actual usage
    enforcement is in sentinel_runner (Stage 2) which calls F-1 with the
    F1_* constants and sentinel drift checks with the DRIFT_* constants.

    Stage 1 enforces the registry-level distinction by exposing these as
    separate named constants (cannot accidentally swap one for the other).
    """
    # Sanity invariants that hold by construction:
    assert F1_N_TRADES_TOL != DRIFT_N_TRADES_TOL  # 0 vs 100
    assert F1_SHARPE_TOL != DRIFT_SHARPE_TOL  # 1e-4 vs 5e-3
    # F1_ANN_PNL_TOL_PIP (absolute pip) is a different unit from
    # DRIFT_ANN_PNL_TOL_PCT (fraction of magnitude); cannot be conflated.
