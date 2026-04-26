# Phase 9.X-F Volume Mode — OANDA GOLD Maintenance Runner

**Status:** DRAFT — design captured, implementation kicking off.
**Date:** 2026-04-26.
**Goal:** maintain OANDA Japan GOLD membership ($500k USD round-trip volume / month) via a dedicated, alpha-independent runner.
**Out of scope:** alpha generation (Phase 9.X-B/J-5 handles that), regulatory compliance review beyond OANDA's published FAQ.

---

## Why this is separate from `run_live_loop.py`

The alpha runner (`run_live_loop.py`, Phase 9.X-B/J-5) targets **Sharpe and PnL**. Its trade rate is signal-driven (≈2-6 trades/day at the planned 2-pair config), nowhere near GOLD's $500k/month.

The volume runner targets **trade count × notional**, with EV ≈ 0 by design. Mixing the two concerns into one runner would make both harder to reason about and increase the chance of a sizing or guard bug damaging real capital.

| Aspect | Alpha runner (`run_live_loop`) | Volume runner (this) |
| ---    | ---                            | ---                  |
| Decision | model + meta-decider | scheduled, condition-gated |
| Trade rate | 2-6 / day total | 30-50 round trips / day |
| Position size | 1 mini lot (planned) | 5 mini lot |
| Hold time | model-driven, minutes-hours | 30-90 sec |
| Stop conditions | TP / SL / max_holding | time / spread / loss / volume |
| Success metric | Sharpe / PnL | cumulative volume USD |

---

## OANDA constraints (verified 2026-04-26 from public FAQ)

Sources:

- [OANDA会員ステータスとは？](https://www.oanda.jp/lab-education/status/)
- [スキャルピングは禁止ですか？ FAQ #231](https://help.oanda.jp/oanda/faq/show/231?site_domain=default)

Key facts:

1. **GOLD維持条件:** monthly volume ≥ $500k USD, **counted on both new + close legs** (round-trip). Example from FAQ: USD/JPY 25万通貨 entry + 25万通貨 close = $500k.
2. **判定タイミング:** daily; status holds until end of next month.
3. **Demote:** on the 3rd of each month if previous-month volume insufficient.
4. **Scalping:** **数秒程度開く** scalping is *not* prohibited per FAQ. Specific second/count thresholds undisclosed.
5. **Prohibited (規約):** "極めて短時間に機械的に反復して本取引を行う行為" and "本取引システムの運用に対して過大に負荷を強いる行為." Violation: account freeze + retroactive trade cancellation, **no prior notice.**

Implication for design: every trade must look like a deliberate human-pace decision. Cool-off ≥ 30 sec, daily ceiling on count, regulatory pause at announcement times.

---

## Mode A specification

### Trade unit
- **Instrument:** USD/JPY (1 unit = $1 of volume → trivial volume math; matches OANDA FAQ example exactly).
- **Size per trade:** 5 mini lots = 5,000 units.
- **Direction:** alternate long / short to keep delta near zero across the session (long → 5 sec gap → short → ...).

### Hold cycle
- **Open:** market order, FOK, no SL/TP attached at order creation.
- **Hold:** 30-90 seconds.
- **Close trigger** (whichever first):
  - TP: unrealized PnL ≥ +1 pip
  - SL: unrealized PnL ≤ -3 pip
  - Time-stop: 90 seconds elapsed
- **Cool-off:** 30 seconds before next OPENING.

### Hard limits
- **Daily round-trips ceiling:** 50 (== 250 mini lots / day at size 5 → $250k volume).
- **Cumulative volume target:** $500k USD (two days × 50 round trips × 5 mini lots × 2 legs ≈ $500k).
- **Daily loss cap:** ¥3,000.
- **Spread gate:** if spread > 1.5 pip when about to OPEN, skip and wait 60 sec.
- **Hours:** only 15:00-21:00 JST (Tokyo / London overlap, lowest typical spread).

### Anti-mechanical-pattern guards (規約 risk reduction)
- Random jitter: hold time uniform in [30, 90] sec; cool-off uniform in [30, 60] sec.
- Hourly rate ceiling: max 6 round trips / hour.
- After 3 consecutive losing round trips → 5-minute cool-off.
- Pause window 5 min before / 30 min after major economic releases (manual list of UTC times in CLI flag, no automated calendar feed).

### Cost projection
- 50 round trips × 5 mini lot × 0.5 pip avg spread × ¥10/pip per mini lot = **¥1,250 / day**
- Worst case 1.5 pip spread: ¥3,750 / day, ¥7,500 over 2 days
- All-stops-loss worst case (50 × 5 lot × 3 pip SL × ¥10) = ¥7,500 / day

---

## State machine

```
       SIGTERM /
       limit hit
        ↓
 ┌──────────┐  spread OK   ┌──────────┐  fill OK   ┌──────────┐
 │  IDLE    │ ───────────▶ │ OPENING  │ ─────────▶ │ HOLDING  │
 │          │              │          │            │          │
 └──────────┘ ◀────────┐   └──────────┘            └──────────┘
      ▲                │        │                        │
      │ cooloff done   │        │ open failure           │ TP/SL/time
      │                │        ▼                        ▼
 ┌──────────┐          │   ┌──────────┐            ┌──────────┐
 │ COOLOFF  │ ◀────────┴── │  ERROR   │            │ CLOSING  │
 │          │              │ (halt)   │            │          │
 └──────────┘              └──────────┘            └──────────┘
                                                        │ close fill
                                                        ▼
                                                    [back to COOLOFF]
```

- IDLE: pre-trade checks (hours, spread, daily counts, cumulative volume, loss cap). If any fails, sleep and retry.
- OPENING: place market order, wait for fill. If broker error → log + 60 sec wait + IDLE.
- HOLDING: poll quote every 2 sec, check TP/SL/time.
- CLOSING: place opposite market order to flatten. Wait for fill, log P&L.
- COOLOFF: jittered sleep, then IDLE.

---

## CLI

```
python -m scripts.run_volume_mode \
  --instrument USD_JPY \
  --units-per-trade 5000 \
  --target-volume-usd 500000 \
  --max-spread-pip 1.5 \
  --max-daily-loss-jpy 3000 \
  --hours-jst 15-21 \
  --max-hourly-trades 6 \
  --max-daily-trades 50 \
  --tp-pip 1.0 \
  --sl-pip 3.0 \
  --time-stop-sec 90 \
  --cooloff-min-sec 30 \
  --cooloff-max-sec 60 \
  --account demo \
  --dry-run                # no real orders, log decisions only
```

Default `--account demo` — operator must explicitly pass `--account live` (with `--confirm-live-trading`) to switch.

---

## Logging

JSONL to `logs/volume_mode.jsonl`. Stable event names:

- `runner.starting`, `runner.shutdown`, `runner.halt`
- `cycle.skipped` (with `reason`: `outside_hours` | `spread_too_wide` | `daily_limit` | `loss_cap` | `volume_target_hit`)
- `cycle.opened` (units, side, fill_price, client_order_id)
- `cycle.closed` (pnl_pip, pnl_jpy, hold_sec, stop_reason)
- `cycle.error` (event during open / close / quote)
- `signal.received` (SIGTERM)
- Cumulative summary every 10 round trips: `summary.progress` (round_trips, volume_usd, net_pnl_jpy, spread_avg)

Example jq queries:

```
# Current cumulative volume:
jq -s 'map(select(.event=="summary.progress")) | last' logs/volume_mode.jsonl

# All errors today:
jq 'select(.event=="cycle.error" and .ts >= "2026-04-26")' logs/volume_mode.jsonl
```

---

## Demo + live deploy steps

### Step 1: Demo dry-run (5 min)
```
python -m scripts.run_volume_mode --account demo --dry-run \
  --target-volume-usd 5000 --max-daily-trades 5
```
Verifies CLI parsing, env loading, hours gate. No HTTP calls.

### Step 2: Demo live-call (10 min)
```
python -m scripts.run_volume_mode --account demo \
  --target-volume-usd 5000 --max-daily-trades 5
```
5 round trips on OANDA practice account. Verify:
- Real order placement and fills
- TP/SL/time triggers all observed
- JSONL log structure correct
- SIGTERM produces graceful close (no orphan position)

### Step 3: Live mode, half-size (Day 1 morning)
```
python -m scripts.run_volume_mode --account live --confirm-live-trading \
  --units-per-trade 5000 --target-volume-usd 250000 --max-daily-trades 25
```
Half the daily target. Operator monitors for 30 min, then leaves it running.

### Step 4: Live mode, full-size (Day 1 afternoon onward)
```
python -m scripts.run_volume_mode --account live --confirm-live-trading \
  --units-per-trade 5000 --target-volume-usd 500000 --max-daily-trades 50
```
GOLD threshold cleared by end of Day 2.

---

## Safety / SafeStop

- SIGTERM/SIGINT registered. On signal: if HOLDING, immediately CLOSE; if OPENING, wait for outcome then halt; otherwise halt immediately.
- Process-exit code 0 only after final state is "no open position" — confirmed via `OandaBroker.get_positions`.
- Max one process per account at a time (file-based lock at `logs/volume_mode.lock`).

---

## Out of scope (deferred)

- Multi-instrument volume mode (USD/JPY single-pair sufficient).
- Alpha-aware sizing (e.g. larger size when alpha signal aligns).
- Automated economic calendar pause.
- Direct integration with run_live_loop (alpha + volume) — they run as separate processes so a failure of one cannot affect the other.

---

## Acceptance criteria

1. End-to-end demo run reaches 5 round trips with ≥ 1 of each {TP, SL, time-stop} stop reason observed.
2. Volume tally in summary lines matches OANDA platform's reported activity (manual check).
3. SIGTERM from any state ends with `OandaBroker.get_positions(USD_JPY) == []`.
4. Loss cap and daily-trades cap enforce halt before exceeding.
5. Live runs for 2 days yield ≥ $500k cumulative volume.

---

## Risk register

| Risk | Mitigation |
| ---  | ---        |
| OANDA flags as "極めて短時間に機械的に反復" | Cool-off ≥ 30 sec + jitter + hourly cap + daily cap; documented in JSONL for post-hoc explanation. |
| Spread widens during major release | Spread gate + JST trading hours window. |
| Network/API failure mid-cycle | ERROR state halts; operator manually flattens via OANDA web. Lock file prevents duplicate processes. |
| Process killed mid-CLOSING leaves orphan position | Lock file + on-startup check: if open USD/JPY position exists, exit with error and require manual reconcile. |
| Unintended live trading | `--account live` requires `--confirm-live-trading`; default demo. |
| Cost > ¥10k unintended | Daily loss cap ¥3,000; cumulative tally logged; manual abort if observed cost diverges from projection. |
| Position not flat at end of day | Time-stop forces close at 90 sec; daily trade cap forces idle period; final SIGTERM closes any holding position. |
