# Phase 9.0 — D3 既存実装 Audit

**作成日**: 2026-04-24
**目的**: Phase 9.1 以降の着手前提として、`src/` に存在する D3 スタック実装の Phase 1 要件カバレッジを棚卸しする。  
**本ドキュメントはコード変更を含まない (docs-only)**。

---

## 1. Audit 対象と評価スケール

| 評価 | 意味 |
|---|---|
| ✅ | Phase 1 要件を満たしている |
| ⚠ | 部分実装 — 動作するが要件の一部が欠けている |
| ❌ | 未実装 / Phase 1 要件を満たさない |

---

## 2. Production Runner D3 結線確認 (最重要)

**対象**: `scripts/run_paper_entry_loop.py` / `scripts/run_paper_evaluation.py` / `scripts/run_live_loop.py`

| Runner | MetaCycleRunner 呼び出し | MetaDeciderService 呼び出し | StrategyRunner 呼び出し | 評価 |
|---|---|---|---|---|
| `run_paper_entry_loop.py` | ❌ なし | ❌ なし | ❌ なし | ❌ |
| `run_paper_evaluation.py` | ❌ なし | ❌ なし | ❌ なし | ❌ |
| `run_live_loop.py` | ❌ なし | ❌ なし | ❌ なし | ❌ |

**観察**:
- 3 runner すべてが M9/M10 経路 (`MinimumEntryPolicy` + `EntrySignal` + `Supervisor.run_exit_gate_tick()`) を使用
- D3 経路 (`MetaCycleRunner.run_one_cycle()`) は production で一度も呼ばれていない
- Phase 1 invariants **I-5 (EV center)** / **I-6 (全候補記録)** / **I-8 (動的全ペア)** が production で実質未充足

**解消 Phase**: → **9.1** (D3 production runner 結線: `scripts/run_paper_decision_loop.py` 新規 + `BarFeed` Protocol 追加)

---

## 3. MetaDeciderService 実装 (`services/meta_decider.py`, 336 行)

### 3.1 Filter 段

| Phase 1 §4.6 要求 filter | 実装状況 | 備考 |
|---|---|---|
| EventCalendar 陳腐化 | ✅ | Rule F1: calendar が stale → 全候補 no_trade |
| 経済指標イベント近傍 | ✅ | Rule F3: 通貨 × near_event_minutes |
| PriceAnomalyGuard (フラッシュ) | ✅ | Rule F4: 急変検知 |
| 明示的 no_trade シグナル除外 | ✅ | Rule F2 |
| 市場状態 (trending/ranging) | ❌ | 未実装 (Phase 9.3 CSI/MetaContext 拡張時) |
| ボラティリティ | ❌ | 未実装 (Phase 9.4 TA 指標) |
| Spread フィルタ | ❌ | 未実装 (GateReason.SPREAD_TOO_WIDE は exit gate にあるが filter 段には未接続) |
| 通貨強弱 (CSI) | ❌ | 未実装 (Phase 9.3) |
| 相関フィルタ | ❌ | `correlation_matrix.py` は存在するが MetaDeciderService に接続されていない |
| 時間帯フィルタ | ❌ | 未実装 |

**評価**: ⚠ (EventCalendar / Anomaly のみ実装, 9 フィルタ中 4 のみ)

### 3.2 Score 段

| 要件 | 実装状況 | 備考 |
|---|---|---|
| EV_after_cost によるスコア計算 | ⚠ | `score = ev_before_cost * confidence` — EV_after_cost ではなく ev_before_cost × confidence の乗算式 |
| 戦略別成績による加重 | ❌ | 未実装 (過去成績フィードバックなし) |
| score_contributions 記録 | ✅ | MetaDecision に ranked list として返却 |
| Concentration warning | ✅ | 候補数 == 1 時にフラグ |

**評価**: ⚠ (EV_after_cost でなく EV_before_cost × confidence を使用)

### 3.3 Select 段

| 要件 | 実装状況 |
|---|---|
| 最高スコア候補を採択 | ✅ |
| filter / score / select snapshot 記録 | ✅ |
| MetaDecision DTO 出力 | ✅ |

**評価**: ✅

### 3.4 MetaContext フィールド gap

Phase 1 §4.6 が要求する filter_input のうち未接続:
- `market_conditions` — Phase 9.3 で追加
- `currency_strength` — Phase 9.3 で追加
- `volatility` — Phase 9.4 で追加
- `correlation_matrix_snapshot` — `correlation_matrix.py` が存在するが MetaContext に未接続

---

## 4. MetaCycleRunner 実装 (`services/meta_cycle_runner.py`, 771 行)

| 要件 | 実装状況 | 備考 |
|---|---|---|
| cycle_id 発行 | ✅ | 呼び出し側から受け取り |
| run_id 管理 | ⚠ | MetaCycleRunner はオプション引数として受け取るが、runner 起動時の system_jobs INSERT は未実装 |
| strategy_signals INSERT | ✅ | StrategySignal 全フィールド + enabled/disabled |
| meta_decisions INSERT | ✅ | filter/score/select snapshot + no_trade_reasons |
| no_trade_events INSERT | ✅ | フィルタ除外候補ごと + NO_CANDIDATES |
| secondary_sync_outbox enqueue | ✅ | F-12 sanitize 済み、idempotency キー付き |
| Append-only 契約 | ✅ | INSERT のみ、UPDATE/DELETE なし |
| all candidates logged (I-6) | ✅ | strategy_signals に enabled=False で落ちた候補も記録 |

**評価**: ⚠ (run_id の system_jobs 連携が欠如)

**解消 Phase**: run_id ↔ system_jobs 連携 → **9.1** (D3 runner 結線時に同時実装)

---

## 5. StrategyRunner 実装 (`services/strategy_runner.py`, 310 行)

| 要件 | 実装状況 | 備考 |
|---|---|---|
| 全戦略を評価 | ✅ | instrument × strategy の全 combination を実行 |
| StrategySignal INSERT | ✅ | strategy_signals テーブル |
| secondary_sync_outbox enqueue | ✅ | |
| 並列実行 (asyncio / threading) | ❌ | for ループによる直列実行 |
| per-strategy timeout (≤200ms) | ❌ | timeout 機構なし |
| Phase 1 §4.16 time budget | ❌ | SLA 計測なし |

**評価**: ⚠ (直列実行のため instrument × strategy 数が増えると time budget 超過リスク)

**解消 Phase**: 並列化 + timeout → **9.1** の P4 または **9.4** (TA 戦略追加時に concurrent 実行が必須化)

---

## 6. EVEstimator 実装 (`services/ev_estimator.py`, 73 行)

| 要件 | 実装状況 | 備考 |
|---|---|---|
| EV_after_cost 計算式 | ✅ | `p_win * avg_win - (1-p_win) * avg_loss - cost.total` |
| cost_model との統合 | ✅ | Cost オブジェクト (spread/commission/slippage) 受け取り |
| EV_before_cost | ⚠ | StrategySignal から読み込むのみ (本サービスでは未計算) |
| confidence interval | ⚠ | ±20% crude approximation (M9 v0 — Phase 9.6 ML で改善予定) |

**評価**: ⚠ (MetaDeciderService の Score 段が EV_after_cost でなく EV_before_cost × confidence を使用しているため連携に不整合)

**解消 Phase**: Score 段の式を EV_after_cost ベースに修正 → **9.1** (D3 runner 結線時に同時修正)

---

## 7. RiskManager + PositionSizer

### RiskManager (`services/risk_manager.py`)

| Phase 1 §4.8 要件 | 実装状況 | 備考 |
|---|---|---|
| concurrent positions 上限 | ✅ | C1: max_concurrent_positions |
| 単一通貨偏重制限 | ✅ | C2: max_single_currency_exposure_pct (デフォルト 30%) |
| 方向偏重制限 | ✅ | C3: max_net_directional_exposure_per_currency_pct |
| 総リスク上限 | ✅ | C4: total_risk_correlation_adjusted |
| duplicate_instrument チェック | ✅ | G1 |
| 実行失敗クールオフ | ✅ | G3: recent_execution_failure_cooloff |
| risk_events DB 書き込み | ❌ | 未実装 (M12 future 計画) |

**評価**: ⚠ (risk_events 未記録)

### PositionSizer (`services/position_sizer.py`)

| 要件 | 実装状況 |
|---|---|
| 固定リスク比率式 (risk_pct × balance / sl_pips) | ✅ |
| min_lot 整合 | ✅ |
| InvalidSL / InvalidRiskPct / SizeUnderMin | ✅ |

**評価**: ✅

---

## 8. 既存 Strategy 実装

| Strategy | 実装ファイル | StrategyEvaluator Protocol 準拠 | 評価 |
|---|---|---|---|
| `MAStrategy` (SMA20/SMA50 crossover) | `services/strategies/ma.py` | ✅ | ✅ |
| `ATRStrategy` | `services/strategies/atr.py` | ✅ | ✅ |
| `AIStrategyStub` (固定出力 placeholder) | `services/strategies/ai_stub.py` | ✅ | ⚠ (Phase 9.6 で LightGBM に置換予定) |
| RSI / MACD / Bollinger 等 TA 戦略 | 未実装 | — | ❌ (Phase 9.4 予定) |

---

## 9. Schema Audit

### `system_jobs` (alembic 0009)

| カラム | 存在 | Phase 1 §5.4.2 run_id 要件 |
|---|---|---|
| `system_job_id` (PK, Text/ULID) | ✅ | → `run_id` として再利用可能 |
| `job_type` | ✅ | → `mode` (paper/live) の代替として利用可能 |
| `started_at` | ✅ | ✅ |
| `ended_at` | ✅ | (`stopped_at` 相当) ✅ |
| `input_params` | ✅ | → `git_sha`, `host`, `pid` を JSON で格納可能 |
| `result_summary` | ✅ | |
| `status` | ✅ | FSM: pending/running/success/failed/canceled |
| `run_id` (明示列) | ❌ なし | → `system_job_id` を `run_id` として読み替え |
| `git_sha` (明示列) | ❌ なし | `input_params` JSON で代替 |
| `host` / `pid` (明示列) | ❌ なし | `input_params` JSON で代替 |

**評価**: ⚠  
**解消方針**: Phase 9.1 着手時に alembic revision で `system_jobs` に `git_sha` / `host` / `pid` / `mode` 列を追加。`system_job_id` を `run_id` として全 logged row に伝播。

### `secondary_sync_outbox` (alembic 0013)

| カラム | 存在 | I-11 要件 |
|---|---|---|
| outbox_id, table_name, primary_key, version_no | ✅ | ✅ |
| payload_json (F-12 sanitize 済み) | ✅ | ✅ |
| enqueued_at, acked_at, last_error, attempt_count, next_attempt_at | ✅ | fire-and-forget + retry ✅ |
| run_id / environment / code_version / config_version | ✅ | audit trail ✅ |

**評価**: ✅ (I-11 要件充足)  
**残作業**: outbox_writer 結線 + outbox_worker (drain → Supabase) — Phase 9.X-B

---

## 10. Dashboard Panel データソース Audit

| Panel | データソース | read-only か | 5.5.4-Rule (修正版) 準拠 |
|---|---|---|---|
| 全 11 panel | `dashboard_query_service` 経由で PostgreSQL Engine に `conn.execute(text(...))` | ✅ read-only (SELECT のみ) | ✅ |
| エラー時 fallback | `[]` または `0` 返却 (graceful) | ✅ | ✅ |
| キャッシュ | Streamlit `@st.cache_data(ttl=5)` を各 panel が適用 | ✅ | — |

**評価**: ✅ (5.5.4-Rule 修正版に準拠 — 一次 DB read-only role 直読みは short-term で許容)

---

## 11. 外部サービス結線確認

| サービス | 実装ファイル | MetaDeciderService 接続 | 評価 |
|---|---|---|---|
| `correlation_matrix.py` | 実装済み | ❌ 未接続 | ❌ |
| `event_calendar.py` | 実装済み | ✅ F3 で使用 | ✅ |
| `price_anomaly_guard.py` | 実装済み | ✅ F4 で使用 | ✅ |
| CSI (通貨強弱) | 未実装 | — | ❌ (Phase 9.3) |
| BarFeed Protocol | 未実装 | — | ❌ (Phase 9.1) |
| OandaInstrumentRegistry | 未実装 (Protocol のみ) | — | ❌ (Phase 9.2) |

---

## 12. 総括: Phase 1 要件カバレッジ Matrix

| カテゴリ | 評価 | 主なギャップ | 解消 Phase |
|---|---|---|---|
| D3 production runner 結線 | ❌ | 3 runner すべて MetaCycleRunner 未呼び出し | 9.1 |
| MetaDeciderService Filter 完備 | ⚠ | 4/9 フィルタのみ実装 | 9.3, 9.4 |
| MetaDeciderService Score 計算式 | ⚠ | EV_before_cost × confidence (EV_after_cost ではない) | 9.1 |
| MetaCycleRunner 全候補ログ (I-6) | ✅ | — | — |
| MetaCycleRunner run_id 連携 | ⚠ | system_jobs INSERT 未実装 | 9.1 |
| StrategyRunner 並列化 / timeout | ❌ | 直列実行, SLA 計測なし | 9.1 or 9.4 |
| EVEstimator 計算式 | ✅ | — | — |
| RiskManager 制約 | ⚠ | risk_events DB 書き込みなし | 9.X-B |
| PositionSizer | ✅ | — | — |
| AIStrategyStub 置換 | ❌ | 固定出力 placeholder | 9.6 |
| TA 戦略 (RSI/MACD/Bollinger) | ❌ | 未実装 | 9.4 |
| system_jobs 明示列 | ⚠ | git_sha/host/pid が input_params JSON に要包含 | 9.1 |
| secondary_sync_outbox schema | ✅ | — | — |
| outbox writer / worker 結線 | ❌ | schema のみ、writer/worker 未実装 | 9.X-B |
| dashboard panel データソース | ✅ | — | — |
| correlation_matrix → MetaDecider 接続 | ❌ | 未接続 | 9.3 |
| BarFeed Protocol | ❌ | 未定義 | 9.1 |
| OandaInstrumentRegistry | ❌ | Protocol のみ | 9.2 |
| CloseReason 拡張 (5 種) | ❌ | LEGACY_BARE 4 種のみ | 9.X-A |
| I-4 CI lint | ❌ | 未整備 | 9.X-B |
| I-8 固定ペア禁止 CI lint | ❌ | 未整備 | 9.X-B |

---

## 13. 次ステップ

詳細な gap → phase 割付は `docs/design/phase9_0_gap_resolution_plan.md` を参照。
