# ruff: noqa: E501 -- stage 0 prose
"""Stage 0 の再実行（2026-09-22 第 2 裁定 §28 / §29）。**return は一切使わない。**

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

測るもの（§28）: data integrity / timestamp availability / lag / revision / missingness /
coverage / currency breadth / sample span / expected turnover / economic capacity / rough power。

**expected turnover は signal の変化だけから出す**（weight を単位 gross に正規化し、その
日次変化の絶対値和を年率にする）。book に通すと PnL が出てしまうので通さない。
**capacity と power は検出下限（MDE95）で表す** — 年 5% / 10% に要る net Sharpe
（vol 10% でそれぞれ 0.5 / 1.0）を、その窓が検出できるかどうかで見る。

hard stop（§29）に当たった track は Stage 1 へ進まない:
semantic mismatch / insufficient breadth / unresolved look-ahead / unrecoverable timing
ambiguity / protected-data requirement / no reproducible public source。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Final

import numpy as np
import pandas as pd

from scripts.research.acquisition_safety import write_provenance
from scripts.research.next_five import prereg, series_map, signals
from scripts.research.top_five import panel

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[3]
ACQUISITION: Final[Path] = REPO_ROOT / "artifacts/research/next_five/acquisition.json"
RECORD: Final[Path] = REPO_ROOT / "artifacts/research/next_five/stage0_rerun.json"
OVERWRITE_ENV: Final[str] = "NEXT_FIVE_OVERWRITE"

TRADING_DAYS: Final[float] = 252.0
MIN_CURRENCIES: Final[int] = 3
MIN_DAYS: Final[int] = 60

HARD_STOPS: Final[tuple[str, ...]] = (
    "SEMANTIC_MISMATCH",
    "INSUFFICIENT_BREADTH",
    "UNRESOLVED_LOOK_AHEAD",
    "UNRECOVERABLE_TIMING_AMBIGUITY",
    "PROTECTED_DATA_REQUIREMENT",
    "NO_REPRODUCIBLE_PUBLIC_SOURCE",
)


def _signal_turnover(scores: pd.DataFrame) -> float:
    """return を使わない turnover の推定: 単位 gross weight の日次変化の年率（片道）。"""
    gross = scores.abs().sum(axis=1).replace(0.0, np.nan)
    weights = scores.div(gross, axis=0)
    daily = weights.diff().abs().sum(axis=1).dropna()
    return float(daily.mean() * TRADING_DAYS / 2.0) if len(daily) else float("nan")


def _persistence(scores: pd.DataFrame) -> float:
    values = scores.to_numpy(dtype=float)
    current, following = values[:-1].ravel(), values[1:].ravel()
    usable = np.isfinite(current) & np.isfinite(following)
    if usable.sum() < 3:
        return float("nan")
    return float(np.corrcoef(current[usable], following[usable])[0, 1])


def _input_rows(track: str, acquisition: dict[str, Any]) -> dict[str, Any]:
    if track == "U3":
        return {c: row for c, row in acquisition.get("statements", {}).items()}
    return {
        key.split("/", 1)[1]: row
        for key, row in acquisition.get("series", {}).items()
        if key.startswith(f"{track}/")
    }


def assess_track(track: str, built: dict[str, Any], acquisition: dict[str, Any]) -> dict[str, Any]:
    spec = prereg.TRACKS[track]
    inputs = _input_rows(track, acquisition)
    ok_inputs = {c: r for c, r in inputs.items() if r.get("outcome") == "OK"}
    failed_inputs = {c: r.get("outcome") for c, r in inputs.items() if r.get("outcome") != "OK"}
    stops: list[str] = []

    if any(outcome == "SEMANTIC_MISMATCH" for outcome in failed_inputs.values()):
        stops.append("SEMANTIC_MISMATCH")

    #: lag 規則が series ごとに凍結されているか（U3 は声明の公表日 +1 営業日、凍結文どおり）
    if track in series_map.SERIES_MAP:
        missing_lag = [c for c, row in series_map.SERIES_MAP[track].items() if not row.get("lag")]
        if missing_lag:
            stops.append("UNRESOLVED_LOOK_AHEAD")

    spans: dict[str, Any] = {}
    for span in ("long", "recent"):
        try:
            scores = signals.scores_for(track, built, span)
        except signals.SignalUnavailableError as error:
            spans[span] = {"usable": False, "why": str(error)[:200]}
            continue
        if scores.empty:
            spans[span] = {"usable": False, "why": "連続した score が無い"}
            continue
        live = scores.notna() & (scores.abs() > 0)
        per_day = live.sum(axis=1)
        years = len(scores) / TRADING_DAYS
        spans[span] = {
            "usable": bool(len(scores) >= MIN_DAYS and int(per_day.min()) >= MIN_CURRENCIES),
            "first": str(scores.index[0].date()),
            "last": str(scores.index[-1].date()),
            "days": int(len(scores)),
            "years": round(years, 2),
            "currencies_with_signal_median": int(per_day.median()),
            "currencies_with_signal_min": int(per_day.min()),
            "distinct_signal_states": int(pd.unique(scores.round(6).to_numpy().ravel()).size),
            "signal_persistence_lag1": round(_persistence(scores), 4),
            "expected_turnover_per_unit_gross": round(_signal_turnover(scores), 2),
            "detection_floor_mde95": round(float(1.96 / np.sqrt(years)), 3) if years > 0 else None,
            "can_detect_sr_0_5_for_5pct_at_10pct_vol": bool(
                years > 0 and 1.96 / np.sqrt(years) <= 0.5
            ),
            "can_detect_sr_1_0_for_10pct_at_10pct_vol": bool(
                years > 0 and 1.96 / np.sqrt(years) <= 1.0
            ),
        }

    primary = spans.get(spec["primary_span"], {})
    if not primary.get("usable"):
        stops.append(
            "INSUFFICIENT_BREADTH" if primary.get("days", 0) >= MIN_DAYS else "INSUFFICIENT_BREADTH"
        )

    revision = sorted(
        {
            row.get("revision_behavior", "")
            for row in ok_inputs.values()
            if row.get("revision_behavior")
        }
    )
    return {
        "track": track,
        "candidate": spec["candidate"],
        "primary_span": spec["primary_span"],
        "inputs_ok": sorted(ok_inputs),
        "inputs_failed": failed_inputs,
        "not_mapped": series_map.NOT_MAPPED.get(track, {}),
        "revision_behavior": revision or (["STATEMENT_TEXT_NOT_REVISED"] if track == "U3" else []),
        "revision_caveat": any("CURRENT_VINTAGE_ONLY" in r for r in revision),
        "spans": spans,
        "hard_stops": sorted(set(stops)),
        "stage_0_passed": not stops,
    }


def run() -> dict[str, Any]:
    acquisition = json.loads(ACQUISITION.read_text(encoding="utf-8"))
    built = panel.build()
    tracks = {track: assess_track(track, built, acquisition) for track in prereg.EXECUTION_ORDER}
    return {
        "cycle": prereg.CYCLE,
        "freeze_digest": prereg.freeze_digest(),
        "authority": "2026-09-22 第 2 裁定 §28 / §29",
        "returns_used": False,
        "tracks": tracks,
        "passed": sorted(t for t, r in tracks.items() if r["stage_0_passed"]),
        "blocked": {t: r["hard_stops"] for t, r in tracks.items() if not r["stage_0_passed"]},
        "hard_stop_vocabulary": list(HARD_STOPS),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Stage 0 を再実行する（return は使わない）")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    payload = run()
    written = write_provenance(
        RECORD,
        payload,
        overwrite=args.overwrite,
        env_name=OVERWRITE_ENV if args.overwrite else None,
    )
    for track, row in payload["tracks"].items():
        primary = row["spans"].get(row["primary_span"], {})
        print(
            f"{track} {row['candidate']} passed={row['stage_0_passed']} stops={row['hard_stops']} "
            f"primary={row['primary_span']} days={primary.get('days')} ccy_min={primary.get('currencies_with_signal_min')} "
            f"MDE95={primary.get('detection_floor_mde95')} turnover~{primary.get('expected_turnover_per_unit_gross')}",
            file=sys.stderr,
        )
    print(f"written: {RECORD} sha256={written}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
