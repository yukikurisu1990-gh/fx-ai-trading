# Volume Mode — First-Run Runbook

**Phase:** 9.X-F/V-1
**Last updated:** 2026-04-26
**Audience:** Operator running `scripts/run_volume_mode.py` for the first time on Monday market-open.

---

## 0. Pre-flight checks (run before market open)

### 0.1 Environment variables

```bash
# Required for live + demo
echo "OANDA_ACCESS_TOKEN: ${OANDA_ACCESS_TOKEN:+set}"
echo "OANDA_ACCOUNT_ID:   ${OANDA_ACCOUNT_ID:+set}"
```

Both must print `set`. If either is empty, populate via your secrets manager and re-source.

### 0.2 Lock file is clear

```bash
ls -la logs/volume_mode.lock 2>/dev/null && echo "LOCK EXISTS — investigate before running" || echo "OK"
```

If a lock exists from a prior run, identify the PID it holds (`cat logs/volume_mode.lock`) and verify the process is gone before deleting.

### 0.3 No pre-existing USD/JPY position

```bash
# Quick check via the runner itself (refuses to start if position exists)
.venv/Scripts/python.exe scripts/run_volume_mode.py \
  --account demo --dry-run --target-volume-usd 1 --max-daily-trades 1 --hours-jst 0-23
```

Look for `runner.halt reason=preexisting_position` — if it fires, flatten via OANDA UI before continuing.

---

## 1. Demo smoke (Step 1 — 5 round trips, ~5 minutes)

Goal: verify real HTTP order placement, fill parsing, TP/SL/time-stop triggers, JSONL output.

```bash
.venv/Scripts/python.exe scripts/run_volume_mode.py \
  --account demo \
  --target-volume-usd 5000 \
  --max-daily-trades 5
```

### Expected JSONL events (in order)

| Event | When | Sanity check |
| ---   | ---  | --- |
| `runner.starting` | T+0 | `account_type=demo`, `dry_run=false` |
| `cycle.opened` × 5 | T+~30s, +90s, ... | each has `client_order_id`, `fill_price`, alternating `side` |
| `cycle.closed` × 5 | each ~30-90s after open | `pnl_pip` finite, `stop_reason ∈ {tp,sl,time}` |
| `summary.progress` | (only at every 10th trade) | (won't fire for 5-trade smoke) |
| `cycle.skipped reason=daily_limit` | after 5th close | confirms limit enforcement |
| `runner.shutdown` | on SIGTERM | `cumulative_volume_usd` ≈ 50,000 |

### What to inspect

```bash
# Last 20 events:
tail -20 logs/volume_mode.jsonl | jq .

# All errors (should be zero):
jq 'select(.event=="cycle.error")' logs/volume_mode.jsonl

# Cumulative volume from closed cycles:
jq 'select(.event=="cycle.closed") | .cumulative_volume_usd' logs/volume_mode.jsonl
```

### Stop the smoke

After 5 round trips, the runner sits in `cycle.skipped reason=daily_limit` loop. Send SIGTERM:

```bash
# Find PID:
ps -ef | grep run_volume_mode | grep -v grep
# Then:
kill -TERM <PID>
```

Verify clean exit: process returns code 0 AND `runner.shutdown` event present in JSONL AND no open USD/JPY position on OANDA UI.

---

## 2. Live, half-size (Step 3 — Day 1, ~3-4 hours)

Goal: $250k of round-trip volume on the live account. Operator monitors first 30 minutes then leaves it.

```bash
.venv/Scripts/python.exe scripts/run_volume_mode.py \
  --account live --confirm-live-trading \
  --units-per-trade 5000 \
  --target-volume-usd 250000 \
  --max-daily-trades 25 \
  --max-daily-loss-jpy 1500 \
  > logs/volume_mode_live_day1.stdout 2>&1 &
```

(Loss cap halved to ¥1,500 for the first live session.)

### Live-mode go/no-go criteria during first 30 minutes

- [ ] At least 5 `cycle.closed` events without `cycle.error`
- [ ] Cumulative `daily_pnl_jpy` swings within ±¥500 (consistent with EV ≈ 0)
- [ ] No `cycle.skipped reason=spread_too_wide` floods (spread environment normal)
- [ ] OANDA UI shows position cleanly opening/closing every ~60-90 sec
- [ ] No `cycle.error` event

If any criterion fails: SIGTERM, investigate, do not progress to Step 3.

---

## 3. Live, full-size (Step 4 — Day 2)

```bash
.venv/Scripts/python.exe scripts/run_volume_mode.py \
  --account live --confirm-live-trading \
  --units-per-trade 5000 \
  --target-volume-usd 500000 \
  --max-daily-trades 50 \
  > logs/volume_mode_live_day2.stdout 2>&1 &
```

Day 2 picks up from Day 1's cumulative position **only via OANDA's monthly tally** — the runner's own `cumulative_volume_usd` resets each process. So `--target-volume-usd 500000` here means "stop after 500k more this run", but our actual GOLD progress is the OANDA-side monthly count.

To check OANDA-side progress, use the OANDA platform's monthly trading volume report.

---

## 4. Monitoring (continuous)

```bash
# Live tail with summary lines highlighted:
tail -f logs/volume_mode.jsonl | jq -r '.event + " " + (.cumulative_volume_usd|tostring)?'

# Daily total volume (last cycle.closed in the file):
jq -s 'map(select(.event=="cycle.closed")) | last' logs/volume_mode.jsonl

# Net PnL today:
jq -s 'map(select(.event=="cycle.closed") | .pnl_jpy) | add' logs/volume_mode.jsonl
```

---

## 5. Emergency stop

### 5.1 Graceful (preferred)

```bash
ps -ef | grep run_volume_mode | grep -v grep
kill -TERM <PID>
```

The runner will:
1. If currently in HOLDING → immediate close
2. Wait for close fill confirmation
3. Verify position flat
4. Exit code 0 with `runner.shutdown`

If the runner does NOT exit within 60 seconds, escalate to 5.2.

### 5.2 Force-flatten via OANDA UI

1. Open OANDA web platform → Positions → USD/JPY → Close.
2. SIGKILL the runner: `kill -9 <PID>` (last resort; will leave stale lock file).
3. Manually delete lock: `rm logs/volume_mode.lock`.
4. Verify in JSONL: last event is NOT `cycle.opened` without matching `cycle.closed`. If it is, the position was closed manually and the runner missed the event — record this in an incident memo.

---

## 6. Day-end checklist

- [ ] `runner.shutdown` event present in JSONL with non-zero `cumulative_volume_usd`
- [ ] `daily_pnl_jpy` within expected band (±¥3,000)
- [ ] No open USD/JPY position on OANDA UI
- [ ] Lock file `logs/volume_mode.lock` removed
- [ ] OANDA monthly volume meter advanced by approximately the expected amount (cross-check with `summary.progress` lines)

---

## 7. Common gotchas

| Symptom | Likely cause | Action |
| ---     | ---          | --- |
| All cycles `cycle.skipped reason=spread_too_wide` | News release / illiquid hours | Wait for liquidity to return; no operator action |
| Continuous `cycle.skipped reason=outside_hours` | JST hours window misconfigured | Check `--hours-jst` flag; default 15-21 may need adjust |
| `runner.halt reason=preexisting_position` | Stale position on OANDA | Manually flatten via UI, restart |
| `runner.halt reason=another_process_holds_lock` | Two processes started | `cat logs/volume_mode.lock` to find PID; investigate |
| PnL drifts beyond ±¥3,000/day on consecutive days | Spread structurally wider than design | Reduce `--units-per-trade` or pause for the day |

---

## Sources

- Design: `docs/design/phase9_x_f_volume_mode.md`
- Code: `scripts/run_volume_mode.py`
- Tests: `tests/unit/test_run_volume_mode.py`
- OANDA constraints: <https://help.oanda.jp/oanda/faq/show/231?site_domain=default>
- GOLD status: <https://www.oanda.jp/lab-education/status/>
