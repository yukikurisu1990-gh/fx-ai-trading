"""Stage 22.0b Mean Reversion Baseline.

PR3 of Phase 22. Consumes the path-aware scalp outcome dataset produced
by 22.0a (artifacts/stage22_0a/labels/labels_<pair>.parquet) and runs a
192-cell sweep:
  N (rolling)        ∈ {10, 20, 50, 100}
  z-threshold        ∈ {1.5, 2.0, 2.5, 3.0}
  horizon (M1 bars)  ∈ {5, 10, 20, 40}
  exit_rule          ∈ {tb_pnl, time_exit_pnl, best_possible_pnl}

For each cell aggregates per-trade PnL pooled across pairs, reports the
5-fold walk-forward stability of the top-K cells, applies +0.2 / +0.5 pip
spread stress, and emits a verdict (ADOPT / PROMISING_BUT_NEEDS_OOS /
REJECT) on the best realistic-exit cell.

Design contract: docs/design/phase22_0b_mean_reversion_baseline.md.

Touches NO src/ files, NO scripts/run_*.py, NO DB schema. 20-pair canonical
universe (a pair is skipped if its candle file is missing); no time-of-day
or pair filter applied.
"""

from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
LABEL_DIR = REPO_ROOT / "artifacts" / "stage22_0a" / "labels"
OUT_DIR = REPO_ROOT / "artifacts" / "stage22_0b"

# Production canonical 20-pair list (matches compare_multipair_v19_causal.py).
PAIRS_CANONICAL_20 = [
    "EUR_USD",
    "GBP_USD",
    "AUD_USD",
    "NZD_USD",
    "USD_CHF",
    "USD_CAD",
    "EUR_GBP",
    "USD_JPY",
    "EUR_JPY",
    "GBP_JPY",
    "AUD_JPY",
    "NZD_JPY",
    "CHF_JPY",
    "EUR_CHF",
    "EUR_AUD",
    "EUR_CAD",
    "AUD_NZD",
    "AUD_CAD",
    "GBP_AUD",
    "GBP_CHF",
]

N_VALUES: tuple[int, ...] = (10, 20, 50, 100)
THRESHOLDS: tuple[float, ...] = (1.5, 2.0, 2.5, 3.0)
HORIZONS: tuple[int, ...] = (5, 10, 20, 40)
EXIT_RULES: tuple[str, ...] = ("tb_pnl", "time_exit_pnl", "best_possible_pnl")
REALISTIC_EXIT_RULES: tuple[str, ...] = ("tb_pnl", "time_exit_pnl")

N_FOLDS = 5
M1_BARS_PER_YEAR = 365 * 24 * 60  # naive; weekend gaps reduce effective trades
ANNUALIZATION_M1 = float(M1_BARS_PER_YEAR)  # used only when annualizing per-trade Sharpe
SPREAD_STRESS_PIPS: tuple[float, ...] = (0.0, 0.2, 0.5)
EVAL_SPAN_YEARS_DEFAULT = 730.0 / 365.25  # ≈2.0 years (730d M1 BA dataset)
MIN_TRADES_FOR_RANKING = 30  # cells below this are excluded from top-K display


# ---------------------------------------------------------------------------
# pip helper
# ---------------------------------------------------------------------------


def pip_size_for(pair: str) -> float:
    return 0.01 if pair.endswith("_JPY") else 0.0001


# ---------------------------------------------------------------------------
# Mid close + causal z-score
# ---------------------------------------------------------------------------


def load_mid_close(pair: str, days: int = 730) -> pd.Series:
    """Load M1 BA candles and compute mid close = (bid_c + ask_c)/2."""
    path = DATA_DIR / f"candles_{pair}_M1_{days}d_BA.jsonl"
    if not path.exists():
        raise FileNotFoundError(path)
    # use pandas read_json for speed
    df = pd.read_json(path, lines=True)
    df["timestamp"] = pd.to_datetime(df["time"], utc=True)
    df = df.set_index("timestamp").sort_index()
    df = df[~df.index.duplicated(keep="first")]
    mid = (df["bid_c"].astype(np.float64) + df["ask_c"].astype(np.float64)) / 2.0
    mid.name = "mid_close"
    return mid


def causal_zscore(mid: pd.Series, n: int) -> pd.Series:
    """z[t] = (mid[t] - rolling_mean(mid, n)[t]) / rolling_std(mid, n)[t].

    Uses bars ≤ t only. Returns NaN for the first n-1 bars and where sigma == 0.
    """
    mu = mid.rolling(n, min_periods=n).mean()
    sigma = mid.rolling(n, min_periods=n).std(ddof=0)
    with np.errstate(divide="ignore", invalid="ignore"):
        z = (mid - mu) / sigma.where(sigma > 0, np.nan)
    return z


# ---------------------------------------------------------------------------
# Cell accumulator
# ---------------------------------------------------------------------------


@dataclass
class CellAcc:
    """Aggregator for a single cell (N, threshold, horizon, exit_rule)."""

    # Pooled across pairs: per-trade PnL stream (kept for MaxDD + diagnostics)
    entry_ts: list[np.ndarray] = field(default_factory=list)
    pnl: list[np.ndarray] = field(default_factory=list)
    # Optional metadata kept for top-K diagnostic; small lists of arrays per pair
    pair_arr: list[np.ndarray] = field(default_factory=list)
    spread_entry: list[np.ndarray] = field(default_factory=list)
    cost_ratio: list[np.ndarray] = field(default_factory=list)
    hour_utc: list[np.ndarray] = field(default_factory=list)
    dow: list[np.ndarray] = field(default_factory=list)
    direction: list[np.ndarray] = field(default_factory=list)

    def extend(
        self,
        entry_ts_arr: np.ndarray,
        pnl_arr: np.ndarray,
        pair_arr: np.ndarray,
        spread_arr: np.ndarray,
        cost_arr: np.ndarray,
        hour_arr: np.ndarray,
        dow_arr: np.ndarray,
        direction_arr: np.ndarray,
    ) -> None:
        if entry_ts_arr.size == 0:
            return
        self.entry_ts.append(entry_ts_arr)
        self.pnl.append(pnl_arr)
        self.pair_arr.append(pair_arr)
        self.spread_entry.append(spread_arr)
        self.cost_ratio.append(cost_arr)
        self.hour_utc.append(hour_arr)
        self.dow.append(dow_arr)
        self.direction.append(direction_arr)

    def materialize(self) -> pd.DataFrame:
        if not self.entry_ts:
            return pd.DataFrame(
                columns=[
                    "entry_ts",
                    "pnl",
                    "pair",
                    "spread_entry",
                    "cost_ratio",
                    "hour_utc",
                    "dow",
                    "direction",
                ]
            )
        out = pd.DataFrame(
            {
                "entry_ts": np.concatenate(self.entry_ts),
                "pnl": np.concatenate(self.pnl),
                "pair": np.concatenate(self.pair_arr),
                "spread_entry": np.concatenate(self.spread_entry),
                "cost_ratio": np.concatenate(self.cost_ratio),
                "hour_utc": np.concatenate(self.hour_utc),
                "dow": np.concatenate(self.dow),
                "direction": np.concatenate(self.direction),
            }
        )
        out = out.sort_values("entry_ts").reset_index(drop=True)
        return out


# ---------------------------------------------------------------------------
# Per-pair processing
# ---------------------------------------------------------------------------

_LABEL_COLUMNS_NEEDED = (
    "entry_ts",
    "horizon_bars",
    "direction",
    "valid_label",
    "gap_affected_forward_window",
    "tb_pnl",
    "time_exit_pnl",
    "best_possible_pnl",
    "spread_entry",
    "cost_ratio",
    "hour_utc",
    "dow",
)


def _build_lookup_arrays(labels: pd.DataFrame) -> dict[tuple[int, str], dict[str, np.ndarray]]:
    """Pre-split labels by (horizon, direction) into pure numpy arrays.

    Indexed by sorted entry_ts (int64 ns) for fast searchsorted lookups.
    """
    out: dict[tuple[int, str], dict[str, np.ndarray]] = {}
    for h in HORIZONS:
        for d in ("long", "short"):
            mask = (labels["horizon_bars"] == h) & (labels["direction"] == d)
            sub = labels[mask].sort_values("entry_ts")
            # tz-aware → naive ns int64. The relative ordering is what matters.
            ts_aware = sub["entry_ts"]
            ts_naive = ts_aware.dt.tz_convert("UTC").dt.tz_localize(None)
            ts = ts_naive.to_numpy().astype("datetime64[ns]").view("int64")
            out[(h, d)] = {
                "ts": ts,
                "tb_pnl": sub["tb_pnl"].to_numpy(dtype=np.float32),
                "time_exit_pnl": sub["time_exit_pnl"].to_numpy(dtype=np.float32),
                "best_possible_pnl": sub["best_possible_pnl"].to_numpy(dtype=np.float32),
                "spread_entry": sub["spread_entry"].to_numpy(dtype=np.float32),
                "cost_ratio": sub["cost_ratio"].to_numpy(dtype=np.float32),
                "hour_utc": sub["hour_utc"].to_numpy(dtype=np.int8),
                "dow": sub["dow"].to_numpy(dtype=np.int8),
            }
    return out


def _match_signals(label_ts: np.ndarray, sig_ts: np.ndarray) -> np.ndarray:
    """Return label-array indices where label_ts == sig_ts via searchsorted.

    Both arrays must be sorted ascending (int64 ns).
    """
    idx = np.searchsorted(label_ts, sig_ts)
    valid = (idx < len(label_ts)) & (label_ts[np.minimum(idx, len(label_ts) - 1)] == sig_ts)
    return idx[valid]


def process_pair(
    pair: str,
    days: int,
    accumulators: dict[tuple[int, float, int, str], CellAcc],
) -> int:
    """Compute z-scores and join against labels_<pair>.parquet for every cell.

    Returns the number of *valid+non-gap* label rows considered for this pair.
    """
    mid = load_mid_close(pair, days=days)
    label_path = LABEL_DIR / f"labels_{pair}.parquet"
    if not label_path.exists():
        raise FileNotFoundError(label_path)
    # Read only the columns we need; cuts load time and memory roughly in half
    labels = pd.read_parquet(label_path, columns=list(_LABEL_COLUMNS_NEEDED))
    labels = labels[labels["valid_label"] & ~labels["gap_affected_forward_window"]]
    n_valid = len(labels)
    if n_valid == 0:
        return 0
    if not pd.api.types.is_datetime64_any_dtype(labels["entry_ts"]):
        labels["entry_ts"] = pd.to_datetime(labels["entry_ts"], utc=True)

    lookup_arrays = _build_lookup_arrays(labels)
    del labels  # free pandas memory

    z_per_n: dict[int, pd.Series] = {n: causal_zscore(mid, n) for n in N_VALUES}

    for n in N_VALUES:
        z = z_per_n[n].dropna()
        if z.empty:
            continue
        z_ts_int = z.index.values.astype("datetime64[ns]").view("int64")
        z_vals = z.values
        for th in THRESHOLDS:
            long_mask = z_vals < -th
            short_mask = z_vals > th
            long_ts = z_ts_int[long_mask]
            short_ts = z_ts_int[short_mask]
            # Both already sorted (z is time-indexed and ascending)
            for h in HORIZONS:
                for d, sig_ts_int in (("long", long_ts), ("short", short_ts)):
                    if sig_ts_int.size == 0:
                        continue
                    arr = lookup_arrays[(h, d)]
                    matched = _match_signals(arr["ts"], sig_ts_int)
                    if matched.size == 0:
                        continue
                    entry_ts_arr = arr["ts"][matched].view("datetime64[ns]")
                    spread_arr = arr["spread_entry"][matched]
                    cost_arr = arr["cost_ratio"][matched]
                    hour_arr = arr["hour_utc"][matched]
                    dow_arr = arr["dow"][matched]
                    pair_arr = np.full(matched.size, pair, dtype=object)
                    direction_arr = np.full(matched.size, d, dtype=object)
                    for exit_rule in EXIT_RULES:
                        pnl = arr[exit_rule][matched]
                        accumulators[(n, th, h, exit_rule)].extend(
                            entry_ts_arr,
                            pnl,
                            pair_arr,
                            spread_arr,
                            cost_arr,
                            hour_arr,
                            dow_arr,
                            direction_arr,
                        )
    return n_valid


# ---------------------------------------------------------------------------
# Cell metric computation
# ---------------------------------------------------------------------------


def compute_eval_span_years(trades_df: pd.DataFrame) -> float:
    """Eval span for annualization. Use fixed dataset span (~2 years) so that
    cells with few trades over the full data range still annualize sensibly.
    """
    return EVAL_SPAN_YEARS_DEFAULT


def annualize(total: float, n: int, span_years: float) -> float:
    if n == 0 or span_years <= 0:
        return 0.0
    return total / span_years


def per_trade_sharpe(pnl: np.ndarray, n_per_year: float = 0.0) -> float:
    """Per-trade Sharpe = mean / std with population std (ddof=0).

    Matches the convention in compare_multipair_v19_causal.py:_sharpe so the
    +0.0822 B Rule baseline figure is comparable. ``n_per_year`` is accepted
    for API compatibility but unused (no sqrt-of-N annualization).
    """
    del n_per_year  # noqa: F841 — explicit unused
    if pnl.size < 2:
        return 0.0
    mean = float(np.mean(pnl))
    var = float(np.var(pnl, ddof=0))
    if var <= 0:
        return 0.0
    return mean / np.sqrt(var)


def max_drawdown(pnl: np.ndarray) -> float:
    if pnl.size == 0:
        return 0.0
    eq = np.cumsum(pnl)
    peak = np.maximum.accumulate(eq)
    dd = peak - eq
    return float(dd.max())


def compute_cell_metrics(
    cell_key: tuple[int, float, int, str],
    trades: pd.DataFrame,
) -> dict:
    n_pkw, th, h, exit_rule = cell_key
    n = len(trades)
    if n == 0:
        return _empty_metrics(cell_key)
    span_years = compute_eval_span_years(trades)
    n_per_year = n / span_years
    pnl = trades["pnl"].to_numpy()
    annual_pnl = annualize(float(pnl.sum()), n, span_years)

    sharpe = per_trade_sharpe(pnl, n_per_year)
    dd = max_drawdown(pnl)
    dd_pct = (dd / abs(annual_pnl)) * 100.0 if abs(annual_pnl) > 1e-9 else float("inf")

    # Spread-stressed (apply the per-trade pip tax uniformly)
    stress_metrics: dict[str, float] = {}
    for stress in SPREAD_STRESS_PIPS:
        stressed = pnl - stress
        stress_metrics[f"annual_pnl_stress_+{stress:.1f}"] = annualize(
            float(stressed.sum()), n, span_years
        )
        stress_metrics[f"sharpe_stress_+{stress:.1f}"] = per_trade_sharpe(stressed, n_per_year)

    # 5-fold walk-forward by chronological position
    fold_metrics = compute_fold_metrics(trades, span_years)

    return {
        "N": n_pkw,
        "threshold": th,
        "horizon_bars": h,
        "exit_rule": exit_rule,
        "n_trades": n,
        "annual_trades": n / span_years,
        "annual_pnl_pip": annual_pnl,
        "sharpe": sharpe,
        "max_dd_pip": dd,
        "dd_pct_pnl": dd_pct,
        "mean_pnl": float(pnl.mean()),
        "median_pnl": float(np.median(pnl)),
        "win_rate": float((pnl > 0).mean()),
        **stress_metrics,
        **fold_metrics,
    }


def _empty_metrics(cell_key: tuple[int, float, int, str]) -> dict:
    n, th, h, exit_rule = cell_key
    out = {
        "N": n,
        "threshold": th,
        "horizon_bars": h,
        "exit_rule": exit_rule,
        "n_trades": 0,
        "annual_trades": 0.0,
        "annual_pnl_pip": 0.0,
        "sharpe": 0.0,
        "max_dd_pip": 0.0,
        "dd_pct_pnl": float("inf"),
        "mean_pnl": 0.0,
        "median_pnl": 0.0,
        "win_rate": 0.0,
    }
    for stress in SPREAD_STRESS_PIPS:
        out[f"annual_pnl_stress_+{stress:.1f}"] = 0.0
        out[f"sharpe_stress_+{stress:.1f}"] = 0.0
    out.update(
        {
            "fold_pos": 0,
            "fold_neg": 0,
            "fold_pnl_cv": float("inf"),
            "fold_concentration_top": 0.0,
            **{f"fold_{i}_pnl": 0.0 for i in range(N_FOLDS)},
            **{f"fold_{i}_n": 0 for i in range(N_FOLDS)},
        }
    )
    return out


def compute_fold_metrics(trades: pd.DataFrame, span_years: float) -> dict:
    """Time-ordered 5-fold split by entry_ts."""
    if trades.empty:
        return {
            "fold_pos": 0,
            "fold_neg": 0,
            "fold_pnl_cv": float("inf"),
            "fold_concentration_top": 0.0,
            **{f"fold_{i}_pnl": 0.0 for i in range(N_FOLDS)},
            **{f"fold_{i}_n": 0 for i in range(N_FOLDS)},
        }
    ts = trades["entry_ts"].to_numpy()
    pnl = trades["pnl"].to_numpy()
    t_min = ts.min()
    t_max = ts.max()
    span = t_max - t_min
    edges = [t_min + (span * i / N_FOLDS) for i in range(N_FOLDS + 1)]
    fold_pnls: list[float] = []
    fold_ns: list[int] = []
    for i in range(N_FOLDS):
        if i < N_FOLDS - 1:
            mask = (ts >= edges[i]) & (ts < edges[i + 1])
        else:
            mask = (ts >= edges[i]) & (ts <= edges[i + 1])
        fp = pnl[mask]
        fold_pnls.append(float(fp.sum()))
        fold_ns.append(int(fp.size))
    fold_pos = sum(1 for v in fold_pnls if v > 0)
    fold_neg = sum(1 for v in fold_pnls if v < 0)
    arr = np.asarray(fold_pnls)
    mean = float(arr.mean())
    std = float(arr.std(ddof=0))
    cv = std / abs(mean) if abs(mean) > 1e-9 else float("inf")
    total = float(np.abs(arr).sum())
    top = float(np.abs(arr).max() / total) if total > 0 else 0.0
    out = {
        "fold_pos": fold_pos,
        "fold_neg": fold_neg,
        "fold_pnl_cv": cv,
        "fold_concentration_top": top,
    }
    out.update({f"fold_{i}_pnl": fold_pnls[i] for i in range(N_FOLDS)})
    out.update({f"fold_{i}_n": fold_ns[i] for i in range(N_FOLDS)})
    return out


# ---------------------------------------------------------------------------
# Verdict
# ---------------------------------------------------------------------------

ADOPT_MIN_TRADES = 70
OVERTRADE_WARN_TRADES = 1000
ADOPT_MIN_SHARPE = 0.082
ADOPT_MIN_PNL = 180.0
ADOPT_MAX_DD = 200.0
ADOPT_MIN_FOLD_POSNEG = (4, 1)


def classify_cell(cell: dict) -> tuple[str, list[str]]:
    """Return (verdict, list of failed gates).

    Verdict ∈ {ADOPT, PROMISING_BUT_NEEDS_OOS, REJECT}. best_possible_pnl
    cells are forced to REJECT regardless of their numbers (diagnostic only).
    """
    failed: list[str] = []
    exit_rule = cell["exit_rule"]
    if exit_rule == "best_possible_pnl":
        return "REJECT", ["non-realistic exit_rule (diagnostic only)"]
    annual_trades = cell["annual_trades"]
    if annual_trades < ADOPT_MIN_TRADES:
        return "REJECT", [f"A0: annual_trades {annual_trades:.0f} < {ADOPT_MIN_TRADES}"]
    if cell["sharpe"] < ADOPT_MIN_SHARPE:
        return "REJECT", [f"A1: sharpe {cell['sharpe']:.4f} < {ADOPT_MIN_SHARPE}"]
    if cell["annual_pnl_pip"] < ADOPT_MIN_PNL:
        return "REJECT", [f"A2: annual_pnl {cell['annual_pnl_pip']:.1f} < {ADOPT_MIN_PNL}"]
    # A3..A5 only checked once A1+A2 pass
    if cell["max_dd_pip"] > ADOPT_MAX_DD:
        failed.append(f"A3: MaxDD {cell['max_dd_pip']:.1f} > {ADOPT_MAX_DD}")
    if not (
        cell["fold_pos"] >= ADOPT_MIN_FOLD_POSNEG[0]
        and cell["fold_neg"] <= ADOPT_MIN_FOLD_POSNEG[1]
    ):
        failed.append(f"A4: fold pos/neg {cell['fold_pos']}/{cell['fold_neg']} not >= 4/1")
    if cell["annual_pnl_stress_+0.5"] <= 0:
        failed.append(f"A5: stress +0.5pip annual PnL {cell['annual_pnl_stress_+0.5']:.1f} <= 0")
    if not failed:
        return "ADOPT", []
    return "PROMISING_BUT_NEEDS_OOS", failed


# ---------------------------------------------------------------------------
# Top-K diagnostics
# ---------------------------------------------------------------------------


def cost_diagnostics(trades: pd.DataFrame) -> dict:
    if trades.empty:
        return {}
    cost_buckets = [(0, 0.5), (0.5, 1.0), (1.0, 1.5), (1.5, 2.0), (2.0, np.inf)]
    spread_buckets = [(0, 1), (1, 2), (2, 3), (3, np.inf)]
    out: dict = {
        "median_spread_entry": float(trades["spread_entry"].median()),
        "median_cost_ratio": float(trades["cost_ratio"].median()),
        "p10_cost_ratio": float(trades["cost_ratio"].quantile(0.10)),
        "p90_cost_ratio": float(trades["cost_ratio"].quantile(0.90)),
        "by_cost_ratio_bucket": {},
        "by_spread_bucket": {},
        "by_pair": {},
        "by_session": {},
    }
    for lo, hi in cost_buckets:
        mask = (trades["cost_ratio"] >= lo) & (trades["cost_ratio"] < hi)
        sub = trades[mask]
        out["by_cost_ratio_bucket"][f"[{lo}, {hi})"] = {
            "n": int(len(sub)),
            "pnl_sum": float(sub["pnl"].sum()),
            "pnl_mean": float(sub["pnl"].mean()) if len(sub) else 0.0,
        }
    for lo, hi in spread_buckets:
        mask = (trades["spread_entry"] >= lo) & (trades["spread_entry"] < hi)
        sub = trades[mask]
        out["by_spread_bucket"][f"[{lo}, {hi}) pip"] = {
            "n": int(len(sub)),
            "pnl_sum": float(sub["pnl"].sum()),
            "pnl_mean": float(sub["pnl"].mean()) if len(sub) else 0.0,
        }
    pair_grp = trades.groupby("pair")["pnl"].agg(["count", "sum", "mean"])
    for pair, row in pair_grp.iterrows():
        out["by_pair"][pair] = {
            "n": int(row["count"]),
            "pnl_sum": float(row["sum"]),
            "pnl_mean": float(row["mean"]),
        }
    sessions = {
        "Tokyo (0-7 UTC)": (0, 7),
        "London (7-14 UTC)": (7, 14),
        "NY (14-21 UTC)": (14, 21),
        "Rollover (21-24 UTC)": (21, 24),
    }
    for name, (lo, hi) in sessions.items():
        mask = (trades["hour_utc"] >= lo) & (trades["hour_utc"] < hi)
        sub = trades[mask]
        out["by_session"][name] = {
            "n": int(len(sub)),
            "pnl_sum": float(sub["pnl"].sum()),
            "pnl_mean": float(sub["pnl"].mean()) if len(sub) else 0.0,
        }
    return out


# ---------------------------------------------------------------------------
# Report writer
# ---------------------------------------------------------------------------


def write_report(
    sweep_df: pd.DataFrame,
    top_k_cells: list[dict],
    top_k_diagnostics: list[dict],
    out_dir: Path,
    pairs_used: list[str],
    pairs_missing: list[str],
) -> Path:
    p = out_dir / "eval_report.md"
    lines: list[str] = []
    lines.append("# Stage 22.0b Mean Reversion Baseline — Evaluation Report")
    lines.append("")
    lines.append(f"Generated: {datetime.now(UTC).isoformat()}")
    lines.append("")
    lines.append("Design contract: `docs/design/phase22_0b_mean_reversion_baseline.md`.")
    lines.append("")
    lines.append("> ⚠ **Multiple testing caveat**: 192 cells were searched. The reported best")
    lines.append("> cell's Sharpe / PnL are *in-sample search results*. Production migration")
    lines.append("> of any ADOPT-classified cell requires independent OOS validation")
    lines.append("> (held-out future time slice, paper-run, or fresh data fetch). The")
    lines.append('> ADOPT classification here means "passes all 6 in-sample gates" — not')
    lines.append('> "production-ready".')
    lines.append("")
    lines.append("## Pair coverage")
    lines.append("")
    lines.append(
        f"- Active pairs: {len(pairs_used)} / 20 canonical "
        f"(missing: {', '.join(pairs_missing) if pairs_missing else 'none'})"
    )
    lines.append("")
    if pairs_missing:
        lines.append(
            f"  *{', '.join(pairs_missing)} M1 BA candle file missing in local data store; "
            "backfill is out of scope for this PR. PR description includes the same caveat.*"
        )
        lines.append("")

    # Verdict (best realistic cell — must have at least MIN_TRADES_FOR_RANKING rows)
    realistic = sweep_df[
        sweep_df["exit_rule"].isin(REALISTIC_EXIT_RULES)
        & (sweep_df["n_trades"] >= MIN_TRADES_FOR_RANKING)
    ]
    if realistic.empty:
        lines.append("## Verdict: NO_DATA — no realistic cell with sufficient trades.")
        verdict_cell = None
    else:
        # primary key: Sharpe; tiebreak by annual_pnl, then n_trades
        ranked = realistic.sort_values(
            by=["sharpe", "annual_pnl_pip", "n_trades"],
            ascending=[False, False, False],
        )
        verdict_cell = ranked.iloc[0].to_dict()
        verdict, failed = classify_cell(verdict_cell)
        verdict_cell["_verdict"] = verdict
        verdict_cell["_failed"] = failed
        lines.append(f"## Verdict: **{verdict}**")
        lines.append("")
        lines.append(
            f"- Best realistic-exit cell: "
            f"N={verdict_cell['N']}, threshold={verdict_cell['threshold']}, "
            f"horizon={verdict_cell['horizon_bars']}, exit_rule={verdict_cell['exit_rule']}"
        )
        lines.append(
            f"- annual_trades={verdict_cell['annual_trades']:.0f} "
            f"(A0 ≥ 70: {'PASS' if verdict_cell['annual_trades'] >= ADOPT_MIN_TRADES else 'FAIL'})"
        )
        lines.append(
            f"- Sharpe={verdict_cell['sharpe']:.4f} "
            f"(A1 ≥ 0.082: {'PASS' if verdict_cell['sharpe'] >= ADOPT_MIN_SHARPE else 'FAIL'})"
        )
        lines.append(
            f"- annual_pnl={verdict_cell['annual_pnl_pip']:.1f} pip "
            f"(A2 ≥ 180: {'PASS' if verdict_cell['annual_pnl_pip'] >= ADOPT_MIN_PNL else 'FAIL'})"
        )
        lines.append(
            f"- MaxDD={verdict_cell['max_dd_pip']:.1f} pip "
            f"(A3 ≤ 200: {'PASS' if verdict_cell['max_dd_pip'] <= ADOPT_MAX_DD else 'FAIL'})"
        )
        a4_pass = verdict_cell["fold_pos"] >= 4 and verdict_cell["fold_neg"] <= 1
        lines.append(
            f"- fold pos/neg={verdict_cell['fold_pos']}/{verdict_cell['fold_neg']} "
            f"(A4 ≥ 4/1: {'PASS' if a4_pass else 'FAIL'})"
        )
        lines.append(
            f"- annual_pnl @ +0.5 pip stress={verdict_cell['annual_pnl_stress_+0.5']:.1f} "
            f"(A5 > 0: {'PASS' if verdict_cell['annual_pnl_stress_+0.5'] > 0 else 'FAIL'})"
        )
        if failed:
            lines.append("")
            lines.append("**Gates that failed**:")
            for f in failed:
                lines.append(f"- {f}")
        if verdict_cell["annual_trades"] > OVERTRADE_WARN_TRADES:
            lines.append("")
            ann_t = verdict_cell["annual_trades"]
            lines.append(
                f"⚠ Overtrading warning: annual_trades = {ann_t:.0f} > {OVERTRADE_WARN_TRADES}."
            )
        lines.append("")

    # Top-K table
    lines.append("## Top-10 cells (realistic exit_rule, by Sharpe)")
    lines.append("")
    lines.append(
        "| rank | N | thr | h | exit | n/yr | PnL/yr | Sharpe | MaxDD | DD%PnL"
        " | fold ± | +0.5 stress |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for i, c in enumerate(top_k_cells, 1):
        lines.append(
            f"| {i} | {c['N']} | {c['threshold']:.1f} | {c['horizon_bars']} | "
            f"{c['exit_rule']} | {c['annual_trades']:.0f} | {c['annual_pnl_pip']:.1f} | "
            f"{c['sharpe']:.4f} | {c['max_dd_pip']:.1f} | {c['dd_pct_pnl']:.1f}% | "
            f"{c['fold_pos']}/{c['fold_neg']} | {c['annual_pnl_stress_+0.5']:.1f} |"
        )
    lines.append("")

    # Per-fold table for top-10
    lines.append("## Top-10 per-fold PnL (pip)")
    lines.append("")
    lines.append("| rank | f1 | f2 | f3 | f4 | f5 | CV | top concentration |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for i, c in enumerate(top_k_cells, 1):
        lines.append(
            f"| {i} | {c['fold_0_pnl']:.1f} | {c['fold_1_pnl']:.1f} | "
            f"{c['fold_2_pnl']:.1f} | {c['fold_3_pnl']:.1f} | {c['fold_4_pnl']:.1f} | "
            f"{c['fold_pnl_cv']:.2f} | {c['fold_concentration_top']:.1%} |"
        )
    lines.append("")

    # Spread stress table for top-10
    lines.append("## Top-10 spread stress sensitivity (annual PnL, pip)")
    lines.append("")
    lines.append("| rank | base | +0.2 | +0.5 |")
    lines.append("|---|---|---|---|")
    for i, c in enumerate(top_k_cells, 1):
        lines.append(
            f"| {i} | {c['annual_pnl_pip']:.1f} | "
            f"{c['annual_pnl_stress_+0.2']:.1f} | "
            f"{c['annual_pnl_stress_+0.5']:.1f} |"
        )
    lines.append("")

    # best_possible vs realistic gap (failure-mode diagnostic)
    lines.append("## Failure-mode diagnostic — best_possible vs realistic")
    lines.append("")
    lines.append(
        "Per (N, threshold, horizon), compare `best_possible_pnl` (post-hoc path peak) "
        "with `tb_pnl` and `time_exit_pnl`. A large gap means path EV exists but the "
        "exit rule fails to capture it; a small gap means there is no path EV to capture."
    )
    lines.append("")
    keys = [(c["N"], c["threshold"], c["horizon_bars"]) for c in top_k_cells]
    seen: set[tuple[int, float, int]] = set()
    lines.append("| N | thr | h | best/yr | tb/yr | time_exit/yr | best - tb | best - time_exit |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for k in keys:
        if k in seen:
            continue
        seen.add(k)
        n, th, h = k
        sub = sweep_df[
            (sweep_df["N"] == n) & (sweep_df["threshold"] == th) & (sweep_df["horizon_bars"] == h)
        ]
        rows_by_exit = {row["exit_rule"]: row for _, row in sub.iterrows()}
        if (
            "best_possible_pnl" in rows_by_exit
            and "tb_pnl" in rows_by_exit
            and "time_exit_pnl" in rows_by_exit
        ):
            best = rows_by_exit["best_possible_pnl"]["annual_pnl_pip"]
            tb = rows_by_exit["tb_pnl"]["annual_pnl_pip"]
            te = rows_by_exit["time_exit_pnl"]["annual_pnl_pip"]
            lines.append(
                f"| {n} | {th:.1f} | {h} | {best:.1f} | {tb:.1f} | {te:.1f} | "
                f"{best - tb:+.1f} | {best - te:+.1f} |"
            )
    lines.append("")

    # Cost diagnostics
    lines.append("## Cost diagnostics for top-10 cells")
    lines.append("")
    for i, (c, diag) in enumerate(zip(top_k_cells, top_k_diagnostics, strict=False), 1):
        lines.append(
            f"### Rank {i}: N={c['N']}, thr={c['threshold']:.1f}, h={c['horizon_bars']}, "
            f"exit={c['exit_rule']}"
        )
        lines.append("")
        lines.append(f"- median spread_entry: {diag.get('median_spread_entry', 0):.3f} pip")
        lines.append(
            f"- median cost_ratio: {diag.get('median_cost_ratio', 0):.3f} "
            f"(p10 {diag.get('p10_cost_ratio', 0):.3f}, p90 {diag.get('p90_cost_ratio', 0):.3f})"
        )
        lines.append("")
        lines.append("PnL by cost_ratio bucket:")
        lines.append("")
        lines.append("| bucket | n | sum | mean |")
        lines.append("|---|---|---|---|")
        for k_, v in diag.get("by_cost_ratio_bucket", {}).items():
            lines.append(f"| {k_} | {v['n']} | {v['pnl_sum']:.1f} | {v['pnl_mean']:.3f} |")
        lines.append("")
        lines.append("PnL by spread_entry bucket:")
        lines.append("")
        lines.append("| bucket | n | sum | mean |")
        lines.append("|---|---|---|---|")
        for k_, v in diag.get("by_spread_bucket", {}).items():
            lines.append(f"| {k_} | {v['n']} | {v['pnl_sum']:.1f} | {v['pnl_mean']:.3f} |")
        lines.append("")
        lines.append("PnL by session:")
        lines.append("")
        lines.append("| session | n | sum | mean |")
        lines.append("|---|---|---|---|")
        for k_, v in diag.get("by_session", {}).items():
            lines.append(f"| {k_} | {v['n']} | {v['pnl_sum']:.1f} | {v['pnl_mean']:.3f} |")
        lines.append("")
        lines.append("Per-pair contribution (top 10 by absolute PnL):")
        lines.append("")
        lines.append("| pair | n | sum | mean |")
        lines.append("|---|---|---|---|")
        ranked = sorted(
            diag.get("by_pair", {}).items(),
            key=lambda kv: abs(kv[1]["pnl_sum"]),
            reverse=True,
        )[:10]
        for pair, v in ranked:
            lines.append(f"| {pair} | {v['n']} | {v['pnl_sum']:.1f} | {v['pnl_mean']:.3f} |")
        lines.append("")

    # NG list compliance
    lines.append("## NG list compliance (postmortem §4)")
    lines.append("")
    lines.append(
        f"- NG#1 pair filter: {len(pairs_used)}/20 pairs evaluated"
        f"{' (missing: ' + ', '.join(pairs_missing) + ')' if pairs_missing else ''}"
        "; no cell-level pair drop ✓"
    )
    lines.append("- NG#2 train-side time filter: not applied — z-score consumes all bars ✓")
    lines.append(
        "- NG#3 test-side filter improvement claim: verdict is on all valid+non-gap rows,"
        " not a time subset ✓"
    )
    lines.append("- NG#4 WeekOpen-aware sample weighting: none ✓")
    lines.append("- NG#5 universe-restricted cross-pair feature: none ✓")
    lines.append("")
    p.write_text("\n".join(lines), encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def init_accumulators() -> dict[tuple[int, float, int, str], CellAcc]:
    return {
        (n, th, h, exit_rule): CellAcc()
        for n in N_VALUES
        for th in THRESHOLDS
        for h in HORIZONS
        for exit_rule in EXIT_RULES
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pairs", nargs="*", default=PAIRS_CANONICAL_20)
    parser.add_argument("--days", type=int, default=730)
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Smoke run on USD_JPY, EUR_USD, GBP_JPY only.",
    )
    args = parser.parse_args(argv)

    if args.smoke:
        args.pairs = ["USD_JPY", "EUR_USD", "GBP_JPY"]

    args.out_dir.mkdir(parents=True, exist_ok=True)

    accumulators = init_accumulators()

    pairs_used: list[str] = []
    pairs_missing: list[str] = []
    print(f"=== Stage 22.0b Mean Reversion Baseline ({len(args.pairs)} pairs) ===")
    for i, pair in enumerate(args.pairs, 1):
        t0 = time.time()
        try:
            n_valid = process_pair(pair, args.days, accumulators)
        except FileNotFoundError as exc:
            print(f"[{i:2d}/{len(args.pairs)}] {pair}: SKIP (no data: {exc})")
            pairs_missing.append(pair)
            continue
        elapsed = time.time() - t0
        pairs_used.append(pair)
        print(f"[{i:2d}/{len(args.pairs)}] {pair}: valid_label_rows={n_valid:>9} ({elapsed:5.1f}s)")

    # Materialize each cell to compute metrics
    sweep_rows: list[dict] = []
    cell_dfs: dict[tuple[int, float, int, str], pd.DataFrame] = {}
    print("Materializing cells and computing metrics ...")
    for cell_key, acc in accumulators.items():
        df = acc.materialize()
        cell_dfs[cell_key] = df
        sweep_rows.append(compute_cell_metrics(cell_key, df))
    sweep_df = pd.DataFrame(sweep_rows)

    # Write the full sweep parquet
    sweep_path = args.out_dir / "sweep_results.parquet"
    sweep_df.to_parquet(sweep_path, compression="snappy")
    print(f"Sweep results: {sweep_path}")

    # Top-K diagnostic — exclude degenerate cells (too few trades for stable stats)
    realistic = sweep_df[
        sweep_df["exit_rule"].isin(REALISTIC_EXIT_RULES)
        & (sweep_df["n_trades"] >= MIN_TRADES_FOR_RANKING)
    ]
    top_sorted = realistic.sort_values(
        by=["sharpe", "annual_pnl_pip", "n_trades"],
        ascending=[False, False, False],
    )
    top_k = top_sorted.head(args.top_k).to_dict("records")
    top_k_diags: list[dict] = []
    for c in top_k:
        cell_key = (int(c["N"]), float(c["threshold"]), int(c["horizon_bars"]), c["exit_rule"])
        df = cell_dfs[cell_key]
        top_k_diags.append(cost_diagnostics(df))

    report_path = write_report(
        sweep_df,
        top_k,
        top_k_diags,
        args.out_dir,
        pairs_used,
        pairs_missing,
    )
    print(f"Report: {report_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
