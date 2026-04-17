# FX-AI-Trading システム設計書 (統合版 / Phases 0–5)

本書は Phase 0〜5 の仕様を、フェーズ分割ではなく**ひとつの統合設計**として記述するものである。各セクションは「責務 (Responsibilities) / 入力 (Inputs) / 出力 (Outputs) / 失敗パターン (Failure Modes)」を末尾に付す。

---

## 1. System Overview

本システムは、OANDA API を経由して**全FX通貨ペアを 24 時間監視し、機械学習と複数戦略の合議によって「通貨ペア × 戦略」の全候補から期待値の高い取引を選択する短期売買システム**である。初期資金は 30 万円、運用は 24 時間を想定する。運用目標は、リスク調整後リターンの最大化、最大ドローダウンの抑制、no_trade を含む安定運用、そして改善ループによる継続的な性能向上の 4 点であり、このいずれかが欠けるようなアーキテクチャ上の妥協は許容しない。

システムは**ローカル PC / VPS / AWS のいずれの環境でも稼働可能**であり、同一のコアロジックをそのまま動かす。環境差は起動時コンフィグ (`RuntimeProfile`) として吸収し、戦略・判定・執行・学習といったドメイン層には一切漏らさない。運用形態としては **single_process_mode / multi_service_mode / container_ready_mode の 3 モード**を持ち、MVP 段階ではローカルでも VPS でも single_process_mode で稼働させ、負荷・運用要求の増大に応じて multi_service_mode、さらには container_ready_mode へと同一コードのまま段階移行する。

システム全体は**4 つの系統**に分割される。TradingCore が分足粒度で売買判断を行い、ExecutionAssist が秒単位で執行直前の補助検査と発注・約定処理を担当する。LearningOps は学習と評価をバッチで行い、常時稼働はしない。Supervisor はプロセス監視・安全停止・再起動責務を持つ。これらは**垂直方向の責務分割**であり、水平方向には **10 の論理コンポーネント** (Market Data / Feature / Strategy / Meta / Execution / Risk / State / Logging / Sync / Dashboard Query Service) が各系統にまたがって存在する。

**Responsibilities**: 全FX通貨ペアに対する売買判断、執行、約定管理、ポジション管理、リスク管理、学習・改善、可視化、24時間の安定稼働。
**Inputs**: OANDA REST / Streaming API (instruments, candles, pricing, orders, transactions, pricing stream, transaction stream)、経済指標カレンダー、運用者による設定および学習ジョブ起動指示。
**Outputs**: OANDA への発注と決済、一次 PostgreSQL への完全ログ、二次 Supabase 等への集計投影、Streamlit ダッシュボードでの可視化、学習済みモデルとその成績記録。
**Failure Modes**: OANDA API 全面障害 (safe_stop)、一次DB 書込失敗 (Critical tier は safe_stop、Important/Observability は継続)、二次DB 障害 (売買無影響、UI は degraded)、ストリーム断 (再接続、閾値超過で safe_stop)、モデル出力異常 (該当戦略のみ stub fallback)、自プロセス停止 (OS レベル supervisor で再起動 + Reconciler で復元)。

---

## 2. Design Principles

設計の根底にあるのは「**壊れにくさ / 原因調査のしやすさ / 段階的に育てられること**」の 3 点である。この優先順位は機能網羅性や性能を上回り、具体的な設計判断 — たとえば「秒単位処理を主判断に使わない」「学習を常時実行しない」「二次DB に依存して売買しない」「ローカル PC でも動く」といった**重要制約** — のすべての根拠になっている。

**層の分離と外部依存の抽象化**は繰り返し適用される原則である。戦略・判定・執行・発注・保存の各層は Interface で切られ、外部サービス (OANDA / PostgreSQL / Supabase / Slack 等) はすべて差し替え可能な `Broker` / `PriceFeed` / `PersistenceAdapter` / `Notifier` 等の抽象越しにしか触らない。この結果、本番 API 直結の前にモック・ペーパー・テストハーネスで検証できる構造が常に維持される。

**設定のハードコード禁止**は厳格に適用される。APP_ENV / 接続情報 / モデルパス / リスクパラメータはすべて環境変数・設定ファイル・クラウドシークレットの 4 階層から取得され、シークレットは `SecretProvider` を介してのみ参照される。

**ログは分析基盤**として第一級に扱う。デバッグ記録ではなく改善ループの中核であり、取引したケースだけでなく、見送り (no_trade) や却下 (reject) や戦略間比較も全量記録される。記録は Common Keys (run_id / experiment_id / code_version / config_version / model_version / strategy_id / strategy_type / strategy_version / meta_strategy_version / instrument / timestamp) を全テーブル横断で持ち、分析 11 軸 (通貨ペア別比較 / 戦略別比較 / メタ選択精度 / EV 妥当性 / no_trade 効果 / 執行品質 / ドリフト / バージョン比較 / 時間帯別 / close_reason 別 / rejection_reason 別) が 1 本の SQL で書ける粒度を保つ。

**DB は物理リセットしない** (No-Reset)。履歴保持・バージョン単位比較・実験単位比較が可能であることは、改善ループを回すための前提条件であり、スキーマ進化は追加・拡張・expand-contract を基本とする。

**巨大実装を一度に作らない**。Phase 単位で前進し、先に計画、次に最小実装、その後に検証と改善というサイクルで進める。仮実装・モック・スタブを活用して骨格を先に通し、仕様の不足は**拡張可能な設計で吸収**して狭い実装に固定しない。

**Responsibilities**: 設計判断の一貫性担保、技術選定のブレ防止、将来拡張時の方針継承。
**Inputs**: 運用要件、過去の障害経験、業務ドメイン制約 (法的・会計的要件含む)。
**Outputs**: コード規約、アーキテクチャ判断、レビュー基準、禁止事項集。
**Failure Modes**: 原則と実装の乖離 (レビュー・CI で検出)、「例外的にハードコード」が常態化、Interface 設計の形骸化 (直接参照の流入)。

---

## 3. Architecture Overview

アーキテクチャは**垂直 (系統) と水平 (論理コンポーネント) の二軸分解**で成り立つ。垂直方向は責務と駆動サイクルで分けた 4 系統、水平方向は技術的凝集性で切った 10 コンポーネントであり、両者は直交する。実行形態 (single_process / multi_service / container_ready) はこの 10 コンポーネントを**どのプロセス境界で束ねるか**の差にすぎず、論理設計は一切変化しない。

**TradingCore (分足駆動)** は売買判断の中枢である。毎サイクル (1m または 5m) で Market Data Service から最新足を受け、Feature Service が特徴量を構築し、Strategy Engine が AI / MA / ATR の 3 戦略を並列評価して候補シグナルを生成する。Meta Strategy Engine がこれらを Filter → Score → Select の 3 段で合成し、Risk Manager が資金制約と相関制約で最終絞り込みを行い、発注意図 (`trading_signals`) を確定する。

**ExecutionAssist (秒駆動)** は主判断には一切関与しない。分足で確定した発注意図を受け、ExecutionGate が秒単位の現実 (spread / 急変 / stale price / broker 可用性) に照らして `Approve / Reject / Defer` を決め、承認されたもののみ Broker 抽象を介して OANDA へ発注する。約定が返ると Execution Engine が State Manager に反映し、Logging Service が execution_metrics と order_transactions を記録する。

**LearningOps (バッチ駆動)** は TradingCore / ExecutionAssist とは別プロセスとして分離される。常時稼働はせず、手動起動またはスケジュールで `LearningJob` をキックし、一次DB から学習データを取り、walk-forward / OOS を伴う学習と評価を行い、ModelRegistry に成果物を登録する。ModelLifecyclePolicy が版の健全性を定期評価し、ドリフトや OOS 悪化を検知すれば drift_events を発行する。

**Supervisor (常時・軽量)** はプロセス群のヘルス監視、`safe_stop(reason)` の発火、再起動時の Reconciler 起動を担う。Reconciler は一次DB の `app_runtime_state` / `orders` / `positions` / `order_transactions` / `stream_status` を起点に、OANDA 実状態 (positions / pending_orders / recent_transactions) と突合し、不整合があれば安全側に補正する。

この 4 系統に対し、10 コンポーネントは次のように割り付く。Market Data Service は TradingCore と ExecutionAssist の両方が subscribe する共有データソースであり、Feature Service / Strategy Engine / Meta Strategy Engine は TradingCore 内で直列に動く。Execution Engine は ExecutionAssist に閉じ、Risk Manager は TradingCore と ExecutionAssist の境界に立つ。State Manager / Logging Service / Sync Service は**系統横断 (cross-cutting)** で、全系統から参照される。Dashboard Query Service は UI 層の唯一の入口であり、売買系の内部を直接叩くことは禁止されている。

**系統間通信**は `EventBus` と `Transport` の抽象で表現され、single_process_mode では in-process チャンネル、multi_service_mode ではローカルキュー、container_ready_mode ではネットワークメッセージバスが実装として差し込まれる。論理契約は 3 モードで同一であり、モード切替はコードを変えない。

**Responsibilities**: 系統ごとの責務封じ込め、コンポーネント境界の維持、実行モード横断での論理同一性保証、系統横断トレース (cycle_id / correlation_id / order_id) の一貫性。
**Inputs**: 起動時の `RuntimeProfile` (環境 × モード)、各系統の設定、EventBus 実装の選択。
**Outputs**: 稼働中の 4 系統、系統間のイベント流、StateManager に集約された現状、全ログの一次DB 永続化、二次DB への非同期投影。
**Failure Modes**: EventBus 実装障害 (in-process はほぼ無し、ネットワーク版はネットワーク断)、系統間の責務越境 (ExecutionAssist が戦略判断を始める等 — レビューで禁止)、Transport 切替時のメッセージ互換性欠損 (DTO 固定で防ぐ)。

---

## 4. Data Flow

システム内のデータフローは**分足サイクル (主判断) / 秒サイクル (執行補助) / バッチサイクル (学習) / 再起動時復元**の 4 系統に整理される。それぞれの流れは相互に独立しつつ、State Manager と一次DB を共有のランデブーポイントとする。

**分足サイクル**では、毎分または 5 分ごとに cycle_id が一つ発行される。Market Data Service は OANDA から candles と pricing を取得して `market_candles` / `market_ticks_or_events` に記録し、Feature Service がこの生データと補助情報 (通貨強弱、相関マトリクス、セッション、指標カレンダー) から `feature_snapshots` を構築する。Strategy Engine は各 Instrument に対して 3 戦略を並列評価して `strategy_signals` を全量記録する (採否に関わらず全件)。EVEstimator が各シグナルの EV_after_cost と confidence_interval を計算し `ev_breakdowns` に書く。Meta Strategy Engine は Filter 段で市場状況 (spread 過大、セッション外、指標直前、サイズ下限未達等) により候補除外を行い、Score 段で EV・成績・通貨強弱等から合成スコアを計算、Select 段で相関とリスク制約を満たす組合せを選ぶ。各段のスナップショットは `meta_decisions` に、Select 段の明細は `pair_selection_runs` / `pair_selection_scores` に記録される。no_trade と判定された候補は `no_trade_events` に記録され、採用されたものだけが `trading_signals` として ExecutionAssist に渡る。

**秒サイクル**では、ExecutionAssist が Market Data Service の pricing stream と transaction stream を subscribe し続け、trading_signals が届くと ExecutionGate が現実の spread / 急変 / データ鮮度 / broker 接続性を検査する。Approve なら Broker 経由で発注し、この段階で `orders` に記録、client_order_id による冪等化が効く。OANDA から transaction stream で返る約定情報は `order_transactions` に全量記録され、State Manager のポジション状態が更新される一方で `positions` テーブルの時系列にも追記される。発注から約定までのスリッページ・レイテンシ・reject 理由は `execution_metrics` に集約される。ポジション保有中は ExitPolicy が 1m/5m サイクルごとに評価され、TP / SL / 最大保有時間 / reverse / EV 低下 / 指標停止前 / 緊急停止 のいずれかで決済を発火し、`close_events` に発火理由を全列挙で記録する。

**バッチサイクル**は LearningOps の領域である。手動 or スケジュールで `system_jobs` に enqueue された `LearningJob` が起動すると、一次DB の `feature_snapshots` / `strategy_signals` / `ev_breakdowns` / `close_events` / `strategy_performance` を読み、walk-forward と OOS を伴う学習・評価を実行し、`training_runs` / `model_evaluations` / `predictions` / `model_registry` を更新する。LifecyclePolicy が OOS 悪化や drift を検知すると `drift_events` を発火し、該当モデルは Review or Demoted 状態に遷移する。

**再起動時復元**では、Supervisor が起動直後に Reconciler を呼ぶ。Reconciler はまず `app_runtime_state` から前回の graceful stop 時点を読み、`orders` / `positions` / `order_transactions` / `stream_status` で直近の DB 状態を再構築する。次に OANDA から get_positions / get_pending_orders / get_recent_transactions を取得し、DB 状態と突合する。差分は `reconciliation_events` に全量記録され、自動補正範囲を超えるものは degraded モードに遷移して手動判断を待つ。

**系統横断の不変条件**として、分足サイクルで確定した cycle_id は秒サイクルの execution_metrics / orders / fills / close_events まで伝搬され、さらに ev_breakdowns / meta_decisions / risk_events / no_trade_events にも同じ cycle_id が紐づく。correlation_id は 1 発注ライフサイクルを通して維持され、発注 → 約定 → 決済までの一連を 1 本の correlation_id で縫う。

**Responsibilities**: サイクル境界の明示、cycle_id / correlation_id の不変伝搬、各段の記録完全性、サイクル間の疎結合。
**Inputs**: OANDA data、経済指標、前サイクルの state、設定、モデル。
**Outputs**: 一次DB への全量ログ、State Manager のメモリ状態更新、EventBus への StateEvent 発行、二次DB への投影 (非同期)。
**Failure Modes**: サイクル時間超過 (次サイクル開始までに完了できない → ログし skip)、cycle_id 伝搬漏れ (分析が壊れる、レビュー・テストで防ぐ)、Reconciler の誤補正 (degraded で手動待機)、stream ギャップ (data_quality_events に記録、長時間は safe_stop)。

---

## 5. Strategy Layer

戦略層は「**何を監視対象とし、各対象に対してどう判断し、候補群からどれを選ぶか**」の 3 段階で構成される。それぞれが独立した Interface を持ち、並列評価と差し替え可能性が設計上担保されている。

### 5.1 通貨ペア選択 (Universe)

監視対象は **OANDA で取引可能な全 FX 通貨ペア** であり、固定リストは禁止されている。`InstrumentUniverse.list_active()` が OANDA API から動的に取得し、毎サイクルで最新状態を `instruments_snapshot` として記録する。これにより、OANDA 側で取扱停止・追加が発生しても、次サイクル以降は自動追随する。マスタとしての `instruments` テーブルは通貨ペアの属性 (pip 単位、最小ロット、取引時間帯等) を保持し、スナップショットと組み合わせて戦略評価の前提情報となる。

Universe は毎サイクルでフル展開され、約 70 ペア × 3 戦略 = 210 候補/サイクルを生む。この規模に対しては Meta Strategy Engine の Filter 段で軽量な除外を先に行うことが設計上の前提であり、Filter 条件 (spread 過大、セッション外、指標直前、サイズ下限未達) を通過したものだけが Score 段以降の重い計算に進む。

**Responsibilities**: 取引可能通貨ペアの動的把握、毎サイクルの最新反映、戦略評価に必要な属性情報の提供。
**Inputs**: OANDA `instruments` API、instruments マスタ。
**Outputs**: `instruments_snapshot` (毎サイクル)、`InstrumentUniverse.list_active()` の返却。
**Failure Modes**: OANDA instruments API 障害 (直前キャッシュで継続、長時間は degraded)、マスタとスナップショット不整合 (data_quality_events に記録)、大規模な追加・削除の一度の反映 (Meta Filter 段でスパイク防止)。

### 5.2 戦略構造 (AI / MA / ATR)

各通貨ペアに対して、`StrategyEvaluator` Interface を実装した 3 戦略を**並列評価**する。AIStrategy は機械学習モデルに基づく主戦略候補であり、MVP 段階では `AIStrategyStub` として固定 confidence で EV パイプを通過させる空実装で始め、後続で本物に差し替える。MAStrategy は移動平均ベース、ATRStrategy は ATR (Average True Range) ベースの従来型ルール戦略であり、AI が未成熟な段階でも意味のあるベースラインを提供する。

各戦略は同じ出力型 `StrategySignal` を返す。これには signal (long / short / no_trade)、confidence、ev_before_cost、ev_after_cost、tp、sl、holding_time が含まれる。EVEstimator は戦略から独立したコンポーネントで、`{value, confidence_interval}` を返す契約を持ち、MVP は v0 ヒューリスティック (spread に対する固定 P(win) プライア)、将来は過去バックテスト学習 (v1) やオンライン更新 (v2) に差し替える。Cost は CostModel が spread / slippage / commission を個別に供給する。

戦略の追加は `StrategyEvaluator` 実装を追加するだけで並列評価に参加させられる。新戦略は `strategy_id` / `strategy_type` / `strategy_version` の 3 キーで識別され、既存戦略の版更新は `strategy_version` の増加で区別される。この版管理により、コード変更を跨いだ戦略比較が Common Keys だけで可能になる。

**Responsibilities**: 通貨ペアごとのシグナル生成、EV の計算、TP/SL と保有時間の算出、戦略ごとの独立性維持。
**Inputs**: `FeatureSet` (Feature Service 出力)、市場 context、CostModel、モデル (AI のみ)。
**Outputs**: 全候補の `StrategySignal` を `strategy_signals` に全量書き込み、EV 内訳を `ev_breakdowns` に書き込み、AI の推論結果は `predictions` にも記録。
**Failure Modes**: モデル推論失敗 (AI は Stub へフォールバック、他戦略は影響なし)、特徴量欠損 (該当ペア・戦略は no_trade、data_quality_events に記録)、EV 信頼区間が過大 (MetaDecider で no_trade 寄りに重み付け)、戦略間で計算時間に大差 (並列評価の timeout 契約)。

### 5.3 メタ戦略 (Filter → Score → Select)

メタ戦略は「**どの通貨ペアで、どの戦略を採用するか**」を決める上位判断層であり、3 段構成を取る。MVP は全段ルールベースで実装し、`MetaDecider` Interface として契約化することで、後続の Score / Select を学習モデルに差し替えることができる。

**Filter 段**は軽量な除外フィルタで、spread 過大、セッション外、指標直前 (高インパクト経済指標の N 分前)、ポジションサイズ下限未満、ブローカー接続不良といった条件で候補を落とす。全通貨ペアの全戦略をここで絞り込むことで、後段の計算コストを抑える。

**Score 段**は残った候補に対してルール合成スコアを計算する。入力には EV_after_cost、confidence、戦略別成績 (過去 N 日の勝率と PnL)、時間帯スコア、通貨強弱、相関状況、市場状態が含まれ、各要素に重みを掛けた合成値を出す。初期はルールベースだが、重みの自動チューニングや完全な学習モデル化への差し替え余地を Interface で残す。

**Select 段**は Score 上位候補から、Risk Manager 制約を満たす組合せを選ぶ。同一通貨への偏重、相関閾値を超えるペアの同方向同時保有、同時ポジション数上限、総リスク (相関調整後) 上限を全て満たす最適組合せを探し、最終的に `MetaDecision` (selected_instrument / selected_strategy / selected_signal / selected_tp / selected_sl / no_trade) を出す。Select 段の明細は `pair_selection_runs` / `pair_selection_scores` に記録され、Score / Filter の集約スナップショットは `meta_decisions` に記録される。

メタ戦略自体もバージョン管理され、`meta_strategy_version` が全ログに付与される。選択の妥当性は後日 `meta_strategy_evaluations` で事後評価され、「採用戦略の事後成績 vs 不採用戦略の反実仮想評価」として比較分析される (regret 分析)。

**Responsibilities**: 複数候補の合議的選択、リスク制約下での組合せ最適化、選択理由の透明化と事後検証可能性の確保。
**Inputs**: 全 `StrategySignal`、MarketState、通貨強弱、相関マトリクス、セッション、EventCalendar、戦略別成績、現在エクスポージャ。
**Outputs**: `MetaDecision`、3 段の詳細記録 (`meta_decisions` / `pair_selection_runs` / `pair_selection_scores`)、no_trade 候補の `no_trade_events` 記録。
**Failure Modes**: 全候補が Filter で落ちる (no_trade、ログのみ)、Score 計算中の入力欠損 (当該候補のみ除外)、Select で Risk 制約を満たす組合せなし (no_trade)、ルール爆発による保守困難 (3 段分離で局所化)、反実仮想評価の重さ (バッチ化で UI ブロック回避)。

---

## 6. Execution Layer

執行層は、メタ戦略が確定した発注意図 (`trading_signals`) を**実際の発注と決済**に変換する。分足と秒単位の二層で責務を分け、秒単位処理を主判断に使わない原則を構造的に担保する。

### 6.1 分足判断 (TradingCore 側の執行責務)

分足層では、MetaDecision を受けて Risk Manager が最終受理を行い、trading_signals を発行する。ここでは PositionSizer が資金・リスク率 (1〜2%)・SL 幅・pip 価値から適正ロットを計算する。最小ロット未満となった場合は `no_trade(reason=SizeUnderMin)` として記録し、小資金運用でもパイプ全体が回ることを担保する。

Risk Manager の `accept(decision, exposure)` では、同時ポジション数、単一通貨エクスポージャ、総リスク (相関調整後)、相関閾値超ペアの同方向同時保有禁止を順に検査する。ここで reject されたものは `risk_events` に理由付きで記録され、no_trade となる。

分足層はまた、保有ポジションに対する `ExitPolicy` 評価も担う。毎サイクルで各保有ポジションについて、緊急停止 > 指標停止前 > SL > TP > reverse signal > EV 低下 > 最大保有時間 の優先度で評価し、発火理由を全列挙して `close_events` に記録する。実際の決済発注は ExecutionAssist が実行する。

**Responsibilities**: 発注意図の生成、ポジションサイジング、リスク制約の適用、決済判断。
**Inputs**: MetaDecision、現在エクスポージャ、現在残高 (account_snapshots)、相関マトリクス、保有ポジション。
**Outputs**: `trading_signals`、`risk_events`、`close_events` (decision 部分)。
**Failure Modes**: サイジング計算で最小ロット未達 (no_trade)、Risk accept 拒否 (no_trade)、ExitPolicy 優先度競合 (全列挙で記録、最優先を実行)、ExitPolicy 発火と新規発注が競合 (既存決済優先)。

### 6.2 秒監視 (ExecutionAssist / ExecutionGate)

秒単位層は**主判断を一切行わない**。責務は spread チェック、急変回避、entry guard (stale price / 不整合検出)、約定確認、異常検知の 5 つに限定される。

`ExecutionGate.check(intent, realtime_context)` が秒単位の最終ゲートとなり、入力 trading_signal と直近の pricing / spread / broker 可用性を照らし合わせ、`Approve` / `Reject(reason)` / `Defer(wait)` を返す。Reject 理由は列挙型で固定化され (`SpreadTooWide` / `SuddenMove` / `StaleSignal` / `BrokerUnreachable` / `MarketClosed` / `RiskLimitExceeded` 等)、すべて `execution_metrics` に記録される。Defer は一定時間再評価待ちであり、時限切れで Reject に遷移する。

Approve されたものだけが `Broker.place_order()` を経て OANDA に送られる。発注は client_order_id による**冪等化**が必須であり、`client_order_id = f"{cycle_id}:{instrument}:{strategy_id}:{monotonic_seq}"` の形式で一意性を保つ。これにより再送による二重発注が構造的に防がれる。発注成功は `orders` テーブルに記録され、OANDA の transaction stream から返る約定情報は `order_transactions` に全量記録される。約定が `fills` 部分として実体化され、`positions` 時系列が更新される。

RateLimiter はすべての OANDA API 呼び出しの前段に立ち、エンドポイント別バケットでバースト抑制を行う。Retry Policy との合成契約は「**RateLimiter は RetryPolicy の前段、トークン消費後に実行、失敗時の再試行待機は RetryPolicy + Backoff に一元化**」である。全リトライは `retry_events` (系統によっては `execution_metrics` と `data_quality_events`) に記録される。

**Responsibilities**: 発注直前のゲーティング、発注の冪等化、約定反映、秒単位の異常検知、broker I/O の抽象化。
**Inputs**: `trading_signals`、pricing stream、transaction stream、spread / broker 状態、RateLimiter トークン。
**Outputs**: 発注結果 (`orders`)、約定 (`order_transactions` / `fills`)、ポジション更新 (`positions`)、実行品質 (`execution_metrics`)、StateEvent。
**Failure Modes**: OANDA タイムアウト (Retry、閾値超で degraded)、注文拒否 (再送せず reason 記録、同一理由連続で cooldown)、stream 切断 (即再接続、長期不可で safe_stop)、transaction 不整合 (Reconciler 発火)、冪等キー衝突 (例外、ログ、Meta に再評価戻し)、Defer の時限切れ連発 (Meta の閾値見直しトリガ)。

---

## 7. Data Layer

データ層は **正本とする一次 DB / 参照専用の二次 DB / それらを束ねる PersistenceAdapter** の 3 層構成である。売買判断・注文・約定・ポジション・リスク状態・完全ログはすべて一次 DB に保持され、売買のクリティカルパスは一次 DB だけで完結する。これは Phase 0 から一貫する不変条件であり、二次 DB 障害で売買が停止することは設計上あってはならない。

### 7.1 一次 DB (PostgreSQL)

一次 DB は **PostgreSQL** を正式採用する。ローカル PC でもローカル PostgreSQL を基本とし、VPS・AWS へ移行する際には接続情報の変更だけで済む構造を維持する。開発初期に限り SQLite を許容するが、**論理設計は常に PostgreSQL 前提**であり、SQLite 利用時は JSONB が TEXT に、パーティショニングが未使用に、並行書込が single writer 前提に落ちるといった制約を受け入れる。SQLite の利用範囲は `single_process_mode × local` の組合せに限定し、それ以外は PostgreSQL 必須である。

一次 DB は**物理リセットしない** (No-Reset) 原則で運用される。本番・準本番はもちろん、学習・分析のためにバージョン単位・実験単位の比較が必要な以上、データ破棄は原則禁止である。スキーマ進化は列追加を基本とし、破壊的変更が必要な場合は新テーブル + View 切替の expand-contract 手順で行う。マイグレーションは **Alembic** で履歴管理され、すべて git 配下に置かれる。

テーブル群は 9 グループ・計 34 テーブルで構成される。Config/Reference (`brokers` / `accounts` / `instruments` / `app_settings`)、Market Data (`market_candles` / `market_ticks_or_events` / `economic_events`)、Learning/Models (`training_runs` / `model_registry` / `model_evaluations` / `predictions`)、Decision Pipeline (`strategy_signals` / `pair_selection_runs` / `pair_selection_scores` / `meta_decisions` / `feature_snapshots` / `ev_breakdowns`)、Execution (`trading_signals` / `orders` / `order_transactions` / `positions`)、Outcome (`close_events` / `execution_metrics`)、Safety & Observability (`no_trade_events` / `drift_events` / `account_snapshots` / `risk_events` / `stream_status` / `data_quality_events`)、Aggregates (`strategy_performance` / `meta_strategy_evaluations` / `daily_metrics`)、Operations (`system_jobs` / `app_runtime_state`) である。これらのテーブルにはすべて Common Keys (run_id / experiment_id / environment / code_version / config_version / model_version / strategy_id / strategy_type / strategy_version / meta_strategy_version / instrument / timestamp) が横断付与される。

Phase 1 / Phase 3 で言及された既存名称 (`intents`, `fills`, `exits`, `exit_decisions`, `execution_gates`, `features`, `ev_decompositions`, `risk_evaluations`, `candles_1m`/`_5m`, `events_calendar`, `no_trade_evaluations`, `anomalies`, `reconciliation_events`, `supervisor_events`, `learning_jobs`, `experiments`) は**いずれも削除されず**、Phase 4 の新名称で物理表を作る場合は旧名称を View で保全する方針をとる。

`signal と order の分離` / `order と position の分離` は物理設計レベルで守られる。`strategy_signals` は判断候補の記録、`trading_signals` は採用された発注意図、`orders` は実発注レコード、`order_transactions` は OANDA transaction stream の全イベント、`positions` はポジション状態の時系列である。この多層化は、**取引したものだけでなく見送ったもの・却下したもの・戦略比較結果**までを構造的に残すための設計である。

**Responsibilities**: 正本保持、売買クリティカルパスの完結、完全ログ、バージョン跨ぎ比較の可能性、再起動時の状態復元源。
**Inputs**: 全系統からの書込、Alembic マイグレーション。
**Outputs**: 読み取り (アプリ / Aggregator / SecondaryProjector / Dashboard Query Service フォールバック)、バックアップ対象の永続データ。
**Failure Modes**: 書込失敗 (Critical tier は safe_stop、Important は at-least-once 再試行、Observability は best-effort でドロップ可)、スキーマ不整合 (Alembic revision 不一致で起動拒否)、ストレージ満杯 (retention とアーカイブで防ぐ)、SQLite → PostgreSQL 切替時の型差 (PersistenceAdapter で吸収)。

### 7.2 二次 DB (Supabase 等)

二次 DB は **Supabase 等のクラウド DB** を採用し、**参照専用**として扱う。ダッシュボード / 改善レビュー / 外部閲覧用途に供され、売買系は読み書きしない。一次 DB からは `SecondaryProjector` が**非同期**で投影し、遅延許容は数秒〜数分 (RPO は UI 用途前提、SLO は後続フェーズで確定)。

二次 DB の主要マートは 8 + 1 である。Phase 3/4 で定義された `dashboard_market_state` / `dashboard_strategy_summary` / `dashboard_selected_signals` / `dashboard_positions` / `dashboard_execution_quality` / `dashboard_daily_metrics` / `dashboard_risk_status` / `dashboard_meta_strategy_eval` に加え、Phase 5 で `dashboard_top_candidates` が追加される。`dashboard_market_state` には Trade Suitability Score (TSS, 0-100) と内訳 (`tss_components` JSONB) が列追加される。

二次 DB 障害時の振る舞いは厳格に定義される。**売買系は完全無影響**、UI は degraded モードバナーを表示して一次 DB RO View にフォールバック、両方不可なら offline モードでキャッシュ最終値のみ表示する。一次 RO フォールバック時は、売買系とは**別ユーザ・別接続プール**を使うことで、売買系の接続を食わない構造にする。

**Responsibilities**: ダッシュボード用の軽量参照データ供給、売買系からの完全分離、UI のための低レイテンシ読み取り。
**Inputs**: `SecondaryProjector` 経由の一次 DB イベント流。
**Outputs**: 8 + 1 マートの常時更新された投影データ、UI クエリへの応答。
**Failure Modes**: 二次 DB 接続断 (UI は degraded、売買無影響)、Projector 遅延 (UI に `last_data_at` 表示で可視化)、投影データ不整合 (一次 DB を正本として再生成可能)、Supabase 固有のレート制限超過 (UI polling 制御で防ぐ)。

### 7.3 Persistence 抽象化と ORM

アプリケーションは `Repository` Interface を通してのみ DB にアクセスし、SQL 実体は `PersistenceAdapter` (SQLAlchemy ベース) に閉じ込められる。Repository はドメイン CRUD を担当し、分析クエリは別層の Direct SQL として `docs/analytics_queries.md` で管理される。この二層化により、ドメイン操作の型安全性と分析クエリの柔軟性を両立する。

Common Keys / cycle_id / correlation_id / order_id は Repository 層で自動伝搬する仕組みを持たせ、アプリケーションコードから書き忘れないようにする。同様に `code_version` / `config_version` はビルド時および起動時に自動注入される。

**Responsibilities**: DB アクセスの抽象化、SQL 詳細の封じ込め、Common Keys の自動付与、マイグレーションの統一管理。
**Inputs**: ドメインオブジェクト、クエリ要求、Alembic revision。
**Outputs**: Repository 越しの CRUD、分析クエリ結果、マイグレーション履歴。
**Failure Modes**: 型ミスマッチ (SQLAlchemy モデル不一致で起動失敗)、トランザクション境界誤り (Critical tier 書込で致命)、Repository 迂回 (レビューで禁止)。

---

## 8. Logging & Observability

ログは**デバッグ記録ではなく、改善ループの中核となる分析基盤**として第一級に扱われる。取引したケースだけでなく、見送り (no_trade)、却下 (reject)、戦略間比較までを全量記録することで、「なぜその判断に至ったか」「なぜその判断をしなかったか」「別戦略ならどうだったか」のすべてが後から完全に再構築できる。

### 8.1 Common Keys

全ログテーブルには Common Keys (run_id / experiment_id / environment / code_version / config_version / model_version / strategy_id / strategy_type / strategy_version / meta_strategy_version / instrument / timestamp) が必須列として付与される。加えて cycle_id / correlation_id / order_id が系統横断トレースに使われる。

`code_version` はビルド時の git SHA 埋込で、`config_version` は起動時の設定ハッシュ計算で自動注入される。`strategy_version` は戦略モジュール単位の版管理であり、コード変更を跨いだ比較を可能にする。タイムスタンプは `event_time_utc` (UTC epoch ms) と `event_wall_time` (ISO8601 TZ 付) の両方を保持し、受信系は `received_at_utc` も別列に持つことで clock skew 下でも分析が破綻しないようにする。

### 8.2 一次 DB の詳細ログ (12 カテゴリ)

一次 DB には以下 12 カテゴリの詳細ログが全量保存される: `strategy_signals` (全候補)、`meta_decisions` (3 段判断)、`feature_snapshots` (特徴量)、`ev_breakdowns` (EV 分解)、`execution_metrics` (発注品質)、`close_events` (決済理由)、`no_trade_events` (見送り)、`drift_events` (モデルドリフト)、`strategy_performance` (戦略別ロールアップ)、`meta_strategy_evaluations` (メタ戦略の選択精度、反実仮想含む)、`daily_metrics` (日次 KPI)、`data_quality_events` (入力データ品質)。

### 8.3 二次 DB の投影 (8 + 1 マート)

二次 DB には軽量な投影が 8 + 1 マート置かれる (Data Layer 7.2 参照)。UI はこれらを参照するのが基本で、二次 DB 不可時のみ一次 RO View にフォールバックする。

### 8.4 分析 11 軸

ログ設計は**次の 11 軸の分析クエリが 1 本の SQL で書ける**粒度を保証する: 通貨ペア別比較 / 戦略別比較 / メタ戦略の選択精度評価 / EV 妥当性分析 / no_trade 効果分析 / 執行品質分析 / ドリフト分析 / バージョン比較 / 時間帯別分析 / close_reason 別分析 / rejection_reason 別分析。

### 8.5 Criticality Tier とログ失敗時原則

ログは重要度別に 3 Tier で扱われる。**Critical tier** (`orders` / `order_transactions` / `fills` / `close_events` / reconciliation / safe_stop 記録) は**同期書込** (トランザクション commit で書込成功) で、書込失敗は**売買を安全側に倒す** (safe_stop 含む)。**Important tier** (`strategy_signals` / `meta_decisions` / `ev_breakdowns` / `execution_metrics` / 採用直結の `no_trade_events` / 異常系の `data_quality_events`) は at-least-once の非同期書込で、失敗はログ化するが**売買は継続**する。**Observability tier** (`feature_snapshots` / 要約 `no_trade_events` / `drift_events` / `strategy_performance` / `meta_strategy_evaluations` / `daily_metrics`) は best-effort + サンプリングで、キュー溢れは古いものから捨てる。

この Tier 契約により、仕様原文の「**ログ保存失敗が売買処理の致命停止要因にならない**。ただし一次 DB への**重要状態**保存失敗は安全側に倒れる」が矛盾なく実装される。

### 8.6 ログ量制御と retention

ログは **Hot / Warm / Cold** の階層で保存される。直近 N 時間は Hot テーブル、日次パーティションで Warm、N 日超は Cold アーカイブ (将来 S3 等) へ移される。`feature_snapshots` のように大容量になるテーブルは `compact_mode` (生配列 → ハッシュ + 統計量要約) を用意して長期保持する。`no_trade_events` は要約 + サンプリング保存を既定とし、異常近辺は全量という**条件付き全量保存**を設定で切替可能とする。`strategy_signals` には `retention_class` 列を持たせ、no_trade 多数時はサンプリングに寄せる運用を可能にする。

### 8.7 PII / Secret マスキング

API key / トークン / account_id 等の機微情報は、ログ書込前に `LogSanitizer` を通し、ブラックリストフィールドをハッシュ化または固定マスクする。Supabase anon key と service key は用途別に分離し、UI プロセスは RO 権限の別 key しか触らない。

**Responsibilities**: 全判断の事後再構築可能性、分析クエリの高速化、書込失敗時の安全契約、機微情報の保護。
**Inputs**: 全系統からのログイベント、Common Keys 自動付与、Criticality Tier 判定。
**Outputs**: 一次 DB への構造化ログ、二次 DB への投影、retention 処理後のアーカイブ。
**Failure Modes**: Critical 書込失敗 (safe_stop)、Important キュー溢れ (警告発報、継続)、Observability ドロップ (サンプリング継続)、retention 誤設定 (保持期間逸脱を監視)、機微情報流出 (Sanitizer 必須、レビュー)。

---

## 9. Learning & Training

学習系統は **LearningOps** として他系統から完全に分離され、**常時実行しない**原則のもとで動く。手動起動またはスケジュールバッチで `LearningJob` を `system_jobs` に enqueue し、実行中は TradingCore / ExecutionAssist に影響を与えない。

学習の入力は一次 DB から取得される。`feature_snapshots` / `strategy_signals` / `ev_breakdowns` / `close_events` / `strategy_performance` が主なデータソースで、Common Keys による条件絞り込みで「特定バージョン範囲 / 特定通貨ペア / 特定期間」の学習データを再現性高く取り出せる。

**モデル / 実験管理**は 3 層で行う。`ModelRegistry` がモデルの保存・読み込み・昇格・降格を Interface として抽象化し、`ExperimentTracker` が実験 ID (`experiment_id`) ごとにパラメータとメトリクスを記録し、`ModelLifecyclePolicy` がアクティブ / レビュー / ディモートの状態遷移を管理する。`training_runs` / `model_registry` / `model_evaluations` / `predictions` テーブルがこの 3 層の永続化を担う。

**過学習対策**は仕様レベルで義務付けられる。Walk-forward validation で時系列に沿った検証を行い、Out-Of-Sample (OOS) データで未見領域の成績を測り、試行回数制限 (同一実験内のハイパラ探索上限) を `ExperimentTracker` レベルで強制する。モデル寿命管理は MaxAgeDays + OOSDegradationThreshold を MVP の判定基準とし、ドリフト検出 (PSI / KL ダイバージェンス / 残差ドリフト) は後続で追加する。ドリフト発火は `drift_events` に記録され、該当モデルは Review or Demoted 状態に遷移する。

**学習 UI** はダッシュボード内に最小機能で提供される。対象選択 (通貨ペア × 戦略)、期間指定、実行方法 (手動 / スケジュール登録)、実行状態確認、履歴確認を UI から行える。UI は LearningOps のジョブキュー (`system_jobs`) に enqueue するだけで、実計算は別系統で走る。進捗は一次 DB 経由で可視化される。

ロールアップ (`strategy_performance` / `meta_strategy_evaluations` / `daily_metrics`) は **Aggregator** という独立バッチで生成される。Aggregator は冪等 (同入力で同出力) を契約化され、バージョン遡及分析に対応する。`meta_strategy_evaluations` の反実仮想計算は重い処理だが、UI には**参照のみ**を提供することで 5-10 秒更新の制約を守る。反実仮想プロトコルは版管理され、`meta_eval_protocol_version` を Common Keys の一部として扱う。

**Responsibilities**: 学習の再現性、過学習抑制、モデル版と実験の追跡、ライフサイクル管理、UI からの操作経路提供。
**Inputs**: 一次 DB の特徴量・シグナル・決済ログ、ハイパラ、学習設定、ユーザの enqueue 指示。
**Outputs**: 学習済みモデル (ModelRegistry)、`training_runs` / `model_evaluations` / `predictions` / `drift_events`、アクティブモデルの版更新、ロールアップテーブル更新。
**Failure Modes**: 学習時間超過 (ジョブ tmo、リトライ or 手動)、OOS 悪化 (Review 遷移、自動ディモート)、ドリフト検出 (drift_events、再学習トリガ)、反実仮想の計算重 (バッチ化で UI ブロック回避)、学習データ不足 (警告、継続)。

---

## 10. Risk Management

リスク管理は**ポジションサイジング / エクスポージャ集計 / 総リスク制御 / 相関制御**の 4 要素で構成され、`PositionSizer` と `RiskManager` の 2 つの Interface に集約される。

**PositionSizer** は、資金・リスク率 (1〜2%)・SL 幅・pip 価値からロットを計算する。最小ロット未満となったケースは `no_trade(reason=SizeUnderMin)` として必ずログに残し、小資金運用でも判断パイプ全体が回ることを担保する。この挙動により、30 万円の初期資金でも pip 価値の高い特定通貨ペアが取引可能対象として自然に絞り込まれる。

**RiskManager** の `accept(decision, exposure)` は、以下を順に検査する。同時ポジション数上限 N、単一通貨エクスポージャ上限 (通貨別ロング / ショート合計)、総リスク上限 (全ポジションの最大損失合計、相関調整後)、相関閾値超ペアの同方向同時保有禁止。これら全てを満たさない MetaDecision は reject され、`risk_events` に理由付きで記録される。

**Exposure** は明示的なドメインオブジェクトとして保持される。通貨別エクスポージャ、総リスク、相関調整後リスクを常時計算し、MetaDecider の Select 段に入力として渡される。これにより、Select 段自身が Risk 制約を満たす組合せ選択を行えるため、Meta と Risk の責務境界が滑らかになる。

**相関制御**は `CorrelationMatrix` (Phase 1) と `PairGraph` で表現される。ローリング計算で直近の相関を保持し、相関閾値を超えるペアの同方向同時保有を制約する。将来は相関の動的変化 (regime change) を監視する機能を追加する拡張点を残す。

**account_snapshots** は残高・有効証拠金・PnL のスナップショットで、イベント駆動 (発注 / 約定 / 決済 / 手動 kick) + 日次クロージングの複合で取得される。この履歴がリスク判定の裏付けとなり、バージョン跨ぎ分析でも資金推移が追跡できる。

**リスク停止の上位判断**としては、`Supervisor.safe_stop(reason)` が最終手段として存在する。新規発注停止 + 既存ポジションは ExitPolicy に従う (または全クローズ指示)。発火理由には「24時間の総損失が閾値超」「連続損失がN回超」「stream 長時間断」「DB Critical 書込失敗」等があり、すべて `supervisor_events` に記録される。

**Responsibilities**: ポジションサイジング、エクスポージャ集計、総リスク・相関・同時ポジ制約の適用、資金推移の記録、致命的事象での安全停止。
**Inputs**: MetaDecision、現在残高、保有ポジション、相関マトリクス、設定 (リスク%・上限値)、Supervisor からの safe_stop 指示。
**Outputs**: `risk_events` (accept / reject)、`account_snapshots`、RiskManager.accept() の結果、Meta Select への Exposure 提供、`supervisor_events` (safe_stop)。
**Failure Modes**: 残高取得失敗 (直前値で継続、data_quality_events に記録、継続失敗で degraded)、エクスポージャ集計の不整合 (Reconciler 発火)、相関行列の計算遅延 (直前値で継続)、サイズ計算の境界値 (SizeUnderMin で no_trade)、safe_stop 誤発火 (閾値監視と手動オーバーライドで対応)。

---

## 11. Failure Handling

失敗処理は**分類された事象ごとのリトライ方針 / レート制限 / 再起動時の整合回復 / 致命時の安全停止 / ログ失敗契約**の 5 本柱で構成される。個別処理の例外ハンドリングではなく、**システムレベルの失敗モードごとに設計上の挙動が決まっている**点が特徴である。

### 11.1 事象別リトライポリシー

OANDA API 一時失敗 (5xx / timeout) は exponential backoff + jitter で再試行し、`RetryExhausted` に達すれば degraded モードに落ちる。ネットワーク断は接続再確立を exponential capped でリトライし、長期断なら safe_stop。注文拒否 (broker reject) は**再送しない**。reason を記録して Meta に再評価を戻し、同一理由連続で cooldown を挟む。接続タイムアウトは exponential で再試行しつつ route 切替 (将来) を検討、閾値超で degraded。Stream 切断は即再接続 (linear → exponential)、ギャップ期間を `stream_status` / `data_quality_events` に記録、長期不可で safe_stop。Stale price (過齢データ) はリトライせず ExecutionGate で Reject する。Transaction 不整合はリトライせず Reconciler 発火、解消不可で safe_stop。

共通の `RetryPolicy { max_attempts, base_delay, max_delay, jitter, retry_on: [...] }` Interface を持ち、全リトライは `retry_events` (または相当ログ) に記録される。

### 11.2 RateLimiter

`RateLimiter` は token bucket 実装を標準とし、OANDA REST / Streaming の上限に合わせてエンドポイント別バケットに分割される。RetryPolicy との合成順序は「**RateLimiter は RetryPolicy の前段**、トークン消費後に実行。失敗時の再試行待機は RetryPolicy + Backoff に一元化」であり、これによりフィードバックループ (リトライ → バースト → throttle → 長い backoff → さらにリトライ) を構造的に防ぐ。超過時は queue に退避し、売買クリティカル優先度付きで処理、ログ等の低優先はドロップ可。

### 11.3 Reconciler (再起動耐性)

起動時に Supervisor が Reconciler を呼ぶ。Reconciler は `app_runtime_state` で前回の graceful stop 時点を読み、`orders` / `positions` / `order_transactions` / `stream_status` で直近の DB 状態を再構築する。次に OANDA から `get_positions()` / `get_pending_orders()` / `get_recent_transactions()` を取得し、両者を突合する。一致していればそのまま稼働、不整合があれば**安全側に補正**する。DB 未記録の実ポジは検出・ログして以後は監視のみ (自動クローズ禁止、手動判断)、DB 記録にない過去注文は `unknown` ステータスで記録する。補正内容はすべて `reconciliation_events` に記録される。自動補正範囲を超える場合は degraded に遷移し、新規発注停止 + 既存ポジは通常 ExitPolicy で手動判断を待つ。

### 11.4 Supervisor と safe_stop

Supervisor は常時・軽量で動き、プロセス・接続・DB・ストリーム・リスクを監視する。致命的事象 (24h 総損失超過、連続損失超過、長期 stream 断、Critical 書込失敗、OANDA API 全面障害) を検知すると `safe_stop(reason)` を発火し、新規発注停止 + 既存ポジションは ExitPolicy に従う (または設定で全クローズ指示)。安全停止状態 (`safe-stop`) はダッシュボードに明示表示され、手動での復帰判断を待つ。

`single_process_mode` では OS レベルの Supervisor (systemd / nssm / launchd) に**プロセス再起動を委ね**、アプリ自前の Supervisor は論理的な安全停止判定に集中する。`multi_service_mode` / `container_ready_mode` では同様に OS / オーケストレータがプロセス生存を保証する。

### 11.5 ログ失敗時原則 (Section 8.5 再掲の契約面)

Critical tier の書込失敗は売買を安全側に倒す (safe_stop 含む)。Important tier の書込失敗は at-least-once 再試行で対処し、売買は継続。Observability tier の書込失敗はドロップ可 (サンプリング継続)。この契約により、ログインフラの健全性要求を重要度別に現実的な範囲に収めつつ、**ログ保存失敗そのものでは売買を止めない**原則と、**重要状態保存失敗は止める**原則が両立する。

### 11.6 データ品質と異常検知

`data_quality_events` は入力データの品質異常 (stale price / 欠損 / ギャップ / 型異常 / transaction 不整合) を専用で記録する。`anomalies` (アプリ一般異常) / `reconciliation_events` (突合専用) と**3 系独立テーブル**で重複を避ける。これら 3 系は `correlation_id` で JOIN して横断分析可能とする。

**Responsibilities**: 事象分類ごとの挙動確定、リトライ過剰の防止、再起動時の状態回復、致命時の安全停止、ログ失敗時の売買継続/停止の判定。
**Inputs**: 全系統からのエラーイベント、外部 API 応答、stream 接続状態、残高推移、手動 kick。
**Outputs**: `retry_events`、`reconciliation_events`、`data_quality_events`、`anomalies`、`supervisor_events`、safe_stop 状態遷移、degraded モード宣言。
**Failure Modes**: Supervisor 自身の停止 (OS レベル supervisor で再起動)、Reconciler の誤判定 (degraded で手動待機)、safe_stop の頻発 (閾値再設定と運用ルール)、Retry の無限ループ (max_attempts で停止)、RateLimiter と Retry の合成破綻 (順序契約で防ぐ)。

---

## 12. MVP Scope

MVP は「**Phase 0〜5 の契約を全て守った上で、最小の実装で全パイプラインが通る状態**」と定義される。ここで作らないものも多いが、**Interface レベルでは全てが確保**されており、後続で個別実装を差し替える形で育てる。

### 12.1 MVP に含むもの

**OANDA 接続**として `OandaBroker` を実装し、instruments / candles / pricing / orders / transactions / pricing stream / transaction stream の 8 API を全て使える状態にする。`InstrumentUniverse.list_active()` から動的に通貨ペアを取得する。

**一次 DB (PostgreSQL) 初版スキーマ**を構築する。Section 7.1 の 9 グループ・34 テーブルを Alembic で作成し、Common Keys を全テーブルに付与する。Phase 1 / 3 の既存名との View エイリアスも張る。

**戦略実装**は `MAStrategy` / `ATRStrategy` を本実装、`AIStrategyStub` を固定 confidence でダミー実装する。EVEstimator は v0 (ヒューリスティック) を使う。

**MetaDecider** は 3 段ルールベースを最小ルール集で実装する。Filter で spread / セッション / 指標近接 / サイズ下限、Score で EV + 成績重み、Select で相関 + 同時ポジ上限 + 総リスク制約を扱う。

**Risk**: `PositionSizer` (1〜2% リスク、最小ロット未達は no_trade)、`RiskManager.accept` (同時ポジ / 通貨偏重 / 総リスク / 相関)。`account_snapshots` はイベント駆動 + 日次で記録。

**ExitPolicy** は最小セット (SL / TP / 最大保有時間 / 緊急停止) を優先度付きで実装する。reverse / EV 低下 / 指標停止前 は Interface で準備済みだが後続で詰める。

**Broker 抽象** は MVP 時点で定義済み。`PaperBroker` / `OandaBroker` / `MockBroker (test)` が同一 Interface で動き、mode 切替は設定で行う。

**最小ダッシュボード (Streamlit)** は Section 5.4 の 10 カテゴリのうち、MVP 段階では「相場状態評価」「戦略別比較」「メタ戦略選択結果」「ポジション状況」「当日 PnL + 稼働状態」「safe_stop 状態」「直近シグナル一覧」を最低限表示する。`dashboard_top_candidates` / TSS の**マート列は確保**するが、計算は粗くてよい。更新は 5-10 秒 polling。

**学習 UI 最小** は enqueue (対象・期間指定) / 状態 / 履歴のみ。LearningOps 本体は Stub でよく、`system_jobs` への enqueue と完了記録が動けば良い。

**Supervisor 最小** はヘルスチェック (プロセス生存 + DB 接続 + OANDA 疎通 + stream 状態) と `safe_stop(reason)` の発火を実装する。Reconciler の骨格 (`app_runtime_state` / `orders` / `positions` / OANDA 実状態の突合) も含む。

**correlation_id / cycle_id / order_id 横断ログ** は MVP 時点から有効にする。これがないと分析 11 軸が成立しない。

**実行モード** は `single_process_mode × local` を MVP 既定とし、`single_process_mode × vps` も動く (MVP 時点で本番稼働可能)。`multi_service_mode` / `container_ready_mode` は Interface 準備のみで、実実装は後続。

### 12.2 MVP では契約のみ (実装後回し)

`SecondaryProjector` の本実装 (MVP は手動バッチ投影または空で良い)、`EventCalendar` の自動取得 (MVP は手動 CSV で OK)、MetaDecider の Score / Select の学習化、EVEstimator v1 以降、モデルドリフト検出、ドリフトマート、反実仮想バッチ、`dashboard_top_candidates` の本生成、認証 (MVP は BasicAuth / IP 制限)、`multi_service_mode` / `container_ready_mode` の運用実装。

### 12.3 MVP の完了基準

次の 8 つが全て成立すれば MVP は完了とする。(1) OANDA に接続し全通貨ペアを毎サイクル評価できる、(2) 3 戦略 × 70 ペアのシグナルが一次 DB に記録される、(3) MetaDecider が MetaDecision を出力し no_trade を含む全判断がログされる、(4) PaperBroker で擬似発注・擬似約定・ポジション更新・決済が一次 DB に記録される、(5) Streamlit で上記 7 カテゴリが表示される、(6) 学習 UI から enqueue → 状態確認 → 履歴確認が動く、(7) Supervisor が safe_stop を発火でき、再起動時に Reconciler が状態を復元する、(8) PostgreSQL に全ログが付き、Common Keys + cycle_id / correlation_id で 1 本の SQL 分析が可能。

**Responsibilities**: 全パイプライン (データ取得 → 特徴量 → 戦略 → メタ → Risk → 発注 → 約定 → 決済 → ログ → 可視化 → 学習 enqueue) を**細く通す**こと。
**Inputs**: OANDA API、PostgreSQL (ローカル)、運用者の手動起動。
**Outputs**: 動作する paper mode 取引システム、完全ログ、最小ダッシュ、学習 UI、Supervisor、Reconciler。
**Failure Modes**: MVP 範囲の過大化 (契約だけで止めるべきものを実装してしまう)、paper と live の不整合 (Broker Interface 共通化で防ぐ)、MVP 完了基準の恣意的緩和 (8 項目を崩さない)、MVP 後のスケール問題 (210 候補/サイクルの処理時間が 1 分を超える等)。

---

## 付録: 重要制約 (全体を通した不変条件)

本システムが全フェーズを通じて**絶対に守る**不変条件は以下のとおり。これらはアーキテクチャ全体の整合性を担保する中核契約であり、いかなる実装判断もこれらに優先してはならない。

1. **秒単位処理を主戦略判断に使わない** — 秒単位は執行補助 5 項目 (spread / 急変 / entry guard / 約定確認 / 異常検知) に限定する。
2. **学習を常時実行しない** — LearningOps はバッチ系統で分離、手動 or スケジュール起動のみ。
3. **二次 DB に依存して売買しない** — 売買クリティカルパスは一次 DB + TradingCore + ExecutionAssist + Supervisor のみで完結。
4. **ローカル PC でも動く** — 3 環境 × 3 モードのうち少なくとも `local × single_process_mode` は常に動作保証。
5. **DB を物理リセットしない (No-Reset)** — 本番・準本番で履歴を保持、バージョン跨ぎ比較を可能に。
6. **設定値ハードコード禁止・秘密コード直書き禁止** — 4 階層の Config + SecretProvider 経由のみ。
7. **UI は売買系を直接参照しない** — Dashboard Query Service 経由、UI 停止で売買影響なし。
8. **ログ保存失敗そのものでは売買を止めない / Critical tier の一次 DB 書込失敗は安全側に倒れる** — Criticality Tier 契約。
9. **cycle_id / correlation_id / order_id は系統を跨いで不変伝搬** — 分析と再現性の前提条件。
10. **Phase 単位で育てる / 一度に巨大実装しない / 既存仕様を独断で削除・簡略化・置換しない** — 設計の進化可能性を維持する。

---

以上が Phase 0〜5 を統合した設計書である。次フェーズの仕様追加は本書の各セクションへ**拡張・追記**として統合される。既存仕様の変更を伴う場合は、必ず Reviewer View と Issues / Improvements の章を伴う差分提案の形で提示すること。

---

## Phase 6 Reference — Hardening (運用成熟化)

Phase 6 は本書 (Phase 0–5 統合設計) に対する実運用前提レビューで特定された Critical / High 指摘を設計段階で閉じるフェーズである。**本書本体は大幅には書き換えず、Phase 6 の詳細は分冊 `docs/phase6_hardening.md` を単一ソースとする**。本 Section はその要約と参照のみ。

### Phase 6 の要旨

Phase 6 は 14 項目の運用契約を追加し、いずれも既存 Section の**追記・強化・初期値確定**として統合される (削除・簡略化はしない):

1. **SafeStopJournal** — `safe_stop` 記録を DB 単独から多重化 (ローカル fsync + Notifier + DB)、Circular Failure 解消 (Section 11 強化)
2. **Mid-Run Reconciler** — 稼働中の transaction stream 取りこぼし / drift を 15 分毎に補完 (Section 4 / 11 強化)。**平常時は trading 系より低優先度**、**stream gap 補完時のみ一時的に高優先度**に昇格し、売買クリティカルパスを阻害しない
3. **EventCalendar Stale Failsafe** — `last_updated_at` + Fallback 全 no_trade + `PriceAnomalyGuard` 二重防御 (Section 5.3 / 11 強化)
4. **client_order_id ULID 化** — 再起動耐性ある冪等キー (Section 6.2 強化)
5. **初期数値パラメータ** — リスク%・DD 閾値・cycle timeout・retention 等の全値を `app_settings` 初期 migration で確定 (Section 10 / 11 強化)
6. **Outbox Pattern** — 発注を `orders(PENDING) → Broker → SUBMITTED` で多段化、書込失敗時の副作用ゼロ化 (Section 6 / 8 強化)
7. **Meta Score Contribution Visibility** — 合成スコアの成分寄与を JSONB で常時記録、過集中警告 (Section 5.3 強化)
8. **相関双窓** — short_window 1h / long_window 30d、regime_detected フラグ記録 (MetaDecider 強制適用は Phase 7)
9. **UI / 二次DB 負荷制御** — Streamlit キャッシュ強制、接続プール分離、エラーレート degraded (Section 7.2 / Phase 5 強化)
10. **feature_snapshots compact_mode 既定化** — ディスク破綻防止 (Section 8.6 強化)。compact 保存で失われた生配列の再現性担保のため、**Feature Service は `feature_version` を持つ決定的コンポーネント**として契約化する (同一入力・同一 feature_version でバイト等価な出力)。feature_version は Common Keys 拡張として全 `feature_snapshots` 行に付与、Aggregator は feature_version 跨ぎの集計を禁止
11. **AIStrategy stub / shadow / active 状態遷移** — MVP は stub、本番移行の 30 日 shadow 期間を契約化 (Section 5.2 / 9 強化)
12. **Reconciler Action Matrix** — 起動時整合の全ケースを決定表化 (Section 11.3 強化)
13. **Notifier Infrastructure** — FileNotifier + SlackNotifier + 通知必須イベント 14 種 (Section 11 強化)。非 critical は `notification_outbox` 経由 (非同期)。**safe_stop 系 critical 通知 (safe_stop / db.critical_write_failed / stream.gap_sustained / reconciler.mismatch_manual_required / ntp.skew_reject 等) は outbox を経由せず、FileNotifier への fsync + 利用可能な全外部 Notifier へ同期直接送信**する (DB 障害が発火源でありうるため経路を DB から切り離す)
14. **Supporting 契約** — NTP 起動検査 (warn 500ms / reject 5s 二段)、swap cost、margin 監視、DR/バックアップ、Emergency Flat CLI
15. **Execution TTL** — `trading_signals.created_at` + `signal_ttl_seconds` (初期 15 秒、範囲 10–20)、ExecutionGate 最初の段で TTL 判定 → 超過で `Reject(SignalExpired)`。Defer は TTL 内のみ再評価、連発で `Reject(DeferExhausted)`。古い判断に基づく発注を構造的に防止
16. **no_trade Taxonomy** — no_trade を意思決定結果として明示扱い、`no_trade_events` に `reason_category` / `reason_code` / `reason_detail` / `source_component` 列追加。発生源 (meta.filter / meta.score / meta.select / risk / event_calendar / price_anomaly / strategy / supervisor) を taxonomy で分類、ダッシュボードで reason 分布可視化。ExecutionGate 由来の Reject (SignalExpired 等) は `execution_metrics` 側に記録し責務分離
17. **戦略 ON/OFF 制御** — `app_settings.strategy.{AI|MA|ATR}.enabled` で戦略個別に有効・無効化。disabled は Strategy Engine の評価対象から除外、`meta_decisions` の `active_strategies` に記録。**AI の `lifecycle_state` (stub/shadow/active) とは独立した直交軸**として扱い、shadow 期間中の緊急停止弁として機能。Aggregator は enabled 切替点を集計境界として跨ぎ禁止
18. **Broker Account Type Safety Contract** — `Broker.account_type` (demo/live) を Interface に露出、`app_settings.expected_account_type` (初期 demo) を正本として起動時 assertion (不一致で起動拒否) + 発注前 assertion (不一致で `safe_stop(account_type_mismatch_runtime)`) + `orders.account_type` 列必須記録。`local` プロファイルは `demo` 固定、`live` への切替は手動 SQL + 起動後の手動 confirmation 必須で自動化禁止。Paper → Live 誤爆防止の 4 重防御 (設定 / 起動 / ランタイム / 運用)

### in-flight 発注の扱い (6.1 補足)

safe_stop 発火時の送信中 HTTP リクエストは中断せず、`place_order_timeout_seconds` (初期 30 秒) まで応答を待つ。新規発注受付は即停止、Outbox の未送信分は dispatch 停止、transaction stream の受信は継続。タイムアウト超過分は `orders.status=FAILED` に遷移し Reconciler で整合。これにより「実ポジション発生・DB 未記録」の窓を最小化

### Phase 6 で確定した横断契約 (C4 / C1 / C6 解消)

本書 Section 7.1 / 7.2 / 8 / 12 と整合する形で以下 3 件を Phase 6 で確定:

- **`config_version` 導出契約 (6.19)** — `SHA256(effective_config_canonical_json)[:16]`。canonical JSON は `app_settings` 全行 + `APP_*`/`FX_*` 環境変数 + `.env` + デフォルトカタログ + secret 参照ハッシュの 5 要素を辞書式ソート + UTF-8/LF 正規化して連結。起動時に 1 回計算し `supervisor_events` に source_breakdown 付きで記録。前回 run と不一致なら Notifier `info` で通知。secret 値そのものは effective_config に含めず SHA256 参照のみ
- **Schema Catalog 確定 (6.20)** — Phase 6 時点の canonical DB テーブル数は **42** (Phase 4 baseline 34 + Phase 6 新規 3: outbox_events / notification_outbox / correlation_snapshots + Phase 1/2 一級明示化 5: reconciliation_events / supervisor_events / retry_events / anomalies / app_settings_changes) + ローカルアーティファクト 2 (SafeStopJournal / NotificationFile)。本書 Section 7.1 / 12.1 の「34 テーブル」記述は Phase 4 snapshot として維持、Phase 6 以降の canonical は `phase6_hardening.md` 6.20 および Iteration 0 で作成する `schema_catalog.md` を参照
- **Retention vs No-Reset 契約 (6.21)** — No-Reset は「`TRUNCATE`/`DROP`/破壊的バルク削除の禁止」、Cold アーカイブは「Copy → Verify → Delete の 3 段プロセス (検証成功後の論理移管)」と定義し両立。Reference / Execution / Aggregates / Supervisor 系は永続保持 (Cold 移動なし)、Decision logs / Observability / Market raw は Hot/Warm/Cold 階層で外部アーカイブ後削除、Outbox 系は非永続で直接削除可。MVP 時点では契約を宣言、実 Cold ジョブは Phase 7 以降で稼働させる (ただし「単純 DELETE 禁止」の原則は MVP から強制)

### 付加される不変条件

本書「付録: 重要制約」に以下 2 項を追加する:

11. **Critical tier の書込は DB 単独に依存しない** — ローカル fsync / Notifier / DB の多重化を必須とする
12. **通知は Outbox + 多重チャネル** — FileNotifier は常時必須、SlackNotifier は MVP 必須、EmailNotifier は任意

### MVP 必須項目 (Phase 6 由来)

MVP リリース条件に以下を追加 (詳細は `docs/phase6_hardening.md` 参照):

**絶対必須**: SafeStopJournal / Mid-Run Reconciler / EventCalendar Stale Failsafe / client_order_id ULID / 初期数値パラメータ / Outbox Pattern / Reconciler Action Matrix / Notifier (File + Slack) / NTP 起動検査

**MVP 強推奨**: Meta Score Contribution / UI 接続分離 / feature compact_mode 既定 / DB バックアップ

**MVP は契約のみ**: 相関双窓の regime tightening 適用 (Phase 7) / AIStrategy shadow 運用 (Phase 7) / CI/CD 自動化 (Phase 7) / EmailNotifier (任意)

### 詳細参照

Phase 6 の全仕様 (設計項目、差分一覧、MVP 必須項目、Phase 7 以降の後回し項目) は **`docs/phase6_hardening.md`** を正本とする。本書本体と `docs/phase6_hardening.md` の間で記述が食い違う場合は後者を優先する (Phase 6 は後発の契約強化であるため)。
