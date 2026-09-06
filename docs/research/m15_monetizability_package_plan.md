# M15 — Autonomous Package: is the Round B′ structure monetizable?

**`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `PRODUCTION_READINESS_NOT_CLAIMED`.**

**Frozen before the first new statistic was computed.** Base master
`a0858ecba4143037d4137da44ac66cf976b77b8e` (the PR #469 merge). Nothing in this
document may be changed after a result is seen; a deviation forced by a defect is
recorded in the results document as a deviation, never edited into here.

---

## 0. The question

Round B′ established that the M15 price path carries serial structure no matched
null reproduces (`PRICE_PATH_STRUCTURE_SURVIVES_NULL_CONTROL`), and that no
**fixed-horizon linear** rule built from it reaches more than 6–16% of break-even.

This package asks the one question that follows:

> **Is there transaction-cost-clearing economic headroom in that structure at
> all — even for a harvester that cannot be built?**

If the answer is no, the family closes and the programme's price-only phase ends.
If the answer is yes, the package continues to label economics and, only if that
in turn succeeds, to one bounded ML meta-label experiment.

**A positive result is not the objective.** The objective is to kill the family at
the earliest defensible point, or to establish that it cannot yet be killed.

## 1. Authorisation and boundaries

Granted for this package by human + ChatGPT:

* re-use of the three **already-seen** panels — `2021-04-26 … 2023-04-25`,
  `2023-04-26 … 2025-04-24`, `2025-04-25 … 2025-12-28`, `PAIRS_20`;
* **recovery of the tick-count `volume` field** from the raw archive **over those
  same spans only**, and its addition to an M15 research representation.

Not granted, and not to be crossed autonomously — each is a stop-and-refer:

* the fresh pool `2016-06-02 … 2021-04-25`, the historical OOS slice, the dead
  window, the forward epoch;
* Formal Confirmation, broker / demo / live, real order execution, production
  readiness;
* any external data acquisition — macro, carry, calendar, COT, implied vol — and
  any new network access.

**No existing boundary guard may be weakened.** The volume reader **calls the
three existing `_assert_span` guards** rather than re-implementing a bound, so a
weakening would break the routes' own tests. The read span and the measured span
are both recorded.

## 2. Panels and the deciding rule

| panel | span | role |
| --- | --- | --- |
| `momentum_2021_2023` | 2021-04-26 … 2023-04-25 | **deciding** |
| `supplemental_2023_2025` | 2023-04-26 … 2025-04-24 | **deciding** |
| `development_2025` | 2025-04-25 … 2025-12-28 | may contradict, may **not** decide |

About 1,200 configurations were searched over 2025 in earlier rounds. Nothing in
this package may be established on it.

## 3. Cost

The committed `EXPLORATORY_ASSUMPTION`, unchanged: per side,
`(observed spread_close_pips + 0.5) / 2` on mid-based returns, so a round trip
costs one observed spread plus 0.5 pips. Written `C` below; its panel median is
about 2.5 pips. Every economic quantity is reported at `C` and at `2C`.

---

# Stage 1A — clean retrace geometry re-test

## 4. What is measured

The Round B′ detector, unchanged: an anchor fires the first bar at which
`|mid_c[t] − mid_c[a]| ≥ k · σ[a] · √(t − a)`, with `σ` the 480-bar trailing
volatility at the reference bar `a`, never re-estimated inside the window; the
observation window is `min(4 × bars_to_anchor, 480)`.

`k ∈ {1.5, 2.0, 3.0}`. **Three thresholds. No threshold may be added.** No
parameter grid of any kind.

Per anchor:

* **absolute retrace in σ** — the maximum move back toward the reference over the
  window, in σ units of the reference bar;
* **absolute continuation in σ** — the maximum extension away from it;
* **maximum continuation before the retrace** — how far it runs before the 50%
  level is first reached;
* **time-to-retrace** — bars to the 50% level, absent if never reached;
* **timeout** — the fraction reaching no retrace level;
* **same-bar ambiguity** — counted, resolved adversely (the continuation on the
  tie bar counts as preceding the retrace);
* **weekend-gap flag** at the anchor.

## 5. The primary statistic — fixed here

**`median_retrace_sigma`, the median absolute retrace in σ.**

Round B′'s primary was the retrace *fraction*, which divides by the realised
excursion. Real and null anchors do not have the same excursions — real ones form
faster and are smaller — so a difference in the fraction can be a difference in
denominators, and Round B′ measured exactly that: the fraction gave `z` up to
+5.70 while the σ-level version gave `z ≤ +1.96`. **The denominator-bearing
statistic may not be the primary of this round.** The fraction is still computed
and reported, as a secondary.

## 6. The nulls

Each is stated as what it preserves and what it destroys, and each is sanity-
checked on generated data before any real comparison is read.

| null | preserves | destroys | role |
| --- | --- | --- | --- |
| **N2 per-bar sign flip** | `|r_t|` at every bar, each bar's total range, the coupling between a bar's sign and its own shape, the calendar and the gaps | the sign of every return, drawn independently per bar | **primary** — direction with clustering held fixed |
| **N1 iid shuffle** | the return marginal, each bar's own shape | all serial dependence, of the return and of the bar range | secondary — how much of an effect needs clustering |
| **N3 weekday** | each return's weekday and hour slot, and its own shape | order within a slot | calendar / weekly-placement diagnostic |

`_rebuild` swaps a bar's high and low offsets when its sign flips, and permutes a
bar's shape with its own return when the returns are permuted. Round B′ found
that not doing so builds bars that close down with the close pinned to the high,
and that the resulting B′-2 answer had the wrong sign.

**Draws: 200 minimum for every real comparison**, including the bloc splits. Round
B′ used 40 for B′-2 and its family-wise `p` was pinned at the `1/41` floor; that
does not recur.

**The primary result is the difference from the matched null N2.** N1 is a
diagnostic and may not carry a verdict.

## 7. Stage 1A kill condition — all five, on **both** deciding panels

A threshold `k` survives only if, on the σ-level primary:

1. the real-minus-N2 difference has the **same sign** on both deciding panels;
2. `|studentized| ≥ 2` on both;
3. the **family-wise** `p ≤ 0.05` on both, Westfall–Young family-max over the
   whole B′-2-style family at 200 draws;
4. the sign survives removing the **10 largest-contributing anchor days**, applied
   to `real − null` and not to the real side alone;
5. **both** the JPY and the non-JPY bloc carry that same sign.

Additionally reported and weighed: effective independent pair count, tail
concentration, weekend-gap dependence, and the 2025 panel as a contradiction
check only.

**If no threshold survives:**
`RETRACE_GEOMETRY_FAMILY_DROPPED_AFTER_CLEAN_RETEST` — Stop A, and the package
still runs Stage 1B on the **B′-1 variance-ratio structure** and Stage 1C, because
the monetizability question is about the structure rather than about this one
detector.

---

# Stage 1B — the monetizable upper bound

## 8. What an oracle is for

An oracle uses future information and is therefore **not a strategy result**. It
is `UPPER_BOUND_DIAGNOSTIC_ONLY`, and it answers a question no realisable rule
can: *if the structure were exploited perfectly, would there be anything left
after cost?* A family whose **upper bound** is small cannot be rescued by a better
label or a better model, so this is the cheapest possible kill.

## 9. The event population

The Stage 1A anchors at each surviving `k`, and — because Stage 1A may drop the
detector entirely — also a **detector-free** population: every bar, held for
`q ∈ {1, 4, 12, 48}` bars, which is where B′-1's structure lives.

## 10. The three bounds, all net of cost

Entry at the bar **after** the anchor, exit at the window end, mid-based returns,
cost `C` charged as one round trip per trade.

* **B-1 perfect take / skip.** The side is fixed by the structure — counter to the
  excursion, which is the direction B′-1 and B′-2 both point — and the oracle
  chooses only *whether to trade*, with perfect foresight. This bounds **every**
  selection model, ML meta-labelling included, on that entry rule.
* **B-2 perfect side.** The oracle chooses long or short with perfect foresight.
  This bounds every direction model.
* **B-0 take-all baseline.** The structural side on every event, no selection.
  What a simple rule actually gets, for the gap in §14 condition 4.

Reported per panel, at `C` and at `2C`: event frequency per pair per year, gross,
net, net per event, net per **taken** event, turnover, maximum drawdown, and the
share of net contributed by the top 10 days.

## 11. The economic gate — fixed here, before any oracle is run

All four must hold on **both** deciding panels, for at least one event population:

* **E1** the perfect take/skip net, divided by the **total** number of events
  (skipped ones included), is at least **0.5 × C**. An oracle that cannot earn
  half a spread per opportunity leaves nothing for a rule that must guess;
* **E2** the perfect take/skip net remains positive at **`2C`**;
* **E3** the top 10 days contribute **less than 50%** of that net;
* **E4** the JPY and non-JPY blocs both have positive oracle net.

**If E1–E4 hold** for some population → `PATH_STRUCTURE_HAS_ECONOMIC_HEADROOM`,
and §14 decides whether Stage 2 begins.

**If they do not** → `PATH_STRUCTURE_STATISTICALLY_REAL_BUT_ECONOMICALLY_TOO_SMALL`
— Stop B. No label search, no ML, no exit optimisation is run on that family, and
the package does not look for a different oracle that would pass.

---

# Stage 1C — tick volume information

## 12. The read

`volume` recovered from the raw archive over the three already-seen spans only,
through the routes' own `_assert_span` guards. Aggregated to the committed M15
grid as the **sum** of the constituent M1 tick counts, into its own cache, so no
existing artifact is rewritten.

Recorded: the span requested, the span measured, rows read, and the guard that
admitted each span.

## 13. What is measured

Coverage and missingness per pair; the share of M15 bars with `volume = 0`;
per-pair medians; session dependence. Then, per pair, the Spearman correlation of
`log(1 + volume)` with `|r_t|`, the 480-bar realised volatility, ATR and the
observed spread, and the persistence of a volume shock (lag-1 to lag-8
autocorrelation of the pair-local volume z-score).

Permitted representations, and no others: `log(1 + volume)`, a pair-local
z-score, and a rolling percentile. No search over transformations.

## 14. The volume gate — fixed here

Per pair, regress `log(1 + volume)` on `{log realised volatility, log spread,
|r_t|, session}` and take the **median `R²`** across pairs. Then measure whether
the residual carries any relation to a forward quantity — next-bar `|r|` and
next-bar signed return — as a studentized rank correlation against the same N2
null.

* **redundant** if the median `R² ≥ 0.80` **and** no forward relation reaches
  `|z| ≥ 2` on both deciding panels → `TICK_VOLUME_INFORMATION_REDUNDANT`, dropped
  as a feature candidate;
* **distinct** otherwise → `TICK_VOLUME_INFORMATION_INCREMENTALLY_DISTINCT`, kept
  as a Stage 3 feature candidate **only**. It does not become a strategy here.

---

# Stage 2 — bounded label / event economics

## 15. Entry conditions — all three

* **A** a clean path/retrace structure survives Stage 1A on both deciding panels,
  **or** B′-1's variance-ratio structure supplies the event population;
* **B** the Stage 1B economic gate E1–E4 passes;
* **C** the effect is not carried by one pair, one bloc, or a handful of days —
  Stage 1A clauses 4 and 5, and E3 and E4.

If any fails materially, Stage 2 is not begun and the package stops.

## 16. Label families — at most three, derived, not searched

Every barrier distance is derived from Stage 1 geometry **measured on the null**
or from cost geometry, never fitted to the real effect, and **no TP × SL grid is
run**.

* **L-A σ-normalised retrace target.** Enter counter to the excursion at the
  anchor. Take profit at the **null's** median absolute retrace in σ; stop at the
  **null's** median adverse extension in σ. Both are process-neutral quantities.
* **L-B first-passage barrier.** Symmetric barriers at the distance at which the
  expected gross equals `3 × C`, computed from the panel's σ. One distance, fixed.
* **L-C cost-adjusted trade / no-trade.** Outcome is the net over a fixed horizon
  equal to Stage 1A's median time-to-retrace; the label is `net > 0`.

## 17. Baselines and evaluation

No ML at this stage. Compared against take-all, the fixed structural rule, and a
no-condition baseline. Reported: gross, cost, net, expectancy per trade, turnover,
maximum drawdown, panel consistency, JPY / non-JPY, tail concentration, and `2C`.

## 18. Stage 2 kill rule

A family is dropped if **any** holds: gross negative; net negative after `C`;
sign reversal between the deciding panels; tail-only; JPY-only; or a simple rule
recovers essentially none of the Stage 1B headroom. **Thresholds are not adjusted
to make a family pass.** If all three families drop:
`PATH_STRUCTURE_HAS_ECONOMIC_HEADROOM_BUT_SIMPLE_HARVESTER_FAILED` — Stop C.

---

# Stage 3 — one bounded ML meta-label experiment

## 19. Entry conditions — all five

1. the simple event population is **gross positive**;
2. it is positive, or close to positive, after realistic cost;
3. the economics point the **same way** on both deciding panels;
4. the take-all baseline leaves visible room to select — the Stage 1B perfect
   take/skip bound exceeds take-all by a clear margin;
5. events per feature is sufficient — **at least 50 events per feature** in the
   smallest training fold.

If the base signal has no edge, **no ML is run**:
`SIMPLE_EVENT_ECONOMICS_ESTABLISHED_ML_NOT_JUSTIFIED` or the relevant stop.

## 20. Design — fixed here

One experiment, run once.

* **Models:** a simple linear model (regularised logistic) **and** LightGBM.
  LightGBM alone is forbidden.
* **Features: at most 20**, from these groups only — path geometry, volatility,
  HTF context, location / range, spread, and tick volume *only if* Stage 1C
  returned `INCREMENTALLY_DISTINCT`. No indicator zoo, no EMA/RSI family.
* **Hyperparameters: fixed, minimal, declared in code.** No search.
* **Label:** a cost-aware meta-label on the Stage 2 trade population —
  `net outcome > 0`. Not a return to all-bar direction prediction.
* **Evaluation:** purged chronological walk-forward with an embargo equal to the
  observation window; against take-all and against the linear baseline; cost
  included; feature-group ablation; panel stability; tail robustness.

**If ML does not beat the simple baseline substantially:**
`ML_META_LABEL_NO_INCREMENTAL_VALUE` — Stop E, and the model is not made more
complex.

## 21. Higher timeframes

H4 / D1 are **not** re-explored as direction signals. They may appear in Stage 2
or Stage 3 only as a small number of **geometry / event context** features, and
are dropped unless they add value over an HTF-free baseline.

## 22. Monthly TSMOM

Not re-explored in this package.

---

# 23. Stop logic

The package may stop autonomously at any of these, and stopping early is
preferred to continuing.

| stop | condition | status |
| --- | --- | --- |
| **A** | clean geometry does not reproduce | `PRICE_PATH_STRUCTURE_NOT_REPRODUCED_CLEANLY` |
| **B** | structure real, upper bound small | `PRICE_PATH_STRUCTURE_REAL_BUT_NOT_ECONOMICALLY_HARVESTABLE` |
| **C** | headroom exists, simple harvester fails | `PATH_STRUCTURE_HAS_ECONOMIC_HEADROOM_BUT_SIMPLE_HARVESTER_FAILED` |
| **D** | ML prerequisites unmet | `SIMPLE_EVENT_ECONOMICS_ESTABLISHED_ML_NOT_JUSTIFIED` |
| **E** | ML adds nothing | `ML_META_LABEL_NO_INCREMENTAL_VALUE` |
| **F** | a candidate stands | `EXPLORATORY_CANDIDATE_READY_FOR_POWERED_FRESH_REPLICATION_DECISION` |

Stop F is a **referral**, not a licence: fresh replication, external data and
Formal Confirmation each need an explicit human + ChatGPT instruction.

# 24. What may not change after a result is seen

The primary statistic (§5), the nulls and their draw count (§6), the Stage 1A kill
condition (§7), the oracle definitions (§10), the economic gate (§11), the volume
gate (§14), the label families and their derived distances (§16), the Stage 2 kill
rule (§18), the Stage 3 entry conditions and design (§19–§20), and the stop
logic (§23).

A defect found in an implementation is fixed and **recorded as a deviation** in
the results document, with the before-and-after measurement. A threshold is never
moved to change an outcome.
