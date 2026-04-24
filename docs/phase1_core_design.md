# Phase 1 — Core Design (コア設計仕様)

> **本書の位置付け**
> 本書はプロジェクト全体の**時間不変のコア設計**を定義する。Phase 6/7/8/9 の各 roadmap が「いつ何を実装するか (lifecycle phase)」を扱うのに対し、本書は「最終的に何を満たしているべきか (architectural invariants)」を扱う。
>
> Phase 1 命名は本書を作成依頼した時点での新規軸 (コア設計を Phase 1 deliverable とする) であり、既存の `phase6_hardening.md` / `phase7_roadmap.md` / `phase8_roadmap.md` / `phase9_roadmap.md` と命名衝突するが、**役割は直交**する: 本書 = 不変仕様 / 既存 phase = 実装順。
>
> **作成プロセス (本書は以下 4 段の出力をそのまま含む)**
> §1. Core Design (整理版) — 依頼仕様の構造化整理
> §2. Reviewer 視点の問題点 — 既存実装と仕様のギャップ
> §3. 改善提案 — 具体的な追加・修正案
> §4. Final Core Design — 統合・修正後の最終仕様
>
> **更新履歴**
> 2026-04-24: 初版。`docs/phase9_roadmap.md` (実装順) を本書 §4 と整合させるよう再編済み。

---

# §1. Core Design (整理版)

依頼仕様を構造化して再記述する。**この段階では既存実装と照合しない**(§2 で行う)。

## 1.1 目的

OANDA API + 機械学習で**全 FX 通貨ペアを監視**し、「通貨ペア × 戦略」の全候補から**期待値 (EV) の高い取引のみ**を選択する短期売買システム。

- 初期資金: ¥300,000
- 運用時間: 24 時間 (営業時間中)
- 目標:
  - リスク調整後リターンの最大化
  - 最大ドローダウン抑制
  - `no_trade` を含む安定運用
  - 改善ループ前提
  - ローカル PC / VPS / AWS で同一動作

## 1.2 システム構成方針

「常時重い処理を行わない」設計。**3 系統に分離**する。

| 系統 | 責務 | 主要時間粒度 |
|---|---|---|
| **売買判断系** (decision) | 戦略評価・メタ判断・発注決定 | 1 分 / 5 分 (bar) |
| **執行補助系** (execution) | spread / 急変 / entry guard / 約定確認 / 異常検知 | 秒以下 (tick) |
| **学習・改善系** (learning) | モデル学習・特徴量バッチ・champion-challenger | バッチ (手動 / cron) |

**禁止事項**:
- 売買判断を秒単位 tick で行わないこと
- 学習を常時実行しないこと
- 二次 DB に依存して売買判断しないこと

## 1.3 通貨ペア管理

- OANDA で取引可能な**全 FX 通貨ペア**を対象
- API から動的取得 (固定リスト禁止)
- **毎サイクル全ペアを評価**

## 1.4 戦略構造

各 instrument に対して以下を**並列評価**:
- AI 戦略 (主戦略候補)
- MA 戦略
- ATR 戦略

各戦略の出力 (StrategyDecision DTO):
- `signal`: `long` / `short` / `no_trade`
- `confidence`: [0, 1]
- `EV_before_cost`
- `EV_after_cost`
- `TP`, `SL`
- `holding_time`

## 1.5 メタ戦略

「どの通貨ペア × どの戦略を採用するか」を決定。

入力:
- 市場状態, ボラティリティ, spread, 通貨強弱, 相関, 時間帯, 指標状態, EV, 戦略別成績

出力 (MetaDecision DTO):
- `selected_instrument`, `selected_strategy`, `selected_signal`, `selected_TP`, `selected_SL`
- `no_trade` (boolean) と理由

**初期はルールベース** (将来 ML 化)。

## 1.6 EV 設計

- `EV_after_cost` を意思決定の中心
- `EV = P(win)·AvgWin − P(loss)·AvgLoss − Cost`
- `Cost = spread + slippage + commission`
- EV が低い候補は `no_trade`
- 勝率より EV を優先

## 1.7 資金管理

- 1 トレード 1〜2% リスク
- 同時ポジション制限
- 通貨偏重制御 (currency exposure aggregation)
- 総リスク制御

## 1.8 決済ロジック

- TP 到達 / SL 到達
- 最大保有時間
- reverse signal (反対方向シグナル)
- EV 低下
- 指標停止前 (event window)
- 緊急停止

## 1.9 DB 設計

- **一次 DB (PostgreSQL)**: 正本。売買はここで完結。詳細ログ保存。
- **二次 DB (Supabase 等)**: 参照専用。集計データのみ。非同期同期。**売買経路は二次 DB に依存しないこと**。

## 1.10 ログ設計

一次 DB に記録:
- 全候補シグナル (採用・却下とも)
- 採否理由
- EV 分解 (P(win), AvgWin, AvgLoss, Cost 内訳)
- メタ戦略判断
- 特徴量 (snapshot)
- 決済理由
- no_trade 評価

## 1.11 学習設計

- 常時実行しない
- 手動 or スケジュールバッチで起動
- モデルバージョン管理 / 実験 ID 管理 / 学習履歴保存

学習 UI (ダッシュボード):
- 学習対象選択, 期間指定, 実行方法 (手動/スケジュール), 状態確認, 履歴

## 1.12 過学習対策

- walk-forward
- OOS データ
- 試行回数制限
- モデル寿命管理

## 1.13 MVP

- OANDA 接続
- 全通貨ペア取得
- 一次 DB
- MA / ATR / AI 戦略 slot
- メタ戦略 (ルール)
- paper mode
- 最低限ログ
- 最小ダッシュボード
- 学習 UI (最小)

---

# §2. Reviewer 視点の問題点

既存実装 (M9 / M10 / Iteration 2 進行中) と本仕様を照合した結果のギャップ。**Phase 1 仕様の多くは既に D3 設計として src/ に scaffolding / 実装が存在**しており、ギャップは「未設計」より「並走 2 系統の収束」が中心。

## 2.1 重大ギャップ (architectural)

### G1. **D3 設計と M10 簡易経路が並走している**
- **既存**: `src/fx_ai_trading/domain/strategy.py` の `StrategyEvaluator` Protocol + `StrategySignal` DTO は、Phase 1 §1.4 の出力と **フィールド完全一致** (signal/confidence/ev_before_cost/ev_after_cost/tp/sl/holding_time_seconds/enabled)。`MAStrategy` / `ATRStrategy` / `AIStrategyStub` も実装済。
- **既存**: `src/fx_ai_trading/domain/meta.py` の `MetaDecider` Protocol + `MetaDecision` DTO も Phase 1 §1.5 と一致 (selected_instrument/strategy_id/signal/tp/sl + no_trade)。
- **既存**: `src/fx_ai_trading/services/meta_cycle_runner.py` (770 行) と `meta_decider.py` (336 行) と `strategy_runner.py` (310 行) は完全実装。
- **問題**: `scripts/run_paper_loop.py` / `run_live_loop.py` / `run_paper_evaluation.py` / `run_paper_entry_loop.py` の**どれも `meta_cycle_runner` を呼んでいない**。M10 で導入した簡易 `EntrySignal.evaluate(quote) -> str | None` + `MinimumEntryPolicy` first-non-None picker を使っている。
- **影響**: D3 設計が test-only 状態。Phase 1 で要求される「AI/MA/ATR 並列 → メタ判断」は domain/services レベルでは存在するが、**production runner には届いていない**。

### G2. **主戦略の時間粒度が tick (Quote) 中心**
- **既存**: `EntrySignal` Protocol は `evaluate(quote: Quote) -> str | None`。1Hz tick ベース。
- **D3 既存**: `FeatureBuilder.build(instrument, tier, ...) -> FeatureSet` は **tier 引数を持つ** (M5 / H1 等)。bar ベース設計。
- **問題**: 簡易経路 (M10 entry signals) は 1m/5m bar を消費していない。Phase 1 §1.2 「主戦略は 1m/5m」を満たさない。
- **影響**: 簡易経路で動かす限り Phase 1 §1.2 違反。D3 経路に収束する必要あり。

### G3. **動的全通貨ペア取得が runner に届いていない**
- **既存**: `PriceFeed.list_active_instruments()` Protocol は domain にあり (`domain/price_feed.py:118`)。
- **問題**: production runner は `--instrument EUR_USD` 単一指定。OANDA から動的取得して全ペア iterate するパスが**runner レベルで存在しない**。
- **影響**: Phase 1 §1.3 「毎サイクル全ペア評価」未達。

## 2.2 中程度ギャップ (interface / contract)

### G4. **EntrySignal Protocol と StrategyEvaluator Protocol の二重化**
- 同一概念が 2 つの Protocol で表現されている。
  - `EntrySignal.evaluate(quote: Quote) -> str | None` (M10 簡易)
  - `StrategyEvaluator.evaluate(instrument, features, context) -> StrategySignal` (D3)
- どちらが production の正と扱うか未決定。

### G5. **二次 DB 売買非依存の明示制約がない**
- **既存**: M23 (Iteration 2) で Supabase projector を計画中だが、「売買経路は一次 DB のみ」の**lint / CI チェックは未設置**。
- **問題**: 将来「便利だから二次 DB を select」のコードが侵入するリスク。Phase 1 §1.9 違反の予防が必要。

### G6. **decision_log の "全候補" 範囲が暗黙**
- **既存**: `meta_decisions` / `strategy_signals` / `no_trade_events` / `feature_snapshots` テーブルは設計されている (D3)。
- **問題**: M10 簡易経路は **却下した signal を記録しない** (no_trade_events 書き込みなし)。Phase 1 §1.10 「全候補シグナル」を満たさない。

### G7. **決済理由の網羅性**
- **既存**: `CloseReason.{SL, TP, EMERGENCY_STOP, MAX_HOLDING_TIME}` は frozen で 4 種のみ。
- **不足**: Phase 1 §1.8 が要求する `reverse_signal` / `ev_decay` / `news_pause` (event window 接近) が close reason 列挙にない。
- **既存**: `MetaReason.NEAR_EVENT` は no_trade 側で存在 — close 側へ展開する必要あり。

### G8. **no_trade reason の網羅性 (run-time)**
- **既存**: `MetaReason.{EV_BELOW_THRESHOLD, CONFIDENCE_BELOW_THRESHOLD, NO_CANDIDATES, NO_SCORED_CANDIDATES, CALENDAR_STALE, SIGNAL_NO_TRADE, NEAR_EVENT, PRICE_ANOMALY}` あり。
- **不足明示**: warmup, spread_too_wide (`GateReason.SPREAD_TOO_WIDE` は別系統), max_positions (`RiskReason.MAX_OPEN_POSITIONS` は別系統), currency_concentration (`RiskReason.SINGLE_CURRENCY_EXPOSURE` は別系統)。
- **問題**: 散在しているが体系的 catalog がない。Phase 1 §1.8 の 1 場所参照を満たす設計書が必要。

### G9. **time-budget SLA が未定義**
- 1m bar cadence で「全ペア × 全戦略」評価には何秒以内で完了する必要があるか未規定。
- 全 OANDA FX ペア (~70+) × 3 strategies = ~210 evaluations / minute。並列度・タイムアウト設計の根拠が必要。

## 2.3 軽微ギャップ (operational)

### G10. **ローカル PC 互換の操作可能定義がない**
- 「ローカル PC で動く」の意味 (CPU only / disk size / RAM / network 制約) が未明示。
- 学習バッチ (LightGBM with G8 6 ヶ月) はメモリ 4GB で OK か等、判定基準が必要。

### G11. **24 時間運用の週末扱い**
- FX 市場は週末クローズ。「24 時間」の文言と整合する週末動作 (trading 系停止 / 学習系継続 / dashboard 継続) を明示する必要。

### G12. **資金 ¥300,000 の用途別配分**
- 1 トレード 1-2% = ¥3,000-6,000 リスク。1 ロットに対する pip 単価 (e.g., USD/JPY 0.1 ロット = ¥100/pip) との関係が未明示。最小ロット制約と齟齬がないかチェック必要。

### G13. **学習 UI の権限**
- 学習トリガを誰が引けるか (operator / admin) が未定義。Phase 8 ロードマップで SSO / 権限分離は将来扱いだが、MVP 時点でも「一人運用 + read-only viewer」の差は要る。

### G14. **モデル lifecycle の運用基準**
- Phase 1 §1.12 「モデル寿命管理」は要件のみ。具体: 何日無更新で警告 / 何日で auto-retire / champion 比較で何日 underperform で challenger に置換、等は未定。

### G15. **既存 D3 scaffolding の実装完成度の不明性**
- `meta_cycle_runner.py` 770 行 / `meta_decider.py` 336 行は実装済だが、Phase 1 仕様の全要件 (相関判定 / 通貨強弱 / 時間帯フィルタ等) を**現状でカバーしているか棚卸しされていない**。

---

# §3. 改善提案

§2 の各ギャップに対する具体的な提案。実装は別途 phase 化する (本書は設計のみ)。

## 3.1 G1, G2, G4 への対応 — D3 経路への収束

**提案**: 「production runner は D3 経路 (StrategyEvaluator/MetaDecider/FeatureBuilder/run_meta_cycle) を唯一の正とする」を Phase 1 invariant として明記。M10 簡易経路 (`EntrySignal` + `MinimumEntryPolicy`) は **eval pipeline の検証専用**として retain (削除はしない / production 出口は閉じる)。

具体的サブ提案:
- 新規 production runner `scripts/run_paper_decision_loop.py` を Phase 9.1 で追加 — `meta_cycle_runner.run_meta_cycle` を bar cadence で叩く
- 既存 `run_paper_entry_loop.py` / `run_paper_evaluation.py` は **M10 簡易経路を維持** (regression / 単純 backtest の検証用)
- `EntrySignal` Protocol は廃止せず、「**特徴量が trivially Quote 1 個に閉じる軽量 signal**」のための小型 Protocol として位置付け

## 3.2 G3 への対応 — 動的全ペア取得

**提案**: `OandaInstrumentRegistry` 新設 (Phase 9.2 範囲) — `PriceFeed.list_active_instruments` を呼び、各サイクル開始時に instrument set を refresh。固定リスト禁止を CI テストで強制 (lint: `scripts/` 配下に `--instrument EUR_USD,USD_JPY` のようなハードコード instrument list は production runner では禁止 / eval-replay-only に限定)。

## 3.3 G5 への対応 — 二次 DB 売買非依存の lint

**提案**: 既存 `tools/lint/run_custom_checks.py` に新ルール追加 — production code path (`src/fx_ai_trading/services/{exit_gate_runner, execution_gate_runner, order_service, order_lifecycle, position_service, run_paper_loop, run_live_loop}.py` 等) からの `from fx_ai_trading.adapters.persistence.supabase` 系 import を禁止。CI gate にする。

## 3.4 G6 への対応 — 全候補ログの完備

**提案**: D3 経路 (`run_meta_cycle`) は既に candidate を `strategy_signals` に書き、却下を `no_trade_events` に書く設計。よって**G3.1 の D3 収束で自動解決**。M10 簡易経路への適用は不要 (eval-only にするため)。

ただし `decision_log` 仕様書を本書 Appendix に追加: どのテーブルが何を記録するか 1 枚マップ。

## 3.5 G7 への対応 — 決済理由 enum 拡張

**提案**: `CloseReason` に新規 dotted 値を追加 (LEGACY_BARE は frozen のため):
- `close.reverse_signal`
- `close.ev_decay`
- `close.news_pause` (NEAR_EVENT を close 側で再利用 or 新規)
- `close.manual` (operator 操作)

reason_codes.py の DOTTED に追加し、`run_exit_gate` の発火条件に新規ブランチを足す。

## 3.6 G8 への対応 — no_trade reason catalog

**提案**: `domain/no_trade_catalog.md` (もしくは reason_codes.py の docstring 拡張) — 「全 no_trade reason の意味と発生サイト」一覧。catalog としての参照単一点を持つ。MetaReason / RiskReason / GateReason / TimeoutReason の cross-reference。

## 3.7 G9 への対応 — time budget SLA

**提案**: 売買判断系の時間予算を以下に固定:
- **bar cadence**: 1m = 60s
- **per-cycle budget**: 30s (50% margin)
- **per-instrument budget**: 30s / N (N = 動的 instrument 数)
- **per-strategy timeout**: 200ms (StrategyEvaluator は pure functional のため CPU だけ。超過は warning + skip)
- **feature build budget**: 5s / cycle (DB IO 含む)
- **meta decide budget**: 1s / cycle

70 ペア × 3 戦略 = 210 evaluations × 200ms = 42s — 単純直列では over。**N=8 並列 (asyncio gather)** で 5.3s。設計上 OK。

## 3.8 G10 への対応 — ローカル PC profile

**提案**: 「**Tier-A**: 売買判断系 + 執行補助系 (常時 24h)」「**Tier-B**: 学習・改善系 (バッチ)」の 2 プロファイル。Tier-A は CPU 2c / RAM 4GB / Disk 20GB / network 必須。Tier-B は単発バッチ (LightGBM 学習) で RAM 8GB 程度。Tier-A と Tier-B は**同一マシンでもプロセス分離**。pytest-mark で `@pytest.mark.cpu_only` 追加し GPU 依存を絶対に持ち込まない。

## 3.9 G11 への対応 — 週末動作

**提案**: 売買判断系は OANDA `instrument.tradeable` フラグを毎サイクル確認。tradeable=false ならその instrument を skip + サイクル全体で 1 件もないなら supervisor を pause 状態に遷移 (既存 SafeStop FSM を流用)。週末に学習バッチを cron で走らせるのは可。

## 3.10 G12 への対応 — 資金配分の最低ロット整合

**提案**: `position_sizer.py` (既存) に「最低ロット未達なら no_trade (`risk.size_under_min` 既存)」のパスがある — Phase 1 invariant として「初期 ¥300,000 + 1-2% リスク + OANDA 最低ロット制約」を満たす instrument 集合を runtime に検出。満たさない instrument は cycle 内で skip 理由 `risk.size_under_min` で記録。

## 3.11 G13 への対応 — 学習 UI 権限

**提案**: MVP 時点では `app_settings.learning_ui_actor` (single string) を導入。Phase 8 で SSO / multi-role に拡張。MVP 中は「ログイン済 = operator 相当 / 未ログイン = viewer」の 2 値で十分。

## 3.12 G14 への対応 — モデル lifecycle

**提案**: `model_metadata.yaml` を model_store の各エントリに必須化:
- `trained_at`, `train_window`, `feature_version`
- `oos_metrics` (sharpe, hit_rate, max_dd)
- `deployment_status`: `pending` / `champion` / `challenger` / `retired`
- `retire_after`: 90 日無 promotion で自動 `retired`
- `replace_threshold`: champion 比較で `oos_sharpe - champion_sharpe > 0.2` で auto-replace 候補 (Phase 9.8)

## 3.13 G15 への対応 — D3 scaffolding 実装完成度の棚卸し

**提案**: Phase 9.0 (新設) として「D3 既存実装の完成度 audit」を最初に実施。`meta_cycle_runner.py` 770 行 / `meta_decider.py` 336 行 / `strategy_runner.py` 310 行 / `feature_service.py` 150 行 が Phase 1 の各要件をどこまで満たしているか matrix 化 (Phase 9.1 着手前の前提条件)。

## 3.14 追加: Strategy slot の登録メカニズム

Phase 1 §1.4 「並列評価」を runtime で実現するには、戦略を**カタログから動的にロード**するメカニズムが要る (現在は AIStrategyStub / MAStrategy / ATRStrategy が hard-coded 候補)。

**提案**: `services/strategies/__init__.py` に `STRATEGY_REGISTRY: dict[str, StrategyEvaluator]` を持たせ、`app_settings.active_strategies` (list[str]) で切替。新戦略追加は registry 行 1 行 + app_settings 更新だけで済む。

---

# §4. Final Core Design (修正後)

§1 仕様 + §3 改善提案を統合した最終仕様。**本セクションが本プロジェクトの不変コア仕様**として正となる。

## 4.1 第一原理 (Invariants)

> 以下は実装言語・モジュール構造に依らず**永続的に守られる原則**。違反 PR は CI で reject すべき性質。

| # | 原則 | 強制方法 |
|---|---|---|
| **I-1** | 売買判断は **1m/5m bar 粒度**で行う (秒単位 tick で行わない) | アーキテクチャ: 売買 runner は `BarFeed` を入力し `QuoteFeed` は entry/exit guard の補助のみ |
| **I-2** | 執行補助系 (tick layer) の許可動作は spread / 急変 / entry guard / 約定確認 / 異常検知の **5 種に限定** | コードレビューポリシー + 命名規約 (`*_guard.py`) |
| **I-3** | 学習 (model training) は**常時実行禁止**。トリガは UI / cron / 手動のみ | プロセス分離: 学習プロセスは supervisor 配下に置かない |
| **I-4** | 売買経路は **一次 DB (PostgreSQL) のみ**を参照する。二次 DB (Supabase) を read してはならない | CI lint: production code path の `from fx_ai_trading.adapters.persistence.supabase` import 禁止 |
| **I-5** | `EV_after_cost` を**意思決定の唯一の中心指標**とする (勝率優先禁止) | MetaDecider 実装制約 + 単体テスト |
| **I-6** | 全戦略候補 (採用・却下とも) は一次 DB に**必ず記録**される (audit trail) | `strategy_signals` 表 + `no_trade_events` 表に書く責務を MetaCycleRunner に閉じる |
| **I-7** | 戦略 / モデル / 特徴量はすべて**deterministic** (同入力 → 同出力) | `feature_hash` / `strategy_version` / `model_version` の永続化 + 再生テスト |
| **I-8** | 通貨ペア集合は **OANDA API から動的取得**する (固定リスト禁止) | `OandaInstrumentRegistry` を介す + lint で `--instrument <hardcoded>` 禁止 |
| **I-9** | プロセスは **Tier-A (24h) / Tier-B (batch)** に分離。同一マシンでも別プロセス | systemd unit / Procfile / docker-compose の分離 |
| **I-10** | 全コードは **CPU only / Linux + Windows 両対応**で動く | CI matrix: Linux + Windows / GPU 依存の import 禁止 |

## 4.2 3 層アーキテクチャ

```
┌─────────────────────────────────────────────────────────────────┐
│  Tier-B: 学習・改善系 (Batch, on-demand)                          │
│  - LightGBM training, walk-forward CV                           │
│  - feature store rebuild                                         │
│  - champion-challenger evaluation (run_promotion_gate)           │
│  起動: UI / cron / 手動                                          │
│  プロセス: 売買 runner と独立                                       │
└─────────────────────────────────────────────────────────────────┘
                          ↑ (model_store / feature_store)
                          │
┌─────────────────────────────────────────────────────────────────┐
│  Tier-A: 売買判断系 (Decision, 1m/5m cadence)                    │
│  - run_meta_cycle: BarFeed → FeatureBuilder → StrategyRunner    │
│                    → MetaDecider → MetaDecision                  │
│  - 全 OANDA 通貨ペア iterate                                       │
│  - AI / MA / ATR 並列評価                                          │
│  - StrategyDecision → MetaDecision → 一次DB                        │
└─────────────────────────────────────────────────────────────────┘
                          ↓ (ExecutionIntent)
┌─────────────────────────────────────────────────────────────────┐
│  Tier-A: 執行補助系 (Execution, sub-second cadence)               │
│  - QuoteFeed: 直近 quote 取得                                      │
│  - SpreadGuard: spread 閾値                                        │
│  - PriceAnomalyGuard: 急変検知                                     │
│  - EntryGuard: stale_quote / news_window / max_positions          │
│  - OrderService: 約定確認                                          │
│  - run_exit_gate: TP/SL/max_hold/reverse/ev_decay/news_pause/em   │
└─────────────────────────────────────────────────────────────────┘
```

**重要**: Tier-A 内の 2 サブ系統 (Decision / Execution) は同一プロセス内で動くが、**時間粒度が異なる**。Decision は 1m/5m cadence、Execution は run_exit_gate cadence (現状 supervisor.attach_exit_gate で外部駆動)。

## 4.3 主要 DTO (既存の D3 設計を正とする)

すべて `src/fx_ai_trading/domain/` 配下に既存。本書はこれを正と認定する。

### 4.3.1 `StrategySignal` (`domain/strategy.py`)
```python
@dataclass(frozen=True)
class StrategySignal:
    strategy_id: str
    strategy_type: str            # 'ma_crossover' | 'atr' | 'ai_lgbm' | ...
    strategy_version: str
    signal: str                   # 'long' | 'short' | 'no_trade'
    confidence: float             # [0, 1]
    ev_before_cost: float
    ev_after_cost: float
    tp: float                     # price units (absolute distance)
    sl: float
    holding_time_seconds: int
    enabled: bool
```

### 4.3.2 `MetaDecision` (`domain/meta.py`)
```python
@dataclass(frozen=True)
class MetaDecision:
    meta_decision_id: UUID
    cycle_id: UUID
    no_trade: bool
    active_strategies: tuple[str, ...]
    regime_detected: bool
    filter_snapshot: dict
    score_snapshot: dict
    select_snapshot: dict
    score_contributions: tuple[dict, ...]
    concentration_warning: bool
    no_trade_reasons: tuple[NoTradeReason, ...] = ()
    selected_instrument: str | None = None
    selected_strategy_id: str | None = None
    selected_signal: str | None = None    # 'long' | 'short'
    selected_tp: float | None = None
    selected_sl: float | None = None
```

### 4.3.3 `FeatureSet` (`domain/feature.py`)
```python
@dataclass(frozen=True)
class FeatureSet:
    feature_version: str
    feature_hash: str             # SHA256 short, deterministic
    feature_stats: dict           # {'sma_20': ..., 'sma_50': ..., 'atr_14': ..., ...}
    sampled_features: dict
    computed_at: datetime
    full_features: dict | None    # None when compact_mode
```

### 4.3.4 `Quote` (`domain/price_feed.py`) — Tier-A Execution 専用
既存通り。`tier=null` (price-only)。Decision には流さない。

### 4.3.5 (新規予定) `BarFeed` Protocol — Decision 入力源
```python
class BarFeed(Protocol):
    """Yield closed bars in event-time order, ascending."""
    def get_bar(self, instrument: str, tier: str) -> Candle | None: ...
    # tier: 'M1' | 'M5' | ... ; None = no new closed bar yet
```

`Candle` (既存 `domain/price_feed.py`) を消費。実装は `OandaCandleFeed` (live polling) と `CandleReplayBarFeed` (PR #174 ベースの履歴 replay)。

## 4.4 通貨ペア管理

**`OandaInstrumentRegistry`** (新規予定):
- `refresh()`: OANDA `accounts/{id}/instruments` を呼び `set[Instrument]` を更新
- `tradeable_now()`: 現在 tradeable な subset
- 起動時 + 各サイクル開始時に refresh
- 失敗時は前回値を**そのまま使い続ける** (silent stale 防止のため warning ログ + 連続失敗 N 回で SafeStop)

**禁止事項** (CI lint):
- production runner script で `--instrument <COMMA_SEPARATED>` ハードコード禁止 (eval-replay 用 script は OK)
- `INSTRUMENTS = ['EUR_USD', ...]` 形式の constant 禁止 (in production code path)

## 4.5 戦略 slot

### 4.5.1 既存実装 (D3)
- `MAStrategy` (`services/strategies/ma.py`) — 完全実装
- `ATRStrategy` (`services/strategies/atr.py`) — 完全実装 (要 audit)
- `AIStrategyStub` (`services/strategies/ai_stub.py`) — 固定出力 stub

### 4.5.2 拡張方針
- `STRATEGY_REGISTRY: dict[str, StrategyEvaluator]` を `services/strategies/__init__.py` に新設
- `app_settings.active_strategies: list[str]` で起動時に有効化
- 新戦略追加 = registry 1 行 + app_settings 1 行
- 各戦略は **pure functional** (DB / clock / random 不可); state は features 経由のみ

### 4.5.3 AI 戦略の本実装 (Phase 9.6)
- `AIStrategyStub` を `MLDirectionStrategy(model_path)` で置換
- `model_path` は `model_store/<strategy_id>/<model_version>/` 配下を指す
- 推論 latency 上限 = 200ms / call (per-strategy timeout)
- model 未配置時は `enabled=False` で fallthrough (no error)

## 4.6 メタ戦略 (`MetaDecider`)

### 4.6.1 既存実装
`src/fx_ai_trading/services/meta_decider.py` (336 行) に rule-based MetaDeciderService 実装あり。Filter → Score → Select の 3 段。

### 4.6.2 Phase 1 が要求する filter input (整合性確認対象)
- ✅ 市場状態 (regime_detected フィールドあり)
- ✅ EV (`ev_after_cost` を score に使用)
- ✅ 戦略別成績 (`MetaReason.EV_BELOW_THRESHOLD` 経路あり)
- ✅ spread (`GateReason.SPREAD_TOO_WIDE` で別系統 gate)
- ✅ ボラティリティ (ATR feature 経由)
- ✅ 指標状態 (`event_calendar.py` + `MetaReason.NEAR_EVENT`)
- ✅ 相関 (`correlation_matrix.py` 既存)
- ⚠ 通貨強弱 — **既存実装に明示的に存在しない可能性** → Phase 9.3 で `CurrencyStrengthIndex` 追加して filter 入力に組込
- ✅ 時間帯 — 既存 event_calendar の time-window 機構を流用

### 4.6.3 出力
`MetaDecision` (4.3.2)。`no_trade=True` 時は `selected_*` 全部 None + `no_trade_reasons` に列挙 (既存契約)。

### 4.6.4 拡張順序
1. **MVP**: rule-based MetaDeciderService 既存実装そのまま
2. **Phase 9.3**: 通貨強弱 filter 追加
3. **Phase 9.7**: EV-weighted picker + regime gate (rule から ML 補助型へ)

## 4.7 EV / Cost

### 4.7.1 計算式
```
EV_after_cost = P(win) · AvgWin − P(loss) · AvgLoss − Cost
Cost = spread + slippage + commission
```

### 4.7.2 実装
- `services/ev_estimator.py` (73 行) — EVEstimator 実装あり (中身要 audit)
- `services/cost_model.py` — Cost 既存実装あり
- 各 StrategyEvaluator は `ev_before_cost` を返す → EVEstimator が `ev_after_cost` を埋める responsibility

### 4.7.3 Decision 規則
- `EV_after_cost < threshold` → `no_trade` with `MetaReason.EV_BELOW_THRESHOLD`
- threshold は `app_settings.ev_threshold` (instrument or strategy 別に override 可)

## 4.8 資金管理

### 4.8.1 既存実装
- `services/risk_manager.py`, `services/position_sizer.py` — 実装あり (要 audit)

### 4.8.2 必須機構
- **per-trade**: position_sizer が `risk_pct ∈ [0.01, 0.02]` から units 計算
- **same-instrument**: `RiskReason.DUPLICATE_INSTRUMENT` で重複 open 拒否
- **同時ポジション数**: `RiskReason.MAX_OPEN_POSITIONS`
- **通貨偏重**: `RiskReason.SINGLE_CURRENCY_EXPOSURE` — base/quote で集計 (e.g., long EUR/USD + long EUR/JPY = 2x EUR)
- **ネット方向**: `RiskReason.NET_DIRECTIONAL_EXPOSURE`
- **総リスク**: `RiskReason.TOTAL_RISK` — 全 open 玉の SL までの合計 risk が account equity の N% 超で拒否

### 4.8.3 ¥300,000 / 最低ロット制約
- OANDA 最小 trade size を超えられない instrument は cycle 内で skip + `RiskReason.SIZE_UNDER_MIN`
- 起動時に「実質取引可能 instrument 集合」を log に記録 (audit)

## 4.9 決済ロジック (`run_exit_gate`)

### 4.9.1 既存実装
- `run_exit_gate` (M9 H+M シリーズ完了) — 唯一の exit 経路
- close reasons: `sl`, `tp`, `emergency_stop`, `max_holding_time` (LEGACY_BARE)

### 4.9.2 拡張 (本書で新規追加)
新規 dotted close reason を `reason_codes.py` の `CloseReason` に追加 (frozen LEGACY_BARE と並立、新値は dotted):
- `close.reverse_signal` — 反対方向 signal が同一 instrument に立った
- `close.ev_decay` — open 中の EV_after_cost が threshold 下回った
- `close.news_pause` — event window 接近 (event_calendar 由来)
- `close.manual` — operator 操作 (既存 emergency_stop と分離)
- `close.session_close` — 週末 close 等の市場停止

`run_exit_gate` 内に各 reason の発火条件を実装する (Phase 9.X で別途)。

### 4.9.3 close 優先順位
複数同時発火時は priority order:
1. `emergency_stop` (operator 起動)
2. `session_close` (市場停止)
3. `sl` / `tp`
4. `news_pause`
5. `max_holding_time`
6. `reverse_signal`
7. `ev_decay`

`ExitDecision.reasons` は全部記録、`primary_reason_code` は priority 順最上位。

## 4.10 no_trade reason catalog (本書 §3.6 提案)

`reason_codes.py` の docstring を拡張するか、`docs/no_trade_catalog.md` を新設して以下を記述:

| reason_code | namespace | 発生サイト | 意味 |
|---|---|---|---|
| `MetaReason.EV_BELOW_THRESHOLD` | UPPERCASE | meta_decider.score | EV_after_cost < threshold |
| `MetaReason.CONFIDENCE_BELOW_THRESHOLD` | UPPERCASE | meta_decider.filter | confidence < threshold |
| `MetaReason.NO_CANDIDATES` | UPPERCASE | meta_decider.filter | 全戦略 enabled=False |
| `MetaReason.NO_SCORED_CANDIDATES` | UPPERCASE | meta_decider.score | 全候補が EV<threshold |
| `MetaReason.CALENDAR_STALE` | UPPERCASE | meta_cycle | event_calendar 更新失敗 |
| `MetaReason.SIGNAL_NO_TRADE` | UPPERCASE | meta_decider.filter | 全戦略 signal='no_trade' |
| `MetaReason.NEAR_EVENT` | UPPERCASE | meta_decider.filter | event window 内 |
| `MetaReason.PRICE_ANOMALY` | UPPERCASE | meta_decider.filter | price_anomaly_guard 発火 |
| `RiskReason.CONCURRENT_LIMIT` | dotted | risk_manager | 同時 N 超過 |
| `RiskReason.SINGLE_CURRENCY_EXPOSURE` | dotted | risk_manager | 通貨偏重 |
| `RiskReason.NET_DIRECTIONAL_EXPOSURE` | dotted | risk_manager | ネット方向偏重 |
| `RiskReason.TOTAL_RISK` | dotted | risk_manager | 総リスク超 |
| `RiskReason.DUPLICATE_INSTRUMENT` | dotted | risk_manager | 重複 open 試行 |
| `RiskReason.MAX_OPEN_POSITIONS` | dotted | risk_manager | open 最大 |
| `RiskReason.RECENT_EXECUTION_FAILURE_COOLOFF` | dotted | risk_manager | 直近失敗 cooloff |
| `RiskReason.INVALID_SL` / `INVALID_RISK_PCT` | dotted | risk_manager | 入力 invalid |
| `RiskReason.SIZE_UNDER_MIN` | dotted | risk_manager | 最低ロット未達 |
| `GateReason.SPREAD_TOO_WIDE` | CamelCase | execution_gate | spread 閾値超 |
| `GateReason.SIGNAL_EXPIRED` | CamelCase | execution_gate | TTL 超過 |
| `GateReason.DEFER_EXHAUSTED` | CamelCase | execution_gate | defer 連続失敗 |
| `GateReason.BROKER_UNREACHABLE` | CamelCase | execution_gate | broker 接続不可 |
| `TimeoutReason.TTL_EXPIRED` | bare | run_execution_gate | TTL 超 |

不足: warmup (decision_log にだけ記録、no_trade_events には書かない設計とする)。

## 4.11 ログ・観測 (decision_log spec)

> **用語注意**: 本書および Phase 9 roadmap に登場する「`decision_log`」は **論理名 (logical view name)** であり、単一の物理テーブル名ではない。実体は alembic 0005 group_d_decision_pipeline で定義された下記 3 表 (+ 関連表) を `cycle_id` で join した federation である:
> - `meta_decisions` (1 row / cycle, 採否最終結果)
> - `strategy_signals` (N rows / cycle, 全戦略候補 enabled/disabled とも)
> - `feature_snapshots` (1 row / (cycle, instrument), feature_hash + sampled_features)
>
> 「全候補ログ」「採否理由」を参照する場合は上記 3 表の join を指す。新規物理テーブル `decision_log` は作らない。

| テーブル | 内容 | 書き手 |
|---|---|---|
| `feature_snapshots` | 1 row per (cycle, instrument) — feature_hash + sampled_features | feature_service |
| `strategy_signals` | 1 row per (cycle, instrument, strategy) — StrategySignal 全フィールド | strategy_runner |
| `meta_decisions` | 1 row per cycle — MetaDecision 全フィールド + filter/score/select snapshot | meta_decider |
| `no_trade_events` | 1 row per (cycle, instrument, reason) — 却下理由 | meta_cycle_runner |
| `risk_events` | 1 row per risk-blocked attempt | risk_manager |
| `orders` | 既存 | order_service |
| `positions` | 既存 | position_service |
| `close_events` | 既存 + 新 close reasons | run_exit_gate |
| `pnl_realized` | 既存 (close_events に列として持つ) | run_exit_gate |
| `model_runs` (新規予定 Phase 9.6) | 1 row per training run | learning_ops |
| `promotion_decisions` (新規予定 Phase 9.8) | 1 row per challenger 評価 | promotion_gate |

**「全候補ログ」の保証**: `meta_cycle_runner` は filter で落ちた candidate も `strategy_signals.enabled=False` or `no_trade_events` のいずれかに必ず書く。test 化 (`test_no_signal_silently_dropped`) で担保。

## 4.12 DB 境界

| 種別 | 役割 | 売買経路依存 |
|---|---|---|
| 一次 PostgreSQL | 正本 / 売買 / 詳細ログ | **必須** |
| 二次 Supabase | dashboard / 集計 / 外部参照 | **禁止** (I-4) |

二次 DB への projection は `services/projection_service.py` (既存) が**一次→二次の片方向**で行う。逆方向は CI lint で禁止。

## 4.13 学習バッチと UI

### 4.13.1 学習トリガ
- 手動: `scripts/train_ml_baseline.py --strategy <id> --window 6m`
- スケジュール: `cron` で日次 / 週次 (例: 毎週土曜 02:00 UTC)
- UI: dashboard から enqueue (Phase 9.5/9.6 で実装)

### 4.13.2 model_store 構造
```
model_store/
  <strategy_id>/
    <model_version>/
      model.pkl           # joblib dump
      metadata.yaml       # 4.13.3 参照
      feature_list.json
      train_metrics.json
```

### 4.13.3 metadata.yaml 必須フィールド
- `trained_at`, `train_window` (start/end), `feature_version`
- `oos_metrics`: `{sharpe, hit_rate, max_dd, n_trades}`
- `deployment_status`: `pending` / `champion` / `challenger` / `retired`
- `retire_after`: ISO timestamp; 経過で auto-retire (warning log)
- `replace_threshold`: dict — promotion gate の比較式

### 4.13.4 学習 UI (MVP)
- 学習対象選択: `STRATEGY_REGISTRY` から enabled なもの
- 期間指定: from / to (default 直近 6 ヶ月)
- 実行方法: 手動即時 / cron 登録
- 状態確認: in-progress / queued / completed のリスト
- 履歴: model_runs テーブルから直近 50 件

## 4.14 過学習対策

| 機構 | 実装ポイント |
|---|---|
| Walk-forward CV | `services/ml/training.py` (Phase 9.6 新規) |
| OOS データ | train_window と eval_window の時系列切り分け (CI で重複検査) |
| 試行回数制限 | `app_settings.ml_max_trials_per_day = 10` (default) |
| モデル寿命管理 | `metadata.yaml` の `retire_after` (default 90 日) |
| Feature drift 検知 | Phase 9.6+ — 学習時 feature 分布 vs production の KL divergence |

## 4.15 ローカル運用要件

### 4.15.1 Tier-A プロファイル (24h 稼働)
- CPU: 2 core min
- RAM: 4 GB min (実消費 ~1.5 GB)
- Disk: 20 GB (DB + log; retention に依存)
- Network: 必須 (OANDA REST + streaming)
- OS: Linux (Ubuntu 22.04+) / Windows 11 両対応
- GPU: 不要

### 4.15.2 Tier-B プロファイル (Batch on-demand)
- CPU: 4 core 推奨
- RAM: 8 GB 推奨 (LightGBM with G8 6 ヶ月)
- Disk: +10 GB (model_store + feature_store)
- GPU: 不要 (将来 Phase 9.9 で任意)

### 4.15.3 プロセス分離
- Tier-A は supervisor 配下 (systemd / Procfile / docker-compose)
- Tier-B は独立スクリプト or cron job (supervisor 配下に置かない — I-3)
- 同一マシンでも別プロセス

## 4.16 時間予算 SLA

| layer | budget | 根拠 |
|---|---|---|
| bar cadence | 60s (1m bar) | 主戦略 |
| per-cycle (全 instrument 全 strategy) | ≤ 30s | 50% margin |
| feature build | ≤ 5s / cycle | DB IO 含む |
| meta decide | ≤ 1s / cycle | pure functional |
| per-strategy timeout | ≤ 200ms | 戦略別 enforcement; 超過は skip + warning |
| ML inference | ≤ 200ms | per-strategy budget の上限 |
| run_exit_gate cadence | 既存 (1Hz 想定) | M9 既設 |
| OANDA API call timeout | 5s | 既存 RetryPolicy |

並列度: per-instrument は asyncio.gather で N=8 並列を default。

## 4.17 既存実装との対応 matrix

| Phase 1 要件 | 既存 src/ | gap |
|---|---|---|
| 1.4 戦略 DTO | `domain/strategy.py` `StrategySignal` | ✅ 完備 |
| 1.5 メタ DTO | `domain/meta.py` `MetaDecision` | ✅ 完備 |
| 1.4 MA / ATR / AI slot | `services/strategies/ma.py, atr.py, ai_stub.py` | ✅ MA/ATR 実装、AI は stub |
| 1.5 メタ runner | `services/meta_decider.py` (336L) + `meta_cycle_runner.py` (770L) | ⚠ 実装あり、production runner 未結線 |
| 1.6 EV | `services/ev_estimator.py` (73L) | ⚠ 中身要 audit |
| 1.6 Cost | `services/cost_model.py` | ✅ |
| 1.7 risk | `services/risk_manager.py` + `position_sizer.py` | ⚠ 中身要 audit |
| 1.8 close reasons | `domain/reason_codes.py` `CloseReason` | ⚠ 4 種のみ; reverse/ev_decay/news_pause 不足 |
| 1.8 run_exit_gate | M9 H+M 完了 | ✅ |
| 1.9 一次 DB | PostgreSQL alembic 既設 | ✅ |
| 1.9 二次 DB | M23 (Iteration 2) で計画 | ⚠ 未実装 + I-4 lint なし |
| 1.10 全候補ログ | `strategy_signals` + `no_trade_events` schema | ⚠ schema あり、production runner 未結線 |
| 1.10 feature_snapshots | schema あり | ⚠ FeatureBuilder 未 audit |
| 1.11 学習 UI | M21 (Iteration 2) で計画 | ⚠ 未実装 |
| 1.11 model 管理 | `services/learning_ops.py` 既存 | ⚠ 中身要 audit |
| 1.12 walk-forward 等 | Phase 9.5/9.6 で計画 | ⚠ 未実装 |
| 1.13 paper mode | `scripts/run_paper_loop.py` 既存 | ⚠ M10 簡易経路、D3 未結線 |
| 1.13 ダッシュボード | M19+ 完了済み | ✅ |
| 1.3 全ペア動的 | `PriceFeed.list_active_instruments` Protocol | ⚠ Protocol のみ、registry 未実装 |
| 1.2 1m/5m bar | `Candle` DTO + tier 引数 | ⚠ DTO あり、`BarFeed` Protocol 未定義 |

## 4.18 MVP 完了判定

以下を全て満たした時点で「MVP 完了 = Phase 1 コア設計の最初の実装が動作している」と認定:

1. ✅ OANDA 接続: live demo runner 動作 (`run_live_loop.py` 既達)
2. ✅ 全通貨ペア取得: `OandaInstrumentRegistry.refresh()` が動的取得
3. ✅ 一次 DB: PostgreSQL に全テーブル alembic apply 済 (既達)
4. ✅ MA/ATR/AI 戦略 slot: D3 経路で 3 strategy が cycle 1 回で並列評価される
5. ✅ メタ戦略 (rule): `MetaDeciderService` が 3 candidate から `MetaDecision` を 1 つ返す
6. ✅ paper mode: `scripts/run_paper_decision_loop.py` (新規) が 1m cadence で実走
7. ✅ 最低限ログ: `feature_snapshots`, `strategy_signals`, `meta_decisions`, `no_trade_events`, `orders`, `positions`, `close_events` が 1 cycle 走らせて全部書かれる
8. ✅ 最小ダッシュボード: `meta_decisions` panel + `close_events` panel が表示
9. ✅ 学習 UI 最小: model_runs リスト表示 (実行は Phase 9.6 で別途)

## 4.19 Phase 9 roadmap への影響

`docs/phase9_roadmap.md` (前回作成) を本書 §4 と整合させるため、以下を更新する (本書の Final 確定後に適用):

- **Phase 9.0 (新設)**: D3 既存実装 audit (G15)
  - `meta_decider.py`, `meta_cycle_runner.py`, `strategy_runner.py`, `feature_service.py`, `ev_estimator.py`, `risk_manager.py`, `position_sizer.py` の完成度棚卸し
  - 各々の Phase 1 要件カバレッジを matrix 化
- **Phase 9.1 修正**: 「Signal layer 整備」→「**D3 production runner 整備**」
  - 新規 `scripts/run_paper_decision_loop.py` (D3 経路の bar cadence runner)
  - `BarFeed` Protocol 新規 (本書 4.3.5)
  - M10 `EntrySignal` は eval-only として retain
- **Phase 9.2 修正**: 「多通貨データ層」→「**動的全ペア化**」
  - `OandaInstrumentRegistry` 新規 (本書 4.4)
  - production runner からの instrument hardcode 禁止 lint
- **Phase 9.3 拡張**: 「CSI signal」→ MetaDecider の filter 入力に通貨強弱を組込 (本書 4.6.4)
- **Phase 9.4 拡張**: TA Signal は **既存の `services/strategies/`** に追加 (separate package を作らない)
- **Phase 9.6 修正**: ML baseline は `AIStrategyStub` を `MLDirectionStrategy` で置換 (D3 Protocol 維持)
- **Phase 9.7 拡張**: meta combiner は既存 `MetaDeciderService` の Score 段を拡張する形 (新規 Policy class を作らない)
- **Phase 9.X 追加 (新設)**: close reason 拡張 (本書 4.9.2) — `reverse_signal` / `ev_decay` / `news_pause` / `manual` / `session_close`
- **Phase 9.X 追加 (新設)**: I-4 lint (二次 DB import 禁止) を `tools/lint/run_custom_checks.py` に追加

`docs/phase9_roadmap.md` 側で本書を参照する preamble を追加し、本書を「**コア設計の正**」として明示する。

---

# §5. Phase 0 / 2 / 3 / 4 / 5 補完仕様 (2026-04-24 統合)

> **本セクションの位置付け**
> ユーザ依頼の Phase 0 (環境) / Phase 2 (バックエンド) / Phase 3 (ログ) / Phase 4 (DB) / Phase 5 (UI) を本書 §4 に統合した。**既に §4 でカバー済の項目は §4.X への cross-reference のみ**を残し、不足分のみを本セクションで追補する。
>
> ユーザの「Phase 0/2/3/4/5」と既存プロジェクトの lifecycle phase (Phase 6/7/8/9) は**直交軸**: 前者 = コア設計の章番号、後者 = 実装順。混同しない。

## 5.0 Phase 0 — 前提・環境設計

### 5.0.1 既存カバレッジ
- DB 二層 (一次 PostgreSQL / 二次 Supabase): §4.12, §1.9
- 売買経路は一次 DB のみ: **I-4** + Phase 9.X-B (CI lint)
- ローカル PC profile: §4.15.1

### 5.0.2 補完: 環境プロファイル (VPS / AWS)

| 項目 | ローカル PC | VPS | AWS |
|---|---|---|---|
| Tier-A (24h) 配置 | ホスト / docker | systemd or docker-compose | EC2 (t3.small+) or ECS Fargate |
| Tier-B (batch) 配置 | 同マシン別プロセス | 同 VPS or 別 VPS | EC2 spot or Batch / SageMaker |
| 一次 DB | localhost:5432 | 同 VPS or managed PG | RDS (db.t3.micro+) |
| 二次 DB | local Supabase or skip | Supabase managed | Supabase managed (推奨) |
| 想定スペック (Tier-A) | 2c / 4GB | 1c / 2GB min | t3.small (2c / 2GB) |
| OANDA 接続 | OK (家庭回線で 24h) | OK | OK |
| 推奨用途 | 開発 / smoke | 本番運用 (個人) | スケール時 / 冗長化 |

**移植性 invariant**: アプリコードは環境差を持たず、設定 (`.env`, `app_settings`) のみで切替できること。**OS 依存 (PowerShell vs bash) を import 時に持たないこと** (G-0/G-1 で SIGBREAK / SIGTERM 両対応済)。

### 5.0.3 補完: 二次 DB 障害分離 (新 invariant 候補)

> **I-11 (新設)**: **二次 DB 障害は売買を停止させない**。projection 失敗は warning ログ + retry queue に積み、Tier-A trading 系は影響を受けないこと。

実装契機:
- `services/projection_service.py` (既存) の失敗時に raise しない (warn + queue)
- `OutboxProcessor` (M9 系列で既存) パターンを二次 DB sink 側に拡張
- 二次 DB 接続不能を「fatal」と扱う code path を CI lint で禁止 (Phase 9.X-B の対象範囲を拡張)

---

## 5.2 Phase 2 — バックエンド設計

### 5.2.1 既存カバレッジ
- OANDA API 接続: M9 (`OandaQuoteFeed`) + M-3d + `services/cost_model.py`
- 非同期処理: `asyncio.gather` per-instrument (§4.16)
- 状態管理: `services/state_manager.py` 既存
- 実行モード (paper/live): `scripts/run_paper_loop.py` / `run_live_loop.py` (G-0/G-1 で SafeStop 完備)
- 注文・約定・ポジション管理: `services/order_service.py` / `order_lifecycle.py` / `position_service.py` (M9 H+M で完成)
- 主判断は分足: **I-1** (§4.1)
- 秒監視は補助のみ: **I-2** (§4.1)
- 売買処理は一次 DB 依存: **I-4** (§4.1)

### 5.2.2 補完: 再起動復元 (Restart Recovery)

現状の `state_manager.py` は in-memory state を保持する。**プロセス再起動後の復元契約**を明示する:

> **5.2.2-Rule**: `state_manager` は起動時に **一次 DB の現在 state からのみ** rebuild する。in-memory cache / file snapshot は restart に跨いでは信用しない (一次 DB が唯一の正)。

復元対象:
- `positions` (open のみ) → `state_manager.open_positions`
- `orders` (PENDING / SUBMITTED 中) → reconciler 経路で broker 状態と突合 (既存 `MidRunReconciler` / Iteration 2 M15)
- 学習中 model_runs → 二次起動で重複学習しないよう `model_runs.status='in_progress'` を起動時に確認 + 30 分超は `failed` に降格

未復元で良いもの:
- `quote_feed` cache (起動後 N tick warmup で再構築)
- `signal` 内部 deque (M10 `EntrySignal` 系の deque は warmup から再開; D3 `StrategyEvaluator` は features 経由で stateless)

### 5.2.3 補完: paper / live モード切替 contract

| 切替対象 | paper | live demo | live real |
|---|---|---|---|
| broker | `PaperBroker` | `OandaBroker(account_type="demo")` | `OandaBroker(account_type="live")` |
| quote_feed | `ReplayQuoteFeed` / `OandaQuoteFeed` | `OandaQuoteFeed` | `OandaQuoteFeed` |
| account_id | 任意 (paper-*) | OANDA demo account_id | OANDA live account_id |
| 実銭損益 | なし | なし | あり |
| safe_stop | 有効 | 有効 | **必須** + 起動時 prompt |

**6.18 invariant 既存**: `OandaBroker._verify_account_type_or_raise` で account_type と実 account の整合を起動時に強制。Phase 1 ではこれを再確認 + live real への昇格は手動承認のみとする (Phase 9.8 も同方針)。

---

## 5.3 Phase 3 — ログ設計

### 5.3.1 既存カバレッジ
- 改善ループ前提: `services/learning_ops.py` + `meta_cycle_runner.py` で全 cycle ログ化 (§4.11)
- 一次 DB 詳細ログ: §4.11 表 (`feature_snapshots` / `strategy_signals` / `meta_decisions` / `no_trade_events` / `risk_events` / `orders` / `positions` / `close_events`)
- 二次 DB 集計ログ: M23 (Iteration 2) 計画 — projection_service 経由
- 必須ログ (シグナル全候補 / 採否 / EV分解 / 特徴量 / 決済 / no_trade): §4.11 + §4.10 catalog
- I-6: 全候補ログを invariant 化 (§4.1)

### 5.3.2 補完: 一次 / 二次のログ役割分担

| ログ種別 | 一次 DB (詳細・正本) | 二次 DB (集計・参照) |
|---|---|---|
| 全 strategy_signals | row 単位 (1 cycle = N strategies × M instruments) | 日次 aggregation (`mart_strategy_daily`) |
| meta_decisions | row 単位 + 全 snapshot | 採用 instrument 別 day-roll |
| no_trade_events | row 単位 + 理由 | 理由別 day-roll (which reason was most common today) |
| feature_snapshots | row 単位 (compact_mode で本体は sample のみ) | feature_hash distribution 統計 |
| close_events | row 単位 + pnl_realized | 日次 pnl roll-up + reason 別 |
| orders / positions | row 単位 | 統計化はしない (一次 DB から直接 dashboard) |
| audit (operator 操作) | 一次 DB | (任意; 必要に応じて二次へ projection) |

**rule**: 二次 DB の row は**必ず一次 DB の集計から再生成可能**でなければならない (二次 DB を消去 → 一次から rebuild できる)。

### 5.3.3 補完: ログ retention

| テーブル | retention (一次 DB) | retention (二次 DB) |
|---|---|---|
| feature_snapshots | 30 日 (compact_mode は 90 日) | 集計のみ無期限 |
| strategy_signals | 90 日 | 日次 mart 無期限 |
| meta_decisions | 90 日 | 日次 mart 無期限 |
| no_trade_events | 90 日 | 日次 mart 無期限 |
| risk_events | 1 年 (audit) | — |
| orders / positions | 無期限 | — |
| close_events / pnl_realized | 無期限 | 日次 mart 無期限 |

retention は `app_settings.retention_*_days` で override 可。`docs/retention_policy.md` (既存) と整合させる。

---

## 5.4 Phase 4 — DB 設計

### 5.4.1 既存カバレッジ
- 一次 DB 正本: §4.12
- 二次 DB 参照: §4.12 + M23
- 状態管理: §5.2.2
- バージョン管理: alembic 既存 (Iteration 2 M24 で modernization 計画)
- 非同期同期: §5.0.3 + projection_service

### 5.4.2 補完: `run_id` / `experiment_id` lifecycle

| ID | 範囲 | 永続化 | 用途 |
|---|---|---|---|
| `cycle_id` (UUID) | 1 cycle (1m bar 1 周) | `meta_decisions.cycle_id` 等 | 1 cycle 内の全 row を join |
| `run_id` (UUID) | 1 process 起動 ~ 終了 | **既存 `system_jobs`** (alembic 0009 group_i_operations) + 全 logged row に `run_id` 列 | プロセス単位の audit / replay |
| `experiment_id` (str) | 1 学習試行 | `model_runs.experiment_id` | 学習バッチの単位 (cron 1 回 = 1 experiment) |
| `model_version` (str) | 1 モデル | `model_runs.model_version` + `model_metadata.yaml` | 推論時のトレース |
| `feature_version` (str) | 1 feature definition set | `feature_snapshots.feature_version` | 特徴量 schema の version |
| `config_version` (str) | 1 app_settings バージョン | `app_settings_history` + 全 logged row | 設定変更の audit |

**既存テーブルの再利用方針 (新規テーブル作成しない)**:
- `system_jobs` (alembic 0009 既存): `run_id` の永続先として再利用。Phase 9.0 audit で必須カラム (`run_id`, `started_at`, `stopped_at`, `mode`, `git_sha`, `host`, `pid`) のカバレッジを確認し、不足あれば alembic 追加列で補う
- 起動時に 1 row insert; 全 cycle row が `run_id` を持つように meta_cycle_runner を改修 (Phase 9.1 範囲)
- 新規物理テーブル `runtime_runs` は **作らない** (`system_jobs` で十分)

### 5.4.3 補完: 再現性 (deterministic replay)

- 同じ `(feature_version, model_version, config_version, replay_data)` → 同じ `MetaDecision` を生成できること (I-7)
- replay 時は `run_id` を新規発行するが、`config_version` / `feature_version` / `model_version` を input 指定で固定可能
- replay 結果と original 結果の **row-level diff test** を Phase 9.0 audit に組込

### 5.4.4 補完: バージョン管理

- DB schema: alembic (既存) — Iteration 2 M24 で modernization
- model: `model_metadata.yaml` (§4.13.3)
- feature: `feature_version` 文字列 (semver) — `FeatureBuilder.get_feature_version()` 既存
- config: `app_settings` row + `app_settings_history` (audit)
- code: git SHA — `runtime_runs.git_sha` で記録

---

## 5.5 Phase 5 — UI / ダッシュボード設計

### 5.5.1 既存カバレッジ
- 既存 panels (`src/fx_ai_trading/dashboard/panels/`):
  - `market_state.py` — 相場評価表示 ✅
  - `meta_decision.py` — メタ判断可視化 ✅
  - `top_candidates.py` — 候補一覧 ✅
  - `strategy_summary.py` — 戦略別成績 ✅
  - `recent_signals.py` — 直近シグナル ✅
  - `positions.py` — オープン玉 ✅
  - `risk_state_detail.py` — リスク状態 ✅
  - `daily_metrics.py` — 日次指標 ✅
  - `execution_quality.py` — 約定品質 ✅
  - `learning_ops.py` — 学習状況 ✅
  - `supervisor_status.py` — 起動状態 ✅
- 二次 DB 参照: §4.12 + dashboard query service B 形態 (Phase 8 で HTTP 化計画)
- 軽量表示: Streamlit 既存 (Phase 8 で Next.js 卒業条件設定済)
- 外部アクセス: BasicAuth + IP 制限 (Phase 8 で SSO 計画)
- 学習設定画面: §4.13.4 + Iteration 2 M21

### 5.5.2 補完: Phase 1 仕様への対応マップ

| Phase 5 要件 | 対応 panel | gap |
|---|---|---|
| 相場評価表示 | `market_state.py` + `top_candidates.py` | ✅ |
| 戦略選択可視化 | `meta_decision.py` + `strategy_summary.py` | ⚠ 通貨強弱 (Phase 9.3) を表示する panel 未実装 |
| EV 可視化 | `top_candidates.py` (内部に EV 列あり) + `meta_decision.py` | ⚠ EV 内訳 (P(win)/AvgWin/AvgLoss/Cost) の breakdown panel 未実装 |
| 学習設定画面 | `learning_ops.py` (status 表示) | ⚠ 「対象選択 + 期間指定 + 即時/cron 実行」UI 部分 (M21 で実装予定) |
| 実行状態 | `supervisor_status.py` | ✅ |

### 5.5.3 補完: 新規 panel (Phase 9 と並行で追加)

- **`currency_strength.py`** (Phase 9.3 と同期): G8+ 全通貨の強度 z-score を heatmap 表示
- **`ev_breakdown.py`** (Phase 9.0 audit 後): meta_decisions の EV 内訳 (P(win), AvgWin, AvgLoss, Cost) を 1 cycle 分 drill-down
- **`promotion_history.py`** (Phase 9.8 と同期): champion-challenger の交代履歴

### 5.5.4 補完: dashboard データソース方針

**現状 (M26 既存実装)**:
- 全 11 panel は `dashboard/panels/` 配下にあり、`dashboard_query_service` 経由で **一次 DB (PostgreSQL) を read-only で直接 query** している (Supabase 経由ではない)
- `dashboard_query_service` は read-only かつ集計クエリ中心 → I-4「売買経路は一次 DB のみ」とは衝突しない (dashboard は売買経路ではない)
- I-11「二次 DB 障害が売買を停止させない」とも整合 (dashboard が落ちても売買は走る)

**短期方針 (現行 ~ M23 完了まで)**:
- 一次 DB read-only 経路を継続。`dashboard_query_service` は **read-only role** で接続することを CI で担保
- 高 QPS 対策として **read replica or 集計テーブル (materialized view)** を優先。Supabase 強制移行は急がない

**長期方針 (M23 完了後)**:
- M23 projection 経路 (Postgres → Supabase) 完成後、**操作系/履歴系 panel は二次 DB 読み取りに段階移行**することを検討
- production 売買中の risk_state_detail / supervisor_status 等の **near-real-time panel は一次 DB 直読みのまま**残す (二次 DB 同期遅延を許容しない)

> **5.5.4-Rule (修正版)**: dashboard panel の DB read 経路は「(a) 一次 DB read-only role 直読み」 or 「(b) 二次 DB 読み取り」のいずれか。**書き込みは一切禁止**。新規 panel 追加時は (a)/(b) のどちらかを明示する。M23 完了までは (a) が default。

---



- **D3**: 既存設計ドキュメント (Iteration 1 で参照されていた `docs/design.md` 由来)。Phase 1 の元
- **M9**: Iteration 2 milestone — run_exit_gate 単一経路化 / QuoteFeed Protocol
- **M10**: Iteration 2 milestone — EntrySignal 簡易経路 (本書 4.5 で eval-only と位置付け)
- **Tier-A / Tier-B**: 本書で導入したプロセス分離区分 (24h / batch)
- **bar cadence**: 1m or 5m candle 終値到達時刻
- **tick cadence**: sub-second; QuoteFeed の polling/streaming 間隔

# Appendix B. 既存ドキュメントとの関係

| ドキュメント | 役割 | 本書との関係 |
|---|---|---|
| `docs/design.md` | D3 元設計 | 本書 §4 がこれと整合 |
| `docs/iteration1_implementation_plan.md` | 過去 plan | 完了済 |
| `docs/iteration2_implementation_plan.md` | 現在進行 plan | M13-M26 進行中 |
| `docs/phase6_hardening.md` | hardening 完了 | 既達 |
| `docs/phase7_roadmap.md` | 運用自動化 | 進行中 |
| `docs/phase8_roadmap.md` | 観測・運用高度化 | 将来 |
| `docs/phase9_roadmap.md` | ML / TA / メタ高度化 | **本書 §4.19 に従い更新** |
| `docs/design/m9_*` 各 closure memo | 実装記録 | 既達 |
| `docs/design/m26_*` closure memo | UI/Console 凍結 | 既達 |

# Appendix C. 変更履歴

- 2026-04-24 v1.0: 初版。§1-4 + Appendix A-C。Phase 9 roadmap への反映指示を §4.19 に記載。
- 2026-04-24 v1.1: §5 (Phase 0 / 2 / 3 / 4 / 5 補完) を追加。新 invariant I-11 (二次 DB 障害分離) / 5.2.2-Rule (再起動復元) / 5.5.4-Rule (dashboard データソース) を導入。
- 2026-04-24 v1.2: 統合レビュー結果を反映。
  - §4.11 冒頭に「decision_log は論理名 (= meta_decisions ⋈ strategy_signals ⋈ feature_snapshots) であり物理テーブルではない」を明記
  - §5.4.2 の `runtime_runs` 新規テーブル提案を撤回し、既存 `system_jobs` (alembic 0009) を `run_id` 永続先として再利用する方針に変更
  - §5.5.4-Rule を実装現状 (M26 panel は一次 DB read-only 直読み) に合わせて緩和。M23 完了までは一次 DB read-only role 直読みが default、M23 後に段階移行を検討する方針へ修正
