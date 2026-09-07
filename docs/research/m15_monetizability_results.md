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

## 1. The answer, stated to the limits of what was bounded

**Three findings, each on its own evidence, and none of them larger than the
evidence supports.**

* **Round B′-2's retrace positive is a selection effect, and this round measured
  the selection rather than inheriting the claim.** The detector picks
  materially different events on the real and null sides — real anchors form
  faster (`z −14.11` at `k = 1.5`), get correspondingly shorter windows, and
  carry smaller excursions (`z −4.88`). Every B′-2-family statistic that reaches
  significance moves in the direction that selection difference predicts: the
  *fraction* rises when its excursion denominator shrinks (`z +3.25 … +5.05`),
  the *adverse extension* falls when the window shortens (`z −3.3 … −3.9`). The
  σ-level absolute retrace — the one statistic whose direction neither predicts —
  is the one that never reaches `|z| ≥ 2` on any panel.
* **The selection question is closed and the direction question is closed, on
  seven event populations, for one linear selector on eight fixed features.**
  B-3's excess over a matched null lies between `−0.68` and `+2.39` round trips
  per opportunity against a floor of `0.50`; the four detector-free populations
  are between two and four orders of magnitude short, the two lower anchor
  thresholds are short by a factor of 2 to 8 **and disagree in sign between the
  deciding panels**, and the one population that clears the floor does so with
  `z ≈ 0.9`, on 6–9 events per pair per year, with a top-ten-day share above 1.
* **Tick volume is not redundant, and it is about volatility, not direction.**
  Its residual — after realised volatility, spread, the current move and the
  session — has a Spearman of **`+0.124`** and **`+0.148`** with the **next bar's
  absolute** return, the same sign on **20 of 20 pairs** on both deciding panels
  and `z = +10.1 / +17.0` against a null that preserves each series' own serial
  dependence. Against the next bar's **signed** return it is `−0.0014` and
  `+0.0013`, `z = −1.3 / +1.3`, 12 and 13 pairs of 20.

**What is not closed.** B-3 bounds *fixed-horizon* rules with a *linear*
selector on *these* features that *enter after the signal and exit at window
end*. It does not bound barrier or first-passage **exits**, non-linear
selectors, other feature sets, or other entry rules. §10 says so where the
earlier version of this document said "the price-only phase closes".

## 2. Identity

| | |
| --- | --- |
| PR #469 | merged, merge commit **`a0858ecba4143037d4137da44ac66cf976b77b8e`** |
| verified before merge | head `850fb40` matched, CI green, `MERGEABLE`/`CLEAN`, no unresolved review comment |
| package plan | `40cbcd9`, before any statistic of this package; amendment A-1 at `cbbe7f4`, before any **real** statistic |
| panels | `2021-04-26…2023-04-25` (624 trading days) · `2023-04-26…2025-04-24` (624) · `2025-04-25…2025-12-28` (212) |
| pairs / bars | `PAIRS_20` · 999,238 + 993,878 + 335,200 |
| tick volume read | **34,316,488** M1 rows over those same three spans, through the routes' own guards |
| declared vs measured span | identical on all three, for prices **and** for volume |
| new market-data spans read | **none** |
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

The frozen E1 floor is `0.50 × C`, and **B-1 clears it on pure noise**:
`E[max(net, 0)]` is about `0.4 · σ_q` for any roughly symmetric distribution and
`σ_q` grows as `√q`, so a gate read off perfect foresight cannot reject.

B-3 returns zero on the same data, and is not inert — on an **Ornstein–Uhlenbeck
level** (the price reverts, half-life about 69 bars) with a 0.2 pip round trip it
returns `+0.929 = +4.6 × C`, taking about 433 of 614 events, where take-all
already earns `+4.0 × C`. An AR(1) on **returns** with `φ = −0.30` was tried as
that control first and is the wrong one: a single lag-1 term largely cancels
inside a `q`-bar block, so fading blocks does not pay under it and an inert
selector would have looked correct.

So B-1 and B-2 became `DESCRIPTIVE_ONLY` and E1 became **E1′** — B-3's net per
event minus the same computation on the matched null — at the same `0.5 × C`
floor. **The floor was not moved**; only the quantity it applies to changed.

## 4. Stage 1A — the clean retrace geometry re-test

### 4.1 Null sanity, at the plan's 200 draws

On a panel-shaped generated walk — 20 series, 50,000 bars, no structure of any
kind, produced by the committed driver:

| `k` | anchors | **σ-level diff** | `z` | trimmed `z` | fraction `z` |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1.5 | 4,120 | +0.1095 | +1.07 | +0.86 | +1.22 |
| 2.0 | 881 | +0.5571 | +1.74 | +1.42 | +0.78 |
| 3.0 | 62 | +0.5430 | +0.34 | +0.33 | −0.81 |

Every cell sits inside its band. **At 40 draws the same walk gave `k = 2.0` a `z`
of `+2.27`** — above the clause-2 floor, on data with nothing in it. The plan
required 200 for exactly this reason; Round B′ ran B′-2 at 40.

The earlier version of this document read the raw differences as a "noise floor"
of the same size as the panels'. That comparison is weaker than it looked — the
walk has 62 anchors at `k = 3.0` against 201 and 350, with two to three times the
null spread — and it is withdrawn. The comparison that survives is the
studentized one: the panels' maximum is `+1.50` and this walk's is `+1.74`.

### 4.2 The panels

**The primary is `median_retrace_sigma`.** Real minus the matched N2 null, 200
draws:

| panel | `k` | anchors | **primary, σ-level** | `z` | day-trimmed `z` | *fraction* `z` |
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

Clause 2 fails at all three thresholds on both deciding panels; clause 4 also
fails at `k = 2.0` and `k = 3.0`, clause 5 at `k = 3.0`.

`RETRACE_GEOMETRY_FAMILY_DROPPED_AFTER_CLEAN_RETEST`.

### 4.3 The selection difference, measured

The first version of this package asserted that the fraction's positive was a
denominator artefact and **did not measure the denominator** —
`median_excursion_sigma` was not among the statistics compared against the null,
so the claim was inherited from Round B′'s 40-draw post-hoc check. It is measured
now, at 200 draws, along with the two axes that set the observation window:

| panel | `k` | bars to anchor `z` | window `z` | excursion `z` | σ-retrace `z` | fraction `z` | adverse ext. `z` |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2021–23 | 1.5 | **−14.11** | **−14.11** | −4.88 | +0.74 | +4.06 | −3.92 |
| 2021–23 | 2.0 | −2.65 | −2.65 | −2.96 | +0.70 | +3.41 | −1.99 |
| 2021–23 | 3.0 | −0.39 | −0.39 | −0.86 | +1.50 | +3.40 | −0.28 |
| 2023–25 | 1.5 | 0.00 *(identical)* | 0.00 *(identical)* | −4.31 | +1.19 | +3.25 | −3.62 |
| 2023–25 | 2.0 | −4.23 | −4.23 | −3.73 | +1.40 | +5.05 | −1.35 |
| 2023–25 | 3.0 | −1.42 | −1.42 | −1.90 | +1.18 | +4.16 | −0.11 |
| 2025 | 1.5 | −0.93 | −0.93 | −1.24 | +0.22 | +1.66 | −3.31 |
| 2025 | 2.0 | −1.25 | −1.25 | −1.29 | +0.63 | +2.48 | −3.32 |

Every selection axis is negative on every panel and threshold: real anchors form
faster than null anchors, so their windows — `min(4 × bars_to_anchor, 480)` — are
shorter, and their excursions are smaller. The window `z` equals the formation
`z` exactly, because one is four times the other.

That single fact predicts the sign of both significant statistics. **The
fraction** divides by a smaller excursion, so it rises. **The adverse extension**
has a shorter window in which to extend, so it falls. Neither is evidence about
path shape, and the earlier document's flat claim that "dividing by an excursion
was the whole effect" is replaced by this: *the two arms do not compare like with
like on any axis, and the only statistic whose direction the mismatch does not
predict is the one that is not significant.*

**One cell does not fit the window story and is worth stating plainly.** At
2023–25 `k = 1.5` the median formation time is **exactly equal** on both sides —
3.0 bars against 3.0, with zero spread across all 200 draws, so its studentized
value is undefined and it is excluded from the family rather than reported as
zero. The window is therefore equal too, and the fraction is still `+3.25`. On
that cell the mismatch runs through the **excursion** alone (`z −4.31`), which is
the axis the fraction's denominator uses; the adverse extension, which needs the
window, is `−3.62` there and is not explained by it. So the selection account
covers the fraction everywhere and the adverse extension on most cells, not on
all of them.

### 4.4 One clause needs reading carefully

Clause 3 — the family-wise `p` — *passes* at `0.005`, `0.005` and `0.015–0.040`.
It is computed, as the plan specifies, as a family-max over the **whole** family,
and that family contains the fraction, whose `|z|` reaches 6.2. So clause 3
passing does not mean the primary is significant; it means *something* in the
family is, and that something is a statistic §4.3 explains. Clause 2 kills the
threshold regardless.

## 5. Stage 1B — the monetizable upper bound

Seven event populations, all net of the committed cost, at `C` and `2C`, against
200 matched-null draws.

### 5.1 The decisive quantity

**B-3's excess over the matched null, in round trips per opportunity**, against a
floor of `0.50` on both deciding panels:

| population | events / pair / yr | 2021–23 @ `C` | 2023–25 @ `C` | 2021–23 @ `2C` | 2023–25 @ `2C` |
| --- | ---: | ---: | ---: | ---: | ---: |
| `horizon_1` | 24,601 | +0.0001 | +0.0001 | −0.0000 | +0.0000 |
| `horizon_4` | 6,168 | +0.0005 | +0.0003 | +0.0004 | +0.0002 |
| `horizon_12` | 2,058 | −0.0071 | +0.0109 | −0.0004 | +0.0033 |
| `horizon_48` | 515 | −0.0055 | −0.0202 | −0.0128 | −0.0141 |
| `anchor_1.5` | 127 | +0.0651 | **−0.0275** | +0.0223 | **−0.0236** |
| `anchor_2.0` | 35 | +0.2431 | **−0.6771** | +0.1359 | **−0.3893** |
| **`anchor_3.0`** | **6.5** | **+2.3896** | **+1.5646** | **+1.2515** | **+0.7394** |

The four detector-free populations are **two to four orders of magnitude** below
the floor. The two lower anchor thresholds are short by a factor of **2 to 8**
and **disagree in sign between the deciding panels** — the earlier version of
this document quoted the horizon range as though it covered all seven, which it
does not, and that is corrected here.

### 5.2 The one population that clears E1′

`anchor_3.0` clears the floor on the point estimate at both cost levels. It fails
E3, and its full description is this:

| | 2021–23 | 2023–25 |
| --- | ---: | ---: |
| pairs producing any anchor | 13 of 20 | 19 of 20 |
| events per pair | 12.9 | 18.1 |
| events per pair per year | 6.5 | 9.0 |
| take-all net per event | +33.83 | +2.75 |
| take-all net per event at `2C` | +30.87 | **−0.32** |
| **take-all, JPY bloc** | +26.95 (6 pairs) | **+17.30** (6 pairs) |
| **take-all, non-JPY bloc** | +39.73 (7 pairs) | **−3.96** (13 pairs) |
| **largest single pair's share of take-all net** | 0.26 | **1.05** |
| top-ten-day share of B-3's net | 1.02 | 1.03 |
| B-3 excess, studentized | **+0.98** | **+0.81** |

On the second deciding panel the two blocs **reverse sign**, and **one pair
carries 105% of the whole panel's take-all net** — every other pair together is
negative. The excess sits inside one standard deviation of its own null. Seven of
twenty pairs produce nothing at all on the first panel. And take-all's per-event
edge falls by more than a factor of ten between the panels, going negative at
double cost.

**A tail share above 1** is not an error: the top ten days contribute more than
the total, the remaining days being negative in aggregate. At 13–18 events per
pair there are barely more than ten days with an anchor on them at all, which is
itself the finding.

**Two limitations of the frozen gate, recorded and not repaired.**

* **E1′ has no significance clause** — it compares a point estimate to a floor,
  and `anchor_3.0` is exactly the case that exposes it: a large excess at
  `z ≈ 0.9`. This is the error class the programme recorded in the momentum
  round.
* **E4 as amended reads the bloc split of B-3, and B-3 is positive in both blocs
  almost everywhere** — it selects, so its net per *taken* event is positive by
  construction. E4 therefore passes for `anchor_3.0` while the economically
  meaningful version of the same check, on **take-all**, reverses sign. The
  take-all split is reported above as a diagnostic; the frozen clause is left
  where it was, because moving a clause onto a different quantity after seeing
  which one fails is the move pre-registration exists to prevent.

E3 fails the population on either reading. The first version of this package
computed **neither** E4 nor a bloc split nor a per-pair concentration, and
reported condition C as evaluated; all three are now in the artifact.

### 5.3 What the descriptive bounds say

| population, 2021–23 @ `C` | B-0 take-all | B-1 perfect skip | B-2 perfect side | B-3 |
| --- | ---: | ---: | ---: | ---: |
| `horizon_1` | −3.022 | +1.243 | +1.436 | −0.0010 |
| `horizon_12` | −3.054 | +6.409 | +12.427 | −0.0078 |
| `horizon_48` | −3.399 | +14.739 | +29.546 | +0.6238 |

A perfect take/skip oracle **does** clear the round trip, by 6 to 23×. That is
not evidence of anything — the same oracle earns `+1.672` on a pure random walk —
and the earlier version of this document said such an oracle "cannot pay for the
spread either", which is false and is withdrawn.

Nor do these bounds "separate nothing", as the earlier version also said. On the
anchor populations they separate strongly and in a coherent direction: B-2's
excess over the null is `z −5.06 / −5.55` at `k = 1.5` and B-1's is `−2.42 /
−3.50`, meaning **real anchors are followed by less absolute movement than
sign-flipped ones**. That is consistent with §4.3's shorter windows and is
reported here rather than claimed as structure.

**B-2 does not dominate B-1**: it picks the side perfectly but must still trade,
so every event whose move is smaller than the spread costs it money, while B-1
may skip. A test asserts the non-domination so a later reading of B-2 as "the
ceiling" fails there rather than in a report.

`PATH_STRUCTURE_STATISTICALLY_REAL_BUT_ECONOMICALLY_TOO_SMALL`.

### 5.4 The 2025 panel, which may not decide

Computed and, in the first version, not reported. It carries the strongest
positives in the stage: `anchor_1.5` B-3 excess `+0.92 × C` at `z +3.17`,
`anchor_2.0` `+1.02 × C`, take-all excess `z +3.65` and `+4.22`. Two populations
clear the E1′ floor there.

It **may not decide** — about 1,200 configurations were searched over it in
earlier rounds and plan §2 excludes it — but omitting the only panel pointing the
other way is a reporting defect independent of the verdict, and it is corrected
here. `anchor_3.0` has no 2025 row at all: 59 anchors over 20 pairs leaves most
pairs below the eight-event minimum.

## 6. Stage 1C — tick volume

### 6.1 The read

Through the three routes' **own** `_assert_span` guards — called, not copied —
for one field, into its own cache. `PRICE_KEYS` and the three readers are
untouched.

| panel | guard | M1 rows read | M15 bars | measured span |
| --- | --- | ---: | ---: | --- |
| `momentum_2021_2023` | `momentum.assert_momentum_span` | 14,591,042 | 999,238 | 2021-04-26 … 2023-04-25 |
| `supplemental_2023_2025` | `supplemental.assert_supplemental_span` | 14,745,861 | 993,878 | 2023-04-26 … 2025-04-24 |
| `development_2025` | `bars._assert_span` | 4,979,585 | 335,200 | 2025-04-25 … 2025-12-28 |

Every M15 bar count matches the price panel exactly and every measured span
equals its declared one. The `development_2025` M1 row count is identical to the
4,979,585 rows the Track A R1 execution recorded for the same span.

**Coverage is complete**: the field is present on **100%** of M15 bars on every
pair of every panel, no M1 row is missing it, and no bar has zero volume. Median
per bar is in the hundreds (`AUD_CAD`: 570 and 494), 1st–99th percentile roughly
40 to 3,500.

### 6.2 Is it a proxy?

Per pair, `log(1 + volume)` regressed on realised volatility, spread, the bar's
own absolute move and two harmonics of the session:

| panel | median `R²` | min | max |
| --- | ---: | ---: | ---: |
| 2021–23 | **0.524** | 0.262 | 0.709 |
| 2023–25 | **0.463** | 0.240 | 0.571 |

The redundancy threshold was `0.80`. This is one seven-column **linear** design —
ATR, shorter volatility windows and non-linearity are not in it, and volume's own
measurement noise sits in the residual — so it bounds redundancy against *these*
controls, not against everything the programme has.

### 6.3 What the residual knows

| panel | vs next `\|r\|` | pairs same sign | vs next signed `r` | pairs same sign |
| --- | ---: | ---: | ---: | ---: |
| 2021–23 | **+0.1243** (`z +10.1`) | **20 / 20** | −0.0014 (`z −1.3`) | 12 / 20 |
| 2023–25 | **+0.1476** (`z +17.0`) | **20 / 20** | +0.0013 (`z +1.3`) | 13 / 20 |

**The null changed and the `z` values with it.** Plan §14 specified the N2 sign
flip, which cannot be used: N2 preserves `|r_t|`, the trailing σ, the spread and
the session **exactly**, so both the residual and `abs_next_return` are identical
under it and the test has no variance. The frozen gate was ill-posed on that
point. The first substitute was an i.i.d. rank permutation, which destroys the
residual's own serial dependence as well as its pairing — and the residual is
strongly dependent, with a lag-1 autocorrelation of 0.89 and 0.84. That
understates the null spread by about elevenfold and produced the `z = +128 /
+146` the earlier version reported. A **circular block shift**, which keeps each
series' own autocorrelation, now runs beside it and is what the verdict reads.

The finding is unchanged and the effect size was always the point: a rank
correlation of 0.12–0.15 with the same sign on all forty pair-panels is a real,
substantial relation to future **volatility**. Against future **direction** the
correlation is a thousandth and the pair count is a coin flip.

Volume shocks persist: the autocorrelation of `log(1 + volume)` is 0.89 / 0.84 at
one bar and still 0.61 / 0.45 at eight, so a shock lasts about two hours.

`TICK_VOLUME_INFORMATION_INCREMENTALLY_DISTINCT` — a **volatility** feature
candidate.

## 7. Stage 2 and Stage 3 — not begun, and why

Plan §15's three entry conditions:

* **A** — a clean structure survives Stage 1A. **Failed**: no threshold survives.
* **B** — the economic gate passes. **Failed**: no population passes E1′ and E3
  together on both deciding panels.
* **C** — the effect is not carried by one pair, one bloc or a handful of days.
  **Failed** for the only population that cleared E1′: a top-ten-day share above
  1, a bloc sign reversal on take-all, and one pair at 105% of a panel's net.

No label family was defined, no barrier was placed, no baseline was run, no ML
experiment was designed. Stage 3's prerequisites are unmet at condition 1.

**This is Stop B, and the plan prefers it to continuing.**

## 8. Deviations from the frozen plan

1. **Amendment A-1** (§3) — before the first real statistic, on generated data,
   making the gate harder.
2. **E1′ has no significance clause** (§5.2) — a gap the `anchor_3.0` result
   exposed. Recorded, not repaired.
3. **E4 reads B-3, where the economically meaningful check is on take-all**
   (§5.2) — recorded, not repaired, with the take-all split reported beside it.
4. **Clause 3's family correction is over the whole family, not the primary**
   (§4.4) — as specified, but it is therefore not a check on the statistic the
   verdict reads.
5. **Stage 1C's null is not N2** (§6.3) — N2 makes the statistic degenerate. Two
   substitutes are computed and the conservative one decides.
6. **Stage 1B ran all three anchor thresholds** though plan §9 scopes it to the
   thresholds that survive Stage 1A, and none did. Conservative — extra
   populations can only make the gate easier to clear, and nothing cleared.
7. **E2′ is implemented as "excess ≥ 0.5 × 2C at 2C"** rather than the plan's
   "remains positive at 2C". Harder than specified.
8. **Plan §25.2's positive-control table is not reproducible at the committed
   defaults** — it was computed at a different fixture size. The substance is
   re-established by `s1b_signal_reference.json` and by a standing test.
9. **`round_b_prime/retrace.py` was changed**, which reaches into a merged round.
   Adding statistics to the compared set grows the family-max family; every
   per-statistic cell both versions compute is identical, so no Round B′
   per-statistic number changed, but Round B′'s family-level `p` would be
   computed over a larger family if it were re-run today.

## 9. Defects found by review and fixed in this package

Two independent review roles read the first version. Their concrete, reproducible
findings were fixed; the corrections above are theirs.

**A data-boundary bypass, present on merged master.** A `str` subclass whose
value is the declared bound passes every span guard — the guards were hardened to
compare parsed dates — and then answers `False` to both `day < lo` and
`day > hi`, so the scan returns **every row in the file**. Measured: 6 of 6
synthetic rows, including the fresh pool, the OOS slice and the forward epoch.
The hardening three earlier audits performed reached the **guards** and not the
**scans**, and the identical hole was present in `bars.read_m1`,
`supplemental.read_m1` and `momentum.read_m1`. All four now compare the parsed
date. **No forbidden row was read in this package**: every run used the module
constants.

Also fixed: `build_cache` served a cached parquet without validating it, and
could report the OOS slice as the development panel's data; E3's tail share was
taken over the *positive parts* of the taken events rather than over B-3's net,
which is meaningless where that net is negative; `geometry.verdict` treated a
clause it could not evaluate as a pass; `events_per_year` scaled by the 252-day
equity convention against panels whose own rate is 312.

## 10. Final interpretation

**Is there monetizable room left in price alone?** Not in what was bounded, and
what was bounded should be stated exactly: *selection and direction, for
fixed-horizon entries held to window end, under one in-sample linear selector on
eight past-only features.* Within that, the answer is no — by two to four orders
of magnitude on every population with enough events to measure it, and by a
factor of two to eight on the anchor populations, which additionally disagree in
sign between the deciding panels.

**What is not bounded, and would need its own round.** Exits. B-3 enters after
the signal and exits at the window's end; the plan's own Stage 2 families L-A and
L-B are barrier-exit families and nothing measured here touches them. Also
unbounded: non-linear selectors, other feature sets, other entry rules and
position sizing. The correct statement is that *this* family closes, not that
price closes.

**Higher timeframes** were not re-explored and there is no reason to as a
direction signal: HTF context is in B-3's feature set and the bound covers it.

**Volume stays**, as a volatility feature and nothing else. It is the only thing
this package found that is both new and real, and what it cannot do is say which
way the price will go — which is what the cost model punishes.

**ML does not stay for this family.** A meta-label model is a selector, and B-3
is an in-sample upper bound on a *linear* selector using exactly the feature
categories Stage 3 was allowed. It found nothing to select. A non-linear model
could in principle exceed a linear one; it would have to do so by a factor of
hundreds.

**Fresh replication is not worth spending.** There is no candidate to replicate,
and the `N = 1` forward budget stays unspent.

**The next question is an information question**, and this package's own volume
result sharpens it: the one variable added here is informative about volatility
and silent about direction. Ranked, with what each would need — **nothing has
been acquired, and each needs its own authorisation**:

| candidate | economic hypothesis | data | frequency | expected turnover | difficulty |
| --- | --- | --- | --- | --- | --- |
| **1. carry / rate differential** | a funding return that is held rather than predicted — the one FX effect whose return does not require calling direction | overnight rates or swap points per pair | daily | very low — monthly or quarterly rebalance | low to acquire; the hypothesis is **not** a free return: the carry premium is usually described as a crash-risk premium with heavy negative skew, and a retail swap-point markup can consume the whole differential, so the financing assumption *is* the backtest |
| **2. economic calendar** | direction is unpredictable but the *timing* of volatility is scheduled; an event filter is a cost decision, not a direction one | release times, and consensus vs actual | event-driven | low — it removes trades | medium: timestamps are easy, historical consensus is not |
| **3. COT positioning** | crowding predicts reversal at a horizon far longer than anything tried here | CFTC weekly commitments | weekly | very low | low to acquire, but it is US-futures positioning used as a proxy for spot FX |
| **4. implied volatility** | the implied-minus-realised premium is a different object from the direction four rounds have failed to predict | FX option implied vol surfaces | daily | low | high: expensive and least likely to be obtainable |

This ranking is a **prior**, not an inference from Stage 1 — nothing measured
here bears on carry, the calendar, COT or implied vol. Carry is first because it
is the only candidate whose return does not require predicting direction.

## 11. Verification

* `tests/research` — **232 tests**, of which 52 are this package's.
* **Mutation testing.** A review role mutated the package 25 ways and **ten
  survived** all 209 tests, including four leakage mutants and the whole of
  `volume_info`, which nothing imported. Re-measured over 26 mutations after the
  hardening pass: **26 of 26 killed.** The entry-timing mutants are pinned by
  arithmetic rather than by perturbation — the entry price is recovered from the
  recorded `gross` and compared against both candidate bars, because displacing
  the bars after an anchor moves the exit price either way.
* Every span refusal is asserted against a **named** exception type. The reader
  is probed with the fresh pool, a one-day overreach on **both** edges of all
  three spans, the OOS slice, a truncated `"2025"`, a full-width numeral, an
  unknown panel, an unregistered pair, and the `str` subclass above.
* A test replaces each route's guard with one that refuses everything and
  requires the reader to stop, so the reader is shown to **use** the route's
  guard rather than a copy of its bounds.
* `ruff format --check`, `ruff check`, `tools/lint/run_custom_checks.py` — clean.

Known, unrelated and pre-existing: the full `pytest tests/` suite crashes on
Windows from `sys.addaudithook` accumulation in `isolation.py`. A separate
referral, not mixed in here.

## 12. Final status

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
