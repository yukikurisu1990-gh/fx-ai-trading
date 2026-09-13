"""Entry point for Track 1. `prereg` reads nothing; `develop` runs the seen-data study.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

    python -m scripts.research.continuous_portfolio.driver prereg
    python -m scripts.research.continuous_portfolio.driver develop
"""

from __future__ import annotations

import argparse
import json
import subprocess
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
            "band_calibration_signal_free_capped_weights": construction.band_calibration(
                weight_cap=prereg_module.PRIMARY.weight_cap
            ),
        }
        path = _write("prereg.json", payload)
    else:
        from scripts.research.continuous_portfolio import development
        from scripts.research.continuous_portfolio import prereg as prereg_module

        if (ARTIFACTS / "development.json").exists():
            raise SystemExit("development.json exists: the pre-registered run happens once")
        checkout = _checkout(
            (
                *prereg_module.HASHED_SOURCES,
                "scripts/research/continuous_portfolio/prereg.py",
                "scripts/research/continuous_portfolio/driver.py",
            )
        )
        if checkout["hashed_sources_modified"]:
            raise SystemExit(f"hashed sources differ from HEAD: {checkout}")
        record = development.run()
        record["checkout"] = checkout
        path = _write("development.json", record)
    print(f"wrote {path}")
    return 0


def _checkout(paths: tuple[str, ...]) -> dict[str, Any]:
    """The commit the run executed, and whether any hashed source differs from it."""
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()
    status = subprocess.run(
        ["git", "status", "--porcelain", "--", *paths], capture_output=True, text=True, check=True
    ).stdout
    return {"head": head, "hashed_sources_modified": [line for line in status.splitlines()]}


if __name__ == "__main__":
    sys.exit(main())
