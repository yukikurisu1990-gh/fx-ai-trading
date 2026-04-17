# D3. Implementation Contracts

## Purpose
MVP 実装に必要な **Interface / Service / Repository / Adapter / Assertion / テスト観点**を契約として固定する。実装者が本書のみを読めば迷わず**責務境界と入出力の約束**を理解できる状態を目指す。Phase 6 までに宣言された抽象層を、具体的な**疑似シグネチャ**と**不変条件**に落とし込む。

## Scope
- アーキテクチャレイヤの責務と非責務
- 全主要 Interface の name / purpose / methods / input / output / side effects / idempotency / failure modes / retry / invariants
- Repository 契約と Common Keys 伝搬
- 外部アダプタ契約 (Broker / PriceFeed / Notifier / SecretProvider)
- Scheduler / Batch / Job 契約
- Config / Assertion 契約 (account_type, config_version, NTP 等)
- live / backtest 共通化原則
- 禁止アンチパターン一覧
- テスト観点 (unit / integration / simulation consistency / contract)

## Out of Scope
- 実 Python コード (Iteration 1 以降)
- 具体的な例外クラス階層の設計 (Iteration 1)
- DI コンテナの構成 (Iteration 1)
- Alembic migration DDL

## Dependencies
- `docs/schema_catalog.md` (D1): Repository の対象スキーマ
- `docs/backtest_design.md` (D2): backtest 固有契約との整合
- `docs/retention_policy.md` (D5): Archiver / Retention Enforcer Interface
- `docs/design.md` Section 4.3 (Core Interfaces 列挙)
- `docs/phase6_hardening.md` 6.1-6.21 (全契約の源泉)

## Related Docs
- `docs/operations.md` (D4): Interface から派生する運用手順

---

## 1. アーキテクチャレイヤの責務

### 1.1 レイヤ一覧

| レイヤ | 責務 | 非責務 |
|---|---|---|
| **Ingestion** | OANDA API からの取得 + Market raw 書込 (market_candles / market_ticks_or_events / economic_events) | 特徴量計算 / 発注 |
| **Feature Generation** | Feature Service で特徴量計算 (決定的、feature_version 付与) | 戦略判断 / モデル推論のトリガ |
| **Prediction** | AIStrategy が ML モデル推論、predictions 書込 | 他戦略評価 / EV 計算 |
| **Strategy Decision** | 3 戦略 (AI/MA/ATR) の並列評価 + EV 計算 + MetaDecider (Filter/Score/Select) | 発注 / 決済 |
| **Risk Check** | PositionSizer + RiskManager.accept で制約適用 | 発注 HTTP / 約定反映 |
| **Order Submission** | trading_signals → orders(PENDING) → ExecutionGate → Broker.place_order (Outbox 経由) | 戦略判断 / Meta |
| **Execution Reconciliation** | transaction stream 受信 + MidRunReconciler + 起動時 Reconciler | 新規発注 |
| **Account Sync** | account_snapshots + margin 監視 | 発注指示 |
| **Persistence** | Repository + PersistenceAdapter (PostgreSQL / SQLite dev) | ドメイン判断 |
| **Backtest Engine** | BacktestRunner + PaperBroker + sim_clock | live 発注 |
| **Monitoring / Alerting** | Supervisor + Notifier (2 経路) + SafeStopJournal | ドメイン判断 |

### 1.2 責務境界の不変条件 (Inherited Constraints)

- **Strategy Decision は発注しない** (Order Submission の責務)
- **Order Submission は戦略判断しない**
- **Persistence はドメイン judgment を持たない** (Repository 経由の CRUD のみ)
- **Monitoring は Trading Core をブロックしない** (Phase 2 非同期境界)
- **Backtest Engine は live データを触らない** (閉じた系、OANDA 非通信)

---

## 2. 主要 Interface 一覧

以下、MVP 実装で作成すべき Interface を責務分類ごとにまとめる。**疑似シグネチャ**は Python 風だが、実装は Iteration 1 で最終化する。

### 2.1 Ingestion 層

#### 2.1.1 `PriceFeed` Interface

```
PriceFeed:
  # 取得 (live / backtest 共通)
  list_active_instruments() -> list[Instrument]
  get_candles(instrument, tier, from_utc, to_utc) -> list[Candle]
  get_latest_price(instrument) -> PriceTick
  subscribe_price_stream(instruments: list) -> AsyncIterator[PriceEvent]
  subscribe_transaction_stream(account_id) -> AsyncIterator[TransactionEvent]
```

- **Purpose**: Market raw データの抽象化。OANDA 実装と PaperBroker 実装 (backtest) で差し替え可能
- **Input contract**: instrument は `instruments` テーブルに存在する code
- **Output contract**: PriceEvent / TransactionEvent は immutable、Common Keys (event_time_utc, received_at_utc) 付与
- **Side effects**: なし (純粋な取得のみ)
- **Idempotency**: 同一入力・同一時点で同一出力 (live は外部 API 依存なので時点変化で変わる、それは OK)
- **Failure modes**: API timeout / auth 失敗 / rate limit 超過 / stream 切断
- **Retry policy**: Phase 6.14 の RetryPolicy を適用 (caller 側)、`PriceFeed` 自身はリトライしない
- **Invariants**: 返却データは時系列昇順

**Implementations**: `OandaPriceFeed` (live) / `HistoricalPriceFeed` (backtest、D1 market_* 由来)

#### 2.1.2 `MarketDataIngester` Service

```
MarketDataIngester:
  ingest_candles_for_instrument(instrument, tier, period) -> IngestResult
  ingest_tick_stream_batch(instrument, period) -> IngestResult
  ingest_economic_events(from_utc, to_utc) -> IngestResult
```

- **Purpose**: `PriceFeed` から取得したデータを Repository 経由で一次DB に書込
- **Output**: `IngestResult` (written_count / skipped_count / errors)
- **Side effects**: D1 `market_candles` / `market_ticks_or_events` / `economic_events` への書込
- **Idempotency**: 同一期間の再実行で重複を挿入しない (UPSERT or `ON CONFLICT DO NOTHING`)
- **Failure modes**: Feed 側 error / DB 書込 error
- **Invariants**: 書込後に Market raw データのカバレッジは単調増加

### 2.2 Feature Generation 層

#### 2.2.1 `FeatureBuilder` Interface

```
FeatureBuilder:
  build(instrument: str, tier: str, cycle_id: UUID, as_of_time: datetime) -> FeatureSet
  get_feature_version() -> str  # 決定的バージョン (6.10)

FeatureSet:
  feature_version: str
  feature_hash: str  # SHA256 short
  feature_stats: dict  # mean / std / min / max / null_count / feature_count per feature
  sampled_features: dict  # top-N important feature の生値 (compact_mode)
  full_features: Optional[dict]  # 全量 (non-compact 時のみ)
  computed_at: datetime
```

- **Purpose**: 決定的特徴量計算 (6.10)
- **Input contract**: `as_of_time` より未来のデータ参照禁止 (look-ahead 防止、contract test で検証)
- **Output contract**: 同一入力 + 同一 feature_version → バイト等価な feature_hash
- **Side effects**: `feature_snapshots` 書込 (Repository 経由)
- **Idempotency**: 必須 (同 cycle_id × instrument で再計算しても同結果)
- **Failure modes**: 入力データ欠損 → FeatureSet を返さず `FeatureUnavailable` 例外 (caller は当該 instrument を no_trade 化)
- **Retry policy**: caller 側で 1 回まで、連続失敗は `data_quality_events`
- **Invariants (critical)**:
  - 現在時刻 `now()` を参照しない
  - seed 未固定乱数を使わない
  - 順序非決定な並列 reduce を使わない
  - 浮動小数の非決定的 reduce を禁止

**Implementations**: `DeterministicFeatureBuilder` (Iteration 1 具実装)

### 2.3 Prediction 層

#### 2.3.1 `ModelRegistry` Interface

```
ModelRegistry:
  load(model_id: str) -> Model
  save(model: Model, metadata: ModelMetadata) -> str  # model_id
  promote(model_id: str, to_state: str)  # stub/shadow/active/review/demoted
  demote(model_id: str, reason: str)
  get_active(strategy_type: str) -> Optional[Model]
  get_shadow(strategy_type: str) -> Optional[Model]
  list_by_state(state: str) -> list[ModelMetadata]
```

- **Purpose**: 6.11 AIStrategy lifecycle 管理
- **Invariants**: 同時に active 状態のモデルは strategy_type × instrument ごとに最大 1 つ
- **Side effects**: `model_registry` テーブル書込
- **Idempotency**: promote / demote は冪等 (既に目的状態なら no-op)
- **Failure modes**: 同時 active 競合 → 排他制御 (advisory lock)

#### 2.3.2 `Predictor` Interface

```
Predictor:
  predict(features: FeatureSet, context: PredictionContext) -> Prediction
  get_model_id() -> str
```

- **Purpose**: AI モデルの推論ラッパー
- **Output**: `Prediction` (value / confidence / model_id)
- **Side effects**: `predictions` 書込
- **Idempotency**: 決定的モデルは同一入力で同一出力
- **Failure modes**: モデルロード失敗 → 呼び出し側 (AIStrategy) で Stub フォールバック

### 2.4 Strategy Decision 層

#### 2.4.1 `StrategyEvaluator` Interface

```
StrategyEvaluator:
  evaluate(instrument: str, features: FeatureSet, context: StrategyContext) -> StrategySignal

StrategySignal:
  strategy_id: str
  strategy_type: str  # 'AI' | 'MA' | 'ATR'
  strategy_version: str
  signal: str  # 'long' | 'short' | 'no_trade'
  confidence: float
  ev_before_cost: float
  ev_after_cost: float  # -> EVEstimator と連携
  tp: float  # price or pips
  sl: float
  holding_time_seconds: int
  enabled: bool  # 6.17 strategy_enabled が false なら評価されない (戻り値には出ない)
```

- **Purpose**: 戦略ごとのシグナル生成
- **Idempotency**: 同入力で同出力 (seed 管理下なら)
- **Side effects**: `strategy_signals` 書込 (評価フレームワーク側)
- **Failure modes**: 推論失敗 (AI) → AIStrategyStub フォールバック、他戦略は影響なし
- **Invariants**: enabled=false の戦略は呼び出されない (Strategy Engine 側で pre-filter)

**Implementations (MVP)**:
- `AIStrategyStub`: 固定 confidence、lifecycle_state=stub 時の実装
- `AIStrategyShadow`: 本物 AI、predictions 書込のみ、signal は MetaDecider に渡さない
- `AIStrategyActive`: 本物 AI、MetaDecider に signal を渡す
- `MAStrategy`: 移動平均ベース
- `ATRStrategy`: ATR ベース

Decision (2.4.1-1): `StrategyEvaluator` は**純粋関数的**であるべき (副作用は評価フレームワーク側で記録)。戦略実装内で DB を触らない。

#### 2.4.2 `EVEstimator` Interface

```
EVEstimator:
  estimate(signal: StrategySignal, cost: Cost) -> EVEstimate

EVEstimate:
  value: float  # EV_after_cost
  confidence_interval: tuple[float, float]  # (lower, upper)
  components: dict  # {'p_win', 'avg_win', 'avg_loss', 'cost_total'}
```

- **Purpose**: EV_after_cost + 信頼区間の計算
- **Side effects**: `ev_breakdowns` 書込 (評価フレームワーク側)
- **Idempotency**: 決定的 (入力が決まれば出力も決まる)
- **Failure modes**: データ不足で confidence_interval が過大 → MetaDecider Score 段で低位重み付け
- **Invariants**: `value = p_win * avg_win - (1-p_win) * avg_loss - cost_total`

**Implementations**:
- `HeuristicEVEstimator` (v0, MVP): spread に対する固定 prior
- `BacktestCalibratedEVEstimator` (v1, Phase 7+): 過去データ学習
- `OnlineCalibrated EVEstimator` (v2, 後続): Bayesian 更新

#### 2.4.3 `CostModel` Interface

```
CostModel:
  compute(instrument: str, intent: TradingIntent) -> Cost

Cost:
  spread: float
  slippage_expected: float
  commission: float
  swap_rate_per_day: float
  total: float
```

- **Purpose**: Cost 構成要素の計算
- **Side effects**: なし
- **Idempotency**: 決定的

#### 2.4.4 `MetaDecider` Interface

```
MetaDecider:
  decide(candidates: list[StrategySignal], context: MetaContext) -> MetaDecision

MetaDecision:
  meta_decision_id: UUID
  cycle_id: UUID
  selected_instrument: Optional[str]  # None iff no_trade
  selected_strategy_id: Optional[str]
  selected_signal: Optional[str]
  selected_tp: Optional[float]
  selected_sl: Optional[float]
  no_trade: bool
  no_trade_reasons: list[NoTradeReason]  # 6.16 taxonomy
  filter_snapshot: dict  # Filter 段の入力と除外履歴
  score_snapshot: dict  # Score 段の入力と合成値
  select_snapshot: dict  # Select 段の候補と選択根拠
  score_contributions: list[dict]  # 6.7 成分寄与
  concentration_warning: bool  # 単一成分寄与 > 60%
  active_strategies: list[str]  # 6.17 その時点で有効だった戦略
  regime_detected: bool  # 6.8 相関 regime
```

- **Purpose**: Filter → Score → Select の 3 段合議
- **Idempotency**: 決定的 (同一 candidates + 同一 context → 同一 MetaDecision)
- **Side effects**: `meta_decisions` / `pair_selection_runs` / `pair_selection_scores` 書込
- **Failure modes**: 全候補 Filter で除外 → no_trade (with reasons) / Score で ev_below_threshold 連発 → no_trade / Select で組合せなし → no_trade
- **Invariants**: `no_trade == true` ⟺ `selected_instrument is None`

**Implementations (MVP)**: `RuleBasedMetaDecider` — Filter/Score/Select すべてルール実装

### 2.5 Risk Check 層

#### 2.5.1 `PositionSizer` Interface

```
PositionSizer:
  size(account_balance: float, risk_pct: float, sl_pips: float, instrument: Instrument) -> SizeResult

SizeResult:
  size_units: int  # 0 の場合は no_trade(SizeUnderMin)
  reason: Optional[str]  # 'size_under_min' 等
```

- **Purpose**: 1〜2% リスクに基づくロット計算
- **Invariants**: 返却 size_units は必ず min_lot の倍数、または 0

#### 2.5.2 `RiskManager` Interface

```
RiskManager:
  accept(decision: MetaDecision, exposure: Exposure) -> RiskAcceptResult

RiskAcceptResult:
  accepted: bool
  reject_reason: Optional[str]  # 6.16 'risk.*' taxonomy
  exposure_after: Optional[Exposure]  # accepted 時のみ

Exposure:
  per_currency: dict[str, float]  # 通貨別 net
  per_direction: dict[str, dict]  # 通貨別 long/short 合計
  total_risk_correlation_adjusted: float
  concurrent_positions: int
```

- **Purpose**: 4 制約 (同時ポジ / 単一通貨 / net 方向 / 総リスク / 相関) の適用
- **Side effects**: `risk_events` 書込
- **Idempotency**: 決定的
- **Invariants (6.18 継承)**: accept は `orders` 行生成の前段、reject 時は `trading_signals` 生成せず no_trade

### 2.6 Order Submission 層

#### 2.6.1 `Broker` Interface (最重要)

```
Broker:
  account_type: str  # 'demo' | 'live' (6.18 必須プロパティ)

  place_order(request: OrderRequest) -> OrderResult
  cancel_order(order_id: str) -> CancelResult
  get_positions(account_id: str) -> list[BrokerPosition]
  get_pending_orders(account_id: str) -> list[BrokerOrder]
  get_recent_transactions(since: str) -> list[TransactionEvent]

OrderRequest:
  client_order_id: str  # ULID フォーマット (6.4)
  account_id: str
  instrument: str
  side: str  # 'long' | 'short'
  size_units: int
  tp: Optional[float]
  sl: Optional[float]
  expires_at: Optional[datetime]
```

- **Purpose**: broker 通信の抽象。OANDA / Paper / Mock で差し替え
- **Critical Invariant (6.18)**: `place_order` 内部で `self.account_type == self._startup_verified_type` を assert、不一致で `AccountTypeMismatch` 例外 + safe_stop(account_type_mismatch_runtime) 発火
- **Critical Invariant (6.4)**: `client_order_id` は ULID、重複時の broker 側挙動で冪等性担保
- **Idempotency**: place_order は同 client_order_id で冪等 (broker 契約)
- **Side effects**: HTTP 通信 (live) / 擬似処理 (paper/mock)
- **Failure modes**: API timeout → retry / reject → 再送せず記録 / account_type mismatch → safe_stop / rate limit → RateLimiter で抑制
- **Retry policy**: Broker 内部では Retry しない。caller (ExecutionAssist / OutboxProcessor) が RetryPolicy 適用

**Implementations**:
- `OandaBroker` (live)
- `PaperBroker` (backtest / paper mode、SlippageModel + LatencyModel 注入)
- `MockBroker` (contract test / unit test 用)

**Decision (2.6.1-1)**: `Broker` 基底クラスで `_verify_account_type_or_raise()` を protected method として提供し、全実装クラスは `place_order` の冒頭で呼び出し必須 (契約テストで検証)。

#### 2.6.2 `ExecutionGate` Interface

```
ExecutionGate:
  check(intent: TradingIntent, realtime_context: RealtimeContext) -> GateResult

GateResult:
  decision: str  # 'approve' | 'reject' | 'defer'
  reason_code: Optional[str]  # 'SpreadTooWide' | 'SuddenMove' | 'StaleSignal' | 'BrokerUnreachable' | 'SignalExpired' | 'DeferExhausted' | ...
  defer_until: Optional[datetime]  # 'defer' 時
  signal_age_seconds: float  # 6.15 TTL 判定用に計算した経過秒数
```

- **Purpose**: 秒単位の発注直前ゲーティング
- **Invariants (6.15 TTL)**: check の**最初**に `now() - trading_signal.created_at > signal_ttl_seconds` を判定、超過で即 `reject(SignalExpired)`
- **Invariants (6.15 Defer)**: Defer 復帰時に TTL 超過なら `reject(SignalExpired)` に自動遷移
- **Side effects**: `execution_metrics` 書込
- **Idempotency**: 冪等 (同じ intent + 同じ context なら同結果)

#### 2.6.3 `OutboxProcessor` Interface

```
OutboxProcessor:
  start()  # 常駐ループ
  stop()
  process_one(outbox_event_id: UUID) -> ProcessResult  # テスト用
  pause_dispatch()  # safe_stop 中の呼び出し
  resume_dispatch()
```

- **Purpose**: Outbox 経由の Broker 発注 dispatch (6.6)
- **Side effects**: `outbox_events.status` 遷移、`orders.status` 遷移、`execution_metrics` 書込
- **Invariants**:
  - safe_stop 中は新規 dispatch しない (pause_dispatch が呼ばれる)
  - dispatching 中の outbox_event は safe_stop でも完了まで待つ (6.1 in-flight)
  - 同じ outbox_event_id を 2 回 dispatch しない (排他)
- **Failure modes**: Broker タイムアウト → orders.status=FAILED + outbox_events.status=failed + retry_events 記録

#### 2.6.4 `OrderLifecycleService` Interface

```
OrderLifecycleService:
  submit(trading_signal: TradingSignal) -> SubmitResult
  on_transaction_event(event: TransactionEvent)  # stream からのコールバック
  cancel(order_id: str, reason: str) -> CancelResult
```

- **Purpose**: orders の state machine (PENDING → SUBMITTED → FILLED/CANCELED/FAILED) 管理
- **Invariants**:
  - 状態遷移は前進のみ (後退禁止)
  - 各遷移で `outbox_events` イベント追加
  - `positions` 時系列への反映を保証

### 2.7 Execution Reconciliation 層

#### 2.7.1 `Reconciler` Interface

```
Reconciler:
  reconcile_on_startup(context: StartupContext) -> ReconcileResult
  reconcile_midrun(trigger: MidrunTrigger) -> ReconcileResult

ReconcileResult:
  matches: int
  auto_corrections: list[Correction]
  manual_required: list[Discrepancy]
  degraded_mode_required: bool
```

- **Purpose**: 6.12 Reconciler Action Matrix の実装
- **Invariants**: OANDA を truth source として扱う (6.2)
- **Invariants (6.12)**: Action Matrix の**自動補正可能範囲のみ自動実施**、それ以外は degraded + 手動待ち
- **Side effects**: `reconciliation_events` 書込、`orders.status` 修正、Notifier 通知 (critical)
- **Failure modes**: OANDA 接続不可 → degraded、自動補正不能 → 手動待ち

#### 2.7.2 `MidRunReconciler` Interface

```
MidRunReconciler:
  start()  # 常駐ループ + 定期 drift check (15 分毎)
  stop()
  on_stream_gap_detected(gap_duration: float)  # StreamWatchdog コールバック
  set_priority(priority: str)  # 'low' | 'high' (6.2 優先度運用)
```

- **Purpose**: 6.2 Mid-Run Reconciler (稼働中の整合補完)
- **Invariants (6.2 優先度)**:
  - 平常時は priority='low' (`rate_limit_reconcile_rps=2`)
  - stream gap 補完中は priority='high' に一時昇格
  - 補完完了後 auto revert to 'low'

### 2.8 Account Sync 層

#### 2.8.1 `AccountSnapshotter` Interface

```
AccountSnapshotter:
  take_snapshot(account_id: str, trigger_reason: str) -> AccountSnapshot
```

- **Purpose**: `account_snapshots` の取得 (6.14 margin 含む)
- **Trigger reasons (契約)**: `order` / `fill` / `close` / `hourly` / `daily_close` / `manual`
- **Side effects**: `account_snapshots` 書込、margin 閾値超過時は `risk_events` + Notifier

### 2.9 Persistence 層

#### 2.9.1 `Repository` Interface (ジェネリック)

```
Repository[T]:
  insert(entity: T, context: CommonKeysContext) -> T
  get(entity_id: ID) -> Optional[T]
  update(entity: T, context: CommonKeysContext) -> T  # MUT テーブルのみ
  upsert(entity: T, context: CommonKeysContext) -> T  # UPS テーブルのみ
  find(criteria: dict) -> list[T]
```

- **Purpose**: D1 Repository 契約。Common Keys 自動伝搬 (D1 3.3)
- **Invariants (D1 3.3)**:
  - 書込時に `CommonKeysContext` から run_id / environment / code_version / config_version を自動 merge
  - アプリコードから明示的に Common Keys を書くのは禁止 (Repository が自動)
- **Failure modes**:
  - Critical tier 書込失敗 → safe_stop 発火 (呼出側の責務)
  - Important tier 書込失敗 → Repository 内で retry + ログ、最終失敗は Notifier warning
  - Observability tier 書込失敗 → silent drop (メトリクスのみ)

#### 2.9.2 `PersistenceAdapter` Interface

```
PersistenceAdapter:
  get_engine() -> SQLAlchemyEngine
  get_session() -> SQLAlchemySession
  execute_analytics(query: str, params: dict) -> list[Row]  # Direct SQL (Phase 2 2 層化)
```

- **Purpose**: 一次DB の接続・session 管理、Repository の土台
- **Implementations**: `PostgreSQLAdapter` (本番) / `SQLiteAdapter` (dev、`single_process_mode × local` 限定)
- **Invariants (D5)**:
  - DELETE 直接発行禁止 (Archiver Interface 経由のみ)
  - TRUNCATE / DROP 禁止 (本番・準本番)

#### 2.9.3 `Archiver` Interface (D5 からの依頼)

```
Archiver:
  run_cold_archive(table_name: str, partition_key: str) -> ArchiveResult
  verify_archive(archive_id: UUID) -> VerifyResult
  delete_after_verified(archive_id: UUID) -> DeleteResult
  list_pending_archives() -> list[PendingArchive]
```

- **Purpose**: D5 `Cold アーカイブ 3 段プロセス` の実装点
- **MVP 実装要件**: Interface のみ定義、実 Archive ジョブは Phase 7 以降
- **Invariants (D5)**: Verify 失敗時は絶対に Delete しない

### 2.10 Monitoring / Alerting 層

#### 2.10.1 `Notifier` Interface (6.13)

```
Notifier:
  send(event: NotifyEvent, severity: str, payload: dict) -> NotifyResult

# Two-path dispatch
NotifierDispatcher:
  dispatch_direct_sync(event: NotifyEvent, ...) -> None  # safe_stop 系 critical
  dispatch_via_outbox(event: NotifyEvent, ...) -> None  # 非 critical
```

- **Purpose**: 6.13 Notifier Infrastructure
- **Critical Invariants (6.13)**:
  - **Critical イベント** (`safe_stop.fired` / `db.critical_write_failed` / `stream.gap_sustained` / `reconciler.mismatch_manual_required` / `ntp.skew_reject` 等) は **outbox 経由禁止**、**FileNotifier への fsync + 利用可能な全外部 Notifier への同期直接送信**
  - **非 critical** は `notification_outbox` 経由 (非同期)
  - `FileNotifier` の書込は**常に成功** (最終防波堤、DB 非依存)
- **Implementations**:
  - `FileNotifier` (常時必須)
  - `SlackNotifier` (MVP 必須)
  - `EmailNotifier` (Phase 7 任意)

#### 2.10.2 `SafeStopJournal` Interface (6.1)

```
SafeStopJournal:
  write(event: SafeStopEvent) -> None  # 同期 fsync
  read_recent(limit: int) -> list[SafeStopEvent]
  reconcile_with_db(supervisor_event_repo: Repository) -> ReconcileJournalResult
```

- **Purpose**: 6.1 SafeStopJournal (ローカル fsync チャネル)
- **Invariants**:
  - 書込は fsync まで同期、blocking
  - 単一プロセスのみ書込 (file lock)
  - 起動時に DB と突合、journal 正本で DB 補完

#### 2.10.3 `Supervisor` Interface

```
Supervisor:
  start()
  stop()
  health() -> HealthStatus
  safe_stop(reason: str) -> None
  resume_from_safe_stop() -> None
  report_metric(name: str, value: float, tags: dict)
```

- **Purpose**: プロセス監視・安全停止・健全性確認 (Phase 1 / 6.14)
- **Invariants**:
  - `safe_stop(reason)` は 6.1 シーケンス (journal → loop stop → notifier → DB) を実行
  - `report_metric` は最小実装 (CPU/memory/RSS/DB 接続数を 1 分毎記録、Phase 7 で Prometheus 化)

### 2.11 Backtest 層 (D2 参照)

#### 2.11.1 `BacktestRunner` Interface

```
BacktestRunner:
  run(config: BacktestConfig) -> BacktestRunId
  get_status(run_id: BacktestRunId) -> BacktestStatus
  cancel(run_id: BacktestRunId) -> None
```

- **Purpose**: D2 backtest engine のエントリポイント
- **Invariants (D2)**:
  - live / backtest でロジック分岐禁止 (Broker / Clock 差し替えのみ)
  - 決定性保証 (seed / feature_version / model_version / config_version 固定で同出力)
  - look-ahead 禁止 (as_of_time 強制、contract test で検証)

#### 2.11.2 `SlippageModel` / `LatencyModel` Interfaces (D2)

```
SlippageModel:
  compute(order: OrderRequest, market_state: MarketState, seed: int) -> SlippageResult

LatencyModel:
  compute(order: OrderRequest, seed: int) -> LatencyMs
```

- **Purpose**: PaperBroker の決定的シミュレーション
- **Invariants**: seed 固定で再現可能

### 2.12 Scheduler / Batch / Job 層

#### 2.12.1 `JobScheduler` Interface

```
JobScheduler:
  enqueue(job: Job) -> JobId
  cancel(job_id: JobId) -> None
  get_status(job_id: JobId) -> JobStatus
  list(filter: JobFilter) -> list[JobSummary]
```

- **Purpose**: `system_jobs` に対応する job 実行管理
- **MVP 対象 Job types**:
  - `learning_job` (LearningOps)
  - `aggregator_job` (Aggregator: strategy_performance / meta_strategy_evaluations / daily_metrics)
  - `cold_archive_job` (D5、Phase 7 以降)
  - `backtest_run_job` (D2)
- **Invariants**:
  - ジョブ実行中は `system_jobs.status=running`、完了で `succeeded` / `failed`
  - 二重実行防止 (同一 job_type + key で排他)

#### 2.12.2 `Aggregator` Interface

```
Aggregator:
  rollup(window_class: str, window_start: datetime, target_tables: list[str]) -> AggregateResult
```

- **Purpose**: Phase 3 / 6.11 の Aggregator (strategy_performance / meta_strategy_evaluations / daily_metrics 生成)
- **Invariants (Phase 3 / 6.11 / 6.17)**:
  - idempotent (同入力で同出力)
  - `strategy_version` / `feature_version` / enabled 切替点を跨ぐ集計を禁止
  - `meta_strategy_evaluations` の反実仮想は `meta_eval_protocol_version` で版管理

### 2.13 Config / Assertion 層

#### 2.13.1 `ConfigProvider` Interface (6.19 対応)

```
ConfigProvider:
  get(name: str, default: Any) -> Any
  get_all() -> dict
  get_config_version() -> str
  compute_config_version() -> tuple[str, dict]  # (version, source_breakdown)
  reload() -> None  # 起動時のみ呼ぶ、稼働中は禁止
```

- **Purpose**: 6.19 config_version 導出契約
- **Invariants (6.19)**:
  - 起動時に 1 回 `compute_config_version()` を呼び、`supervisor_events` に source_breakdown 付きで記録
  - 前回 run との不一致は Notifier info で通知
  - secret 値は effective_config に含めない (SHA256 参照のみ)
  - canonical JSON 化で決定的

#### 2.13.2 `SecretProvider` Interface

```
SecretProvider:
  get(secret_key: str) -> str
  get_hash(secret_key: str) -> str  # SHA256[:16]、config_version 計算用
  list_keys() -> list[str]  # value 非取得
```

- **Purpose**: 機微情報の安全な取得 (Phase 2 Config 階層)
- **Invariants**:
  - value をログ化しない (レビュー + lint で検出)
  - config_version 計算には get_hash のみ使用 (6.19)

#### 2.13.3 `AccountTypeAssertion` (6.18)

```
AccountTypeAssertion:
  verify_at_startup(broker: Broker, expected: str) -> None
    # 不一致で raise AccountTypeMismatch + Notifier critical + exit
  verify_before_order(broker: Broker) -> None
    # 不一致で raise + safe_stop(account_type_mismatch_runtime)
```

- **Purpose**: 6.18 account_type safety の実装
- **Invariants (6.18)**:
  - `Broker.place_order` 実装は内部で `verify_before_order` を**必ず呼ぶ**
  - 契約テストで全 Broker 実装がこのパターンに従うか検証

#### 2.13.4 `NtpChecker` (6.14)

```
NtpChecker:
  check_at_startup() -> NtpStatus  # 500ms 超 warn / 5s 超 reject
  check_periodic() -> NtpStatus
```

- **Purpose**: 6.14 NTP 起動検査 (二段階)
- **Invariants**:
  - `ntp_skew_reject_ms=5000` 超で起動拒否 (ローカルファイルログ + 通知後 exit)
  - `ntp_skew_warn_ms=500` 超で警告 + 起動継続

### 2.14 Event / Transport 層

#### 2.14.1 `EventBus` Interface

```
EventBus:
  publish(topic: str, event: Event) -> None
  subscribe(topic: str, handler: Callable) -> SubscriptionId
  unsubscribe(subscription_id: SubscriptionId)
```

- **Purpose**: 系統間通信 (Phase 2 2.4)
- **Invariants (Phase 2)**:
  - delivery semantics は **at-least-once + idempotent consumer**
  - 3 execution mode で同一 Interface (実装差し替え)
- **Implementations**:
  - `InProcessEventBus` (single_process_mode、MVP 既定)
  - `LocalQueueEventBus` (multi_service_mode、Phase 7+)
  - `NetworkBusEventBus` (container_ready_mode、Phase 8+)

---

## 3. Repository 契約の詳細

### 3.1 Common Keys 自動伝搬 (D1 3.3 継承)

Repository の書込メソッドは **`CommonKeysContext` を必須引数**として受ける:

```
CommonKeysContext:
  run_id: UUID  # Supervisor が起動時に生成
  environment: str  # 'local' | 'vps' | 'aws' | 'backtest'
  code_version: str  # ビルド時埋込
  config_version: str  # 6.19 起動時計算
  cycle_id: Optional[UUID]  # 分足サイクル中のみ
  correlation_id: Optional[UUID]  # 発注 lifecycle 中のみ
  order_id: Optional[str]  # 発注後のみ
  feature_version: Optional[str]  # 特徴量依存書込のみ
  account_type: Optional[str]  # orders / account_snapshots 書込時
```

- アプリ層の呼び出し側は必要なスコープで `CommonKeysContext` を生成・継承
- Repository は書込時に対象テーブルの Common Keys 列に自動 merge
- アプリコードから Common Keys 列を明示的に渡すのは**禁止** (レビュー + 契約テストで検出)

### 3.2 トランザクション境界

```
with repository.transaction() as tx:
  order = tx.orders.insert(order_entity, ctx)
  outbox_event = tx.outbox_events.insert(outbox_entity, ctx)
  # commit or rollback
```

- **Invariants (6.6 Outbox)**: `orders` 書込と `outbox_events` 書込は**同一トランザクション**で commit
- Critical tier の書込は commit 確認後に後続処理

### 3.3 状態遷移 (MUT テーブル)

`orders.status` の前進のみ許可、後退禁止:

```
OrderRepository:
  transition(order_id: str, from_status: str, to_status: str, ctx: CommonKeysContext) -> TransitionResult
```

- `from_status` 指定で楽観ロック (現在の status と一致しない場合は失敗)
- 遷移ログを `supervisor_events` に別途記録

---

## 4. Assertion 契約 (まとめ)

MVP で**機械的に機能する assertion**を以下にまとめる:

| Assertion | When | Fail Action | 根拠 |
|---|---|---|---|
| **NTP 起動検査** | 起動時 | 500ms 超 warn (continue) / 5s 超 reject (exit) | 6.14 |
| **Account Type 起動検査** | 起動時 | 不一致で exit + Notifier critical | 6.18 |
| **Account Type 発注前検査** | 毎発注 | 不一致で safe_stop(account_type_mismatch_runtime) | 6.18 |
| **Config Version 計算** | 起動時 | 前回と不一致で Notifier info (継続) | 6.19 |
| **Alembic Revision 確認** | 起動時 | 期待 revision と不一致で exit | 起動シーケンス |
| **Schema 整合性** | 起動時 | Repository が想定する列が欠損で exit | 起動シーケンス |
| **in-flight timeout** | safe_stop 中 | 30s 超で orders.status=FAILED | 6.1 |
| **Signal TTL 判定** | 毎 ExecutionGate | 超過で Reject(SignalExpired) | 6.15 |
| **Defer 連発判定** | 毎 ExecutionGate | defer_exhausted_threshold 超で Reject(DeferExhausted) | 6.15 |
| **client_order_id ULID 形式** | 毎 place_order | 非 ULID なら例外 | 6.4 |
| **Feature Service 決定性** | contract test | 同入力で異出力なら test fail | 6.10 |
| **look-ahead 検出** | contract test | as_of_time 違反で test fail | D2 |
| **single DELETE 検出** | CI lint | 直接 DELETE で CI fail | D5 |

---

## 5. in-flight Order まわりの責務分界

### 5.1 通常時

- `OrderLifecycleService.submit()` が `orders(PENDING)` + `outbox_events(ORDER_SUBMIT_REQUEST)` を同一トランザクションで insert
- `OutboxProcessor` が outbox_events pending を pick、Broker.place_order 呼出
- 成功で `orders.status=SUBMITTED` + `outbox_events(ORDER_SUBMIT_ACK)`
- 失敗で `orders.status=FAILED` + `outbox_events(ORDER_SUBMIT_FAIL)` + `retry_events` 記録

### 5.2 safe_stop 中 (6.1)

- `Supervisor.safe_stop()` が呼ばれた瞬間:
  1. `SafeStopJournal.write()` 完了 (fsync)
  2. `OrderLifecycleService.submit()` は以後 reject 返却 (新規受付停止)
  3. `OutboxProcessor.pause_dispatch()` (新規 dispatch 停止)
  4. 既に `dispatching` 中の outbox は`place_order_timeout_seconds=30` まで継続
  5. transaction stream 受信は継続 (fill が来ても正常に反映)
  6. タイムアウト超過した PENDING は `status=FAILED` に遷移
  7. Reconciler が起動時 or 手動 resume で再整合

### 5.3 Reconciler の in-flight 扱い

- 起動時 Reconciler が `orders.status=PENDING` を発見したら:
  - OANDA に同 client_order_id を問合せ
  - 存在 → `SUBMITTED` 更新
  - 不在 & 5 分未満 → 待機
  - 不在 & 5 分超 → `FAILED` 更新 (6.12 Action Matrix)

---

## 6. Live / Backtest 共通化の原則

### 6.1 必ず共通

- Feature Service、StrategyEvaluator、EVEstimator、CostModel、MetaDecider、PositionSizer、RiskManager、ExitPolicy、Repository 群、Notifier、Aggregator
- スキーマ (D1 / D2)
- Common Keys 伝搬

### 6.2 必ず差し替え

- `Broker`: live は `OandaBroker`、backtest は `PaperBroker`
- `PriceFeed`: live は `OandaPriceFeed`、backtest は `HistoricalPriceFeed`
- `Clock`: live は `WallClock`、backtest は `SimClock`
- `Supervisor`: live は常駐、backtest は無効化 (BacktestRunner 自身が orchestration)

### 6.3 禁止

- **コード内分岐 `if backtest: ...`** は禁止 (contract test で検出)
- live と backtest で**異なる順序**で Interface 呼出
- live と backtest で**異なるスキーマ**の利用

---

## 7. 禁止するアンチパターン

MVP 実装 + Iteration 1 以降のコードレビューで**拒絶**するパターン:

| # | パターン | 拒絶理由 |
|---|---|---|
| 1 | `time.time()` / `datetime.utcnow()` 直接呼出 | 6.10 決定性 / 6.15 TTL / D2 sim_clock |
| 2 | `DELETE FROM` を Repository 外で発行 | D5 単純 DELETE 禁止 |
| 3 | `TRUNCATE TABLE` / `DROP TABLE` を migration で直接使う | D5 No-Reset |
| 4 | `Broker.place_order` 内で `verify_before_order` を呼ばない実装 | 6.18 |
| 5 | アプリコードから Common Keys 列を直接書込 | D1 3.3 / Repository 自動付与 |
| 6 | Feature Service 内で seed なし乱数 / 現在時刻依存 | 6.10 |
| 7 | Live / backtest で `if backtest` 分岐 | D2 12. |
| 8 | SQLite を `multi_service_mode` や `container_ready_mode` で使用 | D1 6.11 |
| 9 | Secret 値をログ出力 / Exception メッセージに含む | Phase 3 / 6.13 PII マスキング |
| 10 | `orders.status` を後退遷移 (FAILED → PENDING 等) | D1 / 6.6 FSM |
| 11 | `notification_outbox` 経由で safe_stop critical を送信 | 6.13 二経路 |
| 12 | 同期的ログ書込でトレーディングループをブロック | Phase 2 非同期境界 |
| 13 | Observability tier の書込失敗で safe_stop 発火 | 6.13 Criticality Tier |
| 14 | Critical tier の書込を非同期キュー化 | 6.13 Criticality Tier |
| 15 | 本番コード内で `print` (標準出力直接) | 構造化ログ経由のみ |

---

## 8. テスト観点

### 8.1 Unit Test

- 各 Interface 実装の振る舞いを独立に検証
- 乱数 / 時刻 / 外部依存は mock 化
- MVP 合格目安: 全 Interface で主要パスカバレッジ 80%+

### 8.2 Integration Test

- 複数 Interface をまたぐシナリオ (例: Meta → Risk → Outbox → PaperBroker → transaction stream → Reconciler)
- PostgreSQL (docker) + SQLite (in-memory) の両方で schema 作成・書込検証
- MVP 合格目安: 主要ユースケース (1 cycle 分足判断〜決済) 1 end-to-end

### 8.3 Simulation Consistency Test

- 同 config + 同 seed で BacktestRunner を 2 回実行、出力バイト等価
- live 用ロジックを BacktestRunner 経由で走らせ、live と同じ挙動を確認 (D2 12.2 共通化検証)

### 8.4 Contract Test

Interface レベルの**契約不変条件**を機械的に検証:

| 契約 | テスト |
|---|---|
| 6.10 Feature Service 決定性 | 同入力で feature_hash 等価 |
| D2 look-ahead 禁止 | as_of_time 違反検出 |
| 6.18 Broker account_type assertion | 全 Broker 実装で assertion 発火確認 |
| 6.6 Outbox transaction | orders + outbox_events の同一 tx commit |
| 6.4 ULID フォーマット | 全 orders.order_id が ULID |
| 6.13 Notifier 二経路 | critical は outbox 経由しない |
| D5 単純 DELETE 禁止 | CI lint で grep + AST check |
| D1 3.3 Common Keys | Repository 経由以外での Common Keys 書込禁止 |

### 8.5 Chaos Test (Phase 7 で体系化、MVP 最低限)

- DB 接続断 → safe_stop 発火確認
- Stream gap → Mid-Run Reconciler 発火確認
- Broker 5xx 連発 → Retry + degraded
- EventCalendar 削除 → Stale failsafe
- NTP 逸脱 → 起動拒否

---

## 9. Open Questions

| ID | 論点 | 解決予定 |
|---|---|---|
| IC-Q1 | 例外クラス階層設計 (AccountTypeMismatch / SignalExpired / etc の親クラス) | Iteration 1 |
| IC-Q2 | DI コンテナ (手製 / injector / dependency-injector) | Iteration 1 |
| IC-Q3 | async/await vs sync の境界 (Phase 2 2.1 concurrency model 未確定) | Iteration 1 |
| IC-Q4 | Repository のトランザクションスコープをどこまで広げるか | Iteration 1 |
| IC-Q5 | Feature Service の出力が大きい場合の in-memory 抑制 | Phase 7 |

---

## 10. Summary (契約固定点)

本書は以下を MVP 実装契約として固定する:

1. **11 レイヤ + 責務境界の明記**、越境禁止
2. **30+ Interface**を name / purpose / method / input / output / side effect / idempotency / failure / retry / invariant の 10 観点で定義
3. **Common Keys 自動伝搬** は Repository の責務、アプリ直接書込禁止
4. **in-flight Order** は OutboxProcessor + OrderLifecycleService + Reconciler の協調で処理
5. **account_type assertion** は全 Broker 実装で必須、契約テストで保証
6. **config_version 計算** は起動時 1 回、`supervisor_events` に source_breakdown 記録
7. **Live / backtest の分岐禁止**、Broker / PriceFeed / Clock 差し替えのみ
8. **15 アンチパターン**を明記、CI / コードレビューで拒絶
9. **4 段階テスト** (unit / integration / simulation consistency / contract) で品質担保
10. 本書は実装者の単一ソース、Iteration 1 のコードは本書の契約に従う
