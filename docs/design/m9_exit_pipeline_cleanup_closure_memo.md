# M9 Exit Pipeline Cleanup — Closure Memo

> **目的**: M9 で実施した exit pipeline cleanup（H-1 / H-2 / H-3）が何を解消し、何を解消していないかを 1 ページで棚卸しする。
> **位置付け**: 完了済み実装の closure memo。次候補（M-1 / M-2 / M-3）は別 milestone のスコープを定義しているだけで、本メモには着手判断は含めない。
> **読者**: M-1 以降に着手する開発者 / Phase 7 で `side` / `pnl_realized` / `price_feed` Protocol を解凍する実装者 / M12 main loop の所有者。

---

## 1. 背景 — なぜ M9 が必要だったか

Cycle 6.7d / I-09 で `StateManager.on_close` が「positions + close_events + secondary_sync_outbox を 1 トランザクションで書く唯一の close 経路」として確立された。一方で、

- `src/fx_ai_trading/services/exit_executor.py`（旧 `ExitExecutor` クラス）は `CloseEventsRepository.insert` を直接呼ぶ古い書き経路として `src/` に残置されていた。
- production caller は `ExitExecutor` をすでに使っていなかったが、テスト 4 ファイル（contract / integration / unit / smoke）が `ExitExecutor.execute(...)` を直接呼んでおり、FSM truth / E2E truth / SafeStop wiring truth が deprecated path に乗っていた。
- そのため `pytest -W error::DeprecationWarning` を有効化すると `ExitExecutor` 由来の warning でテストが落ち、deprecation 期限を切れない状態だった。
- M9 review（H-1 着手前）の `git grep` で `run_exit_gate` の production caller が **0 件**（Supervisor 側に呼び出し seam が無い）であることも確認された。

M9 の goal はこれらを順序立てて解消すること:

1. Supervisor 側の cadence seam を作る（M12 main loop が tick で叩けるように）
2. テスト truth を `run_exit_gate` 側に移す
3. `ExitExecutor` を物理削除する

---

## 2. H-1 / H-2 / H-3 で何を解消したか

### 2.1 H-1 — Supervisor cadence seam

**解消した問題**: `run_exit_gate` の production caller が 0 件。M12 main loop からこの関数を tick 単位で呼び出す手段が無かった。

**追加した seam**（`src/fx_ai_trading/supervisor/supervisor.py`）:

- `attach_exit_gate(...)` — broker / state_manager / exit_policy / price_feed / side / tp / sl / context を 1 つの不変 attachment snapshot として保持。再 attach は前の snapshot を置換。
- `run_exit_gate_tick() -> list[ExitGateRunResult]` — 内部ループは持たない。caller 駆動。未 attach または `_is_stopped` のとき `[]` を返して no-op（`record_metrics` と同じ pattern）。
- `supervisor=self` を `run_exit_gate(...)` に転送 → 既存 PR-5 / U-2 の `AccountTypeMismatchRuntime → trigger_safe_stop` callback を再利用。

**設計判断**:

- pattern は `attach_metrics_loop` / `record_metrics` と完全一致（caller-driven, no internal loop）。M9 / M12 の責務分離（Supervisor は loop を持たない）を維持。
- tick 例外は伝播する（`run_exit_gate` 契約に追従、`record_metrics` のような fail-open ではない）。`AccountTypeMismatchRuntime` は safe_stop 起動 → 再 raise。
- side default は `"long"`（Cycle 6.7c E2 paper-mode 制約に合わせる）。Phase 7 / M-1 で orders 表から派生させる。

**影響範囲**: 2 ファイルのみ（`supervisor.py` +125 / `tests/integration/test_supervisor_exit_gate_wiring.py` +254 / 15 tests）。SafeStop / notifier / G-2 / G-3 / dispatcher / health / `exit_gate_runner.py` / contract test / alembic 全て diff ゼロ。

### 2.2 H-2 — FSM contract suite migration

**解消した問題**: `tests/contract/test_exit_event_fsm.py`（12 tests）が `ExitExecutor.execute(...)` を直接呼んでいた → FSM truth が deprecated path 上にあった。

**移行**（tests-only / 1 ファイル / -176 / +210）:

- `ExitExecutor.execute(...)` → `run_exit_gate(...)`
- `CloseEventsRepository.insert(...)` → `StateManager.on_close(...)`
- 戻り値 `OrderResult` → `list[ExitGateRunResult]`（`closed` / `noop`）

**契約は 1:1 で保存**:

- no-exit decision → broker 未呼び出し / on_close 未呼び出し
- exit decision → broker.place_order が **OPPOSITE side** で原 size_units / 同 account / 同 instrument 1 回 → `state_manager.on_close` が `order_id` / `primary_reason_code` / `reasons[*].reason_code` を伴って 1 回

**未着手で残したもの**: `ExitExecutor` 削除は H-3c に持ち越し（先に残り 8 テストを移す必要があったため）。

### 2.3 H-3 — 残り 8 テスト移行 + ExitExecutor 物理削除

| Sub-step | 対象 | 種別 | 備考 |
|---|---|---|---|
| H-3a | `tests/integration/test_exit_flow.py`（2 tests）| tests-only | 実 DB を使う E2E。`_seed_open_position(engine, *, order_id)` で per-test seeding（`run_exit_gate` は `state_manager.open_position_details()` から position を読むため）。teardown は新書き経路（`secondary_sync_outbox` / `close_events` / `positions`）を全部含めるように拡張。 |
| H-3b | `tests/unit/test_exit_executor_safe_stop_wiring.py`（5 tests）| tests-only | PR-5 / U-2 SafeStop wiring 契約を `run_exit_gate` 側に移植。payload key 集合 `{actual_account_type, expected_account_type, instrument, client_order_id, detail}` を pin。`expected_account_type=None` は `run_exit_gate` 固有（per-call expected を持たない、`detail` に str(exc) で全捕捉）。 |
| H-3c (1/2) | `tests/integration/test_paper_smoke_end_to_end.py`（1 test, Stage 7）| tests-only | 7-stage smoke の Stage 7 のみ書き換え。real `ExitPolicyService` + real `PaperBroker` + mocked `StateManager`（ちょうど fill した position を 1 件 seed）。in-memory sqlite engine + `_CLOSE_EVENTS_DDL` + `CloseEventsRepository` を撤去 → smoke は self-contained に。 |
| H-3c (2/2) | `src/fx_ai_trading/services/exit_executor.py` 削除 + 5 stale-reference docstring 修正 | src deletion + docs | 168 行を物理削除。`exit_gate_runner.py` の E1 design note は「ExitExecutor is NOT used」という対比から「StateManager.on_close が単一原子書き経路である」という直接記述に rewrite（挙動変更なし）。4 テスト docstring の "intentionally left in tree until X deletes it" → "was subsequently removed in M9/H-3c" 過去形化。 |

**全 H-3 共通の不変条件**:

- migration mapping は 1:1 で保存（`OrderResult` の `status=='filled'` → `outcome=='closed'`、`result is None` → `outcome=='noop'`）。
- StateManager append-only contract 自身は `tests/integration/test_state_manager*` で別途担保 → 移行先テストでは「pipeline reaches the close write exactly once with `primary_reason_code=...`」だけを pin。
- Production code（`run_exit_gate` / `Supervisor` / SafeStop / Notifier）は H-3c (2/2) の `exit_executor.py` 削除と E1 docstring 書き換え以外は一切触っていない。

---

## 3. run_exit_gate が唯一の exit 実行経路になったこと

M9 完了時点で:

- `src/` 配下に `exit_executor.py` は **存在しない**（PR #129 で物理削除、master tip `54dfe12`）。
- `git grep "from fx_ai_trading.services.exit_executor"` / `import.*ExitExecutor` / `ExitExecutor(` は `src/` および `tests/` で **0 件**（egg-info `SOURCES.txt` は build 自動生成 / untracked）。
- 取引閉鎖の DB 書き経路は `StateManager.on_close` 単一（positions + close_events + secondary_sync_outbox を 1 トランザクションで原子的に書く）。
- exit 実行のエントリポイントは `services/exit_gate_runner.py::run_exit_gate(...)` 単一。caller は:
  - production: `Supervisor.run_exit_gate_tick()`（H-1 で追加された seam、tick 駆動）
  - test: `tests/contract/test_exit_event_fsm.py` / `tests/integration/test_exit_flow.py` / `tests/integration/test_paper_smoke_end_to_end.py` / `tests/unit/test_exit_executor_safe_stop_wiring.py` / `tests/integration/test_supervisor_exit_gate_wiring.py` / `tests/unit/test_exit_gate_runner*`

`run_exit_gate` の挙動契約（M9 で新規追加した契約は無く、すべて Cycle 6.7c で確立済み）:

- `state_manager.open_position_details()` から open position 一覧を取得
- 各 position について `exit_policy.evaluate(...)` を呼び、`should_exit=False` なら `ExitGateRunResult(outcome='noop')` を append（broker 未呼び出し / on_close 未呼び出し）
- `should_exit=True` なら `OrderRequest(side=OPPOSITE)` で `broker.place_order(...)`、`status=='filled'` なら `state_manager.on_close(...)` を呼んで `outcome='closed'` を append、それ以外は `outcome='broker_rejected'`

---

## 4. ExitExecutor 廃止完了の整理

| 項目 | 状態 |
|---|---|
| `src/fx_ai_trading/services/exit_executor.py` | 削除済み（PR #129、master `54dfe12`）|
| `services/__init__.py` 等での re-export | もともと無し（self-contained leaf module）|
| production の import / instantiate | 0 件（M9 着手前から） |
| test の import / instantiate | 0 件（H-2 / H-3a / H-3b / H-3c-1 で順次移行） |
| `pytest -W error::DeprecationWarning` での `ExitExecutor` 由来 warning | 0 件 |
| 物理ファイル / ディレクトリ残骸 | 0 件 |
| 「ExitExecutor は H-3 で消す」と未来形で約束していた docstring | 5 ファイル（src 1 + tests 4）すべて過去形に修正済み（PR #129） |

`ExitExecutor` という名前は M9 期間中だけ「テストファイル名」に残っていたが（`tests/unit/test_exit_executor_safe_stop_wiring.py`）、これは PR 粒度を small に保つための一時的な妥協であり、リネームは別 PR で必要に応じて拾う（このメモでは scope 外）。

---

## 5. PR 対応表（#124〜#129）

| H | PR | merge commit | 種別 | 対象ファイル | 主責務 |
|---|---|---|---|---|---|
| H-1 | [#124](https://github.com/yukikurisu1990-gh/fx-ai-trading/pull/124) | `765013f` | src + test | `supervisor/supervisor.py` (+125), `tests/integration/test_supervisor_exit_gate_wiring.py` (+254 / 15 tests) | Supervisor cadence seam（`attach_exit_gate` / `run_exit_gate_tick`）。`supervisor=self` で PR-5 / U-2 SafeStop callback を再利用。 |
| H-2 | [#125](https://github.com/yukikurisu1990-gh/fx-ai-trading/pull/125) | `753e9a9` | tests-only | `tests/contract/test_exit_event_fsm.py` (-176 / +210) | FSM contract（12 tests）を `ExitExecutor` → `run_exit_gate` に移行。`ExitExecutor` 削除はせず。 |
| H-3a | [#126](https://github.com/yukikurisu1990-gh/fx-ai-trading/pull/126) | `5d19993` | tests-only | `tests/integration/test_exit_flow.py` (+153 / -69) | E2E exit-flow（2 tests）を移行。per-test seed + 新書き経路の teardown 拡張。 |
| H-3b | [#127](https://github.com/yukikurisu1990-gh/fx-ai-trading/pull/127) | `328dd1b` | tests-only | `tests/unit/test_exit_executor_safe_stop_wiring.py` (+121 / -75) | PR-5 / U-2 SafeStop wiring（5 tests）を移行。payload key 集合 + `expected_account_type=None` を pin。 |
| H-3c (1/2) | [#128](https://github.com/yukikurisu1990-gh/fx-ai-trading/pull/128) | `571d21f` | tests-only | `tests/integration/test_paper_smoke_end_to_end.py` (+67 / -43) | 7-stage smoke の Stage 7 を移行。in-memory sqlite + `_CLOSE_EVENTS_DDL` + `CloseEventsRepository` を撤去。 |
| H-3c (2/2) | [#129](https://github.com/yukikurisu1990-gh/fx-ai-trading/pull/129) | `54dfe12` | src deletion + docs | `services/exit_executor.py` (-168), `services/exit_gate_runner.py` (E1 docstring 6 行), 4 テスト docstring | `ExitExecutor` 物理削除。stale-reference cleanup（挙動変更なし）。 |

**Master tip after M9 H-1..H-3:** `54dfe12`。

**全 6 PR で守った制約**: 1 PR = 1 責務 / production 挙動ゼロ影響（H-1 の Supervisor 追加 seam を除き、すべて caller-driven 経路追加 or テスト/docstring 書き換え）/ schema 変更ゼロ / SafeStop / notifier / G-2 / G-3 / dispatcher / health / alembic 不触 / CI 完全 green / pre-existing flake（`tests/unit/test_notifier_factory.py::TestC1SilentSkipUnconfiguredChannels::test_unconfigured_channel_emits_warning_log`）は M9 起因ではなく clean master でも 1 failed/1523 passed が同一再現。

---

## 6. 解消済み / 未解消の整理

### 6.1 解消済み

- **deprecated path 残置**: `ExitExecutor` クラスは物理削除。`pytest -W error::DeprecationWarning` で `ExitExecutor` 由来 warning ゼロ。
- **FSM truth が deprecated path 上**: H-2 で `run_exit_gate` 側に移行済み。
- **E2E truth が deprecated path 上**: H-3a / H-3c (1/2) で `run_exit_gate` 側に移行済み。
- **SafeStop wiring truth が deprecated path 上**: H-3b で `run_exit_gate` 側に移行済み。
- **production caller が `run_exit_gate` を tick で叩く手段が無い**: H-1 で `Supervisor.run_exit_gate_tick()` seam を追加済み。
- **stale "ExitExecutor は H-3 で消す" docstring**: PR #129 で 5 箇所すべて過去形に修正済み。

### 6.2 未解消（M9 scope 外、別 milestone）

- **side が paper-mode 固定（"long"）**: `Supervisor.attach_exit_gate(side="long")` がデフォルト。Cycle 6.7c E2 制約。Phase 7 で orders 表から派生させる必要がある（後述 M-1）。
- **`pnl_realized` が常に `None`**: `state_manager.on_close(..., pnl_realized=None)` 固定。`run_exit_gate` は fill_price / avg_price から計算しない（Cycle 6.7c E3）。Phase 7 で価格データが authoritative になった時点で導出する必要がある（後述 M-2）。
- **`price_feed` が plain `Callable[[str], float]`**: Cycle 6.7c E4 で「Protocol wrapper は 6.7c では使わない」と決めた。caller / test が lambda を inject。Phase 7 で複数 price source を抽象化する必要があれば Protocol 化する（後述 M-3）。
- **M12 main loop が `Supervisor.run_exit_gate_tick()` を実際に tick で呼んでいない**: H-1 で seam を作っただけで、loop owner は別 milestone（M12）。M9 scope 外。
- **partial close / scale-in / scale-out / position_id**: Cycle 6.7c L2 で「order_id を logical position identity とし、partial close は Phase 7 scope」と決めた。M9 では一切触らない。

---

## 7. M-1 / M-2 / M-3 — 次候補（未着手 / 着手判断は別途）

> **注意**: 本メモは scope 定義のみ。M-1 着手の Go/No-Go は別途意思決定する。

### M-1 — `side` を orders 表から派生

**目的**: `Supervisor.attach_exit_gate(side="long")` のような default を撤去し、open position ごとに正しい side を取得できるようにする（short ポジションの正しい close）。

**現状**:

- `services/exit_gate_runner.py::run_exit_gate(side: str = "long", ...)` は call 引数で 1 つの side を受け取り、`_CLOSE_SIDE: dict[str, str] = {"long": "short", "short": "long"}` で OPPOSITE を導出。
- `state_manager.open_position_details()` が返す `OpenPositionInfo` は現在 side を含まない。
- paper-mode では long-only なので問題なかったが、Phase 7 / live で破綻する。

**スコープ案**（実装はしない）:

- `OpenPositionInfo` に `side` フィールドを追加 or 別経路で orders 表から派生
- `run_exit_gate` が per-position の side を使うように
- `Supervisor.attach_exit_gate` の `side` 引数の扱いを再設計（default 撤去 / per-position 派生）

**影響範囲（推定）**: `domain/state.py` / `services/exit_gate_runner.py` / `services/state_manager.py` / `supervisor/supervisor.py` / 関連テスト全件。

### M-2 — `pnl_realized` 計算

**目的**: close 時に realized P&L を `state_manager.on_close(..., pnl_realized=...)` に渡せるようにする（現状は `None` 固定）。

**現状**:

- `services/exit_gate_runner.py` は `pnl_realized=None` で `state_manager.on_close` を呼ぶ（Cycle 6.7c E3）。
- broker `OrderResult.fill_price` と `OpenPositionInfo.avg_price` は揃っているが、まだ authoritative ではない（paper / mock のみで保証）。
- close_events / positions テーブルには列はある（書き込まれていないだけ）。

**スコープ案**（実装はしない）:

- `OrderResult.fill_price` の authoritativeness を確認（live broker 含めて）
- `_realized_pl(side, units, avg_price, fill_price)` ヘルパを `run_exit_gate` 内に追加
- 単位 / 通貨 / pip 換算を含めた検算（accounts.base_currency / instruments.pip_location 参照）
- 関連テスト追加（unit / integration / contract）

**影響範囲（推定）**: `services/exit_gate_runner.py` / `domain/broker.py`（OrderResult contract 確認）/ 関連テスト全件。schema 変更は無い見込み（列は既存）。

### M-3 — `price_feed` Protocol 化

**目的**: `Callable[[str], float]` から Protocol に上げ、複数の price source（real-time tick / cached / fallback）を切替可能にする。

**現状**:

- `services/exit_gate_runner.py::run_exit_gate(price_feed: Callable[[str], float], ...)`（Cycle 6.7c E4）。
- caller / test が lambda を inject。
- Phase 7 で OANDA tick / 内部 cache / fallback の切替が必要になれば Protocol 化が望ましい。

**スコープ案**（実装はしない）:

- `domain/price.py`（または `domain/market_data.py`）に `PriceFeed(Protocol)` を定義
- `get_price(instrument: str, *, as_of: datetime | None = None) -> float` を要件にするか、互換のため `__call__(instrument: str) -> float` を残すか検討
- `Supervisor.attach_exit_gate(price_feed=...)` の型を Protocol に
- adapters（OANDA / paper / fallback）と paper-mode integration test 整備

**影響範囲（推定）**: `services/exit_gate_runner.py` / `supervisor/supervisor.py` / 新規 adapter ファイル / 関連テスト全件。schema 変更は無い見込み。

### M-1 / M-2 / M-3 の依存関係

- M-1 は M-2 の前提（side を間違えると pnl の符号が反転する）
- M-2 は schema 変更を含まない見込み（列既存）/ M-1 後に着手するのが無難
- M-3 は M-1 / M-2 と独立（並走可能）が、M-2 で `as_of` 引数が要るなら M-3 を先に上げた方が綺麗

---

## 8. SafeStop 配線が run_exit_gate 側で維持されていることを再確認

PR-5 / U-2（phase6_hardening §6.18 / operations F14）の wiring が M9 完了後も次のとおり成立していることを確認:

### 8.1 配線の所在

- 実装: `src/fx_ai_trading/services/exit_gate_runner.py::run_exit_gate(...)` の `try: broker.place_order(close_request) except AccountTypeMismatchRuntime as exc:` ブロック（行範囲は M9 期間中変更なし）。
- 配線契約は `run_exit_gate` の引数 `supervisor: Supervisor | None = None` 経由で外部から差し込む形（`supervisor=None` のときは re-raise のみ、wired のときは `supervisor.trigger_safe_stop(reason="account_type_mismatch_runtime", occurred_at=now, payload=payload)` を呼んでから re-raise）。

### 8.2 Supervisor 側の自動 wiring

- `Supervisor.run_exit_gate_tick()`（H-1 で追加）が `run_exit_gate(..., supervisor=self)` を渡す（H-1 PR #124 のコードで明示）。
- 結果として、Supervisor 経由で tick が回っていれば SafeStop は自動で wired。

### 8.3 Pin しているテスト

- `tests/unit/test_exit_executor_safe_stop_wiring.py`（H-3b で `run_exit_gate` 側に移行）— 5 tests:
  - `test_no_supervisor_propagates_exception_unchanged` — supervisor 未指定でも `AccountTypeMismatchRuntime` がそのまま伝播 / on_close 未呼び出し
  - `test_supervisor_triggers_safe_stop_with_canonical_reason` — `reason='account_type_mismatch_runtime'` / `occurred_at=now` / payload key 集合 = `{actual_account_type, expected_account_type, instrument, client_order_id, detail}` / `expected_account_type=None` / `detail` に actual と expected の両方の文字列を含む
  - `test_supervisor_wired_does_not_write_close_event` — wired でも `on_close` は呼ばれない
  - `test_supervisor_trigger_safe_stop_failure_does_not_swallow_original` — supervisor 側の例外で原 `AccountTypeMismatchRuntime` が swallowed されない（`contextlib.suppress(Exception)` で守られている）
  - `test_should_exit_false_short_circuits_before_broker` — `should_exit=False` のときは broker 未呼び出し / supervisor 未呼び出し / on_close 未呼び出し
- `tests/integration/test_supervisor_exit_gate_wiring.py`（H-1 で追加）— Supervisor 側から見た wiring の振る舞いも別途 pin。

### 8.4 不変条件のサマリ

| 項目 | 値 / 出典 |
|---|---|
| canonical reason | `"account_type_mismatch_runtime"`（`run_exit_gate` 内 hardcoded、テスト pin あり）|
| payload key 集合 | `{actual_account_type, expected_account_type, instrument, client_order_id, detail}` |
| `expected_account_type` | 常に `None`（`run_exit_gate` は per-call expected を持たない、`detail` に `str(exc)` で全捕捉） |
| 例外の伝播 | safe_stop 起動の成否に関わらず、原 `AccountTypeMismatchRuntime` を re-raise |
| safe_stop 自身が落ちた場合 | `contextlib.suppress(Exception)` で握り、原例外を優先伝播 |
| close_event 書き込み | mismatch 経路では絶対に呼ばない（`state_manager.on_close` 未呼び出し） |
| 残ポジション処理 | for-loop は raise で打ち切り、untrusted broker に対する評価を続行しない |

### 8.5 SafeStop / Notifier / G-2 / G-3 の不触保証

- M9 期間中（PR #124〜#129）に修正したファイルは:
  - `src/fx_ai_trading/supervisor/supervisor.py`（H-1 のみ、seam 追加）
  - `src/fx_ai_trading/services/exit_gate_runner.py`（H-3c (2/2) のみ、E1 docstring 書き換え 6 行 / 挙動変更なし）
  - `src/fx_ai_trading/services/exit_executor.py`（H-3c (2/2) のみ、ファイル削除）
  - テスト 6 ファイル（H-1 / H-2 / H-3a / H-3b / H-3c (1/2) / H-3c (2/2)）
- `src/fx_ai_trading/supervisor/safe_stop.py` / `notifier_factory.py` / `dispatcher.py` / `health.py` / `alembic/` は **6 PR を通じて diff ゼロ**。
- したがって PR-5 / U-2 SafeStop 配線は `run_exit_gate` 側にあり続け、M9 期間中に挙動変更は一切ない。

---

## 9. 参考リンク

- PR #124: <https://github.com/yukikurisu1990-gh/fx-ai-trading/pull/124>（H-1）
- PR #125: <https://github.com/yukikurisu1990-gh/fx-ai-trading/pull/125>（H-2）
- PR #126: <https://github.com/yukikurisu1990-gh/fx-ai-trading/pull/126>（H-3a）
- PR #127: <https://github.com/yukikurisu1990-gh/fx-ai-trading/pull/127>（H-3b）
- PR #128: <https://github.com/yukikurisu1990-gh/fx-ai-trading/pull/128>（H-3c 1/2）
- PR #129: <https://github.com/yukikurisu1990-gh/fx-ai-trading/pull/129>（H-3c 2/2）
- 関連 design memo: `docs/design/cycle_6_9_supervisor_loop_memo.md`（supervisor loop 接続点契約 / M8 / M9 着手時に再評価する点を pin）
- 関連 design memo: `docs/design/cycle_6_9_summary.md`（Cycle 6.9 / 6.10 シリーズ棚卸し）
