# M15 Track A — Exploratory Strategy Research, Round 1

**`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `PRODUCTION_READINESS_NOT_CLAIMED`.**

Nothing in this document is evidence. No candidate is selected, no edge is
confirmed, no Formal Confirmation input is produced, and no `PASS`, `GO` or
`MEETS` is claimed anywhere. Formal Confirmation has not started and will use a
**future untouched epoch**; the historical `EXPLORATORY_OOS_SLICE` is not
pristine (`HISTORICAL_EXPLORATORY_OOS_PRISTINE_CLAIM_WITHDRAWN`) and is not used
here at all.

| | |
| --- | --- |
| Base master | `693d09d3d33dd68b5b30a5389e6ee9940116e9ce` |
| Span | `2025-04-25 … 2025-12-28`, 248 UTC dates |
| Pairs | the registered `PAIRS_20`, all twenty |
| Data | M15 derived from the development M1 corpus, 335,200 bars |
| Corpus status | `EXPLORATORY_SEEN_DATA` |

---

## 1. The headline

**The one signal that looked strong on the full sample is a first-half artefact,
and it is gone by the last quarter.**

Every return and oscillator feature tested has a **negative** information
coefficient against forward returns at every horizon from 1 to 192 bars, with
the sign consistent across pairs — the market looks mean-reverting at a ~24 hour
scale. Full-sample, the strongest cell is the past 96-bar return against the
forward 96-bar return: **mean IC −7.9%, negative in 20 of 20 pairs**.

Split by chronological quarter, that number falls apart:

| feature × horizon | Q1 | Q2 | Q3 | Q4 |
| --- | --- | --- | --- | --- |
| `ret_96` × h=96, mean IC | **−14.6%** | −9.5% | −1.4% | **−1.9%** |
| …pairs with negative IC | 18/20 | 17/20 | 11/20 | 11/20 |
| `ret_192` × h=96, mean IC | **−13.7%** | −8.0% | −2.2% | **+1.3%** |
| …pairs with negative IC | 18/20 | 12/20 | 11/20 | 10/20 |

Q4 is a coin flip. Median ATR over the same quarters: 8.81 → 7.07 → 6.51 → 6.89
pips, so the decay tracks a volatility compression.

The walk-forward confirms it directly. Over 52 (lookback, hold, entry-`z`)
configurations of the reversal strategy:

* first half: **45 of 52** configurations net-positive after cost;
* second half: **2 of 52**;
* rank correlation of net PnL between the halves: **−0.40**;
* taking the best first-half configuration into the second half: **−3,712 pips**.

A negative rank correlation is worse than no information: on this span, choosing
the strategy that worked best recently was actively harmful.

**So Round 1's answer to "does M15 look like it has an economic edge worth
pursuing?" is: not at the M15 decision scale.** Nothing that re-decides within a
day survived. The one direction that did survive a walk-forward operates at a
**4-to-6 day** horizon and trades 14-37 times a year per pair - which is barely
an M15 strategy at all, and which does not clear correction for the search that
found it (§6). Nothing here says an edge is impossible; it says everything found
at the M15 scale was regime-bound, and the thing that was not is under-powered on
eight months of data.

`TRACK_A_EXPLORATORY_STRATEGY_RESEARCH_ROUND_1_COMPLETED`. That token records
that a round happened, not that an edge exists.

## 2. What was run

### The cost assumption — `EXPLORATORY_ASSUMPTION`

Per-side cost = `(observed spread_close_pips at the trading bar + 0.5) / 2`,
charged per unit of `|position change|`. A round trip therefore pays one full
quoted spread plus one pad; a long-to-short flip pays two. **The halving is not
a discount**: returns are computed on the mid, a buy fills at the ask half a
spread above it and the matching sell at the bid half a spread below, so
charging a whole spread per side would double-count. A first drafting of the
engine did exactly that, and every result was twice as bad as the assumption
warranted until it was corrected.

Sensitivity is reported at ×1.00, ×1.25 and ×1.50 throughout.

R1's `cost_table` is **not used** — it is excluded from decision-bearing results
(`R1_UNAUTHORISED_COST_TABLE_OUTPUT_EXCLUDED_FROM_DECISION_BEARING_RESULT`), and
neither is the eligible-bar rate derived from it. The observed spread is used
instead, which §11 of the research instruction permits explicitly.

Median round-trip cost across the twenty pairs: **2.97 pips** (range 1.80 –
5.90). Mean absolute forward move: 3.7 pips at 1 bar, 14.9 at 16, 38.3 at 96.

### The leakage audit

The engine holds `position[t-1]` over the bar `t → t+1`, so a decision taken at
one bar's close cannot earn that bar's own return. Verified three ways:

* an oracle that knows the bar it will trade returns **+38,573** net pips on
  `EUR_USD` — the engine can reward foresight, so a null result is not the
  harness failing;
* the same oracle one bar stale returns **−20,648** — no same-bar target leak;
* every strategy's signal computed on a truncated prefix is identical to the
  full-sample computation over the overlap — no look-ahead in the features.

## 3. Round 1 results — all cost-inclusive

Pooled equal-weight across the twenty pairs, net pips **per pair** over the
whole span. Every number is negative.

| strategy | net | gross | cost | turnover/yr | pairs + | quarters + |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `C2_rev_96h96_z1.5` — fade the 24h move, hold 24h, only \|z\|>1.5 | **−53** | +61 | 114 | 92 | 9/20 | 2/4 |
| `C2_rev_96h96_z0` | −93 | +217 | 310 | 256 | 11/20 | 2/4 |
| `C2_rev_96h96_z1` | −102 | +97 | 199 | 167 | 9/20 | 2/4 |
| `C2_rev_192h192_z1` | −106 | +15 | 121 | 99 | 6/20 | 1/4 |
| `C2_rev_48h48_z1` | −225 | +105 | 330 | 283 | 5/20 | 0/4 |
| `baseline_rsi_14_30_70` | −706 | +148 | 854 | 740 | 0/20 | 0/4 |
| `baseline_donchian_48` | −708 | −108 | 600 | 533 | 1/20 | 0/4 |
| `baseline_ema_12_48` | −1,532 | −46 | 1,486 | 1,307 | 1/20 | 0/4 |

Two things fall out of that table and neither depends on the reversal finding:

* **Turnover is the whole game.** The ranking is almost exactly the inverse of
  turnover. The three baselines pay 600–1,486 pips of cost per pair to harvest a
  gross edge of ±150.
* **Direction matters, and it is not trend.** Mean-reversion families have
  *positive* gross (+61 to +310); trend and breakout families have *negative*
  gross (−46 to −216). Trend-following at M15 on this corpus was not merely
  eaten by cost — it was wrong before cost.

A parameter sweep of 51 (lookback, hold, `z`) reversal configurations found
**7** with gross > cost on the full sample, the best at gross/cost = 1.41 and
+1.45 net pips per trade over 542 pooled trades. §1 explains why that number
should not be believed.

## 4. Research log

| # | Hypothesis | Change | Result | Keep / drop |
| --- | --- | --- | --- | --- |
| 1 | The committed M15 derivation can be reproduced for exploration | Re-implement bucketing off the gated route | 20/20 pairs match R1's bars, complete/incomplete, rows, first/last ts — 0 mismatches | **keep** |
| 2 | Textbook rules have an edge at M15 | EMA cross, Donchian, RSI | −708 to −1,532 net; cost 600–1,486 vs \|gross\| ≤ 148 | **drop** |
| 3 | Some family survives cost | 15 strategies across trend / breakout / reversion / MTF | all negative; best −262 | **drop** |
| 4 | Something is predictable; find what | IC scan, 8 features × 6 horizons × 20 pairs | every feature negative IC at every horizon; `ret_96`×h=96 −7.9%, 20/20 pairs | **keep as the lead** |
| 5 | The cost model is right | Audit | It double-charged: full spread per side on mid-based returns | **corrected** (halved) |
| 6 | Low turnover + selectivity makes the reversal pay | Decide on a grid, hold, enter only on \|z\| tails | best −53 net (gross 61, cost 114); 9/20 pairs | **drop** — still negative |
| 7 | Some parameter cell clears cost | 51-config sweep | 7 clear it; best +783 pips pooled | **suspect** |
| 8 | …and would have been choosable in advance | Walk-forward, tune on H1, test on H2 | 45/52 positive in H1, **2/52** in H2, rank corr **−0.40**, best-of-H1 → −3,712 | **drop** |
| 9 | The edge is regime-bound, not absent | IC by quarter | −14.6% → −9.5% → −1.4% → −1.9%; 18/20 → 11/20 pairs | **keep as the finding** |

## 5. The parallel families

Three roles explored the remaining families in parallel. Each was given the
framework and the leading finding; none was given the others' conclusions.

### G — cross-pair / relative strength: **hypothesis not supported**

The hypothesis was that ranking twenty pairs against each other removes the
common USD move and isolates the *relative* overextension that reverts. Four
independent checks say otherwise, the first decisively:

* projecting the basket weights onto the null space of the 8x20 currency-exposure
  matrix - making it genuinely currency-neutral - removes **96% of the gross**
  (+1,706 to +81 pips) while cost falls only 515 to 390. The family's gross comes
  from the **net currency exposure the basket happens to carry**, not from
  relative value. Structurally unsurprising: that matrix has rank 7, so only 13
  of 20 dimensions are currency-neutral to begin with (checked here);
* fading the pair-specific residual after removing the currency graph gives gross
  **-30**;
* ranking by currency-strength spread is about the same as ranking by raw pair
  return (-430 vs -317);
* a matched time-series control **beats** the cross-sectional version on net
  (+1,774 vs +1,191).

Cross-sectional wins on exactly one axis: **cost robustness** (+676 vs +33 at
x2.0 cost). Its gated variants look strong on the full sample - 4/4 quarters,
18/20 pairs, all 18 parameter-jitter cells and all 20 leave-one-pair-out runs
positive - and still **fail walk-forward selection**: tuning on the first half
and then looking at the second gives -293, rank correlation -0.16. The role also
found its "dispersion gate" correlates 0.979 with plain move magnitude, so it is
not a cross-sectional-shape gate at all.

It found and fixed three sign/logic bugs in its own work, one of which produced a
*good-looking* result rather than an error.

### H — ML: **did not beat the simple rules**

On a matched Aug-Dec walk-forward window the best ML variant returned +157
pips/pair against the reversal benchmark's -71. Three things dissolve that:

* a **single raw feature** - fade the 4-day return - put through the identical
  fold, grid, train-side threshold and cost model returned **+173**, beating every
  model;
* a family-wise block sign-flip permutation over 57 variants gives the best
  **p = 0.699**, and the null's max median (+226.5) is *above* the observed best
  (+173.3);
* feature ablation is incoherent: removing any group collapses the result to about
  zero, and removing the **return** features - the ones with demonstrated IC -
  *improves* it.

Ridge beat LightGBM (OOS IC +0.076 vs +0.031) and its top coefficients are just
"the 4-day return, reversed". Effective sample: about 69 non-overlapping labels
per pair against 50 features. Label shuffles moved results by +/-120 pips, the
same order as the observed effect. The only statistically solid finding in that
family is that **high turnover reliably loses** (`ema_12_48`, p < 0.0001).

The role found and fixed three defects in its own harness, including a
cross-sectional grid that aligned by bar index and so had a median of **one pair
per decision timestamp**, and a meta-label gate that delayed entries by one bar
instead of removing them.

### D/E - regime and session: **conditioning did not help; horizon did**

* **Spread has almost no intraday structure** - 2.37 to 2.56 pips across hours
  0-20, a 7% range. Routing the same edge into a cheaper session is not available
  on this data. The one real cost feature is rollover: hour 21 averages **11.08
  pips** and reaches 24.7 on `GBP_AUD`.
* **Session:** the per-trade edge concentrates in the US session (3.00 vs 1.53
  europe, 0.66 asia) - but US is also the *widest* spread of the three, only
  10/20 pairs clear cost there, and the concentration exists in the first half
  only.
* **Volatility regime:** the 24h reversal is monotonically stronger in high-ATR
  regimes (3.16 vs 0.42 gross per trade), because a high-ATR 24h move is simply
  bigger against a fixed cost. It does not survive the half-split at that
  horizon; at a 4-day horizon it does.
* **ADX separates nothing.** Of 108 horizon x tercile x half cells, only 5 had a
  positive IC - there is no region where momentum works.
* **Spread-conditioned entry** is not a time-of-day proxy (checked) but saves less
  than it costs: gross falls faster than cost does.
* **Every gate lowered net** against the unconditioned base.

What worked was **horizon**, and it is a cliff rather than a frontier: between a
2-day and a 3-day lookback, cost per pair falls 271 to 86 *and gross rises* 259 to
381. At those horizons the walk-forward stops failing - 132/132 and 198/198
held-out cells net-positive at 4-day and 6-day lookbacks, against 0/33 at 24
hours. Parameter perturbation is 54/54 positive, leave-one-pair-out 20/20, and at
x3.0 cost 74-84% of the net survives, because turnover is 14-37 per year rather
than several hundred.

The role's most interesting secondary result: the ATR-high gate does **not**
raise net (+280 to +169) but it removes the JPY dependence of the held-out half
(non-JPY check +19 to +65) and roughly doubles the effective independent pair
count (6.5 to 12.6). Conditioning bought breadth, not return - on 96 pooled
trades, which is below the evidence floor.

Two defects in **this package** were found by that role and are fixed here:

* `runner._pooled` concatenated the per-pair series **by row number**. Pair bar
  counts differ (16,710-16,796), so row *i* was a different instant for different
  pairs. Now aligned on `ts`.
* `reversal_hold`'s `grid[::hold]` rebalance grid **locks to one hour of the day**
  on this corpus (136 of 175 rebalances at the same UTC hour), because a week is
  almost exactly 480 bars. The "best base signal" was therefore accidentally
  session-conditioned, and every single-phase number is one draw from a wide
  distribution.

## 6. The long-horizon result, and the test it had not had

The D/E role's headline - a 4-to-6-day reversal that passes walk-forward - was
the one promising thing in the round, and the role said plainly, twice, that its
1,078-fit search had **never** been corrected for multiple comparison, and that
the ML family's `p = 0.699` neither refutes nor defends it because that family
contained no long-horizon variant. So the correction was run here.

**First attempt, and why it was wrong.** A family-wise block sign-flip over 60
long-horizon variants gave the best `p = 0.031`. That used **single-phase**
signals. Sweeping the rebalance phase shows how much that matters:

| config | phase mean | median | min | max | sd | phases positive |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `lb768_h576_z0.0` | +277 | +285 | -171 | +713 | 284 | 12/16 |
| `lb576_h576_z0.0` | +317 | +277 | -88 | +867 | 290 | 13/16 |
| `lb384_h384_z0.0` | +263 | +300 | -44 | +508 | 159 | **15/16** |
| `lb288_h288_z0.0` | -5 | +9 | -190 | +162 | 110 | 9/16 |
| `lb96_h96_z1.5` | -43 | -52 | -173 | +46 | 60 | 5/16 |

The single-phase +668 behind `p = 0.031` sits near the top of its own phase
distribution. Re-running the same test on **phase-averaged** series - each variant
the mean of eight overlapping tranches, so a lucky offset cannot be the result:

| | |
| --- | --- |
| variants | 60 |
| best | `lb576_h384_z0.0`, **+322** pips/pair |
| individual `p` | 0.047 (z = 1.67) |
| **family-wise `p` for the best** | **0.304** |
| null max median / p95 | +247 / +496 |

**That is the honest number.** The long-horizon reversal is positive across a
broad plateau - the eight best variants sit at +249 to +322 with individual `p`
between 0.017 and 0.074 - and it does **not** clear correction for the search that
found it. It is better placed than anything else in the round: the ML family's
best was `p = 0.699` with the null median *above* the observation, and this one is
at least above its null median. That is all it is.

## 7. Candidates, and what was dropped

**Carried to Round 2, in order.** None is a candidate in the contract's sense;
each is a direction with the evidence for and against stated.

1. **Multi-day reversal, lookback 384-576 bars (4-6 days), hold 384-576, entry
   `z` 0-1.** Phase-averaged +249 to +322 pips/pair; passes the chronological
   walk-forward where the 24h version fails completely; 54/54 parameter
   perturbations and 20/20 leave-one-pair-out positive; keeps 74-84% of net at
   triple cost. **Against it:** family-wise `p = 0.304`; only 29-43
   non-overlapping windows per pair; effective independent pairs 6.5; the
   held-out half's survival is largely JPY; and eight months cannot distinguish
   "this is how FX behaves" from "this sample was range-bound".
2. **The ATR-high conditioning of (1), for breadth rather than return.** It costs
   net (+280 to +169) and buys independence (6.5 to 12.6 effective pairs, JPY
   dependence removed from the held-out half). On 96 pooled trades, which is
   below the floor at which any of this is evidence.
3. **A properly powered test design.** Both the ML and D/E roles reached the same
   wall independently: with about 70 independent observations per pair, the null
   standard deviation is +/-100 pips/pair and the question "did this win" is not
   answerable on this corpus. That is a design problem, not a strategy problem,
   and it is the highest-value thing to fix before more strategies are tried.

**Dropped, with reasons.**

| dropped | why |
| --- | --- |
| every 24h-and-shorter strategy | walk-forward 45/52 positive to 2/52, rank correlation -0.40; IC decays to zero by Q4 |
| trend and breakout families | **negative gross** before cost - wrong direction, not merely too expensive |
| ML | beaten by one raw feature; family-wise `p = 0.699`; incoherent ablation |
| cross-sectional relative strength | 96% of gross is net currency exposure; matched time-series control beats it |
| ADX regime classification | 103 of 108 cells show no sign flip |
| session conditioning | edge is in the widest-spread session, and only in the first half |
| spread-conditioned entry | saves less cost than the gross it removes |
| the "dispersion" gate | correlates 0.979 with plain move magnitude - not a cross-sectional gate |

## 8. A committed prohibition this round ran into

The exploratory package first imported `PAIRS_20` and `pip_size_for_pair` from
`scripts/m15_gate3a/`, and the M15 suite went red:
`test_the_package_has_no_reverse_caller_outside_itself_and_its_own_tests` pins
the reverse-caller set to that package, its own tests and Track A's gated route.
A research package is none of the three.

The tempting fix — add `scripts/research/` to `PERMITTED_CALLER_ROOTS` — is
exactly what that test's own comment says would "widen FB-8's pin rather than
scope it". The universe and the pip-size rule are restated in the research
package instead, checked once against the authority (same twenty pairs, zero
mismatches on the rule) with the cost of the copy written down where the copy
is. **The prohibition was obeyed, not amended.**

`scripts/research/` is outside the fingerprint surface, so none of this round
moved `e147542a…` or touched the two grants.

## 9. What would change the answer

Stated so a later round does not have to rediscover it:

* **A longer span.** Eight months contains one volatility regime and its decay.
  The Q1 behaviour may be the normal state and Q3–Q4 the anomaly, or the
  reverse; this corpus cannot distinguish them.
* **A cheaper cost.** At half the assumed cost several configurations clear.
  That is a broker question, not a research one, and inventing it would be the
  self-deception this round was told to avoid.
* **A different bar.** Every finding here is about M15. Nothing was tested at
  M5, H1 or H4, and the turnover arithmetic that dominates M15 is different at
  each.

## 10. Non-authorisation

This document authorises nothing. It reads no data outside
`2025-04-25 … 2025-12-28`, starts no stage, selects no candidate and creates no
formal evidence. R2, the OOS slice and Formal Confirmation each remain their own
Red gate requiring their own explicit human + ChatGPT act.
