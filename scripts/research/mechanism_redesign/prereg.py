# ruff: noqa: E501 -- pre-registration prose
"""**mechanism redesign cycle の事前登録**（2026-09-24 裁定 §21–§31）。alpha を見る前に凍結する。

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE` ·
`PRODUCTION_READINESS_NOT_CLAIMED`.

凍結の中身は `_payload()` にあるものだけで、`freeze_digest()` がその sha256 を返す。
signal の式は `signals.py`、book の設定・判定規則・指標はここにある。**`signals.py` の
source の sha256 も payload に入れる**（next-five の R-4: digest がコードを含まなかった）。

判定の骨格（null 診断・development economics・Stage 2 適格・verdict）は next-five と同一にする。
2 つの cycle の結果を同じ表に並べるためで、**結果を見て変えたものではない**（next-five の値を import し、
その中身を payload に書き込む。next-five 側が変われば digest が変わる）。
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Final

from scripts.research.next_five import prereg as _nf

CYCLE: Final[str] = "MECHANISM_REDESIGN_2026_09"
AUTHORITY: Final[dict[str, str]] = {
    "ruling": "2026-09-24 Human + ChatGPT 裁定（U1..U5 最終統合報告のレビュー後）",
    "scope": "mechanism 再設計 → signal-blind ranking → 最大 5 本の凍結 → minimal development",
}
WORKFLOW_STATUS: Final[str] = "FIVE_TRACKS_FROZEN_AWAITING_ALPHA_EXECUTION"

#: **pre-alpha amendment**（独立 review 2 役: Role 1 経済 BLOCKER 1 / REQUIRED 8、Role 2 timing REQUIRED 8）。
#: 最初の凍結 digest から変えたのは下の項目で、どれも alpha を 1 本も見る前である。
FREEZE_AMENDMENT_PRE_ALPHA: Final[dict[str, Any]] = {
    "digest_before": "2815e1ddf76a189145e52d7cf5251500351f7a359cbe6aa16bd27c27c177263c",
    "status": "AMENDED_PRE_ALPHA_NO_RETURN_HAD_BEEN_MEASURED",
    "changes": (
        "判定 P&L に carry accrual と仮定 financing markup を入れた（B-1）",
        "digest に依存コードの source と入力 data の hash を入れた（R-1 / RF-5）",
        "rename gate が評価できない場合を NOT_EVALUABLE として凍結した（R-2）",
        "permutation の draw 数を実行時に変えられなくした、記録があれば走らない、dirty tree で走らない（R-3 / RF-6）",
        "有効標本数 10 未満の track に検出力の上限と非 closure 規則を置いた（R-4）",
        "M10 の最近接 family に vol 状態・reversal を書き、vol ratio との rename gate を置いた（R-5）",
        "M01 を BIS の date-bounded SDMX で取得でき、5 本目として加えた（R-6）",
        "M14 の除外理由を直した（R-7）、M15 と #471 pair-level carry の区別を書いた（R-8）",
        "CPI 前年比の分母の月が保護暦日に掛かる stamp を読まない（RF-3）",
        "GBP 失業率の公表 lag を m+3 にした（RF-4）",
        "M15 の改訂留保を CURRENT_VINTAGE_ONLY に直した（RF-7）",
        "取得の事故と露出を acquisition_amendment.json に記録した（RF-1 / RF-2 / RF-8、D-M3）",
    ),
}

FORBIDDEN: Final[tuple[str, ...]] = (
    "fresh pool / historical OOS / dead window / forward epoch の読み取り",
    "有料データの購入",
    "認証付き broker API",
    "demo / paper / live",
    "unrestricted nonlinear ML",
    "post-hoc multi-source optimization",
    "U1..U5 の horizon / sign / subset rescue",
    "6 本目以降の alpha 実行（今回は 5 本）",
    "結果を見た後の horizon / sign / universe / benchmark / feature / threshold の変更（track 間も含む）",
)

UNIVERSE: Final[tuple[str, ...]] = _nf.UNIVERSE
SPANS: Final[dict[str, Any]] = _nf.SPANS
PROTECTED_BOUNDS: Final[dict[str, Any]] = _nf.PROTECTED_BOUNDS
PRIMARY_SPAN_RULE: Final[dict[str, str]] = _nf.PRIMARY_SPAN_RULE
EXECUTION_LAYER: Final[str] = _nf.EXECUTION_LAYER
BOOK_CONFIG: Final[dict[str, Any]] = _nf.BOOK_CONFIG

#: ドル factor の 2 本だけ、book の 3 つの設定を変える。**結果の前に決めてある。**
BOOK_CONFIG_DEVIATIONS: Final[dict[str, dict[str, Any]]] = {
    track: {"neutralize_leading_factor": False, "mapping": "linear", "weight_cap": 0.5}
    for track in ("M15", "M16")
}
BOOK_CONFIG_DEVIATION_WHY: Final[str] = (
    "第 1 主成分（通常はドル方向）を中立化すると、ドル factor の signal は消える。"
    "linear mapping は USD と等ウェイト 7 通貨 basket の対にするため（vol で basket の重みを歪めない）。"
    "weight_cap 0.5 は USD 側の脚が 0.5 に届くようにするため（0.25 のままだと gross が半分になる）"
)

COST: Final[dict[str, Any]] = _nf.COST
BENCHMARKS: Final[tuple[str, ...]] = _nf.BENCHMARKS
CONTROL: Final[str] = _nf.CONTROL
DEVELOPMENT_ECONOMICS: Final[dict[str, Any]] = _nf.DEVELOPMENT_ECONOMICS
STAGE_2_ELIGIBILITY: Final[dict[str, Any]] = _nf.STAGE_2_ELIGIBILITY
VERDICT_LOGIC: Final[tuple[dict[str, str], ...]] = _nf.VERDICT_LOGIC
FAILURE_CLASS_RULE: Final[dict[str, str]] = _nf.FAILURE_CLASS_RULE
DEMOTED_GATE: Final[dict[str, Any]] = _nf.DEMOTED_GATE
CAPACITY_REPORTING: Final[dict[str, Any]] = _nf.CAPACITY_REPORTING
TRACK_STATUS_SUFFIXES: Final[tuple[str, ...]] = _nf.TRACK_STATUS_SUFFIXES

NULL_DIAGNOSTIC: Final[dict[str, Any]] = {
    **_nf.NULL_DIAGNOSTIC,
    "permutation": {**_nf.NULL_DIAGNOSTIC["permutation"], "seed": 20260924},
    "multiplicity": (
        "5 本を同じ null に当てるので、**いずれか 1 本が 5% を切る確率は帰無でも約 23%**（1 − 0.95⁵）。"
        "**1 本通ったことを『edge が見つかった』とは書かない**"
    ),
    "null_pass_probability_by_construction": 0.05,
    "observed_statistic_interpretation": (
        "percentile は『同じ持続性と同じ cost を持つ零情報 signal の中で、観測がどこにいるか』。"
        "**ドル track は符号の regime が少ない**（M15 は long で 6 個）ので、circular shift の帰無も少数の regime の"
        "組み合わせになり、分布は粗い。percentile の細かい差には意味が無い"
    ),
}

#: ドル track の breadth（E5）は **USD を除く 7 通貨の leave-one-out** で測る。
#: USD を抜くとドル factor の book そのものが消え、E5 が構造的に偽になるため。
DOLLAR_TRACK_BREADTH_RULE: Final[str] = (
    "E5 は USD 以外の 7 通貨の leave-one-currency-out の最悪値 > 0"
)

#: **2 回目の pre-alpha amendment**（fresh context の re-audit: BLOCKER 2、REQUIRED 2）。alpha はまだ見ていない。
FREEZE_AMENDMENT_PRE_ALPHA_2: Final[dict[str, Any]] = {
    "digest_before": "e13998514cbf2c49189ac15d4d7397bb6288c90b22c750e5610e84e9fc029132",
    "status": "AMENDED_PRE_ALPHA_NO_RETURN_HAD_BEEN_MEASURED",
    "changes": (
        "carry を spot と同じ pair book 演算子で作る（B-1: x·r は long で carry を 12.5% 過小、recent では通貨ごとに歪んでいた）",
        "GBP 失業率（3 か月平均）の参照期間を stamp の前 2・後 1 か月とし、保護暦日に掛かる stamp を読まない（B-2）",
        "driver は計算の前に development_started.json を書き、それがあれば再実行しない（RF-A）",
        "コードの閉包を driver.py からの静的 import 走査で数える。入力 manifest を v2 にし、rename の比較対象の入力を含める（RF-B）",
        "有効標本数が測れない（NaN）ときも検出力の上限を掛ける",
        "carry の金利は 3 か月銀行間金利が無い日を同じ通貨の BIS 政策金利で埋める（2 回目の re-audit BL-1: "
        "long の JPY 871 日・CHF 170 日で carry が pair book から外れていた）",
        "GBP 失業率の窓を前 2・後 2 か月にした（stamp 慣行に依存しない）",
        "**判断**: BoJ のゼロ金利・量的緩和期間で 3 か月金利も政策金利も無い日は JPY の carry 金利を 0% と置く"
        "（signals.ZERO_RATE_PERIODS）。第 1 期間は m+1 lag に合わせて 2000-09-29 まで（9 月の日に使うのは 7 月の値）",
        "M01 の rename gate CARRY_LEVEL_XS の比較対象は凍結どおり 3 か月銀行間金利だけ（carry 用の埋めを入れない。3 回目の re-audit RF-1）",
        "recent span の 2021-04-27 … 06-29（46 日）は m+1 lag のため全通貨の金利が無く、carry は 0。"
        "score のある track はこの期間に掛からないが、recent の benchmark は掛かりうる",
    ),
    "disclosure_gbp": (
        "GBP 失業率の stamp 2016-04・2016-05（開始月・中心月の慣行なら 2016 年 6 月を含む）、2021-05・2021-06"
        "（2021 年 4 月を含む）、2025-10・2025-11（2025-12-27 以降を含む）は acquisition.json の parquet に保存されている。"
        "月次 1 か月の判定では通っていた。読む側で落とす（窓は前 2・後 2 か月で、stamp 慣行に依存しない）。"
        "取得の request は月次の窓で行っており、3 か月平均の参照期間を request で外すことはできていなかった"
    ),
}

#: **判定する P&L**（B-1）。spot だけでは dollar carry が名乗る premium を測らない。
FINANCING: Final[dict[str, Any]] = {
    "judged_pnl": "spot + carry accrual − spread cost − 仮定 financing markup",
    "carry_accrual": (
        "決定日の exposure × （pair ごとの短期金利の差 base − quote に、spot の currency excess return と"
        "同じ pair book 演算子を掛けた値）× 暦日 / 365。金利は 3 か月銀行間金利、それが無い日は同じ通貨の BIS 政策金利"
        "（signal と同じ lag・staleness）、BoJ のゼロ金利・量的緩和期間で両方無い日は JPY を 0%（判断）。それでも片方の金利が無い pair はその日の平均から外れ、全 pair が無い通貨は 0"
    ),
    "markup_annual_per_unit_currency_gross": 0.0025,
    "markup_is_assumed_not_measured": (
        "retail の swap に含まれる markup の公開記録は無い（economic_edge/carry.py）。"
        "年 0.25%（通貨 gross 1 単位あたり。long の dollar book の pair notional で見ると約 0.44%）を仮定し、"
        "cost stress の倍率を spread cost と同じく掛ける"
    ),
    "spot_only_is_reported": "前 cycle との比較のため、spot だけの gross / net Sharpe を pnl_decomposition に並べる（判定には使わない）",
    "applies_to": (
        "全 5 track の book の P&L（observed・null draw・cost stress・nuisance・benchmark・LOO・capacity）。"
        "M15 だけに入れると track 間で P&L の定義が変わるため。**IC・incremental IC（E3）・Stage 2 回帰は"
        "signal の情報量を測る量なので spot return のまま**"
    ),
}

#: **検出力の上限と、負の結果の範囲**（R-4）。
POWER_RULE: Final[dict[str, Any]] = {
    "min_effective_observations": 10,
    "effective_observations": "primary span の score の AR(1) 近似 N·(1−ρ)/(1+ρ)（return を使わない量）",
    "cap": "有効標本数が 10 未満なら、STRONG / MARGINAL は POSITIVE_EXPLORATORY_SIGNAL_NOT_DECISION_GRADE に下げる",
    "closure_scope": (
        "NOT_SUPPORTED は凍結した formulation と span についての記録であり、mechanism family を閉じない。"
        "有効標本数 10 未満の負の結果は検出力の無い null であって refutation ではない"
    ),
}

#: rename gate が評価できないとき（比較対象が定数・短すぎる・取れない）の扱い（R-2）。
RENAME_NOT_EVALUABLE_RULE: Final[str] = (
    "NOT_EVALUABLE として記録し、verdict は変えない（RENAME にも DISTINCT にも数えない）。"
    "verdict に rename_gates_not_evaluable として並べる"
)

NUISANCE_APPLIES: Final[dict[str, tuple[str, ...]]] = {
    "M15": ("max_staleness_days_monthly", "implementation_tolerance_band"),
    "M11": ("max_staleness_days_monthly", "change_window_months", "implementation_tolerance_band"),
    "M16": ("max_staleness_days_monthly", "change_window_months", "implementation_tolerance_band"),
    "M01": ("max_staleness_days_monthly", "implementation_tolerance_band"),
    "M10": ("liquidity_short_window", "liquidity_long_window", "implementation_tolerance_band"),
}
NUISANCE_RULE: Final[str] = (
    "primary で判定し、事前登録した感度集合の**全点**を報告する。結果の後に best point を選ばない。"
    "`implementation_tolerance_band` は book の band を動かす（signal は動かさない）"
)

TRACKS: Final[dict[str, dict[str, Any]]] = {
    "M15": {
        "candidate": "M15",
        "name": "dollar carry",
        "mechanism": "外国の平均短期金利が米金利を上回る間、ドル factor は carry premium を払う（Lustig–Roussanov–Verdelhan 2014）",
        "why_fx_should_lag": "遅れではなく risk premium。ドル factor は世界景気のリスクを負い、金利差が開いている間その補償が続く",
        "data": "OECD MEI 3 か月銀行間金利 8 通貨（ALFRED、request-level exclusion）",
        "exact_series": "IR3TIB01{US,JP,GB,CA,AU,NZ,CH,EZ}M156N",
        "availability_lag": "第 m 月（月平均）は m+1 月末以降",
        "signal": "d = 外国 7 通貨の 3 か月金利の単純平均（4 通貨以上ある日）− 米 3 か月金利",
        "sign": "d > 0 → ドル売り / 7 通貨 basket 買い。d < 0 → ドル買い",
        "horizon": "月次で更新、保有は符号が変わるまで（1〜数年）",
        "universe": "USD 対 7 通貨の等ウェイト basket",
        "portfolio_mapping": "DOLLAR（BOOK_CONFIG_DEVIATIONS）。**効くのは d の符号だけ**",
        "primary_span": "long",
        "revision": "CURRENT_VINTAGE_ONLY_REVISION_CAVEAT（OECD MEI の現行 vintage。LIBOR 廃止後の USD / GBP は同じ series の中で定義が変わっている可能性がある）",
        "declared_weakness_before_alpha": (
            "**long span で符号の regime が 6 個しかない**（反転 5 回 / 17.7 年）。結果は少数の regime の当たり外れで"
            "決まり、E6（集中）が偽になりやすい。**recent span は全期間ドル買い**（米金利が常に高い）ので、"
            "recent の M15 は benchmark の constant_long_usd と同じ book になり、情報を持たない。"
            "**有効標本数は long 5.0 / recent 1.0**（POWER_RULE の上限に掛かる）。"
            "符号の regime は公知のドル循環（2002–04 のドル安、2008 年後半、2014–15 のドル高）と重なるので、"
            "signal-blind は形式上にとどまる — 結果はある程度事前に推測できる。"
            "1999–2002 は JPY / CHF の金利が欠け 5〜6 通貨の平均、2008-12 の 1 か月の反転は US 3 か月銀行間金利の"
            "funding stress から来ている"
        ),
        "distinct_from_471": "#471 の pair-level carry（C-A）は USD pair で全差が同符号なら同じ book になりうるが、#471 は recent だけで、primary の long は触れていない",
        "rename_gates": ("T5_TIC_FLOW", "M16_WITHIN_CYCLE"),
    },
    "M11": {
        "candidate": "M11",
        "name": "macro data momentum",
        "mechanism": "インフレの加速と失業率の低下が相対的に大きい国の通貨は、将来の引き締めと資本流入で上がる（Dahlquist–Hasseltoft 2020）",
        "why_fx_should_lag": "macro は月次で少しずつ公表され、投資家の注意は限られる。1 回の公表では弱く、累積で効く（under-reaction）",
        "data": "OECD MEI CPI 前年比（EUR は HICP 指数から前年比）・OECD 失業率（ALFRED、request-level exclusion）",
        "exact_series": "CPALTT01{US,JP,GB,CA,CH}M659N、CPALTT01{AU,NZ}Q659N、CP0000EZ19M086NEST、LRHUTTTT{US,JP,GB,CA,AU,EZ}M156S、LRHUTTTT{CH,NZ}Q156S",
        "availability_lag": "月次は m+2 月末、四半期は参照期間の最後の月 + 2 か月の月末",
        "signal": "s_c = xs_z(インフレの 12 か月変化)_c − xs_z(失業率の 12 か月変化)_c。両方ある通貨だけ",
        "sign": "s が高い通貨を買う",
        "horizon": "1〜3 か月",
        "universe": "8 通貨（両入力が揃う通貨。recent は JPY の CPI が無く中央値 5 通貨）",
        "portfolio_mapping": "XS（既存の相対価値 book、第 1 主成分を中立化）",
        "primary_span": "long",
        "revision": "CURRENT_VINTAGE_ONLY_REVISION_CAVEAT（失業率の季節調整改訂）",
        "declared_weakness_before_alpha": (
            "**U1（貿易収支）は Dahlquist–Hasseltoft の構成要素で、NOT_SUPPORTED だった。** 貿易収支は入れない。"
            "recent span は短く（CPI 前年比の分母規則でさらに短くなる）、ほぼ情報を持たない。"
            "long の有効標本数 13.2。3 か月金利の 12 か月変化との cross-section 相関 0.318（#471 の carry change と一部重なる）"
        ),
        "rename_gates": ("U1_TRADE_BALANCE",),
    },
    "M16": {
        "candidate": "M16",
        "name": "米国 vs 他国の macro momentum → ドル",
        "mechanism": "米国の macro が他国より速く改善すると、ドル全体が上がる",
        "why_fx_should_lag": "M11 と同じ under-reaction。M11 の book は第 1 主成分を中立化してこの成分を捨てている",
        "data": "M11 と同じ入力",
        "exact_series": "M11 と同じ",
        "availability_lag": "M11 と同じ",
        "signal": "M11 の score の USD 成分（4 通貨以上ある日）",
        "sign": "USD 成分 > 0 → ドル買い / 7 通貨 basket 売り",
        "horizon": "1〜3 か月",
        "universe": "USD 対 7 通貨の等ウェイト basket",
        "portfolio_mapping": "DOLLAR（BOOK_CONFIG_DEVIATIONS）。効くのは符号だけ",
        "primary_span": "long",
        "revision": "CURRENT_VINTAGE_ONLY_REVISION_CAVEAT",
        "declared_weakness_before_alpha": (
            "M11 と情報集合が同じ。M11 が捨てた成分を測るので、2 本で 1 つの情報を分解している。"
            "long の有効標本数 23.1（GBP の lag を m+3 にした後）。反転のうち数回は通貨数の変化と同じ日（構成が起こした反転）。"
            "ドル track の E5（USD を除く LOO）は構造上ゆるく、book の半分を占める USD 脚の集中は検定されない"
        ),
        "rename_gates": ("T5_TIC_FLOW", "M15_WITHIN_CYCLE"),
    },
    "M10": {
        "candidate": "M10",
        "name": "FX 流動性 premium",
        "mechanism": "流動性が悪化した通貨は、そのリスクの補償として後で高い return を払う（liquidity risk premium）",
        "why_fx_should_lag": "悪化は強制的な売りと在庫の偏りを伴い、裁定資本がすぐには入らない",
        "data": "guarded M15 cache の bid / ask（20 pair、seen の recent span のみ。外部取得なし）",
        "exact_series": "M15 bar の bid_c / ask_c",
        "availability_lag": "当日の bar から作り、翌営業日から使う",
        "signal": "L_c = 直近 20 日の平均 log 相対 spread − 直近 250 日の平均（pair の日次中央値を通貨ごとに平均）",
        "sign": "L が高い（相対的に悪化した）通貨を買う",
        "horizon": "数週〜1 か月",
        "universe": "8 通貨",
        "portfolio_mapping": "XS",
        "primary_span": "recent（long に quote は無い）",
        "revision": "改訂無し",
        "declared_weakness_before_alpha": (
            "recent span 3.8 年だけ（MDE 1.00、有効標本数 0.5 — AR(1) 近似は rolling 窓の signal では過小に出る）。"
            "retail の quote が interbank の流動性を表すかは不確か。通貨別 spread は pair の平均で、"
            "pair 固有の shock を通貨ごとに識別していない。**20 日 / 250 日の比は実質的に通貨別の vol shock に近く、"
            "凍結した『悪化の後に戻る』は流動性 premium というより forced selling 後の reversal である**。"
            "最も近い family は T1 / Track 1 の vol 状態と multi-day reversal"
        ),
        "rename_gates": ("VOL_RATIO_STATE",),
    },
}
TRACKS["M01"] = {
    "candidate": "M01",
    "name": "Taylor 則の政策圧力 gap",
    "mechanism": "fundamentals が要求する政策金利と実際の政策金利の差が大きい国は、中銀が追いつくために引き締めを続け、通貨需要が生まれる",
    "why_fx_should_lag": "市場は観測できる金利差と forward guidance に錨を下ろし、fundamentals が示す将来の政策経路は中銀が動くまで部分的にしか織り込まれない",
    "data": "CPI 前年比（M11 と同じ）・失業率（M11 と同じ）・BIS 政策金利（WS_CBPOL、月末値、SDMX で date-bounded、detail=dataonly）",
    "exact_series": "M11 の CPI / 失業率 + BIS WS_CBPOL M.{US,JP,GB,CA,AU,NZ,CH,XM}",
    "availability_lag": "CPI・失業率は M11 と同じ、政策金利は m+1 月末",
    "signal": "gap_c = 1.5·インフレ_c − 1.0·(失業率_c − 直近 60 か月平均) − 政策金利_c。cross-section で z 化",
    "sign": "gap が高い（政策が fundamentals より緩い）通貨を買う",
    "horizon": "1〜3 か月",
    "universe": "3 入力が揃う通貨（JPY は 2013-04 … 2016-09 に政策金利が無い）",
    "portfolio_mapping": "XS",
    "primary_span": "long",
    "revision": "CURRENT_VINTAGE_ONLY_REVISION_CAVEAT（失業率）。政策金利は改訂無し",
    "declared_weakness_before_alpha": (
        "Taylor 係数（1.5 / 1.0）と Okun 係数 2 は文献の固定値で推定していない。r* とインフレ目標を国ごとに同じと置いている。"
        "**gap は −政策金利を含むので、インフレと失業率が同じなら低金利通貨を買う anti-carry になる** — "
        "閉じた carry の符号反転にならないよう、3 か月金利の cross-section z との rename gate を置く。M11 と入力を共有する。"
        "**long の有効標本数 6.2**（POWER_RULE の上限に掛かる）、recent は 2.3 年・中央値 5 通貨"
    ),
    "rename_gates": ("CARRY_LEVEL_XS", "M11_WITHIN_CYCLE"),
}

for _track, _row in TRACKS.items():
    _row["primary_span"] = "recent" if _track == "M10" else "long"

EXECUTION_ORDER: Final[tuple[str, ...]] = ("M15", "M11", "M16", "M01", "M10")

RENAME_GATES: Final[dict[str, dict[str, Any]]] = {
    "CARRY_LEVEL_XS": {
        "comparator": "3 か月銀行間金利の cross-section z（閉じた carry の signal）",
        "statistic": "日次 score の cross-section 相関の平均の絶対値",
        "threshold": 0.8,
        "if_exceeded": "RENAME_OF_A_PRIOR_TRACK（carry、符号によらない）",
    },
    "M11_WITHIN_CYCLE": {
        "comparator": "M11 の score",
        "statistic": "日次 score の cross-section 相関の平均の絶対値",
        "threshold": 0.8,
        "if_exceeded": "RENAME_WITHIN_THIS_CYCLE",
    },
    "VOL_RATIO_STATE": {
        "comparator": "通貨別 realised vol の 20 日 / 250 日比（log）の cross-section 偏差（currency excess return から作る）",
        "statistic": "日次 score の cross-section 相関の平均の絶対値",
        "threshold": 0.8,
        "if_exceeded": "RENAME_OF_A_PRIOR_TRACK（vol 状態）",
    },
    "T5_TIC_FLOW": {
        "comparator": "Top-Five T5（TIC flow）の score の USD 列",
        "statistic": "重なる日の USD 列の相関の絶対値",
        "threshold": 0.8,
        "if_exceeded": "RENAME_OF_A_PRIOR_TRACK",
    },
    "U1_TRADE_BALANCE": {
        "comparator": "next-five U1（貿易収支）の score",
        "statistic": "日次 score の cross-section 相関の平均の絶対値",
        "threshold": 0.8,
        "if_exceeded": "RENAME_OF_A_PRIOR_TRACK（U1 の救済になる）",
    },
    "M16_WITHIN_CYCLE": {
        "comparator": "M16 の USD 列",
        "statistic": "重なる日の USD 列の相関の絶対値",
        "threshold": 0.8,
        "if_exceeded": "RENAME_WITHIN_THIS_CYCLE（2 本を 1 本として読む）",
    },
    "M15_WITHIN_CYCLE": {
        "comparator": "M15 の USD 列",
        "statistic": "重なる日の USD 列の相関の絶対値",
        "threshold": 0.8,
        "if_exceeded": "RENAME_WITHIN_THIS_CYCLE",
    },
}

#: Stage 0（取得と signal-blind feasibility）の結果。**結果の前に記録する。**
STAGE_0_OUTCOME: Final[dict[str, Any]] = {
    "acquisition_record": "artifacts/research/mechanism_redesign/acquisition.json",
    "feasibility_record": "artifacts/research/mechanism_redesign/feasibility.json",
    "per_track": {
        "M15": {"status": "PASSED", "sign_regimes_long": 6, "sign_regimes_recent": 1},
        "M11": {"status": "PASSED", "years_long": 17.69, "years_recent": 3.21},
        "M16": {"status": "PASSED", "sign_regimes_long": 28, "sign_regimes_recent": 5},
        "M10": {"status": "PASSED_RECENT_ONLY", "years_recent": 3.82},
        "M01": {"status": "PASSED", "route": "BIS SDMX（acquisition_amendment.json）"},
    },
    "amendment_record": "artifacts/research/mechanism_redesign/acquisition_amendment.json",
    "not_selected": {
        "M17": "ROUTE_NOT_REQUEST_BOUNDED — ALFRED が JPNEPUINDXM の期間指定を無視した（D-M2）。EPU family は request-level exclusion を保証できない",
        "M18": "DATA_NOT_FEASIBLE_AT_THIS_SCOPE — CLI は現行 vintage が look-ahead を含み、point-in-time の再構成に数百回の vintage request が要る",
        "M02": "DATA_LIMITED — 日次 2 年金利が無料で 3 通貨",
        "M09": "BREADTH_ONE — 最低 3 通貨の規則を満たさない",
        "M14": (
            "ELIGIBLE_NOT_SELECTED_MAX_FIVE — U5 は第 1 主成分を中立化した book で測ったので、ドル factor の funding stress は"
            "未測定（初版の『U5 の rename』は過剰一般化だった）。ただし最大 5 本の枠を prior score の順で埋め、M14（0.648）は 6 番目。"
            "Stage 0 は行っていない"
        ),
    },
    "selection_rule": (
        "overlap audit を通り、Stage 0 で primary span が取れた候補を選ぶ。5 本を超えるときは prior score の順。"
        "初版は M01 を『政策金利が無い』として落としたが、それは ALFRED 経路の制約で、BIS の SDMX で取れた（R-6）。"
        "M01 を足して 5 本。M14 は 6 番目で選ばない"
    ),
}

METRICS: Final[tuple[str, ...]] = _nf.METRICS
EXPLORATION_DISCLOSURE: Final[str] = "FIVE_WAY_EXPLORATORY_DEVELOPMENT_SEARCH_NO_CONFIRMATION_CLAIM"
SHARED_BLOCKERS: Final[tuple[str, ...]] = _nf.SHARED_BLOCKERS
INTERPRETATION: Final[str] = (
    "development の結果は sign・大きさ・net economics・incremental information・null percentile・"
    "安定性・breadth・集中・turnover・cost 耐性を示すだけで、confirmation ではない。"
    "**単一 candidate に Sharpe 0.3 の証明を求めない**（#489: 必要年数が非現実的）"
)

_SIGNALS_SOURCE: Final[Path] = Path(__file__).with_name("signals.py")
_REPO: Final[Path] = Path(__file__).resolve().parents[3]

#: **結果を変えうるコード**の閉包（R-1 / RF-5、re-audit RF-B）。driver.py から `scripts.*` の import を
#: **静的に辿って**集める（手書きの列挙は抜けていた: cost 定数・PAIRS_20・top_five.prereg など）。
#: driver.py は凍結値そのものを持つので、`FROZEN_DIGEST` の行を除いて hash する。
CLOSURE_ROOT: Final[str] = "scripts/research/mechanism_redesign/driver.py"


def _module_file(module: str) -> Path | None:
    base = _REPO / Path(*module.split("."))
    if base.with_suffix(".py").exists():
        return base.with_suffix(".py")
    if (base / "__init__.py").exists():
        return base / "__init__.py"
    return None


def _package_inits(path: Path) -> list[Path]:
    out = []
    parent = path.parent
    while parent != _REPO and (parent / "__init__.py").exists():
        out.append(parent / "__init__.py")
        parent = parent.parent
    return out


def code_closure() -> tuple[str, ...]:
    import ast

    seen: set[Path] = set()
    stack = [_REPO / CLOSURE_ROOT]
    while stack:
        path = stack.pop()
        if path in seen:
            continue
        seen.add(path)
        stack.extend(p for p in _package_inits(path) if p not in seen)
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                names = [node.module] + [f"{node.module}.{alias.name}" for alias in node.names]
            for name in names:
                if not name.startswith("scripts"):
                    continue
                target = _module_file(name)
                if target is not None and target not in seen:
                    stack.append(target)
    return tuple(sorted(str(path.relative_to(_REPO)).replace("\\", "/") for path in seen))


INPUT_MANIFEST: Final[str] = "artifacts/research/mechanism_redesign/inputs_manifest_v2.json"


def _source_sha(relative: str) -> str:
    raw = (_REPO / relative).read_bytes().replace(b"\r\n", b"\n")
    if relative.endswith("mechanism_redesign/driver.py"):
        raw = b"\n".join(line for line in raw.split(b"\n") if not line.startswith(b"FROZEN_DIGEST"))
    return hashlib.sha256(raw).hexdigest()


def track_status(track: str, suffix: str) -> str:
    if suffix not in TRACK_STATUS_SUFFIXES:
        raise ValueError(f"未登録の status: {suffix}")
    return f"{track}_{TRACKS[track]['candidate']}_{suffix}"


def signals_source_digest() -> str:
    """signal の式そのもの（signals.py の bytes）の sha256。改行コードの差は正規化する。"""
    raw = _SIGNALS_SOURCE.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(raw).hexdigest()


def _payload() -> dict[str, Any]:
    from scripts.research.mechanism_redesign import signals

    return {
        "cycle": CYCLE,
        "authority": AUTHORITY,
        "workflow_status": WORKFLOW_STATUS,
        "forbidden": list(FORBIDDEN),
        "universe": list(UNIVERSE),
        "spans": SPANS,
        "protected_bounds": PROTECTED_BOUNDS,
        "primary_span_rule": PRIMARY_SPAN_RULE,
        "execution_layer": EXECUTION_LAYER,
        "book_config": BOOK_CONFIG,
        "book_config_deviations": BOOK_CONFIG_DEVIATIONS,
        "book_config_deviation_why": BOOK_CONFIG_DEVIATION_WHY,
        "cost": COST,
        "benchmarks": list(BENCHMARKS),
        "control": CONTROL,
        "null_diagnostic": NULL_DIAGNOSTIC,
        "development_economics": DEVELOPMENT_ECONOMICS,
        "dollar_track_breadth_rule": DOLLAR_TRACK_BREADTH_RULE,
        "stage_2_eligibility": STAGE_2_ELIGIBILITY,
        "verdict_logic": [dict(row) for row in VERDICT_LOGIC],
        "failure_class_rule": FAILURE_CLASS_RULE,
        "demoted_gate": DEMOTED_GATE,
        "capacity_reporting": CAPACITY_REPORTING,
        "track_status_suffixes": list(TRACK_STATUS_SUFFIXES),
        "nuisance": signals.NUISANCE,
        "nuisance_applies": {k: list(v) for k, v in NUISANCE_APPLIES.items()},
        "nuisance_rule": NUISANCE_RULE,
        "mechanism_constants": {
            "quarterly_staleness_days": signals.QUARTERLY_STALENESS_DAYS,
            "lag_months": signals.LAG_MONTHS,
            "quarter_extra_months": signals.QUARTER_EXTRA_MONTHS,
            "liquidity_lag_business_days": signals.LIQUIDITY_LAG_BUSINESS_DAYS,
            "min_bars_for_a_day": signals.MIN_BARS_FOR_A_DAY,
            "min_foreign_rates": signals.MIN_FOREIGN_RATES,
            "min_currencies": signals.MIN_CURRENCIES,
        },
        "tracks": TRACKS,
        "execution_order": list(EXECUTION_ORDER),
        "rename_gates": RENAME_GATES,
        "stage_0_outcome": STAGE_0_OUTCOME,
        "metrics": list(METRICS),
        "exploration_disclosure": EXPLORATION_DISCLOSURE,
        "shared_blockers": list(SHARED_BLOCKERS),
        "interpretation": INTERPRETATION,
        "signals_source_sha256": signals_source_digest(),
        "freeze_amendment_pre_alpha": FREEZE_AMENDMENT_PRE_ALPHA,
        "financing": FINANCING,
        "power_rule": POWER_RULE,
        "rename_not_evaluable_rule": RENAME_NOT_EVALUABLE_RULE,
        "lag_overrides": {f"{a}/{b}": v for (a, b), v in signals.LAG_OVERRIDES.items()},
        "lag_justification": signals.LAG_JUSTIFICATION,
        "taylor": {
            "inflation_coef": signals.TAYLOR_INFLATION_COEF,
            "unemployment_gap_coef": signals.TAYLOR_UNEMPLOYMENT_GAP_COEF,
            "trend_window": signals.UNEMPLOYMENT_TREND_WINDOW,
            "trend_min_obs": signals.UNEMPLOYMENT_TREND_MIN_OBS,
        },
        "code_closure_sha256": {path: _source_sha(path) for path in code_closure()},
        "freeze_amendment_pre_alpha_2": FREEZE_AMENDMENT_PRE_ALPHA_2,
        "input_manifest_sha256": hashlib.sha256(
            (_REPO / INPUT_MANIFEST).read_bytes().replace(b"\r\n", b"\n")
        ).hexdigest(),
    }


def freeze_digest() -> str:
    return hashlib.sha256(
        json.dumps(_payload(), sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()


__all__ = [
    "BOOK_CONFIG",
    "BOOK_CONFIG_DEVIATIONS",
    "CAPACITY_REPORTING",
    "COST",
    "CYCLE",
    "DEVELOPMENT_ECONOMICS",
    "EXECUTION_ORDER",
    "NULL_DIAGNOSTIC",
    "NUISANCE_APPLIES",
    "PRIMARY_SPAN_RULE",
    "RENAME_GATES",
    "STAGE_0_OUTCOME",
    "STAGE_2_ELIGIBILITY",
    "TRACKS",
    "freeze_digest",
    "track_status",
]
