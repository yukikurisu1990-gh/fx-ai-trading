# M26 Implementation Plan (Iteration 3)

> **本書の位置付け**: `docs/iteration2_implementation_plan.md` §6.14 で凍結された M26 (UI / Console Operational Boundary Spec Freeze, docs only) の**実装フェーズ計画**。Iter2 では仕様凍結のみで実装を行わなかったが、Iter3 で本書に従って 3 Phase / 3 PR に分割して実装する。
>
> **凍結済仕様 (本書の上位制約、変更不可)**:
> - `docs/operations.md` §15 (4 層責務マトリクス + 6 サブ節)
> - `docs/implementation_contracts.md` §2.16 (UI / Console 層責務契約)
> - `docs/development_rules.md` §10.3.1 (UI 経由 secret 入力ルール)
> - `docs/iteration2_implementation_plan.md` §6.14 (M26 マイルストーン定義)
> - `docs/design.md` 付録 #7 (UI 層は薄いラッパとしてのみ存在する)

---

## 0. 前提 (Iter3 Cycle 5 で確定済、再議不可)

- **UI = Streamlit 継続**。既存 `src/fx_ai_trading/dashboard/` 上に増設する (Cycle 5 / 推奨案 A)。
- **`dashboard_query_service` は A 形態 (Python 関数) のまま**。HTTP 化 (B 形態) は Phase 8 (`docs/phase8_roadmap.md` §2.3)。
- **新規 ctl usecase 不導入**。M22 で確定した 5 コマンドが UI 経由実行可能集合の上限。
- **新規 Protocol 不導入**。SecretProvider は read-only (`get` / `get_hash` / `list_keys`) のまま。
- **secret 書込 sink は `.env` のみ**。DB 平文書込禁止。
- **`emergency-flat-all` は CLI 専用**。UI から実行不可 (4 重防御の継続、phase6 §6.18)。
- **稼働中の即時反映禁止**。`app_settings` 系列の変更は `app_settings_changes` キュー経由、適用は再起動 / hot-reload で別途トリガ。
- **M21 Learning UI は別系統**。本計画の対象外 (operations §15.1 「Operational 層 (Learning UI、別系統)」)。

---

## 1. Phase 分割と依存

### 1.1 全体図

```
M22 (ctl 5 cmd, master)        Iter3
M19 (Dashboard 10 panel, master) ─┐
M26 spec freeze (master)          │
                                  ├→ P1 Operator Console (PR #A) ─┐
                                  │                                ├→ P2 Configuration Runtime (PR #B) ─┐
                                  │                                                                     ├→ P3 Configuration Bootstrap (PR #C)
```

### 1.2 Phase ordering (P1 → P2 → P3) の根拠

| 観点 | P1 → P2 → P3 (採択) | P3 → P2 → P1 (却下理由) |
|---|---|---|
| 副作用範囲 | P1 = subprocess のみ / P2 = DB 1 表 / P3 = filesystem + secret。**小→大** で進む | P3 が secret + `.env` filesystem を先行 → ロールバック単位が `.env` 限定で大きい |
| UX 確立 | P1 で「UI = ctl 薄ラッパ」境界の実例がコードに残り、P2/P3 設計の参照点になる | UI shell 不在のまま `.env` write を実装、operator UX 検証が後回し |
| テスト難度 | P1 は dangerous-op block (negative) と subprocess timeout のみで完結、検証コスト最小 | P3 から始めると secret redaction / atomic write 検証を最初に積むことになり pre-commit blocking |
| CLAUDE.md §23 整合 | P1 マージ後 P2 着手、P2 マージ後 P3 着手で PR 依存ゼロ | 同左 (順序の問題ではなく副作用の前倒しが問題) |

### 1.3 単独 merge 可能性 (CLAUDE.md §23)

- **P1 は P2/P3 に依存しない**: P2/P3 の module を import しない。P1 単独で master merge 可能。
- **P2 は P1 merge 後に着手**: P1 の `pages/` 配置パターン (Streamlit native multipage) を参照する。コード依存は無し (import なし) だが、UI 全体の整合性のため順序遵守。
- **P3 は P2 merge 後に着手**: `app_settings_changes` への audit row 書込 helper (P2 で `dashboard_query_service` に追加) を再利用する。これはコード依存。

---

## 2. Phase 1: Operator Console

### 2.1 目的 / 責務

ctl 5 コマンドのうち `emergency-flat-all` を**除く** 4 コマンド (`start` / `stop` / `resume-from-safe-stop` / `run-reconciler`) を Streamlit から subprocess 経由で発火する**薄ラッパ**を提供する。新規 ctl usecase は導入しない。

### 2.2 変更対象ファイル (≤10、想定 6 件)

| 種別 | パス | 役割 |
|---|---|---|
| 新規 | `src/fx_ai_trading/dashboard/pages/1_Operator_Console.py` | Streamlit 標準 multipage 規約に従うページ entry。`pages/` 配下は自動検出されるため `app.py` 改変不要 |
| 新規 | `src/fx_ai_trading/dashboard/operator/__init__.py` | パッケージ marker |
| 新規 | `src/fx_ai_trading/dashboard/operator/ctl_invoker.py` | `subprocess.run([sys.executable, "scripts/ctl.py", ...])` の薄ラッパ。argv 構築 + timeout + 結果整形のみ。`emergency-flat-all` は引数として受け取り得ない型設計 (Literal 型) |
| 新規 | `src/fx_ai_trading/dashboard/operator/preflight.py` | PID file (`logs/supervisor.pid`) 状態を読み取り、各ボタンの enable/disable を計算する純粋関数 |
| 新規 | `tests/unit/test_ctl_invoker_argv.py` | argv 構築の純粋関数テスト |
| 新規 | `tests/contract/test_operator_console_dangerous_ops_block.py` | `emergency-flat-all` が UI button 集合に**現れない**こと、および `ctl_invoker` の Literal 型に含まれないことを検証する negative test |

**意図的に含めないもの**: `app.py` 改変、新規 panel、`safe_stop_journal` viewer (operator_quickstart §3 既存導線で代替)。

### 2.3 完了条件

- [ ] `streamlit run src/fx_ai_trading/dashboard/app.py` で sidebar に `Operator Console` ページが現れる (Streamlit 標準 multipage 動作確認)
- [ ] 4 コマンド (`start` / `stop` / `resume-from-safe-stop` / `run-reconciler`) がそれぞれ UI ボタンから発火し、`subprocess.CompletedProcess.returncode` と stdout/stderr の末尾が UI に表示される
- [ ] `emergency-flat-all` が UI 上のいずれの button / link / form にも現れない (negative test green)
- [ ] `resume-from-safe-stop` の `--reason` 入力が空のときボタンが disable される (validation)
- [ ] subprocess 呼出に timeout (env 変数で設定可、default 30s) があり、超過時は `st.error` を返す
- [ ] PID file 状態に応じて各ボタンの enable/disable が正しく切り替わる (`start` は PID 不在時のみ enable、`stop` は PID 存在時のみ enable)
- [ ] 「`emergency-flat-all` は CLI 専用」の注意書きと正確な CLI コマンド文字列が常時表示される (operator が UI で迷わないため)

### 2.4 テスト戦略

| 種別 | ファイル | 内容 |
|---|---|---|
| unit | `tests/unit/test_ctl_invoker_argv.py` | argv 構築の純粋関数テスト (subprocess なし)、Literal 型に `emergency-flat-all` が含まれないことを mypy/typing で検証 |
| contract | `tests/contract/test_operator_console_dangerous_ops_block.py` | `emergency-flat-all` の UI 露出ゼロを静的に検証 (page module をパースし button label に含まれないこと) |
| UI smoke | (既存 `tests/contract/test_dashboard_panel_contracts.py` を踏襲した新規) | page module が import error なくロードでき、render が呼べる |
| manual | `docs/dashboard_manual_verification.md` 追記 | start → safe_stop 再現 → resume の 3 step walkthrough |

### 2.5 リスク

| # | Risk | Mitigation |
|---|---|---|
| 1 | Streamlit rerun が同一ボタンクリックで subprocess を二重発火 | `st.session_state["operator.last_invocation_id"]` に ULID を書き、同一 ID は no-op で skip。click 後 1.5s ボタン disable |
| 2 | `start` 等の long-running 呼出が UI worker を block | `subprocess.run(timeout=N)` 必須化、`st.spinner` で進捗表示、timeout 時は `st.error` |
| 3 | `--reason` が空文字でも ctl 側で受理されてしまう (UI bypass) | UI 側の validation に加え、ctl 側既存の reason validation を信頼。UI 側で `--reason=""` の argv を構築できない型設計 |

### 2.6 参照

operations §15.1 (4 層責務、Operational 層 = Operator Console 行) / §15.3 (Operator Console の責務境界) / §15.5 (監査ログ) / contracts §2.16 / iteration2_plan §6.14

---

## 3. Phase 2: Configuration Console — Runtime mode

### 3.1 目的 / 責務

稼働中の `app_settings` レイヤ (`runtime mode` 層 = `service_mode` / `runtime_environment` / 各種 feature flag) を**閲覧可、変更は `app_settings_changes` キュー経由のみ**で受け付ける UI を提供する。即時反映は禁止 (再起動 or hot-reload 経由)。`expected_account_type` は **read-only 表示のみ** (operations §11 L145 で UI 経由変更禁止)。

### 3.2 変更対象ファイル (≤10、想定 6 件)

| 種別 | パス | 役割 |
|---|---|---|
| 新規 | `src/fx_ai_trading/dashboard/pages/2_Configuration_Console.py` | Streamlit page entry (Runtime / Bootstrap の 2 タブを内包、Bootstrap タブは P3 で有効化) |
| 新規 | `src/fx_ai_trading/dashboard/config_console/__init__.py` | パッケージ marker |
| 新規 | `src/fx_ai_trading/dashboard/config_console/runtime_view.py` | 表示 + 変更フォームの render |
| 修正 | `src/fx_ai_trading/services/dashboard_query_service.py` | 関数 `enqueue_app_settings_change(engine, *, name, old_value, new_value, changed_by, reason) -> int` を 1 つ追加。`INSERT INTO app_settings_changes (name, old_value, new_value, changed_by, changed_at, reason) VALUES (...)` のみ。**`UPDATE app_settings ...` は書かない** |
| 新規 | `tests/unit/test_enqueue_app_settings_change.py` | SQL 構築 + 6 列充填の純粋テスト |
| 新規 | `tests/integration/test_config_runtime_queue_insert.py` | 実 SQLite (or test DB) に対し insert 成功 + 読み戻し確認、`UPDATE app_settings` が**呼ばれていない**ことの assertion |

### 3.3 完了条件

- [ ] `app_settings` の現在値テーブルが Configuration Console / Runtime タブに表示される (key / value / value_type / last_changed_at / source)
- [ ] 変更要求が `app_settings_changes` 表に **6 列全て** (`name`, `old_value`, `new_value`, `changed_by`, `changed_at`, `reason`) を充填して insert される
- [ ] `expected_account_type` は表示のみで変更フォームが現れない (operations §11 L145 / §15.1 Runtime mode 層の閲覧 = ○ / 変更 = キュー経由) と整合
- [ ] secret 系 key (`OANDA_API_KEY` / `SMTP_PASSWORD` / `SUPABASE_API_KEY` 等の allow-list 対称外) は本タブに**現れない** (Runtime mode 層に属さないため。secret は P3 Bootstrap タブで扱う)
- [ ] 変更送信後に `「キューに登録しました。次の再起動 / hot-reload で反映されます」` 等の文言が必ず表示される (即時反映ではないことの明示、UX Risk #1 への対応)
- [ ] `UPDATE app_settings ...` を直接実行する経路が存在しない (forbidden_patterns で grep 検証)
- [ ] `dashboard_query_service` の関数追加に留まり、新規 module / 新規 Protocol を作らない

### 3.4 テスト戦略

| 種別 | ファイル | 内容 |
|---|---|---|
| unit | `tests/unit/test_enqueue_app_settings_change.py` | 6 列 insert SQL 構築の純粋テスト、`changed_at` が UTC で渡されること |
| integration | `tests/integration/test_config_runtime_queue_insert.py` | 実 DB セッション + insert + 読み戻し、`app_settings` 本体に変更が**入っていない**ことの assertion |
| contract | `tests/contract/test_config_console_no_secret_keys.py` | secret allow-list 外 key が UI render 結果に含まれないこと |
| UI smoke | (既存 panel contract test 踏襲) | page module が import / render エラーなく動く |
| manual | `docs/dashboard_manual_verification.md` 追記 | キュー登録 → 再起動 → 反映確認の walkthrough |

### 3.5 リスク

| # | Risk | Mitigation |
|---|---|---|
| 1 | operator が「Save」と「Apply」を混同 | success toast / button label に「キューに登録 (再起動で反映)」を必ず含める。`Save` / `Apply` 単独表記禁止 |
| 2 | `app_settings_changes` 列名 drift (memory ベースで `key` 等を使うと silent insert 失敗) | schema_catalog §2 #42 の実列名を SQL に literal で書く、unit test で列名一致を検証 |
| 3 | secret allow-list 漏れで Runtime タブに secret が露出 | allow-list は positive list (Runtime mode 層で扱う key を明示列挙) で実装、新規 key 追加時はテスト失敗で気付ける |

### 3.6 参照

operations §15.1 (Runtime mode 層) / §15.2 (Configuration Console 2 モード) / §15.5 / contracts §2.16 / rules §10.3.1 / schema_catalog §2 #42

---

## 4. Phase 3: Configuration Console — Bootstrap mode

### 4.1 目的 / 責務

アプリ未起動時 (`logs/supervisor.pid` 不在) のみ操作可能な `.env` sink を提供する。secret / 接続情報の初期投入 / rotate がこのモードでしか行えないことを契約として保証する。値そのものはログ / DB / session_state に**一切残さない** (rules §10.3.1)。

### 4.2 変更対象ファイル (≤10、想定 7 件)

| 種別 | パス | 役割 |
|---|---|---|
| 修正 | `src/fx_ai_trading/dashboard/pages/2_Configuration_Console.py` | Bootstrap タブを enable (P2 で disabled placeholder として用意済) |
| 新規 | `src/fx_ai_trading/dashboard/config_console/bootstrap_view.py` | Bootstrap render + form。secret 入力は `text_input(type="password")` を `key=` 引数なしで使用 (session_state 自動保持を回避) |
| 新規 | `src/fx_ai_trading/dashboard/config_console/env_writer.py` | `.env` を tmp file → `os.replace()` で atomic 書換。書込前に `ProcessManager().is_running()` を再チェック (race 対策)。値はメソッド内 local 変数のみで参照、return / log に出さない |
| 新規 | `src/fx_ai_trading/dashboard/config_console/env_diff.py` | 旧 `.env` と新 dict から add/remove/change を計算する純粋関数。値は出力せず key 名 + sha256 prefix のみ返す |
| 新規 | `tests/unit/test_env_diff.py` | diff 計算の純粋テスト |
| 新規 | `tests/unit/test_env_writer_atomic.py` | tmp dir 上で atomic write + 中途失敗 (例外 raise) 時の旧 `.env` 維持を検証 |
| 新規 | `tests/contract/test_bootstrap_disabled_when_running.py` | `ProcessManager.is_running() == True` の場合に Bootstrap form が render されないこと |

### 4.3 完了条件

- [ ] `logs/supervisor.pid` 存在時、Bootstrap タブは form を render せず「App is running (PID=N) — stop the app to edit `.env`」と表示する (read-only モード)
- [ ] `logs/supervisor.pid` 不在時のみ form が render される
- [ ] `.env` 書込は tmp file → `os.replace()` の 2 段階 atomic 経路のみを通る (forbidden_patterns で `open(".env", "w")` 直接呼出禁止)
- [ ] 書込直前 (rename 直前) に `ProcessManager().is_running()` を再チェックし、True ならば書込中止 + `st.error` を返す (race 対策)
- [ ] `app_settings_changes` への audit row には `name` (key 名) / `old_value` (旧 sha256 prefix 8 文字) / `new_value` (新 sha256 prefix 8 文字) / `changed_by` / `changed_at` / `reason` のみ書く。**平文 secret は `old_value` / `new_value` に書かない** (rules §10.3.1 / operations §15.4)
- [ ] secret 値が `st.session_state` に残らない (`text_input` の `key=` 引数を使わない、callback 内で即時消費)
- [ ] secret 値が log に出ない (`LogSanitizer` 経由 + `env_writer` 内で値を含む log 文字列を生成しない)

### 4.4 テスト戦略

| 種別 | ファイル | 内容 |
|---|---|---|
| unit | `tests/unit/test_env_diff.py` | diff 計算純粋テスト、出力に値が含まれないこと |
| unit | `tests/unit/test_env_writer_atomic.py` | tmp dir で write 中途 raise → 旧 `.env` が無傷 / `os.replace` 経路を通ること |
| integration | `tests/integration/test_bootstrap_env_write.py` | tmp `.env` への actual write + permissions + audit row insert 確認 |
| contract | `tests/contract/test_bootstrap_disabled_when_running.py` | PID file 存在シナリオで form render なし |
| contract | `tests/contract/test_bootstrap_no_plaintext_log.py` | env_writer 経路の log capture 内に input 値が現れないこと (sanitizer 検証) |
| manual | `docs/dashboard_manual_verification.md` 追記 | secret 入力 → diff preview → 書込 → 再起動 walkthrough |

### 4.5 リスク

| # | Risk | Mitigation |
|---|---|---|
| 1 | `.env` write race (operator 別タブで `start` 実行 → write 中に PID 出現) | render 時 PID check に加え、`os.replace` 直前にも再チェック。race 検出時は write 中止 + 明示的エラー |
| 2 | Streamlit `text_input` の自動 session_state 保持で secret 値が残る | `key=` 引数なしで render。callback 内で local 変数のみ参照、即時消費後参照しない |
| 3 | `os.replace` の Windows 上 atomicity (異 filesystem 跨ぎで非 atomic) | tmp file は `.env` と同 dir (= 同 filesystem) に作成。manual checklist にも明記 |
| 4 | secret 値が例外メッセージに乗る (例: `ValueError(f"invalid value: {value}")`) | env_writer 内で例外は値を含まない一般的メッセージのみ。`LogSanitizer` 経由化 |

### 4.6 参照

operations §15.1 (Secret 層 / Runtime 接続層) / §15.2 (Bootstrap モード) / §15.4 (UI 経由 secret 入力カタログ) / contracts §2.16 / rules §10.3.1 / schema_catalog §2 #42

---

## 5. Phase 8 送り catalog (Iter3 では実装しない)

下記は M26 仕様凍結 (operations §15.6) で明示された Phase 8 送り境界。Iter3 の P1-P3 実装中にこれらを**先行実装してはならない** (CLAUDE.md §11 自己拡張禁止)。

| # | 機能 | Phase 8 該当節 |
|---|---|---|
| 1 | SSO / OAuth / SAML 認証 | phase8 §2.3, §5.3 |
| 2 | multi-user / role 分離 (viewer / operator / admin) | phase8 §2.3, §5.3 |
| 3 | RBAC / per-key 権限制御 | phase8 §5.3 |
| 4 | Web UI 刷新 (Next.js + FastAPI / React) | phase8 §2.3, §4.3 |
| 5 | HTTP API 経由の operator 操作 (`dashboard_query_service` B 形態) | phase8 §4.3 |
| 6 | `dashboard_operations_audit` (仮称) テーブル新設 | operations §15.5, phase8 §5.3 |
| 7 | `SecretProvider` 書込 Interface (`rotate` / `set` 等) の D3 追加 | operations §15.6, contracts §2.16 |
| 8 | Slack 双方向コマンド (`/fx-ai-trading flat-all` 等) | phase8 §2.2, §5.2 |
| 9 | `emergency-flat-all` の UI ボタン化 (4 重防御の解除) | operations §15.1, phase6 §6.18 |
| 10 | `.env` rotation 自動化 / secret encryption at rest | (将来検討) |
| 11 | DR 訓練 GUI / 月次リハーサル automation | phase8 §2.4, §5.4 |
| 12 | 税務エクスポート GUI | phase8 §2.5, §5.5 |

---

## 6. 横断リスク

| # | Risk | Mitigation |
|---|---|---|
| 1 | Cross-Phase scope creep (P1 のついでに config も触る) | 各 Phase の「変更対象ファイル」表に**ない**ファイルが PR diff に現れたら Evaluator No-Go |
| 2 | 既存 panel への副作用 (Streamlit page 追加で navigation 順序が崩れる) | page file の数字 prefix (`1_` / `2_`) で順序固定、既存 panel は touch しない |
| 3 | M26 spec 凍結 docs と実装の drift | 各 Phase 完了時に operations §15 / contracts §2.16 / rules §10.3.1 / iteration2_plan §6.14 と diff を取り、Evaluator が cross-reference 整合を確認 |
| 4 | Streamlit version 依存 (multipage 規約は古い version で挙動差) | `pyproject.toml` の streamlit 版を fix、CI で `streamlit run --help` の sanity check |

---

## 7. Cross-reference 一覧 (本書 ↔ 凍結仕様)

| 本書 | 凍結 docs |
|---|---|
| §0 前提 | iteration2_plan §6.14 / operations §15 / contracts §2.16 / rules §10.3.1 / design 付録 #7 |
| §2 Phase 1 | operations §15.1 (Operator Console 行) / §15.3 / §15.5 / contracts §2.16 (新規 ctl usecase 不導入) |
| §3 Phase 2 | operations §15.1 (Runtime mode 層) / §15.2 (稼働中モード) / contracts §2.16 (即時反映禁止) / schema_catalog §2 #42 |
| §4 Phase 3 | operations §15.1 (Secret / Runtime 接続層) / §15.2 (起動前モード) / §15.4 / rules §10.3.1 / contracts §2.16 (secret sink = `.env` のみ) |
| §5 Phase 8 送り | operations §15.6 / phase8 §2.3 / §5.3 / contracts §2.16 |

---

## 7.5 実装ループ制御 (Implementation Loop Control)

M26 の各 Phase (P1 / P2 / P3) は、**1 Phase = 1 cycle = 1 PR = 1責務** で進行する。
各 Phase は必ずサブエージェントの改善ループを経てから PR 作成可否を判定する。

### 7.5.1 共通原則

* 各 Phase は **最低 2 ループ、最大 4 ループ** 実施する
* Evaluator が Go を出すまで merge に進まない
* 1 ループ内でスコープを広げない
* 次 Phase は **前 Phase の master merge 完了後** にのみ着手する
* Phase 8 送り catalog (§5) にある機能は、どのループでも実装対象に含めない
* M26 凍結 4 docs

  * `operations.md` §15
  * `implementation_contracts.md` §2.16
  * `development_rules.md` §10.3.1
  * `iteration2_implementation_plan.md` §6.14
    を変更前提にしない

### 7.5.2 サブエージェント構成

#### Orchestrator

* 当該 Phase のスコープ固定
* ループ継続 / 終了判断
* 次 Phase 進行条件の判定
* 「今回やること / やらないこと」の維持

#### UI Implementation Designer

* 当該 Phase の実装方針の詳細化
* 変更対象ファイルと責務境界の確認
* 既存 docs / contracts / runbook との整合確認
* Loop 2 以降では前回指摘の反映責任を持つ

#### Developer

* 実装担当
* 差分最小でコード / test / docs を更新
* 無関係変更を混ぜない
* manual verification に必要な追記のみ許可

#### Evaluator

* Blocker / Major / Minor / Observation を分類
* 当該 Phase の完了条件充足を判定
* Go / No-Go を明示
* No-Go の場合、必ず未解決項目を次ループ入力に落とす

### 7.5.3 ループ構造

#### Loop 1（初回実装）

1. Orchestrator が当該 Phase の対象・非対象を明示
2. UI Implementation Designer が実装方針を提示
3. Developer が初回実装を行う
4. Evaluator が初回レビューを行う

#### Loop 2（改善）

5. UI Implementation Designer が指摘事項を反映した修正版方針を提示
6. Developer が修正を行う
7. Evaluator が再評価する

#### Loop 3+（必要時）

8. Orchestrator が未解決事項のみを再整理
9. UI Implementation Designer / Developer が追加修正
10. Evaluator が最終判定

### 7.5.4 共通 Go / No-Go 基準

各 Phase は以下をすべて満たした場合のみ Go とする。

* Blocker = 0
* Major = 0
* 当該 Phase の完了条件をすべて満たす
* 当該 Phase のテスト戦略に定義された検証が完了している
* 既存 docs / contracts / runbook と整合している
* Phase 8 送りの機能を前倒ししていない
* PR が 1責務に収まっている

以下のいずれかに該当する場合は No-Go とする。

* danger operation が UI に露出する
* secret が `.env` 以外へ書き込まれる
* `app_settings` 本体を Runtime から直接更新する
* `dashboard_query_service` の責務を逸脱する
* 新規 Protocol / 新規 usecase / 新規 API を勝手に導入する
* 前 Phase の未解決事項を抱えたまま次 Phase に進もうとする

### 7.5.5 Phase ゲート条件

#### P1 → P2 ゲート

P2 に進む前に、以下を満たすこと。

* Operator Console が 4 コマンドのみを正しくラップしている
* `emergency-flat-all` が UI に一切露出していない
* subprocess 実行が timeout / duplicate click / validation を含めて安定している
* `dashboard_manual_verification.md` に P1 walkthrough が追記されている
* Evaluator Go

#### P2 → P3 ゲート

P3 に進む前に、以下を満たすこと。

* `app_settings_changes` への 6 列 insert が正しい
* Runtime から `app_settings` 本体へ直接更新する経路がない
* secret 系 key が Runtime タブに露出していない
* キュー登録後の UX 文言が「再起動 / hot-reload 待ち」で統一されている
* `dashboard_manual_verification.md` に P2 walkthrough が追記されている
* Evaluator Go

#### P3 完了ゲート

M26 全体完了前に、以下を満たすこと。

* Bootstrap タブは PID file 存在時に必ず無効化される
* `.env` 書込が atomic write のみで実行される
* 平文 secret が log / DB / session_state に残らない
* audit row は hash prefix のみを保持し、平文を保持しない
* `dashboard_manual_verification.md` に P3 walkthrough が追記されている
* Evaluator Go

### 7.5.6 各ループの出力形式

各 Phase / 各ループで、以下の形式を維持する。

#### Orchestrator Start

* 対象 Phase
* 今回やること
* 今回やらないこと
* 現在ループ番号

#### UI Implementation Designer

* 実装方針
* 変更対象
* 依存関係
* リスク
* 前回からの改善点（Loop 2 以降必須）

#### Developer

* 実装内容
* 変更ファイル
* 差分要約
* 実行した test / manual check

#### Evaluator

* Blocker / Major / Minor / Observation
* Go / No-Go
* 根拠
* 次ループで潰すべき項目

#### Orchestrator Decision

* 次ループへ進むか
* PR 作成へ進むか
* 次 Phase へ進めるか

### 7.5.7 Phase 終了時の記録

各 Phase 完了時は必ず以下を記録する。

* 完了した責務
* 変更ファイル一覧
* 実施した test / manual verification
* Evaluator 最終判定
* 次 Phase の開始条件が満たされているか

---

## 7.6 実装順序の固定

M26 実装は以下の順序でのみ進行する。

1. **P1: Operator Console**
2. **P2: Configuration Console Runtime**
3. **P3: Configuration Console Bootstrap**

順序変更は禁止。
P2 / P3 を前倒ししない理由は `§1.2 Phase ordering` を正本とする。

---

## 8. 完了の判断 (Iter3 全体)

P1 / P2 / P3 が全て master merge されたとき、本計画は完了する。完了条件:

- [ ] 3 PR が順次 squash merge されている
- [ ] M26 凍結 4 docs (operations §15 / contracts §2.16 / rules §10.3.1 / iteration2_plan §6.14) の文言は変更されていない (実装が仕様に従う方向)
- [ ] dashboard_manual_verification.md に P1 / P2 / P3 の walkthrough が追記されている
- [ ] Phase 8 送り catalog (§5) の 12 項目はいずれも実装されていない
