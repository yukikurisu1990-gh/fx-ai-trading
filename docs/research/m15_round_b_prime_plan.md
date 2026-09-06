# M15 Research Program — Round B′: the pre-registered plan

**`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `PRODUCTION_READINESS_NOT_CLAIMED`.**

**Committed before a single research statistic is computed.** Every horizon,
threshold, null construction, tie-break, family boundary and kill condition below
is fixed here and may not be changed after a number is seen. Round A's own
post-mortem is the reason: its headline statistic turned out to be an identity a
random walk scores higher on, and the only defence against repeating that is to
write the null down before the measurement.

Base master: `0f3300a00cf0fdc79e3efb892cd1a491afe035f1` (the PR #468 merge).

---

## 1. The question, and why it comes before labels

Round A closed the direction question at fixed lags: unconditional sign is
unstable across three periods, and a bounded conditional screen over five state
families passed **0 of 39** cells with a measured false-positive rate of 0.227.
It also established the reason a naive geometry study would fail: **`median MFE /
cost` is essentially `1.1 · (σ/cost) · √H`**, and an IID shuffle of the same bars
scores *higher* than the real market on it at every horizon.

The obvious next step — redesign the label as a first-passage / TP-before-SL
problem — inherits that trap twice over. A barrier label is a function of `σ`, so
without a matched null its hit rates measure volatility clustering; and an
asymmetric barrier is a direction choice, so if the sign does not persist neither
does the label's predictability.

So Round B′ asks the prior question:

> **Does the price path contain structure that a matched null cannot produce?**

If it does, the next round can design labels that harvest *that* structure. If it
does not, no label redesign can help and the honest move is to change the
information source rather than the target.

**No strategy is built, no label is predicted, no model is fitted.** Round B′ is
a measurement.

## 2. Data — no new read

The three already-seen panels only, from the existing M15 parquet caches:

| span | days | state |
| --- | ---: | --- |
| `2021-04-26 … 2023-04-25` | 624 | `EXPLORATORY_SEEN_DATA` |
| `2023-04-26 … 2025-04-24` | 624 | `EXPLORATORY_SEEN_DATA` |
| `2025-04-25 … 2025-12-28` | 212 | `EXPLORATORY_SEEN_DATA` |

`PAIRS_20`. **Zero new market-data reads.** The fresh pool
`2016-06-02 … 2021-04-25`, the `EXPLORATORY_OOS_SLICE`, the dead window and the
forward epoch are untouched.

**The two 730-day panels decide.** 2025 has been searched by roughly 1,200
configurations and is known to be anomalous (IC −25% against −5.9% and +2.4%;
19 of 39 Round A cells significant on the shortest panel). It is a consistency
diagnostic and may contradict, never decide.

## 3. Units — σ-normalised throughout

The primary unit is **σ-normalised**: every price move is divided by that pair's
own trailing volatility, measured as `sd(1-bar mid_c difference in pips)` over
`RV_WINDOW = 480` bars, strictly backward-looking. Pips are reported alongside
for economic interpretation, and cost stays in pips (`spread_close_pips + 0.5`,
the unchanged `EXPLORATORY_ASSUMPTION`).

Why: Round 2 measured the JPY bloc at 6.1× the non-JPY one in pips and 3.2× after
volatility normalisation, so about half of the concentration this programme has
repeatedly reported was the unit rather than the economics.

## 4. B′-1 — Null-controlled aggregate path structure

### 4.1 Statistic

The **variance ratio**

```
VR(q) = Var(r_q) / (q · Var(r_1))
```

where `r_1` is the 1-bar σ-normalised mid return and `r_q` the overlapping
`q`-bar return, computed per pair with the standard overlapping-window estimator
and pooled across pairs by simple mean.

`VR(q) < 1` is mean reversion at that aggregation, `> 1` trend, `= 1` a random
walk. It is a **second-moment** statistic on returns — deliberately not a
median-of-excursions statistic, because the latter is the identity Round A
mistook for a finding. `Var` here is the mean of squares about zero rather than
about the sample mean, so a drift estimate cannot leak into it.

### 4.2 Horizons — fixed here

`q ∈ {2, 4, 12, 48, 96, 192, 480}` bars — 30 min, 1h, 3h, 12h, 24h, 48h, 5 days.
**Seven values, no grid.**

### 4.3 The three nulls, and exactly what each preserves and destroys

| null | preserves | destroys | detects |
| --- | --- | --- | --- |
| **N1 IID shuffle** | the marginal distribution of 1-bar returns; the bar count | **all** serial dependence, including volatility clustering | any serial structure at all — but cannot separate clustering from directional dependence |
| **N2 block-preserving sign flip** | the magnitude sequence exactly, so volatility clustering is intact; the calendar | the **sign** ordering, in 5-day blocks with one shared draw | **directional** serial dependence, with clustering held fixed. This is the null that matters |
| **N3 weekday-preserving shuffle** | volatility clustering is not preserved, but each return stays in a slot with the same weekday and the same hour-of-day | serial dependence, but **not** calendar placement | whether the N1 result is an artefact of weekend gaps and session structure rather than of serial dependence |

N2 is the primary null. N1 and N3 exist to say what N2's result is *not*.

**Null sanity**, run before any real-vs-null comparison and reported whatever it
shows: each null is applied to a series generated as an IID Gaussian random walk
with the same length, and `VR(q)` must come out at 1.0 within its own Monte-Carlo
band. A null that does not recover 1.0 on a true random walk is measuring its own
construction, and any real-vs-null difference computed against it is
uninterpretable.

### 4.4 Reported per `q`, per panel

Real `VR`; each null's centre, sd and 95% band; `real − null`; the studentized
effect `(real − null_centre) / null_sd`; JPY / non-JPY split; effective
independent pairs; and stability across four chronological sub-blocks per panel.

### 4.5 Kill condition

If, across the **two 730-day panels**, the sign and rough magnitude of
`real − N2` is not stable at any `q`, record

**`NULL_CONTROLLED_AGGREGATE_PATH_STRUCTURE_NOT_ESTABLISHED`**

and drop the aggregate reversion / aggregation-structure family. A 2025-only
positive is not a deciding vote.

## 5. B′-2 — Excursion-anchored retrace geometry

### 5.1 The anchor — path-based, not clock-based

Every previous round decided on a **clock** grid: the move over the last `L`
bars, re-decided every `H` bars. Round B′ anchors on the **path**: the moment a
cumulative move first reaches `k · σ`, whenever that happens.

Precisely: walking forward, from a reference bar `a` (the last anchor, or the
first usable bar), the excursion at bar `t` is `(mid_c[t] − mid_c[a]) / σ[a]`
where `σ[a]` is the trailing volatility at `a` **scaled to the elapsed horizon**
— `σ[a] · √(t − a)` — so that "1.5σ" means 1.5 standard deviations of a random
walk over the elapsed time, not of a single bar. An anchor fires the first bar
`t` at which `|excursion| ≥ k`, subject to §5.5's timeout. The next anchor's
reference is that bar.

This is the one directional formulation the programme has not tested, and it is
specifically **not** the failed one: it does not require the sign to persist on a
fixed clock lag, only that a completed move be followed by a measurable retrace
shape.

### 5.2 Thresholds — fixed here

`k ∈ {1.5, 2.0, 3.0}`. Three values. **No threshold may be added after the data
is seen.**

`σ` is the same `RV_WINDOW = 480` trailing volatility as §3, in pips per bar,
computed at the anchor's reference bar and never re-estimated inside the window.

### 5.3 What is measured after each anchor

The observation window is `W = 480` bars (5 days) after the anchor bar, fixed.
Let `E` be the realised signed excursion at the anchor, in σ units.

* **retrace fraction** — `max` over the window of the move back toward the
  reference, divided by `|E|`, capped at reporting
* **maximum retrace** reached, and whether the 25 / 50 / 100% retrace levels were
  reached at all
* **time-to-retrace** — bars to first reaching 50% retrace, `NaN` if never
* **continuation before retrace** — how much further the move extends, in σ,
  before the 50% retrace is first reached
* **adverse extension** — the maximum continuation over the whole window
* **timeout behaviour** — the fraction of anchors that reach no retrace level
* the retrace-fraction distribution's 10/25/50/75/90 quantiles

**No net PnL is computed.** These are distributions, not a strategy.

### 5.4 The matched null — the load-bearing part

An excursion anchor is a **selection**: conditioning on "a large move just
happened" makes a subsequent partial retrace likely under a random walk too,
because the anchor is chosen at a local extreme of the sampled path. So the
comparison is not "retrace happened" but "retrace happened more/less/differently
than in a process with the same volatility and the **same anchor-selection
geometry**".

**Null M1 (primary): volatility-preserving sign shuffle.** Take each pair's
1-bar returns, keep their magnitudes in place — so volatility clustering,
calendar placement and the whole magnitude sequence are exact — and randomise
only their signs in 5-day blocks. Then **run the identical anchor detector and
the identical retrace measurement on the result.** The anchor-selection geometry
is therefore reproduced, not assumed away.

**Null M2 (secondary): IID shuffle**, same detector. Destroys clustering as well,
so the M1-vs-M2 difference says how much of any effect needs clustering.

Both nulls are drawn `NULL_DRAWS` times and the real statistic is compared
against the resulting distribution, not against a single draw.

### 5.5 Rules fixed here, so the path is never read favourably

* **Same-bar ambiguity.** M15 OHLC does not say whether the high or the low came
  first within a bar. When a bar could satisfy two conditions, the **adverse one
  is taken as first** — for a long excursion, the low is assumed to precede the
  high. This is the conservative tie-break and it matches the direction the
  programme has used elsewhere. **The count of ambiguous bars is reported.**
* **Weekend gaps.** An anchor or a retrace level crossed by a gap of more than
  one bar's timestamp spacing is tagged and reported **separately** from
  continuous-path cases. A structure that exists only in the gap subset is
  recorded as weak.
* **Anchor timeout.** If no `k · σ` excursion occurs within `ANCHOR_TIMEOUT = 960`
  bars (10 days) of the reference, the reference advances to that bar and no
  anchor is recorded. This bounds the search and is fixed here.
* **Non-overlap.** Consecutive anchors do not share a reference. Overlapping
  observation windows are possible and the effective count is reported as
  `anchors / (W / BARS_PER_DAY)` days of independent information per pair.

### 5.6 Kill condition

Record **`EXCURSION_ANCHORED_RETRACE_GEOMETRY_NOT_ESTABLISHED`** if, on the two
730-day panels, **any** of:

* the sign of `real − M1` on the median retrace fraction is not stable;
* the studentized effect is under 2 in both panels;
* removing the 10 largest-contributing anchor days flips the sign;
* the effect exists only in the JPY bloc or only in the weekend-gap subset;
* the difference is statistically present but economically negligible — defined
  here as a median retrace-fraction difference under **0.05** (5 percentage
  points of the realised excursion).

In that case the first-passage / retrace label family **does not proceed** to a
label round on this evidence.

## 6. B′-HTF — the smallest possible context diagnostic

**Two** context states, fixed here, both from the existing M15 cache:

* **`htf_trend`** — the sign-agreement of the last completed 96-bar and 480-bar
  blocks' returns: `aligned` when both have the same sign, `mixed` otherwise;
* **`htf_location`** — whether the anchor's reference price sits in the outer
  third or the middle third of the trailing 1920-bar (20-day) range.

**Two states each, one comparison each: conditioned retrace geometry against
unconditioned.** No indicator search, no third variable, no interaction.

**Kill condition.** If the context-to-context difference in median retrace
fraction does not reproduce in sign across the two 730-day panels, record
**`HTF_GEOMETRY_CONTEXT_NOT_SUPPORTED`** and drop HTF-conditioned price-only
research.

## 7. B′-4 — monthly TSMOM, one screen, six cells

Every "momentum" this programme has tested is 4–6 days. The FX literature's
time-series momentum is 1–12 months. That octave is untested, has a genuine
prior, and trades rarely enough that cost is not the binding constraint.

**Six cells, fixed here**: `lookback ∈ {1, 2, 3} months` × `hold ∈ {1, 3}
months`, where a month is **2,016 bars** (21 trading days × 96). Signal is
`sign(mid_c[t] − mid_c[t − lookback])`, position held for `hold`, decided on a
grid and phase-averaged over 8 offsets exactly as `round2` does.

Evaluated with the unchanged `engine.evaluate` and the unchanged
`EXPLORATORY_ASSUMPTION` cost: gross / cost / net pips per pair, σ-normalised
return, turnover, pair breadth, JPY / non-JPY, tail concentration, per panel, and
a family-max correction over the six.

**Kill condition.** If the sign is not stable across the two 730-day panels, or
gross is absent, record
**`MONTHLY_TSMOM_NOT_SUPPORTED_IN_EXISTING_PRICE_HISTORY`** and close price-only
directional research at the monthly scale as well.

Note the sample honestly: 624 days is under 30 months, so a 3-month lookback with
a 3-month hold has roughly **7 non-overlapping observations per pair** and about
5 effective independent pairs. This screen is powered to detect only a large
effect, and that limitation is stated here rather than discovered later.

## 8. B′-VOL — inventory only

The ten-year archive's JSONL records carry a `volume` field (tick count) and the
research reader's `PRICE_KEYS` reads only the eight bid/ask price fields, so it is
discarded before the cache is written. Round B′ **confirms this from code and
metadata only**:

* that the field exists in the archive writer and in the stored records' schema;
* where the research reader drops it;
* whether recovering it for the already-seen spans would need a new content read;
* whether coverage can be judged from existing metadata.

**No volume analysis, no strategy, and no new market-data content read.** If
answering any of the above would require opening an archive file for content,
Round B′ stops and reports that instead. The outcome is a referral, not a result.

## 9. Statistical rails

Matched null first; per-panel reporting; studentized effects; family-max
correction with a shared sign draw; the **screen's own false-positive rate
computed alongside any screen**; effective independent pairs as a self-check
(this corpus returns 4.4–6.5; a value near 20 means the null decorrelated the
panel); JPY / non-JPY; σ-normalised units; both-tail diagnostics at
1/3/5/10/20; and a hypothesis-ledger entry per sub-study.

**The aim is not to produce `p < 0.05`.** It is to establish whether an effect is
present, stable and large enough to be worth a label design.

## 10. Multiplicity and family boundaries

Three families, corrected separately and never pooled to flatter one another:

* **B′-1**: 7 horizons × 3 nulls — the family is the 7 horizons; the nulls are
  not variants.
* **B′-2**: 3 thresholds × {unconditioned, 2 HTF contexts × 2 states} = 3 × 5 =
  **15 cells**.
* **B′-4**: **6 cells**.

Total pre-registered: **28 cells**. Nothing else may enter. Any statistic
produced outside these is labelled `POST_HOC_DIAGNOSTIC_ONLY` and may not support
a conclusion.

## 11. Final classification

Exactly one, and **A is not the target**:

| case | condition | consequence |
| --- | --- | --- |
| **A** `PRICE_PATH_STRUCTURE_SURVIVES_NULL_CONTROL` | B′-1 or B′-2 shows a stable, non-negligible real-vs-null difference on both 730-day panels | a later round designs labels that harvest *that* structure |
| **B** monthly only | B′-1 and B′-2 empty, B′-4 stable | a monthly low-turnover family becomes its own research object |
| **C** `PRICE_ONLY_PATH_STRUCTURE_SCREEN_NEGATIVE` | all three empty on the deciding panels | refer the information-source decision to human + ChatGPT |
| **D** unresolved | a concrete implementation, sample or null-design reason prevents a verdict | quantify what would be needed; do **not** add statistics until something is positive |

**Round B′ stops at the classification.** A positive result does not start a
label round, a TP/SL grid, a classifier or any ML — the next round is designed,
not begun.

## 12. Not done in Round B′

No fresh read, no OOS read, no forward read. No ML, no classifier, no LightGBM.
No strategy optimisation, no retrace parameter tuning, no HTF indicator zoo, no
monthly parameter grid, no volume strategy, no external data acquisition. No
Formal Confirmation, no broker, no production claim, no new governance framework,
no general adversarial audit. The Windows `sys.addaudithook` crash remains a
separate open referral and is not mixed into this objective.
