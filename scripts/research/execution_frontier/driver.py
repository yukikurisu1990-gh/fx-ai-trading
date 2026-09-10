"""Entry point for Track 3. Emits artifacts; decides nothing.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `PRODUCTION_READINESS_NOT_CLAIMED`.

Usage::

    python -m scripts.research.execution_frontier.driver replay
    python -m scripts.research.execution_frontier.driver frontier
    python -m scripts.research.execution_frontier.driver all

`replay` measures execution on the two deciding panels. `frontier` substitutes
that measurement into the feasibility frontier's own enumeration. Neither reads
a signal, and neither adjudicates anything: the adjudication is a reading of the
artifacts against gates the pre-registration fixed in advance.

There is no stage here that reaches an unseen span, and there cannot be: this
module holds no archive path. It loads the two already-seen deciding panels
through `round_a.panels`, whose loaders carry their own span guards, and it never
touches the fresh pool, the historical OOS slice, the dead window or the forward
epoch.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

from scripts.research.fxunits import verify_unit_consistency
from scripts.research.round_a import DECIDING_PANELS, panels

ARTIFACTS = Path("artifacts/research/execution_frontier")


def _write(name: str, record: dict[str, Any]) -> Path:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    path = ARTIFACTS / name
    path.write_text(json.dumps(record, indent=2, sort_keys=True, default=str), encoding="utf-8")
    return path


def _load() -> dict[str, dict[str, pd.DataFrame]]:
    return {panel: panels.load_panel(panel) for panel in DECIDING_PANELS}


def _spans(loaded: dict[str, dict[str, pd.DataFrame]]) -> dict[str, Any]:
    """The declared span beside the measured one, never the constant alone.

    `bars.load` does not validate the rows it serves, so a panel's declared span
    is an assertion until something counts it. The frontier reports both for the
    same reason and this stage reads the same caches.
    """
    return {
        "declared": {panel: list(panels.panel_span(panel)) for panel in loaded},
        "measured": {
            panel: [
                str(min(frame["ts"].min() for frame in frames.values())),
                str(max(frame["ts"].max() for frame in frames.values())),
            ]
            for panel, frames in loaded.items()
        },
    }


def _finish(name: str, record: dict[str, Any], loaded: dict[str, Any]) -> dict[str, Any]:
    record["panel_spans"] = _spans(loaded)
    record["unit_audit"] = verify_unit_consistency(record["panels"])
    path = _write(name, record)
    print(f"wrote {path}")
    print(json.dumps(record["unit_audit"], indent=2))
    return record


def run_replay(loaded: dict[str, dict[str, pd.DataFrame]] | None = None) -> dict[str, Any]:
    from scripts.research.execution_frontier import replay

    loaded = loaded if loaded is not None else _load()
    return _finish("replay.json", replay.build(loaded), loaded)


def run_frontier(loaded: dict[str, dict[str, pd.DataFrame]] | None = None) -> dict[str, Any]:
    from scripts.research.execution_frontier import refrontier

    loaded = loaded if loaded is not None else _load()
    return _finish("frontier.json", refrontier.build(loaded), loaded)


def run_all() -> dict[str, Any]:
    """Both stages on one load of the panels, which is the expensive part."""
    loaded = _load()
    return {"replay": run_replay(loaded), "frontier": run_frontier(loaded)}


STAGES = {"replay": run_replay, "frontier": run_frontier, "all": run_all}


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] not in STAGES:
        print(f"usage: python -m scripts.research.execution_frontier.driver {{{'|'.join(STAGES)}}}")
        return 2
    STAGES[argv[1]]()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
