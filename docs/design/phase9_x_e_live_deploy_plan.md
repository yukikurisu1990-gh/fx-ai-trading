# Phase 9.X-E Live Deploy Plan (OANDA GOLD deadline: 1-2 days)

**Status:** DRAFT — awaiting v19 causal-fix eval + user approval.
**Date:** 2026-04-26.
**Trigger:** OANDA GOLD membership requires monthly trading volume; user wants limited live trading within 1-2 days.

---

## Goals

1. Establish a low-risk live trading footprint (1-2 mini lots) on OANDA live account to maintain GOLD status.
2. Production decision loop driven by **causal** features — no backtest-only lookahead.
3. Capability to halt within seconds via the M9 SafeStop / G-0/G-1 supervisor wiring.

## Non-goals (explicitly deferred)

- Aggressive position sizing (>2 mini lots per trade).
- Multi-trade per bar (J-3 top-K plumbing exists but is OFF in production).
- Production rollout of `dxy` group or other Phase 9.X-D features (still in eval).
- Phase 9.11 robustness gate (Sharpe ≥ 0.20) — the v19 result will tell us whether mtf's lift is real and whether it clears 9.11 under causal computation.

---

## Pre-deploy gates

### G1. J-5 PR #223 merged

- PR #223: `feat(phase9-x-b/J-5): activate mtf in production FeatureService`.
- CI green, MERGEABLE confirmed 2026-04-26.
- Production `_compute_mtf_features` is **causal by construction** (operates on candles already filtered to `timestamp < as_of_time` by `FeatureService.build`).
- Acceptance: 44 unit tests pass (`tests/unit/test_feature_service_mtf.py` + `tests/unit/test_feature_service_ta.py`).

### G2. v19 causal-fix eval landed

- Script: `scripts/compare_multipair_v19_causal.py` (clone of v18 + shift(1) lookahead fix in `_add_multi_tf_extended_features`).
- Eval: 20-pair `--feature-groups mtf`, default top-ks `1,2,3,5`.
- Comparison anchor: Phase 9.X-B v18 +mtf reported `lgbm_only K=3` SELECTOR Sharpe **0.174**, PnL **15,118**, DD%PnL **1.8%**.

**Decision matrix on G2 outcome:**

| v19 K=3 Sharpe | Interpretation | Live deploy decision |
| ---            | ---            | ---                  |
| ≥ 0.165        | mtf signal is genuine (≤5% inflation) | GO — deploy `--feature-groups mtf` |
| 0.140 – 0.165  | partial inflation; mtf still positive | GO — deploy with reduced position size (0.5 mini lot) |
| 0.10 – 0.140   | meaningful inflation, signal weak | HOLD — deploy baseline (no `--feature-groups`) until investigated |
| < 0.10         | mtf was mostly leakage | HARD HOLD — deploy baseline only; revisit Phase 9.X-B verdict |

The `K=1 lgbm_only` (no mtf) baseline is unaffected — it does not call `_add_multi_tf_extended_features`. Production fallback is therefore safe regardless of G2.

### G3. Demo paper trading (24-48h)

Run `scripts/run_paper_decision_loop.py --live --feature-groups mtf` (or without `--feature-groups` per G2) against the OANDA **demo** environment for 24-48 hours and verify:

- Trade rate ≤ ~10/day per pair (no explosion pattern).
- `feature_hash` stable across cycles when input candles unchanged.
- All 6 mtf features finite and 8dp-rounded (covered by unit tests but confirm in JSONL output).
- M9 SafeStop fires cleanly on SIGTERM (G-0/G-1 supervisor wiring).

---

## Live deploy steps

### Step 1. Merge J-5 (PR #223)

```
gh pr merge 223 --squash --delete-branch
```

After merge, the production loop accepts `--feature-groups mtf`. Without the flag, behaviour is **identical to Phase 9.16 baseline**.

### Step 2. Launch on demo (24-48h)

```
.venv/Scripts/python.exe scripts/run_paper_decision_loop.py \
  --live \
  --instruments EUR_USD,USD_JPY \
  --feature-groups mtf \
  --account demo \
  > artifacts/phase9_x_e_demo_paper.log 2>&1 &
```

Conservative 2-pair start (EUR/USD + USD/JPY) to minimize blast radius and simplify monitoring.

### Step 3. Switch to live with constrained sizing

Once Step 2 shows clean operation for 24h+:

```
.venv/Scripts/python.exe scripts/run_live_loop.py \
  --instruments EUR_USD,USD_JPY \
  --feature-groups mtf \
  --account live \
  --units-per-trade 1000 \    # 1 mini lot
  --max-concurrent 2 \         # max 2 open positions
  > artifacts/phase9_x_e_live.log 2>&1 &
```

**Position sizing for ¥300k account:**

- 1 mini lot (1,000 units) → ~¥150 / pip on EUR/USD, ~¥1,000 / 100pip range
- Max 2 concurrent positions → ~¥300 max delta per pip across portfolio
- Daily loss cap (manual): ¥6,000 (~2% of equity) → halt and review if breached
- Maximum portfolio drawdown trigger: ¥15,000 (5% of equity) → emergency_stop

### Step 4. Monitoring

- **Real-time:** dashboard query wrappers (Cycle 6.9d) over close_events / pnl_realized.
- **Hourly cron:** check trade count, PnL, latest feature_hash.
- **Manual check at JST market open (07:00, 16:00):** review last-hour trades, flag any anomalies.

### Step 5. OANDA GOLD volume target

GOLD membership thresholds are external — **user to confirm exact monthly volume requirement**. Plan assumes "limited live trading sufficient if positions taken consistently across the month". 1-2 mini lots × 5-10 trades/day × 22 trading days ≈ 220-880 mini lots/month notional, which should comfortably maintain a low-tier volume requirement.

If GOLD demands higher volume than this generates, options:

1. Expand instruments universe (current 2 → 5-10 majors).
2. Accept top-K=2 in production (multi-trade per bar; J-3 plumbing already there).
3. Increase per-trade size (1 → 2 mini lots) — only after 2 weeks of clean live data.

---

## Risk register

| Risk | Mitigation |
| ---  | ---        |
| Backtest Sharpe was inflated by lookahead → live underperforms | G2 quantifies inflation; G3 demo-period catches divergence before live capital. |
| `--feature-groups mtf` triggers `_HISTORY_DEPTH_MTF=2100` candle fetch — slow polling | Tested in J-5; OandaBarFeed has TTL cache. Acceptable. |
| Cross-environment feature_hash drift (backtest vs production) | FEATURE_VERSION v3 bump invalidates v2 hashes; all live runs use v3. |
| OANDA rate limiting | Existing OandaQuoteFeed throttles; no change. |
| Market regime shift mid-deploy (post-FOMC, etc.) | Daily manual review; halt if drawdown > ¥6,000. |

---

## Rollback procedure

1. SafeStop the live loop: send SIGTERM (Linux) or CTRL_BREAK_EVENT (Windows). G-0/G-1 contract guarantees graceful close.
2. Re-launch without `--feature-groups`: identical to Phase 9.16 baseline.
3. If P&L impact > ¥30,000 cumulative, halt entirely and post incident memo to `docs/design/phase9_x_e_incident_<DATE>.md`.

---

## Open items (post-launch)

- Phase 9.X-D dxy / dxy+mtf eval closure (PR #222 still OPEN).
- v19 backtest result feeds into a Phase 9.X-B amendment memo if Sharpe drops materially.
- Phase 9.14 paper-trading validation can run in parallel with live demo (Step 2).

---

## Why this plan is safe

- **Reversible at every step.** Each gate has a documented fallback to Phase 9.16 baseline behavior.
- **Capital-bounded.** Maximum exposure ~¥300 / pip across portfolio; daily loss cap ¥6,000.
- **Causal by construction.** Production `_compute_mtf_features` does not have the v18 lookahead pattern; G2 backtest will quantify how much of the +mtf lift was real.
- **Monitorable.** Existing M9 dashboard wrappers + Cycle 6.10 operator checklist apply unchanged.
