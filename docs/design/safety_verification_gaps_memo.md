# Design Memo — Safety 検証ギャップ 要確認 (Cycle 6.12)

> **ステータス**: 要確認 (verification placeholder). 本メモは結論ではなく、**コード読込みで確認が必要な docs↔code 乖離候補**を記録する。
> **作成契機**: 全体俯瞰レビュー (2026-04-22) の Safety Officer サブエージェント調査で、paper 運用の安全性評価時に 3 件の未確認 path が検出された。
> **重要**: 本メモは修正を提案しない。検証すべき項目の列挙のみ。

---

## 1. 目的 / スコープ

- **目的**: 運用 runbook (operations.md / phase6_hardening.md / operator_quickstart.md) が前提とする実装契約のうち、**コードパスを最後まで追跡できていない** 3 件を可視化する
- **スコープ**: safe_stop / graceful stop / emergency flat / notifier の実行境界
- **非スコープ**: 実装修正、runbook 書き換え、Notifier Dispatcher の仕様変更

---

## 2. 発見ギャップ (3 件)

### 2.1 ギャップ G-1 — `ctl.py stop` の SafeStopHandler 統合 (優先度: **High**)

**現象:**
- `docs/operator_quickstart.md §2` および `phase6_paper_operator_checklist.md §9` が「`python scripts/ctl.py stop` は graceful 停止を行う」と記載
- `scripts/ctl.py:154-162` で `pm.stop()` (ProcessManager) が呼ばれる
- **未確認**: `ProcessManager.stop()` の先が `SafeStopHandler.fire()` を経由するか否か

**SafeStopHandler の契約 (`src/fx_ai_trading/supervisor/safe_stop.py:62-100`):**
1. Step 1: `journal.append()` (line 91) — logs/safe_stop.jsonl
2. Step 2: `stop_callback()` (line 94) — 実際の loop 停止
3. Step 3: `notifier.dispatch_direct_sync()` (line 97) — 通知
4. Step 4: `supervisor_events` INSERT (line 100) — DB audit

**もし経由しない場合の影響:**
- graceful stop でも journal が記録されない
- 次回起動時の reconciliation で「停止が計画的だったか / 障害停止か」の区別が困難
- runbook の「logs/safe_stop.jsonl 差分確認」(operator_checklist §8) が虚構になる

**要確認箇所:**
- `scripts/ctl.py:154-162` から `pm.stop()` の実装へ辿る
- ProcessManager クラス (探索先未特定 — 候補: `src/fx_ai_trading/supervisor/process_manager.py` または類似)
- `SafeStopHandler.fire()` の呼び出し元 grep

---

### 2.2 ギャップ G-2 — `emergency_flat_all` の close 処理実装先 (優先度: **High**)

**現象:**
- `scripts/ctl.py:60-97` — 2 要素確認後 `_notifier.send()` で critical 通知送出
- `scripts/ctl.py:93` 付近のコメント: "Ensure the Supervisor or broker layer processes the flat order"
- **未確認**: 通知後に**実際のポジション close 処理を実行する component が存在するか / どこにあるか**

**runbook の前提:**
- operator が緊急時 `emergency-flat-all` で全ポジションを強制 close できる (経験則 / ops 文書の通念)
- operator_checklist §6 では「safe_stop は人間判断であり自動発火ではない。迷ったら止める方を優先」と記載
- しかし emergency flat を発火した場合の**実行完了確認手順**が未文書化

**もし close 処理が実装されていない場合の影響:**
- 通知だけ飛んで建玉が残存
- operator は Dashboard で手動 close を別途実施する必要があるが、その手順が runbook にない
- live 化時に致命的 — 「緊急停止コマンドを打ったのに建玉が残っている」事態

**要確認箇所:**
- `scripts/ctl.py:60-97` の emergency_flat_all 実装
- 受け手 component: broker adapter / supervisor / exit_gate_runner のいずれか
- grep 候補キーワード: `emergency_flat`, `flat_all`, `force_close`, `close_all_positions`

---

### 2.3 ギャップ G-3 — NotifierDispatcher の複数チャネル配信 (優先度: **Medium**)

**現象:**
- `SafeStopHandler.fire()` Step 3 (line 97): `notifier.dispatch_direct_sync()` — 通知送出
- `SafeStopHandler.fire()` Step 4 (line 100): `supervisor_events` INSERT が **失敗時に `_log.error()` のみ** (line 153 付近)
- **未確認**: Step 3 の `notifier.dispatch_direct_sync()` が**複数チャネル配信 (Slack / Email / Webhook など)** を実装しているか、単一チャネル依存か

**safety 観点での重要性:**
- Step 4 の DB write が失敗しても、Step 3 の通知が配信済みなら operator は気付ける
- しかし Step 3 が**単一チャネル (例: Slack のみ)** で、その channel が落ちていた場合、operator は safe_stop 発火に気付けない
- operations.md / phase6_hardening.md §6.1 で「多重化」と書かれているが、通知の多重化が実装レベルで保証されているか未確認

**要確認箇所:**
- `Notifier` 実装 (探索先未特定 — `src/fx_ai_trading/**/notifier*.py`)
- `dispatch_direct_sync()` の内部: 登録された channel 数 / 送信ループ / 各 channel 障害時のフォールバック
- 設定ファイル: どの channel が有効化されているか

---

## 3. 検証手順 (次セッション用)

> **重要**: 本検証は **read-only** で完結する。実装修正は docs↔code 乖離が確定した後、別 PR で扱う。

### 3.1 G-1 検証ステップ

1. `scripts/ctl.py` の `stop` command 実装を読み、`pm.stop()` 呼び出し箇所を特定
2. `ProcessManager` クラス定義ファイルを特定し `.stop()` メソッドを読む
3. その中で `SafeStopHandler.fire()` が呼ばれているか確認
4. 呼ばれていない場合: どの stop path が正当なのか (graceful ≠ safe_stop の可能性もある) を判断

### 3.2 G-2 検証ステップ

1. `scripts/ctl.py:60-97` の emergency_flat_all 実装を読み切る
2. `_notifier.send()` 後に実際の close 処理 hook があるか確認
3. broker adapter / supervisor 側で emergency シグナルを listen する component を grep
4. 無い場合: runbook に「emergency flat 後の手動 close 手順」追記が必要 (次 PR)

### 3.3 G-3 検証ステップ

1. `Notifier` / `NotifierDispatcher` 実装ファイル特定
2. `dispatch_direct_sync()` 内で複数 channel を iterate しているか確認
3. 各 channel の失敗 isolation (一つ落ちても他は送る) が実装されているか確認
4. 設定で有効化された channel 数を確認 (paper モード・live モード別)

---

## 4. 確認済み事項 (Safety Officer より転記)

以下は本レビューで**コード確認済み**のため、再確認不要:

- `SafeStopJournal.append()` は `os.fsync(fh.fileno())` で durability 保証済 (`safe_stop_journal.py:60` 付近)
- `SafeStopHandler.fire()` の 4 ステップ順序は実装済 (`safe_stop.py:62-100`)
- demo/live 4 重防御は堅牢 (`phase6_hardening.md §6.18` と実装一致)
- `ExitFireMetricsService` の read-only 契約は履行 (`exit_fire_metrics.py`, `engine.connect()` のみ使用)

---

## 5. 関連資料

- `docs/operator_quickstart.md` — operator 30 秒ナビ
- `docs/runbook/phase6_paper_operator_checklist.md` — Phase 6 paper オペレーター時系列
- `docs/runbook/exit_fire_metrics.md` — exit fire 監視 runbook
- `docs/phase6_hardening.md §6.1` — safe_stop 多重化契約
- `docs/operations.md §2.1 / §4.3` — stream gap / retry policy
- `docs/design/cycle_6_9_summary.md` — Cycle 6.9/6.10 系 rollup

---

## 6. 非対象 (このメモで決めないこと)

- **実装修正は行わない** — 検証確定後、G-1 / G-2 / G-3 それぞれ別 PR で対応
- **runbook 書き換えも行わない** — 検証で差異が確認されてから、該当 runbook を更新
- **Notifier Dispatcher の仕様変更は提案しない** — 現状把握のみ
- **live 化判断材料にはしない** — live 化は Phase 7 別議論 (ただし G-1 / G-2 は live 化前に必須で埋めるべき)

---

## 7. 次アクション (人間監督下)

1. **検証 PR 不要** — read-only 調査はセッション内のコード読取で完結
2. 確認結果を本メモに追記 (§4 の "確認済み事項" 拡張)
3. 乖離が見つかった項目のみ、対応 PR を個別に発行
4. G-1 / G-2 は **live 化ゲート**として扱う (Phase 7 着手前に must-resolve)
