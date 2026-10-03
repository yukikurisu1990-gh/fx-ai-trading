"""FXID Cycle 1 の部品を**合成入力だけで**確かめる（実 data は読まない）。"""

from __future__ import annotations

import ast
import inspect

import numpy as np
import pandas as pd
import pytest

from scripts.research.fxid_cycle1 import clock, maxt, stats


# ----------------------------------------------------------------------
# 時計（DST）
# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    ("day", "name", "utc_hour"),
    [
        ("2023-07-12", "ny_open_0800", 12),
        ("2023-01-11", "ny_open_0800", 13),
        ("2023-07-12", "us_release_0830", 12),
        ("2023-07-12", "london_open_0800", 7),
        ("2023-01-11", "london_open_0800", 8),
        ("2023-07-12", "tokyo_open_0900", 0),
        ("2023-01-11", "tokyo_open_0900", 0),
    ],
)
def test_anchor_times_follow_local_dst(day, name, utc_hour):
    assert clock.anchor_utc(pd.Timestamp(day), name).hour == utc_hour


def test_trading_day_rolls_at_ny_17():
    ts = pd.Series(
        pd.to_datetime(
            ["2023-07-12 20:45", "2023-07-12 21:00", "2023-01-11 21:45", "2023-01-11 22:00"],
            utc=True,
        )
    )
    days = clock.trading_day(ts).astype(str).tolist()
    assert days == ["2023-07-12", "2023-07-13", "2023-01-11", "2023-01-12"]


# ----------------------------------------------------------------------
# R-A2 は signal を使わない
# ----------------------------------------------------------------------
FORBIDDEN_NAMES = {"side", "pnl", "direction", "signal", "profit"}


def _names(module) -> set[str]:
    tree = ast.parse(inspect.getsource(module))
    return {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} | {
        n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)
    }


def test_stats_module_has_no_direction_or_pnl_concepts():
    assert not (_names(stats) & FORBIDDEN_NAMES)


def test_returns_in_stats_are_only_used_for_std_or_correlation():
    """return（`ret_for_std`・`moves`・`block`）に平均や和を取らない。"""
    tree = ast.parse(inspect.getsource(stats))
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in {"mean", "sum", "cumsum"}
        ):
            target = ast.unparse(node.func.value)
            assert not any(k in target for k in ("ret_for_std", "moves", "block")), target


def _frame(days: int = 40, start: str = "2023-07-03", seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    ts = pd.date_range(start, periods=days * 96, freq="15min", tz="UTC")
    mid = 1.1 * np.exp(np.cumsum(rng.normal(0, 3e-4, len(ts))))
    raw = pd.DataFrame(
        {
            "ts": ts,
            "mid_c": mid,
            "mid_h": mid * 1.0003,
            "mid_l": mid * 0.9997,
            "spread_close_pips": 1.2,
            "pip_size": 1e-4,
        }
    )
    return stats.prepare(raw)


def test_anchor_moves_respect_same_day_exit():
    frame = _frame()
    long_hold = stats.anchor_moves(frame, "us_release_1000", 8)
    assert len(long_hold) == 0  # 10:00 ET + 8h は NY 16:45 を越える
    ok = stats.anchor_moves(frame, "ny_open_0800", 4)
    assert len(ok) > 0


def test_breadth_participation_ratio_bounds():
    rng = np.random.default_rng(0)
    base = pd.Series(rng.normal(size=200))
    same = {f"p{i}": base + rng.normal(0, 1e-3, 200) for i in range(5)}
    assert stats.breadth(same)["participation_ratio"] < 1.1
    indep = {f"p{i}": pd.Series(rng.normal(size=2000)) for i in range(5)}
    assert stats.breadth(indep)["participation_ratio"] > 4.5


def test_ambiguity_is_path_free_share():
    frame = _frame()
    out = stats.ambiguity_upper_bound(frame, 0.0003)
    expected = float((frame["range_rel"] >= 2 * 0.5 * 0.0003).mean())
    assert abs(out["w=0.5sigma4h"]["share_all_bars"] - expected) < 1e-6


# ----------------------------------------------------------------------
# max-T（合成だけ）
# ----------------------------------------------------------------------
def _grid(days: int = 300, pairs: int = 4) -> maxt.Grid:
    frames = {f"P{i}": _frame(days=days, start="2023-01-02", seed=i) for i in range(pairs)}
    cost = {k: 1e-4 for k in frames}
    return maxt.build_grid(frames, cost)


def test_candidates_are_inside_the_ny_window_and_same_day():
    grid = _grid()
    for c in maxt.make_candidates(grid, 4, seed=1):
        assert (grid.ny_minute[c.t0] >= maxt.ENTRY_NY_FIRST).all()
        assert (grid.ny_minute[c.t0] <= maxt.ENTRY_NY_LAST).all()
        assert (grid.day[c.t1] == grid.day[c.t0]).all()
        assert (grid.ny_minute[c.t1] <= maxt.EXIT_NY_LAST).all()


def test_synthetic_sign_keeps_magnitudes_and_common_sign():
    grid = _grid(days=60)
    out = maxt.synthetic_sign(grid, np.random.default_rng(0))
    assert np.allclose(np.abs(out), np.abs(grid.returns))
    nz = np.abs(grid.returns).min(axis=1) > 0
    ratio = out[nz] / grid.returns[nz]
    assert np.allclose(ratio, ratio[:, [0]])


def test_max_t_calibration_hits_target_on_gaussian_null():
    """純粋な合成の帰無の上で、較正した閾値の独立な検証の FWER が 10% 付近になる。"""
    rng = np.random.default_rng(1)
    cal = rng.standard_normal((800, 10)).max(axis=1)
    ver = rng.standard_normal((800, 10)).max(axis=1)
    out = maxt.calibrate_and_verify(cal, ver, boot=200)
    assert 0.06 < out["verification_fwer"] < 0.14
    assert abs(maxt.equivalent_trials(out["threshold_sharpe"], 1.0) - 10) < 4


def test_real_returns_in_maxt_only_feed_synthetic_generators():
    tree = ast.parse(inspect.getsource(maxt))
    allowed = {
        "build_grid",
        "synthetic_sign",
        "synthetic_gaussian",
        "make_candidates",
        "run_null",
        "selection_power",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            body = ast.unparse(node)
            if "grid.returns" in body:
                assert node.name in allowed, node.name
                if node.name not in {"build_grid", "synthetic_sign"}:
                    assert body.count("grid.returns") == body.count("grid.returns.shape"), node.name


# ----------------------------------------------------------------------
# pre-2016 取得の guard（取得はしない。合成の入力だけ）
# ----------------------------------------------------------------------
def test_acquisition_guard_accepts_only_exact_bounds_inside_the_window():
    import datetime as dt

    from scripts.research.fxid_cycle1 import acquisition_guard as g

    lo, hi = g.check_request("2006-01-02T00:00:00Z", "2016-05-31T21:00:00Z")
    assert hi == g.UPPER_EXCLUSIVE_UTC
    for bad in ("2016-05-31T21:00:01Z", "2016-06-01T00:00:00Z"):
        with pytest.raises(g.AcquisitionBoundaryError):
            g.check_request("2006-01-02T00:00:00Z", bad)
    for loose in (
        "2016-05",
        "2016",
        "2016-05-31",
        "2016-05-31 21:00:00",
        "2016-05-31T21:00:00+00:00",
    ):
        with pytest.raises(g.AcquisitionBoundaryError):
            g.check_request("2006-01-02T00:00:00Z", loose)

    class Sneaky(str):
        def __gt__(self, other):
            return False

    with pytest.raises(g.AcquisitionBoundaryError):
        g.check_request("2006-01-02T00:00:00Z", Sneaky("2017-01-01T00:00:00Z"))
    with pytest.raises(g.AcquisitionBoundaryError):
        g.check_distribution_unit(dt.date(2016, 1, 1), dt.date(2016, 12, 31))
    g.check_distribution_unit(dt.date(2016, 5, 1), dt.date(2016, 5, 31))


def test_acquisition_guard_rejects_whole_response_with_any_protected_row():
    import datetime as dt

    from scripts.research.fxid_cycle1 import acquisition_guard as g

    good = [dt.datetime(2016, 5, 31, 20, 45, tzinfo=dt.UTC)]
    g.check_response(good)
    with pytest.raises(g.AcquisitionBoundaryError):
        g.check_response(good + [dt.datetime(2016, 5, 31, 21, 0, tzinfo=dt.UTC)])
    with pytest.raises(g.AcquisitionBoundaryError):
        g.check_response([dt.datetime(2016, 5, 31, 20, 45)])
