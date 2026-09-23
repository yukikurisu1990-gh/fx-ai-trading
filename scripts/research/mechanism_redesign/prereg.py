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
WORKFLOW_STATUS: Final[str] = "FOUR_TRACKS_FROZEN_AWAITING_ALPHA_EXECUTION"

FORBIDDEN: Final[tuple[str, ...]] = (
    "fresh pool / historical OOS / dead window / forward epoch の読み取り",
    "有料データの購入",
    "認証付き broker API",
    "demo / paper / live",
    "unrestricted nonlinear ML",
    "post-hoc multi-source optimization",
    "U1..U5 の horizon / sign / subset rescue",
    "6 本目以降の alpha 実行（今回は 4 本）",
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
        "4 本を同じ null に当てるので、**いずれか 1 本が 5% を切る確率は帰無でも約 19%**（1 − 0.95⁴）。"
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

NUISANCE_APPLIES: Final[dict[str, tuple[str, ...]]] = {
    "M15": ("max_staleness_days_monthly", "implementation_tolerance_band"),
    "M11": ("max_staleness_days_monthly", "change_window_months", "implementation_tolerance_band"),
    "M16": ("max_staleness_days_monthly", "change_window_months", "implementation_tolerance_band"),
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
        "revision": "市場金利、改訂無し",
        "declared_weakness_before_alpha": (
            "**long span で符号の regime が 6 個しかない**（反転 5 回 / 17.7 年）。結果は少数の regime の当たり外れで"
            "決まり、E6（集中）が偽になりやすい。**recent span は全期間ドル買い**（米金利が常に高い）ので、"
            "recent の M15 は benchmark の constant_long_usd と同じ book になり、情報を持たない"
        ),
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
            "recent span は 3.2 年・5 通貨で、ほぼ情報を持たない"
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
        "declared_weakness_before_alpha": "M11 と情報集合が同じ。M11 が捨てた成分を測るので、2 本で 1 つの情報を分解している",
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
            "recent span 3.8 年だけ（MDE 1.00）。retail の quote が interbank の流動性を表すかは不確か。"
            "**符号の理論が 2 つある**（悪化時に売られて後で戻る premium か、流動性の悪い通貨がさらに売られるか）。"
            "前者を凍結した"
        ),
        "rename_gates": (),
    },
}
for _track, _row in TRACKS.items():
    _row["primary_span"] = "recent" if _track == "M10" else "long"

EXECUTION_ORDER: Final[tuple[str, ...]] = ("M15", "M11", "M16", "M10")

RENAME_GATES: Final[dict[str, dict[str, Any]]] = {
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
    },
    "not_selected": {
        "M01": "DATA_MAPPING_BLOCKED — 政策金利が USD 以外取れない（IRSTCB01 は 404 / title 不一致）。3 か月金利での代用は変数が違うので行わない",
        "M17": "ROUTE_NOT_REQUEST_BOUNDED — ALFRED が JPNEPUINDXM の期間指定を無視した（D-M2）。EPU family は request-level exclusion を保証できない",
        "M18": "DATA_NOT_FEASIBLE_AT_THIS_SCOPE — CLI は現行 vintage が look-ahead を含み、point-in-time の再構成に数百回の vintage request が要る",
        "M02": "DATA_LIMITED — 政策金利が取れず、日次 2 年金利も無料で 3 通貨",
        "M09": "BREADTH_ONE — 最低 3 通貨の規則を満たさない",
    },
    "selection_rule": (
        "overlap audit を通り、Stage 0 で primary span が取れた候補を全部選ぶ（4 本）。"
        "**5 本目を無理に足さない**（裁定 §21）。prior score は選抜に使っていない"
    ),
}

METRICS: Final[tuple[str, ...]] = _nf.METRICS
EXPLORATION_DISCLOSURE: Final[str] = "FOUR_WAY_EXPLORATORY_DEVELOPMENT_SEARCH_NO_CONFIRMATION_CLAIM"
SHARED_BLOCKERS: Final[tuple[str, ...]] = _nf.SHARED_BLOCKERS
INTERPRETATION: Final[str] = (
    "development の結果は sign・大きさ・net economics・incremental information・null percentile・"
    "安定性・breadth・集中・turnover・cost 耐性を示すだけで、confirmation ではない。"
    "**単一 candidate に Sharpe 0.3 の証明を求めない**（#489: 必要年数が非現実的）"
)

_SIGNALS_SOURCE: Final[Path] = Path(__file__).with_name("signals.py")


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
