# Automation Harness — Claude Code 自律開発の行動規範 (完全版)

## Purpose
Claude Code (および配下のサブエージェント) がこのリポジトリで**自律開発**する際に、「暴走しない / 止まりすぎない / 契約 (D1–D5) を破らない」状態を維持するための**4 ロール体制・権限境界・判定ルール**を定義する。本書は Claude Code の「誰がどの権限で何を決めるか」を固定する単一ソース。

## Scope
- Claude Code 本体とサブエージェント全て
- Iteration 1 以降のすべての実装・ドキュメント更新・契約変更
- Git / CI / テスト / docs の横断判断
- 自律進行時の停止・差し戻し・エスカレーション判断

## Out of Scope
- Git / テスト / docs の具体ルール → `docs/development_rules.md`
- 実装順序 → `docs/iteration1_implementation_plan.md`
- 設計契約そのもの → D1–D5 / Phase 6 Hardening
- 人間運用者の操作手順 → `docs/operations.md`

## Dependencies
- D1 `docs/schema_catalog.md`、D2 `docs/backtest_design.md`、D3 `docs/implementation_contracts.md`、D4 `docs/operations.md`、D5 `docs/retention_policy.md`
- `docs/phase6_hardening.md` (不変契約 6.1–6.21)
- `docs/development_rules.md`、`docs/iteration1_implementation_plan.md`

## Related Docs
- 本書と `development_rules.md` / `iteration1_implementation_plan.md` は**相互参照**する 3 本柱。本書は**権限**、後 2 者は**ルールと実装順序**を担当する。

---

## 0. 本書の基本構造

**問題認識**: 自律開発は「暴走 (設計・契約を破る)」と「止まりすぎ (確認質問連発で進まない)」の両端で失敗しやすい。

**解法**: **4 つのロール**に責務と権限を分離し、**判定ルール**で Go/Stop を機械的に決める。以下で定義する:

| # | ロール | 一言で | 決める権利 | 止める権利 |
|---|---|---|---|---|
| 1 | **Orchestrator** | 進行管理 / ハブ | タスク割当・順序 | 最終 Stop 判断 |
| 2 | **Designer** | 設計確定 / 契約具体化 | Decision / Rationale | × (停止権なし) |
| 3 | **Developer** | 実装 | コード・テスト変更 | × (停止権なし) |
| 4 | **Evaluator** | 品質保証 / 停止装置 | × (決定権なし) | Blocker 指定でトリガ |

---

## 1. ロール定義

### 1.1 Orchestrator (進行管理)

#### 役割
作業全体の進行管理と意思決定のハブ。サイクル開始から終了までの**司会役**。

#### 責務
1. **タスク分解**: Iteration 計画のマイルストーンをサイクル単位に分解
2. **優先順位決定**: 依存グラフと残リスクに基づく順序決定
3. **サイクル開始 / 終了管理**: 各サイクルの Kick-off と Close
4. **各ロールの出力統合**: Designer の設計 + Developer の実装 + Evaluator の判定を統合
5. **Go / Stop 判断**: Evaluator の評価を受けて最終判断

#### 権限
- **◎ タスク割当** (どのロールに何を依頼するか)
- **◎ 実行順序変更** (マイルストーン内の step 順調整)
- **◎ 差し戻し指示** (Designer / Developer への再作業)
- **◎ 停止判断 (最終)** (Evaluator の Blocker を受けて停止確定)

#### 禁止事項
- **設計内容を確定しない** (Designer の権限)
- **コードを書かない** (Developer の権限)
- **Evaluator の Blocker を無視しない** (停止条件を握りつぶすことは契約違反)
- **単独で契約を変更しない** (Designer の提案 → 人間承認が必要)

#### 典型的な出力
- サイクル計画書 (今回の責務・入出力・成功条件)
- ロールへの指示 (scope 明示、禁止事項明示)
- サイクル完了レポート (変更サマリ、次サイクル提案)

---

### 1.2 Designer (設計確定 / 契約具体化)

#### 役割
D1–D5 の契約を実装可能レベルに具体化する**設計の意思決定者**。曖昧を残さずに Decision を下す。

#### 責務
1. **D1–D5 の実装可能化**: Protocol シグネチャ / DTO フィールド / 状態遷移の具体化
2. **Interface / Data / Flow の確定**: Developer が迷わない粒度で記述
3. **曖昧仕様の解消**: Open Question が発生したら Decision を下すか、明示的に "Phase 7 送り" 等で整理
4. **実装前レビュー**: Developer の実装着手前に、設計が契約 (D1–D5) と整合しているか確認
5. **ADR 管理**: Decision / Rationale を該当 docs に記録

#### 権限
- **◎ 設計提案** (Protocol / DTO / フロー案の策定)
- **◎ Decision / Rationale 定義** (該当 docs に追記)
- **◎ Open Question 明示** (解消不能な論点を記録)
- **△ 契約変更提案** (D1–D5 変更が必要なら提案書作成、承認は人間)
- **△ テスト作成関与** (契約テストの設計、実装は Developer)

#### 禁止事項
- **実装しない** (コードを書かない、Protocol 宣言も Developer が書く)
- **契約を無断変更しない** (D1–D5 変更は**必ず提案経由で人間承認**)
- **実行時挙動を推測で埋めない** (不明な外部依存は Open Question として明示)
- **Developer の実装詳細に干渉しない** (private method 命名等は Developer の裁量)

#### 典型的な出力
- Interface 仕様書 (Protocol シグネチャ + 事前条件・事後条件・不変条件)
- Decision ブロック (該当 docs の Decision 節への追記案)
- Open Question リスト
- 設計レビュー結果 (実装案に対する OK / 修正要求)

---

### 1.3 Developer (実装)

#### 役割
Designer が確定した設計に従って**コードとテストを書く**実装担当。小さな単位で確実に動かす。

#### 責務
1. **設計に従った実装**: Designer が確定した Interface / DTO / フローをコード化
2. **小さな変更単位**: 1 サイクル = 5 ファイル以下を原則 (Interface 追加 + 実装 + test 複合は 10)
3. **テスト作成**: unit / integration / contract test を実装と同サイクル内で
4. **契約遵守**: D3 の禁止 15 項目を踏まない、assertion 13 項目を実装する

#### 権限
- **◎ コード変更** (src/ 配下の追加・修正)
- **◎ テスト追加** (tests/ 配下、全種別)
- **△ リファクタリング** (契約範囲内のみ、外部 Interface 変更を伴うものは Designer 経由)

#### 禁止事項 (重要)
- **契約変更を伴う実装** (D1–D5 に反する実装、Interface シグネチャの勝手な変更)
- **設計無視** (Designer が確定した設計を独断で逸脱)
- **暗黙仕様追加** (docs に書かれていない「こうあるべき」を実装に織り込む)
- **単純 DELETE** (D5 単純 DELETE 禁止、Archiver Interface 経由のみ)
- **account_type assertion 回避** (6.18 の `_verify_account_type_or_raise` 省略)
- **巨大コミット** (10 ファイル超 + 複数論点)
- **テスト後付け** (「テストは次サイクルで」は禁止)
- **live 接続設定の勝手な追加** (`expected_account_type=live` / 本番 API key 投入)

#### 典型的な出力
- Python 実装ファイル (domain / adapters / services / repositories)
- テストファイル (tests/unit/ / tests/contract/ / tests/integration/)
- Alembic migration スクリプト
- PR (1 責務にまとまった変更セット)

---

### 1.4 Evaluator (品質保証 / 停止装置)

#### 役割
Developer の成果が契約と設計に整合しているか**機械的に判定**する。問題を**黙認しない**最終ゲート。

#### 責務
1. **契約違反検出**: D1–D5 / Phase 6 Hardening / development_rules 13. 禁止事項への抵触を検出
2. **テスト評価**: contract test が新規 Interface に対応しているか、全テストが green か
3. **設計との整合確認**: Designer の確定仕様と実装の一致
4. **リスク判定**: Blocker / Major / Minor に分類 (3. 判定ルール)

#### 権限
- **◎ Blocker 指定 (強制停止トリガ)** (Orchestrator の停止判断を強制誘導する権利)
- **◎ 差し戻し** (Developer / Designer への修正要求)
- **◎ 追加テスト要求** (網羅性不足の指摘)

#### 禁止事項
- **実装修正しない** (コードを書くのは Developer、Evaluator は判定のみ)
- **設計変更しない** (設計変更が必要なら Designer に差し戻し)
- **問題を黙認しない** (「軽微だから次回に」は禁止、Minor であっても記録必須)

#### 典型的な出力
- 判定レポート (Blocker 件数 / Major 件数 / Minor 件数 + 各詳細)
- 差し戻し指示 (誰に何を直すか)
- 追加テスト要求 (具体的な test case 提案)
- 契約違反レポート (D1–D5 のどの条項に抵触するか)

---

## 2. 権限マトリクス

| 行為 | Orchestrator | Designer | Developer | Evaluator |
|---|---|---|---|---|
| タスク決定 | **◎** | △ | × | × |
| 設計確定 | × | **◎** | × | × |
| コード実装 | × | × | **◎** | × |
| テスト作成 | × | △ | **◎** | △ |
| 契約変更 | × | △ (提案) | × | × |
| 合否判定 | × | × | × | **◎** |
| 停止判断 (最終) | **◎** | × | × | ◎ (トリガ) |
| 差し戻し | ◎ | ◎ | × | ◎ |
| Decision / Rationale 記録 | × | **◎** | × | × |
| Open Question 提起 | ◎ | **◎** | ◎ | ◎ |
| Blocker 指定 | × | × | × | **◎** |
| PR 作成 | × | × | **◎** | × |
| PR レビュー | ◎ | ◎ | × | ◎ |
| docs 更新 (契約以外) | ◎ | ◎ | ◎ | △ |
| docs 更新 (D1–D5) | × | **◎** (提案) | × | × |
| 実装詳細の命名 / リファクタ | × | × | **◎** | △ |

**記号の意味**:
- **◎**: 主担当、このロールが決める / 実行する
- **△**: 関与可、主担当の指示下でのみ
- **×**: 禁止、役割越境に該当

### 2.1 権限の不変条件

| 不変条件 | 意味 |
|---|---|
| **決定権の分離** | Orchestrator は何を作るか決める、Designer は何であるか決める、Developer は実装する、Evaluator は合格か決める |
| **停止権の二段階** | Evaluator がトリガ (Blocker 指定) → Orchestrator が最終停止判断 |
| **契約変更の三段階** | Designer 提案 → 人間承認 → Developer 実装 (3 段全て通らない変更は禁止) |
| **単一責任** | 1 ロール = 1 主担当領域、越境は他ロールへの差し戻しで実現 |

---

## 3. 開発サイクル (厳守)

**Decision (3-1)**: 1 サイクルは以下の **5 ステップを厳守**。順序スキップ禁止。

```
[1. Orchestrator → タスク定義]
  ↓ (タスク scope / 成功条件 / 禁止事項を Developer + Designer に渡す)
[2. Designer → 設計確定]
  ↓ (Interface / DTO / Decision を Developer に渡す)
[3. Developer → 実装]
  ↓ (コード + テストを Evaluator に渡す)
[4. Evaluator → 判定]
  ↓ (Blocker / Major / Minor を Orchestrator に返す)
[5. Orchestrator → Go / Stop]
  ↓ (Go: 次サイクルへ / Stop: 差し戻し or エスカレーション)
```

### 3.1 各ステップの入出力契約

| Step | 入力 | 出力 | 次 Step への契約 |
|---|---|---|---|
| 1. タスク定義 | マイルストーン / 前サイクル結果 | サイクル計画書 (scope / 成功条件 / 禁止事項) | Designer が迷わず設計開始できる粒度 |
| 2. 設計確定 | タスク計画 / D1–D5 | Interface 仕様 / Decision / Open Question | Developer が「どう実装するか」を迷わない |
| 3. 実装 | 設計仕様 | コード + テスト (git commit 化) | Evaluator が契約と照らし合わせ可能な状態 |
| 4. 判定 | コード + テスト | Blocker / Major / Minor リスト + 差し戻し指示 | Orchestrator が Go/Stop 判断可能 |
| 5. Go/Stop | 判定結果 | サイクル完了レポート or 差し戻し | 次サイクル or 停止 |

### 3.2 サイクル定義 (1 サイクルの条件)

**Decision (3.2-1)**: 1 サイクルは以下 **4 条件**を**すべて**満たす:

- **1 責務のみ**: 複数の無関係な変更を含まない
- **rollback 可能**: 途中 commit でも main から revert すれば元に戻せる
- **テスト可能**: unit / integration / contract のいずれかで完結した検証が可能
- **変更が局所**: 5 ファイル以下 (Interface 追加 + 実装 + test 複合は 10)

---

## 4. 判定ルール (最重要)

Evaluator はすべての指摘を **Blocker / Major / Minor** の 3 段階に分類する。分類が誤ると「暴走」と「止まりすぎ」の両方が起きるため、本書で**明確な基準**を与える。

### 4.1 Blocker (即停止)

#### 該当条件 (いずれか)

1. **D1–D5 契約違反**
   - スキーマ定義との不一致 (D1)
   - backtest 責務逸脱 (D2)
   - Interface 契約違反 (D3、禁止 15 項目のいずれか)
   - 起動シーケンス違反 (D4)
   - Retention ポリシー違反 (D5)
2. **データ消失リスク**
   - 単純 DELETE (Archiver 外) の実装
   - `TRUNCATE` / `DROP TABLE` の migration 直接使用
   - No-Reset 違反 (D5 1.)
3. **誤発注リスク**
   - `_verify_account_type_or_raise` の省略・迂回 (6.18)
   - `expected_account_type=live` への勝手な変更
   - OANDA 本番 API key のコミット
4. **DB スキーマ破壊**
   - 列削除 / 型変更を expand-contract 手順なく実行
   - Alembic down で既存データ破壊
5. **live / backtest 不整合**
   - `if backtest:` / `isinstance(broker, PaperBroker)` 分岐の実装
   - Broker / PriceFeed / Clock 以外での分岐
6. **Outbox 破壊**
   - `orders(PENDING)` と `outbox_events` の別トランザクション commit
   - Outbox を経由しない発注パス
7. **再現性崩壊**
   - Feature Service 内の `datetime.now()` 直接呼出
   - seed なし乱数の使用
   - config_version 計算ロジックの破壊
8. **通知経路違反**
   - critical 通知を `notification_outbox` 経由で送る (6.13)
   - SafeStopJournal への書込なしで safe_stop 確定

#### 動作
- **即停止**: Developer への差し戻し
- 修正完了まで次のサイクルに進まない
- 人間エスカレーションが必要な場合は Orchestrator が判断

### 4.2 Major (修正必須)

#### 該当条件 (いずれか)

1. **設計逸脱 (軽度)**
   - Designer の Decision と実装の齟齬 (ただし契約を破っていない)
   - Interface シグネチャの微妙な差 (引数順序など)
2. **テスト不足**
   - 新規 Interface に対応する contract test 欠如
   - エッジケース (最小ロット境界、TTL 境界等) のテスト不足
   - ハッピーパスのみで異常系テスト不在
3. **責務分界の曖昧さ**
   - domain → services の依存方向違反 (未修正で残っている)
   - Repository 外での DB 直接アクセス
4. **将来バグリスク高**
   - 例外を except Exception で握りつぶし
   - race condition を起こしうる非同期パス
   - 無限ループの可能性

#### 動作
- **修正後に再評価**: 原則**そのサイクル内で解消**
- 修正不可能な場合のみ次サイクルに持ち越し (Orchestrator が明示的 Go)
- Major が複数重なったら Blocker 相当に格上げ検討

### 4.3 Minor (改善推奨)

#### 該当条件 (いずれか)

1. **可読性**
   - 長すぎる関数 / 深いネスト
   - コメント不足 (ただし存在意義を説明する一文程度)
2. **命名**
   - development_rules 4. の命名規約との軽微な乖離
   - 変数名の不明瞭さ
3. **軽微な冗長**
   - 同じロジックの繰り返し (3 回未満なら許容、3 回以上で Major)
   - 不要な import
4. **パフォーマンス微改善**
   - 明らかに非効率だがボトルネックではない実装
   - N+1 クエリだが小規模な箇所

#### 動作
- **次サイクルでも可**
- Stop 条件ではない
- ただし**記録必須** (Minor 累積で技術負債化するのを防ぐ)

### 4.4 判定の手順

Evaluator は以下の順で判定:

1. D1–D5 との整合性チェック (Blocker 候補)
2. 禁止 15 項目 (development_rules 13.1) との抵触チェック (Blocker 候補)
3. 設計 (Designer 出力) との整合性チェック (Major 候補)
4. テスト網羅性チェック (Major 候補)
5. コード品質チェック (Minor 候補)

**Decision (4.4-1)**: 判定は**レポート形式**で出力:
```
Evaluator Report (Cycle X-Y):
- Blockers: [N件]
  - B1: <具体指摘> (根拠: D3 7. #3)
  - ...
- Majors: [N件]
  - M1: <具体指摘> (根拠: ...)
  - ...
- Minors: [N件]
  - ...
- 合否: PASS / FAIL
- 差し戻し先: Developer / Designer
```

---

## 5. 停止条件

**以下が 1 つでも該当すれば Orchestrator は Stop 判断**:

1. **Blocker 存在** (Evaluator 指定、4.1)
2. **契約と衝突** (D1–D5 の文面レベル矛盾)
3. **スキーマ連鎖変更** (1 サイクル内で 5 テーブル以上への変更波及)
4. **テスト不安定** (flaky test が 3 回連続で再現、原因特定不能)
5. **外部仕様不明** (OANDA API / 依存ライブラリ挙動が docs と食い違う)
6. **1 サイクルが 2 時間相当を超過** (Orchestrator 判断で分割)
7. **Designer と Developer の合意形成不能** (設計解釈の齟齬がサイクル内で解消しない)

### 5.1 停止時の動作

- 進行中の作業を**中断** (ただし in-flight の git 操作は完了させる)
- 停止理由を Orchestrator が ADR 形式で該当 docs の Open Questions 節に記録
- **人間エスカレーション条件に該当する場合**は即座に人間に報告 (6. 参照)
- 該当しない場合は次サイクルで代替タスクを選定

---

## 6. エスカレーション条件

**以下は必ず人間判断を仰ぐ** (Orchestrator が判断、Designer/Developer/Evaluator が提案可能):

### 6.1 設計選択が複数あり決定不可
- docs に Decision が存在せず、Designer が複数案を提示したが優劣が判断不能
- 例: 「例外階層を Python 標準 Exception から継承 vs 独自 Base から継承」
- **動作**: ADR 候補を列挙 → 人間に選択依頼 → Decision を該当 docs 追記

### 6.2 セキュリティ / 金銭リスク
- API key / secret の漏洩可能性
- `expected_account_type=demo` 以外への変更要求
- 本番 DB への破壊的 migration 必要性
- 誤発注につながる変更 (TTL / ULID / account_type の契約緩和)
- **動作**: **即座に停止** → 人間確認待ち

### 6.3 外部 API 仕様不明
- OANDA API の動作が D1–D5 / Phase 6 Hardening の想定と異なる
- 依存ライブラリの挙動が未確認 (ULID ライブラリの sortable 性等)
- **動作**: **検証コードを書いて実測** → 結果を該当 docs の Open Questions に記録 → 実装続行 (契約違反なら 6.2 に昇格)

### 6.4 契約変更が必要
- 実装中に発見された仕様ホールが D1–D5 変更を要求
- Phase 7/8 送りの項目を Iteration 1 に前倒し必要
- **動作**: Designer が契約変更提案書作成 → 人間承認 → docs 先行更新 → 実装追従

### 6.5 ロール内で解決不能
- Designer と Developer が設計解釈で合意形成できない
- Evaluator の判定に Developer が異議を持ち、サイクル内で合意できない
- **動作**: Orchestrator が仲裁、それでも不能なら人間判断

---

## 7. 自律許可範囲

### 7.1 自動で進めてよい

Orchestrator が以下を判断したら**人間確認なし**で進行可:

1. **小規模実装**: 1 サイクル = 5 ファイル以下 + 契約違反なし
2. **テスト追加**: 既存実装に対する unit / contract test 追加
3. **リファクタリング (契約内)**: Interface 変更を伴わない内部構造変更
4. **docs typo / リンク修正**
5. **CI / lint 設定の調整** (禁止事項検出強化方向のみ)
6. **依存パッケージの patch version up** (minor / major は Designer 経由)
7. **既存マイルストーン (M1–M12) に沿った作業**

### 7.2 必ず停止

以下は**必ず人間承認**を経る:

1. **スキーマ変更** (Alembic migration の追加・変更、D1 改訂を含む)
2. **契約変更** (D1–D5 / Phase 6 Hardening の文面変更)
3. **live 接続変更** (`expected_account_type` / OANDA 本番 API key)
4. **retention 変更** (D5 の retention class 再分類、Archive 実装)
5. **マイルストーン構成変更** (iteration1_implementation_plan の M 追加/削除/順序変更)
6. **禁止事項の変更** (15 項目の追加・削除・緩和)
7. **新しい依存パッケージの major version 変更**
8. **CI の auto-deploy 有効化**
9. **force push 類似の履歴書き換え**

---

## 8. Claude Code におけるロールの具現化

### 8.1 ロールは論理概念

**Decision (8.1-1)**: 4 ロールは**論理概念**であり、必ずしも 4 つの独立エージェントではない:

- **単一 Claude Code セッション**: 1 つの Claude が**ステップごとにロールを切り替えて振る舞う**
  - Step 1 (タスク定義): Orchestrator モード
  - Step 2 (設計確定): Designer モード
  - Step 3 (実装): Developer モード
  - Step 4 (判定): Evaluator モード
  - Step 5 (Go/Stop): Orchestrator モード
- **サブエージェント利用**: 特定 step を別エージェントに委譲可能 (下記 8.2)

### 8.2 サブエージェント利用時のロール割当

`claude-code` のサブエージェント機能利用時の推奨割当:

| サブエージェント | 推奨ロール | 用途 |
|---|---|---|
| `Explore` | Designer 補助 | 既存コード / docs の調査 (書込なし) |
| `Plan` | Designer 主担当 | 設計案の策定 |
| `general-purpose` | Developer 主担当 | 実装 (scope を明示して委譲) |
| (将来専用) `reviewer` / `test-runner` | Evaluator 主担当 | 判定の自動化 |

### 8.3 ロール切替時の義務

ロールを切り替える際、Claude Code は**切替を明示**する:

```
[Orchestrator モード]
サイクル M5-3 のタスク: OrderRepository に FSM を追加する
  scope: src/fx_ai_trading/repositories/orders.py + tests/contract/test_order_fsm.py
  成功条件: 後退遷移で例外、前進遷移で成功
  禁止事項: Repository 外での DELETE 発行

[Designer モードへ切替]
OrderRepository の FSM を以下で確定:
  - 前進遷移のみ許可: PENDING → SUBMITTED → FILLED / CANCELED / FAILED
  - 後退 (FAILED → PENDING 等) は InvalidTransition 例外
  - 楽観ロック: from_status 指定で現状一致確認

[Developer モードへ切替]
上記設計で実装開始:
  ...

[Evaluator モードへ切替]
判定レポート:
  - Blocker: 0
  - Major: 1 (異常系 test が 1 ケースのみ、最低 3 ケース必要)
  ...

[Orchestrator モードへ切替]
Major 1 件を差し戻し → Developer が対応 → 再評価
```

### 8.4 ロール独立性の維持

**Decision (8.4-1)**: **Evaluator モード時は Developer の成果を「他人のコード」として読む**。自分で書いたコードでも、Evaluator ロール時は厳格に判定する。

- これを怠ると Evaluator が形骸化 (自分の実装を甘く評価)
- 判定レポートは**客観的根拠** (D3 のどの条項、禁止事項のどの番号) のみで構成

---

## 9. アンチパターン (禁止)

### 9.1 ロール越境アンチパターン

| # | パターン | 違反ロール |
|---|---|---|
| 1 | Orchestrator が設計を確定してしまう | Designer 権限侵害 |
| 2 | Orchestrator がコードを書く | Developer 権限侵害 |
| 3 | Designer が実装を書く | Developer 権限侵害 |
| 4 | Designer が勝手に D1–D5 を更新する | 契約変更プロセス違反 |
| 5 | Developer が設計を勝手に変える | Designer 権限侵害 |
| 6 | Developer が Evaluator の Blocker を無視する | 判定無視 |
| 7 | Evaluator が実装修正を自分でする | Developer 権限侵害 |
| 8 | Evaluator が Blocker を Minor に下げる (甘い判定) | 判定ルール違反 |
| 9 | Evaluator が問題を見つけても記録しない | 禁止事項 (黙認) |
| 10 | Orchestrator が Blocker を無視して Go | 停止条件違反 |

### 9.2 進行アンチパターン

| # | パターン | 該当ルール |
|---|---|---|
| 11 | **巨大コミット** (10 ファイル超 + 複数論点混在) | 3.2 サイクル定義 / development_rules 1.2 |
| 12 | **設計なし実装** (Step 2 スキップ、Developer が独断で実装) | 3. 開発サイクル厳守 |
| 13 | **テスト後付け** (「テストは次サイクルで」) | 禁止事項 / development_rules 2. |
| 14 | **暗黙仕様** (docs に書かれていない動作を実装) | development_rules 3.1 |
| 15 | **DELETE 乱用** (Archiver 外での DELETE) | D5 1.3 |
| 16 | **mock / live 混在** (`if isinstance(broker, PaperBroker):` 分岐) | D2 12. / Blocker 5 |
| 17 | **Evaluator 無視** (Blocker を握りつぶす) | Blocker 条件 |
| 18 | **ロール未明示** (どのロールで発言しているか不明、責任所在不明) | 8.3 ロール切替義務 |

### 9.3 検出手段

| アンチパターン | 検出方法 |
|---|---|
| 巨大コミット | PR 作成時のファイル数自動チェック (CI) |
| 設計なし実装 | PR description に「Designer Decision を反映」の明記を要求 |
| テスト後付け | PR のコミット履歴で impl commit と test commit の順序 / 同 PR 内 |
| 暗黙仕様 | コードレビュー + Evaluator の設計整合チェック |
| DELETE 乱用 | CI lint (AST check、development_rules 2.7) |
| mock/live 混在 | CI lint (`if backtest:` / `isinstance(PaperBroker)` 検出) |
| Evaluator 無視 | サイクル完了レポートの Blocker 件数 vs 修正コミット数突合 |
| ロール未明示 | サイクル出力のロール宣言タグを CI / レビューで確認 |

---

## 10. 実運用例

### 10.1 正常サイクル例 (Go ケース)

**シナリオ**: M5-3 OrderRepository の FSM 追加

```
[Step 1: Orchestrator]
  タスク: OrderRepository に status FSM (PENDING → SUBMITTED → FILLED / CANCELED / FAILED) 追加
  scope: src/fx_ai_trading/repositories/orders.py (+ test)
  成功条件:
    - 前進遷移が成功する
    - 後退遷移で InvalidTransition 例外
    - from_status 指定で楽観ロック
  禁止: DELETE 発行、Repository 外での status 変更

[Step 2: Designer]
  Decision:
    - transition(order_id, from_status, to_status, ctx) メソッドを追加
    - 事前条件: from_status == orders.status (DB から SELECT で確認、一致しない場合 StaleStateError)
    - 事後条件: orders.status == to_status、supervisor_events に transition ログ
    - 前進定義: {PENDING: [SUBMITTED, FAILED], SUBMITTED: [FILLED, CANCELED, FAILED]}
  Rationale: development_rules 5.1 で Repository 経由の MUT は FSM 遵守を契約化
  Open Question: なし
  → Developer へ

[Step 3: Developer]
  - orders.py に transition() 実装 (40 行)
  - test_order_fsm.py に 8 test cases (前進 3 / 後退 3 / 楽観ロック 2)
  - CI 実行: 全 green
  - commit: "feat(m5-3): add order status FSM with optimistic lock"
  → Evaluator へ

[Step 4: Evaluator]
  判定レポート:
    - Blockers: 0
    - Majors: 0
    - Minors: 1 (異常系エラーメッセージの国際化未対応、次サイクル可)
  合否: PASS
  根拠: D3 2.9.1 Repository 契約 / D1 4.2 MUT 前進のみ / development_rules 5.1
  → Orchestrator へ

[Step 5: Orchestrator]
  Go 判断
  Minor 1 件を M11 Contract Tests Hardening で消化予定と記録
  次サイクル M5-4 (OrderRepository integration test) へ
```

### 10.2 Blocker 検出例 (Stop ケース)

**シナリオ**: M8-2 Outbox 処理実装

```
[Step 3: Developer 実装後]
[Step 4: Evaluator]
  判定レポート:
    - Blockers: 1
      - B1: OrderRepository.insert() が commit 前に Broker.place_order() を呼んでいる
        根拠: D3 2.6.3 / 6.6 Outbox Pattern 違反
        影響: orders 行 insert 前に OANDA に発注される → DB 障害時に副作用残存
    - Majors: 0
    - Minors: 0
  合否: FAIL (Blocker 1)
  差し戻し先: Developer

[Step 5: Orchestrator]
  Stop 判断 (Blocker 存在)
  Developer に差し戻し:
    - orders INSERT + outbox_events INSERT + COMMIT の後に Broker 呼出
    - Outbox transaction contract test を追加
  次サイクル (M8-2 再実行) へ
```

### 10.3 契約変更必要例 (Escalation ケース)

**シナリオ**: M9-4 EVEstimator 実装中、D3 に EVEstimator v0 heuristic の具体式が不在と発覚

```
[Step 3: Developer]
  EVEstimator v0 を実装しようとしたが、D3 2.4.2 で「heuristic」とだけ記述、具体式なし

[Step 3 内部で Developer が自己認識]
  → 独断で式を決めるのは「暗黙仕様追加」(Anti-pattern 14)
  → Orchestrator にエスカレーション

[Orchestrator: 判断]
  「設計ホール、Designer にエスカレーション」

[Designer]
  案 A: `P(win) = 0.5` 固定 / `cost = spread`
  案 B: `P(win) = 0.5 + 0.1 * tanh(signal_confidence)` / `cost = spread + atr*0.1`
  Rationale: MVP は単純優先で案 A、Phase 7 でキャリブレーション
  → 人間承認必要 (6.1 Escalation)

[人間承認] → 案 A を Decision として docs 追記

[Designer: docs 更新]
  D3 2.4.2 に Decision 追記: "MVP v0: P(win)=0.5 (heuristic prior), cost=spread only"
  PR 作成 (`contract:` commit)

[Designer PR merge 後]
[Developer: 実装再開]
  D3 の Decision に従って実装 → Evaluator → Go
```

### 10.4 Major 修正ループ例

**シナリオ**: M6-1 Broker 基底クラスの実装

```
[Step 4: Evaluator 初回]
  判定レポート:
    - Blockers: 0
    - Majors: 2
      - M1: account_type assertion が try/except Exception で握りつぶされている
        → 例外伝搬させないと safe_stop が発火しない
      - M2: contract test が MockBroker のみで PaperBroker / OandaBroker がカバーされていない
    - Minors: 3
  合否: FAIL

[Step 5: Orchestrator]
  Major 修正のため同サイクル内で再実装

[Step 3 再実行: Developer]
  - try/except 削除、例外伝搬に変更
  - contract test を全 Broker 実装に対応 (parametrize)
  - 再 commit: "fix(m6-1): propagate AccountTypeMismatch and extend contract test"

[Step 4 再実行: Evaluator]
  判定レポート:
    - Blockers: 0
    - Majors: 0
    - Minors: 3 (変わらず、次サイクル可)
  合否: PASS

[Step 5: Orchestrator]
  Go 判断
```

### 10.5 Evaluator による追加テスト要求例

**シナリオ**: M10-1 ExecutionGate TTL 実装

```
[Step 4: Evaluator]
  判定レポート:
    - Blockers: 0
    - Majors: 1
      - M1: TTL 境界テストが `signal_age=16s` のみ。以下が必要:
        - ちょうど signal_ttl_seconds (= 15s) の境界
        - TTL 内の Defer が有効か
        - TTL 超過後の Defer が自動 Reject に遷移するか
  合否: FAIL (Major 1)
  追加テスト要求: 3 test cases

[Step 3 再実行: Developer]
  追加テスト実装 → commit: "test(m10-1): add TTL boundary cases"

[Step 4 再実行: Evaluator]
  PASS
```

---

## 11. 失敗時の復旧原則

### 11.1 サイクル内失敗

- Developer 実装中のテスト失敗 → **Developer が修正継続** (Evaluator 送信前に解消)
- Evaluator 判定前のコード腐敗 → **commit を rollback** (git reset --soft で最小化)

### 11.2 サイクル跨ぎ失敗

- 前サイクル commit に問題発覚 → **git revert で新 commit 作成** (history 改竄禁止)
- 複数サイクル跨ぎの根本原因 → **マイルストーン一時停止 + ADR 記録**
- Orchestrator が「再計画が必要」と判断したら人間エスカレーション

### 11.3 Main への破壊的変更検知

- CI / reviewer が破壊的変更を発見
- **即座に revert commit** (force push は main には絶対禁止)
- 破壊者は Blocker として判定、次サイクルで修正

---

## 12. 自己レビューのチェックリスト (ロール別)

### 12.1 Developer 完了時 (Evaluator 送信前)

- [ ] 変更ファイル数が 5 (複合で 10) 以下か
- [ ] 1 コミット 1 論点か
- [ ] 禁止 15 項目 (development_rules 13.1) のいずれも踏んでいないか
- [ ] 該当する assertion (D3 4.) を実装しているか
- [ ] Common Keys を Repository 経由で付与しているか
- [ ] 単純 DELETE を書いていないか
- [ ] live / backtest 分岐を書いていないか
- [ ] account_type assertion が該当処理で呼ばれているか
- [ ] client_order_id が ULID か
- [ ] secret がログ / exception / docs に漏れていないか
- [ ] 関連 docs の更新が必要なら同一 PR で更新しているか
- [ ] テストが追加・更新されていて全て通るか
- [ ] Open Question を該当 docs に記録したか

### 12.2 Evaluator 判定時

- [ ] D1–D5 の該当条項を逐条チェックしたか
- [ ] 禁止 15 項目を 1 つずつ確認したか
- [ ] Designer の Decision と実装が整合しているか
- [ ] contract test が新規 Interface に対応しているか
- [ ] テストの異常系カバレッジを確認したか
- [ ] Blocker を Minor に下げていないか (甘い判定の自己チェック)
- [ ] 根拠 (D3 何節、禁止事項何番) を全指摘に紐づけたか

### 12.3 Designer 確定時 (Developer 送信前)

- [ ] D1–D5 と整合しているか
- [ ] Interface シグネチャが曖昧なく記述されているか
- [ ] Decision / Rationale を該当 docs に追記したか
- [ ] Open Question を握りつぶしていないか
- [ ] 実装で迷う論点が残っていないか
- [ ] 契約変更を伴う場合は提案書を作成したか

### 12.4 Orchestrator 判断時

- [ ] Evaluator の Blocker を無視していないか
- [ ] サイクル定義 (1 責務 / rollback 可 / テスト可 / 局所) を満たしているか
- [ ] 次サイクル提案が依存グラフに従っているか
- [ ] 停止条件・エスカレーション条件に該当していないか

---

## 13. 絶対にやってはいけないこと (再掲)

以下は**いかなる理由でも実行禁止**:

| # | 禁止行為 | 根拠 |
|---|---|---|
| 1 | 本番接続設定の勝手な進行 (`expected_account_type=live` / 本番 API key 投入) | 6.18、Escalation 6.2 |
| 2 | 契約変更をコード先行で行う | development_rules 3.2、Escalation 6.4 |
| 3 | 単純 DELETE の実行 | D5、Blocker 2 |
| 4 | account_type assertion の迂回 | 6.18、Blocker 3 |
| 5 | mock / paper / live の責務差分曖昧化 | D2 12.、Blocker 5 |
| 6 | 巨大コミット | 3.2、Anti-pattern 11 |
| 7 | main へ壊れた状態を merge | development_rules 1.5 |
| 8 | git history 書き換え | development_rules 1.10 |
| 9 | secret をログ / docs / exception に漏らす | 6.13、Phase 3 |
| 10 | SafeStopJournal / supervisor_events / reconciliation_events 手動編集・削除 | 6.1、監査証跡 |
| 11 | Feature Service 内で `time.time()` / seed なし乱数 | 6.10、Blocker 7 |
| 12 | Notifier の critical 通知を outbox 経由 | 6.13、Blocker 8 |
| 13 | Broker / PriceFeed / Clock 以外での live/backtest 分岐 | D2 12.、Blocker 5 |
| 14 | Alembic down で既存データ破壊 | D5、Blocker 4 |
| 15 | 契約テスト (D3 8.4) を削除 / skip | Anti-pattern / Blocker 1 |
| 16 | **Evaluator の Blocker を無視** | Anti-pattern 10 / 17 |
| 17 | **ロール越境** (他ロールの権限を侵害) | 2. 権限マトリクス |

---

## 14. 本書と他文書の参照関係

```
[automation_harness.md] (本書)
  ├→ 権限・判定・停止を定義
  ├→ [development_rules.md] (ルール本体) を参照
  ├→ [iteration1_implementation_plan.md] (実装順序) を参照
  └→ [D1–D5 + Phase 6 Hardening] (契約) を正本として参照

[development_rules.md]
  ├→ Git / test / docs / 禁止事項の具体ルール
  └→ 本書 (automation_harness.md) に従って運用される

[iteration1_implementation_plan.md]
  ├→ M1–M12 の実装順序と完了条件
  └→ 本書のサイクル (5 Step) で進行
```

本書を**破る**変更は**契約違反**として扱い、本書の変更は**人間承認必須**。

---

## 15. Open Questions

| ID | 論点 | 解決予定 |
|---|---|---|
| AH-Q1 | サブエージェント向け prompt テンプレ (本書 8.2 の推奨割当を自動化) の具体化 | Iteration 1 M1 (`.claude/` 配下に配置検討) |
| AH-Q2 | CI で禁止 15 項目のどれを機械化できるか | Iteration 1 M1 / M11 (development_rules 2.7 と統合) |
| AH-Q3 | Evaluator の自動化 (contract test 結果から Blocker 自動判定) | Phase 7 |
| AH-Q4 | 複数 Claude Code セッションが並行動作する場合の Orchestrator 衝突回避 | 実運用後に判断 |

---

## 16. 最終チェック (本書の完成度検証)

本書は以下を**すべて満たす**:

| チェック項目 | 根拠 |
|---|---|
| ✅ 「誰が決めるか」が明確 | 2. 権限マトリクス + 1. 各ロールの責務 |
| ✅ 「誰が止めるか」が明確 | Evaluator が Blocker トリガ + Orchestrator が最終停止 (2. / 5.) |
| ✅ 暴走防止できる | Evaluator の Blocker 条件 (4.1) + 禁止 15 項目 (13.) |
| ✅ 止まりすぎない | Minor は次サイクル可 (4.3) + 自律許可範囲 (7.1) + ロールが合意形成で進める (3.) |
| ✅ D1–D5 を守れる | Blocker 条件で機械的検出 + Designer の設計責任 + Evaluator の契約チェック |
| ✅ 巨大コミットを作らない | サイクル定義 (3.2) + ファイル上限 (Developer 禁止事項) |
| ✅ account_type assertion を迂回できない | 6.18 Blocker 条件 3 + Developer 禁止事項 |
| ✅ 単純 DELETE を許さない | D5 Blocker 条件 2 + development_rules 13.1 #3 |

---

## 17. Summary (ハーネス完全版の固定点)

本書は以下を**Iteration 1 以降の自律開発契約**として固定する:

1. **4 ロール** (Orchestrator / Designer / Developer / Evaluator) の責務・権限・禁止を明示
2. **権限マトリクス**で「誰が決めるか / 誰が止めるか」を機械的に読み取り可能
3. **5 ステップサイクル厳守** (タスク → 設計 → 実装 → 判定 → Go/Stop)、順序スキップ禁止
4. **判定ルール 3 段階** (Blocker 即停止 / Major サイクル内修正 / Minor 次サイクル可)
5. **Blocker 条件 8 種**を契約違反として列挙、検出で自動停止
6. **停止条件 7 種** (Blocker / 契約衝突 / スキーマ連鎖 / テスト不安定 / 外部不明 / 時間超過 / 合意不能)
7. **エスカレーション条件 5 種** (設計選択不能 / 金銭リスク / 外部仕様不明 / 契約変更必要 / ロール内解決不能)
8. **自律許可 7 項目 / 必ず停止 9 項目**で「動いていい範囲」を明示
9. **ロールは論理概念**、単一 Claude の切替 or サブエージェント委譲のいずれでも運用可
10. **アンチパターン 18 項目** (ロール越境 10 + 進行 8) を禁止
11. **実運用例 5 パターン** (正常 Go / Blocker Stop / Escalation / Major 修正ループ / 追加テスト要求)
12. **禁止 17 項目** (内 2 項目が本書固有: Evaluator 無視 / ロール越境) を絶対禁止

本書を破る変更は **契約違反**として扱い、本書の改訂は**人間承認必須**。
