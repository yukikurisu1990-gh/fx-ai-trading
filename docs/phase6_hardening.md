# Phase 6 — Hardening (運用成熟化)

## 目的と位置付け

Phase 6 は、Phase 0–5 統合設計 (`docs/design.md`) に対する「実運用前提シニアアーキテクト兼クオンツ」レビューで特定された Critical / High 指摘を**設計段階で閉じる**ためのフェーズである。

原則:
- Phase 0–5 の既存仕様は**削除・簡略化・置換しない**
- Phase 6 は**追記・契約強化・初期値確定**の形で統合する
- Phase 6 項目のうち MVP リリース条件となるものを本書で明示する
- `docs/design.md` には Phase 6 の要約と本書への参照のみ追記し、詳細は本書に集約する

---

## 設計項目

### 6.1 Safe-Stop Persistence Contract (Circular Failure 解消)

`safe_stop` の記録経路を **DB 単一依存から多重化**する。`SafeStopJournal` という append-only のローカルファイル (`logs/safe_stop.jsonl`) を導入し、safe_stop 発火時の書込順序を以下に固定する:

1. **SafeStopJournal** に JSON 一行書込 + `fsync` (DB より先)
2. **トレーディングループ停止** (新規発注受付停止)
3. **Notifier** で外部通知 (Slack / File / Email)
4. **一次DB** `supervisor_events` への書込試行 (Critical tier として)
5. DB 書込失敗時: ローカル journal と通知が既に成立しているため、記録は保全されている

起動時は DB と SafeStopJournal の両方を読み、不整合 (journal に記録あり / DB に記録なし) があれば Reconciler が journal を正本として DB に補完する。`SafeStopJournal` は PostgreSQL とは独立した障害面を持つ。

**不変条件**: Critical tier の書込は DB 単独に依存しない。

**in-flight 発注の扱い (safe_stop 発火時)**:

safe_stop シーケンス実行の瞬間に以下の状態が並行して存在しうる:
- `Broker.place_order()` の HTTP リクエストが OANDA に送信中 (応答待ち)
- Outbox に `ORDER_SUBMIT_REQUEST` が commit 済だが、まだ HTTP 送信未開始
- HTTP 応答受信中 (SUBMITTED / FAILED 確定直前)
- 既存ポジションに対する fill イベントが transaction stream から到着中

これら in-flight リクエストの扱いを以下で固定する:

- **進行中リクエストはキャンセルしない**: 送信中の HTTP コールは中断せず、結果応答を待つ。中断すると OANDA 側と DB 側で状態が不定になる
- **新規発注受付は即時停止**: safe_stop 発火と同時に TradingCore / ExecutionAssist は新規 `trading_signals` の受付 / ExecutionGate 通過 / 発注キューへの投入を停止する
- **応答処理は継続**: すでに送信された place_order の応答受信と `orders.status` の更新 (PENDING → SUBMITTED or FAILED) は通常フローで実施、Outbox `ORDER_SUBMIT_ACK` / `ORDER_SUBMIT_FAIL` の記録も通常通り
- **結果待ちの上限**: `place_order_timeout_seconds` (初期 30 秒) までは応答を待つ。この上限を超過したリクエストは `orders.status=FAILED` に強制遷移し、Reconciler で後日整合
- **Outbox 未送信分**: `ORDER_SUBMIT_REQUEST` が commit されたが HTTP 送信前の entry については、safe_stop 中は OutboxProcessor の dispatch を**停止**する。起動時 Reconciler が pending entry を評価し、OANDA 側に該当 client_order_id がなければ `orders.status=FAILED` に遷移
- **約定・決済の受信は継続**: transaction stream からの fill / close / swap 等のイベント受信と DB 反映は safe_stop 中も継続する (新規発注停止とは独立した責務)
- **ExitPolicy の発火**: 既存ポジションに対する決済 (SL/TP 到達、緊急全決済等) は safe_stop の設定に従う (safe_stop 発火理由によっては全クローズ指示を出す、ExitPolicy 経由)

この契約により、「safe_stop 発火後に実ポジションが OANDA で約定したが DB は知らない」状態の発生を最小化する。最終的な整合保証は Mid-Run Reconciler + 起動時 Reconciler が担う。

### 6.2 Mid-Run Transaction Reconciliation

**再起動時のみ**だった Reconciler を、稼働中も発火する構造に拡張する。`MidRunReconciler` を StreamWatchdog の下位機能として追加する。

発火条件 (いずれか):
- **Stream heartbeat 途絶 60s 超** → 再接続成功後に `get_recent_transactions(since=last_seen_transaction_id)` を呼び取りこぼし補完
- **定期 drift check (15 分毎)** → `get_positions()` + `get_pending_orders()` と一次DB を突合
- **execution_metrics の reject 率が閾値超**で追加発火

Reconcile の差分は `reconciliation_events` に記録する (`trigger_reason` 列で発火源を区別)。補完できないギャップ (OANDA 再生ウィンドウ超過) 検出時は自動 degraded に遷移し、Notifier で警告する。

State Manager のポジション保持は**常に OANDA を truth source** として扱う契約を強化する。DB と OANDA が食い違う場合、DB を更新する (二次DB はその後 Projector 経由で反映)。

**優先度運用 (Rate Limiter / 実行スケジューラでの扱い)**:
- **平常時** の定期 drift check (15 分毎) と軽微な整合作業は **trading 系より低優先度**で実行する。`rate_limit_reconcile_rps = 2` のバケットに従い、売買クリティカルパス (発注・約定反映) を阻害しない
- **stream gap 補完時** (heartbeat 60s 超検知 → 再接続成功 → `get_recent_transactions(since=last_seen_transaction_id)` による取りこぼし補完) のみ、**一時的に高優先度**へ昇格する。売買判断の前提となるポジション状態の早期復元が必要なため
- 昇格は gap 補完処理のスコープに限定し、処理完了後は自動で低優先度に戻す
- この優先度切替は `MidRunReconciler` 内部で管理し、RateLimiter のバケット選択として表現する (trading バケット一時借用 or dedicated high-priority バケット)

### 6.3 EventCalendar Stale Failsafe

`EventCalendar` Interface に以下の契約を必須化:

- `last_updated_at: timestamp` — カレンダー最終更新時刻
- `max_staleness_hours: int` — 許容ステイル時間 (初期 24h)
- `is_stale() -> bool` — 閾値超判定

ステイル時の動作 (**fail-safe + 二重防御**):
- **第一防御**: ステイル検知 → MetaDecider Filter が**全候補を "指標近接扱い" で no_trade** に落とす
- **第二防御 (カレンダー非依存)**: `PriceAnomalyGuard` を追加。直近 5 秒の価格変動が直近 5 分の ATR × `price_anomaly_flash_halt_multiplier` (初期 5 倍) を超えたら、該当ペアの全候補を flash_halt

ステイル状態は `data_quality_events` に記録し、Notifier で通知。ステイル期間中は `dashboard_risk_status` に警告表示。

### 6.4 Client Order ID Restart Resilience (ULID 化)

`client_order_id` 生成方式を **ULID** (Universally Unique Lexicographically Sortable Identifier) に置換する。

新フォーマット: `{ulid}:{instrument}:{strategy_id}` (ULID が主キー、instrument/strategy_id は人可読補助)

- ULID は 48bit 時刻 + 80bit ランダム → 同一ミリ秒内の衝突確率は実質ゼロ
- 時系列ソート可能、cycle_id と互換性を持つ
- 再起動で揮発する内部カウンタに依存しない → 衝突リスクなし

OANDA 側は client_order_id による冪等性をサポートするため、ULID により同一 order の重複送信は broker 側でも弾かれる。既存の cycle_id との紐付けは `orders.cycle_id` を外部キー相当として保持する (Common Keys 体系は不変)。

### 6.5 Initial Numeric Parameters (明文化カタログ)

以下のすべての値を `app_settings` 初期値として仕様に固定する。変更は `config_version` bump 必須 (No-Reset 原則と整合)。

**リスク / 資金管理**
| パラメータ | 初期値 | 範囲 | 備考 |
|---|---|---|---|
| `risk_per_trade_pct` | 1.0 | 0.5–2.0 | 1 トレード最大リスク |
| `max_concurrent_positions` | 5 | 3–10 | 同時保有上限 |
| `max_single_currency_exposure_pct` | 30 | 10–50 | 単一通貨の方向合計 |
| `max_net_directional_exposure_per_currency_pct` | 40 | 20–60 | 単一通貨の net 方向上限 (S3 対策) |
| `correlation_threshold` | 0.7 | 0.5–0.9 | 同方向同時保有禁止の相関閾値 |
| `safe_stop_daily_loss_pct` | 5.0 | 2.0–10.0 | 24h 総損失 |
| `safe_stop_consecutive_loss_count` | 5 | 3–10 | 連続損失回数 |
| `safe_stop_drawdown_warning_pct` | 4.0 | — | 通知開始 (80% 水準) |

**実行 / レイテンシ**
| パラメータ | 初期値 | 備考 |
|---|---|---|
| `cycle_timeout_seconds` | 45 | 1m cycle の 75% |
| `stream_gap_safe_stop_seconds` | 120 | 長期断で safe_stop |
| `stream_mid_run_reconcile_interval_minutes` | 15 | 定期 drift check |
| `event_calendar_max_staleness_hours` | 24 | カレンダーステイル閾値 |
| `price_anomaly_flash_halt_multiplier` | 5 | ATR 倍数 |
| `signal_ttl_seconds` | 15 | Execution TTL、範囲 10–20 (6.15) |
| `defer_timeout_seconds` | 5 | Defer 個別タイムアウト (signal_ttl_seconds 以下) |
| `defer_exhausted_threshold` | 3 | Defer 連発で Reject(DeferExhausted) 格上げ回数 |

**戦略 ON/OFF (6.17)**
| パラメータ | 初期値 | 備考 |
|---|---|---|
| `strategy.AI.enabled` | true | AI 戦略 ON/OFF |
| `strategy.MA.enabled` | true | MA 戦略 ON/OFF |
| `strategy.ATR.enabled` | true | ATR 戦略 ON/OFF |
| `strategy.AI.lifecycle_state` | `stub` | stub / shadow / active の 3 値 (enabled とは直交) |

**Broker 安全契約 (6.1 in-flight / 6.18 Account Type)**
| パラメータ | 初期値 | 備考 |
|---|---|---|
| `expected_account_type` | `demo` | demo / live、起動時 assertion の基準 (6.18) |
| `place_order_timeout_seconds` | 30 | safe_stop 中の in-flight 応答待ち上限 (6.1) |

**相関 / Meta**
| パラメータ | 初期値 | 備考 |
|---|---|---|
| `correlation_short_window_hours` | 1 | 短窓相関 |
| `correlation_long_window_days` | 30 | 長窓相関 |
| `correlation_regime_delta_threshold` | 0.3 | 短長ズレ検知 |
| `correlation_regime_tightening_delta` | 0.1 | **MVP は記録のみ、適用は Phase 7** |
| `meta_score_concentration_warn_pct` | 60 | 単一成分寄与警告 |

**データ / ログ / DB**
| パラメータ | 初期値 | 備考 |
|---|---|---|
| `retention_hot_days` | 7 | Hot テーブル |
| `retention_warm_days` | 90 | Warm パーティション |
| `retention_cold_years` | 2 | Cold アーカイブ |
| `feature_snapshots_max_mb_per_day` | 500 | compact_mode 下での上限 |
| `db_connection_pool_trading_max` | 10 | 売買系接続プール |
| `db_connection_pool_ui_max` | 4 | UI 系接続プール (分離) |
| `db_connection_pool_projector_max` | 4 | Projector 系接続プール |

**Rate Limiter / UI**
| パラメータ | 初期値 | 備考 |
|---|---|---|
| `rate_limit_trading_rps` | 8 | 発注系エンドポイント |
| `rate_limit_reconcile_rps` | 2 | 整合系エンドポイント |
| `rate_limit_market_data_rps` | 4 | データ取得系 |
| `ui_polling_interval_seconds_min` | 5 | UI polling 下限 |
| `ui_cache_ttl_seconds_default` | 5 | Streamlit キャッシュ |
| `secondary_db_error_rate_degrade_pct` | 10 | 1 分窓内 degraded 遷移 |

**起動時検査 (NTP — 二段階)**
| パラメータ | 初期値 | 動作 |
|---|---|---|
| `ntp_skew_warn_ms` | 500 | **500ms 超 → warning (Notifier 通知 + 起動継続)** |
| `ntp_skew_reject_ms` | 5000 | **5s 超 → 起動拒否 (ローカルファイルログ + 通知)** |

### 6.6 Outbox Pattern for Critical Writes

発注経路を Outbox パターンに変更し、「発注成功後に DB 書込失敗」の危険状態を根絶する。

発注シーケンス:
1. `orders` INSERT (status = `PENDING`、client_order_id、cycle_id、intended quantity/price/TP/SL)
2. `outbox_events` INSERT (event_type = `ORDER_SUBMIT_REQUEST`、order_id FK、payload)
3. **COMMIT** (DB 書込成功確認)
4. `Broker.place_order()` 呼び出し (ここで初めて外部 API コール)
5. 応答受信 → `orders.status = SUBMITTED` (or FAILED)、`outbox_events` に `ORDER_SUBMIT_ACK` (or `ORDER_SUBMIT_FAIL`) を INSERT
6. transaction stream から fill → `orders.status = FILLED`、`order_transactions` に追加

失敗時の挙動:
- 1–3 で失敗 → Broker に送信されず副作用なし (safe)
- 4 で失敗 (API 到達不可) → `orders.status` は PENDING のまま → Reconciler が起動時 / 定期で `get_pending_orders()` と突合し、OANDA 側にあれば SUBMITTED、なければ FAILED に遷移
- 5 で失敗 (ack 書込失敗) → outbox_events の PENDING を `OutboxProcessor` が再処理
- 6 の stream 取りこぼし → Mid-Run Reconciler が補完 (6.2)

**Order State Machine**: `PENDING → SUBMITTED → FILLED | CANCELED | FAILED` の有限状態遷移を `orders.status` で管理し、遷移ログも保持する。

### 6.7 Meta Score Contribution Visibility

`meta_decisions` (または `pair_selection_scores`) に以下の列を追加:

- `score_total: numeric` — 合成スコア値
- `score_contributions: jsonb` — 各成分の寄与明細

`score_contributions` のスキーマ:
```
[
  {"name": "ev_after_cost", "raw_value": 0.0012, "weight": 0.4,
   "weighted_value": 0.00048, "contribution_pct": 42},
  {"name": "confidence", "raw_value": 0.75, "weight": 0.2,
   "weighted_value": 0.15, "contribution_pct": 13},
  ...
]
```

**過集中検出**: 単一成分の `contribution_pct > meta_score_concentration_warn_pct` (初期 60) なら `concentration_warning = true` フラグを付け、`anomalies` にも記録。ダッシュボード上で該当判断に警告表示。

Score 関数は線形合成で、重みは `app_settings.meta_score_weights` (JSONB) に保持。重み変更は config_version bump。

### 6.8 Correlation Matrix Window Specification

`CorrelationMatrix` Interface に `CorrelationConfig` を必須化:

```
CorrelationConfig {
  short_window_hours: int       # 初期 1
  long_window_days: int         # 初期 30
  regime_delta_threshold: float # 初期 0.3
  tightening_delta: float       # 初期 0.1
  update_interval_seconds: int  # 初期 60
}
```

**双窓運用**:
- 短窓 (直近 1h): regime change の早期検知用
- 長窓 (直近 30d): 安定した相関の基準

**MVP での扱い (軽微修正反映)**:
- **MVP では**: 双窓の値を計算し `meta_decisions` および `correlation_snapshots` に保存し、regime detection フラグ (`regime_detected: bool`) を記録するのみ
- **MetaDecider Select への regime tightening の強制適用は Phase 7 に後回し**
- MVP 段階では記録された regime フラグを分析材料として使い、閾値や挙動の妥当性を検証する

これにより MVP は「双窓計算 + 記録 + 可視化」に留め、実際の発注挙動を変える動作 (閾値緊縮) は Phase 7 で投入する。データだけ先に貯めておき、後で有効化可能な構造を保つ。

### 6.9 Streamlit / Secondary DB 負荷制御

UI 層の負荷を仕様レベルで強制する。

**Streamlit キャッシュ強制**:
- 全 Dashboard Query Service 呼び出しは `st.cache_data(ttl=N)` 経由を必須 (規約 + code review チェック)
- デフォルト `ttl = 5s`、重クエリ (regret 分析等) は 30s 以上
- `bypass_cache=True` の明示宣言時のみキャッシュ貫通許容

**二次DB 接続分離**:
- UI 用接続プール (`db_connection_pool_ui_max = 4`) を売買系から独立
- Projector 用プール (`db_connection_pool_projector_max = 4`) も独立
- 合計 3 プール (trading / projector / ui) が同一 DB に向かうが、各々の max が守られる

**二次DB エラーレート監視**:
- 内部計測で secondary DB のレスポンスエラーレートを 1 分窓で計測
- `secondary_db_error_rate_degrade_pct = 10%` 超で自動 degraded モード
- degraded 中は UI が「一次 RO View フォールバック」に遷移

**UI Polling Floor**: `ui_polling_interval_seconds_min = 5` を UI 実装側で強制。

**Fallback UX**: Online / Degraded / Offline の 3 状態、UI 側で判定・表示。

### 6.10 Feature Snapshots Compact Mode Default

**MVP から `compact_mode` を既定**とする。

保存する (compact):
- `feature_hash`: 特徴量ベクトル全体の SHA256 先頭 16bytes
- `feature_stats`: JSONB で `{mean, std, min, max, null_count, feature_count}` を特徴量群ごと
- `sampled_features`: 重要度トップ N (初期 20) の生値のみ保存

保存しない (compact 時): 全特徴量の生配列

全量保存の opt-in:
- `feature_snapshot_full_capture = true` でその期間のみ全量保存
- 学習ジョブ前の短期間や、異常検知近辺のみを想定

サイズガード: `feature_snapshots_max_mb_per_day = 500MB` 超で自動 compact 強制 + 警告。

**再現性担保 (Feature Service の決定性契約)**:
- `Feature Service` は **`feature_version` を持つ決定的コンポーネント** として扱う。同一入力 (`market_candles` + `economic_events` + Common Keys) と同一 `feature_version` に対して**バイト等価な出力**を返すことを契約化する
- 以下を禁止する:
  - seed 未固定の乱数使用
  - 現在時刻 (`now()`) を直接特徴量に混ぜる挙動
  - 順序非決定な並列集約 (unordered reduction)
  - 浮動小数の非決定的 reduce 順序
- `feature_version` は全 `feature_snapshots` 行に列として必須付与。Common Keys 体系の拡張として扱い、Phase 3 の共通キー群と並置する
- compact 保存で失われた生配列は、同じ `feature_version` で Feature Service を呼び直すことで後日再生成可能 (`market_candles` + `economic_events` から決定的に再計算)
- `feature_version` が変わる (計算ロジック変更) 場合は:
  - 新旧両方を並走させる期間を設ける (shadow feature と同様の扱い)
  - `strategy_performance` / `meta_strategy_evaluations` / `model_evaluations` 等は `feature_version` を**集計境界**として分離する (Aggregator は feature_version を跨ぐ集計を禁止)
  - これにより「計算ロジックが変わった後の成績」と「変わる前の成績」が混ざらない

### 6.11 AIStrategyStub → Production AI Shadow Migration Protocol

MVP 初期に AIStrategyStub を稼働させた時点から、**shadow 枠を並走させる契約**を用意する。

**Shadow Mode Specification**:
- `AIStrategy` に 3 状態: `stub` / `shadow` / `active`
- `stub`: MVP の固定 confidence 実装
- `shadow`: 本物のモデルが推論を行うが **MetaDecider には渡さず `predictions` にのみ保存**
- `active`: 実運用投入、MetaDecider に採用される

**Shadow 期間の契約**:
- 最短 30 日の shadow 期間を必須
- `model_evaluations` に `shadow=true` フラグで shadow 成績を記録
- Promotion 判定基準 (初期):
  - OOS 成績: 本物 AI が stub を上回る (正の Sharpe、0.5 以上)
  - Calibration: EV 予測と実現の整合度 (Brier score 改善)
  - Drift: shadow 期間内で `drift_events` 発火なし
  - Sample size: 最低 1000 件の predictions
- すべて満たしたら管理画面で `promote_to_active` → `active` 遷移

**Historical Contamination 防止**:
- `strategy_performance` / `meta_strategy_evaluations` は `strategy_version` で集計境界を明示
- stub 期 / shadow 期 / active 期の 3 区分で比較可能
- Aggregator は `strategy_version` 境界を跨ぐ集計を禁止

### 6.12 Reconciler Action Matrix

Reconciler の「安全側補正」の具体を決定表として仕様化する。

| ケース | 検知条件 | 期待アクション | 自動/手動 | 記録先 |
|---|---|---|---|---|
| DB PENDING & OANDA にも存在 | DB.status=PENDING かつ OANDA 側に同 client_order_id | `status=SUBMITTED` に更新 | 自動 | reconciliation_events |
| DB PENDING & OANDA なし (若い) | PENDING 経過 < 5min | そのまま待機 | 自動 | なし |
| DB PENDING & OANDA なし (古い) | PENDING 経過 > 5min | `status=FAILED` に更新、Notifier | 自動 | reconciliation_events + anomalies |
| DB SUBMITTED & OANDA ポジション一致 | 量・方向一致 | そのまま | 自動 | なし |
| DB SUBMITTED & OANDA ポジなし (FILL stream 欠損) | 一致なし、transactions に fill あり | `status=FILLED` + positions 追加 | 自動 | reconciliation_events |
| DB position 保有 & OANDA になし | DB 保有 / OANDA 空 | **自動クローズ禁止**、Notifier + degraded | **手動** | reconciliation_events + supervisor_events |
| DB position なし & OANDA にポジあり | OANDA 保有 / DB 空 | **監視のみ**、Notifier + degraded、exposure に計上するが発注しない | **手動** | reconciliation_events + supervisor_events |
| 数量不一致 (部分約定) | DB.qty ≠ OANDA.qty | OANDA 値で更新、差分を記録 | 自動 | reconciliation_events |
| 通貨ペア不一致 (異常) | client_order_id 一致 / instrument 不一致 | **Critical**: safe_stop 発火 | **手動** | supervisor_events + reconciliation_events |
| Clock skew (500ms–5s) | 起動時 / 定期検査 | 警告 + 起動継続、定期再検 | 自動 | data_quality_events |
| Clock skew 重大 (> 5s) | 起動時検査 | **起動拒否** | 手動 | ローカルファイル (DB 接続前) |

このマトリクスは本書を正本とし、ケース追加は Phase 単位で行う。

### 6.13 Notification Infrastructure

`Notifier` Interface を導入し、Outbox 経由での確実な通知を保証する。

**Notifier 抽象**:
```
Notifier.send(event_type, severity, payload) -> NotifyResult
  severity: critical | warning | info
  event_type: 列挙型
```

**実装 (軽微修正反映)**:
- **`FileNotifier`** — `logs/notifications.jsonl` に fsync、**常時必須**、DB 非依存の最終防波堤
- **`SlackNotifier`** — Webhook 経由、**MVP 必須**
- **`EmailNotifier`** — SMTP、**Iter2 M17 で実装済 (3-path fan-out)**。有効化は SMTP_HOST / SMTP_PORT / SMTP_SENDER / SMTP_USERNAME / SMTP_PASSWORD / SMTP_RECIPIENTS の 6 環境変数全 set で auto-activate / 一部欠落で silently skip (File + Slack で fan-out 継続)

Phase 7 以降で OAuth SSO / 双方向運用を追加。

**通知必須イベント** (MVP から):

| イベント | Severity | 契機 |
|---|---|---|
| `safe_stop.fired` | critical | Supervisor.safe_stop() 発火 |
| `safe_stop.cleared` | info | 手動復帰 |
| `mode.degraded.entered` | warning | 各種 degraded 遷移 |
| `mode.degraded.cleared` | info | 正常復帰 |
| `db.critical_write_failed` | critical | Critical tier 書込失敗 |
| `db.connection_lost_sustained` | critical | 30s 以上接続断 |
| `stream.gap_detected` | warning | 60s gap |
| `stream.gap_sustained` | critical | 120s gap (safe_stop 直前) |
| `drawdown.warning` | warning | 80% safe_stop 閾値到達 |
| `drawdown.stop_threshold` | critical | safe_stop 閾値到達 |
| `oanda.api_persistent_error` | warning | 5 分連続エラー |
| `config.version_changed` | info | config_version 変更 |
| `reconciler.mismatch_manual_required` | critical | 手動対応必要 (Action Matrix) |
| `event_calendar.stale` | warning | 24h 以上更新なし |
| `ntp.skew_warning` | warning | 500ms–5s |
| `ntp.skew_reject` | critical | 5s 超 (起動拒否) |

**通知 Outbox (非 critical 系の既定経路)**:
- 運用系・情報系・警告系の通知は `notification_outbox` テーブル経由で送信 (DB 書込 → 非同期 Notifier dispatch)
- 送信失敗時は指数バックオフで再試行
- `FileNotifier` は常に同期書込成功 (DB 非依存パス)

**safe_stop 系 critical 通知は outbox を経由しない (同期直接送信)**:
- **Critical event 集合 (Iter3 cycle 3 確定 / 7 件)** — `notification_outbox` を**経由せず** sync direct で fan-out するイベント (operations §6.3 と完全一致):
  1. `safe_stop.fired`
  2. `db.critical_write_failed`
  3. `db.connection_lost_sustained`
  4. `stream.gap_sustained`
  5. `drawdown.stop_threshold`
  6. `reconciler.mismatch_manual_required`
  7. `ntp.skew_reject` (※ DB 接続前 / 起動拒否時に発火するため Slack/Email は best-effort、File のみ必須)
- **info 例外**: `safe_stop.cleared` は severity=info だが、SafeStopJournal の連続性を保つため同経路 (sync direct、outbox bypass) で送出する
- これらは `FileNotifier` への fsync + **利用可能な全外部 Notifier (`SlackNotifier` / `EmailNotifier`) への同期直接送信**を行う
- 理由: **DB 障害が safe_stop 発火源そのものでありうる**ため、通知経路が DB 書込 (notification_outbox) に依存していると Circular Failure を再現してしまう。これを構造的に防ぐ
- 同期送信の失敗は各チャネルごとに短いタイムアウト (例: Slack 2 秒) でフェイルオーバし、`FileNotifier` は必ず成功する最終保証となる
- 非 critical / 運用系イベントは従来通り `notification_outbox` 経由 (非同期、DB 書込後 dispatch)

**設定**:
- 通知チャネル有効化は `app_settings.notification_channels` (JSONB) で制御
- 環境別に通知先を変える (local: file のみ、vps/aws: file + slack 必須、email は SMTP_* 6 変数全 set で auto-activate)

### 6.14 追加の運用契約 (Supporting Items)

**NTP Sync 起動検査 (二段階 — 軽微修正反映)**:
- 起動時に `ntp_skew_ms` を測定
- `ntp_skew_warn_ms = 500` 超 → **warning**: Notifier 通知 + 起動継続 + 定期再検
- `ntp_skew_reject_ms = 5000` 超 → **起動拒否**: ローカルファイルログ + 通知、プロセス終了

**Swap Cost の EV 組込**:
- `CostModel` に `swap_rate` を追加、`holding_time × swap_rate` をコストに加算
- `ev_breakdowns` に swap 成分を別列で記録

**Margin 監視**:
- `account_snapshots` に `margin_used` / `margin_available` / `margin_call_trigger_ratio` を追加
- `margin_warning_pct = 50` 以下で警告、`margin_critical_pct = 30` 以下で自動 no_trade + Notifier

**DR / バックアップ契約**:
- 一次DB の日次論理ダンプ (`pg_dump`) + WAL アーカイブ必須
- RPO (Recovery Point Objective): 24h
- RTO (Recovery Time Objective): 2h
- バックアップ先は別ストレージ (ローカル + 外部の 2 系統)

**CI/CD マイグレーションテスト**:
- Alembic up → down → up の往復テスト
- PG と SQLite の両方で schema 作成テスト
- strategy/meta 変更時の shadow backtest を CI で自動実行 (Phase 7 で自動化)

**Emergency Flat CLI**:
- OS レベル CLI (`python scripts/ctl.py emergency-flat-all`) を提供
- 全ポジション即時クローズ + 以降 reject モードに遷移
- Dashboard UI 非依存

### 6.15 Execution TTL (Signal Expiration Contract)

分足で生成された `trading_signals` が秒単位の執行補助で Defer / Retry を繰り返すうちに老朽化し、スプレッドスパイクや急変直後の「過去の EV 予測に基づく発注」を引き起こす危険を構造的に防ぐ。

**TTL 契約**:
- `trading_signals` に `created_at` を必須列として付与 (Common Keys の timestamp とは別の、signal 生成時刻)
- `ExecutionGate.check(intent, realtime_context)` の**最初のチェック**として TTL 判定を実施:
  - `now() - trading_signals.created_at > signal_ttl_seconds` なら即座に `Reject(reason=SignalExpired)`
  - TTL 超過後は Defer 不可 (Defer 復帰時に TTL 超過していれば自動 Reject に遷移)
- TTL は `app_settings.signal_ttl_seconds` (初期 15 秒、範囲 10–20 秒) で制御
- `execution_metrics` に `signal_age_seconds` 列を追加し、ExecutionGate 判定時の経過秒数を全件記録

**Defer の挙動**:
- Defer は "一定時間待って再評価" の仕組みだが、**待機完了時点で TTL 超過していれば自動 Reject(SignalExpired)** に遷移
- Defer の個別タイムアウト (`defer_timeout_seconds`、初期 5 秒) は必ず TTL 以下に設定
- 同一 signal で Defer が連発された場合 (`defer_exhausted_threshold` 回、初期 3 回) は TTL 超過前でも `Reject(DeferExhausted)` に格上げ

**Reject 理由列挙の拡張**:
Phase 6.13 の ExecutionGate Reject 理由列挙に以下を追加:
- `SignalExpired`: TTL 超過
- `DeferExhausted`: Defer 連発閾値超過

**no_trade との責務分離**:
TTL 超過は「発注に至らなかった判断」だが、意思決定レイヤ由来ではなく実行困難由来であるため、`no_trade_events` には記録せず `execution_metrics.reject_reason` に記録する。この責務分離は 6.16 の no_trade taxonomy に整合。

### 6.16 no_trade Taxonomy (意思決定結果としての分類)

`no_trade` は単なる signal 値ではなく、**明示的な意思決定結果**として扱い、発生源ごとに分類可能にする。これにより分析 11 軸の「no_trade 効果分析」「rejection_reason 別分析」が精緻化され、改善ループの診断粒度が上がる。

**no_trade_events テーブルの列追加**:
- `reason_category: text` — 発生源 (大分類)
- `reason_code: text` — 具体コード (小分類)
- `reason_detail: jsonb` — 追加情報 (閾値・実測値・関与パラメータ等)
- `source_component: text` — 発火コンポーネント名 (debug 用)

**Taxonomy 定義**:

| reason_category | reason_code | 発火源 | 備考 |
|---|---|---|---|
| `meta.filter` | `spread_too_wide` | MetaDecider Filter 段 | spread が動的閾値超 |
| `meta.filter` | `session_closed` | MetaDecider Filter 段 | 取引時間外 |
| `meta.filter` | `indicator_imminent` | MetaDecider Filter 段 | 高インパクト指標近接 |
| `meta.filter` | `size_under_min` | MetaDecider Filter 段 | PositionSizer が最小ロット未達 |
| `meta.filter` | `broker_unreachable` | MetaDecider Filter 段 | Broker 接続不良 |
| `meta.score` | `ev_below_threshold` | MetaDecider Score 段 | EV_after_cost 閾値未満 |
| `meta.score` | `confidence_too_low` | MetaDecider Score 段 | confidence_interval 過大 |
| `meta.score` | `strategy_performance_poor` | MetaDecider Score 段 | 戦略の直近成績悪化 |
| `meta.select` | `no_valid_combination` | MetaDecider Select 段 | Risk 制約下で組合せなし |
| `meta.select` | `correlation_conflict` | MetaDecider Select 段 | 相関制約で除外 |
| `risk` | `concurrent_limit` | RiskManager | 同時ポジ数上限 |
| `risk` | `single_currency_exposure` | RiskManager | 単一通貨 exposure 上限 |
| `risk` | `net_directional_exposure` | RiskManager | 単一通貨 net 方向上限 (Phase 6.5 新規) |
| `risk` | `total_risk` | RiskManager | 総リスク上限 |
| `risk` | `correlation_same_direction` | RiskManager | 相関閾値超ペアの同方向禁止 |
| `event_calendar` | `stale` | EventCalendar Stale Failsafe (6.3) | カレンダー古く fail-safe 発動 |
| `price_anomaly` | `flash_halt` | PriceAnomalyGuard (6.3) | ATR 比異常検知 |
| `strategy` | `disabled` | strategy_enabled=false (6.17) | 戦略が OFF |
| `strategy` | `signal_no_trade` | StrategyEvaluator 自身 | 戦略が no_trade を返した (AI 出力等) |
| `supervisor` | `safe_stop_active` | Supervisor | safe_stop 中の新規発注拒否 |
| `supervisor` | `degraded_new_orders_disabled` | Supervisor | degraded 中の新規発注拒否 |

**ExecutionGate Reject との責務分離**:
- **`no_trade_events`**: 発注前の**意思決定レイヤでの却下** (上記 taxonomy すべて)
- **`execution_metrics.reject_reason`**: 発注を試みたが**執行レイヤで却下** (`SpreadTooWide` / `SuddenMove` / `StaleSignal` / `BrokerUnreachable` / `SignalExpired` / `DeferExhausted` 等)

「なぜ取引が発生しなかったか」を意思決定由来 vs 実行困難由来で原因別集計可能にする。

**ダッシュボード反映**:
- `dashboard_meta_strategy_eval` に no_trade reason 分布 (reason_category × reason_code の 2 次元頻度)
- 改善分析ビュー (design Section 5.4 #10) に "no_trade reason 分布" を明示追加
- 時系列で reason_category の分布変化を可視化 (regime change 検出の補助指標として有用)

**Aggregator 対応**:
- `strategy_performance` / `daily_metrics` のロールアップで no_trade 件数を reason_category 別に集計
- `meta_strategy_evaluations` の反実仮想計算で「この no_trade がなければどうだったか」の検討対象を reason_category で絞り込み可能に

### 6.17 戦略単位の ON/OFF 制御 (strategy_enabled)

AI / MA / ATR の各戦略を個別に有効・無効化できる仕組みを導入する。**AI の `stub / shadow / active` (Phase 6.11) とは独立した直交軸**として扱う。

**設計選択**:
- **MVP**: `app_settings` に `strategy.{type}.enabled` 形式のキーで保持
  - `strategy.AI.enabled` (初期 `true`)
  - `strategy.MA.enabled` (初期 `true`)
  - `strategy.ATR.enabled` (初期 `true`)
- **Phase 7+ 拡張点**: 戦略版ごと (strategy_version 単位) の制御が必要になった段階で、`strategy_registry` テーブル (strategy_type / strategy_version / enabled / lifecycle_state / 他) を新設する余地を残す (本 Phase では導入しない)

**2 軸の状態表 (AI の例)**:

| `strategy.AI.enabled` | `strategy.AI.lifecycle_state` | 挙動 |
|---|---|---|
| false | * (任意) | 評価・推論とも行わない (完全 OFF) |
| true | `stub` | 固定 confidence の stub 実装を評価、MetaDecider へ渡す (MVP 既定) |
| true | `shadow` | 本物 AI モデルで推論するが MetaDecider には渡さず `predictions` のみ保存 |
| true | `active` | 本物 AI モデルで推論し MetaDecider に採用候補として渡す |

MA / ATR は lifecycle_state を持たないため、`strategy.MA.enabled` / `strategy.ATR.enabled` のみで制御。

**実装契約**:
- Strategy Engine は cycle 開始時に `app_settings` から有効戦略リストを取得 (毎 cycle ではなくキャッシュ + 無効化イベント subscribe でも可)
- `strategy.{type}.enabled = false` の戦略は並列評価から**除外** (シグナル生成関数自体を呼び出さない)
- 除外された戦略について `strategy_signals` への記録は**行わない** (件数ゼロ)
- **ただし状態ログは残す**: 各 cycle の `meta_decisions` の Filter 段スナップショットに `active_strategies: [AI, MA, ATR]` 形式で**その時点で有効だった戦略リスト**を記録
- 任意ペア × 無効戦略の組合せは `no_trade_events` に `reason_category=strategy` / `reason_code=disabled` で記録 (6.16 taxonomy)

**ダッシュボード反映**:
- 戦略別比較パネル (design Section 5.4 #3) で disabled の戦略は "OFF" バッジ表示、EV / confidence 欄はブランクまたは "—" 表示
- `dashboard_strategy_summary` マートに `enabled: bool` 列を追加、UI に反映
- `dashboard_risk_status` の系統表示に現在 enabled な戦略数を表示

**運用上の注意**:
- disabled 中の戦略を再 enable する時、**過去の無効期間中は `strategy_signals` / `predictions` / `strategy_performance` の行がない**ため、連続成績として扱えない
- `strategy_version` 境界と同様に、enabled/disabled の遷移点も**集計境界**として扱う:
  - Aggregator は enabled 切替点を跨ぐ集計を禁止
  - `strategy_performance` / `meta_strategy_evaluations` はこの境界で期間分割して保存
- enabled 切替は config_version bump 必須 (app_settings 変更の既存仕組み)、変更履歴は `app_settings_changes` (Phase 6 共通機構) で追跡

**2 軸の独立性の帰結**:
- 「AI を shadow で評価したいが結果を一切使わない」= `enabled=true` + `lifecycle_state=shadow`
- 「AI を一時的に全停止」= `enabled=false` (lifecycle_state は関係ない)
- 「AI 本番運用」= `enabled=true` + `lifecycle_state=active`
- この 2 軸分離により、shadow 期間中に性能が悪化しても**即座に enabled=false で停止可能**、促進判定 (Phase 7) 前の安全弁として機能する

### 6.18 Broker Account Type Safety Contract

誤って demo / live を混同した発注を**構造的に防ぐ**。single-shot で資金全損を起こしうる最もクリティカルな人為事故を、設定と起動時検査で封じ込める。

**Account Type の明示化**:
- `Broker` Interface に `account_type` プロパティを必須化: 値は `demo` または `live` のいずれか
- `app_settings.expected_account_type` (初期 `demo`) を**アプリ側の正本**として保持
- 環境別の運用ルール:
  - `local`: **`demo` 固定**、`live` への変更は禁止 (ローカル開発で live 発注を構造的に防止)
  - `vps` / `aws`: `demo` 初期、`live` への切替は手動 SQL のみ (UI / CI/CD からの自動切替は禁止)

**起動時 Assertion (fail-closed)**:
アプリ起動シーケンスで以下を実施し、不一致は**起動拒否**とする:
1. `Broker.account_type` を OANDA 問い合わせ or 設定から取得
2. `app_settings.expected_account_type` と比較
3. 一致: 起動継続、その値を `run_id` と対で `supervisor_events` に記録
4. 不一致: **起動拒否** — ローカルファイルログ + Notifier critical (`account_type.mismatch`) 送信 → プロセス exit
5. アプリはメモリ内に `_startup_verified_type` として記録し、以降の assertion 基準とする

この検査は Phase 6.14 の NTP 起動検査・Phase 6.6 の Outbox pending 処理と並ぶ**起動拒否条件**として扱う。

**発注前 Assertion (毎回必須)**:
- `Broker.place_order()` の実装は**内部で必ず**以下を実行:
  1. `self.account_type == self._startup_verified_type` を assert
  2. 不一致なら例外 `AccountTypeMismatch` を raise
  3. 例外時の挙動: `orders` テーブル記録なし、Notifier critical 発火、`safe_stop(reason=account_type_mismatch_runtime)` 発火
- この assertion は **`OandaBroker` / `PaperBroker` / `MockBroker` の全実装で共通実施**を Interface 契約とする
- Broker 差し替え時も同じ制約が適用されるよう基底クラスまたは契約テストで担保

**記録**:
- `orders` テーブルに **`account_type` 列**を必須追加 (Phase 6 追加列)
- 全 orders 行に発注時の account_type を記録、後日の原因調査で「どの account で発注したか」を即座に特定可能
- `account_snapshots` にも `account_type` を付与 (残高記録のたびに確認可能)
- 起動時の account_type 確認イベントを `supervisor_events` に記録 (`event_type=account_type_verified`)

**live への切替手順 (運用ルール、`docs/operations.md` に反映予定)**:
`live` への切替は**自動化禁止**。以下の手動手順を必須とする:
1. Supervisor から safe_stop + プロセス停止
2. 運用担当者が `app_settings.expected_account_type` を手動 SQL で `live` に変更 (変更履歴は app_settings_changes に記録)
3. アプリ再起動 → 起動時 assertion で live 検出
4. 起動完了と同時に Notifier `info` (`account_type.switched_to_live`) で**管理者に通知**
5. 管理者が Dashboard または CLI で `--confirm-live-trading` フラグを手動で有効化するまで、アプリは `safe_stop` 相当の待機状態を維持 (実発注開始しない)
6. 管理者の手動確認でトレーディングループ開始

**Paper → Live の誤爆防止の 4 重防御** (Stage 番号は本書 §6.18 を canonical とし、operations.md / implementation_contracts.md / development_rules.md は本表を参照):

| Stage | 名称 | レイヤ | 実装 |
|---|---|---|---|
| Stage 1 | local プロファイル固定 | 設定レイヤ | RuntimeProfile=`local` では live 設定不可 |
| Stage 2 | 起動時 assertion | 起動レイヤ | Supervisor 起動 §2.1 Step 9 で `expected_account_type` ⇔ broker 実態突合 |
| Stage 3 | 発注前 assertion | ランタイムレイヤ | `Broker.place_order` の pre-assertion (毎発注ごと) |
| Stage 4 | 手動 confirmation 待ち | 運用レイヤ | `python scripts/ctl.py start --confirm-live-trading` フラグ + Supervisor の待機状態 (LiveConfirmationGate 経由) |

**Note (Stage 名前空間の分離)**: 本表の **4-defense Stages 1-4** は防御層全体の番号。これとは別に、Stage 4 の実装である `LiveConfirmationGate` は内部に独自の **3 段検査 (LiveConfirmationGate Stages 1-3)** を持つ:
- LiveConfirmationGate Stage 1: env var (`OANDA_ACCOUNT_TYPE`) 一致
- LiveConfirmationGate Stage 2: operator flag (`--confirm-live-trading` = `operator_confirmed=True`)
- LiveConfirmationGate Stage 3: `config_version` 非空

両系統の番号は別物のため、参照時は必ず「**4-defense Stage N**」または「**LiveConfirmationGate Stage N**」と明示すること (操作 docs 横断で混同しないため)。

**UI 経由 demo ↔ live 切替も同じ 4 重防御を継続** (operations.md §15.1 / §3.1 / development_rules §10.3.1 と一対): Configuration Console (Iter3 以降) からの `expected_account_type` 変更は**閲覧のみ**を許可し、変更操作は CLI / 手動 SQL に委譲する (UI からの変更チャネルを開かない)。これにより上記 4 防御のうち #1 (`local` 固定) / #4 (`--confirm-live-trading` の手動 confirmation) が UI 都合で迂回されることを構造的に防ぐ。SecretProvider の書込 Interface (`rotate` / `set`) も同じ理由で Iter2 では追加せず、UI 経由 secret 入力 sink を `.env` (起動前モード) に限定する (implementation_contracts.md §2.15)。

### 6.19 `config_version` 導出契約 (C4 解消)

`config_version` は全ログの Common Keys を構成し、**分析の再現性と回帰検出の中核**を担う。したがって「どの設定を入力とし、どうハッシュするか」を曖昧にできない。以下を仕様として固定する。

**基本式**:
```
config_version = SHA256(effective_config_canonical_json)[:16]  # 先頭 16 hex chars
```

**`effective_config_canonical_json` の構成 (含める順序)**:

1. **`app_settings` 全行** (DB 由来)
   - 取得: `SELECT name, value, type, introduced_in_version FROM app_settings ORDER BY name ASC`
   - 全行を配列化、フィールド順は `{name, value, type, introduced_in_version}` 固定

2. **環境変数** (プレフィックス `APP_` / `FX_` のみ)
   - OS 環境変数から `APP_*` / `FX_*` プレフィックスを持つものだけ抽出
   - `key=value` の配列、key で昇順ソート
   - 他プレフィックスは除外 (PATH 等の無関係な値を混ぜない)

3. **`.env` ファイル内容** (存在する場合のみ)
   - ファイル全行を読み込み、コメント行 (`#` で始まる行) と空行を除外
   - 残りを `key=value` パースし、key で昇順ソート
   - `.env` が存在しない (本番) 場合はこの要素は空配列

4. **デフォルト値カタログ** (コード内定数)
   - コード内で定義されるデフォルト値 (app_settings に未登録時のフォールバック) の辞書
   - `{name: default_value}` 配列、name で昇順ソート
   - デフォルトを変えた時点で config_version が変わる (コード改訂の追跡にも使える)

5. **Secret 参照** (Cloud Secret Provider 経由)
   - Secret の**値そのものは含めない** (漏洩リスク回避)
   - `{secret_key: SHA256(secret_value)[:16]}` 形式で参照ハッシュのみ含める
   - secret 値が変わると config_version も変わるが、secret 値は effective_config に残らない
   - secret_key で昇順ソート

**Canonical JSON ルール**:
- キーは**辞書式昇順**
- 値内の空白を維持、構造上の空白 (インデント / 改行) は**すべて除去**
- 文字コードは UTF-8、改行コードは LF 統一
- 浮動小数は `"3.14"` のように文字列化して含める (実装依存の丸め差分を避ける)
- `null` は JSON `null`、欠損と空文字は区別

**計算タイミングと記録**:
- **起動時に 1 回計算** (全コンポーネント初期化前、最初期)
- `run_id` と対で `supervisor_events` に記録 (`event_type=config_version_computed`、`payload={config_version, source_breakdown}`)
- `source_breakdown` には各構成要素のハッシュ (app_settings 部分 / env vars 部分 / .env 部分 / デフォルト / secret 参照) を個別記録 — **どの変更が config_version を動かしたか**を後から特定可能にする
- 全ログ行の Common Keys に `config_version` が載る (Phase 3 既存契約)

**変更検出と通知**:
- 起動時に前回 run の config_version と比較:
  - 一致: 通常起動
  - 不一致: Notifier `info` (`event_type=config.version_changed`、payload に新旧 config_version + source_breakdown の差分) を送信、起動は継続
- この通知により「気付かぬうちに設定が変わっている」事故を防ぐ

**`app_settings` 変更の追跡**:
- `app_settings_changes` テーブル (変更履歴) を別途持ち、app_settings の全更新を `(name, old_value, new_value, changed_by, changed_at, reason)` で記録
- config_version bump の根拠として audit 可能

**環境別の典型値**:
- `local`: app_settings + .env + defaults で構成、env vars は最小
- `vps`: app_settings + env vars + defaults + secret 参照
- `aws`: app_settings + env vars + secret 参照 + defaults (.env なし想定)

環境で構成要素が異なっても、**同じ実効設定なら同じ config_version** になる (正規化により)。

**不変条件**:
- config_version は**決定的** (同一入力 → 同一出力)
- secret 値そのものは effective_config 内にも config_version 内にも現れない
- 非確定的な要素 (時刻 / PID / 乱数) を混ぜない

### 6.20 Schema Catalog Reconciliation and Table Count (C1 解消)

design.md Section 7.1 / 12.1 の「34 テーブル」は Phase 4 時点のスナップショットであり、Phase 6 時点では追加・明示化が発生している。**Phase 6 時点の canonical な表数を本節で確定**し、詳細な物理名カタログは Iteration 0 で作成する `docs/schema_catalog.md` を単一ソースとする。

**Phase 6 時点の DB テーブル総数: 42**

内訳:

**A. Phase 4 baseline: 34 テーブル**
design.md Section 7.1 の 9 グループ (Config/Reference 4 / Market Data 3 / Learning/Models 4 / Decision Pipeline 6 / Execution 4 / Outcome 2 / Safety & Observability 6 / Aggregates 3 / Operations 2 = **34**) をそのまま踏襲。Phase 4 命名を物理、Phase 1/3 旧名は View で保全する方針も不変。

**B. Phase 6 新規追加: 3 テーブル**
| テーブル | 所属グループ | 根拠 |
|---|---|---|
| `outbox_events` | Operations (拡張) | 6.6 Outbox Pattern |
| `notification_outbox` | Operations (拡張) | 6.13 Notifier (非 critical 経路) |
| `correlation_snapshots` | Decision Pipeline (拡張) | 6.8 相関双窓の保存先 |

**C. Phase 1/2 で言及された一級テーブルの明示化: 5 テーブル**
design.md Section 7.1 末尾の「補足: 吸収」で曖昧だった既存テーブルを、Phase 6 で**一級 (first-class) の物理テーブル**として確定する:

| テーブル | 所属グループ | 役割 |
|---|---|---|
| `reconciliation_events` | Safety & Observability (拡張) | 6.2 / 6.12 Reconciler Action Matrix の記録先 |
| `supervisor_events` | Operations (拡張) | 6.1 / 6.18 / 6.19 Supervisor 由来イベント |
| `retry_events` | Safety & Observability (拡張) | Phase 1 / 6.14 全リトライログ |
| `anomalies` | Safety & Observability (拡張) | Phase 2 アプリ一般異常 (data_quality_events / reconciliation_events と並ぶ独立系) |
| `app_settings_changes` | Operations (拡張) | 6.19 app_settings 変更履歴 |

合計: **34 + 3 + 5 = 42 DB テーブル**

**D. DB ではないローカルアーティファクト: 2 ファイル**
| アーティファクト | パス | 役割 |
|---|---|---|
| SafeStopJournal | `logs/safe_stop.jsonl` | 6.1 DB 非依存の safe_stop 記録 |
| NotificationFile | `logs/notifications.jsonl` | 6.13 FileNotifier 常時必須の fallback |

これらは**DB テーブルではなく**、DB 障害時にも書込が成立する独立した永続化チャネル。

**グループ別 Phase 6 後の再集計**:
| グループ | Phase 4 | Phase 6 加算 | Phase 6 後 |
|---|---|---|---|
| A. Config/Reference | 4 | 0 | 4 |
| B. Market Data | 3 | 0 | 3 |
| C. Learning/Models | 4 | 0 | 4 |
| D. Decision Pipeline | 6 | +1 (correlation_snapshots) | 7 |
| E. Execution | 4 | 0 | 4 |
| F. Outcome | 2 | 0 | 2 |
| G. Safety & Observability | 6 | +3 (reconciliation_events, retry_events, anomalies) | 9 |
| H. Aggregates | 3 | 0 | 3 |
| I. Operations | 2 | +4 (outbox_events, notification_outbox, supervisor_events, app_settings_changes) | 6 |
| **合計** | **34** | **+8** | **42** |

**canonical な物理名・列定義の集約先**:
- `docs/schema_catalog.md` を Iteration 0 で作成する
- 本節 (6.20) は**表数と構成の合意**、schema_catalog.md は**列定義・制約・インデックス・外部キー**の単一ソース
- design.md Section 7.1 / 12.1 の「34 テーブル」記述は**Phase 4 スナップショットとして維持**し、「Phase 6 以降の canonical は phase6_hardening.md 6.20 および schema_catalog.md を参照」と注記する

**Alembic 初期 migration スコープ (MVP)**:
MVP リリース時の Alembic 初期 migration は **42 テーブル + Phase 6 列追加群**を含む必要がある。schema_catalog.md を最終ソースとして実装、migration 本体は Iteration 1 で作成。

### 6.21 Retention vs No-Reset Contract (C6 解消)

design.md Section 7.1 「**物理リセットしない (No-Reset)**」と Section 8.6 「**Cold アーカイブで N 日後に移動**」の文面的矛盾を解消する。両者は異なるレイヤの契約であり、互いを否定するものではない。

**定義の明確化**:

1. **No-Reset**:
   - 意味: 本番・準本番の一次DB に対して `TRUNCATE` / `DROP TABLE` / 破壊的バルク削除を行わない
   - 目的: バージョン単位 / 実験単位の**遡及分析**が常に可能な状態を維持する
   - 適用範囲: 本番・準本番環境のみ。開発ローカルは除外

2. **Cold アーカイブ**:
   - 意味: 古いデータを**外部ストレージへコピー**し、**コピー成功と整合検証**の後に一次DB から**DELETE** する 3 段プロセス
   - 目的: 一次DB の肥大化を抑えつつ、データそのものの永続保持を確保
   - 帰結: 一次DB からデータは消えるが、**外部から参照可能**な状態は維持される

**両者は矛盾しない**: No-Reset は「破壊」を禁じる契約であり、Cold アーカイブは「保全付きの外部移管」であって破壊ではない。ただし**アーカイブなしの単純削除は禁止**。

**テーブル分類別 retention ポリシー (MVP 既定)**:

| カテゴリ | 対象テーブル | 保持方針 | Cold アーカイブ |
|---|---|---|---|
| **Reference** | brokers, accounts, instruments, app_settings, app_settings_changes, model_registry | **永続保持、Cold 移動なし** | 対象外 |
| **Execution (法的・監査)** | orders, order_transactions, positions, close_events, trading_signals, account_snapshots | **永続保持、Cold 移動なし** | 対象外 (税務・監査要件) |
| **Decision logs** | strategy_signals, meta_decisions, pair_selection_runs, pair_selection_scores, feature_snapshots, ev_breakdowns, predictions, correlation_snapshots | Hot 7d / Warm 90d / Cold 2y 以降アーカイブ + 削除 | 対象 |
| **Outcome / Execution品質** | execution_metrics | Hot 7d / Warm 90d / Cold 2y 以降アーカイブ + 削除 | 対象 |
| **Observability** | no_trade_events, drift_events, data_quality_events, anomalies, stream_status, retry_events | Hot 7d / Warm 90d / Cold 1y 以降アーカイブ + 削除 (サンプリング可) | 対象 |
| **Market raw** | market_candles, market_ticks_or_events, economic_events | Hot 30d / Warm 1y / Cold 3y 以降アーカイブ + 削除 | 対象 (再取得可能) |
| **Supervisor / Reconciler** | supervisor_events, reconciliation_events | Hot 90d / Warm 2y / Cold 移動なし | **Cold 移動なし、永続** |
| **Aggregates** | strategy_performance, meta_strategy_evaluations, daily_metrics | **永続保持、Cold 移動なし** | 対象外 (体積小・分析頻用) |
| **Operations** | system_jobs, app_runtime_state | system_jobs は Hot 180d / Warm 1y / Cold 移動なし / app_runtime_state は直近 + 履歴 30d | 部分対象 |
| **Outbox 系** | outbox_events, notification_outbox | dispatch 済は Hot 30d / Warm 90d 以降削除 (Cold 不要) | 対象 (非永続保持) |

**Cold アーカイブの 3 段プロセス** (全テーブル共通):

1. **Copy** — 対象行を外部ストレージ (MVP: ローカルファイル `archives/{table}_{yyyymm}.parquet`、Phase 8: S3 等) へエクスポート
2. **Verify** — 行数・チェックサム・サンプル行の整合性検証、失敗時は DELETE へ進まない
3. **Delete** — 一次DB から対象行を DELETE (パーティション単位で `DROP PARTITION` 可)

**No-Reset との整合**:
- 1 / 2 は一次DB への破壊操作なし
- 3 は**検証成功後の論理移管**であり、外部にデータが存続する以上「リセット」に該当しない
- ただし verify 失敗時は絶対に delete しない (データ喪失防止)

**Aggregator データの特殊扱い**:
- `strategy_performance` / `meta_strategy_evaluations` / `daily_metrics` は**永続保持** (No-Reset 完全遵守)。体積が小さく、改善ループの振り返りで頻繁に使うため。

**Outbox 系の特殊扱い**:
- `outbox_events` / `notification_outbox` は **dispatch 完了イベント**で、業務データではない
- 永続保持の必要がなく、Cold アーカイブも不要
- `dispatch_completed_at` が古いものは直接削除で問題なし (retention 90d 程度)
- No-Reset の例外として明示

**External archive access**:
- アーカイブ後のデータは外部から読み取り可能な形式 (Parquet / CSV) で保持
- 必要なら analytics クエリから外部パス経由で一時的に再インポート可能
- 本番 DB への再投入は**原則禁止** (別テーブル or 一時テーブル経由で分析)

**canonical な retention 定義の集約先**:
本節 (6.21) を Phase 6 時点の canonical 契約とし、細則は Iteration 0 で作成する `docs/retention_policy.md` で拡充する。MVP 実装時点では Cold アーカイブジョブは未実装でよい (retention 契約を**宣言だけ**しておき、実 Cold ジョブは Phase 7 以降で稼働)。ただし**「単純 DELETE 禁止」の原則**だけは MVP 時点から守る。

---

## MVP 必須項目 (明示)

以下は**MVP リリース条件**であり、これなしで MVP 完了と認めない。

### 絶対必須 (MVP リリースのブロッカー)

- [ ] **6.1 SafeStopJournal** — ローカル fsync + DB 多重化 + 起動時 journal 整合
- [ ] **6.2 Mid-Run Reconciler** — stream 断再接続時補完 + 15 分毎 drift check
- [ ] **6.3 EventCalendar Stale Failsafe** — `last_updated_at` + `max_staleness_hours` + Fallback すべて no_trade + `PriceAnomalyGuard`
- [ ] **6.4 client_order_id ULID 化** — 冪等性の最終防波堤
- [ ] **6.5 初期数値パラメータ** — 全値を `app_settings` 初期 migration で登録
- [ ] **6.6 Outbox Pattern** — 発注経路の `orders(PENDING) → Broker → SUBMITTED/FAILED` 全段
- [ ] **6.12 Reconciler Action Matrix** — 起動時整合の全ケース
- [ ] **6.13 Notifier** — `FileNotifier` (常時必須) + `SlackNotifier` (MVP 必須) + 通知必須イベント全登録
- [ ] **6.14 NTP 起動検査** — warn 500ms / reject 5s の二段
- [ ] **6.15 Execution TTL** — `signal_ttl_seconds` (初期 15 秒) + Reject(SignalExpired) + Defer 連発 Reject(DeferExhausted)
- [ ] **6.16 no_trade Taxonomy** — `reason_category` / `reason_code` 列追加 + 全発火源の分類コード実装 + ダッシュボード reason 分布表示
- [ ] **6.17 戦略 ON/OFF 制御** — `strategy.{type}.enabled` (MA/ATR/AI) + AI の `lifecycle_state` と独立、Strategy Engine の評価除外 + meta_decisions の active_strategies 記録
- [ ] **6.18 Broker Account Type Safety** — `expected_account_type` 起動時 assertion (不一致で起動拒否) + 発注前 assertion (不一致で safe_stop) + `orders.account_type` 列必須記録 + local プロファイルは demo 固定 + live 切替後の手動 confirmation 待ち
- [ ] **6.1 in-flight 発注 (追加契約)** — safe_stop 発火時の送信中リクエストは中断せず `place_order_timeout_seconds=30` まで応答待ち、Outbox pending は停止、transaction stream 受信は継続
- [ ] **6.19 config_version 導出契約** — canonical JSON 形式 + SHA256 先頭 16 hex chars + `supervisor_events` への起動時記録 + source_breakdown 内訳 + 変更時の Notifier info
- [ ] **6.20 Schema Catalog 確定 (42 DB テーブル + 2 ローカルアーティファクト)** — Phase 4 baseline 34 + Phase 6 新規 3 + 一級明示化 5 の合計 42 テーブルを Alembic 初期 migration で作成。詳細列定義は Iteration 0 の `schema_catalog.md` 成果を参照
- [ ] **6.21 Retention vs No-Reset 契約** — 分類別 retention の**宣言**、Cold アーカイブ 3 段プロセス (Copy → Verify → Delete) の契約、「単純 DELETE 禁止」の原則のみ MVP 時点で強制。実 Cold ジョブは Phase 7 以降

### MVP 強推奨 (外すと短期間で痛い目を見る)

- [ ] **6.7 Meta Score Contribution Visibility** — 改善ループの前提
- [ ] **6.9 Streamlit キャッシュ + 接続分離** — UI が DB を殺す事故の予防
- [ ] **6.10 feature_snapshots compact_mode 既定** — ディスク破綻防止
- [ ] **6.14 DB バックアップ** — 日次論理ダンプ + 外部ストレージ

### MVP は契約のみ (実装は Phase 7 以降可)

- [ ] **6.8 相関双窓** — **MVP は双窓計算 + 保存 + regime_detected 記録のみ**。MetaDecider Select への tightening 強制適用は Phase 7
- [ ] **6.11 AIStrategy `stub/shadow/active`** — MVP は stub のみ、shadow 投入は Phase 7
- [ ] **6.14 CI/CD 自動マイグレーションテスト** — MVP は手動、CI 自動化は Phase 7
- [x] **6.13 EmailNotifier** — Iter2 M17 で実装済 (3-path fan-out)。SMTP_* 6 変数全 set で auto-activate / 一部欠落で skip

---

## 既存設計への差分一覧

Phase 6 は以下 Section に**追記・契約強化・初期値確定**で統合される (削除・簡略化・置換は行わない)。

| 対象 Section (design.md) | 変更内容 | 種別 |
|---|---|---|
| Section 1 System Overview | Notifier / SafeStopJournal / Outbox を Failure Modes に追記 | 追記 |
| Section 2 Design Principles | "Critical tier 書込失敗時の多重化" 原則追加 | 追記 |
| Section 3 Architecture Overview | `MidRunReconciler` / `Notifier` / `OutboxProcessor` / `SafeStopJournal` を cross-cutting 層に追加 (計 14 論理コンポーネント) | コンポーネント追加 |
| Section 4 Data Flow | Outbox 経由発注シーケンス、Mid-Run Reconcile フロー追加 | フロー追加 |
| Section 5.2 Strategy Layer | AIStrategy に `stub/shadow/active` 状態、**戦略単位 `enabled` フラグ (6.17)** と lifecycle_state の 2 軸独立 | 状態追加、制御軸追加 |
| Section 5.3 MetaStrategy | `score_contributions` 列、過集中警告、双窓相関 (MVP 保存のみ)、**no_trade taxonomy (6.16) を全段で付与** | 列・契約追加 |
| Section 6.1 分足判断 | Outbox 経由の `trading_signals → orders(PENDING)` シーケンス契約、`trading_signals.created_at` 必須付与 (6.15 TTL 基準)、**`orders.account_type` 列必須 (6.18)** | シーケンス契約、列追加 |
| Section 6.2 秒監視 | client_order_id ULID 化、MidRunReconciler 連携、ExecutionGate の最初に TTL 判定 (6.15)、Reject 理由列挙に SignalExpired / DeferExhausted 追加、**Broker.place_order は発注前 account_type assertion 必須 (6.18)、safe_stop 中の in-flight 応答待ち最大 30 秒 (6.1)** | ID 方式、連携、TTL 契約、Account 契約 |
| Section 7 Data Layer | `outbox_events` / `notification_outbox` / `correlation_snapshots` / SafeStopJournal (ローカル) 追加、`app_settings` 初期値拡充、双窓相関列、ULID 型、compact_mode 既定、**Phase 6 時点の canonical 表数 42 を 6.20 で確定 (Phase 4 の 34 に加え Phase 6 新規 3 + 一級明示化 5)**、**Retention vs No-Reset 契約を 6.21 で確定 (Cold アーカイブ 3 段プロセス / 分類別保持方針)** | テーブル・列追加、値確定、canonical 表数確定、Retention 契約 |
| Section 8 Logging | SafeStopJournal を Critical tier 多重化書込先として追加、Notifier 通知 outbox の位置付け、**`no_trade_events` に reason_category/code/detail 列追加 (6.16)、`execution_metrics` に `signal_age_seconds` + `reject_reason` 拡張 (6.15)** | 契約強化、列追加 |
| Section 9 Learning | AIStrategy Shadow Migration Protocol、Aggregator の strategy_version 境界跨ぎ集計禁止 | プロトコル追加 |
| Section 10 Risk Management | `max_net_directional_exposure_per_currency_pct`、Margin 監視、双窓相関 regime 連動 (Phase 7)、初期数値確定 | 制約・値追加 |
| Section 11 Failure Handling | Mid-Run Reconcile、EventCalendar stale failsafe、Reconciler Action Matrix、Notifier 連携、SafeStopJournal、Outbox | 全面強化 |
| Section 12 MVP Scope | MVP 必須項目追加 (本書「MVP 必須項目」参照)、**「34 テーブル」記述は Phase 4 snapshot として維持、Phase 6 canonical 42 テーブル + 2 ローカルファイルは 6.20 を参照** | スコープ拡張、表数参照先明示 |
| 付録: 重要制約 | 不変条件 #11 "Critical tier 書込は DB 単独ではなく多重化" #12 "通知は Outbox + 多重チャネル" 追加 | 制約追加 |

---

## Phase 7 以降に後回しにする項目

### Phase 7 (運用自動化)

- **相関 regime tightening の Select 強制適用** (MVP は保存まで)
- **AIStrategy shadow → active Promotion 実運用** (MVP は stub のみ、shadow 投入が Phase 7)
- **CI/CD 自動マイグレーションテスト** (MVP 手動、Phase 7 で自動化)
- **Chaos Engineering (fault injection test) の体系化**
- **Emergency Flat CLI の権限・監査拡張**
- **EmailNotifier 拡張** (Iter2 M17 で SMTP fan-out は実装済。Phase 7 では SES / OAuth 認証 / 配信ステータス追跡 等の運用拡張)

### Phase 8 (観測・運用高度化)

- **Notifier の OAuth / SSO 認証** (MVP は Webhook + file)
- **Slack 双方向運用** (safe_stop 復帰を Slack kick)
- **Dashboard の SSO / マルチユーザ** (MVP は BasicAuth + IP 制限)
- **DR 訓練 (定期 failover リハーサル)**
- **税務エクスポートの GUI 化** (MVP は CLI バッチのみ)

### Phase 9 以降 (スケール期)

- **Drift detection の PSI / KL 実装** (MVP は契約のみ)
- **EVCalibrator (isotonic regression 等)** (MVP は v0 ヒューリスティック)
- **multi_service_mode / container_ready_mode の本番展開**
- **複数ブローカー対応** (MVP は OANDA のみ)
- **champion/challenger A/B テスト基盤** (MVP は shadow のみ)

---

## 本書の更新ポリシー

- Phase 7 以降で Phase 6 項目の詳細を追加する場合は**追記のみ** (既存を削除・簡略化しない)
- `docs/design.md` 本体への本書の内容反映は、原則として**Phase 6 の要約と本書参照のみ**に留める。詳細は本書を単一ソースとする
- Reconciler Action Matrix のケース追加は本書「6.12」を正本として拡張する
