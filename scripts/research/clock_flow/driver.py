"""Entry point for Track 1's stages. Emits artifacts; decides nothing.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `PRODUCTION_READINESS_NOT_CLAIMED`.

Usage::

    python -m scripts.research.clock_flow.driver frontier

`frontier` is the unit audit and the feasibility measurement. It uses no signal:
portfolio directions are drawn from a generator, so there is no signal-to-return
relation for it to find, and the numbers it reports are properties of the design.
It is the stage that must pass before a hypothesis stage may be pre-registered.

There is no stage here that reads an unseen span, and there cannot be: the module
holds no archive path. It loads the two already-seen deciding panels through
`round_a.panels`, whose loaders carry their own span guards.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from scripts.research.round_a import DECIDING_PANELS, panels

ARTIFACTS = Path("artifacts/research/clock_flow")


def _write(name: str, record: dict[str, Any]) -> Path:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    path = ARTIFACTS / name
    path.write_text(json.dumps(record, indent=2, sort_keys=True, default=str), encoding="utf-8")
    return path


def run_frontier() -> dict[str, Any]:
    """Measure what the two deciding panels can decide, in one unit."""
    from scripts.research.clock_flow import frontier

    loaded = {panel: panels.load_panel(panel) for panel in DECIDING_PANELS}
    record = frontier.build(loaded)
    record["panel_spans"] = {panel: list(panels.panel_span(panel)) for panel in DECIDING_PANELS}
    record["measured_spans"] = {
        panel: [
            str(min(frame["ts"].min() for frame in frames.values())),
            str(max(frame["ts"].max() for frame in frames.values())),
        ]
        for panel, frames in loaded.items()
    }
    path = _write("frontier.json", record)
    print(f"wrote {path}")
    print(json.dumps(record["unit_audit"], indent=2))
    return record


STAGES = {"frontier": run_frontier}


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] not in STAGES:
        print(f"usage: python -m scripts.research.clock_flow.driver {{{'|'.join(STAGES)}}}")
        return 2
    STAGES[argv[1]]()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
