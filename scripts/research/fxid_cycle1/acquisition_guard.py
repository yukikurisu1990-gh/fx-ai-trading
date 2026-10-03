# ruff: noqa: E501 -- guard prose
"""pre-2016 FX intraday の取得の guard の仕様（**取得はしない**。合成の test だけで確かめる）。

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

方針（Cycle 1 の裁定 §6）: 保護期間は**取得の request の段階で**除外する。取得後の filter だけで守る方法は採らない。

- 上限: `UPPER_EXCLUSIVE_UTC = 2016-05-31T21:00:00Z`（NY 17:00 = 2016-05-31 の取引日の終わり、夏時間）。
  これより後の bar は 2016-06-01 の取引日（NY 17:00 区切り）に属するので、全て除く。
- 下限: `LOWER_INCLUSIVE_UTC = 2006-01-01T00:00:00Z`。
- 境界は**型と書式を厳密に**検査し、比較は field から作り直した UTC の datetime どうしで行う（文字列の比較・`str` の subclass・緩い書式は拒否）。repo で 3 回抜かれた bypass と同じ形を防ぐ。
- 配布の単位: vendor の時刻帯で見た単位の被覆の終わりを UTC に直し、上限を越える file は **request を出さない**（日付の粒度で比べない）。
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


def _exact_utc(value: object, what: str) -> dt.datetime:
    """`datetime` そのもの（subclass は拒否）で tz 付きのものだけを受け、field から UTC を作り直す。

    呼び出し側の object の比較演算子は使わない（`__ge__` などを上書きした subclass の bypass を防ぐ）。
    `pandas.Timestamp` は subclass なので拒否する（呼び出し側で `to_pydatetime()` に直す）。
    """
    if type(value) is not dt.datetime:  # noqa: E721 - subclass を意図的に拒否する
        raise AcquisitionBoundaryError(f"{what} は datetime そのものだけ: {type(value).__name__}")
    offset = value.utcoffset()
    if type(offset) is not dt.timedelta:  # noqa: E721
        raise AcquisitionBoundaryError(f"{what} に timezone が無い")
    naive = dt.datetime(
        value.year,
        value.month,
        value.day,
        value.hour,
        value.minute,
        value.second,
        value.microsecond,
    )
    return (naive - offset).replace(tzinfo=dt.UTC)


def check_distribution_unit(coverage_start: object, coverage_end_exclusive: object) -> None:
    """年や月などの配布の単位: **vendor の時刻帯で見た被覆の終わり**を UTC に直し、上限を越えるなら request しない。

    例: HistData の 2016-05 の file は EST 固定なので、被覆の終わりは 2016-06-01T00:00 EST = 05:00Z で上限を越える。
    """
    lo = _exact_utc(coverage_start, "単位の開始")
    hi = _exact_utc(coverage_end_exclusive, "単位の終わり")
    if not lo < hi:
        raise AcquisitionBoundaryError("単位の開始 < 終わり でない")
    if lo < LOWER_INCLUSIVE_UTC:
        raise AcquisitionBoundaryError(f"単位が下限より前: {lo}")
    if hi > UPPER_EXCLUSIVE_UTC:
        raise AcquisitionBoundaryError(f"配布の単位（{lo} … {hi}）が保護期間を含む")


def check_response(timestamps: list[object]) -> None:
    """応答の全行を検査する。1 行でも範囲外なら応答全体を拒否する（呼び出し側は何も書かない）。

    空の応答も拒否する（被覆の確認で「無い」と「取れなかった」を区別するため）。
    """
    if len(timestamps) == 0:
        raise AcquisitionBoundaryError("空の応答")
    for ts in timestamps:
        utc = _exact_utc(ts, "応答の行")
        if utc >= UPPER_EXCLUSIVE_UTC or utc < LOWER_INCLUSIVE_UTC:
            raise AcquisitionBoundaryError(f"範囲外の行: {utc}")


__all__ = [
    "LOWER_INCLUSIVE_UTC",
    "UPPER_EXCLUSIVE_UTC",
    "AcquisitionBoundaryError",
    "check_distribution_unit",
    "check_request",
    "check_response",
    "parse_bound",
]
