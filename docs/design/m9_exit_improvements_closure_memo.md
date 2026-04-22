# M9 Exit Improvements — Closure Memo

> **目的**: M9 配下で連続的に landing した 11 PR (H-1 / H-2 / H-3a / H-3b / H-3c-part1 / H-3c-final / M-1a / M-1b / M-2 / M-3a / M-3b / M-3c) と関連 closure memo (M-3) を 1 ページで棚卸し、`run_exit_gate` が "唯一の exit 実行経路" として閉じたことを記録する。
> **位置付け**: M9 exit improvements 全体の closure memo。M-3 シリーズ単独の closure (`m3_quote_feed_migration_closure_memo.md`) より上位レイヤで、H シリーズ (legacy 排除) と M シリーズ (改善) の両方を俯瞰する。
> **対象外**: 実装変更・schema 変更・config 注入・M-3d 着手。本ドキュメントは **docs-only**。

---

## 1. 背景 / なぜ M9 を切ったか

Phase 6.7c 着地時点での exit 経路は 2 系統が並存していた:

1. **`ExitExecutor`** — 旧経路。`CloseEventsRepository.insert` を直接叩き、`StateManager.on_close` は経由しない。PR-5 / U-2 SafeStop 配線は **こちらにしか無い**。
2. **`run_exit_gate`** — 新経路。`StateManager.on_close` 経由で append-only 書込を完結させる。Phase 6.7c で導入された "post-I-09 write path"。

この 2 系統並存は Phase 6 paper の GO 判定後に 4 つの問題を生んでいた:

1. **テストが ExitExecutor 側に張り付いて新経路への移行が止まっている** — H シリーズで解消
2. **`OpenPositionInfo.side` が呼出側から渡される (orders truth から外れた値)** — M-1 で解消
3. **`pnl_realized` が常に NULL** (Cycle 6.7c E3 既知) — M-2 で解消
4. **価格供給が `Callable[[str], float]` で ts/source が取れない** (staleness 判定の余地なし) — M-3 で解消

M9 は **H (legacy 排除) → M (改善) の二段** で攻めた。H が完了して `run_exit_gate` が単一経路になってから M で改善を重ねる順序にしたのは、ExitExecutor が残っているまま M-1/M-2/M-3 を進めると "両経路にパッチを当てる" 工数が膨らむため。

---

## 2. シリーズ全 PR 一覧

### 2.1 H シリーズ — legacy ExitExecutor 排除

| ステージ | PR | merge commit | 種別 | 主な変更 |
|---|---|---|---|---|
| H-1 | #124 | `765013f` | feat | `Supervisor.attach_exit_gate` / `run_exit_gate_tick` cadence seam 追加 (`supervisor=self` で PR-5 / U-2 SafeStop 配線を `run_exit_gate` 側に保持) |
| H-2 | #125 | `753e9a9` | tests | exit-event FSM contract test を `ExitExecutor` → `run_exit_gate` に migration (tests-only) |
| H-3a | #126 | `5d19993` | tests | `test_exit_flow.py` を `ExitExecutor` → `run_exit_gate` に migration (tests-only) |
| H-3b | #127 | `328dd1b` | tests | PR-5 / U-2 safe_stop wiring test を `ExitExecutor` → `run_exit_gate` に migration (tests-only) |
| H-3c part 1 | #128 | `571d21f` | tests | paper-smoke E2E Stage 7 を `ExitExecutor` → `run_exit_gate` に migration。**この時点で `tests/` 配下の `ExitExecutor` importer 数は 0** |
| H-3c final | #129 | `54dfe12` | refactor | `ExitExecutor` 削除。M9 H シリーズ完了 |

### 2.2 M シリーズ — `run_exit_gate` の改善

| ステージ | PR | merge commit | 種別 | 主な変更 |
|---|---|---|---|---|
| M-1a | #131 | `7f2faae` | feat | `OpenPositionInfo.side` を `orders.direction` から read-time に LEFT JOIN で導出 (schema 変更なし) |
| M-1b | #132 | `a097323` | refactor | `run_exit_gate` / `Supervisor.attach_exit_gate` から `side=` 引数を削除 — `pos.side` が唯一の真実 |
| M-2 | #133 | `ed22d27` | feat | gross `pnl_realized` を `run_exit_gate` 内で `(fill_price - avg_price) * units * sign(side)` 算出 → `on_close` で永続化 (Cycle 6.7c E3 解消) |
| M-3a | #134 | `9b8c85b` | feat | `Quote` DTO + `QuoteFeed` Protocol + `callable_to_quote_feed` adapter (consumer 不触の純加算) |
| M-3b | #135 | `1ab48ad` | refactor | `run_exit_gate` / `Supervisor.attach_exit_gate` を `QuoteFeed` ベースに rewire (legacy callable は adapter で吸収) |
| M-3c | #136 | `04e5447` | feat | stale quote gate (default 60s, `emergency_stop` bypass, 新 outcome `'noop_stale_quote'`) |

### 2.3 closure memo

| ステージ | PR | merge commit | 種別 | 内容 |
|---|---|---|---|---|
| M-3 closure | #137 | `fe3a5c5` | docs | M-3 シリーズの 1 ページ closure memo (`docs/design/m3_quote_feed_migration_closure_memo.md`) |
| **M9 closure (本 PR)** | — | — | docs | **M9 exit improvements 全体の closure memo (本ファイル)** |

**Master tip after M-3 closure:** `fe3a5c5`.

---

## 3. M9 で守った制約 (全 PR 共通)

| # | 制約 | 全 PR で遵守 |
|---|---|---|
| 1 | 1 PR = 1 責務 | ✅ |
| 2 | additive change — 既存 caller の挙動同値 (M-1b の引数削除は内部のみ; M-3b の rewire は legacy callable を adapter で吸収) | ✅ |
| 3 | schema 変更ゼロ / migration ゼロ | ✅ |
| 4 | `app_settings` 変更ゼロ | ✅ |
| 5 | broker adapter (paper / mock / oanda) 不触 | ✅ |
| 6 | SafeStop 配線 (PR-5 / U-2) を `run_exit_gate` 側で保持 | ✅ (H-1 で seam 化、H-3 削除を経ても整合) |
| 7 | notifier (G-2 / G-3) 不触 | ✅ |
| 8 | metrics (ExitFireMetricsService 等) 不触 | ✅ |
| 9 | runbook (`docs/runbook/`) 不触 | ✅ |
| 10 | 直接 `datetime.now()` / `time.time()` なし — Clock 注入のみ | ✅ |
| 11 | CI 完全 green (test / contract-tests) | ✅ |

---

## 4. アーキテクチャ最終形

### 4.1 唯一の exit 実行経路

```text
[Supervisor.run_exit_gate_tick (H-1 で導入)]
        │
        │  attach 時に 1 回 wrap した QuoteFeed を参照渡し (M-3b)
        │  supervisor=self で SafeStop 配線を保持 (H-1; PR-5 / U-2)
        ▼
[run_exit_gate (唯一の exit 実装)]
        │
        ├─ M-1a: pos.side は orders.direction LEFT JOIN で導出
        ├─ M-1b: side= 引数なし (pos.side が唯一の真実)
        ├─ M-3a: quote_feed は QuoteFeed | Callable (isinstance 判定)
        ├─ M-3c: per-position stale gate (age > max → noop_stale_quote)
        ▼
[ExitPolicyService.evaluate(...)]
        │
        ▼
[broker.place_order (paper / mock / oanda — 不触)]
        │
        │  fill_price 取得
        ▼
[M-2: pnl_realized = (fill_price - avg_price) * units * sign(side)]
        │
        ▼
[StateManager.on_close (post-I-09 write path; append-only)]
        │
        ▼
[positions(close) + close_events 同時書込 (outbox enqueue 含む)]


[AccountTypeMismatchRuntime path (PR-5 / U-2)]
        │
        ▼
[Supervisor.trigger_safe_stop(reason='account_type_mismatch_runtime')]
        ※ run_exit_gate の supervisor 引数経由で発火
        ※ ExitExecutor 削除後もこの配線は変わらず生きている
```

### 4.2 ExitExecutor が消えた後に残っている契約

- `Supervisor.trigger_safe_stop(reason=..., occurred_at=..., payload=...)` のシグネチャ
- `payload` キーセット: `{actual_account_type, expected_account_type, instrument, client_order_id, detail}` (PR-4 / PR-5 / U-2 で固定)
- `StateManager.on_close(...)` の呼出契約 (close_events / positions 同時書込 + outbox enqueue)
- `ExitDecision` (`position_id` 必須 / `should_exit` / `reasons` / `primary_reason`) の DTO 形

---

## 5. 解消済み / 未解消の整理

### 5.1 M9 で解消したもの

| 課題 | 状態 | 解消した PR |
|---|---|---|
| ExitExecutor と `run_exit_gate` の二重経路 | ✅ 解消 (`run_exit_gate` 単一化) | H-1..H-3c-final |
| Supervisor が exit 経路に cadence seam を持たない | ✅ 解消 (`attach_exit_gate` / `run_exit_gate_tick`) | H-1 |
| 旧テスト群が ExitExecutor を import し続ける | ✅ 解消 (importer 数 0) | H-2 / H-3a / H-3b / H-3c-part1 |
| ExitExecutor が tree に残存 | ✅ 解消 (削除) | H-3c-final |
| `OpenPositionInfo.side` が呼出側から渡される | ✅ 解消 (orders.direction から read-time 導出) | M-1a |
| `run_exit_gate(side=...)` 引数で side が外から汚染し得る | ✅ 解消 (引数削除) | M-1b |
| `pnl_realized` が常に NULL (Cycle 6.7c E3) | ✅ 解消 (gross pnl 算出 + on_close 永続化) | M-2 |
| 価格に timestamp が付かない (staleness 判定不能) | ✅ 解消 (`Quote.ts`, tz-aware) | M-3a |
| 価格のソースが追跡できない | ✅ 解消 (`Quote.source` + SOURCE_* 定数) | M-3a |
| Producer 側の差し込み先が決まっていない | ✅ 解消 (`QuoteFeed` Protocol) | M-3a |
| 既存 callable 呼出側に破壊的変更を強いる | ✅ 回避 (`callable_to_quote_feed` で吸収) | M-3a → M-3b |
| `run_exit_gate` が `quote.ts` を見られない | ✅ 解消 (QuoteFeed ベース化) | M-3b |
| 古い quote で close 判定が走り得る | ✅ 解消 (60s 既定の stale gate) | M-3c |
| operator flat-all が feed 障害で塞がれ得る | ✅ 解消 (`emergency_stop` bypass) | M-3c |
| stale quote 発生時に観測手段がない | ✅ 解消 (WARNING ログ + 専用 outcome) | M-3c |
| M-3 シリーズの境界が散逸 | ✅ 解消 (M-3 closure memo) | #137 |

### 5.2 M9 で意図的に未解消 (deferral)

| 項目 | 現状 | pickup 条件 / 理由 |
|---|---|---|
| **M-3d**: live OANDA streaming producer | **未着手** | M-3 シリーズ最終段。明示指示まで pickup しない (M-3 closure memo §6 が pickup 前提のチェックリスト) |
| `stale_max_age_seconds` の `app_settings` 化 | per-call argument のみ | live producer landing 後に運用負荷を見てから判断。早期に config 化すると schema 変更が先行発生し additive 性が崩れる (M-3 closure §5.2) |
| stale 発火回数の metrics 化 | 未対応 (ログのみ) | ExitFireMetricsService 流の read-only service として後段で別 PR |
| stale gate の operator runbook | 未対応 | live producer (M-3d) で初めて実 runtime で発火し得るため、runbook は M-3d 後に書く方が情報量が高い |
| `pnl_realized` の **net (手数料・スプレッド込)** 化 | 未対応 (現状 gross のみ) | OANDA 側の transactions detail 取得経路が未整備。M-2 は gross までで意図的に止めた |
| paper-mode broker への QuoteFeed 直接接続 | 未対応 (paper は callable のままで動く) | adapter で完全互換のため緊急性なし。M-3d で live と paper の対称性を確保するときに同時検討 |
| ExitFireMetricsService の `pnl_summary_by_reason` 実数値 | M-2 landing で自動的に NULL → 実数値に切替 (service 側コード変更不要) | M-2 で `pnl_realized` が書かれるようになったため、Phase 7 ダッシュボード接続時に確認 |

### 5.3 非影響を再確認

M9 シリーズで diff ゼロを維持した領域 (closure として明示):

- `ExitPolicyService.evaluate` / `ExitDecision` (DTO 形ごと不触)
- `StateManager.on_close` の呼出契約 / write path (PR-5 / U-2 / I-09 構造そのまま)
- broker adapter (paper / mock / oanda)
- SafeStop trigger 配線そのもの (PR-5 / U-2; H-1 の `supervisor=self` で `run_exit_gate` 側に保持)
- notifier (G-2 / G-3)
- metrics emission (ExitFireMetricsService 含む)
- runbook (`docs/runbook/`)
- dashboard query wrappers (`dashboard_query_service`)
- `app_settings` テーブル / seed
- 全 schema (orders / positions / close_events / order_transactions / outbox)
- Alembic migration

→ **M9 exit improvements は "exit 経路の単一化 + 5 種の純加算改善 (side / pnl / quote DTO / consumer rewire / stale gate)" として閉じた**。下流 (broker / state / close-event 書込) の契約も上流 (Supervisor lifecycle / cadence) の契約も変更なし。

---

## 6. SafeStop 配線が `run_exit_gate` 側で維持されていること

PR-5 / U-2 で確立された SafeStop 配線は ExitExecutor 削除後も生きている。証跡:

1. **H-1 (PR #124)** — `Supervisor.attach_exit_gate` で `_ExitGateAttachment(supervisor=self, ...)` を組み立て、`run_exit_gate_tick` がそれを `run_exit_gate(supervisor=self, ...)` に転送するよう新設。これで `AccountTypeMismatchRuntime` の発火点が `run_exit_gate` 側に移った。
2. **H-3b (PR #127)** — 旧 ExitExecutor 上で pin されていた safe_stop wiring 契約 (canonical reason / payload キーセット / supervisor 失敗時の例外伝播) を `tests/unit/test_exit_executor_safe_stop_wiring.py` (改名後は `tests/unit/test_exit_executor_safe_stop_wiring.py` のまま — 中身は `run_exit_gate` 経由) で再 pin。
3. **H-3c final (PR #129)** — ExitExecutor 削除。SafeStop 関連の test は H-3b の時点で全て `run_exit_gate` 経由に移っているため、削除で配線が壊れないことが test green で証明された。
4. **M-3b (PR #135)** — Supervisor の `_ExitGateAttachment` を QuoteFeed ベースに rewire したが、`supervisor=self` 部分は **逐語的に保持**。M-3c (#136) でも触っていない。

`tests/unit/test_exit_executor_safe_stop_wiring.py` (旧名のまま `run_exit_gate` を呼ぶ) と `tests/integration/test_supervisor_exit_gate_wiring.py` が回帰テストとして常時 green。

---

## 7. 次候補（判断材料のみ — 着手指示ではない）

> **重要**: 以下は M9 着地後に「自然に次にあり得る方向」を判断材料として並べただけのもの。本 PR は docs-only であり、いずれにも着手しない。pickup には明示指示が必要。

| 候補 | 性質 | 前提 | 想定スコープ |
|---|---|---|---|
| **M-3d** (live OANDA streaming producer) | 機能追加 | M-3 closure §6 解凍チェックリスト確認 | producer 側に `QuoteFeed` 実装、Supervisor attach 時に producer 切替、回帰テストは `_StaleStubFeed` 流で fake injection |
| **net pnl 化** (M-2 の延長) | 機能追加 | OANDA transactions detail 取得経路の整備 | `run_exit_gate` または下流で fees / spread を引いた net 値に置換 (gross と net の二項目化も選択肢) |
| **`stale_max_age_seconds` の `app_settings` 化** | config 整備 | M-3d 後に運用負荷の実測 | schema 追加 + seed + Supervisor 経由の注入。早期着手は additive 性を崩すため非推奨 |
| **stale 発火 metrics 化** | 観測性 | ExitFireMetricsService の拡張余地 | read-only service として別 PR。本シリーズの境界外 |
| **M-3d 後の operator runbook** | docs | M-3d landing 後 | `docs/runbook/` 配下に stale gate の triage 手順を追加 |

判断軸:
- **緊急性**: net pnl > M-3d > その他。ただし net pnl は producer (OANDA) 側の整備次第。
- **additive 安全性**: M-3d / metrics / runbook は完全 additive。`app_settings` 化のみ schema 変更を伴う。
- **依存関係**: metrics / runbook は M-3d landing が前提に近い (live でしか発火しない事象を観測する意味が薄い)。

---

## 8. 参考リンク

### 8.1 シリーズ memory files

- H-1: `memory/project_m9_h1_merged.md`
- H-2: `memory/project_m9_h2_merged.md`
- H-3a: `memory/project_m9_h3a_merged.md`
- H-3b: `memory/project_m9_h3b_merged.md`
- H-3c part1: `memory/project_m9_h3c_part1_merged.md`
- H-3c final: `memory/project_m9_h3c_final_merged.md`
- M-1a: `memory/project_m9_m1a_pr_opened.md`
- M-1b: `memory/project_m9_m1b_pr_opened.md`
- M-2: `memory/project_m9_m2_pr_opened.md`
- M-3a: `memory/project_m9_m3a_pr_opened.md`
- M-3b: `memory/project_m9_m3b_pr_opened.md`
- M-3c: `memory/project_m9_m3c_pr_opened.md`
- M-3 closure: `memory/project_m9_m3_closure_memo_merged.md`

### 8.2 関連 docs

- M-3 シリーズ単独 closure: `docs/design/m3_quote_feed_migration_closure_memo.md` (#137)
- 6.9 series rollup: `docs/design/cycle_6_9_summary.md`
- ExitFireMetricsService runbook: `docs/runbook/exit_fire_metrics.md`
- Phase 6 paper operator checklist: `docs/runbook/phase6_paper_operator_checklist.md`

### 8.3 関連ソース

- `src/fx_ai_trading/services/exit_gate_runner.py` — `run_exit_gate` 本体 (M9 の集積点)
- `src/fx_ai_trading/supervisor/supervisor.py` — `attach_exit_gate` / `run_exit_gate_tick`
- `src/fx_ai_trading/services/state_manager.py` — `on_close` / `open_position_details`
- `src/fx_ai_trading/domain/price_feed.py` — `Quote` / `QuoteFeed` / `callable_to_quote_feed`
- `src/fx_ai_trading/domain/exit.py` — `ExitDecision`
- `src/fx_ai_trading/domain/state.py` — `OpenPositionInfo`

### 8.4 関連テスト

- `tests/unit/test_exit_gate_runner.py` (M-1 / M-2 / M-3 全 acceptance テスト)
- `tests/unit/test_exit_executor_safe_stop_wiring.py` (旧名のまま — 中身は `run_exit_gate` 経由 SafeStop 契約)
- `tests/integration/test_supervisor_exit_gate_wiring.py` (H-1 / M-3b 配線テスト)
- `tests/unit/test_quote_feed.py` (M-3a Quote / QuoteFeed / adapter)
- `tests/contract/test_exit_event_fsm.py` (H-2 で migration 済 FSM contract)
