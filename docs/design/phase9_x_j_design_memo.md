# Phase 9.X-J Design Memo — Realism Pack

**Status:** kickoff. Implementation starting with J-1 (compounding).
**Date:** 2026-04-27.
**Anchor:** Phase 9.X-I/I-1 v22 with risk-sizing (eval running).
**Goal:** bring production-side guards and stateful elements into the backtest so the simulated Sharpe / PnL / DD numbers more accurately predict live behaviour. Includes one genuine *lever* (compounding) for the 10%/month target.

---

## Why this matters

Backtests model alpha generation but treat every trade as if it's the only trade ever, with constant capital, no risk caps, no production filters. Real production has:

1. **Account balance** that grows with profit and shrinks with losses (compounding)
2. **RiskManagerService** rejecting trades that would breach 4 portfolio caps
3. **MetaDecider Rule F5** rejecting trades that fight the currency strength index
4. **Spread / hours / calendar** gates rejecting trades in unfavourable conditions

Until backtest models these, the gap between backtest Sharpe and live Sharpe is unmeasured.

This phase fills that gap. **One sub-phase (J-1) is also a real return-rate lever** — compounding turns a 4%/month flat-balance backtest into a 60%/year compound return, which is the path to the user's 10%/month target with reasonable leverage.

---

## Sub-phases

### J-1: Account compounding (CRITICAL for 10%/month)

**Implementation:**
- Track `running_balance_jpy`, starting at `--initial-balance-jpy`.
- After each fold: `balance += fold_pnl_jpy`.
- Per-trade size_units uses `running_balance` instead of constant `initial_balance`.
- New CLI flag: `--enable-compounding`.

**Effect:**
- Without compounding: 1-year backtest at 4%/month flat → ~48% total return
- With compounding: 1-year at 4%/month compound → ~60% total return
- For 10%/month target: ~213% annualized vs ~120% simple

This isn't just realism — it's a **capital-efficiency lever** that shows up directly in PnL.

**Effort:** 1-2h. **Calibration prior:** essentially deterministic — compounding always lifts return given positive expectancy. Verification only.

### J-2: RiskManager 4-constraint gate

**Implementation:**
- Mirror `RiskManagerService.allow_trade` logic in backtest:
  - C1: `concurrent_open_positions < max_concurrent` (default 5)
  - C2: per-instrument exposure ≤ `max_per_instrument_pct` (default 50%)
  - C3: per-direction exposure ≤ `max_same_direction_pct` (default 70%)
  - C4: SUM(per-trade risk_pct) ≤ `max_total_risk_pct` (default 5%)
- Apply at SELECTOR pick time, after greedy de-correlation (if any).
- Trades that fail any gate are skipped (don't contribute to ¥ PnL).
- New CLI flags: `--enable-risk-manager`, `--max-concurrent`, `--max-per-instrument-pct`, `--max-same-direction-pct`, `--max-total-risk-pct`.

**Effect:**
- Trades reduced ~10-25% (exact depends on caps).
- DD reduced significantly (no more 3 USD-cluster long trades concurrent during USD weakness).
- Sharpe likely ↑ 5-10% from variance reduction.
- PnL likely ↓ a few percent.

**Effort:** 3-4h. **Calibration prior:** PARTIAL GO ~70% (Sharpe up, PnL slightly down — net realism win).

### J-3: MetaDecider Rule F5 CSI filter

**Implementation:**
- Compute `CurrencyStrengthIndex` per bar (uses log-return averaging across pairs containing each currency, then z-score). Already in production via `src/fx_ai_trading/services/currency_strength.py`.
- Apply Rule F5: reject trade if direction conflicts with strength index threshold (e.g. long USD-base when USD CSI z-score < -1.5).
- New CLI flags: `--enable-csi-filter`, `--csi-z-threshold` (default 1.5).

**Effect:**
- Trades reduced 10-20% (filters out trades against macro flow).
- Per-trade EV likely ↑ (the filter removes the worst trades by hypothesis).
- Sharpe ↑ 3-8%.

**Effort:** 2-3h. **Calibration prior:** PARTIAL GO ~60% (CSI was already merged in Phase 9.3 with positive verdict).

### J-4 / J-5 / J-6 / J-7 (deferred)

- J-4 time-of-day filter: ~30 min, low priority
- J-5 ATR regime EV weighting: ~2-3h, depends on existing inclusion in v22
- J-6 dynamic spread (per-bar from m1 bid/ask): ~4-6h, realism > lever
- J-7 execution latency simulation: ~1-2h, low priority

These are sequenced after J-1/J-2/J-3 deliver concrete results.

---

## Implementation strategy

Single new script `scripts/compare_multipair_v23_realism.py` (clone of v22) with **independent CLI flags** for each sub-phase. Default: all OFF (reproduces v22 exactly). Flags can be enabled in any combination.

This lets one eval run sweep all combinations:
- v22 baseline (risk-sizing only)
- v23 + compounding
- v23 + compounding + risk-manager
- v23 + compounding + risk-manager + CSI

so we see the marginal contribution of each lever.

---

## Verdict gates (per sub-phase)

| Sub | GO criterion |
| --- | ---          |
| J-1 | NetPnL(JPY, compound) > NetPnL(JPY, flat) — essentially automatic |
| J-2 | Sharpe(JPY) ≥ baseline AND DD%PnL(JPY) ≤ 80% × baseline |
| J-3 | Sharpe(JPY) ≥ baseline AND per-trade EV (JPY) ↑ |

---

## Calibration prior — full pack

- 70% — all three GO; combined Sharpe up ~10-20%, compounded PnL up substantially
- 20% — J-1 GO, J-2 / J-3 mixed (some constraints too restrictive)
- 10% — J-2 / J-3 hurt (filters too aggressive, kill ROI without DD benefit)

---

## Sequencing

1. **J-1** implementation + smoke (~1h coding, then queue eval)
2. **J-2** implementation + smoke (~3h coding, then queue eval)
3. **J-3** implementation + smoke (~2h coding, then queue eval)
4. Single combined eval run (all flags on) for closure
5. Closure memo + production-wiring plan addendum to live deploy plan
6. Production wire-up of accepted features (Phase 9.X-K)

---

## Files

- This memo: `docs/design/phase9_x_j_design_memo.md`
- Implementation: `scripts/compare_multipair_v23_realism.py` (new, evolves through J-1 → J-3)
- Eval logs: `artifacts/phase9_x_j_*.log` (per sub-phase)
- Closure: `docs/design/phase9_x_j_closure_memo.md` (after evals)

Master tip when authored: fd1d2f1.
