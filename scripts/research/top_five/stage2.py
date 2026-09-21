# ruff: noqa: E501 -- stage 2 prose
"""Stage 2 を**再現可能な形で**走らせる。

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

初稿では `stage2_t5.json` が手作業で作られており、**生成コードが repo に無かった**。
レビューでそれを指摘され、ここへ移した。この module は 3 つを出す。

1. 凍結した `STAGE_2_ELIGIBILITY` の 3 条件を、近 span の実測値に当てて判定する。
2. 適格なら、凍結が許す**ただ 1 つ**の model（signal と control の 2 変数線形回帰）を走らせる。
3. 裁定の `multiplicity_note` が要求する **帰無通過確率** と、C-2 が導入した
   nuisance 定数（`max_staleness_days`）の感度を測る。

3 は「t が小さい」以上のことを言う。**低 turnover の track は、signal が無くても
3 条件を通りやすい**ので、通過した事実そのものには情報が少ない。どれくらい少ないかを
permutation で測る。
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
import warnings
from pathlib import Path
from typing import Any, Final

import numpy as np
import pandas as pd

from scripts.research.acquisition_safety import write_provenance
from scripts.research.continuous_portfolio import construction
from scripts.research.top_five import execute, panel, prereg, signals

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[3]
RECORD: Final[Path] = REPO_ROOT / "artifacts/research/top_five/stage2_t5.json"

TRACK: Final[str] = "T5"
SPAN: Final[str] = "recent"

#: C-2 が選んだ 75 日の周りを、**結果を見て選び直さないために**明示的に固定する。
#: この格子は報告のためのものであって、ここから良い値を拾うためのものではない。
STALENESS_GRID: Final[tuple[int, ...]] = (45, 60, 62, 70, 75, 80, 90, 120, 400)

DEFAULT_DRAWS: Final[int] = 500
PERMUTATION_SEED: Final[int] = 20260921


def _usable_scores(index: pd.DatetimeIndex) -> pd.DataFrame:
    """T5 の score を、driver と**同じ**連続化規則で取り出す。"""
    raw = signals.t5_scores(index)
    seeded = raw.dropna(how="any")
    if seeded.empty:
        return seeded
    first = index.get_loc(seeded.index[0])
    last = index.get_loc(seeded.index[-1])
    contiguous = index[first : last + 1]
    return raw.reindex(contiguous).ffill().dropna(how="any")


def _regression(
    scores: pd.DataFrame, control: pd.DataFrame, excess: pd.DataFrame
) -> dict[str, Any]:
    """凍結が許す唯一の model: forward ~ 1 + signal + control。"""
    forward = excess.shift(-1)
    rows: list[tuple[float, float, float]] = []
    for day in scores.index:
        s, c, f = scores.loc[day], control.loc[day], forward.loc[day]
        usable = s.notna() & c.notna() & f.notna()
        if usable.sum() >= 3:
            for currency in s.index[usable]:
                rows.append((float(s[currency]), float(c[currency]), float(f[currency])))
    if len(rows) < 100:
        return {"status": "INSUFFICIENT_OBSERVATIONS", "observations": len(rows)}

    frame = pd.DataFrame(rows, columns=["signal", "control", "forward"])
    design = np.column_stack(
        [np.ones(len(frame)), frame["signal"].to_numpy(), frame["control"].to_numpy()]
    )
    target = frame["forward"].to_numpy()
    beta, *_ = np.linalg.lstsq(design, target, rcond=None)
    residual = target - design @ beta
    dof = len(frame) - design.shape[1]
    variance = float(residual @ residual) / dof
    stderr = np.sqrt(np.diag(np.linalg.inv(design.T @ design) * variance))
    centred = target - target.mean()
    return {
        "status": "RAN",
        "observations": int(len(frame)),
        "signal_beta": float(beta[1]),
        "signal_t": float(beta[1] / stderr[1]),
        "control_beta": float(beta[2]),
        "control_t": float(beta[2] / stderr[2]),
        "r_squared": float(1.0 - (residual @ residual) / float(centred @ centred)),
        "caveat": (
            "**観測は通貨 x 日で数えた 4 千件あるが、独立な signal の状態はその数ではない。** "
            "T5 の score は月次 series の前方補完なので、同じ値が数十日続く。"
            "t はこの重複を補正していない — **過大である**"
        ),
    }


def _eligibility(metrics: dict[str, Any]) -> dict[str, Any]:
    """凍結した 3 条件。**近 span でのみ判定する**（cost が実測された唯一の span）。"""
    checks = {
        "condition_1_gross_sharpe_positive": float(metrics["gross_sharpe"]) > 0,
        "condition_2_incremental_ic_positive": float(metrics["incremental_ic"]) > 0,
        "condition_3_net_annual_return_positive": float(metrics["net_annual_return"]) > 0,
    }
    return {
        "rule": prereg.STAGE_2_ELIGIBILITY,
        "measured": {
            "gross_sharpe": round(float(metrics["gross_sharpe"]), 4),
            "incremental_ic": round(float(metrics["incremental_ic"]), 5),
            "net_annual_return": round(float(metrics["net_annual_return"]), 5),
        },
        "checks": checks,
        "eligible": all(checks.values()),
    }


def _sharpe(series: pd.Series) -> float:
    sd = float(series.std(ddof=0))
    return float(series.mean() / sd * np.sqrt(execute.TRADING_DAYS)) if sd > 0 else float("nan")


def _lag_one_autocorrelation(frame: pd.DataFrame) -> float:
    """列平均の lag-1 自己相関。**帰無が signal の持続性を壊していないか**を測る物差し。"""
    values = frame.to_numpy(dtype=float)
    current = values[:-1].ravel()
    following = values[1:].ravel()
    usable = np.isfinite(current) & np.isfinite(following)
    if usable.sum() < 3 or current[usable].std() == 0 or following[usable].std() == 0:
        return float("nan")
    return float(np.corrcoef(current[usable], following[usable])[0, 1])


def _circular_shift(scores: pd.DataFrame, shift: int) -> pd.DataFrame:
    """**行の並びを保ったまま**巡回させる。shuffle ではない。

    shuffle にすると turnover が跳ね上がり、「回転が少ないから cost を払わずに済む」
    という T5 の性質まで壊れる。それでは 3 条件の**通りやすさ**を測ったことにならない。
    """
    return pd.DataFrame(
        np.roll(scores.to_numpy(), shift, axis=0), index=scores.index, columns=scores.columns
    )


def _rank_descending(value: float, values: list[float]) -> int:
    """`value` が `values` の中で大きい方から何位か（1 始まり）。"""
    return int(sorted(values, reverse=True).index(value) + 1)


def _null_calibration(
    scores: pd.DataFrame,
    excess: pd.DataFrame,
    control: pd.DataFrame,
    observed_t: float,
    draws: int,
) -> dict[str, Any]:
    """**circular shift** の帰無。signal 自身の時系列構造を保ったまま、return との対応だけ壊す。

    shuffle ではなく circular shift を使う理由は、T5 の score が月次値の前方補完で
    強く自己相関しているからである。行を混ぜると turnover が跳ね上がり、
    「回転が少ないから cost を払わずに済む」という T5 の性質まで壊してしまう。
    それでは **3 条件の通りやすさ**を測ったことにならない。
    """
    rng = np.random.default_rng(PERMUTATION_SEED)
    config = execute._config(TRACK)
    length = len(scores)
    #: **実行時の不変量。** 帰無が signal の持続性を保っていなければ、測っているのは
    #: 「この gate の通りやすさ」ではなく「高回転 book が cost に負けること」である。
    observed_persistence = _lag_one_autocorrelation(scores)

    passes = 0
    t_ge = 0
    both = 0
    net_sharpes: list[float] = []
    for _ in range(draws):
        shift = int(rng.integers(1, length))
        shifted = _circular_shift(scores, shift)
        drawn_persistence = _lag_one_autocorrelation(shifted)
        if np.isfinite(observed_persistence) and not (
            abs(drawn_persistence - observed_persistence) < 0.05
        ):
            raise AssertionError(
                "帰無が signal の自己相関を壊した "
                f"({observed_persistence:.3f} -> {drawn_persistence:.3f})。"
                "circular shift ではなく shuffle になっていないか"
            )
        daily = construction.run_book(config, shifted, excess, execute.TRADING_DAYS)["daily"]
        net = daily["net"]
        net_annual = float(net.sum() / (len(net) / execute.TRADING_DAYS))
        eligible = (
            _sharpe(daily["gross"]) > 0
            and execute._incremental_ic(shifted, control, excess) > 0
            and net_annual > 0
        )
        t_value = float(_regression(shifted, control, excess).get("signal_t", 0.0))
        net_sharpes.append(_sharpe(net))
        passes += int(eligible)
        t_ge += int(t_value >= observed_t)
        both += int(eligible and t_value >= observed_t)

    array = np.array(net_sharpes)
    return {
        "method": "CIRCULAR_SHIFT_PRESERVING_THE_SIGNAL_AUTOCORRELATION",
        "draws": draws,
        "seed": PERMUTATION_SEED,
        "stage_2_gate_pass_rate_under_null": round(passes / draws, 4),
        "p_value_on_signal_t": round(t_ge / draws, 4),
        "joint_pass_and_t_rate": round(both / draws, 4),
        "null_net_sharpe_mean": round(float(array.mean()), 4),
        "null_net_sharpe_p95": round(float(np.percentile(array, 95)), 4),
        "reading": (
            "**gate の通過率が高いほど、通過した事実の情報量は小さい。** 裁定が "
            "`multiplicity_note` で要求しているのはこの数字であり、"
            "T5 は 5 本で最も turnover が低いので、最も通りやすい track である"
        ),
    }


def _staleness_sensitivity(excess: pd.DataFrame) -> dict[str, Any]:
    """C-2 で**新しく選んだ** `max_staleness_days` の感度。

    **これは値を選び直すための探索ではない。** 凍結値を動かさないまま、
    報告値がこの nuisance 定数のどこに位置するかを開示するためのものである。
    """
    original = prereg.SIGNAL_CONSTANTS["max_staleness_days"]
    config = execute._config(TRACK)
    benches = execute._benchmarks(excess)
    index = excess.index
    grid: dict[str, Any] = {}
    try:
        for days in STALENESS_GRID:
            prereg.SIGNAL_CONSTANTS["max_staleness_days"] = days
            importlib.reload(signals)
            scores = _usable_scores(index)
            if scores.empty:
                grid[str(days)] = {"status": "NO_USABLE_DAYS"}
                continue
            window = scores.index

            def _net(frame: pd.DataFrame, window: pd.DatetimeIndex = window) -> float:
                aligned = frame.reindex(window).dropna(how="any")
                book = construction.run_book(config, aligned, excess, execute.TRADING_DAYS)
                return round(_sharpe(book["daily"]["net"]), 4)

            candidate = _net(scores)
            null = _net(benches["constant_long_usd"])
            grid[str(days)] = {
                "days": int(len(window)),
                "net_sharpe": candidate,
                "constant_long_usd_net_sharpe": null,
                "increment_over_null": round(candidate - null, 4),
                "fx_own_mean_reversion_20d_net_sharpe": _net(benches["fx_own_mean_reversion_20d"]),
            }
    finally:
        prereg.SIGNAL_CONSTANTS["max_staleness_days"] = original
        importlib.reload(signals)

    ran = [row for row in grid.values() if "net_sharpe" in row]
    nets = [row["net_sharpe"] for row in ran]
    increments = [row["increment_over_null"] for row in ran]
    frozen = grid[str(original)]
    rank = _rank_descending(frozen["net_sharpe"], nets)
    beats_price_only = all(
        row["net_sharpe"] > row["fx_own_mean_reversion_20d_net_sharpe"] for row in ran
    )
    return {
        "frozen_value": original,
        "grid": grid,
        "net_sharpe_range": [min(nets), max(nets)],
        "increment_range": [min(increments), max(increments)],
        "frozen_value_rank_among_net_sharpes": rank,
        "grid_size": len(nets),
        "sign_is_positive_at_every_grid_point": all(value > 0 for value in nets),
        "beats_price_only_baseline_at_every_grid_point": beats_price_only,
        "finding": (
            f"**凍結値 {original} は、試した {len(nets)} 点の中で net Sharpe が {rank} 位に"
            "なる点である。** この定数に経済的な内容は無い"
            "（いつ値が古すぎるとみなすかの事務上の上限）のに、"
            f"net Sharpe は {min(nets):+.2f} … {max(nets):+.2f} と動く。"
            "**報告した値は楽観側**であり、"
            f"null 超過分も {min(increments):+.2f} … {max(increments):+.2f} と同じ桁だけ動く。"
            "符号はどの点でも正で、価格のみの mean-reversion book もどの点でも上回るので、"
            "**向きは頑健だが、大きさは信用してはならない**"
        ),
    }


def run(*, draws: int = DEFAULT_DRAWS) -> dict[str, Any]:
    built = panel.build()
    excess = built[SPAN]["currency_excess_return"]
    scores = _usable_scores(excess.index)
    control = execute._benchmarks(excess)["fx_own_momentum_20d"].reindex(scores.index)

    result = execute.run_track(TRACK, SPAN, built)
    eligibility = _eligibility(result["metrics"])
    stage_2 = (
        _regression(scores, control, excess)
        if eligibility["eligible"]
        else {"status": "NOT_ELIGIBLE_STOPPED"}
    )

    payload: dict[str, Any] = {
        "cycle": "TOP_FIVE_2026_09",
        "track": TRACK,
        "span": SPAN,
        "freeze_digest": prereg.freeze_digest(),
        "digest_as_executed": prereg.DIGEST_AS_EXECUTED,
        "post_execution_corrections": prereg.POST_EXECUTION_CORRECTIONS["status"],
        "window": {
            "first": str(scores.index[0].date()),
            "last": str(scores.index[-1].date()),
            "days": int(len(scores)),
            "years": round(len(scores) / execute.TRADING_DAYS, 3),
            "distinct_signal_states": int(scores["USD"].round(6).nunique()),
        },
        "eligibility": eligibility,
        "benchmarks": result["benchmarks"],
        "stage_2": stage_2,
    }
    if eligibility["eligible"]:
        payload["null_calibration"] = _null_calibration(
            scores, excess, control, float(stage_2.get("signal_t", 0.0)), draws
        )
    payload["staleness_sensitivity"] = _staleness_sensitivity(excess)
    payload["conclusion"] = (
        "**Stage 2 は T5 を確認していない。** 3 条件は通ったが、"
        "その gate は帰無のもとでも高い確率で通る（`null_calibration` 参照）。"
        "回帰の signal 係数は t={t:+.2f} で、しかもこの t は前方補完による重複を"
        "補正していないぶん過大である。**UNDERPOWERED_FOR_CONFIRMATORY_CLAIM** であって、"
        "NOT_WORTH_DEVELOPING ではない"
    ).format(t=float(stage_2.get("signal_t", float("nan"))))
    return payload


def main() -> int:
    warnings.filterwarnings("ignore")
    parser = argparse.ArgumentParser(description="Stage 2 を再現する")
    parser.add_argument("--draws", type=int, default=DEFAULT_DRAWS)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    payload = run(draws=args.draws)
    RECORD.parent.mkdir(parents=True, exist_ok=True)
    written = write_provenance(
        RECORD,
        payload,
        overwrite=args.overwrite,
        env_name="TOP_FIVE_OVERWRITE" if args.overwrite else None,
    )
    print(json.dumps(payload["eligibility"]["checks"], ensure_ascii=False))
    print(json.dumps(payload["stage_2"], ensure_ascii=False, default=str)[:300])
    print(json.dumps(payload.get("null_calibration", {}), ensure_ascii=False)[:300])
    print(f"written: {RECORD} sha256={written}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
