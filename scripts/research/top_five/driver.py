# ruff: noqa: E501 -- driver prose
"""5 本を凍結順に走らせ、結果を 1 つの artefact にまとめる。

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

**途中が negative でも止めない**（裁定 §46）。5 本は既に凍結済みなので、
途中結果を理由に cycle を止めることはしない。止まるのは共通基盤の blocker だけである。
"""

from __future__ import annotations

import argparse
import json
import sys
import warnings
from pathlib import Path
from typing import Any, Final

import numpy as np
import pandas as pd

from scripts.research.acquisition_safety import write_provenance
from scripts.research.top_five import execute, panel, prereg, signals

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[3]
RECORD: Final[Path] = REPO_ROOT / "artifacts/research/top_five/development.json"

SPANS: Final[tuple[str, ...]] = ("long", "recent")


def _rename_gate_t4(excess: pd.DataFrame, scores: pd.DataFrame) -> dict[str, Any]:
    """事前登録した gate: 自通貨 lag-1 残差、および 1 日 own-return book との相関。"""
    _, residuals = signals.t4_scores(excess)
    own = residuals.shift(1)
    pairs = []
    for currency in scores.columns:
        a, b = scores[currency], own[currency]
        usable = a.notna() & b.notna()
        if usable.sum() > 100 and a[usable].std() > 0 and b[usable].std() > 0:
            pairs.append(abs(float(np.corrcoef(a[usable], b[usable])[0, 1])))
    own_book_corr = float(np.mean(pairs)) if pairs else float("nan")
    verdict = "RENAME" if np.isfinite(own_book_corr) and own_book_corr > 0.8 else "DISTINCT"
    return {
        "comparator": "自通貨 lag-1 残差 res_i(t) と mu_i(t)",
        "abs_corr": own_book_corr,
        "threshold": 0.8,
        "verdict": verdict,
    }


def _rename_gate_t3(index: pd.DatetimeIndex, span: str, scores: pd.DataFrame) -> dict[str, Any]:
    """閉じた T-R2 の反転になっていないか。(-Δ2y)-only book との相関で見る。"""
    minus_two_year = {}
    for currency in signals.CURVE_LEGS:
        two = signals._two_year(currency)
        change = two.diff(signals.SLOPE_LOOKBACK)
        minus_two_year[currency] = -panel.align_to_panel(
            change, index, lag=signals._lag_for("sovereign_curves", span)
        )
    frame = pd.DataFrame(minus_two_year).reindex(index)
    ranked = frame.rank(axis=1, pct=True)
    centred = ranked.sub(ranked.mean(axis=1), axis=0)
    pairs = []
    for currency in signals.CURVE_LEGS:
        a, b = scores[currency], centred[currency]
        usable = a.notna() & b.notna()
        if usable.sum() > 100 and a[usable].std() > 0 and b[usable].std() > 0:
            pairs.append(abs(float(np.corrcoef(a[usable], b[usable])[0, 1])))
    corr = float(np.mean(pairs)) if pairs else float("nan")
    return {
        "comparator": "(-Δ2y)-only book（閉じた T-R2 の反転）",
        "abs_corr": corr,
        "threshold": 0.8,
        "verdict": "RENAME" if np.isfinite(corr) and corr > 0.8 else "DISTINCT",
    }


def _rename_gate_t5(
    index: pd.DatetimeIndex, scores: pd.DataFrame, excess: pd.DataFrame
) -> dict[str, Any]:
    """2 か月ラグの USD momentum と同じになっていないか。

    **比較対象の horizon を揃える。** T5 の score は月次値を持ち越すので日次 autocorr が
    0.946 と level 的である。それを 21 日 return と比べると相関は機械的に小さく出る —
    prereg は T4 で同じ構造的欠陥を自分で見つけて比較対象を差し替えているのに、
    T5 には同じ審査が当たっていなかった。**実行後のレビューで指摘された。**
    閾値 0.8 は変えない（変えれば事後の閾値調整になる）。
    """
    usd = excess["USD"]
    measured: dict[str, float] = {}
    for months in (1, 2, 3):
        for horizon, label in ((21, "1m"), (126, "6m"), (252, "12m")):
            lagged = usd.rolling(horizon).sum().shift(21 * months)
            a, b = scores["USD"], lagged.reindex(scores.index)
            usable = a.notna() & b.notna()
            if usable.sum() > 100 and a[usable].std() > 0 and b[usable].std() > 0:
                key = f"cum_{label}_lag_{months}m"
                measured[key] = round(abs(float(np.corrcoef(a[usable], b[usable])[0, 1])), 3)
    worst = max(measured.values()) if measured else 0.0
    return {
        "comparator": "1/2/3 か月ラグ x 1/6/12 か月累積の USD basket return",
        "abs_corr_by_comparator": measured,
        "abs_corr_worst": worst,
        "threshold": 0.8,
        "verdict": "RENAME" if worst > 0.8 else "DISTINCT",
        "caveat": (
            "**閾値は超えないが、horizon を揃えると相関は 0.096 から 0.348 へ上がる。** "
            "『2 か月遅れの USD momentum ではない』という断定は、選べた比較対象の中で"
            "最も弱い数字に依拠してはならない"
        ),
    }


def _turnover_verdict(track: str, metrics: dict[str, Any]) -> dict[str, Any]:
    """凍結した turnover 上限に照らす。

    **比較は単位 gross あたりで行う。** band law は gross 1 単位あたりの turnover を
    出すのに対し、実行層の `one_way_traded` は leverage 適用後の建玉変化である。
    生の値をそのまま比べると leverage 倍（この book では約 4.5 倍）過大に見える。
    """
    frozen = prereg.TRACKS[track]["expected_turnover"]
    corrected = float(frozen["corrected_x1_90"])
    per_unit = float(metrics["turnover_per_unit_gross"])
    return {
        "band_law": frozen["band_law"],
        "corrected_x1_90": corrected,
        "measured_levered": round(float(metrics["turnover_round_trips_per_year"]), 1),
        "measured_per_unit_gross": round(per_unit, 1),
        "mean_portfolio_gross": round(float(metrics["portfolio_gross_leverage"]), 2),
        "exceeds_corrected": bool(per_unit > corrected),
    }


def run() -> dict[str, Any]:
    built = panel.build()
    results: dict[str, Any] = {}
    pnl: dict[str, pd.Series] = {}

    for track in prereg.EXECUTION_ORDER:
        hypotheses = (
            list(prereg.TRACKS["T3"]["direction"]["sub_hypotheses"]) if track == "T3" else [None]
        )
        for hypothesis in hypotheses:
            for span in SPANS:
                key = f"{track}_{span}" + (f"_{hypothesis}" if hypothesis else "")
                try:
                    out = execute.run_track(track, span, built, hypothesis=hypothesis)
                except Exception as error:  # noqa: BLE001 - 失敗も記録する
                    results[key] = {
                        "track": track,
                        "span": span,
                        "error": f"{type(error).__name__}: {error}"[:300],
                    }
                    print(f"{key:26s} ERROR {error}", file=sys.stderr)
                    continue
                if "metrics" not in out:
                    results[key] = out
                    print(f"{key:26s} {out.get('verdict')}", file=sys.stderr)
                    continue
                series = out.pop("daily_net")
                pnl[key] = series
                metrics = out["metrics"]
                out["turnover_check"] = _turnover_verdict(track, metrics)

                excess = built[span]["currency_excess_return"]
                if track == "T3":
                    scores = signals.t3_scores(excess.index, span, hypothesis=hypothesis)
                    out["rename_gate"] = _rename_gate_t3(excess.index, span, scores)
                    out["cross_section_width"] = {
                        "median": float(signals.t3_universe_width(excess.index, span).median()),
                        "max": int(signals.t3_universe_width(excess.index, span).max()),
                    }
                elif track == "T4":
                    scores, _ = signals.t4_scores(excess)
                    out["rename_gate"] = _rename_gate_t4(excess, scores)
                elif track == "T5":
                    scores = signals.t5_scores(excess.index)
                    out["rename_gate"] = _rename_gate_t5(excess.index, scores, excess)

                results[key] = out
                print(
                    f"{key:26s} gross={metrics['gross_sharpe']:+.3f} net={metrics['net_sharpe']:+.3f} "
                    f"turnover={metrics['turnover_round_trips_per_year']:6.1f} "
                    f"incIC={metrics['incremental_ic']:+.4f}",
                    file=sys.stderr,
                )

    #: cross-track の相関診断（exploratory のみ。ここから portfolio は組まない）
    correlation = {}
    keys = sorted(pnl)
    for i, a in enumerate(keys):
        for b in keys[i + 1 :]:
            joined = pd.concat([pnl[a].rename("a"), pnl[b].rename("b")], axis=1).dropna()
            if len(joined) > 100:
                correlation[f"{a}|{b}"] = round(float(joined["a"].corr(joined["b"])), 3)

    return {
        "cycle": "TOP_FIVE_2026_09",
        "freeze_digest": prereg.freeze_digest(),
        "panel": built["provenance"],
        "results": results,
        "cross_track_correlation": correlation,
        "multi_source_portfolio": prereg.MULTI_SOURCE_PORTFOLIO,
        "exploration_disclosure": prereg.EXPLORATION_DISCLOSURE,
    }


def main() -> int:
    """再実行は **明示的に**。committed provenance を黙って置き換えさせない。

    `--overwrite` だけでなく env まで要求するのは、「上書きしたいと書けてしまう
    コード」と「上書きしてよいと人が言った事実」を分けるためである。
    """
    warnings.filterwarnings("ignore")
    parser = argparse.ArgumentParser(description="Top-Five 5 本を凍結順に走らせる")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    payload = run()
    RECORD.parent.mkdir(parents=True, exist_ok=True)
    written = write_provenance(
        RECORD,
        payload,
        overwrite=args.overwrite,
        env_name="TOP_FIVE_OVERWRITE" if args.overwrite else None,
    )
    print(json.dumps(payload["results"], indent=1, ensure_ascii=True, default=str)[:400])
    print(f"written: {RECORD} sha256={written}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
