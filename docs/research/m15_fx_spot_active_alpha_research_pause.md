# FX Spot Active-Alpha Research — 研究結果の整理と一時停止

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `PRODUCTION_READINESS_NOT_CLAIMED`

Status: **`FX_SPOT_ACTIVE_ALPHA_RESEARCH_PAUSED`**（Human + ChatGPT 裁定、2026-09-14）

本文書は、FX spot の active-alpha 研究を一時停止する時点での**研究状態の正本**である。機械可読な写しは
`scripts/research/programme_status.py`、仮説ごとの記録は `scripts/research/round_a/ledger.py`（H-001〜H-024）。
三者の一致は `tests/research/test_programme_status.py` が固定する。

> ⚠ **裁定本文の欠落について。** 受領した裁定は §9「Tail diagnostics」の途中（"temporal co"）で途切れている。
> §1〜§8 と §9 の冒頭は裁定どおりに記録した。§9 の残りと、再開条件のうち裁定本文から直接導けない項目は
> **起草**として区別して記録し（§11・§12）、Human + ChatGPT の確認で確定する。

---

## 1. 裁定

- Track 1 の正式 status は **`CONTINUOUS_CURRENCY_PORTFOLIO_ARCHITECTURE_NOT_SUPPORTED_IN_SEEN_DEVELOPMENT`** とする。
- 意味：今回事前登録した continuous currency-level expected-return portfolio architecture は、seen development
  data 上で経済的に支持されなかった。
- **`FX_HAS_NO_EDGE` ではない。** FX spot に edge が無いことは主張しない。
- 次の作業は新しい alpha 探索ではない。研究結果を正本として整理し、FX spot active-alpha research を一時停止し、
  再開条件を固定する。

## 2. Merge 記録

| PR | 内容 | merge commit |
| --- | --- | --- |
| #478 | Pass-region preflight + decision-grade inventory | `a0780e3` |
| #479 | Model-learning 研究（Case C、gate に範囲限定） | `3b4d0a9` |
| #480 | Profit architecture redesign | `3bbb7f5` |
| #481 | Track 1 事前登録 + 実装（凍結 hash `aa0888089e4d…`） | `e13dba2` |
| #482 | Track 1 開発実行 + 結果 | `a98fbc6` |

stack は #481 → #482 の順に解消した（#482 の base 追随 merge は tree hash が承認時と同一）。最終 master CI は green。

**未 merge の研究 PR**: #473（expectation benchmark、survey consensus の検出力ある null）は open のままで、
結果は master に無い。したがって本文書では**正本として引用しない**。扱いは Human + ChatGPT の判断事項。

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
| cost stress | ×1.5 で −1.03、×2 で −1.21（悪化） |
| currency breadth | 弱い（最大の正の通貨 GBP を除くと gross −18.9%、USD を除いても −6.4%） |
| 単純な 20 日 reversal 型 benchmark との日次 P&L 相関 | 約 0.64（primary はその rule より悪い） |

**コストだけが原因ではない。** gross の時点で負である（コストは損失の約 44%）。

詳細: `docs/research/m15_track1_continuous_portfolio_results.md`、記録 `artifacts/research/continuous_portfolio/development.json`。

## 4. Efficiency bundle の扱い

- no-trade band・部分 rebalance 等は **`TURNOVER_REDUCTION_MECHANISM_SUPPORTED`**（engineering result）として残す。
- **`ALPHA_SUPPORTED` とはしない。**
- turnover は約 42.8（bundle なし）→ 約 25.6 RT/年/単位 gross に下がったが、gross expected return は負だった。
- 原則: **`EFFICIENCY_CANNOT_RESCUE_NEGATIVE_EXPECTED_RETURN`**（efficiency cannot rescue negative expected return）。

## 5. Track 3（event / volatility exposure overlay）

- status: **`NOT_STARTED_BASE_EDGE_REQUIRED`**。進まない。理由は core の expected-return source が正でないこと。
- **禁止**（救済としての使用）: event filter、volatility filter、regime filter、horizon 変更。

## 6. Complex ML

- status: **`NOT_AUTHORISED_NO_POSITIVE_BASE_EVIDENCE`**。今回進まない。
- 未承認: LightGBM expansion、nonlinear ML、HMM、neural networks、representation learning、complex ensemble。
- 理由: 単純な architecture が gross 負・時間的に不安定・benchmark に対する優位なしで、複雑さの追加を合理化する
  正の base evidence が無い。原則 **`COMPLEXITY_REQUIRES_POSITIVE_BASE_EVIDENCE`**。

## 7. 60 日 reversal などの post-hoc 観察

- 60 日 reversal の +0.52（および 20 日 reversal の +0.31）を候補に昇格しない。
- status: **`POST_HOC_EXPLORATORY_NON_DECISION_BEARING`**（ledger H-024）。
- 理由: 閉鎖済み・隣接 family（C08 persistence の符号反転、dropped の multi-day reversal family に隣接）、
  標準誤差 約 0.58、6 本の unfitted rule の中の最大値、過去の reversal 証拠と整合する確認ではない。
- **再事前登録は禁止。** 原則 **`A_FAILED_RULE_IS_NOT_AN_INVERTED_RULE`**。

## 8. Tail diagnostic policy（将来に向けた方針）

- 今回の Case C の判定は**変更しない**。過去の事前登録・判定も**書き換えない**。
- 既存の tail kill は、「少数の大きな正の日に依存する strategy」を機械的に kill すると、本物の positive-skew strategy
  まで偽陰性にしうる（Track 1 の事前登録 §14 が合成 MC で開示した通り）。
- したがって将来の方針として、**tail concentration は hard kill から adversarial diagnostic へ降格する**:
  **`TAIL_CONCENTRATION_HARD_KILL_DEMOTED_TO_ADVERSARIAL_DIAGNOSTIC`**（prospective のみ）。

## 9. Tail diagnostics（再開時の最低限）

| 診断 | 区分 |
| --- | --- |
| top 1 day contribution | 裁定 |
| top 5 days contribution | 裁定 |
| top 10 days contribution | 裁定 |
| largest loss days | 裁定 |
| top days 除外後の符号 | 裁定 |
| temporal concentration（top days の時間的集中） | 裁定（本文は "temporal co" で途切れ、語の補完のみ） |
| top / worst days の通貨・pair 集中 | 起草 |
| top days と予定イベントの重なり | 起草 |
| 日次歪度・超過尖度 | 起草 |
| ±3 robust σ 内の日の収益 | 起草 |

## 10. 研究プログラム全体の状態（一時停止時点）

### 10.1 仮説 ledger（`scripts/research/round_a/ledger.py`）

24 件: CLOSED 20、OPEN 4、事前登録 18、post-hoc 6。

| ID | round | status（ledger の記載の要約） |
| --- | --- | --- |
| H-001〜H-004 | Exploratory Round 1 | CLOSED |
| H-005 | Exploratory Round 2（multi-day reversal） | CLOSED |
| H-006 | Supplemental Historical Replication | CLOSED — family dropped from active research |
| H-007 | Momentum Hypothesis | CLOSED |
| H-008、H-009 | Round A（T1、T2） | CLOSED |
| H-010 | Round B′-1 | CLOSED — real but unharvestable microstructure |
| **H-011** | Round B′-2 | **OPEN**（H-010 と方向整合、独立には未確立） |
| H-012 | Round B′-4 | CLOSED |
| H-013 | Monetizability 1A | CLOSED |
| H-014 | Monetizability 1B | CLOSED（固定 horizon・線形 selector の範囲で） |
| **H-015** | Monetizability 1C | **OPEN**（volatility feature 候補、方向については何も言わない） |
| H-016 | Economic Edge Stage 2（carry） | CLOSED — G10 carry premium は short-yen trade |
| H-017 | Economic Edge Stage 3-4（volume） | CLOSED |
| **H-018** | Economic Edge Route C | **OPEN**（cost 優位も expected-return source も無い exogenous 構造） |
| **H-019** | Exogenous Stage A | **OPEN**（forward-known な anchor、向ける先が無い） |
| H-020 | Exogenous Stage C（macro surprise） | CLOSED |
| H-021 | Exogenous Route D（COT） | CLOSED |
| H-022 | Model-learning（#479） | CLOSED — `MODEL_LEARNING_NOT_DECISION_GRADE_UNDER_CURRENT_DEVELOPMENT_GATE` |
| **H-023** | Track 1（#481/#482） | CLOSED — `CONTINUOUS_CURRENCY_PORTFOLIO_ARCHITECTURE_NOT_SUPPORTED_IN_SEEN_DEVELOPMENT` |
| **H-024** | Track 1 benchmark の事後観察 | CLOSED — `POST_HOC_EXPLORATORY_NON_DECISION_BEARING` |

**OPEN の 4 件（H-011、H-015、H-018、H-019）は一時停止時点の状態で凍結する**: 追求しない、閉じない、書き換えない。
いずれも expected-return source ではない（microstructure の方向整合、volatility feature、exogenous 構造、
forward-known anchor）。

### 10.2 phase 記録の status（master 上の正本）

| PR | phase | status |
| --- | --- | --- |
| #464 | Exploratory Round 1 | M15 判断スケールで edge なし（H-001〜H-004） |
| #465 | Exploratory Round 2 | `MULTI_DAY_REVERSAL_UNRESOLVED_INSUFFICIENT_DETECTION_POWER` |
| #466 | Supplemental replication | `MULTI_DAY_REVERSAL_FAILED_SUPPLEMENTAL_HISTORY_REPLICATION` |
| #467 | Momentum hypothesis | `MULTI_DAY_MOMENTUM_UNRESOLVED_IN_FRESH_EXPLORATORY_HISTORY`、`MULTI_DAY_REVERSAL_FAMILY_DROPPED_FROM_ACTIVE_EXPLORATORY_RESEARCH` |
| #468 | Round A | `TRACK_A_RESEARCH_PROGRAM_ROUND_A_COMPLETED` |
| #469 | Round B′ | `PRICE_PATH_STRUCTURE_SURVIVES_NULL_CONTROL`、`MONTHLY_TSMOM_NOT_SUPPORTED_IN_EXISTING_PRICE_HISTORY` |
| #470 | Monetizability | `RETRACE_GEOMETRY_FAMILY_DROPPED_AFTER_CLEAN_RETEST` |
| #471 | Economic edge source expansion | `CARRY_EDGE_NOT_SUPPORTED` |
| #472 | Exogenous directional information | `EXOGENOUS_EXPECTED_RETURN_SOURCE_NOT_FOUND` |
| #474 | FX spot frontier unit audit | `UNIT_CONSISTENCY_VERIFIED`、`PRIOR_FRONTIER_CONCLUSION_CHANGED_RESEARCH_NOT_STARTED` |
| #475 | Track 3 execution frontier | `SIMULATED_EXECUTION_COST_BOUND_ESTABLISHED`、`OFFLINE_EXECUTION_FRONTIER_ESTIMATED`、`CLOCK_STRUCTURE_NOT_DECISION_GRADE_AT_CURRENT_EXECUTION_FRONTIER`、`CLOCK_STRUCTURE_TRACK_V1_WITHDRAWN_AFTER_UNIT_CORRECTION`、`LONDON_FIX_NOT_DECISION_GRADE_AT_CURRENT_EXECUTION_FRONTIER` |
| #476 | Feasibility Gate v2 | `FEASIBILITY_GATE_V2_PROSPECTIVE_ONLY` |
| #477 | Track 2 non-USD surprise | `NON_USD_SURPRISE_DATA_NOT_DECISION_GRADE_SKIP` |
| #478 | Decision-grade inventory | `CURRENT_SEEN_DATA_FX_RESEARCH_SPACE_EXHAUSTED` |
| #479 | Model-learning | `MODEL_LEARNING_NOT_DECISION_GRADE_UNDER_CURRENT_DEVELOPMENT_GATE` |
| #480 | Profit architecture redesign | `PROFIT_ARCHITECTURE_REDESIGN_ASSESSED` |
| #481/#482 | Track 1 | `CONTINUOUS_CURRENCY_PORTFOLIO_ARCHITECTURE_NOT_SUPPORTED_IN_SEEN_DEVELOPMENT` |

**残った durable な engineering output**（alpha ではない）: 実測 execution cost bound（pair 往復 2.58 bp）、
unit-consistent な feasibility gate、signal-blind な capacity / search budget、turnover ∝ √(1−ρ) と band の較正、
差分課金の portfolio accounting、事前登録の凍結・実行束縛・変異テストの手順。

### 10.3 データの状態（一時停止時点）

| span | 状態 |
| --- | --- |
| seen: `2021-04-26 … 2025-12-28`（3 panel） | `EXPLORATORY_SEEN_DATA`。判断の証拠にはならない |
| fresh pool `2016-06-02 … 2021-04-25` | **never read**。完全凍結した候補の one-shot 独立評価用に保留 |
| historical OOS（`2025-12-29` 以降） | **one decoded row per pair; no value reached an output**（"never read" / "pristine" は主張しない） |
| dead window | never read |
| forward epoch | never read。Formal Confirmation 用 |

## 11. 一時停止の範囲

**停止するもの**（明示の再開決定まで）:

- 新しい alpha 仮説の探索、事前登録、seen data 上の alpha 目的の実行
- Track 3 overlay、complex ML
- fresh pool・forward epoch の読み取り、paper-forward、demo / live
- 閉鎖・隣接 family（H-024 の post-hoc reversal を含む）の再事前登録や救済

**停止しないもの**: 既存記録の保守（誤りの訂正、リンク・SHA の更新）、テスト・lint・CI、alpha 探索を伴わない
engineering（Green / Amber の通常作業）。いずれも研究状態を変えない。

## 12. 再開条件

**区分**: 「裁定」は本裁定 §4〜§8 から直接導ける条件、「起草」は裁定本文の欠落部分を補うための提案で、
Human + ChatGPT の確認により確定する。

| ID | 条件 | 区分 |
| --- | --- | --- |
| RC-1 | 再開は Human + ChatGPT の**明示の決定**によってのみ行う。仮説・データ・操作・承認 head を名指しする。記録された status・gate・文書はそれに代わらない | 起草 |
| RC-2 | **正の base expected-return source を先に確立する**（事前登録した検定で）。efficiency 機構・overlay・複雑さはその上にしか載せない | 裁定 |
| RC-3 | Track 3 overlay は正の base edge を持つ core にのみ適用し、救済には使わない | 裁定 |
| RC-4 | complex ML は、単純な architecture が機能するという正の base evidence と、複雑さが何を足すかの説明がある場合にのみ | 裁定 |
| RC-5 | ledger の閉鎖・隣接 family の外にある仮説で、novelty boundary を結果を見る前に書く。post-hoc 観察は昇格しない | 起草 |
| RC-6 | seen data を見直すのではなく**新しい情報**: 独立な情報源、蓄積した forward data、または完全凍結した候補に対する fresh pool の one-shot 使用（それ自体の Red 承認下） | 起草 |
| RC-7 | signal-blind な feasibility（検出力・capacity・search budget）を、結果を読む前に計算して通す | 起草 |
| RC-8 | tail concentration は hard kill ではなく adversarial diagnostic として報告する（§9） | 裁定 |

## 13. Human + ChatGPT の判断事項

1. 本 PR の merge 承認。
2. §9 の起草 4 項目と、§12 の起草 4 条件（RC-1、RC-5、RC-6、RC-7）の確定。**裁定本文が §9 で途切れているため。**
3. 未 merge の #473（expectation benchmark）の扱い。
4. Track 1 の事前登録で開示した tail kill の見逃し（高 Sharpe の lottery 型 book）は、§8 の方針で将来は
   diagnostic 化されるため、追加の判断は不要と考える（過去の判定は不変）。
