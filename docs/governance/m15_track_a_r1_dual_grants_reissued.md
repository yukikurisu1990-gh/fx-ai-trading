# M15 Track A R1 — the two grants, re-issued on the remediated implementation

**Status: `BOTH_GRANTS_INVALIDATED_BY_THE_R1_ORCHESTRATOR_REISSUE_REQUIRED_ON_THE_NEW_FINGERPRINT`.**

They were valid at `c2cdea0`. The R1 orchestrator
(`scripts/m15_track_a/r1_orchestrator.py`) joined the declared surface — 29 files
to 30 — so the fingerprint moved off `64fbace9…` and `require_authorization`
refuses both, with no human in the loop. Expected: §11 of the orchestrator brief
required it and forbade narrowing the surface to avoid it. The surface got wider.

The value to re-issue against, measured on this head and recorded here so a
human does not have to rediscover it:
**`c070b045a58422e936ca6e57965b4c70e8921b03aa1affb25291c813c0dd5d76`** (surface
30 files). Recording it is not issuing a grant against it.

**This document is kept as a historical governance record and is not edited to
match.** Everything below about *scope* still holds — span, pairs, timeframe,
operations, and what neither grant reaches — because that is a ruling and did not
change. What no longer holds is the binding.

Superseded status, retained for the record:
`TRACK_A_R1_DUAL_GRANTS_REISSUED_AND_READY_FOR_EXPLICIT_EXECUTION_COMMAND`

**Approval identifier: PR #458**, merged at the head that carries this file.
Before that merge this record is not citable authority; the merge is what
confers it.

**Always-binding:** `NO_REAL_DATA_READ_PERFORMED` · `NO_EXECUTION_PERFORMED` ·
`PRODUCTION_READINESS_NOT_CLAIMED` ·
`FORWARD_EPOCH_ADOPTION_BLOCKED_INSUFFICIENT_SAMPLE_ADOPTION_WAITS`

**These are authorizations. Neither is an execution command**, and recording
them runs nothing. Nothing has been read; the development corpus is `UNSEEN`.

**Risk tier:** Amber. Authorization-only: no implementation, contract, strategy,
model, feature, calendar, reader, derivation, fingerprint or survey code changes
here.

---

## 1. Why these are being issued again

The grants recorded at PR #456 bound to fingerprint `e43583e0…`. PR #457 closed
the two authorization-integrity defects the review of #456 disclosed, both fixes
edit the declared surface, and the fingerprint moved — so both grants were
refused by `require_authorization`, with no human in the loop. That is the
binding working as designed, and it was expected before that work started.

`docs/governance/m15_track_a_r1_dual_grants.md` is left **unedited** as the
historical record of what was approved then. Re-issuing is a separate act from
rewriting a number a human gave.

**What changed in the implementation these grants bind to**, and it is the
reason to give them again rather than restore the old ones:

- the derivation validates **every input row** against the grant∩request window
  — slice, dead window, forward floor, bounds with warm-up, ordering, canonical
  pair spelling and row shape — and aggregates the validated snapshot rather
  than the caller's objects;
- `DerivationRequest`, `ReadRequest` and `HistoricalRead` are pinned to their
  exact types and snapshotted, so a post-gate `object.__setattr__` can neither
  widen the scope nor forge the record;
- the fingerprint surface is now the transitive closure it always claimed to be
  — 26 files to **29** — because relative imports resolve against the importing
  file's own package.

## 2. Grant A — the historical development read

| Field | Value |
| --- | --- |
| **operation** | `track_a_historical_read` |
| **span_start_utc** | `2025-04-25` |
| **span_end_utc** | `2025-12-28` |
| **pairs** | the registered `PAIRS_20`, all twenty (§3a) |
| **timeframe** | `M1` |
| **approved_head_sha** | `c2cdea03186f2a6e0f7ee394a0a039a24ef1a903` |
| **approved_implementation_fingerprint** | `64fbace9aa8e08d835ec36b8b7fca1562af6826341d3821987d2831aa7e15cc2` |
| **approver_record** | `PR #458 · docs/governance/m15_track_a_r1_dual_grants_reissued.md §2 (2026-09-02)` |

**Recorded on the human operator's explicit written instruction of 2026-09-02 to
re-issue this grant against the remediated implementation.** PR #458's human +
ChatGPT approval and merge is the act that confers authority; before that merge
this is a draft. `approver_record` points at this section because this paragraph
is where the approval is written down.

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
    approved_head_sha="c2cdea03186f2a6e0f7ee394a0a039a24ef1a903",
    approved_implementation_fingerprint=(
        "64fbace9aa8e08d835ec36b8b7fca1562af6826341d3821987d2831aa7e15cc2"
    ),
    approver_record=(
        "PR #458 · docs/governance/m15_track_a_r1_dual_grants_reissued.md §2 (2026-09-02)"
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
| **timeframe** | `M1` |
| **approved_head_sha** | `c2cdea03186f2a6e0f7ee394a0a039a24ef1a903` |
| **approved_implementation_fingerprint** | `64fbace9aa8e08d835ec36b8b7fca1562af6826341d3821987d2831aa7e15cc2` |
| **approver_record** | `PR #458 · docs/governance/m15_track_a_r1_dual_grants_reissued.md §3 (2026-09-02)` |

**Recorded on the same human instruction of 2026-09-02, and approved by the same
merge.** Two grants, one decision; policy §2.5 is why the decision produces two
objects rather than one widened.

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
would void these grants the moment it merged, so it is a separate Work PR.

```python
from scripts.m15_gate3a.pair_authority import PAIRS_20
from scripts.m15_track_a.authorization import OPERATION_M15_DERIVATION, ReadGrant

DERIVATION_GRANT = ReadGrant(
    operation=OPERATION_M15_DERIVATION,
    span_start_utc="2025-04-25",
    span_end_utc="2025-12-28",
    pairs=tuple(sorted(PAIRS_20)),
    timeframe="M1",
    approved_head_sha="c2cdea03186f2a6e0f7ee394a0a039a24ef1a903",
    approved_implementation_fingerprint=(
        "64fbace9aa8e08d835ec36b8b7fca1562af6826341d3821987d2831aa7e15cc2"
    ),
    approver_record=(
        "PR #458 · docs/governance/m15_track_a_r1_dual_grants_reissued.md §3 (2026-09-02)"
    ),
)
```

**What Grant B permits, and only this:** deriving the M15 bars R1 needs, from M1
rows obtained under **Grant A**, through the **approved arm (i) route** —
`derive_m15` delegating to the committed
`scripts.m15_gate3a.aggregation.aggregate_m15` — for **R1's survey and nothing
else**.

**What it forbids:** a direct `aggregate_m15` call bypassing the route; M1 input
from outside Grant A; input rows outside the grant∩request window whatever the
declaration says; M15 derived from the `EXPLORATORY_OOS_SLICE`, the dead window
or the forward epoch; strategy search; and Formal Confirmation.

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

`tests/m15_track_a/test_reissued_dual_grants.py` pins this block against
`scripts/m15_gate3a/pair_authority.py`, so the two cannot drift apart while the
suite is green.

## 4. Where every value comes from

| Value | Derived from |
| --- | --- |
| `2025-04-25` | `no_overlap.DESIGN_START`; prereg §3.1 |
| `2025-12-28` | `oos_slice.DEVELOPMENT_END_UTC` — the day before the ruled slice |
| slice `2025-12-29 … 2026-02-28` | `ceil(0.20 × 310)` = 62 final DESIGN dates |
| `PAIRS_20` | `scripts/m15_gate3a/pair_authority.py` |
| `M1` | `read_route.SOURCE_TIMEFRAME`; the committed `365d_BA` epoch is M1 bid/ask |
| `c2cdea0…` | the merge commit of PR #457 |
| `64fbace9…` | `containment.implementation_fingerprint()` **measured on that merged tree** |

The fingerprint was **measured, not transcribed**. A value reported in a previous
session's summary is not an authority; the number above came from running the
committed function on merged `master` after clearing `__pycache__`, and was
cross-checked against the git blobs at that head — the LF bytes CI sees — which
agree. That cross-check is what makes the recorded value reproducible on another
machine.

## 5. What neither grant authorizes

| Not authorized | Refused by |
| --- | --- |
| **`EXPLORATORY_OOS_SLICE`** `2025-12-29 … 2026-02-28` | `ReadGrant.__post_init__` refuses a **read** grant naming a slice date — and only a read grant: `_assert_operation_span` leaves the derivation operation unconstrained on purpose, so a slice-spanning derivation grant *constructs*. What stops it is `assert_development_only` on the declared interval, on **both** routes, and — since PR #457 — `assert_clear_of_slice` on **every input row** of a derivation. Both measured firing |
| the **dead window** `2026-03-01 … 2026-04-24` | `assert_span_admissible` via `no_overlap` on both routes; a row-level refusal on the read route and, since PR #457, on the derivation route too |
| the **forward epoch**, `2026-04-25` onward | `assert_span_admissible`; a row-level `FORWARD_FLOOR` refusal on both routes |
| **pre-DESIGN** data, before `2025-04-25` | `assert_span_admissible` on the warm-up-widened interval; the row-level window bound |
| any date outside `2025-04-25 … 2025-12-28`, **warm-up included** | `grant_covers` inside `require_authorization`, then the row-level **grant∩request** window — narrowest wins on both ends |
| any pair outside `PAIRS_20` | `pair_authority` refuses it before a path is built |
| an **alias spelling** of a registered pair (`EURUSD`, `eur/usd`) | `grant_covers` at the request level and `assert_batch_pairs_in_scope` on the batch. Not `pair_authority`, which *canonicalises* aliases rather than refusing them — recorded because the mechanism, not only the outcome, is what a reviewer checks |
| any timeframe but `M1` | **the read route** refuses a grant naming another (`checked.timeframe != SOURCE_TIMEFRAME`); the derivation route compares the grant only against the request, so §3's referral applies — no data scope widens either way |
| a **direct `aggregate_m15`** call | `derivation_containment` — a process latch scoped to the opening thread and task, plus a per-row provenance marker |
| a request that widens **after** the gates | the exact-type pins and the three snapshots |
| **training, fitting, evaluation, calibration** | R3 and R4 are separate Red gates with separate approvals |
| Sharpe, `c`, `ω`, `N_eff` as empirical figures | not authorised here in any form |
| the **T-3 measurement** | a Track A duty at the declared candidate under its frozen cost table — not R1's |
| **Formal Confirmation** | the Two-Track contract |
| broker, live, demo, network, external DB, production | the isolation guards, and these grants' silence |

**Warm-up is not an exemption.** A request whose warm-up reaches before
`2025-04-25`, or whose span reaches past `2025-12-28`, is **refused, not
trimmed**.

**Nothing is filtered.** A row outside the authorisation means the batch is not
what the authorisation describes; silently working on the compliant subset would
return a result that looks correct and is not.

## 6. Seen-data — what this costs, and when

**Authorising is not reading. Nothing is seen yet**, and the development corpus
is `UNSEEN` at this head. No seen-data ledger file exists yet — `git ls-files
artifacts/track_a_scratch/` is empty and so is the directory on disk — which is
stronger than an empty ledger and weaker than the sentence an earlier drafting
used.

**At the read**, and not before, the interval becomes `EXPLORATORY_SEEN_DATA`:

- **it does not return** — `SEEN_IS_TERMINAL_AND_NO_RULING_CAN_RESTORE_UNSEEN_STATUS`;
- **it reaches every timeframe.** M1 rows and the M15 bars derived from them are
  the same information at a different resolution, which is also why Grant B
  spends no *additional* seen-data: it derives from rows Grant A already marked;
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
  The surface is **29 files** and, since PR #457, **is** the transitive
  first-party closure — verified against two independently computed ones, with
  relative imports resolved against the importing file's own package. It covers
  the read route, the derivation route, `row_scope`, the survey, `authorization`,
  `containment`, `derivation_containment`, `session_windows`, `aggregation`,
  `no_overlap`, `timeutil`, `oos_slice`, the `ml_step4` adapter chain and
  `scripts/train_lgbm_models.py`.
- **What a source fingerprint cannot see** is in `containment.AUDIT_BOUNDS`: an
  `UNCHECKED_HASH` `.pyc` over unchanged source, an installed dependency, a
  non-`.py` file loaded at run time. Add to that a **dynamic** first-party import
  of the form `importlib.import_module(".x", __package__)`, which the closure
  does not follow — §7a records why that is not a blocker here.
- **Ancestry is a gate-time reviewer obligation**, not an in-process check — git
  is unreachable from inside a gated read:

  ```
  git merge-base --is-ancestor c2cdea03186f2a6e0f7ee394a0a039a24ef1a903 HEAD
  git diff --stat c2cdea03186f2a6e0f7ee394a0a039a24ef1a903..HEAD
  ```

## 7a. The dynamic-import disclosure, and why it is not a blocker here

The closure follows static imports. A first-party module reached only through
`importlib.import_module(".x", __package__)` would sit outside the surface, so
rewriting it would not void a grant. The behaviour is identical at PR #456's
base — it is a disclosure, not a regression — and closing it needs a
source-level prohibition rather than better import resolution.

**Measured at this head before these grants were issued**, because the standing
instruction is to stop if the R1 path actually depends on that form. The whole
29-file surface was scanned on its AST for `import_module`, `__import__`,
`exec_module`, `module_from_spec`, `eval` and `exec`. Two call sites exist:

| site | what it imports | outside the surface? |
| --- | --- | --- |
| `containment._check_single_read_route` | the **14** modules of `scripts.m15_track_a`, enumerated by `package_modules()` | **no** — all 14 are already covered by the package walk |
| `isolation._import_or_none` | optional **third-party** dependencies only; no `scripts.*` name reaches it | not first-party |

So no first-party dependency of the R1 execution path escapes the fingerprint
through a dynamic import. `DYNAMIC_FIRST_PARTY_IMPORT_CLOSURE_GAP_DISCLOSED_NOT_A_R1_EXECUTION_BLOCKER`.
No search for unknown dynamic-import routes was opened.

## 8. The previous grants stay invalid

| record | fingerprint | status |
| --- | --- | --- |
| `m15_track_a_r1_read_grant.md` (PR #454) | `497e187b…` | invalid |
| `m15_track_a_r1_dual_grants.md` (PR #456) | `e43583e0…` | invalid |

Both are left exactly as recorded. Their numbers are **not edited** — each is a
number a human approved, and rewriting one would forge an approval nobody gave.
`test_recorded_read_grant.py` and `test_recorded_dual_grants.py` assert both the
invalidation and that the recorded values were not rewritten.

## 9. What remains before a read

`TRACK_A_R1_DUAL_GRANTS_REISSUED_AND_READY_FOR_EXPLICIT_EXECUTION_COMMAND`.

**One human act, and one piece of engineering.**

The human act: an **explicit human + ChatGPT execution command** naming the
operation, the span, the pairs, the timeframe and the head it runs on. A
real-data read is **Red**, and policy wants that approval *before the run* — an
act, not a document state. Neither these grants, nor a passed execution gate, nor
playbook §5a at 15 of 15 supplies it. Constructing a `ReadGrant` in code is not
the act of granting one, and reading a ticked checklist is not the act of being
commanded.

The engineering, stated because "one thing" would be false without it: **there is
the R1 orchestrator is done.** PR #459 added
`scripts/m15_track_a/r1_orchestrator.py`, the formal entry point, and it passes
**one** `ReadRequest` object to both calls. `DerivationRequest(` now appears in
exactly one committed script — that one. Writing it moved the fingerprint, which
is why the grants above are invalid and why the next step is re-issuing them
rather than running anything. There is still no CLI or `__main__`, deliberately:
an execution affordance is not what an unauthorised head should gain.

## 10. Referrals these grants do not touch

`PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED` · the T-3 numerator ·
Ruling 4's holiday list · P-14 ·
`C_MAP_PREDICTED_DATE_COUNT_VS_OOS_SLICE_QUARANTINE_UNRESOLVED_REFERRED`. None is
in R1's scope and none is returned to it. Route B and the declared-label coverage
diagnostic are unchanged.

## 11. Non-authorisation statement

This document authorises **two** operations, at the scope and implementation
named above, and only when an execution command runs them. It authorises no
training, no evaluation, no OOS read, no broker or network access and no
deployment. No real data was read in producing it.

`NO_REAL_DATA_READ_PERFORMED`; `NO_EXECUTION_PERFORMED`;
`PRODUCTION_READINESS_NOT_CLAIMED`.
