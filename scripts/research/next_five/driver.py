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
import sys
import warnings
from pathlib import Path
from typing import Any, Final

import numpy as np
import pandas as pd

from scripts.research.acquisition_safety import write_provenance
from scripts.research.next_five import execute, prereg, signals
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


def run(*, permutation_draws: int | None = None) -> dict[str, Any]:
    built = panel.build()
    results: dict[str, Any] = {}
    pnl: dict[str, pd.Series] = {}

    for track in prereg.EXECUTION_ORDER:
        for span in SPANS:
            key = f"{track}_{span}"
            try:
                out = execute.run_track(track, span, built, permutation_draws=permutation_draws)
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
            gate = out.get("advance_gate") or {}
            print(
                f"{key:16s} gross={metrics['gross_sharpe']:+.3f} net={metrics['net_sharpe']:+.3f} "
                f"turnover={metrics['turnover_per_unit_gross']:6.1f} "
                f"incIC={metrics['incremental_ic']:+.4f} "
                f"p={gate.get('p_value', float('nan'))}",
                file=sys.stderr,
            )

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
        "authority": prereg.AUTHORITY,
        "panel": built["provenance"],
        "results": results,
        "cross_track_correlation": correlation,
        "exploration_disclosure": prereg.EXPLORATION_DISCLOSURE,
        "interpretation": prereg.INTERPRETATION,
        "multiplicity": prereg.ADVANCE_GATE["multiplicity"],
    }


def main() -> int:
    warnings.filterwarnings("ignore")
    parser = argparse.ArgumentParser(description="次の 5 本を凍結順に走らせる")
    parser.add_argument("--draws", type=int, default=None)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    payload = run(permutation_draws=args.draws)
    RECORD.parent.mkdir(parents=True, exist_ok=True)
    written = write_provenance(
        RECORD,
        payload,
        overwrite=args.overwrite,
        env_name=OVERWRITE_ENV if args.overwrite else None,
    )
    print(
        json.dumps(
            {k: v.get("verdict", "RAN") for k, v in payload["results"].items()}, ensure_ascii=False
        )
    )
    print(f"written: {RECORD} sha256={written}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
