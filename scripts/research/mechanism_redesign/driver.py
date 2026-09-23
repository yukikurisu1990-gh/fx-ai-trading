# ruff: noqa: E501 -- driver prose
"""凍結した 4 本を凍結順に走らせる。**track の結果を見て次の track を変えない**（裁定 §23）。

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

走る前に `prereg.freeze_digest()` が commit 済みの凍結値と一致することを確かめ、
一致しなければ何も走らせない。出力には HEAD・dirty path・argv・開始時刻を残す。
既存の記録は上書きしない（`write_provenance`）。
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

import numpy as np
import pandas as pd

from scripts.research.acquisition_safety import write_provenance
from scripts.research.mechanism_redesign import execute, inputs, prereg, signals
from scripts.research.top_five import panel

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[3]
RECORD: Final[Path] = REPO_ROOT / "artifacts/research/mechanism_redesign/development.json"
SPANS: Final[tuple[str, ...]] = ("long", "recent")

#: **alpha の前に commit した凍結値。** これと一致しない凍結では走らせない。
FROZEN_DIGEST: Final[str] = "e13998514cbf2c49189ac15d4d7397bb6288c90b22c750e5610e84e9fc029132"


def _usd_corr(left: pd.DataFrame, right: pd.DataFrame) -> tuple[float, int]:
    joined = left.index.intersection(right.index)
    a = left["USD"].reindex(joined)
    b = right["USD"].reindex(joined)
    ok = a.notna() & b.notna()
    if ok.sum() < 60 or a[ok].std() == 0 or b[ok].std() == 0:
        return float("nan"), int(ok.sum())
    return float(abs(np.corrcoef(a[ok], b[ok])[0, 1])), int(ok.sum())


def _xs_corr(left: pd.DataFrame, right: pd.DataFrame) -> tuple[float, int]:
    joined = left.index.intersection(right.index)
    lft, rgt = left.reindex(joined), right.reindex(joined)
    usable = lft.notna() & rgt.notna()
    lc = lft.where(usable).sub(lft.where(usable).mean(axis=1), axis=0)
    rc = rgt.where(usable).sub(rgt.where(usable).mean(axis=1), axis=0)
    per_day = (
        (lc * rc).sum(axis=1)
        / np.sqrt((lc**2).sum(axis=1) * (rc**2).sum(axis=1)).replace(0.0, np.nan)
    ).dropna()
    return (float(abs(per_day.mean())) if len(per_day) else float("nan")), int(len(joined))


def _rename_gates(
    track: str, scores: pd.DataFrame, built: dict[str, Any], span: str
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for gate in prereg.TRACKS[track]["rename_gates"]:
        spec = prereg.RENAME_GATES[gate]
        try:
            if gate == "T5_TIC_FLOW":
                from scripts.research.top_five import signals as previous

                measured, overlap = _usd_corr(scores, previous.t5_scores(scores.index))
            elif gate == "U1_TRADE_BALANCE":
                from scripts.research.next_five import signals as previous

                measured, overlap = _xs_corr(scores, previous.scores_for("U1", built, span))
            elif gate == "M16_WITHIN_CYCLE":
                measured, overlap = _usd_corr(scores, signals.scores_for("M16", built, span))
            elif gate == "M15_WITHIN_CYCLE":
                measured, overlap = _usd_corr(scores, signals.scores_for("M15", built, span))
            elif gate == "M11_WITHIN_CYCLE":
                measured, overlap = _xs_corr(scores, signals.scores_for("M11", built, span))
            elif gate == "CARRY_LEVEL_XS":
                rates = signals.carry_rate_panel(scores.index)
                measured, overlap = _xs_corr(scores, signals._xs_z(rates))
            elif gate == "VOL_RATIO_STATE":
                excess = built[span]["currency_excess_return"]
                ratio = np.log(
                    excess.rolling(20, min_periods=20).std()
                    / excess.rolling(250, min_periods=250).std()
                )
                measured, overlap = _xs_corr(scores, ratio.sub(ratio.mean(axis=1), axis=0))
            else:
                raise KeyError(f"凍結されていない rename gate: {gate}")
        except Exception as error:  # noqa: BLE001 - 比較できないことも記録する
            out[gate] = {
                **spec,
                "verdict": "NOT_EVALUABLE",
                "why": f"{type(error).__name__}: {error}"[:150],
            }
            continue
        if not np.isfinite(measured):
            out[gate] = {
                **spec,
                "verdict": "NOT_EVALUABLE",
                "why": "比較対象が定数か、重なりが 60 日未満",
                "overlap_days": overlap,
            }
            continue
        out[gate] = {
            **spec,
            "measured_abs_correlation": round(measured, 4),
            "overlap_days": overlap,
            "verdict": "RENAME" if measured >= float(spec["threshold"]) else "DISTINCT",
        }
    return out


def _code_identity() -> dict[str, Any]:
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
    """**何も計算しないうちに**止めるべき条件を全部確かめる（Role 2 RF-5 / RF-6）。"""
    if RECORD.exists():
        raise SystemExit(
            f"{RECORD} は既にある。再実行は記録されない alpha を見ることになるので走らせない"
        )
    digest = prereg.freeze_digest()
    if digest != FROZEN_DIGEST:
        raise SystemExit(
            f"凍結 digest が commit 済みの値と違う（{digest} != {FROZEN_DIGEST}）。走らせない"
        )
    identity = _code_identity()
    if identity["dirty_paths"]:
        raise SystemExit(f"dirty tree では走らせない: {identity['dirty_paths'][:5]}")
    inputs.verify()
    return digest, identity


def run(*, workers: int = 1) -> dict[str, Any]:
    digest, identity = preflight()
    built = panel.build()
    results: dict[str, Any] = {}
    pnl: dict[str, pd.Series] = {}
    for track in prereg.EXECUTION_ORDER:
        for span in SPANS:
            key = f"{track}_{span}"
            started = time.monotonic()
            print(f"[{time.strftime('%H:%M:%S')}] {key} 開始", file=sys.stderr, flush=True)
            try:
                out = execute.run_track(track, span, built, workers=workers)
            except Exception as error:  # noqa: BLE001 - 失敗も記録する
                results[key] = {
                    "track": track,
                    "span": span,
                    "error": f"{type(error).__name__}: {error}"[:300],
                }
                print(f"{key} ERROR {error}", file=sys.stderr, flush=True)
                continue
            print(
                f"[{time.strftime('%H:%M:%S')}] {key} 終了 {time.monotonic() - started:.0f}s",
                file=sys.stderr,
                flush=True,
            )
            if "metrics" not in out:
                results[key] = out
                continue
            scores = out.pop("scores")
            pnl[key] = out.pop("daily_net")
            out["rename_gates"] = _rename_gates(track, scores, built, span)
            results[key] = out
            m = out["metrics"]
            print(
                f"{key} gross={m['gross_sharpe']:+.3f} net={m['net_sharpe']:+.3f}",
                file=sys.stderr,
                flush=True,
            )

    verdicts: dict[str, Any] = {}
    for track in prereg.EXECUTION_ORDER:
        primary_span = prereg.TRACKS[track]["primary_span"]
        other_span = "recent" if primary_span == "long" else "long"
        primary = results.get(f"{track}_{primary_span}", {})
        other = results.get(f"{track}_{other_span}")
        if "null_diagnostic" in primary:
            verdicts[track] = execute.verdict(
                track, primary, other, primary.get("rename_gates", {})
            )
        else:
            verdicts[track] = {
                "status": primary.get("verdict", "NOT_RUN"),
                "why": primary.get("why") or primary.get("error"),
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
        "freeze_digest": digest,
        "code_identity": identity,
        "panel": built["provenance"],
        "results": results,
        "verdicts": verdicts,
        "cross_track_correlation": correlation,
        "exploration_disclosure": prereg.EXPLORATION_DISCLOSURE,
        "interpretation": prereg.INTERPRETATION,
        "multiplicity": prereg.NULL_DIAGNOSTIC["multiplicity"],
    }


def main() -> int:
    warnings.filterwarnings("ignore")
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=1)
    args = parser.parse_args()
    payload = run(workers=args.workers)
    RECORD.parent.mkdir(parents=True, exist_ok=True)
    written = write_provenance(RECORD, payload)
    print(
        json.dumps({k: v.get("status") for k, v in payload["verdicts"].items()}, ensure_ascii=False)
    )
    print(f"written: {RECORD} sha256={written}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
