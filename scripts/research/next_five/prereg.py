# ruff: noqa: E501 -- freeze prose
"""次の 5 本の **一括事前登録**（2026-09-22 裁定 §J）。

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE` ·
`PRODUCTION_READINESS_NOT_CLAIMED`.

**alpha を 1 本も見る前に、5 本すべてをここで固定する。**
`freeze_digest()` が動いたら、それは別の事前登録である。

前 cycle から持ち越した設計上の変更は 3 つある。どれも**前 cycle が自分で測った失敗**から来ている。

1. **gate は帰無通過率ごと凍結する**（裁定 §G）。前 cycle の 3 条件 gate は帰無で 42% 通った。
   「gate を通った」だけでは情報にならないので、あの形の gate は **diagnostic へ降格**し、
   進行を決める hard gate は **permutation p** に置き換える。
2. **nuisance 定数は primary + 事前登録した感度集合で凍結する**（裁定 §H）。
   前 cycle は `max_staleness_days` を結果を見た後に選び、その値が格子の最大だった。
   今回は集合を先に決め、**全点を報告する**。best point を選ばない。
3. **primary span を signal の周期で決める**。前 cycle の T5 は月次 signal を 555 日
   （独立な状態 24 個）で測って検出力が無かった。月次 signal は **長 span を primary** にする。
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Final

CYCLE: Final[str] = "NEXT_FIVE_2026_09"

AUTHORITY: Final[dict[str, str]] = {
    "ruling": "2026-09-22 Human + ChatGPT 裁定",
    "record": "docs/governance/m15_adjudication_2026_09_19_and_09_20.md §7",
    "selection": "scripts/research/next_five/ranking.py（signal-blind）",
    "inventory": "scripts/research/next_five/inventory.py",
}

WORKFLOW_STATUS: Final[str] = "NEXT_FIVE_FROZEN_AWAITING_EXECUTION"

#: 5 本が終わったら **STOP**（裁定 §O）。
FORBIDDEN_NEXT_STEPS: Final[tuple[str, ...]] = (
    "6 本目の track",
    "fresh pool / historical OOS / dead window / forward epoch の読み取り",
    "paid data の購入",
    "authenticated broker / demo / paper / live",
    "nonlinear ML の training",
    "multi-source portfolio の最適化",
    "paper-forward",
)

#: 前 cycle の 5 本を救わない（裁定 §B）。**今回の prior には使うが、救済実験はしない。**
FORBIDDEN_RESCUES: Final[tuple[str, ...]] = (
    "T1 / T2 / T3 / T4 の low-turnover variant",
    "horizon smoothing",
    "threshold tuning",
    "rebalance tuning",
    "sign flip",
    "currency exclusion",
    "cost-specific rescue",
    "T5 の追加実行",
)

UNIVERSE: Final[tuple[str, ...]] = ("AUD", "CAD", "CHF", "EUR", "GBP", "JPY", "NZD", "USD")

#: 前 cycle と同じ 2 つの seen span。**新しい span は開けない。**
SPANS: Final[dict[str, dict[str, str]]] = {
    "long": {
        "first": "1999-01-04",
        "last": "2016-06-01",
        "source": "ECB euro reference rates（取得済み）",
        "status": "EXPLORATORY_SEEN_DEVELOPMENT_DATA",
    },
    "recent": {
        "first": "2021-04-27",
        "last": "2025-12-26",
        "source": "guarded M15 caches（既取得・archive の新規読み取りなし）",
        "status": "EXPLORATORY_SEEN_DEVELOPMENT_DATA",
    },
}

#: 絶対に読まない（裁定 §N）。**parsed typed date で判定する。文字列比較はしない。**
PROTECTED_BOUNDS: Final[dict[str, dict[str, str]]] = {
    "fresh_pool": {"first": "2016-06-02", "last": "2021-04-25"},
    "historical_oos": {"note": "Track A R1 の OOS slice"},
    "dead_window": {"note": "宣言済みの dead window"},
    "forward_epoch": {"note": "forward Formal Confirmation epoch"},
}

#: **primary span を signal の周期で決める**（前 cycle の検出力失敗への直接の対処）。
#:
#: 月次 signal を近 span（4.8 年）で測ると独立な状態が 55 個前後しかない。
#: 長 span（17.2 年）なら 200 個前後になる。**検出力の高い側で判定する。**
#: ただし **cost 規約が実測されたのは近 span だけ**なので、net は必ず両方報告する。
PRIMARY_SPAN_RULE: Final[dict[str, str]] = {
    "monthly_or_slower": "long",
    "daily": "recent",
    "event_paced": "recent",
    "why": (
        "前 cycle の T5 は月次 signal を 555 日・独立状態 24 個で測り、"
        "その窓の 95% 検出下限 1.321 が実測 +0.838 を上回った。"
        "**周期の遅い signal を短い窓で測るのは、設計段階で負けている**"
    ),
    "both_always_reported": "YES",
    "cost_caveat": (
        "長 span では cost 規約が実測されていない。net を長 span で読むときは"
        "**仮定された cost** であることを必ず添える"
    ),
}

#: 実行層。前 cycle と同じものを使う（比較可能性のため）。
EXECUTION_LAYER: Final[str] = "scripts.research.continuous_portfolio.construction.run_book"

BOOK_CONFIG: Final[dict[str, Any]] = {
    "mapping": "vol_normalized",
    "neutralize_leading_factor": True,
    "weight_cap": 0.25,
    "band": 0.10,
    "vol_target": 0.10,
    "max_leverage": 20.0,
    "leverage_hysteresis": 0.10,
    "sigma_window": 60,
    "factor_window": 120,
    "vol_window": 60,
    "drawdown_governor": False,
    "days_per_year": 252.0,
    "why_max_leverage_is_not_5": (
        "5.0 は placeholder であり **feasibility の hard limit として使うことは禁じられている**。"
        "20.0 は broker の margin ceiling であって **運用の risk budget ではない** — "
        "vol_target 0.10 なら必要 leverage は 4 倍台で、この cap は binding しない。"
        "risk は vol targeting が決める"
    ),
}

#: **今回は deviation を置かない。** 前 cycle は T5 だけ `neutralize_leading_factor=False`
#: にしていた（signal が dollar 軸そのものだったため）。その結果 T5 は breadth 1 になった。
#: 今回の 5 本はいずれも dollar 軸ではないので、全 track を同一設定で走らせる。
BOOK_CONFIG_DEVIATIONS: Final[dict[str, dict[str, Any]]] = {}

COST: Final[dict[str, Any]] = {
    "convention": "前 cycle と同一の凍結 cost 規約（比較可能性のため変更しない）",
    "measured_on": "recent span のみ",
    "stress_multiples": (1.0, 1.5, 2.0),
}

BENCHMARKS: Final[tuple[str, ...]] = (
    "zero_signal",
    "fx_own_momentum_20d",
    "fx_own_mean_reversion_20d",
    #: **前 cycle では結果を見た後に足した null。今回は最初から入れる。**
    "constant_long_usd",
)

CONTROL: Final[str] = "fx_own_momentum_20d（incremental IC はこれを除いた残差で測る）"

#: beta の形が既存 track と重なる場合に要求する rename gate。
#: **S07 は S05（VIX shock → funding 通貨）と同じ「risk-off → 安全通貨」の向きを持つ。**
#: 情報源は違うが、向きが同じなら言い換えかもしれない。**閾値を先に決めておく。**
RENAME_GATES: Final[dict[str, dict[str, Any]]] = {
    "S07": {
        "comparator": "S05（T1）の VIX shock score",
        "statistic": "日次 score の cross-section 相関の時系列平均の絶対値",
        "threshold": 0.8,
        "if_exceeded": "RENAME_OF_A_CLOSED_TRACK — 結果にかかわらず NOT_SUPPORTED とする",
        "why": "向きが同じで情報源が違うとき、実質的に同じ signal を別名で呼んでいないかを測る",
    },
    "S31": {
        "comparator": "S26（T5）の TIC flow score",
        "statistic": "同上",
        "threshold": 0.8,
        "if_exceeded": "RENAME_OF_A_PRIOR_TRACK",
        "why": "どちらも『flow』だが主体も通貨も違う。**違うと主張する以上、測って示す**",
    },
    "S25": {
        "comparator": "S31 の reserves score",
        "statistic": "同上",
        "threshold": 0.8,
        "if_exceeded": "RENAME_WITHIN_THIS_CYCLE",
        "why": "同じ中銀の balance sheet と外貨準備が同じ数字になっていないかを測る",
    },
}

#: ------------------------------------------------------------------
#: 裁定 §G — gate の再設計
#: ------------------------------------------------------------------

#: **前 cycle の gate。** 帰無で 42% 通ったので、**hard gate としては使わない。**
DEMOTED_GATE: Final[dict[str, Any]] = {
    "id": "THREE_SIGN_TRIPLE",
    "conditions": ("gross_sharpe > 0", "incremental_ic > 0", "net_annual_return > 0"),
    "measured_null_pass_rate": 0.42,
    "measured_on": "前 cycle T5 / circular shift 500 回",
    "status": "DEMOTED_TO_DIAGNOSTIC_NOT_A_SELECTION_GATE",
    "why": (
        "**通過率が高い gate は、通っても情報にならない。** しかも通過率は track ごとに違い、"
        "turnover が低いほど高くなる（net > 0 が cost drag 超えを要求するため）。"
        "同じ規則が track によって全く違う厳しさで効いていた"
    ),
    "still_reported": "YES — 診断として残す。ただし『通った』を根拠に進まない",
    "calibrated_at_freeze": {
        "record": "artifacts/research/next_five/gate_calibration.json",
        "null_pass_rate_range": "9.3%（U5）〜 28.7%（U2）",
        "status": "RESEARCH_METHOD_FINDING",
        "interpretation": (
            "**通過率が低い track ほど良い、とは解釈しない**（第 2 裁定 §3）。"
            "gross>0 と incremental IC>0 の帰無通過率はどの track も 0.4〜0.6 で、"
            "割れるのは net>0 だけである。**gate の厳しさを決めているのは cost 構造**であって、"
            "signal の質ではない"
        ),
    },
}

#: ------------------------------------------------------------------
#: 2026-09-22 第 2 裁定 §1–§2 — **null の棄却と development economics を分ける**
#: ------------------------------------------------------------------
#:
#: 初版は `permutation p ≤ 0.05` を進行の唯一の hard gate にしていた。裁定はこれを退けた:
#:
#:     p > 0.05 -> automatically NOT_SUPPORTED   は禁止
#:     p ≤ 0.05 だから candidate 成立            とも扱わない
#:
#: `UNDERPOWERED_FOR_CONFIRMATION != NOT_WORTH_DEVELOPING`。development は sign / 大きさ /
#: net economics / benchmark 増分 / 安定性 / breadth / 集中 / monetizability を screen する工程で、
#: formal confirmation は別工程である。

#: **null 診断。** 判定の材料の 1 つであって、唯一の gate ではない。
NULL_DIAGNOSTIC: Final[dict[str, Any]] = {
    "id": "PERMUTATION_NULL_DIAGNOSTIC",
    "judged_on": "primary span（PRIMARY_SPAN_RULE で決まる）",
    "statistic": "net Sharpe",
    "labels": {
        "NULL_REJECTION_SUPPORTED": "net > 0 かつ circular-shift permutation p ≤ 0.05",
        "NULL_REJECTION_NOT_SUPPORTED": "それ以外",
    },
    "permutation": {
        "method": "CIRCULAR_SHIFT_PRESERVING_THE_SIGNAL_AUTOCORRELATION",
        "draws": 1000,
        "seed": 20260922,
        "why_not_shuffle": (
            "行を混ぜると turnover が跳ね上がり、『回転が少ないので cost を払わない』という"
            "性質まで壊れる。それでは gate の通りやすさを測ったことにならない"
        ),
    },
    "reported": ("null distribution", "null pass probability", "observed percentile", "p-value"),
    "is_the_only_gate": False,
    "multiplicity": (
        "最大 5 本を同じ null に当てるので、**いずれか 1 本が 5% を切る確率は帰無でも約 23%** である。"
        "これを報告に必ず添える。**1 本通ったことを『edge が見つかった』とは書かない**"
    ),
}

#: **development economics。** すべて primary span で判定する。結果を見る前に凍結する。
DEVELOPMENT_ECONOMICS: Final[dict[str, Any]] = {
    "id": "DEVELOPMENT_ECONOMICS",
    "criteria": {
        "E1_net_positive": "net Sharpe > 0",
        "E2_gross_positive": "gross Sharpe > 0",
        "E3_incremental_information": "incremental IC（FX own momentum 20d を除いた残差）> 0",
        "E4_temporal_stability": "正の temporal block の割合 ≥ 0.5",
        "E5_breadth": "leave-one-currency-out の最悪 net Sharpe > 0（1 通貨で持っていない）",
        "E6_concentration": "上位 10 日の寄与 ≤ net 合計の 0.5",
        "E7_cost_robustness": "cost ×2 でも net Sharpe > 0",
        "E8_economic_magnitude": "net Sharpe ≥ 0.30（vol 10% で年 3% 相当）",
    },
    "core": (
        "E1_net_positive",
        "E3_incremental_information",
        "E4_temporal_stability",
        "E7_cost_robustness",
    ),
    "supported_when": "E1–E8 すべて真 → DEVELOPMENT_ECONOMICS_SUPPORTED",
    "reported_not_required": {
        "E9_other_span_sign": "もう一方の span の gross Sharpe の符号（replication の診断）",
    },
}

#: **Stage 2 の適格条件。** p ≤ 0.05 を唯一条件にしない（第 2 裁定 §34）。
STAGE_2_ELIGIBILITY: Final[dict[str, Any]] = {
    "conditions": (
        "DEVELOPMENT_ECONOMICS の core（E1 / E3 / E4 / E7）がすべて真",
        "null における observed percentile ≥ 0.80（p ≤ 0.20）",
    ),
    "model_if_eligible": (
        "forward return を、凍結した signal と control の 2 変数へ回帰する single linear model のみ。"
        "interaction も feature 追加も無い。**非線形 ML は禁止**"
    ),
    "is_confirmation": False,
    "if_not_eligible": "Stage 2 へは進まない。**Stage 1 の結果は記録する**",
}

#: **判定規則。** 上から順に最初に当てはまるものを採る。結果を見た後に変えない。
VERDICT_LOGIC: Final[tuple[dict[str, str], ...]] = (
    {"if": "rename gate が閾値を超えた", "then": "RENAME_OF_A_CLOSED_TRACK"},
    {"if": "E1 が偽（net ≤ 0）", "then": "NOT_SUPPORTED_IN_SEEN_DEVELOPMENT"},
    {
        "if": "DEVELOPMENT_ECONOMICS_SUPPORTED かつ NULL_REJECTION_SUPPORTED",
        "then": "STRONG_DEVELOPMENT_CANDIDATE",
    },
    {
        "if": "core がすべて真 かつ null percentile ≥ 0.80",
        "then": "MARGINAL_DEVELOPMENT_CANDIDATE",
    },
    {"if": "E1 は真だがそれ以外", "then": "POSITIVE_EXPLORATORY_SIGNAL_NOT_DECISION_GRADE"},
)

#: negative のときの失敗分類。
FAILURE_CLASS_RULE: Final[dict[str, str]] = {
    "gross ≤ 0": "SIGNAL_FAILURE",
    "gross > 0 かつ net ≤ 0": "COST_FAILURE",
    "net > 0 だが E5 または E6 が偽": "CONCENTRATION_FAILURE（exploratory の留保として付す）",
}

#: ------------------------------------------------------------------
#: 裁定 §H — nuisance 定数
#: ------------------------------------------------------------------

#: economic meaning を持たない定数は、**primary + 事前登録した感度集合**で凍結する。
#: 結果を見た後に best point を選ばない。**感度全体を報告する。**
NUISANCE_CONSTANTS: Final[dict[str, dict[str, Any]]] = {
    "max_staleness_days": {
        "primary": 75,
        "sensitivity_set": (45, 60, 75, 90, 120),
        "meaning": "低頻度 series の値を、次の公表が来るまで何暦日まで使ってよいか",
        "why_it_has_no_economic_content": "『古すぎる』の線は事務上の取り決めであって、機構ではない",
    },
    "z_window": {
        "primary": 252,
        "sensitivity_set": (126, 252, 504),
        "meaning": "signal を標準化する窓",
        "why_it_has_no_economic_content": "標準化の窓長は signal の意味を変えない",
    },
    "change_window_months": {
        "primary": 12,
        "sensitivity_set": (6, 12, 24),
        "meaning": "低頻度 series の変化を測る窓（月）",
        "why_it_has_no_economic_content": "『変化』の定義幅で、機構が決める値ではない",
    },
    "implementation_tolerance_band": {
        "primary": 0.10,
        "sensitivity_set": (0.05, 0.10, 0.20),
        "meaning": "建玉を動かさない帯（執行の実装許容）",
        "why_it_has_no_economic_content": "執行側の都合であって、期待リターンの源泉ではない",
    },
}

NUISANCE_RULE: Final[str] = (
    "**primary 値で判定し、感度集合の全点を報告する。** "
    "感度集合の中から良い点を選び直すことは、結果を見た後であれば post-hoc であり禁止。"
    "前 cycle では `max_staleness_days` を結果を見た後に決め、**その値が試した 9 点の最大**だった"
)

#: ------------------------------------------------------------------
#: 5 本
#: ------------------------------------------------------------------

TRACKS: Final[dict[str, dict[str, Any]]] = {
    "U1": {
        "candidate": "S29",
        "name": "実体貿易 flow → 通貨",
        "mechanism": (
            "財・サービスの純輸出は、決済のための**実需の通貨需要**を生む。"
            "黒字が拡大する通貨には買い需要が、赤字が拡大する通貨には売り需要が、"
            "景気循環の速さで積み上がる"
        ),
        "data": "各国の月次 貿易収支 / 純輸出（FRED 経由の OECD / 各国統計）",
        "frequency": "monthly",
        "primary_span": "long",
        "publication_lag": (
            "第 m 月の値は m+1 〜 m+2 月に公表される。**m+2 月末以降にのみ使用する**"
            "（前 cycle の TIC と同じ保守側の規約）"
        ),
        "signal": "通貨ごとに『貿易収支の 12 か月変化』を z 化し、cross-section で相対化する",
        "direction": "貿易収支が改善した通貨は**上昇**",
        "horizon": "1〜3 か月（日次 book として保有）",
        "expected_turnover_per_unit_gross": "5〜12 RT/年",
        "why_it_is_not_a_rename": (
            "S26（TIC）は **US の証券投資 flow**で主体は投資家。S29 は **G10 各国の財・サービス収支**で"
            "主体は企業と家計。S13（実質為替 valuation）は価格水準であって flow ではない"
        ),
        "declared_expectation": (
            "**breadth が構造的に大きい**（8 通貨すべてが公表する）。"
            "前 cycle で breadth 1 が致命的だったことへの直接の対処になる"
        ),
        "revision_caveat": (
            "**貿易統計は改訂される。** 取得できるのは現行 vintage であって決定時点の値ではない。"
            "公表 lag 規約はこれを直さない — 『公表されていたか』と『その値だったか』は別の要件である。"
            "無料の範囲では塞げないので、**楽観側に働く留保として明記する**"
        ),
    },
    "U2": {
        "candidate": "S25",
        "name": "中銀 balance sheet の相対ペース → 通貨",
        "mechanism": (
            "QE / QT は自国通貨建て負債の供給量を変える。"
            "相対的に速く膨らむ通貨は、他の条件が同じなら供給過多になる"
        ),
        "data": "各中銀の総資産（FRED 経由。Fed 週次・ECB 週次・BoJ 月次 など）",
        "frequency": "weekly_to_monthly",
        "primary_span": "long",
        "publication_lag": "公表日の **2 営業日後**から使用",
        "signal": "総資産の 12 か月 log 変化を z 化し、cross-section で相対化する",
        "direction": "相対的に速く拡大した通貨は**下落**",
        "horizon": "1〜6 か月",
        "expected_turnover_per_unit_gross": "4〜10 RT/年",
        "why_it_is_not_a_rename": (
            "政策金利（H-016）や市場利回り（S01）は**価格**。balance sheet は**数量**である。"
            "どちらも『金融政策』だが、測っている変数が違う"
        ),
        "declared_expectation": "breadth は中程度（主要 4〜5 中銀）。**全 8 通貨は揃わない**",
    },
    "U3": {
        "candidate": "S27",
        "name": "中銀 communication の tone 変化 → 通貨",
        "mechanism": (
            "声明文の hawkish / dovish への傾きは、次の政策の方向を先に示す。"
            "市場が織り込むより先に通貨需要が動く余地がある"
        ),
        "data": "各中銀の公開テキスト（声明・議事要旨）",
        "frequency": "event_paced",
        "primary_span": "recent",
        "publication_lag": "テキストの公表時刻の **1 営業日後**から使用",
        "signal": (
            "**凍結した語彙表**による hawkish 語数 − dovish 語数を文書長で割り、"
            "前回会合からの変化を取る。**語彙表は結果を見る前に固定し、以後変更しない**"
        ),
        "direction": "hawkish 側へ動いた通貨は**上昇**",
        "horizon": "1〜20 営業日",
        "expected_turnover_per_unit_gross": "6〜18 RT/年",
        "why_it_is_not_a_rename": (
            "会合日の値動き（H-019）と決定そのもの（C01）は扱ったが、"
            "**テキストの内容**は一度も取得していない"
        ),
        "declared_expectation": (
            "**Stage 0 で落ちる公算が最も高い track。** 時刻付き過去テキストの機械取得が"
            "未確認で、`ranking.py` でも public-data reproducibility が 8 本中最低だった"
        ),
        "no_ml": "語彙表は固定。学習も当てはめもしない（Stage 1 は unfitted rule のみ）",
    },
    "U4": {
        "candidate": "S31",
        "name": "公的外貨準備の変化 → 通貨",
        "mechanism": (
            "中銀・財務省が外貨準備を積み増すことは、**自国通貨を売って外貨を買う**ことである。"
            "取り崩しはその逆。介入と再配分が直接に為替需給を動かす"
        ),
        "data": "各国の月次 外貨準備高（FRED 経由 / IMF）",
        "frequency": "monthly",
        "primary_span": "long",
        "publication_lag": "第 m 月の値は m+1 月初に公表される。**m+1 月末以降にのみ使用する**",
        "signal": "外貨準備の 3 か月変化を自国 GDP 規模で正規化せず、**z 化して cross-section 相対化**",
        "direction": "準備を積み増した通貨は**下落**（自国通貨を売っているため）",
        "horizon": "1〜3 か月",
        "expected_turnover_per_unit_gross": "6〜15 RT/年",
        "why_it_is_not_a_rename": (
            "S25 は**自国通貨建て balance sheet の大きさ**、S26 は**民間の証券投資**、"
            "S31 は**公的部門の外貨売買**。主体も通貨も経路も違う。"
            "**それでも rename gate を置いてある**（RENAME_GATES）"
        ),
        "declared_expectation": (
            "**breadth が小さいと予想する。** G10 で準備を能動的に動かしてきたのは実質 CHF（SNB）と "
            "JPY（MOF）で、他は受動的である。**T5 が USD 一軸だったのと同じ構造的弱点**を、"
            "結果を見る前に宣言しておく"
        ),
    },
    "U5": {
        "candidate": "S07",
        "name": "信用 spread・funding stress → 安全通貨",
        "mechanism": (
            "社債 spread の拡大は funding 市場の緊張を表し、"
            "レバレッジの巻き戻しが安全通貨（USD・JPY・CHF）需要に先行する"
        ),
        "data": "US HY OAS / IG OAS / SOFR（FRED 日次）",
        "frequency": "daily",
        "primary_span": "recent",
        "publication_lag": "**2 営業日後**から使用",
        "signal": "OAS の 5 日変化を 252 日 z 化し、凍結 beta へ射影する",
        "direction": {
            "beta": {
                "USD": 0.5,
                "JPY": 1.0,
                "CHF": 1.0,
                "EUR": 0.0,
                "GBP": -0.5,
                "CAD": -0.5,
                "AUD": -1.0,
                "NZD": -1.0,
            },
            "reading": "spread が拡大した日は安全通貨が上昇、資源国通貨が下落",
        },
        "horizon": "5〜20 営業日",
        "expected_turnover_per_unit_gross": "18〜43 RT/年",
        "why_it_is_not_a_rename": (
            "**向きは S05（T1）と同じ『risk-off → 安全通貨』である。情報源だけが違う。**"
            "だから rename gate を置く（閾値 0.8）。"
            "**超えたら結果にかかわらず NOT_SUPPORTED とする** — これは結果を見る前の宣言である"
        ),
        "declared_expectation": (
            "**5 本で最も不利な条件を持つ。** breadth が最小（実効 1〜2）、turnover が最大、"
            "そして向きが既に落ちた track と同じ。ranking では 5 位で、S15 と同点を "
            "次元 2（価格超の増分情報）で割った結果ここにいる"
        ),
    },
}

#: ------------------------------------------------------------------
#: Stage 0 の結果（裁定 §K）。**alpha ではない。** 取得可能性だけの記録である。
#: ------------------------------------------------------------------

#: **この環境から FRED へ到達できなかった。** 19 URL すべて timeout。
#: 一方 federalreserve.gov / ecb.europa.eu / data.snb.ch / bankofcanada.ca /
#: bankofengland.co.uk は HTTP 200 を返した。**FRED だけが届かない。**
#:
#: これは「無料のデータが無い」ではない。**series は無料で存在する。**
#: 取り違えると、次の判断が paid data へ不必要に向かう。
STAGE_0_OUTCOME: Final[dict[str, Any]] = {
    "probe_records": (
        "artifacts/research/next_five/stage0_probe.json",
        "artifacts/research/next_five/stage0_probe_direct.json",
    ),
    "fred_reachability": "ALL_19_URLS_TIMED_OUT_FROM_THIS_ENVIRONMENT",
    "hosts_that_answered": (
        "www.federalreserve.gov",
        "www.ecb.europa.eu",
        "data-api.ecb.europa.eu",
        "data.snb.ch",
        "www.bankofcanada.ca",
        "www.bankofengland.co.uk",
    ),
    "verified_series_found": {
        "CHF_total_assets": "SNB cube snbbipo, D0=T0（provider の dimension 一覧で確認）",
        "CHF_fx_reserves": "SNB cube snbbipo, D0=D（Foreign currency investments）",
        "CAD_total_assets": "Bank of Canada valet V36651（group B1_MONTHLY のラベルで確認）",
    },
    "guesses_that_were_wrong_and_how_we_knew": (
        "BoC V36612 は自己申告で『Treasury Bills』であり総資産ではなかった",
        "BoE LPMB8LU は HTTP 200 で **HTML のエラーページ**を返した（200 = data ではない）",
        "ECB ILM A050100 は『Main refinancing operation』であり総資産ではなかった",
        "ECB ILM は資産・負債の個別項目しか公開しておらず、**総資産の系列が無い**",
    ),
    "per_track": {
        "U1": {
            "status": "DATA_NOT_RETRIEVABLE_FROM_THIS_ENVIRONMENT_PROVIDER_UNAFFECTED",
            "verified_currencies": 0,
            "needed": 3,
            "why": "月次貿易収支は FRED 経由が実務上の唯一の集約点で、8 URL すべて timeout。各国統計局の直接経路は 4 試行すべて 404",
        },
        "U2": {
            "status": "DATA_NOT_RETRIEVABLE_FROM_THIS_ENVIRONMENT_PROVIDER_UNAFFECTED",
            "verified_currencies": 2,
            "needed": 3,
            "why": "CHF と CAD の総資産は provider カタログで確認できたが、**3 通貨目が取れない**。Fed は FRED 経由、ECB の ILM には総資産の系列が無い",
        },
        "U3": {
            "status": "DATA_NOT_RETRIEVABLE_FROM_THIS_ENVIRONMENT_PROVIDER_UNAFFECTED",
            "verified_currencies": 2,
            "needed": 3,
            "why": "Fed と ECB の声明 index は到達したが BoE は不可。**2 通貨の cross-section は demean 後に互いの鏡像**になり breadth 1 になる",
        },
        "U4": {
            "status": "DATA_NOT_RETRIEVABLE_FROM_THIS_ENVIRONMENT_PROVIDER_UNAFFECTED",
            "verified_currencies": 1,
            "needed": 3,
            "why": "SNB の外貨投資のみ確認。他は FRED 経由か、推定した series code が 404 / HTML",
        },
        "U5": {
            "status": "DATA_NOT_RETRIEVABLE_FROM_THIS_ENVIRONMENT_PROVIDER_UNAFFECTED",
            "verified_currencies": 0,
            "needed": 1,
            "why": "HY OAS の無料配信は実質 FRED 経由のみ。**代替の無料経路が存在しない**",
        },
    },
    "what_was_not_done_and_why": (
        "**2 通貨で cross-section を組むことはしなかった。** demean 後に互いの鏡像になり "
        "breadth 1 になる — 前 cycle の T5 を決定不能にしたのと同じ構造である。"
        "凍結した signal は cross-section を要求しており、**通貨数を下げて走らせるのは "
        "凍結の変更**であって実行ではない"
    ),
    "what_would_unblock_it": (
        "**paid data ではない。** 必要なのは (a) FRED へ到達できる network 経路、"
        "または (b) 各 provider のカタログから series を特定する作業である。"
        "後者は CHF と CAD で実際に成功しており、**手間の問題であって可用性の問題ではない**"
    ),
}

EXECUTION_ORDER: Final[tuple[str, ...]] = ("U1", "U2", "U3", "U4", "U5")

#: 共通で報告する指標（裁定 §L）。
METRICS: Final[tuple[str, ...]] = (
    "gross_sharpe",
    "net_sharpe",
    "net_annual_return",
    "ic",
    "incremental_ic",
    "turnover_per_unit_gross",
    "annual_cost",
    "signal_persistence",
    "positive_temporal_blocks",
    "currency_breadth",
    "concentration",
    "top_day_dependence",
    "max_drawdown",
    "cost_stress_x1_5",
    "cost_stress_x2_0",
)

#: net が正のときだけ追加で出すもの（裁定 §L）。
CAPACITY_REPORTING: Final[dict[str, Any]] = {
    "target_vol_scenarios": (0.08, 0.10, 0.12, 0.15),
    "annual_return_targets": (0.05, 0.10),
    "also_report": (
        "risk_leverage",
        "portfolio_gross",
        "pair_specific_margin",
        "scaled_max_drawdown",
        "gap_stress_2pct_adverse",
        "remaining_margin_buffer",
    ),
    "forbidden": (
        "5x を feasibility の hard cap として使うこと",
        "broker の 20x / 25x を risk target として使うこと",
    ),
}

#: per-track の最終 status 語彙。
TRACK_STATUS_SUFFIXES: Final[tuple[str, ...]] = (
    "STRONG_DEVELOPMENT_CANDIDATE",
    "MARGINAL_DEVELOPMENT_CANDIDATE",
    "POSITIVE_EXPLORATORY_SIGNAL_NOT_DECISION_GRADE",
    "NOT_SUPPORTED_IN_SEEN_DEVELOPMENT",
    "DATA_NOT_DECISION_GRADE",
    "DATA_UNAVAILABLE_WITH_CURRENT_FREE_SOURCES",
    #: **到達できないことと、存在しないことは違う。**
    #: Stage 0 で FRED の 19 URL が全て timeout した。series は無料で存在するので
    #: `DATA_UNAVAILABLE_WITH_CURRENT_FREE_SOURCES` と書くと事実に反し、
    #: 将来の読者を**誤って有料データ購入へ向かわせる**。
    "DATA_NOT_RETRIEVABLE_FROM_THIS_ENVIRONMENT_PROVIDER_UNAFFECTED",
    "RENAME_OF_A_CLOSED_TRACK",
)

#: **凍結は alpha を見る前に 1 度だけ動いた。** 上の suffix を足したためである。
#: 動かした時点で signal は 1 本も走っておらず（Stage 0 で全 track が data-blocked）、
#: **結果を見て語彙を変えたのではない**。前 cycle の `SUPERSEDED_PRE_EXECUTION` と同じ性質。
FREEZE_AMENDMENT_PRE_ALPHA: Final[dict[str, str]] = {
    "digest_before": "e647629fcddc68751ca91906c98089cd6efc529a47d84f8c57070a6921f324f3",
    "status": "AMENDED_PRE_ALPHA_NO_SIGNAL_HAD_RUN",
    "what_changed": "TRACK_STATUS_SUFFIXES に DATA_NOT_RETRIEVABLE_FROM_THIS_ENVIRONMENT_PROVIDER_UNAFFECTED を追加",
    "why": (
        "Stage 0 で FRED の 19 URL が全て timeout した。"
        "既存の語彙では『無料ソースが無い』としか書けず、**それは事実に反する** — "
        "series は無料で存在し、この環境から到達できないだけである。"
        "誤った token を残すと、次の判断が paid data へ不必要に向かう"
    ),
}

NEGATIVE_CLASSES: Final[tuple[str, ...]] = (
    "SIGNAL_FAILURE",
    "COST_FAILURE",
    "DATA_FAILURE",
    "CONCENTRATION_FAILURE",
    "IMPLEMENTATION_FAILURE",
)

#: 5 本を同じ枠組みで探索していることの開示（裁定 §M）。
EXPLORATION_DISCLOSURE: Final[str] = "FIVE_WAY_EXPLORATORY_DEVELOPMENT_SEARCH_NO_CONFIRMATION_CLAIM"

#: 途中で止めるのは共通基盤の欠陥だけ（裁定 §K）。
SHARED_BLOCKERS: Final[tuple[str, ...]] = (
    "common future leak",
    "common cost bug",
    "FX panel bug",
    "portfolio-routing defect",
    "protected-date bug",
)

INTERPRETATION: Final[str] = (
    "**最良 candidate を単に winner とは呼ばない**（裁定 §M）。"
    "formal confirmation の主張はしない。fresh へ自動進行しない。"
    "**帰無が routinely 生む数字は edge ではない**（CORE PRINCIPLE）"
)


#: **alpha を見る前の 2 度目の凍結修正**（第 2 裁定 §1 の必須修正）。
#: まだ signal は 1 本も走っていない（前 run は全 track が Stage 0 で止まった）。
FREEZE_AMENDMENT_GATE_SPLIT: Final[dict[str, str]] = {
    "digest_before": "2e805781d31c6025c9e8c372cd11686ec969d22568a136a91b8c787364f2ba8f",
    "status": "AMENDED_PRE_ALPHA_NO_SIGNAL_HAD_RUN",
    "authority": "2026-09-22 第 2 裁定 §1（PR #491 CONDITIONAL MERGE APPROVED の条件）",
    "what_changed": (
        "ADVANCE_GATE（permutation p ≤ 0.05 を唯一の hard gate とする）を廃し、"
        "NULL_DIAGNOSTIC / DEVELOPMENT_ECONOMICS / STAGE_2_ELIGIBILITY / VERDICT_LOGIC に分けた"
    ),
    "why": (
        "p > 0.05 を自動的に NOT_SUPPORTED にすると、development を confirmation の基準で"
        "裁くことになる（UNDERPOWERED_FOR_CONFIRMATION != NOT_WORTH_DEVELOPING）。"
        "逆に p ≤ 0.05 だけで candidate 成立ともしない"
    ),
}


def track_status(track: str, suffix: str) -> str:
    if suffix not in TRACK_STATUS_SUFFIXES:
        raise ValueError(f"未登録の status: {suffix}")
    return f"{track}_{TRACKS[track]['candidate']}_{suffix}"


def _payload() -> dict[str, Any]:
    """**凍結の中身。** ここに無いものは凍結されていない。"""
    return {
        "cycle": CYCLE,
        "authority": AUTHORITY,
        "workflow_status": WORKFLOW_STATUS,
        "forbidden_next_steps": list(FORBIDDEN_NEXT_STEPS),
        "forbidden_rescues": list(FORBIDDEN_RESCUES),
        "universe": list(UNIVERSE),
        "spans": SPANS,
        "protected_bounds": PROTECTED_BOUNDS,
        "primary_span_rule": PRIMARY_SPAN_RULE,
        "execution_layer": EXECUTION_LAYER,
        "book_config": BOOK_CONFIG,
        "book_config_deviations": BOOK_CONFIG_DEVIATIONS,
        "cost": COST,
        "benchmarks": list(BENCHMARKS),
        "control": CONTROL,
        "rename_gates": RENAME_GATES,
        "demoted_gate": DEMOTED_GATE,
        "null_diagnostic": NULL_DIAGNOSTIC,
        "development_economics": DEVELOPMENT_ECONOMICS,
        "stage_2_eligibility": STAGE_2_ELIGIBILITY,
        "verdict_logic": [dict(row) for row in VERDICT_LOGIC],
        "failure_class_rule": FAILURE_CLASS_RULE,
        "nuisance_constants": NUISANCE_CONSTANTS,
        "nuisance_rule": NUISANCE_RULE,
        "tracks": TRACKS,
        "execution_order": list(EXECUTION_ORDER),
        "stage_0_outcome": STAGE_0_OUTCOME,
        "metrics": list(METRICS),
        "capacity_reporting": CAPACITY_REPORTING,
        "track_status_suffixes": list(TRACK_STATUS_SUFFIXES),
        "freeze_amendment_pre_alpha": FREEZE_AMENDMENT_PRE_ALPHA,
        "freeze_amendment_gate_split": FREEZE_AMENDMENT_GATE_SPLIT,
        "negative_classes": list(NEGATIVE_CLASSES),
        "exploration_disclosure": EXPLORATION_DISCLOSURE,
        "shared_blockers": list(SHARED_BLOCKERS),
        "interpretation": INTERPRETATION,
    }


def freeze_digest() -> str:
    """凍結内容の sha256。**これが変わったら、それは別の事前登録である。**

    `default` を渡さない: JSON 化できない値が入ったら黙って `str()` にせず落ちる。
    """
    return hashlib.sha256(
        json.dumps(_payload(), sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()


__all__ = [
    "AUTHORITY",
    "BENCHMARKS",
    "BOOK_CONFIG",
    "BOOK_CONFIG_DEVIATIONS",
    "CAPACITY_REPORTING",
    "CONTROL",
    "COST",
    "CYCLE",
    "DEMOTED_GATE",
    "DEVELOPMENT_ECONOMICS",
    "FAILURE_CLASS_RULE",
    "EXECUTION_LAYER",
    "EXECUTION_ORDER",
    "EXPLORATION_DISCLOSURE",
    "FORBIDDEN_NEXT_STEPS",
    "FREEZE_AMENDMENT_GATE_SPLIT",
    "FREEZE_AMENDMENT_PRE_ALPHA",
    "FORBIDDEN_RESCUES",
    "INTERPRETATION",
    "METRICS",
    "NEGATIVE_CLASSES",
    "NULL_DIAGNOSTIC",
    "NUISANCE_CONSTANTS",
    "NUISANCE_RULE",
    "PRIMARY_SPAN_RULE",
    "PROTECTED_BOUNDS",
    "RENAME_GATES",
    "SHARED_BLOCKERS",
    "STAGE_0_OUTCOME",
    "SPANS",
    "STAGE_2_ELIGIBILITY",
    "TRACKS",
    "TRACK_STATUS_SUFFIXES",
    "UNIVERSE",
    "VERDICT_LOGIC",
    "WORKFLOW_STATUS",
    "freeze_digest",
    "track_status",
]
