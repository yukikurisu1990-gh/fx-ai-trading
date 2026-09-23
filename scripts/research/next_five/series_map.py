# ruff: noqa: E501 -- mapping prose
"""凍結した 5 本の **exact series mapping**（2026-09-22 第 2 裁定 §9 / §15 / §16 / §18–§22）。

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

**series code は名前から推測していない。** すべて provider の metadata
（ALFRED の series ページ / BoJ の getMetadata / SNB の dimensions / BoC の group /
Fed H.4.1 の annotation）で title・単位・頻度を確かめ、`data_access.mapping.check_semantics`
が変数の定義に合うことを機械的に確認したものだけを置いてある。
**alpha は 1 本も見ていない。**

lag の規則は 2 種類ある:

- `business_days` — 日次・週次の series。観測日の n 営業日後から使う
- `month_end_offset` — 月次の series（月初の日付で記録される）。**第 m 月の値は
  m+k 月末以降にのみ使う**。月初の日付に営業日の lag を当てると、公表前の値を使う
  look-ahead になる（初版の U2 はそうなっていた — `FREEZE_AMENDMENT_PLUMBING`）
"""

from __future__ import annotations

from typing import Any, Final

#: 改訂の扱い（第 2 裁定 §38）。
CURRENT_VINTAGE_ONLY: Final[str] = "CURRENT_VINTAGE_ONLY_REVISION_CAVEAT"
STOCK_NOT_MATERIALLY_REVISED: Final[str] = "BALANCE_SHEET_STOCK_REVISIONS_RARE_CURRENT_VINTAGE"
MARKET_DATA_NOT_REVISED: Final[str] = "MARKET_DATA_NOT_REVISED"


def _row(
    provider: str,
    tier: int,
    fetcher: str,
    args: dict[str, Any],
    lag: dict[str, Any],
    revision: str,
    why: str,
) -> dict[str, Any]:
    return {
        "provider": provider,
        "tier": tier,
        "fetcher": fetcher,
        "args": args,
        "lag": lag,
        "revision": revision,
        "why_this_route": why,
    }


_ALFRED_WHY_TRADE = (
    "OECD MEI の『International Merchandise Trade Statistics: Trade Balance: Commodities』を "
    "ALFRED（St. Louis Fed の公式配信）から取る。各国統計局を直接たどると通関 / BoP の定義が国ごとに"
    "混ざるので、**8 通貨を 1 つの定義で揃えられる経路**を選んだ。fred.stlouisfed.org は本環境から"
    "timeout するが、同じ St. Louis Fed の alfred.stlouisfed.org は届く"
)
_ALFRED_WHY_RESERVES = (
    "IMF 由来の『Reserves Excluding Gold』を ALFRED から取る。**全通貨を同じ定義で揃えられる**。"
    "銀行の準備預金（reserve balances）とは別物であることを意味検証で確かめてある"
)

SERIES_MAP: Final[dict[str, dict[str, dict[str, Any]]]] = {
    #: U1 / S29 — 財の貿易収支（自国通貨、季節調整済み、月次）
    "U1": {
        currency: _row(
            "Federal Reserve Bank of St. Louis (ALFRED) / OECD MEI",
            2,
            "alfred",
            {"series_id": series_id},
            {"kind": "month_end_offset", "months": 2},
            CURRENT_VINTAGE_ONLY,
            _ALFRED_WHY_TRADE,
        )
        for currency, series_id in {
            "USD": "XTNTVA01USM664S",
            "JPY": "XTNTVA01JPM664S",
            "GBP": "XTNTVA01GBM664S",
            "CAD": "XTNTVA01CAM664S",
            "AUD": "XTNTVA01AUM664S",
            "NZD": "XTNTVA01NZM664S",
            "CHF": "XTNTVA01CHM664S",
            #: 配信が 2022-12 で終わっている（OECD MEI の euro area 系列の廃止）
            "EUR": "XTNTVA01EZM664S",
        }.items()
    },
    #: U2 / S25 — 中央銀行の総資産
    "U2": {
        "USD": _row(
            "Board of Governors of the Federal Reserve System (H.4.1)",
            1,
            "fed_h41",
            {"series_name": "RESPPA_N.WW"},
            {"kind": "business_days", "n": 2},
            STOCK_NOT_MATERIALLY_REVISED,
            "Fed の一次配信。H.4.1 の annotation『Assets: Total Assets: Total assets: Wednesday level』で確認。"
            "District 別の RESPPA_Fxx は意味検証の禁止語（district）で除外される",
        ),
        "JPY": _row(
            "Bank of Japan",
            1,
            "boj",
            {"db": "BS01", "code": "MABJMTA"},
            {"kind": "month_end_offset", "months": 2},
            STOCK_NOT_MATERIALLY_REVISED,
            "BoJ の一次配信。getMetadata の名称『Bank of Japan Accounts/Assets/Total』で確認",
        ),
        "CHF": _row(
            "Swiss National Bank",
            1,
            "snb_cube",
            {"cube": "snbbipo", "item": "T0"},
            {"kind": "month_end_offset", "months": 2},
            STOCK_NOT_MATERIALLY_REVISED,
            "SNB の一次配信。cube snbbipo の dimension 一覧で D0=T0 が『Assets / Total』であることを確認",
        ),
        "CAD": _row(
            "Bank of Canada",
            1,
            "boc_valet",
            {"series_id": "V36651"},
            {"kind": "month_end_offset", "months": 2},
            STOCK_NOT_MATERIALLY_REVISED,
            "BoC の一次配信。group B1_MONTHLY の label『Total assets』で確認。"
            "**前 cycle の推定 V36612 は Treasury Bills で、意味検証が弾く**",
        ),
        "EUR": _row(
            "Federal Reserve Bank of St. Louis (ALFRED) / ECB",
            2,
            "alfred",
            {"series_id": "ECBASSETSW"},
            {"kind": "business_days", "n": 2},
            STOCK_NOT_MATERIALLY_REVISED,
            "ECB の一次配信（ILM dataflow）には**総資産の系列が無く**、個別項目しか公開されていない。"
            "項目を自分で足した合計は『公式の総資産』ではないので作らず、ECB の総資産を配信している "
            "ALFRED の ECBASSETSW（Central Bank Assets for Euro Area）を使う",
        ),
    },
    #: U4 / S31 — 公的外貨準備（金を除く reserve assets、百万 USD、月次）
    "U4": {
        currency: _row(
            "Federal Reserve Bank of St. Louis (ALFRED) / IMF",
            2,
            "alfred",
            {"series_id": series_id},
            {"kind": "month_end_offset", "months": 1},
            CURRENT_VINTAGE_ONLY,
            _ALFRED_WHY_RESERVES,
        )
        for currency, series_id in {
            "USD": "TRESEGUSM052N",
            "JPY": "TRESEGJPM052N",
            "GBP": "TRESEGGBM052N",
            "CAD": "TRESEGCAM052N",
            "AUD": "TRESEGAUM052N",
            "EUR": "TRESEGEZM052N",
        }.items()
    },
    #: U5 / S07 — 米 high-yield 社債 spread（日次）
    "U5": {
        "SPREAD": _row(
            "Federal Reserve Bank of St. Louis (ALFRED) / ICE Data Indices",
            2,
            "alfred",
            {"series_id": "BAMLH0A0HYM2"},
            {"kind": "business_days", "n": 2},
            MARKET_DATA_NOT_REVISED,
            "ICE BofA の OAS は無料の一次配信が無く、FRED / ALFRED が公式の無料配信である。"
            "**ICE の license により配信は 2023-09-25 以降に限られる**（長 span は存在しない）。"
            "IG spread や Baa-Treasury spread は別の risk なので代替しない（第 2 裁定 §22）",
        ),
    },
}

#: 同じ定義で取れなかった通貨と、その理由（代替はしない）。
NOT_MAPPED: Final[dict[str, dict[str, str]]] = {
    "U2": {
        "GBP": "BoE の総資産系列を provider metadata から特定できなかった（IADB はカタログ API を持たない）。推測した code は使わない",
        "AUD": "RBA の統計表が HTTP 403（provider が拒否）",
        "NZD": "RBNZ の統計表が HTTP 403（前 cycle で確認）",
    },
    "U4": {
        "CHF": (
            "ALFRED に TRESEGCHM052N が無い（404）。SNB の balance sheet には外貨投資 / IMF reserve "
            "position / SDR が別項目で載っているが、**それらを足して『準備』を自作するのは semantic "
            "substitution にあたる**ので使わない。U4 が事前に想定していた能動的な準備運用国の 1 つを失う"
        ),
        "NZD": "ALFRED に TRESEGNZM052N が無い（404）",
    },
    "U1": {},
}


def mapped_currencies(track: str) -> tuple[str, ...]:
    return tuple(currency for currency in SERIES_MAP.get(track, {}) if currency != "SPREAD")


__all__ = [
    "CURRENT_VINTAGE_ONLY",
    "MARKET_DATA_NOT_REVISED",
    "NOT_MAPPED",
    "SERIES_MAP",
    "STOCK_NOT_MATERIALLY_REVISED",
    "mapped_currencies",
]
