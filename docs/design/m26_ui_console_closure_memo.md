# Design Memo — M26 UI / Console Operational Boundary Closure

> **ステータス**: 確定 (closure record). 本メモは M26 (UI / Console Operational Boundary) シリーズの実施範囲・解消状況・defer 判断を永続化するための真値資料である。
> **作成契機**: P1 (#83) / P2 (#85) / P3 (#86) の 3 Phase が master に landed し、最後の未消化チェックボックス (operator 手順書追記) を PR #170 が解消したことで、`docs/m26_implementation_plan.md` §8 の完了条件をすべて満たした。
> **重要**: 本メモは新規実装提案を含まない。マージ済み PR と未着手項目の対応・分類のみを記録する。
> **関連メモ**: `docs/design/g0_g1_safe_stop_closure_memo.md` (停止経路 closure) / `docs/design/g3_fix_phase_closure_memo.md` (notifier 側) / `docs/design/m9_final_closure_memo.md` (exit pipeline)。

---

## 1. 目的 / スコープ

- **目的**:
  - Iter2 で凍結のみ行った M26 仕様 (`docs/operations.md` §15 / `docs/implementation_contracts.md` §2.16 / `docs/development_rules.md` §10.3.1 / `docs/iteration2_implementation_plan.md` §6.14) を、Iter3 で 3 Phase / 4 PR で実装し終えた事実を真値として固定する
  - 凍結 4 docs を改変せず、UI 側を仕様に従わせた経路の対応関係を文書化する
  - production deploy 前の operator/oncall 向けに、`Operator Console` / `Configuration Console (Runtime / Bootstrap)` の操作境界を確定する
  - Phase 8 送り catalog (12 項目) を**前倒し実装していない**ことを再確認する
- **スコープ**:
  - PR #65 (spec freeze) → PR #84 (実装計画) → PR #83 / #85 / #86 (P1〜P3 実装) → PR #170 (operator 手順書) の対応表
  - 計画 §1.2 で却下された P3→P2→P1 順との比較根拠の保存
  - 凍結 4 docs の章節とコード実装の cross-reference
- **非スコープ**:
  - Phase 8 送り 12 項目 (SSO/RBAC/HTTP API/Slack 双方向/UI ボタン化 emergency-flat-all 等) — 計画 §5 に列挙、本シリーズ外
  - `dashboard_query_service` の HTTP 化 (B 形態) — Phase 8 §2.3
  - M21 Learning UI — operations §15.1 「Operational 層 (Learning UI、別系統)」
  - `dashboard_operations_audit` (仮称) テーブル新設 — operations §15.5 / Phase 8

---

## 2. 監査結果サマリ (M26 spec freeze 起源)

**結論**: **PASS** — Iter2 で「仕様凍結のみ・実装は Iter3 送り」と決定された範囲を、Iter3 で凍結 docs に対して drift ゼロで実装完了した。

| ID | severity | 内容 | 出典 |
|---|---|---|---|
| **M26-spec** | (Iter2 当時) | UI 層が ctl と secret 経路を bypass する余地を docs / contract に残していた | `iteration2_implementation_plan.md` §6.14 で凍結 |
| **M26-impl** | (Iter3 当時) | 凍結仕様に対応する Streamlit 実装が未着手 (UI 経由 secret 入力カタログが机上のみ) | `m26_implementation_plan.md` §0 |

**解消経路**: 仕様凍結 (PR #65) → 実装計画 (PR #84) → 3 Phase 順次実装 (PR #83 → #85 → #86) → operator 手順書 (PR #170)。各 PR は 1 責務 / 1 Phase / squash merge で分離。

---

## 3. PR ↔ Phase 対応表 (Closure 真値)

| PR | merge sha | 種別 | 対応 Phase | 主な責務 |
|---|---|---|---|---|
| **#65** | `1e8ebfb` | docs | 仕様凍結 | `operations.md` §15 / `implementation_contracts.md` §2.16 / `development_rules.md` §10.3.1 / `iteration2_implementation_plan.md` §6.14 を文章として凍結 |
| **#84** | `7f5652e` | docs | 実装計画 | `docs/m26_implementation_plan.md` 新設、3 Phase 分割、ファイル table、§5 Phase 8 送り catalog (12 項目)、§7.5 サブエージェント・ループ仕様 |
| **#83** | `9b96e21` | impl | **P1 Operator Console** | `pages/1_Operator_Console.py` + `operator/{__init__, ctl_invoker, preflight}.py` + 2 tests。ctl 4 コマンドを subprocess 薄ラッパで起動。`emergency-flat-all` は Literal 型で除外 |
| **#85** | `4084ecd` | impl | **P2 Configuration Console / Runtime** | `pages/2_Configuration_Console.py` + `config_console/{__init__, runtime_view}.py` + `dashboard_query_service.enqueue_app_settings_change` 追加 + 2 tests。`app_settings_changes` キュー insert のみ、本体 UPDATE 経路なし |
| **#86** | `505b3c5` | impl | **P3 Configuration Console / Bootstrap** | `config_console/{bootstrap_view, env_writer, env_diff}.py` + 4 tests。`.env` を tmp file → `os.replace()` で atomic 書換、PID 在席時は form 非表示 |
| **#170** | `6b024d2` | docs | operator 手順書 | `docs/dashboard_manual_verification.md` に P1 / P2 / P3 walkthrough 追記、`m26_implementation_plan.md` §8 のチェックボックスを完了 |

**到達 contract**:
- ctl 5 コマンドのうち UI 経由実行可能集合 = 4 (`start` / `stop` / `resume-from-safe-stop` / `run-reconciler`)。`emergency-flat-all` は CLI のみ (4 重防御の継続、phase6 §6.18)。
- `app_settings_changes` への 6 列 insert (`name` / `old_value` / `new_value` / `changed_by` / `changed_at` / `reason`) のみが UI 経由 config 変更のシンク。`UPDATE app_settings` を直接実行する経路は UI 側にゼロ。
- `.env` への書込は Bootstrap モード (PID 不在時) のみ可能。tmp file → `os.replace()` の atomic 経路、書込直前に再 PID チェック (race 対策)。
- 平文 secret は DB / log / `st.session_state` に残らない (`st.form(clear_on_submit=True)` + audit row は sha256 prefix 8 文字のみ)。

---

## 4. 凍結 docs と実装の整合 (drift = 0)

`m26_implementation_plan.md` §8 の完了条件「凍結 4 docs の文言は変更されていない」を満たす。実装は仕様に従う方向で行い、仕様側に変更を加えていない。

| 凍結 docs (改変なし) | 実装側 (本シリーズで配置) |
|---|---|
| `operations.md` §15.1 (4 層責務マトリクス) | `pages/1_Operator_Console.py` (Operational 層) / `runtime_view.py` (Runtime mode 層) / `bootstrap_view.py` (Secret + Runtime 接続層) |
| `operations.md` §15.2 (Configuration Console 2 モード) | `pages/2_Configuration_Console.py` の Runtime / Bootstrap タブ分離 |
| `operations.md` §15.3 (Operator Console の責務境界) | `operator/ctl_invoker.py` の `CtlCommand = Literal[...]` で 4 コマンドに型固定 |
| `operations.md` §15.4 (UI 経由 secret 入力カタログ) | `bootstrap_view.py` + `env_writer.py` + `env_diff.py` (sha256 prefix のみで diff/audit) |
| `operations.md` §15.5 (監査ログとの関係) | `dashboard_query_service.enqueue_app_settings_change` への audit row 6 列充填 |
| `operations.md` §15.6 (Phase 8 送り catalog) | 12 項目すべて未実装、計画 §5 に列挙保持 |
| `implementation_contracts.md` §2.16 (UI 層責務契約) | 新規 ctl usecase なし / 新規 Protocol なし / `dashboard_query_service` 拡張は関数 1 個追加のみ |
| `development_rules.md` §10.3.1 (UI 経由 secret 入力ルール) | `text_input(type="password")` + `key=` 引数なし + `clear_on_submit=True` (form 単位) + sha256 prefix 化 |
| `iteration2_implementation_plan.md` §6.14 (M26 マイルストーン定義) | 3 Phase / 3 PR の通り完遂、追加マイルストーン要求なし |

---

## 5. テスト coverage 配置

| 観点 | テスト | Phase |
|---|---|---|
| ctl 4 コマンドの argv 構築 (純粋関数) | `tests/unit/test_ctl_invoker_argv.py` | P1 |
| `emergency-flat-all` の UI 露出ゼロ | `tests/contract/test_operator_console_dangerous_ops_block.py` | P1 |
| PID 在席→ボタン enable/disable | (preflight 純粋関数 + UI smoke) | P1 |
| `enqueue_app_settings_change` 6 列 insert SQL 構築 | `tests/unit/test_enqueue_app_settings_change.py` | P2 |
| 実 DB 上で insert 後の queue 行確認 + `app_settings` 本体不変 | `tests/integration/test_config_runtime_queue_insert.py` | P2 |
| Runtime タブに secret 系 key が現れない | `tests/contract/test_config_console_no_secret_keys.py` | P2 |
| `.env` tmp → `os.replace` atomic + 中途失敗で旧 `.env` 維持 | `tests/unit/test_env_writer_atomic.py` | P3 |
| `.env` diff (key + sha256 prefix) | `tests/unit/test_env_diff.py` | P3 |
| Bootstrap form は PID 在席時に render されない | `tests/contract/test_bootstrap_disabled_when_running.py` | P3 |
| Bootstrap 経路の log capture に平文 secret が現れない | `tests/contract/test_bootstrap_no_plaintext_log.py` | P3 |
| Operator / Runtime / Bootstrap 操作手順 | `docs/dashboard_manual_verification.md` (P1 / P2 / P3 walkthrough) | #170 |

**意図的に作っていないテスト**:
- Streamlit のフル E2E (page render → click → DB 書込) は contract / integration の組合せで代替。Streamlit テスト harness は version 依存が強く、本シリーズは「責務境界が UI module 内で守られていること」を検証することで足りるとした (`m26_implementation_plan.md` §6 横断 Risk #4)。
- secret 値が log に出ないことの動的トレースは `test_bootstrap_no_plaintext_log.py` で網羅。secret rotation の観測ログ系統 (rate / latency) は M21 系の話で本シリーズ外。

---

## 6. 実態整理 (operator / oncall 向け)

PR #83 / #85 / #86 / #170 後の Streamlit dashboard 実態:

```
sidebar:
    app                    — 10 panel ホーム (M19-C)
    Operator Console       — ctl 4 コマンド薄ラッパ (M26 P1)
    Configuration Console  — Runtime / Bootstrap タブ (M26 P2 / P3)

Operator Console (P1):
    PID 不在: Run start = enabled / Run stop = disabled / Run resume = disabled (Reason 必須) / Run reconciler = enabled
    PID 在席: Run start = disabled / Run stop = enabled / Run resume = Reason 入力で enable
    timeout: default 30s (env 上書き可)、超過は st.error
    debounce: 1.5s 内の同一 button click は警告表示で skip
    emergency-flat-all: UI に button/link/form なし。CLI コマンド文字列のみ常時表示

Configuration Console / Runtime (P2):
    現在値テーブル: app_settings 全 row を name / value / type / description / updated_at で表示
    編集対象から除外: expected_account_type (read-only) + secret-like keys (API_KEY/SECRET/PASSWORD/TOKEN/PRIVATE/CREDENTIAL を含む name)
    submit: 「キューに登録 (再起動で反映)」label のみ。app_settings_changes へ 6 列 insert
    apply: 次の Supervisor 再起動 / hot-reload で反映 (UI から即時反映する経路なし)

Configuration Console / Bootstrap (P3):
    PID 在席: form 非表示。warning「App is running — stop the Supervisor before editing .env」のみ
    PID 不在: text_area + Reason + submit ボタンを form 内に表示 (clear_on_submit=True)
    diff preview: added / removed / changed の 3 列、name + sha256 prefix 8 文字のみ。平文値なし
    write: tmp file → os.replace() の atomic 経路。直前に PID 再チェック、race 検出時は中止
    audit: app_settings_changes に name=".env:<KEY>" + old/new = sha256 prefix の 1 row/key
```

**oncall 注意点**:
- UI 経由で `app_settings.value` 本体が直接変わる経路は**ない**。Runtime タブで submit 後も「再起動で反映」のため、即時反映を期待されたら誤解。
- `.env` は Supervisor 停止時しか UI から触れない。稼働中の secret rotate は CLI / 直接編集 + 再起動が必要。
- `emergency-flat-all` は引き続き CLI 専用 (2-factor confirmation、phase6 §6.18 の 4 重防御)。「UI に出ていない」事実は contract test で常時保証。
- 平文 secret が `app_settings_changes` に保存されたら **Bug** (sha256 prefix のみが正)。出現したら即 escalate。

---

## 7. defer 項目 (本シリーズの対象外)

`m26_implementation_plan.md` §5 の Phase 8 送り catalog 12 項目を、本 closure 時点で**いずれも実装していない**ことを再確認する。前倒し禁止 (CLAUDE.md §11 自己拡張禁止 / 計画 §0 前提)。

| # | 機能 | defer 先 |
|---|---|---|
| 1 | SSO / OAuth / SAML 認証 | Phase 8 §2.3, §5.3 |
| 2 | multi-user / role 分離 (viewer / operator / admin) | Phase 8 §2.3, §5.3 |
| 3 | RBAC / per-key 権限制御 | Phase 8 §5.3 |
| 4 | Web UI 刷新 (Next.js + FastAPI / React) | Phase 8 §2.3, §4.3 |
| 5 | HTTP API 経由の operator 操作 (`dashboard_query_service` B 形態) | Phase 8 §4.3 |
| 6 | `dashboard_operations_audit` (仮称) テーブル新設 | operations §15.5 / Phase 8 §5.3 |
| 7 | `SecretProvider` 書込 Interface (`rotate` / `set` 等) の D3 追加 | operations §15.6 / contracts §2.16 |
| 8 | Slack 双方向コマンド (`/fx-ai-trading flat-all` 等) | Phase 8 §2.2, §5.2 |
| 9 | `emergency-flat-all` の UI ボタン化 (4 重防御の解除) | operations §15.1 / phase6 §6.18 |
| 10 | `.env` rotation 自動化 / secret encryption at rest | (将来検討) |
| 11 | DR 訓練 GUI / 月次リハーサル automation | Phase 8 §2.4, §5.4 |
| 12 | 税務エクスポート GUI | Phase 8 §2.5, §5.5 |

---

## 8. live 化判定材料

本メモ単独で GO/NO-GO を出さない。判定は以下を参照する:

- **本 closure**: UI / Console 操作境界が凍結 4 docs 通りに実装され、operator 手順書も整った (本メモ §3-§6)
- **G-0/G-1 closure** (`g0_g1_safe_stop_closure_memo.md`): UI から起動する `ctl stop` が両 OS で SafeStopHandler 4-step を発火する経路を持つ (P1 Operator Console から呼ぶ subprocess 経路の前提)
- **G-3 closure** (`g3_fix_phase_closure_memo.md`): notifier dispatcher 側が file-only safe + Slack opt-in + Email 未活性で機能 (UI で notifier 設定変更を将来許可する場合の前提)
- **M9 final closure** (`m9_final_closure_memo.md`): exit pipeline 側が `run_exit_gate` 単一経路に統合済 (Operator Console の `run-reconciler` から触れる reconcile 後の状態と整合)
- **Phase 6 paper GO record** (`memory/project_phase6_paper_go.md`): paper-mode 運用判定の真値

→ 上記組合せで「operator が UI から触れる範囲が、停止経路 / 通知経路 / exit 経路 / 設定経路のすべてで凍結契約通りに振舞う」が成立する。**live 化 (demo→live 切替) には別途 4 重防御 (phase6 §6.18) と未着手の live-loop runner (M9/M16) が必要であり、本 closure はその前提条件のうち UI / Console 側のみを満たすものである。**

---

## 9. 索引 (Phase / PR / commit)

| Phase / 種別 | PR | merge sha | 関連 docs |
|---|---|---|---|
| spec freeze | #65 | `1e8ebfb` | `operations.md` §15 / `implementation_contracts.md` §2.16 / `development_rules.md` §10.3.1 / `iteration2_implementation_plan.md` §6.14 |
| 実装計画 | #84 | `7f5652e` | `docs/m26_implementation_plan.md` |
| P1 Operator Console | #83 | `9b96e21` | `pages/1_Operator_Console.py` + `operator/*.py` |
| P2 Configuration Console / Runtime | #85 | `4084ecd` | `pages/2_Configuration_Console.py` + `config_console/runtime_view.py` + `dashboard_query_service.enqueue_app_settings_change` |
| P3 Configuration Console / Bootstrap | #86 | `505b3c5` | `config_console/{bootstrap_view, env_writer, env_diff}.py` |
| operator 手順書 | #170 | `6b024d2` | `docs/dashboard_manual_verification.md` (M19-C / M26) |

memory pointers:
- `memory/project_m26_manual_walkthroughs_merged.md` — PR #170 詳細

---
