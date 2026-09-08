# M15 — Expectation Benchmark: Decision-Grade or Skip (results)

**`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `PRODUCTION_READINESS_NOT_CLAIMED`.**

Plan: `docs/research/m15_expectation_benchmark_plan.md`, frozen at `3d2ad14`
**before any relationship between an expectation and an FX return was
computed**, amended once (§15, A-1) before the test ran. Base master
`941fd0eca21fda6436b5f33a6a71bb3f02ea98eb` (the PR #472 merge).

**Programme decision: `REQUEST_QUOTE`, for one package and one only** — the CME
intraday data that answers Families 2 and 3 together. **Family 1 is closed and
no consensus data may be bought**, because the pre-registration forbids exactly
that purchase. If the CME package is declined, the recommendation becomes
`FX_SPOT_DIRECTIONAL_ALPHA_RESEARCH_CLOSED`.

---

## 1. The answer in six lines

* **The survey consensus was obtained for free and tested at decision-grade
  power. It is a powered null.** Pooled over 232 and 225 US release-times the
  design could detect **3.30** and **2.38** pips; it measured **−0.195** and
  **+0.612**, with opposite signs. Net is negative on both panels at single cost
  and at double.
* **The reason the previous package could not answer this was power, and the
  reason it could not see that was my own arithmetic.** The frozen power curve
  was built on raw pair returns instead of USD-oriented ones and understated
  every minimum detectable effect by about three times (amendment A-1).
* **The directional IC is inside its own null.** `+0.041` and `+0.038` against
  null standard deviations of `0.052` and `0.050`, permutation `p = 0.398` and
  `0.428`. An earlier draft called it "real in sign"; it is not distinguishable
  from noise and the claim is withdrawn.
* **What a paid consensus provider would sell is not the consensus.** Every G10
  currency's forecasts are already free and already in hand — **931 non-USD
  release moments** inside the two deciding panels. What is missing is the
  **release timestamp**, and §7 shows measurably that it cannot be reconstructed.
* **The free rates branch is `NOT_DECISION_GRADE_SKIP`.** The pre-registered
  400-day floor is not met (345 and 355 usable days) and the second panel's lead
  cell is underpowered besides.
* **The surviving residual is a sliver, not a band.** Combining both panels, the
  concentrated high-impact effect is `+1.0` pips with a 95% interval of
  `[−3.1, +5.1]`. Against this package's own ×2-cost standard the unexcluded
  window is **`E ∈ [4.2, 5.1]` pips** — and it is a *USD* residual that a *non-USD*
  purchase could not confirm.

## 2. Identity

| | |
| --- | --- |
| PR #472 | merged, merge commit **`941fd0eca21fda6436b5f33a6a71bb3f02ea98eb`** |
| verified before merge | head `75935b7` matched, CI green, `MERGEABLE`/`CLEAN`, no unresolved review thread |
| pre-registration | **`3d2ad14`**, before the first expectation-to-return statistic; amendment A-1 before the test |
| panels | `2021-04-26…2023-04-25` (624 trading days) · `2023-04-26…2025-04-24` (624) · `2025-04-25…2025-12-28` (212, **no coverage** — the archive ends 2025-04-07) |
| **new FX market-data spans read** | **none** |
| fresh pool `2016-06-02…2021-04-25` | **untouched** |
| purchases, trials, accounts, logins | **none** |

## 3. Free consensus audit

### 3.1 The source

| | |
| --- | --- |
| **provider** | Forex Factory historical calendar, archived as `Ehsanrs2/Forex_Factory_Calendar` (Hugging Face) |
| **licence** | MIT, public, not gated. No account, no key, no payment |
| **bytes / digest** | 68,231,084 · `sha256 = f4e92bca4168cfe6…` — **enforced**, not merely recorded: a different digest or row count raises |
| **rows / span** | 83,427 · `2007-01-01 … 2025-04-07` |
| **fields** | `DateTime, Currency, Impact, Event, Actual, Forecast, Previous, Detail` |

### 3.2 The one thing that is provable, and it passed

An archive backfilled with **revised** values would be worthless, and that is
testable against ground truth already held. Of 75 US `CPI m/m` rows overlapping
the ALFRED first-release table, **74 (98.67%)** match to the 0.1pp the archive
publishes. The exception is a rounding boundary.

`ACTUAL_IS_FIRST_RELEASE_NOT_A_REVISION`.

### 3.3 The one thing that is only falsifiable — and the pre-registered rule fired

No arrangement of values can *prove* a forecast was written down before the
print. It can be falsified two ways: a high exact-match share, or a ratio to the
naive previous-value benchmark so low that the forecast looks like the answer.
The rule was `min(ratio) > 0.10` **and** `max(exact) < 0.60`, over all eighteen
signals. **It fired**, on the ratio clause:
`FORECAST_BEHAVIOUR_INCONSISTENT_WITH_A_PRE_RELEASE_SURVEY`.

| signal | n | exact `A=F` | `corr(A,F)` | ratio to naive |
| --- | ---: | ---: | ---: | ---: |
| CPI m/m | 219 | 34.7% | +0.928 | 0.401 |
| Core CPI m/m | 219 | 38.8% | +0.711 | 0.817 |
| Non-Farm Employment Change | 220 | 0.9% | +0.896 | 0.346 |
| Unemployment Rate | 220 | 24.1% | +0.984 | 0.614 |
| Average Hourly Earnings m/m | 220 | 25.9% | **+0.255** | 0.660 |
| Retail Sales m/m | 219 | 7.8% | +0.927 | 0.325 |
| Core Retail Sales m/m | 219 | 10.1% | +0.913 | 0.377 |
| PPI m/m | 219 | 13.2% | +0.862 | 0.437 |
| Unemployment Claims | 953 | 2.4% | +0.969 | 0.791 |
| Durable Goods Orders m/m | 219 | 0.9% | +0.843 | 0.350 |
| Core Durable Goods Orders m/m | 219 | 5.9% | +0.466 | 0.607 |
| Housing Starts | 219 | 5.5% | +0.973 | 0.744 |
| Building Permits | 219 | 6.4% | +0.986 | 0.830 |
| Trade Balance | 220 | 2.3% | +0.982 | 0.516 |
| Core PCE Price Index m/m | 219 | **55.7%** | +0.848 | 0.539 |
| Personal Spending m/m | 219 | 26.0% | +0.984 | **0.146** |
| **Advance GDP q/q** | 73 | 2.7% | +0.992 | **0.083** ← fires |
| Prelim GDP q/q | 72 | 23.6% | +0.999 | 0.490 |

**Exactly one signal tripped the rule**, and it is `Advance GDP q/q` on the ratio
clause. Core PCE's 55.7% exact-match share is the highest in the table and it is
**below** the 0.60 threshold, so it did **not** fire — an earlier draft said "two
signals tripped it", which was wrong. `Personal Spending m/m` at **0.146** is the
nearest miss and is the reason the honest ratio range across the monthly series
is **0.146–0.830**, not the narrower band an earlier draft quoted.

Both low-ratio signals have a reading the rule could not see: last quarter's GDP
growth is a *meaningless benchmark* for this quarter's while forecasters nowcast
the advance estimate well from monthly data already public, and personal spending
is largely implied by retail sales, which prints first.

**The threshold was not relaxed because it fired.** Three things instead.

1. **The bias direction is stated.** A contaminated forecast makes
   `actual − forecast` smaller and its sign less reliable, so contamination
   **attenuates** a surprise. It cannot manufacture a forward return — the actual
   is contemporaneous with the event, not with the return being predicted. **A
   null obtained under possible contamination is therefore weaker evidence, not
   stronger.**
2. **A robustness check** drops the flagged families **at signal level** and
   rebuilds each composite (§5). It changes nothing.
3. **What the flag covers is stated.** `FLAGGED_FAMILIES` is `gdp` and `pce`;
   `pce` did not itself trip the rule and is included because its exact-match
   share is the table's highest. `Personal Spending m/m` sits inside `pce` and is
   therefore also dropped by the check.

Everything the rule did not flag argues the other way: `corr(A,F) = +0.255` on
average hourly earnings is the behaviour of a genuinely hard-to-forecast series,
which no backfilled column would produce.

### 3.4 The failure: the archive does not know what time it is

Against the 75 known US CPI release timestamps the archive is **17 hours early on
63 rows and 16 hours early on 11** — a scraper timezone defect, systematic
without being a constant, and large enough to move an event onto the wrong UTC
date. §7 shows it cannot be repaired.

> **The archive supplies values. ALFRED's vintage date plus the agency's
> documented 08:30 America/New_York rule supplies every timestamp**, and the
> conversion actually in use is asserted to equal the one this package froze.

`FREE_CONSENSUS_DECISION_GRADE_FOR_A_USD_KILL_NOT_FOR_A_MULTI_CURRENCY_CANDIDATE`.

### 3.5 The event table, and the signal that could never match

Ten US federal statistical agency release families, all printing at 08:30
America/New_York, each dated by its own ALFRED series: `CPIAUCSL` 84, `PAYEMS`
84, `RSAFS` 84, `PPIFIS` 84, `ICSA` 363, `DGORDER` 84, `HOUST` 82, `BOPGSTB` 84,
`PCEPILFE` 82, `GDPC1` 28.

Join: **1,476 matched**, 193 unmatched, **2 ambiguous** (both dropped, never
resolved to one row), 1,213 on the day before the release and 263 on the day
itself — the signature of §3.4, absorbed by the one-day tolerance. **750 distinct
release-times**, 182 of them created by two families printing at the same 08:30
and merged into one tradeable moment. **719 carry a composite surprise**, and 31
of those have a composite of exactly zero and take no position, so **688 are
tradeable**.

**`Prelim GDP q/q` matched nothing at all — 28 attempts, 0 successes.** ALFRED
dates only the vintage that first introduces a quarter, which is the *advance*
estimate, so the second estimate has no release date to join to. It is a
pre-registered signal that is structurally dead, and the join now reports
`signals_that_never_matched` so that cannot happen silently again.

The remaining 165 non-matches are the archive's own right edge: it ends
2025-04-07 while the ALFRED dates run to 2026-01, so each monthly signal loses
7–9 releases and weekly claims loses 36. Truncation, not selection.

## 4. Amendment A-1 — the power curve was wrong

The frozen §3.1 curve was built on **raw pair returns**. The test trades
**USD-oriented** returns; the seven USD pairs move together once oriented and
partially cancel when they are not, so the curve understated every minimum
detectable effect by about three times:

| | N | MDE, pips | ×2-cost break-even | N needed |
| --- | ---: | ---: | ---: | ---: |
| 1h, 2021–23 | 89 | **6.16** | 4.27 | **186** |
| 1h, 2023–25 | 87 | **6.04** | 4.09 | **190** |
| 4h, 2021–23 | 89 | **9.93** | 4.27 | **482** |
| 4h, 2023–25 | 87 | **10.58** | 4.09 | **583** |

Three consequences, all fixed before the test ran: **4h joins 12h and 1d as
excluded**; the population is widened by a mechanical rule rather than by
selection; and simultaneous releases become one moment.

**What makes the widening outcome-blind is the code path, not a claim.**
`minimum_detectable_effect` reads only `usd_move_pips` and `cost_pips`; the
signal enters solely as a presence filter, and the driver refuses a cell before
`evaluate` is ever called. The first run's console output — every cell refused —
is not evidence, because the artifact was overwritten by the post-amendment run.

## 5. Family 1 — the result

Pooled over all US 08:30 releases, 1 hour, entry at the open of the first M15 bar
starting **strictly after** the release, cost from that bar's own spread:

| | 2021–23 | 2023–25 |
| --- | ---: | ---: |
| release-times | **232** | **225** |
| pair-events | 1,624 | 1,575 |
| **gross pips** | **−0.195** | **+0.612** |
| cost | 2.118 | 2.049 |
| net (×1 / ×2) | −2.314 / −4.432 | −1.437 / −3.486 |
| **95% interval on gross** | **[−2.51, +2.12]** | **[−1.05, +2.28]** |
| **MDE at 80% power** | **3.30** | **2.38** |
| ×2-cost break-even | 4.24 | 4.10 |
| reference statistic (**not a `t`**) | −0.364 | +1.289 |
| permutation `p` | 0.846 | 0.488 |
| family-max corrected `p` | 0.980 | 0.781 |
| flagged signals dropped | **−0.470** (n=217) | **+0.623** (n=209) |
| directional IC | +0.041 | +0.038 |
| **IC null sd · permutation `p`** | **0.052 · 0.398** | **0.050 · 0.428** |
| hit rate | 49.1% | 51.8% |
| pairs with positive gross | 3 / 7 | 6 / 7 |

**`SURVEY_CONSENSUS_MACRO_EDGE_NOT_SUPPORTED_ON_USD_AT_DECISION_GRADE_POWER`.**

**A powered null, not an ambiguous one.** The design could see 3.30 and 2.38
pips. It saw −0.195 and +0.612, with opposite signs, and both intervals contain
zero.

Four things a reader is owed about it.

* **The IC is inside its own null.** `+0.041` and `+0.038` against null standard
  deviations of `0.052` and `0.050`, `p = 0.398` and `0.428`. On the first panel
  the IC is *positive* while the traded sign rule is *negative*, so it does not
  even corroborate the rule. An earlier draft called this "real in sign"; **that
  claim is withdrawn.**
* **The reference statistic is not a `t`.** It divides by an i.i.d. standard error
  over 1,624 correlated pair-events. Observed and null are divided by the same
  quantity so the permutation `p` is exact, but the number must not be read as a
  `t`; the honest event-level values are −0.17 and +0.60.
* **The three drop reasons are one fact counted three times.** With gross near
  zero and cost 2.1, `NEGATIVE_AFTER_COST` is arithmetically forced and
  `PANEL_SIGN_REVERSAL` follows automatically from two zero-centred estimates.
  Only the family-wise null is independent evidence.
* **The pooled cell is 44% weekly jobless claims** — 315 of 719 composite-bearing
  release-times, against CPI's 65 and employment's 72. The powered null is
  mostly a claims test diluted with a third high-impact events, which is exactly
  what §5.2 is about.

The **robustness check §3.3 forced changes nothing**: dropping the flagged
signals and rebuilding each composite leaves 217 and 209 release-times and a
gross of **−0.470** and **+0.623**.

### 5.1 Every per-indicator cell was refused, and that is the finding

| cell | N | MDE | ×2 break-even | N needed |
| --- | ---: | ---: | ---: | ---: |
| high-impact subset, 2021–23 | 77 | 6.40 | 4.31 | **170** |
| high-impact subset, 2023–25 | 74 | 6.39 | 4.11 | **179** |
| CPI, 2021–23 | 23 | 15.63 | 4.38 | 292 |
| CPI, 2023–25 | 20 | 11.97 | 4.05 | 175 |
| Employment, 2021–23 | 24 | 12.74 | 4.32 | 209 |
| Employment, 2023–25 | 24 | 13.05 | 4.12 | 241 |
| Jobless claims, 2023–25 | 101 | 4.22 | 4.09 | 107 |

`UNDERPOWERED_NOT_REPORTED_AS_EVIDENCE` on all of them. **No single indicator can
be tested on free US data**, and the high-impact rows are the specification: about
**175 high-impact release-times per deciding panel**, against 74–77 available.

### 5.2 What the pooled null rules out, and what survives

Pre-registered before the result. If an effect lived only in the high-impact
subset — `f = 77/232 = 0.332` and `74/225 = 0.329` — the pooled mean carries
`f × E`, so the smallest concentrated effect the **pooled** design could see is
`MDE / f`: **9.9** and **7.2** pips. (A-1 wrote `f ≈ 0.18` for CPI plus
employment alone, which gives 16.5 and 11.8; the four-family figure used here is
the tighter and more conservative of the two.)

Better than the design bound is the **measurement**. Combining the panels by
inverse variance — `sd_null` = 1.179 and 0.849 — gives a pooled gross of
**+0.337 ± 0.689**, 95% interval **[−1.01, +1.69]**, and therefore a concentrated
effect of **E = +1.0 with 95% interval [−3.1, +5.1] pips**.

So the surviving window is:

| standard | window for a concentrated high-impact effect |
| --- | --- |
| **×2 cost — this package's own gate everywhere else** | **`E ∈ [4.2, 5.1]` pips** |
| ×1 cost | `E ∈ [2.1, 5.1]` pips |

An earlier draft quoted "3 to 7 pips" by taking the lower bound at ×1 and the
upper bound from the design MDE rather than the measurement. **At the package's
own standard the window is a sliver.**

### 5.3 What that residual would be worth

Not previously quantified, and it should have been. The per-event standard
deviation of the seven-pair mean is `sd_null × √N` = **18.0** and **12.7** pips.
Per event the information ratio is `(E − cost) / sd`, and the seven pairs are one
bet, so it annualises over *events*:

| concentrated `E` | net per event | events/yr (US, ~38) | events/yr (G10, ~150) |
| ---: | ---: | ---: | ---: |
| 2.1 (×1 break-even) | 0.0 | 0.00 | 0.00 |
| **4.2 (×2 break-even)** | 2.1 | **≈ 0.8** | ≈ 1.7 |
| **5.1 (95% upper)** | 3.0 | **≈ 1.2** | ≈ 2.4 |

So at the very top of the unexcluded window there is a real strategy, and at the
bottom there is nothing. **That asymmetry is the whole case for a purchase, and
it is thin.**

## 6. Family 2 — the free branch, skipped

US 2-year Treasury yield (`DGS2`, FRED, free, 12,562 observations from
1976-06-01, `sha256 = 1fe65fff25b9…`). Pre-registered sign: a rise appreciates
the USD.

| cell | N | MDE | ×2 break-even | N needed |
| --- | ---: | ---: | ---: | ---: |
| lead, 2021–23 | 345 | 7.72 | 9.08 | 249 |
| lead, 2023–25 | 355 | 6.78 | 6.57 | 378 |
| same-day diagnostic | 435 / 455 | 6.14 / 5.35 | 4.61 / 4.30 | 771 / 704 |

**`NOT_DECISION_GRADE_SKIP`**: the pre-registered floor of **400 usable days is
not met on either panel**, and the 2023–25 lead cell is underpowered besides. **No
gross number was computed and none is reported.**

Two deviations from the plan are disclosed rather than absorbed, and both are
part of why the floor is missed. The plan said "the first M15 bar of day `t+1`";
the implementation enters at **22:00 UTC on day `t`** — after the H.15 print
around 16:15 New York, so no look-ahead, but in the rollover window, where the
round trip is **4.54 pips against 2.05–2.12 intraday**, and where a Friday has no
bar inside the entry tolerance, costing about a fifth of the days. And days with
**zero** yield change take no position and are filtered, which the plan's
population did not exclude.

**One property of the power gate this exposes.** `runnable` compares the MDE
against **twice that cell's own measured cost**, so an expensive entry raises the
bar the design must clear and makes the gate *easier* to pass. The 2021–23 lead
cell is `runnable` only because its 4.54 pip entry means only a ≥9 pip effect
would ever be worth trading. That is self-consistent — the gate asks "can this
*tradeable rule* be decided", not "is the underlying phenomenon detectable" — but
it is not the same question, and a cheaper entry hour would have failed the gate
instead. The cell was skipped on the day floor either way.

**The correct general statement**, replacing an overreach in an earlier draft: at
a one-day horizon the ratio of FX noise to a realistic round trip is such that
**these panels cannot decide a daily signal at this cost** — 700–800 usable days
would be needed against the ~455 available, and the lead specification has fewer
still.

`RATE_PATH_EVENT_REPRICING_NOT_TESTABLE_ON_FREE_DATA` — the hypothesis that
matters needs intraday short-rate futures, priced in §8.

## 7. What a paid consensus provider would actually be selling

The archive carries forecasts for every G10 currency. Inside the two deciding
panels there are **1,086 non-USD high-impact rows** with both an actual and a
forecast, forming **931 distinct (currency, date) moments**:

| CAD | GBP | EUR | AUD | NZD | CHF | JPY |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 287 | 226 | 217 | 213 | 86 | 46 | 11 |

That is **five times** the ~175 release-times §5.1 says a decision-grade
high-impact test needs. **The consensus is not the missing ingredient. The
timestamp is** — and the archive's dates cannot be repaired outside the US.

Measured against the scheduled central-bank meeting dates the previous package
acquired and validated against BIS rate changes with zero orphans:

| currency · event | rows | date **+0** = meeting | date **+1** = meeting | dominant rule |
| --- | ---: | ---: | ---: | :---: |
| USD · Federal Funds Rate | 34 | **27** | 7 | +0 |
| EUR · Main Refinancing Rate | 34 | **26** | 8 | +0 |
| EUR · Monetary Policy Statement | 34 | 7 | **27** | **+1** |
| JPY · BOJ Policy Rate | 34 | 5 | **29** | **+1** |
| AUD · Cash Rate | 43 | **34** | 9 | +0 |

`a_single_offset_would_repair_the_archive: false`. **The same ECB meeting appears
under two different date rules depending on which event row describes it**, because
the error depends on the release's local time of day — the thing being
reconstructed. The US branch survives only because ALFRED anchors the date
independently and the population sits in one narrow time band.

This section is produced by `consensus.non_usd_survey`, committed and written to
`s1_consensus.json`. An earlier draft carried these numbers in prose with no code
behind them, which is a failure mode this repository has shipped before.

**And it is the wrong purchase anyway.** The residual in §5.2 is a **USD**
residual — a possible effect in US high-impact releases. Multi-currency consensus
supplies **non-USD** events. If the mechanism is USD-specific the purchase cannot
confirm it; if it is not USD-specific, the plan already ruled that the powered USD
null closes it.

## 8. Paid provider comparison — full decision-grade cost, never a pilot

| provider | verdict | published price |
| --- | --- | --- |
| **Trading Economics API** — `Date` (intraday), `Actual`, `Previous`, **`Forecast` = survey consensus**, `TEForecast` = own model, `Revised` flag | **SKIP — FORBIDDEN BY THE PRE-REGISTRATION.** Plan §7: "a kill is final … no second consensus provider is bought to retry it". The field set is exactly right and it does not matter | $149/mo Standard, $299/mo Professional, billed yearly (≈ $1,788 / $3,588 a year) |
| **Econoday** — archive to 2001, "figures as initially reported", consensus = median of a weekly panel of 20 economists | **SKIP — FORBIDDEN BY THE PRE-REGISTRATION**, same clause | not public |
| **Databento** (CME Globex MDP 3.0) — **one package answers Family 2-paid and Family 3** | **REQUEST QUOTE** — the only purchase this package recommends considering | usage-based $/GB (rate not published); Standard $199/mo, **Plus $1,750/mo** (16+ yr L1), **Unlimited $4,500/mo** (all schemas) |
| Bloomberg / LSEG / FactSet / Macrobond / Haver | **SKIP — TOO EXPENSIVE FOR CURRENT EVIDENCE** | terminal-class, widely reported ≈$30k/yr |
| Consensus Economics | **SKIP — LOW INFORMATION VALUE** (monthly horizons, not release-level) | quote |
| CME DataMine options RR/BF · CLS spot flow | **SKIP — TOO EXPENSIVE FOR CURRENT EVIDENCE** | quote |
| any cheap scrape or one-month sample | **SKIP — INCONCLUSIVE**, the worst outcome this package recognises | low |

**Why the CME package and nothing else.** It is the only candidate that answers
**two untested families with one purchase** — ZQ/SR3 for the intraday
expected-rate-path repricing of Family 2, and 6E/6J/6B/6A/6C/6S trades for the
signed order flow of Family 3, in one dataset with one set of timestamps. Its top
tier is a **published** price and buys the whole history rather than a fragment,
so it does not violate the no-pilot rule.

Four things must be confirmed **before** any purchase and could not be
established from the public pages:

1. the historical coverage start for `GLBX.MDP3`, and whether the `trades` schema
   spans `2021-04-26 … 2025-04-24`;
2. whether `trades` carries the aggressor side — **without it Family 3 cannot be
   built at all**;
3. the CME licence pass-through for an individual researcher;
4. whether data downloaded during a subscription month may be retained for
   research afterwards.

No price is invented. Where none is public it is recorded as requiring a quote.

## 9. Decision-grade matrix

| source | new information | direction relevance | decision-grade? | total required cost | verdict |
| --- | --- | --- | --- | --- | --- |
| Free consensus archive (US) | high — the expectation, first time held | direct | **yes, for a USD kill** | **¥0** | **executed — powered null** |
| Free consensus archive (non-US) | high | direct | **no — no usable timestamp (§7)** | ¥0 | blocked, and forbidden to unblock by purchase |
| Free `DGS2` daily yields | medium | indirect | **no — 700–800 days needed** | ¥0 | **executed as a skip** |
| Paid consensus timestamps | high | direct | would be yes | ≈$1,788/yr | **SKIP — pre-registration forbids it** |
| CME intraday (Databento) | high — expected-path repricing **and** signed flow | direct | yes, if the four confirmations hold | **$1,750–4,500 for one month of full history** plus licence (≈¥26万–68万) | **REQUEST QUOTE** |
| Terminal-class vendors | high | direct | yes | ≈$30k/yr | **SKIP — TOO EXPENSIVE** |
| COT, IV, retail positioning, news sentiment | low or already tested | weak | — | — | **SKIP — LOW INFORMATION VALUE** |

## 10. ML

`ML_RE_ENTRY_CRITERIA_NOT_SATISFIED`. Not one of the five conditions holds: no
expected-return source survives a simple test; nothing is positive after cost;
the deciding panels disagree in sign; the per-indicator cells have no power; and
there is no second independent source to interact with.

## 11. Verification

* `tests/research` — **366 passed**, 41 of them this package's.
* **An independent review found nine mutations that the first suite let live.**
  Three were leak-shaped: an archive row dated *after* a release could join to
  it, an event's own surprise could enter its own scale, and the rates decision
  hour could move to before the number it trades on was public. **All nine are
  now killed**, along with three more added while fixing them — **12 of 12**, run
  with the bytecode cache cleared between mutations.
* The gate is enforced by the engine and pinned by tests: an underpowered cell
  reaches a verdict only as `NOT_DECISION_GRADE_SKIP`; the null draws **one sign
  per event**; the archive digest **raises** rather than being printed; the cost
  comes from the entry bar and not the exit; the horizon is exactly the bars it
  says; two candidate rows in one join window drop both; and a missing
  family-wise correction and a missing panel each fail closed.
* Every number in this document is machine-checked against the artifacts:
  **154 checks, zero mismatches** — which is how a wrong integrity verdict and
  five stale table values were caught before anyone read them.

## 12. Disclosed, not dressed up

* **The frozen power curve was wrong**; it is left in place, marked, and
  superseded by A-1.
* **The forecast column failed its own pre-registered integrity rule**, on one
  signal. The threshold was not relaxed; the bias direction is stated and a
  robustness check is reported.
* **`Prelim GDP q/q` is a pre-registered signal that matched nothing.**
* **The pooled test dilutes**, and it is 44% weekly jobless claims.
* **The "1h" horizon is 75 minutes** — entry-bar open to the close of the fourth
  bar after it. Forward-looking, so not a leak, but it is not 60 minutes.
* **The power gate's threshold moves with the cell's own cost** (§6), so it is a
  question about a tradeable rule and not about a phenomenon.
* **The family-max correction does not share draws across cells.** Each cell
  re-seeds its own null, which treats the cells as more independent than they are
  and **inflates** the corrected `p` — conservative, and it did not change a
  verdict.
* **`DGS2` is live and unpinned**: a re-run on another day gives a different
  digest and a slightly different `N`. Only the calendar archive is pinned.
* **The pipeline is not runnable from committed code alone**: `stage_consensus`
  reads the previous package's `s2_macro_releases.json` for the actual-integrity
  audit. It fails closed if absent.
* **The 2025 panel has no coverage** — the archive ends 2025-04-07 — so this
  package has two panels, not three.
* **The tail clause is uninformative when net is negative**; it did not fire and
  should not be read as having passed.
* **Family 3 was never tested**, only priced.

## 13. Statuses

`FREE_CONSENSUS_DECISION_GRADE_FOR_A_USD_KILL_NOT_FOR_A_MULTI_CURRENCY_CANDIDATE` ·
`ACTUAL_IS_FIRST_RELEASE_NOT_A_REVISION` ·
`FORECAST_BEHAVIOUR_INCONSISTENT_WITH_A_PRE_RELEASE_SURVEY` ·
**`SURVEY_CONSENSUS_MACRO_EDGE_NOT_SUPPORTED_ON_USD_AT_DECISION_GRADE_POWER`** ·
**`SURVEY_CONSENSUS_FAMILY_CLOSED_NO_FURTHER_CONSENSUS_PURCHASE`** ·
`NOT_DECISION_GRADE_SKIP` (free rates lead) ·
`FREE_CONSENSUS_EXISTS_FOR_EVERY_G10_CURRENCY_THE_RELEASE_TIMESTAMP_IS_WHAT_IS_MISSING` ·
`RATE_PATH_EVENT_REPRICING_NOT_TESTABLE_ON_FREE_DATA` ·
`SIGNED_ORDER_FLOW_NOT_TESTABLE_ON_FREE_DATA` ·
`ML_RE_ENTRY_CRITERIA_NOT_SATISFIED` ·
**`REQUEST_QUOTE`** (CME intraday only) — and, if that quote is declined,
**`FX_SPOT_DIRECTIONAL_ALPHA_RESEARCH_CLOSED`**.

Always binding: `NON_DECISION_BEARING_EXPLORATORY_ONLY` ·
`RESEARCH_SCRATCH_NON_AUTHORITATIVE` · `PRODUCTION_READINESS_NOT_CLAIMED` ·
fresh pool `2016-06-02 … 2021-04-25` untouched · historical OOS slice untouched ·
dead window untouched · future untouched epoch untouched · Formal Confirmation
not performed · no broker, demo or live contact · **no contract, trial, account,
subscription or payment**.
