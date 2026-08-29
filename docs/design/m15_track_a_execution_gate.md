# M15 Track A — Minimum Research Execution Gate (R1 enablement)

**Status:**
`TRACK_A_R1_EXECUTION_INFRASTRUCTURE_READY_PENDING_EXPLICIT_DATA_READ_AUTHORISATION`

**Always-binding:** `PRODUCTION_READINESS_NOT_CLAIMED` ·
`NO_EXECUTION_PERFORMED` · `NO_REAL_DATA_READ_PERFORMED` ·
`FORWARD_EPOCH_ADOPTION_BLOCKED_INSUFFICIENT_SAMPLE_ADOPTION_WAITS`

**Risk tier:** Amber. This document and the code it describes build the
apparatus for a Red operation; they do not perform it and do not authorise it.

---

## 1. What this gate is, and what it is not

The Two-Track amendment (`docs/design/m15_minimum_research_gate.md` §8.11–§8.13)
made exploratory M15 research **contractually** permissible. It deliberately
stopped there: `CONTRACT_PERMISSION_IS_NOT_EXECUTION_AUTHORISATION` (§8.12.3).

This gate is the missing half — the apparatus that makes a Track A R1 run
**safe to authorise**, so that the authorisation, when it is given, is a
decision about *whether* to read rather than a hope about *what the code will
do*.

**It is not:**

- a real-data read — nothing here opens a candle file;
- a derivation, training, evaluation, or fitting of anything;
- an authorisation for any of the above;
- a claim that Track A's research design is settled;
- a discharge of the 149-surface inventory, of Track B's freezes, or of the
  gate-3a continuation.

**The ordering it presumes**, and does not shortcut:

| # | Step | State |
| --- | --- | --- |
| 1 | Two-Track contract approval and merge (PR #451) | not taken |
| 2 | This execution gate reviewed, approved, merged | this PR |
| 3 | Explicit human + ChatGPT **real-data read authorisation** | not requested |
| 4 | Track A R1 execution | not performed |

Steps 2 and 3 are distinct on purpose. A merged execution gate says the
apparatus is sound; only step 3 says a read may happen, and it names the span
it covers.

## 2. The design rule every module here follows

> **Every route that could reach real data exists, is named, is gated, and its
> body is absent.**

Each route runs its full gate sequence and then raises `NotImplementedError`
with a token saying that every gate passed and nothing was read. Three
consequences, all intended:

1. **The gates are testable today**, against real refusals, with no data.
2. **A future implementing PR adds a body, not a policy.** It inherits the
   gates by construction; it cannot forget to add them, because the raise sits
   *after* them.
3. **An accidental call fails loudly.** There is no path on which a missing
   authorisation degrades to a silent read.

## 3. Module inventory

| Module | Responsibility |
| --- | --- |
| `scripts/m15_track_a/__init__.py` | the status tokens, and the output classification every artefact carries |
| `authorization.py` | the single gate: an in-process `ReadGrant`, never ambient |
| `scratch.py` | Q8 — the one write root, by positive containment |
| `isolation.py` | network, DNS, UDP, external DB, broker, live, demo, order submission — all off |
| `identity.py` | research-grade run identity and the declared calendar reading |
| `seen_ledger.py` | the write-ahead `EXPLORATORY_SEEN_DATA` ledger |
| `breadth.py` | the `K` record, in R-7's unit |
| `oos_budget.py` | Q7's `N = 1` on the `EXPLORATORY_OOS_SLICE` |
| `read_route.py` | the **one** historical read route |
| `derivation.py` | the **one** M1→M15 research derivation route |
| `containment.py` | the executable containment audit |

Tests: `tests/m15_track_a/` (three modules).

## 4. Authorisation — why an object and not an environment variable

`EXPLICIT_TRACK_A_DATA_READ_AUTHORIZATION_REQUIRED`.

An environment variable is **ambient**: it authorises every route in the
process, for the whole process lifetime, and it survives into subprocesses.
Playbook §2.9's "approval scope is exact" requires the opposite. So a grant is
an in-process frozen object a caller must construct and pass to the route it
authorises, naming:

- the **operation** — one of a closed set of three, checked at construction;
- the **span**, as explicit UTC dates;
- the **pairs** and the **timeframe**;
- the **approved head SHA** — a full 40-character lowercase hex SHA, because an
  abbreviated or absent SHA cannot identify the head an approval was given
  against;
- the **approver record** — where the human + ChatGPT approval is written down.

**Coverage is containment, not overlap.** A request reaching one day beyond the
granted span is refused; a request naming one pair the grant omits is refused;
a grant for a read does not cover a derivation. `type(value) is not str` is used
in place of `isinstance`, so a `str` subclass cannot lie about its content.

The module deliberately does **not** verify that the approver record exists.
Whether an approval is genuine is answered by the merge ceremony; this file
makes its **absence** a hard, early, typed failure.

## 5. Q8 — the write root

`artifacts/track_a_scratch/`, a module constant with no caller-supplied
component. Containment is **positive**: a path is writable only if it resolves
inside the root. A denylist of protected prefixes is kept as well, but as a
second line, not the mechanism.

Two specific holes are closed here:

- **The NR-A gap.** `scripts/m15_gate3a/guards._PROTECTED_PREFIXES` omits
  `artifacts/m15_gate3a`, so `refuse_real_path` **permits** the write
  §8.11.9 item 6 forbids. `scratch.assert_writable` refuses it, and a test
  pins the discrepancy so the gap cannot be closed silently in one place and
  left open in the other.
- **Reserved artefact names.** A file called `scrub_report.json` or
  `no_overlap_proof.json` can be cited as evidence whatever directory it sits
  in (§8.12.13 G-9). Those canonical filenames refuse **inside** the scratch
  root as well.

Path aliasing — extended-UNC spellings, trailing dots, `..`, relative paths —
is delegated to the committed `scripts/m15_gate3a/path_authority`, which has
been through four audit rounds. Track A does not re-derive it.

## 6. Isolation, enforced rather than asserted

A research runner is by definition an **unrouted caller** (§3.7), so guards are
installed on the primitives, not at call sites:

| Boundary | Enforcement |
| --- | --- |
| TCP | `socket.socket.connect`, `connect_ex` — non-loopback refuses |
| UDP | `socket.socket.sendto` — a `connect`-only guard misses it entirely |
| DNS | `socket.getaddrinfo`, `socket.gethostbyname` — a lookup reaches a resolver *before* any connection |
| External DB | `create_engine` patched at **three** module targets; in-memory SQLite only |
| Broker / live / demo / order submit / production deploy / external storage | refused by name, with the boundary quoted in the error |

Local file reads are **not** blocked: Track A exists to perform one, and which
files it may touch is `read_route`'s and `scratch`'s job, not the socket
guard's.

The same two residual routes — UDP and DNS — were also open in the **test
session's** guard (`tests/conftest.py`), recorded by the FR-19 review and left
unfixed. They are fixed here too, with tests in
`tests/contract/test_default_run_side_effect_free.py`.

## 7. The seen-data ledger

`EXPLORATORY_SEEN_DATA` is **write-ahead and append-only**: an interval is
declared *before* it is touched, so a run that dies mid-read still leaves the
span marked. Four rules, from §8.11.4:

1. Marking reaches **every timeframe** — a declaration deliberately ignores the
   timeframe field, because M1 rows and the M15 bars derived from them are the
   same information.
2. Marking reaches **every pair** named in the declaration.
3. **Warm-up counts.** The request's `touched_start_utc` is the warm-up-widened
   start, and it is that widened span the ledger checks.
4. **A discarded run still spends.** There is no un-declare.

`assert_declared` requires a **single** prior declaration to cover the request.
Stitching two partial declarations together is refused — an interval nobody
declared as one interval was never declared.

## 8. Breadth, budget, identity

- **`K`** (`breadth.py`) is counted in R-7's unit — the six axes
  `pair_set × feature_set × model × hyperparameters × threshold × split` — and
  counts **distinct** configurations whose result was observed. An unknown axis
  refuses rather than being recorded as a new degree of freedom.
- **`N`** (`oos_budget.py`) is Q7's `N = 1` on the `EXPLORATORY_OOS_SLICE`.
  There is no `set_budget` and no environment override. `N` and `K` are
  **different budgets** and neither substitutes for the other.
- **Identity** (`identity.py`) is research-grade and says so:
  `TRACK_A_RESEARCH_RUN_IDENTITY_NOT_EVIDENCE_GRADE_PROVENANCE`. The
  `ValidatedCalendar` artefact contract is unchanged for Track B; requiring it
  of Track A would block exploration on an artefact that does not exist, for no
  leakage reason. The calendar reading is a **declared label** from a closed
  set — Track A may not author market hours (ω-12) — and two runs with
  different labels are not comparable. Nothing here reads the wall clock.

## 9. The derivation route — arm (i), and what it costs

`RESEARCH_SCRATCH_M15_DERIVATION_ROUTE_NOT_SELECTED` named three arms.
**Arm (i) is selected**: reuse the committed
`scripts.m15_gate3a.aggregation.aggregate_m15`.

**Why not arm (ii)** — a second, fenced research aggregator: it is the only arm
that creates a *new* way to be wrong. The committed aggregator's defects are
known, enumerated and audited across four re-check rounds. A second
implementation starts at zero and diverges silently, which is exactly what the
weekend-gap defect was — one identical defect produced twice by two
implementations. One implementation with a BLOCKED audit is a known quantity;
two implementations are two unknown ones.

**What arm (i) costs, stated rather than absorbed.** The delegate's source audit
stands `M15_AGGREGATION_DATASET_MACHINERY_SOURCE_AUDIT_BLOCKED_PENDING_TARGETED_FIXES`,
so Track A would be giving an audit-blocked module its first real-data caller.
That cost is not paid by the code. It is paid by the authorisation — which names
the operation and the head — and by
`A_TRACK_A_DERIVATION_IS_NOT_THE_SECTION_4_ARTIFACT_AND_MAY_NOT_BE_RECORDED_AS_ONE`.

## 10. The turnover two-axis collision — RULED here

### 10.1 The collision

§8.7.5 locked two unregistered axes of the turnover budget **pre-observation**,
naming their permissive arms:

- **Axis 1 — mean versus per-day cap.** `metrics.py:120` computes a **mean**;
  prereg §9 says "≤ 40 trades/day". Since `max ≥ mean`, the mean is the
  permissive arm, and it is also the **incumbent** — it is what the committed
  code does.
- **Axis 2 — active-day versus calendar-day denominator.** The contract is
  silent; the committed code passes the **active** axis. The calendar
  denominator is larger, so it is the permissive arm — and §8.12.13 C-20 records
  that taking it widens the gate-4 corridor by about **42%**, "a loosening
  Ruling 10 forbids".

§8.13.13 then recorded the deadlock:
`THE_TURNOVER_AXES_ARE_FIXABLE_NEITHER_BEFORE_NOR_AFTER_TRACK_A_AND_THE_COLLISION_IS_UNRULED`
— §8.13.5 excludes strategy parameters from the Track A start conditions, so the
axes cannot be fixed before Track A; and the pre-observation lock cannot be
satisfied once Track A computes a single turnover figure.

### 10.2 The ruling

**`TURNOVER_AXES_FIXED_AT_THE_COMMITTED_IMPLEMENTATION_MEAN_OVER_ACTIVE_DAYS`.**

Both axes are fixed **now**, at the arms the committed implementation already
takes: the turnover figure is the **mean** trades per day over the **active**-day
denominator.

### 10.3 Why this is the minimum rule, and introduces no new research threshold

1. **No threshold moves.** The ceiling stays prereg §9's ≤ 40 trades/day. What
   is fixed is what the *measured* number means, not what it must be under.
2. **Nothing is chosen that was not already chosen.** Both arms are what
   `metrics.py` computes on this PR's base head. The ruling **records** an
   incumbent; it does not select among live options. The pre-observation
   requirement is therefore satisfied by construction: the arms were fixed in
   committed code long before Track A existed, and this document is written
   before the first read.
3. **Ruling 10 is satisfied on both axes.** Neither arm widens the corridor
   relative to today's behaviour — by definition, since it *is* today's
   behaviour. C-20's 42% widening arises only from switching axis 2 to the
   calendar denominator, which is **not** taken.
4. **§8.7.5's permissive-arm preference is honoured on axis 1 and overridden on
   axis 2.** On axis 1 the permissive arm and the incumbent coincide, so there
   is nothing to trade off. On axis 2 they diverge, and CLAUDE.md's rule
   applies: *the stricter reading of a research restriction wins*. Ruling 10's
   prohibition on loosening is the stricter reading; §8.7.5's naming of a
   permissive arm was a tie-break convention, not a licence to loosen. The
   override is recorded here rather than being read into §8.7.5.
5. **The lock's purpose is served.** A pre-observation lock exists so that an
   observation-informed choice cannot benefit the chooser. Here no choice is
   being made after any observation, because no observation exists — and the
   arm taken on the one axis where the arms differ is the **stricter** one,
   which could not benefit a chooser even if it were being chosen late.
6. **These are not strategy parameters.** §8.13.5 excludes strategy parameters
   from the Track A start conditions. A measurement convention of an incumbent
   implementation is not a candidate, a threshold, a feature or a
   hyperparameter, so §8.13.5 does not reach it and the "cannot be fixed before
   Track A" limb of the deadlock does not apply.

### 10.4 What this ruling does **not** do

- It does **not** discharge S-62 or S-63 as inventory surfaces. They remain
  decision-bearing for **Track B**, whose freeze is taken at candidate
  pre-registration; this ruling binds the *Track A* reading and the incumbent
  code path.
- It does **not** settle the gate-4 corridor question, which is a Track B
  acceptance matter.
- It does **not** touch the turnover **numerator**, the entry-date attribution
  (§8.7.5), or Q10(iii) — which §8.13's review confirmed does not move turnover
  at all.
- It creates no new token that a later reading can widen: the fixed arms are
  stated as the two concrete conventions, not as a principle.

## 11. Containment result

`scripts/m15_track_a/containment.py` is the executable form of playbook §4's
Track A variant. It walks the package's **AST** rather than matching substrings
— the first draft matched substrings and flagged its own source, which is the
shape of false assurance this whole programme keeps finding.

Eight checks: exactly one read route; exactly one derivation route; every route
gated by `authorization`; no ungated file-opening call outside the three ledger
modules; the write root is a constant; the isolation guards cover every named
boundary; no forbidden import reaches the package; and no route reaches a
forward-epoch span.

Final statuses:
`TRACK_A_EXECUTION_CONTAINMENT_VERIFIED_NO_UNGATED_ROUTE` /
`TRACK_A_EXECUTION_CONTAINMENT_BREACHED_UNGATED_ROUTE_FOUND`.

It is an **execution-containment** check, not a hostile-input audit, and it does
not replace the gate-6 source-contamination audit Track B still needs.

## 12. Governance propagation

The Two-Track model no longer requires reading PR #451 to discover:

| Where | What |
| --- | --- |
| `CLAUDE.md` | "Read first" entry; a Two-Track section before the working rules |
| playbook §2.1/§2.2 | the one narrow Track A exception to "no real read" |
| playbook §3 | the Two-Track gate ladder, MREG → A-R1 → A-R2/R3 → A-R4 → B-0 → B-1 |
| playbook §4 | the four items that **invert** for a Track A containment audit |
| playbook §5, §6 | scope notes fencing the formal templates to Track B |
| playbook §5a | this gate's own template |
| playbook §6 | the ratio checkbox names which derivation supplies it |
| playbook §7 | a track field |
| playbook §8 | the four `M15_SINGLE_RUN_EVIDENCE_*` statuses fenced to Track B, plus `..._VOID_REGISTRATION_NOT_LATE` |
| playbook §9 | merge-checklist additions |
| policy §2a | **a Track A run is Red**; R1/R3/R4 are three separate Red gates |
| prereg §13a | the clause-by-clause Two-Track amendment table |

## 13. Independent review

Three separated roles were run against the source and diff, without the other
roles' conclusions: **execution containment / test safety**, **governance and
authorisation sequencing**, and **adversarial bypass**. Their findings and the
post-fix re-verification are recorded in the pull request body.

## 14. Non-authorisation statement

Nothing in this document or in `scripts/m15_track_a/` authorises a real-data
read, a derivation, training, evaluation, a run, a broker connection, or a
deployment. No real data was read in producing it. No training, evaluation or
fitting was performed. `PRODUCTION_READINESS_NOT_CLAIMED`;
`NO_EXECUTION_PERFORMED`.
