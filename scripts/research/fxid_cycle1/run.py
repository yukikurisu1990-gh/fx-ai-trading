# ruff: noqa: E501 -- driver prose
"""FXID Cycle 1 を 1 回走らせて記録する（R-A2 + 統計基盤の技術検証 + 設計の算術）。決定的。

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

止まる条件: 記録が既にある・scripts / tests / docs/governance が dirty・git の失敗。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Final

import numpy as np
import pandas as pd
from scipy.stats import norm

from scripts.research.exploratory_m15.bars import PAIRS
from scripts.research.fxid_cycle1 import clock, maxt, stats
from scripts.research.patsd_stage0 import data as guarded

REPO: Final[Path] = Path(__file__).resolve().parents[3]
RECORD: Final[Path] = REPO / "artifacts/research/fxid_cycle1/cycle1.json"
ROUTE_FILES: Final[tuple[str, ...]] = (
    "scripts/research/exploratory_m15/momentum.py",
    "scripts/research/exploratory_m15/supplemental.py",
    "scripts/research/exploratory_m15/bars.py",
    "scripts/research/exploratory_m15/round2.py",
    "scripts/research/patsd_stage0/data.py",
)
REPS_CAL: Final[int] = 1537
REPS_VER: Final[int] = 1537
REPS_SENS: Final[int] = 500
REPS_POWER: Final[int] = 400


def _git(*args: str) -> str:
    done = subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, check=False)
    if done.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} が失敗した: {done.stderr[:200]}")
    return done.stdout.strip()


def _sha(path: str) -> str:
    return hashlib.sha256((REPO / path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _median(values) -> float | None:
    clean = [v for v in values if v is not None and np.isfinite(v)]
    return round(float(np.median(clean)), 4) if clean else None


def r_a2(frames: dict[str, pd.DataFrame]) -> dict[str, Any]:
    per_pair: dict[str, Any] = {}
    moves: dict[str, dict[str, pd.Series]] = {name: {} for name in clock.ANCHORS}
    blocks: dict[str, pd.Series] = {}
    for pair, frame in frames.items():
        overall = float(frame["spread_rel"].median())
        windows = stats.window_spreads(frame, overall)
        block = stats.block_moves(frame, 4)
        sigma_4h = float(block.std(ddof=1))
        per_pair[pair] = {
            "overall_spread_bp_median": round(overall * 1e4, 3),
            "overall_spread_bp_mean": round(float(frame["spread_rel"].mean()) * 1e4, 3),
            "hourly_ny": stats.hourly_profile(frame),
            "windows": windows,
            "anchor_economics": stats.anchor_economics(frame, windows),
            "ambiguity_upper_bound": stats.ambiguity_upper_bound(frame, sigma_4h),
        }
        for name in clock.ANCHORS:
            moves[name][pair] = stats.anchor_moves(frame, name, 4)
        blocks[pair] = block
    breadth = {name: stats.breadth(moves[name]) for name in clock.ANCHORS}
    breadth["unconditional_4h_blocks"] = stats.breadth(blocks)

    summary: dict[str, Any] = {
        "hourly_ny_median_across_pairs": {},
        "windows": {},
        "anchor_cost_to_sigma_median": {},
        "ambiguity_median": {},
    }
    for hour in range(24):
        summary["hourly_ny_median_across_pairs"][hour] = {
            "spread_bp_mean": _median(
                [p["hourly_ny"].get(hour, {}).get("spread_bp_mean") for p in per_pair.values()]
            ),
            "vol_bp_std": _median(
                [p["hourly_ny"].get(hour, {}).get("vol_bp_std") for p in per_pair.values()]
            ),
        }
    for name in clock.ANCHORS:
        summary["windows"][name] = {
            "spread_bp_mean": _median(
                [p["windows"][name]["spread_bp_mean"] for p in per_pair.values()]
            ),
            "ratio_mean_to_overall_median": _median(
                [p["windows"][name]["ratio_mean_to_overall_median"] for p in per_pair.values()]
            ),
        }
        summary["anchor_cost_to_sigma_median"][name] = {
            str(h): _median(
                [
                    p["anchor_economics"][name].get(str(h), {}).get("cost_to_sigma")
                    for p in per_pair.values()
                ]
            )
            for h in stats.HOLDS_HOURS
        }
    for k in ("w=0.25sigma4h", "w=0.5sigma4h", "w=1.0sigma4h"):
        summary["ambiguity_median"][k] = _median(
            [p["ambiguity_upper_bound"][k]["share_all_bars"] for p in per_pair.values()]
        )
    summary["overall_spread_bp_median_of_pairs"] = _median(
        [p["overall_spread_bp_median"] for p in per_pair.values()]
    )
    summary["overall_spread_bp_mean_of_pairs"] = _median(
        [p["overall_spread_bp_mean"] for p in per_pair.values()]
    )
    return {"per_pair": per_pair, "breadth": breadth, "summary": summary}


def statistics_infrastructure(frames: dict[str, pd.DataFrame]) -> dict[str, Any]:
    cost = {pair: float(frame["spread_rel"].mean()) + 0.5e-4 for pair, frame in frames.items()}
    grid = maxt.build_grid(frames, cost)
    out: dict[str, Any] = {
        "years": round(grid.years, 3),
        "trading_days": grid.n_days,
        "bars": int(grid.returns.shape[0]),
    }
    for n in (10, 20):
        candidates = maxt.make_candidates(grid, n, seed=n)
        cal, cal_first = maxt.run_null(grid, candidates, REPS_CAL, stream=1000 + n)
        ver, _ = maxt.run_null(grid, candidates, REPS_VER, stream=2000 + n)
        result = maxt.calibrate_and_verify(cal, ver)
        single_sd = float(cal_first.std(ddof=1))
        result["single_candidate_null_sd"] = round(single_sd, 4)
        result["analytic_se_1_over_sqrt_years"] = round(1 / math.sqrt(grid.years), 4)
        result["equivalent_independent_trials"] = round(
            maxt.equivalent_trials(result["threshold_sharpe"], single_sd), 2
        )
        result["nominal_trials"] = n
        result["trades_per_candidate_median"] = int(np.median([len(c.t0) for c in candidates]))
        out[f"N={n}"] = result
    # 感度: 正規の合成（pair × NY 時の vol の形と相関だけを seen から）
    n = 20
    candidates = maxt.make_candidates(grid, n, seed=n)
    observed = grid.returns != 0
    corr = np.corrcoef(grid.returns[observed.all(axis=1)].T)
    chol = np.linalg.cholesky(corr + 1e-9 * np.eye(len(corr)))
    hours = pd.Series(grid.ny_minute // 60)
    hour_scale = np.zeros_like(grid.returns)
    for j in range(grid.returns.shape[1]):
        col = pd.Series(grid.returns[:, j]).where(observed[:, j])
        by_hour = col.groupby(hours).std(ddof=1)
        hour_scale[:, j] = hours.map(by_hour).fillna(0.0).to_numpy() * observed[:, j]
    gauss, _ = maxt.run_null(
        grid, candidates, REPS_SENS, stream=3000, kind="gaussian", chol=chol, hour_scale=hour_scale
    )
    threshold_20 = out["N=20"]["threshold_sharpe"]
    out["sensitivity_gaussian_N=20"] = {
        "reps": REPS_SENS,
        "threshold_q90": round(float(np.quantile(gauss, 0.9)), 4),
        "fwer_at_sign_null_threshold": round(float((gauss > threshold_20).mean()), 4),
    }
    out["synthetic_selection_power_N=20"] = {
        str(s): round(
            maxt.selection_power(
                grid, candidates, REPS_POWER, threshold_20, s, stream=int(s * 100)
            ),
            4,
        )
        for s in (0.8, 1.0, 1.3, 1.5)
    }
    out["note"] = (
        "技術検証。ランダムな候補の較正は、S1 / S2 を含む将来の pipeline の FWER を保証しない。閾値は凍結しない"
    )
    return out


def design_arithmetic() -> dict[str, Any]:
    """data 分割の案 × prior の τ × G4-A / G4-B の、最後まで通る確率（仮定した真の Sharpe の下）。"""
    mu = 0.07
    fresh_years = 4.895

    def p_select(years: float, n_eff: int, s: float) -> float:
        se = 1 / math.sqrt(years)
        thr = se * norm.ppf((1 - 0.10) ** (1 / n_eff))
        return float(1 - norm.cdf((thr - s) / se))

    def p_estimate(years: float, tau: float, g4: float, s: float) -> tuple[float, float]:
        se = 1 / math.sqrt(years)
        w = tau**2 / (tau**2 + se**2)
        need = mu + (g4 - mu) / w
        return float(1 - norm.cdf((need - s) / se)), need

    def p_confirm(years: float, s: float) -> float:
        return float(1 - norm.cdf(1.645 - s * math.sqrt(years)))

    splits = {
        "3_block_pre2016_select_10y__seen_estimate_4.68y__fresh": (10.0, 4.68, fresh_years),
        "pre2016_split_select_6y__pre2016_estimate_4y__fresh": (6.0, 4.0, fresh_years),
        "pre2016_split_6y_4y__fresh_kept__forward_3y_confirm": (6.0, 4.0, 3.0),
    }
    out: dict[str, Any] = {}
    for name, (sel, est, conf) in splits.items():
        rows = {}
        for tau in (0.4, 0.565, 0.8):
            for label, g4 in (("G4-A_1.0", 1.0), ("G4-B_0.8", 0.8)):
                cells = {}
                for s in (0.8, 1.0, 1.5):
                    ps = p_select(sel, 20, s)
                    pe, need = p_estimate(est, tau, g4, s)
                    pc = p_confirm(conf, s)
                    cells[str(s)] = round(ps * pe * pc, 4)
                rows[f"tau={tau}|{label}"] = {
                    "overall": cells,
                    "observed_needed_in_estimate_block": round(need, 3),
                }
        out[name] = rows
    return out


def run() -> dict[str, Any]:
    if RECORD.exists():
        raise SystemExit(f"{RECORD} は既にある。上書きしない")
    dirty = _git("status", "--porcelain", "--", "scripts", "tests", "docs/governance").splitlines()
    if dirty:
        raise SystemExit(f"dirty tree では走らせない: {dirty[:5]}")
    identity = {
        "head": _git("rev-parse", "HEAD"),
        "dirty_path_count": 0,
        "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "authorization": "R-A2（2026-10-03 裁定）",
        "route_file_sha256": {p: _sha(p) for p in ROUTE_FILES},
        "code_sha256": {
            str(p.relative_to(REPO)).replace("\\", "/"): _sha(str(p.relative_to(REPO)))
            for p in sorted((REPO / "scripts/research/fxid_cycle1").glob("*.py"))
        },
    }
    frames: dict[str, pd.DataFrame] = {}
    input_hashes: dict[str, str] = {}
    for pair in PAIRS:
        raw = guarded.load_pair(pair)
        input_hashes[pair] = guarded.content_hash(raw)
        frames[pair] = stats.prepare(raw)
    payload = {
        **identity,
        "input_content_sha256": input_hashes,
        "span": [stats.FIRST, stats.LAST],
        "r_a2": r_a2(frames),
        "statistics_infrastructure": statistics_infrastructure(frames),
        "design_arithmetic": design_arithmetic(),
        "completed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    return payload


def _clean(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clean(v) for v in value]
    if isinstance(value, (np.floating, float)):
        return None if not math.isfinite(float(value)) else float(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.bool_):
        return bool(value)
    return value


def main() -> int:
    argparse.ArgumentParser().parse_args()
    payload = _clean(run())
    raw = (
        json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=True, allow_nan=False) + "\n"
    ).encode("utf-8")
    RECORD.parent.mkdir(parents=True, exist_ok=True)
    temp = RECORD.with_name(RECORD.name + ".partial")
    temp.write_bytes(raw)
    temp.replace(RECORD)
    print(json.dumps({"sha256": hashlib.sha256(raw).hexdigest()}), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
