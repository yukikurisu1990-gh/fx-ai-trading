# M15 Track A R1 — the two recorded grants

**Status: `BOTH_GRANTS_INVALIDATED_BY_PR_457_REISSUE_REQUIRED_ON_THE_NEW_FINGERPRINT`.**

They were valid at `fc3e0f8`. PR #457 closed the two authorization-integrity
defects §5a and §7 disclosed, both fixes edit the declared surface, and the
fingerprint moved off `e43583e0…` — so `require_authorization` refuses both, with
no human in the loop. That is the binding working as designed and it was expected
before that work started.

**This document is kept as a historical governance record and is not edited to
match.** The numbers below are the ones a human approved; re-issuing is a
separate act from rewriting. What still holds is everything here about *scope* —
span, pairs, timeframe, operations, and what neither grant reaches — because that
is a ruling and did not change. What no longer holds is the binding, and §7a says
exactly which claims PR #457 falsified.

Superseded status, retained for the record:
`TRACK_A_R1_HISTORICAL_DEVELOPMENT_READ_REAUTHORIZED_ON_CURRENT_IMPLEMENTATION`
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

**Recorded on the human operator's explicit written instruction of 2026-08-31 to
issue this grant against the merged implementation.** PR #456's human + ChatGPT
approval and merge is the act that confers authority; before that merge this is
a draft. `approver_record` points at this section because this paragraph is
where the approval is written down.

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

**Recorded on the same human instruction of 2026-08-31, and approved by the same
merge.** Two grants, one decision; §2.5 is why the decision produces two objects
rather than one widened.

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
| the **dead window** `2026-03-01 … 2026-04-24` | `assert_span_admissible` via `no_overlap` on both routes; **plus** a row-level refusal on the read route only (§5a) |
| the **forward epoch**, `2026-04-25` onward | `assert_span_admissible` on both routes; **plus** a row-level `FORWARD_FLOOR` refusal on the read route only (§5a) |
| **pre-DESIGN** data, before `2025-04-25` | `assert_span_admissible`, on the warm-up-widened interval |
| any date outside `2025-04-25 … 2025-12-28`, **warm-up included** | `grant_covers` inside `require_authorization`; the grant ∩ request intersection on both routes |
| any pair outside `PAIRS_20` | `pair_authority`, before a path is built |
| any timeframe but `M1` | the read route refuses a grant naming another |
| a **direct `aggregate_m15`** call | `derivation_containment` — a process latch, which is the load-bearing half, plus a per-row provenance marker whose limits §5a records |
| **training, fitting, evaluation, calibration** | R3 and R4 are separate Red gates with separate approvals |
| Sharpe, `c`, `ω`, `N_eff` as empirical figures | not authorised here in any form |
| the **T-3 measurement** | a Track A duty at the *declared candidate under its frozen cost table* — not R1's, and R1 reaches no verdict |
| **Formal Confirmation** | the Two-Track contract |
| broker, live, demo, network, external DB, production | the isolation guards, and these grants' silence |

**Warm-up is not an exemption.** A request whose warm-up reaches before
`2025-04-25`, or whose span reaches past `2025-12-28`, is **refused, not
trimmed**.

## 5a. The slice defence is not symmetric, and this is where it differs

**The read route has three layers of span defence. The derivation route has
one.** Two review roles at PR #456 measured the difference; an earlier revision
of this document asserted the opposite, so it is set out here in full rather
than summarised.

**Layer 1 — the grant constructor. Present for the read, absent for the
derivation.** `_assert_operation_span` constrains `track_a_historical_read` (may
not reach past `2025-12-28`) and `track_a_exploratory_oos_slice_read` (may name
only slice dates), and constrains `track_a_m15_research_derivation` **not at
all** — not the slice, not the dead window, not the forward epoch, not
`1900-01-01 … 2099-12-31`. That is deliberate; its docstring says the derivation
"derives over whatever its own read was authorised for, and its route applies
the development gate itself."

**Layer 2 — the declaration gate. Present on both, and it works.** `derive_m15`
runs `require_authorization` → `assert_span_admissible` →
`assert_development_only(read_request)` → `DELEGATE`, and the third refuses the
whole slice, a span reaching one day into it, and a warm-up extension reaching
back into it, before any aggregation. Measured, not assumed.

**Layer 3 — the row-level guards. Present for the read, absent for the
derivation.** `read_historical` carries `is_dead_window_instant`, the
`FORWARD_FLOOR` row check, `assert_clear_of_slice` on the computed window, and
`type(request) is not ReadRequest` — because, as its own commentary says,
metadata checks "cannot see bytes" and "a subclass can answer a field
differently each time it is read". **`derive_m15` carries none of the four.** It
gates what a request *declares* and never compares a row's timestamp against the
interval it just gated. An adversarial role demonstrated both consequences on
synthetic rows: rows dated inside the slice, the dead window and the forward
epoch aggregate under the recorded Grant B; and a `ReadRequest` subclass honest
at the gates and widened afterwards produces a `DerivedM15` labelled over the
slice while the seen-data ledger records five development days.

**What this does and does not mean.**

- It **does not** reach protected data. No route in this repository can produce
  slice, dead-window or forward rows: `read_historical` refuses them at three
  layers, and it is the only reader. The demonstration had to hand-build the
  rows.
- It **does** mean Grant B's span constrains the *declaration* and not the
  *bytes*, so the guarantee is one layer thinner than the read's.
- It **matters at execution time**, because no R1 orchestrator exists in this
  repository yet (`DerivationRequest(` appears in no committed script). Whoever
  writes the read→derive composition must pass the **same** `ReadRequest` object
  to both calls. Building it twice is the failure mode.

**Neither recorded grant names a slice, dead-window or forward date**, so this
costs these two authorizations nothing. It is disclosed because a reviewer who
believed the earlier text would have counted layers that are not there.

`DERIVATION_ROUTE_ROW_LEVEL_GUARDS_AND_REQUEST_TYPE_PIN_ABSENT_REFERRED` —
closing the gap means editing `derivation.py`, which is on the fingerprint
surface and would void both grants the moment it merged. It is therefore a
separate Work PR, taken **before** any execution command, not folded into an
authorization-only record.

`test_a_derivation_grant_over_the_slice_is_stopped_by_the_route` and
`test_the_derivation_route_has_no_row_level_guards` pin both halves — the layer
that holds and the layer that is missing — so neither can change silently.

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
- **Any change on the declared surface voids both**, with no human in the loop.
  The surface is **26 files**: every `.py` under `scripts/m15_track_a/` plus an
  import closure resolved through `importlib`, so a shadowed module is hashed as
  it would actually be loaded. It covers the read route, the derivation route,
  the survey, `authorization`, `containment`, `derivation_containment`,
  `session_windows`, `aggregation`, `no_overlap`, `timeutil` and the data
  adapter — and also `scripts/train_lgbm_models.py`, so editing that research
  script voids both grants too.
- **The surface is not the transitive closure, and this record does not claim it
  is.** `containment._first_party_imports` resolves every **relative** import
  against `scripts.m15_track_a` regardless of which package the file is in, so
  `scripts/m15_gate3a/aggregation.py`'s four relative imports resolve to modules
  that do not exist and are dropped. Measured at this head: surface **26**, true
  closure **28**; the two outside it are `scripts/ml_step4/contract.py` and
  `scripts/ml_step4/inventory.py`, both off the Track A read path
  (`inventory` is reached only from `RealDataAdapter.verify()`, which Track A
  never calls). The reachable consequence an adversarial role demonstrated: a
  **new** module added to `scripts/m15_gate3a/` and imported relatively is
  outside the surface, so rewriting it afterwards leaves the fingerprint —
  and both grants — unchanged.
  `FINGERPRINT_SURFACE_IS_NOT_THE_TRANSITIVE_CLOSURE_RELATIVE_IMPORTS_MISRESOLVED_REFERRED`:
  fixing it edits `containment.py`, which is *on* the surface and would void
  these grants the moment it merged, so it is a separate Work PR taken before
  any execution command. `test_the_disclosed_closure_gap_is_still_exactly_this`
  pins the gap so it cannot widen unnoticed.
- **What a source fingerprint cannot see** is in `containment.AUDIT_BOUNDS`: an
  `UNCHECKED_HASH` `.pyc` over unchanged source, an installed dependency, a
  non-`.py` file loaded at run time. Add to that list the closure gap above, and
  the fact that the surface is walked **outward** from `scripts/m15_track_a/`:
  a future R1 runner that *imports* the package is not in the closure and would
  not void either grant. That is intended — the routes gate regardless of
  caller — but it is not something the fingerprint protects.
- **Ancestry is a gate-time reviewer obligation**, not an in-process check — git
  is unreachable from inside a gated read:

  ```
  git merge-base --is-ancestor fc3e0f881d424844ca6823ae2708b76839c313dc HEAD
  git diff --stat fc3e0f881d424844ca6823ae2708b76839c313dc..HEAD
  ```

## 7a. What PR #457 changed about this record

Two claims in §5a and §7 were disclosures of defects. Both defects are closed, so
both disclosures are now **historical**:

| §5a said | now |
| --- | --- |
| `derive_m15` carries none of the read route's four row-level guards | it validates **every input row** against the grant-request intersection — slice, dead window, forward floor, window bounds, ordering, pair scope, canonical spelling and row shape — pins `DerivationRequest`, `ReadRequest` and `HistoricalRead` to their exact types, and snapshots all three so a post-gate `object.__setattr__` cannot widen the scope or forge the record (`scripts/m15_track_a/row_scope.py`) |
| Grant B constrains the declaration, not the bytes | it constrains the bytes: the rows that are validated are the rows that are aggregated, because a normalised snapshot is what reaches the delegate |

| §7 said | now |
| --- | --- |
| the surface is **not** the transitive closure — 26 files against a closure of 28 | relative imports resolve against the importing file's own package, and the surface (**29**) **is** the closure, measured against two independently computed ones; the fingerprint is `56a22b46…` → **`64fbace9…`** after the review fixes |
| `scripts/ml_step4/{contract,inventory}.py` sit outside it | both are covered |
| a new module in `scripts/m15_gate3a/`, imported relatively, escapes | it does not; rewriting one moves the fingerprint |

`DERIVATION_ROUTE_ROW_LEVEL_GUARDS_AND_REQUEST_TYPE_PIN_ABSENT_REFERRED` and
`FINGERPRINT_SURFACE_IS_NOT_THE_TRANSITIVE_CLOSURE_RELATIVE_IMPORTS_MISRESOLVED_REFERRED`
are **discharged at PR #457**.

The surface went from **26 files to 29** — wider, not narrower. §5 of the
remediation brief forbade preserving these grants by shrinking it, and nothing
was shrunk or excepted.

## 8. The previous grant stays invalid

`docs/governance/m15_track_a_r1_read_grant.md` records a grant bound to
`497e187bb9fcfbc51a348d59c486bccf8d0e7c27c6fbf52cc28908a8073a7018`. The R1
enablement work moved the fingerprint, so that grant is **invalid**, and it is
left that way: its recorded number is **not edited**, because it is the number a
human approved. `tests/m15_track_a/test_recorded_read_grant.py` asserts both the
invalidation and that the number was not rewritten.

## 9. What remains before a read

`TRACK_A_R1_DUAL_GRANTS_RECORDED_AND_PREFLIGHT_COMPLETE_READY_FOR_EXPLICIT_EXECUTION_COMMAND`.

**One human act, and one piece of engineering.**

The human act: an **explicit human + ChatGPT execution command** naming the
operation, the span, the pairs, the timeframe and the head it runs on. Recording
these grants is not that command, and constructing a `ReadGrant` object in code
is not the act of granting one. A real-data read is **Red**, and CLAUDE.md wants
that approval *before the run*, which is an act rather than a document state —
so neither these grants, nor a passed execution gate, nor playbook §5a at 15 of
15 supplies it. The instruction that authorised these grants directed in the
same breath that nothing be executed.

The engineering, stated because "exactly one thing" would be false without it:
**there is no R1 orchestrator in this repository.** `DerivationRequest(` appears
in no committed script, no module in `scripts/m15_track_a/` has a `__main__`,
and the only read → derive → survey composition that exists is a pytest fixture.
Writing that runner is Amber code work, and §5a is the reason it has to pass one
`ReadRequest` object to both calls rather than building it twice.

Two disclosed defects should be closed before that runner is pointed at real
data — `DERIVATION_ROUTE_ROW_LEVEL_GUARDS_AND_REQUEST_TYPE_PIN_ABSENT_REFERRED`
(§5a) and
`FINGERPRINT_SURFACE_IS_NOT_THE_TRANSITIVE_CLOSURE_RELATIVE_IMPORTS_MISRESOLVED_REFERRED`
(§7). Both edit the fingerprint surface, so both void these grants and require
re-issue on the new fingerprint. That is the mechanism working, not an
obstacle.

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
