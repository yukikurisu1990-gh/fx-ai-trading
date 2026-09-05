# M15 Track A — Exploratory Strategy Research, Round 2: results

**`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `PRODUCTION_READINESS_NOT_CLAIMED`.**

No edge is confirmed, no candidate is selected, no Formal Confirmation input is
produced, and no `PASS` / `GO` / `MEETS` is claimed. Formal Confirmation has not
started and will use a **future untouched epoch**; the historical
`EXPLORATORY_OOS_SLICE` is not read.

Base master `8617f7a1aab054d8f01d3aae63a411bf0a467dda`. The family was fixed in
`m15_track_a_exploratory_round_2_plan.md`, committed as `f63369e` **before** any
experiment ran — a review role verified the timestamps.

---

## 1. Classification

**`MULTI_DAY_REVERSAL_UNRESOLVED_INSUFFICIENT_DETECTION_POWER`.**

The effect is there in the sample and it is not an obvious artefact — it survives
delay, inverts symmetrically, and holds across the whole pre-registered
neighbourhood. It also cannot be separated from zero by the test this round
committed to in advance, on data this thin:

| | |
| --- | ---: |
| power **under the pre-registered family-max decision rule**, at the pre-registered effect | **0.29** |
| span needed for 80% power under that rule | **3.67×** ≈ +661 days |
| family-wise `p` after dropping the best **3** days of 212 | 0.053 → **0.157** |
| family-wise `p` for the **non-JPY 14** as their own family | **0.284** |
| family-wise `p` for the **JPY 6** as their own family | **0.025** |

The corpus cannot decide. That is the answer, and everything below is why.

## 2. Three corrections the review forced, before any result is read

Two review roles found the same two defects independently, and one found four
more. They are stated first because every number in the first draft of this
document was affected.

**The main deliverable was computed on a quantity that was not pre-registered.**
The plan fixes 8 rebalance phases; the power analysis used **4** — and the four
it used are the better half:

```
per-phase net, lb480/h480/z1.0: 224.5, -61.9, 65.8, -34.0, 260.9, 362.0, 671.4, 608.2
8-phase mean (pre-registered) = 262.1
the 4 that were used           = 305.7      their complement = 218.6
```

So Q3 sat on a number 17% larger than the registered one. Corrected throughout.

**The power arithmetic mixed one- and two-sided tests**, reporting a two-sided
MDE beside a one-sided power — each row's more flattering half. Now two-sided
throughout.

**The random-walk null permuted each pair independently**, which makes the twenty
pairs independent *inside the null*, shrinks its standard deviation and inflates
the z from about 2.9 to 4.6. Now a shared permutation key across pairs, so the
null keeps the cross-pair correlation the real panel has.

And the correction that goes the other way: the first draft's overlapping-window
inference compared the observed **mean** block IC against the spread of
**individual** null blocks. Against the right yardstick — the spread of null
*means* — the observed sits about 3.8 standard errors below the bias, not at its
median. The retraction in §4 is narrowed accordingly.

All of it now runs from committed code (`round2.py`, `round2_power.py`,
`round2_sensitivity.py`); the first pass produced six of seven artefacts from
scratch scripts that no longer existed, which is how these errors survived to
being written down.

## 3. What was run — 39 pre-registered configurations

27 primary (`lookback` × `hold` × `entry_z` over the 4-to-6 day neighbourhood) and
12 secondary (ATR terciles at the centre). Each phase-averaged over 8 rebalance
offsets; phase is a nuisance parameter, averaged and never selected. A review
role confirmed the shipped family matches the plan exactly — no extra cell, none
dropped, all 39 at `phases: 8`.

**All 27 primary configurations are net-positive**, +124 to +353 pips per pair,
12–18 of 20 pairs positive in each. Centre `lb480_h480_z1.0`:

| | |
| --- | --- |
| net / gross / cost | **+262** / +324 / 62 pips per pair |
| Sharpe-like (8-phase blend) | 2.18 |
| max drawdown | −96 pips |
| closed trades (pooled) | 353 |
| win rate / avg trade | 0.527 / +14.3 pips |
| turnover | 51.7 per year |
| pairs positive | 17/20 |
| top-pair share of \|PnL\| | 0.199 |
| net at ×1.25 / ×1.5 / ×2.0 / ×3.0 cost | +247 / +231 / +200 / **+138** |

Cost is 19% of gross, against 60–100% for everything Round 1 tried at the M15
scale. That is arithmetic, not a finding, and it is the only reason this horizon
is worth testing at all.

Two honesty notes on that table. The Sharpe-like 2.18 is the **8-phase blend's**;
single-phase Sharpe-likes across the eight run −0.39 to 3.75, and 15 of the 27
configurations contain at least one negative phase. And the 353 trades are not
353 observations: 34 non-overlapping windows per pair and 5.07 effective
independent pairs put the information content nearer 170.

## 4. Q1 — stability

The 31-day block IC of past-480 against forward-480 is negative in all eight
blocks (−23.8 to −44.2%), 16–20 of 20 pairs negative in each, no trend
(spearman −0.048, p = 0.91).

**Most of that is the overlapping-window bias.** An iid permutation of each
pair's own bar moves — same marginals, no autocorrelation — produces a mean
31-day block IC of −37.4% against the observed −46.7%, and **84% of null blocks
are negative**. "Negative in 8 of 8 blocks and 16–20 of 20 pairs" is what the
bias looks like; it is not evidence.

**But not all of it.** Against the correct yardstick — the sampling spread of the
null *mean*, sd 0.026, not the spread of individual null blocks, sd 0.35 — the
observed mean sits **−3.75 SE** below the bias (−2.46 SE under a shared
permutation). There is a real residual. The first draft said the observed IC was
"at the median of what a random walk gives", which came from comparing a mean to
a distribution of singletons. That sentence is withdrawn.

*(Two different block-IC constructions appear in the artefacts: `block_stability`
computes the past return from data before the block and averages −33.9%; the bias
check recomputes both legs inside the block and averages −46.7%. The comparison
above is self-consistent — observed and null use the same construction — but the
two numbers are not interchangeable and are now labelled.)*

The P&L series is free of that bias, and says less than it appears to. Block net
is 6/8 positive, but a bootstrap says a random 26-day stretch of this same series
is positive 75% of the time, so 6/8 is exactly what a stationary positive-mean
process gives. **And the series is not well described as stationary at all:**

```
top  3 days of 212 -> 41.1% of net       median day  +0.000
top 10 days of 212 -> 97.0% of net       days positive  49.5%
```

**What can honestly be said about Q1: there is no decay.** That is the whole
answer, and it is the one property that separates this horizon from the 24-hour
version Round 1 killed (IC −14.6% → −1.9%, walk-forward inverted).

## 5. Q2 — regime

**Volatility.** ATR terciles at `lb480_h480_z0.0`, which roughly partition the
unconditioned +337:

| bucket | net | trades | net per trade |
| --- | ---: | ---: | ---: |
| high | **+206** | 173 | 1.19 |
| mid | +79 | 176 | 0.45 |
| low | +35 | 210 | 0.17 |

Monotone. A review role checked whether this is just "bigger pips where pips are
bigger" by normalising each decision's P&L by the ATR at entry, and the ordering
survives (0.43 / 1.06 / 1.94, and 0.06 / 0.60 / 1.05 on non-JPY alone). So it is
a real statement — cost does not scale with the size of the move while the
reversion does — and the first draft called it "nearly a tautology" too harshly.
It is also **not established**: paired across pairs it is +1.48 with 14/20
positive, which at 5.08 effective independent pairs is t = 1.31, p = 0.13.

**Pairs, and the concentration that decides the round.**

| family (same 27 configurations, corrected separately) | best net | family-wise `p` |
| --- | ---: | ---: |
| all 20 pairs | +352.5 | 0.053 |
| **JPY, 6 pairs** | +843.9 | **0.025** |
| **non-JPY, 14 pairs** | +163.2 | **0.284** |

The JPY six alone test *better* than all twenty. The other fourteen do not clear
anything: their best configuration is +163 against a null max median of +79.

The first draft claimed the data supports "a thin general effect plus a large JPY
component", on the ground that non-JPY is positive in 27 of 27 configurations.
**That claim is withdrawn.** The 27 configurations are one overlapping
observation of the same 212 days, which is precisely what the family-wise
correction exists to price, and priced it says 0.284. Getting the non-JPY residual
to a decidable state would need roughly **+2,000 days** — about five and a half
years — even on the more generous single-variant rule.

What the data supports is: **substantially a JPY result, plus a non-JPY residual
this corpus cannot test.** Not "a JPY episode and nothing else" either — dropping
October 2025 still leaves the JPY bloc at +361 of +632, and 7 of 9 months
positive.

*(In pips the JPY bloc is 6.1× the non-JPY one. Normalised by each pair's own P&L
volatility it is 3.2×, so about half that gap is the pip unit rather than the
economics. The concentration is real; its size is overstated by the unit.)*

## 6. The ATR-high breadth mechanism

| | unconditioned | ATR-high |
| --- | ---: | ---: |
| net per pair | +337 | +206 |
| per-pair net **sd** | 477 | **235** |
| coefficient of variation | 1.42 | **1.14** |
| effective independent pairs | 5.07 | 6.27 |
| top-pair share of \|PnL\| | 0.179 | 0.174 |
| JPY share of total net | 0.75 | 0.68 |

**The mechanism is variance reduction, not de-concentration.** The filter halves
the dispersion of per-pair outcomes while cutting net by 39%, and barely moves
the JPY share (0.75 → 0.68) or the top-pair share. It buys breadth by removing
the tail of per-pair results — including the JPY pairs' large wins — not by
finding the effect anywhere new.

Round 1 reported 6.5 → 12.6 on this axis; measured here with a correlation-based
estimator it is 5.07 → 6.27. Different estimators, same direction, and the
smaller number is the one computed here.

## 7. Q3 — detection power, the round's deliverable

**Headline null — block sign-flip**, one shared draw across the family,
preserving the observed daily magnitudes:

| family | variants | best | family-wise `p` | null max median |
| --- | ---: | --- | ---: | ---: |
| primary | 27 | `lb576_h480_z0.0` +352.5 | **0.053** | +83.4 |
| secondary | 12 | `lb480_h480_z0.0` +336.9 | 0.030 | +45.4 |

**The secondary 0.030 does not mean what it looks like.** Its best cell is
`atr_bucket='all'` — the *same series* as a primary cell. Corrected inside the
27-cell primary family the identical cell gives **0.064**; the 0.030 comes from
correcting it against 11 ATR-conditioned neighbours instead of 26 unconditioned
ones. It is not a statement about the ATR axis. The ATR-conditioned cells taken
as their own 9-cell family give `atrhigh` p = 0.003, which is the number that
*is* about that axis.

**Power, against the rule the plan actually pre-registered.** §9 commits to a
family-max test, so the critical value is the null's 95th percentile, not a
per-variant z:

| | |
| --- | ---: |
| critical value (null max p95) | 357.5 |
| effect sd (block bootstrap) | 172.0 |
| **power at the pre-registered effect (+262.1)** | **0.29** |
| power at the family best (+352.5) | 0.49 |
| minimum detectable effect, 80% | **502.3** |
| **span multiple for 80% power** | **3.67×** ≈ **+661 days** |

A single-variant two-sided calculation on the same effect gives power 0.53 and
+220 days; that is the answer to a question this round did not ask. The
pre-registered rule is the family-max test, and under it the sample has **less
than a third** the power needed.

**How much rests on a handful of days:**

| days dropped | best net | family-wise `p` |
| ---: | ---: | ---: |
| 0 | 352.5 | **0.053** |
| 1 | 306.2 | 0.076 |
| 3 | 239.6 | **0.157** |
| 5 | 184.7 | 0.212 |
| 10 | 102.4 | 0.437 |

Three days out of 212 move it across the conventional threshold. The threshold
was never the binding fact.

**Supporting null — shared-permutation random walk**, and the same arithmetic run
separately on the two blocs. The strategy on random walks built from each pair's
own moves with a shared permutation key, so the cross-pair correlation survives:

| | all 20 | JPY 6 | non-JPY 14 |
| --- | ---: | ---: | ---: |
| observed net | +262.1 | +632.2 | **+103.5** |
| shared-RW null mean / sd | −46.0 / 105.0 | −49.4 / 191.6 | −44.5 / 106.2 |
| z / p | **2.93** / 0.01 | 3.56 / < 0.01 | **1.39** / 0.05 |
| bootstrap 95% CI | [+14.8, +519.0] | [+135.2, +1196.7] | **[−108.8, +328.2]** |
| P(net ≤ 0) | 0.019 | 0.005 | **0.174** |
| single-variant two-sided power | 0.53 | 0.64 | **0.15** |
| additional days for 80% | +220 | +113 | **+2005** |

The first draft's z = 4.57 came from permuting pairs independently. The strategy
does beat a random walk, which is worth knowing and is not the headline: the
shuffle also destroys volatility clustering, so a z-score-conditioned rule could
beat it without any mean reversion at all.

**The non-JPY column is the round in one place.** Its confidence interval
contains zero, its P(net ≤ 0) is 17%, its power is 0.15, and closing that would
take about **2,000 more days**. Every favourable number in this document is
carried by six correlated pairs.

## 8. What the review found that changes how to read this

Both roles ran their own mutation batteries. Four checks in this design turn out
not to be doing work, and one of those matters:

* **the one-bar shift is inert here** — removing it moves the best net 352.5 →
  353.5. At a 480-bar hold, one bar is 0.3% of the position's life. Causality is
  enforced by `_signal`'s windows, not by the shift; the shift's existence is
  demonstrable only by the same-bar oracle test (which correctly loses, −22,051);
* **the ATR rank can be made to read the future and the headline does not move** —
  the ATR cells change a lot (`atrhigh` 205.9 → 83.5) but the secondary family's
  maximum is a non-ATR cell, so it hides. **This family design cannot detect a
  leak on the ATR axis**, which is a design flaw and not a result;
* the rollover block suppresses 1.6% of grid points and moves the result by 0.2
  pips;
* 5-day and 1-day permutation blocks give nearly the same `p`.

What *is* load-bearing: phase averaging (best-phase 0.003 vs worst-phase 0.69)
and the shared sign draw (0.053 shared vs 0.196 independent). Both are
implemented the correct way round.

Causality itself is clean, constructively: perturbing everything after a cut
point changes no earlier signal across six configurations; prefix truncation
matches; the same-bar oracle loses; the span guard refuses every out-of-window
date and the cached bars contain no bar outside `2025-04-25 … 2025-12-28`.

## 9. Suspicious, stated rather than buried

* **97% of the net comes from 10 of 212 days**, the median day is 0.000, and
  49.5% of days are positive.
* **The JPY six carry it**; the other fourteen do not clear their own test.
* **`p = 0.053` is not a boundary, it is a band** — 0.021 to 0.053 depending on
  the permutation block length, and 0.157 after removing three days.
* **The neighbourhood was chosen by Round 1's uncorrected 1,078-fit search on the
  same corpus.** Pre-registering the neighbourhood does not undo that. Adding
  back the six `lb288`/`lb768` cells Round 1 looked at and set aside moves the
  primary `p` 0.053 → 0.068.
* **34 non-overlapping windows per pair, 5.07 effective independent pairs.**

## 10. Answers, and what would change them

**Q1 — stable across time?** No decay, and nothing stronger. The block-IC
evidence was mostly bias; the P&L evidence is consistent with a positive mean and
cannot distinguish that from the alternative on 212 days carried by ten of them.

**Q2 — an economically nameable regime?** Yes, weakly: reversion after large
multi-day moves, strongest in the top ATR tercile, and the ordering survives
volatility normalisation. It is a nameable hypothesis, not an established regime
(t = 1.31 at the honest degrees of freedom).

**Q3 — can this corpus decide?** **No.** Power 0.29 against the pre-registered
rule; 3.67× the span for 80%.

**What would change the classification.** More span — about 660 more days for the
full universe under the pre-registered rule, or roughly five and a half years to
make the non-JPY residual testable on its own. Nothing about looking harder at
these 212 days will do it, and this round deliberately did not try.

## 11. Non-authorisation

This document authorises nothing. No historical OOS read, no forward epoch, no
Formal Confirmation, no broker, no production claim, no new gate, no candidate
selection. R2 and Formal Confirmation each remain their own Red gate requiring
their own explicit human + ChatGPT act.

`TRACK_A_EXPLORATORY_STRATEGY_RESEARCH_ROUND_2_COMPLETED`.
