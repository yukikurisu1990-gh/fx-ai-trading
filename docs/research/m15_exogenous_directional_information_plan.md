# M15 — Exogenous Directional Information: research plan (pre-registration)

**`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `PRODUCTION_READINESS_NOT_CLAIMED`.**

Base master `b7073d5aa460438bfe5220e39e841ef9a75d9cc5` (the PR #471 merge).

**This document is frozen before the first research statistic of this package is
computed.** Source *reachability* probes were run before it — whether a URL
answers, what columns a file has, how many meeting dates a page lists. No FX
return, no panel statistic and no relationship between an external series and a
price was looked at. Where a number below describes an external source it comes
from those probes and is recorded so the plan can be checked against what was
actually acquired.

Nothing in §§1–24 may be changed because of a result. An amendment must be a
separate commit, must state what forced it, and must come before the statistic
it affects — the same rule the Economic Edge package used at its amendment A-1.

---

## 1. The question

Ten families have now failed to produce a reproducible expected-return source:
unconditional and conditional direction, trend/breakout, reversal/momentum,
multi-day direction, monthly TSMOM, path and retrace geometry, a linear
selector, carry, and tick-volume timing. What the last package *did* establish
is that an **exogenous anchor selects days that move more** — at a spread that is
slightly wider, not narrower.

So the question here is not "is there another price feature".

> **Can information that exists outside the price series, is knowable before the
> fact, and has an economic reason to move an exchange rate, produce a
> directional expected return that survives transaction cost?**

Two things are evaluated **separately** throughout and may never be merged into
one claim:

* **Expected-return source (Layer A)** — why hold this side at all.
* **Opportunity / timing source (Layer B)** — when is holding it worth the cost.

Being able to predict movement is not an edge. Being able to predict volatility
is not an edge. Execution (Layer C) may never be the origin of an edge.

## 2. The forward-known requirement

The Economic Edge package anchored on days a policy rate **changed**. Whether a
meeting changes a rate is not knowable in advance, so that population bounded
what an anchor could offer without being one.

**Every event population in this package must be knowable before it happens.**
Concretely: a scheduled meeting date published in advance; a statistical release
date published in advance; a report whose publication time is fixed by rule. An
event attribute that is only known afterwards — did the rate change, was the
print high — may be used as a **post-hoc diagnostic split** and may never enter
an entry condition. Any rule that would need to know the outcome to take the
trade is a bug in this package, not a finding.

## 3. Panels, pairs, cost, and what decides

Unchanged from the previous four packages, and restated so this document is
self-contained.

| | |
| --- | --- |
| `momentum_2021_2023` | `2021-04-26 … 2023-04-25`, 624 trading days — **decides** |
| `supplemental_2023_2025` | `2023-04-26 … 2025-04-24`, 624 trading days — **decides** |
| `development_2025` | `2025-04-25 … 2025-12-28`, 212 trading days — **may contradict, never decides** |
| pairs | `PAIRS_20` |
| bars | M15, the existing three reader routes; **no new FX span is read** |

`development_2025` has had roughly 1,200 configurations searched over it across
this programme. It is reported for every result and it decides nothing. A result
that holds on 2025 and on neither deciding panel is a negative result.

**Cost — `EXPLORATORY_ASSUMPTION`, unchanged.** Per side
`(spread_close_pips + 0.5) / 2` applied to mid returns, so a round trip is one
spread plus 0.5 pips. Every headline is also reported at **×2**. Where an event
window is involved the cost is taken from the **entry bar's own spread**, not
from a period average, so an event-time spread widening is paid rather than
averaged away.

## 4. Data sources — what may be acquired

Free, public, keyless only. **If a source needs a paid contract, a metered API,
an account, a login or a secret, this package stops and refers it.** No exception
is made for a source that would improve a result.

Required for every acquired source, recorded in an artifact: provider, source
identity and URL, field definition, frequency, timezone, publication timestamp
semantics, revision semantics, historical coverage, currency/country mapping,
missingness, `sha256` digest of the bytes actually fetched, and acquisition date.

### 4.1 Ranked, as fixed before acquisition

1. **Central-bank scheduled meeting calendar** — the forward-known anchor §2 asks
   for, and the only candidate that reaches many currencies.
2. **Macroeconomic release calendar** — release dates are published a year ahead,
   so they are forward-known even though the print is not.
3. **Real-time vintage actual and a pre-release expectation** — the only route to
   a *directional* macro quantity. §7 governs it.
4. **Public financing / swap proxies** — for §9 only, not to revive carry.
5. **COT positioning** — considered only under the branch conditions in §17.

### 4.2 What the reachability probes found

Recorded here so acquisition can be checked against it.

| source | route | verdict |
| --- | --- | --- |
| Federal Reserve — FOMC calendar | `federalreserve.gov/monetarypolicy/fomccalendars.htm`, statement links `monetaryYYYYMMDDa.htm` | **acquirable**, 46 dates 2021–2026 |
| ECB — monetary policy statements | `ecb.europa.eu/press/press_conference/monetary-policy-statement/{year}/html/index_include.en.html` | **acquirable**, 8 per year |
| Bank of Japan — MPM | `boj.or.jp/en/mopo/mpmsche_minu/past.htm`, statement files `k{yymmdd}.pdf` | **acquirable**, 8 per year 2021–2025 |
| Reserve Bank of Australia | `rba.gov.au/media-releases/{year}/`, releases titled *Monetary Policy Decision* | **acquirable with retries**, 11/yr to 2023 and 8/yr from 2024 |
| Bank of England | every index, RSS and sitemap route returns 404/500 or only future dates | **not acquirable** |
| Bank of Canada | press-release index renders client-side; the key-rate page lists only recent decisions | **not acquirable** |
| Reserve Bank of New Zealand | HTTP 403 to every automated client tried, including a full browser header set | **not acquirable** |
| Swiss National Bank | every assessment and press-release path tried returns 404 | **not acquirable** |
| CFTC Commitments of Traders | `publicreporting.cftc.gov/resource/gpe5-46if.json`, keyless Socrata | **acquirable** |
| ALFRED real-time vintages | `alfred.stlouisfed.org/graph/alfredgraph.csv?id=…&vintage_date=…`, vintage list at `/series/downloaddata?seid=…` | **acquirable** |
| Cleveland Fed inflation nowcast | `clevelandfed.org/-/media/files/webcharts/inflationnowcasting/nowcast_month.json`, daily nowcast path per target month | **acquirable** |
| Atlanta Fed GDPNow real-time archive | `GDPTrackingModelDataAndForecasts.xlsx` | acquirable, **not used** — see §7.4 |
| Survey consensus history (any indicator) | Bloomberg, Refinitiv, Econoday, Trading Economics | **paid or licence-restricted — referral, not acquired** |
| OANDA historical financing | no public archive found | see §9 |

**The four unacquirable central banks are recorded as a coverage limitation and
their meeting dates are not reconstructed by hand.** Writing dates into a
committed file from memory would put unverified scope into an artifact, which
this repository has ruled against before. GBP, CAD, NZD and CHF therefore have no
scheduled-meeting anchor in this package.

19 of `PAIRS_20` contain at least one of USD, EUR, JPY, AUD. Only `GBP_CHF` has
none and it is excluded from the scheduled-event study by construction, not by
result.

## 5. Publication-time semantics — frozen

The single largest leakage risk in this package is treating a value as available
earlier than it was.

* **Central-bank decisions.** The acquired date is the **announcement date**. Its
  time of day is *not* acquired for every bank, so **the scheduled-event study in
  §6 is a day-level study** — an event day is a UTC calendar date. No intraday
  claim is made from a source whose timestamp is a date.
* **US CPI.** Released by the BLS at **08:30 America/New_York**, a time fixed by
  rule and published a year ahead. Converted to UTC **with the correct daylight
  rule for each date** — 12:30 UTC under EDT, 13:30 UTC under EST. A fixed offset
  is a bug.
* **Entry bar.** The first M15 bar whose **open is strictly after** the release
  timestamp. A bar that contains the release is never entered on.
* **COT.** As-of **Tuesday**, published **Friday 15:30 America/New_York**. The
  earliest permitted decision bar is the first M15 bar opening strictly after
  **Friday 20:30 UTC** — the later of the two daylight conversions, taken
  unconditionally so the conversion can never be optimistic.
* **Policy rates** (carried over): used with a one-trading-day lag from the
  effective date.

Every one of these is pinned by a test, and each is a targeted mutation in §21.

## 6. Stage A — scheduled-event structure (Layer B)

**Population.** For pair `XXX_YYY`, an event day is a UTC date on which the
central bank of `XXX` or of `YYY` held a **scheduled** decision, among the four
acquired banks. Unscheduled/emergency decisions are flagged and **excluded from
the event population** — they are not forward-known — and reported separately.

**Control.** The previous package's Sunday artefact is not repeated. A control
day must match the event day on:

1. **day of week**, and
2. **trading-day status** — at least `MIN_BARS_FOR_A_TRADING_DAY = 48` M15 bars,
   the same constant the Economic Edge package used, and
3. **volatility context** — the tercile of the trailing 60-day realised
   volatility of that pair, computed from data strictly before the day.

Every ratio the verdict reads is computed **within** a (weekday × volatility
tercile) cell and pooled across cells. A pooled ratio that ignores the cells is a
diagnostic only.

**Measured**, per pair and per panel: absolute daily move, realised volatility,
mean spread, tick volume, high–low range, and the share of days whose absolute
move exceeds the round-trip cost.

**Null.** Event days are re-drawn **inside the same weekday and the same
volatility tercile**, 200 draws, preserving the calendar structure. The
permutation `p` is two-sided on the pooled matched ratio.

**Verdict.**

* `FORWARD_KNOWN_EVENT_OPPORTUNITY_STRUCTURE_SUPPORTED` — the matched absolute-move
  ratio exceeds 1 on **both** deciding panels, with at least 60% of eligible pairs
  agreeing on each, and permutation `p < 0.05` on both.
* otherwise `SCHEDULED_EVENT_OPPORTUNITY_STRUCTURE_NOT_SUPPORTED`.

**A supported verdict is an opportunity result and is not an edge**, and the
report must say so in the same sentence. The cost-clearing share is reported
beside it precisely because the last package found magnitude was not the binding
constraint.

**Post-hoc diagnostic only:** changed versus unchanged decisions. It may not
enter an entry condition (§2).

## 7. Stage B — macro real-time data

### 7.1 The rule

A revised historical series may **never** be used as the actual that was known at
release time. For each release the following are distinguished and stored
separately: **first-release actual**, **pre-release expectation**, **prior value
known at release time**, **latest revised value**.

`first-release actual` is the value for observation month *m* in the **earliest
ALFRED vintage in which m appears**. `prior value known at release time` is the
value for *m−1* in the **vintage immediately preceding** that one.

### 7.2 The expectation, and what it is not

No free source provides a **survey consensus history** for any release in this
programme's currencies. Every candidate is paid or licence-restricted.
Accordingly:

> **`REAL_TIME_MACRO_SURVEY_CONSENSUS_NOT_AVAILABLE_WITHOUT_A_PAID_CONTRACT`** —
> recorded, referred, and **not worked around by synthesising a consensus**.

One quantity does exist that is public, keyless, published **before** the
release, and archived at daily frequency: the **Federal Reserve Bank of
Cleveland inflation nowcast**. It is used, and it is labelled honestly:

* it is a **model nowcast, not a market consensus**. A surprise computed against
  it is `MODEL_NOWCAST_SURPRISE_NOT_SURVEY_SURPRISE` and a null on it does **not**
  refute a consensus-surprise hypothesis;
* the archive shows, for each target month, the nowcast on each business day, and
  the CPI series **stops on the release date**. That truncation is the evidence
  the path is a real-time record rather than a re-run; it is evidence, not proof,
  and the residual risk that the published archive was recomputed with revised
  inputs is disclosed and cannot be eliminated from the file alone.

The expectation used for a release is the nowcast on the **last business day
strictly before the release date**.

### 7.3 Scope, and why it cannot pass

Indicators: **US CPI (headline, month-over-month)** and **US core CPI
(month-over-month)** — the two the nowcast archive covers with a matching ALFRED
first-release. Both print in the same release, so they are two signals on one
event set, not two event sets.

**This family is USD-only, with roughly 24 releases per deciding panel.** §16's
kill rule drops a single-currency family and drops a family with few events.
**It is therefore pre-registered as a bounded diagnostic whose best attainable
outcome is a negative one** — `MACRO_SURPRISE_DIRECTIONAL_EDGE_NOT_SUPPORTED`, or
at most `MACRO_SURPRISE_SIGNAL_PRESENT_BUT_SINGLE_CURRENCY_INSUFFICIENT_BREADTH`,
which is **not** a candidate under §18. It is run because it answers a question
the programme has asked, not because it can win.

### 7.4 What is not run, and why

* **Employment (payrolls, unemployment).** No public real-time expectation
  exists at any frequency. `NO_REAL_TIME_EXPECTATION_AVAILABLE` — not run.
* **GDP.** The Atlanta Fed GDPNow real-time archive exists and would give a clean
  surprise, but GDP is quarterly: about 18 releases across all three panels, one
  currency. §16's event-count rule kills it before it starts. Recorded as
  acquirable and **not acquired**, so that a later session does not mistake the
  omission for an oversight.
* **Policy-decision surprise** (decision against what was priced) needs OIS or
  fed-funds-futures history. No free source. Referred.
* **Non-US inflation.** No comparable public nowcast archive. Not run.

## 8. Stage C — macro surprise direction (Layer A)

Run only for the family §7.3 admits.

**Surprise.** `z = (first_release_actual − nowcast) / s`, where `s` is the
standard deviation of `(actual − nowcast)` over the **preceding 24 releases
only** — an expanding, strictly backward-looking scale. A full-sample scale is a
leak and is a mutation in §21.

**Direction convention, fixed here, before any return is computed.**

> A **higher-than-expected** US CPI print is hawkish for the Fed and
> **appreciates the USD**.

So the position is long USD against the counter currency when `z > 0` and short
USD when `z < 0`, in every pair containing USD, for every horizon. **The sign is
not chosen from the data.** If the measured effect is opposite, the family is
recorded as contradicting its pre-registered economics and is **dropped, not
inverted** — the rule this programme adopted after the reversal/momentum round.

**Horizons.** Three, and no more: **1 hour, 4 hours, 1 day** from the entry bar.
Two signals × three horizons = **6 cells**, the whole search.

**Sizing.** Fixed unit per event. No volatility scaling in Stage C; scaling is a
Stage D question and may not be used to rescue a negative expectancy (§13).

**Execution realism.** Entry at the open of the first bar starting strictly after
the release (§5), cost from that bar's own spread, `×1` and `×2` reported. Bars
missing at the release time — a holiday, a gap — drop the event; they do not
shift it to a later bar.

## 9. Stage D — broker financing feasibility

The purpose is **not** to revive carry. The question is one number: how far is
the policy-rate proxy the last package used from what a broker would actually
pay?

Investigated and recorded: whether OANDA publishes historical financing rates
without a login; whether any public swap-point or forward-point history covers
the eight currencies; pair-level financing; long/short asymmetry; the
triple-swap/weekend convention; and the markup, where any of it is public.

**If it needs a login, an account or a secret, this stage stops and reports the
route only.**

**Reopening rule, fixed now.** Carry is re-examined **only** if broker-realizable
financing is *materially more favourable* than the research proxy — defined here
as improving the non-JPY bloc's net by more than **+20 pips per pair per panel**,
which is roughly five times the `+4.2 / +4.0` that bloc actually earned. Equal or
worse gives `CARRY_FAMILY_CLOSED_AFTER_BROKER_FINANCING_CHECK`. If financing
history cannot be obtained at all, the verdict is
`BROKER_REALIZABLE_CARRY_NOT_SUPPORTED_FINANCING_HISTORY_NOT_PUBLIC` and carry
stays closed.

## 10. Stage E — direction × opportunity integration

Run **only** if Stage C or §17's COT branch produces a directional signal that is
positive after cost on both deciding panels. Otherwise it is not run, and the
report says so rather than reporting an integration of nothing.

Tick volume may be used **only** as opportunity, volatility, execution timing or
position-size context. **It may never be a direction input.** Four models:

* **M0** no signal;
* **M1** directional signal only;
* **M2** M1 plus a simple volatility control;
* **M3** M1 plus tick-volume opportunity context.

Compared on net, expectancy per event, drawdown, turnover, tail share, event
capture and incremental value over M1.

**A negative expected value may not be turned positive by sizing.** If M3 beats
M1 only through leverage on a base that does not clear cost, that is reported as
`SIZING_DOES_NOT_CREATE_EXPECTED_RETURN` and not as an improvement.

## 11. Stage F — bounded ML

Not run unless **all five** hold, evaluated against the artifacts and not against
a narrative:

1. an exogenous directional source with a **gross** edge;
2. still a candidate after realistic cost;
3. enough events — at least **100 per deciding panel** in the family;
4. a simple economic rule with the **same sign** on both deciding panels;
5. measured heterogeneity a selector could exploit.

If ML runs it is a **take/skip and expected-net ranking model over events**,
never a per-bar direction model. Logistic regression or ridge, and LightGBM, each
against the simple rule. At most **20 features**, drawn from: surprise magnitude
and sign, previous surprise, rate differential, tick volume, realised volatility,
spread, a bounded higher-timeframe volatility context, and bounded calendar
context. An indicator zoo is forbidden. Success is incremental net, expectancy,
drawdown, turnover efficiency and panel stability — **not AUC**. Failure is
`ML_NO_INCREMENTAL_VALUE_ON_EXOGENOUS_SIGNAL`.

## 12. Multiplicity

Three families, declared now, each corrected within itself by Westfall–Young
family-max over 200 matched null draws:

| family | cells |
| --- | ---: |
| scheduled-event structure (§6) | 1 population × 6 measured quantities = **6** |
| macro surprise direction (§8) | 2 signals × 3 horizons = **6** |
| COT direction (§17), if reached | 4 signals × 2 horizons = **8** |

**20 cells is the entire search of this package.** A cell not listed here may not
be added after a result. `development_2025` is reported for every cell and enters
no correction, because it decides nothing.

## 13. Kill rules

A directional family is **dropped** — not tuned, not inverted, not re-cut — if
any of these holds:

* no gross directional effect before cost;
* the sign reverses between the two deciding panels;
* negative after cost at `×1`;
* the effect is confined to one currency;
* fewer than 30 events per deciding panel;
* the top 10 events contribute more than **50%** of net (the same
  `TAIL_SHARE_CEILING` the previous package used);
* the measured sign contradicts the pre-registered economics;
* the family-max corrected result is indistinguishable from the matched null.

An opportunity family is dropped if the matched ratio fails §6's verdict.

**A uniformly negative point estimate with an interval spanning zero is an
underpowered null, not a refutation** — the correction this programme adopted
after the momentum round. Power against the pre-registered effect is reported
whenever a family is dropped for absence of effect.

## 14. Stage progression

* **A → B** always: the calendar is needed either way.
* **B → C** only if §7 yields a real-time expectation and first-release actual.
  Otherwise `REAL_TIME_MACRO_SURPRISE_DATA_NOT_RELIABLY_AVAILABLE`, referral, and
  jump to §17.
* **C → E** only if §13 does not drop the family.
* **E → F** only if all five of §11 hold.
* **D** runs regardless; it is a feasibility question, not a research one.

## 15. Branches

* **Route A** — macro direction survives, volume adds value → integration → ML if
  §11 holds → adjudication.
* **Route B** — macro direction survives, volume adds nothing → evaluate the
  simple macro candidate alone.
* **Route C** — macro real-time data unobtainable → COT feasibility and, if safe,
  bounded COT research.
* **Route D** — macro obtainable but no edge → bounded COT research.
* **Route E** — neither macro nor COT yields an expected-return source →
  programme-level reconsideration, and an implied-volatility **referral only**.

## 16. What counts as a candidate

`EXPLORATORY_EXOGENOUS_EDGE_CANDIDATE_READY_FOR_FRESH_REPLICATION_DECISION`
requires **all** of: an economic rationale fixed before the result; an exogenous
information source; clear timestamp and provenance; a gross edge; positive after
cost at `×1`; the same sign on both deciding panels; more than one currency; a
tail share under the ceiling; no worse than a simple baseline; and every
parameter frozen. **Nothing is read from the fresh pool even then** — the
candidate is handed to a human + ChatGPT decision.

## 17. COT branch

Entered under Route C or D. Feasibility first: futures-to-currency mapping,
weekly publication lag, historical coverage, as-of versus publication date,
revision behaviour, and the mapping from a futures contract to an FX spot pair.
If any is unclear the branch stops at feasibility.

**Signals, fixed now — four.** Computed per currency from the CFTC *Traders in
Financial Futures* report, on the **leveraged-money** category, as a share of
open interest:

| signal | definition | **pre-registered sign** |
| --- | --- | --- |
| `net_level` | net long share of open interest | **contrarian** |
| `net_change` | week-on-week change in that share | **momentum** |
| `net_percentile` | percentile of `net_level` in a trailing 104-week window | **contrarian** |
| `net_extreme` | ±1 when `net_percentile` is above 0.90 or below 0.10, else 0 | **contrarian** |

The three contrarian signs are the crowded-positioning hypothesis: speculative
positioning at an extreme is a position that has to be unwound. The momentum sign
on `net_change` is the order-flow-continuation hypothesis: a change in
positioning is flow that has not finished. **These are two different economic
claims and each is committed to one sign here, before any return is computed.** A
signal whose measured sign is opposite is dropped, not flipped.

**Pair mapping.** For `XXX_YYY` the score is `s(XXX) − s(YYY)`, using each
currency's own futures contract. USD has no leveraged-money futures series in
this report, so **USD is scored as the negative of the equally-weighted mean of
the other seven** — a pre-registered construction, not a fitted one.

**Horizons.** Two: **1 week** and **4 weeks**. Four signals × two horizons = 8
cells, the whole COT search. No cross-sectional variants, no `k` grid, no
threshold sweep.

## 18. Statuses this package may record

`FORWARD_KNOWN_EVENT_OPPORTUNITY_STRUCTURE_SUPPORTED` ·
`SCHEDULED_EVENT_OPPORTUNITY_STRUCTURE_NOT_SUPPORTED` ·
`REAL_TIME_MACRO_SURVEY_CONSENSUS_NOT_AVAILABLE_WITHOUT_A_PAID_CONTRACT` ·
`REAL_TIME_MACRO_SURPRISE_DATA_NOT_RELIABLY_AVAILABLE` ·
`MACRO_SURPRISE_DIRECTIONAL_EDGE_NOT_SUPPORTED` ·
`MACRO_SURPRISE_SIGNAL_PRESENT_BUT_SINGLE_CURRENCY_INSUFFICIENT_BREADTH` ·
`BROKER_REALIZABLE_CARRY_NOT_SUPPORTED_FINANCING_HISTORY_NOT_PUBLIC` ·
`CARRY_FAMILY_CLOSED_AFTER_BROKER_FINANCING_CHECK` ·
`COT_EDGE_NOT_SUPPORTED` · `COT_FEASIBILITY_ESTABLISHED` ·
`ML_NO_INCREMENTAL_VALUE_ON_EXOGENOUS_SIGNAL` ·
`SIZING_DOES_NOT_CREATE_EXPECTED_RETURN` ·
`EXPLORATORY_EXOGENOUS_EDGE_CANDIDATE_READY_FOR_FRESH_REPLICATION_DECISION` ·
`EXOGENOUS_EXPECTED_RETURN_SOURCE_NOT_FOUND`.

## 19. Hard boundaries

Not crossed autonomously; each needs a human + ChatGPT act.

Fresh FX pool `2016-06-02 … 2021-04-25`; the historical OOS slice; the dead
window; the future untouched epoch; Formal Confirmation; broker, demo or live
trading; a real order; production deployment; a paid data contract; a new metered
API; account creation; entering a secret.

## 20. Reporting

Every directional result reports: directional IC, signed return, gross, cost,
net, expectancy per event, event count, currency breadth, panel consistency, tail
contribution, event-class breakdown, and cost `×2`. Every carry-like result keeps
the three lines — spot, carry income, cost — that add up.

No result is reported without its matched null. No pooled ratio is reported as a
verdict input when a matched one exists.

## 21. Tests and targeted mutation

Each of these must be independently killed by a test:

release timestamp; timezone and the daylight rule; publication lag; first-release
versus revised value; the prior-value-known-at-release rule; event-to-currency
mapping; the pre-registered surprise sign; the backward-only surprise scale; the
policy-rate lag; the COT Tuesday-as-of versus Friday-publication gap; the
weekday × volatility-tercile matching; the null preserving calendar structure;
the tick-volume alignment; the broker-financing sign; and the consistency of
every number in the results document with the artifacts.

## 22. Review

Two roles at the end, given the source, diff and this plan and **not** each
other's conclusions:

* **Role 1** — FX economics and statistical interpretation.
* **Role 2** — temporal leakage, provenance, event timestamps, implementation.

A general adversarial audit is not run. Reproducible blockers are fixed in scope
and re-verified.

## 23. Amendments

Each amendment appends here with the commit that made it, what forced it, and
the statistic it precedes.

### A-1 — the COT horizon is measured in calendar time, not in bars

**Made before any COT return was computed.** §17 fixed two horizons, "1 week"
and "4 weeks", and the frozen constant expressed them as `7 * 96` and `28 * 96`
M15 bars. Those are not the same thing. The FX week has no weekend bars, so 672
bars is about seven **trading** days — roughly nine and a half calendar days —
and 2,688 bars is about five and a half calendar weeks, not four. A horizon
labelled "1 week" that holds for nine days is a misspecification, and it would
have been reported under the wrong name.

The horizons are therefore defined in **calendar time**: the position is closed
at the first bar at or after `entry + 7 days` and `entry + 28 days`. The names
in §17 are unchanged and now mean what they say. Nothing about the signals,
signs, pair mapping, cost or kill rules changes, and no COT statistic had been
computed when this was written.

### A-2 — COT currency coverage, recorded rather than assumed

**Made before any COT return was computed.** §17 assumed each of the seven
non-USD currencies has its own futures contract in the CFTC *Traders in
Financial Futures* report. Six of them — AUD, GBP, CAD, EUR, JPY, CHF — sit in
the `CURRENCY` subgroup; **NZD sits in `CURRENCY(NON-MAJOR)`** under the contract
name `NZ DOLLAR`, with history from 2006. All seven are therefore available and
§17's USD construction — the negative of the equally-weighted mean of the other
seven — stands unchanged. This is recorded because the coverage was checked, not
assumed, and a later session should not have to re-establish it.
