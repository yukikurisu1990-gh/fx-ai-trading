"""Entry point for the feasibility package. Emits artifacts; decides nothing.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `PRODUCTION_READINESS_NOT_CLAIMED`.

Usage::

    python -m scripts.research.feasibility.driver inventory

`inventory` runs the Pass-Region Preflight over every catalogued research
direction. It reads no price, computes no return, and cannot: the whole package
imports nothing that opens a market-data file.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ARTIFACTS = Path("artifacts/research/feasibility")


def _write(name: str, record: dict[str, Any]) -> Path:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    path = ARTIFACTS / name
    path.write_text(json.dumps(record, indent=2, sort_keys=True, default=str), encoding="utf-8")
    return path


def run_inventory() -> dict[str, Any]:
    from scripts.research.feasibility import inventory

    record = inventory.build()
    path = _write("inventory.json", record)
    print(f"wrote {path}")
    print(json.dumps({"status": record["status"], "by_verdict": record["by_verdict"]}, indent=2))
    return record


STAGES = {"inventory": run_inventory}


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] not in STAGES:
        print(f"usage: python -m scripts.research.feasibility.driver {{{'|'.join(STAGES)}}}")
        return 2
    STAGES[argv[1]]()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
