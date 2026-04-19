# Operator Quickstart (Iteration 2 / Demo Mode)

> **目的**: 迷ったときに「次に何を見るか」を 30 秒で決めるためのナビゲーション。
> 詳細はすべて既存 docs にリンクする。説明はしない。

---

## 0. 通常運用フロー（最初に覚える）

```text
1. 起動する     → python scripts/ctl.py start
2. 状態を見る   → Dashboard
3. 操作する     → python scripts/ctl.py <cmd>
4. 異常時      → safe_stop / ログ確認
5. 復旧        → operations.md §4
```

→ details: `docs/operations.md`

---

## 1. このシステムを使う前に

- Iteration 2 は **demo only**。live は Phase 7 で解禁予定
- live 切替操作は Iter2 では実行しない (4-defense gate でブロック)
- README §Running the System を未実施なら先にそちらへ

→ details: `docs/iteration2_completion.md` / `docs/phase6_hardening.md` §6.18

---

## 2. 起動と停止 (ctl 5 コマンド)

| コマンド | いつ実行できるか |
|---|---|
| `python scripts/ctl.py start` | アプリ未起動時 (PID file 不在) |
| `python scripts/ctl.py stop` | アプリ起動中 (graceful 停止) |
| `python scripts/ctl.py resume-from-safe-stop --reason="..."` | safe_stop 状態のとき |
| `python scripts/ctl.py run-reconciler` | アプリ起動中、整合性疑い時 |
| `python scripts/ctl.py emergency-flat-all` | 緊急時のみ (2-factor token 入力必須) |

→ details: `docs/operations.md` §11 (Cheat Sheet) / `scripts/ctl.py` (実装)

---

## 3. 状態を確認する

優先順に見る:

```text
1. Dashboard
2. logs/safe_stop.jsonl
3. Dashboard "Positions"
```

→ details: `docs/dashboard_manual_verification.md`

---

## 4. 異常時のログ追跡

優先順に見る:

```text
1. supervisor       → supervisor_events テーブル / logs/supervisor.log
2. broker           → orders / transactions テーブル
3. execution        → execution_metrics / risk_events テーブル
```

横断追跡には Common Keys: `cycle_id` / `run_id` / `order_id` / `correlation_id`

### 4.1 ログ → DB → イベントの追跡導線

異常 1 件を端から端まで縫うときの基本順:

```text
[1] logs/notifications.jsonl で event_type と発火時刻を特定
       ↓ (event payload に correlation_id が入っている)
[2] supervisor_events テーブルで同 correlation_id の前後イベント列を取得
       ↓ (cycle_id を取得)
[3] orders / order_transactions / execution_metrics を同 cycle_id で JOIN
       ↓
[4] 該当 order_id があれば close_events / risk_events / no_trade_events も同 order_id / correlation_id で参照
```

SQL 例 (correlation_id で発注 lifecycle を一望、列名はテーブル別の最小共通項のみ):

```sql
SELECT 'orders'             AS src, event_time_utc FROM orders             WHERE correlation_id = :cid
UNION ALL
SELECT 'order_transactions'      , event_time_utc FROM order_transactions WHERE correlation_id = :cid
UNION ALL
SELECT 'execution_metrics'       , event_time_utc FROM execution_metrics  WHERE correlation_id = :cid
UNION ALL
SELECT 'close_events'            , event_time_utc FROM close_events       WHERE correlation_id = :cid
ORDER BY event_time_utc;
```

(各テーブル固有の列は `schema_catalog.md` §2.1 を参照して個別 SELECT)

→ details: `docs/design.md` §8 / `docs/phase6_hardening.md` §6.5 / `docs/schema_catalog.md` §3 (Common Keys 伝搬規則)

---

## 5. CLI / Dashboard / SQL の使い分け

```text
- 通常操作   → CLI (ctl)
- 状態確認   → Dashboard
- 深い調査   → SQL (read-only 推奨)
```

書込系の SQL (DELETE / TRUNCATE / status 後退遷移) は **禁止**。

→ details: `docs/operations.md` §3 (許可介入境界) / §15 (UI 操作境界)

---

## 6. 詳細ドキュメント索引

| 目的 | docs |
|---|---|
| 起動・停止・運用手順 | `docs/operations.md` |
| 状態確認 (Dashboard) | `docs/dashboard_manual_verification.md` |
| 設計全体像 | `docs/design.md` |
| 契約仕様 (Interface) | `docs/implementation_contracts.md` |
| 安全装置 (4-defense / safe_stop) | `docs/phase6_hardening.md` |
| 開発ルール / 禁止操作 | `docs/development_rules.md` |
| データ保持 | `docs/retention_policy.md` |
| スキーマ定義 | `docs/schema_catalog.md` |
| 次フェーズ計画 | `docs/phase7_roadmap.md` / `docs/phase8_roadmap.md` |
