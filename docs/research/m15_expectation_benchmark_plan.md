# M15 — Expectation Benchmark Package: Decision-Grade or Skip (pre-registration)

**`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `PRODUCTION_READINESS_NOT_CLAIMED`.**

Base master `941fd0eca21fda6436b5f33a6a71bb3f02ea98eb` (the PR #472 merge).

**Frozen before any relationship between an expectation and an FX return was
computed.** What existed before this document is listed in §3: a power curve
built from the *unconditional* dispersion of forward returns, and an audit of
one free archive's internal integrity. Neither can be influenced by the
hypothesis, and both are recorded here so the thresholds can be checked against
what produced them.

---

## 1. The question, and why this package is different

Fourteen price-derived families and three exogenous ones have failed to produce
a reproducible expected-return source. The programme has measured **realised**
quantities (price, first-release macro actuals, policy rates, positioning) and
**timing** (a forward-known meeting anchor that reproduces at `1.58× / 1.63×`).
It has never held the other half of a repricing:

> **the expectation the market carried into the event.**

Expected return is realised minus expected. Every direction test so far has
compared price with price, or a realisation with a *model* proxy of the
expectation. This package asks whether **realised − expected** predicts FX
direction, for the three expectation sources that exist:

* **Family 1 — survey consensus macro surprise** (`actual − consensus`);
* **Family 2 — rate-path repricing** (change in what the market prices for
  policy);
* **Family 3 — signed order flow** (the expectation revealed by transactions).

## 2. Decision-grade or skip — the governing rule

**A cheap, underpowered test is worse than no test**, because it converts an
open question into an ambiguous null that invites another purchase. This package
therefore refuses to run any test that cannot decide.

For every hypothesis, the **Decision-Grade Minimum Requirement** in §4 is fixed
*before* acquisition. Data that does not meet it is recorded
`NOT_DECISION_GRADE_SKIP` and **not bought, not tested, and not partially
tested** — at any price.

Two grades are distinguished, and the distinction is the reason this package can
reach a decision at all:

* **Decision-grade for a KILL** — enough statistical power, correct timestamps,
  verified as-of integrity. A powered null on a sufficient event set closes the
  hypothesis.
* **Decision-grade for a CANDIDATE** — the above **plus** currency breadth,
  panel consistency and a tail under the ceiling.

A single-currency test can therefore **kill** but never **promote**. That
asymmetry is deliberate: promotion carries the whole programme's remaining
resources — the fresh pool — so it needs breadth; killing needs only power.

## 3. What was computed before this freeze

Two things, both recorded so a reviewer can check that no result drove a
threshold.

### 3.1 The power curve (design only)

Forward returns were taken at the **84 real US CPI release timestamps** already
held from the previous package, with random signs drawn **per event** so that
the cross-pair dependence inside an event survives the draw. This measures only
how noisy an event-time FX return is. No expectation data existed at the time.

Minimum detectable effect at 80% power, two-sided 5% (`2.802 × sd` of the null
mean), in pips per pair-event, scaled as `√(24/N)`:

| horizon · universe | N=24 | N=50 | N=100 | N=200 | N=400 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1h · 20 pairs | 5.21 / 5.96 | 3.61 / 4.13 | 2.55 / 2.92 | 1.80 / 2.06 | 1.28 / 1.46 |
| 1h · 7 USD pairs | 4.38 / 3.74 | 3.04 / 2.59 | **2.15 / 1.83** | 1.52 / 1.30 | 1.07 / 0.92 |
| 4h · 7 USD pairs | 6.98 / 5.68 | 4.84 / 3.94 | **3.42 / 2.78** | 2.42 / 1.97 | 1.71 / 1.39 |
| 12h · 7 USD pairs | 7.87 / 5.84 | 5.45 / 4.04 | 3.86 / 2.86 | 2.73 / 2.02 | 1.93 / 1.43 |
| 1d · 7 USD pairs | 15.40 / 8.49 | 10.67 / 5.88 | **7.54 / 4.16** | 5.33 / 2.94 | 3.77 / 2.08 |

(first value `momentum_2021_2023`, second `supplemental_2023_2025`)

The mean round trip at an event-time entry is **2.20 / 2.04 pips** on USD pairs,
so the **×2-cost break-even is about 4.1–4.4 pips gross**.

**This fixes the horizons before any result exists.** At `N ≈ 96` the design
detects a break-even effect comfortably at **1h** and **4h**, marginally at
**12h**, and **not at all at 1d**. Therefore:

> **Family 1 is run at 1h and 4h only. 12h and 1d are excluded a priori as
> underpowered at the available event count, and no 1d number will be reported
> as evidence.**

It also explains, without excusing, why the previous package's macro cells were
inconclusive: at `N = 24` the 1d cell could not have detected anything smaller
than 8–15 pips.

### 3.2 The free archive's internal integrity (audit only)

The Forex Factory historical calendar archive (§5.1) was fetched and audited
against ground truth already held. The audit measured the archive's own
consistency, never its relationship to an FX return. Its findings are in §5.

## 4. Decision-Grade Minimum Requirements

### 4.1 Family 1 — survey consensus macro surprise

| requirement | threshold | why this number |
| --- | --- | --- |
| historical depth | both deciding panels, 624 trading days each | the programme's existing panel structure |
| **event count** | **≥ 90 release-times per deciding panel** | §3.1: at `N ≈ 96` the MDE is 2.2–3.4 pips against a 4.1–4.4 pip break-even |
| currency coverage | **≥ 1 to kill**, **≥ 4 to promote** | §2 |
| **timestamp precision** | exact minute, from a documented release rule, **validated against an independent source** | a 1h horizon on a wrong timestamp measures nothing |
| first-release actual | the value as published, **verified against ALFRED vintages** | a revised actual is not what the market reacted to |
| consensus vintage | pre-release, and **behaviourally consistent with a genuine survey** (§5.3) | as-of-ness of a forecast cannot be proven from values; it can be falsified |
| prior value at event time | present | required by the surprise definition |
| revision separation | actual, prior and revised kept apart | carried over from the previous package |
| power | **MDE ≤ ×2-cost break-even at the tested horizon** | §2 |
| panel split | both deciding panels independently | carried over |

### 4.2 Family 2 — rate-path repricing

Two distinct hypotheses with different data needs, and only one is free:

* **F2-free — daily lead.** Does a day's change in a policy-sensitive yield
  predict the *next* day's FX move? Needs daily yields with panel-length
  history. Requirement: ≥ 400 usable days per deciding panel (§3.1 gives a 1d
  MDE of 2.1–3.8 pips at N=400, under the break-even).
* **F2-paid — event-time expected-path repricing.** Does the intraday repricing
  of the expected policy path around a release predict the subsequent FX move?
  Needs **intraday** short-rate futures with exact timestamps, continuous roll
  semantics and full panel coverage. **No free source has this**, so it is
  costed rather than run.

### 4.3 Family 3 — signed order flow

Trade-level history with aggressor reconstruction, consistent rolls, full panel
coverage, ≥ 400 usable days per deciding panel. **No free source has this**, so
it is costed rather than run.

## 5. Family 1 — the acquired source and what the audit found

### 5.1 Source

| | |
| --- | --- |
| **provider** | Forex Factory historical calendar, archived as `Ehsanrs2/Forex_Factory_Calendar` |
| **URL** | `https://huggingface.co/datasets/Ehsanrs2/Forex_Factory_Calendar` → `forex_factory_cache.csv` |
| **licence** | MIT, public, not gated. No account, no key, no payment |
| **bytes / digest** | 68,231,084 · `sha256 = f4e92bca4168cfe6…` |
| **rows / span** | 83,427 · `2007-01-01 … 2025-04-07` |
| **fields** | `DateTime, Currency, Impact, Event, Actual, Forecast, Previous, Detail` |

### 5.2 What passed

* **The actual is the first release, not a revision.** Of 75 US `CPI m/m` rows
  overlapping the ALFRED ground truth, **74 (98.7%)** match the ALFRED
  first-release month-over-month to 0.1pp. The single exception is a rounding
  boundary. **The archive is not backfilled with revised values** — the failure
  mode that would have made it worthless.
* **Coverage is complete.** 219 US `CPI m/m` rows over 18 years, no duplicates.

### 5.3 What the forecast column looks like

As-of-ness of a *forecast* cannot be proven from values alone; it can be
falsified, and it was not:

| US indicator | n | exact `A = F` | `sd(A−F)` | `sd(A−F) / sd(A−prior)` |
| --- | ---: | ---: | ---: | ---: |
| CPI m/m | 69 | 33.3% | 0.144 pp | 0.45 |
| Core CPI m/m | 68 | 30.9% | 0.154 pp | 0.81 |
| Non-Farm Employment Change | 76 | 1.3% | 121k | 0.34 |
| Unemployment Rate | 76 | 15.8% | 0.076 pp | 0.60 |
| Retail Sales m/m | 74 | 2.7% | 0.160 pp | 0.31 |
| PPI m/m | 53 | 15.1% | 0.260 pp | 0.53 |
| Average Hourly Earnings m/m | 76 | 19.7% | 0.057 pp | 0.66 |

Three things a contaminated column could not do: `sd(A−F)` for CPI m/m is
**0.144pp**, the documented accuracy of the professional survey rather than
something implausibly small; the ratio to the naive prior-value benchmark is
**0.31–0.81**, so the forecast carries real information without being the answer;
and Average Hourly Earnings shows `corr(A,F) = 0.200`, the behaviour of a
genuinely hard-to-forecast series. **This is evidence, not proof**, and it is
labelled that way wherever the result is reported.

### 5.4 What failed, and the consequence

**The archive's timestamps are wrong.** Against 75 known US CPI release
timestamps the archive is **−17 hours early on 63 and −16 hours on 11** — a
timezone-handling defect in the scraper, systematic but not a constant, and the
error is large enough to move an event onto the wrong UTC **date**.

The error cannot be corrected from the archive alone without the ground truth
that would make the correction unnecessary. Therefore:

> **The archive supplies values only. Every release timestamp is taken from
> ALFRED's vintage date plus the statistical agency's documented release time,
> and the two sources are cross-checked and the agreement rate reported.**

This is the same construction the previous package validated at 84 of 84, and it
restricts Family 1 to indicators ALFRED carries — which is why the free branch is
**USD-only** and can therefore **kill but not promote** (§2).

### 5.5 Verdict on the consensus source

`FREE_CONSENSUS_DECISION_GRADE_FOR_A_USD_KILL_NOT_FOR_A_MULTI_CURRENCY_CANDIDATE`
— Case A of §9 restricted to one currency, and Case B for breadth.

## 6. Family 1 — the frozen test

**Release families and their ALFRED anchors.** All four print at **08:30
America/New_York**, a time fixed by rule and published a year ahead, converted
with the real daylight rule.

| release family | signals | ALFRED series for the release date |
| --- | --- | --- |
| CPI | `CPI m/m`, `Core CPI m/m` | `CPIAUCSL` |
| Employment Situation | `Non-Farm Employment Change`, `Unemployment Rate`, `Average Hourly Earnings m/m` | `PAYEMS` |
| Retail Sales | `Retail Sales m/m`, `Core Retail Sales m/m` | `RSAFS` |
| PPI | `PPI m/m` | `PPIFIS` |

**Surprise.** `z = (actual − forecast) / s`, where `s` is the standard deviation
of `(actual − forecast)` over the **preceding 24 releases of that signal only** —
an expanding, strictly backward-looking scale. A full-sample scale is a leak.

**Composite.** A release-time carries one surprise: the **mean of the
standardised surprises of the signals in that release**, each already oriented by
its own pre-registered sign.

**Pre-registered signs, fixed here before any return was computed.** Every one is
the same economics — a stronger or more inflationary print is hawkish for the
Fed and appreciates the USD:

| signal | sign |
| --- | ---: |
| CPI m/m, Core CPI m/m | **+1** |
| Non-Farm Employment Change | **+1** |
| Unemployment Rate | **−1** |
| Average Hourly Earnings m/m | **+1** |
| Retail Sales m/m, Core Retail Sales m/m | **+1** |
| PPI m/m | **+1** |

**A measured effect in the opposite direction drops the family. It is never
inverted.**

**Position.** Long USD when the composite `z > 0`, short when `z < 0`, in every
pair with a USD leg. Entry at the open of the **first M15 bar starting strictly
after** the release timestamp. Cost is one round trip from **that bar's own
spread**, and every headline is repeated at **×2**.

**Cells.** Pooled × {1h, 4h} = **2 primary**; 4 release families × {1h, 4h} =
**8 secondary**. **10 cells, the entire search**, corrected together by
Westfall–Young family-max over 200 draws of a null that permutes the surprise
across release-times while leaving the events, the pairs and the returns fixed.

**Reported for every cell** (plan carried over): directional IC, signed return,
gross, cost, net, expectancy per event, event count, pair breadth, panel
consistency, tail share as **top-10 events over net**, event-class breakdown,
cost ×2, the 95% interval from the null, and the MDE at 80% power from the same
null.

## 7. Family 1 — kill and pass conditions

**Kill — `SURVEY_CONSENSUS_MACRO_EDGE_NOT_SUPPORTED`** if **any** holds on the
primary pooled cells:

* the family-max corrected `p ≥ 0.05` on either deciding panel;
* net ≤ 0 at ×1 cost on either deciding panel;
* the sign reverses between the deciding panels;
* the top ten events contribute more than **50%** of net;
* fewer than 90 release-times on either deciding panel.

**A kill is final for this programme.** No second consensus provider is bought to
retry it, which is the rule §2 exists to enforce. It is recorded as
`SURVEY_CONSENSUS_MACRO_EDGE_NOT_SUPPORTED_ON_USD_AT_DECISION_GRADE_POWER`, and
the interpretation is fixed here, before the result: **a powered USD null closes
Family 1 for the continuation decision**, because the mechanism under test —
surprise → rate repricing → currency — is not USD-specific, USD is a leg of 7 of
the 20 pairs and the most heavily analysed currency in the sample, and buying
multi-currency consensus after a powered null would be the rescue purchase this
package forbids.

**Pass.** Survives every clause → `SURVEY_CONSENSUS_MACRO_EDGE_SUPPORTED_ON_USD`,
which is **not** a candidate: promotion additionally needs breadth (§2), and that
is where paid multi-currency consensus becomes justified — a purchase made
*after* a positive, never to rescue a negative.

## 8. Family 2 — the free test that is run

**F2-free.** Daily change in the US 2-year Treasury yield (`DGS2`, FRED, free,
daily since 1976) as a proxy for repricing of the expected policy path.

* **Research question**: does a day's rate repricing *lead* the FX move, or is it
  contemporaneous?
* **Pre-registered sign**: a **rise** in the US 2-year yield appreciates the USD.
* **Population**: every trading day of each deciding panel with a `DGS2`
  observation on day `t` and `t−1`; position held from the first M15 bar of day
  `t+1` for **1 day**.
* **Contemporaneous control**: the same-day association is computed and reported
  as a diagnostic. **The test is about the lead**, and a contemporaneous
  association with no lead is a negative result, not a partial success.
* **Cells**: 2 — the lead and the same-day diagnostic. Corrected together.
* **Power**: ≥ 400 days per panel gives an MDE of 2.1–3.8 pips against a
  break-even of about 4.2, so the test decides.
* **Kill**: `RATE_LEAD_NOT_SUPPORTED` on the same clause set as §7.

**F2-paid is not run.** The hypothesis that matters — intraday expected-path
repricing around an event — needs short-rate futures at exact timestamps across
both panels. Free daily yields cannot address it and a partial purchase is
forbidden, so §10 costs the full package instead.

Free daily yields exist for **USD (FRED), CAD (Bank of Canada Valet) and GBP
(Bank of England)** and, for the other five currencies, only at **monthly**
frequency (62 points per panel). A cross-currency yield-differential test is
therefore **`NOT_DECISION_GRADE_SKIP`** on breadth, and is not run at two pairs.

## 9. Family 3 — not run, costed

No free source carries trade-level FX futures history with aggressor
reconstruction over both panels. §10 prices the full decision-grade package. **No
trial, no free credit, no one-month sample** — those are the shapes §2 forbids.

## 10. What is priced, and how a purchase is judged

For every paid candidate the report states the **total cost of the full
decision-grade package**, never a pilot price, and classifies it:

`BUY — DECISION GRADE` · `REQUEST QUOTE` · `SKIP — INCONCLUSIVE` ·
`SKIP — LOW INFORMATION VALUE` · `SKIP — TOO EXPENSIVE FOR CURRENT EVIDENCE`.

A candidate may be bought only if it answers a hypothesis the free branch could
not, carries new information, is decision-grade at full coverage, and can end the
question in one shot. **Price alone never qualifies or disqualifies**; a cheap
dataset that cannot decide is `SKIP — INCONCLUSIVE`, which is the worst outcome
this package recognises.

## 11. Stop rule

Families 1, 2 and 3 are the **final** expected-return source tests. If each is
either **tested at decision grade and null**, or **not decision-grade at an
acquisition cost the evidence cannot justify**, the recommendation is

> **`FX_SPOT_DIRECTIONAL_ALPHA_RESEARCH_CLOSED`**

with the fresh pool `2016-06-02 … 2021-04-25` **left unread**, and futures named
as the pivot candidate — evaluated, not implemented.

## 12. ML

Not used. Re-entry needs all five: an expected-return source surviving §7 on both
deciding panels; positive after realistic cost; same sign on both panels; enough
events; and either two independent sources or an explicit interaction
hypothesis. A base that does not stand on its own is never handed to a model.

## 13. Hard boundaries

Not crossed: the fresh pool, the historical OOS slice, the dead window, the
future epoch, Formal Confirmation, broker/demo/live, a real order, production
deployment, **a paid contract, a trial, a metered API, account creation, a
subscription, a broker login, entering a secret**. Provider research is public-web
only.

## 14. Review

Two roles at the end, given the source, diff and this plan and not each other's
conclusions: **Role 1** economics, statistics and information value; **Role 2**
provenance, temporal integrity, leakage and implementation.

## 15. Amendments

None yet. Each appends here with the commit that made it, what forced it, and the
statistic it precedes.
