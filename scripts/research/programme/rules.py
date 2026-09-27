# ruff: noqa: E501 -- governance prose
"""programme の判定規則（2026-09-28 裁定 §24–§33）。**規則であって、実行の許可ではない。**

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

ここにあるのは:

- 保護情報の台帳（§28 の D-M3 を含む）
- 何が閉じ、何が開いているか（§24・§25）
- forward に進める最低条件（§26）と、ledger の各行をそれに当てた結果
- broker financing の認証取得（§29）と有料 data（§30）の trigger
- STOP / CONTINUE の条件（§31・§32）
- programme の path 比較（§15）

**どの関数も、条件を満たしたときに「許可された」とは返さない。** 返すのは「Human + ChatGPT に
上げる資格がある」までで、forward・fresh・broker auth・有料 data は、それぞれ別の Red / Amber gate である。
`FX_RESEARCH_PAUSED` は自動では立てない（§33）。
"""

from __future__ import annotations

import re
from typing import Any, Final

# ----------------------------------------------------------------------
# 保護情報の台帳（§28）
# ----------------------------------------------------------------------
D_M3_TOKEN: Final[str] = (
    "JPY_RATE_RELATED_FORWARD_CONFIRMATION_CONTAMINATED_BY_EXTERNAL_INFORMATION_EXPOSURE"
)

PROTECTED_INFORMATION_LEDGER: Final[tuple[dict[str, str], ...]] = (
    {
        "item": "FX fresh pool 2016-06-02 … 2021-04-25",
        "state": "UNREAD（M15 archive・公開 FX とも request で除外）",
        "scope": "全 FX track の将来の確認用",
    },
    {
        "item": "historical EXPLORATORY_OOS_SLICE",
        "state": "HISTORICAL_EXPLORATORY_OOS_PRISTINE_CLAIM_WITHDRAWN（R1 が 1 pair 1 行、計 20 行を decode。値は出力に届いていない）",
        "scope": "formal evidence には使えない。Formal Confirmation は将来の未接触 epoch を使う",
    },
    {"item": "dead window", "state": "UNREAD", "scope": "—"},
    {
        "item": "forward Formal Confirmation epoch（FX 価格）",
        "state": "UNREAD。FORWARD_EPOCH_ADOPTION_BLOCKED_INSUFFICIENT_SAMPLE_ADOPTION_WAITS",
        "scope": "—",
    },
    {
        "item": "D-M3: lead session が forward epoch の BoJ 政策決定（2026 年）を読んだ",
        "state": D_M3_TOKEN,
        "scope": "**JPY 金利に関係する forward 確認だけ**（JPY の政策金利・carry を signal または会計に使う track）。FX 価格の forward epoch 全体を汚染したとは扱わない",
    },
    {
        "item": "D-M1: ALFRED の metadata page を 2026 年の最新観測付きで parse",
        "state": "EXTERNAL_INFORMATION_EXPOSURE（値は使っていない）",
        "scope": "その series の forward 確認で開示が要る",
    },
    {
        "item": "D-M2: EPU の response を parse して拒否",
        "state": "EXTERNAL_INFORMATION_EXPOSURE",
        "scope": "EPU を使う track",
    },
    {
        "item": "D-5: next-five の bulk response（H.4.1 zip・SNB cube・BoJ・Fed JSON）が保護期間の行を含んだまま memory 上で parse され、保存前に切られた",
        "state": "EXTERNAL_INFORMATION_EXPOSURE（C-4 の月次 stamp 2016-06-01 / 2025-12-01 は保存された。run4 で読む側から落とした）",
        "scope": "U1–U5 の source の forward 確認で開示が要る",
    },
    {
        "item": "C-1: Top-Five の signals._two_year が保護期間・forward epoch の parquet 行を読んでいた（recent の T3 score 3 件）",
        "state": "報告値の前に閉じた。cycle は CORRECTED_AFTER_RESULTS_WERE_SEEN",
        "scope": "Top-Five",
    },
    {
        "item": "CPI 前年比の分母・HICP 2025=100・現行 vintage の SA 係数",
        "state": "保護期間の水準が逆算可能な形で保存された（逆算はしていない）",
        "scope": "M01 / M11 / M16 の macro 入力",
    },
    {
        "item": "ML Step 4 365d_BA holdout（2026-03-01 … 2026-04-24）",
        "state": "CONSUMED",
        "scope": "M1 lineage（終了）",
    },
    {
        "item": "seen として消費済みの span",
        "state": "EXPLORATORY_SEEN_DATA: M15 archive の 3 window（2021-04-26 … 2025-12-28）、公開 pre-2016 FX と macro（1999 … 2016-06-01）",
        "scope": "いずれも holdout・confirmation に使えない",
    },
)


# ----------------------------------------------------------------------
# 閉じたもの・開いているもの（§24・§25）
# ----------------------------------------------------------------------
CLOSURE_PRINCIPLE: Final[str] = (
    "閉じるのは『この情報集合 × この定式化 × この seen の文脈』だけ。"
    "『FX に edge は無い』とは言わない。言えるのは、試した形では seen data の上で null と区別できる経済的な効果が出なかったこと。"
    "span が短い検定は『閉じた』のではなく『検出力不足で決まらなかった』に近い — 各項目に MDE を付ける"
)

#: 各項目に、決定に使った span の長さと、そこでの MDE（両側 5%・検出力 80%、Sharpe）を付ける。
CLOSED: Final[tuple[dict[str, str], ...]] = (
    {
        "what": "M15 の multi-day reversal / momentum（lb480_h480、PAIRS_20、M15 derived）",
        "scope": "両方向とも 3 span（0.7 + 2 + 2 年）で null と区別できない。family を active 探索から外した",
        "span_and_mde": "各 span 約 2 年、MDE ≈ 2.0（pips 単位の検定で、Sharpe の MDE は目安）",
    },
    {
        "what": "M15 textbook rules・15 本の戦略 family・reversal の parameter sweep",
        "scope": "development 2025 の上で cost 後すべて負。walk-forward でも選べない",
        "span_and_mde": "0.7 年、MDE ≈ 3.4。**cost が gross を大きく上回った**ことが結論で、検出力の話ではない",
    },
    {
        "what": "M15 の price-path structure（VR < 1）の収益化",
        "scope": "構造は null を超えて実在（p 0.005）するが、線形 selector 8 特徴・7 母集団で round trip cost の 6–16%",
        "span_and_mde": "3 panel。cost に対する比で閉じた（検出力ではない）",
    },
    {
        "what": "US CPI surprise・COT positioning・survey consensus",
        "scope": (
            "事前登録の判定は 2 つの決定 panel の両方を要求し、どれも NOT_SUPPORTED。"
            "ただし CPI 4h は 2023–25 panel で family-max p 0.040（family-wise で通過）、2021–23 panel では family-max p 0.99、"
            "development 2025 では 0.75。CPI 1h は family-max p 0.124 / 0.906"
        ),
        "span_and_mde": "各 panel 2 年、event 単位の MDE（例: CPI 4h で 19.1 pips/pair-event、観測 net 15.3）。**検出力不足に近い**",
    },
    {
        "what": "continuous currency portfolio（Track 1）・model learning M01/M03/M13",
        "scope": "walk-forward で事前登録の pass rule を満たさない（Track 1 net −0.84）",
        "span_and_mde": "out-of-fold 2.9 年、MDE ≈ 1.6",
    },
    {
        "what": "市場利回り repricing（5 日）・実質為替 valuation",
        "scope": "5 日は cost で負（turnover 82〜98）。valuation は名目平均回帰より有意に悪い（増分 IC の NW t −3.34）",
        "span_and_mde": "4.8 年（MDE 1.28）/ 12.6 年（MDE 0.79）。valuation は有意な**負**の増分で閉じた",
    },
    {
        "what": "Top-Five T1–T4、next-five U1・U3・U4・U5、mechanism redesign M10",
        "scope": "NOT_SUPPORTED_IN_SEEN_DEVELOPMENT（T3・U3・U5・M10 の long は DATA_NOT_DECISION_GRADE）。T4 と T1・T2 は cost で負",
        "span_and_mde": "long 17 年（MDE 0.67）と recent 2〜4.8 年（MDE 1.3〜2.0）",
    },
    {
        "what": "M15 USD factor（carry + macro）",
        "scope": "M15_CORRECTED_FINANCING_NOT_DECISION_GRADE。spot ≈ 0、economics は financing の仮定次第",
        "span_and_mde": "17.7 年、MDE 0.67、有効標本 5",
    },
)

OPEN: Final[dict[str, tuple[str, ...]]] = {
    "UNTESTED": (
        "**公開の長い span（1999–2016）での古典的 premia**: 断面 carry（G10、k 本の long-short）と 1〜12 か月の通貨 momentum。"
        "long span で検定したのは USD factor の carry（M15）と 4〜6 日の momentum 類似・valuation だけ",
        "options / risk-reversal・implied vol の情報（有料）",
        "order flow・positioning の高頻度 data（有料）",
        "cross-asset（金利先物・株・商品）を使う定式化の大半",
        "family 単位で事前固定した合成（1 つの統計量）",
    ),
    "UNDERPOWERED": (
        "政策金利 carry（pair / 断面 k2・k3 / 変化）: 2 panel × 2 年、MDE ≈ 2.0。文献でよく引かれる carry の Sharpe はこれより遥かに小さい — **閉じたのではなく決まらなかった**",
        "US CPI surprise・COT・survey consensus（上記、event 単位の MDE が観測値を上回る）",
        "Sharpe 0.3 前後の効果全般（seen の最長 22 年で検出力 0.3 前後）",
        "月次 macro の遅い signal（有効標本 5–25）: M11・M01・M16 はここ",
        "USD factor（breadth 1、符号 regime 6–28）",
        "20 日の市場利回り repricing（T-R2）: gross 0.83 だが cost 8.2%/年で net 0.05",
    ),
    "NEGATIVE_BUT_NOT_REFUTED": (
        "multi-day reversal / momentum（区間が 0 を跨ぐ負の点推定）",
        "next-five U2（long −0.07）",
    ),
    "DATA_BLOCKED": (
        "T3・U3・U5・M10 の long span（data が decision grade でない）",
        "非 USD surprise（vintage archive が無い）",
    ),
    "PAID_ONLY": ("consensus の有料 vintage、options、tick / order book の長い履歴",),
    "FINANCING_UNKNOWN": (
        "全行の FULL_RETAIL_NET（broker financing 履歴は認証が必要で、今回取得禁止）",
        "financing を除いた positive（U2 / U4 recent・T-R2・T-V・M11・M01・M16）は上方に偏っている。M01 は judged（carry + markup 込み）で 0.30 → 0.08",
    ),
    "CONFIRMATION_BLOCKED": (
        "forward epoch は採用待ち（FORWARD_EPOCH_ADOPTION_BLOCKED_INSUFFICIENT_SAMPLE_ADOPTION_WAITS）",
        "fresh pool は未読で保護中（使う判断は Human + ChatGPT）",
    ),
    "CONTAMINATED": (f"JPY 金利に関係する forward 確認（{D_M3_TOKEN}）",),
}


# ----------------------------------------------------------------------
# forward の最低条件（§26）
# ----------------------------------------------------------------------
FORWARD_MIN_NULL_PERCENTILE: Final[float] = 0.95
FORWARD_MIN_EFFECTIVE_N: Final[float] = 10.0
#: financing の drag（Sharpe の単位、markup 1%/pair notional/年あたり）。#495 の USD-factor book で記録された値
#: （M16: 0.344 → 0.070、M15: 0.165 → −0.109、どちらも markup 0 → 2% で 0.274 下がる）。book の gross notional / vol が
#: 違えば変わるので、**参照値**として使う。APPROXIMATE_RESEARCH_FINANCING であって実際の broker financing ではない。
FINANCING_DRAG_SHARPE_PER_1PCT_MARKUP_REFERENCE: Final[float] = 0.137
CONSERVATIVE_MARKUP_PCT: Final[float] = 2.0

FORWARD_ELIGIBILITY_CONDITIONS: Final[tuple[str, ...]] = (
    "F1 evidence tier A（事前登録・1 回・1 つの仮説の primary・事後修正なし・無効でない・多数の cell からの選択でない）",
    f"F2 development で null を超える: null percentile ≥ {FORWARD_MIN_NULL_PERCENTILE}（または p ≤ 0.05）。"
    "family-max の p が記録されていればそれを使い、**同じ mechanism の全ての決定 span で**成り立つこと",
    "F3 financing 抜きの TC-net が、conservative の financing drag（markup 2%/pair notional、参照 0.274 Sharpe）を引いても正",
    f"F4 有効標本数 ≥ {FORWARD_MIN_EFFECTIVE_N:.0f}（distinct signal states は有効標本数ではないので不明扱い）",
    "F5 LOO・concentration が破綻していない（最悪 LOO が正、top-10 日の寄与 < 1）",
    f"F6 汚染されていない（{D_M3_TOKEN} の対象 = signal か judged P&L が金利を使う track。対象なら金利を使わない形で凍結し直す必要がある）",
    "F7 forward の長さで意思決定が変わる（§27 の情報量）",
    "F8 凍結 digest・入力 manifest・1 回限りの実行が forward 前に commit されている",
)


def forward_eligibility(
    row: dict[str, Any], siblings: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    """1 行を §26 の最低条件に当てる。**満たしても forward の許可ではない**（Red gate）。

    `siblings` は同じ mechanism の他の決定 span の primary 行（F2 はその全てで成り立つ必要がある）。
    """
    net = row.get("sharpe_ex_financing")
    eff = (
        row.get("effective_n")
        if row.get("effective_n_kind") == "EFFECTIVE_INDEPENDENT_OBSERVATIONS"
        else None
    )
    loo = row.get("loo_worst")
    conc = row.get("concentration_top10")

    def beats_null(r: dict[str, Any]) -> bool | None:
        pct, p = r.get("null_percentile"), r.get("p_value")
        family_p = _family_max_p(r)
        if family_p is not None:
            #: a recorded family-max p takes precedence over any cell-level statistic
            return bool(family_p <= 0.05)
        if pct is None and p is None:
            return None
        return bool(
            (pct is not None and pct >= FORWARD_MIN_NULL_PERCENTILE)
            or (p is not None and p <= 0.05)
        )

    f2_all = [beats_null(r) for r in [row, *(siblings or [])]]
    conservative = FINANCING_DRAG_SHARPE_PER_1PCT_MARKUP_REFERENCE * CONSERVATIVE_MARKUP_PCT
    checks: dict[str, bool | None] = {
        "F1_tier_A": row.get("evidence_tier") == "A",
        "F2_beats_null_on_every_deciding_span": False
        if False in f2_all
        else (None if None in f2_all else True),
        "F3_positive_after_conservative_financing": None
        if net is None
        else bool(net - conservative > 0),
        "F4_effective_n": None if eff is None else bool(eff >= FORWARD_MIN_EFFECTIVE_N),
        "F5_robustness": None if loo is None or conc is None else bool(loo > 0 and 0 <= conc < 1),
        "F6_not_contaminated": not row.get("rate_exposure", False),
    }
    return {
        "track_id": row["track_id"],
        "checks": checks,
        "passed": [k for k, v in checks.items() if v is True],
        "failed": [k for k, v in checks.items() if v is False],
        "unknown_not_recorded": [k for k, v in checks.items() if v is None],
        "eligible_to_raise_to_human": all(v is True for v in checks.values()),
        "note": "None は記録が無いことで、合格ではない。F7・F8 は行の値では判定できない。F1–F6 を全て満たしても forward は別の Red gate",
    }


def _family_max_p(row: dict[str, Any]) -> float | None:
    """notes に記録された family-max の p（あれば、cell 単独の p より優先する）。"""
    match = re.search(r"family_max_p=([0-9.]+)", str(row.get("notes") or ""))
    return float(match.group(1)) if match else None


# ----------------------------------------------------------------------
# broker financing（§29）と有料 data（§30）の trigger
# ----------------------------------------------------------------------
BROKER_AUTH_TRIGGER: Final[tuple[str, ...]] = (
    "B1 financing を除いた edge が正で、null と区別できる（percentile ≥ 0.95）",
    "B2 financing の不確実性が結論を左右する（financing の cell の間で符号か判定が変わる）",
    "B3 有効標本数が足りる（≥ 10）",
    "B4 実際の financing が分かると意思決定が変わる",
    "B5 それより大きな不確実性（検出力・汚染・data の質）が結論を支配していない",
)

BROKER_TRIGGER_LIMITATION: Final[str] = (
    "carry を収穫する book（M15 のように spot ≈ 0 で edge が financing そのもの）では B1 が原理的に成り立たない。"
    "その場合 broker financing の価値は『edge があるか』ではなく『carry が retail の markup を上回るか』で、"
    "B1 の代わりに『政策金利差の carry が null を超える』を置くべきだが、M15 の carry 込み total も percentile 0.60 で超えていない"
)


def broker_auth_trigger(
    ex_financing_row: dict[str, Any], *, sign_changes_across_financing_cells: bool
) -> dict[str, Any]:
    pct = ex_financing_row.get("null_percentile")
    net = ex_financing_row.get("sharpe_ex_financing")
    eff = (
        ex_financing_row.get("effective_n")
        if ex_financing_row.get("effective_n_kind") == "EFFECTIVE_INDEPENDENT_OBSERVATIONS"
        else None
    )
    b1 = net is not None and net > 0 and pct is not None and pct >= FORWARD_MIN_NULL_PERCENTILE
    b3 = eff is not None and eff >= FORWARD_MIN_EFFECTIVE_N
    clean = not ex_financing_row.get("rate_exposure", False) and ex_financing_row.get(
        "evidence_tier"
    ) in {"A", "B"}
    checks = {
        "B1_ex_financing_edge_beats_null": b1,
        "B2_financing_material": sign_changes_across_financing_cells,
        "B3_effective_n": b3,
        "B4_decision_changes": b1 and sign_changes_across_financing_cells,
        "B5_no_larger_uncertainty_dominates": b1 and b3 and clean,
    }
    return {
        "track_id": ex_financing_row["track_id"],
        "checks": checks,
        "met": all(checks.values()),
        "limitation": BROKER_TRIGGER_LIMITATION,
    }


PAID_DATA_TRIGGER: Final[tuple[str, ...]] = (
    "P1 無料 data では検定できない、事前に書いた具体的な仮説がある（data を買ってから仮説を探さない）",
    "P2 その data の期間と頻度で、想定する効果に検出力がある（§13 の年数の制約を data が破れる — 例: event 数・breadth で有効標本を増やせる）",
    "P3 vintage / point-in-time が保証され、保護期間を request で除外できる",
    "P4 費用が、得られる情報量（forward 何年分に相当するか）に見合う",
    "P5 Human + ChatGPT の承認（有料 data は Amber 以上）",
)
PAID_DATA_TRIGGER_EVALUATION: Final[str] = (
    "ledger の行には当てていない（有料 data の候補仮説が 1 つも書かれていないので、P1 の時点で満たさない）"
)


# ----------------------------------------------------------------------
# STOP / CONTINUE（§31・§32）。FX_RESEARCH_PAUSED は自動では立てない（§33）
# ----------------------------------------------------------------------
STOP_CONDITIONS: Final[tuple[str, ...]] = (
    "S1 新しい候補が、検出力のある設計でも null と区別できない状態が続き、残りの未検定領域が有料 data か forward しかない",
    "S2 事業目標（年 5%）に要る TC-net Sharpe（vol 10% で financing 込み 0.5–0.77）が、programme の縮小推定の上位でも届かない範囲にあると確かめられた",
    "S3 保護 data を使う以外に情報を増やす手段が無く、その使用が承認されない",
    "S4 financing を含めた retail の net が、どの現実的な仮定でも負",
)

CONTINUE_CONDITIONS: Final[tuple[str, ...]] = (
    "C1 事前に書いた family 単位の設計（1 つの統計量、best-of-N なし）で、検出力 ≥ 0.5 を持てる対象がある",
    "C2 未検定の情報源に、経済的な理由と point-in-time の入手経路がある",
    "C3 研究の目的を『年 5% の戦略』から『情報の測定』へ明示的に変え、そのための予算を Human + ChatGPT が認める",
)

PAUSE_POLICY: Final[str] = (
    "FX_RESEARCH_PAUSED は自動では立てない。STOP 条件の評価は Human + ChatGPT に上げる"
)


# ----------------------------------------------------------------------
# path 比較（§15）。評価は定性的な順位（高・中・低）で、数値の見せかけの精度を付けない
# ----------------------------------------------------------------------
_ROUTE_THROUGH_FORWARD: Final[str] = (
    "decision-bearing な結論には forward での Formal Confirmation が要る。36 か月でも SE 0.58 なので、"
    "どの path も forward の段階で D と同じ時間と検出力の制約を受ける（B・C は forward の前の選別であって代わりではない）"
)

PATH_COMPARISON: Final[dict[str, dict[str, str]]] = {
    "A_serial_single_signal": {
        "label": "A. 単一 signal の逐次探索（今までの方法）",
        "info_gain": "低（1 本あたり seen の検出力 0.1–0.3）",
        "power": "低",
        "overfit_risk": "高（試行の数が増えるほど偽陽性が増え、seen span も減る）",
        "data_need": "中（無料 data は大半を使った）",
        "time": "選別に 1 本 1 cycle、確認に forward 3 年以上",
        "engineering_cost": "中",
        "forward_consumption": "候補ごとに消費",
        "broker_paid_need": "retail の判断には financing が要る（研究段階は近似で可）",
        "five_pct_relevance": "低（単体で TC-net 0.5–0.77 が要る）",
        "route_to_decision_bearing_result": _ROUTE_THROUGH_FORWARD,
    },
    "B_family_level_prereg": {
        "label": "B. family 単位の事前登録（1 family = 1 統計量）",
        "info_gain": "中（family 共通の効果があるかを 1 回で答える）",
        "power": "中（family 共通の効果があるときだけ。K 本の平均で必要年数が (1+(K−1)ρ)/K 倍）",
        "overfit_risk": "低（best-of-N を禁じる）",
        "data_need": "新しい source か保護 data（seen の再利用は結果を知った後なので D tier まで）",
        "time": "選別に 1–2 cycle、確認に forward 3 年以上",
        "engineering_cost": "中",
        "forward_consumption": "family で 1 回",
        "broker_paid_need": "retail の判断には financing が要る（研究段階は近似で可）",
        "five_pct_relevance": "中〜低（family 共通の効果が真にあり、それが TC-net 0.5 超のときだけ）",
        "route_to_decision_bearing_result": _ROUTE_THROUGH_FORWARD,
    },
    "C_fixed_multi_source_composite": {
        "label": "C. 事前固定の多 source 合成（等ウェイト・等リスク）",
        "info_gain": "中（弱い source の和に意味があるかを 1 回で）",
        "power": "中（真の source が N 本あれば √N。cost 後の s が 0 の source は足しても 0）",
        "overfit_risk": "中（どの source を入れるかが結果を見た後だと selection になる）",
        "data_need": "既存 source で組めるが、seen で結果を知っている source の合成は tier D",
        "time": "選別に 1 cycle、確認に forward 3 年以上",
        "engineering_cost": "中",
        "forward_consumption": "1 回",
        "broker_paid_need": "retail の判断には financing が要る（研究段階は近似で可）",
        "five_pct_relevance": (
            "低（cost 後の真の s = 0.2 の独立な source が ρ = 0.1 で 15 本、s = 0.1 なら ρ = 0.1 では上限 0.32 で届かない。"
            "programme の推定 s は約 0.07）"
        ),
        "route_to_decision_bearing_result": _ROUTE_THROUGH_FORWARD,
    },
    "D_wait_for_forward": {
        "label": "D. forward を待つ",
        "info_gain": "低（36 か月でも Sharpe の SE 0.58）",
        "power": "非常に低",
        "overfit_risk": "なし",
        "data_need": "なし",
        "time": "3 年以上",
        "engineering_cost": "低",
        "forward_consumption": "消費する",
        "broker_paid_need": "retail の判断には financing が要る",
        "five_pct_relevance": "低（確かめる候補が無い）",
        "route_to_decision_bearing_result": "forward そのもの。ただし確かめる候補が今は無い",
    },
    "E_hold_or_end": {
        "label": "E. 保留・終了",
        "info_gain": "なし",
        "power": "—",
        "overfit_risk": "なし",
        "data_need": "なし",
        "time": "—",
        "engineering_cost": "なし",
        "forward_consumption": "保存",
        "broker_paid_need": "不要",
        "five_pct_relevance": "なし",
        "route_to_decision_bearing_result": "なし（保護 data は保存される）",
    },
}


__all__ = [
    "BROKER_AUTH_TRIGGER",
    "BROKER_TRIGGER_LIMITATION",
    "CLOSED",
    "CLOSURE_PRINCIPLE",
    "CONSERVATIVE_MARKUP_PCT",
    "CONTINUE_CONDITIONS",
    "D_M3_TOKEN",
    "FINANCING_DRAG_SHARPE_PER_1PCT_MARKUP_REFERENCE",
    "FORWARD_ELIGIBILITY_CONDITIONS",
    "OPEN",
    "PAID_DATA_TRIGGER",
    "PAID_DATA_TRIGGER_EVALUATION",
    "PATH_COMPARISON",
    "PAUSE_POLICY",
    "PROTECTED_INFORMATION_LEDGER",
    "STOP_CONDITIONS",
    "broker_auth_trigger",
    "forward_eligibility",
]
