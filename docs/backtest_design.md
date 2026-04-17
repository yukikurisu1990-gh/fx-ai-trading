# D2. Backtest Design

## Purpose
FX-AI-Trading の **backtest 世界の契約**を固定する。live と同一コア (Feature Service / StrategyEvaluator / MetaDecider / RiskManager / ExitPolicy) を、**決定的**で**監査可能**で**再現可能**な検証環境で動作させるための責務境界・look-ahead 防止・order state machine・slippage/fee/latency 模擬・評価指標・禁止事項を定める。本書により **Critical C2 (backtest engine の設計不在) を解消**する。

## Scope
- backtest engine の責務と境界
- 入力データと時間粒度
- look-ahead bias 防止ルール
- order / execution simulation
- 再現性・決定性・seed 管理
- 評価指標
- live との共通化方針
- walk-forward / OOS / embargo 等の検証プロトコル

## Out of Scope
- 具体的な Python 実装 (コード生成は Iteration 1 以降)
- Alembic migration DDL
- ハイパーパラメータ探索 (これは LearningOps 側の関心事、本書は検証エンジン側)
- パフォーマンス/ベンチマーク最適化 (Phase 7 以降)

## Dependencies
- `docs/schema_catalog.md` (D1): 入出力データ構造
- `docs/phase6_hardening.md` 6.10 (Feature Service 決定性 / feature_version)
- `docs/phase6_hardening.md` 6.11 (AIStrategy stub/shadow/active 遷移の shadow 検証で backtest が必須)
- `docs/phase7_roadmap.md` (7.1 regime tightening validation / 7.2 shadow → active Promotion)

## Related Docs
- `docs/implementation_contracts.md` (D3): BacktestRunner / MetaDecider / Broker Interface
- `docs/retention_policy.md` (D5): backtest 出力の保持クラス
- `docs/operations.md` (D4): backtest ジョブの運用

---

## 1. Backtest Engine の責務

### 1.1 中心責務

`BacktestRunner` は以下を責務とする:
1. 指定期間の `market_candles` / `market_ticks_or_events` / `economic_events` を**時系列順で供給**する
2. 各時点で Feature Service → StrategyEvaluator → EVEstimator → MetaDecider → RiskManager → PositionSizer → ExecutionGate → `PaperBroker` (シミュレータ) を**live と同じ呼び出し順序**で駆動する
3. 擬似 Broker (PaperBroker の backtest 実装) が発注・約定・決済をシミュレートする
4. 結果 (発注履歴 / 評価指標 / 判断ログ) を一次DB に**live と同じスキーマ**で書き込む (D1 7. の方針に従い `environment=backtest` で区別)

### 1.2 非責務 (Out of Scope for BacktestRunner)

- 戦略パラメータの探索 (これは LearningOps / `training_runs` の責務)
- モデル学習自体 (LearningOps)
- 実ブローカーとの通信 (backtest は Broker 層で PaperBroker を差し替える)
- UI 表示 (Dashboard Query Service の読み先は live/backtest 共通、区別は `environment` で)

### 1.3 Simulation Boundary

**Decision (1.3-1)**: `BacktestRunner` は以下を**自身で持つ**:
- シミュレーション時計 (`sim_clock`)
- `PaperBroker` インスタンス (Broker Interface 実装)
- `market_data_replayer` (時系列順に history を供給)
- `event_bus` (live と同じ EventBus 抽象、in-process 実装)

以下は **live と共通の本番コード**を使う (差し替え禁止):
- Feature Service (6.10 決定性契約)
- StrategyEvaluator (AI / MA / ATR)
- EVEstimator / CostModel
- MetaDecider (Filter / Score / Select)
- PositionSizer / RiskManager
- ExecutionGate
- ExitPolicy
- ModelRegistry (読み取り)

**Inherited Constraint (1.3-2)**: live / backtest で**分岐するロジックを書かない**。切替は Broker Interface と PriceFeed Interface の実装差し替えのみ。条件分岐 (`if backtest: ...`) は禁止。違反は contract test で検出する (D3)。

---

## 2. 対象市場データと時間粒度

### 2.1 入力データソース (D1 B 群)

| テーブル | 用途 | backtest での供給方法 |
|---|---|---|
| `market_candles` | 1m / 5m / 他 tier のロウソク足 | 指定期間を `event_time_utc` 昇順で供給 |
| `market_ticks_or_events` | tick / pricing event | 存在期間分を時系列供給 (欠損は欠損として扱う、補間禁止) |
| `economic_events` | 経済指標カレンダー | 指定期間の予定を時系列供給 |

**Decision (2.1-1)**: backtest 入力は**一次DB の market_* テーブル**から読む。外部 CSV 直読みは不可 (再現性担保のため、事前に ingest して DB に入れる)。

### 2.2 時間粒度

- **主サイクル**: 1m (live と同じ)
- **補助**: 5m (MetaDecider の補助、live と同じ)
- **execution 相当**: tick / pricing event 単位のイベント駆動 (supports ExecutionGate / slippage シミュレーション)

### 2.3 データ欠損の扱い

- `market_candles` の欠損 → 該当 cycle は `data_quality_events(reason_code=candle_missing)` 記録し、当該 instrument は no_trade
- `market_ticks_or_events` の gap → 同上、ExecutionGate で `StaleSignal` 相当の reject
- `economic_events` 欠損 → EventCalendar stale failsafe (6.3) が live と同様に発動 (全 no_trade)

**Inherited Constraint (2.3-1)**: データを**補間しない**。欠損は欠損として扱う (look-ahead bias の温床になるため)。

---

## 3. Feature Availability Rule (Look-Ahead Bias 防止)

### 3.1 基本原則

**Decision (3.1-1)**: ある時刻 `t` の判断に使用可能な特徴量は、**`event_time_utc <= t - data_availability_lag` を満たす行のみ**である。

- `data_availability_lag` は tier 別に定義:
  - 1m candle: 1 分 (足が閉じてから使う、最後の未確定足は使わない)
  - 5m candle: 5 分
  - tick: 実時間到着時点 (遅延なし、ただし live の受信遅延を下記で模擬)
  - economic_events: scheduled_time - 公開ラグ (指標はリリース後にしか使えない)

### 3.2 Backtest 内での強制

Feature Service は `as_of_time: UTC timestamp` を必須引数として受け取る (D3):
- backtest では `sim_clock.now()` を渡す
- live では実際の `now()`
- Feature Service は供給された as_of_time 以降のデータにアクセスしない (契約)

### 3.3 検証

**Decision (3.3-1)**: **contract test** で look-ahead を機械的に検出:
- テストで fixture の market_candles を insert
- 最後の 1 本を「未来データ」として隠し、Feature Service を `as_of_time` < 未来データ時刻 で呼ぶ
- 出力に未来データの影響が出たらテスト失敗
- `feature_hash` が変わった場合は検証 NG

### 3.4 model_version による look-ahead

AI モデルが**未来期間で学習したモデル**を backtest で使う場合も look-ahead bias:
- backtest 期間の終了時刻 > モデルの学習データ終端 を検出、**backtest 実行を拒否**
- `model_registry` に `training_data_end_utc` を記録、BacktestRunner が検証する

---

## 4. Signal / Order / Execution のタイミング

Live と共通の order lifecycle (D3 参照) を、backtest では以下の擬似時計で進める:

| ステップ | live | backtest |
|---|---|---|
| Signal 生成 | 分足 cycle の開始時刻 | 同じ (sim_clock の cycle 境界) |
| EV 計算 | Signal 生成と同時 | 同じ |
| MetaDecision | Signal 全量揃った後 | 同じ (擬似的には瞬時、実時間は 0) |
| trading_signal.created_at | MetaDecider Select 完了時刻 | sim_clock.now() |
| TTL 判定 (6.15) | `now() - created_at > signal_ttl_seconds` | `sim_clock.now() - created_at > signal_ttl_seconds` |
| ExecutionGate | 実 tick データで判定 | 次 tick event (または次 1 秒単位の market_ticks_or_events 行) |
| Broker.place_order | 実 HTTP リクエスト | PaperBroker が次 tick で「約定候補」生成 |
| Fill | transaction stream で非同期到着 | PaperBroker が決定的に模擬 (4.3) |

### 4.1 擬似 Clock (sim_clock)

- 単調増加、巻き戻しなし
- event-driven: 次のイベント (candle close / tick / economic event / internal timer) で時計を進める
- `sim_clock.now()` はアプリ内で time.time() を置換 (live は wall clock)

### 4.2 Cycle Timeout

Live では `cycle_timeout_seconds=45` が設定値。backtest では**シミュレーション時計上は瞬時**だが:
- backtest 実行中の実時間で cycle 処理が 45 秒を超えた場合も、backtest は続行 (実運用遅延と backtest 計算遅延を区別)
- ただし `data_quality_events(reason_code=backtest_cycle_slow)` に記録

### 4.3 Slippage / Spread / Fee / Latency の擬似

`PaperBroker` は発注から約定までを以下で模擬する:

| 要素 | 模擬方式 | 根拠 |
|---|---|---|
| **Spread** | tick データの bid/ask 差分を使用 (実データベース) | 実データに近似 |
| **Slippage** | `slippage_model_name` 設定で切替: `zero` / `fixed_pips` / `volume_based` / `atr_ratio` | 決定的、seed 不要 |
| **Fee (commission)** | `accounts.commission_rate` に基づく定率 | マスタ由来 |
| **Swap** | `CostModel` が holding_time × `swap_rate` で計算 (6.14 継承) | live と同じロジック |
| **Execution latency** | `execution_latency_ms` (固定値、設定で切替) or `execution_latency_distribution` (決定的分布、seed 付き) | seed があれば決定的 |
| **Reject 率** | 実データ由来の spread が設定閾値超なら ExecutionGate で reject (live と同じ、シミュ独自 reject は禁止) | live ロジック共通 |

**Decision (4.3-1)**: slippage と latency はセットで 1 つの「backtest profile」として設定可能:
- `profile=zero`: すべて 0 (理想化、デバッグ用)
- `profile=fixed_conservative`: 0.5 pips slippage + 200ms latency (保守的)
- `profile=stochastic_default`: 決定的分布 + seed 管理

**Inherited Constraint (4.3-2)**: slippage / latency モデルは**独立した Interface** (`SlippageModel` / `LatencyModel`) として D3 で定義、PaperBroker 内部で組み合わせる。live Broker はこれらを使わない (実測値が入る)。

---

## 5. Order State Machine (Backtest 版)

D1 の `orders.status` 状態遷移 (`PENDING → SUBMITTED → FILLED / CANCELED / FAILED`) は live / backtest 共通。backtest 固有の遷移ルール:

### 5.1 PENDING → SUBMITTED

- Live: OutboxProcessor が Broker.place_order 呼出 → HTTP 成功で SUBMITTED
- Backtest: PaperBroker が即座に SUBMITTED (rejectable な条件は ExecutionGate で事前 reject)

### 5.2 SUBMITTED → FILLED

- Live: transaction stream の ORDER_FILL 受信
- Backtest: PaperBroker が以下の決定的ルールで約定判定:
  - `market` order: 次 tick の ask/bid で約定 (long は ask、short は bid) + slippage 加算
  - `limit` order: tick の価格範囲が limit を跨いだ時点で約定 (決定的)
  - SL/TP 付随: position 保有中に tick の low/high が SL/TP を越えた時点で発火

### 5.3 SUBMITTED → CANCELED

- Live: 手動 cancel / expire
- Backtest: 時限 expire (例: IOC 相当) を`order_expiration_seconds` 設定値で模擬

### 5.4 PENDING → FAILED (6.1 タイムアウト)

- Live: `place_order_timeout_seconds=30` 超過で FAILED
- Backtest: シミュ時計上の時限 (設定可能)、通常 backtest では発生させない

### 5.5 Partial Fill の扱い

- Live: transaction stream で部分約定イベント受信
- Backtest: `PaperBroker` が tick 単位で部分約定を生成 (例: 注文サイズ > tick volume → 複数 tick に分割)
- 模擬する・しないは `partial_fill_simulation: bool` 設定で切替、既定は**しない** (単純化、partial fill は Phase 7 以降で有効化)

**Decision (5.5-1)**: MVP backtest では partial fill を**模擬しない**。1 発注 = 1 約定イベント。partial fill の模擬は Phase 7 で optional 追加。

### 5.6 in-flight Order の backtest での扱い (6.1 継承)

Live の safe_stop 発火時の in-flight 扱い (place_order_timeout_seconds まで応答待ち) は backtest では発生しにくいが、**シミュレート可能な形で残す**:
- `sim_safe_stop_event` を backtest シナリオに注入できる (特定 sim_clock 時点で safe_stop を擬似発火)
- その時点で in-flight (PENDING) の orders は 6.1 ルールで処理される
- これにより safe_stop 復旧の contract test を backtest 経由でも実行可能

---

## 6. Account / Balance / Margin / Position の更新規則

### 6.1 Account Snapshot の生成

- Live: event driven (order / fill / close / hourly / daily_close / manual) + 日次クロージング (D1 G 群)
- Backtest: 同じ trigger_reason を**シミュ時計で発火**:
  - `fill`: 約定ごと
  - `close`: 決済ごと
  - `hourly`: sim_clock が hour boundary を越えたとき
  - `daily_close`: 00:00 UTC 境界

### 6.2 Balance / PnL 計算

- 約定ごとに `account_snapshots` に残高を書込
- PnL = 約定価格 - 発注価格 - slippage - commission (long / short 方向による符号反転)
- swap は holding_time に応じて日次クロージで加算

### 6.3 Margin 計算

- `margin_used` = position size × instrument.margin_rate
- `margin_available` = balance - margin_used
- `margin_used / balance > margin_critical_pct (= 0.7 等)` で `risk_events` + no_trade 寄り

**Decision (6.3-1)**: MVP backtest では margin call の実発動 (強制クローズ) は**模擬しない**。margin_critical を超えたら `risk_events` にログし no_trade、ただし既存ポジは維持。margin call 強制クローズの模擬は Phase 7 以降。

### 6.4 Position Snapshots

D1 `positions` の時系列 append 方式は backtest でも同じ。1 約定 / 1 決済 / swap 発生ごとに新行追記。

---

## 7. PnL 算出規則

### 7.1 Realized PnL (決済済)

```
realized_pnl = Σ (close_price - open_price) × size × direction_sign
             - Σ commissions
             - Σ slippage_costs
             + Σ swap_applied (deposits - charges)
```

### 7.2 Unrealized PnL (保有中)

```
unrealized_pnl = Σ (current_tick_price - open_price) × size × direction_sign
               - Σ expected_close_commission (保守的に含める)
               + Σ swap_accrued_so_far
```

### 7.3 Currency Conversion

- `accounts.base_currency` (例: JPY) に変換
- 交差通貨レートは sim_clock の tick データから取得

### 7.4 PnL の記録先

- `account_snapshots.realized_pnl` / `account_snapshots.unrealized_pnl`
- `close_events.realized_pnl` (1 決済あたりの確定 PnL)
- `daily_metrics.pnl_total` (日次 Aggregator 出力)

**Inherited Constraint (7.4-1)**: live と backtest で PnL 計算式は**厳格に同一**であること。環境依存の補正を入れない。

---

## 8. 再現性 (Reproducibility)

### 8.1 決定性契約 (Determinism Contract)

backtest は以下を満たせば**バイト等価**で再現可能:

| 入力 | 内容 |
|---|---|
| `backtest_run_id` | 一意 ID |
| 期間 | `start_utc` / `end_utc` |
| 対象 `instrument` リスト | `InstrumentUniverse` snapshot の明示指定 |
| `feature_version` | 使用する Feature Service 版 (6.10) |
| `model_version` | 使用する active AI model_id |
| `strategy_version` (AI / MA / ATR) | 使用する各戦略版 |
| `meta_strategy_version` | MetaDecider 版 |
| `config_version` | 6.19 で計算される effective config hash |
| `slippage_model` + `latency_model` + seed | シミュレーション決定性 |
| `meta_eval_protocol_version` | 評価プロトコル版 (6.11 反実仮想) |

以上が同一なら**同一出力**が保証される。

### 8.2 Seed 管理

以下の乱数源は**全て seed 可能**にする:
- SlippageModel (stochastic 時)
- LatencyModel (stochastic 時)
- Broker の partial fill 模擬 (Phase 7 拡張時)
- ExperimentTracker の hyperparameter sampler (LearningOps 側)

**Decision (8.2-1)**: seed は `backtest_runs.seed` 列で記録、同 backtest_run_id で再実行すると同値。

### 8.3 Feature Service 決定性 (6.10 継承)

- 同一 (market_candles + economic_events + Common Keys + feature_version) → バイト等価な `feature_hash`
- seed なし / 時刻依存なし / 非決定並列なし (6.10 の禁止事項)

### 8.4 再現不可能な要素の扱い

以下は backtest 決定性を破る可能性があり、**禁止または明示管理**:

| 要素 | 扱い |
|---|---|
| 壁時計 now() | **禁止** (sim_clock のみ使用) |
| OS 依存の浮動小数演算 | JSON canonical 化で抑制、PG numeric 型で丸め統一 |
| 並列処理の順序 | 禁止 (backtest は単一スレッド or 決定的順序) |
| 外部 API 呼出 | 禁止 (market data は DB 由来のみ) |

---

## 9. Walk-Forward / OOS / Embargo

### 9.1 Walk-Forward Validation

- `train_window_days` / `test_window_days` / `step_days` を指定
- 時系列順に window を滑らせ、train → test の fold を生成
- 各 fold の結果を `model_evaluations` に記録、`fold_index` 列付与

### 9.2 Out-Of-Sample (OOS)

- Train 区間と OOS 区間を**明示的に分離**
- OOS 区間のデータで StrategyEvaluator を動かし、結果を Train 区間と比較
- Phase 7 の AIStrategy shadow → active Promotion 判定で使用

### 9.3 Embargo

- Train window 直後の一定期間 (`embargo_days`、初期 3 日) を**評価対象から除外**
- 理由: 学習データのリークが残る可能性があるため
- Embargo 期間は `model_evaluations.embargo_days` に記録

### 9.4 Leakage 検出

以下の leak パターンを **contract test** で検出:

| Leak 種別 | 検出方法 |
|---|---|
| Train / Test 時刻オーバーラップ | 各 fold の時刻範囲を計算、共通部分がないこと |
| 未来データ参照 | Feature Service の as_of_time 強制 + hash 検証 |
| Global normalization | 正規化パラメータが全期間から計算されていないこと (train 内のみ) |

---

## 10. 評価指標 (MVP)

backtest / live の成績は以下の指標で評価 (D5 `daily_metrics` / `strategy_performance` / `meta_strategy_evaluations` に記録):

### 10.1 Return 系

- `return_total` (期間合計損益、base currency)
- `return_annualized`
- `return_per_trade_avg`
- `return_per_strategy` (strategy_type × strategy_version 別)

### 10.2 Risk 系

- `max_drawdown` (絶対額 / %)
- `volatility` (日次リターンの std)
- `sharpe_ratio` (年率化)
- `sortino_ratio` (下方偏差ベース)
- `calmar_ratio` (年率リターン / 最大DD)

### 10.3 Trade Quality 系

- `win_rate`
- `profit_factor` (total_win / total_loss)
- `avg_win` / `avg_loss`
- `ev_prediction_vs_actual_brier` (EV 予測値と実現 PnL の Brier score、EVEstimator 校正の監視)
- `slippage_avg_pips`
- `latency_avg_ms`
- `reject_rate` (ExecutionGate reject / 総発注試行)
- `signal_age_at_execution_avg_seconds` (6.15 TTL 関連)

### 10.4 Operational Stability 系

- `no_trade_rate` (no_trade / (trades + no_trade))
- `no_trade_by_reason_category` (6.16 分布)
- `safe_stop_count` (期間中の発火数、backtest では擬似注入数)
- `degraded_duration_minutes` (backtest では擬似注入)
- `data_quality_event_count`

### 10.5 Meta 系

- `meta_regret` (採用戦略の実績 vs 不採用候補の反実仮想の平均差、6.11 protocol に従う)
- `meta_selection_precision` (Select で採用されたものの事後勝率)

---

## 11. 禁止事項 (Anti-Patterns)

以下は **絶対禁止**、違反は Iteration 1 の contract test で機械的に検出する:

1. **Future leak**: `as_of_time` より未来のデータを特徴量 / 判断に使用
2. **Live / backtest の分岐**: アプリ内で `if backtest: ...` のような条件分岐 (切替は Broker / PriceFeed / Clock の Interface 差し替えのみ)
3. **暗黙補完**: 欠損データを平均値 / 前値 / 線形補間などで埋める (データ品質問題は品質問題としてログするのみ)
4. **現在時刻の使用**: `time.now()` / `datetime.utcnow()` の直接呼出 (sim_clock or Clock Service 経由のみ)
5. **model_version の不一致**: backtest 実行時に使うモデルの学習データ終端 > backtest 開始日 (look-ahead)
6. **seed なし stochastic**: 乱数を使うなら必ず seed 管理下
7. **バッチ処理での先読み**: バックテストバッチが rows を**未来方向に読み込んで**特徴量計算すること
8. **config_version の無視**: 同一 backtest_run_id 内で config が変わる挙動 (設定再読込禁止)
9. **外部 API 呼出**: backtest は閉じた系、OANDA 等への通信禁止

---

## 12. Live Execution Design との整合方針

### 12.1 スキーマ共通化

- 全ログテーブル (42 表 + backtest 追加表) は live / backtest 共通
- 区別は `environment` + `run_id` で判定 (D1 7. 継承)

### 12.2 ロジック共通化

- Feature / Strategy / Meta / Risk / Exit は**同一コード**
- 差分は Broker 層 (OandaBroker / PaperBroker) と Clock 層 (WallClock / SimClock) のみ

### 12.3 Event Bus 共通化

- EventBus は in-process 実装を backtest / single_process_mode で共有
- backtest は実時間非依存に動作 (event の dispatch は sim_clock tick と同期)

### 12.4 Supervisor / Reconciler の扱い

- **Supervisor**: backtest では**無効化** (プロセス健全性は backtest ドライバ側の責務)
- **Reconciler**: backtest では起動時 Reconciler は動作不要 (クリーン状態から開始)。ただし**擬似再起動テスト**を backtest 内で走らせる場合のみ Reconciler が sim_clock ベースで動作

---

## 13. backtest 専用テーブル (D1 Open Question Q2 の解決)

D1 で Open Question として残した `backtest_runs` / `backtest_metrics` を以下で定義する。

**Decision (13-1)**: Phase 6 時点の canonical 42 表には**含めず**、Iteration 1 の Alembic 初期 migration で**追加作成**する (実質 44 表)。D1 の 42 表は Phase 6 時点の**非 backtest** canonical、backtest 関連は D2 固有の拡張とする。

### 13.1 `backtest_runs`

| 項目 | 内容 |
|---|---|
| Purpose | 1 回の backtest 実行単位。paramters + 成果物リンクを保持 |
| PK | `backtest_run_id` |
| Grain | 1 backtest 実行 |
| Update | MUT (status 遷移: `queued` → `running` → `succeeded` / `failed` / `cancelled`) |
| 主要列 (論理) | 期間 (start_utc / end_utc) / universe snapshot / model_version / strategy_version / meta_strategy_version / feature_version / config_version / seed / slippage_profile / latency_profile / fold_index (walk-forward 時) / started_at / finished_at / result_summary_json |
| Retention class | Aggregates (永続) |

### 13.2 `backtest_metrics`

| 項目 | 内容 |
|---|---|
| Purpose | backtest_run ごとの評価指標 (10 章の全指標) |
| PK | `(backtest_run_id, metric_name)` |
| Grain | 1 指標値 |
| Update | AO (同 backtest_run_id を再実行したければ新 backtest_run_id) |
| 主要列 (論理) | metric_name / metric_value / metric_unit / computed_at / aggregator_version |
| Retention class | Aggregates (永続) |

### 13.3 関連 FK

- `training_runs.backtest_validation_run_id` (FK to `backtest_runs`) — 学習後の検証 backtest の紐付け
- `model_evaluations.backtest_run_id` (FK to `backtest_runs`) — shadow evaluation で backtest を使う場合

---

## 14. C2 解消の論点整理

Phase 5 / Phase 6 時点のレビューで **Critical C2 "Backtest Engine の設計不在"** が指摘された項目を、本書でどう解消したかを明示する:

| C2 の論点 | 本書での解消 |
|---|---|
| Phase 7.1 regime tightening の妥当性検証ができない | 13. `backtest_runs` + 10. 評価指標 + 9. Walk-forward により tightening_delta の backtest A/B が可能 |
| Phase 7.2 AIStrategy shadow → active の OOS 判定ができない | 9.2 OOS / 13. `backtest_runs` / `model_evaluations.shadow=true` 連動で、6.11 Promotion 判定基準 (OOS Sharpe / Brier / drift / sample size) が backtest 出力から判定可能 |
| Phase 7.3 CI/CD shadow backtest の自動実行 | 13. の backtest_run_id が CI から kick 可能、D3 `BacktestRunner` Interface が明確なら CI ランナーが orchestration 可 |
| MetaDecider 初期ルール / 数値パラメータの事前検証 | MVP リリース前に短期間の backtest を走らせ、6.5 初期値 (correlation_threshold=0.7 等) の妥当性を事前評価可能 |
| 本番投入される数値がすべて勘 | backtest 結果を根拠に app_settings を調整、変更履歴は `app_settings_changes` |

**Decision (14-1)**: C2 解消は**設計契約の提供**として本 D2 で完了。実 BacktestRunner のコードは Iteration 1 以降で実装。ただし**Interface と責務境界**は本書が単一ソースで確定した。

---

## 15. Open Questions

| ID | 論点 | 解決予定 |
|---|---|---|
| BT-Q1 | `market_ticks_or_events` の backtest 供給 vs 1m candle のみでの近似 (tick データが揃わない期間の運用) | Iteration 1 実装時判断 (MVP は 1m candle 中心、tick は available 期間のみ) |
| BT-Q2 | walk-forward の fold 生成の**並列実行**可否 (単一 backtest_run_id で複数 fold 並列?) | Phase 7 でパフォーマンス要件が明確になってから判断 |
| BT-Q3 | backtest の結果を二次DB マートに流すか | D4 (operations) で検討、MVP は一次DB 参照のみで十分 |
| BT-Q4 | AI モデルの shadow 期間中、live と backtest で同時に shadow 動作させる運用 | Phase 7 着手時点で再考 |

---

## 16. Summary (契約固定点)

本書は以下を**MVP 実装に向けた契約**として固定する:

1. **スキーマは live / backtest 共通** (区別は `environment` + `run_id`)
2. **ロジックは live / backtest 共通** (Broker / Clock 差し替えのみ)
3. **Feature Service は決定性** (6.10 継承)
4. **as_of_time で look-ahead 防止** (アプリ全層で now() 禁止)
5. **PaperBroker の slippage / latency / fee は Interface 分離**、seed 管理で再現性担保
6. **Order state machine は live と同じ** FSM、backtest 固有遷移は擬似注入のみ
7. **評価指標 4 系統 16+ 項目**を全 backtest で計算・記録
8. **backtest_runs / backtest_metrics は Iteration 1 で追加**、42 → 44 表に
9. **look-ahead / live-backtest 分岐 / 暗黙補完 / 壁時計使用は contract test で機械的検出**
10. **C2 はこれで解消**、以降 Phase 7 で実装品質を Iteration 着手条件に組み込む
