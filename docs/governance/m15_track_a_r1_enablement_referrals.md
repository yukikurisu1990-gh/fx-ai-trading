# R1 enablement — the five referrals, closed

**Status:** `R1_ENABLEMENT_REFERRALS_CLOSED_BY_AUTHORITY`

**Approval identifier: PR #455.** Recorded 2026-08-31 as an explicit human +
ChatGPT decision round. Before that PR merges this record is not citable
authority; the merge is what confers it.

**Always-binding:** `NO_REAL_DATA_READ_PERFORMED` · `NO_EXECUTION_PERFORMED` ·
`PRODUCTION_READINESS_NOT_CLAIMED`

---

## 0. How these were decided

Four of the five turned out **not to be open questions at all** — the committed
authorities answer them, and the earlier revision of this work had answered them
differently because it had not read far enough. That is the finding worth
recording: three review roles blocked a PR whose defects were, in the main,
**already ruled against in text that was merged months earlier**.

The instruction for this round was to decide by **authority and intent, not by
which reading is stricter**. On that basis every one of these is settled by
quotation.

## 1. Calendar A — **Route B.** No calendar is authored.

**Decision: `CALENDAR_A_NOT_AUTHORED_R1_USES_THE_DECLARED_LABEL_ROUTE`.**

Two merged authorities settle it, and they agree.

**PR #444's D-6**, which created the calendar contract in the first place:

> **This document deliberately invents no broker market-hours times.** No
> open/close instants, no DST transition dates, no holiday list appear here **or
> may be added by an implementer**.

An implementer may not add them. That is not a preference about strictness; it
is a prohibition on the act, and the earlier revision performed exactly that act.

**Execution gate §8**, merged at `37edbb0`:

> The `ValidatedCalendar` artefact contract is unchanged for Track B; requiring
> it of Track A would **block exploration on an artefact that does not exist,
> for no leakage reason**. The calendar reading is a **declared label** from a
> closed set — **Track A may not author market hours (ω-12)**

So Track A does not need a `ValidatedCalendar`, and may not write one. The
premise the earlier revision used to narrow the reader-freedom pin — that D-6
*forces* Track A to reach the validator — is refuted by the sentence above.

**What R1 does instead.** `derive_m15` passes `expected_minutes=None`, the
aggregator's calendar-derived accounting comes back `None`, and R1 reports
observed structure as
`COVERAGE_AUTHORITY_ABSENT_R1_REPORTS_A_DECLARED_LABEL_DIAGNOSTIC`. The absent
fields are reported **as absent** rather than filled in, and a test asserts that.

**What was deleted.** `scripts/m15_gate3a/calendar_build.py` and both
`artifacts/m15_calendar/*.json`. `scripts/m15_gate3a/session_windows.py`
replaces it and carries only content that **is** committed — Ruling 4's frozen
session partition and its frozen rollover window, both fixed UTC clock windows.

**Not discharged:** `PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED`. It
is a real approval item and it stays open. R1 does not need it, because R1 does
not claim the coverage authority.

**Recorded for whoever eventually approves one.** The invented boundary was not
only unauthorised, it was **wrong**: OANDA's week opens at New York 17:00, which
is `21:00Z` under EDT, and roughly 27 of the development corpus's weeks are EDT.
A review role measured a real read aborting on the first Sunday. Whoever writes
the real calendar has to handle DST, and this repository's own
`scripts/stage22_0a_scalp_label_design.py:247` counts `hour_utc == 21` as
week-open on the same data.

## 2. Calendar B / the holiday list — **not adopted; sent to the later stage.**

**Decision: `RULING_4_HOLIDAY_LIST_IS_NOT_R1S_TO_SUPPLY_AND_NONE_IS_APPLIED`.**

Ruling 4 makes the holiday / thin-liquidity exclusion calendar `[FIXED-AT design
audit]`, before implementation. No design audit has fixed one, and D-6's
sentence above forbids an implementer adding one. So there is no Calendar B
object, no holiday list, and no illiquidity exclusion in R1.

**The rollover window is different and is kept.** `21:55–22:15 UTC` is stated
numerically in Ruling 4, is a fixed UTC clock window, requires no market-hours
inference and no DST logic. It is applied on **bucket overlap**, not bucket
start — a start test excludes only the 22:00 bucket and leaves 21:45 covering
21:55–21:59, which *narrows* a minimum Ruling 4 says may only widen.

**Source authority:** prereg §5, Ruling 4 FROZEN.
**Role:** event eligibility only, never slot membership.
**Where used:** `session_windows.is_event_eligible_window`, called by
`r1_survey` for the spread population and the eligible-bar rate.
**Outcome-independent:** it is a function of the UTC clock alone; no price, no
observation and no metric reaches it.

**The consequence of the empty holiday list, stated rather than implied:** no
date is excluded for illiquidity, so the **eligible-bar rate is overstated** and
thin sessions remain in the barrier/cost population, which pushes that ratio's
median **down**. Carried in the survey output as `HOLIDAY_STATUS` and
`HOLIDAY_CONSEQUENCE`.

## 3. T-3 — **option B.** A later-stage duty.

**Decision:
`T_3_IS_A_LATER_STAGE_DUTY_UNDER_THE_DECLARED_CANDIDATES_FROZEN_COST_TABLE`**,
ruled in full in `docs/governance/m15_track_a_t3_stage_ruling.md`.

D-3 records that classifying the measurement as a Track A surface **inverts**
prereg §6's "before implementation" timing, because Track A *is* implementation;
D-4 fixes the duty under the declared candidate's frozen cost table. R1 has no
frozen cost table — it is the stage that measures the spreads one will be built
from — so a T-3 value computed there answers a different question.

**The numerator is therefore not ruled**, and does not need to be for R1 to run:
`T_3_NUMERATOR_REFERRED_TO_THE_STAGE_THAT_OWNS_THE_MEASUREMENT`. R1 reports all
three readings as descriptive statistics with no threshold and no verdict, and a
test asserts the survey record contains no T-3 token.

This closes both challenges the review roles raised — the numerator choice and
the measurement/consequence separation — by removing the stage that made either
question R1's.

## 4. `cost_schema` import narrowing — **permitted. Implementation-only.**

**Decision: `TRACK_A_COST_SCHEMA_IMPORT_NARROWING_IS_IMPLEMENTATION_ONLY_PERMITTED`.**

The question asked was whether narrowing the *import surface* narrows or changes
decision-bearing cost semantics or authority. It does not:

| | before | after |
| --- | --- | --- |
| what Track A may import | nothing | `EXECUTION_PADDING_PIP`, `FLAT_SLIPPAGE_CELL_PIP`, `SESSIONS_UTC` |
| what the constants mean | Ruling 5 / Ruling 4 FROZEN | unchanged |
| who may change them | a human + ChatGPT ruling | unchanged |
| `validate_cost_table` | unreachable | unreachable |
| any cost **decision** Track A can now take | none | none |

The three symbols are frozen constants. The alternative — restating `0.3`, `0.5`
and the three session windows inside Track A — creates a *second* authority for
numbers the contract froze, which is the "pip authority 100×" defect in a new
place. Narrowing the import surface is the conservative option, not the
permissive one.

**`calendar_authority`'s prohibition is restored** and needed no ruling: nothing
in Track A imports it any more, because Calendar A is gone.

## 5. What is still open

- **`PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED`** — §1. Not R1's.
- **`T_3_NUMERATOR_REFERRED_TO_THE_STAGE_THAT_OWNS_THE_MEASUREMENT`** — §3.
- **`RULING_4_HOLIDAY_LIST_IS_NOT_R1S_TO_SUPPLY_AND_NONE_IS_APPLIED`** — §2, for
  the design audit that will fix the list.
- **P-14** — which derivation discharges playbook §6's checkbox. Untouched.
- **`C_MAP_PREDICTED_DATE_COUNT_VS_OOS_SLICE_QUARANTINE_UNRESOLVED_REFERRED`** —
  out of R1 scope, untouched, and R1's implementation does not reach the c-map.

## 6. Non-authorisation statement

This document closes four referrals by quotation and records what remains open.
It authorises no read, no derivation, no training, no evaluation and no
execution. `NO_REAL_DATA_READ_PERFORMED`; `NO_EXECUTION_PERFORMED`;
`PRODUCTION_READINESS_NOT_CLAIMED`.
