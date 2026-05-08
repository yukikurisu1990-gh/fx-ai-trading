"""Stage 25.0c-β — F2 multi-timeframe volatility regime eval.

Implements the binding contract from PR #286 (25.0c-α
docs/design/phase25_0c_f2_design.md). Reads 25.0a-β path-quality
labels, builds F2 categorical multi-TF volatility regime features,
trains 18 cells of logistic regression with chronological 70/15/15
split, selects trade threshold on validation only, evaluates test
ONCE with realised barrier PnL via M1 path re-traverse.

MANDATORY CLAUSES (verbatim per 25.0c-α §12):

1. Phase 25 framing.
   Phase 25 is not a hyperparameter-tuning phase. It is a label-and-
   feature-class redesign phase. Novelty must come from input feature
   class and label design.

2. F2 negative list (binding).
   F2 features are CATEGORICAL multi-TF volatility regime tags. F2 is
   NOT continuous vol-derivative magnitudes (that's F1, REJECT_BUT_
   INFORMATIVE per PR #284 — see scope review PR #285). Raw RV, raw
   expansion ratio, raw vol-of-vol, raw range compression score are
   PROHIBITED as direct model features in 25.0c. F2 is NOT a Donchian
   / z-score / Bollinger band touch / moving-average crossover /
   calibration-only signal. Recent return sign (f2_e) is secondary
   directional context only — it MUST NOT serve as a standalone
   primary trigger. The trigger uses the joint regime VECTOR,
   alignment counts, and transition events.

3. Diagnostic columns are not features.
   The 25.0a-β diagnostic columns (max_fav_excursion_pip,
   max_adv_excursion_pip, time_to_fav_bar, time_to_adv_bar,
   same_bar_both_hit) MUST NOT appear in any model's feature matrix.
   A unit test enforces this.

4. Causality and split discipline.
   All f2 features use shift(1).rolling pattern; signal bar t's own
   data MUST NOT enter feature[t]. Train / val / test splits are
   strictly chronological (70/15/15 by calendar date). Threshold
   selection uses VALIDATION ONLY; test set is touched once.

5. γ closure preservation.
   Phase 25.0c does not modify the γ closure (PR #279).

6. Production-readiness preservation.
   PROMISING_BUT_NEEDS_OOS / ADOPT_CANDIDATE in 25.0c are hypothesis-
   generating only. Production-readiness requires X-v2-equivalent
   frozen-OOS PR per Phase 22 contract.
"""

from __future__ import annotations

import argparse
import importlib
import sys
import time
import warnings
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

REPO_ROOT = Path(__file__).resolve().parent.parent
ARTIFACT_ROOT = REPO_ROOT / "artifacts" / "stage25_0c"
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

stage23_0a = importlib.import_module("stage23_0a_build_outcome_dataset")
stage25_0b = importlib.import_module("stage25_0b_f1_volatility_expansion_eval")

PAIRS_20 = stage23_0a.PAIRS_20
load_m1_ba = stage23_0a.load_m1_ba
pip_size_for = stage23_0a.pip_size_for

# Reuse from 25.0b (shared infrastructure)
load_path_quality_labels = stage25_0b.load_path_quality_labels
split_70_15_15 = stage25_0b.split_70_15_15
_compute_realised_barrier_pnl = stage25_0b._compute_realised_barrier_pnl
compute_8_gate_metrics = stage25_0b.compute_8_gate_metrics
gate_matrix = stage25_0b.gate_matrix
assign_verdict_with_h = stage25_0b.assign_verdict_with_h
calibration_quintile_check = stage25_0b.calibration_quintile_check
_proxy_pnl_per_row = stage25_0b._proxy_pnl_per_row
_select_threshold_on_val = stage25_0b._select_threshold_on_val
aggregate_m1_to_tf_local = stage25_0b.aggregate_m1_to_tf_local
_compute_rv = stage25_0b._compute_rv
_compute_return_sign = stage25_0b._compute_return_sign
PROHIBITED_DIAGNOSTIC_COLUMNS = stage25_0b.PROHIBITED_DIAGNOSTIC_COLUMNS
LOW_POWER_N_TEST = stage25_0b.LOW_POWER_N_TEST
LOW_POWER_N_TRAIN = stage25_0b.LOW_POWER_N_TRAIN

# ---------------------------------------------------------------------------
# Design constants (LOCKED from 25.0c-α §3, §5, §6, §7, §8, §9)
# ---------------------------------------------------------------------------

K_FAV = stage25_0b.K_FAV  # 1.5
K_ADV = stage25_0b.K_ADV  # 1.0
H_M1_BARS = stage25_0b.H_M1_BARS  # 60
SPAN_DAYS = stage25_0b.SPAN_DAYS  # 730

# F2 RV window (per-TF; same as F1)
RV_WINDOW = {"M5": 12, "M15": 8, "H1": 24}

# Tertile percentile boundaries (FIXED)
TERTILE_LOW = 0.33
TERTILE_HIGH = 0.66

# Cell grid (18 cells; bidirectionality LOCKED)
CELL_TRAILING_WINDOWS = (100, 200)
CELL_FEATURE_REPRESENTATIONS = ("per_tf_only", "per_tf_joint", "all")
CELL_ADMISSIBILITY_FILTERS = ("none", "high_alignment", "transition")

# Threshold candidates inherited from 25.0b
THRESHOLD_CANDIDATES = stage25_0b.THRESHOLD_CANDIDATES

# Validation split inherited
TRAIN_FRAC = stage25_0b.TRAIN_FRAC
VAL_FRAC = stage25_0b.VAL_FRAC

# 8-gate harness inherited
A1_MIN_SHARPE = stage25_0b.A1_MIN_SHARPE
A2_MIN_ANNUAL_PNL = stage25_0b.A2_MIN_ANNUAL_PNL

# Carried from F1 — used to verify NO raw F1 cols in feature matrix (HARD)
PROHIBITED_F1_RAW_COLS = (
    "f1_a_rv_M5",
    "f1_a_rv_M15",
    "f1_a_rv_H1",
    "f1_c_expansion_ratio_M5",
    "f1_c_expansion_ratio_M15",
    "f1_c_expansion_ratio_H1",
    "f1_d_vol_of_vol_M5",
    "f1_d_vol_of_vol_M15",
    "f1_d_vol_of_vol_H1",
    "f1_e_range_score_M5",
    "f1_e_range_score_M15",
    "f1_e_range_score_H1",
)

# F2 feature column lists per representation
F2_PER_TF_COLS = [
    "f2_a_regime_M5",
    "f2_a_regime_M15",
    "f2_a_regime_H1",
    "f2_e_return_sign",
]
F2_PER_TF_JOINT_COLS = F2_PER_TF_COLS + ["f2_b_joint_regime"]
F2_ALL_COLS = F2_PER_TF_JOINT_COLS + [
    "f2_c_high_count",
    "f2_c_low_count",
    "f2_d_transitioned_M5",
    "f2_d_transitioned_M15",
    "f2_d_transitioned_H1",
]

# Categorical vs numeric
F2_CATEGORICAL_COLS_BASE = (
    "f2_a_regime_M5",
    "f2_a_regime_M15",
    "f2_a_regime_H1",
    "f2_b_joint_regime",
    "f2_e_return_sign",
)
F2_NUMERIC_COLS_BASE = ("f2_c_high_count", "f2_c_low_count")
F2_BOOL_COLS_BASE = (
    "f2_d_transitioned_M5",
    "f2_d_transitioned_M15",
    "f2_d_transitioned_H1",
)

CATEGORICAL_COVARIATES = ["pair", "direction"]


# ---------------------------------------------------------------------------
# F2 feature computation (NEW; vectorized, shift(1) causal)
# ---------------------------------------------------------------------------


def _compute_tertile_boundaries(rv: pd.Series, lookback: int) -> tuple[pd.Series, pd.Series]:
    """Tertile boundaries on causal-shifted RV. Returns (q33, q66) series."""
    shifted = rv.shift(1)
    q33 = shifted.rolling(lookback).quantile(TERTILE_LOW)
    q66 = shifted.rolling(lookback).quantile(TERTILE_HIGH)
    return q33, q66


def _compute_regime_tag(rv: pd.Series, q33: pd.Series, q66: pd.Series) -> pd.Series:
    """Map shift(1)-RV into {low, med, high} tag per bar."""
    shifted = rv.shift(1)
    tag = pd.Series(np.full(len(shifted), None, dtype=object), index=shifted.index)
    valid = shifted.notna() & q33.notna() & q66.notna()
    tag.loc[valid & (shifted < q33)] = "low"
    tag.loc[valid & (shifted > q66)] = "high"
    tag.loc[valid & (shifted >= q33) & (shifted <= q66)] = "med"
    return tag


def _compute_joint_regime(m5: pd.Series, m15: pd.Series, h1: pd.Series) -> pd.Series:
    """Concat per-TF tags into joint regime string. NaN if any TF tag is NaN."""
    valid = m5.notna() & m15.notna() & h1.notna()
    out = pd.Series(np.full(len(m5), None, dtype=object), index=m5.index)
    out.loc[valid] = (
        m5.loc[valid].astype(str)
        + "_"
        + m15.loc[valid].astype(str)
        + "_"
        + h1.loc[valid].astype(str)
    )
    return out


def _compute_alignment_counts(
    m5: pd.Series, m15: pd.Series, h1: pd.Series
) -> tuple[pd.Series, pd.Series]:
    """Returns (high_count, low_count) per row."""
    high_count = (
        (m5 == "high").astype("int8")
        + (m15 == "high").astype("int8")
        + (h1 == "high").astype("int8")
    )
    low_count = (
        (m5 == "low").astype("int8") + (m15 == "low").astype("int8") + (h1 == "low").astype("int8")
    )
    return high_count, low_count


def _compute_transition_flag(regime_series: pd.Series) -> pd.Series:
    """True if regime[t] != regime[t-1] (regime tags already causal)."""
    prev = regime_series.shift(1)
    valid = regime_series.notna() & prev.notna()
    out = pd.Series(False, index=regime_series.index, dtype="bool")
    out.loc[valid] = regime_series.loc[valid] != prev.loc[valid]
    return out


def compute_f2_features_for_pair(pair: str, days: int, trailing_window: int) -> pd.DataFrame:
    """Build F2 feature DataFrame keyed by M5 signal_ts for one pair.

    Returns DataFrame with columns: pair, signal_ts, all 10 F2 features.
    NOTE: RV is computed internally to derive regime tags but is NOT
    stored in output (F2 negative list — raw continuous RV PROHIBITED).
    """
    m1 = load_m1_ba(pair, days=days)
    m5 = aggregate_m1_to_tf_local(m1, "M5")
    m15 = aggregate_m1_to_tf_local(m1, "M15")
    h1 = aggregate_m1_to_tf_local(m1, "H1")

    # Compute RV per TF (intermediate; not stored in output)
    regime_per_tf: dict[str, pd.Series] = {}
    transition_per_tf: dict[str, pd.Series] = {}
    for tf, tf_df in [("M5", m5), ("M15", m15), ("H1", h1)]:
        n_rv = RV_WINDOW[tf]
        mid_c = (tf_df["bid_c"] + tf_df["ask_c"]) / 2.0
        rv = _compute_rv(mid_c, n_rv)
        q33, q66 = _compute_tertile_boundaries(rv, trailing_window)
        tag = _compute_regime_tag(rv, q33, q66)
        regime_per_tf[tf] = tag
        transition_per_tf[tf] = _compute_transition_flag(tag)

    # Build per-TF DataFrame on M5 index (signals are at M5 boundaries)
    df_m5 = pd.DataFrame(
        {
            "f2_a_regime_M5": regime_per_tf["M5"],
            "f2_d_transitioned_M5": transition_per_tf["M5"],
        },
        index=m5.index,
    )
    # f2_e on M5
    m5_mid_c = (m5["bid_c"] + m5["ask_c"]) / 2.0
    df_m5["f2_e_return_sign"] = _compute_return_sign(m5_mid_c, 13)

    df_m15 = pd.DataFrame(
        {
            "f2_a_regime_M15": regime_per_tf["M15"],
            "f2_d_transitioned_M15": transition_per_tf["M15"],
        },
        index=m15.index,
    )
    df_h1 = pd.DataFrame(
        {
            "f2_a_regime_H1": regime_per_tf["H1"],
            "f2_d_transitioned_H1": transition_per_tf["H1"],
        },
        index=h1.index,
    )

    # Map M15/H1 features back to M5 signal_ts via merge_asof (backward)
    base = df_m5.copy()
    base["pair"] = pair
    base["signal_ts"] = base.index
    base = base.reset_index(drop=True)

    df_m15_res = df_m15.reset_index().rename(columns={df_m15.index.name or "index": "ts_m15"})
    if "ts_m15" not in df_m15_res.columns:
        df_m15_res = df_m15_res.rename(columns={df_m15_res.columns[0]: "ts_m15"})
    df_h1_res = df_h1.reset_index().rename(columns={df_h1.index.name or "index": "ts_h1"})
    if "ts_h1" not in df_h1_res.columns:
        df_h1_res = df_h1_res.rename(columns={df_h1_res.columns[0]: "ts_h1"})

    base_sorted = base.sort_values("signal_ts")
    df_m15_sorted = df_m15_res.sort_values("ts_m15")
    df_h1_sorted = df_h1_res.sort_values("ts_h1")
    merged = pd.merge_asof(
        base_sorted, df_m15_sorted, left_on="signal_ts", right_on="ts_m15", direction="backward"
    )
    merged = pd.merge_asof(
        merged, df_h1_sorted, left_on="signal_ts", right_on="ts_h1", direction="backward"
    )
    merged = merged.drop(columns=["ts_m15", "ts_h1"])

    # Compute joint regime + alignment counts on the merged df
    merged["f2_b_joint_regime"] = _compute_joint_regime(
        merged["f2_a_regime_M5"], merged["f2_a_regime_M15"], merged["f2_a_regime_H1"]
    )
    high_count, low_count = _compute_alignment_counts(
        merged["f2_a_regime_M5"], merged["f2_a_regime_M15"], merged["f2_a_regime_H1"]
    )
    merged["f2_c_high_count"] = high_count
    merged["f2_c_low_count"] = low_count

    return merged


# ---------------------------------------------------------------------------
# Cell grid (18 cells; deterministic order TF → trailing → representation → admissibility)
# ---------------------------------------------------------------------------


def _build_cells() -> list[dict]:
    cells = []
    # Note: F2 cells don't have a "TF" dimension (per 25.0c-α §5);
    # ordering is trailing → representation → admissibility.
    for tw in CELL_TRAILING_WINDOWS:
        for rep in CELL_FEATURE_REPRESENTATIONS:
            for adm in CELL_ADMISSIBILITY_FILTERS:
                cells.append({"trailing_window": tw, "representation": rep, "admissibility": adm})
    return cells


CELL_GRID = _build_cells()
assert len(CELL_GRID) == 18


# ---------------------------------------------------------------------------
# Cell admissibility filter dispatch
# ---------------------------------------------------------------------------


def _apply_admissibility_filter(df: pd.DataFrame, filter_name: str) -> pd.DataFrame:
    if filter_name == "none":
        return df
    if filter_name == "high_alignment":
        return df[df["f2_c_high_count"] >= 2]
    if filter_name == "transition":
        mask = df["f2_d_transitioned_M5"] | df["f2_d_transitioned_M15"] | df["f2_d_transitioned_H1"]
        return df[mask]
    raise ValueError(f"Unknown admissibility filter: {filter_name}")


# ---------------------------------------------------------------------------
# Cell feature representation dispatch
# ---------------------------------------------------------------------------


def _select_feature_cols(representation: str) -> list[str]:
    if representation == "per_tf_only":
        return list(F2_PER_TF_COLS)
    if representation == "per_tf_joint":
        return list(F2_PER_TF_JOINT_COLS)
    if representation == "all":
        return list(F2_ALL_COLS)
    raise ValueError(f"Unknown representation: {representation}")


# ---------------------------------------------------------------------------
# Pipeline build
# ---------------------------------------------------------------------------


def build_logistic_pipeline_f2(feature_cols: list[str]) -> Pipeline:
    """Build pipeline with categorical/numeric column dispatch.

    OneHotEncoder with handle_unknown='ignore' for unseen joint regimes.
    """
    cat_in = [c for c in feature_cols if c in F2_CATEGORICAL_COLS_BASE]
    num_in = [c for c in feature_cols if c in F2_NUMERIC_COLS_BASE]
    bool_in = [c for c in feature_cols if c in F2_BOOL_COLS_BASE]

    transformers: list[tuple] = []
    if num_in:
        transformers.append(("num", StandardScaler(), num_in))
    if bool_in:
        # Bools as passthrough (already 0/1)
        transformers.append(("bool", "passthrough", bool_in))
    transformers.append(
        (
            "cat",
            OneHotEncoder(handle_unknown="ignore", sparse_output=False),
            cat_in + CATEGORICAL_COVARIATES,
        ),
    )
    pre = ColumnTransformer(transformers)
    return Pipeline(
        [
            ("pre", pre),
            (
                "clf",
                LogisticRegression(
                    penalty="l2",
                    C=1.0,
                    class_weight="balanced",
                    solver="lbfgs",
                    max_iter=1000,
                    random_state=42,
                ),
            ),
        ]
    )


# ---------------------------------------------------------------------------
# Per-cell evaluation
# ---------------------------------------------------------------------------


def evaluate_cell(
    cell: dict,
    full_df: pd.DataFrame,
    splits: tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame],
    pair_runtime: dict,
) -> dict:
    """Train one cell, select threshold on val, evaluate test once."""
    train_full, val_full, test_full = splits
    representation = cell["representation"]
    admissibility = cell["admissibility"]
    feature_cols = _select_feature_cols(representation)

    # Apply admissibility filter
    train = _apply_admissibility_filter(train_full, admissibility).copy()
    val = _apply_admissibility_filter(val_full, admissibility).copy()
    test = _apply_admissibility_filter(test_full, admissibility).copy()

    n_train = len(train)
    n_val = len(val)
    n_test = len(test)

    # Pass-through rates
    pt_rate_train = n_train / max(len(train_full), 1)
    pt_rate_val = n_val / max(len(val_full), 1)
    pt_rate_test = n_test / max(len(test_full), 1)

    if n_train < 100 or n_val < 50 or n_test < 50:
        return {
            "cell": cell,
            "n_train": n_train,
            "n_val": n_val,
            "n_test": n_test,
            "passthrough_rates": {
                "train": pt_rate_train,
                "val": pt_rate_val,
                "test": pt_rate_test,
            },
            "test_auc": float("nan"),
            "verdict": "REJECT",
            "h_state": "INSUFFICIENT_DATA",
            "low_power": True,
            "skip_reason": "insufficient sample after admissibility filter",
        }

    x_train = train[feature_cols + CATEGORICAL_COVARIATES]
    y_train = train["label"].astype(int)
    x_val = val[feature_cols + CATEGORICAL_COVARIATES]
    y_val = val["label"].astype(int)
    x_test = test[feature_cols + CATEGORICAL_COVARIATES]
    y_test = test["label"].astype(int)

    pipeline = build_logistic_pipeline_f2(feature_cols)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        pipeline.fit(x_train, y_train)

    train_p = pipeline.predict_proba(x_train)[:, 1]
    val_p = pipeline.predict_proba(x_val)[:, 1]
    test_p = pipeline.predict_proba(x_test)[:, 1]

    def _safe_auc(y, p):
        if len(np.unique(y)) < 2:
            return float("nan")
        return float(roc_auc_score(y, p))

    train_auc = _safe_auc(y_train, train_p)
    val_auc = _safe_auc(y_val, val_p)
    test_auc = _safe_auc(y_test, test_p)

    # Bidirectional pivot for threshold selection
    val["_p"] = val_p
    val_long = val[val["direction"] == "long"].set_index(["pair", "signal_ts"])
    val_short = val[val["direction"] == "short"].set_index(["pair", "signal_ts"])
    common_idx = val_long.index.intersection(val_short.index)
    if len(common_idx) < 10:
        return {
            "cell": cell,
            "n_train": n_train,
            "n_val": n_val,
            "n_test": n_test,
            "passthrough_rates": {
                "train": pt_rate_train,
                "val": pt_rate_val,
                "test": pt_rate_test,
            },
            "test_auc": test_auc,
            "verdict": "REJECT",
            "h_state": "PIVOT_INSUFFICIENT",
            "low_power": True,
            "skip_reason": "bidirectional pivot insufficient overlap on val",
        }

    val_long_p_s = val_long.loc[common_idx, "_p"]
    val_short_p_s = val_short.loc[common_idx, "_p"]
    val_long_label_s = val_long.loc[common_idx, "label"]
    val_short_label_s = val_short.loc[common_idx, "label"]
    val_atr_s = val_long.loc[common_idx, "atr_at_signal_pip"]

    threshold, threshold_log = _select_threshold_on_val(
        val_long_p_s, val_short_p_s, val_long_label_s, val_short_label_s, val_atr_s
    )

    test["_p"] = test_p
    test_long = test[test["direction"] == "long"].set_index(["pair", "signal_ts"])
    test_short = test[test["direction"] == "short"].set_index(["pair", "signal_ts"])
    common_test_idx = test_long.index.intersection(test_short.index)
    if len(common_test_idx) < 10:
        return {
            "cell": cell,
            "n_train": n_train,
            "n_val": n_val,
            "n_test": n_test,
            "passthrough_rates": {
                "train": pt_rate_train,
                "val": pt_rate_val,
                "test": pt_rate_test,
            },
            "train_auc": train_auc,
            "val_auc": val_auc,
            "test_auc": test_auc,
            "verdict": "REJECT",
            "h_state": "TEST_PIVOT_INSUFFICIENT",
            "low_power": True,
            "skip_reason": "bidirectional pivot insufficient overlap on test",
        }
    test_long_p = test_long.loc[common_test_idx, "_p"]
    test_short_p = test_short.loc[common_test_idx, "_p"]
    test_atr = test_long.loc[common_test_idx, "atr_at_signal_pip"]
    test_long_label = test_long.loc[common_test_idx, "label"]
    test_short_label = test_short.loc[common_test_idx, "label"]

    long_traded_mask = (test_long_p >= threshold) & (test_long_p >= test_short_p)
    short_traded_mask = (test_short_p >= threshold) & (test_short_p > test_long_p)

    realised_pnls: list[float] = []
    proxy_pnls: list[float] = []
    by_pair_count: dict[str, int] = {}
    by_direction_count = {"long": 0, "short": 0}

    for (pair, signal_ts), traded in long_traded_mask.items():
        if not traded:
            continue
        atr = float(test_atr.loc[(pair, signal_ts)])
        label = int(test_long_label.loc[(pair, signal_ts)])
        proxy_pnls.append(_proxy_pnl_per_row(label, atr, True))
        if pair in pair_runtime:
            r = _compute_realised_barrier_pnl(pair, signal_ts, "long", atr, pair_runtime[pair])
            if r is not None:
                realised_pnls.append(r)
                by_pair_count[pair] = by_pair_count.get(pair, 0) + 1
                by_direction_count["long"] += 1
    for (pair, signal_ts), traded in short_traded_mask.items():
        if not traded:
            continue
        atr = float(test_atr.loc[(pair, signal_ts)])
        label = int(test_short_label.loc[(pair, signal_ts)])
        proxy_pnls.append(_proxy_pnl_per_row(label, atr, True))
        if pair in pair_runtime:
            r = _compute_realised_barrier_pnl(pair, signal_ts, "short", atr, pair_runtime[pair])
            if r is not None:
                realised_pnls.append(r)
                by_pair_count[pair] = by_pair_count.get(pair, 0) + 1
                by_direction_count["short"] += 1

    realised_arr = np.asarray(realised_pnls)
    proxy_arr = np.asarray(proxy_pnls)
    realised_metrics = compute_8_gate_metrics(realised_arr, len(realised_arr))
    gates = gate_matrix(realised_metrics)
    proxy_metrics = compute_8_gate_metrics(proxy_arr, len(proxy_arr))
    verdict, h_state = assign_verdict_with_h(test_auc, gates, len(realised_arr))
    cal = calibration_quintile_check(test_p, y_test.to_numpy())
    low_power = n_test < LOW_POWER_N_TEST or n_train < LOW_POWER_N_TRAIN

    return {
        "cell": cell,
        "n_train": n_train,
        "n_val": n_val,
        "n_test": n_test,
        "passthrough_rates": {
            "train": pt_rate_train,
            "val": pt_rate_val,
            "test": pt_rate_test,
        },
        "train_auc": train_auc,
        "val_auc": val_auc,
        "test_auc": test_auc,
        "auc_gap_train_test": (train_auc - test_auc) if np.isfinite(test_auc) else float("nan"),
        "verdict": verdict,
        "h_state": h_state,
        "threshold_selected": threshold,
        "threshold_log": threshold_log,
        "calibration": cal,
        "realised_metrics": realised_metrics,
        "proxy_metrics": proxy_metrics,
        "gates": gates,
        "by_pair_trade_count": by_pair_count,
        "by_direction_trade_count": by_direction_count,
        "low_power": low_power,
    }


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


def write_eval_report(
    out_path: Path,
    cell_results: list[dict],
    split_dates: tuple[pd.Timestamp, pd.Timestamp, pd.Timestamp, pd.Timestamp],
    feature_nan_drop_count: int,
    feature_nan_drop_rate_overall: float,
    feature_nan_drop_by_pair: dict[str, dict],
    regime_distribution: dict[str, dict],
) -> None:
    t_min, t70, t85, t_max = split_dates
    lines: list[str] = []
    lines.append("# Stage 25.0c-β — F2 Multi-Timeframe Volatility Regime Eval")
    lines.append("")
    lines.append(f"Generated: {datetime.now(UTC).isoformat()}")
    lines.append("")
    lines.append("Design contract: `docs/design/phase25_0c_f2_design.md` (PR #286)")
    lines.append("")
    lines.append("## Mandatory clauses")
    lines.append("")
    lines.append(
        "**1. Phase 25 framing.** Phase 25 is not a hyperparameter-tuning phase. "
        "It is a label-and-feature-class redesign phase. Novelty must come from "
        "input feature class and label design."
    )
    lines.append("")
    lines.append(
        "**2. F2 negative list (binding).** F2 features are CATEGORICAL multi-TF "
        "volatility regime tags. F2 is NOT continuous vol-derivative magnitudes "
        "(that's F1, REJECT_BUT_INFORMATIVE per PR #284). Raw RV, raw expansion "
        "ratio, raw vol-of-vol, raw range compression score are PROHIBITED as "
        "direct model features. f2_e (return sign) is secondary directional "
        "context only."
    )
    lines.append("")
    lines.append(
        "**3. Diagnostic columns are not features.** The 25.0a-β diagnostic "
        "columns MUST NOT appear in any model's feature matrix."
    )
    lines.append("")
    lines.append(
        "**4. Causality and split discipline.** All f2 features use shift(1)."
        "rolling pattern. Train / val / test splits are strictly chronological "
        "(70/15/15). Threshold selection uses VALIDATION ONLY; test set is "
        "touched once."
    )
    lines.append("")
    lines.append(
        "**5. γ closure preservation.** Phase 25.0c does not modify the γ closure (PR #279)."
    )
    lines.append("")
    lines.append(
        "**6. Production-readiness preservation.** PROMISING_BUT_NEEDS_OOS / "
        "ADOPT_CANDIDATE in 25.0c are hypothesis-generating only. Production-"
        "readiness requires X-v2-equivalent frozen-OOS PR."
    )
    lines.append("")
    lines.append(
        "**Test-touched-once invariant**: threshold selected on validation "
        "only; test set touched once."
    )
    lines.append("")
    lines.append("## Realised barrier PnL methodology (inherited from 25.0b-β)")
    lines.append("")
    lines.append(
        "Final test 8-gate evaluation uses realised barrier PnL via M1 path "
        "re-traverse with 25.0a barrier semantics:"
    )
    lines.append("- favourable barrier first → +K_FAV × ATR")
    lines.append("- adverse barrier first → −K_ADV × ATR")
    lines.append("- same-bar both-hit → adverse first → −K_ADV × ATR")
    lines.append("- horizon expiry → mark-to-market")
    lines.append("")
    lines.append(
        "Validation threshold selection uses synthesized PnL proxy (±K_FAV/K_ADV × ATR by label)."
    )
    lines.append("")
    lines.append("## Split dates")
    lines.append("")
    lines.append(f"- min: {t_min}")
    lines.append(f"- train < {t70}")
    lines.append(f"- val [{t70}, {t85})")
    lines.append(f"- test [{t85}, {t_max}]")
    lines.append("")
    lines.append("## Feature NaN drop")
    lines.append("")
    lines.append(
        f"- overall drop count: {feature_nan_drop_count}; rate: {feature_nan_drop_rate_overall:.4f}"
    )
    lines.append("")
    if feature_nan_drop_by_pair:
        lines.append("Per-pair feature NaN drop:")
        lines.append("")
        lines.append("| pair | drop_count | drop_rate |")
        lines.append("|---|---|---|")
        for pair, d in sorted(feature_nan_drop_by_pair.items()):
            lines.append(f"| {pair} | {d['count']} | {d['rate']:.4f} |")
        lines.append("")

    # Summary table sorted by test AUC desc
    lines.append("## All 18 cells — summary (sorted by test AUC desc)")
    lines.append("")
    lines.append(
        "| trailing | rep | admissibility | n_train | n_test | pt% (test) | "
        "train_AUC | val_AUC | test_AUC | gap | verdict | n_trades | sharpe | "
        "ann_pnl | low_power |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    sorted_by_auc = sorted(
        cell_results,
        key=lambda c: c.get("test_auc", -1) if np.isfinite(c.get("test_auc", -1)) else -1,
        reverse=True,
    )
    for c in sorted_by_auc:
        cell = c["cell"]
        rm = c.get("realised_metrics", {})
        pt = c.get("passthrough_rates", {}).get("test", float("nan"))
        lines.append(
            f"| {cell['trailing_window']} | {cell['representation']} | "
            f"{cell['admissibility']} | {c.get('n_train', 0)} | "
            f"{c.get('n_test', 0)} | {pt:.3f} | "
            f"{c.get('train_auc', float('nan')):.4f} | "
            f"{c.get('val_auc', float('nan')):.4f} | "
            f"{c.get('test_auc', float('nan')):.4f} | "
            f"{c.get('auc_gap_train_test', float('nan')):.4f} | "
            f"{c.get('verdict', '-')} | "
            f"{rm.get('n_trades', 0)} | {rm.get('sharpe', float('nan')):.4f} | "
            f"{rm.get('annual_pnl', 0.0):+.1f} | "
            f"{'YES' if c.get('low_power') else 'no'} |"
        )
    lines.append("")

    lines.append("## Top-3 cells by test AUC — expanded breakdown")
    lines.append("")
    for c in sorted_by_auc[:3]:
        cell = c["cell"]
        lines.append(
            f"### Cell: trailing={cell['trailing_window']}, "
            f"rep={cell['representation']}, adm={cell['admissibility']}"
        )
        lines.append("")
        rm = c.get("realised_metrics", {})
        pm = c.get("proxy_metrics", {})
        gates = c.get("gates", {})
        nt = c.get("n_train", 0)
        nv = c.get("n_val", 0)
        nte = c.get("n_test", 0)
        pt = c.get("passthrough_rates", {})
        lines.append(f"- n_train: {nt}, n_val: {nv}, n_test: {nte}")
        lines.append(
            f"- pass-through (train/val/test): "
            f"{pt.get('train', 0):.3f} / {pt.get('val', 0):.3f} / {pt.get('test', 0):.3f}"
        )
        lines.append(
            f"- train AUC: {c.get('train_auc', float('nan')):.4f}, "
            f"val AUC: {c.get('val_auc', float('nan')):.4f}, "
            f"test AUC: {c.get('test_auc', float('nan')):.4f}, "
            f"gap: {c.get('auc_gap_train_test', float('nan')):.4f}"
        )
        lines.append(f"- threshold selected on validation: {c.get('threshold_selected')}")
        rm_n = rm.get("n_trades", 0)
        rm_s = rm.get("sharpe", float("nan"))
        rm_p = rm.get("annual_pnl", 0)
        rm_d = rm.get("max_dd", 0)
        rm_a4 = rm.get("a4_n_positive", 0)
        rm_a5 = rm.get("a5_stressed_annual_pnl", float("nan"))
        lines.append(
            f"- realised: n_trades={rm_n}, sharpe={rm_s:.4f}, "
            f"ann_pnl={rm_p:+.1f}, max_dd={rm_d:.1f}, "
            f"A4 pos={rm_a4}/4, A5 stress ann_pnl={rm_a5:+.1f}"
        )
        pm_n = pm.get("n_trades", 0)
        pm_s = pm.get("sharpe", float("nan"))
        pm_p = pm.get("annual_pnl", 0)
        lines.append(f"- proxy: n_trades={pm_n}, sharpe={pm_s:.4f}, ann_pnl={pm_p:+.1f}")
        gate_str = " ".join(f"{k}={'OK' if v else 'x'}" for k, v in gates.items())
        lines.append(f"- gates: {gate_str}")
        cal = c.get("calibration", {})
        cal_m = cal.get("monotonic")
        cal_b = cal.get("brier", float("nan"))
        lines.append(f"- calibration: monotonic={cal_m}, brier={cal_b:.4f}")
        lines.append(f"- verdict: **{c.get('verdict')}** ({c.get('h_state')})")
        bp = c.get("by_pair_trade_count", {})
        bd = c.get("by_direction_trade_count", {})
        lines.append(f"- by-pair trade count: {bp}")
        lines.append(f"- by-direction trade count: {bd}")
        lines.append("")

    lines.append("## Top-3 cells by realised Sharpe — compact")
    lines.append("")
    sorted_by_sharpe = sorted(
        cell_results,
        key=lambda c: (
            c.get("realised_metrics", {}).get("sharpe", -1e9)
            if np.isfinite(c.get("realised_metrics", {}).get("sharpe", -1e9))
            else -1e9
        ),
        reverse=True,
    )
    lines.append("| trailing | rep | admissibility | sharpe | ann_pnl | n_trades | verdict |")
    lines.append("|---|---|---|---|---|---|---|")
    for c in sorted_by_sharpe[:3]:
        cell = c["cell"]
        rm = c.get("realised_metrics", {})
        lines.append(
            f"| {cell['trailing_window']} | {cell['representation']} | "
            f"{cell['admissibility']} | {rm.get('sharpe', float('nan')):.4f} | "
            f"{rm.get('annual_pnl', 0):+.1f} | {rm.get('n_trades', 0)} | "
            f"{c.get('verdict', '-')} |"
        )
    lines.append("")

    lines.append("## Per-cell admissibility pass-through rate")
    lines.append("")
    lines.append("| trailing | rep | admissibility | pt_train | pt_val | pt_test |")
    lines.append("|---|---|---|---|---|---|")
    for c in cell_results:
        cell = c["cell"]
        pt = c.get("passthrough_rates", {})
        lines.append(
            f"| {cell['trailing_window']} | {cell['representation']} | "
            f"{cell['admissibility']} | {pt.get('train', 0):.3f} | "
            f"{pt.get('val', 0):.3f} | {pt.get('test', 0):.3f} |"
        )
    lines.append("")

    lines.append("## Joint regime distribution (train set)")
    lines.append("")
    if regime_distribution:
        lines.append("| joint_regime | count | rate | rare (<1%) |")
        lines.append("|---|---|---|---|")
        for jr, info in sorted(
            regime_distribution.items(), key=lambda x: x[1]["count"], reverse=True
        ):
            lines.append(
                f"| {jr} | {info['count']} | {info['rate']:.4f} | "
                f"{'YES' if info['rate'] < 0.01 else 'no'} |"
            )
        lines.append("")

    lines.append("## 'none' admissibility cell — interpretation")
    lines.append("")
    lines.append(
        "The 'none' admissibility cells use ALL 25.0a-β labels (no regime "
        "filter). They are the **full-sample baseline cells** — by design "
        "(per 25.0c-α §5), they address F1's sample-size pressure and provide "
        "the cleanest test of whether F2's categorical regime features alone "
        "produce learnable signal under realistic sample sizes."
    )
    lines.append("")

    lines.append("## Multiple-testing caveat")
    lines.append("")
    lines.append(
        "These are 18 evaluated cells. PROMISING_BUT_NEEDS_OOS / ADOPT_CANDIDATE "
        "verdicts are hypothesis-generating ONLY; production-readiness requires "
        "an X-v2-equivalent frozen-OOS PR per Phase 22 contract."
    )
    lines.append("")

    h1_pass_cells = [
        c for c in cell_results if np.isfinite(c.get("test_auc", -1)) and c["test_auc"] >= 0.55
    ]
    n_h1 = len(h1_pass_cells)
    n_total = len(cell_results)
    lines.append(f"## H1 routing summary: {n_h1} / {n_total} cells PASS H1 (test AUC >= 0.55)")
    lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pairs", nargs="*", default=PAIRS_20)
    parser.add_argument("--days", type=int, default=SPAN_DAYS)
    parser.add_argument("--out-dir", type=Path, default=ARTIFACT_ROOT)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument(
        "--smoke-slice-days", type=int, default=90, help="Days to use in smoke mode"
    )
    args = parser.parse_args(argv)

    if args.smoke:
        args.pairs = ["USD_JPY", "EUR_USD", "GBP_JPY"]

    args.out_dir.mkdir(parents=True, exist_ok=True)

    print(f"=== Stage 25.0c-β F2 eval ({len(args.pairs)} pairs) ===")
    print(f"Cells: {len(CELL_GRID)} (LOCKED 18; bidirectionality LOCKED)")

    # Load 25.0a labels (excludes 5 prohibited diagnostic cols at load)
    print("Loading 25.0a path-quality labels...")
    labels = load_path_quality_labels()
    if args.pairs != PAIRS_20:
        labels = labels[labels["pair"].isin(args.pairs)]
    if args.smoke:
        cutoff = labels["signal_ts"].max() - pd.Timedelta(days=args.smoke_slice_days)
        labels = labels[labels["signal_ts"] >= cutoff]
    print(f"  labels rows: {len(labels)}")

    # Build pair_runtime for realised barrier PnL
    print("Building pair runtime (M1 OHLC)...")
    pair_runtime: dict[str, dict] = {}
    for pair in args.pairs:
        m1 = load_m1_ba(pair, days=args.days)
        pair_runtime[pair] = {
            "pip": pip_size_for(pair),
            "m1_pos": pd.Series(np.arange(len(m1), dtype=np.int64), index=m1.index),
            "n_m1": len(m1),
            "bid_h": m1["bid_h"].to_numpy(),
            "bid_l": m1["bid_l"].to_numpy(),
            "bid_c": m1["bid_c"].to_numpy(),
            "ask_h": m1["ask_h"].to_numpy(),
            "ask_l": m1["ask_l"].to_numpy(),
            "ask_c": m1["ask_c"].to_numpy(),
            "ask_o": m1["ask_o"].to_numpy(),
            "bid_o": m1["bid_o"].to_numpy(),
        }

    # Compute features per (pair, trailing_window) once; reuse across 9 cells
    feature_cache: dict[tuple[str, int], pd.DataFrame] = {}
    print("Computing F2 features per (pair, trailing_window)...")
    for trailing in CELL_TRAILING_WINDOWS:
        for pair in args.pairs:
            t0 = time.time()
            feats = compute_f2_features_for_pair(pair, days=args.days, trailing_window=trailing)
            feature_cache[(pair, trailing)] = feats
            print(f"  {pair} trailing={trailing}: rows={len(feats)} ({time.time() - t0:5.1f}s)")

    # Build per-cell merged dataset(s) — but features depend on trailing_window only,
    # so we build merged_for_trailing once per trailing_window.
    merged_per_trailing: dict[int, pd.DataFrame] = {}
    feature_nan_drop_count_total = 0
    feature_nan_drop_by_pair: dict[str, dict] = {}
    n_before_drop_total = 0
    for trailing in CELL_TRAILING_WINDOWS:
        feats_concat = pd.concat(
            [feature_cache[(pair, trailing)] for pair in args.pairs], ignore_index=True
        )
        feats_concat["pair"] = feats_concat["pair"].astype("object")
        labels_local = labels.copy()
        labels_local["pair"] = labels_local["pair"].astype("object")
        merged = pd.merge(labels_local, feats_concat, on=["pair", "signal_ts"], how="inner")
        n_before = len(merged)
        # NaN drop on F2 categorical/numeric/bool (excluding f2_e which can be 0)
        nan_check_cols = list(F2_CATEGORICAL_COLS_BASE) + list(F2_NUMERIC_COLS_BASE)
        nan_check_cols = [c for c in nan_check_cols if c in merged.columns]
        nan_check_cols = [c for c in nan_check_cols if c != "f2_e_return_sign"]
        nan_mask = merged[nan_check_cols].isna().any(axis=1)
        merged_clean = merged[~nan_mask].copy()
        merged_per_trailing[trailing] = merged_clean
        if trailing == CELL_TRAILING_WINDOWS[0]:
            n_before_drop_total = n_before
            feature_nan_drop_count_total = int(n_before - len(merged_clean))
            for pair in args.pairs:
                npb = (merged["pair"] == pair).sum()
                npa = (merged_clean["pair"] == pair).sum()
                d = int(npb - npa)
                rate = d / npb if npb > 0 else 0.0
                feature_nan_drop_by_pair[pair] = {"count": d, "rate": rate}
        print(f"  trailing={trailing}: merged={n_before}, after NaN drop={len(merged_clean)}")
    feature_nan_drop_rate_overall = (
        feature_nan_drop_count_total / n_before_drop_total if n_before_drop_total > 0 else 0.0
    )

    # Use trailing=100 dataset for split-date computation (deterministic)
    base_df = merged_per_trailing[CELL_TRAILING_WINDOWS[0]]
    train_df, val_df, test_df, t70, t85 = split_70_15_15(base_df)
    t_min = base_df["signal_ts"].min()
    t_max = base_df["signal_ts"].max()
    print(f"  split: train={len(train_df)}, val={len(val_df)}, test={len(test_df)}")

    # Joint regime distribution on train (for report)
    regime_distribution: dict[str, dict] = {}
    if "f2_b_joint_regime" in train_df.columns:
        jr_counts = train_df["f2_b_joint_regime"].value_counts(dropna=True)
        total = jr_counts.sum()
        for jr, count in jr_counts.items():
            regime_distribution[str(jr)] = {
                "count": int(count),
                "rate": float(count / total) if total > 0 else 0.0,
            }

    # Per-cell evaluation
    cell_results: list[dict] = []
    for i, cell in enumerate(CELL_GRID):
        t0 = time.time()
        merged_for_cell = merged_per_trailing[cell["trailing_window"]]
        train_c, val_c, test_c, _, _ = split_70_15_15(merged_for_cell)
        result = evaluate_cell(cell, merged_for_cell, (train_c, val_c, test_c), pair_runtime)
        cell_results.append(result)
        rm = result.get("realised_metrics", {})
        pt = result.get("passthrough_rates", {})
        print(
            f"  cell {i + 1}/18 tw={cell['trailing_window']} "
            f"rep={cell['representation']:<14} adm={cell['admissibility']:<14} "
            f"n_test={result.get('n_test', 0):>6} pt={pt.get('test', 0):.2f} "
            f"AUC={result.get('test_auc', float('nan')):.3f} "
            f"sharpe={rm.get('sharpe', float('nan')):+.3f} "
            f"ann_pnl={rm.get('annual_pnl', 0):+.1f} "
            f"verdict={result.get('verdict', '-')} "
            f"({time.time() - t0:5.1f}s)"
        )

    # Write report
    report_path = args.out_dir / "eval_report.md"
    write_eval_report(
        report_path,
        cell_results,
        (t_min, t70, t85, t_max),
        feature_nan_drop_count_total,
        feature_nan_drop_rate_overall,
        feature_nan_drop_by_pair,
        regime_distribution,
    )
    print(f"\nReport: {report_path}")
    h1_pass = sum(
        1 for c in cell_results if np.isfinite(c.get("test_auc", -1)) and c["test_auc"] >= 0.55
    )
    print(f"H1 PASS: {h1_pass}/18 cells")
    return 0


if __name__ == "__main__":
    sys.exit(main())
