# M15 Track A R1 — historical read authorization

**Status:** `TRACK_A_R1_READ_SCOPE_AND_AUTHORIZATION_SEQUENCE_RULED`

**Rulings recorded here** (human + ChatGPT, 2026-08-30):
`EXPLORATORY_OOS_SLICE_RULED_AS_FINAL_TWENTY_PERCENT_OF_COMMITTED_DESIGN_UTC_DATES` ·
`READ_GRANT_BINDS_TO_APPROVED_IMPLEMENTATION_ANCESTRY_NOT_SELF_REFERENTIAL_EXECUTION_HEAD`

**Still not granted, and not executed.** The scope is now determined; issuing the
grant is a separate step and running the read is a separate approval again.

**Always-binding:** `NO_REAL_DATA_READ_PERFORMED` · `NO_EXECUTION_PERFORMED` ·
`PRODUCTION_READINESS_NOT_CLAIMED` ·
`FORWARD_EPOCH_ADOPTION_BLOCKED_INSUFFICIENT_SAMPLE_ADOPTION_WAITS`

**Risk tier:** Amber. This document records an authorization analysis and two
rulings. **It grants nothing** — see §8.

---

## 1. What this document is

The Minimum Research Execution Gate is merged (`37edbb0`). The remaining
precondition of a Track A R1 read is an explicit human + ChatGPT `ReadGrant`
naming the operation, span, pairs, timeframe and approved head SHA.

This document derives that scope **from the committed authorities only**. It
invents no date.

**An earlier revision of it found the grant could not be issued at all**, for two
reasons: the `EXPLORATORY_OOS_SLICE` boundary was unrecorded, so the development
span's end was underivable, and `approved_head_sha` was self-defeating, because
recording a grant moves `HEAD`. Both are now closed by ruling — §4 and §4a —
and the earlier reasoning is kept rather than deleted, because what a boundary
was *chosen against* is the only evidence that it was chosen outcome-blind.

Every element of the scope is now determined. **Issuing the grant is still a
separate act, and running the read is a separate approval after that.**

## 2. The `ReadGrant` schema, from source

`scripts/m15_track_a/authorization.py` — **eight** required fields, each validated
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
| **approved head SHA** | the merged head carrying the approved read implementation | §4a — recorded, and **not** compared to `identity.code_sha` |
| **approved implementation fingerprint** | `containment.implementation_fingerprint()` at that head | §4a — the field the gate actually enforces, measured from the tree |
| **span start** | **2025-04-25** | `no_overlap.DESIGN_START`; prereg §3.1 "Design (exploratory) 2025-04-25 → 2026-02-28" |
| **excluded — dead window** | 2026-03-01 → 2026-04-24 | `no_overlap.DEAD_START`/`DEAD_END`; the consumed M1 holdout, quarantined at every timeframe for every role |
| **excluded — forward epoch** | 2026-04-25 onward | `no_overlap.FORWARD_FLOOR`. It is the **Track B confirmation dataset** and does not exist yet (`FORWARD_EPOCH_ADOPTION_BLOCKED_INSUFFICIENT_SAMPLE_ADOPTION_WAITS`) |
| **span end** | **2025-12-28** | §4 — the day before the ruled `EXPLORATORY_OOS_SLICE` |

## 4a. RULED — what a grant binds to

**`READ_GRANT_BINDS_TO_APPROVED_IMPLEMENTATION_ANCESTRY_NOT_SELF_REFERENTIAL_EXECUTION_HEAD`.**

### The problem, confirmed from source before it was fixed

`require_authorization` used to refuse unless
`identity.code_sha == grant.approved_head_sha`. Reading the two definitions
together shows what that actually was:

- `RunIdentity.code_sha` is **caller-asserted**. `identity.py` derives it from
  nothing; the module's own docstring said so, and the check's docstring
  admitted the limit.
- `ReadGrant.approved_head_sha` is likewise a string the grant's author writes.

So the check compared **two caller-asserted strings**. It refused an honest run
at the wrong head and refused a dishonest one never — a caller running anything
at all could assert the approved head and pass.

**And the self-reference was real, not theoretical.** A grant has to be recorded
in the repository before it is exercised; recording it is a commit; the commit
moves `HEAD`. An honest run at the new head is then refused by the grant that
the commit exists to record. There is no head an author can write into the field
that satisfies it: naming the pre-commit head fails at execution, and naming the
post-commit head is impossible because the commit does not exist yet.

### The ruling

**A grant binds to the approved *implementation*, measured, not to an asserted
head.** `ReadGrant` gains an eighth required field,
`approved_implementation_fingerprint`, and `require_authorization` refuses unless
it equals `containment.implementation_fingerprint()` **computed from the running
tree** at check time.

The fingerprint is a sha256 over the declared implementation surface: every
`.py` under `scripts/m15_track_a/` **recursively**, plus every `m15_gate3a`
module the package imports — `aggregation`, `no_overlap`, `pair_authority`,
`path_authority`. Paths are hashed with the bytes, and the file count with both,
so renaming a module or swapping two files does not cancel out. The surface is
located from the **package's own directory**, not from a repository root, so it
describes the code that is actually imported and gives the same value on the
approver's machine and the reviewer's.

Two of those details were measured rather than assumed, and both were wrong in
the first drafting:

* it globbed **non-recursively**, so `m15_track_a/helpers/reader.py` would have
  been outside the fingerprint entirely — the read logic could move one
  directory down and keep an old grant valid;
* it listed only the two modules `read_route` imports, leaving `aggregation`
  (the derivation route's delegate) and `path_authority` (which decides what is
  inside the scratch root) uncovered.

A test now pins the sibling list against the package's **actual** imports, since
the failure mode is a fifth import that nobody adds to the list.

Coverage was then measured on clones, not argued: a byte changed in
`read_route.py`, `isolation.py` or `no_overlap.py`, a new module, a module in a
new subdirectory, and a deleted module each change the value; a byte-identical
copy at a different path does not.

What this buys, exactly:

| Change after approval | Old check | Ruled check |
| --- | --- | --- |
| a commit recording the grant, or a document | ❌ voided the grant | ✅ grant stands |
| one byte of `read_route.py`, `isolation.py`, `no_overlap.py`, … | ✅ if honest | ✅ **always** |
| a caller asserting the approved head while running other code | ❌ passed | ✅ refused |

### The sequence, and it is the plain one

1. **#453's final head is fixed** and its implementation reviewed.
2. **Human + ChatGPT approve that implementation head.**
3. #453 is merged. The merge commit changes `HEAD` and changes **no** covered
   file, so the fingerprint is unchanged.
4. An **authorization-only** commit records the `ReadGrant`, carrying the
   approved head SHA and that fingerprint.
5. The read runs at a head at or after (4). The fingerprint check passes because
   nothing on the implementation surface moved.
6. Any substantive change re-opens the approval, automatically: the fingerprint
   no longer matches and the grant is refused with no human in the loop.

### The limit, stated rather than implied

This binds the **implementation**, not the **ancestry**. Whether the execution
head descends from the approved head is a `git` question, and reaching git from
inside a gated read means spawning a process the isolation layer exists to
refuse. It stays a **gate-time obligation on the reviewer**, discharged with

```
git merge-base --is-ancestor <approved_head_sha> HEAD
git diff --stat <approved_head_sha>..HEAD
```

and it is the weaker of the two checks: a head with identical implementation
bytes reads identically wherever it sits in the graph.

Two further limits, on the same footing as the rest of this apparatus:
the fingerprint covers **source files**, so it does not see an installed
dependency changing under it; and code in the same process can bypass any
in-process check, which is what `AUDIT_BOUNDS` has said throughout.

## 4. RULED — the `EXPLORATORY_OOS_SLICE` boundary

**`EXPLORATORY_OOS_SLICE_RULED_AS_FINAL_TWENTY_PERCENT_OF_COMMITTED_DESIGN_UTC_DATES`.**

### What R-2 fixed, and what it left open

§4's **R-2**, in its own words:

> **Chronological only** — the **final contiguous portion of the design span**,
> the M1 precedent's shape. No random split, no shuffled k-fold …
>
> **Quarantined from R1 onward.** The boundary is **chosen and recorded before
> stage R1**, and **no stage before R4 may read, describe, plot or compute a
> statistic over it — descriptive statistics included**.
>
> **Purge counted in bars, never wall-clock.** ≥ 25 M15 bars (`horizon + 1`) of
> the design span immediately preceding the slice are dropped from training.

R-2 fixed the **shape** and the **timing of the decision**. It fixed no
**size** — and the previous revision of this document therefore refused to name
a date, recording
`THE_EXPLORATORY_OOS_SLICE_BOUNDARY_IS_UNRECORDED_AND_R_2_REQUIRES_IT_BEFORE_R1`
after searching the contract packet, the pre-registration, the gate-4 design
audit, the playbook and the policy.

**Two near-misses were checked and rejected then, and are still rejected:**

- **The 25% training prefix** (§8.8) fixes `n_initial_training_dates = 78`, a
  training-only block `2025-04-25 … 2025-07-11`, over `N_design_dates = 310`.
  That is the **`c`-map estimator's** *initial* block — the opposite end of the
  span, for a different purpose.
- **T_v / T_h** (prereg §3.1) are the **forward epoch's** validation/holdout
  boundaries, `[FIXED-AT gate 3a]`, not a design-span internal split.

Neither is the slice. So the size was a genuine human decision, and it has now
been taken.

### The ruling

The `EXPLORATORY_OOS_SLICE` is the **final 20% of the committed DESIGN span,
counted in UTC calendar dates**:

* the unit is the **UTC calendar date** — consistent with §3.7's
  `CALENDAR_UTC_DATES_NO_MARKET_HOURS`;
* the population is the **committed DESIGN span only**;
* `tail = ceil(0.20 × number_of_design_dates)`;
* the tail is **contiguous** and ends on the last design date;
* **no weekday or market-day snapping**;
* computed **without looking at any price, outcome or metric**;
* it is the **N = 1** exploratory OOS (`oos_budget`), consumed at its first
  decision-bearing observation;
* it is **completely separate** from every ordinary development read;
* once read, it is **not reused**.

**A human chose the fraction. No human chose a date.** That separation is why
the arithmetic lives in `scripts/m15_track_a/oos_slice.py` rather than in prose:
`0.20` is a number that can be argued about before any data exists, and
`2025-12-29` is a consequence of it and two committed constants. The module
reads no file, no environment variable and no clock, and a test asserts that on
its AST.

### The derivation, in full

Every input is a committed constant; every step is integer or calendar
arithmetic.

| Step | Source | Value |
| --- | --- | --- |
| `DESIGN_START` | `no_overlap.py` | `2025-04-25` |
| `DESIGN_END` | `no_overlap.py` | `2026-02-28` (23:59:59Z) |
| `number_of_design_dates` | inclusive date count | **310** |
| `tail` | `ceil(0.20 × 310)` | **62** |
| `slice_start` | `DESIGN_END − (tail − 1)` days | **2025-12-29** |
| `slice_end` | `= DESIGN_END`; a *final* portion ends nowhere else | **2026-02-28** |
| `development_end` | `slice_start − 1` day | **2025-12-28** |
| `development_start` | `= DESIGN_START` | **2025-04-25** |

**310 is a cross-check, not a coincidence.** The pre-registration's 25%-prefix
ruling (§8.8) arrived at `N_design_dates = 310` independently, which confirms the
counting convention — inclusive, UTC dates — rather than supplying a second
authority for it.

The ceiling is computed as `-(-n * 20 // 100)`, exact integer arithmetic. A
boundary that depended on how binary floating point rounds `0.2` would be a
boundary nobody could check by hand.

### Why the ≥ 25-bar purge is **not** subtracted from the read span

The earlier revision sketched `span_end_utc = slice_start − ≥25 M15 bars`. That
is wrong, in a way worth recording:

1. **The purge is a *training* exclusion.** R-2 says those bars "are dropped
   **from training**". Dropping a bar from training is a stage that runs on data
   this read has already returned.
2. **It is counted in bars, and counting bars requires reading them.** Making
   the read span depend on an eligible-bar index is circular: R1 is the read.
3. **Converting it to calendar days would mean inventing a number.** "Enough
   days to certainly contain 25 M15 bars" depends on weekends and holidays, and
   picking a safe margin is exactly the invention this document refuses.

So the read stops at `development_end`, and the purge binds downstream — the
same division §8.11.12 **F-5** already records at `DESIGN_END` itself, where a
Friday-afternoon signal bar's 24-bar label reaches into the dead window. The
labels are purged; the bars are read.

This read returns **M1 rows only** — no labels, no features, no statistics — so
nothing it returns observes the slice.

### The quarantine is enforced, not just recorded

`read_route.assert_development_only` refuses any `track_a_historical_read` whose
**touched** interval — warm-up included — reaches `slice_start` or later. It sits
beside `assert_span_admissible` rather than inside it, because the design-span
and dead-window bounds come from the committed `no_overlap` module while this
boundary comes from a ruling, and collapsing the two would hide which authority
refused a read.

It **refuses**; it does not trim. A read silently shortened to the development
span leaves the caller believing it got what it asked for.

## 5. The development `ReadGrant`, in full

The scope that follows from §4 and §4a, and the only scope an ordinary Track A
R1 read may be granted:

```
operation                          = track_a_historical_read
span_start_utc                     = 2025-04-25
span_end_utc                       = 2025-12-28
pairs                              = PAIRS_20   (all twenty)
timeframe                          = M1
approved_head_sha                  = <the merged head carrying the approved implementation>
approved_implementation_fingerprint = <containment.implementation_fingerprint() at that head>
approver_record                    = <the recorded human + ChatGPT approval>
```

248 UTC dates. Excluded, each by its own mechanism:

| Excluded | From | Enforced by |
| --- | --- | --- |
| `EXPLORATORY_OOS_SLICE` `2025-12-29 … 2026-02-28` | the grant span, and the route | `assert_development_only`, and a separate operation |
| dead window `2026-03-01 … 2026-04-24` | every role, every timeframe | `assert_span_admissible`, `no_overlap` |
| forward epoch `2026-04-25` onward | every Track A operation | `assert_span_admissible`, and a row-level floor |
| anything outside the grant | — | the grant ∩ request intersection |

**Warm-up does not get an exemption.** A warm-up extension that reaches past
`2025-12-28` is refused, not trimmed: a bar read to prime an indicator is read.

**The two grants that are not this one.** Reading the slice is
`track_a_exploratory_oos_slice_read`, with its own approval and `N = 1`; deriving
M15 is `track_a_m15_research_derivation`, with its own approval. Neither is
implied by this one, and `grant_covers` refuses a grant for one operation
driving another.

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

## 7. What the grant, when issued, will not cover

Recorded now so the eventual grant is read narrowly:

- **not** the `EXPLORATORY_OOS_SLICE` — a separate operation, a separate
  authorization, and Q7's `N = 1`, consumed at its first decision-bearing
  observation;
- **not** the M1 → M15 derivation — `track_a_m15_research_derivation` is its own
  grant, and playbook §2.5 forbids chaining irreversible stages;
- **not** the forward epoch, in any role;
- **not** the dead window 2026-03-01 → 2026-04-24;
- **not** any date from **2025-12-29** onward, by span and by route;
- **not** Formal Confirmation, and no Track A output may be cited for one;
- **not** training, evaluation, calibration or any fitted object — R1 reads;
  R3 and R4 are separate Red gates with separate approvals;
- **not** broker, live, demo, order submission, network, external DB or
  production deployment.

## 8. Non-authorisation statement

This document authorises **nothing**, and that is unchanged by the two rulings
it now records. A determined scope is not a grant, and a grant is not an
execution command.

**No `ReadGrant` is issued here, and none is committed anywhere in this PR.**
That is deliberate. A grant needs the approved head SHA and the implementation
fingerprint of a **merged** head, and no such head exists while this PR is open;
committing a grant that names an unmerged head would point an authorisation at
code that can still change. §4a step 4 puts the grant in a separate
authorization-only commit after merge, which is the simplest order that is also
checkable.

Three things remain outstanding, in order, and none of them is discharged by
this document:

1. human + ChatGPT approval of **this implementation head**;
2. the authorization-only commit **recording** the grant §5 specifies;
3. an explicit **execution command** for the read itself.

The route refuses without a grant regardless of what is written here.
`NO_REAL_DATA_READ_PERFORMED`; `NO_EXECUTION_PERFORMED`;
`PRODUCTION_READINESS_NOT_CLAIMED`.
