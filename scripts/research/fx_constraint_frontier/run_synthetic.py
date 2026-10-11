# ruff: noqa: E501 -- research prose
"""統計の契約の合成の較正と選択を 1 回だけ実行し、記録する（事前登録 §5）。実の候補を使わない。

command: python -X utf8 -m scripts.research.fx_constraint_frontier.run_synthetic
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Final

from scripts.research.fx_constraint_frontier import contracts as c
from scripts.research.fx_constraint_frontier import provenance as pv

RECORD: Final[Path] = pv.REPO / "artifacts/research/fx_constraint_frontier/synthetic_contracts.json"


def main() -> int:
    payload = pv.start(RECORD)
    payload["command"] = "python -X utf8 -m scripts.research.fx_constraint_frontier.run_synthetic"
    payload["code_sha256"] = {
        "contracts.py": pv.sha256_text(Path(c.__file__)),
        "run_synthetic.py": pv.sha256_text(Path(__file__)),
    }
    payload["seed"] = c.SEED
    payload["reps"] = c.REPS
    payload["design"] = {
        "F": c.F,
        "W": c.W,
        "tau_sys": c.TAU_SYS,
        "t_s": 4.67,
        "t_e": 6.4,
        "alpha_fw": c.ALPHA_FW,
        "min_point": c.MIN_POINT,
        "tau_floor": c.TAU_FLOOR,
        "li_ji_meff_base": c.li_ji_meff(c.variant_corr(0.7, 0.0)),
    }
    p1, target = c.calibrate_p1()
    payload["s1_p1"] = {"value": p1, "s0_z0_fwer_target": target, "calibrated_on": "Z0 only"}
    results = c.evaluate(p1=p1)
    payload["results"] = results
    payload["selection"] = c.select(results)
    pv.finish(RECORD, payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
