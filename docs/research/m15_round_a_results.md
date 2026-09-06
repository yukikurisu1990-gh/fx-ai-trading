# M15 Research Program — Round A: results

**`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `PRODUCTION_READINESS_NOT_CLAIMED`.**

Plan: `docs/research/m15_round_a_plan.md`, committed at `e7d53b2` **before any
cell was computed**. Base master `b274762` (the PR #467 merge).

**Next branch: Case A — T4 Event Economics**, on one event, bounded as §9
describes. Not because the evidence is strong; because the pre-registered
condition for A is met and the condition for the alternatives is not. §8 states
the case against it in full.

`TRACK_A_RESEARCH_PROGRAM_ROUND_A_COMPLETED`.

---

## 1. The two findings

**T1 — the opportunity is abundant, and it always was.** At a 48-hour horizon the
median best-direction excursion is **72.8–88.6 pips against a median round-trip
cost of 2.4–2.8 pips**: a ratio of 24.4 to 34.6. Of 120 pre-registered cells, **118 are
opportunity-rich, 2 are marginal and none is structurally unattractive**. The two
marginal cells are the 4-hour rollover window, where cost doubles.

This reframes four rounds of failure. Round 1 concluded that turnover killed
everything, and it did — but *not* because M15 FX fails to move enough to pay a
spread. At 48 hours a strategy needs to capture about **4% of the median
available excursion** to break even. **The binding constraint is prediction, not
opportunity.** `Case C` — exit for lack of tradable movement — is decisively
ruled out.

**T2 — conditioning on these five state families did not stabilise the sign.**
Of 39 pre-registered cells, exactly **one** passes the six-condition structural
screen. And no cell in the family survives a multiplicity-aware test: the
family-max correction gives `p = 0.397` and `p = 0.700` on the two deciding
panels separately, and **`p = 0.2025` on the two pooled**. The binding screen
conditions were effect size against cost (**4 of 39**) and tail robustness
(**4 of 39**) — not sign agreement, which 29 of 39 cells achieved.

## 2. Identity

| | |
| --- | --- |
| PR #467 | merged, merge commit **`b274762e4335f4f0fee7dc7b2ae93558e2db28b6`** |
| verified before merge | head `ab640df` matched, CI green (contract-tests + test), `MERGEABLE`/`CLEAN`, no unresolved review comment |
| Round A plan | `e7d53b2`, committed before any cell was computed |
| panels | `2021-04-26…2023-04-25` (624 trading days), `2023-04-26…2025-04-24` (624), `2025-04-25…2025-12-28` (212) |
| pairs | `PAIRS_20`, all twenty |
| bars | 999,238 + 993,878 + 335,200 |
| **new market-data reads** | **zero** |
| fresh pool `2016-06-02…2021-04-25` | **untouched** |

Round A's package contains no reader, no archive path and no span bound, so
"performs no read" is a property of the code rather than a promise in a document.
Nothing under `scripts/m15_track_a/` was touched.

## 3. T0 — the infrastructure

**Reused unchanged:** `engine.atr_pips` / `zscore` / `donchian` /
`higher_timeframe`, `familywise.family_wise` (family-max, shared sign draw),
`momentum_inference.interval` (block bootstrap, CI, two-sided `p`), and
`round2`'s constants — `Z_WINDOW = 480`, `ATR_PERIOD = 14`,
`ATR_RANK_WINDOW = 960`, `N_PHASES = 8`. The ATR state here is therefore the
same object the reversal and momentum rounds conditioned on.

**New, and small:**

* **The hypothesis ledger** (`round_a/ledger.py`) — nine entries covering every
  family run against the seen panels since Round 1. It records that roughly
  **1,200 configurations** have been evaluated against the 2025 window, which is
  why the plan forbids 2025 from being a deciding vote. It is a record, not a
  gate: nothing checks it and nothing fails because of it.
* **The standard diagnostic block** (`round_a/panels.py`) — pips per pair per
  day, effective independent pairs by the correlation estimator, JPY / non-JPY,
  and both tails at 1/3/5/10/20 days. Assembled from the functions above.

## 4. T1 — the Tradability Atlas

### 4.1 Horizon is the whole story

Median over all pairs, unconditioned, per period:

| H | period | median MFE | median cost | **MFE ÷ cost** | median \|move\| | \|move\| ÷ cost | P(MFE > 3×cost) | median adverse at MFE>2×cost |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 16 (4h) | 2021–23 | 22.7 | 2.4 | 8.8 | 11.7 | 4.4 | 0.92 | 6.2 |
|  | 2023–25 | 20.1 | 2.4 | 7.9 | 10.3 | 4.0 | 0.91 | 5.4 |
|  | 2025 | 19.0 | 2.8 | 6.4 | 9.7 | 3.3 | 0.87 | 5.2 |
| 48 (12h) | 2021–23 | 41.9 | 2.4 | 16.2 | 22.6 | 8.6 | 0.98 | 11.2 |
|  | 2023–25 | 37.3 | 2.4 | 14.8 | 19.9 | 7.8 | 0.98 | 9.8 |
|  | 2025 | 34.9 | 2.8 | 11.7 | 18.1 | 6.1 | 0.97 | 9.1 |
| 96 (24h) | 2021–23 | 62.0 | 2.4 | 24.1 | 34.1 | 13.0 | 0.99 | 16.4 |
|  | 2023–25 | 55.1 | 2.4 | 21.9 | 29.9 | 11.7 | 0.99 | 14.2 |
|  | 2025 | 50.6 | 2.8 | 17.1 | 27.1 | 9.2 | 0.99 | 13.2 |
| 192 (48h) | 2021–23 | 88.6 | 2.4 | 34.6 | 49.2 | 18.6 | 1.00 | 23.4 |
|  | 2023–25 | 79.3 | 2.4 | 31.6 | 43.6 | 17.1 | 1.00 | 20.2 |
|  | 2025 | 72.8 | 2.8 | 24.4 | 39.0 | 13.2 | 0.99 | 18.9 |
| 480 (5d) | 2021–23 | 140.2 | 2.4 | 55.0 | 75.8 | 28.8 | 1.00 | 37.5 |
|  | 2023–25 | 126.1 | 2.4 | 50.7 | 69.7 | 27.4 | 1.00 | 32.4 |
|  | 2025 | 115.8 | 2.8 | 39.0 | 60.5 | 20.6 | 1.00 | 30.4 |

The ordering is monotone in horizon and stable across all three periods. Nothing
here is close to the cost line except the 4-hour rollover window.

### 4.2 The state dimensions barely matter

* **ATR tercile** — at h192 the MFE/cost ratio runs 23.4 (low, 2025) to 37.5
  (high, 2021–23). Monotone in the expected direction and **small**: high ATR
  raises both the excursion and, slightly, nothing else — cost is essentially
  flat across terciles (2.3 vs 2.5 pips). This is the arithmetic behind Round 2's
  ATR-high effect, and the atlas shows the effect is a 15% shift in a ratio that
  is already 25×, not a difference between tradable and untradable.
* **Session** — asia / europe / us are within 3% of each other at h192
  (ratios 35.2 / 36.9 / 32.5 on the 2021–23 panel). **Rollover is the one real
  cost feature**: median cost 4.6–6.0 pips against 2.3–2.9 elsewhere, halving the
  ratio. This confirms Round 1's finding that there is no cheap session to route
  into, and identifies the one window worth excluding.
* **Blocs** — JPY carries a higher ratio than non-JPY at every horizon
  (30.9–42.1 vs 22.3–32.9 at h192), driven by larger excursions rather than
  cheaper quotes.

### 4.3 What this implies for label design

The atlas was built to inform labels, and three numbers do:

1. **A time-exit captures about half of a perfect exit.** Median |terminal move|
   is 0.535–0.555× median MFE at h192 and 0.522–0.553× at h480, so the ratio is
   about 0.54 in every period at both horizons. A label defined as "the return
   at horizon" therefore throws away roughly half the movement a first-passage
   label could address.
2. **A realistic take-profit is 2–3× cost, not 10×.** At h192, `P(MFE > 2×cost)`
   is 0.999 but the median MFE is 24–35× cost; the useful design question is where
   between those a TP stops being reachable, and the quantile table in
   `t1_atlas_cells.json` answers it per cell.
3. **The adverse excursion paid to reach a 2×cost favourable move is 18.9–23.4
   pips at h192** — about 8× the cost, and about a quarter of the favourable
   excursion. Any TP/SL geometry has to survive that; a stop tighter than roughly
   8× cost would be hit routinely on paths that eventually work.

**The prohibition stands.** MFE and MAE are computed from future bars on purpose,
as an upper bound. They are recorded in the plan (§4.5) and in `atlas.py` as
tradability and label-design diagnostics that may never become a feature, a
filter, a conditioning variable or an entry rule. Nothing in Round A returns a
position.

## 5. T2 — the Conditional Sign Screen

### 5.1 What was screened

39 cells: five marginal condition families (13 levels) × three horizons, with the
context direction fixed per family before the run. All 39 were computed on all
three panels; nothing was added, dropped or re-binned.

### 5.2 The six conditions, and which ones bind

| condition | cells passing |
| --- | ---: |
| 1 — the two 730-day panels agree in sign | **29 / 39** |
| 2 — 2025 is not strong counter-evidence | 22 / 39 |
| 3 — \|effect\| ≥ 2 × median round-trip cost in both | **4 / 39** |
| 4 — T1 says the cell is tradable | 39 / 39 |
| 5 — effective observations ≥ 30 and effective pairs ≥ 3 | 39 / 39 |
| 6 — removing the best 10 days does not flip the sign | **4 / 39** |
| **all six** | **1 / 39** |

**Sign agreement is not the scarce thing — 29 of 39 cells achieve it.** That is
above the ~19.5 a coin-flip would give, but the 39 cells are heavily nested (five
families partitioning the same bars, three horizons of the same series), so they
are nothing like 39 independent trials and the excess is not evidence. What is
scarce is **magnitude against cost** and **tail robustness**, and they are scarce
in the same way: most conditional drifts are small relative to a 2.4-pip round
trip, and what magnitude exists sits in a handful of days.

### 5.3 The one survivor

**`F5_extreme:extreme:h192`** — when the 24-hour move is beyond 2σ of its own
480-bar distribution, fade the 48-hour move and hold 48 hours. It fires on 8.1–8.5%
of bars.

| | 2021–23 (deciding) | 2023–25 (deciding) | 2025 (corroboration) |
| --- | ---: | ---: | ---: |
| gross pips per entry | **+5.70** | **+11.39** | **−2.41** |
| × median round-trip cost | 2.37 | 4.75 | −0.89 |
| rate, pips/pair/day | +0.229 ± 0.155 | +0.483 ± 0.172 | −0.114 ± 0.281 |
| **two-sided `p` vs zero** | **0.134** | **0.0064** | 0.744 |
| CI95 on the total | [−38.1, +265.8] | [+72.1, +401.6] | [−123.6, +58.8] |
| total pips/pair | +115.0 | +238.4 | −19.1 |
| pairs net-positive | 14/20 | 13/20 | 8/20 |
| effective independent pairs | 6.45 | 5.76 | 4.38 |
| **JPY / non-JPY** | **−78 / +198** | **+522 / +117** | −75 / +5 |
| **total after removing the best 10 days** | **+4.6** (of +115.0) | +100.5 (of +238.4) | −77.6 |

The two deciding panels **are consistent with each other** — the difference in
rate is +0.254 ± 0.232, `z = +1.10`, `p = 0.274`, so this is not a magnitude
conflict. Pooled by inverse variance over the 1,244 deciding days:
**+0.342 ± 0.115 pips/pair/day, `z = 2.97`, `p = 0.0030`**; the pooled
block-bootstrap on the concatenated series gives **+0.355 ± 0.116, `p = 0.0020`,
CI95 [+131, +586] pips/pair**.

### 5.4 And no cell survives multiplicity

| correction | best cell | family-wise `p` |
| --- | --- | ---: |
| 2021–23 alone, 39 cells | — | **0.397** |
| 2023–25 alone, 39 cells | — | **0.700** |
| **the two pooled, 39 cells, 1,244 days** | `F2_vol:expansion:h192`, net 965.6 | **0.2025** (null max p95 = 1282.7) |

Four of 39 cells reach `p < 0.05` on the pooled panels uncorrected — against
about 2 expected from 39 independent tests, which for 39 *correlated* tests is
unremarkable. Bonferroni over 39 needs `p < 0.00128`; the survivor is at 0.0020.

**Two further reasons the survivor's evidence is weaker than `p = 0.002` sounds.**

* **The screen selects on the quantity being tested.** Conditions 1 and 3 filter
  on sign agreement and on effect size, so the surviving cell's effect is biased
  upward by construction. The pooled `p` is optimistic before multiplicity is
  even considered.
* **The survivor is not the family's best by total.** `F2_vol:expansion:h192`
  has pooled net 965.6 against the survivor's 353.3, and failed the screen only
  because its per-entry effect is 1.62× cost in one panel, under the 2.0
  threshold. Condition 3 measures per-entry economics and so prefers rare
  high-conviction events over frequent thin ones; that is a defensible choice
  fixed in advance, but it means "the one that survived" and "the strongest one"
  are different cells.

### 5.5 The 2025 panel, and why it was kept out of the vote

19 of 39 cells reach `p < 0.05` on the 2025 panel, against 4 and 2 on the two
longer ones — more significant cells on the **shortest** panel. Of those 19, 14
have positive drift and 9 of those use the fade convention. That is exactly Round
1's finding that the 2025 window carried an unusually strong mean reversion
(IC −25% against −5.9% and +2.4% elsewhere), so it is a property of the period
rather than a defect in this screen — and it is precisely why the plan made 2025
corroboration rather than a vote.

## 6. Tail dependence and pair dependence

Both are reported for every cell in `t2_screen_cells.json`. For the survivor:
removing the best 10 days of 502 takes the 2021–23 total from **+115.0 to +4.6**
— 96% of it. The sign does not flip, which is all condition 6 required, and in
retrospect that condition was too weak: a threshold on *sign* cannot distinguish
"robust" from "one pip from zero". This is the same concentration the reversal
round showed (97% in 10 of 212 days) and it is stated rather than trimmed away.
Removal is a diagnostic; it enters no rule.

Effective independent pairs run 4.38–6.45 across the survivor's panels,
consistent with the 4.6–6.5 this corpus has returned in every round. Twenty pairs
are about five markets, and the per-cell counts are reported on that basis.

The survivor's currency source **flips between the deciding panels** — non-JPY
carries it in 2021–23 (+198 against JPY's −78) and JPY carries it in 2023–25
(+522 against non-JPY's +117). Two panels agreeing in sign while disagreeing
about which currencies produce it is weak evidence for one mechanism.

## 7. Answers to the two questions Round A was asked

**Where does tradable movement exist?** Almost everywhere, at every horizon from
4 hours upward, in every ATR state and every session except rollover, in all
three periods. The cost line is not the constraint at any horizon at or above 12
hours.

**Does conditioning stabilise the sign?** Not in these five families. One cell of
39 passes a six-condition screen; no cell clears multiplicity on either deciding
panel or on the two pooled; the strongest per-entry effects are rare-event cells
whose totals are carried by a handful of days. The unconditional-direction
failure of the previous four rounds is **not** explained by a missing state
variable among ATR, volatility expansion, higher-timeframe trend, range position
or recent extremeness.

## 8. The classification, and the case against it

**Case A — T4 Event Economics.**

The pre-registered condition (§6 of the plan) is: T1 has opportunity-rich cells
**and** T2 yields at least one structural candidate. Both hold. The alternatives
do not: **C** is ruled out by T1; **B** requires *zero* candidates and one
passed, so choosing B would be discarding a survivor after seeing that it is
weak — the exact post-hoc rule change every audit in this programme has caught;
**D** requires that the sample cannot support the structure, and that is not what
the numbers say — the pooled deciding estimate is adequately powered
(80% power needs 0.89× the span already in hand; the 2021–23 panel alone would
need 3.57×, about 1,606 more days).

**Two defects in my own pre-registration, stated rather than used.** §6 does not
make A and D mutually exclusive, so a reader could reach either; I am following
A because its stated condition is met and D's is not, not because A is the
outcome I prefer. And condition 6 tested only that a sign survives trimming, which
+4.6 from +115.0 technically does.

**The case against A, in full.** No cell in the family clears multiplicity
(0.397 / 0.700 / 0.2025). The survivor's own pooled `p = 0.002` is uncorrected,
sits above the Bonferroni line for 39 cells, and is biased upward by the screen
that selected it. 96% of one deciding panel's total is in 10 days of 502. The
currency source flips between panels. The third period is negative. A reader who
weighted multiplicity above the letter of the pre-registration would classify
this **D**, and that reading is defensible on the numbers in §5.4 — it is
recorded here so the choice is visible rather than buried.

## 9. What T4 may and may not be

Recorded now, so the next round cannot become the fifth optimisation cycle:

* **One event**, the survivor, defined exactly as screened. No neighbourhood, no
  parameter grid, no alternative thresholds.
* **Exit geometry from T1's own quantiles**, pre-registered before running —
  at most three candidate exits, chosen from the atlas and not from performance.
* **Cost charged** at the unchanged `EXPLORATORY_ASSUMPTION`, reported at ×1 to ×3.
* **All three panels reported separately**, 2025 still corroboration.
* **A pre-registered fail condition**: if net economics are not positive in both
  deciding panels at ×1 cost, or if the best-10-day trimmed net turns negative in
  either, the event is dropped and the branch moves to **B** — cost-aware /
  first-passage label redesign, which T1 §4.3 has already prepared.
* **No ML.** ML remains gated behind an event population with demonstrated gross
  economics, which is what T4 exists to establish or refute.
* **No fresh data.** The fresh pool stays reserved for a powered internal
  replication of whatever survives T4.

## 10. Artifacts, and how to regenerate them

`python -m scripts.research.round_a.driver` writes all nine JSON artifacts under
`artifacts/track_a_scratch/round_a/` (gitignored, as every previous round's
were): `round_a_panels`, `t1_atlas_cells`, `t1_atlas_verdicts`,
`t2_screen_cells`, `t2_structural_candidates`, `t2_familywise`,
`t2_pooled_deciding_panels`, `t2_unconditional_reference`, `hypothesis_ledger`,
`round_a_summary`. Every number in this document comes from them.

**Two defects in the driver were found and fixed while running it**, both by
opening the artifacts rather than trusting the code: the plan requires a
block-bootstrap CI and a two-sided `p` on every cell and the first version
computed neither; the second version computed them but wrote `t2_screen_cells`
**before** the loop that adds them, so the field was absent from the artifact
again. A third defect was found before any cell was computed: `d1_state` was
populated on 173 of 16,760 bars because `higher_timeframe` already broadcasts
its value to every bar, so `.diff()` was comparing adjacent bars rather than
adjacent 96-bar blocks.

## 11. Status

* `TRACK_A_RESEARCH_PROGRAM_ROUND_A_COMPLETED`
* `NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
* fresh historical pool `2016-06-02 … 2021-04-25` **untouched**
* `EXPLORATORY_OOS_SLICE`, dead window and forward epoch **not read**
* Formal Confirmation **not performed**; `PRODUCTION_READINESS_NOT_CLAIMED`
* No candidate frozen, no strategy built, no ML trained, no gate created.

Round A stops here. T4, label redesign, ML, fresh reads and Formal Confirmation
are each their own later decision and none is started.
