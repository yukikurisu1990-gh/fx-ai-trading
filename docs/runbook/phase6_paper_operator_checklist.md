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

## 10. paper-loop runner（M9 OandaQuoteFeed wiring verification）

> **位置付け**: `scripts/ctl.py` 系（本書 §3 / §9）と**並行**に存在する別系統の起動口。M-3d で導入された `OandaQuoteFeed` の constructor / `Supervisor.attach_exit_gate` 経路が live OANDA 接続で通ることを確認するための、薄い outside-cadence runner。
>
> **wiring verification モード**: `broker` / `state_manager` / `exit_policy` は `fx_ai_trading.ops.null_safe_stubs` の null-safe stub。`open_position_details()` が常に `[]` を返すため `run_exit_gate` は即 `[]` を返し、close path は実行されない（=実際の発注・決済は起きない）。production paper stack の本物構築は次 PR の責務。

### 10.1 環境変数

| Env | 必須 | デフォルト | 用途 |
|---|---|---|---|
| `OANDA_ACCESS_TOKEN` | 必須 | — | OANDA REST トークン |
| `OANDA_ACCOUNT_ID` | 必須 | — | OANDA account id |
| `OANDA_ENVIRONMENT` | 任意 | `practice` | `practice` / `live`（本書スコープでは `practice` 固定） |
| `PAPER_LOOP_INTERVAL_SECONDS` | 任意 | `5.0` | tick cadence |
| `PAPER_LOOP_INSTRUMENT` | 任意 | `EUR_USD` | feed 構築対象 instrument |

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
| `runner.starting` | 起動直後 | `interval_seconds`, `instrument`, `max_iterations`, `log_path` |
| `runner.env_missing` | 必須 env 欠落で即 exit (rc=2) | `detail` |
| `runner.attached` | `Supervisor.attach_exit_gate` 後 | `instrument`, `oanda_environment`, `account_id_suffix`, `wiring_mode="verification"` |
| `tick.completed` | 各 tick の最後 | `iteration`, `results_count`, `tick_duration_ms` |
| `tick.exit_result` | `ExitGateRunResult` 1 件ごと | `iteration`, `instrument`, `order_id`, `outcome`, `primary_reason` |
| `tick.error` | tick 内例外（次 tick で再試行） | `iteration` + `exc_info` |
| `shutdown.signal_received` | SIGINT 受信時 | `signum` |
| `runner.shutdown` | loop 抜けた直後 | `iterations` |

### 10.4 jq レシピ

```bash
# tick あたりの所要時間
tail -f logs/paper_loop.jsonl | jq -c 'select(.event=="tick.completed") | {iteration, results_count, tick_duration_ms}'

# wiring verification 中は results_count が常に 0 のはず
jq -c 'select(.event=="tick.completed" and .results_count!=0)' logs/paper_loop.jsonl

# 起動～接続の確認
jq -c 'select(.event=="runner.starting" or .event=="runner.attached")' logs/paper_loop.jsonl

# tick が落ちたケースだけ
jq -c 'select(.event=="tick.error")' logs/paper_loop.jsonl
```

### 10.5 outcome 値の見方（次 PR で実データが流れ始めたとき用）

本 PR の wiring verification モードでは `tick.exit_result` 行は出ない（`results_count=0`）。次 PR で production paper stack が attach された後は以下を判別軸にする:

| `outcome` | 意味 | 初動 |
|---|---|---|
| `closed` | exit gate が正常 close 発火 | 通常運用、§4 / §5 と同じ |
| `noop_stale_quote` | M-3c stale-quote ガード発火（quote 古い） | feed 健全性確認、`OANDA_ENVIRONMENT` 確認 |
| `noop_*` その他 | exit policy が非発火判定 | `primary_reason` で切り分け |
| `error_*` | 内部エラー | `tick.error` と相関、`exc_info` 確認 |

SafeStop の発火経路は本書 §6 と同一（このランナー側では発火しない）。

### 10.6 非対象（このランナーの守備範囲外）

- production paper stack（real Broker / StateManager / ExitPolicy）の構築 — 次 PR
- `run_exit_gate` 本体改変 / Supervisor-internal loop 化 — 凍結（`project_cycle_6_9a_blocked.md`）
- SafeStop / schema / metrics / net pnl — 各専任 PR の責務

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
