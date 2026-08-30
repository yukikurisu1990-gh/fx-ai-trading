# M15 Track A R1 — historical read authorization

**Status:** `TRACK_A_R1_HISTORICAL_DEVELOPMENT_READ_GRANT_BLOCKED_SLICE_BOUNDARY_UNRECORDED`

**Always-binding:** `NO_REAL_DATA_READ_PERFORMED` · `NO_EXECUTION_PERFORMED` ·
`PRODUCTION_READINESS_NOT_CLAIMED` ·
`FORWARD_EPOCH_ADOPTION_BLOCKED_INSUFFICIENT_SAMPLE_ADOPTION_WAITS`

**Risk tier:** Amber. This document records an authorization analysis and a
blocker. It grants nothing.

---

## 1. What this document is

The Minimum Research Execution Gate is merged (`37edbb0`). The remaining
precondition of a Track A R1 read is an explicit human + ChatGPT `ReadGrant`
naming the operation, span, pairs, timeframe and approved head SHA.

This document derives that scope **from the committed authorities only**. It
invents no date.

**Its finding is that the grant cannot be issued today**, and the reason is a
single missing prior decision that the contract itself requires to be taken
before R1. Everything else in the scope is determined, and is recorded here so
that the grant can be issued in one step once that decision exists.

## 2. The `ReadGrant` schema, from source

`scripts/m15_track_a/authorization.py` — seven required fields, each validated
at construction and **re-validated** at check time:

| Field | Type | Constraint |
| --- | --- | --- |
| `operation` | `str` | one of a closed set of three (below) |
| `span_start_utc` | `str` | zero-padded ISO `YYYY-MM-DD`, real date |
| `span_end_utc` | `str` | same, and not before the start |
| `pairs` | `tuple[str, ...]` | non-empty, exact `str`, no duplicates |
| `timeframe` | `str` | non-empty, exact `str` |
| `approved_head_sha` | `str` | full 40-character lowercase hex |
| `approver_record` | `str` | ≥ 8 characters, locating the recorded approval |

No other field exists, and none is optional. Coverage is **containment, not
overlap**: a request one day beyond the span, or naming one pair the grant
omits, is refused.

The three operations, and they are three for a reason:

| Operation | Meaning |
| --- | --- |
| `track_a_historical_read` | reading historical bars |
| `track_a_m15_research_derivation` | M1 → M15 aggregation |
| `track_a_exploratory_oos_slice_read` | reading the `EXPLORATORY_OOS_SLICE` |

A grant for one does **not** cover another. That separation is what makes the
next section enforceable rather than merely stated.

## 3. What is determined

| Element | Value | Authority |
| --- | --- | --- |
| **operation** | `track_a_historical_read` | The operation R1 performs on this route is a read of the **M1 source**. Turning those bars into M15 is a different closed operation with its own grant (`track_a_m15_research_derivation`) — not because R1 has no derivation in it, but because the two are separately authorised |
| **pairs** | the frozen **`PAIRS_20`** universe, all twenty | `scripts/m15_gate3a/pair_authority.py`; `aggregation.py` "fails closed outside the frozen PAIRS_20 universe" |
| **timeframe** | **`M1`** | R1 reads the source bars. The committed 365d_BA epoch is M1 bid/ask; M15 does not exist until the derivation runs. `read_route.SOURCE_DESCRIPTION` names "the committed 365d_BA M1 bid/ask files" |
| **approved head SHA** | ⛔ **NOT DETERMINED** | see §4a |
| **span start** | **2025-04-25** | `no_overlap.DESIGN_START`; prereg §3.1 "Design (exploratory) 2025-04-25 → 2026-02-28" |
| **excluded — dead window** | 2026-03-01 → 2026-04-24 | `no_overlap.DEAD_START`/`DEAD_END`; the consumed M1 holdout, quarantined at every timeframe for every role |
| **excluded — forward epoch** | 2026-04-25 onward | `no_overlap.FORWARD_FLOOR`. It is the **Track B confirmation dataset** and does not exist yet (`FORWARD_EPOCH_ADOPTION_BLOCKED_INSUFFICIENT_SAMPLE_ADOPTION_WAITS`) |
| **span end** | ⛔ **NOT DETERMINED** | see §4 |

## 4a. Why the approved head is not determined either

An earlier drafting of the table above named **`37edbb0`**, the merged master,
and that was wrong in a way worth recording rather than quietly fixing.

`require_authorization` compares `approved_head_sha` to `identity.code_sha`, so
the grant names **the code that will run the read**. At `37edbb0`
`read_historical` raises `NotImplementedError` and reads nothing: a grant naming
it authorises a read that cannot happen. The head that *can* perform the read is
the one carrying the body — this PR's — and it is **not merged and not
approved**. Naming an unmerged head in a grant would be worse still: the grant
would point at code that can still change.

So the head is determined by a rule, not yet by a value:

`APPROVED_HEAD_IS_THE_MERGED_HEAD_CARRYING_THE_READ_BODY_WHICH_DOES_NOT_EXIST_YET`

The value is filled in at the same moment as the span end, by the same human +
ChatGPT decision, and not before.

## 4. Why the span end cannot be derived — the blocker

**`THE_EXPLORATORY_OOS_SLICE_BOUNDARY_IS_UNRECORDED_AND_R_2_REQUIRES_IT_BEFORE_R1`.**

**First, R-2's standing, because it decides how this block should be read.**
R-2 lives in the contract packet's §4, and C-9 holds that the packet's §8.11 /
§8.12 / §8.13 rulings cannot be cited as authority while no approved head SHA
carries them. R-2 is in the same position: it is **this programme's own stated
restriction, not a ruling anyone has approved**.

That does not weaken the block — it is why the block is correct. The repository
rule is that *the stricter reading of a research restriction wins*. A recorded
restriction that has not been ratified is still the stricter reading, and the
looser reading ("no approved authority quarantines the slice, so read the whole
design span") is exactly the reading that rule exists to refuse. If a future
ruling **retires** R-2, the span end becomes derivable in one line; until then
it is not.

§4's **R-2** defines the slice and quarantines it, in its own words:

> **Chronological only** — the **final contiguous portion of the design span**,
> the M1 precedent's shape. No random split, no shuffled k-fold …
>
> **Quarantined from R1 onward.** The boundary is **chosen and recorded before
> stage R1**, and **no stage before R4 may read, describe, plot or compute a
> statistic over it — descriptive statistics included**.
>
> **Purge counted in bars, never wall-clock.** ≥ 25 M15 bars (`horizon + 1`) of
> the design span immediately preceding the slice are dropped from training.

Three consequences, and together they close the question:

1. **The slice is inside the design span.** So a grant reading
   `2025-04-25 → 2026-02-28` under `track_a_historical_read` would authorise
   reading the slice — which R-2 forbids before R4, and which
   `track_a_exploratory_oos_slice_read` exists precisely to keep separate.
2. **The development corpus therefore ends before the slice**, minus the
   ≥ 25-bar purge: `development_end = slice_start − purge`.
3. **`slice_start` is named by no committed source.** Searched: the contract
   packet, the pre-registration, the gate-4 design audit, the playbook and the
   policy. R-2 states the *shape* ("final contiguous portion") and the *timing
   of the decision* ("before stage R1"), and nothing states its size, fraction
   or date.

**Two near-misses, checked and rejected as the boundary:**

- **The 25% training prefix** (§8.8) fixes `n_initial_training_dates = 78`,
  a training-only block `2025-04-25 … 2025-07-11`, first predicted DESIGN date
  `2025-07-12`, over `N_design_dates = 310`. That is the **`c`-map estimator's**
  prefix — an *initial* block for `rho_x`/`c` — **not** the `EXPLORATORY_OOS_SLICE`,
  which is a *final* block for evaluation. Different surface, different end of
  the span, different purpose. Citing it as the slice boundary would be
  inventing an authority.
- **T_v / T_h** (prereg §3.1) are the **forward epoch's** validation/holdout
  boundaries, `[FIXED-AT gate 3a]`, and are not the design span's internal split.

**And no non-empty prefix of the design span is provably outside the slice.**
The slice is the *final* contiguous portion, so a prefix is clear of it only if
it ends before the slice begins — and **no committed source bounds how large the
slice may be**, so no prefix can be shown to end before it.

Stated precisely, because the earlier drafting of this paragraph overstated it:
this is an argument from a *missing upper bound*, not a claim that the slice
plausibly consumes the whole design span. A slice that left no training data
would be degenerate, and R-2's purge — "≥ 25 M15 bars of the design span
immediately preceding the slice are dropped **from training**" — presupposes
training data before it. So a sane boundary certainly leaves a large prefix. The
point is that "certainly" is not "derivably": picking the prefix would mean
picking the number, and picking the number is the decision §5 refers upward.

**Fail closed.** No development span is granted.

## 5. What the next decision is, exactly

One human + ChatGPT decision, and it is one R-2 already requires **before R1**:

> **Choose and record the `EXPLORATORY_OOS_SLICE` boundary** — the start date of
> the final contiguous portion of the design span reserved for the single R4
> evaluation.

It must be **outcome-blind**, taken before any DESIGN observation, and — on the
model of the 25% prefix ruling — stated as a **declared, mechanical, pre-data
boundary** whose job is to remove researcher discretion, with no optimality
claimed for it. Once it exists, the development grant follows mechanically:

```
span_start_utc = 2025-04-25                       (DESIGN_START)
span_end_utc   = slice_start − ≥25 M15 bars       (R-2 purge)
```

and the ≥ 25-bar purge is counted **in bars, never wall-clock** (R-2), so the
arithmetic needs the eligible-bar index, not a calendar subtraction.

Note also §8.11.12 **F-5**: a trailing purge of ≥ 25 M15 bars applies at
`DESIGN_END` itself, because a Friday-afternoon signal bar's 24-bar label reaches
into the dead window. That purge binds the *labels*, not this read's span, and it
is recorded here so the two are not confused.

## 6. The seen-data consequence — irreversible, and stated before any read

Whatever span is eventually granted becomes **`EXPLORATORY_SEEN_DATA`** the
moment it is read, and it does not return.

- **Marking reaches every timeframe.** M1 rows and the M15 bars derived from
  them are the same information at a different resolution, so a declaration
  deliberately ignores the timeframe field.
- **Marking reaches every pair** named in the declaration.
- **Warm-up counts.** A bar read only to initialise an indicator is seen. The
  request's warm-up-widened start is what the ledger checks, not the label span.
- **A discarded run still spends it.** There is no un-declare, and the ledger
  is append-only and write-ahead: the interval is recorded *before* it is
  touched, so a run that dies mid-read still leaves the span marked.
- **It does not become Track B confirmation data.** Existing historical data is
  the Track A **development** dataset; the unseen forward epoch is the Track B
  **confirmation** dataset. `SEEN_IS_TERMINAL_AND_NO_RULING_CAN_RESTORE_UNSEEN_STATUS`
  — the roles do not swap back, and no ruling restores unseen status.

## 7. What a grant, when issued, will not cover

Recorded now so the eventual grant is read narrowly:

- **not** the `EXPLORATORY_OOS_SLICE` — a separate operation, a separate
  authorization, and Q7's `N = 1`, consumed at its first decision-bearing
  observation;
- **not** the M1 → M15 derivation — `track_a_m15_research_derivation` is its own
  grant, and playbook §2.5 forbids chaining irreversible stages;
- **not** the forward epoch, in any role;
- **not** the dead window 2026-03-01 → 2026-04-24;
- **not** Formal Confirmation, and no Track A output may be cited for one;
- **not** training, evaluation, calibration or any fitted object — R1 reads;
  R3 and R4 are separate Red gates with separate approvals;
- **not** broker, live, demo, order submission, network, external DB or
  production deployment.

## 8. Non-authorisation statement

This document authorises **nothing**. No `ReadGrant` is issued by it, no read is
performed, and the read route's body refuses without a grant regardless of what
is written here. `NO_REAL_DATA_READ_PERFORMED`; `NO_EXECUTION_PERFORMED`;
`PRODUCTION_READINESS_NOT_CLAIMED`.
