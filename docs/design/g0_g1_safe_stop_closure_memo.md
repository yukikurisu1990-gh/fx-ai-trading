# Design Memo — G-0/G-1 Safe-Stop Fix Closure

> **ステータス**: 確定 (closure record). 本メモは G-0/G-1 SafeStop 経路修復の実施範囲・解消状況・defer 判断を永続化するための真値資料である。
> **作成契機**: PR #166 (PR-A, Unix 経路) と PR #167 (PR-B, Windows 経路) のマージにより、`ctl stop` から `SafeStopHandler` 4-step 契約への到達経路が両 OS で機能するようになった。closed-as-stale となった PR #111 (旧実装) との関係を明示し、live 化前残課題を整理する目的で作成。
> **重要**: 本メモは新規実装提案を含まない。マージ済み PR と未着手項目の対応・分類のみを記録する。
> **関連メモ**: `docs/design/g3_fix_phase_closure_memo.md` (notifier dispatcher 側 / 直前フェーズの closure 様式) / `docs/design/m9_final_closure_memo.md` (M9 exit pipeline closure)。

---

## 1. 目的 / スコープ

- **目的**:
  - G-0/G-1 監査で検出された Safe-Stop 経路欠落 (`python -m fx_ai_trading.supervisor` が startup 後即 exit 0 → `ProcessManager.stop()` が既終了プロセスを `proc.terminate()` する dead-code 状態) の解消範囲を確定する
  - PR-A (#166) / PR-B (#167) の役割分担と、両 OS で `SafeStopHandler` 4-step 契約 (journal → loop_stop → notifier → supervisor_events) が外部から起動可能になった事実を真値として固定する
  - closed-as-stale となった PR #111 (旧実装) との関係を明文化し、再 implementation の判断根拠を残す
  - production deploy 前の operator/oncall 向けに、`ctl stop` の挙動が両 OS で「graceful safe_stop」になった旨を確定する
- **スコープ**:
  - PR-A (#166) / PR-B (#167) で landed した変更点と、それが解消した監査リスクの対応表
  - PR #111 closure 判断 (rebase 不可 → 現 master 上で再 implementation) の永続化
  - safe_stop 経路の現状実態 (Unix=SIGTERM/SIGINT、Windows=SIGBREAK via CTRL_BREAK_EVENT) の operator 説明
- **非スコープ**:
  - Notifier dispatcher / channel 側の修復 (G-3 で完結済 — `g3_fix_phase_closure_memo.md` を参照)
  - SafeStopHandler 内部 4-step の振る舞い変更 (本 Fix の対象は「経路の到達可能性」のみ)
  - M9 exit pipeline 側の修復 (`m9_final_closure_memo.md` 参照)

---

## 2. 監査結果サマリ (G-0/G-1)

**結論**: **FAIL** — `SafeStopHandler` 4-step 契約はコード上存在し unit test も通っていたが、それを起動する経路が production には存在しなかった。具体的には:

| ID | severity | 内容 | 出典 |
|---|---|---|---|
| **G-0** | Critical | `python -m fx_ai_trading.supervisor` が startup() 完了後に即 exit 0 → 外部からの停止信号を待つ block 点が無い | `supervisor/__main__.py` 旧実装 |
| **G-1** | Critical | Windows で `ProcessManager.stop()` が `proc.terminate()` を呼ぶが、これは `TerminateProcess` (uncatchable) であり SafeStopHandler が一切走らない | `ops/process_manager.py` 旧実装 |

**検出経路**: G-3 audit と並行して整理された supervisor process lifecycle の調査 (R-1 系) で発覚。`grep -rn "trigger_safe_stop" src` で signal handler からの呼出が 0 hit だったことが直接の根拠。

---

## 3. PR ↔ G-* 対応表 (Closure 真値)

| PR | branch / merge sha | 対応 G-* | 解消種別 | 備考 |
|---|---|---|---|---|
| **PR-A** (#166) | `fix/supervisor-safe-stop-block-on-signal` → `8b4fadb` | **G-0** | full close (Unix) | `__main__.py` に `_install_signal_driven_safe_stop()` を新設。SIGTERM/SIGINT で `threading.Event.set()` → main thread で `Supervisor.trigger_safe_stop(reason="signal_received")` を発火。signal handler は flag-only、I/O は main thread。 |
| **PR-B** (#167) | `fix/supervisor-safe-stop-windows-compat` → `2938498` | **G-1** | full close (Windows) | `ProcessManager.start()` で `creationflags=CREATE_NEW_PROCESS_GROUP`、`stop()` で `os.kill(pid, CTRL_BREAK_EVENT)` (catchable)。`__main__.py` で `SIGBREAK` も同じ flag-only handler に登録。 |

**到達 contract**:
- `Supervisor.trigger_safe_stop(reason, occurred_at)` → `SafeStopHandler` 4-step (journal → loop_stop → notifier → supervisor_events) → `__main__.main()` が exit 0/1/2 を返す。
- exit code: 0 = normal safe_stop 完了、1 = `StartupError` (startup 段階失敗で signal 待ちに到達せず)、2 = `trigger_safe_stop` 自体が raise。

---

## 4. PR #111 (旧実装) の closure 判断

PR #111 は本 Fix と同じ問題に対する旧 branch (`feature/safe-stop-block-on-signal-old`) として 2026-04-23 時点で open 状態にあったが、以下の理由で **close-as-stale** とした:

- **drift 17,742 deletions**: branch 作成以降に master 側で M9 cleanup / M10 シリーズ / replay infrastructure / cycle-15〜17 schema が landed しており、機械的 rebase は事実上 master 側の作業を巻き戻す結果になる。
- **conflict 範囲が `__main__.py` の単一関数を超え、test 構造 (M9 exit pipeline) / process_manager 周辺の M22 contract まで波及していた**。
- **設計意図 (signal handler は flag-only / I/O は main thread)** は PR #111 の commit message に文書化済 — 再 implementation でも完全に保存できる。

→ 現 master 上で PR-A (Unix path) を新規 PR として開き直し、その上で PR-B (Windows compat) を分割実装した。**PR #111 自体に commit していた ServiceImpl 分は廃棄し、本メモが唯一の永続記録となる。**

`memory/project_g0_g1_safe_stop_pra_merged.md` および `memory/project_g0_g1_safe_stop_prb_merged.md` も同じ判断を保存している。

---

## 5. テスト coverage 配置

| 観点 | テスト | 備考 |
|---|---|---|
| Unix subprocess smoke (SIGTERM end-to-end) | `tests/integration/test_supervisor_main_entrypoint.py::TestModuleSubprocessSmoke::test_module_blocks_then_exits_clean_on_sigterm` | win32 では skip (理由は同テスト docstring) |
| signal handler 設置 (Event 返却 / 状態) | `TestSignalDrivenSafeStop::test_install_returns_event_and_received_list` | 全 OS |
| handler 動作 (signum 記録 / Event set) | `TestSignalDrivenSafeStop::test_handler_sets_event_and_records_signum` | 全 OS |
| Windows SIGBREAK 登録 | `TestSignalDrivenSafeStop::test_install_registers_sigbreak_on_windows` | win32 のみ |
| `main()` block → trigger_safe_stop 発火 | `TestSignalDrivenSafeStop::test_main_blocks_then_fires_safe_stop_on_signal` | 全 OS / spy で trigger 引数を検証 |
| `ProcessManager.start()` 分岐 (creationflags) | `tests/integration/test_ctl_start_stop.py::TestProcessManagerCrossPlatformBranching::test_start_on_unix_does_not_set_creationflags` / `test_start_on_windows_sets_create_new_process_group` | mock-based / 全 OS |
| `ProcessManager.stop()` 分岐 (signal kind) | 同上 `test_stop_on_unix_calls_terminate` / `test_stop_on_windows_sends_ctrl_break_event` | mock-based / 全 OS |

**Windows subprocess smoke を「敢えて作らなかった」理由**: `CTRL_BREAK_EVENT` は console を共有するプロセスにのみ届く。pytest を git-bash / 一般的な CI shell で起動した場合 console が attach しておらず、event は silently drop される。これは OS の delivery 規約であり本コードベースの実装責務ではない。production の `ctl stop` は real shell から起動されるので console を持ち、delivery は OS 保証で機能する。

---

## 6. 実態整理 (operator / oncall 向け)

PR-A + PR-B 後の `ctl stop` 挙動:

```
Unix (Linux / macOS):
    ctl stop
      → ProcessManager.stop()
      → proc.terminate()  ==  SIGTERM to supervisor PID
      → supervisor _handler() sets stop_event
      → main thread: Supervisor.trigger_safe_stop(reason="signal_received", occurred_at=clock.now())
      → SafeStopHandler 4-step: journal → loop_stop → notifier → supervisor_events
      → exit 0 (or 2 if trigger raised)

Windows:
    ctl stop
      → ProcessManager.stop()
      → os.kill(pid, signal.CTRL_BREAK_EVENT)  to process group created by start()
      → supervisor receives SIGBREAK, _handler() sets stop_event
      → main thread: Supervisor.trigger_safe_stop(reason="signal_received", occurred_at=clock.now())
      → SafeStopHandler 4-step (同上)
      → exit 0 (or 2)

Fallback (両 OS 共通):
    timeout_graceful (default 10s) 経過 → ProcessManager.stop() が SIGKILL (proc.kill())
    SIGKILL は uncatchable / safe_stop は走らない。
    journal は再起動時の Supervisor startup step 7 (SafeStopJournal reconcile) で「未完了 safe_stop」として検出される設計
    (g3_fix_phase_closure_memo.md §3 R-9/R-10 関連)。
```

**oncall 注意点**:
- `ctl stop` の正常時は exit code 0 + `safe_stop complete` ログラインで判定可能 (`__main__.py:205`)。
- exit code 2 は `trigger_safe_stop` 自体が raise したケース → SafeStopHandler 内部の障害。`safe_stop.jsonl` を確認すること。
- 10 秒以内に exit しない場合、SIGKILL fallback が走る。次回 startup で journal reconcile が走るので、運用上は journal を確認して safe_stop が「中断状態」のままになっていないかを見る。

---

## 7. defer 項目 (本 Fix の対象外)

| ID | 内容 | defer 先 | 根拠 |
|---|---|---|---|
| D-1 | SIGKILL fallback 後の journal reconcile を operator が認知できる notification | M16 metrics-loop / oncall pager 整備 | 本 Fix は経路到達のみが scope。reconcile 自体は startup step 7 で既存。 |
| D-2 | trigger_safe_stop の reason 引数値の標準化 (現状 `"signal_received"` 固定) | 別 audit で類型化 | `safe_stop.jsonl` 検索性のための文字列体系化。本 Fix では引数渡しのみ実装。 |
| D-3 | Windows console-less 環境での CTRL_BREAK_EVENT 配送ハードニング | OS contract 範囲外 | 上記 §5 の理由により本コードベース責務外と判断。 |
| D-4 | trading-loop / metrics-loop 自体の signal hook 配線 | M9 / M16 | 本 Fix は supervisor process 側のみ。loop 側は別 milestone。 |

---

## 8. live 化判定材料

本メモ単独で GO/NO-GO を出さない。判定は以下を参照する:

- **本 closure**: G-0/G-1 経路が両 OS で機能 = 「停止経路の前提」が成立 (本メモ §3-§5)
- **G-3 closure** (`g3_fix_phase_closure_memo.md`): notifier dispatcher 側が file-only safe + Slack opt-in + Email 未活性で機能
- **M9 final closure** (`m9_final_closure_memo.md`): exit pipeline 側が `run_exit_gate` 単一経路に統合済
- **Phase 6 paper GO record** (`memory/project_phase6_paper_go.md`): paper-mode 運用判定の真値

→ 三者組合せで「safe_stop の 4-step 契約が、外部からの停止信号で確実に発火し、各 step が実装と運用の両面で動作する」が成立する。

---

## 9. 索引 (audit ID / PR / commit)

| ID | PR | merge sha | 関連 commit |
|---|---|---|---|
| G-0 | #166 | `8b4fadb` | (squash 単独) |
| G-1 | #167 | `2938498` | PR-B 内 2 commit (`b3e3dbc` impl, `e2c73cc` Linux-CI import 修正) |
| (referenced) closed | #111 | — | close-as-stale, drift 17,742 deletions |

memory pointers:
- `memory/project_g0_g1_safe_stop_pra_merged.md` — PR-A 詳細
- `memory/project_g0_g1_safe_stop_prb_merged.md` — PR-B 詳細

---
