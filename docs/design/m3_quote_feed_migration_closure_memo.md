# M-3 QuoteFeed Migration — Closure Memo

> **目的**: M9 配下の M-3 シリーズ (M-3a / M-3b / M-3c) で何を解消し、何を意図的に未着手のまま残したかを 1 ページに棚卸する。
> **位置付け**: 完了済み 3 PR の closure memo。M-3d (live OANDA producer) は未着手で、本メモはその pickup 前提を明示するためにある。
> **対象外**: 実装変更・config 注入・metrics / runbook 追加。本ドキュメントは **docs-only**。

---

## 1. 背景 / なぜ M-3 を切ったか

`run_exit_gate` は M9 H-* シリーズで "唯一の exit 経路" として確立されたが、価格供給は依然として `Callable[[str], float]` のままだった。これにより以下の 3 点が同時に未解決:

1. **タイムスタンプが取れない** — 価格 float のみが返るため、`quote.ts` を inspect する staleness gate を追加する余地がない。
2. **ソースが追跡できない** — どの producer (paper / mock / oanda live) から来た価格かを exit 側で判別できない。
3. **将来の live producer (OANDA streaming) を差し込む先がない** — Producer 側に Protocol が存在しないため、live producer の実装着地点が決まらない。

M-3 シリーズはこの 3 点を **追加的に / 既存挙動を一切変えずに** 解決するための 3 段ロケットとして設計された:

| ステージ | 役割 | 性質 |
|---|---|---|
| M-3a | DTO + Protocol + adapter を **producer 側だけ**に追加 | 純加算 (consumer 不触) |
| M-3b | run_exit_gate / Supervisor を `QuoteFeed` ベースに rewire (legacy callable は adapter で吸収) | 純加算 (挙動同値) |
| M-3c | `quote.ts` を見て stale quote gate を発火 | 新 outcome 追加 (legacy 経路は age=0 で発火しない) |

> **3 段に分けた理由**: 1 PR = 1 責務を厳守し、各段で「DTO 追加だけ / consumer 配線だけ / staleness logic だけ」が独立してレビューできる粒度を確保するため。M-3a を merge した時点で M-3b の rewire が有効化される、というような暗黙依存を避けた。

---

## 2. PR 対応表

| ステージ | PR | merge commit | 種別 | 主な変更 |
|---|---|---|---|---|
| M-3a | #134 | `9b8c85b` | feat | `domain/price_feed.py`: `Quote` (frozen DTO, tz-aware ts validation) / `QuoteFeed` (`@runtime_checkable` Protocol) / `callable_to_quote_feed` adapter / `SOURCE_*` constants |
| M-3b | #135 | `1ab48ad` | refactor | `services/exit_gate_runner.run_exit_gate`: `price_feed: Callable[[str], float]` → `quote_feed: QuoteFeed \| Callable[[str], float]` (isinstance 判定で wrap) / `supervisor/supervisor.Supervisor.attach_exit_gate`: 同 union を受け、attach 時に **1 回だけ** wrap (per-tick double-wrap なし) |
| M-3c | #136 | `04e5447` | feat | `services/exit_gate_runner.run_exit_gate`: `stale_max_age_seconds: float = 60.0` 追加 / per-position `(now - quote.ts).total_seconds()` 検査 / 新 outcome `'noop_stale_quote'` / `emergency_stop` bypass / warning ログに instrument / age / source / max_age |

**Master tip after series:** `04e5447`.

**全 3 PR で守った制約**:
- 1 PR = 1 責務
- additive change (既存 callable 呼び出し側はゼロ変更で動く)
- schema 変更ゼロ / migration ゼロ / app_settings ゼロ
- broker adapter (paper / mock / oanda) 不触
- SafeStop / notifier / G-2 / G-3 不触
- CI 完全 green (test / contract-tests 両方)

---

## 3. 何を導入したか

### 3.1 `Quote` DTO (M-3a)

```text
@dataclass(frozen=True)
class Quote:
    price:  float
    ts:     datetime  # tz-aware required (post_init validates)
    source: str       # SOURCE_* constants
```

- **frozen**: 渡した先で書き換えられないことを型レベルで保証。
- **`__post_init__` で tz-aware 検証**: naive datetime を受け取った瞬間に `ValueError`。staleness 計算で tz mismatch エラーが発生しないことを producer 側で先に潰す設計。
- **`source` 文字列**: SOURCE_LEGACY_CALLABLE / SOURCE_OANDA_LIVE / SOURCE_OANDA_REST_SNAPSHOT / SOURCE_PAPER / SOURCE_TEST_FIXTURE — 観測時に producer を一意に特定できる。

### 3.2 `QuoteFeed` Protocol (M-3a)

```text
@runtime_checkable
class QuoteFeed(Protocol):
    def get_quote(self, instrument: str) -> Quote: ...
```

- `@runtime_checkable` で `isinstance(x, QuoteFeed)` が成立。これが M-3b の "QuoteFeed か legacy callable か" の discrimination の基盤。
- 引数は instrument 1 個。複数 instrument の bulk fetch は意図的に未定義（M-3d で必要になったときに別 Protocol を切る判断）。

### 3.3 `callable_to_quote_feed` adapter (M-3a)

```text
def callable_to_quote_feed(
    fn: Callable[[str], float],
    *,
    clock: Clock,
    source: str = SOURCE_LEGACY_CALLABLE,
) -> QuoteFeed:
    ...  # 内部で fn(instrument) を Quote(price=..., ts=clock.now(), source=...) に包む
```

- `ts = clock.now()` で合成。これにより **legacy callable 経由の quote は常に age=0 として観測される** — M-3c の staleness gate が legacy 経路では絶対に発火しないことを保証する重要な不変条件。
- `clock` は呼び出し側から注入 (ローカル `datetime.now()` 禁止 — 既存 lint ルール準拠)。

### 3.4 `run_exit_gate` / `Supervisor` の QuoteFeed 化 (M-3b)

- `run_exit_gate(quote_feed=...)`: `QuoteFeed | Callable[[str], float]` を受け、ループ前に **1 回だけ** isinstance 判定して `qf` に正規化。`qf.get_quote(pos.instrument).price` でループ内では QuoteFeed として扱う。
- `Supervisor.attach_exit_gate(quote_feed=...)`: 同じ union を受け、attach 時に `self._clock` で 1 回 wrap して `_ExitGateAttachment` に格納。`run_exit_gate_tick` は格納済 QuoteFeed を `run_exit_gate` に **参照渡し**するだけ — per-tick double-wrap が起きないことが integration テストで pin されている。
- PR-5 / U-2 SafeStop wiring (`supervisor=self`) は完全保持。

### 3.5 stale quote gate (M-3c)

| 項目 | 仕様 |
|---|---|
| trigger | `age_seconds > stale_max_age_seconds` (**strict `>`** — age == max_age は stale 扱いしない) |
| bypass | `context.get("emergency_stop")` が truthy なら gate 全スキップ |
| 既定値 | `stale_max_age_seconds = 60.0` (per-call argument; app_settings 化は 5.1 で deferral) |
| 結果 | 新 outcome `'noop_stale_quote'` (broker 呼出ゼロ / on_close ゼロ / 次 tick で再評価) |
| ログ | `WARNING run_exit_gate: stale quote — instrument=%s age=%.1fs source=%s max_age=%.1fs; skipping close evaluation` |
| emergency_stop の読み出し | per-tick で **1 回だけ** (ループ外) — 同 tick 内の全 position は同一 operator intent を共有 |

---

## 4. アーキテクチャ依存関係

```text
[future M-3d producer (OANDA streaming)]                ← 未着手
        ↓ implements
[QuoteFeed Protocol]                                    ← M-3a
        ↑
        │ isinstance discrimination
        │
[QuoteFeed | Callable[[str], float]]
        ↓ legacy branch wraps via
[callable_to_quote_feed (clock-bound, source="legacy_callable")]
        ↓
[run_exit_gate (M-3b consumer)]
        ↓ per-position
[quote = qf.get_quote(instrument)]
        ↓
[M-3c stale gate: age_seconds > max_age AND not emergency_stop?]
        ├─ YES → outcome="noop_stale_quote" + WARNING log + skip
        └─ NO  → ExitPolicyService.evaluate(...) → close path (既存)
```

**非影響領域** (本シリーズで一切触っていない):
- `ExitPolicyService.evaluate` / `ExitDecision`
- `StateManager.on_close` / 全 close-event 書込経路
- broker adapter (paper / mock / oanda)
- SafeStop / notifier (PR-5 / U-2 / G-2 / G-3 配線そのまま)
- schema / Alembic migration / `app_settings` テーブル
- metrics / runbook / dashboard query

---

## 5. 解消済み / 未解消の整理

### 5.1 M-3 で解消したもの

| 課題 | 状態 | 解消した PR |
|---|---|---|
| 価格にタイムスタンプが付かない | ✅ 解消 (`Quote.ts`, tz-aware required) | #134 |
| 価格のソースが追跡できない | ✅ 解消 (`Quote.source` + SOURCE_* 定数) | #134 |
| Producer 側の差し込み先が決まっていない | ✅ 解消 (`QuoteFeed` Protocol) | #134 |
| 既存 callable 呼出側に破壊的変更を強いる | ✅ 回避 (`callable_to_quote_feed` で吸収) | #134 → #135 |
| `run_exit_gate` が `quote.ts` を見られない | ✅ 解消 (M-3b で QuoteFeed ベースに) | #135 |
| `Supervisor.attach_exit_gate` が legacy callable しか受けない | ✅ 解消 (union 受け / attach 時 1 回 wrap) | #135 |
| 古い quote で close 判定が走り得る | ✅ 解消 (60s 既定の stale gate) | #136 |
| operator flat-all が feed 障害で塞がれ得る | ✅ 解消 (`emergency_stop` bypass) | #136 |
| stale quote 発生時に観測手段がない | ✅ 解消 (WARNING ログ + 専用 outcome) | #136 |

### 5.2 M-3 で意図的に未解消 (deferral)

| 項目 | 現状 | 解消予定 / pickup 条件 |
|---|---|---|
| **M-3d**: live OANDA streaming producer | 未着手 | M-3 シリーズ最終段。明示指示まで pickup しない (本メモがその境界) |
| `stale_max_age_seconds` の `app_settings` 化 | per-call argument のみ | live producer landing 後に運用負荷を見てから判断。早期に config 化すると schema 変更が先行発生し additive 性が崩れる |
| stale 発火回数の metrics 化 | 未対応 (ログのみ) | ExitFireMetricsService 流の read-only service として後段で別 PR。本シリーズの境界外 |
| stale gate の operator runbook | 未対応 | live producer (M-3d) で初めて実 runtime で発火し得るため、runbook は M-3d 後に書く方が情報量が高い |
| paper-mode broker への QuoteFeed 直接接続 | 未対応 (paper は callable のままで動く) | adapter で完全互換のため緊急性なし。M-3d で live と paper の対称性を確保するときに同時に検討 |

### 5.3 非影響を再確認

本シリーズで diff ゼロを維持した領域 (closure として明示):

- `app_settings` テーブル / seed / schema migration
- metrics emission (ExitFireMetricsService 含む)
- runbook (`docs/runbook/`)
- SafeStop trigger 配線 (PR-5 / U-2)
- notifier (G-2 / G-3)
- 全 schema (orders / positions / close_events / order_transactions / outbox)
- Alembic migration

→ **M-3 シリーズは "exit path への純加算 3 段" として閉じた**。下流 (broker / state / close-event 書込) も上流 (Supervisor lifecycle / cadence) も契約変更なし。

---

## 6. M-3d 解凍チェックリスト

M-3d (live OANDA streaming producer) を pickup するときの前提を以下に保管する:

1. **producer 側に `QuoteFeed` Protocol を実装** — `domain/price_feed.QuoteFeed` を import し `get_quote(instrument) -> Quote` を実装。`Quote.source` には新規 SOURCE_OANDA_STREAMING (仮) 等を追加。
2. **producer の clock 注入を確認** — `Quote.ts` は producer が観測した market timestamp を入れる (clock.now() ではない)。M-3a の `callable_to_quote_feed` とは ts の意味が異なる点に注意。
3. **`stale_max_age_seconds` の調整余地** — live streaming は 60s 既定で十分余裕がある。OANDA REST snapshot fallback を経由する場合は producer 側で fallback フラグを source に乗せ、運用側で必要なら per-call で `stale_max_age_seconds` を引き上げる (app_settings 化はそれでも保留可)。
4. **paper / live の対称性** — Supervisor は QuoteFeed を 1 つしか持たない。live と paper を同時に走らせる構成を考えるときは Supervisor 側の attach 時に producer を切り替える形になる (M-3d の責務の外、運用側の構成判断)。
5. **既存 stale gate との結合テスト** — M-3c の `TestStaleQuoteGate` クラス (5 テスト) はそのまま回帰テストとして機能する。live producer 追加時は `_StaleStubFeed` と同じ shape の fake を injection して回帰確認。

---

## 7. 参考リンク

- M-3a 実装メモ: `memory/project_m9_m3a_pr_opened.md`
- M-3b 実装メモ: `memory/project_m9_m3b_pr_opened.md`
- M-3c 実装メモ: `memory/project_m9_m3c_pr_opened.md`
- M9 H-* シリーズ (run_exit_gate を sole exit path にした履歴): `memory/project_m9_h*_merged.md`
- 関連ソース:
  - `src/fx_ai_trading/domain/price_feed.py` (Quote / QuoteFeed / callable_to_quote_feed)
  - `src/fx_ai_trading/services/exit_gate_runner.py` (run_exit_gate / stale gate)
  - `src/fx_ai_trading/supervisor/supervisor.py` (attach_exit_gate / run_exit_gate_tick)
- 関連テスト:
  - `tests/unit/test_quote_feed.py` (M-3a Quote/QuoteFeed/adapter)
  - `tests/unit/test_exit_gate_runner.py::TestQuoteFeedAcceptance` (M-3b)
  - `tests/unit/test_exit_gate_runner.py::TestStaleQuoteGate` (M-3c)
  - `tests/integration/test_supervisor_exit_gate_wiring.py::TestAttachExitGateLegacyCallable` (M-3b)
