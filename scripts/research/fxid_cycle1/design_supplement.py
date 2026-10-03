# ruff: noqa: E501 -- driver prose
"""Cycle 1 の設計の算術の補遺（**data を読まない**。純粋な算術）。独立レビュー（Role 1 の R2・R3）への対応。

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

- run 2 の `design_arithmetic` は prior の平均を μ = 0.07 に固定していた。懐疑的な prior（μ = 0）の行をここで足す。
- 分割ごとの選択の検出力（max-T、試行 20、Šidák）を、最後まで通る確率と並べて出す。
- 仮定: 真の Sharpe は期間をまたいで一定、候補は独立（実測の等価試行数は 16.8 なので保守側）、「最大でもある」条件は無視。
- prior・G4・閾値は**凍結しない**（裁定）。
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any, Final

from scipy.stats import norm

REPO: Final[Path] = Path(__file__).resolve().parents[3]
RECORD: Final[Path] = REPO / "artifacts/research/fxid_cycle1/cycle1_design_supplement.json"
FRESH_YEARS: Final[float] = 4.895
SPLITS: Final[dict[str, tuple[float, float, float]]] = {
    "1_3_block_pre2016_select_10y__seen_estimate_4.68y__fresh": (10.0, 4.68, FRESH_YEARS),
    "2_pre2016_split_select_6y__pre2016_estimate_4y__fresh": (6.0, 4.0, FRESH_YEARS),
    "4_pre2016_split_6y_4y__fresh_kept__forward_3y_confirm": (6.0, 4.0, 3.0),
}


def p_select(years: float, n_eff: int, s: float) -> float:
    se = 1 / math.sqrt(years)
    thr = se * norm.ppf((1 - 0.10) ** (1 / n_eff))
    return float(1 - norm.cdf((thr - s) / se))


def p_estimate(years: float, mu: float, tau: float, g4: float, s: float) -> tuple[float, float]:
    se = 1 / math.sqrt(years)
    w = tau**2 / (tau**2 + se**2)
    need = mu + (g4 - mu) / w
    return float(1 - norm.cdf((need - s) / se)), need


def p_confirm(years: float, s: float) -> float:
    return float(1 - norm.cdf(1.645 - s * math.sqrt(years)))


def compute() -> dict[str, Any]:
    out: dict[str, Any] = {"assumptions": __doc__.split("- ", 1)[1].strip()}
    for name, (sel, est, conf) in SPLITS.items():
        block: dict[str, Any] = {
            "selection_power_n20": {
                str(s): round(p_select(sel, 20, s), 4) for s in (0.8, 1.0, 1.5)
            },
            "confirm_power": {str(s): round(p_confirm(conf, s), 4) for s in (0.8, 1.0, 1.5)},
        }
        for mu in (0.0, 0.07):
            for tau in (0.4, 0.565, 0.8):
                for label, g4 in (("G4-A_1.0", 1.0), ("G4-B_0.8", 0.8)):
                    cells = {}
                    need = 0.0
                    for s in (0.8, 1.0, 1.5):
                        pe, need = p_estimate(est, mu, tau, g4, s)
                        cells[str(s)] = round(p_select(sel, 20, s) * pe * p_confirm(conf, s), 4)
                    block[f"mu={mu}|tau={tau}|{label}"] = {
                        "overall": cells,
                        "observed_needed_in_estimate_block": round(need, 3),
                    }
        out[name] = block
    return out


def main() -> int:
    if RECORD.exists():
        raise SystemExit(f"{RECORD} は既にある。上書きしない")
    RECORD.write_text(
        json.dumps(compute(), ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n"
    )
    print(RECORD)
    return 0


if __name__ == "__main__":
    sys.exit(main())
