# ruff: noqa: E501 -- calibration prose
"""**gate を凍結する時点で、その gate の帰無通過率を測る**（2026-09-22 裁定 §G）。

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

前 cycle の失敗はこうだった — 事前登録した 3 条件 gate を T5 が通り、設計上は
「何かを示した」ように読めたが、後から測ると **その gate は帰無でも 42% 通った**。
つまり通過そのものに情報がほとんど無かった。

**だから今回は、gate を凍結する時点で測る。** 候補のデータは一切使わない。
使うのは (a) 既に seen の FX panel と (b) 各 track が *宣言した signal の周期* だけである。
**signal-blind** であり、alpha を見る前に走らせられる。

測り方: 各 track の宣言周期と同じ持続性を持つ **零情報の合成 signal** を引き、
凍結した執行層に通し、凍結した gate に当てる。通った割合が帰無通過率である。

裁定 §G の帰結:

    null pass probability が高い gate は、hard selection gate として扱わず
    diagnostic へ降格する。「gate を通った」だけを情報として扱わない。
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
from scripts.research.continuous_portfolio import construction
from scripts.research.next_five import prereg
from scripts.research.top_five import panel

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[3]
RECORD: Final[Path] = REPO_ROOT / "artifacts/research/next_five/gate_calibration.json"

TRADING_DAYS: Final[float] = 252.0
DEFAULT_DRAWS: Final[int] = 150
SEED: Final[int] = 20260922

#: 宣言された頻度 → 合成 signal の保持日数（営業日）。
#: **これは track が自分で宣言した周期であって、結果から決めた値ではない。**
HOLD_DAYS: Final[dict[str, int]] = {
    "monthly": 21,
    "weekly_to_monthly": 21,
    "event_paced": 30,
    "daily": 5,
}


def _config(track: str) -> construction.BookConfig:
    """凍結した book 設定。**track ごとの逸脱は今回置いていない。**"""
    frozen = {k: v for k, v in prereg.BOOK_CONFIG.items() if not k.startswith("why_")}
    frozen.pop("days_per_year", None)
    frozen.update(prereg.BOOK_CONFIG_DEVIATIONS.get(track, {}))
    return construction.BookConfig(name=track, cost_multiple=1.0, **frozen)


def _synthetic(
    index: pd.DatetimeIndex, columns: list[str], hold: int, rng: np.random.Generator
) -> pd.DataFrame:
    """**零情報だが、宣言された周期と同じ持続性を持つ** score。

    毎日引き直すと turnover が跳ね上がり、「回転が少ないから cost を払わない」という
    性質が消えてしまう。それでは gate の通りやすさを測ったことにならない。
    """
    blocks = len(index) // hold + 1
    steps = rng.normal(0.0, 1.0, size=(blocks, len(columns)))
    held = np.repeat(steps, hold, axis=0)[: len(index)]
    return pd.DataFrame(held, index=index, columns=columns)


def _daily_ic(scores: pd.DataFrame, forward: pd.DataFrame) -> float:
    """日次 cross-section 相関の平均。**ベクトル化して回す**（150 回引くため）。"""
    aligned = forward.reindex(scores.index)
    usable = scores.notna() & aligned.notna()
    enough = usable.sum(axis=1) >= 3
    if not enough.any():
        return float("nan")
    left = scores.where(usable)[enough]
    right = aligned.where(usable)[enough]
    left = left.sub(left.mean(axis=1), axis=0)
    right = right.sub(right.mean(axis=1), axis=0)
    numerator = (left * right).sum(axis=1)
    denominator = np.sqrt((left**2).sum(axis=1) * (right**2).sum(axis=1))
    per_day = numerator / denominator.replace(0.0, np.nan)
    return float(per_day.mean())


def _residual(scores: pd.DataFrame, control: pd.DataFrame) -> pd.DataFrame:
    """control を cross-section で外した残差 score（ベクトル化）。"""
    usable = scores.notna() & control.notna()
    left = scores.where(usable)
    right = control.where(usable)
    left_c = left.sub(left.mean(axis=1), axis=0)
    right_c = right.sub(right.mean(axis=1), axis=0)
    beta = (left_c * right_c).sum(axis=1) / (right_c**2).sum(axis=1).replace(0.0, np.nan)
    return left_c.sub(right_c.mul(beta, axis=0))


def _sharpe(series: pd.Series) -> float:
    sd = float(series.std(ddof=0))
    return float(series.mean() / sd * np.sqrt(TRADING_DAYS)) if sd > 0 else float("nan")


def calibrate_track(track: str, built: dict[str, Any], draws: int) -> dict[str, Any]:
    spec = prereg.TRACKS[track]
    span = spec["primary_span"]
    hold = HOLD_DAYS[spec["frequency"]]
    excess = built[span]["currency_excess_return"]
    columns = list(excess.columns)
    forward = excess.shift(-1)
    control = excess.rolling(20).sum()
    config = _config(track)
    rng = np.random.default_rng(SEED + abs(hash(track)) % 10_000)

    passes = 0
    net_positive = 0
    gross_positive = 0
    incremental_positive = 0
    net_sharpes: list[float] = []
    for _ in range(draws):
        scores = _synthetic(excess.index, columns, hold, rng)
        daily = construction.run_book(config, scores, excess, TRADING_DAYS)["daily"]
        net = daily["net"]
        net_annual = float(net.sum() / (len(net) / TRADING_DAYS))
        gross_ok = _sharpe(daily["gross"]) > 0
        incremental = _daily_ic(_residual(scores, control), forward)
        incremental_ok = bool(np.isfinite(incremental) and incremental > 0)
        net_ok = net_annual > 0
        gross_positive += int(gross_ok)
        incremental_positive += int(incremental_ok)
        net_positive += int(net_ok)
        passes += int(gross_ok and incremental_ok and net_ok)
        net_sharpes.append(_sharpe(net))

    array = np.array([value for value in net_sharpes if np.isfinite(value)])
    return {
        "track": track,
        "candidate": spec["candidate"],
        "primary_span": span,
        "declared_frequency": spec["frequency"],
        "synthetic_hold_days": hold,
        "draws": draws,
        "demoted_gate_null_pass_rate": round(passes / draws, 4),
        "component_null_pass_rates": {
            "gross_sharpe_positive": round(gross_positive / draws, 4),
            "incremental_ic_positive": round(incremental_positive / draws, 4),
            "net_annual_return_positive": round(net_positive / draws, 4),
        },
        "null_net_sharpe_mean": round(float(array.mean()), 4),
        "null_net_sharpe_sd": round(float(array.std(ddof=0)), 4),
        "null_net_sharpe_p95": round(float(np.percentile(array, 95)), 4),
        "detection_floor_mde95": round(float(1.96 / np.sqrt(len(excess) / TRADING_DAYS)), 4),
    }


def run(draws: int = DEFAULT_DRAWS) -> dict[str, Any]:
    built = panel.build()
    tracks = {track: calibrate_track(track, built, draws) for track in prereg.EXECUTION_ORDER}
    rates = {t: row["demoted_gate_null_pass_rate"] for t, row in tracks.items()}
    strictness = {
        "min": min(rates.values()),
        "max": max(rates.values()),
        "spread": round(max(rates.values()) - min(rates.values()), 4),
        "reading": (
            "**同じ規則が track によって違う厳しさで効いている**かどうかがここで見える。"
            "幅が大きいほど、『gate を通った』という事実の意味が track ごとに違う"
        ),
    }
    return {
        "cycle": prereg.CYCLE,
        "freeze_digest": prereg.freeze_digest(),
        "authority": "2026-09-22 Human + ChatGPT 裁定 §G",
        "signal_blind": "NO_CANDIDATE_DATA_USED_ONLY_THE_SEEN_FX_PANEL_AND_DECLARED_PERIODICITY",
        "method": (
            "各 track が宣言した周期と同じ持続性を持つ零情報 signal を引き、"
            "凍結した執行層に通し、凍結した gate に当てる"
        ),
        "seed": SEED,
        "tracks": tracks,
        "gate_strictness_across_tracks": strictness,
        "demoted_gate": prereg.DEMOTED_GATE,
        "null_diagnostic": {
            **{k: v for k, v in prereg.NULL_DIAGNOSTIC.items() if k != "permutation"},
            "permutation": prereg.NULL_DIAGNOSTIC["permutation"],
            "null_pass_rate_basis": (
                "**構成上 5%。** permutation は同じ circular-shift 分布から引くので、"
                "p 値は帰無のもとで一様になる。**実行時に null 分布の形を報告して確かめる** — "
                "ここで nested simulation を回すと 5 本 x 1000 draw x 外側 draw で"
                "現実的な時間に収まらないため、その検証は執行段へ回す"
            ),
        },
        "consequence": (
            "裁定 §G に従い、**帰無通過率の高い gate は hard selection gate として使わない**。"
            "3 条件 triple は diagnostic として報告し、判定は VERDICT_LOGIC（null 診断 + development economics）が決める"
        ),
    }


def main() -> int:
    warnings.filterwarnings("ignore")
    parser = argparse.ArgumentParser(description="gate の帰無通過率を凍結時に測る")
    parser.add_argument("--draws", type=int, default=DEFAULT_DRAWS)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    payload = run(args.draws)
    RECORD.parent.mkdir(parents=True, exist_ok=True)
    written = write_provenance(RECORD, payload, overwrite=args.overwrite)
    for track, row in payload["tracks"].items():
        print(
            f"{track} ({row['candidate']}, {row['primary_span']}): "
            f"帰無通過率 {row['demoted_gate_null_pass_rate']:.2%}  "
            f"MDE95 {row['detection_floor_mde95']:.3f}",
            file=sys.stderr,
        )
    print(json.dumps(payload["gate_strictness_across_tracks"], ensure_ascii=False))
    print(f"written: {RECORD} sha256={written}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
