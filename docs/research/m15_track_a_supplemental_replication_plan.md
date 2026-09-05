# M15 Track A — Supplemental Historical Replication: the pre-read record

**`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `PRODUCTION_READINESS_NOT_CLAIMED`.**

**This file is committed before a single byte of the supplemental history is
read.** It fixes two things that must not be chosen after the data is seen: the
span, and the candidate. Round 2's own failure was a headline computed on a
quantity that had not been registered, and the fix for that is to register the
quantity.

Base master: `eab8f255d4ce57240e3e7f66110e5394fc8ded9e` (the PR #465 merge).

---

## 1. The question

Round 2 classified the multi-day reversal
`MULTI_DAY_REVERSAL_UNRESOLVED_INSUFFICIENT_DETECTION_POWER`: present in the
sample, not separable from zero by the pre-registered test, and needing about
3.67× the span for 80% power. Round 2 also said, correctly, that no amount of
further looking at those 248 days would change it.

So this round does not look at them again. It applies the **frozen** candidate to
**earlier** history and asks one question: **does the sign replicate?**

Not "can it be made to work there" — the candidate does not move. If the
supplemental period is negative, that is the finding.

## 2. The span, resolved from metadata before any content was read

`artifacts/oanda_archive_2026-05-31/candles_manifest.json` records `first_time`
and `last_time` per file for the 2026-05-31 ten-year snapshot. All twenty
`M1_3650d_BA` files start **2016-06-02** and end 2026-05-29, so the common
availability floor is 2016-06-02 and the binding constraint is the instruction's
730-day cap, not the archive.

| | |
| --- | --- |
| end date | **2025-04-24** — the day before the development corpus starts |
| start date | **2023-04-26** — 730 calendar days inclusive, the instruction's cap |
| **supplemental span** | **`2023-04-26 … 2025-04-24`, 730 UTC dates** |
| pairs | the registered `PAIRS_20`, all twenty |
| source | `data/candles_{pair}_M1_3650d_BA.jsonl` |

The start is mechanical: `end − 729 days`, because the archive reaches back to
2016 for every pair and the cap binds first. **No performance was consulted.**
Nothing here was chosen to make a period look good, and the span was written down
before the reader that can open it existed.

## 3. The scope, and what it is not

`SUPPLEMENTAL_EXPLORATORY_HISTORY`. Reading it makes it
`EXPLORATORY_SEEN_DATA`, like the development corpus, and it is **never formal
evidence**.

Two new operation names, added only where they are needed:

* `track_a_supplemental_historical_read`
* `track_a_supplemental_m15_derivation`

**What is deliberately not done.** The development-window guard
(`bars._assert_span`, which refuses anything before `2025-04-25` or at/after
`2025-12-29`) is **not relaxed, widened or parameterised**. It keeps refusing
exactly what it refused yesterday. The supplemental read is a **separate route**
with its own constants and its own guard, so the existing prohibition is
untouched rather than made conditional — the difference between adding a door
and removing a wall.

Nor is `scripts/m15_track_a/` touched. The gated R1 route, the two exercised
grants and the implementation fingerprint `e147542a…` are all outside this work;
`scripts/research/` is off the fingerprint surface, so the grants stay valid.

**What stays forbidden and is not read**: the historical
`EXPLORATORY_OOS_SLICE` (`2025-12-29 … 2026-02-28`), the dead window, the forward
epoch, and everything after `2025-04-24` other than the already-seen development
corpus. The ten-year archive physically contains all of them, which is exactly
why the supplemental reader clips at both ends rather than only at one.

## 4. The candidate, frozen before the data exists

**`lookback = 480`, `hold = 480`, `entry_z = 1.0`.**

It is not frozen by this sentence. It is frozen by
`scripts/research/exploratory_m15/round2.py::CENTRE = (480, 480)`, committed at
`c076988` and merged as `eab8f255` — **before** this branch was created and
before any supplemental byte was read. The replication runs that code unmodified:
same `_signal`, same 8-phase averaging, same `engine.evaluate`, same cost model.

**This candidate does not move.** Not after seeing the supplemental result, not
"slightly", not "to match the earlier regime".

## 5. What else is allowed, and what it is for

A **9-cell robustness neighbourhood** — `lookback` ∈ {384, 480, 576} ×
`hold` ∈ {384, 480, 576}, `entry_z` fixed at 1.0. It is a local-stability
diagnostic. **The best of the nine is not promoted to the headline**, whatever it
shows.

**ATR-high as a secondary**, using Round 2's committed tercile definition
unchanged — `round2._signal(..., atr_bucket="high")`, trailing rank over 960
bars, no re-optimisation of the threshold.

The **cost model is Round 1/2's unchanged** `EXPLORATORY_ASSUMPTION`: per-side
`(observed spread + 0.5) / 2` on mid-based returns. Reported at ×1.00, ×1.25,
×1.50, ×2.0, ×3.0. R1's unauthorised `cost_table` is not used.

## 6. What replication will mean

Reported side by side and never merged into one number:

| | original | supplemental | combined |
| --- | --- | --- | --- |
| net, gross, cost | | | |
| IC | | | |

**A positive combined figure with a negative supplemental period is not a
replication** and will not be called one. The supplemental period stands alone.

Then, on the supplemental period: chronological block stability, JPY versus
non-JPY, leave-one-pair-out and leave-one-currency-out, top-day concentration
(1, 3, 5, 10 days, and the net after removing them), and the updated power
arithmetic against Round 2's family-max rule — asking whether the uncertainty
actually **shrank**, not whether a `p` crossed a line.

Top-day exclusion is a diagnostic. It does not become part of the rule.

## 7. Not done this round

No ML. No re-search of trend, breakout, RSI or session. No new features, no new
thresholds, no broad parameter search, no post-hoc variants — and if one is
tried at all it is labelled `POST_HOC_EXPLORATORY` and kept out of the
conclusion. No historical OOS read, no forward epoch, no Formal Confirmation, no
broker, no production claim, no new gate, no surface inventory.

## 8. The classification

Exactly one of `MULTI_DAY_REVERSAL_REPLICATED_IN_SUPPLEMENTAL_EXPLORATORY_HISTORY`,
`MULTI_DAY_REVERSAL_REMAINS_UNRESOLVED_AFTER_SUPPLEMENTAL_HISTORY`, or
`MULTI_DAY_REVERSAL_FAILED_SUPPLEMENTAL_HISTORY_REPLICATION`.

**A is not the target.**
