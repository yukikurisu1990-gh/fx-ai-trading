# M15 — Exogenous Directional Information: results

**`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `PRODUCTION_READINESS_NOT_CLAIMED`.**

Plan: `docs/research/m15_exogenous_directional_information_plan.md`, frozen at
`a2dfccc` **before the first research statistic of this package was computed**,
amended three times (§23, A-1 to A-3) — each amendment before the statistic it
affects. Base master `b7073d5aa460438bfe5220e39e841ef9a75d9cc5` (the PR #471
merge).

**Final status: `EXOGENOUS_EXPECTED_RETURN_SOURCE_NOT_FOUND`.**

---

## 1. The answer

* **A forward-known anchor works, and it is the same non-edge as before, larger.**
  Scheduled central-bank meeting days move **1.58× / 1.63×** as far as matched
  control days, on 19 of 19 and 18 of 19 pairs, at `p = 0.005` — the permutation
  floor — on **all three** panels. The spread on those days is **1.01× / 1.02×**,
  wider, and the share of days clearing the round trip is **1.004× / 0.996×**.
  Movement rose by three fifths and the cost-clearing rate did not move at all.
* **The real-time macro surprise is buildable and carries no usable direction.**
  84 CPI releases reconstructed from ALFRED vintages against the Cleveland Fed's
  archived daily nowcast, with two independent sources agreeing on the release
  date **84 times out of 84**. The pre-registered direction is positive on the
  second deciding panel (`+9.1` and `+17.3` gross pips at 1h and 4h, `p = 0.050`
  and `0.025`) and **negative on the first**. Dropped on a pre-registered sign
  reversal, on 24 events against a floor of 30, and on being one currency.
* **Broker-realizable financing is not public.** Six anonymous probes: two 404s,
  one 403, and the only reachable OANDA route is developer documentation whose
  account endpoints need a token. Carry stays closed.
* **COT positioning is the first genuinely multi-currency direction test this
  programme has run, and it does not survive its own null.** Eight
  pre-registered cells. Seven fail on gross sign, breadth or cost. The eighth —
  `net_extreme` held four weeks — is **positive on all three panels** after cost
  (`+19.5 / +20.7 / +10.1` net pips per pair-event, tail share 0.09–0.11) and
  **cannot be separated from noise**: raw permutation `p = 0.199 / 0.149`,
  family-max corrected `0.701 / 0.498`. Its 80%-power detection threshold is
  **26.1 and 22.9 pips against observed 24.4 and 24.0** — the design is looking
  for an effect roughly its own size. **That is an underpowered null, not a
  refutation**, and it is the one thing in this package a human should rule on.

Nothing here is an expected-return source. Movement is not direction, and the
one direction candidate is inside its own noise band.

## 2. Identity

| | |
| --- | --- |
| PR #471 | merged, merge commit **`b7073d5aa460438bfe5220e39e841ef9a75d9cc5`** |
| verified before merge | head `d87afab` matched, CI green, `MERGEABLE`/`CLEAN`, no unresolved review thread |
| plan frozen | `a2dfccc`, before the first statistic; amendments A-1/A-2 and A-3 each before the statistic they affect |
| panels | `2021-04-26…2023-04-25` (624 trading days) · `2023-04-26…2025-04-24` (624) · `2025-04-25…2025-12-28` (212) |
| pairs | `PAIRS_20` |
| **new FX market-data spans read** | **none** |
| fresh pool `2016-06-02…2021-04-25` | **untouched** |
| historical OOS slice, dead window, forward epoch | **untouched** |
| declared search | **20 cells**: 6 event-structure, 6 macro, 8 COT |

## 3. The new data sources

Every one is public, keyless, and cost nothing. **No paid contract, no metered
API, no account, no login, no secret** — and the one route that would have needed
a token was recorded and not taken.

### 3.1 Central-bank scheduled meeting calendars

| | |
| --- | --- |
| **providers** | Federal Reserve, European Central Bank, Bank of Japan, Reserve Bank of Australia |
| **field** | the **announcement date** of a scheduled monetary policy decision |
| **extraction** | the document identifier, not the rendering: `monetaryYYYYMMDDa.htm`, `ecb.isYYMMDD`, `kYYMMDD.pdf`, and an RBA media release whose headline contains *Monetary Policy Decision* |
| **frequency** | 8 a year for the Fed, ECB and BoJ; 11 a year for the RBA through 2023 and 8 from 2024 |
| **timezone** | a plain date, treated as a UTC calendar date. **No time of day is acquired, so everything downstream is a day-level study** |
| **revision** | a decision date is not revised |
| **digests** | FOMC 164,831 bytes `sha256 = 7c4fe2c87049…`; BoJ 113,716 bytes `495f791ad6cf…`; ECB and RBA five pages each, first `706094d6b17c…` and `d577b88d6e43…` |
| **coverage** | USD 40, EUR 40, JPY 40, AUD 49 decision dates inside 2021–2025 |

The FOMC page yields 45 statement links for 2021–2026 and the BoJ page 168 back
to 2010; both are filtered to the calendar years, giving the 40 above.

**Cadence matches the published schedule on every year for every bank**, which is
the first integrity check. The second is stronger, because it uses a source the
calendar cannot have influenced: every policy-rate change in the BIS series over
2021–2025 must be explained by a scheduled meeting shortly before it.

| currency | rate changes | explained | effective-date lag, days | orphans |
| --- | ---: | ---: | ---: | ---: |
| USD | 17 | **17** | 2 | 0 |
| EUR | 18 | **18** | 7 | 0 |
| AUD | 16 | **16** | 2 | 0 |
| JPY | 4 | **4** | 2, 3, 4 | 0 |

Not one orphan, and the lag is a **constant per bank** — the BIS effective date
sits a fixed distance after the decision. A hallucinated or missing meeting date
would appear here as an unexplained change.

### 3.2 Four banks that could not be acquired

The Bank of England, the Bank of Canada, the Reserve Bank of New Zealand and the
Swiss National Bank return 403, 404 or 500 to every automated route tried —
index pages, year archives, RSS, sitemaps — or serve only future dates. Their
meeting dates are **not reconstructed by hand**; a date typed from memory into a
committed file is unverified scope inside an artifact.

So GBP, CAD, NZD and CHF carry no scheduled anchor here. 19 of `PAIRS_20` still
have a covered leg; **`GBP_CHF` is excluded by construction, not by result**.

### 3.3 ALFRED real-time vintages

| | |
| --- | --- |
| **provider** | Federal Reserve Bank of St. Louis, ALFRED |
| **series** | `CPIAUCSL` (670 vintages held) and `CPILFESL` (377) |
| **field** | the seasonally adjusted index level **as it stood on a given vintage date** |
| **publication timestamp** | the vintage date **is** the release date |
| **revision** | the entire point of the source: a month's value changes across vintages |
| **walked** | 91 vintages per series, 2019-01 to 2026-01, yielding **84** first releases each |
| **digests** | vintage lists `02fa28796b5f…` and `1865b75c374d…` |

### 3.4 The Cleveland Fed inflation nowcast — and what it is not

| | |
| --- | --- |
| **provider** | Federal Reserve Bank of Cleveland, inflation nowcasting web chart |
| **field** | the model's nowcast of month-over-month CPI and core CPI, **on each business day** of the target month and the following one |
| **coverage** | 159 target months, 2013-07 to 2026-09 |
| **bytes / digest** | 7,584,820 · `sha256 = b52088ef25f2…` |
| **revision** | the archive is presented as the historical path; whether it was recomputed cannot be settled from the file |

**It is a model nowcast, not a survey consensus.** No free source carries a
consensus history — every candidate is paid or licence-restricted — so
`REAL_TIME_MACRO_SURVEY_CONSENSUS_NOT_AVAILABLE_WITHOUT_A_PAID_CONTRACT` is
recorded and **no consensus was synthesised**. Every surprise below is labelled
`MODEL_NOWCAST_SURPRISE_NOT_SURVEY_SURPRISE`, and a null against it does not
refute a consensus-surprise hypothesis.

Two things support the archive being a real-time record rather than a re-run:
the CPI path **stops on the business day before the release**, and the actual is
placed **on** the release date. Neither is proof, and the residual risk is
disclosed rather than assumed away.

**One parsing defect mattered a great deal.** The chart axis interleaves marker
labels — `CPI May`, `PCE Jun` — between the business days, so there are more
categories than data points. Indexing the raw category list put every release two
or three business days early, and ALFRED's vintage date then agreed with the
archive on **0 of 84** releases. Aligning the datasets to the date labels only
makes it **84 of 84**. That agreement is now the check that the release calendar
is right, and it is pinned by a test.

### 3.5 CFTC Commitments of Traders

| | |
| --- | --- |
| **provider** | CFTC, *Traders in Financial Futures*, keyless Socrata endpoint |
| **field** | `lev_money_positions_long − lev_money_positions_short`, over `open_interest_all` |
| **frequency** | weekly |
| **as of** | **Tuesday** — 366 of 369 report dates; the other three are Mondays in holiday weeks |
| **published** | the following **Friday, 15:30 America/New_York** |
| **revision** | the CFTC republishes only on a stated correction and does not restate the as-of date |
| **coverage** | 369 weeks, 2019-01 to 2026-01, **all seven** non-USD currencies |
| **currency mapping** | AUD, GBP, CAD, EUR, JPY, CHF from the `CURRENCY` subgroup; **NZD from `CURRENCY(NON-MAJOR)`** as `NZ DOLLAR` (amendment A-2). USD has no contract and is the negative of the equally-weighted mean of the other seven |

### 3.6 What was not acquired, and why

* **Survey consensus** — paid or licence-restricted everywhere. Referred.
* **Employment surprises** — no public real-time expectation exists at any
  frequency. Not run.
* **GDP** — the Atlanta Fed GDPNow real-time archive exists and would give a
  clean surprise, but GDP is quarterly: about 18 releases across all three
  panels, one currency. The event-count rule kills it before it starts.
  **Acquirable and deliberately not acquired**, so a later session does not
  mistake the omission for an oversight.
* **Policy-decision surprise** against what was priced — needs OIS or fed funds
  futures history. No free source. Referred.
* **Broker financing** — §6.

## 4. Stage A — the forward-known event structure

### 4.1 What is compared with what

An event day is a UTC date on which the central bank of either leg held a
**scheduled** decision. A control day must match on **day of week** *and* on the
**tercile of trailing 60-day realised volatility**, and must carry at least 48
M15 bars. Every ratio the verdict reads is computed inside a (weekday × tercile)
cell and pooled; the null re-draws the event days **inside the same cells**, 200
draws, preserving both the weekday mix and the regime mix.

Two failure modes are being closed here at once. The previous package's headline
reversed when Sundays were matched away. And central banks meet more often in the
middle of a tightening cycle, so an unmatched comparison would partly measure
the cycle.

### 4.2 The result

| matched ratio | 2021–23 | 2023–25 | 2025 *(may not decide)* |
| --- | ---: | ---: | ---: |
| **absolute move** | **1.5827** | **1.6333** | 1.5597 |
| pairs agreeing | **19 / 19** | **18 / 19** | 17 / 19 |
| permutation `p` | **0.0050** | **0.0050** | 0.0050 |
| high–low range | 1.4564 | 1.4244 | 1.3531 |
| realised volatility | 1.4658 | 1.3169 | 1.2470 |
| tick volume | 1.1675 | 1.1175 | 1.1345 |
| **spread** | **1.0105** | **1.0165** | 1.0051 |
| **share clearing the round trip** | **1.0042** | **0.9958** | 1.0438 |

Event days per pair: 15 to 35 per deciding panel, against 471 and 472 control
days. `p = 0.0050` is the floor at 200 draws — no draw of 200 reached the
observed ratio on any panel.

`FORWARD_KNOWN_EVENT_OPPORTUNITY_STRUCTURE_SUPPORTED`, with
`EVENT_DAY_COST_ADVANTAGE_NOT_ESTABLISHED` beside it.

### 4.3 Why it is bigger than the last package's number, and why it still is not an edge

The previous package measured `1.33 / 1.13` around days a rate **changed**. This
is `1.58 / 1.63` around days a meeting was **scheduled** — a larger effect on a
larger and forward-known population. The reason is mechanical: the BIS effective
date sits 2 to 7 days after the decision (§3.1), so a ±1-day window around the
effective date frequently **missed the announcement day altogether**. The
forward-known calendar hits it directly.

And it is still not an edge, for the same reason as before. **Movement rises by
about three fifths while the share of days clearing the round trip does not move
at all** — 1.0042 and 0.9958 — because ordinary days already clear it. Magnitude
was never the binding constraint. Direction is, and a bigger move in an unknown
direction is a bigger loss half the time.

## 5. Stage C — the macro surprise

The pre-registered hypothesis: a higher-than-expected US CPI print is hawkish and
**appreciates the USD**. Long USD on a positive standardised surprise, in every
USD pair, entering at the open of the first M15 bar starting **strictly after**
08:30 America/New_York — 12:30 UTC under daylight time, 13:30 under standard —
and paying that bar's own spread.

Gross pips per pair-event:

| cell | 2021–23 | 2023–25 | 2025 |
| --- | ---: | ---: | ---: |
| `cpi_1h` | −3.697 | **+9.128** | −2.152 |
| `cpi_4h` | −3.980 | **+17.303** | −9.843 |
| `cpi_1d` | +14.104 | +13.925 | −0.261 |
| `core_cpi_1h` | −1.396 | +4.343 | −2.152 |
| `core_cpi_4h` | +0.072 | +7.874 | −9.843 |
| `core_cpi_1d` | +18.568 | +9.721 | −0.261 |

`MACRO_SURPRISE_DIRECTIONAL_EDGE_NOT_SUPPORTED`, on four pre-registered clauses:

* **`SINGLE_CURRENCY_USD_ONLY`** — true by construction and stated in the plan
  before anything was measured;
* **`FEWER_THAN_30_EVENTS_PER_DECIDING_PANEL`** — 24 in each;
* **`PANEL_SIGN_REVERSAL`** on `cpi_1h`, `cpi_4h` and `core_cpi_1h`.

The second deciding panel's `cpi_4h` reaches `p = 0.025` on its own null and the
first panel's is negative. **The sign is not inverted to fit** — the family is
dropped, which is the rule this programme adopted after a failed reversal rule
was nearly re-run as a momentum rule on the data that refuted it.

In 2025 the CPI and core CPI cells are identical because the two surprises
happened to share a sign on all six releases in that window; the ICs differ
(`−0.480` against `−0.474`), so the two series are distinct.

## 6. Stage D — broker financing

Six anonymous probes, no login attempted:

| candidate | status |
| --- | --- |
| OANDA financing rates (US entity) | 404 |
| OANDA financing rates (non-US entity) | 404 |
| OANDA v20 developer documentation | 200 — the account endpoints that carry realised financing need an account and a token |
| OANDA historical rates page | 404 |
| CME FX settlements | 403 |
| BIS effective exchange rates bulk file | 200 — carries no forward or swap-point series |

`BROKER_REALIZABLE_CARRY_NOT_SUPPORTED_FINANCING_HISTORY_NOT_PUBLIC`. The
reopening threshold was fixed before the probe — financing would have to improve
the non-JPY bloc by more than 20 pips per pair per panel, about five times what
that bloc actually earned — and it cannot be tested, so **carry stays closed**.
The route to broker data is reported, not taken.

## 7. The COT branch

### 7.1 Timing is the whole risk, and it was tightened

A report as of Tuesday is nominally published the following Friday at 15:30
America/New_York. Three of 369 as-of dates are Mondays — holiday weeks — and the
existing rule handles those. The case it does not handle is the mirror one: a
federal holiday later in the week delays the *release* by one business day while
the as-of date stays Tuesday, and then a Friday entry is a look-ahead of up to
three days.

The report carries no release timestamp, so the delay cannot be detected per
week. **Amendment A-3** therefore made the rule unconditionally conservative:
entry is the first bar after **Monday 20:30 UTC**, three calendar days past the
nominal Friday. That is at or after every possible publication.

The correction was ordered before the corrected numbers existed: the Monday rule
governs every verdict and the Friday numbers are a timing-sensitivity diagnostic.
It also turned out to be **cheaper**: a Friday 20:45 UTC entry is the illiquid
end of the week, and the mean round trip on the one-week cells falls from about
8.6 pips to about 4.9.

### 7.2 Eight cells, gross and net pips per pair-event

| cell | 2021–23 gross / net | 2023–25 gross / net | 2025 gross / net |
| --- | ---: | ---: | ---: |
| `net_level_1w` | −1.683 / −6.573 | −2.949 / −6.474 | −2.218 / −6.898 |
| `net_change_1w` | −4.901 / −9.790 | +1.804 / −1.721 | −6.622 / −11.302 |
| `net_percentile_1w` | +3.069 / −1.817 | +1.551 / −1.975 | +1.669 / −3.013 |
| `net_extreme_1w` | +3.316 / −1.556 | +0.826 / −2.694 | +8.700 / +4.452 |
| `net_level_4w` | −8.034 / −12.976 | −8.562 / −11.963 | −11.795 / −16.657 |
| `net_change_4w` | −11.414 / −16.357 | −2.743 / −6.144 | −2.798 / −7.660 |
| `net_percentile_4w` | +9.171 / +4.233 | +6.950 / +3.549 | −0.950 / −5.814 |
| **`net_extreme_4w`** | **+24.388 / +19.475** | **+24.032 / +20.667** | +14.625 / +10.141 |

`COT_EDGE_NOT_SUPPORTED`. Six cells fail on gross sign, breadth or cost. Two —
`net_percentile_4w` and `net_extreme_4w` — fail on **nothing except the
family-wise null**.

### 7.3 The one cell that survived everything else

`net_extreme_4w` is the contrarian rule at its sharpest: hold against a currency
whose leveraged-money net position sits above the 90th percentile of its own
trailing 104 weeks, for four calendar weeks.

| | 2021–23 | 2023–25 | 2025 |
| --- | ---: | ---: | ---: |
| weeks with any extreme | 77 | 94 | 23 |
| pair-events | 926 | 1,217 | 260 |
| gross pips per pair-event | +24.388 | +24.032 | +14.625 |
| cost | 4.913 | 3.365 | 4.483 |
| **net** | **+19.475** | **+20.667** | **+10.141** |
| net at **double** cost | +14.563 | +17.302 | +5.658 |
| pairs with positive gross | 12 / 20 | 14 / 20 | 8 / 19 |
| hit rate | 0.546 | 0.545 | 0.454 |
| top-10 share of positive gross | **0.086** | **0.107** | 0.290 |
| naive `t` | 2.620 | 2.936 | 1.207 |
| **permutation `p`** | **0.199** | **0.149** | 0.567 |
| **family-max corrected `p`** | **0.701** | **0.498** | 0.995 |
| **80%-power detection threshold, pips** | **26.06** | **22.92** | 33.93 |

Read that table in order.

* It passes **nine** of the plan's ten candidate criteria: an economic rationale
  fixed in advance, an exogenous source, clear provenance and timestamps, a gross
  effect, positive after cost at ×1 and ×2, the same sign on both deciding
  panels, seven currencies rather than one, a tail share far under the ceiling,
  and no tuned parameter.
* It fails the tenth. **The naive `t` of 2.6 and 2.9 is an artefact of counting
  1,217 pair-events from 94 weeks as independent observations.** They are not:
  the pairs share currency legs and the four-week holds overlap. The permutation
  null, which preserves exactly that structure, returns `p = 0.199` and `0.149`,
  and the family-max correction over the eight declared cells returns `0.701` and
  `0.498`.
* And the design was never able to answer the question. **The smallest effect it
  could detect at 80% power is 26.1 and 22.9 pips; the observed effect is 24.4
  and 24.0.** A uniformly positive point estimate whose interval spans zero is an
  underpowered null, not a refutation — the correction this programme adopted
  after the momentum round.

`net_percentile_4w` points the same way with a quarter of the size, which is not
independent evidence: `net_extreme` is a thresholded `net_percentile`, so the two
are one signal read at two sharpnesses.

**Nothing was done to rescue this cell.** No threshold was moved, no trader
category swapped, no horizon added, no pair subset taken. Those are the searches
this programme exists to avoid, and the plan named all four in advance.

## 8. Stages E and F — not run, and why

**Stage E (direction × opportunity integration) was not run.** The plan gates the
M0–M3 comparison on a directional source that survives the kill rules. None did.
An M0–M3 table built on a signal inside its own noise band would be a table with
no question behind it.

**Stage F (bounded ML) was not run.** Its five prerequisites are evaluated
against the artifacts rather than asserted: a gross edge that survives the kill
rules — **false**; a candidate after realistic cost — **false**; enough events —
**false** (the largest cell has 94 weeks against a floor of 100); a simple
economic rule with the same sign on both deciding panels — **false**, since the
rule that has it did not survive; measured heterogeneity a selector could
exploit — **not established**. `ML_NOT_RUN_PREREQUISITES_NOT_MET`.

Tick volume was therefore never given a direction role, which the plan forbids
outright, and no sizing rule was used to turn a negative expectancy positive.

## 9. Verification

* `tests/research` — **309 passed**, 36 of them this package's.
* **26 targeted mutations, all 26 killed.** Among them: a fixed UTC offset in
  place of the daylight rule; entry on the bar containing the release; the
  two-hour gap guard removed; the prior-known value read from the release vintage
  instead of the one before it; a full-sample surprise scale; the USD side of a
  pair flipped; the pre-registered macro sign inverted; the COT safety days
  removed; the COT as-of Tuesday used directly; an expanding percentile window;
  the USD score's sign; a contrarian signal made momentum; the volatility tercile
  dropped from the matched cells; the matched ratio collapsed to a pooled one;
  the null re-drawing uniformly; the minimum-bars filter removed; the trailing
  window reading its own day; the verdict's completeness check removed; the
  family-wise correction ignored; the family maximum replaced by a minimum; the
  FOMC `Statement:` requirement removed; the nowcast marker labels kept; a
  constant cost; the COT horizon back in bars; the RBA parser admitting the
  Payments System Board; and the breadth share zeroed.
* **That battery found five defects in my own tests**, all fixed and all the same
  species: a fixture built from the constant it was testing. The minimum-bars
  fixture trimmed itself to zero when the threshold was zeroed; the breadth
  fixture moved with `BREADTH_SHARE`; the first-release fixture left the prior
  month unrevised so the two candidate vintages agreed; the percentile fixture
  had no early spike, so a rolling and an expanding window gave the same answer;
  and the tercile test asserted on a bucket whose boundaries are cut on the whole
  panel.
* `ruff format --check`, `ruff check`, `tools/lint/run_custom_checks.py` — clean.
* Every number in this document is machine-checked against the artifacts.

## 10. Disclosed, not dressed up

* **Four of eight central banks are missing** and the reason is access, not
  design. GBP, CAD, NZD and CHF have no scheduled anchor.
* **The macro expectation is a model nowcast**, and whether its published archive
  was recomputed cannot be settled from the file.
* **The COT four-week holds overlap** and are counted as independent events, each
  paying its own round trip. That overstates both the cost and the sample size;
  the permutation null is what keeps the inference honest, and it is the reason
  the naive `t` and the reported `p` disagree so sharply.
* **The volatility tercile is cut on the whole panel's distribution.** It is a
  stratification — it decides which days are compared with which, the null
  permutes inside the same strata, and no position is taken from it. The
  quantity being stratified on is strictly backward-looking.
* **Stage A is a day-level study.** No decision time of day was acquired for the
  four banks, so no intraday claim is made from it.
* **2025 agrees with Stage A and contradicts nothing that matters**, and it
  decides nothing either way.

## 11. Referred, not guessed

1. **`net_extreme_4w`, and only that cell.** It passes nine of ten candidate
   criteria and fails the multiplicity one, with the design's own power at
   roughly the size of the observed effect. A bounded, pre-registered replication
   of **exactly this frozen rule** on unseen data is the only thing that can
   settle it. That is a fresh-data read and needs an explicit human + ChatGPT
   act; **this session did not take it and does not recommend taking it
   casually** — one of the three remaining archive windows would be spent.
2. **Survey consensus history** for CPI and employment. Paid everywhere found. It
   would turn the macro family from a model-nowcast diagnostic into a real test.
3. **A full central-bank meeting calendar** for the four missing banks, which
   would take Stage A from four currencies to eight.
4. **Decision-time-of-day** for the four acquired banks, which would make Stage A
   an intraday study instead of a daily one.
5. **Broker financing history**, still the thing that decides whether any carry
   result was ever implementable.
6. **Implied volatility** — referral only, and it ranks last: it prices the layer
   that already works.

## 12. Statuses

`FORWARD_KNOWN_EVENT_OPPORTUNITY_STRUCTURE_SUPPORTED` ·
`EVENT_DAY_COST_ADVANTAGE_NOT_ESTABLISHED` ·
`REAL_TIME_MACRO_SURVEY_CONSENSUS_NOT_AVAILABLE_WITHOUT_A_PAID_CONTRACT` ·
`MACRO_SURPRISE_DIRECTIONAL_EDGE_NOT_SUPPORTED` ·
`BROKER_REALIZABLE_CARRY_NOT_SUPPORTED_FINANCING_HISTORY_NOT_PUBLIC` ·
`COT_EDGE_NOT_SUPPORTED` · `ML_NOT_RUN_PREREQUISITES_NOT_MET` ·
**`EXOGENOUS_EXPECTED_RETURN_SOURCE_NOT_FOUND`**.

Always binding: `NON_DECISION_BEARING_EXPLORATORY_ONLY` ·
`RESEARCH_SCRATCH_NON_AUTHORITATIVE` · `PRODUCTION_READINESS_NOT_CLAIMED` ·
fresh pool `2016-06-02 … 2021-04-25` untouched · historical OOS slice untouched ·
dead window untouched · future untouched epoch untouched · Formal Confirmation
not performed · no broker, demo or live contact · no real order · no production
deployment.
