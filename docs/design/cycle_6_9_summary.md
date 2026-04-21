# Cycle 6.9 / 6.10 Series — 棚卸しサマリ

> **目的**: Cycle 6.9 / 6.10 シリーズで何が landed し / 何が凍結中で / M8 / M9 が landing したら何を再評価すべきかを 1 ページで俯瞰する。
> **位置付け**: 完了済み実装の棚卸し。将来の supervisor loop 接続点契約は `cycle_6_9_supervisor_loop_memo.md` を参照（役割は別）。

---

## 1. 目的 / スコープ

- **対象**: Cycle 6.9a / 6.9b / 6.9 設計メモ / 6.9c / 6.9d / 6.10
- **読者**: Phase 6 hardening の整合確認をしたい開発者 / M8 / M9 着手時にこのシリーズの前提を引き継ぐ実装者
- **狙い**:
  - 5 連続の autonomous-mode PR 後の cross-PR 整合確認
  - M8 / M9 解凍時に「何を再評価するか」のチェックリストを残す
  - 6.9a 凍結 trace を恒久化

---

## 2. シリーズ概要（PR 一覧）

| Cycle | PR | merge commit | 状態 | 種別 |
|---|---|---|---|---|
| 6.9a CadenceWatchdog | — | — | **凍結** | 実装保留 (M8 / M9 待ち) |
| 6.9b ExitFireMetricsService | #102 | `f401629` | merged | read-only service |
| 6.9 設計メモ (supervisor loop / cadence watchdog 接続点) | #103 | `a296528` | merged | docs-only |
| 6.9c ExitFireMetricsService runbook | #104 | `608fcb4` | merged | docs-only (新 `docs/runbook/`) |
| 6.9d Dashboard query wrappers | #105 | `f098b99` | merged | read-only adapter |
| 6.10 Phase 6 paper operator checklist | #106 | `9801dfc` | merged | docs-only |

**Master tip after series:** `9801dfc`.

**全 5 PR で守った制約**: 1 PR = 1 責務 / additive only / schema 変更ゼロ / supervisor.py 拡張ゼロ / write path 不触 / 既存挙動ゼロ影響 / CI 完全 green。

---

## 3. アーキテクチャ依存関係

```text
[UI layer (将来)]
        ↑
        │ (UI-safe fallback)
        │
[dashboard_query_service.py]                      ← 6.9d wrappers
        ↑
        │ (delegate)
        │
[ExitFireMetricsService]                          ← 6.9b
        ↑
        │ (read-only via engine.connect())
        │
[close_events table (append-only)]                ← 既存 (D3 §2.14)
        ↑
        │ (write-side, 不触)
        │
[exit_gate_runner / CloseEventsRepository]        ← 既存 (Cycle 6.7c-d)


[ドキュメント面]
        ┌─────────────────────────────────────────────────┐
        │ docs/operator_quickstart.md (汎用 30 秒ナビ)     │  既存
        └─────────────────────────────────────────────────┘
                                │
                                ▼
        ┌─────────────────────────────────────────────────┐
        │ docs/runbook/phase6_paper_operator_checklist.md │  6.10
        │ (Phase 6 paper 時系列チェックリスト)             │
        └─────────────────────────────────────────────────┘
                                │
                                ▼
        ┌─────────────────────────────────────────────────┐
        │ docs/runbook/exit_fire_metrics.md (詳細 runbook) │  6.9c
        └─────────────────────────────────────────────────┘
                                │
                                ▼
        ┌─────────────────────────────────────────────────┐
        │ ExitFireMetricsService (Service の使い方は      │  ← 6.9b 実装
        │ docstring + 統合テスト)                          │
        └─────────────────────────────────────────────────┘


[未来契約 (M8 / M9 で接続)]
        ┌─────────────────────────────────────────────────┐
        │ docs/design/cycle_6_9_supervisor_loop_memo.md   │  6.9 設計メモ
        │ (将来の supervisor loop / cadence watchdog 接続点)│
        └─────────────────────────────────────────────────┘
                                │
                                ▼
        [CadenceWatchdog (6.9a)] — 凍結中
```

**読み方**:
- 縦の矢印は呼び出し依存（上→下が呼ぶ側）
- ドキュメント面は「最初に開く順序」を表す
- 設計メモは未来側、それ以外は完了側

---

## 4. 適用した autonomous mode 制約

このシリーズは autonomous mode (stable-controlled-complete v3) 下で実行された。全 PR で以下を遵守:

| # | ルール | 全 PR で遵守 |
|---|---|---|
| 1 | 1 PR = 1 責務 | ✅ |
| 2 | additive change only — 既存挙動不変更 | ✅ |
| 3 | schema 変更なし（migration / index 追加なし）| ✅ |
| 4 | supervisor.py 拡張なし | ✅ |
| 5 | component 本体 (meta_cycle / execution_gate / reconciler / sync_worker) 不触 | ✅ |
| 6 | write path (orders / positions / risk / execution) 不触 | ✅ |
| 7 | read-only service は `engine.connect()` 限定 — `engine.begin()` 不使用 | ✅ |
| 8 | 直接 `datetime.now()` / `time.time()` なし — Clock 注入のみ | ✅ |

**安全領域** (このシリーズの全範囲):
- docs-only PR (#103 / #104 / #106 / 本 PR)
- read-only service (#102)
- query wrapper (UI 未接続) (#105)

**禁止領域** (M8 / M9 まで触らない、`feedback_autonomous_mode.md` 参照):
- supervisor loop の実装
- CadenceWatchdog の実装 (6.9a)
- component 本体変更
- schema 変更
- write path の変更

---

## 5. 残課題

### 5.1 凍結中（M8 / M9 待ち）

- **Cycle 6.9a CadenceWatchdog** — `project_cycle_6_9a_blocked.md` 参照
  - 理由: `supervisor.py` に running cadence loop が未実装 (M9 / M12) / Reconciler lifecycle が未実装 (M8) / 4 dispatch sites が未実在
  - 凍結中ブランチ: 該当なし（実装ゼロで保持）
  - 設計契約は `docs/design/cycle_6_9_supervisor_loop_memo.md` §3 に保管済（component_tick / cadence_violation contracts）

### 5.2 Phase 7 で意味を持つ機能

- `ExitFireMetricsService.pnl_summary_by_reason` — 現状 `pnl_realized` は常に NULL（Cycle 6.7c E3）。Phase 7 で pnl 実装が landing すると自動的に実数値を返す（service 側のコード変更不要）
- `dashboard_query_service.get_exit_fire_pnl_summary_by_reason` — 同上、wrapper は変更不要

### 5.3 別 PR に分離した out-of-scope 項目

- UI (Streamlit) パネル追加 — 6.9d query wrapper の消費側、未着手
- Observability (structured log / metrics emission) — 設計判断必須のため autonomous mode 下では default-defer（v3 ルール明記）
- 既存 `dashboard_query_service.get_close_events_recent` の ExitFireMetricsService 経由化 — 「既存挙動変更」になり autonomous mode 停止条件 #5 に抵触するため意図的に未実施。手動 PR で要判断

---

## 6. M8 / M9 解凍チェックリスト

M8 (Reconciler / MidRunReconciler lifecycle) または M9 / M12 (1-minute trading cycle loop) が `supervisor.py` に landing した時点で、以下を**順に**再評価:

1. **`feedback_autonomous_mode.md` の forbidden zones を更新**
   - "Supervisor loop implementation" / "CadenceWatchdog implementation" / "Component lifecycle integration" / "Cross-component orchestration" を削除または条件付き解禁
2. **6.9a CadenceWatchdog の Designer Freeze を再起動**
   - 設計契約は `docs/design/cycle_6_9_supervisor_loop_memo.md` §3 を pickup
   - 4 dispatch sites の実在確認 → contracts (`component_tick` / `cadence_violation`) を該当箇所に挿入
   - exit_gate を監視対象に含めるかは別判断 (`cycle_6_9_supervisor_loop_memo.md` §7 参照)
3. **既存 read-only service との非干渉確認**
   - ExitFireMetricsService は loop 内呼び出しでも安全 (read-only / 例外伝播 / 状態なし)。loop 内で metrics 取得を行う場合、UI セーフフォールバックは不要なので service 直接呼び出しでよい
4. **observability の解禁判断**
   - loop が動き始めたら structured log / metrics emission の設計判断材料が揃う。"observability default-defer" ルールを再評価
5. **本サマリ docs (このファイル) を更新**
   - 6.9a 凍結ステータスを「解凍済」に変更、解凍時の merge commit を §2 に追記

---

## 7. 関連資料

| カテゴリ | パス | 役割 |
|---|---|---|
| Service 実装 | `src/fx_ai_trading/services/exit_fire_metrics.py` | 6.9b |
| Service ユニットテスト | `tests/unit/test_exit_fire_metrics.py` | 6.9b |
| Service 統合テスト (DB) | `tests/integration/test_exit_fire_metrics_db.py` | 6.9b |
| Dashboard query wrappers | `src/fx_ai_trading/services/dashboard_query_service.py` (関数 4 つ) | 6.9d |
| Dashboard query wrappers tests | `tests/unit/test_dashboard_query_service.py` (16 tests 追加) | 6.9d |
| 詳細 runbook (exit fire 監視) | `docs/runbook/exit_fire_metrics.md` | 6.9c |
| Phase 6 paper オペレーター チェックリスト | `docs/runbook/phase6_paper_operator_checklist.md` | 6.10 |
| 将来 supervisor loop / watchdog 接続点 設計メモ | `docs/design/cycle_6_9_supervisor_loop_memo.md` | 6.9 設計メモ |
| 6.9a 凍結トレース | `project_cycle_6_9a_blocked.md` (memory) | — |
| 既存: 汎用ナビ | `docs/operator_quickstart.md` | — |
| 既存: Phase 6 hardening 仕様 | `docs/phase6_hardening.md` | — |
| 既存: 全体運用手順 | `docs/operations.md` | — |
| 既存: schema 定義 | `docs/schema_catalog.md` | — |

---

## 8. 非対象（このサマリで決めないこと）

- M8 / M9 自体の設計 — 別計画 (`docs/m26_implementation_plan.md` ほか)
- 新機能追加 — このサマリは棚卸し専用
- 既存 docs の修正 — 既存 docs はリンクのみ
- `supervisor.py` の変更 — 禁止領域
- スクリプト / コード追加 — このサマリは docs-only
- Cycle 6.7 / 6.8 シリーズの棚卸し — 別 cycle (`project_cycle_6_8_closure.md` 参照)
