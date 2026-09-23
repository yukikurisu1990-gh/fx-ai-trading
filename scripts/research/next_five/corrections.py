# ruff: noqa: E501 -- correction prose
"""**alpha を 1 回見た後**に見つかった共通基盤の誤りと、その修正（2026-09-22 第 2 裁定 §40）。

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

凍結（`prereg.freeze_digest()` = `0bc7b198…`、freeze commit `84d7832`）は **書き換えない**。
ここにあるのは、実装が凍結文と食い違っていた箇所を **凍結文へ戻す** 修正である。
どれも signal の符号・horizon・benchmark・universe・portfolio・feature・target・threshold・
cost を動かさない。**裁量が入ったもの（C-5 の読み、C-6 の fail-closed）は、その旨と根拠を
各項に書いてある。** 裁量の無い修正だとは主張しない。

修正の初版（commit 1e9d34e）は、独立の再監査で BLOCKER 3 件を出した（U2 / U4 が KeyError で
落ちる、C-2 が `_align` の ffill と組んで 2016 年の変化値を約 1 年運ぶ、C-1 と run_book の
連続性要件の衝突）。その版で始めた実行は **どの track も終わる前に止め、途中の出力は
見ていない**。

**これは 2 回目の alpha 測定である。** 裁定 §40 は共通基盤の date / leakage / acquisition bug を
「止めて直し、実行済みの track を監査し、都合よく結果を保持しない」と定めている。
1 回目（`development_run2.json`）の結果は **全 track で INVALID** として残し、
2 回目の結果が 1 回目より良くても悪くても、2 回目を記録として採る。
1 回目で 5 本とも `NOT_SUPPORTED` だったことは、この修正の動機ではない（修正は 2 つの
独立 review role の指摘に従っており、どちらの role も結果の方向を指定していない）。
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Final

#: 修正後の lag（凍結した series_map の値を上書きするのではなく、ここから読む）。
LAG_CORRECTIONS: Final[dict[tuple[str, str], dict[str, Any]]] = {
    #: H.4.1 は水曜 level を翌木曜 16:30 ET に公表する。凍結文は「公表日の 2 営業日後」
    ("U2", "USD"): {"kind": "business_days", "n": 3},
    #: ECB 週次財務諸表は金曜日付で翌火曜 15:00 CET に公表する。+2 営業日は公表日そのもので、
    #: long span の return（ECB 参照レート 14:15 CET の fix-to-fix）より公表が後だった
    ("U2", "EUR"): {"kind": "business_days", "n": 4},
}

POST_ALPHA_CORRECTIONS: Final[dict[str, dict[str, Any]]] = {
    "C-1": {
        "found_by": "Role 1（経済）R-1 / Role 2（来歴）R-1 — 独立に同じ指摘",
        "where": "signals.scores_for",
        "was": "decision day の窓へ reindex した後、上限なく ffill していた",
        "frozen_text_restored": "`max_staleness_days` の staleness 規則、P-6『欠けた通貨は 0』",
        "effect_seen": "U1 recent の EUR（系列は 2022-12 終了）の最終 score を 685 営業日（暦日 959 日、2023-05-12 … 2025-12-26）持ち越していた。"
        "U3 の感度（staleness 45）では 3 通貨未満の日が 165 日 book に入っていた",
        "tracks": ("U1", "U2", "U3", "U4", "U5"),
    },
    "C-2": {
        "found_by": "Role 1 R-2 / Role 2 B-1 — 独立に同じ指摘",
        "where": "signals._change",
        "was": "n か月前の基準値を上限なく ffill で拾っていた",
        "frozen_text_restored": "『12 か月変化』『3 か月変化』。基準値にも staleness 規則を当てる",
        "effect_seen": "recent span の最初の 12 か月、基準値が 2016-06 の観測だった（約 5 年変化）。"
        "balance_sheet_usd の 2021-04-28 の値は 0.556、平時の |変化| は 0.091",
        "addendum": "初版の修正は `_change` が欠損行を返し、`_align` がその欠損行を観測日として "
        "staleness を通しつつ 2016 年の値を ffill で運んだ（U1 USD の z が −15.8）。"
        "`_align` の入口で欠損行を落とす。1 回目の実行と比べ、recent span の開始は U1 / U2 で約 1 年（2022-01-24 → 2023-01-23）、U4 で約 3 か月（2021-12-22 → 2022-03-24）遅くなる",
        "discretion": "**判断である。** 基準値の鮮度を `max_staleness_days` と同じ定数で測るのは凍結文に無い選択で、『n か月前の観測が存在すること』を要求する案もありえた。実データでは月次の age はほぼ 0、週次は 7 日以下で、効くのは保護期間の空白を跨ぐ箇所だけである",
        "side_effect": "`max_staleness_days` の感度点は、基準値と整列の 2 箇所に同時に効く",
        "tracks": ("U1", "U2", "U4"),
    },
    "C-3": {
        "found_by": "Role 1 R-3 / Role 2 R-3 — 独立に同じ指摘",
        "where": "signals._align（month_end_offset）",
        "was": "月末に `DateOffset(months=k)` を足しており、2 月末 + 2 か月 = 4 月 28 日など 1〜3 日早く着地",
        "frozen_text_restored": "『第 m 月の値は m+k 月末以降にのみ使用する』",
        "tracks": ("U1", "U2", "U4"),
    },
    "C-4": {
        "found_by": "Role 2 B-1（保護データ）",
        "where": "signals._load（monthly=True）",
        "was": "取得層は stamp の日付で seen を判定しており、2016-06-01 stamp（参照期間 2016 年 6 月 = fresh pool）"
        "と 2025-12-01 stamp（参照期間が forward epoch に掛かる）が保存され、前者が C-2 経由で計算に入っていた",
        "frozen_text_restored": "fresh pool と forward epoch は schema 確認にも使わない（第 2 裁定 §2–§4）",
        "note": "parquet は書き換えない（committed provenance の暗黙 overwrite 禁止）。読む経路で落とす",
        "tracks": ("U1", "U2", "U4"),
    },
    "C-5": {
        "found_by": "Role 2 R-2",
        "where": "signals._lag_kwargs（U2 USD / EUR）",
        "was": "週次 series を『観測日の 2 営業日後』から使っていた",
        "frozen_text_restored": "TRACKS['U2']['publication_lag'] = 『公表日の 2 営業日後から使用』",
        "discretion": "**凍結文の内部矛盾を、厳しい側の読みで解いた。** series_map（観測日 +2）と "
        "FREEZE_AMENDMENT_PLUMBING P-2（『週次は 2 営業日後』）は観測日基準と読め、TRACKS は公表日基準である。"
        "CLAUDE.md『研究制限は厳しい読みが勝つ』に従い TRACKS を採った。凍結 digest の中の series_map の値は"
        "書き換えず、ここから読む側で上書きしている",
        "residual": "`BDay` は祝日を知らない。Thanksgiving・イースター・年末で公表が遅れた週は、"
        "公表日 + 2 営業日より早く使う可能性が残る（数は少ない）",
        "effect_seen": "ECB は公表日当日の 14:15 CET fix から return を取っており、公表（15:00 CET）より約 45 分先の情報",
        "tracks": ("U2",),
    },
    "C-6": {
        "found_by": "独立再監査 BLOCKER-3",
        "where": "signals.scores_for / execute.run_track / execute._nuisance_sensitivity",
        "was": "C-1 で ffill を外すと、3 通貨未満の日が span の途中から削られ、run_book が連続性違反で "
        "ValueError を出して track 全体が error になった（U3 の感度点 staleness 45（165 日）/ 60（2 日）と z_window 126（5 日）で起きる。z_window 126 は staleness ではなく、USD の tone が 2024-01-31 … 07-31 に本物の 0.0（h = d）で変化 0 が続き、126 日窓の sd が 0 → z が欠損になる経路で、旧版は ffill が古い z で埋めていた）",
        "fix": "途中で途切れたら `NonContiguousScoresError` で止め、primary なら DATA_NOT_DECISION_GRADE、"
        "感度点なら NOT_COMPUTABLE_NONCONTIGUOUS として記録する",
        "discretion": "**判断である。** 途切れた日を flat で残す・区間を分けるのどちらも凍結文に無いので、"
        "どちらも選ばず fail-closed にした。結果を作る選択肢を増やさない側",
        "tracks": ("U1", "U2", "U3", "U4", "U5"),
    },
}

#: 修正ではないが、1 回目の実行と 2 回目の実行の間でコードに入った変更。
NON_RESULT_CHANGES: Final[dict[str, str]] = {
    "N-1_PARALLEL_NULL": (
        "null 診断の circular shift を ProcessPool で並列に引く。shift の列は並列化の前に 1 本の乱数列から"
        "決めるので、worker 数によらず同じ draw になる"
    ),
    "N-2_CAPACITY_LABEL": (
        "`capacity.reachable` は『net Sharpe が正なので leverage 計算を出した』という意味だけで、"
        "実現可能性ではない。max_leverage で到達可否を判定する案は CAPACITY_REPORTING.forbidden に触れるので採らなかった"
    ),
    "N-3_PROVENANCE": "driver が HEAD・dirty path・argv・開始時刻を出力へ記録する",
    "N-4_MESSAGES": "『連続 decision day が N 日しかない』を『3 通貨以上の score がある decision day が N 日』へ直し、0 列のときは 0 行を返す",
}

#: 1 回目の実行記録の扱い。**消さない・上書きしない。**
INVALIDATED_RECORDS: Final[dict[str, str]] = {
    "artifacts/research/next_five/development_run2.json": (
        "INVALID_ALL_TRACKS_SUPERSEDED_BY_POST_ALPHA_CORRECTIONS_C1_C5 — 数値は何を実行したかの記録として"
        "残すが、結果ではない。U1/U2/U4 の recent span と `other_span_gross_sign` は保護期間の内容を含む"
    ),
}

#: 直せないので開示だけするもの（再取得は network を再び触るので行わない）。
DISCLOSURES: Final[dict[str, str]] = {
    "D-1_ACQUISITION_CODE_MTIME": (
        "取得（parquet 00:01–00:06）と Stage 0（00:07）の後に、acquire / fetch / mapping / statements / "
        "series_map / signals を編集してから 84d7832 に commit した。artefact は commit 版のコードで作られて"
        "いない。parquet 23 本の content hash は acquisition.json と一致する（Role 2 が確認）"
    ),
    "D-2_ACQUISITION_DIGEST": (
        "acquisition.json の freeze_digest f939b0… は最終凍結 0bc7b198… と違い、どの payload から出たか"
        "再構成できない。取得時点の凍結内容はこの digest からは立証できない"
    ),
    "D-3_LEXICON_ORDER": (
        "TONE_LEXICON が初めて commit されたのは 84d7832 で、tone parquet の作成より後である。"
        "『1 語も数える前に固定した』は git 履歴では立証できない（会話記録上は固定後に数えた）"
    ),
    "D-4_NO_SIGNAL_HAD_RUN_IS_FALSE": (
        "FINAL_EXECUTION_SET の MDE 値は実データで scores_for を回さないと出ない。"
        "`NO_SIGNAL_HAD_RUN` は誤りで、正しくは『return は使っていない（score の日数だけを数えた）』。"
        "return を使った証拠は無い"
    ),
    "D-5_FULL_SERIES_PARSED_IN_MEMORY": (
        "H.4.1 の zip、SNB cube、BoJ の全系列、Fed の ne-press.json は期間を request に入れられず、"
        "**fresh pool と 2026 年の行を含む応答をメモリに読み込んで parse し、保存前に切り落とした**。"
        "acquire.py の docstring は BoJ を期間指定と書いていたが誤りだった。"
        "保存物に保護期間の stamp は無い（Role 2 が 23 本で確認）が、C-4 の月次 stamp は残っていた。"
        "T-V の先例は『除外は request の性質』であり、これに届いていない — Human + ChatGPT 判断事項"
    ),
    "D-6_U3_JPY_WHOLE_PAGE": (
        "U3 の JPY は本文を抽出できず、38 文書すべてページ全体（navigation 等を含む、205–1714 語）で"
        "採点した。tone は (h−d)/語数なので定型文の分は差分で消えない。生 HTML を保存していないので"
        "再抽出には再取得が要り、行わない。U3 の JPY 成分は欠陥を持つ"
    ),
    "D-7_REVISION_AND_VALUATION": (
        "U1 と U4 は ALFRED の現行 vintage のみで、当時の公表値ではない（vintage 列・日付も未記録）。"
        "U4 の『Reserves Excluding Gold』は USD 建てで、為替の評価変動を含む。"
        "凍結した機構『積み増し = 自国通貨売り』と一致するとは限らない。"
        "U1 は季節調整済み（…M664S）の現行 vintage なので、季節調整の係数は保護期間を含む全標本から推定されている"
        "（暗黙の情報流入。大きさは測っていない）"
    ),
    "D-8_BREADTH_OVERSTATED": (
        "U1 の EUR は別定義（euro area 19 か国の goods net trade）で 2022-12 に終了。U4 の EUR は recent span "
        "の行が 0。U2 の EUR は構成国の変化で段差がある。U5 は 1 系列を beta で配っているので 3 通貨規則は形式上"
    ),
    "D-9_STAGE0_COVERAGE": (
        "Stage 0 は PROTECTED_DATA_REQUIREMENT / UNRECOVERABLE_TIMING_AMBIGUITY / NO_REPRODUCIBLE_PUBLIC_SOURCE "
        "を評価しておらず、C-2 も C-5 も検出しなかった。`returns_used: False` だが panel.build() は return を読む"
    ),
    "D-10_RECENT_BOUNDARY": (
        "recent span の最初の return（2021-04-27）は 2021-04-26 の close を使う。コードの is_seen は 04-26 を"
        "未見扱いにしているが、CLAUDE.md 上 2021-04-26 は seen（2021-04-26 … 2023-04-25）。保守側の不一致で、"
        "保護期間の読みではない"
    ),
    "D-11_U5_FIVE_OBSERVATIONS": (
        "U5 の『5 日変化』は `shift(5)`、つまり 5 観測である。日曜の観測 2025-11-30 が 1 つあり、2 営業日の lag を"
        "足すと 11-28 の値と同じ日に衝突する（後の値が残る）。影響は小さく、直していない"
    ),
}


def corrections_digest() -> str:
    payload = {
        "lag_corrections": {f"{t}/{c}": v for (t, c), v in LAG_CORRECTIONS.items()},
        "post_alpha_corrections": POST_ALPHA_CORRECTIONS,
        "non_result_changes": NON_RESULT_CHANGES,
        "invalidated_records": INVALIDATED_RECORDS,
        "disclosures": DISCLOSURES,
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()


__all__ = [
    "DISCLOSURES",
    "INVALIDATED_RECORDS",
    "LAG_CORRECTIONS",
    "NON_RESULT_CHANGES",
    "POST_ALPHA_CORRECTIONS",
    "corrections_digest",
]
