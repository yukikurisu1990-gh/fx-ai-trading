# Runbook — ExitFireMetricsService 運用ガイド

> **目的**: Phase 6 paper 運転中に `close_events` の発火傾向を把握し、異常の兆候と初動を 30 秒で判断するためのガイド。
> 「使い方」ではなく「何を見て / 何をすべきか」を定義する。

---

## 1. 目的 / スコープ

- 対象サービス: `ExitFireMetricsService` (Cycle 6.9b, `src/fx_ai_trading/services/exit_fire_metrics.py`)
- 対象データ: `close_events` テーブル（決済イベント append-only / EXECUTION_PERMANENT / D3 §2.14）
- 対象読者: paper 運転監督者 / oncall / shift 引き継ぎ担当
- 位置付け: 監視の最小セット。詳細は §9 リンク先を参照

---

## 2. 前提

- `ExitFireMetricsService` は `close_events` の**唯一のテスト済み読み取り口**。並行して同じ集計をアドホック SQL で書かない
- 書き込み側は `CloseEventsRepository`（`exit_gate_runner` 経由）— runbook ではその挙動は前提として扱う
- `pnl_realized` は Cycle 6.7c E3 により現状 **常に NULL**。pnl 集計は Phase 7 以降に意味を持つ
- window 指定は Clock 注入に従う（`WallClock` 既定、テストは `FixedClock`）
- DB 例外はサービスが伝播する。UI セーフフォールバックが必要な場合は `dashboard_query_service.py` 経由（別責務）

---

## 3. メソッド早見表

| メソッド | 返り値 | 使いどころ |
|---|---|---|
| `summary(window)` | `{total_fires, distinct_reasons, span_start_utc, span_end_utc}` | **最初に見る**。発火有無 / 時間スパン健全性 |
| `count_by_reason(window)` | `{reason_code: count}` | reason 分布 / 偏り検出 / 想定外 reason_code 検出 |
| `pnl_summary_by_reason(window)` | `{reason_code: {count, pnl_sum, pnl_avg}}` | Phase 7 以降の pnl ドリフト監視（Phase 6 中は count のみ有用） |
| `recent_fires(limit)` | 最新 N 件の dict list（新しい順） | 個別事象の深掘り / `correlation_id` 追跡 |

`window` は `timedelta` または `None`。`None` は全期間。`span_start_utc` / `span_end_utc` は tz-aware UTC。

---

## 4. 健全パターン（baseline）

以下は「通常稼働中にこの値なら問題なし」の目安。baseline は運用開始時に自分の環境で記録し、本書の値を上書きして使う。

- 1 時間窓 `summary(window=timedelta(hours=1))`
  - `total_fires > 0`（戦略とマーケットによる。完全 0 が数時間続けば §5 へ）
  - `span_end_utc` が「現在時刻から数分以内」（exit_gate は cadence で発火するため）
- 24 時間窓 `summary(window=timedelta(hours=24))`
  - `distinct_reasons` は 2–4 程度（tp / sl / time / reverse など ExitPolicy が許容する範囲内）
- `count_by_reason(timedelta(hours=1))`
  - 出現 reason_code は ExitPolicy で定義されたものだけ（`docs/phase6_hardening.md` 6.8 節参照）
  - tp と sl の比率は戦略に依存。急激な変化は §5 異常パターンへ

---

## 5. 異常パターン一覧

| 症状 | 考えられる意味 | 初動 |
|---|---|---|
| `total_fires=0` が 1h 窓で継続 | exit_gate 停止 / データ入口停止 / ポジション不在 | `exit_gate_runner` ログ確認、`orders` 直近数、supervisor health |
| `span_end_utc` が 1h 以上古い | exit 発火停止（ポジション未保有ではなく停止） | supervisor event / exit_gate ログ / DB 接続 |
| 想定外 reason_code 出現 | ExitPolicy 契約違反（設定追加ミス含む） | `recent_fires` で `reasons[].detail` と `correlation_id` を取得、ExitPolicy 設定と突合 |
| sl 比率が急上昇（例: 1h 窓で 70%+ かつ 5 件以上） | 市場急変 / 戦略破綻 | `risk_events` / `trading_signals` を相互参照、§7 safe_stop 判断へ |
| `distinct_reasons=1` が長時間継続 | ExitPolicy priority 設定ミス / 特定条件ロックイン | ExitPolicy priority と発火ロジック見直し |
| `pnl_summary_by_reason` で pnl_sum / pnl_avg が全て None | **Phase 6 paper 中は正常**（E3 により pnl_realized=NULL） | アクション不要。Phase 7 以降で同じ状態なら異常 |
| `count_by_reason` unbounded で `emergency` 等の緊急 reason が混入 | 緊急決済発生 | `recent_fires` で時刻と correlation_id 特定、`risk_events` / `supervisor_events` 並行確認 |

---

## 6. 初動チェックリスト（30 秒オペレーション）

1. `summary(timedelta(hours=1))` と `summary(timedelta(hours=24))` を比較
2. `count_by_reason(timedelta(hours=1))` で reason 分布スナップ
3. 異常兆候あり → `recent_fires(limit=20)` で直近事象取得
4. 怪しい事象は `correlation_id` を起点に相関確認:
   - `orders` 対応行 / `order_transactions` 発注系譜
   - `supervisor_events` の並行事象
   - `risk_events` の同時刻記録
5. §7 により safe_stop 要否を判断

---

## 7. safe_stop 判断材料

以下のいずれかを満たしたら safe_stop を **積極的に検討**する（自動発火ではない — 判断は人間）:

- `count_by_reason(timedelta(hours=1))` で `sl` 比率 70%+ かつ 5 件以上 → 戦略破綻疑い
- `summary(timedelta(minutes=30))` で `total_fires=0` かつ `exit_gate` が稼働中のはず → exit ハング疑い
- **想定外 reason_code を観測** → 即座に safe_stop 候補（ExitPolicy 契約違反）
- `emergency` 相当の reason が 2 件以上 / 短時間に出現

safe_stop 発火手順（SafeStopJournal 多重化契約含む）:
- `docs/phase6_hardening.md §6.1`
- `docs/operations.md §4`
- コマンド: `python scripts/ctl.py` 系 — `docs/operator_quickstart.md §2`

---

## 8. Paper 運転中の観測チェックリスト

| タイミング | アクション | 保存先 |
|---|---|---|
| 開始時 | `summary()` で baseline 記録 | 引き継ぎノート |
| 1 時間ごと | `count_by_reason(timedelta(hours=1))` スナップ | 引き継ぎノート |
| 1 日 1 回 | `summary(timedelta(hours=24))` で span 健全性確認 | daily ops log |
| shift 交代時 | `recent_fires(limit=50)` を添付して引き継ぎ | ハンドオフ |
| 異常検知時 | §6 初動チェックリスト実施、結果を `correlation_id` 単位で記録 | incident log |

---

## 9. 関連資料

| カテゴリ | 参照先 |
|---|---|
| Service 実装 | `src/fx_ai_trading/services/exit_fire_metrics.py` |
| 書込側 Repository | `src/fx_ai_trading/repositories/close_events.py` |
| Cycle 6.9 設計メモ（将来 loop / watchdog 接続点） | `docs/design/cycle_6_9_supervisor_loop_memo.md` |
| close_events schema | `docs/schema_catalog.md §23` |
| ExitPolicy 契約（reason_code 定義） | `docs/phase6_hardening.md §6.1 / §6.8` |
| safe_stop 手順 | `docs/phase6_hardening.md §6.1`, `docs/operations.md §4` |
| operator quickstart | `docs/operator_quickstart.md` |
| UI 側ダッシュボード | `docs/dashboard_operator_guide.md` |

---

## 10. 非対象（この Runbook で決めないこと）

- UI (Streamlit) 表示仕様 — `docs/dashboard_operator_guide.md` 管轄
- しきい値の自動アラート / metrics emission — 将来 observability PR で追加
- `pnl_realized` 計算式 — Phase 7 pnl 実装時に確定
- exit_gate 本体の実装 — 変更禁止領域（Cycle 6.7d 以降凍結）
- supervisor loop の実装 — M8/M9 で解禁
- CadenceWatchdog との連携 — Cycle 6.9a 凍結、M8/M9 後に再評価（`project_cycle_6_9a_blocked.md` 参照）
