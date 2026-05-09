"""Stage 25.0e-β — F3 cross-pair / relative currency strength eval.

Implements the binding contract from PR #292 (25.0e-α
docs/design/phase25_0e_alpha_f3_design.md). Reads 25.0a-β path-quality
labels, builds F3 cross-pair features (per-currency strength + cross-pair
correlation), trains 18 cells of logistic regression with chronological
70/15/15 split, selects trade threshold on validation only, evaluates
test ONCE with realised barrier PnL via M1 path re-traverse.

MANDATORY CLAUSES (verbatim per 25.0e-α §9):

1. Phase 25 framing.
   Phase 25 is the entry-side return on alternative admissible feature
   classes (F1-F6) layered on the 25.0a-β path-quality dataset. Each
   F-class is evaluated as an independent admissible-discriminative
   experiment. ADOPT requires both H2 PASS and the full 8-gate A1-A5
   harness.

2. Diagnostic columns prohibition.
   Calibration / threshold-sweep / directional-comparison columns are
   diagnostic-only. ADOPT_CANDIDATE routing must not depend on any
   single one of them. They exist to characterise the AUC-PnL gap,
   not to monetise it.

3. γ closure preservation.
   Phase 24 γ hard-close (PR #279) is unmodified. No 25.0e PR touches
   stage24 artifacts or stage24 verdict text.

4. Production-readiness preservation.
   X-v2 OOS gating remains required before any production deployment.
   No 25.0e PR pre-approves production wiring.

5. NG#10 / NG#11 not relaxed.
   25.0e PRs do not change the entry-side budget cap or the diagnostic-
   vs-routing separation rule.

6. F3 verdict scoping.
   The 25.0e-β verdict applies only to the F3 best cell on the 25.0a-β-
   spread dataset. Convergence with F4-F6 is a separate question;
   structural-gap inferences are jointly conditional on F3 H4 outcome.

PRODUCTION-MISUSE GUARDS (verbatim per 25.0e-α §5.1):

GUARD 1 — research-not-production: F3 features stay in scripts/; not
auto-routed to feature_service.py.
GUARD 2 — threshold-sweep-diagnostic: any threshold sweep here is
diagnostic-only.
GUARD 3 — directional-comparison-diagnostic: any long/short
decomposition is diagnostic-only.

H3 reference: best-of-{F1, F2} test AUC = 0.5644 (F1 rank-1 per
PR #284). H3 PASS at F3 best AUC ≥ 0.5744 (lift ≥ 0.01).

Strict-causal rule (§2.5): F3 features at signal_ts=t use only bars
strictly before t (bars ≤ t-1). All cross-pair series go through
shift(1) before any rolling aggregation.

F3-b correlation pairs are PREDECLARED (no target-aware selection).
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
import time
import warnings
from datetime import UTC, datetime
from pathlib import Path

# Windows console may default to cp932; force UTF-8 so em-dashes / Unicode in
# log strings do not crash the run before report write. Errors=replace is a
# best-effort fallback.
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

REPO_ROOT = Path(__file__).resolve().parent.parent
ARTIFACT_ROOT = REPO_ROOT / "artifacts" / "stage25_0e"
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

stage23_0a = importlib.import_module("stage23_0a_build_outcome_dataset")
stage25_0b = importlib.import_module("stage25_0b_f1_volatility_expansion_eval")

PAIRS_20 = stage23_0a.PAIRS_20
load_m1_ba = stage23_0a.load_m1_ba
aggregate_m1_to_tf_local = stage25_0b.aggregate_m1_to_tf_local
pip_size_for = stage23_0a.pip_size_for

# Reuse from 25.0b (shared infrastructure)
load_path_quality_labels = stage25_0b.load_path_quality_labels
split_70_15_15 = stage25_0b.split_70_15_15
_compute_realised_barrier_pnl = stage25_0b._compute_realised_barrier_pnl
compute_8_gate_metrics = stage25_0b.compute_8_gate_metrics
gate_matrix = stage25_0b.gate_matrix
_proxy_pnl_per_row = stage25_0b._proxy_pnl_per_row
_select_threshold_on_val = stage25_0b._select_threshold_on_val
PROHIBITED_DIAGNOSTIC_COLUMNS = stage25_0b.PROHIBITED_DIAGNOSTIC_COLUMNS
LOW_POWER_N_TEST = stage25_0b.LOW_POWER_N_TEST
LOW_POWER_N_TRAIN = stage25_0b.LOW_POWER_N_TRAIN
A1_MIN_SHARPE = stage25_0b.A1_MIN_SHARPE
A2_MIN_ANNUAL_PNL = stage25_0b.A2_MIN_ANNUAL_PNL
SPAN_DAYS = stage25_0b.SPAN_DAYS
TRAIN_FRAC = stage25_0b.TRAIN_FRAC
VAL_FRAC = stage25_0b.VAL_FRAC


# ---------------------------------------------------------------------------
# Design constants (LOCKED per 25.0e-α)
# ---------------------------------------------------------------------------

# H3 reference per 25.0e-α §4 + user directive (PR #292 review):
# best-of-{F1, F2} test AUC = max(0.5644, 0.5613) = 0.5644.
# H3 PASS at F3 best AUC ≥ 0.5644 + 0.01 = 0.5744.
H3_REFERENCE_AUC = 0.5644
H3_LIFT_THRESHOLD = 0.01
H3_PASS_AUC = H3_REFERENCE_AUC + H3_LIFT_THRESHOLD  # 0.5744

# H1 per 25.0e-α §4
H1_PASS_AUC = 0.55

# Currencies in canonical 20-pair universe
CURRENCIES = ("USD", "EUR", "JPY", "GBP", "AUD", "CAD", "CHF", "NZD")

# F3-b correlation pair-set: PREDECLARED, no target-aware selection
# (per user directive on PR #292 review).
F3_B_CORR_PAIRS: tuple[tuple[str, str], ...] = (
    ("EUR_USD", "GBP_USD"),
    ("AUD_USD", "NZD_USD"),
    ("USD_JPY", "USD_CHF"),
    ("EUR_JPY", "GBP_JPY"),
    ("EUR_GBP", "EUR_USD"),
    ("AUD_JPY", "NZD_JPY"),
)

# Sweep grid per 25.0e-α §3 — 18 cells
CELL_SUBGROUPS = ("F3a", "F3b", "F3a_F3b")
CELL_LOOKBACKS = (20, 50, 100)
CELL_ZSCORE_WINDOWS = (20, 50)

# Threshold candidates inherited from 25.0b
THRESHOLD_CANDIDATES = stage25_0b.THRESHOLD_CANDIDATES

CATEGORICAL_COLS = ["pair", "direction"]


# ---------------------------------------------------------------------------
# Currency-pair orientation helpers (§2.3 of 25.0e-α)
# ---------------------------------------------------------------------------


def pairs_containing(currency: str, universe: tuple[str, ...] = tuple(PAIRS_20)) -> list[str]:
    """Return canonical pairs containing currency `currency`.

    Only pairs in the canonical 20-pair universe are returned. No
    synthetic / unavailable pair is constructed.
    """
    out: list[str] = []
    for p in universe:
        base, quote = p.split("_")
        if currency in (base, quote):
            out.append(p)
    return out


def signed_return_orientation(pair: str, currency: str) -> int:
    """Return +1 if `currency` is base in `pair`, -1 if it is quote.

    Raises ValueError if currency not in pair.
    """
    base, quote = pair.split("_")
    if currency == base:
        return +1
    if currency == quote:
        return -1
    raise ValueError(f"currency {currency} not in pair {pair}")


# ---------------------------------------------------------------------------
# Wide M5 returns matrix (one column per pair, indexed by M5 timestamp)
# ---------------------------------------------------------------------------


def build_wide_m5_returns(
    pairs: list[str], days: int = SPAN_DAYS
) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    """Build wide DataFrame of M5 log-returns: index=M5 ts, columns=pairs.

    Also returns per-pair M5 OHLC dict for downstream re-use.
    Log-return at M5 bar T uses mid close at T and at T-1.
    """
    m5_per_pair: dict[str, pd.DataFrame] = {}
    log_ret_series: dict[str, pd.Series] = {}
    for pair in pairs:
        m1 = load_m1_ba(pair, days=days)
        m5 = aggregate_m1_to_tf_local(m1, "M5")
        m5_per_pair[pair] = m5
        mid_c = (m5["bid_c"] + m5["ask_c"]) / 2.0
        log_ret_series[pair] = np.log(mid_c).diff()

    wide = pd.DataFrame(log_ret_series)
    wide.index.name = "ts"
    return wide, m5_per_pair


# ---------------------------------------------------------------------------
# F3-a per-currency strength (causal: shift(1) BEFORE rolling)
# ---------------------------------------------------------------------------


def compute_currency_strength(
    wide_returns: pd.DataFrame,
    currency: str,
    lookback: int,
    zscore_window: int,
) -> pd.Series:
    """Causal currency-strength index z-score for `currency`.

    Strict-causal contract (§2.5 of 25.0e-α):
      feature(t) uses bars <= t-1 only.

    Steps:
      1. Build signed-return series: per pair containing `currency`,
         orient sign so positive return = `currency` strengthening.
      2. Equal-weight mean across the available canonical pairs.
      3. shift(1) before rolling mean over `lookback`.
      4. shift(1) before rolling mean / std (over `zscore_window`)
         used for z-score.

    Output index aligned to `wide_returns` index. NaN before warmup.
    """
    pairs = pairs_containing(currency)
    if not pairs:
        return pd.Series(np.nan, index=wide_returns.index)

    signed_components = []
    for p in pairs:
        if p not in wide_returns.columns:
            continue
        sign = signed_return_orientation(p, currency)
        signed_components.append(sign * wide_returns[p])
    if not signed_components:
        return pd.Series(np.nan, index=wide_returns.index)

    signed_returns_df = pd.concat(signed_components, axis=1)
    signed_mean = signed_returns_df.mean(axis=1, skipna=True)

    # CAUSAL: shift BEFORE any rolling stat used for feature(t).
    rolled_strength = signed_mean.shift(1).rolling(lookback, min_periods=lookback).mean()
    z_mean = rolled_strength.shift(1).rolling(zscore_window, min_periods=zscore_window).mean()
    z_std = rolled_strength.shift(1).rolling(zscore_window, min_periods=zscore_window).std()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        zscore = (rolled_strength - z_mean) / z_std
    zscore[~np.isfinite(zscore)] = np.nan
    return zscore


# ---------------------------------------------------------------------------
# F3-b cross-pair correlation (causal: shift(1) BEFORE rolling)
# ---------------------------------------------------------------------------


def compute_pair_correlation(
    wide_returns: pd.DataFrame,
    pair_a: str,
    pair_b: str,
    lookback: int,
) -> pd.Series:
    """Rolling Pearson correlation between log_returns of two pairs.

    Strict-causal: shift(1) BEFORE rolling so feature(t) uses bars ≤ t-1.
    """
    if pair_a not in wide_returns.columns or pair_b not in wide_returns.columns:
        return pd.Series(np.nan, index=wide_returns.index)
    a = wide_returns[pair_a].shift(1)
    b = wide_returns[pair_b].shift(1)
    corr = a.rolling(lookback, min_periods=lookback).corr(b)
    corr[~np.isfinite(corr)] = np.nan
    return corr


# ---------------------------------------------------------------------------
# Feature matrix assembly per cell
# ---------------------------------------------------------------------------


def feature_columns_for_cell(subgroup: str) -> list[str]:
    cols: list[str] = []
    if subgroup in ("F3a", "F3a_F3b"):
        cols.extend([f"f3a_{c}_strength_z" for c in CURRENCIES])
    if subgroup in ("F3b", "F3a_F3b"):
        for a, b in F3_B_CORR_PAIRS:
            cols.append(f"f3b_corr_{a}_{b}")
    return cols


def build_f3_features(
    wide_returns: pd.DataFrame,
    lookback: int,
    zscore_window: int,
) -> pd.DataFrame:
    """Build all F3 feature columns at once (computed per ts, per cell).

    Includes both F3-a and F3-b columns. Subsetting is done downstream
    via feature_columns_for_cell(subgroup).
    """
    feats: dict[str, pd.Series] = {}
    for c in CURRENCIES:
        feats[f"f3a_{c}_strength_z"] = compute_currency_strength(
            wide_returns, c, lookback, zscore_window
        )
    for a, b in F3_B_CORR_PAIRS:
        feats[f"f3b_corr_{a}_{b}"] = compute_pair_correlation(wide_returns, a, b, lookback)
    out = pd.DataFrame(feats, index=wide_returns.index)
    return out


# ---------------------------------------------------------------------------
# Cell grid
# ---------------------------------------------------------------------------


def build_cells() -> list[dict]:
    cells: list[dict] = []
    for sg in CELL_SUBGROUPS:
        for lb in CELL_LOOKBACKS:
            for zw in CELL_ZSCORE_WINDOWS:
                cells.append({"subgroup": sg, "lookback": lb, "zscore_window": zw})
    return cells


CELL_GRID = build_cells()
assert len(CELL_GRID) == 18, f"expected 18 cells, got {len(CELL_GRID)}"


# ---------------------------------------------------------------------------
# Decile reliability calibration (diagnostic-only per §6 of 25.0e-α)
# ---------------------------------------------------------------------------


def calibration_decile_check(p: np.ndarray, label: np.ndarray) -> dict:
    """10-bucket reliability table + per-bucket Brier + overall Brier.

    Diagnostic-only: this output does NOT change ADOPT criteria.
    """
    n = len(p)
    if n < 30:
        return {
            "n": n,
            "monotonic": False,
            "buckets": [],
            "overall_brier": float("nan"),
            "low_n_flag": True,
        }
    df = pd.DataFrame({"p": p, "label": label})
    try:
        df["bucket"] = pd.qcut(df["p"], 10, labels=False, duplicates="drop")
    except ValueError:
        return {
            "n": n,
            "monotonic": False,
            "buckets": [],
            "overall_brier": float("nan"),
            "low_n_flag": True,
        }
    grouped_rows: list[dict] = []
    for bucket_id, sub in df.groupby("bucket"):
        bucket_brier = brier_score_loss(sub["label"].to_numpy(), sub["p"].to_numpy())
        grouped_rows.append(
            {
                "bucket": int(bucket_id),
                "p_hat_mean": float(sub["p"].mean()),
                "realised_win_rate": float(sub["label"].mean()),
                "n": int(len(sub)),
                "brier": float(bucket_brier),
            }
        )
    rates = [r["realised_win_rate"] for r in grouped_rows]
    monotonic = all(rates[i] <= rates[i + 1] for i in range(len(rates) - 1))
    overall_brier = float(brier_score_loss(label, p))
    low_n = n < 100
    return {
        "n": n,
        "monotonic": bool(monotonic),
        "buckets": grouped_rows,
        "overall_brier": overall_brier,
        "low_n_flag": bool(low_n),
    }


# ---------------------------------------------------------------------------
# Per-cell verdict tree (per 25.0e-α §7) — H1/H2 + 8-gate
# ---------------------------------------------------------------------------


def assign_cell_verdict(test_auc: float, gates: dict[str, bool], n_trades: int) -> tuple[str, str]:
    """Returns (verdict, h_state). Per-cell only.

    Aggregate-level H3/H4 framing is applied at sweep level later.
    Per-cell semantics:
      H1 FAIL                            -> REJECT_NON_DISCRIMINATIVE
      H1 PASS, H2 PASS, all gates OK     -> ADOPT_CANDIDATE
      H1 PASS, H2 PASS, A3-A5 partial    -> PROMISING_BUT_NEEDS_OOS
      H1 PASS, H2 PASS, A3-A5 fail       -> REJECT
      H1 PASS, H2 FAIL                   -> REJECT_BUT_INFORMATIVE
                                            (refined to ORTHOGONAL or
                                             REDUNDANT after H3 at
                                             aggregate level)
    """
    h1_pass = np.isfinite(test_auc) and test_auc >= H1_PASS_AUC
    if not h1_pass:
        return "REJECT_NON_DISCRIMINATIVE", "H1_FAIL"
    h2_pass = gates.get("A1", False) and gates.get("A2", False)
    if not h2_pass:
        return "REJECT_BUT_INFORMATIVE", "H1_PASS_H2_FAIL"
    all_keys = ("A0", "A1", "A2", "A3", "A4", "A5")
    if all(gates.get(k, False) for k in all_keys):
        return "ADOPT_CANDIDATE", "ALL_GATES_PASS"
    # H1+H2 pass but at least one of A3-A5 (or A0) fails
    a3_a5 = ("A3", "A4", "A5")
    n_a3_a5_pass = sum(1 for k in a3_a5 if gates.get(k, False))
    if n_a3_a5_pass >= 1:
        return "PROMISING_BUT_NEEDS_OOS", "H1_H2_PASS_A3_A5_PARTIAL"
    return "REJECT", "H1_H2_PASS_A3_A5_FAIL"


# ---------------------------------------------------------------------------
# Bidirectional pivot helper for threshold logic (mirrors F1 _bidirectional)
# ---------------------------------------------------------------------------


def _pivot_long_short(df: pd.DataFrame, p_col: str, feature_cols: list[str]) -> pd.DataFrame:
    """Pivot to wide: each (pair, signal_ts) row carries label_long,
    label_short, p_long, p_short, atr.
    """
    base_cols = ["pair", "signal_ts", "atr_at_signal_pip"] + feature_cols
    base = df[df["direction"] == "long"][base_cols]
    long_part = df[df["direction"] == "long"][["pair", "signal_ts", "label", p_col]].rename(
        columns={"label": "label_long", p_col: "p_long"}
    )
    short_part = df[df["direction"] == "short"][["pair", "signal_ts", "label", p_col]].rename(
        columns={"label": "label_short", p_col: "p_short"}
    )
    out = pd.merge(base, long_part, on=["pair", "signal_ts"], how="inner")
    out = pd.merge(out, short_part, on=["pair", "signal_ts"], how="inner")
    return out


# ---------------------------------------------------------------------------
# Pipeline builder
# ---------------------------------------------------------------------------


def build_logistic_pipeline(numeric_cols: list[str]) -> Pipeline:
    pre = ColumnTransformer(
        [
            ("num", StandardScaler(), numeric_cols),
            ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_COLS),
        ]
    )
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
    df_full: pd.DataFrame,
    splits: tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame],
    pair_runtime: dict,
) -> dict:
    """Train one cell, select threshold on val, evaluate on test once."""
    subgroup = cell["subgroup"]
    feature_cols = feature_columns_for_cell(subgroup)
    train_df, val_df, test_df = splits

    n_train, n_val, n_test = len(train_df), len(val_df), len(test_df)
    if n_train < 100 or n_val < 50 or n_test < 50:
        return {
            "cell": cell,
            "feature_cols": feature_cols,
            "n_train": n_train,
            "n_val": n_val,
            "n_test": n_test,
            "test_auc": float("nan"),
            "verdict": "REJECT_NON_DISCRIMINATIVE",
            "h_state": "INSUFFICIENT_DATA",
            "low_power": True,
            "skip_reason": "insufficient sample",
        }

    x_train = train_df[feature_cols + CATEGORICAL_COLS]
    y_train = train_df["label"].astype(int)
    x_val = val_df[feature_cols + CATEGORICAL_COLS]
    y_val = val_df["label"].astype(int)
    x_test = test_df[feature_cols + CATEGORICAL_COLS]
    y_test = test_df["label"].astype(int)

    pipeline = build_logistic_pipeline(feature_cols)
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

    # Pivot val to (pair, signal_ts) wide for threshold selection
    val = val_df.copy()
    val["_p"] = val_p
    val_long = val[val["direction"] == "long"].set_index(["pair", "signal_ts"])
    val_short = val[val["direction"] == "short"].set_index(["pair", "signal_ts"])
    common_idx = val_long.index.intersection(val_short.index)
    if len(common_idx) < 10:
        return {
            "cell": cell,
            "feature_cols": feature_cols,
            "n_train": n_train,
            "n_val": n_val,
            "n_test": n_test,
            "train_auc": train_auc,
            "val_auc": val_auc,
            "test_auc": test_auc,
            "verdict": "REJECT_NON_DISCRIMINATIVE",
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

    # Test set traversal (touched once)
    test = test_df.copy()
    test["_p"] = test_p
    test_long = test[test["direction"] == "long"].set_index(["pair", "signal_ts"])
    test_short = test[test["direction"] == "short"].set_index(["pair", "signal_ts"])
    common_test_idx = test_long.index.intersection(test_short.index)
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
    by_direction_count: dict[str, int] = {"long": 0, "short": 0}

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
    n_trades = len(realised_arr)

    realised_metrics = compute_8_gate_metrics(realised_arr, n_trades)
    gates = gate_matrix(realised_metrics)
    proxy_metrics = compute_8_gate_metrics(proxy_arr, len(proxy_arr))
    verdict, h_state = assign_cell_verdict(test_auc, gates, n_trades)
    cal_decile = calibration_decile_check(test_p, y_test.to_numpy())

    low_power = n_test < LOW_POWER_N_TEST or n_train < LOW_POWER_N_TRAIN

    return {
        "cell": cell,
        "feature_cols": feature_cols,
        "n_train": n_train,
        "n_val": n_val,
        "n_test": n_test,
        "train_auc": train_auc,
        "val_auc": val_auc,
        "test_auc": test_auc,
        "auc_gap_train_test": (train_auc - test_auc) if np.isfinite(test_auc) else float("nan"),
        "verdict": verdict,
        "h_state": h_state,
        "threshold_selected": threshold,
        "threshold_log": threshold_log,
        "calibration_decile": cal_decile,
        "realised_metrics": realised_metrics,
        "proxy_metrics": proxy_metrics,
        "gates": gates,
        "by_pair_trade_count": by_pair_count,
        "by_direction_trade_count": by_direction_count,
        "low_power": low_power,
    }


# ---------------------------------------------------------------------------
# Aggregate-level H3 / H4 reasoning
# ---------------------------------------------------------------------------


def aggregate_h3_h4(cell_results: list[dict]) -> dict:
    """Pick best-AUC cell, decide H3 / H4 status.

    H3: best F3 AUC ≥ best-of-{F1, F2} + 0.01 = H3_PASS_AUC.
    H4: best F3 cell realised Sharpe ≥ 0 (structural-gap escape).
    """
    valid = [
        c
        for c in cell_results
        if np.isfinite(c.get("test_auc", float("nan")))
        and c.get("h_state") not in ("INSUFFICIENT_DATA", "PIVOT_INSUFFICIENT")
    ]
    if not valid:
        return {
            "best_cell": None,
            "best_auc": float("nan"),
            "h3_pass": False,
            "h3_lift_observed": float("nan"),
            "h3_reference_auc": H3_REFERENCE_AUC,
            "h3_pass_threshold": H3_PASS_AUC,
            "h4_pass": False,
            "h4_realised_sharpe": float("nan"),
            "h4_trigger_msg": "no valid cell",
        }
    # Best by test AUC
    best = max(valid, key=lambda c: c["test_auc"])
    best_auc = float(best["test_auc"])
    h3_lift = best_auc - H3_REFERENCE_AUC
    h3_pass = h3_lift >= H3_LIFT_THRESHOLD
    rm = best.get("realised_metrics", {})
    sharpe = rm.get("sharpe", float("nan"))
    h4_pass = bool(np.isfinite(sharpe) and sharpe >= 0.0)
    if not h4_pass:
        h4_msg = (
            "H4 FAIL — F3 best-cell realised Sharpe < 0 at AUC ≈ structural-gap "
            "regime; triggers PR #291 §6.4 strong soft-stop strengthening."
        )
    else:
        h4_msg = "H4 PASS — F3 escapes the AUC-PnL gap."
    return {
        "best_cell": best["cell"],
        "best_auc": best_auc,
        "best_realised_metrics": rm,
        "h3_pass": bool(h3_pass),
        "h3_lift_observed": float(h3_lift),
        "h3_reference_auc": H3_REFERENCE_AUC,
        "h3_pass_threshold": H3_PASS_AUC,
        "h4_pass": h4_pass,
        "h4_realised_sharpe": float(sharpe) if np.isfinite(sharpe) else float("nan"),
        "h4_trigger_msg": h4_msg,
    }


def refine_verdict_with_h3(cell: dict, h3_pass: bool) -> dict:
    """If a cell verdict is REJECT_BUT_INFORMATIVE, refine to ORTHOGONAL
    (H3 pass) or REDUNDANT (H3 fail) per §7.
    """
    if cell.get("verdict") == "REJECT_BUT_INFORMATIVE":
        cell = dict(cell)
        if h3_pass:
            cell["verdict"] = "REJECT_BUT_INFORMATIVE_ORTHOGONAL"
        else:
            cell["verdict"] = "REJECT_BUT_INFORMATIVE_REDUNDANT"
    return cell


# ---------------------------------------------------------------------------
# Report writer
# ---------------------------------------------------------------------------


def write_eval_report(
    out_path: Path,
    cell_results: list[dict],
    agg: dict,
    split_dates: tuple[pd.Timestamp, pd.Timestamp, pd.Timestamp, pd.Timestamp],
    feature_nan_drop_count: int,
    feature_nan_drop_rate_overall: float,
    feature_nan_drop_by_pair: dict[str, dict],
) -> None:
    t_min, t70, t85, t_max = split_dates
    lines: list[str] = []
    lines.append("# Stage 25.0e-β — F3 Cross-Pair / Relative Currency Strength Eval")
    lines.append("")
    lines.append(f"Generated: {datetime.now(UTC).isoformat()}")
    lines.append("")
    lines.append("Design contract: `docs/design/phase25_0e_alpha_f3_design.md` (PR #292)")
    lines.append("")
    lines.append("## Mandatory clauses (verbatim per 25.0e-α §9)")
    lines.append("")
    lines.append(
        "**1. Phase 25 framing.** Phase 25 is the entry-side return on alternative "
        "admissible feature classes (F1-F6) layered on the 25.0a-β path-quality "
        "dataset. Each F-class is evaluated as an independent admissible-discriminative "
        "experiment. ADOPT requires both H2 PASS and the full 8-gate A1-A5 harness."
    )
    lines.append("")
    lines.append(
        "**2. Diagnostic columns prohibition.** Calibration / threshold-sweep / "
        "directional-comparison columns are diagnostic-only. ADOPT_CANDIDATE routing "
        "must not depend on any single one of them. They exist to characterise the "
        "AUC-PnL gap, not to monetise it."
    )
    lines.append("")
    lines.append(
        "**3. γ closure preservation.** Phase 24 γ hard-close (PR #279) is unmodified. "
        "No 25.0e PR touches stage24 artifacts or stage24 verdict text."
    )
    lines.append("")
    lines.append(
        "**4. Production-readiness preservation.** X-v2 OOS gating remains required "
        "before any production deployment. No 25.0e PR pre-approves production wiring."
    )
    lines.append("")
    lines.append(
        "**5. NG#10 / NG#11 not relaxed.** 25.0e PRs do not change the entry-side "
        "budget cap or the diagnostic-vs-routing separation rule."
    )
    lines.append("")
    lines.append(
        "**6. F3 verdict scoping.** The 25.0e-β verdict applies only to the F3 best "
        "cell on the 25.0a-β-spread dataset. Convergence with F4-F6 is a separate "
        "question; structural-gap inferences are jointly conditional on F3 H4 "
        "outcome."
    )
    lines.append("")
    lines.append("## Production-misuse guards (verbatim per 25.0e-α §5.1)")
    lines.append("")
    lines.append(
        "**GUARD 1 — research-not-production**: F3 features stay in scripts/; not "
        "auto-routed to feature_service.py."
    )
    lines.append("")
    lines.append(
        "**GUARD 2 — threshold-sweep-diagnostic**: any threshold sweep here is diagnostic-only."
    )
    lines.append("")
    lines.append(
        "**GUARD 3 — directional-comparison-diagnostic**: any long/short "
        "decomposition is diagnostic-only."
    )
    lines.append("")
    lines.append("## Causality and correlation-set notes")
    lines.append("")
    lines.append(
        "F3 features at signal_ts=t use only bars strictly before t (bars ≤ t-1). "
        "All cross-pair series go through `shift(1)` before any rolling aggregation; "
        "a bar-t lookahead unit test enforces this invariant."
    )
    lines.append("")
    lines.append(
        "**F3-b uses a predeclared small correlation set; no target-aware pair "
        "selection.** The 6 predeclared pairs are: "
        + ", ".join(f"({a},{b})" for a, b in F3_B_CORR_PAIRS)
        + "."
    )
    lines.append("")
    lines.append("## Realised barrier PnL methodology")
    lines.append("")
    lines.append(
        "Final test 8-gate evaluation uses **realised barrier PnL** computed by "
        "re-traversing M1 paths with 25.0a barrier semantics (favourable barrier "
        "→ +K_FAV × ATR; adverse barrier → -K_ADV × ATR; same-bar both-hit → "
        "adverse first; horizon expiry → mark-to-market). Validation threshold "
        "selection uses synthesized PnL proxy for speed."
    )
    lines.append("")
    lines.append("## H3 reference (binding from 25.0e-α §4 + PR #292 review)")
    lines.append("")
    lines.append(
        f"- best-of-{{F1, F2}} test AUC = {H3_REFERENCE_AUC:.4f} "
        "(F1 rank-1 = 0.5644; F2 rank-1 = 0.5613)"
    )
    lines.append(f"- H3 PASS threshold = {H3_PASS_AUC:.4f} (lift ≥ 0.01)")
    lines.append("- H3 is evaluated on the BEST F3 cell, single-set comparison.")
    lines.append("- Combined feature set (F3 + F1/F2) is NOT implemented in 25.0e-β.")
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

    # All cells summary sorted by test AUC desc
    sorted_by_auc = sorted(
        cell_results,
        key=lambda c: c.get("test_auc", -1) if np.isfinite(c.get("test_auc", -1)) else -1,
        reverse=True,
    )
    lines.append("## All 18 cells — summary (sorted by test AUC desc)")
    lines.append("")
    lines.append(
        "| subgroup | lookback | zscore_window | n_train | n_test | "
        "train_AUC | val_AUC | test_AUC | gap | verdict | h_state | "
        "n_trades | sharpe | ann_pnl | A4 | A5_ann | low_power |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for c in sorted_by_auc:
        cell = c["cell"]
        rm = c.get("realised_metrics", {})
        lines.append(
            f"| {cell['subgroup']} | {cell['lookback']} | "
            f"{cell['zscore_window']} | {c.get('n_train', 0)} | "
            f"{c.get('n_test', 0)} | "
            f"{c.get('train_auc', float('nan')):.4f} | "
            f"{c.get('val_auc', float('nan')):.4f} | "
            f"{c.get('test_auc', float('nan')):.4f} | "
            f"{c.get('auc_gap_train_test', float('nan')):.4f} | "
            f"{c.get('verdict', '-')} | {c.get('h_state', '-')} | "
            f"{rm.get('n_trades', 0)} | {rm.get('sharpe', float('nan')):.4f} | "
            f"{rm.get('annual_pnl', 0.0):+.1f} | "
            f"{rm.get('a4_n_positive', 0)} | "
            f"{rm.get('a5_stressed_annual_pnl', float('nan')):+.1f} | "
            f"{'YES' if c.get('low_power') else 'no'} |"
        )
    lines.append("")

    # Top-3 cells by test AUC expanded
    lines.append("## Top-3 cells by test AUC — expanded breakdown")
    lines.append("")
    for c in sorted_by_auc[:3]:
        cell = c["cell"]
        lines.append(
            f"### Cell: subgroup={cell['subgroup']}, lookback={cell['lookback']}, "
            f"zscore_window={cell['zscore_window']}"
        )
        lines.append("")
        rm = c.get("realised_metrics", {})
        pm = c.get("proxy_metrics", {})
        gates = c.get("gates", {})
        nt = c.get("n_train", 0)
        nv = c.get("n_val", 0)
        nte = c.get("n_test", 0)
        lines.append(f"- n_train: {nt}, n_val: {nv}, n_test: {nte}")
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
        cal = c.get("calibration_decile", {})
        cal_m = cal.get("monotonic")
        cal_b = cal.get("overall_brier", float("nan"))
        cal_low = cal.get("low_n_flag", False)
        lines.append(
            f"- calibration decile: monotonic={cal_m}, overall_brier={cal_b:.4f}, "
            f"low_n_flag={cal_low}"
        )
        lines.append(f"- verdict: **{c.get('verdict')}** ({c.get('h_state')})")
        bp = c.get("by_pair_trade_count", {})
        bd = c.get("by_direction_trade_count", {})
        lines.append(f"- by-pair trade count: {bp}")
        lines.append(f"- by-direction trade count: {bd}")
        lines.append("- features: " + ", ".join(c.get("feature_cols", [])))
        lines.append("")

    # Best-cell decile reliability table (diagnostic-only)
    if sorted_by_auc and sorted_by_auc[0].get("calibration_decile", {}).get("buckets"):
        lines.append("## Best-cell decile reliability table (diagnostic-only)")
        lines.append("")
        cal = sorted_by_auc[0]["calibration_decile"]
        lines.append(
            f"n={cal.get('n')}, monotonic={cal.get('monotonic')}, "
            f"overall_brier={cal.get('overall_brier'):.4f}, "
            f"low_n_flag={cal.get('low_n_flag', False)}"
        )
        lines.append("")
        lines.append("| bucket | n | p_hat_mean | realised_win_rate | brier |")
        lines.append("|---|---|---|---|---|")
        for row in cal.get("buckets", []):
            lines.append(
                f"| {row['bucket']} | {row['n']} | {row['p_hat_mean']:.4f} | "
                f"{row['realised_win_rate']:.4f} | {row['brier']:.4f} |"
            )
        lines.append("")

    # Aggregate H3 / H4 outcome
    lines.append("## Aggregate H1 / H2 / H3 / H4 outcome")
    lines.append("")
    bc = agg.get("best_cell")
    lines.append(f"- Best F3 cell: **{bc}** with test AUC {agg.get('best_auc', float('nan')):.4f}")
    lines.append(
        f"- H1 PASS threshold = {H1_PASS_AUC:.4f}; "
        f"H1 PASS at best cell: {agg.get('best_auc', 0) >= H1_PASS_AUC}"
    )
    bc_metrics = agg.get("best_realised_metrics", {})
    h2_pass = (
        np.isfinite(bc_metrics.get("sharpe", float("nan")))
        and bc_metrics.get("sharpe", -1) >= A1_MIN_SHARPE
        and bc_metrics.get("annual_pnl", -1) >= A2_MIN_ANNUAL_PNL
    )
    lines.append(
        f"- H2 (A1 Sharpe ≥ {A1_MIN_SHARPE} AND A2 ann_pnl ≥ {A2_MIN_ANNUAL_PNL}) "
        f"at best cell: **{h2_pass}** "
        f"(sharpe={bc_metrics.get('sharpe', float('nan')):.4f}, "
        f"ann_pnl={bc_metrics.get('annual_pnl', 0):+.1f})"
    )
    lines.append(
        f"- H3 (lift ≥ {H3_LIFT_THRESHOLD}, threshold ≥ {H3_PASS_AUC:.4f}): "
        f"**{agg.get('h3_pass')}** "
        f"(observed lift = {agg.get('h3_lift_observed', float('nan')):+.4f})"
    )
    lines.append(
        f"- H4 (best-cell realised Sharpe ≥ 0): **{agg.get('h4_pass')}** "
        f"(realised Sharpe = {agg.get('h4_realised_sharpe', float('nan')):.4f})"
    )
    lines.append("")
    lines.append(f"> {agg.get('h4_trigger_msg', '')}")
    lines.append("")

    # Routing recommendation framing — non-decisive
    lines.append("## Routing recommendation framing (non-decisive)")
    lines.append("")
    lines.append(
        "This section lists which §7 verdict tree branch the best cell falls into. "
        "It is informational. The actual routing decision (next F-class / "
        "Phase 25 close / production discussion) is handed to the next PR."
    )
    lines.append("")
    lines.append(
        "Per 25.0e-α §7 verdict tree, applied to the best cell after H3 "
        "refinement of REJECT_BUT_INFORMATIVE branches:"
    )
    lines.append("")
    if bc is not None:
        # Find the best-cell record in cell_results to get its current verdict
        best_record = None
        for c in cell_results:
            if c.get("cell") == bc:
                best_record = c
                break
        if best_record is not None:
            refined = refine_verdict_with_h3(best_record, agg.get("h3_pass", False))
            lines.append(f"- Best-cell refined verdict: **{refined['verdict']}**")
            lines.append(f"- Best-cell h_state: {refined['h_state']}")
    lines.append("")
    lines.append(
        "If H4 FAIL, PR #291 §6.4 strong soft-stop strengthening is the recommended "
        "next-PR consideration; user judgement decides whether to continue F4/F5/F6 "
        "or close Phase 25."
    )
    lines.append("")

    # Multiple-testing caveat
    lines.append("## Multiple-testing caveat")
    lines.append("")
    lines.append(
        "These are 18 evaluated cells. PROMISING_BUT_NEEDS_OOS / ADOPT_CANDIDATE "
        "verdicts are hypothesis-generating ONLY; production-readiness requires "
        "an X-v2-equivalent frozen-OOS PR per Phase 22 contract."
    )
    lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Data integration
# ---------------------------------------------------------------------------


def join_features_to_labels(feature_panel: pd.DataFrame, labels: pd.DataFrame) -> pd.DataFrame:
    """Join F3 feature panel (timestamp-indexed; pair-agnostic) to labels.

    F3 features are pair-agnostic at the bar level — per-bar features
    apply to all pairs at that timestamp. Join is on signal_ts only.
    """
    feats = feature_panel.copy()
    feats = feats.reset_index()
    feats = feats.rename(columns={"ts": "signal_ts"})
    if "signal_ts" not in feats.columns:
        feats = feats.rename(columns={feats.columns[0]: "signal_ts"})
    labels = labels.copy()
    labels["pair"] = labels["pair"].astype("object")
    merged = pd.merge(labels, feats, on="signal_ts", how="inner")
    return merged


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def _build_pair_runtime(pair: str, days: int) -> dict:
    m1 = load_m1_ba(pair, days=days)
    return {
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pairs", nargs="*", default=PAIRS_20)
    parser.add_argument("--days", type=int, default=SPAN_DAYS)
    parser.add_argument("--out-dir", type=Path, default=ARTIFACT_ROOT)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args(argv)

    if args.smoke:
        # Smoke uses a subset for fast wiring check; not for verdict.
        args.pairs = ["EUR_USD", "GBP_USD", "USD_JPY"]

    args.out_dir.mkdir(parents=True, exist_ok=True)

    print(f"=== Stage 25.0e-beta F3 eval ({len(args.pairs)} pairs) ===")
    print(
        f"H1={H1_PASS_AUC:.2f} | H3 ref AUC={H3_REFERENCE_AUC:.4f} "
        f"| H3 pass >= {H3_PASS_AUC:.4f} | cells={len(CELL_GRID)}"
    )

    # 1. Load 25.0a-β labels (drop diagnostic cols at load)
    print("Loading 25.0a-β path-quality labels...")
    labels = load_path_quality_labels()
    if args.pairs != PAIRS_20:
        labels = labels[labels["pair"].isin(args.pairs)]
    print(f"  labels rows: {len(labels)}")

    # 2. Build wide M5 returns matrix and per-pair runtime
    print("Building wide M5 returns matrix...")
    t0 = time.time()
    wide_returns, m5_per_pair = build_wide_m5_returns(args.pairs, days=args.days)
    print(f"  wide returns shape: {wide_returns.shape} ({time.time() - t0:5.1f}s)")
    print("Building M1 path runtime per pair...")
    pair_runtime: dict[str, dict] = {}
    for pair in args.pairs:
        t0 = time.time()
        pair_runtime[pair] = _build_pair_runtime(pair, days=args.days)
        print(f"  {pair}: m1 rows {pair_runtime[pair]['n_m1']} ({time.time() - t0:5.1f}s)")

    # 3. For each (lookback, zscore_window) build feature panel; subgroup
    #    selects subset within evaluate_cell. Cache panels by (lb, zw).
    cell_results: list[dict] = []
    panel_cache: dict[tuple[int, int], pd.DataFrame] = {}
    for i, cell in enumerate(CELL_GRID):
        t_cell = time.time()
        key = (cell["lookback"], cell["zscore_window"])
        if key not in panel_cache:
            panel_cache[key] = build_f3_features(
                wide_returns, lookback=cell["lookback"], zscore_window=cell["zscore_window"]
            )
        panel = panel_cache[key]

        # Join to labels
        merged = join_features_to_labels(panel, labels)
        feat_cols_for_cell = feature_columns_for_cell(cell["subgroup"])
        # Drop rows with NaN in any feature for the cell
        nan_mask = merged[feat_cols_for_cell].isna().any(axis=1)
        merged_clean = merged[~nan_mask].copy()

        # Compute drop stats once for first cell only (logged in report header)
        if i == 0:
            n_before_drop_first = len(merged)
            feature_nan_drop_count = int(n_before_drop_first - len(merged_clean))
            feature_nan_drop_rate_overall = (
                feature_nan_drop_count / n_before_drop_first if n_before_drop_first > 0 else 0.0
            )
            feature_nan_drop_by_pair: dict[str, dict] = {}
            for pair in args.pairs:
                n_pair_before = (merged["pair"] == pair).sum()
                n_pair_after = (merged_clean["pair"] == pair).sum()
                drop = int(n_pair_before - n_pair_after)
                rate = drop / n_pair_before if n_pair_before > 0 else 0.0
                feature_nan_drop_by_pair[pair] = {"count": drop, "rate": rate}

        # Chronological split
        train_df, val_df, test_df, t70_local, t85_local = split_70_15_15(merged_clean)
        if i == 0:
            t_min = merged_clean["signal_ts"].min()
            t_max = merged_clean["signal_ts"].max()
            t70 = t70_local
            t85 = t85_local

        result = evaluate_cell(cell, merged_clean, (train_df, val_df, test_df), pair_runtime)
        cell_results.append(result)
        rm = result.get("realised_metrics", {})
        print(
            f"  cell {i + 1}/18 sg={cell['subgroup']:8} lb={cell['lookback']:3} "
            f"zw={cell['zscore_window']:2} "
            f"n_test={result.get('n_test', 0):>6} "
            f"AUC={result.get('test_auc', float('nan')):.4f} "
            f"sharpe={rm.get('sharpe', float('nan')):+.3f} "
            f"ann_pnl={rm.get('annual_pnl', 0):+.1f} "
            f"verdict={result.get('verdict', '-')} "
            f"({time.time() - t_cell:5.1f}s)"
        )

    # 4. Aggregate H3 / H4
    agg = aggregate_h3_h4(cell_results)
    print("")
    print("=== Aggregate H1/H2/H3/H4 ===")
    print(f"  best cell: {agg.get('best_cell')}")
    print(f"  best AUC : {agg.get('best_auc'):.4f}")
    print(
        f"  H3 lift  : {agg.get('h3_lift_observed'):+.4f} "
        f"(threshold >= {H3_LIFT_THRESHOLD}; PASS={agg.get('h3_pass')})"
    )
    print(f"  H4 sharpe: {agg.get('h4_realised_sharpe'):.4f} (PASS={agg.get('h4_pass')})")
    print(f"  {agg.get('h4_trigger_msg', '')}")

    # 5. Write report
    report_path = args.out_dir / "eval_report.md"
    write_eval_report(
        report_path,
        cell_results,
        agg,
        (t_min, t70, t85, t_max),
        feature_nan_drop_count,
        feature_nan_drop_rate_overall,
        feature_nan_drop_by_pair,
    )
    print(f"\nReport: {report_path}")

    # 6. Save sweep_results.json + parquet (gitignored)
    summary_rows = []
    for c in cell_results:
        rm = c.get("realised_metrics", {})
        summary_rows.append(
            {
                "subgroup": c["cell"]["subgroup"],
                "lookback": c["cell"]["lookback"],
                "zscore_window": c["cell"]["zscore_window"],
                "n_train": c.get("n_train", 0),
                "n_val": c.get("n_val", 0),
                "n_test": c.get("n_test", 0),
                "train_auc": c.get("train_auc", float("nan")),
                "val_auc": c.get("val_auc", float("nan")),
                "test_auc": c.get("test_auc", float("nan")),
                "verdict": c.get("verdict"),
                "h_state": c.get("h_state"),
                "n_trades": rm.get("n_trades", 0),
                "sharpe": rm.get("sharpe", float("nan")),
                "annual_pnl": rm.get("annual_pnl", 0.0),
                "max_dd": rm.get("max_dd", 0.0),
                "a4_n_positive": rm.get("a4_n_positive", 0),
                "a5_stressed_annual_pnl": rm.get("a5_stressed_annual_pnl", float("nan")),
                "low_power": c.get("low_power", False),
            }
        )
    summary_df = pd.DataFrame(summary_rows)
    summary_df.to_parquet(args.out_dir / "sweep_results.parquet")
    summary_df.to_json(args.out_dir / "sweep_results.json", orient="records", indent=2)

    # Also persist aggregate summary as JSON
    agg_serialisable = dict(agg)
    if agg_serialisable.get("best_cell") is not None:
        agg_serialisable["best_cell"] = dict(agg_serialisable["best_cell"])
    if agg_serialisable.get("best_realised_metrics"):
        agg_serialisable["best_realised_metrics"] = {
            k: (float(v) if isinstance(v, (np.floating, np.integer)) else v)
            for k, v in agg_serialisable["best_realised_metrics"].items()
        }
    (args.out_dir / "aggregate_summary.json").write_text(
        json.dumps(agg_serialisable, indent=2, default=str), encoding="utf-8"
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
