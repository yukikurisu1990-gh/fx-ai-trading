# ruff: noqa: E501 -- data prose
"""R-A の route だけで seen の M15 bid / ask cache を読み、timeframe に集約する。

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

- 読むのは `prereg.ROUTES` の 3 つの `load(pair)` だけ（それぞれの route の span guard が効く）。
- 全行が 2021-04-26 … 2025-12-28 の中にあることを parsed date で確かめる。1 行でも外にあれば止まる。
- この module は **方向・損益を計算しない**。出すのは bid / ask / mid の bar と spread だけ。
"""

from __future__ import annotations

import datetime as dt
import hashlib
import importlib
from typing import Final

import pandas as pd

from scripts.research.patsd_stage0 import prereg

FIRST: Final[dt.date] = dt.date.fromisoformat(prereg.FIRST_DAY)
LAST: Final[dt.date] = dt.date.fromisoformat(prereg.LAST_DAY)
RULE: Final[dict[str, str]] = {"H1": "1h", "H4": "4h"}


class BoundaryError(AssertionError):
    """R-A の span の外の行。"""


def assert_in_span(ts: pd.Series) -> None:
    days = pd.to_datetime(ts, utc=True).dt.date
    if days.min() < FIRST or days.max() > LAST:
        raise BoundaryError(f"span の外の行がある: {days.min()} … {days.max()}")
    fresh_end = dt.date.fromisoformat(prereg.FRESH_POOL[1])
    if (days <= fresh_end).any():
        raise BoundaryError("fresh pool の日付の行がある")


def load_pair(pair: str) -> pd.DataFrame:
    """3 つの route を連結する（重なりは無い）。"""
    frames = []
    for module_name, first, last in prereg.ROUTES:
        module = importlib.import_module(module_name)
        frame = module.load(pair)
        days = frame["ts"].dt.date
        if days.min() < dt.date.fromisoformat(first) or days.max() > dt.date.fromisoformat(last):
            raise BoundaryError(f"{module_name}: route の宣言 span の外の行がある")
        frames.append(frame)
    out = pd.concat(frames, ignore_index=True).sort_values("ts").reset_index(drop=True)
    if out["ts"].duplicated().any():
        raise BoundaryError(f"{pair}: route の間で timestamp が重なる")
    assert_in_span(out["ts"])
    return out


def content_hash(frame: pd.DataFrame) -> str:
    return hashlib.sha256(
        pd.util.hash_pandas_object(frame, index=False).values.tobytes()
    ).hexdigest()


def aggregate(m15: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    """M15 → H1 / H4 / D（UTC）。側ごとの OHLC、終値時点の spread、rollover を含む bar の印。"""
    if timeframe == "M15":
        out = m15.copy()
        out["close_rollover"] = out["rollover"]
        return out
    key = m15["ts"].dt.floor(RULE[timeframe]) if timeframe in RULE else m15["ts"].dt.floor("1D")
    grouped = m15.groupby(key, sort=True)
    out = pd.DataFrame(
        {
            "mid_o": grouped["mid_o"].first(),
            "mid_h": grouped["mid_h"].max(),
            "mid_l": grouped["mid_l"].min(),
            "mid_c": grouped["mid_c"].last(),
            "spread_close_pips": grouped["spread_close_pips"].last(),
            "close_rollover": grouped["rollover"].last(),
            "any_rollover": grouped["rollover"].any(),
            "pip_size": grouped["pip_size"].last(),
            "n_m15": grouped.size(),
        }
    )
    out.index.name = "ts"
    return out.reset_index()


__all__ = ["BoundaryError", "aggregate", "assert_in_span", "content_hash", "load_pair"]
