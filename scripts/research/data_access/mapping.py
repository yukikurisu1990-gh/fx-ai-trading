# ruff: noqa: E501 -- mapping prose
"""series mapping と、その **意味の検証**（第 2 裁定 §9 / §10 / §15）。

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

**取得元を変えてよいのは、同じ economic variable を測っている場合だけ**（§15）。
だから mapping は必ず「どの変数を測るつもりか」を持ち、provider の metadata
（title / notes）がその変数の条件を満たすかを **機械的に** 確かめる。

条件は「含むべき語」と「含んではならない語」で書く。後者が効くのは前 cycle の
取り違えそのものである — BoC `V36612` は title に *Treasury Bills* を、ECB `A050100` は
*refinancing* を含んでいた。どちらも総資産ではない。
"""

from __future__ import annotations

import dataclasses
from typing import Any, Final

from scripts.research.data_access.fetch import SEMANTIC_MISMATCH, FetchError


@dataclasses.dataclass(frozen=True)
class Variable:
    """測りたい経済変数と、その判定条件（小文字で照合する）。"""

    name: str
    description: str
    #: どれか 1 組のすべての語を含むこと（組の中は AND、組同士は OR）
    required_any: tuple[tuple[str, ...], ...]
    #: 1 つでも含んだら別の変数である
    forbidden: tuple[str, ...]


VARIABLES: Final[dict[str, Variable]] = {
    "CB_TOTAL_ASSETS": Variable(
        name="CB_TOTAL_ASSETS",
        description="中央銀行の総資産（balance sheet 全体の大きさ）",
        required_any=(("total", "asset"), ("central bank assets",)),
        forbidden=(
            "district",
            "treasury bills",
            "refinancing",
            "gold (",
            "loans",
            "repo",
            "securities held",
            "liabilities and capital:",
        ),
    ),
    "FX_RESERVES": Variable(
        name="FX_RESERVES",
        description="公的外貨準備（reserve assets。**銀行の準備預金ではない**）",
        required_any=(
            ("reserves", "excluding gold"),
            ("reserve assets",),
            ("foreign exchange reserves",),
        ),
        forbidden=(
            "reserve balances",
            "required reserve",
            "bank reserves",
            "depository institutions",
            "total assets",
        ),
    ),
    "GOODS_TRADE_BALANCE": Variable(
        name="GOODS_TRADE_BALANCE",
        description="財の貿易収支（輸出 − 輸入）",
        required_any=(("trade balance",), ("net trade",)),
        forbidden=("current account", "services only", "price index", "volume index"),
    ),
    "HY_CREDIT_SPREAD": Variable(
        name="HY_CREDIT_SPREAD",
        description="米 high-yield 社債の option-adjusted spread",
        required_any=(("high yield", "spread"), ("high yield", "oas")),
        forbidden=("investment grade", "baa", "aaa", "effective yield", "total return"),
    ),
}


def check_semantics(variable: str, evidence: str) -> dict[str, Any]:
    """provider の metadata 文字列が、その変数の条件を満たすか。**満たさなければ例外。**"""
    spec = VARIABLES[variable]
    text = " ".join(evidence.lower().split())
    matched = [group for group in spec.required_any if all(word in text for word in group)]
    violated = [word for word in spec.forbidden if word in text]
    if not matched or violated:
        raise FetchError(
            SEMANTIC_MISMATCH,
            f"{variable}: metadata が定義と一致しない（必要語の一致={matched}、禁止語={violated}）"
            f" — {evidence[:160]}",
        )
    return {"variable": variable, "matched": [list(g) for g in matched], "evidence": evidence[:400]}


@dataclasses.dataclass(frozen=True)
class SeriesMapping:
    """第 2 裁定 §10 が列挙した、mapping に最低限残す項目。"""

    track: str
    currency: str
    variable: str
    provider: str
    tier: int
    series_id: str
    official_title: str
    units: str
    frequency: str
    seasonal_adjustment: str
    coverage_first: str
    coverage_last: str
    publication_lag: str
    revision_behavior: str
    source_url: str
    metadata_url: str
    retrieval_timestamp_utc: str
    content_hash: str
    semantic_check: dict[str, Any]

    def as_record(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


#: 取得経路の優先順位（第 2 裁定 §7）。
TIERS: Final[dict[int, str]] = {
    1: "provider-native official source",
    2: "FRED / ALFRED official distribution endpoint",
    3: "他の public / official / reproducible source",
    4: "public but reputable institutional aggregator",
}

__all__ = ["TIERS", "VARIABLES", "SeriesMapping", "Variable", "check_semantics"]
