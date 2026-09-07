# M15 — Economic Edge Source Expansion: results

**`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `PRODUCTION_READINESS_NOT_CLAIMED`.**

Plan: `docs/research/m15_economic_edge_source_expansion_plan.md`, frozen at
`a36ab82` **before any external data was fetched**, amended once at `41d7c52`
(§23, amendment A-1) before any carry economics was computed. Base master
`cfe2f9499e7dac9d799fc1580be403830903d356` (the PR #470 merge).

**Final status:
`ECONOMIC_EDGE_SOURCE_NOT_FOUND_EXOGENOUS_OPPORTUNITY_STRUCTURE_ESTABLISHED`.**

The expected-return layer is still empty. The opportunity layer, for the first
time in this programme, is not.

---

## 1. The answer

**Four findings, in the order the evidence supports them.**

* **A public, eight-currency carry source exists and was acquired** — BIS central
  bank policy rates, one anonymous HTTPS GET of a static public file, verified
  against ten known central-bank facts before anything was built on it. The
  plan's fallback cross-check then caught a **definition break inside the
  sample** in EUR, which appears in 6 of the 20 pairs, and it was corrected on
  fidelity grounds before any economics ran.
* **Carry has the shape it should have and fails anyway, for a specific reason.**
  The cross-sectional `k = 3` basket earns `+82 / +118` pips per pair with carry
  income `+49 / +121` and spot `+33 / −2` — the interest *is* the return and spot
  did not take it away, at 0.18–0.28 turnover a year. But JPY pairs return
  `+262 / +384` against non-JPY `+4.2 / +4.0`, so it is **a short-yen trade
  wearing a diversified label**, and the fourth sub-period of *both* deciding
  panels is a large loss. `CARRY_EDGE_NOT_SUPPORTED`.
* **Tick volume predicts movement and not cost-clearing movement.** At the carry
  horizon it forecasts next-week realised volatility strongly (`ρ +0.14 / +0.16`,
  `z +9.2 / +10.9`, **20 of 20 pairs** on both deciding panels) and whether the
  move will exceed the round trip **not at all** (`ρ −0.027 … +0.019`, 9–13 pairs
  of 20). Used as a filter it makes carry **worse in 15 of 15 cells**, because a
  carry position earns by the day and removing half the days removes half the
  income.
* **Scheduled policy decisions do define an exogenous opportunity population,
  and it is the first one whose cost works *for* it.** On rate-change days ±1 the
  absolute move is `1.55× / 1.31×` larger **and the spread is narrower**
  (`0.92× / 0.94×`), giving a move-net-of-cost ratio of `1.60 / 1.35` with
  **19 of 19 and 18 of 20 pairs agreeing**. Every previous opportunity variable
  in this programme had its own cost rising with it.

**What this does not establish.** An opportunity population is not an edge. The
event days clear cost only `1.04×` more often than ordinary days — because
**91% of ordinary days already move more than the round trip.** Magnitude was
never the binding constraint. Direction is, and nothing here addresses it.

## 2. Identity

| | |
| --- | --- |
| PR #470 | merged, merge commit **`cfe2f9499e7dac9d799fc1580be403830903d356`** |
| verified before merge | head `c2044b1` matched, CI green, `MERGEABLE`/`CLEAN`, no unresolved review comment |
| plan | `a36ab82`, before any external data; amendment A-1 at `41d7c52`, before any carry economics |
| panels | `2021-04-26…2023-04-25` (624 trading days) · `2023-04-26…2025-04-24` (624) · `2025-04-25…2025-12-28` (212) |
| pairs / bars | `PAIRS_20` · 999,238 + 993,878 + 335,200 |
| currencies | AUD, CAD, CHF, EUR, GBP, JPY, NZD, USD — exactly what `PAIRS_20` spans |
| **new FX market-data spans read** | **none** |
| fresh pool `2016-06-02…2021-04-25` | **untouched** |

## 3. The new data source

### 3.1 What was acquired

| | |
| --- | --- |
| **source** | BIS — *Central bank policy rates* (`WS_CBPOL`), public bulk flat file |
| **URL** | `https://data.bis.org/static/bulk/WS_CBPOL_csv_flat.zip` |
| **access** | one anonymous HTTPS GET. **No key, no account, no metered call, no payment** |
| **bytes / digest** | 4,102,141 · `sha256 = 24278555f8078eac…` (recorded in full in the artifact) |
| **field** | `OBS_VALUE`, per cent per year — the single unit across all eight |
| **frequency** | daily, as published: a step function between decisions |
| **rows** | 732,269 source rows streamed; **148,045** daily observations kept |
| **licensing** | BIS publishes this publicly for non-commercial use with attribution |

**Coverage**, all eight present, all reaching the present day:

| currency | first | last | observations |
| --- | --- | --- | ---: |
| AUD | 1976-04-07 | 2026-08-27 | 12,771 |
| CAD | 1960-07-27 | 2026-08-31 | 17,181 |
| CHF | 1946-01-01 | 2026-09-01 | 20,986 |
| EUR | 1999-01-01 | 2026-09-01 | 10,074 |
| GBP | 1946-01-01 | 2026-08-28 | 23,427 |
| JPY | 1946-01-01 | 2026-09-01 | 24,874 |
| NZD | 1985-01-04 | 2026-08-28 | 12,372 |
| USD | 1954-07-01 | 2026-09-01 | 26,360 |

**Verified against known history before anything was built on it** — ten checks,
all passing: USD `0.125` at the ZIRP floor and `5.125` at the peak; JPY `−0.10`
under NIRP and `0.50` after normalisation; CHF `−0.75` and `1.50`; EUR `0.00` and
`4.50`; AUD `0.10`; NZD `5.50`.

### 3.2 Date semantics, timezone, revision

`TIME_PERIOD` is the date the rate is **effective**, not a publication date. A
policy rate is announced and effective; it is not a statistic that gets revised,
which is why the plan ranks it above macro data. The bulk file is regenerated, so
a later download could extend the series — the `sha256` identifies the exact
bytes this analysis used.

The source carries a plain date with no time. It is treated as a **UTC calendar
date** and joined to the M15 grid's UTC date, the convention every panel in this
repository uses. **Every rate is used with a one-trading-day lag**, so no decision
can be taken on the bar that announced the change.

### 3.3 Why the policy rate, and what that costs

The plan's hierarchy (§5) was fixed **before** anything was fetched, ranked on
fidelity to what a position actually earns:

1. **broker financing actuals** — what a retail account genuinely receives. No
   public archive exists. This is the implementation gap, referred in §9;
2. **swap / forward points** — the market price of carry. No public,
   reproducible, eight-currency history without a paid contract;
3. **short-term money-market rates** — economically closest to (2), but the eight
   would have to be assembled from different series with different definitions
   and mixed frequency, and a cross-sectional ranking across inconsistent
   definitions is not a ranking;
4. **policy rates** — coarsest, and the only one available for all eight from
   **one source, one definition, one frequency**.

What the coarseness costs was measured, not argued. Against overnight
money-market rates over the **rate span** `2020-06-01 … 2026-01-05`, which is the
window the artifact records (FRED, public CSV, no key):

| currency | overnight series | mean gap | sd | corr |
| --- | --- | ---: | ---: | ---: |
| USD | `DFF` | −0.0408 | 0.0434 | 0.99981 |
| EUR | `ECBESTRVOLWGTTRMDMNRT` | −0.0797 | 0.0397 | 0.99978 |
| GBP | `IUDSOIA` | −0.0513 | 0.0366 | 0.99985 |

Only three currencies are cross-checked, because only three have a genuinely
daily public overnight series without a key; assembling the other five from
monthly series would measure the frequency mismatch rather than the rate gap.

Four to eight basis points, against differentials that run to several percentage
points.

### 3.4 Amendment A-1 — EUR's definition break

**The fallback cross-check found it, which is what it was for.**

BIS's euro-area series is **not one definition**. Its own `COMPILATION` field
says the steering rate became the deposit facility on 2024-09-18 and was the main
refinancing rate before. Measured against the ECB's own two series, it is
*exactly* the MRO before that date and *exactly* the deposit facility after:

| period | BIS EUR − deposit facility |
| --- | ---: |
| before 2024-09-18 | **+0.500** |
| from 2024-09-18 | **+0.001** |

A definition break inside the sample, in a currency appearing in 6 of 20 pairs.
It also measures the wrong thing: under excess liquidity €STR anchors to the
deposit facility, not the MRO. Against €STR, BIS as-is sits `−0.4477` away
(sd 0.227) where the deposit facility sits `−0.0797` (sd 0.040) — in line with
USD's `−0.0408` and GBP's `−0.0513`.

**EUR uses the ECB deposit facility rate throughout** (FRED `ECBDFR`). Still a
policy rate, same central bank, same frequency — the correction picks the right
one of the ECB's three. The other seven have no definition break inside the
panels: every transition they carry predates 2021.

## 4. Stage 2 — carry economics

Twelve cells: three families × three rebalances, the fourth family being the two
cross-sectional `k` values. **This is the entire carry search.**

Three lines that add up, never one "gross". Both deciding panels, at cost `C`:

| cell | spot | carry income | net | gross+ | same sign | net+ | tail | breadth |
| --- | ---: | ---: | ---: | :---: | :---: | :---: | :---: | :---: |
| `pair_level` weekly | −243 / +270 | +219 / +523 | −29 / +789 | ✗ | ✗ | ✗ | ✗ | ✗ |
| `pair_level` fortnightly | −205 / +250 | +218 / +522 | +7 / +767 | ✓ | ✓ | ✓ | ✗ | ✗ |
| `pair_level` monthly | −216 / +226 | +216 / +517 | −4 / +739 | ✗ | ✗ | ✗ | ✗ | ✗ |
| `cross_sectional_k2` weekly | −63 / +32 | +55 / +157 | −11 / +188 | ✗ | ✗ | ✗ | ✗ | ✗ |
| `cross_sectional_k2` fortnightly | −66 / +33 | +55 / +157 | −13 / +188 | ✗ | ✗ | ✗ | ✗ | ✗ |
| `cross_sectional_k2` monthly | −81 / +13 | +54 / +155 | −28 / +167 | ✗ | ✗ | ✗ | ✗ | ✓ |
| **`cross_sectional_k3` weekly** | **+33 / −2** | **+49 / +121** | **+82 / +118** | **✓** | **✓** | **✓** | ✗ | ✓ |
| `cross_sectional_k3` fortnightly | +23 / −4 | +49 / +121 | +72 / +116 | ✓ | ✓ | ✓ | ✗ | ✗ |
| `cross_sectional_k3` monthly | +9 / −10 | +48 / +119 | +57 / +108 | ✓ | ✓ | ✓ | ✗ | ✗ |
| `carry_change` weekly | +236 / −105 | +57 / −11 | +258 / −148 | ✗ | ✗ | ✗ | ✗ | ✗ |
| `carry_change` fortnightly | +266 / −79 | +101 / −27 | +348 / −123 | ✗ | ✗ | ✗ | ✗ | ✗ |
| `carry_change` monthly | +216 / −634 | +138 / −47 | +347 / −691 | ✗ | ✗ | ✗ | ✓ | ✓ |

### 4.1 The one family with a coherent story, and why it still fails

`cross_sectional_k3` is the textbook good shape: the interest is the return and
spot did not take it away, at a turnover of **0.18–0.28 a year** and a cost of
**0.5–0.9 pips** over two years. Carry is exactly the low-turnover object the
plan predicted.

It fails on the two clauses that matter.

| | 2021–23 | 2023–25 |
| --- | ---: | ---: |
| JPY pairs, mean net | **+261.9** | **+383.6** |
| non-JPY pairs, mean net | **+4.2** | **+4.0** |
| ratio | **63×** | **95×** |
| top-ten-day share of net | 1.51 | 1.42 |
| largest single pair's share | 0.39 | 0.45 |
| effective independent pairs | 4.55 | 3.21 |
| sub-period net, four blocks | +49.7, +65.4, +61.9, **−95.6** | +84.6, +87.5, +18.6, **−72.8** |

**It is a short-yen trade.** Non-JPY contributes four pips per pair over two
years — nothing. And the **fourth sub-period of both deciding panels is a large
loss** against solid gains in the first three: the carry unwind, not noise. The
top ten days contribute more than the total, the rest being negative in
aggregate.

`pair_level` shows the other failure mode cleanly — carry income `+218 / +522`
against spot `−205 / +250`, so it earned the interest and gave it back on one
panel and not the other, with net flipping sign across rebalance frequencies.
`carry_change` reverses sign between the deciding panels at every frequency.

**`CARRY_EDGE_NOT_SUPPORTED`.** The branch is dropped rather than optimised.
What it establishes is narrower and more useful than "carry does not work": over
these two panels the G10 carry premium *is* the short-yen trade, it does earn its
interest, and it pays for it in the last quarter of each window.

### 4.2 The implementation gap, stated and not claimed away

Everything above is **research carry** built from public policy rates. What a
retail account receives is the broker's financing, which embeds a markup and a
tom-next spread and is not publicly archived. The two are separate objects. No
production profitability is claimed from public rates, and the difference is
referred in §9.

## 5. Stage 3 — tick volume as an opportunity source

Measured at the horizon it would have to work at: a **daily** state, looking one
carry rebalance (**5 trading days**) ahead. Measuring a one-bar relationship and
asserting it survives to a week is the mistake that would have made this stage
meaningless.

Fifteen pre-registered cells, against a circular-block-shift null that keeps each
series' own serial dependence:

| representation | future realised volatility | future absolute return | **movement exceeds cost** |
| --- | --- | --- | --- |
| `normalised_level` | +0.139 / +0.123 (z +5.5 / +5.9) | +0.050 / +0.041 | +0.017 / −0.005 |
| `rolling_percentile` | +0.126 / +0.119 (z +5.0 / +6.0) | +0.048 / +0.038 | +0.016 / −0.004 |
| **`persistence`** | **+0.142 / +0.161 (z +9.2 / +10.9)** | +0.062 / +0.075 | −0.007 / −0.004 |
| `shock` | +0.057 / +0.086 | +0.024 / +0.031 | +0.019 / −0.004 |
| `change` | +0.057 / +0.052 | +0.043 / +0.040 | −0.004 / −0.027 |

Pairs agreeing in sign, on both deciding panels: **20 of 20** for volatility on
three of the five representations; **9 to 13 of 20** — a coin flip — for
cost-exceeding movement, on every one.

**That third column is the finding.** Volume predicts *how much* the price will
move and not *whether the move will clear the spread*, because the spread widens
with volume too. The only target that pays for a trade is the one volume cannot
see.

## 6. Stage 4 — integration

Base: `cross_sectional_k3` weekly, the one carry cell with gross economics on
both deciding panels. Its failure is a **tail** failure, which is a timing
failure — so the integration question is whether opportunity information
addresses the specific way it breaks.

It does not. **M3 is worse than M1 in 15 of 15 cells across all three panels:**

| panel | M1 (carry alone) | M3 range (carry × volume filter) | days removed |
| --- | ---: | --- | ---: |
| 2021–23 | **+89.1** | −38.8 … +47.7 | 53–55% |
| 2023–25 | **+120.3** | −155.6 … −49.3 | 51–56% |
| 2025 | +108.8 | +26.2 … +71.7 | 59–66% |

The mechanism is not subtle and it is specific to what carry is: **a carry
position accrues its interest every day it is held.** Removing half the days
removes half the income while leaving the spot risk of the days that remain. Time
in the market *is* the return. An opportunity filter is the wrong instrument for
an expected-return source that pays by the day, whatever the filter knows.

M2 — timing with no expected-return view, the direction-free control — is noise:
`+314, −45, −144, −321, −198` on the first panel alone. As the plan predicted.

`OPPORTUNITY_TIMING_ADDS_NO_INCREMENTAL_VALUE`.

## 7. Route C — the calendar branch

Carry weak and volume timing nothing, so the next source has to be **exogenous**
rather than another transform of the same prices.

### 7.1 The event population, and what it is not

Policy-rate decisions are one of the four event classes the plan names, and the
dates on which a G10 policy rate **changed** are already in the acquired series —
no new acquisition, no new provenance risk. Inside the panels: 4 (JPY) to 21
(NZD) changes per currency, 108 in total.

Stated plainly, this population **is not** a central-bank calendar:

* it contains only meetings that **changed** a rate. A scheduled meeting that
  held is invisible, and those are the majority — so this is biased toward the
  surprises, and a full calendar would show smaller effects;
* it carries **no CPI, employment or GDP** releases. Those need their own source
  and are referred;
* the BIS date is the **effective** date, which for most of these central banks
  is the announcement day or the day after.

### 7.2 What it shows

Days within ±1 of a rate change in either leg, against every other day:

| | 2021–23 | 2023–25 | 2025 |
| --- | ---: | ---: | ---: |
| event days / other days | 32 / 592 | 27 / 597 | 12 / 200 |
| absolute move, ratio | **1.548** | **1.315** | 1.198 |
| realised volatility, ratio | 1.312 | 1.179 | 1.080 |
| tick volume, ratio | 1.641 | 1.292 | 1.222 |
| **spread, ratio** | **0.921** | **0.941** | **0.871** |
| **move net of cost, ratio** | **1.599** | **1.347** | 1.240 |
| pairs with net ratio > 1 | **19 / 19** | **18 / 20** | 9 / 10 |
| standardised difference, net | 0.429 | 0.298 | 0.204 |

**The spread narrows while the movement grows.** That is the opposite of every
opportunity variable this programme has tried: volume-selected busy days come
with wider spreads, because volume rises in thin and stressed conditions too.
Scheduled decisions happen in the most liquid hours with the deepest
participation, so the anchor selects *good* liquidity rather than merely high
activity.

### 7.3 What it does not show

**`exceeds_cost` ratio is only 1.04 / 1.03.** The baseline is already `0.911` —
**91% of ordinary days already move more than the round trip.** Magnitude was
never the binding constraint in this programme, and an anchor that raises the
cost-clearing rate by four percentage points is economically trivial on its own.

And the standardised differences are `0.30–0.43`: real, modest, and about
**5% of days**.

Above all: **nothing here says anything about direction.** A bigger move at a
tighter spread is worth something only if one knows which way, and five packages
have now established that this programme does not.

`CALENDAR_EVENT_OPPORTUNITY_STRUCTURE_SUPPORTED`, read strictly as a statement
about the **opportunity layer**.

## 8. Stage 5 — ML not run

The plan's four prerequisites (§15):

1. the expected-return source has gross economics on its own — **partly**:
   `cross_sectional_k3` does, but fails its own pass condition;
2. something survives realistic cost — **yes**, `+82 / +118` net;
3. the opportunity source has incremental information — **no**. Stage 4: 15 of 15
   cells worse;
4. a simple interaction leaves visible selection room — **no**.

Condition 3 fails outright, so **no model was fitted**. A meta-label model is a
selector over an opportunity signal, and the opportunity signal has just been
measured to destroy the base rather than improve it. `ML_NOT_JUSTIFIED`.

## 9. Deviations, limitations and referrals

1. **Amendment A-1** (§3.4) — before any carry economics, on fidelity grounds.
2. **The calendar verdict rule was not in the frozen plan.** §16 named the
   question but no numeric criterion, so the rule used — net-of-cost ratio above
   1 on both deciding panels, with three quarters of pairs agreeing — was written
   at implementation time. It is disclosed here rather than presented as
   pre-registered, and §7.3 is why the verdict is read narrowly whatever the rule.
3. **The event population is rate *changes*, not scheduled meetings** (§7.1).
4. **Research carry is not broker carry** (§4.2). No production profitability is
   claimed from public rates. **Referral**: whether a broker's historical
   financing can be obtained at all, and how far it sits from the policy-rate
   differential, is the question that decides whether any carry work is
   implementable. It cannot be answered from public data.
5. **CPI, employment and GDP releases were not acquired.** A full calendar needs
   a source with its own provenance and revision behaviour — and, unlike policy
   rates, macro statistics **are** revised, so a real-time vintage would be
   required. **Referral.**
6. **Swap points were not obtained**, so the second rank of the hierarchy is
   untested. **Referral.**

## 10. Verification

* `tests/research` — **257 tests**, of which 25 are this package's.
* **Mutation testing**, 27 mutations of the properties that matter, **all
  killed**: the rate lag removed; the forward fill moved after the shift so the
  lag becomes one *observation* rather than one day; the accrual divided by 365
  turned into 252; the accrual made per-bar instead of per-calendar-day; the
  differential's sign inverted; carry made not to follow the position; the
  position traded on its own decision bar; the EUR override removed so the
  definition break returns; EUR mapped to a member state; the dead band removed;
  the basket made non-neutral; each of the four carry kill clauses disabled in
  turn; 2025 made a deciding panel; each opportunity state made to read the day
  it labels; the forward target turned backward; the filter threshold moved off
  the median and made a fixed level; the event population made to include
  no-change days; and a thirteenth carry cell added.
* **Two test defects of my own were found by that battery and fixed**: a monotone
  volume fixture made every rolling percentile `1.0`, silently disabling the
  filter tests; and a 40-day fixture skipped three Stage 3 tests entirely.
* `ruff format --check`, `ruff check`, `tools/lint/run_custom_checks.py` — clean.
* Every number in this document was verified against the artifacts.

Known, unrelated and pre-existing: the full `pytest tests/` suite crashes on
Windows from `sys.addaudithook` accumulation in `isolation.py`. A separate
referral.

## 11. Research interpretation

**1. Was a new expected-return source found?** No. Carry is the strongest
candidate the public data can express and, over these two panels, it is one
currency and one crash. It is not nothing — it earns its interest, at negligible
turnover — but it is not a diversified premium and it is not separable from being
short the yen through a specific historical episode.

**2. Is tick volume useful for monetisation?** Not as a filter, and now for a
reason rather than a measurement. It knows about magnitude and not about
cost-clearing magnitude, and the thing it would filter earns by the day.

**3. What is price-derived information now limited to?** Describing volatility.
Across six packages it has produced: a variance-ratio structure 6–18× below
break-even, a retrace geometry that dissolves into a selection artefact, and a
volume signal that forecasts realised volatility at `z ≈ +10` and forecasts
nothing about whether a move pays. Every one is a statement about **magnitude**.
None is about direction, and cost is charged on direction.

**4. Is carry implementable?** Unknown, and unknowable from here. The gap between
a policy-rate differential and a broker's financing is the whole question and no
public archive answers it.

**5. How much does the broker financing difference matter?** Decisively. The
`cross_sectional_k3` net is `+82 / +118` pips per pair over two years — roughly
`0.4` pips per pair per day. A financing markup of a few tenths of a basis point
per day would consume it. This is not a strategy that survives an unfavourable
financing assumption, and no favourable one has been demonstrated.

**6. Is it worth going on to COT or implied volatility?** On this evidence, the
question to ask first is different. Both are **positioning and risk-premium**
sources, and the thing this programme is missing is not another opportunity
variable — it now has a good one — but a **direction-bearing expected return**.
COT is the better of the two on that axis: it is a positioning measure with a
reversal hypothesis at horizons far longer than anything tried here, it is free
and public from the CFTC, and it is weekly, which suits the turnover profile that
carry showed is affordable. Implied volatility is a **volatility** premium, which
is the layer that already works.

**7. Is there a fresh-replication candidate?** **No.** The plan's criteria (§21)
require gross edge, positive after cost, breadth, non-catastrophic tail and a
working simple baseline. `cross_sectional_k3` fails breadth and tail. Nothing is
forwarded, and the `N = 1` forward budget stays unspent.

## 12. Final decision

**No fresh-replication candidate. The next source has a reasoned case.**

The programme has, for the first time, a **working opportunity layer** — an
exogenous anchor that raises movement while *lowering* cost — and a demonstrably
empty **expected-return layer**. That asymmetry is the finding, and it says what
to do next: stop looking for opportunity variables and look for a direction-
bearing return.

Recommended, in order, each needing its own authorisation:

1. **COT positioning** — free and public (CFTC), weekly, a genuine reversal
   hypothesis at a horizon carry showed is affordable, and it is about
   *direction*. It is US-futures positioning used as a proxy for spot FX, which
   is its main weakness and should be stated up front.
2. **A real economic calendar with real-time vintages** — to widen §7's anchor
   from rate *changes* to all scheduled events, which would also remove the
   surprise bias.
3. **Broker financing history** — not a research source but the question that
   decides whether any carry result could ever be implemented.

Implied volatility ranks last: it prices the layer that already works.

## 13. Final status

* **`ECONOMIC_EDGE_SOURCE_NOT_FOUND_EXOGENOUS_OPPORTUNITY_STRUCTURE_ESTABLISHED`**
* `CARRY_EDGE_NOT_SUPPORTED`
* `OPPORTUNITY_TIMING_ADDS_NO_INCREMENTAL_VALUE`
* `CALENDAR_EVENT_OPPORTUNITY_STRUCTURE_SUPPORTED` — the opportunity layer only
* `ML_NOT_JUSTIFIED` — prerequisite 3 fails
* `NON_DECISION_BEARING_EXPLORATORY_ONLY` ·
  `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
* **Fresh historical pool `2016-06-02 … 2021-04-25` untouched.** Historical OOS
  untouched. The dead window and the future untouched epoch untouched.
* **Formal Confirmation not performed.** No broker, demo or live contact. No
  order of any kind. No production deployment.
* External data acquired: BIS policy rates and three FRED overnight-rate series,
  all public, all keyless, all recorded with provenance. **No paid contract, no
  metered API, no account, no secret.**
* `PRODUCTION_READINESS_NOT_CLAIMED`.

Fresh historical replication, further external acquisition and Formal
Confirmation each await an explicit human + ChatGPT instruction.
