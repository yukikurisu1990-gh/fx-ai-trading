# M15 — Economic Edge Source Expansion: the frozen plan

**`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `PRODUCTION_READINESS_NOT_CLAIMED`.**

**Frozen before the first external-data result was seen.** Base master
`cfe2f9499e7dac9d799fc1580be403830903d356` (the PR #470 merge). Nothing here may
be changed because of a result; a defect forces a recorded amendment, never an
edit.

---

## 0. Why the programme is changing shape

Four rounds established, on already-seen data, that the M15 price path carries
serial structure no matched null reproduces and that **nothing in it pays a
round trip**: fixed-horizon direction, conditional direction, retrace geometry,
monthly TSMOM and linear selection each left no reproducible candidate. The one
positive was negative in a useful way — **tick volume carries clear incremental
information about future absolute movement and essentially none about
direction** (Spearman `+0.124 / +0.148` against `−0.0014 / +0.0013`).

That is the shape of the problem, and it suggests the wrong question was being
asked. Price alone was being made to answer *when* and *which way*
simultaneously. This package separates them:

* **Layer A — Expected Return.** Which side is there an economic reason to hold?
* **Layer B — Opportunity / Timing.** When is holding it worth the cost?
* **Layer C — Execution / Portfolio.** How is it held cheaply?

**Layer C may not manufacture an edge.** A basket construction that turns a
zero-expectancy signal positive is a measurement artefact, not a strategy.

## 1. The research questions, in the order they will be answered

1. **Is there a public, reproducible carry data source that covers the eight
   currencies `PAIRS_20` needs, over the three already-seen panels, without
   look-ahead?** If not, the carry branch stops before it starts.
2. **Does a simple carry signal have gross economics, and is the return carry
   income or spot movement?** Confusing the two is the classic carry error.
3. **Can tick volume say *when* a slow signal is worth holding**, rather than
   which way to hold it?
4. **Does combining them beat either alone**, after cost?
5. Only if all four clear: **does a bounded model beat the simple architecture?**

## 2. Authorisation and hard boundaries

Granted for this package by human + ChatGPT: **investigation and acquisition of
new public information sources** — policy rates, interest-rate differentials,
central-bank rates, publicly accessible carry data — with provenance recorded.

**Stop and refer, do not proceed autonomously:** a paid contract, a metered API,
a new account, entering a secret, or any broker permission. Also, unchanged from
every prior round:

* the fresh historical pool `2016-06-02 … 2021-04-25`;
* the historical OOS slice, the dead window, the future untouched epoch;
* Formal Confirmation, broker / demo / live, real orders, production.

A candidate that survives everything here returns to human + ChatGPT as
`READY_FOR_POWERED_FRESH_REPLICATION_DECISION`. **Fresh data is not read.**

## 3. Panels, and what may decide

| panel | span | role |
| --- | --- | --- |
| `momentum_2021_2023` | 2021-04-26 … 2023-04-25 | **deciding** |
| `supplemental_2023_2025` | 2023-04-26 … 2025-04-24 | **deciding** |
| `development_2025` | 2025-04-25 … 2025-12-28 | may contradict, may **not** decide |

The 2025 panel has had about 1,200 configurations searched over it. It is
reported everywhere and decides nothing — a rule this programme has broken by
omission before, so every stage reports it.

**A rate series will be fetched over a span wider than the panels** (rates are
slow and a signal needs history before the first panel bar). That is not a
market-data read: it is a macro series, and no FX price outside the three seen
panels is read at any point.

## 4. Currencies

`PAIRS_20` spans exactly eight currencies — **AUD, CAD, CHF, EUR, GBP, JPY, NZD,
USD** — all G10. A source that cannot cover all eight cannot serve, because a
cross-sectional ranking over a subset silently changes the universe.

## 5. Carry source selection hierarchy — fixed here

Ranked on **economic fidelity to what a position actually earns**, then on
acquisition reliability. The ranking is fixed now so that it cannot be
rationalised backwards from whichever source turns out to be easiest to fetch.

1. **Broker financing / rollover actuals.** What a retail position genuinely
   earns. Not available historically; recorded as the implementation gap and
   referred, never claimed.
2. **Swap points / forward points.** The market price of carry, and the closest
   tradable proxy. Preferred if a public, reproducible, eight-currency history
   exists.
3. **Short-term money-market rate differential** (overnight or 1-month
   interbank / risk-free rates). Economically close to forward points under
   covered interest parity, and far more likely to be publicly reproducible.
4. **Policy-rate differential.** Coarsest — it steps discretely and lags the
   market — but the most reliably public, and it captures the slow-moving
   component the multi-week horizons here care about.

**The selected primary and the fallback are recorded with their reasons in the
Stage 1 output**, whatever they turn out to be.

### 5.1 Vintage and revision — a hard rule

Policy and money-market rates are **not revised** the way macro statistics are;
a rate that was set on a date was known on that date. That is why they sit above
macro data in this hierarchy. Nonetheless:

* every rate observation is used with a **lag of at least one trading day** from
  its own effective date, so a same-day announcement cannot be traded on the bar
  that announced it;
* a series that *is* revised, or that is published with a delay, must be used at
  its **publication** date, not its reference date, or it must not be used;
* the acquisition record states, per series, whether it revises and what its
  publication lag is. If that cannot be established, the series is not used.

## 6. Carry construction — fixed here

For a pair `BASE_QUOTE`, holding **one unit long** earns approximately

```
carry_rate(BASE_QUOTE) = rate(BASE) − rate(QUOTE)
```

per annum, and the daily accrual applied to a position held over one calendar day
is `carry_rate / 365`. Sign convention: long `AUD_JPY` when AUD's rate exceeds
JPY's earns positive carry; the same position short earns its negative.

* **Accrual is by calendar day**, so a position held over a weekend accrues three
  days. This is what a broker does and it is where a naive weekday-only accrual
  overstates or understates by about 40%.
* Accrual is applied to the **held** position, using the same
  `position.shift(1)` convention `engine.evaluate` uses, so a decision at `t`
  accrues from `t + 1`.
* Carry is expressed in **pips** so it is commensurable with the price return and
  with cost: `carry_pips = carry_rate/365 × price / pip_size` per day held.

## 7. Signal families — at most three, no grids

* **C-A pair-level carry.** Long the pair when `rate(BASE) > rate(QUOTE)` by more
  than a fixed dead-band, short when below. One dead-band, derived from the
  cost geometry, not searched.
* **C-B cross-sectional currency carry.** Rank the eight currencies by rate; go
  long the top `k` and short the bottom `k` at the **currency** level, held
  through whichever `PAIRS_20` pairs express it. `k = 2` and `k = 3`. Two
  values, fixed.
* **C-C carry change.** The signal is the *change* in the differential over a
  fixed lookback rather than its level. One lookback, matched to the rebalance.

**No TP/SL grid, no threshold search, no per-pair tuning.**

## 8. Horizons and rebalancing — fixed here

Rebalance **weekly, fortnightly and monthly**. Three values. M15 is never the
entry frequency; it is used only to price the fills and to supply the Layer-B
activity context. Positions are held between rebalances.

## 9. Transaction cost

The committed `EXPLORATORY_ASSUMPTION`, unchanged: per side
`(observed spread_close_pips + 0.5) / 2`, so a round trip is one observed spread
plus 0.5 pips, written `C`. Every economic quantity is reported at `C` and at
`2C`. Carry accrual is a **separate line** and is never netted into "gross"
without being shown.

## 10. Carry metrics — all of them, every time

Gross **spot** return; **carry accrual**; total gross; cost; net; turnover and
annualised turnover; maximum drawdown; the number of pairs and currencies
carrying the result; JPY vs non-JPY; the largest single currency's share; the
top-ten-day contribution; and sub-period consistency across four blocks per
panel.

**The decomposition is mandatory.** A carry strategy that earned its interest and
gave it all back on spot is a different object from one where spot helped, and
the two must never be reported as one number.

## 11. Carry kill conditions — any one drops the branch

* gross **total** return consistently negative across the deciding panels;
* carry income does not cover spot losses at all;
* turnover and cost consume the result;
* one currency carries it;
* removing the ten largest days removes the profit;
* the sign reverses between the deciding panels;
* the gap between the public proxy and realisable financing is large enough that
  the public number cannot stand in for it.

**Thresholds are not adjusted to make a family pass.** If all three families
drop: `CARRY_EDGE_NOT_SUPPORTED`.

## 12. Carry pass condition — all of them

A clear economic rationale; low turnover; breadth across several currencies;
positive after `C` **or** gross headroom large enough that cost is not the
binding constraint; the same direction on both deciding panels; and a tail
dependence that is measured and bounded.

## 13. Stage 3 — tick volume as an opportunity source

Runs whether or not carry survives, because the question is independent.

**The question is not direction.** It is: *does tick volume identify periods in
which holding a slow signal is worth more?* Targets are future absolute return,
future realised volatility, and whether movement exceeds cost — never sign.

Representations, and no others: normalised level, rolling percentile, shock
(deviation from a trailing median), change, and persistence. **No feature
search.**

### 13.1 The opportunity oracle, and its kill condition

Before any model, the ceiling. An oracle that knows the future opportunity state
perfectly is `UPPER_BOUND_DIAGNOSTIC_ONLY`, and it answers: *how much could
perfect timing improve a base expected-return signal at all?*

**If the oracle's improvement over always-hold is small, the timing family is
dropped** and no model is fitted to it. The prior package established why: a
gate read off a foresight bound must be referred to the same bound on a matched
null, so the oracle's improvement is always reported **beside the same
computation on a matched null**.

**Tick volume may never be used to build a direction trade.** It has no
direction information; a rule that appears to find some is a bug.

## 14. Stage 4 — integration

Only if a Layer-A source has gross economics **and** Layer B has incremental
value. Four models, compared on the same population:

* **M0** no trade / benchmark;
* **M1** expected-return source alone;
* **M2** opportunity timing alone;
* **M3** expected-return × opportunity.

**The question is whether M3 improves on M1**, net, on both deciding panels. M2
alone is expected to fail and is run to show it.

Reported: gross, carry accrual, cost, net, turnover, maximum drawdown, tail,
currency breadth, panel stability, `2C`, the fraction of trades the filter
removes, and the incremental net value.

### 14.1 Portfolio construction

Currency-level baskets are permitted where carry is naturally a currency-level
object, including USD-exposure neutralisation and gross-exposure control.
**Simple, transparent, and no optimiser.** Layer C may not create an edge.

## 15. Stage 5 — the ML condition

All four, or no model is fitted:

1. the expected-return source has gross economics on its own;
2. something survives realistic cost;
3. the opportunity source has incremental information;
4. a simple interaction leaves visible selection room.

**A direction predictor is forbidden.** The model may only be an opportunity
probability, an expected-net-value ranking, a take/skip, or a position
confidence. At most 20 features from the named categories; a linear model **and**
LightGBM, never LightGBM alone; hyperparameters fixed and declared; purged
chronological walk-forward with an embargo.

**Success is economic**: net, drawdown and turnover efficiency out of time.
AUC is not success. Otherwise
`ML_NO_INCREMENTAL_VALUE_ON_ECONOMIC_EDGE_SOURCE`.

## 16. The calendar branch

Reached if carry is weak, or if carry survives and an exogenous timing source is
still wanted. Publicly accessible calendar data with clear provenance may be
acquired.

**The first question is not whether scheduled events predict direction.** It is
whether they define an **exogenous opportunity population** — a set of periods
picked out by something other than the price series itself. Event classes are
limited to policy-rate decisions, inflation, employment and major growth
releases. Around each: absolute move, realised volatility, spread, tick volume,
and whether movement exceeds cost. Direction is secondary and may not be the
headline.

**No news or sentiment research.**

## 17. COT and implied volatility

Not required in this package. If carry, volume and the calendar together do not
settle the question, the research case for each is written up — data, hypothesis,
frequency, turnover, difficulty — and referred. Acquisition cost or coverage that
cannot be established from public sources is a referral, not a guess.

## 18. Multiplicity boundary — fixed here

The families this package may evaluate, and no others:

| layer | families | cells |
| --- | --- | ---: |
| carry | C-A, C-B (`k ∈ {2,3}`), C-C | 4 |
| rebalance | weekly, fortnightly, monthly | × 3 |
| **carry total** | | **12** |
| opportunity | 5 representations × 3 targets | 15 |
| integration | M0–M3 | 4 |

**Twelve carry cells is the entire carry search.** Any statistic outside these is
`POST_HOC_DIAGNOSTIC_ONLY` and may not carry a verdict. Family-wise correction is
applied within each layer and reported.

## 19. Progression logic

| route | condition | next |
| --- | --- | --- |
| **A** | carry strong, volume useful | integrate → conditional ML → adjudicate |
| **B** | carry strong, volume useless | evaluate carry alone as a candidate |
| **C** | carry weak, volume useful for volatility only | calendar, as a new exogenous source |
| **D** | carry weak, volume economically useless | calendar |
| **E** | nothing has gross edge | write the COT / IV case and pause the programme |

A negative branch is **dropped**, not optimised. Continuing to search one family
until it turns positive is the failure mode these rounds exist to avoid.

## 20. Final classification

One of, or a more accurate status defined at the time:

* `ECONOMIC_EDGE_SOURCE_NOT_FOUND`
* `CARRY_DATA_SOURCE_NOT_RELIABLY_AVAILABLE`
* `CARRY_EDGE_NOT_SUPPORTED`
* `CARRY_EDGE_SUPPORTED_EXPLORATORY`
* `VOLUME_USEFUL_AS_OPPORTUNITY_FILTER_ONLY`
* `CARRY_PLUS_VOLUME_INCREMENTAL_EDGE_SUPPORTED`
* `CALENDAR_EVENT_OPPORTUNITY_STRUCTURE_SUPPORTED`
* `ML_NO_INCREMENTAL_VALUE_ON_ECONOMIC_EDGE_SOURCE`
* `EXPLORATORY_ECONOMIC_EDGE_CANDIDATE_READY_FOR_FRESH_REPLICATION_DECISION`

## 21. Fresh-replication candidate criteria

A candidate is only forwarded if it has **all** of: a clear economic hypothesis;
gross edge; positive after realistic cost; low or moderate turnover; several
periods; reasonable currency breadth; a tail dependence that is not
catastrophic; a simple baseline that works without a model; clear data
provenance; and every parameter frozen.

## 22. What may not change after a result is seen

The source hierarchy (§5), the vintage rule (§5.1), the carry construction and
sign convention (§6), the three signal families and their fixed parameters (§7),
the horizons (§8), the cost treatment (§9), the mandatory decomposition (§10),
the kill and pass conditions (§11–§12), the opportunity targets and
representations (§13), the integration models (§14), the ML condition (§15), the
multiplicity boundary (§18), and the progression logic (§19).

A defect found in an implementation is fixed and **recorded as a deviation** in
the results document, with the before-and-after measurement. A threshold is never
moved to change an outcome.
