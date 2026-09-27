# ruff: noqa: E501 -- audit prose
"""financing accounting の監査（2026-09-24 第 3 裁定 §5–§13）。

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

問いは 3 つ:

1. これまでの backtest の `net` は何を含んでいたか（spread・slippage・commission・rollover・
   financing・swap・金利調整・triple-day・long / short の非対称・pair ごとの financing）。
2. OANDA の financing の過去の値を、公開情報だけで取れるか。
3. financing を入れていないことが、過去の track の経済的な符号を変えうるか（**再実行はしない**）。

**financing は alpha ではない**（§7）。signal を変えず、同じ position に金利の受け払いを足し引きする
会計である。実際の OANDA financing の履歴が無いので、近似は `APPROXIMATE_RESEARCH_FINANCING` と呼び、
**actual OANDA financing とは呼ばない**（§11）。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Final

from scripts.research.acquisition_safety import write_provenance

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[3]
#: v1 は判定式の向きの誤り・M11 / M01 の欠落、v2 は method の文言が古い式のまま（re-audit R-2）。
RECORD: Final[Path] = REPO_ROOT / "artifacts/research/usd_factor_financing/financing_audit_v3.json"

# ----------------------------------------------------------------------
# 1. 既存の net の定義（数値は書き換えない。名前を正確にする。§6）
# ----------------------------------------------------------------------
NET_EX_FINANCING: Final[str] = "NET_EX_TRANSACTION_COSTS_EXCLUDING_FINANCING"
NET_APPROX: Final[str] = "NET_INCLUDING_APPROXIMATE_INTEREST_DIFFERENTIAL_AND_ASSUMED_MARKUP"

#: 共通の transaction cost 規約（`continuous_portfolio.construction`）。
TRANSACTION_COST_CONVENTION: Final[dict[str, str]] = {
    "spread": "charged_cost = Σ|Δexposure| × 1.703 bp（片道）。Track 3 で実測した market order の round trip 2.69 / 2.47 bp の中点 2.58 bp を基にした保守的な換算",
    "slippage": "spread の実測（all-bars の約定）に含まれる。別の項は無い",
    "commission": "無し（OANDA の retail は spread 課金。commission 口座は想定していない）",
    "rollover": "無し。exploratory_m15 系は rollover の bar で新規に建てないだけで、rollover の費用は計上していない",
    "financing_swap_interest_adjustment": "**無し**（mechanism redesign cycle だけが近似を入れた）",
    "triple_day": "無し（financing を入れていないので該当しない）",
    "long_short_asymmetry": "無し",
    "pair_specific_financing": "無し",
}

NET_DEFINITIONS: Final[dict[str, dict[str, str]]] = {
    "exploratory_m15 Round 1 / Round 2 / 補足再現 / momentum": {
        "net": NET_EX_FINANCING,
        "note": "bar の bid / ask spread。保有は M15〜数日で financing の影響は小さいが 0 ではない",
    },
    "Track 1 continuous currency portfolio（PR #481/#482）": {
        "net": NET_EX_FINANCING,
        "note": "financing は P&L から除外、政策金利の carry accrual を診断として報告（年 0.085%）",
    },
    "#471 economic edge（carry）": {
        "net": "SPOT_PLUS_RESEARCH_CARRY_POLICY_RATES_MINUS_COST",
        "note": "spot・carry・cost を分けて計上。carry は政策金利の research carry で broker financing ではない",
    },
    "T-R 市場利回り repricing（PR #485 / r2）": {"net": NET_EX_FINANCING, "note": "—"},
    "T-V 実質為替 valuation（PR #486–#488）": {
        "net": NET_EX_FINANCING,
        "note": "carry_exposure を診断として測った（除外した carry の向き）",
    },
    "Top-Five T1〜T5（PR #490）": {
        "net": NET_EX_FINANCING,
        "note": "panel は spot only（carry_leg_absent_on_both_spans）",
    },
    "next-five U1〜U5（PR #493）": {"net": NET_EX_FINANCING, "note": "Top-Five と同じ panel"},
    "carry の基準は cycle ごとに違う（review O-8）": {
        "net": "—",
        "note": "Track 1 は当日の政策金利 × x·r（診断のみ）、#471 は政策金利の research carry、mechanism redesign は lag 付き 3 か月金利 × pair operator、今回の修正版は当時の政策金利（primary）と lag 付き 3 か月金利（感度）",
    },
    "mechanism redesign M11 / M01 / M10（PR #494）": {
        "net": NET_APPROX,
        "note": "3 か月銀行間金利差の carry 近似 − 仮定 markup 0.25%/年。実際の OANDA financing ではない",
    },
}

# ----------------------------------------------------------------------
# 2. OANDA の financing の公開情報（§8–§10）
# ----------------------------------------------------------------------
FINANCING_SOURCE_AUDIT: Final[dict[str, Any]] = {
    "status": "PUBLIC_FINANCING_HISTORY_NOT_AVAILABLE_WITHOUT_AUTHENTICATED_BROKER_ACCESS",
    "evidence_strength": (
        "PUBLIC_FINANCING_HISTORY_NOT_FOUND_IN_LIMITED_ANONYMOUS_PROBE。404 は推測した URL が外れただけで、"
        "公開の過去履歴が存在しないことの証明ではない（review R-3）。現在値の公開ページは存在する（今回は読まない）"
    ),
    "evidence": (
        "#472 Stage D（exogenous/financing.py）の anonymous probe 6 件: OANDA の financing-rates ページ（US / 非 US）は 404、"
        "historical rates ページは 404、v20 developer 文書は 200 だが実現 financing を持つ account endpoint は token 必須、"
        "CME settlements は 403、BIS の bulk に swap point は無い。**公開の過去 financing の記録は見つかっていない**"
    ),
    "not_probed_again_this_cycle": (
        "OANDA Japan / OANDA の現在のスワップポイント・financing rate の公開ページは**今回取得していない**。"
        "表示されるのは 2026 年（forward epoch）の値で、第 3 裁定 §24 の保護情報（observation values）に当たる。"
        "また現在の値から過去を逆算することは §10 で禁じられている"
    ),
    "items": {
        "pair": "公開の履歴無し",
        "long_financing / short_financing": "公開の履歴無し（現在値のみ公開、今回は読まない）",
        "date": "—",
        "rate / points / percentage definition": "OANDA の v20 は per-instrument の financing rate（年率、long / short 別）を account 文脈で返す。公開の過去値は無い",
        "conversion method": "account 通貨への換算は account の設定に依存",
        "triple-day rule": "OANDA は保有時間に比例して日次で課金（週末分を含む暦日の accrual）とされる。公式の過去の運用を公開情報で検証できていない",
        "holidays": "同上",
        "markup": "benchmark 金利に broker の markup を上乗せ・差し引き。markup の値は公開の履歴が無い",
        "account / server / instrument dependency": "account の区分・法人（OANDA Japan / 他地域）で異なりうる",
    },
    "human_return_item": "実際の financing 履歴には認証付きの broker access（自分の口座の取引履歴）が要る。**接続していない**",
}

#: 近似の設計（§11）。**actual OANDA financing とは呼ばない。**
APPROXIMATION: Final[dict[str, Any]] = {
    "name": "APPROXIMATE_RESEARCH_FINANCING",
    "interest_differential": (
        "pair ごとの 3 か月銀行間金利の差（base − quote）に spot と同じ pair book 演算子を掛け、決定日の exposure と内積を取り、"
        "暦日 / 365 で accrual（週末は暦日で入る — triple-day の総量と同じ）。金利が無い日は BIS 政策金利、BoJ のゼロ金利・"
        "量的緩和期は 0%（mechanism redesign と同じ規則）"
    ),
    "markup_band_annual_per_unit_currency_gross": (0.0, 0.0025, 0.005, 0.01),
    "central_markup": 0.0025,
    "zero_financing_row": "spot − spread（NET_EX_TRANSACTION_COSTS_EXCLUDING_FINANCING）も必ず並べる",
    "asymmetry": "long / short の非対称は markup を |exposure| に対称に掛けることで近似する（実際の bid / offer の非対称は再現していない）",
    "rule": "**primary の経済判定を、都合のよい 1 点の近似だけで決めない**。markup band の中で総合 P&L の符号が変わるなら FINANCING_NOT_DECISION_GRADE",
}

# ----------------------------------------------------------------------
# 3. financing を入れていないことが過去の verdict を変えうるか（signal-blind、§12–§13）
# ----------------------------------------------------------------------
#: 3 か月金利の cross-section 標準偏差（%、span の日平均）。`signals.carry_rate_panel` から測った。
RATE_DISPERSION_SD: Final[dict[str, float]] = {"long": 1.75, "recent": 1.378}
#: 和がゼロの book の向きが金利の順位と無関係なときの、|x·r| の典型的な大きさ ≈ 0.38 × gross × sd。
#: （8 通貨で ±G/8 の book の ||x||₂ = G/√8、相関の典型値 1/√7 から）。**向きを知らない上での典型値**。
CARRY_SCALE_COEF: Final[float] = 0.38
MARKUP_HIGH: Final[float] = 0.01


def _row(
    name: str, span: str, net: float, gross: float, *, measured_carry: float | None = None
) -> dict[str, Any]:
    typical_carry = CARRY_SCALE_COEF * gross * RATE_DISPERSION_SD[span] / 100.0
    markup_range = (0.0025 * gross, MARKUP_HIGH * gross)
    if measured_carry is not None:
        #: 測った carry があれば、それに markup 0〜1% を足し引きして符号を見る
        worst = net + measured_carry - markup_range[1]
        best = net + measured_carry
        could_flip = (worst > 0) != (net > 0) or (best > 0) != (net > 0)
    elif net > 0:
        #: 正の net は、不利な carry と最大の markup で負になりうるか（review R-1: 向きを見る）
        could_flip = net < typical_carry + markup_range[1]
    else:
        #: 負の net は、有利な carry と markup 0 で正になりうるか（markup は負を深めるだけ）
        could_flip = abs(net) < typical_carry
    return {
        "track": name,
        "span": span,
        "net_annual_ex_financing": round(net, 5),
        "mean_currency_gross": round(gross, 3),
        "markup_cost_band": [round(markup_range[0], 5), round(markup_range[1], 5)],
        "typical_carry_scale": round(typical_carry, 5),
        "measured_carry": measured_carry,
        "financing_could_plausibly_change_economic_sign": bool(could_flip),
    }


def impact_audit() -> list[dict[str, Any]]:
    def load(path: str) -> dict[str, Any]:
        return json.loads((REPO_ROOT / path).read_text(encoding="utf-8"))

    rows: list[dict[str, Any]] = []
    top = load("artifacts/research/top_five/development.json")["results"]
    for key, result in top.items():
        metrics = result.get("metrics")
        if not metrics:
            continue
        span = "long" if "_long" in key else "recent"
        rows.append(
            _row(
                f"Top-Five {key}",
                span,
                metrics["net_annual_return"],
                metrics["portfolio_gross_leverage"],
            )
        )
    nf = load("artifacts/research/next_five/development_run4.json")["results"]
    for key, result in nf.items():
        metrics = result.get("metrics")
        if not metrics:
            continue
        span = "long" if key.endswith("_long") else "recent"
        rows.append(
            _row(
                f"next-five {key}",
                span,
                metrics["net_annual_return"],
                metrics["portfolio_gross_leverage"],
            )
        )
    for path, book, name in (
        ("artifacts/research/market_yields/development.json", "A_yield_repricing", "T-R A"),
        ("artifacts/research/market_yields/development_r2.json", "B_slow_rate_state", "T-R2 B"),
        ("artifacts/research/valuation/development.json", "A_valuation", "T-V A"),
    ):
        summary = load(path)["books"][book]["summary"]
        span = "long" if name.startswith("T-V") else "recent"
        rows.append(_row(name, span, summary["net_annual_return"], summary["mean_currency_gross"]))
    #: 直前 cycle の正の判定（review R-2）。記録にある carry 近似と markup 0.25% を使って、
    #: markup を 0〜1% に動かしたときの符号を見る（carry は lag 付き 3 か月金利の近似）
    mr = load("artifacts/research/mechanism_redesign/development.json")["results"]
    for key in ("M11_long", "M01_long"):
        result = mr[key]
        decomposition = result["pnl_decomposition"]
        net_ex = decomposition["annual_spot_gross"] - decomposition["annual_spread_cost"]
        rows.append(
            _row(
                f"mechanism redesign {key}（net は spot − spread）",
                "long",
                net_ex,
                result["metrics"]["portfolio_gross_leverage"],
                measured_carry=decomposition["annual_carry"],
            )
        )
    track1 = load("artifacts/research/continuous_portfolio/development.json")
    summary = track1["primary"]["summary"]
    rows.append(
        _row(
            "Track 1 primary",
            "recent",
            summary["net_annual_return"],
            summary["mean_currency_gross"],
            measured_carry=track1["carry_diagnostic_primary"]["annual_carry_accrual"],
        )
    )
    return rows


def run() -> dict[str, Any]:
    rows = impact_audit()
    flagged = [row for row in rows if row["financing_could_plausibly_change_economic_sign"]]
    return {
        "transaction_cost_convention": TRANSACTION_COST_CONVENTION,
        "net_definitions": NET_DEFINITIONS,
        "financing_source_audit": FINANCING_SOURCE_AUDIT,
        "approximation": APPROXIMATION,
        "impact_audit": {
            "method": (
                "signal-blind: 記録済みの年率 net（financing 抜き）と平均通貨 gross だけを使う。position の向きは記録に無いので、"
                "carry は『向きが金利と無関係なときの典型値 c = 0.38 × gross × 金利の cross-section sd』。"
                "net > 0 なら net < c + 1%·gross（不利な carry と最大 markup で負になりうる）、net ≤ 0 なら |net| < c"
                "（有利な carry と markup 0 で正になりうる）で flag。測った carry がある track（Track 1・mechanism redesign の "
                "M11 / M01）は、それに markup 0〜1%·gross を足し引きして符号を見る。**再実行はしない**"
            ),
            "rows": rows,
            "flagged": [
                f"{r['track']}（net {r['net_annual_ex_financing']:+.4f}、carry 典型 {r['typical_carry_scale']:.4f}）"
                for r in flagged
            ],
        },
    }


def main() -> int:
    payload = run()
    RECORD.parent.mkdir(parents=True, exist_ok=True)
    written = write_provenance(RECORD, payload)
    for row in payload["impact_audit"]["rows"]:
        print(
            row["track"],
            row["net_annual_ex_financing"],
            row["mean_currency_gross"],
            row["typical_carry_scale"],
            row["financing_could_plausibly_change_economic_sign"],
            file=sys.stderr,
        )
    print(f"written {RECORD} {written}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
