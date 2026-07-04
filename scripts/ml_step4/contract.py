"""Frozen ML Step 4 contract configuration + deterministic hashes.

Every element of the PR #407 / PR #408 champion configuration is bound here to
an existing committed convention (no invented parameters). Nothing in this
module may be changed at execution time; a future execution PR reads these
frozen values and either runs exactly this contract or stops.

Three deterministic hashes are exposed so a future run's provenance chain
(F-5) is reproducible:

  * ``config_hash``          — the whole frozen contract;
  * ``feature_config_hash``  — the feature-set descriptor (v4 base only);
  * ``model_config_hash``    — the LightGBM model descriptor.

All hashes are SHA-256 over canonical JSON (``sort_keys=True``, compact
separators). Same inputs → byte-identical hash (determinism invariant).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Final

# --- Statuses ---------------------------------------------------------------
IMPLEMENTATION_STATUS: Final[str] = "ML_STEP4_CONTRACT_EXECUTOR_IMPLEMENTED_NO_RUN"
EXECUTION_NOT_PERFORMED: Final[str] = "ML_STEP4_EXECUTION_NOT_PERFORMED"
PRODUCTION_NOT_CLAIMED: Final[str] = "PRODUCTION_READINESS_NOT_CLAIMED"

# Forbidden final-status labels (may appear ONLY in this prohibition list).
FORBIDDEN_STATUS_LABELS: Final[tuple[str, ...]] = (
    "PASS",
    "Tier 1",
    "TIER_1",
    "FORMALLY_VERIFIED",
    "BYTE_ADMISSIBLE",
    "BYTE_ADMISSIBILITY_APPROVED",
    "NEW_EPOCH_ADOPTED",
    "ML_STEP4_AUTHORISED",
    "PRODUCTION_READY",
)

# --- Bound epoch ------------------------------------------------------------
EPOCH_ID: Final[str] = "RESEARCH_FROZEN_HOLDOUT_EPOCH_365D_BA_V1"
SPAN: Final[str] = "365d_BA"
EXPECTED_FILE_COUNT: Final[int] = 20
EXPECTED_TOTAL_BYTES: Final[int] = 1_481_715_517
PR_B1_INVENTORY_PATH: Final[str] = (
    "artifacts/gate_p1_pr_b/firstrun_365d_ba/raw_inventory_365d_BA.json"
)

# --- Label contract (B-2 bid/ask triple-barrier) ----------------------------
MODEL_FAMILY: Final[str] = "lightgbm_multiclass_3class"
HORIZON_M1_BARS: Final[int] = 20
TP_MULT_ATR14: Final[float] = 1.5
SL_MULT_ATR14: Final[float] = 1.0
ATR_PERIOD: Final[int] = 14
ATR_MIN_PERIODS: Final[int] = 14
SL_FIRST_TIE: Final[str] = "sl_first_strict_lt"

# --- Feature set ------------------------------------------------------------
FEATURE_VERSION: Final[str] = "v4"
FEATURE_BASE_ONLY: Final[bool] = True
# Opt-in groups that MUST be excluded from this first Step 4.
EXCLUDED_FEATURE_GROUPS: Final[tuple[str, ...]] = ("mtf", "vol", "moments")
ENABLED_FEATURE_GROUPS: Final[tuple[str, ...]] = ()  # base only

# --- Split ------------------------------------------------------------------
COMMON_WINDOW_START_UTC: Final[str] = "2025-04-25T17:09:00Z"
COMMON_WINDOW_END_UTC: Final[str] = "2026-04-24T20:58:00Z"
SPLIT_FRACTIONS: Final[tuple[float, float, float]] = (0.70, 0.15, 0.15)
PURGE_EMBARGO_BARS: Final[int] = HORIZON_M1_BARS + 1  # 21

# --- Thresholds -------------------------------------------------------------
THRESHOLD_CANDIDATES: Final[tuple[float, float, float]] = (0.35, 0.40, 0.45)
PRODUCTION_DEFAULT_THRESHOLD: Final[float] = 0.40
MAX_CONFIGURATIONS: Final[int] = 3  # 3 validation threshold variants; 1 on holdout

# --- Cost cells -------------------------------------------------------------
PRIMARY_COST_CELL_PIPS: Final[float] = 0.5
DIAGNOSTIC_COST_CELLS_PIPS: Final[tuple[float, float]] = (0.0, 1.0)
ALL_COST_CELLS_PIPS: Final[tuple[float, ...]] = (0.0, 0.5, 1.0)

# --- Position sizing / concurrency ------------------------------------------
STAKE_UNITS_PER_TRADE: Final[float] = 1.0
NON_COMPOUNDING: Final[bool] = True
MAX_OPEN_POSITIONS_PER_PAIR: Final[int] = 1
PNL_UNIT: Final[str] = "pips_post_cost"
TRADING_DAYS_PER_YEAR: Final[int] = 252

# --- Frozen LightGBM params (PR #411 B-1 fix) --------------------------------
# PR #407 §4 binds hyperparameters to the TRAINER's committed defaults
# (scripts/train_lgbm_models.py: _LGBM_PARAMS + _N_ESTIMATORS), frozen — no
# invented parameters. These literals MUST equal the trainer's; a test pins
# them against the trainer source (AST-parsed, no import).
LGBM_PARAMS: Final[dict[str, Any]] = {
    "learning_rate": 0.05,
    "num_leaves": 31,
    "verbose": -1,
}
LGBM_N_ESTIMATORS: Final[int] = 200
LGBM_OBJECTIVE: Final[str] = "multiclass"
LGBM_NUM_CLASS: Final[int] = 3
CALIBRATION: Final[str] = "none_raw_predict_proba"
# Seed / determinism decision (PR #411 B-1): the bound trainer convention has
# NO random_state, so this frozen contract does not invent one. Determinism
# handling (seed capture / thread settings) is an explicit responsibility of
# the future guarded execute() wiring PR, where it must be declared and
# recorded in the run provenance — never silently added here.

# --- Acceptance criteria (PR #407 §10 / PR #408 §5, binding lower bounds) -----
ACCEPTANCE_CRITERIA: Final[dict[str, Any]] = {
    "min_holdout_trades": 300,
    "min_daily_coverage_frac": 0.60,
    "min_post_cost_expectancy_pips": 0.0,  # strictly > 0
    "min_daily_portfolio_sharpe_annualised": 0.8,
    "max_equity_drawdown_frac": 0.15,
    "max_turnover_trades_per_day": 40.0,
    "max_pair_trade_share": 0.40,
    "max_pair_positive_pnl_share": 0.50,
    "cost_sensitivity_min_expectancy_at_1pip": 0.0,  # >= 0
    "session_concentration": "diagnostic_only",
    "provenance": "complete_per_pr407_section_7",
}

# --- Forbidden scope --------------------------------------------------------
FORBIDDEN_SCOPE: Final[tuple[str, ...]] = (
    "730d_BA",
    "3650d_BA",
    "phase_c2",
    "extra_model_families",
    "deployed_models_lgbm_reuse",
    "broad_hyperparameter_search",
    "holdout_threshold_tuning",
    "pair_session_filters",
    "google_drive",
    "r2",
)


class ContractViolationError(ValueError):
    """Raised when a requested configuration deviates from the frozen contract."""


def _canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256_hex(obj: Any) -> str:
    return hashlib.sha256(_canonical(obj).encode("utf-8")).hexdigest()


def feature_config() -> dict[str, Any]:
    """Deterministic feature-set descriptor for the frozen contract."""
    return {
        "feature_version": FEATURE_VERSION,
        "base_only": FEATURE_BASE_ONLY,
        "enabled_groups": sorted(ENABLED_FEATURE_GROUPS),
        "excluded_groups": sorted(EXCLUDED_FEATURE_GROUPS),
    }


def model_config() -> dict[str, Any]:
    """Deterministic model descriptor for the frozen contract."""
    return {
        "family": MODEL_FAMILY,
        "objective": LGBM_OBJECTIVE,
        "num_class": LGBM_NUM_CLASS,
        "params": dict(sorted(LGBM_PARAMS.items())),
        "n_estimators": LGBM_N_ESTIMATORS,
        "calibration": CALIBRATION,
        "retrain_from_scratch": True,
        "deployed_model_reuse": False,
        "hyperparameter_search": "none",
        # No random_seed here: the bound trainer convention defines none
        # (PR #411 B-1). Determinism is declared at the wiring PR / runtime.
        "seed_policy": "wiring_pr_responsibility_trainer_defines_none",
    }


def contract_dict() -> dict[str, Any]:
    """The whole frozen contract as a canonical, hashable dict."""
    return {
        "epoch_id": EPOCH_ID,
        "span": SPAN,
        "expected_file_count": EXPECTED_FILE_COUNT,
        "expected_total_bytes": EXPECTED_TOTAL_BYTES,
        "pr_b1_inventory_path": PR_B1_INVENTORY_PATH,
        "label": {
            "scheme": "b2_bid_ask_triple_barrier",
            "tp_mult_atr14": TP_MULT_ATR14,
            "sl_mult_atr14": SL_MULT_ATR14,
            "atr_period": ATR_PERIOD,
            "atr_min_periods": ATR_MIN_PERIODS,
            "sl_first_tie": SL_FIRST_TIE,
            "horizon_m1_bars": HORIZON_M1_BARS,
        },
        "feature_config": feature_config(),
        "model_config": model_config(),
        "split": {
            "common_window_start_utc": COMMON_WINDOW_START_UTC,
            "common_window_end_utc": COMMON_WINDOW_END_UTC,
            "fractions": list(SPLIT_FRACTIONS),
            "purge_embargo_bars": PURGE_EMBARGO_BARS,
        },
        "threshold_candidates": list(THRESHOLD_CANDIDATES),
        "cost_cells_pips": {
            "primary": PRIMARY_COST_CELL_PIPS,
            "diagnostics": list(DIAGNOSTIC_COST_CELLS_PIPS),
        },
        "position": {
            "stake_units_per_trade": STAKE_UNITS_PER_TRADE,
            "non_compounding": NON_COMPOUNDING,
            "max_open_positions_per_pair": MAX_OPEN_POSITIONS_PER_PAIR,
            "pnl_unit": PNL_UNIT,
        },
        "acceptance_criteria": ACCEPTANCE_CRITERIA,
        "forbidden_scope": list(FORBIDDEN_SCOPE),
        "max_configurations": MAX_CONFIGURATIONS,
    }


def config_hash() -> str:
    """Deterministic SHA-256 of the whole frozen contract."""
    return _sha256_hex(contract_dict())


def feature_config_hash() -> str:
    """Deterministic SHA-256 of the feature-set descriptor."""
    return _sha256_hex(feature_config())


def model_config_hash() -> str:
    """Deterministic SHA-256 of the model descriptor."""
    return _sha256_hex(model_config())


def assert_model_family(family: str) -> None:
    """Fail closed if a non-contract model family is requested."""
    if family != MODEL_FAMILY:
        raise ContractViolationError(
            f"model family {family!r} is not the pre-registered "
            f"{MODEL_FAMILY!r} (extra families are forbidden)"
        )


def assert_no_deployed_model_reuse(model_path: str | None) -> None:
    """Fail closed if a deployed models/lgbm/ artifact would be reused."""
    if model_path is None:
        return
    normalised = str(model_path).replace("\\", "/").lower()
    if "models/lgbm" in normalised:
        raise ContractViolationError(
            "deployed models/lgbm/ reuse is forbidden (retrain from scratch)"
        )


def assert_feature_groups(enabled: object) -> tuple[str, ...]:
    """Validate requested opt-in feature groups; base-only is the only legal set.

    Any non-empty group set (including the excluded ``mtf``/``vol``/``moments``
    or any unknown group) fails closed.
    """
    try:
        requested = tuple(sorted(str(g) for g in enabled))  # type: ignore[union-attr]
    except TypeError as exc:  # pragma: no cover - defensive
        raise ContractViolationError(f"feature groups not iterable: {enabled!r}") from exc
    if requested:
        raise ContractViolationError(
            f"opt-in feature groups {list(requested)} are excluded from this "
            f"first Step 4 (v4 base only); enabled must be empty"
        )
    return ()


@dataclass(frozen=True)
class ContractHashes:
    """Bundle of the three deterministic provenance hashes."""

    config_hash: str = field(default_factory=config_hash)
    feature_config_hash: str = field(default_factory=feature_config_hash)
    model_config_hash: str = field(default_factory=model_config_hash)

    def as_dict(self) -> dict[str, str]:
        return {
            "config_hash": self.config_hash,
            "feature_config_hash": self.feature_config_hash,
            "model_config_hash": self.model_config_hash,
        }
