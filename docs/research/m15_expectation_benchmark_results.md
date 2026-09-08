# M15 — Expectation Benchmark: Decision-Grade or Skip (results)

**`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `PRODUCTION_READINESS_NOT_CLAIMED`.**

Plan: `docs/research/m15_expectation_benchmark_plan.md`, frozen at `3d2ad14`
**before any relationship between an expectation and an FX return was
computed**, amended once (§15, A-1) before the test ran. Base master
`941fd0eca21fda6436b5f33a6a71bb3f02ea98eb` (the PR #472 merge).

**Programme decision: `REQUEST_QUOTE`** — one narrow residual hypothesis
survives, its purchase specification is now exact, and it is the last thing this
programme should buy.

---

## 1. The answer in five lines

* **The survey consensus was obtained for free and tested at decision-grade
  power. It is a powered null.** Pooled over 232 and 225 US release-times, the
  design could detect **3.30** and **2.38** pips; it measured **−0.195** and
  **+0.612**. Net is negative on both panels at single cost and at double.
* **The reason the previous package could not answer this was power, and the
  reason it could not see that was my own arithmetic.** The frozen power curve
  was built on raw pair returns instead of USD-oriented ones and understated
  every minimum detectable effect by about three times (amendment A-1).
* **What a paid provider would sell is not the consensus.** The consensus for
  every G10 currency is already free and already in hand — **932 non-USD
  release moments** inside the two deciding panels. What is missing, and what
  cannot be reconstructed, is the **release timestamp**.
* **The free rates branch is `NOT_DECISION_GRADE_SKIP`, by measurement.** At a
  one-day horizon the FX noise is so large relative to a 2-pip round trip that
  345–455 days cannot decide; 249–771 would be needed.
* **One residual is real and narrow**: an effect confined to high-impact
  releases, between about **3 and 7–10 pips** per event. Below 3 it is not
  tradeable; above 7–10 the pooled null already excludes it. That band is worth
  one purchase and nothing more.

## 2. Identity

| | |
| --- | --- |
| PR #472 | merged, merge commit **`941fd0eca21fda6436b5f33a6a71bb3f02ea98eb`** |
| verified before merge | head `75935b7` matched, CI green, `MERGEABLE`/`CLEAN`, no unresolved review thread |
| pre-registration | **`3d2ad14`**, before the first expectation-to-return statistic; amendment A-1 before the test |
| panels | `2021-04-26…2023-04-25` (624 trading days) · `2023-04-26…2025-04-24` (624) · `2025-04-25…2025-12-28` (212, no coverage — the archive ends 2025-04-07) |
| **new FX market-data spans read** | **none** |
| fresh pool `2016-06-02…2021-04-25` | **untouched** |
| purchases, trials, accounts, logins | **none** |

## 3. Free consensus audit

### 3.1 The source

| | |
| --- | --- |
| **provider** | Forex Factory historical calendar, archived as `Ehsanrs2/Forex_Factory_Calendar` (Hugging Face) |
| **licence** | MIT, public, not gated. No account, no key, no payment |
| **bytes / digest** | 68,231,084 · `sha256 = f4e92bca4168cfe6…` |
| **rows / span** | 83,427 · `2007-01-01 … 2025-04-07` |
| **fields** | `DateTime, Currency, Impact, Event, Actual, Forecast, Previous, Detail` |

### 3.2 The one thing that is provable, and it passed

An archive that had been backfilled with **revised** values would be worthless,
and that is testable against ground truth already held. Of 75 US `CPI m/m` rows
overlapping the ALFRED first-release table, **74 (98.67%)** match to the 0.1pp
the archive publishes. The single exception is a rounding boundary.

`ACTUAL_IS_FIRST_RELEASE_NOT_A_REVISION`.

### 3.3 The one thing that is only falsifiable — and the pre-registered rule fired

No arrangement of values can *prove* a forecast was written down before the
print. It can be falsified two ways: by tracking the actual too closely (a high
exact-match share) or by beating the naive previous-value benchmark by so much
that it looks like the answer (a very low ratio). The pre-registered rule was
`min(ratio) > 0.10` and `max(exact) < 0.60`, over all eighteen signals.

**It fired.** `FORECAST_BEHAVIOUR_INCONSISTENT_WITH_A_PRE_RELEASE_SURVEY`.

| US indicator | n | exact `A = F` | `corr(A,F)` | `sd(A−F)` | ratio to naive |
| --- | ---: | ---: | ---: | ---: | ---: |
| CPI m/m | 219 | 34.7% | +0.928 | 0.134 pp | 0.401 |
| Core CPI m/m | 219 | 38.8% | +0.711 | 0.115 pp | 0.817 |
| Non-Farm Employment Change | 220 | 0.9% | +0.896 | 717k | 0.346 |
| Unemployment Rate | 220 | 24.1% | +0.984 | 0.466 pp | 0.614 |
| Average Hourly Earnings m/m | 220 | 25.9% | **+0.255** | 0.357 pp | 0.660 |
| Retail Sales m/m | 219 | 7.8% | +0.927 | 1.003 pp | 0.325 |
| PPI m/m | 219 | 13.2% | +0.862 | 0.365 pp | 0.437 |
| Unemployment Claims | 953 | 2.4% | +0.969 | 127k | 0.791 |
| **Core PCE Price Index m/m** | 219 | **55.7%** | +0.848 | 0.072 pp | 0.539 |
| **Advance GDP q/q** | 73 | 2.7% | +0.992 | 0.772 pp | **0.083** |

**Two signals tripped it, and both have an innocent reading that the rule could
not see.** `Advance GDP q/q` fails the ratio because the *benchmark* is
meaningless — the previous quarter's growth predicts this quarter's badly, while
forecasters nowcast the advance estimate well from monthly data already public.
`Core PCE Price Index m/m` has the highest exact-match share because it is
largely computable from CPI and PPI, both of which print before it.

**The threshold is not relaxed because it fired.** Instead, two things are done.

First, the direction of the bias is stated. A contaminated forecast makes
`actual − forecast` smaller and its sign less reliable, so contamination
**attenuates** a surprise; it cannot manufacture a forward return, because the
actual is contemporaneous with the event and not with the return being
predicted. **A null obtained under possible contamination is therefore weaker
evidence, not stronger**, and §5 carries that caveat.

Second, a robustness check drops the two flagged families and re-runs the
primary. It changes nothing (§5).

Everything the rule did not flag argues the other way: `sd(A−F) = 0.134pp` on
CPI m/m is the documented accuracy of the professional survey rather than
something implausibly small, the ratios sit at 0.33–0.82 across the monthly
series, and average hourly earnings shows `corr(A,F) = +0.255` — the behaviour
of a genuinely hard-to-forecast series, which no backfilled column would
produce.

### 3.4 The failure: the archive does not know what time it is

Against the 75 known US CPI release timestamps the archive is **17 hours early
on 63 rows and 16 hours early on 11**. That is a scraper timezone defect,
systematic without being a constant, and large enough to move an event onto the
wrong UTC date.

**It is not repairable, and §7 shows why.** For US releases the damage is
contained because ALFRED supplies the authoritative date and the join tolerates
one day. So:

> **The archive supplies values. ALFRED's vintage date plus the agency's
> documented 08:30 America/New_York rule supplies every timestamp.**

`FREE_CONSENSUS_DECISION_GRADE_FOR_A_USD_KILL_NOT_FOR_A_MULTI_CURRENCY_CANDIDATE`.

### 3.5 The event table that came out

Ten US federal statistical agency release families, all printing at 08:30
America/New_York, each dated by its own ALFRED series:

| family | ALFRED | release dates | family | ALFRED | release dates |
| --- | --- | ---: | --- | --- | ---: |
| cpi | `CPIAUCSL` | 84 | claims | `ICSA` | 363 |
| employment | `PAYEMS` | 84 | durable_goods | `DGORDER` | 84 |
| retail | `RSAFS` | 84 | housing | `HOUST` | 82 |
| ppi | `PPIFIS` | 84 | trade | `BOPGSTB` | 84 |
| | | | pce | `PCEPILFE` | 82 |
| | | | gdp | `GDPC1` | 28 |

Join: **1,476 matched**, 193 unmatched, **2 ambiguous**, of which 1,213 sat on
the day before the release and 263 on the day itself — the signature of §3.4's
defect, absorbed by the one-day tolerance. **750 distinct release-times**, 182
of them created by two families printing at the same 08:30 and merged into one
tradeable moment. **719 carry a composite surprise.**

## 4. Amendment A-1 — the power curve was wrong

The frozen §3.1 curve was built on **raw pair returns**. The test trades
**USD-oriented** returns, and the seven USD pairs move together once oriented
while partially cancelling when they are not. The curve therefore understated
every minimum detectable effect by about three times:

| | N | MDE, pips | ×2-cost break-even | N needed |
| --- | ---: | ---: | ---: | ---: |
| 1h, 2021–23 | 89 | **6.16** | 4.27 | **186** |
| 1h, 2023–25 | 87 | **6.04** | 4.09 | **190** |
| 4h, 2021–23 | 89 | **9.93** | 4.27 | **482** |
| 4h, 2023–25 | 87 | **10.58** | 4.09 | **583** |

Three consequences, all fixed before the test ran: **4h joins 12h and 1d as
excluded** (no US population reaches 480–580 events); the population is widened
by a mechanical rule rather than by selection; and simultaneous releases become
one moment.

The error was mine and it was found by the engine rather than by a reviewer —
the first run of the test refused every cell as underpowered, which is the gate
working.

## 5. Family 1 — the result

Pooled over all US 08:30 releases, 1 hour, entry at the open of the first M15
bar starting **strictly after** the release, cost from that bar's own spread:

| | 2021–23 | 2023–25 |
| --- | ---: | ---: |
| release-times | **232** | **225** |
| pair-events | 1,624 | 1,575 |
| **gross pips** | **−0.195** | **+0.612** |
| cost | 2.118 | 2.049 |
| net (×1) | −2.314 | −1.437 |
| net (×2) | −4.432 | −3.486 |
| **95% interval on gross** | **[−2.51, +2.12]** | **[−1.05, +2.28]** |
| **MDE at 80% power** | **3.30** | **2.38** |
| **×2-cost break-even** | **4.24** | **4.10** |
| `t` | −0.364 | +1.289 |
| permutation `p` | 0.846 | 0.488 |
| family-max corrected `p` | 0.980 | 0.781 |
| **gross, flagged families dropped** | **−0.241** (n=217) | **+0.585** (n=209) |
| directional IC | +0.041 | +0.038 |
| hit rate | 49.1% | 51.8% |
| pairs with positive gross | 3 / 7 | 6 / 7 |

**`SURVEY_CONSENSUS_MACRO_EDGE_NOT_SUPPORTED_ON_USD_AT_DECISION_GRADE_POWER`**,
dropped on three pre-registered clauses: the family-wise null, negative after
cost, and a sign reversal between the deciding panels.

**This is a powered null and not an ambiguous one.** The design could see
3.30 and 2.38 pips. It saw −0.195 and +0.612, with opposite signs, and both
confidence intervals contain zero while their upper bounds sit at roughly the
**single**-cost break-even. Any effect large enough to pay a realistic round
trip would have been found.

**The robustness check §3.3 forced changes nothing.** Dropping GDP and core PCE
— the two families the forecast audit flagged — leaves 217 and 209 release-times
and a gross of **−0.241** and **+0.585** pips against MDE 3.40 and 2.83. The
conclusion does not depend on the two signals whose forecast behaviour could not
be cleared.

One honest observation on the other side: the **directional IC is +0.041 and
+0.038 — the pre-registered sign, on both panels.** That is the shape the
programme has now met three times: a relationship that is real in sign and about
half the size of the transaction cost. It is not an edge, and it is reported
because a reader is entitled to see it.

### 5.1 Every per-family cell was refused, and that is the finding

No single indicator can be tested on free US data. The engine reports the number
each would need rather than reporting a null:

| cell | N | MDE | ×2 break-even | N needed |
| --- | ---: | ---: | ---: | ---: |
| high-impact subset, 2021–23 | 77 | 6.40 | 4.31 | **170** |
| high-impact subset, 2023–25 | 74 | 6.39 | 4.11 | **179** |
| CPI, 2021–23 | 23 | 15.63 | 4.38 | 292 |
| CPI, 2023–25 | 20 | 11.97 | 4.05 | 175 |
| Employment, 2021–23 | 24 | 12.74 | 4.32 | 209 |
| Employment, 2023–25 | 24 | 13.05 | 4.12 | 241 |
| Jobless claims, 2023–25 | 101 | 4.22 | 4.09 | 107 |

**`UNDERPOWERED_NOT_REPORTED_AS_EVIDENCE`** on all of them. The high-impact rows
are the purchase specification: **about 175 high-impact release-times per
deciding panel**, against 74–77 available from the US alone.

### 5.2 What the pooled null does and does not rule out

Pre-registered in amendment A-1, before the result. If an effect lived only in
the high-impact subset — a fraction `f = 0.33` of the pooled population — the
pooled mean would carry `f × E`, so the smallest concentrated effect this design
could see is `MDE / f`:

* 2021–23: `3.30 / 0.332` = **9.9 pips**
* 2023–25: `2.38 / 0.329` = **7.2 pips**

**A high-impact-only effect above about 7–10 pips per event is excluded. One
between about 3 and 7 pips is not.** Below 3 pips it does not clear a 2.1 pip
round trip and is not worth owning. That band — **3 to 7 pips, confined to
high-impact releases** — is the entire residual of Family 1, and §8 prices it.

## 6. Family 2 — the free branch, skipped by measurement

US 2-year Treasury yield (`DGS2`, FRED, free, 12,562 observations from
1976-06-01, `sha256 = 1fe65fff25b9…`). Pre-registered sign: a rise appreciates
the USD. The **lead** cell opens after 22:00 UTC, when the change is public; the
**same-day** cell is a diagnostic that trades on a number completed after its own
entry.

| cell | N | MDE | ×2 break-even | N needed |
| --- | ---: | ---: | ---: | ---: |
| lead, 2021–23 | 345 | 7.72 | 9.08 | 249 |
| lead, 2023–25 | 355 | 6.78 | 6.57 | 378 |
| same-day diagnostic, 2021–23 | 435 | 6.14 | 4.61 | 771 |
| same-day diagnostic, 2023–25 | 455 | 5.35 | 4.30 | 704 |

**`NOT_DECISION_GRADE_SKIP`.** The lead cell is below the pre-registered floor of
400 usable days on both panels and above its own break-even on the second. **No
gross number was computed and none is reported** — that is the difference between
this package and an ambiguous null.

Two things this measurement establishes anyway, and they matter more than the
test would have:

* **At a one-day horizon FX noise dwarfs the cost.** Deciding a daily signal on a
  624-day panel needs 700–800 usable days. **No daily-frequency hypothesis is
  decidable on these panels**, which retroactively explains a good deal of this
  programme's history.
* **A 22:00 UTC entry costs 4.54 pips round trip** against 2.05–2.12 intraday.
  The rollover window is not a place to open a position.

`RATE_PATH_EVENT_REPRICING_NOT_TESTABLE_ON_FREE_DATA` — the hypothesis that
matters needs intraday short-rate futures, priced in §8.

## 7. What a paid consensus provider would actually be selling

The archive carries forecasts for every G10 currency. Inside the two deciding
panels there are **1,088 non-USD high-impact rows with both an actual and a
forecast**, forming **932 distinct (currency, date) moments**:

| CAD | GBP | EUR | AUD | NZD | CHF | JPY |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 287 | 226 | 217 | 215 | 86 | 46 | 11 |

That is **three times** what §5.1 says a decision-grade high-impact test needs.
The consensus is not the missing ingredient. **The timestamp is** — and the
archive's dates cannot be repaired outside the US, which this measurement
settles:

| currency · event | rows | archive date **+1** = meeting date | archive date **+0** = meeting date |
| --- | ---: | ---: | ---: |
| USD · Federal Funds Rate | 34 | 7 | **27** |
| EUR · Main Refinancing Rate | 34 | 8 | **26** |
| EUR · Monetary Policy Statement | 34 | **27** | 7 |
| JPY · BOJ Policy Rate | 34 | **29** | 5 |
| AUD · Cash Rate | 43 | 9 | **34** |

**The same ECB meeting appears under two different date rules depending on which
event row describes it.** There is no single offset to correct, because the
error depends on the release's local time of day — which is the thing being
reconstructed. The US branch survives only because ALFRED anchors the date
independently and the population sits in one narrow time band.

So the purchase specification is exact:

> **A release timestamp with intraday precision and a stated timezone, for G10
> high-impact releases, covering `2021-04-26 … 2025-04-24`, alongside a survey
> consensus kept separate from any model forecast, and an actual as first
> reported.**

## 8. Paid provider comparison — full decision-grade cost, never a pilot

| provider | what it would supply | historical depth | timestamp | consensus / revision | published price | verdict |
| --- | --- | --- | --- | --- | --- | --- |
| **Trading Economics API** | calendar with `Date`, `Actual`, `Previous`, **`Forecast` = survey consensus**, `TEForecast` = own model, `Revised` flag | **not documented** | `Date` has intraday precision; **timezone not documented** | consensus and model forecast are separate fields, revisions flagged | **$149/mo** Standard, **$299/mo** Professional, billed yearly (≈ **$1,788 / $3,588 a year**) | **REQUEST QUOTE** — the field set is exactly right; two unknowns are fatal if wrong |
| **Econoday** | consensus, actual as initially reported, revisions, event timing | **back to 2001**, described as the only unbroken archive of figures as first reported | event timing history is a named product feature | consensus = median of a weekly panel of 20 economists | **not public** | **REQUEST QUOTE** — the closest match to the specification |
| **Databento** (CME Globex MDP 3.0) | trades with aggressor side, and short-rate futures — **answers Family 2-paid and Family 3 with one purchase** | subscription tiers publish the span they include | exchange timestamps, nanosecond | n/a | usage-based **$/GB, rate not published**; **Standard $199/mo** (1 year of L1 history), **Plus $1,750/mo** (16+ years of L1), **Unlimited $4,500/mo** (all schemas) | **REQUEST QUOTE**, and the strongest candidate — see below |
| Bloomberg / LSEG / FactSet / Macrobond / Haver | everything, in a terminal | ✓ | ✓ | ✓ | terminal-class, widely reported around **$30k a year** | **SKIP — TOO EXPENSIVE FOR CURRENT EVIDENCE** |
| Consensus Economics | monthly survey of macro forecasts, 1989→, research licence available | ✓ | quarterly/monthly horizons, **not release-level** | ✓ | quote | **SKIP — LOW INFORMATION VALUE** for an event study |
| CME DataMine (FX options RR/BF surface) | risk reversals and butterflies | product start | end of day | n/a | quote | **SKIP — TOO EXPENSIVE FOR CURRENT EVIDENCE** — a different family, not one of the three |
| CLS (spot FX flow) | the real spot flow | ✓ | ✓ | n/a | institutional, quote | **SKIP — TOO EXPENSIVE FOR CURRENT EVIDENCE** |
| any cheap calendar scrape / one-month sample | — | — | — | — | low | **SKIP — INCONCLUSIVE**, which this package treats as the worst outcome |

**Databento is the strongest candidate and the reason is structural, not
financial.** One CME package answers **two** of the three families — the
intraday expected-rate-path repricing of Family 2 and the signed order flow of
Family 3 — because ZQ/SR3 and 6E/6J/6B/6A/6C/6S sit in the same dataset with the
same timestamps and the same aggressor field. Its top tier is a **published**
price, and the subscription is the whole history rather than a fragment, so it
does not violate the no-pilot rule. What must be confirmed **before** any
purchase, and could not be established from the public pages:

1. the historical coverage start for `GLBX.MDP3` and whether it spans
   `2021-04-26 … 2025-04-24` in the `trades` schema;
2. whether `trades` carries the aggressor side, without which Family 3 cannot be
   built at all;
3. the CME licence pass-through for an individual researcher;
4. whether data downloaded during a subscription month may be retained for
   research afterwards.

**No number is invented here.** Where a price is not public it is recorded as
requiring a quote.

## 9. Decision-grade matrix

| source | new information | direction relevance | decision-grade? | total required cost | verdict |
| --- | --- | --- | --- | --- | --- |
| Free consensus archive (US) | high — the expectation, first time held | direct | **yes, for a USD kill** | **¥0** | **executed — powered null** |
| Free consensus archive (non-US) | high | direct | **no — no usable timestamp** | ¥0 | blocked on §7 |
| Free `DGS2` daily yields | medium | indirect | **no — 700–800 days needed** | ¥0 | **executed as a skip** |
| Paid consensus **timestamps** (TE / Econoday) | high — unblocks 932 non-USD moments | direct | **yes, if depth and timezone confirm** | TE ≈ **$1,788/yr** (≈¥26万); Econoday quote | **REQUEST QUOTE** |
| CME intraday (Databento) | high — expected-path repricing **and** signed flow | direct | **yes, if the four confirmations hold** | **$1,750–4,500 for one month of full history**, plus licence (≈¥26万–68万) | **REQUEST QUOTE** |
| Terminal-class vendors | high | direct | yes | ≈$30k/yr | **SKIP — TOO EXPENSIVE** |
| COT, IV, retail positioning, news sentiment | low or already tested | weak | — | — | **SKIP — LOW INFORMATION VALUE** |

## 10. ML

`ML_RE_ENTRY_CRITERIA_NOT_SATISFIED`. Not one of the five conditions holds: no
expected-return source survives a simple test; nothing is positive after cost;
the two deciding panels disagree in sign; the per-indicator cells have no power;
and there is no second independent source to interact with. A base that does not
stand on its own is not handed to a model.

## 11. Verification

* `tests/research` — **349 passed**, 24 of them this package's.
* The gate is enforced by the engine, not by prose: an underpowered cell cannot
  reach a verdict as a null, only as `NOT_DECISION_GRADE_SKIP`, and a test pins
  that. The null draws **one sign per event**, and a test shows the per-pair-event
  alternative shrinks the null by more than half.
* `ruff format --check`, `ruff check`, `tools/lint/run_custom_checks.py` — clean.
* The archive digest is checked against the frozen value at every acquisition.

## 12. Disclosed, not dressed up

* **The power curve in the frozen plan was wrong.** It is left in place, marked,
  and superseded by amendment A-1 rather than rewritten.
* **The forecast column failed its own pre-registered integrity rule**, on two
  signals with innocent readings the rule could not see. The threshold was not
  relaxed; the bias direction is stated and a robustness check is reported.
  As-of-ness of a forecast cannot be proven from values by any means.
* **The pooled test dilutes.** §5.2 states exactly what it can and cannot rule
  out, and that statement was pre-registered before the result.
* **The 2025 panel has no coverage** — the archive ends 2025-04-07 — so this
  package has two panels, not three.
* **The tail clause is uninformative here.** Net is negative on both panels, so
  a ratio of the top ten to a negative total carries no meaning; it did not fire
  and it should not be read as having passed.
* **Family 3 was never tested**, only priced.

## 13. Statuses

`FREE_CONSENSUS_DECISION_GRADE_FOR_A_USD_KILL_NOT_FOR_A_MULTI_CURRENCY_CANDIDATE` ·
`ACTUAL_IS_FIRST_RELEASE_NOT_A_REVISION` ·
`FORECAST_BEHAVIOUR_INCONSISTENT_WITH_A_PRE_RELEASE_SURVEY` (§3.3) ·
**`SURVEY_CONSENSUS_MACRO_EDGE_NOT_SUPPORTED_ON_USD_AT_DECISION_GRADE_POWER`** ·
`NOT_DECISION_GRADE_SKIP` (free rates lead) ·
`RATE_PATH_EVENT_REPRICING_NOT_TESTABLE_ON_FREE_DATA` ·
`SIGNED_ORDER_FLOW_NOT_TESTABLE_ON_FREE_DATA` ·
`ML_RE_ENTRY_CRITERIA_NOT_SATISFIED` · **`REQUEST_QUOTE`**.

Always binding: `NON_DECISION_BEARING_EXPLORATORY_ONLY` ·
`RESEARCH_SCRATCH_NON_AUTHORITATIVE` · `PRODUCTION_READINESS_NOT_CLAIMED` ·
fresh pool `2016-06-02 … 2021-04-25` untouched · historical OOS slice untouched ·
dead window untouched · future untouched epoch untouched · Formal Confirmation
not performed · no broker, demo or live contact · **no contract, trial, account,
subscription or payment**.
