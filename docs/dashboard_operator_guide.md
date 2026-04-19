# Dashboard Operator Guide (Iteration 2 / Demo Mode)

> **目的**: Dashboard の各 panel を「何のために見るか」「どの数値で異常と判定するか」だけに絞った参照表。
> 説明はしない。詳細は既存 docs にリンクする。

---

## 0. このガイドの読み方

```text
- 平常時      → §1 を上から流し見
- 異常疑い時   → §2 で閾値照合
- 値が "—"    → §3 で正常 / 異常を判定
```

→ launch / layout: `docs/dashboard_manual_verification.md`

---

## 1. 10 panel 監視責務マップ

### Row 1 (Market State / Strategy Summary / Meta Decision)

| Panel | 何を見るか | 異常シグナル |
|---|---|---|
| Market State | `phase_mode` / `environment` | `environment` が `demo` 以外 (Iter2) |
| Strategy Summary | order count per status | `FAILED` が連続増加 |
| Meta Decision | static placeholder | (Iter2 は監視対象外) |

### Row 2 (Positions / Daily Metrics)

| Panel | 何を見るか | 異常シグナル |
|---|---|---|
| Positions | open position 一覧 | `max_concurrent_positions=5` 超過 |
| Daily Metrics | filled / canceled / failed の当日カウント | `failed` 比率の急増 |

### Row 3 (Supervisor Status / Recent Signals)

| Panel | 何を見るか | 異常シグナル |
|---|---|---|
| Supervisor Status | 直近 supervisor_events | `safe_stop.fired` / `account_type.mismatch` |
| Recent Signals | 直近 20 orders | `REJECT(SignalExpired)` / `REJECT(DeferExhausted)` の連発 |

### Row 4 (Top Candidates / Execution Quality / Risk State Detail)

| Panel | 何を見るか | 異常シグナル |
|---|---|---|
| Top Candidates | TSS mart 上位候補 | (M20 までは "—" が正常) |
| Execution Quality | fill / slippage / latency | latency が `cycle_timeout_seconds=45` に接近 |
| Risk State Detail | risk_events の判定理由 | `safe_stop_active` / `margin_critical` |

→ panel layout / fallback: `docs/dashboard_manual_verification.md`

---

## 2. 数値基準カタログ (異常判定)

| 領域 | 閾値 | 動作 | 出典 |
|---|---|---|---|
| NTP skew | > 500ms | warning + 起動継続 | `phase6_hardening.md` §6.5 |
| NTP skew | > 5s | 起動拒否 | `phase6_hardening.md` §6.5 |
| Margin | ≤ 50% | warning | `phase6_hardening.md` §6.14 |
| Margin | ≤ 30% | 自動 no_trade + Notifier | `phase6_hardening.md` §6.14 |
| Drawdown | 4.0% (80% 水準) | 通知開始 | `phase6_hardening.md` §6.5 |
| Drawdown | 5.0% | safe_stop 発火 | `phase6_hardening.md` §6.5 |
| Daily loss | 5.0% | safe_stop 発火 | `phase6_hardening.md` §6.5 |
| Consecutive loss | 5 回 | safe_stop 発火 | `phase6_hardening.md` §6.5 |
| Stream gap | > 120s | safe_stop 発火 | `phase6_hardening.md` §6.5 |
| Cycle timeout | 45s | cycle abort | `phase6_hardening.md` §6.5 |

→ パラメータ全量: `docs/phase6_hardening.md` §6.5

---

## 3. 表示が "—" / "No ..." のときの扱い

```text
- Market State が "—"          → DB 未接続 (起動直後 / DB 障害)
- Top Candidates が "No ..."   → M20 未到達 (Iter2 の正常状態)
- 他 panel が "No ..."          → 該当データなし (正常)
```

判定:
- Market State が "—" → DB 接続 / Supervisor 起動を確認 (`docs/operations.md` §4)
- それ以外の panel が "No ..." → §1 異常シグナル列に該当しなければ正常

---

## 4. 異常検知時の次アクション

```text
1. Supervisor Status の最新 event を確認
2. Notifier (Slack / logs/notifications.jsonl) を確認
3. operations.md §4 の対応 runbook (F1–F15) へ
```

→ details: `docs/operations.md` §4 / `docs/operator_quickstart.md` §4

---

## 5. 関連ドキュメント

| 目的 | docs |
|---|---|
| Dashboard 起動 / panel 一覧 | `docs/dashboard_manual_verification.md` |
| 数値パラメータ全量 | `docs/phase6_hardening.md` §6.5 |
| safe_stop / 4-defense | `docs/phase6_hardening.md` §6.1 / §6.18 |
| 異常時 runbook | `docs/operations.md` §4 |
| ナビゲーション | `docs/operator_quickstart.md` |
