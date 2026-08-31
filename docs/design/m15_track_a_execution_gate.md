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
stopped there: `CONTRACT_PERMISSION_IS_NOT_EXECUTION_AUTHORISATION` (§8.12 header and §8.12.1).

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
| 1 | Two-Track contract approval and merge (PR #451) | ✅ **taken** — merged `4f45515` (2026-08-30); the note below is retained as the state at this document's own drafting | ~~**not taken**~~ — this branch is stacked on `2cdb687`, PR #451's unmerged head, so §8.11–§8.13 are `…NOT_YET_CITABLE_AS_AUTHORITY` and every propagated statement here is provisional (§12) |
| 2 | This execution gate reviewed, approved, merged | this PR |
| 3 | Explicit human + ChatGPT **real-data read authorisation** | not requested |
| 4 | Track A R1 execution | not performed |

Steps 2 and 3 are distinct on purpose. A merged execution gate says the
apparatus is sound; only step 3 says a read may happen, and it names the span
it covers.

**On "the execution gate authorises R1 only".** §8.12.10's token says the gate
reaches **R1 and no further** — R3 and R4 need their own Red approvals. It is a
statement of *scope*, not of *sufficiency*: reaching a gate is not passing
through it, and the read still needs the explicit grant of step 3. Wherever
this programme's documents carry the "authorises R1 only" phrasing, that is the
reading, and the checklist at playbook §5a keeps the grant **outside** its items
so that a fully-ticked gate cannot be mistaken for a granted read.

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

Local file reads are **not** blocked wholesale: Track A exists to perform one.
Which files it may touch is decided by the classifier, which uses `realpath`
**and** — when the string test says "outside" — filesystem identity. On this
machine `data/`, `FX-AI-~1\data`, `\\localhost\C$\…\data`, `DATA/` and a
junction all name the same directory and report the same `(st_dev, st_ino)`,
and a string test caught only two of them.

Two forms of Win32 namespace path **reduce**: `\\?\UNC\…` and `\\?\X:\…`.
Anything else — a volume-GUID path, a device path — is **refused rather than
reduced**. An earlier drafting stripped the prefix unconditionally, which turned
`\\?\Volume{GUID}\…\data\x` into a *relative* path; `realpath` anchored it
under the working directory, the cheap string test then **succeeded** on that
wrong path, and the identity walk — which only runs when the string test fails —
never ran. The read landed.

### The guarantee is bounded, and the bound is named

`sys.addaudithook` is route-independent **for anything that goes through
CPython's own I/O**. It is not route-independent for a third-party **C
extension** that calls the OS directly: `pyarrow.OSFile` and
`pyarrow.memory_map` read `data/` and wrote into `docs/` with every guard
installed, because pyarrow's file layer is C++ and raises no Python audit
event. This repository already depends on it —
`scripts/evaluate_ml_baseline.py` calls `pq.read_table`, and the feature store
is parquet.

**No in-process mechanism closes that class.** A C extension calling
`CreateFileW` or `open(2)` is below anything Python can hook; the complete
answers are all outside the process — a sandbox, a container, a filesystem ACL.
What `isolation.NATIVE_REFUSED_TARGETS` does instead is name the native readers
this repository depends on and **refuse them outright** while the guards are
armed.

**Refuse, not classify** — and the difference is the whole of a round. The
first version of this guard wrapped each target and worked out generically which
argument was the path and whether the call was a read or a write. A
re-verification took it apart four ways at once, because fifteen heterogeneous
APIs do not share a signature: `pa.output_stream` has no `mode`, so the wrapper
called it a read and it **wrote into `docs/`, into `src/`, and truncated the
append-only ledger**; `pq.write_table`'s first argument is a Table, so every
call was refused *including outside the repository* while the keyword form was
not checked at all; the read/write decision fell back to whether the destination
path happened to contain the letter `x`; and `pa.fs.LocalFileSystem` is a class,
so wrapping the constructor checked nothing and replacing the class broke
`isinstance` process-wide. A refusal needs none of that. R1 has no read body, so
it has nothing to parse and no reason to call any of them.

Two consequences a reviewer should hold onto:

- **The bound is the list, and it is now true of the list.** Where a target
  cannot be replaced — `sqlite3.Connection` and pyarrow's filesystem class are
  immutable extension types — it is either guarded another way (a refusing
  subclass, a connection factory) or **disclosed** by
  `isolation.unpatchable_native_targets()`. An entry that is listed but not
  actually refused is worse than a missing one, because this paragraph is what
  tells you to rely on it.
- **A native reader nobody listed is a hole, and the containment audit cannot
  find it.** `pyarrow.dataset`, `pyarrow.orc`, `lightgbm.Booster` and a raw
  `ctypes` call were all reached in review before they were added; the next one
  will be too. Read the apparatus as "an accidental crossing fails loudly, and a
  deliberate one has to appear in a diff" — not as a sandbox.

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

## 10. The turnover two-axis collision — dissolved for execution, **referred** for decision

### 10.1 The collision

§8.7.5 locked two unregistered axes of the turnover budget **pre-observation**,
naming their permissive arms:

- **Axis 1 — mean versus per-day cap.** `scripts/ml_step4/metrics.py:120-124`
  computes `n_trades / n_trading_days` — a **mean**; prereg §9 says "≤ 40
  trades/day portfolio-wide", enforced as `turnover <=
  max_turnover_trades_per_day` at `scripts/ml_step4/acceptance.py:200-203`
  against the frozen `40.0` at `scripts/ml_step4/contract.py:134`. Since
  `max ≥ mean`, the mean is the permissive arm.
- **Axis 2 — the denominator.** §8.6.6 records that the candidates are **four,
  not two**: active dates (the implementation — `metrics.py:227` computes
  `n_days = len({t.day for t in trades})` and hands it to `turnover` at `:236`
  — and the *smallest* denominator, hence the strictest reading); the
  registered R-5 denominator `distinct_utc_calendar_dates_in_holdout`, which
  `compute_all` already receives and already uses for `daily_coverage` in the
  same call; every UTC calendar date in the evaluated span; and the dates an
  approved calendar authority recognises. §8.12.13 C-20 records that the
  calendar reading widens the gate-4 corridor by about **42%** — "a loosening
  Ruling 10 forbids".

§8.13.13 then recorded the deadlock:
`THE_TURNOVER_AXES_ARE_FIXABLE_NEITHER_BEFORE_NOR_AFTER_TRACK_A_AND_THE_COLLISION_IS_UNRULED`
— the axes cannot be fixed before Track A, and the pre-observation lock cannot
be satisfied once Track A computes a single turnover figure.

### 10.2 What this gate rules, and what it deliberately does not

**`A_TRACK_A_TURNOVER_FIGURE_IS_REPORTED_ON_EVERY_CANDIDATE_AXIS_AND_IS_NEVER_COMPARED_TO_THE_FROZEN_CEILING`.**

A Track A run that computes turnover reports it on **every** candidate — both
statistics on axis 1, all four denominators on axis 2 — side by side, and
compares none of them to prereg §9's ceiling. No axis is selected.

**No axis selection is taken here.** The selection was referred —
`THE_TURNOVER_AXIS_SELECTION_IS_REFERRED_TO_HUMAN_CHATGPT_AT_TRACK_B_CANDIDATE_PRE_REGISTRATION`
— and §10.4 records the analysis the ruling body needed.

**The referral has since been answered.** The human + ChatGPT Gate-decision
round of **2026-08-30** ruled the axes, in the pre-registration where C-15 and
C-20 place them — `…preregistration_design.md` **§9a**:
**`TURNOVER_CEILING_RULED_PER_DAY_CAP_ON_THE_ENTRY_DATE_MAXIMUM`** and
**`TURNOVER_DENOMINATOR_AXIS_IS_NON_BINDING_UNDER_THE_CAP_AND_STAYS_UNREGISTERED`**.
Axis A is fixed at the **strict** arm, so Ruling 10 is satisfied by
construction; Axis B is not ruled, because a date with no trades cannot raise a
maximum and all four §8.6.6 candidates then agree. §10.2's reporting obligation
survives the ruling and is **extended to both tracks** by §9a.

### 10.3 Why the deadlock dissolves without a selection

The deadlock is only a deadlock for a rule that must **compare** a Track A
figure to the frozen ceiling. Nothing requires that:

1. **A Track A figure cannot discharge an acceptance row anyway.** §8.11.2(1)
   makes every Track A output `NON_DECISION_BEARING_EXPLORATORY_ONLY`, and
   §8.13's carry table puts a turnover figure in the row that "may **never**"
   cross to Track B. A number that may not reach the acceptance test does not
   need the acceptance test's convention fixed before it can be computed.
2. **Reporting every candidate removes the choice, rather than making it.** The
   thing §8.7.5's lock protects against is an experimenter selecting the
   convention that flatters the result after seeing it. If all of them are
   recorded, side by side, on every run, there is nothing to select and nothing
   an observation could inform.
3. **Nothing frozen moves.** The ceiling, the numerator, §8.7.5's entry-date
   attribution and Q10(iii) are all untouched, and Ruling 10's prohibition on
   loosening is not engaged, because no comparison is performed at all.
4. **These are start conditions the gate can supply.** §8.13.5 excludes
   *strategy parameters* from the Track A start conditions. "Record every
   candidate and compare none" is a reporting obligation on the run, not a
   parameter of the strategy, so the gate may impose it.

### 10.4 The analysis the referred selection will need — recorded now, before any data

An earlier drafting of this section **did** rule the axes, at "mean over active
days", and defended the choice as a pre-observation freeze of the incumbent
implementation. The independent governance review defeated that defence, and
the defeats are recorded here rather than discarded, because a ruling body will
meet the same arguments:

- **The pre-observation defence is foreclosed for these two surfaces
  specifically.** §8.10.3's "known favourable directions" table names
  **S-62 / S-63 — turnover as a mean over a calendar denominator** as
  analytically favourable *without seeing any data*, and §8.4.11's A-ω-5
  standard says a pre-data freeze alone does not protect such an arm. C-13
  restates it: `SEQUENCING_IS_NOT_THE_OPERATIVE_CONTROL_ON_AN_ANALYTICALLY_KNOWABLE_DIRECTION`.
  So "no observation exists yet" is not an argument for taking the mean.
- **§8.7.5 names permissive arms; it does not prefer them.** Its words are that
  the permissive arms are named "so that leaving them open is not mistaken for
  leaving them neutral" — a **disclosure of the risk direction**. Reading a
  disclosure as a licence is the invalid-inference shape §8.12.13 withdrew.
- **"No threshold moves" is false on axis 1.** §8.7.5 says settling
  mean-versus-cap "would change the ceiling's **meaning**". A strategy averaging
  20 trades/day with one 60-trade day passes under the mean and fails under the
  cap. The numeral is stable; the criterion is not.
- **The incumbent is not the baseline Ruling 10 uses**, and it is not committed
  for this family: Ruling 10 baselines on the frozen prereg §9 row, and
  `scripts/ml_step4/metrics.py` is **M1-lineage**, which prereg §11 admits only
  "reusable after audit/wrapping". There is no committed M15 turnover
  implementation to be incumbent.
- **The axes are already classified.** C-15/C-20 place them as **terms in an
  acceptance test**, outside arm 3, and leave the survival of §8.7.5's lock
  expressly unruled. This gate does not displace that classification.
- **§8.13.13 contains both limbs of the deadlock.** It excludes strategy
  parameters from the start conditions *and* adds the turnover axes to §8.13.5's
  list. The contradiction is inherited, not resolved here, and it is one of the
  things the referral has to settle.

**Directional note for the ruling body, not a decision:** on axis 2 the
active-date denominator is the strictest of the four and is the only one that
cannot widen the corridor. CLAUDE.md's stricter-reading rule points at it. That
observation is recorded as an input; taking it is a human + ChatGPT act.

### 10.5 What §10 does **not** do

- It does **not** discharge S-62 or S-63. They remain live Track B surfaces.
- It does **not** settle the gate-4 corridor question.
- It does **not** touch the turnover numerator, §8.7.5's entry-date attribution,
  or Q10(iii) — which §8.13's review confirmed does not move turnover at all.
- It carries **no approval identifier**, and under §8.12.13 C-9 a section
  without one may not be cited as authority. §10.2 is an execution-gate
  reporting obligation, which the gate may impose; it is not a ruling on a
  frozen acceptance row, and it must not be read as one.

## 11. The containment audit and what it actually checks

`scripts/m15_track_a/containment.py` is the executable form of playbook §4's
Track A variant. It runs **twelve** checks — all twelve are named below, in two
groups.

**Six behavioural probes — these carry the verdict.** Each arms the guards and
then actually attempts the forbidden thing, requiring a refusal:

| Probe | Attempts |
| --- | --- |
| `write_containment_enforced` | a write into `docs/` |
| `market_data_read_refused` | a read under `data/` outside the gated window |
| `network` | a non-loopback connect and a non-loopback name lookup |
| `subprocess` | launching a process |
| `database` | a remote SQLAlchemy engine |
| `read_route_gated` | the declared route with no grant |

Every probe is chosen so a *failure of the guard* is still harmless: the read
probe names a file that does not exist, so an absent hook yields
`FileNotFoundError`, never a real read.

**Six source checks — advisory, and labelled so.** `broker_live_demo`,
`read_body_declared`, `single_read_route`, `authorization_not_ambient`,
`write_root`, `derivation_route`.

`broker_live_demo` sat in the probe table for two rounds and does not belong
there: it iterates `FORBIDDEN_OPERATIONS` and calls `assert_operation_allowed`,
which raises **iff** the name is in that same dict. It cannot fail and it
attempts nothing. The split is now pinned in code as
`containment.BEHAVIOURAL_CHECKS` / `SOURCE_CHECKS`, and a test compares both
against this section, so the document, the code and the PR body cannot drift
apart again — the previous drift test only checked that all twelve names
appeared somewhere. The module roster is **enumerated from the directory**, not
hand-written, so a new module is scanned by existing.

`read_body_declared` reads the route's own AST. It is **not** a behavioural
probe — an earlier drafting's docstring claimed it "drives the route to the end
of its gate sequence", which it never did.

**Until R1's body landed, this check asked whether the body was *absent*, and
that answer licensed a claim that nothing could be read. That question is
gone.** R1 has a body now. Pretending otherwise would be the overclaiming this
document spent six rounds retiring, so the check asks the question that still
has a useful answer: **is the body the one route that was declared, reading only
the one declared source?** Seven conditions:

1. exactly **one** `read_historical`, so a second live definition cannot hide
   behind the first;
2. **no module-level rebinding** of a permitted call name;
3. no default argument that is a call or a subscript — those run at import time,
   before any gate exists;
4. every call is on the declared list, and **no call whose callee has no name**
   (`_T["slurp"](path)` had a `Subscript` callee, so there was nothing to
   compare and the check silently skipped it);
5. every **node type** is on the declared list, and no decorator;
6. the body opens **exactly one** thing — a path from `source_path_for` — and
   does so **inside** `gated_read_window`;
7. and **the module around it** contains no other reader at all.

Condition 6 is what "one route, no fallback" means once a route exists.

**Condition 7 exists because a review role defeated 1–6.** They read one
*function*, while listing `read_route` in `_PERMITTED_FILE_OPENERS` exempts the
whole *module* from the reader-name sweep — which made this module's four
helpers the only code in the package that could open a file with no source check
at all. The role added four lines to `_row_from_source`, read an undeclared
market-data file from them, and the audit returned `PASS` on every check. Its
first attempt used `globals()` and `_indirection_findings` caught it; the second
used no reflection and nothing did. So the sweep the exemption removes is put
back, with exactly one pinned exception: the single `open` the body performs,
identified by the exact finding string it produces rather than by its line
number, so nothing else written on that line is swallowed with it.

**And one defence moved rather than disappeared.** `ast.Subscript` had to become
a permitted node type, because the body does `row[key]`. A bare subscript was
previously a finding, and that is what caught `SLURP["path"]` — an object whose
`__getitem__` reads. So the rule is now narrower and equivalent: a subscript on
a **local** is a dict lookup and is fine; a subscript on a **module-level name**
is a capability and is a finding. The first two alone were
defeated end to end: a body that read a file with `numpy.memmap` and stored the
bytes in a module global has no `return`, ends in the raise, and used a name no
reader list contained. An allowlist over the calls does not depend on having
anticipated the reader.

`declared_gate_sequence_matches_at_this_head` is set only when **the audit as
a whole passed**, and `read_body_declared` passed, and the behavioural
`market_data_read_refused` probe passed. An earlier drafting computed it
independently of the verdict, so a `BREACHED` report still carried it as `True`
and the field could be quoted on its own.

**It has never meant "nothing can be read", and since R1's body landed it does
not even mean "nothing is read".** It means: the reading this head performs is
the one route that was declared, and an *ungated* market-data read is still
refused.

**What earlier draftings claimed and did not do.** The first version of this
section listed eight checks including "no forbidden import reaches the package"
and "no route reaches a forward-epoch span". Neither was in the audit: the
import pin lives in `tests/m15_gate3a/test_wp5_reader_freedom.py`, and the
forward-epoch limb lives in `read_route.assert_span_admissible`. That version
also answered "is the route gated?" by scanning source text for the gates'
names — which a **docstring** listing those names satisfied. The second version
said "twelve checks" and then named eleven, omitting `broker_live_demo`, and
put `read_body_absent` in the probe table; the code's own section banner said
eight probes while this document said six and the PR body said seven. All are
corrected — **six and six** — and a test compares both lists against
`containment.BEHAVIOURAL_CHECKS` / `SOURCE_CHECKS`.

The count then drifted twice more after that sentence was first written: this
section said six while its own summary line still said "seven and five", and
the module banner said seven and five again. Three artefacts, three numbers,
twice over. They are one number now, and the test reads the split out of the
section rather than only checking that the twelve names appear somewhere in it.
The false descriptions are recorded rather than quietly replaced.

### The verdict says only what the audit did

`TRACK_A_EXECUTION_CONTAINMENT_PROBES_PASSED_BOUNDED_ASSURANCE` /
`TRACK_A_EXECUTION_CONTAINMENT_PROBE_FAILED`.

It used to read `…_VERIFIED_NO_UNGATED_ROUTE`, and **that phrasing is the defect
this PR kept reproducing in new places: the artefact claimed more than the
mechanism delivers.** Six independent audit contexts each found a route the
audit had certified against, and each time the fix went to the specific route —
never to the claim. No in-process audit can establish "no ungated route": a C
extension, a rewritten source file, a reflected reader and a pre-seeded hardlink
are all outside what it can see, and three of those were demonstrated end to end
*against a report that said VERIFIED*.

So every report now carries `bounds`, a list of what it does **not** establish,
and the field formerly called `no_market_data_read` is
`declared_gate_sequence_matches_at_this_head` — which is what it checks. The
report also separates `behavioural_checks` from `source_checks_advisory`, so a
consumer can tell which half carries the verdict.

It is an **execution-containment** check, not a hostile-input audit, and it does
not replace the gate-6 source-contamination audit Track B still needs.

## 12. Governance propagation — done, and not done

**`GOVERNANCE_PROPAGATION_COMPLETE` — on this PR's merge, not before**, and
`GOVERNANCE_PROPAGATION_IMPLEMENTATION_PENDING` governs until then, exactly as
C-10 says.

This is the third spelling PR #455 has tried, and the first two were both wrong
in the way C-10 anticipates. The first wrote the discharges into a *different*
file. The second minted a token — `…_AT_THIS_HEAD` — that is not in the contract
vocabulary and scoped it to a **branch** head, when C-10 requires "a named
**master** SHA". Master is `d694377`; this PR is open; so the predicate is not
true yet, and saying so is the only accurate thing to say.

What *is* true is that every item is now discharged **in the file it names**, so
the predicate becomes true on merge without further work. The difference between
the second and third attempts matters:

The **first** attempt wrote the discharge for P-10 and P-13 into *this* file
while the files those items name were untouched. Two review roles refuted it
item by item, and they were right: "a predicate on **named files**, not a
self-assessment" refuses exactly that, and the withdrawn revision said so in its
own sentence while doing it.

The discharge is now **in the named files**:

* **P-10** — `docs/design/m15_minimum_research_gate.md` §8.13's approval line
  carries PR #451's approved head `2cdb687` and merge commit `4f45515`, and
  `THE_TWO_TRACK_SECTIONS_ARE_RULED_AND_CITABLE_AS_AUTHORITY_FROM_MERGE_4F45515`
  supersedes the pending token wherever it stood;
* **P-13** — `docs/design/m15_first_cost_hurdle_aware_design_audit_fable5.md`
  §1a carries an approval identifier (PR #455) and now **rules** the scope
  reading, with `P_13_DISCHARGED_AT_PR_455`. Its T-3 row is corrected in the
  same edit, because D-3 found that row's classification inverted prereg §6's
  timing;
* **P-5** — the playbook's §1 gate table, rebuilt in this PR.

`grep` for the pending tokens in the MRG now returns only the lines that record
them as *superseded*, and **all eight** RULED sections carry C-9's identifier —
not one section declaring it on the others' behalf, which is what the second
attempt did and what C-10 refuses.

§8.12.13 C-10 makes completeness "a predicate on named files, not a
self-assessment", holding **only on a named master SHA**. When this section was
written the branch was not on master and PR #451 was unmerged, so the predicate
was false whatever the table said. Both conditions are gone: #451 merged as
`4f45515`, #452 as `37edbb0`, #453 as `6b75aab`, #454 as `d694377`, and the three
outstanding items below are discharged by PR #455.

**The predicate was false on 2026-08-31 and nobody had checked.** An R1 execution
command arrived, and this row — CLAUDE.md's *first* Track A precondition, ahead
of the execution gate and the derivation route — was one of six things that
turned out not to hold. That is what a predicate on named files is for, and it
only works if someone evaluates it. The table below is now the evaluation.

| Item | Target | State at this head |
| --- | --- | --- |
| P-1 | `CLAUDE.md` | done |
| P-2 | playbook §2 | done |
| P-3 | playbook §5/§6 + a Track A checklist | done (§5a) |
| P-4 | playbook §7/§9 track field | done |
| **P-5** | playbook **§1 gate table** + §3 ladder | **done at PR #455** — §3 was already done; the §1 table stopped at PR #444 and now carries #449, #450, #451, #452, #453, #454, the refused execution command and #455, reconciled against `d694377`. This one **is** a change to the named file |
| P-6 | policy | done (§2a) |
| **P-7** | prereg §3.1/§4/§10/§11/§13/§14/§16 | **DISCHARGED** — §13a **RULED, IN FORCE** by the human + ChatGPT round of 2026-08-30. The first drafting covered §3.1/§4/§11/§16 only and called §10 and §14 "unchanged", which would have recorded P-7 complete while three clauses still forbade the read; a contract-consistency review caught that before the ruling was taken, and the table now carries §10 item 3, §13 and §14 |
| **P-8** | `docs/prompts/*` | done |
| P-9 | playbook §8 | done |
| **P-10** | approval identifiers on **every** RULED MRG section | **done at PR #455, on merge.** C-9 wants a PR number, an approved head SHA and a date on each RULED section, and P-10 applies it to the sections already written. §8.11, §8.12 and §8.13 now each carry the line (PR #451 · `2cdb687` · `4f45515`), and the remaining RULED sections carry theirs. Two earlier revisions got this wrong in different ways — one wrote the discharge into *this* file, the next wrote it into §8.13 only and declared it applied to the others at a distance |
| P-11 | playbook §4 | done |
| P-12 | prereg §7/§8 | done — and **now in force**, since its text is §13a's, which was `NOT IN FORCE` when this row first read "done" |
| **P-13** | gate-4 audit T-1/T-2/T-6 | **done at PR #455, on merge.** §1a now carries C-9's identifier (PR #455 · head recorded at merge · 2026-08-31) and **rules** the scope reading. Its T-3 row is narrowed rather than relaxed: the measurement is sited at the declared candidate under its frozen cost table, and **a Track A measurement still fires the block**. An earlier revision of PR #455 wrote that Track A 'neither fires the block', which removed a stop trigger; a review role caught it and it is withdrawn |
| P-14 | playbook §3 + §6 ratio checkbox | done |
| P-15 | prereg §6 | done — same dependency on §13a being in force, and same correction |

**The Two-Track authority is citable; the propagation is not complete.** Those
are different claims and an earlier revision of this section ran them together.
§8.12.13 C-9 and the packet's own approval line carried
`THE_TWO_TRACK_SECTIONS_ARE_RULED_AS_RECORDED_AND_NOT_YET_CITABLE_AS_AUTHORITY`
and `APPROVAL_IDENTIFIER_PENDING_UNTIL_MERGE` with §8.11, §8.12 and §8.13 until
PR #451 was approved and merged. It was, as `4f45515` on 2026-08-30. Every
propagated statement in this document rests on authority that is cited by a
merge commit rather than by a promise.

**What completeness would buy, when it is reached.** It discharges CLAUDE.md's
Track A precondition 1 and nothing else. Precondition 2 (the execution gate passed on a
named head) and precondition 3 (the derivation route decided in a diff) are
separate, and **none of the three is a read authorisation**. Two explicit human +
ChatGPT grants — one to read, one to derive — remain, and this document has said
from its first draft that a contract permission is not an execution
authorisation.

## 13. Independent review of this head

Three separated roles were dispatched against head `f0a5bc9`, each given the
source, the diff and the contract and **not** the other roles' conclusions:
execution containment / test safety, governance and authorisation sequencing,
and adversarial bypass. All three returned. Two further **fresh** audit
contexts then re-verified, against `474e273` and against `3b7d3de`. Their
findings and the fixes are recorded in the pull request body.

**The head this document describes is the one the PR reports as final.** It is
not `f0a5bc9`, `474e273` or `3b7d3de` — each of those was superseded by the
round its own re-verification produced. A reviewer should read the PR body for
the head, and should treat this sentence as the only claim this section makes
about which head is current.

**An earlier drafting of this section asserted, in the past tense, that the
roles had run and that a post-fix re-verification had been recorded — at a head
that contained the sentence and predated the roles' reports.** That is a
forward reference asserted as completed, the shape §12.15 records against this
programme and the governance forbids outright. It was caught by one of the
roles it described. The correction is recorded here rather than made silently.

**What the round found, in summary** — three roles, converging independently on
five of the same defects:

- The isolation guards were **route-dependent**: installing the database guard
  first left every socket primitive unpatched while `is_installed()` answered
  True, and `_socket`, `asyncio`, `subprocess`, a pre-bound `create_engine` and
  `sendmsg` were never covered at all. Replaced by a `sys.addaudithook` as the
  primary control.
- The scratch root was **advisory**: a plain `open(…, "w")` wrote anywhere. The
  audit hook now confines writes process-wide.
- There was **no single read route at process level** — `data/` was open to any
  caller that simply declined to use the route. The hook now refuses reads under
  `data/` outside the gated window.
- The containment audit **certified on structure**: a gateless route whose
  docstring named the gates passed, and a module absent from the hand-written
  roster was never scanned.
- Six shapes of **forged grant** passed `require_authorization`, the approved
  head SHA was never compared to anything, and `N = 1` could be spent four times
  by four processes.
- And the governance half asserted things the source did not support — §11's
  check list, §13 above, and a turnover ruling whose central defence §8.10.3 had
  already foreclosed for those exact two surfaces (§10.4).

### 13.1 The re-verification, and what the *fixes* broke

The fourth context was asked specifically to hunt for defects created by the
round-one fixes, because four of the last five rounds in this programme
produced one. It found **four**, all in the audit-hook rewrite, and all of them
the same shape: *moving to a stronger mechanism does not close a class of hole,
because the new mechanism has its own surface.*

| What the rewrite did | What it missed |
| --- | --- |
| handled the `open` audit event | **every other filesystem event** — `os.rename`, `os.remove`, `os.mkdir`, `os.rmdir`, `os.truncate`, `os.link`, `os.symlink`, `os.chmod`. `os.rename` of a candle file out of the repository, then an ordinary read, was a **complete escape** |
| read the `open` event's *mode* | for `os.open` CPython passes `mode=None` and puts the flags in the **third** argument, so `Path.touch`, `tempfile.mkstemp` and an `O_TRUNC` on an append-only ledger were all classified as reads |
| matched `artifacts/oanda_archive` by prefix | the directory that exists is `artifacts/oanda_archive_2026-05-31`, and `startswith("artifacts/oanda_archive/")` is False — the **whole committed 10-year archive** was readable. Case-flipped and `\\?\` spellings of `data/` were open too |
| imported `scratch` lazily, inside the hook | the import's own `open` calls re-entered the hook against a half-initialised module, so `install_all()` **crashed** in any process that had not already imported `scratch`. Every test file imports it at module top, so the suite never saw it — only a real caller did |

It also found that `tuple.__len__` had been left unpinned beside the pinned
`tuple.__getitem__`; that the host was read through `str(...)`, which a
subclass overrides; that the guard's own root-resolution failure meant
*permitted*; that a non-`IsolationError` escaping the hook broke unrelated I/O;
that the gated read window was process-wide rather than per-thread; that
deleting a claim file silently reset `N = 1` while the ledger still recorded
the spend; and that the "atomic on POSIX and Windows" claim for `O_APPEND` was
false — the Windows CRT emulates it as seek-then-write, and four processes
still lost 5–13% of their lines.

All are fixed and each carries a test that fails at `474e273`. The append
ledger is now taken under an explicit `O_CREAT | O_EXCL` lock, measured at
120/120 lines over six four-process rounds; the earlier scheme measured
105–113. Two further Windows facts were found while fixing it and are recorded
in the source: a lock whose delete is still pending reports
`ERROR_ACCESS_DENIED`, not `ERROR_FILE_EXISTS`, so the retry has to catch
`PermissionError` too; and a path check on a file another process is unlinking
resolves through `\$Extend\$Deleted` and fails, so the lock path is derived
from the already-checked ledger path rather than re-checked.

**The suite was green at every one of these heads.** That is now five rounds in
this programme at which a green suite predicted conformance and an independent
context found blockers.

### 13.2 The second re-verification, and what *those* fixes broke

A second fresh context audited `3b7d3de` and found the round-two fixes had
created two more blockers and left five path bypasses open. The through-line is
one sentence: **a path decision made on a string is a decision about a
spelling, not about a file.** Measured on this machine, `data/`,
`FX-AI-~1\data`, `\\localhost\C$\…\data`, `\\.\C:\…\data`, `DATA/` and a
junction all name the same directory, and only two of the six were caught —
because the read path used `abspath` while only the write path used `realpath`.

| Defect | Fix |
| --- | --- |
| **Created by the fix:** an `int` file descriptor was "unclassifiable", and round two had made unclassifiable fatal. CPython writes every `.pyc` through `_io.FileIO(fd, "wb")`, so a guarded run **died on its first uncached import** — and `containment.audit()` died with it. The suite passed only because `__pycache__` was warm | an `int` is permitted; the `open` that produced it was already checked |
| **Created by the fix:** `read_body_absent`'s "no `return`, terminal `raise`" test was satisfied by a body reading through `numpy.memmap` into a module global, and `no_market_data_read` was computed independently of the verdict — so a `BREACHED` report still carried `True` | an allowlist over the calls the route may make, plus gating the field on the overall verdict |
| Five read spellings — 8.3 short names, `\\localhost\C$`, `\\?\UNC\`, `\\.\`, and a junction — reached the filesystem | `realpath` for every decision, plus a **filesystem-identity** fallback: `(st_dev, st_ino)` is the same for all of them |
| The same UNC spelling bypassed **write** containment, including the `os.rename`-a-candle-file escape §13.1 records as closed. An `os.rmdir` reached a real repository directory | the same identity fallback |
| The append-only ledger could be zeroed by six filename spellings (trailing dot, trailing space, `::$DATA`, two case variants, and `os.open` with `O_TRUNC`) | exact `(st_dev, st_ino)` identity against the ledgers that exist, plus a normalised, case-folded, stream-stripped name for one that does not |
| A leaked lock was a permanent denial of service on every ledger — and the write-ahead declaration is the first thing it halts | a lock older than `APPEND_LOCK_STALE_SECONDS` is broken |
| The read window leaked to sibling coroutines | pinned to the thread **and task** that opened it. A bare `ContextVar` is not enough: a `Task` copies the context at creation, so a task spawned inside the window inherits it |
| The alias sweep caught one binding form of seven | every *reference* to a reader name, plus `getattr` with a constant |
| `identity` defaulted to `None`, silently skipping the head-SHA comparison | required |

### 13.3 The third re-verification — and the one finding that changed the claim

A third fresh context audited the round-three head. It found two more blockers
created by that round, and one that goes to the apparatus's central claim.

**The claim itself was too strong.** `sys.addaudithook` is route-independent
for CPython's own I/O and **not** for a third-party C extension.
`pyarrow.OSFile` and `pyarrow.memory_map` read `data/` and wrote into `docs/`
with every guard installed, and this repository already calls `pq.read_table`.
No in-process mechanism closes that class. The response is in two parts, and
the second matters as much as the first: the native readers this repository
depends on are named in `isolation.NATIVE_REFUSED_TARGETS` and refused at their
Python entry points, **and §6 now states the bound** — the guarantee is exactly
that list, the audit cannot detect a native reader nobody listed, and only
something outside the process closes the class.

**Created by the round-three fix:**

| Defect | Fix |
| --- | --- |
| The cache exemption ran **before** the market-data test, and round three had routed reads through the classifier — so `data/__pycache__/candles.jsonl` was *refused* at the previous head and *readable* at the next. `.git/__pycache__/…` was writable for the same reason, despite `.git` having been taken off the cache list | protected trees are tested first; the exemption requires the **parent** directory to be a cache; and a set of roots no exemption reaches |
| `_inside_protected` returned `None` past 64 levels, and `None` meant "outside, therefore permitted" — a deep path spelled through the administrative share read real bytes | the walk fails **closed**, at 256 |

**Also closed:** `_identity_map`'s `lru_cache` went stale when an archive
directory appeared after the first call — the enumeration it cached was never
needed, and the walk now returns the components below the repository root so
the ordinary name tests do the work; the append-only ledger was destroyable by
`os.ftruncate` on an appending descriptor, `os.truncate`, `unlink`, `rename`,
`replace` and a native writer, because the check was wired into the `open`
event alone; a reused `gated_read_window` instance made `__exit__` reset an
already-used `Token`, which **raised** and left the window open for the rest of
the process; `os.open(..., dir_fd=…)` bypasses the classifier because the audit
event does not carry `dir_fd`, and CI is `ubuntu-latest` where `dir_fd` exists;
consumed-holdout evidence under `artifacts/ml_step4/` and
`artifacts/gate_p1_pr_b/` was readable, which is the same leakage in a different
costume; and the ledger's own bytes differed by platform, because `os.open`
defaults to text mode on Windows and turned every `\n` into CRLF.

**Left open, and named rather than fixed:** a **hardlink** pre-seeded into the
working tree defeats path-based containment in both directions, and cannot be
detected by any path test — the ledger's `(st_dev, st_ino)` check catches it
there, but a general one would need to enumerate the protected trees. It
requires an attacker who can already write the working tree, which is a
different threat model from the one this gate addresses, and it is recorded
here rather than left implicit.

### 13.4 The fourth re-verification — the fix was the largest hole in the head

A fourth fresh context audited the round-four head, and the finding is the
sharpest instance of the pattern in this document: **the native-reader guard
added to close the C-extension hole was itself the biggest opening in the
apparatus.**

It was a generic wrapper that worked out, for each of fifteen APIs, which
argument was the path and whether the call was a read or a write. Heterogeneous
APIs do not share a signature, so it got all of that wrong at once:

| What the wrapper assumed | What happened |
| --- | --- |
| there is a `mode` argument | `pa.output_stream` has none, so it was classified a *read* — and a read was refused only for market data. It **wrote into `docs/` and `src/`, and truncated the append-only ledger**: a write route that had not existed before the guard was added |
| `args[0]` is the path | `pq.write_table`'s first argument is a Table. Every call was refused **including outside the repository** — the repository's own `build_feature_store.py` could not run — while `pq.write_table(table=…, where=…)` was not checked at all |
| a mode is a `str` in `args[1]` | for `pq.write_table(t, path)` the read/write decision was made by asking whether the **destination path** contained `w`, `a`, `x` or `+` |
| a listed target is a function | `pa.fs.LocalFileSystem` is a class. Wrapping the constructor checked nothing, the instance methods stayed original — and replacing the class with a function made `isinstance` raise **process-wide** |

The response is a design change, not another patch: **refuse, do not classify.**
Every entry in `NATIVE_REFUSED_TARGETS` raises while the guards are armed, with
no argument inspected. That costs the use of pyarrow inside a Track A run, which
R1 does not need because it has no read body; an implementing PR that needs one
adds a narrow wrapper *with that API's signature in front of it*. Where the
target is an immutable extension type, it is guarded by a refusing **subclass**
(`LocalFileSystem`) or through a factory (`sqlite3`), and anything that still
cannot be replaced is disclosed by `unpatchable_native_targets()` — because an
entry that is listed but not refused is worse than a missing one, and §6 is what
tells a reviewer to rely on the list.

**Also created by round four and closed here:** the cache exemption's
`_NEVER_EXEMPT_ROOTS` contained `src`, so writing a `src/**/__pycache__/*.pyc`
refused and **a cold import of any `src/` module died** — the round-three defect,
re-created for one subtree, and the regression test written to cover it set
`PYTHONPYCACHEPREFIX` outside the repository, so it certified a configuration a
real run does not have. The exemption now keys on the **file** (`.pyc`, or the
`.pyc.<n>` temporary CPython renames) rather than on the directory, which fixes
both directions at once.

**Also closed:** `\?\Volume{GUID}\…` was reduced to a *relative* path, so the
cheap string test succeeded on a wrong path and the identity walk never ran —
only two namespace forms reduce now, and the rest are refused; `sqlite3`'s
`ATTACH` created a file inside `data/` with no audit event; `os.rename` of the
**scratch root itself** took the whole governance-record tree out of the
repository, because the source classified as `scratch` and the destination as
`outside`; the read-route check was defeated by a `Subscript` that is not a
callee, by a bare-`Name` decorator and by an f-string format spec, and is now an
allowlist over **node types** rather than over call names; and the module
exemption in the structural sweep skipped the reflection check too, so a reader
assembled from `builtins.__dict__["open"]` inside a permitted opener went
unscanned.

**Five rounds, and each round's fix created the next round's blockers.** That is
the strongest single argument in this document for why an execution gate needs
independent re-verification rather than a green suite. It is recorded here, and
not only in a commit message, because a reviewer deciding whether to trust this
apparatus should weigh it — and because the one thing that has held across all
five rounds is that **every defect was found by a context that had not written
the code.**

### 13.5 The fifth re-verification, and the change that ends the pattern

A fifth fresh context audited the round-five head and found two categories.

**The apparatus did not run.** With the guards armed on a clean checkout,
**every module import died.** The cache exemption keyed on a `.pyc` *file*, and
the first thing a cold import does is create the `__pycache__` *directory*;
`IsolationError` is a `RuntimeError`, so the `except OSError` that makes
`exist_ok=True` work never saw it. The virtual environment lives inside the
checkout here, so third-party imports died too. That is a functional blocker
that five rounds of security review had not surfaced, because every round ran
in a process whose caches were already warm.

**And the routes.** Every listed pyarrow target was reachable under its
*defining* name (`pa.OSFile is pa.lib.OSFile`), and re-importing the package
rebound the re-export back to the original. Seven listed **classes** were
replaced by functions, so `isinstance` broke process-wide — the round-four
defect again, while a comment claimed the list held no class targets. sqlite
`ATTACH` landed through `Cursor.execute` and through SQLAlchemy's own DBAPI
path. `mmap` on an `O_RDWR|O_APPEND` descriptor, `shutil.copy2`,
`_winapi.CreateFile` and `_winapi.CopyFile2` each destroyed the ledger, and all
four are real CPython audit events this module had claimed to handle in full.

One of those is worth recording as a **measured limit** rather than a defect:
`pyarrow._fs` cannot be patched at all. Replacing any name in it — the abstract
`FileSystem`, `LocalFileSystem`, `SubTreeFileSystem` — breaks `pyarrow._hdfs`
on import with `KeyError: '__pyx_vtable__'`. **A guard that breaks the
dependency it guards is not an option**, so the module is disclosed through
`unpatchable_native_targets()` instead, and §6 points a reviewer at it.

#### The change that is not another patch

Six independent audit contexts each found a route the audit had certified
against, and **each time the fix went to the specific route and never to the
claim.** That is the defect class, and it is the one this round closes:

- `TRACK_A_EXECUTION_CONTAINMENT_VERIFIED_NO_UNGATED_ROUTE` is **retired**. No
  in-process audit can establish "no ungated route". The status is
  `…_PROBES_PASSED_BOUNDED_ASSURANCE`, and a test forbids the words *verified*,
  *proven* and *guaranteed* in it.
- Every report carries **`bounds`** — five statements of what it does not
  establish — so the qualification travels with the verdict and cannot be
  dropped in quotation.
- `no_market_data_read`, which read `True` while three separate rewrites of the
  route read a file, is now `declared_gate_sequence_matches_at_this_head`.
- The report separates `behavioural_checks` from `source_checks_advisory`, so a
  reader can tell which half carries the verdict.

#### And the tests

The fifth reviewer's closing diagnosis was that *every fix has been to the
specific attack, and the regression test has been written to the specific
attack too* — with two proofs: `.git/__pycache__/x.pyc` slipped past a test
that pinned the filename `x`, and a cold-import test set `PYTHONPYCACHEPREFIX`
outside the repository, certifying a configuration a real run does not have.

`tests/m15_track_a/test_defect_classes.py` is written against the **class**. It
enumerates `NATIVE_REFUSED_TARGETS` and requires every entry to refuse; sweeps
the same list for lost type identity; imports the dependency's own graph to
prove the guard did not break it; requires the disclosure channel to be
non-empty while a known gap exists; cold-imports every package found on disk
**without** `PYTHONPYCACHEPREFIX`; sweeps the protected roots rather than the
one that failed; and asserts the status carries no universal claim.

**Six rounds. Eight independent audit contexts. Every defect was found by a
context that had not written the code, and a green suite predicted conformance
at every single head.** A reviewer weighing this apparatus should weigh that
first, and should read §6's bound and the report's `bounds` before quoting any
status from it.

## 15. The final Human + ChatGPT Gate-decision round — 2026-08-30

Four decisions were reserved for a human + ChatGPT round before Track A could
begin. This section records them and nothing else: no surface was re-audited,
no new adversarial search was run, and no statistical question outside these
four was reopened.

### 15.1 The turnover axes — RULED

Recorded in the pre-registration at **§9a**, because C-15 and C-20 place these
surfaces in prereg §9 / Ruling 10 territory, outside arm 3 — a ruling written
only here or in the contract packet would fall to C-9 and to the
unamended-clause rule.

**`TURNOVER_CEILING_RULED_PER_DAY_CAP_ON_THE_ENTRY_DATE_MAXIMUM`** ·
**`TURNOVER_DENOMINATOR_AXIS_IS_NON_BINDING_UNDER_THE_CAP_AND_STAYS_UNREGISTERED`** ·
**`A_TURNOVER_FIGURE_IS_REPORTED_ON_EVERY_CANDIDATE_AXIS_IN_BOTH_TRACKS`.**

It was a **genuine human choice, not a derivation** — the "calendar is a ~42%
loosening" argument needs the incumbent as its baseline, and §10.4 established
there is no committed M15 turnover implementation to be one, which leaves
"loosening" without a referent on these axes and Ruling 10 selecting nothing.
The chosen rule tightens, closes both axes with one decision, and cannot be
moved back without a visible loosening ruling. The numeral 40 is unchanged and
no new threshold was created. §9a records the accepted cost: a single outlier
day can now close family A by a convention rather than by economics, and
`metrics.py`/`acceptance.py` need a per-date maximum that they do not yet have.

### 15.2 prereg §13a / P-7 — RULED

**`PREREG_TWO_TRACK_AMENDMENT_RULED_AND_IN_FORCE_FOR_TRACK_A_ONLY`** ·
**`P_7_DISCHARGED_AT_THIS_RULING`.**

The draft was **not** sufficient and was widened before adoption. As drafted it
covered §3.1, §4, §11 and §16, said §10 was "unchanged" and said "§14 below is
unchanged" — so adopting it would have discharged P-7 on paper while prereg
§10 item 3 ("gate 3a … must complete before any implementation PR reads or
derives data", and §8.11.12 A-3 makes Track A implementation), §13 and §14 ("no
raw data access; no metric computation") each still forbade the read. That is
precisely the failure §8.12.13's widened P-7 was written to prevent. Rows for
§10, §13 and §14 were added, and rows were added for the §8 model freeze,
Ruling 9's `ev_min` grid, Ruling 5's cost model and §6's no-label-search — four
clauses C-15 limb 1 names, whose silence would have re-frozen surfaces §8.13.4
declares free to vary. The §8 row's "training span only" limb was restored, and
§13a's claim that the ladder "skips none" was corrected: playbook §1 places
**A-R1 before the gate-3a continuation**, so it reorders as well as adds.

### 15.3 The bounded-assurance threat model — ACCEPTED

**`TRACK_A_R1_BOUNDED_ASSURANCE_THREAT_MODEL_ACCEPTED`.**

#452 is accepted as **bounded assurance, not a sandbox**. The known
limitations — an unlisted C extension, `pyarrow._fs` and anything else
`unpatchable_native_targets()` discloses, a hardlink pre-seeded into the working
tree, and code deliberately disarming an in-process guard — are accepted as
**residual risk for Track A R1**, on the criterion that R1's purpose is not
production-grade isolation but to make an **accidental** boundary crossing fail
loudly and a **deliberate** one appear in a diff.

The acceptance is conditional on two properties that were checked, not assumed:
the limitations are **disclosed** (§6, `AUDIT_BOUNDS`,
`unpatchable_native_targets()`), and the report claims no more than
`…_PROBES_PASSED_BOUNDED_ASSURANCE`. An independent review re-ran 35 of the
listed native targets, 17 boundary probes and 17 intended-path refusals against
a clean clone and found the disclosures matched the code. **Absence of a
production sandbox is not, on its own, a reason to block.**

### 15.4 The general adversarial audit — CLOSED for this scope

**`GENERAL_ADVERSARIAL_AUDIT_COMPLETE_FOR_TRACK_A_R1_BOUNDED_SCOPE`.**

"No unknown attack route exists" is **no longer a merge condition** for Track A
R1. Six fix rounds and eight independent audit contexts is where this stops.

What still blocks, from here: a **concrete, reproducible** defect inside the
Track A R1 threat model — historical data readable without an explicit
authorisation; network, DB or broker reachable; a write outside the scratch
root from the intended Track A path; the seen ledger, `K` or `N = 1` bypassable;
or the apparatus not running on a clean checkout.

What does **not** block: a theoretical C-extension bypass nobody has exhibited;
anything that only a real sandbox would close; production hardening; a
pre-seeded hardlink; in-process self-disarming.

### 15.5 What this round did not do

It did not merge either PR, did not authorise a read, and did not re-open the
149-surface inventory. **Two review roles** ran — contract consistency, and
bounded-assurance / merge risk — and both were asked the same question: whether
a material blocker remained for a human decision. Both found the same one, a
**doc-only** defect: this PR's own diff had left a **withdrawn** turnover ruling
alive in the contract packet, citing as its authority the very section that
retired it, and calling the permissive arm the stricter one. It is corrected,
and the drift test that missed it — it swept the source documents but not the
files the source is propagated **into** — now sweeps the propagation targets too.

## 16. R1's read body — implemented, and still ungranted

**`TRACK_A_R1_HISTORICAL_READ_IMPLEMENTED_PENDING_A_GRANT_AND_AN_EXECUTION_COMMAND`.**

§2's design rule said "every route that could reach real data exists, is named,
is gated, and its body is absent", and that a future PR "adds a body, not a
policy". That PR is this one. The gates are unchanged; a body was added beneath
them.

**What it does.** For each pair it may read, it resolves one committed
`365d_BA` M1 bid/ask file from a module-constant template, reads the lines whose
timestamp falls inside the window, and returns them in the row shape
`aggregate_m15` consumes. Nothing else: no aggregation, no labels, no features,
no fit, no score, and no write beyond the ledger entries the gates already
require.

**Every bound is the narrowest of the three that constrain it — and the first
drafting of this section said the opposite.** It said "every bound comes from
the grant, not from the request", reasoning that a request mutated after the
gate could not then widen the read. True, and it inverted the safety. Coverage
is *containment*, so a grant may legitimately be **wider** than the request, and
the wider part passed neither `assert_span_admissible` nor the seen-data
declaration — both of which are checked against the **request**.

Two review roles reproduced it independently, on two different axes:

* **time** — a May declaration, a May request and a full-design-span grant
  returned September and February rows;
* **pairs** — a one-pair declaration with a two-pair grant **opened both files**,
  which the time-axis fix alone did not touch.

Ten months and a second pair would have become `EXPLORATORY_SEEN_DATA` with one
month and one pair on the record. Seen-data is irreversible, so an under-record
is not something a later entry repairs.

The window and the pair list are therefore the **intersection** of grant and
request: no wider than the grant, so no unauthorised byte; no wider than the
request, so a mutated request still cannot widen it; and therefore no wider than
what was declared. A requested pair the grant does not name, or two spellings of
one pair, are **refused** rather than silently dropped or folded — both mean the
request is not what the gate checked.

**What the scan touches, stated exactly.** The source is one JSONL file per pair
covering the whole epoch and there is no index, so finding the window means
scanning. A review role measured what that cost under the first drafting: a
malformed row *outside* the granted span still failed an inside-the-span read,
which proved every line in the file was being parsed in full — including the
consumed dead window, which this repository's own PR #444 ruling
("**hashing IS a byte read**") would count as read. Two properties now bound it,
and neither is an assumption about the data:

* prices are materialised **only** for rows inside the window; every other line
  is decoded for its timestamp and discarded;
* the scan **stops** at the first row past the window, and the source is
  *required* to be strictly increasing for that stop to be sound — a source that
  is not refuses the read rather than returning a silently truncated one.

The dead window and the forward epoch sit after every admissible window, so
stopping is what keeps them unread; relying on the committed files not
containing them would be a property of the data, not of the route. What remains
is disclosed rather than softened, as `read_route.SCAN_DISCLOSURE`:
`SCAN_DECODES_TIMESTAMPS_OF_EARLIER_ROWS_IN_THE_SAME_FILE`.

**One source, no fallback.** `train_lgbm_models.py` has an "if the BA file is
missing, use mid" branch — the shape §8.13.5 asked for a single route to remove.
Here a missing file is a **refusal**. A test asserts it on the AST: exactly one
`open` in the route, and every `except` re-raises.

**Two things the body adds to the gates rather than inheriting.** A grant naming
`M15` is refused, because M15 does not exist until the derivation runs and is a
separate operation with a separate grant. And a **row** whose timestamp falls in
the dead window, or at or after `FORWARD_FLOOR`, is refused even when the
declared interval passed `assert_span_admissible` — `no_overlap` checks
declarations and says so
(`CALLER_DECLARED_METADATA_ONLY__NO_FILE_OPENED__NO_BYTE_MEASURED`), so the
declaration being clean is not evidence that the bytes are.

**Both of those row-level refusals are unreachable at this head, and the tests
say so rather than implying coverage they do not have.** With the window clamped
to the request, and the request bounded at `DESIGN_END` by
`assert_span_admissible`, and `DEAD_START` exactly one second after `DESIGN_END`,
no row the scan reaches can be in either quarantined span. They stay in as a
backstop for a head where `assert_span_admissible` is weakened, and the test that
covers them asserts the *ordering property that makes them unreachable* instead
of pretending to exercise them.

**The containment audit's question changed with it.** `read_body_absent` asked
whether the body was *absent*, and that answer licensed a claim that nothing
could be read. It is now `read_body_declared` and asks whether the body is **the
declared route**: one definition, one `open`, on a path from `source_path_for`,
inside `gated_read_window`. §11 records the seven conditions and the one defence
that had to move — `ast.Subscript` is permitted now, because the body does
`row[key]`, so the rule narrowed to "a subscript on a **module-level** name is a
finding" and keeps catching `SLURP["path"]`.

**The seventh condition exists because a review role defeated the first six.**
Conditions 1–6 read **one function**, while adding `read_route` to
`_PERMITTED_FILE_OPENERS` exempts the whole **module** from the reader-name
sweep. The role measured the gap that opened: it put four lines into
`_row_from_source` — a helper, so outside conditions 1–6 — read an undeclared
market-data file from them, and **every audit check still returned PASS**. Its
first attempt used `globals()` and the indirection sweep caught it; the second
used no reflection and nothing did. The exemption is now bounded by the sweep it
removes: every reader-name reference in the module must be the one open the body
performs, pinned by its exact finding string rather than by its line.

That the hole was opened by this PR's own fix, and closed only because a role
went looking, is the same shape §13.1–§13.5 record five times over. It is
recorded here for the same reason: **a green suite has never once predicted
conformance in this package.**

**And it is still ungranted, on two counts.**
`docs/design/m15_track_a_r1_read_authorization.md` records both.

1. The development span's **end** cannot be derived: R-2 requires the
   `EXPLORATORY_OOS_SLICE` boundary to be "chosen and recorded before stage R1"
   and no committed source names it.
2. The **approved head SHA** is not determined either. A grant names the code
   that will run the read, and at the merged master `37edbb0` the body does not
   exist; the head that carries it is this PR's, unmerged and unapproved. An
   earlier drafting of the authorization document put `37edbb0` in the table,
   which would have authorised a read against code that cannot perform one.

The body exists; the authorisation that would let it run does not, and this PR
does not create one.

## 17. The two blockers R1 was left on, and how they were closed

`TRACK_A_R1_READ_SCOPE_AND_AUTHORIZATION_SEQUENCE_RULED`.

§16 ended with the read body implemented and ungranted on two counts. Both are
now closed by human + ChatGPT ruling, recorded in full in
`docs/design/m15_track_a_r1_read_authorization.md` §4 and §4a.

**1. `EXPLORATORY_OOS_SLICE_RULED_AS_FINAL_TWENTY_PERCENT_OF_COMMITTED_DESIGN_UTC_DATES`.**
R-2 fixed the slice's shape and the timing of the decision but not its size, and
the size was a genuine human choice. It is now the final 20% of the committed
DESIGN span in UTC calendar dates, and the dates fall out of two committed
constants: 310 design dates, `ceil(0.20 x 310) = 62`, slice
`2025-12-29 … 2026-02-28`, development span `2025-04-25 … 2025-12-28`.

**A human chose `0.20`; nobody chose `2025-12-29`.** The arithmetic lives in
`scripts/m15_track_a/oos_slice.py`, which reads no file, no environment variable
and no clock — asserted on its AST, after a first draft of that very test was
defeated by the word "environment" appearing in the module's prose.

The quarantine is enforced in **three** places, because a review role drove all
62 slice dates through a single one of them. `read_route.assert_development_only`
refuses — never trims — a `track_a_historical_read` whose **touched** interval,
warm-up included, reaches `2025-12-29`; the route re-applies the same check to
the **computed window**, after every request field has stopped being consulted;
and `ReadGrant` itself refuses to be constructed over a slice date for that
operation, with the mirror rule for `track_a_exploratory_oos_slice_read`.

The reproduction that forced all three: a `ReadRequest` **subclass** answering
`span_end_utc` honestly at the gates and widening afterwards — the route reads
that field three times — combined with a grant reaching `2026-02-28`, returned
the whole quarantined slice. The route now pins `type(request) is ReadRequest`
exactly, as it already did for the grant. The same role also found
`derivation.derive_m15` applying `assert_span_admissible` but **not** the slice
gate, while its docstring claimed it carried the read route's gates. It sits beside `assert_span_admissible`
rather than inside it: the design-span and dead-window bounds come from the
committed `no_overlap` module, this one comes from a ruling, and collapsing them
would hide which authority refused a read.

The ≥ 25-bar purge is deliberately **not** subtracted from the read span. R-2
drops those bars "from training", counting **in bars** — and counting bars means
reading them, so making the read span depend on the purge is circular. The bars
are read; the labels are purged downstream, the same division §8.11.12 F-5
already records at `DESIGN_END`.

**2. `READ_GRANT_BINDS_TO_APPROVED_IMPLEMENTATION_ANCESTRY_NOT_SELF_REFERENTIAL_EXECUTION_HEAD`.**
The self-reference was real and was confirmed from source, not assumed.
`require_authorization` refused unless `identity.code_sha` equalled
`grant.approved_head_sha` — **two caller-asserted strings**, since `code_sha` is
never derived from the running tree. It refused an honest run at the wrong head,
refused a dishonest one never, and made recording a grant invalidate that grant,
because the commit that records it moves `HEAD`.

`ReadGrant` gains an eighth required field,
`approved_implementation_fingerprint`, and the gate refuses unless it equals
`containment.implementation_fingerprint()` **measured from the running tree**: a
sha256 over every `.py` under `scripts/m15_track_a/` plus the **transitive**
first-party import closure, with paths and the file count hashed alongside the
bytes, line endings normalised, and every module resolved through `importlib`
rather than by path arithmetic.

**Three of those words are corrections a review role forced, and each was a
measured hole, not a tidy-up.**

* *Transitive.* The first drafting listed the modules the package imports
  directly. `no_overlap` imports `timeutil`, and `timeutil.to_utc` is what
  `is_dead_window_instant` is built on: shifting it by 400 days disabled the
  route's dead-window row guard **with the fingerprint unchanged and the grant
  still valid**. `numeric_authority`, both package `__init__.py` files and
  `ml_step4/data_adapter.py` were outside in the same way. Worse, the anti-drift
  test written to catch exactly this walked only the package's own files, so it
  passed while the drift was already present.
* *Through `importlib`.* `scripts` has no `__init__.py`, so it is a PEP 420
  namespace package and `PYTHONPATH` alone can serve `scripts.m15_gate3a` from
  elsewhere. Path arithmetic hashed the repository's pristine file while the
  process ran the shadow — matching fingerprint, valid grant, **and nothing in
  any diff at all**. `find_spec` resolves what will actually be imported.
* *Line endings normalised.* `core.autocrlf` is true here and CI is Linux, so
  one commit produced two different values. That is not a bypass, but it would
  have made the workflow unworkable: a value recorded from CI could never match
  the host the read runs on, and flipping the git setting would have voided a
  grant with no code change.

**And one of those fixes introduced a fourth defect, caught by measurement
rather than by review.** `import importlib` does not bind `importlib.util`, and
the resolver caught `AttributeError` — so every sibling resolved to `None` and
the surface silently shrank back to twelve files while the code said "closure".
An over-broad `except` turned a missing import into precisely the silent
weakening the function exists to prevent. The import is explicit now and
`AttributeError` is no longer caught.

So an authorization-only commit keeps the grant valid, and a change to anything
on the **declared surface** voids it with no human in the loop. Stated that way
deliberately: an earlier drafting of this paragraph said "**any** change to what
a read does", and that was the overclaiming this document has spent eight rounds
retiring. `AUDIT_BOUNDS` names what a source fingerprint cannot see — an
`UNCHECKED_HASH` `.pyc` (which needs no craft and is gitignored), an installed
dependency, a non-`.py` file loaded at run time.

The other limit, also stated rather than implied: this binds the implementation,
not the ancestry. Whether the execution head descends from the approved head is
a `git` question, and reaching git from inside a gated read means spawning a
process the isolation layer exists to refuse — so it stays a gate-time
obligation on the reviewer (`git merge-base --is-ancestor`, `git diff --stat`),
and it is the weaker of the two, since identical implementation bytes read
identically wherever they sit.

**Nothing here issues a grant.** No `ReadGrant` is committed in this PR, and
that is the point of the sequence: a grant names the fingerprint of a **merged**
head, and none exists while the PR is open. Approval of the implementation, the
authorization-only commit, and the execution command remain three separate
steps.

## 14. Non-authorisation statement

Nothing in this document or in `scripts/m15_track_a/` authorises a real-data
read, a derivation, training, evaluation, a run, a broker connection, or a
deployment. No real data was read in producing it. No training, evaluation or
fitting was performed. `PRODUCTION_READINESS_NOT_CLAIMED`;
`NO_EXECUTION_PERFORMED`.
