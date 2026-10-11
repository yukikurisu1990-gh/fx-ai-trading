# ruff: noqa: E501 -- research prose
"""候補 × 制約の frontier の行列・分類・寄与の分解を 1 回だけ実行し、記録する（事前登録 §9〜§12）。

command: python -X utf8 -m scripts.research.fx_constraint_frontier.run_frontier
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any, Final

from scripts.research.fx_constraint_frontier import frontier as fr
from scripts.research.fx_constraint_frontier import provenance as pv

RECORD: Final[Path] = pv.REPO / "artifacts/research/fx_constraint_frontier/frontier.json"
SYNTH: Final[Path] = pv.REPO / "artifacts/research/fx_constraint_frontier/synthetic_contracts.json"


def _clean(x: Any) -> Any:
    if isinstance(x, float) and not math.isfinite(x):
        return "inf" if x > 0 else "-inf"
    if isinstance(x, dict):
        return {k: _clean(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_clean(v) for v in x]
    return x


def main() -> int:
    payload = pv.start(RECORD)
    synth = json.loads(SYNTH.read_text(encoding="utf-8"))
    chosen = str(synth["selection"]["chosen"])
    inp = fr.load_inputs()
    payload["command"] = "python -X utf8 -m scripts.research.fx_constraint_frontier.run_frontier"
    payload["code_sha256"] = {
        "frontier.py": pv.sha256_text(Path(fr.__file__)),
        "run_frontier.py": pv.sha256_text(Path(__file__)),
        "contracts.py": pv.sha256_text(Path(fr.c.__file__)),
    }
    payload["input_sha256"] = {
        "inputs.json": pv.sha256_text(fr.HERE / "inputs.json"),
        "synthetic_contracts.json": pv.sha256_text(SYNTH),
    }
    payload["seed"] = fr.c.SEED
    payload["reps"] = fr.c.REPS
    payload["contract_chosen"] = chosen
    payload["d_quantiles"] = {k: fr.d_quantiles(inp, k) for k in ("pub", "desk")}
    points = []
    for p in fr.grid():
        r = fr.evaluate_point(inp, p, chosen)
        points.append((p, r))
    payload["matrix"] = [
        {"point": p.__dict__, "deviation": fr.deviation(p), "result": r} for p, r in points
    ]
    payload["classification"] = fr.classify(points)
    payload["critical"] = {
        con: fr.critical_thresholds(inp, con) for con in sorted({chosen, "S0", "S3", "S4"})
    }
    payload["shapley_margin"] = {
        t: fr.shapley(inp, "S0", chosen, t) for t in ("system", "K1", "K2", "K3", "K4")
    }
    hi = dict(inp)
    hi["financing_bp_per_night"] = 1.0
    payload["financing_1bp_sensitivity_H1_E2_median"] = fr.evaluate_point(
        hi, fr.Point("E2", "H1", "flat", "median", "current"), chosen
    )
    pv.finish(RECORD, _clean(payload))
    return 0


if __name__ == "__main__":
    sys.exit(main())
