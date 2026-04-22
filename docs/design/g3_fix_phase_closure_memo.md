# Design Memo — G-3 Fix Phase Closure

> **ステータス**: 確定 (closure record). 本メモは G-3 Fix Phase の実施範囲・解消状況・defer 判断を永続化するための真値資料である。
> **作成契機**: G-3 audit (2026-04-22) で検出された 15 件のリスクに対し、PR-β (#118) で設計を確定し PR-1〜PR-4 (#119/#120/#121/#122) を逐次マージした後、live 化前残課題を最終整理する目的で作成。
> **重要**: 本メモは新規実装提案を含まない。マージ済み PR と未着手項目の対応・分類のみを記録する。
> **関連メモ**: `docs/design/g3_notifier_fix_plan.md` (PR-β / 設計の真値) / `docs/design/g2_fix_phase_memo.md` (直前フェーズの closure 様式)。

---

## 1. 目的 / スコープ

- **目的**:
  - G-3 audit で検出された 15 件のリスク (R-1 Critical / R-2-3 High / R-4-15 Medium-Low) のうち、本 Fix Phase で実施した範囲を確定する
  - マージ済み PR (#118 / #119 / #120 / #121 / #122) と監査 ID (R-1〜R-15) / 設計契約 (C-1〜C-10) の対応表を真値として固定する
  - live 化前必須の残課題を「最小限」に絞り、defer 項目を明文化してスコープドリフトを防ぐ
  - 現時点の notifier runtime の実態 (file-only safe + Slack opt-in + Email 未活性) を operator/oncall 向けに明文化する
- **スコープ**:
  - G-3 Fix Phase Designer Freeze (PR-β #118) の総括
  - PR-1〜PR-4 で解消したリスクと、明示的に defer したリスクの分類確定
  - live 化判定 (本 Fix Phase 単独で notifier 観点 GO/NO-GO は出さず、判定材料の整理のみ)
- **非スコープ**:
  - 新規 Issue / 新規 audit の追加 (本 Fix Phase 完了後に独立して実施)
  - Email チャネルの本活性化 (本 Closure 段階では明示 defer。`notifier_factory` PR-1 ハードガード維持)
  - M8/M9 実装計画の詳細化 (G-3 由来の M8 defer 項目は §5 で先に固定)

---

## 2. G-3 Audit 結果サマリ (2026-04-22 監査)

**結論**: **FAIL** — 多チャネル通知の dispatcher (`NotifierDispatcherImpl`) と SlackNotifier / EmailNotifier が production code から呼ばれておらず、`safe_stop` step 3 の通知は実質 `FileNotifier` への file 書込 1 経路のみ。さらに supervisor process そのものが起動できない (`__main__` 不在)。

### 検出された 15 リスク (R-1〜R-15)

| ID | severity | 内容 | 出典 |
|---|---|---|---|
| **R-1** | Critical | `NotifierDispatcherImpl` / `SlackNotifier` / `EmailNotifier` の production 呼出 = 0、`supervisor/__main__.py` 不在 | `grep -rn "NotifierDispatcherImpl(" src` → 0 hit |
| **R-2** | High | `EmailNotifier` SMTP timeout 無し → ハング時 step 3 が無限ブロック → step 4 (DB record) 未到達 | `adapters/notifier/email.py` |
| **R-3** | High | `EmailNotifier` 3 回 retry に backoff 無し / 上限秒数なし → R-2 を増幅 | 同上 |
| R-4 | Medium | dispatcher が `FileNotifier` の `NotifyResult` を見ていない (file 失敗が silent) | `adapters/notifier/dispatcher.py` |
| R-5 | Medium | dispatcher が channel 別結果を返さず → `_safe_stop_completed` が虚偽 True になりうる | `supervisor/safe_stop.py:_fire_step3_notifier` |
| R-6 | Medium | Slack/Email の credential / config 読込が production code に無い → R-1 解消後も externals=[] で起動 | `notifier_factory` 不在 |
| R-7 | Medium | SlackNotifier の HTTP 200 意味的失敗 / except 句冗長 | `adapters/notifier/slack.py` |
| R-8 | Medium | ctl emergency-flat-all が dispatcher を経由しない | `scripts/ctl.py` (G-2 U-9 と重複) |
| R-9 | Medium | SafeStopJournal cross-process 競合 | `supervisor/safe_stop_journal.py` |
| R-10 | Low | SafeStopJournal `read_all` が破損行 silent skip | 同上 |
| R-11 | Low | ctl の SafeStopJournal.append が try/except 無し | `scripts/ctl.py` |
| **R-12** | High | Notifier channel の health probe が startup 16 step に無い → 設定ミスは safe_stop 発火時まで気付けない | `supervisor/startup.py:_step15_health_check` |
| R-13 | Low | `dispatch_via_outbox` が file-only stub | `adapters/notifier/dispatcher.py` |
| R-14 | Low | SlackNotifier の payload formatter (formatting only) | `adapters/notifier/slack.py` |
| R-15 | Low | fan-out 順序と blocker の不整合 | `adapters/notifier/dispatcher.py` |

### 設計判断 (PR-β / 設計メモ §2)

- R-1 が本質、R-2/R-3/R-6/R-12 は R-1 解消と同時/直後に live を脅かす派生リスク。
- 「R-1 を単独で解消する PR」は禁止。R-1 → R-2/R-3 → R-4/R-5 → R-12 をこの順で 4 PR に分割し、precondition で守る (PR-1 単独 merge 禁止 → PR-2 同時 open + 即 merge 必須)。

---

## 3. PR ↔ リスク ID / 契約対応表 (真値)

本 Fix Phase でマージ済みの 5 PR と監査リスク (R-*) / 設計契約 (C-*) の対応を以下に固定する。**本表が真値であり、commit message のラベルは書き換えない**。

| PR # | merge SHA | branch | 責務 | 解消した R-* | pin した C-* |
|---|---|---|---|---|---|
| **#118** (PR-β) | `b567f2a` | `docs/g3-notifier-fix-plan` | docs-only — 設計 memo `docs/design/g3_notifier_fix_plan.md` 確定 | (設計確定のみ) | C-1〜C-10 を初稿で導入 |
| **#119** (PR-1) | `ea7c054` | `fix/g3-pr1-notifier-factory` | `notifier_factory` 新設 + `supervisor/__main__.py` 新設 + dispatcher を Supervisor へ注入 (file-only safe) | **R-1** / R-6 (Slack 部分) | **C-1** / **C-10** / **C-9** (file-only fallback) |
| **#120** (PR-2) | `b0cf9e1` | `fix/g3-pr2-email-timeout` | `EmailNotifier` に `connect_timeout_s=10`、`_MAX_RETRY` を 3→2 に削減 (`email.py` のみ) | **R-2** / **R-3** / R-15 | **C-2** / C-9 |
| **#121** (PR-3) | `f28fcf9` | `fix/g3-pr3-dispatch-result` | `DispatchResult` dataclass 導入 + `_fire_step3_notifier` を file 配送成功にバインド | **R-4** / **R-5** | **C-4** / **C-5** |
| **#122** (PR-4) | `0ac15ef` | `fix/g3-pr4-health-probe` | startup step 15 に Slack DNS+TCP / SMTP TCP 接続 health probe 追加 (degraded only) | **R-12** | **C-6** |

### Designer Freeze 4 PR 計画と実施状況

PR-β (#118) で立てた 4 実装 PR 計画はすべてオリジナル順序で実施済:

| 元計画 | 内容 | 実施 PR | 状態 | 実装上のずれ |
|---|---|---|---|---|
| PR-1 | NotifierDispatcher 配線 + `__main__` 新設 + 設定不在縮退 | #119 | ✅ merged | factory は ConfigProvider ではなく **環境変数のみ** (`SLACK_WEBHOOK_URL`) を使用。Email は **ハードガード** (factory 内で `email_notifier=None` 固定)。 |
| PR-2 | Email timeout / retry 削減 | #120 | ✅ merged | `email.py` 単体改修のみ。factory への接続 (Email channel 活性化) は意図的に未実施 (§4 / §5 参照)。 |
| PR-3 | DispatchResult 導入 + step 3 判定 | #121 | ✅ merged | `getattr(result, "file_success", True)` で旧 mock 後方互換性を維持。external/email leg 失敗は step 3 bool に流さない (C-5)。 |
| PR-4 | health probe 追加 | #122 | ✅ merged | `SMTP_HOST` / `SMTP_PORT` 環境変数を probe-only で読込。Email channel 活性化は伴わない (PR-1 ハードガード維持)。 |

---

## 4. 解消済み / 未解消の整理

### 4.1 解消済 (本 Fix Phase で close)

| R-* | 解消 PR | 確認方法 |
|---|---|---|
| **R-1** | #119 | `python -m fx_ai_trading.supervisor` が exit 0 で起動 / `dispatcher = ctx.notifier` が `NotifierDispatcherImpl` インスタンス |
| **R-2** | #120 | `EmailNotifier.send` が wall-clock 30 秒以内に必ず戻る (contract test) |
| **R-3** | #120 | `_MAX_RETRY=2` の固定値、backoff 無し |
| **R-4** | #121 | `dispatcher` が `DispatchResult.file: NotifyResult` を返し `file_success` プロパティで露出 |
| **R-5** | #121 | `_fire_step3_notifier` が `getattr(result, "file_success", True)` で判定 → `_safe_stop_completed` ⇔ file 配送成功 |
| **R-12** | #122 | step 15 で Slack/SMTP probe 失敗時 `result.outcome=="degraded"` / `15 in result.degraded_steps` (StartupError は raise しない) |
| R-15 | #120 (実質) | Email retry 上限が 2 に削減され、fan-out 順序の最終 leg ブロック上限が確定 (30s) |

### 4.2 部分解消 (条件付き)

| R-* | 状態 | 内容 |
|---|---|---|
| **R-6** (config 読込) | **Slack のみ解消** | factory が `SLACK_WEBHOOK_URL` 環境変数を読込 (PR-1)。Email config (host/port/sender/recipients/auth) は **未実装** (Email channel 自体が未活性のため). PR-4 の `SMTP_HOST/PORT` は probe-only で channel 活性化を伴わない。 |

### 4.3 未解消 (明示 defer)

| R-* | severity | defer 先 | 理由 |
|---|---|---|---|
| R-7 | Medium | **Iter 2 後半 / 別 phase** | SlackNotifier の HTTP 200 意味的失敗 (Slack 側が JSON で `ok=false` を返すケース)。SafeStop の真値性は file 配送に bind 済 (C-4) のため live を直接脅かさない。 |
| R-8 | Medium | **G-2 U-9 で解消済 (#117)** | ctl emergency-flat-all → safe_stop 配線は G-2 PR-α (`#117`) で完了。dispatcher 経由化自体は今後 emergency-flat 設計と一緒に再評価。 |
| R-9 | Medium | **別 Fix Phase (Journal 整合 phase)** | SafeStopJournal cross-process 競合は notifier 設計と直交。G-3 scope 外。 |
| R-10 | Low | 同上 | `read_all` 破損行 silent skip は R-9 と一緒に扱う。 |
| R-11 | Low | **後続 backlog** | ctl の `SafeStopJournal.append` try/except 化。G-2 U-9 解消で実害は縮小。 |
| R-13 | Low | **M8** | `dispatch_via_outbox` の本実装は `notification_outbox` 表 + OutboxProcessor 接続が前提 (G-2 §5 deferral と同じ defer 先)。 |
| R-14 | Low | **後続 backlog** | SlackNotifier の payload formatter は表現の問題で safe_stop 真値性に無影響。 |

---

## 5. 現時点の Notifier Runtime 実態

operator/oncall が運用判断するための「2026-04-22 master tip `0ac15ef` 時点の真値」を以下に固定する。

### 5.1 production wiring (`supervisor/__main__.py` → `notifier_factory.build_notifier_dispatcher`)

```
NotifierDispatcherImpl
├─ file        : FileNotifier(log_path=logs/notifications.jsonl)   [常時, P-2 last-resort]
├─ externals   : [SlackNotifier(...)] if SLACK_WEBHOOK_URL else []  [opt-in]
└─ email       : None                                               [hard-disabled, PR-1 guard]
```

### 5.2 環境変数 (G-3 Fix Phase で追加 / 既存)

| 環境変数 | PR | 用途 | 不在時挙動 |
|---|---|---|---|
| `SLACK_WEBHOOK_URL` | #119 | SlackNotifier instantiate + step 15 Slack probe | externals=[] / probe skip |
| `SMTP_HOST` | #122 | step 15 SMTP probe **のみ** (channel 活性化はしない) | probe skip |
| `SMTP_PORT` | #122 | step 15 SMTP probe **のみ** (非数値は WARNING + `None` 化) | probe skip |

### 5.3 SafeStop step 3 の真値性 (C-4 / C-5)

| シナリオ | `_safe_stop_completed` |
|---|---|
| File OK / Slack OK / Email N/A | **True** |
| File OK / Slack 失敗 / Email N/A | **True** (WARN log)、operator は `logs/notifications.jsonl` を真値ソースとして読む |
| File 失敗 / Slack OK / Email N/A | **False** (last-resort 喪失は深刻、retry 余地あり) |
| File 失敗 / Slack 失敗 / Email N/A | **False** (同上) |

### 5.4 startup step 15 の振る舞い (C-6)

| 条件 | startup outcome | `15 in degraded_steps` |
|---|---|---|
| DB OK / Slack/SMTP probe 未設定 | `ready` | False |
| DB OK / Slack probe 成功 | `ready` | False |
| DB OK / Slack probe DNS 失敗 | `degraded` | True (StartupError は raise しない) |
| DB OK / Slack probe TCP 失敗 | `degraded` | True |
| DB OK / SMTP probe TCP 失敗 | `degraded` | True |
| DB 失敗 | (raise `StartupError(15)`) | — |

### 5.5 SafeStop wall-clock budget (C-3 / C-9)

```
SafeStopHandler.fire wall-clock ≤ ~60s (step 3 = 30s 上限 + 他 step)
  step 1 journal append   : ~immediate (fsync)
  step 2 loop stop        : ~immediate (in-memory flag)
  step 3 dispatcher       : ≤ 30s budget
    ├─ File   : ~immediate (fsync)
    ├─ Slack  : ≤ 5s (timeout 既存)
    └─ Email  : N/A (channel 未活性)        [将来 PR で活性化されたら 10s × (1+2 retry) = 30s]
  step 4 DB record        : ~immediate (Postgres SELECT)
```

---

## 6. Live 前必須かどうかの判定

本 Fix Phase 単独で「notifier 観点 live GO」は出さない。以下を判定材料として固定する。

### 6.1 live 前 must-resolve (本 Fix Phase scope 内では「無し」)

本 Fix Phase の 4 実装 PR で以下が確立済のため、**notifier 経路に live blocker は無い**:
- safe_stop 通知が file (last-resort) と Slack (opt-in) で多重化されている (C-4 / C-10)
- safe_stop シーケンスが 60 秒以内に必ず戻る (C-3 / C-9 / Email 未活性により実態はさらに短い)
- 設定ミス (Slack URL DNS 失敗 / SMTP 到達不能) が起動時に degraded で可視化される (C-6)
- 起動できない (`ModuleNotFoundError`) という R-1 の元症状が解消済

### 6.2 live 前推奨 (本 Fix Phase scope 外、operator 判断項目)

| 項目 | 推奨理由 | 担当 |
|---|---|---|
| Slack webhook URL の払出 + `SLACK_WEBHOOK_URL` 設定 | externals=[] で起動すると oncall が file 監視必須となり Toil 増 | operator / infra |
| `logs/notifications.jsonl` / `logs/safe_stop.jsonl` の監視配線 | P-2 file-only fallback の真値ソース。Slack 不達時の唯一の通知経路 | operator / observability team |
| step 15 health probe (Slack DNS / SMTP TCP) の WARNING を起動ログ監視に組込む | C-6 の degraded 通知を operator が見落とさない | operator |

### 6.3 live 後の優先 backlog (本 Fix Phase scope 外)

| 項目 | 優先度 | defer 先 |
|---|---|---|
| Email channel 活性化 (factory の Email ハードガード解除) | Medium | 別 PR (本 Closure 後に operator が SMTP 設定を要求した時点で再評価) |
| R-7 (Slack HTTP 200 意味的失敗) | Low | Iter 2 後半 |
| R-9/R-10 (SafeStopJournal cross-process) | Medium | 別 Fix Phase (Journal 整合) |
| R-13 (`dispatch_via_outbox` 本実装) | Medium | M8 (OutboxProcessor 着手と同時) |

---

## 7. Deferral 一覧 (集約)

§4.3 / §6.3 を統合した defer 一覧。各項目の defer 先と理由を本表で固定する。

| ID | 内容 | Defer 先 | 理由 |
|---|---|---|---|
| **Email channel 活性化** | factory での `EmailNotifier` instantiate / 設定スキーマ (host/port/sender/recipients/auth) 読込 | **別 PR** (operator 要求時) | PR-2 (#120) で `EmailNotifier` 単体は安全化済。channel 活性化を伴わなかった理由は (a) 現状 oncall への通知は Slack で十分 / (b) SMTP 設定の払出が operator 判断 / (c) Email 未活性のままでも C-3/C-4/C-9/C-10 はすべて満たされる、の 3 点。 |
| **R-6** (Email config 読込) | 同上 | 同上 | Email 活性化と同時に解消する性質のため一括 defer。 |
| **R-7** (Slack HTTP 200 意味的失敗) | **Iter 2 後半** | safe_stop 真値性は file 配送に bind 済 (C-4) のため live blocker ではない。 |
| **R-8** (ctl emergency-flat-all → dispatcher) | **G-2 U-9 で解消済 (#117)** | safe_stop 配線そのものは完了。dispatcher 直接経由化は今後の emergency-flat 設計で再評価。 |
| **R-9** (SafeStopJournal cross-process 競合) | **別 Fix Phase (Journal 整合 phase)** | notifier 設計と直交。G-3 scope 外。 |
| **R-10** (`read_all` 破損行 silent skip) | 同上 | R-9 と一緒。 |
| **R-11** (ctl `SafeStopJournal.append` try/except) | **後続 backlog** | G-2 U-9 解消で実害縮小。本フェーズ scope 外。 |
| **R-13** (`dispatch_via_outbox` 本実装) | **M8** (OutboxProcessor / `notification_outbox` 表着手時) | C-8 で「G-3 では変更しない」を明示固定済。 |
| **R-14** (Slack payload formatter) | **後続 backlog** | 表現の問題で safe_stop 真値性に無影響。 |
| **G-3 Fix Phase 全体の Closure 化** | (本メモ) | G-3 audit リスク 15 件の処理状況をここで真値固定 |

---

## 8. SafeStop 優先 / file-only fallback の原則 再確認

本 Closure 段階で以下 2 原則を **再確認・永続化** する。設計メモ `g3_notifier_fix_plan.md` §3.0 P-1 / P-2 の文言と同等。

### 8.1 P-1 SafeStop 優先ルール (再掲)

**外部通知 (Slack / Email / 将来の追加チャネル) によって SafeStop シーケンスがブロックされてはならない。**

本 Fix Phase で確立した実装上の保証:
- `EmailNotifier` の `connect_timeout_s=10` + `_MAX_RETRY=2` (#120) → step 3 wall-clock ≤ 30s
- `_fire_step3_notifier` の bool は `DispatchResult.file_success` のみで判定 (#121) → external/email leg の失敗は step 3 を blocking させない
- `_step15_health_check` の probe failure は `_mark_step_degraded(15)` のみ呼出 (#122) → 起動を blocking しない
- 並列 fan-out は採用していない (`adapters/notifier/dispatcher.py`)

### 8.2 P-2 file-only fallback (再掲)

**`FileNotifier` (= `logs/notifications.jsonl` への fsync 書込) は配信経路の last-resort として常に必須であり、外部チャネルはベストエフォートである。**

本 Fix Phase で確立した実装上の保証:
- `notifier_factory.build_notifier_dispatcher` の `file_notifier` は **required** (PR-1 / `__main__.py` で常時 instantiate)
- 設定不在のチャネル (Slack URL 未設定 / Email channel そのもの) は silent skip + WARNING ログのみで起動継続 (C-1)
- `_safe_stop_completed=True` ⇔ file 配送成功 (C-4) — 外部通知の成否は safe_stop 完了の真値性に持ち込まない
- operator runbook は `logs/notifications.jsonl` を真値ソースとして読む運用 (本 Closure §5.2 / §6.2 で再確認)

### 8.3 反例 (本フェーズで明示的に採用しなかった選択肢)

- step 3 を「全チャネル成功」で判定する → P-1 違反
- external notifier の例外を `SafeStopHandler` まで伝播させる → P-1 違反
- Email retry に unbounded backoff を入れる → P-1 違反 (PR-2 で 2 回上限固定)
- `FileNotifier` を optional にする → P-2 違反 (factory で required 維持)
- 外部チャネル全失敗で起動を停止する → P-2 違反 (step 15 は degraded 止まり)

---

## 9. 次フェーズ候補 (任意 / scope 拡張ではない)

本 Closure memo の merge をもって G-3 Fix Phase は **クローズ**。次フェーズの候補を以下に挙げるが、本メモはどれかを「確定」させない (operator / 設計判断で選択)。

| 候補 | 起点 | scope の概形 | 依存 |
|---|---|---|---|
| **Email channel 活性化** | 本 Closure §7 | factory で `EmailNotifier` instantiate + 設定スキーマ読込 + integration test | operator が SMTP 設定を払出すこと |
| **Journal 整合 Fix Phase** | R-9 / R-10 | SafeStopJournal cross-process lock / 破損行ハンドリング | なし |
| **M8 (OutboxProcessor + notification_outbox)** | R-13 / G-2 §5 deferral | `notification_outbox` 表 + OutboxProcessor 接続 + `dispatch_via_outbox` 本実装 + R-13/U-2/U-4 を 1 PR 化 | M8 マイルストーン着手 |
| **emergency-flat-all → dispatcher 直接経由** | R-8 (G-2 U-9 補強) | `scripts/ctl.py` の dispatcher 経由化 | G-3 PR-1 (#119) の dispatcher 配線 |

---

## 10. クローズ条件 (本フェーズ)

G-3 Fix Phase は以下 5 PR がすべて merge された時点で **クローズ**:

1. **PR-β** (#118) — 設計確定 → ✅ merged `b567f2a`
2. **PR-1** (#119) — dispatcher 配線 → ✅ merged `ea7c054`
3. **PR-2** (#120) — Email timeout / retry → ✅ merged `b0cf9e1`
4. **PR-3** (#121) — DispatchResult / step 3 判定 → ✅ merged `f28fcf9`
5. **PR-4** (#122) — health probe → ✅ merged `0ac15ef`

→ **本 Closure memo の merge をもって G-3 Fix Phase クローズ** (master tip 想定: 本メモ merge 直後)。

---

## 11. 関連資料

- `docs/design/g3_notifier_fix_plan.md` — G-3 Fix Phase 設計メモ (PR-β / 真値 §3.0 P-1/P-2 / §5 C-1〜C-10)
- `docs/design/g2_fix_phase_memo.md` — G-2 Fix Phase Closure memo (本メモの様式の参考元)
- `docs/design/safety_verification_gaps_memo.md` — Cycle 6.12 の verification gap memo (G-1/G-2/G-3 の起点)
- `docs/phase6_hardening.md §6.13` — 通知 two-path dispatch 契約
- `docs/operations.md §F14` — operator runbook (safe_stop reason 一覧)
- `src/fx_ai_trading/supervisor/notifier_factory.py` — production wiring (#119)
- `src/fx_ai_trading/supervisor/__main__.py` — Supervisor entry point (#119 / #122)
- `src/fx_ai_trading/adapters/notifier/email.py` — `EmailNotifier` timeout / retry (#120)
- `src/fx_ai_trading/adapters/notifier/dispatcher.py` — `NotifierDispatcherImpl` + `DispatchResult` (#121)
- `src/fx_ai_trading/domain/notifier.py` — `DispatchResult` dataclass (#121)
- `src/fx_ai_trading/supervisor/safe_stop.py` — `_fire_step3_notifier` file-bound 判定 (#121)
- `src/fx_ai_trading/supervisor/health.py` — `NotifierProbeResult` / `probe_slack_webhook` / `probe_smtp_connection` (#122)
- `src/fx_ai_trading/supervisor/startup.py` — `_step15_health_check` + `_probe_external_notifiers` (#122)

---

## 12. 非対象 (本メモで決めないこと)

- **新規 Issue / 新規 audit の追加** — 本 Closure memo は確定済みの G-3 audit 結果と PR 実施状況の真値化のみを担う
- **Email channel 活性化の実装詳細** — §7 / §9 で defer 判断のみ固定。実装着手は別 PR の commit / PR description で行う
- **次フェーズの確定** — §9 の候補一覧は判断材料であり、選択は operator / 設計判断
- **commit message の書き換え** — 不可逆かつ master tip 保護のため、本 §3 の対応表を真値として永続化する方針 (G-2 closure memo §8 と同方針)
- **runbook の書換え** — 本 Closure 段階では operator runbook (`docs/operations.md`) は更新しない (§5 / §6.2 の真値固定で十分とし、runbook 反映は次の operator-facing PR で)
