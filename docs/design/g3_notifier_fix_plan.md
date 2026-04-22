# G-3 Fix Phase 設計メモ — Notifier 多チャネル配信の修正方針

| 項目 | 値 |
|---|---|
| 対象フェーズ | G-3 Safety Fix Phase |
| 対象領域 | Notifier 多チャネル配信 (`adapters/notifier/*`, `supervisor/safe_stop.py` step 3) |
| 起点監査 | G-3 audit (read-only, 本セッション 2026-04-22) |
| 直前完了 | G-2 Fix Phase (#112 / #113 / #114 / #115 / #116 / #117 全 merge / master tip `96d0c34`) |
| ステータス | **設計確定 (本 PR-β)** — 実装は別 PR (本メモ §6 参照) |
| 関連メモ | `docs/design/g2_fix_phase_memo.md`, `docs/design/safety_verification_gaps_memo.md` |

---

## 1. 目的とスコープ

### 目的
`SafeStop` 発火時に operator/oncall に確実に通知が届く状態を確立する。具体的には:
- Slack / Email を含む multi-channel 配信を **production で実行可能** にする。
- 1 チャネルの失敗・遅延が他チャネルや safe_stop シーケンス全体をブロックしない契約を確立する。
- チャネル別配送結果を可観測にし、「配送失敗が全部 silent」を解消する。

### 非対象 (本 Fix Phase で扱わないこと)
- 通知 routing (severity 別 / event_code 別) のポリシー化 → Iter 2 後半。
- `notification_outbox` 表の実装と OutboxProcessor 接続 → M8 scope (G-2 §5 deferral と同じ defer 先)。
- PagerDuty / SMS 等の追加チャネル → Iter 2 後半。
- `dispatch_via_outbox` の本実装 (現状 file-only stub) → M8 scope。

---

## 2. 現状整理 — R-1 が本質である

G-3 audit で 15 件 (Critical 1 / High 2 / Medium 6 / Low 6) を抽出したが、**R-1 が本質的な唯一の課題** であり、他は R-1 解消後に同時/直後に発火する派生リスク。

### R-1 (Critical) — multi-channel が production に **配線されていない**

| 観測事実 | 該当行 / 確認方法 |
|---|---|
| `NotifierDispatcherImpl(...)` の production 呼出 = 0 | `grep -rn "NotifierDispatcherImpl(" src` → 0 ヒット (tests に 14 箇所) |
| `SlackNotifier(...)` / `EmailNotifier(...)` の production 呼出 = 0 | 同上 |
| `Supervisor(clock=...)` を起動する production code = 0 | docstring 例のみ |
| `src/fx_ai_trading/supervisor/__main__.py` = 不在 | `grep -rn "if __name__" src` → 0 ヒット |
| `ProcessManager.start()` は `python -m fx_ai_trading.supervisor` を spawn | `ops/process_manager.py:57` |

→ 結論: **safe_stop の "通知" は production で `FileNotifier` への file 書込 1 経路のみ**。Slack/Email/Dispatcher は dead code。supervisor process そのものが起動できない (`__main__` 不在 → ModuleNotFoundError)。

### 派生リスク (R-1 を解消した瞬間に live を脅かす)

| ID | 内容 | R-1 と同時に解消必須か |
|---|---|---|
| R-2 | `EmailNotifier` SMTP **timeout 無し** → ハング時 step 3 が無限ブロック → step 4 (DB record) に到達せず | **Yes** |
| R-3 | `EmailNotifier` 3 回 retry に backoff 無し → R-2 を増幅 | **Yes** |
| R-6 | Slack/Email の credential / config 読込が production code に無い → R-1 を解消しても `external_notifiers=[]` で起動して file-only に縮退 | **Yes** |
| R-12 | Notifier channel の health probe が startup 16 step に無い → 設定ミスは safe_stop 発火時まで気付けない | **Yes** |

### R-1 と切り離せる派生リスク

| ID | 内容 | 解消順序の自由度 |
|---|---|---|
| R-4 | dispatcher が `FileNotifier` の `NotifyResult` を見ていない (file 失敗が silent) | R-1 と独立、後追い可 |
| R-5 | dispatcher が channel 別結果を返さない → `_safe_stop_completed` が虚偽 True になりうる | R-1 と独立、後追い可 |
| R-7 | SlackNotifier の HTTP 200 意味的失敗 / except 句冗長 | R-1 と独立、後追い可 |
| R-8 | ctl emergency-flat-all が dispatcher を経由しない | dispatcher 配線後に検討 |
| R-9 | SafeStopJournal cross-process 競合 | independent (G-3 とは別 phase) |
| R-10 | SafeStopJournal `read_all` が破損行 silent skip | R-9 と一緒 |
| R-11 | ctl の SafeStopJournal.append が try/except 無し | independent |
| R-13 | `dispatch_via_outbox` が file-only stub | M8 scope |
| R-14 | SlackNotifier の payload formatter | independent |
| R-15 | fan-out 順序と blocker の不整合 | R-2/R-3 で実質解消 |

### 判断

「R-1 を単独で解消する PR」を作ってはいけない。R-1 を解消した瞬間 R-2/R-3/R-6/R-12 が即座に live を脅かす状態になるため、**R-1 と R-2/R-3/R-6/R-12 を 1 セットで配線する** 必要がある。

---

## 3. 修正方針 (設計の核)

### 3.0 大原則 (本 Fix Phase 全 PR を貫く invariant)

以下の 2 原則は §3.1 〜 §3.4 すべての設計判断に優先する。実装 PR (PR-1 ~ PR-4) で
これらに反する選択肢が出た場合は、設計議論を本メモに差戻して再合意する。

#### P-1 SafeStop 優先ルール

**外部通知 (Slack / Email / 将来の追加チャネル) によって SafeStop シーケンスが
ブロックされてはならない。**

- 「ブロック」とは: step 3 の wall-clock が外部通知の遅延・失敗・例外に依存して
  伸びる状態、または step 4 (DB record) に到達できない状態を指す。
- 具体策:
  - Email timeout 必須化 (§3.2) — 設定可能だが **無限待ちは禁止**。
  - dispatcher は外部通知の `NotifyResult(success=False)` を **例外に昇格しない** (既存契約の維持)。
  - `_safe_stop_completed` の判定を file 配送成功にバインドする (§3.3.3) — 外部通知の成否を
    safe_stop 完了の真値性に持ち込まない。
  - 並列 fan-out は採用しない (§3.3.1) — 並列化で外部通知の失敗を隠す代償として
    順序契約 (6.1) や §13.1 制約を曖昧化する選択を取らない。
- 反例 (本ルールに違反するため採用しない): step 3 を「全チャネル成功」で判定する、
  external notifier の例外を SafeStopHandler まで伝播させる、Email retry に
  unbounded backoff を入れる、等。

#### P-2 File-only fallback の明文化

**`FileNotifier` (= `logs/notifications.jsonl` への fsync 書込) は配信経路の last-resort
として常に必須であり、外部チャネルはベストエフォートである。**

- 必須性 (`FileNotifier`):
  - `NotifierDispatcherImpl.__init__` の `file_notifier` は **required** のまま (既存契約)。
  - `notifier_factory.build_notifier_dispatcher` は `FileNotifier` を必ず生成・注入する。
    設定 / 環境変数の有無に依存しない。
  - 設定不在 / 起動順序ミス / 設定読込失敗のいずれでも、結果として
    「`FileNotifier` だけが繋がっている dispatcher」が production の **正常な縮退状態** とする。
- ベストエフォート性 (Slack / Email):
  - 設定不在のチャネルは silent skip (`notifier_factory` は warning ログのみ、起動は通す)。
  - 配信失敗 (`NotifyResult(success=False)`) は warning ログのみで、step 3 の bool を
    False にしない (= P-1 と整合)。
  - operator は「Slack/Email が来なかった可能性」を前提に、`logs/notifications.jsonl`
    と `logs/safe_stop.jsonl` を **真値ソースとして読む運用** をとる (operations runbook 側で再確認)。
- 反例 (本ルールに違反するため採用しない): `FileNotifier` を optional にする、
  外部チャネル全失敗で起動を停止する、Slack/Email が届かないことを runtime error として扱う、等。

→ 本 2 原則は §5 の契約 C-9 / C-10 として規定する。

### 3.1 NotifierDispatcher を production に接続する方式

新規モジュール: `src/fx_ai_trading/supervisor/notifier_factory.py` (新設、本メモ §6 PR-1 で実装)

責務:
1. `ConfigProvider` または環境変数から Slack / Email の設定を読込む。
2. 設定が揃っているチャネルだけを instantiate して `NotifierDispatcherImpl` に注入する。
3. 設定が無いチャネルは **silent に skip** (KeyError / ValueError を起動で raise しない)。
4. 設定読込ミスは **startup step 15 (health) で fail-loud** (R-12 と対)。

```python
# 設計上のシグネチャ (実装は PR-1)
def build_notifier_dispatcher(
    *,
    config: ConfigProvider,         # または env: Mapping[str, str]
    file_notifier: FileNotifier,    # 必須 (last-resort)
) -> NotifierDispatcherImpl:
    externals: list[NotifierBase] = []
    if (slack_url := config.get_optional("notifier.slack.webhook_url")):
        externals.append(SlackNotifier(webhook_url=slack_url))
    email = None
    if (email_cfg := config.get_optional("notifier.email")):
        email = EmailNotifier(
            host=email_cfg["host"],
            port=email_cfg["port"],
            sender=email_cfg["sender"],
            recipients=email_cfg["recipients"],
            username=email_cfg.get("username"),
            password=email_cfg.get("password"),
            connect_timeout_s=NOTIFIER_EMAIL_TIMEOUT_S,  # PR-2 で導入
        )
    return NotifierDispatcherImpl(
        file_notifier=file_notifier,
        external_notifiers=externals,
        email_notifier=email,
    )
```

呼出箇所 (PR-1 で追加):
- `supervisor/__main__.py` (新設) で `Supervisor` を instantiate → `StartupContext.notifier` に注入。
- `__main__.py` は `ProcessManager.start()` の `python -m fx_ai_trading.supervisor` 想定と一致させる。

### 3.2 timeout / retry / fail-fast 方針

| チャネル | timeout | retry | backoff | 根拠 |
|---|---|---|---|---|
| **File** | N/A (ローカル fsync) | なし | N/A | last-resort 経路。raise しない契約 (既存)。 |
| **Slack** | **5 秒 (既存維持)** | なし (既存維持) | N/A | webhook は冪等でないので retry より timeout 厳守 |
| **Email** | **接続/送信ともに 10 秒 (新規導入)** | **2 回まで (既存 3 → 2 に削減)** | **指数 backoff も無し** (development_rules.md §13.1 で `time.sleep` 制約) | **safe_stop ブロック上限を 30 秒に固定** (= 10s × (1 + 2 retry)) |

- `EmailNotifier.__init__` に `connect_timeout_s: int = 10` 引数を追加 (PR-2)。`smtplib.SMTP(host, port, timeout=connect_timeout_s)` で渡す。
- `_MAX_RETRY = 3 → 2` に変更 (PR-2)。
- backoff (`time.sleep`) は §13.1 制約により **導入しない**。retry 直後 = 同じ transient error の可能性が高いが、production timeout 30 秒上限を優先。

### 3.3 SafeStop をブロックしない設計

#### 3.3.1 channel 単位の wall-clock fence

逐次 fan-out (File → externals → Email) のままでよいが、**dispatcher 全体のブロック上限を保証** する:

```
safe_stop_step3_wall_budget_s = 30
  ├─ File:     ~immediate (fsync)
  ├─ Slack:    ≤ 5s
  └─ Email:    ≤ (10s × (1 + 2 retry)) = 30s   ← ここが律速
```

並列 fan-out (`concurrent.futures` 等) は **採用しない**:
- 追加スレッド/プロセスは §13.1 の clock 制約とテスト容易性を悪化。
- 既存の逐次フローで timeout を律速にすれば 30 秒上限で十分。
- safe_stop 4-step のうち step 3 が 30 秒かかっても step 2 (loop stop) は既に完了しており、新規 trade は発生しない。

#### 3.3.2 Step 4 (DB record) を Step 3 のブロックから守る

現状: `dispatch_direct_sync` が無限ブロックすると step 4 に到達しない。
PR-2 で email timeout を導入すれば step 3 は最大 30 秒で必ず戻る → step 4 が必ず実行される。

代替案 (採用しない): step 3 を別 thread で fire-and-forget。理由は §3.3.1 と同じ + 6.1 順序契約を曖昧にする。

#### 3.3.3 dispatcher の戻り値変更 (PR-3)

`dispatch_direct_sync` の return を `None → DispatchResult` に変更:

```python
@dataclass(frozen=True)
class DispatchResult:
    file: NotifyResult              # 必ず存在
    externals: list[NotifyResult]   # external_notifiers と同順
    email: NotifyResult | None      # email_notifier 不在時 None
    
    @property
    def all_success(self) -> bool: ...
    @property
    def any_external_success(self) -> bool: ...
```

`SafeStopHandler._fire_step3_notifier` の判定ロジック:
- `result.file.success is False` → **step 3 失敗 (last-resort 経路の喪失は深刻)**。
- 設定済 external/email がすべて失敗 → step 3 は警告 log を出すが **True を返す** (file は届いたので safe_stop 完了の意味はある)。
- どちらの定義も「`_safe_stop_completed` が file 配送成功と同値」を保証する (R-5 / R-4 の同時解消)。

(細部の闾値判定は PR-3 で確定。本メモは「dispatcher が channel 別結果を返す」「step 3 の bool は file 配送成功と一致する」の 2 点を契約として固定する。)

### 3.4 設定 (Slack / Email) の注入方法

#### 3.4.1 設定スキーマ (`app_settings` または環境変数)

| キー | 型 | 必須 | デフォルト | 備考 |
|---|---|---|---|---|
| `notifier.slack.webhook_url` | str | No | None | 不在 → Slack channel 無効化 |
| `notifier.email.host` | str | No | None | 不在 → Email channel 無効化 |
| `notifier.email.port` | int | No | 587 | STARTTLS 既定 |
| `notifier.email.sender` | str | Yes if email enabled | — | |
| `notifier.email.recipients` | list[str] | Yes if email enabled | — | カンマ区切り入力可 |
| `notifier.email.username` | str | No | None | SMTP auth |
| `notifier.email.password` | str (secret) | No | None | env var `SMTP_PASSWORD` 経由推奨 |
| `notifier.email.connect_timeout_s` | int | No | 10 | §3.2 |
| `notifier.email.max_retry` | int | No | 2 | §3.2 |

- secret (`webhook_url`, `password`) は **環境変数優先** で読込 (Cycle 16 の seed 方針と整合)。
- 設定欠損は startup 時 ERROR ログ + degraded 起動 (channel 無効化) → step 15 health で **明示警告** (R-12 解消)。

#### 3.4.2 startup での読込タイミング

- StartupRunner step 4 (config load) の直後 (新規 step を追加せず既存の config 読込完了点を再利用)。
- `StartupContext.notifier` を `notifier_factory.build_notifier_dispatcher(...)` の戻り値で初期化する形にする。
- 既存テストへの影響は最小化: `StartupContext.notifier: object` のままにし、テストは MagicMock で注入し続けられる。

#### 3.4.3 health probe (R-12 解消)

Step 15 (health check) に追加 (PR-4):
- Slack: webhook URL の DNS resolve のみ (HTTP POST はせず) → 5 秒 timeout。
- Email: `smtplib.SMTP(host, port, timeout=10)` で接続のみ → 即 close (login/STARTTLS せず)。
- どちらも失敗時は **degraded** 扱い (起動は continue、UI / 起動ログに警告)。`StartupError` は raise しない。
- 理由: production に Slack/Email を後付け接続する shake-down 期間に、設定ミスで Supervisor が起動できないのは過剰。

---

## 4. 修正順序 (PR 分割と依存関係)

```
[ G-3 audit (本セッション完了) ]
        │
        ▼
[ PR-β: 本設計 memo (この PR, docs-only) ]
        │
        ▼
[ PR-1: notifier_factory + supervisor/__main__ + dispatcher 配線 ]
        │   ← R-1 を解消 (single seal)。設定不在時は file-only で起動継続。
        ▼
[ PR-2: EmailNotifier に timeout 導入 + retry を 2 に削減 ]
        │   ← R-2/R-3 解消。PR-1 と直列でなければならない (R-2/R-3 が live を脅かす状態を作らない)。
        ▼
[ PR-3: dispatcher の戻り値を DispatchResult 化、SafeStopHandler step 3 の判定を file 配送成功にバインド ]
        │   ← R-4/R-5 解消。
        ▼
[ PR-4: startup step 15 に Slack DNS / SMTP TCP 接続 health probe を追加 ]
        │   ← R-12 解消。
        ▼
[ G-3 Fix Phase クローズ memo (PR-α 系) ]
```

依存関係:
- **PR-1 → PR-2 は直列必須**。PR-1 を merge した時点で R-2/R-3 が live を脅かす状態 (Email
  ハングで safe_stop が無限ブロック) になるため、PR-1 と PR-2 はセットで扱う。
- **PR-1 単独 merge は禁止**。以下を merge precondition として PR-1 review に明記する:
  1. PR-2 (Email timeout / retry 削減) が **同時に PR として open しており**、CI green かつ
     review approved 状態であること。
  2. PR-1 と PR-2 の merge 順序は **PR-1 → 即 PR-2** とし、間に他 PR を挟まない。
  3. もし PR-2 が想定外の手戻りで delay する場合、PR-1 は **revert** または **draft 戻し** にする
     (中途半端な merge 状態で master に live-threatening な構成を残さない)。
  この precondition は PR-1 の PR description 冒頭にコピーされること。
- PR-3 / PR-4 は PR-2 完了後に並列着手可。

各 PR の責務 (1 PR = 1 責務):

| PR | 責務 | 主変更ファイル | テスト追加 |
|---|---|---|---|
| **PR-1** | NotifierDispatcher 配線 + supervisor `__main__` 新設 + 設定不在時の縮退 | `src/fx_ai_trading/supervisor/notifier_factory.py` (新), `src/fx_ai_trading/supervisor/__main__.py` (新), `scripts/ctl.py` (PID file path 整合のみ) | unit (factory), integration (supervisor 起動 → dispatcher 接続確認) |
| **PR-2** | Email timeout 10s + retry 3→2 | `src/fx_ai_trading/adapters/notifier/email.py` のみ | contract test (timeout 動作 / retry 回数) |
| **PR-3** | DispatchResult 導入 + step 3 判定 file-bound | `src/fx_ai_trading/adapters/notifier/dispatcher.py`, `src/fx_ai_trading/supervisor/safe_stop.py` | contract test (R-4/R-5 ケース) |
| **PR-4** | health probe 追加 | `src/fx_ai_trading/supervisor/health.py` または `startup.py` step 15 | integration (DNS 失敗 / TCP 失敗の degraded path) |

非対象 PR (本 Fix Phase で開けない):
- R-7 (Slack 200 意味的失敗) — backlog 化、Iter 2 で再評価。
- R-8 (ctl が dispatcher 経由しない) — backlog 化、emergency-flat 設計と一緒に再評価。
- R-9/R-10 (SafeStopJournal cross-process) — 別 Fix Phase (Journal 整合 phase) で扱う。
- R-11 / R-13 / R-14 — backlog 化。
- R-15 — PR-2 で実質解消。

---

## 5. 契約・不変量 (実装側がレビュー時に守るべき bar)

| ID | 契約 | テスト形式 |
|---|---|---|
| C-1 | `notifier_factory.build_notifier_dispatcher` は設定不在のチャネルを silently skip し、startup を通す | unit |
| C-2 | `EmailNotifier.send` は wall-clock 30 秒以内に必ず戻る (timeout × (1+retry)) | contract (mock socket hang) |
| C-3 | `SafeStopHandler.fire` は wall-clock 60 秒以内に必ず戻る (step 3 = 30s 上限 + 他 step) | integration |
| C-4 | `_safe_stop_completed=True` ⇔ file 配送 (last-resort) が成功した | contract |
| C-5 | external/email 全失敗でも `_safe_stop_completed=True` になり得る (file 成功している限り)、ただし WARN log を出す | contract |
| C-6 | startup step 15 で Slack/SMTP 接続失敗は degraded であり StartupError を raise しない | integration |
| C-7 | secret (webhook URL, SMTP password) は **log 出力に含まれない** | contract (caplog 検査) |
| C-8 | `dispatch_via_outbox` の振る舞いは G-3 で変更しない (M8 scope) | regression |
| C-9 | **P-1 SafeStop 優先ルール**: 外部通知の遅延・失敗・例外は `SafeStopHandler.fire` の wall-clock を §3.2 の上限を超えて伸ばさず、step 4 の到達を阻害しない | integration (mock 外部 hang / 例外) |
| C-10 | **P-2 file-only fallback**: `notifier_factory.build_notifier_dispatcher` は外部設定不在でも `FileNotifier` を必ず注入し、起動を degraded で通す。`FileNotifier` 配送成功 = `_safe_stop_completed=True` の必要十分条件 (C-4 と等価) | unit (factory) + contract (step 3 判定) |

---

## 6. PR-α (本設計後の実装) と PR-β (本メモ) の分離

| 種別 | PR | 内容 |
|---|---|---|
| **PR-β (本 PR)** | docs-only | 本ファイル `docs/design/g3_notifier_fix_plan.md` 1 件 |
| **PR-1 ~ PR-4** | 実装 | §4 の表参照 |

PR-β を先に merge する理由:
- PR-1 を実装に入る前に「設定スキーマ」「dispatcher 戻り値の契約」「health probe の degraded 扱い」を確定させ、PR-1 ~ PR-4 の review が実装議論に集中できる状態を作る。
- G-2 Fix Phase で確認済の進め方 (`g2_fix_phase_memo.md` PR-β 先行) と同一フロー。

---

## 7. クローズ条件

G-3 Fix Phase は以下 5 PR がすべて merge された時点でクローズ:
1. **PR-β (本メモ)** — 設計確定
2. **PR-1** — dispatcher 配線
3. **PR-2** — Email timeout / retry
4. **PR-3** — DispatchResult / step 3 判定
5. **PR-4** — health probe

クローズ時に `docs/design/g3_notifier_fix_plan.md` 末尾に "Closure" セクションを追記し、各 PR の merge SHA と実装上の決定事項 (本メモの設計とのずれ) を真値化する。

---

## 8. 関連資料

- `docs/design/g2_fix_phase_memo.md` — G-2 Fix Phase Closure memo (PR ↔ audit ID 対応表)
- `docs/design/safety_verification_gaps_memo.md` — Cycle 6.12 の verification gap memo (G-1/G-2/G-3 の元)
- `docs/phase6_hardening.md §6.13` — 通知 two-path dispatch 契約
- `docs/operations.md §F14` — operator runbook (safe_stop reason 一覧)
- `src/fx_ai_trading/adapters/notifier/dispatcher.py` — NotifierDispatcherImpl 実装 (PR-3 改修対象)
- `src/fx_ai_trading/adapters/notifier/email.py` — EmailNotifier 実装 (PR-2 改修対象)
- `src/fx_ai_trading/adapters/notifier/slack.py` — SlackNotifier 実装 (本 Fix Phase は変更しない)
- `src/fx_ai_trading/supervisor/safe_stop.py` — SafeStopHandler step 3 (PR-3 改修対象)
- `src/fx_ai_trading/supervisor/startup.py` — StartupRunner step 15 (PR-4 改修対象)

---

## 9. 非対象 (本メモで決めないこと)

- 各 PR の commit message / branch 名 — 着手時に確定
- Slack 既存 webhook の払出フロー — operator 判断
- Email サーバ選定 (社内 SMTP relay vs SES 等) — infra 判断
- PagerDuty / SMS の追加 — Iter 2 後半
- `notification_outbox` 表の物理設計 — M8 scope
- `dispatch_via_outbox` の本実装 — M8 scope
