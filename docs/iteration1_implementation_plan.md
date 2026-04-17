# Iteration 1 Implementation Plan

## Purpose
Iteration 0 で固定された契約 (D1–D5 + Phase 6 Hardening) をベースに、**MVP スケルトン (paper mode での細い疎通まで)** を**後戻り最小の順序で安全に構築する**ための実装計画書。Claude Code と人間運用者が本書の順序に従うことで、契約衝突なく MVP 到達可能であることを保証する。

## Scope
- Iteration 1 のゴール / 非ゴール
- 12 マイルストーン (M1–M12) とその依存関係
- 各 M の目的 / 入力 / 変更対象 / 完了条件 / テスト条件 / リスク / 後続依存
- 推奨実装順序とコミット単位例
- 並列可能 / 並列禁止の境界
- MVP 完了条件
- Iteration 2 / Phase 7 / Phase 8 に送る項目

## Out of Scope
- 具体的な Python コード (本書は計画、実装は各サイクルで)
- OANDA 本番接続設定 (Iteration 2 以降)
- AI 本物モデルの学習パイプライン (Phase 7)
- Backtest engine の**実体**実装 (Interface のみ Iteration 1、実体は Phase 7)
- Cold Archive 実 Job (Phase 7)
- UI SSO / マルチユーザ (Phase 8)

## Dependencies
- D1 `docs/schema_catalog.md`: 44 テーブル構造
- D3 `docs/implementation_contracts.md`: 30+ Interface
- D4 `docs/operations.md`: 16 Step の起動シーケンス
- D5 `docs/retention_policy.md`: 単純 DELETE 禁止
- `docs/phase6_hardening.md`: 不変契約 (6.1–6.21)

## Related Docs
- `docs/automation_harness.md`: Claude Code 自律開発の行動規範
- `docs/development_rules.md`: Git / test / docs ルール本体

---

## 1. Iteration 1 のゴール

**定義**: **paper mode で 1 分足分足判断 → Outbox → PaperBroker → 擬似約定 → ポジション更新 → ExitPolicy → 決済** までの**パイプラインが細く通る**状態。

具体的成功条件:

1. **OANDA API** に demo アカウントで接続し、instruments / candles / pricing の取得ができる (発注はしない)
2. **Feature Service** が 1 通貨ペアに対して決定的 (feature_version 付き) に特徴量計算
3. **3 戦略** (AIStrategyStub / MAStrategy / ATRStrategy) が並列評価され `strategy_signals` に記録
4. **MetaDecider** (3 段ルール) が `meta_decisions` を出力、no_trade を含む全判断を記録
5. **PaperBroker** が擬似発注・擬似約定を出し、`orders` / `order_transactions` / `positions` が更新される
6. **ExitPolicy** が TP / SL / 時間 / 緊急停止で発火
7. **Supervisor** の起動シーケンス (D4 2.1 Step 1–16) 全てが成功
8. **SafeStopJournal** + **Notifier 二経路** が正しく動作
9. **Streamlit 最小ダッシュボード**で 7 パネルを表示
10. **Contract Test 8 項目** が CI で全て green
11. **Alembic 初期 migration** が 44 テーブル + 旧名 View を作成、up/down/up 往復テスト成功
12. **42 テーブル + 2 ローカルファイル + backtest 用 2 テーブル**で Common Keys が正しく伝搬

---

## 2. 非ゴール (Iteration 1 Out of Scope)

以下は**Iteration 1 では実装しない** (契約だけ固める / stub で通す):

- **OANDA live 接続** (demo only、`expected_account_type=demo` 固定)
- **OANDA 本番 API key の投入** (開発用 demo key のみ)
- **AI モデル本体** (AIStrategyStub のみ、本物は Phase 7)
- **Backtest engine 実体** (D2 の Interface 宣言まで、BacktestRunner.run() は NotImplementedError)
- **Cold Archive 実行** (D5 Archiver Interface のみ、実 Job は Phase 7)
- **相関双窓 regime tightening の Select 適用** (記録までは実装、強制適用は Phase 7)
- **AIStrategy shadow→active Promotion 自動化** (状態機は実装、運用は Phase 7)
- **Dashboard SSO / マルチユーザ** (BasicAuth 想定、SSO は Phase 8)
- **EmailNotifier** (FileNotifier + SlackNotifier のみ、Email は Phase 7)
- **CI 自動マイグレーションテスト** (手動 or 最小 CI、自動化は Phase 7)
- **DR 訓練** (バックアップは実装、訓練は Phase 8)
- **Chaos Engineering 体系化** (最小 fault injection test のみ MVP、体系化は Phase 7)
- **Emergency Flat CLI の 2-factor / 監査拡張** (CLI 本体のみ、拡張は Phase 7)
- **multi_service_mode / container_ready_mode の本番運用** (`single_process_mode × local` で MVP 完結、他モードは Interface のみ)

---

## 3. 実装原則

1. **契約を破らない**: D1–D5 / Phase 6 Hardening の文面に反する実装をしない (`docs/automation_harness.md` 5. 停止条件)
2. **後戻り最小の順序**: 依存の根元から順に実装 (Interface → 基盤 → ドメイン → UI)
3. **常に細く通す**: 各マイルストーン完了時点で「壊れていない状態」を維持 (`docs/development_rules.md` 1.6)
4. **Interface 先 / 実装後**: D3 の Interface を Protocol / ABC で宣言した後に Adapter / 実装を作る
5. **Contract Test と実装は同期**: D3 8.4 の 8 項目は Interface 追加と同時に test を追加
6. **live 接続禁止**: `expected_account_type` は `demo` 固定、OANDA 本番 API key は投入しない
7. **paper mode を最短で通す**: M6 で Broker Interface / PaperBroker が揃った時点で、M8 の Outbox と組み合わせて**最小疎通試験**ができる状態を目指す

---

## 4. 前提条件

### 4.1 Iteration 0 成果物の存在

以下すべてが `docs/` 配下に存在していること:
- `docs/design.md` (Phase 0–5 + Phase 6 Reference)
- `docs/phase6_hardening.md` (6.1–6.21)
- `docs/phase7_roadmap.md` / `docs/phase8_roadmap.md`
- `docs/schema_catalog.md` (D1)
- `docs/backtest_design.md` (D2)
- `docs/implementation_contracts.md` (D3)
- `docs/operations.md` (D4)
- `docs/retention_policy.md` (D5)
- `docs/automation_harness.md`
- `docs/development_rules.md`
- 本書 `docs/iteration1_implementation_plan.md`

### 4.2 開発環境

- PostgreSQL が local で動作 (Docker 推奨、または直接インストール)
- Python 3.11 または 3.12 (3.14 は回避、H7 解消)
- Git / GitHub 接続 (private repo `yukikurisu1990-gh/fx-ai-trading`)
- OANDA demo アカウントの API key (実発注しない paper 用として保持)
- 開発機での NTP 同期 (D4 2.1 Step 2 で 500ms 超 warn / 5s 超 reject)

### 4.3 マインドセット

- 1 サイクル完了毎に「次は何か」を明示
- 疑問発生時は docs 確認 → Open Question 追記 → エスカレーション条件確認 (`automation_harness.md` 5./6.)
- 実装 PR は**常に小さく**

---

## 5. マイルストーン一覧

| M | 名称 | 目的 | 典型工数 | 依存 |
|---|---|---|---|---|
| **M1** | Tooling & Repo Foundation | Python / 依存 / CI / 禁止 lint 設定 | 1–2 日 | なし |
| **M2** | Alembic & Initial Schema | 44 テーブル + 旧名 View + app_settings 初期値 | 2–3 日 | M1 |
| **M3** | Common Keys & Config Infrastructure | ConfigProvider / SecretProvider / config_version / NtpChecker / CommonKeysContext | 2 日 | M1, M2 |
| **M4** | Domain Interfaces / DTOs / Exceptions | D3 の全 Interface を Protocol / ABC で宣言、DTO dataclass、例外階層 | 2–3 日 | M1 |
| **M5** | Repository & Persistence Adapter | PostgreSQL/SQLite Adapter、Repository 群 (44 + 2 テーブル対応)、Common Keys 自動伝搬 | 3–4 日 | M2, M3, M4 |
| **M6** | Broker, Notifier, SafeStopJournal | MockBroker/PaperBroker/OandaBroker 骨格、FileNotifier/SlackNotifier、SafeStopJournal | 2–3 日 | M4, M5 |
| **M7** | Supervisor & Startup Sequence | Supervisor 骨格、D4 Step 1-16 の起動シーケンス、NTP / account_type / config_version / Alembic revision 検査 | 2 日 | M3, M6 |
| **M8** | Outbox, OrderLifecycle, Reconciler | OutboxProcessor、OrderLifecycleService (FSM)、起動時 Reconciler、MidRunReconciler (骨格のみ) | 3–4 日 | M5, M6 |
| **M9** | Strategy Layer Skeleton | Feature Service (決定性)、AIStrategyStub / MAStrategy / ATRStrategy、EVEstimator v0、CostModel、MetaDecider (3 段ルール) | 4–5 日 | M4, M5 |
| **M10** | Risk + ExecutionGate | PositionSizer、RiskManager、ExecutionGate (TTL 判定 / Defer) | 2 日 | M4, M9 |
| **M11** | Contract Tests Hardening | D3 8.4 の 8 項目を CI で green、禁止 15 項目の lint 整備 | 2 日 | M3–M10 |
| **M12** | Minimal Dashboard & Paper Smoke | Streamlit 7 パネル、supervisor metric 記録、paper mode 疎通 end-to-end test | 3 日 | 全 M |

**総工数目安**: 28–36 日 (1 人日換算)。実時間は並列化・中断を考慮して 5–8 週間を想定。

---

## 6. マイルストーン詳細

### 6.1 M1: Tooling & Repo Foundation

**目的**: Python / 依存 / CI / lint / pre-commit hook を固定し、以降のマイルストーンが**契約違反検出機構**の上で動く状態を作る。

**入力**:
- `docs/development_rules.md` (規約)
- `docs/automation_harness.md` (禁止事項)
- 既存 `pyproject.toml` (空テンプレ想定)

**変更対象 (ファイル)**:
- `pyproject.toml` (Python 3.11/3.12 pin、依存ピン留め)
- `requirements.txt` / `requirements-dev.txt` (もしくは pyproject の optional-deps)
- `.python-version` (pyenv 用、任意)
- `.pre-commit-config.yaml` (pre-commit hook、禁止 lint 含む)
- `.github/workflows/ci.yml` (pytest + ruff + migration test + contract test の最小 CI)
- `.gitignore` (`.env` 除外、`logs/` 除外、`__pycache__` 等)
- `src/fx_ai_trading/__init__.py` (空パッケージ作成)
- `tests/__init__.py`
- `docs/development_rules.md` に DR-Q1 / DR-Q2 の Decision 追記

**完了条件**:
- [ ] Python version が `pyproject.toml` で `>=3.11,<3.13` に固定
- [ ] 依存パッケージのロック (pip-tools / uv / poetry のいずれか選定、MVP では `pip-tools` 想定)
- [ ] `ruff check .` / `ruff format --check .` が green
- [ ] Custom lint: `DELETE FROM` 直接発行の検出、`print(` の検出、`datetime.now()` の検出 (3 項目以上)
- [ ] GitHub Actions CI が `pytest` を実行 (テスト 0 件でも green)
- [ ] pre-commit hook で commit 時に lint が走る
- [ ] `README.md` の「初期セットアップ」手順が再現可能

**テスト条件**:
- CI green
- 意図的に禁止パターンを入れた commit が pre-commit / CI で弾かれる (lint 検証)

**リスク**:
- 依存ライブラリの競合 (特に SQLAlchemy / Alembic / psycopg / oandapyV20 のバージョン組合せ)
- pre-commit hook が遅すぎる → 対応: 重い lint は CI のみに寄せる

**後続依存**: すべての M が M1 完了後に開始可

---

### 6.2 M2: Alembic & Initial Schema

**目的**: D1 に従った 44 テーブル + 旧名 View + `app_settings` 初期値 (6.5) を Alembic で作成。

**入力**: D1 `schema_catalog.md`、Phase 6.5 初期パラメータ、D5 retention class

**変更対象**:
- `alembic.ini` / `migrations/env.py` / `migrations/script.py.mako`
- `migrations/versions/0001_initial_schema.py` (44 テーブル + 複合インデックス + FK)
- `migrations/versions/0002_legacy_view_aliases.py` (Phase 1/3 旧名 10+ View)
- `migrations/versions/0003_app_settings_seed.py` (6.5 全 32+ key の INSERT)
- `tests/migration/test_alembic_up_down.py` (up/down/up 往復テスト)
- `tests/migration/test_schema_coverage.py` (44 テーブル全ての存在確認、Common Keys 列の存在確認)
- `docs/schema_catalog.md` に Q5 (具体列型) の Decision 追記

**完了条件**:
- [ ] Alembic `upgrade head` で 44 テーブル + 2 backtest テーブル作成 (46 テーブル)
- [ ] Phase 1/3 旧名 10+ View が `intents` / `fills` / `exits` 等で作成される
- [ ] `app_settings` に 6.5 の全 key が INSERT される
- [ ] PostgreSQL と SQLite 両方で schema 作成成功 (SQLite は dev 用、JSONB 等を TEXT で代替)
- [ ] `alembic downgrade base` で全テーブル削除 (local / dev のみ、本番は No-Reset)
- [ ] `upgrade → downgrade → upgrade` 往復テスト green
- [ ] 全テーブルに `run_id` / `environment` / `code_version` / `config_version` + 該当 Common Keys 列が存在

**テスト条件**:
- Migration test 3 件以上 (up/down、schema coverage、app_settings seed)
- CI で PG + SQLite 両方で migration 実行 (Docker コンテナ経由)

**リスク**:
- PostgreSQL 固有型 (JSONB) と SQLite の差分 → 対応: 型 mapping 層を migration で条件分岐
- View 構文の方言差 → 対応: SQLAlchemy Core の抽象を活用
- 複合インデックスの選定不足 → 性能問題は M12 で検出

**後続依存**: M3, M5, M9 が M2 完了後に開始可

---

### 6.3 M3: Common Keys & Config Infrastructure

**目的**: ConfigProvider / SecretProvider / CommonKeysContext / config_version / NtpChecker の基盤を作り、**全ての Repository 書込に Common Keys が自動伝搬する**状態にする。

**入力**: 6.19 config_version 契約、D1 3.3 Common Keys 伝搬、6.14 NTP 起動検査

**変更対象**:
- `src/fx_ai_trading/config/provider.py` (ConfigProvider)
- `src/fx_ai_trading/config/secret.py` (SecretProvider / 環境別実装)
- `src/fx_ai_trading/config/config_version.py` (6.19 canonical JSON + SHA256)
- `src/fx_ai_trading/config/ntp.py` (NtpChecker、500ms warn / 5s reject)
- `src/fx_ai_trading/common/context.py` (CommonKeysContext dataclass)
- `src/fx_ai_trading/common/ulid.py` (ULID 生成、6.4)
- `src/fx_ai_trading/common/clock.py` (Clock Interface + WallClock / SimClock)
- `src/fx_ai_trading/common/exceptions.py` (例外階層のスケルトン)
- `tests/unit/test_config_version.py` (決定性テスト)
- `tests/unit/test_common_keys_context.py`
- `tests/contract/test_config_version_determinism.py` (同入力で同 hash)

**完了条件**:
- [ ] ConfigProvider が 4 階層 (起動引数 / env / .env / default) で値取得
- [ ] config_version が 5 要素 canonical JSON で SHA256[:16] として計算
- [ ] secret 値が effective_config に含まれない (SHA256 参照のみ)
- [ ] NtpChecker が 500ms 超で warn、5s 超で起動拒否 (ただし起動拒否実行は M7 の Supervisor で)
- [ ] CommonKeysContext が dataclass で全 Common Keys を保持
- [ ] ULID 生成が時系列ソート可能 (contract test で検証)
- [ ] Clock Interface の WallClock / SimClock が差し替え可能

**テスト条件**:
- Unit test: ConfigProvider の 4 階層優先順位
- Unit test: config_version の canonical 化 (キーソート、改行正規化等)
- Contract test: 同一入力で config_version が等価
- Unit test: NtpChecker の閾値判定
- Unit test: ULID のソート性

**リスク**:
- `.env` パースのエッジケース (空行、コメント、引用符)
- NTP ライブラリ選定 (`ntplib` / 外部 API / OS command)
- ULID ライブラリ選定 (`python-ulid` / `ulid-py`)

**後続依存**: M5 / M7 が M3 完了後に本格着手

---

### 6.4 M4: Domain Interfaces / DTOs / Exceptions

**目的**: D3 の 30+ Interface を **Python Protocol / ABC** で宣言し、DTO (dataclass) と例外階層を固定。**この時点では実装なし**、以降のマイルストーンで具体実装を Interface に従って埋める。

**入力**: D3 全章、特に 2.1–2.14 の Interface 定義

**変更対象**:
- `src/fx_ai_trading/domain/broker.py` (Broker Protocol + OrderRequest / OrderResult DTO)
- `src/fx_ai_trading/domain/price_feed.py` (PriceFeed Protocol)
- `src/fx_ai_trading/domain/strategy.py` (StrategyEvaluator / StrategySignal)
- `src/fx_ai_trading/domain/meta.py` (MetaDecider / MetaDecision)
- `src/fx_ai_trading/domain/risk.py` (RiskManager / PositionSizer / Exposure)
- `src/fx_ai_trading/domain/execution.py` (ExecutionGate / TradingIntent / GateResult)
- `src/fx_ai_trading/domain/exit.py` (ExitPolicy / ExitDecision)
- `src/fx_ai_trading/domain/feature.py` (FeatureBuilder / FeatureSet)
- `src/fx_ai_trading/domain/ev.py` (EVEstimator / CostModel / Cost)
- `src/fx_ai_trading/domain/model_registry.py` (ModelRegistry / Predictor)
- `src/fx_ai_trading/domain/notifier.py` (Notifier / NotifyEvent)
- `src/fx_ai_trading/domain/event_bus.py` (EventBus / Transport)
- `src/fx_ai_trading/domain/correlation.py` (CorrelationMatrix)
- `src/fx_ai_trading/domain/event_calendar.py` (EventCalendar)
- `src/fx_ai_trading/common/exceptions.py` (完全な例外階層)
- `tests/contract/test_protocols_exist.py` (全 Protocol の import 可能性、メソッド存在)

**完了条件**:
- [ ] D3 2. の 30+ Interface が**全て** Protocol or ABC として存在
- [ ] DTO はすべて `@dataclass(frozen=True)` で immutable (Phase 2 の状態管理契約)
- [ ] 例外階層が定義: `BaseError` → `ContractViolationError` / `AccountTypeMismatch` / `SignalExpired` / `DeferExhausted` / `AccountTypeMismatchRuntime` など
- [ ] Protocol のシグネチャが D3 の記述と完全一致
- [ ] import lint: `domain/` は他層を import しない (依存方向 `development_rules.md` 5.1)

**テスト条件**:
- Contract test: 全 Protocol が import 可能、必須メソッド存在
- Unit test (各 DTO): frozen / 等価性 / Common Keys 保持

**リスク**:
- Protocol vs ABC の選択 (Python 3.11+ では Protocol が型推論良い、ABC はランタイムチェック強い)
  - **Decision**: **Protocol を基本、契約チェックが必要な箇所のみ ABC** (契約テストで runtime 検証する場合 ABC が楽)
- dataclass の型 hint 精度 (Optional / Union)

**後続依存**: M5 以降の実装層は M4 の Interface に従う

---

### 6.5 M5: Repository & Persistence Adapter

**目的**: 44 + 2 テーブルに対する Repository を作り、**Common Keys を Repository で自動伝搬**する機構を完成させる。

**入力**: D1 (全テーブル定義)、M3 (CommonKeysContext)、M4 (DTO)

**変更対象**:
- `src/fx_ai_trading/adapters/persistence/postgres.py` (PostgreSQLAdapter)
- `src/fx_ai_trading/adapters/persistence/sqlite.py` (SQLiteAdapter、dev only)
- `src/fx_ai_trading/repositories/base.py` (Repository 基底、Common Keys 自動付与)
- `src/fx_ai_trading/repositories/orders.py` (OrderRepository、FSM 付き)
- `src/fx_ai_trading/repositories/market.py` (market_candles / market_ticks_or_events / economic_events)
- `src/fx_ai_trading/repositories/strategy.py` (strategy_signals / predictions / ev_breakdowns / feature_snapshots)
- `src/fx_ai_trading/repositories/meta.py` (meta_decisions / pair_selection_runs / pair_selection_scores / correlation_snapshots)
- `src/fx_ai_trading/repositories/execution.py` (trading_signals / order_transactions / positions / close_events / execution_metrics)
- `src/fx_ai_trading/repositories/observability.py` (no_trade_events / drift_events / anomalies / data_quality / retry_events / stream_status / risk_events / reconciliation_events / supervisor_events)
- `src/fx_ai_trading/repositories/operations.py` (system_jobs / app_runtime_state / outbox_events / notification_outbox / app_settings_changes)
- `src/fx_ai_trading/repositories/aggregates.py` (strategy_performance / meta_strategy_evaluations / daily_metrics / backtest_runs / backtest_metrics)
- `src/fx_ai_trading/repositories/reference.py` (brokers / accounts / instruments / app_settings / training_runs / model_registry / model_evaluations)
- `src/fx_ai_trading/repositories/archiver.py` (Archiver Interface 実装 skeleton、実 Archive 処理は Phase 7)
- `tests/integration/test_repository_commonkeys.py` (Common Keys 自動伝搬)
- `tests/contract/test_no_direct_delete.py` (Repository 外 DELETE 禁止、grep / AST)
- `tests/contract/test_order_fsm.py` (orders 状態遷移の前進のみ検証)

**完了条件**:
- [ ] PostgreSQL / SQLite 両方の Adapter で接続・session 管理ができる
- [ ] Repository 経由で全テーブルに INSERT / SELECT / UPDATE (MUT テーブルのみ) / UPSERT (UPS テーブル) 可能
- [ ] Common Keys が Repository 内で自動付与される (直接書込不可を contract test で検証)
- [ ] `orders.status` の FSM が前進のみ許可 (後退で例外)
- [ ] `DELETE FROM` の直接発行が CI lint で検出される (M1 で入れた lint の動作確認)
- [ ] トランザクション境界が明示的 (`with adapter.transaction() as tx:` パターン)

**テスト条件**:
- Integration test: Repository 経由で各テーブルに INSERT + SELECT
- Contract test: Common Keys 自動付与
- Contract test: `orders.status` 後退遷移で例外
- Contract test: DELETE 直接発行の CI lint

**リスク**:
- SQLAlchemy Core vs ORM の選択 (Core で raw SQL 寄り、ORM でモデル抽象化)
  - **Decision**: **Repository は Core + 手書き SQL 寄り**、ORM のフル活用はしない (分析クエリで生 SQL 優位、D3 2.9.2)
- 44 テーブルの Repository 実装でボイラープレート肥大化 → 共通 base class + metaclass で抑制

**後続依存**: M6–M12 が本 M に依存

---

### 6.6 M6: Broker, Notifier, SafeStopJournal

**目的**: Broker 3 実装 (Mock/Paper/Oanda skeleton) と Notifier 2 実装 + SafeStopJournal を作成、**account_type assertion (6.18) / Notifier 二経路 (6.13) / SafeStopJournal (6.1) の contract test を通す**。

**入力**: D3 2.6.1, 2.10.1, 2.10.2 / 6.1 / 6.13 / 6.18

**変更対象**:
- `src/fx_ai_trading/adapters/broker/base.py` (Broker 基底、`_verify_account_type_or_raise`)
- `src/fx_ai_trading/adapters/broker/mock.py` (MockBroker、contract test 用)
- `src/fx_ai_trading/adapters/broker/paper.py` (PaperBroker 骨格、SlippageModel / LatencyModel 注入口)
- `src/fx_ai_trading/adapters/broker/oanda.py` (OandaBroker 骨格、本実装は Iteration 2)
- `src/fx_ai_trading/adapters/notifier/base.py` (Notifier 基底)
- `src/fx_ai_trading/adapters/notifier/file.py` (FileNotifier、fsync 同期書込)
- `src/fx_ai_trading/adapters/notifier/slack.py` (SlackNotifier、Webhook 方式)
- `src/fx_ai_trading/adapters/notifier/dispatcher.py` (二経路 dispatcher: direct sync / outbox)
- `src/fx_ai_trading/supervisor/safe_stop_journal.py` (SafeStopJournal、file lock + fsync)
- `src/fx_ai_trading/common/assertions.py` (AccountTypeAssertion / NtpChecker 連携)
- `tests/contract/test_broker_account_type_assertion.py` (全 Broker 実装で assertion)
- `tests/contract/test_notifier_two_path.py` (critical は outbox 通らない)
- `tests/integration/test_safe_stop_journal.py` (fsync + DB 整合)

**完了条件**:
- [ ] MockBroker / PaperBroker / OandaBroker 全てで `place_order` 内部で `_verify_account_type_or_raise` を呼ぶ
- [ ] 不一致時 `AccountTypeMismatch` 例外 + Notifier critical + safe_stop
- [ ] FileNotifier が logs/notifications.jsonl に fsync 同期書込
- [ ] SlackNotifier が Webhook でメッセージ送信 (本番 URL は env / secret から)
- [ ] Notifier 二経路: critical → direct sync (outbox 経由しない) / 非 critical → outbox
- [ ] SafeStopJournal が logs/safe_stop.jsonl に fsync + file lock で書込
- [ ] SafeStopJournal 起動時読み取り + DB 突合が可能 (実行は M7 で)

**テスト条件**:
- Contract test: account_type assertion (全 Broker)
- Contract test: Notifier 二経路 (critical は outbox に行かない)
- Integration test: SafeStopJournal fsync + 読み込み
- Unit test: Notifier 個別実装

**リスク**:
- Slack Webhook 失敗時の fallback 順序 (Slack → File → ??) → **Decision: Slack 失敗は FileNotifier だけで OK** (MVP、EmailNotifier は Phase 7)
- 同期書込 (fsync) のパフォーマンス → Critical tier のみの制限を守る
- file lock のクロスプラットフォーム差 (Windows / Linux) → `fcntl` / `msvcrt` / `portalocker` ライブラリ

**後続依存**: M7 (Supervisor が Notifier / SafeStopJournal を使う) / M8 (Outbox が Broker を使う)

---

### 6.7 M7: Supervisor & Startup Sequence

**目的**: Supervisor 骨格と D4 2.1 の 16 Step 起動シーケンスを実装し、**正しい順序で assertion が発火、SafeStopJournal が読まれ、Reconciler が起動する**状態にする。

**入力**: D4 2.1 Step 1–16、M3 / M6

**変更対象**:
- `src/fx_ai_trading/supervisor/supervisor.py` (Supervisor 本体、常駐ループ)
- `src/fx_ai_trading/supervisor/startup.py` (16 Step の起動シーケンス実装)
- `src/fx_ai_trading/supervisor/health.py` (HealthStatus / ヘルスチェック 10 秒毎)
- `src/fx_ai_trading/supervisor/safe_stop.py` (safe_stop 発火ロジック、6.1 シーケンス)
- `tests/integration/test_startup_sequence.py` (16 Step の個別失敗パターン)
- `tests/contract/test_safe_stop_fire_sequence.py` (journal → loop stop → notifier → DB の順序)

**完了条件**:
- [ ] Step 1–16 が順次実行され、各 Step の失敗時に適切な挙動 (warn / exit / degraded)
- [ ] Step 2 NTP 検査が 5s 超で起動拒否
- [ ] Step 4 config_version 計算成功、supervisor_events に source_breakdown 記録
- [ ] Step 7 SafeStopJournal ↔ DB 整合 (journal にあり DB にない → DB に補完)
- [ ] Step 9 account_type 不一致で起動拒否
- [ ] Step 15 全 green 時のみトレーディングループ開始許可
- [ ] safe_stop 発火シーケンス: journal → loop stop → notifier → DB の順序で contract test green
- [ ] supervisor_events にメトリクス 9 項目 (D4 6.2) が 1 分毎記録 (MVP は text / JSONB)

**テスト条件**:
- Integration test: 16 Step 正常系 end-to-end
- Integration test: 各 Step の失敗時挙動 (NTP 逸脱、DB 不通、account_type 不一致)
- Contract test: safe_stop 発火シーケンス順序

**リスク**:
- 起動シーケンスの中断復帰 (Step 10 で失敗して再起動したら Step 1 から？) → **Decision: 必ず Step 1 から再実行** (冪等性前提)
- メトリクス記録で DB に負荷 → 1 分毎 + 軽量な 9 項目のみで MVP 成立

**後続依存**: M8 / M12 が Supervisor を使う

---

### 6.8 M8: Outbox, OrderLifecycle, Reconciler

**目的**: Outbox Pattern (6.6) + OrderLifecycleService (FSM) + Reconciler (6.12 Action Matrix + 6.2 MidRun) を実装し、**発注パイプラインが contract を満たす**状態にする。

**入力**: 6.6, 6.12, 6.2, 6.1 in-flight、M5 / M6 / M7

**変更対象**:
- `src/fx_ai_trading/services/outbox_processor.py` (OutboxProcessor、常駐ループ + pause/resume)
- `src/fx_ai_trading/services/order_lifecycle.py` (OrderLifecycleService、FSM 管理)
- `src/fx_ai_trading/supervisor/reconciler.py` (起動時 Reconciler、Action Matrix)
- `src/fx_ai_trading/supervisor/midrun_reconciler.py` (15 分毎 drift check + stream gap 補完)
- `src/fx_ai_trading/supervisor/stream_watchdog.py` (heartbeat 監視、gap 検知)
- `tests/contract/test_outbox_transaction.py` (orders + outbox_events 同一 tx)
- `tests/contract/test_ulid_format.py` (client_order_id ULID)
- `tests/contract/test_reconciler_action_matrix.py` (6.12 全ケース)
- `tests/integration/test_in_flight_order_handling.py` (6.1、safe_stop 中の in-flight)

**完了条件**:
- [ ] `orders(PENDING)` + `outbox_events(ORDER_SUBMIT_REQUEST)` が同一 tx で commit
- [ ] OutboxProcessor が pending を pick → Broker.place_order → status 遷移
- [ ] client_order_id が ULID フォーマット (contract test で全 orders 行検証)
- [ ] 起動時 Reconciler が 6.12 Action Matrix の全ケースを正しく分岐 (Mock OANDA + 擬似データで検証)
- [ ] MidRunReconciler が 15 分毎の drift check で差分検知 (Mock タイマーでテスト)
- [ ] safe_stop 中の in-flight orders が place_order_timeout_seconds で FAILED 遷移
- [ ] OutboxProcessor の pause_dispatch / resume_dispatch が Supervisor から呼べる

**テスト条件**:
- Contract test: Outbox 同一 tx
- Contract test: ULID フォーマット
- Contract test: Reconciler Action Matrix (11 ケース)
- Integration test: in-flight handling
- Unit test: OrderLifecycle FSM の後退遷移例外

**リスク**:
- MidRunReconciler の優先度切替 (6.2) の実装複雑度 → **Decision**: MVP は RateLimiter に 2 bucket (trading / reconcile) + MidRunReconciler が bucket を切替
- Reconciler の 11 ケース全網羅は時間がかかる → 優先度高い 5–6 ケースを MVP、残りは Iteration 2

**後続依存**: M12 (paper smoke test が Outbox 経由発注)

---

### 6.9 M9: Strategy Layer Skeleton

**目的**: Feature Service + 3 戦略 + EVEstimator + CostModel + MetaDecider + Risk を実装し、**1 cycle の分足判断パイプラインが通る**状態にする。

**入力**: D3 2.2-2.5、Phase 6.10 / 6.17、M5

**変更対象**:
- `src/fx_ai_trading/services/feature_service.py` (FeatureBuilder 決定性実装、feature_version 付与)
- `src/fx_ai_trading/services/strategies/ai_stub.py` (AIStrategyStub、固定 confidence)
- `src/fx_ai_trading/services/strategies/ma.py` (MAStrategy、移動平均)
- `src/fx_ai_trading/services/strategies/atr.py` (ATRStrategy、ATR ベース)
- `src/fx_ai_trading/services/ev_estimator.py` (EVEstimator v0 ヒューリスティック)
- `src/fx_ai_trading/services/cost_model.py` (CostModel、spread/slippage/commission/swap)
- `src/fx_ai_trading/services/meta_decider.py` (MetaDecider 3 段ルール)
- `src/fx_ai_trading/services/correlation_matrix.py` (相関双窓、保存まで、regime tightening は Phase 7)
- `src/fx_ai_trading/services/event_calendar.py` (手動 CSV ベース、stale 検知)
- `src/fx_ai_trading/services/price_anomaly_guard.py` (6.3 ATR 異常検知)
- `tests/contract/test_feature_determinism.py` (6.10 同入力で feature_hash 等価)
- `tests/contract/test_no_lookahead.py` (as_of_time 違反検出)
- `tests/unit/test_strategies.py` (各戦略の単体)
- `tests/unit/test_meta_decider.py` (3 段の分岐)

**完了条件**:
- [ ] FeatureBuilder が `feature_version` 付きで決定的 (同入力で同 feature_hash)
- [ ] look-ahead 防止 contract test green (as_of_time より未来データを参照しない)
- [ ] AIStrategyStub が固定 confidence で StrategySignal 返却
- [ ] MAStrategy / ATRStrategy が市場データからシグナル生成
- [ ] EVEstimator v0 が `{value, confidence_interval}` で返す
- [ ] MetaDecider の Filter / Score / Select が 3 段で動作
- [ ] score_contributions / active_strategies / regime_detected が meta_decisions に記録
- [ ] no_trade_events に 6.16 taxonomy で reason_category / reason_code が記録
- [ ] 戦略 ON/OFF (6.17) が app_settings 経由で動作 (disabled 戦略はスキップ)
- [ ] EventCalendar stale failsafe + PriceAnomalyGuard 動作

**テスト条件**:
- Contract test: Feature 決定性
- Contract test: look-ahead 禁止
- Unit test: 各戦略のシグナル生成
- Unit test: MetaDecider 3 段の全 taxonomy カバー
- Integration test: Feature → Strategy → Meta の end-to-end 1 cycle

**リスク**:
- Feature 計算の決定性 (浮動小数の演算順序) → **Decision**: numpy の reduce を決定的に使う、並列 reduce 禁止
- MetaDecider のルール複雑度 → MVP は最小ルール集 (spread 過大 / session / 指標近接 / sizing のみ)

**後続依存**: M10 が MetaDecider を受ける

---

### 6.10 M10: Risk + ExecutionGate

**目的**: PositionSizer + RiskManager + ExecutionGate を実装し、**TTL / Defer / 4 制約が全て動く**状態にする。

**入力**: D3 2.5 / 2.6.2、Phase 6.15 TTL / 6.5 初期値、M4 / M9

**変更対象**:
- `src/fx_ai_trading/services/position_sizer.py` (1-2% リスク、最小ロット判定)
- `src/fx_ai_trading/services/risk_manager.py` (4 制約 accept / reject)
- `src/fx_ai_trading/services/execution_gate.py` (TTL 最初判定、Defer、reason 列挙)
- `tests/contract/test_signal_ttl.py` (6.15 SignalExpired)
- `tests/contract/test_defer_exhausted.py` (6.15 DeferExhausted)
- `tests/unit/test_risk_manager.py` (4 制約個別)
- `tests/unit/test_position_sizer.py` (最小ロット境界)

**完了条件**:
- [ ] PositionSizer が最小ロット未達で SizeUnderMin (no_trade) 返却
- [ ] RiskManager.accept が 4 制約を順に検査
- [ ] ExecutionGate の最初に TTL 判定、超過で Reject(SignalExpired)
- [ ] Defer 連発で Reject(DeferExhausted)
- [ ] execution_metrics に signal_age_seconds / reject_reason 記録

**テスト条件**:
- Contract test: TTL 境界 (14s / 16s で挙動差)
- Contract test: Defer 連発
- Unit test: Risk 4 制約の各単体
- Unit test: PositionSizer 最小ロット境界

**リスク**:
- Defer 実装の複雑さ (非同期 + timeout) → MVP は sync + sleep で最小実装可能

**後続依存**: M12 paper smoke test

---

### 6.11 M11: Contract Tests Hardening

**目的**: D3 8.4 の 8 項目 contract test + 禁止 15 項目の CI lint を**全て機械検出できる**状態にする。

**入力**: D3 7. 禁止事項、D3 8.4 contract test

**変更対象**:
- `tests/contract/test_*` 既存 test の漏れを埋める
- `.github/workflows/ci.yml` に contract test 専用ジョブ追加
- `tools/lint/custom_checks.py` (禁止パターンの AST check 拡張)
- `.pre-commit-config.yaml` に禁止 lint 統合

**完了条件**:
- [ ] 契約テスト 8 項目が全て CI で green
- [ ] 禁止 15 項目のうち最低 10 項目が CI lint で機械検出 (grep + AST)
  - `datetime.now()` 直接呼出
  - `print()` 直接
  - `DELETE FROM` 直接発行
  - `TRUNCATE` / `DROP TABLE` migration 直接
  - `if backtest:` / `isinstance(broker, PaperBroker)` 分岐
  - `_verify_account_type_or_raise` 呼ばない Broker 実装
  - Common Keys の Repository 外書込
  - 乱数 seed なし
  - secret のログ出力
  - `notification_outbox` 経由の critical 通知
- [ ] 残り 5 項目はコードレビュー / 人間チェック対象として documented

**テスト条件**:
- CI が契約テスト全 green
- 意図的な違反 commit が CI / pre-commit で弾かれる

**リスク**:
- AST check の偽陽性 / 偽陰性 → 必要な例外を whitelist (`# noqa: CUSTOM` コメントで明示的許可)

**後続依存**: M12 前の品質確保

---

### 6.12 M12: Minimal Dashboard & Paper Smoke Test

**目的**: Streamlit 最小ダッシュボード + paper mode での end-to-end 疎通。**Iteration 1 ゴール達成**の最終関門。

**入力**: Phase 5 UI / Dashboard Query Service、D4 Runbook、全 M

**変更対象**:
- `src/fx_ai_trading/dashboard/app.py` (Streamlit メインエントリ)
- `src/fx_ai_trading/dashboard/panels/market_state.py` (相場状態評価)
- `src/fx_ai_trading/dashboard/panels/strategy_summary.py` (戦略別比較)
- `src/fx_ai_trading/dashboard/panels/meta_decision.py` (メタ戦略選択結果)
- `src/fx_ai_trading/dashboard/panels/positions.py` (ポジション状況)
- `src/fx_ai_trading/dashboard/panels/daily_metrics.py` (当日 PnL + 稼働状態)
- `src/fx_ai_trading/dashboard/panels/supervisor_status.py` (safe_stop / degraded)
- `src/fx_ai_trading/dashboard/panels/recent_signals.py` (直近シグナル)
- `src/fx_ai_trading/services/dashboard_query_service.py` (UI 用クエリ、cache 付)
- `scripts/ctl.py` (最小 CLI: start / stop / emergency-flat-all の雛形)
- `tests/integration/test_paper_smoke_end_to_end.py` (1 cycle 全パイプライン)

**完了条件**:
- [ ] Streamlit が `streamlit run src/fx_ai_trading/dashboard/app.py` で起動
- [ ] 7 パネル全てがデータ表示 (Mock data でも OK、最終的に DB 接続)
- [ ] `st.cache_data(ttl=5)` 必須適用 (DR-Q2 lint で強制)
- [ ] paper mode 疎通: demo OANDA → 1 cycle → 1 instrument の判断 → PaperBroker → 擬似 fill → ExitPolicy → close_event の end-to-end
- [ ] Supervisor メトリクス 9 項目が 1 分毎記録
- [ ] `ctl start` で Supervisor + Dashboard が起動
- [ ] `ctl emergency-flat-all` が stub で動作 (実発注はせず、log のみ)

**テスト条件**:
- Integration test: paper smoke end-to-end (1 cycle の完全な流れ)
- Manual test: Dashboard 表示確認
- Integration test: Supervisor start/stop

**リスク**:
- Streamlit のキャッシュ戦略 (大量 polling が二次DB を殺す、H3)  → cache ttl 強制 + connection pool 分離 (M2 で分離済)
- OANDA demo 接続の安定性 → fallback として fixture data で smoke test

**後続依存**: Iteration 1 完了 → Iteration 2 開始可

---

## 7. 推奨実装順序 (dependency graph)

```
M1 (Tooling)
  ├→ M2 (Schema)
  │   ├→ M3 (Config)      (並列可: M4 と)
  │   └→ M4 (Interfaces)  (並列可: M3 と)
  │       ↓
  │   M5 (Repository)  ← 必須直列
  │       ↓
  │   M6 (Broker/Notifier/Journal)  ← 必須直列
  │       ↓
  │   M7 (Supervisor)       M9 (Strategy)
  │       ↓                     ↓
  │   M8 (Outbox/Lifecycle)  M10 (Risk/Gate)
  │       └─────────┬───────────┘
  │                 ↓
  │           M11 (Contract tests harden)
  │                 ↓
  │           M12 (Dashboard + Smoke)
```

**並列可能**:
- M3 と M4 (独立、M5 で合流)
- M7 と M9 (M5 / M6 が揃った後、独立)

**並列禁止**:
- M1 → M2 → M5: 順序必須 (schema → config → repository)
- M7 → M8: Supervisor が Outbox の pause/resume を呼ぶ、先に Supervisor 骨格
- M11 は M3–M10 すべて完了後に harden (個別 contract test は各 M で都度追加)

---

## 8. コミット単位の例

マイルストーン M5 (Repository) を例に、1 サイクル単位を示す:

| Cycle | Commit 例 | ファイル数 |
|---|---|---|
| 5-1 | `feat(m5): add PostgreSQLAdapter skeleton with session management` | 2 |
| 5-2 | `feat(m5): add Repository base class with CommonKeysContext propagation` | 3 |
| 5-3 | `feat(m5): add OrderRepository with FSM enforcement` | 3 |
| 5-4 | `test(m5): add contract test for order status transition` | 1 |
| 5-5 | `feat(m5): add market data repositories (candles, ticks, events)` | 4 |
| 5-6 | `feat(m5): add strategy / meta / execution repositories` | 6 |
| 5-7 | `feat(m5): add observability repositories` | 5 |
| 5-8 | `feat(m5): add operations / aggregates / reference repositories` | 6 |
| 5-9 | `test(m5): integration test for Common Keys auto-propagation` | 2 |
| 5-10 | `contract(m5): add no-direct-delete CI lint` | 3 |

合計 10 サイクル、1 PR = 1 サイクル (または関連 2-3 サイクルを 1 PR に統合)。

---

## 9. paper 疎通可能なタイミング

- **M6 完了時点**: PaperBroker が単体で発注受付 (ただし Outbox なし、直接呼出)
- **M8 完了時点**: Outbox 経由で PaperBroker に発注可能 (Supervisor なしでも可)
- **M9 完了時点**: Strategy + Meta → Outbox → PaperBroker の細い疎通可能 (ExecutionGate なし)
- **M10 完了時点**: Risk + ExecutionGate 込みで完全な判断パイプライン
- **M12 完了時点**: Dashboard 含めた Iteration 1 の完成形、end-to-end smoke

**Decision (9-1)**: **M10 完了時点で paper mode の最小 e2e が走る**。M11 / M12 は品質向上 + UI 追加。

---

## 10. live 接続禁止期間

**Inherited Constraint (10-1)**: **Iteration 1 全期間を通じて `expected_account_type=live` への切替禁止**。

- `local` プロファイルは `demo` 固定 (6.18)
- OANDA 本番 API key を `.env` / Secret Provider に投入しない (demo API key のみ)
- `ctl --confirm-live-trading` フラグは**Iteration 2 以降**でのみ有効化
- 全 contract test / integration test は **demo account + PaperBroker / MockBroker** で実行

**Rationale**: Iteration 1 は skeleton 構築フェーズ、live 接続で誤発注リスクを冒さない。

---

## 11. backtest 実装の扱い

**Decision (11-1)**: Iteration 1 では **BacktestRunner Interface の宣言のみ** (D2 準拠)、**実体実装は Phase 7**。

- M4 (Domain Interfaces) で `BacktestRunner` Protocol 定義
- `BacktestRunner.run()` の実装は `raise NotImplementedError("Backtest engine scheduled for Phase 7")`
- 例外としてPhase 7 前倒しで実装する判断が出た場合 → `docs/iteration1_implementation_plan.md` に M13 として追加 (contract-change process)

**Rationale**: MVP paper smoke のみ Iteration 1 目標。backtest まで含めると工数超過リスク高。

---

## 12. MVP 到達条件

Iteration 1 完了 = MVP 到達。以下 10 項目**すべて**が成立:

1. [ ] M1–M12 すべてが完了 (完了条件を各々満たす)
2. [ ] `alembic upgrade head` で 46 テーブル + 旧名 View が作成される
3. [ ] `ctl start` で Supervisor の 16 Step 起動シーケンスが全て green で通る
4. [ ] PaperBroker 経由で 1 cycle 分足判断 → 発注 → 擬似約定 → 決済が end-to-end で完走
5. [ ] Streamlit の 7 パネルが全てデータ表示
6. [ ] 学習 UI (enqueue / status / history) 最小機能が動作 (LearningOps 本体は stub)
7. [ ] Supervisor safe_stop が正常発火・復帰可能
8. [ ] Contract test 8 項目 + 禁止 lint 10 項目が CI で green
9. [ ] PostgreSQL に全ログが付き、Common Keys + cycle_id / correlation_id で 1 本 SQL 分析可能
10. [ ] Notifier 二経路動作 (critical → File + Slack 同期、非 critical → outbox 経由)

---

## 13. Iteration 2 へ送るもの

Iteration 1 で**契約のみ確保、実装後回し**を Iteration 2 に送る:

- **OANDA live 接続** (demo → live 切替、手動 confirmation 運用)
- **EmailNotifier 実装** (SMTP / SES)
- **Reconciler Action Matrix 全ケース網羅** (MVP は 5-6 ケース)
- **Dashboard の残り 3 パネル** (トップ候補一覧 / 執行品質 / リスク状態 詳細 / 改善分析ビュー)
- **TSS (Trade Suitability Score) 計算** (MVP は空または固定値)
- **`dashboard_top_candidates` mart の本生成** (MVP は空)
- **二次DB (Supabase) の Projector 実装** (MVP は手動 snapshot / 空)
- **Emergency Flat CLI の 2-factor** (MVP は単純な CLI)
- **`multi_service_mode` 実運用** (MVP は Interface のみ)

---

## 14. Phase 7 へ送るもの

- **Backtest Engine 実体** (BacktestRunner.run() 実装、SlippageModel / LatencyModel 決定的実装、反実仮想計算)
- **AIStrategy shadow → active Promotion** (model_registry 状態遷移の自動化、OOS 判定)
- **相関双窓 regime tightening の MetaDecider Select 強制適用** (MVP は記録のみ)
- **CI 自動マイグレーションテスト** (MVP は手動)
- **Chaos Engineering 体系化** (fault injection シナリオ カタログ化)
- **Drift detection 本実装** (PSI / KL / 残差、MVP は契約のみ)
- **EVCalibrator v1 以降** (MVP は v0 ヒューリスティックのみ)
- **Cold Archive 実ジョブ** (Archiver Interface の実装、retention_policy 遵守)
- **Streamlit 卒業条件超過時の UI フロント刷新** (Next.js + FastAPI)

---

## 15. Phase 8 へ送るもの

- **OAuth / SSO Notifier** (Slack Bot Token への upgrade)
- **Slack 双方向運用** (コマンド受付、安全装置付き)
- **Dashboard SSO / マルチユーザ**
- **DR 訓練の月次体系化**
- **税務エクスポート GUI**
- **複数運用者向け権限分離** (Emergency Flat の 2-factor など)

---

## 16. Open Questions をどの Milestone で閉じるか

| Open Question (原籍) | 閉じる Milestone | 備考 |
|---|---|---|
| D1 Q1 (market_ticks_or_events type 列挙) | M4 / M5 | Interface 宣言時に enum 確定 |
| D1 Q2 (backtest_runs / backtest_metrics 扱い) | M2 | Alembic で追加作成 |
| D1 Q3 (positions 最新状態の View) | M2 / M5 | migration + Repository で選択 |
| D1 Q4 (meta_decisions_full View) | M5 | Repository のクエリで |
| D1 Q5 (具体列型) | M2 | Alembic 初期 migration で確定 |
| D2 BT-Q1–Q4 | M4 (Interface) / Phase 7 (実体) | Interface のみ Iteration 1 |
| D3 IC-Q1 (例外階層) | M3 / M4 | 例外 hierarchy を定義 |
| D3 IC-Q2 (DI コンテナ) | M4 / M5 | **Decision**: 手製 DI (簡易 factory)、injector ライブラリは Phase 7 判断 |
| D3 IC-Q3 (async/await 境界) | M3 / M6 / M8 | **Decision**: asyncio を主、CPU バウンドのみ ProcessPoolExecutor |
| D3 IC-Q4 (Repository tx スコープ) | M5 | caller 側で `with tx:` ブロック、Repository は参加のみ |
| D3 IC-Q5 (Feature 体積抑制) | Phase 7 | MVP は compact_mode で足りる |
| D4 OP-Q1 (ctl CLI) | M12 | `click` or `typer`、**Decision: click** |
| D4 OP-Q3 (systemd / nssm) | M12 / 運用時 | 雛形 docs を M12 で追加 |
| D5 RP-Q1–Q5 | Phase 7 | Cold Archive 実装時 |
| AH-Q1–Q3 | M1 | CI lint / サブエージェント prompt 整備 |
| DR-Q1–Q4 | M1 / M3 / Phase 7 | PR template / lint ツール / Secret 管理 |

---

## 17. 実装原則 (再掲 + 本書固有)

1. **契約を破らない**: D1–D5 / Phase 6 違反の実装をしない
2. **後戻り最小**: 依存根元から順 (M1 → M12)
3. **常に細く通す**: 各 M 完了時に main が壊れない
4. **Interface 先 / 実装後**: D3 に従った Protocol 先行
5. **Contract Test と実装は同期**: D3 8.4 / 8 項目は Interface 追加と同 PR
6. **live 接続禁止**: Iteration 1 全期間 demo only
7. **paper mode 最短で通す**: M10 完了時点で e2e 疎通
8. **Backtest 実体は Phase 7**: Iteration 1 は Interface 宣言のみ
9. **並列は 2 箇所のみ**: M3/M4 + M7/M9 の 2 組、それ以外は直列
10. **1 サイクル 1 責務**: `docs/automation_harness.md` 3. に従う

---

## 18. Open Questions (本書固有)

| ID | 論点 | 解決予定 |
|---|---|---|
| IP-Q1 | Iteration 1 全体の絶対日数コミット (5-8 週間目安だが、Claude Code 主体のペースで変動) | 実作業開始後に再評価 |
| IP-Q2 | M1-M12 のうち人間運用者が介入すべきタイミング (レビュー粒度) | `docs/automation_harness.md` 8. に従う |
| IP-Q3 | OANDA demo key 取得方法 / テスト環境セットアップ手順 | M1 で README 整備 |

---

## 19. Summary (計画固定点)

本書は以下を**Iteration 1 の実装契約**として固定する:

1. **12 マイルストーン M1–M12** の目的・入力・完了条件・テスト条件・リスク・後続依存を明記
2. **依存グラフ**: M1→M2→{M3||M4}→M5→M6→{M7||M9}→{M8||M10}→M11→M12
3. **paper 疎通は M10 時点**、M12 で Dashboard 含めた完成形
4. **live 接続は Iteration 1 全期間禁止** (demo only、`local=demo` 固定)
5. **Backtest 実体は Phase 7**、Iteration 1 は Interface 宣言のみ
6. **MVP 到達条件 10 項目**の全成立で Iteration 1 完了
7. **コミット単位例** (M5 で 10 サイクル) を示し、大きな PR を作らない原則を再確認
8. **Open Questions は各 M で閉じる**、閉じた内容は該当 docs の Decision 節に記録
9. **Iteration 2 / Phase 7 / Phase 8 送り項目**を明示し、Iteration 1 膨張を防ぐ
10. 本書を破る実装は**計画違反**、`development_rules.md` の contract-change process で変更可
