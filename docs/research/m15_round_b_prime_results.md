# M15 Research Program — Round B′: results

**`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `PRODUCTION_READINESS_NOT_CLAIMED`.**

Plan: `docs/research/m15_round_b_prime_plan.md`, committed at `d5cd618` **before
any research statistic was computed**, amended twice before any real statistic at
`ccafebc` and `1b1a3ae`. Base master `0f3300a` (the PR #468 merge).

**Final classification: Case A —
`PRICE_PATH_STRUCTURE_SURVIVES_NULL_CONTROL`.**

It is derived by `driver._classification` from the four machine verdicts, not
chosen here. Economic materiality is deliberately not an input to it; it governs
what Case A's *consequence* may be, which §12 states.

`TRACK_A_RESEARCH_PROGRAM_ROUND_B_PRIME_COMPLETED`.

---

## 1. The answer

**There is serial structure in the M15 price path that no matched null
reproduces. It replicates across two independent 730-day panels, it survives a
family-max correction, and the best linear rule that can be built from it —
measured in-sample, which flatters it — reaches between 6% and 16% of what a
round trip costs.**

Three statements, in the order the evidence supports them.

* **B′-1 is positive and clean.** `VR(q) < 1` at every horizon on every panel,
  stable on both deciding panels at `q ∈ {2, 4, 12, 48, 96, 192}`, studentized to
  **−14.7** against a null that holds `|r_t|` fixed bar by bar. Westfall–Young
  family-max over the seven horizons gives `p = 0.005` on all three panels — the
  floor for 200 draws. This is the most robust measurement this programme has
  produced.
* **B′-2's pre-registered statistic is positive and confounded.** The retrace
  fraction survives all five kill clauses at `k = 2.0` and `k = 3.0`. But the same
  quantity measured in **σ units**, with no excursion in its denominator, is
  positive on all nine panel × threshold cells and **significant in none of them**
  (`z` from `+0.18` to `+1.96`). Real anchors are smaller than null anchors
  (`median_excursion_sigma` 5.92 vs 6.75, `z −2.94`), so a similar absolute
  retrace divided by a smaller denominator is most of the effect. B′-2 points the
  same way as B′-1 and does not independently establish anything.
* **Neither is worth trading, on the evidence this round can produce.** The best
  linear predictor of the next `q`-bar move from the last 96 bars, fitted and
  scored on the same data, reaches **8–29%** of the break-even information
  coefficient; the part not attributable to fitting noise reaches **5.6–16%**.
  Short by a factor of **6 to 18**, at every horizon from one bar to twelve hours.

B′-4 is cleanly negative. B′-VOL read nothing.

## 2. The round was wrong before it was reviewed, and both roles found it

The first version of this document recorded **Case C —
`PRICE_ONLY_PATH_STRUCTURE_SCREEN_NEGATIVE`**, whose pre-registered condition is
that all three studies are empty, while its own artifacts recorded B′-1 and B′-2
as non-empty. Two independent review roles found that separately. It is recorded
here because the correction changes the round's conclusion, not its presentation.

Two defects, both material.

**The classification did not follow the pre-registered rule.** Case A's trigger
had fired; it was declined on the ground that Case A also requires a
"non-negligible" difference and the plan attached an economic floor to B′-2 and
none to B′-1. That is true and it is a defect in the pre-registration — but the
floor was then supplied from a `POST_HOC_DIAGNOSTIC_ONLY` model that the plan's
own §10 forbids from carrying a conclusion, and used to overturn the case. The
fix is structural: `driver._classification` now applies plan §11 to the four
verdicts, `test_the_classification_follows_the_pre_registered_rule` pins it, and
economic materiality is excluded from its inputs by construction.

**The primary null was not the null the plan specifies.** Plan §5.4 registers a
per-bar sign flip after which "the identical anchor detector and the identical
retrace measurement" run on the result, so that "the anchor-selection geometry is
reproduced, not assumed away". The implementation flipped each return's sign and
re-attached the **real bar's** high and low offsets. Those offsets are strongly
coupled to the sign of the bar's own return — measured on `EUR_USD` over 2021–23:

| | `(h−c) − (c−l)` |
| --- | ---: |
| `corr` with `sign(r_t)` | **−0.5744** |
| mean on up bars | −3.70 pips |
| mean on down bars | +3.64 pips |

An up bar closes near its high. Flipping the sign without swapping the offsets
builds a bar that closes **down** with its close pinned to the high, and
`find_anchors` reads exactly `mid_h` and `mid_l` for both the retrace depth and
the continuation. This was a bug against the written specification, not a change
of specification: the corrected null implements §5.4 more faithfully, and it
preserves each bar's **total range** exactly.

Two things follow, and the second is uncomfortable.

* Under the corrected null, B′-2 **reverses sign and strengthens**. Real paths
  retrace *more* of their excursion than a direction-destroyed path with coherent
  bars, where before they appeared to retrace less. The earlier document's
  reading — "less retrace than the null, which is continuation" — is **withdrawn
  in full**. The direction now agrees with B′-1 instead of contradicting it.
* B′-2's corrected numbers are a **second look at the same data**. The defect is
  demonstrable without reference to any outcome, and the fix was specified by
  coherence rather than by the result; but the round cannot claim B′-2 as a clean
  pre-registered finding, and does not. That is one of two reasons §12 declines to
  treat B′-2 as establishing anything.

B′-1 is unaffected by all of this — `variance_ratio` reads only `mid_c` and
`pip_size` — so Case A rests on the study that was never touched.

## 3. Identity

| | |
| --- | --- |
| PR #468 | merged, merge commit **`0f3300a00cf0fdc79e3efb892cd1a491afe035f1`** |
| pre-registration | `d5cd618`, before any statistic; amendments `ccafebc`, `1b1a3ae`, both before any **real** statistic |
| panels | `2021-04-26…2023-04-25` (624 days) · `2023-04-26…2025-04-24` (624) · `2025-04-25…2025-12-28` (212) |
| declared vs measured span | identical on all three |
| pairs / bars | `PAIRS_20` · 999,238 + 993,878 + 335,200 |
| deciding panels | the two 730-day panels. 2025 may contradict; it may not decide |
| **new market-data reads** | **zero** |
| fresh pool `2016-06-02…2021-04-25` | **untouched** |
| artifacts | 22, from one end-to-end driver pass plus the generated-data amendment evidence |

## 4. Null sanity — run before any real comparison, one per study

**B′-1**, three nulls on a generated IID random walk, 40,000 bars, 40 draws.
Every one must return `VR ≈ 1`:

| `q` | N1 iid | **N2 sign flip** | N3 weekday |
| ---: | ---: | ---: | ---: |
| 2 | 0.9993 | **0.9987** | 0.9992 |
| 48 | 0.9921 | **0.9843** | 1.0195 |
| 192 | 1.0022 | **0.9854** | 1.0512 |
| 480 | 0.9738 | **0.9981** | 1.0811 |

Largest `|z|` across all seven horizons: 1.469 / 1.521 / 1.383. No horizon fails.

**B′-2 had no sanity check in the first version, and that is precisely what would
have caught the null defect.** It has one now, and because `k = 3.0` yields
single-digit anchor counts on one series it runs on a **panel-shaped** walk — 20
generated series of 50,000 bars:

| `k` | anchors | retrace fraction, real − null | `z` | adverse extension, real − null | `z` |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1.5 | 4,120 | +0.0192 | +1.18 | −0.0071 | −0.09 |
| 2.0 | 881 | +0.0253 | +1.15 | −0.3456 | −1.26 |
| 3.0 | 62 | −0.0470 | −0.91 | −0.7703 | −0.60 |

A generated walk has neither reversion nor continuation, and every cell sits
inside its band. The corrected null is unbiased at the scale the panels are read
at.

## 5. The two pre-registration amendments, now reproducible

Both were made on generated data before any panel was touched and both made the
test harder. Neither had a producing file in the tree — the same "artifact with
no committed generator" failure this programme has hit before, and a review role
measuring the committed code got numbers close to but not equal to the recorded
ones. `scripts/research/round_b_prime/amendment_evidence.py` reproduces both, and
**its numbers supersede the plan's tables where they differ**.

**§13 — the registered primary null was degenerate.** A 5-day *block* sign flip
leaves every path inside a block untouched, so a `q`-bar sum with `q` below the
block length keeps its variance. On a generated AR(1) with `φ = −0.10` and a
volatility cycle:

| `q` | real | block flip *(registered)* | per-bar flip *(amended)* |
| ---: | ---: | ---: | ---: |
| 2 | 0.9073 | **0.9073** | 0.9986 |
| 96 | 0.8808 | **0.8736** | 0.9840 |
| 480 | 0.8247 | 0.9464 | 0.9753 |

At `q = 2` the block flip differs from the real value in the fifth decimal. A null
that cannot move the statistic cannot reject anything. It only begins to work at
`q = 480`, which is the block length.

**§14 — the retrace window was 24× the excursion.** On a generated walk at
`k = 1.5`:

| window | window ÷ excursion | median retrace fraction | `reached_50` |
| --- | ---: | ---: | ---: |
| flat 480 *(registered)* | 24.0× | 2.241 | 0.835 |
| ×2 | 2.0× | 0.582 | 0.555 |
| **×4 *(adopted)*** | **4.0×** | **0.781** | **0.661** |
| ×8 | 8.0× | 0.998 | 0.757 |

The flat window measures the window: a median "retrace" of 2.24 times the
excursion, with the 50% level saturated. The adopted multiple restores the scale
the pre-registered 0.05 floor was written for.

## 6. B′-1 — the variance ratio

Real `VR(q)`, with the studentized difference from the primary null:

| `q` | 2021–23 | 2023–25 | 2025 |
| ---: | --- | --- | --- |
| 2 | 0.9665 (**z −13.76**) | 0.9768 (z −9.81) | 0.9620 (z −10.34) |
| 4 | 0.9413 (z −14.69) | 0.9601 (z −9.97) | 0.9448 (z −7.73) |
| 12 | 0.9225 (z −11.40) | 0.9382 (z −9.18) | 0.9161 (z −8.31) |
| 48 | 0.9257 (z −6.62) | 0.9410 (z −5.43) | 0.9032 (z −5.48) |
| 96 | 0.9527 (z −3.14) | 0.9339 (z −4.47) | 0.8852 (z −4.84) |
| 192 | 0.9552 (z −2.08) | 0.9233 (z −3.41) | 0.8134 (z −5.53) |
| 480 | 0.8748 (z −3.69) | 0.9391 (z −1.66) | 0.7196 (z −5.44) |

Stable on both deciding panels at six of seven horizons; `q = 480` is excluded by
the stability rule because 2023–25 reaches only `z −1.66`. N1 and N3 give nearly
identical differences, so this is not a calendar or weekend-gap artefact.

**Family-max correction over the seven horizons**, Westfall–Young on the 200
draws already taken:

| panel | observed max abs `z` | null max, mean / p95 | family-wise `p` |
| --- | ---: | ---: | ---: |
| 2021–23 | 14.687 | 1.585 / 2.627 | **0.005** |
| 2023–25 | 9.970 | 1.588 / 2.458 | **0.005** |
| 2025 | 10.341 | 1.577 / 2.667 | **0.005** |

`0.005` is `1/201`, the floor for 200 draws: no null draw came close.

### 6.1 Where it is, stated accurately

The first version of this document said "the effect is in every bloc and every
sub-period". **That is false and is withdrawn.** From `b1_bloc_split.json`, the
studentized difference from the primary null:

| `q` | 2021–23 JPY | 2021–23 non-JPY | 2023–25 JPY | 2023–25 non-JPY |
| ---: | ---: | ---: | ---: | ---: |
| 2 | −4.83 | −13.00 | −1.64 | −11.92 |
| 12 | −2.55 | −11.96 | −1.30 | −10.70 |
| 48 | −1.11 | −8.50 | −1.00 | −5.92 |
| 96 | **+1.87** | −4.82 | −1.22 | −4.36 |
| 192 | **+2.42** | −4.11 | −2.36 | −2.93 |
| 480 | +0.84 | −5.53 | −0.14 | −2.39 |

**B′-1 is a non-JPY effect at short horizons.** The six JPY pairs reach the
round's own `|z| ≥ 2` bar at two of twelve cells, and at `q = 192` on 2021–23 they
cross it with the **opposite sign**. Sub-periods are likewise mixed: the 2021–23
`q = 192` blocks are `1.030 / 0.962 / 0.874 / 0.877` — the first is above 1. At
`q = 12`, where the effect is largest, all four blocks are below 1 on both
deciding panels (`0.924 / 0.928 / 0.899 / 0.965` and
`0.920 / 0.975 / 0.907 / 0.966`), and that is the range the claim should have been
confined to.

## 7. What the structure is worth — `POST_HOC_DIAGNOSTIC_ONLY`

These are outside the 28 pre-registered cells and **cannot carry a verdict** (plan
§10). They do not choose the case — §2 explains why that matters — and they are
reported because §6 without them says less than is known.

### 7.1 It is not a one-bar effect

The first version of this document called it "a one-bar quoting effect". The
sample autocorrelation function, measured directly against the same
direction-destroying null, **refutes that** and the claim is withdrawn:

| panel | `ρ₁` | `z` at lag 1 | lags of 100 outside ±3 sd | expected by chance |
| --- | ---: | ---: | ---: | ---: |
| 2021–23 | −0.0316 | −20.5 | **20** | 0.27 |
| 2023–25 | −0.0244 | −13.4 | **17** | 0.27 |

Lag 1 dominates individually but carries only 12–14% of the summed `|ρ_k|` over
100 lags. Only lags 1, 97 and 100 are outside the band on **both** deciding
panels, so most of the rest does not replicate — but "a single lag-1 term" is not
what the data says, and the coarse-base test that suggested it is, by the identity
`VR_b(q) = VR₁(bq) / VR₁(b)`, a restatement of §6 rather than independent
evidence. Both are recorded in `post_hoc_diagnostics.json`; neither is
load-bearing any more.

### 7.2 The bound that does not depend on the mechanism

The plan gave B′-2 an economic floor and B′-1 none. The floor that was missing is
Round A's own — the **break-even information coefficient**, `cost / sd(q-bar
move)` — and the quantity to compare it against is the best **linear** predictor
of the next `q`-bar move from the last 96 bars, whose `R²` follows from the
autocovariances alone. It is computed on the same data it is scored on, so it is
an upper bound on any linear rule rather than an achievable IC; and the same
statistic is computed on the null, because 96 free parameters extract something
from noise.

| `q` | in-sample IC | null IC | excess | break-even | **excess ÷ break-even** |
| ---: | ---: | ---: | ---: | ---: | ---: |
| **2021–23** | | | | | |
| 1 | 0.0399 | 0.0106 | 0.0294 | 0.3698 | **0.079** |
| 4 | 0.0307 | 0.0106 | 0.0201 | 0.1907 | **0.105** |
| 12 | 0.0262 | 0.0104 | 0.0159 | 0.1114 | **0.142** |
| 48 | 0.0164 | 0.0095 | 0.0070 | 0.0562 | **0.124** |
| **2023–25** | | | | | |
| 1 | 0.0325 | 0.0104 | 0.0221 | 0.3939 | **0.056** |
| 4 | 0.0249 | 0.0104 | 0.0145 | 0.1999 | **0.073** |
| 12 | 0.0285 | 0.0099 | 0.0186 | 0.1163 | **0.160** |
| 48 | 0.0162 | 0.0095 | 0.0067 | 0.0587 | **0.113** |

**Short by 6 to 18×, at every horizon.** Even crediting the whole in-sample fit —
noise included — the ratio only reaches 0.083 to 0.292. This does not depend on
the lag-1 story, on the microstructure reading, or on any model of what the
structure is; it uses the measured autocovariances and nothing else.

The earlier document's headline, "short by a factor of 11 to 120", is
**withdrawn**. It rested on `ρ₁/q`, which is the correlation between adjacent
non-overlapping `q`-blocks — the IC of one specific suboptimal rule, not of the
best one available at that horizon — and it mixed the best case of one panel with
the worst of the other. The correct shortfall is roughly flat in `q`, because a
lag-1 term pays a fixed expected gross per round trip whatever the holding period.

## 8. B′-2 — the retrace geometry

The pre-registered statistic is the **retrace fraction**: the maximum move back
toward the reference over the observation window, divided by the realised
excursion.

| panel | `k` | anchors | real − null | `z` | clauses passed | survives |
| --- | ---: | ---: | ---: | ---: | --- | :---: |
| 2021–23 | 1.5 | 5,081 | +0.0514 | +4.70 | 3 of 5 — below the 0.05 floor on the other panel | no |
| 2021–23 | 2.0 | 1,409 | +0.0658 | +2.97 | **5 of 5** | **yes** |
| 2021–23 | 3.0 | 201 | +0.1473 | +3.16 | **5 of 5** | **yes** |
| 2023–25 | 1.5 | 5,511 | +0.0482 | +3.76 | — | no |
| 2023–25 | 2.0 | 1,826 | +0.0928 | +5.57 | **5 of 5** | **yes** |
| 2023–25 | 3.0 | 350 | +0.1565 | +5.70 | **5 of 5** | **yes** |

All five clauses were evaluated for the first time this round. Clause 3 — the day
trim — now applies to `real − null` rather than to the real median alone, and
holds. Clause 4 — bloc confinement — needed a JPY / non-JPY split that did not
previously exist for B′-2 at all; both blocs carry the same sign in every
surviving cell (`k = 2.0`: JPY +0.081 / +0.120, non-JPY +0.063 / +0.075;
`k = 3.0`: JPY +0.068 / +0.206, non-JPY +0.183 / +0.133). Family-max over the
whole B′-2 family gives `p = 0.024` on both deciding panels — which is `1/41`, the
floor for 40 draws, and therefore a ceiling on what this study can claim; see §10.

### 8.1 Why it does not establish anything

**The anchor populations differ, and they differ in the direction that produces
the result.** From `post_hoc_diagnostics.json` at `k = 2.0`:

| | 2021–23 real / null | `z` | 2023–25 real / null | `z` |
| --- | --- | ---: | --- | ---: |
| median bars to anchor | 5.0 / 7.1 | −3.74 | 3.0 / 5.0 | −3.65 |
| median excursion (σ) | 5.92 / 6.75 | −2.94 | 5.29 / 5.98 | −3.45 |
| median scaled excursion | 2.242 / 2.181 | +6.96 | 2.325 / 2.232 | +7.47 |

Real excursions form **faster** and are **smaller** in σ. The retrace fraction
divides by that excursion, so a smaller denominator raises the fraction for the
same absolute retrace — which is the sign observed.

The check is the same statistic with no excursion in its denominator, the **median
retrace in σ units**:

| `k` | 2021–23 | 2023–25 | 2025 |
| ---: | --- | --- | --- |
| 1.5 | +0.074 (z +1.34) | +0.096 (z +1.47) | +0.026 (z +0.21) |
| 2.0 | +0.214 (z +1.09) | +0.209 (**z +1.96**) | +0.163 (z +0.41) |
| 3.0 | +1.119 (z +1.50) | +0.681 (z +1.26) | +0.135 (z +0.18) |

**Positive in all nine cells and significant in none.** The direction is
consistent — real paths do retrace more — and the magnitude is not separable from
the null once the denominator is removed. Combined with §2's point that these are
second-look numbers, B′-2 corroborates B′-1's direction and establishes nothing on
its own.

### 8.2 How much of it needs volatility clustering

The plan registered a secondary IID null for exactly this question and the first
version never ran it. Against N1, which destroys clustering as well as direction,
the same differences are two to three times larger:

| `k` | 2021–23 N2 / N1 | 2023–25 N2 / N1 |
| ---: | --- | --- |
| 1.5 | +0.051 / +0.149 | +0.048 / +0.176 |
| 2.0 | +0.066 / +0.175 | +0.093 / +0.240 |
| 3.0 | +0.147 / +0.260 | +0.157 / +0.313 |

So roughly **two-thirds of the retrace effect measured against an IID null is
volatility clustering**, not direction. That is what the secondary null was
registered to say.

### 8.3 B′-HTF

`HTF_GEOMETRY_CONTEXT_DIFFERENCE_REPRODUCES` in sign, and it is a diagnostic with
**no null and no error bars** — `b2_htf_context.json` holds conditional medians
and raw differences only. The plan under-specified it. Nothing is built on it.

## 9. B′-4 — monthly TSMOM

Six cells, `lookback ∈ {1, 2, 3}` months × `hold ∈ {1, 3}` months, phase-averaged
over eight offsets. **Gross** pips per pair, before cost:

| cell | 2021–23 | 2023–25 |
| --- | ---: | ---: |
| lb1 h1 | −573.0 | −526.8 |
| lb1 h3 | −442.4 | −431.0 |
| lb2 h1 | −397.0 | −678.7 |
| lb2 h3 | −237.6 | −578.4 |
| lb3 h1 | −313.0 | −577.9 |
| lb3 h3 | **+54.4** | −646.4 |

Eleven of twelve cells are negative before cost, and the twelfth disagrees across
panels. Family-max two-sided `p = 0.3227` and `0.3106`; every per-cell `t` lies in
`[−1.571, +0.104]`.

`MONTHLY_TSMOM_NOT_SUPPORTED_IN_EXISTING_PRICE_HISTORY`. The sample is about seven
non-overlapping observations per pair against 3.5–4.8 effective independent pairs,
so this is an **underpowered null result, not a refutation of monthly momentum** —
and the earlier document's gloss that the negative gross is itself "a monthly
reversion consistent with §6" is **withdrawn**. A uniformly negative point estimate
with an interval spanning zero is the error this programme recorded in the
momentum round; it is not evidence of the opposite sign.

## 10. Deviations from the pre-registration

Recorded whether or not they change a result. Three were found by review roles and
none was disclosed in the first version.

1. **The primary null did not meet its own specification** (§2). The largest
   deviation, corrected, and the reason B′-2's numbers are second-look.
2. **The variance-ratio estimator is non-overlapping.** Plan §4.1 registers "the
   standard **overlapping**-window estimator"; the code uses non-overlapping blocks
   and says so in its docstring, but neither amendment covers it and the first
   version of this document never mentioned it. It is conservative for the
   headline — wider null bands — and it costs the most power at long `q`, which is
   where the round wants to be able to say the signal is *absent*. At `q = 480` it
   uses about 104 blocks per pair against roughly 50,000 overlapping windows.
3. **Draw counts below `NULL_DRAWS = 200`.** B′-1 uses 200. B′-2 uses 40, its bloc
   split 40 and the anchor-population comparison 20, because each draw re-runs the
   anchor detector over every pair. The consequence is concrete: B′-2's family-wise
   `p` cannot go below `1/41 = 0.024` however strong the effect is, so §8's
   `p = 0.024` is a **ceiling artefact of the draw count**, not a measurement.
4. **The B′-2 family is larger than registered.** The plan names five statistics
   per threshold, or 15 cells; `against_null` reports ten and the family-max runs
   over 29–30 cells. More conservative than registered, and recorded rather than
   trimmed.
5. **Plan §4.1's stated reason for the about-zero second moment is backwards.** It
   says taking the mean of squares about zero prevents a drift estimate leaking in.
   It does the opposite: with drift `µ`, `VR(q) = (σ² + qµ²)/(σ² + µ²)`, which
   *rises* in `q`. The null destroys the drift, so this biases `real − null` upward
   on the real side only — conservative for a `VR < 1` finding, but it inflates
   long-horizon real `VR`, and §6.1's positive JPY cell at `q = 192` is plausibly a
   USDJPY-trend artefact for this reason.
6. **`sigma_normalised_returns` divides by a rolling `.std()`** — which subtracts
   the rolling mean — while `variance_ratio` takes its second moment about zero.
   Measured: the two sigma paths differ by a median factor of 0.99992, 1–99
   percentile 0.9937–1.0072. Immaterial, since `VR` is a ratio of two variances of
   the same series, and left uncorrected because changing a statistic after seeing
   its result is what this round exists to avoid.
7. **Clause 3's registered wording was not what the first version ran.** It trims
   the ten largest-contributing anchor **days**; the first version trimmed anchors
   by retrace fraction and applied the trim to the real median alone, which cannot
   test `real − null`. Corrected.

## 11. Verification

* **`tests/research` — 161 tests, all passing**, of which 49 cover Round B′: the
  original 30 plus 19 in `test_round_b_prime_hardening.py`.
* **Mutation testing.** A review role mutated the round's source 23 ways and **14
  survived**; eight of the original tests assert on source text or docstrings, and
  one imported `DECIDING_PANELS` from `round_a` rather than from the driver, so it
  checked a different object than the code used. Re-measured after the hardening
  pass: **23 of 23 mutations killed**, including a null that flips 5% of bars, a
  driver that lets 2025 decide, a verdict that reaches the post-hoc diagnostics
  through an alias, a volume inventory that opens an archive file, and both dropped
  `.shift(1)` calls that prefix-stability tests cannot see.
* **`content_read_performed` is now a measurement, not a literal.** The inventory
  wraps `open` and `Path.open` for the duration of its own call and reports what
  was opened; a test opens a real archive file inside it and asserts the flag
  flips.
* `ruff format --check`, `ruff check`, `tools/lint/run_custom_checks.py` — clean.
* Every number in this document was verified against the artifacts
  programmatically.

Known, unrelated and pre-existing: the full `pytest tests/` suite crashes on
Windows from `sys.addaudithook` accumulation in `isolation.py`. Reproduced with
this branch stashed. It is a separate referral and is not mixed in here.

## 12. Case A, and what it does and does not license

`PRICE_PATH_STRUCTURE_SURVIVES_NULL_CONTROL`. Plan §11's consequence is that "a
later round designs labels that harvest *that* structure". Two things bound what
that can mean, and neither is a reason to record a different case.

* **Fixed-horizon linear rules are closed.** §7.2's bound uses the measured
  autocovariances and nothing else, is computed in-sample, and still reaches only
  6–16% of break-even at every horizon from one bar to twelve hours. There is no
  linear rule on a fixed horizon in this structure that pays a round trip. That
  also explains the four earlier rounds rather than merely adding to them: Rounds
  1, 2 and both replications measured block-level ICs at 24 hours to 5 days and
  found the sign unstable, and the achievable IC there is a fraction of a percent.
  The instability was sampling noise around approximately zero.
* **Path-shaped rules are not closed, and not established either.** §7.2 bounds
  linear predictors of a fixed-horizon move; a first-passage or excursion-anchored
  label is a different object and is not covered by it. B′-2 is the round's only
  measurement of that object, and §8.1 shows its pre-registered statistic is mostly
  a denominator effect while the denominator-free version is positive everywhere
  and significant nowhere.

So the honest position is that the round found real structure, closed the family of
rules it can bound, and left one family open with weak, second-look,
direction-consistent evidence. **Round B′ stops at the classification.** It does
not start a label round, a TP/SL grid, a classifier or any ML, and Case A is not
authority to begin one — the next round is designed, not begun.

## 13. Referrals

1. **The information-source decision**, to human + ChatGPT. Price alone has now
   been screened three ways across four rounds. The ordering this round would
   propose is carry first, then the economic calendar, then COT, then implied
   volatility — with **tick volume noted as already in the repository** and the
   cheapest of them to evaluate. Nothing has been acquired and no download has been
   made.
2. **Tick volume**,
   `TICK_VOLUME_INFORMATION_INVENTORY_CONFIRMED_PENDING_SEPARATE_AUTHORISED_RESEARCH`.
   The archive writer emits a `volume` field; `bars.read_m1` copies only the eight
   `PRICE_KEYS` and discards it, so no M15 cache has it. Recovering it needs a
   content read of **already-seen** spans — not a new span — and is therefore its
   own authorisation. The manifest carries no per-field statistics, so whether the
   field is populated cannot be judged from metadata. No content was read. The
   first question, if it is ever authorised, is whether tick volume is close to a
   deterministic function of spread and realised volatility.
3. **B′-2 at full draw count.** Its family-wise `p` is pinned at the `1/41` floor by
   40 draws (§10.3). If the path-shaped family is pursued, that study needs
   `NULL_DRAWS = 200` and a pre-registered σ-level statistic — the confound-free
   one — as its primary, not the fraction.
4. **The Windows `sys.addaudithook` crash** in `tests/isolation.py`, pre-existing
   and unrelated. Not mixed into this round.

## 14. Status

* `TRACK_A_RESEARCH_PROGRAM_ROUND_B_PRIME_COMPLETED`
* `PRICE_PATH_STRUCTURE_SURVIVES_NULL_CONTROL` (Case A)
* `NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
* `PRODUCTION_READINESS_NOT_CLAIMED`
* Zero new market-data reads. The fresh pool, the historical OOS slice, the dead
  window and the future untouched epoch were not read.
