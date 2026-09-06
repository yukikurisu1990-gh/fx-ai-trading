# M15 Research Program — Round B′: results

**`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `PRODUCTION_READINESS_NOT_CLAIMED`.**

Plan: `docs/research/m15_round_b_prime_plan.md`, committed at `d5cd618` **before
any research statistic was computed**, amended twice before any real statistic at
`ccafebc` and `1b1a3ae`. Base master `0f3300a` (the PR #468 merge).

**Final classification: Case C —
`PRICE_ONLY_PATH_STRUCTURE_SCREEN_NEGATIVE`**, in its most informative form: the
screen did not fail to find structure. It **found structure, measured it, and
found it short of tradable by a factor of 11 to 120.**

`TRACK_A_RESEARCH_PROGRAM_ROUND_B_PRIME_COMPLETED`.

---

## 1. The answer

**There is real, strongly replicating serial structure in the M15 price path.
It lives at the one-bar scale, it is a quoting effect, and it is unharvestable.**

The variance ratio is below 1 at every horizon on every panel, stably across the
two deciding panels, with studentized effects reaching **−14.7**. That is not
noise and it is not the artefact Round A fell into — the nulls were sanity-checked
against a generated random walk first, and the primary null preserves `|r_t|` at
every bar so volatility clustering is identical on both sides.

Three post-hoc diagnostics then say what it is:

* **it vanishes when the base return is coarsened.** At the same total horizon of
  48 bars, `VR` goes `0.9257` (1-bar base) → `0.9823` (4-bar) → **`1.0031`**
  (12-bar). At a 3-hour base, **no cell has a deficit on both deciding panels**;
* **an MA(1) at lag 1 explains 60–149%** of the deficit at every horizon;
* **the implied block-level predictability is 0.07%–3.3% against break-evens of
  5.6%–37%** — short by 11× at one bar and by 120× at 48 bars.

B′-2's single surviving cell is the same phenomenon seen from the other side: its
anchors form in a **median of 3 bars** with a 12-bar observation window, and the
real and null anchor populations differ on **every** axis measured
(`z` from −5.9 to −15.5), so the pre-registered comparison is not comparing like
with like. B′-4 is cleanly negative. B′-HTF reproduces only inside the same
contaminated cells and flips sign at `k = 3.0`.

## 2. Identity

| | |
| --- | --- |
| PR #468 | merged, merge commit **`0f3300a00cf0fdc79e3efb892cd1a491afe035f1`** |
| verified before merge | head `b5d8cb7` matched, CI green, `MERGEABLE`/`CLEAN`, no unresolved review comment |
| pre-registration | `d5cd618`, before any statistic; amendments `ccafebc`, `1b1a3ae`, both before any **real** statistic |
| panels | `2021-04-26…2023-04-25` (624 days) · `2023-04-26…2025-04-24` (624) · `2025-04-25…2025-12-28` (212) |
| declared vs measured span | identical on all three |
| pairs / bars | `PAIRS_20` · 999,238 + 993,878 + 335,200 |
| **new market-data reads** | **zero** |
| fresh pool `2016-06-02…2021-04-25` | **untouched** |

## 3. The two pre-registration defects found and fixed before any real statistic

Both were caught by arithmetic on generated data, with no panel touched, and both
made the test **harder**.

**`ccafebc` — the registered primary null was degenerate.** A 5-day *block* sign
flip leaves every path inside a block untouched, so the variance of any `q`-bar
sum below the block length is unchanged and the null returns the real value
exactly. On a synthetic AR(1) with `φ = −0.10`:

| `q` | real | block flip *(registered)* | per-bar flip *(amended)* |
| ---: | ---: | ---: | ---: |
| 2 | 0.8959 | **0.8959** | 1.0005 |
| 96 | 0.8477 | **0.8477** | 1.0014 |
| 480 | 0.7912 | **0.7912** | 1.0016 |

A null that reproduces the statistic to four decimals cannot reject anything.

**`1b1a3ae` — the retrace window was 37× the excursion.** A `1.5σ` anchor forms
in a median of 13 bars on the generated walk, so a flat 480-bar window measures
the window rather than the retrace: median fraction 2.33, `reached_50` saturated
at 0.86. Amended to `min(4 × bars_to_anchor, 480)`, which gives 0.756 and 0.664 on
the same walk and restores the scale the pre-registered 0.05 economic floor was
written for.

**Two detector properties were recorded rather than changed**, because changing
them after seeing counts would be tuning: the `√elapsed` threshold times out on
about 16% of searches, consuming roughly 70% of the series; and `k = 3.0` yields
about 6 anchors per 60,000 bars, so that cell was expected to be undecidable — and
was.

## 4. Null sanity — run before any real comparison

Each null on a generated IID Gaussian random walk, 40,000 bars, 40 draws. Every
one must return `VR ≈ 1`:

| `q` | walk itself | N1 iid | **N2 sign flip** | N3 weekday | N2 sd |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 2 | 1.0067 | 1.0027 | **1.0013** | 0.9981 | 0.0076 |
| 48 | 1.0339 | 1.0064 | **1.0055** | 1.0062 | 0.0521 |
| 192 | 0.9629 | 0.9976 | **1.0078** | 1.0091 | 0.0973 |
| 480 | 1.1391 | 0.9948 | **0.9964** | 0.9886 | 0.1535 |

No horizon fails. The null contracts were also measured directly: **only N2 has
`|r_t|` identical bar by bar**, which is the property that makes a real-minus-N2
difference attributable to direction rather than to clustering.

## 5. B′-1 — the variance ratio

Real `VR(q)`, the primary null's mean, and the studentized difference:

| `q` | 2021–23 | 2023–25 | 2025 |
| ---: | --- | --- | --- |
| 2 | 0.9665 (**z −13.76**) | 0.9768 (z −9.81) | 0.9620 (z −10.34) |
| 4 | 0.9413 (z −14.69) | 0.9601 (z −9.97) | 0.9448 (z −7.73) |
| 12 | 0.9225 (z −11.40) | 0.9382 (z −9.18) | 0.9161 (z −8.30) |
| 48 | 0.9257 (z −6.62) | 0.9410 (z −5.43) | 0.9032 (z −5.48) |
| 96 | 0.9527 (z −3.14) | 0.9339 (z −4.47) | 0.8852 (z −4.84) |
| 192 | 0.9552 (z −2.08) | 0.9233 (z −3.40) | 0.8134 (z −5.53) |
| 480 | 0.8748 (z −3.69) | 0.9391 (z −1.66) | 0.7196 (z −5.44) |

**Stable on both deciding panels at `q ∈ {2, 4, 12, 48, 96, 192}`.** N1 and N3
give nearly identical differences, so this is not a calendar or weekend-gap
artefact. By the plan's §4.5 the kill condition is **not** met.

The effect is in every bloc and every sub-period: `b1_bloc_split.json` and
`b1_temporal_stability.json` carry the JPY / non-JPY and four-block breakdowns.
This is the most robust measurement this programme has produced.

## 6. What it is — `POST_HOC_DIAGNOSTIC_ONLY`

None of the three nulls controls for microstructure: all of them destroy serial
dependence, so bid-ask bounce and genuine reversion both appear as
`real − null < 0`. That is a gap in the pre-registration and these diagnostics
close it. **They cannot carry a verdict** (plan §10); they are reported because
reporting §5 without them would be reporting less than is known.

### 6.1 The deficit is a one-bar effect

`VR` at the same total horizon, assembled from different base units:

| total bars | base 1 | base 4 | **base 12** |
| ---: | ---: | ---: | ---: |
| 48 (2021–23) | 0.9257 | 0.9823 | **1.0031** |
| 24 (2021–23) | — | 0.9728 | **1.0082** |
| 144 (2021–23) | — | — | **1.0059** |
| 24 (2023–25) | — | 0.9742 | **0.9901** |
| 144 (2023–25) | — | — | 0.9602 |

**At a 3-hour base unit, no `(base, q)` cell shows a deficit on both deciding
panels.** The 2021–23 base-12 row is 1.008 / 1.003 / 1.006 / 0.945 and the
2023–25 row is 0.990 / 1.003 / 0.960 / 1.001 — they disagree in sign at every
horizon. The monotone progression 0.926 → 0.982 → 1.003 at a fixed 48-bar total
is the signature of an effect that lives at the sampling frequency.

### 6.2 A lag-1 model explains most of it

`ρ₁ = VR(2) − 1` is **−0.0335** (2021–23) and **−0.0232** (2023–25). Under an
MA(1) with only that lag, `VR(q) = 1 + 2ρ₁(1 − 1/q)`:

| `q` | 2021–23 explained by lag 1 | 2023–25 |
| ---: | ---: | ---: |
| 12 | — | 68.9% |
| 48 | — | 77.1% |
| 96 | — | 69.5% |
| 192 | 148.9% | 60.2% |
| 480 | 53.4% | 76.0% |

### 6.3 It cannot pay for a round trip

If the deficit is the lag-1 effect §6.1 and §6.2 say it is, then the correlation
between adjacent non-overlapping `q`-blocks is `ρ₁ / q` — one lag-1 covariance
spread across a `q × q` block. Against the break-even IC, `cost / sd(q-bar move)`:

| `q` | break-even IC | achievable block IC | **ratio** |
| ---: | ---: | ---: | ---: |
| 1 | 36.98% | 3.35% | **0.091** |
| 2 | 26.61% | 1.67% | 0.063 |
| 4 | 19.07% | 0.84% | 0.044 |
| 12 | 11.14% | 0.28% | **0.025** |
| 48 | 5.62% | 0.07% | **0.012** |

*(2021–23; the 2023–25 ratios run 0.059 to 0.008.)*

**Short by a factor of 11 at one bar and 120 at 48 bars.** A deliberately
generous bound — crediting the *whole* variance deficit to one predictable
component, `√|VR(q) − 1|` — reaches 2.5× break-even at `q = 12`, and is reported
in `post_hoc_diagnostics.json` so the generous reading is visible. It is not
achievable: §6.1 and §6.2 say the deficit is a single lag-1 term, and a lag-1
term traded at `q = 12` gives `ρ₁/12`, not `√|VR−1|`.

### 6.4 One inconsistency in the statistic, measured and left alone

`sigma_normalised_returns` divides by a rolling **`.std()`**, which subtracts the
rolling mean, while `variance_ratio` takes its second moment **about zero**. A
sign flip changes the rolling mean slightly, so the null's normalisation is not
bit-identical to the real one. Measured: the ratio of the two sigma paths has a
median of **0.99992** and a 1–99 percentile range of **0.9937–1.0072**.

It is immaterial — `VR` is a ratio of two variances of the *same* normalised
series, so a uniform rescaling cancels exactly and only second-order
time-variation survives — and it is **not corrected here**, because changing a
statistic after seeing its result is the thing this round exists to avoid. It is
recorded so a later round can make the two conventions agree from the start.

## 7. B′-2 — the retrace geometry

| `k` | 2021–23 | 2023–25 | 2025 | verdict |
| --- | --- | --- | --- | --- |
| 1.5σ | −0.0717 (z −5.61) | −0.0804 (z −4.95) | −0.0731 (z −2.38) | **survives** all three clauses |
| 2.0σ | −0.0195 (z −0.74) | +0.0009 (z +0.04) | +0.0225 | sign disagrees, effect absent |
| 3.0σ | +0.0902 (z +1.78) | +0.0991 (z +2.89) | +0.0791 | sign agrees, `|z| ≥ 2` fails |

Anchor counts: 5,081 / 5,511 / 1,230 at `k = 1.5`; 201 / 350 / 59 at `k = 3.0` —
the thinness the plan predicted.

Note the direction. The surviving cell shows **less** retrace than the null, which
is *continuation*, and B′-1 shows mean reversion. Those look contradictory, and
the resolution is that neither is what it appears to be.

### 7.1 The surviving cell is confounded — `POST_HOC_DIAGNOSTIC_ONLY`

The retrace fraction divides by the realised excursion, and the detector fires at
different places on the real series and the null. Comparing the anchor
**populations** at `k = 1.5`:

| | real | null | `z` |
| --- | ---: | ---: | ---: |
| anchors | 5,081 | 4,985 | +0.62 |
| median bars to anchor | 3 | 4 | — |
| median excursion (σ) | 3.799 | 4.104 | **−5.91** |
| median scaled excursion | 1.783 | 1.728 | **+10.35** |
| median adverse extension (σ) | 3.240 | 4.208 | **−15.46** |

*(2021–23; 2023–25 gives −4.63, +6.42, −15.92 on the same three.)*

**The populations differ on every axis except their count.** Real excursions are
smaller (a smaller denominator), real paths extend less far (a smaller numerator),
and real anchors overshoot their threshold by more. A retrace-fraction difference
computed across two populations that differ this much is not a statement about
path shape.

And the scale settles it: **a median of 3 bars to anchor with a 12-bar
observation window** is 45 minutes measured over 3 hours — inside the zone where
§6.1 shows the whole variance-ratio effect lives, and outside any zone where a
2.5-pip round trip can be paid.

### 7.2 Weekend gaps, tails, and same-bar ambiguity

At `k = 2.0`: 1,399 of 1,409 anchors are continuous-path (median retrace 0.673)
against 10 weekend-gap anchors (0.749) on 2021–23, and 1,807 against 19 on
2023–25. **The result does not live in the gap subset.** Trimming the ten largest
or ten smallest anchors moves the median by under 0.007.

`ambiguous_bars` is 877 of 1,409 — **and that figure is an upper bound, not a
measurement**. The implemented test counts every anchor whose continuation
maximum happens to fall on the retrace-reaching bar, which is far broader than a
genuine within-bar ordering ambiguity. The conservative adverse-first rule is
applied correctly; the count reported should be read as "at most this many".

## 8. B′-HTF

| context | states | 2021–23 | 2023–25 | reproduces |
| --- | --- | ---: | ---: | --- |
| `htf_trend` | aligned − mixed | +0.072 / +0.071 / +0.010 | +0.023 / −0.052 / −0.130 | only `k = 1.5` |
| `htf_location` | middle − outer | −0.083 / −0.012 / −0.190 | −0.068 / −0.010 / +0.146 | `k = 1.5`, `2.0` |

By the plan's §6 the kill condition is not met — a sign difference reproduces.
But it reproduces **only in the cells §7.1 shows are confounded**: at `k = 1.5`
where the anchors are 3 bars long, and at `k = 2.0` where the differences are
−0.012 and −0.010, an order of magnitude below the 0.05 floor the plan set for
B′-2. At `k = 3.0` both contexts flip sign between panels. HTF context adds
nothing that is not already explained by the microstructure zone.

## 9. B′-4 — monthly TSMOM

Six cells, unchanged cost model, phase-averaged over eight offsets.

| cell | 2021–23 gross / net | 2023–25 gross / net | 2025 net |
| --- | ---: | ---: | ---: |
| lb1m h1m | −573.0 / −613.0 | −526.8 / −565.4 | +140.7 |
| lb1m h3m | −442.4 / −455.7 | −431.0 / −442.3 | +173.5 |
| lb2m h1m | −397.0 / −422.3 | −678.7 / −705.2 | +243.4 |
| lb2m h3m | −237.6 / −249.8 | −578.4 / −591.0 | +283.2 |
| lb3m h1m | −313.0 / −333.4 | −577.9 / −599.3 | +315.0 |
| lb3m h3m | **+54.4 / +43.2** | −646.4 / −659.8 | +252.9 |

**Gross is negative in five of six cells on both deciding panels**, and the sixth
disagrees in sign between them. Turnover is 2.3–12.4 per year and cost is 2.6–38.6
pips per pair, so cost is not the explanation — the direction is wrong before it.
Studentized family-max over the six: `p = 0.32` (2021–23) and `p = 0.31`
(2023–25). 2025 is positive in all six and is not a deciding vote.

`MONTHLY_TSMOM_NOT_SUPPORTED_IN_EXISTING_PRICE_HISTORY`. Note that a negative
monthly *momentum* gross is a monthly *reversion*, consistent with §5's `VR < 1`
— and equally unharvestable for the same reason.

The sample was stated in the plan before the run and holds: 8.2–24.7
non-overlapping observations per pair, about five effective independent pairs.
This screen could only ever have detected a large effect.

## 10. B′-VOL — inventory, no content read

* **The field exists.** `scripts/fetch_oanda_candles.py` emits
  `{"time": ..., "volume": int(c.get("volume", 0)), ...}` per record.
* **The research reader drops it.** `bars.read_m1` copies only the eight
  `PRICE_KEYS` out of each decoded row, so `volume` is parsed and discarded before
  `to_m15` sees it. All three routes share that reader, so no M15 cache has a
  volume column or any aggregate of one.
* **Recovery needs a content read but no new span.** The already-seen spans would
  be re-decoded. That is a re-read of `EXPLORATORY_SEEN_DATA` — the spans cannot
  become unseen — but it is still a market-data content read and therefore its own
  authorisation.
* **Coverage cannot be judged from metadata.** The manifest carries `row_count`,
  `first_time`, `last_time` and `sha256` per file but **no per-field statistics**,
  so whether `volume` is *populated* rather than merely present in the schema is
  not knowable without reading.

**No market-data content was read.** Referral:
`TICK_VOLUME_INFORMATION_INVENTORY_CONFIRMED_PENDING_SEPARATE_AUTHORISED_RESEARCH`.
The first question if it is ever authorised: **is tick volume close to a
deterministic function of spread and realised volatility, or does it carry
information neither has?** Nothing downstream is worth designing until that is
answered.

## 11. Interpretation

**Is there structure a matched null cannot produce?** Yes, unambiguously — and
this is the first time this programme has been able to say that. `VR < 1` at
`z = −14.7`, replicating across both deciding panels, every bloc and every
sub-period, against a null that holds volatility clustering exactly fixed.

**Is it worth anything?** No. It lives at the sampling frequency, disappears at a
3-hour base, is explained by a single lag-1 term, and delivers a block-level
predictability 11–120× below break-even. It is the price of the quote, not an
edge in the market.

**How does this fit the fixed-lag direction failures?** It explains them. Rounds
1, 2, the supplemental replication and the momentum round all measured
block-level ICs at 24-hour to 5-day horizons and found them unstable in sign. §6.3
says why: whatever aggregate reversion the variance ratio detects is a one-bar
term whose block-level projection at those horizons is **0.03%–0.28%** — far
below the noise in any 624-day estimate. The sign instability those rounds saw
was not a failure to find the effect. It was sampling noise around approximately
zero, which is what the effect is at those horizons.

**Is there a basis to proceed to first-passage / retrace label research?** **No.**
The one cell that survived the pre-registered screen is confounded on every
measured axis of its own anchor population, sits at a 45-minute scale, and points
the opposite way to B′-1. Designing labels to harvest it would be designing labels
to harvest the bid-ask bounce.

**Is HTF context worth keeping?** No. It reproduces only inside the confounded
cells and flips sign at `k = 3.0`.

**Is monthly directional research worth keeping?** No. Gross is negative before
cost in five of six cells on both deciding panels.

**What price-only room is left?** On the evidence of Rounds 1, 2, the two
replications, A and B′: **very little at tradable horizons.** Round A established
that the opportunity metric is a `√H` identity and that break-even needs an IC of
1.7%–5% at 12h–5d. Round B′ establishes that the only serial structure the data
contains at all is a one-bar term worth 0.03%–0.28% at those horizons. Those two
numbers together are close to a closure argument, and §12 states it as one.

## 12. Final classification — Case C

**`PRICE_ONLY_PATH_STRUCTURE_SCREEN_NEGATIVE`.**

**Why not Case A**, whose literal trigger fired. Case A requires "a stable,
**non-negligible** real-vs-null difference", and its consequence is "a later round
designs labels that harvest *that* structure". The difference is stable and it is
not negligible statistically — but the plan **gave B′-1 no economic floor**, which
is a defect in my pre-registration of exactly the kind Round A's condition 6 was.
Supplying the floor that was missing — Round A's own break-even IC, established in
a previous round rather than invented now — the effect is 11–120× too small, and
Case A's consequence is void: there is nothing to harvest. B′-2's survivor cannot
rescue it, being confounded on every axis and living at 45 minutes.

**Why not Case B.** B′-4 is negative on both deciding panels before cost.

**Why not Case D.** Nothing prevented a verdict. The nulls were sanity-checked,
the detector was validated for causality and window semantics before the panels
were touched, and the effect sizes are measured rather than uncertain. `k = 3.0`
was undecidable, as the plan predicted, and it does not change the answer.

**The honest statement of the negative**, which is stronger than Case C's original
wording:

> For price and spread-derived information, across the directional, conditional,
> path-geometry and monthly-scale formulations this programme has tested, the only
> serial structure the M15 series contains that survives a matched null is a
> one-bar quoting effect worth **0.03%–3.3%** of block-level predictability against
> break-evens of **5.6%–37%**. No edge-generating structure was found at any
> horizon where the spread can be paid.

## 13. Referral — the information-source decision

Round B′ does **not** acquire anything and does not choose. It refers the decision
to human + ChatGPT, with the candidates in the order this programme's evidence
supports:

1. **carry / interest-rate differential** — the most documented FX factor, a
   genuine economic prior rather than a data-mined one, low turnover, and
   orthogonal to price path;
2. **economic calendar** — an *exogenous* event anchor, which is the one thing
   that would fix the selection bias every price-derived event definition carries;
3. **COT positioning** — weekly, so its frequency matches the effective sample
   this corpus actually has;
4. **implied volatility** — a risk-premium channel, and the only candidate here
   that bears on the non-directional side.

**Already in the repository and unused: tick volume** (§10). It is the cheapest
of all of these to evaluate and needs an authorised re-read rather than an
acquisition.

None is started. No data is downloaded, no vendor is contacted, no scope is
widened.

## 14. Status

* `TRACK_A_RESEARCH_PROGRAM_ROUND_B_PRIME_COMPLETED`
* `NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
* fresh historical pool `2016-06-02 … 2021-04-25` **untouched**
* `EXPLORATORY_OOS_SLICE`, dead window and forward epoch **not read**
* Formal Confirmation **not performed**; `PRODUCTION_READINESS_NOT_CLAIMED`
* No candidate frozen, no strategy built, no label predicted, no model fitted, no
  gate created, no data acquired.

Round B′ stops here. Label research, ML, fresh replication and any new data
source are each their own later decision and none is started.

## 15. Artifacts

`python -m scripts.research.round_b_prime.driver` writes every JSON under
`artifacts/track_a_scratch/round_b_prime/` (gitignored, as every previous round's
were): `b1_null_sanity` first, then `panels`, `b1_variance_ratio`, `b1_verdict`,
`b1_bloc_split`, `b1_temporal_stability`, `b2_retrace_geometry`, `b2_verdict`,
`b2_subsets`, `b2_htf_context`, `b4_monthly_tsmom`, `b4_verdict`,
`b4_familywise`, `post_hoc_diagnostics`, `bvol_inventory` and
`round_b_prime_summary`. Every number in this document comes from them.
