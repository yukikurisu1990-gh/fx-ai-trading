# ruff: noqa: E501 -- verdict prose
"""5 本の最終 status。**凍結した語彙で、凍結した判定規則に照らして決める。**

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

裁定 §32 は negative を 5 つに分けることを求めている。「failed」で一括りにすると、
次に何をすればよいかが分からなくなるからである — signal が無いのか、cost で消えたのか、
data が足りないのか、1 通貨に依存しているのか、評価の作り方が悪いのかは、別の問題である。

数値は `artifacts/research/top_five/development.json` と
`artifacts/research/top_five/stage2_t5.json` の実測値である。**どちらも
`prereg.POST_EXECUTION_CORRECTIONS` の 3 件を入れた後の値**であり、
「凍結どおりに 1 回走らせた結果」ではない。その差は上記 record が持つ。
"""

from __future__ import annotations

from typing import Any, Final

from scripts.research.top_five import prereg

#: 5 本すべてに等しくかかる留保。**track ごとの理由文へ書くと、読む人が
#: 「その track に固有の弱点」と誤読する。** 共通のものは共通の場所へ置く。
SHARED_CAVEATS: Final[dict[str, str]] = {
    "carry_leg_absent_on_both_spans": (
        "**panel は両 span とも spot only で、carry leg を持たない。** 凍結文の "
        "`EXCESS_PANEL['disclosure']` は長 span と T3 / T5 だけを名指ししていたが、"
        "実際に組まれた panel の provenance は `CARRY_LEG_ABSENT_ON_BOTH_SPANS_SPOT_ONLY` "
        "である。**凍結時の開示が実物より狭かった**ので、ここで広げて記録する。"
        "影響は track ごとに違う — T1（金利差を経由する risk repricing）と "
        "T3（sovereign curve）は carry と機構的に重なるので**最も強く効き**、"
        "T2（交易条件）と T4（通貨間伝播）は間接的、T5（資本フロー）は最も薄い。"
        "carry を後から足すことはしない（凍結の外だからである）"
    ),
    "seen_development_only": (
        "両 span とも `EXPLORATORY_SEEN_DEVELOPMENT_DATA` である。**どの status も "
        "confirmation ではない。** fresh pool / historical OOS / dead window / "
        "forward epoch は本 cycle で一度も読んでいない"
    ),
    "vocabulary_gap": (
        "凍結した `TRACK_STATUS_SUFFIXES` には **『正だが、この検出力では確認できない』**を"
        "表す token が無い。結果を見た後に語彙を足すのは post-hoc なのでしない。"
        "そのため T5 には `MARGINAL_DEVELOPMENT_CANDIDATE` を当てるが、"
        "**これは「証拠がある」という意味ではない** — 下の `why_marginal_is_not_evidence` を読むこと"
    ),
}

#: 各 track の最終 status と、その根拠。
VERDICTS: Final[dict[str, dict[str, Any]]] = {
    "T1": {
        "status": prereg.track_status("T1", "NOT_SUPPORTED_IN_SEEN_DEVELOPMENT"),
        "failure_class": "COST_FAILURE",
        "why": (
            "**gross は両 span で正**（長 +0.139 / 近 +0.336）だが、net は両方とも負"
            "（−0.435 / −0.500）。incremental IC も +0.0131 / +0.0066 で正である。"
            "turnover は単位 gross あたり 54.2 / 52.4 RT/年で、凍結した補正値 82.5 の**範囲内**"
            "である — 想定外に売買しすぎたのではない。"
            "凍結した cost 規約から予想される drag は約 0.77 Sharpe 単位で、"
            "**gross の +0.34 はそれを賄えない**。つまり『費用が想定を超えた』のではなく、"
            "**『情報の大きさが、想定どおりの費用に届かない』**のである"
        ),
        "how_much_information": (
            "**「情報は確かにある」とまでは書かない。** incremental IC +0.0066（近）は"
            "日次 cross-section 相関の平均が 0.7% ということであり、"
            "この panel の日次 IC のばらつきに対して**別個に有意だとは検定していない**。"
            "言えるのは『符号は 2 span で一致して正だった』ところまでで、"
            "それ自体は 2 回の観測である"
        ),
    },
    "T2": {
        "status": prereg.track_status("T2", "NOT_SUPPORTED_IN_SEEN_DEVELOPMENT"),
        "failure_class": "SIGNAL_FAILURE（長 span）/ COST_FAILURE（近 span）",
        "why": (
            "長 span は **gross からして負**（−0.354、incremental IC −0.0027）で、"
            "原油と通貨の交易条件という機構が 17 年の panel では支持されない。"
            "近 span は gross +0.519 と正だが net −0.253。turnover は単位 gross あたり "
            "42.3 / 50.4 RT/年で凍結範囲内なので、ここでも**費用は想定どおり**であり、"
            "gross がそれに届かない。"
            "**2 つの span で失敗の種類が違う**ので、まとめて『failed』とは書かない"
        ),
        "incremental_over_t1": (
            "**凍結が名指しで要求した cross-track control の結果を、ここで報告する。** "
            "T2 の beta は T1 の beta と +0.856 相関しているので、"
            "『FX 自身の価格を超える増分』だけでは足りず、**T1 を超える増分**を測る必要があった。"
            "実測は長 span **−0.0115**、近 span **−0.0019** で、**どちらも負**である。"
            "すなわち T2 は、T1 が既に持っている情報に対して**何も足していない**。"
            "近 span の gross が正だったことは、T2 固有の機構の証拠ではない"
        ),
    },
    "T3": {
        "status": prereg.track_status("T3", "NOT_SUPPORTED_IN_SEEN_DEVELOPMENT"),
        "long_span_status": prereg.track_status("T3", "DATA_NOT_DECISION_GRADE"),
        "failure_class": "DATA_FAILURE（長 span）/ COST_FAILURE（近 span）",
        "why": (
            "**長 span は data が足りない。** 10y は 5 通貨とも揃うが、**2y leg が揃わない** — "
            "USD 2y は 2020 年開始、GBP 2y は 2016 年開始で、1999-2016 に組めるのは "
            "EUR / CHF / CAD の 3 通貨だけ（中央値 3）。連続する decision day が 60 日に"
            "満たず DATA_NOT_DECISION_GRADE とした。"
            "近 span は 5 通貨で組めるが、**H1 と H2 は定義上の鏡像**（PnL 相関 −0.993）で、"
            "H1 gross −0.749 / H2 gross +0.749。net は H1 **−1.638** / H2 **−0.148** で"
            "**どちらも負**である。"
            "**5 本で唯一、凍結した turnover 想定を超えた track**でもある"
            "（単位 gross あたり 57.9 対 補正値 34.8、1.66 倍）"
        ),
        "sign_multiplicity": (
            "**どちらかが positive だったから curve theory が支持された、とは言えない。** "
            "H2 の gross が正なのは H1 の gross が負であることと同じ 1 つの事実であり"
            "（相関 −0.993 は定義上の鏡像）、2 通りの探索のうち片方を選んで報告することを"
            "凍結が禁じている。**net はどちらも負**なので、そもそも選ぶ対象が無い。"
            "裁定が要求したとおり、**両方の符号を事前登録し、両方を報告した**"
        ),
        "carry_interaction": (
            "T3 は SHARED_CAVEATS の carry 欠落が**最も強く効く** track である。"
            "金利の形を signal にしながら、金利 carry を落とした panel の上で測っている。"
            "この留保は net が両符号とも負であることを救わないが、"
            "**次に carry leg を入れて組み直す価値がある唯一の track**ではある"
        ),
    },
    "T4": {
        "status": prereg.track_status("T4", "NOT_SUPPORTED_IN_SEEN_DEVELOPMENT"),
        "failure_class": "SIGNAL_FAILURE + COST_FAILURE",
        "why": (
            "近 span は **gross も負**（−0.409、incremental IC −0.0289）。長 span は "
            "gross +0.258 だが net −1.435、近 span は −2.890。turnover は単位 gross あたり "
            "153.3 / 153.5 RT/年で、凍結補正値 191.5 の範囲内ではあるが**絶対水準が桁違いに高い** — "
            "1 日 signal なので当然である。"
            "**5 本で最悪の net** であり、これは実行前に予想されていた — 凍結文が"
            "「gate を通っても cost で落ちる公算が高い」と書いている。"
            "rename gate は通った（自通貨 lag-1 残差との相関は閾値 0.8 未満）ので、"
            "**H-003 / Track 1 の言い換えではない**が、別物であることは役に立たなかった"
        ),
    },
    "T5": {
        "status": prereg.track_status("T5", "MARGINAL_DEVELOPMENT_CANDIDATE"),
        "failure_class": "UNDERPOWERED_FOR_CONFIRMATORY_CLAIM_NOT_A_NEGATIVE_CLASS",
        "why": (
            "**5 本で唯一 net が正。** 近 span（2021-04-28 … 2023-06-14、555 日 = 2.20 年）で "
            "gross +0.891 / net **+0.838** / 年 net **+8.57%**、maxDD −9.8%。"
            "turnover は単位 gross あたり 6.4 RT/年で**5 本中最小**（次点 T2 の 1/7）、"
            "cost を 2 倍にしても net Sharpe +0.784 とほぼ動かない。"
            "incremental IC +0.0255 は 5 本で最大。"
            "rename gate も通った（horizon を揃えた 1/6/12 か月 x 1/2/3 か月ラグの "
            "USD basket return との相関は最悪でも 0.398、閾値 0.8）ので、"
            "**遅れた USD momentum の言い換えではない**"
        ),
        "why_marginal_is_not_evidence": (
            "**この +0.838 は、同じ形をした零情報 signal が出す値と区別がつかない。** "
            "`stage2_t5.json` の permutation（T5 の score を circular shift し、"
            "自己相関を保ったまま return との対応だけ壊す、500 回）が示すのは次の 3 つである。"
            "**(a) 凍結した Stage 2 の 3 条件は、帰無のもとでも 42% 通る。** "
            "裁定の `multiplicity_note` が添えろと言っていた数字がこれで、"
            "T5 は 5 本で最も turnover が低いぶん最も通りやすい。**gate を通った事実に情報は薄い。** "
            "**(b) 回帰の signal 係数は t = +0.94 で、permutation p = 0.314。** "
            "しかもこの t は月次値の前方補完による重複を補正していないので**過大**である。"
            "**(c) 零情報 null の net Sharpe は 95 パーセンタイルで +1.13** に達し、"
            "実測 +0.838 はその内側に収まる"
        ),
        "why_it_is_still_a_candidate": (
            "**それでも『開発に値しない』ではない**（裁定の "
            "`UNDERPOWERED_FOR_CONFIRMATORY_CLAIM != NOT_WORTH_DEVELOPING`）。"
            "残す理由は測れた Sharpe ではなく、**Sharpe と独立に成り立つ構造**である — "
            "(1) turnover が 5 本で最小で、cost 2 倍でも崩れない（他の 4 本を殺したのは cost であり、"
            "T5 はその失敗様式に対して構造的に強い）、"
            "(2) incremental IC が 5 本で最大、"
            "(3) 情報源が価格に対して外生（他 track と PnL 相関 |r| ≤ 0.073）、"
            "(4) nuisance 定数をどこへ動かしても**符号は正のまま**で、"
            "価格のみの mean-reversion book を**全点で上回る**。"
            "確認できないのは、この span に**検出力が無い**からであって、"
            "効果が無いと示されたからではない"
        ),
        "what_would_settle_it": (
            "本 cycle では**やらない**（すべて未承認）。記録のみ: "
            "TIC は 2023-01 で止まっているので、まず **data の延長**が要る。"
            "そのうえで 555 日・24 状態という標本を増やすには、"
            "**保護 pool か forward epoch のどちらか**を開けるしかない。"
            "どちらも Red gate であり、本 cycle の権限の外である"
        ),
        "the_qualifications_in_numbers": (
            "**(1) 検出力の高い方の span が平坦。** 長 span は 4,331 日（17.2 年、近 span の 7.8 倍）で "
            "gross +0.037 / net **−0.017** — ほぼゼロ。"
            "**(2) breadth が 1。** USD を抜くと net Sharpe が +0.838 から **+0.059** へ落ちる。"
            "通貨別寄与でも USD が gross PnL の **91%** を占める。事実上 1 通貨の結果である。"
            "**(3) 独立な状態が 24 個しかない。** score は月次 TIC の前方補完なので、"
            "555 日という日数は独立標本数ではない。SR の t 値は √2.20 を掛けて **1.24**。"
            "**(4) 集中が重い。** 上位 5 日が net の **41%**、上位 10 日で **80%**。"
            "temporal block は 9 分割中 6 が正。"
            "**(5) 価格のみの baseline との差が小さい。** 同じ 555 日で 20 日 mean reversion book が "
            "net **+0.487**（gross +0.846 は T5 の +0.891 とほぼ同じ）を出す。"
            "T5 の優位は **turnover が 1/5 で cost を払わない**ところから来ており、"
            "**gross の情報量の差ではない**。"
            "**(6) 零情報 null との差。** 定数 long-USD book（signal を一切見ない）が net +0.260 で、"
            "増分は +0.578。ただし (7) の幅を見ること。"
            "**(7) nuisance 定数に敏感。** `max_staleness_days` は経済的内容を持たない事務上の"
            "上限だが、45-400 日で net Sharpe が **+0.557 … +0.838**、null 超過分が "
            "**+0.116 … +0.595** と動く。**凍結値 75 は試した 9 点で net Sharpe 第 1 位**、"
            "すなわち報告値は楽観側の端である。"
            "**(8) data が 2023-01 で終わる。** vintage 2 か月を足すと使用可能域は 2023-06 まで"
        ),
    },
}

#: 全 track に共通して出た engineering の発見（裁定 §40）。
#: **これは alpha verdict を救うためのものではない。** 分離して記録する。
ENGINEERING_FINDING: Final[dict[str, Any]] = {
    "id": "E-002",
    "status": "TURNOVER_MUST_BE_COMPARED_PER_UNIT_GROSS_NOT_IN_LEVERED_UNITS",
    "finding": (
        "**これは最初、別の（誤った）発見として記録されていた。** 初稿は「実測 turnover が "
        "band law を全 track で 1.7-7.8 倍上回った」と書いていたが、それは**単位の取り違え**"
        "だった。実行層の `one_way_traded` は **leverage 適用後**の建玉変化であり、"
        "band law の turnover は **gross 1 単位あたり**の定義である。この book の平均 "
        "portfolio gross は 2.5-5.4 なので、生の値をそのまま比べると leverage 倍だけ過大に見える。"
        "単位を揃えると T1 54.2 / T2 42.3-50.4 / T4 153.3-153.5 / T5 6.0-6.4 でいずれも**凍結範囲内**、"
        "**超過は T3 の 57.9 対 34.8（1.66 倍）だけ**である"
    ),
    "how_it_was_caught": (
        "band law が 18.3 とする 20 日 momentum book を同じ実行層に通したところ "
        "134.4 RT/年 と出た。7.3 倍という比は、どの score 型にも共通する構造を疑わせる値で、"
        "そこで平均 gross が 4.5 であることに気づいた"
    ),
    "why_it_matters": (
        "**cost 自体は正しく課金されている** — `charged_cost` は実際の建玉変化に課すので、"
        "net Sharpe も verdict も影響を受けない。誤っていたのは**比較の単位**だけである。"
        "ただし turnover を凍結値と突き合わせる規則は本 cycle の判定規則の 1 つなので、"
        "誤ったまま放置すれば 4 本を誤った理由で COST_FAILURE と呼ぶところだった"
    ),
    "not_a_rescue": (
        "**この訂正で verdict は 1 つも変わらない。** T1 / T2 / T4 の net は依然として負で、"
        "変わったのは『費用が想定を超えた』から『情報が想定どおりの費用に届かない』への"
        "**理由の書き換え**である。後者の方が、次に何を変えるべきかをより正しく示す"
    ),
    "carried_forward": (
        "次の cycle では、turnover を報告する箇所で **必ず単位を明記する**。"
        "`turnover_per_unit_gross` を metric に追加した"
    ),
}

#: 本 cycle で**方法そのもの**について分かったこと。verdict とは別に残す。
METHOD_FINDING: Final[dict[str, Any]] = {
    "id": "M-001",
    "status": "A_PREREGISTERED_GATE_WITHOUT_ITS_NULL_PASS_RATE_IS_NOT_A_TEST",
    "finding": (
        "凍結した Stage 2 の 3 条件（gross > 0 / incremental IC > 0 / net > 0）は、"
        "**帰無のもとで 42% 通る**。T5 がこれを通って Stage 2 へ自動進行したことは、"
        "設計上『何かを示した』ように読めるが、実際にはコイン投げ 1.25 回分の情報しかない。"
        "裁定の `multiplicity_note` は最初からこの数字を添えることを要求していた"
    ),
    "why_it_generalises": (
        "**通過率は track ごとに違い、turnover が低いほど高くなる。** net > 0 という条件は "
        "cost drag を超えることを要求するが、T5 の drag は年 0.5% 程度しかないので、"
        "gross がわずかでも正なら通ってしまう。T4（drag が桁違い）なら同じ条件はほぼ通らない。"
        "**同じ規則が、track によって全く違う厳しさで効く**"
    ),
    "carried_forward": (
        "次の cycle では、gate を凍結する時点で**各 track の帰無通過率を計算して一緒に凍結する**。"
        "通過率が 20% を超える gate は、gate ではなく足切りとして扱う"
    ),
}

#: 複数 source の合成は本 cycle では行わない（裁定 §39）。
MULTI_SOURCE: Final[str] = (
    "cross-track PnL 相関はすべて |r| ≤ 0.073（T3 の H1/H2 は定義上の鏡像 −0.993 を除く）。"
    "**独立性は高いが、合成する対象が無い** — net 正は T5 の 1 本だけで、それも"
    "零情報 null と区別がついていない。portfolio 化は次フェーズの prereg 対象であり、"
    "本 cycle では行わない（post-hoc multi-source portfolio optimization は未承認）"
)


def summary() -> dict[str, Any]:
    return {
        "verdicts": {track: row["status"] for track, row in VERDICTS.items()},
        "net_positive": [
            t for t, r in VERDICTS.items() if "MARGINAL" in r["status"] or "STRONG" in r["status"]
        ],
        "confirmed": [],
        "engineering": ENGINEERING_FINDING["status"],
        "method": METHOD_FINDING["status"],
        "multi_source": MULTI_SOURCE,
        "shared_caveats": sorted(SHARED_CAVEATS),
    }


__all__ = [
    "ENGINEERING_FINDING",
    "METHOD_FINDING",
    "MULTI_SOURCE",
    "SHARED_CAVEATS",
    "VERDICTS",
    "summary",
]
