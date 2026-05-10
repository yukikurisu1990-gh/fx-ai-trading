"""Stage 25.0f-β — F5 liquidity / spread / volume eval.

Implements the binding contract from PR #295 (25.0f-α
docs/design/phase25_0f_alpha_f5_design.md). Reads 25.0a-β path-quality
labels, builds F5 features (F5-a spread regime, F5-b volume regime, F5-c
joint / interaction), trains 21 cells of logistic regression with
chronological 70/15/15 split, selects trade threshold on validation
only, evaluates test ONCE with realised barrier PnL via M1 path
re-traverse.

F5 is the LAST feature-axis attempt within Phase 25.

MANDATORY CLAUSES (verbatim per 25.0f-α §9):

1. Phase 25 framing.
   Phase 25 is the entry-side return on alternative admissible feature
   classes (F1-F6) layered on the 25.0a-β path-quality dataset. ADOPT
   requires both H2 PASS and the full 8-gate A0-A5 harness.

2. Diagnostic columns prohibition.
   Calibration / threshold-sweep / directional-comparison columns are
   diagnostic-only. ADOPT_CANDIDATE routing must not depend on any
   single one of them.

3. γ closure preservation.
   Phase 24 γ hard-close (PR #279) is unmodified.

4. Production-readiness preservation.
   X-v2 OOS gating remains required before any production deployment.

5. NG#10 / NG#11 not relaxed.

6. F5 verdict scoping.
   The 25.0f-β verdict applies only to the F5 best cell on the 25.0a-β-
   spread dataset. F5 is the LAST feature-axis attempt within Phase 25.
   F5 H4 FAIL strongly supports definitive feature-axis stop; next
   recommended routing consideration is R5 (soft close) or R2 (label
   redesign), but the user still chooses.

PRODUCTION-MISUSE GUARDS (verbatim per 25.0f-α §5.1):

GUARD 1 — research-not-production: F5 features stay in scripts/; not
auto-routed to feature_service.py.
GUARD 2 — threshold-sweep-diagnostic: any threshold sweep here is
diagnostic-only.
GUARD 3 — directional-comparison-diagnostic: any long/short
decomposition is diagnostic-only.

H3 reference: best-of-{F1, F2, F3} test AUC = 0.5644.
H3 PASS at F5 best AUC ≥ 0.5744 (lift ≥ 0.01).

Strict-causal rule (§2.7): F5 features at signal_ts=t use only bars
strictly before t (bars ≤ t-1). All spread / volume / joint series go
through shift(1) before any rolling aggregation.

F5-c regime tercile thresholds are FIT ON TRAIN SPLIT ONLY and applied
to val / test (no full-sample qcut).

F5-a spread basis: 25.0a-β path_quality_dataset.parquet
spread_at_signal_pip column (pip-normalised, signal-bar M5 spread).
Shifted by 1 before rolling.
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

# Windows console may default to cp932; force UTF-8.
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
ARTIFACT_ROOT = REPO_ROOT / "artifacts" / "stage25_0f"
DATA_DIR = REPO_ROOT / "data"
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

stage23_0a = importlib.import_module("stage23_0a_build_outcome_dataset")
stage25_0b = importlib.import_module("stage25_0b_f1_volatility_expansion_eval")

PAIRS_20 = stage23_0a.PAIRS_20
pip_size_for = stage23_0a.pip_size_for

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
THRESHOLD_CANDIDATES = stage25_0b.THRESHOLD_CANDIDATES


# ---------------------------------------------------------------------------
# Design constants (LOCKED per 25.0f-α)
# ---------------------------------------------------------------------------

# H3 reference per 25.0f-α §4.1: best-of-{F1, F2, F3} = 0.5644.
H3_REFERENCE_AUC = 0.5644
H3_LIFT_THRESHOLD = 0.01
H3_PASS_AUC = H3_REFERENCE_AUC + H3_LIFT_THRESHOLD  # 0.5744

H1_PASS_AUC = 0.55

# F5-c absolute z-score cutoffs (fixed hyperparameters, not train-fit)
F5C_HIGH_Z_CUTOFF = 1.0
F5C_LOW_Z_CUTOFF = -1.0

# Sweep grid per 25.0f-α §3 — 21 cells
CELL_SUBGROUPS = (
    "F5a",
    "F5b",
    "F5c",
    "F5a_F5b",
    "F5a_F5c",
    "F5b_F5c",
    "F5a_F5b_F5c",
)
CELL_LOOKBACKS = (20, 50, 100)

CATEGORICAL_COLS = ["pair", "direction"]

# Volume pre-flight thresholds
VOLUME_MIN_NONNULL_FRACTION = 0.99


# ---------------------------------------------------------------------------
# Volume pre-flight (§2.5.1 binding contract)
# ---------------------------------------------------------------------------


class VolumePreflightError(RuntimeError):
    """Raised when volume data is absent / sparse / non-causal."""


def _parse_oanda_ts(s: str) -> datetime:
    if s.endswith("Z"):
        s = s[:-1]
    if "." in s:
        head, frac = s.split(".", 1)
        frac = frac.rstrip("0")
        if len(frac) > 6:
            frac = frac[:6]
        s = head + ("." + frac if frac else "")
    return datetime.fromisoformat(s).replace(tzinfo=UTC)


def load_m1_with_volume(pair: str, days: int = SPAN_DAYS) -> pd.DataFrame:
    """Local M1 BA loader that PRESERVES the volume column.

    Mirrors stage23_0a.load_m1_ba but keeps `volume`. Returns a
    timezone-aware (UTC) DatetimeIndex DataFrame, sorted, dedup'd.
    """
    path = DATA_DIR / f"candles_{pair}_M1_{days}d_BA.jsonl"
    if not path.exists():
        raise FileNotFoundError(path)
    rows: list[dict] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            raw = json.loads(line)
            if "volume" not in raw:
                raise VolumePreflightError(
                    f"{pair}: jsonl row missing 'volume' field at {raw.get('time')}"
                )
            rows.append(
                {
                    "timestamp": _parse_oanda_ts(raw["time"]),
                    "volume": float(raw["volume"]),
                    "bid_o": float(raw["bid_o"]),
                    "bid_h": float(raw["bid_h"]),
                    "bid_l": float(raw["bid_l"]),
                    "bid_c": float(raw["bid_c"]),
                    "ask_o": float(raw["ask_o"]),
                    "ask_h": float(raw["ask_h"]),
                    "ask_l": float(raw["ask_l"]),
                    "ask_c": float(raw["ask_c"]),
                }
            )
    df = pd.DataFrame(rows).set_index("timestamp")
    df.index = pd.DatetimeIndex(df.index, tz=UTC)
    df = df[~df.index.duplicated(keep="first")].sort_index()
    return df


def verify_volume_preflight(
    pairs: list[str],
    days: int = SPAN_DAYS,
    min_nonnull_fraction: float = VOLUME_MIN_NONNULL_FRACTION,
) -> dict[str, dict]:
    """Halt-and-report contract per 25.0f-α §2.5.1.

    Verifies for each pair:
    - volume column present in M1 BA jsonl
    - non-null fraction >= min_nonnull_fraction
    - no negative volume values
    - M1 index strictly monotonic-increasing
    - M5 sum-aggregation index strictly monotonic-increasing

    Raises VolumePreflightError on any failure (no silent fallback).
    Returns per-pair diagnostic dict on success.
    """
    diag: dict[str, dict] = {}
    for pair in pairs:
        m1 = load_m1_with_volume(pair, days=days)
        if "volume" not in m1.columns:
            raise VolumePreflightError(f"{pair}: volume column absent")
        nn = float(m1["volume"].notna().mean())
        if nn < min_nonnull_fraction:
            raise VolumePreflightError(
                f"{pair}: volume non-null fraction {nn:.4f} < {min_nonnull_fraction}"
            )
        if (m1["volume"] < 0).any():
            raise VolumePreflightError(f"{pair}: negative volume detected")
        if not m1.index.is_monotonic_increasing:
            raise VolumePreflightError(f"{pair}: M1 index not monotonic")
        # M5 sum aggregate
        m5 = m1[["volume"]].resample("5min", label="right", closed="right").sum()
        if not m5.index.is_monotonic_increasing:
            raise VolumePreflightError(f"{pair}: M5 sum-volume index not monotonic")
        diag[pair] = {
            "m1_rows": int(len(m1)),
            "volume_nonnull_fraction": nn,
            "volume_min": float(m1["volume"].min()),
            "volume_mean": float(m1["volume"].mean()),
            "volume_max": float(m1["volume"].max()),
            "m5_sum_rows": int(len(m5)),
        }
    return diag


# ---------------------------------------------------------------------------
# F5-a spread (basis: 25.0a-β spread_at_signal_pip)
# ---------------------------------------------------------------------------


def compute_spread_z_for_pair(spread_series: pd.Series, lookback: int) -> pd.Series:
    """Causal rolling z-score of spread series.

    Strict-causal contract (§2.7): feature(t) uses bars <= t-1.
    Implementation: shift(1) BEFORE rolling stats.

    spread_series: pip-normalised spread time-series indexed by M5
                   signal_ts; one row per (pair, signal_ts). Source is
                   25.0a-β path_quality_dataset.parquet
                   spread_at_signal_pip column (already on the 25.0a-β
                   M5-signal-bar basis).
    """
    shifted = spread_series.shift(1)
    mean = shifted.rolling(lookback, min_periods=lookback).mean()
    std = shifted.rolling(lookback, min_periods=lookback).std()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        z = (shifted - mean) / std
    z[~np.isfinite(z)] = np.nan
    return z


# ---------------------------------------------------------------------------
# F5-b volume (basis: M1 jsonl volume aggregated to M5)
# ---------------------------------------------------------------------------


def compute_volume_z_for_pair(volume_series: pd.Series, lookback: int) -> pd.Series:
    """Causal rolling z-score of M5 sum-volume series.

    Strict-causal: shift(1) BEFORE rolling.
    """
    shifted = volume_series.shift(1)
    mean = shifted.rolling(lookback, min_periods=lookback).mean()
    std = shifted.rolling(lookback, min_periods=lookback).std()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        z = (shifted - mean) / std
    z[~np.isfinite(z)] = np.nan
    return z


# ---------------------------------------------------------------------------
# F5-c joint / interaction features (continuous + boolean only;
# the 9-bucket regime cross is computed PER CELL with TRAIN-fit terciles).
# ---------------------------------------------------------------------------


def compute_f5c_continuous_and_flags(
    spread_z: pd.Series,
    volume_z: pd.Series,
    lookback: int,
) -> pd.DataFrame:
    """F5-c continuous + boolean interaction terms.

    F5-c is interaction / joint-regime, NOT concat. Inputs spread_z and
    volume_z are already shift(1)-causal so all outputs are causal.
    F5-c MUST NOT be target-aware and MUST NOT use future information.

    Columns (4 per lookback):
    - f5c_spread_x_volume_<lb>     : continuous product
    - f5c_high_spread_high_vol_<lb>: bool (spread_z > 1.0 AND volume_z > 1.0)
    - f5c_high_spread_low_vol_<lb> : bool (spread_z > 1.0 AND volume_z < -1.0)
    - f5c_low_spread_high_vol_<lb> : bool (spread_z < -1.0 AND volume_z > 1.0)

    The 9-bucket regime cross is computed in `add_f5c_regime_cross_train_fit`
    per cell with TRAIN-fitted tercile thresholds (no full-sample qcut).
    """
    out = pd.DataFrame(index=spread_z.index)
    out[f"f5c_spread_x_volume_{lookback}"] = spread_z * volume_z
    out[f"f5c_high_spread_high_vol_{lookback}"] = (
        (spread_z > F5C_HIGH_Z_CUTOFF) & (volume_z > F5C_HIGH_Z_CUTOFF)
    ).astype(int)
    out[f"f5c_high_spread_low_vol_{lookback}"] = (
        (spread_z > F5C_HIGH_Z_CUTOFF) & (volume_z < F5C_LOW_Z_CUTOFF)
    ).astype(int)
    out[f"f5c_low_spread_high_vol_{lookback}"] = (
        (spread_z < F5C_LOW_Z_CUTOFF) & (volume_z > F5C_HIGH_Z_CUTOFF)
    ).astype(int)
    return out


def fit_terciles_on_train(values: pd.Series) -> tuple[float, float]:
    """Return (q33, q67) cutoffs from TRAIN values. No future leakage."""
    finite = values.dropna()
    if len(finite) < 30:
        # Degenerate: fall back to ±1 sentinels so apply path produces all bucket 1
        return (-1e18, +1e18)
    return (float(finite.quantile(1.0 / 3.0)), float(finite.quantile(2.0 / 3.0)))


def apply_terciles(values: pd.Series, q33: float, q67: float) -> pd.Series:
    """Apply train-fitted terciles to map values to {0, 1, 2}.

    Bucket 0 = below q33, Bucket 1 = [q33, q67), Bucket 2 = >= q67.
    NaN values stay NaN.
    """
    out = pd.Series(np.nan, index=values.index, dtype="float64")
    mask = values.notna()
    v = values[mask]
    bucket = pd.Series(1, index=v.index, dtype="int64")
    bucket[v < q33] = 0
    bucket[v >= q67] = 2
    out[mask] = bucket.astype("float64")
    return out


def f5c_regime_columns_for_lookback(lookback: int) -> list[str]:
    return [f"f5c_regime_{lookback}_{i}" for i in range(9)]


# ---------------------------------------------------------------------------
# Subgroup → feature columns mapping (per 25.0f-α §2.2 distinction)
# ---------------------------------------------------------------------------


def feature_columns_for_cell(subgroup: str, lookback: int) -> list[str]:
    """Return feature column names for a (subgroup, lookback) cell.

    F5-a + F5-b is CONCAT (2 columns: spread_z + volume_z).
    F5-c is INTERACTION (4 continuous/boolean + 9 regime = 13 columns).
    F5-a + F5-b + F5-c is the union (15 columns).
    """
    cols: list[str] = []
    if subgroup in ("F5a", "F5a_F5b", "F5a_F5c", "F5a_F5b_F5c"):
        cols.append(f"f5a_spread_z_{lookback}")
    if subgroup in ("F5b", "F5a_F5b", "F5b_F5c", "F5a_F5b_F5c"):
        cols.append(f"f5b_volume_z_{lookback}")
    if subgroup in ("F5c", "F5a_F5c", "F5b_F5c", "F5a_F5b_F5c"):
        cols.append(f"f5c_spread_x_volume_{lookback}")
        cols.append(f"f5c_high_spread_high_vol_{lookback}")
        cols.append(f"f5c_high_spread_low_vol_{lookback}")
        cols.append(f"f5c_low_spread_high_vol_{lookback}")
        cols.extend(f5c_regime_columns_for_lookback(lookback))
    return cols


def cell_uses_f5c(subgroup: str) -> bool:
    return subgroup in ("F5c", "F5a_F5c", "F5b_F5c", "F5a_F5b_F5c")


# ---------------------------------------------------------------------------
# Cell grid (21 cells)
# ---------------------------------------------------------------------------


def build_cells() -> list[dict]:
    cells: list[dict] = []
    for sg in CELL_SUBGROUPS:
        for lb in CELL_LOOKBACKS:
            cells.append({"subgroup": sg, "lookback": lb})
    return cells


CELL_GRID = build_cells()
assert len(CELL_GRID) == 21, f"expected 21 cells, got {len(CELL_GRID)}"


# ---------------------------------------------------------------------------
# Per-pair panel construction
# ---------------------------------------------------------------------------


def build_pair_panel(
    pair: str,
    spread_series: pd.Series,
    volume_series: pd.Series,
) -> pd.DataFrame:
    """Build per-pair feature panel keyed by signal_ts.

    Includes:
    - f5a_spread_z_<lb> for each lookback
    - f5b_volume_z_<lb> for each lookback
    - f5c continuous + boolean (4 cols) for each lookback

    Excludes the 9-bucket regime cross — that is computed per cell with
    TRAIN-fitted terciles in evaluate_cell.

    Index = signal_ts (M5 timestamp). spread_series and volume_series
    must already be aligned to the same M5 index.
    """
    parts: list[pd.DataFrame] = []
    for lb in CELL_LOOKBACKS:
        spread_z = compute_spread_z_for_pair(spread_series, lb).rename(f"f5a_spread_z_{lb}")
        volume_z = compute_volume_z_for_pair(volume_series, lb).rename(f"f5b_volume_z_{lb}")
        f5c_part = compute_f5c_continuous_and_flags(spread_z, volume_z, lb)
        parts.append(pd.concat([spread_z, volume_z, f5c_part], axis=1))
    panel = pd.concat(parts, axis=1)
    panel["pair"] = pair
    panel["signal_ts"] = panel.index
    return panel.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Build per-pair spread (from labels) and volume (from M1 jsonl)
# ---------------------------------------------------------------------------


def build_pair_spread_volume_series(
    pair: str,
    labels_pair: pd.DataFrame,
    days: int,
) -> tuple[pd.Series, pd.Series]:
    """Return (spread_series, volume_series) both indexed by M5 signal_ts.

    spread_series: from labels_pair.spread_at_signal_pip (dedup by signal_ts).
                   Per 25.0a-β, this is pip-normalised at the M5 signal bar.
                   Returned as-is; shift(1) is applied LATER in
                   compute_spread_z_for_pair.
    volume_series: from M1 jsonl `volume` aggregated M5-sum, then reindexed
                   onto the spread_series index (left-join). Same time
                   alignment as the labels.
    """
    spread = (
        labels_pair[["signal_ts", "spread_at_signal_pip"]]
        .drop_duplicates(subset=["signal_ts"])
        .set_index("signal_ts")
        .sort_index()
    )["spread_at_signal_pip"]

    m1 = load_m1_with_volume(pair, days=days)
    m5_sum_volume = (m1[["volume"]].resample("5min", label="right", closed="right").sum())["volume"]

    # Align volume to spread index (label set is the authority for which
    # signal_ts rows exist in 25.0a-β)
    volume = m5_sum_volume.reindex(spread.index)
    return spread, volume


# ---------------------------------------------------------------------------
# Decile reliability calibration (diagnostic-only)
# ---------------------------------------------------------------------------


def calibration_decile_check(p: np.ndarray, label: np.ndarray) -> dict:
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
    rows: list[dict] = []
    for bucket_id, sub in df.groupby("bucket"):
        bucket_brier = brier_score_loss(sub["label"].to_numpy(), sub["p"].to_numpy())
        rows.append(
            {
                "bucket": int(bucket_id),
                "p_hat_mean": float(sub["p"].mean()),
                "realised_win_rate": float(sub["label"].mean()),
                "n": int(len(sub)),
                "brier": float(bucket_brier),
            }
        )
    rates = [r["realised_win_rate"] for r in rows]
    monotonic = all(rates[i] <= rates[i + 1] for i in range(len(rates) - 1))
    overall_brier = float(brier_score_loss(label, p))
    low_n = n < 100
    return {
        "n": n,
        "monotonic": bool(monotonic),
        "buckets": rows,
        "overall_brier": overall_brier,
        "low_n_flag": bool(low_n),
    }


# ---------------------------------------------------------------------------
# Per-cell verdict (per 25.0f-α §7)
# ---------------------------------------------------------------------------


def assign_cell_verdict(test_auc: float, gates: dict[str, bool], n_trades: int) -> tuple[str, str]:
    h1_pass = np.isfinite(test_auc) and test_auc >= H1_PASS_AUC
    if not h1_pass:
        return "REJECT_NON_DISCRIMINATIVE", "H1_FAIL"
    h2_pass = gates.get("A1", False) and gates.get("A2", False)
    if not h2_pass:
        return "REJECT_BUT_INFORMATIVE", "H1_PASS_H2_FAIL"
    all_keys = ("A0", "A1", "A2", "A3", "A4", "A5")
    if all(gates.get(k, False) for k in all_keys):
        return "ADOPT_CANDIDATE", "ALL_GATES_PASS"
    a3_a5 = ("A3", "A4", "A5")
    n_a3_a5_pass = sum(1 for k in a3_a5 if gates.get(k, False))
    if n_a3_a5_pass >= 1:
        return "PROMISING_BUT_NEEDS_OOS", "H1_H2_PASS_A3_A5_PARTIAL"
    return "REJECT", "H1_H2_PASS_A3_A5_FAIL"


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
# Add F5-c regime cross with TRAIN-FITTED terciles (per 25.0f-α correction)
# ---------------------------------------------------------------------------


def add_f5c_regime_cross_train_fit(
    train: pd.DataFrame,
    val: pd.DataFrame,
    test: pd.DataFrame,
    lookback: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Fit spread/volume terciles ON TRAIN and apply to all 3 splits.

    NO full-sample qcut. NO future leakage. Adds 9 one-hot columns
    f5c_regime_<lb>_0 .. f5c_regime_<lb>_8 for the spread-tercile ×
    volume-tercile cross.
    """
    spread_col = f"f5a_spread_z_{lookback}"
    volume_col = f"f5b_volume_z_{lookback}"

    if spread_col not in train.columns or volume_col not in train.columns:
        raise ValueError(
            f"add_f5c_regime_cross_train_fit: panel must include {spread_col} and "
            f"{volume_col} before regime cross is fitted"
        )

    sq33, sq67 = fit_terciles_on_train(train[spread_col])
    vq33, vq67 = fit_terciles_on_train(train[volume_col])

    out_dfs: list[pd.DataFrame] = []
    for df in (train, val, test):
        df = df.copy()
        spread_tercile = apply_terciles(df[spread_col], sq33, sq67)
        volume_tercile = apply_terciles(df[volume_col], vq33, vq67)
        regime = (spread_tercile * 3 + volume_tercile).astype("Int64")
        for i in range(9):
            df[f"f5c_regime_{lookback}_{i}"] = (regime == i).astype("Int8")
        out_dfs.append(df)
    return out_dfs[0], out_dfs[1], out_dfs[2]


# ---------------------------------------------------------------------------
# Per-cell evaluation
# ---------------------------------------------------------------------------


def evaluate_cell(
    cell: dict,
    splits: tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame],
    pair_runtime: dict,
) -> dict:
    subgroup = cell["subgroup"]
    lookback = cell["lookback"]
    train_df, val_df, test_df = splits

    n_train, n_val, n_test = len(train_df), len(val_df), len(test_df)
    if n_train < 100 or n_val < 50 or n_test < 50:
        return {
            "cell": cell,
            "feature_cols": [],
            "n_train": n_train,
            "n_val": n_val,
            "n_test": n_test,
            "test_auc": float("nan"),
            "verdict": "REJECT_NON_DISCRIMINATIVE",
            "h_state": "INSUFFICIENT_DATA",
            "low_power": True,
            "skip_reason": "insufficient sample",
        }

    # If F5-c is in the cell, fit regime terciles on train and apply to all.
    if cell_uses_f5c(subgroup):
        train_df, val_df, test_df = add_f5c_regime_cross_train_fit(
            train_df, val_df, test_df, lookback
        )

    feature_cols = feature_columns_for_cell(subgroup, lookback)
    # Drop rows with NaN in any feature for the cell (per-cell because
    # different lookbacks have different warmup)
    for split_df in (train_df, val_df, test_df):
        nan_mask = split_df[feature_cols].isna().any(axis=1)
        if nan_mask.any():
            split_df.drop(split_df[nan_mask].index, inplace=True)
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
            "h_state": "INSUFFICIENT_DATA_AFTER_NAN_DROP",
            "low_power": True,
            "skip_reason": "insufficient sample after feature NaN drop",
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
# Aggregate H3 / H4
# ---------------------------------------------------------------------------


def aggregate_h3_h4(cell_results: list[dict]) -> dict:
    valid = [
        c
        for c in cell_results
        if np.isfinite(c.get("test_auc", float("nan")))
        and c.get("h_state")
        not in (
            "INSUFFICIENT_DATA",
            "INSUFFICIENT_DATA_AFTER_NAN_DROP",
            "PIVOT_INSUFFICIENT",
        )
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
    best = max(valid, key=lambda c: c["test_auc"])
    best_auc = float(best["test_auc"])
    h3_lift = best_auc - H3_REFERENCE_AUC
    h3_pass = h3_lift >= H3_LIFT_THRESHOLD
    rm = best.get("realised_metrics", {})
    sharpe = rm.get("sharpe", float("nan"))
    h4_pass = bool(np.isfinite(sharpe) and sharpe >= 0.0)
    if not h4_pass:
        h4_msg = (
            "H4 FAIL — F5 best-cell realised Sharpe < 0 at AUC ≈ structural-gap "
            "regime. This strongly supports definitive feature-axis stop within "
            "Phase 25, but the user still chooses (next routing consideration: "
            "R5 soft close or R2 label redesign)."
        )
    else:
        h4_msg = "H4 PASS — F5 escapes the AUC-PnL gap (surprising but possible)."
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
    volume_preflight_diag: dict[str, dict],
) -> None:
    t_min, t70, t85, t_max = split_dates
    lines: list[str] = []
    lines.append("# Stage 25.0f-β — F5 Liquidity / Spread / Volume Eval")
    lines.append("")
    lines.append(f"Generated: {datetime.now(UTC).isoformat()}")
    lines.append("")
    lines.append("Design contract: `docs/design/phase25_0f_alpha_f5_design.md` (PR #295)")
    lines.append("")
    lines.append(
        "**F5 is the LAST feature-axis attempt within Phase 25** per PR #294 routing review."
    )
    lines.append("")
    lines.append("## Mandatory clauses (verbatim per 25.0f-α §9)")
    lines.append("")
    lines.append(
        "**1. Phase 25 framing.** Phase 25 is the entry-side return on "
        "alternative admissible feature classes (F1-F6) layered on the 25.0a-β "
        "path-quality dataset. ADOPT requires both H2 PASS and the full 8-gate "
        "A0-A5 harness."
    )
    lines.append("")
    lines.append(
        "**2. Diagnostic columns prohibition.** Calibration / threshold-sweep / "
        "directional-comparison columns are diagnostic-only. ADOPT_CANDIDATE "
        "routing must not depend on any single one of them."
    )
    lines.append("")
    lines.append("**3. γ closure preservation.** Phase 24 γ hard-close (PR #279) is unmodified.")
    lines.append("")
    lines.append(
        "**4. Production-readiness preservation.** X-v2 OOS gating remains "
        "required before any production deployment."
    )
    lines.append("")
    lines.append("**5. NG#10 / NG#11 not relaxed.**")
    lines.append("")
    lines.append(
        "**6. F5 verdict scoping.** The 25.0f-β verdict applies only to the F5 "
        "best cell on the 25.0a-β-spread dataset. F5 is the LAST feature-axis "
        "attempt within Phase 25. F5 H4 FAIL strongly supports definitive "
        "feature-axis stop; next recommended routing consideration is R5 "
        "(soft close) or R2 (label redesign), but the user still chooses."
    )
    lines.append("")
    lines.append("## Production-misuse guards (verbatim per 25.0f-α §5.1)")
    lines.append("")
    lines.append(
        "**GUARD 1 — research-not-production**: F5 features stay in scripts/; "
        "not auto-routed to feature_service.py."
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
    lines.append("## Causality / leakage notes")
    lines.append("")
    lines.append(
        "F5 features at signal_ts=t use only bars strictly before t (bars ≤ t-1). "
        "All spread / volume / joint series go through `shift(1)` before any "
        "rolling aggregation. Bar-t lookahead unit tests cover F5-a, F5-b, F5-c."
    )
    lines.append("")
    lines.append(
        "**F5-c regime tercile thresholds are FIT ON TRAIN SPLIT ONLY** and "
        "applied to val/test (no full-sample qcut). spread_z and volume_z "
        "tercile cutoffs come from the train portion of the chronological "
        "70/15/15 split per cell."
    )
    lines.append("")
    lines.append(
        "**F5-a spread basis**: 25.0a-β `spread_at_signal_pip` column "
        "(pip-normalised, signal-bar M5 spread). Values are dedup'd by "
        "(pair, signal_ts) then `shift(1)` is applied before rolling stats."
    )
    lines.append("")
    lines.append("## Volume pre-flight (§2.5.1 binding contract)")
    lines.append("")
    lines.append("| pair | m1_rows | non-null fraction | m1 vol min/mean/max | m5_sum_rows |")
    lines.append("|---|---|---|---|---|")
    for pair, d in sorted(volume_preflight_diag.items()):
        lines.append(
            f"| {pair} | {d['m1_rows']} | {d['volume_nonnull_fraction']:.6f} | "
            f"{d['volume_min']:.0f} / {d['volume_mean']:.2f} / {d['volume_max']:.0f} | "
            f"{d['m5_sum_rows']} |"
        )
    lines.append("")
    lines.append(
        f"All pairs met the binding contract: non-null ≥ "
        f"{VOLUME_MIN_NONNULL_FRACTION}, no negatives, monotonic indices."
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
    lines.append("## H3 reference (binding from 25.0f-α §4.1)")
    lines.append("")
    lines.append(
        f"- best-of-{{F1, F2, F3}} test AUC = {H3_REFERENCE_AUC:.4f} "
        "(F1 rank-1 = 0.5644; F2 rank-1 = 0.5613; F3 rank-1 = 0.5480)"
    )
    lines.append(f"- H3 PASS threshold = {H3_PASS_AUC:.4f} (lift ≥ 0.01)")
    lines.append("")
    lines.append("## Split dates")
    lines.append("")
    lines.append(f"- min: {t_min}")
    lines.append(f"- train < {t70}")
    lines.append(f"- val [{t70}, {t85})")
    lines.append(f"- test [{t85}, {t_max}]")
    lines.append("")
    lines.append("## Feature NaN drop (lookback warmup)")
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

    sorted_by_auc = sorted(
        cell_results,
        key=lambda c: c.get("test_auc", -1) if np.isfinite(c.get("test_auc", -1)) else -1,
        reverse=True,
    )
    lines.append("## All 21 cells — summary (sorted by test AUC desc)")
    lines.append("")
    lines.append(
        "| subgroup | lookback | n_train | n_test | "
        "train_AUC | val_AUC | test_AUC | gap | verdict | h_state | "
        "n_trades | sharpe | ann_pnl | A4 | A5_ann | low_power |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for c in sorted_by_auc:
        cell = c["cell"]
        rm = c.get("realised_metrics", {})
        lines.append(
            f"| {cell['subgroup']} | {cell['lookback']} | "
            f"{c.get('n_train', 0)} | {c.get('n_test', 0)} | "
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

    lines.append("## Top-3 cells by test AUC — expanded breakdown")
    lines.append("")
    for c in sorted_by_auc[:3]:
        cell = c["cell"]
        lines.append(f"### Cell: subgroup={cell['subgroup']}, lookback={cell['lookback']}")
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

    lines.append("## Aggregate H1 / H2 / H3 / H4 outcome")
    lines.append("")
    bc = agg.get("best_cell")
    lines.append(f"- Best F5 cell: **{bc}** with test AUC {agg.get('best_auc', float('nan')):.4f}")
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

    lines.append("## Routing recommendation framing (non-decisive)")
    lines.append("")
    lines.append(
        "This section lists which §7 verdict tree branch the best cell falls into. "
        "It is informational. The actual routing decision (R5 soft close / R2 "
        "label redesign / continue) is handed to the next PR. **F5 H4 FAIL "
        "strongly supports definitive feature-axis stop within Phase 25, but the "
        "user still chooses.**"
    )
    lines.append("")
    if bc is not None:
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

    lines.append("## Multiple-testing caveat")
    lines.append("")
    lines.append(
        "These are 21 evaluated cells. PROMISING_BUT_NEEDS_OOS / ADOPT_CANDIDATE "
        "verdicts are hypothesis-generating ONLY; production-readiness requires "
        "an X-v2-equivalent frozen-OOS PR per Phase 22 contract."
    )
    lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def _build_pair_runtime(pair: str, days: int) -> dict:
    m1 = load_m1_with_volume(pair, days=days)
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
    args = parser.parse_args(argv)

    args.out_dir.mkdir(parents=True, exist_ok=True)

    print(f"=== Stage 25.0f-beta F5 eval ({len(args.pairs)} pairs) ===")
    print(
        f"H1={H1_PASS_AUC:.2f} | H3 ref AUC={H3_REFERENCE_AUC:.4f} "
        f"| H3 pass >= {H3_PASS_AUC:.4f} | cells={len(CELL_GRID)}"
    )

    # 0. Volume pre-flight (HALT-AND-REPORT contract)
    print("Volume pre-flight check (§2.5.1 binding contract)...")
    t0 = time.time()
    try:
        volume_preflight_diag = verify_volume_preflight(args.pairs, days=args.days)
    except VolumePreflightError as exc:
        print(f"VOLUME PRE-FLIGHT FAILED: {exc}")
        return 2
    print(f"  Pre-flight passed for {len(volume_preflight_diag)} pairs ({time.time() - t0:5.1f}s)")

    # 1. Load 25.0a-β labels
    print("Loading 25.0a-β path-quality labels...")
    labels = load_path_quality_labels()
    if args.pairs != PAIRS_20:
        labels = labels[labels["pair"].isin(args.pairs)]
    print(f"  labels rows: {len(labels)}")

    # 2. Per-pair: build spread + volume series, compute panel, build runtime
    pair_runtime: dict[str, dict] = {}
    panels: list[pd.DataFrame] = []
    print("Building per-pair F5 panels + M1 runtime...")
    for pair in args.pairs:
        t_pair = time.time()
        labels_pair = labels[labels["pair"] == pair]
        spread, volume = build_pair_spread_volume_series(pair, labels_pair, days=args.days)
        panel = build_pair_panel(pair, spread, volume)
        panels.append(panel)
        pair_runtime[pair] = _build_pair_runtime(pair, days=args.days)
        print(
            f"  {pair}: panel rows {len(panel)} "
            f"(m1 rows {pair_runtime[pair]['n_m1']}, "
            f"{time.time() - t_pair:5.1f}s)"
        )
    panel_all = pd.concat(panels, ignore_index=True)

    # 3. Join panel to labels (on pair, signal_ts)
    panel_all["pair"] = panel_all["pair"].astype("object")
    labels["pair"] = labels["pair"].astype("object")
    merged = pd.merge(labels, panel_all, on=["pair", "signal_ts"], how="inner")
    n_before_drop = len(merged)
    print(f"  merged rows: {n_before_drop}")

    # We do NOT drop NaN at the panel level here — different cells have
    # different lookbacks; per-cell NaN drop happens inside evaluate_cell.

    # Per-pair drop bookkeeping for the report (using lookback=20 / F5-a as
    # representative warmup). The cell loop tracks its own n_train/n_val/n_test.
    repr_col = "f5a_spread_z_20"
    feature_nan_mask = merged[repr_col].isna()
    feature_nan_drop_count = int(feature_nan_mask.sum())
    feature_nan_drop_rate_overall = (
        feature_nan_drop_count / n_before_drop if n_before_drop > 0 else 0.0
    )
    feature_nan_drop_by_pair: dict[str, dict] = {}
    for pair in args.pairs:
        n_pair_before = (merged["pair"] == pair).sum()
        n_pair_after = ((merged["pair"] == pair) & ~feature_nan_mask).sum()
        drop = int(n_pair_before - n_pair_after)
        rate = drop / n_pair_before if n_pair_before > 0 else 0.0
        feature_nan_drop_by_pair[pair] = {"count": drop, "rate": rate}

    # 4. Chronological split (on full merged; per-cell NaN drop is later)
    train_df, val_df, test_df, t70, t85 = split_70_15_15(merged)
    t_min = merged["signal_ts"].min()
    t_max = merged["signal_ts"].max()
    print(f"  split: train={len(train_df)}, val={len(val_df)}, test={len(test_df)}")

    # 5. Per-cell sweep
    cell_results: list[dict] = []
    for i, cell in enumerate(CELL_GRID):
        t_cell = time.time()
        result = evaluate_cell(cell, (train_df, val_df, test_df), pair_runtime)
        cell_results.append(result)
        rm = result.get("realised_metrics", {})
        print(
            f"  cell {i + 1}/21 sg={cell['subgroup']:14} lb={cell['lookback']:3} "
            f"n_test={result.get('n_test', 0):>7} "
            f"AUC={result.get('test_auc', float('nan')):.4f} "
            f"sharpe={rm.get('sharpe', float('nan')):+.3f} "
            f"ann_pnl={rm.get('annual_pnl', 0):+.1f} "
            f"verdict={result.get('verdict', '-')} "
            f"({time.time() - t_cell:5.1f}s)"
        )

    # 6. Aggregate H3 / H4
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

    # 7. Write report
    report_path = args.out_dir / "eval_report.md"
    write_eval_report(
        report_path,
        cell_results,
        agg,
        (t_min, t70, t85, t_max),
        feature_nan_drop_count,
        feature_nan_drop_rate_overall,
        feature_nan_drop_by_pair,
        volume_preflight_diag,
    )
    print(f"\nReport: {report_path}")

    # 8. Save sweep_results + aggregate_summary
    summary_rows = []
    for c in cell_results:
        rm = c.get("realised_metrics", {})
        summary_rows.append(
            {
                "subgroup": c["cell"]["subgroup"],
                "lookback": c["cell"]["lookback"],
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
