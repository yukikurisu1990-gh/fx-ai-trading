"""Stage 22.0b Mean Reversion Baseline unit tests.

Verifies causal z-score, parquet join keys, NG list compliance, fold split,
spread stress, verdict logic, and the diagnostic-only treatment of
best_possible_pnl.
"""

from __future__ import annotations

import importlib.util
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "stage22_0b_mean_reversion_baseline.py"

_spec = importlib.util.spec_from_file_location("stage22_0b_mr", SCRIPT)
assert _spec is not None and _spec.loader is not None
mod = importlib.util.module_from_spec(_spec)
sys.modules["stage22_0b_mr"] = mod
_spec.loader.exec_module(mod)


# ---------------------------------------------------------------------------
# Causal z-score
# ---------------------------------------------------------------------------


def test_zscore_causal_no_lookahead() -> None:
    """Perturbing future bars must not change z[t]."""
    base = np.linspace(100.0, 100.5, 200)
    s_a = pd.Series(base.copy())
    s_b = pd.Series(base.copy())
    s_b.iloc[150:] += 5.0  # mutate the future
    z_a = mod.causal_zscore(s_a, n=20)
    z_b = mod.causal_zscore(s_b, n=20)
    # bars before the perturbation must be identical
    pd.testing.assert_series_equal(z_a.iloc[:150], z_b.iloc[:150])


def test_zscore_signal_directions() -> None:
    """A high z value implies short signal; a low z implies long."""
    rng = np.random.default_rng(0)
    arr = 100.0 + rng.normal(scale=0.01, size=500)
    arr[300] = 105.0  # spike up → z high
    arr[400] = 95.0  # spike down → z low
    s = pd.Series(arr)
    z = mod.causal_zscore(s, n=30)
    assert z.iloc[300] > 2.0
    assert z.iloc[400] < -2.0
    # signals derived from these
    threshold = 1.5
    assert z.iloc[300] > threshold  # → short
    assert z.iloc[400] < -threshold  # → long


def test_zscore_first_n_bars_nan() -> None:
    s = pd.Series(np.linspace(100.0, 101.0, 50))
    z = mod.causal_zscore(s, n=20)
    assert z.iloc[:19].isna().all()
    assert not z.iloc[19:].isna().all()


def test_zscore_zero_sigma_returns_nan() -> None:
    s = pd.Series([100.0] * 50)  # constant → sigma=0
    z = mod.causal_zscore(s, n=20)
    assert z.isna().all()


# ---------------------------------------------------------------------------
# Cell metrics: spread stress, fold split, sharpe
# ---------------------------------------------------------------------------


def _make_trades(
    timestamps: list[datetime], pnl: list[float], pair: str = "USD_JPY"
) -> pd.DataFrame:
    n = len(timestamps)
    return (
        pd.DataFrame(
            {
                "entry_ts": pd.to_datetime(timestamps, utc=True),
                "pnl": np.asarray(pnl, dtype=np.float64),
                "pair": [pair] * n,
                "spread_entry": np.full(n, 1.5, dtype=np.float32),
                "cost_ratio": np.full(n, 0.9, dtype=np.float32),
                "hour_utc": np.full(n, 10, dtype=np.int8),
                "dow": np.full(n, 1, dtype=np.int8),
                "direction": ["long"] * n,
            }
        )
        .sort_values("entry_ts")
        .reset_index(drop=True)
    )


def test_spread_stress_subtracts_uniformly_from_pnl() -> None:
    start = datetime(2025, 1, 1, tzinfo=UTC)
    ts = [start + timedelta(hours=i) for i in range(100)]
    pnl = [1.0] * 100
    trades = _make_trades(ts, pnl)
    cell_key = (20, 2.0, 10, "tb_pnl")
    metrics = mod.compute_cell_metrics(cell_key, trades)
    base = metrics["annual_pnl_pip"]
    stressed_05 = metrics["annual_pnl_stress_+0.5"]
    # Annualization uses the fixed dataset span (~2 years)
    expected_drop = 0.5 * len(ts) / mod.EVAL_SPAN_YEARS_DEFAULT
    assert abs(base - stressed_05 - expected_drop) < 1e-3


def test_fold_split_5_chronological_buckets() -> None:
    start = datetime(2025, 1, 1, tzinfo=UTC)
    ts = [start + timedelta(days=i) for i in range(100)]
    pnl = [1.0] * 100
    trades = _make_trades(ts, pnl)
    cell_key = (20, 2.0, 10, "tb_pnl")
    metrics = mod.compute_cell_metrics(cell_key, trades)
    # 5 folds of 20 trades each (boundary may include one extra in last fold)
    fold_ns = [metrics[f"fold_{i}_n"] for i in range(5)]
    assert sum(fold_ns) == 100
    assert metrics["fold_pos"] == 5  # all folds positive PnL
    assert metrics["fold_neg"] == 0


def test_fold_pos_neg_with_mixed_signs() -> None:
    start = datetime(2025, 1, 1, tzinfo=UTC)
    ts = [start + timedelta(days=i) for i in range(100)]
    # first 60 days positive, last 40 negative
    pnl = [1.0] * 60 + [-1.0] * 40
    trades = _make_trades(ts, pnl)
    metrics = mod.compute_cell_metrics((20, 2.0, 10, "tb_pnl"), trades)
    # folds 0-2 (~0..60) positive, fold 3-4 (~60..100) negative
    assert metrics["fold_pos"] >= 3
    assert metrics["fold_neg"] >= 1


# ---------------------------------------------------------------------------
# Verdict logic
# ---------------------------------------------------------------------------


def _cell_metric_template(**overrides) -> dict:
    base = {
        "N": 20,
        "threshold": 2.0,
        "horizon_bars": 10,
        "exit_rule": "tb_pnl",
        "n_trades": 1000,
        "annual_trades": 500.0,
        "annual_pnl_pip": 250.0,
        "sharpe": 0.15,
        "max_dd_pip": 100.0,
        "dd_pct_pnl": 40.0,
        "mean_pnl": 0.5,
        "median_pnl": 0.4,
        "win_rate": 0.55,
        "annual_pnl_stress_+0.0": 250.0,
        "annual_pnl_stress_+0.2": 150.0,
        "annual_pnl_stress_+0.5": 50.0,
        "sharpe_stress_+0.0": 0.15,
        "sharpe_stress_+0.2": 0.10,
        "sharpe_stress_+0.5": 0.05,
        "fold_pos": 5,
        "fold_neg": 0,
        "fold_pnl_cv": 0.5,
        "fold_concentration_top": 0.30,
        **{f"fold_{i}_pnl": 50.0 for i in range(5)},
        **{f"fold_{i}_n": 200 for i in range(5)},
    }
    base.update(overrides)
    return base


def test_verdict_adopt_when_all_gates_pass() -> None:
    cell = _cell_metric_template()
    verdict, failed = mod.classify_cell(cell)
    assert verdict == "ADOPT"
    assert failed == []


def test_verdict_promising_when_a4_fails_but_a1_a2_a3_pass() -> None:
    cell = _cell_metric_template(fold_pos=2, fold_neg=3)
    verdict, failed = mod.classify_cell(cell)
    assert verdict == "PROMISING_BUT_NEEDS_OOS"
    assert any("A4" in f for f in failed)


def test_verdict_promising_when_a5_stress_fails() -> None:
    cell = _cell_metric_template(**{"annual_pnl_stress_+0.5": -5.0})
    verdict, failed = mod.classify_cell(cell)
    assert verdict == "PROMISING_BUT_NEEDS_OOS"
    assert any("A5" in f for f in failed)


def test_verdict_reject_when_a0_below_minimum_trades() -> None:
    cell = _cell_metric_template(annual_trades=20.0)
    verdict, failed = mod.classify_cell(cell)
    assert verdict == "REJECT"
    assert any("A0" in f for f in failed)


def test_verdict_reject_when_a1_below_baseline_sharpe() -> None:
    cell = _cell_metric_template(sharpe=0.05)
    verdict, failed = mod.classify_cell(cell)
    assert verdict == "REJECT"
    assert any("A1" in f for f in failed)


def test_verdict_reject_when_a2_below_baseline_pnl() -> None:
    cell = _cell_metric_template(annual_pnl_pip=120.0)
    verdict, failed = mod.classify_cell(cell)
    assert verdict == "REJECT"
    assert any("A2" in f for f in failed)


def test_best_possible_pnl_excluded_from_adopt_judgement() -> None:
    """best_possible_pnl is diagnostic-only; verdict must be REJECT
    regardless of the metric values.
    """
    cell = _cell_metric_template(exit_rule="best_possible_pnl", sharpe=2.0, annual_pnl_pip=10000.0)
    verdict, failed = mod.classify_cell(cell)
    assert verdict == "REJECT"
    assert any("non-realistic" in f or "diagnostic" in f for f in failed)


def test_overtrading_warning_threshold_constant() -> None:
    assert mod.OVERTRADE_WARN_TRADES == 1000
    assert mod.ADOPT_MIN_TRADES == 70


# ---------------------------------------------------------------------------
# Cell accumulator + cost diagnostics
# ---------------------------------------------------------------------------


def test_cell_acc_extend_concatenates_arrays() -> None:
    acc = mod.CellAcc()
    ts1 = pd.to_datetime(["2025-01-01", "2025-01-02"], utc=True).values
    ts2 = pd.to_datetime(["2025-01-03"], utc=True).values
    acc.extend(
        ts1,
        np.array([1.0, 2.0], dtype=np.float32),
        np.full(2, "USD_JPY", dtype=object),
        np.array([1.0, 1.0], dtype=np.float32),
        np.array([0.5, 0.5], dtype=np.float32),
        np.array([10, 11], dtype=np.int8),
        np.array([1, 1], dtype=np.int8),
        np.array(["long", "long"], dtype=object),
    )
    acc.extend(
        ts2,
        np.array([3.0], dtype=np.float32),
        np.full(1, "EUR_USD", dtype=object),
        np.array([0.8], dtype=np.float32),
        np.array([0.4], dtype=np.float32),
        np.array([12], dtype=np.int8),
        np.array([2], dtype=np.int8),
        np.array(["short"], dtype=object),
    )
    df = acc.materialize()
    assert len(df) == 3
    assert df["pair"].tolist() == ["USD_JPY", "USD_JPY", "EUR_USD"]
    assert df["entry_ts"].is_monotonic_increasing


def test_cost_diagnostic_buckets_disjoint_and_total_correct() -> None:
    rng = np.random.default_rng(42)
    n = 5000
    ts = pd.to_datetime(np.arange(n) * 60_000_000_000, utc=True)  # 1 minute apart
    cost_ratios = rng.uniform(0, 3, size=n).astype(np.float32)
    spreads = rng.uniform(0, 4, size=n).astype(np.float32)
    pnls = rng.normal(scale=1.0, size=n).astype(np.float32)
    df = pd.DataFrame(
        {
            "entry_ts": ts,
            "pnl": pnls,
            "pair": ["USD_JPY"] * n,
            "spread_entry": spreads,
            "cost_ratio": cost_ratios,
            "hour_utc": rng.integers(0, 24, size=n).astype(np.int8),
            "dow": rng.integers(0, 7, size=n).astype(np.int8),
            "direction": ["long"] * n,
        }
    )
    diag = mod.cost_diagnostics(df)
    # buckets must sum to total n (entries with cost_ratio < 0 don't exist here)
    bucket_n = sum(b["n"] for b in diag["by_cost_ratio_bucket"].values())
    assert bucket_n == n
    sp_bucket_n = sum(b["n"] for b in diag["by_spread_bucket"].values())
    assert sp_bucket_n == n


# ---------------------------------------------------------------------------
# NG-list compliance
# ---------------------------------------------------------------------------


def test_no_week_open_filter_in_pipeline() -> None:
    """The script must not consult `is_week_open_window` when producing trades.

    We assert the column is never read by the script's strategy loop.
    """
    src = SCRIPT.read_text(encoding="utf-8")
    # the only place the term may appear is in NG-list comments, never as a
    # filtering predicate. Easiest check: the canonical filter line uses only
    # valid_label and gap_affected_forward_window.
    assert 'labels["valid_label"]' in src
    assert "gap_affected_forward_window" in src
    # ensure no row-drop on is_week_open_window in the strategy code
    assert (
        "is_week_open_window" not in src or src.count("is_week_open_window") <= 2
    )  # NG-list comment only


def test_no_pair_drop_in_loop() -> None:
    """The accumulator processes every pair where a parquet exists. It does
    NOT inspect pair tier or session bucket as a drop criterion."""
    src = SCRIPT.read_text(encoding="utf-8")
    # canonical 20-pair list constant must be present
    assert "PAIRS_CANONICAL_20" in src
    # ensure no implicit subsetting of pairs based on JPY/USD tier
    assert "pair_tier" not in src.lower()
    assert "currency_family" not in src.lower()


def test_canonical_pairs_list_size_20() -> None:
    assert len(mod.PAIRS_CANONICAL_20) == 20
    assert "CAD_JPY" not in mod.PAIRS_CANONICAL_20  # canonical 20 doesn't include CAD_JPY
    assert "GBP_CHF" in mod.PAIRS_CANONICAL_20


# ---------------------------------------------------------------------------
# Fold split has no future leakage (entries split by chronological order)
# ---------------------------------------------------------------------------


def test_fold_split_chronological_no_leakage() -> None:
    """Each fold must contain only trades from a contiguous chronological slice."""
    start = datetime(2025, 1, 1, tzinfo=UTC)
    ts = [start + timedelta(days=i) for i in range(50)]
    pnl = list(range(50))  # 0..49 — fold k should have higher pnl values than fold k-1
    trades = _make_trades(ts, [float(p) for p in pnl])
    metrics = mod.compute_cell_metrics((20, 2.0, 10, "tb_pnl"), trades)
    # fold sums are monotonically non-decreasing because pnl values increase with time
    fold_pnls = [metrics[f"fold_{i}_pnl"] for i in range(5)]
    for i in range(1, 5):
        assert fold_pnls[i] >= fold_pnls[i - 1]
