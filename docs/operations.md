# D4. Operations

## Purpose
FX-AI-Trading の**日常運用 / 起動シーケンス / 障害対応 / 再実行 / 監視 / 手動介入の境界**を準手順書 (Runbook) レベルで固定する。事故発生時に本書を開けば**初動手順**が分かり、運用者が判断に迷わない状態を目指す。Phase 6 の `safe_stop` / `degraded` / `Reconciler` / `Notifier` と整合し、D1 (schema) / D3 (interfaces) / D5 (retention) を運用時の振る舞いに変換する。

## Scope
- 運用原則と責務分担
- 想定運用フロー (起動 / 定常 / 日次締め / 再実行)
- 障害分類と初動手順
- 再試行 / idempotency / 二重実行防止の運用面
- ログ / メトリクス / アラート / ヘルスチェック
- 手動介入が許可される / 禁止されるケース
- 監査時の追跡項目

## Out of Scope
- コード実装 (Iteration 1 以降)
- CI/CD パイプラインの具体 (Phase 7)
- DR 訓練のスケジュール詳細 (Phase 8)
- OS レベル (systemd / nssm) 設定ファイル本体 (実装時に雛形化)

## Dependencies
- `docs/schema_catalog.md` (D1): 参照するテーブル
- `docs/implementation_contracts.md` (D3): Interface と Assertion
- `docs/retention_policy.md` (D5): Archive / backup / 違反検知
- `docs/backtest_design.md` (D2): backtest ジョブの運用
- `docs/phase6_hardening.md` 6.1-6.21: 契約の根拠

## Related Docs
- 将来: `docs/dr_runbook.md` (Phase 8)、`docs/chaos_scenarios.md` (Phase 7)

---

## 1. 運用原則

### 1.1 不変条件 (全フェーズ共通)

1. **売買クリティカルパスを UI / 二次DB / ログが阻害しない** (Phase 2 非同期境界)
2. **Critical 事象は必ず通知** (6.13 Notifier、FileNotifier + Slack + Email 同期直接送信、M17 三経路)
3. **manual intervention より自動復旧を優先** (ただし自動補正範囲を超えるものは degraded で待機、6.12)
4. **記録なしの変更禁止** (設定変更は `app_settings_changes`、状態遷移は `supervisor_events`)
5. **本番 DB の物理リセット禁止** (D5 No-Reset)
6. **demo / live の誤混同は絶対禁止** (6.18 四重防御)

### 1.2 責務分担

| 責務 | 担当 | タイミング |
|---|---|---|
| 定常稼働の監視 | Supervisor (自動) | 常時 |
| Critical 事象の検知 | Supervisor + StreamWatchdog + Reconciler | 常時 |
| Critical 通知送信 | Notifier (自動、三経路: File / Slack / Email) | 事象発生時 |
| 自動リカバリ | Reconciler / MidRunReconciler / OutboxProcessor | 自動 |
| safe_stop 判断 | Supervisor (自動、閾値ベース) | 事象発生時 |
| safe_stop からの復帰 | 運用者 (手動) | 事故調査後 |
| live account への切替 | 運用者 (手動 SQL + confirmation) | 稼働開始 / 本番切替時 |
| Alembic migration 実行 | 運用者 | リリース時 |
| バックアップ実行 | 独立 cron (自動) | 日次 00:30 UTC |
| Archive ジョブ (Phase 7+) | Archiver (自動) | 日次 02:00 UTC |
| DR 訓練 (Phase 8+) | 運用者 | 月次 |

---

## 2. 想定運用フロー

### 2.1 起動シーケンス (Startup Sequence)

Phase 6 の全 assertion / 検査をどの順で実行するかを確定する。**失敗時の挙動**も併記。

**Step 番号の表記ルール**: 範囲表記は ASCII hyphen (`Step 2-10`)。`Step 0` は OS / Supervisor (`systemd` / `nssm` / 手動) によるプロセス起動レイヤで、アプリ本体の責務外。`Step 1-16` がアプリ起動シーケンス本体 (Supervisor が実行)。本書で「Step N」は常に `Step 1-16` のいずれかを指す。

```
Step 0: プロセス起動 (OS / systemd / nssm / 手動)
  ↓
Step 1: ローカルリソース初期化
  - logging 初期化 (ファイルハンドル確保、fsync 可能確認)
  - FileNotifier 準備 (logs/notifications.jsonl 書込準備)
  - SafeStopJournal 準備 (logs/safe_stop.jsonl 読込 + writer 用 lock)
  Fail → stdout/stderr + exit (DB 使えない可能性あり、ローカルログのみ)
  ↓
Step 2: NTP 起動検査 (6.14)
  - NtpChecker.check_at_startup()
  - skew ≤ 500ms: continue
  - 500ms < skew ≤ 5000ms: Notifier warn (FileNotifier + Slack if available) + continue
  - skew > 5000ms: Notifier critical + ローカルファイルログ + exit
  ↓
Step 3: Config / Secret 読込
  - ConfigProvider.reload()
  - SecretProvider.list_keys() で期待 keys の存在確認
  Fail → ローカルファイルログ + Notifier critical + exit
  ↓
Step 4: Config Version 計算 (6.19)
  - ConfigProvider.compute_config_version() → (config_version, source_breakdown)
  - 前回 run の config_version と比較
  - 前回と異なる場合: Notifier info (event_type=config.version_changed, payload=diff)
  ↓
Step 5: DB 接続確認
  - PersistenceAdapter.get_engine() で接続
  - 疎通 SELECT 1
  Fail → FileNotifier critical + Notifier critical (Slack/Email) + exit
  ↓
Step 6: Alembic Revision 確認
  - 現行 DB revision が想定値 (アプリ起動時点の期待 head) と一致
  Fail → Notifier critical + exit (migration 適用漏れ検出)
  ↓
Step 7: SafeStopJournal ↔ DB 整合 (6.1)
  - SafeStopJournal.read_recent() と supervisor_events を突合
  - Journal にあり DB にない safe_stop → DB に補完 (Reconciler の一部)
  - 結果を supervisor_events に journal_reconcile_completed として記録
  ↓
Step 8: Outbox Pending 処理 (6.6)
  - OutboxProcessor が outbox_events.status ∈ {pending, dispatching} を pick
  - dispatching で place_order_timeout_seconds 超過分を FAILED に遷移
  - pending を通常 dispatch に乗せる
  ↓
Step 9: Account Type 起動検査 (6.18)
  - Broker.account_type 取得
  - app_settings.expected_account_type と比較
  - 不一致: Notifier critical (account_type.mismatch) + exit
  - 一致: Broker._startup_verified_type にセット、supervisor_events に account_type_verified 記録
  - live 初回切替時は別途 --confirm-live-trading フラグ待ち (6.18 運用手順)

  【demo↔live 切替 SQL runbook (M13b)】
  demo → live 切替手順（必ず 4 重防御を順守すること）:
    1. アプリ停止: `python scripts/ctl.py stop` で safe_stop を完了させる
    2. app_settings 更新 (手動 SQL):
         UPDATE app_settings
         SET value = 'live', introduced_in_version = (SELECT MAX(introduced_in_version) FROM app_settings)
         WHERE name = 'expected_account_type';
       確認: SELECT name, value FROM app_settings WHERE name = 'expected_account_type';
    3. 環境変数設定: .env に OANDA_ACCOUNT_TYPE=live を追記（OANDA_ACCESS_TOKEN も live 用に差し替え）
    4. アプリ再起動: `python scripts/ctl.py start --confirm-live-trading`
       ※ --confirm-live-trading フラグなしで起動した場合は LiveConfirmationGate Stage 2 でブロック

  live → demo 切替手順:
    1. アプリ停止: `python scripts/ctl.py stop`
    2. app_settings 更新:
         UPDATE app_settings SET value = 'demo' WHERE name = 'expected_account_type';
    3. .env を demo 用 OANDA_ACCESS_TOKEN に戻し、OANDA_ACCOUNT_TYPE=demo に変更
    4. アプリ再起動: `python scripts/ctl.py start` （--confirm-live-trading 不要）

  注意事項:
  - 上記 SQL は `app_settings_changes` への記録も推奨 (audit trail):
      INSERT INTO app_settings_changes (name, old_value, new_value, changed_by, changed_at, reason)
      VALUES ('expected_account_type', 'demo', 'live', 'operator', NOW(), '切替理由を記述');
  - live 実発注は Iteration 3 以降で運用解禁 (IP2-Q0)。Iter2 は demo 接続のみ。
  - expected_account_type の UI 経由変更は禁止 (operations.md §15.1 / M26)
  ↓
Step 10: Reconciler 起動時実行 (6.12 Action Matrix)
  - Reconciler.reconcile_on_startup(context)
  - DB と OANDA の positions / pending_orders / recent_transactions を突合
  - 自動補正範囲外の不整合: degraded モード遷移 + Notifier critical + 手動待ち
  - 結果を reconciliation_events に記録
  ↓
Step 11: Stream 接続開始
  - PriceFeed.subscribe_price_stream(universe)
  - PriceFeed.subscribe_transaction_stream(account_id)
  - StreamWatchdog 起動 (heartbeat 監視、gap 検出)
  ↓
Step 12: Feature Service / Model 初期化
  - FeatureBuilder 初期化 (feature_version 確認)
  - ModelRegistry.get_active(strategy_type) で active AI model ロード
  - shadow model があれば shadow モードで起動
  Fail → 警告 + Stub フォールバック (AI だけ失敗、他戦略は継続)
  ↓
Step 13: MidRunReconciler 起動
  - 15 分毎 drift check を開始、priority=low
  ↓
Step 14: OutboxProcessor 本格稼働開始
  - resume_dispatch()
  ↓
Step 15: Supervisor 通常監視 開始
  - health() で全コンポーネント状態確認
  - 全 green → トレーディングループ開始許可
  ↓
Step 16: 通常稼働 (Normal Operation)
```

**Decision (2.1-1)**: Step 2-10 のいずれかで失敗した場合、**トレーディングループは起動しない**。Step 11-14 の部分失敗は degraded モードで起動する (縮退運用)。

**Iteration 2 実装状態 (本実装 vs stub)**:
- **本実装 (Iter2 完了)**: Step 0-7, Step 9, Step 15, Step 16 — `src/fx_ai_trading/supervisor/startup.py` 参照
- **Stub / 部分実装 (Phase 7 で本実装)**: Step 8 (OutboxProcessor pending) / Step 10 (Reconciler) / Step 11 (Stream subscription、`stream_watchdog.py` M8 stub) / Step 12 (Feature Service / Model init) / Step 13 (MidRunReconciler、M15 で本実装済み) / Step 14 (OutboxProcessor resume)
- Iter2 の `python scripts/ctl.py start` は 16 Step を全て呼出すが、stub Step は no-op or 最小実装で通過する。Phase 7 で本実装に差替えても呼出側の契約は不変。

### 2.2 定常処理 (Normal Cycle, 1 分周期)

毎分 cycle_id が発行されて以下を実行 (Phase 1 / 4 継承):

```
[00:00] cycle_id 発行 (UUID)
  ↓
[00:00.1s] InstrumentUniverse.list_active() (動的取得、OANDA / キャッシュ)
  ↓
[00:00.5s] MarketDataIngester.ingest_candles_for_instrument(*) — 並列
  ↓
[00:01s] FeatureBuilder.build(instrument, tier, cycle_id, as_of_time=now) — 並列
  ↓
[00:02s] StrategyEvaluator.evaluate() — 3 戦略 × 通貨ペア並列
  ↓
[00:04s] EVEstimator.estimate(*) — 並列
  ↓
[00:05s] MetaDecider.decide(candidates, context)
  - Filter → Score → Select
  - score_contributions 記録、concentration_warning 判定
  - regime_detected 判定 (相関双窓)
  ↓
[00:06s] RiskManager.accept(decision, exposure)
  - no_trade_events / risk_events 書込
  ↓
[00:07s] trading_signals 生成 (採用された MetaDecision のみ)
  ↓
[00:08s] OrderLifecycleService.submit(trading_signal)
  - orders(PENDING) + outbox_events(ORDER_SUBMIT_REQUEST) を同一 tx で commit (6.6)
  ↓
[00:09s 〜] OutboxProcessor が非同期 dispatch
  - ExecutionGate.check (6.15 TTL 判定含む)
  - Approve → Broker.place_order (6.18 assertion + 6.4 ULID)
  - Reject → execution_metrics に記録、orders.status=FAILED
  - Defer → 再評価待ち
  ↓
[00:* 非同期] transaction stream から fill 受信
  - OrderLifecycleService.on_transaction_event()
  - orders.status=FILLED + positions + account_snapshots 更新
  ↓
[00:* 非同期] ExitPolicy 評価 (保有ポジションに対して毎 cycle)
  - 発火条件合致 → close_events 記録 + Broker 経由で決済発注
  ↓
[00:59s] cycle 完了、metrics を supervisor_events に記録
  ↓
[次 cycle]
```

**Decision (2.2-1)**: cycle_timeout_seconds=45 (6.5) を超過した cycle は次 cycle を skip せず、遅延しつつ処理を完走させる。ただし `data_quality_events(reason_code=cycle_slow)` に記録。連続 5 cycle timeout で Notifier warning。

### 2.3 シグナル生成 → 発注フロー (詳細)

2.2 の [00:08s 〜] 部分を展開:

```
trading_signals.insert(PENDING)
  ↓
outbox_events.insert(ORDER_SUBMIT_REQUEST, status=pending)
  ↓
COMMIT tx  ← ここまでで一次DB に永続化 (6.6 の不変条件)
  ↓
OutboxProcessor が pending を pick (in-memory queue or polling)
  ↓
ExecutionGate.check(intent, realtime_context)
  - TTL 判定 (6.15): now - created_at > signal_ttl_seconds なら Reject(SignalExpired)
  - Defer 連発判定 (6.15): defer_count >= defer_exhausted_threshold なら Reject(DeferExhausted)
  - spread / stale price / broker 疎通 チェック
  ↓
  Approve:
    Broker.place_order(OrderRequest)
      → _verify_account_type_or_raise() (6.18)
      → HTTP → OANDA
      → 成功: orders.status=SUBMITTED + outbox_events.status=acked
      → 失敗: orders.status=FAILED + outbox_events.status=failed + retry_events
  Reject:
    orders.status=FAILED + execution_metrics(reject_reason=X)
  Defer:
    defer_until に timestamp セット、outbox_events を再 pending 化
```

### 2.4 約定反映フロー

```
OANDA transaction stream → TransactionEvent 受信
  ↓
OrderLifecycleService.on_transaction_event(event)
  ↓ (event.type = ORDER_FILL / ORDER_CANCEL / STOP_LOSS_TRIGGERED / TAKE_PROFIT_TRIGGERED / MARGIN_CALL / SWAP_APPLIED 等)
  ↓
order_transactions に append (生データ保存)
  ↓
events.type 別にディスパッチ:
  - ORDER_FILL: orders.status=FILLED + positions append (open) + execution_metrics
  - STOP_LOSS_TRIGGERED / TAKE_PROFIT_TRIGGERED: close_events + positions append (close) + account_snapshots
  - SWAP_APPLIED: account_snapshots (swap 列加算)
```

### 2.5 日次締め (Daily Close)

毎日 00:00 UTC 境界 (世界標準市場クローズ近傍) で以下を実行:

```
1. account_snapshots を trigger_reason=daily_close で取得 (全口座)
2. Aggregator 起動: strategy_performance (日次 window) / daily_metrics
3. system_jobs に aggregator_job として記録
4. 実行結果を daily_metrics に永続保持
5. Notifier info (event_type=daily_close_completed、payload に PnL / DD サマリ)
```

**Decision (2.5-1)**: 日次締めは **別プロセス / 別 job** (Supervisor が kick)。トレーディングループと並列で実行され、ブロックしない。

### 2.6 再計算 / 再実行

アーキテクチャ原則: **元データは No-Reset で残る**ので、派生データ (Aggregate, meta_strategy_evaluations 反実仮想) は**再計算可能**。

- `strategy_performance` 再計算: 同一 window_class + window_start で Aggregator 再実行 → UPSERT で更新
- `meta_strategy_evaluations` 再計算: `meta_eval_protocol_version` を上げて再 kick、既存行は残る
- `daily_metrics` 再計算: date_utc + account_id 指定で Aggregator 再実行
- Backtest 再実行: 同 `backtest_run_id` で再 kick は禁止 (新 run_id で実行)

**Invariants (Aggregator idempotency)**: 再計算は同入力で同出力。version 列を跨ぐ集計は禁止 (D1 / D5)。

---

## 3. 手動介入が許可 / 禁止されるケース

### 3.1 許可される手動介入

| 操作 | 許可条件 | 手順 | UI 経由可否 (Iter3+) |
|---|---|---|---|
| safe_stop 状態からの復帰 | 事故調査完了 | `python scripts/ctl.py resume-from-safe-stop --reason="..."` + 監査ログ | ○ Operator Console (ctl ラッパ、reason 必須) |
| degraded モードからの復帰 | 整合性確認後 | Reconciler 再実行 → 復帰条件 (health green) を確認 | △ Reconciler 再実行のみ (Operator Console)。直接的な状態書込は UI 経由禁止 |
| `expected_account_type` を demo ↔ live 切替 | 運用者判断 | 手動 SQL で変更 → アプリ再起動 → 起動 assertion → --confirm-live-trading | △ 表示のみ。変更は Iter3 でも CLI/SQL 維持 (6.18 4 重防御維持、UI からは参照のみ) |
| `app_settings` の設定値変更 | 運用者判断 | 手動 SQL + `app_settings_changes` 記録 + config_version bump | △ Configuration Console「稼働中モード」で変更キュー (即時反映なし、適用は再起動 or hot-reload 経由) |
| 学習 job の enqueue | UI | ダッシュボードの学習 UI (M21、§15.1 / §15.3 参照) | ○ Learning UI (Operator Console とは**別系統**、M21 で拡張) |
| Emergency Flat (全ポジションクローズ) | 緊急時 | `python scripts/ctl.py emergency-flat-all` (UI 非依存、6.14) | × UI 非依存維持 (CLI 専用、2-factor 必須、6.14) |
| Reconciler 手動 kick | degraded 状態の調査後 | `python scripts/ctl.py run-reconciler` | ○ Operator Console (ctl ラッパ) |
| Alembic migration 適用 | リリース時 | `alembic upgrade head` + 事前バックアップ | × CLI 専用維持 (UI から実行禁止) |

### 3.2 禁止される手動介入

以下は**絶対禁止** (CI lint + コードレビュー + 運用教育で徹底):

| 操作 | 禁止理由 |
|---|---|
| 本番 DB での `DELETE FROM *` 直接発行 | D5 単純 DELETE 禁止 |
| 本番 DB での `TRUNCATE` / `DROP TABLE` | D5 No-Reset |
| `orders.status` の後退遷移 (FAILED → PENDING 等) | D3 / D1 FSM |
| `client_order_id` の手動発行・再利用 | 6.4 ULID 冪等性担保崩壊 |
| SafeStopJournal (`logs/safe_stop.jsonl`) の手動編集・削除 | 6.1 二次正本の改ざん |
| `supervisor_events` / `reconciliation_events` の手動削除 | 監査証跡の毀損 |
| OANDA 側で直接ポジションクローズ (アプリを経由せず) | 整合性崩壊、Reconciler が混乱 (緊急時のみ例外、手動介入ログ必須) |
| 複数プロセスでの同時書込 (同一 account_id で multi-process 起動) | Outbox / State Manager の排他崩壊 |

### 3.3 緊急時例外

以下のみ一時的に禁止事項を超える操作が許容される (ただし事後に必ず監査ログと recovery 手順を文書化):

- OANDA API / アプリ停止で broker 側で直接全ポジション close (アプリ復旧後に Reconciler で整合)
- DB 破損時のバックアップリストア (No-Reset の例外として記録)

---

## 4. 障害分類と初動手順 (Runbook)

### 4.1 障害分類一覧

| # | 障害 | 検知経路 | 自動対応 | 手動初動 |
|---|---|---|---|---|
| F1 | Market data 欠損 (candles / ticks) | MarketDataIngester / FeatureBuilder | 該当 instrument を no_trade、data_quality_events | ログ確認、欠損期間の再取得判断 |
| F2 | Prediction failure (AI model) | Predictor / StrategyEvaluator | Stub フォールバック | ModelRegistry 確認、再ロード判断 |
| F3 | Broker API 5xx / timeout | Broker.place_order | RetryPolicy + degraded (閾値超) | Broker 状態確認、Phase 7 の route 切替判断 |
| F4 | Network 断 (OANDA 到達不可) | Broker / PriceFeed | Retry + safe_stop (長期断) | ネットワーク確認、手動で SafeStop 維持 |
| F5 | Persistence failure (DB 書込失敗) | Repository / SafeStopJournal | Critical tier → safe_stop、Important/Observability → 継続 | DB 健康状態確認、接続再確立 |
| F6 | Reconciliation mismatch (自動補正不能) | Reconciler | degraded モード + Notifier critical | OANDA / DB 突合、手動整合 |
| F7 | Duplicate execution risk | OutboxProcessor / Reconciler | ULID 冪等で broker 側で弾く | 発注履歴確認 |
| F8 | Stream gap (transaction stream) | StreamWatchdog | 再接続 + MidRunReconciler (priority=high) + safe_stop (長期) | Stream 状態確認 |
| F9 | Stale price (過齢データ) | ExecutionGate | Reject(StaleSignal) | PriceFeed 確認 |
| F10 | Margin call risk | AccountSnapshotter | no_trade + Notifier warn (50%) / critical (30%) | ポジション縮小判断 |
| F11 | Drawdown 閾値到達 | Supervisor | Notifier warn (80%) / safe_stop (100%) | 事故調査、戦略停止判断 |
| F12 | Config / Secret 読込失敗 | 起動時 §2.1 Step 3 (Config / Secret 読込) | 起動拒否 | Secret Provider 確認 |
| F13 | Alembic revision 不一致 | 起動時 §2.1 Step 6 (Alembic Revision 確認) | 起動拒否 | migration 確認 |
| F14 | Account type mismatch | 起動 §2.1 Step 9 (Account Type 起動検査) or 発注前 (Broker.place_order pre-assertion) | 起動拒否 or safe_stop | Broker 設定確認 |
| F15 | NTP skew 大幅 | 起動 §2.1 Step 2 (NTP 起動検査) or 定期再検 | warn (500ms+) / 起動拒否 (5s+) | NTP サービス確認 |

### 4.2 Runbook テンプレート (F1–F15 共通)

各障害に対して以下のテンプレートで対応:

```
[障害名]: F#

状況把握 (5 分以内):
  1. Notifier で受信した payload 確認
  2. Dashboard で last_data_at / degraded_mode / safe_stop 状態確認
  3. supervisor_events / anomalies / reconciliation_events の直近を確認
  4. 関連テーブル (障害種別による) の直近書込確認

初動判断 (5–15 分以内):
  - 自動対応が進行中 → 結果待ち (Notifier で次イベントを監視)
  - degraded / safe_stop → 事故調査モード

事故調査:
  - correlation_id で系統横断トレース (cycle_id / order_id でも可)
  - 該当期間の strategy_signals / meta_decisions / ev_breakdowns / orders / positions を SQL 抽出
  - market_candles / economic_events で市場側の特異事象確認

復旧判断:
  - データ欠損・一時的 API 障害 → 自動リカバリ完了を待つ
  - Reconciliation mismatch → 手動整合 or OANDA 側で手動調整 + ログ記録
  - safe_stop → 根本原因特定後に `python scripts/ctl.py resume-from-safe-stop`

事後対応:
  - 障害レポートを supervisor_events (event_type=incident_report) に記録
  - 類似再発防止のため app_settings / 閾値調整判断
  - 必要なら Phase 7 chaos scenario に追加
```

### 4.3 障害別初動フロー

F1 / F7 / F9 は自動処理で運用者初動が発生しないため省略 (§4.1 表参照)。

#### F2: Prediction failure (AI model)

```
1. Predictor 例外検知 (logs/supervisor.log + supervisor_events 警告)
2. 自動: Predictor が Stub フォールバックに切替 (取引継続)
3. strategy_signals は stub_used=true で記録継続
4. 運用者: ModelRegistry でモデル状態確認:
   - 確認順: (a) `ModelRegistry.get_active(strategy_type)` で active 版を特定 → (b) 成果物ファイル存在 → (c) ファイル整合性 → (d) version 互換性
   - 参照先: `model_registry` テーブル (state ∈ {stub/shadow/active/review/demoted}、6.11 AIStrategy lifecycle / implementation_contracts §2.3.1)
   - 判定基準: 成果物欠落 → 再配置 / 整合性 NG → 再配置 / version 互換性なし → ロールバック判断
5. 復旧:
   - モデル再ロード可能 → ModelRegistry update + Notifier info
   - 不可 → 該当戦略を `strategy.AI.enabled=false` で一時停止 (6.17)
6. fallback 解除: 次 cycle で strategy_signals.stub_used=false を 1 件以上確認
```

#### F3: Broker API 5xx / timeout

```
1. Broker.place_order が 5xx / timeout を検知 (retry_events に記録)
2. 自動: RetryPolicy 適用
3. retry 上限到達 → degraded モード遷移 + Notifier critical
4. 運用者: OANDA ステータスページ / 直近 retry_events で原因切り分け
5. 一過性 (5xx 一時障害) → 自然回復待ち、degraded 自動解除
6. 持続 (恒常的 5xx / API 仕様変更) → §9.2 degraded 復帰手順
7. Phase 7 で route 切替 (broker fallback) 検討対象
```

#### F4: Network 断 (OANDA 到達不可)

```
1. Notifier で `oanda.api_persistent_error` (warning) 受信
2. 5 分連続で受信継続 → Supervisor が safe_stop 検討開始
3. 運用者確認: インターネット接続 / OANDA ステータスページ
4. 長期障害確定:
   - Supervisor safe_stop(reason=oanda_unreachable) 自動発火
   - 既存ポジは ExitPolicy に従う (通常は自動クローズ発注されない、次回接続時の処理)
5. 復旧時:
   - 接続回復を Notifier `oanda.api_recovered` で確認
   - 運用者判断: `python scripts/ctl.py resume-from-safe-stop`
   - Reconciler が OANDA と突合、不整合あれば degraded で待機
```

#### F5: DB 書込失敗 (Critical tier)

```
1. Notifier で `db.critical_write_failed` (critical) 受信
2. SafeStopJournal に safe_stop 記録確認 (fsync 済)
3. supervisor_events と journal 突合:
   - journal にあり DB にない → DB 復旧を待つ (Journal が正本)
4. DB 接続復旧:
   - 基本原因 (disk full / connection pool exhausted / service down) を切り分け
   - 必要なら pg_restore + WAL replay (バックアップから)
5. 復旧確認:
   - Repository 経由で疎通 SELECT + insert 試験
6. アプリ再起動:
   - Reconciler が SafeStopJournal で DB 補完
   - 通常起動フローに復帰
```

#### F6: Reconciliation mismatch (自動補正不能)

```
1. Notifier `reconciler.mismatch_manual_required` (critical) 受信
2. degraded モード自動遷移 — 新規発注停止 (Reconciler 判定)
3. reconciliation_events から不整合タイプ確認:
   - position_qty_mismatch / order_status_mismatch / stale_pending_order
4. OANDA 管理画面で実状態を目視確認:
   - position_qty_mismatch → 「Open Positions」画面の units と DB `positions.units` を instrument 単位で照合
   - order_status_mismatch → 「Pending Orders」「Trade History」画面と DB `orders.status` を `client_order_id` 単位で照合
   - stale_pending_order → 「Pending Orders」画面に DB `orders.status=PENDING` の `client_order_id` が存在するか確認
5. 手動整合判断:
   - 自然解消可能 (次 fill / close で吸収) → 待機
   - 不可 → orders.status の前進遷移のみで補正 (§3.2 後退禁止)
   - 補正内容を reconciliation_events に audit 記録 (例):
     ```sql
     INSERT INTO reconciliation_events
       (reconciliation_event_id, trigger_reason, action_taken,
        order_id, event_time_utc, detail)
     VALUES (:event_id, :trigger_reason, :action_taken,
             :order_id, NOW(), :detail_json);
     -- trigger_reason ∈ {startup, midrun_heartbeat_gap, periodic_drift_check}
     ```
6. `python scripts/ctl.py run-reconciler` 再実行 → green なら degraded 解消
7. 解消不能 → §9.2 (degraded 復帰) / §9.3 (safe_stop 復帰) へ
```

#### F8: Stream gap (transaction stream)

```
1. StreamWatchdog が heartbeat 60 秒途絶を検知
2. Notifier `stream.gap_detected` (warning)
3. 自動: MidRunReconciler priority=high に昇格 + get_recent_transactions(since=last_seen) で補完
4. 補完成功: priority=low に戻す、completed ログ
5. 補完不能 (OANDA 再生ウィンドウ超過、判定基準: get_recent_transactions が `since` パラメータに対して "out of range" / 空応答 / since 直後以降の txn が連続欠落 のいずれかを返した場合):
   - degraded 遷移 + Notifier critical (`stream.gap_sustained` に格上げ)
   - 運用者: Dashboard で positions と OANDA 側を目視確認 (F6 step 4 の照合手順を流用)
6. 長期不可 (heartbeat 途絶 120 秒超):
   - safe_stop(reason=stream_gap_sustained) 自動発火
```

#### F10: Margin call risk

```
1. AccountSnapshotter が margin_level (= equity / margin_used × 100%) を監視
2. margin_level ≤ 50% (margin_warning_pct): Notifier warn、no_trade 傾向 (RiskManager で rejection 増)
3. margin_level ≤ 30% (margin_critical_pct): Notifier critical + 自動 no_trade、全新規発注停止 (risk_events で記録)
4. 運用者確認: positions、市場状況
5. 判断:
   - 自然クローズ待機 (ExitPolicy に任せる)
   - 手動 Emergency Flat (`python scripts/ctl.py emergency-flat-all`)
6. 復旧: margin_level 改善後に no_trade 解除 (詳細は phase6_hardening.md §6.14)
```

#### F11: Drawdown 閾値到達

```
1. Supervisor が daily_metrics 監視
2. ratio > 80% of safe_stop_daily_loss_pct (= 4%): Notifier warn (drawdown.warning)
3. ratio > 100% (= 5%): safe_stop(reason=drawdown_daily_exceeded) 自動
4. 運用者: 事故調査、原因分析
5. 判断:
   - 戦略調整 (app_settings で重み変更)
   - 戦略一時 OFF (`strategy.AI.enabled=false` 等、6.17)
6. 再稼働: `python scripts/ctl.py resume-from-safe-stop`
```

#### F12: Config / Secret 読込失敗

```
1. 起動時 §2.1 Step 3 (Config / Secret 読込) で例外
2. 起動拒否: プロセス終了 (PID file 未生成)
3. logs/supervisor.log に root cause 記録 (file 不在 / parse error / decrypt failure)
4. 運用者: Secret Provider (env / file / KMS) を確認
5. 修正後: `python scripts/ctl.py start` で再起動
6. 起動成功確認: PID file 生成 + §2.1 Step 16 (通常稼働) 到達
```

#### F13: Alembic revision 不一致

```
1. 起動時 §2.1 Step 6 (Alembic Revision 確認) で head 不一致
2. 起動拒否: プロセス終了
3. 運用者: alembic current / alembic heads で差分確認
4. 判断:
   - 未適用 migration あり → alembic upgrade head
   - 手動編集等で破綻 → 下記 5 の復旧手順を実施
5. 復旧 (DB 状態が破綻した場合):
   - (a) §9.4 「DB バックアップからの復元」に従い pg_restore で直近 backup を適用
   - (b) WAL replay により最新時点まで前進 (PITR、§7.1 retention/backup 方針)
   - (c) restore 後に再度 alembic upgrade head で head 整合を確認
   - (d) `app_settings` / `supervisor_events` の整合を §9.5 復帰共通原則で検証
6. 修正後: python scripts/ctl.py start で再起動
```

#### F14: Account type mismatch

```
1a. 起動時 §2.1 Step 9 (Account Type 起動検査) で expected_account_type と broker 実態の不一致
    → 起動拒否 + Notifier critical (`account_type.mismatch`)
1b. 発注前 assertion 不一致 (Broker.place_order pre-assertion、6.18)
    → safe_stop(reason=account_type_mismatch_runtime)
2. 運用者: OANDA 管理画面で account type を確認
3. demo ↔ live 切替の場合: §3.1 「expected_account_type 切替」手順に従う
4. live 切替時は --confirm-live-trading 必須 (4 重防御、phase6_hardening.md §6.18)
5. 復帰前必須チェック (無限ループ防止):
   - (a) §3.1 「expected_account_type 切替」runbook の完了を確認
   - (b) `app_settings.expected_account_type` と `.env` の `OANDA_ACCOUNT_TYPE` が一致
   - (c) (b) 未完了で resume を実行すると同一 mismatch を即時再発するため禁止
6. 修正後:
   - 起動拒否ケース → python scripts/ctl.py start
   - safe_stop ケース → python scripts/ctl.py resume-from-safe-stop --reason="..."
```

#### F15: NTP skew 大幅

```
1. 起動時 §2.1 Step 2 (NTP 起動検査) で測定 (ntp_skew_warn_ms=500 / ntp_skew_reject_ms=5000)
2. > 5000ms → 起動拒否 + ローカルファイルログ + Notifier critical (`ntp.skew_reject`)
3. 500–5000ms → warning + 起動継続 + 定期再検 (Notifier `ntp.skew_warning`)
4. 運用者: OS の NTP サービス (w32time / chronyd / ntpd) 状態確認
5. 同期再実行:
   - Windows: w32tm /resync
   - Linux: chronyc makestep / ntpdate -u
6. 同期結果検証:
   - Windows: w32tm /query /status の "Last Successful Sync Time" が直近 / "Phase Offset" がミリ秒オーダー
   - Linux: chronyc tracking の "System time" 行が "0.000xxx seconds" レベル
7. 修正後:
   - 起動拒否ケース → `python scripts/ctl.py start`
   - warning ケース → 定期再検 (Notifier `ntp.skew_warning` の解消) を確認、解消しない場合は §9 へ
```

### 4.4 safe_stop reason_code カタログ

Notifier / supervisor_events に記録される `reason` 値の早見表。
未掲載の reason は §4.3 の詳細フロー / `logs/safe_stop.jsonl` の発火 payload を参照。

| reason | 発火元 | 関連 F# | 復旧手順 | 関連 Notifier event_type |
|---|---|---|---|---|
| `oanda_unreachable` | Supervisor (長期 API 障害確定時) | F4 | §4.3 F4 / §9.3 | `oanda.api_persistent_error` |
| `stream_gap_sustained` | StreamWatchdog (120s 超 gap) | F8 | §4.3 F8 / §9.3 | `stream.gap_sustained` |
| `stream_gap` | StreamWatchdog (`stream_gap_sustained` の Iter3 採用標準名、両者は同じ発火条件を指す互換 alias) | F8 | §4.3 F8 / §9.3 | `stream.gap_sustained` |
| `drawdown_daily_exceeded` | Supervisor (daily_loss_pct 到達) | F11 | §4.3 F11 / §9.3 | `drawdown.stop_threshold` |
| `consecutive_loss_exceeded` | Supervisor (`safe_stop_consecutive_loss_count` 到達、phase6 §6.5 初期値 5) | F11 派生 | §9.3 | (専用 event_type なし、`safe_stop.fired` payload に reason) |
| `db_critical_write_failed` | Supervisor (Critical tier 書込失敗確定、F5 から safe_stop へ昇格) | F5 | §4.3 F5 / §9.4 | `db.critical_write_failed` |
| `account_type_mismatch_runtime` | Broker.place_order pre-assertion | F14 | `phase6_hardening.md` §6.18 / §9.3 | `account_type.mismatch` |

復旧の共通原則:
- reason 確認 → 該当 F# の §4.3 フロー → §9.3 (safe_stop 復帰) の順で進む
- 命名規則: reason_code は **underscore_only** (例 `db_critical_write_failed`)、Notifier event_type は **dot-separated** (例 `db.critical_write_failed`)。schema_catalog.md §2.3 Note 参照。

---

## 5. 再試行ルールと Idempotency

### 5.1 RetryPolicy 共通原則 (6.14 継承)

- 全ての外部 I/O (broker / DB / stream 再接続) に RetryPolicy 適用
- RetryPolicy + RateLimiter の合成順序: **RateLimiter が前段** (6.14 P6)
- 全リトライは `retry_events` に記録
- 上限到達で degraded or safe_stop (事象別、4.1 表参照)

### 5.2 Idempotency 保証点

| 操作 | 冪等キー | 実装 |
|---|---|---|
| place_order | `client_order_id` (ULID) | broker 側冪等 + DB の orders PK |
| order_transactions 書込 | `(broker_txn_id, account_id)` | PK 衝突時は skip (ON CONFLICT DO NOTHING) |
| market_candles 書込 | `(instrument, tier, event_time_utc)` | ON CONFLICT DO NOTHING |
| Aggregator rollup | `(window_class, window_start, strategy_type, ...)` | UPSERT |
| Archive ジョブ | `(table_name, partition_key)` | system_jobs で重複防止 |

### 5.3 二重実行防止

- 同一プロセスでの重複 outbox dispatch: in-memory lock (outbox_event_id 単位)
- 複数プロセスでの重複 (multi_service_mode 前提): advisory lock (PostgreSQL `pg_advisory_lock`)
- Job の二重起動: JobScheduler が同 job_type + key で排他

---

## 6. ログ / メトリクス / アラート

### 6.1 ログ層 (Phase 3 継承)

Criticality Tier 別の書込経路:

| Tier | 対象テーブル | 書込方式 | 失敗時 |
|---|---|---|---|
| **Critical** | orders / order_transactions / close_events / supervisor_events (safe_stop 系) | 同期 tx commit | safe_stop |
| **Important** | strategy_signals / meta_decisions / ev_breakdowns / execution_metrics / 採用直結 no_trade_events / data_quality_events | at-least-once 非同期 | ログ化、継続 |
| **Observability** | feature_snapshots / drift_events / anomalies / retry_events / stream_status / 要約 no_trade_events | best-effort + サンプリング | silent drop |

### 6.2 メトリクス (MVP 最小)

Supervisor が 1 分毎に以下を `supervisor_events(event_type=metric_sample)` に記録:

| メトリクス | 説明 |
|---|---|
| `cpu_percent` | プロセス CPU 使用率 |
| `memory_rss_mb` | Resident Set Size |
| `db_connections_count` | Repository から見た active 接続数 |
| `cycle_duration_seconds` | 直近 cycle の所要時間 |
| `outbox_pending_count` | outbox_events.status=pending の数 |
| `notification_outbox_pending_count` | 同上 (通知) |
| `stream_heartbeat_age_seconds` | 最後の heartbeat 受信からの経過 |
| `active_positions_count` | 現在保有ポジション数 |
| `concurrent_orders_pending_count` | orders.status=PENDING の数 |

**Decision (6.2-1)**: MVP は supervisor_events に text で記録。Phase 7 で Prometheus 等へ移行。

### 6.3 アラート (6.13 Notifier 必須イベント)

critical 経路の fan-out 順序（M17）: **File → Slack → Email**。
各経路は独立 — Email 失敗は File/Slack を阻害しない。
SMTP 設定: `SMTP_HOST` / `SMTP_PORT` / `SMTP_SENDER` / `SMTP_RECIPIENTS` / `SMTP_USERNAME` / `SMTP_PASSWORD` 環境変数（`.env` 経由）。

**Critical event 集合 (Iter3 cycle 3 確定 / 7 件)**: severity=critical かつ sync direct (outbox bypass) で File+Slack+Email へ fan-out するイベント:
1. `safe_stop.fired`
2. `db.critical_write_failed`
3. `db.connection_lost_sustained`
4. `stream.gap_sustained`
5. `drawdown.stop_threshold`
6. `reconciler.mismatch_manual_required`
7. `ntp.skew_reject` (※ DB 接続前 / 起動拒否時に発火するため Slack/Email は best-effort、File のみ必須)

| イベント | severity | channel | escalation |
|---|---|---|---|
| safe_stop.fired | critical | File + Slack + Email (sync direct) | 即時 |
| safe_stop.cleared | info | sync direct (info 例外、journal 連続性のため outbox bypass) | なし |
| db.critical_write_failed | critical | File + Slack + Email (sync direct) | 即時 |
| db.connection_lost_sustained | critical | File + Slack + Email (sync direct) | 即時 |
| stream.gap_sustained | critical | File + Slack + Email (sync direct) | 即時 |
| reconciler.mismatch_manual_required | critical | File + Slack + Email (sync direct) | 即時 |
| ntp.skew_reject | critical | File 必須 + Slack/Email best-effort (DB 接続前 / 起動拒否時に発火するため Slack/Email は到達不能の場合あり) | 手動調査 |
| mode.degraded.entered | warning | outbox | 30 分以内 |
| mode.degraded.cleared | info | outbox | なし |
| drawdown.warning | warning | outbox | 30 分以内 |
| drawdown.stop_threshold | critical | File + Slack + Email (sync direct) | 即時 |
| stream.gap_detected | warning | outbox | 30 分以内 |
| oanda.api_persistent_error | warning | outbox | 1 時間以内 |
| event_calendar.stale | warning | outbox | 運用者確認後解消 |
| ntp.skew_warning | warning | outbox | 定期再検で解消 |
| config.version_changed | info | outbox | 監査 |

### 6.4 ヘルスチェック

Supervisor が以下を 10 秒毎にチェック:

| 項目 | 異常判定 |
|---|---|
| DB 接続 | `SELECT 1` が 2 秒以上または失敗 |
| Broker 疎通 | get_positions() が 5 秒以上または失敗 (optional、rate limit 考慮) |
| Price stream heartbeat | 60 秒超 gap |
| Transaction stream heartbeat | 60 秒超 gap |
| Outbox processor 生存 | last_processed_at が 5 分以上更新なし |
| Notifier 生存 | FileNotifier が 5 分以上書込なし (heartbeat 自己発行) |

異常検知で degraded or safe_stop (4.1 表に準拠)。

---

## 7. バックアップと復旧 (D5 連動)

### 7.1 バックアップスケジュール (MVP)

| 対象 | 頻度 | 保存先 | 保持期間 |
|---|---|---|---|
| 一次DB 論理ダンプ (pg_dump -Fc) | 日次 00:30 UTC | ローカル SSD + 外部 (Phase 8 で S3) | 30d |
| 一次DB WAL アーカイブ | 連続 | 同上 | 7d |
| `logs/safe_stop.jsonl` | 日次 (日次バックアップに含む) | 同上 | 180d |
| `logs/notifications.jsonl` | 週次 | 同上 | 90d |
| Cold Archive (Parquet) | D5 Archiver ジョブ起動時 | 別ストレージ | 永続 |

### 7.2 リストアテスト

- **月次**: staging 環境で直近 pg_dump をリストア、起動確認
- **月次**: Cold Archive (Parquet) のランダムサンプル Verify
- 失敗時: Notifier critical + 調査

### 7.3 事業継続 (BCP)

- **RPO (Recovery Point Objective)**: 24 時間 (論理ダンプ)、分単位 (WAL 追いつき)
- **RTO (Recovery Time Objective)**: 2 時間 (MVP)、Phase 8 の DR 訓練で改善

---

## 8. 監査時に追跡する項目

### 8.1 取引追跡

1 取引を追跡するには以下の軸で SQL JOIN:

```
cycle_id (分足単位)
  → strategy_signals (全候補)
    → meta_decisions (採用判断)
      → trading_signals (採用された発注意図)
        → orders (発注、ULID)
          → order_transactions (OANDA 側イベント)
            → positions (ポジション推移)
              → close_events (決済理由)
                → execution_metrics (執行品質)

並行記録:
  - ev_breakdowns (EV 内訳)
  - feature_snapshots (判断時点の特徴量)
  - risk_events (Risk accept/reject)
  - no_trade_events (不採用の根拠)
  - account_snapshots (資金推移)
```

### 8.2 変更追跡

- **設定変更**: `app_settings_changes` で who / when / what を追跡
- **モデル変更**: `model_registry` 状態遷移 + `training_runs` / `model_evaluations`
- **コード変更**: Common Keys の `code_version` で時点特定
- **Config 変更**: Common Keys の `config_version` で effective_config 全体の fingerprint

### 8.3 事故追跡

- `supervisor_events` (safe_stop / degraded 遷移)
- `reconciliation_events` (整合性事象)
- `anomalies` (アプリ一般異常)
- `data_quality_events` (データ品質)
- `retry_events` (リトライ履歴)
- `logs/safe_stop.jsonl` (DB 非依存の二次証跡)

---

## 9. リカバリ方針

本章は障害発生後の**状態復帰**を一本化する。検知 → 分類 → 復帰の順に、迷わず subsection を選択できる構造を提供する。

### 9.0 状態遷移と復帰判断 (Where to Read)

```text
       ┌──────────┐   trigger (F1-F15)    ┌────────────┐
       │  normal  │ ────────────────────▶ │  degraded  │
       └──────▲───┘                       └─────┬──────┘
              │                                 │ 閾値超 / 持続
              │ health green                    ▼
              │                          ┌────────────┐
              └──────────────────────────│ safe_stop  │
                          復帰           └────────────┘

  個別 strategy / AI / instrument の縮退 → §9.1 (degraded / safe_stop に至らない)
  degraded → normal                       → §9.2
  safe_stop → normal                      → §9.3
  DB 物理破損 (corruption / disk full)    → §9.4
  全 subsection 共通の進め方               → §9.5
```

| 観測した状態 | 入口 (障害分類) | 復帰 subsection |
|---|---|---|
| 個別戦略 / AI モデル / instrument の不調 (全体は稼働) | §4.3 該当 F# | §9.1 |
| degraded モード遷移 | §4.3 F3 / F6 | §9.2 |
| safe_stop 発火 | §4.3 F4 / F8 / F11 / F14 + §4.4 reason カタログ | §9.3 |
| DB 物理破損 | §4.3 F5 | §9.4 |
| 共通の判断・記録手順 | — | §9.5 |

### 9.1 partial recovery (一部機能の縮退)

**Trigger**: 個別戦略 / AI モデル / 特定 instrument の不調 (degraded / safe_stop に至らない範囲)
**復帰先**: normal (該当機能のみ単独復帰)
**復帰条件**: 該当機能の health green

- 個別戦略の不調: `strategy.X.enabled=false` で OFF、他戦略で継続
- AI モデルの不調: `lifecycle_state=stub` に戻す、または enabled=false
- 特定 instrument の不調: manual で除外リスト (将来機能、Phase 7+)

### 9.2 degraded からの復帰手順

**Trigger**: Reconciler 自動補正不能 (F6) / Broker 5xx 持続 (F3) 等
**復帰先**: normal
**復帰条件**: Reconciler green + Supervisor.health() green
**Note (Iter2)**: `python scripts/ctl.py resume-from-degraded` ヘルパーは未実装。Iter3 候補 (§3.1 経由の手動手順で代替)。

```
1. degraded 原因を supervisor_events / reconciliation_events で特定
2. `python scripts/ctl.py run-reconciler` で再実行、整合性確認
3. 自然回復しない場合: §3.1 許可介入に従い、復帰条件 (health green) が満たされたことを確認
4. Supervisor が health() 確認 → green なら通常稼働復帰
```

### 9.3 safe_stop からの復帰手順

**Trigger**: §4.4 reason カタログ参照 (F4 / F8 / F11 / F14 等)
**復帰先**: normal
**復帰条件**: 事故調査完了 + Reconciler green + Supervisor.health() green

```
1. safe_stop 原因を supervisor_events / journal で特定
2. 事故調査完了、影響範囲の整合性確認
3. 必要なら手動で orders / positions を OANDA と突合、手動整合
4. `python scripts/ctl.py resume-from-safe-stop --reason="..."`
5. Supervisor が Reconciler + health check → green で通常稼働
6. 復帰イベントを supervisor_events + Notifier info で記録
```

### 9.4 DB 破損からの復旧

**Trigger**: DB 物理破損 (corruption / disk full / 接続恒常 down)
**復帰先**: normal (経由: safe_stop → restore → reconcile)
**復帰条件**: pg_restore + WAL replay + Reconciler green

```
1. safe_stop 状態に遷移 (自動)
2. 最新 pg_dump からリストア
3. WAL replay で最新に追いつく
4. Reconciler が OANDA と突合、不整合を reconciliation_events に記録
5. 手動で不整合解消
6. safe_stop 復帰、通常稼働
```

### 9.5 復帰共通原則

§9.1-§9.4 のいずれでも守る統一手順:

```
1. 検知: Notifier (logs/notifications.jsonl) + supervisor_events で root cause 確認
2. trace: §4.3 該当 F# フローを参照 (reason → F# 対応は §4.4)
3. 判定: §9.0 decision tree で subsection 選択
4. 実行: §9.1-§9.4 の手順を順守 (orders.status 後退禁止、§3.2)
5. 記録: 復帰イベントを supervisor_events (event_type=incident_report) + Notifier info に記録
```

**禁止事項** (復帰時も §3.2 を継承):
- `orders.status` の後退遷移
- SafeStopJournal / supervisor_events / reconciliation_events の手動削除
- 単純 DELETE / TRUNCATE (D5 No-Reset)

---

## 10. D1 / D3 / D5 との整合

### 10.1 D1 との整合

- 運用時に書込・読込する全テーブルが D1 で定義済
- Common Keys 伝搬は Repository 経由 (D1 3.3 / D3 3.1)
- 運用は No-Reset (D1 1. / D5 1.1)

### 10.2 D3 との整合

- 運用手順は D3 Interface の expected usage に従う
- 起動時 assertion 群は D3 4. にまとめた通り実行
- 禁止アンチパターン (D3 7.) は運用でも遵守

### 10.3 D5 との整合

- Archive ジョブは D5 の retention class に従う
- バックアップ方針は D5 8. に準拠
- 単純 DELETE 禁止は運用手順でも同様 (CLI は Archiver 経由のみ)

---

## 11. Operations 責務一覧 (Cheat Sheet)

> **ctl 5 コマンド契約 (Iter3 cycle 3 確定)**: 以下表の上 5 行は §15.3 Operator Console 契約と完全一致する正本セット。順序・コマンド名・2-factor 要件は両節で同一であり、片方のみの変更は禁止 (development_rules §13.1 と対応)。M22 / Mi-CTL-1 で確定。

| コマンド / 操作 | 説明 | 権限 |
|---|---|---|
| `python scripts/ctl.py start` | アプリ起動 (起動シーケンス 2.1 を実行) | 運用者 |
| `python scripts/ctl.py stop` | graceful 停止 (SIGTERM → SIGKILL on timeout) | 運用者 |
| `python scripts/ctl.py resume-from-safe-stop --reason=` | safe_stop 復帰 (reason 必須) | 運用者 |
| `python scripts/ctl.py run-reconciler` | Reconciler 手動 kick | 運用者 |
| `python scripts/ctl.py emergency-flat-all` | 全ポジション即クローズ + reject モード (**2-factor 必須**、`TwoFactorAuthenticator` Protocol = implementation_contracts §2.18 / phase6 §6.14 / §15.3) | 運用者 (緊急時のみ) |
| 学習 job enqueue | Streamlit Learning UI から実行 (Iter2、M21 / §15.1 §15.3、`ctl` コマンドは Iter2 では未提供) | 運用者 / UI |
| backtest enqueue | Phase 7+ で `python scripts/ctl.py enqueue-backtest` 追加予定 (Iter2 未実装) | 運用者 |
| `python scripts/ctl.py run-archive-job --table= --partition=` | Cold Archive 手動 kick (Phase 7+) | 運用者 |
| `python scripts/ctl.py start --confirm-live-trading` | live 切替後の trading 開始許可 (4-defense Stage 4 = 運用レイヤ手動 confirmation、phase6 §6.18) | 運用者 (手動必須) |
| `alembic upgrade head` | migration 適用 | 運用者 (リリース時、バックアップ後) |

---

## 12. Open Questions

| ID | 論点 | 解決予定 |
|---|---|---|
| OP-Q1 | `ctl` CLI の具体実装 (argparse / click / typer) | ✅ 解決済 (Iter1 M12 で click 採用、Iter2 M22 で 5 コマンド本格化) |
| OP-Q2 | staging 環境の位置付け (Phase 8 の DR 訓練で必要) | Phase 8 |
| OP-Q3 | VPS での systemd unit / Windows での nssm unit の雛形 | Iter3 候補 (現状: design.md §324 / retention_policy §3 で概念のみ。unit ファイル雛形は未提供) |
| OP-Q4 | Dashboard Query Service で UI からの運用操作をどこまで露出するか | Phase 7/8 (§15 で Iter2 仕様凍結済) |
| OP-Q5 | 複数オペレーター対応時の権限モデル | Phase 8 |

---

## 13. Summary (運用契約固定点)

本書は以下を MVP 運用契約として固定する:

1. **16 Step の起動シーケンス**、各 Step の失敗時挙動明確化
2. **1 分 cycle の定常処理フロー**、cycle_timeout_seconds=45 超過で記録するが skip しない
3. **手動介入の 8 許可 + 8 禁止 + 緊急例外**を明示
4. **障害分類 F1–F15** の検知経路・自動対応・手動初動をマトリクス化
5. **F2-F6 / F8 / F10-F15 の詳細 Runbook** を §4.3 で提供 (F1 / F7 / F9 は自動処理のみ)
6. **メトリクス 9 項目** を supervisor_events に 1 分毎記録
7. **アラート** は 6.13 Notifier 二経路 contract (sync direct / outbox) に従い、critical は M17 三経路 fan-out (File / Slack / Email) で配信
8. **バックアップは RPO 24h / RTO 2h** を MVP から保証
9. **取引追跡は 10 テーブル JOIN** で完全再現可能 (Common Keys + cycle_id + correlation_id)
10. **degraded / safe_stop / DB 破損**の復旧手順を MVP から文書化

---

## 14. Service Mode 運用ガイドライン (D3 §2.14.2 / Iteration 2 M24)

### 14.1 3 モードの位置付け

| モード | `ServiceModeName` 値 | EventBus 実装 | 運用状態 |
|---|---|---|---|
| Single Process | `single_process_mode` | `InProcessEventBus` | **MVP 既定 / 唯一の実運用** |
| Multi Service | `multi_service_mode` | `LocalQueueEventBus` | Interface のみ (Phase 7+) |
| Container Ready | `container_ready_mode` | `NetworkBusEventBus` | Interface のみ (Phase 8+) |

### 14.2 運用ルール (MVP)

1. **`ServiceMode` は起動時に 1 度だけ解決**: `get_service_mode(ServiceModeName.SINGLE_PROCESS)` を composition root で呼び、以降は同一インスタンスを使い回す
2. **モード文字列の手動変更禁止**: `app_settings` / 設定ファイルで `service_mode = single_process_mode` 以外を MVP で指定すると `NotImplementedError` で起動失敗。これは安全装置であり迂回禁止
3. **モード切替は OS 層で吸収**: プロセス再起動は OS の Supervisor (`systemd` / `nssm` / `launchd`) に委譲。アプリ側は `single_process_mode` 前提で動く (D3 §2.14.2 / design.md §324)
4. **将来モードの先行設定は不可**: `multi_service_mode` を Phase 7、`container_ready_mode` を Phase 8 で本番化するまで、いずれの enum 値も実装が `NotImplementedError` を返す。設定ファイルや `app_settings` への先行投入は禁止

### 14.3 Phase 7 / Phase 8 への引継

- **Phase 7**: `MultiServiceMode` の concrete 実装 + `LocalQueueEventBus` の実装。本ガイドラインの §14.2 #2 制約を撤廃する
- **Phase 8**: `ContainerReadyMode` の concrete 実装 + オーケストレータ (k8s / nomad / 等) 選定。`supports_container_orchestration = True` を返す実装を導入

### 14.4 Cheat Sheet (§11) との関係

- §11 の `ctl` コマンドは全て `single_process_mode` 前提。Phase 7+ で multi_service_mode 実運用化する際は `ctl` も再設計対象

---

## 15. UI 操作境界 (Configuration Console / Operator Console)

> **位置付け**: Iteration 2 では仕様凍結のみ（実装は Iteration 3 以降の別 PR）。
> 本章は UI 経由で「許可 / 禁止」「閲覧 / 操作」を**接合面レベルで固定**するための運用契約。
> 実装の有無に関わらず本章の境界を破る変更は禁止 (development_rules §13.1 #16 と対応)。

### 15.1 4 層責務マトリクス

| 層 | 責務 | UI 経由可否 | 取得 / 適用パス |
|---|---|---|---|
| Secret 層 | 取引所 API key / SMTP 認証 / Supabase key 等 | 閲覧 = 不可 (hash 表示のみ) / 入力 = `.env` sink 限定 | 入力: Configuration Console「起動前モード」→ `.env` 書込 → アプリ再起動。読出: SecretProvider (`get` / `get_hash` / `list_keys`、D3 §2.13.2、read-only) |
| Runtime 接続層 | OANDA endpoint / SMTP host / DB DSN | 閲覧 = 表示 (host のみ、credential 部分はマスク) / 変更 = `.env` 経由 | 同上 (Secret 層と同経路、`.env` 一本化) |
| Runtime mode 層 | `expected_account_type` / `service_mode` / `runtime_environment` / 各種 feature flag | 閲覧 = ○ / 変更 = `app_settings_changes` キュー経由のみ (即時反映なし) | Configuration Console「稼働中モード」→ 変更キュー → 再起動 or hot-reload で適用、`app_settings_changes` に監査記録 |
| Operational 層 (Operator Console) | start / stop / resume-from-safe-stop / run-reconciler (M22 確定 5 コマンド中、`emergency-flat-all` 除く 4 コマンド) | 閲覧 = ○ / 操作 = ctl ラッパ経由のみ | Operator Console → `scripts/ctl.py` の既存 usecase を呼ぶだけ。新規 usecase 不導入 |
| Operational 層 (Learning UI、別系統) | enqueue-learning-job / 学習ステータス参照 / 履歴閲覧 | 閲覧 = ○ / 操作 = Learning UI 経由 | Iter1 既存の Streamlit Learning UI (M21 で enqueue / status / history 拡張、IP2 §6.9)。Operator Console とは**別系統**で、ctl 5 コマンド契約 (§15.3) の上限には含まれない |

**Emergency Flat (`python scripts/ctl.py emergency-flat-all`) は 4 層のいずれにも入らず UI 非依存維持** (6.14 / 6.18 4 重防御の継続)。

### 15.2 Configuration Console の 2 モード

- **起動前モード (Bootstrap)**: アプリ未起動時のみ操作可能。`.env` への書込が唯一の sink。Secret / 接続情報の初期投入はこのモードでしか行えない。書込時は `LogSanitizer` 経由で値そのものをログに出さず、key 名と書換え時刻のみ記録
- **稼働中モード (Runtime)**: アプリ起動後は `app_settings` 系列の閲覧 + 変更キュー登録のみ可能。Secret / 接続情報は表示のみ (key 一覧 + hash)、変更操作は無効化。即時反映は不可で、適用は再起動 or hot-reload を別途トリガ

### 15.3 Operator Console の責務境界

- **既存 ctl のラッパに留める**: `python scripts/ctl.py start` / `python scripts/ctl.py stop` / `python scripts/ctl.py resume-from-safe-stop` / `python scripts/ctl.py run-reconciler` / `python scripts/ctl.py emergency-flat-all` (M22 で確定する 5 コマンド、§11 Cheat Sheet 上 5 行と完全一致) のうち、`emergency-flat-all` を**除く** 4 コマンドのみ Operator Console から実行可能
- **新規 usecase の追加禁止**: Operator Console から新しい運用 action を生やさない。必要が出た場合は ctl 側に先に追加し、それを Operator Console が呼ぶ順序を守る
- **2-factor が必要な ctl はそのまま 2-factor を要求**: Operator Console 側で 2-factor を「省略可」にする迂回禁止
- **`reason` フィールドは Operator Console でも必須**: ctl が要求する `--reason="..."` は UI からも省略不可
- **Learning UI は本節の対象外** (§15.1 「Operational 層 (Learning UI、別系統)」行参照): `enqueue-learning-job` 等の学習系操作は M21 拡張の Streamlit Learning UI で行う。Operator Console の M22 5 コマンド契約とは**別系統**で、本節の「新規 usecase の追加禁止」原則は Operator Console にのみ適用される (Learning UI 側は IP2 §6.9 の learning_jobs テーブル契約に従う)

### 15.4 UI 経由 secret 入力カタログ (Iter3 以降の実装範囲)

| Secret 名 | 入力契機 | sink | 監査記録 |
|---|---|---|---|
| OANDA API key | 起動前モードで初期投入 / rotate | `.env` のみ (DB 書込禁止) | `app_settings_changes` に key 名 + sha256 prefix + 操作者 + UTC time、値本体は記録せず |
| SMTP password | 同上 | `.env` のみ | 同上 |
| Supabase API key | 同上 | `.env` のみ | 同上 |
| その他外部接続 credential | 同上 | `.env` のみ | 同上 |

**禁止**: 上記 secret を `app_settings` テーブル本体や `app_settings_changes.old_value` / `app_settings_changes.new_value` に**平文で書込むこと** (development_rules §10.3.1 と対応、実列名は schema_catalog §2 #42)。SecretProvider 書込 Interface (`rotate` / `set` 等) は Iter2 では未導入のため、UI からは「`.env` 書換 + 再起動誘導」までが上限。

### 15.5 監査ログとの関係

- **Iter2 で必要な監査**: ctl 経由の操作は既存の `app_settings_changes` + `safe_stop.jsonl` + `notifications.jsonl` で十分。UI 専用の audit テーブルは Iter2 では新設しない
- **Phase 8 で追加**: `dashboard_operations_audit` テーブル (**仮称、Phase 8 で正式テーブル名確定**、UI 操作の who / when / which action / which target) は SSO/multi-user とセットで Phase 8 (phase8_roadmap §5.3) で導入。schema_catalog の現 43 表体系には未登録。Iter3 で UI を実装する場合も、それまでは「単独運用者前提」「ctl の既存監査経路で代替」とする

### 15.6 Phase 8 への送り (本章境界の再評価条件)

以下が成立した時点で本章の境界は再評価対象になる:

1. SSO / multi-user 化 (operator / viewer / admin の権限分離、phase8_roadmap §5.3)
2. Streamlit 卒業条件超過 (phase8_roadmap §2.3) → Next.js + FastAPI への UI 刷新
3. SecretProvider 書込 Interface (`rotate` / `set`) の D3 追加 (Iter2 では read-only `get` / `get_hash` / `list_keys` のまま)

これらの 1 つでも成立するまで、UI は **「ctl の上に薄いラッパを被せたもの + `.env` の起動前 sink」** を超えて拡張しない。
