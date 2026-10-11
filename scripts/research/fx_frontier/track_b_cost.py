# ruff: noqa: E501 -- research prose
"""Track B — EXECUTION_COST_FRONTIER（F0 §8）。seen の M15 bid / ask の spread だけを測る（target の return は計算しない）。

読むもの: `scripts.research.patsd_stage0.data.load_pair`（承認済みの route、2021-04-26 … 2025-12-28、fresh の guard 付き）。
使う列: bid / ask の終値と始値（spread の snapshot）、ts。mid の変化・return は計算しない。

all-in の往復（推定）= entry の spread / 2 + exit の spread / 2 + slippage 0.5 bp。同じ時間帯での entry と exit なら、spread + 0.5 bp。
実約定の data は無いので、slippage は推定である。
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Final

import numpy as np
import pandas as pd

from scripts.research.exploratory_m15.bars import PAIRS
from scripts.research.patsd_stage0 import data as guarded

REPO: Final[Path] = Path(__file__).resolve().parents[3]
RECORD: Final[Path] = REPO / "artifacts/research/fx_frontier/track_b_cost.json"
NY: Final[str] = "America/New_York"
SLIPPAGE_BP: Final[float] = 0.5
#: NY 現地時刻の時間帯（bar の終わりの時刻、分で [start, end)）
BUCKETS: Final[dict[str, list[tuple[int, int]]]] = {
    "tokyo_1900_0200": [(19 * 60, 24 * 60), (0, 2 * 60)],
    "pre_london_0200_0300": [(2 * 60, 3 * 60)],
    "london_open_0300_0400": [(3 * 60, 4 * 60)],
    "london_morning_0400_0800": [(4 * 60, 8 * 60)],
    "ny08_0800_0900": [(8 * 60, 9 * 60)],
    "ny09_0900_1000": [(9 * 60, 10 * 60)],
    "ny10_1000_1045": [(10 * 60, 10 * 60 + 45)],
    "london_fix_1045_1115": [(10 * 60 + 45, 11 * 60 + 15)],
    "ny_afternoon_1115_1600": [(11 * 60 + 15, 16 * 60)],
    "pre_rollover_1600_1700": [(16 * 60, 17 * 60)],
    "post_rollover_1700_1900": [(17 * 60, 19 * 60)],
}
#: 定時の発表の slot（bar の始まりが 08:30 か 10:00 ET の平日）。実際の発表の有無は見ない
EVENT_STARTS: Final[tuple[int, ...]] = (8 * 60 + 30, 10 * 60)


def _git(*args: str) -> str:
    done = subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, check=False)
    if done.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} が失敗した")
    return done.stdout.strip()


def spreads(frame: pd.DataFrame) -> pd.DataFrame:
    """bar ごとの spread（bp）と、NY 現地時刻の属性。return は計算しない。"""
    mid_c = (frame["ask_c"] + frame["bid_c"]) / 2
    mid_o = (frame["ask_o"] + frame["bid_o"]) / 2
    end = pd.to_datetime(frame["ts"], utc=True) + pd.Timedelta(minutes=15)
    start_ny = pd.to_datetime(frame["ts"], utc=True).dt.tz_convert(NY)
    end_ny = end.dt.tz_convert(NY)
    out = pd.DataFrame(
        {
            "spread_close_bp": (frame["ask_c"] - frame["bid_c"]) / mid_c * 1e4,
            "spread_open_bp": (frame["ask_o"] - frame["bid_o"]) / mid_o * 1e4,
            "end_minute": end_ny.dt.hour * 60 + end_ny.dt.minute,
            "start_minute": start_ny.dt.hour * 60 + start_ny.dt.minute,
            "weekday": start_ny.dt.dayofweek,
            "dst": start_ny.map(lambda t: bool(t.dst())),
        }
    )
    return out[out["weekday"] < 5]


def _bucket_mask(s: pd.DataFrame, name: str) -> pd.Series:
    m = pd.Series(False, index=s.index)
    for lo, hi in BUCKETS[name]:
        m |= (s["end_minute"] >= lo) & (s["end_minute"] < hi)
    return m


def _stats(x: pd.Series) -> dict[str, Any]:
    x = x.dropna()
    if len(x) == 0:
        return {"n": 0}
    q = np.quantile(x, [0.25, 0.5, 0.75, 0.9])
    return {
        "n": int(len(x)),
        "p25": round(float(q[0]), 3),
        "median": round(float(q[1]), 3),
        "p75": round(float(q[2]), 3),
        "p90": round(float(q[3]), 3),
        "mean": round(float(x.mean()), 3),
        "all_in_rt_median_bp_est": round(float(q[1]) + SLIPPAGE_BP, 3),
        "share_all_in_le_1bp": round(float((x + SLIPPAGE_BP <= 1.0).mean()), 4),
    }


def classify_1bp(share: float) -> str:
    if share >= 0.5:
        return "CONTINUOUS"
    if share >= 0.05:
        return "PARTIAL"
    if share > 0:
        return "MOMENTARY"
    return "NEVER"


def pair_frontier(s: pd.DataFrame) -> dict[str, Any]:
    out: dict[str, Any] = {"buckets": {}, "dst": {}, "weekday": {}, "event_slot": {}}
    for name in BUCKETS:
        st = _stats(s.loc[_bucket_mask(s, name), "spread_close_bp"])
        st["le_1bp_class"] = classify_1bp(st.get("share_all_in_le_1bp", 0.0))
        out["buckets"][name] = st
    for flag, label in ((True, "summer"), (False, "winter")):
        out["dst"][label] = _stats(s.loc[s["dst"] == flag, "spread_close_bp"])
    for d in range(5):
        out["weekday"][str(d)] = _stats(s.loc[s["weekday"] == d, "spread_close_bp"])
    ev = s["start_minute"].isin(EVENT_STARTS)
    out["event_slot"]["scheduled_release_slot"] = _stats(s.loc[ev, "spread_close_bp"])
    out["event_slot"]["other"] = _stats(s.loc[~ev, "spread_close_bp"])
    out["overall"] = _stats(s["spread_close_bp"])
    return out


def run() -> dict[str, Any]:
    if RECORD.exists():
        raise SystemExit(f"{RECORD} は既にある。上書きしない")
    dirty = _git("status", "--porcelain", "--", "scripts", "tests", "docs").splitlines()
    if dirty:
        raise SystemExit(f"dirty tree では走らせない: {dirty[:5]}")
    started = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    pairs: dict[str, Any] = {}
    hashes: dict[str, str] = {}
    for pair in PAIRS:
        raw = guarded.load_pair(pair)
        hashes[pair] = guarded.content_hash(raw)
        pairs[pair] = pair_frontier(spreads(raw))
    best = sorted(
        (
            (v["buckets"][b]["median"], p, b)
            for p, v in pairs.items()
            for b in BUCKETS
            if v["buckets"][b].get("n", 0) > 0
        )
    )[:10]
    return {
        "head": _git("rev-parse", "HEAD"),
        "dirty_path_count": 0,
        "command": "python -X utf8 -m scripts.research.fx_frontier.track_b_cost",
        "started_utc": started,
        "completed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "span": [str(guarded.FIRST), str(guarded.LAST)],
        "input_content_sha256": hashes,
        "code_sha256": hashlib.sha256(
            Path(__file__).read_bytes().replace(b"\r\n", b"\n")
        ).hexdigest(),
        "slippage_bp_assumption": SLIPPAGE_BP,
        "pairs": pairs,
        "lowest_median_spread_pair_buckets": [
            {"median_bp": m, "pair": p, "bucket": b} for m, p, b in best
        ],
    }


def main() -> int:
    payload = run()
    raw = (json.dumps(payload, ensure_ascii=False, indent=1) + "\n").encode("utf-8")
    RECORD.parent.mkdir(parents=True, exist_ok=True)
    RECORD.write_bytes(raw)
    print(hashlib.sha256(raw).hexdigest())
    return 0


if __name__ == "__main__":
    sys.exit(main())
