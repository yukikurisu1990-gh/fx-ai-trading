"""P1 / P2 の fast-track の governance の契約（指示 §29 の 12 項目）。合成と記録だけを使う。"""

from __future__ import annotations

import ast
import hashlib
import json
import math
import pathlib

import numpy as np
import pytest

from scripts.research.fx_system_reopen_feasibility import gates, p1, system_prior
from scripts.research.fx_system_reopen_feasibility import prereg as pr

REPO = pathlib.Path(__file__).resolve().parents[2]
PKG = REPO / "scripts/research/fx_system_reopen_feasibility"
HOLD = REPO / "docs/governance/fxid_long_term_hold_ruling_2026_10.md"
ARCH = REPO / "docs/governance/fx_system_architecture_ruling_2026_10.md"
RESULT = REPO / "artifacts/research/fx_system_reopen_feasibility/p1_result.json"


# 1. authoritative な HOLD は変わっていない
def test_authoritative_hold_unchanged():
    hold = HOLD.read_text(encoding="utf-8")
    assert "**最終 state: `FXID_LONG_TERM_HOLD_NO_JUSTIFIED_ALPHA_CYCLE`**" in hold
    assert gates.AUTHORITATIVE_STATE == "FXID_LONG_TERM_HOLD_NO_JUSTIFIED_ALPHA_CYCLE"
    arch = ARCH.read_text(encoding="utf-8")
    assert "**`FXID_LONG_TERM_HOLD_NO_JUSTIFIED_ALPHA_CYCLE` は解除しない**" in arch
    assert "ARCH-C — COMPOSITION_DOES_NOT_SOLVE_THE_FUNDAMENTAL_LIMITATION" in arch


# 2・3. 例外は P1 / P2 だけ。P3 以降は未承認
def test_exception_scope_is_p1_p2_only():
    assert frozenset({"P1", "P2"}) == gates.EXCEPTION_SCOPE
    for phase in ("P3", "P4", "P5", "P6"):
        assert not gates.phase_allowed(phase)
        assert phase in gates.UNAPPROVED_PHASES
    arch = ARCH.read_text(encoding="utf-8")
    assert "**P3 以降には及ばない**" in arch


# 4・5・6. fresh・broker・価格の系列の読み取りの禁止（import と呼び出しの検査）
ALLOWED_IMPORTS = {
    "__future__",
    "dataclasses",
    "hashlib",
    "itertools",
    "json",
    "math",
    "subprocess",
    "sys",
    "time",
    "pathlib",
    "typing",
    "numpy",
    "scripts.research.fx_system_reopen_feasibility",
}


@pytest.mark.parametrize("path", sorted(PKG.glob("*.py")), ids=lambda p: p.name)
def test_package_imports_no_data_broker_or_protected_reader(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
    imported |= {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    assert imported <= ALLOWED_IMPORTS, imported - ALLOWED_IMPORTS
    calls = {ast.unparse(n.func) for n in ast.walk(tree) if isinstance(n, ast.Call)}
    forbidden_calls = (
        "read_parquet",
        "read_csv",
        "load_pair",
        "requests",
        "urlopen",
        "oanda",
        "np.load",
        "fromfile",
        "__import__",
        "importlib",
        "pickle",
    )
    for forbidden in forbidden_calls:
        assert not any(forbidden in c for c in calls), (path.name, forbidden)
    assert "open" not in calls, path.name
    for fn in (n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)):
        body = ast.unparse(fn)
        if "read_bytes" in body or "read_text" in body:
            assert fn.name == "_sha", (path.name, fn.name)
        if "subprocess.run" in body:
            assert fn.name == "_git", (path.name, fn.name)
            assert "['git', *args]" in body, (path.name, fn.name)


# 7. G4 は system 単位の 1.0
def test_g4_is_system_level_one():
    assert gates.G4_SYSTEM_SHARPE == 1.0
    assert pr.TARGET == 1.0


# 8. component の prior で system の prior を緩められない（2 次の moment と tail、ρ > 0 を含む）
def test_component_priors_cannot_loosen_system_prior():
    tau = 0.4
    for k, rho in ((10, 0.0), (10, 0.3), (5, 0.0)):
        with pytest.raises(ValueError):
            system_prior.assert_not_loosened(tau, tau, k=k, rho=rho)
        tc = system_prior.calibrated_component_tau(tau, k, rho)
        assert math.isclose(system_prior.implied_system_prior_scale(tc, k, rho), tau)
        system_prior.assert_not_loosened(tc, tau, k, rho)


def test_second_moment_uses_trace_of_inverse_correlation():
    k, rho = 10, 0.3
    trace = 1 / (1 + (k - 1) * rho) + (k - 1) / (1 - rho)
    r = np.full((k, k), rho)
    np.fill_diagonal(r, 1.0)
    assert math.isclose(system_prior.second_moment_factor(r), trace, rel_tol=1e-9)
    assert trace > k


@pytest.mark.parametrize("rho", [0.0, 0.3])
def test_implied_scale_matches_simulation_including_correlated_case(rho):
    rng = np.random.default_rng(1)
    tau, k = 0.4, 10
    r = np.full((k, k), rho)
    np.fill_diagonal(r, 1.0)
    s = rng.normal(0, tau, size=(40000, k))
    q = np.einsum("ij,ij->i", s, np.linalg.solve(r, s.T).T)
    rms = math.sqrt(float(q.mean()))
    assert abs(rms - system_prior.implied_system_prior_scale(tau, k, rho)) / rms < 0.02


def test_tail_of_calibrated_prior_does_not_exceed_g4_tail():
    for k, rho in ((10, 0.0), (10, 0.3)):
        tc = system_prior.calibrated_component_tau(0.4, k, rho)
        assert system_prior.implied_tail(tc, k, rho) <= system_prior.g4_tail(0.4)


def test_single_component_sign_choice_doubles_the_tail():
    # k = 1 でも、符号を data で選ぶと tail は G4 の 2 倍になり、拒否される
    with pytest.raises(ValueError):
        system_prior.assert_not_loosened(0.4, 0.4, k=1)


# 9. P2 は P1 が PASS の場合だけ
def test_p2_only_after_p1_pass():
    assert gates.p2_allowed("PASS")
    for v in ("AMBER", "STOP", "pass", ""):
        assert not gates.p2_allowed(v)


# 10. G は事前の基準で H を上回る時だけ
def _res(fwer, upper, power, dof):
    return gates.PipelineResult(fwer, upper, power, dof)


def test_g_only_when_it_beats_h_on_preregistered_criterion():
    c = gates.GCriterion()
    h = _res(0.09, 0.10, {"a": 0.3, "b": 0.3}, 10)
    assert gates.choose_architecture(h, _res(0.09, 0.10, {"a": 0.5, "b": 0.5}, 12), c) == "G"
    assert gates.choose_architecture(h, _res(0.09, 0.12, {"a": 0.9, "b": 0.9}, 12), c) == "H"
    assert gates.choose_architecture(h, _res(0.09, 0.10, {"a": 0.5, "b": 0.3}, 12), c) == "G"
    assert gates.choose_architecture(h, _res(0.09, 0.10, {"a": 0.35, "b": 0.35}, 12), c) == "H"
    assert gates.choose_architecture(h, _res(0.09, 0.10, {"a": 0.5, "b": 0.5}, 100), c) == "H"
    assert gates.choose_architecture(h, _res(0.09, 0.10, {"a": 0.5, "c": 0.9}, 12), c) == "H"
    assert gates.choose_architecture(h, _res(0.09, 0.10, {"a": 0.9, "b": 0.1}, 12), c) == "H"
    h2 = _res(0.05, 0.07, {"a": 0.3, "b": 0.3}, 10)
    assert gates.choose_architecture(h2, _res(0.08, 0.095, {"a": 0.6, "b": 0.6}, 12), c) == "H"


# 11. 結果に依存した候補の拡大の禁止（universe の固定と、事前登録の hash の一致）
def test_candidate_universe_is_fixed_and_preregistered():
    assert len(pr.FAMILIES) == 15
    eligible = [k for k, v in pr.FAMILIES.items() if v[2].startswith("ELIGIBLE")]
    assert eligible == ["F1_dollar_intraday_W_fixing_inventory"]
    assert pr.WINDOWS == ("EUR_morning_0200_0815", "JPY_post_tokyo_fix", "EUR_post_ECB_0815_1700")
    assert RESULT.exists()
    rec = json.loads(RESULT.read_text(encoding="utf-8"))
    for path, sha in rec["preregistration_sha256"].items():
        raw = (REPO / path).read_bytes().replace(b"\r\n", b"\n")
        assert hashlib.sha256(raw).hexdigest() == sha, path
    eur, jpy, ecb = pr.WINDOWS[0], pr.WINDOWS[1], pr.WINDOWS[2]
    expected = {
        "P1-O": {eur: 0.74, jpy: 0.85, ecb: 0.25},
        "P1-B": {eur: 0.28, jpy: 0.0, ecb: 0.0},
        "P1-S": {eur: 0.064, jpy: 0.0, ecb: 0.0},
    }
    assert {k: v["sharpe"] for k, v in pr.SCENARIOS.items()} == expected
    assert rec["verdict"]["p1_verdict"] == "STOP"
    assert rec["p2_executed"] is False


# 12. REOPEN の提案は実行の許可ではない
def test_reopen_proposal_is_not_execution_permission():
    assert gates.REOPEN_PROPOSAL_GRANTS_EXECUTION is False
    assert "**REOPEN の提案（`FXID_REOPEN_REVIEW_PROPOSAL`）は、実行の許可ではない**" in (
        ARCH.read_text(encoding="utf-8")
    )


# 算術の部品
def test_long_only_bound_and_hedge_arithmetic():
    r = p1.corr_matrix(2, 0.5)
    s = np.array([0.75, 0.0])
    assert math.isclose(p1.max_sharpe_unconstrained(s, r), 0.75 / math.sqrt(0.75), rel_tol=1e-9)
    lo, support = p1.max_sharpe_long_only(s, r)
    assert math.isclose(lo, 0.75) and support == [0]
    s2 = np.array([0.5, 0.5])
    assert math.isclose(p1.max_sharpe_long_only(s2, p1.corr_matrix(2, 0.0))[0], math.sqrt(0.5))


def test_final_classification():
    assert gates.final_classification("STOP", None).startswith("FAST-A")
    assert gates.final_classification("AMBER", None).startswith("FAST-A")
    assert gates.final_classification("PASS", False).startswith("FAST-B")
    assert gates.final_classification("PASS", True).startswith("FAST-C")
