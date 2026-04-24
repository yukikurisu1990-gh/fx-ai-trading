# M9 Exit Improvements — **Final** Closure Memo

> **目的**: M9 配下で連続 landing した 13 PR (H-1 / H-2 / H-3a / H-3b / H-3c-part1 / H-3c-final / M-1a / M-1b / M-2 / M-3a / M-3b / M-3c / **M-3d**) と関連 closure memo (M-3 / M9 中間 closure) を踏まえ、**M-3d まで含めた M9 シリーズ全体の最終到達点**を 1 ページで確定する。
> **位置付け**: M9 series の **最終 closure**。先行する `m9_exit_improvements_closure_memo.md` (PR #138, master tip `3122cee`) は M-3d 未着手のスナップショット。本メモは PR #139 (M-3d producer landing, master tip `0a9e071`) を反映した上書き版で、M9 を完全クローズする。
> **対象外**: 実装変更・schema 変更・config 注入・Supervisor wiring・metrics / runbook 拡張。本ドキュメントは **docs-only**。

---

## 0a. Post-publication amendment (2026-04-24)

> **趣旨**: 本メモ初出 (PR #140, master `056d272`) 直後に、§5.2 / §7 / §9 で "意図的に未実施" と記述していた **`OandaQuoteFeed` の Supervisor 接続** が **PR #142 (`a66c714`, `bootstrap production paper stack`) の `scripts/run_paper_loop.py:build_supervisor_with_paper_stack` 配線で完了** していたことが事後に判明した。本メモ §5.2 / §7 / §9 / §0 の「未接続 (意図的; deferral)」「(将来 attach 時)」「意図的に未実施」「Supervisor 接続が残作業」の記述は **その時点では正しかったが、現在の master では事実と異なる**。
>
> 本セクションを以て差分を明示し、本文 §1〜§10 は当初の snapshot として保持する。
>
> | 旧記述箇所 | 旧記述 | post-#142 / #162 の事実 |
> |---|---|---|
> | §0 表「Supervisor への live producer 接続」 | 未接続 (意図的; §5.2 deferral) | ✅ paper stack 経由で接続済 (`scripts/run_paper_loop.py`) |
> | §0 表「残 deferral 件数」 | 6 | 5 (Supervisor 接続が解消側へ移動) |
> | §2.2 表 M-3d 行 | "Supervisor wiring は意図的に未実施" | producer landing は #139、wiring は #142 (paper stack) / #162 (`stale_max_age_seconds` 配線) で完了 |
> | §4.1 ASCII diagram | "※ Supervisor 接続は別 PR (deferral)" / "(将来 attach 時)" | paper stack の `build_supervisor_with_paper_stack` で `attach_exit_gate(quote_feed=OandaQuoteFeed(...))` を直接呼出 |
> | §5.1 解消済リスト | (Supervisor 接続は欠落) | **+ `OandaQuoteFeed` の Supervisor 接続 (`run_paper_loop.build_supervisor_with_paper_stack` 経由 / PR #142, #162)** |
> | §5.2 deferral 表先頭行 | "**`OandaQuoteFeed` の Supervisor 接続** ... `attach_exit_gate(quote_feed=...)` には未接続" | この行は **解消済み**。§5.1 へ移動 |
> | §5.2 prose ("差引 6 項目 ...") | 6 項目 + paper QuoteFeed 直接接続 + `pnl_summary_by_reason` の合計 8 候補 | Supervisor 接続も解消側に移動。実質残り 5 項目 + `pnl_summary_by_reason` の 6 候補 (paper QuoteFeed 直接接続も #142 で接続経路上は完了) |
> | §7 末文 | "現状: ... `attach_exit_gate(quote_feed=OandaQuoteFeed(...))` を呼ぶだけで実 runtime 接続が完了する状態" / "接続が **意図的に未実施** な理由は §5.2 冒頭参照" | paper-mode runner では接続済。**live-mode 単独 runner はまだ存在しない** (M9/M16 trading-loop bootstrap scope) ため "live 単体 runner への接続" は未着手のまま |
> | §9 候補表 "Supervisor 接続" 行 | 緊急性 = 最優先 | 接続済 (本表からは削除相当)。残る関連候補は **live-mode 単独 trading-loop runner** (M9/M16) と、その上での streaming producer 切替 |
> | §9 判断軸 ("Supervisor 接続 > net pnl > その他") | Supervisor 接続が最優先 | paper-mode 接続済を踏まえ、優先度は net pnl / metrics / runbook の順に再考要 |
>
> **新規残候補 (post-#142 / #162 の整理)**:
> - **live-mode trading-loop runner の bootstrap** — paper-loop runner と対称な `scripts/run_live_loop.py` に相当する未実装作業。M9/M16 scope。本メモ §5.2 deferral には載っていない (旧 §5.2 の "Supervisor 接続" は paper の文脈)。
> - その他の旧 §5.2 deferral (net pnl / streaming producer / stale gate metrics / runbook / `app_settings` 化) は **未消化のまま** で本 amendment の対象外。
>
> **影響範囲**: 本 amendment は docs-only。コード実態の変更ゼロ。closure memo の "snapshot at landing" 性質を保つため §1〜§10 本文は触らず、本セクションのみで差分を表明する。

---

## 0. 旧 closure memo (#138) との差分

| 観点 | 旧 closure memo (#138, `3122cee`) | 本メモ (post-#139, `0a9e071`) |
|---|---|---|
| 対象シリーズ | H + M-1 + M-2 + M-3a..M-3c | 同左 + **M-3d** |
| QuoteFeed の到達点 | Protocol + adapter + consumer rewire + stale gate | 同左 + **live OANDA REST polling producer (`OandaQuoteFeed`) 実装** |
| M-3d の扱い | §7「次候補（判断材料）」に記載 | §2.2 / §5.1 に「✅ 解消」として移動 |
| `adapters/price_feed/` sub-package | 存在しない | 新設 (M-3d で導入) |
| Supervisor への live producer 接続 | — | **未接続 (意図的; §5.2 deferral)** |
| 残 deferral 件数 | 7 | 6 (M-3d 完了の 1 件減) |

旧 closure memo は破棄せず歴史記録として残す。本メモを M9 の最終真実とする。

---

## 1. 背景 / なぜ M9 を切ったか (旧 closure §1 の要約)

Phase 6.7c 着地時点で exit 経路は 2 系統並存していた。`ExitExecutor` (旧, PR-5 / U-2 SafeStop 配線あり, `StateManager.on_close` 非経由) と `run_exit_gate` (新, post-I-09 write path)。これが Phase 6 paper GO 後に 4 つの問題を生んでいた:

1. テストが ExitExecutor 側に張り付き新経路への移行が止まる → **H で解消**
2. `OpenPositionInfo.side` が呼出側から渡される → **M-1 で解消**
3. `pnl_realized` 常時 NULL (Cycle 6.7c E3) → **M-2 で解消**
4. 価格に ts/source が無く staleness 判定不能 → **M-3 (a/b/c) で解消、M-3d で live 供給**

H (legacy 排除) → M (改善) の二段で進めた根拠は、ExitExecutor 残存中に M を進めると両経路へのパッチで工数が膨らむため。

---

## 2. シリーズ全 PR 一覧 (M-3d を追加した最終版)

### 2.1 H シリーズ — legacy ExitExecutor 排除

| ステージ | PR | merge commit | 種別 | 主な変更 |
|---|---|---|---|---|
| H-1 | #124 | `765013f` | feat | `Supervisor.attach_exit_gate` / `run_exit_gate_tick` cadence seam 追加 (`supervisor=self` で PR-5 / U-2 SafeStop 配線を `run_exit_gate` 側に保持) |
| H-2 | #125 | `753e9a9` | tests | exit-event FSM contract test を `ExitExecutor` → `run_exit_gate` に migration |
| H-3a | #126 | `5d19993` | tests | `test_exit_flow.py` を `ExitExecutor` → `run_exit_gate` に migration |
| H-3b | #127 | `328dd1b` | tests | PR-5 / U-2 safe_stop wiring test を `run_exit_gate` 経由に migration |
| H-3c part 1 | #128 | `571d21f` | tests | paper-smoke E2E Stage 7 を migration (`tests/` 配下の `ExitExecutor` importer 数 0) |
| H-3c final | #129 | `54dfe12` | refactor | `ExitExecutor` 削除 |

### 2.2 M シリーズ — `run_exit_gate` の改善 (M-3d 追記)

| ステージ | PR | merge commit | 種別 | 主な変更 |
|---|---|---|---|---|
| M-1a | #131 | `7f2faae` | feat | `OpenPositionInfo.side` を `orders.direction` から read-time に LEFT JOIN で導出 |
| M-1b | #132 | `a097323` | refactor | `run_exit_gate` / `Supervisor.attach_exit_gate` から `side=` 引数を削除 (`pos.side` が唯一の真実) |
| M-2 | #133 | `ed22d27` | feat | gross `pnl_realized` を `(fill_price - avg_price) * units * sign(side)` で算出 → `on_close` で永続化 |
| M-3a | #134 | `9b8c85b` | feat | `Quote` DTO + `QuoteFeed` Protocol + `callable_to_quote_feed` adapter |
| M-3b | #135 | `1ab48ad` | refactor | `run_exit_gate` / `Supervisor.attach_exit_gate` を `QuoteFeed` ベースに rewire |
| M-3c | #136 | `04e5447` | feat | stale quote gate (default 60s, `emergency_stop` bypass, 新 outcome `'noop_stale_quote'`) |
| **M-3d** | **#139** | **`0a9e071`** | **feat** | **`OandaQuoteFeed` (REST polling producer) 実装。`adapters/price_feed/` 新設。Supervisor wiring は意図的に未実施** |

### 2.3 closure memo

| ステージ | PR | merge commit | 種別 | 内容 |
|---|---|---|---|---|
| M-3 closure | #137 | `fe3a5c5` | docs | M-3 シリーズ単独の closure memo |
| M9 中間 closure | #138 | `3122cee` | docs | M-3d 未着手時点の M9 全体 closure |
| **M9 final closure (本 PR)** | — | — | docs | **M-3d 反映の M9 最終 closure (本ファイル)** |

**Master tip after M-3d:** `0a9e071`.

---

## 3. M9 で守った制約 (全 13 PR + 2 closure memo 共通)

| # | 制約 | 全 PR で遵守 |
|---|---|---|
| 1 | 1 PR = 1 責務 | ✅ |
| 2 | additive change — 既存 caller の挙動同値 | ✅ |
| 3 | schema 変更ゼロ / migration ゼロ | ✅ |
| 4 | `app_settings` 変更ゼロ | ✅ |
| 5 | broker adapter (paper / mock / oanda) **の挙動** 不触 (M-3d は `OandaAPIClient.get_pricing` を **読み取り側で初使用**、broker order surface には触れない) | ✅ |
| 6 | SafeStop 配線 (PR-5 / U-2) を `run_exit_gate` 側で保持 | ✅ (H-1 で seam 化、H-3 削除を経ても整合、M-3b / M-3c / M-3d を経ても逐語保持) |
| 7 | notifier (G-2 / G-3) 不触 | ✅ |
| 8 | metrics (ExitFireMetricsService 等) 不触 | ✅ |
| 9 | runbook (`docs/runbook/`) 不触 | ✅ |
| 10 | 直接 `datetime.now()` / `time.time()` なし — Clock 注入のみ (M-3d 例外: `Quote.ts` は **OANDA `time` フィールド** から導出、`clock.now()` は使わない — staleness 判定の前提を守るため) | ✅ |
| 11 | CI 完全 green (test / contract-tests) | ✅ |

---

## 4. アーキテクチャ最終形 (M-3d 反映)

### 4.1 唯一の exit 実行経路

```text
[OandaQuoteFeed (M-3d, REST polling, source=oanda_rest_snapshot)]
        │     ※ Supervisor 接続は別 PR (deferral)
        │     ※ `Quote.ts` は OANDA `time` フィールド由来 (clock.now() 不使用)
        ▼ (将来 attach 時)
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
        ├─ M-3b: QuoteFeed が一級市民 (legacy callable は adapter で吸収)
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
        ※ ExitExecutor 削除 / M-3 シリーズを経ても配線は不変
```

### 4.2 M-3d で増えた境界

| 境界 | 役割 | M-3d 後の責務 |
|---|---|---|
| `OandaQuoteFeed.get_quote(instrument)` | producer 入口 | `OandaAPIClient.get_pricing` を 1 回叩き、`prices[0]` の best bid/ask から mid を作り `Quote` を返す |
| `OandaQuoteFeedError(RuntimeError)` | parse error | response 構造異常 (missing `prices` / `bids` / `asks` / `time` / `price`) を transport error (`V20Error`) と区別。call site では同等扱いで OK |
| `Quote.ts` | observation time | OANDA `time` 文字列を `datetime.fromisoformat(s.replace("Z","+00:00"))` で UTC datetime に変換。**`clock.now()` を使わない** ことで M-3c stale gate の前提が守られる |
| `Quote.source` | provenance tag | 既定 `SOURCE_OANDA_REST_SNAPSHOT`。streaming 版が landing したら `SOURCE_OANDA_LIVE` 等に切替可能 (constructor で override 受付) |

### 4.3 ExitExecutor が消えた後に残っている契約 (M-3d で変化なし)

- `Supervisor.trigger_safe_stop(reason=..., occurred_at=..., payload=...)` のシグネチャ
- `payload` キーセット: `{actual_account_type, expected_account_type, instrument, client_order_id, detail}`
- `StateManager.on_close(...)` の呼出契約 (close_events / positions 同時書込 + outbox enqueue)
- `ExitDecision` (`position_id` 必須 / `should_exit` / `reasons` / `primary_reason`) の DTO 形

---

## 5. 解消済み / 未解消 / 非影響 — 最終整理

### 5.1 M9 で解消したもの (M-3d 完了を含む)

| 課題 | 状態 | 解消した PR |
|---|---|---|
| ExitExecutor と `run_exit_gate` の二重経路 | ✅ 解消 | H-1..H-3c-final |
| Supervisor が exit 経路に cadence seam を持たない | ✅ 解消 | H-1 |
| 旧テスト群が ExitExecutor を import し続ける | ✅ 解消 | H-2 / H-3a / H-3b / H-3c-part1 |
| ExitExecutor が tree に残存 | ✅ 解消 | H-3c-final |
| `OpenPositionInfo.side` が呼出側から渡される | ✅ 解消 | M-1a |
| `run_exit_gate(side=...)` 引数で side が外から汚染し得る | ✅ 解消 | M-1b |
| `pnl_realized` が常に NULL (Cycle 6.7c E3) | ✅ 解消 (gross) | M-2 |
| 価格に timestamp が付かない | ✅ 解消 | M-3a |
| 価格のソースが追跡できない | ✅ 解消 | M-3a |
| Producer 側の差し込み先が決まっていない | ✅ 解消 | M-3a |
| 既存 callable 呼出側に破壊的変更を強いる | ✅ 回避 | M-3a → M-3b |
| `run_exit_gate` が `quote.ts` を見られない | ✅ 解消 | M-3b |
| 古い quote で close 判定が走り得る | ✅ 解消 | M-3c |
| operator flat-all が feed 障害で塞がれ得る | ✅ 解消 (`emergency_stop` bypass) | M-3c |
| stale quote 発生時に観測手段がない (test green の限り) | ✅ 解消 (WARNING ログ + 専用 outcome) | M-3c |
| M-3 シリーズの境界が散逸 | ✅ 解消 | M-3 closure (#137) |
| **live producer 不在で QuoteFeed が抽象のまま** | **✅ 解消 (`OandaQuoteFeed` 実装)** | **M-3d (#139)** |
| **OANDA pricing response の parse 失敗を transport error と取り違え得る** | **✅ 解消 (`OandaQuoteFeedError` で分離)** | **M-3d (#139)** |
| **REST 版の `Quote.ts` が `clock.now()` で汚染され得る (実装誤り防止)** | **✅ 解消 (OANDA `time` 必須化、欠落時は raise)** | **M-3d (#139)** |

### 5.2 M9 で意図的に未解消 (deferral) — M-3d 完了で 1 件減

| 項目 | 現状 | pickup 条件 / 理由 |
|---|---|---|
| **`OandaQuoteFeed` の Supervisor 接続** | producer 実装のみ。`Supervisor.attach_exit_gate(quote_feed=...)` には未接続 | M-3d は「producer 実装」が責務。1 PR = 1 責務を守るため接続は別 PR。接続時は `OandaQuoteFeed(api_client=..., account_id=...)` を `attach_exit_gate` に渡すだけで済む (Protocol 互換) |
| `stale_max_age_seconds` の `app_settings` 化 | per-call argument のみ | live producer 実 runtime 接続後に運用負荷を見てから判断。早期 config 化は schema 変更が先行発生し additive 性が崩れる |
| stale 発火回数の metrics 化 | 未対応 (ログのみ) | ExitFireMetricsService 流の read-only service として後段で別 PR |
| stale gate / OANDA quote feed の operator runbook | 未対応 | live producer Supervisor 接続後に実 runtime で発火し得るため、runbook はその後に書く方が情報量が高い |
| `pnl_realized` の **net (手数料・スプレッド込)** 化 | 未対応 (現状 gross のみ) | OANDA 側の transactions detail 取得経路が未整備。M-2 は gross までで意図的に止めた |
| OANDA streaming producer (`PricingStream` 経由) | 未対応 (M-3d は polling のみ) | polling で実運用負荷を観測した後に、必要性が確認できてから別 PR。`Quote.source` を `SOURCE_OANDA_LIVE` に切替えるだけで callsite 改変不要な設計 |
| paper-mode broker への QuoteFeed 直接接続 | 未対応 (paper は callable のままで動く) | adapter で完全互換のため緊急性なし |
| ExitFireMetricsService の `pnl_summary_by_reason` 実数値 | M-2 landing で自動的に NULL → 実数値に切替 (service 側コード変更不要) | Phase 7 ダッシュボード接続時に確認 |

旧 closure memo (#138) §5.2 の 7 項目から **M-3d (live OANDA streaming producer)** が解消側へ移り、代わりに **producer の Supervisor 接続** と **OANDA streaming producer (PricingStream 経由)** の 2 項目が deferral に分離・残存。差引 6 項目 + paper QuoteFeed 直接接続 + `pnl_summary_by_reason` の合計 8 候補 (うち最後 2 件は actively waiting)。

### 5.3 非影響を再確認 (M9 全期間で diff ゼロ維持)

- `ExitPolicyService.evaluate` / `ExitDecision` (DTO 形ごと不触)
- `StateManager.on_close` の呼出契約 / write path (PR-5 / U-2 / I-09 構造そのまま)
- broker adapter (paper / mock / oanda) **の挙動・契約**
- `OandaAPIClient` 本体 (M-3d は consumer として `get_pricing` を **読み取り**、client 側コードは未変更)
- SafeStop trigger 配線そのもの (PR-5 / U-2; H-1 の `supervisor=self` で `run_exit_gate` 側に保持)
- notifier (G-2 / G-3)
- metrics emission (ExitFireMetricsService 含む)
- runbook (`docs/runbook/`)
- dashboard query wrappers (`dashboard_query_service`)
- `app_settings` テーブル / seed
- 全 schema (orders / positions / close_events / order_transactions / outbox)
- Alembic migration
- `Supervisor.attach_exit_gate` 呼出側 (M-3d は wiring に手を付けないため)

→ **M9 exit improvements は「exit 経路の単一化 + 6 種の純加算改善 (side / pnl / quote DTO / consumer rewire / stale gate / live OANDA producer)」として完全クローズ**。下流 (broker / state / close-event 書込) の契約も上流 (Supervisor lifecycle / cadence) の契約も変更なし。

---

## 6. SafeStop 配線が `run_exit_gate` 側で維持されていること

PR-5 / U-2 で確立された SafeStop 配線は ExitExecutor 削除後 / M-3 シリーズ 4 段 (a/b/c/d) を経ても生きている。証跡:

1. **H-1 (PR #124)** — `Supervisor.attach_exit_gate` で `_ExitGateAttachment(supervisor=self, ...)` を組み立て、`run_exit_gate_tick` が `run_exit_gate(supervisor=self, ...)` に転送するよう新設。これで `AccountTypeMismatchRuntime` の発火点が `run_exit_gate` 側に移った。
2. **H-3b (PR #127)** — 旧 ExitExecutor 上で pin されていた safe_stop wiring 契約 (canonical reason / payload キーセット / supervisor 失敗時の例外伝播) を `run_exit_gate` 経由 test として再 pin。
3. **H-3c final (PR #129)** — ExitExecutor 削除。SafeStop 関連 test は H-3b 時点で全て `run_exit_gate` 経由に移っているため、削除で配線が壊れないことが test green で証明。
4. **M-3b (PR #135)** — Supervisor の `_ExitGateAttachment` を QuoteFeed ベースに rewire したが `supervisor=self` 部分は **逐語保持**。
5. **M-3c (PR #136)** — stale gate 追加。`emergency_stop` bypass を導入したが `supervisor=self` 配線・SafeStop trigger 経路は **不変**。
6. **M-3d (PR #139)** — producer 追加のみ。Supervisor / `run_exit_gate` のシグネチャは **完全に未変更**。SafeStop 配線への影響ゼロ。

`tests/unit/test_exit_executor_safe_stop_wiring.py` (旧名のまま `run_exit_gate` を呼ぶ) と `tests/integration/test_supervisor_exit_gate_wiring.py` が回帰テストとして常時 green。

---

## 7. QuoteFeed が live OANDA producer まで接続されたこと

M-3 シリーズの到達経路を 1 行ずつ振り返る:

| ステージ | DTO | Protocol | adapter | consumer | stale gate | producer |
|---|---|---|---|---|---|---|
| M-3a (#134) | ✅ `Quote` | ✅ `QuoteFeed` | ✅ `callable_to_quote_feed` | (未着手) | (未着手) | (未着手) |
| M-3b (#135) | ✅ | ✅ | ✅ | ✅ `run_exit_gate` / `Supervisor.attach_exit_gate` rewire | (未着手) | (未着手) |
| M-3c (#136) | ✅ | ✅ | ✅ | ✅ | ✅ 60s + `emergency_stop` bypass + `noop_stale_quote` | (未着手) |
| **M-3d (#139)** | **✅** | **✅** | **✅** | **✅** | **✅** | **✅ `OandaQuoteFeed` (REST polling)** |

**現状: live OANDA データを `Quote(price, ts, source)` として返す producer が存在する。`Supervisor.attach_exit_gate(quote_feed=OandaQuoteFeed(...))` を呼ぶだけで実 runtime 接続が完了する状態。**

接続が **意図的に未実施** な理由は §5.2 冒頭参照 (1 PR = 1 責務遵守 + Protocol 互換のため接続コストは極小)。

---

## 8. 旧 closure memo (#138) 時点で未着手だった M-3d が完了したこと

| 観点 | #138 時点 | #139 (M-3d) 後 |
|---|---|---|
| `adapters/price_feed/` sub-package | 存在しない | 新設 (M-3d) |
| `OandaQuoteFeed` クラス | 存在しない | 実装 (~125 LoC) |
| `OandaQuoteFeedError` クラス | 存在しない | 実装 (parse error 専用) |
| `OandaQuoteFeed` の test 数 | 0 | 15 (unit 13 + integration 2) |
| `OandaAPIClient.get_pricing` の production caller | 0 (定義のみで未使用) | 1 (`OandaQuoteFeed.get_quote`) |
| #138 §7 の M-3d 候補 | 「次候補」として記載 | **本メモ §2.2 / §5.1 で「✅ 解消」へ移動** |
| Master tip | `3122cee` | `0a9e071` (差分: M-3d 4 ファイル +444 行 / -0 行) |

#138 §7 にあった "M-3 closure §6 解凍チェックリスト確認" は M-3d 着手時 (本セッション内) に消化済。具体的には:

- ✅ M-3 closure memo (#137) §6 を読み直してから M-3d ブランチを切った
- ✅ `OandaAPIClient.get_pricing` が production 未使用であることを確認 (clean attach point)
- ✅ `Quote.ts` を `clock.now()` に汚染しないことを test で pin (`test_ts_is_parsed_from_oanda_time_field_not_clock`)
- ✅ Supervisor wiring を **意図的に未実施** で 1 PR = 1 責務維持
- ✅ `callable_to_quote_feed` adapter を温存 (back-compat)

---

## 9. 次候補（判断材料のみ — 着手指示ではない）

> **重要**: 以下は M9 完全クローズ後に「自然に次にあり得る方向」を判断材料として並べただけのもの。本 PR は docs-only であり、いずれにも着手しない。pickup には明示指示が必要。

| 候補 | 性質 | 前提 | 想定スコープ |
|---|---|---|---|
| **`OandaQuoteFeed` の Supervisor 接続** | 機能配線 | M-3d producer が実装済 (本メモで確認済) | `Supervisor.attach_exit_gate(quote_feed=OandaQuoteFeed(...))` の callsite 1 箇所変更 + integration test 1 本。Protocol 互換のため producer 側変更ゼロ |
| **net pnl 化** (M-2 の延長) | 機能追加 | OANDA transactions detail 取得経路の整備 | `run_exit_gate` 直後 or 下流で fees / spread を引いた net 値に置換 (gross と net の二項目化も選択肢) |
| **OANDA streaming producer (`PricingStream`)** | 機能追加 | live REST producer (M-3d) を実 runtime で運用観察 | producer 別実装 + `Quote.source = SOURCE_OANDA_LIVE`。callsite 不触 (Protocol 互換) |
| **`stale_max_age_seconds` の `app_settings` 化** | config 整備 | live producer Supervisor 接続後に運用負荷の実測 | schema 追加 + seed + Supervisor 経由の注入。早期着手は additive 性を崩すため非推奨 |
| **stale 発火 metrics 化** | 観測性 | ExitFireMetricsService の拡張余地 | read-only service として別 PR |
| **OANDA quote feed / stale gate の operator runbook** | docs | live runtime での発火事例蓄積 | `docs/runbook/` 配下に triage 手順を追加 |

判断軸:
- **緊急性**: Supervisor 接続 > net pnl > その他。Supervisor 接続は producer 実装済の状態を実 runtime に届ける唯一の残作業のため。
- **additive 安全性**: Supervisor 接続 / metrics / runbook / streaming producer は完全 additive。`app_settings` 化のみ schema 変更を伴う。
- **依存関係**: metrics / runbook は Supervisor 接続後でないと実 runtime で発火しない。streaming は polling 運用観察後に判断する方が情報量が高い。

---

## 10. 参考リンク

### 10.1 シリーズ memory files (M-3d 追加版)

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
- M9 中間 closure (#138): `memory/project_m9_closure_memo_merged.md`
- **M-3d (#139): `memory/project_m9_m3d_merged.md`**

### 10.2 関連 docs

- M-3 シリーズ単独 closure: `docs/design/m3_quote_feed_migration_closure_memo.md` (#137)
- M9 中間 closure: `docs/design/m9_exit_improvements_closure_memo.md` (#138)
- 6.9 series rollup: `docs/design/cycle_6_9_summary.md`
- ExitFireMetricsService runbook: `docs/runbook/exit_fire_metrics.md`
- Phase 6 paper operator checklist: `docs/runbook/phase6_paper_operator_checklist.md`

### 10.3 関連ソース

- `src/fx_ai_trading/services/exit_gate_runner.py` — `run_exit_gate` 本体 (M9 の集積点)
- `src/fx_ai_trading/supervisor/supervisor.py` — `attach_exit_gate` / `run_exit_gate_tick`
- `src/fx_ai_trading/services/state_manager.py` — `on_close` / `open_position_details`
- `src/fx_ai_trading/domain/price_feed.py` — `Quote` / `QuoteFeed` / `callable_to_quote_feed`
- **`src/fx_ai_trading/adapters/price_feed/oanda_quote_feed.py` — `OandaQuoteFeed` / `OandaQuoteFeedError` (M-3d で新設)**
- `src/fx_ai_trading/adapters/broker/oanda_api_client.py` — `get_pricing` (M-3d で初の production caller を獲得)
- `src/fx_ai_trading/domain/exit.py` — `ExitDecision`
- `src/fx_ai_trading/domain/state.py` — `OpenPositionInfo`

### 10.4 関連テスト

- `tests/unit/test_exit_gate_runner.py` (M-1 / M-2 / M-3 全 acceptance テスト)
- `tests/unit/test_exit_executor_safe_stop_wiring.py` (旧名のまま — 中身は `run_exit_gate` 経由 SafeStop 契約)
- `tests/integration/test_supervisor_exit_gate_wiring.py` (H-1 / M-3b 配線テスト)
- `tests/unit/test_quote_feed.py` (M-3a Quote / QuoteFeed / adapter)
- `tests/contract/test_exit_event_fsm.py` (H-2 で migration 済 FSM contract)
- **`tests/unit/test_oanda_quote_feed.py` (M-3d producer unit, 13 tests)**
- **`tests/integration/test_oanda_quote_feed_pricing.py` (M-3d producer integration, 2 tests)**
