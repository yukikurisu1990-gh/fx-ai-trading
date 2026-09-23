# 次の 5 本（U1..U5）— 最終統合報告（2026-09-24）

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE` ·
`PRODUCTION_READINESS_NOT_CLAIMED`

2026-09-22 第 2 裁定（「仮説が失敗したのではない。取得経路が失敗した」）への最終報告。
数値の出典は `artifacts/research/next_five/development_run4.json`（sha256 `4146b33a…`）。

---

## Executive Summary

- **何をしたか**: 取得経路（provider 一次配信 → ALFRED）を作り直し、20 系列と中銀声明 3 系統を
  取得した。**Stage 0 を 5 本すべてで通過**し、凍結どおり U1..U5 を実行した。
- **何本測れたか**: **5 本とも primary span で測れた**。代替 track は使っていない。
- **positive candidate**: **無い**。primary span で net Sharpe が正の track は 0 本、
  null diagnostic で p ≤ 0.05 の track も 0 本（最小 p = 0.449）。
- **data blockage**: 5 本の実行を止めるものは残っていない。部分的な欠けは残る（U2 の GBP/AUD/NZD、
  U4 の CHF/NZD、U5 の long span は license で存在しない、U3 の JPY は本文を抽出できない）。
- **年 5% の候補**: **無い**。net が負なので leverage 計算は凍結規則どおり出していない。
- **正直に書くべきこと**: 1 回目の実行の後、2 つの独立 review role が共通基盤の date / leakage bug を
  見つけた。裁定 §40 に従い **1 回目を全 track INVALID とし、直して 2 回目を記録として採った**。
  修正の初版にも BLOCKER が 3 件あり、その版の実行は track が 1 本も終わる前に止めた。
- **次に何をすべきか**: 同じ 5 本を深掘りしない。**新しい機構**を、今回作った取得層の上で事前登録する
  のが次の一手。有料データを買う理由は今回の結果からは出ていない。

---

## Identity

| 項目 | 値 |
|---|---|
| #491 final head | `f50fd01` |
| #491 merge SHA | `6c54027` |
| PR A（取得・mapping・最終凍結） | #492、head `84d7832`、CI 2/2 SUCCESS、**OPEN（Amber、Human + ChatGPT の merge 承認待ち）** |
| PR B（実行・修正・結果・本報告） | branch `research/m15-next-five-execution`。commit `1e9d34e` → `55be254` → `d8e89be` → 本報告の commit |
| 最終 freeze digest | `0bc7b198d1564fd1d2da8d4433762d3c0fb7c60bac7ae0526e26dbdae3e9715c`（freeze commit `84d7832`、実行前。**修正後も不変**） |
| corrections digest | `54251bb0…`（`scripts/research/next_five/corrections.py`、alpha 後の修正を別に記録） |
| 記録として採る実行 | `development_run4.json` — HEAD `d8e89be`、**dirty path 0**、開始 2026-09-23T17:06:02Z、`--workers 14` |
| INVALID の実行 | `development_run2.json`（1 回目。全 track INVALID、消さずに残す） |
| 中止した実行 | run3（修正初版 `1e9d34e`）。**track が 1 本も終わる前に止め、出力ファイル無し、ログは見ていない** |

---

## Data Acquisition Architecture

`scripts/research/data_access/`（再利用できる層）と `scripts/research/next_five/acquire.py`。

- **Tier 1 = provider 一次配信**: Fed H.4.1（一括 zip）、BoJ（時系列 API）、SNB（data cube）、
  BoC（Valet）、Fed / ECB / BoJ の声明ページ。
- **Tier 2 = 公式の再配信**: ALFRED（alfred.stlouisfed.org）— OECD MEI の貿易収支、IMF の外貨準備、
  ECB の総資産、ICE BofA HY OAS。
- **fallback の規則**: 同じ経済変数の場合に限って経路を替える。合わなければ `DATA_MAPPING_BLOCKED`。
  series code は推測しない。metadata → title → units → frequency → coverage → 定義の順に確かめ、
  `mapping.check_semantics`（必須語・禁止語）が通らなければ保存しない。
- **network の境界**: `NEXT_FIVE_ACQUIRE_APPROVED=1` かつ script 実行の時だけ外へ出る。
  テストは conftest の socket / subprocess guard で塞いであり、mutation で opt-in を消しても外へは出ない。
- **failure taxonomy（10 分類）**: HTTP_STATUS / TIMEOUT / DNS / TLS / CONTENT_INVALID /
  PARSER_FAILURE / SERIES_NOT_FOUND / SEMANTIC_MISMATCH / PROVIDER_UNAVAILABLE（503 のみ）/
  ENVIRONMENT_RETRIEVAL_FAILURE。前 cycle の `classify_failure` には HTTP_STATUS に至る分岐が
  無かったので直してある（#491）。
- **期間を request に入れられたのは ALFRED と BoC だけ**。H.4.1 の zip、SNB の cube、BoJ の全系列、
  Fed の ne-press.json は全期間の応答をメモリで parse し、保存前に切り落とした（下記「保護データ」D-5）。

---

## Exact Series Mapping

| track / 通貨 | provider | series | 定義 | 頻度 | lag | 改訂 | coverage（保存分） |
|---|---|---|---|---|---|---|---|
| U1 USD/JPY/GBP/CAD/AUD/NZD/CHF | ALFRED / OECD MEI | `XTNTVA01{国}M664S` | 財の貿易収支（自国通貨、季調済み） | 月次 | m+2 月末以降 | 現行 vintage のみ | 1990-01 … 2025-12（long 318 行 / recent 56 行） |
| U1 EUR | ALFRED / OECD MEI | `XTNTVA01EZM664S` | euro area 19 か国の goods net trade（**他と定義が違う**） | 月次 | m+2 月末 | 現行 vintage | 1990-01 … **2022-12 で終了** |
| U2 USD | Fed H.4.1 | `RESPPA_N.WW` | 総資産（水曜 level） | 週次 | **観測 +3 営業日**（木曜公表 +2、C-5） | ほぼ改訂無し | 2002-12 … 2025-12 |
| U2 EUR | ALFRED / ECB | `ECBASSETSW` | ユーロシステム総資産（金曜日付） | 週次 | **観測 +4 営業日**（火曜公表 +2、C-5） | ほぼ改訂無し | 1999-01 … 2025-12 |
| U2 JPY | BoJ | `BS01/MABJMTA` | 日銀勘定 資産合計 | 月次 | m+2 月末 | ほぼ改訂無し | 1998-04 … 2025-12 |
| U2 CHF | SNB | `snbbipo / T0` | SNB 資産合計 | 月次 | m+2 月末 | ほぼ改訂無し | 1996-12 … 2025-12 |
| U2 CAD | BoC | `V36651` | BoC 総資産 | 月次 | m+2 月末 | ほぼ改訂無し | 1990-01 … 2025-12 |
| U2 GBP / AUD / NZD | — | **NOT_MAPPED** | BoE は metadata から特定できない。RBA / RBNZ は HTTP 403 | | | | |
| U3 USD / EUR / JPY | Fed / ECB / BoJ | 声明テキスト | 凍結語彙表（hawkish 16 語・dovish 19 語）で (H−D)/語数 → 前回差 | 会合ごと | 公表 +1 営業日 | 改訂無し | USD 38 本（2021-04-28 …）、EUR 37 本、JPY 38 本（**JPY はページ全体**） |
| U4 USD/JPY/GBP/CAD/AUD | ALFRED / IMF | `TRESEG{国}M052N` | 金を除く外貨準備（百万 USD） | 月次 | m+1 月末 | 現行 vintage のみ | 1990-01 … 2025-12 |
| U4 EUR | ALFRED / IMF | `TRESEGEZM052N` | 同（単位 "Dollars"） | 月次 | m+1 月末 | 現行 vintage | 1999-01 … 2016-06（**recent 0 行**） |
| U4 CHF / NZD | — | **NOT_MAPPED** | ALFRED に系列が無い（404）。SNB の項目を足して自作するのは代替にあたるので行わない | | | | |
| U5（1 系列を凍結 beta で 8 通貨へ） | ALFRED / ICE | `BAMLH0A0HYM2` | 米 HY OAS | 日次 | +2 営業日 | 改訂無し | **2023-09-25 … 2025-12-26 のみ**（ICE の license） |

---

## FRED Result

- **fred.stlouisfed.org / api.stlouisfed.org: この環境から unreachable**（TIMEOUT）。
  分類は **ENVIRONMENT_RETRIEVAL_FAILURE**。他の 6 ホストは 200 を返したので、環境の network は生きている。
- **provider 側は unaffected**。同じ St. Louis Fed の **alfred.stlouisfed.org は届き**、同じ系列を
  同じ定義で配信している。今回の Tier 2 はすべて ALFRED 経由。
- FRED API key は使っていない（env 経由のみという規則。repo に保存していない）。
- **FRED に届かないことを理由に有料データへは進んでいない。**

---

## Protected Data Status

- **fresh pool（2016-06-02 … 2021-04-25）、historical OOS slice、dead window、forward epoch の FX データは
  読んでいない。** FX return は long = ECB 参照レート 1999-01-04 … 2016-06-01、
  recent = 2021-04-27 … 2025-12-26 の seen span だけから作っている。
- **保存した外部系列**: parquet 23 本すべてで、2016-06-02 … 2021-04-26 と 2025-12-26 以降の stamp は 0 行
  （Role 2 が確認）。content hash は 23/23 一致。
- **開示すべき 2 点**:
  1. **D-5**: H.4.1 の zip、SNB の cube、BoJ の全系列、Fed の ne-press.json は、保護期間と 2026 年の行を
     含む応答を **メモリに読み込んで parse し、保存前に切り落とした**。T-V の先例（除外は request の性質）
     には届いていない。値は保存も計算もしていない。
  2. **C-4**: 月次系列は stamp の日付で seen を判定していたため、**2016-06-01 stamp（参照期間 2016 年 6 月 =
     fresh pool）と 2025-12-01 stamp が保存されていた**。1 回目の実行では前者が recent span の
     「12 か月変化」の基準値として計算に入っていた（C-2）。2 回目では読む側で落としている。
- recent span の最初の return は 2021-04-26 の close を使う（D-10）。CLAUDE.md の定義では 04-26 は seen。

---

## Original Five Status

| track | 候補 | 状態 | 理由 |
|---|---|---|---|
| U1 | S29 貿易 flow | **acquired**（8 通貨） | ALFRED / OECD MEI |
| U2 | S25 中銀 balance sheet | **acquired**（5 通貨） | provider 一次配信 4 + ALFRED 1。GBP/AUD/NZD は NOT_MAPPED |
| U3 | S27 声明 tone | **acquired**（3 通貨、recent のみ） | Fed / ECB / BoJ のページ。long span は機械取得できる声明が無い |
| U4 | S31 外貨準備 | **acquired**（6 通貨、recent は 5） | ALFRED / IMF。CHF/NZD は NOT_MAPPED |
| U5 | S07 信用 spread | **acquired**（recent のみ） | ALFRED / ICE。long span は license で存在しない |

**blocked も replaced も 0 本。**

## Replacement Tracks

**使っていない。** Stage 0 を 5 本とも通過したので、inventory からの差し替えは発生しなかった。

## Final Execution Set

U1（S29）、U2（S25）、U3（S27）、U4（S31）、U5（S07）の **5 本**。凍結順どおり実行した。6 本目は無い。

---

## Each Track Result

共通事項:
- 凍結した continuous currency book、cost は凍結参照値、null は circular shift 1000 回（seed 20260922）。
- Stage 1 は fixed / unfitted rule。**Stage 2 はどの track も eligibility（core E1/E3/E4/E7 +
  null percentile ≥ 0.80）を満たさず、実行していない。**
- primary span で net が 0 以下の track は、凍結規則により leverage / capacity の計算を出さない。

### U1 / S29 — 貿易収支の改善 → 通貨高

- **Mechanism**: 財の貿易黒字の改善は、実需の自国通貨買いを意味する。
- **Data**: OECD MEI の財の貿易収支 8 通貨（ALFRED）。EUR は別定義で 2022-12 に終了。
- **Timing**: 第 m 月の値は m+2 月末以降に使う。12 か月変化 → 252 日 z → cross-section 相対化。
- **Sample**: primary = long、4,332 日（17.2 年）。recent は 758 日。
- **Power**: MDE95 = net Sharpe 0.473（long）。
- **Null diagnostic**: 観測 net Sharpe −0.202。null の p05 / p50 / p95 = −0.459 / −0.075 / +0.304。
  percentile 0.306、**p = 0.694**。null の 38.9% が正。
- **Stage 1**: 実行。**Stage 2**: 不適格で未実行。
- **Gross Sharpe**: −0.122（long）/ −0.161（recent）
- **Net Sharpe**: −0.202（long、年 −2.16%）/ −0.255（recent）
- **Incremental information**: incremental IC +0.0016（E3 は形式上 pass だが大きさはほぼ 0）。IC −0.003。
- **Turnover**: 6.4 RT/年/単位 gross（25.3 回転/年）
- **Annual cost**: 0.86%
- **Stability**: 正の四半期ブロック 33/69
- **Currency breadth**: leave-one-currency-out の net は 8 通り全部が負（最悪 −0.356）
- **Concentration**: top-10 日の寄与 −0.76（損失が一部の日に集中していない）
- **Tail / DD**: 日次 p05 −1.08%、最大 DD −84%（book 規模で）
- **Cost stress**: cost 2 倍で net −0.283
- **Leverage / Margin**、**5% / 10% capacity**: net ≤ 0 なので出さない
- **Verdict**: `U1_S29_NOT_SUPPORTED_IN_SEEN_DEVELOPMENT`
- **Failure classification**: **SIGNAL_FAILURE**（gross も負）

### U2 / S25 — 中銀 balance sheet の相対膨張 → 通貨安

- **Mechanism**: 相対的に速く膨らむ中銀の通貨は供給過多になる。
- **Data**: Fed H.4.1・ECB（ALFRED）・BoJ・SNB・BoC の総資産。5 通貨。
- **Timing**: 週次は公表日 +2 営業日（C-5）、月次は m+2 月末。12 か月 log 変化 → z → 相対化 → 符号反転。
- **Sample**: primary = long、4,206 日（16.7 年）。recent は 758 日。
- **Power**: MDE95 0.480。
- **Null diagnostic**: 観測 −0.066、null p95 +0.294、percentile 0.552、**p = 0.449**。
- **Stage 1**: 実行。**Stage 2**: 不適格。
- **Gross Sharpe**: **+0.030**（long）/ **+0.476**（recent、secondary）
- **Net Sharpe**: −0.066（long、年 −0.72%）/ **+0.417**（recent、secondary、年 +4.6%）
- **Incremental information**: long −0.0004、recent +0.0064
- **Turnover**: 8.7 RT/年（long）、4.0（recent）
- **Annual cost**: 1.05%（long）
- **Stability**: 32/67（long）、8/12（recent）
- **Currency breadth**: long は LOO 最悪 −0.301。recent は 8 通り全部が正（最小 +0.079）
- **Concentration**: long の top-10 日寄与 −2.51
- **Tail / DD**: 最大 DD −55%（long）/ −14%（recent）
- **Cost stress**: cost 2 倍で long net −0.162
- **Leverage / Margin / capacity**: primary net ≤ 0 なので出さない。
- **Verdict**: `U2_S25_NOT_SUPPORTED_IN_SEEN_DEVELOPMENT`
- **Failure classification**: **COST_FAILURE**（primary の gross が正、net が負）。ただし gross +0.030 は
  null の中心と区別できない大きさ。
- **recent span の +0.417 について（重要）**:
  - secondary span なので判定には使わない（凍結規則）。3.0 年で MDE は 1.13 なので、検出下限を大きく下回る。
  - **この値は修正で符号が変わった**。1 回目（INVALID）は −0.516。原因は C-2（基準値が 2016 年の観測だった）と
    C-4（保護期間を参照する月次値）の除去で、recent span の開始が 2022-01-24 → 2023-01-23 に動いたこと。
    修正は 2 つの独立 role が結果の方向を知らずに要求したもので、救済のために選んだものではない。
    それでも **修正 1 回で符号が変わる量は、情報ではなく標本の揺れ** と読むのが正しい。
  - 参考値（判定外）: 年 5% に必要な gross は約 5.2、年 10% は 10.5（margin 使用 52%、DD 換算 −32%）。

### U3 / S27 — 声明 tone の hawkish 化 → 通貨高

- **Mechanism**: 声明の hawkish / dovish の傾きは次の政策の方向を先に示す。
- **Data**: Fed / ECB / BoJ の声明 113 本、凍結語彙表。**JPY はページ全体で採点**（D-6、欠陥）。
- **Timing**: 公表 +1 営業日。前回差 → z → 相対化。
- **Sample**: primary = recent、1,024 日（4.1 年）、3 通貨ちょうど。long は声明が無く DATA_NOT_DECISION_GRADE。
- **Power**: MDE95 0.972。
- **Null diagnostic**: 観測 −0.230、null p95 +0.594、percentile 0.443、**p = 0.557**。
- **Stage 1**: 実行。**Stage 2**: 不適格。
- **Gross Sharpe**: −0.105。**Net Sharpe**: −0.230（年 −2.44%）
- **Incremental information**: −0.0115
- **Turnover**: 11.8 RT/年。**Annual cost**: 1.32%
- **Stability**: 7/16。**Breadth**: LOO 最悪 −0.370（EUR を抜いた時だけ +0.027）
- **Concentration**: top-10 日寄与 −2.37。**Tail / DD**: 最大 DD −21%
- **Cost stress**: cost 2 倍で −0.354
- **感度**: staleness 45 / 60 と z_window 126 は途中で 3 通貨を割り、NOT_COMPUTABLE（C-6、fail-closed）
- **Verdict**: `U3_S27_NOT_SUPPORTED_IN_SEEN_DEVELOPMENT`
- **Failure classification**: **SIGNAL_FAILURE**

### U4 / S31 — 外貨準備の積み増し → 通貨安

- **Mechanism**: 準備の積み増しは自国通貨売り・外貨買いである。
- **Data**: IMF の金を除く外貨準備（ALFRED）、6 通貨（recent は 5）。**USD 建てなので為替の評価変動を含む**（D-7）。
- **Timing**: m+1 月末。3 か月 log 変化 → z → 相対化 → 符号反転。
- **Sample**: primary = long、4,332 日（17.2 年）。recent は 975 日。
- **Power**: MDE95 0.473。
- **Null diagnostic**: 観測 −0.378、null p95 +0.289、percentile **0.092**、**p = 0.908**。
- **Stage 1**: 実行。**Stage 2**: 不適格。
- **Gross Sharpe**: −0.315（long）/ +0.090（recent）
- **Net Sharpe**: −0.378（long、年 −4.14%）/ +0.011（recent）
- **Incremental information**: +0.0057（long）
- **Turnover**: 5.5 RT/年。**Annual cost**: 0.70%
- **Stability**: 26/69。**Breadth**: LOO は 8 通り全部が負（最悪 −0.497）
- **Concentration**: top-10 日寄与 −0.33。**Tail / DD**: 最大 DD −81%
- **Cost stress**: cost 2 倍で −0.442
- **Verdict**: `U4_S31_NOT_SUPPORTED_IN_SEEN_DEVELOPMENT`
- **Failure classification**: **SIGNAL_FAILURE**

### U5 / S07 — 信用 spread の拡大 → 安全通貨高

- **Mechanism**: HY spread の拡大は funding stress を表し、安全通貨（USD・JPY・CHF）の需要に先行する。
- **Data**: 米 HY OAS 1 系列を凍結 beta で 8 通貨へ配る（3 通貨規則は形式上だけ満たす）。
- **Timing**: +2 営業日。5 観測変化 → z → beta 射影。
- **Sample**: primary = recent、453 日（1.8 年）。long は license で存在しない。
- **Power**: MDE95 **1.46**（5 本で最も弱い）。
- **Null diagnostic**: 観測 −0.910、null p95 +0.612、percentile 0.339、**p = 0.661**。
- **Stage 1**: 実行。**Stage 2**: 不適格。
- **Gross Sharpe**: −0.280。**Net Sharpe**: −0.910（年 −10.4%）
- **Incremental information**: −0.0245
- **Turnover**: **44.4 RT/年**（212 回転/年）。**Annual cost**: **7.2%**
- **Stability**: 2/8。**Breadth**: LOO 全部が負（最悪 −1.20）
- **Tail / DD**: 最大 DD −22%。**Cost stress**: cost 2 倍で −1.52
- **Rename gate**: T1（VIX shock）との相関 0.321 < 0.8 で DISTINCT
- **Verdict**: `U5_S07_NOT_SUPPORTED_IN_SEEN_DEVELOPMENT`
- **Failure classification**: **SIGNAL_FAILURE**（gross が負）。cost が無くても負で、cost が損失を 3 倍に広げている。

---

## Cross-Track Comparison（primary span）

| track | span | gross | net | turnover RT/年 | 年 cost | null percentile | p | incIC | 正ブロック | LOO 最悪 | capacity | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| U1 | long 17.2y | −0.122 | −0.202 | 6.4 | 0.86% | 0.306 | 0.694 | +0.0016 | 33/69 | −0.356 | 出さない | NOT_SUPPORTED（SIGNAL） |
| U2 | long 16.7y | +0.030 | −0.066 | 8.7 | 1.05% | 0.552 | 0.449 | −0.0004 | 32/67 | −0.301 | 出さない | NOT_SUPPORTED（COST） |
| U3 | recent 4.1y | −0.105 | −0.230 | 11.8 | 1.32% | 0.443 | 0.557 | −0.0115 | 7/16 | −0.370 | 出さない | NOT_SUPPORTED（SIGNAL） |
| U4 | long 17.2y | −0.315 | −0.378 | 5.5 | 0.70% | 0.092 | 0.908 | +0.0057 | 26/69 | −0.497 | 出さない | NOT_SUPPORTED（SIGNAL） |
| U5 | recent 1.8y | −0.280 | −0.910 | 44.4 | 7.21% | 0.339 | 0.661 | −0.0245 | 2/8 | −1.205 | 出さない | NOT_SUPPORTED（SIGNAL） |

track 間の日次 net の相関はすべて |ρ| ≤ 0.16。**5 本は互いに別物を測っている**（rename gate も全て DISTINCT）。
そのうえで、どれも edge を示さなかった。

---

## Null / Gate Findings

- **p 値**: 0.449 / 0.557 / 0.661 / 0.694 / 0.908。**5 本とも null の内側**で、p ≤ 0.05 は 0 本。
  5 本を同じ null に当てると、帰無でも 1 本以上が 5% を切る確率は約 23% ある。今回はそれすら起きていない。
- **null の通過率**: permutation p は構成上 5%。旧 3 条件 triple（gross > 0・incIC > 0・net > 0）は
  前 cycle の実測で帰無通過率 42% なので、diagnostic へ降格したまま。
- **null の形**: 5 本とも null の中央値が負（−0.06 〜 −0.63）。**信号の持続性と cost が同じなら、
  情報の無い signal は平均して負になる**。「net が負」は情報が無いことの自然な帰結で、それ以上の否定ではない。
- **gate の有用性**: 2 軸の分離（NULL_REJECTION と DEVELOPMENT_ECONOMICS）は今回の判断を変えていない。
  両軸とも 5 本すべて NOT_SUPPORTED で、軸が食い違う track は無かった。
- **現実的な null を超えた観測は無い。** 最も高い percentile は U2 の 0.552。

---

## Positive Candidates

- **decision-grade positive: 0 本。**
- **observed positive（判定外の secondary span）**:
  - U2 recent: net +0.417（3.0 年、MDE 1.13）。上記のとおり修正 1 回で符号が変わった量。
  - U4 recent: net +0.011。ゼロと同じ。
  - どちらも primary ではなく、凍結規則上 rescue に使えない。**observed positive と decision-grade positive は別物**で、
    この 2 つは前者に過ぎない。

## Negative Candidates

- **SIGNAL_FAILURE（gross も負）**: U1、U3、U4、U5
- **COST_FAILURE（gross 正・net 負）**: U2。ただし gross +0.030 は null の中心と区別できない。
- **cost だけで説明できる track は無い。** 前 cycle（4 本が cost で死んだ）と違い、今回は信号そのものが無い。

## Data-Blocked Candidates

- **provider 側に存在しない**:
  - U5 の long span（ICE の license で 2023-09-25 以前は配信されない）
  - U4 の CHF / NZD（ALFRED に系列が無い）
  - U1 EUR の 2023 年以降（OECD MEI の euro area 系列が廃止）
  - U3 の long span（機械取得できる過去声明が無い）
- **provider が拒否した**: U2 の AUD / NZD（RBA・RBNZ が HTTP 403）
- **metadata から特定できない**: U2 の GBP（BoE IADB にカタログ API が無い）
- **environment retrieval failure**: FRED（fred.stlouisfed.org）の TIMEOUT のみ。ALFRED で完全に迂回できた。
- **どれも track 全体を止めてはいない。**

---

## Engineering Findings（alpha 判定とは別）

1. **alpha の後に共通基盤の bug が見つかった。** 2 つの独立 review role（経済 / 来歴・timing・governance）が、
   互いの結論を知らずに同じ 3 件を指摘した。
   - C-1: `scores_for` の上限なし ffill。U1 EUR の score を系列終了後 685 営業日持ち越していた。
   - C-2: `_change` の基準値が保護期間の空白を跨ぐ。「12 か月変化」の中身が約 5 年変化だった。
   - C-3: 月次値の着地が 1〜3 日早い（`DateOffset` を月末に足した）。
   Role 2 はさらに C-4（保護期間を参照する月次 stamp）と C-5（ECB 週次を公表日当日に使う look-ahead）を指摘した。
2. **修正の初版にも BLOCKER が 3 件あった**（独立再監査）。U2 / U4 が KeyError で丸ごと落ちる、C-2 の修正が
   `_align` の ffill と組んで 2016 年の値を約 1 年運ぶ、ffill を外すと run_book の連続性要件と衝突する。
   その版の実行は止め、直した版を 2 回目の独立再監査に通した（BLOCKER 無し）。
3. **mutation**: 修正 10 箇所を 1 つずつ戻し、10/10 をテストが捕まえる。
4. **判断が入った修正は判断として記録した**:
   - C-2: 基準値の鮮度を `max_staleness_days` で測る
   - C-5: 凍結文の内部矛盾（series_map と P-2 は観測日基準、TRACKS は公表日基準）を厳しい側で解く
   - C-6: 途中の欠けは flat にも分割にもせず fail-closed
5. **来歴の弱点（開示のみ、D-1〜D-4）**:
   - 取得後にコードを編集してから commit した
   - 取得時の digest を再構成できない
   - 語彙表の commit が tone の計算より後で、「数える前に固定した」を git 履歴で立証できない
   - `NO_SIGNAL_HAD_RUN` は誤りで、Stage 0 で score の日数を数えていた（return は使っていない）
6. **Stage 0 は C-2 も C-5 も検出できなかった**（D-9）。Stage 0 は「データがあるか」を見る段で、
   「データが正しい時刻に正しい中身で入るか」は見ていない。
7. `BDay` は祝日を知らないので、祝日週の週次公表は 1 日早く使う可能性が残る（C-5 residual）。
   U5 の「5 日変化」は 5 観測（D-11）。

---

## Paid Data Assessment

**必要にならなかった。**

- 5 本とも無料の公式配信で、凍結した経済変数そのものを取れた。
- 失敗は data の欠けではなく signal そのものにある。gross が負、または null と区別できない。
- 有料データで良くなりうるのは次の 3 つだけ。
  - U5 の long span（ICE の過去 OAS）
  - U3 の本文品質
  - U1 / U4 の point-in-time vintage
- どれも「符号が逆」「null の中央」という今回の結果を覆す筋ではない。
- **FRED に届かないことは有料化の理由にならない**（ALFRED で完全に迂回できた）。

## Remaining Candidate Space

- **未検証の機構**: inventory の S01〜S31 のうち、今回と前 cycle で測っていないもの（rerank #489 の下位）。
  ただし #489 の signal-blind feasibility は、**pooled 22.5 年でも真の Sharpe 0.3 を検出する力は 0.30** と示している。
  1 本ずつの span 延長では決められない構造は変わっていない。
- **今回測ったが確定していないもの**:
  - U5（MDE 1.46 で、ほぼ何も言えない）
  - U3（3 通貨・4 年、JPY 本文に欠陥）
- **point-in-time vintage**: U1 / U4 は現行 vintage のみ。季節調整の係数は保護期間を含む全標本から推定されている。
- **multi-source の事前登録**: まだ行っていない。個別の 5 本がどれも null の内側なので、それらを後から
  組み合わせるのは post-hoc 最適化になり、禁止されている。

---

## Final Answers

1. **net cost 後で positive な candidate はあったか？**
   — **無い。** primary span の net Sharpe は 5 本とも負（−0.066 〜 −0.910）。secondary span の
   U2 recent +0.417 は判定外で、修正 1 回で符号が変わった量である。
2. **FX 自身の price information を超える incremental value はあったか？**
   — **無い。** incremental IC は −0.025 〜 +0.006。U1 と U4 の E3 は形式上 pass だが、+0.002 / +0.006 は
   ゼロと区別できない。
3. **null / no-information behavior を超えた candidate はあったか？**
   — **無い。** percentile は 0.09 〜 0.55、p は 0.45 〜 0.91。5 本とも零情報の circular shift の分布の内側にある。
4. **現実的な risk / leverage / margin で年 5% net が射程の candidate はあるか？**
   — **無い。** net が負なので、leverage は損失を拡大するだけ。凍結規則どおり capacity は出していない。
5. **年 10% net はどうか？** — **無い。** 同上。
6. **今回の最大ボトルネックは？** — **signal quality。**
   - 5 本中 4 本は gross が負で、残る 1 本の gross も null の中心にある。
   - 前 cycle の主因だった cost は、今回は主因ではない。例外は U5 で、212 回転/年・年 7.2% の cost を払っている。
   - power も弱い（MDE 0.47〜1.46）。ただし 3 本は 17 年の long span を持ち、そこでも点推定が負なので、
     「power が足りず正の edge を見落とした」とは読めない。
7. **次に進むべきものは？** — **new mechanism。**
   - **same candidate deepening** は No。5 本とも null の内側で、horizon・符号・部分集合を変えるのは禁止された救済にあたる。
   - **new free data** はそれだけでは No。data plumbing は今回の成果として完成しており、欠けているのは data ではない。
   - **paid data** は No。上の Paid Data Assessment のとおり。
   - **execution engineering** は No。cost が主因ではない。
   - **multi-source prereg** は、構成要素に単独で null を超えたものが 1 本も無い現状では時期尚早。
   - 次は、**今回の取得層を再利用して、まだ測っていない機構を少数、事前登録すること**である。
     ただし #489 の検出力の天井（1 本では決められない）を前提に、候補の数と span をあらかじめ設計する必要がある。

---

## Human + ChatGPT Decisions Needed

1. **PR #492（取得・mapping・最終凍結）と本 PR（実行・修正・結果）の merge 可否**。両方 Amber。
   本 PR は alpha 後の修正（C-1〜C-6）を含み、**2 回目の alpha 測定を記録として採っている**。
   裁定 §40 の「止めて直し、都合よく結果を保持しない」の適用として受け入れるかを判断してほしい。
   1 回目は INVALID として残してある。
2. **D-5（保護期間を含む応答をメモリで parse した件）の扱い**。保存物にも計算にも残っていない
   （C-4 の月次 stamp は読む側で落としてある）が、T-V の先例「除外は request の性質」には届いていない。
   次の取得で request 段階の除外を必須にするかどうか。
3. **次 cycle の方向**。new mechanism を、#489 の検出力の天井を前提に設計してよいか。
   それとも FX spot の alpha 研究そのものの継続可否を問い直すか。
