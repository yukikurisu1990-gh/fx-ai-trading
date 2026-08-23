# M15 Minimum Research Gate — decision packet

**Type.** Gate-decision PR (policy §14.2). **Risk tier.** Amber — doc-only, and
it defines a research boundary.

**Completion state.**
`M15_MINIMUM_RESEARCH_GATE_PENDING_HUMAN_CHATGPT_RULING`

**Statuses carried, unchanged.**
`M15_AGGREGATION_DATASET_MACHINERY_SOURCE_AUDIT_BLOCKED_PENDING_TARGETED_FIXES` ·
`M15_GATE3A_CONTINUATION_OUTPUT_SURFACE_CORE_RULED_PRODUCTION_DEPENDENCIES_DEFERRED`
(PR #450) · `M15_GATE3A_CONTRACT_AND_PROOF_DESIGN_DECISION_RULED` (PR #444) ·
`M15_GATE3A_D5_8_AND_SECTION12_25_CONTRACT_RULED` (PR #448) ·
`M15_AGGREGATION_DATASET_MACHINERY_IMPLEMENTED_SYNTHETIC_ONLY_NO_RUN` ·
`M15_GATE3A_DATASET_EPOCH_ADOPTION_PROPOSED` · `PRODUCTION_CONTINUATION_NOT_READY` ·
`PRODUCTION_READINESS_NOT_CLAIMED` · `NO_EXECUTION_PERFORMED` ·
`FORWARD_EPOCH_ADOPTION_BLOCKED_INSUFFICIENT_SAMPLE_ADOPTION_WAITS` ·
`PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED`.

**Forbidden-label note.** This document asserts none of `PASS`, `Tier 1`,
`FORMALLY_VERIFIED`, `PRODUCTION_READY`, `READY_FOR_LIVE`, `M15_AUTHORISED`,
`H1_AUTHORISED`, `H2_STARTED`, `PHASE_C2_STARTED`, `NEW_EPOCH_ADOPTED`,
`BYTE_ADMISSIBLE`, `MEETS`, `ROBUST`, `DEPLOYABLE`; every occurrence of such a
label in this document sits inside this list or inside a prohibition sentence.

**Nothing here is executed.** No source, test or artifact is changed; no data is
read; no dataset is downloaded; no model is trained; no evaluation is run.

---

## 1. Why this gate exists

The programme's objective is to find out whether **M15 carries a
cost-inclusive, out-of-sample tradeable edge**. Completing production-grade
evidence infrastructure is a means, not the objective.

Four audit rounds have improved the evidence machinery substantially and have
also shown how much remains: PR #450 closed with **seven production dependencies
deferred** (§10 there), including reader-freedom scope, candidate payload schema
admission and status semantics. Requiring all of them before the first research
question is asked is disproportionate to the objective.

This gate therefore separates two things the programme has so far treated as one:

| | Production-grade evidence gate | **Minimum Research Gate** |
| --- | --- | --- |
| Question | may this output become authoritative evidence? | does M15 carry an edge worth pursuing? |
| Output | committed evidence | `RESEARCH_SCRATCH_NON_AUTHORITATIVE` |
| Blocked by | PR #450 §10's seven dependencies | §3's boundaries, §4's integrity requirements, the frozen frame in §2, policy §6 Red approval per stage, and PR #450 §10 rows **F** and **G**, which block a real read on either route |

**This gate is `READ_ONLY_RESEARCH_EXPLORATION_GATE`.** It is not a production
readiness gate, not a live-trading gate, not an evidence-promotion gate, and not
a substitute for the formal Gate-3a continuation. The token names **data access**;
R3 is a training run and R4 an evaluation, and neither is read-only in this
repository's sense (§7).

**PR #450 §2.2 binds this document by name:** "**A Minimum Research Gate is not a
lighter alternative to a Contract Gate-decision and confers no authority of its
own.**" Nothing here is lighter than a Contract Gate-decision — this *is* one, and
it confers only what a human + ChatGPT ruling on it confers.

---

## 2. What committed authority already supplies — and it is more than expected

**The exploratory role already exists in the frozen pre-registration.**
`docs/design/m15_first_cost_hurdle_aware_preregistration_design.md` §3.1 defines:

> | **Design (exploratory)** | 2025-04-25 → **2026-02-28** | M15 aggregate of the
> adopted `365d_BA` epoch's pre-holdout span (R-2a) | usable only after the §4
> derivation artifact exists; **results never citable as evidence** |

So the *role*, its *span*, and its *non-citability* are committed. This gate
invents none of them.

**The acceptance thresholds are frozen and are not this gate's to set.** §9 of the
same document, "FROZEN; design audit may only tighten":

| Criterion | Frozen threshold |
| --- | --- |
| net expectancy (empirical cost) | > 0 |
| gross expectancy vs cost | ≥ 1.5 × all-in cost |
| stressed-cost survival | net ≥ 0 at 2× cost **and** at p90 session spread |
| daily portfolio Sharpe (ann., UTC-day) | ≥ 0.8 |
| max equity drawdown (vs fixed notional) | ≤ 0.15 |
| trade count lower bound | ≥ 1,000 holdout trades **and** effective-N ≥ 400, else `INSUFFICIENT_SAMPLE` |
| daily coverage | ≥ 0.60 |
| turnover upper bound | ≤ 40 trades/day portfolio-wide |
| pair trade concentration | ≤ 0.40 |
| pair positive-PnL concentration | ≤ 0.50 |
| class-frequency sanity | recorded; defect trigger only, not a standalone pass/fail gate |
| concurrency/exposure | recorded; caps **[FIXED-AT design audit]**, before implementation |

All twelve rows are reproduced. The last two are recorded-only items rather than
pass/fail gates, and are carried so this quotation cannot be read as the table
minus what did not suit it.

Plus the **validation kill gate**: net expectancy > 0 **and** gross ≥ 1.5 × cost
at ≥ 1 registered `ev_min` point, within the turnover budget; all-fail closes the
family with no holdout consumed. `N_EFF_HOLDOUT_FLOOR = 400` and
`RAW_HOLDOUT_TRADE_FLOOR = 1000` are in source at
`scripts/m15_gate3a/effective_n.py`.

**`Ruling 10` forbids loosening these.** This gate does not restate them as its
own criteria, does not soften them, and does not apply them to exploratory
results — see §6.

**The cost model's structure is committed; its numbers are not.**
`all_in_cost = median_spread(pair, session) + pad_exec + cell_slippage`, with
**`pad_exec = 0.3 pip`** and **`cell_slippage = 0.5 pip` (primary)** — both frozen
by Ruling 5, and the whole model scoped by Ruling 5 as a **quote-cost-validity
research claim, not a live-fill claim** (prereg §5). Omitting `pad_exec`'s value
understates modelled cost by a third, in a gate whose R-5 exists to prevent
exactly that.

**But the per-pair × session spread tables do not exist.**
`artifacts/m15_gate3a/cost_table_plan_or_metadata.json` records
`option_selected: "B__DEFER_COST_TABLE_PRODUCTION_TO_IMPLEMENTATION"`, and T-6
re-points their production to gate 3a or the implementation PR, from design-span
data only, with mandatory human approval. So "under the committed cost model" is
not a lookup — the tables must be estimated first, under Q5 and subject to R-10.
**A zero-cost result is not admissible as a primary finding anywhere in this
programme.**

**The design audit tightened, and the tightenings bind.** §9 is headed "FROZEN;
design audit **may only tighten**" — and gate 4 did tighten. PR #430 imposed
**T-1…T-7**, recorded in the playbook as "Gate 4 — Fable 5 design audit
(PR #430, tightenings T-1…T-7) | ✅ accepted for gate 3a". Four reach this gate
directly:

- **T-1** — dead-window data is **never loaded**, for any purpose, including
  indicator warm-up.
- **T-3** — if the **median eligible barrier/cost ratio on design data is < 3.0**,
  execution authorisation (gate 7) is **BLOCKED** pending a new human + ChatGPT
  ruling. Verbatim: "M15 must demonstrably escape the M1 cost regime before
  anything runs." This is measured **on design data**, needs **no model**, and is
  the direct test of the stated reason for preferring M15 to M1 — so it belongs
  in R1, not after a model exists (§7).
- **T-4** — timeout share is mandatory evidence, with a > 60% investigation trigger.
- **T-5** — max drawdown is measured against a **10,000-pip fixed notional**.

**T-6** re-points the cost tables and the effective-N estimator with mandatory
human approval; **T-7** requires the ts-bound / no-overlap proof in the gate-3a
artifacts.

**Other frozen frame:** `PAIRS_20`; M15; horizon frozen at **24 bars** (Ruling 6);
purge/embargo **≥ 25 M15 bars** at every role boundary; the dead window
2026-03-01 → 2026-04-24 excluded from every role.

**The M1 precedent is committed, and it is narrower than a prior.** The `365d_BA`
M1 flagship returned a valid `DOES_NOT_MEET`: expectancy **−3.49 pips/trade** at
the 0.5-pip cell, **−2.99** with the cell removed (spread stays embedded in the
bid/ask labels, so −2.99 is not a zero-cost figure), **20 of 20 pairs negative**.

Its reach is stated in the committed post-run audit: "**Does PR #425 prove all
possible M1 strategies cannot work? No.**" and "Is M1 structurally disadvantaged
**for this architecture and data**? Yes." The prereg localises the failure to four
mechanisms — barriers a few pips wide with embedded spread consuming them,
~20-minute timeouts, 168 trades/day, and feature information content — and **the
M15 design changes all four**. The prereg accordingly frames the M15 hypothesis as
one "under test (not an expectation)".

**So the honest position is equipoise, not a negative prior.** An earlier draft of
this packet asserted that M15 was chosen because "M1's spread/ATR ratio made a
short-horizon edge structurally implausible" and that "the prior is that there is
no edge". Neither is committed: the spread/ATR framing traces to Phase 23
material classified `REQUIRES_SEPARATE_EVIDENCE_RECONCILIATION`, which **C-8
(Ruling 13) bars from this family's priors** by name, and the post-audit refuses
the generality. Both claims are withdrawn.

**This matters in a specific direction.** A negative prior plus an undefined
`failed` verdict (§7) plus §6's consequence for `failed` is a route by which an
underpowered exploratory negative closes a programme. The first admissible
measurement that moves equipoise is **T-3's median eligible barrier/cost ratio on
design data**, which needs no model and no prior — which is the case for running
this gate cheaply rather than confirming a belief expensively.

---

## 3. Mandatory safety boundaries

These bind every stage. They are not negotiable by a Work PR.

### 3.1 Broker

**Forbidden:** live order · demo order · any broker write · position
modification · account action. **The research phase requires no broker connection
at all**, and none may be opened.

Price data comes from a local read-only source — but **no such source is approved
yet** (Q3), so this sentence constrains a future ruling rather than describing the
present state. Any reader used at R1–R4 is a **new byte-reading capability** over
`data/`: `scripts/m15_gate3a/**` is contract-bound reader-free (§12.14, pinned by
`tests/m15_gate3a/test_wp5_reader_freedom.py`), and `guards.py`'s
`_PROTECTED_PREFIXES` names `data` and `models` as trees that package may never
target. PR #450 §10 rules its deferrals are not preconditions for this gate, but
its row **E** defers the P/V reader because a new read capability "needs its own
audit". Whether that reasoning reaches the exploratory reader is part of Q3.

### 3.2 Database

**Forbidden: any database access.** No DB write, no schema mutation, no
`INSERT`/`UPDATE`/`DELETE`, no migration, and no external DB dependency for
research execution. "Preferred path" was the wrong register for a section headed
*not negotiable*.

A read-only exception is not available under this gate. If one is ever required it
needs **explicit separate human authorisation**, a read-only **role** — not merely
a read-only transaction, which is per-statement-scoped and is exactly the
named-route defence this subsection warns against — and no credential display. This is a
live risk in this repository, not a hypothetical: an unscoped `pytest tests/` once
wrote to a live local database because `.env` loaded at import, and PR #446
established that **presence of a credential is not authorisation to use it**.

**Two limits on that fix bind this gate, and an earlier draft of this packet
overstated it.** The claim that "route-independent enforcement (a
`sys.addaudithook` on `open`) is what actually holds" is **withdrawn as false**.
First, the guards live in `tests/conftest.py` and install at conftest import, so
they hold for a **pytest session only** — a research run is `python scripts/…`,
which they never see. Second, the `.env` guard is **not** route-independent:
`tests/conftest.py:253` prefilters with a case-sensitive `endswith(".env")` and
`:255` compares an `abspath` that strips neither trailing dots nor spaces, so
`.ENV`, `.Env`, `.env.` and `.env ` each read the file in full even inside a
guarded session — on Windows, where this repository runs, all four name the same
file. That is **FR-19(a)**, recorded by the fourth re-check and **deferred** by
PR #450 §10 row D; FR-19(b) records that the socket guard binds only
`connect`/`connect_ex`, leaving `send`, `sendall`, `sendto`, `getaddrinfo` and
`gethostbyname` — and the C base `_socket.socket.connect` — unguarded, so §3.3's
DNS clause has nothing behind it either.

**This gate therefore inherits no working `.env` defence and no working network
defence**, and must supply its own (§3.5).

### 3.3 Network

During research execution: **no arbitrary network, no DNS, no storage upload, no
external telemetry, no webhook, no Slack or email.** Any dataset must be prepared
locally and read-only beforehand.

### 3.4 Credentials

A research run **may not read `.env`**, may not read any credential-shaped
environment variable, and **may not test for the presence of one**. No stage needs
a broker or database credential, and none may be displayed, logged or written to
an artifact.

The word *normal* is deliberately absent from this rule. The run that caused the
recorded incident **was** a normal run — `pytest tests/`, no flags — and the
credential reached it at import time, without anyone classifying it as unusual.
The presence check is named because `_gate_p1_inspector/guards/credentials.py`
already blocks it: a run that can ask whether `OANDA_ACCESS_TOKEN` exists can
branch on it without ever displaying it.

### 3.5 What enforces §3.1–§3.4

§3.1–§3.4 are prohibitions on a **process**, and every guard this repository owns
installs in a **pytest session**. `sys.addaudithook` appears in exactly one
non-vendored file in the tree (`tests/conftest.py:264`); there is no
`sitecustomize.py`. A research run of the shape this repository already uses —
`python scripts/compare_multipair_v23_realism.py`, reading `data/*.jsonl` directly
and writing logs under `artifacts/` — is bound by nothing.

**Normative.** No stage R1–R4 runs outside a fail-closed guarded envelope, and a
guard violation is a **HALT**, not a logged warning. This is not new work and not
production hardening: `scripts/_gate_p1_inspector/guards/` is merged and was built
for exactly this — a read-only research inspection outside pytest — with network,
subprocess, credential (including presence-check), filesystem write-allowlist,
`python -B` and `sys.meta_path` import guards, driven by
`scripts/gate_p1_pr_b_launcher.py` with an outer/inner topology and a scrubbed
environment. The second precedent is `scripts/ml_step4/executor.py`'s
`guarded_execute`, which refuses any non-dry-run call and is what made "no
execution" *true* rather than promised for the programme's only completed research
gate. The implementation Work PR reuses that shape, or states why each guard is
unnecessary here.

**Subprocess spawning is named explicitly**, because it is the generic bypass for
every in-process guard and child interpreters inherit none of them. **Runtime
package installation is forbidden**: `uv sync` against the stale lock is
destructive, and the playbook already bars any Red operation that presumes a
frozen uv environment.

### 3.6 Data recency, and consumed data

Two hard date boundaries, derived rather than invented.

**No stage may read, aggregate, plot, summarise or otherwise observe any bar
timestamped at or after 2026-03-01.** The prereg makes 2026-03-01 → 2026-04-24 a
dead window "excluded from every role at every timeframe", and puts validation on
a forward epoch starting no earlier than 2026-04-25 whose boundaries `T_v`/`T_h`
are `[FIXED-AT gate 3a]` and not yet fixed. §7's instruction that R4 "must not …
approach the frozen holdout" **cannot be obeyed** by a researcher, because the
holdout's edges do not exist yet; a fixed date can be. The committed archive
snapshot (`artifacts/oanda_archive_2026-05-31/`, 3650 days) already contains
forward-epoch bars, so this is an access rule, not a hypothetical. Observing them
would be a decision-bearing observation of a holdout that has not been adopted.

**The dead window is the consumed `365d_BA` M1 holdout**, and exclusion reaches
**feature warm-up and every lookback**, not only labels (T-1; playbook §6). Every
span declared under this gate passes `scripts/m15_gate3a/no_overlap.assert_design_bounds`
and `assert_no_dead_window` — already committed, reader-free, fail-closed, and
usable today. `DEAD_START` is exactly one second after `DESIGN_END`, so a `<=`/`<`
slip pulls consumed-holdout bars into exploratory training; that is why the check
is a call, not a promise.

### 3.7 Writes

A research run writes only beneath a **single named research-scratch root**, and
creates nothing elsewhere. It may not write under `artifacts/m15_gate3a/`,
`artifacts/ml_step4/365d_ba_v1/`, `artifacts/gate_p1_pr_b/`, `data/`, `models/` or
`docs/`.

Neither existing protection reaches a research process: `tests/conftest.py`'s
`PROTECTED_TRACKED_ARTIFACTS` teardown hash is pytest-only, and
`scripts/m15_gate3a/guards.py::refuse_real_path` is routed from a single call
site — that module's own docstring states that containment of an *unrouted* caller
"is not a property this module has, and must not be cited as one." A research
runner is by definition an unrouted caller.

---

## 4. Minimum research-integrity requirements

Each is here because **its absence would materially mislead the conclusion**, not
because production wants it. §5 states that test explicitly.

**R-1 Frozen research question, registered before results are seen.** Target
pairs · timeframe M15 · label definition · prediction horizon · evaluation
evaluation periods · transaction-cost model · primary metrics · stop criteria.

**Where a frozen value already exists, the registration adopts it unchanged** —
pairs (Ruling 2), horizon and label geometry (Ruling 6), feature policy
(Ruling 7), model family, hyperparameters and calibration (Ruling 8), the `ev_min`
grid (Ruling 9), the cost model (Ruling 5). It may tighten; it may not loosen,
substitute or re-derive, and any departure is a **contract amendment requiring a
human + ChatGPT ruling**, not a registration.

**Correction to an earlier draft.** This requirement previously cited "the ML
Step 4 corrected-run precedent" as the recorded instance of registering after
seeing results. That is backwards: the corrected run is the **counter-example** —
"no tuning and no feedback loop", and the post-audit answers "Was there any tuning
after seeing results? **No**". It is the model of how a re-measurement is done
correctly, and the prereg carries its ceremony verbatim as the invalid-run rule.

**R-2 Split discipline, and the exploratory out-of-sample slice.** **No holdout
exists under this gate** (§7), so the vocabulary is fixed: the tested slice is the
**`EXPLORATORY_OOS_SLICE`**, and the words *holdout*, *validation* and
*out-of-sample evidence* stay reserved to the forward-epoch evaluation (§6).
Calling the exploratory slice "the holdout" is how a scratch number acquires an
evidence name.

- **Chronological only** — the final contiguous portion of the design span, the M1
  precedent's shape. No random split, no shuffled k-fold, no group-shuffle
  anywhere, including any internal early-stopping split.
- **Quarantined from R1 onward.** The boundary is chosen and recorded **before
  stage R1**, and no stage before R4 may read, describe, plot or compute a
  statistic over it — descriptive statistics included.
- **Purge counted in bars, never wall-clock.** ≥ 25 M15 bars (`horizon + 1`) of
  the design span immediately preceding the slice are dropped from training. A
  Friday-afternoon signal bar's 24-bar label reaches into Monday, so a 6h15m
  elapsed-time purge would not purge it. Note this is an **extension**: the frozen
  25 attaches to *role* boundaries, and an intra-span split is a new boundary
  type. Extending it is a tightening and therefore permitted.
- **A trailing edge needs a different, larger number.** If any design puts
  training data *after* a tested slice — walk-forward, rolling origin, repeated
  split — the trailing gap must be ≥ the **longest feature lookback in bars**, not
  `horizon + 1`. Prereg §7 permits H1/H4 completed-bar context, and an ATR-14 on
  H4 reaches 224 M15 bars. The single chronological cut above has no trailing edge
  and is the simplest conforming choice.
- **No statistic may straddle the slice.** Everything fitted is fitted on the
  training portion only and frozen before the slice is read: the per-pair/session
  spread tables, `W̄`/`L̄`, the isotonic calibration (prereg §8: "carved from the
  training span only"), and any scaler or pair encoding. **This is the subtlest
  leakage route in the whole gate**, because the labels themselves depend on cost —
  `TP_dist = max(1.5×ATR, 3.0×cost)`, `SL_dist = max(1.0×ATR, 2.0×cost)`, and the
  eligibility hurdle `1.5×ATR ≥ 2.0×cost` (Ruling 6). A cost table fitted over the
  whole design span means **the labels inside the slice were constructed using the
  slice**. That is target leakage in the strict sense and it is invisible to every
  acausal check. The prereg's "estimated on design data and frozen" was written
  when the whole design span was training; carving a slice out of it turns that
  phrase into a contamination instruction.
- **One split timestamp for all pairs**, since `rho_x` already records that the
  pairs are correlated.
- **Nothing changes after the slice is read** — no feature, threshold, model, cost
  assumption or pair set.

**R-3 M15 aggregation correctness**, on synthetic and reference cases: timestamp
ordering · bucket boundary · OHLC aggregation · duplicate handling ·
missing/rejected observation handling · timezone and epoch binding. Event and
label eligibility requires **`n_source_bars == 15`**, with incomplete buckets
diagnostics-only and **no imputation** (Ruling 3) — partial-bin handling is one of
the recorded defect classes in R-4, so the rule that prevents it belongs here.

**Full production calendar-provenance machinery is not required here** — it is
provenance for evidence authority, not correctness of a conclusion. But the
six-field vocabulary cannot simply be borrowed: **three of PR #444 §5's six
quantities are defined against the approved calendar artifact**, which does not
exist (`PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED`), and PR #448's
D-5.8 forbids inventing the expected slot set from observed data or a
self-generated rule. So under this gate only `observed_source_minute_count`,
`rejected_source_minute_count` and `usable_source_minute_count` are computable;
`expected_source_minute_count`, `absent_source_minute_count` and
`max_unavailable_gap_minutes` are reported as
`NOT_COMPUTABLE_WITHOUT_APPROVED_CALENDAR` and **never estimated**.

The three computable counts are reported **per pair × session × month**, because
eligibility requires a complete bucket and non-uniform missingness therefore thins
the event set non-randomly and biases the spread estimates drawn from the same
data. **Coverage completeness is unverified under this gate**, no exploratory
coverage figure carries certification meaning or may be cited in any later
calendar or admission argument, and R5 carries that as a stated limitation: a
result that varies by period or session may be a coverage artifact.

**R-4 Leakage and bar-integrity controls.** Two families, and **the second is the
one that has actually bitten this programme.**

**(a) Time-direction (acausal) controls.** Forbidden: future bars · target
leakage · centred rolling windows · post-event values · forward-filled future
information · cross-split contamination · any upper-timeframe context bar that is
not **completed** when it is used (prereg §7, "only completed upper bars, no
peek") · probability calibration fitted on anything but a split carved from the
**training** span (Ruling 8).

**(b) Causal-but-wrong controls.** An earlier draft of this requirement listed
only family (a) and cited this repository's history as the argument for it. That
was the wrong way round: **every item in (a) is a time-direction violation, and
the defects recorded here were strictly causal.** They would each pass (a)
unchanged. Three classes, none of them nameable as "leakage":

- **Session discontinuity.** No feature may compute a difference, return, true
  range or rolling statistic *across* a market closure as though the bars were
  adjacent. A `prev_close.shift(1)` that pulls Friday's close at Monday's open is
  causal and still wrong. The committed convention is the ML Step 4 lineage's
  **F8 warm-up guard** — "ATR-14 with `min_periods=14`, **no prev-close fillna**".
- **Bucket completeness.** Applied to context bars as well as to labels: the
  frozen `n_source_bars == 15` rule (R-3), and its analogue on any upper-timeframe
  bin. A partial bin is garbage before it is ever a peek.
- **Warm-up.** Every rolling feature declares its minimum window and enforces it —
  `min_periods` equal to the full window, **never 1** — and the researcher declares
  a single `w_bars` burn-in **≥ the longest feature lookback in the set, including
  H1/H4 context**, with bars inside the burn-in event-ineligible. The committed
  articulation is again the F8 guard and playbook §8's "warm-up burn-in applied
  (W bars event-ineligible)". An ATR computed from a single bar is not leakage in
  any direction; it is simply not an ATR.

**(c) At least one negative control, run and reported — not asserted.** A
prohibition list catches only the defect the author already imagined, and none of
the classes in (b) was on anyone's list before it fired. This is the repository's
own R-1 negative-control rule: `WarmupPolicy`'s docstring records a
`dead_window_loaded: False` field that "asserted the T-1 leakage claim while
measuring nothing". A list of forbidden things is exactly that shape. Minimum: a
**within-fold shuffled-target** run — shuffle `y`, retrain, re-evaluate, and treat
`|shuffled_sharpe| ≥ 0.10` as contamination regardless of every other number — and
a **train/test parity** check.

**On the evidence cited.** The earlier draft's supporting claims — "every positive
Phase-9 result was invalidated" and "the clean baseline came back at Sharpe
−0.189" — are **withdrawn**. The figure is not committed to this repository: it
lives on the unmerged branch `research/post-bug-fix-2026-05-03` and in untracked
local logs, where it is labelled the **M1_V2** baseline, not an M15 one. Even if it
were committed, **C-8 (Ruling 13)** bars any number from a fenced legacy route from
entering this family's design justification or priors, and it was doing exactly
that work here — it was the stated reason R-4 is IN. The defect *classes* in (b)
stand on committed, unfenced authority: the ML Step 4 F8 warm-up guard, the
`min_periods=14` convention pinned across that lineage, prereg §7's completed-bar
rule, and Ruling 3. R-4 needed no fenced numeric to justify it.

**R-5 Cost realism.** Spread, slippage and fees where applicable, using the
committed cost model — `median_spread(pair, session) + 0.3 pip execution padding
+ 0.5 pip cell slippage` — with **both** committed stresses reported: **2× cost**
and **p90 session spread** (prereg §5). Two committed exclusions are part of cost
realism rather than production nicety, because a trade scored in a window where
cost is unmodelled fabricates expectancy: the **rollover window 21:55–22:15 UTC
minimum** and low-liquidity holiday sessions are event-ineligible (Ruling 4;
widen-only). Pip conversion uses the per-pair map with
`global_pip_size_authoritative_for_all_pairs = false` — a 100× JPY pip error is a
recorded invalidation in this programme, not a hypothetical. **A zero-cost result
is never a primary finding**, and every cost claim carries Ruling 5's scope: a
quote-cost-validity claim, not a live-fill claim.

**R-6 Reproducibility.** Code commit SHA · dataset identity · parameters and
config · random seed where applicable · the exact command · an environment
dependency summary. **Byte-level proof is not required here.** Note the recorded
infrastructure caveat: `uv.lock` is stale and `uv sync` against it is destructive,
so the environment summary records what was actually installed.

**R-7 No silent cherry-picking.** Every variant tried is recorded — pairs, models,
thresholds — with the selection rule stated in advance. Reporting only the best
result is forbidden. Recording is disclosure, not control, so three limbs make it
bite:

- **Registered verifiably.** The question, the variant grid and the selection rule
  are committed to the branch **before** the run, and the run record cites that
  registration commit SHA, which must be an ancestor of the run's code SHA (R-6).
  A registration that cannot be shown to predate the result is not one.
- **Counted with a defined unit.** `K` is the number of evaluations whose result
  was **observed**, counted per configuration — pair set × feature set × model ×
  hyperparameters × threshold × split — not per script invocation. Narrowing a
  sweep after reading its output **adds** to `K`; it never resets it.
- **Compared against the right null.** The best result is reported against the
  null expectation for that `K`, never against zero, with the method named. The
  arithmetic is unforgiving: on ~221 weekday UTC days the standard error of an
  annualised Sharpe is ≈ 1.07, so under a true null one configuration clears 0.8
  about 23% of the time, at least one of 20 does so with probability ≈ 99%, and the
  **expected best of 60 configurations is an annualised Sharpe around 2.5 with no
  edge whatsoever**. A best-of-`K` figure without that comparison is not evidence.

Also not reopened: the five selection routes closed as 再試行禁止 in
`phase22_alternatives_postmortem.md` §4.

**R-8 No promotion.** Every result under this gate is
`EXPLORATORY_NON_PROMOTED_RESEARCH_RESULT` and may not be promoted to production
evidence, gate evidence or live readiness. This matches the prereg's own
"results never citable as evidence". R-8 is admitted on the **containment** ground
of §5's second limb, not the correctness ground — see §5.

**R-9 Effective-N, reported and never assumed.** At the frozen 24-bar horizon an
event initiated at every eligible bar overlaps its 23 successors, and PAIRS_20
returns are cross-correlated — so raw trade counts overstate independent evidence,
by up to two orders of magnitude in plausible regimes. Ruling 11 already requires
**both** the raw event count and the effective-N. Every exploratory result reports
both, at portfolio and per-pair granularity, using the committed arithmetic of
`artifacts/m15_gate3a/effective_n_estimator_spec.json` (`APPROVED_SPEC`):
`rho_h = 1 + 23 × overlap_fraction`, `rho_x = 1 + 19 × mean_abs_pairwise_corr`,
`N_eff = Σ(N_raw_pair / rho_h_pair) / rho_x`, with the overlap fractions and the
correlation shown. This costs nothing — the estimator is committed, pure, and
reads no data.

**The floors are not applied.** `RAW_HOLDOUT_TRADE_FLOOR = 1000` and
`N_EFF_HOLDOUT_FLOOR = 400` govern the forward-epoch evaluation; no exploratory
output passes `role="holdout"`, applies either floor, or carries
`SAMPLE_SUFFICIENT` or `INSUFFICIENT_SAMPLE` (§6). Reporting the number is not
applying the threshold. Implementation note: `effective_n()` fails closed outside
`role ∈ {"holdout", "validation"}`, so exploratory use calls the arithmetic
without a verdict rather than inventing a role.

**R-10 Exploratory results may not set the formal contract's free parameters.**
Several quantities family A will freeze are estimated **on the design span** — the
very span this gate opens to search: the per-pair/session spread tables, the EV
gate's `W̄`/`L̄`, the barrier/cost ratio distribution, the final feature list, the
warm-up `W`, and `mean_abs_pairwise_corr`, which the committed estimator spec fixes
as "estimated on DESIGN data only and frozen".

The last is the sharpest case and closes a route neither Ruling 10 nor R-7
catches: `rho_x = 1 + 19 × mean_abs_pairwise_corr` sits in the **denominator** of
`N_eff`, so a variant yielding a lower correlation estimate **raises** `N_eff` and
makes `INSUFFICIENT_SAMPLE` less likely. That disarms a frozen sample floor while
loosening no threshold and while listing every variant honestly. **No quantity
destined to be frozen into the family-A contract may be taken from an exploratory
variant chosen after its results were seen.** Each is either estimated by a rule
registered before the campaign starts, or left entirely to the design audit and
gate 3a, which own it. Exploratory estimates of these quantities are diagnostics
and are labelled as such.

---

## 5. The anti-overengineering test

For every candidate requirement, ask:

> **Absent this, would the research conclusion about whether M15 carries an edge
> be *materially wrong*?**

**Yes** → it belongs in the Minimum Research Gate.
**No**, and it is mainly for evidence promotion, hostile filesystems, arbitrary
attacker input, production deployment or forensic provenance → **defer to the
production gate.**

**A second limb, because one is not enough.** *Absent this, could the exploratory
work damage, contaminate, or later be mistaken for committed evidence?* **Yes →
IN**, whatever the first answer. The first limb screens *correctness* and generates
R-1…R-7, R-9 and R-10. It cannot screen containment: **R-8 fails the first limb
outright** — the conclusion is exactly as right without it — and is in regardless,
because the cost of a wrong *use* of a right conclusion is not recoverable. §3's
safety boundaries are admitted on this limb too, which is why **§5 may never be
cited to strike a §3 boundary**: a missing broker guard would not make the
conclusion wrong, and that is not the test §3 answers to.

**The adversary this gate defends against is the researcher's own optimism and the
data's own defects — not a malicious actor and not a hostile filesystem.** That
sentence, not the question above, is what actually generates the OUT column.

**What OUT does not mean.** Every item marked OUT stays **fully binding wherever it
already binds** — on the gate-3a continuation, the continuation writer and the
committed evidence tree. Nothing here withdraws, narrows or defers PR #444's
D-series or §12, PR #448's rulings, or PR #450 §2. "OUT" means only "not
additionally imposed on a research-scratch route that touches none of those
surfaces".

Applied, with the reasoning stated so it can be checked:

| Requirement | In or out | Why |
| --- | --- | --- |
| Frozen research question (R-1) | **IN** | Registering after results is how a noise result becomes a finding. |
| Leakage controls (R-4), **both families** | **IN** | A leaked feature produces a confident, entirely false edge. And the causal-but-wrong family is the one that actually fired here — an acausal-only list would have caught none of it. |
| Effective-N reporting (R-9) | **IN** | The 24-bar horizon makes raw counts overstate independence by up to two orders of magnitude; a conclusion drawn on raw counts is wrong by that factor. The estimator is committed, pure and reads no data. |
| Contract-parameter contamination control (R-10) | **IN** | One of the design-estimated values sits in the denominator of `N_eff` and mechanically weakens a frozen sample floor. |
| Dead-window and design-bounds check, **by call not assertion** | **IN** | This is a leakage control wearing a provenance label: endpoints cannot exclude an interior bar, and `DEAD_START` is one second after `DESIGN_END`. `no_overlap.assert_design_bounds` / `assert_no_dead_window` are committed, reader-free and free to call. |
| No promotion (R-8) | **IN**, on the containment limb | Fails the correctness limb and is in anyway: an exploratory number entering the evidence tree is not recoverable. |
| Cost realism (R-5) | **IN** | The M1 flagship was gross-negative *and* net-negative; a zero-cost result would have looked publishable. |
| Train/val/holdout separation (R-2) | **IN** | Without it there is no out-of-sample claim at all. |
| Aggregation correctness (R-3) | **IN** | A wrong bucket boundary changes every label and every feature. |
| Reproducibility basics (R-6) | **IN** | An unreproducible positive is not a finding. |
| No cherry-picking (R-7) | **IN** | Selection over 20 pairs × models × thresholds manufactures edges from noise. |
| Byte-level four-limb proof (D-11), **as a proof with tokens** | **OUT** | Protects evidence *authority*, not correctness of a conclusion. The one limb with a correctness function — the dead-window scan — is taken above as a plain call, without the proof apparatus. |
| Candidate → promotion lifecycle | **OUT** | Nothing is promoted under this gate. |
| Reserved-filename impersonation refusal | **OUT** | Hostile-input hardening; the researcher is not the attacker here. |
| Win32 namespace / junction / reparse handling | **OUT** | Hostile-filesystem hardening. |
| Single routing authority, closed-set root | **OUT** | Evidence-surface integrity, not research correctness. |
| Provenance binding to committed authority | **OUT** for exploratory; **IN** as R-6's lightweight record | The conclusion needs to be reproducible, not forensically attributable. |
| `_SCHEMAS` / typed registry separation | **OUT** | Write-permission architecture. |
| Calendar-provenance machinery, complete | **OUT** | But an obvious coverage defect is still a finding (R-3). |

---

## 6. What passing this gate does **not** mean

A `PROMISING` outcome here is **not**: a Gate-3a formal continuation pass · a
production-grade source-audit pass · artifact promotion permission · live or demo
execution permission · P/V reader completion · calendar approval · satisfaction
of the §9 frozen acceptance thresholds · **evidence that T-3 is satisfied** (a
median eligible barrier/cost ratio < 3.0 is a T-3 finding however good the other
metrics look) · the continuation output-surface implementation Work PR · the FR-19
test-safety Work PR · the **fifth** independent source-audit re-check, which has
not been started · forward-epoch adoption · discharge of the prereg's gates 4–9,
which remain "none skippable" for family A.

**The frozen thresholds are not applied to exploratory results.** They govern the
*validation kill gate* and the *one-shot frozen holdout* on the **forward epoch**,
which is not yet adopted. An exploratory result may not be described as having
met or failed them, and the tokens `MEETS` and `DOES_NOT_MEET` are reserved to
that formal evaluation.

**And a `failed` outcome here is not a formal negative either.** This is the
asymmetry an earlier draft left open. The exploratory span is short and the
estimator imprecise — the standard error of an annualised Sharpe on ~221 weekday
UTC days is ≈ 1.07, the same order as the effects being looked for — so power to
detect a real but modest edge is low and **`inconclusive` is a likely honest
outcome**. An exploratory `failed` does **not** close family A, does not discharge
or pre-empt the validation kill gate, does not trigger Ruling 12's family-B branch
(which requires failure of the *formal* kill gate this gate cannot run), and is
not `DOES_NOT_MEET`.

**If M15 research fails**, stopping work on production-grade evidence
infrastructure becomes a live option, and that is the point of sequencing this
gate first — but that is a **human + ChatGPT business decision**, recorded as one,
into which the exploratory result enters as clearly-marked non-evidence background
under C-8. It decides nothing on its own, and it may not be taken on a sample the
design could not have detected an edge in. **If it is promising**, the programme
returns to PR #450 §10's deferred dependencies with a reason to pay for them.

---

## 7. Proposed staged flow

| Stage | Content | Reads real data? |
| --- | --- | --- |
| **R0** | Synthetic correctness: aggregation, label, evaluation harness, leakage controls, on synthetic and reference cases | **No** |
| **R1** | Read-only descriptive survey over an approved local dataset — schema, date span, pair coverage, missingness, descriptive statistics, **the distribution of `barrier_distance / cost` on eligible bars and its median (T-3), the eligible-bar rate per pair and session, and the per-pair × session spread distribution (median / p90 / p95)**. **No training** | Yes — Red, needs Q3 |
| **R2** | Naive and simple baselines — momentum / reversion / a rule with no fitted parameters — trained from scratch, on the **training portion only** | Yes — Red |
| **R3** | M15 model research (the planned LightGBM family), on the **training portion only** | Yes — Red |
| **R4** | Single evaluation on the quarantined `EXPLORATORY_OOS_SLICE` (R-2). **Not** the pre-registered holdout evaluation and **not** conducted under §9's frozen conditions (§6) | Yes — Red |
| **R5** | Decision: **clearly promising** / **inconclusive** / **failed**, on the rule below | — |

**Each Red stage is its own gate.** R1 (first real-data read), R3 (training) and
R4 (evaluation) are each Red under policy §6, and CLAUDE.md forbids chaining
distinct irreversible stages automatically. **A ruling on this packet authorises
none of them**; approval of one does not carry to the next; each stage reports and
stops.

**R0 is available now** and needs no ruling on a Red operation — but it is **not
free and not Green.** It touches M15 aggregation, labels, the cost model and
evaluation paths, all policy §3 protected paths, so the implementing Work PR is
**Amber** and is not self-mergeable; policy §8 forecloses the objection, since
"synthetic-only" describes the test data, not the risk of the code.

**R0 does not authorise a second aggregation implementation.** The committed
machinery in `scripts/m15_gate3a/**` is the aggregation authority even while its
source audit is blocked. A parallel harness built outside it is the same hazard
Q1(a) names for data, now for code — and code is where all four audit rounds found
every defect. If a promising result comes from a harness that aggregates
differently from the committed machinery, it is not a preview of the formal
family; if a failed result does, it may be a bug in the scratch code. If R0 must
aggregate independently, the divergence is declared and the two are cross-checked
on identical synthetic fixtures, with any disagreement a finding rather than a
preference.

**R2 completes and is recorded before R3 begins**, and its comparison is reported
(§10). A baseline run after the model is not a baseline, it is a post-hoc foil.
**No previously-trained or deployed model may be used as the baseline**, and no
model whose training data overlaps the exploratory slice, the dead window or the
consumed `365d_BA` holdout (Ruling 8: from-scratch only, no deployed-model reuse).
No number from a fenced legacy route may serve as the baseline (C-8).

**A zero-data calculation R0 must include, and it may moot Q1 and Q3.** Before any
real-data read is requested, establish from committed numbers alone whether the
frozen sample floors are reachable at all. The inputs are all committed: the M1
flagship fired **8,082 trades over 48 UTC days** (168.4/day portfolio); the prereg
projects the M15 event rate "~15× lower" (≈ 11/day); the turnover cap is ≤ 40
trades/day; the frozen holdout minimum is 2 months (≈ 43 weekday UTC days). Apply
the committed effective-N arithmetic (R-9) across a stated grid of overlap
fractions and mean absolute pairwise correlations, and report the raw count and
holdout length required for `N_eff ≥ 400`. **If the grid shows the floors
unreachable at the frozen horizon, universe and minimum holdout span, that is
reported to human + ChatGPT as a Ruling-10 referral before any real-data read is
authorised** — it would mean family A terminates in `INSUFFICIENT_SAMPLE` whatever
the edge, and no exploratory result could change it. The property that makes M15
attractive over M1 — a ~15× lower event rate — is the same property that pushes
the sample floor away. This calculation reads nothing, costs nothing, and is the
cheapest decisive thing in the whole packet.

**A constraint the committed frame imposes on R4.** The frozen holdout lives on
the **forward epoch**, which §3.1 records as "not yet adopted", and the forward
epoch is `..._ADOPTION_BLOCKED_INSUFFICIENT_SAMPLE_ADOPTION_WAITS`. So the
one-shot frozen holdout **is not available to this gate**, and R4's out-of-sample
evaluation must be an *exploratory* temporal split inside the design span. It
**must not** consume, touch or approach the frozen holdout, and its result is not
a holdout result. Because the holdout's edges do not exist yet, "must not
approach" is unfollowable as an instruction; the operative rule is §3.6's fixed
date ceiling.

**And the exploratory split is out-of-sample for the classifier only.** Under the
committed contract the design span is the **fitting surface** for the cost model,
the EV payoffs and the eligibility hurdle — which is exactly why the frozen frame
puts validation and holdout on a *different epoch*. A slice carved from the design
span shares those fitted quantities with its own test window, so an exploratory
positive is **optimistically biased at the system level even when the classifier's
split is clean**. That is a further reason its result is not a holdout result, and
a further reason the **R2 baseline comparison** is the load-bearing number rather
than the model's absolute metrics: run under the same fitted cost model, the bias
partly cancels in the comparison.

**The R5 decision rule, registered before R1 begins.** R-1 requires stop criteria,
and a three-way verdict with none is the failure R-1 names. These are deliberately
expressed in quantities that are **not** the §9 frozen thresholds, so nothing here
restates, softens or pre-empts them (§6):

- **failed** — the median eligible `barrier_distance / cost` is below **3.0**
  (T-3's own number, adopted here as an exploratory stop because it is the
  condition that makes M15 materially different from the failed M1 cost regime);
  **or** the best slice net-of-cost expectancy is negative with an interval
  excluding zero; **or** the R0 feasibility calculation shows the frozen sample
  floors unreachable.
- **clearly promising** — the best slice net-of-cost expectancy is positive, its
  interval computed on **effective-N** excludes zero, it survives the 2× cost
  stress, it beats the R2 baseline net of cost, and it exceeds the null expectation
  for the campaign's `K` (R-7).
- **inconclusive** — everything else, including every case where effective-N is
  too small to separate the two.

**`failed` may not be returned on a sample the design could not have detected an
edge in.** If the slice does not reach the same order as the frozen floors, the
verdict is `inconclusive`, never `failed`. The floors are not applied as
acceptance thresholds (§6); they are the committed scale reference for what this
programme already judges marginal. `inconclusive` is the expected outcome of a
short exploratory span, is a legitimate result, and is not a reason to extend the
iteration budget.

---

## 8. Questions this gate cannot rule — human + ChatGPT required

Committed authority settles more than expected (§2), but not these. Each is a
genuine research or governance choice, so this packet **stops** rather than
inventing.

**Q1 — the derivation-artifact precondition, and it is the blocking one.** The
prereg makes the exploratory span "usable only after the **§4 derivation artifact**
exists". That artifact is the derived M15 dataset the gate-3a continuation
produces — and the continuation is unauthorised, its output surface's production
dependencies were just deferred (PR #450 §10), and its calendar approval is
outstanding. **So the committed path to exploratory M15 data runs through
machinery this programme has deliberately postponed.**

**Only one of the options below is a reading of the contract; the others are
requests to amend it, and an earlier draft of this packet presented all three as
free choices.** The committed text points hard at (b): prereg §3.1 — "gate 3a must
complete **before any implementation PR reads or derives data**"; prereg §4 — the
design-data M15 aggregate "is a **new derived dataset** and requires a
Gate-P2-style adoption artifact **before any real read**"; playbook §2 stop rules
1 and 2 — refuse and redirect a real read or a real M15 derivation until the
machinery source audit is accepted, which it is not. Under CLAUDE.md's "the
stricter reading of a research restriction wins", (b) is the default and the
others cost an amendment. That is the human's call to make either way — but it
must be made with the price visible.

- **(a) — a contract amendment, not a reading.** Read-only research proceeds on a
  **research-scratch M15 derivation** that is explicitly *not* the §4 artifact —
  non-promoted, non-citable, outside the evidence tree. This unblocks R1–R4 now.
  It requires amending or referring back prereg §3.1, prereg §4 **and** playbook
  §2.1–§2.2, and it creates a second derivation path — the structure that produced
  the same weekend-gap defect independently in two scripts.
- **(b) — the reading the contract supports.** The §4 artifact exists first, so
  R1–R4 wait. But note (d): this is cheaper than it looks.
- **(c) — also a contract amendment.** An existing committed dataset used directly
  at M1 or another timeframe. Prereg §2 forbids a same-data M1 flagship retry and
  admits general M1 "only under a materially new microstructure-grade hypothesis
  and separate protocol"; Ruling 7 makes M1 aggregation input only; and H1/H4 are
  family B under Ruling 12, reachable only after family A fails validation.
- **(d) — derivable, and absent from the earlier draft.** Satisfy what Ruling 1
  actually requires of gate 3a — derivation artifact, forward-epoch artifact,
  inventory, checksums, ts-bounds, derivation and aggregation identity, retention
  binding — plus PR #450 §10 rows **F** and **G**, **without** paying rows A–E,
  because §10's own closing paragraph states those "are **not** preconditions for
  read-only research into whether M15 carries an edge at all". Option (b) as
  originally written overstated the cost and made (a) look more necessary than it
  is.

**What a ruling for (a) or (c) must also do.** Playbook §5 binds any design-span
derivation PR with "only after the source audit (re-check) is **accepted**", and
playbook §6 gates "**ANY** single run" on an adopted forward epoch. A ruling would
have to state that these govern the *production-evidence* path and do not reach a
non-authoritative research derivation — or amend them. This packet does not decide
which, and the stricter reading currently wins.

**Q2 — initial pair set, with the default already against a subset.** Ruling 2
freezes "design 2025-04-25→2026-02-28 (**exploratory only**, never evidence,
**fixed PAIRS_20**)" — PAIRS_20 is pinned to the exploratory role itself, not only
to the formal family — and R-2a bars "inclusion/exclusion decisions **anywhere in
this family**". A subset is also not the multiple-comparison saving it looks like:
what controls selection is registering the set in advance (R-7), not shrinking it,
and **dropping pairs lowers effective-N**, since `N_eff` rises with the number of
contributing pairs. The narrow question is therefore whether an explicitly
registered subset may be used for **cost** reasons without constituting a pair
selection within family A. **Default if unruled: `PAIRS_20`.**

**Q3 — which dataset, and whether reading it may begin.** The OANDA archive
snapshot is committed provenance (20 pairs × 6 timeframes × 10 years, 17.54 GB).
Reading it is a **real-data read** and therefore Red under policy §6 regardless of
being read-only. This gate does not authorise it.

**Q4 — historical period, and only one direction is open.** The design span
2025-04-25 → 2026-02-28 is committed for the exploratory role. The **forward**
direction is not a research choice and is not being asked: 2026-03-01 → 2026-04-24
is the consumed dead window, and anything at or after 2026-04-25 is the forward
epoch that will *become* validation and holdout, so reading it is a
decision-bearing observation of a holdout nobody has adopted (§3.6). The
**backward** direction is a genuine question but is also constrained: earlier data
leaves the adopted epoch and requires `730d_BA` or `3650d_BA`, both explicitly
non-authorised by Ruling 2 — so it would be a **new epoch-adoption decision**, not
a scope choice inside this gate. **Default if unruled: the design span only.**

**Q5 — the exact cost model for exploratory work.** The committed model is
`median_spread(pair, session) + pad_exec + 0.5 pip`. Whether exploratory work uses
it unchanged, or a deliberately pessimistic variant, is a choice — but Ruling 5
makes **both** stresses (2× and p90) mandatory rather than alternatives, so a
pessimistic variant is admissible only as an *additional* stress, never as a
substitute. Note also that the numeric spread tables **do not yet exist** (§2), so
exploratory work must estimate them from the design span itself; under R-10 that
estimate is a diagnostic and does not become the frozen table. **Zero cost is not
among the options.**

**Q6 — initial model family.** LightGBM is the planned family. Whether R2's
baselines must complete before R3 begins is a sequencing choice.

**Q7 — how many research iterations before the exploratory slice is consumed.**
The **rule** is derivable and is recorded here as the fail-closed default; only the
**number** needs a human choice.

*Default, in force unless a ruling raises it:* the `EXPLORATORY_OOS_SLICE` is
consumed at its **first decision-bearing observation** — the frozen contract's own
definition of consumption (prereg §3.2: "consumed at its single authorised
evaluation, **or upon any decision-bearing observation of it**"). Budget **N = 1**:
every R2/R3 iteration happens on the training portion, and the slice is read once,
at R4.

*What is asked:* whether to raise N above 1, to what, and what multiple-comparison
correction applies at that N. **Raising N is a loosening and needs the ruling;
N = 1 needs none.** Leaving Q7 blank is not a third option — an unbounded budget is
the widest reading of what the gate permits, and playbook §2.8 requires the
narrower reading of an ambiguous permission.

**Why this is not a small number.** The design span is not only the exploratory
arena; it is the source of the quantities family A will **freeze** (R-10). So
unbounded design-span search does not merely over-fit an exploratory figure — it
selects the contract family A commits to. Family A then meets the kill gate on the
genuinely disjoint forward epoch and the over-fit is paid for honestly there, but
the currency is scarce: Ruling 12 allows family A, then family B, then a mandatory
programme-level review, with no third family without a new roadmap arc and audit.
Burning family A on a design-span search artefact spends one of two committed
slots.

**Q8 — where exploratory outputs live.** §9 classifies them; the concrete
directory and writer are deliberately not invented here, and §9 now records that
only a Contract Gate-decision may fix them.

**Q9 — does exploratory work consume the C-7 multiple-comparison budget?** Prereg
§12 risk 10 records the budget as "families A then B only; small pre-registered
candidate sets (one horizon, three `ev_min`)". Because validation and the frozen
holdout live on a forward epoch the exploratory stage cannot touch, exploratory
search does not inflate the *formal* family's error rate — **provided** R-10 holds
and no frozen contract value is set from an exploratory variant. On that reading
C-7 bounds only the formal families. The alternative reading is that any search
over family A's own design role counts against C-7. This packet does not choose.

**Q10 — three researcher degrees of freedom sit inside a frozen threshold.**
`daily portfolio Sharpe (ann., UTC-day)` is frozen at ≥ 0.8 and the sampling
convention is fixed, but committed authority nowhere fixes: (i) which timestamp
attributes a trade's PnL to a UTC day — at a 24-bar horizon a 20:00 UTC entry
closes the next UTC day, and entry- versus exit-day attribution changes the series
and its volatility; (ii) the denominator of `daily coverage ≥ 0.60` — calendar
days, weekday UTC days, or days with at least one eligible bar; (iii) the
annualisation factor, where `sqrt(252)` versus `sqrt(365)` moves a Sharpe by ~20%.
Settling these after results are seen is the R-1 failure. This gate does not settle
them; it **refers them back**, which Ruling 10 permits. Meanwhile every reported
Sharpe states which convention it used.

**Q11 — is the frozen Sharpe criterion measurable at the frozen minimum holdout?**
Ruling 2 fixes the holdout minimum at 2 months, ≈ 43 weekday UTC days, where the
SE of an annualised Sharpe is ≈ **2.4**. A true Sharpe of exactly 0.8 would then be
observed above 0.8 roughly half the time. For comparison, the M1 flagship's
−18.91 was unambiguous on 48 days only because it sat ≈ 8 standard errors from
zero. The threshold is not thereby wrong, and this gate neither changes nor
proposes to change it — Ruling 10 forbids loosening. It refers the question back,
because the cheapest place to learn the answer is **before** a real-data read, not
after a one-shot holdout has been consumed.

---

## 9. Output classification

Everything produced under this gate is
**`RESEARCH_SCRATCH_NON_AUTHORITATIVE`**, and separately
`EXPLORATORY_NON_PROMOTED_RESEARCH_RESULT` as a finding.

Normative, if this gate is ruled: such output is kept **separate from the
production evidence tree**; it is **never automatically promoted**; and it
**never overwrites committed evidence**. **This packet invents no directory and no
writer.** If one is needed, its root and identity are fixed by a **separate
Contract Gate-decision, never by a Work PR**: PR #450 §6 reserves "a new output
root, or widening the candidate root" and the derived M15 data output surface to a
Gate-decision, and §2.2 forbids a Work PR adding a derived-data identity for its
own convenience. An earlier draft of this section offered a Work PR the
alternative of "a narrower rule of its own"; that is **withdrawn** — it granted
exactly the authority PR #450 §6 withholds.

Whatever ruling creates the root, it must be a **module constant with no
caller-supplied directory component**, must sit outside `artifacts/m15_gate3a/` and
outside the continuation root, and must reuse no committed artifact identity or
canonical filename. §5's OUT ruling on reserved-filename refusal is honest **only**
under that constraint: with a constant root and no caller-supplied component the
researcher is not the adversary, and without one the Win32 trailing-dot family is a
correctness surface, not merely an attack surface.

**Contract inputs are covered too.** Any cost table, `W̄`/`L̄` payoff estimate,
effective-N input, warm-up `W` or spread statistic produced under this gate is
`RESEARCH_SCRATCH_NON_AUTHORITATIVE` and may not become a frozen contract value
(R-10). A value chosen after seeing exploratory results is not a pre-registered
value.

---

## 10. Metrics to measure

Not acceptance thresholds — **the minimum set that must be reported** for a
conclusion to be interpretable:

Definitions are pinned to committed authority even where no threshold is applied,
so an exploratory number stays comparable with the M1 precedent and with the later
formal run. **Pinning a definition is not applying a threshold.**

**Point estimates.** raw traded-event count · **effective-N, portfolio and
per-pair, with the overlap fractions and correlation used** (R-9) · gross return ·
**net return after costs** · **average net expectancy per trade in pips** — the
committed frame's primary — with the per-pair pip map and
`global_pip_size_authoritative_for_all_pairs = false` recorded · hit rate
(**diagnostic only**: the M1 run recorded 7.83% with avg win +6.38 / avg loss −4.33
pips, so a low hit rate is not itself adverse) · **exit-type counts (TP / SL /
timeout) and timeout share** (T-4, > 60% triggers investigation) · class
frequencies · **annualised daily portfolio Sharpe on UTC-day portfolio sums** —
the convention prereg §9 and the effective-N spec both fix, **not** a per-trade
Sharpe and not a substituted risk-adjusted statistic · **maximum drawdown against
the pinned 10,000-pip fixed notional** (T-5) · daily coverage with its denominator
stated (Q10).

**Uncertainty, mandatory.** Every headline estimate carries a standard error or
interval and the number of observations behind it. For iid daily returns the SE of
an annualised Sharpe on `N` daily observations is ≈ `sqrt(252/N)` — ≈ **1.07** on
the exploratory span's ~221 weekday UTC days, ≈ 1.38 at the 0.60 coverage floor,
and autocorrelation and fat tails make both optimistic. **A Sharpe reported
without that number is not a result.** Per-trade expectancy carries a standard
error computed on the **effective-N**, never the raw count. Because Sharpe at this
span cannot separate 0.8 from 0 at any conventional level, **net expectancy per
trade is the discriminating statistic and daily Sharpe the comparability
statistic** — report both, neither alone.

**Selection exposure, mandatory.** `K` as defined in R-7, reported with the best
result compared against the null expectation for that `K`.

**Stability.** By period, over equal sub-spans whose count is fixed before results
are seen; and by pair, **all pairs shown, not the survivors**, each with its own
trade count and effective-N.

**Cost sensitivity.** Both committed stresses by name: **2 × cost(pair, session)**
and the **p90 session spread** — recorded as unavailable, never silently skipped,
where no session estimate exists.

Reported alongside: every variant tried (R-7), the selection rule, and the
reproducibility record (R-6). **A result reported without its net-of-cost figure is
not a result, and a result that does not name the split it was computed on is not
a result either.**

---

## 11. Non-authorisation

This packet authorises no operation. It permits no real-data read, no dataset
download, no derivation, no training, no inference, no validation, no holdout
evaluation, no execution, no broker or demo activity, no database access, no
network access, and no calendar generation. It adopts no epoch, promotes no
artifact, and grants no source-audit acceptance. It does not authorise the
gate-3a continuation and does not discharge
`PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED`.

Nothing in its preparation used a forbidden operation: no source, test or artifact
change · no real-data read · no `.env` read · no DB · no network, DNS or socket ·
no credential use · no PR merged.

`PRODUCTION_READINESS_NOT_CLAIMED` · `NO_EXECUTION_PERFORMED`.

---

## 12. The internal review, and what it was not allowed to add

Five independent doc-only review roles were run against the first draft —
research methodology, leakage and out-of-sample discipline, execution safety,
statistical evaluation, and governance and minimum scope — each given the source
and the contract and none given another role's conclusions.

**What they found is recorded above**, and the corrections are substantial: an
uncommitted and fenced Sharpe figure doing load-bearing work in R-4; a leakage
list that would have caught **none** of the defects it cited as its own
justification; a false claim that PR #446's audit hook is route-independent; two
contract amendments presented as free readings in Q1; a Work-PR authority in §9
that PR #450 §6 withholds; a missing `pad_exec` value; two dropped rows in a table
presented as complete; and the entire T-1…T-7 gate-4 tightening set omitted from a
packet that quotes the clause anticipating it.

**But a review of a *minimum* gate has its own failure mode, and it is the one this
programme keeps hitting.** The five roles between them proposed roughly fifty
additions. Adopting all of them would have done to this gate exactly what PR #450
had just stopped doing to the continuation contract: deepening indefinitely until
nothing is ever learned about whether the edge exists. **The anti-overengineering
test in §5 applies to the review as well as to the gate.** So the following were
argued for and **declined**, with reasons, rather than silently dropped:

| Declined | Why |
| --- | --- |
| A three-way exploratory split with a `K_confirm` budget proposed at 3 | The number was invented. Q7's `N = 1` default is **derived** from the frozen consumption rule instead, and raising it is the human's call. An AI setting a research budget is the failure this gate exists to avoid. |
| Restating the four-limb proof's BI and DB limbs as gate requirements | Evidence authority, not conclusion correctness. Only the dead-window scan crosses over, and it is taken as a plain committed call, not as a proof with tokens. |
| Per-currency exposure metrics, concurrency caps, disjoint replication | Production risk monitoring. `rho_x` already carries the dependence the edge question needs. |
| A full guarded-envelope specification | §3.5 points at the merged `_gate_p1_inspector` guards and requires reuse or a stated reason. Specifying the envelope here would be designing the implementation inside a gate decision. |
| Adding an exploratory role to `effective_n()` | An Amber source change to a protected path, and out of scope for this task. §4 R-9 calls the arithmetic without a verdict instead. |
| Notebook-execution and temp-file boundaries | No notebooks exist in the tree and no notebook dependency is declared; temp writes are harmless. Generic threat modelling. |

**One disagreement between roles was resolved on the evidence, not by vote.** On
the iteration budget, one role derived `N = 1` from the frozen "decision-bearing
observation" rule and another proposed `K_confirm = 3` as a default. The derived
rule wins: committed authority supplies it, the invented number does not, and
CLAUDE.md makes the stricter reading of a research restriction win. The proposed
structure is retained only as the shape a *raised* budget would have to take.

**One role's supporting claim was wrong and the finding still stands.** Two roles
reported that `−0.189` "appears nowhere in the repository". It does appear — in
untracked local research logs, and at commit `dc15fb6` on the unmerged branch
`research/post-bug-fix-2026-05-03`, where it is labelled the **M1_V2** baseline.
That makes the defect worse rather than better: the figure is not committed to
this repository, it is an **M1** number, and it was being used in an **M15**
document as this programme's own history. The conclusion was adopted; the basis
was corrected.

---

## 13. Completion state

**`M15_MINIMUM_RESEARCH_GATE_PENDING_HUMAN_CHATGPT_RULING`.**

The boundaries (§3), the integrity requirements (§4), the scope test (§5), the
non-implications (§6), the staged flow (§7), the output classification (§9) and
the metric set (§10) are derived from committed authority and are offered as
ruled text.

**Q1 blocks the gate from being useful without a ruling**, and Q2–Q11 are genuine
choices. An AI may not settle them: Q1 in particular decides whether M15 research
can begin before the deferred production dependencies are paid for, which is the
question this gate exists to put — and it now carries the amendment cost of each
option rather than presenting three as free.

**One correction to the earlier draft's own scoping claim.** It said only Q1
blocks. That was wrong by one item: **Q7 blocks R2–R4** and does not block R0–R1,
because ruling those stages with the iteration budget blank grants an unbounded
budget by omission. Q7 now carries a derived fail-closed default, which converts
it from a blocker into an ordinary ruling item.

**The cheapest thing in this packet is also the most decisive.** §7's zero-data
feasibility calculation reads nothing, needs no authorisation beyond R0, and could
establish that the frozen sample floors are unreachable at the frozen horizon,
universe and minimum holdout span — in which case family A terminates in
`INSUFFICIENT_SAMPLE` whatever the edge, and Q1 and Q3 need not be answered at
all. It should be run before any of them is ruled.
