# Design Memo — G-2 Fix Phase Closure (Cycle 6.13)

> **ステータス**: 確定 (closure record). 本メモは G-2 Fix Phase の実施範囲・残課題・defer 判断を永続化するための真値資料である。
> **作成契機**: G-2 audit (2026-04-22) で検出された 5 種類の自動 safe_stop トリガ未接続に対し、4 PR を逐次マージした後、live 化前残課題を最終整理する目的で作成。
> **重要**: 本メモは新規実装提案を含まない。マージ済み PR と未着手項目の対応・分類のみを記録する。

---

## 1. 目的 / スコープ

- **目的**:
  - G-2 audit で検出された 10 件の Issue (I-G2-01〜10) と 9 件の未接続トリガ (U-1〜U-9) のうち、本 Fix Phase で実施した範囲を確定する
  - マージ済み PR (#112 / #113 / #114 / #115) と監査 ID の対応表を真値として固定する (commit message のラベル誤記を補正)
  - live 化前必須の残課題を「最小限」に絞り、defer 項目を明文化してスコープドリフトを防ぐ
- **スコープ**:
  - G-2 Fix Phase Designer Freeze (in-session, 2026-04-22) の総括
  - 残 PR 計画 (live 化前必須のみ、最大 1 本)
- **非スコープ**:
  - 新規 Issue の追加 (本 Fix Phase 完了後の G-3 audit / 別フェーズで扱う)
  - runbook 書換え (該当 PR で個別対応)
  - M8/M9 実装計画の詳細化

---

## 2. G-2 Audit 結果サマリ (2026-04-22 監査)

**結論**: **FAIL** — ドキュメント・契約に記載された 5 種類の自動安全停止トリガが全て未接続。`Supervisor.trigger_safe_stop()` の caller は `supervisor/__main__.py` の signal handler 1 箇所のみで、システム由来の異常に対する自律停止能力は実質ゼロ。

### 検出された 10 Issue (I-G2-*)

| ID | 内容 | 深刻度 |
|---|---|---|
| I-G2-01 | `AccountTypeMismatchRuntime` 例外が safe_stop に接続されていない | Critical |
| I-G2-02 | `CriticalWriteError` がどこにも raise されていない (raise sites = 0 hit) | Critical |
| I-G2-03 | `StreamWatchdog` が stub (always True) | High |
| I-G2-04 | `MidRunReconciler` の drift 検知が safe_stop を発火しない | High |
| I-G2-05 | `HealthChecker` 失敗が safe_stop に接続されていない | High |
| I-G2-06 | SafeStopHandler Step 1/2/3 が try/except で保護されていない | Medium |
| I-G2-07 | Idempotency が部分失敗時に「リトライ封印」として機能してしまう | Medium |
| I-G2-08 | FileNotifier の silent failure (dispatcher が返値を確認しない) | Medium |
| I-G2-09 | supervisor 起動中シグナル取り逃しウィンドウ | Low |
| I-G2-10 | `emergency-flat-all` が safe_stop sequence を経由しない | High |

### 未接続トリガ 9 件 (U-*)

| # | イベント | 出典 | 現状 |
|---|---|---|---|
| U-1 | `account_type_mismatch_runtime` | `exceptions.py:57`, `dispatcher.py:8` | 例外 raise はある / safe_stop fire 無し |
| U-2 | `db.critical_write_failed` | `exceptions.py:108`, `dispatcher.py:8` | 例外 raise すら無し |
| U-3 | `stream.gap_sustained` | `dispatcher.py:9`, watchdog 設計 | watchdog stub (always True) |
| U-4 | `reconciler.mismatch_manual_required` | `dispatcher.py:9` | MidRunReconciler は audit のみ |
| U-5 | `ntp.skew_reject` | `dispatcher.py:9` | startup error → exit code 2 (safe_stop fire 無し) |
| U-6 | `drawdown_daily_exceeded` | `safe_stop.py:73` 例示 | 計測経路自体無し |
| U-7 | `health_check_failed` (runtime detection) | `health.py` | 起動後 caller 無し |
| U-8 | `fatal_unhandled_exception` | (明文化なし) | uncaught exception → 即死、safe_stop 無し |
| U-9 | `emergency_flat_all_initiated` | `ctl.py:60-97` | safe_stop に接続されていない |

---

## 3. PR ↔ 監査 ID 対応表 (ラベル補正の真値)

本 Fix Phase でマージ済みの 4 PR と監査 ID の対応を以下に固定する。
**commit message / PR title 上のラベルは書き換えず、本表を真値とする**。

| PR # | Branch | Commit / PR title 上の ID | 監査メモの真の ID | 内容 | 整合 |
|---|---|---|---|---|---|
| **#112** | `fix/g2-pr1-safe-stop-step-exception-guard` | `I-G2-06` | **I-G2-06** | SafeStopHandler Step 1/2/3 例外保護 (各 step に try/except + bool 戻り値) | ✅ 一致 |
| **#113** | `fix/g2-pr2-safe-stop-completed-flag` | `I-G2-02` ← **誤記** | **I-G2-07** | `_safe_stop_completed` を `_is_stopped` から分離 (idempotency 罠の解消) | ⚠️ ラベル不一致 (本表が真値) |
| **#114** | `fix/g2-pr4-wire-account-type-mismatch-runtime` | `U-1` | **U-1** | `AccountTypeMismatchRuntime` → `trigger_safe_stop` 配線 (`run_execution_gate`) | ✅ 一致 |
| **#115** | `fix/g2-pr5-wire-account-type-mismatch-exit-paths` | `U-2` ← **計画外**ラベル流用 | **U-1b** (Designer Freeze 計画外、U-1 を exit paths へ拡張) | 同上 wiring を `run_exit_gate` / `ExitExecutor.execute` へ展開 | ⚠️ U-2 (audit) = `db.critical_write_failed` と衝突 (本表が真値) |

**運用方針**:
- commit 履歴は書き換えない (master tip 保護 / squash 済み)
- 今後本フェーズの PR を参照する際は、本表の「監査メモの真の ID」列を用いる
- 将来 audit を再実施する際は、本表を起点に真値の対応を辿る

### Designer Freeze 5 PR 計画と実施状況

Designer Freeze (in-session, 2026-04-22) で立てた 5 PR 計画と実施結果:

| 元計画 | 内容 | 実施 PR | 状態 |
|---|---|---|---|
| PR-1 | I-G2-06 (Step 1/2/3 例外保護) | #112 | ✅ merged |
| PR-2 | I-G2-07 (idempotency 再試行解禁) | #113 | ✅ merged (ラベル誤記あり) |
| PR-3 | I-G2-09 (signal handler 早期 install) | — | ❌ skip → defer (§5 参照) |
| PR-4 | U-1 (account_type → execution_gate wiring) | #114 | ✅ merged |
| PR-5 | U-9 (emergency-flat-all → safe_stop) | — | ❌ 当初 skip → 本 Closure 後に PR-α として再着手 |
| (計画外) | U-1b (U-1 を exit paths へ拡張) | #115 | ✅ merged |

---

## 4. Closure 判定: live 化前必須残課題

本 Fix Phase 残タスクを「live 前必須 / M8/M9 待ち / 後続まとめ」の 3 区分に分類し、live 化前に必須なのは **U-9 のみ** に確定する。

| 項目 | 監査 severity | 判定 | 根拠 |
|---|---|---|---|
| **U-9** (`emergency-flat-all` → safe_stop) | High (I-G2-10 と対) | **live 前必須** | live 運用で operator が打つ唯一の緊急停止コマンドが現状 FileNotifier 書込のみ。「停めるべき時に停まる」契約が空文化しており、live 化前 must-resolve |
| **I-G2-09** (signal early install) | Low | **後続まとめ** (M8/M9 supervisor loop 着手時) | startup race 数秒のみ / 人間運用で回避可。M8/M9 supervisor loop の signal 設計と一緒に組み直す方が、暫定 handler の重複が避けられる |
| **U-2** (`db.critical_write_failed`) | Critical | **M8 wiring とまとめる** | raise site 自体が 0 hit。docs-only PR は単独価値が薄い。M8 (OutboxProcessor / Critical tier writer 接続) で raise + wiring + docs を 1 PR 化する方が乖離期間ゼロ |

→ **live 化前残 PR = 1 本 (U-9 配線、本 Closure memo 完了後に PR-α として着手)**

---

## 5. Deferral 一覧 (M8/M9 / 後続まとめ)

以下は本 Fix Phase の scope 外として明示的に defer する項目。各項目の defer 先と理由を本表で固定する。

| ID | イベント / 内容 | Defer 先 | 理由 |
|---|---|---|---|
| **U-2** | `db.critical_write_failed` (`CriticalWriteError` raise sites + wiring + docs sync) | **M8** (OutboxProcessor / Critical tier writer 着手時) | raise site 自体が 0 hit。docs-only では実害不変。M8 で raise + wiring + docs を 1 PR 化 |
| **U-3** | `stream.gap_sustained` | **M9** | StreamWatchdog 本実装が前提 (現状 stub `always True`) |
| **U-4** | `reconciler.mismatch_manual_required` | **M8** | MidRunReconciler 本接続が前提 (現状 audit のみ / `__main__` で instantiate されていない) |
| **U-5** | `ntp.skew_reject` | **M8/M9** (supervisor loop の中で再評価) | 現状 startup error → exit code 2 で完結。runtime 検知 → safe_stop は loop 着手時に再設計 |
| **U-6** | `drawdown_daily_exceeded` | **Iter 2 後半 / M-EXIT-1 系** | 計測経路自体が無い (audit でも別カテゴリ扱い) |
| **U-7** | `health_check_failed` (runtime detection) | **M8/M9** (cadence watchdog / supervisor loop) | startup 時のみ caller 有り。本実装が前提 |
| **U-8** | `fatal_unhandled_exception` | **後続 (要文書化)** | 明文化なし。audit 上 "uncaught exception → 即死" 報告のみ |
| **I-G2-09** | startup 中 signal 取り逃し | **M8/M9** (supervisor loop 着手時) | Low severity。supervisor loop の signal 設計と一緒に組み直す方が暫定 handler の重複が避けられる |
| **G-3 audit** | NotifierDispatcher 多チャネル配信検証 | **PR-α merge 後** に着手可 | I-G2-07 が #113 で既に解消済みなので G-3 を後置する根拠は消失 (read-only audit) |

---

## 6. 残 PR 計画 (本 Closure memo merge 後に着手)

### PR-α: U-9 — `ctl emergency-flat-all` → safe_stop sequence 配線

| 項目 | 内容 |
|---|---|
| 責務 | `scripts/ctl.py` `_do_emergency_flat` の拡張のみ |
| 変更内容 | 既存 FileNotifier 呼出は維持。直後に (1) `SafeStopJournal.append(event_code="emergency_flat_initiated", ...)`、(2) `ProcessManager(pid_file).stop()` を追加 |
| supervisor 未起動時の仕様 | PID file 不在時は journal append のみ実行、stop は no-op (cross-process magic は導入しない) |
| 挙動 | supervisor 側の既存 signal handler 経路 (#112 で堅牢化済み) が `trigger_safe_stop` を発火 → `safe_stop.jsonl` に 2 entry (`emergency_flat_initiated` + `safe_stop.triggered`) が残る |
| 対象ファイル | `scripts/ctl.py` のみ + 新規 integration test |
| 非対象 | 実際の broker 側 flat 発注 (既存 docstring 通り Supervisor / broker layer の責務)、cross-process signaling magic |
| 依存 | なし (#112 / #113 で safe_stop 経路は既に堅牢) |

### G-2 Fix Phase 完了条件

以下 2 つが満たされた時点で G-2 Fix Phase は **クローズ**:
1. PR-α (U-9 配線) が merge される
2. 本 Closure memo (PR-β) が merge される

クローズ後の次フェーズは **G-3 audit** (NotifierDispatcher 多チャネル配信、read-only)。

---

## 7. 関連資料

- `docs/design/safety_verification_gaps_memo.md` — Cycle 6.12 で書かれた verification gap memo (G-1/G-2/G-3 verification の元メモ)
- `docs/phase6_hardening.md §6.1` — safe_stop 多重化契約
- `docs/operations.md §F14` — operator runbook 上の safe_stop reason 一覧
- `src/fx_ai_trading/supervisor/safe_stop.py` — SafeStopHandler 実装 (#112 / #113 で堅牢化済み)
- `src/fx_ai_trading/supervisor/supervisor.py` — `trigger_safe_stop` 入口 (#113 で `_safe_stop_completed` 分離済み)
- `src/fx_ai_trading/services/execution_gate_runner.py` — U-1 wiring (#114)
- `src/fx_ai_trading/services/exit_gate_runner.py` / `exit_executor.py` — U-1b wiring (#115)
- `scripts/ctl.py` — U-9 wiring 対象 (PR-α で着手)

---

## 8. 非対象 (本メモで決めないこと)

- **新規 Issue の追加** — 本 Closure memo は確定済みの Audit 結果と PR 実施状況の真値化のみを担う
- **PR-α の実装詳細** — §6 は仕様確定、実装着手は PR-α の commit / PR で行う
- **M8/M9 の実装計画** — defer 先のみ確定し、実装計画は M8/M9 着手時に別メモで策定
- **commit message の書き換え** — 不可逆かつ master tip 保護のため、本 §3 の対応表を真値として永続化する方針
