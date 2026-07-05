"""Feature generation for the ML Step 4 run body.

Two strictly separated paths:

* **Production binding (identity only here):** the real run's bulk v4-base
  feature computation is bound to the committed trainer convention
  (``scripts.train_lgbm_models``: ``_add_features`` + ``_add_upper_tf_features``
  restricted to ``_FEATURE_COLS`` — FEATURE_VERSION v4 base, opt-in groups
  excluded). ``load_production_feature_builder()`` lazily imports that module
  (pandas/lightgbm stack) and is NOT invoked anywhere in this build's tests —
  invoking it on real data is the future execution PR's job.
* **Fixture path (used in tests):** ``compute_fixture_features`` — a tiny,
  pure-Python, strictly causal feature builder used ONLY to rehearse the
  pipeline plumbing on synthetic bars. It is explicitly NOT the production v4
  feature set and is labeled as such in every manifest it touches.

Both paths record the contract feature descriptor (v4 base only) so drift is
visible in provenance.
"""

from __future__ import annotations

from typing import Any, Final

from . import contract

FIXTURE_FEATURE_NAMES: Final[tuple[str, ...]] = (
    "ret_1",
    "ret_5",
    "roll_mean_10",
    "roll_vol_10",
    "hl_range",
)

PRODUCTION_FEATURE_BUILDER_ID: Final[str] = (
    "scripts.train_lgbm_models._add_features+_add_upper_tf_features/_FEATURE_COLS"
)


class FeatureContractError(ValueError):
    """Raised when the feature path violates the frozen feature contract."""


def feature_binding() -> dict[str, Any]:
    """Provenance record: contract descriptor + bound production builder."""
    fc = contract.feature_config()
    if fc["feature_version"] != "v4" or not fc["base_only"] or fc["enabled_groups"]:
        raise FeatureContractError(f"feature contract drifted: {fc}")
    return {
        "contract_feature_config": fc,
        "feature_config_hash": contract.feature_config_hash(),
        "production_builder": PRODUCTION_FEATURE_BUILDER_ID,
        "fixture_builder": "scripts.ml_step4.features.compute_fixture_features",
        "fixture_builder_is_production_v4": False,
    }


def load_production_feature_builder():  # pragma: no cover - future execution only
    """Lazily import the committed trainer bulk feature builder (heavy deps).

    NOT called in this build's tests or CI. The future first-run execution PR
    invokes this on real data after its own gates.
    """
    from scripts import train_lgbm_models as trainer

    return {
        "add_features": trainer._add_features,
        "add_upper_tf_features": trainer._add_upper_tf_features,
        "feature_cols": list(trainer._FEATURE_COLS),
    }


def compute_fixture_features(bars: list[dict]) -> tuple[list[list[float]], list[str]]:
    """Deterministic, strictly causal fixture features (NOT production v4).

    Row i uses ONLY bars ``<= i`` (no lookahead): 1-bar and 5-bar mid returns,
    10-bar rolling mean deviation and volatility, and the current bar's mid
    high-low range. Warmup rows are zero-filled (deterministic).
    """
    mids = [(b["bid_c"] + b["ask_c"]) / 2.0 for b in bars]
    rows: list[list[float]] = []
    for i in range(len(bars)):
        ret_1 = mids[i] - mids[i - 1] if i >= 1 else 0.0
        ret_5 = mids[i] - mids[i - 5] if i >= 5 else 0.0
        window = mids[max(0, i - 9) : i + 1]
        mean10 = sum(window) / len(window)
        var10 = sum((m - mean10) ** 2 for m in window) / len(window)
        hl = ((bars[i]["bid_h"] + bars[i]["ask_h"]) / 2.0) - (
            (bars[i]["bid_l"] + bars[i]["ask_l"]) / 2.0
        )
        rows.append([ret_1, ret_5, mids[i] - mean10, var10**0.5, hl])
    return rows, list(FIXTURE_FEATURE_NAMES)


# ---------------------------------------------------------------------------
# Production v4-BASE feature computation (first-run execution only)
# ---------------------------------------------------------------------------
#
# CONTRACT NOTE: PR #407 §4 requires "FEATURE_VERSION v4 BASE only — opt-in
# groups (mtf, vol, moments) EXCLUDED". The committed trainer's _FEATURE_COLS
# is 45 columns and INCLUDES the 6-feature MTF group (h4/d1/w1) because the
# DEPLOYED models enable mtf. The first-run therefore uses ONLY the 39 base
# columns (15 M1 + 24 M5/M15/H1 upper-TF) and NEVER calls _add_mtf_features.

V4_BASE_M1_COLS: Final[tuple[str, ...]] = (
    "atr_14",
    "bb_lower",
    "bb_middle",
    "bb_pct_b",
    "bb_upper",
    "bb_width",
    "ema_12",
    "ema_26",
    "last_close",
    "macd_histogram",
    "macd_line",
    "macd_signal",
    "rsi_14",
    "sma_20",
    "sma_50",
)
V4_BASE_UPPER_TF_COLS: Final[tuple[str, ...]] = (
    "m5_return_1",
    "m5_return_3",
    "m5_volatility",
    "m5_rsi_14",
    "m5_ma_slope",
    "m5_bb_pct_b",
    "m5_trend_slope",
    "m5_trend_dir",
    "m15_return_1",
    "m15_return_3",
    "m15_volatility",
    "m15_rsi_14",
    "m15_ma_slope",
    "m15_bb_pct_b",
    "m15_trend_slope",
    "m15_trend_dir",
    "h1_return_1",
    "h1_return_3",
    "h1_volatility",
    "h1_rsi_14",
    "h1_ma_slope",
    "h1_bb_pct_b",
    "h1_trend_slope",
    "h1_trend_dir",
)
V4_BASE_FEATURE_COLS: Final[tuple[str, ...]] = V4_BASE_M1_COLS + V4_BASE_UPPER_TF_COLS  # 39
# The 6 opt-in MTF columns that MUST NOT appear in the first-run feature set.
_EXCLUDED_MTF_COLS: Final[tuple[str, ...]] = (
    "h4_atr_14",
    "d1_return_3",
    "d1_range_pct",
    "d1_atr_14",
    "w1_return_1",
    "w1_range_pct",
)


def production_feature_binding() -> dict[str, Any]:
    """Provenance for the production v4-base feature wiring (identity + hash)."""
    fc = contract.feature_config()
    if fc["feature_version"] != "v4" or not fc["base_only"] or fc["enabled_groups"]:
        raise FeatureContractError(f"feature contract drifted: {fc}")
    return {
        "feature_version": "v4_base_only",
        "feature_config_hash": contract.feature_config_hash(),
        "builders": "scripts.train_lgbm_models._add_features + _add_upper_tf_features",
        "mtf_excluded": True,
        "excluded_groups": ["mtf", "vol", "moments"],
        "feature_cols": list(V4_BASE_FEATURE_COLS),
        "n_features": len(V4_BASE_FEATURE_COLS),
        "deployed_FEATURE_COLS_note": "trainer _FEATURE_COLS (45) adds the opt-in "
        "mtf group; excluded here per PR #407 §4",
    }


def compute_production_v4_base(df):
    """Add v4-BASE features to a pair DataFrame; return (df, cols). Fail-closed.

    Calls ONLY the two committed base builders (never `_add_mtf_features`),
    then asserts exactly the 39 base columns are present and no excluded MTF
    column leaked. NaN filling is left to the caller (train/predict fillna 0.0)
    to mirror the trainer.
    """
    from scripts import train_lgbm_models as trainer  # lazy: builders only

    df = trainer._add_features(df)
    df = trainer._add_upper_tf_features(df)
    missing = [c for c in V4_BASE_FEATURE_COLS if c not in df.columns]
    if missing:
        raise FeatureContractError(f"v4-base features missing: {missing}")
    leaked = [c for c in _EXCLUDED_MTF_COLS if c in df.columns]
    if leaked:
        raise FeatureContractError(f"excluded MTF features present (contract violation): {leaked}")
    return df, list(V4_BASE_FEATURE_COLS)
