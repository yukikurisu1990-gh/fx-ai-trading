"""Entry point for Track 1. `prereg` reads nothing; `develop` runs the seen-data study.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

    python -m scripts.research.continuous_portfolio.driver prereg
    python -m scripts.research.continuous_portfolio.driver develop

`develop` is the pre-registered run and happens once. Before it reads a byte it
compares every hashed source, the pre-registration and this driver with their
content at `HEAD` (so neither a dirty file nor a git index flag can hide an
edit), and writes a start marker. A marker or a finished record already present
refuses the run: a run that failed after the marker is a recorded event, not a
free retry.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Final

ROOT: Final[Path] = Path(__file__).resolve().parents[3]
ARTIFACTS: Final[Path] = ROOT / "artifacts/research/continuous_portfolio"
STARTED: Final[str] = "development.started.json"
FINISHED: Final[str] = "development.json"

RUN_BOUND_SOURCES: Final[tuple[str, ...]] = (
    "scripts/research/continuous_portfolio/prereg.py",
    "scripts/research/continuous_portfolio/driver.py",
)


def _write(name: str, payload: dict[str, Any]) -> Path:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    path = ARTIFACTS / name
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8"
    )
    return path


def _normalised(text: str) -> str:
    return "".join(line + chr(10) for line in text.splitlines())


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(ROOT), *args], capture_output=True, text=True, check=True
    ).stdout


def checkout(paths: tuple[str, ...]) -> dict[str, Any]:
    """The commit the run executes, and every path whose content differs from it."""
    head = _git("rev-parse", "HEAD").strip()
    modified = []
    for relative in paths:
        committed = subprocess.run(
            ["git", "-C", str(ROOT), "show", f"HEAD:{relative}"],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        on_disk = ROOT / relative
        if committed.returncode != 0 or not on_disk.is_file():
            modified.append(relative)
            continue
        if _normalised(committed.stdout) != _normalised(on_disk.read_text(encoding="utf-8")):
            modified.append(relative)
    return {"head": head, "sources_differing_from_head": modified}


def develop() -> Path:
    from scripts.research.continuous_portfolio import development
    from scripts.research.continuous_portfolio import prereg as prereg_module

    for name in (STARTED, FINISHED):
        if (ARTIFACTS / name).exists():
            raise SystemExit(f"{name} exists: the pre-registered run happens once")
    bound = checkout((*prereg_module.HASHED_SOURCES, *RUN_BOUND_SOURCES))
    if bound["sources_differing_from_head"]:
        raise SystemExit(f"sources differ from HEAD: {bound}")
    frozen = prereg_module.assert_frozen()
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    marker = json.dumps(
        {
            "started_utc": dt.datetime.now(dt.UTC).isoformat(),
            "checkout": bound,
            "preregistration_frozen_hash": frozen,
        },
        indent=2,
        sort_keys=True,
    )
    try:
        with (ARTIFACTS / STARTED).open("x", encoding="utf-8") as handle:
            handle.write(marker + "\n")
    except FileExistsError as exc:
        raise SystemExit(f"{STARTED} exists: the pre-registered run happens once") from exc
    record = development.run()
    record["checkout"] = bound
    return _write(FINISHED, record)


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
        path = develop()
    print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
