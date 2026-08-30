# M15 Track A R1 — the recorded historical development `ReadGrant`

**Status:** `TRACK_A_R1_HISTORICAL_DEVELOPMENT_READ_EXPLICITLY_AUTHORIZED`

**Always-binding:** `NO_REAL_DATA_READ_PERFORMED` · `NO_EXECUTION_PERFORMED` ·
`PRODUCTION_READINESS_NOT_CLAIMED` ·
`FORWARD_EPOCH_ADOPTION_BLOCKED_INSUFFICIENT_SAMPLE_ADOPTION_WAITS`

**This document records an authorization. It does not run anything.** An
authorization and an execution command are different acts, and this is the
first. Nothing in this repository reads market data because this file exists;
the read happens only when a human + ChatGPT execution command says so, and
whoever issues that command is the one authorising the irreversible part.

**Risk tier:** Amber. Authorization-only: this commit changes no implementation,
no contract semantics, no strategy, model or feature code.

---

## 1. The authorization

Recorded as an explicit human + ChatGPT decision, 2026-08-31.

| Field | Value |
| --- | --- |
| **operation** | `track_a_historical_read` |
| **span_start_utc** | `2025-04-25` |
| **span_end_utc** | `2025-12-28` |
| **pairs** | the registered `PAIRS_20`, all twenty |
| **timeframe** | `M1` |
| **approved_head_sha** | `6b75aab0161fe7caf74b4260feec8d43cbfd618e` |
| **approved_implementation_fingerprint** | `497e187bb9fcfbc51a348d59c486bccf8d0e7c27c6fbf52cc28908a8073a7018` |
| **approver_record** | this document, `docs/governance/m15_track_a_r1_read_grant.md` §1 |

Both dates are **inclusive UTC calendar dates**: 248 dates, `2025-04-25`
through `2025-12-28`.

The twenty pairs, from `scripts/m15_gate3a/pair_authority.py` — the grant names
the universe, not a copy of it, and the constructor normalises through that
authority:

```
AUD_CAD  AUD_JPY  AUD_NZD  AUD_USD  CHF_JPY
EUR_AUD  EUR_CAD  EUR_CHF  EUR_GBP  EUR_JPY
EUR_USD  GBP_AUD  GBP_CHF  GBP_JPY  GBP_USD
NZD_JPY  NZD_USD  USD_CAD  USD_CHF  USD_JPY
```

### The grant, as the object the gate checks

Transcribed, not retyped from memory. A mistyped fingerprint fails closed.

```python
from scripts.m15_gate3a.pair_authority import PAIRS_20
from scripts.m15_track_a.authorization import OPERATION_HISTORICAL_READ, ReadGrant

GRANT = ReadGrant(
    operation=OPERATION_HISTORICAL_READ,
    span_start_utc="2025-04-25",
    span_end_utc="2025-12-28",
    pairs=tuple(sorted(PAIRS_20)),
    timeframe="M1",
    approved_head_sha="6b75aab0161fe7caf74b4260feec8d43cbfd618e",
    approved_implementation_fingerprint=(
        "497e187bb9fcfbc51a348d59c486bccf8d0e7c27c6fbf52cc28908a8073a7018"
    ),
    approver_record="docs/governance/m15_track_a_r1_read_grant.md §1 (2026-08-31)",
)
```

## 2. Where every value comes from

Nothing here was chosen while writing this document.

| Value | Derived from |
| --- | --- |
| `2025-04-25` | `no_overlap.DESIGN_START`; prereg §3.1 |
| `2025-12-28` | `oos_slice.DEVELOPMENT_END_UTC` — the day before the ruled slice |
| slice `2025-12-29 … 2026-02-28` | `ceil(0.20 × 310)` = 62 final DESIGN dates, `EXPLORATORY_OOS_SLICE_RULED_AS_FINAL_TWENTY_PERCENT_OF_COMMITTED_DESIGN_UTC_DATES` |
| `PAIRS_20` | `scripts/m15_gate3a/pair_authority.py` |
| `M1` | the committed `365d_BA` epoch is M1 bid/ask; M15 does not exist until the derivation runs |
| `6b75aab…` | the merge commit of PR #453, the head carrying the approved implementation |
| `497e187b…` | `containment.implementation_fingerprint()` on that head |

The fingerprint was computed by the committed function on merged `master`, with
its surface and hash algorithm unchanged. It was cross-checked against the git
blobs at `HEAD` — the LF bytes CI sees — and the two agree, which is the
property the approval workflow needs: the value recorded here is reproducible on
the reviewer's machine and on the runner, not only on the authoring host.

## 3. What this grant does **not** authorize

Each of these is refused by a named mechanism, not only by this list.

| Not authorized | Refused by |
| --- | --- |
| **`EXPLORATORY_OOS_SLICE`**, `2025-12-29 … 2026-02-28` | the grant's own span; `ReadGrant.__post_init__` refuses a `track_a_historical_read` grant naming a slice date at all; `read_route.assert_development_only` on the touched interval; and again on the computed window |
| the **dead window**, `2026-03-01 … 2026-04-24` | `assert_span_admissible` via `no_overlap`; a row-level refusal |
| the **forward epoch**, `2026-04-25` onward | `assert_span_admissible`; a row-level `FORWARD_FLOOR` refusal |
| any date outside `2025-04-25 … 2025-12-28`, **warm-up included** | the grant ∩ request intersection; the ledger's write-ahead declaration |
| any pair outside `PAIRS_20` | `pair_authority`, before a path is built |
| any timeframe but `M1` | the route refuses a grant naming another, including `M15` |
| the **M1 → M15 derivation** | `track_a_m15_research_derivation` is a separate operation and a separate grant |
| **training, fitting, evaluation, calibration** | R3 and R4 are separate Red gates with separate approvals |
| Sharpe, `c`, `ω`, `N_eff` as empirical figures | not authorised here in any form |
| **Formal Confirmation**, and citing any Track A output for one | the Two-Track contract |
| broker, live, demo, order submission, network, external DB, production | the isolation guards, and this grant's silence |

**A warm-up extension is not an exemption.** A bar read only to prime an
indicator is read. A request whose warm-up reaches before `2025-04-25` or whose
span reaches past `2025-12-28` is **refused, not trimmed**.

## 4. Seen-data — what this costs, and when

**Authorising is not reading, and nothing is seen yet.** The development corpus
remains untouched until an execution command runs the read.

**At that moment**, and not before, the interval read becomes
`EXPLORATORY_SEEN_DATA`:

- **it does not return.**
  `SEEN_IS_TERMINAL_AND_NO_RULING_CAN_RESTORE_UNSEEN_STATUS`;
- **it reaches every timeframe.** M1 rows and the M15 bars derived from them are
  the same information at a different resolution, so the declaration ignores the
  timeframe field;
- **it reaches every pair named in the declaration**;
- **warm-up counts**, and the ledger checks the warm-up-widened start;
- **a discarded run still spends it.** The ledger is append-only and
  write-ahead: the interval is recorded *before* it is touched, so a run that
  dies mid-read still leaves the span marked;
- **it never becomes Track B confirmation evidence.** The historical corpus is
  the Track A **development** dataset; the unseen forward epoch is the Track B
  **confirmation** dataset. The roles do not swap back.

**The `EXPLORATORY_OOS_SLICE` stays unread and unauthorised.** It is not covered
by this grant, it is quarantined until R4, and reading it is
`track_a_exploratory_oos_slice_read` — a separate approval with an `N = 1`
budget, consumed at its first decision-bearing observation.

## 5. What invalidates this grant, automatically

The grant binds to `approved_implementation_fingerprint`, measured from the
running tree at check time —
`READ_GRANT_BINDS_TO_APPROVED_IMPLEMENTATION_ANCESTRY_NOT_SELF_REFERENTIAL_EXECUTION_HEAD`.

- **A commit that records an authorization or a document keeps it valid.** That
  is the sequencing this design exists for: the commit adding *this file* moves
  `HEAD` and changes no covered file, so the fingerprint is unchanged. A test
  asserts that.
- **Any change on the declared implementation surface voids it**, with no human
  in the loop: the package's `.py` files and their transitive first-party import
  closure, resolved through `importlib` so a shadowed module is hashed as it
  would actually be loaded. A test asserts that too.
- **What a source fingerprint cannot see** is in
  `containment.AUDIT_BOUNDS`: an `UNCHECKED_HASH` `.pyc` over unchanged source
  (which needs no craft, and which `__pycache__` being gitignored keeps out of
  any diff), an installed dependency changing underneath, and a non-`.py` file
  loaded at run time. Run the read with `python -B` or
  `PYTHONDONTWRITEBYTECODE=1` and no populated `__pycache__` if that matters to
  the reader.
- **Ancestry is a gate-time obligation on the reviewer**, not an in-process
  check — `git` is unreachable from inside a gated read. Before executing:

  ```
  git merge-base --is-ancestor 6b75aab0161fe7caf74b4260feec8d43cbfd618e HEAD
  git diff --stat 6b75aab0161fe7caf74b4260feec8d43cbfd618e..HEAD
  ```

  It is the weaker of the two: identical implementation bytes read identically
  wherever they sit in the graph.

## 6. What remains before a read

`TRACK_A_R1_READ_GRANT_RECORDED_AND_READY_FOR_EXPLICIT_EXECUTION_COMMAND`.

Exactly one thing: an **explicit human + ChatGPT execution command** naming the
operation, the span, the pairs, the timeframe and the head it runs on.

Recording this grant is **not** that command, and constructing a `ReadGrant`
object in code is not the act of granting one — `authorization.py` says so, and
this document says so because a reader arriving here from a search result should
not have to go and check.

## 7. Not carried by this authorization

`C_MAP_PREDICTED_DATE_COUNT_VS_OOS_SLICE_QUARANTINE_UNRESOLVED_REFERRED` is
open: the 25%-prefix ruling (§8.9.1, c-15) fixes 232 predicted DESIGN dates
running to `2026-02-28`, which includes all 62 slice dates that R-2 quarantines
before R4. Either the `c`-map's estimation is an R4-or-later activity, or the
count available before R4 is 170 rather than 232 (`248 = 78 + 170`); no recorded
ruling says which.

**It does not touch this grant's scope** — the development span is 248 dates
under either resolution — and it is named here so that it is not mistaken for
something this authorization settled. It binds a later stage.

## 8. Non-authorisation statement, for everything else

This document authorises **one** thing: the operation, span, pairs, timeframe
and implementation named in §1, and only when an execution command runs it. It
authorises no derivation, no training, no evaluation, no OOS read, no broker or
network access and no deployment. No real data was read in producing it, and no
training, evaluation or fitting was performed.

`NO_REAL_DATA_READ_PERFORMED`; `NO_EXECUTION_PERFORMED`;
`PRODUCTION_READINESS_NOT_CLAIMED`.
