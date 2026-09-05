# M15 Track A R1 — the two grants, issued on the preflight-binding implementation

**Status: `TRACK_A_R1_DUAL_GRANTS_REISSUED_FINAL_PREFLIGHT_COMPLETE_READY_FOR_EXPLICIT_EXECUTION_COMMAND`.**

**Approval identifier: PR #462**, merged at the head that carries this file.
Before that merge this record is not citable authority; the merge is what
confers it.

**Always-binding:** `NO_REAL_DATA_READ_PERFORMED` · `NO_EXECUTION_PERFORMED` ·
`PRODUCTION_READINESS_NOT_CLAIMED` ·
`FORWARD_EPOCH_ADOPTION_BLOCKED_INSUFFICIENT_SAMPLE_ADOPTION_WAITS`

> **The first two of those four were discharged for this scope on 2026-09-05**,
> when these grants were exercised. The line above is left as recorded; it is not
> a current claim.

**These are authorizations. Neither is an execution command**, and recording
them runs nothing. Nothing has been read; the development corpus is `UNSEEN` and
the seen-data ledger is empty.

> **Exercised on 2026-09-05.** The paragraph above describes the state when these
> grants were recorded and is left as written; it is no longer the current state.
> An explicit human + ChatGPT execution command authorised Track A R1, both
> grants were spent once through `r1_orchestrator.run_r1`, and the development
> corpus is now **`EXPLORATORY_SEEN_DATA`**. No grant field below is altered.
> See `m15_track_a_r1_execution_record.md`.

**Risk tier:** Amber. Authorization-only: no implementation, contract, strategy,
model, feature, calendar, reader, derivation, streaming, orchestrator,
fingerprint or survey code changes here. The diff touches `docs/`, `tests/` and
`CLAUDE.md` — a review role caught "`docs/` and `tests/` only" being false in
three places at once. None of the three is on the fingerprint surface, which is
the property that matters and which a test in this PR **measures** rather than
assumes.

**What "final preflight" means, and what it does not.** It means §5a's checklist
reaches 15 of 15: the last two outstanding items were these two grants, and they
are now issued against the implementation that would actually run. It does
**not** mean these grants are immune to what comes next. Any change on the
declared surface moves the fingerprint and voids them both, with no human in the
loop — that has happened five times and the mechanism is the point, not a
nuisance.

---

## 1. Why these are being issued again

**Three** grant records exist before this one, and the fingerprint has moved
**five** times. Those are different counts and the table separates them: the
first three rows are documents a human approved, the next two are values no
document records as a grant.

| Record | PR | Fingerprint | Surface | What voided it |
| --- | --- | --- | --- | --- |
| `m15_track_a_r1_read_grant.md` | #454 | `497e187b…` | — | the enablement work |
| `m15_track_a_r1_dual_grants.md` | #456 | `e43583e0…` | 26 | the authorization-integrity fixes |
| `m15_track_a_r1_dual_grants_reissued.md` | #458 | `64fbace9…` | 29 | the R1 orchestrator |
| — | #459 | `1f1f0ed5…` | 30 | the bounded-memory route |
| — | #460 | `c1e71fd3…` | 32 | the preflight binding |
| **this record** | **#462** | **`e147542a…`** | **32** | — |

**Every recorded grant *field* is left exactly as a human approved it, and
re-issuing is a separate act from rewriting.** That is the guarantee, and
`test_the_three_superseded_records_are_still_refused` enforces it by reading the
superseded fingerprints out of the documents and requiring the gate to refuse
each one.

It is a narrower guarantee than "the earlier documents are never edited", which
an earlier draft of this paragraph claimed. A review role checked `git log`
rather than the claim: `m15_track_a_r1_dual_grants_reissued.md` has been edited
three times since its own merge, each time to update the "value to re-issue
against" pointer it carries. No grant field was touched, but the document was.
`test_the_recorded_reissue_fingerprint_is_the_measured_one` is repointed at
**this** record in the same change, so that pointer no longer lives on a
superseded one and a future move does not require editing history again.

**What changed in the implementation these two grants bind to**, since the pair
at `64fbace9…`:

- **PR #459 — the R1 orchestrator.** `scripts/m15_track_a/r1_orchestrator.py`
  is the formal entry point binding preflight → write-ahead seen declaration →
  gated M1 read → authorised M15 derivation **on the same `ReadRequest`** →
  breadth `K` → the committed survey → stop. It reaches no next stage by
  construction; calling the stages by hand is not the formal route.
- **PR #460 — the bounded-memory route.** The read and the derivation run window
  by window, so the retained raw M1 rows are a property of the window rather
  than of the corpus. The old shape held every row of every pair at once, about
  4.5–6 GB, and an OOM would have landed *after* the irreversible seen
  declaration.
- **PR #461 — the preflight binding.** The implementation fingerprint is
  measured **once before the read** instead of about 321 times a run, roughly
  320 of which sat after that same declaration, where a refusal costs the corpus
  rather than nothing. A second measurement closes the interval after the last
  window. Neither is a gate a window can trip over.

None of the three widens a data scope. What they change is the route, its memory
profile and where its identity checks happen.

## 2. Grant A — the historical development read

| Field | Value |
| --- | --- |
| **operation** | `track_a_historical_read` |
| **span_start_utc** | `2025-04-25` |
| **span_end_utc** | `2025-12-28` |
| **pairs** | the registered `PAIRS_20`, all twenty (§3a) |
| **pairs_explicit** | AUD_CAD AUD_JPY AUD_NZD AUD_USD CHF_JPY EUR_AUD EUR_CAD EUR_CHF EUR_GBP EUR_JPY EUR_USD GBP_AUD GBP_CHF GBP_JPY GBP_USD NZD_JPY NZD_USD USD_CAD USD_CHF USD_JPY |
| **timeframe** | `M1` |
| **approved_head_sha** | `0bb987e775658db3532affdc3992cad94382faa3` |
| **approved_implementation_fingerprint** | `e147542aec04f2cf781c5ecd062d8a08b1d058007634c54357f00756736b5e50` |
| **approver_record** | `PR #462 · docs/governance/m15_track_a_r1_dual_grants_final_preflight.md §2 (2026-09-04)` |

**Recorded on the human operator's explicit written instruction of 2026-09-04 to
re-issue both grants against the merged PR #461 implementation.** PR #462's
human + ChatGPT approval and merge is the act that confers authority; before
that merge this is a draft. `approver_record` points at this section because
this paragraph is where the approval is written down.

248 inclusive UTC calendar dates.

```python
from scripts.m15_gate3a.pair_authority import PAIRS_20
from scripts.m15_track_a.authorization import OPERATION_HISTORICAL_READ, ReadGrant

READ_GRANT = ReadGrant(
    operation=OPERATION_HISTORICAL_READ,
    span_start_utc="2025-04-25",
    span_end_utc="2025-12-28",
    pairs=tuple(sorted(PAIRS_20)),
    timeframe="M1",
    approved_head_sha="0bb987e775658db3532affdc3992cad94382faa3",
    approved_implementation_fingerprint=(
        "e147542aec04f2cf781c5ecd062d8a08b1d058007634c54357f00756736b5e50"
    ),
    approver_record=(
        "PR #462 · docs/governance/m15_track_a_r1_dual_grants_final_preflight.md §2 (2026-09-04)"
    ),
)
```

## 3. Grant B — the M15 research derivation

| Field | Value |
| --- | --- |
| **operation** | `track_a_m15_research_derivation` |
| **span_start_utc** | `2025-04-25` |
| **span_end_utc** | `2025-12-28` |
| **pairs** | the registered `PAIRS_20`, all twenty (§3a) |
| **pairs_explicit** | AUD_CAD AUD_JPY AUD_NZD AUD_USD CHF_JPY EUR_AUD EUR_CAD EUR_CHF EUR_GBP EUR_JPY EUR_USD GBP_AUD GBP_CHF GBP_JPY GBP_USD NZD_JPY NZD_USD USD_CAD USD_CHF USD_JPY |
| **timeframe** | `M1` |
| **approved_head_sha** | `0bb987e775658db3532affdc3992cad94382faa3` |
| **approved_implementation_fingerprint** | `e147542aec04f2cf781c5ecd062d8a08b1d058007634c54357f00756736b5e50` |
| **approver_record** | `PR #462 · docs/governance/m15_track_a_r1_dual_grants_final_preflight.md §3 (2026-09-04)` |

**Recorded on the same human instruction of 2026-09-04, and approved by the same
merge.** Two grants, one decision; policy §2.5 is why the decision produces two
objects rather than one widened.

Grant B authorises the derivation over **the development M1 input Grant A
authorises, and nothing else**: the approved arm (i) route, for R1 only.

**`timeframe` is `M1`, and that is not a typo.** The grant names the timeframe of
the **input** the derivation consumes, which is what `grant_covers` compares
against `read_request.timeframe`. M15 is the output; it does not exist until this
operation runs.

**And that comparison is between two caller-supplied strings**, which is worth
saying plainly rather than implying a check that is not there. `read_historical`
pins its grant against the committed constant — `checked.timeframe !=
SOURCE_TIMEFRAME` raises — and **`derive_m15` has no equivalent**: a review role
measured a self-consistent non-`M1` derivation grant (grant, request and read all
naming `M15`) running to completion. Nothing widens as a result, because
`row_scope` validates every row against the grant∩request window whatever the
label says, and the rows can only have come from a read the read route already
pinned to `M1`. But the value in this grant is `M1` because that is what the
operation consumes, **not** because a wrong value would be caught, and a future
re-issue writing `M15` here — the natural mistake, given the operation's name —
would be honoured and recorded.

`DERIVATION_ROUTE_DOES_NOT_PIN_ITS_TIMEFRAME_TO_THE_COMMITTED_SOURCE_CONSTANT_REFERRED`
— adding the pin edits `derivation.py`, which is on the fingerprint surface and
would void these grants the moment it merged, so it is a separate Work PR. This
referral is carried forward unchanged from the PR #458 record.

```python
from scripts.m15_gate3a.pair_authority import PAIRS_20
from scripts.m15_track_a.authorization import OPERATION_M15_DERIVATION, ReadGrant

DERIVATION_GRANT = ReadGrant(
    operation=OPERATION_M15_DERIVATION,
    span_start_utc="2025-04-25",
    span_end_utc="2025-12-28",
    pairs=tuple(sorted(PAIRS_20)),
    timeframe="M1",
    approved_head_sha="0bb987e775658db3532affdc3992cad94382faa3",
    approved_implementation_fingerprint=(
        "e147542aec04f2cf781c5ecd062d8a08b1d058007634c54357f00756736b5e50"
    ),
    approver_record=(
        "PR #462 · docs/governance/m15_track_a_r1_dual_grants_final_preflight.md §3 (2026-09-04)"
    ),
)
```

## 4. What is being read, and how

The **only** authorised route is `scripts/m15_track_a/r1_orchestrator.run_r1`,
which takes both grants and runs, in this order:

```
preflight                      no MARKET-DATA file is opened; refusals cost 0 data bytes
  -> freeze the verified binding   the fingerprint and both grants, measured once
  -> declare the seen interval write-ahead, BEFORE the read
  -> derive_streaming          window by window: the gated read and the authorised
                               derivation, each window's raw M1 rows released
                               before the next window is read
  -> close the interval        one full fingerprint measurement after the last window
  -> record breadth K          result_observed=False: R1 scores nothing
  -> r1_survey.survey          the committed survey, unmodified
  -> STOP
```

Calling the stages by hand is not this route and is not what these grants
authorise.

## 5. What neither grant reaches

Neither grant covers, and `require_authorization` refuses, every one of:

| Excluded | Span or scope |
| --- | --- |
| `EXPLORATORY_OOS_SLICE` | `2025-12-29 … 2026-02-28` |
| dead window | `2026-03-01 … 2026-04-24` |
| forward epoch | `2026-04-25` onward |
| future data | anything after the forward floor |
| pre-DESIGN | anything before `2025-04-25` |
| out-of-scope pairs | anything outside the registered `PAIRS_20` |
| out-of-scope timeframes | anything but `M1` |

A `track_a_historical_read` grant **cannot even be constructed** over a span
reaching the slice: `_assert_operation_span` refuses at construction, so the
ceiling is on the grant object where no caller-supplied request can reach it.

Grant B additionally does not authorise:

- a **direct `aggregate_m15` bypass** — the committed aggregator refuses real
  rows outside the derivation route;
- any input the read grant did not cover — `row_scope` validates **every input
  row** against the grant∩request intersection, and refuses on the rows
  actually received rather than on caller trust;
- strategy search, model fitting, threshold selection, training, validation,
  holdout, or any Formal Confirmation step.

**A read grant does not authorise a derivation and a derivation grant does not
authorise a read** (policy §2.5). Neither covers the other's operation, and
neither covers `track_a_exploratory_oos_slice_read`.

## 6. What these grants are still not

They are **authorizations, not an execution command.** R1 is Red: running it
needs an explicit human + ChatGPT instruction naming the operation, span, pairs,
timeframe and approved head SHA, given as an act at the time of running. No
recorded grant, no passed gate and no fully-ticked checklist supplies that.

`ReadGrant` is where an approval is **recorded and enforced in-process**. The
object does not verify that the approval exists, so constructing one is never
the act of granting it. It binds to a **measured implementation fingerprint**,
so any change on the declared surface voids it with no human in the loop.

Inside Track A, R1 (first read), R3 (training) and R4 (evaluation) remain
**separate Red gates**. These two grants reach R1 and stop.

## 7. Binding

| Value | Source |
| --- | --- |
| `0bb987e775658db3532affdc3992cad94382faa3` | the merge commit of PR #461, on `master` |
| `e147542aec04f2cf781c5ecd062d8a08b1d058007634c54357f00756736b5e50` | `containment.implementation_fingerprint()` **measured on that merged tree**, and again on a clean `git archive` of it |

Surface: **32** files — every `.py` under `scripts/m15_track_a/` plus the
transitive first-party import closure, resolved through the import system.

`approved_head_sha` is a caller-asserted string and the fingerprint is not: the
fingerprint is what `require_authorization` measures and compares. A commit that
adds an authorisation record, a document or a test keeps these grants valid;
**any** change to what a read actually does voids them.

This document is outside the fingerprint surface, and a test in this PR proves
it by measuring the value before and after writing a governance file rather
than asserting it.
