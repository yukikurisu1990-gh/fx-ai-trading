# Iteration 2 Implementation Plan

## 1. Purpose

Iteration 1 の Conditional Complete 状態を **Full MVP** に昇格させるフェーズ。`docs/iteration1_completion.md` に記録された 8 件の Carryover ID（`M-EXIT-1` / `M-METRIC-1` / `M-LRN-1` / `Mi-CTL-1` / `Mi-DASH-1` / `Ob-ALEMBIC-1` / `Ob-MIDRUN-1` / `Ob-PANEL-FALLBACK-1`）を全て解消し、MVP §12 の 10 項目全てを Full Green にすることが Iteration 2 完了条件。

本 Iteration は「skeleton から MVP 完成への充填フェーズ」と位置付け、Phase 7（Backtest / AI / Cold Archive）および Phase 8（SSO / 税務 / DR）には踏み込まない。

---

## 2. Scope

### 2.1 In Scope

- OANDA live 接続（demo→live 切替、手動 confirmation 運用）
- EmailNotifier 実装（SMTP）
- Reconciler Action Matrix 全 11 ケース + MidRunReconciler 実体
- Dashboard 残り 3 パネル（トップ候補 / 執行品質 / リスク状態詳細）+ 実 DB 結線
- TSS（Trade Suitability Score）計算 + `dashboard_top_candidates` **テーブル新規作成**（migration 0011）+ mart 本生成
- Supabase Projector（二次 DB への定期 snapshot）
- Emergency Flat CLI の 2-factor 化
- multi_service_mode Interface 拡張（接続点のみ、本運用は Phase 7）
- ExitPolicy Service + close_event 記録
- Supervisor 1 分メトリクスループ（9 項目、`supervisor_events` 永続蓄積）
- Learning UI（enqueue / status / history）+ LearningOps 最小
- ctl CLI の実 process 管理（start / stop / resume-from-safe-stop / run-reconciler / emergency-flat-all）
- alembic `path_separator` 現代化 + migration tooling 整備
- **D3（implementation_contracts.md）への新規 Protocol 5 件追加**（ExitPolicy / LearningExecutor / ProjectionTransport / TwoFactorAuthenticator / ServiceMode）
- **operations.md の同期更新**（§3.1 emergency-flat 2-factor 必須、§6.3 アラート Email 経路、service_mode 章新設、§11 ctl Cheat Sheet 拡張）
- **Operator/Configuration Console UI 仕様化（ドキュメントのみ、M26）**：4 層責務マトリクス、Configuration Console（起動前 .env sink / 稼働中 read-only + 変更キュー）、Operator Console（既存 ctl ラッパ、新規 usecase 不導入）、UI 経由 secret 入力 sink を `.env` 限定とする原則、Phase 8 SSO/multi-user 送りの境界明示。実装は Iteration 3 以降の別 PR、本 Iter は仕様凍結のみ（詳細は §6.14 M26）

### 2.2 Out of Scope（Phase 7 / Phase 8 へ明示送り）

**Phase 7 送り**:
- Backtest Engine 実体（`BacktestRunner.run()` 実装）
- AI 本物モデル学習 / 推論（AIStrategy は Iteration 2 もスタブのまま）
- shadow→active Promotion 自動化
- 相関双窓 regime tightening の MetaDecider Select 強制適用
- Drift detection 本実装（PSI / KL / 残差）
- EVCalibrator v1 以降
- Cold Archive 実ジョブ
- Chaos Engineering 体系化
- CI 自動マイグレーションテスト
- Streamlit 卒業条件超過時の UI フロント刷新（Next.js + FastAPI）

**Phase 8 送り**:
- OAuth / SSO Notifier
- Slack 双方向運用
- Dashboard SSO / マルチユーザ
- DR 訓練月次体系化
- 税務エクスポート GUI
- Emergency Flat の 2-factor 以上の権限分離（本 Iteration は 2-factor 止まり）

---

## 3. Inputs / Dependencies

### 3.1 主要入力

- `docs/iteration1_implementation_plan.md`（M1–M12 計画 + §13 Iteration 2 送り 9 項目）
- `docs/iteration1_completion.md`（Carryover ID 8 件、主対象 5 領域）
- `docs/schema_catalog.md` (D1)、`docs/implementation_contracts.md` (D3)、`docs/operations.md` (D4)、`docs/retention_policy.md` (D5)、`docs/phase6_hardening.md`

### 3.2 コード依存

Iteration 1 で確定した以下は**前提として動作保証**:
- `src/fx_ai_trading/supervisor/*`（startup 16 Step + safe_stop fire sequence）
- `src/fx_ai_trading/services/outbox_processor.py`（pause / resume）
- `src/fx_ai_trading/services/execution_gate.py`（TTL / Defer）
- `src/fx_ai_trading/adapters/broker/*`（MockBroker / PaperBroker / OandaBroker 骨格）
- `src/fx_ai_trading/adapters/notifier/*`（FileNotifier / SlackNotifier / dispatcher）
- `src/fx_ai_trading/dashboard/*`（app.py + panels/ 7 パネル + query_service）

### 3.3 外部依存

- OANDA demo API key（live API key は Iteration 2 でも Production 本発注には使わず、疎通のみ確認）
- SMTP サーバ（EmailNotifier 用、開発は MailHog 等のローカル SMTP）
- Supabase プロジェクト（Projector 用、無料枠で可）

---

## 4. Goals

### 4.1 定量ゴール

1. MVP §12 の 10 項目全てが Full（現状 5 Full / 3 Partial / 2 未達）
2. 既存 contract test 15 本は全て green 維持
3. Iteration 2 新規 contract test を最低 6 本追加（Live Gate / ExitPolicy / Email / Reconciler Full / TSS / 2-factor）
4. paper smoke end-to-end が Stage 7（exit policy）まで到達
5. Dashboard 10 panel 全てが実 DB データを表示（fallback なし構成で確認）
6. Supervisor メトリクス 9 項目が 1 分毎 supervisor_events に記録される

### 4.2 定性ゴール

1. Carryover ID 8 件全てが「resolved by Iteration 2 M-xx」として `iteration1_completion.md` 側に対応できる形で解消
2. Iteration 3 / Phase 7 への「送り項目」が明示的リストとして残る
3. 1 PR = 1 サイクル、各 M は最大 10 サイクル目安を遵守

---

## 5. Milestones

| M | 名称 | 目的 | 典型工数 | 依存 | 主 Carryover |
|---|------|------|---------|------|-------------|
| **M13** | OANDA Live Adapter + Demo→Live Gate | OandaBroker 本実装、live confirmation 基盤 | 3–4 日 | Iter1 M6 | (前提) |
| **M14** | ExitPolicy Service + close_event Wiring | TP/SL/time/emergency 発火、close_events 記録 | 3–4 日 | Iter1 M5, M10 | **M-EXIT-1** |
| **M15** | Reconciler Full Action Matrix + MidRunReconciler | 11 ケース全網羅 + 2-bucket RateLimiter | 3–4 日 | Iter1 M8 | **Ob-MIDRUN-1** |
| **M16** | Supervisor 1-Minute Metrics Loop | 9 項目を 60s 毎記録 | 1–2 日 | Iter1 M7 | **M-METRIC-1** |
| **M17** | EmailNotifier + Dispatcher Strengthening | SMTP 実装、critical 3 経路 | 2 日 | Iter1 M6 | (Iter1§13) |
| **M18** | Dashboard Query Service Extension + Seed | phase_mode / environment seed 追加、query 拡張 | 2 日 | Iter1 M12 | **Ob-PANEL-FALLBACK-1** |
| **M19** | Dashboard 残り 3 Panel + Real Data 結線 | トップ候補/執行品質/リスク詳細 + 既存 7 の実 DB 疎通 | 3–4 日 | M18 | **Mi-DASH-1** |
| **M20** | TSS Calculation + dashboard_top_candidates Mart | TSS 計算、mart 生成 | 2–3 日 | M18, Iter1 M9 | (Iter1§13) |
| **M21** | Learning UI + LearningOps Minimal | enqueue/status/history + LearningOps 最小 | 3 日 | Iter1 M12 | **M-LRN-1** |
| **M22** | ctl CLI Process Management + 2-Factor Emergency | start/stop 実 process、2-factor confirmation | 2–3 日 | M13 | **Mi-CTL-1** |
| **M23** | Supabase Projector + Secondary DB Snapshot | Projector Interface 実装、定期 snapshot | 2–3 日 | Iter1 M5 | (Iter1§13) |
| **M24** | Alembic Modernization + multi_service_mode I/F Expansion | alembic 2.x 設定、MSM 接続点整備 | 1–2 日 | Iter1 M2 | **Ob-ALEMBIC-1** |
| **M25** | Iteration 2 Contract Hardening + E2E Suite Extension | 新契約 test + paper smoke exit 延伸 | 2–3 日 | M13-M24 | (全 M 検証) |
| **M26** | UI / Console Operational Boundary Spec Freeze (docs only) | Operator/Configuration Console 責務境界・secret/config UI ルール・Phase 8 送りを 6 docs に凍結 | 0.5–1 日 | M22 (ctl 5 cmd 確定) | — (Iter1§13 にも未記載、本 Iter で新設) |

**総工数目安**: 30–40 日（1 人日換算）。並列化・中断考慮で実時間 6–9 週間想定。M26 は docs only かつ M22 確定後に着手するため総工数への寄与は誤差範囲。

---

## 6. Detailed Milestones

### 6.1 M13: OANDA Live Adapter + Demo→Live Gate

**目的**: Iteration 1 で骨格のみだった `OandaBroker` を本実装し、demo→live 切替を安全に行う gate（手動 confirmation + 複数検証）を整備。

**入力**:
- Iter1 M6（`adapters/broker/oanda.py` 骨格 + `_verify_account_type_or_raise`）
- 6.18 account_type assertion 契約
- `docs/operations.md` Step 9 / 10

**変更対象**:
- `src/fx_ai_trading/adapters/broker/oanda.py`（place_order / cancel_order / get_order / stream_transactions 実装）
- `src/fx_ai_trading/adapters/broker/oanda_api_client.py`（oandapyV20 薄ラッパー、rate limit 考慮）
- `src/fx_ai_trading/supervisor/live_confirmation.py`（`--confirm-live-trading` フラグ検査、複数検証）
- `src/fx_ai_trading/config/provider.py`（live 用 secret 読込追加）
- `tests/contract/test_live_confirmation_gate.py`（demo 固定の contract）
- `tests/contract/test_oanda_broker_account_type.py`（live/demo 両方で assertion）
- `tests/integration/test_oanda_demo_connection.py`（demo 接続疎通、VCR 等で録画）

**完了条件**:
- [ ] `OandaBroker.place_order` が demo 環境で擬似発注（**Iteration 2 は demo のみ**、live 実発注の運用解禁は Iteration 3 以降で別 PR で議論）
- [ ] `live_confirmation.py` が `expected_account_type=live` への切替を 3 段階検証（環境変数 + フラグ + 対話 or config_version 明示一致）
- [ ] `ctl --confirm-live-trading` が `live_confirmation.py` 経由で呼出され、検証失敗時は即 exit（Mi-CTL-1 副担当として）
- [ ] `OandaBroker._verify_account_type_or_raise` が demo/live 両方で正しく動作（D3 §2.13.3 `AccountTypeAssertion` を委譲利用、新規 Protocol 化はしない）
- [ ] demo 接続で `instruments` / `candles` / `pricing` 取得成功
- [ ] ネットワーク失敗時は retry_events に記録、TTL 内は retry
- [ ] **live 実発注（place_order で live account）は本 Iteration ではコード経路は存在するが、CI test では demo only を強制**
- [ ] `app_settings.expected_account_type` の demo↔live 切替 SQL 手順を `docs/operations.md` Step 9 周辺の runbook として追記（許可介入表に登録）
- [ ] `ctl --confirm-live-trading` の startup 16 Step 内位置（Step 9 完了 → confirm 待ち遷移）を `supervisor_events` に記録

**テスト条件**:
- Contract: live confirmation gate（demo 固定で live 呼出し不可）
- Contract: account_type assertion（live/demo 両方）
- Integration: demo 接続疎通（録画済みレスポンスで可）

**リスク**:
- OANDA API の rate limit（本 Iteration は demo のみ、live は疎通確認のみ）
- 誤って live API key を test に流出 → Secret Provider の読込経路を contract test で固定

**後続依存**: M22（ctl の live confirmation、start / emergency-flat で使用）、M25（E2E 契約）

---

### 6.2 M14: ExitPolicy Service + close_event Wiring

**目的**: `M-EXIT-1` 解消。TP / SL / time / emergency の exit 発火、`close_events` テーブル記録、position クローズまでの end-to-end を実装。

**入力**:
- Iter1 M5 Repository（`close_events` / `positions`）、M10 ExecutionGate、M4 ExitPolicy Protocol
- Carryover: **M-EXIT-1**

**変更対象**:
- `src/fx_ai_trading/services/exit_policy.py`（ExitPolicyService、TP/SL/time/emergency の 4 ルール）
- `src/fx_ai_trading/services/exit_executor.py`（Broker に close 指示 → close_events 記録）
- `src/fx_ai_trading/domain/exit.py`（Iter1 M4 Protocol に不足ある場合のみ追記、破壊的変更禁止）
- **`docs/implementation_contracts.md` への `ExitPolicy` Protocol 新規追加**（D3 は現状名称言及のみで Protocol 未定義のため、本 M で追加）
- `tests/contract/test_exit_policy_rules.py`（4 ルール個別）
- `tests/contract/test_exit_event_fsm.py`（close_events FSM、前進のみ）
- `tests/integration/test_exit_flow.py`（position 作成 → TP hit → close_event 記録）
- `tests/unit/test_exit_policy.py`

**完了条件**:
- [ ] ExitPolicy が TP / SL / time-based / emergency-flat の 4 ルールで `ExitDecision` 返却
- [ ] ExitExecutor が Broker 経由でクローズ発注 → `close_events` INSERT（Common Keys + cycle_id + correlation_id）
- [ ] position の状態が open → closing → closed で前進のみ
- [ ] **emergency-flat は M22 の ctl `emergency-flat-all` から ExitExecutor を呼出（M14 ↔ M22 相互依存）**
- [ ] close_events が `trading_signals` / `orders` と cycle_id で join 可能
- [ ] **`close_events` は retention_policy §3.1 #23 で `EXECUTION_PERMANENT` 指定（削除不可、税務 7 年保持）。partial close 不実装を本制約と整合させる旨を §6.2 リスク欄および本 M 完了時に注記**
- [ ] D3 への `ExitPolicy` Protocol 追加が contract test で参照可能

**テスト条件**:
- Contract: TP/SL/time/emergency 個別発火
- Contract: close_events FSM 前進のみ
- Integration: position open → TP hit → close_event end-to-end
- Unit: ExitPolicy ルール単体

**リスク**:
- partial close（部分決済）の複雑度 → **Decision**: Iteration 2 は 100% close のみ、partial close は Phase 7 送り
- TP / SL の同時 hit → **Decision**: 先に評価された rule が優先（deterministic 順序）

**後続依存**: M19（Dashboard panel で close_events 表示）、M22（emergency-flat 経路で呼出）、M25（E2E 延伸）

---

### 6.3 M15: Reconciler Full Action Matrix + MidRunReconciler

**目的**: `Ob-MIDRUN-1` 解消。Iteration 1 で 5–6 ケースだった Reconciler Action Matrix を全 11 ケースに拡張、MidRunReconciler を RateLimiter 2-bucket 切替付きで実体化。

**入力**:
- Iter1 M8 Reconciler 骨格、**`docs/phase6_hardening.md` §6.12 Action Matrix（11 ケース定義の正本）**、§6.2 MidRun
- Carryover: **Ob-MIDRUN-1**

**変更対象**:
- `src/fx_ai_trading/supervisor/reconciler.py`（classify 11 ケース全網羅）
- `src/fx_ai_trading/supervisor/midrun_reconciler.py`（check 実体 + bucket 切替）
- `src/fx_ai_trading/common/rate_limiter.py`（2-bucket: trading / reconcile）
- `src/fx_ai_trading/supervisor/stream_watchdog.py`（heartbeat 監視 + gap 検知、骨格→実体）
- `tests/contract/test_reconciler_action_matrix.py`（既存を拡張、11 ケース全明示）
- `tests/contract/test_rate_limiter_buckets.py`
- `tests/integration/test_midrun_reconciler_bucket_switch.py`
- `tests/integration/test_stream_watchdog_gap_detection.py`

**完了条件**:
- [ ] Reconciler Action Matrix の 11 ケース全てに explicit test（既存 `test_reconciler_action_matrix.py` の test 数は本 M 着手時に grep で再計測、追加分のみ新規アサーション）
- [ ] MidRunReconciler が 15 分毎（テストでは mock timer）に drift check を実行
- [ ] RateLimiter が trading / reconcile の 2-bucket を保持、MidRun 発動時に bucket 切替
- [ ] StreamWatchdog が heartbeat gap を検知して stream_status に記録
- [ ] safe_stop 中の in-flight order 処理は既存 test（`tests/contract/test_safe_stop_fire_sequence.py` / `tests/integration/test_in_flight_order_handling.py` / `tests/integration/test_safe_stop_journal.py`）を壊さない
- [ ] `operations.md` §2.1 Step 11（PriceFeed/TransactionStream + StreamWatchdog 起動順）と Step 13（MidRunReconciler 起動シーケンス）と本 M 実装の wiring 整合確認

**テスト条件**:
- Contract: Action Matrix 11 ケース explicit
- Contract: RateLimiter bucket 独立性
- Integration: MidRun bucket 切替
- Integration: StreamWatchdog gap 検知

**リスク**:
- 既存 `test_reconciler_action_matrix.py` との衝突 → **Decision**: 既存 test を温存、新規 test ファイルで追加カバレッジ
- MidRun の 15 分タイマーを CI で遅延させない → fake clock で即時発火

**後続依存**: M25（新契約を hardening suite に組込）

---

### 6.4 M16: Supervisor 1-Minute Metrics Loop

**目的**: `M-METRIC-1` 解消。Supervisor に 60 秒周期のメトリクス記録ループを追加、9 項目を `supervisor_events` に書く。

**入力**:
- Iter1 M7 Supervisor、**`docs/operations.md` §6.2 メトリクス 9 項目仕様（テーブル正本）**
- Carryover: **M-METRIC-1**

**変更対象**:
- `src/fx_ai_trading/supervisor/metrics_loop.py`（新規、60s 周期の記録ループ）
- `src/fx_ai_trading/supervisor/supervisor.py`（metrics_loop の起動組込、startup 16 Step 内位置を明示）
- `src/fx_ai_trading/supervisor/health.py`（9 項目収集ロジック、既存 HealthStatus 拡張）
- `tests/integration/test_metrics_loop.py`（fake clock で 60s 間隔記録確認）
- `tests/contract/test_supervisor_metrics_schema.py`（supervisor_events スキーマで 9 項目全記録）

**完了条件**:
- [ ] MetricsLoop が 60s 毎に起動、停止・一時停止が Supervisor から制御可能
- [ ] 9 項目（operations.md §6.2 テーブル参照）が supervisor_events に 1 行として記録
- [ ] メトリクスは Common Keys + cycle_id で join 可能
- [ ] safe_stop 時に MetricsLoop も停止（fire sequence を破らない、`tests/integration/test_startup_sequence.py` を非破壊）
- [ ] DB 書込失敗時は log warn、loop は継続（fail-open）

**テスト条件**:
- Integration: fake clock で 60s 間隔
- Contract: 9 項目 schema 一致
- Integration: safe_stop 時の停止

**リスク**:
- DB 負荷 → 9 項目 + 1 分毎なら年間 ~525k 行
- **`supervisor_events` は retention_policy §3.1 #41 で `SUPERVISOR_PERMANENT` 指定（Cold 移動なし、永続蓄積）**。MVP 期間 3–6 ヶ月（retention_policy §9.3 で Archiver 未実装許容）の範囲では問題化しないが、Phase 7 Cold Archive 着手時に再評価必須。本 M リスクとして明示記録
- Common Keys の自動付与が抜ける → Repository 経由強制

**後続依存**: M23（Supabase Projector が supervisor_events を読む）

---

### 6.5 M17: EmailNotifier + Dispatcher Strengthening

**目的**: Iter1§13 EmailNotifier 実装。critical 通知の 3 経路（File + Slack + Email）化。

**Scope 拡張の正当化（Loop 3 反映）**: `phase6_hardening.md` §6.13 行 354 / 838 では EmailNotifier は「**任意（MVP では未実装可）**」とされていたが、`docs/iteration1_implementation_plan.md` §13 で Iter2 送りに昇格。本 M で MVP §12 #10「Notifier 二経路 + Email」を Full 化するため**必須化**。phase6 側の「任意」記述は Iter1 時点判定であり、Iter2 で必須化された旨を本書に固定（phase6 自体は変更しない）。

**入力**:
- Iter1 M6 Notifier dispatcher、`docs/phase6_hardening.md` §6.13 二経路契約（D3 §2.10.1 と整合）
- Iter1§13

**変更対象**:
- `src/fx_ai_trading/adapters/notifier/email.py`（SMTP 実装）
- `src/fx_ai_trading/adapters/notifier/dispatcher.py`（3 経路 fan-out、既存 2 経路 test を壊さない）
- `src/fx_ai_trading/config/provider.py`（SMTP 設定読込）
- **`docs/operations.md` §6.3 アラート表に Email 経路を追加**（現状 File + Slack のみ記載）
- `tests/contract/test_notifier_two_path.py`（既存、Email を含めても critical/非critical 分岐が保持されること確認）
- `tests/contract/test_email_notifier.py`（新規）
- `tests/contract/test_forbidden_patterns.py`（既存、SMTP 認証情報文字列が ログに混入しないこと確認）
- `tests/integration/test_email_dispatch.py`（MailHog 等ローカル SMTP で疎通）

**完了条件**:
- [ ] EmailNotifier が SMTP 経由でメール送信（認証 + STARTTLS）
- [ ] critical 通知が File + Slack + Email の 3 経路 fan-out（順序: File → Slack → Email）
- [ ] 非-critical 通知は outbox 経由のまま（既存契約保持）
- [ ] SMTP 失敗時は他経路を阻害しない（Fan-out 独立性）
- [ ] secret（SMTP password）が effective_config / ログに出ない

**テスト条件**:
- Contract: 二経路 + Email 経路の独立性
- Contract: Email Notifier の送信 payload
- Integration: MailHog / Fake SMTP で end-to-end 送信

**リスク**:
- SMTP retry の無限ループ → max_retry=3 + backoff
- メール量の暴走 → rate_limit（n 通/分）を app_settings で制御

**後続依存**: M25（新契約を hardening）

---

### 6.6 M18: Dashboard Query Service Extension + App Settings Seed Extension

**目的**: `Ob-PANEL-FALLBACK-1` 解消。`phase_mode` / `environment` を含む app_settings seed 拡張と、dashboard_query_service の新規クエリ追加。

**入力**:
- Iter1 M12 dashboard、Iter1 M2 app_settings seed
- Carryover: **Ob-PANEL-FALLBACK-1**

**変更対象**:
- `alembic/versions/0011_app_settings_phase_mode_seed.py`（新規 migration、key 追加。0012 以降は M20 で別途）
- `src/fx_ai_trading/services/dashboard_query_service.py`（新規 query: `get_top_candidates`, `get_execution_quality_summary`, `get_risk_state_detail`, `get_close_events_recent`）
- `tests/migration/test_app_settings_phase_mode_seed.py`
- `tests/unit/test_dashboard_query_service.py`（**新規作成**。既存 `tests/unit/test_dashboard_query_service.py` は不在のため、本 M で全 query の base test を新設し、その同ファイル内に拡張 query 用 test を追加）
- `tests/migration/test_migration_chain.py` / `test_schema_coverage.py` / `test_roundtrip.py`（既存、0011 追加で 3 本全てに影響、green 維持を必須化）

**完了条件**:
- [ ] `phase_mode` / `runtime_environment`（後述命名衝突回避）が app_settings seed に存在
- [ ] dashboard_query_service に 4 つの新規 query（fallback 不要、実 DB 返却）
- [ ] 既存 query 関数（M12 で導入済の `get_open_positions` / `get_recent_orders` / `get_recent_supervisor_events` 等）を破壊しない
- [ ] クエリは `ttl=5` 前提の cache キー設計
- [ ] `tests/migration/test_migration_chain.py` / `test_schema_coverage.py` / `test_roundtrip.py` 3 本が 0011 追加後も green

**命名衝突注意（Loop 3 反映）**: app_settings の `environment` キーは Common Keys（D1 §3.1 の row 属性 `environment`）と命名衝突する懸念あり。本 M では **`runtime_environment`** にリネーム採用、Common Keys 側は変更せず。詳細は §13 IP2-Q6 を参照。

**テスト条件**:
- Migration: seed 追加で既存 migration roundtrip 破壊なし
- Unit: 新規 query 各個

**リスク**:
- seed 追加で既存 test が失敗 → 追加のみで削除 / 変更せず

**後続依存**: M19（新 panel が新 query を使う）、M20（TSS mart が query に追加される）

---

### 6.7 M19: Dashboard 残り 3 Panel + Real Data 結線

**目的**: `Mi-DASH-1` 解消。Iter1§13 Dashboard 残り 3 panel の実装と、既存 7 panel の実 DB データ表示確認。

**入力**:
- M18 query service 拡張
- Iter1 M12 panel 7 本
- Carryover: **Mi-DASH-1**

**サイクル境界（責務分離、Loop 2 反映）**:
- **Cycle 19-A**: 3 panel 新規追加（top_candidates / execution_quality / risk_state_detail）
- **Cycle 19-B**: 既存 7 panel の実 DB 結線 + real data integration test
- **Cycle 19-C**: 10 panel レイアウト確定 + Streamlit ブラウザ目視手順 docs

**「改善分析ビュー」の扱い（Loop 3 反映）**: `iteration1_implementation_plan.md` §13 行 760 では「残り 3 パネル（トップ候補一覧 / 執行品質 / リスク状態 詳細 / 改善分析ビュー）」と 4 名挙げられているが「3 パネル」と明記されている。本 Iteration では先頭 3 つのみ実装し、**「改善分析ビュー」は §10.1 に従い Phase 7 送り**（Backtest Engine + AIStrategy 完成後に意味を持つビューのため）。

**変更対象**:
- `src/fx_ai_trading/dashboard/panels/top_candidates.py`（Cycle 19-A、dashboard_top_candidates mart から）
- `src/fx_ai_trading/dashboard/panels/execution_quality.py`（Cycle 19-A、execution_metrics 集計）
- `src/fx_ai_trading/dashboard/panels/risk_state_detail.py`（Cycle 19-A、risk_events + positions 詳細）
- `src/fx_ai_trading/dashboard/app.py`（Cycle 19-C、10 panel レイアウト、既存 row 構成維持）
- `tests/integration/test_dashboard_real_data.py`（Cycle 19-B、実 SQLite で 10 panel 全て fallback 無し表示）
- `docs/dashboard_manual_verification.md`（Cycle 19-C、目視手順）

**完了条件**:
- [ ] 10 panel 全てが実 DB 接続下でデータ表示（mock 除く）
- [ ] `st.cache_data(ttl=5)` 全 panel 適用
- [ ] 既存 7 panel の表示を破壊しない（**panel 単体 test は現状不在のため、本 M で `test_dashboard_real_data.py` を唯一の panel 検証経路とする**）
- [ ] DB 接続失敗時は既存 graceful fallback を保持

**テスト条件**:
- Integration: 実 SQLite に seed + panel render → 10 panel dataframe 非 empty
- Manual: `streamlit run` でブラウザ確認（目視テスト項目を docs に記載）

**リスク**:
- 10 panel の streamlit レイアウトが肥大 → 3 tab 構成に分割検討
- 大量 polling で DB 負荷 → cache ttl + connection pool（既存設計踏襲）

**後続依存**: M20（top_candidates panel は TSS mart から）

---

### 6.8 M20: TSS Calculation + dashboard_top_candidates Mart

**目的**: Iter1§13 TSS 計算と `dashboard_top_candidates` mart 生成。

**正当化（Loop 2 反映）**: TSS + mart は **MVP §12 #9（PostgreSQL 全ログ + Common Keys で 1 本 SQL 分析可能）** を実現するための集計ビュー。mart なしでは M-METRIC-1 が解消しても「1 本 SQL 分析」が困難。よって Iteration 2 必須。ただし本 Iteration は **最小 3 instrument（USDJPY / EURUSD / GBPUSD）のみ**、フル instrument / 重み詳細チューニングは Iteration 3。

**入力**:
- Iter1 M9 MetaDecider / strategy_signals、Iter1 M5 aggregates repository

**事実訂正（Loop 3 反映）**: Loop 1/2 では「`dashboard_top_candidates` mart は Iter1 で既に schema に存在」と前提していたが、`docs/schema_catalog.md` および `migrations/versions/0001-0010` を grep した結果 **当該テーブルは未存在**。よって本 M で **migration 0012 として新規 CREATE TABLE が必須**。これにより Iter2 全体で **新規テーブル +1 件**（合計 42 物理 → 43 物理 + ローカル 2 ファイル）。MVP §12 #2 の数値も §9 で訂正する。

**変更対象**:
- `src/fx_ai_trading/services/tss_calculator.py`（新規、TSS 計算ロジック）
- `src/fx_ai_trading/services/mart_builder.py`（新規、dashboard_top_candidates mart 生成）
- `src/fx_ai_trading/services/mart_scheduler.py`（新規、周期実行）
- **`alembic/versions/0012_dashboard_top_candidates_table.py`**（**新規 CREATE TABLE**、schema_catalog.md にも追記）
- `docs/schema_catalog.md`（新規テーブル登録、グループ H Aggregates 配下）
- `tests/migration/test_dashboard_top_candidates_schema.py`（新規）
- `tests/unit/test_tss_calculator.py`
- `tests/unit/test_mart_builder.py`
- `tests/integration/test_mart_refresh.py`

**完了条件**:
- [ ] TSS が `{score, components: [...], horizon_min}` で返却
- [ ] mart が 15 分毎に refresh（fake clock でテスト）
- [ ] `dashboard_top_candidates` テーブルが migration 0012 で CREATE され、top N 行が INSERT（UPSERT）
- [ ] M19 の top_candidates panel が mart から読み出し
- [ ] 対象 instrument は **USDJPY / EURUSD / GBPUSD の 3 本のみ**（Iteration 2 限定範囲）
- [ ] schema_catalog.md にテーブル定義（列 / PK / FK / 粒度 / 更新方針 / 保持クラス / 正本 / 下流消費者）を追加

**テスト条件**:
- Unit: TSS 計算の決定性
- Unit: mart builder 単体
- Integration: scheduler 発火 → mart 更新

**リスク**:
- TSS の重み設計が未成熟 → **Decision**: 初期は MetaDecider score + confidence の線形結合、詳細チューニングは Iteration 3

**後続依存**: M19（panel 表示）

---

### 6.9 M21: Learning UI + LearningOps Minimal

**目的**: `M-LRN-1` 解消。学習 UI（enqueue / status / history）と LearningOps の最小スケルトン。

**入力**:
- Iter1 M12 dashboard、D3 ModelRegistry Protocol、system_jobs table
- Carryover: **M-LRN-1**

**変更対象**:
- `src/fx_ai_trading/dashboard/panels/learning_ops.py`（新規、enqueue / status / history UI）
- `src/fx_ai_trading/services/learning_ops.py`（新規、system_jobs 経由の enqueue/status、本 Iteration は stub 実行器）
- `src/fx_ai_trading/services/dashboard_query_service.py`（`get_learning_jobs` 追加）
- **`docs/implementation_contracts.md` への `LearningExecutor` Protocol 新規追加**（D3 §2.3 系または ModelRegistry 近傍に追加。Loop 3 で D3 不在を確認）
- `tests/integration/test_learning_ops_ui.py`
- `tests/unit/test_learning_ops_service.py`

**完了条件**:
- [ ] enqueue: UI から training job を system_jobs に INSERT（status=PENDING）
- [ ] status: PENDING / RUNNING / COMPLETED / FAILED を UI で表示
- [ ] history: 過去 N 件の training_runs を表示
- [ ] 本 Iteration の executor は stub（即座に COMPLETED、model_registry に dummy entry）
- [ ] Phase 7 の本 LearningOps を差し込める Interface（`LearningExecutor` Protocol）を D3 に新規宣言

**テスト条件**:
- Integration: enqueue → status → history の一連
- Unit: LearningOps service 単体

**リスク**:
- 本 executor の責務範囲 → **Decision**: Iteration 2 は stub のみ、実学習は Phase 7

**後続依存**: Phase 7（本 executor 実装時に差し替え）

---

### 6.10 M22: ctl CLI Process Management + 2-Factor Emergency Flat

**目的**: `Mi-CTL-1` 解消 + Iter1§13 Emergency Flat 2-factor。ctl の start / stop が実 process を起動・停止、emergency-flat-all に 2-factor confirmation を付与。

**入力**:
- Iter1 M12 ctl stub、M13 live confirmation gate
- Carryover: **Mi-CTL-1**

**変更対象**:
- `scripts/ctl.py`（start / stop / **resume-from-safe-stop / run-reconciler** / emergency-flat-all）
- `src/fx_ai_trading/ops/process_manager.py`（新規、Supervisor subprocess 管理 + PID 記録）
- `src/fx_ai_trading/ops/two_factor.py`（新規、confirmation token 検証）
- **`docs/implementation_contracts.md` への `TwoFactorAuthenticator` Protocol 新規追加**（D3 §2.13 Config/Assertion 層、Phase 8 SSO 版に差し替え可能な形で。Loop 3 で D3 不在を確認）
- **`docs/operations.md` §3.1 許可介入表 / §11 Cheat Sheet の同期更新**（emergency-flat-all に **2-factor 必須**を明記、resume-from-safe-stop / run-reconciler を ctl 一覧に追加）
- `tests/contract/test_emergency_flat_two_factor.py`
- `tests/integration/test_ctl_start_stop.py`
- `tests/integration/test_ctl_resume_from_safe_stop.py`（新規、Step 7 SafeStopJournal↔DB 突合 / Step 14 OutboxProcessor resume の wiring 確認）

**ctl 既存 test 不在の扱い（Loop 3 反映）**: `tests/contract/test_ctl_*.py` / `tests/integration/test_ctl_*.py` は現状不在。本 M で全 ctl サブコマンドの新規 test を投入する（既存破壊の懸念なし）。

**完了条件**:
- [ ] `ctl start` が Supervisor を background process として起動、PID を `logs/supervisor.pid` に記録
- [ ] `ctl stop` が SIGTERM → graceful wait → SIGKILL の階段で停止
- [ ] `ctl resume-from-safe-stop --reason=...` が `operations.md` §11 仕様に整合
- [ ] `ctl run-reconciler` が手動 reconciliation を起動可能
- [ ] `ctl emergency-flat-all` が 2-factor（token + 対話確認）を経て実行、log + Notifier critical 送出
- [ ] 2-factor は Interface（D3 `TwoFactorAuthenticator`）として定義され、Phase 8 の SSO 版に差し替え可能
- [ ] `operations.md` §3.1 / §11 が **2-factor 必須**および新 ctl サブコマンドを反映済

**テスト条件**:
- Contract: 2-factor 失敗時の実行拒否
- Integration: start → stop の process lifecycle

**リスク**:
- Windows / Linux の process 管理差分 → `subprocess.Popen` + psutil で吸収
- PID stale → start 時に既存 PID 有効性を psutil で検証

**後続依存**: M25（新契約 hardening）

---

### 6.11 M23: Supabase Projector + Secondary DB Snapshot

**目的**: Iter1§13 Supabase Projector 実装。PostgreSQL の supervisor_events / positions / close_events を Supabase に定期 snapshot。

**入力**:
- Iter1 M5 Repository、Iter1§13
- **Loop 3 訂正**: 既存 D3 に `ProjectionTransport` Protocol は不在。本 M で D3 に **新規追加**する（grep 確認済）

**スコープ縮約（Loop 2 反映）**: Iter2 は **Projector Interface + 1 テーブル（supervisor_events）の Mock snapshot のみ**。本運用（4 テーブル + retry / schema 整合）は **Phase 7 Cold Archive と併合して再設計**する。これにより M23 の工数を 2–3 日 → 1–2 日に圧縮、Iteration 2 の MVP 達成を優先。

**変更対象**:
- `src/fx_ai_trading/adapters/projector/supabase.py`（新規、Supabase クライアント骨格のみ）
- `src/fx_ai_trading/services/projection_service.py`（新規、supervisor_events の snapshot のみ）
- **`docs/implementation_contracts.md` への `ProjectionTransport` Protocol 新規追加**（D3 §2.9 Persistence 層 or §2.14 Event/Transport 層に追加）
- `tests/contract/test_projection_transport.py`（Interface 契約）
- `tests/integration/test_supabase_projector.py`（MockSupabaseClient で supervisor_events のみ）

**完了条件**:
- [ ] Projector Interface（`ProjectionTransport` Protocol）が D3 に定義済
- [ ] `supervisor_events` のみ 5 分毎に Mock Supabase へ upsert（実 Supabase 疎通は manual runbook のみ）
- [ ] 失敗時は log warn + retry_events、次周期で再試行
- [ ] Common Keys が一次 DB 側で保持されている（Projector 側は pass-through）
- [ ] **他 3 テーブル（positions / close_events / orders）は Phase 7 で拡張予定と明示**
- [ ] **Projector ≠ Archiver**: 5 分 snapshot は `retention_policy.md` §13.1 Archiver（日次 02:00 UTC）とは別経路。`supervisor_events` の `SUPERVISOR_PERMANENT` 制約に対し Projector は **読取/upsert のみで Delete しない**ため retention 衝突なし

**テスト条件**:
- Contract: ProjectionTransport Protocol 整合
- Integration: MockSupabaseClient で差分 upsert

**リスク**:
- Supabase 依存 → **Decision**: Interface 経由で SupabaseClient を差し替え可能にし、Iter2 でテストは Mock のみ（実 Supabase 疎通は docs の manual runbook）

**後続依存**: Phase 7（Cold Archive が Projector 系を再利用）

---

### 6.12 M24: Alembic Modernization + multi_service_mode Interface Expansion

**目的**: `Ob-ALEMBIC-1` 解消 + Iter1§13 multi_service_mode Interface 拡張。

**入力**:
- Iter1 M2 alembic config、Carryover: **Ob-ALEMBIC-1**

**multi_service_mode の Iteration 2 範囲（Loop 3 反映）**: `iteration1_implementation_plan.md` §13 行 765 では「multi_service_mode **実運用**（MVP は Interface のみ）」と記載されているが、本書 §10.1 で **Phase 7 送り**に再分類。Iter2 では「**Interface 宣言 + 接続点定義のみ**」に範囲縮小。理由は (a) container_ready_mode のオーケストレータ選定が未確定、(b) Iter2 完了条件は MVP §12 の Full 化に集中させたいため。iter1§13 の「実運用」表現は本書で **「Interface 拡張」**へ更新。

**変更対象**:
- `alembic.ini`（`path_separator = os` 追加、`version_path_separator` 移行）
- `alembic/env.py`（必要なら migration DeprecationWarning 解消）
- `src/fx_ai_trading/ops/service_mode.py`（新規、`ServiceMode` Interface 宣言、接続点定義）
- **`docs/implementation_contracts.md` への `ServiceMode` Interface 新規追加**（D3 §2.14 EventBus 周辺。Loop 3 で D3 不在を確認）
- `tests/migration/test_migration_chain.py` / `test_schema_coverage.py` / `test_roundtrip.py`（既存、alembic 設定変更で 3 本全てに影響、green 維持）
- `docs/operations.md`（service_mode 運用ガイドライン追記）
- `tests/migration/test_alembic_no_deprecation.py`（warning 0 件）

**完了条件**:
- [ ] `pytest tests/migration/` 実行時に alembic deprecation warning が 0 件
- [ ] migration up/down/up が破壊されない
- [ ] `service_mode.py` が single_process_mode / multi_service_mode / container_ready_mode の Interface を宣言
- [ ] 本 Iteration では single_process_mode のみ実運用（他 2 モードは Interface のみ、Phase 7 送り明示）

**テスト条件**:
- Migration: deprecation warning 0 件
- Migration: 既存 roundtrip 保持

**リスク**:
- alembic 設定変更で既存 migration 破壊 → 事前に roundtrip を緑のまま維持

**後続依存**: なし（独立）

---

### 6.13 M25: Iteration 2 Contract Hardening + E2E Suite Extension

**目的**: Iteration 2 で新規導入した契約を CI で machine-enforce、paper smoke を exit stage まで延伸。

**入力**:
- M13–M24 全て、Iter1 M11 contract tests
- Carryover: **M-EXIT-1 の最終検証**

**変更対象**:
- `tests/integration/test_paper_smoke_end_to_end.py`（Stage 6-7 追加: ExitPolicy 発火 + close_event）
- `tests/contract/test_iteration2_invariants.py`（新規、統合契約）
- `tests/contract/test_forbidden_patterns.py`（既存、lint 拡張で期待 pattern 数を更新）
- `.github/workflows/ci.yml`（Iteration 2 contract-tests ジョブ拡張）
- `tools/lint/custom_checks.py`（新禁止 pattern: live API key の secret 外漏れ、2-factor bypass）

**lint (a) 方針反転の明示（Loop 3 反映）**: 既存 `tools/lint/custom_checks.py` docstring（行 24 周辺）では「Secret / PII values in log messages — too many false positives, human-review 扱い」とされていた。本 M で **(a) live API key の検出を machine 化**するが、false positive を抑えるため対象を厳格に絞る:
- 限定正規表現（例: `OANDA_LIVE_TOKEN=`, `.*-live-[A-Za-z0-9]{32,}` 等の live key 固有 prefix）
- src/ のみ適用（test/ tool/ は除外）
- 方針変更コメントを `custom_checks.py` の docstring に明記

**lint (b) bypass pattern 確定タイミング**: 2-factor の AST 形が M22 完成まで未確定のため、本 M 内部順序として **M22 → M25 lint 追加** を遵守。

**完了条件（Loop 2 反映: 新契約 7 本具体列挙）**:
- [ ] paper smoke が 7 Stage 完走（Stage 7 = close_event 記録確認）
- [ ] 既存 contract 15 本の green 維持
- [ ] **Iteration 2 新契約 7 本以上が CI 対象**:
  1. `tests/contract/test_live_confirmation_gate.py`（M13）
  2. `tests/contract/test_oanda_broker_account_type.py`（M13）
  3. `tests/contract/test_exit_policy_rules.py`（M14）
  4. `tests/contract/test_exit_event_fsm.py`（M14）
  5. `tests/contract/test_email_notifier.py`（M17）
  6. `tests/contract/test_emergency_flat_two_factor.py`（M22）
  7. `tests/contract/test_projection_transport.py`（M23）
- [ ] 禁止 lint が Iteration 1 時点から 2 項目以上追加: **(a)** live API key の secret 外漏れ検出（限定正規表現 + src/ only + 方針反転コメント）、**(b)** 2-factor bypass パターン検出（M22 完成後に AST pattern 確定）
- [ ] `tests/contract/test_forbidden_patterns.py` の期待 pattern 数を 2 項目分増やしても green

**テスト条件**:
- Integration: paper smoke Stage 1–7 完走
- Contract: 新契約集約 green
- CI: 新禁止 lint が意図違反 commit を弾く

**リスク**:
- 新契約と既存契約の衝突 → 既存を非変更ルールで追加

**後続依存**: Iteration 2 完了判定

---

### 6.14 M26: UI / Console Operational Boundary Spec Freeze (docs only)

**目的**: Iteration 3 以降に実装される Operator Console / Configuration Console の責務境界・secret/config UI ルール・Phase 8 送り境界を、本 Iteration で**コード変更なしに 6 docs へ凍結**する。実装ではなく**仕様の不変式化**を責務とする独立マイルストーン。

**位置付け**:
- M22 (ctl CLI 5 コマンド) と一致しない: M22 は CLI 実装、M26 は UI 経由境界の仕様。Operator Console は M22 の薄ラッパだが、Configuration Console は M22 と無関係 (`.env` sink + `app_settings_changes` キュー)
- M25 (contract hardening) と分離: M25 はコード contract test、M26 は docs 整合性凍結。責務トーンが異なる
- 実装は本 Iteration では**行わない**: Iter3 以降の別 PR で具体化、M26 は「実装が境界を逸脱しないための事前固定」

**入力**:
- `docs/iteration2_implementation_plan.md` §2.1 / §10.2 / §13 (本 M で更新済)
- `docs/operations.md` §1.1 / §3.1 / §11 / §14 (既存運用契約)
- `docs/development_rules.md` §10 / §13.1 (既存 secret/config ルール)
- `docs/implementation_contracts.md` §1 / §2.13.2 SecretProvider / §2.14.2 ServiceMode
- `docs/design.md` 付録 (全体不変条件 #7)
- `docs/phase6_hardening.md` §6.13 / §6.18 (4 重防御)
- `docs/phase8_roadmap.md` §2.3 / §5.3 (Phase 8 送り先の妥当性)
- `docs/schema_catalog.md` §2 #42 (`app_settings_changes` 実列名)

**変更対象** (6 docs only、コード変更なし):
1. `docs/iteration2_implementation_plan.md`: §2.1 / §10.2 / §13 IP2-Q8 / §5 / §6.14 / §8 / §15
2. `docs/operations.md`: §3.1 表に「UI 経由可否 (Iter3+)」列追加 / §15 新設 (15.1–15.6)
3. `docs/development_rules.md`: §10.3.1 新設 / §13.1 #16 追加 / §15 #9 を「Code 16 項目」化
4. `docs/implementation_contracts.md`: §2.15 新設 (新規 Protocol 不導入、UI/Console 層責務契約)
5. `docs/design.md`: 付録 #7 に UI 4 層境界 + `.env` sink 限定の 1 文追記
6. `docs/phase6_hardening.md`: §6.18 末尾に UI 経由 demo↔live 4 重防御継続の段落追記

**完了条件**:
- [ ] **UI 責務境界の確定**: 4 層 (Secret / Runtime 接続 / Runtime mode / Operational) が operations.md §15.1 と implementation_contracts.md §2.15 で完全一致
- [ ] **Console 種別ごとの責務確定**: Configuration Console (2 モード: 起動前 / 稼働中) と Operator Console (M22 ctl 5 コマンドラッパ、`emergency-flat-all` 除く 4 コマンド) と Learning UI (M21 別系統) の 3 種別が 6 docs 間で混同なく分離
- [ ] **secret/config UI ルールの確定**: `.env` sink 限定 / DB 平文書込禁止 (`app_settings_changes` 実列 `old_value` / `new_value` 名指し) / SecretProvider 書込 IF 不導入が development_rules.md §10.3.1 / operations.md §15.4 / implementation_contracts.md §2.15 で一貫
- [ ] **Phase 8 送り境界の確定**: SSO/multi-user / Streamlit 卒業→Next.js+FastAPI / `dashboard_operations_audit` (仮称) / SecretProvider 書込 IF が iteration2_plan.md §10.2 / operations.md §15.6 / implementation_contracts.md §2.15 / phase8_roadmap.md §2.3/§5.3 と矛盾なし
- [ ] **6 docs 間 cross-reference の reachability**: 相互参照リンク (operations §15 ↔ contracts §2.15 ↔ rules §10.3.1/§13.1#16 ↔ plan §2.1/§10.2/IP2-Q8 ↔ design 付録#7 ↔ phase6 §6.18) が全て到達可能
- [ ] **既存 M13–M25 への非影響**: 本 M で他 M の責務・完了条件・テスト条件を変更しない (docs only スコープの厳守)

**テスト条件**:
- **本 M はコード変更なしのため CI test 追加なし**。代替として 6 docs 整合性レビューを必須とする:
  - Designer 役による cross-document consistency review (役割境界 / Iter2 切り分け / secret-config / operations / hardening / D3-rules / 将来計画 の 7 観点)
  - Developer 役による diff verification review (ID/参照整合性 / cross-link reachability / ctl コマンド名一貫性 / 数値・table 名整合 / typo / scope creep の 6 観点)
  - Evaluator 役による Go/No-Go 判定。Blocker または Major 検出時は Designer 差戻し (CLAUDE.md §6)

**リスク**:
- **仕様凍結が Iter3 実装時の制約として機能しない**: 凍結文言が抽象的すぎると Iter3 で形骸化 → 6 docs 全てに「実装は Iter3 以降の別 PR、本 Iter は仕様凍結のみ」を明示し、IP2-Q8 で実装着手 Iteration を Open Question 化済
- **`dashboard_operations_audit` (仮称) のテーブル名が Phase 8 着手時に変わる**: 3 文書 (plan / operations / contracts) で「仮称、Phase 8 で正式テーブル名確定」と明示済、phase8_roadmap §5.3 が正本
- **scope creep (Iter2 で UI 実装まで踏み込む)**: 完了条件・変更対象を docs only に限定、コード/テスト/migration の追加禁止を CLAUDE.md §10 / §11 で担保

**後続依存**:
- **Iteration 3 UI 実装**: 本 M で凍結された 4 層境界 / Configuration Console 2 モード / Operator Console = M22 ctl 5 コマンドラッパ契約に従って Streamlit 拡張 or 別 entry point として実装
- **Phase 8 UI 刷新**: SSO/multi-user / `dashboard_operations_audit` (仮称) 正式名確定 / Next.js+FastAPI 移行 / SecretProvider 書込 IF 追加が Phase 8 で本 M 境界の再評価対象 (operations.md §15.6)

---

## 7. Carryover Mapping

`docs/iteration1_completion.md` §4 の全 ID と担当 M の対応表。

### 7.1 Major → Milestone

| Carryover ID | 主担当 M | 副担当 M | 完了条件との対応 |
|--------------|---------|---------|-----------------|
| **M-EXIT-1** | M14 | M25 | §6.2 完了条件 全 5 項 + §6.13 Stage 7 |
| **M-METRIC-1** | M16 | M23 | §6.4 完了条件 全 5 項 |
| **M-LRN-1** | M21 | — | §6.9 完了条件 全 5 項 |

### 7.2 Minor → Milestone

| Carryover ID | 主担当 M | 副担当 M | 完了条件との対応 |
|--------------|---------|---------|-----------------|
| **Mi-CTL-1** | M22 | M13 | §6.10 完了条件（start/stop 実 process + 2-factor）+ §6.1（live gate） |
| **Mi-DASH-1** | M19 | M18 | §6.7 完了条件（10 panel 実データ）+ §6.6（query / seed） |

### 7.3 Observation → Milestone

| Carryover ID | 主担当 M | 備考 |
|--------------|---------|------|
| **Ob-ALEMBIC-1** | M24 | deprecation warning 0 件化 |
| **Ob-MIDRUN-1** | M15 | MidRunReconciler 実体 + 11 ケース全網羅 |
| **Ob-PANEL-FALLBACK-1** | M18 | app_settings seed 拡張 |

### 7.4 逆引き（Milestone → Carryover）

| M | Carryover | 解消状態 |
|---|-----------|---------|
| M13 | (Mi-CTL-1 副) | 副担当として live gate 提供 |
| M14 | M-EXIT-1 主 | 主担当 |
| M15 | Ob-MIDRUN-1 主 | 主担当 |
| M16 | M-METRIC-1 主 | 主担当 |
| M17 | — | Iter1§13 only |
| M18 | Ob-PANEL-FALLBACK-1 主、Mi-DASH-1 副 | 副担当で query 拡張 |
| M19 | Mi-DASH-1 主 | 主担当 |
| M20 | — | Iter1§13 only |
| M21 | M-LRN-1 主 | 主担当 |
| M22 | Mi-CTL-1 主 | 主担当 |
| M23 | M-METRIC-1 副 | 副担当で二次 DB snapshot |
| M24 | Ob-ALEMBIC-1 主 | 主担当 |
| M25 | M-EXIT-1 副 | 副担当で E2E Stage 7 検証 |

---

## 8. Recommended Order

### 8.1 Dependency Graph

```
M13 (OANDA Live/Gate) ──┐
M14 (ExitPolicy)        ├→ M25 (Contract + E2E extension)
M15 (Reconciler Full)   │
M16 (Metrics Loop)      │
M17 (EmailNotifier)     │
                        │
M18 (Query/Seed ext) → M19 (3 panel + real data)
                     → M20 (TSS + mart) ──┐
                                          ├→ (M19 top_candidates 表示)
M21 (Learning UI)       ──┐
M22 (ctl + 2-factor)    ←─ M13 ──→ M26 (UI/Console spec freeze, docs only)
M23 (Supabase Projector)
M24 (Alembic + MSM I/F)
```

### 8.2 並列可能 / 直列

**並列可能**:
- M13 と M14 と M15 と M16 と M17（独立、M25 で合流）
- M21 と M22 と M23（独立）
- M18 と M24（独立）
- M26（docs only、M22 確定後であれば他 M と並列可、M25 とも独立）

**直列必須**:
- M18 → M19 → M20（Dashboard の積み上げ）
- M13 → M22（live confirmation を ctl が使う）
- M13–M24 → M25（最終契約 hardening）
- M22 → M26（M22 で ctl 5 コマンドが確定してから UI 仕様凍結に進む。M26 は docs only のため M25 と並列でも可）

### 8.3 推奨実装順

1. M24（alembic modernization、低リスクから）
2. M13 + M17 並行（Broker / Notifier 基盤）
3. M14（ExitPolicy、M-EXIT-1 最優先）
4. M15（Reconciler Full）
5. M16（Metrics Loop）
6. M18 → M19 → M20（Dashboard 積み上げ）
7. M21 + M22 並行
8. M23（Projector）
9. M25（最終契約 + E2E）
10. M26（UI/Console 仕様凍結、docs only。M22 確定後であれば M25 と並列可、Iter2 PR 列の最後に位置付け）

---

## 9. MVP / Completion Criteria

Iteration 2 完了 = MVP §12 の 10 項目全てが **Full**:

| # | 条件 | 対応 M | Iter1 時点 | Iter2 目標 |
|---|------|--------|-----------|-----------|
| 1 | M13-M25 完了 | 全 M | — | **Full** |
| 2 | alembic **42 + 1 = 43 物理テーブル + 2 ローカル**（Loop 3 訂正） | M20 (新 1) + M24 保持 | Full (42) | **Full (43)** |
| 3 | `ctl start` で 16 Step green | M22 | Partial | **Full** |
| 4 | 1 cycle 発注→擬似約定→**決済** | M14 + M25 | 未達 | **Full** |
| 5 | Streamlit 10 panel 実データ | M19 | Partial | **Full** |
| 6 | 学習 UI 最小機能 | M21 | 未達 | **Full** |
| 7 | safe_stop 正常発火 | — | Full | Full 維持 |
| 8 | Contract + 禁止 lint | M25 | Full | Full 拡張 |
| 9 | PostgreSQL 全ログ + 1 本 SQL 分析 | M16 + M23 | 未検証 | **Full** |
| 10 | Notifier 二経路 + Email | M17 | Full | Full 拡張 |

**Iteration 2 完了宣言条件**:
1. 上記 10/10 Full
2. Carryover 8 件全て `resolved by Iteration 2 M-xx` と `iteration1_completion.md` に対応可能
3. 既存 contract 15 本 + 新規 7 本以上 CI green
4. paper smoke 7 Stage 完走
5. Blocker 0 + Major 0

**MVP #2（alembic tables 数）の明示（Loop 3 で訂正）**: Iter1 時点は **42 物理テーブル + 2 ローカルファイル**（schema_catalog.md 行 4 確認、Loop 1/2 で「46」と誤記していたのを訂正）。Iter2 では M20 で `dashboard_top_candidates` を **新規 CREATE TABLE**（migration 0012）するため **+1 で 43 物理 + 2 ローカル = 45 とカウント**。app_settings の **seed 追加**（phase_mode / runtime_environment）はテーブル数に影響しない。

---

## 10. Deferred Items

Iteration 2 でも触らず、明示的に Phase 7 / Phase 8 へ送る項目。

### 10.1 Phase 7 送り

- Backtest Engine 実体（`BacktestRunner.run()` 実装、SlippageModel / LatencyModel 決定的実装、反実仮想計算）
- AIStrategy 本物モデル（学習 + 推論 + shadow→active Promotion 自動化）
- 相関双窓 regime tightening の MetaDecider Select 強制適用
- Drift detection 本実装（PSI / KL / 残差）
- EVCalibrator v1 以降
- Cold Archive 実ジョブ（retention_policy 遵守）
- Chaos Engineering 体系化（fault injection シナリオカタログ）
- CI 自動マイグレーションテスト
- Streamlit 卒業条件超過時の UI 刷新（Next.js + FastAPI）
- LearningOps 本 executor（Iteration 2 は stub のみ）
- multi_service_mode / container_ready_mode の本運用（Iteration 2 は Interface 宣言 + 接続点定義のみ。iter1§13 行 765「実運用」表現は本書で「Interface 拡張」へ再分類）
- ExitPolicy の partial close（Iteration 2 は 100% close のみ）
- **Supabase Projector の本運用 4 テーブル対応**（Iteration 2 は supervisor_events のみ Mock）
- **OANDA live 実発注の運用解禁**（Iteration 2 は demo only、live 経路はコード存在のみで CI は demo 強制）
- **TSS フル instrument / 重みチューニング**（Iteration 2 は 3 instrument 限定）
- **Dashboard「改善分析ビュー」panel**（iter1§13 行 760 で名称言及、本 Iter は §6.7 サイクル境界で対象外。Backtest Engine + AIStrategy 実装後に意味を持つビュー）
- **app_settings 関連 retention 通知 5 イベント**（`archive.verify_failed` / `backup.pg_dump_failed` 等、retention_policy §13.2）の機械検出 + Notifier critical 経路統合
- **L1/L2 jsonl ローテーション本実装**（`safe_stop.jsonl` 180d / `notifications.jsonl` 90d、retention_policy §3.2）

### 10.2 Phase 8 送り

- OAuth / SSO Notifier
- Slack 双方向運用（コマンド受付、安全装置付き）
- Dashboard SSO / マルチユーザ
- DR 訓練月次体系化
- 税務エクスポート GUI
- Emergency Flat の 2-factor を超える権限分離（Iteration 2 は 2-factor 止まり）
- **Operator/Configuration Console 本実装**（Iter2 はドキュメント仕様のみ。実装は Iteration 3 以降の別 PR）
- **SecretProvider 書込 Interface（rotate / set）**（Iter2 は read-only `get/get_hash/list_keys` のまま、UI 経由 secret 書込 sink は `.env` に限定）
- **`dashboard_operations_audit` テーブル**（**仮称、Phase 8 で正式テーブル名確定**、UI 操作監査、Phase 8 SSO/multi-user とセットで導入。schema_catalog の現 43 表体系には未登録、Iter2 は ctl 系の既存 audit のみで足りる）

---

## 11. Testing Strategy Summary

### 11.1 新規テストファイル一覧（具体名、Loop 2 反映）

| 担当 M | 層 | ファイル |
|--------|---|---------|
| M13 | contract | `tests/contract/test_live_confirmation_gate.py` |
| M13 | contract | `tests/contract/test_oanda_broker_account_type.py` |
| M13 | integration | `tests/integration/test_oanda_demo_connection.py` |
| M14 | contract | `tests/contract/test_exit_policy_rules.py` |
| M14 | contract | `tests/contract/test_exit_event_fsm.py` |
| M14 | integration | `tests/integration/test_exit_flow.py` |
| M14 | unit | `tests/unit/test_exit_policy.py` |
| M15 | contract | `tests/contract/test_reconciler_action_matrix.py`（既存拡張） |
| M15 | contract | `tests/contract/test_rate_limiter_buckets.py` |
| M15 | integration | `tests/integration/test_midrun_reconciler_bucket_switch.py` |
| M15 | integration | `tests/integration/test_stream_watchdog_gap_detection.py` |
| M16 | contract | `tests/contract/test_supervisor_metrics_schema.py` |
| M16 | integration | `tests/integration/test_metrics_loop.py` |
| M17 | contract | `tests/contract/test_email_notifier.py` |
| M17 | integration | `tests/integration/test_email_dispatch.py` |
| M18 | migration | `tests/migration/test_app_settings_phase_mode_seed.py` |
| M18 | unit | `tests/unit/test_dashboard_query_service.py`（**新規作成**、既存不在のため base + 拡張 query を統合） |
| M19 | integration | `tests/integration/test_dashboard_real_data.py` |
| M20 | unit | `tests/unit/test_tss_calculator.py` |
| M20 | unit | `tests/unit/test_mart_builder.py` |
| M20 | integration | `tests/integration/test_mart_refresh.py` |
| M20 | migration | `tests/migration/test_dashboard_top_candidates_schema.py`（migration 0012 新規 CREATE TABLE） |
| M21 | integration | `tests/integration/test_learning_ops_ui.py` |
| M21 | unit | `tests/unit/test_learning_ops_service.py` |
| M22 | contract | `tests/contract/test_emergency_flat_two_factor.py` |
| M22 | integration | `tests/integration/test_ctl_start_stop.py` |
| M22 | integration | `tests/integration/test_ctl_resume_from_safe_stop.py`（Step 7/14 wiring） |
| M23 | contract | `tests/contract/test_projection_transport.py` |
| M23 | integration | `tests/integration/test_supabase_projector.py` |
| M24 | migration | `tests/migration/test_alembic_no_deprecation.py` |
| M25 | integration | `tests/integration/test_paper_smoke_end_to_end.py`（既存拡張） |
| M25 | contract | `tests/contract/test_iteration2_invariants.py` |

### 11.2 集計（Loop 3 反映）

| 層 | 追加 |
|---|------|
| unit | 4 本 |
| contract | 8 本（新規）+ 既存拡張 1 本 = 9 本 |
| integration | 15 本（新規、ctl resume 追加）+ 既存拡張 1 本 = 16 本 |
| migration | 3 本（M18 / M20 / M24） |
| **総計** | **31 本（新規）+ 2 本（既存拡張）** |

### 11.3 既存テストへの影響範囲（Loop 3 追加）

各 M の変更が既存 511 test のうちどれに触るかを明示。Iter1 完了時の green 状態を破壊しないために本表を実装時の必読チェックリストとする。

| M | 影響可能性ある既存 test | 対応 |
|---|------------------------|------|
| M13 | `tests/contract/test_broker_account_type_assertion.py` | account_type assertion 契約を非破壊で拡張 |
| M14 | `tests/contract/test_order_fsm.py` / `tests/contract/test_outbox_transaction.py` | exit_executor が orders/outbox 経路に触るため両 FSM 維持必須 |
| M15 | `tests/contract/test_safe_stop_fire_sequence.py` / `tests/integration/test_in_flight_order_handling.py` / `tests/integration/test_safe_stop_journal.py` | safe_stop / in-flight / journal 全て非破壊 |
| M16 | `tests/integration/test_startup_sequence.py` | 16 Step に metrics_loop 起動挿入、startup_sequence 整合 |
| M17 | `tests/contract/test_notifier_two_path.py` / `tests/contract/test_forbidden_patterns.py` | 二経路 contract + SMTP 認証情報 lint |
| M18 | `tests/integration/test_app_settings_repository.py` / `tests/migration/test_migration_chain.py` / `test_schema_coverage.py` / `test_roundtrip.py` | seed + migration 0011 で全 4 本影響 |
| M19 | （既存 panel test 不在） | 影響なし、新規 `test_dashboard_real_data.py` のみ |
| M20 | `tests/migration/test_migration_chain.py` / `test_schema_coverage.py` / `test_roundtrip.py` | migration 0012 新規 CREATE で 3 本影響 |
| M22 | （既存 ctl test 不在） | 影響なし、全 ctl test を本 M で新規投入 |
| M24 | `tests/migration/test_migration_chain.py` / `test_schema_coverage.py` / `test_roundtrip.py` | alembic.ini 改修で 3 本影響 |
| M25 lint | `tests/contract/test_forbidden_patterns.py` | lint 拡張で期待 pattern 数を 2 増 |

---

## 12. Risks & Mitigations

| リスク | 緩和策 |
|--------|--------|
| OANDA live key 流出 | live confirmation gate + secret 読込経路の contract test 固定 |
| SMTP 暴走 / 無限 retry | max_retry=3 + backoff + rate_limit |
| Supabase 依存 | Interface 経由 + Mock テストのみ Iter2、実疎通は manual runbook |
| Dashboard 10 panel の polling | cache ttl=5 + connection pool 既存設計踏襲 |
| MidRun 15 分タイマーを CI で遅延 | fake clock 即時発火 |
| 既存 contract 破壊 | M25 で既存 15 本の green を必須条件に |
| 2-factor bypass | CI lint で bypass 検出 |

---

## 13. Open Questions

| ID | 論点 | 解決予定 M |
|----|------|------------|
| **IP2-Q0** | **OANDA live 実発注の運用解禁時期**（Iteration 3 か Phase 7 か） | M13 設計時に方針確定、**暫定: Iteration 2 は demo only、live 実発注解禁は Iteration 3 以降で別 PR で議論** |
| IP2-Q1 | TSS の重み / horizon の初期値 | M20（暫定: MetaDecider score の線形結合、詳細は Iteration 3） |
| IP2-Q2 | Supabase projection 周期（5 分が最適か） | M23（暫定 5 分、運用 1 ヶ月後再評価） |
| IP2-Q3 | Learning UI の stub executor の挙動（即時 COMPLETED で OK か） | M21（Decision: Iteration 2 は stub 即時、Phase 7 で本 executor） |
| IP2-Q4 | 2-factor の実装方式（TOTP / email code / 対話） | M22（暫定: 対話 + TOTP、SSO は Phase 8） |
| IP2-Q5 | multi_service_mode の接続点粒度（Iter2 でどこまで表現するか） | M24（暫定: Interface 宣言 + docs に matrix） |
| **IP2-Q6** | **app_settings `environment` キーが Common Keys（D1 §3.1 の row 属性 `environment`）と命名衝突する懸念** | M18（**Decision: app_settings 側を `runtime_environment` にリネーム**、Common Keys 側は変更せず） |
| **IP2-Q7** | **`dashboard_top_candidates` 実装戦略**（新規 CREATE TABLE か View 戦略か） | M20（**Decision: migration 0012 で新規 CREATE TABLE**。MVP §12 #2 の table 数を 42→43 へ更新、view 戦略は Phase 7 で再評価） |
| **IP2-Q8** | **Operator/Configuration Console の実装着手 Iteration**（Iter3 か Phase 8 か） | Iter2 仕様凍結後（**Decision: 仕様は Iter2 で固定（本書 §2.1 / operations.md §15）、実装は Iteration 3 以降の別 PR**。SSO/multi-user/`dashboard_operations_audit`（**仮称、Phase 8 で正式テーブル名確定**）は Phase 8 へ送り、UI 経由 secret 書込 sink は Iter3 着手時も `.env` 限定。Streamlit 卒業条件超過で UI 刷新は phase8_roadmap §2.3 に従う） |

---

## 14. Summary

本書は以下を **Iteration 2 の実装契約** として固定:

1. **14 マイルストーン M13–M26** の目的・入力・完了条件・テスト条件・リスク・後続依存（M26 は UI/Console 仕様凍結 docs only）
2. **Carryover Mapping**: 8 Carryover ID 全てが特定 M に割り当て済（M26 は新規責務のため Carryover 紐付けなし）
3. **MVP §12 の 10 項目全て Full 化** を Iteration 2 完了条件
4. **Phase 7 / Phase 8 送り項目** を明示
5. **改善ループによる自己精査** 済（Loop 1 → Loop 2 → **Loop 3 cross-reference review** を経由）
6. 本書を破る実装は Iteration 2 の契約違反

---

## 15. Loop 3 Cross-Reference Findings (Audit Log)

Iter1 完了文書 + 6 設計文書（schema_catalog / implementation_contracts / operations / retention_policy / phase6_hardening / iteration1_implementation_plan §13）と本書を網羅照合した結果の検出と解消対応。各項目は plan 内の修正箇所にリンクで対応する。

### 15.1 検出 集計

- **修正必要**: 16 件 / **追記必要**: 28 件 / **矛盾**: 18 件 / **重複**: 4 件 (4 agent 並列調査の合算、重複を除く実質ユニーク 30 件)

### 15.2 主要矛盾の解消

| ID | 矛盾内容 | 設計文書事実 | 解消（plan 内反映） |
|----|---------|--------------|--------------------|
| L3-M1 | alembic table 数「46」誤記 | schema_catalog.md 行 4「**42 物理 + ローカル 2**」 | §9 表 + 末尾段落で **42 → 43**（M20 で +1）に訂正 |
| L3-M2 | `dashboard_top_candidates` mart 既存前提 | grep 結果 0 件、未存在 | §6.8 M20 で **migration 0012 新規 CREATE TABLE 必須**化、§2.1 In Scope に明記 |
| L3-M3 | ExitPolicy Protocol が D3 既存前提 | D3 では §6.1 名称言及のみで Protocol 未定義 | §6.2 M14 変更対象に **D3 への新規 Protocol 追加**を明示 |
| L3-M4 | ProjectionTransport Protocol が D3 既存前提 | D3 全文 grep で不在 | §6.11 M23 変更対象に **D3 への新規 Protocol 追加**を明示 |
| L3-M5 | multi_service_mode Interface が D3 既存前提 | D3 では `LocalQueueEventBus` 名称言及のみ | §6.12 M24 変更対象に **D3 への新規 Interface 追加**を明示 |
| L3-M6 | `tests/unit/test_dashboard_query_service.py` 既存前提 | Glob 結果 0 件、未存在 | §6.6 M18 で **新規作成扱いに変更**、§11.1 ファイル名修正 |
| L3-M7 | panel/ctl test 既存前提 | Glob 結果 0 件、未存在 | §6.7 M19 / §6.10 M22 で「既存不在、本 M で唯一の検証経路」と明記 |
| L3-M8 | EmailNotifier「任意」→「必須」昇格の正当化欠落 | phase6 §6.13 で「任意」 / iter1§13 で Iter2 送り | §6.5 M17 冒頭に **Scope 拡張の正当化**段落追加 |
| L3-M9 | multi_service_mode「実運用」→「Interface のみ」再分類の正当化欠落 | iter1§13 行 765「実運用」 / 本書 §10.1 Phase 7 送り | §6.12 M24 冒頭に **再分類の正当化**段落追加、§10.1 にも反映 |
| L3-M10 | 11 ケース Action Matrix の出典が operations.md と誤認 | operations.md には番号定義なし、phase6_hardening.md §6.12 が正本 | §6.3 M15 入力欄を **phase6_hardening.md §6.12** に修正 |
| L3-M11 | supervisor_events 永続性の retention 影響未記述 | retention_policy §3.1 #41「SUPERVISOR_PERMANENT」 | §6.4 M16 リスク欄に永続蓄積注記、Phase 7 Cold Archive 着手時の再評価必須を明示 |
| L3-M12 | close_events retention の plan 内記述欠落 | retention_policy §3.1 #23「EXECUTION_PERMANENT」 | §6.2 M14 完了条件に retention + 7 年保持 + partial close 不実装の整合を明示 |
| L3-M13 | operations.md の 2-factor 必須記述欠落 | operations.md §3.1 / §11 で 2-factor 言及なし | §6.10 M22 変更対象に **operations.md 同期更新**を追加 |
| L3-M14 | operations.md の Email 経路欠落 | operations.md §6.3 アラート表は File + Slack のみ | §6.5 M17 変更対象に **operations.md §6.3 表更新**を追加 |
| L3-M15 | ctl サブコマンド 2 種欠落（resume-from-safe-stop / run-reconciler） | operations.md §11 Cheat Sheet に既存 | §6.10 M22 変更対象 + 完了条件 + §11.1 test に追加 |
| L3-M16 | 「改善分析ビュー」panel が plan に未記載 | iter1§13 行 760 で名称言及（4 名挙げて「3 パネル」と記述） | §6.7 M19 の責務分離段落で **Phase 7 送り**と明示、§10.1 にも追加 |
| L3-M17 | lint (a) human-review 方針反転の正当化欠落 | custom_checks.py 行 24 周辺で「human-review」 | §6.13 M25 に **方針反転の明示 + 限定正規表現 + src/ only**を追加 |
| L3-M18 | app_settings `environment` キー Common Keys 衝突 | D1 §3.1 で `environment` は row 属性 | §13 IP2-Q6 として追加、§6.6 M18 で `runtime_environment` リネーム決定 |

### 15.3 重要な追記（未割当解消）

- §6.1 M13: `expected_account_type` SQL runbook、Step 9 confirm-live-trading 位置記録
- §6.3 M15: Step 11 PriceFeed/StreamWatchdog wiring、Step 13 MidRun 起動シーケンス
- §6.10 M22: Step 7 SafeStopJournal↔DB 突合、Step 14 OutboxProcessor resume wiring、ctl resume / run-reconciler test 追加
- §6.11 M23: **Projector ≠ Archiver**（5 分 snapshot は日次 02:00 UTC Archiver と別経路、SUPERVISOR_PERMANENT に対し Delete しないため衝突なし）
- §10.1: 「改善分析ビュー」panel、retention 通知 5 イベント、L1/L2 jsonl ローテ本実装を Phase 7 送りに追加
- §11.3: **既存 511 test への影響範囲表**（M13–M25 × 影響 test）を新設

### 15.4 Loop 3 で「該当なし」と確認した項目

- Carryover 8 ID は plan §7.1/7.2/7.3 で 1:1 一致確認済（L3 で再検証）
- phase6 §6.18 account_type assertion / §6.13 二経路は plan で正しく参照
- 新契約 7 本のファイル名は既存 tests/ 配下に未存在を確認、衝突なし
- MVP §12 10 項目は iteration1_completion §2.3 と plan §9 で完全対応（数値は L3-M1 で訂正）

### 15.5 M26 新設 (UI/Console 仕様凍結、Loop 4 追加)

Loop 3 後の追加レビューで「§2.1 In Scope に追加した『UI 仕様化』が §6 Detailed Milestones のどの M にも紐付いていない」という構造的不整合を検出。M に紐付かない In Scope 項目は完了条件・推奨実装順序・テスト戦略の対象外となり「誰の責任でいつ完了するか不明」の宙吊り状態となるため、独立マイルストーン **M26: UI / Console Operational Boundary Spec Freeze (docs only)** を新設して解消。

| 観点 | 解消手段 |
|------|---------|
| §2.1 In Scope の宙吊り | UI 仕様化行末尾に「(M26)」紐付け、§6.14 へのリンク追加 |
| §5 Milestones 表 | M25 直後に M26 行追加 (典型工数 0.5–1 日、依存 M22) |
| §6 Detailed Milestones | §6.14 M26 として目的・入力・変更対象 6 docs・完了条件 6 項・テスト条件・リスク・後続依存を明記 |
| §8 Recommended Order | §8.1 Dependency Graph に M22 → M26 を追加、§8.2 並列可能に M26 を追加、§8.3 推奨実装順 #10 に追加 |
| 既存 M13–M25 への影響 | なし (本 M は他 M の責務・完了条件・テスト条件を変更しない、docs only スコープを §6.14 完了条件で担保) |

**M26 と M25 の責務分離**: M25 は「コード contract test + paper smoke E2E 拡張」、M26 は「docs 整合性凍結 (コード変更なし)」。M25 に M26 を統合すると「コード contract」と「docs 凍結」が雑居し M25 の責務が不明瞭になるため、独立マイルストーンとして分離。

**M26 と M22 の責務分離**: M22 は「ctl CLI 5 コマンドの実 process 管理 + 2-factor」、M26 は「UI 経由境界の仕様」。Operator Console は M22 の薄ラッパだが、Configuration Console (`.env` sink + `app_settings_changes` キュー) は M22 と無関係なため、M22 拡張ではなく独立 M として扱う。
