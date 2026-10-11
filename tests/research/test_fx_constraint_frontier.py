"""FX Feasibility Constraint Frontier の契約（合成だけ、fresh 不読、G4 と HOLD は不変）。"""

from __future__ import annotations

import ast
import hashlib
import inspect
import pathlib

import numpy as np

from scripts.research.fx_constraint_frontier import contracts as c

REPO = pathlib.Path(__file__).resolve().parents[2]
HOLD = REPO / "docs/governance/fxid_long_term_hold_ruling_2026_10.md"
GOV = REPO / "docs/governance/fx_feasibility_constraint_frontier_review_2026_10.md"


def test_hold_ruling_bytes_are_pinned():
    raw = HOLD.read_bytes().replace(b"\r\n", b"\n")
    assert hashlib.sha256(raw).hexdigest() == (
        "e7abc2f56c559d0965c551485dbc9d4e883af8acd66ebfb2e393954d9718e221"
    )


def test_governance_keeps_g4_and_forbids_fresh_and_trading():
    gov = GOV.read_text(encoding="utf-8")
    assert "**`2016-06-02 … 2021-04-25`** を一切読まない" in gov
    assert "net Sharpe ≥ 1.0**。最初から下げない" in gov
    assert "live / demo / paper の取引" in gov


def test_contracts_module_reads_no_data():
    tree = ast.parse(inspect.getsource(c))
    names = {ast.unparse(n.func) for n in ast.walk(tree) if isinstance(n, ast.Call)}
    assert not any(x.endswith(("read_parquet", "read_csv", "load_pair", "open")) for x in names)


def test_g4_uses_the_system_prior_tau_0_4():
    assert c.TAU_SYS == 0.4
    go, post = c._go(np.array([1.98, 1.97]), 6.4)
    assert go.tolist() == [True, False]


def test_li_ji_meff_for_block_equicorrelation():
    assert abs(c.li_ji_meff(c.variant_corr(0.7, 0.0)) - 12.0) < 1e-9


def test_null_scenario_fwer_is_controlled_for_s0():
    d = c.draw(c.SCENARIOS[0], 4.67, 6.4, 2000, np.random.default_rng(1))
    m = c.metrics(c.SCENARIOS[0], d, c.run_contract("S0", d, 4.67, 6.4, 0.0))
    assert m["fwer"] <= 0.10
    assert m["go"] == 0.0


def test_family_corr_is_portfolio_correlation():
    r = c.family_corr(0.7, 0.3)
    assert abs(r[0, 1] - 0.3 / ((1 + 3 * 0.7) / 4)) < 1e-12


def test_window_sharpe_formula_and_horizon_rules():
    from scripts.research.fx_constraint_frontier import frontier as fr

    w = fr.Window(250, 1, 4.0, 20.0, "x")
    base = fr.window_sharpe(w, 1.0, 0.5, None, 6.0, "flat", 0.2, True)
    assert abs(base - (250**0.5) * (2.0 - 1.0) / 20.0) < 1e-12
    h1 = fr.window_sharpe(w, 1.0, 0.5, 24.0, 6.0, "flat", 0.2, True)
    assert abs(h1 - (200**0.5) * (2.0 - 1.2) / 40.0) < 1e-12
    per = fr.window_sharpe(w, 1.0, 0.5, 24.0, 6.0, "persist", 0.2, True)
    assert abs(per - (200**0.5) * (4.0 - 1.2) / 40.0) < 1e-12


def test_deviation_excludes_sensitivity_points():
    from scripts.research.fx_constraint_frontier import frontier as fr

    assert fr.deviation(fr.Point("E3", "H0", "flat", "median", "current")) is None
    assert fr.deviation(fr.Point("E0", "H0", "flat", "p90", "current")) is None
    assert fr.deviation(fr.Point("E1", "H1", "flat", "median", "paid")) == 5


def test_g4_years_and_inputs_rules():
    from scripts.research.fx_constraint_frontier import frontier as fr

    assert fr.g4_required_years(1.0) == float("inf")
    assert abs(fr.g4_required_years(2.0) - 1 / (0.58 * 0.16)) < 1e-12
    inp = fr.load_inputs()
    # 原則固定の時間帯の外の候補は E0（事前登録 §3）
    for k in ("K3_FOMC", "K3_BOJ", "K4"):
        assert inp["cost"]["E1"][k] == inp["cost"]["E0"][k] == inp["cost"]["E2"][k]
    assert inp["d"]["pub"]["beta"] == [1.2, 2.2]


def test_retained_fast_path_matches_contract():
    from scripts.research.fx_constraint_frontier import frontier as fr

    for name in ("S0", "S3", "S4"):
        d = c.draw(c.SCENARIOS[4], 4.67, 6.4, 1500, np.random.default_rng(3))
        a = fr.retained(name, d, 4.67, 6.4)
        b = c.run_contract(name, d, 4.67, 6.4, 0.0)["retained"]
        assert (a == b).all()
