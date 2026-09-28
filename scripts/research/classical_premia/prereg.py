# ruff: noqa: E501 -- pre-registration prose
"""**FINAL_CLASSICAL_PREMIA_LONG_SPAN_CYCLE の事前登録**（2026-09-29 裁定 §3–§41）。alpha を見る前に凍結する。

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE` ·
`PRODUCTION_READINESS_NOT_CLAIMED`.

**primary hypothesis は 1 本だけ**: G10 の既存 8 通貨で、古典的な断面 carry（family A）と
中期の断面 momentum（family B）を、結果を見る前に固定した**等リスク合成**として持つと、
1999–2016 の seen の長 span で cost 後に経済的に意味のある正の情報があるか。

検定するのは **COMPOSITE だけ**。carry 単独・momentum 単独は分解の診断で、どちらか良い方を採ることは禁止（§3・§14・§40）。
best-of-N・winner selection・horizon selection・符号反転・結果を見た後の rule 変更は禁止（§7・§11・§41）。

設計の理由（signal を見ずに決めた）は `docs/research/m15_final_classical_premia_prereg_2026_09_29.md`。
"""

from __future__ import annotations

import ast
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Final

CYCLE: Final[str] = "FINAL_CLASSICAL_PREMIA_LONG_SPAN_CYCLE"
QUALIFIER: Final[str] = "FINAL_BOUNDED_SEEN_DATA_ALPHA_CYCLE"

#: §4: programme の既存 universe を変えない（top_five.UNIVERSE と同じ 8 通貨。test で照合する）。
UNIVERSE: Final[tuple[str, ...]] = ("AUD", "CAD", "CHF", "EUR", "GBP", "JPY", "NZD", "USD")
NUMERAIRE: Final[str] = "USD"

#: §5: 既に seen の公開長 span（ECB 参照レート 1999-01-04 … 2016-06-01）。fresh pool 2016-06-02 以降は読まない。
SPAN: Final[dict[str, str]] = {
    "source": "ECB euro reference rates（T-V で取得済み、artifacts/track_a_scratch/valuation/fx_*.parquet）",
    "first_price_day": "1999-01-04",
    "first_decision_on_or_after": "2000-02-01",
    "last_return_day": "2016-06-01",
    "why_first_decision": "momentum の 252 営業日 formation と 252 営業日の共分散窓の両方が揃う最初の月初（1999-01-04 から 252 営業日は 1999-12 下旬）。両 family とも同じ日から始める",
}

#: §6: 新しい取得はしない。必要な系列は全て既に取得・seen 化されている。
DATA_ACQUISITION: Final[dict[str, str]] = {
    "status": "NO_NEW_ACQUISITION_REQUIRED",
    "fx": "ECB 参照レート（EUR 建て 7 通貨）。top_five.panel.long_span_panel（seen window の guard 付き）",
    "policy_rates": "BIS 政策金利（月次、SDMX で endPeriod 付き取得済み。mechanism_redesign の取得記録の content hash を _load が照合）",
    "short_rates_3m": "OECD 3 か月銀行間金利（financing の感度基準だけに使う。signal には使わない）",
}

REBALANCE: Final[dict[str, str]] = {
    "rule": "毎月の最初の ECB 営業日（decision day）に target を作り直し、次の decision day まで通貨 exposure を一定に持つ",
    "execution_price": "decision day の ECB 参照レート（14:15 CET）。P&L は decision day t の exposure × 翌営業日 t+1 の return",
}

CARRY: Final[dict[str, Any]] = {
    "family": "A — cross-sectional carry",
    "rate": "BIS 政策金利の月末値（policy rate）",
    "why_this_rate": (
        "signal を見ずに 3 条件で選んだ（§8）。(1) timing: 政策金利は公表時刻が明確で、月末値は月末の時点で確定している。"
        "OECD の 3 か月金利は月平均で、月内の値を含むので lag を置かないと look-ahead になり、置くと 1 か月古くなる。"
        "(2) availability: BIS 政策金利は 8 通貨とも 1999-01 から揃う（EUR は 1999-01 から、JPY は BIS が数値を持たない "
        "ゼロ金利・量的緩和の期間だけ #495 で凍結した 0% を置く）。OECD の JPY 3 か月金利は 2002-04 まで、CHF は 1999-08 まで無い。"
        "(3) economic closeness: FX の forward points は短期の銀行間金利で決まるので 3 か月金利の方が経済的には近いが、"
        "G10 では政策金利と短期金利の順位はほぼ一致し、programme の financing 会計（#495）の primary 基準も同じ政策金利である。"
        "signal と会計を同じ金利にすると『高金利通貨を持って金利差を受け取る』という carry の定義そのものになる"
    ),
    "placement": "signal: 第 m 月の値を m 月末の**翌暦日**から使う（decision day = 月初の営業日には必ず前月末の値が届く。月末が週末・休日でも 1 か月古い値にならない、Role 1 N1）。会計: m 月末の当日から（#495 と同じ）",
    "stale_carryover": "_align は最後の値を最大 75 日運ぶので、JPY の 0% 期間の始めには直前の BIS 値（例 2001-02 の値）がしばらく残り、2016 のマイナス金利（−0.1%）は 0% と置かれる。順位への影響は無視できる（Role 1 N2・Role 2 N-7。記録のみ）",
    "zero_lower_bound": "2009–2015 の USD / EUR / JPY / CHF は数 bp しか違わないが、rank weight は満額の差を付ける。AMP の標準的な扱いで、解釈上の代償として記録する（Role 1 N3）",
    "jpy_zero_periods": (
        ("1999-02-12", "2000-09-29"),
        ("2001-03-19", "2006-07-31"),
        ("2013-04-04", "2016-06-01"),
    ),
    "jpy_zero_periods_source": "usd_factor_financing.prereg.FINANCING['jpy_policy_zero_periods']（#495 で凍結済み。BIS に値が無い日だけ 0% と置く。test で一致を確認）",
    "staleness_days": 75,
    "score": "s_c = r_c（金利の水準、%）。USD も 8 通貨の 1 つとして順位に入る",
    "sign": "高金利を long、低金利を short（符号は文献どおり。反転しない）",
    "missing": "decision day に 1 通貨でも金利が無ければ fail-closed（例外で止まる。値を補わない）",
    "grid": "禁止。政策金利・3 か月金利・その他の短期金利を alpha で比べない（§8）",
}

MOMENTUM: Final[dict[str, Any]] = {
    "family": "B — cross-sectional medium-term momentum",
    "return": "R_c = 通貨 c の対 USD 日次 log return（spot のみ、金利差を含まない）、R_USD = 0",
    "formation": "12-1: m_c(t) = Σ R_c over 営業日 [t−251, t−21]（log price の差 logP(t−21) − logP(t−252)）。直近 21 営業日（約 1 か月）を飛ばす",
    "formation_trading_days": 252,
    "skip_trading_days": 21,
    "holding": "1 か月（次の decision day まで。重なりの無い月次 rebalance）",
    "why_this_rule": (
        "signal を見ずに文献の canonical 定義を 1 つだけ採った（§9）。Asness–Moskowitz–Pedersen (2013, Value and Momentum Everywhere) の"
        "通貨 momentum は『直近 1 か月を飛ばした過去 12 か月の return、月次 rebalance』で、資産クラス横断の標準定義である。"
        "Menkhoff–Sarno–Schmeling–Schrimpf (2012) は 1〜12 か月の formation を並べて報告しているが、その中から最良を選ぶことは"
        "horizon selection になるので採らない。直近 1 か月を飛ばすのは短期の反転と、programme が既に測った数日の reversal / momentum family との重なりを避けるため"
    ),
    "why_spot_not_excess": (
        "**文献の定義からの意図的な逸脱**（alpha 前に決めた、Role 1 R1）。AMP (2013) と MSSS (2012) の通貨 momentum は "
        "forward から作る excess return（金利差を含む）で formation を作る。ここでは spot だけを使う。理由: 金利差を含むと "
        "momentum の順位が carry の順位を機械的に含み、2 つの family が別の premium を測るという合成の前提が崩れる。"
        "carry は family A が持つ。formation の窓（12-1）と月次保有は AMP どおり"
    ),
    "score": "s_c = m_c。USD は 0",
    "sign": "過去の勝ち通貨を long、負け通貨を short（反転しない）",
    "grid": "禁止。1 / 3 / 6 / 9 / 12 か月を走らせない。holding も変えない（§11）",
}

RANKING: Final[dict[str, str]] = {
    "method": "rank weights（Asness–Moskowitz–Pedersen 2013）: w_c = rank(s_c) − mean(rank)、同順位は平均順位。Σ|w| = 1 に正規化（long 側 +0.5、short 側 −0.5、和はゼロ）",
    "why": "8 通貨しかないので上位 / 下位 k 通貨の portfolio は k の選択が要り、それ自体が自由度になる。rank weight は全通貨を使い、k を持たない",
    "all_equal": "全通貨が同順位なら w = 0（その family はその月 flat）",
}

RISK: Final[dict[str, Any]] = {
    "covariance": "decision day t の前日までの 252 営業日（t−252 … t−1）の R（対 USD 日次 log return、8 通貨）の標本共分散（ddof=1）× 252。R_t は t の fix で初めて確定するので使わない（point-in-time、§13、Role 2 N-2）",
    "annualisation": "252 営業日 / 年（programme の規約）。ECB の暦は約 256 日 / 年なので年率 return は約 1.5% 小さめ、Sharpe は約 0.8% 小さめに出る（保守側、Role 1 N4・Role 2 N-3）",
    "covariance_window": 252,
    "family_scaling": "u_k = w_k / σ_k、σ_k = √(w_kᵀ Σ w_k)。family ごとに ex-ante vol を 1 に揃える",
    "family_weighting": "composite = 0.5·u_carry + 0.5·u_momentum",
    "why_equal_risk": "2 資産の equal risk contribution は相関に依らず w_k ∝ 1/σ_k に一致する（RC_1 = RC_2 ⇔ w_1σ_1 = w_2σ_2）。u_k を等ウェイトで足すのはその厳密な ERC で、return から何も推定しない（§12）",
    "target_vol": 0.10,
    "leverage": "L = 0.10 / √(rawᵀ Σ raw)。x = L · raw",
    "gross_cap": 5.0,
    "gross_cap_rule": "通貨 gross Σ|x| が 5.0 を超える月は 5.0 に縮める（programme の max_leverage 5 と同じ値）",
    "zero_vol": "σ_k = 0（w_k = 0）の family はその月 0。両方 0 なら flat",
    "hysteresis": "無し（月次なので）",
    "fitted_weights": "禁止（regression / Sharpe / inverse covariance の最適化 / mean-variance / full-sample の risk parity）",
}

COST: Final[dict[str, Any]] = {
    "transaction": "construction.charged_cost: Σ|Δx| × 1.703 bp（programme の保守的な basket 規約、routing 比 1.32 込み）。decision day の target 変更にだけ掛かる",
    "stress_multiples": (1.5, 2.0),
    "stress_scales_markup": True,
}

FINANCING: Final[dict[str, Any]] = {
    "name": "APPROXIMATE_RESEARCH_FINANCING（actual OANDA financing ではない）",
    "routing": "USD numeraire: 外国 7 通貨それぞれを USD pair 1 本で持つ。P&L = x · R。pair notional = Σ_{c≠USD} |x_c|",
    "carry_formula": "Σ_c x_c × (r_c − r_USD)/100 × 暦日(t→t+1)/365。和がゼロなので numeraire に依らない",
    "rate_bases": {
        "policy_contemporaneous": "PRIMARY。BIS 政策金利の月末値を月末から使う（#495 と同じ）",
        "three_month_lagged": "SENSITIVITY。mechanism_redesign.signals.carry_rate_panel（lag 付き 3 か月金利、欠けは政策金利で補う）",
    },
    "markup_band": (0.0, 0.005, 0.01, 0.02),
    "central_markup": 0.005,
    "adverse_markup": 0.02,
    "markup_unit": "pair notional 1 単位あたりの年率（#495 と同じ単位。結果を見て変えない、§17）",
    "cells": "金利基準 2 × markup 4 = 8 セル",
    "central_cell": "policy_contemporaneous | 0.005",
    "full_retail_net": "FULL_RETAIL_NET_UNKNOWN",
}

LINES: Final[dict[str, str]] = {
    "gross_spot": "x · R（spot の寄与）",
    "transaction_cost": "Σ|Δx| × 1.703 bp",
    "carry": "金利差の受け払い（近似）",
    "markup": "仮定の retail markup",
    "tc_net": "NET_EX_TRANSACTION_COSTS_EXCLUDING_FINANCING = gross_spot − transaction_cost",
    "judged_net": "TOTAL_ECONOMIC(basis, m) = gross_spot + carry(basis) − transaction_cost − m × pair notional",
    "headline": "TC-net と judged net（central cell）を必ず並べる（§18）。carry を含む book では TC-net は carry の受取を含まないので、carry の premium の主部は judged net 側に出る",
}

NULL: Final[dict[str, Any]] = {
    "primary": "currency_label_permutation",
    "why_primary_changed_pre_alpha": (
        "Role 1 R5: carry の月次 target は lag-1 自己相関 0.994（family 単独の有効標本数 ≈ 0.6）で、16 年間ほぼ 1 つの静的な "
        "賭け（高金利 AUD / NZD 対 低金利 JPY / CHF）である。時間方向の circular shift では shift 後もほぼ同じ賭けが残り、"
        "帰無の中心が carry premium そのものを含む（carry premium を検定できない）。通貨の label を入れ替える帰無は "
        "『高金利の**その**通貨が稼いだのか』を問うので、静的な carry premium を含めて検定できる"
    ),
    "currency_label_permutation": {
        "method": "各 draw で 8 通貨の置換 π（恒等置換を除く）を 1 つ引き、**両 family の score の列に同じ π を全期間で**当てる（通貨 i に通貨 π(i) の score を渡す）。book・共分散・return・金利・cost・markup は実際のまま",
        "preserves": "score の時系列（持続性・turnover の性質）・2 family の相互関係・cross-sectional の分布・rank weight・vol scaling・cost と financing の会計",
        "breaks": "score と、その通貨自身の return・金利の対応（= 情報）",
        "draws": 2000,
        "seed": 20260929,
        "distinct": "8! − 1 = 40,319 通りから復元抽出",
    },
    "joint_circular_shift": {
        "role": "SECONDARY（報告のみ、判定に使わない）。timing の情報（静的な断面を超える部分）の診断",
        "method": "carry と momentum の日次 score panel（span 内の行）を**同じ k 行**だけ巡回させる",
        "shift_range": "k ~ 一様整数 [252, n−252]",
        "draws": 2000,
        "seed": 20260930,
        "centre": "静的な carry の賭けを含むので中心は 0 ではない",
    },
    "primary_statistic": "composite judged net Sharpe（central cell: policy_contemporaneous, markup 0.005）",
    "reported_statistic": "composite TC-net Sharpe（両方の帰無で）",
    "p_value": "(1 + #{null ≥ observed}) / (1 + draws)",
    "percentile": "mean(null < observed)",
}

LOO: Final[dict[str, str]] = {
    "method": "8 通貨から 1 通貨を除いた 7 通貨の universe で composite を**作り直す**（順位・rank weight・vol scaling をやり直す）。8 本",
    "reported": "judged net（central）と TC-net の Sharpe・年率",
}

METRICS: Final[tuple[str, ...]] = (
    "gross annual return / gross Sharpe（spot）",
    "gross economic（spot + carry）",
    "TC-net annual return / Sharpe",
    "approximate-financing total return / judged net Sharpe（8 セル）",
    "turnover（round trips / 年、gross 1 単位あたり）",
    "annual transaction cost",
    "carry contribution / markup contribution",
    "family contributions（spot・carry は線形に厳密、cost は |Δx_f|、markup は外国脚の |x_f| の比で按分）",
    "signal persistence（月次 rank weight の lag-1 自己相関、family ごと）と有効標本数（composite と family ごと）",
    "positive calendar-year blocks",
    "currency breadth（通貨別寄与は cross-section 平均を引いた return / 金利で測る。numeraire に依らない）",
    "leave-one-currency-out（作り直し）",
    "top 1 / 5 / 10 day contribution",
    "max DD",
    "cost ×1.5 / ×2",
    "null percentile / p-value",
)

EFFECTIVE_N: Final[dict[str, str]] = {
    "definition": "月次 composite の target weight（x / Σ|x|）の lag-1 自己相関 ρ から N_eff = N_months × (1−ρ)/(1+ρ)（programme の effective_observations と同じ式、月次の position に当てる）",
    "per_family": "family ごとにも同じ式で報告する（carry ≈ 0.6、momentum ≈ 18 が実行前に分かっている、power.json）",
    "f4_known_before_run": "composite の N_eff（11.6）は target weight だけで決まり、実行前に既知。**F4 は実行前から PASS が分かっている**。その値の大半は momentum の回転から来る（Role 1 R5）",
}

#: §34・§35: 研究としての判定。上から順に評価する。
RESEARCH_VERDICT: Final[tuple[dict[str, str], ...]] = (
    {
        "if": "post-run review が material defect（leakage / routing / 誤った signal・cost・financing・universe）を BLOCKER とした",
        "then": "INVALID（修正 run はしない、§27）",
    },
    {
        "if": "TC-net 年率 ≤ 0、または judged net（central）年率 ≤ 0",
        "then": "NOT_SUPPORTED_IN_SEEN_DEVELOPMENT（failure class を付ける）",
    },
    {
        "if": "judged net（central）の primary null（通貨 label の置換）での percentile < 0.80",
        "then": "NOT_SUPPORTED_IN_SEEN_DEVELOPMENT（null の中央〜下側）",
    },
    {
        "if": "どちらかの family の composite 内寄与（judged、central）が −0.5 × composite 合計より小さい",
        "then": "NOT_SUPPORTED_IN_SEEN_DEVELOPMENT（片 family が極端に逆向き、合成の前提が崩れる）",
    },
    {
        "if": "currency LOO の作り直しで judged net（central）が正の universe が 6/8 未満",
        "then": "NOT_SUPPORTED_IN_SEEN_DEVELOPMENT（極端な通貨集中）",
    },
    {"if": "それ以外", "then": "POSITIVE_EXPLORATORY_NOT_DECISION_GRADE"},
)
FAILURE_CLASS: Final[dict[str, str]] = {
    "gross spot ≤ 0 かつ judged ≤ 0": "SIGNAL_FAILURE",
    "gross spot > 0 だが TC-net ≤ 0": "COST_FAILURE",
    "TC-net > 0 だが judged ≤ 0": "FINANCING_FAILURE",
    "judged > 0 だが TC-net ≤ 0": "CARRY_ONLY_POSITIVE_SPOT_NET_NOT_POSITIVE（§35 の TC-net ≤ 0 で失敗）",
}
CAVEATS: Final[dict[str, str]] = {
    "FAMILY_CONCENTRATION_CAVEAT": "composite の judged net が正のとき、片 family の寄与が合計の 80% 以上（§29）。自動失格ではない",
    "CURRENCY_CONCENTRATION_CAVEAT": "1 通貨を除いた作り直しのどれかで judged net（central）年率 ≤ 0（§30）。自動失格ではない",
}

#: §35「年 5% に要る Sharpe との差が依然大きい」を事前に数値で固定する。
BUSINESS_GAP: Final[dict[str, Any]] = {
    "required_sharpe_5pct_at_10pct_vol": 0.50,
    "rule": "judged net（central）Sharpe + 1 × SE(=1/√年数) < 0.50 なら REQUIRED_SHARPE_GAP_LARGE（1 標準誤差の上端でも要求に届かない）",
}

#: §35「DD / required risk が business objective と明確に不整合」を事前に数値で固定する（Role 1 R4）。
BUSINESS_RISK: Final[dict[str, Any]] = {
    "max_required_vol_for_5pct": 0.15,
    "max_drawdown_at_required_vol": -0.40,
    "rule": (
        "REQUIRED_RISK_INCONSISTENT: judged net（central）Sharpe ≤ 0、または 年 5% に要る vol（0.05 / Sharpe）が 15% を超える、"
        "または 観測した最大 DD をその vol へ比例で伸ばした値が −40% より深い"
    ),
    "why": "15% は裁定 §31 の vol scenario の上端。#496 の算術で vol 15% の年 5% は 10 年 DD の中央値 −39%。それより深い DD は、個人の年 5% 目標と明確に不整合とみなす",
}

#: §33: forward / fresh 提案の最低条件。全部 PASS でも fresh 使用は自動承認されない（提案するだけ）。
FORWARD_ELIGIBILITY: Final[dict[str, str]] = {
    "F1": "clean tier A: 事前登録・1 回だけ・結果後の修正なし・post-run review に BLOCKER なし",
    "F2": "judged net（central）の primary null（通貨 label の置換）で percentile ≥ 0.95、または p ≤ 0.05（primary は 1 本なので family 調整は不要）",
    "F3": "adverse markup 0.02 で金利基準 2 つの両方の judged net 年率 > 0",
    "F4": "有効標本数 ≥ 10（EFFECTIVE_N の定義）",
    "F5": "CURRENCY_CONCENTRATION_CAVEAT が無い、top-10 日の寄与 < 1、正の暦年 block が半分以上",
    "F6": "fresh pool の確認に関わる保護情報の汚染が無い（D-M3 は forward の JPY 金利確認だけが対象で、fresh pool 2016-06-02 … 2021-04-25 には及ばない。report で ledger を確認して判定）",
    "F7": (
        "fresh 4.9 年を使うと判断が変わりうる: 観測 judged Sharpe を真とした fresh 単独の片側 5% 検出力 ≥ 0.20 かつ fresh で "
        "net ≤ 0 になる確率 ≥ 0.10。**通るのは観測 Sharpe がおよそ 0.36〜0.58 のときだけ**で、それより強い結果は fresh で"
        "判断が変わらないので FAIL になる（意図どおり、Role 1 N6）"
    ),
    "F8": "freeze digest・input manifest・execution intent・hash chain の ledger・1 回の実行記録が commit されている",
}

#: §36・§39: programme の disposition。
DISPOSITION: Final[tuple[dict[str, str], ...]] = (
    {"if": "INVALID", "then": "HUMAN_RETURN_INVALID_RUN（修正 run はしない）"},
    {
        "if": "POSITIVE_EXPLORATORY_NOT_DECISION_GRADE かつ F1〜F8 すべて PASS かつ REQUIRED_RISK_INCONSISTENT でない",
        "then": "A. FRESH_CONFIRMATION_PROPOSAL（提案だけ。fresh は開かない）",
    },
    {
        "if": "POSITIVE_EXPLORATORY_NOT_DECISION_GRADE かつ REQUIRED_SHARPE_GAP_LARGE でも REQUIRED_RISK_INCONSISTENT でもない",
        "then": "B. POSITIVE_EXPLORATORY_BUT_NOT_CONFIRMATION_READY",
    },
    {
        "if": "それ以外",
        "then": "C. LONG_TERM_HOLD / NO_FURTHER_SEEN_DATA_ALPHA_SEARCH（FX_HAS_NO_EDGE ではない）",
    },
)
FORBIDDEN_TOKENS: Final[tuple[str, ...]] = ("FX_RESEARCH_PAUSED", "FX_HAS_NO_EDGE")

#: §11: secondary sensitivity は alpha 前に固定し、primary verdict には使わない。
SENSITIVITY: Final[tuple[str, ...]] = (
    "cost ×1.5 / ×2（markup も同倍率）",
    "financing 8 セル（金利基準 2 × markup 4）",
    "diagnostic: carry 単独 / momentum 単独（同じ vol target・同じ cost・同じ financing）",
)

CAPACITY: Final[dict[str, Any]] = {
    "only_if": "judged net（central）年率 > 0（§31）",
    "target_vols": (0.08, 0.10, 0.12, 0.15),
    "margin_rate": 0.04,
    "margin_rate_why": "日本の個人向け店頭 FX の証拠金規制（最大 25 倍）。broker の上限であって、経済的に許容できる risk ではない（§32）",
    "gap_stress": "最大の単一通貨 exposure に 1 日 20% の逆行（CHF 2015-01-15 の規模）",
    "never": "weak Sharpe を leverage で年 5% にしない（§32）",
}

NEVER: Final[tuple[str, ...]] = (
    "fresh / OOS / dead / forward を読まない",
    "authenticated broker・有料 data・ML を使わない",
    "結果を見た後に weight・formation・universe・rate source・financing cell・rebalance・smoothing を変えない（§41）",
    "carry 単独・momentum 単独を次 cycle へ昇格させない（§40）",
    "結果確認後の再実行をしない（worker 数だけが違う決定的な再実行を除く、§26）",
)

# ----------------------------------------------------------------------
# freeze digest
# ----------------------------------------------------------------------
_REPO: Final[Path] = Path(__file__).resolve().parents[3]
CLOSURE_ROOT: Final[str] = "scripts/research/classical_premia/driver.py"
#: power.py も閉包に入れる（power.json を作った code、Role 2 N-4）
CLOSURE_ROOTS: Final[tuple[str, ...]] = (CLOSURE_ROOT, "scripts/research/classical_premia/power.py")
POWER_RECORD: Final[str] = "artifacts/research/classical_premia/power.json"
INPUT_FILES: Final[tuple[str, ...]] = (
    *(
        f"artifacts/track_a_scratch/valuation/fx_{c.lower()}.parquet"
        for c in UNIVERSE
        if c != "EUR"
    ),
    *(
        f"artifacts/track_a_scratch/mechanism_redesign/policy_rate_bis_{c.lower()}.parquet"
        for c in UNIVERSE
    ),
    *(
        f"artifacts/track_a_scratch/mechanism_redesign/short_rate_3m_{c.lower()}.parquet"
        for c in UNIVERSE
    ),
    "artifacts/research/mechanism_redesign/acquisition.json",
    "artifacts/research/mechanism_redesign/acquisition_amendment.json",
)


def code_closure() -> tuple[str, ...]:
    """driver から辿れる `scripts` の import の推移閉包（package の `__init__` を含む）。"""

    def module_file(module: str) -> Path | None:
        base = _REPO / Path(*module.split("."))
        if base.with_suffix(".py").exists():
            return base.with_suffix(".py")
        if (base / "__init__.py").exists():
            return base / "__init__.py"
        return None

    seen: set[Path] = set()
    stack = [_REPO / root for root in CLOSURE_ROOTS]
    while stack:
        path = stack.pop()
        if path in seen:
            continue
        seen.add(path)
        parent = path.parent
        while parent != _REPO and (parent / "__init__.py").exists():
            if parent / "__init__.py" not in seen:
                stack.append(parent / "__init__.py")
            parent = parent.parent
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                if node.level != 0:
                    #: 相対 import は閉包が辿れないので許さない（Role 2 N-4）
                    raise ValueError(f"{path}: 相対 import は閉包の外に出る")
                if node.module:
                    names = [node.module] + [f"{node.module}.{alias.name}" for alias in node.names]
            for name in names:
                if name.startswith("scripts"):
                    target = module_file(name)
                    if target is not None and target not in seen:
                        stack.append(target)
    return tuple(sorted(str(p.relative_to(_REPO)).replace("\\", "/") for p in seen))


#: digest から外すのは、driver.py のこの形の行**ちょうど 1 行**だけ（Role 2 R-1）。
FROZEN_LINE: Final[re.Pattern[bytes]] = re.compile(
    rb'^FROZEN_DIGEST: Final\[str\] = "(UNFROZEN|[0-9a-f]{64})"$'
)


def _sha_text(relative: str) -> str:
    raw = (_REPO / relative).read_bytes().replace(b"\r\n", b"\n")
    if relative == CLOSURE_ROOT:
        lines = raw.split(b"\n")
        matches = [i for i, line in enumerate(lines) if FROZEN_LINE.match(line)]
        if len(matches) != 1:
            raise ValueError(
                f"{CLOSURE_ROOT}: FROZEN_DIGEST の行がちょうど 1 行ではない（{len(matches)}）"
            )
        raw = b"\n".join(line for i, line in enumerate(lines) if i != matches[0])
    return hashlib.sha256(raw).hexdigest()


def _sha_bytes(relative: str) -> str:
    sha = hashlib.sha256()
    with (_REPO / relative).open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            sha.update(block)
    return sha.hexdigest()


def _payload() -> dict[str, Any]:
    return {
        "cycle": CYCLE,
        "qualifier": QUALIFIER,
        "universe": list(UNIVERSE),
        "numeraire": NUMERAIRE,
        "span": SPAN,
        "data_acquisition": DATA_ACQUISITION,
        "rebalance": REBALANCE,
        "carry": CARRY,
        "momentum": MOMENTUM,
        "ranking": RANKING,
        "risk": RISK,
        "cost": COST,
        "financing": FINANCING,
        "lines": LINES,
        "null": NULL,
        "loo": LOO,
        "metrics": list(METRICS),
        "effective_n": EFFECTIVE_N,
        "research_verdict": [dict(row) for row in RESEARCH_VERDICT],
        "failure_class": FAILURE_CLASS,
        "caveats": CAVEATS,
        "business_gap": BUSINESS_GAP,
        "business_risk": BUSINESS_RISK,
        "forward_eligibility": FORWARD_ELIGIBILITY,
        "disposition": [dict(row) for row in DISPOSITION],
        "forbidden_tokens": list(FORBIDDEN_TOKENS),
        "sensitivity": list(SENSITIVITY),
        "capacity": CAPACITY,
        "never": list(NEVER),
        "code_closure_sha256": {path: _sha_text(path) for path in code_closure()},
        #: parquet は bytes、JSON の取得記録は CRLF を正規化して hash する（checkout の改行に依らない、re-audit NEW-1）
        "input_sha256": {
            path: _sha_text(path) if path.endswith(".json") else _sha_bytes(path)
            for path in INPUT_FILES
        },
        "power_record_sha256": _sha_text(POWER_RECORD),
    }


def freeze_digest() -> str:
    return hashlib.sha256(
        json.dumps(_payload(), sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()


__all__ = [
    "CARRY",
    "CYCLE",
    "FINANCING",
    "MOMENTUM",
    "NULL",
    "RISK",
    "UNIVERSE",
    "code_closure",
    "freeze_digest",
]
