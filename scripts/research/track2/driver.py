"""Entry point for Track 2. Emits artifacts; decides nothing by itself.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `PRODUCTION_READINESS_NOT_CLAIMED`.

Usage::

    python -m scripts.research.track2.driver stage0

`stage0` audits the calendar data and computes no signal and no return. It is the
stage that can stop the Track, and the pre-registration forbids running Stage 1
if it fails.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ARTIFACTS = Path("artifacts/research/track2")
CACHE = Path("artifacts/track_a_scratch/track2/forex_factory_cache.csv")


def _write(name: str, record: dict[str, Any]) -> Path:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    path = ARTIFACTS / name
    path.write_text(json.dumps(record, indent=2, sort_keys=True, default=str), encoding="utf-8")
    return path


def run_stage0() -> dict[str, Any]:
    from scripts.research.track2 import stage0

    record = stage0.build(cache=CACHE)
    path = _write("stage0.json", record)
    print(f"wrote {path}")
    print(json.dumps(record["verdict"], indent=2))
    return record


STAGES = {"stage0": run_stage0}


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] not in STAGES:
        print(f"usage: python -m scripts.research.track2.driver {{{'|'.join(STAGES)}}}")
        return 2
    STAGES[argv[1]]()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
