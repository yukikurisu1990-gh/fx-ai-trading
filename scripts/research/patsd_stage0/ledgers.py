# ruff: noqa: E501 -- ledger prose
"""S0-4（fresh pool の汚染台帳）と S0-5（rename 台帳）。

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

**価格の file の中身は読まない。** pre-R1 の取得の重なりは、file system の metadata（mtime）と、
学習 log の text に書かれた日付だけで判定する。
"""

from __future__ import annotations

import datetime as dt
import re
from pathlib import Path
from typing import Any, Final

from scripts.research.patsd_stage0 import prereg

REPO: Final[Path] = Path(__file__).resolve().parents[3]

#: 「価格を読んでいない」と「外部情報を知っている」を分ける。scope は mechanism・通貨・期間に限る（裁定 §21・§22）。
FRESH_EXPOSURES: Final[tuple[dict[str, str], ...]] = (
    {
        "id": "X-472-ALFRED-COT",
        "kind": "EXTERNAL_INFORMATION",
        "source": "#472 exogenous",
        "scope": "US CPI の vintage（ALFRED）と CFTC COT の 2019-01 以降の値。USD の macro surprise / positioning の mechanism だけ",
        "price_read": "NO",
    },
    {
        "id": "X-471-BIS",
        "kind": "EXTERNAL_INFORMATION",
        "source": "#471 economic edge",
        "scope": "BIS 政策金利の 2020-06 以降。carry / 金利の mechanism だけ",
        "price_read": "NO",
    },
    {
        "id": "X-494-CPI-DENOM",
        "kind": "EXTERNAL_INFORMATION",
        "source": "#494 mechanism redesign",
        "scope": "CPI 前年比の分母から 2020 年の物価水準が逆算可能。M01 / M11 / M16（macro momentum・Taylor gap）だけ",
        "price_read": "NO",
    },
    {
        "id": "X-D-M3",
        "kind": "EXTERNAL_INFORMATION",
        "source": "#495 / #496",
        "scope": "2026 年の BoJ の政策決定。forward の JPY 金利に関する確認だけ（fresh pool 2016–2021 には及ばない）",
        "price_read": "NO",
    },
    {
        "id": "X-GENERAL-EVENTS",
        "kind": "GENERAL_KNOWLEDGE",
        "source": "一般常識",
        "scope": "Brexit 2016-06-23、2020-03 の COVID の急変など。event の family（F4）と tail の検査の設計に効きうる。F4 の event list は fresh の時期を見ずに凍結する",
        "price_read": "NO",
    },
    {
        "id": "X-ARCHIVE",
        "kind": "PRICE_FILE_PRESENT_UNREAD",
        "source": "OANDA 10 年 archive（2016-06-02 … 2026-05-29）",
        "scope": "fresh の M1〜D の bid / ask を含む。guard 付きの route は seen の span しか読んでいない",
        "price_read": "NO",
    },
)


def pre_r1_overlap() -> dict[str, Any]:
    """pre-R1 の `*_1825d_BA` の取得が fresh の末尾と重なるか。**中身を読まずに**判定する。"""
    data_dir = REPO / "data"
    stamps = sorted(
        dt.datetime.fromtimestamp(p.stat().st_mtime, tz=dt.UTC)
        for p in data_dir.glob("candles_*_1825d_BA.jsonl")
    )
    log = REPO / "artifacts" / "m15_v2_1825d_train1095.log"
    first_train = None
    if log.exists():
        match = re.search(
            r"train \[(\d{4}-\d{2}-\d{2})", log.read_text(encoding="utf-8", errors="replace")
        )
        first_train = match.group(1) if match else None
    fresh_end = dt.date.fromisoformat(prereg.FRESH_POOL[1])
    earliest_fetch = stamps[0].date() if stamps else None
    implied_start = earliest_fetch - dt.timedelta(days=1825) if earliest_fetch else None
    overlap = implied_start is not None and implied_start <= fresh_end
    return {
        "files": len(stamps),
        "earliest_file_mtime_utc": stamps[0].isoformat() if stamps else None,
        "implied_first_candle_date": implied_start.isoformat() if implied_start else None,
        "first_training_date_in_log": first_train,
        "fresh_pool_end": fresh_end.isoformat(),
        "overlap": bool(overlap),
        "method": "mtime − 1825 日（取得は取得日から遡る）と、学習 log の最初の日付。price の中身は開いていない",
        "caveat": "mtime は copy で変わりうる。log の最初の日付と一致するかで確かめる",
    }


def s0_4() -> dict[str, Any]:
    overlap = pre_r1_overlap()
    #: 日付は必ず parsed date で比べる（文字列比較は repo で禁止されている bypass）
    first_train = overlap["first_training_date_in_log"]
    log_ok = first_train is not None and dt.date.fromisoformat(first_train) > dt.date.fromisoformat(
        prereg.FRESH_POOL[1]
    )
    label = "AMBER" if overlap["overlap"] or not log_ok else "GREEN"
    return {
        "exposures": list(FRESH_EXPOSURES),
        "pre_r1_1825d": overlap,
        "fresh_price_read": "NONE_KNOWN",
        "classification": label,
        "fresh_length_years": round(
            (
                dt.date.fromisoformat(prereg.FRESH_POOL[1])
                - dt.date.fromisoformat(prereg.FRESH_POOL[0])
            ).days
            / 365.25,
            3,
        ),
    }


#: cycle 1 の 4 family と過去の同型（#498 §3・§36）。差を書けない family は数えない。
RENAME_LEDGER: Final[tuple[dict[str, str], ...]] = (
    {
        "family": "F1 条件付き multi-day trend / breakout（H4 → 数日〜数週、barrier exit、vol 状態）",
        "prior": "Round 1 の 1〜6 日 trend / breakout（M15 decision、gross 負）、月次 TSMOM（B′-4）、pre-R1 の intraday Donchian",
        "difference": "H4 の decision・事前固定の barrier exit・vol 状態の条件付け（Round 1 は M15 decision で固定 horizon）。ただし方向の情報源（過去の価格の trend）は同じ",
        "genuine": "PARTIAL",
    },
    {
        "family": "F3 clock / flow（WMR 16:00 fix・月末・Tokyo fix）",
        "prior": "session filter（pre-R1・R1）、Track 3 の session 別 cost",
        "difference": "filter ではなく、機械的な hedging / rebalance の flow を signal にする。repo に同型の検定は無い",
        "genuine": "YES",
    },
    {
        "family": "F4 event の条件付け層（回避・発表後の drift）",
        "prior": "CPI / COT / consensus の signal（#472・#473・#477、支持されず）、MetaDecider の near_event（未 backtest）",
        "difference": "signal ではなく、他 family の上の回避 / 参加の層。回避の層は未検定",
        "genuine": "YES",
    },
    {
        "family": "F5 vol 状態の policy（圧縮後の拡大、H4〜日）",
        "prior": "R1 の ATR gate（breadth だけ）、Round A の ATR 状態、pre-R1 の vol filter",
        "difference": "状態の遷移（圧縮 → 拡大）を entry の条件にする。ATR の水準の gate とは違う",
        "genuine": "YES",
    },
)


def s0_5() -> dict[str, Any]:
    genuine = sum(1 for row in RENAME_LEDGER if row["genuine"] == "YES")
    partial = sum(1 for row in RENAME_LEDGER if row["genuine"] == "PARTIAL")
    bands = prereg.S0_5_BANDS
    label = (
        "GREEN"
        if genuine >= bands["green_min"]
        else "AMBER"
        if genuine >= bands["amber_min"]
        else "RED"
    )
    return {
        "ledger": list(RENAME_LEDGER),
        "genuine_yes": genuine,
        "partial": partial,
        "classification": label,
        "counting_rule": "PARTIAL は本物の差として数えない（保守側）",
    }


__all__ = ["FRESH_EXPOSURES", "RENAME_LEDGER", "pre_r1_overlap", "s0_4", "s0_5"]
