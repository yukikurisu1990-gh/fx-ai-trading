# ruff: noqa: E501 -- power prose
"""**実行前の検出力**（§19）。alpha を 1 つも計算しない。

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

読むのは decision day の数・span の長さ・月次 target weight の持続性だけで、**return と signal を
突き合わせない**（P&L・IC・Sharpe は計算しない）。target weight は過去の金利・過去の return・過去の共分散の
関数で、翌日以降の return を含まない。

「検出力が低いから走らせない」とはしない（裁定 §19）。最後の bounded development test として実行する。
"""

from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Any, Final

from scripts.research.acquisition_safety import write_provenance
from scripts.research.classical_premia import book, data, execute, prereg

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[3]
RECORD: Final[Path] = REPO_ROOT / prereg.POWER_RECORD
Z_975: Final[float] = 1.959964
Z_80: Final[float] = 0.841621


def _phi(x: float) -> float:
    return 0.5 * math.erfc(-x / math.sqrt(2.0))


def two_sided_power(true_sharpe: float, years: float) -> float:
    se = 1.0 / math.sqrt(years)
    return _phi(true_sharpe / se - Z_975) + _phi(-true_sharpe / se - Z_975)


def composite_sharpe(family_sharpe: float, rho: float) -> float:
    """2 family が同じ真の Sharpe s・相関 ρ で等リスクなら、合成は s·√(2/(1+ρ))。"""
    return family_sharpe * math.sqrt(2.0 / (1.0 + rho))


def analysis(years: float, persistence: dict[str, Any]) -> dict[str, Any]:
    se = 1.0 / math.sqrt(years)
    return {
        "available_years": round(years, 3),
        "sharpe_se": round(se, 4),
        "mde_two_sided_5pct_power_80": round((Z_975 + Z_80) * se, 4),
        "detection_floor_two_sided_5pct": round(Z_975 * se, 4),
        "power_composite_true_sharpe": {
            f"{s}": round(two_sided_power(s, years), 4) for s in (0.2, 0.3, 0.5)
        },
        "carry_momentum_correlation_assumption": {
            "range": [-0.2, 0.0, 0.2],
            "why": "文献（Menkhoff et al. 2012、Asness et al. 2013）で通貨の carry と momentum の return の相関は 0 近傍（弱い負から弱い正）。**仮定であり、このデータで測っていない**",
        },
        "composite_sharpe_if_each_family_has": {
            f"family_s={s}": {
                f"rho={r}": round(composite_sharpe(s, r), 4) for r in (-0.2, 0.0, 0.2)
            }
            for s in (0.1, 0.2, 0.3)
        },
        "power_if_each_family_has": {
            f"family_s={s}": {
                f"rho={r}": round(two_sided_power(composite_sharpe(s, r), years), 4)
                for r in (-0.2, 0.0, 0.2)
            }
            for s in (0.1, 0.2, 0.3)
        },
        "signal_persistence_and_effective_n": persistence,
        "reading": (
            "Sharpe の SE ≈ 1/√年数 は日次 iid の近似で、月次 rebalance の持続的な position では不確実性を過小評価する。"
            "有効標本数（月次 target の自己相関から）が小さいほど、実際の検出力は表より低い"
        ),
        "decision": "検出力が低くても走らせる（裁定 §19）",
        "what_the_gates_actually_test": (
            "carry の target はほぼ静的なので、family 単独の有効標本数は 1 未満になる。primary null（通貨 label の置換）は "
            "『高金利の**その**通貨群が稼いだか』を 2,000 通りの別の割り当てと比べるので、静的な carry premium も含めて検定する。"
            "secondary の circular shift は静的な賭けを帰無に含むので中心が 0 でなく、timing の情報だけを見る。"
            "composite の有効標本数は target weight だけで決まり、F4（≥ 10）は実行前に PASS と分かっている（大半は momentum の回転による）"
        ),
    }


def persistence_from_targets(inputs: book.Inputs, scores) -> dict[str, Any]:
    cov = book.covariances(inputs.returns, inputs.decision_days, list(prereg.UNIVERSE))
    targets = book.targets(inputs, scores, cov=cov)
    out: dict[str, Any] = {"composite": execute.effective_n(targets["composite"])}
    for family in book.FAMILIES:
        #: family ごとの有効標本数（Role 1 R5）。carry はほぼ静的な 1 つの賭けになる
        out[family] = execute.effective_n(targets[family])
    out["months_at_gross_cap"] = int(targets["capped"]["capped"].sum())
    out["note"] = "target weight だけから計算した（return との突き合わせなし）"
    return out


def main() -> int:
    inputs, scores, provenance = data.build()
    years = len(inputs.span) / book.TRADING_DAYS
    payload = {
        "cycle": prereg.CYCLE,
        "computed_before_alpha": True,
        "panel": provenance,
        "analysis": analysis(years, persistence_from_targets(inputs, scores)),
    }
    written = write_provenance(RECORD, payload)
    print(f"written {RECORD} {written}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
