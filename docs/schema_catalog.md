# D1. Schema Catalog

## Purpose
一次DB (PostgreSQL) の **44 物理テーブル** (Phase 6 baseline 42 + M20 で追加された `dashboard_top_candidates` 1 表 + Phase 6 Cycle 6.1 で追加された `secondary_sync_outbox` 1 表) + ローカルアーティファクト **2 ファイル**について、論理名 / 物理名 / 目的 / 主キー / 外部キー / 粒度 / 更新方針 / 保持クラス / 正本 / 下流消費者 を**契約として固定**する。Alembic 初期 migration、Repository 設計、分析クエリ、retention ジョブの単一ソース。

## Scope
- Phase 6 baseline 42 表 + Iter2 M20 で追加された 1 表 + Phase 6 Cycle 6.1 で追加された 1 表 = **44 DB テーブル** と **2 ローカル永続ファイル**
- 物理表・ローカルファイルの構造契約 (列は**どの情報が載るか**のレベルで確定、具体的な型とサイズは Alembic migration 時に schema_catalog と整合する形で最終化)
- Common Keys (Phase 3 / 6.19 / 6.10) の伝搬規則
- View エイリアス方針 (Phase 1/3 旧名は View で保全)

## Out of Scope
- SQL DDL そのもの (Alembic migration が実装)
- Repository の I/F シグネチャ (D3 で定義)
- 保持期間の**数値** (D5 で確定)
- 二次DB マートのスキーマ (design.md Section 7.2 / Phase 3 継承、本書は一次DB 側のみ)

## Dependencies
- `docs/design.md` Section 7.1 (Phase 4 baseline 34 テーブル定義)
- `docs/phase6_hardening.md` 6.20 (Phase 6 時点 canonical 42 テーブル、本書 Iter2 M20 で 1 表追加し 43 表が現行 canonical)
- `docs/phase6_hardening.md` 6.5 (初期数値パラメータの app_settings 投入)

## Related Docs
- `docs/implementation_contracts.md` (Repository 契約、列を読み書きする Interface)
- `docs/retention_policy.md` (保持クラスの具体値)
- `docs/backtest_design.md` (backtest 由来データの扱い)
- `docs/operations.md` (運用・再生成・復元手順)

---

## 1. 設計原則 (Inherited Constraints)

以下は design.md / phase6_hardening.md から継承する**破ってはいけない制約**:

1. **No-Reset**: 本番・準本番で `TRUNCATE` / `DROP TABLE` / 破壊的バルク削除を行わない。削除は必ず Copy→Verify→Delete の 3 段で行う (D5)
2. **正本は常に一次DB**: 二次DB は非同期投影で正本ではない。State Manager のメモリ保持は派生であり、再起動時は一次DB から復元
3. **Common Keys の全行付与**: すべての行に run_id / environment / code_version / config_version + 対象に応じた追加キーを自動付与
4. **cycle_id / correlation_id / order_id** による系統横断トレース: 発注 → 約定 → 決済を 1 本の correlation_id で縫う
5. **expand-contract**: スキーマ進化は列追加を基本、破壊的変更は新テーブル + View で段階移行
6. **Phase 1/3 旧名は View で保全**: 物理は Phase 4 命名、旧名 (`intents`, `fills`, `exits`, `ev_decompositions`, `features`, `execution_gates`, `risk_evaluations`, `candles_1m`/`_5m`, `events_calendar`, `no_trade_evaluations`) は View エイリアスで後方互換

---

## 2. テーブル総覧 (44 + ローカル 2)

### 2.1 グループ別カタログ

表頭の略記:
- **Update**: AO = Append-Only / MUT = Mutable (row 更新あり) / UPS = Upsert (同一キーで INSERT or UPDATE) / SNAP = Snapshot (定期全量)
- **Grain**: 1 行が表す単位
- **SoT**: Source of Truth (正本はどこ由来か)
- **Ret**: Retention class (D5 のクラス定義を参照)

#### A. Config / Reference (4 表)

| # | Physical | Purpose | PK | FK / Ref | Grain | Update | SoT | Ret |
|---|---|---|---|---|---|---|---|---|
| 1 | `brokers` | 接続ブローカーマスタ (OANDA 等) | `broker_id` | — | 1 broker | MUT | 管理入力 | Reference (永続) |
| 2 | `accounts` | 取引口座マスタ (口座通貨・残高基準) | `account_id` | `broker_id` | 1 口座 | MUT | 管理入力 + OANDA 同期 | Reference (永続) |
| 3 | `instruments` | 取引可能通貨ペアのマスタ (pip 単位・最小ロット・取引時間帯等の静的属性) | `instrument` | — | 1 通貨ペア | MUT (低頻度) | 管理入力 + OANDA 同期 | Reference (永続) |
| 4 | `app_settings` | 実行時設定の現行値 (6.5 初期パラメータの実体) | `name` | — | 1 設定キー | MUT | 手動 SQL / migration | Reference (永続) |

**Decision**: 4 表すべて `account_type` / 環境等の切替で**履歴参照**が必要な場合は `app_settings_changes` (Operations 群) を使用する。マスタ自体は最新値を保持、監査履歴は別テーブル。

#### B. Market Data (3 表)

| # | Physical | Purpose | PK | FK | Grain | Update | SoT | Ret |
|---|---|---|---|---|---|---|---|---|
| 5 | `market_candles` | OANDA candles (1m / 5m / 他 tier) | `(instrument, tier, event_time_utc)` | `instrument` | 1 足 | AO | OANDA | Market raw |
| 6 | `market_ticks_or_events` | OANDA pricing 配信・stream gap・heartbeat 等の raw event (type 列で区別) | `(instrument, event_time_utc, event_seq)` | `instrument` | 1 イベント | AO | OANDA | Market raw |
| 7 | `economic_events` | 経済指標カレンダー (6.3 EventCalendar の永続化) | `event_id` | — | 1 指標 | UPS | 手動 CSV (MVP) / 外部 API (将来) | Reference (長期保持) |

**Open Question (Q1)**: `market_ticks_or_events` の type 列挙 (`tick` / `pricing` / `stream_gap` / `heartbeat` / `reconnect`) を D3 `implementation_contracts.md` で最終固定する。Phase 5 Review P5 では 2 テーブル分割案が提案されたが、Phase 6 時点の canonical は単一テーブル + type 列方式。

**Decision (2.1-B-1)**: Phase 6 は**単一テーブル + type**。分割は Phase 7+ で必要性が出た時点で再検討。

#### C. Learning / Models (4 表)

| # | Physical | Purpose | PK | FK | Grain | Update | SoT | Ret |
|---|---|---|---|---|---|---|---|---|
| 8 | `training_runs` | 学習ジョブ 1 回の実行履歴 (開始・終了・入力条件・成果物参照) | `training_run_id` | `experiment_id`, `model_id` | 1 ジョブ | AO (status は遷移あり) | LearningOps | Learning artifacts (永続) |
| 9 | `model_registry` | モデル登録・版・メタ (active / shadow / review / demoted 等の状態) | `model_id` | `training_run_id` | 1 model version | MUT (状態遷移) | LearningOps / ModelLifecyclePolicy | Reference (永続) |
| 10 | `model_evaluations` | OOS / walk-forward / Brier score 等の評価結果 (shadow=true の並走評価含む) | `evaluation_id` | `model_id`, `training_run_id` | 1 評価実行 | AO | LearningOps | Learning artifacts (永続) |
| 11 | `predictions` | モデル推論出力の個別記録 (AIStrategy の発した予測値) | `(model_id, cycle_id, instrument)` | `model_id`, `instrument` | 1 予測 | AO | StrategyEngine / LearningOps | Decision logs |

**Rationale**: `training_runs` と `model_evaluations` を分離するのは、同一 model_id に対して**複数回の評価**(walk-forward の fold ごと、shadow 期間中の週次再評価等) を実行するため。

#### D. Decision Pipeline (7 表)

| # | Physical | Purpose | PK | FK | Grain | Update | SoT | Ret |
|---|---|---|---|---|---|---|---|---|
| 12 | `strategy_signals` | 全戦略 × 全候補のシグナル (採否問わず全量) | `(cycle_id, instrument, strategy_id)` | `cycle_id` | 1 候補 | AO | StrategyEngine | Decision logs |
| 13 | `pair_selection_runs` | MetaDecider Select 段の 1 ラン単位サマリ | `selection_run_id` | `cycle_id` | 1 Select 実行 | AO | MetaStrategy Engine | Decision logs |
| 14 | `pair_selection_scores` | Select 段の各候補スコア詳細 (Score 段の合成結果を Select 側の正本として保存) | `(selection_run_id, instrument, strategy_id)` | `selection_run_id` | 1 候補のスコア | AO | MetaStrategy Engine | Decision logs |
| 15 | `meta_decisions` | Filter / Score / Select 3 段のスナップショット + `score_contributions` (6.7) + `active_strategies` (6.17) + `regime_detected` (6.8) | `meta_decision_id` | `cycle_id` | 1 cycle の meta 判断 | AO | MetaStrategy Engine | Decision logs |
| 16 | `feature_snapshots` | cycle 時点の特徴量スナップショット。compact_mode 既定 (6.10)、`feature_version` 必須 | `(cycle_id, instrument)` | `cycle_id`, `instrument` | 1 cycle × 1 pair | AO | Feature Service | Decision logs |
| 17 | `ev_breakdowns` | EV 内訳 (P(win), AvgWin, AvgLoss, Cost 内訳, confidence_interval, swap_cost) | `(cycle_id, instrument, strategy_id)` | `cycle_id` | 1 候補の EV 内訳 | AO | EVEstimator / CostModel | Decision logs |
| 18 | `correlation_snapshots` | 短窓 1h / 長窓 30d の相関マトリクス (6.8)、`regime_detected` | `(timestamp_utc, window_class)` | — | 1 時点 × 1 窓種別 | AO | CorrelationMatrix | Decision logs |

**Decision (2.1-D-1)**: `meta_decisions` は 1 cycle に 1 行 (3 段のサマリを 1 行に集約)、`pair_selection_runs` / `pair_selection_scores` は Select 段の詳細明細を外部キー先行関係で保持。`meta_decisions_full` View (Phase 6 View 保全の一環) で結合ビュー提供。

**Inherited Constraint (2.1-D-2)**: `feature_snapshots.feature_version` は Common Keys 拡張として必須 (6.10)。compact_mode の場合でも `feature_hash` / `feature_stats` / `sampled_features` の 3 列は埋める。

#### E. Execution (4 表)

| # | Physical | Purpose | PK | FK | Grain | Update | SoT | Ret |
|---|---|---|---|---|---|---|---|---|
| 19 | `trading_signals` | 採用された発注意図 (Phase 1 `intents` の物理) | `trading_signal_id` | `meta_decision_id`, `cycle_id` | 1 発注意図 | AO | MetaStrategy Engine | Execution (法的・監査) |
| 20 | `orders` | 発注レコード。有限状態遷移 `PENDING → SUBMITTED → FILLED/CANCELED/FAILED` (6.6) | `order_id (ULID)` | `trading_signal_id`, `account_id` | 1 発注 | MUT (status 遷移のみ) | ExecutionAssist / OutboxProcessor | Execution (法的・監査) |
| 21 | `order_transactions` | OANDA transaction stream の全イベント (ORDER_FILL / ORDER_CANCEL / STOP_LOSS_TRIGGERED 等、ハートビートは要約後) | `(broker_txn_id, account_id)` | `order_id` (可能な場合) | 1 broker イベント | AO | OANDA transaction stream | Execution (法的・監査) |
| 22 | `positions` | 保有ポジションの時系列履歴 (各イベントで新行追記) | `position_snapshot_id` | `order_id` (open 時) | 1 position 変化イベント | AO (時系列) | ExecutionAssist + Reconciler | Execution (法的・監査) |

**Critical Inherited Constraint (2.1-E-1)** (6.4 / 6.18): `orders.order_id` は **ULID** (時間プレフィックス 48bit + ランダム 80bit)。`orders.client_order_id` 列はフォーマット `{ulid}:{instrument}:{strategy_id}` の人可読補助 (PK ではない)。発注前に account_type assertion (6.18) を通過したことが orders 行生成の前提。`orders.account_type` 列必須。

**Decision (2.1-E-2)**: `positions` は**時系列 append** で各変化イベント (open / add / close / swap_applied) を新行として記録。最新状態は「当該 instrument × account の MAX(position_snapshot_id)」または MV (マテリアライズドビュー) で提供。

#### F. Outcome (2 表)

| # | Physical | Purpose | PK | FK | Grain | Update | SoT | Ret |
|---|---|---|---|---|---|---|---|---|
| 23 | `close_events` | 決済イベント (TP / SL / 時間 / reverse / EV 低下 / 指標 / 緊急の発火理由全列挙) | `close_event_id` | `order_id`, `position_snapshot_id` | 1 決済 | AO | ExitPolicy / ExecutionAssist | Decision logs (ただし発注一式は法的・監査扱いで上位分類) |
| 24 | `execution_metrics` | 発注〜約定品質 (signal_age_seconds / slippage / latency / reject_reason 含む、6.15 SignalExpired / DeferExhausted) | `execution_metric_id` | `order_id` | 1 発注試行 | AO | ExecutionGate / ExecutionAssist | Decision logs |

**Inherited Constraint (2.1-F-1)** (6.8 ExitPolicy): `close_events` の発火理由は単一ではなく**複数同時の発火理由を全列挙**して保持 (JSONB `reasons: [{priority, reason_code, detail}]`)。最優先が実行されたという事実と理由のリストを分けて保存。

#### G. Safety & Observability (9 表)

| # | Physical | Purpose | PK | FK | Grain | Update | SoT | Ret |
|---|---|---|---|---|---|---|---|---|
| 25 | `no_trade_events` | 見送り判断 (taxonomy 付き: `reason_category` / `reason_code` / `reason_detail` / `source_component`、6.16) | `no_trade_event_id` | `cycle_id` (or `meta_decision_id`) | 1 見送り判断 | AO | MetaStrategy / Risk / Filter / Supervisor | Observability |
| 26 | `drift_events` | モデル / 特徴量ドリフト検出 (PSI / KL / 残差) | `drift_event_id` | `model_id` | 1 ドリフト検知 | AO | LearningOps | Observability |
| 27 | `account_snapshots` | 残高・有効証拠金・PnL・margin_used / margin_available スナップショット (trigger_reason 列あり: `order`/`fill`/`close`/`hourly`/`daily_close`/`manual`) | `account_snapshot_id` | `account_id` | 1 スナップショット | AO | RiskManager / Supervisor | Execution (法的・監査) |
| 28 | `risk_events` | RiskManager.accept / reject の判定記録 | `risk_event_id` | `cycle_id` | 1 判定 | AO | RiskManager | Observability |
| 29 | `stream_status` | pricing / transaction stream の接続状態遷移 (connected / heartbeat / gap / reconnect) | `stream_status_id` | — | 1 状態変化 | AO | StreamWatchdog | Observability |
| 30 | `data_quality_events` | 入力データ品質事象 (stale price / 欠損 / ギャップ / 型異常 / transaction 不整合) | `data_quality_event_id` | — | 1 事象 | AO | MarketDataService / Reconciler | Observability |
| 31 | `reconciliation_events` | Reconciler Action Matrix (6.12) の各ケース実行記録 (trigger_reason: `startup`/`midrun_heartbeat_gap`/`periodic_drift_check`) | `reconciliation_event_id` | `order_id` / `position_snapshot_id` (該当時) | 1 Reconcile ケース | AO | Reconciler / MidRunReconciler | Supervisor/Reconciler (永続) |
| 32 | `retry_events` | 全リトライログ (caller / エンドポイント / attempt / backoff_ms / 結果) | `retry_event_id` | — | 1 リトライ試行 | AO | 各呼び出し側 | Observability |
| 33 | `anomalies` | アプリ一般異常 (data_quality_events / reconciliation_events とは別系統のアプリエラー) | `anomaly_id` | — | 1 異常 | AO | 全コンポーネント | Observability |

**Decision (2.1-G-1)**: `no_trade_events` の taxonomy は D3 Interface 契約で enum 列挙を確定 (6.16 の 8 category × 20+ code)。DB 側は text 型で格納、enum 外の値はアプリ側で rejection (契約テストで担保)。

**Rationale (2.1-G-2)**: `data_quality_events` / `reconciliation_events` / `anomalies` は**責務が異なる 3 系独立**。`correlation_id` で JOIN 可能。重複記録を避けるため、発生源コンポーネントが one-and-only-one で決まる。

#### H. Aggregates (4 表 = Phase 6 baseline 3 + M20 追加 1)

| # | Physical | Purpose | PK | FK | Grain | Update | SoT | Ret |
|---|---|---|---|---|---|---|---|---|
| 34 | `strategy_performance` | 戦略別ロールアップ (window_class × strategy_type × strategy_version) | `(window_class, window_start, strategy_type, strategy_version, instrument)` | `instrument` | 1 ロールアップ行 | UPS (Aggregator が idempotent 再計算) | Aggregator | Aggregates (永続) |
| 35 | `meta_strategy_evaluations` | メタ戦略の選択精度 (反実仮想含む、`meta_eval_protocol_version` 必須) | `(window_class, window_start, meta_strategy_version)` | — | 1 評価期間 | UPS | Aggregator | Aggregates (永続) |
| 36 | `daily_metrics` | 日次 KPI (PnL / DD / exposure / trade count / rejection rate / no_trade 比) | `(date_utc, account_id)` | `account_id` | 1 日 × 1 口座 | UPS | Aggregator | Aggregates (永続) |
| 43 | `dashboard_top_candidates` | TSS 上位候補 mart (Dashboard Top Candidates panel の読み元、15 分毎に MartScheduler が refresh) | `candidate_id` | — | 1 候補 (rank 順) | SNAP (15 分毎 refresh) | MartScheduler (M20 / migration 0012) | Aggregates (短期、最新 snapshot 上書き) |

**Inherited Constraint (2.1-H-1)** (Phase 3 Aggregator idempotency): 同一入力 + 同一 Aggregator version で同一結果。reason_category 別・strategy_version 別の集計境界を跨ぐ集計を禁止 (6.11, 6.17)。

**Decision (2.1-H-2)** (M20 追加): `dashboard_top_candidates` は Phase 6 baseline には含まれず、Iter2 M20 (migration `0012_dashboard_top_candidates_table.py`) で追加された 43 番目の物理表。Dashboard 専用 mart のため SoT は MartScheduler (Aggregator) で、業務 SoT (orders / positions 等) からは派生扱い。番号 43 は baseline 42 表の追記順を保つため group 末尾に付与している。

#### I. Operations (7 表)

| # | Physical | Purpose | PK | FK | Grain | Update | SoT | Ret |
|---|---|---|---|---|---|---|---|---|
| 37 | `system_jobs` | バッチ・学習・Aggregator・Cold archive 等のジョブ実行履歴 | `system_job_id` | — | 1 ジョブ実行 | MUT (status 遷移) | LearningOps / Aggregator / Archiver | Operations (長期) |
| 38 | `app_runtime_state` | Supervisor / State Manager の**永続スナップショット** (稼働中の正本ではなく、再起動 Reconciler の起点) | `snapshot_id` | — | 1 スナップショット | AO | Supervisor | 直近 + 履歴 30d |
| 39 | `outbox_events` | 発注 Outbox の event キュー (`ORDER_SUBMIT_REQUEST` / `ORDER_SUBMIT_ACK` / `ORDER_SUBMIT_FAIL` 等、6.6) | `outbox_event_id` | `order_id` | 1 outbox entry | MUT (dispatch status) | TradingCore / ExecutionAssist | Outbox (短期、dispatch 済は直接削除可) |
| 40 | `notification_outbox` | 非 critical 通知 Outbox (6.13)、critical は outbox バイパスで直接同期送信 | `notification_outbox_id` | — | 1 通知 entry | MUT (dispatch status) | Notifier | Outbox (短期) |
| 41 | `supervisor_events` | Supervisor / 起動検査 / safe_stop / config_version 計算 / account_type 検証 等のイベント (event_type 列挙は **§2.3 supervisor_events.event_type Canonical** 参照) | `supervisor_event_id` | — | 1 Supervisor イベント | AO | Supervisor | Supervisor/Reconciler (永続) |
| 42 | `app_settings_changes` | `app_settings` の全変更履歴 (name / old_value / new_value / changed_by / changed_at / reason) | `app_settings_change_id` | — | 1 変更 | AO | 変更実行者 / migration | Reference (永続) |
| 44 | `secondary_sync_outbox` | 一次→二次 DB 同期 Outbox (Phase 6 Cycle 6.1)。Sync Service worker が pull → Sink に at-least-once 配送、Sink 側が `(table_name, primary_key, version_no)` で idempotent upsert | `outbox_id` | — | 1 sync envelope | MUT (acked_at / attempt_count 更新) | 業務テーブル書込元 (Trading Core, Aggregator, etc.) | Outbox (短期、acked 後 7d で purge 可) |

**Critical Inherited Constraint (2.1-I-1)** (6.6 Outbox): `outbox_events` への書込は発注の**前段** (HTTP 送信より前)、commit 成功後にのみ Broker.place_order が呼ばれる。`outbox_events.status: pending / dispatching / acked / failed` の state machine を持ち、OutboxProcessor が pending を dispatch する。

**Decision (2.1-I-2)**: `outbox_events` と `notification_outbox` は**非永続** (D5)。dispatch 済みエントリは Hot 30d / Warm 90d 経過で**直接 DELETE 可**。業務データではなく dispatch 管理用のテーブル。

**Decision (2.1-I-3)** (Phase 6 Cycle 6.1, mig `0013_secondary_sync_outbox.py`): `secondary_sync_outbox` は Phase 6 Decision Freeze F-2 / F-3 / F-12 に基づく**新規 outbox**。既存 `outbox_events` (発注 HTTP) と `notification_outbox` (通知) とは責務が独立で、同名衝突を避けるため `secondary_sync_*` 接頭辞で命名。M23 `ProjectionService` (snapshot 方式・supervisor_events 専用) はそのまま維持し、Phase 6 以降に追加される **新しい Secondary 同期対象は本 outbox 経由のみ**で実装する (snapshot 方式は拡張しない)。番号 44 は Phase 6 baseline 42 + M20 #43 + Cycle 6.1 #44 の追記順を保つため group 末尾に付与。

**Decision (2.1-I-4)** (Phase 6 Cycle 6.1): `secondary_sync_outbox` の payload は**書込元側で sanitization 済**であることを前提とする (F-12)。Sink は payload を信頼し、エラーメッセージに payload の値を **echo してはならない**。sanitization 共通関数自体は Cycle 6.2 で導入される (本 cycle はテーブルと Protocol 契約のみ)。

**Decision (2.1-I-5)** (Phase 6 Cycle 6.1): `secondary_sync_outbox` には外部キーを設けない。書込元テーブルが Group A〜H 全てを跨ぐ可能性があり、`(table_name, primary_key)` 組での参照は Sink 側 idempotency に閉じる (Primary 側参照整合は Sync Service worker の責務外)。これにより書込元テーブルの DROP / 再作成が outbox に波及しない (Migration 進化容易性)。

### 2.2 ローカルアーティファクト (非DB、2 ファイル)

| # | Path | Purpose | Format | Write Policy | Rotation | SoT Role |
|---|---|---|---|---|---|---|
| L1 | `logs/safe_stop.jsonl` | 6.1 SafeStopJournal。DB 書込失敗時でも safe_stop を記録する独立永続化チャネル | JSONL (1 行 1 イベント) | 同期 fsync (writer は 1 プロセス、file lock) | 日次ローテ、180d 保持 | safe_stop 発火の**二次正本** (DB と突合) |
| L2 | `logs/notifications.jsonl` | 6.13 FileNotifier 常時必須の fallback チャネル | JSONL | 同期 fsync | 日次ローテ、90d 保持 | 最終保証の通知記録 |

**Critical Inherited Constraint (2.2-1)** (6.1): L1 への書込は safe_stop シーケンスの**最初**に実施 (DB 書込より前)。fsync 完了を待ってから後続ステップ。起動時は L1 と `supervisor_events` の両方を読み、不整合なら L1 を正本として DB に補完。

### 2.3 `supervisor_events.event_type` Canonical (Iter3 cycle 3 確定)

`supervisor_events` の `event_type` 列に書き込まれる**正本列挙**。docs 全体 (operations / phase6_hardening / implementation_contracts) はこの表を参照する。新規 event_type 追加は本書を更新してから他 docs へ波及させること (本書が単一ソース)。

| event_type | 発火元 (Supervisor / Reconciler / etc) | 契機 | 備考 |
|---|---|---|---|
| `account_type_verified` | Supervisor (起動 §2.1 Step 9) | account_type assertion 通過 | `payload={expected, observed}`、6.18 |
| `config_version_computed` | Supervisor (起動最初期) | `compute_config_version()` 完了 | `payload={config_version, source_breakdown}`、6.19 |
| `config.version_changed` | Supervisor (起動時 vs 前回 run 比較) | config_version の変動検出 | `payload={old, new, diff}`、Notifier `info` を併発 |
| `journal_reconcile_completed` | Supervisor (起動 §2.1 Step 5) | SafeStopJournal vs DB 突合完了 | 6.1 |
| `metric_sample` | Supervisor (1 分毎 MetricsLoop、M16) | 1 分毎の 9 項目 metrics | `payload={metric_name, value, ...}` |
| `daily_close_completed` | Supervisor (日次締め §2.5) | daily_metrics aggregation 完了 | `payload={pnl, dd, summary}` |
| `incident_report` | Supervisor (障害事後、運用者 or 自動) | 復旧後の事故レポート | `payload={root_cause, F#, action}`、§9.5 |
| `safe_stop_fired` | Supervisor (safe_stop 発火) | 6.1 / §4.4 reason_code | `payload={reason, trigger_event}`、Notifier `safe_stop.fired` を併発 |
| `safe_stop_cleared` | Supervisor (手動復帰) | `python scripts/ctl.py resume-from-safe-stop` 受領 | `payload={cleared_by, reason}`、Notifier `safe_stop.cleared` を併発 |
| `degraded_entered` | Supervisor / Reconciler | degraded モード遷移 | Notifier `mode.degraded.entered` を併発 |
| `degraded_cleared` | Supervisor / Reconciler | normal 復帰 | Notifier `mode.degraded.cleared` を併発 |

**Decision (2.3-1)**: 上記 11 種が Iter2 baseline。Phase 7+ で追加する場合は本表に追記し、operations.md / phase6_hardening.md / implementation_contracts.md の該当箇所も同 PR で更新する (3 docs 同時改訂を契約とする)。

**Note (2.3-2)**: Notifier event_type (例 `safe_stop.fired`) と supervisor_events.event_type (例 `safe_stop_fired`) は**別系統の名前空間**で命名規則も異なる (Notifier は dot-separated、supervisor_events は underscore)。両者の対応関係は本表の備考列で明示する。例外として `config.version_changed` は両系統で同名を採用 (Iter2 既存実装を尊重)。

---

## 3. Common Keys の伝搬規則

### 3.1 必須 Common Keys (全 43 テーブル)

Phase 3 + 6.10 の Common Keys は全テーブル (ローカルファイル含む) に**自動付与**する:

| Key | 由来 | 付与方法 |
|---|---|---|
| `run_id` | プロセス起動単位 (Supervisor) | Repository 層が起動時に取得した値を自動挿入 |
| `environment` | RuntimeProfile (`local`/`vps`/`aws`) | 起動時設定 |
| `code_version` | ビルド時 git SHA | ビルド時埋込 |
| `config_version` | 6.19 起動時計算 | 起動時計算値を Repository 経由で付与 |
| `event_time_utc` | イベント発生時刻 (UTC epoch ms) | アプリ側で提供 (now() 禁止) |
| `event_wall_time` | ISO8601 (任意、後方互換用) | 同上 |
| `received_at_utc` | 受信側時刻 | Repository 層で付与 |

### 3.2 対象限定 Common Keys

以下は該当テーブルのみ付与:

| Key | 付与対象 |
|---|---|
| `instrument` | 通貨ペア関連の全テーブル (市場データ・決定・執行・決済・集計の大半) |
| `cycle_id` | Decision Pipeline / Execution / Outcome / Observability 系 |
| `correlation_id` | 発注 lifecycle 関連 (`trading_signals`, `orders`, `order_transactions`, `execution_metrics`, `close_events`, `positions`, `risk_events`, `reconciliation_events` 等) |
| `order_id` | 発注 lifecycle 関連 (上記のうち order が決まった後の行) |
| `experiment_id` | 学習関連 (`training_runs`, `model_evaluations`, `predictions`) |
| `model_version` / `model_id` | Learning / Decision 由来の該当行 |
| `strategy_id` / `strategy_type` / `strategy_version` | Strategy / Decision / Outcome 系 |
| `meta_strategy_version` | Meta 系 |
| `meta_eval_protocol_version` | `meta_strategy_evaluations` のみ (6.11) |
| `feature_version` | `feature_snapshots`, `predictions`, `ev_breakdowns` (決定的特徴量計算に依存する表) |
| `account_type` | `orders`, `account_snapshots` (6.18) |

### 3.3 付与の自動化契約 (Inherited Constraint)

Repository 層は Common Keys の書き忘れを**構造的に防ぐ**:
- Repository の書込メソッドは `CommonKeysContext` を必須引数として受け取る
- アプリ内で `CommonKeysContext` は `cycle_id` や `correlation_id` をスコープで引き継ぐ
- Repository が受け取った object に Common Keys を自動 merge、明示的な上書きはレビュー禁止

---

## 4. 更新方針の詳細

### 4.1 Append-Only (AO)
- 既存行を UPDATE しない。状態変化は新行で表現
- 対象: イベントログ系 (`*_events`, `strategy_signals`, `predictions`, `positions`, `order_transactions`, `feature_snapshots` 等)
- 理由: No-Reset + バージョン跨ぎ分析

### 4.2 Mutable (MUT)
- 行の status / metadata が遷移する
- 対象: `orders` (PENDING→SUBMITTED→...) / `model_registry` (active/shadow/...) / `system_jobs` (running/success/failed) / `app_settings` / `outbox_events` (pending/dispatching/...) / `notification_outbox`
- 契約: 状態遷移は有限状態機械 (FSM) で定義、後退遷移禁止、遷移ログは Operations 系の監査テーブルに別途記録

### 4.3 Upsert (UPS)
- 同一 PK で INSERT または UPDATE
- 対象: Aggregator 出力 (`strategy_performance`, `meta_strategy_evaluations`, `daily_metrics`)、`economic_events` (CSV 再取込)
- 契約: idempotent (同入力 → 同結果)、計算元のバージョンを PK または列に含める

### 4.4 Snapshot (SNAP)
- 定期的な全量ダンプ、過去分は保持
- 対象: 明示的 SNAP 対象なし (`account_snapshots` は trigger 由来で AO 扱い)

---

## 5. 派生カラム / 計算カラム / 監査カラム

以下は複数テーブル共通の設計ルール:

| 種別 | 対象 | 計算方式 |
|---|---|---|
| `config_version` | 全テーブル | 6.19 によりアプリ起動時 1 回計算、Repository が行挿入時に自動付与 |
| `code_version` | 全テーブル | ビルド時埋込値を Repository 経由 |
| `correlation_id` | 発注 lifecycle | cycle 開始時に生成、発注意図から決済・ログ全てに伝搬 |
| `order_id` | 発注 lifecycle | ULID (6.4)、`orders` INSERT 時に生成、以後の行に FK/参照として伝搬 |
| `event_time_utc` + `received_at_utc` | 全テーブル | イベント由来の時刻 + 受信側時刻を両保持 (clock skew 解析用) |
| `score_contributions` | `meta_decisions` | JSONB で Score 成分の寄与明細 (6.7) |
| `reasons` | `close_events` | JSONB で発火理由全列挙 |
| `reason_category` / `reason_code` / `reason_detail` | `no_trade_events` | 6.16 taxonomy に従う enum text + JSONB |
| `status` (state machine 列) | MUT テーブル | FSM を Interface 契約で定義、後退禁止 |

---

## 6. in-flight Order の保持と判定

Phase 6.1 in-flight 契約の具体化:

### 6.1 保持単位

- **1 件の in-flight リクエスト = 1 行の `orders`** (`status=PENDING`) + **1 行の `outbox_events`** (`event_type=ORDER_SUBMIT_REQUEST`, `status=dispatching`)
- この 2 行は同一トランザクションで commit (6.6)

### 6.2 in-flight の判定条件

`orders.status = 'PENDING'` **または** `outbox_events.status ∈ {'pending', 'dispatching'}` が 1 件でも存在する instrument × account。

### 6.3 safe_stop 中の扱い (6.1)

- 新規 `orders` 行生成 (= 新規発注) を停止
- 既存 PENDING の HTTP レスポンス受信は継続 (`place_order_timeout_seconds` = 30 秒まで)
- タイムアウト超過した PENDING 行は `status=FAILED` に強制遷移
- OutboxProcessor は dispatching 継続分を処理後、新規 pending の dispatch を停止

---

## 7. backtest と live で共通 / 異なるスキーマ

**Decision (7-1)**: **スキーマは原則共通**。live と backtest で別テーブルを作らない。

区別方法:
- すべての行の `environment` Common Key で区別 (live: `local`/`vps`/`aws`、backtest: `backtest`)
- `run_id` はプロセス起動単位で独立、backtest は `backtest_run_id` と紐づく専用 run_id を生成
- `config_version` は backtest 条件 (対象期間 / seed / 固定 feature_version 等) を canonical に含める

**Rationale**: 同一スキーマにすることで、live で発見されたバグが backtest でも再現でき、regression 検証の往復が破綻しない。

### 7.1 backtest 専用の追加表 (D2 で詳細)

D2 `backtest_design.md` で規定する backtest 専用テーブル (本カタログにおける Operations 群拡張の扱い):

- `backtest_runs` (1 backtest 実行の parameters + 成果物リンク) — **本カタログには Phase 6 では未登録**、D2 で定義
- `backtest_metrics` (backtest 結果の評価指標) — 同上

**Open Question (Q2)**: `backtest_runs` / `backtest_metrics` を Phase 6 時点で 42 テーブルに追加するか、あるいは D2 固有として別扱いするか。本書では**D2 で規定、Phase 6 canonical には含めず**とし、Phase 7 で 42 → 44 等に拡張する選択肢を残す。Iteration 1 の Alembic で backtest 用テーブルを**初期から作成**する判断は D2 にて。

---

## 8. 監査上残すべき項目

以下は No-Reset 原則に加え、**法的・税務・内部監査の観点で絶対に失えない**データ:

| 項目 | 該当テーブル | 根拠 |
|---|---|---|
| 全発注と約定 | `orders`, `order_transactions`, `positions`, `close_events` | 税務・ブローカー報告 |
| アカウント状態推移 | `account_snapshots` | 税務・残高説明 |
| 判断根拠 (EV / Meta / no_trade) | `strategy_signals`, `meta_decisions`, `ev_breakdowns`, `no_trade_events` | 再現性・戦略改善 |
| 設定変更履歴 | `app_settings_changes`, `supervisor_events` (config_version_computed) | 変更起因の挙動差の説明責任 |
| 安全系イベント | `supervisor_events`, `reconciliation_events`, `safe_stop_journal (L1)` | 事故検証 |

これらは D5 の「永続保持 / Cold 移動なし」区分に属する (D5 参照)。

---

## 9. C1 再発防止のための整合チェック観点

D1 は Phase 6.20 の canonical と整合する。**再発防止**のため、以下を Iteration 1 の Alembic migration レビュー時にチェック:

| チェック項目 | 観点 |
|---|---|
| 表数 | Alembic で作成される表 = 44 (Phase 6 baseline 42 + M20 `dashboard_top_candidates` 1 + Cycle 6.1 `secondary_sync_outbox` 1; 本書 44 + D2 で追加されうる backtest_* 系は別枠) |
| グループ別の数 | A=4 / B=3 / C=4 / D=7 / E=4 / F=2 / G=9 / H=4 / I=7 = 44 (H は Phase 6 baseline 3 + M20 追加 1 / I は Phase 6 baseline 6 + Cycle 6.1 追加 1) |
| View エイリアス | Phase 1/3 旧名 10 件 (intents / fills / exits / exit_decisions / execution_gates / features / ev_decompositions / risk_evaluations / candles_1m / candles_5m / events_calendar / no_trade_evaluations 等) が View で保全されているか |
| Common Keys 列 | 44 表全てに Phase 3 / 6.10 / 6.18 の Common Keys が漏れなく列定義されているか |
| 外部キー | orders → trading_signals / trading_signals → meta_decisions / predictions → model_registry 等の参照が張られているか |
| Retention class | D5 の分類と本書の Ret 列が一致しているか |

---

## 10. 未確定項目 / Open Questions

| ID | 論点 | 解決予定 |
|---|---|---|
| Q1 | `market_ticks_or_events` の type 列挙の確定 | D3 `implementation_contracts.md` |
| Q2 | backtest 専用テーブル (`backtest_runs` / `backtest_metrics`) の 42 表への組込タイミング | D2 `backtest_design.md` + Iteration 1 Alembic |
| Q3 | `positions` の最新状態を提供する View 名 / MV 採否 | Iteration 1 schema migration |
| Q4 | `meta_decisions_full` View のクエリ仕様 | D3 Repository 契約 |
| Q5 | 各テーブルの具体的な列型 (JSONB vs TEXT / numeric 精度 等) | Iteration 1 Alembic initial migration |

**Decision**: Q1–Q4 は D2 / D3 / Iteration 1 で段階的に解消。本書は「**何があるか / なぜあるか / どう使うか**」の単一ソース、列型は migration が決める。
