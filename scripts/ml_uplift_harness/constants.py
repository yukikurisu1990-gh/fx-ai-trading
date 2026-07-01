"""Controlled vocabulary + defaults for the ML uplift harness (synthetic-only)."""

from __future__ import annotations

from typing import Final

CONTRACT_VERSION: Final[str] = "ml-uplift-harness.v1"

# Candidate spans a contract may *reference* (real data is NOT read in this PR).
ALLOWED_CANDIDATE_SPANS: Final[frozenset[str]] = frozenset({"365d_BA", "730d_BA", "3650d_BA"})

# --- Controlled harness statuses ---
STATUS_CONTRACT_VALIDATED: Final[str] = "HARNESS_CONTRACT_VALIDATED_SYNTHETIC_ONLY"
STATUS_REPORT_SHAPE_VALIDATED: Final[str] = "HARNESS_REPORT_SHAPE_VALIDATED_SYNTHETIC_ONLY"
STATUS_REAL_EXPERIMENT_NOT_AUTHORISED: Final[str] = "REAL_EXPERIMENT_NOT_AUTHORISED"
STATUS_REAL_DATA_READ_NOT_AUTHORISED: Final[str] = "REAL_DATA_READ_NOT_AUTHORISED"
STATUS_MODEL_TRAINING_NOT_AUTHORISED: Final[str] = "MODEL_TRAINING_NOT_AUTHORISED"
STATUS_BACKTEST_NOT_AUTHORISED: Final[str] = "BACKTEST_NOT_AUTHORISED"
STATUS_TRADING_METRICS_NOT_COMPUTED: Final[str] = "TRADING_METRICS_NOT_COMPUTED"
STATUS_T2_NOT_AUTHORISED: Final[str] = "T2_NOT_AUTHORISED"
STATUS_BYTE_ADMISSIBILITY_NOT_APPROVED: Final[str] = "BYTE_ADMISSIBILITY_NOT_APPROVED"
STATUS_NEW_EPOCH_NOT_AUTHORISED: Final[str] = "NEW_EPOCH_NOT_AUTHORISED"
STATUS_PRODUCTION_CHANGE_NOT_AUTHORISED: Final[str] = "PRODUCTION_CHANGE_NOT_AUTHORISED"

HARNESS_STATUSES: Final[tuple[str, ...]] = (
    STATUS_CONTRACT_VALIDATED,
    STATUS_REPORT_SHAPE_VALIDATED,
    STATUS_REAL_EXPERIMENT_NOT_AUTHORISED,
    STATUS_REAL_DATA_READ_NOT_AUTHORISED,
    STATUS_MODEL_TRAINING_NOT_AUTHORISED,
    STATUS_BACKTEST_NOT_AUTHORISED,
    STATUS_TRADING_METRICS_NOT_COMPUTED,
    STATUS_T2_NOT_AUTHORISED,
    STATUS_BYTE_ADMISSIBILITY_NOT_APPROVED,
    STATUS_NEW_EPOCH_NOT_AUTHORISED,
    STATUS_PRODUCTION_CHANGE_NOT_AUTHORISED,
)

# --- Synthetic markers stamped into every synthetic report ---
MARKER_SYNTHETIC_ONLY: Final[str] = "SYNTHETIC_ONLY"
MARKER_NOT_REAL_EVIDENCE: Final[str] = "NOT_REAL_EXPERIMENT_EVIDENCE"
MARKER_NO_MODEL_RUN: Final[str] = "NO_MODEL_RUN"
MARKER_NO_BACKTEST: Final[str] = "NO_BACKTEST"
MARKER_NO_TRADING_METRICS: Final[str] = "NO_TRADING_METRICS"
SYNTHETIC_MARKERS: Final[tuple[str, ...]] = (
    MARKER_SYNTHETIC_ONLY,
    MARKER_NOT_REAL_EVIDENCE,
    MARKER_NO_MODEL_RUN,
    MARKER_NO_BACKTEST,
    MARKER_NO_TRADING_METRICS,
)

# --- Non-authorisation flags (all False in this PR) ---
NON_AUTHORISATION_FLAGS: Final[tuple[str, ...]] = (
    "real_data_read",
    "feature_generation_performed",
    "label_generation_performed",
    "model_training_performed",
    "model_inference_performed",
    "backtest_performed",
    "sweep_performed",
    "replay_performed",
    "trading_metrics_computed",
    "t2_execution_authorised",
    "byte_admissibility_approved",
    "new_epoch_adoption_authorised",
    "production_change_authorised",
    "llm_integration_authorised",
)

# Flags that MUST be False for a contract to validate in this PR (fail-closed).
MUST_BE_FALSE_FLAGS: Final[tuple[str, ...]] = (
    "real_data_authorised",
    *NON_AUTHORISATION_FLAGS,
)

# --- Tokens that must NEVER appear in a harness report ---
FORBIDDEN_REPORT_TOKENS: Final[tuple[str, ...]] = (
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

# --- Performance / trading-metric keys forbidden in any harness output ---
FORBIDDEN_METRIC_KEYS: Final[frozenset[str]] = frozenset(
    {
        "sharpe",
        "pnl",
        "ic",
        "mi",
        "expectancy",
        "expected_value",
        "win_rate",
        "drawdown",
        "ranking_performance",
        "precision_at_k",
        "auc",
        "calibration",
    }
)

# Path segments that must never appear in a harness input/output path (real
# market data / archives). The harness reads NO such paths.
FORBIDDEN_PATH_SEGMENTS: Final[tuple[str, ...]] = (
    "data",
    "oanda_archive",
    "candles",
    ".jsonl",
    ".parquet",
    ".csv",
    "firstrun_365d_ba",
    "firstrun_730d_ba",
    "firstrun_3650d_ba",
)
