# M15 — Autonomous Package: is the Round B′ structure monetizable?

**`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `PRODUCTION_READINESS_NOT_CLAIMED`.**

Plan: `docs/research/m15_monetizability_package_plan.md`, frozen at `40cbcd9`
**before the first statistic of this package was computed**, amended once at
`cbbe7f4` — before the first **real** statistic — because the economic gate as
frozen was passed by pure noise. Base master
`a0858ecba4143037d4137da44ac66cf976b77b8e` (the PR #469 merge).

**Final classification: B —
`PRICE_PATH_STRUCTURE_REAL_BUT_NOT_ECONOMICALLY_HARVESTABLE`.**

Stage 2 was **not begun**: its entry condition B failed, and the plan's stop
logic prefers killing a family early to continuing.

---

## 1. The answer

**The price-only phase closes.** Three findings, each on its own evidence.

* **Round B′-2's retrace positive was a denominator effect.** Re-tested with the
  σ-level absolute retrace as the primary and 200 null draws instead of 40,
  **no threshold reaches `|z| ≥ 2` on any panel** — the largest is `+1.50`. The
  same anchors, the same null and the same draws give the *fraction* `z` between
  `+3.25` and `+5.05` on the deciding panels. Dividing by an excursion the
  detector does not select identically on both sides was the whole effect.
* **There is no economic headroom, and the check that says so is not a
  strategy.** For every event population, the best **in-sample linear selector on
  past-only features**, minus what the same selector extracts from a matched
  null, is between `−0.02` and `+0.01` round trips per opportunity. The floor
  was `0.50`. One population clears it on the point estimate — a `3σ` excursion
  anchor, 5–7 events per pair per year — and fails the tail clause with a top-ten-
  day share of `1.00`, its excess sitting within one standard deviation of its
  own null.
* **Tick volume is not redundant, and it is not about direction.** Its residual —
  after realised volatility, spread, the current move and the session — has a
  Spearman of **`+0.124` and `+0.148`** with the **next bar's absolute** return,
  the same sign on **20 of 20 pairs** on both deciding panels. Against the next
  bar's **signed** return it is `−0.0014` and `+0.0013`, 12 and 13 pairs of 20.
  It is a volatility variable that the programme did not already have, and it
  says nothing about which way the price goes.

The structure Round B′ found is real. It is not tradable, and the reason is not
that the right label has not been tried — an oracle that selects perfectly among
the entries it is given cannot pay for the spread either.

## 2. Identity

| | |
| --- | --- |
| PR #469 | merged, merge commit **`a0858ecba4143037d4137da44ac66cf976b77b8e`** |
| verified before merge | head `850fb40` matched, CI green, `MERGEABLE`/`CLEAN`, no unresolved review comment |
| package plan | `40cbcd9`, before any statistic of this package; amendment A-1 at `cbbe7f4`, before any **real** statistic |
| panels | `2021-04-26…2023-04-25` (624 days) · `2023-04-26…2025-04-24` (624) · `2025-04-25…2025-12-28` (212) |
| declared vs measured span | identical on all three, for prices **and** for the recovered volume |
| pairs / bars | `PAIRS_20` · 999,238 + 993,878 + 335,200 |
| new market-data spans read | **none** |
| tick volume | recovered over **those same three spans only**, 2,328,316 M15 bars, bar-for-bar identical to the price panels |
| fresh pool `2016-06-02…2021-04-25` | **untouched** |

## 3. Amendment A-1 — the frozen gate was passed by noise

Made on generated data, before any panel was touched, and it made the gate
**harder**. `oracle.noise_reference` runs the bounds on a pure IID random walk
with the panels' own 2.5 pip round trip:

| bound, net per event | `q = 1` | `q = 4` | `q = 12` | `q = 48` |
| --- | ---: | ---: | ---: | ---: |
| B-0 take-all | −2.498 | −2.504 | −2.506 | −2.627 |
| **B-1 perfect take / skip** | +0.002 | +0.103 | +0.477 | **+1.672 (+0.67 × C)** |
| B-2 perfect side | −1.703 | −0.903 | +0.266 | +3.067 |
| **B-3 achievable selection** | **0.0000** | **0.0000** | **0.0000** | **−0.0007** |

The frozen E1 floor is `0.50 × C`, and **B-1 clears it on pure noise**. The
reason is arithmetic: `E[max(net, 0)]` over a roughly symmetric distribution is
about `0.4 · σ_q` whatever produced it, and `σ_q` grows as `√q`. A gate read off
perfect foresight cannot reject anything.

B-3 returns zero on the same data — but zero is also what a broken selector
returns, so it is checked against a structure that is really there. On an
**Ornstein–Uhlenbeck level** (the price reverts, half-life about 69 bars) with a
0.2 pip round trip:

| bound | `q = 1` | `q = 12` | `q = 48` |
| --- | ---: | ---: | ---: |
| B-0 take-all | −0.193 | −0.027 | **+0.804 (+4.0 × C)** |
| **B-3** | 0.0000 | +0.073 (+0.4 × C) | **+0.929 (+4.6 × C)**, about 433 of 614 taken |

An AR(1) on **returns** with `φ = −0.30` was tried as the control first and is
the wrong one: a single lag-1 term largely cancels inside a `q`-bar block, so
fading blocks does not pay under it and take-all stays negative. It would have
let an inert selector look correct.

So B-1 and B-2 became `DESCRIPTIVE_ONLY` and **E1 became E1′**: B-3's net per
event **minus the same computation on the matched N2 null**, at the same `0.5 × C`
floor. The floor was not moved; only the quantity it applies to changed, from one
noise passes to one noise fails.

## 4. Stage 1A — the clean retrace geometry re-test

### 4.1 Null sanity, and what it says about the primary's scale

First, on a panel-shaped generated walk — 20 series, 50,000 bars, no structure of
any kind. Every difference must sit inside its band:

| `k` | anchors | **σ-level diff** | `z` | trimmed `z` | fraction diff | `z` |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1.5 | 4,120 | +0.1095 | +1.07 | +0.86 | +0.0165 | +1.22 |
| 2.0 | 881 | +0.5571 | +1.74 | +1.42 | +0.0182 | +0.78 |
| 3.0 | 62 | +0.5430 | +0.34 | +0.33 | −0.0420 | −0.81 |

They do — but **this is the most informative table in the section**, and not
because it passes. A pure random walk produces σ-level differences of `+0.11`,
`+0.56` and `+0.54`. The real deciding panels produce `+0.05` to `+1.12`. The
detector-plus-null machinery generates differences of the same order on data with
nothing in it, because the detector does not select the same anchors on the two
sides and a median over a few hundred selected events is a small-sample
statistic. Whatever the panels show, it is not larger than the noise floor of the
instrument measuring it.

**A draw-count fact worth recording.** At 40 draws the same walk gave `k = 2.0` a
`z` of `+2.27` — above the clause-2 floor, on data with no structure. At 200 it
is `+1.74`. The plan required 200 for exactly this reason and Round B′ ran B′-2
at 40; had this round inherited that, a generated random walk would have cleared
its own significance clause.

### 4.2 The panels

**The primary is `median_retrace_sigma`.** Real minus the matched N2 null, 200
draws:

| panel | `k` | anchors | **primary, σ-level** | `z` | day-trimmed `z` | *secondary: fraction* `z` |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2021–23 | 1.5 | 5,081 | +0.0511 | **+0.74** | +0.03 | *+4.06* |
| 2021–23 | 2.0 | 1,409 | +0.1399 | **+0.70** | −0.11 | *+3.41* |
| 2021–23 | 3.0 | 201 | +1.1176 | **+1.50** | +1.32 | *+3.40* |
| 2023–25 | 1.5 | 5,511 | +0.0890 | **+1.19** | +0.61 | *+3.25* |
| 2023–25 | 2.0 | 1,826 | +0.1966 | **+1.40** | +0.47 | *+5.05* |
| 2023–25 | 3.0 | 350 | +0.6424 | **+1.18** | −0.91 | *+4.16* |
| 2025 | 1.5 | 1,230 | +0.0300 | +0.22 | +0.53 | *+1.66* |
| 2025 | 2.0 | 357 | +0.2256 | +0.63 | +0.29 | *+2.48* |
| 2025 | 3.0 | 59 | +0.0624 | +0.09 | −0.02 | *+1.85* |

**Every difference is positive and none is significant.** Clause 2 fails at all
three thresholds on both deciding panels; clause 4 also fails at `k = 2.0` and
`k = 3.0`, and clause 5 at `k = 3.0`.

`RETRACE_GEOMETRY_FAMILY_DROPPED_AFTER_CLEAN_RETEST`.

### 4.3 One clause needs reading carefully

 Clause 3 — the family-wise `p` — *passes*
at `0.005`, `0.005` and `0.015–0.040`. It is computed, as the plan specifies, as
a family-max over the **whole** family of statistics, and that family contains the
fraction, whose `|z|` reaches 6.2. So clause 3 passing does not mean the primary
is significant; it means *something* in the family is, and that something is the
denominator-bearing statistic. Clause 2 kills the threshold regardless, so there
is no consequence — but a future round should apply the family correction to the
primary alone.

## 5. Stage 1B — the monetizable upper bound

Seven event populations: the detector-free `q ∈ {1, 4, 12, 48}` and the anchors
at `k ∈ {1.5, 2.0, 3.0}`. All net of the committed cost, all reported at `C` and
at `2C`, all against 200 matched-null draws.

### 5.1 The decisive quantity

**B-3's excess over the matched null, in round trips per opportunity.** The gate
is `≥ 0.50` on both deciding panels.

| population | 2021–23 @ `C` | 2023–25 @ `C` | 2021–23 @ `2C` | 2023–25 @ `2C` |
| --- | ---: | ---: | ---: | ---: |
| `horizon_1` | +0.0001 | +0.0001 | −0.0000 | +0.0000 |
| `horizon_4` | +0.0005 | +0.0003 | +0.0004 | +0.0002 |
| `horizon_12` | −0.0071 | +0.0109 | −0.0004 | +0.0033 |
| `horizon_48` | −0.0055 | −0.0202 | −0.0128 | −0.0141 |
| `anchor_1.5` | +0.0651 | −0.0275 | +0.0223 | −0.0236 |
| `anchor_2.0` | +0.2431 | −0.6771 | +0.1359 | −0.3893 |
| **`anchor_3.0`** | **+2.3896** | **+1.5646** | **+1.2515** | **+0.7394** |

The four detector-free populations are between **two and four orders of magnitude
below the floor**, and two of them are negative. `anchor_1.5` and `anchor_2.0`
disagree in sign between the two deciding panels.

### 5.2 The one population that clears E1′, and why it fails

`anchor_3.0` clears the floor on the point estimate at both cost levels. It fails
E3, and it is worth stating exactly what it is:

| | 2021–23 | 2023–25 |
| --- | ---: | ---: |
| pairs producing any anchor | 13 of 20 | 19 of 20 |
| events per pair | 12.9 | 18.1 |
| events per pair per year | 5.2 | 7.3 |
| take-all net per event | +33.83 | +2.75 |
| take-all net per event at `2C` | +30.87 | **−0.32** |
| pairs with positive take-all | 11 of 13 | 11 of 19 |
| **top-ten-day share of B-3's net** | **1.00** | **1.00** |
| B-3 excess, studentized | **+0.98** | **+0.81** |

The top-ten-day share is `1.00` because there are barely more than ten days with
an anchor on them — which is the finding rather than an artefact of the metric.
The excess sits inside one standard deviation of its own null, take-all's
per-event edge falls by more than a factor of ten between the panels and goes
negative at double cost, and seven of twenty pairs produce nothing at all on the
first panel.

**A limitation of the frozen gate, recorded and not repaired.** E1′ has no
significance requirement — it compares a point estimate to a floor. `anchor_3.0`
is precisely the case that exposes it: a large excess with `z ≈ 0.9`. E3 caught
it, so the outcome is unaffected, but the gate should have carried a studentized
clause and it was too late to add one once the result was visible. This is the
same error class the programme recorded in the momentum round — a uniformly
positive point estimate with an interval spanning zero.

### 5.3 What the descriptive bounds say

The perfect-foresight bounds behave exactly as the noise reference predicted, and
that is their whole content:

| population, 2021–23 @ `C` | B-0 take-all | B-1 perfect skip | B-2 perfect side | B-3 |
| --- | ---: | ---: | ---: | ---: |
| `horizon_1` | −3.022 | +1.243 | +1.436 | −0.0010 |
| `horizon_12` | −3.054 | +6.409 | +12.427 | −0.0078 |
| `horizon_48` | −3.399 | +14.739 | +29.546 | +0.6238 |

B-1 and B-2 grow with `√q` on both real and generated data and separate nothing.
**B-2 does not dominate B-1**, which is a property of the definitions and is easy
to misread: B-2 picks the side perfectly but is still obliged to trade, so every
event whose move is smaller than the spread costs it money, while B-1 may skip. A
test asserts the non-domination so that a later reading of B-2 as "the ceiling"
fails there rather than in a report.

`PATH_STRUCTURE_STATISTICALLY_REAL_BUT_ECONOMICALLY_TOO_SMALL`.

## 6. Stage 1C — tick volume

### 6.1 The read

Recovered through the three routes' **own** `_assert_span` guards — called, not
copied — for one field, into its own cache. `PRICE_KEYS` and the three readers
are untouched.

| panel | guard | source | M15 bars | measured span |
| --- | --- | --- | ---: | --- |
| `momentum_2021_2023` | `momentum.assert_momentum_span` | `candles_{pair}_M1_3650d_BA.jsonl` | 999,238 | 2021-04-26 … 2023-04-25 |
| `supplemental_2023_2025` | `supplemental.assert_supplemental_span` | same | 993,878 | 2023-04-26 … 2025-04-24 |
| `development_2025` | `bars._assert_span` | `candles_{pair}_M1_365d_BA.jsonl` | 335,200 | 2025-04-25 … 2025-12-28 |

Every bar count matches the price panel exactly, and every measured span equals
its declared one.

**Coverage is complete**: the field is present on **100%** of M15 bars on every
pair of every panel, no M1 row is missing it, and no bar has zero volume. Median
per bar is in the hundreds (`AUD_CAD`: 570 and 494), 1st–99th percentile roughly
40 to 3,500.

### 6.2 Is it a proxy?

Per pair, `log(1 + volume)` regressed on realised volatility, spread, the bar's
own absolute move and the session:

| panel | median `R²` | min | max |
| --- | ---: | ---: | ---: |
| 2021–23 | **0.524** | 0.262 | 0.709 |
| 2023–25 | **0.463** | 0.240 | 0.571 |

The redundancy threshold was `0.80`. **Half of it is not explained by anything
the programme already has.**

### 6.3 What the residual knows

Spearman of the residual against the next bar, with a permutation null at 200
draws:

| panel | vs next `|r|` | pairs same sign | vs next signed `r` | pairs same sign |
| --- | ---: | ---: | ---: | ---: |
| 2021–23 | **+0.1243** (`z +128`) | **20 / 20** | −0.0014 (`z −1.2`) | 12 / 20 |
| 2023–25 | **+0.1476** (`z +146`) | **20 / 20** | +0.0013 (`z +1.4`) | 13 / 20 |

The `z` values are large because `n` is about a million per pair; **the effect
size is the finding, not the `z`.** A rank correlation of 0.12–0.15 with the same
sign on all forty pair-panels is a real, substantial relation to future
**volatility**. Against future **direction** the correlation is a thousandth, and
the pair count is a coin flip.

Volume shocks persist: the pair-local autocorrelation of `log(1 + volume)` is
0.89 / 0.84 at one bar and still 0.61 / 0.45 at eight, so a shock lasts about two
hours.

`TICK_VOLUME_INFORMATION_INCREMENTALLY_DISTINCT` — kept as a **feature candidate
only**, and it is a volatility feature.

## 7. Stage 2 and Stage 3 — not begun, and why

Plan §15's three entry conditions:

* **A** — a clean structure survives Stage 1A. **Failed**: no threshold survives.
* **B** — the economic gate passes. **Failed**: no population passes E1′ and E3
  together on both deciding panels.
* **C** — the effect is not carried by one pair, one bloc or a handful of days.
  **Failed** for the only population that cleared E1′: a top-ten-day share of
  1.00, and 13 of 20 pairs producing any event at all on the first panel.

All three fail, so no label family was defined, no barrier was placed, no
baseline was run, and no ML experiment was designed. Stage 3's prerequisites are
consequently unmet at condition 1 — there is no gross-positive simple event
population that replicates across the deciding panels.

**This is Stop B, and the plan prefers it to continuing.**

## 8. Deviations from the frozen plan

1. **Amendment A-1** (§3) — made before the first real statistic, on generated
   data, and it made the gate harder.
2. **E1′ has no significance clause** (§5.2) — a gap in the frozen gate, found
   only when `anchor_3.0` exposed it. Recorded, not repaired, because repairing a
   threshold after seeing a result is the thing pre-registration exists to
   prevent. E3 caught the case regardless.
3. **Clause 3's family correction is over the whole family, not the primary**
   (§4) — as the plan specifies, but it means clause 3 is not a check on the
   statistic the verdict reads. No consequence here; a future round should
   narrow it.
4. **Two implementation defects were fixed during the run**, both making a stage
   possible rather than changing an answer: `retrace.summarise`'s σ-level day
   trim indexed a NumPy array with a pandas mask, and the family-max matrix
   filtered its rows per key, so a statistic a thin threshold cannot always
   compute produced an inhomogeneous array instead of falling through to its own
   guard. Both surfaced on the 2025 panel; neither touches an artifact that had
   already been produced.
5. **`retrace.null_sanity` did not report the primary.** The first version listed
   the fraction and the adverse extension and omitted `median_retrace_sigma` —
   so Stage 1A's primary had no sanity check, which is the identical gap B′-2
   shipped with. Fixed, the artifact regenerated, and the result (§4.1) turned
   out to carry the section's most useful number: the instrument's noise floor is
   the same size as the effect the panels show.

## 9. Verification

* `tests/research` — **209 tests**, of which 29 are this package's.
* Every span refusal is asserted against a **named** exception type, so a
  `KeyError` or a `FileNotFoundError` cannot be mistaken for a guard firing. The
  volume reader is probed with the fresh pool, a one-day overreach on **both**
  edges of all three spans, the OOS slice, a truncated `"2025"`, an unknown panel
  and an unregistered pair.
* A test replaces each route's guard with one that refuses everything and
  requires the reader to stop — so the reader is shown to **use** the route's
  guard rather than a copy of its bounds.
* All five Stage 1A clauses are each shown to be individually capable of killing
  a threshold.
* The economic gate is shown to ignore a large perfect-foresight excess while
  reading a selectable one, and to sit exactly on its floor at `1.25` and fail at
  `1.24`.
* B-3 is shown to be neither inert nor credulous: zero on a random walk, above
  cost on an Ornstein–Uhlenbeck level.
* `ruff format --check`, `ruff check`, `tools/lint/run_custom_checks.py` — clean.

Known, unrelated and pre-existing: the full `pytest tests/` suite crashes on
Windows from `sys.addaudithook` accumulation in `isolation.py`. A separate
referral, not mixed in here.

## 10. Final interpretation

**Is there monetizable room left in price alone?** On this evidence, no. The
serial structure is real and replicates; the best selector that can be built from
past information, measured in-sample and net-referenced, is two to four orders of
magnitude short of a round trip on every population that has enough events to
measure, and the one thin population that clears the floor on a point estimate
does so within one standard deviation of its own null and on ten days.

**Higher timeframes** were not re-explored and there is no reason to: the
question they would answer is a direction question, and the economic bound is not
direction-specific — it bounds any linear selector on the features that include
HTF context.

**Volume stays**, as a volatility feature and nothing else. It is the only thing
this package found that is both new and real. What it cannot do is tell the
programme which way the price will go, and direction is what the cost model
punishes.

**ML does not stay.** A meta-label model is a selector, and B-3 is an in-sample
upper bound on a linear selector using exactly the feature categories Stage 3 was
allowed. It found nothing to select. A non-linear model could in principle exceed
a linear one, but not by the two-to-four orders of magnitude required.

**Fresh replication is not worth spending.** There is no candidate to replicate.
The `N = 1` forward budget is unspent and should stay that way.

**The next question is an information question, not a modelling one**, and the
package's own volume result sharpens it: the one variable added here turned out
to be informative about volatility and silent about direction. That is the shape
of the problem. Ranked, with what each would need — **nothing has been acquired,
and each needs its own authorisation**:

| candidate | economic hypothesis | data | frequency | expected turnover | difficulty |
| --- | --- | --- | --- | --- | --- |
| **1. carry / rate differential** | a funding return that does not have to be predicted, only held; the one FX effect with a mechanism rather than a pattern | overnight rate or swap points per pair | daily | very low — a monthly or quarterly rebalance | low: rates are public, but per-broker swap points are not, and the backtest is only as good as the financing assumption |
| **2. economic calendar** | direction is unpredictable but the *timing* of volatility is scheduled; an event filter is a cost decision, not a direction one | release times, and consensus vs actual | event-driven | low — it removes trades rather than adding them | medium: timestamps are easy, historical consensus is not |
| **3. COT positioning** | crowding predicts reversal at a horizon far longer than anything tried here | CFTC weekly commitments | weekly | very low | low to acquire, but it is US-futures positioning used as a proxy for a spot FX pair |
| **4. implied volatility** | the risk premium between implied and realised is a different object from the direction the programme keeps failing to predict | FX option implied vol surfaces | daily | low | high: expensive, and the least likely to be obtainable |

Carry first, because it is the only one whose return does not require predicting
direction at all — which is precisely the thing four rounds have now failed to
do.

## 11. Final status

* **B — `PRICE_PATH_STRUCTURE_REAL_BUT_NOT_ECONOMICALLY_HARVESTABLE`**
* `RETRACE_GEOMETRY_FAMILY_DROPPED_AFTER_CLEAN_RETEST`
* `PATH_STRUCTURE_STATISTICALLY_REAL_BUT_ECONOMICALLY_TOO_SMALL`
* `TICK_VOLUME_INFORMATION_INCREMENTALLY_DISTINCT` — a volatility feature, kept
* `NON_DECISION_BEARING_EXPLORATORY_ONLY` ·
  `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
* **Fresh pool `2016-06-02 … 2021-04-25` untouched.** Historical OOS untouched.
  The dead window and the forward epoch untouched.
* **Formal Confirmation not performed.** No broker, demo or live contact. No
  order of any kind.
* No external data acquired and no new network access.
* `PRODUCTION_READINESS_NOT_CLAIMED`.

Fresh historical replication, external data acquisition and Formal Confirmation
each await an explicit human + ChatGPT instruction.
