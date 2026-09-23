# ruff: noqa: E501 -- policy prose
"""**保護期間は request の段階で外す**（2026-09-24 裁定 §6–§8、§34 — D-5 を受けた prospective rule）。

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

next-five の取得（D-5）は、期間を request に入れられない endpoint（Fed H.4.1 の一括 zip、
SNB cube、BoJ の全系列、Fed の ne-press.json）から **保護期間を含む応答をメモリで parse し、
保存前に切り落とした**。値は保存も計算もしていないが、「除外は request の性質」には届いていない。

この module は、それ以後の取得すべてに次を課す。

1. **期間を request に入れられる endpoint では、保護期間を request そのものから外す。**
   download / parse の後で filter する方法は使わない。
2. **一括配信しか無い endpoint（BULK_ONLY）は使わない。** 唯一の公式 source で、仮説に不可欠で、
   意味の同じ代替が無い場合でも、**Human + ChatGPT の明示承認（`APPROVED_BULK_EXCEPTIONS`）が
   記録されるまで取得しない。** 現在の承認は 0 件。
3. **参照期間で判定する。** 月次の値は月初の日付で記録されるが、中身はその月全体の集計である。
   2016-06-01 stamp（2016 年 6 月分）は fresh pool の内容なので、request の終端は
   2016-05-01 にする（next-five の C-4 が読む側で補った穴を、request 側で塞ぐ）。
4. **provider が bound を無視したら捨てる。** 応答に request 外の stamp が 1 つでもあれば
   保存せずに止める（`ProviderIgnoredBoundError`）。これは filter ではなく拒否である。

FX の fresh pool を読むこととは別の問題として扱う（裁定 §8）。ここで守るのは
**外部 series の保護暦日**であり、FX panel の保護は `top_five.sources` が持つ。
"""

from __future__ import annotations

import datetime as dt
from typing import Final

import pandas as pd

#: 保護暦日。**外部 series の参照期間がここに 1 日でも掛かったら request しない。**
FRESH_POOL: Final[tuple[dt.date, dt.date]] = (dt.date(2016, 6, 2), dt.date(2021, 4, 26))
#: 最後の seen 日の翌日以降（development 末尾 2 日・historical OOS slice・dead window・
#: forward epoch をまとめて保守側に外す）。
AFTER_LAST_SEEN: Final[dt.date] = dt.date(2025, 12, 27)

#: request してよい暦日の区間（両端を含む）。1990 年以前は必要が無いので取らない。
SEEN_CALENDAR: Final[tuple[tuple[dt.date, dt.date], ...]] = (
    (dt.date(1990, 1, 1), dt.date(2016, 6, 1)),
    (dt.date(2021, 4, 27), dt.date(2025, 12, 26)),
)

#: 観測 1 つが覆う参照期間の種類。
POINT: Final[str] = "POINT"  # 日次の値・その日時点の残高
WEEK_ENDING: Final[str] = "WEEK_ENDING"  # その日で終わる 1 週間の集計
MONTH: Final[str] = "MONTH"  # 月初日付で記録される月の集計
QUARTER: Final[str] = "QUARTER"

#: 期間を request に入れられない endpoint。**承認が記録されるまで使わない。**
BULK_ONLY_PROVIDERS: Final[dict[str, str]] = {
    "fed_h41": "H.4.1 は一括 zip のみ（Output.aspx?rel=H41&filetype=zip）",
    "snb_cube": "SNB data cube の CSV は全期間を返す",
    "boj_full_series": "next-five で使った getDataCode は期間を指定していなかった（startDate/endDate の対応は未確認）",
    "fed_press_json": "Fed の ne-press.json は全記事を返す",
    "bis_bulk_zip": "BIS の WS_*_csv_flat.zip は全期間",
}

#: Human + ChatGPT が明示承認した bulk-only の例外。**現在 0 件。**
APPROVED_BULK_EXCEPTIONS: Final[dict[str, str]] = {}


class ProtectedRequestError(ValueError):
    """request の参照期間が保護暦日に掛かっている。"""


class BulkOnlySourceRefusedError(PermissionError):
    """期間を request に入れられない endpoint で、承認も無い。"""


class ProviderIgnoredBoundError(ValueError):
    """provider が request の期間を守らなかった。**応答は保存しない。**"""


def as_day(value: object, *, field: str) -> dt.date:
    """厳密な `YYYY-MM-DD` の `str` だけを受け、**parse した date で比較する。**

    本 repo は `"2016-06"` のような曖昧な綴りと、`__lt__` を上書きした `str` subclass で
    bound を抜かれた記録がある。型は `str` そのものに限る。
    """
    if type(value) is not str or len(value) != 10 or value[4] != "-" or value[7] != "-":
        raise ValueError(f"{field} must be an exact YYYY-MM-DD str, not {value!r}")
    try:
        return dt.date.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"{field} must be an exact YYYY-MM-DD str, not {value!r}") from error


def reference_period(stamp: dt.date, kind: str) -> tuple[dt.date, dt.date]:
    """1 つの観測が覆う暦日の区間。"""
    if kind == POINT:
        return stamp, stamp
    if kind == WEEK_ENDING:
        return stamp - dt.timedelta(days=6), stamp
    if kind == MONTH:
        period = pd.Period(stamp, freq="M")
        return period.start_time.date(), period.end_time.date()
    if kind == QUARTER:
        period = pd.Period(stamp, freq="Q")
        return period.start_time.date(), period.end_time.date()
    raise ValueError(f"unknown reference-period kind {kind!r}")


def touches_protected(first: dt.date, last: dt.date) -> bool:
    """暦日区間が保護暦日に 1 日でも掛かるか。"""
    lo, hi = FRESH_POOL
    return (first <= hi and last >= lo) or last >= AFTER_LAST_SEEN


def check_request(first: str, last: str, *, kind: str) -> tuple[dt.date, dt.date]:
    """request しようとしている **stamp の範囲** が、参照期間まで含めて保護暦日を避けているか。

    `first` / `last` は provider に渡す stamp の下限・上限。月次なら月初の日付を渡す。
    """
    start = as_day(first, field="first")
    end = as_day(last, field="last")
    if end < start:
        raise ProtectedRequestError(f"request の終端 {end} が始端 {start} より前")
    covered_first = reference_period(start, kind)[0]
    covered_last = reference_period(end, kind)[1]
    inside = any(lo <= covered_first and covered_last <= hi for lo, hi in SEEN_CALENDAR)
    if not inside or touches_protected(covered_first, covered_last):
        raise ProtectedRequestError(
            f"request {start} … {end}（{kind}、参照期間 {covered_first} … {covered_last}）は "
            "seen 暦日の 1 区間に収まっていない。保護暦日は request から外す"
        )
    return start, end


def seen_request_windows(kind: str) -> tuple[tuple[str, str], ...]:
    """kind ごとに、request に渡してよい stamp の範囲（seen 暦日の 2 区間）。

    月次は参照期間全体が seen に入る月だけ: long は 1990-01 … 2016-05、recent は 2021-05 … 2025-11。
    """
    if kind == POINT:
        windows = (("1990-01-01", "2016-06-01"), ("2021-04-27", "2025-12-26"))
    elif kind == WEEK_ENDING:
        windows = (("1990-01-07", "2016-06-01"), ("2021-05-03", "2025-12-26"))
    elif kind == MONTH:
        windows = (("1990-01-01", "2016-05-01"), ("2021-05-01", "2025-11-01"))
    elif kind == QUARTER:
        windows = (("1990-01-01", "2016-01-01"), ("2021-07-01", "2025-07-01"))
    else:
        raise ValueError(f"unknown reference-period kind {kind!r}")
    for first, last in windows:
        check_request(first, last, kind=kind)
    return windows


def assert_provider_allowed(provider: str) -> None:
    """bulk-only の provider は、承認が記録されていなければ呼ぶ前に止める。"""
    if provider in BULK_ONLY_PROVIDERS and provider not in APPROVED_BULK_EXCEPTIONS:
        raise BulkOnlySourceRefusedError(
            f"{provider}: {BULK_ONLY_PROVIDERS[provider]}。期間を request に入れられないので、"
            "Human + ChatGPT の例外承認が記録されるまで取得しない（裁定 §7 / §34）"
        )


def assert_response_within(
    stamps: pd.DatetimeIndex, first: dt.date, last: dt.date, *, label: str
) -> None:
    """応答の stamp が request の範囲に収まっているか。**外れたら保存せずに止める。**"""
    days = pd.DatetimeIndex(stamps).date
    stray = [day for day in days if day < first or day > last]
    if stray:
        raise ProviderIgnoredBoundError(
            f"{label}: provider が request の期間 {first} … {last} を守らず、外の stamp を "
            f"{len(stray)} 件返した（最初 {stray[:3]}）。応答は保存しない"
        )


__all__ = [
    "AFTER_LAST_SEEN",
    "APPROVED_BULK_EXCEPTIONS",
    "BULK_ONLY_PROVIDERS",
    "FRESH_POOL",
    "MONTH",
    "POINT",
    "QUARTER",
    "SEEN_CALENDAR",
    "WEEK_ENDING",
    "BulkOnlySourceRefusedError",
    "ProtectedRequestError",
    "ProviderIgnoredBoundError",
    "as_day",
    "assert_provider_allowed",
    "assert_response_within",
    "check_request",
    "reference_period",
    "seen_request_windows",
    "touches_protected",
]
