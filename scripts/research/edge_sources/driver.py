"""Write the reframing record. Reads no market data.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

    python -m scripts.research.edge_sources.driver
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, Final

from scripts.research.edge_sources import TARGET_NET_RETURN, WORKFLOW_STATUS, candidates, capacity

ROOT: Final[Path] = Path(__file__).resolve().parents[3]
ARTIFACTS: Final[Path] = ROOT / "artifacts/research/edge_sources"


def build() -> dict[str, Any]:
    return {
        "classification": "NON_DECISION_BEARING_EXPLORATORY_ONLY",
        "workflow_status": WORKFLOW_STATUS,
        "market": "G10 FX spot",
        "target_net_return": TARGET_NET_RETURN,
        "market_data_read": False,
        "capacity": {
            "calibration_from_track_1_record": capacity.calibration_from_record(ROOT),
            "continuous_book": capacity.continuous_book_table(),
            "return_and_leverage": capacity.return_and_leverage_table(),
            "event_book": capacity.event_book_table(),
            "sample_years_needed_one_sided_5pct": {
                f"power_{p:g}": {
                    f"{s:g}": capacity.sample_years_needed(s, p)
                    for s in capacity.NET_SHARPE_SCENARIOS
                }
                for p in (0.5, 0.8)
            },
        },
        "evidence_map": [asdict(e) for e in candidates.EVIDENCE_MAP],
        "candidates": [{**asdict(c), "score": candidates.score(c)} for c in candidates.CANDIDATES],
        "ranking": candidates.ranking(),
        "weights": {"gains": candidates.GAIN_WEIGHTS, "burdens": candidates.BURDEN_WEIGHTS},
        "distinct_directions": candidates.distinct_directions(),
        "proposed_tracks": [
            {"track": name, "candidates": list(members)}
            for name, members in candidates.PROPOSED_TRACKS
        ],
    }


def main() -> int:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    path = ARTIFACTS / "reframing.json"
    path.write_text(
        json.dumps(build(), indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
