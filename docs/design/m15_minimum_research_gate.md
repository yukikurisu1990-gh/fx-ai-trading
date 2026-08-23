# M15 Minimum Research Gate — decision packet

**Type.** Gate-decision PR (policy §14.2). **Risk tier.** Amber — doc-only, and
it defines a research boundary.

**Completion state.** One, unchanged:
`M15_MINIMUM_RESEARCH_GATE_PENDING_HUMAN_CHATGPT_RULING`

**Zero-data feasibility disposition** (§0, a carried status — *not* a second
completion state, and not a verdict on family A):
`SAMPLE_FLOOR_REACHABILITY_NOT_DETERMINABLE_WITHOUT_MEASURED_INPUTS` ·
`ZERO_DATA_FEASIBILITY_BEFORE_REAL_DATA`

**Unified referral — RULED** (§8.1, human + ChatGPT):
`Q11_AND_SECTION0_RULED_FREEZE_D_AT_GATE3A_CONTINUATION_BEFORE_DATA` ·
`TWO_MONTH_HOLDOUT_IS_A_MINIMUM_NOT_THE_OPERATIVE_DURATION` ·
`HOLDOUT_DURATION_D_IS_FROZEN_ONCE_AT_GATE3A_CONTINUATION_BEFORE_DATA` ·
`POST_FREEZE_DURATION_RESELECTION_IS_FORBIDDEN_FOR_CURRENT_FAMILY_A` ·
`DURATION_SELECTION_MUST_BE_OUTCOME_BLIND` ·
`Q11_AND_SECTION0_RULED_ON_FREEZE_SEMANTICS`

**Still open after that ruling:**
`EXACT_D_SELECTION_BLOCKED_BY_Q10_AND_REMAINING_DURATION_AUTHORITY` ·
`Q10_NEXT_HUMAN_CHATGPT_RULING_REQUIRED` ·
`GATE3A_CONTINUATION_DATE_NOT_FROZEN_RESIDUAL_AFTER_Q11_SECTION0_RULING` ·
`NR_K_REQUIRES_HUMAN_CHATGPT_RULING_AFTER_Q10` ·
`NR_L_REQUIRES_HUMAN_CHATGPT_RULING` ·
`REGISTERED_DATA_PLAN_REFERENT_AND_CONTENTS_NOT_DETERMINABLE` ·
`NO_GENERAL_CONTRACT_AMENDMENT_PROCEDURE_REGISTERED` ·
`SPAN_SIZING_BASIS_NOT_COMMITTED` ·
`FR_19_OPEN_PRECONDITION_CANDIDATE_FOR_FUTURE_RESEARCH_EXECUTION`

**Historical:** `Q11_AND_SECTION0_PENDING_HUMAN_CHATGPT_RULING` — **SUPERSEDED BY
HUMAN + CHATGPT RULING** (§8.1.0).

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

## 0. Zero-data feasibility — the most upstream question

`ZERO_DATA_FEASIBILITY_BEFORE_REAL_DATA`. Before Q1–Q11 are ruled, a cheaper
question is asked: **using committed authority and no data at all, can M15
Family A ever reach the frozen sample floors?** If it provably could not, every
question below that presupposes a real-data read would not need answering.

**This is a derivation, not a gate.** It advances nothing, appears nowhere in the
playbook's gate order, and passing or failing it changes no research state. It is
arithmetic over committed constants, performed in this document: **no code is
executed, no stage is run, nothing is read.**

### 0.1 The committed quantities

| Quantity | Value | Committed source |
| --- | --- | --- |
| horizon `H` | 24 M15 bars (6 h) | Ruling 6; spec `frozen_parameters.H_m15_bars`; `effective_n.py:51` |
| raw trade floor | ≥ 1,000 holdout trades | prereg §9 H; `effective_n.py:53` |
| effective-N floor | ≥ 400 | prereg §9 H; `effective_n.py:52` |
| turnover ceiling | ≤ 40 trades/day portfolio-wide | prereg §9 H; also binds validation as "the turnover budget" (§9.V, Rulings 9 and 10) |
| pair universe | PAIRS_20 | Ruling 2 / R-2a |
| pair trade concentration | ≤ 0.40 — a **max single-pair share** (`metrics.py:154`) | prereg §9 H |
| `rho_h` | `1 + (H−1) × mean_overlap_fraction` | spec `horizon_overlap_factor` |
| `rho_x` | `1 + (P−1) × mean_abs_pairwise_corr` | spec `cross_pair_discount` |
| `N_eff` | `Σ(N_raw_p / rho_h_p) / rho_x` | spec `portfolio_effective`; `effective_n.py:283–302` |
| holdout span | ≥ 2 months, actual boundaries `[FIXED-AT gate-3a continuation]` — a **minimum**; no committed source states a maximum | Ruling 2; absence of a maximum verified across the prereg, the gate-4 audit, the gate-3a record and the playbook |

**The hinge.** The ceiling and `N_raw` constrain the same variable: the spec
defines `N_raw` as "eligible **traded** events … that **fire an EV-gated trade**",
and `effective_n.py:63–73` pins it against the two strictly larger confusable
counts, noting that feeding either "clears the frozen floors by orders of
magnitude and thereby **disarms `INSUFFICIENT_SAMPLE`**". Were `N_raw` the
eligible-*bar* count, the ceiling would not bind it and none of this would run.

### 0.2 Three inputs are empirical — and that is the result

`mean_overlap_fraction`, `mean_abs_pairwise_corr` and the event rate itself are
**not frozen**.

- The spec ties the correlation to "per-pair **daily PnL** series, estimated on
  **DESIGN data only** and frozen". A daily-PnL series does not exist until a
  strategy has been fitted and run on the design span — **the stages this
  derivation sits upstream of.** The input that most moves the answer is produced
  by the work it is meant to precede.
- `mean_overlap_fraction` is **not** in `frozen_parameters` and, unlike the
  correlation, is not even scoped to design data — on the plain reading it is
  measured on the evaluated role's own realised gaps, making it structurally
  unknowable in advance.
- No committed authority bounds the traded-event rate **from below**; the ceiling
  bounds it only from above.

### 0.3 The decisive arithmetic: the deflator budget

The sharpest zero-data statement available is not a duration but a **budget**. At
the ceiling `R = 40/day` over a 2-month holdout (61 calendar × 5/7 ≈ 43.6 weekday
days), the maximum attainable raw count is `40 × 43.6 = 1,744`, so `N_eff ≥ 400`
requires

> **`(1 + 23·ω) × (1 + 19·c) ≤ 4.36`**

— the *entire* deflation budget, for both effects combined, at the frozen minimum
span and the maximum permitted rate. Equivalently: `c ≤ 0.177` when `ω = 0`, or
`ω ≤ 0.146` when `c = 0`. (Using gate 4's "~43 trading days" the budget is 4.30,
`c ≤ 0.174`, `ω ≤ 0.144`.)

**That budget is easily exceeded by ordinary trade arrival alone.** Under a
Poisson process at exactly the ceiling, `mean_overlap_fraction = 0.213` and
`rho_h = 5.90` — which **exceeds the whole 4.36 budget on its own**, giving
`N_eff = 296 < 400` even at zero cross-pair correlation. So a 2-month holdout at
the ceiling is infeasible under Poisson arrivals **at any correlation whatever**.

This is gate 4's already-recorded "intentionally demanding but narrow" corridor,
quantified.

### 0.4 Three corrections to earlier, more confident versions of this derivation

**(a) The turnover ceiling does not force `rho_h = 1`.** An earlier draft argued
that ≤ 40 trades/day over 20 pairs gives a mean same-pair gap of 48 bars against a
24-bar horizon, so `rho_h = 1` exactly. That computes `φ(mean gap)`; the spec asks
for the **mean of the overlap fraction** "estimated per pair from the realised
inter-event gaps". `φ` is convex, so by Jensen `E[φ(g)] ≥ φ(E[g])` — the mean-gap
argument bounds the mean overlap only from **below**, and that bound is vacuous
whenever the mean gap exceeds the horizon. `rho_h = 1` holds **iff no same-pair
trade ever fires within 6 hours of the previous one**, which is a claim about the
realised process, not a consequence of a rate ceiling. **Withdrawn.**

**(b) The ceiling is a holdout *mean*, so it bounds `rho_h` not at all.**
`turnover()` is `n_trades / n_trading_days` (`metrics.py:120`) — a portfolio
average over the span, not a per-day cap. A mean-only constraint admits arbitrary
clustering: `sup rho_h = 24`. Two trades an hour apart on one pair inside a London
session is not exotic and yields `rho_h ≈ 10.6` at exactly the frozen ceiling.

**(c) The concentration cap admits far worse than one hot pair, and accrual is
not monotone in concentration.** `≤ 0.40` bounds the *largest* pair's share, so
several pairs may sit near it. Under regular arrivals: one pair at 16/day with the
other 19 at 1.26/day accrues `Σ N_eff_pair = 24.9/day` — but **three pairs at
13.33/day each (share 0.333, equally legal) accrue 2.34/day**, roughly 10× worse,
because every active pair crosses the overlap threshold at once. An internal
review put this corner at ~4.3 years by applying `P = 20` to a three-pair
allocation; `P` is the *contributing* count, so recomputed consistently it is
~1.1 years. **Neither the 24.9/day figure nor the 4.3-year figure is adopted.**

### 0.5 The "3.3 years" figure — and why rejecting it was wrong

The figure appears **nowhere** in the repository: `3.3 year`, `33,500` and
`838 trading` return zero hits across `docs/`, `artifacts/` and `scripts/`.

Its arithmetic reproduces exactly: `ω = 0.5 → rho_h = 12.5`, `c = 0.3 → rho_x =
6.7`, `400 × 12.5 × 6.7 = 33,500` trades, `÷ 40/day = 838` weekday days ≈ 3.32
years.

An earlier version of this section **rejected** it on the ground that `ω = 0.5`
requires 8 trades/pair/day — 160/day portfolio-wide, four times the ceiling.
**That rejection was wrong, and the reason matters more than the figure.** It
holds only under regular arrivals. At exactly the frozen ceiling, `ω = 0.5` is
reached by one clustered doublet per pair per day — and, decisively, it is what
**the pre-registration's own draft estimator** yields. Prereg §9:

> Draft estimator (for the design audit to fix): block-adjust by horizon (events
> per pair thinned by **mean overlap factor ≈ horizon/mean inter-event gap**)

At the ceiling that is `24/48 = 0.5`, hence `rho_h = 12.5` — the inherited premise
exactly. **So the 3.3-year figure is the frozen turnover ceiling fed through a
committed formula, not an out-of-contract assumption.**

The APPROVED spec supersedes the draft under T-6, and the spec's arithmetic is
what `INSUFFICIENT_SAMPLE` is computed from. But **the two committed formulas
disagree by 12.5× in `rho_h` at the frozen ceiling**, and an earlier version of
this section resolved that disagreement silently, in the direction that makes the
family look feasible. The divergence is recorded here as an open item, not
resolved: `DRAFT_AND_APPROVED_OVERLAP_ESTIMATORS_DIVERGE_AT_THE_FROZEN_CEILING`.

### 0.6 Two estimator routes that raise `N_eff` without breaking any rule

Both go **around** `effective_n()`, not through it — its internal hardening
(`count_quantity` pinning, per-pair rather than scalar-collapsed computation,
canonical pair identity, the frozen-horizon check) is real, and I found no way
past any of it.

**(a) `P` is caller-supplied, and a smaller universe is *faster* to the floors.**
The spec says `P = number of pairs **contributing**`; `effective_n.py:280` takes
`n_pairs = len(records)` with only an upper bound. Under a fixed portfolio
turnover budget the numerator is capped at 40/day regardless of how many pairs
share it, while `rho_x = 1 + (P−1)·c` falls as `P` falls. At the ceiling and
corr 0.3, with every pair below the overlap threshold:

| `P` | rate/pair | `rho_x` | `N_eff`/day | weekday days to the floors |
| --- | --- | --- | --- | --- |
| 20 | 2.00 | 6.70 | 5.97 | 67 |
| 12 | 3.33 | 4.30 | 9.30 | 43 |
| **10** | **4.00** | **3.70** | **10.81** | **37** |
| 9 | 4.44 | 3.40 | 3.57 | 112 |
| 5 | 8.00 | 2.20 | 1.45 | 275 |

**The fastest route to the sample floors *through the estimator* is ten
contributing pairs, not twenty** — 45% off the required span, at a 0.100 share,
far inside the 0.40 cap — until `P = 9` pushes each pair over the 4/day overlap
threshold and the gain reverses sharply. **The contract offers no such route:**
Ruling 2 / R-2a fix the universe at PAIRS_20 and bar "inclusion/exclusion
decisions anywhere in this family". NR-K is therefore a defect in the
**estimator's caller contract**, not a permitted pair-universe remedy, and it must
not be merged with the duration limb (§8.1.8). Separately, a pair that fired no trades adds nothing to the numerator
while raising `rho_x`, so simply *omitting* it is a free gain. Nothing pins `P`
to `PAIRS_20`, and nothing ties the `P` used for `rho_x` to the pair set the
concentration cap is computed over.

**(b) `mean_abs_pairwise_corr` has no production rule and no defined freeze
point.** The spec fixes the symbol and the span and nothing else — not which
strategy's PnL, not whether idle pair-days enter the series, not the correlation
method, not entry- versus exit-day attribution (the same ambiguity Q10(i) records
for the Sharpe series, on the same daily series), not the minimum observations
behind the estimate. The same artifact asserts
`no_strategy_metrics_computed_at_gate3a: true` while defining the quantity on
per-pair **daily PnL**, which is a strategy metric — so the freeze point is
undefined and whoever computes it first sets it. And a daily correlation is the
wrong resolution for a 6-hour horizon: at the projected ~0.56 trades/pair/day most
pair-days are idle, and idle days pull `|corr|` toward zero, so the estimator
**understates dependence most in exactly the sparse regime this family expects**.
`PAIRS_20` also draws 40 currency legs from 8 currencies, so 88 of its 190
pair-pairs share a leg and a single scalar mean cannot carry that block structure.

Two referrals follow, in the playbook's register format:

| Referral | Disposition | Basis |
| --- | --- | --- |
| **NR-K** — `P` in `rho_x` is caller-controlled and is not pinned to `PAIRS_20` | `MUST_RESOLVE_BEFORE_ANY_EFFECTIVE_N_VERDICT` | Omitting zero-trade or tail pairs raises `N_eff` at no numerator cost and can flip the verdict with both the raw floor and the 0.40 cap satisfied |
| **NR-L** — `mean_abs_pairwise_corr` has no production rule and no freeze point | `MUST_RESOLVE_BEFORE_ANY_EFFECTIVE_N_VERDICT` | Method, idle-day handling, day attribution, minimum observations and the freeze gate are all unpinned, and the value sits in the denominator that decides `INSUFFICIENT_SAMPLE` |

Accordingly §12's earlier remark that "`rho_x` already carries the dependence the
edge question needs" is **withdrawn as unestablished**.

### 0.7 Verdict

**`SAMPLE_FLOOR_REACHABILITY_NOT_DETERMINABLE_WITHOUT_MEASURED_INPUTS`.** Of the
three dispositions this exercise could return, the answer is the third — and
**neither** of the other two is provable.

- **`STRUCTURALLY_INFEASIBLE` is not established.** A proof would need a
  committed lower bound on `mean_abs_pairwise_corr` and on `mean_overlap_fraction`
  — no committed source supplies either — and a committed **maximum** holdout span
  to rule a required duration out, where only a minimum exists. That is the whole
  of the argument. It is **not** a claim that a required duration is reachable:
  "adoption waits" fixes *when* adoption may happen, not that accrual continues or
  that the programme waits. Family A survives on zero-data grounds because
  infeasibility is unproven, not because a long enough holdout is available.
- **`STRUCTURALLY_FEASIBLE` is not established either, and this packet does not
  assert it.** What is established is narrower: the frozen criteria set is **not
  self-contradictory** — a non-empty satisfying region exists. That is a fact
  about the criteria, not about M15.
- **Three inputs are empirical, not two**, and an earlier version of this section
  declared the first of them settled at 1.00, which is the error the rest
  inherited: `mean_overlap_fraction`, `mean_abs_pairwise_corr`, and the realised
  event rate at each registered `ev_min`.
- **Missing authorities, named:** `EVENT_RATE_NOT_COMMITTED` ·
  `MEAN_OVERLAP_FRACTION_NOT_FROZEN_AND_ROLE_MEASURED` ·
  `MEAN_ABS_PAIRWISE_CORR_NOT_YET_ESTIMATED_DESIGN_DATA_ONLY` ·
  `DRAFT_AND_APPROVED_OVERLAP_ESTIMATORS_DIVERGE_AT_THE_FROZEN_CEILING` · NR-K ·
  NR-L.

**So this calculation does not moot Q1 or Q3.** An honest grid spans roughly 25
weekday days to over a decade, and a range that wide decides nothing. The hope
recorded earlier in this packet — that the zero-data calculation might be
"decisive" and make the real-data questions unnecessary — is **withdrawn**.

**What it does establish is worth keeping, and it runs the other way.** It refutes
the *reverse* claim, that the floors are comfortably reachable at the frozen
minimum: §0.3's budget is 4.36 and an ordinary Poisson arrival process spends 5.90
on its own, and at the prereg's own projected ~11/day the **raw** floor alone needs
≈4.1 months before any deflator is applied. **The frozen 2-month minimum is very
likely the wrong span** — which is what gate 4 said, and why it directed gate 3a to
size the holdout generously. And it converts the open question into the one a
human can actually rule on: *for each corner of the grid, what forward-accrual
date does `T_h` imply?* The committed record already places the earliest feasible
forward adoption at ≈ 2026-10 on a ~5-month requirement, so a central case of
~11 months of holdout puts `T_h` in mid-2027, and a 2.4-year holdout puts it near
the end of 2028. A long holdout is permitted; it is simply not free, and the price
is calendar time this packet should quote rather than elide.

**And what it cannot address at all.** The floors count **events, not
information**: at `ev_min = 0.0` a trade with `EV = +0.001` pip clears them
exactly as one with `EV = +2` pips does, and neither the spec nor `effective_n()`
weights by signal. "The frozen floors are reachable" is therefore not "the design
can detect an edge", and §7's R5 rule — "`failed` may not be returned on a sample
the design could not have detected an edge in" — reaches for a power calculation
the `N_eff` floors do not supply. Nothing here bears on whether an edge exists, in
either direction.

**This re-derives a committed note, it does not discover a constraint.** Gate 4
already computed the same corridor and already ruled on it: "with turnover ≤
40/day and ≥ 1,000 holdout trades, a 2-month holdout (~43 trading days) gives a
feasible corridor of [1,000 … ~1,720] trades — intentionally demanding but
narrow. **Gate 3a should prefer a holdout longer than the 2-month minimum when
accrued data allows**", and "a false rejection into `INSUFFICIENT_SAMPLE` is
**recoverable by adopting more forward data — acceptable by design**".

**Two scope caveats on every duration here.** They are **holdout-only**: prereg
§3.1 requires validation ≥ 3 months ahead of the holdout and §3.2 an embargo of ≥
25 M15 bars at the boundary, so the forward-epoch calendar requirement is
`3 months + embargo + D`, against an earliest feasible adoption of ≈ 2026-10. And
they price only the **holdout** leg: the spec's validation limb refers to "the
family's minimum" with no antecedent, and `effective_n.py` fails closed to
`NOT_EVALUATED_AT_THIS_ROLE` rather than inheriting the holdout floor. If a
validation floor is ever set at parity the requirement roughly doubles. That is an
open Ruling-11 referral, not a gap this derivation may fill.

### 0.8 What a negative result could and could not mean

Stated **in advance**, so a finding cannot later be read as an argument for
relaxation.

**It could not close Family A.** Prereg §1 closes the family on sample grounds
only for an `INSUFFICIENT_SAMPLE` "**that cannot be remedied by the registered
data plan**" — but that clause sits under the heading "**What closes the family
before any holdout touch**", so it governs a *pre-holdout* verdict only, and "the
registered data plan" is undefined (§8.1.4). An earlier version of this sentence
said "the registered plan *contains* the remedy"; that is **withdrawn** as
unsupported. On a holdout-role verdict the contract is simply silent — it neither
closes family A nor keeps it open. Demonstrating
unreachability at the frozen minimum establishes that **the minimum is the wrong
span**, not that no admissible span exists. Irremediability would require showing
that no holdout length reachable by forward accrual clears the floors — a far
stronger claim this arithmetic does not attempt. A family disposition is never
self-granted in any case.

**The admissible responses are exactly two:** a holdout longer than the frozen
minimum — a preference gate 4 recorded **non-bindingly**, outside its T-list, and
which the frozen pre-registration does not express at all; or a human + ChatGPT
ruling on Family
A's continuation or scope. **Lowering the raw or effective-N floors, and raising
the ≤ 40/day ceiling, are not among them** — Ruling 10 forbids loosening, and the
ceiling was considered and settled by gate 4, which recorded that it "is a budget,
**not a target**".

**And infeasibility may not be demonstrated by assuming operation at the
minimum.** Ruling 2 fixes a floor, not a duration, and `T_h` is `[FIXED-AT gate-3a
continuation]`. Every quantity computed at 43.6 weekday days in §0 and in Q11 is a
**conditional arithmetic identity at the floor**, never a property of the holdout
family A will actually be evaluated on. A minimum is a budget, not a target — in
the same sense, and for the same reason, as the ≤ 40/day ceiling.

**Feasibility may not be demonstrated by assuming operation at the ceiling.**
Every rate here is a conditional arithmetic identity, never a design target — and
the ceiling is an outcome, not a dial: Ruling 9 selects the operating point by
validation net expectancy subject to the budget, so nothing pushes the rate toward
40/day.

**And a reachable result authorises nothing.** It does not discharge Q1 or Q3,
does not permit a real-data read, does not shorten the forward-epoch WAIT or the
≈ 2026-10 earliest-accrual record, and does not discharge
`PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED`. The symmetry is
deliberate: an unstated positive branch is where "feasible" gets read as
"proceed".

**`INSUFFICIENT_SAMPLE` is reserved and is not emitted here.** It is a *measured*
verdict of `effective_n()` at `role ∈ {validation, holdout}`; §4 R-9 and §6
reserve it, and a zero-data derivation cannot produce one. No token proposed by
this section contains it, `FAILED`, or `FAMILY_A`.

**Duration is not a free variable either.** Because "adopt more forward data" is a
pre-blessed remedy, "we need a longer holdout" could otherwise be invoked after
seeing a short one fail — a power calculation performed after the result, which
R-1 names as the failure mode. So: the span is **fixed at forward-epoch adoption,
before any validation or holdout computation**, together with the (rate, overlap,
correlation) assumption used to size it; prereg §3.2 already bars in-flight
extension, since the holdout is consumed "upon any decision-bearing observation of
it"; and re-running this grid after any real-data observation is a **post-hoc
power calculation**, recordable as a diagnostic and referable, never citable as
authority to extend.

**Conditionality disclosed.** Durations are in weekday UTC days — a convention
Q10 refers back as unfixed — and the arrival processes named here (regular,
Poisson, clustered doublet) are **modelling references, not committed authority**.
The "~43 trading days" figure is gate 4's. The 96-buckets/day figure is an
arithmetic ceiling, not an eligible-slot count: Ruling 4's rollover exclusion
removes at least two buckets and the holiday calendar is `[FIXED-AT design audit]`
and unfixed. No expected slot set is inferred from data or a self-generated rule
(§4 R-3).

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

**Three further levers, added after §0's derivation exposed them.**

- **The event rate.** §0 makes the traded-event rate the single unfrozen quantity
  governing whether a frozen sample floor is reached. Choosing an `ev_min`
  operating point, a variant or a threshold **in order to raise the event rate so
  a floor clears** is this requirement's own route applied to a different
  quantity: it disarms a frozen floor while loosening no threshold and while
  listing every variant honestly. Ruling 9's selection metric — validation net
  expectancy subject to the turnover budget — is not substitutable by trade count,
  and no feasibility corridor may become an input to `ev_min` selection.
- **The reported pair count `P`.** `rho_x = 1 + (P−1)·c` takes `P` from the
  caller, and §0.6 measures the effect: under a fixed turnover budget a smaller
  reported universe reaches the floors *faster*, and omitting a pair that fired no
  trades is a free gain. `P` is reported over the full `PAIRS_20` universe,
  including pairs that fired nothing; the pair set used for `P`, the pair set the
  concentration cap is computed over, and `PAIRS_20` are reported together and
  must be the same twenty.
- **The holdout duration `D` (`T_h`).** It is a formal-contract free parameter
  `[FIXED-AT gate-3a continuation]`, and the only one that moves **both** frozen
  sample criteria at once — `N_eff` grows with the span while the annualised-Sharpe
  standard error falls as `1/√D`. It is also the parameter **this gate is most
  likely to set by accident**, because the only inputs a sizing calculation has —
  the traded-event rate, `mean_overlap_fraction` and `mean_abs_pairwise_corr` — are
  the design-span estimates this requirement already governs. **No duration may be
  derived from an exploratory estimate chosen after that estimate's result was
  seen.** Under this requirement's second branch `D` is left entirely to the
  gate-3a continuation, which owns it. Two of those three inputs are measured on
  the evaluated role itself, so the sizing input is a **declared assumption, never
  a measurement** (§8.1.3).

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

**A zero-data calculation R0 must include — and §0 has now performed it.** §0 is
the authority for what follows; the paragraph below is retained because it
specifies the *stage* obligation, but its earlier claim that the calculation "may
moot Q1 and Q3" is **withdrawn** (§0.7): the honest grid spans roughly 25 weekday
days to over a decade and therefore decides neither question. Before any
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
authorised**. What such a finding would and would not mean is fixed in advance at
§0.8: it could **not** close family A, because prereg §1 closes on sample grounds
only for an `INSUFFICIENT_SAMPLE` "that cannot be remedied by the registered data
plan" and the registered plan contains the remedy. A lower event rate is one of the
four mechanisms prereg §1 lists for preferring M15, and it is also the mechanism
that moves a fixed trade-count floor further away; recording that tension is a
statement about the interaction of two frozen criteria, **not evidence about
whether M15 carries an edge**. This calculation reads nothing and costs nothing.

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
and the effect of pair count on effective-N **depends on what is held fixed — and
under a fixed turnover budget the committed estimator rewards a *smaller*
universe**. An earlier version of this packet asserted that "dropping pairs lowers
effective-N, since `N_eff` rises with the number of contributing pairs"; that is
**withdrawn as backwards**. It holds only with per-pair counts fixed. With the
*portfolio total* fixed — the regime the ≤ 40 trades/day ceiling creates — the
numerator is capped regardless of how many pairs share it while
`rho_x = 1 + (P−1)·c` falls with `P`: at the ceiling and corr 0.3 the frozen floors
are reached in 67 weekday days at `P = 20` and **37 at `P = 10`**, reversing only
below `P = 10` when each pair crosses the overlap threshold (§0.6). Dropping pairs
is an effective-N **inflation** route, so the case against a subset rests on R-2a
and R-7 alone, never on an arithmetic penalty that does not exist. The narrow question is therefore whether an explicitly
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
over family A's own design role counts against C-7.

**Default if unruled, per playbook §2.8:** exploratory search over family A's own
design role **does** count against the C-7 budget. Where what a gate permits is
ambiguous the narrower reading governs until a ruling adopts the wider one —
exactly as Q7's `N = 1` does. An earlier version of this packet said only that it
"does not choose", which left the wider reading in force by omission.

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

**Q11 — at what holdout length does the frozen Sharpe criterion discriminate,
must the adopted span reach it, and when is that span fixed?** **RULED together
with §0 as one referral — see §8.1**, which carries the ruling. In summary: the
two-month value is a **floor**, `D` is frozen **once at the Gate-3a continuation
boundary before any data**, and post-freeze reselection is forbidden. The **exact
numeric `D` is not ruled** and is blocked by Q10. The text below is the material
the ruling was taken on.

An earlier version asked whether the criterion is "measurable at the frozen
**minimum** holdout". That heading embedded the conflation the referral exists to
expose: the minimum is a floor on *adoption*, not the span the criterion will be
evaluated on. It is also the mirror of an error §0.8 already guards against for
the ceiling.

Ruling 2 fixes a holdout **minimum** of 2 months (≈ 43.6 weekday UTC days) and no
maximum; at that floor the SE of an annualised Sharpe is ≈ **2.4** — a figure
insensitive to Q10(iii)'s unfixed annualisation, since the day count moves with the
factor, and equivalent to `SE ≈ 1/√(holdout in years)`. It is a **best case**: at
Q10(ii)'s 0.60 coverage floor it is ≈ **3.10**, and positive lag-1 autocorrelation
— structurally expected in a continuation family whose 6-hour horizon straddles the
UTC-day boundary on ~25% of trades — inflates it further. Fat tails do not: at a
per-period Sharpe of 0.05 the skew and kurtosis terms move it under 3%.

At that floor a **no-edge** strategy is observed at Sharpe ≥ 0.8 about **37%** of
the time. (The companion figure — a target-edge strategy observed there ~50% of
the time — is **invariant in `D`** and is not a fact about the minimum; see
§8.1.5a.) For comparison, the M1 flagship's −18.91 was unambiguous on 48 days only
because it sat ≈ 8 standard errors from zero.

**The threshold is not in question.** Ruling 10 forbids loosening and this gate
neither changes nor proposes to change it. **Nor is a duration an acceptance
proof.** And unlike §0's limb, **this one has no verdict**: `INSUFFICIENT_SAMPLE`
is defined only on raw and effective counts, so an imprecise Sharpe on a
contract-compliant span yields an ordinary pass/fail. What is referred is `D`, the
α it is judged at — no error rate is committed anywhere — and the point at which
`D` is fixed. §8.1 carries the authority, the options and the recommendation.


---

### 8.1 Q11 + §0 — RULED. Holdout-duration freeze semantics

**`Q11_AND_SECTION0_RULED_FREEZE_D_AT_GATE3A_CONTINUATION_BEFORE_DATA`** ·
`Q11_AND_SECTION0_ARE_ONE_REFERRAL`

**Status change.** `Q11_AND_SECTION0_PENDING_HUMAN_CHATGPT_RULING` is
**HISTORICAL — SUPERSEDED BY HUMAN + CHATGPT RULING**, recorded here rather than
deleted. §8.1.1–§8.1.6 below are the material the ruling was taken on and are
retained as supporting record; §8.1.7's option set is likewise historical.

#### 8.1.0 The ruling, as recorded

A human + ChatGPT ruling has been received on the unified Q11 + §0 referral and is
recorded here as **authority**. Three limbs.

**Ruling A — the two-month value is a floor, not the operative duration.**
The committed `holdout ≥ 2 months` is a lower bound. It is **not**
`holdout = 2 months`, and no part of this packet — §0, Q11, sample feasibility or
Sharpe measurability — may be reasoned as though it were.
**`TWO_MONTH_HOLDOUT_IS_A_MINIMUM_NOT_THE_OPERATIVE_DURATION`.**

**Ruling B — the exact `D` is frozen once, at the Gate-3a continuation boundary,
before data.** Option B of §8.1.7 is adopted. The freeze precedes, at minimum,
every one of: validation data observation · holdout data observation · empirical
`N_eff` · empirical overlap · empirical pair correlation · Sharpe · returns · hit
rate · signal strength · **any** model-performance outcome. Because validation and
the holdout share one forward epoch, *"just before the holdout is read"* is **too
late**; the freeze is at the continuation boundary.
**`HOLDOUT_DURATION_D_IS_FROZEN_ONCE_AT_GATE3A_CONTINUATION_BEFORE_DATA`.**

**Ruling C — no post-freeze reselection.** After the freeze, `D` may not be
extended, shortened, reselected, rerolled or replaced. Specifically forbidden:
lengthening on seeing `N_eff` fall short · lengthening on seeing sample counts ·
changing on seeing correlation · changing on seeing Sharpe · lengthening on
negative performance · shortening on promising performance. **An
insufficient-sample outcome at the frozen `D` is accepted as the result.** A
different `D` is not a remedy and not a retry:
**`NEW_EXPLICIT_PREREGISTRATION_OR_CONTRACT_DECISION_REQUIRED`.**
**`POST_FREEZE_DURATION_RESELECTION_IS_FORBIDDEN_FOR_CURRENT_FAMILY_A`.**

**Normative wording.** `HOLDOUT_DURATION_IS_A_MINIMUM_PLUS_A_SINGLE_PRE_DATA_FREEZE`

> The committed two-month value is a **lower bound, not the operative holdout
> duration**. The exact holdout duration `D` **SHALL** be fixed **once**, at the
> Gate-3a continuation boundary, **before** validation or holdout data, empirical
> sample quantities, correlation estimates, or research-performance outcomes are
> observed. Once fixed for Family A, `D` **SHALL NOT** be extended, shortened,
> reselected or rerun in response to measured sample sufficiency or research
> outcomes. Selecting a different `D` after the freeze requires a new explicit
> pre-registration or contract decision.

**Governing principle.** **`DURATION_SELECTION_MUST_BE_OUTCOME_BLIND`.** The
purpose of the ruling is singular: the span may not be chosen, or re-chosen, in
the light of what the data turned out to say.

**And the closure clause is not a remedy.** The prereg's "cannot be remedied by
the registered data plan" **may not** be read as authorising an unregistered
duration extension. Committed text registers no extension rule, so there is: no
automatic extension remedy, no post-hoc remedy triggered by measured
insufficiency, and no open-ended "keep extending until `N_eff` passes". The
earlier phrasing "the registered data plan *contains* the remedy" is withdrawn and
is not current authority (§8.1.4).

##### What this ruling does **not** decide

- **The exact numeric `D`.** Not in days, weekday days, calendar months, bars or
  years. **`EXACT_D_SELECTION_BLOCKED_BY_Q10_AND_REMAINING_DURATION_AUTHORITY`** —
  Q10 is the upstream authority on day convention and duration semantics and is
  unruled, and no committed source supplies an α, a power target or a
  false-negative tolerance. None is invented here.
- **Family A's fate.** The Zero-Data verdict
  `SAMPLE_FLOOR_REACHABILITY_NOT_DETERMINABLE_WITHOUT_MEASURED_INPUTS` stands
  unchanged. Freeze *semantics* are settled; reachability is not, and this ruling
  neither passes nor fails family A.
- **NR-K, NR-L, Q1, Q3, Q8, Q9.** Untouched — see §8.1.9.

So the ruling is best read as: **`Q11_AND_SECTION0_RULED_ON_FREEZE_SEMANTICS`**.

##### The consequence the ruling creates, stated rather than left implicit

Ruling B bars observing **empirical pair correlation** before the freeze. That
**forecloses limb (ii)** of §8.1.6's sizing partition, whose only example was the
design-span `mean_abs_pairwise_corr`. So `D` may be sized on **availability
metadata alone** — calendar span, weekday and session counts, rollover and holiday
exclusions, pair inventory, source-minute completeness.

**It follows that `D` cannot be sized to reach `N_eff ≥ 400` at all.** Every input
that would let anyone target that floor is now either outcome-side or foreclosed.
That is not an oversight in the ruling; it is coherent with Ruling C, which
instructs that the result at the frozen `D` be accepted. It does mean the
programme is choosing a span on availability and accepting whatever sample it
yields — which is the price of an outcome-blind duration, and is worth naming
before it is paid rather than after.

#### 8.1.1 Why they are one referral

Not because they resemble each other. Because they share all four of:

| | |
| --- | --- |
| **Same authority** | Ruling 2's holdout span — not the §9 threshold table |
| **Same variable** | the holdout duration `D` (`T_h`), and both limbs relax monotonically in it |
| **Same remedy** | a longer `D`, **fixed at forward-epoch adoption** — never an extension of a measured span |
| **Same decision boundary** | *when* `D` may be set, and on what information |

And each makes the **same conflation**: each computes at "the frozen minimum" as
though the minimum were the operative duration. It is not — §8.1.2.

**Neither limb dominates the parameter space.** An earlier draft of this
subsection claimed the Q11 limb strictly dominates. **That claim is withdrawn.**
The limbs cross where `(1 + 23·ω)(1 + 19·c) > 106.5` — the same product form §0.3
budgets at 4.36 — and the crossover sits *inside* the regimes this document
already names:

**`NON_NORMATIVE_DIAGNOSTIC_ONLY` — every figure in this table is a derived
diagnostic, appears in no committed source, and may not be cited as a required
duration or used to size `D` (§8.1.5, and Ruling B's "exact `D` not ruled").**

| Holdout length each limb needs (weekday UTC days) | c = 0.054 | c = 0.3 | c = 0.5 |
| --- | --- | --- | --- |
| §0 limb — regular arrivals | 25 | 67 | 105 |
| §0 limb — Poisson at the ceiling | 120 | 395 | 620 |
| §0 limb — clustered doublet (§0.4b, "not exotic") | 215 | 709 | **1,111** |
| §0 limb — the prereg's own draft estimator (§0.5) | 253 | 838 | **1,312** |
| Q11 limb, at an α this contract never committed | 1,065 | 1,065 | 1,065 |

At the grid's own highest correlation the effective-N limb **overtakes** Q11. The
earlier table selected precisely the two regimes in which Q11 wins.

**So the unification does not rest on dominance. It rests on plannability, which
is a stronger ground.** The Q11 limb is a function of the **day count alone** —
untouched by `rho_h`, `rho_x`, `P` or the trade count — so it is computable from
calendar arithmetic at the moment the contract requires the duration to be fixed.
The effective-N limb depends on three quantities every one of which is produced by
running the strategy on the span being sized (§8.1.3), so **at gate 3a it cannot
be sized at all.** That asymmetry is the reason they must be ruled together: fix a
discrimination standard and gate-3a sizing becomes a calendar computation with no
research outcome in it; leave it unfixed and **no availability-only rule justifies
any duration whatsoever.**

#### 8.1.2 The exact 2-month authority — a floor, not a target

Verbatim, and it says *minimums* in both places:

> prereg §3.1 — "frozen minimum spans (Ruling 2): **validation ≥ 3 months and
> holdout ≥ 2 months**"
>
> Ruling 2 — "**minimums** validation ≥ 3 mo, holdout ≥ 2 mo; adoption waits if
> data insufficient"

There is **no committed maximum** anywhere, and this packet invents none. So
"2 months" is a floor; the operative duration is `T_h`, marked `[FIXED-AT gate
3a]` — and, precisely, **at the gate-3a *continuation***: gate 3a has run and
expressly did not fix it (`m15_gate3a_dataset_epoch_adoption.md`: the boundaries
"remain **[FIXED-AT gate-3a continuation]** when the data exists"; the manifest
carries `"holdout_span_utc": "PENDING"`).

**The minimum must not be read as the planned duration.** Gate 4 points the other
way — "gate 3a should prefer a holdout longer than the 2-month minimum when
accrued forward data allows" — but that sentence is labelled **"Feasibility note
(non-binding)"** in the audit itself and is absent from the binding T-1…T-7 list.
An earlier draft of this packet called it a direction; it is a preference, and the
frozen pre-registration expresses none. **The word "longer" appears nowhere in the
pre-registration.**

**And the minimum is not an acceptance criterion.** It is absent from §9's frozen
table, and failing it produces no verdict — only "adoption waits". Three things
must stay apart: a **span-admissibility floor at adoption** (Ruling 2); a **wait
rule** (prereg §3.1); and the **§9 count floors**, which are the only things that
produce a sample verdict. §0 and Q11 both compute at the first; what actually
binds is the third, on whatever span the first two produced.

**A scope correction this packet owes itself.** Ruling 10's loosening prohibition
binds "**the design audit**" over "**these thresholds**" — the §9 V/H tables. The
span minimums are Ruling 2, not §9. **Ruling 10 therefore does not reach the
duration**, and no argument here rests on pretending it does. Ruling 10 continues
to govern the Sharpe threshold, the sample floors and the turnover ceiling, none
of which this referral proposes to change.

#### 8.1.3 What is derivable

- **The holdout branch is closed, and more strongly than "barred".** The holdout
  is consumed "at its single authorised evaluation, or upon any decision-bearing
  observation of it **(including via an invalid run)**". Any longer window ending
  later still **contains** the consumed span, so an "extended holdout" is a window
  with an already-read prefix. And a genuinely disjoint later window is not an
  extension at all — prereg §3.1 already names it **Disjoint replication**, "a
  further, later or separately adopted span | future decision", a separate gate.
  **Post-measurement extension of a measured holdout has no coherent object.**
- **The invalid-run ceremony does not reach this case.** #422→#425 requires an
  invalidator proven *independently of the result*, a **code-only** fix, and a
  re-measurement of the *same* data with no feedback loop. A duration change
  satisfies none of the three: it changes the data, its trigger is the observed
  sample, and it is definitionally a change to the split. R-1 already cites that
  ceremony correctly as the **counter-example**; it must not be reached for here.
- **The latest admissible freeze is earlier than "before the holdout is read".**
  `T_v` and `T_h` are fixed at the **same moment** (prereg §3.1), and validation
  runs on the **same forward epoch** as the holdout. So a `T_h` still movable
  after validation would be sized on that epoch's own realised event rate — the
  best available predictor of the holdout's, from an adjacent span, same strategy,
  same regime. The freeze point is the forward-epoch **gate-3a continuation**.
- **Sizing can only ever be a declared assumption, never a measurement.** Of
  `N_eff`'s three inputs, `N_raw` and `rho_h` are produced by running the strategy
  on the span being sized, and `rho_h` is not even scoped to design data. **Two of
  three are unavailable in principle before the run.** It follows that
  `INSUFFICIENT_SAMPLE` at holdout is **not an error**: it is the contract's
  pre-declared output for a sizing assumption that was declared in advance and
  turned out wrong. Read as an error it invites remediation, and "we need more
  data" becomes a lever; read correctly there is nothing to remediate.

#### 8.1.4 What is **not** derivable — and one of these defeats an earlier claim

- **The validation branch is open, and an earlier statement in this packet was
  wrong about it.** §0.8 said post-hoc extension is "already barred". That is true
  of the **holdout** branch only. `effective_n_estimator_spec.json`
  (`APPROVED_SPEC`) resolves a **measured** validation insufficiency to: "family A
  closes **or adoption waits** per the frozen contract; **no holdout is touched**."
  A validation sample cannot be insufficient before adoption — there is no sample —
  so this is a post-measurement trigger with re-adoption as an authorised
  disposition, on a branch where consumption never fires. The disjunction has **no
  selector**, the validation floors are caller-supplied (`effective_n.py` fails
  closed to `NOT_EVALUATED_AT_THIS_ROLE`), "the family's minimum" has no
  antecedent, and the validation span is nowhere declared consumed or one-shot.
- **The closure clause does not reach a holdout-role verdict at all, and an
  earlier claim in this packet was wrong about it.** §0.8 said "the registered plan
  *contains* the remedy". **Withdrawn.** The clause sits under the heading "**What
  closes the family before any holdout touch:**", so it governs a *pre-holdout*
  verdict only. A holdout-role `INSUFFICIENT_SAMPLE` is governed by §9 H, Ruling 11
  ("an effective-N failure prevents holdout acceptance") and the estimator spec
  ("holdout acceptance cannot be granted") — **none of which states a remedy or a
  closure.** So the contract neither closes family A on this ground nor keeps it
  open; it is silent.
- **"The registered data plan" is undefined.** The phrase occurs **exactly once**
  in the pre-registration and once repo-wide — in the clause itself; `remed*`
  likewise occurs exactly once, on the same line. Two readings are available and
  they move the clause in **opposite** directions: the plan as prereg §3 (which
  contains a minimum, no maximum, and only pre-adoption freedoms), or the plan as
  the gate-3a adoption record (under which the remedy set is strictly narrower).
  Playbook §2.8 requires the narrower reading until a ruling adopts the wider one.
  **`REGISTERED_DATA_PLAN_REFERENT_AND_CONTENTS_NOT_DETERMINABLE`.**
- **No general amendment procedure is registered.** Ruling 10's tighten-or-refer
  clause is scoped to §9's acceptance thresholds; **Ruling 2 carries no such clause
  at all**, and the prereg's only amendment idiom is instance-scoped. So citing
  "a Ruling-10 referral" against a span change does not hold —
  **`NO_GENERAL_CONTRACT_AMENDMENT_PROCEDURE_REGISTERED`**, and the only route is a
  fresh human + ChatGPT ruling.
- **And this limb has no verdict.** `INSUFFICIENT_SAMPLE` is defined only on raw
  and effective **counts**, so an imprecise Sharpe on a contract-compliant span
  yields an ordinary pass/fail. §0's limb has a named verdict and a (pre-holdout)
  closure clause; Q11's limb has neither. **A ruling that supplies a remedy only
  for the counts limb would leave the Sharpe limb with no verdict, no remedy and no
  closure — silently standing**, which is precisely what merging the referral
  exists to prevent.
- **The remedy clause's scope is genuinely ambiguous, and the drift is recorded.**
  prereg §3.1 qualifies it — "if insufficient forward data has accrued **at
  adoption time**, adoption waits" — and its direction is anti-shrink only
  ("impatience cannot **shrink** the holdout"). But the one downstream place the
  rule is quoted, `m15_gate3a_dataset_epoch_adoption.md`, renders it as "if
  insufficient forward data has accrued, adoption waits" — **dropping the
  qualifier**, and introducing it as "the frozen contract's own rule". The
  de-qualified form is timeless, and it is the form the estimator spec then applies
  to a measured result.
- **Gate 4 §11 is the strongest foothold for the permissive reading**, and it is in
  an *accepted* audit: "a false rejection into `INSUFFICIENT_SAMPLE` is
  **recoverable by adopting more forward data — acceptable by design**." Read
  post-holdout it contradicts the consumption rule; read pre-adoption it merely
  restates "adoption waits". Both readings fit the words.
- **No error rate is committed anywhere.** The ≥ 0.8 threshold is frozen; the
  type-I and type-II rates it is meant to deliver are not — not in the prereg, not
  in gate 4, not in the estimator spec. So "measurable" has no fixed meaning, and
  any claim of the form "the criterion needs `D` = X" silently supplies one.
- **No committed artifact records the assumption a span was sized from.** The
  adoption manifest enumerates what gets fixed at the continuation — source, spans,
  inventory hash, retention binding, no-overlap proof — and **no sizing rationale**.
  So "we re-derived from a corrected assumption" has no baseline to be checked
  against.

#### 8.1.5 What the Sharpe limb does and does not say — three corrections

**`NON_NORMATIVE_DIAGNOSTIC_ONLY`.** Every number in this subsection — and in
§8.1.1's crossover table — is a derived diagnostic, not committed authority. None
of `~1,065`, `~1,111`, `~1,312`, `37%`, `43%`, the one-sided 5%, or any α or power
figure appears in any committed source. They are retained because they show *why*
the referral was needed; **none may be promoted to contract justification, cited
as a required duration, or used to size `D`.**

Stated because an earlier draft of this packet got each of them wrong, and each
error ran in the direction of making the case look stronger than it is.

**(a) The 50% figure is invariant in `D` and is not a fact about the minimum.**
`P(observed ≥ 0.8 | true = 0.8) = 0.5` at **every** holdout length — 43.6 days,
one year, ten years. It is a tautology of comparing an unbiased estimator with its
own true value under a symmetric sampling law. Only the false-positive limb moves:
≈ 37% at the minimum, 21% at one trading year, 5% at 1,065 days. An earlier draft
presented both as consequences of the frozen minimum; only one is.

**(b) Any stated "required duration" imports an error rate the contract never
committed.** A corpus search of the pre-registration, the gate-4 audit and the
estimator spec finds **no** significance level, confidence statement, power target
or standard-error requirement — for the Sharpe row or any other. The ≥ 0.8
criterion is a bare **point comparison** on a realised statistic, frozen "as
printed". So `1,065` is not a neutral consequence of the SE; it is the length at
which a no-edge strategy clears 0.8 only 5% of the time, and the answer swings
**12×** across plausible α:

| α (one-sided) | 0.25 | 0.20 | 0.10 | 0.05 | 0.01 |
| --- | --- | --- | --- | --- | --- |
| weekday days | 179 | 279 | 647 | 1,065 | 2,131 |

`1,065` additionally accepts a **50% false-negative rate at the target edge**; a
conventionally powered design (α = 0.05, power 0.80) needs ≈ 2,434 weekday days
≈ 9.7 years. **Choosing α is the ruling being asked for, not an input to it.**

**(c) The discrimination gap overstates the frame, and the real exposure is the
false negative.** 37% is the marginal false-positive rate of **one row of a
ten-row conjunction** — and the Sharpe row is *nested inside* the `net expectancy
> 0` row rather than additional to it, since an annualised Sharpe ≥ 0.8 > 0
implies positive mean daily PnL. Gate 4 §11 already ruled the conjunction
"demanding", validation must be passed first, and gates 8–10 plus mandatory
disjoint replication sit *after* holdout acceptance — **so a false positive is
caught.** This packet's own §10 and §7 R5 already make expectancy, not Sharpe, the
discriminating statistic.

A false negative is not caught. The holdout is consumed and unrepeatable. And this
is the part duration cannot fix: a strategy at a true annualised Sharpe of **1.2 —
50% above the frozen target — is vetoed by the Sharpe row alone 43% of the time at
the minimum and still 21% at 1,065 days**, and a strategy sitting exactly at 0.8
is vetoed 50% of the time **at every `D`**. That is an inherent property of a
point comparison. **It is emphatically not an argument to lower 0.8** — Ruling 10
forbids it, and tightening would make the false-negative rate worse.

#### 8.1.6 What information may set `D`

The intuitive split — "availability metadata yes, research outcomes no" — is the
wrong axis, because a trade **count** looks like metadata and is not.
`N_raw` counts events that "pass the cost-hurdle **and fire an EV-gated trade**",
so it is a monotone functional of how much positive expected edge the model
believes it sees. The operative rule is **self-reference**:

**Superseded in part by Ruling B (§8.1.0): limb (ii) is foreclosed.** The ruling
bars observing empirical pair correlation before the freeze, and the design-span
`mean_abs_pairwise_corr` was limb (ii)'s only example. **`D` is therefore sized on
limb (i) alone.** The partition is retained below because limb (ii) still governs
quantities other than `D`, and because the rule's *shape* — self-reference — is
what generalises.

> A quantity may inform the duration decision only if **(i)** it is computable
> without running any strategy on any span, or ~~**(ii)** it is a DESIGN-span
> quantity estimated under a rule registered before the estimate was produced and
> frozen before `D` is fixed~~ *(foreclosed for `D` by Ruling B)*. **No quantity
> realised in the span whose length is being chosen may inform that choice** — not
> its trade count, not its gaps, not
> its coverage, not its correlation.

| | |
| --- | --- |
| **Admissible (limb i)** | calendar span; weekday and session counts; rollover and holiday exclusions; pair inventory; source-minute completeness |
| **Admissible (limb ii), conditionally** | `mean_abs_pairwise_corr` — the *only* deflator the spec scopes to DESIGN data, "never validation/holdout". Conditional on **NR-L** being closed first, since its freeze point is undefined and nothing today guarantees it is frozen *before* `D` is chosen |
| **Inadmissible** | `N_raw` · realised inter-event gaps and `rho_h` (also role-measured) · eligible-bar counts (cost-table dependent — limb ii at best, never on the sized span) · `daily coverage` (numerator is days with trades) · every performance metric |

#### 8.1.7 The options — HISTORICAL, superseded by Ruling B

**Historical record.** These are the four classes the ruling was taken on.
**Option B is adopted** (§8.1.0 Ruling B); A and C are refused; D survives only in
the form B already requires. The analysis is retained so the ruling can be checked
against what it chose between, not because any choice remains open.

**Option A — 2 months is only a floor, and extension after measurement is
permitted.**
*Authority:* Ruling 2's floor with no maximum; gate 4 §11's "recoverable by
adopting more forward data" — **a non-binding risk note, outside the T-list, never
carried into the pre-registration**; the estimator spec's validation branch.
*Benefit:* Family A is not lost to a sizing mistake.
*Risk:* **Destroys the holdout.** `N_eff` and the Sharpe SE are monotone in the
same `D`, so any `D` short enough to risk `INSUFFICIENT_SAMPLE` is short enough
that the Sharpe estimate is uninformative — the escape hatch and the failure fire
on the same knob. That is optional stopping with the stopping statistic coupled to
the test statistic by construction. At the minimum, an edgeless strategy clears
0.8 about **37%** of the time per look.
*Consequence:* On the holdout branch it has no coherent object (§8.1.3).
*Amendment:* Yes — prereg §3.2's consumption rule.

**Option B — the exact duration is frozen before any outcome inspection.**
*Authority:* prereg §3.1's `[FIXED-AT gate 3a]`; Ruling 1's "gate 3a must complete
before any implementation PR reads or derives data"; gate order §10 places
adoption four gates before the single run.
*Benefit:* Preserves the holdout. And it **forces the disclosure** — because the
SE falls only as `1/√D`, a human who must write `T_h` down in advance is
confronted with the real cost and rules on it knowingly. Under A that cost is
never quoted.
*Risk:* Freezing the *number* without freezing the *assumption* leaves it
re-derivable from a design-span estimate chosen after its result was seen; and
"before any outcome inspection" is an intention unless tied to a committed event.
*Consequence:* `INSUFFICIENT_SAMPLE` becomes a real possible outcome, accepted in
advance.
*Amendment:* **No.** This is what the contract already says, made checkable.

**Option C — exactly 2 months for family A.**
*Authority:* **none found.** No committed text makes the minimum a maximum.
*Risk:* Contradicts gate 4 §5's accepted "should prefer a holdout longer than the
2-month minimum". And §0 shows it is very likely the wrong span — the deflator
budget is 4.36 and ordinary Poisson arrival spends 5.90 alone. **C maximises the
probability of landing in `INSUFFICIENT_SAMPLE` on a one-shot holdout, i.e. it
manufactures the situation in which Option A gets argued for.**
*Amendment:* Yes — it would convert a floor into a ceiling.

**Option D — an authority-derived sizing rule.** `D` = the longest holdout the
accrued forward data supports at adoption, subject to ≥ 2 months and ≥ 3 months of
validation preceding it.
*Authority:* gate 4 §5 and §11 read as instruction — **though the audit labels
them non-binding**; Ruling 2's floor; prereg §3.1's `[FIXED-AT gate 3a]`. Every
limb committed **except one**.
*Risk:* The uncommitted limb is the **adoption decision date**, and that is exactly
where the lever migrates — "wait one more month before adopting" is arithmetically
identical to "extend the holdout by one month". Playbook §1 gives an *earliest*
(≈ 2026-10) and no latest.
*Consequence:* **D is safe iff the adoption decision date is frozen with the same
discipline the duration would otherwise need.** Unfrozen, D is A wearing a
different hat.
*Amendment:* No, if the adoption date is fixed; otherwise yes in effect.

#### 8.1.8 The recommendation that was offered — and what the ruling did with it

**Option B, or equivalently D with the adoption decision date frozen alongside
`D`** — **adopted by the ruling as Ruling B.** One limb of the recommendation was
*not* carried: the ruling fixes the freeze of `D` and does **not** state that the
Gate-3a continuation *date* is itself frozen. §8.1.9 records that as a live
residual, because a late adoption date is arithmetically equivalent to a longer
`D`.

*Authority:* it is what prereg §3.1, Ruling 1 and gate order §10 already provide;
no amendment is required. *Benefit:* it is the only class that preserves the
holdout's meaning, and it surfaces the true cost before it is paid rather than
after. *Research-integrity risk:* the residual is that the freeze is asserted
rather than checkable — closed by the wording below. *Operational consequence:* a
materially longer wait than ≈ 2026-10, and `INSUFFICIENT_SAMPLE` accepted in
advance as a real outcome. *Effect on family A:* it is **not** closed; it is sized
honestly, and a sizing that proves wrong yields a pre-declared verdict rather than
a remediation. *Contract amendment required:* **no** — which is itself the
strongest argument for it over A and C, both of which need one.

This recommendation is **not** chosen because it keeps family A alive. On the
contrary, it makes an unfavourable outcome more likely to be reached and recorded.

**Normative wording candidate** (for the ruling to adopt, amend or reject):

> `T_v` and `T_h` appear as literal UTC instants in the committed forward-epoch
> adoption artifact, together with the `(rate, overlap, correlation)` assumption
> used to derive them. That commit is an **ancestor of the code SHA of the
> validation run**, and no later commit alters either value. No quantity realised
> on the forward epoch informs either. `INSUFFICIENT_SAMPLE` is the pre-declared
> outcome of a wrong sizing assumption, not a defect, and is not remediated by
> lengthening a span that has been measured.

Three checks, all mechanical, all over committed objects. No new machinery, no
artifact, no threshold, no maximum.

#### 8.1.9 Dependencies and residuals

**The live residual: the Gate-3a continuation *date* is not frozen.** Ruling B
freezes `D` at the continuation boundary. It does not fix **when that boundary is
declared reached** — and because `D` is bounded by accrued data, choosing a later
adoption date is arithmetically equivalent to choosing a longer `D`. Committed
authority gives an *earliest* (≈ 2026-10) and no latest. The ruling therefore
closes the direct lever and leaves an indirect one open. It is not closed here,
because closing it would be ruling something the ruling did not rule:
**`GATE3A_CONTINUATION_DATE_NOT_FROZEN_RESIDUAL_AFTER_Q11_SECTION0_RULING`.**
The residual is narrower than the original lever — a late date cannot be chosen in
response to a measured `N_eff`, since Ruling B puts the freeze before every
measurement — but it is not nothing, and it should be put with Q10.

**NR-K** (`P` caller-supplied) and **NR-L** (`mean_abs_pairwise_corr` has no
production rule or freeze point) are **not ruled**, and the ruling changes their
sequencing rather than their substance:

| | Status | Relation to the ruling |
| --- | --- | --- |
| **NR-K** | `NR_K_REQUIRES_HUMAN_CHATGPT_RULING_AFTER_Q10` | Independent of `D`. Whether a `P` freeze-point is also needed, and whether it must precede the `D` freeze, is to be settled after Q10. It is **not** a pair-universe remedy — R-2a bars pair selection outright. |
| **NR-L** | `NR_L_REQUIRES_HUMAN_CHATGPT_RULING` | Ruling B **moots its earlier role here**: the correlation may no longer inform `D` at all, since it is an empirical quantity and the freeze precedes every empirical observation. NR-L survives as its own question — where the correlation is measured from (training / validation / holdout) and when it is frozen — and no value is invented. |

**They must not be merged into the duration question.** Three separate levers act
on the same floor, and collapsing them would let a ruling on one read as settling
the others.

Not ruled here and unaffected: **Q1** stays `REQUIRED_NOW`, default (b) — real-data
read remains unauthorised and read-only confers no exemption; permitting it needs
an explicit contract amendment. **Q3** depends on Q1. **Q8** blocks any stage that
writes. **Q9** keeps the playbook §2.8 narrower reading as its default.

**Q10 is now the next upstream ruling** — see §8.2.

**And `N = 1` is not reopened by this.** A different `D` is not a second research
iteration, a retry or a confirmation run. Ruling C routes it through
`NEW_EXPLICIT_PREREGISTRATION_OR_CONTRACT_DECISION_REQUIRED` precisely so it
cannot be laundered into one: **within the same Family A and the same
pre-registration, a post-freeze rerun is forbidden.**

---

### 8.2 Q10 — the next upstream ruling

**`Q10_NEXT_HUMAN_CHATGPT_RULING_REQUIRED`.** Not ruled here. It is upstream of
everything numeric in this packet, and after §8.1 it is what blocks `D`.

**What Q10 has to settle.** The frozen criterion is `daily portfolio Sharpe
(ann., UTC-day) ≥ 0.8`, and the sampling *unit* is committed. What is not:

- **What a "day" is** for the purposes of a duration — calendar days, weekday UTC
  days, eligible trading days after Ruling 4's rollover exclusion and the
  `[FIXED-AT design audit]` holiday calendar, sessions, or bars. These give
  materially different answers: the same two-month floor is 61 calendar days or
  ≈ 43.6 weekday days, and the corridor in §0 moves with the choice.
- **Which of those `D` is denominated in**, and whether the duration unit and the
  annualisation factor must sit on the same clock — 5/7 implies ≈ 260.7 weekday
  days per year against an annualisation of 252, a ~1.7% inconsistency no
  committed source resolves.
- **The coverage denominator** for `daily coverage ≥ 0.60`, which changes both the
  active-day count and the reported Sharpe level.
- **Its relation to the sample-planning arithmetic**, since every figure in §0 and
  §8.1 is stated in weekday UTC days by convention, not by authority.

**Is it derivable?** Partly, and the parts differ. Committed *arithmetic* points at
trading days — gate 4 computes "a 2-month holdout (~43 trading days)", and the M1
precedent used 8,082 trades over 48 UTC days — but neither is a **definition**, and
what counts as a trading day is itself unfixed while Ruling 4's holiday policy
remains `[FIXED-AT design audit]`. So: **the convention is not derivable today,
and choosing one is a ruling.** Whether it is an amendment or a gap-filling
decision depends on which limb, and this packet does not pre-judge that.

**What Q10 must not do.** It may not loosen the ≥ 0.8 threshold, the sample floors
or the turnover ceiling. Ruling 10 permits tightening or referral only, and the
threshold is not in question — only the units it is evaluated in.

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

### 12.1 Second review round — the zero-data feasibility derivation

Five further independent doc-only roles were run against the derivation before it
was written into §0: quantitative feasibility, prereg/contract authority, research
methodology, an adversarial "can `N_eff` be inflated?" brief, and
governance/minimum-scope. They were given the lead's derivation **to attack**, and
they defeated its central claim.

**What they overturned.** The lead's first derivation concluded that the turnover
ceiling structurally excludes horizon overlap, so `rho_h = 1.00` exactly and the
frozen floors are reachable in months — verdict `STRUCTURALLY_FEASIBLE`. Three
independent defects killed it: the spec's `mean_overlap_fraction` is a **mean over
realised gaps**, so Jensen's inequality runs against the mean-gap argument; the
turnover figure is a holdout **mean** (`metrics.py:120`), which bounds no
individual gap; and the concentration cap bounds only the *largest* pair's share.
Every arithmetic figure in the original derivation reproduced exactly — **the
errors were entirely in the premises**, which is why a green calculation was not
evidence of a sound one.

**What they found that the lead had missed entirely.** The pre-registration
contains its **own draft overlap estimator** — "mean overlap factor ≈
horizon/mean inter-event gap" — which at the frozen ceiling yields exactly the
`overlap = 0.5` premise the lead had rejected as out-of-contract. The lead's
rejection was wrong, and two committed formulas disagree by 12.5× at the frozen
ceiling (§0.5). The adversarial role additionally found that the reported pair
count `P` is caller-controlled and that a *smaller* universe reaches the floors
faster (§0.6) — the exact opposite of what this packet's Q2 asserted.

**Where the lead overrode a role.** Two roles put the maximum-concentration corner
at ~4.3 years. Recomputed, that figure applies `P = 20` to a three-pair
allocation, while the spec defines `P` as the *contributing* count; consistently
computed it is ~1.1 years. **The 4.3-year figure is not adopted**, and neither is
the lead's own earlier 24.9/day accrual, which was one allocation presented as the
worst case.

**Corrections this packet makes to its own earlier text**, each named in place
rather than quietly edited: the `rho_h = 1` claim (§0.4a); the rejection of the
3.3-year figure (§0.5); Q2's pair-count monotonicity, which had the sign backwards
(§8); the "may moot Q1 and Q3" expectation (§7, §13); "`rho_x` already carries the
dependence the edge question needs" (§0.6); and Q9's silence, which left the wider
reading in force by omission (§8).

**And the anti-overengineering test was applied to this round too.** Declined:
replacing the committed estimator with a statistically better-behaved one —
Ruling 10 permits only tightening or referral, and the committed form is what
`INSUFFICIENT_SAMPLE` is computed from, so its crudeness is recorded (NR-K, NR-L)
and not acted on. Also declined: adopting any of the modelling processes named in
§0 as contract values. They are references for a grid, not authority.

---

### 12.2 Third review round — the Q11 + §0 unified referral

Four fresh doc-only roles — prereg/contract interpretation, statistical sample
planning, research integrity and degrees of freedom, and an adversarial "can the
duration be changed after outcomes are seen?" — were given the lead's
reconstruction **to attack**. They defeated four of its claims. Every decisive
finding was re-verified by the lead at source before adoption.

| Claim the lead made | Outcome |
| --- | --- |
| "The Q11 limb strictly dominates" | **Refuted.** It fails at the grid's own highest correlation: the clustered-doublet and prereg-draft regimes need 1,111 and 1,312 weekday days against Q11's 1,065. The earlier table selected exactly the two regimes where Q11 wins. |
| "…without inventing any test", alongside a figure of ~1,065 days | **Self-contradictory.** 1,065 *is* a one-sided 5% test. The answer swings 12× across plausible α (179 → 2,131 days), and 1,065 additionally accepts a 50% false-negative rate at the target edge. |
| The 37%/50% pair as consequences of the minimum | **Half wrong.** The 50% limb is invariant in `D` — a tautology at every holdout length. Only the 37% moves. |
| "the registered plan *contains* the remedy" (§0.8) | **Withdrawn.** The clause is headed "what closes the family **before any holdout touch**", so it never reaches a holdout-role verdict; and its key term is undefined. |
| "post-hoc extension already barred" (§0.8) | **True of one branch only.** The estimator spec resolves a *measured* validation insufficiency to "family A closes **or adoption waits** … no holdout is touched" — post-measurement re-adoption, unselected, on a branch where consumption never fires. |
| gate 4 "directed" a longer holdout | **Non-binding.** The audit labels it "Feasibility note (non-binding)" and omits it from T-1…T-7. |
| "the contract's fastest route … is ten pairs" (§0.6) | **Not a contract route.** R-2a bars pair selection; NR-K is an estimator caller-contract defect. |

**Two findings the roles supplied that the lead had missed entirely.** The
discrimination framing **overstates** the frame — 37% is one row of a ten-row
conjunction, and the Sharpe row is *nested inside* the `net > 0` row rather than
additional to it — while the real exposure is the **false negative**, which the
gate ordering does not absorb and which duration cannot cure: a strategy at a true
Sharpe of 1.2, half again the target, is vetoed 43% of the time at the minimum.
And the unification's correct ground is not dominance but **plannability**: the
Sharpe limb is a function of the day count alone, so it is the only limb sizeable
at the moment the contract requires the duration to be fixed.

**Where the lead overrode a role.** One report concluded the two limbs are unified
partly by "one limb strictly dominating". The statistical recomputation refutes
that and the lead verified the refutation independently; the unification is
retained on plannability instead.

**Anti-overengineering.** Nothing was added beyond the referral: no maximum
holdout, no extension rule, no error rate, no new machinery, no production
hardening. Declined: inventing an α; inventing a validation floor; merging NR-K or
NR-L into this referral; and treating "wait long enough" as an acceptance proof.

---

## 13. Completion state

**`M15_MINIMUM_RESEARCH_GATE_PENDING_HUMAN_CHATGPT_RULING`** — one completion
state, unchanged. The unified referral carries
`Q11_AND_SECTION0_PENDING_HUMAN_CHATGPT_RULING` as a status, not as a second
completion state.

The boundaries (§3), the integrity requirements (§4), the scope test (§5), the
non-implications (§6), the staged flow (§7), the output classification (§9) and
the metric set (§10) are derived from committed authority and are offered as
ruled text.

**§8.1 records a human + ChatGPT ruling on the frozen 2-month minimum.** Two
months is a **floor**, not the operative duration; the exact `D` is frozen **once,
at the Gate-3a continuation boundary, before any validation or holdout data,
empirical sample quantity, correlation estimate or performance outcome**; and
post-freeze extension, shortening, reselection, rerolling and replacement are
forbidden for the current Family A. An insufficient-sample outcome at the frozen
`D` is accepted as the result; a different `D` requires a new explicit
pre-registration or contract decision. The governing principle is
`DURATION_SELECTION_MUST_BE_OUTCOME_BLIND`.

**What the ruling did not settle, and what it newly exposes.** The **exact numeric
`D` is not ruled** — blocked by Q10, and by the absence of any committed α or power
target; none is invented. **Q10 is now the next upstream ruling** (§8.2). The
ruling also leaves one indirect lever open: it freezes `D` at the continuation
boundary but does not fix **when that boundary is declared reached**, and a later
adoption date is arithmetically equivalent to a longer `D`
(`GATE3A_CONTINUATION_DATE_NOT_FROZEN_RESIDUAL_AFTER_Q11_SECTION0_RULING`). And it
carries a consequence worth naming: because empirical correlation may not be
observed before the freeze, **`D` can be sized on availability metadata alone, and
therefore cannot be sized to reach `N_eff ≥ 400` at all** — coherent with the
instruction to accept the result, and the price of an outcome-blind duration.

**Unchanged by the ruling:** the Zero-Data verdict
`SAMPLE_FLOOR_REACHABILITY_NOT_DETERMINABLE_WITHOUT_MEASURED_INPUTS`; Q1
(`REQUIRED_NOW`, default (b)); NR-K and NR-L, both unruled; FR-19, open; and
`N = 1`, which a post-freeze rerun may not be laundered into reopening.

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

**The zero-data feasibility question has now been answered, and the answer is
"undetermined".** §0 performs the derivation as arithmetic over committed
constants — nothing executed, nothing read. An earlier version of this packet
called it "the cheapest decisive thing in the whole packet" and expected it might
make Q1 and Q3 unnecessary. **That expectation is withdrawn**: three inputs are
empirical, not two; an honest grid spans roughly 25 weekday days to over a decade;
and a range that wide moots nothing.

What survives is narrower and still useful. The derivation **refutes the reverse
claim** — that the floors are comfortably reachable at the frozen 2-month
minimum — and it re-derives, rather than discovers, the corridor gate 4 already
recorded as "intentionally demanding but narrow" with "adopt more forward data" as
its pre-blessed remedy. It also converts the question into one a human can rule
on: what forward-accrual date does each corner imply, against a committed earliest
adoption of ≈ 2026-10?

**Q1–Q11, classified.** Every item in §8 is by construction human-ruled; the
classification records the *primary* disposition and what changes if the
zero-data derivation had come out infeasible.

| Q | Disposition now (verdict: undetermined) | If family A were infeasible |
| --- | --- | --- |
| **Q1** derivation-artifact precondition | **REQUIRED_NOW** · default **(b)** is `DERIVABLE_FROM_COMMITTED_AUTHORITY`; departing from it `REQUIRES_HUMAN_CHATGPT_RULING` | MOOT |
| **Q2** pair set | `DERIVABLE_FROM_COMMITTED_AUTHORITY` — default `PAIRS_20` | MOOT, but **sensitive**: infeasibility invites widening the universe, which R-2a bars and which §0.6 shows is not the free win it looks like |
| **Q3** dataset, and whether reading may begin | `REQUIRES_HUMAN_CHATGPT_RULING` (Red, policy §6); the reader limb is `DEFERRED_TO_PRODUCTION` (PR #450 §10 row E) | MOOT |
| **Q4** historical period | `DERIVABLE_FROM_COMMITTED_AUTHORITY` — design span only | **Flips to `REQUIRES_HUMAN_CHATGPT_RULING`, and dangerously**: infeasibility pushes directly at a wider epoch, which Ruling 2 non-authorises. Nothing in §0 is an argument for one |
| **Q5** exploratory cost model | `DERIVABLE_FROM_COMMITTED_AUTHORITY` | exploratory limb MOOT; the cost tables persist as a `DEFERRED_TO_PRODUCTION` T-6 item |
| **Q6** initial model family / R2-before-R3 | `DERIVABLE_FROM_COMMITTED_AUTHORITY` — Ruling 8 freezes the family and §7 settles the sequencing; barely a live question | MOOT |
| **Q7** iteration budget | `DERIVABLE_FROM_COMMITTED_AUTHORITY` for `N = 1`; `REQUIRES_HUMAN_CHATGPT_RULING` only to raise. Blocks R2–R4 | MOOT |
| **Q8** where exploratory outputs live | **REQUIRED_NOW** · `REQUIRES_HUMAN_CHATGPT_RULING` — and it blocks **any stage that writes, including R0** | mostly MOOT while the work is doc arithmetic; live the moment anything is written |
| **Q9** C-7 budget | `REQUIRES_HUMAN_CHATGPT_RULING`; narrower reading now in force as the default | exploratory limb MOOT; survives for family B |
| **Q10** three Sharpe degrees of freedom | **REQUIRED_NOW** · `REQUIRES_HUMAN_CHATGPT_RULING` — §0's durations depend on Q10(ii)'s day convention, so the packet is circular with itself until it is ruled | **survives** |
| **Q11 + §0** — freeze semantics for the holdout duration | **RULED** (§8.1.0) · `Q11_AND_SECTION0_RULED_FREEZE_D_AT_GATE3A_CONTINUATION_BEFORE_DATA`. Two months is a floor; `D` frozen once at the continuation boundary before any data; no post-freeze reselection. **Exact `D` not ruled** | n/a — ruled |
| **Q10** day convention and duration semantics | **NEXT** · `Q10_NEXT_HUMAN_CHATGPT_RULING_REQUIRED` — now the upstream blocker for `D` (§8.2) | **survives** |
| **Gate-3a continuation date** | `GATE3A_CONTINUATION_DATE_NOT_FROZEN_RESIDUAL_AFTER_Q11_SECTION0_RULING` — the indirect lever the ruling leaves open; put it with Q10 | survives |
| **NR-K** `P` caller-supplied | `NR_K_REQUIRES_HUMAN_CHATGPT_RULING_AFTER_Q10` — independent of `D`; **not** a pair-universe remedy (R-2a bars one) | survives |
| **NR-L** `mean_abs_pairwise_corr` has no production rule or freeze point | `NR_L_REQUIRES_HUMAN_CHATGPT_RULING` — its earlier role here is **mooted** by Ruling B (the correlation may no longer inform `D`); survives as its own question | survives |

**Q10 and Q11 are the only two that survive an infeasibility verdict**, which is
itself the argument for having taken the derivation first. **Q11 and §0 are one
referral with two limbs**, not two: the same frozen 2-month minimum, questioned in
the sample-count dimension and the Sharpe-precision dimension, with the same
remedy — **a longer `D`, fixed at the gate-3a continuation before any validation or
holdout computation, never an extension of a span that has been measured**. §8.1
is that referral.

**They are not symmetric in consequence, and the ruling must be told so.** §0's
limb has a named verdict (`INSUFFICIENT_SAMPLE`) and a closure clause — scoped
"before any holdout touch". Q11's limb has **neither**. A ruling that supplies a
remedy only for the counts limb would leave the Sharpe limb with no verdict, no
remedy and no closure, silently standing — which is exactly the outcome merging
them prevents.

**And the earlier scoping claim is short by two, not one.** It said only Q1 blocks;
the previous revision added Q7 (blocks R2–R4). Q8 also blocks every stage that
writes, **including R0**, because §3.7 permits writes only beneath a named
research-scratch root and §9 reserves naming it to a Contract Gate-decision.
