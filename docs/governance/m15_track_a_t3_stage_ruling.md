# T-3 — which stage owns it

**Status:** `T_3_IS_A_TRACK_A_DUTY_AT_THE_DECLARED_CANDIDATE_UNDER_ITS_FROZEN_COST_TABLE_NOT_AT_R1`
· `A_TRACK_A_MEASUREMENT_FIRES_T_3_S_BLOCK_UNCHANGED`
· `T_3_NUMERATOR_NOT_RULED_HERE_BECAUSE_R1_IS_NOT_THE_STAGE_THAT_TAKES_IT`

**Approval identifier: PR #455.** Recorded 2026-08-31 as an explicit human +
ChatGPT ruling. Before that PR merges this record is not citable authority; the
merge is what confers it.

**Always-binding:** `NO_REAL_DATA_READ_PERFORMED` · `NO_EXECUTION_PERFORMED` ·
`PRODUCTION_READINESS_NOT_CLAIMED`

---

## 0. Correction — the second revision of this document was also wrong

The **first** revision put the measurement in R1 and ruled a numerator; a review
role showed the reconstruction was not honest. The **second** moved the duty out
of Track A entirely and said "Track A neither fires the block". A review role
showed that was worse: it **removed a stop trigger**, and reasoned from a clause
that had already been superseded.

`docs/design/m15_first_cost_hurdle_aware_preregistration_design.md` **§13a is
RULED and IN FORCE**, and it is the amendment D-3 was waiting for. Its §6 row,
verbatim:

> | **§6** barrier/spread ratio "**before implementation** … derived and
> recorded" | The derivation is a **Track A duty**, performed under the declared
> candidate's frozen cost table. Its "before implementation" timing is
> **re-sited into Track A**, before Track B candidate pre-registration
> completes. A Track A measurement **fires** T-3's block; it does **not**
> discharge playbook §6's checkbox (§8.13.6) |

So D-3's "until it is amended … prereg §6 governs" no longer bites: prereg §6
**has** been amended, and the amendment sites the duty **inside Track A** and
**keeps the firing**. The second revision cited D-3's conditional without
checking whether its condition still held — and, having just recorded the first
revision's truncated quotation of playbook §6 as a fault, truncated the same
sentence again, stopping before "a Track A measurement **fires** T-3's block".

Both errors are corrected below.
`A_TRACK_A_MEASUREMENT_FIRES_T_3_S_BLOCK_UNCHANGED`.

## 1. What this ruling replaces

An earlier revision of this document put T-3's **measurement** in R1 and ruled a
numerator. A review role showed the reconstruction was not honest: it quoted
playbook §6 up to the clause before the one that contradicted it, cited §8.12.13
for a passage that is in §8.12.10, and presented a conflict that the committed
text had already resolved the other way. That revision is **withdrawn in full**
and replaced by what the authorities actually say.

The question was also being answered on the wrong basis. The instruction for
this round is explicit — decide **by T-3's intent and its authority, not by
which reading is stricter** — and on that basis the authorities are not in
conflict at all.

## 2. Step 1 — the stage. **A Track A duty, and not at R1.**

Three authorities, read together rather than one at a time.

**prereg §13a (RULED, IN FORCE)** — quoted in §0 — makes the derivation a **Track
A duty** "performed under the declared candidate's frozen cost table", re-sites
the "before implementation" timing **into** Track A, and states that a Track A
measurement **fires** T-3's block.

**D-4**, in the same direction:

> **The measurement is therefore a duty, not a permission**: the ratio is
> computed on the design span under the **declared candidate's frozen cost
> table**, before candidate pre-registration completes, and the value is
> committed. Whether that value may **discharge** playbook §6's checkbox stays
> with P-14.
> **`THE_T_3_RATIO_MEASUREMENT_IS_A_DUTY_UNDER_THE_DECLARED_CANDIDATES_COST_TABLE_NOT_A_PERMISSION`.**

**playbook §6**, quoted through to the end of the sentence this time:

> ratio rule computed **from the §4 derivation artifact under the declared
> candidate's frozen cost table** — **a Track A measurement fires T-3's block**
> but does not discharge this checkbox

All three name the same trigger: **a declared candidate with a frozen cost
table**. That is inside Track A — §8.11.12 A-3 records Track A as where the cost
table "gets written for the first time" — and it is **not R1**.

**Why not R1, decided on intent rather than on strictness.** R1 is the stage
that *measures the spreads a cost table will be built from*. It has no declared
candidate and no frozen cost table, so a T-3 value taken there would be taken
under a cost table that does not exist yet. T-3 asks whether M15 "demonstrably
escapes the M1 cost regime" **for the thing that will actually be traded**; a
number computed before that thing exists answers a different question, and would
either fire the block on a figure no candidate uses or fail to fire one it
should.

**What R1's number is, then.** A descriptive statistic — one of the things §7
also asks R1 for — and *not* the measurement §13a names. It fires nothing,
because it is not that measurement. **The block is untouched: when the Track A
measurement is taken under the declared candidate's frozen cost table, it fires
exactly as §13a, D-4 and playbook §6 say.**

## 3. Step 2 — the numerator. **Not ruled, and R1 does not need it.**

The numerator ruling belongs with the stage that **takes** the measurement —
Track A at the declared candidate, under its frozen cost table. It is **not taken here**, and the reasons are worth recording so it
is not re-litigated from scratch:

| Reading | Numerator | Ratio on eligible bars |
| --- | --- | --- |
| pre-floor TP | `1.5 × ATR14_M15` | `≥ 2.0`; fires below `ATR/cost = 2.0` |
| post-floor TP | `max(1.5 × ATR14_M15, 3.0 × cost)` | **`≥ 3.0` identically — cannot fire** |
| post-floor SL | `max(1.0 × ATR14_M15, 2.0 × cost)` | `≥ 2.0`; fires below `ATR/cost = 3.0` |

Two facts a later ruling should start from, both measured rather than argued:

- **the post-floor TP reading cannot fire.** Its numerator is defined in terms of
  cost, so its ratio to cost is `≥ 3.0` by construction and the `3.0` threshold
  is unreachable. Any ruling that selects it is selecting a test with one
  possible outcome;
- **post-floor SL is the strictest reading that *can* fire**, and Ruling 6 names
  `TP_dist` and `SL_dist` — the post-floor quantities — as "the spread-floored
  barriers", while `1.5 × ATR14_M15` is not called a barrier anywhere in the
  committed text. A review role raised both points and they stand unanswered.

`T_3_NUMERATOR_REFERRED_TO_THE_STAGE_THAT_TAKES_THE_MEASUREMENT`.

## 4. What R1 does instead

R1 reports the `barrier_distance / cost` distribution **as an ordinary
descriptive statistic**, under all three readings, with:

- **no `3.0` threshold**,
- **no T-3 status token**,
- **no verdict**, and
- an explicit `numerator_ruling: UNRULED_ALL_THREE_READINGS_REPORTED`.

A test asserts the survey record contains no `T3_MEDIAN…` token at all, so R1
cannot quietly re-acquire the duty. Reporting the distribution is not the T-3
measurement; it is the descriptive statistic §7 also asks R1 for, and it gives
the later stage its numbers without pre-empting either ruling.

## 5. What this ruling does not do

- it does **not** weaken T-3. **A Track A measurement fires the block**, exactly
  as §13a, D-4 and playbook §6 say — at the declared candidate, under its
  frozen cost table. The second revision of this document said Track A
  "neither fires the block", which removed a stop trigger; that sentence is
  **withdrawn**;
- it does **not** decide P-14 (which derivation discharges playbook §6's
  checkbox) or the numerator;
- it does **not** resolve **S-20a** — which price series `ATR14_M15` uses is an
  `UNREGISTERED_RESEARCH_CHOICE`. R1 uses **bid** and says so in its output
  (`ATR_PRICE_SERIES_IS_AN_UNREGISTERED_RESEARCH_CHOICE_S_20A`). Naming an
  unregistered choice is not registering it;
- it does **not** touch
  `C_MAP_PREDICTED_DATE_COUNT_VS_OOS_SLICE_QUARANTINE_UNRESOLVED_REFERRED`.

## 6. Non-authorisation statement

This document rules on stage ownership. It authorises no read, no derivation, no
training, no evaluation and no execution. `NO_REAL_DATA_READ_PERFORMED`;
`NO_EXECUTION_PERFORMED`; `PRODUCTION_READINESS_NOT_CLAIMED`.
