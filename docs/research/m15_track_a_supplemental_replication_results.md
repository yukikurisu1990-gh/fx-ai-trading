# M15 Track A — Supplemental Historical Replication: the result

**`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `PRODUCTION_READINESS_NOT_CLAIMED`.**

Plan: `docs/research/m15_track_a_supplemental_replication_plan.md`, committed at
`ae18734` **before** any supplemental byte was read. Base master `eab8f255`.

**Classification:
`MULTI_DAY_REVERSAL_FAILED_SUPPLEMENTAL_HISTORY_REPLICATION`.**

---

## 1. The answer, in one paragraph

The frozen candidate does not replicate. On `2023-04-26 … 2025-04-24` — three
times the original span, from the same twenty pairs, the same code, the same
cost model — it loses **−577.3 pips per pair**, and it loses **−426.5 gross**,
before any cost is charged. One pair of twenty is positive. All nine cells of the
robustness neighbourhood are negative, gross and net. The signal's information
coefficient, **−25.07%** on the development window, is **+2.35%** here: not
weaker, **absent**, and if anything on the momentum side. The two periods'
per-day rates differ by −2.16 pips/pair/day with a bootstrap CI95 of
`[−3.68, −0.70]` and `p = 0.0042` — the strongest single number this programme
has produced about the multi-day reversal, and it points at the development
result being period-specific.

## 2. What was read

| | |
| --- | --- |
| span | `2023-04-26 … 2025-04-24`, 730 UTC dates, exactly as pre-registered |
| pairs | `PAIRS_20`, all twenty |
| operations | `track_a_supplemental_historical_read`, `track_a_supplemental_m15_derivation` |
| scope | `SUPPLEMENTAL_EXPLORATORY_HISTORY` → now `EXPLORATORY_SEEN_DATA` |
| M1 rows | **14,745,861** |
| M15 bars | **993,878** (complete 936,810 · incomplete 57,068 = 5.7%) |
| bars outside the span | **0** on all twenty pairs |

The development-window guard `bars._assert_span` is **unchanged** and still
refuses everything it refused before, including this span. The supplemental route
has its own guard, which refuses `≥ 2025-04-25` and `< 2023-04-26`; neither route
can reach the other's window and neither can reach the `EXPLORATORY_OOS_SLICE`,
the dead window or the forward epoch. Verified in both directions before the
read. Nothing under `scripts/m15_track_a/` was touched, so the R1 grants and the
fingerprint `e147542a…` are unaffected.

## 3. The frozen candidate — `lookback=480, hold=480, entry_z=1.0`

Frozen by `round2.py::CENTRE`, committed `c076988`, merged `eab8f255`, before
this branch existed. It did not move. Its development figure reproduces at
**+262.1**, identical to the Round 2 registered value, which is the evidence that
the evaluation path is the same one.

| | original `2025-04-25…12-28` | **supplemental `2023-04-26…2025-04-24`** | combined |
| --- | ---: | ---: | ---: |
| net pips/pair | **+262.1** | **−577.3** | −315.2 |
| gross pips/pair | +324.1 | **−426.5** | — |
| cost pips/pair | 62.0 | 150.8 | — |
| mean IC | **−25.07%** | **+2.35%** | — |
| pairs with negative IC | 19/20 | 7/20 | — |
| pairs net-positive | 17/20 | **1/20** | — |
| closed trades | 353 | 989 | — |
| average trade | +14.27 | −11.62 | — |
| Sharpe-like | +2.18 | −1.32 | — |
| max drawdown | −96.0 | −667.0 | — |
| turnover/yr | 51.7 | 49.4 | — |

The combined column is shown because the plan requires it and for no other
reason. **A negative supplemental period is not a replication whatever the
combined figure says**, and here the combined figure is negative too.

Cost sensitivity (net pips/pair): supplemental **−615.0** at ×1.25, **−652.7** at
×1.50, **−728.1** at ×2.0, **−879.0** at ×3.0. Cost is not what killed it — gross
is already −426.5.

## 4. Rates, because the spans differ

248 dates against 730 is not a fair comparison of totals.

| | days traded | total | rate pips/pair/day | CI95 |
| --- | ---: | ---: | ---: | --- |
| original | 212 | +262.1 | **+1.2364** | `[+0.0853, +2.4534]` |
| supplemental | 624 | −577.3 | **−0.9252** | `[−1.8638, −0.0437]` |
| combined | 836 | −315.2 | −0.3770 | `[−1.0784, +0.3097]` |

**Difference (supplemental − original): −2.1616/day, CI95
`[−3.6809, −0.7023]`, two-sided `p = 0.0042`.**

Had the original rate been the truth, the supplemental period would have returned
**+771.5**. It returned −577.3, a shortfall of **−1,348.8** pips per pair.

The combined standard error did shrink — 0.6081 → 0.3557 — so the extra history
**did** reduce the uncertainty. It reduced it around a point estimate that had
moved below zero.

## 5. Diagnostics on the supplemental period

**Chronological blocks (8 × ~91 days).** Net positive in **2 of 8**; mean IC
negative in 5 of 8 but never near the development level, and positive in three.

| block | span | mean IC | pairs IC<0 | net | pairs+ |
| --- | --- | ---: | ---: | ---: | ---: |
| 1 | 2023-04-26…07-25 | −1.08% | 10/20 | −222.1 | 5/20 |
| 2 | 2023-07-25…10-24 | −10.65% | 14/20 | +60.0 | 13/20 |
| 3 | 2023-10-24…2024-01-25 | +0.40% | 10/20 | −40.5 | 8/20 |
| 4 | 2024-01-25…04-24 | −27.89% | 19/20 | +7.0 | 10/20 |
| 5 | 2024-04-24…07-24 | +18.55% | 3/20 | −139.9 | 4/20 |
| 6 | 2024-07-24…10-23 | +3.61% | 8/20 | −104.6 | 4/20 |
| 7 | 2024-10-23…2025-01-24 | −10.12% | 12/20 | −29.7 | 11/20 |
| 8 | 2025-01-24…04-24 | −12.09% | 16/20 | −107.6 | 7/20 |

Block 4 is worth naming: IC −27.89% with 19/20 pairs negative, i.e. the
development window's own signature, and it still only made **+7.0** pips. A
strongly negative IC does not reliably become money at this scale — which is the
Round 1 finding, seen again from the other side.

**Blocs.** JPY −728.9, non-JPY −512.4. Both negative. The development window's
JPY concentration (+632.2 against +262.1 overall) has no counterpart here; the
failure is not a JPY story.

**Leave-one-out.** Pair LOO ranges −615.4…−524.9 — **0 of 20 removals turn it
positive**. Currency LOO ranges −747.9 (drop USD) … −448.0 (drop EUR); all eight
negative.

**Top-day concentration.** Removing the best days makes it *worse*, which is the
opposite of the development window: −577.3 → **−699.9** (top 1) → −791.6 (top 3)
→ −865.2 (top 5) → −1,010.8 (top 10). For contrast the development window went
+262.1 → +7.8 after removing its ten best days — i.e. the original result was
carried by ten days out of 212 and the supplemental loss is not carried by
anything.

**9-cell neighbourhood** (`lookback` × `hold` ∈ {384,480,576}², `entry_z=1.0`),
diagnostic only, not promoted:

| | h=384 | h=480 | h=576 |
| --- | ---: | ---: | ---: |
| **lb=384** | −397.8 | −473.7 | −532.5 |
| **lb=480** | −590.3 | **−577.3** | −557.2 |
| **lb=576** | −690.4 | −611.8 | −603.5 |

**0 of 9 positive on net and 0 of 9 positive on gross** (gross −229.7 … −544.5),
2–5 pairs positive per cell. There is no neighbouring cell to retreat to.

**ATR-high secondary**, Round 2's tercile definition unchanged, no threshold
re-optimisation: `z=0.0` net −272.3 (gross −191.8, 4/20 pairs), `z=1.0` net
−134.2 (gross −77.6, 7/20 pairs). Less negative than the unconditioned family and
still negative. Round 2's `p = 0.030` cell does not survive.

## 6. Detection power, updated

Two-sided throughout, and on `|effect|` so that a negative effect is not read as
no effect.

| | net | effect sd | MDE(80%) | \|obs\|/MDE | power | extra days for 80% |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| original | +262.1 | 128.9 | 361.2 | 0.73 | 0.53 | +190 |
| supplemental | −577.3 | 289.7 | 811.6 | 0.71 | 0.51 | +609 |
| combined | −315.2 | 322.9 | 904.7 | 0.35 | 0.16 | — |

Under **Round 2's own family-max rule**, applied unchanged to the supplemental
9-cell family: critical value **+609.7**, family-wise `p` for the best cell
**0.9757**, power at a +262.1 effect **0.131**.

So the question "does more data resolve it" has two answers and they point the
same way. Per-period, no: each period on its own still sits near power 0.5. On
the comparison, **yes** — the difference between the two periods is the one
quantity here that is well separated from zero (`p = 0.0042`), and it says the
periods are not draws from the same process.

## 7. What this does and does not license

It **does** close the multi-day reversal as a candidate. Round 2 left it
`MULTI_DAY_REVERSAL_UNRESOLVED_INSUFFICIENT_DETECTION_POWER` and said only more
data could move it. More data arrived — three times as much — and moved it to
negative, before costs, on 19 of 20 pairs, in 9 of 9 neighbouring cells.

It does **not** license the mirror image. The supplemental IC is `+2.35%`, so a
*momentum* version of the same rule would have made money over these 730 days.
That is an arithmetic consequence of the sign, not a finding: it was not
pre-registered, it is `POST_HOC_EXPLORATORY`, it was **not run**, and inverting a
failed rule on the data that failed it is the search this round exists to avoid.

Nothing here is decision-bearing, nothing here is holdout evidence, no
`EXPLORATORY_OOS_SLICE` or forward data was touched, and no new optimisation is
started from this result.

## 8. Integrity checks

Timestamps strictly increasing with no duplicates and no sub-15-minute gaps on
all twenty pairs; no NaNs; no negative spreads; spread median 1.90 pips against
the development window's 2.30 and p99 14.0 against 17.6 — i.e. the supplemental
period is the *cheaper* one, which cuts against cost as an explanation.
Re-aggregating raw M1 for a sampled day reproduces `mid_o`, `mid_c` and
`n_source_bars` in 96/96 buckets; `mid_h`/`mid_l` differ in 2/96 because the
committed `to_m15` takes the extremum of bid and ask separately and then
averages. The development window shows the same in 1/96 buckets, so it is a
property of the shared bucketing applied identically to both periods, not a
supplemental-route defect.

Every number above is produced by committed code —
`scripts/research/exploratory_m15/supplemental_replication.py`, run as a module,
regenerates `supplemental_primary_replication.json`, `supplemental_diagnostics.json`
and `supplemental_power.json` under `artifacts/track_a_scratch/` (gitignored, as
Round 1's and Round 2's were). Round 2's post-mortem found that six of its seven
artefacts came from uncommitted scratch scripts and that this is why two
arithmetic errors reached its report; the driver exists so that cannot happen
here. The figures in this document were checked against a fresh run of it, and
`supplemental_data_summary.json` comes from `supplemental.build_cache`.

`TRACK_A_SUPPLEMENTAL_HISTORICAL_REPLICATION_COMPLETED`.
