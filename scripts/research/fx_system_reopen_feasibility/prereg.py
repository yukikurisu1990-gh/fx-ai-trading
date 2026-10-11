# ruff: noqa: E501 -- preregistration prose
"""P1 の事前登録（**計算の前に commit する**）。component の universe・scenario・判定の規則を固定する。

承認: Human + ChatGPT の指示「FX System Architecture — Decision Freeze + P1/P2 Fast-Track」（2026-10-08）の、P1 / 条件付きの P2 に限った一度限りの HOLD の例外（`docs/governance/fx_system_architecture_ruling_2026_10.md` §6）。

効果の値は、全て repo に commit 済みの記録（主に #503 `docs/research/fxid_final_mechanism_feasibility_review_2026_10.md` §13 と、§15 の判定）から取る。新しい価格 data・新しい文献の候補は使わない。

単位: 年率の net Sharpe（真の値の想定）。retail の OANDA の cost（往復 spread + slippage 0.5 bp）の後。
"""

from __future__ import annotations

from typing import Final

# ---------------------------------------------------------------------------
# 1. mechanism family の棚卸し（同じ economic source を strategy 名で複数に数えない）
# ---------------------------------------------------------------------------
#: family -> (過去の判定, 理由, P1 での扱い)。"ELIGIBLE" 以外は全ての scenario で寄与 0（復活させない）
FAMILIES: Final[dict[str, tuple[str, str, str]]] = {
    "F1_dollar_intraday_W_fixing_inventory": (
        "ECONOMICALLY_UNATTRACTIVE（#503）／ HOLD の裁定 §6 の near-miss",
        "EUR の欧州の朝・JPY の仲値の後・EUR の ECB の後を、同じ W 字の別の窓として 1 family にする",
        "ELIGIBLE_AS_PRESERVED_NEAR_MISS",
    ),
    "F2_local_currency_trading_hours_customer_flow": (
        "C03 NO_DECISION_GRADE_PASS_REGION／H-002 CLOSED（gate として）／#503 で programme の要求に不足",
        "EUR の朝の窓は F1 と同じ時間・同じ符号で、economic source が重なる（B&R の顧客の flow と KMW の dealer の在庫は同じ現象の 2 つの説明）",
        "MERGED_INTO_F1",
    ),
    "F3_institutional_order_flow": (
        "NOT_IMPLEMENTABLE_WITH_AVAILABLE_INFORMATION（#503）",
        "非公開の flow",
        "LOCKED",
    ),
    "F4_month_end_equity_hedging": (
        "DUPLICATE_OF_PREVIOUS_RESEARCH（C05 / S21 停止）・ECONOMICALLY_UNATTRACTIVE（#503 §13d）",
        "年 12 回、cost に負ける",
        "LOCKED",
    ),
    "F5_post_fix_reversal": (
        "NOT_IMPLEMENTABLE_WITH_AVAILABLE_INFORMATION（#503）",
        "効果は 1〜15 分の中",
        "LOCKED",
    ),
    "F6_tokyo_fixing_spike_gotobi": (
        "NOT_IMPLEMENTABLE / INSUFFICIENT_EVIDENCE（#503）",
        "秒単位の spike、長い drift は査読なし。数時間の窓は F1 に含む",
        "LOCKED",
    ),
    "F7_macro_announcement_repricing": (
        "INSUFFICIENT_EVIDENCE / DUPLICATE（#473 の検出力のある帰無、S2 保留）",
        "調整は数分",
        "LOCKED",
    ),
    "F8_intraday_momentum": (
        "INSUFFICIENT_EVIDENCE / DUPLICATE（S1 除外、VR < 1）",
        "測られた反転と逆",
        "LOCKED",
    ),
    "F9_short_horizon_mean_reversion": (
        "Round 1 で net 負、B′ の構造は損益分岐の 6〜16%（#469 / #470）、multi-day の反転は dropped（#465〜#467）",
        "cost で回収できない",
        "LOCKED",
    ),
    "F10_session_transition": (
        "C03 NO_DECISION_GRADE_PASS_REGION",
        "経済性の机上の判定で不合格",
        "LOCKED",
    ),
    "F11_option_cut": (
        "#474 の cell（方向は未検定、毎日は損益分岐 IR 4〜59）",
        "経済的に不可能に近い",
        "LOCKED",
    ),
    "F12_carry": (
        "CARRY_EDGE_NOT_SUPPORTED（#471）／#497 で LONG_TERM_HOLD",
        "carry は rollover をまたいで初めて生じ、当日決済では 0",
        "LOCKED",
    ),
    "F13_cross_sectional_or_ts_momentum": (
        "#497 で hedge の役だけ、B′-4 の月次 TSMOM は負",
        "日次以上の horizon で当日決済の範囲外",
        "LOCKED",
    ),
    "F14_classical_premia_composite": (
        "#497 LONG_TERM_HOLD（TC-net 0.127、carry 99%）",
        "F12 と F13 の合成",
        "LOCKED",
    ),
    "F15_other_researched_daily": (
        "T-R / T-R2 / T-V / Top-Five / next-five は NOT_SUPPORTED、M16 は POSITIVE_EXPLORATORY だが #495 で「閉じる」",
        "日次の horizon で当日決済の範囲外",
        "LOCKED",
    ),
}

# ---------------------------------------------------------------------------
# 2. F1 の窓（同じ family の別の窓）と、scenario ごとの効果（年率の retail の net Sharpe）
# ---------------------------------------------------------------------------
WINDOWS: Final[tuple[str, ...]] = (
    "EUR_morning_0200_0815",
    "JPY_post_tokyo_fix",
    "EUR_post_ECB_0815_1700",
)

#: 各窓の cost / σ（#503 §13a・§13b・§13c の EUR_USD / USD_JPY の時刻ごとの実測から）
COST_OVER_SIGMA: Final[dict[str, float]] = {
    "EUR_morning_0200_0815": 0.068,
    "JPY_post_tokyo_fix": 0.063,
    "EUR_post_ECB_0815_1700": 0.056,
}
TRADES_PER_YEAR: Final[int] = 250

#: scenario の定義（計算の前に固定）。値と根拠
SCENARIOS: Final[dict[str, dict[str, object]]] = {
    "P1-O": {
        "label": "Optimistic: 原典で確認された、実装の可能性のある最も強い post-cost の効果",
        "sharpe": {
            "EUR_morning_0200_0815": 0.74,  # B&R（1997–2007）の EBS の net を retail に置き換えた推定（#503 §13a）。古い sample
            "JPY_post_tokyo_fix": 0.85,  # KMW 1999–2018 の平均を retail に置き換えた推定 0.82〜0.89 の中間（#503 §13b）。最近の証拠（CME 2009–18 で −0.2〜0.07、2013 年以降横ばい）と矛盾する
            "EUR_post_ECB_0815_1700": 0.25,  # KMW 1999–2018 の cost なしの gross / σ 0.072 − retail の cost / σ 0.056 = 0.016 × √250（#503 §13c）。CME 2009–18 は 0.08
        },
        "rho_within_family": 0.0,
        "cost_multiplier": 1.0,
        "stale_flags": {
            "JPY_post_tokyo_fix": True,
            "EUR_morning_0200_0815": True,
            "EUR_post_ECB_0815_1700": True,
        },
    },
    "P1-B": {
        "label": "Base: 最近の証拠を優先し、公表の後の減衰と市場の変化を考えた、最も防御できる中心の推定",
        "sharpe": {
            # CME 2009–2018（firm な気配・全 spread、最も新しい原典の証拠）を基にした retail の推定 0.29〜0.52 の中間 0.40 に、
            # 公表の後の減衰 30%（#505 の設計の感度 30〜60% の低い端。CME の期間は KMW の公表 2024 より前なので、公表の後の減衰の全量は掛けない）
            "EUR_morning_0200_0815": round(0.40 * 0.70, 3),
            # 最近の証拠（CME 2009–18 で −0.2〜0.07、2013 年以降の half spread で横ばい）の中心は 0 以下。最適化は正でない窓を持たないので 0
            "JPY_post_tokyo_fix": 0.0,
            # CME 2009–18 の firm な全 spread で 0.08。retail の cost はそれより高いので 0
            "EUR_post_ECB_0815_1700": 0.0,
        },
        "rho_within_family": 0.3,  # 同じ W 字の強さが日ごとに共通に効く（強い日は全ての窓が同時に利益）ので正
        "cost_multiplier": 1.0,
        "stale_flags": {
            "JPY_post_tokyo_fix": False,
            "EUR_morning_0200_0815": False,
            "EUR_post_ECB_0815_1700": False,
        },
    },
    "P1-S": {
        "label": "Stress: より高い cost・より弱い効果・正の相関・集中",
        "sharpe": {
            "EUR_morning_0200_0815": round(
                0.16 * 0.40, 3
            ),  # L1 を基にした最低 0.16 に、減衰 60%（#505 の感度の高い端）
            "JPY_post_tokyo_fix": 0.0,
            "EUR_post_ECB_0815_1700": 0.0,
        },
        "rho_within_family": 0.5,
        "cost_multiplier": 1.5,  # 往復の cost を 1.5 倍（Sharpe は 0.5 × cost / σ × √250 だけ下がる）
        "stale_flags": {
            "JPY_post_tokyo_fix": False,
            "EUR_morning_0200_0815": False,
            "EUR_post_ECB_0815_1700": False,
        },
    },
}

#: 判定に使わない感度（事前に宣言）: 窓の間の負の相関、と、状態を解いた（復活させた）上限の参考
SENSITIVITY_RHO: Final[tuple[float, ...]] = (-0.2,)
#: 状態を無視した参考の行（判定に使わない。当日決済に反する family を含む）。値は記録のまま
STATUS_UNLOCKED_REFERENCE: Final[dict[str, float]] = {
    "F14_classical_premia_composite_TC_net": 0.127,  # #497、overnight
    "F15_M16_central": 0.276,  # #495、日次、閉じた family
}

# ---------------------------------------------------------------------------
# 3. 判定の規則（指示 §13 をそのまま。後から変えない）
# ---------------------------------------------------------------------------
TARGET: Final[float] = 1.0
PASS_RULE: Final[str] = (
    "PASS: (1) Base の credible な system の上限 ≥ 1.0、(2) それが 1 つの古い sample・1 つの極端な相関の仮定・"
    "1 つの古い component だけで成立していない、(3) 正の限界の寄与を持つ distinct な economic mechanism family が 2 つ以上、"
    "(4) execution cost の stress の後でも production の目標に現実的な余地が残る。"
    "AMBER: Optimistic で ≥ 1.0、Base で < 1.0（P2 に進まない）。"
    "STOP: Base と Optimistic のどちらにも credible な 1.0 到達の経路が無い、または 1.0 超えが古い JPY など 1 つの古い推定だけに依存する。"
)
STOP_STATE: Final[str] = "PORTFOLIO_ARCHITECTURE_FEASIBLE_BUT_COMPONENT_SUPPLY_INSUFFICIENT"
