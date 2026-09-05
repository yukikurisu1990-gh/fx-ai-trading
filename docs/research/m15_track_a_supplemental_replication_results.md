# M15 Track A — Supplemental Historical Replication: the result

**`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `PRODUCTION_READINESS_NOT_CLAIMED`.**

Plan: `docs/research/m15_track_a_supplemental_replication_plan.md`, committed at
`ae18734` **before** any supplemental byte was read. Base master `eab8f255`.

**Classification:
`MULTI_DAY_REVERSAL_FAILED_SUPPLEMENTAL_HISTORY_REPLICATION`.**

---

## 0. The authorisation this round ran under

A read of real market data is Red. The act came in the instruction that opened
this round, which named the operation, the resolution rule for the span, the
pairs and the timeframe, and said in terms:

> 上記ルールで決定された pre-2025-04-25 supplemental historical span を Track A
> exploratory replication 用に読むことを許可します。

Two independent audit roles reported, correctly, that **the act was not recorded
anywhere in the repository** — the plan and this file described the span and the
candidate but never the authorisation, no grant artefact exists for
`track_a_supplemental_historical_read`, and the only claim of authorisation sat
in an uncommitted edit to a *different* file. That is the R1 post-mortem finding
repeated: the blocker is the record, not the run. Section 0 exists because of it,
and the governance updates that reference it are committed in the same change.

What this authorisation is and is not: it is an explicit human authorisation for
**this** span, **these** operations and **this** exploratory purpose. It is not a
`ReadGrant`, it carries no fingerprint binding and it appends to no ledger,
because this route is outside `scripts/m15_track_a/` and outside the R1
fingerprint surface by design. It authorises nothing else — not the OOS slice,
not the forward epoch, not a re-read, and not the next round.

## 1. The answer, in one paragraph

The frozen candidate does not replicate. On `2023-04-26 … 2025-04-24` — three
times the original span, the same twenty pairs, the same code, the same cost
model — it loses **−577.3 pips per pair**, and it loses **−426.5 gross**, before
any cost is charged. One pair of twenty is net-positive; sixteen of twenty are
negative on gross. All nine cells of the robustness neighbourhood are negative on
both. The signal's information coefficient, **−25.07%** on the development
window, is **+2.35%** here: not weaker, **absent**. And the read had about
**76%** power to detect the effect it was testing for, so a null result is a
result rather than a shrug.

## 2. What was read

| | |
| --- | --- |
| span | `2023-04-26 … 2025-04-24`, 730 UTC dates, exactly as pre-registered |
| pairs | `PAIRS_20`, all twenty |
| operations | `track_a_supplemental_historical_read`, `track_a_supplemental_m15_derivation` |
| scope | `SUPPLEMENTAL_EXPLORATORY_HISTORY` → now `EXPLORATORY_SEEN_DATA` |
| source | `data/candles_{pair}_M1_3650d_BA.jsonl` — the **ten-year** archive |
| M1 rows | **14,745,861** |
| M15 bars | **993,878** (complete 936,810 · incomplete 57,068 = 5.7%) |
| bars outside the span | **0** on all twenty pairs |

The development-window guard `bars._assert_span` still refuses every well-formed
span it refused before, including this one, and the supplemental route has its
own guard whose upper bound *is* `DEVELOPMENT_START_UTC`, so the two windows are
adjacent by construction rather than by coincidence.

**One claim in the first version of this section was false and is withdrawn.** It
said neither route could reach the OOS slice, the dead window or the forward
epoch, and that this had been "verified in both directions". The verification
covered well-formed dates only. An audit found that a **truncated** bound defeats
both guards: `end="2025"` sorts below `"2025-04-25"` and passes, and the scan's
`end + "T99"` sentinel then sorted *above* `"2025-12-29T…"` because `-` (0x2D)
precedes `T` (0x54) — so OOS rows reached `json.loads`, which under
`HISTORICAL_EXPLORATORY_OOS_PRISTINE_CLAIM_WITHDRAWN` is a read. The same hole
existed in the development reader.

Both are now closed: a bound must be an exact `YYYY-MM-DD` or it is refused
(`MalformedUtcDateError`), the sentinel is gone and the scan compares date
prefixes of equal width, and `load`/`build_cache` validate the **rows** they
serve rather than only the request that asked for them. The change to
`bars._assert_span` strictly *narrows* it — every well-formed span it admitted it
still admits, every span it refused it still refuses — which is the opposite of
the weakening the instruction forbade. Twenty-one tests cover the hole and a
mutation battery over the survivors an audit named now kills **14 of 14** where
the first version killed 8.

**No forbidden row was in fact read.** Both audits verified this independently
against the caches: global ts range `2023-04-26 00:00Z … 2025-04-24 23:45Z`, zero
rows outside it on any pair.

Nothing under `scripts/m15_track_a/` was touched. An audit re-derived
`implementation_surface()` → 32 files and `implementation_fingerprint()` →
`e147542a…`, matching the recorded grant, and re-ran the WP5 reader-freedom pin
(21 passed). The two grants in force are unaffected.

## 3. The frozen candidate — `lookback=480, hold=480, entry_z=1.0`

Frozen by `round2.py::CENTRE`, committed `c076988`, merged `eab8f255`. An audit
established the freeze by timeline rather than by assertion: `CENTRE` landed at
21:46:07, the plan at 21:47:43, and the **first supplemental parquet was written
at 21:48:56**. `round2.py`, `engine.py`, `bars.py` and `familywise.py` are
byte-identical to their pre-read blobs. The development figure reproduces at
**+262.1**, identical to Round 2's registered value.

| | original `2025-04-25…12-28` | **supplemental `2023-04-26…2025-04-24`** | combined |
| --- | ---: | ---: | ---: |
| net pips/pair | **+262.1** | **−577.3** | −315.2 |
| gross pips/pair | +324.1 | **−426.5** | — |
| cost pips/pair | 62.0 | 150.8 | — |
| mean IC | **−25.07%** | **+2.35%** | — |
| pairs with negative IC | 19/20 | 7/20 | — |
| pairs net-positive | 17/20 | **1/20** | — |
| pairs **gross**-negative | 2/20 | **16/20** | — |
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
is already −426.5, on 16 of 20 pairs.

**The two periods come from different archive files** — `*_M1_365d_BA` for the
development window, `*_M1_3650d_BA` for the supplemental one. The scanning logic
is line-for-line the same and `to_m15` is shared, so the *code* is common, but
the extraction is not, and §8's spread figures should be read with that in mind.
An audit checked the seam across the 10 pairs with a true 15-minute join at
`2025-04-24 23:45Z → 2025-04-25 00:00Z` and found gaps of 0.1 to 4.2 median bar
moves, mixed in sign, mean ≈ −0.7 pips. No level shift; the archives agree.

## 4. Rates, because the spans differ

248 dates against 730 is not a fair comparison of totals.

| | days traded | total | rate pips/pair/day | CI95 |
| --- | ---: | ---: | ---: | --- |
| original | 212 | +262.1 | **+1.2364** | `[+0.0853, +2.4534]` |
| supplemental | 624 | −577.3 | **−0.9252** | `[−1.8638, −0.0437]` |
| combined | 836 | −315.2 | −0.3770 | `[−1.1602, +0.3704]` |

**Difference (supplemental − original): −2.1616/day, CI95
`[−3.6809, −0.7023]`, two-sided `p = 0.0042`.**

Had the original rate been the truth, the supplemental period would have returned
**+771.5**. It returned −577.3, a shortfall of **−1,348.8** pips per pair. That
projection is this round's pre-specified alternative and §6 is powered against
it.

Two qualifications, both raised by audit and both narrowing what §4 may claim.

* **That `p` is a percentile bootstrap (CI inversion), not a null-hypothesis
  test.** The resampling distribution is centred on the observed difference, so
  it reports how far zero sits in its tail. It is robust to block length
  (0.006 at 1 day, 0.0042 at 5, 0.0011 at 10, 0.0000 at 20), and the daily series
  is *negatively* autocorrelated (supplemental lag-1 −0.227, Ljung-Box(10)
  p ≈ 0.000), so longer blocks shrink rather than inflate it. It is not, however,
  "the strongest single number this programme has produced" — an earlier draft
  said that and it is withdrawn.
* **It does not show the periods are draws from different processes.** It treats
  the original rate as a fixed comparator, and the original period is where
  Round 1's 1,078-fit search *chose* this neighbourhood. Round 2's own family-max
  null over just 27 cells has a median of +83.4 (≈ +0.393/day), so a third of the
  observed +1.2364 is what pure selection returns under a strict null before
  Round 1's larger search is counted. "The original estimate was selection noise
  and the true rate is ≤ 0 in both periods" fits these data as well as a regime
  change does. Both readings give the same classification.

The combined standard error shrank on the rate scale, 0.6081 → 0.3911 — but that
is close to what pooling 212 days with 624 gives for free (√(212/836) = 0.503
against an observed 0.643), so it is weak evidence of anything. On the **total**
scale the uncertainty grew, 128.9 → 322.9, and combined power fell to 0.16. The
honest summary is that the extra history moved the point estimate below zero, not
that it tightened the combined interval in any informative way.

## 5. Diagnostics on the supplemental period

**Chronological blocks (8 × ~91 days).** Net positive in **2 of 8**; mean IC
negative in 5 of 8, never near the development level, and positive in three. IC
windows are masked by timestamp, not row position — per-pair bar counts differ by
up to 186 over this span, and an audit found the positional version put the IC
and the net of a single table row on slightly different windows.

| block | span | mean IC | pairs IC<0 | net | pairs+ |
| --- | --- | ---: | ---: | ---: | ---: |
| 1 | 2023-04-26…07-25 | −1.04% | 10/20 | −222.1 | 5/20 |
| 2 | 2023-07-25…10-24 | −10.55% | 14/20 | +60.0 | 13/20 |
| 3 | 2023-10-24…2024-01-25 | +0.29% | 10/20 | −40.5 | 8/20 |
| 4 | 2024-01-25…04-24 | −27.86% | 19/20 | +7.0 | 10/20 |
| 5 | 2024-04-24…07-24 | +18.31% | 3/20 | −139.9 | 4/20 |
| 6 | 2024-07-24…10-23 | +3.79% | 8/20 | −104.6 | 4/20 |
| 7 | 2024-10-23…2025-01-24 | −9.99% | 12/20 | −29.7 | 11/20 |
| 8 | 2025-01-24…04-24 | −12.12% | 16/20 | −107.6 | 7/20 |

Block 4 is worth naming: IC −27.86% with 19/20 pairs negative — the development
window's own signature — and it still only made **+7.0** pips. A strongly
negative IC does not reliably become money at this scale, which is the Round 1
finding seen from the other side.

**Blocs.** JPY −728.9, non-JPY −512.4. Both negative. The development window's
JPY concentration (+632.2 against +262.1 overall) has no counterpart here; the
failure is not a JPY story.

**Leave-one-out.** Pair LOO ranges −615.4…−524.9 — **0 of 20 removals turn it
positive**. Currency LOO ranges −747.9 (drop USD) … −448.0 (drop EUR); all eight
negative.

**Day concentration, both tails.** The first version of this section removed only
the *best* days — the right question for a gain and the wrong one for a loss —
and concluded that "the supplemental loss is not carried by anything". **That
sentence was wrong and is withdrawn.** Both audits caught it.

| days removed | original | supplemental |
| --- | ---: | ---: |
| none | +262.1 (of 212 days) | −577.3 (of 624 days) |
| best 1 / 3 / 5 / 10 / 20 | +222.8 / +154.4 / +101.7 / **+7.8** / −139.5 | −699.9 / −791.6 / −865.2 / −1010.8 / −1225.8 |
| worst 1 / 3 / 5 / 10 / 20 | +291.0 / +334.6 / +376.1 / +455.9 / +555.4 | −512.4 / −388.3 / −295.4 / **−125.2** / **+148.1** |

So **78% of the supplemental loss sits in 10 days of 624, and 20 days flip its
sign** — the mirror image of the development window's ten-days-of-212, not its
opposite. Both periods are carried by a handful of days. That is a real
qualification on the *magnitude* of the supplemental loss, and §7 states what it
does and does not touch. Removal is a diagnostic and does not enter any rule.

**9-cell neighbourhood** (`lookback` × `hold` ∈ {384,480,576}², `entry_z=1.0`),
diagnostic only, not promoted:

| | h=384 | h=480 | h=576 |
| --- | ---: | ---: | ---: |
| **lb=384** | −397.8 | −473.7 | −532.5 |
| **lb=480** | −590.3 | **−577.3** | −557.2 |
| **lb=576** | −690.4 | −611.8 | −603.5 |

**0 of 9 positive on net and 0 of 9 positive on gross** (gross −229.7 … −544.5),
**1–5** pairs positive per cell, four cells with exactly one. There is no
neighbouring cell to retreat to.

**ATR-high secondary**, Round 2's tercile definition unchanged, no threshold
re-optimisation: `z=0.0` net −272.3 (gross −191.8, 4/20 pairs), `z=1.0` net
−134.2 (gross −77.6, 7/20 pairs). Less negative than the unconditioned family and
still negative. The plan named "ATR-high as a secondary" in the singular; running
it at both `entry_z` levels is a small unregistered expansion, and both are
reported rather than the better one.

An earlier draft ended this paragraph with "Round 2's `p = 0.030` cell does not
survive". **Withdrawn**: that cell is `lb480_h480_z0.0` at `atr_bucket='all'`,
which this round never evaluates, and the number that is actually about the ATR
axis is Round 2's `p = 0.003`. Nothing computed here speaks to either.

## 6. Detection power

Two-sided throughout, and on `|effect|` so a negative effect is not read as no
effect. The **pre-specified alternative** is +771.5 — what this period returns if
the development rate is the truth — and it leads, because power at the *observed*
effect is a monotone restatement of the p-value and says nothing about how good a
test this was. An earlier draft led with the observed-effect column and
understated the study by a factor of about 1.4; an audit caught it, and the error
ran in favour of the conclusion, which is not a reason to leave it.

| | net | effect sd | power vs **+771.5** | MDE(80%) | power at observed | +calendar days for 80% |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| original | +262.1 | 128.9 | — | 361.2 | 0.53 | +220 |
| supplemental | −577.3 | 289.7 | **0.759** | 811.6 | 0.51 | +712 |
| combined | −315.2 | 322.9 | — | 904.7 | 0.16 | +6,051 |

Under **Round 2's own family-max rule**, applied unchanged to the supplemental
9-cell family: critical value **+609.7**, family-wise `p` for the best cell
**0.9757**, and power against +771.5 of **0.699**.

Days are reported as **calendar** days, matching `round2_power`; an earlier draft
mixed trading days (+609) into the same column as Round 2's calendar figures and
made this round look like a correction of Round 2's arithmetic. In trading days
the supplemental figure is +609 and the original +190.

So: the supplemental read carried roughly **70–76% power against the effect it
was testing for** and found the opposite sign. Each period taken alone remains
underpowered *for its own effect* — that is the Round 2 conclusion and it still
holds — but the replication question is not the same question, and it was
answerable.

## 7. What this does and does not license

It **does** close the multi-day reversal as a candidate. Round 2 left it
`MULTI_DAY_REVERSAL_UNRESOLVED_INSUFFICIENT_DETECTION_POWER` and said only more
data could move it. More data arrived — three times as much — and the sign
inverted, before costs, on 16 of 20 pairs by gross and 19 of 20 by net, in 9 of 9
neighbouring cells, at ~76% power against the replication alternative, with IC
near zero in every equal-bar third of the period.

It does **not** establish a reliable negative effect in 2023–2025. That is a
different claim and the evidence for it is weak: the supplemental total is about
two standard errors from zero, sensitive to block length, and 20 days of 624
reverse its sign. The classification is about the *failure to replicate*, which
is robust, not about the *magnitude* of the loss, which is not.

It does **not** license the mirror image. The supplemental IC is `+2.35%`, so a
*momentum* version of the same rule would have made money over these 730 days.
That is an arithmetic consequence of the sign, not a finding: it was not
pre-registered, it is `POST_HOC_EXPLORATORY`, it was **not run**, and inverting a
failed rule on the data that refuted it is the search this round exists to avoid.

Nothing here is decision-bearing, nothing is holdout evidence, no
`EXPLORATORY_OOS_SLICE` or forward data was touched, and no new optimisation is
started from this result.

## 8. Integrity checks

Computed by `supplemental_replication.integrity` and written to
`supplemental_integrity.json`.

| | development | supplemental |
| --- | ---: | ---: |
| bars outside the span | 0 | 0 |
| pairs with monotone timestamps | 20/20 | 20/20 |
| duplicate timestamps | 0 | 0 |
| smallest gap between bars | 900 s | 900 s |
| NaN cells in `mid_c` / `spread_close_pips` | 0 | 0 |
| negative spreads | 0 | 0 |
| spread median / p99 (pips) | 2.30 / 17.6 | 1.90 / 14.0 |

The supplemental period is the *cheaper* one, which cuts against cost as an
explanation — bearing in mind §3's note that the two come from different archive
extractions. Re-aggregating raw M1 for a sampled day reproduces `mid_o`, `mid_c`
and `n_source_bars` in **96/96** buckets; `mid_h`/`mid_l` differ in 2/96 because
the committed `to_m15` takes the extremum of bid and ask separately and then
averages. The development window shows the same, so it is a property of the
shared bucketing applied identically to both periods.

Every number in this document is produced by committed code.
`python -m scripts.research.exploratory_m15.supplemental_replication` regenerates
`supplemental_primary_replication.json`, `supplemental_diagnostics.json`,
`supplemental_integrity.json` and `supplemental_power.json` under
`artifacts/track_a_scratch/` (gitignored, as Round 1's and Round 2's were), and
`supplemental.build_cache` produces `supplemental_data_summary.json`. Round 2's
post-mortem found that six of its seven artefacts came from uncommitted scratch
scripts and that this is why two arithmetic errors reached its report. The first
version of this section was itself computed in scratch — both audits noticed the
paragraph claiming committed provenance sitting three lines below numbers that
had none — which is why the checks are now in the driver.

`TRACK_A_SUPPLEMENTAL_HISTORICAL_REPLICATION_COMPLETED`.
