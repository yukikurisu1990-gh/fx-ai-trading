# ruff: noqa: E501 -- driver prose
"""Stage 0 を 1 回走らせて記録を書く。決定的（seed 固定）。R-A の範囲だけ。

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

止まる条件: 記録が既にある・scripts / tests / docs/governance が dirty・git が失敗する。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any, Final

import numpy as np

from scripts.research.exploratory_m15.bars import PAIRS
from scripts.research.patsd_stage0 import cost, data, ledgers, null_pipeline, prereg

REPO: Final[Path] = Path(__file__).resolve().parents[3]
RECORD: Final[Path] = REPO / "artifacts/research/patsd_stage0/stage0.json"
INJECTION_TARGET: Final[tuple[int, int, int, int, int]] = (0, 0, 1, 1, 0)

_PANEL = None
_BOOK = None


def _git(*args: str) -> str:
    done = subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, check=False)
    if done.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} が失敗した: {done.stderr[:200]}")
    return done.stdout.strip()


def _init(panel, book) -> None:
    global _PANEL, _BOOK
    _PANEL, _BOOK = panel, book


def _job(args: tuple) -> dict:
    rep, injection = args
    return null_pipeline.run_replication(_PANEL, _BOOK, rep, injection)


def _clean(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clean(v) for v in value]
    if isinstance(value, (np.floating, float)):
        return None if not math.isfinite(float(value)) else float(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, np.bool_):
        return bool(value)
    return value


def run(workers: int) -> dict[str, Any]:
    if RECORD.exists():
        raise SystemExit(f"{RECORD} は既にある。上書きしない")
    dirty = _git("status", "--porcelain", "--", "scripts", "tests", "docs/governance").splitlines()
    if dirty:
        raise SystemExit(f"dirty tree では走らせない: {dirty[:5]}")
    identity = {
        "head": _git("rev-parse", "HEAD"),
        "dirty_path_count": 0,
        "freeze_digest": prereg.freeze_digest(),
        "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "authorization": prereg.AUTHORIZATION,
    }

    # S0-1
    per_pair: dict[str, dict] = {}
    input_hashes: dict[str, str] = {}
    h4: dict[str, Any] = {}
    f3: dict[str, dict] = {}
    for pair in PAIRS:
        m15 = data.load_pair(pair)
        input_hashes[pair] = data.content_hash(m15)
        per_pair[pair] = cost.pair_economics(m15)
        f3[pair] = cost.f3_month_end_power(m15)
        h4[pair] = data.aggregate(m15, "H4")
    s0_1 = {"per_pair": per_pair, "summary": cost.summarize(per_pair), "f3_month_end_power": f3}

    # S0-2 / S0-3
    h4_cost = {pair: float(cost.relative_spread(h4[pair]).median()) for pair in PAIRS}
    panel = null_pipeline.build_panel(h4, h4_cost)
    book = null_pipeline.build_trade_book(panel)
    jobs = [(rep, None) for rep in range(prereg.NULL_REPLICATIONS)]
    for s in prereg.INJECTED_TRUE_SHARPES:
        jobs += [
            (10_000 + rep, (s, INJECTION_TARGET)) for rep in range(prereg.INJECTION_REPLICATIONS)
        ]
    with ProcessPoolExecutor(
        max_workers=workers, initializer=_init, initargs=(panel, book)
    ) as pool:
        results = list(pool.map(_job, jobs, chunksize=4))
    null_results = results[: prereg.NULL_REPLICATIONS]
    ladder = prereg.SELECTION["dsr_ladder"]
    null_rates = {
        str(t): {
            "false_pass_rate": float(np.mean([r[str(t)]["any_pass"] for r in null_results])),
            "null_g4_rate": float(np.mean([r[str(t)]["g4"] for r in null_results])),
            "null_g4_point_deflated_rate": float(
                np.mean([r[str(t)]["g4_point_deflated"] for r in null_results])
            ),
            "mean_passers": float(np.mean([r[str(t)]["n_pass"] for r in null_results])),
        }
        for t in ladder
    }
    calibrated = next(
        (
            t
            for t in ladder
            if null_rates[str(t)]["false_pass_rate"] <= prereg.S0_2_BANDS["target_rate"]
        ),
        None,
    )
    if calibrated is None:
        s0_2_label = "RED"
    elif calibrated >= prereg.S0_2_BANDS["green_min_p"]:
        s0_2_label = "GREEN"
    else:
        s0_2_label = "AMBER"
    s0_2 = {
        "replications": prereg.NULL_REPLICATIONS,
        "trials_per_replication": sorted({r["n_trials"] for r in null_results}),
        "effective_trials": {
            "median": float(np.median([r["n_eff"] for r in null_results])),
            "min_max": [
                int(min(r["n_eff"] for r in null_results)),
                int(max(r["n_eff"] for r in null_results)),
            ],
        },
        "best_baseline_sharpe_median": float(np.median([r["best_baseline"] for r in null_results])),
        "by_dsr_threshold": null_rates,
        "calibrated_p": calibrated,
        "classification": s0_2_label,
    }

    injection: dict[str, Any] = {}
    offset = prereg.NULL_REPLICATIONS
    for s in prereg.INJECTED_TRUE_SHARPES:
        block = results[offset : offset + prereg.INJECTION_REPLICATIONS]
        offset += prereg.INJECTION_REPLICATIONS
        injection[str(s)] = {
            str(t): {
                "g4_pass_prob": float(np.mean([r[str(t)]["g4_with_injected"] for r in block])),
                "g4_point_deflated_pass_prob": float(
                    np.mean([r[str(t)]["g4_point_with_injected"] for r in block])
                ),
                "any_pass_rate": float(np.mean([r[str(t)]["any_pass"] for r in block])),
            }
            for t in ladder
        }
    arithmetic = null_pipeline.g4_arithmetic(panel.oof_years)
    if calibrated is None:
        s0_3_value = None
        s0_3_label = "RED"
    else:
        s0_3_value = injection[str(prereg.S0_3_TRUE_SHARPE)][str(calibrated)]["g4_pass_prob"]
        bands = prereg.S0_3_BANDS
        s0_3_label = (
            "GREEN"
            if s0_3_value >= bands["green_min"]
            else "AMBER"
            if s0_3_value >= bands["amber_min"]
            else "RED"
        )
    s0_3 = {
        "arithmetic_pre_deflation": arithmetic,
        "simulated": injection,
        "primary": {
            "true_sharpe": prereg.S0_3_TRUE_SHARPE,
            "at_calibrated_p": calibrated,
            "g4_pass_prob": s0_3_value,
        },
        "classification": s0_3_label,
        "oof_years": round(panel.oof_years, 3),
        "injection_target": list(INJECTION_TARGET),
    }

    s0_4 = ledgers.s0_4()
    s0_5 = ledgers.s0_5()
    labels = {
        "S0-1": s0_1["summary"]["classification"],
        "S0-2": s0_2_label,
        "S0-3": s0_3_label,
        "S0-4": s0_4["classification"],
        "S0-5": s0_5["classification"],
    }
    if "RED" in labels.values():
        overall = "STAGE0_RED_RETURN_TO_HUMAN"
    elif "AMBER" in labels.values():
        overall = "STAGE0_AMBER_PROCEED_REQUIRES_HUMAN_DECISION"
    else:
        overall = "STAGE0_GREEN_B_PRIME_ELIGIBLE_PENDING_R_B1"
    return _clean(
        {
            "cycle": prereg.CYCLE,
            **identity,
            "completed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "input_content_sha256": input_hashes,
            "s0_1": s0_1,
            "s0_2": s0_2,
            "s0_3": s0_3,
            "s0_4": s0_4,
            "s0_5": s0_5,
            "gate_table": labels,
            "overall": overall,
            "success_estimate_label": "MODEL_BASED_PRIOR_SUCCESS_ESTIMATE_VERY_LOW",
        }
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()
    payload = run(args.workers)
    raw = (
        json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=True, allow_nan=False) + "\n"
    ).encode("utf-8")
    RECORD.parent.mkdir(parents=True, exist_ok=True)
    temp = RECORD.with_name(RECORD.name + ".partial")
    temp.write_bytes(raw)
    temp.replace(RECORD)
    print(
        json.dumps(
            {
                "gate_table": payload["gate_table"],
                "overall": payload["overall"],
                "sha256": hashlib.sha256(raw).hexdigest(),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
