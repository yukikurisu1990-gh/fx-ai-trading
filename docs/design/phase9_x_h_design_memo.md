# Phase 9.X-H Design Memo — Economic Calendar Features

**Status:** kickoff. Implementation pending Phase 9.X-G outcome.
**Date:** 2026-04-26.
**Anchor:** Phase 9.X-E v19 causal +mtf K=3 SELECTOR — Sharpe 0.158 / PnL 11,414 / DD%PnL 2.1%.
**Goal:** add awareness of macro release timing as orthogonal alpha source. Targets +5-15% PnL lift, possibly Sharpe lift via DD reduction (avoid mid-event noise trades).

---

## Why this is different

Every prior phase has asked: "what better signal can we extract from price/volume?" Phase 9.X-H asks: **"can we tell the model when high-volatility events are coming so it can specialize?"**

Day-of-FOMC bars behave structurally different from quiet Tuesday bars. Currently, the model treats them identically. Even minimal calendar awareness should let the model:

1. **Filter out pre-event high-uncertainty bars** (the SL is much wider than usual; entry EV is asymmetric)
2. **Specialize on post-event trend / mean-reversion** (NFP-type releases often produce 50+ pip continuation)
3. **Detect quiet regimes** (no event for ±2h → favour mean-reversion strategies)

---

## Data source plan

### Primary: curated CSV of high-importance events

For the 9-month walk-forward (2025-09 → 2026-06), enumerate the top events:

| Event | Currency | Frequency | Approx count over 9mo |
| ---   | ---      | ---       | ---                  |
| FOMC rate decision | USD | 8/year | ~6 |
| FOMC minutes | USD | 8/year | ~6 |
| Powell speeches | USD | irregular | ~10 |
| NFP | USD | monthly first Fri | 9 |
| CPI | USD | monthly | 9 |
| Core CPI | USD | monthly | 9 |
| Retail sales | USD | monthly | 9 |
| PMI flash (manuf+svc) | USD | monthly | 9 |
| ECB rate decision | EUR | 8/year | ~6 |
| ECB press conf | EUR | 8/year | ~6 |
| EZ CPI | EUR | monthly | 9 |
| BOE rate decision | GBP | 8/year | ~6 |
| UK CPI | GBP | monthly | 9 |
| BOJ rate decision | JPY | 8/year | ~6 |
| BOJ outlook report | JPY | quarterly | 3 |
| AU CPI | AUD | quarterly | 3 |
| RBA rate decision | AUD | 11/year | ~8 |
| NZ CPI | NZD | quarterly | 3 |
| RBNZ rate decision | NZD | 7/year | ~5 |
| BOC rate decision | CAD | 8/year | ~6 |
| Canada CPI | CAD | monthly | 9 |
| SNB rate decision | CHF | 4/year | 3 |

**Total: ~150 high-impact events over 9 months (~17/month).**

Curation effort: 4-6 hours scraping forexfactory historical export OR manual entry. Stored as `data/economic_calendar/events_2025_2026.csv`:

```
timestamp_utc,currency,event_name,importance
2025-09-17T18:00:00Z,USD,FOMC Rate Decision,high
2025-09-05T12:30:00Z,USD,Non-Farm Payrolls,high
...
```

### Out-of-scope for v1

- Actual / forecast / previous values (just timing first; if signal exists, layer values in v2)
- Surprise factors (actual − consensus)
- Speeches outside scheduled (would need NLP)
- Events for currencies not in our 20-pair universe (EUR, USD, JPY, GBP, AUD, CAD, NZD, CHF cover ≥95% of our pairs)

---

## Features to derive (per bar, per pair)

For each pair (e.g. EUR/USD), derive features for **both currencies** (EUR and USD events) and combine:

```
hours_to_next_event_base    # USD event for USD/JPY, EUR event for EUR/USD
hours_since_last_event_base
hours_to_next_event_quote   # JPY event for USD/JPY, USD event for EUR/USD
hours_since_last_event_quote
in_pre_event_window          # 1 if any event for either currency within next 30min
in_post_event_window         # 1 if any event for either currency within last 60min
in_quiet_window              # 1 if NO event for either currency within ±2h
event_importance_next        # 0/0.5/1 for none/medium/high (next 30min)
event_importance_recent      # 0/0.5/1 for none/medium/high (last 60min)
```

**9 new features per pair.** Pure-Python computation, vectorisable. No new data dep at runtime — calendar CSV bundled in repo.

---

## Hypothesis on lift

Three potential mechanisms:

1. **Trade filtering** (DD reduction). Avoiding pre-event bars eliminates the worst tail-loss trades. Expected DD%PnL improvement ≈ -0.5pt (2.1% → 1.6%). Indirectly lifts Sharpe via lower variance.

2. **Post-event specialization** (PnL+). Post-event bars have stronger directional persistence; LightGBM will learn to predict more confidently here. Expected PnL +5-10%.

3. **Quiet-window mean-reversion alpha** (PnL+). Quiet bars favour mean-reversion strategies; the model can learn `bb_pct_b` matters more in this regime. Expected PnL +3-7%.

Combined target: **+5-15% PnL, +0.005-0.020 Sharpe**. Stacks orthogonally with Phase 9.X-G if both succeed.

---

## Implementation plan — `scripts/compare_multipair_v21_calendar.py`

Will branch FROM v20 (post-Phase 9.X-G merge if GO, otherwise from v19) so the de-correlation lever stays available alongside calendar features.

### Pipeline addition

In `_build_pair_features`, add after `_add_orthogonal_features`:

```python
df = _add_calendar_features(df, instrument, calendar)
```

Where `calendar` is loaded once at script startup from CSV.

### CLI surface

```
--calendar-path PATH      # default: data/economic_calendar/events_2025_2026.csv
--feature-groups calendar # opt-in flag, like vol/mtf
```

When the calendar group is enabled, the 9 new feature columns are appended to each pair's feature dataframe and the model retrains with them.

---

## Verdict gates

| Verdict | Condition |
| ---     | ---       |
| GO         | Sharpe ≥ 0.18 AND PnL ≥ 1.10× anchor (anchor depends on 9.X-G outcome) |
| PARTIAL GO | Sharpe ≥ anchor |
| STRETCH GO | Sharpe ≥ 0.20 |
| NO ADOPT | Sharpe < anchor |

If Phase 9.X-G GOed at e.g. Sharpe 0.190, the 9.X-H anchor moves to that value. Calendar then needs to lift further.

---

## Calibration prior

This is a **data-axis** addition (like Phase 9.X-D DXY was). Track record on data axes is mixed:
- Phase 9.16 (20-pair): GO (+6%)
- Phase 9.X-D (DXY synthetic): NO ADOPT
- Phase 9.X-B (mtf, vol, moments): partial — depends on cell

Calendar is structurally different from DXY: DXY was a derivative of existing pair feeds (no new info). Calendar IS new info (timing of macro events, which is unobservable from price).

- 60% — PARTIAL GO (modest +5-10% PnL, Sharpe within ±0.005)
- 25% — GO (+10-15% PnL, Sharpe +0.005-0.015)
- **10% — STRETCH GO (Sharpe ≥ 0.20)** ★ best case (only if Phase 9.X-G also GO)
- 5% — NO ADOPT (calendar timing too coarse vs m5 bars)

---

## Sequencing

1. **Wait for Phase 9.X-G verdict** (eval running).
2. **If 9.X-G GO/STRETCH GO**: branch v21 from v20 (with de-correlation), add calendar features, eval. Calendar lift stacks on top of 9.X-G structural gain.
3. **If 9.X-G NO ADOPT**: branch v21 from v19, calendar becomes the primary lever. Curation + impl happens regardless because calendar is orthogonal to selector logic.
4. Curation: 4-6 hours (forexfactory historical + manual cleanup).
5. Implementation: 2-3 hours (`_add_calendar_features` + CSV loader).
6. Eval: 30-60 min.
7. Closure: 1 hour.

**Total Phase 9.X-H budget: ~1-1.5 days.**

---

## Risk register

| Risk | Mitigation |
| ---  | ---        |
| Calendar data quality | Cross-check 2-3 sources before commit; smoke-test on known FOMC dates. |
| Timezone handling | All timestamps stored as UTC; explicit `.tz_convert("UTC")` on load. |
| Lookahead from "next event" features | Compute strictly from event timestamps in the past; "next" means earliest timestamp > current bar time, no actual values used. |
| Calendar covers backtest period only | Live trading reads same CSV; calendar must extend forward through deploy period. Add monthly maintenance cron in runbook. |
| Pre-event filter eliminates good trades | Verdict gate verifies Sharpe AND PnL — if PnL collapses, NO ADOPT. |

---

## Files

- This memo: `docs/design/phase9_x_h_design_memo.md`
- Curated calendar: `data/economic_calendar/events_2025_2026.csv` (TBD)
- Implementation: `scripts/compare_multipair_v21_calendar.py` (TBD)
- Eval logs: `artifacts/phase9_x_h_calendar.log` (TBD)
- Closure: `docs/design/phase9_x_h_closure_memo.md` (after eval)

Master tip when authored: fd1d2f1 (after PR #224, #225, #226 merged; #227 still in flight).
