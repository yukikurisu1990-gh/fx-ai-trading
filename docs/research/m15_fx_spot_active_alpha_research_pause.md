# FX Spot Active-Alpha Research — 研究結果の整理と一時停止

`PRODUCTION_READINESS_NOT_CLAIMED`

Status: **`FX_SPOT_ACTIVE_ALPHA_RESEARCH_PAUSED`**（2026-09-14 の Human + ChatGPT 裁定による一時停止を表す。token 自体は `記録用`）

## 0. この文書の位置づけ

- 本文書は、Human + ChatGPT が 2026-09-14 に決めた**研究運営上の制約**（FX spot active-alpha research の一時停止）を
  記録する governance 記録であり、一時停止時点の研究状態の正本である。**Track A の研究出力ではない。**
- 本文書が引用する Track 1 などの数値は、それぞれの記録のとおり `NON_DECISION_BEARING_EXPLORATORY_ONLY` のままである。
  ここでは**停止という制約を課した理由**として、裁定 §3 の求めにより記録する。GO・候補・edge の証拠として引用するのではない。
  最小研究 gate §8.11.2(1) は Track A の結果を「このプログラムが記録するいかなる決定」の証拠にも使えないと定めているため、
  この引用との関係は §13 で Human + ChatGPT の確認事項とする。
- 機械可読な写しは `scripts/research/programme_status.py`、仮説ごとの記録は `scripts/research/round_a/ledger.py`
  （H-001〜H-024）。本文書の判定・範囲・禁止・条件の各表の行は、写しの対応する項目と**一字一句一致**することを
  `tests/research/test_programme_status.py` が要求する。
- **出典区分**: `裁定`（受領した裁定本文にある）、`裁定（推奨）`（裁定本文が推奨として述べた）、`裁定から導出`（裁定から導けるが
  そのものとしては述べられていない。確認待ち）、`既存規則`（CLAUDE.md・自律開発方針・既存の裁定や事前登録で既に拘束的）、
  `起草`（裁定本文の欠落を補う提案。確認待ち）、`記録用`（裁定が名付けなかった状態に本記録が付けた token）。
- **確認待ちの効力（全節共通）**: `起草` と `裁定から導出` の禁止・停止・条件は、確認されるまで**暫定的に拘束する**（厳しい方の読み）。
  確認待ちの行が許可を広げることはない。

> ⚠ **裁定本文の欠落。** 受領した裁定は §9「Tail diagnostics」の途中（"temporal co"）で途切れている。
> 途切れた語は特定できない。§9 以降にあったはずの内容は、本文書では `起草` として区別し、Human + ChatGPT の確認で確定する。

---

## 1. 裁定と status

| 対象 | status | 出典 |
| --- | --- | --- |
| programme | `FX_SPOT_ACTIVE_ALPHA_RESEARCH_PAUSED` | 記録用 |
| track_1_continuous_currency_portfolio | `CONTINUOUS_CURRENCY_PORTFOLIO_ARCHITECTURE_NOT_SUPPORTED_IN_SEEN_DEVELOPMENT` | 裁定 |
| efficiency_bundle | `TURNOVER_REDUCTION_MECHANISM_SUPPORTED` | 裁定 |
| track_3_event_volatility_overlay_of_480 | `NOT_STARTED_BASE_EDGE_REQUIRED` | 裁定 |
| complex_ml | `NOT_AUTHORISED_NO_POSITIVE_BASE_EVIDENCE` | 記録用 |
| post_hoc_currency_reversal_observation | `POST_HOC_EXPLORATORY_NON_DECISION_BEARING` | 裁定 |
| tail_policy_prospective | `TAIL_CONCENTRATION_HARD_KILL_DEMOTED_TO_ADVERSARIAL_DIAGNOSTIC` | 裁定（推奨） |

- Track 1 の意味: 今回事前登録した continuous currency-level expected-return portfolio architecture は、seen development
  data 上で経済的に支持されなかった。
- **`FX_HAS_NO_EDGE` ではない。** FX spot に edge が無いことは主張しない。
- 次の作業は新しい alpha 探索ではない。研究結果を正本として整理し、FX spot active-alpha research を一時停止し、再開条件を記録する。

**原則**

| 原則 | 出典 |
| --- | --- |
| `EFFICIENCY_CANNOT_RESCUE_NEGATIVE_EXPECTED_RETURN` | 裁定 |
| `COMPLEXITY_REQUIRES_POSITIVE_BASE_EVIDENCE` | 記録用 |
| `A_FAILED_RULE_IS_NOT_AN_INVERTED_RULE` | 既存規則 |

## 2. Merge 記録

| PR | 内容 | merge commit |
| --- | --- | --- |
| #478 | Pass-region preflight + decision-grade inventory | `a0780e3` |
| #479 | Model-learning 研究（Case C、gate に範囲限定） | `3b4d0a9` |
| #480 | Profit architecture redesign | `3bbb7f5` |
| #481 | Track 1 事前登録 + 実装（凍結 hash `aa0888089e4d…`） | `e13dba2` |
| #482 | Track 1 開発実行 + 結果 | `a98fbc6` |

stack は #481 → #482 の順に解消した（#482 の base 追随 merge は tree hash が承認時と同一）。最終 master CI は green。

**未 merge の研究 PR**: #473（expectation benchmark、survey consensus の検出力ある null）は open のままで、結果は master に無い。
したがって本文書では**正本として引用しない**。同 PR は survey-consensus family を閉じる内容を含むが、未 merge のため ledger に無く、
閉鎖としても開放としても扱わない。扱いは §13 の判断事項。

## 3. Track 1 Case C の根拠（primary portfolio、10% vol target）

| 指標 | 値 |
| --- | --- |
| gross Sharpe | **−0.47**（−0.4688） |
| net Sharpe | **−0.84**（−0.8425） |
| net 年率 | 約 −8.42% |
| 実現 vol | 約 9.99% |
| cost | 約 3.74%/年 |
| turnover | 約 25.6 round trip / 年 / 単位 gross |
| 正の fold | 1 / 6 |
| max DD | 約 −32% |
| cost stress | ×1.5 で −1.0288、×2 で −1.2147（悪化） |
| currency breadth | 弱い（最大の正の通貨 GBP を除くと gross −18.85%、USD を除いても −6.41%、累計） |
| 単純な 20 日 reversal 型 benchmark との日次 P&L 相関 | 約 0.64（primary はその rule より悪い） |

**コストだけが原因ではない。** gross の時点で負である（コストは損失の約 44%）。

詳細: `docs/research/m15_track1_continuous_portfolio_results.md`、記録 `artifacts/research/continuous_portfolio/development.json`。

## 4. Efficiency bundle の扱い

- no-trade band・部分 rebalance 等は **`TURNOVER_REDUCTION_MECHANISM_SUPPORTED`**（engineering result）として残す。
- **`ALPHA_SUPPORTED` とはしない。**
- turnover は約 42.8（bundle なし）→ 約 25.6 RT/年/単位 gross に下がったが、gross expected return は負だった。
  （bundle なしの baseline は band 以外に mapping・cap・neutralization・vol target も異なる。band だけを外した診断では 42.0。）
- 原則: **`EFFICIENCY_CANNOT_RESCUE_NEGATIVE_EXPECTED_RETURN`**。

## 5. Track 3（#480 の event / volatility exposure overlay）と救済の禁止

- status: **`NOT_STARTED_BASE_EDGE_REQUIRED`**。進まない。理由は core の expected-return source が正でないこと。
- ここでの Track 3 は #480 の再設計が定義した overlay であり、#475 の「Track 3 execution frontier」とは別物。

**禁止する救済**

| 禁止 | 出典 |
| --- | --- |
| event filter による救済 | 裁定 |
| volatility filter による救済 | 裁定 |
| regime filter による救済 | 裁定 |
| horizon 変更による救済 | 裁定 |
| post-hoc の通貨レベル reversal 観察（H-024）の再事前登録 | 裁定 |
| 閉鎖・隣接 family の符号反転 | 裁定から導出 |
| leverage・vol target の変更による救済 | 既存規則 |
| turnover・コスト効率の改善を alpha として扱うこと | 裁定から導出 |

## 6. Complex ML

- status: **`NOT_AUTHORISED_NO_POSITIVE_BASE_EVIDENCE`**。今回進まない。
- 理由: 単純な architecture が gross 負・時間的に不安定・benchmark に対する優位なしで、複雑さの追加を合理化する正の base evidence が無い。

**未承認**

| model family | 出典 |
| --- | --- |
| LightGBM expansion | 裁定 |
| nonlinear ML | 裁定 |
| HMM | 裁定 |
| neural networks | 裁定 |
| representation learning | 裁定 |
| complex ensemble | 裁定 |

## 7. post-hoc の通貨レベル reversal 観察

- 60 日 reversal の +0.52、20 日 reversal の +0.31 を候補に昇格しない。status: **`POST_HOC_EXPLORATORY_NON_DECISION_BEARING`**（ledger H-024）。
- **対象は通貨レベルの reversal family**: 5・20・60 日のどれでも、どの符号の組み合わせでも（Track 1 の結果記録が
  既に述べた範囲）。**それ以外の horizon に及ぶかは `裁定から導出` で、§13 の確認事項**とし、確認までは及ぶものとして扱う。
- 理由: 閉鎖済み・隣接 family（C08 persistence の符号反転、dropped の multi-day reversal family に隣接）、標準誤差 約 0.58、
  6 本の unfitted rule の中の最大値、過去の reversal 証拠と整合する確認ではない。
- **再事前登録は禁止。**

## 8. Tail diagnostic policy（将来に向けた推奨）

- 今回の Case C の判定は**変更しない**。過去の事前登録・判定も**書き換えない**。
- 既存の tail kill は、「少数の大きな正の日に依存する strategy」を機械的に kill すると、本物の positive-skew strategy まで
  偽陰性にしうる。
- したがって裁定は、将来の方針として **tail concentration を hard kill から adversarial diagnostic へ降格することを推奨**した:
  **`TAIL_CONCENTRATION_HARD_KILL_DEMOTED_TO_ADVERSARIAL_DIAGNOSTIC`**（prospective のみ、出典は 裁定（推奨））。
- **この降格は、tail 条項も発火して閉じた family（H-021 COT、H-022 Track A など）を再び開かない**（`裁定から導出`、RC-10）。
  いずれも tail 条項だけで閉じたのではない（H-021 は family-wise null と tail 上限、H-022 はコスト stress・JPY 集中・上位 10 日占有率など）。
- 降格は、Track 1 事前登録が開示した「高 Sharpe の lottery 型 book を tail kill が通す」問題を**解消しない**（diagnostic 化すれば
  通過はむしろ容易になる）。この受け入れ判断は §13 に残す。

## 9. Tail diagnostics（再開時の最低限）

| 診断 | 出典 |
| --- | --- |
| top 1 day contribution | 裁定 |
| top 5 days contribution | 裁定 |
| top 10 days contribution | 裁定 |
| largest loss days | 裁定 |
| top days 除外後の符号 | 裁定 |
| 「temporal co…」（語は未確定: concentration / consistency / correlation 等） | 起草 |
| top / worst days の通貨・pair 集中 | 起草 |
| top days と予定イベントの重なり | 起草 |
| 日次歪度・超過尖度 | 起草 |
| ±3 robust σ 内の日の収益 | 起草 |

注: net 合計が 0 以下の book では top-day 占有率は定義されない（Track 1 の記録では `None`）。そのときは除外後の符号と
largest loss days で読む。

## 10. 研究プログラム全体の状態（一時停止時点）

### 10.1 仮説 ledger（`scripts/research/round_a/ledger.py`）

24 件: CLOSED 20、OPEN 4、事前登録 18、post-hoc 6。

| ID | round | 状態 |
| --- | --- | --- |
| H-001〜H-004 | Exploratory Round 1 | CLOSED |
| H-005 | Exploratory Round 2（multi-day reversal） | CLOSED |
| H-006 | Supplemental Historical Replication | CLOSED |
| H-007 | Momentum Hypothesis | CLOSED |
| H-008 | Round A（T1） | CLOSED |
| H-009 | Round A（T2） | CLOSED |
| H-010 | Round B′-1 | CLOSED |
| H-011 | Round B′-2 | OPEN |
| H-012 | Round B′-4 | CLOSED |
| H-013 | Monetizability 1A | CLOSED |
| H-014 | Monetizability 1B | CLOSED |
| H-015 | Monetizability 1C | OPEN |
| H-016 | Economic Edge Stage 2（carry） | CLOSED |
| H-017 | Economic Edge Stage 3-4（volume） | CLOSED |
| H-018 | Economic Edge Route C | OPEN |
| H-019 | Exogenous Stage A | OPEN |
| H-020 | Exogenous Stage C（macro surprise） | CLOSED |
| H-021 | Exogenous Route D（COT） | CLOSED |
| H-022 | Model-learning（#479） | CLOSED |
| H-023 | Track 1（#481/#482） | CLOSED |
| H-024 | Track 1 benchmark の事後観察（通貨レベル reversal） | CLOSED |

**一時停止時点で OPEN の 4 件（H-011、H-015、H-018、H-019）**: 本記録は ledger の status 文を変更しない。いずれも expected-return
source ではなく（microstructure の方向整合、volatility feature、cost 優位の無い exogenous 構造、向ける先の無い forward-known anchor）、
停止中は追求しない。OPEN であることは再開の根拠にならない（RC-1、RC-9）。H-011 は retrace geometry の検定で、その family は
#470 で `RETRACE_GEOMETRY_FAMILY_DROPPED_AFTER_CLEAN_RETEST` になっている（ledger の OPEN 文はそれ以前のもの）。H-015 の
volatility feature は §5 の volatility filter による救済と同じ中身で、その用途には使えない（`裁定から導出`）。

### 10.2 phase 記録の status（master 上の正本）

| PR | phase | status |
| --- | --- | --- |
| #464 | Exploratory Round 1 | M15 判断スケールで edge なし（H-001〜H-004） |
| #465 | Exploratory Round 2 | `MULTI_DAY_REVERSAL_UNRESOLVED_INSUFFICIENT_DETECTION_POWER` |
| #466 | Supplemental replication | `MULTI_DAY_REVERSAL_FAILED_SUPPLEMENTAL_HISTORY_REPLICATION` |
| #467 | Momentum hypothesis | `MULTI_DAY_MOMENTUM_UNRESOLVED_IN_FRESH_EXPLORATORY_HISTORY`、`MULTI_DAY_REVERSAL_FAMILY_DROPPED_FROM_ACTIVE_EXPLORATORY_RESEARCH` |
| #468 | Round A | `TRACK_A_RESEARCH_PROGRAM_ROUND_A_COMPLETED` |
| #469 | Round B′ | `TRACK_A_RESEARCH_PROGRAM_ROUND_B_PRIME_COMPLETED`、`PRICE_PATH_STRUCTURE_SURVIVES_NULL_CONTROL`、`MONTHLY_TSMOM_NOT_SUPPORTED_IN_EXISTING_PRICE_HISTORY` |
| #470 | Monetizability | `PRICE_PATH_STRUCTURE_REAL_BUT_NOT_ECONOMICALLY_HARVESTABLE`、`RETRACE_GEOMETRY_FAMILY_DROPPED_AFTER_CLEAN_RETEST` |
| #471 | Economic edge source expansion | `ECONOMIC_EDGE_SOURCE_NOT_FOUND_EXOGENOUS_MOVEMENT_STRUCTURE_ESTABLISHED`、`CARRY_EDGE_NOT_SUPPORTED` |
| #472 | Exogenous directional information | `EXOGENOUS_EXPECTED_RETURN_SOURCE_NOT_FOUND` |
| #474 | FX spot frontier unit audit | `UNIT_CONSISTENCY_VERIFIED`、`PRIOR_FRONTIER_CONCLUSION_CHANGED_RESEARCH_NOT_STARTED` |
| #475 | Track 3 execution frontier（#480 の Track 3 とは別） | `SIMULATED_EXECUTION_COST_BOUND_ESTABLISHED`、`OFFLINE_EXECUTION_FRONTIER_ESTIMATED`、`CLOCK_STRUCTURE_NOT_DECISION_GRADE_AT_CURRENT_EXECUTION_FRONTIER`、`CLOCK_STRUCTURE_TRACK_V1_WITHDRAWN_AFTER_UNIT_CORRECTION`、`LONDON_FIX_NOT_DECISION_GRADE_AT_CURRENT_EXECUTION_FRONTIER` |
| #476 | Feasibility Gate v2 | `FEASIBILITY_GATE_V2_PROSPECTIVE_ONLY`、`FEASIBILITY_GATE_V1_LEGACY_FROZEN` |
| #477 | Track 2 non-USD surprise | `NON_USD_SURPRISE_DATA_NOT_DECISION_GRADE_SKIP` |
| #478 | Decision-grade inventory | `CURRENT_SEEN_DATA_FX_RESEARCH_SPACE_EXHAUSTED` |
| #479 | Model-learning | `MODEL_LEARNING_NOT_DECISION_GRADE_UNDER_CURRENT_DEVELOPMENT_GATE` |
| #480 | Profit architecture redesign | `PROFIT_ARCHITECTURE_REDESIGN_ASSESSED` |
| #481/#482 | Track 1 | `CONTINUOUS_CURRENCY_PORTFOLIO_ARCHITECTURE_NOT_SUPPORTED_IN_SEEN_DEVELOPMENT` |

**残った durable な engineering output**（alpha ではない）: 実測 execution cost bound（pair 往復 2.58 bp は実測 2 値
2.6902 / 2.4660 の中点）、unit-consistent な feasibility gate、signal-blind な capacity / search budget、turnover ∝ √(1−ρ) と
band の較正、差分課金の portfolio accounting、事前登録の凍結・実行束縛・変異テストの手順。

### 10.3 データの状態（一時停止時点）

| span | 状態 |
| --- | --- |
| seen: `2021-04-26 … 2025-12-28`（3 panel） | `EXPLORATORY_SEEN_DATA`。判断の証拠にはならない |
| fresh_pool `2016-06-02 … 2021-04-25` | never read |
| historical_oos（`2025-12-29` 以降） | one decoded row per pair; no value reached an output |
| dead_window | never read |
| forward_epoch | never read |

- 状態の文言は `scripts/research/model_learning/__init__.py` の `PROTECTED_SPANS` の写しである。historical OOS について
  "never read" / "pristine" は主張しない。fresh pool は完全凍結した候補の one-shot 独立評価用、forward epoch は Formal Confirmation 用。
- **汚染記録の抜け（開示）**: `SEEN_SPANS[*]["hypotheses_run_here"]` は H-022 までで、Track 1 が 3 つの seen span すべてで
  評価した H-023・H-024 を含まない。同ファイルは Track 1 の凍結 hash の対象なので、変更すると凍結記録の再現性テストが壊れる。
  そのため本 PR では変更せず、ここに記録する。

## 11. 一時停止の範囲

**確認待ちの行の効力**: 出典が `起草` または `裁定から導出` の停止行は、確認されるまで**暫定的に拘束する**（厳しい方の読み）。
確認待ちの「停止しないもの」の行は、許可を**広げない**。

**停止するもの**（明示の再開決定まで）

| 活動 | 出典 |
| --- | --- |
| 新しい alpha 探索（FX spot active-alpha research） | 裁定 |
| 新しい alpha 仮説の事前登録（seen data・新しい外部データのどちらでも） | 起草 |
| Red 承認なしの seen data 上の alpha 目的の実行 | 既存規則 |
| 再開決定（RC-9）の前の、Red 承認を得た alpha 目的の実行や fresh pool・forward epoch の読み取り | 裁定から導出 |
| Track 3 overlay（#480 の event / volatility exposure overlay） | 裁定 |
| complex ML | 裁定 |
| 停止中の track（#480 の Track 3 overlay、complex ML など）の実装や学習 pipeline の作成（市場データを使うかどうかを問わない） | 起草 |
| 停止中の track の部品を「engineering」として作り seen data で検証すること（方向を持たない volatility 予測器、event anchor、overlay 部品など） | 起草 |
| コスト・band・netting を測り直して閉じた判定の net を再計算すること | 起草 |
| commit 済み artefact を再分析して新しい alpha の主張を導くこと | 起草 |
| Red 承認なしの fresh pool・forward epoch の読み取り | 既存規則 |
| paper-forward、demo / live 注文、broker 認証 API | 既存規則 |
| 閉鎖・隣接 family の再事前登録や救済 | 裁定から導出 |

**停止しないもの**（研究状態を変えない）

| 活動 | 出典 |
| --- | --- |
| 既存記録の保守（誤りの訂正、リンク・SHA の更新） | 起草 |
| テスト・lint・CI の保守 | 起草 |
| 市場データの読み取りも alpha の主張も伴わず、停止中の track の実装でもない engineering | 起草 |

## 12. 再開条件

RC-2〜RC-4 は**再開後の作業の順序**を定めるもので、停止中に満たすべき前提ではない（停止中は事前登録も実行もしないため）。
**どの条件も、それが記録上満たされたことだけでは再開にならない**（RC-1、RC-9）。確認待ちの条件は、確認までは暫定的に適用する。

| ID | 条件 | 出典 |
| --- | --- | --- |
| RC-1 | 実データの読み取りや実行を伴う再開は、operation・span・pairs・timeframe・承認 head を名指しした Human + ChatGPT の明示の承認を実行前に要する。記録された status・gate・文書・この表の条件がすべて揃ったことはそれに代わらない | 既存規則 |
| RC-2 | 再開後の順序: 正の base expected-return source を事前登録した検定で先に確立し、efficiency 機構・overlay・複雑さはその後にしか載せない | 裁定から導出 |
| RC-3 | 再開後の順序: #480 の Track 3 overlay は正の base edge を持つ core にのみ適用し、救済には使わない | 裁定から導出 |
| RC-4 | 再開後の順序: complex ML は、単純な architecture の正の base evidence がある場合にのみ検討する | 裁定から導出 |
| RC-5 | 仮説は ledger の閉鎖 family と隣接 family の外にあり、novelty boundary を結果を見る前に書く。post-hoc 観察は昇格しない。隣接 = 同じ単位（通貨または pair）で、過去リターンに基づく同じ信号を horizon・符号・閾値だけ変えたもの | 起草 |
| RC-6 | seen data の見直しではなく新しい情報に基づく: 独立な情報源、蓄積した forward data、または完全凍結した候補に対する fresh pool の one-shot 使用（それ自体の Red 承認下）。Track A の結果は再開決定の根拠にならない | 起草 |
| RC-7 | 結果を読む前に Feasibility Gate v2（#476、凍結済みの閾値、緩和なし）と signal-blind な capacity・search budget を計算して通す | 起草 |
| RC-8 | tail concentration は hard kill ではなく adversarial diagnostic として報告する | 裁定（推奨） |
| RC-9 | 読み取りを伴わない再開（新しい仮説の事前登録の作成など）を含め、一時停止の解除は仮説を名指しした Human + ChatGPT の明示の決定による | 裁定から導出 |
| RC-10 | tail concentration の降格は、tail 条項も発火して閉じた family（H-021、H-022 など）を再び開かない | 裁定から導出 |

RC-1 の根拠（既存規則）: CLAUDE.md の「A real-data read is Red … an act, not a document state」と「no recorded grant, passed gate or
fully-ticked checklist supplies it」、自律開発方針の「A Track A run is Red」。これが拘束するのは**実データの読み取りと実行**に限られる。
読み取りを伴わない再開（事前登録の作成など）と、仮説の名指しは、既存規則ではなく本裁定からの導出（RC-9）である。

## 13. Human + ChatGPT の判断事項

1. 本 PR の merge 承認。
2. 出典が `起草` と `裁定から導出` の項目の確定（§5・§9・§11 の該当行、§12 の RC-2〜RC-7・RC-9・RC-10）。**裁定本文が §9 で途切れているため。**
   RC-7 について: #476 の Gate v2 を緩和なしで課すと、#478 の結論（有効 3.488 年が必要でパネル長を超える）により seen data 上の
   どの設計も通らない。それが意図どおりか（= 新しいデータを待つ）を確認されたい。
3. 「temporal co…」の語の確定。
4. H-024 の範囲が 5・20・60 日以外の horizon に及ぶか（§7）。
5. `記録用` token（`FX_SPOT_ACTIVE_ALPHA_RESEARCH_PAUSED`、`NOT_AUTHORISED_NO_POSITIVE_BASE_EVIDENCE`、
   `COMPLEXITY_REQUIRES_POSITIVE_BASE_EVIDENCE`）の名称の承認。
6. 未 merge の #473（expectation benchmark）の扱いと、それが閉じる survey-consensus family を ledger に入れるか。
7. **Track 1 事前登録が開示した tail kill の見逃し（高 Sharpe の lottery 型 book）を受け入れるか。** §8 の降格はこれを解消しない。
8. 最小研究 gate §8.11.2(1)（Track A の結果を決定の証拠にしない）と、本文書 §3 が停止の理由として Track A の数値を記録することの関係。
9. OPEN のまま停止した ledger 4 件（H-011、H-015、H-018、H-019）を、停止に合わせて閉じるか。本記録は status 文を変えていない。
