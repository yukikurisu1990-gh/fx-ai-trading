"""FXID_REOPEN_FOR_COMPONENT_DISCOVERY の契約（D0 の固定・D2 の算術・data を読まないこと）。"""

from __future__ import annotations

import ast
import inspect
import json
import math
import pathlib

from scripts.research.fx_component_discovery import d2_desk

REPO = pathlib.Path(__file__).resolve().parents[2]
GOV = REPO / "docs/governance/fxid_limited_reopen_component_discovery_2026_10.md"
HOLD = REPO / "docs/governance/fxid_long_term_hold_ruling_2026_10.md"
RECORD = REPO / "artifacts/research/fx_component_discovery/d2_desk.json"


def test_hold_ruling_untouched_and_reopen_is_limited():
    assert "**最終 state: `FXID_LONG_TERM_HOLD_NO_JUSTIFIED_ALPHA_CYCLE`**" in HOLD.read_text(
        encoding="utf-8"
    )
    gov = GOV.read_text(encoding="utf-8")
    assert "**`NEW_COMPONENT_DISCOVERY` だけ**" in gov
    assert "**自動的に HOLD に戻る**" in gov
    assert "**fresh `2016-06-02 … 2021-04-25`** | **読まない**" in gov


def test_desk_module_reads_only_the_committed_cost_record():
    tree = ast.parse(inspect.getsource(d2_desk))
    imported = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
    imported |= {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    assert imported <= {"__future__", "hashlib", "json", "math", "sys", "pathlib", "typing"}
    assert d2_desk.COST_RECORD.name == "cycle1_run2.json"


def test_scenarios_follow_d0_prereg():
    assert d2_desk.DECAY == {"Optimistic": 0.0, "Base": 0.5, "Stress": 0.7}
    assert d2_desk.COST_MULT == {"Optimistic": 1.0, "Base": 1.0, "Stress": 1.5}
    assert math.isclose(d2_desk.Z_REQUIRED, 2.4865, abs_tol=1e-3)


def test_recorded_result_kills_the_only_family_at_k8():
    rec = json.loads(RECORD.read_text(encoding="utf-8"))
    fam = rec["family_CB_ANNOUNCEMENT_DAY_UNCERTAINTY_PREMIUM"]
    assert all(v["K8"] for v in fam.values())
    assert rec == d2_desk.compute()
