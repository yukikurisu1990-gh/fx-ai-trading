# Phase 9.X-L Design Memo — Time-of-day + Spread Filter (v25)

**Status:** kickoff. Implementation in progress.
**Date:** 2026-04-27.
**Anchor:** Phase 9.X-E v19 causal +mtf K=3 SELECTOR — Sharpe 0.158.
**Goal:** lift Sharpe via *subtractive* lever (remove low-EV trade conditions) instead of *additive* lever (add features/model classes/picks).

---

## Why this lever

External reviewer ranked this Rank-1 in the open-lever list (`docs/design/sharpe_improvement_brief.md` §9). The reasoning:

- Across 5 phases (9.17 / 9.17b / 9.19 / 9.X-A / 9.X-C/M-1) we confirmed the "trade-rate explosion + per-trade EV collapse" pattern.
- Within-OHLC feature engineering has saturated at Sharpe ~0.158 (Phase 9.X-B: vol/moments/mtf/all all tie within 0.003).
- Therefore: **subtract bad-condition trades** rather than add candidates.
- Time-of-day and spread are **structural priors** with economic justification — less overfit-prone than a learned meta-labelling Layer-2.

## Filter design

### F1: Time-of-day exclusion (UTC hours)

Exclude trades where `bar.timestamp.hour` is in a configured set. Default exclusions (justification in parens):

| UTC hour | Excluded? | Justification |
| ---      | ---       | ---           |
| 03-04    | ✓         | Tokyo lunch (12-13 JST) — minimum liquidity in Asian session |
| 21       | ✓         | NY close (16 NY) — MTM rush + spread widening |
| 22-23    | ✓         | Asian open hand-off — stale pricing risk |

(7 hours excluded out of 24 = 29% bars excluded if every hour traded equally; in practice ~15-20% of trades.)

Default `--exclude-hours-utc "3,4,21,22,23"`. Empty string disables.

### F2: Max spread filter (per-bar)

Skip trades where the current m5 bar's spread (in pips) exceeds a threshold. Spread proxy options (cheapest to most expensive):

1. **ATR-based proxy:** skip if `atr_14` > 95th percentile (per pair). No new data needed.
2. **Direct bid/ask:** compute spread at the bar's close from raw m1 bid/ask. More accurate but requires propagating bid/ask through feature pipeline.

For MVP we use option (1) **ATR-relative** filter via the `--max-atr-percentile` flag. Default 95 (skip top 5% high-vol bars per pair). Option (2) is left as v25.1 enhancement.

### Application order

Filters apply **post-SELECTOR**, after greedy de-correlation / RiskManager / CSI:

```
SELECTOR picks K candidates
  → (optional) Phase 9.X-G greedy de-correlation
  → (optional) Phase 9.X-J RiskManager 4-gate
  → (optional) Phase 9.X-J CSI Rule F5
  → Phase 9.X-L F1 time-of-day filter
  → Phase 9.X-L F2 spread/ATR filter
  → final list of trades, compute pip + JPY PnL
```

Picks failing any filter set `sel_cand_idx_per_rank[r, b] = -1` (no trade).

## CLI surface

```
--enable-time-filter             # toggle F1 (default off)
--exclude-hours-utc "3,4,21,22,23"
--enable-spread-filter           # toggle F2 (default off)
--max-atr-percentile 95          # 0-100; per-pair quantile threshold
```

Default OFF for both: v25 reproduces v24 exactly when filters disabled.

## Verdict gates

vs anchor (v19 causal +mtf K=3 lgbm_only Sharpe 0.158, PnL 11,414, DD%PnL 2.1%):

| Verdict | Per-trade Sharpe | Daily Sharpe | PnL retention |
| --- | --- | --- | --- |
| **STRETCH GO** | ≥ 0.20 | ≥ 1.5 | ≥ 0.85× anchor |
| GO | ≥ 0.18 | ≥ 1.0 | ≥ 0.85× anchor |
| PARTIAL GO | ≥ 0.165 | ≥ baseline | ≥ 0.80× anchor |
| NO ADOPT | < 0.165 | regression | < 0.80× anchor |

**Note:** this is the first Phase where we explicitly accept PnL DROPS (filtering removes trades). Acceptance criterion is Sharpe-priority; PnL must not drop more than ~20% (else operational PnL goal breaks).

## Calibration prior (mine; reviewer's was higher)

External reviewer rated this **Rank-1** with implicit "Sharpe 0.20 reachable." My quantitative analysis suggests this is optimistic:

- Tokyo lunch (~4% bars), NY close+Asia handover (~6%), weekend roll (~3%) ≈ **~13% of bars are structurally "bad."**
- If filter perfectly identifies these and they have 50% lower per-trade EV than average:
  - Expected per-trade Sharpe lift ≈ +0.005 to +0.015 → 0.163 to 0.173.
  - **Phase 9.11 0.20 gate not cleared by this alone.**
- Need to stack with Phase 9.X-H (calendar) + spread filter + risk-sizing for a path to 0.20.

Calibration:

- 60% — PARTIAL GO (Sharpe lift +0.005 to +0.015)
- 25% — GO (Sharpe lift +0.015 to +0.025)
- 10% — STRETCH GO (clears 0.20 alone — only if filter also captures hidden alpha I'm not modelling)
- 5% — NO ADOPT (filter strips good trades, PnL collapses)

## Implementation plan

`scripts/compare_multipair_v25_filter.py` — clone of v24:

1. Add per-bar UTC-hour and ATR-percentile precompute (in `_eval_fold` near pair_arrays construction).
2. Apply F1/F2 filters after the existing CSI / RiskManager filter blocks.
3. Add 4 CLI flags.
4. New summary block "PHASE 9.X-L - SUBTRACTIVE FILTER SUMMARY" showing trade count before/after, Sharpe lift, PnL retention.
5. Stack with realism pack (compounding + risk-mgr + CSI) for the headline eval.

## Sequencing

1. **Now:** v25 implementation.
2. After 1 of currently-running 3 evals completes (CPU slot frees up), kick off v25 with `--enable-time-filter --enable-spread-filter` + full realism stack.
3. Compare against v23 / v24 on per-trade Sharpe AND daily annualized Sharpe (Phase 9.X-K).
4. Closure verdict.
5. If GO/STRETCH GO: production wiring proposal.

## Risks

- **Filter too aggressive:** trade count drops 30%+, PnL drops too much, Sharpe stays flat or down.
- **Hour set wrong for our universe:** 20-pair includes JPY/EUR/GBP/AUD/NZD pairs — "Tokyo lunch" affects JPY pairs more than non-JPY. Universal hour exclusion may over-filter EUR_USD / GBP_USD. Future v25.1 could do per-currency-family exclusion.
- **ATR filter ≠ spread filter:** ATR captures volatility, not spread directly. If high-ATR bars actually have BETTER per-trade EV (volatility = opportunity), filter goes wrong direction.

## Files

- This memo: `docs/design/phase9_x_l_design_memo.md`
- Implementation: `scripts/compare_multipair_v25_filter.py` (new)
- Eval log: `artifacts/phase9_x_l_filter.log` (new, when kicked off)
- Closure: `docs/design/phase9_x_l_closure_memo.md` (after eval)

Master tip when authored: `fd1d2f1` + open PRs.
