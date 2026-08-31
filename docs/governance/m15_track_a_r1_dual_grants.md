# M15 Track A R1 — the two recorded grants

**Status:** `TRACK_A_R1_HISTORICAL_DEVELOPMENT_READ_REAUTHORIZED_ON_CURRENT_IMPLEMENTATION`
· `TRACK_A_R1_M15_RESEARCH_DERIVATION_AUTHORIZED_ON_CURRENT_IMPLEMENTATION`

**Approval identifier: PR #456**, merged at the head that carries this file.
Before that merge this record is not citable authority; the merge is what
confers it.

**Always-binding:** `NO_REAL_DATA_READ_PERFORMED` · `NO_EXECUTION_PERFORMED` ·
`PRODUCTION_READINESS_NOT_CLAIMED` ·
`FORWARD_EPOCH_ADOPTION_BLOCKED_INSUFFICIENT_SAMPLE_ADOPTION_WAITS`

**These are authorizations. Neither is an execution command**, and recording
them runs nothing. R1 executes when a human + ChatGPT execution command says so,
and whoever issues it is the one authorising the irreversible part.

**Risk tier:** Amber. Authorization-only: no implementation, contract, strategy,
model, feature, calendar or survey code changes here.

---

## 1. Why there are two

`derive_m15` requires `track_a_m15_research_derivation`, and a
`track_a_historical_read` grant does not cover it — playbook §2.5 forbids
chaining irreversible stages, and the route refuses the mismatch. R1 needs both:
it reads M1, then derives M15 from what it read. Two operations, two grants, one
implementation.

Both bind to the **same** measured implementation fingerprint, so a change to
what either route does voids **both** at once.

## 2. Grant A — the historical development read

| Field | Value |
| --- | --- |
| **operation** | `track_a_historical_read` |
| **span_start_utc** | `2025-04-25` |
| **span_end_utc** | `2025-12-28` |
| **pairs** | the registered `PAIRS_20`, all twenty |
| **timeframe** | `M1` |
| **approved_head_sha** | `fc3e0f881d424844ca6823ae2708b76839c313dc` |
| **approved_implementation_fingerprint** | `e43583e0d72b6f89a0cfe53b375b3b1d9df6062418423ec56a7db83c0d7bd752` |
| **approver_record** | `PR #456 · docs/governance/m15_track_a_r1_dual_grants.md §2 (2026-08-31)` |

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
    approved_head_sha="fc3e0f881d424844ca6823ae2708b76839c313dc",
    approved_implementation_fingerprint=(
        "e43583e0d72b6f89a0cfe53b375b3b1d9df6062418423ec56a7db83c0d7bd752"
    ),
    approver_record="PR #456 · docs/governance/m15_track_a_r1_dual_grants.md §2 (2026-08-31)",
)
```

## 3. Grant B — the M15 research derivation

| Field | Value |
| --- | --- |
| **operation** | `track_a_m15_research_derivation` |
| **span_start_utc** | `2025-04-25` |
| **span_end_utc** | `2025-12-28` |
| **pairs** | the registered `PAIRS_20`, all twenty |
| **timeframe** | `M1` |
| **approved_head_sha** | `fc3e0f881d424844ca6823ae2708b76839c313dc` |
| **approved_implementation_fingerprint** | `e43583e0d72b6f89a0cfe53b375b3b1d9df6062418423ec56a7db83c0d7bd752` |
| **approver_record** | `PR #456 · docs/governance/m15_track_a_r1_dual_grants.md §3 (2026-08-31)` |

**`timeframe` is `M1`, and that is not a typo.** The grant names the timeframe of
the **input** the derivation consumes, which is what `grant_covers` compares
against the request. M15 is the output; it does not exist until this operation
runs. A grant naming `M15` would be refused by the read route it inherits its
request from.

```python
from scripts.m15_gate3a.pair_authority import PAIRS_20
from scripts.m15_track_a.authorization import OPERATION_M15_DERIVATION, ReadGrant

DERIVATION_GRANT = ReadGrant(
    operation=OPERATION_M15_DERIVATION,
    span_start_utc="2025-04-25",
    span_end_utc="2025-12-28",
    pairs=tuple(sorted(PAIRS_20)),
    timeframe="M1",
    approved_head_sha="fc3e0f881d424844ca6823ae2708b76839c313dc",
    approved_implementation_fingerprint=(
        "e43583e0d72b6f89a0cfe53b375b3b1d9df6062418423ec56a7db83c0d7bd752"
    ),
    approver_record="PR #456 · docs/governance/m15_track_a_r1_dual_grants.md §3 (2026-08-31)",
)
```

**What Grant B permits, and only this:** deriving the M15 bars R1 needs, from M1
rows obtained under Grant A, through the **approved arm (i) route** —
`derive_m15` delegating to the committed
`scripts.m15_gate3a.aggregation.aggregate_m15`.

**What it forbids:** a direct `aggregate_m15` call bypassing the route (refused
at the aggregator by `derivation_containment`); M1 input from outside Grant A;
M15 derived from the `EXPLORATORY_OOS_SLICE` or the forward epoch; strategy
search; and Formal Confirmation.

## 3a. The pair universe, written out

Both grants name the same twenty. Spelled out because a table row reading "the
registered `PAIRS_20`" is a promise about a list a human approving this cannot
see, and the drift between the two would be silent.

The list, canonical and complete:

```
AUD_CAD AUD_JPY AUD_NZD AUD_USD CHF_JPY
EUR_AUD EUR_CAD EUR_CHF EUR_GBP EUR_JPY
EUR_USD GBP_AUD GBP_CHF GBP_JPY GBP_USD
NZD_JPY NZD_USD USD_CAD USD_CHF USD_JPY
```

`tests/m15_track_a/test_recorded_dual_grants.py` pins this block against
`scripts/m15_gate3a/pair_authority.py`, so the two cannot drift apart while the
suite is green.

## 4. Where every value comes from

| Value | Derived from |
| --- | --- |
| `2025-04-25` | `no_overlap.DESIGN_START`; prereg §3.1 |
| `2025-12-28` | `oos_slice.DEVELOPMENT_END_UTC` — the day before the ruled slice |
| slice `2025-12-29 … 2026-02-28` | `ceil(0.20 × 310)` = 62 final DESIGN dates |
| `PAIRS_20` | `scripts/m15_gate3a/pair_authority.py` |
| `M1` | the committed `365d_BA` epoch is M1 bid/ask |
| `fc3e0f8…` | the merge commit of PR #455 |
| `e43583e0…` | `containment.implementation_fingerprint()` **measured on that merged tree** |

The fingerprint was **measured, not transcribed**. A value reported in a previous
session's summary is not an authority; the number above came from running the
committed function on merged `master`, and was cross-checked against the git
blobs at `HEAD` — the LF bytes CI sees — which agree. That cross-check is what
makes the recorded value reproducible on another machine.

## 5. What neither grant authorizes

| Not authorized | Refused by |
| --- | --- |
| **`EXPLORATORY_OOS_SLICE`** `2025-12-29 … 2026-02-28` | `assert_development_only` on the touched interval and again on the computed window — on **both** routes, and see §5a for which layer stops which |
| the **dead window** `2026-03-01 … 2026-04-24` | `assert_span_admissible` via `no_overlap`; a row-level refusal |
| the **forward epoch**, `2026-04-25` onward | `assert_span_admissible`; a row-level `FORWARD_FLOOR` refusal |
| **pre-DESIGN** data, before `2025-04-25` | `assert_span_admissible`, on the warm-up-widened interval |
| any date outside `2025-04-25 … 2025-12-28`, **warm-up included** | `grant_covers` inside `require_authorization`; the grant ∩ request intersection on both routes |
| any pair outside `PAIRS_20` | `pair_authority`, before a path is built |
| any timeframe but `M1` | the read route refuses a grant naming another |
| a **direct `aggregate_m15`** call | `derivation_containment` — a process latch and a per-row marker, checked inside the aggregator |
| **training, fitting, evaluation, calibration** | R3 and R4 are separate Red gates with separate approvals |
| Sharpe, `c`, `ω`, `N_eff` as empirical figures | not authorised here in any form |
| the **T-3 measurement** | a Track A duty at the *declared candidate under its frozen cost table* — not R1's, and R1 reaches no verdict |
| **Formal Confirmation** | the Two-Track contract |
| broker, live, demo, network, external DB, production | the isolation guards, and these grants' silence |

**Warm-up is not an exemption.** A request whose warm-up reaches before
`2025-04-25`, or whose span reaches past `2025-12-28`, is **refused, not
trimmed**.

## 5a. The slice defence is not symmetric, and this is where it differs

Recording these grants turned up a fact worth stating plainly rather than
leaving in the code: **a `track_a_m15_research_derivation` grant can be
constructed over slice dates. A `track_a_historical_read` grant cannot.**

`_assert_operation_span` constrains two operations and deliberately not the
third — its docstring says so: `track_a_m15_research_derivation` "derives over
whatever its own read was authorised for, and its route applies the development
gate itself." So the derivation has **one** layer where the read has two.

That compensating control was measured, not assumed. `derive_m15` runs
`require_authorization` → `assert_span_admissible` →
`assert_development_only(read_request)` → `DELEGATE`, and the third call refuses
the whole slice, a span reaching one day into it, and a warm-up extension that
reaches back into it — before any aggregation happens.

Neither recorded grant names a slice date, so the asymmetry costs these two
authorizations nothing. It is recorded because the earlier revision of this
document claimed the grant constructor refused **both** operations, which is
false, and a reviewer who believed it would have counted a layer that is not
there. `test_a_derivation_grant_over_the_slice_is_stopped_by_the_route` pins the
real behaviour in both directions.

## 6. Seen-data — what this costs, and when

**Authorising is not reading. Nothing is seen yet**, and the development corpus
is `UNSEEN` at this head.

**At the read**, and not before, the interval becomes `EXPLORATORY_SEEN_DATA`:

- **it does not return** — `SEEN_IS_TERMINAL_AND_NO_RULING_CAN_RESTORE_UNSEEN_STATUS`;
- **it reaches every timeframe.** M1 rows and the M15 bars derived from them are
  the same information at a different resolution, so the declaration ignores the
  timeframe field — which is also why Grant B spends no *additional* seen-data:
  it derives from rows Grant A already marked;
- **it reaches every pair** named in the declaration;
- **warm-up counts**, and the ledger checks the warm-up-widened start;
- **a discarded run still spends it.** The ledger is append-only and write-ahead:
  the interval is recorded *before* it is touched;
- **it never becomes Track B confirmation evidence.**

The `EXPLORATORY_OOS_SLICE` stays unread and unauthorised under both grants.

## 7. What invalidates both grants, automatically

They bind to `approved_implementation_fingerprint`, measured from the running
tree at check time
(`READ_GRANT_BINDS_TO_APPROVED_IMPLEMENTATION_ANCESTRY_NOT_SELF_REFERENTIAL_EXECUTION_HEAD`).

- **A commit that records an authorization or a document keeps them valid.** The
  commit adding *this file* moves `HEAD` and changes no covered file. A test
  asserts it.
- **Any change on the declared surface voids both**, with no human in the loop:
  every `.py` under `scripts/m15_track_a/` plus its transitive first-party import
  closure, resolved through `importlib` so a shadowed module is hashed as it
  would actually be loaded. That includes the read route, the derivation route,
  the survey, the containment module, the session windows and the aggregator.
- **What a source fingerprint cannot see** is in `containment.AUDIT_BOUNDS`: an
  `UNCHECKED_HASH` `.pyc` over unchanged source, an installed dependency, a
  non-`.py` file loaded at run time.
- **Ancestry is a gate-time reviewer obligation**, not an in-process check — git
  is unreachable from inside a gated read:

  ```
  git merge-base --is-ancestor fc3e0f881d424844ca6823ae2708b76839c313dc HEAD
  git diff --stat fc3e0f881d424844ca6823ae2708b76839c313dc..HEAD
  ```

## 8. The previous grant stays invalid

`docs/governance/m15_track_a_r1_read_grant.md` records a grant bound to
`497e187bb9fcfbc51a348d59c486bccf8d0e7c27c6fbf52cc28908a8073a7018`. The R1
enablement work moved the fingerprint, so that grant is **invalid**, and it is
left that way: its recorded number is **not edited**, because it is the number a
human approved. `tests/m15_track_a/test_recorded_read_grant.py` asserts both the
invalidation and that the number was not rewritten.

## 9. What remains before a read

`TRACK_A_R1_DUAL_GRANTS_RECORDED_AND_PREFLIGHT_COMPLETE_READY_FOR_EXPLICIT_EXECUTION_COMMAND`.

Exactly one thing: an **explicit human + ChatGPT execution command** naming the
operation, the span, the pairs, the timeframe and the head it runs on. Recording
these grants is not that command, and constructing a `ReadGrant` object in code
is not the act of granting one.

## 10. Referrals these grants do not touch

`PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED` · the T-3 numerator ·
Ruling 4's holiday list · P-14 ·
`C_MAP_PREDICTED_DATE_COUNT_VS_OOS_SLICE_QUARANTINE_UNRESOLVED_REFERRED`. None is
in R1's scope and none is returned to it.

## 11. Non-authorisation statement

This document authorises **two** operations, at the scope and implementation
named above, and only when an execution command runs them. It authorises no
training, no evaluation, no OOS read, no broker or network access and no
deployment. No real data was read in producing it.

`NO_REAL_DATA_READ_PERFORMED`; `NO_EXECUTION_PERFORMED`;
`PRODUCTION_READINESS_NOT_CLAIMED`.
