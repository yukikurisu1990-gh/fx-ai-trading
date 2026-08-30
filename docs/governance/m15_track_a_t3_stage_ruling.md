# T-3 — which stage owns it, and what its numerator is

**Status:** `T_3_IS_A_TRACK_A_R1_MEASUREMENT_OBLIGATION_ITS_CONSEQUENCE_BINDS_LATER_GATES`
· `T_3_NUMERATOR_RULED_PRE_FLOOR_ATR_BARRIER`

**Approval identifier: PR #455.** Recorded 2026-08-31 as an explicit human +
ChatGPT ruling. Before that PR merges this record is not citable authority; the
merge is what confers it.

**Always-binding:** `NO_REAL_DATA_READ_PERFORMED` · `NO_EXECUTION_PERFORMED` ·
`PRODUCTION_READINESS_NOT_CLAIMED`

---

## 1. Why a ruling was needed at all

The first Track A R1 execution command had to be refused, and one of the reasons
was that **T-3 could not be computed as specified**. Two questions were open and
neither had a committed answer.

**Which stage owns the measurement.** §7's stage table puts it in R1 —
"the distribution of `barrier_distance / cost` on eligible bars and its median
(T-3)" — and §5.1 agrees: it "is measured **on design data**, needs **no model**,
and is the direct test of the stated reason for preferring M15 to M1 — so it
belongs in R1, not after a model exists". But **D-3** observes that prereg §6
says *before implementation*, adds prereg §6 to the propagation list as **P-15**,
and holds that "until it is amended … prereg §6 governs"; and **D-4** places the
measurement under "the **declared candidate's frozen cost table**", before
candidate pre-registration completes. The playbook agrees with D-4: "from the §4
derivation artifact under the declared candidate's frozen cost table".

**What the numerator is.** No committed source says. The design audit states
both readings in one sentence — eligible TP distances are "**≥ 2×cost
pre-floor** and **≥ 3×cost post-floor**" — and never says which one T-3 divides.

## 2. Step 1 — the stage. **R1 measures. A later gate decides.**

The two authorities are not actually in conflict once the *measurement* and the
*consequence* are separated, and separating them is what §8.12.13's own
classification already does:

> T-3's **measurement** is a Track A strategy surface, its **consequence** binds
> gates 5→7, and a Track A measurement **fires** T-3's block while **not**
> discharging playbook §6's checkbox.

So:

* **R1 measures and reports** the `barrier_distance / cost` distribution on
  eligible bars, and its median, over the authorised development corpus. It
  reaches no verdict, blocks nothing, and discharges nothing. Its output is
  `NON_DECISION_BEARING_EXPLORATORY_ONLY`, like every Track A output.
* **The consequence — gate-7 execution authorisation BLOCKED pending a new human
  + ChatGPT ruling — is not R1's to apply.** It binds gates 5→7, under the
  declared candidate's frozen cost table, from the §4 derivation artifact. D-4
  and the playbook describe *that* measurement, and this ruling does not move it.
* **The two are different measurements of the same quantity**, taken at
  different times under different cost tables, and the later one is the one with
  consequences. A Track A number is not a substitute for it and may never be
  cited as one.

**What R1's number is for**, then: it is the early warning the §7 table wants —
"M15 must demonstrably escape the M1 cost regime" is worth knowing *before* the
programme spends R2–R4 on it. §7's own R5 rule uses it that way, as an
**exploratory stop**, and calls it "T-3's own number, adopted here as an
exploratory stop".

**Why this does not permanently block R1.** The brief is explicit — "T-3未解決を
理由にR1全体を永久blockしない。stage ownershipを先に決める" — and the ownership
question is now decided. R1 runs, measures and reports.

## 3. Step 2 — the numerator. **Pre-floor: `1.5 × ATR14_M15`.**

Ruling 6 FROZEN gives three candidate numerators:

| Reading | Numerator | Ratio on eligible bars |
| --- | --- | --- |
| **pre-floor TP** | `1.5 × ATR14_M15` | `≥ 2.0`, and free to be below 3.0 |
| post-floor TP | `max(1.5 × ATR14_M15, 3.0 × cost)` | **`≥ 3.0` identically** |
| post-floor SL | `max(1.0 × ATR14_M15, 2.0 × cost)` | `≥ 2.0` |

**The post-floor TP reading is refused because it makes T-3 unfirable.** Its
numerator is defined *in terms of cost*, so its ratio to cost cannot fall below
`3.0` — the threshold T-3 tests against. A test whose result is fixed by its own
definition is not the test the contract describes as "M15 must demonstrably
escape the M1 cost regime, **not just claim to**". Circularity is the objection,
not inconvenience.

**The pre-floor TP reading is selected**, for three reasons that are all in the
committed text:

1. it is the quantity the **eligibility condition itself** uses —
   `1.5 × ATR14_M15 ≥ 2.0 × cost` — so "eligible bars" and "the ratio on eligible
   bars" are about the same number, and eligibility sets a floor of `2.0` that
   T-3's `3.0` then tests against. The two rulings compose;
2. it is the **attainable move**, which is the thing that either escapes the cost
   regime or does not. A floor does not escape cost; it is made of cost;
3. the design audit's own phrasing — "≥ 2×cost **pre-floor**" — is the reading
   under which its sentence carries information.

**The post-floor SL reading is not selected**, but it is not absurd, so R1
reports it too.

**All three are reported.** `r1_survey` computes the ruled numerator *and* both
alternatives, and puts all three medians in the survey record. A ruling that can
be re-read against the numbers is one a later gate can revisit cheaply; one that
discards the alternatives is not.

## 4. What this ruling does not do

- it does **not** move D-4's or the playbook's later measurement, or weaken it;
- it does **not** let a Track A number discharge playbook §6's checkbox, fire
  the gate-5→7 block, or appear in a formal decision;
- it does **not** freeze the numerator for that later measurement. If the
  candidate's frozen cost table makes a different reading correct there, this
  ruling is silent on it — the three medians are reported precisely so the
  question can be reopened on evidence;
- it does **not** resolve **S-20a**, which records that *which price series*
  `ATR14_M15` is computed on is an `UNREGISTERED_RESEARCH_CHOICE`. R1 uses the
  **bid** series and says so in its output
  (`ATR_PRICE_SERIES_IS_AN_UNREGISTERED_RESEARCH_CHOICE_S_20A`). Naming an
  unregistered choice is not registering it.

## 5. Non-authorisation statement

This document rules on stage ownership and a numerator. It authorises no read,
no derivation, no training, no evaluation and no execution.
`NO_REAL_DATA_READ_PERFORMED`; `NO_EXECUTION_PERFORMED`;
`PRODUCTION_READINESS_NOT_CLAIMED`.
