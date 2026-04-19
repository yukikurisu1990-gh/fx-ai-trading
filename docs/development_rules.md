# Development Rules — 開発運用の単一ソース

## Purpose
本プロジェクトの **Git / テスト / ドキュメント / 契約変更 / 命名 / config / secret / logging** の運用ルールを**単一ソース**として固定する。Iteration 1 以降のすべての作業 (Claude Code 自律 / 人間運用者) が本書に従う。`docs/automation_harness.md` と `docs/iteration1_implementation_plan.md` は本書のルールを前提とする。

## Scope
- Git 運用 (ブランチ / コミット / PR / rollback)
- テスト運用 (契約テスト優先、test 種別使い分け)
- ドキュメント運用 (D1–D5 正本、契約先の原則)
- 命名規約 / ディレクトリ規約
- 抽象層追加の条件
- TODO / FIXME / feature flag の扱い
- Migration / config / secret / logging / metrics ルール
- backtest / live 共通化の実装ルール
- 禁止事項一覧

## Out of Scope
- 設計契約そのもの (D1–D5 / Phase 6 Hardening が正本)
- Claude Code の動作ループ (`docs/automation_harness.md` が定義)
- 実装順序 (`docs/iteration1_implementation_plan.md` が定義)
- 人間運用手順 (`docs/operations.md`)

## Dependencies
- D1 `docs/schema_catalog.md`: スキーマ変更の対象
- D3 `docs/implementation_contracts.md`: Interface / 禁止アンチパターン
- D5 `docs/retention_policy.md`: 単純 DELETE 禁止
- `docs/phase6_hardening.md`: 不変契約

## Related Docs
- `docs/automation_harness.md`: 自律開発の行動規範 (本書のルールを運用に落とす)
- `docs/iteration1_implementation_plan.md`: Iteration 1 の実装順序

---

## 1. Git 運用

### 1.1 ブランチ戦略

**Decision (1.1-1)**: MVP 期は **main + feature branch** の単純 2 階層。

- **`main`**: 常に動く状態、全 test green、全契約充足
- **feature branch**: `feat/<milestone>-<step>` / `fix/<issue>` / `refactor/<scope>` / `chore/<task>` / `docs/<scope>` の命名
  - 例: `feat/m2-alembic-initial-migration` / `feat/m4-broker-interface` / `docs/update-d3-exception-hierarchy`
- **1 ブランチ 1 目的** (複数マイルストーン / 複数機能を 1 ブランチに混ぜない)
- ブランチ寿命は**最大 3 日**を目安。長くなる場合は分割

**Inherited Constraint (1.1-2)**: `main` への直接コミットは**禁止** (PR 経由のみ)。例外: 極めて軽微な docs typo 修正のみ人間運用者が判断。

### 1.2 コミット戦略

**Decision (1.2-1)**: **Conventional Commits 風**を採用 (既存の git_workflow.md 不在のため本書で正式化)。

形式:
```
<type>: <summary>

[optional body]
```

`<type>` は以下:

| type | 用途 |
|---|---|
| `feat` | 新機能追加 |
| `fix` | バグ修正 |
| `refactor` | 振る舞いを変えない構造変更 |
| `test` | テスト追加・修正 |
| `docs` | ドキュメント更新のみ |
| `chore` | ビルド / 依存 / CI / 雑務 |
| `migration` | Alembic migration 関連 |
| `contract` | D1–D5 / Phase 6 Hardening の契約文書変更 |
| `revert` | 過去 commit の revert |

**1 コミット 1 論点の原則**:
- 無関係な変更を混ぜない
- 例 NG: "feat: add Broker interface and fix existing test bug" → 2 コミットに分割
- 例 OK: "feat: add Broker interface" + "test: add Broker contract tests" (Interface 追加とその test は論理的に 1 セットなので連続コミットは OK、統合 PR で出す)

### 1.3 schema / business logic の分離

**Decision (1.3-1)**: 原則として schema 変更 (Alembic migration) と business logic 変更は**別コミット**。

- schema 変更を先にマージ、次に logic 変更を乗せる
- Rationale: schema migration で DB 停止リスクがある場合、rollback が容易になる
- 例外: 同じ PR 内で migration + 最小 test (schema 作成確認) は同 commit OK

### 1.4 Interface change と adapter implementation の分離

**Decision (1.4-1)**: Interface 定義と、その具体実装 (Adapter / Repository / 実 Broker 等) は**可能な限り別コミット**。

- Interface 追加コミット → Mock 実装コミット → 本物実装コミット、の順
- Rationale: Interface レイヤを安定させてから実装に進むことで、contract test の基盤が先に固まる

### 1.5 壊れた状態で main に入れない

- PR マージ前に **ローカル + CI 両方で test green** 必須
- CI red の PR は**絶対にマージしない** (緊急 hotfix でも例外なし)
- マージ後に main が red になった場合、**即座に revert commit** を作成 (force push 禁止)

### 1.6 途中経過でも rollback 可能性を維持

**Decision (1.6-1)**: 各 feature branch は**途中状態でも main から revert 可能**であること。

- マイルストーン途中のコミットでも、そこで止めて main にマージしても壊れない状態を保つ
- 実現策:
  - 未完成の Interface は**呼び出しを空実装 or `NotImplementedError`** で stub
  - 未完成機能は **feature flag** (`app_settings` で `flags.*.enabled=false`) で無効化
  - migration は always-forward-compatible (既存動作を壊さない列追加のみで段階的に)

### 1.7 PR / レビュー戦略

**Decision (1.7-1)**: MVP 期は人間運用者 1 名による簡易レビュー。

- PR には以下を含める:
  - 変更サマリ (何を / なぜ)
  - 関連マイルストーン / step
  - test 結果 (green 確認)
  - 契約遵守チェック (禁止事項 15 項目、assertion 13 項目のどれに関連するか)
  - docs 更新の有無
- レビューチェック項目:
  - 変更ファイル数 ≤ 5 (Interface 追加 + 実装 + test の複合は 10)
  - 1 コミット 1 論点
  - contract test が追加 / 更新されている
  - docs 更新が必要な変更で docs が更新されている

### 1.8 Squash の扱い

**Decision (1.8-1)**: **Squash Merge を既定**とする。

- PR 内の細かいコミットを 1 つにまとめて main に入れる
- main 上では **PR 単位 = 1 コミット**
- Rationale: bisect 容易性と履歴の見やすさ
- 例外: 契約変更 + 実装追従のように**複数コミットを main に残したい場合は明示的に merge commit**

### 1.9 Hotfix 条件

- **Critical 事象** (safe_stop 連発 / データ破損 / セキュリティ) のみ hotfix 許容
- Hotfix でも PR 経由 + test green 必須
- ブランチ名: `fix/hotfix-<short-desc>`、main へ最短マージ
- Hotfix 後に必ず **post-mortem** (`supervisor_events` に incident_report、`docs/operations.md` Runbook 更新)

### 1.10 Force Push / History 書き換え禁止

- **`git push --force` を main / 共有ブランチに絶対禁止**
- 個人 feature branch でも push 先を共有する場合は `--force-with-lease` を使う (他人作業保護)
- `git rebase -i` で他人のコミットを書き換えるのは禁止
- 例外: Iteration 1 開始前の一度きりの squash など、**全員合意**の上のみ

---

## 2. テスト戦略

### 2.1 テスト種別と優先度

**Decision (2.1-1)**: D3 8. の 4 段階をこの優先順で整備:

| # | 種別 | 目的 | MVP 必須 | 実装時期 |
|---|---|---|---|---|
| 1 | **Contract Test** | Interface 契約の不変条件検証 | **最優先 / 必須** | Interface 追加と同時 |
| 2 | **Unit Test** | 個別モジュールの振る舞い検証 | 必須 | 実装と同時 |
| 3 | **Integration Test** | 複数コンポーネント連携検証 | 必須 (主要 flow のみ MVP) | M12 で集中整備 |
| 4 | **Simulation Consistency Test** | live/backtest の整合検証 | Phase 7 以降 | backtest 実装時 |

### 2.2 Contract Test (最重要)

D3 8.4 の 8 項目は**MVP 必須**:

| 契約 | 検証内容 | 実装タイミング |
|---|---|---|
| Feature Service 決定性 (6.10) | 同入力で feature_hash 等価 | M5 (Feature Service) |
| look-ahead 禁止 (D2 3.) | as_of_time 違反検出 | M5 / M11 (backtest Interface 時) |
| Broker account_type assertion (6.18) | 全 Broker 実装で assertion 発火 | M6 (Broker) |
| Outbox transaction (6.6) | orders + outbox_events の同一 tx commit | M8 (Outbox) |
| ULID フォーマット (6.4) | orders.order_id が ULID | M8 |
| Notifier 二経路 (6.13) | critical は outbox 経由しない | M6 (Notifier) |
| 単純 DELETE 禁止 (D5) | CI lint で grep + AST check | M1 (CI) |
| Common Keys 伝搬 (D1 3.3) | Repository 経由以外での書込禁止 | M3 / M5 |

### 2.3 Migration Test

- 全 Alembic revision で `up → down → up` の往復テスト
- PostgreSQL と SQLite 両方で schema 作成が成立
- 初期 seed 投入後の `app_settings` 全 key の存在確認
- Migration test は CI で**PR 毎に実行**

### 2.4 Determinism Test

- Feature Service: 同入力 + 同 feature_version でバイト等価
- BacktestRunner: 同 backtest_run_id 再実行で同一 metrics
- EVEstimator: 同 signal + 同 cost で同一 EV
- 乱数を使う場合は seed 管理下のみ

### 2.5 Look-Ahead 防止 Test

- Feature Service に「未来データ」fixture を投入
- `as_of_time` より過去のデータのみで特徴量計算されるか
- 未来データを混ぜても `feature_hash` が変わらないか

### 2.6 Account Type Assertion Test

- `MockBroker` / `PaperBroker` / `OandaBroker` の全実装で:
  - account_type 不一致で `AccountTypeMismatch` 例外発火
  - 起動時 assertion 失敗で起動拒否
  - 発注前 assertion 失敗で safe_stop 発火

### 2.7 No-Reset / Retention Violation Test

- CI lint で以下を検出:
  - `DELETE FROM` 直接発行 (Archiver Interface 経由以外)
  - `TRUNCATE TABLE` / `DROP TABLE` の migration 直接使用
  - Repository 外での DML

### 2.8 Notifier 二経路 Test

- critical イベント (`safe_stop.fired` / `db.critical_write_failed` 等) が:
  - `notification_outbox` に**書かれない**
  - `FileNotifier` (logs/notifications.jsonl) に**必ず書かれる**
  - 外部 Notifier (Slack 等) に**同期送信**される (失敗時は次にフォールバック)

### 2.9 Outbox Transaction Test

- `orders(PENDING)` と `outbox_events(ORDER_SUBMIT_REQUEST)` が**同一トランザクションで commit**
- 片方のみ成功する状況を作り、どちらもロールバックされる確認

### 2.10 Smoke Test と Integration Test の使い分け

| Smoke Test | Integration Test |
|---|---|
| 1 秒以内に完了、CI 常時 | 数秒〜数分、CI で選択的実行 |
| 「パイプラインが壊れていない」を確認 | 「主要ユースケースが動く」を確認 |
| 例: 起動シーケンスの Step 1-5 がエラーを出さない | 例: 1 cycle の分足判断が end-to-end で通る (M12) |

---

## 3. ドキュメント運用

### 3.1 D1–D5 を正本とする

**Inherited Constraint (3.1-1)**: **D1 / D2 / D3 / D4 / D5 の文面が契約の正本**。コードと docs が食い違った場合、docs を正として判断する。

- 既存 docs に反する実装は**契約違反** (`docs/automation_harness.md` 5.1 で停止条件)
- 不整合発見時は「docs 先更新 → 実装追従」の順 (6. 契約変更プロセス)

### 3.2 docs 先 or 同時更新の原則

**Decision (3.2-1)**: 契約変更を伴う実装変更は **docs 更新を先行** or 同時実施。実装のみ先行は**禁止**。

- Interface 追加/変更 → D3 を先に更新 → 実装
- スキーマ変更 → D1 + Alembic migration を同時更新
- 運用手順変更 → D4 を先に更新 → コード / CLI 追従
- retention 変更 → D5 を先に更新 → Archiver 追従

### 3.3 実装だけ先に変えない (禁止)

- 「コードを書いてから docs を後追い」は禁止
- ただし**実装の詳細** (具体的な行数、private method の名前等) は docs に書かない (Interface は書くが、internal は書かない)
- 判断基準: **他の人 / 他のエージェントが実装を見ずに docs だけで仕様を理解できるか**

### 3.4 Open Question を閉じた時の反映先

- 実装中に Open Question が解決したら、**該当 docs の Open Questions 節から Decision 節に移動**
- 例: D3 IC-Q1 (例外階層) が Iteration 1 M4 で決まったら → D3 の IC-Q1 を削除、Decision として該当箇所に記述

### 3.5 roadmap への反映条件

- `docs/phase7_roadmap.md` / `docs/phase8_roadmap.md` は**将来計画**
- Iteration 1 中に Phase 7/8 内容が前倒しで実装される判断になった場合 → roadmap の「実装時期」を Iteration 1 に書き換え + 該当マイルストーンを追加
- 逆に Iteration 1 スコープから落とす場合 → iteration1_implementation_plan の「Out of Scope」に追加 + roadmap に移動
- roadmap 変更は `contract:` タイプのコミット

### 3.6 ADR (Architecture Decision Record)

**Decision (3.6-1)**: 実装中に重要判断が発生した場合、**該当 docs の Decision 節に追記**する形式で ADR を残す。

- 別途 `docs/adr/` ディレクトリは**作らない** (docs が分散すると追跡困難)
- Decision の書式: `Decision (<docs-section>-N): <内容>` + `Rationale: <理由>`
- 例: D3 2.13.1 に "Decision: SecretProvider は AWS Secrets Manager 既定、SMTP は Phase 7" など

---

## 4. 命名規約

### 4.1 Python (code)

- **ファイル / モジュール**: `snake_case` (例: `broker.py` / `meta_decider.py`)
- **クラス / Protocol / ABC**: `PascalCase` (例: `Broker` / `MetaDecider` / `StrategySignal`)
- **関数 / メソッド**: `snake_case` (例: `place_order` / `compute_config_version`)
- **定数 / 環境変数キー**: `UPPER_SNAKE_CASE` (例: `CYCLE_TIMEOUT_SECONDS`)
- **Interface suffix は付けない**: Java 風の `IBroker` / `BrokerInterface` は**禁止**、`Broker` のまま
- **Abstract Base Class の prefix は付けない**: `AbstractBroker` / `BaseBroker` を**強制しない**。ただし base class の中身が実装含むなら `BrokerBase` 許容

### 4.2 DB (schema)

- **テーブル名**: `snake_case`、D1 の命名に従う
- **列名**: `snake_case`、意味が一意に伝わるように
- **外部キー**: `{referenced_table}_{referenced_column}` (例: `order_id`, `broker_id`)
- **インデックス**: `ix_{table}_{columns}` (例: `ix_orders_cycle_id_status`)
- **主キー**: PK 用カラム名は `{table_singular}_id` (例: `order_id`, `meta_decision_id`、ただし natural key の場合は例外)

### 4.3 Git (branch / commit)

- **ブランチ**: `{type}/{milestone}-{short-desc}` または `{type}/{short-desc}`
- **コミット**: Conventional Commits (1.2 参照)

### 4.4 Logging / Metrics / Events

- **ログ event_type**: `<domain>.<event>` (例: `safe_stop.fired` / `config.version_changed` / `account_type.mismatch`)
- **メトリクス名**: `{domain}_{metric}` (例: `cycle_duration_seconds`, `outbox_pending_count`)

---

## 5. ディレクトリ規約

**Decision (5-1)**: 以下の Python package 構造を採用。

```
src/
  fx_ai_trading/            # ルートパッケージ
    __init__.py
    config/                 # ConfigProvider / SecretProvider
    common/                 # CommonKeysContext, exceptions, ULID util
    domain/                 # DTO / Protocol (Interface 定義)
      broker.py
      strategy.py
      meta.py
      risk.py
      ...
    adapters/               # Interface の具体実装
      broker/
        oanda.py
        paper.py
        mock.py
      notifier/
        file.py
        slack.py
      persistence/
        postgres.py
        sqlite.py
    repositories/           # Repository 実装 (D1 の 44 テーブル)
    services/               # ビジネスロジック (Feature / Strategy / Meta / Risk / Execution / Exit)
    supervisor/             # Supervisor / SafeStopJournal / Reconciler / MidRunReconciler / OutboxProcessor
    dashboard/              # Streamlit UI
    backtest/               # BacktestRunner / SimClock (M11+)
tests/
  unit/
  integration/
  contract/
  migration/
migrations/
  versions/                 # Alembic revisions
docs/                       # 本 docs 群
scripts/                    # ctl CLI 等
```

**Rationale**: D3 1.1 の 11 レイヤと対応。`domain/` は Interface / DTO のみ (実装なし)、`adapters/` が外部依存を含む実装、`services/` がドメインロジック。

### 5.1 依存方向

- `domain/` → 他から参照されるが、何も import しない (純粋 Interface)
- `services/` → `domain/` を参照、`adapters/` を参照しない (Interface 経由のみ)
- `adapters/` → `domain/` を参照、`services/` を参照しない
- `repositories/` → `domain/` + `adapters/persistence/` を参照
- `supervisor/` → ほぼ全てに依存 (orchestrator 的)

**禁止**: 逆方向依存 (例: `domain/` が `services/` を import) は import lint で検出。

---

## 6. 契約変更ルール

### 6.1 契約とは

以下が「契約」:
- D1 スキーマ catalog (テーブル構造 / Common Keys / retention class)
- D2 backtest 責務
- D3 Interface / 禁止アンチパターン / assertion
- D4 起動シーケンス / 障害分類 / Runbook
- D5 retention class / アーカイブ手順
- Phase 6 Hardening (6.1–6.21)
- `app_settings` 初期値 (6.5)

### 6.2 契約変更のプロセス

1. **提案**: 変更提案をブランチに docs 変更先行で書く (コミット `contract:` タイプ)
2. **影響分析**: 該当契約に依存する他 docs / 既存コードをリストアップ
3. **人間レビュー**: 契約変更は**必ず人間 reviewer の承認が必要**
4. **実装追従**: 契約が main にマージされた後、実装を追従する PR を作成
5. **整合性検証**: 実装 PR マージ前に全 contract test を再度通す

### 6.3 禁止: 契約を**暗黙に**変える

- コードが先、docs が後、は**禁止**
- `if backtest:` のような分岐で契約を実質的に骨抜きにするのは**禁止**
- 契約変更を伴わない「実装詳細の修正」だけなら契約変更プロセス不要 (例: 内部の private method の rename)

---

## 7. 抽象層の増やし方 / 増やしてはいけない条件

### 7.1 増やしてよい条件

- **複数の具体実装**が既に存在する、または**明確に予定**されている
- 例: Broker (Oanda / Paper / Mock の 3 実装) / Notifier (File / Slack / 将来 Email)
- **契約テストが書きやすくなる**
- **live / backtest の分岐 (D2 12.2) を Interface で吸収**する時

### 7.2 増やしてはいけない条件

- **実装が 1 つしか存在しない**のに将来のために抽象化する (YAGNI)
- **テスタビリティのため**だけに追加 (mock が必要なら既存の小さな Interface でよい)
- **設計の美しさ**のため (具体的な問題解決と紐づかない)

**Decision (7-1)**: 抽象層追加は**既存契約 (D3) で定義済みのもの優先**。D3 にない新 Interface を勝手に追加は禁止 (契約変更プロセス経由)。

---

## 8. TODO / FIXME / Feature Flag の扱い

### 8.1 TODO / FIXME

**Decision (8.1-1)**: コード内の `# TODO:` / `# FIXME:` は**期限 + 対応者 + 追跡 ID** を必須:

```python
# TODO(iteration1-m5): Feature Service v0 の normalize 実装
# FIXME(ADR-D3-IC-Q3): async/await 境界の判断待ち
```

- 期限なしの TODO / FIXME は CI lint で**警告**
- Iteration 1 完了時に全 TODO を棚卸し

### 8.2 Feature Flag

- Feature flag は `app_settings` の `flags.<feature>.enabled` 形式で管理
- コードは `ConfigProvider.get("flags.X.enabled", False)` で読む
- flag の ON/OFF 切替は `app_settings_changes` に履歴記録
- Iteration 1 終了時に全 flag を棚卸し、不要なものは削除 (長期残留禁止)

### 8.3 Strategy ON/OFF (6.17)

- `strategy.AI.enabled` / `strategy.MA.enabled` / `strategy.ATR.enabled` は feature flag とは別系統 (ドメイン概念)
- `lifecycle_state` と直交
- コードで直接触らず、Strategy Engine の pre-filter で enabled を確認する

---

## 9. Migration ルール

### 9.1 Alembic 基本原則

- **expand-contract** を基本 (破壊的変更を 2+ revision に分割)
- **up → down → up** の往復テストを CI で必須
- migration script は 1 revision = 1 論理的変更

### 9.2 破壊的変更の禁止

- 列削除 → View で旧名保全しつつ別 revision で削除
- テーブル削除 → 全 caller が移行済確認後、別 revision で DROP
- 型変更 → 新列追加 → data backfill → 旧列削除、の 3 revision

### 9.3 初期 migration (Iteration 1 M2)

- 44 テーブル + 2 ローカルファイル相当のセットアップ
- Phase 1/3 旧名の View エイリアス
- `app_settings` 初期値 seed (6.5 全 key)
- Common Keys 列を全 table に付与 (D1 3.)
- 複合インデックスを Common Keys ベースで設定

### 9.4 データ Backfill

- 既存行がある状態で列追加する migration は **default 値 NULL** or **固定値で backfill**
- Backfill は migration 内で小バッチ (1000 行毎 commit) で実施、ロック最小化

---

## 10. Config / Secret ルール

### 10.1 Config の 4 階層 (Phase 2.11 継承)

優先度順:
1. プロセス起動引数 (`--flag=value`)
2. 環境変数 (`APP_*` / `FX_*` プレフィックス)
3. `.env` ファイル (ローカル開発)
4. Cloud Secret Provider (本番)
5. デフォルト値 (コード内定数)

### 10.2 config_version 導出への貢献 (6.19)

- 1–4 すべてが `config_version` 計算の入力 (canonical JSON)
- secret 値は**ハッシュ参照のみ**、値そのものは含めない

### 10.3 `.env` / Secret の扱い

**禁止**:
- `.env` を**コミット**する (`.gitignore` で除外必須)
- secret 値を docs / log / exception message に含める
- secret 値を `config_version` に直接含める

**必須**:
- `.env.example` で必要な env var を**キーのみ** docs 化
- secret は SecretProvider Interface 経由でのみ取得
- ログ出力時は `LogSanitizer` を通す (D3 2.10 / 6.13 継承)

### 10.3.1 UI 経由 secret 入力ルール (Iter3 以降の Configuration Console)

UI から secret を入力する場合の**唯一許可される sink は `.env`** (operations.md §15.4 と対応):

**禁止**:
- secret 値を `app_settings` / `app_settings_changes.old_value` / `app_settings_changes.new_value` / 他 DB テーブルに**平文書込** (実列名は schema_catalog §2 #42 の `(name, old_value, new_value, changed_by, changed_at, reason)`)
- UI のセッション state / ブラウザ Cookie / Local Storage に secret 値を保持
- UI ログ / ダッシュボードパネル / エラー表示に secret 値を露出 (key 名 + sha256 prefix までは許可)
- SecretProvider に書込 Interface (`rotate` / `set` 等) を Iter2 で追加すること (Iter2 は read-only `get` / `get_hash` / `list_keys` のみ、D3 §2.13.2)

**必須**:
- 入力契機は Configuration Console「起動前モード」のみ (アプリ未起動時)。「稼働中モード」では表示 (key 一覧 + hash) のみで変更操作は無効化
- `.env` 書込時は値そのものをログに出さず、`app_settings_changes` の `name` 列に key 名、`old_value` / `new_value` には sha256 prefix のみ、`changed_by` に操作者、`changed_at` に UTC time、`reason` に変更理由を記録 (`LogSanitizer` 経由、平文の secret は `old_value` / `new_value` に書込まない)
- 適用は `.env` 書込 + アプリ再起動の 2 段階。即時反映は禁止 (6.18 4 重防御の継続)

### 10.4 環境別 config

- `environment = local` / `vps` / `aws` / `backtest` で設定差分
- `expected_account_type = demo` 初期、環境別に上書き可能だが**local は demo 固定** (6.18)

---

## 11. Logging / Metrics / Alerting 実装ルール

### 11.1 Criticality Tier (6.13 継承)

コードで Logger 呼び出し時、**tier に応じた書込経路**を使う:

```python
# Critical tier: 同期書込、失敗で safe_stop
critical_repo.insert(order_submitted, ctx)  # Repository 同期

# Important tier: at-least-once 非同期、失敗でログ + continue
important_logger.log(strategy_signal, ctx)  # queue 経由

# Observability tier: best-effort、サンプリング可
observability_logger.log(feature_snapshot, ctx, sample_rate=0.1)
```

### 11.2 構造化ログ

- 全ログは構造化 (JSON / key-value)
- `print()` / `sys.stdout.write()` は**禁止** (CI lint 対象)
- 本番では **stdout に構造化ログ** + 一次DB への書込の両方

### 11.3 メトリクス

- Supervisor が 1 分毎に 9 メトリクス (D4 6.2) を `supervisor_events(event_type=metric_sample)` に記録
- MVP は DB 書込のみ、Prometheus 化は Phase 7

### 11.4 Alerting (Notifier 2 経路)

- **Critical イベント**は `FileNotifier` 同期 + 外部 Notifier 同期直接送信 (6.13)
- **非 critical** は `notification_outbox` 経由
- `notification_outbox` 経由で critical を送るのは**禁止**

---

## 12. Backtest / Live 共通コード化ルール

### 12.1 共通化の原則 (D2 12. 継承)

- **共通コード**: Feature / Strategy / EV / Cost / Meta / Risk / Exit / Repository / Notifier / Aggregator
- **差し替え**: Broker / PriceFeed / Clock の 3 点のみ

### 12.2 禁止パターン

```python
# ❌ 禁止: アプリ内での live/backtest 分岐
if is_backtest:
    ...
else:
    ...

# ❌ 禁止: Broker 型判定
if isinstance(broker, PaperBroker):
    ...

# ✅ 正しい: Interface 差し替え (DI で注入)
# Broker が OandaBroker か PaperBroker かは caller が意識しない
broker.place_order(request)
```

### 12.3 Clock の扱い

**Decision (12.3-1)**: `datetime.now()` / `time.time()` の直接呼出を**禁止**、`Clock` Interface 経由のみ:

```python
# Clock は live / backtest で差し替え
class Clock(Protocol):
    def now_utc(self) -> datetime: ...

# WallClock (live) / SimClock (backtest) が実装
```

これにより backtest でも決定的に時刻制御できる。

---

## 13. 禁止事項一覧

### 13.1 コード (`docs/automation_harness.md` 12. 再掲 + 追加)

| # | 禁止 | 根拠 |
|---|---|---|
| 1 | `datetime.now()` / `time.time()` 直接呼出 | Clock Interface 経由のみ (12.3) |
| 2 | `print()` / `sys.stdout.write()` 直接 | 構造化ログのみ (11.2) |
| 3 | `DELETE FROM` を Repository / Archiver 外で発行 | D5 1.3 |
| 4 | `TRUNCATE` / `DROP TABLE` を migration で直接 | D5 1.1 |
| 5 | `if backtest:` / `if isinstance(broker, PaperBroker):` 分岐 | D2 12. |
| 6 | Broker 実装で `_verify_account_type_or_raise` 省略 | 6.18 |
| 7 | Common Keys 列を Repository 外で直接書込 | D1 3.3 |
| 8 | Feature Service 内で seed なし乱数 / 現在時刻依存 | 6.10 |
| 9 | Secret 値をログ / Exception / docs に含める | 6.13 / Phase 3 |
| 10 | `orders.status` 後退遷移 | D1 / 6.6 FSM |
| 11 | critical 通知を `notification_outbox` 経由で送る | 6.13 |
| 12 | 同期的ログ書込でトレーディングループブロック | Phase 2 非同期境界 |
| 13 | Observability tier 書込失敗で safe_stop | 6.13 |
| 14 | Critical tier 書込を非同期キュー化 | 6.13 |
| 15 | 契約 docs と矛盾する実装 | 3.1 |
| 16 | UI 層が `ConfigProvider` / `SecretProvider` / `dashboard_query_service` を経由せず config / secret / DB を直接読み書き | operations.md §15.1 / 10.3.1。UI は ctl ラッパ + `.env` 起動前 sink + read-only query に閉じる |

### 13.2 Git

| # | 禁止 | 根拠 |
|---|---|---|
| 1 | `main` / `master` への force push | 1.10 |
| 2 | `main` に壊れた状態を merge | 1.5 |
| 3 | `main` への直接 commit (PR 経由なし) | 1.1 |
| 4 | 巨大 commit (10 ファイル超 + 複数論点) | 1.2 / 4.2 |
| 5 | secret を含む commit | 10.3 |
| 6 | 他人コミットの rebase 書き換え | 1.10 |

### 13.3 Docs

| # | 禁止 | 根拠 |
|---|---|---|
| 1 | D1–D5 に反する実装 | 3.1 |
| 2 | コード先行の契約変更 (docs 後追い) | 3.2 / 3.3 |
| 3 | Open Question の暗黙決定 (docs に記録せず実装で固定) | 3.4 |
| 4 | `docs/adr/` ディレクトリ新設 (ADR は該当 docs 内記述) | 3.6 |

---

## 14. Open Questions

| ID | 論点 | 解決予定 |
|---|---|---|
| DR-Q1 | PR テンプレの具体化 (`.github/PULL_REQUEST_TEMPLATE.md`) | Iteration 1 M1 |
| DR-Q2 | CI lint の具体ツール選定 (ruff / custom AST checker) | Iteration 1 M1 |
| DR-Q3 | `.env.example` の canonical な形 (6.19 で canonical key 順が確定してから) | Iteration 1 M3 |
| DR-Q4 | 共有 VPS / AWS 環境での Secret 管理先 (Vault / Secrets Manager) | Phase 7 |

---

## 15. Summary (ルール固定点)

本書は以下を**MVP 以降の開発契約**として固定する:

1. **Git**: main + feature branch / Conventional Commits / 1 コミット 1 論点 / main red 不可 / force push 禁止
2. **Test**: Contract test 最優先 / migration / determinism / look-ahead / account_type / Notifier 二経路 / Outbox tx の 8 項目を MVP 必須
3. **Docs**: D1–D5 正本 / 契約先更新 / 実装後追い禁止 / ADR は該当 docs 内記述
4. **Naming**: Python は `snake_case` / `PascalCase`、DB は `snake_case`、Interface suffix 禁止
5. **Directory**: `domain/` → `services/` / `adapters/` / `repositories/` → `supervisor/` の依存方向
6. **Config / Secret**: 4 階層、secret は SecretProvider 経由、`.env` コミット禁止
7. **Logging**: Criticality Tier 別書込経路、`print()` 禁止、構造化ログ必須
8. **Live/Backtest**: Broker / PriceFeed / Clock の 3 点差し替えのみ、分岐禁止
9. **禁止事項**: Code 16 項目 / Git 6 項目 / Docs 4 項目 を CI / review で機械検出

本書を破る変更は **契約違反**として扱う (contract-change process 経由のみ変更可)。
