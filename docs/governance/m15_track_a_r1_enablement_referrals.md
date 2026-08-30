# R1 enablement — what this work could not decide

**Status:** `R1_ENABLEMENT_REFERRALS_OPEN_NOT_RULED`

**Approval identifier: PR #455.** This document **rules nothing**. It records
questions the enablement work ran into, each of which needs a human + ChatGPT
decision, and it exists because an earlier revision of that work answered two of
them on its own authority and had to be reverted.

**Always-binding:** `NO_REAL_DATA_READ_PERFORMED` · `NO_EXECUTION_PERFORMED` ·
`PRODUCTION_READINESS_NOT_CLAIMED`

---

## 1. Why this document exists

Three independent review roles returned **BLOCKED** on the first revision of
PR #455. Two of their findings were the same shape, and it is a shape worth
naming: **a session had resolved a conflict between two committed rules by
picking one, and recorded the resolution as though it were settled.**

- the reader-freedom pin's `calendar_authority` prohibition was deleted, citing
  `docs/governance/m15_track_a_r1_enablement_ruling.md` §3 — **a file that did
  not exist**;
- `calendar_build` authored a market-hours boundary and called it "the committed
  FX week", when no committed source states one and ω-12 forbids Track A from
  authoring market hours at all.

Both are reverted. What is left is the questions, written down as questions.

## 2. `MARKET_HOURS_BOUNDARY_FOR_CALENDAR_A_REFERRED_TO_HUMAN_AND_CHATGPT`

**The conflict.** Stage R1 must measure missingness and coverage (§7). PR #444's
D-6 makes a committed calendar artifact the coverage authority and forbids
inferring expected slots from data. But `m15_track_a_execution_gate.md` §8,
merged at `37edbb0`, says the opposite about Track A specifically:

> requiring it of Track A would **block exploration on an artefact that does not
> exist, for no leakage reason**. The calendar reading is a **declared label**
> from a closed set — **Track A may not author market hours (ω-12)**

and `identity.py` has said the same in this package's own words throughout: "no
approved calendar artifact exists and Track A may not invent one".

**What the first revision did, and why it was wrong.** It authored one:
Sunday 22:00 UTC open, Friday 22:00 UTC close, labelled "committed". No
committed source says that. Worse, a review role measured that it is **factually
wrong** — OANDA's week opens at New York 17:00, which is `21:00Z` under EDT, and
roughly 27 of the development corpus's 35 weeks are EDT. This repository's own
`scripts/stage22_0a_scalp_label_design.py:247` counts `hour_utc == 21` as
week-open on the same data. Under a real read, a Calendar A built from those
constants **aborts the first Sunday**:

```
AggregationError: … 60 source minute(s) lie outside the expected-slot
authority, earliest 2025-05-04T21:00:00+00:00
```

The synthetic dry run could not catch it, because the fixture imported the same
`in_fx_week` the calendar used. A calendar and its test agreeing with each other
is not evidence about the market.

**The question, and it is genuinely open:**

> Does Track A's R1 measure coverage against an **approved calendar artifact**
> (which requires someone to approve a market-hours boundary, which ω-12 says
> Track A may not author), or against the **declared label** §8 provides for
> (in which case R1 reports an *observed-structure diagnostic* and says plainly
> that the D-6 coverage authority does not exist)?

**What the code does until it is answered.** `calendar_build` still contains the
arithmetic, and its output is labelled
`CALENDAR_A_PROPOSED_NOT_APPROVED_MARKET_HOURS_REFERRED_TO_HUMAN_AND_CHATGPT`.
The committed artifacts carry that status in a field a reader cannot miss.
`validate_calendar`'s `approval` marker is stamped because the validator's
vocabulary requires it, and that module's own docstring is the answer to what it
means: it "neither performs nor evidences the approval".

**`PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED` is not discharged by
this work**, and nothing here claims it is.

## 3. `TRACK_A_COST_SCHEMA_IMPORT_NARROWING_PROPOSED_NOT_RULED`

`scripts.m15_gate3a.cost_schema` was removed from `TRACK_A_FORBIDDEN_MODULES`
and replaced by a three-symbol entry: `EXECUTION_PADDING_PIP`,
`FLAT_SLIPPAGE_CELL_PIP`, `SESSIONS_UTC` — Ruling 5's two frozen cost pads and
Ruling 4's frozen session partition. `validate_cost_table` and the rest of the
module stay unreachable.

**Why it looks defensible.** R1 must report a per-pair × session spread
distribution and the cost that follows from it. The alternative is restating
`0.3`, `0.5` and the three session windows inside Track A, which creates a
second authority for numbers the contract froze — the "pip authority 100×"
defect in a new place.

**Why it is a referral and not a ruling.** Deleting an entry from a committed
prohibition is a change to a frozen contract, and CLAUDE.md's stop list names
that explicitly. A session may propose it; a session may not take it.

`calendar_authority`'s prohibition is **restored** and needs no ruling: the
validation moved to `calendar_build.validated_calendar_a`, on the gate-3a side
of the boundary, so Track A receives a record it cannot mint and never imports
the module.

## 4. `RULING_4_HOLIDAY_THIN_LIQUIDITY_LIST_IS_EMPTY_BECAUSE_NO_DESIGN_AUDIT_HAS_FIXED_ONE`

Ruling 4 makes the holiday / abnormal-thin-liquidity exclusion calendar
`[FIXED-AT design audit]`, before implementation. No design audit has fixed one.
Calendar B therefore carries an **empty** list.

The consequence, stated in the artifact and repeated here so it is not only in a
JSON field: no date is excluded for illiquidity, so the **eligible-bar rate is
overstated**, and thin sessions stay in the population the barrier/cost ratio is
computed over — which pushes the median **down**, and is therefore conservative
for T-3 and anti-conservative for the rate. Someone has to fix the list.

## 5. `T_3_NUMERATOR_SELECTION_IS_CHALLENGED_AND_THE_CHALLENGE_IS_RECORDED`

`docs/governance/m15_track_a_t3_stage_ruling.md` selects the **pre-floor**
numerator. A review role argued the selection is wrong in a specific, checkable
way, and the objection is recorded rather than absorbed:

- of the three readings, `post_floor_tp` is unfirable (ratio `≥ 3.0`
  identically), `pre_floor_tp` fires below `ATR/cost = 2.0`, and
  `post_floor_sl` fires below `ATR/cost = 3.0`. So **`post_floor_sl` is the
  strictest firable reading, and the ruling chose the middle one**;
- Ruling 6 names `TP_dist` and `SL_dist` — the **post-floor** quantities — as
  the "spread-floored barriers". `1.5 × ATR14_M15` is not called a barrier
  anywhere in the committed text;
- CLAUDE.md: "the stricter reading of a research restriction wins".

The counter-argument is in the ruling: a numerator defined in terms of cost
cannot test whether the move escapes cost, and the eligibility condition uses
`1.5 × ATR14_M15` directly. **The survey reports all three medians**, so whoever
resolves this can read the numbers rather than the arguments.

## 6. `T_3_CONSEQUENCE_SEPARATION_IS_CHALLENGED`

The same review role read the T-3 stage ruling's separation of *measurement*
from *consequence* as a loosening, citing six committed statements that a Track
A measurement **fires** T-3's block — including prereg §13a, which is IN FORCE.

The ruling's position is that firing the block and *applying* it are different
acts, and that R1 reports a status the later gate consumes. That reading may be
right and it may be a distinction without a difference. **It is not a session's
call**, the objection is concrete, and it is referred.

Until it is resolved, `r1_survey` emits
`T3_MEDIAN_ELIGIBLE_BARRIER_COST_RATIO_{BELOW,AT_OR_ABOVE}_3_0_REPORTED_TO_THE_LATER_GATE`
and reaches no verdict, which is the conservative reading under either.

## 7. Non-authorisation statement

This document authorises nothing and rules nothing. It records five open
questions and one restored prohibition.
`NO_REAL_DATA_READ_PERFORMED`; `NO_EXECUTION_PERFORMED`;
`PRODUCTION_READINESS_NOT_CLAIMED`.
