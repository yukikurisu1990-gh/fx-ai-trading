# ruff: noqa: E501 -- feasibility prose
"""signal-blind feasibility（2026-09-24 裁定 §20）。**return は見ない。**

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

使うのは panel の**日付 index だけ**と、Stage 0 で取得した入力から作った score だけ。
panel の構築は return を計算するが、その値はここでは参照しない（index を取り出すだけ）。

出すもの: coverage・通貨数・signal の持続性・（ドル track の）符号反転の回数・
**有効標本数**・日数ベースの検出下限・cost の損益分岐。

**有効標本数を必ず並べる。** 日数ベースの MDE（1.96/√年）は、signal がほとんど動かないときに
情報量を大きく見せる。自己相関 ρ の AR(1) 近似で N_eff = N·(1−ρ)/(1+ρ) を出す。
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path
from typing import Any, Final

import numpy as np

from scripts.research.acquisition_safety import write_provenance
from scripts.research.mechanism_redesign import signals
from scripts.research.top_five import panel

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[3]
RECORD: Final[Path] = REPO_ROOT / "artifacts/research/mechanism_redesign/feasibility.json"
TRADING_DAYS: Final[float] = 252.0

#: 凍結 cost 規約での 1 単位 gross・1 往復あたりの cost（前 cycle の実測: turnover 6 RT/年で年 0.7〜0.9%、
#: gross ≈ 4 の book）。**損益分岐の桁を示すための算術で、実測ではない。**
ASSUMED_ANNUAL_COST_AT_6_RT: Final[float] = 0.008
VOL_TARGET: Final[float] = 0.10


def _one(track: str, span: str, index) -> dict[str, Any]:
    built = {span: {"currency_excess_return": _index_only(index)}}
    try:
        scores = signals.scores_for(track, built, span)
    except (signals.SignalUnavailableError, signals.NonContiguousScoresError) as error:
        return {
            "track": track,
            "span": span,
            "status": type(error).__name__,
            "why": str(error)[:200],
        }
    if scores.empty:
        return {"track": track, "span": span, "status": "NO_USABLE_DAYS"}
    values = scores.to_numpy()
    rho = float(np.corrcoef(values[:-1].ravel(), values[1:].ravel())[0, 1])
    days = len(scores)
    years = days / TRADING_DAYS
    n_eff = days * (1 - rho) / (1 + rho) if rho < 1 else 1.0
    row: dict[str, Any] = {
        "track": track,
        "span": span,
        "status": "OK",
        "first": scores.index[0].date().isoformat(),
        "last": scores.index[-1].date().isoformat(),
        "days": days,
        "years": round(years, 2),
        "median_active_currencies": int((scores != 0).sum(axis=1).median()),
        "signal_lag1_autocorrelation": round(rho, 4),
        "effective_independent_observations": round(n_eff, 1),
        "mde95_net_sharpe_by_days": round(float(1.96 / np.sqrt(years)), 3),
        "breakeven_gross_sharpe_at_assumed_cost": round(
            ASSUMED_ANNUAL_COST_AT_6_RT / VOL_TARGET, 3
        ),
    }
    if track in signals.DOLLAR_TRACKS:
        sign = np.sign(scores["USD"])
        flips = int((sign.diff().abs() > 0).sum())
        row["usd_sign_flips"] = flips
        row["usd_sign_flips_per_year"] = round(flips / years, 2)
        row["share_of_days_long_usd"] = round(float((sign > 0).mean()), 3)
        row["sign_regimes"] = flips + 1
    return row


def _index_only(index):
    import pandas as pd

    return pd.DataFrame(index=index)


def run() -> dict[str, Any]:
    warnings.filterwarnings("ignore")
    indices = {
        "long": panel.long_span_panel()["currency_excess_return"].index,
        "recent": panel.recent_span_panel()["currency_excess_return"].index,
    }
    rows = [_one(track, span, indices[span]) for track in signals.SCORERS for span in indices]
    return {
        "cycle": "MECHANISM_REDESIGN_2026_09",
        "returns_used": "NO（panel の日付 index だけを使う。return の値は参照しない）",
        "rows": rows,
    }


def main() -> int:
    payload = run()
    RECORD.parent.mkdir(parents=True, exist_ok=True)
    written = write_provenance(RECORD, payload)
    for row in payload["rows"]:
        print(row, file=sys.stderr)
    print(f"written {RECORD} {written}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
