"""Unit tests for Stage 24.0a path-EV characterisation."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

stage24_0a = importlib.import_module("stage24_0a_path_ev_characterisation")


# ---------------------------------------------------------------------------
# 1: score formula constants are fixed
# ---------------------------------------------------------------------------


def test_score_formula_constants_fixed():
    assert stage24_0a.AXIS_1_WEIGHT == 1.0
    assert stage24_0a.AXIS_2_WEIGHT == 0.3
    assert stage24_0a.AXIS_3_WEIGHT == -0.5
    assert stage24_0a.K == 3
    assert stage24_0a.ANNUAL_TRADES_MIN == 70.0
    assert stage24_0a.MAX_PAIR_SHARE == 0.5
    assert stage24_0a.MIN_FOLD_SHARE == 0.10
    assert stage24_0a.POSITIVE_RATE_MIN == 0.55
    # Confirm CLI does not expose these
    import inspect

    src = inspect.getsource(stage24_0a.main)
    for k in ("AXIS_1_WEIGHT", "AXIS_2_WEIGHT", "AXIS_3_WEIGHT", "K", "POSITIVE_RATE_MIN"):
        assert f"default={k}" not in src


# ---------------------------------------------------------------------------
# 2-7: eligibility excludes for each constraint
# ---------------------------------------------------------------------------


def _full_metrics(**overrides) -> dict:
    base = {
        "n_trades": 1000,
        "annual_trades": 500.0,
        "mean_best_possible_pnl": 1.0,
        "median_best_possible_pnl": 0.5,
        "p75_best_possible_pnl": 1.5,
        "positive_rate_best_pnl": 0.6,
        "realised_gap": 0.5,
        "mean_abs_mae_after_cost": 1.0,
        "worst_possible_pnl_p10": -2.0,
        "max_pair_share": 0.1,
        "min_fold_share": 0.20,
    }
    base.update(overrides)
    return base


def test_eligibility_excludes_low_trade_count():
    m = _full_metrics(annual_trades=50.0)
    assert not stage24_0a.is_eligible(m)


def test_eligibility_excludes_pair_concentration():
    m = _full_metrics(max_pair_share=0.7)
    assert not stage24_0a.is_eligible(m)


def test_eligibility_excludes_fold_concentration():
    m = _full_metrics(min_fold_share=0.05)
    assert not stage24_0a.is_eligible(m)


def test_eligibility_excludes_negative_mean_path_ev():
    m = _full_metrics(mean_best_possible_pnl=-0.5)
    assert not stage24_0a.is_eligible(m)


def test_eligibility_excludes_negative_p75_path_ev():
    m = _full_metrics(p75_best_possible_pnl=-0.3)
    assert not stage24_0a.is_eligible(m)


def test_eligibility_excludes_low_positive_rate():
    m = _full_metrics(positive_rate_best_pnl=0.50)
    assert not stage24_0a.is_eligible(m)


def test_eligibility_passes_when_all_six_satisfied():
    m = _full_metrics()
    assert stage24_0a.is_eligible(m)


# ---------------------------------------------------------------------------
# 8: score formula axis 1 dominates
# ---------------------------------------------------------------------------


def test_score_axis1_increases_with_mean_best():
    m1 = _full_metrics(mean_best_possible_pnl=1.0)
    m2 = _full_metrics(mean_best_possible_pnl=2.0)
    assert stage24_0a.compute_score(m2) > stage24_0a.compute_score(m1)


# ---------------------------------------------------------------------------
# 9: axis 3 penalises adverse path
# ---------------------------------------------------------------------------


def test_score_axis3_penalises_adverse_path():
    m1 = _full_metrics(mean_abs_mae_after_cost=1.0)
    m2 = _full_metrics(mean_abs_mae_after_cost=3.0)
    # higher mae → lower score (because weight is -0.5)
    assert stage24_0a.compute_score(m2) < stage24_0a.compute_score(m1)


# ---------------------------------------------------------------------------
# 10: p75 NOT in score
# ---------------------------------------------------------------------------


def test_p75_not_in_score():
    m1 = _full_metrics(p75_best_possible_pnl=1.0)
    m2 = _full_metrics(p75_best_possible_pnl=10.0)
    assert stage24_0a.compute_score(m1) == stage24_0a.compute_score(m2)


# ---------------------------------------------------------------------------
# 11: halt triggers when no eligible cell
# ---------------------------------------------------------------------------


def test_halt_triggers_when_no_cell_eligible():
    cell_results = [
        {
            **stage24_0a.PHASE23_CELLS[i],
            "metrics": _full_metrics(annual_trades=50),
            "eligible": False,
            "score": float("-inf"),
        }
        for i in range(5)
    ]
    halt, frozen = stage24_0a.select_frozen(cell_results)
    assert halt is True
    assert frozen == []


# ---------------------------------------------------------------------------
# 12: top-K returns at most K
# ---------------------------------------------------------------------------


def test_top_k_returns_at_most_k():
    cell_results = []
    for i in range(10):
        m = _full_metrics(mean_best_possible_pnl=float(i + 1))
        cell_results.append(
            {
                **stage24_0a.PHASE23_CELLS[i],
                "metrics": m,
                "eligible": True,
                "score": stage24_0a.compute_score(m),
            }
        )
    halt, frozen = stage24_0a.select_frozen(cell_results)
    assert halt is False
    assert len(frozen) == stage24_0a.K  # = 3


# ---------------------------------------------------------------------------
# 13: top-K returns fewer when eligible count < K
# ---------------------------------------------------------------------------


def test_top_k_returns_fewer_when_eligible_count_lt_k():
    cell_results = []
    for i in range(5):
        eligible = i < 2  # only first 2 eligible
        m = _full_metrics(mean_best_possible_pnl=float(i + 1) if eligible else -1.0)
        cell_results.append(
            {
                **stage24_0a.PHASE23_CELLS[i],
                "metrics": m,
                "eligible": eligible,
                "score": stage24_0a.compute_score(m) if eligible else float("-inf"),
            }
        )
    halt, frozen = stage24_0a.select_frozen(cell_results)
    assert halt is False
    assert len(frozen) == 2


# ---------------------------------------------------------------------------
# 14: Phase 23 cell enumeration total = 216
# ---------------------------------------------------------------------------


def test_phase23_cell_enumeration_total_216():
    assert len(stage24_0a.PHASE23_CELLS) == 216
    counts = {}
    for c in stage24_0a.PHASE23_CELLS:
        counts[c["source_stage"]] = counts.get(c["source_stage"], 0) + 1
    assert counts == {"23.0b": 18, "23.0c": 36, "23.0d": 18, "23.0c-rev1": 144}


# ---------------------------------------------------------------------------
# 15: signal generators imported from Phase 23 modules
# ---------------------------------------------------------------------------


def test_signal_generators_imported_from_phase23_modules():
    assert hasattr(stage24_0a, "stage23_0b")
    assert hasattr(stage24_0a, "stage23_0c")
    assert hasattr(stage24_0a, "stage23_0d")
    assert hasattr(stage24_0a, "stage23_0c_rev1")
    assert callable(stage24_0a.stage23_0b.extract_signals)
    assert callable(stage24_0a.stage23_0c.extract_signals_first_touch)
    assert callable(stage24_0a.stage23_0d.extract_signals_first_touch_donchian)
    assert callable(stage24_0a.stage23_0c_rev1._signals_first_touch)
    assert callable(stage24_0a.stage23_0c_rev1._signals_f1_neutral_reset)
    assert callable(stage24_0a.stage23_0c_rev1._signals_f2_cooldown)
    assert callable(stage24_0a.stage23_0c_rev1._signals_f3_reversal)


# ---------------------------------------------------------------------------
# 16: frozen JSON includes required fields
# ---------------------------------------------------------------------------


def test_frozen_entry_streams_json_includes_required_fields():
    cell_results = []
    for i in range(5):
        eligible = i < 3
        m = _full_metrics(mean_best_possible_pnl=float(i + 1) if eligible else -1.0)
        cell_results.append(
            {
                **stage24_0a.PHASE23_CELLS[i],
                "metrics": m,
                "eligible": eligible,
                "score": stage24_0a.compute_score(m) if eligible else float("-inf"),
            }
        )
    halt, frozen = stage24_0a.select_frozen(cell_results)
    payload = stage24_0a._make_frozen_payload(cell_results, halt, frozen)
    assert payload["version"] == "24.0a-1"
    assert "halt_criteria" in payload
    assert "eligibility_criteria" in payload
    assert "score_formula" in payload
    assert "K" in payload
    assert payload["K"] == 3
    assert "frozen_cells" in payload
    if frozen:
        cell0 = payload["frozen_cells"][0]
        for k in (
            "rank",
            "source_stage",
            "source_pr",
            "source_merge_commit",
            "source_verdict",
            "reject_reason",
            "signal_timeframe",
            "filter",
            "cell_params",
            "score",
            "metrics",
        ):
            assert k in cell0


# ---------------------------------------------------------------------------
# 17: smoke mode shape
# ---------------------------------------------------------------------------


def test_smoke_mode_3pairs_3cells_from_23_0b():
    assert len(stage24_0a.SMOKE_PAIRS) == 3
    smoke = stage24_0a.smoke_cells()
    assert len(smoke) == 3
    assert all(c["source_stage"] == "23.0b" for c in smoke)


# ---------------------------------------------------------------------------
# 18: tie-breaker uses lower mae
# ---------------------------------------------------------------------------


def test_tie_breaker_lower_mae_wins():
    # Two cells with same score; one has lower mae → should rank first
    m1 = _full_metrics(mean_best_possible_pnl=1.0, realised_gap=0.0, mean_abs_mae_after_cost=2.0)
    m2 = _full_metrics(mean_best_possible_pnl=1.0, realised_gap=0.0, mean_abs_mae_after_cost=1.0)
    s1 = stage24_0a.compute_score(m1)
    s2 = stage24_0a.compute_score(m2)
    # Score tie: 1.0 + 0 - 0.5*2.0 = 0.0 vs 1.0 + 0 - 0.5*1.0 = 0.5 — actually different
    # So construct both with axis 3 contributing same, varying only mae for tie-break test
    m1 = _full_metrics(mean_best_possible_pnl=2.0, realised_gap=0.0, mean_abs_mae_after_cost=2.0)
    m2 = _full_metrics(mean_best_possible_pnl=1.5, realised_gap=0.0, mean_abs_mae_after_cost=1.0)
    s1 = stage24_0a.compute_score(m1)  # 2 - 0.5*2 = 1.0
    s2 = stage24_0a.compute_score(m2)  # 1.5 - 0.5*1 = 1.0
    assert s1 == s2, f"setup expects equal scores; got {s1} vs {s2}"
    cell_results = [
        {**stage24_0a.PHASE23_CELLS[0], "metrics": m1, "eligible": True, "score": s1},
        {**stage24_0a.PHASE23_CELLS[1], "metrics": m2, "eligible": True, "score": s2},
    ]
    _, frozen = stage24_0a.select_frozen(cell_results)
    # Cell 2 (mae=1.0) should rank before cell 1 (mae=2.0) on tie-break
    assert frozen[0]["metrics"]["mean_abs_mae_after_cost"] == 1.0


# ---------------------------------------------------------------------------
# 19: compute_metrics on synthetic trades
# ---------------------------------------------------------------------------


def test_compute_metrics_handles_empty():
    m = stage24_0a.compute_metrics(pd.DataFrame())
    assert m["n_trades"] == 0
    assert m["annual_trades"] == 0.0


def test_compute_metrics_basic_shape():
    n = 100
    trades = pd.DataFrame(
        {
            "entry_ts": pd.date_range("2026-01-01", periods=n, freq="1h", tz="UTC"),
            "pair": ["EUR_USD"] * n,
            "direction": ["long"] * n,
            "tb_pnl": np.full(n, -0.5, dtype=np.float64),
            "time_exit_pnl": np.full(n, -1.0, dtype=np.float64),
            "best_possible_pnl": np.linspace(-2, 4, n).astype(np.float64),
            "mae_after_cost": np.linspace(-3, -1, n).astype(np.float64),
            "worst_possible_pnl": np.linspace(-5, -2, n).astype(np.float64),
            "cost_ratio": np.full(n, 0.5),
            "signal_timeframe": ["M5"] * n,
        }
    )
    m = stage24_0a.compute_metrics(trades)
    assert m["n_trades"] == n
    # mean of linspace(-2, 4, 100) = 1.0
    assert abs(m["mean_best_possible_pnl"] - 1.0) < 1e-6
    # positive_rate: count of best_possible_pnl > 0
    expected_pos = float((np.linspace(-2, 4, n) > 0).mean())
    assert abs(m["positive_rate_best_pnl"] - expected_pos) < 1e-6
    # max_pair_share = 1.0 (all EUR_USD)
    assert m["max_pair_share"] == 1.0
    # realised_gap = mean_best - mean(max(tb, time_exit))
    # = 1.0 - max(-0.5, -1.0) = 1.0 - (-0.5) = 1.5
    assert abs(m["realised_gap"] - 1.5) < 1e-6


# ---------------------------------------------------------------------------
# 20: each Phase 23 cell has source attribution
# ---------------------------------------------------------------------------


def test_each_cell_has_source_attribution():
    for c in stage24_0a.PHASE23_CELLS:
        assert "source_stage" in c
        assert "source_pr" in c
        assert "source_merge_commit" in c
        assert "source_verdict" in c
        assert "reject_reason" in c
        assert "signal_timeframe" in c
        assert "cell_params" in c
        # verdict should be REJECT for all 216 (Phase 23 conclusion)
        assert c["source_verdict"] == "REJECT"
        # signal_timeframe must be M5 or M15
        assert c["signal_timeframe"] in ("M5", "M15")
