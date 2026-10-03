# ruff: noqa: E501 -- guard prose
"""pre-2016 FX intraday の取得の guard の仕様（**取得はしない**。合成の test だけで確かめる）。

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

方針（Cycle 1 の裁定 §6）: 保護期間は**取得の request の段階で**除外する。取得後の filter だけで守る方法は採らない。

- 上限: `UPPER_EXCLUSIVE_UTC = 2016-05-31T21:00:00Z`（NY 17:00 = 2016-05-31 の取引日の終わり、夏時間）。
  これより後の bar は 2016-06-01 の取引日（NY 17:00 区切り）に属するので、全て除く。
- 下限: `LOWER_INCLUSIVE_UTC = 2006-01-01T00:00:00Z`。
- 境界は**型と書式を厳密に**検査する（文字列の比較・`str` の subclass・緩い書式は拒否）。repo で 3 回抜かれた bypass と同じ形を防ぐ。
- 配布の単位: 単位の被覆の終わりが上限を越える file（年や月の file で 2016 年 6 月を含むもの）は、**request を出さない**。
- 応答の検査: 応答の中に上限以上の timestamp が 1 行でもあれば、**応答全体を捨てて何も書かない**（部分的な保存もしない）。
"""

from __future__ import annotations

import datetime as dt
from typing import Final

UPPER_EXCLUSIVE_UTC: Final[dt.datetime] = dt.datetime(2016, 5, 31, 21, 0, tzinfo=dt.UTC)
LOWER_INCLUSIVE_UTC: Final[dt.datetime] = dt.datetime(2006, 1, 1, 0, 0, tzinfo=dt.UTC)


class AcquisitionBoundaryError(ValueError):
    """保護期間に掛かる、または境界が曖昧な request / 応答。"""


def parse_bound(value: object) -> dt.datetime:
    """厳密な `YYYY-MM-DDTHH:MM:SSZ` だけを受ける。型は `str` そのもの（subclass は拒否）。"""
    if type(value) is not str:  # noqa: E721 - subclass を意図的に拒否する
        raise AcquisitionBoundaryError(f"境界は str そのものだけ: {type(value).__name__}")
    if (
        len(value) != 20
        or value[4] != "-"
        or value[7] != "-"
        or value[10] != "T"
        or value[-1] != "Z"
    ):
        raise AcquisitionBoundaryError(f"境界は厳密な YYYY-MM-DDTHH:MM:SSZ だけ: {value!r}")
    try:
        return dt.datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.UTC)
    except ValueError as error:
        raise AcquisitionBoundaryError(f"日付として読めない: {value!r}") from error


def check_request(start: object, end_exclusive: object) -> tuple[dt.datetime, dt.datetime]:
    """request を出す前の検査。parse した datetime どうしで比べる。"""
    lo = parse_bound(start)
    hi = parse_bound(end_exclusive)
    if lo < LOWER_INCLUSIVE_UTC:
        raise AcquisitionBoundaryError(f"下限より前: {lo}")
    if hi > UPPER_EXCLUSIVE_UTC:
        raise AcquisitionBoundaryError(f"上限（{UPPER_EXCLUSIVE_UTC}）を越える: {hi}")
    if not lo < hi:
        raise AcquisitionBoundaryError("start < end でない")
    return lo, hi


def check_distribution_unit(unit_start: dt.date, unit_end_inclusive: dt.date) -> None:
    """年や月などの配布の単位: その単位の被覆が上限の日（2016-05-31）を越えるなら request しない。"""
    if unit_end_inclusive > UPPER_EXCLUSIVE_UTC.date():
        raise AcquisitionBoundaryError(
            f"配布の単位（{unit_start} … {unit_end_inclusive}）が保護期間を含む"
        )


def check_response(timestamps: list[dt.datetime]) -> None:
    """応答の全行を検査する。1 行でも範囲外なら応答全体を拒否する（呼び出し側は何も書かない）。"""
    for ts in timestamps:
        if ts.tzinfo is None or ts.utcoffset() is None:
            raise AcquisitionBoundaryError("timezone の無い timestamp")
        if ts >= UPPER_EXCLUSIVE_UTC or ts < LOWER_INCLUSIVE_UTC:
            raise AcquisitionBoundaryError(f"範囲外の行: {ts}")


__all__ = [
    "LOWER_INCLUSIVE_UTC",
    "UPPER_EXCLUSIVE_UTC",
    "AcquisitionBoundaryError",
    "check_distribution_unit",
    "check_request",
    "check_response",
    "parse_bound",
]
