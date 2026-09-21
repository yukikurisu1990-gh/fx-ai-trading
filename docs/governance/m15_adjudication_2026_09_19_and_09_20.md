# Human + ChatGPT 裁定記録 — 2026-09-19 / 2026-09-20

`DECISION_RECORD` · `PRODUCTION_READINESS_NOT_CLAIMED`

本書は **act の記録**である。ここに書かれていることは、文書が主張しているのではなく、
**Human + ChatGPT が実際に決めた**。PR #489 の §0a が「裁定本文が repo に存在しない」と
記録していた欠落を埋めるために作成した。

---

## 0. この記録の性質と、その限界

**重要**: 本書は 2026-09-19 裁定の**逐語再現ではない**。当該裁定はセッション内で口頭に相当する形で
与えられ、その全文は本 repo に持ち込まれていない。本書が記録するのは:

1. **2026-09-20 の裁定**（PR #489 の最終報告をレビューした上で下されたもの）— これは全文が
   本セッションに与えられており、**逐語に近い形で §2 以降に記録できる**。
2. **2026-09-19 裁定のうち、2026-09-20 裁定が明示的に確認・変更した部分**。

2026-09-19 裁定の節番号（§2〜§46）は PR #489 の code と doc が引用しているが、
**その全文は依然として repo に無い**。本書はそれを捏造しない。
代わりに、**2026-09-20 裁定が上書きした箇所を明示**し、引用が残っている箇所については
「検証不能な引用である」という事実自体を記録する。

→ `PRIOR_ADJUDICATION_TEXT_NOT_IN_REPO_CITATIONS_UNVERIFIABLE`

---

## 1. 2026-09-19 裁定（PR #486–#488 のレビューに伴うもの）

PR #489 の code / doc が引用している内容のうち、**後続の act によって確認されたもの**:

| 項目 | 内容 | 状態 |
| --- | --- | --- |
| T-R fast | `MARKET_YIELD_REPRICING_FAST_5D_MEASURE_NOT_SUPPORTED_IN_SEEN_DEVELOPMENT` | 確認済み |
| T-R2 slow | `MARKET_YIELD_SLOW_REPRICING_NOT_SUPPORTED_IN_SEEN_DEVELOPMENT`（事前登録した 20 日 formulation について） | 確認済み |
| family closure | `MARKET_YIELD_REPRICING_SIMPLE_DIRECTIONAL_FAMILY_NOT_SUPPORTED_IN_SEEN_DEVELOPMENT`（scope 限定） | 確認済み |
| T-V | `REAL_EXCHANGE_RATE_VALUATION_NOT_SUPPORTED_IN_DEVELOPMENT` | 確認済み |
| 上限 | 「最大 2 track」 | **2026-09-20 に変更**（§2 参照） |

closure が**閉じる**のは 4 点（public daily sovereign-yield data / simple fast directional
repricing / simple slow directional repricing / subsequent G10 FX directional return）、
**閉じない**のは 8 点（OIS / market-implied policy path / rate futures / intraday rate
repricing / curve shape / term-premium information / rates options / distributional
policy-path information）。これは 2026-09-20 裁定 §6・§7 が再確認している。

---

## 2. 2026-09-20 裁定 — 本 cycle の execution authorization

PR #489 の最終報告と、その後の研究進行方針をレビューした上で下された。

### 2.1 上限の変更

> 前回の「最大2 track」という上限を変更します。

**上位 5 つの genuinely distinct expected-return source を、結果を見る前にすべて設計・freeze し、
その後まとめて minimal development まで実行する**ことを承認。

目的は 1 本ずつ結果を見て次を調整することではなく、

> G10 FX spot において、どの種類の information source に economic edge の兆候が残っているかを、
> 同一の development framework で一気に地図化すること

**5 本終了後は必ず停止し、6 本目へ自動で進まない。**

### 2.2 今回の性格

confirmation ではなく **development candidate discovery / comparative screening**。

したがって:

- development 結果を formal proof と呼ばない
- 5 候補中の best を「真の edge」と断定しない
- p 値だけで採否を決めない
- 一方で negative economics を power 不足だけで無視もしない

### 2.3 PR #489 の扱い

**`CONDITIONAL_MERGE_APPROVED`** — 以下を完了後、追加 Human 確認なしで merge してよい。

1. 2026-09-19 裁定を decision record として repo に記録 ← **本書**
2. S07 / S02 gated probe を実行
3. availability / coverage 結果を更新
4. 必要なら signal-blind ranking を再計算
5. `BEST_AVAILABLE_SPAN_STILL_UNDERPOWERED_FOR_A_REALISTIC_EDGE` が
   **development 禁止を意味しない**ことを明示 ← §3
6. relevant tests / contract-tests / mutation checks green
7. GitHub CI green

merge 後、#489 final head / merge SHA / master SHA / CI を記録する。

### 2.4 gated probe の承認

S07 / S02 等、#489 で未確定の public-data availability probe を承認。

**metadata / availability / coverage の確認のみ。**

禁止: alpha 計算 / FX return read を伴う signal test / protected span read /
authenticated broker / paid source。

必須記録: source・URL・parameters・retrieval timestamp・HTTP result・hash・coverage・
failure classification。

> TLS / SSL / local environment failure を provider unavailable と混同しない。

### 2.5 network safety（事故の再発防止）

> mutation 下で `acquire()` が network へ出て committed provenance を上書きした事故

を再発させない。必須:

- tests: network fail-closed
- acquisition: explicit opt-in
- provenance overwrite: explicit mode only
- mutation test から live network へ到達不能

実装と、実際に見つかった 4 つの穴は `scripts/research/acquisition_safety.py` の docstring と
`tests/research/test_acquisition_safety.py` に記録した。

---

## 3. `UNDERPOWERED_FOR_CONFIRMATORY_CLAIM != NOT_WORTH_DEVELOPING`

**これを authoritative principle として記録する**（2026-09-20 裁定 §4）。

PR #489 は「到達可能などの span も、現実的な 0.2–0.5 の edge を 0 と分離できない」と結論し、
全候補の verdict を `BEST_AVAILABLE_SPAN_STILL_UNDERPOWERED_FOR_A_REALISTIC_EDGE` とした。
**これは正しい statement だが、development を禁止する statement ではない。**

- **confirmatory claim**（formal な有意性の主張）には検出力が足りない — これは #489 の通り。
- **development screening**（どの information source に兆候があるかの地図化）は別工程であり、
  検出力が 80% に届かないことを理由に実行しない、という帰結にはならない。

development で screen するもの:

sign / effect magnitude / net economics / benchmark increment / temporal stability /
breadth / concentration / cost robustness / annual-profit capacity

**confirmation は別工程**であり、本 cycle では行わない。

→ 記録する token: `UNDERPOWERED_FOR_CONFIRMATORY_CLAIM_DOES_NOT_FORBID_DEVELOPMENT`

同時に、逆向きの誤用も禁じられている（§31）: negative economics を
「どうせ検出力不足だから」で無視してはならない。negative の候補は
signal content / cost・turnover / data・power / concentration の**どの失敗か**を分けて記録する。

---

## 4. 本 cycle で越えてはならない線

| 対象 | 状態 |
| --- | --- |
| fresh pool `2016-06-02 … 2021-04-25` | **読まない**（schema 確認にも使わない） |
| historical OOS | **読まない** |
| dead window | **読まない** |
| forward Formal Confirmation epoch | **読まない** |
| paid data | **購入しない**（design-only proposal のみ） |
| authenticated broker / demo / paper / live | **触れない**（public specification のみ） |
| nonlinear ML | **本 cycle では training しない**（proposal のみ） |
| multi-source portfolio 最適化 | **本 cycle では行わない**（次 phase の prereg 対象） |
| 6 本目の track | **進まない** |

pre-2016 の既 seen corpus は `EXPLORATORY_SEEN_DEVELOPMENT_DATA` として使用可。
ただし protected fresh span を含む full download は禁止。

protected range の除外は **string lexical compare ではなく parsed typed date bound** で保証し、
download-then-filter は禁止。

---

## 5. cycle 終了条件

以下が完了したら **STOP**:

- #489 merged
- gated probes resolved
- final ranking frozen
- top-five execution set frozen
- 5 track すべて実行、または事前に data-blocked と宣言
- integrated adversarial review 完了
- final report 提出

fresh confirmation / paid escalation / complex ML / multi-source optimization /
paper-forward には進まない。

5 本すべて negative でも `FX research paused` を**勝手に設定しない**。
その場合は what failed / why / what remains / whether paid or new information is now justified
を Human + ChatGPT へ返す。

---

## 6. 2026-09-21 裁定 — 全 cycle の autonomous execution authorization

**この節は後から追記された。** PR #490 の最終報告をレビューした上で 2026-09-21 に
下された裁定の全文がセッションに与えられたので、その内容をここに記録する。
本 cycle の code / doc は §1〜§57 を節番号で引用しており、
**その引用先が repo に無い**という §0 と同じ欠落を埋めるためである。

**逐語再現ではない。** 構造と拘束力のある文言を保存した要約であり、
原文の節番号を維持している。

### 6.1 与えられた権限（§1 冒頭）

以下を **途中で Human 確認へ戻らずに**実行してよい:

1. PR #490 の未確定事項を修正
2. Top-Five 全 5 track を**結果を見る前に**再 freeze
3. #490 を merge
4. 必要な public / free data を取得
5. 5 本すべてを minimal development まで実行
6. 共通基準で比較
7. 最終統合報告を提出し、**その後 STOP**

### 6.2 依然として未承認のもの（逐語）

- fresh pool read（`2016-06-02 … 2021-04-25`）
- historical OOS read
- dead window read
- forward Formal Confirmation epoch read
- paid data purchase
- authenticated broker API
- demo / paper / live execution
- nonlinear / complex ML
- post-hoc multi-source portfolio optimization
- 6 本目以降の track execution

### 6.3 主要な拘束（§5, §22–§28, §37, §39, §42–§43）

- **acquisition は承認済み**（public / free のみ）。provider / URL / request parameters /
  取得時刻 / HTTP status / content hash / coverage / 頻度 / 公表タイミングを記録すること
- protected span は **request 自体から除外**。download-then-filter は禁止。
  範囲境界は **parsed typed date** で判定し、文字列の辞書順比較を使わない
- test / mutation では network を hard-disable し、
  **opt-in guard が mutation で壊れても live network へ到達できない構造**にすること
- **T3 は両符号（H1 appreciation / H2 depreciation）を prereg し、両方を報告する。**
  結果を見て良かった符号だけを primary 扱いしない
- **leverage は三概念を分ける** — `max_leverage=5` を feasibility の hard limit として
  使わない。broker の 20x / 25x を運用の risk budget として使わない
- **5 本中 Sharpe 最大だからという理由だけで `winner` と扱わない。**
  absolute economics を優先する（§37）
- 旧 freeze は `SUPERSEDED_PRE_EXECUTION` として保持する
- xlrd: research 用途限定 / version 固定 / production dependency へ波及させない /
  `.xls` は data parsing のみ / embedded macro を実行しない / 取得 file の hash を記録
- 報告と research docs は**日本語**で記載する

### 6.4 手順と PR 構成（§44, §45, §48, §50, §51）

- §44: #490 は「裁定反映 → xlrd → T3 dual-sign → 5 本 freeze 完成 → new digest →
  tests → contract-tests → mutation / leakage → CI green」が揃えば
  **追加 Human 確認なしで merge 可**
- §45: **#490 merge 後に** data 本取得 → timing / availability audit → five-track execution
- §48: review は 2 roles（Role 1 = economics / mechanism / profitability / leverage、
  Role 2 = timing / leakage / provenance / implementation / governance）。
  **reviewer へ期待結論を教えない**
- §50: micro-PR を避け、#490 以降は**最大 3 PR 程度**
- §51: **#490 以降に作る execution / result PR は Amber**（Human + ChatGPT merge approval 待ち）。
  本裁定は execution authorization であって、結果 PR の自動 merge authorization ではない

### 6.5 停止条件（§55, §56, §57）

- 5 本終了後 **STOP**。6 本目 / fresh confirmation / multi-source optimization /
  非線形 ML / paid acquisition / paper-forward は禁止
- 全部 negative でも `FX research paused` を**勝手に設定しない**。
  programme-level 判断は Human + ChatGPT へ返す
- 途中で Human へ戻るのは原則 7 つの場合のみ（protected data / paid purchase /
  authenticated broker / legal ambiguity / common methodology blocker /
  freeze 後の execution set 変更 / 6 本目）

### 6.6 CORE PRINCIPLE（逐語に近い）

> 今回の目的は、5 本の中から無理に winner を作ることではない。
> 目的は、**どの種類の外部情報が、FX 自身の price history を超えて、
> 実際に monetizable な expected return を持つのかを、
> 同じ development framework で比較すること**である。

### 6.7 本 cycle で実際に起きた手順逸脱（記録）

**§44 / §45 の順序を守らなかった。** #490 を freeze のみで merge せず、
同じ branch 上で acquisition と execution まで行った。
その結果 #490 は freeze / acquisition / execution を 1 本に含んでおり、
§44 が merge 許可を与えた範囲より中身が広い。

→ repository 規約（tier をまたぐなら高い方が支配する／研究制限は厳しい読みを採る）と
§51 に従い、**#490 は execution-evidence PR として扱い、merge せず
Human + ChatGPT の merge approval を待つ**。

結果そのものへの影響は無い（freeze は実行前に完成しており、digest も記録されている）が、
**手順としては逸脱であり、隠さず記録する。**
