# T-3 — which stage owns it

**Status:** `T_3_IS_A_LATER_STAGE_DUTY_UNDER_THE_DECLARED_CANDIDATES_FROZEN_COST_TABLE`
· `T_3_NUMERATOR_NOT_RULED_HERE_BECAUSE_R1_IS_NOT_THE_STAGE_THAT_NEEDS_IT`

**Approval identifier: PR #455.** Recorded 2026-08-31 as an explicit human +
ChatGPT ruling. Before that PR merges this record is not citable authority; the
merge is what confers it.

**Always-binding:** `NO_REAL_DATA_READ_PERFORMED` · `NO_EXECUTION_PERFORMED` ·
`PRODUCTION_READINESS_NOT_CLAIMED`

---

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

## 2. Step 1 — the stage. **Not R1.**

§7's stage table lists "the distribution of `barrier_distance / cost` on eligible
bars and its median (T-3)" under R1, and §2 says it "belongs in R1, not after a
model exists". **§8.13.10's D-3 corrects that classification by name**, and D-4
then fixes where the duty does sit.

**D-3(1), verbatim:**

> **prereg §6 was quoted with "before implementation" removed.** Its text is:
> "**before implementation**, the actual distribution of `barrier_distance /
> cost` on design data must be derived and recorded". Since §8.11.12 A-3 records
> that Track A is where the features, calibration, EV gate and cost table "**get
> written for the first time**", Track A *is* implementation, and classifying the
> measurement as a Track A surface **inverts** prereg §6's timing. prereg §6 is
> added to propagation as **P-15**, and until it is amended
> `WHERE_THIS_PACKET_AND_A_GOVERNANCE_DOCUMENT_DISAGREE_THE_GOVERNANCE_DOCUMENT_GOVERNS_UNTIL_PROPAGATED`
> means **prereg §6 governs**.

**D-4, verbatim:**

> **The measurement is therefore a duty, not a permission**: the ratio is
> computed on the design span under the **declared candidate's frozen cost
> table**, before candidate pre-registration completes, and the value is
> committed. Whether that value may **discharge** playbook §6's checkbox stays
> with P-14.
> **`THE_T_3_RATIO_MEASUREMENT_IS_A_DUTY_UNDER_THE_DECLARED_CANDIDATES_COST_TABLE_NOT_A_PERMISSION`.**

The playbook agrees: its §6 item is satisfied "from the §4 derivation artifact
under the declared candidate's frozen cost table".

**So T-3 is option B: a later-stage duty.** R1 has no frozen cost table — it is
the stage that *measures the spreads the cost table will be built from* — so a
T-3 value computed in R1 would be computed under a cost table that does not yet
exist, which is exactly the timing inversion D-3 names.

**This is decided on intent, and the intent is served by it.** T-3 asks whether
M15 "demonstrably escapes the M1 cost regime" for the thing that will actually
be traded — a declared candidate under a frozen cost table. A number computed
before either exists answers a different question, and would either fire a block
on a figure the candidate does not use or fail to fire one it should.

## 3. Step 2 — the numerator. **Not ruled, and R1 does not need it.**

Under option B the numerator ruling belongs with the stage that owns the
measurement. It is **not taken here**, and the reasons are worth recording so it
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

`T_3_NUMERATOR_REFERRED_TO_THE_STAGE_THAT_OWNS_THE_MEASUREMENT`.

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

- it does **not** weaken T-3. The block still fires, at the stage that owns it,
  under the cost table the contract names;
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
