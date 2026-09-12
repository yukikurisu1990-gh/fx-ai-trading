"""Entry point: write the model-learning design artefacts. Reads no market data.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

    python -m scripts.research.model_learning.driver design

The design stage is signal-blind by construction — every number it writes is
arithmetic over declared constants — and the only filesystem touch in this
package is the artefact write below.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Final

from scripts.research.model_learning import PROTECTED_SPANS, SEEN_SPANS
from scripts.research.model_learning import prereg as prereg_module
from scripts.research.model_learning import universe as universe_module

ARTIFACTS: Final[Path] = Path("artifacts/research/model_learning")


def _write(name: str, payload: dict[str, Any]) -> Path:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    path = ARTIFACTS / name
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def design() -> Path:
    payload = universe_module.build()
    payload["seen_spans"] = {
        name: {key: value for key, value in block.items()} for name, block in SEEN_SPANS.items()
    }
    payload["protected_spans"] = PROTECTED_SPANS
    payload["protected_data_read"] = False
    #: The frozen specification travels with the design it was frozen against, so
    #: a reader never has to take on trust that the two agree.
    payload["preregistration"] = prereg_module.specification()
    payload["preregistration_frozen_hash"] = prereg_module.assert_frozen()
    return _write("design.json", payload)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("design",))
    args = parser.parse_args(argv)
    if args.stage == "design":
        path = design()
        print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
