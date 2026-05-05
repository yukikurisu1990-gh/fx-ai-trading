"""Stage 22.0e-v2 Independent OOS Validation.

Single-cell verification of PR #259's PROMISING_BUT_NEEDS_OOS finding.
NO re-search. NO sweep. ONE cell. ONE model.

Frozen specification:
    primary signal: Donchian-immediate breakout
    N_DONCHIAN     = 50
    CONF_THRESHOLD = 0.55
    HORIZON_BARS   = 40
    EXIT_RULE      = "time_exit_pnl"
    FEATURE_SET    = stage22_0e_meta_labeling.MAIN_FEATURE_COLS

Train: first 80% of the 730d data by entry_ts. Test: last 20% (~146d).
Single LightGBM model, time-ordered early-stopping validation. OOS sub-folds
(4) are diagnostic-only — never used for training.

Verdict (3-class, audit-aligned):
- ADOPT: A0..A5 + S0 + S1 all pass on OOS. Paper-run prerequisite, not
  production-ready.
- PROMISING_CONFIRMED: A1 (Sharpe) AND A2 (PnL) AND S0 AND S1 pass, but
  one of A3/A4/A5 fails (risk gate).
- FAILED_OOS: A1 OR A2 fail; OR A0 fail (no statistical power); OR S0 OR
  S1 fail (contamination / overfit).

Touches NO src/ files, NO scripts/run_*.py, NO DB schema. 20-pair
canonical universe; no pair / time filter.
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
import time
import warnings
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd

warnings.filterwarnings(
    "ignore",
    message="no explicit representation of timezones available for np.datetime64",
)

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = REPO_ROOT / "artifacts" / "stage22_0e_v2"
PR259_SCRIPT = REPO_ROOT / "scripts" / "stage22_0e_meta_labeling.py"


# ---------------------------------------------------------------------------
# Import PR #259 module dynamically (it's not a package, just a script)
# ---------------------------------------------------------------------------


def _load_pr259_module():
    spec = importlib.util.spec_from_file_location("stage22_0e_pr259", PR259_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load PR #259 script at {PR259_SCRIPT}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["stage22_0e_pr259"] = mod
    spec.loader.exec_module(mod)
    return mod


_PR259 = _load_pr259_module()

# Pull the frozen constants and helpers from PR #259 (no redefinition)
MAIN_FEATURE_COLS = _PR259.MAIN_FEATURE_COLS
FORBIDDEN_FEATURES = _PR259.FORBIDDEN_FEATURES
PAIRS_CANONICAL_20 = _PR259.PAIRS_CANONICAL_20
LGBM_PARAMS = _PR259.LGBM_PARAMS

ADOPT_MIN_TRADES = _PR259.ADOPT_MIN_TRADES
ADOPT_MIN_SHARPE = _PR259.ADOPT_MIN_SHARPE
ADOPT_MIN_PNL = _PR259.ADOPT_MIN_PNL
ADOPT_MAX_DD = _PR259.ADOPT_MAX_DD
ADOPT_MIN_FOLD_POSNEG = _PR259.ADOPT_MIN_FOLD_POSNEG
S0_HARD_GATE = _PR259.S0_HARD_GATE
S0_DIAGNOSTIC = _PR259.S0_DIAGNOSTIC
S1_MAX_TRAIN_TEST_GAP = _PR259.S1_MAX_TRAIN_TEST_GAP
OVERTRADE_WARN_TRADES = _PR259.OVERTRADE_WARN_TRADES

# ---------------------------------------------------------------------------
# Frozen cell — DO NOT VARY (asserted by unit tests)
# ---------------------------------------------------------------------------

PRIMARY_SIGNAL = "donchian_immediate"
N_DONCHIAN = 50
CONF_THRESHOLD = 0.55
HORIZON_BARS = 40
EXIT_RULE = "time_exit_pnl"

# Train / OOS split
TRAIN_FRAC = 0.80
ES_VAL_FRAC = 0.20  # within-train, time-ordered last 20%

# OOS sub-folds for diagnostic stability
N_OOS_SUBFOLDS = 4

# Spread stress
SPREAD_STRESS_PIPS: tuple[float, ...] = (0.0, 0.2, 0.5)


# ---------------------------------------------------------------------------
# Helpers (a few re-implemented to keep dependencies minimal)
# ---------------------------------------------------------------------------


def _categorical_columns(features: list[str]) -> list[str]:
    return [c for c in ("pair", "direction") if c in features]


def _prepare_lgbm_frame(df: pd.DataFrame, features: list[str]) -> pd.DataFrame:
    out = df[features].copy()
    for c in _categorical_columns(features):
        out[c] = out[c].astype("category")
    return out


def per_trade_sharpe(pnl: np.ndarray) -> float:
    if pnl.size < 2:
        return 0.0
    mean = float(np.mean(pnl))
    var = float(np.var(pnl, ddof=0))
    if var <= 0:
        return 0.0
    return mean / np.sqrt(var)


def annualize(total: float, span_years: float) -> float:
    return 0.0 if span_years <= 0 else total / span_years


def max_drawdown(pnl: np.ndarray) -> float:
    if pnl.size == 0:
        return 0.0
    eq = np.cumsum(pnl)
    peak = np.maximum.accumulate(eq)
    return float((peak - eq).max())


def time_ordered_es_split(
    train_ts: np.ndarray, frac: float = ES_VAL_FRAC
) -> tuple[np.ndarray, np.ndarray]:
    """Time-ordered last `frac` of the train range as ES validation. NOT random."""
    if train_ts.size == 0:
        return np.array([], dtype=int), np.array([], dtype=int)
    val_cut = np.quantile(train_ts, 1.0 - frac)
    fit_mask = train_ts <= val_cut
    val_mask = train_ts > val_cut
    return np.where(fit_mask)[0], np.where(val_mask)[0]


def chronological_4_subfolds(oos_ts: np.ndarray) -> list[tuple[int, int]]:
    """Return list of (start_idx, end_idx) for 4 chronological sub-folds.

    Indices are positions into the sorted OOS array.
    """
    if oos_ts.size < 4:
        return []
    n = oos_ts.size
    edges = [int(n * i / N_OOS_SUBFOLDS) for i in range(N_OOS_SUBFOLDS + 1)]
    edges[-1] = n
    return [(edges[k], edges[k + 1]) for k in range(N_OOS_SUBFOLDS)]


# ---------------------------------------------------------------------------
# Train + OOS predict (single model)
# ---------------------------------------------------------------------------


@dataclass
class OOSResult:
    n_train: int = 0
    n_oos: int = 0
    n_oos_filtered: int = 0
    oos_span_years: float = 0.0

    train_sharpe: float = 0.0  # on filtered conf>=threshold trades within train
    oos_sharpe: float = 0.0
    oos_annual_pnl: float = 0.0
    oos_annual_trades: float = 0.0
    oos_max_dd: float = 0.0
    oos_dd_pct: float = 0.0
    oos_mean_pnl: float = 0.0
    oos_win_rate: float = 0.0

    oos_annual_pnl_stress_02: float = 0.0
    oos_annual_pnl_stress_05: float = 0.0

    sub_fold_pnls: list[float] = field(default_factory=list)
    sub_fold_ns: list[int] = field(default_factory=list)
    sub_fold_sharpes: list[float] = field(default_factory=list)
    sub_fold_pos: int = 0
    sub_fold_neg: int = 0
    sub_fold_ranges: list[tuple[str, str]] = field(default_factory=list)

    train_test_gap: float = 0.0
    shuffled_sharpe: float = 0.0

    feature_importance: dict[str, float] = field(default_factory=dict)
    oos_trades_df: pd.DataFrame | None = None


def evaluate_frozen_cell(
    full_df: pd.DataFrame,
    shuffle_y: bool = False,
) -> OOSResult:
    """Train a single LightGBM model on first 80%, evaluate on last 20%."""
    sub = full_df[full_df["horizon_bars"] == HORIZON_BARS]
    if sub.empty:
        return OOSResult()
    sub = sub.sort_values("entry_ts").reset_index(drop=True)
    entry_ts_int = sub["entry_ts"].values.astype("datetime64[ns]").view("int64")
    pnl_full = sub[EXIT_RULE].to_numpy(dtype=np.float64)
    y_full = (pnl_full > 0).astype(np.int8)

    # Chronological split: first 80% = train, last 20% = OOS
    cut_int = int(np.quantile(entry_ts_int, TRAIN_FRAC))
    train_mask = entry_ts_int <= cut_int
    oos_mask = entry_ts_int > cut_int
    train_idx = np.where(train_mask)[0]
    oos_idx = np.where(oos_mask)[0]

    if train_idx.size < 1000 or oos_idx.size < 100:
        return OOSResult(n_train=int(train_idx.size), n_oos=int(oos_idx.size))

    # Within-train ES split (time-ordered last 20%)
    train_ts_arr = entry_ts_int[train_idx]
    fit_local, val_local = time_ordered_es_split(train_ts_arr, ES_VAL_FRAC)
    fit_idx = train_idx[fit_local]
    val_idx = train_idx[val_local]

    # Optional within-fold shuffle (S0 sanity)
    y_for_train = y_full.copy()
    if shuffle_y:
        rng = np.random.default_rng(0)
        shuffled = y_for_train[train_idx].copy()
        rng.shuffle(shuffled)
        y_for_train[train_idx] = shuffled

    features = list(MAIN_FEATURE_COLS)
    cats = _categorical_columns(features)

    X_fit = _prepare_lgbm_frame(sub.iloc[fit_idx], features)  # noqa: N806
    X_val = _prepare_lgbm_frame(sub.iloc[val_idx], features)  # noqa: N806
    X_train_all = _prepare_lgbm_frame(sub.iloc[train_idx], features)  # noqa: N806
    X_oos = _prepare_lgbm_frame(sub.iloc[oos_idx], features)  # noqa: N806

    train_set = lgb.Dataset(X_fit, label=y_for_train[fit_idx], categorical_feature=cats)
    val_set = lgb.Dataset(
        X_val,
        label=y_for_train[val_idx],
        categorical_feature=cats,
        reference=train_set,
    )
    booster = lgb.train(
        params={k: v for k, v in LGBM_PARAMS.items() if k != "n_estimators"},
        train_set=train_set,
        num_boost_round=LGBM_PARAMS["n_estimators"],
        valid_sets=[val_set],
        callbacks=[
            lgb.early_stopping(stopping_rounds=20, verbose=False),
            lgb.log_evaluation(period=0),
        ],
    )

    # Train-set predictions (filtered)
    train_pred = booster.predict(X_train_all)
    train_keep = train_pred >= CONF_THRESHOLD
    train_sharpe = per_trade_sharpe(pnl_full[train_idx][train_keep]) if train_keep.any() else 0.0

    # OOS predictions (filtered)
    oos_pred = booster.predict(X_oos)
    oos_keep = oos_pred >= CONF_THRESHOLD
    if not oos_keep.any():
        return OOSResult(
            n_train=int(train_idx.size),
            n_oos=int(oos_idx.size),
            n_oos_filtered=0,
            train_sharpe=train_sharpe,
        )

    kept_idx = oos_idx[oos_keep]
    kept_pnl = pnl_full[kept_idx]
    kept_ts = sub["entry_ts"].iloc[kept_idx].values
    kept_pred = oos_pred[oos_keep]
    kept_pair = sub["pair"].iloc[kept_idx].values
    kept_dir = sub["direction"].iloc[kept_idx].values
    kept_hour = sub["hour_utc"].iloc[kept_idx].values  # diagnostic only
    kept_dow = sub["dow"].iloc[kept_idx].values  # diagnostic only

    # OOS span (in years)
    span = (kept_ts.max() - kept_ts.min()) / np.timedelta64(1, "s") / (365.25 * 86400.0)
    span_years = float(span) if span > 0 else 1e-9

    oos_sharpe = per_trade_sharpe(kept_pnl)
    oos_annual_pnl = annualize(float(kept_pnl.sum()), span_years)
    oos_annual_trades = kept_pnl.size / span_years
    oos_max_dd = max_drawdown(kept_pnl)
    oos_dd_pct = (
        (oos_max_dd / abs(oos_annual_pnl)) * 100.0 if abs(oos_annual_pnl) > 1e-9 else float("inf")
    )
    oos_mean_pnl = float(kept_pnl.mean())
    oos_win_rate = float((kept_pnl > 0).mean())

    oos_annual_stress_02 = annualize(float((kept_pnl - 0.2).sum()), span_years)
    oos_annual_stress_05 = annualize(float((kept_pnl - 0.5).sum()), span_years)

    # Sub-folds (diagnostic, on filtered OOS chronological order)
    kept_ts_int = kept_ts.astype("datetime64[ns]").view("int64")
    sub_fold_ranges: list[tuple[str, str]] = []
    sub_pnls: list[float] = []
    sub_ns: list[int] = []
    sub_sharpes: list[float] = []
    for s, e in chronological_4_subfolds(kept_ts_int):
        sub_pnl_arr = kept_pnl[s:e]
        sub_pnls.append(float(sub_pnl_arr.sum()))
        sub_ns.append(int(sub_pnl_arr.size))
        sub_sharpes.append(per_trade_sharpe(sub_pnl_arr))
        sub_fold_ranges.append((str(kept_ts[s]), str(kept_ts[e - 1])))
    sub_fold_pos = sum(1 for v in sub_pnls if v > 0)
    sub_fold_neg = sum(1 for v in sub_pnls if v < 0)

    # Feature importance (gain)
    fi: dict[str, float] = {f: 0.0 for f in features if f not in cats}
    for fname, gain in zip(
        booster.feature_name(),
        booster.feature_importance(importance_type="gain"),
        strict=False,
    ):
        if fname in fi:
            fi[fname] = float(gain)

    # Trade list for diagnostics
    oos_trades_df = pd.DataFrame(
        {
            "entry_ts": kept_ts,
            "pair": kept_pair,
            "direction": kept_dir,
            "predicted_P": kept_pred,
            "pnl": kept_pnl,
            "hour_utc": kept_hour,
            "dow": kept_dow,
        }
    )

    return OOSResult(
        n_train=int(train_idx.size),
        n_oos=int(oos_idx.size),
        n_oos_filtered=int(kept_pnl.size),
        oos_span_years=span_years,
        train_sharpe=train_sharpe,
        oos_sharpe=oos_sharpe,
        oos_annual_pnl=oos_annual_pnl,
        oos_annual_trades=oos_annual_trades,
        oos_max_dd=oos_max_dd,
        oos_dd_pct=oos_dd_pct,
        oos_mean_pnl=oos_mean_pnl,
        oos_win_rate=oos_win_rate,
        oos_annual_pnl_stress_02=oos_annual_stress_02,
        oos_annual_pnl_stress_05=oos_annual_stress_05,
        sub_fold_pnls=sub_pnls,
        sub_fold_ns=sub_ns,
        sub_fold_sharpes=sub_sharpes,
        sub_fold_pos=sub_fold_pos,
        sub_fold_neg=sub_fold_neg,
        sub_fold_ranges=sub_fold_ranges,
        train_test_gap=train_sharpe - oos_sharpe,
        feature_importance=fi,
        oos_trades_df=oos_trades_df,
    )


# ---------------------------------------------------------------------------
# Verdict (user-revised boundaries)
# ---------------------------------------------------------------------------


def classify_verdict(
    real: OOSResult, shuffled_sharpe: float
) -> tuple[str, dict[str, bool], list[str]]:
    """User-revised classification:

    ADOPT: A0..A5 + S0 + S1 all pass.
    PROMISING_CONFIRMED: A1 + A2 + S0 + S1 pass, but one of A3/A4/A5 fails.
    FAILED_OOS: A1 OR A2 fails; OR A0 fail; OR S0 OR S1 fails.
    """
    a0 = real.oos_annual_trades >= ADOPT_MIN_TRADES
    a1 = real.oos_sharpe >= ADOPT_MIN_SHARPE
    a2 = real.oos_annual_pnl >= ADOPT_MIN_PNL
    a3 = real.oos_max_dd <= ADOPT_MAX_DD
    a4 = (
        real.sub_fold_pos >= ADOPT_MIN_FOLD_POSNEG[0]
        and real.sub_fold_neg <= ADOPT_MIN_FOLD_POSNEG[1]
    )
    a5 = real.oos_annual_pnl_stress_05 > 0
    s0 = abs(shuffled_sharpe) < S0_HARD_GATE
    s1 = real.train_test_gap <= S1_MAX_TRAIN_TEST_GAP

    gates = {"A0": a0, "A1": a1, "A2": a2, "A3": a3, "A4": a4, "A5": a5, "S0": s0, "S1": s1}
    failed = [k for k, v in gates.items() if not v]

    # FAILED_OOS conditions (any of these)
    if not a0 or not a1 or not a2 or not s0 or not s1:
        return "FAILED_OOS", gates, failed

    # If we reach here, A0/A1/A2/S0/S1 all pass.
    # ADOPT requires A3 + A4 + A5 also pass.
    if a3 and a4 and a5:
        return "ADOPT", gates, failed
    return "PROMISING_CONFIRMED", gates, failed


# ---------------------------------------------------------------------------
# Drawdown concentration analysis
# ---------------------------------------------------------------------------


def analyze_drawdown_concentration(trades: pd.DataFrame) -> dict:
    if trades.empty:
        return {}
    pnl = trades["pnl"].to_numpy()
    n = pnl.size

    # 7.1 Worst trades (top 20)
    worst_idx = np.argsort(pnl)[:20]
    worst_trades = trades.iloc[worst_idx][
        ["entry_ts", "pair", "direction", "predicted_P", "pnl"]
    ].copy()
    neg_total = float(pnl[pnl < 0].sum())
    worst_20_sum = float(pnl[worst_idx].sum())
    worst_20_share_of_neg = worst_20_sum / neg_total if neg_total < 0 else 0.0

    # 7.2 Worst pair
    pair_grp = trades.groupby("pair", observed=False)["pnl"].agg(["count", "sum", "mean"])
    pair_grp = pair_grp.sort_values("sum")
    pair_max_dds: list[float] = []
    for p in pair_grp.index:
        sub_pnl = trades[trades["pair"] == p]["pnl"].to_numpy()
        pair_max_dds.append(max_drawdown(sub_pnl))
    pair_grp["max_dd"] = pair_max_dds
    total_max_dd = max_drawdown(pnl)
    if total_max_dd > 0:
        pair_grp["max_dd_share"] = pair_grp["max_dd"] / total_max_dd
    else:
        pair_grp["max_dd_share"] = 0.0
    worst_pair = pair_grp.iloc[0]
    worst_pair_share = float(worst_pair["max_dd"] / total_max_dd) if total_max_dd > 0 else 0.0

    # 7.5 Per-session
    sessions = {
        "Tokyo (0-7)": (0, 7),
        "London (7-14)": (7, 14),
        "NY (14-21)": (14, 21),
        "Rollover (21-24)": (21, 24),
    }
    session_grp: dict[str, dict[str, float]] = {}
    for name, (lo, hi) in sessions.items():
        mask = (trades["hour_utc"] >= lo) & (trades["hour_utc"] < hi)
        sub_pnl = trades[mask]["pnl"]
        session_grp[name] = {
            "n": int(mask.sum()),
            "pnl_sum": float(sub_pnl.sum()),
            "pnl_mean": float(sub_pnl.mean()) if mask.any() else 0.0,
            "max_dd": max_drawdown(sub_pnl.to_numpy()),
        }

    # 7.4 Consecutive losses
    is_loss = (pnl < 0).astype(np.int8)
    longest_run = 0
    cur = 0
    run_lengths: list[int] = []
    for v in is_loss:
        if v == 1:
            cur += 1
            longest_run = max(longest_run, cur)
        else:
            if cur > 0:
                run_lengths.append(cur)
            cur = 0
    if cur > 0:
        run_lengths.append(cur)
    run_hist = pd.Series(run_lengths).value_counts().sort_index().to_dict() if run_lengths else {}

    return {
        "n_total": n,
        "total_pnl": float(pnl.sum()),
        "total_max_dd": total_max_dd,
        "worst_trades_top20": worst_trades.to_dict("records"),
        "worst_20_sum_pnl": worst_20_sum,
        "worst_20_share_of_neg_pnl": worst_20_share_of_neg,
        "per_pair": pair_grp.reset_index().to_dict("records"),
        "worst_pair": str(worst_pair.name),
        "worst_pair_max_dd_share": worst_pair_share,
        "per_session": session_grp,
        "longest_consecutive_loss_run": longest_run,
        "consecutive_loss_run_histogram": run_hist,
    }


def attribute_drawdown(diag: dict, sub_fold_pnls: list[float], sub_fold_ranges: list) -> str:
    """Categorise the dominant drawdown concentration."""
    if not diag:
        return "NO_TRADES"
    top20_share = abs(diag.get("worst_20_share_of_neg_pnl", 0.0))
    pair_share = diag.get("worst_pair_max_dd_share", 0.0)
    streak = diag.get("longest_consecutive_loss_run", 0)
    # sub-fold concentration
    if sub_fold_pnls:
        worst_sub = min(sub_fold_pnls)
        total_neg = sum(v for v in sub_fold_pnls if v < 0)
        sub_share = worst_sub / total_neg if total_neg < 0 else 0.0
    else:
        sub_share = 0.0

    causes: list[str] = []
    if top20_share > 0.60:
        causes.append(f"FEW_TRADE_CONCENTRATION (top-20 = {top20_share:.1%} of neg PnL)")
    if pair_share > 0.40:
        causes.append(f"SINGLE_PAIR_CONCENTRATION (worst pair MaxDD share = {pair_share:.1%})")
    if sub_share > 0.40:
        causes.append(f"SINGLE_PERIOD_CONCENTRATION (worst sub-fold = {sub_share:.1%})")
    if streak >= 10:
        causes.append(f"CONSECUTIVE_LOSS_STREAK (longest = {streak})")
    if not causes:
        return "DISTRIBUTED — no single dimension dominates"
    return "; ".join(causes)


# ---------------------------------------------------------------------------
# Build signal dataset (delegate to PR #259)
# ---------------------------------------------------------------------------


def build_full_signal_df(
    pairs: list[str], days: int = 730
) -> tuple[pd.DataFrame, list[str], list[str]]:
    pairs_used: list[str] = []
    pairs_missing: list[str] = []
    dfs: list[pd.DataFrame] = []
    for i, pair in enumerate(pairs, 1):
        t0 = time.time()
        try:
            df = _PR259.build_signal_dataset(pair, N_DONCHIAN, days=days)
        except FileNotFoundError as exc:
            print(f"[{i:2d}/{len(pairs)}] {pair}: SKIP ({exc})")
            pairs_missing.append(pair)
            continue
        if df.empty:
            continue
        df["n_donchian"] = N_DONCHIAN
        dfs.append(df)
        pairs_used.append(pair)
        print(f"[{i:2d}/{len(pairs)}] {pair}: {len(df):>7} signals ({time.time() - t0:5.1f}s)")
    if not dfs:
        return pd.DataFrame(), pairs_used, pairs_missing
    full = pd.concat(dfs, ignore_index=True).sort_values("entry_ts").reset_index(drop=True)
    return full, pairs_used, pairs_missing


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


def write_report(
    real: OOSResult,
    shuffled_sharpe: float,
    verdict: str,
    gates: dict[str, bool],
    failed: list[str],
    diag: dict,
    attribution: str,
    out_dir: Path,
    pairs_used: list[str],
    pairs_missing: list[str],
) -> Path:
    p = out_dir / "eval_report.md"
    lines: list[str] = []
    lines.append("# Stage 22.0e-v2 Independent OOS Validation — Evaluation Report")
    lines.append("")
    lines.append(f"Generated: {datetime.now(UTC).isoformat()}")
    lines.append("")
    lines.append("Design contract: `docs/design/phase22_0e_v2_independent_oos.md`.")
    lines.append("")
    lines.append("> ⚠ **Independence caveat**: this is an OOS validation of a single cell")
    lines.append("> pre-selected from a 48-cell sweep in PR #259. The OOS window is a")
    lines.append("> chronological hold-out from the same 730-day OANDA pull, NOT a fresh")
    lines.append("> fetch. ADOPT here means (1) the PR #259 cell was not a multiple-")
    lines.append("> testing artifact and (2) the eight gates are met without re-tuning.")
    lines.append("> ADOPT does NOT mean production-ready — paper-run on bars beyond the")
    lines.append("> 730-day pull is the next layer.")
    lines.append("")
    lines.append("## Frozen cell")
    lines.append("")
    lines.append(f"- primary signal: {PRIMARY_SIGNAL}")
    lines.append(f"- N_DONCHIAN = {N_DONCHIAN}")
    lines.append(f"- CONF_THRESHOLD = {CONF_THRESHOLD}")
    lines.append(f"- HORIZON_BARS = {HORIZON_BARS}")
    lines.append(f"- EXIT_RULE = {EXIT_RULE}")
    lines.append(f"- FEATURE_SET = {list(MAIN_FEATURE_COLS)}")
    lines.append("")
    lines.append("## Pair coverage")
    lines.append("")
    lines.append(
        f"- Active pairs: {len(pairs_used)} / 20 canonical "
        f"(missing: {', '.join(pairs_missing) if pairs_missing else 'none'})"
    )
    lines.append("")

    # Verdict
    lines.append(f"## Verdict: **{verdict}**")
    lines.append("")
    a0 = real.oos_annual_trades >= ADOPT_MIN_TRADES
    a1 = real.oos_sharpe >= ADOPT_MIN_SHARPE
    a2 = real.oos_annual_pnl >= ADOPT_MIN_PNL
    a3 = real.oos_max_dd <= ADOPT_MAX_DD
    a4 = (
        real.sub_fold_pos >= ADOPT_MIN_FOLD_POSNEG[0]
        and real.sub_fold_neg <= ADOPT_MIN_FOLD_POSNEG[1]
    )
    a5 = real.oos_annual_pnl_stress_05 > 0
    s0 = abs(shuffled_sharpe) < S0_HARD_GATE
    s0_diag = abs(shuffled_sharpe) < S0_DIAGNOSTIC
    s1 = real.train_test_gap <= S1_MAX_TRAIN_TEST_GAP

    pass_str = lambda b: "PASS" if b else "FAIL"  # noqa: E731 - small inline ternary
    lines.append(
        f"- A0 OOS annual_trades={real.oos_annual_trades:.0f} ≥ "
        f"{ADOPT_MIN_TRADES}: **{pass_str(a0)}**"
    )
    lines.append(f"- A1 OOS Sharpe={real.oos_sharpe:.4f} ≥ {ADOPT_MIN_SHARPE}: **{pass_str(a1)}**")
    lines.append(
        f"- A2 OOS annual_pnl={real.oos_annual_pnl:.1f} ≥ {ADOPT_MIN_PNL}: **{pass_str(a2)}**"
    )
    lines.append(f"- A3 OOS MaxDD={real.oos_max_dd:.1f} ≤ {ADOPT_MAX_DD}: **{pass_str(a3)}**")
    lines.append(
        f"- A4 OOS sub-fold pos/neg={real.sub_fold_pos}/{real.sub_fold_neg} ≥ "
        f"{ADOPT_MIN_FOLD_POSNEG[0]}/{ADOPT_MIN_FOLD_POSNEG[1]}: "
        f"**{pass_str(a4)}**"
    )
    lines.append(
        f"- A5 stress +0.5pip annual_pnl={real.oos_annual_pnl_stress_05:.1f} "
        f"> 0: **{pass_str(a5)}**"
    )
    lines.append(
        f"- S0 |shuffled_sharpe|={abs(shuffled_sharpe):.4f} < {S0_HARD_GATE}: "
        f"**{pass_str(s0)}** (diagnostic <{S0_DIAGNOSTIC}: "
        f"{'pass' if s0_diag else 'fail'})"
    )
    lines.append(
        f"- S1 train_test_gap={real.train_test_gap:.4f} ≤ "
        f"{S1_MAX_TRAIN_TEST_GAP}: **{pass_str(s1)}**"
    )
    if failed:
        lines.append("")
        lines.append(f"**Gates failed**: {', '.join(failed)}")
    if real.oos_annual_trades > OVERTRADE_WARN_TRADES:
        lines.append("")
        ann_t = real.oos_annual_trades
        lines.append(
            f"⚠ Overtrading warning: annual_trades = {ann_t:.0f} > {OVERTRADE_WARN_TRADES}."
        )
    lines.append("")

    # OOS summary
    lines.append("## OOS summary")
    lines.append("")
    lines.append(f"- Train rows: {real.n_train:,}")
    lines.append(f"- OOS rows (raw breakouts in last 20%): {real.n_oos:,}")
    lines.append(f"- OOS rows after conf={CONF_THRESHOLD} filter: {real.n_oos_filtered:,}")
    lines.append(f"- OOS span: {real.oos_span_years:.3f} years")
    lines.append(f"- OOS mean PnL/trade: {real.oos_mean_pnl:.3f} pip")
    lines.append(f"- OOS win rate: {real.oos_win_rate:.3f}")
    lines.append(f"- OOS DD%PnL: {real.oos_dd_pct:.1f}%")
    lines.append(f"- Train Sharpe (filtered conf≥{CONF_THRESHOLD}): {real.train_sharpe:.4f}")
    lines.append(f"- OOS Sharpe (filtered conf≥{CONF_THRESHOLD}): {real.oos_sharpe:.4f}")
    lines.append(f"- Train-OOS gap (S1): {real.train_test_gap:.4f}")
    lines.append("")

    # OOS sub-folds
    lines.append("## OOS sub-folds (DIAGNOSTIC ONLY — no training role)")
    lines.append("")
    lines.append("| sub-fold | range | n | sum_pnl | sharpe |")
    lines.append("|---|---|---|---|---|")
    for k, ((rng_lo, rng_hi), n_, pnl_, sh_) in enumerate(
        zip(
            real.sub_fold_ranges,
            real.sub_fold_ns,
            real.sub_fold_pnls,
            real.sub_fold_sharpes,
            strict=False,
        ),
        1,
    ):
        lines.append(f"| {k} | {rng_lo[:19]} → {rng_hi[:19]} | {n_} | {pnl_:.1f} | {sh_:.4f} |")
    lines.append("")

    # Spread stress
    lines.append("## Spread stress (OOS annual PnL, pip)")
    lines.append("")
    lines.append("| stress | annual_pnl |")
    lines.append("|---|---|")
    lines.append(f"| +0.0 | {real.oos_annual_pnl:.1f} |")
    lines.append(f"| +0.2 | {real.oos_annual_pnl_stress_02:.1f} |")
    lines.append(f"| +0.5 | {real.oos_annual_pnl_stress_05:.1f} |")
    lines.append("")

    # Drawdown concentration
    lines.append("## Drawdown concentration analysis")
    lines.append("")
    if not diag:
        lines.append("(no OOS trades)")
    else:
        lines.append(f"- Total OOS PnL: {diag['total_pnl']:.1f}")
        lines.append(f"- Total MaxDD: {diag['total_max_dd']:.1f}")
        lines.append(f"- Worst-20 trade PnL sum: {diag['worst_20_sum_pnl']:.1f}")
        lines.append(f"- Worst-20 share of negative PnL: {diag['worst_20_share_of_neg_pnl']:.1%}")
        lines.append(
            f"- Worst pair: **{diag['worst_pair']}** "
            f"(MaxDD share = {diag['worst_pair_max_dd_share']:.1%})"
        )
        lines.append(f"- Longest consecutive loss run: {diag['longest_consecutive_loss_run']}")
        lines.append("")
        lines.append("### Worst 20 trades")
        lines.append("")
        lines.append("| entry_ts | pair | dir | pred_P | pnl |")
        lines.append("|---|---|---|---|---|")
        for t in diag["worst_trades_top20"][:20]:
            ts = str(t["entry_ts"])[:19]
            lines.append(
                f"| {ts} | {t['pair']} | {t['direction']} | "
                f"{t['predicted_P']:.3f} | {t['pnl']:.1f} |"
            )
        lines.append("")
        lines.append("### Per-pair PnL (sorted ascending by sum_pnl)")
        lines.append("")
        lines.append("| pair | n | sum_pnl | mean_pnl | max_dd | max_dd_share |")
        lines.append("|---|---|---|---|---|---|")
        for r in diag["per_pair"]:
            lines.append(
                f"| {r['pair']} | {r['count']} | {r['sum']:.1f} | "
                f"{r['mean']:.3f} | {r['max_dd']:.1f} | {r['max_dd_share']:.1%} |"
            )
        lines.append("")
        lines.append("### Per-session PnL")
        lines.append("")
        lines.append("| session | n | sum_pnl | mean | max_dd |")
        lines.append("|---|---|---|---|---|")
        for sess, v in diag["per_session"].items():
            lines.append(
                f"| {sess} | {v['n']} | {v['pnl_sum']:.1f} | "
                f"{v['pnl_mean']:.3f} | {v['max_dd']:.1f} |"
            )
        lines.append("")
        lines.append("### Consecutive-loss-run histogram")
        lines.append("")
        lines.append("| run length | count |")
        lines.append("|---|---|")
        for k_, v in sorted(diag["consecutive_loss_run_histogram"].items()):
            lines.append(f"| {k_} | {v} |")
        lines.append("")
    lines.append(f"### Drawdown attribution: **{attribution}**")
    lines.append("")
    lines.append(
        "*This attribution is descriptive only — it does not prescribe any "
        "risk-control mechanism in this PR. The attribution informs (but does "
        "not authorise) future risk-control studies subject to NG-list "
        "constraints.*"
    )
    lines.append("")

    # Feature importance
    lines.append("## Feature importance (LightGBM gain)")
    lines.append("")
    if real.feature_importance:
        items = sorted(real.feature_importance.items(), key=lambda kv: kv[1], reverse=True)
        lines.append("| feature | gain |")
        lines.append("|---|---|")
        for f, g in items:
            lines.append(f"| {f} | {g:.0f} |")
    lines.append("")

    # NG list
    lines.append("## NG list compliance (postmortem §4)")
    lines.append("")
    lines.append("- NG#1 pair filter: 20-pair universe, no cell-level pair drop ✓")
    lines.append("- NG#2 train-side time-of-day filter: not applied ✓")
    lines.append("- NG#3 test-side filter improvement claim: OOS verdict on full last-20% ✓")
    lines.append("- NG#4 WeekOpen-aware sample weighting: none ✓")
    lines.append("- NG#5 universe-restricted cross-pair feature: none ✓")
    lines.append("")

    # Audit allowlist
    lines.append("## Feature allowlist compliance (audit PR #258)")
    lines.append("")
    lines.append(f"- MAIN_FEATURE_COLS = {list(MAIN_FEATURE_COLS)}")
    iwow_in = "is_week_open_window" in MAIN_FEATURE_COLS
    lines.append(f"- is_week_open_window in MAIN: {iwow_in} (must be False)")
    lines.append(f"- hour_utc in MAIN: {('hour_utc' in MAIN_FEATURE_COLS)} (must be False)")
    lines.append(f"- dow in MAIN: {('dow' in MAIN_FEATURE_COLS)} (must be False)")
    lines.append("")

    p.write_text("\n".join(lines), encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pairs", nargs="*", default=PAIRS_CANONICAL_20)
    parser.add_argument("--days", type=int, default=730)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args(argv)

    pairs = ["USD_JPY", "EUR_USD", "GBP_JPY"] if args.smoke else args.pairs
    args.out_dir.mkdir(parents=True, exist_ok=True)

    print("=== Stage 22.0e-v2 Independent OOS Validation ===")
    print(f"Frozen cell: N={N_DONCHIAN}, conf={CONF_THRESHOLD}, h={HORIZON_BARS}, exit={EXIT_RULE}")
    print(f"Pairs: {len(pairs)}")
    print()

    print("[1/3] Building signal dataset (Donchian-immediate, N=50) ...")
    t0 = time.time()
    full_df, pairs_used, pairs_missing = build_full_signal_df(pairs, args.days)
    if full_df.empty:
        print("ERROR: no signal data produced")
        return 1
    print(f"     total signals: {len(full_df):,} ({time.time() - t0:5.1f}s)")
    print()

    print("[2/3] Training single LightGBM model (first 80%) and predicting OOS (last 20%) ...")
    t0 = time.time()
    real_result = evaluate_frozen_cell(full_df, shuffle_y=False)
    print(
        f"     n_oos_filtered={real_result.n_oos_filtered}, "
        f"OOS Sharpe={real_result.oos_sharpe:.4f}, "
        f"OOS annual_pnl={real_result.oos_annual_pnl:.1f}, "
        f"MaxDD={real_result.oos_max_dd:.1f} ({time.time() - t0:5.1f}s)"
    )
    print()

    print("[3/3] Shuffled-target sanity (S0) ...")
    t0 = time.time()
    shuffled_result = evaluate_frozen_cell(full_df, shuffle_y=True)
    shuffled_sharpe = shuffled_result.oos_sharpe
    print(f"     shuffled_sharpe={shuffled_sharpe:.4f} ({time.time() - t0:5.1f}s)")
    print()

    # Drawdown analysis
    if real_result.oos_trades_df is not None and not real_result.oos_trades_df.empty:
        diag = analyze_drawdown_concentration(real_result.oos_trades_df)
        attribution = attribute_drawdown(
            diag, real_result.sub_fold_pnls, real_result.sub_fold_ranges
        )
    else:
        diag = {}
        attribution = "NO_TRADES"

    # Verdict
    verdict, gates, failed = classify_verdict(real_result, shuffled_sharpe)
    print(f"=== Verdict: {verdict} ===")
    if failed:
        print(f"Gates failed: {failed}")
    print(f"Drawdown attribution: {attribution}")

    # Save trade list (regenerable, not committed)
    if real_result.oos_trades_df is not None:
        trades_path = args.out_dir / "oos_trades.parquet"
        real_result.oos_trades_df.to_parquet(trades_path, compression="snappy")
        print(f"\nOOS trades: {trades_path}")

    report_path = write_report(
        real_result,
        shuffled_sharpe,
        verdict,
        gates,
        failed,
        diag,
        attribution,
        args.out_dir,
        pairs_used,
        pairs_missing,
    )
    print(f"Report: {report_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
