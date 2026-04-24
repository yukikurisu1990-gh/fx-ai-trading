# Phase 9 — ML 価格予測 / 通貨強弱 / TA メタ戦略 (Roadmap / 実装順)

> **本書の位置付け**: Phase 9 は Phase 8 ロードマップで「スケール期: ML 高度化 / マルチブローカー / champion-challenger 等 (Phase 8 範囲外)」として後送りされた領域を、**実装に着手できる粒度**まで分解した**実装順** roadmap。
>
> **コア設計 (不変仕様) は別ドキュメント**: `docs/phase1_core_design.md` を正とする。本書はそこで定義された invariants (I-1 ~ I-10) と DTO (StrategySignal / MetaDecision / FeatureSet) を**実装に落とし込むための時系列計画**。本書と Phase 1 コア設計が衝突した場合は **Phase 1 が優先**する。
>
> **2026-04-24 更新**: 既存 D3 設計 (`StrategyEvaluator` / `MetaDecider` / `FeatureBuilder` / `EVEstimator` + MA/ATR/AI strategies) が `src/fx_ai_trading/domain/` と `services/` に**ほぼ全面実装済み**であることが Phase 1 audit で判明。これを受けて以下を再編:
> - **Phase 9.0 を新設**: 既存 D3 実装の完成度棚卸し
> - **Phase 9.1 を再定義**: M10 簡易経路の昇格ではなく「D3 経路の production runner 結線」
> - **Phase 9.2 を再定義**: G8 限定 → OANDA 動的全ペア (`OandaInstrumentRegistry`)
> - **Phase 9.4 / 9.6 / 9.7 を再定義**: 新規 package を作らず、既存 D3 contract (`StrategyEvaluator`) を満たす実装で extend
>
> **前提となる既存契約 (Iteration 2 / M9 / M10 / D3 で確立済)**
> - **D3 (既設・正)**: `StrategyEvaluator` Protocol + `StrategySignal` DTO (`domain/strategy.py`); `MetaDecider` Protocol + `MetaDecision` DTO (`domain/meta.py`); `FeatureBuilder` Protocol + `FeatureSet` DTO (`domain/feature.py`); `MAStrategy` / `ATRStrategy` / `AIStrategyStub` (`services/strategies/`); `MetaDeciderService` + `run_meta_cycle` (`services/meta_decider.py` + `meta_cycle_runner.py`)
> - **M9 (既達)**: `run_exit_gate` 単一 exit 経路, `QuoteFeed` Protocol, `OandaQuoteFeed`
> - **M10 (eval-only として retain)**: `EntrySignal` Protocol + `MinimumEntryPolicy` first-non-None picker — Phase 1 §4.5 で eval/regression 用途に位置付け
> - **PR #172/174 (既達)**: `fetch_oanda_candles`, `CandleReplayQuoteFeed`, `--replay-candles`

---

## 1. 目的

Phase 8 までで運用が「壊れない / 育つ / チームで運用できる」状態に達した上に、**判断軸の高度化**を載せる:

- **市場把握**: 単一通貨ペアの直近 N tick だけでなく、**全通貨ペアの相互関係**から相場状態を把握する
- **テクニカル分析**: SMA / EMA / RSI / MACD / ATR / Bollinger 等を `EntrySignal` Protocol 準拠で組み込み、戦略の語彙を増やす
- **ML 価格予測**: 教師あり学習による方向性 / 期待リターン推定を `EntrySignal` Protocol 準拠で組み込む
- **メタ戦略**: 上記を「戦略の集合」として持ち、**相場状態に応じた champion 選定**で組み合わせる

最終的な指標 (本書の意味する「確実に実現可能な指標」):
- Phase 9 完了時点で、**3 種類以上の独立な戦略系統 (rule / TA / ML) が同一 Protocol で eval pipeline 上を走り**、champion-challenger フレーム上で**月次の自動リプレース**が回っていること

---

## 2. 範囲

### 2.1 In Scope (本書で扱う)

- 多通貨ペア候補データ取得・蓄積パイプライン (1 JSONL = 1 instrument)
- `SignalFeed` Protocol と `CandleReplaySignalFeed` (OHLCV+volume を Signal 層に提供; `QuoteFeed` とは別系統)
- 通貨強弱指数 (Currency Strength Index, CSI) 計算サービスとそれを消費する `CrossPairStrengthSignal`
- TA 指標ライブラリ (純関数) と TA 系 `EntrySignal` 群
- 特徴量 / ラベル生成パイプライン (リーケージ防止 / forward-return / triple-barrier)
- ML ベースライン (gradient boosting; LightGBM 想定) と `MLPriceDirectionSignal`
- メタ戦略結合層 (EV-weighted picker, 相場状態ゲート)
- backtest → paper A/B → live demo → live real の昇格ゲート定式化

### 2.2 Out of Scope (Phase 10+ または別ロードマップ)

- マルチブローカー対応 (OANDA 以外) — 別ロードマップ
- 強化学習 (RL) — Phase 10+
- 深層学習 (LSTM / Transformer) は Phase 9.9 で**任意**として扱う (gradient boosting が rule を上回ったときのみ)
- 約定品質 (slippage モデル / TWAP-VWAP 比較) — Phase 11
- Tick データへの拡張 (現状 candle ベース) — Phase 11
- 社外データ (経済指標 / news / sentiment) — Phase 12

---

## 3. 入力 / 依存

### 3.1 主要入力

- **OHLCV candle**: `scripts/fetch_oanda_candles.py` 出力 (PR #172) — instrument 単位の JSONL
- **Quote stream (replay)**: `CandleReplayQuoteFeed` 出力 (PR #174) — `Quote(price=close, ts, source)`
- **Live quote / candle**: `OandaQuoteFeed` (M-3d) と `fetch_oanda_candles` のライブモード化 (Phase 9.2 で追加)

### 3.2 コード依存

- M9 完了 (run_exit_gate 単一経路, QuoteFeed Protocol, OandaQuoteFeed) — **完了済**
- M10 完了 (EntrySignal Protocol, MinimumEntryPolicy multi-signal picker) — **完了済**
- PR #174 (CandleReplayQuoteFeed + `--replay-candles`) — **完了済**
- Iteration 2 完了 (M13-M26) — **進行中**: live adapter / reconciler / dashboard / TSS calculator が前提

### 3.3 外部依存

- LightGBM (Phase 9.6 で導入) — Apache-2.0
- pandas / numpy (既存) — feature store / バックテスト集計
- pyarrow (Phase 9.5 で feature store の parquet 化) — Apache-2.0
- (任意) PyTorch (Phase 9.9 で LSTM/Transformer を試すなら)

---

## 4. ゴール

### 4.1 定量ゴール (Phase 9 全体完了時点)

- 同一 eval pipeline 上で **3 種類以上の戦略系統**が独立に走る
- 直近 6 ヶ月分の OHLCV (M5 想定) を replay した backtest で、ML 戦略の **out-of-sample Sharpe ≥ rule baseline + 0.3**
- champion-challenger の自動 promotion が **月次で 1 回以上**実行される
- 主要通貨 8 ペア (EUR/USD, USD/JPY, GBP/USD, USD/CHF, AUD/USD, USD/CAD, NZD/USD, EUR/JPY) で CSI が**毎時更新**される

### 4.2 定性ゴール

- 「rule signal を一つ作る → backtest → paper A/B → 採否決定」の**標準サイクル**が確立
- ML モデルの**再現性** (同じ入力 → 同じモデル → 同じ予測) が保証される
- 「なぜこの signal が発火したか」が常に **decision log として残る** (auditability)
- 戦略が増えても eval pipeline / live runner の構造が変わらない (Protocol 越しに plug)

---

## 5. Phase 分割

| Phase | 名称 | 目的 | 概算規模 | 依存 |
|---|---|---|---|---|
| **9.0** | **D3 既存実装 audit** | `meta_decider` / `meta_cycle_runner` / `strategy_runner` / `feature_service` / `ev_estimator` / `risk_manager` / `position_sizer` の Phase 1 要件カバレッジ棚卸し (docs only) | 小 (PR 1) | M10 完了 |
| **9.1** | **D3 production runner 結線** | `scripts/run_paper_decision_loop.py` 新規 — `run_meta_cycle` を bar cadence で叩く; `BarFeed` Protocol; M10 経路は eval-only として retain | 中 (PR 3-5) | 9.0 |
| **9.2** | **動的全ペア化** | `OandaInstrumentRegistry`; production runner からの instrument hardcode 禁止 lint; multi-instrument の event-time merged backtest | 中 (PR 3-4) | 9.1 |
| **9.X-A** | **close reason 拡張** | `close.reverse_signal` / `ev_decay` / `news_pause` / `manual` / `session_close` を `CloseReason` に追加; `run_exit_gate` 発火条件追加 | 小 (PR 2) | 9.0 (並行可) |
| **9.X-B** | **I-4 lint (二次 DB import 禁止)** | `tools/lint/run_custom_checks.py` に CI rule 追加 | 小 (PR 1) | M23 着手前に推奨 |
| 9.3 | 通貨強弱指数 (CSI) | G8+ 通貨強弱、`CurrencyStrengthIndex` を `MetaDecider` filter 入力に組込 (新規 Signal class は作らない) | 小 (PR 2-3) | 9.2 |
| 9.4 | TA 戦略追加 | SMA / EMA / RSI / MACD / Bollinger を `services/strategies/` に追加 (各々 `StrategyEvaluator` 準拠) | 中 (PR 4-5) | 9.1 |
| 9.5 | Feature / Label pipeline | 特徴量・ラベル生成、parquet feature store; `FeatureBuilder` 既存 Protocol を拡張 | 中 (PR 3-4) | 9.4 |
| 9.6 | ML baseline | LightGBM, walk-forward CV, `AIStrategyStub` を `MLDirectionStrategy(model_path)` で置換 | 大 (PR 5-7) | 9.5 |
| 9.7 | Meta-strategy 拡張 | EV-weighted picker / 相場状態ゲートを `MetaDeciderService` の Score 段に組込 (新規 Policy class は作らない) | 中 (PR 3-4) | 9.3 / 9.4 / 9.6 |
| 9.8 | 昇格ゲート / Online A/B | backtest → paper → live promotion 定式化; `model_metadata.yaml` lifecycle 自動化 | 中 (PR 3-4) | 9.7 |
| 9.9 | (任意) Sequence model | LSTM / Transformer を `StrategyEvaluator` Protocol 越しに | 大 (PR 5-7) | 9.6 が rule baseline 超過 |

---

## 6. Phase 詳細

### 6.0 Phase 9.0 — D3 既存実装 audit (新設)

**目的**: Phase 9.1 以降の前提として、既に `src/` に居る D3 stack の実装完成度を Phase 1 要件に対して棚卸し、不足箇所を 9.X-* / 9.1+ のどこで埋めるかを確定する。

**変更対象 (docs only — コードは書かない)**:
- 新規: `docs/design/phase9_0_d3_audit.md` — 以下の matrix を含む:
  - **(最優先) production runner の D3 結線確認**: `scripts/run_paper_entry_loop.py` / `scripts/run_paper_evaluation.py` / `scripts/run_live_loop.py` のいずれも `MetaCycleRunner` を呼んでいない事実 (M10 簡易経路に依存) を再検証 + 移行コスト見積
  - `services/meta_decider.py` (336 lines): Filter / Score / Select 段の現状実装と Phase 1 §4.6 要件 (市場状態 / ボラ / spread / 通貨強弱 / 相関 / 時間帯 / 指標 / EV / 戦略別成績) の対応
  - `services/meta_cycle_runner.py` (770 lines): cycle 1 周分の処理 step と Phase 1 §4.11 ログ書き込み責務の対応 (decision_log = `meta_decisions ⋈ strategy_signals ⋈ feature_snapshots` の federation; 単一 table ではない)
  - `services/strategy_runner.py` (310 lines): 並列実行 / per-strategy timeout の現状
  - `services/feature_service.py` (150 lines): feature_hash 決定論性の検証
  - `services/ev_estimator.py` (73 lines): cost integration の実装範囲
  - `services/risk_manager.py` + `position_sizer.py`: Phase 1 §4.8 (1-2% / 通貨偏重 / 総リスク) のカバレッジ
  - `services/strategies/{ma, atr, ai_stub}.py`: 各 StrategyEvaluator の動作確認
  - `services/correlation_matrix.py` / `services/event_calendar.py` / `services/price_anomaly_guard.py`: MetaDecider filter 入力源としての結線確認
  - **既存 schema 確認**: `system_jobs` (alembic 0009) のカラムが Phase 1 §5.4.2 の `run_id` lifecycle 要件 (started_at / stopped_at / mode / git_sha / host / pid) を充足しているか確認 — 不足あれば 9.1 で alembic 追加列
  - **既存 outbox 確認**: `secondary_sync_outbox` (alembic 0013) のスキーマと Phase 1 I-11 (fire-and-forget + 再送キュー) の整合
  - **dashboard panel データソース確認**: `dashboard_query_service` 経由の全 11 panel が一次 DB read-only role で接続されていることを確認 (5.5.4-Rule 修正版に整合)
- 新規: `docs/design/phase9_0_gap_resolution_plan.md` — 各不足を 9.1-9.X のどこで解消するか割付

**完了条件**:
- 各 service について「Phase 1 要件カバレッジ ✅ / ⚠ / ❌」が記録される
- ❌ 項目は 9.1 以降のどの Phase で埋めるかが本書 §5 に追記される
- audit memo は **コード変更を伴わない** (本 Phase は docs only)

**リスク**:
- audit で重大な未実装が判明 → 9.1 着手前に追加 patch phase が要る可能性 — その場合は 9.0 を完了させてから判定

---

### 6.1 Phase 9.1 — D3 production runner 結線 (再定義)

**目的**: Phase 1 invariant I-1 / I-2 の実現。production runner を**D3 経路**に収束させる。M10 簡易経路 (`EntrySignal` + `MinimumEntryPolicy`) は **eval-only として retain** (削除しない、production は D3 へ)。

**変更対象 (想定)**:
- 新規: `src/fx_ai_trading/domain/bar_feed.py` — `BarFeed` Protocol (`get_bar(instrument, tier) -> Candle | None`); `Candle` DTO は既存
- 新規: `src/fx_ai_trading/adapters/bar_feed/candle_replay_bar_feed.py` — 既存 `CandleReplayQuoteFeed` の bar 版 (PR #174 の JSONL を Candle として yield)
- 新規: `src/fx_ai_trading/adapters/bar_feed/oanda_candle_feed.py` — OANDA から live bar を polling (1m/5m)
- 新規: `scripts/run_paper_decision_loop.py` — 1m bar cadence runner; `run_meta_cycle` を呼ぶ; D3 経路の唯一の paper 入口
- 新規: `scripts/run_live_decision_loop.py` — 同上の live demo 版 (`OandaCandleFeed` + `OandaBroker(account_type="demo")`)
- 修正: `services/meta_cycle_runner.py` — instrument 単一渡し → instrument 集合受けの API 拡張 (動的全ペアの前提として)
- **既存維持**: `scripts/run_paper_entry_loop.py` / `run_paper_evaluation.py` — M10 経路は eval-only として残す。production への結線パスは閉じる (docstring に明記)

**完了条件**:
- `run_paper_decision_loop.py` が 1 cycle で `feature_snapshots` / `strategy_signals` / `meta_decisions` / `no_trade_events` 全部に書き込みする
- `MetaDecision.no_trade=False` で発注された注文が `orders` / `positions` に記録される
- 1m cadence で 5 cycle 連続実走 (smoke)
- M10 簡易経路 (`run_paper_entry_loop.py`) が test 全 green を維持

**リスク**:
- `meta_cycle_runner` の API 変更 (instrument 集合受け) で既存 test 影響 → backward-compat な signature (default = 1 instrument list) で吸収
- 1m cadence の per-cycle SLA (本書 §16 = 30s) を超える可能性 → 9.0 audit 段階で per-cycle 計測; 超過時は 9.1 内で並列度調整

---

### 6.2 Phase 9.2 — 動的全ペア化 (再定義)

**目的**: Phase 1 invariant I-8 の実現。OANDA から取引可能 instrument を動的取得し、毎サイクル全ペアを評価する。固定リスト禁止を CI lint で強制。

**変更対象**:
- 新規: `src/fx_ai_trading/services/instrument_registry.py` — `OandaInstrumentRegistry` クラス
  - `refresh()`: OANDA `accounts/{id}/instruments` を呼び `set[Instrument]` を更新
  - `tradeable_now()`: 現時点 tradeable な subset
  - 失敗時は前回値を保持 + warning ログ; N 連続失敗で SafeStop
- 修正: `services/meta_cycle_runner.py` — 起動時 + 各 cycle で `OandaInstrumentRegistry.tradeable_now()` を呼び、その instrument 集合を iterate
- 修正: `tools/lint/run_custom_checks.py` — production code path での instrument hardcode 検出 ルール:
  - `scripts/run_paper_decision_loop.py` / `scripts/run_live_decision_loop.py` で `--instrument <comma_separated>` 形式の引数禁止
  - `INSTRUMENTS = ['EUR_USD', ...]` のような module-level constant 禁止 (in production code path)
- 修正: `scripts/fetch_oanda_candles.py` — `--instruments EUR_USD,USD_JPY,...` で fan-out (eval/replay 用途のみ)
- 新規: `src/fx_ai_trading/adapters/bar_feed/multi_instrument_replay_bar_feed.py` — N 個の JSONL を `ts` で merge (k-way heap merge); eval pipeline 用

**完了条件**:
- production runner が起動時 `tradeable_now()` で instrument 集合を取得 → 1 cycle 完了
- OANDA API 失敗時の前回値保持 + warning ログが unit test で確認
- I-8 lint が CI で実行され、hardcode した instrument list を含む違反 PR を reject
- 動的取得 instrument 集合の **per-cycle SLA (≤30s)** が達成される (実測ログ)

**リスク**:
- instrument 数が多い (~70 ペア) で per-cycle SLA 超過 → asyncio.gather で N=8 並列; 9.1 audit で実測判定
- 通貨ペアごとの取引時間差 (土日 close 跨ぎ) → `instrument.tradeable=False` で skip + cycle 全 skip なら supervisor pause

---

### 6.3 Phase 9.3 — 通貨強弱指数 (CSI) → MetaDecider filter 入力 (再定義)

**目的**: 「全通貨を対象とした通貨間強弱の判断」を **MetaDecider の filter 入力**として組み込む。新規 `CrossPairStrengthSignal` (M10 経路) は作らず、D3 contract に統合する。

**変更対象**:
- 新規: `src/fx_ai_trading/services/currency_strength.py` — `CurrencyStrengthIndex` サービス
  - 入力: `OandaInstrumentRegistry.tradeable_now()` の全 FX ペア (G8 限定ではない)
  - 出力: 各通貨 (EUR/USD/JPY/GBP/CHF/AUD/CAD/NZD/...) の強度 score (z-score 正規化)
  - 計算: 各通貨について「base 側ペア直近リターン平均 − quote 側ペア直近リターン平均」(古典 CSI)
  - 更新粒度: 1 cycle = 1 update (`MetaContext` に強度 dict を載せる)
- 修正: `domain/meta.py` — `MetaContext` に `currency_strength: dict[str, float] | None = None` を追加 (optional フィールド; 既存 caller への破壊なし)
- 修正: `services/meta_decider.py` — Filter 段に「base/quote 強度差 < threshold → SIGNAL_NO_TRADE」相当の rule を追加 (rule 化対象は 9.7 で score 段に移動)
- 新規: `tests/unit/test_currency_strength.py`

**完了条件**:
- CSI が cycle ごとに更新され `meta_decisions.filter_snapshot` に記録される
- `MetaDecider.decide` の判定で CSI が参照される (test 化)
- I-8 (動的全ペア) 達成時、G8 限定でなく全 FX ペアで CSI が計算される

**リスク**:
- 通貨ペアの欠損 (一部 instrument が未配信の bar) で CSI が NaN → そのペアを除外して計算続行 + warning
- ペア数が少ない時間帯 (週末跨ぎ) → CSI 計算閾値 (最小ペア数 4) 未達なら `MetaContext.currency_strength=None`

---

### 6.4 Phase 9.4 — TA 戦略追加 (再定義)

**目的**: 「テクニカル分析手法を取り入れたメタ戦略」の素材。TA 指標を**純関数**として用意し、各々を **`StrategyEvaluator` Protocol 準拠の戦略**として `services/strategies/` に追加する (新規 package を作らない; 既存 MA/ATR と同居)。

**変更対象**:
- 新規: `src/fx_ai_trading/services/ta_indicators/` 配下 (純関数 ライブラリ)
  - `sma.py` — `simple_moving_average(closes, period) -> float | None`
  - `ema.py` — `exponential_moving_average(closes, period)`
  - `rsi.py` — `rsi(closes, period=14)` (Wilder)
  - `macd.py` — `macd(closes, fast=12, slow=26, signal=9)`
  - `bollinger.py` — `bollinger(closes, period=20, std=2.0)`
  - (`atr.py` は `services/strategies/atr.py` で既使用 — 共有 helper 化)
- 修正: `services/feature_service.py` — `FeatureSet.feature_stats` に `rsi_14`, `macd`, `bb_upper/mid/lower`, `ema_*` 等を追加
- 新規: `src/fx_ai_trading/services/strategies/` 配下 (`StrategyEvaluator` 準拠)
  - `rsi.py` — `RSIStrategy(period=14, oversold=30, overbought=70)`
  - `macd.py` — `MACDStrategy()` — MACD line cross
  - `bollinger.py` — `BollingerBreakoutStrategy()` — band touch
- 修正: `services/strategies/__init__.py` — `STRATEGY_REGISTRY` に追加 (Phase 1 §4.5.2)
- 新規: `tests/unit/test_ta_indicators.py` (golden value pin)
- 新規: `tests/unit/test_strategies_ta.py`

**完了条件**:
- 全 TA 指標が単体テストで決定論性 + 参照実装相当の golden number と一致
- 新 TA 戦略が `STRATEGY_REGISTRY` に登録され、`run_meta_cycle` の cycle で `MAStrategy`/`ATRStrategy` と並列評価される
- 全候補が `strategy_signals` に書かれ (採否問わず)、却下は `no_trade_events` に記録

**リスク**:
- 参照実装 (pandas-ta 等) の Wilder smoothing 解釈差 → 期待値は **本 phase 着手時点で計算した golden number を pin** (外部依存を test に持ち込まない)
- 状態保持 (RSI / MACD は前 bar 結果引きずり) → `FeatureBuilder` が rolling window を保持; 戦略は純関数 (state なし)

---

### 6.5 Phase 9.5 — Feature / Label pipeline

**目的**: ML モデル学習の前提となる**特徴量とラベル**を leak-free に生成し、parquet feature store として保存。`services/feature_service.py` の scaffolding を本格化。

**変更対象**:
- 修正: `src/fx_ai_trading/services/feature_service.py` — feature 計算オーケストレーション
- 新規: `src/fx_ai_trading/services/labeling/forward_return.py` — `forward_return(closes, horizon=12)`
- 新規: `src/fx_ai_trading/services/labeling/triple_barrier.py` — TP/SL/timeout のいずれが先に到達したかでラベル付け (`+1` / `−1` / `0`)
- 新規: `scripts/build_feature_store.py` — JSONL → parquet 変換ジョブ
  - 入力: `data/g8_m5_<YYYYMM>/`
  - 出力: `data/features/g8_m5_<YYYYMM>.parquet` (1 row = 1 (instrument, ts), 列 = 全 TA + CSI + 各種派生)
- 新規: `tests/unit/test_labeling.py`, `tests/integration/test_feature_store_roundtrip.py`

**Leak-free design (重要)**:
- すべての特徴量は **bar t における t 以前の情報のみ**を使用
- ラベル `y_t` は **bar t+H** までの情報を使用 (future window)
- 学習時は `y_t` の future window が完了している t のみ使用 (timeline cutoff)
- 特徴量計算と signal 計算は**同じコード**を使う (`services/ta_indicators/*` を共有)

**完了条件**:
- 6 ヶ月分 G8 8 ペア × M5 = ~250k rows の parquet が < 30 秒で生成される
- forward-return / triple-barrier ラベルの単体テスト (合成 OHLCV で期待値ピン)
- 特徴量/ラベルの**リーケージ検査**: 学習データの最大 ts < 検証データの最小 ts (時系列 split 必須)

**リスク**:
- triple-barrier の TP/SL を ATR 倍率で動的に決めるか固定 pips にするか → 9.5 着手時に決定; 初期は固定 pips で simple
- 通貨ペア間の同一 ts での同期 — multi-instrument feed の merge 結果 ts に揃える

---

### 6.6 Phase 9.6 — ML baseline (gradient boosting) — `AIStrategyStub` 置換 (再定義)

**目的**: 最初の ML 戦略。LightGBM で「次 H bars でクロスする barrier」を予測する 3 クラス分類 (or 期待リターン回帰)。**`AIStrategyStub` を `MLDirectionStrategy` で置換** (`StrategyEvaluator` Protocol 維持; 新規 package を作らない)。

**変更対象**:
- 新規: `src/fx_ai_trading/services/ml/training.py` — walk-forward CV 学習ループ
- 新規: `src/fx_ai_trading/services/ml/model_store.py` — モデル永続化 (joblib + `metadata.yaml`: Phase 1 §4.13.3 必須フィールド)
- 新規: `src/fx_ai_trading/services/ml/inference.py` — 推論 (load → predict → score; latency ≤ 200ms; SLA enforcement)
- 修正: `src/fx_ai_trading/services/strategies/ai_stub.py` を `ai.py` にリネーム; 中身を `MLDirectionStrategy(model_path, threshold=0.6)` に置換 (`AIStrategyStub` 名は backward-compat alias で残す or 削除は判断保留)
- 新規: `scripts/train_ml_baseline.py` — feature parquet → model 保存
- 新規: `scripts/evaluate_ml_baseline.py` — 学習済みモデルの OoS メトリクス
- 新規: `tests/unit/test_ml_inference_determinism.py` (同入力 → 同出力)
- 修正: `services/strategies/__init__.py` `STRATEGY_REGISTRY` 更新

**学習プロトコル**:
- Walk-forward (expanding window): 学習 6 ヶ月 → 検証 1 ヶ月、1 ヶ月ずつ前進
- 評価メトリクス: precision / recall / Sharpe / hit rate / max DD
- ハイパパラ探索は OPTUNA 等を使うが、**当該 phase の MVP では grid search で固定** (再現性優先)

**完了条件**:
- `scripts/train_ml_baseline.py` で 1 モデル学習 → `models/ml_baseline_<timestamp>/` 配下に保存
- `MLPriceDirectionSignal(model_path=...)` を `MinimumEntryPolicy` chain に投入可能
- backtest で **out-of-sample Sharpe が rule baseline + 0.3 以上**
- 同入力 → 同推論結果 (deterministic test pin)

**リスク**:
- データ不足 (6 ヶ月 × G8 = ~2M rows でも instrument 別に分けると ~250k/instrument) → cross-instrument 学習 (instrument を feature 化) を許容
- 過学習 → walk-forward + early stopping + feature importance 監視
- リーケージ → 9.5 の時系列 split を厳守

---

### 6.7 Phase 9.7 — Meta-strategy 拡張 (再定義)

**目的**: 個別戦略を**相場状態に応じて選択**する。新規 Policy class は作らず、**既存 `MetaDeciderService` の Score 段を拡張**して EV-weighted + regime gate を実現する。

**変更対象**:
- 修正: `src/fx_ai_trading/services/meta_decider.py` — Score 段に regime-aware の EV 重み付けを追加
- 修正: `src/fx_ai_trading/services/ev_estimator.py` — strategy 別 / regime 別の期待 EV (recent N trades の rolling) を返す API 追加
- 新規: `src/fx_ai_trading/services/regime/atr_regime.py` — ATR ベースの簡易 regime classifier (`'trend'` / `'range'` / `'high_vol'`)
- 修正: `domain/meta.py` — `MetaContext` に `regime: str | None = None` フィールド (optional)
- 修正: `services/tss_calculator.py` — regime × strategy の EV マトリクスを計算し、`MetaDecider` の Score 入力に注入
- 新規: `tests/unit/test_meta_decider_ev_weighted.py`, `tests/unit/test_regime_classifier.py`

**完了条件**:
- backtest で `EVWeightedEntryPolicy` が `MinimumEntryPolicy` を Sharpe で上回る
- regime 切替が decision log に記録される
- TSS が日次で per-(regime, signal) EV を再計算

**リスク**:
- regime 分類の不安定 → ヒステリシス (state 切替には N 連続観測必要)
- EV のサンプル数不足 → bayesian 事前分布 (Beta-Binomial 等) を allow

---

### 6.8 Phase 9.8 — 昇格ゲート / Online A/B

**目的**: 「backtest で良かった戦略」を**安全に live に昇格**するゲートを定式化し、自動化する。

**変更対象**:
- 修正: `src/fx_ai_trading/services/learning_ops.py` — challenger 登録 / paper A/B run / 昇格判定 API
- 新規: `src/fx_ai_trading/services/promotion_gate.py` — 昇格条件評価器
  - 条件: paper run >= 14 日, trades >= 100, Sharpe >= champion+0.2, max DD <= champion×1.2
- 新規: `scripts/run_promotion_gate.py` — 日次バッチで challenger を評価し、条件満たせば champion 入替
- 新規: `tests/unit/test_promotion_gate.py`, `tests/integration/test_learning_ops_promotion_flow.py`

**完了条件**:
- challenger を登録 → 14 日 paper → 自動昇格判定 が 1 サイクル動作
- 昇格 / 据え置きの decision が監査ログに残る
- 既存 champion との切替時に notification 発火

**リスク**:
- A/B 期間中の市場レジーム偏り → 評価期間を伸ばす / 重み調整は 9.8 着手時に再議
- 昇格時の position migration — 既存 open 玉は champion (旧) で運用継続、新 entry のみ challenger に流す原則

---

### 6.9 Phase 9.9 — (任意) Sequence model (再定義)

**目的**: gradient boosting baseline (9.6) が rule を上回ったときに限って着手。LSTM / Transformer を **`StrategyEvaluator` Protocol 越しに**同居させる。

**条件付き着手**: 9.6 の Sharpe が rule baseline + 0.5 以上で、かつ 9.7 のメタ層が 1 サイクル安定運用後。

**変更対象 (概略)**:
- 新規: `src/fx_ai_trading/services/ml/sequence_models/lstm.py`
- 新規: `src/fx_ai_trading/services/strategies/ml_sequence.py` — `SequenceModelStrategy(model_path)` (`StrategyEvaluator` 準拠)
- PyTorch 依存追加 (CPU inference を default; GPU 任意; I-10 維持)

**完了条件**:
- Sequence model が 9.6 baseline を out-of-sample Sharpe で上回る
- inference latency < 200ms / call (CPU; per-strategy SLA budget)

**リスク**:
- 過学習・データ不足 — Sequence は GBT より食う; 数ヶ月分では足りない可能性 → fetch を 2 年分に拡張する pre-phase が必要

---

### 6.10 Phase 9.X-A — close reason 拡張 (新設)

**目的**: Phase 1 §4.9.2 — 既存 4 種 (`sl`/`tp`/`emergency_stop`/`max_holding_time`) を拡張し、`reverse_signal` / `ev_decay` / `news_pause` / `manual` / `session_close` を追加。

**変更対象**:
- 修正: `src/fx_ai_trading/domain/reason_codes.py` — `CloseReason` に dotted 値追加 (LEGACY_BARE は frozen で触らず、新値を `DOTTED` set へ):
  - `close.reverse_signal`
  - `close.ev_decay`
  - `close.news_pause`
  - `close.manual`
  - `close.session_close`
- 修正: `src/fx_ai_trading/services/exit_policy.py` (or `exit_gate_runner.py`) — 各 reason の発火条件を実装
- 新規: `tests/unit/test_close_reason_priorities.py` — Phase 1 §4.9.3 priority order の test
- 新規: `tests/integration/test_close_reasons_e2e.py`

**完了条件**:
- 全新規 reason が `close_events.primary_reason_code` に書ける (test 化)
- 複数同時発火時の priority order が test で pin
- I-4 違反なし (DB 書き込みは一次のみ)

---

### 6.11 Phase 9.X-B — I-4 lint + outbox writer 結線 (新設, scope 縮小版)

**目的**: Phase 1 invariant I-4 (売買経路は一次 DB のみ) と I-11 (二次 DB 障害が売買を停止させない) を CI + 実装の両側で担保。M23 (Iteration 2 Supabase projector) 着手前に gate を入れる。

**前提 (前回 review で判明)**:
- `secondary_sync_outbox` テーブルは **既に alembic 0013 で schema 化済み** → 新規 schema 作成不要
- 残作業は (a) CI lint, (b) outbox writer の結線, (c) retry worker の 3 点に縮小

**変更対象**:
- (a) 修正: `tools/lint/run_custom_checks.py` — 新ルール:
  - `src/fx_ai_trading/services/{exit_gate_runner, execution_gate_runner, order_service, order_lifecycle, position_service, meta_cycle_runner, strategy_runner}.py` 等の trading-path module から `from fx_ai_trading.adapters.persistence.supabase` 系の import を検出 → fail
  - `scripts/run_*_loop.py` も同様
- (a) 新規: `tests/unit/test_no_secondary_db_in_trading_path.py` (lint rule の自己テスト)
- (b) 新規: `services/secondary_outbox_writer.py` — `secondary_sync_outbox` への enqueue (fire-and-forget API; trading-path から呼ばれる)
- (c) 新規: `services/secondary_outbox_worker.py` — 別プロセスで outbox を drain → Supabase へ projection (Phase 9.X-B では skeleton + dry-run のみ; 実 Supabase 結線は M23 で確定)

**完了条件**:
- CI で I-4 違反 PR が reject される
- 既存コードは違反 0 (M23 未着手のため自然に true)
- outbox writer/worker は dry-run mode で起動可能 (実 Supabase 結線なしでもエラーにならない)

---

## 7. Recommended Order

```
9.0 ─> 9.1 ─┬─> 9.2 ─┬─> 9.3 ──────────────────────┐
            │        └─> 9.5 ─> 9.6 ─────────────> 9.7 ─> 9.8 ─> [9.9 任意]
            └─> 9.4 ──────────────┘

並行実施可 (依存少):
  9.X-A (close reason 拡張)   ← 9.0 完了後いつでも
  9.X-B (I-4 lint)            ← M23 着手前であればいつでも
```

- **直列で必須**: 9.0 → 9.1 → 9.2 → 9.5 → 9.6 → 9.7 → 9.8
- **並列可**: 9.3 (CSI) と 9.4 (TA) は 9.1/9.2 の後にどちらから着手してもよい
- **並行可**: 9.X-A / 9.X-B は本流とは独立に着手 (規模も小)
- **任意**: 9.9 は 9.8 完了 + 9.6 baseline が rule 超過の条件付き

---

## 8. 完了判定 (Phase 9 全体)

Phase 9 完了の認定条件:

1. ✅ rule (3pt momentum / mean-reversion / down-only) / TA (4 種以上) / ML (LightGBM baseline) の **3 系統が同一 eval pipeline で走る**
2. ✅ G8 8 ペアの **CSI が backtest 中に毎 bar 更新**される
3. ✅ champion-challenger フレーム上で **月次の自動昇格判定**が 1 サイクル以上完了
4. ✅ 6 ヶ月 OHLCV replay で **ML 戦略 OoS Sharpe ≥ rule baseline + 0.3**
5. ✅ 全 signal の **inference / backtest が deterministic** (同入力 → 同出力)
6. ✅ Phase 9.1-9.8 各々で **closure memo を docs/design/** に残す (M9 / M26 と同じ pattern)

---

## 9. リスクと緩和

| リスク | 対象 phase | 緩和策 |
|---|---|---|
| Look-ahead bias | 9.5, 9.6 | 時系列 split を CI で強制; feature と signal の計算コード共有 |
| Overfitting | 9.6, 9.9 | walk-forward CV; out-of-sample-only 採否; feature importance 監視 |
| Data drift | 9.6, 9.7, 9.8 | 月次 re-train; champion-challenger による自動入替 |
| Multi-pair time alignment | 9.2, 9.3 | k-way merge を `(ts, instrument)` で厳密順序; gap は warning |
| Low-volume backtest illiquidity | 9.6, 9.8 | volume threshold filter; 主要時間帯 (London/NY overlap) のみ評価 |
| LightGBM/PyTorch deps | 9.6, 9.9 | uv lock で固定; CI で wheel ビルド |
| Production latency 超過 | 9.6, 9.9 | inference timing test (< 50ms target); 違反 PR は CI で fail |
| Strategy explosion (戦略増えすぎ) | 9.7 | TSS が EV based で淘汰; 90 日 underperform で auto-deprecate |

---

## 10. なぜ今は実装しないか (各 phase に着手するまでの judgement)

| phase | 着手前提 |
|---|---|
| 9.1 | Iteration 2 (M13-M26) が完了 — paper / live / dashboard の運用基盤が安定してから |
| 9.2 | 9.1 完了 + 多通貨を扱える本気の必要性 (CSI / cross-pair ML を実装する手前) |
| 9.3 | 9.2 完了 — 多通貨データが揃ってから |
| 9.4 | 9.1 完了 — 単独で着手可能だが、TA だけで戦略を増やしてもメタ層 (9.7) がないと効果が薄い |
| 9.5 | TA / CSI が増えた後 (feature の量が ML 投入に値するレベルになってから) |
| 9.6 | 9.5 完了 + 6 ヶ月以上の clean data |
| 9.7 | 9.6 + 複数 signal が同時稼働できる状況 |
| 9.8 | 9.7 完了 + 14 日連続 paper 運用が回っている状況 |
| 9.9 | 9.6 baseline が rule を明確に上回った場合のみ |

---

## 11. 各 phase の実装 / レビュー protocol

各 phase 着手時に以下を遵守する (Iteration 2 の M9 / M26 で確立した pattern を踏襲):

1. **Design memo を先に書く**: `docs/design/phase9_<X>_design_memo.md` (実装前)
2. **PR を分割**: 1 phase = 3-7 PR、1 PR = ≤500 lines / ≤10 files (CLAUDE.md §23)
3. **テスト同梱**: 新コードは unit test 必須、deterministic test を必ず含める
4. **closure memo を後に書く**: `docs/design/phase9_<X>_closure_memo.md` (実装完了後)
5. **memory 更新**: `~/.claude/projects/.../memory/MEMORY.md` に index 追加

---

## 12. Open Questions (着手時に確定する)

- **Q1**: candle granularity — M5 を default としたが、M1 / M15 / H1 の同時保持はいつから?
- **Q2**: feature store backend — parquet (local fs) のみで開始するが、duckdb / postgres-table 化は何時点で必要?
- **Q3**: ML モデルの再現性 — 学習時の random seed, library version, OS をどこまで固定するか (9.6 着手時に decide)
- **Q4**: champion-challenger の **同時走行最大数** — 戦略増殖を抑える上限値 (initial proposal: 3 challenger まで)
- **Q5**: live 昇格の **手動承認**を残すか自動のみか (9.8 着手時に decide; 初期は手動承認 + 自動 paper 評価が無難)

---

## 13. Summary

Phase 9 は 9 段の階段で **rule → TA → ML → メタ** に積み上げる。各段は単体で価値を返し (CSI / TA backtest など)、最終段 (9.7 + 9.8) で「相場状態に応じて自動的に best 戦略が走る」状態に到達する。

「確実に実現可能な指標」の意味で本書が機能する条件:
- 各 phase の **完了条件が客観的に judge 可能** (定量メトリクスで gate)
- 既存契約 (`QuoteFeed` / `EntrySignal` Protocol / `run_exit_gate`) を**変えずに** plug-in する設計
- backtest → paper → live demo → live real の**昇格パスが共通**で、戦略系統 (rule/TA/ML) によらず再利用される

実装は **9.1 から順に着手**し、各 phase 着手時に本書 §6.X を再読 → design memo (`docs/design/phase9_<X>_design_memo.md`) → PR シリーズ → closure memo の順で進める。
