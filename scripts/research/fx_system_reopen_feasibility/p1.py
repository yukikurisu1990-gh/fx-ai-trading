# ruff: noqa: E501 -- research prose
"""P1 — COMPONENT_SUPPLY_AND_SYSTEM_UPPER_BOUND の計算（事前登録 `prereg.py` を読むだけ。価格 data を読まない）。

止まる条件: 記録が既にある・scripts / tests / docs が dirty・git の失敗。
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Final

import numpy as np

from scripts.research.fx_system_reopen_feasibility import gates
from scripts.research.fx_system_reopen_feasibility import prereg as pr

REPO: Final[Path] = Path(__file__).resolve().parents[3]
RECORD: Final[Path] = REPO / "artifacts/research/fx_system_reopen_feasibility/p1_result.json"
PREREG_FILES: Final[tuple[str, ...]] = (
    "scripts/research/fx_system_reopen_feasibility/prereg.py",
    "docs/research/fx_system_p1_prereg_2026_10.md",
)
#: 3 つの窓の時刻（ET、当日決済）。JPY の窓は東京の仲値（冬 19:55、夏 20:55 ET）→ 02:00 ET（同じ取引日の中）
WINDOW_TIMES_ET: Final[dict[str, tuple[str, str]]] = {
    "EUR_morning_0200_0815": ("02:00", "08:15"),
    "EUR_post_ECB_0815_1700": ("08:15", "16:45"),
    "JPY_post_tokyo_fix": ("19:55/20:55", "02:00(+1 暦日、同じ取引日)"),
}


def _sha(path: str) -> str:
    return hashlib.sha256((REPO / path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _git(*args: str) -> str:
    done = subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, check=False)
    if done.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} が失敗した: {done.stderr[:200]}")
    return done.stdout.strip()


def corr_matrix(n: int, rho: float) -> np.ndarray:
    r = np.full((n, n), rho)
    np.fill_diagonal(r, 1.0)
    return r


def max_sharpe_unconstrained(s: np.ndarray, r: np.ndarray) -> float:
    return float(math.sqrt(max(float(s @ np.linalg.solve(r, s)), 0.0)))


def max_sharpe_long_only(s: np.ndarray, r: np.ndarray) -> tuple[float, list[int]]:
    """重み ≥ 0 の最大の Sharpe（小さい n なので部分集合を全て調べる）。"""
    best, best_set = 0.0, []
    idx = range(len(s))
    for size in range(1, len(s) + 1):
        for sub in itertools.combinations(idx, size):
            ss = s[list(sub)]
            rr = r[np.ix_(sub, sub)]
            w = np.linalg.solve(rr, ss)
            if np.all(w >= -1e-12):
                val = math.sqrt(max(float(ss @ w), 0.0))
                if val > best + 1e-12:
                    best, best_set = val, list(sub)
    return best, best_set


def scenario_sharpes(name: str) -> np.ndarray:
    sc = pr.SCENARIOS[name]
    s = np.array([float(sc["sharpe"][w]) for w in pr.WINDOWS])  # type: ignore[index]
    mult = float(sc["cost_multiplier"])  # type: ignore[arg-type]
    if mult != 1.0:
        drag = np.array(
            [
                (mult - 1.0) * pr.COST_OVER_SIGMA[w] * math.sqrt(pr.TRADES_PER_YEAR)
                for w in pr.WINDOWS
            ]
        )
        s = s - drag
    return s


def evaluate_scenario(name: str) -> dict[str, Any]:
    sc = pr.SCENARIOS[name]
    s = scenario_sharpes(name)
    rho = float(sc["rho_within_family"])  # type: ignore[arg-type]
    r = corr_matrix(len(s), rho)
    unc = max_sharpe_unconstrained(s, r)
    lo, lo_set = max_sharpe_long_only(s, r)
    # 1 つの component を除いた時の long only の上限（1 つの component への依存の確認）
    leave_one_out = {}
    for i, w in enumerate(pr.WINDOWS):
        keep = [j for j in range(len(s)) if j != i]
        v, _ = max_sharpe_long_only(s[keep], r[np.ix_(keep, keep)])
        leave_one_out[w] = round(v, 4)
    stale = sc["stale_flags"]  # type: ignore[assignment]
    non_stale = [j for j, w in enumerate(pr.WINDOWS) if not stale[w]]  # type: ignore[index]
    non_stale_bound = (
        max_sharpe_long_only(s[non_stale], r[np.ix_(non_stale, non_stale)])[0] if non_stale else 0.0
    )
    sens = {}
    for rho_s in pr.SENSITIVITY_RHO:
        rs = corr_matrix(len(s), rho_s)
        sens[f"rho={rho_s}"] = {
            "unconstrained": round(max_sharpe_unconstrained(s, rs), 4),
            "long_only": round(max_sharpe_long_only(s, rs)[0], 4),
        }
    positive_windows = [w for w, v in zip(pr.WINDOWS, s, strict=True) if v > 0]
    return {
        "label": sc["label"],
        "window_sharpe_after_cost_stress": {
            w: round(float(v), 4) for w, v in zip(pr.WINDOWS, s, strict=True)
        },
        "rho_within_family": rho,
        "unconstrained_any_sign": round(unc, 4),
        "long_only": round(lo, 4),
        "long_only_support": [pr.WINDOWS[i] for i in lo_set],
        "leave_one_out_long_only": leave_one_out,
        "bound_without_stale_components": round(non_stale_bound, 4),
        "currency_exposure_constrained": round(
            lo, 4
        ),  # 窓は時間が重ならない（WINDOW_TIMES_ET）ので同じ
        "same_day_constrained": round(lo, 4),  # overnight の family は全て LOCKED
        "positive_windows": positive_windows,
        "distinct_families_with_positive_contribution": 1 if positive_windows else 0,
        "family_concentration_constrained_feasible": False,  # 1 family では 1 family ≤ 50% の risk の system を組めない
        "sensitivity_not_for_verdict": sens,
    }


def verdict(results: dict[str, dict[str, Any]]) -> dict[str, Any]:
    b, o = results["P1-B"], results["P1-O"]
    base_bound = b["long_only"]
    cond1 = base_bound >= pr.TARGET
    cond2 = (
        cond1
        and min(b["leave_one_out_long_only"].values()) >= pr.TARGET
        and b["bound_without_stale_components"] >= pr.TARGET
    )
    cond3 = b["distinct_families_with_positive_contribution"] >= 2
    # 規則 (4) の実装（実行の前に定義）: Base の効果に cost の倍率 1.5 を掛けた後の long only の上限 ≥ 1.0
    s_b = np.array([float(pr.SCENARIOS["P1-B"]["sharpe"][w]) for w in pr.WINDOWS])  # type: ignore[index]
    drag = np.array(
        [0.5 * pr.COST_OVER_SIGMA[w] * math.sqrt(pr.TRADES_PER_YEAR) for w in pr.WINDOWS]
    )
    rb = corr_matrix(len(s_b), float(pr.SCENARIOS["P1-B"]["rho_within_family"]))  # type: ignore[arg-type]
    base_cost_stress = max_sharpe_long_only(s_b - drag, rb)[0]
    cond4 = base_cost_stress >= pr.TARGET
    if cond1 and cond2 and cond3 and cond4:
        v = "PASS"
    elif o["long_only"] >= pr.TARGET and not cond1:
        # Optimistic で ≥ 1.0 でも、古い 1 つの推定だけに依存するなら STOP（指示 §13）
        v = (
            "STOP"
            if o["bound_without_stale_components"] < pr.TARGET
            or min(o["leave_one_out_long_only"].values()) < pr.TARGET
            else "AMBER"
        )
    else:
        v = "STOP"
    return {
        "p1_verdict": v,
        "conditions": {
            "1_base_bound_ge_1": cond1,
            "2_not_single_stale_or_extreme": cond2,
            "3_two_distinct_families": cond3,
            "4_room_after_cost_stress": cond4,
        },
        "base_long_only_after_cost_x1_5": round(base_cost_stress, 4),
        "optimistic_long_only": o["long_only"],
        "optimistic_without_stale": o["bound_without_stale_components"],
        "optimistic_leave_one_out_min": min(o["leave_one_out_long_only"].values()),
        "stop_state": pr.STOP_STATE if v == "STOP" else None,
        "p2_allowed": gates.p2_allowed(v),
        "final_classification": gates.final_classification(v, None),
    }


def run() -> dict[str, Any]:
    if RECORD.exists():
        raise SystemExit(f"{RECORD} は既にある。上書きしない")
    dirty = _git("status", "--porcelain", "--", "scripts", "tests", "docs").splitlines()
    if dirty:
        raise SystemExit(f"dirty tree では走らせない: {dirty[:5]}")
    results = {name: evaluate_scenario(name) for name in pr.SCENARIOS}
    b_lo = results["P1-B"]["long_only"]
    unlocked = math.sqrt(b_lo**2 + sum(v**2 for v in pr.STATUS_UNLOCKED_REFERENCE.values()))
    return {
        "head": _git("rev-parse", "HEAD"),
        "dirty_path_count": len(dirty),
        "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "authorization": "Human + ChatGPT 2026-10-08 の P1 / 条件付き P2 に限った一度限りの HOLD の例外",
        "preregistration_sha256": {p: _sha(p) for p in PREREG_FILES},
        "code_sha256": {
            str(p.relative_to(REPO)).replace("\\", "/"): _sha(str(p.relative_to(REPO)))
            for p in sorted((REPO / "scripts/research/fx_system_reopen_feasibility").glob("*.py"))
        },
        "families": {
            k: {"previous_status": v[0], "reason": v[1], "p1_treatment": v[2]}
            for k, v in pr.FAMILIES.items()
        },
        "window_times_et": WINDOW_TIMES_ET,
        "scenarios": results,
        "status_unlocked_reference_not_for_verdict": {
            "components": pr.STATUS_UNLOCKED_REFERENCE,
            "base_plus_unlocked_rho0": round(unlocked, 4),
            "note": "当日決済に反し、閉じた family を含む。判定に使わない",
        },
        "verdict": verdict(results),
        "p2_executed": False,
    }


def main() -> int:
    payload = run()
    raw = (json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=True) + "\n").encode("utf-8")
    RECORD.parent.mkdir(parents=True, exist_ok=True)
    RECORD.write_bytes(raw)
    print(
        json.dumps(
            {
                "sha256": hashlib.sha256(raw).hexdigest(),
                "verdict": payload["verdict"]["p1_verdict"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
