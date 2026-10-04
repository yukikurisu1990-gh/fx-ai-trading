"""R-A2b の部品を**合成入力だけで**確かめる（実 data は読まない）。"""

from __future__ import annotations

import ast
import hashlib
import inspect
import math
import pathlib

import numpy as np
import pandas as pd
import pytest

from scripts.research.fxid_cycle1 import stats
from scripts.research.fxid_ny_followup import economics as eco
from scripts.research.fxid_ny_followup import run as driver

REPO = pathlib.Path(driver.__file__).resolve().parents[3]


def test_preregistered_times_are_pinned():
    assert eco.PRIMARY == {"ny_0900": (9, 0), "ny_0930": (9, 30), "ny_1000": (10, 0)}
    assert eco.BASELINE == {"ny_0800": (8, 0)}
    assert pd.Timedelta(hours=4) == eco.HOLD
    assert (eco.K_BASE, eco.N_BASE, eco.SLIP_BASE_BP, eco.THRESHOLD, eco.S_TARGET) == (
        3,
        100,
        0.5,
        0.15,
        1.0,
    )
    assert eco.K_GRID == (2, 3, 5) and eco.N_GRID == (50, 100, 200)
    assert eco.SLIP_GRID_BP == (0.5, 1.0)


def test_preregistration_hash_is_pinned_in_the_driver():
    raw = (REPO / driver.PREREG).read_bytes().replace(b"\r\n", b"\n")
    assert hashlib.sha256(raw).hexdigest() == driver.PREREG_SHA256


@pytest.mark.parametrize(
    ("day", "hour", "minute", "utc"),
    [
        ("2023-07-12", 9, 30, "13:30"),
        ("2023-01-11", 9, 30, "14:30"),
        ("2023-03-13", 9, 0, "13:00"),  # 夏時間の開始の翌月曜
        ("2023-11-06", 10, 0, "15:00"),  # 冬時間の開始の翌月曜
    ],
)
def test_ny_moments_follow_dst(day, hour, minute, utc):
    m = eco.ny_moments(day, day, hour, minute)
    assert len(m) == 1 and m[0].strftime("%H:%M") == utc


def test_weekends_are_skipped_and_exits_are_same_day():
    m = eco.ny_moments("2023-07-08", "2023-07-14", 10, 0)  # 土〜金
    assert len(m) == 5
    assert eco.same_day_exit(m).all()
    late = eco.ny_moments("2023-07-10", "2023-07-10", 13, 0)  # 17:00 決済は不可
    assert not eco.same_day_exit(late).any()


def test_required_formula_matches_cycle1():
    v = eco.required_gross_to_sigma(2.0, 25.0, 3, 100, 0.5)
    assert math.isclose(v, 2.5 / 25.0 + 1 / math.sqrt(300))


def _frame(days=60, spread_pips=1.0, seed=0):
    rng = np.random.default_rng(seed)
    ts = pd.date_range("2023-06-05", periods=days * 96, freq="15min", tz="UTC")
    mid = 1.1 * np.exp(np.cumsum(rng.normal(0, 3e-4, len(ts))))
    raw = pd.DataFrame(
        {
            "ts": ts,
            "mid_c": mid,
            "mid_h": mid * 1.0003,
            "mid_l": mid * 0.9997,
            "spread_close_pips": spread_pips,
            "pip_size": 1e-4,
        }
    )
    out = stats.prepare(raw)
    out["spread_rel"] = (
        1e-4  # 相対 spread を一定にする（mid の変動で pips 一定は相対で一定にならない）
    )
    return out


def test_constant_spread_methods_agree_and_no_double_count(monkeypatch):
    monkeypatch.setattr(stats, "FIRST", "2023-06-05")
    monkeypatch.setattr(stats, "LAST", "2023-07-31")
    frame = _frame()
    row = eco.anchor_table(frame, 9, 30)
    assert row["days"] > 30
    # 一定の spread なら half + half = 片側の全額 = Cycle 1 の方式
    assert math.isclose(row["rt_half_spread_bp"], row["entry_spread_bp"], rel_tol=1e-9)
    assert math.isclose(row["rt_half_spread_bp"], row["cycle1_window_spread_bp"], rel_tol=1e-9)


def test_exit_spread_is_measured_separately(monkeypatch):
    monkeypatch.setattr(stats, "FIRST", "2023-06-05")
    monkeypatch.setattr(stats, "LAST", "2023-07-31")
    frame = _frame()
    close_ny = (frame["ts"] + stats.BAR).dt.tz_convert("America/New_York")
    wide = (close_ny.dt.hour == 13) & (close_ny.dt.minute == 30)
    frame.loc[wide, "spread_rel"] *= 3
    row = eco.anchor_table(frame, 9, 30)
    assert math.isclose(row["exit_spread_bp"], 3 * row["entry_spread_bp"], rel_tol=1e-6)
    assert math.isclose(row["rt_half_spread_bp"], 2 * row["entry_spread_bp"], rel_tol=1e-6)


def test_classify():
    assert eco.classify({"a": 0.1, "b": 0.1, "c": 0.1}) == "R_A2B_ECON_ALL_THREE"
    assert eco.classify({"a": 0.2, "b": 0.1, "c": 0.2}) == "R_A2B_ECON_PARTIAL"
    assert eco.classify({"a": 0.2, "b": 0.2, "c": 0.2}) == "R_A2B_ECON_NONE"


FORBIDDEN = {"side", "pnl", "direction", "signal", "profit", "sign", "long", "short"}


def _names(module) -> set[str]:
    tree = ast.parse(inspect.getsource(module))
    return {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} | {
        n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)
    }


def test_no_direction_or_pnl_concepts():
    assert not (_names(eco) & FORBIDDEN)
    assert not (_names(driver) & FORBIDDEN)


def test_moves_only_feed_std_and_breadth():
    """`moves` は np.std と breadth にだけ渡る（平均・和を取らない）。"""
    tree = ast.parse(inspect.getsource(eco))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            text = ast.unparse(node)
            if "moves" in text and "_moves" not in text:
                func = ast.unparse(node.func)
                assert func in {"np.std", "pd.Series"} or text.startswith("float(np.std("), text


def test_driver_reads_only_through_the_guarded_route():
    tree = ast.parse(inspect.getsource(driver))
    imported = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module} | {
        a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names
    }
    assert "scripts.research.patsd_stage0" in imported
    assert not any(m.startswith(("oandapyV20", "requests", "urllib", "httpx")) for m in imported)
    calls = {ast.unparse(n.func) for n in ast.walk(tree) if isinstance(n, ast.Call)}
    assert "guarded.load_pair" in calls
    assert not any("read_parquet" in c or "read_csv" in c for c in calls)


def test_no_aggregate_of_price_changes_other_than_std():
    """log mid（とその差）に平均・和を取る式が無い（別名も、log_mid を含む代入で追う）。"""
    tree = ast.parse(inspect.getsource(eco))
    tainted = {"log_mid", "moves", "_moves"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(t in ast.unparse(node.value) for t in tainted):
            for target in node.targets:
                tainted.add(ast.unparse(target))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = ast.unparse(node.func)
        args = " ".join(ast.unparse(a) for a in node.args)
        receiver = ast.unparse(node.func.value) if isinstance(node.func, ast.Attribute) else ""
        aggregate = func.split(".")[-1] in {"mean", "sum", "cumsum", "average", "nanmean", "nansum"}
        if aggregate:
            assert not any(t in args or t in receiver for t in tainted), ast.unparse(node)


def test_recorded_artifact_has_no_direction_or_pnl_keys():
    import json

    path = REPO / "artifacts/research/fxid_ny_followup/r_a2b.json"
    keys: set[str] = set()

    def walk(value):
        if isinstance(value, dict):
            for k, v in value.items():
                keys.add(k)
                walk(v)
        elif isinstance(value, list):
            for v in value:
                walk(v)

    walk(json.loads(path.read_text(encoding="utf-8")))
    banned = (
        "pnl",
        "sharpe",
        "win_rate",
        "winrate",
        "side",
        "direction",
        "signal",
        "mean_return",
        "profit",
    )
    assert not [k for k in keys if any(b in k.lower() for b in banned)]
