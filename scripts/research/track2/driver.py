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
    """Write the artifact, and put it through the unit audit first.

    Every other recent Track does this and Track 2's first version did not, so
    two artifacts carried a hundred and forty-nine numbers nothing had checked
    the units of.
    """
    from scripts.research.fxunits import verify_unit_consistency

    record["unit_audit"] = verify_unit_consistency(
        {key: value for key, value in record.items() if key != "unit_audit"}
    )
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


def run_stage1() -> dict[str, Any]:
    """Only after Stage 0 has passed, which this checks rather than assumes."""
    from scripts.research.round_a import DECIDING_PANELS, panels
    from scripts.research.track2 import stage0, stage1

    audit_path = ARTIFACTS / "stage0.json"
    if not audit_path.is_file():
        raise RuntimeError("Stage 0 has not been run; the pre-registration runs it first")
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    if not audit["verdict"]["pass"]:
        raise RuntimeError(
            "Stage 0 did not pass, and the pre-registration forbids running Stage 1: "
            f"{audit['verdict']['status']}"
        )
    #: The correction comes from the artifact Stage 0 validated, so the two
    #: stages cannot use different constants. Restating it here is how they
    #: diverged the first time.
    offset_hours = int(audit["date_fidelity"]["offset_hours_applied"])
    archive, _ = stage0.acquire_archive(CACHE)
    loaded = {panel: panels.load_panel(panel) for panel in DECIDING_PANELS}
    record = stage1.build(stage0.in_panels(archive), loaded, offset_hours=offset_hours)
    record["stage0_verdict"] = audit["verdict"]
    path = _write("stage1.json", record)
    print(f"wrote {path}")
    print(json.dumps(record["verdict"], indent=2))
    return record


STAGES = {"stage0": run_stage0, "stage1": run_stage1}


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] not in STAGES:
        print(f"usage: python -m scripts.research.track2.driver {{{'|'.join(STAGES)}}}")
        return 2
    STAGES[argv[1]]()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
