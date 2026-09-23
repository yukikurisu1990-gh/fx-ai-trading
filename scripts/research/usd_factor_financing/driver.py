# ruff: noqa: E501 -- driver prose
"""M15 と M16 の修正版を**同じ修正で 1 回だけ、両方**走らせる（第 3 裁定 §20–§21）。

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE` ·
`POST_RESULT_IMPLEMENTATION_CORRECTED_EXPLORATORY_ONLY`.

計算の前に止まる条件: 記録か開始記録が既にある・凍結 digest が違う・scripts / tests が dirty・
入力が manifest と一致しない。開始記録は計算の前に書く。
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import warnings
from pathlib import Path
from typing import Any, Final

import pandas as pd

from scripts.research.acquisition_safety import write_provenance
from scripts.research.mechanism_redesign import driver as _md
from scripts.research.mechanism_redesign import inputs, signals
from scripts.research.top_five import panel
from scripts.research.usd_factor_financing import execute, prereg

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[3]
RECORD: Final[Path] = REPO_ROOT / "artifacts/research/usd_factor_financing/development.json"
STARTED: Final[Path] = (
    REPO_ROOT / "artifacts/research/usd_factor_financing/development_started.json"
)

FROZEN_DIGEST: Final[str] = "3ceb6ca52c82f4693efee5c2a936d7346df97d87d4dae99112fd7b52f4ad0865"


def _rename_gates(
    track: str, scores: pd.DataFrame, built: dict[str, Any], span: str
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    threshold = float(prereg.RENAME_GATES["threshold"])
    for gate in prereg.RENAME_GATES[track]["gates"]:
        try:
            if gate == "T5_TIC_FLOW":
                from scripts.research.top_five import signals as previous

                measured, overlap = _md._usd_corr(scores, previous.t5_scores(scores.index))
            else:
                other = "M16" if gate == "M16_WITHIN_CYCLE" else "M15"
                measured, overlap = _md._usd_corr(scores, signals.scores_for(other, built, span))
        except Exception as error:  # noqa: BLE001
            out[gate] = {
                "verdict": "NOT_EVALUABLE",
                "why": f"{type(error).__name__}: {error}"[:150],
            }
            continue
        if measured != measured:  # NaN
            out[gate] = {"verdict": "NOT_EVALUABLE", "overlap_days": overlap}
            continue
        out[gate] = {
            "measured_abs_correlation": round(measured, 4),
            "overlap_days": overlap,
            "threshold": threshold,
            "verdict": "RENAME" if measured >= threshold else "DISTINCT",
        }
    return out


def _identity() -> dict[str, Any]:
    def _git(*args: str) -> str:
        return subprocess.run(
            ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, check=False
        ).stdout.strip()

    return {
        "head": _git("rev-parse", "HEAD"),
        "dirty_paths": _git("status", "--porcelain", "--", "scripts", "tests").splitlines(),
        "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "argv": list(sys.argv),
    }


def preflight() -> tuple[str, dict[str, Any]]:
    for path in (RECORD, STARTED):
        if path.exists():
            raise SystemExit(f"{path} は既にある。1 回だけの実行なので走らせない")
    digest = prereg.freeze_digest()
    if digest != FROZEN_DIGEST:
        raise SystemExit(f"凍結 digest が違う（{digest} != {FROZEN_DIGEST}）")
    identity = _identity()
    if identity["dirty_paths"]:
        raise SystemExit(f"dirty tree では走らせない: {identity['dirty_paths'][:5]}")
    inputs.verify()
    return digest, identity


def run(*, workers: int = 1) -> dict[str, Any]:
    digest, identity = preflight()
    STARTED.parent.mkdir(parents=True, exist_ok=True)
    write_provenance(
        STARTED, {"freeze_digest": digest, "code_identity": identity, "status": "STARTED"}
    )
    built = panel.build()
    results: dict[str, Any] = {}
    pnl: dict[str, pd.Series] = {}
    for track in prereg.EXECUTION_ORDER:
        for span in prereg.SPANS:
            key = f"{track}_{span}"
            print(f"[{time.strftime('%H:%M:%S')}] {key} 開始", file=sys.stderr, flush=True)
            #: 例外は捕まえない（Role 2 O-5）: 片方だけの結果で 1 回きりの実行を消費しない。
            #: 落ちたら記録は書かれず、開始記録が残るので再実行は Human + ChatGPT の判断になる
            out = execute.run_track(track, span, built, workers=workers)
            scores = out.pop("scores")
            pnl[key] = out.pop("daily_net_total_central")
            out["rename_gates"] = _rename_gates(track, scores, built, span)
            results[key] = out
            print(f"[{time.strftime('%H:%M:%S')}] {key} 終了", file=sys.stderr, flush=True)
    verdicts = {
        track: execute.verdict(
            results[f"{track}_{prereg.PRIMARY_SPAN}"],
            results[f"{track}_{prereg.PRIMARY_SPAN}"].get("rename_gates", {}),
        )
        if "null_diagnostic" in results.get(f"{track}_{prereg.PRIMARY_SPAN}", {})
        else {
            "status": "NOT_RUN",
            "why": results.get(f"{track}_{prereg.PRIMARY_SPAN}", {}).get("error"),
        }
        for track in prereg.EXECUTION_ORDER
    }
    correlation = {}
    keys = sorted(pnl)
    for i, a in enumerate(keys):
        for b in keys[i + 1 :]:
            joined = pd.concat([pnl[a].rename("a"), pnl[b].rename("b")], axis=1).dropna()
            if len(joined) > 100:
                correlation[f"{a}|{b}"] = round(float(joined["a"].corr(joined["b"])), 3)
    return {
        "cycle": prereg.CYCLE,
        "qualifier": prereg.QUALIFIER,
        "freeze_digest": digest,
        "code_identity": identity,
        "panel": built["provenance"],
        "results": results,
        "verdicts": verdicts,
        "cross_track_correlation": correlation,
    }


def main() -> int:
    warnings.filterwarnings("ignore")
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=1)
    args = parser.parse_args()
    payload = run(workers=args.workers)
    written = write_provenance(RECORD, payload)
    print(
        json.dumps({k: v.get("status") for k, v in payload["verdicts"].items()}, ensure_ascii=False)
    )
    print(f"written: {RECORD} sha256={written}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
