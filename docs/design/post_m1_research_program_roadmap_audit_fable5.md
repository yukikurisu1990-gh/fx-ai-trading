# Fable 5 adversarial audit — Post-M1 research program roadmap (PR #427)

- **Document class:** doc-only adversarial audit of the roadmap merged in
  PR #427. Not an implementation PR, not an execution PR, not a
  selected-family pre-registration. Executes and authorises nothing.
- **Branch:** `docs/fable5-post-m1-roadmap-audit`
- **Base:** master `ed893494d981060c68aeb8c7fecc3852d7340b00` (post PR #427 merge).
- **Method:** adversarial reading of the committed roadmap against the
  committed M1 record (PR #413 audit; PRs #421–#426), the binding tier
  classifications, and the Gate P1/P2 protocols. No code modified, no raw data
  read, no training, no holdout evaluation, no new metrics.

## Statuses

- **Verdict:**
  **`POST_M1_RESEARCH_PROGRAM_ROADMAP_ACCEPTABLE_FOR_SELECTED_FAMILY_PREREGISTRATION`**
  — with **eight binding conditions** (§12) that become mandatory content of
  the selected-family pre-registration PR (gate 3). The roadmap document itself
  does not require rewriting: its open questions anticipated exactly the
  rulings this audit now makes.
- Carried prior: **`M1_FLAGSHIP_FIRST_RUN_QUESTION_CLOSED_FAILED_PREREGISTERED_CRITERIA`**
- Always binding: **`PRODUCTION_READINESS_NOT_CLAIMED`** · **`NO_EXECUTION_PERFORMED`**

Forbidden-label note: this document does not assert `PASS`, `Tier 1`,
`FORMALLY_VERIFIED`, `PRODUCTION_READY`, `M15_AUTHORISED`, `H1_AUTHORISED`,
`H2_STARTED`, `PHASE_C2_STARTED`, `NEW_EPOCH_ADOPTED`, `BYTE_ADMISSIBLE`, or
`MEETS`; those tokens appear only in this prohibition list.

---

## 1. Executive verdict

- **Is the PR #427 roadmap acceptable as the next program-level governance
  record?** Yes — subject to the binding conditions in §12.
- **Too permissive, too narrow, or appropriately conservative?** Appropriately
  conservative in structure (nothing is authorised; every family is behind the
  ten-gate pipeline; the forbidden list is correct). Two spots are *locally*
  too permissive and are tightened by ruling here: the pre-holdout-reuse
  default (§5, ruling R-2) and the absence of a program-level stopping rule
  (§10, condition C-7). One spot is arguably too narrow — "deferred
  indefinitely" for microstructure M1 — and is judged acceptable as written
  (§4).
- **Does it correctly avoid prematurely authorising M15?** Yes. The ranking is
  explicitly a proposal; §11 of the roadmap withholds authorisation past
  gate 2; no family is executable from the roadmap alone.
- **Does it correctly prevent reusing the consumed `365d_BA` holdout?** The
  quarantine statement is correct and broad ("any strategy that … designs
  against the same price window is contaminated"). This audit hardens it into
  an operational rule: **the consumed calendar window (2026-03-01 →
  2026-04-24) is dead for ALL roles, at ALL timeframes, for the next family**
  (ruling R-2b) — closing the residual ambiguity about whether that window
  could reappear inside a future validation or holdout span.
- **Does it correctly separate roadmap → roadmap audit → pre-registration →
  design audit → implementation?** Yes; the ten-gate pipeline is ordered,
  non-skippable, and each gate requires explicit human + ChatGPT approval.
- **Blockers before the selected-family pre-registration PR?** **None that
  require a roadmap rewrite.** The dataset/epoch ruling (R-1/R-2) must be
  resolved **inside or before** gate 3 (condition C-1); it does not block
  opening the gate-3 PR, but blocks *merging* it without the ruling.

## 2. Audit scope

Audited: `docs/design/post_m1_research_program_roadmap_fable5.md` (primary
target) and the shared `post_remediation_t2_ml_step4_roadmap.md` pointer
chain. Context (read, not re-audited): the PR #425 execution report; the
PR #426 post-run audit + diagnosis; the PR #413 trading-logic/profitability
audit; the binding tier classifications of
`research_development_roadmap_post_audit.md`; the PR #360 tabular-evidence
rebase memo (legacy-route traceability-only status); Gate P1 (+Amendment 1)
and Gate P2 records.

## 3. M1 closure fidelity — FAITHFUL, no loopholes found

Verified against the committed record: PR #421 invalidated (PR #422, JPY
pip-scale bug); PR #425 corrected evidence **valid**; corrected outcome
**`DOES_NOT_MEET`**; M1 flagship lineage **closed**; the failure is a failed
classifier, **not** an implementation invalidator (PR #426 §8); same-data M1
flagship retry **forbidden** (roadmap §5 forbidden row + §4.F); general M1
admissible **only** under a materially new microstructure-grade hypothesis
with new data and a separate protocol (roadmap §4.F); `365d_BA` holdout
**consumed and quarantined** (roadmap §6).

Adversarial probe for softening: the roadmap's family A/B definitions were
checked for a disguised M1 re-entry (e.g. "M15 with M1 sub-bar logic" or M1
features inside an M15 label). None found — family A is defined at native M15
bars with M15 labels. **One residual door** existed: the roadmap's open
question 2 (pre-holdout reuse) could, if answered permissively, let the
consumed *calendar window* re-enter a future validation set at a different
timeframe. Closed by ruling R-2b below. With that ruling, no loophole remains.

## 4. Candidate ranking audit

**A-first (M15) — SUSTAINED, with conditions.** The time-to-valid-test
argument survives attack: family A's falsification gate is *validation-first*
(no holdout consumed on failure), the data and tooling exist today, and a
one-year-class span yields ample M15 events (~35k bars/pair-year → thousands
of label events per pair even after abstention). The cost improvement is
real but should not be oversold: ATR-proportional barriers scale roughly with
√timeframe-ratio for volatility, not linearly — the roadmap's "~4–8×" wider
barriers claim is a fair range but the pre-registration must derive the
*actual* expected barrier/spread ratio from design data (condition C-3). The
expected edge source ("continuation/trend persistence at M15") is the weakest
element — it is a hypothesis with mixed archived support (Phase 9.16-era
multi-TF results: small gross, fragile net). That is acceptable *for a
falsification frame* — the family is designed to be cheap to refute — but the
pre-registration must state it as a hypothesis under test, not an expectation
(the roadmap already frames it honestly). **Overconfidence check: the roadmap
is not overconfident** — §5 explicitly plans for A failing its validation gate.

**B-second (H1/H4) — SUSTAINED; do not promote to first.** The cost-headroom
argument for H1-first is real but loses to the sample-size cost: H4 yields
~1.5k bars/pair-year and far fewer independent label events; a one-year-class
epoch cannot power a decisive H4 verdict, and adopting a multi-year epoch
first would put the slowest, highest-friction step (epoch adoption at scale)
on the critical path of the *first* post-M1 test. M15-first gets a valid
accept/refute verdict fastest; H1/H4 inherits its cost model and label
tooling. **Split ruling:** if family B is reached, **H1 and H4 must be split
into separate pre-registered contracts** (different event counts, horizons,
and acceptance floors); the roadmap's grouping is acceptable at program level
only (condition C-6). **Sample-size risk is correctly stated, not overstated:**
the roadmap already inverts it ("the *opposite* risk dominates") and demands a
trade-count lower bound.

**C/D supporting layers — SUSTAINED.** Correctly demoted to conditioning
layers; standalone session/calendar alpha is not supported by the archived
record. Leakage risks acknowledged (regime definitions from design data only;
small pre-registered regime set). Calendar/event correctly blocked pending
point-in-time provenance; family A proceeds without it.

**E/F deferrals — SUSTAINED.** Carry needs data the repo does not have;
microstructure M1 is correctly the only legitimate M1 return path.
**"Deferred indefinitely" is appropriate, not too strong:** it is a statement
about data prerequisites, not a ban — the roadmap explicitly records what a
legitimate return requires. No change needed.

**G/H classifications — SUSTAINED.** Portfolio/pair-selection gated behind a
positive-edge family (allocation cannot create edge — consistent with the
archived Phase 9.13/9.19 record); risk-overlay-only correctly forbidden as
standalone (Phase 9.13 C-1/C-2 precedent: Layer-1-only levers fail).

**Ranking recommendation: KEEP A-FIRST.** No decision table needed — the
decisive axes (falsification speed, sample size, data-in-hand, epoch friction)
all point the same way; a table would restate, not resolve. H1-first is the
registered escalation if A fails honestly.

## 5. Dataset / epoch strategy audit — the highest-risk section

- **Quarantine breadth:** the roadmap's consumed-holdout quarantine is
  correctly broad in *intent* (forbids design/tuning/pair/session/threshold/
  feature selection; extends across timeframes via the "same price window"
  clause). **Hardened by ruling here:**
  - **R-2a (pre-holdout reuse — RULED, safest default):** the `365d_BA`
    pre-holdout span (2025-04-25 → 2026-03-01) **may be used as
    exploratory/design data only** for the next family (any timeframe),
    subject to: (i) results on it are never citable as evidence; (ii) the
    **pair universe is fixed at PAIRS_20 by convention** — no pair inclusion/
    exclusion decisions at design time (this is the concrete channel by which
    the publicly-committed PR #425 per-pair holdout table could otherwise leak
    into "independent" design choices); (iii) all validation and holdout spans
    for the new family are disjoint from and strictly later than (or from a
    separately adopted epoch than) the design span. **Forbidding pre-holdout
    reuse entirely was considered and rejected:** it would push the first
    post-M1 test onto an unadopted multi-year epoch, maximising the slowest
    gate for no leakage benefit — the pre-holdout span never generated
    decision metrics.
  - **R-2b (consumed-window death rule — RULED):** the calendar window
    **2026-03-01 → 2026-04-24 is excluded from every role** (design,
    validation, holdout) **at every timeframe for the next family.** It was
    observed in full detail (per-pair, per-threshold) in committed documents;
    no future span containing it can be treated as unseen.
- **Role definitions:** design / validation / frozen holdout / disjoint
  replication are defined clearly, with chronological ordering, purge/embargo,
  and consumption rules. Adequate.
- **Invalid-run rules:** consistent with the #421→#425 precedent, including
  the critical qualifiers (one-time-per-incident, explicit approval,
  feedback-loop test). Adequate.
- **Accidental authorisation check:** the roadmap does **not** authorise
  `730d_BA`/`3650d_BA` (explicitly "unauthorised here", twice) and adopts no
  epoch. Confirmed clean.
- **Gate-P2-style adoption rule:** present in the roadmap but **not
  positionally enforced** in the ten-gate pipeline — see §8. Condition **C-1**:
  the dataset/epoch ruling (which epoch; how the M15 aggregate is derived,
  checksummed, and inventoried; where the new frozen holdout comes from) must
  be **resolved and human-approved before the gate-3 PR is merged** (it may be
  a section inside gate 3 or a separate prior PR). An M15 dataset derived from
  archived M1 raw data is a *new derived dataset* and requires its own
  inventory/checksum artifact before any real read (condition C-2).
- **Leakage-permitting ambiguity?** With R-2a/R-2b imposed: none found. Not
  blocked.

## 6. Acceptance philosophy audit — sound draft; four tightenings imposed

The draft principles are appropriately conservative in structure (cost-aware
net expectancy primary; mandatory gross/net decomposition; turnover budget by
construction; trade-count lower bound; stressed-cost survival;
validation-first gating; disjoint replication; closed invalidation
vocabulary). Stress-point rulings:

- **`+0.5 pips/trade` draft validation floor:** premature as an absolute
  number — at M15 the right floor depends on the empirical cost model that
  does not exist yet. **Ruling:** the floor must be **cost-relative**, not
  absolute — draft form: *validation net expectancy > 0 under the empirical
  cost model AND gross expectancy ≥ k× modelled all-in cost (k pre-registered,
  suggested 1.5)*. The absolute `+0.5` may be retained as an additional
  sanity floor. (Condition C-4.)
- **Different floors for M15 vs H1/H4:** yes — floors must be set per family
  at its own pre-registration (pips-per-trade economics differ by an order of
  magnitude); the roadmap already implies this; made explicit here.
- **Sharpe threshold now or deferred:** defer the number to gate 3 (correctly
  draft-only in the roadmap); but the *metric definition* (annualised daily
  portfolio Sharpe, UTC-day aggregation) must be frozen at gate 3 exactly as
  in the M1 contract — no metric-definition drift.
- **Turnover budget by timeframe:** yes — per-family budgets (the roadmap's
  10–40/day draft fits M15; H1/H4 budgets will be far lower). Per-family at
  gate 3.
- **Cost-stress form:** **both** — survival at 2× the modelled cost **and** at
  a high-percentile (suggested 90th) session-spread cost. Two different
  failure modes (model error vs regime tails). (Condition C-4.)
- **`INSUFFICIENT_SAMPLE` mandatory for H1/H4:** yes — and also for M15 (an
  abstention-heavy design could produce too few validation events; the verdict
  must exist at every timeframe). (Condition C-5.)
- **Exit-type counts and timeout share as mandatory evidence:** yes —
  mandatory evidence-schema items for every future run, alongside gross/net
  layer decomposition and concurrent-exposure metrics (§10 risk 8).
  (Condition C-5.)

Gameability probe: the principle most open to gaming was the absolute
validation floor (pick a lucky span, clear +0.5, touch holdout). The
cost-relative floor plus stressed-cost survival plus fixed pair universe
closes the cheapest gaming paths. Not blocked; targeted fixes imposed as
conditions on gate 3.

## 7. Source reuse / non-reuse audit — SAFE, one addition

Classifications verified against the committed record: governance/evidence
patterns (ml_step4 manifest/evidence/acceptance, checksum/inventory, scrubber,
protected-evidence guard, per-pair pip authority) — correctly reusable as-is;
feature/label/PnL/metric helpers — correctly reusable **only after per-family
audit** (and the M15/H1-native review is separately conditioned, C-3); old M1
evidence and stage/compare experiments — correctly historical-only, consistent
with the PR #360 rebase memo (legacy tabular routes are traceability-only and
`HALTED_INPUT_UNAVAILABLE`; they cannot silently re-enter as evidence because
every future evidence path must flow through the gate-5/6 audited pipeline
with checksum-verified inputs — the structural guarantee, not just a policy
statement); optimistic legacy PnL routes (pre-F-2), deployed-model machinery,
and invalid backtest routes — correctly forbidden; live/paper runners —
correctly excluded from research evidence.

**Legacy-route reconciliation check (Phase 20–26 / M1-M5-M15 era):** the
binding classifications of `research_development_roadmap_post_audit.md` and
the PR #360 memo already fence these as archived/invalid/traceability-only;
the roadmap does not reopen them. **Addition imposed (condition C-8):** the
gate-3 PR must include a one-paragraph *no-legacy-evidence* declaration — an
explicit statement that no number from the fenced legacy routes enters the new
family's design, priors, or acceptance justification except as archived
context clearly cited as such. This makes the reconciliation obligation
visible at every gate rather than implicit. No silent-evidence path found —
not blocked.

## 8. Decision-gate audit — sufficient, with one structural insertion

The ten gates are correctly ordered and non-skippable; none is redundant
(gates 2/4/6/8 are four *different* adversarial surfaces: program, contract,
source, result — the M1 arc demonstrated each catches distinct defect
classes; notably gate 6's class of bug — INV-1 — slipped past gates 4-era
reviews and was only provably caught post-run, which argues for *more*
pre-run source auditing, not less).

- **Missing gate:** **epoch/dataset adoption**. Imposed as **gate 3a**
  (condition C-1/C-2): a Gate-P2-style adoption artifact (inventory, checksums,
  ts-bounds, derivation script identity for any M1→M15 aggregation, retention
  binding) must exist and be human-approved **before gate 5 (implementation)
  reads anything and before gate 3 merges its epoch-dependent numbers**. It
  may be delivered as a separate PR between gates 2 and 3, or as a
  severable, explicitly-approved section of the gate-3 PR.
- **Empirical spread-model admissibility:** not a separate gate — it is a
  mandatory *section* of gate 3 (model specification + padding policy) whose
  implementation is verified at gates 5–6. A separate gate would add latency
  without a new adversarial surface.
- **Calendar-data provenance:** a separate gate **if and only if** family D
  features are ever activated; family A/B proceed without it. Recorded as a
  conditional gate, not inserted now.
- **Should gate 3 be blocked until the dataset/epoch ruling?** Blocked from
  **merging** without it; not blocked from being drafted (C-1). This keeps the
  critical path short without letting an unruled epoch leak into a merged
  contract.

## 9. Specific open-question rulings

| # | Open question | Ruling |
| --- | --- | --- |
| 1 | Epoch choice | **Must resolve before gate 3 merges** (gate 3a artifact; C-1/C-2) |
| 2 | `365d_BA` pre-holdout reuse | **RULED HERE (R-2a/R-2b):** exploratory design only, fixed PAIRS_20, disjoint later validation/holdout; consumed window dead at all timeframes |
| 3 | M15-first vs H1-first | **RULED HERE:** keep A-first (M15); H1-first rejected on sample-size/epoch-friction grounds; H1/H4 split into separate contracts if reached (C-6) |
| 4 | Empirical spread reliability | **Must resolve before implementation** (spec at gate 3; validated at gates 5–6; quote-vs-fill padding mandatory — §10 risk 4) |
| 5 | Calendar/event data provenance | **Not necessary** for family A/B; conditional gate if D activates |
| 6 | M15/H1 feature builder correctness | **Must resolve before implementation** (native-timeframe review at gates 4–5; value-pinned mixed-scale tests carried over — the INV-1 lesson; C-3) |
| 7 | EV-gate calibration | **Must resolve before gate 3 merges** — the trade-gate mechanism (calibrated-EV vs rank-based) is contract-defining and cannot be deferred to implementation (C-4) |
| 8 | Evidence-schema additions | **Must resolve in gate 3** — exit-type counts, timeout share, gross/net layers, concurrent-exposure metrics mandatory (C-5) |

## 10. Missing risks (not adequately covered by PR #427 — now recorded)

1. **Overlapping-label effective-N:** horizon-h labels on consecutive bars are
   mechanically autocorrelated; row counts overstate independent evidence by
   ~h×. Gate-3 power/sample arguments must use an effective-N estimate, not
   raw row counts. (C-6.)
2. **Cross-pair dependence:** 20 pairs share base currencies and global
   shocks; portfolio Sharpe overstates diversification (archived Phase 9.19:
   "pairs are systemically correlated" — the √K lift never materialised).
   Concentration gates alone do not capture this; gate 3 must state how daily
   aggregation treats it (at minimum: report per-currency exposure).
3. **Non-stationarity:** a single-year design span embeds one regime mix;
   acceptance on it is regime-conditional. Mitigated by disjoint replication
   (already required); gate 3 should state the claim scope accordingly.
4. **Broker-quote vs executable-fill gap:** BA candles are indicative
   top-of-book quotes; real fills degrade under size/volatility. The empirical
   spread model must carry an explicit execution-padding term; results claim
   "quote-cost validity" only. (With C-4's stressed-cost tests.)
5. **Weekend / rollover / holiday effects:** bar-boundary anomalies, wide
   rollover spreads, and thin holiday sessions can dominate M15 cost tails;
   the cost model and event definition must handle them explicitly (exclusion
   windows are a design choice to pre-register, not discover).
6. **Class imbalance at M15:** wider barriers change label class mix; training
   and threshold behaviour must be checked against imbalance (report class
   frequencies as evidence).
7. **Probability calibration:** raw `predict_proba` was uncalibrated in M1;
   any EV gate built on probabilities inherits this (ruled into gate 3 — Q7).
8. **Trade concurrency / exposure aggregation:** multi-hour M15/H1 horizons
   mean overlapping open positions; the M1 machinery never modelled
   concurrent exposure. Evidence must include max concurrent positions and
   per-currency net exposure; the simulator contract must define it. (C-5.)
9. **M1→M15 aggregation alignment:** derived-bar construction (boundary
   convention, DST, partial bars, missing minutes) is a fresh unit-bug surface
   of exactly the INV-1 class. Mitigation: checksummed derivation artifact
   (gate 3a) + value-pinned aggregation tests (JPY + non-JPY) + gate-6 audit.
   (C-2/C-3.)
10. **Multiple-comparison budget:** each family consumes statistical surprise;
    unbounded sequential families on the same design data is a search. **Budget
    imposed:** families A and B are the program's registered budget against
    this data generation; a third family requires a new program-level roadmap
    + audit. (C-7.)
11. **Stopping rule:** **imposed (C-7):** if A fails its validation gate → B
    may proceed (own pre-registration). If B also fails → **program-level
    stop**: mandatory human + ChatGPT program review; no family C, no epoch
    reshuffle, no "one more idea" without a new roadmap arc. A validated
    failure closes its question permanently, exactly as M1's did.
12. **Operator search temptation:** the strongest systemic risk after a clean
    governance record is erosion by small exceptions ("just check the holdout
    once", "just one more threshold"). Standing counter-measures: every
    negative result closes its registered question; consumed data is dead;
    corrected re-measurements require the full #422→#425 ceremony. This audit
    restates them as program invariants.

## 11. Blockers

**None requiring a roadmap rewrite or pre-gate-3 fix PR.** All findings are
imposed as binding conditions on gate 3 (§12). The roadmap's own text remains
the governing program record; this audit's rulings (R-2a, R-2b, ranking) and
conditions (C-1…C-8) bind the next gates.

## 12. Recommendation for next gate

**Merge this audit; proceed to the selected-family pre-registration design PR
(gate 3)** — subject to these **binding conditions**:

- **C-1** Dataset/epoch ruling resolved and human-approved before gate 3
  merges (gate 3a; separate PR or severable approved section).
- **C-2** Any derived M15 dataset gets a Gate-P2-style adoption artifact
  (inventory + checksums + ts-bounds + derivation identity) before any real
  read; `730d_BA`/`3650d_BA` remain unauthorised.
- **C-3** Pre-registration derives the actual barrier/spread ratio from design
  data; feature builders reviewed at native M15; value-pinned mixed-scale
  (JPY + non-JPY) tests carried over to every conversion/aggregation path.
- **C-4** Acceptance floors cost-relative (net > 0 under empirical cost AND
  gross ≥ k× cost, k pre-registered), plus stressed-cost survival at both 2×
  and a high-percentile spread; EV-gate mechanism (incl. calibration) fixed in
  the contract.
- **C-5** Evidence schema adds exit-type counts, timeout share, gross/net
  layers, class frequencies, and concurrency/exposure metrics;
  `INSUFFICIENT_SAMPLE` verdict available at every timeframe.
- **C-6** Sample-power argument uses effective-N (overlap-adjusted); if
  family B is reached, H1 and H4 are separate contracts.
- **C-7** Program budget: families A then B only; both failing triggers a
  mandatory program-level review — no third family without a new roadmap arc.
- **C-8** Gate-3 PR carries an explicit no-legacy-evidence declaration.

**Exact allowed next PR shape:** selected-family pre-registration design PR —
**doc-only**, family A (M15-first cost-hurdle-aware) per the sustained
ranking; must incorporate R-2a/R-2b and C-1…C-8; **no implementation, no
training, no holdout evaluation, no epoch adoption unless separately
authorised via gate 3a, no `730d_BA`, no `3650d_BA`, no Phase C2, no
production claim.**

## 13. Non-authorisation statements

This document does **not**: implement anything; train models; evaluate any
holdout; execute any run; compute new metrics; adopt any epoch; authorise
family A (or any family) beyond permitting the gate-3 *document* to be
drafted; start H2/H3, Phase C2, or M15/H1 implementation; use `730d_BA` or
`3650d_BA`; modify any prior evidence; access Google Drive or R2; or claim
production readiness. The consumed `365d_BA` holdout remains quarantined
(now with the hardened R-2b death rule). Statuses:
`POST_M1_RESEARCH_PROGRAM_ROADMAP_ACCEPTABLE_FOR_SELECTED_FAMILY_PREREGISTRATION`,
`M1_FLAGSHIP_FIRST_RUN_QUESTION_CLOSED_FAILED_PREREGISTERED_CRITERIA`,
`NO_EXECUTION_PERFORMED`, `PRODUCTION_READINESS_NOT_CLAIMED`.
