"""Entry point for Track 1. `prereg` reads nothing; `develop` runs the seen-data study.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

    python -m scripts.research.continuous_portfolio.driver prereg
    python -m scripts.research.continuous_portfolio.driver develop
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Final

ARTIFACTS: Final[Path] = Path("artifacts/research/continuous_portfolio")


def _write(name: str, payload: dict[str, Any]) -> Path:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    path = ARTIFACTS / name
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8"
    )
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("prereg", "develop"))
    args = parser.parse_args(argv)
    if args.stage == "prereg":
        from scripts.research.continuous_portfolio import construction
        from scripts.research.continuous_portfolio import prereg as prereg_module

        payload = {
            "classification": "NON_DECISION_BEARING_EXPLORATORY_ONLY",
            "frozen_hash": prereg_module.freeze_hash(),
            "specification": prereg_module.specification(),
            "band_calibration_signal_free": construction.band_calibration(),
        }
        path = _write("prereg.json", payload)
    else:
        from scripts.research.continuous_portfolio import development

        path = _write("development.json", development.run())
    print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
