# M15 — Exogenous Directional Information: results

**`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `PRODUCTION_READINESS_NOT_CLAIMED`.**

Plan: `docs/research/m15_exogenous_directional_information_plan.md`, frozen at
`a2dfccc` **before the first research statistic of this package was computed**,
amended four times (§23, A-1 to A-4) — each amendment before the statistic it
affects, and A-4 after an independent review. Base master
`b7073d5aa460438bfe5220e39e841ef9a75d9cc5` (the PR #471 merge).

**Final status: `EXOGENOUS_EXPECTED_RETURN_SOURCE_NOT_FOUND`.**

---

## 1. The answer

* **A forward-known anchor works, and it is the same non-edge as before, larger.**
  Scheduled central-bank meeting days move **1.5827× / 1.6333×** as far as
  matched control days, on 19 of 19 and 18 of 19 pairs, at a family-max corrected
  `p = 0.005` — the permutation floor — on **all three** panels. The spread on
  those days is `1.0105× / 1.0165×` and **that difference is not distinguishable
  from its own null** (corrected `p = 1.000 / 0.955`). The share of days clearing
  the round trip is `1.0042 / 0.9958`, corrected `p = 1.000` on both. Movement
  rose by three fifths; cost-clearing did not move at all.
* **The real-time macro surprise is buildable and carries no usable direction.**
  84 CPI releases reconstructed from ALFRED vintages against the Cleveland Fed's
  archived daily nowcast, with two independent sources agreeing on the release
  date **84 times out of 84**. `MACRO_SURPRISE_DIRECTIONAL_EDGE_NOT_SUPPORTED` on
  five pre-registered clauses at once.
* **Broker-realizable financing is not public.** Six anonymous probes: **three**
  404s, one 403, and the only reachable OANDA route is developer documentation
  whose account endpoints need a token. Carry stays closed.
* **COT positioning is the first genuinely multi-currency direction test this
  programme has run, and it fails.** Eight pre-registered cells; all eight
  dropped. The one that came closest — `net_extreme` held four weeks — is
  positive on all three panels after cost, and **three separate pre-registered
  checks say that is a coincidence**: the ten largest events are 52% and 57% of
  net, above the ceiling; the same pairs do not carry it on the two deciding
  panels (Spearman **−0.308**, 10 of 20 signs agreeing — chance); and the effect
  comes from **opposite halves of the universe** on the two panels (USD-leg
  `−7.8` then `+49.6`; non-USD-leg `+60.4` then `−0.1`).

Nothing here is an expected-return source. Movement is not direction, and the one
direction candidate is a pooled coincidence of two unrelated realisations.

### 1a. What an independent review changed

Two roles reviewed the first version. **Every correction moved in the same
direction — the first version was not conservative enough about
`net_extreme_4w`, never too aggressive** — and four of them changed a headline:

| the first version said | the artifact says |
| --- | --- |
| tail share 0.086 / 0.107, "far under the ceiling" | that statistic is not §13's clause. §13 is top-ten over **net**: **0.523 / 0.573**, both **above** the 0.50 ceiling |
| "passes nine of the plan's ten candidate criteria" | it passes eight; §16's "no worse than a simple baseline" was never measured, and the clause called "the tenth" is a §13 kill rule, not a §16 criterion |
| 80%-power threshold 26.1 / 22.9 pips, "roughly its own size" | that was `2.8 ×` the same i.i.d. standard error the document itself calls invalid. On the null's own scale it is **71.0 / 65.7** pips — nearly three times the observed effect |
| permutation `p = 0.199 / 0.149` | the null freely permuted week labels, which scatters the runs of consecutive extreme weeks that four-week holds depend on — anti-conservative. Under a **circular shift**, `p = 0.413 / 0.164` |

A fifth correction — the per-pair cross-panel agreement — was not a change to a
number but the addition of one nobody had computed, and it is the most
decision-relevant statistic in the package (§7.4).

## 2. Identity

| | |
| --- | --- |
| PR #471 | merged, merge commit **`b7073d5aa460438bfe5220e39e841ef9a75d9cc5`** |
| verified before merge | head `d87afab` matched, CI green, `MERGEABLE`/`CLEAN`, no unresolved review thread |
| plan frozen | `a2dfccc`, before the first statistic; amendments A-1/A-2, A-3 and A-4 each before the statistic they affect |
| panels | `2021-04-26…2023-04-25` (624 trading days) · `2023-04-26…2025-04-24` (624) · `2025-04-25…2025-12-28` (212) |
| pairs | `PAIRS_20` |
| **new FX market-data spans read** | **none** |
| fresh pool `2016-06-02…2021-04-25` | **untouched** |
| historical OOS slice, dead window, forward epoch | **untouched** |
| declared search | **20 cells**: 6 event-structure, 6 macro, 8 COT — each family corrected within itself |

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

**Cadence matches the published schedule on every year for every bank.** That
check is necessary and not sufficient — one extra unscheduled decision plus one
missed scheduled meeting would net to the right count — so it is backed by a
second one that uses a source the calendar cannot have influenced: every
policy-rate change in the BIS series over 2021–2025 must be explained by a
scheduled meeting shortly before it.

| currency | rate changes | explained | effective-date lag, days | orphans |
| --- | ---: | ---: | ---: | ---: |
| USD | 17 | **17** | 2 | 0 |
| EUR | 18 | **18** | 7 | 0 |
| AUD | 16 | **16** | 2 | 0 |
| JPY | 4 | **4** | 2, 3, 4 | 0 |

Not one orphan. The lag is a **single value for the Fed, the ECB and the RBA** —
the BIS effective date sits a fixed distance after the decision — and takes three
values across the BoJ's four changes. An unscheduled decision, or a hallucinated
or missing meeting date, would appear here as an unexplained change.

**Plan §6 asked for unscheduled decisions to be flagged and excluded, and no
flag is implemented** — no acquired source carries one. The containment check
above is what stands in for it, and it found none.

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
| **revision** | the entire point of the source: a month's value changes across vintages, and four genuine inter-vintage revisions sit inside these 84 rows |
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
`MODEL_NOWCAST_SURPRISE_NOT_SURVEY_SURPRISE`.

The consequence is sharper than "a null here does not refute a consensus
hypothesis". A surprise measured this way is
`(actual − consensus) + (consensus − nowcast)`, and the second term is error of
comparable size to the first. It **attenuates the measured surprise toward zero
and can flip its sign on an individual release** — which makes a panel sign
reversal on this family nearly uninformative about the economics.

Two things support the archive being a real-time record rather than a re-run: the
CPI path **stops on the business day before the release**, and the actual is
placed **on** the release date. Neither is proof, and the residual risk is
disclosed rather than assumed away.

**One parsing defect mattered a great deal.** The chart axis interleaves marker
labels — `CPI May`, `PCE Jun` — between the business days, so there are more
categories than data points. Indexing the raw category list put every release two
or three business days early, and ALFRED's vintage date then agreed with the
archive on **0 of 84** releases. Aligning the datasets to the date labels only
makes it **84 of 84**. That agreement is now the check that the release calendar
is right, and it is pinned by a test — as is the failure mode where a future
archive ships one point per category, which now raises rather than truncating.

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
draws, and the six declared quantities are corrected against the **family
maximum** of the same draws.

Two failure modes are closed at once. The previous package's headline reversed
when Sundays were matched away. And central banks meet more often in the middle
of a tightening cycle, so an unmatched comparison would partly measure the cycle.

### 4.2 The result

| matched ratio | 2021–23 | 2023–25 | 2025 *(may not decide)* |
| --- | ---: | ---: | ---: |
| **absolute move** | **1.5827** | **1.6333** | 1.5597 |
| pairs agreeing | **19 / 19** | **18 / 19** | 17 / 19 |
| family-max corrected `p` | **0.0050** | **0.0050** | 0.0050 |
| high–low range | 1.4564 | 1.4244 | 1.3531 |
| realised volatility | 1.4658 | 1.3169 | 1.2470 |
| tick volume | 1.1675 | 1.1175 | 1.1345 |
| spread | 1.0105 (`p = 1.000`) | 1.0165 (`p = 0.955`) | 1.0051 (`p = 1.000`) |
| share clearing the round trip | 1.0042 (`p = 1.000`) | 0.9958 (`p = 1.000`) | 1.0438 (`p = 0.751`) |

Event days per pair: median 15 and 16 per deciding panel, range 15–35 and 15–32,
against a median of 476 and 472 control days (range 456–476 and 456–473).
`p = 0.0050` is the floor at 200 draws — no draw reached the observed ratio on
any panel, before or after the family correction.

The observed move ratio sits **11.3 and 10.9 null standard deviations** above the
null mean (`1.0055 ± 0.0509`, `1.0050 ± 0.0578`).

`FORWARD_KNOWN_EVENT_OPPORTUNITY_STRUCTURE_SUPPORTED`, with
`EVENT_DAY_COST_ADVANTAGE_NOT_ESTABLISHED` beside it — and note that the cost
side is now doubly not-established: the spread is nominally *wider* and that
difference is itself inside the null.

### 4.3 Why it is bigger than the last package's number, and why it still is not an edge

The previous package measured `1.33 / 1.13` around days a rate **changed**. This
is `1.58 / 1.63` around days a meeting was **scheduled** — a larger effect on a
larger and forward-known population. The reason is mechanical: the BIS effective
date sits 2 to 7 days after the decision (§3.1), so a ±1-day window around the
effective date frequently **missed the announcement day altogether**. The
forward-known calendar hits it directly.

And it is still not an edge. **Movement rises by about three fifths while the
share of days clearing the round trip does not move at all** — because ordinary
days already clear it, at a base rate of 0.960 and 0.954. Magnitude was never the
binding constraint. Direction is, and a bigger move in an unknown direction is a
bigger loss half the time.

### 4.4 One limitation of this null, stated rather than corrected

Each pair's event days are re-drawn with its own draw, so the pooled null does
not carry the dependence that comes from **all pairs sharing the same meeting
dates**. The pooled null is therefore tighter than the truth and `p = 0.0050` is
a lower bound. The margin absorbs it: even inflating the null standard deviation
by `√19` — the worst case, in which the 19 pairs are one observation — the
observed ratio is still 2.6 and 2.5 standard deviations out, and the point
estimate does not move at all.

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

`MACRO_SURPRISE_DIRECTIONAL_EDGE_NOT_SUPPORTED`, on five pre-registered clauses:

* **`SINGLE_CURRENCY_USD_ONLY`** — true by construction and stated in the plan
  before anything was measured;
* **`FEWER_THAN_30_EVENTS_PER_DECIDING_PANEL`** — 24 in each;
* **`PANEL_SIGN_REVERSAL`** on `cpi_1h`, `cpi_4h` and `core_cpi_1h`;
* **`NEGATIVE_AFTER_COST`** on all four sub-daily cells;
* **`TAIL_ABOVE_CEILING`** on all three daily cells.

**The sign is not inverted to fit** — the family is dropped, which is the rule
this programme adopted after a failed reversal rule was nearly re-run as a
momentum rule on the data that refuted it.

Two things the table deserves to have said about it.

* **The one-day horizon carries the pre-registered sign on both deciding
  panels** — `cpi_1d` `+14.10 / +13.93` gross and `+11.91 / +11.89` net, and
  `core_cpi_1d` likewise. Their corrected `p` is 0.806 and 0.652, nowhere near
  significance, and their tail shares are 1.06 and 0.93, over the ceiling. It
  changes no conclusion and it should be visible rather than left in the table.
* **The one cell that clears the family correction on a panel is the one that
  reverses on the other.** `cpi_4h` corrected `p = 0.040` on 2023–25 and −3.98
  gross on 2021–23.

The design could detect 12–40 pips at 80% power depending on the cell; the
observed effects are inside that range on one panel and the wrong sign on the
other.

In 2025 the CPI and core CPI cells are identical because the two surprises
happened to share a sign on all six releases in that window; only `sign(z)`
enters the direction, and the ICs differ (`−0.480` against `−0.474`), so the two
series are distinct.

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
The route to broker data is reported, not taken. The probe's positive branch now
requires a machine-readable payload as well as the word "historical", so a
marketing page cannot flip the verdict.

## 7. The COT branch

### 7.1 Timing, tightened twice

A report as of Tuesday is nominally published the following Friday at 15:30
America/New_York. Three of 369 as-of dates are Mondays — holiday weeks — and the
existing rule handles those. The case it did not handle is the mirror one: a
federal holiday later in the report week delays the *release* by one business day
while the as-of date stays Tuesday.

**Amendment A-3** made the rule unconditionally conservative: entry is the first
bar starting after **Monday 20:30 UTC**, three calendar days past the nominal
Friday.

**What that guarantees, stated exactly.** It is at or after every
**one-business-day** holiday delay — and under standard time the margin is
exactly fifteen minutes, because entry is the first bar *strictly after* 20:30
UTC. It does **not** cover a multi-day suspension, and the report carries no
release timestamp from which one could be detected. The acquired series runs
weekly through the autumn of 2025 with no gap; any publication suspension in that
period would sit in `development_2025`, which decides nothing, and **outside both
deciding panels**.

The conservative rule also turned out **cheaper**: a Friday 20:45 UTC entry is
the illiquid end of the week, and the mean round trip on the one-week cells falls
from about 8.6 to 4.9 pips on the first deciding panel and 6.4 to 3.5 on the
second.

**Amendment A-4** replaced the null. A free permutation of week labels scatters
the runs of consecutive extreme weeks that a four-week hold depends on, so in the
null the overlapping windows carry near-independent signs and partly cancel while
in the data they add coherently — anti-conservative. The null is now a **circular
shift** of the whole score table, which preserves the serial persistence and the
within-week cross-section exactly.

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

`COT_EDGE_NOT_SUPPORTED`. **All eight are dropped.** Six fail on gross sign,
breadth or cost. The two four-week positioning-level cells —
`net_percentile_4w` and `net_extreme_4w` — fail on the family-wise null **and**
on the tail-share ceiling.

### 7.3 The cell that came closest

`net_extreme_4w` is the contrarian rule at its sharpest: hold against a currency
whose leveraged-money net position sits above the 90th percentile of its own
trailing 104 weeks, for four calendar weeks.

| | 2021–23 | 2023–25 | 2025 |
| --- | ---: | ---: | ---: |
| weeks with any extreme | 77 | 94 | 23 |
| pair-events | 926 | 1,217 | 260 |
| gross pips per pair-event | +24.388 | +24.032 | +14.625 |
| cost | 4.913 | 3.365 | 4.483 |
| **net** | **+19.475** | **+20.667** | +10.141 |
| net at **double** cost | +14.563 | +17.302 | +5.658 |
| pairs with positive gross | 12 / 20 | 14 / 20 | 8 / 19 |
| hit rate | 0.546 | 0.545 | 0.454 |
| **top-10 events ÷ net (§13's clause)** | **0.5228** | **0.5733** | 2.2292 |
| naive `t` | 2.620 | 2.936 | 1.207 |
| **permutation `p`, circular shift** | **0.4129** | **0.1642** | 0.7968 |
| **family-max corrected `p`** | **0.7463** | **0.4925** | not computed¹ |
| **95% interval on gross, pips** | **[−25.3, +74.1]** | **[−21.9, +70.0]** | [−57.1, +86.3] |
| **80%-power threshold, pips** | **71.0** | **65.7** | 102.5 |
| unconditional-long baseline over the same events | +7.297 | +19.635 | +58.195 |

¹ On the 212-day panel some circular shifts leave a cell with no events, so the
cells no longer share a draw count. Westfall–Young needs draw *b* to be the same
draw in every cell, and the implementation **refuses** the correction rather than
truncating and silently pairing draw *b* of one cell with draw *b+1* of another.
That panel decides nothing.

Read that in order.

* **The tail clause fires.** §13 asks whether the ten largest events contribute
  more than half of net. They contribute **52% and 57%**. The first version of
  this document reported 0.086 and 0.107 — a different statistic, the top ten
  over the sum of the *positive* gross only, which at this sample size returns
  roughly what pure noise gives and therefore cannot fail.
* **The interval spans zero on both deciding panels**, and the design's own
  minimum detectable effect at 80% power is **nearly three times the observed
  effect**. The naive `t` of 2.6 and 2.9 counts 926 and 1,217 pair-events from 77
  and 94 weeks as independent; the pairs share currency legs and the four-week
  holds overlap.
* **On the second panel it barely beats doing nothing clever.** Unconditional
  long over exactly the same events returns `+19.6` against the rule's `+24.0`.
  On 2025 the baseline returns `+58.2` and the rule `+14.6` — far worse.

### 7.4 The disaggregation nobody had computed

The pooled means agree on the two deciding panels. **The pairs do not.**

| | Spearman | Pearson | pairs agreeing on sign |
| --- | ---: | ---: | ---: |
| `net_extreme_4w` | **−0.308** | −0.377 | **10 / 20** |
| `net_percentile_4w` | −0.132 | −0.312 | 8 / 20 |
| `net_extreme_1w` | −0.370 | −0.538 | 9 / 20 |
| `net_level_4w` | +0.463 | +0.387 | 17 / 20 |

Ten of twenty is exactly chance, and the rank correlation is **negative**: the
pairs that paid on the first deciding panel are, if anything, the ones that lost
on the second. The only cell whose pairs do agree across panels — `net_level_4w`
at 17 of 20 — agrees on **losing money** on both.

The split by leg says the same thing more starkly:

| mean gross pips | 2021–23 | 2023–25 | 2025 |
| --- | ---: | ---: | ---: |
| USD-leg pairs | **−7.784** (489 events) | **+49.645** (591) | −31.562 (136) |
| non-USD pairs | **+60.389** (437) | **−0.149** (626) | +65.281 (124) |

**The two deciding panels' pooled agreement is built from opposite halves of the
universe.** That is not one effect reproducing; it is two unrelated realisations
whose averages happen to land at the same place.

This also corrects the rule's description. For the seven USD pairs the position
does not come from an extreme in either leg: the USD score is a continuous mean
of the other seven and is essentially never zero, so a USD pair trades in almost
every week in which *anything* is extreme. Those 489 and 591 events are more than
half the sample and are one common "dollar against the crowd" factor, not seven
independent currencies — which is also part of why the naive `t` overstates.

### 7.5 What the candidate checklist actually says

Plan §16 lists ten criteria. Against the artifacts:

| criterion | verdict |
| --- | --- |
| economic rationale fixed in advance | pass |
| exogenous information source | pass |
| clear timestamp and provenance | pass |
| a gross edge | pass on the pooled mean, **contradicted by §7.4** |
| positive after cost at ×1 | pass |
| same sign on both deciding panels | pass on the pooled mean, **contradicted by §7.4** |
| more than one currency | pass nominally; **more than half the events are one dollar factor** |
| tail share under the ceiling | **fail** — 0.523 and 0.573 |
| no worse than a simple baseline | **marginal**: +24.0 against +19.6 on the second panel, and far worse than baseline on 2025 |
| every parameter frozen | pass |

It fails one outright, is marginal on a second, and has two more contradicted by
the disaggregation — separately from the §13 kill rules, which drop it on the
family-wise null and on the tail. The first version of this document said "passes
nine of the plan's ten candidate criteria"; that count dropped the baseline
criterion, which was never measured, and substituted a §13 kill rule in its
place.

**Nothing was done to rescue this cell.** No threshold was moved, no trader
category swapped, no horizon added, no pair subset taken. Those are the searches
this programme exists to avoid, and the plan named all four in advance.

## 8. Stages E and F — not run, and why

**Stage E (direction × opportunity integration) was not run.** The plan gates the
M0–M3 comparison on a directional source that survives the kill rules. None did.

**Stage F (bounded ML) was not run.** Its five prerequisites are evaluated
against the artifacts rather than asserted: a gross edge that survives the kill
rules — **false**; a candidate after realistic cost — **false**; enough events —
**false** (the largest cell has 94 weeks against a floor of 100); a simple
economic rule with the same sign on both deciding panels — **false**; measured
heterogeneity a selector could exploit — **not established**.
`ML_NOT_RUN_PREREQUISITES_NOT_MET`.

Tick volume was therefore never given a direction role, which the plan forbids
outright, and no sizing rule was used to turn a negative expectancy positive.

## 9. Verification

* `tests/research` — **324 passed**, 51 of them this package's.
* **37 targeted mutations, all 37 killed**, in two batteries. The first 26 cover
  the daylight rule, entry on the release bar, the vintage supplying the
  prior-known value, a full-sample surprise scale, the USD side of a pair, the
  pre-registered macro sign, the COT safety days, the as-of Tuesday used
  directly, an expanding percentile, the USD score's sign, a contrarian signal
  made momentum, the tercile dropped from the matched cells, the ratio collapsed
  to pooled, a uniform null, the minimum-bars filter, the trailing window reading
  its own day, the completeness check, the family-wise correction, the family
  maximum made a minimum, the FOMC `Statement:` requirement, the nowcast marker
  labels, a constant cost, the horizon back in bars, the RBA parser, and the
  breadth share. The second 11 cover what the review found unguarded: the COT
  positioning table shifted a week into the future, the same for its
  week-on-week change, the tercile cut on the day's own volatility, the COT
  breadth literal, the nowcast expectation taken on or after the release, a
  widened safety margin, the positives-only tail denominator, an unequal-draw
  family maximum, the event family maximum made a minimum, the looser
  net-after-cost clause, and the old label-wrap rule.
* **The first battery found five defects in my own tests** and **the review
  found six more**, all one species: a fixture built from the constant it was
  testing, or an assertion one step removed from the property. The worst was that
  **shifting the entire COT positioning table one week into the future passed all
  36 tests** — the largest leak this branch could have carried.
* `ruff format --check`, `ruff check`, `tools/lint/run_custom_checks.py` — clean.
* **The results document is checked against the artifacts by a committed test**
  (`test_the_results_document_agrees_with_the_artifacts`), which plan §21 asked
  for and the first version did not have. It skips when the scratch artifacts are
  absent, as they are in CI.

## 10. Disclosed, not dressed up

* Four of eight central banks are missing, and the reason is access.
* Plan §6's unscheduled-decision flag is not implemented; the BIS containment
  check stands in for it.
* The macro expectation is a model nowcast, it attenuates the true surprise, and
  whether its published archive was recomputed cannot be settled from the file.
* The COT four-week holds overlap and are counted as independent events, each
  paying its own round trip. That overstates both the cost and the sample size.
* The COT safety margin covers a one-business-day delay and not a multi-day
  suspension, with a fifteen-minute margin under standard time.
* Stage A's null draws each pair's event days independently, so its `p` is a
  lower bound (§4.4).
* The volatility tercile is cut on the whole panel's distribution. It is a
  stratification — the null permutes inside the same strata and no position is
  taken from it — and the quantity stratified on is strictly backward-looking.
* Stage A is a day-level study. No decision time of day was acquired.
* At the archive boundary the real-time table would skip one release for want of
  a predecessor vintage; the artifact records that it did not happen here.
* 2025 agrees with Stage A, contradicts the COT cell that came closest, and
  decides nothing either way.

## 11. Referred, not guessed

1. **`net_extreme_4w` is referred as a closed negative, not as a near-miss.** It
   fails the pre-registered tail clause, its interval spans zero, its 80%-power
   threshold is nearly three times the observed effect, and the two deciding
   panels' agreement comes from opposite halves of the universe. **A replication
   of the same design on a window of the same length would have the same power
   and would settle nothing**, so spending one of the three remaining archive
   windows on it is not recommended. What would change the answer is a longer
   history or a design with fewer overlapping holds — both new work, and neither
   authorised here.
2. **Survey consensus history** for CPI and employment. Paid everywhere found. It
   would turn the macro family from a model-nowcast diagnostic into a real test.
3. **A full central-bank meeting calendar** for the four missing banks, which
   would take Stage A from four currencies to eight.
4. **Decision time of day** for the four acquired banks, which would make Stage A
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
