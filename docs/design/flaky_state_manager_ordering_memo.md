# Design Memo — StateManager 順序決定性 (Cycle 6.12)

> **ステータス**: 調査完了 + 修正適用済 (2026-04-22, F-2 Step 1 = PR #109 reproduction, F-2 Step 2 = 方針 B 採用 / 本ブランチ).
> **作成契機**: PR #107 (Cycle 6.11) CI 初回で `test_fill_after_close_writes_open_not_add` が FAIL → rerun で green。全体俯瞰レビュー (2026-04-22) の Runtime Auditor サブエージェント調査により「テスト汚染ではなく、本番コードの順序決定性に起因する可能性」が指摘された。
> **更新履歴**:
>   - 2026-04-22 初版 (PR #108 Cycle 6.12) — 仮説 R-1/R-2/R-3 と修正方針 A/B/C を提示。
>   - 2026-04-22 F-2 Step 1 (PR #109) — 再現テスト追加で R-1 を実バグとして確定。
>   - 2026-04-22 F-2 Step 2 (本 PR) — 方針 B を採用、3 site の ORDER BY を順序非依存 query に置換。

---

## 1. 目的 / スコープ

- **目的**: flaky test の挙動と、その根本原因候補を、次セッション以降の調査者 (人間監督モード) が再現・検証できる形で保存する
- **スコープ**: `state_manager.open_instruments()` の ORDER BY tie-break 仕様、および `on_fill()` の `event_type` 決定ロジック周辺
- **非スコープ**: 修正方針の決定、実コード変更、テスト変更

---

## 2. 現象

### 2.1 対象テスト

- `tests/unit/test_state_manager_write.py::TestOnFill::test_fill_after_close_writes_open_not_add`

### 2.2 失敗メッセージ

```text
AssertionError: assert 'add' == 'open'
```

### 2.3 再現観測 (2026-04-22)

| 実行パターン | 結果 |
|---|---|
| CI full suite (PR #107 1 回目) | **FAIL** |
| CI full suite (rerun) | PASS |
| ローカル isolated — branch | 初回 FAIL, 2 回目 PASS |
| ローカル isolated — master | PASS |
| ローカル full suite (1377 tests) on branch | 全 PASS |

**特徴**: 明確な原因行動 (ファイル変更・依存追加) と結び付かず、rerun で通る典型的 flaky パターン。ただし**ランダム失敗ではなく、ある条件で決定的に失敗する**可能性が高い (§4 参照)。

---

## 3. テストが検証する契約

`close` 後に同一 instrument で再 `fill` が発生した場合、新しい fill は `event_type='open'` として記録されるべき (pyramiding 時の `event_type='add'` ではない)。

関連分岐:

- `src/fx_ai_trading/state/state_manager.py` 周辺の `on_fill()` 内:
  ```python
  existing = self.open_instruments()
  event_type = "add" if instrument in existing else "open"
  ```
- 判定の正しさは **`open_instruments()` が close 後に空集合を返すこと**に依存する。

---

## 4. 非決定性の候補 (証拠付き)

> Runtime Auditor 調査による。確度順に列挙。**いずれも仮説であり、未検証**。

### 4.1 候補 R-1 — window function DESC tie-break (確度: **High**)

**証拠:**
- `src/fx_ai_trading/state/state_manager.py:156-157` 付近 — `open_instruments()` 内で
  ```sql
  ORDER BY event_time_utc DESC, position_snapshot_id DESC
  ```
  の tie-break を使用 (要再確認、行番号は 2026-04-22 時点の読み値)
- `src/fx_ai_trading/common/ulid.py:43` 付近 — `ts_ms = int(time.time() * 1000)` のミリ秒精度
- テスト側 `FixedClock` が 3 回の fill 呼び出しで**同一 datetime を返す** (`clock.py:54-58`)

**メカニズム仮説:**
- `on_fill()` → `on_close()` → `on_fill()` の 3 イベントが全て同一ミリ秒の `event_time_utc` を持つ
- tie-break は `position_snapshot_id DESC` (ULID) 比較に落ちる
- ULID のミリ秒プレフィックスも同一のため、**末尾 80bit のランダムサフィックス**が順序を決定
- 結果: `open_instruments()` が直近イベントとして「close 行」を返すか「再 open 行」を返すかが**ランダム化**
- close 行が最新と判定されれば `event_type='open'` (PASS), 直近 fill 行が最新と判定されれば `instrument in existing=True` → `event_type='add'` (FAIL)

**落ちやすさ評価:** High — CI 環境では複数 INSERT が同一ミリ秒内で高確率発生。ローカルでは実行速度変動で再現率低。

### 4.2 候補 R-2 — トランザクション分離レベル × 接続プール (確度: **Medium**)

**証拠:**
- `state_manager.py:166` 付近 — `with self._engine.connect() as conn:` でクエリ毎に独立接続
- `on_close()` は `with self._engine.begin() as conn:` トランザクション境界
- `enqueue.py:127-128` — `enqueue_secondary_sync()` が別トランザクションを開く可能性

**メカニズム仮説:**
- on_fill() が on_close() の commit 前に close 行を見逃す読み取り分離
- SQLite デフォルト (DEFERRED) では通常問題ないが、I/O 遅延 × 接続再利用の組み合わせで observable race が出うる

**落ちやすさ評価:** Medium — CI ディスク I/O 競合時にタイミング一致の可能性。

### 4.3 候補 R-3 — FixedClock キャッシング (確度: **Low**)

**証拠:**
- `common/clock.py:54-58` — `FixedClock._dt` を保持、常に同一値返却
- `on_fill()` 内で `now = self._clock.now()` を一度だけ取得

**メカニズム仮説:**
- フィクスチャ / connection pool 層での暗黙キャッシュが `open_instruments()` の戻り値を汚染する可能性

**落ちやすさ評価:** Low — コード上に明示的キャッシュ機構は未発見 (`engine.connect()` は毎回新規)。排除はできない程度。

---

## 5. 本番影響評価 (最重要)

**本 flaky test は単なるテスト課題ではなく、本番コードの決定性バグ候補である**。

### 5.1 なぜ paper では顕在化していないか

- paper 低頻度取引では `on_close()` → 同一 instrument の即 `on_fill()` が 1 ミリ秒以内に起きにくい
- OANDA broker 応答の往復時間 (通常 50–500ms) が自然な時間差を生んでいる

### 5.2 live 切替後に致命化するシナリオ

- スキャルピング / 高頻度再参入が常態化すると、close→reopen が同一ミリ秒で発生する頻度が上がる
- 再 open が誤って `event_type='add'` になると:
  - `positions` 行の連続性 (open → ... → close → open → ...) が破綻
  - `concurrent_positions` / `exposure` 計算が add 判定時の想定建玉で汚染される
  - `close_events` との対応が取れなくなり reconcile が失敗する可能性

### 5.3 Phase 6 paper 運用での取り扱い

- **paper 継続は可** (発生確率が低く、ExitFireMetricsService 経由で `span_end_utc` 監視していれば異常は検知可能)
- **live 化前には必ず解消すべき** (§6 の修正方針を人間監督下で実施)

---

## 6. 修正方針候補 (未決定)

> 以下は次セッション F-2 で評価する選択肢。**本メモでは決定しない**。

### 6.1 方針 A — ORDER BY 句を insertion-order で強化

- `ORDER BY event_time_utc DESC, position_snapshot_id DESC` に `, rowid DESC` を追加 (SQLite 専用)
- 長所: 最小 diff
- 短所: DB 方言依存 (Postgres では別手法要)

### 6.2 方針 B — event_type 判定を「close 有無 query」に置換

- `on_fill()` で「最新 close row の position_snapshot_id が直近 open/add 以降に存在するか」を explicit SQL で判定
- 長所: window function tie-break に依存しない
- 短所: on_fill hot path でクエリが増える

### 6.3 方針 C — タイムスタンプ精度向上

- `event_time_utc` をマイクロ秒 / ULID 26 桁全比較に拡張
- 長所: 根本対処
- 短所: schema 変更 or 比較ロジック書き換え、広範囲に波及

**推奨手順 (次セッション用)**:
1. 再現テスト PR (read-only, 同一ミリ秒シナリオを明示的に網羅) を先に 1 本
2. 仮説確定後、方針 A–C から選定して修正 PR を 1 本

---

## 7. 関連資料

- Cycle 6.7b (PR #94) — StateManager write path 導入
- Cycle 6.7d PR-B (PR #97) — on_close atomicity (I-03)
- `docs/design/cycle_6_9_summary.md` — Cycle 6.9/6.10 系 rollup (本メモと補完関係)
- `docs/design/cycle_6_9_supervisor_loop_memo.md` — 将来 supervisor loop 契約 (順序性の別論点)
- `docs/phase6_hardening.md §6.1` — safe_stop / atomicity 契約

---

## 8. 非対象 (このメモで決めないこと)

- **本メモは修正方針を選ばない** — 方針 A/B/C の評価は次セッション F-2
- **本メモはテストを書き換えない** — 再現テストは次セッションで新規 PR として追加
- **本メモは live 化スケジュールに影響しない** — live 化判断は Phase 7 別議論
- **他の flaky test の一般論は対象外** — 本件固有の調査入口のみ

---

## 9. 結果記録 (2026-04-22)

### 9.1 F-2 Step 1 — 再現テスト (PR #109, merged)

- 追加: `tests/unit/test_state_manager_ordering_repro.py` (read-only, src 変更なし)
- monkeypatch で `state_manager` モジュール内の `generate_ulid` を制御し、open/close 行が同一ミリ秒で adverse な ULID lex 順 (open psid > close psid) を取るよう強制
- 結果: R-1 が決定的に発火することを 5 テストで確認 — `test_fires_when_open_psid_greater_than_close_psid`, `test_open_instruments_directly_returns_closed_instrument_under_adverse_ulids`, `test_open_position_details_returns_closed_instrument_under_adverse_ulids` 等が adverse 列で必ず失敗
- 影響範囲: `open_instruments` / `open_position_details` / `_last_open_snapshot_id` の 3 site で同型 ORDER BY が再利用されていることを確認

### 9.2 F-2 Step 2 — 方針選定と修正 (本 PR)

**方針 B を採用** (本メモ §6.2 → 「event_type 判定を close 有無 query に置換」)

- 方針 A は技術的に成立せず: `position_snapshot_id` は PRIMARY KEY (一意) のため、`ORDER BY ... position_snapshot_id DESC, <new column>` の後段 tie-break は到達不可能
- 方針 C は schema 変更が必要 (timestamp 精度向上 = column type change)、Designer Freeze の制約と衝突
- 方針 B は schema 変更不要、DB 方言依存ゼロ、append-only 性質を活用した構造的解

**実装 (state_manager.py, 3 site):**

| 関数 | 修正前 (順序依存) | 修正後 (順序非依存) |
|---|---|---|
| `open_instruments()` | window function `ROW_NUMBER() OVER (... ORDER BY event_time_utc DESC, position_snapshot_id DESC)` で latest 行取得、event_type で filter | `GROUP BY instrument HAVING SUM(CASE WHEN event_type IN ('open','add') THEN 1 ELSE 0 END) > SUM(CASE WHEN event_type='close' THEN 1 ELSE 0 END)` |
| `open_position_details()` | 同型 window function、latest 行の units/avg_price 等を返却 | `WHERE event_type='open' AND NOT EXISTS (SELECT 1 FROM positions c WHERE c.order_id=p.order_id AND c.event_type='close')` |
| `_last_open_snapshot_id()` | `WHERE event_type IN ('open','add') ORDER BY ... LIMIT 1` で最新 add or open psid を返却 | `WHERE event_type='open' LIMIT 1` (L2: 1 order = 1 open row なので unique) |

**`on_fill()` の event_type 判定**は `open_instruments()` に依存しているため、`open_instruments()` を直すだけで自動的に order-deterministic になる (追加の変更不要)。

### 9.3 検証結果

- PR #109 の 5 reproduction tests: 全 PASS (assertion を反転させ「invariant holds」型に書き換え。adverse な ULID 列に対しても期待動作)
- `tests/unit/test_state_manager_*.py` + `tests/unit/test_exit_gate_runner.py`: 85 / 85 PASS
- 全テストスイート: 1382 / 1382 PASS (regression なし)
- `python tools/lint/run_custom_checks.py`: clean
- `python -m ruff check / format --check`: clean

### 9.4 paper-mode 範囲外の注意

- pyramiding (1 order に複数の add 行) は L2 paper-mode で発生しない。本修正は paper-mode で identity-equivalent。
- 将来 pyramiding を導入する場合、`open_position_details()` は open 行の units/avg_price のみ返すため、(open, add*) の units 集計が別途必要。設計時に再検討。
- `_last_open_snapshot_id()` の link target が「latest add」から「the open」へ変わるが、open 行は position の identity event であり audit anchor として最も安定。

### 9.5 fix 適用後の本メモの位置付け

- 本メモは原因分析と方針決定の記録として保持。今後 R-1 系の事象が再発した場合の 1 次資料。
- 仮説 R-2 (transaction isolation) / R-3 (FixedClock キャッシング) は R-1 解消で flaky が消失すれば、別事象としては未確認 (本修正で同時に消える) — 再発時に本メモを再開。
