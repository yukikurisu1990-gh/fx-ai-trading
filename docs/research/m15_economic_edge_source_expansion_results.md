# M15 — Economic Edge Source Expansion: results

**`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `PRODUCTION_READINESS_NOT_CLAIMED`.**

Plan: `docs/research/m15_economic_edge_source_expansion_plan.md`, frozen at
`a36ab82` **before any external data was fetched**, amended once at `41d7c52`
(§23, amendment A-1) before any carry economics was computed. Base master
`cfe2f9499e7dac9d799fc1580be403830903d356` (the PR #470 merge).

**Final status:
`ECONOMIC_EDGE_SOURCE_NOT_FOUND_EXOGENOUS_MOVEMENT_STRUCTURE_ESTABLISHED`.**

No expected-return source was found. An exogenous anchor picks out days that
**move more** — and, contrary to the first version of this document, **not days
that cost less**.

---

## 1. The answer

* **A public, eight-currency carry source exists and was acquired**, and the
  plan's own fallback cross-check earned its keep immediately by finding a
  **definition break inside the sample** in EUR — a currency in 6 of 20 pairs.
  Corrected before any economics ran (amendment A-1).
* **`CARRY_EDGE_NOT_SUPPORTED`, and the decomposition says why twice over.**
  `cross_sectional_k3` earns `+82 / +118` pips per pair at 0.18–0.28 turnover a
  year. Split by bloc: JPY pairs `+262 / +384`, non-JPY `+4.2 / +4.0` — and the
  **non-yen leg gave its entire interest back on spot** (carry `+41.5 / +64.5`
  against spot `−36.8 / −59.5`). That is the classic carry error the plan's
  mandatory decomposition exists to catch, occurring one level below where the
  pooled row shows it. The fourth sub-period of both panels is a large loss.
* **Tick volume predicts movement and not cost-clearing movement.** At the carry
  horizon it forecasts next-week realised volatility strongly (`ρ +0.14 / +0.16`,
  `z +9.2 / +10.9`, 20 of 20 pairs on two of five representations) and whether
  the move will exceed the round trip **not at all** (9–13 pairs of 20). Used as
  a filter it is worse in 15 of 15 cells — and the reason is **not** the one the
  first version gave: removed carry income is 20–66% of the damage, and the
  dominant channel is that the filter **keeps the losing spot days**.
* **Policy-rate change days move more, at a slightly wider spread.** Day-of-week
  matched: absolute move `1.33× / 1.13×`, 17 of 19 and 17 of 20 pairs, permutation
  `p = 0.012 / 0.015`. Spread `1.05× / 1.02×` — **wider, not narrower**. The
  cost-clearing rate barely moves (`1.001 / 1.008`), because 91% of ordinary days
  already clear the round trip.

**The first version of this document led with the opposite of that last line**,
and it was wrong. §7.4 records what happened.

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

## 3. The new data sources

### 3.1 BIS policy rates — the primary

| | |
| --- | --- |
| **source** | BIS — *Central bank policy rates* (`WS_CBPOL`), public bulk flat file |
| **URL** | `https://data.bis.org/static/bulk/WS_CBPOL_csv_flat.zip` |
| **access** | one anonymous HTTPS GET. **No key, no account, no metered call, no payment** |
| **bytes / digest** | 4,102,141 · `sha256 = 24278555f8078eac…` |
| **field** | `OBS_VALUE`, per cent per year — one unit across all eight |
| **frequency** | daily, as published: a step function between decisions |
| **rows** | 732,269 source rows streamed; **148,045** daily observations kept |
| **licensing** | BIS publishes this publicly for non-commercial use with attribution |

Coverage, all eight present: AUD 1976-04-07…2026-08-27 (12,771 obs), CAD
1960-07-27…2026-08-31 (17,181), CHF 1946-01-01…2026-09-01 (20,986), EUR
1999-01-01…2026-09-01 (10,074), GBP 1946-01-01…2026-08-28 (23,427), JPY
1946-01-01…2026-09-01 (24,874), NZD 1985-01-04…2026-08-28 (12,372), USD
1954-07-01…2026-09-01 (26,360).

Verified against ten known central-bank facts before anything was built on it:
USD `0.125` at the ZIRP floor and `5.125` at the peak; JPY `−0.10` under NIRP and
`0.50` after normalisation; CHF `−0.75` and `1.50`; AUD `0.10`; NZD `5.50`.

### 3.2 The EUR series actually used — FRED `ECBDFR`

Recorded separately because **it is not the BIS series**, and the coverage table
above describes the series it replaced. Its own record is in the artifact:

| | |
| --- | --- |
| **series** | `ECBDFR`, the ECB deposit facility rate |
| **URL** | `https://fred.stlouisfed.org/graph/fredgraph.csv?id=ECBDFR` |
| **digest** | `sha256 = 4d8d607fca79…`, recorded per run |
| **coverage over the rate span** | 2,045 observations, 2020-06-01…2026-01-05, range `−0.50 … 4.00` |
| **revision** | a decision, not a statistic: announced with an effective date, not revised |

The first version of this package computed that digest and discarded it, leaving
the input that determines EUR in 6 of 20 pairs with no recorded source at all. A
review role found it; it is fixed and pinned by a test.

### 3.3 Date semantics, timezone, revision

`TIME_PERIOD` is the date the rate is **effective**, not a publication date. A
policy rate is announced and effective; it is not revised, which is why the plan
ranks it above macro data. Plain dates with no time, treated as **UTC calendar
dates** and joined to the M15 grid's UTC date. **Every rate is used with a
one-trading-day lag**, so no decision can be taken on the bar that announced the
change.

### 3.4 Why the policy rate, and what that costs

The plan's hierarchy (§5), fixed before anything was fetched: broker financing
actuals (no public archive — the implementation gap, §9.4); swap points (no
public eight-currency history without a paid contract); short-term money-market
rates (economically closest, but the eight would have to be assembled from
different series with different definitions and mixed frequency); policy rates
(coarsest, and the only one available for all eight from one source, one
definition, one frequency).

What the coarseness costs, measured over the rate span `2020-06-01 … 2026-01-05`
against overnight money-market rates (FRED, public CSV, no key):

| currency | series | mean gap | sd | corr |
| --- | --- | ---: | ---: | ---: |
| USD | `DFF` | −0.0406 | 0.0434 | 0.99981 |
| EUR | `ECBESTRVOLWGTTRMDMNRT` | −0.0797 | 0.0397 | 0.99978 |
| GBP | `IUDSOIA` | −0.0513 | 0.0366 | 0.99985 |

Only three currencies have a genuinely daily public overnight series without a
key; assembling the other five from monthly series would measure the frequency
mismatch rather than the rate gap. **This bound is narrower than it looks** — see
§9.7.

### 3.5 Amendment A-1 — EUR's definition break

BIS's euro-area series is **not one definition**. Its own `COMPILATION` field
says the steering rate became the deposit facility on 2024-09-18 and was the main
refinancing rate before. Measured, the series is *exactly* the MRO before that
date (gap to the deposit facility `+0.500`) and *exactly* the deposit facility
after (`+0.001`). Under excess liquidity €STR anchors to the deposit facility,
not the MRO. So **EUR uses the ECB deposit facility throughout** — still a policy
rate, same central bank, same frequency; the correction picks the right one of
the ECB's three.

## 4. Stage 2 — carry economics

Twelve cells: three families × three rebalances. Three lines that add up — spot,
carry income, cost — never one "gross". Both deciding panels, at cost `C`:

| cell | spot | carry income | net | gross+ | same sign | net+ | tail | bloc sign |
| --- | ---: | ---: | ---: | :---: | :---: | :---: | :---: | :---: |
| `pair_level` weekly | −243 / +270 | +219 / +523 | −29 / +789 | ✗ | ✗ | ✗ | ✗ | ✗ |
| `pair_level` fortnightly | −205 / +250 | +218 / +522 | +7 / +767 | ✓ | ✓ | ✓ | ✗ | ✗ |
| `pair_level` monthly | −216 / +226 | +216 / +517 | −4 / +739 | ✗ | ✗ | ✗ | ✗ | ✗ |
| `cross_sectional_k2` weekly | −63 / +32 | +55 / +157 | −11 / +188 | ✗ | ✗ | ✗ | ✗ | ✗ |
| `cross_sectional_k2` fortnightly | −66 / +33 | +55 / +157 | −13 / +188 | ✗ | ✗ | ✗ | ✗ | ✗ |
| `cross_sectional_k2` monthly | −81 / +13 | +54 / +155 | −28 / +167 | ✗ | ✗ | ✗ | ✗ | ✓ |
| **`cross_sectional_k3` weekly** | **+33 / −2** | **+49 / +121** | **+82 / +118** | **✓** | **✓** | **✓** | **✗** | ✓ |
| `cross_sectional_k3` fortnightly | +23 / −4 | +49 / +121 | +72 / +116 | ✓ | ✓ | ✓ | ✗ | ✗ |
| `cross_sectional_k3` monthly | +9 / −10 | +48 / +119 | +57 / +108 | ✓ | ✓ | ✓ | ✗ | ✗ |
| `carry_change` weekly | +236 / −105 | +57 / −11 | +258 / −148 | ✗ | ✗ | ✗ | ✗ | ✗ |
| `carry_change` fortnightly | +266 / −79 | +101 / −27 | +348 / −123 | ✗ | ✗ | ✗ | ✗ | ✗ |
| `carry_change` monthly | +216 / −634 | +138 / −47 | +347 / −691 | ✗ | ✗ | ✗ | **✗** | ✓ |

The "bloc sign" column is the **coded** clause — it asks only whether the two
blocs share a sign. `cross_sectional_k3` weekly passes it. The clause that fired
mechanically is **tail**, and the concentration below is a judgment applied on
top of it, not a coded test.

### 4.1 The one family with a coherent story, and why it fails twice

The pooled row is the textbook good shape: net `+82 / +118`, carry income
`+49 / +121`, spot `+33 / −2`, turnover **0.18–0.28 a year**, cost 0.5–0.9 pips
over two years.

**Split by bloc, the pooled row is misleading:**

| 2021–23 | spot | carry | net | pairs net + | four sub-periods |
| --- | ---: | ---: | ---: | :---: | --- |
| JPY (6 pairs) | +196.5 | +65.8 | **+261.9** | 4/6 | +62.8, +128.4, +151.4, **−80.6** |
| non-JPY (14) | **−36.8** | +41.5 | **+4.2** | 5/14 | +44.1, +38.5, +23.6, **−102.0** |

| 2023–25 | spot | carry | net | pairs net + | four sub-periods |
| --- | ---: | ---: | ---: | :---: | --- |
| JPY (6) | +131.3 | +253.1 | **+383.6** | 4/6 | +214.2, +217.1, +48.6, **−96.2** |
| non-JPY (14) | **−59.5** | +64.5 | **+4.0** | 7/14 | +29.1, +31.9, +5.7, **−62.7** |

Two failures, not one.

1. **It is a short-yen trade.** JPY pairs return 63× and 95× what the non-yen
   pairs do, on 3.2–4.6 effective independent pairs rather than 20.
2. **The non-yen leg — which *is* the diversified G10 carry premium hypothesis —
   gave its entire interest back on spot.** Carry `+41.5 / +64.5` against spot
   `−36.8 / −59.5`, leaving `+4.2 / +4.0` pips per pair over two years, with 5 of
   14 and 7 of 14 pairs positive. §1's "the interest *is* the return and spot did
   not take it away" is true of the pooled row **only because the yen leg's spot
   gain masks it**, and that is the exact error plan §10's decomposition exists
   to prevent — occurring one level below where the plan looks.

Both blocs lose their fourth sub-period on both panels. The top ten days
contribute 1.51 and 1.42 times the total, the rest being negative in aggregate.

`pair_level` shows the other failure mode: carry income `+218 / +522` against
spot `−205 / +250`, net flipping sign across rebalance frequencies.
`carry_change` reverses sign between the deciding panels at every frequency.

**`CARRY_EDGE_NOT_SUPPORTED`.**

### 4.2 Two properties of the construction that the table does not show

**The signal never moved.** Over 2021–23 the bottom three by rate is CHF / EUR /
JPY on **100% of days**; over 2023–25 the same three, and USD is top-three on
100%. `cross_sectional_k3` on these panels is a **static long CAD/NZD/USD, short
CHF/EUR/JPY book**. The 0.18–0.28 turnover is therefore not the virtue §4.1's
shape suggests — it is the statement that the ranking never crossed. Each panel
is closer to **one** bet than to 624 days, and "the same sign on both deciding
panels" is close to vacuous for a static position across adjacent windows.

**The basket is not equal-weighted where it matters.** `PAIRS_20` is an
incomplete graph — NZD and CAD appear in 3 pairs, USD in 7 — so a currency target
of `±1/k` expressed through pair positions is amplified by degree. Realised
exposure, 2021–23:

| USD | JPY | EUR | GBP | NZD | CHF | CAD | AUD |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| +1.117 | **−1.073** | −1.027 | +0.759 | +0.384 | −0.561 | +0.245 | +0.157 |

The short-JPY leg this section diagnoses as an economic fact is **mechanically
amplified about 4×** relative to CAD and 7× relative to AUD. And the mean
absolute pair weight is **0.168** against `pair_level`'s `±1`, so the §4 table
compares families at roughly 6× different notional with no scale column.

### 4.3 The implementation gap

Everything above is **research carry** from public policy rates. What a retail
account receives is the broker's financing, which embeds a markup and a tom-next
spread and is not publicly archived. The two are separate objects. No production
profitability is claimed, and the gap is referred (§9.4).

## 5. Stage 3 — tick volume as an opportunity source

A **daily** state, looking one carry rebalance (5 trading days) ahead. Fifteen
pre-registered cells, against a circular-block-shift null:

| representation | future realised volatility | future absolute return | **movement exceeds cost** |
| --- | --- | --- | --- |
| `normalised_level` | +0.139 / +0.123 (z +5.5 / +5.9) | +0.050 / +0.041 | +0.017 / −0.005 |
| `rolling_percentile` | +0.126 / +0.119 (z +5.0 / +6.0) | +0.048 / +0.038 | +0.016 / −0.004 |
| **`persistence`** | **+0.142 / +0.161 (z +9.2 / +10.9)** | +0.062 / +0.075 | −0.007 / −0.004 |
| `shock` | +0.057 / +0.086 | +0.024 / +0.031 | +0.019 / −0.004 |
| `change` | +0.057 / +0.052 | +0.043 / +0.040 | −0.004 / −0.027 |

Pairs agreeing in sign on **both** deciding panels, for the volatility column:
`persistence` and `rolling_percentile` **20 of 20**; `normalised_level` 19 and 20;
`shock` 18 and 20; `change` 18 and 18. For the cost column: **9 to 13 of 20** on
every representation — a coin flip.

Volume predicts *how much* the price will move and not *whether the move will
clear the spread*, because the spread widens with volume too.

## 6. Stage 4 — integration, and what the filter actually removed

Base: `cross_sectional_k3` weekly. **M3 is worse than M1 in 15 of 15 cells.**

| panel | M1 | of which spot / carry | M3 range | days removed |
| --- | ---: | --- | --- | ---: |
| 2021–23 | **+89.1** | +40.3 / +48.8 | −38.8 … +47.7 | 53.0–57.8% |
| 2023–25 | **+120.3** | **−1.1** / +121.4 | −155.6 … −49.3 | 51.1–55.5% |

**The mechanism is not the one the first version of this document gave.** It
claimed the filter removes carry income. Decomposed:

| representation | 2021–23 gap | removed carry | removed spot | 2023–25 gap | removed carry | removed spot |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `normalised_level` | 47.4 | 27.1 (57%) | 20.4 | 256.4 | 64.2 (25%) | **192.2** |
| `rolling_percentile` | 41.4 | 27.3 (66%) | 14.1 | 247.1 | 59.2 (24%) | **187.9** |
| `persistence` | 55.5 | 21.9 (39%) | 33.6 | 169.6 | 54.5 (32%) | **115.1** |
| `change` | 48.0 | 21.3 (44%) | 26.7 | 275.9 | 54.6 (20%) | **221.3** |
| `shock` | 127.9 | 25.7 (20%) | **102.2** | 235.4 | 63.8 (27%) | **171.7** |

Removed carry is 20–66% of the damage and **removed spot dominates in 8 of the
10 deciding cells**. On 2023–25 the panel's total spot is ≈0 (`−1.1`) and the
filter splits it into roughly `−193` kept against `+192` removed: the
high-volume days are the yen-carry-unwind days, which is exactly when this
position loses. That is **adverse selection on spot**, not lost interest.

The corrected reading is more interesting than the original and points the other
way: the volume state *is* informative about this position's spot outcome — with
the wrong sign for a filter. It was not tested as a direction signal and must not
be, on either this evidence or the prior package's.

M2 — timing with no expected-return view — is noise: `+314, −45, −144, −321,
−198` on the first panel.

`OPPORTUNITY_TIMING_ADDS_NO_INCREMENTAL_VALUE`.

## 7. Route C — the calendar

### 7.1 The event population, and what it is not

Days within ±1 of a G10 policy-rate **change**, from the acquired series. Inside
the deciding panels: **59** changes on 2021–23 and **50** on 2023–25; 126 across
all three panels. Per currency across the three: NZD 21, GBP 20, CAD 19, EUR 18,
USD 17, AUD 16, CHF 11, JPY 4.

Stated plainly, this **is not** a central-bank calendar:

* only meetings that **changed** a rate. A scheduled meeting that held is
  invisible, and those are the majority — so the sample is biased toward
  surprises, and a full calendar would show smaller effects;
* **whether a meeting will change a rate is not knowable in advance**, so this
  population cannot be used as a forward-looking anchor at all. It bounds what an
  event anchor could offer; it is not one;
* no CPI, employment or GDP releases — referred (§9.5);
* the BIS date is the **effective** date and the panel is lagged a further day,
  so the window is `[D, D+2]` relative to the effective date and **never contains
  the announcement day**. For the ECB the deposit facility takes effect about six
  days after the decision, so for EUR — 6 of 20 pairs — the window sits 6 to 9
  days after the decision and contains no ECB information event.

### 7.2 What it shows, day-of-week matched

**Every ratio the verdict reads is matched on day of week.** §7.4 says why.

| | 2021–23 | 2023–25 | 2025 *(may not decide)* |
| --- | ---: | ---: | ---: |
| event days / other days | 31 / 490 | 26 / 492 | 12 / 163 |
| **absolute move, matched** | **1.3345** | **1.1273** | 1.0288 |
| **spread, matched** | **1.0509** | **1.0222** | 0.9834 |
| move net of cost, matched | 1.3513 | 1.1342 | 1.0305 |
| exceeds cost, matched | 1.0014 | 1.0083 | 0.9978 |
| tick volume, matched | 1.4118 | 1.1325 | 0.9793 |
| pairs with net ratio > 1 | **17 / 19** | **17 / 20** | 4 / 9 |
| permutation `p`, two-sided | **0.0117** | **0.0153** | 0.560 |

Event days **move about 33% and 13% more**, with 17 of 19 and 17 of 20 pairs
agreeing, and a permutation test that re-draws event days **within day of week**
and standardises each pair before pooling gives `p = 0.012 / 0.015`. That is
real.

**The spread is `1.05×` and `1.02×` — wider.** 17 of 19 and 14 of 20 pairs show a
wider spread on event days. There is no cost advantage.

`CALENDAR_EVENT_MOVEMENT_STRUCTURE_SUPPORTED` ·
`EVENT_DAY_COST_ADVANTAGE_NOT_ESTABLISHED`.

### 7.3 And it is still not an edge

The cost-clearing rate rises by `1.0014` and `1.0083` — because **91% of ordinary
days already move more than the round trip**. Magnitude was never the binding
constraint in this programme. Direction is, and nothing here addresses it. A
bigger move at a slightly wider spread is worth something only if one knows which
way.

### 7.4 What the first version of this document got wrong

It led with: *"the spread narrows while the movement grows… the first
opportunity variable in this programme whose cost works for it."* **That was a
day-of-week composition artefact, and both review roles found it independently.**

The M15 panels carry a **Sunday pseudo-session** — the 21:00–24:00 UTC open. On
`EUR_USD` over 2021–23 it is **10.45 bars** against ~95 on a weekday, with a
median spread of **2.51 pips** against 1.49 and a daily move of **7.97 pips**
against 36–48. Policy rates take effect on weekdays, so the unmatched comparison
put **17.5%** Sunday in the control group and **0%** in the event group. That
alone produced the "narrower spread".

| spread ratio | as first published | Sundays dropped |
| --- | ---: | ---: |
| 2021–23 | **0.921** (3 of 19 pairs wider) | **1.041** (**17 of 19** wider) |
| 2023–25 | **0.941** (4 of 20) | **0.998** (7 of 20) |

Two fixes, both in committed code and both pinned by tests: days with fewer than
48 bars are **dropped** from the daily table, and every ratio the verdict reads
is computed **within day of week** and then pooled. The unmatched ratio is still
reported beside it and is never read.

The movement effect survives both controls and now carries a null it did not have
before. The cost claim does not survive, and is withdrawn.

## 8. Stage 5 — ML not run

The plan's four prerequisites: (1) the expected-return source has gross economics
— *partly*, but it fails its own pass condition; (2) something survives realistic
cost — *yes*; (3) the opportunity source has incremental information — **no**,
15 of 15 cells worse; (4) a simple interaction leaves selection room — **no**.

Condition 3 fails outright, so **no model was fitted**. A meta-label model is a
selector over an opportunity signal, and that signal has been measured destroying
the base. `ML_NOT_JUSTIFIED`.

## 9. Deviations, limitations and referrals

1. **Amendment A-1** (§3.5) — before any carry economics, on fidelity grounds.
2. **The calendar verdict rule was not in the frozen plan.** §16 named the
   question and no numeric criterion, so the rule — matched net-of-cost ratio
   above 1 on both deciding panels, three quarters of pairs agreeing, and a
   permutation `p ≤ 0.05` — was written at implementation time. The permutation
   clause and the day-of-week matching were **added after the first result**, in
   response to review, and both make the test harder.
3. **Day-of-week matching and the Sunday filter are post-result fixes** (§7.4).
   They correct a defect rather than move a threshold, and they turn a positive
   claim into a negative one — but they were not pre-registered.
4. **Broker financing history** — decides whether any carry result is
   implementable. `cross_sectional_k3` earns `+82 / +118` over **624 trading
   days** = **0.13 / 0.19** pips per pair per day. A financing markup of a few
   tenths of a basis point per day would consume it. **Referral.**
5. **CPI, employment and GDP releases were not acquired.** Unlike policy rates,
   macro statistics **are** revised, so a real-time vintage would be required.
   **Referral.**
6. **Swap points were not obtained**, so the second rank of the source hierarchy
   is untested. **Referral.**
7. **The 4–8 bp cross-check does not bound the carry error.** It covers 3 of 8
   currencies, and the result is a *ranking of levels* whose closest pair on
   2021–23 is CAD 1.749 against USD 1.634 — an 11.5 bp gap, within about 1.5× the
   measured dispersion, straddling the top-three boundary. More fundamentally,
   what an FX position earns differs from the interest differential by the
   **cross-currency basis**, a distinct and sign-persistent term of order tens of
   basis points that is historically negative for JPY and CHF funding — against
   precisely the leg that generates the entire result. It is not measured here
   and is not covered by the 4–8 bp figure. It is estimable from public forward
   points for the majors and is a separate research question from §9.4's markup.
8. **JPY has a definition break inside `supplemental_2023_2025`.** The same
   `COMPILATION` field that caught EUR says the BOJ's series moves from the
   YCC-era short-term policy rate to the uncollateralised overnight call-rate
   target on **2024-03-21**. It is ~5 bp economically, the same order as the
   measured gaps, so it does not move the verdict — but §3.5's "the other seven
   have no definition break inside the panels" was **false as first written**, and
   it was false for the currency that carries the whole result.
9. **Plan §18's family-wise correction was not applied.** `FAMILYWISE_ALPHA` and
   `STUDENTIZED_FLOOR` are defined and unused. Stage 3's `z` of +5 to +11 would
   survive any correction over 15 cells, but the carry layer carries **no
   uncertainty measure at all** — `+82 / +118` and the bloc splits are point
   estimates with no null. Route C now has one; carry does not.
10. **`largest_pair_share` is computed where plan §10 asks for the largest single
    *currency*'s share**, and `TAIL_SHARE_CEILING = 0.50` is an
    implementation-time numeric criterion not in the plan. Immaterial here — the
    measured share is 1.51 — but disclosed for symmetry with item 2.

## 10. Verification

* `tests/research` — **273 tests**, of which 41 are this package's.
* **Mutation testing.** A review role mutated the package 30 ways and **nine
  survived**, including a one-day look-ahead in the rate join that changed 959 of
  50,019 bars by up to 0.50 percentage points and still passed 25 of 25 tests —
  because every carry test built a **constant** rate panel, so the join date was
  invisible to all of them. After the hardening pass, **21 of 21 re-tested
  mutations killed**, including: the rate join reading tomorrow; `_fred_daily`
  skipping its forward fill; the override provenance discarded; the header lookup
  back to case-sensitive; a non-zero-sum basket; the dead band removed; the
  forward-volatility target losing its final shift; the calendar window made
  one-sided; the Sunday sessions put back; the matched ratio replaced by the raw
  one; `_matched_ratio` ignoring its weekday grouping; the verdict reading `x2.0`
  where it means `x1.0`; `_improves` failing open; and an unmeasurable tail share
  treated as a pass.
* Four tests that did not test what they were named for were replaced, and two
  fixture defects of my own were found by that battery and fixed.
* `ruff format --check`, `ruff check`, `tools/lint/run_custom_checks.py` — clean.
* Every number in this document was verified against the artifacts
  programmatically.

Known, unrelated and pre-existing: the full `pytest tests/` suite crashes on
Windows from `sys.addaudithook` accumulation in `isolation.py`. A separate
referral.

## 11. Research interpretation

**1. Was a new expected-return source found?** No. Carry is the strongest
candidate public data can express, and over these panels it is one currency, one
static position and one crash — with its non-yen half returning four pips per
pair over two years after giving back all its interest on spot.

**2. Is tick volume useful for monetisation?** Not as a filter. It knows about
magnitude and not about cost-clearing magnitude, and applied to a carry position
it removes the wrong days — the ones it keeps are the losing ones.

**3. What is price-derived information limited to?** Describing volatility.
Across six packages: a variance-ratio structure 6–18× below break-even, a retrace
geometry that dissolves into a selection artefact, and a volume signal that
forecasts realised volatility at `z ≈ +10` and forecasts nothing about whether a
move pays. Every one is about **magnitude**. Cost is charged on **direction**.

**4. Is carry implementable?** Unknown from here — but less unknowable than the
first version said. The broker markup (§9.4) is not obtainable from public data;
the **cross-currency basis** (§9.7) is, from public forward points for the
majors, and it is the larger and more measurable of the two unmeasured terms.

**5. How much does the financing difference matter?** Decisively. `+0.13 / +0.19`
pips per pair per day is consumed by a markup of a few tenths of a basis point.
No favourable financing assumption has been demonstrated.

**6. Is it worth going on to COT or implied volatility?** The programme's gap is
a **direction-bearing expected return**, and on that axis COT is the better
candidate: free and public from the CFTC, weekly, with a reversal hypothesis at a
horizon carry showed is affordable. Three constraints belong in the case up
front: the report is published Friday for the prior Tuesday, so a **≥3-day
publication lag** must be honoured — this is the plan's own vintage rule, and
unlike policy rates it binds here; legacy and disaggregated formats are different
objects with a 2006 break; and **IMM futures give USD-cross series only**, so COT
can express a USD-versus-one-currency view but **cannot rank eight currencies**,
which is the construction the carry work just used.

Implied volatility should **not** be ranked last for the reason the first version
gave. "It prices the layer that already works" conflates realised-volatility
forecasting with two distinct objects: the **variance risk premium**, which is
return-bearing, and **risk reversals / option skew**, which are direction-bearing
— the thing the programme is missing. The honest reason to rank it last is
acquisition: FX option surfaces are not freely and reproducibly public
historically, which is the criterion the plan actually sets.

**7. Is there a fresh-replication candidate?** **No.** The plan's criteria
require gross edge, positive after cost, breadth, non-catastrophic tail and a
working simple baseline. `cross_sectional_k3` fails breadth and tail, and §4.2
shows it is not even a cross-sectional strategy on these panels. Nothing is
forwarded, and the `N = 1` forward budget stays unspent.

## 12. Final decision

**No fresh-replication candidate. The expected-return layer is empty and the
opportunity layer is thinner than the first version of this document claimed.**

What is established: an exogenous anchor picks out days that **move about 13–33%
more**, replicating across pairs and panels at `p ≈ 0.01`. What is **not**
established, and was wrongly claimed: that those days are cheaper to trade. They
are marginally more expensive.

That changes what to do next only in emphasis. The programme still lacks a
direction-bearing expected return, and no amount of opportunity structure
substitutes for one. Recommended, each needing its own authorisation:

1. **COT positioning** — with the three constraints in §11.6 stated in the
   research case before any acquisition;
2. **A real economic calendar with real-time vintages** — which would widen §7's
   anchor from rate *changes* to all scheduled events and remove the surprise
   bias and the forward-knowability problem;
3. **The cross-currency basis from public forward points** — cheaper than either,
   and it bounds the largest unmeasured term in the carry work;
4. **Broker financing history** — not a research source, but the question that
   decides whether any carry result could ever be implemented.

## 13. Final status

* **`ECONOMIC_EDGE_SOURCE_NOT_FOUND_EXOGENOUS_MOVEMENT_STRUCTURE_ESTABLISHED`**
* `CARRY_EDGE_NOT_SUPPORTED`
* `OPPORTUNITY_TIMING_ADDS_NO_INCREMENTAL_VALUE`
* `CALENDAR_EVENT_MOVEMENT_STRUCTURE_SUPPORTED`
* `EVENT_DAY_COST_ADVANTAGE_NOT_ESTABLISHED`
* `ML_NOT_JUSTIFIED` — prerequisite 3 fails
* `NON_DECISION_BEARING_EXPLORATORY_ONLY` ·
  `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
* **Fresh historical pool `2016-06-02 … 2021-04-25` untouched.** Historical OOS
  untouched. The dead window and the future untouched epoch untouched.
* **Formal Confirmation not performed.** No broker, demo or live contact. No
  order of any kind. No production deployment.
* External data acquired: BIS policy rates and **four** FRED series — three
  overnight rates used as a cross-check and `ECBDFR` used as a **primary input**
  for EUR. All public, all keyless, all recorded with provenance. **No paid
  contract, no metered API, no account, no secret.**
* `PRODUCTION_READINESS_NOT_CLAIMED`.

Fresh historical replication, further external acquisition and Formal
Confirmation each await an explicit human + ChatGPT instruction.
