"""architecture redesign の合成・解析の算術の test（data を読まない）。"""

from __future__ import annotations

import ast
import inspect
import math

import numpy as np

from scripts.research.architecture_redesign import synthetic as syn


def test_incidence_has_rank_seven_for_eight_currencies():
    a = syn.incidence()
    assert a.shape == (20, 8)
    assert np.all(a.sum(axis=1) == 0)
    assert np.linalg.matrix_rank(a) == 7


def test_three_pair_signals_net_to_one_currency_bet():
    z = syn.net_currency_exposure({"EUR_USD": 1.0, "USD_JPY": -1.0, "EUR_JPY": 1.0})
    assert z == {"EUR": 2.0, "USD": -2.0}


def test_max_combined_sharpe_formula():
    assert math.isclose(syn.max_combined_sharpe(0.5, 0.5, 0.0), math.sqrt(0.5))
    assert math.isclose(syn.max_combined_sharpe(0.5, 0.5, 0.5), math.sqrt(0.25 / 0.75))
    assert math.isclose(syn.max_combined_sharpe(0.3, 0.0, 0.0), 0.3)


def test_false_discovery_selected_portfolio_is_null_out_of_sample():
    out = syn.portfolio_false_discovery(n=40, k=5, days=500, reps=60)
    assert out["mean_portfolio_insample_sharpe"] > 1.0
    assert abs(out["mean_portfolio_independent_period_sharpe"]) < 0.4


def test_module_reads_no_data():
    tree = ast.parse(inspect.getsource(syn))
    calls = {ast.unparse(n.func) for n in ast.walk(tree) if isinstance(n, ast.Call)}
    assert not any(
        c.endswith(("read_parquet", "read_csv", "load_pair", "load")) or "requests" in c
        for c in calls
    )
    imported = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
    assert imported <= {
        "__future__",
        "pathlib",
        "typing",
        "scipy.stats",
        "scripts.research.exploratory_m15.bars",
    }
