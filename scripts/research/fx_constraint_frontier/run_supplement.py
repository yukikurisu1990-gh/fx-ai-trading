# ruff: noqa: E501 -- research prose
"""独立レビューの後の補足の計算を 1 回だけ実行し、記録する（分類の規則は変えない）。

command: python -X utf8 -m scripts.research.fx_constraint_frontier.run_supplement
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Final

from scripts.research.fx_constraint_frontier import frontier as fr
from scripts.research.fx_constraint_frontier import provenance as pv
from scripts.research.fx_constraint_frontier import supplement as sp
from scripts.research.fx_constraint_frontier.run_frontier import _clean

RECORD: Final[Path] = pv.REPO / "artifacts/research/fx_constraint_frontier/supplement.json"
SYNTH: Final[Path] = pv.REPO / "artifacts/research/fx_constraint_frontier/synthetic_contracts.json"


def main() -> int:
    payload = pv.start(RECORD)
    payload["status"] = (
        "POST_REVIEW_SUPPLEMENT_NOT_PREREGISTERED_AS_COMPUTED_CLASSIFICATION_RULE_UNCHANGED"
    )
    payload["command"] = "python -X utf8 -m scripts.research.fx_constraint_frontier.run_supplement"
    payload["code_sha256"] = {
        "supplement.py": pv.sha256_text(Path(sp.__file__)),
        "run_supplement.py": pv.sha256_text(Path(__file__)),
        "frontier.py": pv.sha256_text(Path(fr.__file__)),
        "contracts.py": pv.sha256_text(Path(fr.c.__file__)),
    }
    payload["input_sha256"] = {"inputs.json": pv.sha256_text(fr.HERE / "inputs.json")}
    payload["seed"] = fr.c.SEED
    payload["reps"] = fr.c.REPS
    chosen = str(json.loads(SYNTH.read_text(encoding="utf-8"))["selection"]["chosen"])
    inp = fr.load_inputs()
    payload["A_B_sensitivities_and_literal_system"] = sp.section_a_b(inp, chosen)
    payload["C_years_grid"] = sp.section_c(inp)
    payload["D_review_corrections"] = sp.section_d(inp, chosen)
    payload["E_synthetic_prereg_null"] = sp.section_e_synthetic_prereg_null()
    payload["F_single_test_years_reference"] = {
        f"s_{s}_alpha_{a}": round(sp.single_test_years(s, a), 2)
        for s in (0.42, 0.5, 1.0)
        for a in (0.10, 0.05)
    }
    pv.finish(RECORD, _clean(payload))
    return 0


if __name__ == "__main__":
    sys.exit(main())
