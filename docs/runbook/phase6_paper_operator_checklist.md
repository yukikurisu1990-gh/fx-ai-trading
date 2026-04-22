# Runbook — Phase 6 Paper オペレーター チェックリスト

> **目的**: Phase 6 paper 運転中のオペレーターが「いま何をすればよいか」を 1 ページで決定するための時系列チェックリスト index。
> 詳細は既存 docs / runbook へ全てリンク。説明はしない。

---

## 1. 目的 / スコープ / 前提

- **対象**: Phase 6 paper モード運用中のオペレーター / oncall / shift 担当
- **位置付け**: `docs/operator_quickstart.md`（汎用 30 秒ナビ）と `docs/runbook/exit_fire_metrics.md`（exit fire 監視特化）の橋渡し。Phase 6 paper シナリオに**特化**した時系列手順
- **前提**:
  - demo only（live は Phase 7 で解禁、Iter2 では `4-defense gate` でブロック）
  - Phase 6 paper = GO 状態（Cycle 6.7d 以降の hardening 適用済 — `docs/phase6_hardening.md` 参照）
  - close_events 集計は `ExitFireMetricsService` 経由が唯一のテスト済み読み取り口

---

## 2. 起動前チェック

| # | 確認項目 | 詳細 / リンク |
|---|---|---|
| 1 | `.env` の `DATABASE_URL` / `OANDA_*` が paper 環境設定 | `docs/operations.md` |
| 2 | DB 接続（migration 済 / Phase 6 hardening tables 存在） | `docs/schema_catalog.md` |
| 3 | アプリ未起動（PID file 不在） | `docs/operator_quickstart.md §2` |
| 4 | live 切替フラグが OFF（`4-defense gate` 一段目） | `docs/phase6_hardening.md §6.18` |
| 5 | `logs/` ディレクトリ書き込み可能 | `docs/operations.md` |

---

## 3. 起動シーケンス

```text
1. python scripts/ctl.py start
2. Dashboard 起動・ログイン確認
3. baseline 記録:
   - get_exit_fire_summary() の現在値（runbook/exit_fire_metrics.md §4 参照）
   - logs/safe_stop.jsonl が空 / 最新 entry の確認
   - dashboard "Positions" の建玉確認
4. supervisor_events に startup イベントが記録されたことを確認
```

→ details: `docs/operator_quickstart.md §2`, `docs/runbook/exit_fire_metrics.md §3`

---

## 4. 通常運用中の観測サイクル

| 周期 | アクション | リンク先 |
|---|---|---|
| **5–10 分** | dashboard で Positions / 最新 supervisor_events を流し見 | `docs/dashboard_manual_verification.md` |
| **1 時間** | `get_exit_fire_count_by_reason(window_seconds=3600)` で reason 分布スナップ → 引き継ぎノート | `docs/runbook/exit_fire_metrics.md §8` |
| **1 日** | `get_exit_fire_summary(window_seconds=86400)` で span 健全性 / `logs/safe_stop.jsonl` 差分 | `docs/runbook/exit_fire_metrics.md §8` |
| **shift 交代** | §8 引き継ぎチェックリストを実施 | 本書 §8 |

数値の「健全パターン」「異常パターン」は `docs/runbook/exit_fire_metrics.md §4 / §5` を参照。

---

## 5. 異常検知時の初動分岐表

| 観測症状 | 即座のアクション | 詳細 |
|---|---|---|
| `total_fires=0` が 1h 継続 | exit_gate / supervisor health 確認 | `docs/runbook/exit_fire_metrics.md §5` |
| `span_end_utc` が 1h 以上古い | exit ハング疑い、supervisor ログ確認 | `docs/runbook/exit_fire_metrics.md §5` |
| 想定外 `reason_code` 出現 | 即 safe_stop 候補、ExitPolicy 契約違反 | `docs/runbook/exit_fire_metrics.md §5 / §7` |
| sl 比率急上昇（1h 70%+ かつ 5 件以上） | risk_events / trading_signals 相互参照 → safe_stop 検討 | `docs/runbook/exit_fire_metrics.md §7` |
| `emergency` 相当 reason 出現 | `recent_fires` で correlation_id 取得 → 全テーブル横断追跡 | `docs/operator_quickstart.md §4.1` |
| supervisor_events にエラー event | logs/supervisor.log + safe_stop.jsonl 確認 | `docs/operator_quickstart.md §4` |
| broker 通信エラー / OANDA 4xx・5xx | orders / order_transactions の status 確認 | `docs/operations.md` |

横断追跡の Common Keys は `cycle_id` / `run_id` / `order_id` / `correlation_id`。SQL テンプレートは `docs/operator_quickstart.md §4.1` を参照。

---

## 6. safe_stop 判断と発火手順

**判断材料**: `docs/runbook/exit_fire_metrics.md §7`

**発火手順**（SafeStopJournal 多重化契約含む）:
1. `python scripts/ctl.py` 系コマンドの該当系統で発火 — `docs/operator_quickstart.md §2`
2. `logs/safe_stop.jsonl` への記録 → DB → 通知の順序契約 — `docs/phase6_hardening.md §6.1`
3. in-flight 発注の扱いは `docs/phase6_hardening.md §6.1` 参照

**人間判断であり自動発火ではない**。迷ったら止める方を優先。

---

## 7. 復旧（safe_stop → resume）

```text
1. 異常原因の特定（ログ + DB 横断、§5 表参照）
2. 必要なら DB 整合（run-reconciler）
3. python scripts/ctl.py resume-from-safe-stop --reason="..."
4. baseline 再記録（§3 step 3 と同じ）
```

→ details: `docs/operations.md §4`

---

## 8. shift 引き継ぎチェックリスト

引き継ぎ時に **次担当者へ渡すスナップショット**:

| 項目 | 取得方法 |
|---|---|
| 最新 baseline | `get_exit_fire_summary()` の値 |
| 直近 1h reason 分布 | `get_exit_fire_count_by_reason(window_seconds=3600)` |
| 直近 50 件の生 events | `get_exit_fire_recent(limit=50)` |
| 進行中インシデント | incident log の open エントリ一覧 |
| 未完了アクション | TODO ノート |
| safe_stop 履歴差分 | `logs/safe_stop.jsonl` の今日の追記分 |

→ details: `docs/runbook/exit_fire_metrics.md §8`

---

## 9. 終了手順

```text
1. python scripts/ctl.py stop  （graceful 停止、in-flight 完了待ち）
2. logs/ ディレクトリ保全（rotate 設定確認）
3. 当日 baseline / shift メモを保存
4. supervisor_events に shutdown イベントが記録されたことを確認
```

→ details: `docs/operator_quickstart.md §2`, `docs/operations.md`

---

## 10. paper-loop runner（M9 production paper stack）

> **位置付け**: `scripts/ctl.py` 系（本書 §3 / §9）と**並行**に存在する別系統の起動口。M9 exit pipeline（`run_exit_gate` + M-1a/b 側面 + M-2 PnL + M-3a/b/c/d QuoteFeed）を outside-cadence で駆動する、薄い host loop。
>
> **本 PR から: production paper stack で稼働**: `broker` は `PaperBroker(account_type="demo")`、`state_manager` は `StateManager(engine, ...)`（DB engine は `DATABASE_URL` から構築）、`exit_policy` は `ExitPolicyService(max_holding_seconds=...)`、`quote_feed` は `OandaQuoteFeed`。`StateManager.open_position_details()` に open 行が見えていれば close path（broker.place_order → on_close → close_events / positions(close) / outbox）まで到達する。前 PR (#141) の null-safe stub による wiring verification モードは廃止された。

### 10.1 環境変数

| Env | 必須 | デフォルト | 用途 |
|---|---|---|---|
| `DATABASE_URL` | 必須 | — | StateManager が読み書きする DB（`.env` から `python-dotenv` 経由で渡す運用は本ランナー側ではしない — 起動前に export しておく） |
| `OANDA_ACCESS_TOKEN` | 必須 | — | OANDA REST トークン |
| `OANDA_ACCOUNT_ID` | 必須 | — | OANDA account id（`StateManager` の account scope のデフォルトもこれ） |
| `OANDA_ENVIRONMENT` | 任意 | `practice` | `practice` / `live`（本書スコープでは `practice` 固定） |
| `PAPER_LOOP_INTERVAL_SECONDS` | 任意 | `5.0` | tick cadence |
| `PAPER_LOOP_INSTRUMENT` | 任意 | `EUR_USD` | feed 構築対象 instrument |
| `PAPER_LOOP_MAX_HOLDING_SECONDS` | 任意 | `86400` | `ExitPolicyService` の holding ceiling（24h） |

### 10.2 起動 / 停止

```text
# 起動（フォアグラウンド、Ctrl-C で graceful shutdown）
python -m scripts.run_paper_loop --interval 5 --instrument EUR_USD

# スモーク（N tick で自動終了）
python -m scripts.run_paper_loop --max-iterations 3

# CLI flags は env を上書きする
python -m scripts.run_paper_loop --log-dir logs --log-level DEBUG
```

SIGINT（Ctrl-C）は in-flight tick 完了後に loop を抜ける。`scripts/ctl.py` 系の SafeStop / PID 管理とは無関係（このランナーは PID file を作らない）。

### 10.3 ログの読み方（`logs/paper_loop.jsonl`）

JSON Lines、rotating 10 MiB × 5。1 行 = 1 JSON object。共通 envelope: `ts` / `level` / `logger` / `message`。

| event | いつ出る | 主なフィールド |
|---|---|---|
| `runner.starting` | 起動直後 | `interval_seconds`, `instrument`, `max_iterations`, `max_holding_seconds`, `log_path` |
| `runner.env_missing` | 必須 OANDA env 欠落で即 exit (rc=2) | `detail` |
| `runner.db_config_missing` | `DATABASE_URL` 欠落で即 exit (rc=2) | `detail` |
| `runner.attached` | `Supervisor.attach_exit_gate` 後 | `instrument`, `oanda_environment`, `account_id_suffix`, `max_holding_seconds`, `stack="paper"` |
| `tick.completed` | 各 tick の最後 | `iteration`, `results_count`, `tick_duration_ms` |
| `tick.exit_result` | `ExitGateRunResult` 1 件ごと | `iteration`, `instrument`, `order_id`, `outcome`, `primary_reason` |
| `tick.error` | tick 内例外（次 tick で再試行） | `iteration` + `exc_info` |
| `shutdown.signal_received` | SIGINT 受信時 | `signum` |
| `runner.shutdown` | loop 抜けた直後 | `iterations` |

### 10.4 jq レシピ

```bash
# tick あたりの所要時間
tail -f logs/paper_loop.jsonl | jq -c 'select(.event=="tick.completed") | {iteration, results_count, tick_duration_ms}'

# close が起きた tick だけ（results_count > 0 は何かが evaluate された証拠）
jq -c 'select(.event=="tick.completed" and .results_count!=0)' logs/paper_loop.jsonl

# 実際の close / noop / stale を outcome で分けて拾う
jq -c 'select(.event=="tick.exit_result") | {iteration, instrument, order_id, outcome, primary_reason}' logs/paper_loop.jsonl

# 起動～接続の確認
jq -c 'select(.event=="runner.starting" or .event=="runner.attached" or .event=="runner.env_missing" or .event=="runner.db_config_missing")' logs/paper_loop.jsonl

# tick が落ちたケースだけ
jq -c 'select(.event=="tick.error")' logs/paper_loop.jsonl
```

### 10.5 outcome 値の見方

`tick.exit_result.outcome` は `ExitGateRunResult.outcome`。`StateManager.open_position_details()` に open 行があれば 1 行 / 1 position 出る。

| `outcome` | 意味 | 初動 |
|---|---|---|
| `closed` | exit gate が正常 close 発火（`StateManager.on_close` 完了） | 通常運用、§4 / §5 と同じ。`close_events` / `positions(close)` / `secondary_sync_outbox` を確認 |
| `noop` | `ExitPolicy` 非発火（保有継続） | `primary_reason` は `null` |
| `noop_stale_quote` | M-3c stale-quote ガード発火（quote 古い、emergency_stop なし） | feed 健全性確認、`OANDA_ENVIRONMENT` 確認、次 tick で自動再試行 |
| `broker_rejected` | broker が close を拒否 | broker 応答ログ確認、`positions(close)` は書かれない |

SafeStop の発火経路は本書 §6 と同一（このランナー側では SafeStop を発火させない — 既存 SafeStop wiring は `run_exit_gate` 内の PR-5 / U-2 経路のまま）。

### 10.6 非対象（このランナーの守備範囲外）

- `run_exit_gate` 本体改変 / Supervisor-internal loop 化 — 凍結（`project_cycle_6_9a_blocked.md`）
- SafeStop / schema / metrics / net pnl — 各専任 PR の責務
- strategy / signal generation / execution gate — このランナーは exit cadence のみ

### 10.7 paper-loop bootstrap（新規 open を 1 件作る）

`scripts/run_paper_loop` は **exit cadence 専用**で、open position を作成する経路を持たない（strategy / signal generation は凍結スコープ、§10.6）。ランナーに対して exit path を確認したいとき、operator は `scripts/paper_open_position` で 1 件だけ open position を作成できる。

本ブートストラップの責務は **1 PR / 1 責務**で「新規 open を最小構成で作る」ことに限定されている。既存 `OrdersRepository` / `PaperBroker` / `StateManager` の公開 API のみを使い、FSM (`PENDING → SUBMITTED → FILLED`) を忠実に踏む：

1. `OrdersRepository.create_order`               → `status='PENDING'`
2. `OrdersRepository.update_status('SUBMITTED')` → broker 送出を表明
3. `PaperBroker.place_order`                     → 即時 fill
4. `OrdersRepository.update_status('FILLED')`    → fill 確認後の終端遷移
5. `StateManager.on_fill`                        → `positions(open)` + `secondary_sync_outbox`（単一 txn）

起動コマンド（環境変数 `DATABASE_URL` が必要、読み方は §10.1 と同じ）：

```bash
python -m scripts.paper_open_position \
    --account-id $OANDA_ACCOUNT_ID \
    --instrument EUR_USD \
    --direction buy \
    --units 1000
```

| CLI flag | 必須 | 既定値 | 意味 |
|---|---|---|---|
| `--account-id` | ○ | — | `orders.account_id` / `positions.account_id`（本番 schema では `accounts` への FK）|
| `--instrument` | ○ | — | OANDA instrument（例: `EUR_USD`）|
| `--direction` | ○ | — | `buy` または `sell`。broker side へのマッピングは `buy → long` / `sell → short`（production と一致）|
| `--units` | ○ | — | 約定数量（> 0）|
| `--account-type` | × | `demo` | `PaperBroker` は `demo` のみ許可（6.18 不変条件）|
| `--nominal-price` | × | `1.0` | `PaperBroker` の同期 fill 価格。以降の close で M-2 gross PnL を検証するとき `positions.avg_price` として残る |
| `--log-dir` / `--log-filename` / `--log-level` | × | `logs/paper_open_position.jsonl` / `INFO` | 構造化 JSONL ログ（`apply_logging_config`、§10.3 と同じ形式）|

**Exit code**:

| rc | 意味 | 対応 |
|---|---|---|
| 0 | open 成功（`bootstrap.opened` ログを確認）| `run_paper_loop` を起動して exit cadence に乗せる |
| 2 | `DATABASE_URL` が未設定 | `.env` を確認（§10.1 と同じチェック）|
| 3 | 同じ `(account, instrument)` で既に open 行あり — pre-flight reject | `StateManager.open_instruments()` を確認。重複 open は意図的に禁止（pyramid `event_type='add'` 回避）|
| 4 | `PaperBroker` が `status='filled'` を返さなかった（想定外）| broker 応答ログを確認。`orders` は `SUBMITTED` で止まる — `FILLED` に進まない |

**イベント名（grep しやすい）**：

```
bootstrap.starting             起動直後（args + log_path）
bootstrap.db_config_missing    rc=2
bootstrap.duplicate_open       rc=3（pre-flight で既存 open を検出）
bootstrap.broker_rejected      rc=4（broker 応答が非 filled）
bootstrap.opened               成功（order_id / psid / fill_price / side）
```

**既知の制限（本 PR では意図的に未対応）**：

- `orders.submitted_at` / `orders.filled_at` は **NULL のまま**。`OrdersRepository.update_status` は timestamp を受け取らない。observability 側で filled_at を必要とする場合は、Repository API の追加拡張（strictly additive、別 PR）で対応する。
- `order_transactions` 行は書かれない — `PaperBroker.get_recent_transactions` は `[]` を返す。
- tp / sl は設定しない — exit は `ExitPolicyService`（`run_paper_loop` 側の `max_holding_seconds` など）に完全に委ねる。

**本ブートストラップの守備範囲外**（§10.6 と同様、別 PR 分割対象）：

- 既存 position への pyramiding（`event_type='add'`）— 明示的に pre-flight で拒否
- `run_exit_gate` / Supervisor / SafeStop — 不変
- schema / metrics / net pnl — 不変

---

### 10.8 paper-entry runner（cadence で open を発火する）

`scripts/paper_open_position`（§10.7）は **1 ショット**で open を 1 件作るが、close 後の自動再 open はできない。close path を継続的に検証したいとき（max_holding_seconds 経過 → close → 再 open → … のサイクル確認等）、operator は `scripts/run_paper_entry_loop` で **cadence 駆動の open 発火**を回せる。

本ランナーの責務は **1 PR / 1 責務**で「最小 entry policy で paper の auto-open を可能にする」ことに限定されている。strategy / signal generation の凍結スコープ（§10.6, Cycle 6.9a）は侵食しない。固定された `(instrument, direction, units)` に対して、tick ごとに `MinimumEntryPolicy` が 4 分岐で発火可否のみを決める：

- `already_open` — 同 `(account, instrument)` で既に open がある（`StateManager.open_instruments()` 参照）
- `no_quote`     — `QuoteFeed.get_quote` が例外（一時的な feed outage、次 tick で再試行）
- `stale_quote`  — `(clock.now() - quote.ts).total_seconds() > stale_after_seconds`（M-3c と同じ厳密 `>`、既定 60s）
- `ok`           — 発火 → §10.7 と完全に同じ FSM 5-step（`create_order` → `update_status('SUBMITTED')` → `PaperBroker.place_order` → `update_status('FILLED')` → `StateManager.on_fill`）

#### CLI usage

```bash
python -m scripts.run_paper_entry_loop \
    --account-id $OANDA_ACCOUNT_ID \
    --instrument EUR_USD \
    --direction buy \
    --units 1000
```

| CLI flag | 必須 | 既定値 | 意味 |
|---|---|---|---|
| `--account-id` | ○ | — | `orders.account_id` / `positions.account_id`（§10.7 と同義）|
| `--instrument` | ○ | — | OANDA instrument（例: `EUR_USD`）。policy はこの 1 件のみを監視 |
| `--direction` | ○ | — | `buy` または `sell`。broker side マッピングは §10.7 と同じ |
| `--units` | ○ | — | 約定数量（> 0）|
| `--account-type` | × | `demo` | §10.7 と同義 |
| `--nominal-price` | × | `1.0` | §10.7 と同義 |
| `--interval` | × | `5.0` | tick 間 sleep 秒。`PAPER_ENTRY_INTERVAL_SECONDS` で上書き可 |
| `--stale-after-seconds` | × | `60.0` | M-3c 既定。`PAPER_ENTRY_STALE_AFTER_SECONDS` で上書き可 |
| `--max-iterations` | × | `0` | `0` = SIGINT まで継続。smoke test では `1` / `2` などを指定 |
| `--log-dir` / `--log-filename` / `--log-level` | × | `logs/paper_entry_loop.jsonl` / `INFO` | 構造化 JSONL ログ（`apply_logging_config`、§10.3 と同じ形式）|

#### 必須 / optional env

| 変数 | 必須 | 既定値 | 出典 |
|---|---|---|---|
| `DATABASE_URL` | ○ | — | §10.1 と同じ（StateManager / OrdersRepository が利用）|
| `OANDA_ACCESS_TOKEN` | ○ | — | §10.1 と同じ（OandaQuoteFeed が利用）|
| `OANDA_ACCOUNT_ID` | ○ | — | §10.1 と同じ |
| `OANDA_ENVIRONMENT` | × | `practice` | §10.1 と同じ |
| `PAPER_ENTRY_INTERVAL_SECONDS` | × | `5.0` | `--interval` 未指定時の fallback |
| `PAPER_ENTRY_STALE_AFTER_SECONDS` | × | `60.0` | `--stale-after-seconds` 未指定時の fallback |

#### Exit code

| rc | 意味 | 対応 |
|---|---|---|
| 0 | 正常終了（SIGINT または `--max-iterations` 到達）| `entry_runner.shutdown` ログで `iterations` を確認 |
| 2 | 必須 env または `DATABASE_URL` 欠落 | `entry_runner.env_missing` / `entry_runner.db_config_missing` ログを確認、`.env` を修正 |

#### イベントログ一覧（grep しやすい）

```
entry_runner.starting          起動直後（args + log_path）
entry_runner.attached          components 構築完了（instrument / interval / stale_after_seconds）
entry_runner.env_missing       rc=2（OANDA env 欠落）
entry_runner.db_config_missing rc=2（DATABASE_URL 欠落）
entry_runner.shutdown          正常終了（iterations）
shutdown.signal_received       SIGINT 受信
tick.no_fire                   policy が発火を見送り（reason: already_open / no_quote / stale_quote）
tick.opened                    open 成功（order_id / psid / fill_price / side）
tick.skip_duplicate            policy.evaluate と _open_one_position の race（recoverable）
tick.broker_rejected           broker が非 filled を返した（_open_one_position が abort）
tick.error                     tick 内で予期せぬ例外（次 tick で再試行）
tick.completed                 各 tick 末尾（iteration / tick_duration_ms）
```

#### 既知の制限（本 PR では意図的に未対応）

- `orders.submitted_at` / `orders.filled_at` は **NULL のまま**。§10.7 と同じ理由（`OrdersRepository.update_status` が timestamp を受け取らない）。
- `order_transactions` 行は書かれない。§10.7 と同じ理由（`PaperBroker.get_recent_transactions` が `[]`）。
- `tick.skip_duplicate` 経路は recoverable だが、duplicate 状態が続く限り毎 tick `tick.no_fire(reason=already_open)` がログに残り続ける（policy 自体が冪等のため副作用なし）。
- `tick.broker_rejected` 後、対象 `orders` 行は `status='SUBMITTED'` のまま **残留する**（FILLED へは進まない）。§10.7 の rc=4 と同じ性質。次 tick の `_open_one_position` は新しい `order_id` を作って独立に再試行するため、SUBMITTED 残留行は累積し得る — operator は `SELECT order_id FROM orders WHERE status='SUBMITTED'` で観測し、必要なら手動で reconcile する。
- 1 ランナー = 1 instrument。複数 instrument を回す場合は instrument ごとに別プロセスで起動する。

#### out of scope（本ランナーの守備範囲外、別 PR 分割対象）

- 実 strategy / signal generation surfaces（Cycle 6.9a 凍結、§10.6）— `MinimumEntryPolicy` は deliberately fixed predicate であり、戦略フレームワークではない
- `OrdersRepository.update_status` の timestamp 拡張（strictly additive、別 PR）
- pyramiding（`event_type='add'`）— `_open_one_position` の pre-flight で `DuplicateOpenInstrumentError` を raise
- `run_exit_gate` / Supervisor / SafeStop — 不変
- schema / metrics / net pnl — 不変
- 複数 instrument を 1 プロセスで多重化する scheduler — 別 PR

---

## 11. 関連資料一覧

| カテゴリ | 参照先 |
|---|---|
| 汎用 30 秒ナビ | `docs/operator_quickstart.md` |
| 全体運用手順 | `docs/operations.md` |
| Phase 6 hardening 仕様 | `docs/phase6_hardening.md` |
| Exit fire 監視 runbook | `docs/runbook/exit_fire_metrics.md` |
| Cycle 6.9 設計メモ（将来 supervisor loop / watchdog 接続点） | `docs/design/cycle_6_9_supervisor_loop_memo.md` |
| Dashboard 手動検証 | `docs/dashboard_manual_verification.md` |
| Dashboard オペレーターガイド | `docs/dashboard_operator_guide.md` |
| Schema 定義 | `docs/schema_catalog.md` |
| Iteration 2 完了仕様 | `docs/iteration2_completion.md` |
| 開発ルール | `docs/development_rules.md` |
| 次フェーズ計画 | `docs/phase7_roadmap.md` / `docs/phase8_roadmap.md` |

---

## 12. 非対象（このチェックリストで決めないこと）

- live mode の手順 — Phase 7 解禁時に別 PR
- `ExitFireMetricsService` 内部仕様 — `docs/runbook/exit_fire_metrics.md` 参照
- safe_stop の内部実装契約 — `docs/phase6_hardening.md §6.1` 参照
- supervisor loop / cadence watchdog — Cycle 6.9a 凍結（M8/M9 後に再評価、`project_cycle_6_9a_blocked.md`）
- アラート自動化 / metrics emission — 将来 observability PR
- UI (Streamlit) パネル仕様 — `docs/dashboard_operator_guide.md` 管轄
