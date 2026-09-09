# FX spot feasibility frontier — unit audit, and the frontier it corrects

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `PRODUCTION_READINESS_NOT_CLAIMED`

Status: **`UNIT_CONSISTENCY_VERIFIED`**, and
**`PRIOR_FRONTIER_CONCLUSION_CHANGED_RESEARCH_NOT_STARTED`**.

This discharges §1 of the execution decision — the unit-consistency audit that
had to pass before Track 1, 2 or 3 could begin. It reports what was wrong, what
the corrected measurement says, and why the second half of §1 then fired: *"if
the existing frontier's conclusion changes under the unit correction, return to
Human + ChatGPT without starting the research."* It changed, in a way that
removes Track 1's approved primary design. The hypothesis stages of all three
tracks are therefore **not started**.

Every number is measured on the two already-seen deciding panels only. The fresh
pool `2016-06-02 … 2021-04-25`, the historical OOS slice, the dead window and the
forward Formal Confirmation epoch were not read, and the code in
`scripts/research/clock_flow/` holds no archive path, so it cannot open one.

Artifact: `artifacts/research/clock_flow/frontier.json`. Every figure below is
machine-checked against it.

---

## 1. The defect

Three problems, nested, in one table.

**1.1 Two units.** Calendar rows were basis points; event rows were **pips**, and
the hurdle printed beside them was a pips figure. On `EUR_USD` one pip is 0.93 bp,
so the two columns looked like each other; on `USD_JPY` one pip is 0.67 bp. Pips
are a quote-currency unit whose economic size depends on the price level, basis
points are relative, and only the second can be summed across pairs or netted
against a portfolio return.

**1.2 Two universes.** Calendar rows were the median across twenty pairs. Event
rows were `EUR_USD` alone.

**1.3 Two notionals — the one that moved the numbers.** The MDE was a
**portfolio** statistic: a twenty-pair currency basket carrying two units of gross
currency exposure. The hurdle beside it was **one pair's** median round trip,
doubled. Implementing that exposure through the available pairs trades
`Σ|w_p| = 1.549` units of pair notional, so the book pays about 1.55× a single
pair's cost before anything else is considered.

An earlier draft of this document attributed most of that factor to the
`1/n_counterparties` weighting over-weighting the wide-spread `NZD`, `CAD` and
`CHF` legs. **That was wrong.** The independent audit decomposed it: the total is
1.602 / 1.629 and the composition term is only 1.034 / 1.052. It is almost
entirely traded notional, not the spread profile.

The MDE itself had been computed correctly. **The entire original error was on
the cost side of the comparison.**

## 2. The corrected convention

> Every return, cost, hurdle, minimum detectable effect and interval is **basis
> points of the mid price at the moment of the trade**, converted per observation
> and never with a panel-wide constant.

`scripts/research/fxunits.py` holds it. `pips_to_bp` is the only conversion;
`verify_unit_consistency` walks a finished record and names any numeric field
that is not `_bp`. A subtree holding no monetary quantity declares itself
`{"_unit": "count"}` — and after the audit showed that marker skipping four
monetary siblings on one subtree, the design descriptors are now named one by one
in the exempt list instead, and the marker survives on exactly two subtrees that
contain nothing else.

Three corrections travel with it:

- **Cost is charged at both ends** — half the round trip at the entry bar's
  spread and mid, half at the exit bar's. A window ending in a liquidity hole
  pays for that hole. The direction is chosen at entry, so the exit spread enters
  only as a subtraction.
- **The clock is local.** The WM/Refinitiv benchmark is struck at 16:00
  **London**: 16:00 UTC on 209 of the momentum panel's trading days and 15:00 UTC
  on 312.
  Reading a fixed UTC hour measures a seasonal mixture of the fix and the hour
  beside it, and it is what smeared the rollover spike across "hour 21" and "hour
  22". It is one spike, at 17:00 New York.
- **The gate uses the median round trip, not the mean.** `MDE ≤ 2 × cost`
  compares an effect against a design's own cost, so a fatter cost tail *bought*
  decidability. The mean is still reported, as the expectancy cost, because that
  is what a strategy pays.

## 3. Five defects an independent audit found in the first correction

All were fixed before the numbers below were produced, all are pinned by a test,
and **every one of them made a design look better than it is.**

1. **A window did not have to be near its moment.** The only filter was that its
   four bars were contiguous. On the 103 partial Sundays in each panel no pair
   has a bar before about 21:00 UTC, so a "pre-fix" window became Friday's last
   hour — 46 hours early, and perfectly contiguous — and a "post-fix" window
   became the weekly open. 16.5% of every clock cell, and the reason `n_events`
   equalled `n_days` exactly. `spread_by_moment` thirty lines away already
   applied the right test, so the two halves of the artifact disagreed about
   which days existed.
2. **A window could open at the weekly reopen**, the widest spreads of the week.
3. **The hurdle was a mean over that inflated tail** (see §2).
4. **A "1d" horizon was two overlapping days**: the exit was taken at the end of
   `days[start + step]`, so every horizon ran a day long, and at `step = 1`
   consecutive events shared a whole day.
5. **The MDE was one draw, and an average over directions.** One random direction
   per event makes the gross series independent by construction; the resulting
   number matched the i.i.d. standard error to within 1%, which is exactly the
   shortcut the docstring claimed to be avoiding. At the 25 events of a month-end
   cell the same cell read 21.5 bp and 14.2 bp on two runs differing only in how
   far the generator had advanced.

Directions are now drawn 200 times in each of two regimes — independently per
event, and held fixed across a panel so that abutting windows and a persistent
rule appear as serial dependence — and the gate uses the 90th percentile of the
persistent branch, with a lag-one deflation of the effective sample size.
`mde_optimistic_bp` carries the other end of the range.

## 4. The corrected frontier

Two deciding panels: **521 and 518 trading days** (1.996 years each; 103 and 106
partial sessions excluded), twenty pairs, eight currency states. Portfolio
directions are drawn from a generator, so no signal-to-return relation exists to
be found.

### 4.1 Statistical power

MDE is the conservative figure; the optimistic one is in brackets. The hurdle is
twice the median round trip.

| design | N | dispersion | MDE | hurdle | powered |
| --- | ---: | ---: | ---: | ---: | --- |
| calendar 1d | 519 / 517 | 34.2 / 30.0 | **5.28 [4.22] / 4.54 [3.70]** | 6.84 / 6.35 | **yes** |
| calendar 1w | 102 / 102 | 73.7 / 63.7 | 25.7 / 22.8 | 16.1 / 6.17 | no |
| calendar 2w | 50 / 50 | 103 / 90.7 | 55.6 / 45.5 | 15.8 / 6.16 | no |
| calendar 1m | 23 / 23 | 160 / 129 | 121 / 96.3 | 6.81 / 6.36 | no |
| london_fix pre | 521 / 517 | 11.6 / 9.1 | 2.00 / 1.54 | 5.88 / 5.68 | yes |
| london_fix post | 521 / 517 | 8.3 / 6.8 | 1.26 / 1.05 | 5.89 / 5.71 | yes |
| london_open pre | 520 / 518 | 7.7 / 7.6 | 1.29 / 1.26 | 6.19 / 5.88 | yes |
| ny_option_cut pre | 521 / 518 | 9.9 / 8.2 | 1.64 / 1.32 | 6.31 / 6.19 | yes |
| tokyo_fix pre | 519 / 517 | 6.4 / 5.6 | 1.04 / 0.94 | 6.57 / 6.14 | yes |
| rollover pre | 521 / 517 | 3.6 / 4.6 | 0.56 / 0.72 | 8.69 / 7.24 | yes |

**The daily calendar design is powered**, where the old frontier said it was not
— though its headroom is 1.56 / 1.82 bp, not the 7.8 bp an intermediate version
of this document reported before the audit's fixes. That row alone fires §1: the
previous report's headline, *"the decidable region is event time, not calendar
time"*, is false.

### 4.2 Economic feasibility, which the power gate cannot see

    break-even gross IR = (mean cost / dispersion) × √(events per year)

| design | events/yr | break-even gross IR |
| --- | ---: | ---: |
| calendar 1m | 11.5 | **0.09 / 0.10** |
| calendar 2w | 25.1 | **0.38 / 0.17** |
| calendar 1w | 51.1 | **0.77 / 0.35** |
| calendar 1d | 260 / 259 | 2.08 / 2.04 |
| london_fix pre, every day | 261 / 259 | 4.12 / 5.00 |
| ny_option_cut post, every day | 261 / 259 | 4.10 / 4.93 |
| london_fix post, every day | 261 / 259 | 5.88 / 6.73 |
| london_open pre, every day | 260 / 260 | 6.58 / 6.20 |
| tokyo_fix pre, every day | 260 / 259 | 8.48 / 8.88 |
| rollover pre, every day | 261 / 259 | 24.0 / 14.9 |
| rollover post, every day | 209 / 206 | 58.7 / 49.1 |

Nothing this programme has produced has had a gross IR near 1.5. **Every
every-day clock window needs between four and fifty-nine just to break even.**
The powered region and the payable region do not overlap anywhere in the
every-day rows — which is what the previous report guessed, and then contradicted
itself about by claiming event time resolved the tension. It does not: an event
window traded daily is a daily strategy.

### 4.3 What resolves it: selectivity — and how little survives

An event design decouples dispersion from frequency: the window length fixes `σ`,
selectivity fixes `f`. That leaves a band, quadratic in `1/cost`:

    f_min = (1.401 · σ/median cost)² / years     (powered)
    f_max = (IR_max · σ/mean cost)²              (payable)

Measuring the month-end and quarter-end subsets directly rather than
extrapolating — 25 and 8 events per panel:

| cell · month-end | MDE | hurdle | powered | break-even IR |
| --- | ---: | ---: | --- | ---: |
| **london_open pre** | 6.03 / 5.87 | 6.23 / 5.96 | **yes / yes** | **1.42 / 1.36** |
| tokyo_fix pre | 4.70 / 4.85 | 6.54 / 6.23 | yes / yes | 1.83 / 2.30 |
| ny_option_cut pre | 6.32 / 7.96 | 6.33 / 6.39 | yes / no | 1.40 / 1.22 |
| london_fix post | 7.17 / 4.42 | 5.91 / 5.78 | no / yes | 1.25 / 1.61 |
| london_open post | 6.18 / 5.88 | 6.09 / 5.98 | no / yes | 1.33 / 1.27 |
| london_fix **pre** | 14.7 / 10.5 | 5.85 / 5.77 | **no / no** | **0.59 / 0.82** |
| ny_option_cut post | 13.9 / 10.1 | 5.85 / 5.77 | no / no | 0.60 / 0.82 |
| tokyo_fix post | 3.32 / 6.41 | 6.47 / 6.18 | yes / no | 2.47 / 1.36 |

At quarter-end (8 events per panel) **nothing is powered** except the rollover
windows, whose economics are hopeless anyway.

Two things stand out, and they point in opposite directions.

**The cell with the best economics is the one with no power.** The London fix
pre-window at month-end needs a break-even gross IR of only 0.59 / 0.82 — the
most plausible number anywhere in the grid outside the multi-week calendar rows —
and it is *not* adjudicable on either panel, because its month-end dispersion is
17.40 / 12.59 against an all-day 11.64 / 9.12. Volatility 1.49× / 1.38× higher at
month-end is a signature consistent with a concentrated rebalancing flow. It is
also exactly what destroys the power to measure its mean.

**Exactly one cell is powered on both deciding panels and payable at
`IR_max = 1.5`: the London *open* pre-window at month-end**, and it passes the
power gate by 0.20 and 0.09 bp. That is one cell, on a margin of three per cent,
out of thirty measured.

### 4.4 The cost surface, now the highest-leverage variable

`f_max` is quadratic in `1/cost`: **halving execution cost multiplies the feasible
band by four.** No plausible improvement in a signal does that. Four measured
facts bear on it.

| | momentum | supplemental |
| --- | ---: | ---: |
| all bars, median round trip | 2.258 | 2.130 |
| at the London fix | 2.075 | 1.997 |
| at 17:00 New York (rollover) | **9.885** | **8.112** |
| last bar before the weekend | **8.693** | **6.335** |
| an ordinary 23:45 UTC close | 2.439 | 2.193 |

- **Two spikes, not a gradient.** Across both panels the round trip sits between
  1.99 and 2.49 bp in twenty-two of the twenty-four UTC hours; 21:00 is 6.43 /
  4.94 and 22:00 is 3.37 / 2.92, and that is one spike split by daylight saving.
  There is no cheap hour to move into — only two expensive moments to avoid.
- **The weekly close is the second spike**, 3.6× / 2.9× an ordinary close. It
  surfaced through an artifact: 84% of the momentum panel's "1w" periods happen
  to end on a Friday and 1% of the supplemental panel's do, because five *trading*
  days is not one *calendar* week and holidays shift the alignment. The same
  misalignment shows in the median hold the artifact now records — 116.75 hours
  against 167.75 for the same nominal horizon — and the 2.6× cost difference
  between those two rows is that alignment, not economics. The underlying fact is
  real and applies to any design holding across the weekend. A horizon defined in
  calendar weeks rather than trading days would remove the artifact; the daily
  and monthly cells are unaffected, holding 23.75 and 695.75 hours on both panels.
- **The construction trades 1.55× the exposure it expresses.** Cutting that is a
  design question about which pairs implement a currency view, not a signal
  question.

## 5. Verdict on §1

| question | answer |
| --- | --- |
| A transcription error? | No. |
| Currency-basket returns in bp? | Partly — the calendar rows were, correctly. |
| Pair costs in pips? | Yes, the event rows, on `EUR_USD` only. |
| A deliberate conversion? | No. |
| Root cause | A portfolio-scale MDE compared against a single-pair-scale cost hurdle, with a pips/bp mix and a one-pair/twenty-pair mix on top. |
| Corrected convention | Basis points of mid, per observation. |
| Machine-verifiable status | `UNIT_CONSISTENCY_VERIFIED`. |
| **Did the previous frontier's conclusion change?** | **Yes — and it removes Track 1's approved primary design.** |

What changed:

1. **Daily calendar designs are powered.** The headline "the decidable region is
   event time, not calendar time" is withdrawn.
2. **Every-day clock windows are economically impossible** (break-even gross IR
   4.1 to 58.7). §3 of the decision asked for primary cells A (pre-fix drift), B
   (post-fix reversal) and C (month-end amplification). **A and B as every-day
   cells cannot pay**, and C is therefore not an amplifier on a base cell — it is
   the only form in which A and B could exist at all.
3. **Selectivity does not rescue the London fix.** At month-end the fix
   pre-window has the best economics in the grid and no power on either panel.
   The one cell that is powered on both panels and payable is the London **open**
   pre-window at month-end, by 0.20 and 0.09 bp — a margin too thin to
   pre-register eight cells around.
4. **Execution cost is the dominant lever, quadratically**, and the cost surface
   has two discrete spikes rather than a gradient. Track 3 is no longer a
   supporting exercise.

Per §1, the research is **not started**: no hypothesis tested, no cell
adjudicated, no pre-registration frozen, in any of the three tracks.

## 6. What a re-decision needs

**Q1. What is `IR_max`?** The band's ceiling is the largest gross information
ratio worth believing in advance. This document reports every band at 1.0, 1.5
and 2.0 rather than choosing. At 1.0, `london_open pre · month-end` (1.42 / 1.36)
falls outside and **nothing in the grid survives both gates**; at 2.0 five
month-end cells do. The choice decides whether Track 1 exists.

**Q2. May a month-end cell pool the two deciding panels?** At 25 events per panel
the cells sit on the power margin, and one of them passes on one panel and fails
on the other three times in the table above. Pooling gives `N = 50` and power;
the two-panel-agreement rule exists to prevent exactly that borrowing. A ruling is
needed on whether pooled estimation plus per-panel sign agreement satisfies it.

**Q3. Should Track 3 be resequenced ahead of Track 1?** It is now the
highest-leverage item by a wide margin, it is purely offline and already
approved, and its result changes which cells are worth pre-registering: at half
the cost the London fix pre-window at month-end moves from unpowered to powered
and stays the best-economics cell in the grid. Freezing a Track 1
pre-registration first risks freezing cells a cost improvement makes obsolete.

**Q4. Does Track 1 survive at all in its approved form?** §3 named A, B and C as
primary. On this measurement A and B are impossible daily and C is not an
amplifier but the only viable frequency, and at that frequency the fix — the
mechanism with the strongest published rationale — is the one cell that cannot be
measured. A design that honours the mechanism and the frontier at once would be a
small number of month-end cells with pooled estimation, which is Q2, or a
Track-3-first sequence, which is Q3.

A statement rather than a question: the previous report's §E, §T and §Y answers
1–5 rest on the withdrawn frontier and are **superseded by this document**.

## 7. Review record

Roles used: implementation (this session) and one independent review role
(temporal integrity / provenance / unit consistency / leakage / cost modelling),
given the source, the diff and the artifact but not the implementer's
conclusions. Role 1 (economics / statistics / novelty / multiple testing / power)
was not run, because §1 fired before any hypothesis existed for it to review.
That is a gap, and it is named here rather than left implicit.

The review returned two blockers and four required fixes; all six were accepted
on their evidence and fixed, and §3 lists five of them. It also refuted a claim
this document had made about *why* the portfolio costs 1.55× a single pair
(§1.3), and showed that the conclusion in §5 survives every correction while the
row originally cited to support it did not. Re-running the corrected code
surfaced one further defect the review had not seen — a tz-aware moment
subtracted from a naive bar timestamp in the new proximity check — which a test
caught as a `TypeError`; had the two sides been silently comparable it would have
been a shifted window instead.

Machine checks: 53 tests in `tests/research/test_clock_flow.py`, `ruff check` and
`ruff format --check` clean, and every figure in this document verified against
`frontier.json` by a script rather than by transcription.
