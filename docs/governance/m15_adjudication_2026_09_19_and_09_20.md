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
