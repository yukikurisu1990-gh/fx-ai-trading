"""Entry point: write the redesign artefacts. Reads no market data.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

    python -m scripts.research.profit_architecture.driver redesign
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Final

from scripts.research.profit_architecture import (
    MEASURED_ANNUAL_VOL_PER_GROSS_BP,
    STATUS,
    candidates,
    cost_audit,
    mechanics,
)

ARTIFACTS: Final[Path] = Path("artifacts/research/profit_architecture")


def build() -> dict[str, Any]:
    assessed = candidates.assess_all()
    return {
        "classification": "NON_DECISION_BEARING_EXPLORATORY_ONLY",
        "classification_secondary": "RESEARCH_SCRATCH_NON_AUTHORITATIVE",
        "status": STATUS,
        "vol_per_gross_bp": MEASURED_ANNUAL_VOL_PER_GROSS_BP,
        "cost_decomposition": cost_audit.decomposition(),
        "prediction_vs_turnover": cost_audit.prediction_vs_turnover(),
        "gate_audit": cost_audit.gate_audit(),
        "turnover_law": mechanics.turnover_law_table(),
        "no_trade_band": mechanics.no_trade_band_table(),
        "multi_horizon_turnover": {
            f"fast_share_{share:g}": mechanics.multi_horizon_turnover(fast_share=share)
            for share in (0.0, 0.2, 0.3, 0.5, 1.0)
        },
        "pair_routing": mechanics.pair_routing_audit(),
        "capacity": mechanics.capacity_table(),
        "confirmation_power": mechanics.confirmation_power_table(),
        "n_candidates": len(assessed),
        "candidates": assessed,
        "ranking": candidates.ranking(),
        "selected_tracks": candidates.selected_tracks(),
        "score_weights": dict(candidates.SCORE_WEIGHTS),
        "signal_free": True,
        "market_data_read": False,
        "protected_spans_read": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("redesign",))
    parser.parse_args(argv)
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    path = ARTIFACTS / "redesign.json"
    path.write_text(json.dumps(build(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
