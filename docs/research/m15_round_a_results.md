# M15 Research Program — Round A: results

**`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `PRODUCTION_READINESS_NOT_CLAIMED`.**

Plan: `docs/research/m15_round_a_plan.md`, committed at `e7d53b2` **before any
cell was computed**. Base master `b274762` (the PR #467 merge).

**Next branch: Case B — cost-aware / first-passage label redesign.**

`TRACK_A_RESEARCH_PROGRAM_ROUND_A_COMPLETED`.

> **This document's first version said Case A.** Two independent review roles
> showed both of A's conjuncts were unsupported: T1's "abundant opportunity" is a
> statistic a zero-information random walk scores **higher** on, and the screen
> that produced A's single candidate fires on **22.7%** of pure noise. A third
> defect settled it — the plan's sample condition is per pair, the code applied it
> pooled over twenty, and under the registered reading Round A has **zero**
> structural candidates. §11 records what changed and why.

---

## 1. The two findings

**T1 — the opportunity metric is a tautology, and the real constraint is a number
nobody had computed.** Forward excursions are large relative to cost at every
horizon: median MFE ÷ median cost runs 6.8 at 4 hours to 58.4 at 5 days. But an
IID shuffle of each pair's own bars — same volatility, same bar shapes, **all
serial structure destroyed** — scores **higher on every horizon and every panel**
(real ÷ null = 0.80 to 0.92). A market with provably no exploitable structure
beats the real one on this metric, because `median MFE / cost` is essentially the
identity `1.1 · (σ/cost) · √H`.

What replaces it: the **break-even information coefficient**,
`cost / sd(terminal move)` — the signed edge the movement must be predicted with
for it to pay for the spread. It is **1.67–1.73% at 5 days**, **2.54–2.68% at 48
hours**, **5.04–5.20% at 12 hours** on the two long panels. Set against the ICs
this programme has measured at the 5-day horizon — **−5.85%, +2.35%, −25.07%** —
every one exceeds break-even **in absolute value**. The constraint has never been
that the market moves too little, nor that the signal is too weak. It is that
**the sign does not persist**, and Round A puts a number on how much weaker it
could afford to be: at 5 days, about 1.7%.

**T2 — conditioning did not stabilise the sign, and the screen that said
otherwise fires on noise a fifth of the time.** Of 39 pre-registered cells,
**zero** pass the six-condition structural screen under the plan's own reading of
its sample condition. Under the looser reading the code first used, exactly one
passes — and the screen's measured false-positive rate is **0.2268**, with a null
mean of 0.31 cells passing. "One of 39" is what the null does.

## 2. Identity

| | |
| --- | --- |
| PR #467 | merged, merge commit **`b274762e4335f4f0fee7dc7b2ae93558e2db28b6`** |
| verified before merge | head `ab640df` matched, CI green, `MERGEABLE`/`CLEAN`, no unresolved review comment |
| Round A plan | `e7d53b2`, committed before any cell was computed (an audit verified this against artifact mtimes) |
| panels | `2021-04-26…2023-04-25` (624 trading days), `2023-04-26…2025-04-24` (624), `2025-04-25…2025-12-28` (212) |
| declared vs **measured** span | identical on all three panels |
| pairs | `PAIRS_20`, all twenty |
| bars | 999,238 + 993,878 + 335,200 |
| **new market-data reads** | **zero** |
| fresh pool `2016-06-02…2021-04-25` | **untouched** |

`scripts/research/round_a/` contains no reader and no archive path, so it cannot
open a market-data file. What keeps the fresh pool out of reach is the span guard
inside each of the three routes — an audit verified all three refuse it — not the
package boundary; an earlier version of this document claimed the latter and it
was wrong. Nothing under `scripts/m15_track_a/` was touched: the fingerprint
re-derives to 32 files and `e147542a…`, and the WP5 pin passes.

The **measured** span is reported beside the declared one because `bars.load` —
unlike `momentum.load` and `supplemental.load` — does not validate the rows it
serves, so the development panel's span was previously a transcribed constant. It
is now measured, and matches.

## 3. T0 — the infrastructure

Reused unchanged: `engine.atr_pips` / `zscore` / `donchian` /
`higher_timeframe`, `familywise.family_wise`, `momentum_inference.interval` and
`.difference`, and `round2`'s constants (`Z_WINDOW = 480`, `ATR_PERIOD = 14`,
`ATR_RANK_WINDOW = 960`, `N_PHASES = 8`).

New: the **hypothesis ledger** (nine entries; roughly 1,200 configurations have
been evaluated against the 2025 window, which is why the plan makes 2025
corroboration rather than a vote), the **standard diagnostic block**, and — added
after review — **`benchmarks.py`**, carrying the three nulls this round turned
out to need: the IID shuffle for T1, the studentized family-max for T2, and the
screen's own false-positive rate.

## 4. T1 — the Tradability Atlas

### 4.1 The measurements, and the null that refutes their headline

Unconditioned, all pairs. `median MFE ÷ median cost` is the statistic the plan
registered; the null column is the same statistic on IID-shuffled bars:

| H | panel | real | **null** | real ÷ null | **break-even IC** |
| ---: | --- | ---: | ---: | ---: | ---: |
| 16 (4h) | 2021–23 | 9.46 | 11.81 | 0.80 | 8.66% |
| | 2023–25 | 8.35 | 10.41 | 0.80 | 8.95% |
| | 2025 | 6.79 | 7.93 | 0.86 | 12.50% |
| 48 (12h) | 2021–23 | 17.44 | 21.05 | 0.83 | **5.04%** |
| | 2023–25 | 15.54 | 18.73 | 0.83 | 5.20% |
| | 2025 | 12.45 | 14.11 | 0.88 | 7.23% |
| 96 (24h) | 2021–23 | 25.81 | 30.14 | 0.86 | 3.58% |
| | 2023–25 | 22.98 | 26.92 | 0.85 | 3.69% |
| | 2025 | 18.09 | 20.05 | 0.90 | 5.22% |
| 192 (48h) | 2021–23 | 36.92 | 42.98 | 0.86 | **2.54%** |
| | 2023–25 | 33.04 | 38.44 | 0.86 | 2.68% |
| | 2025 | 26.00 | 28.62 | 0.91 | 3.78% |
| 480 (5d) | 2021–23 | 58.44 | 68.70 | 0.85 | **1.67%** |
| | 2023–25 | 52.54 | 61.35 | 0.86 | 1.73% |
| | 2025 | 41.36 | 44.91 | 0.92 | 2.55% |

**The real market never beats the null.** The horizon monotonicity is `√H`, the
cross-period stability is the stability of `σ`, and the whole atlas is
`1.1 · (σ/cost) · √H`. Under the plan's thresholds 119 of 120 cells are
"opportunity-rich" and one is marginal — but an audit showed the minimum ratio
across all 120 cells is 2.52 against an "unattractive" line of 1.5, and
`P(MFE > 2×cost)` never fell below 0.587 against a line of 0.50. **The
classification could not have failed.** It is reported for completeness and
carries no information.

**Withdrawn from the first version**: "the opportunity is abundant, and it always
was"; "the binding constraint is prediction, not opportunity" stated as a finding
rather than as a property of an oracle maximum over two directions; and "a
strategy needs to capture about 4% of the median available excursion to break
even", which was the most misleading sentence in the document — a direction-blind
strategy captures **none** of the MFE however large it is.

### 4.2 What the atlas does establish

**Case C is ruled out**, for a weaker reason than the first version gave. Not
"movement is abundant" — the null has more of it — but: *at the horizons this
programme has been working at, cost is not the quantity that decides the answer.*
Break-even at 5 days is an IC of 1.7% and the measured |IC| has been 5.85%, 2.35%
and 25.07%. Cost is a real drag and it closed every sub-daily strategy in Round 1;
at 2 days and beyond it is not what is missing.

**Rollover is the one cost feature.** Median round trip 4.6–6.0 pips against
2.3–2.9 elsewhere, halving the ratio, and the only cell the classification called
marginal. Sessions are otherwise indistinguishable on median MFE — 88.8 / 88.6 /
88.5 at h192 on the 2021–23 panel, a **0.3%** spread. The first version said
"within 3%" of the *ratio*; that spread is **13.5%** and it is a statement about
the cost denominator, not about opportunity.

**ATR terciles** move the ratio from 23.4 (low, 2025) to 37.5 (high, 2021–23) —
the arithmetic behind Round 2's ATR-high effect, and a 15% shift on a base of
25×, not a boundary between tradable and untradable.

### 4.3 What it implies for label design

1. **A time exit captures 0.52–0.56× of a perfect exit** (median |terminal move|
   ÷ median MFE, every panel, h192 and h480). "The return at horizon" addresses
   about half the movement a first-passage label could.
2. **The drawdown paid *to reach* a favourable move is smaller than the first
   version said.** `mae_at_mfe` is the opposite-side maximum over the *whole*
   window and can occur after the favourable peak; the plan's wording is "the
   drawdown paid to reach it". `atlas.adverse_before_peak` computes the pre-peak
   quantity on a strided sample and the two differ materially, so "a stop tighter
   than roughly 8× cost would be hit routinely" overstated the requirement. The
   measured figures are in `t1_null_benchmark.json`.
3. **The design target is an IC, not a pip count.** Any label redesign should be
   judged against the break-even IC for its horizon: 1.7% at 5 days, 2.5% at 48
   hours, 5.0% at 12 hours.

**The prohibition stands.** MFE and MAE are computed from future bars on purpose.
The plan (§4.5) and `atlas.py` both record that they may never be a feature, a
filter, a conditioning variable or an entry rule; tests assert no Round A module
evaluates a position and that `screen.py` contains no excursion token at all.

## 5. T2 — the Conditional Sign Screen

### 5.1 The six conditions

39 cells: five marginal condition families (13 levels) × three horizons, context
direction fixed per family before the run, non-overlapping and phase-averaged
over 8 offsets.

| condition | cells passing |
| --- | ---: |
| 1 — the two 730-day panels agree in sign | 29 / 39 |
| 2 — 2025 is not strong counter-evidence | 22 / 39 |
| 3 — \|effect\| ≥ 2 × median round-trip cost in both | **4 / 39** |
| 4 — T1 says the cell is tradable | 39 / 39 |
| **5 — effective observations ≥ 30 *per pair* and effective pairs ≥ 3** | **33 / 39** |
| 6 — removing the best 10 days does not flip the sign *(the plan's literal rule)* | 20 / 39 |
| **all six** | **0 / 39** |

Two of these differ from the first version, and both are corrections rather than
choices made after seeing the outcome:

* **Condition 5 is per pair.** The plan quantifies its only "30" as "the
  non-overlapping count **per pair**" (§5.2). The code applied it to the count
  pooled over twenty pairs, under which all 39 cells passed and the condition
  **could never have failed**. The ambiguity is my plan's defect, and it had been
  resolved in the direction that produced a survivor. Both readings are computed
  and reported; the registered one governs.
* **Condition 6 is the plan's literal rule** — remove the best 10 days, either
  sign. The code removed the *worst* 10 from a negative total, which is the better
  test but not the registered one. The literal rule passes 20 of 39; the stricter
  variant passes 4. The first version reported 4 as a binding pre-registered
  condition; it is not the pre-registered condition.

### 5.2 The cell that passes under the looser reading

**`F5_extreme:extreme:h192`** — when the 24-hour move is beyond 2σ, fade the
48-hour move and hold 48 hours. It fires on 8.1–8.5% of bars, and it fails
condition 5 as registered: **21.2 and 22.1** non-overlapping entries per pair
against a threshold of 30.

| | 2021–23 (deciding) | 2023–25 (deciding) | 2025 |
| --- | ---: | ---: | ---: |
| gross pips per entry | +5.70 | +11.39 | −2.41 |
| × median round-trip cost | 2.37 | 4.75 | −0.89 |
| rate, pips/pair/active day | +0.229 ± 0.155 | +0.483 ± 0.172 | −0.114 ± 0.281 |
| two-sided `p` vs zero | 0.134 | 0.0064 | 0.744 |
| total pips/pair | +115.0 | +238.4 | −19.1 |
| effective observations **per pair** | **21.2** | **22.1** | 7.0 |
| effective independent pairs | 6.45 | 5.76 | 4.38 |
| JPY / non-JPY | −78 / +198 | +522 / +117 | −75 / +5 |
| total after removing the best 10 days | **+4.6** (of +115.0) | +100.5 | −77.6 |

The two deciding panels do not conflict: the difference is +0.254 ± 0.232,
`z = 1.10`. Inverse-variance pooled, **+0.342 ± 0.115, `z = 2.97`** — both now
computed by `driver._panel_comparison` rather than by hand. The rate is per
**active** day; the pooled series spans 502 + 494 = **996** active days, not the
1,244 the first version wrote.

### 5.3 Three things that dissolve it

**It is indistinguishable from its own complement.** F5's other level — `normal`,
90% of bars — carries the **same sign** in both deciding panels, with a *larger*
total on one: **+459.2 against the survivor's +115.0** on 2021–23, and +185.6
against +238.4 on 2023–25. A state that does not change the sign of the drift has
not stabilised anything; conditioning on "extreme" scaled the per-entry
magnitude, which is mechanical when the conditioning variable *is* the size of
the past move — and is also why condition 3 selects rare cells. **This comparison
is what T2 existed to make, and the first version never made it.**

**The screen fires on noise more than a fifth of the time.** Under a shared block
sign-flip null carrying conditions 1, 2, 3 and 6, with the static conditions 4
and 5 as measured:

```
P(at least one of 39 cells passes all six | null) = 0.2268
mean cells passing = 0.311      0: 3093   1: 684   2: 145   3: 49   4+: 29
```

An independent role computed 0.2135 by a slightly different construction. "One of
39 passed" is the null's ordinary outcome, and a decision rule with a 22%
false-positive rate cannot carry a branch.

**Multiplicity on the right scale leaves it borderline rather than dead.** The
committed `family_wise` maxes the raw net total, and cell null sds here span
**73 to 551** because cells fire on 8% to 50% of bars — so the null maximum
belongs to the frequent cells. Studentized (max-`t`, Westfall–Young):

| family | best cell | `t` | p two-sided | p one-sided |
| --- | --- | ---: | ---: | ---: |
| pooled deciding | **`F5_extreme:extreme:h192`** | 2.98 | **0.060** | 0.035 |
| 2021–23 | `F5_extreme:extreme:h480` | 2.96 | 0.061 | 0.035 |
| 2023–25 | `F5_extreme:extreme:h192` | 2.75 | 0.102 | 0.058 |
| 2025 | `F1_atr:high:h480` | 3.42 | 0.006 | 0.003 |

The first version said "no cell in the family survives a multiplicity-aware test"
and quoted 0.397 / 0.700 / 0.2025. **That was over-scepticism from a mis-specified
statistic** and is withdrawn: on the correct scale the survivor is the family's
best and lands at 0.060 two-sided. The first version's claim was also contradicted
by its own artifact, which recorded `family_wise_p = 0.0215` on the 2025 panel.

### 5.4 The 2025 panel

19 of 39 cells reach `p < 0.05` there against 4 and 2 on the longer panels — more
significant cells on the **shortest** one, 14 of them positive and 9 of those
using the fade convention. That is Round 1's finding that 2025 carried an
unusually strong mean reversion (IC −25% against −5.9% and +2.4%), and it is why
the plan made 2025 corroboration rather than a vote.

## 6. Tail and pair dependence

Reported for every cell. For the cell of §5.2: removing the best 10 days of 502
takes 2021–23 from +115.0 to **+4.6** — 96% of it. The plan's condition only
required the sign to survive, which +4.6 technically does; that is a defect in the
condition, not a property of the cell.

Effective independent pairs run 4.38–6.45, consistent with the 4.6–6.5 this corpus
returns in every round. Twenty pairs are about five markets. The cell's currency
source **flips between the deciding panels** — non-JPY carries it in 2021–23, JPY
in 2023–25.

## 7. Answers to the two questions Round A was asked

**Where does tradable movement exist?** Everywhere, and that is not informative —
a random walk with the same volatility produces more of it. The useful form of the
question is the break-even IC: 1.7% at 5 days, 5.0% at 12 hours, and the
programme's measured |IC| has always exceeded it.

**Does conditioning stabilise the sign?** **No.** Zero of 39 cells pass the
registered screen; the one that passes a looser reading has a complement with the
same sign and four times the total; and the screen itself fires on 22.7% of noise.
Neither ATR state, volatility expansion, higher-timeframe trend, range position
nor recent extremeness explains the sign instability of the previous four rounds.

## 8. The branch: Case B

**Case B — cost-aware / first-passage label redesign. Direction is set aside as
the primary target.**

* **Not A.** Its condition is "T1 has opportunity-rich cells **and** T2 yields at
  least one structural candidate". Under the plan's own reading of condition 5 the
  second conjunct is **zero**, and the first is satisfied only by a classification
  that could not have failed, on a metric the null beats.
* **Not C.** T1 rules it out, for the weaker reason in §4.2.
* **Not D.** D requires that the sample cannot support the structure. The pooled
  deciding estimate is not sample-limited; it is *multiplicity*- and
  *screen*-limited. The first version rejected D with a post-hoc power figure
  computed at the selected effect — which `momentum_inference`'s own docstring
  calls "near useless for reading a null result", and which §5.4 had already
  called biased upward by the screen that chose it. That argument was circular and
  is withdrawn; D is rejected on the corrected grounds above.

**What B means concretely**, from T1's own numbers: stop asking "which way will it
go" as the primary question and start asking "will a move worth more than the cost
occur, and in what geometry". The atlas supplies the design inputs — a time exit
captures about half of a perfect one, the break-even IC is 1.7–5.0% by horizon,
and the adverse excursion paid to reach a favourable move is measured in
`t1_null_benchmark.json`. The next round should pre-register a small set of
first-passage / cost-aware labels and ask whether *any* is more predictable than
the signed return at the same horizon — with a benchmark, a measured screen
false-positive rate and a studentized correction from the start.

**Carried forward, labelled for what it is:** `F5_extreme:extreme:h192` sits at
`p = 0.060` two-sided after the correct multiplicity treatment, fails the
registered sample condition, and has a same-signed complement with four times the
total. It is not a candidate. It is a note.

## 9. What T4 would have been

Kept on the record because the boundary is worth having: one event exactly as
screened, exit geometry pre-registered from T1's quantiles, cost at ×1 to ×3, all
three panels separate, a pre-registered fail condition, no ML, no fresh data. If a
later round revisits the event, that is the shape it must take.

## 10. Artifacts

`python -m scripts.research.round_a.driver` writes every JSON artifact under
`artifacts/track_a_scratch/round_a/` (gitignored, as every previous round's were),
including the five added after review: `t1_null_benchmark`,
`t2_studentized_familymax`, `t2_screen_false_positive_rate`,
`t2_conditional_vs_complement` and `t2_panel_comparison`. **Every number in this
document comes from them** — the first version said so while the pooled estimate,
the panel-difference test and the power arithmetic had no code behind them at all,
which is the Round 2 failure the driver's own docstring cites as its reason for
existing.

## 11. What changed after review, and the defects that produced it

Two independent roles. Both reached Case B; neither was given the other's
conclusions.

**Findings that changed the answer.** T1's headline refuted by its own null
(real ÷ null 0.80–0.92); the screen's false-positive rate measured at 0.2268 for
the first time; condition 5 applied pooled where the plan says per pair, which is
the difference between one candidate and none; the multiplicity statistic
un-studentized, which had made the survivor look dead when it is borderline; and
the survivor never compared with its own complement, which is the comparison T2
existed to make.

**Defects in my pre-registration, recorded rather than used.** §5.6's condition 5
does not define "effective observations" and §5.2's only quantification of 30 is
per pair — the two readings give different answers and the plan does not say
which. §5.6's condition 6 tests only that a sign survives, which +4.6 of +115.0
does. §6 does not make cases A and D mutually exclusive. §4.5's classification
thresholds were set where nothing could reach them.

**Defects in the implementation, all fixed.** `classify` thresholded the median of
the ratio where the plan says the ratio of the medians (119/1, not 118/2); the
atlas emitted 15 unregistered `overall` cells while the document called all 120
"pre-registered" and the ledger said 105; `mae_at_mfe` is not the drawdown paid to
reach the peak; `panels.py` made three false claims about the data boundary, one
refuted by a live reproduction; and the development panel's span was a transcribed
constant because `bars.load`, alone among the three routes, does not validate its
rows.

**Defects I introduced while fixing those.** Renaming the atlas table left the
driver's lookup on the old name, so condition 4 silently failed for all 30 non-F1
cells — a missing key defaulted to `insufficient_data`. And the first
false-positive-rate computation assumed conditions 4 and 5 always pass, measuring
a screen nobody ran. Both are now pinned by tests, and the driver raises rather
than defaulting if the lookup comes back empty.

**Test coverage.** An audit measured the suite at **64%** mutation kill with the
same-bar-leakage mutant surviving outright — the test that named `screen._entries`
never called it. It now kills **23 of 23**, including that mutant, both of my own
bugs above, and every threshold, bin edge, direction rule and window offset.

## 12. Status

* `TRACK_A_RESEARCH_PROGRAM_ROUND_A_COMPLETED`
* `NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
* fresh historical pool `2016-06-02 … 2021-04-25` **untouched**
* `EXPLORATORY_OOS_SLICE`, dead window and forward epoch **not read**
* Formal Confirmation **not performed**; `PRODUCTION_READINESS_NOT_CLAIMED`
* No candidate frozen, no strategy built, no ML trained, no gate created.

Round A stops here. The label-redesign round, T4, ML, fresh reads and Formal
Confirmation are each their own later decision and none is started.
