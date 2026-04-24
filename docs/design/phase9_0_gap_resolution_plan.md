# Phase 9.0 — Gap Resolution Plan

**作成日**: 2026-04-24  
**前提ドキュメント**: `docs/design/phase9_0_d3_audit.md`  
**本ドキュメントはコード変更を含まない (docs-only)**。

audit で判明した各 gap を Phase 9.X のどの段階で解消するかを割り付ける。

---

## 優先度 A: Phase 9.1 で解消 (D3 production runner 結線)

### A-1. D3 production runner 未結線 (❌ 最重要)

**gap**: `scripts/run_paper_entry_loop.py` / `run_paper_evaluation.py` / `run_live_loop.py` が `MetaCycleRunner` を呼ばない。I-5/I-6/I-8 が production で実質未充足。

**解消方法**:
1. `BarFeed` Protocol を `domain/price_feed.py` に追加 (bar 粒度の `Quote` 相当, OHLCV)
2. `scripts/run_paper_decision_loop.py` を新規作成 — `MetaCycleRunner.run_one_cycle()` を呼ぶ D3 ランナー
3. `M10` 経路 (`run_paper_entry_loop.py`) は eval/replay 専用として retain (削除しない)

**完了条件**: `run_paper_decision_loop.py --dry-run` が MetaCycleRunner → MetaDeciderService → StrategyRunner を 1 cycle 完走し、`strategy_signals` / `meta_decisions` に行が INSERT される

---

### A-2. MetaDeciderService Score 段の計算式不整合 (⚠)

**gap**: Score = `ev_before_cost × confidence` を使用。Phase 1 I-5 は `EV_after_cost` を意思決定の唯一中心と定める。

**解消方法**:
- `MetaDeciderService._score()` の式を `ev_after_cost × confidence` に修正
- 既存テスト (`test_meta_decider.py`) の期待値を更新

**完了条件**: Score 段が `StrategySignal.ev_after_cost` を参照し、`ev_before_cost` を直接 score に使わない

---

### A-3. MetaCycleRunner の run_id ↔ system_jobs 連携 (⚠)

**gap**: MetaCycleRunner は `run_id` をオプション引数で受け取るが、runner 起動時に `system_jobs` への INSERT が行われない。Phase 1 §5.4.2 の cycle 単位 audit trail が未整備。

**解消方法**:
1. alembic revision で `system_jobs` に `git_sha` / `host` / `pid` / `mode` 列を追加
2. `run_paper_decision_loop.py` 起動時に `system_jobs` へ 1 row INSERT → `system_job_id` を `run_id` として以降の全 row に伝播

**完了条件**: 起動 → 停止の 1 run で `system_jobs` に 1 row が INSERT/UPDATE される

---

### A-4. StrategyRunner 並列化 / timeout 整備 (⚠)

**gap**: 直列実行のため strategy 数 × instrument 数が増えると time budget (per-cycle ≤30s) を超過するリスク。

**解消方法**:
- Phase 9.1 時点では instrument が 1〜3 種程度 → 並列化は Phase 9.2 (多通貨) または Phase 9.4 (TA 追加) 着手時に実施
- Phase 9.1 では SLA 計測コード (logging で per-strategy 経過時間を記録) のみ追加
- Phase 9.4 で asyncio.gather + per-strategy timeout (200ms) を実装

**完了条件 (9.1)**: per-strategy / per-cycle 経過時間がログに記録される  
**完了条件 (9.4)**: 並列実行 + 200ms timeout が実装され、slow strategy が cycle 全体をブロックしない

---

## 優先度 B: Phase 9.2 で解消 (動的全ペア化)

### B-1. OandaInstrumentRegistry 未実装 (❌)

**gap**: `domain/price_feed.py` に Protocol のみ存在。production runner は `--instrument EUR_USD` のように単一ペアで起動。I-8 (動的全ペア) が未充足。

**解消方法**:
- `adapters/oanda/instrument_registry.py` を新規実装 — OANDA API から instrument リストを取得し cache
- `run_paper_decision_loop.py` が `OandaInstrumentRegistry.list_active()` を呼ぶように変更
- CI lint で `G8_INSTRUMENTS = [...]` 等のハードコードを検出

**完了条件**: runner が起動時に OANDA から動的取得した instrument リストで MetaCycleRunner を呼ぶ

---

## 優先度 C: Phase 9.3 で解消 (CSI + correlation → MetaDecider 接続)

### C-1. MetaDeciderService Filter — 通貨強弱 / 相関 未接続 (❌)

**gap**: `correlation_matrix.py` は実装済みだが MetaDecider に未接続。CSI (通貨強弱指数) は未実装。

**解消方法**:
- `services/csi_calculator.py` を新規実装 — G8+ 全通貨の強弱 z-score を計算
- MetaContext に `currency_strength: dict[str, float]` / `correlation_snapshot: dict` フィールドを追加
- MetaDeciderService Filter に Rule F5 (通貨強弱フィルタ) / Rule F6 (相関フィルタ) を追加

**完了条件**: MetaDecision の `filter_snapshot` に CSI / correlation フィルタ適用結果が記録される

---

### C-2. MetaDeciderService Filter — 市場状態 / 時間帯フィルタ未実装 (❌)

**gap**: market_conditions / 時間帯 filter が Phase 1 §4.6 に記載されているが未実装。

**解消方法**:
- Phase 9.3 で CSI 実装と同時に Rule F7 (時間帯フィルタ) を追加
- 市場状態 (trending/ranging) は Phase 9.4 (TA 指標) 実装後に Rule F8 として追加

---

## 優先度 D: Phase 9.4 で解消 (TA 戦略追加)

### D-1. TA 戦略未実装 (❌)

**gap**: `services/strategies/` には MA / ATR / AIStub のみ。RSI / MACD / Bollinger 等の TA 戦略が未実装。

**解消方法**:
- `services/strategies/rsi.py`, `services/strategies/macd.py`, `services/strategies/bollinger.py` を追加
- 各戦略は `StrategyEvaluator` Protocol 準拠 (新規 Protocol 追加なし)

**完了条件**: TA 戦略が MetaCycleRunner の 1 cycle で MA/ATR と並走して評価され `strategy_signals` に記録される

---

### D-2. StrategyRunner 並列化 + timeout (❌ → Phase 9.4 で完了)

再掲: A-4 参照

---

### D-3. MetaDeciderService Filter — ボラティリティフィルタ (❌)

**gap**: ボラティリティ filter が未実装。ATR や Bollinger Width を TA として取得後に接続。

**解消方法**: Phase 9.4 で TA 指標計算後、MetaContext に volatility を追加し Rule F8 として接続

---

## 優先度 E: Phase 9.6 で解消 (ML baseline)

### E-1. AIStrategyStub の置換 (❌)

**gap**: `AIStrategyStub` は固定出力 placeholder。Phase 1 §4.5.3 では LightGBM baseline に置換予定。

**解消方法**:
- Phase 9.5 (Feature/Label pipeline) 後に `services/strategies/lgbm_strategy.py` を実装
- `AIStrategyStub` は削除せず残す (eval/regression 用)

---

## 優先度 F: Phase 9.X-A / 9.X-B で解消

### F-1. CloseReason 拡張 (❌)

**gap**: CloseReason は LEGACY_BARE (SL/TP/EMERGENCY_STOP/MAX_HOLDING_TIME) の 4 種のみ。Phase 1 §3 が追加要求する `reverse_signal` / `ev_decay` / `news_pause` / `manual` / `session_close` が未実装。

**解消方法** (Phase 9.X-A):
- `domain/reason_codes.py` に DOTTED 拡張として CloseReason.{REVERSE_SIGNAL, EV_DECAY, NEWS_PAUSE, MANUAL, SESSION_CLOSE} を追加
- LEGACY_BARE は一切触らない (後方互換維持)
- `run_exit_gate` の close 優先順位ロジックに新 reason を接続

---

### F-2. I-4 / I-8 CI lint (❌)

**gap**: 売買経路からの supabase import を禁止する lint が未整備。固定通貨ペアのハードコードを禁止する lint も未整備。

**解消方法** (Phase 9.X-B):
- `tools/lint/run_custom_checks.py` に 2 ルール追加:
  - Rule: trading-path module からの supabase import を検出 → fail
  - Rule: `G8_INSTRUMENTS = [...]` 等の固定リスト定義を検出 → fail
- `tests/unit/test_no_secondary_db_in_trading_path.py` を追加

---

### F-3. risk_events DB 書き込み (❌)

**gap**: RiskManager がリスク判定を行うが `risk_events` テーブルへの INSERT が未実装。

**解消方法** (Phase 9.X-B または 9.1 の patch):
- `risk_manager.py` から `risk_events` テーブルへの INSERT を追加
- I-6 (全候補記録) の一部として扱う

---

## 解消 Phase サマリ

| Gap | 優先度 | 解消 Phase |
|---|---|---|
| D3 production runner 未結線 | **最重要** | 9.1 |
| Score 段 EV 計算式不整合 | 高 | 9.1 |
| run_id ↔ system_jobs 連携 | 高 | 9.1 |
| StrategyRunner SLA 計測 | 中 | 9.1 |
| StrategyRunner 並列化 + timeout | 中 | 9.4 |
| OandaInstrumentRegistry | 高 | 9.2 |
| CSI + correlation → MetaDecider | 中 | 9.3 |
| 市場状態 / 時間帯フィルタ | 中 | 9.3-9.4 |
| ボラティリティフィルタ | 中 | 9.4 |
| TA 戦略 (RSI/MACD/Bollinger) | 中 | 9.4 |
| AIStrategyStub 置換 | 低 | 9.6 |
| CloseReason 拡張 (5 種) | 中 | 9.X-A |
| I-4 / I-8 CI lint | 中 | 9.X-B |
| outbox writer / worker 結線 | 中 | 9.X-B |
| risk_events DB 書き込み | 低 | 9.X-B or 9.1 patch |
| system_jobs 明示列追加 | 中 | 9.1 |
