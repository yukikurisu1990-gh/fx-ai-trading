# ruff: noqa: E501 -- driver prose
"""5 本を凍結順に走らせ、1 つの artefact にまとめる（2026-09-22 裁定 §K / §L）。

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

**途中が negative でも止めない。** 5 本は既に凍結済みなので、途中結果を理由に
cycle を止めることはしない。止まるのは `SHARED_BLOCKERS` だけである。

**data が無い track は `DATA_UNAVAILABLE_WITH_CURRENT_FREE_SOURCES` として記録する。**
「到達できなかった」と「存在しない」を混同しない。
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
from scripts.research.next_five import corrections, execute, prereg, series_map, signals
from scripts.research.top_five import panel

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[3]
RECORD: Final[Path] = REPO_ROOT / "artifacts/research/next_five/development.json"
OVERWRITE_ENV: Final[str] = "NEXT_FIVE_OVERWRITE"

SPANS: Final[tuple[str, ...]] = ("long", "recent")


def _rename_gate(
    track: str, scores: pd.DataFrame, built: dict[str, Any], span: str
) -> dict[str, Any]:
    """凍結した rename gate（`prereg.RENAME_GATES`）。**閾値は事前に決めてある。**"""
    candidate = prereg.TRACKS[track]["candidate"]
    spec = prereg.RENAME_GATES.get(candidate)
    if spec is None:
        return {}

    comparator = None
    try:
        if candidate == "S07":
            from scripts.research.top_five import signals as previous

            comparator = previous.t1_scores(scores.index, span)
        elif candidate == "S31":
            from scripts.research.top_five import signals as previous

            comparator = previous.t5_scores(scores.index)
        elif candidate == "S25":
            comparator = signals.scores_for("U4", built, span)
    except Exception as error:  # noqa: BLE001 - 比較できないことも記録する
        return {
            **spec,
            "verdict": "COMPARATOR_UNAVAILABLE",
            "why": f"{type(error).__name__}: {error}"[:150],
        }

    if comparator is None or comparator.empty:
        return {**spec, "verdict": "COMPARATOR_UNAVAILABLE"}

    joined_index = scores.index.intersection(comparator.index)
    if len(joined_index) < 60:
        return {**spec, "verdict": "COMPARATOR_TOO_SHORT", "overlap_days": int(len(joined_index))}

    left = scores.reindex(joined_index)
    right = comparator.reindex(joined_index)
    usable = left.notna() & right.notna()
    left_c = left.where(usable).sub(left.where(usable).mean(axis=1), axis=0)
    right_c = right.where(usable).sub(right.where(usable).mean(axis=1), axis=0)
    numerator = (left_c * right_c).sum(axis=1)
    denominator = np.sqrt((left_c**2).sum(axis=1) * (right_c**2).sum(axis=1))
    per_day = (numerator / denominator.replace(0.0, np.nan)).dropna()
    if per_day.empty:
        return {**spec, "verdict": "COMPARATOR_UNAVAILABLE"}

    measured = float(abs(per_day.mean()))
    exceeded = measured >= float(spec["threshold"])
    return {
        **spec,
        "measured_abs_correlation": round(measured, 4),
        "overlap_days": int(len(joined_index)),
        "verdict": "RENAME" if exceeded else "DISTINCT",
    }


def _code_identity() -> dict[str, Any]:
    """**どのコードで走ったか**（Role 2 R-4）。dirty tree から走らせたら、それも記録する。"""

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


def run(*, permutation_draws: int | None = None, workers: int = 1) -> dict[str, Any]:
    built = panel.build()
    results: dict[str, Any] = {}
    pnl: dict[str, pd.Series] = {}

    for track in prereg.EXECUTION_ORDER:
        for span in SPANS:
            key = f"{track}_{span}"
            try:
                started = time.monotonic()
                print(f"[{time.strftime('%H:%M:%S')}] {key} 開始", file=sys.stderr, flush=True)
                out = execute.run_track(
                    track, span, built, permutation_draws=permutation_draws, workers=workers
                )
                print(
                    f"[{time.strftime('%H:%M:%S')}] {key} 終了 {time.monotonic() - started:.0f}s",
                    file=sys.stderr,
                    flush=True,
                )
            except Exception as error:  # noqa: BLE001 - 失敗も記録する
                results[key] = {
                    "track": track,
                    "span": span,
                    "error": f"{type(error).__name__}: {error}"[:300],
                }
                print(f"{key:16s} ERROR {error}", file=sys.stderr)
                continue

            if "metrics" not in out:
                results[key] = out
                print(f"{key:16s} {out.get('verdict')}", file=sys.stderr)
                continue

            scores = out.pop("scores")
            pnl[key] = out.pop("daily_net")
            out["rename_gate"] = _rename_gate(track, scores, built, span)
            out["distinct_signal_states"] = int(pd.unique(scores.round(6).to_numpy().ravel()).size)
            results[key] = out

            metrics = out["metrics"]
            gate = out.get("null_diagnostic") or {}
            print(
                f"{key:16s} gross={metrics['gross_sharpe']:+.3f} net={metrics['net_sharpe']:+.3f} "
                f"turnover={metrics['turnover_per_unit_gross']:6.1f} "
                f"incIC={metrics['incremental_ic']:+.4f} "
                f"p={gate.get('p_value', float('nan'))}",
                file=sys.stderr,
            )

    #: **判定は 2 つの span が揃ってから当てる**（E9 の replication 診断のため）。
    verdicts: dict[str, Any] = {}
    for track in prereg.EXECUTION_ORDER:
        primary_span = prereg.TRACKS[track]["primary_span"]
        other_span = "recent" if primary_span == "long" else "long"
        primary = results.get(f"{track}_{primary_span}", {})
        other = results.get(f"{track}_{other_span}")
        if "null_diagnostic" in primary:
            verdicts[track] = execute.verdict(track, primary, other, primary.get("rename_gate"))
        else:
            verdicts[track] = {
                "status": primary.get("verdict", "NOT_RUN"),
                "failure_class": "DATA_FAILURE" if "verdict" in primary else None,
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
        "freeze_digest": prereg.freeze_digest(),
        "corrections_digest": corrections.corrections_digest(),
        "post_alpha_corrections": corrections.POST_ALPHA_CORRECTIONS,
        "invalidated_records": corrections.INVALIDATED_RECORDS,
        "disclosures": corrections.DISCLOSURES,
        "revision_caveats": {
            track: sorted({row["revision"] for row in series_map.SERIES_MAP[track].values()})
            for track in series_map.SERIES_MAP
        },
        "code_identity": _code_identity(),
        "authority": prereg.AUTHORITY,
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
    parser = argparse.ArgumentParser(description="次の 5 本を凍結順に走らせる")
    parser.add_argument("--draws", type=int, default=None)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument(
        "--out",
        default=None,
        help="出力先。**コミット済みの前回記録を上書きしないために** 別ファイルへ書ける",
    )
    args = parser.parse_args()

    payload = run(permutation_draws=args.draws, workers=args.workers)
    record = Path(args.out) if args.out else RECORD
    record.parent.mkdir(parents=True, exist_ok=True)
    written = write_provenance(
        record,
        payload,
        overwrite=args.overwrite,
        env_name=OVERWRITE_ENV if args.overwrite else None,
    )
    print(
        json.dumps(
            {k: v.get("verdict", "RAN") for k, v in payload["results"].items()}, ensure_ascii=False
        )
    )
    print(f"written: {record} sha256={written}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
