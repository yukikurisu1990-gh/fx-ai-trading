# ruff: noqa: E501 -- pre-registration prose
"""5 本の **凍結された** 事前登録。1 本目の結果を見る前に全て確定している（裁定 §10）。

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

**なぜ一括で凍結するのか。** 1 本ずつ結果を見て次を調整すると、5 本は 5 つの独立な
検定ではなく、1 本の長い探索になる。そうなると「どの情報源に兆候があるか」という
問いに答えられない — 答えは常に「最後に調整した方向」になるからである。

**この版は初稿ではない。** 初稿は 2 つの独立レビューに通され、10 件の blocker が出た。
うち実際に凍結を壊していたもの（lag の向き・OOS 境界・digest の網羅漏れ・
発火しない gate・使えない data 形式・leverage 規約の欠落）をすべて直した上で再凍結した。
**直した内容は 1 つも alpha に依存していない** — すべて結果を見る前に決まる事柄である。
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Final

from scripts.research.top_five import (
    CYCLE,
    FORBIDDEN_NEXT_STEPS,
    OUTCOMES,
    UNIVERSE,
    WORKFLOW_STATUS,
)

# ---------------------------------------------------------------------------
# 権限
# ---------------------------------------------------------------------------

#: **凍結した signal の数値定数。** これが `signals.py` にしか無かったのは穴だった —
#: TRACKS の散文には「5 日」「252 日」と書いてあるが、`signals.py` の数値だけを変えても
#: digest は動かない。`prereg` は BookConfig について同じ失敗を自分で見つけて直している
#: （「関数名の文字列しか凍結しておらず既定値が変われば digest が動かないまま別の実験に
#: なっていた」）のに、signal 側で同じ穴が残っていた。**実行後のレビューで指摘された。**
#:
#: **実行時にこれらが凍結値だったことは確認済み**である（再実行が 548 日 / net 0.672 を
#: 再現した）。値は 1 つも変えていない — digest が覆う範囲を広げただけである。
SIGNAL_CONSTANTS: Final[dict[str, int]] = {
    "z_window": 252,
    "shock_lookback": 5,
    "slope_lookback": 20,
    "factor_window": 120,
    "partner_window": 252,
    "tic_window_months": 12,
    #: **暦日**で数える。初版は「行数」で数えており、union index が 2016-05-31 と
    #: 2021-04-28 の間に 1 行も持たないため、**1 行で 5 年の空白を跨いで**いた。
    #: 実測で近 span 初日が 1,792 日前の値を使っていた。宣言した意図（次の公表が
    #: 来るはずの幅）に実装を合わせた。
    "max_staleness_days": 75,
}

#: 実行に使われた digest。**この値は書き換えない。**
#: SIGNAL_CONSTANTS を payload に足したので現在の `freeze_digest()` はこれと異なる。
#: 走った設計はこちらであり、差は「覆う範囲」だけである。
DIGEST_AS_EXECUTED: Final[str] = "28100ebedfea45765371585df5c4308fee261e2496a9798acca79c920158962c"

#: 旧 freeze。**削除せず履歴として保持する**（2026-09-21 裁定 §1）。
#: alpha を 1 本も見る前に差し替えたので、これは post-result rescue ではない。
SUPERSEDED_FREEZE: Final[dict[str, str]] = {
    "digest": "29ba80d68a5462fe015a6f2566d3c0b63319d0549de7b9a4d34a890f2339b1ca",
    "status": "SUPERSEDED_PRE_EXECUTION",
    "commit": "0702d97",
    "why": (
        "2026-09-21 裁定が T3 の符号を dual-hypothesis へ、leverage の解釈を三概念の"
        "分離と target-vol scenario へ、acquisition を承認済みへ改めた。"
        "**この時点で alpha は 1 本も見られていない**"
    ),
}

#: **実行後に入れた訂正の記録。** 2026-09-21 裁定は「結果を見る前に凍結」を求めており、
#: ここに並ぶ 3 件はいずれも **結果を見た後**に入った。だから「凍結どおり走った」とは書けない。
#: 何がどちらの性質かを分けて残す — leakage の閉塞は入れないと結果が無効になるが、
#: nuisance 定数の値決めは **researcher degrees of freedom** そのものだからである。
POST_EXECUTION_CORRECTIONS: Final[dict[str, Any]] = {
    "digest_before": DIGEST_AS_EXECUTED,
    "status": "CORRECTED_AFTER_RESULTS_WERE_SEEN_NOT_A_CLEAN_PREREGISTERED_RUN",
    "why_recorded_here": (
        "digest が動いた事実は test が押さえているが、**何がなぜ動いたか**は digest からは"
        "読めない。後から読む人が「凍結どおりの 1 回」と誤読しないように、"
        "訂正の中身を凍結 payload の中へ置く"
    ),
    "corrections": (
        {
            "id": "C-1",
            "kind": "LEAKAGE_CLOSURE",
            "what": (
                "`signals._two_year` が取得層の `_truncate` を通らず parquet を直読みしており、"
                "`*_2y.parquet` が持つ保護 pool と forward epoch の行（通貨により 510-2,092 行、"
                "最大 2026-09-15）が slope 計算へ入っていた"
            ),
            "measured_impact": (
                "近 span の score 3 日（2021-05-11 / 05-26 / 05-27）が保護 pool の値に依存。"
                "**doc が書いていた『fresh pool 未読』は、この leg については偽だった**"
            ),
            "discretion": "無し。塞がなければ結果が無効になる一方向の修正である",
        },
        {
            "id": "C-2",
            "kind": "UNIT_BUG_FIX_PLUS_A_CHOSEN_CONSTANT",
            "what": (
                "staleness 上限を `ffill(limit=45)` の **行数**で数えていた。union index は "
                "2016-05-31 と 2021-04-28 の間に 1 行も持たないので、**1 行で 1,792 日**を"
                "跨いでいた。暦日で数えるよう直した"
            ),
            "measured_impact": "近 span 初日が vintage 2016-05-31 の値を使っていた",
            "discretion": (
                "**ある。** 暦日へ直すこと自体は一方向の修正だが、**75 日という値は新しく"
                "選んだ数**である（旧値は 45 行で、単位が違うので移せない）。"
                "感度は `stage2.py` が測って artefact に残す — "
                "**T5 の net Sharpe は 45-400 日で +0.56 … +0.84 と動き、凍結値 75 は"
                "試した格子のほぼ上端に当たる。報告値は楽観側である**"
            ),
        },
        {
            "id": "C-3",
            "kind": "MISSING_NULL_ADDED",
            "what": "`constant_long_usd`（signal を見ずに USD を買い持ちする book）を benchmark へ追加",
            "measured_impact": "T5 の近 span 増分は net +0.838 に対し null +0.260 で **+0.578**",
            "discretion": (
                "**唯一の正の結果を弱める方向にしか働かない**追加であり、candidate の設計は"
                "1 つも変えていない。それでも『結果を見た後に足した benchmark』である事実は残す"
            ),
        },
    ),
    "what_this_does_not_excuse": (
        "C-1 と C-2 は **実行前に閉じているべきだった**。5 本を凍結してから走らせる設計の"
        "目的は、まさにこの種の事後調整を不可能にすることだった。**次の cycle では、"
        "外部 series を読む経路を 1 本に強制し、そこを通らない読み出しを test で禁じる**"
    ),
}

#: 本 cycle の authority。**2026-09-19 裁定の全文は今も repo に無い**ので、
#: その節番号への引用は検証不能である。その事実ごと持ち回る（#489 が立てた token）。
AUTHORITY: Final[dict[str, str]] = {
    "record": "docs/governance/m15_adjudication_2026_09_19_and_09_20.md",
    "2026_09_20": "全文がセッションに与えられ、decision record §2 に記録されている",
    "2026_09_19": "PRIOR_ADJUDICATION_TEXT_NOT_IN_REPO_CITATIONS_UNVERIFIABLE",
}

# ---------------------------------------------------------------------------
# 共通枠組 — 5 本で同一にすることが比較可能性の前提である
# ---------------------------------------------------------------------------

#: **lag 規約。初稿はここを取り違えていた。**
#:
#: 初稿は「米国の引け値が同じ日の欧州 fix を動かすことは物理的にありえない」と書いたが、
#: それは fix(t) が VIX(t) に汚染されていないことの証明であって、**VIX(t) で fix(t) の
#: 建玉を決めてよいことの証明ではない**。むしろ逆である: VIX close(22:15 CET) は
#: ECB fix(14:15 CET) の 8 時間後なので、fix(t) で建てる book に VIX(t) を使えば
#: **8 時間の先読み**になる。
#:
#: 正しい規約は 1 本しかない: **外部値は、その公表時刻より後に始まる return 窓にしか
#: 入れてよくない。** 実装は source ごとの公表時刻表（PUBLICATION_TIMES）で決まる。
TIMESTAMP_RULE: Final[str] = (
    "AN_EXTERNAL_VALUE_MAY_ONLY_INFORM_A_RETURN_WINDOW_THAT_BEGINS_STRICTLY_AFTER_ITS_PUBLICATION"
)

#: 公表時刻（CET 基準）と、そこから決まる lag。**推定ではなく publisher の仕様である。**
#: 長 span の return 窓は ECB fix(t) → fix(t+1)、近 span は UTC 日足 close(t) → close(t+1)。
PUBLICATION_TIMES: Final[dict[str, dict[str, Any]]] = {
    "cboe_vix_close": {
        "published_cet": "22:15",
        "long_span_lag_business_days": 2,
        "recent_span_lag_business_days": 1,
        "why": "ECB fix 14:15 CET より後。近 span の UTC 日足 close(22:00 CET) より 45 分前",
    },
    "eia_wti_daily": {
        "published_cet": "週次サイクル（水曜更新、day t の値は 1〜7 暦日遅れ）",
        "long_span_lag_business_days": 7,
        "recent_span_lag_business_days": 7,
        "why": (
            "EIA の spot は Weekly Petroleum Status Report と同じ水曜サイクルで更新される。"
            "**日次公表ではない** — 初稿の 1 日 lag は両 span で不足だった。"
            "最悪ケース（次の水曜）で凍結する"
        ),
    },
    "sovereign_curves": {
        "published_cet": "各国夕刻（US 21:30-24:00, BoC 22:30, Bundesbank 夕刻, SNB 同等以降）",
        "long_span_lag_business_days": 2,
        "recent_span_lag_business_days": 2,
        "why": (
            "いずれも ECB fix より後。近 span でも US Treasury は 17:00 ET を越える日が"
            "あるので、両 span とも 2 日に倒す"
        ),
    },
    "tic_monthly": {
        "published_cet": "第 m 月の値は m+2 月中旬",
        "long_span_lag_business_days": "m+2 月末以降（月次規約）",
        "recent_span_lag_business_days": "同上",
        "why": "初回公表への保守側の倒し。ただし改訂は別問題（REVISION_CAVEAT 参照）",
    },
    "fx_internal": {
        "published_cet": "同一 panel 内",
        "long_span_lag_business_days": 1,
        "recent_span_lag_business_days": 1,
        "why": "T4 は外部データを使わないので、実行層の 1 日規約がそのまま正しい",
    },
}

#: TIC は**改訂される**。m+2 規約は初回公表のタイミングしか制御しない。
#: 同じ repo の valuation ルートは vintage の取り違えを実際に発見して直している。
REVISION_CAVEAT: Final[str] = (
    "TIC_PUBLISHED_FILE_CARRIES_CURRENT_REVISIONS_NOT_THE_VINTAGE_AVAILABLE_AT_DECISION_TIME"
)

#: 2 つの seen span。保護 pool はこの間にあり、開かない。
#:
#: **近 span の終端を 2025-12-24 に繰り上げた。** 初稿は 2025-12-26 で終えていたが、
#: それは金曜で、その t+1 return は 2025-12-29 = `oos_slice.SLICE_START_UTC`、つまり
#: **OOS の初日**を要求する。R1 で実際に起きた「window の 1 行先を decode した」事故と
#: 同じ形である。規約として書く: **最終 decision day は、その t+1 return が span の
#: 内側に存在する最後の日**。
SPANS: Final[dict[str, dict[str, Any]]] = {
    "long": {
        "first": "1999-01-04",
        "last_decision_day": "2016-05-31",
        "last_return_day": "2016-06-01",
        "source": "ECB euro reference rates, EXPLORATORY_SEEN_DEVELOPMENT_DATA",
        "return_window": "fix(t) -> fix(t+1), 14:15 CET",
    },
    "recent": {
        "first": "2021-04-27",
        "last_decision_day": "2025-12-24",
        "last_return_day": "2025-12-26",
        "source": "the three guarded OANDA M15 routes, EXPLORATORY_SEEN_DATA",
        "return_window": "UTC daily close(t) -> close(t+1)",
    },
}

#: 触れてはならない境界。**parsed date として比較する**（裁定 §19）。文字列比較はしない。
PROTECTED_BOUNDS: Final[dict[str, str]] = {
    "fresh_pool_start": "2016-06-02",
    "development_end": "2025-12-28",
    "oos_slice_start": "2025-12-29",
    "rule": "PARSED_TYPED_DATE_BOUNDS_ONLY_NEVER_STRING_LEXICAL_COMPARE",
    "acquisition": (
        "期間パラメータを取らない endpoint（VIX / EIA / SNB / TIC）は全量配信なので、"
        "取得後に **parsed date で切り落としてから** panel に入れる。切り落とし前の frame を "
        "signal に触れさせない"
    ),
}

#: 執行層は既存のものを再利用する（裁定 §39）。**数値で凍結する** — 初稿は関数名の
#: 文字列しか凍結しておらず、既定値が変われば digest が動かないまま別の実験になっていた。
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
        "既定の 5.0 は placeholder で、**5x を economic feasibility の hard limit として"
        "使うことは禁じられている**。ここに置いた 20.0 は broker の margin ceiling であって "
        "**運用の risk budget ではない** — vol_target 0.10 なら必要 leverage は 4.29x で、"
        "この cap は実際には binding しない。**risk は vol targeting が決める**という"
        "構造を明示するために、cap を ceiling の位置に置いてある。"
        "「20x まで可能だから低い Sharpe でも十分」という読み方は 2026-09-21 裁定 §27 が"
        "明示的に禁じている"
    ),
}

#: T5 だけ既定から外す（開示済みの逸脱）。理由は BLOCKER として指摘されたとおり:
#: T5 の mu は正規化すれば **dollar factor そのもの**であり、`neutralize_leading_factor`
#: が除く PC1 は G10 panel では dollar factor である。既定のままだと **層が仮説を消す**ので、
#: null が「flow に情報が無い」のか「層が消した」のか区別できない。H-025 に同じ形の先例がある。
BOOK_CONFIG_DEVIATIONS: Final[dict[str, dict[str, Any]]] = {
    "T5": {
        "neutralize_leading_factor": False,
        "why": "signal が dollar 方向そのものなので、leading factor 除去は仮説の除去になる",
        "disclosed": True,
    }
}

#: leverage は 3 概念に分ける（2026-09-21 裁定 §22-§28）。
#: **5x を economic feasibility の hard limit として使わない。**
#: **同時に、broker の 20x/25x を通常運用の risk budget として使うことも禁止。**
LEVERAGE_FRAMEWORK: Final[dict[str, Any]] = {
    "A_broker_hard": {
        "value": "20x",
        "source": "artifacts/research/edge_sources/oanda_margin_rates.json（公開仕様のみ）",
        "detail": "研究 universe 28 pair の margin rate は 0.04-0.05。最悪値 0.05 を採る",
        "what_it_is": "**margin 上の absolute ceiling** である。それ以上でも以下でもない",
        "what_it_is_not": (
            "20x の risk scaling が安全だという意味ではない。Sharpe 0.1 でも 20x 掛ければ"
            "有望だという意味でもない。年 5% capacity が実用的だという意味でもない"
        ),
    },
    "B_portfolio_gross": "book が実際に建てた gross。毎日記録する",
    "C_risk": "target vol / VOL_PER_UNIT_GROSS。運用の risk budget はここで決まる",
    "standard_target_vol_scenarios": (0.08, 0.10, 0.12, 0.15),
    "how_to_judge": (
        "**broker ceiling を hurdle にしない。** 「5x を超えるから不可」も"
        "「20x まで可能だから Sharpe 0.107 で十分」も、どちらも誤りである。"
        "正しい問いは: candidate の**実測** net Sharpe と volatility から、"
        "realistic な target risk で年間 return へ変換できるか — である。"
        "**alpha を見る前に固定倍率だけで否定も肯定もしない**"
    ),
    "capacity_reporting": (
        "net-positive candidate について、年 5% / 年 10% net に必要な "
        "target vol・risk leverage・portfolio gross・pair 別 margin 利用率・DD・"
        "gap stress・残 margin buffer を算出する"
    ),
    "never": "net edge <= 0 を leverage で救わない",
}

#: cost 規約。**片方の span でしか測っていない**ことを明示して持ち回る。
COST: Final[dict[str, Any]] = {
    "charged_one_way_bp": "continuous_portfolio.CHARGED_ONE_WAY_BP (= 1.703)",
    "stress_multiples": (1.0, 1.5, 2.0),
    "caveat": "CHARGED_COST_MEASURED_ON_2021_2025_OANDA_NOT_ESTABLISHED_FOR_THE_1999_2016_SPAN",
    "reporting": "2 span の net は分けて報告する。判定も span 別に行い、pooled net は判定に使わない",
}

#: **turnover は band law の値をそのまま信じない。** 直前の T-R2 事前登録が、fast run の
#: 実測 82.4 RT に対し band law が 43.4 を出したこと（倍率 1.90）を記録している。
#: 短い lookback ほど law は turnover を過小評価する。両方を凍結し、実測が補正値を
#: 超えたら `B_cost_or_turnover_failure` と判定する。
TURNOVER_CORRECTION: Final[dict[str, Any]] = {
    "measured_multiple": 1.90,
    "evidence": "scripts/research/market_yields/prereg_r2.py:147（fast run 82.4 vs law 43.4）",
    "rule": "実測 turnover が補正値を超えたら B_cost_or_turnover_failure",
}

#: 全 track 共通の benchmark。「悪い baseline より良い」を edge と呼ばないため。
BENCHMARKS: Final[tuple[str, ...]] = (
    "zero_signal",
    "fx_own_momentum_20d",
    "fx_own_mean_reversion_20d",
)

#: 外部情報 track は、FX 自身の価格情報を超える増分を示すこと。
CONTROL: Final[str] = "incremental_ic_over_fx_own_momentum_20d"

#: T2 は T1 に対する増分も示す。beta vector の相関が +0.856（R2 0.73）で、
#: risk-off 局面では 2 本が 73% 同じ持ち高を取るため、「別物だ」の主張に裏づけが要る。
CROSS_TRACK_CONTROLS: Final[dict[str, str]] = {
    "T2": "incremental_ic_over_T1_signal（beta 相関 +0.856 のため必須）",
}

#: 報告する metric。5 本で同じ表になる。
METRICS: Final[tuple[str, ...]] = (
    "gross_annual_return",
    "net_annual_return",
    "gross_sharpe",
    "net_sharpe",
    "realized_vol",
    "ic",
    "incremental_ic",
    "turnover_round_trips_per_year",
    "annual_cost",
    "signal_persistence",
    "position_persistence",
    "max_drawdown",
    "positive_temporal_blocks",
    "currency_contribution",
    "leave_one_currency_out",
    "top_1_day_contribution",
    "top_5_day_contribution",
    "top_10_day_contribution",
    "downside_tail",
    "temporal_concentration",
    "cost_x1_5",
    "cost_x2",
    #: 層が仮説をどれだけ消したかを毎回測る。共有層を使う以上これが無いのは欠落である。
    "raw_to_neutralised_score_corr",
    "factor_abs_cosine",
    #: 裁定 §27-§28
    "portfolio_gross_leverage",
    "risk_leverage",
    "margin_utilisation",
)

#: Stage 1 は fixed / unfitted rule のみ。
STAGE_1_ONLY: Final[str] = "FIXED_UNFITTED_RULE_NO_FITTING_NO_SEARCH_NO_ML"

#: Stage 2 へ進む条件は **事前に** 決める。
#: 初稿は条件を pooled span で書いていたが、cost 規約が長 span で成立していないので
#: pooled net を判定に使ってはならない。**近 span（cost が実測された側）で判定する。**
STAGE_2_ELIGIBILITY: Final[dict[str, str]] = {
    "judged_on": "recent span のみ（cost 規約が実測された唯一の span）",
    "condition_1": "gross_sharpe > 0",
    "condition_2": "incremental_ic over fx_own_momentum_20d > 0",
    "condition_3": "net_annual_return > 0 at the charged cost convention",
    "model_if_eligible": (
        "forward return を、凍結した signal と control の 2 変数へ回帰する single linear "
        "model のみ。interaction も feature 追加も無い"
    ),
    "if_not_eligible": "STOP。Stage 2 へは進まない",
    "multiplicity_note": (
        "同じ規則でも track ごとに帰無通過確率が違う（cost drag が違うため）。"
        "低 turnover の track はノイズでも通りやすい。**Stage 2 へ自動進行した事実を"
        "報告するときは、その track の帰無通過確率を必ず添える**"
    ),
}

#: 非線形 ML は本 cycle では training しない。
NONLINEAR_ML: Final[str] = "PROPOSAL_ONLY_NO_TRAINING_IN_THIS_CYCLE"

#: 長 span の excess return panel の作り方。**carry leg が無いことを開示する。**
#: T3 は金利の signal を、金利 carry を落とした panel の上で測ることになる。
EXCESS_PANEL: Final[dict[str, str]] = {
    "long": "ECB reference rate から作る currency vs basket の spot return。carry leg は無い",
    "recent": "既存の guarded route が作る currency excess return",
    "disclosure": "CARRY_LEG_ABSENT_ON_THE_LONG_SPAN_OMITTED_VARIABLE_CORRELATES_WITH_T3_SIGNAL",
    "consequence": "T3 と T5 の長 span 結果はこの欠落込みで読む。carry を後から足さない",
}


# ---------------------------------------------------------------------------
# 5 本の track
# ---------------------------------------------------------------------------

TRACKS: Final[dict[str, dict[str, Any]]] = {
    "T1": {
        "candidate": "S05",
        "name": "cross-asset risk repricing -> G10 FX",
        "category": "cross-asset information",
        "mechanism": (
            "株式 volatility の repricing は risk appetite の変化そのものであり、"
            "funding currency（JPY・CHF）と high-beta commodity currency（AUD・NZD・CAD）へ "
            "反対向きに効く。**FX の価格から導けない外部資産の情報**である"
        ),
        "novelty": "H-002 は price-only の session / ATR 条件付けであって cross-asset state ではない",
        "data": "CBOE VIX daily close (cdn.cboe.com VIX_History.csv)",
        "data_evidence": "gated probe 2026-09-20: HTTP 200",
        "data_caveat": (
            "1990-2003 の VIX は 2003 年の新方式による**遡及計算**で、長 span 前半は"
            "実時間に存在しなかった値である"
        ),
        "signal": "z = 5 日 log(VIX) 変化を 252 日で標準化（平均・標準偏差は day t までの行のみ）",
        "direction": {
            "rule": "VIX が上がる（risk off）と safe haven が上がる。mu = z * beta",
            "beta": {
                "JPY": 1.0,
                "CHF": 1.0,
                "USD": 0.5,
                "EUR": 0.0,
                "GBP": 0.0,
                "CAD": -0.5,
                "AUD": -1.0,
                "NZD": -1.0,
            },
            "frozen": "この beta は事前に決めた economic prior であり、当てはめて求めない",
        },
        "horizon": "日次判断。保有は band 層",
        "expected_turnover": {"band_law": 43.4, "corrected_x1_90": 82.5},
        "breadth": 2.0,
        "breadth_source": "candidates.py の S05 記録「実効 2（risk 軸 1 本）」。初稿の 2.5 は根拠なき上方修正だった",
        "known_weakness": (
            "risk 軸 1 本。USD +0.5 は dollar smile が支配的になる 2008 年以降の性質で、"
            "長 span 前半では成立しない。EUR 0 は numeraire 軸かつ regime 依存の正直な棄権であり、"
            "長 span の結果は EUR の regime 変化に対する暗黙の賭けを含む"
        ),
    },
    "T2": {
        "candidate": "S06",
        "name": "commodity terms of trade -> commodity currencies",
        "category": "external macro-financial state (commodity)",
        "mechanism": (
            "原油価格の変化は産出国の実質所得を動かす。T1 の単一 risk 軸とは**別の経済主張**"
            "である — 通貨固有の交易条件であって global risk appetite ではない"
        ),
        "novelty": "C11 は一度も実行されていない",
        "data": "EIA official US crude spot (www.eia.gov RWTCd.xls)",
        "data_evidence": "gated probe 2026-09-20: HTTP 200",
        "data_caveat": (
            "**OLE2 バイナリ .xls である。** CSV 代替を探したが存在せず（`?download=csv` も"
            "同じバイナリ、FRED は timeout）、読むには `xlrd` が要る。"
            "**2026-09-21 裁定 §2 が追加を承認**した（research 用途限定・version 固定・"
            "parsing のみ・埋め込み macro を実行しない・取得 file の hash を記録）"
        ),
        "signal": "z = 5 日 log(WTI) return を 252 日で標準化（T1 と同形）",
        "direction": {
            "rule": "原油高は産出国通貨に有利、輸入国通貨に不利。mu = z * beta",
            "beta": {
                "CAD": 1.0,
                "AUD": 0.5,
                "NZD": -0.5,
                "USD": 0.0,
                "GBP": 0.0,
                "EUR": -0.5,
                "CHF": -0.25,
                "JPY": -1.0,
            },
            "frozen": "経済的 prior。当てはめない",
            "revised_from_first_draft": (
                "初稿は NZD +0.5 だったが、**ニュージーランドは原油の純輸入国**（輸出は"
                "乳製品・食肉・木材）で、原油高は交易条件の**悪化**である。宣言した機構が"
                "自分の beta に破られていた。NZD を -0.5 に、豪州の輸出は鉄鉱石・石炭・LNG で"
                "原油ではないので AUD を +1.0 から +0.5 に、石油輸入強度に照らして "
                "CHF を -0.5 から -0.25 に直した"
            ),
        },
        "horizon": "T1 と同じ",
        "expected_turnover": {"band_law": 43.4, "corrected_x1_90": 82.5},
        "breadth": 1.5,
        "cross_track_control": "T1 の signal に対する incremental IC も報告する",
        "known_weakness": (
            "実効 breadth が最も狭い。また USD 0 は近 span では誤り（2021-2025 の米国は"
            "石油の純輸出国）だが、長 span では正しい。span 別報告でそこを読む"
        ),
    },
    "T3": {
        "candidate": "S02",
        "name": "sovereign curve shape -> G10 FX",
        "category": "rates information the closure does not reach",
        "mechanism": (
            "**curve の形状**（10y-2y）は level とは別の量である。level は期待政策金利に、"
            "slope は成長期待と term premium に支配される。closure は curve shape を"
            "『届かない情報集合』として明示的に列挙している"
        ),
        "novelty": "closed family が使ったのは実現 2 年利回りの level の変化である",
        "data": (
            "10y: US Treasury daily curve / Bundesbank Zinsstruktur 10 年 "
            "(D.I.ZST.ZI.EUR.S1311.B.A604.R10XX...) / Bank of Canada Valet / SNB rendoblid / "
            "BoE (IUDMNZC)。2y は market_yields/sources.py で取得済み"
        ),
        "data_evidence": (
            "gated probe 2026-09-20: US Treasury 200・Bundesbank ZST 200 (230,846 bytes)・"
            "BoC 200・SNB 200・BoE 200 (87,507 bytes)。"
            "**初稿は Umlaufsrendite (ZAR) と書いていたが、その系列は 404 だった** — "
            "200 を返したのは Zinsstruktur (ZST) の方である"
        ),
        "universe": {
            "included": ("USD", "EUR", "CAD", "CHF", "GBP"),
            "excluded": ("JPY", "AUD", "NZD"),
            "why": (
                "10y が probe で取れたのは 5 通貨。JGB は 404、RBA と RBNZ は 403 だった。"
                "**除外リストは今ここで固定する** — Stage 0 で追加で取れたとしても加えない。"
                "凍結後に cross-section の構成を変えるのは設計変更である"
            ),
        },
        "signal": "各通貨の slope = 10y - 2y。その 20 日変化を 5 通貨 cross-section で rank し中心化",
        "direction": {
            "rule": "**符号は 1 つに決めない。両方を事前登録した sub-hypothesis とする**",
            "frozen": (
                "2026-09-21 裁定 §3。実行前レビューで economic sign が理論的に曖昧と判明したため、"
                "旧 freeze の「steepening -> 通貨高」を primary として実行しない"
            ),
            "sub_hypotheses": {
                "T3-H1": "steepening -> subsequent currency appreciation",
                "T3-H2": "steepening -> subsequent currency depreciation",
            },
            "reporting_rule": (
                "**H1 と H2 を両方報告する。** 結果を見て良かった符号だけを primary 扱いしない。"
                "「どちらかが positive だったから curve theory が支持された」という主張は禁止。"
                "**sign multiplicity を明示する** — T3 は 2 通りの探索である"
            ),
            "why_ambiguous": (
                "curve steepening は単一 mechanism ではない: bull steepening / bear steepening / "
                "policy easing expectations / inflation-growth repricing / term-premium change / "
                "fiscal-risk premium で符号が異なりうる。"
                "**今回これらを結果後に分類して最適化しない**（裁定 §4）。"
                "まず凍結済みの simple curve-shape hypothesis を評価する"
            ),
        },
        "rename_gate": (
            "閉じた T-R2 は 20 日の Δ2y を cross-section z 化し符号 +1 で走った。T3 は 2y leg を "
            "-1 で入れるので、**反転した T-R2 になりうる**。Δ10y-only book と (-Δ2y)-only book を"
            "併走させ、T3 の日次 P&L が後者と |corr| > 0.8 なら「閉じた規則の反転」と判定して"
            "結果を採らない"
        ),
        "horizon": "日次判断、20 日 state",
        "expected_turnover": {"band_law": 18.3, "corrected_x1_90": 34.8},
        "breadth": 1.5,
        "breadth_source": "5 通貨 sum-zero cross-section の自由度は 4、dollar factor 除去後の実効は 1.5-2",
        "known_weakness": "同じ情報源の level が 2 回失敗した直後の第 2 仮説。prior は低い",
    },
    "T4": {
        "candidate": "S10",
        "name": "currency-network propagation -> G10 FX",
        "category": "currency-network propagation",
        "mechanism": (
            "ある通貨の固有の動きは、相関構造で結ばれた相手通貨へ 1 日遅れて伝播する。"
            "**自分の過去リターンではなく、相手の残差**を見るところが要点である"
        ),
        "novelty_gate": {
            "why_it_could_be_a_rename": (
                "H-003 は relative strength、Track 1 は 5/20/60 日の線形結合で、どちらも"
                "『自分の過去リターン』から作る。H-024 は 5/20/60 の reversal benchmark の"
                "復活を禁じている"
            ),
            "PRE_REGISTERED_AUDIT": (
                "**初稿の gate は発火しえなかった。** 1 日量と h 日 momentum の相関上限は "
                "rho/sqrt(h) なので、5 日で 0.36・20 日で 0.18・60 日で 0.10 にしかならず、"
                "閾値 0.8 には構造的に届かない。比較対象を差し替える: "
                "**(i) 自通貨の lag-1 残差 res_i(t) と mu_i(t) の相関、"
                "(ii) 1 日 own-return book と T4 の日次 P&L の相関**。"
                "**(i) が |corr| > 0.8、または (ii) が |corr| > 0.8 なら RENAME と判定して"
                "結果を採らない。** 閾値は結果を見る前に決めてある"
            ),
            "why_the_new_comparator_is_the_right_one": (
                "相手 j は残差相関が最大の通貨として選ばれるので、corr(mu_i, res_i) は"
                "定義上その最大相関 rho_ij に等しい。G10 の 1 factor 除去後で EUR/CHF や "
                "AUD/NZD の残差相関は 0.6-0.8 に達するから、**mu_i は実質「自分の 1 日残差 × rho」**"
                "になりうる。そこを測るのが正しい gate である"
            ),
            "conflict_with_h010": (
                "H-010 は残差の 1 日構造について **VR < 1（平均回帰）を全 horizon・全 panel で"
                "測り、CLOSED - real but unharvestable microstructure** と記録している。"
                "T4 は momentum 符号を凍結しているので、**H-010 と符号が逆**である。"
                "それでも正の伝播を選ぶ理由は、H-010 が測ったのは *自分自身* の系列相関であり、"
                "T4 が賭けるのは *他通貨への* 伝播だからである。両者は別の量だが、"
                "**この区別が薄ければ T4 は H-010 の裏返しになる** — gate (i) がそこを捕まえる"
            ),
        },
        "data": "既 seen の FX 日次 excess return panel のみ（外部取得ゼロ）",
        "data_evidence": "既取得。新規取得なし",
        "signal": (
            "(1) 日次 currency excess return から **trailing 120 日窓**の leading factor を"
            "除いて残差を得る（centered 窓は使わない）。"
            "(2) 通貨 i について、t-1 までの trailing 252 日窓で残差相関が最大の相手 j を選ぶ。"
            "(3) mu_i(t) = 残差_j(t)。**相手の**昨日の固有変動が今日の期待に入る"
        ),
        "direction": {
            "rule": "正の伝播。相手が固有に上がった通貨は、翌日上がる",
            "frozen": "反転版は事後に試さない",
        },
        "horizon": "日次。intraday 版は使わない（turnover 100 超で cost が致命的と実測済み）",
        "expected_turnover": {"band_law": 100.8, "corrected_x1_90": 191.5},
        "breadth": 2.5,
        "known_weakness": (
            "price-only であり、閉じた family に最も近い。turnover が 5 本で圧倒的に高く、"
            "補正後 191 RT/年では cost drag が 2.8 を超える。**gate を通っても cost で落ちる"
            "公算が高い**ことは実行前に分かっている"
        ),
    },
    "T5": {
        "candidate": "S26",
        "name": "international capital flow (TIC) -> USD",
        "category": "flow / positioning proxy",
        "mechanism": (
            "米国長期証券への越境ネット買いは、実需のドル需要そのものである。"
            "H-021 が閉じた COT は先物投機であって、現物 flow とは別物である"
        ),
        "novelty": "H-021（先物投機ポジション）とは data も主体も異なる。未検定",
        "data": "US Treasury TIC S-1 (ticdata.treasury.gov/Publish/s1_globl.csv, monthly)",
        "data_evidence": "gated probe 2026-09-20: HTTP 200, 400,000 bytes（先頭切り詰め読み）",
        "signal": (
            "S-1 の **全世界計・長期証券の net foreign purchases of US securities** 行を取り、"
            "その月次系列の 12 か月 z-score を mu の大きさとする。"
            "**行と集計は今ここで固定する** — gross でも domestic/foreign 別でも国別でもない"
        ),
        "vintage": (
            "第 m 月の値は m+2 月末以降にしか使わない（公表は m+2 月中旬なので保守側）。"
            "ただし配信ファイルは改訂後の値なので、REVISION_CAVEAT が残る"
        ),
        "direction": {
            "rule": "流入超は USD 高。mu_USD = +z、他 7 通貨は -z/7（ゼロサム）",
            "frozen": "反転版は事後に試さない",
        },
        "rename_gate": (
            "使用可能になる時点で 2-3 か月前の flow なので、**「2 か月ラグの USD momentum」と"
            "ほぼ同じになりうる**。外国人が米債を買い越した月は、ドルと米債が上がった月である。"
            "TIC z と 1/2/3 か月ラグの USD basket return の相関を必ず報告し、"
            "**いずれかで |corr| > 0.8 なら RENAME と判定して結果を採らない**"
        ),
        "denomination_caveat": (
            "TIC の net purchase は USD 建てなので、z-score は買われた資産の USD 価格水準の "
            "z-score を部分的に含む（機械的汚染）"
        ),
        "horizon": "月次判断を日次に持ち越す",
        "expected_turnover": {"band_law": 5.1, "corrected_x1_90": 9.7},
        "breadth": 1.0,
        "known_weakness": (
            "**本質的に USD 1 軸**。月次なので長 span で約 209 観測、近 span だけなら 56 で"
            "negative を閉じられない。米国の経常赤字はファイナンスされねばならないので"
            "net 長期流入は会計的にほぼ定常であり、変動は主体構成と評価変動にある"
        ),
    },
}

#: 実行順。**前の track の結果を後の track の設計に反映しない。**
EXECUTION_ORDER: Final[tuple[str, ...]] = ("T1", "T2", "T3", "T4", "T5")

#: 順位は保持したまま実行しない候補。
NOT_EXECUTED: Final[dict[str, dict[str, str]]] = {
    "S07": {
        "rank": "3",
        "status": "DESIGN_ONLY_NOT_EXECUTED",
        "why": (
            "ICE BofA high-yield OAS は FRED 経由しか無料 route が無く、承認済み probe は "
            "series page と root の両方で TIMEOUT。**仮説は何も検定されていない**。"
            "2026-09-14 の記録は当該 series が 200 で配信されていることを示しており、"
            "**閉じたのではなく、この環境から届かないだけ**である"
        ),
    },
    "S25": {
        "rank": "5",
        "status": "DESIGN_ONLY_NOT_EXECUTED",
        "why": (
            "ECB 200 / SNB 200 だが **Fed H.4.1 に clean な無料 CSV endpoint が無い**"
            "（DDP は 400、HTML のみ 200）。**Fed 抜きの G10 中銀 balance sheet panel は"
            "仮説として成立しない**。S07 と同じく、閉じたのではない"
        ),
    },
    "S20_and_paid": {
        "rank": "-",
        "status": "PAID_DATA_DESIGN_ONLY_NOTHING_PURCHASED",
        "why": "risk reversal / OIS / intraday futures。購入しない。設計は #489 §7 に記録済み",
    },
}

#: なぜ S14 / S15 / S12 を繰り上げなかったか。
PROMOTION_REASONING: Final[str] = (
    "順位だけなら S07 と S25 の次は S14(7) / S15(8) / S12(9) だが、3 つとも price-only "
    "または conditioning であり、H-023 / H-024 / H-003 という **閉じた family に隣接**する。"
    "凍結枠をそこに使うと rename を生む危険があり、それは禁じられている。"
    "また 5 本すべてが price momentum の変形にならないようにせよという要求にも反する。"
    "S26(10) は非価格の別情報集合で、data も probe 済みなので、これを繰り上げた。"
    "**この判断は alpha を 1 つも見る前に行っている。**"
)

#: 判定の目安。統計的有意性の規則ではなく economic な解釈である。
#: 既存の `edge_sources.ECONOMIC_BANDS` とは 0.2-0.3 の扱いが違う。本 cycle は
#: development screening なので、**こちらを使い、差があることを記録する**。
INTERPRETATION: Final[dict[str, str]] = {
    "net_sharpe_le_0": "negative",
    "net_sharpe_0_to_0_2": "weak",
    "net_sharpe_0_2_to_0_5": "marginal / potentially useful depending on stability and cost",
    "net_sharpe_0_5_to_0_8": "meaningful development candidate",
    "net_sharpe_gt_0_8": "strong development candidate",
    "not_a_significance_rule": (
        "5 本の中で最大だった / p < 0.05 だった / Sharpe が一番高かった、だけでは昇格しない"
    ),
    "differs_from_committed_bands": (
        "edge_sources.ECONOMIC_BANDS は 0.30 を low_value の上端に置く。本 cycle は "
        "0.2-0.5 を marginal とする。**両方 committed なので、報告では本 cycle の帯と "
        "既存帯の双方を示す**"
    ),
}

#: 失敗の分け方（2026-09-21 裁定 §32）。「failed」で一括りにしない。
NEGATIVE_CLASSES: Final[dict[str, str]] = {
    "SIGNAL_FAILURE": "gross から弱い / negative",
    "COST_FAILURE": "gross はあるが net で消える",
    "DATA_FAILURE": "coverage / timing / sample 不足",
    "CONCENTRATION_FAILURE": "one currency / one episode 依存",
    "IMPLEMENTATION_FAILURE": "research design を正しく評価できていない",
}

#: 各 track が取りうる最終 status（裁定 §52）。**track 接頭辞を付ける** —
#: 接頭辞が無いと、記録された verdict がどの track のものか token から読めない。
TRACK_STATUS_SUFFIXES: Final[tuple[str, ...]] = (
    "STRONG_DEVELOPMENT_CANDIDATE",
    "MARGINAL_DEVELOPMENT_CANDIDATE",
    "NOT_SUPPORTED_IN_SEEN_DEVELOPMENT",
    "DATA_NOT_DECISION_GRADE",
    "DATA_UNAVAILABLE_WITH_CURRENT_FREE_SOURCES",
)


def track_status(track: str, suffix: str) -> str:
    """`T1_S05_STRONG_DEVELOPMENT_CANDIDATE` のような形にする。"""
    if suffix not in TRACK_STATUS_SUFFIXES:
        raise ValueError(f"未登録の status: {suffix}")
    return f"{track}_{TRACKS[track]['candidate']}_{suffix}"


#: 結果を見た後の救済は禁止。
FORBIDDEN_RESCUES: Final[tuple[str, ...]] = (
    "sign flip after result",
    "horizon optimization",
    "lag optimization",
    "threshold tuning",
    "currency removal",
    "feature addition",
    "cost-specific smoothing",
    "band optimization",
    "leverage optimization",
    "model complexity addition",
)

#: **本取得は 2026-09-21 裁定 §5 で承認された。** metadata probe だけでなく、
#: VIX / WTI / sovereign curve / TIC と、その他 prereg が固定した public/free input を
#: 取得し、既に許可された seen-development FX panel と結合してよい。
ACQUISITION: Final[dict[str, Any]] = {
    "authorized": "2026-09-21 Human + ChatGPT 裁定 §5",
    "scope": "public / free source のみ",
    "forbidden": (
        "protected fresh span / historical OOS / dead window / forward epoch / "
        "authenticated OANDA / paid API"
    ),
    "must_record": (
        "provider",
        "url",
        "request_parameters",
        "retrieval_timestamp",
        "http_status",
        "content_hash",
        "coverage",
        "frequency",
        "publication_timing",
    ),
    "request_level_exclusion": (
        "protected span は **request 自体から除外**する。download-then-filter は禁止。"
        "期間パラメータを取らない全量配信 endpoint の場合は、**parsed date で切り落とす前の "
        "frame を signal に一切触れさせない**ことを実装で保証する"
    ),
}


#: 複数 candidate が positive でも、本 cycle では合成しない（裁定 §39）。
MULTI_SOURCE_PORTFOLIO: Final[str] = (
    "NO_WEIGHTS_OPTIMIZATION_NO_BLENDING_NO_SOURCE_SELECTION_THIS_CYCLE_PROPOSAL_ONLY"
)

#: cross-track の相関診断は exploratory に行うが、そこから portfolio を組まない（§36）。
CROSS_TRACK_DIAGNOSTIC: Final[tuple[str, ...]] = (
    "pairwise_pnl_correlation",
    "currency_exposure_similarity",
    "event_dependence",
    "common_risk_factor",
)

#: 本 cycle は 5 通りの探索である。p 値を formal proof として扱わない（§38）。
EXPLORATION_DISCLOSURE: Final[str] = (
    "FIVE_WAY_EXPLORATORY_DEVELOPMENT_SEARCH_PLUS_A_TWO_SIGN_SUB_SEARCH_WITHIN_T3"
)


def _payload() -> dict[str, Any]:
    """digest が覆う対象。**公開定数を 1 つ残らず入れる。**

    初稿は `FORBIDDEN_RESCUES` / `NEGATIVE_CLASSES` / `NONLINEAR_ML` /
    `PROMOTION_REASONING` を覆っておらず、**事後に最も緩めたくなるリストが digest の外**に
    あった。mutation でそれが実証されたので、ここは集合等価を test で固定する。
    """
    return {
        "cycle": CYCLE,
        "workflow_status": WORKFLOW_STATUS,
        "signal_constants": SIGNAL_CONSTANTS,
        "digest_as_executed": DIGEST_AS_EXECUTED,
        "outcomes": list(OUTCOMES),
        "forbidden_next_steps": list(FORBIDDEN_NEXT_STEPS),
        "universe": list(UNIVERSE),
        "authority": AUTHORITY,
        "spans": SPANS,
        "protected_bounds": PROTECTED_BOUNDS,
        "timestamp_rule": TIMESTAMP_RULE,
        "publication_times": PUBLICATION_TIMES,
        "revision_caveat": REVISION_CAVEAT,
        "execution_layer": EXECUTION_LAYER,
        "book_config": BOOK_CONFIG,
        "book_config_deviations": BOOK_CONFIG_DEVIATIONS,
        "leverage_framework": LEVERAGE_FRAMEWORK,
        "cost": COST,
        "turnover_correction": TURNOVER_CORRECTION,
        "benchmarks": list(BENCHMARKS),
        "control": CONTROL,
        "cross_track_controls": CROSS_TRACK_CONTROLS,
        "metrics": list(METRICS),
        "stage_1_only": STAGE_1_ONLY,
        "stage_2_eligibility": STAGE_2_ELIGIBILITY,
        "nonlinear_ml": NONLINEAR_ML,
        "excess_panel": EXCESS_PANEL,
        "tracks": TRACKS,
        "execution_order": list(EXECUTION_ORDER),
        "not_executed": NOT_EXECUTED,
        "promotion_reasoning": PROMOTION_REASONING,
        "interpretation": INTERPRETATION,
        "negative_classes": NEGATIVE_CLASSES,
        "forbidden_rescues": list(FORBIDDEN_RESCUES),
        "acquisition": ACQUISITION,
        "superseded_freeze": SUPERSEDED_FREEZE,
        "post_execution_corrections": POST_EXECUTION_CORRECTIONS,
        "track_status_suffixes": list(TRACK_STATUS_SUFFIXES),
        "multi_source_portfolio": MULTI_SOURCE_PORTFOLIO,
        "cross_track_diagnostic": list(CROSS_TRACK_DIAGNOSTIC),
        "exploration_disclosure": EXPLORATION_DISCLOSURE,
    }


def freeze_digest() -> str:
    """凍結内容の sha256。**これが変わったら、それは別の事前登録である。**

    `default` を渡さない: JSON 化できない値が入ったら黙って `str()` にせず落ちる。
    初稿は `default=str` を渡しており、tuple→list のような型変更に盲目だった。
    """
    return hashlib.sha256(
        json.dumps(_payload(), sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()


__all__ = [
    "ACQUISITION",
    "DIGEST_AS_EXECUTED",
    "AUTHORITY",
    "BENCHMARKS",
    "BOOK_CONFIG",
    "BOOK_CONFIG_DEVIATIONS",
    "CONTROL",
    "COST",
    "CROSS_TRACK_CONTROLS",
    "EXCESS_PANEL",
    "CROSS_TRACK_DIAGNOSTIC",
    "EXECUTION_LAYER",
    "EXECUTION_ORDER",
    "EXPLORATION_DISCLOSURE",
    "FORBIDDEN_RESCUES",
    "INTERPRETATION",
    "LEVERAGE_FRAMEWORK",
    "METRICS",
    "MULTI_SOURCE_PORTFOLIO",
    "NEGATIVE_CLASSES",
    "NONLINEAR_ML",
    "NOT_EXECUTED",
    "PROMOTION_REASONING",
    "PROTECTED_BOUNDS",
    "PUBLICATION_TIMES",
    "REVISION_CAVEAT",
    "SIGNAL_CONSTANTS",
    "SPANS",
    "STAGE_1_ONLY",
    "STAGE_2_ELIGIBILITY",
    "POST_EXECUTION_CORRECTIONS",
    "SUPERSEDED_FREEZE",
    "TIMESTAMP_RULE",
    "TRACKS",
    "TRACK_STATUS_SUFFIXES",
    "TURNOVER_CORRECTION",
    "freeze_digest",
    "track_status",
]
