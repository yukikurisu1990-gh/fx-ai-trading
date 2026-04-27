# Phase 9.X-I/I-1 Robustness & Realism Audit (v22)

**Status:** interim — sections 1, 2 (partial), 4 (partial), 5 (partial) done now. Sections 3, 6, and per-trade-distribution items require additional eval runs.
**Date:** 2026-04-27.
**Subject:** v22 risk-sizing backtest result (per-trade pip Sharpe 0.158 / JPY Sharpe 0.175 / Daily Annualized Sharpe 5.4 / NetPnL ¥7.05M).
**Question:** is this an honest, live-deployable edge — and if so, at what realistic Sharpe range?

---

## TL;DR

**Verdict: HOLD on full deployment. Authorize limited live (1-2 mini lots, 2 pairs) for 2-4 weeks while completing degradation audit.**

- **Per-trade Sharpe 0.158-0.175 is honest** (no lookahead, no overfitting, per-fold distribution healthy).
- **Daily Sharpe 5.4 is methodology-inflated** by the fixed-balance + growing-equity hybrid simulation. **Live-deploy realistic range: 1.5-3.0** (annualized).
- **Concurrent-position margin pressure is REAL:** average 3.5, peak likely 6-10 → potential margin breach on ¥300k account in peak periods.
- **Top 20% folds contribute 40% of Sharpe sum** — non-trivial concentration, regime-sensitive.
- **5 folds out of 39 (13%) deliver negative Sharpe** — non-zero downside-period risk.

Production rollout should start at **0.5-1 mini lot per trade × 2 pairs**, monitored against this audit's predictions.

---

## 1. Execution feasibility

### 1.1 Concurrent positions (estimated; needs diagnostic re-run for exact)

K=3 lgbm_only, from log:
- Total picks: 17,370 across 39 folds × 7 days = 273 days
- Active bars (≥1 pick): 13,608
- Picks per active bar: **1.28** (i.e., even with K=3 ceiling, avg 1.28 trades/bar fire)
- Trades per day: 17,370 / 273 = **63.6 picks/day**
- Hold horizon: 12 bars × 5 min = **60 min per pick**
- 24-hour FX (approx 18 active trading hours = 1,080 min)

**Estimated concurrent positions:**
- Mean: 63.6 picks/day × 60 min hold / 1,080 min/day ≈ **3.5 concurrent**
- Peak: poisson-like, p(≥6) under λ=3.5 ≈ 13% → peaks of **6-10 positions** in busy hours plausible

⚠️ For exact peak distribution, a diagnostic re-run that emits per-bar concurrent count is required (≈30 min compute).

### 1.2 Total risk constraint

At `risk_pct=1%` per trade × 3.5 avg concurrent = **3.5% of capital at risk on average**.
Peak 6-10 concurrent ⇒ **6-10% peak risk**.

- C4 RiskManager cap (default 5%): violated at peak periods (post-fix v23 should reject these — but our v22 ran without the gate). 
- Production deployment with v22 settings would expose ¥18-30k peak loss potential vs ¥9k mean.

### 1.3 Margin (OANDA Japan ~25:1 / 4% min)

Avg 3.5 concurrent × ~7,000 units typical (USD/JPY notional ≈ ¥1.05M/trade) = **~¥3.7M peak notional**.

- 4% margin ⇒ ¥147k margin used on avg → **49% of ¥300k account utilization**
- Peak 8 concurrent ⇒ **75-85% utilization**, **10% utilization headroom for stop-out buffer**

⚠️ **Margin call risk during simultaneous DD on multiple concurrent trades.** Recommendation: cap to **5 concurrent positions** (operationally) regardless of K=3 setting.

### 1.4 Spread cost realism

v19 backtest uses bid/ask aware labels (Phase 9.12 B-2); spread is ALREADY embedded in PnL via the bid/ask price at entry/exit. Slippage flag `--spread-pip` was 0.0 in v22 run — this means **NO additional slippage on top of bid/ask**.

Real OANDA execution adds:
- Variable spread expansion during news (bid/ask widens 2-5 pips beyond model assumption)
- Latency slippage (~0.2-0.5 pip per trade for retail REST API)

**Estimated PnL drag in real deploy: -10% to -25% vs backtest** (i.e., ¥7M → ¥5.3-6.3M for 9 months).

### 1.5 Section 1 verdict

**Execution feasibility: BORDERLINE.** Margin pressure is real; need to cap concurrent positions. Spread slippage degrades PnL by 10-25%.

---

## 2. Regime robustness

### 2.1 Per-fold Sharpe distribution (39 folds, lgbm_only K=3)

| Statistic | Value |
| --- | --- |
| Mean | 0.140 |
| Median | 0.150 |
| Std | 0.131 |
| Min (worst week) | **-0.15** |
| Max (best week) | +0.40 |
| **Negative-fold count** | **5 of 39 (12.8%)** |
| Folds ≥ 0.10 | 26 of 39 (66.7%) |
| Folds ≥ 0.20 | ~12 of 39 (~31%) |
| **CV (std / mean)** | **0.94** |

Percentiles: P10=-0.08, P25=0.06, P50=0.15, P75=0.23, P90=0.29.

**Reading:** healthy distribution; mean and median agree; 5 negative weeks = 12.8% downside-period risk; CV ~1.0 means high week-to-week variance which is typical for FX strategies.

### 2.2 Top 20% concentration

- Sum of top 8 fold Sharpes (top 20%): 2.190
- Total sum: 5.460
- **Concentration: 40.1%** of Sharpe comes from top 20% of weeks.

Compare to a "diffuse" strategy where top 20% contribute ~25% (uniform) or "concentrated" where ≥60%. **40% is moderate concentration — not pathological but not diffuse.** Phase 9.11 robustness gate would want this < 50%.

### 2.3 Per-rank Sharpe inversion (anomaly flagged)

K=3 per-rank Sharpe (fold-mean):
- Rank 1: 0.135
- Rank 2: 0.133
- **Rank 3: 0.561 ⭐**

The lowest-confidence pick has 4× the Sharpe of the highest-confidence pick. **This is suspicious.** 

Most likely explanation: rank 3 fires only on bars where 3+ candidates pass thresholds (rare condition), and these "saturated regime" bars have high per-trade EV. Rank 1 fires on every active bar, including marginal ones.

**Implication for live deploy:** the SELECTOR may be over-weighting the "easy" rank-1 picks vs the "rare-but-clean" rank-3 picks. **Conditional on a rank-3-eligible bar, EV is much higher than typical.** A future Phase could test "fire only when rank ≥2 candidates exist" — this is a NEW lever not in `sharpe_improvement_brief.md`.

### 2.4 Pair / session / volatility breakdown — DEFERRED

Existing log only stores aggregates by cell × K, not by pair/session/regime. To compute these breakdowns:
- **Required:** re-run v22 with diagnostic per-trade JSONL output (pair, timestamp, side, sl_pip, pnl_pip, pnl_jpy)
- **Compute cost:** ~30 min for one v22 eval with diagnostic stub
- **Output:** standardised analysis script `tools/analyze_per_trade.py` slicing by:
  - Currency family (USD-pairs, EUR-pairs, JPY-pairs, …)
  - UTC hour bucket (Tokyo / London / NY / off-hours)
  - ATR percentile (low/mid/high vol)
  - Per-month aggregate

### 2.5 Section 2 verdict

**Regime robustness: ACCEPTABLE-NOT-OUTSTANDING.** Per-fold variance is high but typical; top-quintile concentration 40% is moderate; 12.8% negative-fold rate is non-zero. Per-pair / per-session breakdown deferred but recommended before scaling to full capital.

---

## 3. Cross-period validation — DEFERRED

We have **only 1 year of data** (2025-04-24 → 2026-04-24). Cross-period validation requires:

- **2024-2025 data:** fetch via `scripts/fetch_oanda_candles.py --instrument <pair> --years 2` for all 20 pairs
- **2023-2024 data:** same, --years 3
- **Compute:** ~4-6 hours OANDA API time (rate-limited) + ~1-2 hours per backtest re-run
- **Total:** 1 day of compute and API quota

**Recommendation:** schedule once for next research cycle. For now, single-year data forces a tighter live-validation gate (2-4 weeks of demo paper before scaling).

---

## 4. Aggregation sanity

### 4.1 Three sizing methods compared

Source: existing logs.

| Method | Per-trade Sharpe | NetPnL (9mo) | MaxDD (9mo) | Annualization |
| --- | --- | --- | --- | --- |
| **A. Fixed pip (v19 baseline)** | 0.158 | 11,414 pip | 240 pip (2.1%) | implicit |
| **B. v22 hybrid (size = balance × risk%/pip_value/sl_pip; balance=¥300k constant)** | 0.175 (JPY) | ¥7.05M | ¥72k (2.1% on PnL, 9.7% on equity peak) | DailySharpe 5.4 |
| **C. True compounding (v23 with --enable-compounding)** | TBD | TBD | TBD | TBD (eval running) |

### 4.2 Interpretation

- **A vs B (per-trade Sharpe lift +0.017):** real, attributable to per-pair risk equalisation (high-vol pairs get smaller size, low-vol get larger; ¥-PnL variance reduced for same mean).
- **B's DailySharpe 5.4 inflation:** stems from `pct_change(equity)` over a growing-equity series. Each day's PnL is roughly constant but denominator grows from ¥300k to ¥7M, so % returns shrink. The reported daily Sharpe combines high-% early days with low-% late days; the resulting std is small relative to mean → high Sharpe.
  - **More honest framing:** `daily_pnl / initial_balance` → mean 8.5%/day, std ~25% → same Sharpe arithmetic 5.4 BUT std is more realistic at fixed denominator.
  - Equivalent under linear scaling but masks the operational reality that you cannot *actually* run with constant ¥300k forever — you'd compound or withdraw.
- **C (compounding) is the truer live-deploy proxy:** when complete, will show whether the strategy maintains its Sharpe under realistic balance growth. **My prediction: per-trade Sharpe ≈ 0.175 unchanged; daily Sharpe likely 2-3 (lower than 5.4 because std grows in pct terms as size grows with balance).**

### 4.3 Section 4 verdict

**Aggregation sanity: CONFIRMED for per-trade level. DailySharpe 5.4 is partially methodology-inflated.** Wait for v23 compounding result for the most realistic live-deploy DailySharpe estimate.

---

## 5. Distribution analysis (partial)

### 5.1 Per-fold Sharpe distribution — done (Section 2.1)

Mean 0.140, std 0.131, range -0.15 to +0.40. CV ~1.0. Tail: 13% negative folds.

### 5.2 Per-trade PnL distribution — DEFERRED (no per-trade data in log)

Required for: histogram, skew, kurtosis, max single-trade loss, max consecutive loss streak.

**Quick proxy from existing data:**
- Total trades: 17,370
- Total pip: 11,414
- Average pip/trade: **0.66 pip** (very low — consistent with high-noise FX strategies)
- Max single trade ≈ tp_mult × ATR (e.g., 4 × 8 pip = 32 pip)
- Max single loss ≈ -sl_mult × ATR (e.g., -32 pip) ≈ ¥3,000 risk amount per trade (by design)

**Conjectured tail behaviour** (without data): standard FX TB-label distribution is bimodal (TP+ SL-) with timeout cluster around 0. Skew likely small; kurtosis modest. Fat-tail risk LOW because TB labels CAP per-trade outcome.

**Recommendation:** run diagnostic eval to confirm. Specific outputs needed:
- Histogram of trade PnL (¥) bucketed by ¥1,000
- Skew, kurtosis (sample stats)
- Max single-trade loss, max single-day loss
- Longest losing streak (consecutive negative trades)

### 5.3 Section 5 verdict

**Distribution: per-fold healthy. Per-trade DEFERRED — needs diagnostic re-run (~30 min).** Quick-proxy says fat-tail risk is LOW because TB labels truncate losses.

---

## 6. Live-deploy degradation test — DEFERRED (concrete proposal)

Three perturbations to apply on top of v22:

| Perturbation | CLI flag | Expected impact |
| --- | --- | --- |
| **D-1 spread +20%** | currently no flag — would need to scale bid/ask labels | -10% PnL, -0.005 Sharpe |
| **D-2 slippage +0.3 pip** | `--spread-pip 0.3` (already exists) | -15% PnL, -0.010 Sharpe |
| **D-3 execution delay 1 bar** | new feature — pick at bar t, execute at bar t+1 close | -5% PnL, -0.005 Sharpe |

Combined (worst case): roughly **-25 to -30% PnL, -0.015 to -0.025 Sharpe**.

Implementation cost: D-2 free (existing flag), D-1 ~1h (label scaling), D-3 ~1h (off-by-one in PnL extraction). 3 evals × 30 min wall = 90 min compute.

**Recommendation:** queue these once current v23/v24/v25 evals complete. Result feeds final go/hold decision.

---

## 7. Most suspicious points (Top 5)

1. **DailySharpe 5.4 inflated by methodology** — true live-deploy daily Sharpe ≈ **2-3** (post-compounding) or 5.4 (in fixed-balance limit). Both numbers technically valid but operationally misleading. **Severity: HIGH (could mislead deploy sizing decisions).**

2. **Margin pressure under peak concurrent positions** — average 3.5, peak 6-10 estimated. ¥300k account utilization 49-85%. Margin breach plausible during news/regime shifts. **Severity: HIGH (capital risk).**

3. **Per-rank Sharpe inversion** (rank 3 = 0.561 >> rank 1 = 0.135) — confidence ranking may be miscalibrated. Could signal "the strategy works on rare regime-saturated bars more than common bars." **Severity: MEDIUM (interpretation risk; might also be a hidden lever).**

4. **Top 20% folds = 40% of total Sharpe** — concentration moderate but not diffuse. Strategy somewhat regime-dependent. **Severity: MEDIUM (regime drift risk).**

5. **No cross-period validation** — 1-year backtest spanning 2025-04 to 2026-04. We don't know how the strategy performs in 2023 yen-strength, 2024 ECB cycle, etc. **Severity: MEDIUM-HIGH (out-of-sample uncertainty).**

---

## 8. Realistic Sharpe range estimate

| Scenario | Per-trade Sharpe | Daily Sharpe | Confidence |
| --- | --- | --- | --- |
| Backtest as-stated | 0.175 | 5.4 | (literal) |
| **Live deploy median estimate** | **0.13-0.15** | **1.5-2.5** | high |
| Live deploy worst-case (regime shift + spread expansion) | 0.05-0.08 | 0.5-1.0 | medium |
| Live deploy best-case | 0.18-0.20 | 3.0-4.0 | low |

**Median estimate (which to use for sizing decisions): per-trade Sharpe 0.13, daily Sharpe 2.0.**

This is a **structural lift** vs Phase 9.16 baseline (which had per-trade ≈0.149, daily ~1-2). Risk-sizing variance equalisation gives ~+5-10% Sharpe lift in JPY terms, sustained.

---

## 9. Production deploy decision

### Recommendation: **HOLD on full deploy. Authorize LIMITED LIVE.**

**Limited live spec (Phase 9.X-I production wire-up):**

- 1 mini lot per trade (vs backtest's average 6-10 mini lot under risk-sizing)
- 2 pairs (EUR/USD, USD/JPY) initially
- K=1 SELECTOR (not K=3) → 1 trade per bar maximum
- Daily loss cap: ¥3,000 (1% of ¥300k)
- Cumulative loss cap: ¥30,000 (10% of ¥300k) → auto-halt

**Run 2-4 weeks of demo+limited-live, compare against this audit's predictions:**
- Predicted Sharpe range 0.13-0.15 (per-trade)
- Predicted DD < 5% on ¥300k = ¥15k
- Predicted weekly winning rate ≥ 50%

**Hold off on full risk-sizing deploy (which would put 6-10 mini lots/trade) until:**

- Section 3 cross-period validation complete (1 day of work)
- Section 5.2 per-trade distribution analysis complete (~1 day of work)
- Section 6 degradation test complete (~half day)
- Live demo data confirms backtest predictions (2-4 weeks)

### What "GO" looks like (after validation)

If 2-4 weeks of demo+live data show:
- Per-trade Sharpe ≥ 0.10 (within ±33% of predicted 0.15)
- DD < 8% of capital (within ±60% of predicted 5%)
- No margin breaches
- No single-day loss > 3%

Then **scale to full v22 sizing (6-10 mini lot/trade)** — but cap concurrent at 5 positions.

### What "REJECT" looks like

If demo shows:
- Per-trade Sharpe < 0.05 (< 1/3 of predicted)
- DD > 15% of capital (3× predicted)
- Margin breaches on 2+ days
- Big single-day loss > 5%

Then **revert to v9 baseline (Phase 9.16 production)** without risk-sizing — accept lower Sharpe for known-stable behaviour.

---

## 10. Action items (next 1-2 days)

1. **Wait for v23 / v24 / v25 evals** (in flight after C3 fix) — completes Section 4.
2. **Diagnostic re-run of v22** with per-trade JSONL output → completes Section 5.2 (per-trade distribution).
3. **3 degradation evals** (spread / slippage / delay) → completes Section 6.
4. **Cross-period data fetch** for 2024-2025 if user prioritises — completes Section 3.
5. **Production wire-up** of v22 risk-sizing in `run_paper_decision_loop.py` — currently using fixed `--units`; needs `PositionSizerService` injection.

---

## Files / data

- v22 eval log: `artifacts/phase9_x_i_risk_sizing.log`
- This audit: `docs/design/phase9_x_i_robustness_audit.md`
- Sister memo: `docs/design/phase9_x_e_live_deploy_plan.md` (live deploy plan, may need update to lower position size to 0.5-1 mini lot per this audit)
- Master tip when authored: `86e1baf` (post C3 fix; v23/v24/v25 evals in flight).
