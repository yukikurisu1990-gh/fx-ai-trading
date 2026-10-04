# ruff: noqa: E501 -- driver prose
"""R-A2b を 1 回走らせて記録する（事前登録 `docs/research/fxid_ny_followup_preregistration_2026_10.md`）。決定的。

`POST_HOC_EXPLORATORY_FOLLOW_UP` · `NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

止まる条件: 記録が既にある・scripts / tests / docs が dirty・事前登録が未 commit か sha256 が違う・git の失敗。
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

from scripts.research.exploratory_m15.bars import PAIRS
from scripts.research.fxid_cycle1 import stats
from scripts.research.fxid_ny_followup import economics
from scripts.research.patsd_stage0 import data as guarded

REPO: Final[Path] = Path(__file__).resolve().parents[3]
RECORD: Final[Path] = REPO / "artifacts/research/fxid_ny_followup/r_a2b.json"
PREREG: Final[str] = "docs/research/fxid_ny_followup_preregistration_2026_10.md"
#: 事前登録の commit 時の sha256（LF に正規化）。違えば走らない
PREREG_SHA256: Final[str] = "5973babf6f5e9f6ef6ed0a05958833f5f6b64198de2c4b4bd745a63af8ea95b4"
ROUTE_FILES: Final[tuple[str, ...]] = (
    "scripts/research/exploratory_m15/momentum.py",
    "scripts/research/exploratory_m15/supplemental.py",
    "scripts/research/exploratory_m15/bars.py",
    "scripts/research/exploratory_m15/round2.py",
    "scripts/research/patsd_stage0/data.py",
)


def _git(*args: str) -> str:
    done = subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, check=False)
    if done.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} が失敗した: {done.stderr[:200]}")
    return done.stdout.strip()


def _sha(path: str) -> str:
    return hashlib.sha256((REPO / path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def run() -> dict[str, Any]:
    if RECORD.exists():
        raise SystemExit(f"{RECORD} は既にある。上書きしない")
    dirty = _git("status", "--porcelain", "--", "scripts", "tests", "docs").splitlines()
    if dirty:
        raise SystemExit(f"dirty tree では走らせない: {dirty[:5]}")
    if not _git("ls-files", PREREG):
        raise SystemExit("事前登録が commit されていない")
    if _sha(PREREG) != PREREG_SHA256:
        raise SystemExit("事前登録の sha256 が pin と違う")
    identity = {
        "head": _git("rev-parse", "HEAD"),
        "dirty_path_count": 0,
        "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "authorization": "R-A2b NY_ENTRY_TIME_SIGNAL_FREE_ECONOMICS（2026-10-05 裁定）",
        "label": "POST_HOC_EXPLORATORY_FOLLOW_UP",
        "preregistration": {"path": PREREG, "sha256": PREREG_SHA256},
        "route_file_sha256": {p: _sha(p) for p in ROUTE_FILES},
        "code_sha256": {
            str(p.relative_to(REPO)).replace("\\", "/"): _sha(str(p.relative_to(REPO)))
            for p in sorted((REPO / "scripts/research/fxid_ny_followup").glob("*.py"))
            + [
                REPO / "scripts/research/fxid_cycle1/stats.py",
                REPO / "scripts/research/fxid_cycle1/clock.py",
            ]
        },
    }
    frames: dict[str, pd.DataFrame] = {}
    input_hashes: dict[str, str] = {}
    spans: dict[str, list[str]] = {}
    for pair in PAIRS:
        raw = guarded.load_pair(pair)
        input_hashes[pair] = guarded.content_hash(raw)
        frame = stats.prepare(raw)
        spans[pair] = [str(frame["ts"].min()), str(frame["ts"].max())]
        frames[pair] = frame
    return {
        **identity,
        "input_content_sha256": input_hashes,
        "span": [stats.FIRST, stats.LAST],
        "observed_bar_span_by_pair": spans,
        "r_a2b": economics.evaluate(frames),
        "completed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


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
