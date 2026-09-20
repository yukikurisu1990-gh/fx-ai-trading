# ruff: noqa: E501 -- verdict prose
"""5 本の最終 status。**凍結した語彙で、凍結した判定規則に照らして決める。**

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

裁定 §32 は negative を 5 つに分けることを求めている。「failed」で一括りにすると、
次に何をすればよいかが分からなくなるからである — signal が無いのか、cost で消えたのか、
data が足りないのか、1 通貨に依存しているのか、評価の作り方が悪いのかは、別の問題である。
"""

from __future__ import annotations

from typing import Any, Final

from scripts.research.top_five import prereg

#: 各 track の最終 status と、その根拠。数値は
#: `artifacts/research/top_five/development.json` の実測値である。
VERDICTS: Final[dict[str, dict[str, Any]]] = {
    "T1": {
        "status": prereg.track_status("T1", "NOT_SUPPORTED_IN_SEEN_DEVELOPMENT"),
        "failure_class": "COST_FAILURE",
        "why": (
            "**gross は両 span で正**（長 +0.139 / 近 +0.336）だが、net は両方とも負"
            "（−0.435 / −0.500）。実測 turnover は 191 / 284 RT/年で、凍結した補正値 82.5 を"
            "2.3-3.4 倍超える。**情報が無いのではなく、その情報を取りに行く費用が上回る。**"
            "incremental IC は +0.0131 / +0.0066 で正であり、FX 自身の価格情報を超える分は"
            "わずかにあるが、cost を賄う水準ではない"
        ),
    },
    "T2": {
        "status": prereg.track_status("T2", "NOT_SUPPORTED_IN_SEEN_DEVELOPMENT"),
        "failure_class": "SIGNAL_FAILURE（長 span）/ COST_FAILURE（近 span）",
        "why": (
            "長 span は **gross からして負**（−0.354、incremental IC −0.0027）で、"
            "原油と通貨の交易条件という機構が 17 年の panel では支持されない。"
            "近 span は gross +0.519 と正だが turnover 248 RT/年で net −0.253。"
            "**2 つの span で失敗の種類が違う**ので、まとめて『failed』とは書かない"
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
            "H1 gross −0.622 / H2 gross +0.622。net は H1 −1.487 / H2 −0.247 で**どちらも負**"
        ),
        "sign_multiplicity": (
            "**どちらかが positive だったから curve theory が支持された、とは言えない。** "
            "H2 の gross が正なのは H1 の gross が負であることと同じ 1 つの事実であり、"
            "2 通りの探索のうち片方を選んで報告することを凍結が禁じている。"
            "**net はどちらも負**なので、そもそも選ぶ対象が無い"
        ),
    },
    "T4": {
        "status": prereg.track_status("T4", "NOT_SUPPORTED_IN_SEEN_DEVELOPMENT"),
        "failure_class": "SIGNAL_FAILURE + COST_FAILURE",
        "why": (
            "近 span は **gross も負**（−0.409、incremental IC −0.0289）。長 span は "
            "gross +0.258 だが turnover 538 RT/年で net −1.435、近 span は 760 RT/年で −2.890。"
            "**5 本で最悪の net** であり、これは実行前に予想されていた — 凍結文が"
            "「gate を通っても cost で落ちる公算が高い」と書いている。"
            "rename gate は通った（自通貨 lag-1 残差との相関は閾値 0.8 未満）ので、"
            "**H-003 / Track 1 の言い換えではない**が、別物であることは役に立たなかった"
        ),
    },
    "T5": {
        "status": prereg.track_status("T5", "MARGINAL_DEVELOPMENT_CANDIDATE"),
        "failure_class": "該当なし（net 正）。ただし下記の留保がすべて効く",
        "why": (
            "**5 本で唯一 net が正**。近 span で gross +0.726 / net +0.672 / 年 net +6.85%、"
            "turnover 16.1 RT/年と最小、cost を 2 倍にしても net Sharpe 0.618 で崩れない。"
            "rename gate も通った（1/2/3 か月ラグの USD basket return との相関 0.096）ので、"
            "**2 か月遅れの USD momentum ではない**"
        ),
        "why_only_marginal": (
            "**(1) 検出力の高い方の span が平坦である。** 長 span は 4,331 日（17.2 年）で "
            "gross +0.037 / net −0.017 — ほぼゼロ。近 span の 548 日（2.17 年）の 8 倍の標本が"
            "何も示さない。"
            "**(2) 事前登録した Stage 2 が null。** 3 条件を満たしたので自動進行し、"
            "2 変数線形回帰を走らせたところ signal 係数は t = +0.72（観測 4,232、R² 0.0008）。"
            "観測単位の予測力としては測れない。"
            "**(3) breadth が 1。** USD を抜くと net Sharpe が +0.67 から **−0.12** へ落ちる。"
            "結果は事実上 1 通貨である。"
            "**(4) 集中が重い。** 上位 5 日が net の **52%**。"
            "**(5) 価格のみの baseline に僅差。** 同じ 548 日で 20 日 mean reversion book が "
            "net Sharpe +0.550 を出す。外部データを一切使わない baseline との差は +0.12 しかない。"
            "**(6) data が 2023-01 で終わる。** vintage 2 か月を足すと近 span の使用可能域は "
            "2021-04 から 2023-06 までしかない"
        ),
    },
}

#: 全 track に共通して出た engineering の発見（裁定 §40）。
#: **これは alpha verdict を救うためのものではない。** 分離して記録する。
ENGINEERING_FINDING: Final[dict[str, Any]] = {
    "id": "E-002",
    "status": "EXECUTION_LAYER_TURNOVER_EXCEEDS_THE_BAND_LAW_FOR_EVERY_SCORE_TYPE_TESTED",
    "finding": (
        "5 本すべてで、実測 turnover が凍結した補正値（band law × 1.90）を上回った: "
        "T1 284 対 82.5、T2 248 対 82.5、T3 270 対 34.8、T4 760 対 191.5、T5 16.1 対 9.7。"
        "**超過率は 1.7 倍から 4.0 倍**で、score の作り方に依らず起きている"
    ),
    "why_it_matters": (
        "band law は『forecast が lookback どおりに減衰する』前提で turnover を出す。"
        "5 日差分の z-score も cross-section rank も月次 z も、その前提を満たさない。"
        "**turnover の見積もりが構造的に低い**ということであり、cost を軸に判定してきた"
        "本 programme の過去の feasibility 計算すべてに関わる"
    ),
    "not_a_rescue": (
        "**この発見で今回の verdict を救わない。** band を広げれば T1 / T2 の net は改善しうるが、"
        "それは結果を見た後の band optimization であり、凍結が明示的に禁じている。"
        "次の cycle で **事前に**決めるべき設計事項として記録する"
    ),
    "when_it_may_be_worked_on": (
        "positive な economics を持つ candidate が、この床に実際に阻まれていると分かったとき"
    ),
}

#: 複数 source の合成は本 cycle では行わない（裁定 §39）。
MULTI_SOURCE: Final[str] = (
    "cross-track PnL 相関はすべて |corr| < 0.08（T3 の H1/H2 は定義上の鏡像 −0.993 を除く）。"
    "**独立性は高いが、合成する対象が無い** — net 正は T5 の 1 本だけで、それも marginal である。"
    "portfolio 化は次フェーズの prereg 対象であり、本 cycle では行わない"
)


def summary() -> dict[str, Any]:
    return {
        "verdicts": {track: row["status"] for track, row in VERDICTS.items()},
        "net_positive": [
            t for t, r in VERDICTS.items() if "MARGINAL" in r["status"] or "STRONG" in r["status"]
        ],
        "engineering": ENGINEERING_FINDING["status"],
        "multi_source": MULTI_SOURCE,
    }


__all__ = ["ENGINEERING_FINDING", "MULTI_SOURCE", "VERDICTS", "summary"]
