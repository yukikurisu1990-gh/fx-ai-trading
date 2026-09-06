# M15 Research Program — Round A: the pre-registered plan

**`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `PRODUCTION_READINESS_NOT_CLAIMED`.**

**Committed before any cell is computed.** Every bin boundary, condition family,
horizon and cell count below is fixed here. None may be adjusted after seeing a
number — the failure mode this programme has hit repeatedly is a family assembled
after the fact, and the correction for it is to fix the family first.

Base master: `b274762e4335f4f0fee7dc7b2ae93558e2db28b6` (the PR #467 merge).

---

## 1. What Round A is for

Two questions, and **neither of them is "does this make money"**:

* **T1** — where does a *tradable amount of movement* exist at all? Which
  `horizon × market state` cells contain forward excursions comfortably larger
  than the round-trip cost, and which are structurally too tight to trade
  whatever the signal?
* **T2** — under a bounded set of pre-registered market states, is the sign of
  the conditional forward drift **stable across the three seen periods**?

Round A produces no strategy, no candidate, no net PnL headline and no
optimisation. Its output is a map and a screen, used to decide whether Event
Economics, label redesign, ML meta-labelling or an Exit evaluation is the
rational next round.

## 2. Data scope — no new read

Three already-seen panels, from the existing M15 parquet caches:

| span | days | cache | state |
| --- | ---: | --- | --- |
| `2021-04-26 … 2023-04-25` | 730 | `momentum_replication_b` | `EXPLORATORY_SEEN_DATA` |
| `2023-04-26 … 2025-04-24` | 730 | `supplemental_replication` | `EXPLORATORY_SEEN_DATA` |
| `2025-04-25 … 2025-12-28` | 248 | `exploratory_round_1` | `EXPLORATORY_SEEN_DATA` |

`PAIRS_20`, all twenty. **Zero new market-data reads.** The fresh internal
replication pool `2016-06-02 … 2021-04-25` is **not touched**; neither is the
`EXPLORATORY_OOS_SLICE`, the dead window or the forward epoch. Round A adds no
reader route and widens no guard.

The three periods are reported **separately throughout**. The 2025 development
window is the most selection-contaminated of the three — every previous round
searched it — so where a rule needs a majority it is the **two 730-day periods
that must agree**, with 2025 read as corroboration or as counter-evidence, never
as the deciding vote.

## 3. T0 — the statistical infrastructure, and what is *not* built

Reused unchanged: `engine.atr_pips` / `zscore` / `donchian` / `higher_timeframe`,
`familywise.family_wise` (family-max, shared sign draw),
`momentum_inference.interval` (block bootstrap, CI, p) and its
`effective_independent_pairs` self-check, `round2`'s constants
(`Z_WINDOW = 480`, `ATR_PERIOD = 14`, `ATR_RANK_WINDOW = 960`, `N_PHASES = 8`).

New, and deliberately small:

* **A hypothesis ledger** — one row per research family ever run against the seen
  panels: id, round, population, target, condition family, horizon family,
  pre-specified or post-hoc, result, status. It exists so the cumulative
  multiplicity of reusing these three periods is *visible*, not so that a new
  governance object exists. It is a record, not a gate.
* **A standard diagnostic block** — every reported quantity carries: pips per
  pair per day, total, effective observations, effective independent pairs,
  JPY / non-JPY, best and worst 1/3/5/10/20-day contributions, block-bootstrap
  CI. Assembled from the existing functions above.

No production framework, no new gate, no surface inventory.

## 4. T1 — the Tradability Atlas

### 4.1 Dimensions, fixed here

| dimension | levels |
| --- | --- |
| horizon `H` (M15 bars) | **16** (4h), **48** (12h), **96** (24h), **192** (48h), **480** (5d) |
| ATR state | trailing tercile of `atr_pips(14)` ranked over 960 bars: **low / mid / high** |
| session | the decision bar's `session`: **asia / europe / us**, and **rollover** reported as its own state |
| pair bloc | **ALL** (20) / **JPY** (6) / **non-JPY** (14) |

Primary atlas: `5 × 3 × 3 = 45` cells per period. Session breakdown:
`5 × 4 × 3 = 60` cells per period. Both are **descriptive**: every cell is
reported, nothing is selected, so no multiplicity correction is owed and none is
claimed.

### 4.2 The excursion definition, tied to the engine

`engine.evaluate` holds `position.shift(1)` and earns `mid_c.shift(-1) - mid_c`,
so a decision at bar `t` is on risk from `t+1` and a hold of `H` bars exits at
`t+H+1`. The atlas uses exactly that window:

```
entry reference   P0 = mid_c[t+1]
path window       bars t+2 … t+H+1   (H bars, strictly after entry)
up excursion      max(mid_h over window) − P0        (pips)
down excursion    P0 − min(mid_l over window)        (pips)
terminal move     |mid_c[t+H+1] − P0|                (pips)
realized range    up + down
MFE (oracle)      max(up, down)   — the best any direction rule could reach
MAE at that MFE   the opposite excursion — the drawdown paid to reach it
```

`MFE` here is an **upper bound on capturable movement**, computed with knowledge
of the future *on purpose*. It is a tradability and label-design diagnostic and
is never a feature, never a signal and never enters a position. Section 4.5 fixes
that in writing.

### 4.3 Cost

The unchanged Round 1/2 `EXPLORATORY_ASSUMPTION`. Round-trip cost at the decision
bar = `spread_close_pips[t] + SLIPPAGE_PAD_PIPS` (0.5). R1's unauthorised
`cost_table` is not used and neither is anything derived from it.

### 4.4 Metrics per cell, per period

Observations; effective observations (`n / H`, the non-overlapping count);
mean and median of terminal move, MFE, MAE-at-MFE and realized range; the
10/25/50/75/90 quantiles of MFE and of terminal move; median round-trip cost;
the ratios `median MFE / cost` and `median |move| / cost`; and

```
P(MFE > 1 × cost),  P(MFE > 2 × cost),  P(MFE > 3 × cost)
P(|terminal move| > 1 × cost),  … > 2 × cost,  … > 3 × cost
median adverse excursion conditional on MFE > 2 × cost
```

### 4.5 Classification, fixed before the numbers exist

| label | rule |
| --- | --- |
| **Opportunity-rich** | `median MFE ≥ 3 × median cost` **and** `P(MFE > 2×cost) ≥ 0.50`, in **all three** periods |
| **Marginal** | `median MFE ≥ 1.5 × median cost` in all three periods, but not opportunity-rich |
| **Structurally unattractive** | `median MFE < 1.5 × median cost` in **any** period |

A cell that is opportunity-rich in one period and unattractive in another is
**not** reported as opportunity-rich; the three-period requirement is part of the
definition. No cell is promoted to a headline on one period's number.

**Prohibition, recorded here so it cannot be softened later:** MFE and MAE are
computed from future bars. They may be used to describe the opportunity set and
to derive candidate take-profit / stop distances for a *future* round's label
design. They may **not** be used as a conditioning variable, a filter, a feature
or an entry rule in Round A or any later round. Any use of them inside a position
decision is look-ahead.

## 5. T2 — the Conditional Sign Screen

### 5.1 Condition families, fixed here

Five families, all constructible from the existing M15 columns, all strictly
backward-looking. **Marginal, not crossed** — crossing them would blow the cell
budget and produce cells nobody could interpret.

| family | levels | count |
| --- | --- | ---: |
| **F1 ATR state** | trailing tercile of `atr_pips(14)` over 960 bars: low / mid / high | 3 |
| **F2 Volatility expansion** | `rv(96) / rv(384)` where `rv` is the rolling sd of 1-bar pip moves: **compression** (≤ 1) / **expansion** (> 1) | 2 |
| **F3 D1 trend state** | the sign of the last **completed** daily change, from `higher_timeframe(bars, 96)`: up / down | 2 |
| **F4 Range position** | quartile of `(close − low_192) / (high_192 − low_192)` from `donchian(192)`: Q1 / Q2 / Q3 / Q4 | 4 |
| **F5 Recent extreme move** | `|zscore(96-bar move, 480)| > 2`: extreme / normal | 2 |

**13 condition levels.**

### 5.2 Horizons and cell budget

`H ∈ {48, 192, 480}` — 12h, 48h and 5 days. Shorter than 48 is excluded because
Round 1 established that everything re-deciding within half a day is closed by
turnover arithmetic, and longer than 480 is excluded because the non-overlapping
count per pair falls below 30.

**13 levels × 3 horizons = 39 cells.** Under the 48 the instruction allows, and
the family is closed here. No condition variable, level or horizon may be added
after the run.

### 5.3 The context direction, fixed per family

A cell's drift needs a direction to be signed against. It is fixed per family
**before** any measurement, from that family's own prior in the existing
literature of this programme:

| family | context direction `d(t)` | why this one |
| --- | --- | --- |
| F1, F2, F5 | `−sign(mid_c[t] − mid_c[t−H])` | symmetric states carry no directional prior of their own; the reversal convention is the one every previous round used, so the sign is comparable to them |
| F3 | `+sign(last completed daily change)` | a higher-timeframe trend state's own claim is continuation |
| F4 | `−sign(rangepos − 0.5)` → fade the extreme: `+1` in Q1/Q2, `−1` in Q3/Q4 | a range-position state's own claim is mean reversion toward the middle |

A cell's drift being **negative** is as informative as its being positive: it
means the state's own prior is wrong there, consistently.

### 5.4 The estimator — non-overlapping, phase-averaged

For each cell, horizon `H`, pair and each of `N_PHASES = 8` rebalance offsets,
take the bars `t ≡ phase (mod H)` that fall in the cell and compute

```
contribution(t) = d(t) × (mid_c[t+H+1] − mid_c[t+1]) / pip_size
```

Within a phase these entries do not overlap. The eight phases are averaged;
phase is a nuisance parameter and is never selected. Round 1 found that a single
phase locks to one hour of the day on this corpus, which is why this is not
optional.

Reported per cell per period:

* `mean_pips_per_entry` — the H-bar drift under the context direction. **This is
  the quantity compared against the round-trip cost.**
* `rate_pips_per_day` = `mean_pips_per_entry × 96 / H` — the rate while in the
  state
* `cell_share` — the fraction of bars in the cell
* `contribution_pips_per_day` = `rate × cell_share` — the economic contribution
  of trading only this state
* effective observations (non-overlapping entries), effective independent pairs
* per-pair breadth, JPY / non-JPY split
* block-bootstrap CI and two-sided `p` on the daily contribution series
* best and worst 1/3/5/10/20-day contributions

**Gross only.** T2 subtracts no cost and builds no strategy; cost enters as the
yardstick `mean_pips_per_entry / round-trip cost` and through T1.

### 5.5 Multiplicity

Family-max over the 39 cells with a shared sign draw, via the existing
`familywise` machinery, reported for the record. It is **not** the gate. Round 2's
lesson is that a `p` near 0.05 on this corpus is a band rather than a boundary;
what Round A is looking for is **consistency, magnitude, breadth and robustness**,
and the gate is §5.6.

### 5.6 What may be passed to T4 — all six, not any one

A cell becomes a **structural candidate** only if:

1. the **two 730-day periods agree in sign**;
2. the 2025 development window is **not strong counter-evidence** — defined as:
   its drift is not opposite in sign *and* larger in magnitude than the smaller of
   the two agreeing periods;
3. `|mean_pips_per_entry| ≥ 2 × median round-trip cost` in both agreeing periods
   — an effect too small to pay for itself is not a candidate however consistent;
4. T1 classifies the corresponding `horizon × ATR × bloc` cell as
   **opportunity-rich or marginal**, never structurally unattractive;
5. effective observations ≥ **30 per period** and effective independent pairs
   ≥ **3**;
6. removing the best 10 days does **not** flip the sign in either agreeing period.

**Sign agreement alone does not qualify a cell.** With 39 cells and two periods,
roughly ten cells will agree in sign by chance; that is the arithmetic the other
five conditions exist to survive.

If zero cells qualify, Round A reports zero. That is a result.

## 6. Decision rule for the next round, fixed here

| case | condition | next round |
| --- | --- | --- |
| **A** | T1 has opportunity-rich cells **and** T2 yields ≥1 structural candidate | **T4 Event Economics** — no ML yet |
| **B** | T1 has opportunity **but** T2 yields zero structural candidates | **cost-aware / first-passage label redesign** — direction set aside |
| **C** | T1 finds cost-clearing opportunity broadly absent | **Exit evaluation** for price-only M15 research |
| **D** | structure appears but the sample cannot support it | compute the required sample and power, then judge whether any future round can |

Round A stops at the classification. **T4, label redesign, ML, fresh reads and
Formal Confirmation are each their own later decision** and none is started here.

## 7. Not done in Round A

No strategy optimisation, no ML training, no feature search, no hyperparameter
search, no fresh historical read, no OOS read, no Formal Confirmation, no
candidate freeze, no broker or production claim, no new gate, no general
adversarial audit. Unconditional momentum, unconditional reversal, simple trend,
simple breakout, EMA/RSI/Donchian tuning and hyperparameter-only ML are **not
re-explored**; they are closed and the ledger records them as such.
