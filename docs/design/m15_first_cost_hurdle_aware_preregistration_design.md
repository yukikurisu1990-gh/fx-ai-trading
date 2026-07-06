# Family A pre-registration design — M15-first cost-hurdle-aware trend/continuation

- **Document class:** doc-only selected-family pre-registration design (gate 3
  of the accepted Post-M1 research program). Not an implementation PR, not an
  execution PR. **Nothing is trained, read, derived, evaluated, or executed
  here.**
- **Branch:** `docs/m15-first-cost-aware-preregistration`
- **Base:** master `434e504632fa03d0e8b57d0a9646236b9507f1b2` (post PR #428 merge).
- **Governing records:** PR #427 roadmap (gate 1) + PR #428 adversarial audit
  (gate 2, `POST_M1_RESEARCH_PROGRAM_ROADMAP_ACCEPTABLE_FOR_SELECTED_FAMILY_PREREGISTRATION`),
  whose rulings **R-2a / R-2b** and binding conditions **C-1…C-8** are
  incorporated below.

## Statuses

- **`M15_FIRST_COST_HURDLE_AWARE_PREREGISTRATION_PROPOSED`**
- Carried: `POST_M1_RESEARCH_PROGRAM_ROADMAP_ACCEPTABLE_FOR_SELECTED_FAMILY_PREREGISTRATION`
  · `M1_FLAGSHIP_FIRST_RUN_QUESTION_CLOSED_FAILED_PREREGISTERED_CRITERIA`
- Always binding: **`PRODUCTION_READINESS_NOT_CLAIMED`** · **`NO_EXECUTION_PERFORMED`**

Forbidden-label note: this document does not assert `PASS`, `Tier 1`,
`FORMALLY_VERIFIED`, `PRODUCTION_READY`, `M15_AUTHORISED`, `H1_AUTHORISED`,
`H2_STARTED`, `PHASE_C2_STARTED`, `NEW_EPOCH_ADOPTED`, `BYTE_ADMISSIBLE`, or
`MEETS`; those tokens appear only in this prohibition list.

Numeric-value convention (amended): the human + ChatGPT pre-merge rulings
(§16) have been applied. Every previously-generic `[CANDIDATE]` value required
for this contract is now **frozen** as a pre-registration value; the only
remaining deferred items carry an explicit **[FIXED-AT gate 3a]**,
**[FIXED-AT design audit]**, or **[FIXED-AT implementation audit]** marker.
**Merging this PR accepts the frozen values below as the family-A
pre-registration contract** — while still authorising **no** implementation,
data adoption/derivation, training, or execution.

---

## 1. Executive thesis

**Hypothesis under test (not an expectation):** at the M15 timeframe, a
cost-hurdle-aware trend/continuation classifier over the fixed PAIRS_20
universe can select trades whose **net expectancy under an empirical
per-pair/session cost model is positive**, at a portfolio turnover within a
pre-registered budget.

- **Why M15 first:** the valid M1 failure (PR #425/#426) localised to
  short-horizon economics — barriers a few pips wide with embedded spread
  consuming them, ~20-minute timeouts, 168 trades/day — and to feature
  information content. M15 attacks the economics directly: ATR-proportional
  barriers several times wider at unchanged spread, event rate ~15× lower,
  label noise reduced, while data and tooling exist today (fastest valid
  falsification — the PR #428-sustained ranking).
- **Why this is NOT a continuation of the failed M1 lineage:** different
  native timeframe, different label geometry (spread-floored barriers +
  eligibility hurdle), different decision rule (calibrated EV gate, not a raw
  class-probability threshold), different acceptance frame (cost-relative
  floors, validation-first), and — decisively — **no design input from the
  consumed holdout** (R-2b). The only shared elements are audited
  infrastructure and conventions (per-pair pip authority, evidence
  discipline).
- **Why falsifiable, and cheaply:** the family carries a **validation-first
  kill gate**: if validation net expectancy under the empirical cost model
  fails the §9 floor at every registered operating point, the family is
  **closed without consuming any holdout**. A clean negative is a valid,
  useful outcome; the design optimises for decision speed, not for rescue.
- **What closes the family before any holdout touch:** failing the validation
  floor (§9.V) at all registered EV-gate operating points; or
  `INSUFFICIENT_SAMPLE` on effective-N grounds that cannot be remedied by the
  registered data plan; or a design-audit/source-audit finding of a
  contract-level defect.

## 2. Closed prior constraints (binding)

M1 flagship **closed** (`M1_FLAGSHIP_FIRST_RUN_QUESTION_CLOSED_FAILED_PREREGISTERED_CRITERIA`);
corrected PR #425 evidence **valid `DOES_NOT_MEET`** (expectancy −3.49
pips/trade at 0.5 cell; gross −2.99; 20/20 pairs negative; no validation edge);
PR #426 accepted the closure and diagnosis; PR #427 proposed the successor
program; PR #428 accepted it with rulings R-2a/R-2b and conditions C-1…C-8.
The `365d_BA` M1 frozen holdout is **consumed**; the calendar window
**2026-03-01 → 2026-04-24 is dead for all roles at all timeframes** (§3);
same-data M1 flagship retry is **forbidden**; general M1 is admissible only
under a materially new microstructure-grade hypothesis and separate protocol.

## 3. Dataset and epoch plan (C-1 — resolved by Rulings 1–2, §16)

### 3.1 Roles and spans (approved as design-POLICY; data adoption deferred to gate 3a)

| Role | Span (UTC) | Source | Status |
| --- | --- | --- | --- |
| **Design (exploratory)** | 2025-04-25 → **2026-02-28** | M15 aggregate of the adopted `365d_BA` epoch's pre-holdout span (R-2a) | usable only after the §4 derivation artifact exists; results never citable as evidence |
| **DEAD window** | **2026-03-01 → 2026-04-24** | — | excluded from every role at every timeframe (R-2b) |
| **Validation** | 2026-04-25 → T_v | **new forward epoch** (separately adopted; gate 3a) | not yet adopted |
| **Frozen holdout** | T_v (+embargo) → T_h | same new forward epoch | not yet adopted; one-shot |
| **Disjoint replication** | a further, later or separately adopted span | future decision | required before any production-grade claim |

T_v / T_h (the validation/holdout boundary and end) are **[FIXED-AT gate 3a]**
when the forward epoch is adopted, with **frozen minimum spans (Ruling 2):
validation ≥ 3 months and holdout ≥ 2 months**; the forward epoch starts **no
earlier than 2026-04-25**; if insufficient forward data has accrued at
adoption time, **adoption waits** — the verdict `INSUFFICIENT_SAMPLE` exists
precisely so that impatience cannot shrink the holdout.

### 3.2 Rules

- **Chronological ordering:** design < (dead window) < validation < holdout <
  replication. The dead window sits between design and validation, providing a
  natural ≥ 1-month buffer in addition to formal purge.
- **Purge/embargo:** ≥ horizon + 1 = **25 M15 bars** at every role boundary
  (horizon frozen at 24 by Ruling 6).
- **Holdout consumption:** the frozen holdout is consumed at its single
  authorised evaluation, or upon any decision-bearing observation of it
  (including via an invalid run).
- **Invalid-run rule:** the #422→#425 ceremony verbatim — prove the
  invalidator from committed evidence; code-only fix; adversarial re-check;
  a corrected re-measurement only by explicit separate approval and only if
  no feedback loop occurred; otherwise holdout forfeiture.
- **R-2a compliance:** pair universe fixed at **PAIRS_20** (the 20 inventory
  pairs — no inclusion/exclusion decisions anywhere in this family); design
  results never citable as evidence; validation/holdout strictly later than
  and disjoint from the design span. **R-2b compliance:** the dead window
  appears in no role above and is banned from design/validation/holdout/
  replication/pair/session/threshold/feature/acceptance use.
- **Gate 3a placement (Ruling 1 — RESOLVED):** gate 3a is **deferred to a
  named separate PR** (proposed branch:
  `docs/m15-gate3a-dataset-epoch-adoption`). **PR #429 merges only as the
  family-A contract design** — it adopts no epoch and approves no real read.
  Gate 3a must complete **before any implementation PR reads or derives
  data**, and must provide: the design-data M15 derivation artifact; the
  forward-epoch adoption artifact; inventory; checksums; timestamp bounds;
  derivation identity; the M1→M15 aggregation identity; and the retention
  binding. Exact forward validation/holdout calendar boundaries and the
  derived-dataset inventory/checksums are **[FIXED-AT gate 3a]**.
- **Explicit non-authorisations:** no `730d_BA`; no `3650d_BA`; no epoch
  adopted by this document; no raw data read in this PR.

## 4. M15 aggregation and derived-dataset policy (C-2)

The design-data M15 aggregate is a **new derived dataset** and requires a
Gate-P2-style adoption artifact **before any real read**. Required contract
(specified now; produced later, at gate 3a / implementation):

- **Input identity:** the 20 committed `365d_BA` M1 BA files, named by the
  PR-B.1 inventory (filename + SHA-256 + size), restricted to the design span.
- **Output identity:** 20 M15 BA files with their own inventory (filename,
  SHA-256, size, `ts_min_utc`/`ts_max_utc`, row count) committed as the
  adoption artifact.
- **Boundary convention:** bars bucketed by floor(timestamp / 15 min) on the
  **UTC** clock; bar timestamp = bucket start. No DST logic (UTC only).
- **Bid/ask OHLC aggregation:** per side (bid, ask): open = first M1 open in
  bucket; close = last M1 close; high = max of M1 highs; low = min of M1 lows.
  No mid-price construction at aggregation time.
- **Partial-bar policy (Ruling 3 — FROZEN):** every bucket records
  `n_source_bars`; **event/label eligibility requires a complete bucket
  (`n_source_bars == 15`)**. Incomplete buckets are recorded for gap
  diagnostics only — they must not create labels or trade events. No
  imputation.
- **Missing-minute policy:** absent M1 minutes are simply absent (no
  imputation); a per-file gap report (count + max gap) is part of the
  artifact.
- **Weekend/rollover/holiday:** no synthetic bars across market close; buckets
  spanning the weekend boundary are terminated at close; the session/rollover
  exclusion windows for *event eligibility* are defined in §5/§6, not by
  deleting data.
- **Spread computation:** per-bar quoted spread = `ask_c − bid_c` (plus
  open-side variant recorded); this is the raw material of the §5 cost model.
- **Per-pair pip-size mapping:** `pip_size_for` (0.01 iff `*_JPY` else 0.0001)
  carried forward verbatim as the sole conversion authority; the derived
  inventory records the mapping.
- **Derivation identity:** the aggregation script's path + git SHA + its own
  config hash recorded in the artifact; re-running it must be byte-reproducible
  from the same inputs.
- **Required tests before any real read (INV-1 lesson):** value-pinned
  aggregation tests on synthetic JPY-scale AND non-JPY-scale inputs (exact
  expected OHLC/spread/pip outputs); boundary tests (bucket edges, weekend,
  gaps); checksum round-trip test.
- **Not done in this PR:** no aggregation is implemented or executed here.

## 5. Cost model and spread policy (C-4 prerequisite)

- **Per-pair, session-aware empirical spread model (Ruling 4 — session
  partition FROZEN):** from design-span M15 quoted spreads, per pair ×
  session — **Asia 00:00–07:59, Europe 08:00–15:59, US 16:00–23:59 UTC** —
  estimate the median and p90 quoted spread. The numeric spread tables are
  frozen from design data **[FIXED-AT gate 3a or design audit]**.
- **All-in modelled cost per trade (Ruling 5 — FROZEN):** `cost(pair, session)
  = median_spread(pair, session) + pad_exec + cell_slippage`, with
  **`pad_exec = 0.3 pip`** (quote-vs-fill execution padding) and
  **`cell_slippage = 0.5 pip` (primary)**. This is explicitly a
  **quote-cost-validity research claim, not a live-fill claim** —
  production/paper fill validity requires the separate gate-10 track; the
  padding acknowledges (not eliminates) the executable-fill gap.
- **Stress tests (both mandatory):** (i) **2× stress** — all metrics
  recomputed at `2 × cost(pair, session)`; (ii) **p90 stress** — recomputed
  with p90 session spread substituted for the median. Acceptance requires
  survival per §9.
- **Weekend/rollover/holiday (Ruling 4 — FROZEN as minimum):** the rollover
  exclusion window is **21:55–22:15 UTC minimum** — gate 3a / the design audit
  may **widen it only for conservatism; it must not be narrowed** without a
  new human + ChatGPT ruling. Rollover windows and low-liquidity holiday
  sessions are event-ineligible (cost there is unmodelled, so no trade may be
  scored there); the holiday / abnormal-thin-liquidity exclusion calendar is
  **[FIXED-AT design audit]**, before implementation.
- **Admissibility requirements:** the cost model is admissible only if the
  spread estimates derive from the checksummed derived dataset (§4), the
  estimation script identity is recorded, and per-pair/session tables are
  committed as metadata (no raw rows).
- **Evidence requirements:** every future run's evidence records the full cost
  table used, the padding, the stress results, and
  `global_pip_size_authoritative_for_all_pairs = false` with the per-pair map.
- **Not done in this PR:** no spreads are computed here.

## 6. Label design (C-3/C-4)

- **Geometry (bid/ask-aware, B-2 heritage):** long enters next-bar ask, exits
  on bid; short mirrored; SL-first same-bar tie; timeout scored at
  horizon-end mark-to-market on the exit side. (These conventions survived
  three audits; they are carried, not re-derived.)
- **Spread-floored barriers (Ruling 6 — FROZEN):** `TP_dist =
  max(1.5 × ATR14_M15, 3.0 × cost(pair, session))`, `SL_dist =
  max(1.0 × ATR14_M15, 2.0 × cost(pair, session))`.
- **Cost-hurdle eligibility (Ruling 6 — FROZEN):** a bar is an eligible event
  only if `1.5 × ATR14_M15 ≥ 2.0 × cost(pair, session)` — bars whose
  attainable move cannot plausibly clear cost are never labeled, trained on,
  or traded. This is the family's defining condition.
- **Barrier/spread ratio requirement (C-3, Ruling 6 — FROZEN):** before
  implementation, the actual distribution of `barrier_distance / cost` on
  design data must be derived and recorded; a **median eligible ratio < 3.0
  triggers design-audit reconsideration before implementation** — M15 must
  demonstrably escape the M1 cost regime, not just claim to.
- **Horizon (Ruling 6 — FROZEN):** **24 M15 bars (6 hours)**. No horizon
  search; no label-parameter search; no post-validation label change.
- **Class vocabulary:** {−1, 0, +1} (short/timeout/long), unchanged.
- **No drift:** identical label code path for training, validation, and
  holdout; no label parameter may change after validation is first computed;
  no threshold or label search after validation.
- **Material differences from the failed M1 setup:** native M15 bars; spread
  floors; eligibility hurdle; 4–8 h horizon (vs 20 min); EV-gated decisions
  (§8) instead of raw probability cutoffs; per-pair session cost inside the
  label economics.
- **Not done in this PR:** no labels implemented.

## 7. Feature policy

| Feature group | Classification |
| --- | --- |
| Native M15 OHLC technical base (v4-style, recomputed at M15) | **allowed only after audit** (native-M15 review, C-3; warmups/windows revalidated) |
| H1/H4 completed-bar context features | **allowed only after audit** (alignment audit: only completed upper bars, no peek) |
| Session/time-of-day encodings | **allowed now** (deterministic calendar arithmetic; frozen set) |
| Realised-volatility features (from M15 history) | **allowed only after audit** |
| Spread/cost-regime features (from design-frozen cost tables) | **supporting-only** (may gate eligibility; must not become a fitted alpha input without design-audit approval) |
| Calendar/economic-event features | **deferred** (blocked pending point-in-time provenance — PR #428 ruling) |
| Carry/macro features | **deferred** (no data source) |
| Microstructure/tick features | **deferred** (family F prerequisite) |
| M1-derived features (any) | **forbidden** — no M1 microstructure proxying from OHLC M1; M1 exists in this family only as aggregation input |

Cross-cutting prohibitions (Ruling 7): **M1 data may be used only as
aggregation input** — no M1-derived feature, no M1 microstructure proxy (from
OHLC M1 or otherwise), and no consumed-window-derived feature is allowed
(R-2b); no feature selection on any holdout; no legacy-route feature evidence
(C-8); the final feature list is frozen at the design audit and hashed into
the contract.

## 8. Model and decision policy

- **Baseline model family (Ruling 8 — FROZEN):** LightGBM 3-class classifier —
  retained deliberately: the model family was not the proven M1 failure mode,
  and changing it would confound the timeframe/cost-economics test. Params
  **frozen**: `learning_rate = 0.05`, `num_leaves = 31`, `n_estimators = 200`,
  `verbose = −1`; from-scratch training only; no deployed-model reuse; no
  model-family search; no post-result model changes.
- **Class imbalance (Ruling 8 — FROZEN):** **default = no class weighting**
  for this first M15 contract. Class frequencies are a mandatory evidence
  item (§9). If the class distribution makes the sample invalid, the run
  takes `INSUFFICIENT_SAMPLE` or invalid-status handling — **weights are
  never changed post hoc**; any future class-weighting change requires a
  separate design amendment before execution.
- **Probability calibration (C-4, Ruling 8 — FROZEN):** **isotonic
  regression**, fit on a split **carved from the training span only** — never
  validation, never holdout; **no calibration-method search**.
- **EV-gate mechanism (C-4 — the decision rule):** for each eligible bar and
  direction d ∈ {long, short}:
  `EV_d = p̂_d × W̄(pair, session) − (1 − p̂_d) × L̄(pair, session) −
  cost(pair, session)`, where p̂ is the calibrated probability of the
  direction's barrier class and W̄/L̄ are expected win/loss magnitudes in pips
  **estimated on design data and frozen** (never re-fit on validation/
  holdout). Trade direction d iff `EV_d ≥ ev_min` and `EV_d > EV_{−d}`.
  **A raw probability threshold alone is explicitly not a permitted decision
  rule.**
- **Operating-point selection (Ruling 9 — FROZEN):** `ev_min ∈ {0.0, 0.25,
  0.5}` pips; chosen on **validation only**; tie rule: **smallest passing
  `ev_min`**; selection metric: validation net expectancy subject to the
  turnover budget. The selected operating point is evaluated on the holdout
  **exactly once**. A raw probability threshold alone remains forbidden.
- **Seed policy:** any RNG actually used is recorded in the manifest; if the
  trainer convention defines none, that is recorded honestly (M1 precedent);
  reproducibility level declared (`bounded_not_bitwise_guaranteed`).
- **Not done in this PR:** no training.

## 9. Metrics and acceptance criteria (Ruling 10 — FROZEN; design audit may only tighten)

**V. Validation kill gate (evaluated before any holdout touch) — FROZEN:**
validation net expectancy under the empirical cost model > 0 **AND**
validation gross expectancy ≥ **1.5 ×** modelled all-in cost, at at least one
registered `ev_min` operating point, within the turnover budget. Fail at all
points → **family A closed, no holdout consumed**.

**H. Holdout acceptance (single evaluation, selected operating point) — FROZEN:**

| Criterion | Frozen threshold |
| --- | --- |
| net expectancy (empirical cost) | > 0 |
| gross expectancy vs cost | ≥ 1.5 × all-in cost |
| stressed-cost survival | net expectancy ≥ 0 at 2× cost AND ≥ 0 at p90 session spread |
| daily portfolio Sharpe (ann., UTC-day) | ≥ 0.8 |
| max equity drawdown (vs fixed notional) | ≤ 0.15 |
| trade count lower bound | ≥ 1,000 holdout trades AND effective-N ≥ 400, else `INSUFFICIENT_SAMPLE` |
| daily coverage | ≥ 0.60 |
| turnover upper bound | ≤ 40 trades/day portfolio-wide |
| pair trade concentration | ≤ 0.40 |
| pair positive-PnL concentration | ≤ 0.50 |
| class-frequency sanity | recorded; defect trigger only, not a standalone pass/fail gate |
| concurrency/exposure | recorded; caps **[FIXED-AT design audit]**, before implementation |

**Loosening prohibition (Ruling 10):** the design audit may only **tighten**
these thresholds or refer them back for a new human + ChatGPT ruling — it may
not loosen them.

**Mandatory evidence schema (C-5):** exit-type counts (TP/SL/timeout),
timeout share, gross/net layer decomposition, class frequencies, concurrency
metrics, per-currency exposure, full cost-model metadata, EV-gate metadata
(candidates, selected, rejected-with-metrics), calibration metadata
(method + fit-span), effective-N estimate, per-pair pip map + convention +
`global…= false`.

**Effective-N (C-6, Ruling 11 — mandatory):** raw event counts overstate
independence under overlapping horizons and cross-pair dependence. The method
is **[FIXED-AT design audit or gate 3a]**, with frozen minimum requirements:
it must adjust for overlapping labels; it must adjust or discount for
cross-pair dependence; evidence must report BOTH the raw event count and the
effective-N; `INSUFFICIENT_SAMPLE` is available at validation and at holdout;
and an effective-N failure prevents holdout acceptance. Draft estimator (for
the design audit to fix): block-adjust by horizon (events per pair thinned by
mean overlap factor ≈ horizon/mean inter-event gap) and discount cross-pair by
an average-correlation factor estimated on design data. Daily-aggregation
dependence: Sharpe is computed on UTC-day portfolio sums (as in M1),
acknowledged as correlated across pairs — the per-currency exposure metric is
the monitoring instrument.

**Disjoint replication:** required before any production-grade claim; not
part of this family's acceptance.

## 10. Execution protocol (gates for this family — none skippable)

1. **This pre-registration design PR** (gate 3) — contract values frozen by
   the §16 rulings; merging this PR accepts them as the family-A contract.
2. **Fable 5 design audit PR** (gate 4) — may only tighten or refer back
   (Ruling 10).
3. **Gate 3a dataset/epoch PR** (Ruling 1: separate PR, proposed branch
   `docs/m15-gate3a-dataset-epoch-adoption`) — design-data derivation artifact
   (§4) + forward-epoch adoption artifact (§3.1); requires human + ChatGPT
   approval; **must complete before any implementation PR reads or derives
   data**.
4. **Code-only implementation PR(s)** (gate 5) — fixture-tested; value-pinned
   JPY/non-JPY tests on every conversion/aggregation path; no real run.
5. **Source-contamination audit PR** (gate 6).
6. **Single-run execution PR** (gate 7) — validation kill gate first; holdout
   once only if it passes; metadata-only scrub-clean evidence.
7. **Post-run audit PR** (gate 8).
8. **Disjoint replication decision** (gate 9).
9. **Paper/live gates** (gate 10) — separate approval track; never implied.

## 11. Source reuse / non-reuse declaration

- **Reusable as governance/evidence patterns:** ml_step4 manifest / evidence /
  acceptance / diagnostics discipline; checksum + inventory tooling; scrubber;
  protected-evidence guard; ordered hard-gate executor; **per-pair pip-size
  authority (`data_adapter.pip_size_for`) carried forward verbatim**.
- **Reusable after audit/wrapping:** feature builders (native-M15 review
  required), label helpers (`labels.py` B-2 machinery — parameterised floors/
  horizon), PnL helper (`traded_direction_pnl_price`, F-2-corrected), metric
  helpers (extended per C-5).
- **Historical-only:** all M1 flagship evidence (both directories); archived
  stage/compare logs; Phase 9.x numerics per the standing tier
  classifications.
- **Forbidden:** optimistic legacy PnL routes; deployed-model machinery in
  evidence paths; invalid backtest routes; anything reading the consumed
  window for design/tuning.
- **Live/paper runners:** engineering assets for the separate production
  gates; never research evidence.

**C-8 no-legacy-evidence declaration:** no number from the fenced legacy
routes (archived Phase 9.x numerics, pre-F-2 PnL outputs, halted tabular
evidence, stage/compare logs) enters this family's design justification,
priors, thresholds, acceptance criteria, pair selection, session selection,
feature selection, or evidence claims. Where archived context is referenced
(e.g. "small gross, fragile net at multi-TF"), it is cited as non-evidence
background only and decides nothing.

## 12. Risk register

| # | Risk | Handling in this design |
| --- | --- | --- |
| 1 | Overlapping-label effective-N | §9 effective-N gate; horizon frozen; events thinned in the estimator |
| 2 | Cross-pair dependence | fixed PAIRS_20 (no selection); per-currency exposure metric; correlation discount in effective-N |
| 3 | Non-stationarity | claim scoped to the evaluated spans; disjoint replication required for stronger claims |
| 4 | Quote-vs-fill gap | execution padding in the cost model; dual stress tests; quote-cost-validity claim scope |
| 5 | Weekend/rollover/holiday | event-ineligibility windows frozen at design audit; aggregation policy §4 |
| 6 | Class imbalance | mandatory class-frequency evidence; frozen default = no weighting (Ruling 8); INSUFFICIENT_SAMPLE/invalid handling instead of post-hoc weight changes |
| 7 | Probability calibration | training-span-only calibration split; method frozen pre-run |
| 8 | Concurrency/exposure aggregation | simulator must define overlapping-position accounting; concurrency metrics mandatory |
| 9 | M1→M15 aggregation alignment (INV-1-class) | checksummed derivation artifact; value-pinned JPY/non-JPY tests; gate-6 audit |
| 10 | Multiple-comparison budget | C-7: families A then B only; small pre-registered candidate sets (one horizon, three ev_min) |
| 11 | Operator search temptation | validation kill gate closes the family without a holdout touch; every negative closes its question; consumed data dead |
| 12 | Stopping-rule discipline | if A fails validation → B (own contracts, H1/H4 split); if B fails → mandatory program-level review; no family C without a new roadmap arc |

## 13. Blockers and open questions

**Merge blockers — RESOLVED by the §16 rulings:** the §3/C-1 dataset question
is resolved by deferral to the named separate gate-3a PR (Ruling 1), with the
span policy approved as design-policy (Ruling 2); every previously-generic
[CANDIDATE] contract value is frozen (Rulings 3–10). The remaining deferred
items below carry explicit [FIXED-AT …] markers and do not block this merge.

**Must resolve before implementation (gates 4–5 / gate 3a):**
- Forward-epoch adoption artifact + design-data derivation artifact (gate 3a
  PR `docs/m15-gate3a-dataset-epoch-adoption`): exact validation/holdout
  calendar boundaries **[FIXED-AT gate 3a]**; derived-dataset inventory and
  checksums **[FIXED-AT gate 3a]**; cost tables **[FIXED-AT gate 3a or design
  audit]**.
- Barrier/spread ratio derivation from design data (§6, C-3).
- Native-M15 feature-builder review (§7) **[FIXED-AT implementation audit]**.
- Effective-N formula details **[FIXED-AT design audit]**; concurrency/
  exposure caps **[FIXED-AT design audit]**; holiday exclusion calendar
  **[FIXED-AT design audit]**.

**Must resolve before execution (gates 6–7):**
- Source-contamination audit; evidence-schema implementation (C-5); scrubber
  coverage of the new payload fields.

**Before any production claim:** disjoint replication (gate 9) + separate
paper/live gates (gate 10).

## 14. Non-authorisation statements

This document authorises **nothing**: no implementation; no training; no
execution; no holdout evaluation; no raw data access; no metric computation;
no epoch adoption (the §3 span policy is approved as design-policy only —
data adoption happens exclusively in the separate gate-3a PR; the forward
epoch is not adopted by this text); no `730d_BA`; no `3650d_BA`; no Phase C2;
no H2/H3; no paper/live trading; no production readiness; no selected-family
run. The consumed `365d_BA` holdout and the dead window 2026-03-01 →
2026-04-24 remain quarantined. Statuses:
`M15_FIRST_COST_HURDLE_AWARE_PREREGISTRATION_PROPOSED`,
`NO_EXECUTION_PERFORMED`, `PRODUCTION_READINESS_NOT_CLAIMED`.

## 15. Recommendation for next gate

1. Merge this amended pre-registration — merging accepts the §16-frozen values
   as the family-A contract (authorising no implementation or execution).
2. Then the **Fable 5 design audit PR** (gate 4) attacks the frozen contract
   (tighten-or-refer-back only, per Ruling 10).
3. Then the **gate-3a dataset/epoch PR**
   (`docs/m15-gate3a-dataset-epoch-adoption`), implementation (gate 5), and
   source audit (gate 6) — in order, each separately approved.
4. Nothing runs until gate 7 is separately authorised with its own one-shot
   discipline.

## 16. Human + ChatGPT pre-merge rulings (applied by amendment)

Merging PR #429 accepts these rulings and the values they freeze as the
family-A pre-registration contract. They authorise **no** implementation, data
adoption/derivation, training, or execution.

| # | Ruling | Frozen outcome |
| --- | --- | --- |
| 1 | Gate 3a placement | **Separate PR** (`docs/m15-gate3a-dataset-epoch-adoption`); PR #429 merges as contract design only; gate 3a must complete before any implementation PR reads/derives data; must provide derivation artifact, forward-epoch adoption artifact, inventory, checksums, ts-bounds, derivation + M1→M15 aggregation identity, retention binding |
| 2 | Dataset spans (design-policy, not adoption) | design 2025-04-25→2026-02-28 (exploratory only, never evidence, fixed PAIRS_20); dead window 2026-03-01→2026-04-24 dead for all roles at all timeframes; validation/holdout from a new forward epoch starting **no earlier than 2026-04-25**; boundaries [FIXED-AT gate 3a]; minimums validation ≥ 3 mo, holdout ≥ 2 mo; adoption waits if data insufficient; no `730d_BA`/`3650d_BA` |
| 3 | M15 aggregation | event/label eligibility requires `n_source_bars == 15`; incomplete buckets diagnostics-only; no imputation; UTC bucket-start, per-side bid/ask OHLC, no synthetic weekend bars, value-pinned JPY/non-JPY tests, pip authority — all retained |
| 4 | Sessions & rollover | Asia 00:00–07:59 / Europe 08:00–15:59 / US 16:00–23:59 UTC frozen; rollover exclusion **21:55–22:15 UTC minimum** — widen-only-for-conservatism, never narrowed without a new human + ChatGPT ruling; holiday/thin-liquidity exclusion policy [FIXED-AT design audit], before implementation |
| 5 | Cost model | all-in cost = median quoted spread + **0.3 pip** execution padding + **0.5 pip** flat cell (primary); mandatory 2× and p90 stress; **quote-cost-validity research claim, not a live-fill claim** — production/paper fill validity requires separate gates |
| 6 | Label contract | TP = 1.5 × ATR14_M15, SL = 1.0 × ATR14_M15; floors TP ≥ 3.0 × cost, SL ≥ 2.0 × cost; eligibility 1.5 × ATR14_M15 ≥ 2.0 × cost; median eligible barrier/cost ratio < 3.0 → design-audit reconsideration before implementation; **horizon = 24 M15 bars (6 h)**; classes {−1, 0, +1}; SL-first tie; timeout MTM at horizon end on exit side; no horizon/label search; no post-validation label change |
| 7 | Feature policy | native-M15 base + H1/H4 context + realised-vol = after-audit; session/time = allowed; spread/cost-regime = supporting-only; calendar + carry + microstructure = deferred; **M1-derived features forbidden — M1 is aggregation input only**; no consumed-window features |
| 8 | Model & calibration | LightGBM 3-class, `learning_rate 0.05 / num_leaves 31 / n_estimators 200 / verbose −1`; from-scratch only; no reuse; no model-family search; **no class weighting** (frequencies reported; INSUFFICIENT_SAMPLE/invalid handling, never post-hoc weight changes; future weighting = separate design amendment before execution); **isotonic calibration**, training-span-only fit split, no method search |
| 9 | EV gate | `ev_min ∈ {0.0, 0.25, 0.5}` pips; validation-only selection; tie = smallest passing; selected point evaluated on holdout exactly once; raw probability threshold alone forbidden |
| 10 | Acceptance thresholds | validation kill gate (net > 0 AND gross ≥ 1.5 × cost, ≥ 1 registered point, within budget; all-fail → family closed pre-holdout) and holdout table (§9) **frozen as printed**; design audit may only tighten or refer back — never loosen |
| 11 | Effective-N | mandatory; method [FIXED-AT design audit or gate 3a]; must adjust for overlap + cross-pair dependence; raw count AND effective-N reported; `INSUFFICIENT_SAMPLE` at validation and holdout; effective-N failure prevents holdout acceptance |
| 12 | Program budget (C-7) | family A = M15-first; family B = H1/H4 as separate contracts if reached; A fails validation → B under its own pre-registration; B fails → mandatory program-level review; no third family without a new roadmap arc + audit |
| 13 | No-legacy-evidence (C-8) | no number from fenced legacy routes in design justification, priors, thresholds, acceptance criteria, pair/session/feature selection, or evidence claims; archived records citable only as clearly-marked non-evidence background |
